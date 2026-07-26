"""Разрешение одной локализации: от того, что выбрал пользователь, до того, что
получит стадия озвучки.

Единственный путь, по которому это делается::

    Wizard/CLI input → project/job/localization → ConfigResolver
        → ResolvedLocalization → voice adapter → voice stage

Ничего своего этот модуль не решает. Приоритет слоёв целиком принадлежит
``src.config_resolver`` (порядок D1 не изменён):

``global_default → format_policy → channel_profile → channel_config
→ template_policy → project_override → localization_override → runtime_override``
(+ ``environment`` - только секреты).

Явно выбранные пользователем провайдер и профиль подаются в резолвер как
``runtime_override``, поэтому они бьют ``localization_override`` без отдельной
ветки в коде. Блок ``channel_config.json → languages.<lang>.voice``, который до
этого этапа не читал никто, попадает сюда через слой ``localization_override``,
уже реализованный в D1.

Модуль только читает: ни один файл здесь не создаётся и не изменяется, сеть не
вызывается, TTS не вызывается.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.audio.voice_policy import (
    FALLBACK_POLICY_LOCAL_STUB_ONLY_FOR_TESTS,
    FALLBACK_POLICY_LOCAL_TTS,
    FALLBACK_POLICY_MANUAL_AUDIO,
    FALLBACK_POLICY_NONE,
    OUTPUT_MODE_DISABLED,
    OUTPUT_MODE_MANUAL_AUDIO,
    VoicePolicy,
)
from src.config_resolver import keys as k
from src.config_resolver import resolve_config, to_voice_policy
from src.config_resolver.models import SOURCE_RUNTIME_OVERRIDE

from . import locales
from .models import (
    ISSUE_COMPAT_DEFAULT_PROFILE,
    ISSUE_EXISTING_NARRATION_LANGUAGE_MISMATCH,
    ISSUE_EXISTING_NARRATION_PROFILE_MISMATCH,
    ISSUE_FALLBACK_UNAVAILABLE,
    ISSUE_LOCAL_TTS_UNAVAILABLE,
    ISSUE_MANUAL_AUDIO_MISSING,
    ISSUE_NO_PROVIDER,
    ISSUE_SECRET_MISSING,
    ISSUE_UNKNOWN_LANGUAGE,
    ISSUE_UNKNOWN_PROVIDER,
    ISSUE_VOICE_ID_MISSING,
    ISSUE_VOICE_PROFILE_DISABLED,
    ISSUE_VOICE_PROFILE_LANGUAGE_MISMATCH,
    ISSUE_VOICE_PROFILE_NOT_FOUND,
    ISSUE_VOICE_PROFILE_PROVIDER_MISMATCH,
    NARRATION_SOURCE_EXISTING_ARTIFACT,
    NARRATION_SOURCE_MANUAL_AUDIO,
    NARRATION_SOURCE_NONE,
    NARRATION_SOURCE_TTS,
    SEVERITY_ERROR,
    SEVERITY_WARNING,
    STATUS_AWAITING_SOURCE,
    STATUS_BLOCKED,
    STATUS_COMPLETED,
    STATUS_MANUAL_AUDIO_READY,
    STATUS_READY_FOR_GENERATION,
    STATUS_SKIPPED,
    TTS_BLOCKED_EXISTING_NARRATION,
    TTS_BLOCKED_LOCAL_TTS_UNAVAILABLE,
    TTS_BLOCKED_MANUAL_SOURCE,
    TTS_BLOCKED_NO_PROVIDER,
    TTS_BLOCKED_SECRET_MISSING,
    TTS_BLOCKED_VALIDATION_ERROR,
    TTS_BLOCKED_VOICE_DISABLED,
    LocalizationIssue,
    ResolvedLocalization,
)
from .secrets import is_secret_configured, secret_env_var

# Последний резервный профиль. Не выдуман: это тот самый литерал, на который
# падает сегодняшний src.news.voice_adapter.load_voice_profile_for_channel
# ("ru_dom"), и убрать его - значит поменять поведение каналов без
# voice_profile в конфигурации.
COMPAT_DEFAULT_VOICE_PROFILE = "ru_dom"

# Провайдеры, реально зарегистрированные в TTSProviderManager
# (src/news/voice_stage.py: ElevenLabsProvider + AudioFileProvider) плюс
# псевдо-вариант "выключено" из capabilities.VOICE_PROVIDER_DISABLED.
PROVIDER_DISABLED = "disabled"
PROVIDER_ELEVENLABS = "elevenlabs"
PROVIDER_AUDIO_FILE = "audio_file"
KNOWN_PROVIDERS = frozenset({PROVIDER_DISABLED, PROVIDER_ELEVENLABS, PROVIDER_AUDIO_FILE})

# Провайдеры, которым нужен voice_id.
PROVIDERS_REQUIRING_VOICE_ID = frozenset({PROVIDER_ELEVENLABS})

_LOCAL_TTS_FALLBACKS = frozenset({FALLBACK_POLICY_LOCAL_TTS, FALLBACK_POLICY_LOCAL_STUB_ONLY_FOR_TESTS})


def _voice_manifest_path(project_root: Path, localization_id: str) -> Path:
    return project_root / "localizations" / localization_id / "voice" / "voice_manifest.json"


def _read_existing_manifest(project_root: Path | None, localization_id: str) -> dict[str, Any]:
    """Существующий voice_manifest.json, прочитанный терпимым читателем.

    Наличие готовой озвучки определяется по манифесту, а не по одному факту
    существования файла: манифест - это то, что уже сегодня хранит provider,
    voice_profile и признак платного вызова.
    """
    if project_root is None:
        return {}
    path = _voice_manifest_path(project_root, localization_id)
    if not path.is_file():
        return {}
    from src.audio.voice_manifest import read_voice_manifest

    try:
        data = read_voice_manifest(path)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _manifest_audio_path(manifest: dict[str, Any]) -> str:
    """Путь к готовой озвучке, если она действительно лежит на диске.

    Та же строгость, что у ``src.content_creation.service._completed_narration``:
    манифест должен *объявлять* файл, и файл должен существовать. Манифест,
    ссылающийся на удалённый wav, готовой озвучкой не считается.
    """
    candidates = [
        str(manifest.get("audio_path") or ""),
        str((manifest.get("narration") or {}).get("output_path") or ""),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return candidate
    return ""


def resolve_localization(
    *,
    channel_id: str = "",
    template_id: str = "",
    format_id: str = "",
    language: str = "",
    localization_id: str = "",
    locale: str = "",
    subtitle_language: str = "",
    project_id: str = "",
    project_root: str | Path | None = None,
    script_path: str = "",
    manual_audio_path: str = "",
    voice_provider_override: str = "",
    voice_profile_override: str = "",
    overrides: dict[str, Any] | None = None,
    channels_dir: str = "channels",
    projects_dir: str = "projects",
    include_secrets: bool = True,
    secret_probe: Any = None,
) -> ResolvedLocalization:
    """Разрешить одну локализацию. Только чтение; ничего не пишет и не вызывает TTS.

    ``secret_probe`` - подменяемая проверка «настроен ли ключ» (тесты подставляют
    свою, чтобы не зависеть от окружения машины). Возвращает только ``bool``.
    """
    probe = secret_probe or is_secret_configured
    issues: list[LocalizationIssue] = []

    language_raw = str(language or "")
    normalized = locales.normalize_language(language_raw)
    # localization_id - имя папки. Оно берётся как есть: старый проект с папкой
    # "ru-RU" должен продолжать читаться, и переименовывать её D2 не имеет права.
    folder = str(localization_id or language_raw or normalized)
    effective_language = normalized or language_raw
    if language_raw and not normalized:
        issues.append(
            LocalizationIssue(
                code=ISSUE_UNKNOWN_LANGUAGE,
                severity=SEVERITY_WARNING,
                message=(
                    f"Язык {language_raw!r} не входит в известный список "
                    f"({', '.join(locales.known_language_codes())}); настройки языка "
                    "разрешаются как есть, без нормализации."
                ),
                localization_id=folder,
            )
        )

    # Слой localization_override читает channel_config.json → languages.<code>.
    # Для этого нужен именно нормализованный код: так "ru-RU" из старого проекта
    # находит блок languages.ru, который до D2 не читал никто.
    resolved_config = resolve_config(
        channel_id=channel_id,
        template_id=template_id,
        format_id=format_id,
        language=normalized or language_raw,
        project_id=project_id,
        overrides=_runtime_overrides(voice_provider_override, voice_profile_override, overrides),
        channels_dir=channels_dir,
        projects_dir=projects_dir,
        include_secrets=include_secrets,
    )
    policy: VoicePolicy = to_voice_policy(resolved_config)

    provider = str(resolved_config.get(k.KEY_VOICE_PROVIDER) or "")
    if provider and provider not in KNOWN_PROVIDERS:
        issues.append(
            LocalizationIssue(
                code=ISSUE_UNKNOWN_PROVIDER,
                severity=SEVERITY_ERROR,
                message=(
                    f"Неизвестный провайдер озвучки {provider!r}. Зарегистрированы: "
                    f"{', '.join(sorted(KNOWN_PROVIDERS))}."
                ),
                localization_id=folder,
            )
        )

    profile_id, profile, profile_issues = _resolve_profile(
        resolved_config,
        channel_id=channel_id,
        channels_dir=channels_dir,
        language=effective_language,
        provider=provider,
        folder=folder,
    )
    issues.extend(profile_issues)

    provider_settings = _provider_settings(policy, profile)
    voice_id = profile.voice_id if profile is not None else ""
    model_id = str(profile.model_id if profile is not None else "") or str(
        resolved_config.get(k.KEY_VOICE_MODEL_ID) or ""
    )
    if provider in PROVIDERS_REQUIRING_VOICE_ID and not voice_id:
        issues.append(
            LocalizationIssue(
                code=ISSUE_VOICE_ID_MISSING,
                severity=SEVERITY_ERROR,
                message=(
                    f"Провайдеру {provider!r} нужен voice_id, но у профиля "
                    f"{profile_id or '—'} он не задан."
                ),
                localization_id=folder,
            )
        )

    env_var = secret_env_var(provider)
    secret_required = bool(env_var)
    secret_configured = bool(probe(env_var)) if secret_required else False

    root = Path(project_root) if project_root else None
    manifest = _read_existing_manifest(root, folder)
    existing_narration = _manifest_audio_path(manifest)
    if existing_narration:
        issues.extend(
            _existing_artifact_issues(
                manifest,
                folder=folder,
                language=effective_language,
                profile_id=profile_id,
                provider=provider,
            )
        )
    narration_output = ""
    if root is not None:
        from src.audio.scene_voice_generator import generation_output_paths

        narration_output = str(generation_output_paths(root, folder)["narration_wav"])

    manual_path = str(manual_audio_path or "")
    if manual_path and not Path(manual_path).is_file():
        issues.append(
            LocalizationIssue(
                code=ISSUE_MANUAL_AUDIO_MISSING,
                severity=SEVERITY_ERROR,
                message=f"Файл ручной озвучки не найден: {manual_path}",
                localization_id=folder,
            )
        )

    decision = _decide_narration_source(
        policy=policy,
        provider=provider,
        folder=folder,
        existing_narration=existing_narration,
        existing_incompatible=any(
            issue.code == ISSUE_EXISTING_NARRATION_LANGUAGE_MISMATCH and issue.is_error for issue in issues
        ),
        manual_path=manual_path,
        secret_required=secret_required,
        secret_configured=secret_configured,
    )
    issues.extend(decision["issues"])

    has_errors = any(issue.is_error for issue in issues)
    if has_errors and decision["status"] != STATUS_COMPLETED:
        status = STATUS_BLOCKED if decision["status"] != STATUS_SKIPPED else STATUS_SKIPPED
    else:
        status = decision["status"]
    tts_allowed = bool(decision["tts_allowed"]) and not has_errors
    tts_blocked_reason = str(decision["tts_blocked_reason"])
    if not tts_allowed and not tts_blocked_reason:
        tts_blocked_reason = TTS_BLOCKED_VALIDATION_ERROR

    return ResolvedLocalization(
        localization_id=folder,
        language=effective_language,
        language_raw=language_raw,
        locale=locales.normalize_locale(locale, language=effective_language),
        subtitle_language=locales.normalize_language(subtitle_language) or effective_language,
        voice_provider=provider,
        voice_profile_id=profile_id,
        resolved_voice_id=voice_id,
        voice_name=profile.display_name if profile is not None else "",
        tts_model=model_id,
        provider_settings=provider_settings,
        fallback_policy=policy.fallback_policy,
        fallback_applied=bool(decision["fallback_applied"]),
        fallback_reason=str(decision["fallback_reason"]),
        narration_source=str(decision["narration_source"]),
        manual_audio_path=manual_path,
        existing_narration_path=existing_narration,
        narration_output_path=narration_output,
        script_path=str(script_path or ""),
        secret_env_var=env_var,
        secret_required=secret_required,
        secret_configured=secret_configured,
        status=status,
        reuse_existing_narration=bool(decision["reuse_existing"]),
        tts_allowed=tts_allowed,
        tts_blocked_reason=tts_blocked_reason,
        policy=policy,
        voice_profile=profile,
        config=resolved_config,
        issues=tuple(issues),
    )


def _runtime_overrides(
    voice_provider_override: str, voice_profile_override: str, overrides: dict[str, Any] | None
) -> dict[str, Any]:
    """Явный выбор пользователя как слой ``runtime_override``.

    Именно это делает «runtime бьёт localization» частью резолвера, а не отдельной
    ветки в коде локализации.
    """
    merged: dict[str, Any] = dict(overrides or {})
    if voice_provider_override:
        merged[k.KEY_VOICE_PROVIDER] = voice_provider_override
    if voice_profile_override:
        merged[k.KEY_VOICE_PROFILE] = voice_profile_override
    return merged


def _resolve_profile(
    resolved_config: Any,
    *,
    channel_id: str,
    channels_dir: str,
    language: str,
    provider: str,
    folder: str,
) -> tuple[str, Any, list[LocalizationIssue]]:
    """Профиль по id, который уже выбрал ConfigResolver.

    Приоритет здесь не пересчитывается: id приходит из резолвера, а этот код
    только достаёт профиль из ``voices.yaml`` тем же поиском, что и раньше
    (``src.audio.voice_profile_registry.lookup_profile``).
    """
    from src.audio.voice_profile_registry import VoiceProfileRegistryError, lookup_profile

    issues: list[LocalizationIssue] = []
    profile_id = str(resolved_config.get(k.KEY_VOICE_PROFILE) or "")
    # Явный выбор пользователя разрешено искать в voices.yaml других каналов -
    # ровно так же, как это делает load_voice_profile_for_channel сегодня.
    allow_global = bool(profile_id) and resolved_config.source_of(k.KEY_VOICE_PROFILE) == SOURCE_RUNTIME_OVERRIDE
    if not profile_id:
        profile_id = COMPAT_DEFAULT_VOICE_PROFILE
        issues.append(
            LocalizationIssue(
                code=ISSUE_COMPAT_DEFAULT_PROFILE,
                severity=SEVERITY_WARNING,
                message=(
                    f"Голосовой профиль не задан ни одним слоем конфигурации; взят "
                    f"совместимый по умолчанию {COMPAT_DEFAULT_VOICE_PROFILE!r} - то же значение, "
                    "на которое падает пайплайн сегодня."
                ),
                localization_id=folder,
            )
        )
    if provider == PROVIDER_DISABLED:
        return profile_id, None, issues

    try:
        profile = lookup_profile(
            channel_id, profile_id, channels_dir=channels_dir, allow_global=allow_global
        )
    except VoiceProfileRegistryError as exc:
        issues.append(
            LocalizationIssue(
                code=ISSUE_VOICE_PROFILE_NOT_FOUND,
                severity=SEVERITY_ERROR,
                message=str(exc),
                localization_id=folder,
            )
        )
        return profile_id, None, issues

    if profile.language and language and locales.normalize_language(profile.language) != locales.normalize_language(
        language
    ):
        issues.append(
            LocalizationIssue(
                code=ISSUE_VOICE_PROFILE_LANGUAGE_MISMATCH,
                severity=SEVERITY_ERROR,
                message=(
                    f"Голосовой профиль {profile.profile_id!r} рассчитан на язык "
                    f"{profile.language!r} и не подходит для локализации {language!r}. "
                    "Задайте голос этого языка в channel_config.json → "
                    f"languages.{language}.voice или передайте другой профиль явно."
                ),
                localization_id=folder,
            )
        )
    if provider and profile.provider and profile.provider != provider:
        issues.append(
            LocalizationIssue(
                code=ISSUE_VOICE_PROFILE_PROVIDER_MISMATCH,
                severity=SEVERITY_ERROR,
                message=(
                    f"Профиль {profile.profile_id!r} принадлежит провайдеру "
                    f"{profile.provider!r}, а выбран провайдер {provider!r}."
                ),
                localization_id=folder,
            )
        )
    if not profile.enabled:
        issues.append(
            LocalizationIssue(
                code=ISSUE_VOICE_PROFILE_DISABLED,
                severity=SEVERITY_WARNING,
                message=f"Голосовой профиль {profile.profile_id!r} помечен enabled: false.",
                localization_id=folder,
            )
        )
    return profile.profile_id, profile, issues


def _provider_settings(policy: VoicePolicy, profile: Any) -> dict[str, Any]:
    """Настройки провайдера в том же порядке слияния, что у
    ``src.audio.narration_models.build_narration_request_from_scenes``:
    профиль, поверх него ``policy.provider_settings``."""
    settings: dict[str, Any] = {}
    if profile is not None and profile.settings:
        settings.update(profile.settings)
    if policy.provider_settings:
        settings.update(policy.provider_settings)
    return settings


def _existing_artifact_issues(
    manifest: dict[str, Any], *, folder: str, language: str, profile_id: str, provider: str
) -> list[LocalizationIssue]:
    """Совместим ли уже готовый артефакт с текущей локализацией."""
    issues: list[LocalizationIssue] = []
    manifest_language = str(manifest.get("language") or "")
    if manifest_language and language:
        if locales.normalize_language(manifest_language) != locales.normalize_language(language):
            issues.append(
                LocalizationIssue(
                    code=ISSUE_EXISTING_NARRATION_LANGUAGE_MISMATCH,
                    severity=SEVERITY_ERROR,
                    message=(
                        f"Готовая озвучка в {folder!r} записана для языка {manifest_language!r}, "
                        f"а локализация разрешена как {language!r}. Переиспользовать её нельзя."
                    ),
                    localization_id=folder,
                )
            )
    manifest_profile = str(manifest.get("voice_profile") or "")
    manifest_provider = str(manifest.get("provider") or "")
    if manifest_profile and profile_id and manifest_profile != profile_id:
        issues.append(
            LocalizationIssue(
                code=ISSUE_EXISTING_NARRATION_PROFILE_MISMATCH,
                severity=SEVERITY_WARNING,
                message=(
                    f"Готовая озвучка сделана профилем {manifest_profile!r}, а сейчас разрешён "
                    f"{profile_id!r}. Файл будет переиспользован без перегенерации; удалите его "
                    "вручную, если нужен новый голос."
                ),
                localization_id=folder,
            )
        )
    elif manifest_provider and provider and manifest_provider != provider:
        issues.append(
            LocalizationIssue(
                code=ISSUE_EXISTING_NARRATION_PROFILE_MISMATCH,
                severity=SEVERITY_WARNING,
                message=(
                    f"Готовая озвучка сделана провайдером {manifest_provider!r}, а сейчас выбран "
                    f"{provider!r}. Файл будет переиспользован без перегенерации."
                ),
                localization_id=folder,
            )
        )
    return issues


def _decide_narration_source(
    *,
    policy: VoicePolicy,
    provider: str,
    folder: str,
    existing_narration: str,
    existing_incompatible: bool,
    manual_path: str,
    secret_required: bool,
    secret_configured: bool,
) -> dict[str, Any]:
    """Единственное место, где решается: TTS, ручной файл или готовый артефакт.

    Порядок ветвей выбран так, чтобы ни в одном случае озвучка не перегенерировалась
    там, где сегодня она бы переиспользовалась, и чтобы сеть не вызывалась там, где
    сегодня вызов заведомо провалится (нет ключа).
    """
    issues: list[LocalizationIssue] = []
    result: dict[str, Any] = {
        "narration_source": NARRATION_SOURCE_NONE,
        "status": STATUS_AWAITING_SOURCE,
        "reuse_existing": False,
        "tts_allowed": False,
        "tts_blocked_reason": "",
        "fallback_applied": False,
        "fallback_reason": "",
        "issues": issues,
    }

    if not policy.enabled or policy.output_mode == OUTPUT_MODE_DISABLED or provider == PROVIDER_DISABLED:
        result["status"] = STATUS_SKIPPED
        result["tts_blocked_reason"] = TTS_BLOCKED_VOICE_DISABLED
        return result

    if existing_narration and not existing_incompatible:
        result["narration_source"] = NARRATION_SOURCE_EXISTING_ARTIFACT
        result["status"] = STATUS_COMPLETED
        result["reuse_existing"] = True
        result["tts_blocked_reason"] = TTS_BLOCKED_EXISTING_NARRATION
        return result

    if manual_path:
        result["narration_source"] = NARRATION_SOURCE_MANUAL_AUDIO
        result["status"] = STATUS_MANUAL_AUDIO_READY if Path(manual_path).is_file() else STATUS_AWAITING_SOURCE
        result["tts_blocked_reason"] = TTS_BLOCKED_MANUAL_SOURCE
        return result

    if provider == PROVIDER_AUDIO_FILE or policy.output_mode == OUTPUT_MODE_MANUAL_AUDIO:
        result["narration_source"] = NARRATION_SOURCE_MANUAL_AUDIO
        result["status"] = STATUS_AWAITING_SOURCE
        result["tts_blocked_reason"] = TTS_BLOCKED_MANUAL_SOURCE
        return result

    if not provider:
        result["status"] = STATUS_AWAITING_SOURCE
        result["tts_blocked_reason"] = TTS_BLOCKED_NO_PROVIDER
        issues.append(
            LocalizationIssue(
                code=ISSUE_NO_PROVIDER,
                severity=SEVERITY_WARNING,
                message="Провайдер озвучки не выбран ни одним слоем конфигурации.",
                localization_id=folder,
            )
        )
        return result

    if secret_required and not secret_configured:
        return _apply_secret_fallback(result, policy=policy, provider=provider, folder=folder, issues=issues)

    result["narration_source"] = NARRATION_SOURCE_TTS
    result["status"] = STATUS_READY_FOR_GENERATION
    result["tts_allowed"] = True
    return result


def _apply_secret_fallback(
    result: dict[str, Any],
    *,
    policy: VoicePolicy,
    provider: str,
    folder: str,
    issues: list[LocalizationIssue],
) -> dict[str, Any]:
    """Провайдер выбран, но его ключ не настроен - что делать.

    Голос и провайдер при этом не подменяются: меняется только источник звука, и
    причина всегда записывается явно.
    """
    result["tts_blocked_reason"] = TTS_BLOCKED_SECRET_MISSING
    env_var = secret_env_var(provider)
    base = f"Ключ провайдера {provider!r} ({env_var}) не настроен, платный вызов невозможен."

    if policy.fallback_policy == FALLBACK_POLICY_MANUAL_AUDIO:
        result["narration_source"] = NARRATION_SOURCE_MANUAL_AUDIO
        result["status"] = STATUS_AWAITING_SOURCE
        result["fallback_applied"] = True
        result["fallback_reason"] = (
            f"{base} fallback_policy={FALLBACK_POLICY_MANUAL_AUDIO}: проект ждёт готовый "
            "аудиофайл. Импортируйте его командой "
            "`pipeline.py --voice-action import-audio --job-id <id> --audio-file <path>`."
        )
        issues.append(
            LocalizationIssue(
                code=ISSUE_SECRET_MISSING,
                severity=SEVERITY_WARNING,
                message=result["fallback_reason"],
                localization_id=folder,
            )
        )
        return result

    if policy.fallback_policy in _LOCAL_TTS_FALLBACKS:
        result["status"] = STATUS_BLOCKED
        result["tts_blocked_reason"] = TTS_BLOCKED_LOCAL_TTS_UNAVAILABLE
        result["fallback_reason"] = (
            f"{base} fallback_policy={policy.fallback_policy}, но ни один локальный TTS-провайдер "
            "не зарегистрирован в TTSProviderManager - озвучку придётся импортировать вручную."
        )
        issues.append(
            LocalizationIssue(
                code=ISSUE_LOCAL_TTS_UNAVAILABLE,
                severity=SEVERITY_ERROR,
                message=result["fallback_reason"],
                localization_id=folder,
            )
        )
        return result

    result["status"] = STATUS_BLOCKED
    result["fallback_reason"] = (
        f"{base} fallback_policy={policy.fallback_policy or FALLBACK_POLICY_NONE}: замена источника "
        "не разрешена, стадия озвучки остановлена."
    )
    issues.append(
        LocalizationIssue(
            code=ISSUE_FALLBACK_UNAVAILABLE,
            severity=SEVERITY_ERROR,
            message=result["fallback_reason"],
            localization_id=folder,
        )
    )
    return result


__all__ = [
    "COMPAT_DEFAULT_VOICE_PROFILE",
    "KNOWN_PROVIDERS",
    "PROVIDERS_REQUIRING_VOICE_ID",
    "PROVIDER_AUDIO_FILE",
    "PROVIDER_DISABLED",
    "PROVIDER_ELEVENLABS",
    "resolve_localization",
]
