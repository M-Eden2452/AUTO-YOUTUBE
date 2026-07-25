"""Turn the material a renderer actually used into an EvidenceRecord.

Why this exists
---------------
Two rights vocabularies already exist in this repository and both are correct in
their own layer: ``src.assets.models`` (AssetCandidate / AssetLicense /
AssetProvenance - what a provider told us) and
``src.project_foundation.models.EvidenceRecord`` (what a project stores as proof).
Until now nothing connected them, so the one template that renders a user's own
file - Story Card - produced a finished video with an empty rights report.

This module is that connection and nothing more. It does not download, search,
call a provider, touch the network, or modify the source file. It reads the file
that was really handed to the renderer, computes its checksum, and describes it
using the models that already exist.

Two honest outcomes
-------------------
- **A provider asset** (AssetCandidate/DownloadedAsset, or its ``to_dict()``):
  everything the provider and the licence policy recorded is carried across,
  including the raw ``provenance`` and ``technical_validation`` blocks, and the
  verification status is decided by the same
  ``src.projects.rights.classify_rights`` the unified report uses - never a second
  copy of that rule.
- **A local file the user pointed at**: recorded as ``user_supplied`` with no
  licence, no source and no commercial-use claim. It can still be rendered - that
  is the user's call - but it is never reported as ``verified``. A file existing
  on disk is not permission to publish it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.project_foundation.models import (
    EVIDENCE_RECORD_SCHEMA_VERSION,
    MEDIA_ROLE_VISUAL,
    PROVIDER_USER_SUPPLIED,
    SOURCE_TYPE_PROVIDER,
    SOURCE_TYPE_USER_SUPPLIED,
    VERIFICATION_REVIEW_REQUIRED,
    EvidenceRecord,
    utc_now_iso,
)

VIDEO_SUFFIXES = {".mp4", ".mov", ".m4v", ".mkv", ".webm", ".avi"}
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tif", ".tiff"}


class AssetEvidenceError(ValueError):
    """Raised when evidence cannot be recorded for a material (e.g. the file is gone)."""


def media_type_for_path(path: str | Path) -> str:
    suffix = Path(path).suffix.lower()
    if suffix in VIDEO_SUFFIXES:
        return "video"
    if suffix in IMAGE_SUFFIXES:
        return "image"
    return ""


def _as_dict(asset: Any) -> dict[str, Any]:
    """Accept an AssetCandidate/DownloadedAsset, its dict form, or nothing."""
    if asset is None:
        return {}
    if isinstance(asset, dict):
        return dict(asset)
    to_dict = getattr(asset, "to_dict", None)
    if callable(to_dict):
        result = to_dict()
        if isinstance(result, dict):
            return dict(result)
    raise AssetEvidenceError(
        f"asset must be an AssetCandidate/DownloadedAsset, a dict, or None - got {type(asset).__name__}."
    )


def _block(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    return dict(value) if isinstance(value, dict) else {}


def _technical_validation(path: Path, media_type: str) -> dict[str, Any]:
    """Best-effort local probe through the existing validator.

    Never raises: a material we cannot probe is still a material we must record.
    ffprobe/Pillow only - no network.
    """
    facts: dict[str, Any] = {"size_bytes": path.stat().st_size}
    if media_type not in {"video", "image"}:
        facts["status"] = "skipped"
        facts["reason"] = f"unsupported_media_type:{Path(path).suffix.lower() or 'none'}"
        return facts
    try:
        from src.assets.download import validate_local_asset

        facts.update(validate_local_asset(path, media_type))
    except Exception as exc:  # ProviderValidationError, missing ffprobe, corrupt file
        facts["status"] = "failed"
        facts["error"] = str(exc)
    return facts


def build_asset_evidence_record(
    *,
    evidence_id: str,
    local_path: str | Path,
    asset: Any = None,
    media_role: str = MEDIA_ROLE_VISUAL,
    acquired_at: str = "",
    notes: str = "",
) -> EvidenceRecord:
    """Describe the file at ``local_path`` as evidence.

    ``local_path`` must be the file the renderer is really given: the checksum is
    always computed from it, so a candidate that was swapped out before the render
    can never end up misdescribing the final material.
    """
    path = Path(local_path)
    if not str(local_path).strip():
        raise AssetEvidenceError("local_path is required to record evidence.")
    if not path.is_file():
        raise AssetEvidenceError(
            f"Cannot record evidence: {path} does not exist or is not a file. "
            "Evidence must describe the material that was actually used."
        )

    from src.assets.download import sha256_file
    from src.projects.rights import classify_rights

    data = _as_dict(asset)
    license_block = _block(data, "license")
    provenance_block = _block(data, "provenance")

    checksum = sha256_file(path)
    media_type = str(data.get("media_type") or "") or media_type_for_path(path)
    warnings: list[str] = []

    declared_checksum = str(data.get("checksum_sha256") or provenance_block.get("checksum_sha256") or "")
    if declared_checksum and declared_checksum.lower() != checksum.lower():
        # The asset record and the file on disk disagree. The file wins - it is what
        # the viewer will see - but the disagreement is recorded, never hidden.
        warnings.append(
            f"checksum of the rendered file ({checksum[:12]}...) does not match the one recorded "
            f"for the asset ({declared_checksum[:12]}...); the rendered file's checksum is stored."
        )

    if not data:
        # A file from the user's own disk. Everything about its rights is unknown,
        # and unknown is what gets written down.
        record = EvidenceRecord(
            evidence_id=evidence_id,
            asset_id="",
            source_url="",
            provider=PROVIDER_USER_SUPPLIED,
            author="",
            license_name="",
            license_url="",
            commercial_use_status="unknown",
            attribution_required=False,
            attribution_text="",
            acquired_at=acquired_at or utc_now_iso(),
            checksum_sha256=checksum,
            local_path=str(path.resolve()),
            original_filename=path.name,
            notes=_join_notes(
                notes,
                "Локальный файл пользователя. Права не проверялись и не подтверждены: "
                "перед публикацией убедитесь, что у вас есть право на коммерческое использование.",
                *warnings,
            ),
            verification_status=VERIFICATION_REVIEW_REQUIRED,
            media_role=media_role,
            media_type=media_type,
            source_type=SOURCE_TYPE_USER_SUPPLIED,
            allowed_for_render=False,
            review_required=True,
            provenance={},
            technical_validation=_technical_validation(path, media_type),
            schema_version=EVIDENCE_RECORD_SCHEMA_VERSION,
        )
        return record

    source_page = str(
        data.get("source_page_url") or provenance_block.get("source_page_url") or data.get("source_url") or ""
    )
    license_name = str(license_block.get("license_name") or data.get("license_name") or "")
    allowed = license_block.get("allowed_for_render")
    review = license_block.get("review_required")
    commercial = license_block.get("commercial_use_allowed")

    status = classify_rights(
        allowed_for_render=allowed if isinstance(allowed, bool) else None,
        review_required=review if isinstance(review, bool) else None,
        license_name=license_name,
        source_url=source_page,
        checksum=checksum,
    )

    technical = _block(data, "technical_validation") or _technical_validation(path, media_type)

    return EvidenceRecord(
        evidence_id=evidence_id,
        asset_id=str(data.get("asset_id") or ""),
        source_url=source_page,
        provider=str(data.get("provider") or provenance_block.get("provider") or ""),
        author=str(data.get("author_name") or data.get("author") or ""),
        license_name=license_name,
        license_url=str(license_block.get("license_url") or data.get("license_url") or ""),
        commercial_use_status=(
            "allowed" if commercial is True else "not_allowed" if commercial is False else "unknown"
        ),
        attribution_required=bool(license_block.get("attribution_required", False)),
        attribution_text=str(license_block.get("attribution_text") or ""),
        acquired_at=acquired_at
        or str(data.get("downloaded_at") or provenance_block.get("downloaded_at") or "")
        or utc_now_iso(),
        checksum_sha256=checksum,
        local_path=str(path.resolve()),
        original_filename=str(data.get("original_filename") or provenance_block.get("original_filename") or path.name),
        notes=_join_notes(notes, *warnings),
        verification_status=status,
        media_role=media_role,
        media_type=media_type,
        source_type=SOURCE_TYPE_PROVIDER,
        provider_asset_id=str(data.get("provider_asset_id") or provenance_block.get("provider_asset_id") or ""),
        download_url=str(data.get("download_url") or provenance_block.get("download_url") or ""),
        author_url=str(data.get("author_url") or ""),
        allowed_for_render=allowed is True,
        review_required=review is True,
        # Kept verbatim so nothing the provider layer recorded is lost in translation.
        provenance=provenance_block,
        technical_validation=technical,
        schema_version=EVIDENCE_RECORD_SCHEMA_VERSION,
    )


def _join_notes(*parts: str) -> str:
    return " ".join(part.strip() for part in parts if part and part.strip())


__all__ = [
    "AssetEvidenceError",
    "build_asset_evidence_record",
    "media_type_for_path",
]
