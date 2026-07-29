from __future__ import annotations

import sys
from typing import Protocol

from src.content_creation import languages
from src.content_creation.models import ContentCreationResult
from src.content_creation.output_report import describe_output_file
from src.content_creation.presentation import print_rights_lines
from src.content_creation.wizard_state import WizardState


CANCEL = "__cancel__"

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


def status_icon_key(status: str) -> str:
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


def tag(icons: dict[str, str], key: str, message: str) -> str:
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


class PromptAdapter(Protocol):
    """Thin prompt interface shared by interactive, plain and test adapters."""

    def select(
        self,
        message: str,
        choices: list[tuple[str, str]],
        *,
        allow_cancel: bool = True,
    ) -> str: ...

    def text(self, message: str, default: str = "") -> str: ...

    def confirm(self, message: str, default: bool = False) -> bool: ...


class PlainAdapter:
    """Numbered-question fallback for terminals without arrow-key interaction."""

    def select(
        self,
        message: str,
        choices: list[tuple[str, str]],
        *,
        allow_cancel: bool = True,
    ) -> str:
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
    """Arrow-key interactive adapter, used when stdin/stdout are real TTYs."""

    def __init__(self) -> None:
        import questionary

        self._questionary = questionary
        self._style = build_questionary_style()

    def select(
        self,
        message: str,
        choices: list[tuple[str, str]],
        *,
        allow_cancel: bool = True,
    ) -> str:
        options = list(choices)
        if allow_cancel:
            options = [*options, (CANCEL, "Отмена")]
        answer = self._questionary.select(
            message,
            choices=[label for _, label in options],
            style=self._style,
        ).ask()
        if answer is None:
            return CANCEL
        for value, label in options:
            if label == answer:
                return value
        return CANCEL

    def text(self, message: str, default: str = "") -> str:
        answer = self._questionary.text(
            message,
            default=default,
            style=self._style,
        ).ask()
        return answer if answer is not None else default

    def confirm(self, message: str, default: bool = False) -> bool:
        answer = self._questionary.confirm(
            message,
            default=default,
            style=self._style,
        ).ask()
        return bool(answer) if answer is not None else default


def default_adapter() -> PromptAdapter:
    if sys.stdin.isatty() and sys.stdout.isatty():
        try:
            return QuestionaryAdapter()
        except Exception:
            return PlainAdapter()
    return PlainAdapter()


class WizardPresentation:
    """Terminal-only summaries and result rendering for a wizard run."""

    icons: dict[str, str]

    def print_summary(self, state: WizardState) -> None:
        icons = self.icons
        print()
        print("=" * 44)
        print(tag(icons, "check", "Итоговая сводка"))
        print("=" * 44)
        if state.title:
            print(f"{icons['input']} Название: {state.title}")
        print(f"{icons['format']} Формат: {state.format_id}")
        print(f"{icons['template']} Шаблон: {state.template_id}")
        print(f"{icons['channel']} Канал: {state.channel_id}")
        print(
            f"{icons['language']} Язык: "
            f"{languages.display_name(state.language)} ({state.language})"
        )
        print(
            f"{icons['input']} Источник сценария: "
            f"{state.content_input_mode or '-'}"
        )
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
            print(
                f"{icons['timing']} Целевая длительность: "
                f"{state.target_duration_sec} сек"
            )
            print("    Режим завершения: draft_complete")
            print("    Адаптация сценария: light")
            print("    Визуальный режим: video-first")
            print("    Инфографический fallback: disabled")
        profile_label = state.voice_profile or "не настроено"
        if state.voice_profile_display_name:
            profile_label += (
                f" (display_name={state.voice_profile_display_name}, "
                f"model={state.voice_profile_model_id})"
            )
        print(
            f"{icons['voice']} Озвучка: provider={state.voice_provider} "
            f"profile={profile_label} mode={state.voice_mode}"
        )
        self._print_localization_lines(state)
        print(f"{icons['subtitles']} Субтитры: {state.subtitle_style}")
        print(
            f"{icons['music']} Музыка: {state.music_mode}"
            + (f" ({state.music_path})" if state.music_path else "")
        )
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

    def _print_localization_lines(self, state: WizardState) -> None:
        """Print the read-only localization resolution without breaking summary."""
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
            f"    Локализация: {resolved.localization_id} / "
            f"locale={resolved.locale or '-'} / "
            f"субтитры={resolved.subtitle_language or '-'}"
        )
        print(
            f"    Голос: {resolved.voice_name or '-'} "
            f"({resolved.voice_profile_id or '-'}), "
            f"voice_id={resolved.resolved_voice_id or '-'}, "
            f"model={resolved.tts_model or '-'}"
        )
        source = (
            resolved.config.source_of("voice.voice_profile")
            if resolved.config is not None
            else ""
        )
        print(f"    Откуда взят голос: {source or '-'}")
        secret_state = (
            "настроен" if resolved.secret_configured else "не настроен"
        )
        required = "требуется" if resolved.secret_required else "не требуется"
        print(f"    Ключ провайдера: {required}, {secret_state}")
        print(
            f"    Источник озвучки: {resolved.narration_source} "
            f"(fallback={resolved.fallback_policy or '-'})"
        )
        if resolved.reuse_existing_narration:
            print(
                "    Готовая озвучка будет переиспользована: "
                f"{resolved.existing_narration_path}"
            )
        if not resolved.tts_allowed:
            print(
                "    TTS не будет запущен: "
                f"{resolved.tts_blocked_reason or '-'}"
            )
        for issue in resolved.issues:
            print(tag(self.icons, "warning", f"{issue.severity}: {issue.message}"))

    def _print_preflight_summary(
        self,
        state: WizardState,
        result: ContentCreationResult,
    ) -> None:
        icons = self.icons
        evidence = result.evidence
        print()
        print("=" * 44)
        print(tag(icons, "check", "Сценарий подготовлен (без платной генерации)"))
        print("=" * 44)
        print(f"Целевая длительность: {state.target_duration_sec} сек")
        estimated = evidence.get("estimated_duration_sec")
        print(
            "Оценочная длительность речи: "
            f"{estimated if estimated is not None else '-'} сек"
        )
        print(f"Слов: {evidence.get('word_count', '-')}")
        print(f"Символов: {evidence.get('character_count', '-')}")
        print(
            f"Модель голоса: {evidence.get('voice_name', '-')} "
            f"({evidence.get('model_id', '-')})"
        )
        credits = evidence.get("expected_credits")
        credits_label = (
            credits
            if credits is not None
            else "неизвестно (тариф этой модели не задан)"
        )
        print(f"Ожидаемый расход credits: {credits_label}")
        print(f"Сцен: {evidence.get('scene_count', '-')}")
        print(
            f"Кеш: готово {evidence.get('cache_ready_scenes', '-')}, "
            f"нужно сгенерировать {evidence.get('cache_missing_scenes', '-')}"
        )
        print("=" * 44)

    def print_result(self, result: ContentCreationResult) -> None:
        icons = self.icons
        print(tag(icons, status_icon_key(result.status), f"status={result.status}"))
        print(f"project_id={result.project_id}")
        print(f"project_root={result.project_root}")
        final_video = result.output_paths.get("final_video")
        if final_video:
            report = describe_output_file(
                final_video,
                project_root=result.project_root,
            )
            print(f"output_path={report['absolute_path']}")
            print(
                "output_project_relative="
                f"{report['project_relative_path']}"
            )
            print(f"size_bytes={report['size_bytes']}")
            print(f"duration_sec={report['duration_sec']}")
            print(f"resolution={report['resolution']}")
            print(f"audio_present={report['audio_present']}")
        if result.evidence.get("evidence_manifest_path"):
            print_rights_lines(result.evidence)
        for warning in result.warnings:
            print(tag(icons, "warning", warning))
        for error in result.errors:
            print(tag(icons, "error", error))
        if result.rerun_commands:
            print(f"rerun: {result.rerun_commands[0]}")


__all__ = [
    "CANCEL",
    "ICONS_ASCII",
    "ICONS_UNICODE",
    "PlainAdapter",
    "PromptAdapter",
    "QuestionaryAdapter",
    "WizardPresentation",
    "build_questionary_style",
    "choose_icon_set",
    "default_adapter",
    "status_icon_key",
    "tag",
]
