from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from src.audio.narration_models import NarrationRequest, build_narration_request_from_scenes
from src.audio.tts.models import VoiceProfile
from src.audio.voice_policy import AUDIO_POLICY_DEFAULTS, VoicePolicy, resolve_voice_policy, voice_policy_from_channel_config
from src.audio.voice_profile_registry import lookup_profile
# Re-exported on purpose: load_voice_profile_for_channel() propagates it, and callers
# have always been able to catch it from here.
from src.audio.voice_profile_registry import VoiceProfileRegistryError as VoiceProfileRegistryError
from src.audio.voice_workflow import VoiceApproval, voice_paths
from src.localization.resolver import COMPAT_DEFAULT_VOICE_PROFILE

if TYPE_CHECKING:  # pragma: no cover - import only for the annotation
    from src.localization.models import ResolvedLocalization

# News-to-Short carries no production_catalog ids of its own; these are the ones its
# rendered output actually matches (see resolve_voice_policy_for_channel below).
NEWS_TEMPLATE_ID = "fullscreen_voiceover_v1"
NEWS_FORMAT_ID = "vertical_short"


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

    The lookup itself now lives in
    ``src.audio.voice_profile_registry.lookup_profile`` so that this function, the
    UI layer and ``src.localization`` all use one implementation; the precedence
    chain (override → channel default → "ru_dom") stays here, unchanged.
    """
    query = profile_override or (channel_voice_config or {}).get("voice_profile") or COMPAT_DEFAULT_VOICE_PROFILE
    return lookup_profile(channel_id, query, allow_global=bool(profile_override))


def resolve_localization_for_channel(
    *,
    channel_id: str,
    language: str,
    project_root: str | Path | None = None,
    project_id: str = "",
    projects_dir: str | Path | None = None,
    projects_fallback_dirs: tuple[str | Path, ...] | list[str | Path] = (),
    channels_dir: str | Path | None = None,
    template_id: str = NEWS_TEMPLATE_ID,
    format_id: str = NEWS_FORMAT_ID,
    voice_profile_override: str | None = None,
    voice_provider_override: str | None = None,
    manual_audio_path: str = "",
    script_path: str = "",
) -> "ResolvedLocalization | None":
    """Compatibility wrapper: one resolved localization, or ``None`` if this channel
    cannot be resolved at all.

    News jobs carry no production_catalog template_id, so the same assumption
    ``resolve_voice_policy_for_channel`` already documents is applied here:
    News-to-Short's output is the ``fullscreen_voiceover_v1`` contract.

    Returns ``None`` instead of raising when the channel is unknown to the resolver
    (a directory with neither ``channel.json`` nor ``channel_config.json``). The old
    readers treated that as "no configuration" and kept going
    (``_load_channel_config`` returns ``{}``), so callers fall back to the legacy
    path rather than a channel that used to work starting to fail.
    """
    from src.config_resolver import ConfigResolutionError
    from src.localization import resolve_localization

    try:
        return resolve_localization(
            channel_id=channel_id,
            template_id=template_id,
            format_id=format_id,
            language=language,
            localization_id=language,
            project_id=project_id,
            project_root=project_root,
            projects_dir=projects_dir,
            projects_fallback_dirs=projects_fallback_dirs,
            channels_dir=channels_dir,
            script_path=script_path,
            manual_audio_path=manual_audio_path,
            voice_profile_override=voice_profile_override or "",
            voice_provider_override=voice_provider_override or "",
        )
    except ConfigResolutionError:
        return None


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
    format_id: str = NEWS_FORMAT_ID,
    template_id: str = NEWS_TEMPLATE_ID,
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
