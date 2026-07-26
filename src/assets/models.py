from __future__ import annotations

import dataclasses
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ASSET_SCHEMA_VERSION = 1
RIGHTS_ALLOWED_STATUSES = {"user_owned", "licensed", "creative_commons", "public_domain"}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def asdict_clean(value: Any) -> Any:
    if dataclasses.is_dataclass(value):
        return {key: asdict_clean(item) for key, item in dataclasses.asdict(value).items()}
    if isinstance(value, dict):
        return {key: asdict_clean(item) for key, item in value.items()}
    if isinstance(value, list):
        return [asdict_clean(item) for item in value]
    return value


def orientation_from_dimensions(width: int, height: int) -> str:
    if not width or not height:
        return "unknown"
    if height > width:
        return "vertical"
    if width > height:
        return "horizontal"
    return "square"


def stable_asset_id(*parts: Any) -> str:
    raw = "|".join(str(part or "") for part in parts)
    return "asset_" + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


@dataclass
class AssetLicense:
    license_name: str = "unknown"
    license_url: str = ""
    provider_terms_url: str = ""
    rights_status: str = "legacy_unknown"
    commercial_use_allowed: bool = False
    modification_allowed: bool = False
    attribution_required: bool = True
    attribution_text: str = ""
    allowed_for_render: bool = False
    review_required: bool = True
    notes: str = ""
    checked_at: str = field(default_factory=utc_now_iso)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "AssetLicense":
        if not isinstance(data, dict):
            return cls()
        values = {field.name: data.get(field.name) for field in dataclasses.fields(cls) if field.name in data}
        license_name = data.get("license_name") or data.get("license") or data.get("license_note")
        if license_name and "license_name" not in values:
            values["license_name"] = str(license_name)
        rights_status = data.get("rights_status")
        if rights_status and "rights_status" not in values:
            values["rights_status"] = str(rights_status)
        if "allowed_for_render" not in values and rights_status:
            values["allowed_for_render"] = rights_status in RIGHTS_ALLOWED_STATUSES
        if "review_required" not in values:
            values["review_required"] = not bool(values.get("allowed_for_render", False))
        return cls(**values)

    @classmethod
    def from_legacy(cls, data: dict[str, Any]) -> "AssetLicense":
        rights_status = str(data.get("rights_status") or "legacy_unknown")
        allowed = bool(data.get("allowed_for_render", rights_status in RIGHTS_ALLOWED_STATUSES))
        review_required = bool(data.get("review_required", not allowed))
        return cls(
            license_name=str(data.get("license") or data.get("license_note") or "unknown"),
            license_url=str(data.get("license_url") or ""),
            provider_terms_url=str(data.get("provider_terms_url") or ""),
            rights_status=rights_status,
            commercial_use_allowed=bool(data.get("commercial_use_allowed", allowed)),
            modification_allowed=bool(data.get("modification_allowed", allowed)),
            attribution_required=bool(data.get("attribution_required", data.get("credit_required", False))),
            attribution_text=str(data.get("attribution_text") or data.get("attribution") or ""),
            allowed_for_render=allowed,
            review_required=review_required,
            notes=str(data.get("license_notes") or data.get("license_note") or ""),
            checked_at=str(data.get("checked_at") or utc_now_iso()),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict_clean(self)


@dataclass
class AssetProvenance:
    provider: str = ""
    provider_asset_id: str = ""
    source_page_url: str = ""
    download_url: str = ""
    original_filename: str = ""
    downloaded_at: str = ""
    checksum_sha256: str = ""
    project_id: str = ""
    scene_id: str = ""
    search_query: str = ""
    metadata_snapshot: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "AssetProvenance":
        if not isinstance(data, dict):
            return cls()
        values = {field.name: data.get(field.name) for field in dataclasses.fields(cls) if field.name in data}
        return cls(**values)

    @classmethod
    def from_legacy(cls, data: dict[str, Any]) -> "AssetProvenance":
        return cls(
            provider=str(data.get("provider") or ""),
            provider_asset_id=str(data.get("provider_asset_id") or data.get("source_id") or data.get("id") or ""),
            source_page_url=str(data.get("source_page_url") or data.get("source_page") or data.get("source_url") or ""),
            download_url=str(data.get("download_url") or data.get("direct_download_url") or ""),
            original_filename=str(data.get("original_filename") or Path(str(data.get("path") or data.get("local_path") or "")).name),
            downloaded_at=str(data.get("downloaded_at") or ""),
            checksum_sha256=str(data.get("checksum_sha256") or ""),
            project_id=str(data.get("project_id") or ""),
            scene_id=str(data.get("scene_id") or data.get("scene_assignment") or ""),
            search_query=str(data.get("search_query") or data.get("query") or data.get("original_query") or ""),
            metadata_snapshot=dict(data.get("raw_metadata") or data.get("metadata_snapshot") or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict_clean(self)


@dataclass
class ProviderCapabilities:
    provider: str
    media_types: list[str] = field(default_factory=lambda: ["video", "image"])
    supports_search: bool = True
    supports_preview: bool = True
    supports_download: bool = True
    supports_license_metadata: bool = True
    supports_orientation_filter: bool = False
    supports_pagination: bool = False
    max_results: int = 20
    # Languages this provider's index can actually be searched in. English-only is the
    # honest default: none of the registered providers documents reliable retrieval for
    # a Russian query, and posting one anyway is what returned 0 results from Wikimedia
    # and NASA across the whole confirmed run.
    query_languages: list[str] = field(default_factory=lambda: ["en"])
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict_clean(self)


@dataclass
class AssetCandidate:
    asset_id: str
    provider: str
    provider_asset_id: str = ""
    media_type: str = "video"
    title: str = ""
    description: str = ""
    tags: list[str] = field(default_factory=list)
    # Where ``tags`` came from. "provider" means the API labelled the asset;
    # "query_derived" means the adapter had nothing and echoed the search string back.
    # Only the first kind is evidence that a result matches what was asked for - see
    # src.assets.semantic_selection.candidate_ranker.
    tags_source: str = "provider"
    source_page_url: str = ""
    preview_url: str = ""
    download_url: str = ""
    author_name: str = ""
    author_url: str = ""
    width: int = 0
    height: int = 0
    duration_sec: float = 0.0
    orientation: str = "unknown"
    search_query: str = ""
    local_path: str = ""
    original_filename: str = ""
    downloaded_at: str = ""
    checksum_sha256: str = ""
    project_id: str = ""
    scene_id: str = ""
    license: AssetLicense = field(default_factory=AssetLicense)
    provenance: AssetProvenance = field(default_factory=AssetProvenance)
    raw_metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: int = ASSET_SCHEMA_VERSION
    technical_validation: dict[str, Any] = field(default_factory=dict)
    crop_suitability_score: float = 0.0
    policy_decision: dict[str, Any] = field(default_factory=dict)
    rights_declaration: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AssetCandidate":
        version = int(data.get("schema_version") or 0)
        media_type = str(data.get("media_type") or data.get("type") or "video")
        width = int(data.get("width") or 0)
        height = int(data.get("height") or 0)
        license_data = data.get("license") if isinstance(data.get("license"), dict) else None
        license_obj = AssetLicense.from_dict(license_data) if license_data else AssetLicense.from_legacy(data)
        provenance_data = data.get("provenance") if isinstance(data.get("provenance"), dict) else None
        provenance = AssetProvenance.from_dict(provenance_data) if provenance_data else AssetProvenance.from_legacy(data)
        local_path = str(data.get("local_path") or data.get("path") or data.get("downloaded_path") or "")
        asset_id = str(data.get("asset_id") or data.get("id") or stable_asset_id(data.get("provider"), data.get("source_url"), local_path))
        return cls(
            asset_id=asset_id,
            provider=str(data.get("provider") or ""),
            provider_asset_id=str(data.get("provider_asset_id") or data.get("source_id") or provenance.provider_asset_id),
            media_type=media_type,
            title=str(data.get("title") or ""),
            description=str(data.get("description") or data.get("caption") or ""),
            tags=_as_list(data.get("tags") or data.get("keywords")),
            tags_source=str(data.get("tags_source") or "provider"),
            source_page_url=str(data.get("source_page_url") or data.get("source_page") or data.get("source_url") or ""),
            preview_url=str(data.get("preview_url") or data.get("thumbnail_url") or ""),
            download_url=str(data.get("download_url") or data.get("direct_download_url") or ""),
            author_name=str(data.get("author_name") or data.get("author") or ""),
            author_url=str(data.get("author_url") or ""),
            width=width,
            height=height,
            duration_sec=float(data.get("duration_sec") or data.get("duration") or 0),
            orientation=str(data.get("orientation") or orientation_from_dimensions(width, height)),
            search_query=str(data.get("search_query") or data.get("query") or data.get("original_query") or ""),
            local_path=local_path,
            original_filename=str(data.get("original_filename") or Path(local_path).name),
            downloaded_at=str(data.get("downloaded_at") or ""),
            checksum_sha256=str(data.get("checksum_sha256") or ""),
            project_id=str(data.get("project_id") or provenance.project_id),
            scene_id=str(data.get("scene_id") or data.get("scene_assignment") or provenance.scene_id),
            license=license_obj,
            provenance=provenance,
            raw_metadata=dict(data.get("raw_metadata") or {}),
            schema_version=version,
            technical_validation=dict(data.get("technical_validation") or {}),
            crop_suitability_score=float(data.get("crop_suitability_score") or data.get("vertical_score") or 0),
            policy_decision=dict(data.get("policy_decision") or {}),
            rights_declaration=dict(data.get("rights_declaration") or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict_clean(
            {
                "schema_version": self.schema_version if self.schema_version is not None else ASSET_SCHEMA_VERSION,
                "asset_id": self.asset_id,
                "provider": self.provider,
                "provider_asset_id": self.provider_asset_id,
                "media_type": self.media_type,
                "title": self.title,
                "description": self.description,
                "tags": self.tags,
                "tags_source": self.tags_source,
                "source_page_url": self.source_page_url,
                "preview_url": self.preview_url,
                "download_url": self.download_url,
                "author_name": self.author_name,
                "author_url": self.author_url,
                "width": self.width,
                "height": self.height,
                "duration_sec": self.duration_sec,
                "orientation": self.orientation or orientation_from_dimensions(self.width, self.height),
                "search_query": self.search_query,
                "local_path": self.local_path,
                "original_filename": self.original_filename,
                "downloaded_at": self.downloaded_at,
                "checksum_sha256": self.checksum_sha256,
                "project_id": self.project_id,
                "scene_id": self.scene_id,
                "license": self.license.to_dict(),
                "provenance": self.provenance.to_dict(),
                "raw_metadata": self.raw_metadata,
                "technical_validation": self.technical_validation,
                "crop_suitability_score": self.crop_suitability_score,
                "policy_decision": self.policy_decision,
                "rights_declaration": self.rights_declaration,
            }
        )

    def to_manifest_dict(self) -> dict[str, Any]:
        data = self.to_dict()
        local_path = self.local_path
        data.update(
            {
                "type": self.media_type,
                "path": local_path,
                "downloaded_path": local_path,
                "source_url": self.source_page_url,
                "source_page": self.source_page_url,
                "author": self.author_name,
                "license_name": self.license.license_name,
                "rights_status": self.license.rights_status,
                "allowed_for_render": self.license.allowed_for_render,
                "review_required": self.license.review_required,
                "policy_decision": self.policy_decision,
                "rights_declaration": self.rights_declaration,
                "duration": self.duration_sec,
                "download_status": "downloaded" if local_path and self.checksum_sha256 else ("local" if local_path else "not_downloaded"),
            }
        )
        return data


@dataclass
class DownloadedAsset(AssetCandidate):
    @classmethod
    def from_candidate(
        cls,
        candidate: AssetCandidate,
        *,
        local_path: str,
        checksum_sha256: str,
        downloaded_at: str,
        technical_validation: dict[str, Any],
    ) -> "DownloadedAsset":
        data = candidate.to_dict()
        data.update(
            {
                "local_path": local_path,
                "checksum_sha256": checksum_sha256,
                "downloaded_at": downloaded_at,
                "technical_validation": technical_validation,
            }
        )
        provenance = AssetProvenance.from_dict(data.get("provenance"))
        provenance.downloaded_at = downloaded_at
        provenance.checksum_sha256 = checksum_sha256
        provenance.original_filename = provenance.original_filename or Path(local_path).name
        data["provenance"] = provenance.to_dict()
        loaded = AssetCandidate.from_dict(data)
        values = {field.name: getattr(loaded, field.name) for field in dataclasses.fields(AssetCandidate)}
        return cls(**values)


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, tuple | set):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and "," in value:
        return [item.strip() for item in value.split(",") if item.strip()]
    return [str(value).strip()] if str(value).strip() else []
