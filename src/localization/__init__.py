"""Runtime-слой локализации: язык, locale и голос одной языковой версии проекта.

Второй системой локализаций или голосов это не является и являться не может:
профили голосов по-прежнему живут в ``config/channels/*/voices.yaml``
(``src.audio.voice_profile_registry``), политика звука - в
``src.audio.voice_policy``, приоритет слоёв - в ``src.config_resolver``, а
фактический результат озвучки - в ``localizations/<id>/voice/voice_manifest.json``
(``src.audio.voice_manifest``). Этот пакет только собирает их ответы в один
контракт и ничего не пишет.
"""

from .locales import (
    default_locale,
    display_name,
    is_known_language,
    known_language_codes,
    list_language_definitions,
    normalize_language,
    normalize_locale,
)
from .models import (
    NARRATION_SOURCE_EXISTING_ARTIFACT,
    NARRATION_SOURCE_MANUAL_AUDIO,
    NARRATION_SOURCE_NONE,
    NARRATION_SOURCE_TTS,
    STATUS_AWAITING_SOURCE,
    STATUS_BLOCKED,
    STATUS_COMPLETED,
    STATUS_MANUAL_AUDIO_READY,
    STATUS_READY_FOR_GENERATION,
    STATUS_SKIPPED,
    LocalizationError,
    LocalizationIssue,
    ResolvedLocalization,
)
from .resolver import COMPAT_DEFAULT_VOICE_PROFILE, resolve_localization
from .secrets import is_secret_configured, secret_env_var
from .validation import (
    validate_local_path,
    validate_localization_set,
    validate_stored_localization_config,
)

__all__ = [
    "COMPAT_DEFAULT_VOICE_PROFILE",
    "NARRATION_SOURCE_EXISTING_ARTIFACT",
    "NARRATION_SOURCE_MANUAL_AUDIO",
    "NARRATION_SOURCE_NONE",
    "NARRATION_SOURCE_TTS",
    "STATUS_AWAITING_SOURCE",
    "STATUS_BLOCKED",
    "STATUS_COMPLETED",
    "STATUS_MANUAL_AUDIO_READY",
    "STATUS_READY_FOR_GENERATION",
    "STATUS_SKIPPED",
    "LocalizationError",
    "LocalizationIssue",
    "ResolvedLocalization",
    "default_locale",
    "display_name",
    "is_known_language",
    "is_secret_configured",
    "known_language_codes",
    "list_language_definitions",
    "normalize_language",
    "normalize_locale",
    "resolve_localization",
    "secret_env_var",
    "validate_local_path",
    "validate_localization_set",
    "validate_stored_localization_config",
]
