from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import requests

from src.assets.download import download_candidate_asset
from src.assets.http_client import ProviderHttpClient
from src.assets.models import (
    AssetCandidate,
    AssetLicense,
    AssetProvenance,
    DownloadedAsset,
    ProviderCapabilities,
    orientation_from_dimensions,
)
from src.assets.license_policy import apply_policy_to_candidate
from src.assets.provider_contract import (
    AssetPreview,
    AssetSearchRequest,
    DownloadContext,
    ProviderConfigurationError,
    ProviderHealth,
)


REQUEST_TIMEOUT = 24
PEXELS_LICENSE_URL = "https://www.pexels.com/license/"
PEXELS_TERMS_URL = "https://www.pexels.com/terms-of-service/"


class PexelsStockProvider:
    name = "pexels"

    def __init__(self, api_key: str, *, http: Any | None = None) -> None:
        self.api_key = api_key
        self.http = http or ProviderHttpClient(timeout=REQUEST_TIMEOUT)

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            provider=self.name,
            media_types=["video", "image"],
            supports_orientation_filter=True,
            supports_pagination=True,
            max_results=80,
        )

    def search(self, request: AssetSearchRequest) -> list[AssetCandidate]:
        if not self.api_key:
            raise ProviderConfigurationError("PEXELS_API_KEY is not configured.", provider=self.name, query=request.query)
        if request.media_type == "image":
            return self._search_images(request)
        return self._search_videos(request)

    def get_preview(self, candidate: AssetCandidate) -> AssetPreview:
        return AssetPreview(
            candidate_id=candidate.asset_id,
            url=candidate.preview_url,
            width=candidate.width,
            height=candidate.height,
            media_type="image" if candidate.preview_url else candidate.media_type,
            duration_sec=0.0 if candidate.preview_url else candidate.duration_sec,
            rendition="pexels_preview",
        )

    def resolve_license(self, candidate: AssetCandidate) -> AssetLicense:
        candidate.license = _pexels_license(candidate)
        apply_policy_to_candidate(candidate)
        return candidate.license

    def download(self, candidate: AssetCandidate, destination: Path, context: DownloadContext) -> DownloadedAsset:
        self.resolve_license(candidate)
        return download_candidate_asset(candidate, destination, context, http=self.http if isinstance(self.http, ProviderHttpClient) else None)

    def health_check(self) -> ProviderHealth:
        return ProviderHealth(provider=self.name, configured=bool(self.api_key), status="configured" if self.api_key else "missing_api_key")

    def _search_videos(self, request: AssetSearchRequest) -> list[AssetCandidate]:
        data = self.http.get_json(
            "https://api.pexels.com/videos/search",
            headers={"Authorization": self.api_key},
            params={
                "query": request.query,
                "per_page": request.max_results,
            },
            timeout=request.timeout_sec,
        )
        candidates = []
        for video in data.get("videos", []):
            best = _best_video_file(video.get("video_files", []), request.orientation_preference)
            if not best:
                continue
            width = int(best.get("width") or video.get("width") or 0)
            height = int(best.get("height") or video.get("height") or 0)
            if width < request.min_width or height < request.min_height:
                continue
            provider_asset_id = str(video.get("id") or "")
            source_page = str(video.get("url") or "")
            author = video.get("user") or {}
            # The videos endpoint returns no title and no description. The only real
            # description Pexels gives is the slug in the page URL
            # (".../video/stone-fragments-on-the-table-8516551/"), so that is used
            # instead of echoing the query back and calling it metadata.
            slug_title = _title_from_source_page(source_page)
            api_description = str(video.get("description") or "").strip()
            candidate = AssetCandidate(
                asset_id=f"pexels_video_{provider_asset_id}",
                provider=self.name,
                provider_asset_id=provider_asset_id,
                media_type="video",
                title=slug_title or f"Pexels video {provider_asset_id}",
                description=api_description or slug_title,
                tags=_slug_tags(slug_title) if slug_title else _query_tags(request.query),
                tags_source="provider" if slug_title else "query_derived",
                source_page_url=source_page,
                preview_url=str(video.get("image") or ""),
                download_url=str(best.get("link") or ""),
                author_name=str(author.get("name") or ""),
                author_url=str(author.get("url") or ""),
                width=width,
                height=height,
                duration_sec=float(video.get("duration") or 0),
                orientation=orientation_from_dimensions(width, height),
                search_query=request.query,
                project_id=request.project_id,
                scene_id=request.scene_id,
                raw_metadata={"pexels": video},
                crop_suitability_score=_crop_score(width, height),
            )
            candidate.license = _pexels_license(candidate)
            candidate.provenance = _provenance(candidate)
            apply_policy_to_candidate(candidate)
            candidates.append(candidate)
        return candidates

    def _search_images(self, request: AssetSearchRequest) -> list[AssetCandidate]:
        data = self.http.get_json(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": self.api_key},
            params={
                "query": request.query,
                "orientation": _pexels_orientation(request.orientation_preference),
                "per_page": request.max_results,
            },
            timeout=request.timeout_sec,
        )
        candidates = []
        for photo in data.get("photos", []):
            width = int(photo.get("width") or 0)
            height = int(photo.get("height") or 0)
            if width < request.min_width or height < request.min_height:
                continue
            src = photo.get("src") or {}
            provider_asset_id = str(photo.get("id") or "")
            candidate = AssetCandidate(
                asset_id=f"pexels_photo_{provider_asset_id}",
                provider=self.name,
                provider_asset_id=provider_asset_id,
                media_type="image",
                title=str(photo.get("alt") or "").strip() or _title_from_source_page(str(photo.get("url") or "")) or f"Pexels photo {provider_asset_id}",
                description=str(photo.get("alt") or "").strip(),
                tags=_slug_tags(str(photo.get("alt") or "") or _title_from_source_page(str(photo.get("url") or ""))),
                tags_source="provider" if (photo.get("alt") or photo.get("url")) else "query_derived",
                source_page_url=str(photo.get("url") or ""),
                preview_url=str(src.get("medium") or src.get("small") or ""),
                download_url=str(src.get("original") or src.get("large2x") or src.get("large") or ""),
                author_name=str(photo.get("photographer") or ""),
                author_url=str(photo.get("photographer_url") or ""),
                width=width,
                height=height,
                duration_sec=0,
                orientation=orientation_from_dimensions(width, height),
                search_query=request.query,
                project_id=request.project_id,
                scene_id=request.scene_id,
                raw_metadata={"pexels": photo},
                crop_suitability_score=_crop_score(width, height),
            )
            candidate.license = _pexels_license(candidate)
            candidate.provenance = _provenance(candidate)
            apply_policy_to_candidate(candidate)
            candidates.append(candidate)
        return candidates


def search_videos(api_key: str, query: str, per_page: int = 10, orientation: str = "landscape") -> list[dict[str, Any]]:
    if not api_key:
        return []
    response = requests.get(
        "https://api.pexels.com/videos/search",
        headers={"Authorization": api_key},
        params={"query": query, "orientation": orientation, "per_page": per_page},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.json().get("videos", [])


def search_images(api_key: str, query: str, per_page: int = 10, orientation: str = "landscape") -> list[dict[str, Any]]:
    if not api_key:
        return []
    response = requests.get(
        "https://api.pexels.com/v1/search",
        headers={"Authorization": api_key},
        params={"query": query, "orientation": orientation, "per_page": per_page},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.json().get("photos", [])


def _pexels_license(candidate: AssetCandidate) -> AssetLicense:
    return AssetLicense(
        license_name="pexels",
        license_url=PEXELS_LICENSE_URL,
        provider_terms_url=PEXELS_TERMS_URL,
        rights_status="licensed",
        commercial_use_allowed=True,
        modification_allowed=True,
        attribution_required=False,
        attribution_text=f"{candidate.media_type.title()} by {candidate.author_name} on Pexels".strip(),
        allowed_for_render=True,
        review_required=False,
        notes="Pexels normalized license metadata; verify provider terms before publishing.",
    )


def _provenance(candidate: AssetCandidate) -> AssetProvenance:
    return AssetProvenance(
        provider=candidate.provider,
        provider_asset_id=candidate.provider_asset_id,
        source_page_url=candidate.source_page_url,
        download_url=candidate.download_url,
        original_filename=Path(candidate.download_url.split("?", 1)[0]).name,
        project_id=candidate.project_id,
        scene_id=candidate.scene_id,
        search_query=candidate.search_query,
        metadata_snapshot=candidate.raw_metadata,
    )


def _best_video_file(files: list[dict[str, Any]], orientation_preference: str) -> dict[str, Any] | None:
    valid = [item for item in files if item.get("link") and str(item.get("file_type", "")).startswith("video")]
    valid.sort(
        key=lambda item: (
            _orientation_score(orientation_from_dimensions(int(item.get("width") or 0), int(item.get("height") or 0)), orientation_preference),
            int(item.get("width") or 0) * int(item.get("height") or 0),
        ),
        reverse=True,
    )
    return valid[0] if valid else None


def _pexels_orientation(preference: str) -> str:
    if preference == "vertical":
        return "portrait"
    if preference == "horizontal":
        return "landscape"
    return "square" if preference == "square" else "portrait"


def _orientation_score(orientation: str, preference: str) -> int:
    if orientation == preference:
        return 4
    if preference == "vertical" and orientation == "horizontal":
        return 2
    if preference == "horizontal" and orientation == "vertical":
        return 2
    return 1


def _crop_score(width: int, height: int) -> float:
    if not width or not height:
        return 0.0
    ratio = width / height
    return max(0.0, min(100.0, 100.0 - abs(ratio - (9 / 16)) * 100.0))


def _query_tags(query: str) -> list[str]:
    """Last resort only, and always paired with ``tags_source="query_derived"`` so the
    ranker knows not to treat these as evidence about the asset."""
    return [part.strip().lower() for part in query.replace(",", " ").split() if part.strip()]


def _title_from_source_page(url: str) -> str:
    """Pexels page URLs carry the human title as a slug: ``/video/<slug>-<id>/``."""
    path = str(url or "").rstrip("/").rsplit("/", 1)[-1]
    if not path:
        return ""
    parts = [part for part in path.split("-") if part]
    if parts and parts[-1].isdigit():
        parts = parts[:-1]
    words = [part for part in parts if part and not part.isdigit()]
    return " ".join(words)


def _slug_tags(title: str) -> list[str]:
    return [word.lower() for word in re.split(r"[\s\-_,]+", str(title or "")) if word]
