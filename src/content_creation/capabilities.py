from __future__ import annotations

from pathlib import Path
from typing import Any

from src.audio import voice_policy
from src.audio.tts.audio_file_provider import AudioFileProvider
from src.audio.tts.elevenlabs_provider import ElevenLabsProvider
from src.audio.voice_profile_registry import VoiceProfileRegistry
# Re-exported on purpose: resolve_voice_profile() below propagates it, and callers
# (src/content_creation/wizard.py) catch it without importing src.audio themselves.
from src.audio.voice_profile_registry import VoiceProfileRegistryError as VoiceProfileRegistryError
from src.production_catalog.catalog import get_default_catalog
from src.project_foundation.channels import ChannelRegistry
from src.project_foundation.models import ProjectFoundationError

# Legacy dev/test-only providers (src/voice_engine.py local_stub, MOSS-TTS-Nano) are
# intentionally NOT listed here: they are not TTSProvider subclasses registered with
# TTSProviderManager, and per CLAUDE.md must never be offered as a production voice
# option. See docs/implementation/global_adaptive_voice/MIGRATION_NOTES.md.
VOICE_PROVIDER_DISABLED = "disabled"


def _channels_root() -> Path:
    from src.config_resolver.paths import resolve_application_paths

    return resolve_application_paths().channels_root


def list_voice_providers() -> list[dict[str, Any]]:
    """Real, registered TTS providers plus the "disabled" pseudo-option.

    Sourced by instantiating the two TTSProvider subclasses that are actually
    registered together in src/news/voice_stage.py (ElevenLabsProvider,
    AudioFileProvider) - never a second hardcoded list.
    """
    elevenlabs = ElevenLabsProvider()
    audio_file = AudioFileProvider()
    return [
        {
            "provider_id": VOICE_PROVIDER_DISABLED,
            "display_name": "Без озвучки",
            "paid": False,
            "configured": True,
            "available": True,
            "supports_preflight": False,
            "supports_audition": False,
            "supports_full_generation": False,
            "output_formats": [],
            "production_ready": True,
            "status": "production",
        },
        {
            "provider_id": elevenlabs.name,
            "display_name": "ElevenLabs",
            "paid": elevenlabs.paid,
            "configured": bool(elevenlabs.api_key),
            "available": bool(elevenlabs.api_key),
            "supports_preflight": True,
            "supports_audition": True,
            "supports_full_generation": True,
            "output_formats": ["mp3_44100_128"],
            "production_ready": True,
            "status": "production",
        },
        {
            "provider_id": audio_file.name,
            "display_name": "Ручной WAV-файл",
            "paid": audio_file.paid,
            "configured": True,
            "available": True,
            "supports_preflight": False,
            "supports_audition": False,
            "supports_full_generation": True,
            "output_formats": ["wav"],
            "production_ready": True,
            "status": "production",
        },
    ]


def _voices_path(channel_id: str) -> Path:
    from src.audio.voice_profile_registry import channel_voices_path

    return channel_voices_path(channel_id)


def _global_voice_registries() -> list[Path]:
    """Every voices.yaml on disk, in a deterministic order.

    Mirrors the fallback src.news.voice_adapter.load_voice_profile_for_channel
    already performs at runtime: a channel with no voices.yaml of its own can still
    use a profile that is genuinely registered elsewhere. Keeping the two in sync
    matters - when they disagreed, the wizard cleared a profile that the pipeline
    would in fact have resolved, and the user's voice choice was silently dropped.
    Both now read the same helper in src.audio.voice_profile_registry.
    """
    from src.audio.voice_profile_registry import global_voices_paths

    return global_voices_paths()


def list_voice_profiles(channel_id: str, *, include_global: bool = True) -> list[dict[str, Any]]:
    """Voice profiles usable by a channel via the canonical VoiceProfileRegistry.

    A channel's own voices.yaml comes first. When it has none (e.g. story-card
    channels like nature_pulse) and include_global is set, profiles registered by
    other channels are offered instead - exactly the set the pipeline would accept
    as an explicit --voice-profile override. Each entry carries `source_channel_id`
    so a caller can show where the profile actually lives.
    """
    own_path = _voices_path(channel_id)
    sources: list[tuple[str, Path]] = []
    if own_path.is_file():
        sources.append((channel_id, own_path))
    elif include_global:
        sources.extend((path.parent.name, path) for path in _global_voice_registries())
    if not sources:
        return []
    profiles = []
    seen: set[str] = set()
    for source_channel_id, path in sources:
        registry = VoiceProfileRegistry.from_yaml(path)
        for profile_id, profile in registry.profiles().items():
            if profile_id in seen:
                continue
            seen.add(profile_id)
            profiles.append(_describe_profile(profile_id, profile, source_channel_id))
    return profiles


def _describe_profile(profile_id: str, profile: Any, source_channel_id: str) -> dict[str, Any]:
    aliases = [alias for alias, target in voice_profile_registry_aliases().items() if target == profile_id]
    return {
        "profile_id": profile_id,
        "display_name": profile.display_name,
        "aliases": aliases,
        "provider": profile.provider,
        "language": profile.language,
        "model_id": profile.model_id,
        "enabled": profile.enabled,
        "configured": bool(profile.voice_id),
        "source_channel_id": source_channel_id,
    }


def voice_profile_registry_aliases() -> dict[str, str]:
    from src.audio.voice_profile_registry import ALIASES

    return dict(ALIASES)


def resolve_voice_profile(channel_id: str, query: str) -> str:
    """Resolve a --voice-profile value (exact id, alias, or display name like "Дом")
    to a canonical profile_id.

    Resolution order is exactly the one src.news.voice_adapter.load_voice_profile_for_channel
    uses downstream: the channel's own voices.yaml first, then every other channel's.
    Before this matched, the UI layer rejected a profile that the pipeline would have
    accepted, so choosing a voice for a channel without its own voices.yaml silently
    produced a run with no narration. Keeping them in step is no longer a matter of
    discipline: both call the one implementation in
    src.audio.voice_profile_registry.lookup_profile.
    """
    from src.audio.voice_profile_registry import lookup_profile

    return lookup_profile(channel_id, query, allow_global=True).profile_id


# Only styles with a real, tested implementation are listed. src.subtitles is the sole
# real engine wired into a template (fullscreen_voiceover_v1 via news_to_short);
# src/news/subtitles.py is its adapter. "phrase" / "shorts_large" / "word_by_word" do
# not exist in the codebase (confirmed by repo-wide search) and are deliberately NOT
# listed here - see CLAUDE.md "не документировать выдуманные команды".
def list_subtitle_styles() -> list[dict[str, Any]]:
    from src.subtitles import SubtitlePolicy, resolve_subtitle_style

    documentary = resolve_subtitle_style(style_id="documentary")
    policy = SubtitlePolicy.from_style(documentary)
    return [
        {
            "style_id": "disabled",
            "display_name": "Без субтитров",
            "supported_formats": ["vertical_short", "longform", "horizontal_clip"],
            "renderer": None,
            "position": None,
            "max_lines": None,
            "max_characters": None,
            "timing_source": None,
            "status": "production",
        },
        {
            "style_id": "documentary",
            "display_name": "Документальные субтитры (burned-in)",
            "supported_formats": ["vertical_short"],
            "renderer": "src.subtitles.engine.build_subtitle_result",
            "position": "bottom_safe_zone",
            "max_lines": documentary.max_lines,
            "max_characters": policy.max_characters_per_cue,
            # Фактическая иерархия этапа Q3. word_timestamps в контракте есть, но их
            # сегодня не пишет ни один модуль репозитория, поэтому здесь их нет.
            "timing_source": "scene_timeline",
            "timing_source_fallbacks": ["legacy_planned"],
            "status": "targeted_tested",
            "notes": (
                "Тайминг берётся из реальной длительности озвучки через общий scene timeline "
                "(src.audio.scene_timeline). Текст — полная реплика сцены, разбитая по "
                "предложениям и пунктуации. Стиль читается из config/channels/<id>/subtitle_style.json. "
                "Потайминги отдельных слов не поддерживаются: их не пишет ни один провайдер."
            ),
        },
    ]


# Honest capability list for the templates in this catalog. local_file became really
# usable once src.audio.music_manifest started writing assets/music/music_manifest.json:
# src/news/final_renderer.py already looped, sidechain-ducked and mixed the bed, it just
# never had a manifest to read. It is marked targeted_tested, not production: the mix
# arguments are covered by tests, but no full live render with music has been produced yet.
def list_music_options() -> list[dict[str, Any]]:
    return [
        {
            "mode_id": "disabled",
            "display_name": "Без музыки",
            "status": "production",
        },
        {
            "mode_id": "local_file",
            "display_name": "Локальный файл",
            "status": "targeted_tested",
            "supported_templates": ["fullscreen_voiceover_v1"],
            "notes": (
                "Локальный трек подмешивается под озвучку с автоматическим ducking. "
                "Права на файл не проверяются автоматически - используйте только свою "
                "или лицензированную музыку."
            ),
        },
    ]


# channel_profile_type values, in the order the create workflows understand them.
CHANNEL_TYPE_PROJECT_FOUNDATION = "project_foundation"  # config/channels/<id>/channel.json
CHANNEL_TYPE_NEWS_CONFIG = "news_channel_config"  # channel_config.json with mode=news_to_short
CHANNEL_TYPE_LEGACY_PIPELINE = "legacy_video_pipeline"  # old pipeline.py --channel/--video profile

# Which create workflow can actually consume each channel shape. A legacy pipeline
# channel (quotes/psychology/survival/size_comparison) has a completely different
# schema - channel_name/video_format/obsidian_folder, no `mode`, no `voice` block, no
# voices.yaml - and is read by src/channel_loader.py, not by src/news or
# src/project_foundation. Offering it as a content_creator channel produced a run that
# could never generate voice; it is still listed (so nothing is hidden) but marked
# unusable so the wizard can filter it out.
_CHANNEL_TYPE_TEMPLATES: dict[str, list[str]] = {
    CHANNEL_TYPE_PROJECT_FOUNDATION: ["story_card_text_only_v1", "fullscreen_voiceover_v1"],
    CHANNEL_TYPE_NEWS_CONFIG: ["fullscreen_voiceover_v1"],
    CHANNEL_TYPE_LEGACY_PIPELINE: [],
}


def _classify_channel_config(path: Path) -> str:
    """news_to_short channel vs. legacy pipeline channel, by the config's own shape."""
    import json

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return CHANNEL_TYPE_LEGACY_PIPELINE
    if not isinstance(data, dict):
        return CHANNEL_TYPE_LEGACY_PIPELINE
    if str(data.get("mode", "")) == "news_to_short" or isinstance(data.get("voice"), dict):
        return CHANNEL_TYPE_NEWS_CONFIG
    return CHANNEL_TYPE_LEGACY_PIPELINE


def list_channels() -> list[dict[str, Any]]:
    """Every channel on disk, each labelled with what it can actually be used for.

    Three channel storage shapes coexist and are not unified:
    project_foundation ChannelProfile (config/channels/<id>/channel.json, used by the
    story_card_text_only_v1 workflow), the news channel_config.json
    (config/channels/<id>/channel_config.json with mode=news_to_short + voices.yaml, used by
    the fullscreen_voiceover_v1 / news_to_short workflow), and the legacy
    pipeline.py --channel/--video profile (src/channel_loader.py), which no create
    workflow can consume.

    Every channel is still listed - nothing is hidden - but each carries
    `supported_templates` and `usable_for_content_creation` so callers can filter
    truthfully instead of offering a channel that will fail downstream.
    """
    channels: list[dict[str, Any]] = []
    seen: set[str] = set()
    for profile in ChannelRegistry().list():
        seen.add(profile.channel_id)
        channels.append(
            {
                "channel_id": profile.channel_id,
                "display_name": profile.display_name,
                "channel_profile_type": CHANNEL_TYPE_PROJECT_FOUNDATION,
                "default_language": profile.default_language,
                "supported_languages": profile.supported_languages,
                "default_application": profile.default_application,
                "default_format": profile.default_format,
                "default_template": profile.default_template,
                "export_targets": profile.export_targets,
                "has_voice_config": (
                    _channels_root() / profile.channel_id / "voices.yaml"
                ).is_file(),
                "supported_templates": list(_CHANNEL_TYPE_TEMPLATES[CHANNEL_TYPE_PROJECT_FOUNDATION]),
                "usable_for_content_creation": True,
            }
        )
    channels_dir = _channels_root()
    if channels_dir.is_dir():
        for entry in sorted(channels_dir.iterdir(), key=lambda item: item.name):
            channel_id = entry.name
            if channel_id in seen or not entry.is_dir():
                continue
            config_path = entry / "channel_config.json"
            has_voices = (entry / "voices.yaml").is_file()
            if not config_path.is_file() and not has_voices:
                continue
            channel_type = _classify_channel_config(config_path) if config_path.is_file() else CHANNEL_TYPE_NEWS_CONFIG
            supported = list(_CHANNEL_TYPE_TEMPLATES[channel_type])
            channels.append(
                {
                    "channel_id": channel_id,
                    "display_name": channel_id,
                    "channel_profile_type": channel_type,
                    "default_language": "ru",
                    "supported_languages": ["ru"],
                    "default_application": "content_creator" if supported else "",
                    "default_format": "vertical_short" if supported else "",
                    "default_template": supported[0] if supported else "",
                    "export_targets": [],
                    "has_voice_config": has_voices,
                    "supported_templates": supported,
                    "usable_for_content_creation": bool(supported),
                    "notes": (
                        ""
                        if supported
                        else "Профиль старого pipeline.py --channel/--video; создание контента его не использует."
                    ),
                }
            )
    return channels


def list_channels_for_template(template_id: str) -> list[dict[str, Any]]:
    """Channels a given template can actually be created with."""
    return [channel for channel in list_channels() if template_id in channel.get("supported_templates", [])]


# implementation_status / tested_status here are a factual record from the Stage 2E
# audit (docs/handoff + a live crow-video run), not derived automatically - keep in
# sync with docs/implementation/unified_content_cli/IMPLEMENTATION_REPORT.md.
TEMPLATE_TESTED_STATUS: dict[str, str] = {
    "story_card_text_only_v1": "live_tested",
    "fullscreen_voiceover_v1": "live_tested",
}


def describe_template_capabilities(template_id: str) -> dict[str, Any]:
    catalog = get_default_catalog()
    template = catalog.templates.get(template_id)
    audio_policy = voice_policy.AUDIO_POLICY_DEFAULTS.get(template.audio_policy_id or "", {})
    subtitle_ids = ["disabled"]
    if template.template_id == "fullscreen_voiceover_v1":
        subtitle_ids.append("documentary")
    return {
        "template_id": template.template_id,
        "display_name": template.display_name,
        "format_id": template.format_id,
        "implementation_status": template.implementation_status,
        "tested_status": TEMPLATE_TESTED_STATUS.get(template.template_id, "architecture_supported"),
        "voice_allowed": bool(audio_policy.get("enabled", template.requires_voice)),
        "voice_required": bool(template.requires_voice),
        "subtitles_allowed": template.template_id == "fullscreen_voiceover_v1",
        "subtitles_required": False,
        "recommended_subtitle_style": "documentary" if template.template_id == "fullscreen_voiceover_v1" else "disabled",
        "subtitle_style_ids": subtitle_ids,
        # story_card_short_render.render_story_card_short always writes audio=False
        # (see src/production_plan/story_card_short_render.py) - it cannot mix in
        # music today, so music is not offered for this template at all.
        "music_allowed": template.template_id == "fullscreen_voiceover_v1",
        "music_required": False,
        "supported_timing_modes": sorted(voice_policy.TIMING_MODES) if template.requires_voice else ["visual_driven"],
        # The template's own policy decides how audio is produced and how scenes are
        # timed - these are not user choices. The wizard used to ask for both and then
        # throw the answers away (no workflow reads ContentCreationRequest.timing or
        # .voice.mode), so it now takes the policy value from here instead.
        "default_voice_mode": str(
            audio_policy.get("output_mode", voice_policy.OUTPUT_MODE_SCENE_AUDIO if template.requires_voice else voice_policy.OUTPUT_MODE_DISABLED)
        ),
        "default_timing_mode": str(
            audio_policy.get("timing_mode", voice_policy.TIMING_MODE_NARRATION_DRIVEN if template.requires_voice else voice_policy.TIMING_MODE_VISUAL_DRIVEN)
        ),
        "supported_renderers": (template.workflow_binding or {}).get("renderer_entrypoints", []),
        "supported_languages": None,
        "output_resolution": None,
        "evidence_required": template.evidence_required,
    }


def build_capabilities_report() -> dict[str, Any]:
    catalog = get_default_catalog()
    return {
        "applications": catalog.applications.serialize(),
        "formats": catalog.formats.serialize(),
        "templates": [describe_template_capabilities(t.template_id) for t in catalog.templates.list_all()],
        "export_targets": catalog.export_targets.serialize(),
        "channels": list_channels(),
        "voice_providers": list_voice_providers(),
        "subtitle_styles": list_subtitle_styles(),
        "music_options": list_music_options(),
    }


__all__ = [
    "ProjectFoundationError",
    "build_capabilities_report",
    "describe_template_capabilities",
    "list_channels",
    "list_channels_for_template",
    "list_music_options",
    "list_subtitle_styles",
    "list_voice_profiles",
    "list_voice_providers",
    "resolve_voice_profile",
]
