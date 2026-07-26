from __future__ import annotations

from pathlib import Path
from typing import Any

from src.assets.download import sha256_file, validate_local_asset
from src.assets.license_policy import apply_policy_to_candidate
from src.assets.models import AssetCandidate, DownloadedAsset, ProviderCapabilities, utc_now_iso
from src.assets.provider_contract import (
    AssetPreview,
    AssetSearchRequest,
    DownloadContext,
    ProviderHealth,
    ProviderNoResultsError,
    ProviderValidationError,
    ensure_license_allows_render,
)
from src.media_library import load_media_index


class LocalLibraryStockProvider:
    name = "local_library"

    def __init__(self, *, index: dict[str, Any] | None = None, index_path: str | Path | None = None) -> None:
        self.index = index if index is not None else load_media_index(index_path or "assets/library/metadata/media_index.json")

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            provider=self.name,
            media_types=["video", "image", "music"],
            supports_search=True,
            supports_preview=True,
            supports_download=True,
            supports_license_metadata=True,
            # Searched against this project's own records, which are written in the
            # project's language rather than in English.
            query_languages=["en", "ru"],
            notes="Uses current schema-safe local records only; legacy records require review.",
        )

    def search(self, request: AssetSearchRequest) -> list[AssetCandidate]:
        query_tokens = _tokens(request.query)
        candidates = []
        for item in self.index.get("items", []):
            if not _is_current_safe_record(item):
                continue
            if (item.get("type") or item.get("media_type")) != request.media_type:
                continue
            local_path = Path(str(item.get("local_path") or item.get("path") or ""))
            if not local_path.exists():
                continue
            item_tokens = _tokens(
                " ".join(
                    [
                        str(item.get("title", "")),
                        str(item.get("description", "")),
                        " ".join(str(value) for value in item.get("keywords", [])),
                        " ".join(str(value) for value in item.get("tags", [])),
                    ]
                )
            )
            if query_tokens and not (query_tokens & item_tokens):
                continue
            candidate = AssetCandidate.from_dict(
                {
                    **item,
                    "asset_id": item.get("id") or item.get("asset_id"),
                    "provider": item.get("provider") or self.name,
                    "media_type": item.get("type") or item.get("media_type"),
                    "search_query": request.query,
                    "project_id": request.project_id,
                    "scene_id": request.scene_id,
                }
            )
            candidate.provider = self.name
            if not candidate.provider_asset_id:
                candidate.provider_asset_id = str(item.get("provider_asset_id") or item.get("id") or candidate.asset_id)
            candidate.search_query = request.query
            apply_policy_to_candidate(candidate)
            if candidate.license.review_required or not candidate.license.allowed_for_render:
                continue
            candidates.append(candidate)
        candidates.sort(key=lambda candidate: (candidate.height > candidate.width, candidate.width * candidate.height), reverse=True)
        if not candidates:
            raise ProviderNoResultsError("No safe local library assets matched.", provider=self.name, query=request.query)
        return candidates[: request.max_results]

    def get_preview(self, candidate: AssetCandidate) -> AssetPreview:
        return AssetPreview(
            candidate_id=candidate.asset_id,
            local_path=candidate.preview_url or candidate.local_path,
            width=candidate.width,
            height=candidate.height,
            media_type=candidate.media_type,
            duration_sec=candidate.duration_sec,
            rendition="local_library_file",
            fallback_reason="existing_local_file",
        )

    def resolve_license(self, candidate: AssetCandidate):
        apply_policy_to_candidate(candidate)
        return candidate.license

    def download(self, candidate: AssetCandidate, destination: Path, context: DownloadContext) -> DownloadedAsset:
        ensure_license_allows_render(candidate)
        local_path = Path(candidate.local_path)
        if not local_path.exists():
            raise ProviderValidationError(f"Local library file is missing: {local_path}", provider=self.name, query=candidate.search_query)
        checksum = candidate.checksum_sha256 or sha256_file(local_path)
        validation = candidate.technical_validation if candidate.technical_validation.get("status") == "passed" else validate_local_asset(local_path, candidate.media_type)
        candidate.project_id = candidate.project_id or context.project_id
        candidate.scene_id = candidate.scene_id or context.scene_id
        candidate.provenance.project_id = candidate.project_id
        candidate.provenance.scene_id = candidate.scene_id
        candidate.provenance.checksum_sha256 = checksum
        candidate.provenance.downloaded_at = candidate.provenance.downloaded_at or utc_now_iso()
        return DownloadedAsset.from_candidate(
            candidate,
            local_path=str(local_path),
            checksum_sha256=checksum,
            downloaded_at=candidate.provenance.downloaded_at,
            technical_validation=validation,
        )

    def health_check(self) -> ProviderHealth:
        return ProviderHealth(provider=self.name, configured=True, status="ready")


def _is_current_safe_record(item: dict[str, Any]) -> bool:
    return (
        int(item.get("schema_version") or 0) >= 1
        and bool(item.get("allowed_for_render"))
        and not bool(item.get("review_required"))
        and isinstance(item.get("license"), dict)
        and isinstance(item.get("provenance"), dict)
    )


def _tokens(value: str) -> set[str]:
    return {part.lower() for part in str(value or "").replace(",", " ").split() if part.strip()}
