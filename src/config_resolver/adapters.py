"""Compatibility adapters: a ResolvedConfig in the shape an existing consumer expects.

These exist so consumers can migrate one at a time instead of in one sweep. Nothing in
the pipeline calls them yet - stage D1 introduces the resolver and proves it agrees
with the current readers; stage D2 is where call sites start using it.

The proof that they agree lives in ``tests/test_config_resolver_parity.py``: for every
channel on disk, ``to_voice_policy(resolve_config(...))`` must equal
``src.news.voice_adapter.resolve_voice_policy_for_channel(...)`` field for field.
"""

from __future__ import annotations

from typing import Any

from . import keys as k
from .models import ResolvedConfig


def to_voice_policy(resolved: ResolvedConfig) -> Any:
    """The same ``VoicePolicy`` the voice stage builds today, from resolved values.

    Only the fields the resolver actually knows about are set; everything else keeps
    its ``VoicePolicy`` dataclass default, exactly as ``VoicePolicy.from_dict`` would
    leave it when a layer does not mention a field.
    """
    from src.audio.voice_policy import VoicePolicy

    mapping = {
        "enabled": k.KEY_VOICE_ENABLED,
        "required": k.KEY_VOICE_REQUIRED,
        "provider": k.KEY_VOICE_PROVIDER,
        "voice_profile": k.KEY_VOICE_PROFILE,
        "model_id": k.KEY_VOICE_MODEL_ID,
        "output_mode": k.KEY_VOICE_OUTPUT_MODE,
        "timing_mode": k.KEY_VOICE_TIMING_MODE,
        "approval_required": k.KEY_VOICE_APPROVAL_REQUIRED,
        "audition_required": k.KEY_VOICE_AUDITION_REQUIRED,
        "scene_level_generation": k.KEY_VOICE_SCENE_LEVEL,
        "fallback_policy": k.KEY_VOICE_FALLBACK_POLICY,
        "failure_policy": k.KEY_VOICE_FAILURE_POLICY,
        "output_format": k.KEY_VOICE_OUTPUT_FORMAT,
        "target_sample_rate": k.KEY_VOICE_SAMPLE_RATE,
        "target_channels": k.KEY_VOICE_CHANNELS,
        "speed": k.KEY_VOICE_SPEED,
        "provider_settings": k.KEY_VOICE_PROVIDER_SETTINGS,
    }
    data = {field: resolved.get(key) for field, key in mapping.items()}
    return VoicePolicy.from_dict({field: value for field, value in data.items() if value is not None})


def to_render_settings(resolved: ResolvedConfig) -> dict[str, Any]:
    """Frame geometry and rate, in the ``{"width", "height", "fps", "aspect_ratio"}``
    shape the renderers and ``NewsJob.resolution`` already use."""
    return {
        "width": resolved.get(k.KEY_WIDTH),
        "height": resolved.get(k.KEY_HEIGHT),
        "fps": resolved.get(k.KEY_FPS),
        "aspect_ratio": resolved.get(k.KEY_ASPECT_RATIO),
    }


def secret_presence(resolved: ResolvedConfig) -> dict[str, bool]:
    """``{key: configured}`` for every credential the resolver knows about.

    Values are booleans by construction - the resolver never holds the secret itself,
    so this cannot leak one.
    """
    return {key: bool(resolved.resolved(key).value) for key in k.SECRET_KEYS}


__all__ = ["secret_presence", "to_render_settings", "to_voice_policy"]
