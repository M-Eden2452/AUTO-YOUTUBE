from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.audio.narration_models import NarrationRequest, build_narration_request_from_scenes
from src.audio.tts.models import VoiceProfile
from src.audio.voice_policy import AUDIO_POLICY_DEFAULTS, VoicePolicy, resolve_voice_policy, voice_policy_from_channel_config
from src.audio.voice_profile_registry import VoiceProfileRegistry, VoiceProfileRegistryError
from src.audio.voice_workflow import VoiceApproval, voice_paths


def resolve_voice_policy_for_channel(
    channel_voice_config: dict[str, Any] | None,
    channel_workflow_config: dict[str, Any] | None = None,
) -> VoicePolicy:
    """News-to-Short's rendered output (fullscreen footage, no big text overlay) matches
    the fullscreen_voiceover_v1 template contract, so its template-layer policy defaults
    are used even though News jobs don't carry a production_catalog template_id today."""
    return resolve_voice_policy(
        channel_defaults=voice_policy_from_channel_config(channel_voice_config, channel_workflow_config),
        template_defaults=AUDIO_POLICY_DEFAULTS.get("fullscreen_voiceover_default"),
    )


def load_voice_profile_for_channel(
    channel_id: str,
    channel_voice_config: dict[str, Any] | None,
    *,
    profile_override: str | None = None,
) -> VoiceProfile:
    """Resolve a voice profile for a channel.

    profile_override (e.g. an explicit --voice-profile from the unified
    content-creation CLI/wizard) takes priority over the channel's own
    configured default and, when given, is also resolved across every
    channel's voices.yaml - not just this one - so a channel with no
    voices.yaml of its own (e.g. nature_pulse) can still use a profile that is
    genuinely registered elsewhere (e.g. ru_dom in nature_science_news_ru's
    voices.yaml) instead of raising FileNotFoundError. Without an override,
    behavior is unchanged: this channel's own voices.yaml is required.
    """
    query = profile_override or (channel_voice_config or {}).get("voice_profile") or "ru_dom"
    voices_path = Path("channels") / channel_id / "voices.yaml"
    if voices_path.is_file() or not profile_override:
        registry = VoiceProfileRegistry.from_yaml(voices_path)
        return registry.resolve(query)

    for candidate in sorted(Path("channels").glob("*/voices.yaml")):
        try:
            return VoiceProfileRegistry.from_yaml(candidate).resolve(query)
        except VoiceProfileRegistryError:
            continue
    raise VoiceProfileRegistryError(
        f"Could not resolve voice profile {query!r} for channel {channel_id!r}: it has no "
        "voices.yaml of its own, and no other channel's voices.yaml has this profile either."
    )


def load_approval(project_root: str | Path, language: str) -> VoiceApproval | None:
    path = voice_paths(project_root, language)["approval"]
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return VoiceApproval(**data)
    except (OSError, json.JSONDecodeError, TypeError):
        return None


def script_to_narration_request(
    *,
    script: dict[str, Any],
    project_root: str | Path,
    job_id: str,
    channel_id: str,
    language: str,
    policy: VoicePolicy,
    voice_profile: VoiceProfile,
    approval: VoiceApproval | None,
    format_id: str = "vertical_short",
    template_id: str = "fullscreen_voiceover_v1",
) -> NarrationRequest:
    return build_narration_request_from_scenes(
        project_id=job_id,
        job_id=job_id,
        channel_id=channel_id,
        localization_id=language,
        language=language,
        format_id=format_id,
        template_id=template_id,
        voice_profile=voice_profile,
        policy=policy,
        scenes=script.get("scenes", []),
        full_text=script.get("narration_text", ""),
        approval=approval,
        output_root=project_root,
    )
