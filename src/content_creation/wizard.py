from __future__ import annotations

"""Compatibility facade for the interactive content-creation Wizard."""

from typing import Any

from src.content_creation.models import (
    ContentCreationRequest,
    ContentCreationResult,
)
from src.content_creation.service import create_content
from src.content_creation.wizard_presentation import (
    CANCEL,
    ICONS_ASCII,
    ICONS_UNICODE,
    PlainAdapter,
    PromptAdapter,
    QuestionaryAdapter,
    build_questionary_style,
    choose_icon_set,
    default_adapter,
    status_icon_key,
    tag,
)
from src.content_creation.wizard_state import (
    CONTENT_INPUT_MODES,
    RESUMABLE_TEMPLATE_IDS,
    STAGE_LABELS_RU,
    START_ACTIONS,
    TARGET_DURATION_CHOICES,
    WizardState,
    build_request,
    profiles_for_language,
    voice_profile_label,
)
from src.content_creation.wizard_steps import Wizard, WizardCancelled


_WizardState = WizardState
_Cancelled = WizardCancelled
_default_adapter = default_adapter
_profiles_for_language = profiles_for_language
_voice_profile_label = voice_profile_label
_status_icon_key = status_icon_key
_tag = tag


def _build_request(
    state: _WizardState,
    *,
    project_overrides: dict[str, Any] | None = None,
) -> ContentCreationRequest:
    return build_request(
        state,
        project_overrides=project_overrides,
    )


def _request_builder_patchpoint(
    state: _WizardState,
    *,
    project_overrides: dict[str, Any] | None = None,
) -> ContentCreationRequest:
    return _build_request(
        state,
        project_overrides=project_overrides,
    )


class _Wizard(Wizard):
    """Compatibility class preserving the former module-local constructor."""

    def __init__(
        self,
        prompt: PromptAdapter,
        icons: dict[str, str],
        create_fn,
        *,
        project_overrides: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            prompt,
            icons,
            create_fn,
            project_overrides=project_overrides,
            build_request_fn=_request_builder_patchpoint,
        )


def run_wizard(
    adapter: PromptAdapter | None = None,
    *,
    create_fn=create_content,
    no_icons: bool = False,
    projects_root: str | None = None,
    project_fallback_roots: tuple[str, ...] = (),
    channels_root: str | None = None,
) -> ContentCreationResult | None:
    """Fill, review and execute one request through the shared service."""
    if projects_root is None:
        from src.config_resolver import resolve_application_paths

        application_paths = resolve_application_paths()
        projects_root = str(application_paths.projects_root)
        project_fallback_roots = tuple(
            str(path)
            for path in application_paths.project_fallback_roots
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


__all__ = [
    "CANCEL",
    "CONTENT_INPUT_MODES",
    "ICONS_ASCII",
    "ICONS_UNICODE",
    "PlainAdapter",
    "PromptAdapter",
    "QuestionaryAdapter",
    "RESUMABLE_TEMPLATE_IDS",
    "STAGE_LABELS_RU",
    "START_ACTIONS",
    "TARGET_DURATION_CHOICES",
    "_Cancelled",
    "_Wizard",
    "_WizardState",
    "_build_request",
    "_default_adapter",
    "_profiles_for_language",
    "_status_icon_key",
    "_tag",
    "_voice_profile_label",
    "build_questionary_style",
    "choose_icon_set",
    "run_wizard",
]
