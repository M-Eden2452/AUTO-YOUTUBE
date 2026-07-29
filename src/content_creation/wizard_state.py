from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.content_creation.models import ContentCreationRequest
from src.content_creation.request_builder import from_wizard_state


START_ACTIONS = [
    ("new", "Создать новый ролик"),
    ("resume", "Продолжить незавершённый проект"),
]

# Templates whose workflow can genuinely pick a project back up mid-way. Story card
# is not one of them: it has no stages, and re-running it needs the source file and
# card text again, which the project view does not carry.
RESUMABLE_TEMPLATE_IDS = {"fullscreen_voiceover_v1"}

STAGE_LABELS_RU = {
    "input": "ввод",
    "article_ingestion": "загрузка статьи",
    "research": "проверка фактов",
    "script": "сценарий",
    "visual_plan": "визуальный план",
    "asset_search": "подбор материалов",
    "voice": "озвучка",
    "subtitles": "субтитры",
    "preview_render": "превью",
    "quality_check": "контроль качества",
    "final_render": "финальный рендер",
    "export": "экспорт",
}

CONTENT_INPUT_MODES = [
    ("topic", "Тема (тема ролика, сценарий сгенерируется автоматически)"),
    ("article_url", "Ссылка на статью"),
    ("pasted_script", "Готовый текст (вставить сценарий целиком)"),
    ("script_file", "Файл со сценарием (.txt/.md)"),
]

TARGET_DURATION_CHOICES = [
    ("50", "50 секунд — рекомендуемый Shorts"),
    ("45", "45 секунд"),
    ("55", "55 секунд"),
    ("30", "30 секунд"),
    ("60", "60 секунд"),
    ("90", "90 секунд"),
    ("manual", "Указать вручную"),
]

RECOVERABLE_INPUT_REASONS = {
    "empty",
    "too_long",
    "bad_scheme",
    "no_host",
    "search_engine_url",
    "http_429",
    "http_403",
    "timeout",
    "connection_error",
    "request_error",
    "empty_article",
    "invalid_content",
    "not_found",
    "unsupported_extension",
    "bad_encoding",
    "read_error",
}


def profiles_for_language(
    profiles: list[dict[str, Any]],
    language: str,
) -> list[dict[str, Any]]:
    """Return only voices that can speak the selected localization."""
    from src.localization import normalize_language

    target = normalize_language(language) or str(language or "")

    def speaks_target(profile: dict[str, Any]) -> bool:
        declared = str(profile.get("language") or "")
        if not declared:
            return True
        return (normalize_language(declared) or declared) == target

    return [profile for profile in profiles if speaks_target(profile)]


def voice_profile_label(profile: dict[str, Any], channel_id: str) -> str:
    """Show where a profile comes from when it is borrowed from another channel."""
    label = f"{profile['display_name']} ({profile['profile_id']})"
    source = profile.get("source_channel_id", "")
    if source and source != channel_id:
        label += f" — из канала {source}"
    return label


@dataclass
class WizardState:
    format_id: str = ""
    template_id: str = ""
    channel_id: str = ""
    language: str = "ru"
    title: str = ""
    content_input_mode: str = ""
    topic: str = ""
    source_url: str = ""
    pasted_script: str = ""
    script_path: str = ""
    text_top: str = ""
    source_asset_path: str = ""
    target_duration_sec: int = 55
    project_id: str = ""
    voice_provider: str = "disabled"
    voice_profile: str = ""
    voice_profile_display_name: str = ""
    voice_profile_model_id: str = ""
    voice_mode: str = "disabled"
    audio_file: str = ""
    subtitle_style: str = "disabled"
    music_mode: str = "disabled"
    music_path: str = ""
    timing_mode: str = ""
    dry_run: bool = False
    approve_paid_generation: bool = False
    prepare_only: bool = False


def build_request(
    state: WizardState,
    *,
    project_overrides: dict[str, Any] | None = None,
) -> ContentCreationRequest:
    return from_wizard_state(
        state,
        project_overrides=project_overrides,
    )


__all__ = [
    "CONTENT_INPUT_MODES",
    "RECOVERABLE_INPUT_REASONS",
    "RESUMABLE_TEMPLATE_IDS",
    "STAGE_LABELS_RU",
    "START_ACTIONS",
    "TARGET_DURATION_CHOICES",
    "WizardState",
    "build_request",
    "profiles_for_language",
    "voice_profile_label",
]
