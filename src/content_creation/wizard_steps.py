from __future__ import annotations

"""Interactive Wizard steps and execution orchestration."""

import inspect
from pathlib import Path
from typing import Any

from src.runtime_network import NETWORK_ACTION_DESCRIPTIONS

from src.content_creation import capabilities, input_validation, languages
from src.content_creation.models import (
    ContentCreationError,
    ContentCreationResult,
)
from src.content_creation.wizard_presentation import (
    CANCEL,
    PromptAdapter,
    WizardPresentation,
    status_icon_key,
    tag,
)
from src.content_creation.wizard_state import (
    CONTENT_INPUT_MODES,
    RECOVERABLE_INPUT_REASONS,
    RESUMABLE_TEMPLATE_IDS,
    STAGE_LABELS_RU,
    TARGET_DURATION_CHOICES,
    WizardState,
    build_request,
    profiles_for_language,
    required_network_actions,
    voice_profile_label,
)
from src.production_catalog.catalog import get_default_catalog


class WizardCancelled(Exception):
    pass


class Wizard(WizardPresentation):
    """One Wizard run composed from prompt steps and terminal presentation."""

    def __init__(
        self,
        prompt: PromptAdapter,
        icons: dict[str, str],
        create_fn,
        *,
        project_overrides: dict[str, Any] | None = None,
        build_request_fn=build_request,
    ) -> None:
        self.prompt = prompt
        self.icons = icons
        self.create_fn = create_fn
        self.project_overrides = dict(project_overrides or {})
        self.build_request_fn = build_request_fn
        self.catalog = get_default_catalog()

    def _select(
        self,
        key: str,
        message: str,
        choices: list[tuple[str, str]],
    ) -> str:
        value = self.prompt.select(tag(self.icons, key, message), choices)
        if value == CANCEL:
            raise WizardCancelled()
        return value

    def _text(self, key: str, message: str, default: str = "") -> str:
        return self.prompt.text(
            tag(self.icons, key, message),
            default=default,
        )

    def _confirm(
        self,
        key: str,
        message: str,
        default: bool = False,
    ) -> bool:
        return self.prompt.confirm(
            tag(self.icons, key, message),
            default=default,
        )

    def _template_caps(self, template_id: str) -> dict[str, Any]:
        return capabilities.describe_template_capabilities(template_id)

    def choose_format(self, state: WizardState) -> None:
        choices = [
            (format_.format_id, f"{format_.display_name} ({format_.format_id})")
            for format_ in self.catalog.formats.list_all()
            if format_.enabled
            and any(
                template.enabled
                for template in self.catalog.templates.filter_by_format(
                    format_.format_id
                )
            )
        ]
        if not choices:
            print("Нет ни одного формата с готовым шаблоном.")
            raise WizardCancelled()
        state.format_id = self._select("format", "Формат видео:", choices)

    def choose_template(self, state: WizardState) -> None:
        templates = [
            template
            for template in self.catalog.templates.filter_by_format(
                state.format_id
            )
            if template.enabled
        ]
        if not templates:
            print(
                f"Для формата {state.format_id!r} пока нет доступных шаблонов."
            )
            raise WizardCancelled()
        choices = [
            (
                template.template_id,
                f"{template.display_name} ({template.template_id})",
            )
            for template in templates
        ]
        state.template_id = self._select("template", "Шаблон:", choices)

    def choose_channel(self, state: WizardState) -> None:
        usable = (
            capabilities.list_channels_for_template(state.template_id)
            if state.template_id
            else [
                channel
                for channel in capabilities.list_channels()
                if channel.get("usable_for_content_creation")
            ]
        )
        choices = [
            (
                channel["channel_id"],
                f"{channel['display_name']} ({channel['channel_id']})",
            )
            for channel in usable
        ]
        if not choices:
            print(
                "Нет ни одного канала, настроенного для шаблона "
                f"{state.template_id!r}."
            )
            raise WizardCancelled()
        state.channel_id = self._select("channel", "Канал:", choices)

    def choose_language(self, state: WizardState) -> None:
        choices = [
            (
                item["code"],
                f"{item['display_name']} ({item['code']})",
            )
            for item in languages.list_languages()
        ]
        state.language = self._select("language", "Язык:", choices)
        channel = next(
            (
                item
                for item in capabilities.list_channels()
                if item["channel_id"] == state.channel_id
            ),
            None,
        )
        template_caps = (
            self._template_caps(state.template_id)
            if state.template_id
            else {"voice_required": False}
        )
        profiles = (
            capabilities.list_voice_profiles(state.channel_id)
            if state.channel_id
            else []
        )
        for warning in languages.language_support_warnings(
            channel=channel,
            template_requires_voice=template_caps.get(
                "voice_required",
                False,
            ),
            voice_profiles=profiles,
            language=state.language,
        ):
            print(tag(self.icons, "warning", warning))

    def choose_content_input(self, state: WizardState) -> None:
        if state.template_id == "story_card_text_only_v1":
            print(
                "Текст карточки - главный визуальный слой этого шаблона "
                "(не дублируется субтитрами)."
            )
            state.content_input_mode = ""
            state.topic = ""
            state.source_url = ""
            state.pasted_script = ""
            state.script_path = ""
            state.text_top = self._text("input", "Текст карточки:")
            state.source_asset_path = self._text(
                "input",
                "Путь к локальному видео-ассету:",
            )
            return

        state.content_input_mode = self._select(
            "input",
            "Источник сценария:",
            CONTENT_INPUT_MODES,
        )
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
                print(tag(self.icons, "error", result.message))
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
                    state.pasted_script = self._text(
                        "input",
                        "Текст сценария:",
                    )
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
                state.script_path = self._text(
                    "input",
                    "Путь к файлу сценария (.txt/.md):",
                )
                result = input_validation.validate_script_file(
                    state.script_path
                )
                if result.valid:
                    break
                print(tag(self.icons, "error", result.message))
                if not self._confirm(
                    "input",
                    "Попробовать другой путь?",
                    default=True,
                ):
                    raise WizardCancelled()
            state.topic = ""
            state.source_url = ""
            state.pasted_script = ""

    def choose_title(self, state: WizardState) -> None:
        from src.project_foundation.naming import build_project_id, suggest_title

        suggested = suggest_title(
            state.topic,
            state.text_top,
            state.pasted_script,
            state.source_url,
        )
        while True:
            answer = self._text(
                "input",
                "Название ролика:",
                default=suggested,
            ).strip()
            state.title = answer or suggested
            if state.title:
                break
            print(tag(self.icons, "error", "Название не может быть пустым."))
        print(
            "    Папка проекта будет называться: "
            f"{build_project_id(state.title)}"
        )

    def choose_target_duration(self, state: WizardState) -> None:
        if state.template_id != "fullscreen_voiceover_v1":
            return
        choice = self._select(
            "timing",
            "Желаемая длительность ролика:",
            TARGET_DURATION_CHOICES,
        )
        if choice != "manual":
            state.target_duration_sec = int(choice)
            return
        while True:
            raw = self._text(
                "timing",
                "Длительность в секундах (например 50):",
            )
            if raw.strip().isdigit() and int(raw.strip()) > 0:
                state.target_duration_sec = int(raw.strip())
                return
            print(
                tag(
                    self.icons,
                    "error",
                    "Введите положительное целое число секунд.",
                )
            )

    def choose_voice(self, state: WizardState) -> None:
        template_caps = self._template_caps(state.template_id)
        if not (
            template_caps["voice_required"]
            or template_caps["voice_allowed"]
        ):
            state.voice_provider = "disabled"
            state.voice_profile = ""
            state.voice_profile_display_name = ""
            state.voice_profile_model_id = ""
            state.voice_mode = "disabled"
            state.audio_file = ""
            return
        providers = capabilities.list_voice_providers()
        if state.template_id == "fullscreen_voiceover_v1":
            providers.sort(
                key=lambda item: (
                    0
                    if item["provider_id"] == "elevenlabs"
                    and item.get("available")
                    else 1
                    if item["provider_id"] == "audio_file"
                    else 2
                )
            )
        provider_choices = [
            (
                provider["provider_id"],
                f"{provider['display_name']} ({provider['provider_id']})",
            )
            for provider in providers
        ]
        state.voice_provider = self._select(
            "voice",
            "Источник озвучки:",
            provider_choices,
        )
        state.voice_profile = ""
        state.voice_profile_display_name = ""
        state.voice_profile_model_id = ""
        state.audio_file = ""
        if state.voice_provider == "disabled":
            state.voice_mode = "disabled"
            return
        if state.voice_provider == "elevenlabs":
            profiles = profiles_for_language(
                capabilities.list_voice_profiles(state.channel_id),
                state.language,
            )
            if profiles:
                profile_choices = [
                    (
                        profile["profile_id"],
                        voice_profile_label(profile, state.channel_id),
                    )
                    for profile in profiles
                ]
                state.voice_profile = self._select(
                    "voice",
                    "Голос:",
                    profile_choices,
                )
                self._resolve_profile_display(state)
            else:
                state.voice_profile = ""
                state.voice_profile_display_name = ""
                state.voice_profile_model_id = ""
                print(
                    tag(
                        self.icons,
                        "warning",
                        f"Нет голосового профиля для языка "
                        f"{state.language!r}. Добавьте голос в "
                        f"config/channels/{state.channel_id}/voices.yaml и укажите "
                        "его в channel_config.json → "
                        f"languages.{state.language}.voice - иначе платная "
                        "генерация не будет выполнена.",
                    )
                )
        elif state.voice_provider == "audio_file":
            state.audio_file = self._text(
                "voice",
                "Путь к WAV-файлу озвучки:",
            )
        state.voice_mode = (
            "manual_audio"
            if state.voice_provider == "audio_file"
            else template_caps["default_voice_mode"]
        )

    def _resolve_profile_display(self, state: WizardState) -> None:
        query = state.voice_profile or "ru_dom"
        try:
            profile_id = capabilities.resolve_voice_profile(
                state.channel_id,
                query,
            )
        except Exception:
            state.voice_profile = ""
            state.voice_profile_display_name = ""
            state.voice_profile_model_id = ""
            print(
                tag(
                    self.icons,
                    "warning",
                    f"Голосовой профиль {query!r} не найден ни в "
                    f"config/channels/{state.channel_id}/voices.yaml, ни в других "
                    "каналах - платная генерация не будет выполнена.",
                )
            )
            return
        state.voice_profile = profile_id
        for profile in capabilities.list_voice_profiles(state.channel_id):
            if profile["profile_id"] == profile_id:
                state.voice_profile_display_name = profile["display_name"]
                state.voice_profile_model_id = profile["model_id"]
                source = profile.get(
                    "source_channel_id",
                    state.channel_id,
                )
                if source and source != state.channel_id:
                    print(
                        tag(
                            self.icons,
                            "voice",
                            f"Голос {profile['display_name']} ({profile_id}) "
                            f"взят из канала {source} - у канала "
                            f"{state.channel_id} нет своего voices.yaml.",
                        )
                    )
                return
        state.voice_profile_display_name = ""
        state.voice_profile_model_id = ""

    def choose_subtitles(self, state: WizardState) -> None:
        template_caps = self._template_caps(state.template_id)
        if not template_caps["subtitles_allowed"]:
            state.subtitle_style = "disabled"
            return
        subtitle_ids = set(template_caps["subtitle_style_ids"])
        options = [
            style
            for style in capabilities.list_subtitle_styles()
            if style["style_id"] in subtitle_ids
        ]
        if state.template_id == "fullscreen_voiceover_v1":
            options.sort(
                key=lambda item: (
                    0 if item["style_id"] == "documentary" else 1
                )
            )
        choices = [
            (
                style["style_id"],
                f"{style['display_name']} ({style['style_id']})",
            )
            for style in options
        ]
        state.subtitle_style = self._select(
            "subtitles",
            "Субтитры:",
            choices,
        )

    def choose_music(self, state: WizardState) -> None:
        template_caps = self._template_caps(state.template_id)
        if not template_caps["music_allowed"]:
            state.music_mode = "disabled"
            state.music_path = ""
            print(
                tag(
                    self.icons,
                    "music",
                    "Этот шаблон не поддерживает музыку - будет использован "
                    "режим disabled.",
                )
            )
            return
        options = [
            option
            for option in capabilities.list_music_options()
            if state.template_id
            in option.get("supported_templates", [state.template_id])
        ]
        choices = [
            (
                option["mode_id"],
                f"{option['display_name']} ({option['mode_id']})",
            )
            for option in options
        ]
        state.music_mode = self._select("music", "Музыка:", choices)
        if state.music_mode == "disabled":
            state.music_path = ""
            return
        while True:
            state.music_path = self._text(
                "music",
                "Путь к аудиофайлу музыки:",
            )
            result = input_validation.validate_music_path(state.music_path)
            if result.valid:
                return
            print(tag(self.icons, "error", result.message))
            if not self._confirm(
                "music",
                "Попробовать другой путь?",
                default=True,
            ):
                state.music_mode = "disabled"
                state.music_path = ""
                return

    def choose_timing(self, state: WizardState) -> None:
        state.timing_mode = self._template_caps(
            state.template_id
        )["default_timing_mode"]

    def choose_dry_run(self, state: WizardState) -> None:
        state.dry_run = self._confirm(
            "check",
            "Выполнить как dry-run (ничего не создавать по-настоящему)?",
            default=state.dry_run,
        )

    def fill_all(self, state: WizardState) -> None:
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

    def choose_project_to_resume(
        self,
        state: WizardState,
        *,
        projects_root: str,
        project_fallback_roots: tuple[str, ...] = (),
    ) -> bool:
        """Pick an unfinished resumable project and refill the working state."""
        from src.projects import ProjectRepository

        views = ProjectRepository(
            projects_root,
            fallback_roots=project_fallback_roots,
        ).list()
        unfinished = [
            view
            for view in views
            if not view.is_finished
            and view.template_id in RESUMABLE_TEMPLATE_IDS
        ]
        skipped = [
            view
            for view in views
            if not view.is_finished
            and view.template_id not in RESUMABLE_TEMPLATE_IDS
        ]

        if not unfinished:
            print(
                tag(
                    self.icons,
                    "warning",
                    "Незавершённых проектов, которые можно продолжить, нет.",
                )
            )
            if skipped:
                print(
                    f"    ({len(skipped)} незавершённых проектов другого "
                    "шаблона - их продолжение пока не поддерживается, такой "
                    "ролик нужно создать заново.)"
                )
            return False

        unfinished.sort(
            key=lambda view: view.updated_at or view.created_at,
            reverse=True,
        )
        choices = [
            (view.project_id, self._resume_label(view))
            for view in unfinished
        ]
        project_id = self._select(
            "check",
            "Какой проект продолжить?",
            choices,
        )
        view = next(
            view
            for view in unfinished
            if view.project_id == project_id
        )
        state.project_id = view.project_id
        state.title = view.title
        state.channel_id = view.channel_id
        state.template_id = view.template_id
        state.format_id = view.format_id
        state.language = view.language or "ru"

        template_caps = self._template_caps(state.template_id)
        state.voice_provider = (
            "elevenlabs"
            if template_caps["voice_required"]
            else "disabled"
        )
        state.voice_mode = template_caps["default_voice_mode"]
        state.timing_mode = template_caps["default_timing_mode"]
        subtitles_built = (
            Path(view.project_root)
            / "localizations"
            / state.language
            / "subtitles"
            / "subtitles.ass"
        ).is_file()
        state.subtitle_style = (
            "documentary"
            if subtitles_built and template_caps["subtitles_allowed"]
            else "disabled"
        )
        state.music_mode = "disabled"
        state.dry_run = False

        print()
        print(
            tag(
                self.icons,
                "check",
                f"Продолжаем проект {view.project_id}",
            )
        )
        print(f"    Название: {view.title}")
        print(f"    Папка: {Path(view.project_root).resolve()}")
        print(
            "    Последняя завершённая стадия: "
            f"{self._stage_label(view.last_completed_stage)}"
        )
        if view.blocking_stages:
            print(
                "    Требуют внимания: "
                f"{', '.join(view.blocking_stages)}"
            )
        return True

    def _resume_label(self, view) -> str:
        stage = self._stage_label(view.last_completed_stage)
        updated = (view.updated_at or view.created_at or "")[:10]
        title = view.title or view.project_id
        return f"{title} — остановлен на: {stage}" + (
            f" ({updated})" if updated else ""
        )

    @staticmethod
    def _stage_label(stage: str) -> str:
        if not stage:
            return "ничего не завершено"
        return STAGE_LABELS_RU.get(stage, stage)

    def review_edit_loop(self, state: WizardState) -> bool:
        """Return True to proceed to creation, False when the user cancels."""
        edit_menu = [
            ("run", tag(self.icons, "launch", "Запустить")),
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
                fresh = WizardState()
                try:
                    self.fill_all(fresh)
                except WizardCancelled:
                    return False
                state.__dict__.update(fresh.__dict__)
                continue
            if action == "edit_format":
                old_format = state.format_id
                try:
                    self.choose_format(state)
                except WizardCancelled:
                    continue
                if state.format_id != old_format:
                    compatible = {
                        template.template_id
                        for template in self.catalog.templates.filter_by_format(
                            state.format_id
                        )
                        if template.enabled
                    }
                    if state.template_id not in compatible:
                        try:
                            self.choose_template(state)
                        except WizardCancelled:
                            state.format_id = old_format
                            continue
                        self._reset_dependents(state)
                continue
            if action == "edit_template":
                old_template = state.template_id
                try:
                    self.choose_template(state)
                except WizardCancelled:
                    continue
                if state.template_id != old_template:
                    self._reset_dependents(state)
                continue
            if action == "edit_channel":
                try:
                    self.choose_channel(state)
                except WizardCancelled:
                    pass
                continue
            if action == "edit_language":
                try:
                    self.choose_language(state)
                except WizardCancelled:
                    pass
                continue
            if action == "edit_input":
                try:
                    self.choose_content_input(state)
                except WizardCancelled:
                    pass
                continue
            if action == "edit_title":
                try:
                    self.choose_title(state)
                except WizardCancelled:
                    pass
                continue
            if action == "edit_voice":
                try:
                    self.choose_voice(state)
                except WizardCancelled:
                    pass
                continue
            if action == "edit_subtitles":
                try:
                    self.choose_subtitles(state)
                except WizardCancelled:
                    pass
                continue
            if action == "edit_music":
                try:
                    self.choose_music(state)
                except WizardCancelled:
                    pass
                continue

    def _reset_dependents(self, state: WizardState) -> None:
        try:
            self.choose_voice(state)
            self.choose_subtitles(state)
            self.choose_music(state)
            self.choose_timing(state)
        except WizardCancelled:
            pass

    def confirm_network_access(self, state: WizardState) -> None:
        """Ask once for exactly the network classes this run would reach.

        The wizard's counterpart to the CLI's repeatable --allow-network. Asked
        before the first create call, so nothing reaches the network on the
        strength of a configured key, a default-on provider or a later paid
        approval. Declining is a complete answer: the run continues offline and
        the workflow reports each blocked action.
        """
        if state.network_access_reviewed:
            return
        state.network_access_reviewed = True
        needed = required_network_actions(state)
        if not needed:
            state.allow_network = ()
            return
        print(
            tag(
                self.icons,
                "warning",
                "Этому запуску нужен доступ в сеть:",
            )
        )
        for action in needed:
            print(f"   - {action}: {NETWORK_ACTION_DESCRIPTIONS[action]}")
        print(
            tag(
                self.icons,
                "warning",
                "Без разрешения эти действия будут отклонены. Наличие "
                "API-ключа разрешением не является.",
            )
        )
        approved = self._confirm(
            "warning",
            "Разрешить перечисленные сетевые действия?",
            default=False,
        )
        state.allow_network = needed if approved else ()

    def confirm_paid_generation(self, state: WizardState) -> None:
        if state.dry_run or state.voice_provider != "elevenlabs":
            state.approve_paid_generation = False
            return
        print(
            tag(
                self.icons,
                "paid",
                "Генерация озвучки через ElevenLabs использует сеть и "
                "платный API-вызов.",
            )
        )
        state.approve_paid_generation = self._confirm(
            "paid",
            "Подтвердить платную генерацию озвучки сейчас?",
            default=False,
        )
        state.prepare_only = not state.approve_paid_generation

    def run_creation_with_preflight(
        self,
        state: WizardState,
    ) -> ContentCreationResult | None:
        state.approve_paid_generation = False
        state.prepare_only = False
        result = self.run_creation(state)
        if (
            result is None
            or result.status != "prepared_awaiting_paid_approval"
        ):
            return result
        state.project_id = result.project_id
        self._print_preflight_summary(state, result)
        print(
            tag(
                self.icons,
                "paid",
                "Генерация озвучки через ElevenLabs использует сеть и "
                "платный API-вызов.",
            )
        )
        approve = self._confirm(
            "paid",
            "Подтвердить платную генерацию озвучки сейчас?",
            default=False,
        )
        if not approve:
            return result
        state.approve_paid_generation = True
        return self.run_creation(state)

    def run_creation(
        self,
        state: WizardState,
    ) -> ContentCreationResult | None:
        # Every wizard path - new, resume and the two-phase paid flow - reaches
        # creation through here, so this is the one place the network question
        # has to be asked to keep CLI and Wizard at parity.
        self.confirm_network_access(state)
        try:
            supports_progress = (
                "progress_callback"
                in inspect.signature(self.create_fn).parameters
            )
        except (TypeError, ValueError):
            supports_progress = False

        while True:
            request = self.build_request_fn(
                state,
                project_overrides=self.project_overrides,
            )
            print(tag(self.icons, "launch", "Выполняется..."))

            def _on_stage(stage: str, status: str) -> None:
                if status == "running":
                    print(f"  ... {stage}")
                else:
                    print(
                        "  "
                        + tag(
                            self.icons,
                            status_icon_key(status),
                            f"{stage}: {status}",
                        )
                    )

            try:
                if supports_progress:
                    result = self.create_fn(
                        request,
                        progress_callback=_on_stage,
                    )
                else:
                    result = self.create_fn(request)
            except ContentCreationError as exc:
                action = self._handle_error(exc, state)
                if action == "cancel":
                    return None
                continue
            self.print_result(result)
            return result

    def _handle_error(
        self,
        exc: ContentCreationError,
        state: WizardState,
    ) -> str:
        print(tag(self.icons, "error", str(exc)))
        if exc.reason not in RECOVERABLE_INPUT_REASONS:
            print(
                "Настройки сохранены. Отредактируйте их через меню сводки, "
                "если нужно."
            )
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
            except WizardCancelled:
                return "cancel"
            return "changed"
        return "retry"


__all__ = ["Wizard", "WizardCancelled"]
