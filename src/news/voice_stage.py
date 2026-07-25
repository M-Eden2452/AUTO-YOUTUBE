from __future__ import annotations

from pathlib import Path
from typing import Any

from src.audio.tts.models import compute_settings_hash, compute_text_hash


def build_safe_voice_manifest(
    *,
    project_root: str | Path,
    language: str,
    script: dict[str, Any],
    channel_voice_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    voice_root = Path(project_root) / "localizations" / language / "voice"
    voice_root.mkdir(parents=True, exist_ok=True)
    channel_voice_config = channel_voice_config or {}
    settings = channel_voice_config.get("settings") or {}
    selection = {
        "provider": channel_voice_config.get("provider", "elevenlabs"),
        "voice_profile": channel_voice_config.get("voice_profile", "ru_dom" if language == "ru" else ""),
        "voice_id": channel_voice_config.get("voice_id", "hDfThiytYnsDMuVgm6Qy" if language == "ru" else ""),
        "voice_name": channel_voice_config.get("voice_name", "Dom" if language == "ru" else ""),
        "model_id": channel_voice_config.get("model", channel_voice_config.get("model_id", "eleven_multilingual_v2" if language == "ru" else "")),
        "language": language,
        "settings": settings,
    }
    script_text = script.get("narration_text", "")
    manifest = {
        "status": "provider_selection_required",
        "voice_stage_status": "provider_selection_required",
        "language": language,
        "draft_provider": "audio_file",
        "paid_provider": "elevenlabs",
        "paid_tts_requires_approval": True,
        "audition_requires_approval": True,
        "full_generation_requires_approval": True,
        "never_auto_fallback_to_paid": True,
        "paid_call_performed": False,
        "message": "Черновой источник озвучки не настроен. Добавьте тестовый аудиофайл, подключите локальный TTS или выберите платную пробу ElevenLabs.",
        "selection": selection,
        "script_hash": compute_text_hash(script_text),
        "settings_hash": compute_settings_hash(settings),
        "character_count": len(script_text),
        "audio_path": "",
        "source_type": "",
    }
    _write_json(voice_root / "voice_selection.json", selection)
    _write_json(voice_root / "voice_manifest.json", manifest)
    return manifest


def build_or_generate_voice_manifest(
    *,
    project_root: str | Path,
    language: str,
    script: dict[str, Any],
    channel_voice_config: dict[str, Any] | None = None,
    channel_workflow_config: dict[str, Any] | None = None,
    channel_id: str = "",
    job_id: str = "",
    execute: bool = False,
    voice_profile_override: str | None = None,
) -> dict[str, Any]:
    """Compatibility adapter for the News-to-Short "voice" stage.

    When execute=False (the default) or no approval is on record yet, this delegates to
    the original build_safe_voice_manifest() unchanged - today's stub/dry-run behavior is
    byte-identical. Only when execute=True AND a matching approval exists does it run the
    real generation through the shared global voice workflow (src/audio/narration_workflow),
    never calling ElevenLabs directly from News pipeline code.

    voice_profile_override, when given (e.g. an explicit --voice-profile passed to the
    unified content-creation CLI/wizard), takes priority over the channel's configured
    default and is resolved even for a channel with no voices.yaml of its own - see
    src.news.voice_adapter.load_voice_profile_for_channel.
    """
    if not execute:
        return build_safe_voice_manifest(
            project_root=project_root, language=language, script=script, channel_voice_config=channel_voice_config
        )

    from src.audio.narration_workflow import generate_final
    from src.audio.tts.audio_file_provider import AudioFileProvider
    from src.audio.tts.elevenlabs_provider import ElevenLabsProvider
    from src.audio.tts.provider_manager import TTSProviderManager
    from src.news.voice_adapter import (
        load_approval,
        load_voice_profile_for_channel,
        resolve_voice_policy_for_channel,
        script_to_narration_request,
    )

    approval = load_approval(project_root, language)
    if approval is None:
        return build_safe_voice_manifest(
            project_root=project_root, language=language, script=script, channel_voice_config=channel_voice_config
        )

    policy = resolve_voice_policy_for_channel(channel_voice_config, channel_workflow_config)
    voice_profile = load_voice_profile_for_channel(
        channel_id, channel_voice_config, profile_override=voice_profile_override
    )
    request = script_to_narration_request(
        script=script,
        project_root=project_root,
        job_id=job_id,
        channel_id=channel_id,
        language=language,
        policy=policy,
        voice_profile=voice_profile,
        approval=approval,
    )
    manager = TTSProviderManager()
    manager.register(ElevenLabsProvider())
    manager.register(AudioFileProvider())
    try:
        return generate_final(request, manager=manager)
    except PermissionError:
        return build_safe_voice_manifest(
            project_root=project_root, language=language, script=script, channel_voice_config=channel_voice_config
        )


def _write_json(path: Path, data: dict[str, Any]) -> None:
    import json

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

