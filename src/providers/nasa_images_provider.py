from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from src.assets.download import download_candidate_asset
from src.assets.http_client import ProviderHttpClient
from src.assets.license_policy import apply_policy_to_candidate
from src.assets.models import AssetCandidate, AssetLicense, AssetProvenance, DownloadedAsset, ProviderCapabilities
from src.assets.provider_contract import AssetPreview, AssetSearchRequest, DownloadContext, ProviderHealth


NASA_IMAGES_API_BASE = "https://images-api.nasa.gov"
NASA_POLICY_URL = "https://www.nasa.gov/nasa-brand-center/images-and-media/"


class NasaImageLibraryStockProvider:
    name = "nasa_images"

    def __init__(self, *, api_base: str | None = None, http: Any | None = None, max_results: int | None = None) -> None:
        self.api_base = (api_base or os.getenv("NASA_IMAGES_API_BASE") or NASA_IMAGES_API_BASE).rstrip("/")
        timeout = float(os.getenv("NASA_IMAGES_REQUEST_TIMEOUT") or 24)
        self.max_results = int(max_results or os.getenv("NASA_IMAGES_MAX_RESULTS") or 8)
        self.http = http or ProviderHttpClient(timeout=timeout)

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            provider=self.name,
            media_types=["image", "video"],
            supports_search=True,
            supports_preview=True,
            supports_download=True,
            supports_license_metadata=True,
            max_results=self.max_results,
            notes="NASA Image and Video Library search/asset/metadata endpoints.",
        )

    def search(self, request: AssetSearchRequest) -> list[AssetCandidate]:
        data = self.http.get_json(
            f"{self.api_base}/search",
            params={"q": request.query, "media_type": request.media_type, "page_size": min(request.max_results, self.max_results)},
            timeout=request.timeout_sec,
        )
        items = data.get("collection", {}).get("items", [])
        candidates: list[AssetCandidate] = []
        for item in items[: self.max_results]:
            candidate = self._candidate_from_item(item, request)
            if candidate:
                apply_policy_to_candidate(candidate)
                candidates.append(candidate)
        return candidates[: request.max_results]

    def get_preview(self, candidate: AssetCandidate) -> AssetPreview:
        return AssetPreview(
            candidate_id=candidate.asset_id,
            url=candidate.preview_url,
            width=candidate.width,
            height=candidate.height,
            media_type="image" if candidate.preview_url else candidate.media_type,
            duration_sec=0.0 if candidate.preview_url else candidate.duration_sec,
            rendition="nasa_search_preview",
            fallback_reason="nasa_search_preview",
        )

    def resolve_license(self, candidate: AssetCandidate) -> AssetLicense:
        apply_policy_to_candidate(candidate)
        return candidate.license

    def download(self, candidate: AssetCandidate, destination: Path, context: DownloadContext) -> DownloadedAsset:
        self.resolve_license(candidate)
        return download_candidate_asset(candidate, destination, context, http=self.http)

    def health_check(self) -> ProviderHealth:
        return ProviderHealth(provider=self.name, configured=True, status="configured")

    def _candidate_from_item(self, item: dict[str, Any], request: AssetSearchRequest) -> AssetCandidate | None:
        data = (item.get("data") or [{}])[0]
        nasa_id = str(data.get("nasa_id") or "").strip()
        if not nasa_id:
            return None
        media_type = str(data.get("media_type") or request.media_type or "").lower()
        if media_type != request.media_type:
            return None
        asset_urls = self._asset_urls(nasa_id, request.timeout_sec)
        metadata = self._metadata(nasa_id, request.timeout_sec)
        selected_url = _select_rendition(asset_urls, media_type)
        if not selected_url:
            return None
        captions_url = _first_matching(asset_urls, {".srt", ".vtt", ".ttml"})
        preview = _preview_url(item)
        keywords = [str(value) for value in data.get("keywords", []) if str(value).strip()]
        description = str(data.get("description") or metadata.get("AVAIL:Description") or "")
        raw_metadata = {
            "nasa_id": nasa_id,
            "title": data.get("title", ""),
            "description": description,
            "keywords": keywords,
            "media_type": media_type,
            "date_created": data.get("date_created", ""),
            "center": data.get("center", ""),
            "creator": data.get("photographer") or data.get("creator") or data.get("secondary_creator") or "NASA",
            "location": data.get("location", ""),
            "metadata_url": f"{self.api_base}/metadata/{nasa_id}",
            "captions_url": captions_url,
            "available_renditions": asset_urls,
            "metadata": metadata,
            "use_context": "editorial/informational",
        }
        candidate = AssetCandidate(
            asset_id=f"nasa_images_{nasa_id}",
            provider=self.name,
            provider_asset_id=nasa_id,
            media_type=media_type,
            title=str(data.get("title") or nasa_id),
            description=description,
            tags=keywords,
            tags_source="provider" if keywords else "none",
            source_page_url=f"https://images.nasa.gov/details/{nasa_id}",
            preview_url=preview,
            download_url=selected_url,
            author_name=str(data.get("photographer") or data.get("creator") or data.get("secondary_creator") or "NASA"),
            search_query=request.query,
            project_id=request.project_id,
            scene_id=request.scene_id,
            license=AssetLicense(
                license_name="NASA Media Guidelines",
                license_url=NASA_POLICY_URL,
                provider_terms_url=NASA_POLICY_URL,
                rights_status="licensed",
                commercial_use_allowed=True,
                modification_allowed=True,
                attribution_required=True,
                attribution_text="Source: NASA",
                allowed_for_render=True,
                review_required=False,
                notes="NASA media policy metadata; do not imply NASA endorsement.",
            ),
            provenance=AssetProvenance(
                provider=self.name,
                provider_asset_id=nasa_id,
                source_page_url=f"https://images.nasa.gov/details/{nasa_id}",
                download_url=selected_url,
                original_filename=Path(selected_url.split("?", 1)[0]).name,
                project_id=request.project_id,
                scene_id=request.scene_id,
                search_query=request.query,
                metadata_snapshot=raw_metadata,
            ),
            raw_metadata=raw_metadata,
        )
        return candidate

    def _asset_urls(self, nasa_id: str, timeout_sec: float) -> list[str]:
        data = self.http.get_json(f"{self.api_base}/asset/{nasa_id}", timeout=timeout_sec)
        return [str(item.get("href") or "") for item in data.get("collection", {}).get("items", []) if item.get("href")]

    def _metadata(self, nasa_id: str, timeout_sec: float) -> dict[str, Any]:
        data = self.http.get_json(f"{self.api_base}/metadata/{nasa_id}", timeout=timeout_sec)
        return data if isinstance(data, dict) else {}


def _select_rendition(urls: list[str], media_type: str) -> str:
    candidates = [url for url in urls if _suffix(url) in (IMAGE_SUFFIXES if media_type == "image" else VIDEO_SUFFIXES)]
    candidates = [url for url in candidates if not _is_service_file(url)]
    candidates.sort(key=lambda url: _rendition_score(url, media_type), reverse=True)
    return candidates[0] if candidates else ""


def _rendition_score(url: str, media_type: str) -> tuple[int, int]:
    lower = url.lower()
    suffix = _suffix(url)
    if media_type == "video":
        format_score = {".mp4": 40, ".m4v": 35, ".mov": 20, ".webm": 15}.get(suffix, 0)
    else:
        format_score = {".jpg": 40, ".jpeg": 40, ".png": 35, ".webp": 25}.get(suffix, 0)
    quality = 30 if any(token in lower for token in ("~orig", "orig.", "original")) else 10
    if media_type == "video" and suffix == ".mov":
        quality -= 25
    return format_score, quality


def _is_service_file(url: str) -> bool:
    lower = url.lower()
    return any(token in lower for token in ("metadata.json", "collection.json", "manifest.json"))


def _first_matching(urls: list[str], suffixes: set[str]) -> str:
    return next((url for url in urls if _suffix(url) in suffixes), "")


def _preview_url(item: dict[str, Any]) -> str:
    for link in item.get("links", []) or []:
        if link.get("rel") == "preview" and link.get("href"):
            return str(link["href"])
    return ""


def _suffix(url: str) -> str:
    return Path(str(url).split("?", 1)[0]).suffix.lower()


def _tokens(value: str) -> list[str]:
    return [part.lower() for part in re.findall(r"[a-zA-Z0-9]+", value or "") if part]


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
VIDEO_SUFFIXES = {".mp4", ".m4v", ".mov", ".webm"}
