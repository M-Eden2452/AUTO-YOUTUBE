from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import quote

from src.assets.download import download_candidate_asset
from src.assets.http_client import ProviderHttpClient
from src.assets.license_policy import apply_policy_to_candidate
from src.assets.models import AssetCandidate, AssetLicense, AssetProvenance, DownloadedAsset, ProviderCapabilities
from src.assets.provider_contract import AssetPreview, AssetSearchRequest, DownloadContext, ProviderHealth, ProviderInvalidResponseError


IA_SEARCH_BASE = "https://archive.org/advancedsearch.php"
IA_METADATA_BASE = "https://archive.org/metadata"
IA_DOWNLOAD_BASE = "https://archive.org/download"
IA_RIGHTS_URL = "https://help.archive.org/help/rights/"


class InternetArchiveStockProvider:
    name = "internet_archive"

    def __init__(
        self,
        *,
        search_base: str | None = None,
        metadata_base: str | None = None,
        download_base: str | None = None,
        user_agent: str | None = None,
        http: Any | None = None,
        max_results: int | None = None,
    ) -> None:
        self.search_base = search_base or os.getenv("INTERNET_ARCHIVE_SEARCH_BASE") or IA_SEARCH_BASE
        self.metadata_base = (metadata_base or os.getenv("INTERNET_ARCHIVE_METADATA_BASE") or IA_METADATA_BASE).rstrip("/")
        self.download_base = (download_base or os.getenv("INTERNET_ARCHIVE_DOWNLOAD_BASE") or IA_DOWNLOAD_BASE).rstrip("/")
        self.user_agent = user_agent or os.getenv("INTERNET_ARCHIVE_USER_AGENT") or "AI-YouTube/0.3 InternetArchiveStockProvider"
        timeout = float(os.getenv("INTERNET_ARCHIVE_REQUEST_TIMEOUT") or 24)
        self.max_results = int(max_results or os.getenv("INTERNET_ARCHIVE_MAX_RESULTS") or 8)
        self.http = http or ProviderHttpClient(user_agent=self.user_agent, timeout=timeout)

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            provider=self.name,
            media_types=["image", "video"],
            supports_search=True,
            supports_preview=True,
            supports_download=True,
            supports_license_metadata=True,
            supports_pagination=True,
            max_results=self.max_results,
            notes="Internet Archive Advanced Search plus selected item metadata file resolution.",
        )

    def search(self, request: AssetSearchRequest) -> list[AssetCandidate]:
        mediatype = "movies" if request.media_type == "video" else "image"
        data = self.http.get_json(
            self.search_base,
            params={
                "q": f"({request.query}) AND mediatype:{mediatype}",
                "fl[]": [
                    "identifier",
                    "title",
                    "description",
                    "creator",
                    "collection",
                    "mediatype",
                    "date",
                    "year",
                    "subject",
                    "licenseurl",
                    "rights",
                    "publicdate",
                    "downloads",
                ],
                "rows": min(request.max_results, self.max_results),
                "page": 1,
                "output": "json",
            },
            timeout=request.timeout_sec,
        )
        docs = data.get("response", {}).get("docs", [])
        candidates = [self._candidate_from_doc(doc, request) for doc in docs]
        return [candidate for candidate in candidates if candidate is not None]

    def resolve_candidate_file(self, candidate: AssetCandidate) -> dict[str, Any]:
        metadata = self.http.get_json(f"{self.metadata_base}/{candidate.provider_asset_id}")
        files = metadata.get("files")
        if not isinstance(files, list):
            raise ProviderInvalidResponseError("Internet Archive metadata has no files list.", provider=self.name)
        selected = _select_file(files, candidate.media_type)
        if not selected:
            raise ProviderInvalidResponseError("Internet Archive item has no suitable media file.", provider=self.name)
        filename = str(selected.get("name") or "")
        candidate.download_url = f"{self.download_base}/{quote(candidate.provider_asset_id)}/{quote(filename)}"
        candidate.original_filename = filename
        candidate.provenance.download_url = candidate.download_url
        candidate.provenance.original_filename = filename
        snapshot = {
            **candidate.raw_metadata,
            "item_metadata": metadata.get("metadata", {}),
            "selected_file": selected,
            "files_count": len(files),
        }
        candidate.raw_metadata = snapshot
        candidate.provenance.metadata_snapshot = snapshot
        return selected

    def get_preview(self, candidate: AssetCandidate) -> AssetPreview:
        preview_url = candidate.preview_url or (f"https://archive.org/services/img/{candidate.provider_asset_id}" if candidate.provider_asset_id else "")
        return AssetPreview(
            candidate_id=candidate.asset_id,
            url=preview_url,
            width=candidate.width,
            height=candidate.height,
            media_type="image" if preview_url else candidate.media_type,
            duration_sec=0.0 if preview_url else candidate.duration_sec,
            rendition="internet_archive_thumbnail",
            fallback_reason="internet_archive_services_thumbnail" if preview_url and not candidate.preview_url else "",
        )

    def resolve_license(self, candidate: AssetCandidate) -> AssetLicense:
        apply_policy_to_candidate(candidate)
        return candidate.license

    def download(self, candidate: AssetCandidate, destination: Path, context: DownloadContext) -> DownloadedAsset:
        if not candidate.download_url:
            self.resolve_candidate_file(candidate)
        self.resolve_license(candidate)
        return download_candidate_asset(candidate, destination, context, http=self.http)

    def health_check(self) -> ProviderHealth:
        return ProviderHealth(provider=self.name, configured=True, status="configured")

    def _candidate_from_doc(self, doc: dict[str, Any], request: AssetSearchRequest) -> AssetCandidate | None:
        identifier = str(doc.get("identifier") or "").strip()
        if not identifier:
            return None
        collection = doc.get("collection", [])
        subjects = _as_list(doc.get("subject"))
        license_url = str(doc.get("licenseurl") or "").strip()
        rights = str(doc.get("rights") or "").strip()
        license_name = _license_name(license_url, rights)
        raw_metadata = {
            "identifier": identifier,
            "collection": collection,
            "rights": rights,
            "licenseurl": license_url,
            "publicdate": doc.get("publicdate", ""),
            "downloads": doc.get("downloads", ""),
            "source_metadata": doc,
        }
        candidate = AssetCandidate(
            asset_id=f"internet_archive_{identifier}",
            provider=self.name,
            provider_asset_id=identifier,
            media_type=request.media_type,
            title=str(doc.get("title") or identifier),
            description=str(doc.get("description") or ""),
            tags=subjects,
            tags_source="provider" if subjects else "none",
            source_page_url=f"https://archive.org/details/{identifier}",
            author_name=_first_value(doc.get("creator")),
            search_query=request.query,
            project_id=request.project_id,
            scene_id=request.scene_id,
            license=AssetLicense(
                license_name=license_name,
                license_url=license_url,
                provider_terms_url=IA_RIGHTS_URL,
                rights_status="public_domain" if license_name in {"CC0", "Public Domain"} else "creative_commons" if license_name.startswith("CC BY") else "review_required",
                commercial_use_allowed=True,
                modification_allowed=True,
                attribution_required=True,
                attribution_text=_first_value(doc.get("creator")),
                allowed_for_render=True,
                review_required=False,
                notes=rights,
            ),
            provenance=AssetProvenance(
                provider=self.name,
                provider_asset_id=identifier,
                source_page_url=f"https://archive.org/details/{identifier}",
                project_id=request.project_id,
                scene_id=request.scene_id,
                search_query=request.query,
                metadata_snapshot=raw_metadata,
            ),
            raw_metadata=raw_metadata,
        )
        apply_policy_to_candidate(candidate)
        return candidate


def _select_file(files: list[dict[str, Any]], media_type: str) -> dict[str, Any] | None:
    usable = [item for item in files if _is_media_file(item, media_type)]
    usable.sort(key=lambda item: _file_score(item, media_type), reverse=True)
    return usable[0] if usable else None


def _is_media_file(file: dict[str, Any], media_type: str) -> bool:
    name = str(file.get("name") or "")
    suffix = Path(name).suffix.lower()
    lower = name.lower()
    if any(token in lower for token in SERVICE_FILE_TOKENS):
        return False
    if media_type == "video":
        return suffix in VIDEO_SUFFIXES or any(token in str(file.get("format") or "").lower() for token in ("h.264", "mpeg4", "mpeg", "webm", "ogg video"))
    return suffix in IMAGE_SUFFIXES


def _file_score(file: dict[str, Any], media_type: str) -> tuple[int, int, int]:
    name = str(file.get("name") or "")
    suffix = Path(name).suffix.lower()
    fmt = str(file.get("format") or "").lower()
    size = _int(file.get("size"))
    if media_type == "video":
        format_score = 100 if suffix == ".mp4" or "h.264" in fmt else 80 if "mpeg4" in fmt else 45 if suffix in {".webm", ".ogv"} else 30
        huge_penalty = -80 if size > 2_500_000_000 else 0
        derivative_score = 20 if any(token in name.lower() for token in ("derivative", "h264", "512kb", "small")) else 0
        return format_score + huge_penalty + derivative_score, min(size, 500_000_000), -size
    format_score = 100 if suffix in {".jpg", ".jpeg"} else 80 if suffix == ".png" else 40
    return format_score, min(size, 200_000_000), -size


def _license_name(license_url: str, rights: str) -> str:
    text = f"{license_url} {rights}".lower()
    if "publicdomain/zero" in text or "cc0" in text:
        return "CC0"
    if "publicdomain/mark" in text or "public domain" in text:
        return "Public Domain"
    match = re.search(r"licenses/by/([0-9.]+)", text)
    if match:
        return f"CC BY {match.group(1).rstrip('/')}"
    match = re.search(r"licenses/by-sa/([0-9.]+)", text)
    if match:
        return f"CC BY-SA {match.group(1).rstrip('/')}"
    if "all rights reserved" in text:
        return "All Rights Reserved"
    if "by-nc" in text:
        return "CC BY-NC"
    if "by-nd" in text:
        return "CC BY-ND"
    return rights or "unknown"


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    return [str(value)] if str(value).strip() else []


def _first_value(value: Any) -> str:
    values = _as_list(value)
    return values[0] if values else ""


def _tokens(value: str) -> list[str]:
    return [part.lower() for part in re.findall(r"[a-zA-Z0-9]+", value or "") if part]


def _int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


VIDEO_SUFFIXES = {".mp4", ".m4v", ".mov", ".mpeg", ".mpg", ".webm", ".ogv"}
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}
SERVICE_FILE_TOKENS = {
    "_meta.",
    "_files.",
    "_reviews.",
    "_thumb",
    ".torrent",
    ".xml",
    ".sqlite",
    ".json",
    "metadata",
    "manifest",
}
