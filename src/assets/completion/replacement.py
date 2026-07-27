"""Replace one visual slot without rerunning research, scripting, or asset search.

The replacement command is an explicit author action.  The supplied file is copied
into the project, technically validated, recorded as confirmed user-owned material,
and attached to exactly one existing :class:`VisualSlot`.  Derived render state is
then marked stale so a normal pipeline resume can rebuild it.

This module deliberately does not introduce another project repository.  Project kind
is detected through the read-only :class:`ProjectRepository`; the news project's own
``NewsJob`` and asset manifest remain the records that are updated.
"""

from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.assets.download import sha256_file, validate_local_asset
from src.assets.license_policy import evaluate_asset_policy
from src.assets.models import (
    ASSET_SCHEMA_VERSION,
    AssetCandidate,
    AssetLicense,
    AssetProvenance,
    orientation_from_dimensions,
    stable_asset_id,
)
from src.assets.provider_contract import ProviderValidationError
from src.assets.semantic_selection.decision import (
    DECISION_KEY,
    FRAMING_CROP_REVIEW,
    FRAMING_HARD_REJECT,
    RESOLVED,
    RESOLVED_NEEDS_REVIEW,
    SUPPORT_FULL,
    VERDICT_COMPLETE,
    SelectionDecision,
    framing_decision,
    read_decision,
)
from src.news.models import NEWS_TO_SHORT_STAGES, NewsJob, StageState, completion_settings, utc_now_iso
from src.news.project_store import NewsProjectStore
from src.projects.repository import PROJECT_KIND_NEWS_JOB, ProjectRepository

from .assembly import (
    ASSEMBLY_COMPOSITE,
    ASSEMBLY_EXACT,
    ASSEMBLY_FALLBACK,
    ASSEMBLY_PARTIAL,
    ASSEMBLY_UNRESOLVED,
    SceneVisualAssembly,
    VisualSlot,
    attach_assembly,
    read_assembly,
)
from .modes import (
    TIER_EMERGENCY,
    TIER_EXACT,
    TIER_GENERATED,
    evaluate_usability,
    normalize_mode,
)

REPLACEMENT_HISTORY_SCHEMA_VERSION = 1
STALE_STAGES = ("preview_render", "quality_check", "final_render", "export")
_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
_VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm", ".ogv", ".mpeg", ".mpg"}
_MANUAL_CROP_APPROVED = "manual_crop_approved"
_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


class VisualSlotReplacementError(ValueError):
    """An expected, user-actionable failure of a slot replacement."""

    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.code = code


def replace_visual_slot(
    *,
    projects_root: str | Path,
    project_id: str,
    scene_id: str,
    slot_id: str,
    source_file: str | Path,
    source_url: str = "",
    license_file: str | Path = "",
    confirm_user_owned: bool = False,
) -> dict[str, Any]:
    """Import ``source_file`` and replace only ``scene_id`` / ``slot_id``.

    The call is offline and deterministic.  It performs no provider search and no
    paid API operation.  A successful return means the asset manifest and job state
    are already durable; replacement-report regeneration is best-effort and any
    report error is returned as a warning.
    """

    project_id = str(project_id or "").strip()
    scene_id = str(scene_id or "").strip()
    slot_id = str(slot_id or "").strip()
    if not scene_id:
        raise VisualSlotReplacementError("A scene id is required.", code="scene_id_required")
    if not slot_id:
        raise VisualSlotReplacementError("A slot id is required.", code="slot_id_required")
    if not confirm_user_owned:
        raise VisualSlotReplacementError(
            "Replacing a renderable slot requires explicit confirmation that the user "
            "owns or controls the supplied media rights.",
            code="rights_confirmation_required",
        )

    repository = ProjectRepository(projects_root)
    root = _checked_project_root(repository, project_id)
    if repository.detect_kind(project_id) != PROJECT_KIND_NEWS_JOB:
        raise VisualSlotReplacementError(
            f"Project {project_id!r} is not a news_to_short project.",
            code="unsupported_project_kind",
        )

    store = NewsProjectStore(projects_root)
    job = _load_job(store, project_id)
    assets_path = root / "assets" / "assets_manifest.json"
    assets_manifest = _read_required_json(assets_path, label="assets manifest")
    scene_entry = _find_scene(assets_manifest, scene_id)
    assembly = read_assembly(
        scene_entry,
        scene_duration_sec=_float(scene_entry.get("required_duration_sec")),
    )
    slot = assembly.slot(slot_id)
    if slot is None:
        available = ", ".join(item.slot_id for item in assembly.slots) or "none"
        raise VisualSlotReplacementError(
            f"Visual slot {slot_id!r} was not found in scene {scene_id!r}; available slots: {available}.",
            code="slot_not_found",
        )

    source = _checked_source_file(source_file)
    media_type = _media_type(source)
    validation = _validate_source(source, media_type)
    checksum = _checksum(source, label="replacement file")
    now = utc_now_iso()

    proof_source = _checked_license_file(license_file)
    proof_checksum = _checksum(proof_source, label="license proof") if proof_source else ""
    proof_target = (
        root
        / "assets"
        / "replacements"
        / "licenses"
        / _safe_component(scene_id)
        / _safe_component(slot_id)
        / f"{proof_checksum}_{_safe_filename(proof_source.name)}"
        if proof_source
        else None
    )
    media_target = (
        root
        / "assets"
        / "replacements"
        / _safe_component(scene_id)
        / _safe_component(slot_id)
        / f"{checksum}{source.suffix.lower()}"
    )

    previous_slot = slot.to_dict()
    previous_asset = dict(slot.selected_asset)
    proof_record = _proof_record(proof_source, proof_target, proof_checksum)
    replacement_asset, crop_decision = _build_replacement_asset(
        project_id=project_id,
        scene_id=scene_id,
        slot=slot,
        source=source,
        target=media_target,
        source_url=str(source_url or "").strip(),
        checksum=checksum,
        validation=validation,
        proof_record=proof_record,
        now=now,
    )

    # Validate every record that must be preserved before copying or writing anything.
    history_path = root / "assets" / "replacements" / "replacement_history.json"
    history = _load_history(history_path, project_id)
    quality_path = root / "quality" / "quality_report.json"
    render_path = root / "render" / "final_render_manifest.json"
    quality_manifest, quality_warning = _read_optional_json(quality_path, label="quality manifest")
    render_manifest, render_warning = _read_optional_json(render_path, label="final render manifest")
    missing_path = root / "assets" / "missing_assets.json"
    missing_manifest, missing_warning = _read_optional_json(missing_path, label="missing-assets manifest")
    warnings = [item for item in (quality_warning, render_warning, missing_warning) if item]

    if proof_source and proof_target:
        _copy_verified(proof_source, proof_target, proof_checksum)
    _copy_verified(source, media_target, checksum)

    _apply_replacement(
        scene_entry=scene_entry,
        assembly=assembly,
        slot=slot,
        asset=replacement_asset,
        crop_decision=crop_decision,
        mode=normalize_mode(
            assembly.completion_mode or str(completion_settings(job).get("mode") or "")
        ),
        now=now,
    )
    scene_usable = assembly.usable_in_draft
    if scene_usable:
        assets_manifest["missing_scenes"] = _without_scene(
            assets_manifest.get("missing_scenes"), scene_id
        )
        if isinstance(missing_manifest, dict):
            missing_manifest["missing_scenes"] = _without_scene(
                missing_manifest.get("missing_scenes"), scene_id
            )

    from src.news.asset_manager import refresh_manifest_summaries

    refresh_manifest_summaries(
        assets_manifest,
        mode=str(completion_settings(job).get("mode") or ""),
    )

    history_entry = {
        "operation": "replace_visual_slot",
        "operation_id": f"replace_{checksum[:16]}_{now}",
        "replaced_at": now,
        "project_id": project_id,
        "scene_id": scene_id,
        "slot_id": slot_id,
        "source_file": str(source),
        "source_url": str(source_url or "").strip(),
        "previous_slot": previous_slot,
        "previous_asset_id": str(previous_asset.get("asset_id") or ""),
        "replacement_asset_id": str(replacement_asset.get("asset_id") or ""),
        "replacement_path": str(media_target),
        "checksum_sha256": checksum,
        "license_proof": proof_record,
    }
    history["entries"].append(history_entry)

    stale_metadata = {
        "stale_reason": "visual_slot_replaced",
        "stale_at": now,
        "stale_scene_id": scene_id,
        "stale_slot_id": slot_id,
    }
    _mark_job_stale(job, stale_metadata)
    if isinstance(quality_manifest, dict):
        _mark_manifest_stale(quality_manifest, stale_metadata, clear_output=False)
    if isinstance(render_manifest, dict):
        _mark_manifest_stale(render_manifest, stale_metadata, clear_output=True)

    # Each project record is replaced atomically.  Research, script, visual planning,
    # provider search records, and source media are intentionally not written.
    _write_json_atomic(assets_path, assets_manifest)
    if isinstance(missing_manifest, dict):
        _write_json_atomic(missing_path, missing_manifest)
    _write_json_atomic(history_path, history)
    if isinstance(quality_manifest, dict):
        _write_json_atomic(quality_path, quality_manifest)
    if isinstance(render_manifest, dict):
        _write_json_atomic(render_path, render_manifest)
    _write_json_atomic(root / "job.json", job.to_dict())

    report_paths: dict[str, str] = {}
    try:
        from src.news.draft_completion import write_completion_report

        report_paths = write_completion_report(root=root, job=job)
    except Exception as exc:  # the replacement itself remains valid and rerenderable
        warnings.append(f"replacement_report_not_regenerated:{type(exc).__name__}:{exc}")

    return {
        "status": "replaced",
        "project_id": project_id,
        "scene_id": scene_id,
        "slot_id": slot_id,
        "asset_id": str(replacement_asset.get("asset_id") or ""),
        "asset_path": str(media_target),
        "media_type": media_type,
        "checksum_sha256": checksum,
        "source_url": str(source_url or "").strip(),
        "license_proof_path": str(proof_target) if proof_target else "",
        "license_proof_checksum_sha256": proof_checksum,
        "history_path": str(history_path),
        "assets_manifest_path": str(assets_path),
        "stale_stages": list(STALE_STAGES),
        "report_paths": report_paths,
        "warnings": warnings,
    }


def _checked_project_root(repository: ProjectRepository, project_id: str) -> Path:
    if not project_id:
        raise VisualSlotReplacementError("A project id is required.", code="project_id_required")
    base = repository.projects_root.resolve()
    candidate = repository.project_root(project_id).resolve()
    try:
        relative = candidate.relative_to(base)
    except ValueError as exc:
        raise VisualSlotReplacementError(
            "The project id resolves outside the projects root.",
            code="invalid_project_id",
        ) from exc
    if len(relative.parts) != 1 or relative.parts[0] in {"", ".", ".."}:
        raise VisualSlotReplacementError(
            "The project id must name one project folder.",
            code="invalid_project_id",
        )
    if not candidate.is_dir():
        raise VisualSlotReplacementError(
            f"Project {project_id!r} was not found under {base}.",
            code="project_not_found",
        )
    return candidate


def _load_job(store: NewsProjectStore, project_id: str) -> NewsJob:
    try:
        return store.load_job(project_id)
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise VisualSlotReplacementError(
            f"The project job manifest could not be read: {exc}",
            code="job_manifest_invalid",
        ) from exc


def _read_required_json(path: Path, *, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise VisualSlotReplacementError(
            f"The {label} does not exist: {path}",
            code="manifest_missing",
        )
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise VisualSlotReplacementError(
            f"The {label} is not valid JSON: {path}",
            code="manifest_invalid",
        ) from exc
    if not isinstance(data, dict):
        raise VisualSlotReplacementError(
            f"The {label} must contain a JSON object: {path}",
            code="manifest_invalid",
        )
    return data


def _read_optional_json(path: Path, *, label: str) -> tuple[dict[str, Any] | None, str]:
    if not path.is_file():
        return None, ""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, f"{label}_not_marked_stale:{type(exc).__name__}"
    if not isinstance(data, dict):
        return None, f"{label}_not_marked_stale:not_an_object"
    return data, ""


def _find_scene(manifest: dict[str, Any], scene_id: str) -> dict[str, Any]:
    scenes = manifest.get("scenes")
    if not isinstance(scenes, list):
        raise VisualSlotReplacementError(
            "The assets manifest has no scene list.",
            code="assets_manifest_invalid",
        )
    for entry in scenes:
        if isinstance(entry, dict) and str(entry.get("scene_id") or "") == scene_id:
            return entry
    raise VisualSlotReplacementError(
        f"Scene {scene_id!r} was not found in the assets manifest.",
        code="scene_not_found",
    )


def _checked_source_file(value: str | Path) -> Path:
    text = str(value or "").strip()
    if not text:
        raise VisualSlotReplacementError(
            "A replacement file is required.",
            code="source_file_required",
        )
    source = Path(text).resolve()
    if not source.is_file():
        raise VisualSlotReplacementError(
            f"Replacement file does not exist: {source}",
            code="source_file_missing",
        )
    return source


def _checked_license_file(value: str | Path) -> Path | None:
    text = str(value or "").strip()
    if not text:
        return None
    source = Path(text).resolve()
    if not source.is_file():
        raise VisualSlotReplacementError(
            f"License proof does not exist: {source}",
            code="license_file_missing",
        )
    try:
        size = source.stat().st_size
    except OSError as exc:
        raise VisualSlotReplacementError(
            f"License proof cannot be read: {source}",
            code="license_file_unreadable",
        ) from exc
    if size <= 0:
        raise VisualSlotReplacementError(
            f"License proof is empty: {source}",
            code="license_file_empty",
        )
    return source


def _media_type(source: Path) -> str:
    suffix = source.suffix.lower()
    if suffix in _IMAGE_EXTENSIONS:
        return "image"
    if suffix in _VIDEO_EXTENSIONS:
        return "video"
    raise VisualSlotReplacementError(
        f"Unsupported replacement file type {suffix or '(none)'}; use an image or video file.",
        code="unsupported_media_type",
    )


def _validate_source(source: Path, media_type: str) -> dict[str, Any]:
    try:
        validation = validate_local_asset(source, media_type)
    except FileNotFoundError as exc:
        raise VisualSlotReplacementError(
            f"Required media validator is unavailable: {exc}",
            code="media_validator_unavailable",
        ) from exc
    except ProviderValidationError as exc:
        raise VisualSlotReplacementError(
            f"Replacement file failed technical validation: {exc}",
            code="invalid_media",
        ) from exc
    except OSError as exc:
        raise VisualSlotReplacementError(
            f"Replacement file could not be validated: {exc}",
            code="source_file_unreadable",
        ) from exc
    return dict(validation)


def _checksum(path: Path | None, *, label: str) -> str:
    if path is None:
        return ""
    try:
        return sha256_file(path)
    except OSError as exc:
        raise VisualSlotReplacementError(
            f"The {label} could not be read: {path}",
            code="source_file_unreadable",
        ) from exc


def _proof_record(source: Path | None, target: Path | None, checksum: str) -> dict[str, Any]:
    if source is None or target is None:
        return {}
    return {
        "original_filename": source.name,
        "stored_path": str(target),
        "checksum_sha256": checksum,
    }


def _build_replacement_asset(
    *,
    project_id: str,
    scene_id: str,
    slot: VisualSlot,
    source: Path,
    target: Path,
    source_url: str,
    checksum: str,
    validation: dict[str, Any],
    proof_record: dict[str, Any],
    now: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    asset_id = stable_asset_id("manual_slot_replacement", project_id, scene_id, slot.slot_id, checksum)
    internal_source = source_url or f"manual://user-owned/{checksum}"
    rights_declaration: dict[str, Any] = {
        "schema_version": 1,
        "confirmation_status": "owner_approved",
        "owner_approval_status": "owner_approved",
        "confirmed": True,
        "owner_confirmed": True,
        "rights_confirmed": True,
        "rights_status": "user_owned",
        "license_name": "user_owned",
        "commercial_use_allowed": True,
        "modification_allowed": True,
        "project_id": project_id,
        "scene_id": scene_id,
        "slot_id": slot.slot_id,
        "confirmed_at": now,
        "confirmation_source": "manual_slot_replacement",
    }
    if proof_record:
        rights_declaration["license_proof"] = dict(proof_record)

    width = int(validation.get("width") or 0)
    height = int(validation.get("height") or 0)
    duration = float(validation.get("duration_sec") or 0.0)
    candidate = AssetCandidate(
        asset_id=asset_id,
        provider="user",
        provider_asset_id=asset_id,
        media_type=str(validation.get("media_type") or _media_type(source)),
        title=source.stem,
        description="User-supplied replacement for one visual slot.",
        tags=[source.stem],
        tags_source="manual",
        source_page_url=internal_source,
        download_url=internal_source,
        author_name="user",
        width=width,
        height=height,
        duration_sec=duration,
        orientation=str(validation.get("orientation") or orientation_from_dimensions(width, height)),
        local_path=str(target),
        original_filename=source.name,
        downloaded_at=now,
        checksum_sha256=checksum,
        project_id=project_id,
        scene_id=scene_id,
        license=AssetLicense(
            license_name="user_owned",
            rights_status="user_owned",
            commercial_use_allowed=True,
            modification_allowed=True,
            attribution_required=False,
            allowed_for_render=True,
            review_required=False,
            notes="Owner-confirmed manual visual-slot replacement.",
            checked_at=now,
        ),
        provenance=AssetProvenance(
            provider="user",
            provider_asset_id=asset_id,
            source_page_url=internal_source,
            download_url=internal_source,
            original_filename=source.name,
            downloaded_at=now,
            checksum_sha256=checksum,
            project_id=project_id,
            scene_id=scene_id,
            metadata_snapshot={
                "operation": "manual_slot_replacement",
                "slot_id": slot.slot_id,
                "declared_source_url": source_url,
                "rights_declaration": rights_declaration,
                "license_proof": proof_record,
            },
        ),
        raw_metadata={
            "operation": "manual_slot_replacement",
            "slot_id": slot.slot_id,
            "source_filename": source.name,
        },
        schema_version=ASSET_SCHEMA_VERSION,
        technical_validation=dict(validation),
        rights_declaration=rights_declaration,
    )
    policy = evaluate_asset_policy(
        candidate,
        policy_path=_REPOSITORY_ROOT / "config" / "license_policy.json",
    )
    if not policy.allowed_for_render or policy.review_required:
        raise VisualSlotReplacementError(
            f"Confirmed user-owned replacement was blocked by the license policy: {policy.reason}",
            code="rights_policy_blocked",
        )
    candidate.policy_decision = policy.to_dict()
    asset = candidate.to_manifest_dict()

    detected_framing = framing_decision(asset)
    detected_status = str(detected_framing.get("status") or "")
    if detected_status in FRAMING_HARD_REJECT:
        raise VisualSlotReplacementError(
            f"Replacement cannot fill the project frame safely: {detected_framing.get('reason') or detected_status}",
            code="technically_unsuitable",
        )
    crop_decision = dict(detected_framing)
    crop_decision["automated_status"] = detected_status
    crop_decision["manual_confirmation"] = True
    crop_decision["confirmation_source"] = "manual_slot_replacement"
    if detected_status == FRAMING_CROP_REVIEW:
        crop_decision["status"] = _MANUAL_CROP_APPROVED
        crop_decision["render_ready"] = True

    previous_decision = read_decision(slot.selected_asset)
    decision = SelectionDecision(
        scene_id=scene_id,
        asset_id=asset_id,
        provider="user",
        source_class=previous_decision.source_class,
        provider_confidence=1.0,
        semantic_score=1.0,
        semantic_status="manual_confirmed",
        metadata_score=1.0,
        metadata_status="manual_confirmed",
        technical_score=1.0,
        technical_status=str(crop_decision.get("status") or detected_status),
        framing=crop_decision,
        duration_status="validated",
        duration={"duration_sec": duration},
        rights_status="user_owned",
        rights_allowed_for_render=True,
        rights_review_required=False,
        slots={
            "matched_slots": ["manual_replacement"],
            "missing_slots": [],
            "missing_required_slots": [],
            "conflicting_slots": [],
            "undecidable_slots": [],
        },
        slot_verdict=VERDICT_COMPLETE,
        support_status=SUPPORT_FULL,
        support_requirements=[],
        selection_reasons=[
            "selected_by:manual_slot_replacement",
            "author_confirmed_scene_fit",
            "owner_confirmed_rights",
            "technical_validation_passed",
        ],
    )
    asset.update(
        {
            DECISION_KEY: decision.to_dict(),
            "selected_by": "manual_slot_replacement",
            "support_status": SUPPORT_FULL,
            "slot_verdict": VERDICT_COMPLETE,
            "framing_status": str(crop_decision.get("status") or ""),
            "framing_check": crop_decision,
            "quality_score": 1.0,
            "rights_score": 1.0,
            "manual_replacement": {
                "scene_id": scene_id,
                "slot_id": slot.slot_id,
                "imported_at": now,
                "declared_source_url": source_url,
                "license_proof": proof_record,
            },
        }
    )
    return asset, crop_decision


def _apply_replacement(
    *,
    scene_entry: dict[str, Any],
    assembly: SceneVisualAssembly,
    slot: VisualSlot,
    asset: dict[str, Any],
    crop_decision: dict[str, Any],
    mode: str,
    now: str,
) -> None:
    usability = evaluate_usability(
        asset,
        mode=mode,
        quality_tier=TIER_EXACT,
        require_local_file=True,
    )
    if usability.blocked or not usability.usable_in_draft:
        reasons = ", ".join(usability.block_reasons or usability.reasons) or "not usable"
        raise VisualSlotReplacementError(
            f"Replacement did not pass the visual render gate: {reasons}",
            code="replacement_not_usable",
        )

    slot.selected_asset = dict(asset)
    slot.media_types = [str(asset.get("media_type") or asset.get("type") or "")]
    slot.support_status = SUPPORT_FULL
    slot.quality_tier = TIER_EXACT
    slot.usability = usability
    slot.provenance = dict(asset.get("provenance") or {})
    slot.rights = {
        "status": "user_owned",
        "allowed_for_render": True,
        "review_required": False,
        "license": dict(asset.get("license") or {}),
        "license_name": "user_owned",
        "rights_declaration": dict(asset.get("rights_declaration") or {}),
    }
    slot.crop_decision = dict(crop_decision)
    slot.replacement_priority = usability.replacement_priority
    slot.reuse_of_asset = ""
    slot.reuse_reason = ""
    slot.ladder_level = "manual_replacement"
    note = f"manual_replacement:{now}"
    if note not in slot.notes:
        slot.notes.append(note)

    assembly.completion_mode = mode
    assembly.replacement_recommendations = [
        item
        for item in assembly.replacement_recommendations
        if str(item.get("slot_id") or "") != slot.slot_id
    ]
    assembly.ladder_trace.append(f"manual_replacement:{slot.slot_id}")
    _refresh_assembly_status(assembly)
    attach_assembly(scene_entry, assembly)

    primary = assembly.primary_asset
    if primary:
        primary_decision = read_decision(primary)
        scene_entry["selected_asset"] = primary
        scene_entry[DECISION_KEY] = dict(primary.get(DECISION_KEY) or {})
        scene_entry["support_status"] = primary_decision.support_status
        scene_entry["support_requirements"] = list(primary_decision.support_requirements)
    if assembly.publish_ready:
        scene_entry["resolution_status"] = RESOLVED
    elif assembly.usable_in_draft:
        scene_entry["resolution_status"] = RESOLVED_NEEDS_REVIEW


def _refresh_assembly_status(assembly: SceneVisualAssembly) -> None:
    if not assembly.slots or not assembly.usable_in_draft:
        assembly.assembly_status = ASSEMBLY_UNRESOLVED
    elif assembly.publish_ready:
        assembly.assembly_status = ASSEMBLY_EXACT if len(assembly.slots) == 1 else ASSEMBLY_COMPOSITE
    elif any(slot.quality_tier in {TIER_GENERATED, TIER_EMERGENCY} for slot in assembly.slots):
        assembly.assembly_status = ASSEMBLY_FALLBACK
    else:
        assembly.assembly_status = ASSEMBLY_PARTIAL
    statuses = {slot.support_status for slot in assembly.slots if slot.support_status}
    assembly.support_status = SUPPORT_FULL if statuses == {SUPPORT_FULL} else (
        next(iter(statuses)) if len(statuses) == 1 else "mixed_support"
    )


def _without_scene(value: Any, scene_id: str) -> list[Any]:
    result: list[Any] = []
    for item in value if isinstance(value, list) else []:
        item_scene = str(item.get("scene_id") or "") if isinstance(item, dict) else str(item)
        if item_scene != scene_id:
            result.append(item)
    return result


def _load_history(path: Path, project_id: str) -> dict[str, Any]:
    if not path.exists():
        return {
            "schema_version": REPLACEMENT_HISTORY_SCHEMA_VERSION,
            "project_id": project_id,
            "entries": [],
        }
    data = _read_required_json(path, label="replacement history")
    entries = data.get("entries")
    if not isinstance(entries, list):
        raise VisualSlotReplacementError(
            f"Replacement history has no entries list: {path}",
            code="replacement_history_invalid",
        )
    data.setdefault("schema_version", REPLACEMENT_HISTORY_SCHEMA_VERSION)
    data.setdefault("project_id", project_id)
    return data


def _mark_job_stale(job: NewsJob, metadata: dict[str, Any]) -> None:
    for stage_name in STALE_STAGES:
        state = job.stages.get(stage_name)
        if state is None:
            state = StageState(stage=stage_name)
            job.stages[stage_name] = state
        state.status = "stale"
        state.started_at = None
        state.finished_at = None
        state.error = None
        state.settings = {**dict(state.settings or {}), **metadata}
    # Preserve unknown/newer stages and the canonical ordering of known stages.
    job.stages = {
        **{name: job.stages[name] for name in NEWS_TO_SHORT_STAGES if name in job.stages},
        **{name: state for name, state in job.stages.items() if name not in NEWS_TO_SHORT_STAGES},
    }
    job.status = "render_stale"
    job.current_stage = STALE_STAGES[0]
    job.updated_at = str(metadata.get("stale_at") or utc_now_iso())


def _mark_manifest_stale(
    manifest: dict[str, Any],
    metadata: dict[str, Any],
    *,
    clear_output: bool,
) -> None:
    prior_status = str(manifest.get("status") or "")
    if prior_status and prior_status != "stale":
        manifest["previous_status"] = prior_status
    manifest["status"] = "stale"
    manifest["stale"] = True
    manifest.update(metadata)
    if clear_output and manifest.get("output_path"):
        manifest["stale_output_path"] = str(manifest.get("output_path") or "")
        manifest["output_path"] = ""
    if clear_output:
        manifest["publish_ready"] = False


def _copy_verified(source: Path, target: Path, checksum: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if _checksum(target, label="stored replacement") != checksum:
            raise VisualSlotReplacementError(
                f"Replacement destination already contains different data: {target}",
                code="replacement_path_collision",
            )
        return
    temporary = target.parent / f".{target.name}.{uuid4().hex}.tmp"
    try:
        shutil.copyfile(source, temporary)
        if _checksum(temporary, label="copied replacement") != checksum:
            raise VisualSlotReplacementError(
                f"Checksum changed while copying replacement to {target}.",
                code="replacement_copy_mismatch",
            )
        os.replace(temporary, target)
    except VisualSlotReplacementError:
        raise
    except OSError as exc:
        raise VisualSlotReplacementError(
            f"Replacement could not be copied into the project: {exc}",
            code="replacement_copy_failed",
        ) from exc
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


def _write_json_atomic(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.parent / f".{path.name}.{uuid4().hex}.tmp"
    try:
        temporary.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, path)
    except OSError as exc:
        raise VisualSlotReplacementError(
            f"Project state could not be updated atomically at {path}: {exc}",
            code="project_write_failed",
        ) from exc
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


def _safe_component(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", str(value or "")).strip("_")[:80] or "item"


def _safe_filename(value: str) -> str:
    source = Path(str(value or "proof"))
    stem = _safe_component(source.stem)
    suffix = re.sub(r"[^a-zA-Z0-9.]+", "", source.suffix)[:16]
    return f"{stem}{suffix}"


def _float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


__all__ = [
    "REPLACEMENT_HISTORY_SCHEMA_VERSION",
    "STALE_STAGES",
    "VisualSlotReplacementError",
    "replace_visual_slot",
]
