"""Runtime-контракт одной локализации: что именно будет озвучено, каким голосом,
откуда взята каждая настройка и почему TTS будет или не будет вызван.

Три вещи разделены намеренно, и объединять их нельзя:

1. **Сохранённая конфигурация** - ``config/channels/<id>/channel_config.json``,
   ``config/channels/<id>/voices.yaml``, ``projects/<id>/job.json``. Этот модуль их только
   читает и никогда не пишет.
2. **Разрешённая runtime-конфигурация** - ``ResolvedLocalization`` ниже. Живёт в
   памяти на время одного запуска, ни в один manifest целиком не сохраняется.
3. **Фактический результат стадии озвучки** - ``localizations/<id>/voice/voice_manifest.json``
   (``src.audio.voice_manifest``). Он уже существует и остаётся единственным местом,
   где хранится, что реально сгенерировано.

Provenance пользовательского и уже существующего аудио тоже остаётся там, где он
есть сегодня (``voice_manifest.json``: ``source_type``, ``provider``, ``voice_profile``,
``paid_call_performed``). ``ResolvedLocalization`` только *читает* его, чтобы решить,
можно ли переиспользовать готовую озвучку.

Секретов здесь нет физически: про ключ хранится один ``bool``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.audio.tts.models import VoiceProfile
from src.audio.voice_policy import VoicePolicy

# --- источник озвучки ---------------------------------------------------------
# Три реальных источника, между которыми уже сегодня выбирает проект:
# TTS (src.audio.narration_workflow.generate_final), ручной файл
# (src.audio.voice_workflow.import_manual_audio) и готовый артефакт (проверка
# voice_manifest["audio_path"] в src.content_creation.service._completed_narration).
NARRATION_SOURCE_NONE = "none"
NARRATION_SOURCE_TTS = "tts"
NARRATION_SOURCE_MANUAL_AUDIO = "manual_audio"
NARRATION_SOURCE_EXISTING_ARTIFACT = "existing_artifact"

NARRATION_SOURCES = frozenset(
    {
        NARRATION_SOURCE_NONE,
        NARRATION_SOURCE_TTS,
        NARRATION_SOURCE_MANUAL_AUDIO,
        NARRATION_SOURCE_EXISTING_ARTIFACT,
    }
)

# --- статус готовности озвучки ------------------------------------------------
# Все значения взяты из существующего словаря состояний
# src.audio.narration_workflow.EXTENDED_VOICE_STATES - нового набора статусов
# D2/E2 не вводит (это проверяется тестом).
STATUS_SKIPPED = "skipped"
STATUS_COMPLETED = "completed"
STATUS_MANUAL_AUDIO_READY = "manual_audio_ready"
# Ровно тот статус, который пишет сегодняшний src.news.voice_stage.build_safe_voice_manifest,
# когда черновой источник озвучки не настроен и нужно положить WAV.
STATUS_AWAITING_SOURCE = "provider_selection_required"
# Провайдер и голос определены, генерация возможна - но только после approval.
STATUS_READY_FOR_GENERATION = "final_confirmation_required"
STATUS_BLOCKED = "blocked"

# --- почему TTS не будет вызван ------------------------------------------------
TTS_BLOCKED_VOICE_DISABLED = "voice_disabled"
TTS_BLOCKED_EXISTING_NARRATION = "existing_narration_reused"
TTS_BLOCKED_MANUAL_SOURCE = "manual_audio_source"
TTS_BLOCKED_SECRET_MISSING = "secret_missing"
TTS_BLOCKED_LOCAL_TTS_UNAVAILABLE = "local_tts_unavailable"
TTS_BLOCKED_NO_PROVIDER = "no_provider"
# Провайдер и ключ в порядке, но локализация не прошла проверку (например, профиль
# не того языка) - генерировать в таком виде нельзя.
TTS_BLOCKED_VALIDATION_ERROR = "validation_error"

# --- код проблемы --------------------------------------------------------------
ISSUE_UNKNOWN_LANGUAGE = "unknown_language"
ISSUE_UNKNOWN_LOCALE = "unknown_locale"
ISSUE_UNKNOWN_PROVIDER = "unknown_provider"
ISSUE_NO_PROVIDER = "no_provider"
ISSUE_VOICE_PROFILE_NOT_FOUND = "voice_profile_not_found"
ISSUE_VOICE_PROFILE_LANGUAGE_MISMATCH = "voice_profile_language_mismatch"
ISSUE_VOICE_PROFILE_PROVIDER_MISMATCH = "voice_profile_provider_mismatch"
ISSUE_VOICE_PROFILE_DISABLED = "voice_profile_disabled"
ISSUE_VOICE_ID_MISSING = "voice_id_missing"
ISSUE_SECRET_MISSING = "secret_missing"
ISSUE_MANUAL_AUDIO_MISSING = "manual_audio_missing"
ISSUE_LOCAL_TTS_UNAVAILABLE = "local_tts_unavailable"
ISSUE_FALLBACK_UNAVAILABLE = "fallback_unavailable"
ISSUE_MULTIPLE_ACTIVE_SOURCES = "multiple_active_narration_sources"
ISSUE_UNKNOWN_NARRATION_SOURCE = "unknown_narration_source"
ISSUE_EXISTING_NARRATION_LANGUAGE_MISMATCH = "existing_narration_language_mismatch"
ISSUE_EXISTING_NARRATION_PROFILE_MISMATCH = "existing_narration_profile_mismatch"
ISSUE_DUPLICATE_LOCALIZATION_ID = "duplicate_localization_id"
ISSUE_DUPLICATE_OUTPUT_PATH = "duplicate_narration_output_path"
ISSUE_SECRET_IN_CONFIG = "secret_in_config"
ISSUE_PATH_OUTSIDE_PROJECT = "path_outside_project"
ISSUE_COMPAT_DEFAULT_PROFILE = "compatibility_default_voice_profile"

SEVERITY_ERROR = "error"
SEVERITY_WARNING = "warning"


class LocalizationError(ValueError):
    """Неверный запрос локализации: неизвестный язык/провайдер/профиль.

    ``reason`` - один из ``ISSUE_*``, чтобы CLI и мастер могли предложить понятное
    действие, не разбирая текст сообщения (тот же приём, что у
    ``ContentCreationError`` и ``ConfigResolutionError``).
    """

    def __init__(self, message: str, *, reason: str = "generic") -> None:
        super().__init__(message)
        self.reason = reason


@dataclass(frozen=True)
class LocalizationIssue:
    """Одна проблема или предупреждение по локализации."""

    code: str
    severity: str
    message: str
    localization_id: str = ""

    @property
    def is_error(self) -> bool:
        return self.severity == SEVERITY_ERROR

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "localization_id": self.localization_id,
        }


@dataclass(frozen=True)
class ResolvedLocalization:
    """Всё, что нужно стадии озвучки для одной языковой версии проекта.

    ``localization_id`` - имя папки (``localizations/<id>/...``). Оно берётся из
    проекта как есть и **не нормализуется**: старый проект с папкой ``ru-RU``
    должен продолжать читаться. Нормализованный код языка лежит отдельно, в
    ``language``.
    """

    localization_id: str
    language: str
    # То, что пришло на вход (CLI, job.json). Нужно, чтобы объяснить нормализацию.
    language_raw: str = ""
    locale: str = ""
    # Обычно совпадает с language. Отдельное поле, потому что контракт не должен
    # предполагать, что язык субтитров всегда равен языку озвучки (Q3).
    subtitle_language: str = ""

    voice_provider: str = ""
    voice_profile_id: str = ""
    resolved_voice_id: str = ""
    voice_name: str = ""
    tts_model: str = ""
    provider_settings: dict[str, Any] = field(default_factory=dict)

    fallback_policy: str = ""
    fallback_applied: bool = False
    fallback_reason: str = ""

    narration_source: str = NARRATION_SOURCE_NONE
    manual_audio_path: str = ""
    existing_narration_path: str = ""
    narration_output_path: str = ""
    script_path: str = ""

    # Только признак. Значение ключа в этот объект попасть не может.
    secret_env_var: str = ""
    secret_required: bool = False
    secret_configured: bool = False

    status: str = STATUS_AWAITING_SOURCE
    reuse_existing_narration: bool = False
    tts_allowed: bool = False
    tts_blocked_reason: str = ""

    # Готовые объекты для существующих потребителей: policy идёт в
    # narration_workflow, profile - в script_to_narration_request.
    policy: VoicePolicy | None = None
    voice_profile: VoiceProfile | None = None
    # Ссылка на разрешённую конфигурацию: источник каждой настройки и trace.
    # Секреты в ней - булевы (см. src/config_resolver/models.ResolvedValue).
    config: Any = None

    issues: tuple[LocalizationIssue, ...] = ()

    # -- производные ------------------------------------------------------

    @property
    def voice_style(self) -> Any:
        """Стиль подачи, как его понимает единственный настоящий провайдер:
        ``settings.style`` ElevenLabs. Отдельного поля нет намеренно - иначе одно
        и то же значение хранилось бы в двух местах."""
        return self.provider_settings.get("style")

    @property
    def errors(self) -> tuple[LocalizationIssue, ...]:
        return tuple(issue for issue in self.issues if issue.is_error)

    @property
    def warnings(self) -> tuple[LocalizationIssue, ...]:
        return tuple(issue for issue in self.issues if not issue.is_error)

    @property
    def valid(self) -> bool:
        return not self.errors

    def voice_selection(self) -> dict[str, Any]:
        """Блок ``selection``, который уже пишет ``voice_stage.build_safe_voice_manifest``
        в ``voice_selection.json`` - в том же виде и с теми же ключами."""
        return {
            "provider": self.voice_provider,
            "voice_profile": self.voice_profile_id,
            "voice_id": self.resolved_voice_id,
            "voice_name": self.voice_name,
            "model_id": self.tts_model,
            "language": self.localization_id,
            "settings": dict(self.provider_settings),
        }

    def to_dict(self, *, include_config: bool = False, include_trace: bool = False) -> dict[str, Any]:
        data: dict[str, Any] = {
            "localization_id": self.localization_id,
            "language": self.language,
            "language_raw": self.language_raw,
            "locale": self.locale,
            "subtitle_language": self.subtitle_language,
            "voice_provider": self.voice_provider,
            "voice_profile_id": self.voice_profile_id,
            "resolved_voice_id": self.resolved_voice_id,
            "voice_name": self.voice_name,
            "voice_style": self.voice_style,
            "tts_model": self.tts_model,
            "provider_settings": dict(self.provider_settings),
            "fallback_policy": self.fallback_policy,
            "fallback_applied": self.fallback_applied,
            "fallback_reason": self.fallback_reason,
            "narration_source": self.narration_source,
            "manual_audio_path": self.manual_audio_path,
            "existing_narration_path": self.existing_narration_path,
            "narration_output_path": self.narration_output_path,
            "script_path": self.script_path,
            "secret_env_var": self.secret_env_var,
            "secret_required": self.secret_required,
            "secret_configured": self.secret_configured,
            "status": self.status,
            "reuse_existing_narration": self.reuse_existing_narration,
            "tts_allowed": self.tts_allowed,
            "tts_blocked_reason": self.tts_blocked_reason,
            "issues": [issue.to_dict() for issue in self.issues],
        }
        if include_config and self.config is not None:
            data["config"] = self.config.to_dict(include_trace=include_trace)
        return data

    def explain_rows(self) -> list[dict[str, Any]]:
        """«параметр → значение → откуда взято» для настроек локализации.

        Источник берётся у ConfigResolver, поэтому колонка «откуда» здесь та же
        самая, что у ``channels show --explain``. Значение секрета не выводится
        никогда - только «настроен / не настроен».
        """
        from src.config_resolver import keys as k

        rows: list[dict[str, Any]] = [
            {"key": "localization_id", "value": self.localization_id, "resolved_from": "project", "origin": ""},
            {"key": "language", "value": self.language, "resolved_from": "", "origin": ""},
            {"key": "locale", "value": self.locale, "resolved_from": "", "origin": ""},
            {"key": "subtitle_language", "value": self.subtitle_language, "resolved_from": "", "origin": ""},
        ]
        resolver_rows = (
            ("voice.provider", k.KEY_VOICE_PROVIDER, self.voice_provider),
            ("voice.voice_profile", k.KEY_VOICE_PROFILE, self.voice_profile_id),
            ("voice.model_id", k.KEY_VOICE_MODEL_ID, self.tts_model),
            ("voice.fallback_policy", k.KEY_VOICE_FALLBACK_POLICY, self.fallback_policy),
        )
        for label, key, value in resolver_rows:
            resolved = None
            if self.config is not None and key in self.config:
                resolved = self.config.resolved(key)
            rows.append(
                {
                    "key": label,
                    "value": value,
                    "resolved_from": resolved.source if resolved else "",
                    "origin": resolved.origin if resolved else "",
                    "warnings": list(resolved.warnings) if resolved else [],
                }
            )
        rows.append(
            {
                "key": "voice_id",
                "value": self.resolved_voice_id,
                "resolved_from": "voices.yaml",
                "origin": f"config/channels/*/voices.yaml#{self.voice_profile_id}" if self.voice_profile_id else "",
            }
        )
        rows.append(
            {
                "key": self.secret_env_var or "secret",
                "value": "настроен" if self.secret_configured else "не настроен",
                "resolved_from": "environment" if self.secret_required else "не требуется",
                "origin": "environment",
            }
        )
        rows.append(
            {
                "key": "narration_source",
                "value": self.narration_source,
                "resolved_from": "fallback_policy" if self.fallback_applied else "voice.output_mode",
                "origin": self.fallback_reason,
            }
        )
        for row in rows:
            row.setdefault("warnings", [])
        return rows


__all__ = [
    "ISSUE_COMPAT_DEFAULT_PROFILE",
    "ISSUE_DUPLICATE_LOCALIZATION_ID",
    "ISSUE_DUPLICATE_OUTPUT_PATH",
    "ISSUE_EXISTING_NARRATION_LANGUAGE_MISMATCH",
    "ISSUE_EXISTING_NARRATION_PROFILE_MISMATCH",
    "ISSUE_FALLBACK_UNAVAILABLE",
    "ISSUE_LOCAL_TTS_UNAVAILABLE",
    "ISSUE_MANUAL_AUDIO_MISSING",
    "ISSUE_MULTIPLE_ACTIVE_SOURCES",
    "ISSUE_NO_PROVIDER",
    "ISSUE_PATH_OUTSIDE_PROJECT",
    "ISSUE_SECRET_IN_CONFIG",
    "ISSUE_SECRET_MISSING",
    "ISSUE_UNKNOWN_LANGUAGE",
    "ISSUE_UNKNOWN_LOCALE",
    "ISSUE_UNKNOWN_NARRATION_SOURCE",
    "ISSUE_UNKNOWN_PROVIDER",
    "ISSUE_VOICE_ID_MISSING",
    "ISSUE_VOICE_PROFILE_DISABLED",
    "ISSUE_VOICE_PROFILE_LANGUAGE_MISMATCH",
    "ISSUE_VOICE_PROFILE_NOT_FOUND",
    "ISSUE_VOICE_PROFILE_PROVIDER_MISMATCH",
    "NARRATION_SOURCES",
    "NARRATION_SOURCE_EXISTING_ARTIFACT",
    "NARRATION_SOURCE_MANUAL_AUDIO",
    "NARRATION_SOURCE_NONE",
    "NARRATION_SOURCE_TTS",
    "SEVERITY_ERROR",
    "SEVERITY_WARNING",
    "STATUS_AWAITING_SOURCE",
    "STATUS_BLOCKED",
    "STATUS_COMPLETED",
    "STATUS_MANUAL_AUDIO_READY",
    "STATUS_READY_FOR_GENERATION",
    "STATUS_SKIPPED",
    "TTS_BLOCKED_EXISTING_NARRATION",
    "TTS_BLOCKED_LOCAL_TTS_UNAVAILABLE",
    "TTS_BLOCKED_MANUAL_SOURCE",
    "TTS_BLOCKED_NO_PROVIDER",
    "TTS_BLOCKED_SECRET_MISSING",
    "TTS_BLOCKED_VALIDATION_ERROR",
    "TTS_BLOCKED_VOICE_DISABLED",
    "LocalizationError",
    "LocalizationIssue",
    "ResolvedLocalization",
]
