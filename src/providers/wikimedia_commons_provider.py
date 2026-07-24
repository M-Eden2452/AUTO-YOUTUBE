from __future__ import annotations

import html
import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import quote

from src.assets.download import download_candidate_asset
from src.assets.http_client import ProviderHttpClient
from src.assets.license_policy import apply_policy_to_candidate
from src.assets.models import AssetCandidate, AssetLicense, AssetProvenance, DownloadedAsset, ProviderCapabilities, orientation_from_dimensions
from src.assets.provider_contract import AssetPreview, AssetSearchRequest, DownloadContext, ProviderHealth


WIKIMEDIA_API_BASE = "https://commons.wikimedia.org/w/api.php"
WIKIMEDIA_REUSE_URL = "https://commons.wikimedia.org/wiki/Commons:Reusing_content_outside_Wikimedia"


class WikimediaCommonsStockProvider:
    name = "wikimedia"

    def __init__(
        self,
        *,
        api_base: str | None = None,
        user_agent: str | None = None,
        http: Any | None = None,
        max_results: int | None = None,
    ) -> None:
        self.api_base = api_base or os.getenv("WIKIMEDIA_API_BASE") or WIKIMEDIA_API_BASE
        self.user_agent = user_agent or os.getenv("WIKIMEDIA_USER_AGENT") or "AI-YouTube/0.3 WikimediaCommonsStockProvider"
        timeout = float(os.getenv("WIKIMEDIA_REQUEST_TIMEOUT") or 24)
        self.max_results = int(max_results or os.getenv("WIKIMEDIA_MAX_RESULTS") or 8)
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
            notes="MediaWiki Action API File namespace search with imageinfo/extmetadata.",
        )

    def search(self, request: AssetSearchRequest) -> list[AssetCandidate]:
        limit = min(max(1, request.max_results), self.max_results)
        search_data = self.http.get_json(
            self.api_base,
            params={
                "action": "query",
                "format": "json",
                "list": "search",
                "srnamespace": 6,
                "srsearch": request.query,
                "srlimit": limit,
            },
            timeout=request.timeout_sec,
        )
        pages = search_data.get("query", {}).get("search", [])
        titles = [str(page.get("title") or "") for page in pages if page.get("title")]
        if not titles:
            return []
        info = self.http.get_json(
            self.api_base,
            params={
                "action": "query",
                "format": "json",
                "prop": "imageinfo",
                "titles": "|".join(titles),
                "iiprop": "url|mime|size|extmetadata|commonmetadata|metadata|timestamp",
                "iiurlwidth": 720,
            },
            timeout=request.timeout_sec,
        )
        candidates: list[AssetCandidate] = []
        for page in (info.get("query", {}).get("pages") or {}).values():
            candidate = self._candidate_from_page(page, request)
            if not candidate:
                continue
            if candidate.media_type != request.media_type:
                continue
            if candidate.width and candidate.width < request.min_width:
                continue
            if candidate.height and candidate.height < request.min_height:
                continue
            apply_policy_to_candidate(candidate)
            candidates.append(candidate)
        return candidates[:limit]

    def get_preview(self, candidate: AssetCandidate) -> AssetPreview:
        return AssetPreview(
            candidate_id=candidate.asset_id,
            url=candidate.preview_url,
            width=candidate.width,
            height=candidate.height,
            media_type="image" if candidate.preview_url else candidate.media_type,
            duration_sec=0.0 if candidate.preview_url else candidate.duration_sec,
            rendition="wikimedia_thumb",
        )

    def resolve_license(self, candidate: AssetCandidate) -> AssetLicense:
        apply_policy_to_candidate(candidate)
        return candidate.license

    def download(self, candidate: AssetCandidate, destination: Path, context: DownloadContext) -> DownloadedAsset:
        self.resolve_license(candidate)
        return download_candidate_asset(candidate, destination, context, http=self.http)

    def health_check(self) -> ProviderHealth:
        return ProviderHealth(provider=self.name, configured=True, status="configured")

    def _candidate_from_page(self, page: dict[str, Any], request: AssetSearchRequest) -> AssetCandidate | None:
        imageinfo = (page.get("imageinfo") or [{}])[0]
        title = str(page.get("title") or "")
        if not title:
            return None
        mime = str(imageinfo.get("mime") or "").lower()
        media_type = "video" if mime.startswith("video/") else "image" if mime.startswith("image/") else ""
        if not media_type:
            return None
        ext = imageinfo.get("extmetadata") if isinstance(imageinfo.get("extmetadata"), dict) else {}
        page_id = str(page.get("pageid") or "")
        source_page = _file_page_url(title)
        width = int(imageinfo.get("width") or 0)
        height = int(imageinfo.get("height") or 0)
        license_name = _normalize_license_name(_ext(ext, "LicenseShortName"))
        license_url = _ext(ext, "LicenseUrl")
        author = _ext(ext, "Artist") or _ext(ext, "Author")
        credit = _ext(ext, "Credit")
        attribution = _ext(ext, "Attribution") or _build_attribution(author, license_name)
        categories = _categories(_ext(ext, "Categories"))
        description = _ext(ext, "ImageDescription") or _ext(ext, "ObjectName") or title.removeprefix("File:")
        raw_snapshot = {
            "page_id": page_id,
            "title": title,
            "mime": mime,
            "timestamp": imageinfo.get("timestamp", ""),
            "extmetadata": ext,
            "restriction_warnings": _restriction_warnings(ext),
        }
        candidate = AssetCandidate(
            asset_id=f"wikimedia_{page_id or _safe_id(title)}",
            provider=self.name,
            provider_asset_id=page_id or title,
            media_type=media_type,
            title=title.removeprefix("File:"),
            description=description,
            tags=categories + _tokens(request.query),
            source_page_url=source_page,
            preview_url=str(imageinfo.get("thumburl") or ""),
            download_url=str(imageinfo.get("url") or ""),
            author_name=author or credit,
            width=width,
            height=height,
            duration_sec=float(imageinfo.get("duration") or _ext(ext, "Duration") or 0),
            orientation=orientation_from_dimensions(width, height),
            search_query=request.query,
            project_id=request.project_id,
            scene_id=request.scene_id,
            license=AssetLicense(
                license_name=license_name or "unknown",
                license_url=license_url,
                provider_terms_url=WIKIMEDIA_REUSE_URL,
                rights_status="creative_commons" if "CC" in license_name else "public_domain" if "Public" in license_name else "licensed",
                commercial_use_allowed=True,
                modification_allowed=True,
                attribution_required=bool(attribution),
                attribution_text=attribution,
                allowed_for_render=True,
                review_required=False,
                notes=str(_ext(ext, "UsageTerms") or ""),
            ),
            provenance=AssetProvenance(
                provider=self.name,
                provider_asset_id=page_id or title,
                source_page_url=source_page,
                download_url=str(imageinfo.get("url") or ""),
                original_filename=Path(str(imageinfo.get("url") or title)).name,
                project_id=request.project_id,
                scene_id=request.scene_id,
                search_query=request.query,
                metadata_snapshot=raw_snapshot,
            ),
            raw_metadata=raw_snapshot,
        )
        return candidate


def _file_page_url(title: str) -> str:
    normalized = title.replace(" ", "_")
    return "https://commons.wikimedia.org/wiki/" + quote(normalized, safe=":/_")


def _ext(extmetadata: dict[str, Any], key: str) -> str:
    value = extmetadata.get(key)
    if isinstance(value, dict):
        value = value.get("value")
    return _clean_text(value)


def _clean_text(value: Any) -> str:
    text = html.unescape(str(value or ""))
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _normalize_license_name(value: str) -> str:
    raw = value.strip()
    lower = raw.lower().replace("-", " ")
    if "cc0" in lower:
        return "CC0"
    match = re.search(r"cc\s*by\s*sa\s*([0-9.]+)", lower)
    if match:
        return f"CC BY-SA {match.group(1)}"
    match = re.search(r"cc\s*by\s*([0-9.]+)", lower)
    if match:
        return f"CC BY {match.group(1)}"
    if "public domain" in lower or lower == "pd":
        return "Public domain"
    return raw or "unknown"


def _build_attribution(author: str, license_name: str) -> str:
    if author and license_name and license_name.lower() not in {"cc0", "public domain"}:
        return f"{author}, {license_name}"
    return author


def _categories(value: str) -> list[str]:
    return [item.strip() for item in re.split(r"[|,]", value or "") if item.strip()]


def _restriction_warnings(extmetadata: dict[str, Any]) -> list[str]:
    values = []
    for key in ("Restrictions", "Permission", "NonFree", "Trademarked"):
        text = _ext(extmetadata, key)
        if text:
            values.append(text)
    return values


def _tokens(value: str) -> list[str]:
    return [part.lower() for part in re.findall(r"[a-zA-Z0-9]+", value or "") if part]


def _safe_id(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", value).strip("_")[:80]
