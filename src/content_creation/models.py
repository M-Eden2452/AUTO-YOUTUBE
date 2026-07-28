from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Any


class ContentCreationError(ValueError):
    """Raised for invalid ContentCreationRequest input, an unsupported format/template
    combination, or a classified/anticipated failure (bad URL, article-fetch network
    error, invalid file path) that a caller should show as a clean message rather than
    a traceback.

    reason: short machine-readable tag (e.g. "search_engine_url", "http_429",
    "timeout", "connection_error", "invalid_content", "empty_article",
    "unsupported_extension", "not_found") - lets CLI/wizard callers offer
    context-appropriate next actions without string-matching the message.
    retryable: whether re-attempting the same request might succeed (network
    hiccups) vs. requiring the user to change their input (bad URL, missing file).
    """

    def __init__(self, message: str, *, reason: str = "generic", retryable: bool = False) -> None:
        super().__init__(message)
        self.reason = reason
        self.retryable = retryable


@dataclass
class VoiceRequestConfig:
    """Voice/audio selection for a create request.

    provider: "disabled" | "elevenlabs" | "audio_file" (only providers that are
    actually registered with the canonical TTSProviderManager - see
    src.content_creation.capabilities.list_voice_providers()).
    mode: src.audio.voice_policy OUTPUT_MODE_* value
      ("scene_audio" | "single_narration" | "manual_audio" | "disabled").
    profile: voice_profile id or an alias/display name (e.g. "ru_dom" or "Дом"),
      resolved through src.audio.voice_profile_registry.VoiceProfileRegistry.
    """

    provider: str = "disabled"
    profile: str = ""
    mode: str = "disabled"
    audio_file: str = ""
    approve_paid_generation: bool = False

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass
class SubtitleRequestConfig:
    """style must be one of src.content_creation.capabilities.list_subtitle_styles() ids."""

    style: str = "disabled"

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass
class MusicRequestConfig:
    """mode must be one of src.content_creation.capabilities.list_music_options() ids."""

    mode: str = "disabled"
    path: str = ""
    volume: float = 0.10

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass
class TimingRequestConfig:
    """mode is a src.audio.voice_policy TIMING_MODE_* value, or empty to use the template default."""

    mode: str = ""
    fixed_duration_sec: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass
class RenderRequestConfig:
    quality: str = "default"
    resolution: str = ""

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass
class ExecutionFlags:
    dry_run: bool = False
    prepare_only: bool = False
    resume: bool = False
    until_stage: str = ""
    stage: str = ""
    # Re-run an already-completed news_to_short stage instead of skipping it on
    # resume. False everywhere by default and equivalent to pipeline.py's
    # --force-stage, exposed here so a repair resume never needs the legacy CLI.
    force_stage: bool = False

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass
class ContentCreationRequest:
    """The single request shape accepted by both the flag-based `create` command
    and the interactive `wizard`, per docs/handoff Stage 2E. Coordinates existing
    foundation components (ProjectFactory/ChannelRegistry, production_catalog,
    VoiceProfileRegistry, news_to_short pipeline) - it never implements TTS, asset
    search, subtitles, rendering, licensing, or project storage itself.
    """

    project_id: str = ""
    title: str = ""
    source_url: str = ""
    script_path: str = ""
    pasted_script: str = ""
    content_input_mode: str = ""  # "" (legacy/unspecified) | topic | article_url | pasted_script | script_file
    channel_id: str = ""
    format_id: str = ""
    template_id: str = ""
    language: str = "ru"
    text: dict[str, str] = field(default_factory=dict)
    source_asset_path: str = ""
    topic: str = ""
    target_duration_sec: int | None = None
    voice: VoiceRequestConfig = field(default_factory=VoiceRequestConfig)
    subtitles: SubtitleRequestConfig = field(default_factory=SubtitleRequestConfig)
    music: MusicRequestConfig = field(default_factory=MusicRequestConfig)
    timing: TimingRequestConfig = field(default_factory=TimingRequestConfig)
    render: RenderRequestConfig = field(default_factory=RenderRequestConfig)
    execution: ExecutionFlags = field(default_factory=ExecutionFlags)
    # Explicit per-scene "what to show", keyed by 1-based scene number or scene_id.
    # The single supported entry point for a visual brief - see the `--visual-brief`
    # flag, which reads one JSON file into this field. Optional: without it every
    # command behaves exactly as before.
    visual_briefs: dict[str, dict[str, Any]] = field(default_factory=dict)
    # Empty values keep a stored setting on resume and resolve to strict/none for a
    # newly created project. Autonomous completion is never enabled implicitly.
    completion_mode: str = ""
    script_adaptation: str = ""
    project_overrides: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "title": self.title,
            "source_url": self.source_url,
            "script_path": self.script_path,
            "pasted_script": self.pasted_script,
            "content_input_mode": self.content_input_mode,
            "channel_id": self.channel_id,
            "format_id": self.format_id,
            "template_id": self.template_id,
            "language": self.language,
            "text": dict(self.text),
            "source_asset_path": self.source_asset_path,
            "topic": self.topic,
            "target_duration_sec": self.target_duration_sec,
            "visual_briefs": {key: dict(value) for key, value in self.visual_briefs.items()},
            "completion_mode": self.completion_mode,
            "script_adaptation": self.script_adaptation,
            "voice": self.voice.to_dict(),
            "subtitles": self.subtitles.to_dict(),
            "music": self.music.to_dict(),
            "timing": self.timing.to_dict(),
            "render": self.render.to_dict(),
            "execution": self.execution.to_dict(),
            "project_overrides": dict(self.project_overrides),
        }


@dataclass
class ContentCreationResult:
    status: str
    project_id: str
    project_root: str
    stages: list[dict[str, Any]] = field(default_factory=list)
    output_paths: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)
    quality_report: dict[str, Any] = field(default_factory=dict)
    rerun_commands: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "project_id": self.project_id,
            "project_root": self.project_root,
            "stages": list(self.stages),
            "output_paths": dict(self.output_paths),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "evidence": dict(self.evidence),
            "quality_report": dict(self.quality_report),
            "rerun_commands": list(self.rerun_commands),
        }
