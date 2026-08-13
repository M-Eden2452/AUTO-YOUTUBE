from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Any


OUTPUT_MODE_SINGLE_NARRATION = "single_narration"
OUTPUT_MODE_SCENE_AUDIO = "scene_audio"
OUTPUT_MODE_MANUAL_AUDIO = "manual_audio"
OUTPUT_MODE_DISABLED = "disabled"
OUTPUT_MODES = frozenset(
    {OUTPUT_MODE_SINGLE_NARRATION, OUTPUT_MODE_SCENE_AUDIO, OUTPUT_MODE_MANUAL_AUDIO, OUTPUT_MODE_DISABLED}
)

TIMING_MODE_NARRATION_DRIVEN = "narration_driven"
TIMING_MODE_VISUAL_DRIVEN = "visual_driven"
TIMING_MODE_FIXED_DURATION = "fixed_duration"
TIMING_MODE_ADAPTIVE = "adaptive"
TIMING_MODES = frozenset(
    {TIMING_MODE_NARRATION_DRIVEN, TIMING_MODE_VISUAL_DRIVEN, TIMING_MODE_FIXED_DURATION, TIMING_MODE_ADAPTIVE}
)

FALLBACK_POLICY_NONE = "none"
FALLBACK_POLICY_MANUAL_AUDIO = "manual_audio"
FALLBACK_POLICY_LOCAL_TTS = "local_tts"
FALLBACK_POLICY_LOCAL_STUB_ONLY_FOR_TESTS = "local_stub_only_for_tests"
FALLBACK_POLICIES = frozenset(
    {
        FALLBACK_POLICY_NONE,
        FALLBACK_POLICY_MANUAL_AUDIO,
        FALLBACK_POLICY_LOCAL_TTS,
        FALLBACK_POLICY_LOCAL_STUB_ONLY_FOR_TESTS,
    }
)


class VoicePolicyError(ValueError):
    """Raised for an invalid VoicePolicy field value."""


@dataclass
class VoicePolicy:
    enabled: bool = True
    required: bool = False
    provider: str = ""
    voice_profile: str = ""
    language: str = ""
    model_id: str = ""
    output_mode: str = OUTPUT_MODE_DISABLED
    timing_mode: str = TIMING_MODE_ADAPTIVE
    approval_required: bool = True
    audition_required: bool = True
    scene_level_generation: bool = False
    reuse_cache: bool = True
    pause_policy: dict[str, Any] = field(default_factory=dict)
    post_processing: dict[str, Any] = field(default_factory=dict)
    fallback_policy: str = FALLBACK_POLICY_NONE
    failure_policy: str = "block"
    output_format: str = "wav"
    target_sample_rate: int = 48000
    target_channels: int = 1
    loudness_target: float | None = None
    peak_limit: float | None = None
    speed: float | None = None
    provider_settings: dict[str, Any] = field(default_factory=dict)
    notes: str = ""

    def __post_init__(self) -> None:
        if self.output_mode not in OUTPUT_MODES:
            raise VoicePolicyError(f"output_mode must be one of {sorted(OUTPUT_MODES)}, got {self.output_mode!r}.")
        if self.timing_mode not in TIMING_MODES:
            raise VoicePolicyError(f"timing_mode must be one of {sorted(TIMING_MODES)}, got {self.timing_mode!r}.")
        if self.fallback_policy not in FALLBACK_POLICIES:
            raise VoicePolicyError(
                f"fallback_policy must be one of {sorted(FALLBACK_POLICIES)}, got {self.fallback_policy!r}."
            )

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "VoicePolicy":
        data = data or {}
        allowed = {f.name for f in dataclasses.fields(cls)}
        filtered = {key: value for key, value in data.items() if key in allowed and value is not None}
        return cls(**filtered)


# Keyed by TemplateDefinition.audio_policy_id (src/production_catalog/models.py).
# Deliberately kept out of src/production_catalog so that package never has to import
# src/audio - the catalog only stores the string id, this module owns what it means.
AUDIO_POLICY_DEFAULTS: dict[str, dict[str, Any]] = {
    "fullscreen_voiceover_default": {
        "enabled": True,
        "required": True,
        "output_mode": OUTPUT_MODE_SCENE_AUDIO,
        "timing_mode": TIMING_MODE_NARRATION_DRIVEN,
        "scene_level_generation": True,
        "approval_required": True,
        "audition_required": True,
        "fallback_policy": FALLBACK_POLICY_MANUAL_AUDIO,
        "failure_policy": "block",
        "output_format": "wav",
        "target_sample_rate": 48000,
        "target_channels": 1,
    },
    "story_card_no_voice": {
        "enabled": False,
        "required": False,
        "output_mode": OUTPUT_MODE_DISABLED,
        "timing_mode": TIMING_MODE_VISUAL_DRIVEN,
        "scene_level_generation": False,
        "fallback_policy": FALLBACK_POLICY_NONE,
    },
}


def _non_null(data: dict[str, Any] | None) -> dict[str, Any]:
    if not data:
        return {}
    return {key: value for key, value in data.items() if value is not None}


def resolve_voice_policy(
    *,
    channel_defaults: dict[str, Any] | None = None,
    template_defaults: dict[str, Any] | None = None,
    project_overrides: dict[str, Any] | None = None,
    localization_overrides: dict[str, Any] | None = None,
) -> VoicePolicy:
    """Resolve a VoicePolicy from the 4-layer precedence: channel < template/format < project < localization.

    Each layer is a plain dict of VoicePolicy field names (already normalized - see
    voice_policy_from_channel_config() for the adapter from the raw voices.yaml/
    channel_config.json shape). Layers are merged shallowly in order; a later layer's
    explicit (non-None) value always wins over an earlier one. Missing/None entries are
    skipped so a partial override layer never resets fields it doesn't mention.
    """
    merged: dict[str, Any] = {}
    for layer in (channel_defaults, template_defaults, project_overrides, localization_overrides):
        merged.update(_non_null(layer))
    return VoicePolicy.from_dict(merged)


def voice_policy_from_channel_config(
    channel_voice_config: dict[str, Any] | None,
    voice_workflow_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Adapt the existing channel_config.json ``"voice"``/``"voice_workflow"`` shape
    (see config/channels/nature_science_news_ru/channel_config.json) into a normalized dict of
    VoicePolicy field overrides, without requiring any change to that file's shape."""
    voice_cfg = channel_voice_config or {}
    workflow_cfg = voice_workflow_config or {}
    normalized: dict[str, Any] = {
        "provider": voice_cfg.get("provider"),
        "voice_profile": voice_cfg.get("voice_profile"),
        "model_id": voice_cfg.get("model_id", voice_cfg.get("model")),
        "provider_settings": voice_cfg.get("settings"),
        "approval_required": workflow_cfg.get("paid_tts_requires_approval"),
        "audition_required": workflow_cfg.get("audition_requires_approval"),
        "speed": (voice_cfg.get("settings") or {}).get("speed"),
    }
    never_auto_fallback = workflow_cfg.get("never_auto_fallback_to_paid")
    if never_auto_fallback is not None:
        normalized["fallback_policy"] = FALLBACK_POLICY_NONE if never_auto_fallback else FALLBACK_POLICY_MANUAL_AUDIO
    return _non_null(normalized)
