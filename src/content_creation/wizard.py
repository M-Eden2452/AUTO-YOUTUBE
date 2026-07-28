from __future__ import annotations

import inspect
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from src.content_creation import capabilities, input_validation, languages
from src.content_creation.models import (
    ContentCreationError,
    ContentCreationRequest,
    ContentCreationResult,
    ExecutionFlags,
    MusicRequestConfig,
    SubtitleRequestConfig,
    TimingRequestConfig,
    VoiceRequestConfig,
)
from src.content_creation.output_report import describe_output_file
from src.content_creation.service import create_content
from src.production_catalog.catalog import get_default_catalog

CANCEL = "__cancel__"

# ---------------------------------------------------------------------------
# Visual theme (Stage 2E.1 Phase 9): icons + questionary Style, with an ASCII
# fallback for terminals that can't render emoji (or --no-icons/non-TTY).
# ---------------------------------------------------------------------------

ICONS_UNICODE: dict[str, str] = {
    "format": "🎬",
    "template": "🧩",
    "channel": "📺",
    "language": "🌐",
    "input": "📝",
    "voice": "🗣",
    "subtitles": "💬",
    "music": "🎵",
    "timing": "⏱",
    "check": "🔍",
    "paid": "💳",
    "launch": "🚀",
    "success": "✅",
    "warning": "⚠",
    "error": "❌",
    "blocked": "⛔",
}

ICONS_ASCII: dict[str, str] = {
    "format": "[*]",
    "template": "[*]",
    "channel": "[*]",
    "language": "[*]",
    "input": "[>]",
    "voice": "[*]",
    "subtitles": "[*]",
    "music": "[*]",
    "timing": "[*]",
    "check": "[>]",
    "paid": "[$]",
    "launch": "[>]",
    "success": "[OK]",
    "warning": "[!]",
    "error": "[X]",
    "blocked": "[!!]",
}

# Maps a real stage/result status string to an icon key - never a blanket
# "completed = checkmark"; see _create_fullscreen_voiceover in service.py, which
# now only reports "completed" when the manifest actually has an audio_path/
# output_path, so this mapping can trust the status it's given.
_STATUS_ICON_KEYS: dict[str, str] = {
    "completed": "success",
    "dry_run_completed": "success",
    "needs_review": "warning",
    "prepared_awaiting_render": "warning",
    "prepared_awaiting_paid_approval": "paid",
    "skipped_existing_output": "warning",
    "blocked": "blocked",
    "failed": "error",
}


def _status_icon_key(status: str) -> str:
    return _STATUS_ICON_KEYS.get(status, "warning")


def choose_icon_set(*, no_icons: bool = False) -> dict[str, str]:
    if no_icons:
        return ICONS_ASCII
    encoding = getattr(sys.stdout, "encoding", None) or ""
    try:
        "🎬".encode(encoding or "utf-8")
    except (LookupError, UnicodeEncodeError):
        return ICONS_ASCII
    return ICONS_UNICODE


def _tag(icons: dict[str, str], key: str, message: str) -> str:
    return f"{icons.get(key, '')} {message}".strip()


def build_questionary_style():
    import questionary

    return questionary.Style(
        [
            ("qmark", "fg:#00afff bold"),
            ("question", "bold"),
            ("answer", "fg:#00d787 bold"),
            ("pointer", "fg:#00afff bold"),
            ("highlighted", "fg:#00afff bold"),
            ("selected", "fg:#00d787"),
            ("instruction", "fg:#8a8a8a"),
            ("text", ""),
            ("disabled", "fg:#858585 italic"),
        ]
    )


# ---------------------------------------------------------------------------
# Prompt adapters
# ---------------------------------------------------------------------------


class PromptAdapter(Protocol):
    """Thin prompting interface so tests can inject canned answers instead of a
    real terminal. Both concrete adapters below (interactive and plain-text
    fallback) implement this, and it's what a test's ScriptedAdapter mocks."""

    def select(self, message: str, choices: list[tuple[str, str]], *, allow_cancel: bool = True) -> str: ...

    def text(self, message: str, default: str = "") -> str: ...

    def confirm(self, message: str, default: bool = False) -> bool: ...


class PlainAdapter:
    """Numbered-question fallback for non-interactive terminals (no arrow keys)."""

    def select(self, message: str, choices: list[tuple[str, str]], *, allow_cancel: bool = True) -> str:
        print(message)
        options = list(choices)
        if allow_cancel:
            options = [*options, (CANCEL, "Отмена")]
        for index, (_, label) in enumerate(options, start=1):
            print(f"  {index}) {label}")
        while True:
            raw = input(f"Введите номер (1-{len(options)}): ").strip()
            if raw.isdigit() and 1 <= int(raw) <= len(options):
                return options[int(raw) - 1][0]
            print("Некорректный ввод, попробуйте снова.")

    def text(self, message: str, default: str = "") -> str:
        suffix = f" [{default}]" if default else ""
        raw = input(f"{message}{suffix}: ").strip()
        return raw or default

    def confirm(self, message: str, default: bool = False) -> bool:
        suffix = "[Y/n]" if default else "[y/N]"
        raw = input(f"{message} {suffix}: ").strip().lower()
        if not raw:
            return default
        return raw in ("y", "yes", "д", "да")


class QuestionaryAdapter:
    """Arrow-key interactive adapter, used when stdout/stdin is a real TTY."""

    def __init__(self) -> None:
        import questionary

        self._questionary = questionary
        self._style = build_questionary_style()

    def select(self, message: str, choices: list[tuple[str, str]], *, allow_cancel: bool = True) -> str:
        options = list(choices)
        if allow_cancel:
            options = [*options, (CANCEL, "Отмена")]
        answer = self._questionary.select(
            message, choices=[label for _, label in options], style=self._style
        ).ask()
        if answer is None:
            return CANCEL
        for value, label in options:
            if label == answer:
                return value
        return CANCEL

    def text(self, message: str, default: str = "") -> str:
        answer = self._questionary.text(message, default=default, style=self._style).ask()
        return answer if answer is not None else default

    def confirm(self, message: str, default: bool = False) -> bool:
        answer = self._questionary.confirm(message, default=default, style=self._style).ask()
        return bool(answer) if answer is not None else default


def _default_adapter() -> PromptAdapter:
    if sys.stdin.isatty() and sys.stdout.isatty():
        try:
            return QuestionaryAdapter()
        except Exception:
            return PlainAdapter()
    return PlainAdapter()


# ---------------------------------------------------------------------------
# Wizard working state (UI-local staging area - converted to a real
# ContentCreationRequest only once the user confirms, via _build_request()).
# ---------------------------------------------------------------------------

START_ACTIONS = [
    ("new", "Создать новый ролик"),
    ("resume", "Продолжить незавершённый проект"),
]

# Templates whose workflow can genuinely pick a project back up mid-way. Story card
# is not one of them: it has no stages, and re-running it needs the source file and
# card text again, which the project view does not carry. Offering "continue" for a
# template that would then ask for everything anyway is worse than not offering it.
RESUMABLE_TEMPLATE_IDS = {"fullscreen_voiceover_v1"}

# Shown next to a project in the resume list, so "where did I stop" is readable.
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


def _profiles_for_language(profiles: list[dict[str, Any]], language: str) -> list[dict[str, Any]]:
    """Only the voices that can actually speak this localization.

    A profile with no declared language is kept: voices.yaml allows omitting it, and
    dropping such a profile would remove a voice that does work today. Comparison goes
    through src.localization normalization, so "ru" and "ru-RU" are the same language.
    """
    from src.localization import normalize_language

    target = normalize_language(language) or str(language or "")

    def speaks_target(profile: dict[str, Any]) -> bool:
        declared = str(profile.get("language") or "")
        if not declared:
            return True
        return (normalize_language(declared) or declared) == target

    return [profile for profile in profiles if speaks_target(profile)]


def _voice_profile_label(profile: dict[str, Any], channel_id: str) -> str:
    """Show where a profile comes from when it is borrowed from another channel."""
    label = f"{profile['display_name']} ({profile['profile_id']})"
    source = profile.get("source_channel_id", "")
    if source and source != channel_id:
        label += f" — из канала {source}"
    return label

TARGET_DURATION_CHOICES = [
    ("50", "50 секунд — рекомендуемый Shorts"),
    ("45", "45 секунд"),
    ("55", "55 секунд"),
    ("30", "30 секунд"),
    ("60", "60 секунд"),
    ("90", "90 секунд"),
    ("manual", "Указать вручную"),
]

# reasons from ContentCreationError worth a retry/change-input recovery menu,
# rather than just bailing out - kept here (not in input_validation/service) since
# it is purely about what the *wizard* offers the user next.
_RECOVERABLE_INPUT_REASONS = {
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


@dataclass
class _WizardState:
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


def _build_request(
    state: _WizardState,
    *,
    project_overrides: dict[str, Any] | None = None,
) -> ContentCreationRequest:
    text: dict[str, str] = {"top": state.text_top} if state.text_top else {}
    video_first = state.template_id == "fullscreen_voiceover_v1"
    return ContentCreationRequest(
        project_id=state.project_id,
        title=state.title,
        channel_id=state.channel_id,
        format_id=state.format_id,
        template_id=state.template_id,
        language=state.language,
        content_input_mode=state.content_input_mode,
        topic=state.topic,
        source_url=state.source_url,
        pasted_script=state.pasted_script,
        script_path=state.script_path,
        text=text,
        source_asset_path=state.source_asset_path,
        target_duration_sec=state.target_duration_sec,
        voice=VoiceRequestConfig(
            provider=state.voice_provider,
            profile=state.voice_profile,
            mode=state.voice_mode,
            audio_file=state.audio_file,
            approve_paid_generation=state.approve_paid_generation,
        ),
        subtitles=SubtitleRequestConfig(style=state.subtitle_style),
        music=MusicRequestConfig(mode=state.music_mode, path=state.music_path),
        timing=TimingRequestConfig(mode=state.timing_mode),
        execution=ExecutionFlags(
            dry_run=state.dry_run, prepare_only=state.prepare_only, resume=bool(state.project_id)
        ),
        # The Wizard owns no creation logic: these are the working defaults it passes
        # into the same service used by the flag-based CLI.
        completion_mode="draft_complete" if video_first else "",
        script_adaptation="light" if video_first else "",
        project_overrides=dict(project_overrides or {}),
    )


class _Cancelled(Exception):
    pass


class _Wizard:
    """Holds the prompt adapter/icons/catalog for one wizard run so the many
    small `_choose_*` step methods don't have to thread them through as
    parameters. Pure presentation + validation glue: every choice list comes
    from the same registries/catalog the flag-based `create` command uses, and
    business rules (music path validation, URL rejection, ...) are the same
    src.content_creation.input_validation/capabilities helpers `create` uses."""

    def __init__(
        self,
        prompt: PromptAdapter,
        icons: dict[str, str],
        create_fn,
        *,
        project_overrides: dict[str, Any] | None = None,
    ) -> None:
        self.prompt = prompt
        self.icons = icons
        self.create_fn = create_fn
        self.project_overrides = dict(project_overrides or {})
        self.catalog = get_default_catalog()

    def _select(self, key: str, message: str, choices: list[tuple[str, str]]) -> str:
        value = self.prompt.select(_tag(self.icons, key, message), choices)
        if value == CANCEL:
            raise _Cancelled()
        return value

    def _text(self, key: str, message: str, default: str = "") -> str:
        return self.prompt.text(_tag(self.icons, key, message), default=default)

    def _confirm(self, key: str, message: str, default: bool = False) -> bool:
        return self.prompt.confirm(_tag(self.icons, key, message), default=default)

    def _template_caps(self, template_id: str) -> dict[str, Any]:
        return capabilities.describe_template_capabilities(template_id)

    # -- individual steps ---------------------------------------------------

    def choose_format(self, state: _WizardState) -> None:
        # A format is only offered when it has at least one enabled template. Without
        # this check, picking a format with no template (longform used to be one)
        # dead-ends in choose_template and aborts the whole wizard, losing every
        # answer the user had already given.
        choices = [
            (f.format_id, f"{f.display_name} ({f.format_id})")
            for f in self.catalog.formats.list_all()
            if f.enabled and any(t.enabled for t in self.catalog.templates.filter_by_format(f.format_id))
        ]
        if not choices:
            print("Нет ни одного формата с готовым шаблоном.")
            raise _Cancelled()
        state.format_id = self._select("format", "Формат видео:", choices)

    def choose_template(self, state: _WizardState) -> None:
        templates = [t for t in self.catalog.templates.filter_by_format(state.format_id) if t.enabled]
        if not templates:
            print(f"Для формата {state.format_id!r} пока нет доступных шаблонов.")
            raise _Cancelled()
        choices = [(t.template_id, f"{t.display_name} ({t.template_id})") for t in templates]
        state.template_id = self._select("template", "Шаблон:", choices)

    def choose_channel(self, state: _WizardState) -> None:
        # Only channels the chosen template can actually be created with - legacy
        # pipeline.py --channel/--video profiles (quotes/psychology/survival/
        # size_comparison) have a different schema entirely and would produce a run
        # that can never generate voice. See capabilities.list_channels_for_template.
        usable = (
            capabilities.list_channels_for_template(state.template_id)
            if state.template_id
            else [c for c in capabilities.list_channels() if c.get("usable_for_content_creation")]
        )
        choices = [(c["channel_id"], f"{c['display_name']} ({c['channel_id']})") for c in usable]
        if not choices:
            print(f"Нет ни одного канала, настроенного для шаблона {state.template_id!r}.")
            raise _Cancelled()
        state.channel_id = self._select("channel", "Канал:", choices)

    def choose_language(self, state: _WizardState) -> None:
        choices = [(item["code"], f"{item['display_name']} ({item['code']})") for item in languages.list_languages()]
        state.language = self._select("language", "Язык:", choices)
        channel = next((c for c in capabilities.list_channels() if c["channel_id"] == state.channel_id), None)
        template_caps = self._template_caps(state.template_id) if state.template_id else {"voice_required": False}
        profiles = capabilities.list_voice_profiles(state.channel_id) if state.channel_id else []
        for warning in languages.language_support_warnings(
            channel=channel, template_requires_voice=template_caps.get("voice_required", False),
            voice_profiles=profiles, language=state.language,
        ):
            print(_tag(self.icons, "warning", warning))

    def choose_content_input(self, state: _WizardState) -> None:
        if state.template_id == "story_card_text_only_v1":
            # Story Card has no script/article pipeline at all - it only ever
            # needs the card text + a local asset, so the topic/URL/script
            # source picker is not applicable and must not be shown.
            print("Текст карточки - главный визуальный слой этого шаблона (не дублируется субтитрами).")
            state.content_input_mode = ""
            state.topic = ""
            state.source_url = ""
            state.pasted_script = ""
            state.script_path = ""
            state.text_top = self._text("input", "Текст карточки:")
            state.source_asset_path = self._text("input", "Путь к локальному видео-ассету:")
            return

        state.content_input_mode = self._select("input", "Источник сценария:", CONTENT_INPUT_MODES)
        if state.content_input_mode == "topic":
            state.topic = self._text("input", "Тема ролика:")
            state.source_url = ""
            state.pasted_script = ""
            state.script_path = ""
        elif state.content_input_mode == "article_url":
            while True:
                state.source_url = self._text("input", "Ссылка на статью:")
                result = input_validation.validate_article_url(state.source_url)
                if result.valid:
                    break
                print(_tag(self.icons, "error", result.message))
                action = self._select(
                    "input",
                    "Что делать дальше?",
                    [
                        ("retry", "Ввести другую ссылку"),
                        ("use_topic", "Использовать только тему"),
                        ("pasted_script", "Вставить готовый текст"),
                    ],
                )
                if action == "use_topic":
                    state.content_input_mode = "topic"
                    state.topic = self._text("input", "Тема ролика:")
                    state.source_url = ""
                    return
                if action == "pasted_script":
                    state.content_input_mode = "pasted_script"
                    state.pasted_script = self._text("input", "Текст сценария:")
                    state.source_url = ""
                    return
            state.topic = ""
            state.pasted_script = ""
            state.script_path = ""
        elif state.content_input_mode == "pasted_script":
            state.pasted_script = self._text("input", "Текст сценария:")
            state.topic = ""
            state.source_url = ""
            state.script_path = ""
        elif state.content_input_mode == "script_file":
            while True:
                state.script_path = self._text("input", "Путь к файлу сценария (.txt/.md):")
                result = input_validation.validate_script_file(state.script_path)
                if result.valid:
                    break
                print(_tag(self.icons, "error", result.message))
                if not self._confirm("input", "Попробовать другой путь?", default=True):
                    raise _Cancelled()
            state.topic = ""
            state.source_url = ""
            state.pasted_script = ""

    def choose_title(self, state: _WizardState) -> None:
        """Name the video. Pre-filled, so the common case is one Enter press.

        This is what the project folder is named after. Before it existed, the
        folder was built from the topic - or, for a pasted script, from its first
        80 characters, which is how `wizard_установил_questionary_единственная_
        подходящая_библиотека__20260724T210156` came to exist.
        """
        from src.project_foundation.naming import build_project_id, suggest_title

        suggested = suggest_title(state.topic, state.text_top, state.pasted_script, state.source_url)
        while True:
            answer = self._text("input", "Название ролика:", default=suggested).strip()
            state.title = answer or suggested
            if state.title:
                break
            print(_tag(self.icons, "error", "Название не может быть пустым."))
        print(f"    Папка проекта будет называться: {build_project_id(state.title)}")

    def choose_target_duration(self, state: _WizardState) -> None:
        # Only fullscreen_voiceover_v1 (news_to_short) reads target_duration_sec
        # (see src.content_creation.service._create_fullscreen_voiceover) - story
        # card has no duration concept to pick.
        if state.template_id != "fullscreen_voiceover_v1":
            return
        choice = self._select("timing", "Желаемая длительность ролика:", TARGET_DURATION_CHOICES)
        if choice != "manual":
            state.target_duration_sec = int(choice)
            return
        while True:
            raw = self._text("timing", "Длительность в секундах (например 50):")
            if raw.strip().isdigit() and int(raw.strip()) > 0:
                state.target_duration_sec = int(raw.strip())
                return
            print(_tag(self.icons, "error", "Введите положительное целое число секунд."))

    def choose_voice(self, state: _WizardState) -> None:
        template_caps = self._template_caps(state.template_id)
        if not (template_caps["voice_required"] or template_caps["voice_allowed"]):
            state.voice_provider = "disabled"
            state.voice_profile = ""
            state.voice_profile_display_name = ""
            state.voice_profile_model_id = ""
            state.voice_mode = "disabled"
            state.audio_file = ""
            return
        providers = capabilities.list_voice_providers()
        if state.template_id == "fullscreen_voiceover_v1":
            # Enter should choose a working narrated Short when ElevenLabs is
            # configured. Disabled remains available, but is no longer the accidental
            # default for a template whose defining feature is voice-over.
            providers.sort(
                key=lambda item: (
                    0
                    if item["provider_id"] == "elevenlabs" and item.get("available")
                    else 1
                    if item["provider_id"] == "audio_file"
                    else 2
                )
            )
        provider_choices = [(p["provider_id"], f"{p['display_name']} ({p['provider_id']})") for p in providers]
        state.voice_provider = self._select("voice", "Источник озвучки:", provider_choices)
        state.voice_profile = ""
        state.voice_profile_display_name = ""
        state.voice_profile_model_id = ""
        state.audio_file = ""
        if state.voice_provider == "disabled":
            state.voice_mode = "disabled"
            return
        if state.voice_provider == "elevenlabs":
            profiles = _profiles_for_language(capabilities.list_voice_profiles(state.channel_id), state.language)
            if profiles:
                profile_choices = [(p["profile_id"], _voice_profile_label(p, state.channel_id)) for p in profiles]
                state.voice_profile = self._select("voice", "Голос:", profile_choices)
                self._resolve_profile_display(state)
            else:
                # Before D2 the wizard fell through to the "ru_dom" default here, so an
                # English localization was quietly given a Russian voice. Now it says so.
                state.voice_profile = ""
                state.voice_profile_display_name = ""
                state.voice_profile_model_id = ""
                print(
                    _tag(
                        self.icons,
                        "warning",
                        f"Нет голосового профиля для языка {state.language!r}. Добавьте голос в "
                        f"channels/{state.channel_id}/voices.yaml и укажите его в channel_config.json → "
                        f"languages.{state.language}.voice - иначе платная генерация не будет выполнена.",
                    )
                )
        elif state.voice_provider == "audio_file":
            state.audio_file = self._text("voice", "Путь к WAV-файлу озвучки:")
        # Output mode is a template policy decision, not a user choice: nothing in the
        # pipeline reads ContentCreationRequest.voice.mode, so asking for it only made
        # the wizard longer. audio_file always means manual_audio.
        state.voice_mode = (
            "manual_audio" if state.voice_provider == "audio_file" else template_caps["default_voice_mode"]
        )

    def _resolve_profile_display(self, state: _WizardState) -> None:
        """Resolve the chosen (or default) voice profile through the existing
        VoiceProfileRegistry so the summary/approval never show a blank
        "profile=-" for a profile that will actually be used downstream.

        capabilities.resolve_voice_profile now uses the same channel-then-global
        lookup as src.news.voice_adapter, so a profile accepted here is the profile
        the pipeline will really use. Previously this raised for any channel without
        its own voices.yaml and silently cleared the user's choice.
        """
        query = state.voice_profile or "ru_dom"
        try:
            profile_id = capabilities.resolve_voice_profile(state.channel_id, query)
        except Exception:
            state.voice_profile = ""
            state.voice_profile_display_name = ""
            state.voice_profile_model_id = ""
            print(
                _tag(
                    self.icons,
                    "warning",
                    f"Голосовой профиль {query!r} не найден ни в channels/{state.channel_id}/voices.yaml, "
                    "ни в других каналах - платная генерация не будет выполнена.",
                )
            )
            return
        state.voice_profile = profile_id
        for profile in capabilities.list_voice_profiles(state.channel_id):
            if profile["profile_id"] == profile_id:
                state.voice_profile_display_name = profile["display_name"]
                state.voice_profile_model_id = profile["model_id"]
                source = profile.get("source_channel_id", state.channel_id)
                if source and source != state.channel_id:
                    print(
                        _tag(
                            self.icons,
                            "voice",
                            f"Голос {profile['display_name']} ({profile_id}) взят из канала {source} - "
                            f"у канала {state.channel_id} нет своего voices.yaml.",
                        )
                    )
                return
        state.voice_profile_display_name = ""
        state.voice_profile_model_id = ""

    def choose_subtitles(self, state: _WizardState) -> None:
        template_caps = self._template_caps(state.template_id)
        if not template_caps["subtitles_allowed"]:
            state.subtitle_style = "disabled"
            return
        subtitle_ids = set(template_caps["subtitle_style_ids"])
        options = [s for s in capabilities.list_subtitle_styles() if s["style_id"] in subtitle_ids]
        if state.template_id == "fullscreen_voiceover_v1":
            options.sort(key=lambda item: 0 if item["style_id"] == "documentary" else 1)
        choices = [(s["style_id"], f"{s['display_name']} ({s['style_id']})") for s in options]
        state.subtitle_style = self._select("subtitles", "Субтитры:", choices)

    def choose_music(self, state: _WizardState) -> None:
        template_caps = self._template_caps(state.template_id)
        if not template_caps["music_allowed"]:
            state.music_mode = "disabled"
            state.music_path = ""
            print(_tag(self.icons, "music", "Этот шаблон не поддерживает музыку - будет использован режим disabled."))
            return
        # local_file used to be hidden here because nothing wrote
        # assets/music/music_manifest.json. src.audio.music_manifest now does, and the
        # renderer's existing mixing/ducking path picks it up, so the option is real.
        options = [
            option
            for option in capabilities.list_music_options()
            if state.template_id in option.get("supported_templates", [state.template_id])
        ]
        choices = [(m["mode_id"], f"{m['display_name']} ({m['mode_id']})") for m in options]
        state.music_mode = self._select("music", "Музыка:", choices)
        if state.music_mode == "disabled":
            state.music_path = ""
            return
        while True:
            state.music_path = self._text("music", "Путь к аудиофайлу музыки:")
            result = input_validation.validate_music_path(state.music_path)
            if result.valid:
                return
            print(_tag(self.icons, "error", result.message))
            if not self._confirm("music", "Попробовать другой путь?", default=True):
                state.music_mode = "disabled"
                state.music_path = ""
                return

    def choose_timing(self, state: _WizardState) -> None:
        """Not a question: the template's audio policy owns scene timing.

        No workflow reads ContentCreationRequest.timing, and since the voice stage
        writes the real narration timings onto the script (src.audio.scene_timeline),
        scene length is determined by the generated audio rather than by a mode the
        user picks. Kept as a step so the value is always populated and visible in
        the summary.
        """
        state.timing_mode = self._template_caps(state.template_id)["default_timing_mode"]

    def choose_dry_run(self, state: _WizardState) -> None:
        state.dry_run = self._confirm(
            "check", "Выполнить как dry-run (ничего не создавать по-настоящему)?", default=state.dry_run
        )

    def fill_all(self, state: _WizardState) -> None:
        self.choose_format(state)
        self.choose_template(state)
        self.choose_channel(state)
        self.choose_language(state)
        self.choose_content_input(state)
        self.choose_title(state)
        self.choose_target_duration(state)
        self.choose_voice(state)
        self.choose_subtitles(state)
        self.choose_music(state)
        self.choose_timing(state)
        self.choose_dry_run(state)

    # -- resume --------------------------------------------------------------

    def choose_project_to_resume(
        self,
        state: _WizardState,
        *,
        projects_root: str,
        project_fallback_roots: tuple[str, ...] = (),
    ) -> bool:
        """Pick an unfinished project and refill the state from it.

        Returns False when there is nothing to continue, so the caller can fall back
        to creating a new one instead of dead-ending.

        Everything is read from the project itself - channel, template, language,
        title, whether subtitles were built - rather than asked again. The one thing
        this deliberately does not do is re-ask the paid voice question: the service
        layer decides that by looking for narration that already exists.
        """
        from src.projects import ProjectRepository

        views = ProjectRepository(
            projects_root, fallback_roots=project_fallback_roots
        ).list()
        unfinished = [
            view
            for view in views
            if not view.is_finished and view.template_id in RESUMABLE_TEMPLATE_IDS
        ]
        skipped = [view for view in views if not view.is_finished and view.template_id not in RESUMABLE_TEMPLATE_IDS]

        if not unfinished:
            print(_tag(self.icons, "warning", "Незавершённых проектов, которые можно продолжить, нет."))
            if skipped:
                print(
                    f"    ({len(skipped)} незавершённых проектов другого шаблона - их продолжение "
                    "пока не поддерживается, такой ролик нужно создать заново.)"
                )
            return False

        # Most recently touched first: that is almost always the one meant.
        unfinished.sort(key=lambda view: view.updated_at or view.created_at, reverse=True)
        choices = [(view.project_id, self._resume_label(view)) for view in unfinished]
        project_id = self._select("check", "Какой проект продолжить?", choices)

        view = next(view for view in unfinished if view.project_id == project_id)
        state.project_id = view.project_id
        state.title = view.title
        state.channel_id = view.channel_id
        state.template_id = view.template_id
        state.format_id = view.format_id
        state.language = view.language or "ru"

        template_caps = self._template_caps(state.template_id)
        state.voice_provider = "elevenlabs" if template_caps["voice_required"] else "disabled"
        state.voice_mode = template_caps["default_voice_mode"]
        state.timing_mode = template_caps["default_timing_mode"]
        # Read from the project instead of guessing: if subtitles were built, keep
        # building them. Music needs no answer at all - the renderer reads the music
        # manifest the project already has, whatever this request says.
        subtitles_built = (
            Path(view.project_root) / "localizations" / state.language / "subtitles" / "subtitles.ass"
        ).is_file()
        state.subtitle_style = "documentary" if subtitles_built and template_caps["subtitles_allowed"] else "disabled"
        state.music_mode = "disabled"
        state.dry_run = False

        print()
        print(_tag(self.icons, "check", f"Продолжаем проект {view.project_id}"))
        print(f"    Название: {view.title}")
        print(f"    Папка: {Path(view.project_root).resolve()}")
        print(f"    Последняя завершённая стадия: {self._stage_label(view.last_completed_stage)}")
        if view.blocking_stages:
            print(f"    Требуют внимания: {', '.join(view.blocking_stages)}")
        return True

    def _resume_label(self, view) -> str:
        stage = self._stage_label(view.last_completed_stage)
        updated = (view.updated_at or view.created_at or "")[:10]
        title = view.title or view.project_id
        return f"{title} — остановлен на: {stage}" + (f" ({updated})" if updated else "")

    @staticmethod
    def _stage_label(stage: str) -> str:
        if not stage:
            return "ничего не завершено"
        return f"{STAGE_LABELS_RU.get(stage, stage)}"

    # -- summary / edit loop -------------------------------------------------

    def print_summary(self, state: _WizardState) -> None:
        icons = self.icons
        print()
        print("=" * 44)
        print(_tag(icons, "check", "Итоговая сводка"))
        print("=" * 44)
        if state.title:
            print(f"{icons['input']} Название: {state.title}")
        print(f"{icons['format']} Формат: {state.format_id}")
        print(f"{icons['template']} Шаблон: {state.template_id}")
        print(f"{icons['channel']} Канал: {state.channel_id}")
        print(f"{icons['language']} Язык: {languages.display_name(state.language)} ({state.language})")
        print(f"{icons['input']} Источник сценария: {state.content_input_mode or '-'}")
        if state.content_input_mode == "topic":
            print(f"    Тема: {state.topic}")
        elif state.content_input_mode == "article_url":
            print(f"    URL: {state.source_url}")
        elif state.content_input_mode == "pasted_script":
            print(f"    Текст сценария: {len(state.pasted_script)} симв.")
        elif state.content_input_mode == "script_file":
            print(f"    Файл: {state.script_path}")
        if state.text_top:
            print(f"    Текст карточки: {state.text_top}")
        if state.template_id == "fullscreen_voiceover_v1":
            print(f"{icons['timing']} Целевая длительность: {state.target_duration_sec} сек")
            print("    Режим завершения: draft_complete")
            print("    Адаптация сценария: light")
            print("    Визуальный режим: video-first")
            print("    Инфографический fallback: disabled")
        profile_label = state.voice_profile or "не настроено"
        if state.voice_profile_display_name:
            profile_label += f" (display_name={state.voice_profile_display_name}, model={state.voice_profile_model_id})"
        print(f"{icons['voice']} Озвучка: provider={state.voice_provider} profile={profile_label} mode={state.voice_mode}")
        self._print_localization_lines(state)
        print(f"{icons['subtitles']} Субтитры: {state.subtitle_style}")
        print(f"{icons['music']} Музыка: {state.music_mode}" + (f" ({state.music_path})" if state.music_path else ""))
        print(f"{icons['timing']} Timing: {state.timing_mode or '-'}")
        print(f"Dry-run: {state.dry_run}")
        network_actions = []
        paid_actions = []
        if state.content_input_mode == "article_url":
            network_actions.append("загрузка статьи по ссылке")
        if state.voice_provider == "elevenlabs":
            network_actions.append("вызов ElevenLabs API")
            paid_actions.append("платная генерация озвучки ElevenLabs")
        print(f"Сетевые действия: {', '.join(network_actions) or 'нет'}")
        print(f"Платные действия: {', '.join(paid_actions) or 'нет'}")
        print("=" * 44)

    def _print_localization_lines(self, state: _WizardState) -> None:
        """Which voice will really be used, where each part of that answer comes from,
        and why TTS will or will not run - resolved through src.localization, so the
        summary cannot disagree with what the pipeline then does.

        Read-only and free: no network, no provider call, no writes. A credential is
        shown only as настроен/не настроен. Never raises: a summary that cannot be
        built must not take the whole wizard down.
        """
        if not state.channel_id or state.voice_provider == "disabled":
            return
        try:
            from src.localization import resolve_localization

            resolved = resolve_localization(
                channel_id=state.channel_id,
                template_id=state.template_id,
                format_id=state.format_id,
                language=state.language,
                voice_profile_override=state.voice_profile or "",
                manual_audio_path=state.audio_file or "",
            )
        except Exception:  # noqa: BLE001 - сводка не имеет права ломать мастер
            return
        print(
            f"    Локализация: {resolved.localization_id} / locale={resolved.locale or '-'} / "
            f"субтитры={resolved.subtitle_language or '-'}"
        )
        print(
            f"    Голос: {resolved.voice_name or '-'} ({resolved.voice_profile_id or '-'}), "
            f"voice_id={resolved.resolved_voice_id or '-'}, model={resolved.tts_model or '-'}"
        )
        source = resolved.config.source_of("voice.voice_profile") if resolved.config is not None else ""
        print(f"    Откуда взят голос: {source or '-'}")
        secret_state = "настроен" if resolved.secret_configured else "не настроен"
        required = "требуется" if resolved.secret_required else "не требуется"
        print(f"    Ключ провайдера: {required}, {secret_state}")
        print(
            f"    Источник озвучки: {resolved.narration_source} (fallback={resolved.fallback_policy or '-'})"
        )
        if resolved.reuse_existing_narration:
            print(f"    Готовая озвучка будет переиспользована: {resolved.existing_narration_path}")
        if not resolved.tts_allowed:
            print(f"    TTS не будет запущен: {resolved.tts_blocked_reason or '-'}")
        for issue in resolved.issues:
            print(_tag(self.icons, "warning", f"{issue.severity}: {issue.message}"))

    def review_edit_loop(self, state: _WizardState) -> bool:
        """Returns True to proceed to creation, False if the user cancelled."""
        edit_menu = [
            ("run", _tag(self.icons, "launch", "Запустить")),
            ("edit_format", "Изменить формат"),
            ("edit_template", "Изменить шаблон"),
            ("edit_channel", "Изменить канал"),
            ("edit_language", "Изменить язык"),
            ("edit_input", "Изменить источник сценария"),
            ("edit_title", "Изменить название"),
            ("edit_voice", "Изменить озвучку"),
            ("edit_subtitles", "Изменить субтитры"),
            ("edit_music", "Изменить музыку"),
            ("restart", "Начать заново"),
        ]
        while True:
            self.print_summary(state)
            action = self.prompt.select("Что дальше?", edit_menu)
            if action == CANCEL:
                return False
            if action == "run":
                return True
            if action == "restart":
                fresh = _WizardState()
                try:
                    self.fill_all(fresh)
                except _Cancelled:
                    return False
                state.__dict__.update(fresh.__dict__)
                continue
            if action == "edit_format":
                old_format = state.format_id
                try:
                    self.choose_format(state)
                except _Cancelled:
                    continue
                if state.format_id != old_format:
                    compatible = {t.template_id for t in self.catalog.templates.filter_by_format(state.format_id) if t.enabled}
                    if state.template_id not in compatible:
                        try:
                            self.choose_template(state)
                        except _Cancelled:
                            state.format_id = old_format  # no usable template for the new format - revert
                            continue
                        self._reset_dependents(state)
                continue
            if action == "edit_template":
                old_template = state.template_id
                try:
                    self.choose_template(state)
                except _Cancelled:
                    continue
                if state.template_id != old_template:
                    self._reset_dependents(state)
                continue
            if action == "edit_channel":
                try:
                    self.choose_channel(state)
                except _Cancelled:
                    pass
                continue
            if action == "edit_language":
                try:
                    self.choose_language(state)
                except _Cancelled:
                    pass
                continue
            if action == "edit_input":
                try:
                    self.choose_content_input(state)
                except _Cancelled:
                    pass
                continue
            if action == "edit_title":
                try:
                    self.choose_title(state)
                except _Cancelled:
                    pass
                continue
            if action == "edit_voice":
                try:
                    self.choose_voice(state)
                except _Cancelled:
                    pass
                continue
            if action == "edit_subtitles":
                try:
                    self.choose_subtitles(state)
                except _Cancelled:
                    pass
                continue
            if action == "edit_music":
                try:
                    self.choose_music(state)
                except _Cancelled:
                    pass
                continue

    def _reset_dependents(self, state: _WizardState) -> None:
        """Recompute voice/subtitles/music/timing for a newly-picked template -
        clears any prior selection that's no longer applicable/valid."""
        try:
            self.choose_voice(state)
            self.choose_subtitles(state)
            self.choose_music(state)
            self.choose_timing(state)
        except _Cancelled:
            pass

    # -- paid confirmation + progress/result --------------------------------

    def confirm_paid_generation(self, state: _WizardState) -> None:
        if state.dry_run or state.voice_provider != "elevenlabs":
            state.approve_paid_generation = False
            return
        print(_tag(self.icons, "paid", "Генерация озвучки через ElevenLabs использует сеть и платный API-вызов."))
        state.approve_paid_generation = self._confirm("paid", "Подтвердить платную генерацию озвучки сейчас?", default=False)
        state.prepare_only = not state.approve_paid_generation

    def _print_preflight_summary(self, state: _WizardState, result: ContentCreationResult) -> None:
        """Free, no-cost summary of the just-prepared script - shown before the paid
        ElevenLabs confirmation, never after, so the user can decide with real numbers
        in front of them (see src.content_creation.service._build_paid_preflight_summary,
        which computes every field here from the actual script.json - no TTS call made)."""
        icons = self.icons
        evidence = result.evidence
        print()
        print("=" * 44)
        print(_tag(icons, "check", "Сценарий подготовлен (без платной генерации)"))
        print("=" * 44)
        print(f"Целевая длительность: {state.target_duration_sec} сек")
        estimated = evidence.get("estimated_duration_sec")
        print(f"Оценочная длительность речи: {estimated if estimated is not None else '-'} сек")
        print(f"Слов: {evidence.get('word_count', '-')}")
        print(f"Символов: {evidence.get('character_count', '-')}")
        print(f"Модель голоса: {evidence.get('voice_name', '-')} ({evidence.get('model_id', '-')})")
        credits = evidence.get("expected_credits")
        credits_label = credits if credits is not None else "неизвестно (тариф этой модели не задан)"
        print(f"Ожидаемый расход credits: {credits_label}")
        print(f"Сцен: {evidence.get('scene_count', '-')}")
        print(
            f"Кеш: готово {evidence.get('cache_ready_scenes', '-')}, "
            f"нужно сгенерировать {evidence.get('cache_missing_scenes', '-')}"
        )
        print("=" * 44)

    def run_creation_with_preflight(self, state: _WizardState) -> ContentCreationResult | None:
        """fullscreen_voiceover_v1 + elevenlabs, non-dry-run path: first create/prepare
        the project with approve_paid_generation left False - this always stops before
        any paid TTS call (see service._create_fullscreen_voiceover's
        requires_paid_approval/execute_voice gating) and returns a script/voice-manifest-
        backed evidence summary. Only after that summary is shown does this ask for the
        paid confirmation; on "yes" it resumes the same project (project_id + resume=True)
        to actually run the paid generation and the rest of the pipeline."""
        state.approve_paid_generation = False
        state.prepare_only = False
        result = self.run_creation(state)
        if result is None or result.status != "prepared_awaiting_paid_approval":
            return result
        state.project_id = result.project_id
        self._print_preflight_summary(state, result)
        print(_tag(self.icons, "paid", "Генерация озвучки через ElevenLabs использует сеть и платный API-вызов."))
        approve = self._confirm("paid", "Подтвердить платную генерацию озвучки сейчас?", default=False)
        if not approve:
            return result
        state.approve_paid_generation = True
        return self.run_creation(state)

    def run_creation(self, state: _WizardState) -> ContentCreationResult | None:
        try:
            supports_progress = "progress_callback" in inspect.signature(self.create_fn).parameters
        except (TypeError, ValueError):
            supports_progress = False

        while True:
            request = _build_request(state, project_overrides=self.project_overrides)
            print(_tag(self.icons, "launch", "Выполняется..."))

            def _on_stage(stage: str, status: str) -> None:
                if status == "running":
                    print(f"  ... {stage}")
                else:
                    print(f"  {_tag(self.icons, _status_icon_key(status), f'{stage}: {status}')}")

            try:
                if supports_progress:
                    result = self.create_fn(request, progress_callback=_on_stage)
                else:
                    result = self.create_fn(request)
            except ContentCreationError as exc:
                action = self._handle_error(exc, state)
                if action == "cancel":
                    return None
                continue
            self.print_result(result)
            return result

    def _handle_error(self, exc: ContentCreationError, state: _WizardState) -> str:
        print(_tag(self.icons, "error", str(exc)))
        if exc.reason not in _RECOVERABLE_INPUT_REASONS:
            print("Настройки сохранены. Отредактируйте их через меню сводки, если нужно.")
            return "changed"
        options = [("retry", "Повторить попытку")]
        if state.content_input_mode != "topic":
            options.append(("use_topic", "Использовать только тему"))
        options.append(("change_input", "Изменить источник сценария"))
        action = self.prompt.select("Что делать дальше?", options)
        if action == CANCEL:
            return "cancel"
        if action == "use_topic":
            state.content_input_mode = "topic"
            state.topic = self._text("input", "Тема ролика:")
            state.source_url = ""
            return "changed"
        if action == "change_input":
            try:
                self.choose_content_input(state)
            except _Cancelled:
                return "cancel"
            return "changed"
        return "retry"

    def print_result(self, result: ContentCreationResult) -> None:
        icons = self.icons
        print(_tag(icons, _status_icon_key(result.status), f"status={result.status}"))
        print(f"project_id={result.project_id}")
        print(f"project_root={result.project_root}")
        final_video = result.output_paths.get("final_video")
        if final_video:
            report = describe_output_file(final_video, project_root=result.project_root)
            print(f"output_path={report['absolute_path']}")
            print(f"output_project_relative={report['project_relative_path']}")
            print(f"size_bytes={report['size_bytes']}")
            print(f"duration_sec={report['duration_sec']}")
            print(f"resolution={report['resolution']}")
            print(f"audio_present={report['audio_present']}")
        if result.evidence.get("evidence_manifest_path"):
            # Short and honest: what we can prove about the material used, and where
            # the full record is. Licence detail stays in `project rights-report`.
            from src.content_creation.cli import _print_rights_lines

            _print_rights_lines(result.evidence)
        for warning in result.warnings:
            print(_tag(icons, "warning", warning))
        for error in result.errors:
            print(_tag(icons, "error", error))
        if result.rerun_commands:
            print(f"rerun: {result.rerun_commands[0]}")


def run_wizard(
    adapter: PromptAdapter | None = None,
    *,
    create_fn=create_content,
    no_icons: bool = False,
    projects_root: str | None = None,
    project_fallback_roots: tuple[str, ...] = (),
    channels_root: str | None = None,
) -> ContentCreationResult | None:
    """Interactive terminal wizard: fill settings, review/edit, confirm, create.

    Pure presentation layer over the same registries/catalog/service the
    flag-based `create` command uses - see src.content_creation.service.create_content
    and src.content_creation.capabilities. Returns None if the user cancels at
    any point (including declining the final confirmation); no project is
    created until that point.
    """
    if projects_root is None:
        from src.config_resolver import resolve_application_paths

        application_paths = resolve_application_paths()
        projects_root = str(application_paths.projects_root)
        project_fallback_roots = tuple(
            str(path) for path in application_paths.project_fallback_roots
        )
        channels_root = str(application_paths.channels_root)
    prompt = adapter or _default_adapter()
    icons = choose_icon_set(no_icons=no_icons)
    wizard = _Wizard(
        prompt,
        icons,
        create_fn,
        project_overrides={
            "projects_root": projects_root,
            "project_fallback_roots": list(project_fallback_roots),
            "channels_root": channels_root or "",
        },
    )
    state = _WizardState()

    try:
        action = wizard._select("check", "Что делаем?", START_ACTIONS)
        if action == "resume":
            if wizard.choose_project_to_resume(
                state,
                projects_root=projects_root,
                project_fallback_roots=project_fallback_roots,
            ):
                # A resumed project keeps its own id, channel, template and language,
                # and its finished stages are not run again - so it goes straight to
                # execution rather than back through the questionnaire.
                return wizard.run_creation_with_preflight(state)
            print(_tag(icons, "warning", "Создаём новый ролик."))
        wizard.fill_all(state)
    except _Cancelled:
        print(_tag(icons, "warning", "Отменено; проект не создан."))
        return None

    if not wizard.review_edit_loop(state):
        print(_tag(icons, "warning", "Отменено; проект не создан."))
        return None

    if state.voice_provider == "elevenlabs" and not state.dry_run:
        return wizard.run_creation_with_preflight(state)

    wizard.confirm_paid_generation(state)

    return wizard.run_creation(state)
