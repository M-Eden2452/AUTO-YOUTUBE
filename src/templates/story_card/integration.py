from __future__ import annotations

import copy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.project_foundation.evidence import EvidenceBundle
from src.project_foundation.models import (
    VERIFICATION_VERIFIED,
    ChannelProfile,
    ProjectManifest,
)
from src.project_foundation.policies import ChannelOutputPolicy
from src.project_foundation.storage import atomic_write_json, ensure_dir
from src.production_plan.story_card_short_render import (
    DEFAULT_STORY_CARD_PRESET_PATH,
    load_story_card_preset,
    render_story_card_short,
)

STORY_CARD_CANONICAL_TEMPLATE_ID = "story_card_text_only_v1"

# This template uses exactly one visual, so one stable id is enough: re-rendering the
# same project replaces the record instead of piling up near-duplicates.
STORY_CARD_VISUAL_EVIDENCE_ID = "visual_source_asset"
STORY_CARD_LEGACY_ALIASES = ("story_card_short_v1",)
STORY_CARD_SUPPORTED_FORMAT_ID = "vertical_short"

_STORY_CARD_TEMPLATE_IDS = frozenset({STORY_CARD_CANONICAL_TEMPLATE_ID, *STORY_CARD_LEGACY_ALIASES})

RENDER_STATUS_DRY_RUN = "dry_run"
RENDER_STATUS_PREPARED = "prepared"
RENDER_STATUS_RENDERED = "rendered"
RENDER_STATUS_SKIPPED_EXISTING_OUTPUT = "skipped_existing_output"
RENDER_STATUS_FAILED = "failed"

DEFAULT_OUTPUT_FILENAME = "story_card_short.mp4"
DEFAULT_PREVIEW_FILENAME = "story_card_preview.png"
DEFAULT_RENDER_REQUEST_FILENAME = "story_card_render_request.json"


class StoryCardIntegrationError(ValueError):
    """Raised for invalid Story Card integration input (template, format, asset, text)."""


def canonicalize_story_card_template_id(template_id: str) -> str:
    """Resolve a template_id or legacy alias to the canonical Story Card template_id.

    Mirrors the alias mapping registered in src.production_catalog.catalog
    (story_card_short_v1 -> story_card_text_only_v1) without importing that
    package, per the Stage 2C scope boundary (Production Catalog stays
    unconnected on this stage).
    """
    text = str(template_id or "").strip()
    if text in _STORY_CARD_TEMPLATE_IDS:
        return STORY_CARD_CANONICAL_TEMPLATE_ID
    raise StoryCardIntegrationError(
        f"template_id {template_id!r} is not the Story Card template "
        f"{STORY_CARD_CANONICAL_TEMPLATE_ID!r} or a known legacy alias {STORY_CARD_LEGACY_ALIASES}."
    )


@dataclass
class StoryCardIntegrationResult:
    project_id: str
    template_id: str
    canonical_template_id: str
    render_status: str
    render_request_path: str
    output_path: str
    width: int
    height: int
    fps: int
    duration_seconds: float
    source_asset: str
    localization: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "template_id": self.template_id,
            "canonical_template_id": self.canonical_template_id,
            "render_status": self.render_status,
            "render_request_path": self.render_request_path,
            "output_path": self.output_path,
            "width": self.width,
            "height": self.height,
            "fps": self.fps,
            "duration_seconds": self.duration_seconds,
            "source_asset": self.source_asset,
            "localization": dict(self.localization),
            "warnings": list(self.warnings),
            "metadata": dict(self.metadata),
        }


def _check_channel_compatibility(
    channel: ChannelProfile,
    project: ProjectManifest,
    canonical_template_id: str,
    warnings: list[str],
) -> None:
    """Validate ChannelProfile/ChannelOutputPolicy compatibility (alias-aware).

    Raises StoryCardIntegrationError for hard policy violations. Adds soft
    observations to `warnings`. Does not call src.project_foundation.policies.validate()
    because that check compares template_id by exact string, not by alias -
    duplicating just the template/language/export_targets rules here keeps
    Stage 2B's validate() untouched while staying alias-aware.
    """
    if project.language not in channel.supported_languages:
        raise StoryCardIntegrationError(
            f"language {project.language!r} is not in channel {channel.channel_id!r} "
            f"supported_languages {channel.supported_languages}."
        )

    policy = ChannelOutputPolicy.from_dict(channel.output_policy)

    if policy.allowed_templates:
        allowed_canonical: set[str] = set()
        for allowed in policy.allowed_templates:
            try:
                allowed_canonical.add(canonicalize_story_card_template_id(allowed))
            except StoryCardIntegrationError:
                allowed_canonical.add(str(allowed))
        if canonical_template_id not in allowed_canonical:
            raise StoryCardIntegrationError(
                f"template {canonical_template_id!r} is not in channel "
                f"{channel.channel_id!r} allowed_templates {policy.allowed_templates}."
            )

    if policy.allowed_formats and project.format_id not in policy.allowed_formats:
        raise StoryCardIntegrationError(
            f"format_id {project.format_id!r} is not in channel {channel.channel_id!r} "
            f"allowed_formats {policy.allowed_formats}."
        )

    if policy.allowed_export_targets:
        disallowed = [t for t in project.export_targets if t not in policy.allowed_export_targets]
        if disallowed:
            warnings.append(
                f"export_targets {disallowed} are not in channel {channel.channel_id!r} "
                f"allowed_export_targets {policy.allowed_export_targets}."
            )

    if channel.default_template:
        try:
            default_canonical = canonicalize_story_card_template_id(channel.default_template)
        except StoryCardIntegrationError:
            default_canonical = channel.default_template
        if default_canonical != canonical_template_id:
            warnings.append(
                f"project template {canonical_template_id!r} overrides channel "
                f"{channel.channel_id!r} default_template {channel.default_template!r}."
            )


def _record_source_asset_evidence(
    *,
    project: ProjectManifest,
    source_asset: Path,
    asset: Any,
    warnings: list[str],
) -> dict[str, Any]:
    """Store what this project is really using, in the project's own EvidenceBundle.

    Uses the existing bundle at ``<project_root>/evidence/evidence_manifest.json`` -
    the same file ``src.projects.build_rights_report`` already reads - rather than a
    story-card-specific format. The record is keyed by a fixed evidence_id because
    this template has exactly one visual, so re-rendering updates it in place.

    Raises StoryCardIntegrationError if the material cannot be described. That is
    deliberate: this template is registered with evidence_required=True, and a video
    whose source we cannot account for is worse than a video we did not make.
    """
    from src.assets.evidence_adapter import AssetEvidenceError, build_asset_evidence_record

    try:
        record = build_asset_evidence_record(
            evidence_id=STORY_CARD_VISUAL_EVIDENCE_ID, local_path=source_asset, asset=asset
        )
    except AssetEvidenceError as exc:
        raise StoryCardIntegrationError(f"Could not record evidence for the source asset: {exc}") from exc

    bundle = EvidenceBundle.load(project.project_root, project.project_id)
    bundle.add(record, overwrite=True)
    manifest_path = bundle.save(project.project_root)

    if record.verification_status != VERIFICATION_VERIFIED:
        warnings.append(
            f"Права на исходный материал не подтверждены (статус: {record.verification_status}, "
            f"источник: {record.source_type or 'не указан'}). Подробности: "
            "project rights-report --project-id "
            f"{project.project_id}."
        )

    return {
        "evidence_id": record.evidence_id,
        "evidence_manifest_path": Path(manifest_path).as_posix(),
        "checksum_sha256": record.checksum_sha256,
        "source_type": record.source_type,
        "provider": record.provider,
        "rights_status": record.verification_status,
        "review_required": record.review_required,
    }


def prepare_story_card_render(
    project: ProjectManifest,
    *,
    channel: ChannelProfile | None = None,
    source_asset_path: str | Path,
    source_asset: Any = None,
    text: dict[str, str],
    render_preset_path: str | Path = DEFAULT_STORY_CARD_PRESET_PATH,
    output_filename: str = DEFAULT_OUTPUT_FILENAME,
    preview_filename: str = DEFAULT_PREVIEW_FILENAME,
    render_request_filename: str = DEFAULT_RENDER_REQUEST_FILENAME,
    dry_run: bool = True,
    allow_overwrite: bool = False,
    render: bool = False,
) -> StoryCardIntegrationResult:
    """Prepare (and optionally perform) a Story Card render for a ProjectManifest.

    Never touches the network, never downloads assets, never calls TTS. Only
    reads a local source_asset_path and writes under project.project_root.
    When dry_run is True, no files are written regardless of `render`.

    ``source_asset`` is optional provenance for the same file: an AssetCandidate /
    DownloadedAsset (or its dict form) when the material came from a provider, so
    its licence and provenance are stored instead of being flattened into
    "user_supplied". ``source_asset_path`` always decides which file is rendered
    and which file the checksum is taken from.
    """
    if not isinstance(project, ProjectManifest):
        raise StoryCardIntegrationError("prepare_story_card_render requires a ProjectManifest instance.")

    warnings: list[str] = []
    canonical_template_id = canonicalize_story_card_template_id(project.template_id)

    if project.format_id != STORY_CARD_SUPPORTED_FORMAT_ID:
        raise StoryCardIntegrationError(
            f"format_id {project.format_id!r} is not supported by the Story Card template; "
            f"expected {STORY_CARD_SUPPORTED_FORMAT_ID!r}."
        )

    if channel is not None:
        if not isinstance(channel, ChannelProfile):
            raise StoryCardIntegrationError("channel must be a ChannelProfile instance when provided.")
        _check_channel_compatibility(channel, project, canonical_template_id, warnings)

    source_asset_path_resolved = Path(source_asset_path)
    if not source_asset_path_resolved.is_file():
        raise StoryCardIntegrationError(f"source_asset_path {source_asset_path!r} does not exist or is not a file.")

    top_text = str((text or {}).get("top") or "").strip()
    comment_text = str((text or {}).get("comment") or "").strip()
    if not top_text and not comment_text:
        raise StoryCardIntegrationError("text must include a non-empty 'top' or 'comment' localization string.")

    preset = copy.deepcopy(load_story_card_preset(render_preset_path))
    preset_text = dict(preset.get("text") or {})
    if top_text:
        preset_text["top"] = top_text
    if comment_text:
        preset_text["comment"] = comment_text
    preset["text"] = preset_text

    width, height = [int(value) for value in preset["resolution"]]
    fps = int(preset["fps"])
    duration_seconds = float(preset["duration_sec"])

    project_root = Path(project.project_root)
    output_path = project_root / "outputs" / output_filename
    preview_path = project_root / "outputs" / preview_filename
    render_request_path = project_root / "outputs" / render_request_filename

    localization = {
        "language": project.language,
        "text": {"top": preset_text.get("top", ""), "comment": preset_text.get("comment", "")},
    }

    metadata: dict[str, Any] = {
        "preset_name": preset.get("name", ""),
        "preset_path": str(Path(render_preset_path)),
        "frame_preview_path": preview_path.as_posix(),
        "channel_id": channel.channel_id if channel is not None else "",
    }

    if dry_run:
        return StoryCardIntegrationResult(
            project_id=project.project_id,
            template_id=project.template_id,
            canonical_template_id=canonical_template_id,
            render_status=RENDER_STATUS_DRY_RUN,
            render_request_path=render_request_path.as_posix(),
            output_path=output_path.as_posix(),
            width=width,
            height=height,
            fps=fps,
            duration_seconds=duration_seconds,
            source_asset=str(source_asset_path_resolved),
            localization=localization,
            warnings=warnings,
            metadata=metadata,
        )

    if output_path.exists() and not allow_overwrite:
        warnings.append(
            f"output_path {output_path.as_posix()!r} already exists; pass allow_overwrite=True to replace it."
        )
        return StoryCardIntegrationResult(
            project_id=project.project_id,
            template_id=project.template_id,
            canonical_template_id=canonical_template_id,
            render_status=RENDER_STATUS_SKIPPED_EXISTING_OUTPUT,
            render_request_path=render_request_path.as_posix(),
            output_path=output_path.as_posix(),
            width=width,
            height=height,
            fps=fps,
            duration_seconds=duration_seconds,
            source_asset=str(source_asset_path_resolved),
            localization=localization,
            warnings=warnings,
            metadata=metadata,
        )

    # Record what is being used *before* rendering: this is the moment the project
    # commits to one specific file, and the checksum below is taken from that same
    # file, so a candidate swapped out earlier can never end up in the report.
    evidence = _record_source_asset_evidence(
        project=project, source_asset=source_asset_path_resolved, asset=source_asset, warnings=warnings
    )

    render_request = {
        "schema_version": "story_card_render_request.v1",
        "project_id": project.project_id,
        "channel_id": channel.channel_id if channel is not None else "",
        "template_id": project.template_id,
        "canonical_template_id": canonical_template_id,
        "format_id": project.format_id,
        "language": project.language,
        "source_asset": str(source_asset_path_resolved),
        "output_path": output_path.as_posix(),
        "frame_preview_path": preview_path.as_posix(),
        "preset": preset,
        # Ties the render input to its rights record: same file, same checksum.
        "evidence_id": evidence.get("evidence_id", ""),
        "source_asset_checksum_sha256": evidence.get("checksum_sha256", ""),
    }
    metadata["evidence"] = evidence
    ensure_dir(output_path.parent)
    atomic_write_json(render_request_path, render_request)

    if not render:
        return StoryCardIntegrationResult(
            project_id=project.project_id,
            template_id=project.template_id,
            canonical_template_id=canonical_template_id,
            render_status=RENDER_STATUS_PREPARED,
            render_request_path=render_request_path.as_posix(),
            output_path=output_path.as_posix(),
            width=width,
            height=height,
            fps=fps,
            duration_seconds=duration_seconds,
            source_asset=str(source_asset_path_resolved),
            localization=localization,
            warnings=warnings,
            metadata=metadata,
        )

    render_manifest = render_story_card_short(
        source_video=source_asset_path_resolved,
        output_path=output_path,
        frame_preview_path=preview_path,
        preset=preset,
    )
    metadata["render_manifest"] = render_manifest
    render_status = RENDER_STATUS_RENDERED if render_manifest.get("status") == "completed" else RENDER_STATUS_FAILED

    return StoryCardIntegrationResult(
        project_id=project.project_id,
        template_id=project.template_id,
        canonical_template_id=canonical_template_id,
        render_status=render_status,
        render_request_path=render_request_path.as_posix(),
        output_path=output_path.as_posix(),
        width=int(render_manifest.get("resolution", {}).get("width") or width),
        height=int(render_manifest.get("resolution", {}).get("height") or height),
        fps=fps,
        duration_seconds=float(render_manifest.get("duration_sec") or duration_seconds),
        source_asset=str(source_asset_path_resolved),
        localization=localization,
        warnings=warnings,
        metadata=metadata,
    )
