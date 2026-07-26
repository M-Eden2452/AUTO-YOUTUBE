"""Which settings the resolver knows about, and what each one falls back to.

Every entry here is a setting that some file on disk really carries or some module
really reads. Nothing is invented: ``default`` repeats the value that is hardcoded in
the consumer today, and ``consumers`` names the modules that actually read the setting
at this commit. A key with an empty ``consumers`` tuple is a setting that exists in
``channels/<id>/channel_config.json`` but that no code reads yet - the resolver reports
it with an ``no_consumer_yet`` warning instead of pretending it has an effect.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

TYPE_STR = "str"
TYPE_INT = "int"
TYPE_FLOAT = "float"
TYPE_BOOL = "bool"
# Provider-specific tuning that is passed through verbatim (VoicePolicy.provider_settings).
TYPE_DICT = "dict"
# A key whose value is never read, only its presence. See models.ResolvedValue.
TYPE_SECRET_PRESENCE = "secret_presence"

VALUE_TYPES = frozenset({TYPE_STR, TYPE_INT, TYPE_FLOAT, TYPE_BOOL, TYPE_DICT, TYPE_SECRET_PRESENCE})


@dataclass(frozen=True)
class SettingDefinition:
    key: str
    value_type: str
    default: Any
    description: str
    # Modules that read this setting today. Empty = configured but not wired anywhere.
    consumers: tuple[str, ...] = ()
    # Only for TYPE_SECRET_PRESENCE: the environment variable whose presence is checked.
    env_var: str = ""

    @property
    def is_secret(self) -> bool:
        return self.value_type == TYPE_SECRET_PRESENCE

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "value_type": self.value_type,
            "default": self.default,
            "description": self.description,
            "consumers": list(self.consumers),
            "is_secret": self.is_secret,
            "env_var": self.env_var,
        }


KEY_LANGUAGE = "language"
KEY_TARGET_DURATION = "target_duration_sec"
KEY_MIN_DURATION = "min_duration_sec"
KEY_MAX_DURATION = "max_duration_sec"
KEY_WIDTH = "resolution.width"
KEY_HEIGHT = "resolution.height"
KEY_ASPECT_RATIO = "aspect_ratio"
KEY_FPS = "fps"
KEY_VOICE_ENABLED = "voice.enabled"
KEY_VOICE_REQUIRED = "voice.required"
KEY_VOICE_PROVIDER = "voice.provider"
KEY_VOICE_PROFILE = "voice.voice_profile"
KEY_VOICE_MODEL_ID = "voice.model_id"
KEY_VOICE_OUTPUT_MODE = "voice.output_mode"
KEY_VOICE_TIMING_MODE = "voice.timing_mode"
KEY_VOICE_APPROVAL_REQUIRED = "voice.approval_required"
KEY_VOICE_AUDITION_REQUIRED = "voice.audition_required"
KEY_VOICE_SCENE_LEVEL = "voice.scene_level_generation"
KEY_VOICE_FALLBACK_POLICY = "voice.fallback_policy"
KEY_VOICE_FAILURE_POLICY = "voice.failure_policy"
KEY_VOICE_OUTPUT_FORMAT = "voice.output_format"
KEY_VOICE_SAMPLE_RATE = "voice.target_sample_rate"
KEY_VOICE_CHANNELS = "voice.target_channels"
KEY_VOICE_SPEED = "voice.speed"
KEY_VOICE_PROVIDER_SETTINGS = "voice.provider_settings"
KEY_SUBTITLES_ENABLED = "subtitles.enabled"
KEY_SUBTITLES_STYLE = "subtitles.style"
KEY_MUSIC_ENABLED = "music.enabled"
KEY_MUSIC_DUCKING = "music.ducking"
KEY_SECRET_ELEVENLABS = "secrets.elevenlabs_api_key"
KEY_SECRET_OPENAI = "secrets.openai_api_key"
KEY_SECRET_PEXELS = "secrets.pexels_api_key"
KEY_SECRET_PIXABAY = "secrets.pixabay_api_key"


SETTINGS: tuple[SettingDefinition, ...] = (
    SettingDefinition(
        key=KEY_LANGUAGE,
        value_type=TYPE_STR,
        # src.news.models.NewsJob.create(language="ru") and
        # src.project_foundation.models.ProjectManifest.language both default to "ru".
        default="ru",
        description="Язык проекта.",
        consumers=("src.news.pipeline", "src.project_foundation.projects", "src.content_creation.service"),
    ),
    SettingDefinition(
        key=KEY_TARGET_DURATION,
        value_type=TYPE_INT,
        # src.content_creation.service._create_via_news_to_short() ends its chain at 55,
        # and NewsJob.target_duration_sec is 55 as well.
        default=55,
        description="Целевая длительность ролика в секундах.",
        consumers=("src.news.pipeline", "src.content.script_engine"),
    ),
    SettingDefinition(
        key=KEY_MIN_DURATION,
        value_type=TYPE_INT,
        default=None,
        description="Минимально допустимая длительность. Есть в channel_config.json, но пока не читается.",
    ),
    SettingDefinition(
        key=KEY_MAX_DURATION,
        value_type=TYPE_INT,
        default=None,
        description="Максимально допустимая длительность. Есть в channel_config.json, но пока не читается.",
    ),
    SettingDefinition(
        key=KEY_WIDTH,
        value_type=TYPE_INT,
        default=1080,  # NewsJob.resolution default
        description="Ширина кадра.",
        consumers=("src.news.final_renderer", "src.production_plan.story_card_short_render"),
    ),
    SettingDefinition(
        key=KEY_HEIGHT,
        value_type=TYPE_INT,
        default=1920,  # NewsJob.resolution default
        description="Высота кадра.",
        consumers=("src.news.final_renderer", "src.production_plan.story_card_short_render"),
    ),
    SettingDefinition(
        key=KEY_ASPECT_RATIO,
        value_type=TYPE_STR,
        default="9:16",  # NewsJob.aspect_ratio
        description="Соотношение сторон.",
        consumers=("src.news.models",),
    ),
    SettingDefinition(
        key=KEY_FPS,
        value_type=TYPE_INT,
        # 30 is hardcoded in the ffmpeg filter of src/news/final_renderer.py and in
        # config/render_presets/story_card_short_v1.json; channel_config.json also
        # says 30, but nothing reads it from there.
        default=30,
        description="Кадров в секунду. Сейчас зашито в рендерер, из конфигурации не читается.",
    ),
    SettingDefinition(
        key=KEY_VOICE_ENABLED,
        value_type=TYPE_BOOL,
        default=True,  # VoicePolicy.enabled
        description="Разрешена ли озвучка.",
        consumers=("src.audio.voice_policy", "src.news.voice_stage"),
    ),
    SettingDefinition(
        key=KEY_VOICE_REQUIRED,
        value_type=TYPE_BOOL,
        default=False,  # VoicePolicy.required
        description="Обязательна ли озвучка для шаблона.",
        consumers=("src.audio.voice_policy", "src.news.voice_stage"),
    ),
    SettingDefinition(
        key=KEY_VOICE_PROVIDER,
        value_type=TYPE_STR,
        default="",  # VoicePolicy.provider
        description="Провайдер TTS.",
        consumers=("src.news.voice_adapter", "src.audio.narration_workflow"),
    ),
    SettingDefinition(
        key=KEY_VOICE_PROFILE,
        value_type=TYPE_STR,
        default="",  # VoicePolicy.voice_profile
        description="Идентификатор голосового профиля из voices.yaml.",
        consumers=("src.news.voice_adapter", "src.audio.voice_profile_registry"),
    ),
    SettingDefinition(
        key=KEY_VOICE_MODEL_ID,
        value_type=TYPE_STR,
        default="",  # VoicePolicy.model_id
        description="Модель TTS.",
        consumers=("src.news.voice_adapter", "src.audio.narration_workflow"),
    ),
    SettingDefinition(
        key=KEY_VOICE_OUTPUT_MODE,
        value_type=TYPE_STR,
        default="disabled",  # VoicePolicy.output_mode
        description="Как производится звук: scene_audio / single_narration / manual_audio / disabled.",
        consumers=("src.audio.voice_policy", "src.news.voice_stage"),
    ),
    SettingDefinition(
        key=KEY_VOICE_TIMING_MODE,
        value_type=TYPE_STR,
        default="adaptive",  # VoicePolicy.timing_mode
        description="Чем задаётся тайминг сцен.",
        consumers=("src.audio.voice_policy", "src.audio.scene_timeline"),
    ),
    SettingDefinition(
        key=KEY_VOICE_APPROVAL_REQUIRED,
        value_type=TYPE_BOOL,
        default=True,  # VoicePolicy.approval_required
        description="Нужно ли подтверждение перед платной генерацией.",
        consumers=("src.audio.voice_workflow", "src.content_creation.service"),
    ),
    SettingDefinition(
        key=KEY_VOICE_AUDITION_REQUIRED,
        value_type=TYPE_BOOL,
        default=True,  # VoicePolicy.audition_required
        description="Нужно ли подтверждение перед пробой голоса.",
        consumers=("src.audio.voice_workflow",),
    ),
    SettingDefinition(
        key=KEY_VOICE_SCENE_LEVEL,
        value_type=TYPE_BOOL,
        default=False,  # VoicePolicy.scene_level_generation
        description="Генерировать озвучку посценно, а не одним файлом.",
        consumers=("src.audio.voice_policy", "src.news.voice_stage"),
    ),
    SettingDefinition(
        key=KEY_VOICE_FALLBACK_POLICY,
        value_type=TYPE_STR,
        default="none",  # VoicePolicy.fallback_policy
        description="Что делать, если основной провайдер недоступен.",
        consumers=("src.audio.voice_policy", "src.news.voice_stage"),
    ),
    SettingDefinition(
        key=KEY_VOICE_FAILURE_POLICY,
        value_type=TYPE_STR,
        default="block",  # VoicePolicy.failure_policy
        description="Что делать при ошибке озвучки.",
        consumers=("src.audio.voice_policy",),
    ),
    SettingDefinition(
        key=KEY_VOICE_OUTPUT_FORMAT,
        value_type=TYPE_STR,
        default="wav",  # VoicePolicy.output_format
        description="Формат файла озвучки.",
        consumers=("src.audio.narration_workflow",),
    ),
    SettingDefinition(
        key=KEY_VOICE_SAMPLE_RATE,
        value_type=TYPE_INT,
        default=48000,  # VoicePolicy.target_sample_rate
        description="Частота дискретизации озвучки.",
        consumers=("src.audio.narration_workflow",),
    ),
    SettingDefinition(
        key=KEY_VOICE_CHANNELS,
        value_type=TYPE_INT,
        default=1,  # VoicePolicy.target_channels
        description="Число аудиоканалов озвучки.",
        consumers=("src.audio.narration_workflow",),
    ),
    SettingDefinition(
        key=KEY_VOICE_SPEED,
        value_type=TYPE_FLOAT,
        default=None,  # VoicePolicy.speed
        description="Скорость речи.",
        consumers=("src.audio.narration_workflow",),
    ),
    SettingDefinition(
        key=KEY_VOICE_PROVIDER_SETTINGS,
        value_type=TYPE_DICT,
        default=None,  # VoicePolicy.provider_settings (пустой dict по умолчанию)
        description="Настройки провайдера TTS, передаются как есть.",
        consumers=("src.audio.narration_workflow",),
    ),
    SettingDefinition(
        key=KEY_SUBTITLES_ENABLED,
        value_type=TYPE_BOOL,
        # SubtitleRequestConfig.style defaults to "disabled".
        default=False,
        description="Включены ли субтитры.",
        consumers=("src.content_creation.service", "src.news.subtitles"),
    ),
    SettingDefinition(
        key=KEY_SUBTITLES_STYLE,
        value_type=TYPE_STR,
        default="disabled",  # SubtitleRequestConfig.style
        description="Стиль субтитров из capabilities.list_subtitle_styles().",
        consumers=("src.content_creation.service",),
    ),
    SettingDefinition(
        key=KEY_MUSIC_ENABLED,
        value_type=TYPE_BOOL,
        default=False,  # MusicRequestConfig.mode == "disabled"
        description="Подмешивается ли музыка.",
        consumers=("src.content_creation.service", "src.audio.music_manifest"),
    ),
    SettingDefinition(
        key=KEY_MUSIC_DUCKING,
        value_type=TYPE_BOOL,
        # src/news/final_renderer.py: music_manifest.get("ducking", True)
        default=True,
        description="Приглушать ли музыку под голосом.",
        consumers=("src.news.final_renderer", "src.audio.music_manifest"),
    ),
    SettingDefinition(
        key=KEY_SECRET_ELEVENLABS,
        value_type=TYPE_SECRET_PRESENCE,
        default=False,
        description="Настроен ли ключ ElevenLabs (значение не читается).",
        consumers=("src.audio.tts.env", "src.voice_engine"),
        env_var="ELEVENLABS_API_KEY",
    ),
    SettingDefinition(
        key=KEY_SECRET_OPENAI,
        value_type=TYPE_SECRET_PRESENCE,
        default=False,
        description="Настроен ли ключ OpenAI (значение не читается).",
        consumers=("src.assets.semantic_visual_openai",),
        env_var="OPENAI_API_KEY",
    ),
    SettingDefinition(
        key=KEY_SECRET_PEXELS,
        value_type=TYPE_SECRET_PRESENCE,
        default=False,
        description="Настроен ли ключ Pexels (значение не читается).",
        consumers=("src.news.asset_manager", "src.assets.provider_diagnostics"),
        env_var="PEXELS_API_KEY",
    ),
    SettingDefinition(
        key=KEY_SECRET_PIXABAY,
        value_type=TYPE_SECRET_PRESENCE,
        default=False,
        description="Настроен ли ключ Pixabay (значение не читается).",
        consumers=("src.news.asset_manager", "src.assets.provider_diagnostics"),
        env_var="PIXABAY_API_KEY",
    ),
)

SETTINGS_BY_KEY: dict[str, SettingDefinition] = {setting.key: setting for setting in SETTINGS}

VOICE_KEYS: tuple[str, ...] = tuple(key for key in SETTINGS_BY_KEY if key.startswith("voice."))
SECRET_KEYS: tuple[str, ...] = tuple(key for key, s in SETTINGS_BY_KEY.items() if s.is_secret)


def get_setting(key: str) -> SettingDefinition:
    setting = SETTINGS_BY_KEY.get(key)
    if setting is None:
        known = ", ".join(sorted(SETTINGS_BY_KEY))
        raise KeyError(f"Неизвестная настройка {key!r}. Известны: {known}.")
    return setting


def list_keys() -> list[str]:
    return [setting.key for setting in SETTINGS]


__all__ = [
    "SECRET_KEYS",
    "SETTINGS",
    "SETTINGS_BY_KEY",
    "TYPE_BOOL",
    "TYPE_DICT",
    "TYPE_FLOAT",
    "TYPE_INT",
    "TYPE_SECRET_PRESENCE",
    "TYPE_STR",
    "VALUE_TYPES",
    "VOICE_KEYS",
    "SettingDefinition",
    "get_setting",
    "list_keys",
]
