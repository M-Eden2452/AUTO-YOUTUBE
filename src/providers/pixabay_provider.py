from __future__ import annotations

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
PIXABAY_LICENSE_URL = "https://pixabay.com/service/license-summary/"
PIXABAY_TERMS_URL = "https://pixabay.com/service/terms/"


class PixabayStockProvider:
    name = "pixabay"

    def __init__(self, api_key: str, *, http: Any | None = None) -> None:
        self.api_key = api_key
        self.http = http or ProviderHttpClient(timeout=REQUEST_TIMEOUT)

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            provider=self.name,
            media_types=["video", "image"],
            supports_orientation_filter=True,
            supports_pagination=True,
            max_results=200,
        )

    def search(self, request: AssetSearchRequest) -> list[AssetCandidate]:
        if not self.api_key:
            raise ProviderConfigurationError("PIXABAY_API_KEY is not configured.", provider=self.name, query=request.query)
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
            rendition="pixabay_preview",
        )

    def resolve_license(self, candidate: AssetCandidate) -> AssetLicense:
        candidate.license = _pixabay_license(candidate)
        apply_policy_to_candidate(candidate)
        return candidate.license

    def download(self, candidate: AssetCandidate, destination: Path, context: DownloadContext) -> DownloadedAsset:
        self.resolve_license(candidate)
        return download_candidate_asset(candidate, destination, context, http=self.http if isinstance(self.http, ProviderHttpClient) else None)

    def health_check(self) -> ProviderHealth:
        return ProviderHealth(provider=self.name, configured=bool(self.api_key), status="configured" if self.api_key else "missing_api_key")

    def _search_videos(self, request: AssetSearchRequest) -> list[AssetCandidate]:
        data = self.http.get_json(
            "https://pixabay.com/api/videos/",
            params={
                "key": self.api_key,
                "q": request.query,
                "video_type": "film",
                "safesearch": "true",
                "per_page": request.max_results,
            },
            timeout=request.timeout_sec,
        )
        candidates = []
        for hit in data.get("hits", []):
            best = _best_video_file(hit.get("videos", {}), request.orientation_preference)
            if not best:
                continue
            width = int(best.get("width") or 0)
            height = int(best.get("height") or 0)
            if width < request.min_width or height < request.min_height:
                continue
            provider_asset_id = str(hit.get("id") or "")
            preview = _video_preview_url(hit)
            candidate = AssetCandidate(
                asset_id=f"pixabay_video_{provider_asset_id}",
                provider=self.name,
                provider_asset_id=provider_asset_id,
                media_type="video",
                title=f"Pixabay video {provider_asset_id}",
                description=str(hit.get("tags") or request.query),
                tags=_tags(hit.get("tags") or ""),
                tags_source="provider" if str(hit.get("tags") or "").strip() else "none",
                source_page_url=str(hit.get("pageURL") or ""),
                preview_url=preview,
                download_url=str(best.get("url") or ""),
                author_name=str(hit.get("user") or ""),
                author_url=_author_url(hit),
                width=width,
                height=height,
                duration_sec=float(hit.get("duration") or 0),
                orientation=orientation_from_dimensions(width, height),
                search_query=request.query,
                project_id=request.project_id,
                scene_id=request.scene_id,
                raw_metadata={"pixabay": hit},
                crop_suitability_score=_crop_score(width, height),
            )
            candidate.license = _pixabay_license(candidate)
            candidate.provenance = _provenance(candidate)
            apply_policy_to_candidate(candidate)
            candidates.append(candidate)
        return candidates

    def _search_images(self, request: AssetSearchRequest) -> list[AssetCandidate]:
        data = self.http.get_json(
            "https://pixabay.com/api/",
            params={
                "key": self.api_key,
                "q": request.query,
                "image_type": "photo",
                "orientation": _pixabay_orientation(request.orientation_preference),
                "safesearch": "true",
                "per_page": request.max_results,
            },
            timeout=request.timeout_sec,
        )
        candidates = []
        for hit in data.get("hits", []):
            width = int(hit.get("imageWidth") or 0)
            height = int(hit.get("imageHeight") or 0)
            if width < request.min_width or height < request.min_height:
                continue
            provider_asset_id = str(hit.get("id") or "")
            candidate = AssetCandidate(
                asset_id=f"pixabay_image_{provider_asset_id}",
                provider=self.name,
                provider_asset_id=provider_asset_id,
                media_type="image",
                title=f"Pixabay image {provider_asset_id}",
                description=str(hit.get("tags") or request.query),
                tags=_tags(hit.get("tags") or ""),
                tags_source="provider" if str(hit.get("tags") or "").strip() else "none",
                source_page_url=str(hit.get("pageURL") or ""),
                preview_url=str(hit.get("previewURL") or hit.get("webformatURL") or ""),
                download_url=str(hit.get("largeImageURL") or hit.get("webformatURL") or ""),
                author_name=str(hit.get("user") or ""),
                author_url=_author_url(hit),
                width=width,
                height=height,
                duration_sec=0,
                orientation=orientation_from_dimensions(width, height),
                search_query=request.query,
                project_id=request.project_id,
                scene_id=request.scene_id,
                raw_metadata={"pixabay": hit},
                crop_suitability_score=_crop_score(width, height),
            )
            candidate.license = _pixabay_license(candidate)
            candidate.provenance = _provenance(candidate)
            apply_policy_to_candidate(candidate)
            candidates.append(candidate)
        return candidates


def search_videos(api_key: str, query: str, per_page: int = 10) -> list[dict[str, Any]]:
    if not api_key:
        return []
    response = requests.get(
        "https://pixabay.com/api/videos/",
        params={"key": api_key, "q": query, "video_type": "film", "safesearch": "true", "per_page": per_page},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.json().get("hits", [])


def search_images(api_key: str, query: str, per_page: int = 10, orientation: str = "horizontal") -> list[dict[str, Any]]:
    if not api_key:
        return []
    response = requests.get(
        "https://pixabay.com/api/",
        params={
            "key": api_key,
            "q": query,
            "image_type": "photo",
            "orientation": orientation,
            "safesearch": "true",
            "per_page": per_page,
        },
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.json().get("hits", [])


def search_music(api_key: str, query: str, per_page: int = 8) -> list[dict[str, Any]]:
    if not api_key:
        return []
    response = requests.get(
        "https://pixabay.com/api/audio/",
        params={"key": api_key, "q": query, "audio_type": "music", "safesearch": "true", "per_page": per_page},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.json().get("hits", [])


def _pixabay_license(candidate: AssetCandidate) -> AssetLicense:
    return AssetLicense(
        license_name="pixabay",
        license_url=PIXABAY_LICENSE_URL,
        provider_terms_url=PIXABAY_TERMS_URL,
        rights_status="licensed",
        commercial_use_allowed=True,
        modification_allowed=True,
        attribution_required=False,
        attribution_text=f"{candidate.media_type.title()} by {candidate.author_name} on Pixabay".strip(),
        allowed_for_render=True,
        review_required=False,
        notes="Pixabay normalized license metadata; verify provider terms before publishing.",
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


def _best_video_file(videos: dict[str, Any], orientation_preference: str) -> dict[str, Any] | None:
    valid = [item for item in videos.values() if isinstance(item, dict) and item.get("url")]
    valid.sort(
        key=lambda item: (
            _orientation_score(orientation_from_dimensions(int(item.get("width") or 0), int(item.get("height") or 0)), orientation_preference),
            int(item.get("width") or 0) * int(item.get("height") or 0),
        ),
        reverse=True,
    )
    return valid[0] if valid else None


def _pixabay_orientation(preference: str) -> str:
    if preference == "vertical":
        return "vertical"
    if preference == "horizontal":
        return "horizontal"
    return "all"


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


def _tags(value: str) -> list[str]:
    return [item.strip().lower() for item in str(value or "").replace(",", " ").split() if item.strip()]


def _author_url(hit: dict[str, Any]) -> str:
    user = str(hit.get("user") or "").strip()
    user_id = str(hit.get("user_id") or "").strip()
    if user and user_id:
        return f"https://pixabay.com/users/{user}-{user_id}/"
    return ""


def _video_preview_url(hit: dict[str, Any]) -> str:
    picture_id = str(hit.get("picture_id") or "").strip()
    if picture_id:
        return f"https://i.vimeocdn.com/video/{picture_id}_640x360.jpg"
    return ""
