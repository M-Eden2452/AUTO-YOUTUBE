from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


IMPLEMENTATION_STATUS_ACTIVE = "active"
IMPLEMENTATION_STATUS_PLANNED = "planned"
IMPLEMENTATION_STATUS_EXPERIMENTAL = "experimental"

IMPLEMENTATION_STATUSES = frozenset(
    {
        IMPLEMENTATION_STATUS_ACTIVE,
        IMPLEMENTATION_STATUS_PLANNED,
        IMPLEMENTATION_STATUS_EXPERIMENTAL,
    }
)


class CatalogValidationError(ValueError):
    """Raised for invalid catalog definitions or unknown catalog lookups."""


def _validate_implementation_status(value: str, *, owner: str) -> None:
    if value not in IMPLEMENTATION_STATUSES:
        raise CatalogValidationError(
            f"{owner}: implementation_status must be one of {sorted(IMPLEMENTATION_STATUSES)}, got {value!r}."
        )


def _as_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str | bytes):
        return (str(value),)
    return tuple(str(item) for item in value)


@dataclass(frozen=True)
class ApplicationDefinition:
    application_id: str
    display_name: str
    description: str
    supported_input_types: tuple[str, ...]
    supported_format_ids: tuple[str, ...]
    enabled: bool
    implementation_status: str

    def __post_init__(self) -> None:
        _validate_implementation_status(self.implementation_status, owner=f"application {self.application_id!r}")
        object.__setattr__(self, "supported_input_types", _as_tuple(self.supported_input_types))
        object.__setattr__(self, "supported_format_ids", _as_tuple(self.supported_format_ids))

    def to_dict(self) -> dict[str, Any]:
        return {
            "application_id": self.application_id,
            "display_name": self.display_name,
            "description": self.description,
            "supported_input_types": list(self.supported_input_types),
            "supported_format_ids": list(self.supported_format_ids),
            "enabled": self.enabled,
            "implementation_status": self.implementation_status,
        }


@dataclass(frozen=True)
class FormatDefinition:
    format_id: str
    display_name: str
    width: int
    height: int
    aspect_ratio: str
    enabled: bool
    implementation_status: str

    def __post_init__(self) -> None:
        _validate_implementation_status(self.implementation_status, owner=f"format {self.format_id!r}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "format_id": self.format_id,
            "display_name": self.display_name,
            "width": self.width,
            "height": self.height,
            "aspect_ratio": self.aspect_ratio,
            "enabled": self.enabled,
            "implementation_status": self.implementation_status,
        }


@dataclass(frozen=True)
class TemplateDefinition:
    template_id: str
    application_id: str
    format_id: str
    display_name: str
    description: str
    version: int
    enabled: bool
    implementation_status: str
    supported_input_types: tuple[str, ...]
    supported_export_targets: tuple[str, ...]
    requires_voice: bool
    supports_topic_input: bool
    supports_script_input: bool
    recommended_for: tuple[str, ...]
    render_preset_id: str
    legacy_aliases: tuple[str, ...] = ()
    workflow_binding: dict[str, Any] = field(default_factory=dict)
    output_contract: dict[str, Any] = field(default_factory=dict)
    evidence_required: bool = True
    script_policy_id: str | None = None
    asset_policy_id: str | None = None
    audio_policy_id: str | None = None
    duration_policy_id: str | None = None
    selection_policy_id: str | None = None
    quality_policy_id: str | None = None

    def __post_init__(self) -> None:
        _validate_implementation_status(self.implementation_status, owner=f"template {self.template_id!r}")
        object.__setattr__(self, "supported_input_types", _as_tuple(self.supported_input_types))
        object.__setattr__(self, "supported_export_targets", _as_tuple(self.supported_export_targets))
        object.__setattr__(self, "recommended_for", _as_tuple(self.recommended_for))
        object.__setattr__(self, "legacy_aliases", _as_tuple(self.legacy_aliases))

    def to_dict(self) -> dict[str, Any]:
        return {
            "template_id": self.template_id,
            "application_id": self.application_id,
            "format_id": self.format_id,
            "display_name": self.display_name,
            "description": self.description,
            "version": self.version,
            "enabled": self.enabled,
            "implementation_status": self.implementation_status,
            "supported_input_types": list(self.supported_input_types),
            "supported_export_targets": list(self.supported_export_targets),
            "requires_voice": self.requires_voice,
            "supports_topic_input": self.supports_topic_input,
            "supports_script_input": self.supports_script_input,
            "recommended_for": list(self.recommended_for),
            "render_preset_id": self.render_preset_id,
            "legacy_aliases": list(self.legacy_aliases),
            "workflow_binding": dict(self.workflow_binding),
            "output_contract": dict(self.output_contract),
            "evidence_required": self.evidence_required,
            "script_policy_id": self.script_policy_id,
            "asset_policy_id": self.asset_policy_id,
            "audio_policy_id": self.audio_policy_id,
            "duration_policy_id": self.duration_policy_id,
            "selection_policy_id": self.selection_policy_id,
            "quality_policy_id": self.quality_policy_id,
        }


@dataclass(frozen=True)
class ExportTargetDefinition:
    target_id: str
    display_name: str
    format_id: str
    width: int
    height: int
    aspect_ratio: str
    safe_zone_profile: str
    output_filename: str
    enabled: bool
    implementation_status: str
    max_duration_sec: int | None = None

    def __post_init__(self) -> None:
        _validate_implementation_status(self.implementation_status, owner=f"export target {self.target_id!r}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_id": self.target_id,
            "display_name": self.display_name,
            "format_id": self.format_id,
            "width": self.width,
            "height": self.height,
            "aspect_ratio": self.aspect_ratio,
            "max_duration_sec": self.max_duration_sec,
            "safe_zone_profile": self.safe_zone_profile,
            "output_filename": self.output_filename,
            "enabled": self.enabled,
            "implementation_status": self.implementation_status,
        }
