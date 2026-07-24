from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .models import ChannelProfile, EvidenceSummary, ProjectFoundationError, ProjectManifest


@dataclass
class ChannelOutputPolicy:
    """Output constraints for a channel.

    An empty allow-list means "no restriction" (anything is allowed) - this keeps
    safe defaults permissive rather than accidentally blocking everything.
    """

    allowed_applications: list[str] = field(default_factory=list)
    allowed_formats: list[str] = field(default_factory=list)
    allowed_templates: list[str] = field(default_factory=list)
    allowed_export_targets: list[str] = field(default_factory=list)
    allowed_languages: list[str] = field(default_factory=list)
    require_verified_evidence: bool = False
    allow_review_required_assets: bool = True
    allow_unknown_license: bool = False
    minimum_resolution: dict[str, int] | None = None
    preferred_resolution: dict[str, int] | None = None
    maximum_duration_seconds: int | None = None
    require_voiceover: bool = False
    require_music: bool = False
    require_subtitles: bool = False
    require_manual_qc: bool = False
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed_applications": list(self.allowed_applications),
            "allowed_formats": list(self.allowed_formats),
            "allowed_templates": list(self.allowed_templates),
            "allowed_export_targets": list(self.allowed_export_targets),
            "allowed_languages": list(self.allowed_languages),
            "require_verified_evidence": self.require_verified_evidence,
            "allow_review_required_assets": self.allow_review_required_assets,
            "allow_unknown_license": self.allow_unknown_license,
            "minimum_resolution": dict(self.minimum_resolution) if self.minimum_resolution else None,
            "preferred_resolution": dict(self.preferred_resolution) if self.preferred_resolution else None,
            "maximum_duration_seconds": self.maximum_duration_seconds,
            "require_voiceover": self.require_voiceover,
            "require_music": self.require_music,
            "require_subtitles": self.require_subtitles,
            "require_manual_qc": self.require_manual_qc,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> ChannelOutputPolicy:
        data = data or {}
        return cls(
            allowed_applications=list(data.get("allowed_applications") or []),
            allowed_formats=list(data.get("allowed_formats") or []),
            allowed_templates=list(data.get("allowed_templates") or []),
            allowed_export_targets=list(data.get("allowed_export_targets") or []),
            allowed_languages=list(data.get("allowed_languages") or []),
            require_verified_evidence=bool(data.get("require_verified_evidence", False)),
            allow_review_required_assets=bool(data.get("allow_review_required_assets", True)),
            allow_unknown_license=bool(data.get("allow_unknown_license", False)),
            minimum_resolution=data.get("minimum_resolution") or None,
            preferred_resolution=data.get("preferred_resolution") or None,
            maximum_duration_seconds=data.get("maximum_duration_seconds"),
            require_voiceover=bool(data.get("require_voiceover", False)),
            require_music=bool(data.get("require_music", False)),
            require_subtitles=bool(data.get("require_subtitles", False)),
            require_manual_qc=bool(data.get("require_manual_qc", False)),
            notes=str(data.get("notes", "")),
        )


@dataclass
class ValidationResult:
    allowed: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    evaluated_rules: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "evaluated_rules": list(self.evaluated_rules),
        }


def _check_resolution_at_least(actual: dict[str, Any], minimum: dict[str, int]) -> bool:
    try:
        return int(actual.get("width", 0)) >= int(minimum.get("width", 0)) and int(actual.get("height", 0)) >= int(
            minimum.get("height", 0)
        )
    except (TypeError, ValueError):
        return False


def validate(
    policy: ChannelOutputPolicy,
    channel: ChannelProfile,
    project: ProjectManifest,
    evidence_summary: EvidenceSummary,
) -> ValidationResult:
    """Validate a ProjectManifest against a ChannelOutputPolicy.

    Does not probe real media files (no ffprobe) - resolution/duration/voiceover/music/
    subtitles checks only run when the corresponding value is present in project.metadata.
    """
    if not isinstance(policy, ChannelOutputPolicy):
        raise ProjectFoundationError("validate() requires a ChannelOutputPolicy instance.")
    if not isinstance(channel, ChannelProfile):
        raise ProjectFoundationError("validate() requires a ChannelProfile instance.")
    if not isinstance(project, ProjectManifest):
        raise ProjectFoundationError("validate() requires a ProjectManifest instance.")
    if not isinstance(evidence_summary, EvidenceSummary):
        raise ProjectFoundationError("validate() requires an EvidenceSummary instance.")

    errors: list[str] = []
    warnings: list[str] = []
    evaluated_rules: list[str] = []

    evaluated_rules.append("application")
    if policy.allowed_applications and project.application_id not in policy.allowed_applications:
        errors.append(
            f"application_id {project.application_id!r} is not in allowed_applications {policy.allowed_applications}."
        )

    evaluated_rules.append("format")
    if policy.allowed_formats and project.format_id not in policy.allowed_formats:
        errors.append(f"format_id {project.format_id!r} is not in allowed_formats {policy.allowed_formats}.")

    evaluated_rules.append("template")
    if policy.allowed_templates and project.template_id not in policy.allowed_templates:
        errors.append(f"template_id {project.template_id!r} is not in allowed_templates {policy.allowed_templates}.")

    evaluated_rules.append("language")
    if project.language not in channel.supported_languages:
        errors.append(
            f"language {project.language!r} is not in channel {channel.channel_id!r} supported_languages "
            f"{channel.supported_languages}."
        )
    if policy.allowed_languages and project.language not in policy.allowed_languages:
        errors.append(f"language {project.language!r} is not in allowed_languages {policy.allowed_languages}.")

    evaluated_rules.append("export_targets")
    if policy.allowed_export_targets:
        disallowed = [target for target in project.export_targets if target not in policy.allowed_export_targets]
        if disallowed:
            errors.append(f"export_targets {disallowed} are not in allowed_export_targets {policy.allowed_export_targets}.")

    evaluated_rules.append("evidence_blocked")
    if evidence_summary.blocked > 0:
        errors.append(f"{evidence_summary.blocked} evidence record(s) are blocked; blocked material is never allowed.")

    evaluated_rules.append("evidence_verified")
    if policy.require_verified_evidence and evidence_summary.total > evidence_summary.verified:
        unverified = evidence_summary.total - evidence_summary.verified
        errors.append(f"{unverified} evidence record(s) are not verified but require_verified_evidence is true.")

    evaluated_rules.append("evidence_review_required")
    if not policy.allow_review_required_assets and evidence_summary.review_required > 0:
        errors.append(
            f"{evidence_summary.review_required} evidence record(s) require review and "
            "allow_review_required_assets is false."
        )

    evaluated_rules.append("evidence_unknown_license")
    if not policy.allow_unknown_license and evidence_summary.unknown > 0:
        errors.append(f"{evidence_summary.unknown} evidence record(s) have unknown license status.")

    metadata = project.metadata or {}

    evaluated_rules.append("maximum_duration_seconds")
    if policy.maximum_duration_seconds is not None:
        duration = metadata.get("duration_seconds")
        if duration is None:
            warnings.append("duration_seconds not present in project metadata; skipping maximum_duration_seconds check.")
        elif float(duration) > float(policy.maximum_duration_seconds):
            errors.append(f"duration_seconds {duration} exceeds maximum_duration_seconds {policy.maximum_duration_seconds}.")

    evaluated_rules.append("minimum_resolution")
    if policy.minimum_resolution:
        resolution = metadata.get("resolution")
        if not resolution:
            warnings.append("resolution not present in project metadata; skipping minimum_resolution check.")
        elif not _check_resolution_at_least(resolution, policy.minimum_resolution):
            errors.append(f"resolution {resolution} is below minimum_resolution {policy.minimum_resolution}.")

    evaluated_rules.append("preferred_resolution")
    if policy.preferred_resolution:
        resolution = metadata.get("resolution")
        if not resolution:
            warnings.append("resolution not present in project metadata; skipping preferred_resolution check.")
        elif resolution != policy.preferred_resolution:
            warnings.append(f"resolution {resolution} does not match preferred_resolution {policy.preferred_resolution}.")

    for flag_name, requirement in (
        ("require_voiceover", "has_voiceover"),
        ("require_music", "has_music"),
        ("require_subtitles", "has_subtitles"),
        ("require_manual_qc", "manual_qc_passed"),
    ):
        evaluated_rules.append(flag_name)
        if getattr(policy, flag_name):
            value = metadata.get(requirement)
            if value is None:
                warnings.append(f"{requirement} not present in project metadata; skipping {flag_name} check.")
            elif not value:
                errors.append(f"{flag_name} is true but project metadata {requirement} is false.")

    return ValidationResult(allowed=not errors, errors=errors, warnings=warnings, evaluated_rules=evaluated_rules)
