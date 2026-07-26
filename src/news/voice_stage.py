from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from src.audio.tts.models import compute_settings_hash, compute_text_hash

if TYPE_CHECKING:  # pragma: no cover - import only for the annotation
    from src.localization.models import ResolvedLocalization


# The selection block this stage has always written for a Russian project with no
# explicit configuration. Kept as the compatibility path for a caller that passes
# only channel_voice_config (older signature, and every test that predates D2).
_LEGACY_RU_DEFAULTS = {
    "provider": "elevenlabs",
    "voice_profile": "ru_dom",
    "voice_id": "hDfThiytYnsDMuVgm6Qy",
    "voice_name": "Dom",
    "model_id": "eleven_multilingual_v2",
}


def _legacy_selection(language: str, channel_voice_config: dict[str, Any]) -> dict[str, Any]:
    """The pre-D2 selection: channel_config.json's ``voice`` block, with hardcoded
    Russian defaults behind it. Unchanged - it is what a caller without a resolved
    localization still gets."""
    is_ru = language == "ru"
    settings = channel_voice_config.get("settings") or {}
    return {
        "provider": channel_voice_config.get("provider", _LEGACY_RU_DEFAULTS["provider"]),
        "voice_profile": channel_voice_config.get(
            "voice_profile", _LEGACY_RU_DEFAULTS["voice_profile"] if is_ru else ""
        ),
        "voice_id": channel_voice_config.get("voice_id", _LEGACY_RU_DEFAULTS["voice_id"] if is_ru else ""),
        "voice_name": channel_voice_config.get("voice_name", _LEGACY_RU_DEFAULTS["voice_name"] if is_ru else ""),
        "model_id": channel_voice_config.get(
            "model",
            channel_voice_config.get("model_id", _LEGACY_RU_DEFAULTS["model_id"] if is_ru else ""),
        ),
        "language": language,
        "settings": settings,
    }


def build_safe_voice_manifest(
    *,
    project_root: str | Path,
    language: str,
    script: dict[str, Any],
    channel_voice_config: dict[str, Any] | None = None,
    localization: "ResolvedLocalization | None" = None,
) -> dict[str, Any]:
    """The no-cost manifest: what *would* be spoken, by which voice, and why nothing
    was generated yet. Never calls a provider.

    When ``localization`` is given, the selection comes from it - so the voice really
    is the one ConfigResolver resolved for this language, including
    ``channel_config.json → languages.<lang>.voice``, which nothing read before D2.
    Without it the pre-D2 selection is used unchanged, and for
    ``nature_science_news_ru`` both produce the same block (proved in
    tests/test_localization_voice_integration.py).
    """
    voice_root = Path(project_root) / "localizations" / language / "voice"
    voice_root.mkdir(parents=True, exist_ok=True)
    channel_voice_config = channel_voice_config or {}
    if localization is not None:
        selection = localization.voice_selection()
        settings = dict(localization.provider_settings)
    else:
        selection = _legacy_selection(language, channel_voice_config)
        settings = selection["settings"]
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
    if localization is not None:
        # Additive, and only what a reader can act on: which source will be used, why
        # TTS is not running, and whether the required key is configured (a bool - the
        # key's value cannot appear here).
        #
        # `status`/`voice_stage_status` are deliberately NOT touched: they describe the
        # *result* of this stage ("ничего не сгенерировано"), and every existing reader
        # (quality_check, preview_render, project status) depends on that meaning. The
        # resolved plan is reported next to them as `localization_status`.
        manifest.update(
            {
                "localization_id": localization.localization_id,
                "locale": localization.locale,
                "localization_status": localization.status,
                "narration_source": localization.narration_source,
                "narration_output_path": localization.narration_output_path,
                "tts_blocked_reason": localization.tts_blocked_reason,
                "fallback_policy": localization.fallback_policy,
                "fallback_applied": localization.fallback_applied,
                "secret_configured": localization.secret_configured,
            }
        )
        if localization.fallback_reason:
            manifest["message"] = localization.fallback_reason
        messages = [issue.message for issue in localization.issues]
        if messages:
            manifest["warnings"] = messages
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
    localization: "ResolvedLocalization | None" = None,
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

    ``localization`` (a src.localization.ResolvedLocalization) is what D2 adds. When it
    is given, the policy and the voice profile are the ones it already resolved instead
    of being resolved a second time here, and two things are decided before any
    provider is touched:

    * a narration file that already exists and is compatible is **not** overwritten -
      the manifest describing it is returned as it is on disk, which is what makes
      resume safe (before this, a second voice stage rewrote the manifest as the
      unconfigured stub and lost the record of narration sitting on disk);
    * if the provider needs a key that is not configured, the fallback policy decides
      the source and no network call is attempted - previously this reached
      ElevenLabsProvider and failed there.
    """
    if localization is not None and localization.reuse_existing_narration:
        existing = _existing_manifest(project_root, localization.localization_id)
        if existing:
            return existing

    if not execute or (localization is not None and not localization.tts_allowed):
        return build_safe_voice_manifest(
            project_root=project_root,
            language=language,
            script=script,
            channel_voice_config=channel_voice_config,
            localization=localization,
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
            project_root=project_root,
            language=language,
            script=script,
            channel_voice_config=channel_voice_config,
            localization=localization,
        )

    if localization is not None and localization.policy is not None and localization.voice_profile is not None:
        policy = localization.policy
        voice_profile = localization.voice_profile
    else:
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
            project_root=project_root,
            language=language,
            script=script,
            channel_voice_config=channel_voice_config,
            localization=localization,
        )


def _existing_manifest(project_root: str | Path, localization_id: str) -> dict[str, Any]:
    """The manifest of narration that is already on disk, read through the tolerant
    reader so a pre-schema-v2 manifest keeps working."""
    path = Path(project_root) / "localizations" / localization_id / "voice" / "voice_manifest.json"
    if not path.is_file():
        return {}
    from src.audio.voice_manifest import read_voice_manifest

    try:
        manifest = read_voice_manifest(path)
    except (OSError, ValueError):
        return {}
    if not isinstance(manifest, dict):
        return {}
    manifest.setdefault("voice_stage_status", manifest.get("status", "completed"))
    return manifest


def _write_json(path: Path, data: dict[str, Any]) -> None:
    import json

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
