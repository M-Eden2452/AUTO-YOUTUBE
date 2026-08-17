from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.runtime_network import (
    NETWORK_ACTION_ARTICLE_FETCH,
    NETWORK_ACTION_ASSET_DOWNLOAD,
    NETWORK_ACTION_PREVIEW_DOWNLOAD,
    NETWORK_ACTION_PROVIDER_SEARCH,
    NETWORK_ACTION_VOICE_PREFLIGHT,
    NETWORK_ACTION_VOICE_SYNTHESIS,
)

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
    # Explicit network approval for this run, in the same shape the CLI's
    # repeatable --allow-network produces. Empty means deny, and it stays empty
    # unless the user answers the network step - reviewed only records that the
    # question was already put, so a two-phase paid run does not ask twice.
    allow_network: tuple[str, ...] = ()
    network_access_reviewed: bool = False


def required_network_actions(state: WizardState) -> tuple[str, ...]:
    """Which network classes this particular wizard run would actually reach.

    The wizard asks about exactly these and nothing more, so answering "yes"
    never approves a class the run has no use for. A dry run only ever reaches
    article ingestion: the asset stage builds an empty provider set for it
    (see src.news.asset_manager.build_news_asset_manifest).
    """
    actions: list[str] = []
    if state.content_input_mode == "article_url" or state.source_url:
        actions.append(NETWORK_ACTION_ARTICLE_FETCH)
    if state.template_id == "fullscreen_voiceover_v1" and not state.dry_run:
        actions.extend(
            (
                NETWORK_ACTION_PROVIDER_SEARCH,
                NETWORK_ACTION_ASSET_DOWNLOAD,
                NETWORK_ACTION_PREVIEW_DOWNLOAD,
            )
        )
    if state.voice_provider == "elevenlabs" and not state.dry_run:
        # Both classes, asked once. The paid generation is a separate and second
        # gate, so naming synthesis here approves reaching the network, never
        # spending: a run whose paid confirmation is declined simply never calls
        # it. Asking only for preflight looked narrower and was in fact broken -
        # the two-phase paid flow captures allow_network in its first phase and
        # never asks again (run_creation_with_preflight), so the phase that pays
        # would be refused inside the provider, after the owner had already
        # approved everything the wizard showed them.
        actions.extend(
            (NETWORK_ACTION_VOICE_PREFLIGHT, NETWORK_ACTION_VOICE_SYNTHESIS)
        )
    return tuple(dict.fromkeys(actions))


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
    "required_network_actions",
    "voice_profile_label",
]
