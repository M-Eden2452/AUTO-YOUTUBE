from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


SCHEMA_VERSION = 1


class ProjectFoundationError(ValueError):
    """Raised for invalid Project/Channel/Evidence Foundation data."""


PROJECT_STATUS_DRAFT = "draft"
PROJECT_STATUS_PREPARED = "prepared"
PROJECT_STATUS_ASSETS_READY = "assets_ready"
PROJECT_STATUS_AUDIO_READY = "audio_ready"
PROJECT_STATUS_RENDER_READY = "render_ready"
PROJECT_STATUS_RENDERED = "rendered"
PROJECT_STATUS_QC_PASSED = "qc_passed"
PROJECT_STATUS_EXPORTED = "exported"
PROJECT_STATUS_ARCHIVED = "archived"
PROJECT_STATUS_FAILED = "failed"

PROJECT_STATUSES = (
    PROJECT_STATUS_DRAFT,
    PROJECT_STATUS_PREPARED,
    PROJECT_STATUS_ASSETS_READY,
    PROJECT_STATUS_AUDIO_READY,
    PROJECT_STATUS_RENDER_READY,
    PROJECT_STATUS_RENDERED,
    PROJECT_STATUS_QC_PASSED,
    PROJECT_STATUS_EXPORTED,
    PROJECT_STATUS_ARCHIVED,
    PROJECT_STATUS_FAILED,
)

VERIFICATION_VERIFIED = "verified"
VERIFICATION_REVIEW_REQUIRED = "review_required"
VERIFICATION_BLOCKED = "blocked"
VERIFICATION_UNKNOWN = "unknown"

VERIFICATION_STATUSES = (
    VERIFICATION_VERIFIED,
    VERIFICATION_REVIEW_REQUIRED,
    VERIFICATION_BLOCKED,
    VERIFICATION_UNKNOWN,
)

# What kind of material an evidence record describes. src.projects.rights re-exports
# these so the unified rights report and the stored records cannot drift apart.
MEDIA_ROLE_VISUAL = "visual"
MEDIA_ROLE_MUSIC = "music"
MEDIA_ROLE_VOICE = "voice"
MEDIA_ROLE_OTHER = "other"

MEDIA_ROLES = (MEDIA_ROLE_VISUAL, MEDIA_ROLE_MUSIC, MEDIA_ROLE_VOICE, MEDIA_ROLE_OTHER)

# EvidenceRecord's own version, separate from the project/channel SCHEMA_VERSION:
# v2 added the visual-provenance fields (see EvidenceRecord). Bumping the shared
# SCHEMA_VERSION instead would have re-versioned ProjectManifest and ChannelProfile,
# whose formats did not change.
EVIDENCE_RECORD_SCHEMA_VERSION = 2

# Recorded in EvidenceRecord.source_type: how the material reached the project.
SOURCE_TYPE_USER_SUPPLIED = "user_supplied"
SOURCE_TYPE_PROVIDER = "provider"

# EvidenceRecord.provider for a file the user pointed at on their own disk. It is a
# statement about *where the file came from*, never a claim about rights.
PROVIDER_USER_SUPPLIED = "user_supplied"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _as_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str | bytes):
        return [str(value)]
    return [str(item) for item in value]


def _require_non_empty_str(value: Any, *, field_name: str, owner: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ProjectFoundationError(f"{owner}: {field_name} is required and cannot be empty.")
    return text


@dataclass
class ChannelBranding:
    channel_name: str = ""
    logo_path: str = ""
    primary_font: str = ""
    secondary_font: str = ""
    default_music_policy: str = "optional"
    default_voice_id: str = ""
    visual_style_notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "channel_name": self.channel_name,
            "logo_path": self.logo_path,
            "primary_font": self.primary_font,
            "secondary_font": self.secondary_font,
            "default_music_policy": self.default_music_policy,
            "default_voice_id": self.default_voice_id,
            "visual_style_notes": self.visual_style_notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> ChannelBranding:
        data = data or {}
        return cls(
            channel_name=str(data.get("channel_name", "")),
            logo_path=str(data.get("logo_path", "")),
            primary_font=str(data.get("primary_font", "")),
            secondary_font=str(data.get("secondary_font", "")),
            default_music_policy=str(data.get("default_music_policy", "optional")),
            default_voice_id=str(data.get("default_voice_id", "")),
            visual_style_notes=str(data.get("visual_style_notes", "")),
        )


@dataclass
class ChannelProfile:
    channel_id: str
    display_name: str = ""
    description: str = ""
    default_language: str = "ru"
    supported_languages: list[str] = field(default_factory=lambda: ["ru"])
    default_application: str = ""
    default_format: str = ""
    default_template: str = ""
    export_targets: list[str] = field(default_factory=list)
    branding: ChannelBranding = field(default_factory=ChannelBranding)
    output_policy: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        self.channel_id = _require_non_empty_str(self.channel_id, field_name="channel_id", owner="ChannelProfile")
        self.display_name = str(self.display_name or self.channel_id)
        self.description = str(self.description or "")
        self.default_language = str(self.default_language or "ru")
        self.supported_languages = _as_str_list(self.supported_languages) or [self.default_language]
        if self.default_language not in self.supported_languages:
            self.supported_languages = [self.default_language, *self.supported_languages]
        self.default_application = str(self.default_application or "")
        self.default_format = str(self.default_format or "")
        self.default_template = str(self.default_template or "")
        self.export_targets = _as_str_list(self.export_targets)
        if isinstance(self.branding, dict):
            self.branding = ChannelBranding.from_dict(self.branding)
        elif self.branding is None:
            self.branding = ChannelBranding()
        if not isinstance(self.output_policy, dict):
            self.output_policy = {}
        self.created_at = str(self.created_at or utc_now_iso())
        self.updated_at = str(self.updated_at or self.created_at)
        self.schema_version = int(self.schema_version or SCHEMA_VERSION)

    def to_dict(self) -> dict[str, Any]:
        return {
            "channel_id": self.channel_id,
            "display_name": self.display_name,
            "description": self.description,
            "default_language": self.default_language,
            "supported_languages": list(self.supported_languages),
            "default_application": self.default_application,
            "default_format": self.default_format,
            "default_template": self.default_template,
            "export_targets": list(self.export_targets),
            "branding": self.branding.to_dict(),
            "output_policy": dict(self.output_policy),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ChannelProfile:
        if not isinstance(data, dict):
            raise ProjectFoundationError("ChannelProfile.from_dict expects a dict.")
        return cls(
            channel_id=data.get("channel_id", ""),
            display_name=data.get("display_name", ""),
            description=data.get("description", ""),
            default_language=data.get("default_language", "ru"),
            supported_languages=data.get("supported_languages", []),
            default_application=data.get("default_application", ""),
            default_format=data.get("default_format", ""),
            default_template=data.get("default_template", ""),
            export_targets=data.get("export_targets", []),
            branding=data.get("branding", {}),
            output_policy=data.get("output_policy", {}),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            schema_version=data.get("schema_version", SCHEMA_VERSION),
        )


@dataclass
class ProjectManifest:
    project_id: str
    title: str = ""
    channel_id: str = ""
    application_id: str = ""
    format_id: str = ""
    template_id: str = ""
    language: str = "ru"
    export_targets: list[str] = field(default_factory=list)
    status: str = PROJECT_STATUS_DRAFT
    source_type: str = "manual"
    source_reference: str = ""
    project_root: str = ""
    localization_root: str = ""
    evidence_root: str = ""
    created_at: str = ""
    updated_at: str = ""
    schema_version: int = SCHEMA_VERSION
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.project_id = _require_non_empty_str(self.project_id, field_name="project_id", owner="ProjectManifest")
        self.title = str(self.title or self.project_id)
        self.channel_id = str(self.channel_id or "")
        self.application_id = str(self.application_id or "")
        self.format_id = str(self.format_id or "")
        self.template_id = str(self.template_id or "")
        self.language = str(self.language or "ru")
        self.export_targets = _as_str_list(self.export_targets)
        if self.status not in PROJECT_STATUSES:
            raise ProjectFoundationError(
                f"ProjectManifest {self.project_id!r}: unknown status {self.status!r}. "
                f"Must be one of {list(PROJECT_STATUSES)}."
            )
        self.source_type = str(self.source_type or "manual")
        self.source_reference = str(self.source_reference or "")
        self.project_root = str(self.project_root or f"projects/{self.project_id}")
        self.localization_root = str(self.localization_root or f"{self.project_root}/localizations/{self.language}")
        self.evidence_root = str(self.evidence_root or f"{self.project_root}/evidence")
        self.created_at = str(self.created_at or utc_now_iso())
        self.updated_at = str(self.updated_at or self.created_at)
        self.schema_version = int(self.schema_version or SCHEMA_VERSION)
        if not isinstance(self.metadata, dict):
            raise ProjectFoundationError(f"ProjectManifest {self.project_id!r}: metadata must be a dict.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "title": self.title,
            "channel_id": self.channel_id,
            "application_id": self.application_id,
            "format_id": self.format_id,
            "template_id": self.template_id,
            "language": self.language,
            "export_targets": list(self.export_targets),
            "status": self.status,
            "source_type": self.source_type,
            "source_reference": self.source_reference,
            "project_root": self.project_root,
            "localization_root": self.localization_root,
            "evidence_root": self.evidence_root,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "schema_version": self.schema_version,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProjectManifest:
        if not isinstance(data, dict):
            raise ProjectFoundationError("ProjectManifest.from_dict expects a dict.")
        return cls(
            project_id=data.get("project_id", ""),
            title=data.get("title", ""),
            channel_id=data.get("channel_id", ""),
            application_id=data.get("application_id", ""),
            format_id=data.get("format_id", ""),
            template_id=data.get("template_id", ""),
            language=data.get("language", "ru"),
            export_targets=data.get("export_targets", []),
            status=data.get("status", PROJECT_STATUS_DRAFT),
            source_type=data.get("source_type", "manual"),
            source_reference=data.get("source_reference", ""),
            project_root=data.get("project_root", ""),
            localization_root=data.get("localization_root", ""),
            evidence_root=data.get("evidence_root", ""),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            schema_version=data.get("schema_version", SCHEMA_VERSION),
            metadata=data.get("metadata", {}),
        )


@dataclass
class EvidenceRecord:
    """One rights-bearing material, described well enough to be auditable.

    Fields below ``schema_version`` v1 (evidence_id ... verification_status) are the
    original set. The v2 additions exist for one reason: a real production workflow
    finally writes evidence (Story Card), and the material it describes is a visual
    asset whose provenance is already modelled elsewhere in this repository. The
    extension is therefore not open-ended - it is exactly the set of facts that
    ``src.projects.rights.RightsItem`` (the unified rights report) and
    ``src.assets.models.AssetLicense``/``AssetProvenance`` (the canonical provider
    contract) already carry and that a v1 record could not express without loss.

    Deliberately *not* added: a second ``rights_status``. ``verification_status``
    already is this record's rights status; duplicating it would let the two disagree.

    v1 records stay readable unchanged - every new field is optional, and
    ``allowed_for_render``/``review_required`` fall back to what the unified report
    previously derived from ``verification_status`` when they are absent.
    """

    evidence_id: str
    asset_id: str = ""
    source_url: str = ""
    provider: str = ""
    author: str = ""
    license_name: str = ""
    license_url: str = ""
    commercial_use_status: str = "unknown"
    attribution_required: bool = False
    attribution_text: str = ""
    acquired_at: str = ""
    checksum_sha256: str = ""
    local_path: str = ""
    original_filename: str = ""
    proof_files: list[str] = field(default_factory=list)
    notes: str = ""
    verification_status: str = VERIFICATION_UNKNOWN
    # --- schema v2 -------------------------------------------------------
    media_role: str = MEDIA_ROLE_OTHER
    media_type: str = ""
    source_type: str = ""
    provider_asset_id: str = ""
    download_url: str = ""
    author_url: str = ""
    allowed_for_render: bool = False
    review_required: bool = False
    provenance: dict[str, Any] = field(default_factory=dict)
    technical_validation: dict[str, Any] = field(default_factory=dict)
    schema_version: int = EVIDENCE_RECORD_SCHEMA_VERSION

    def __post_init__(self) -> None:
        self.evidence_id = _require_non_empty_str(self.evidence_id, field_name="evidence_id", owner="EvidenceRecord")
        self.asset_id = str(self.asset_id or "")
        self.source_url = str(self.source_url or "")
        self.provider = str(self.provider or "")
        self.author = str(self.author or "")
        self.license_name = str(self.license_name or "")
        self.license_url = str(self.license_url or "")
        self.commercial_use_status = str(self.commercial_use_status or "unknown")
        self.attribution_required = bool(self.attribution_required)
        self.attribution_text = str(self.attribution_text or "")
        self.acquired_at = str(self.acquired_at or "")
        self.checksum_sha256 = str(self.checksum_sha256 or "")
        self.local_path = str(self.local_path or "")
        self.original_filename = str(self.original_filename or "")
        self.proof_files = _as_str_list(self.proof_files)
        self.notes = str(self.notes or "")
        if self.verification_status not in VERIFICATION_STATUSES:
            raise ProjectFoundationError(
                f"EvidenceRecord {self.evidence_id!r}: unknown verification_status {self.verification_status!r}. "
                f"Must be one of {list(VERIFICATION_STATUSES)}."
            )
        self.media_role = str(self.media_role or MEDIA_ROLE_OTHER)
        if self.media_role not in MEDIA_ROLES:
            # Raised rather than coerced, for the same reason verification_status is:
            # a typo here would silently mis-file a material in the rights report.
            raise ProjectFoundationError(
                f"EvidenceRecord {self.evidence_id!r}: unknown media_role {self.media_role!r}. "
                f"Must be one of {list(MEDIA_ROLES)}."
            )
        self.media_type = str(self.media_type or "")
        self.source_type = str(self.source_type or "")
        self.provider_asset_id = str(self.provider_asset_id or "")
        self.download_url = str(self.download_url or "")
        self.author_url = str(self.author_url or "")
        self.allowed_for_render = bool(self.allowed_for_render)
        self.review_required = bool(self.review_required)
        self.provenance = dict(self.provenance or {})
        self.technical_validation = dict(self.technical_validation or {})
        self.schema_version = int(self.schema_version or EVIDENCE_RECORD_SCHEMA_VERSION)

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "asset_id": self.asset_id,
            "source_url": self.source_url,
            "provider": self.provider,
            "author": self.author,
            "license_name": self.license_name,
            "license_url": self.license_url,
            "commercial_use_status": self.commercial_use_status,
            "attribution_required": self.attribution_required,
            "attribution_text": self.attribution_text,
            "acquired_at": self.acquired_at,
            "checksum_sha256": self.checksum_sha256,
            "local_path": self.local_path,
            "original_filename": self.original_filename,
            "proof_files": list(self.proof_files),
            "notes": self.notes,
            "verification_status": self.verification_status,
            "media_role": self.media_role,
            "media_type": self.media_type,
            "source_type": self.source_type,
            "provider_asset_id": self.provider_asset_id,
            "download_url": self.download_url,
            "author_url": self.author_url,
            "allowed_for_render": self.allowed_for_render,
            "review_required": self.review_required,
            "provenance": dict(self.provenance),
            "technical_validation": dict(self.technical_validation),
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvidenceRecord:
        if not isinstance(data, dict):
            raise ProjectFoundationError("EvidenceRecord.from_dict expects a dict.")
        verification_status = data.get("verification_status", VERIFICATION_UNKNOWN)
        return cls(
            evidence_id=data.get("evidence_id", ""),
            asset_id=data.get("asset_id", ""),
            source_url=data.get("source_url", ""),
            provider=data.get("provider", ""),
            author=data.get("author", ""),
            license_name=data.get("license_name", ""),
            license_url=data.get("license_url", ""),
            commercial_use_status=data.get("commercial_use_status", "unknown"),
            attribution_required=data.get("attribution_required", False),
            attribution_text=data.get("attribution_text", ""),
            acquired_at=data.get("acquired_at", ""),
            checksum_sha256=data.get("checksum_sha256", ""),
            local_path=data.get("local_path", ""),
            original_filename=data.get("original_filename", ""),
            proof_files=data.get("proof_files", []),
            notes=data.get("notes", ""),
            verification_status=verification_status,
            media_role=data.get("media_role", MEDIA_ROLE_OTHER),
            media_type=data.get("media_type", ""),
            source_type=data.get("source_type", ""),
            provider_asset_id=data.get("provider_asset_id", ""),
            download_url=data.get("download_url", ""),
            author_url=data.get("author_url", ""),
            # A v1 record has neither flag. Falling back to what the unified rights
            # report used to derive from the status keeps such records reading exactly
            # as they did before this schema existed.
            allowed_for_render=data.get("allowed_for_render", verification_status == VERIFICATION_VERIFIED),
            review_required=data.get("review_required", verification_status == VERIFICATION_REVIEW_REQUIRED),
            provenance=data.get("provenance", {}),
            technical_validation=data.get("technical_validation", {}),
            schema_version=data.get("schema_version", EVIDENCE_RECORD_SCHEMA_VERSION),
        )


@dataclass
class EvidenceSummary:
    total: int = 0
    verified: int = 0
    review_required: int = 0
    blocked: int = 0
    unknown: int = 0

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)
