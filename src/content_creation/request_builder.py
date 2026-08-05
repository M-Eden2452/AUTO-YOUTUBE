"""Canonical boundary перевода пользовательского ввода в запрос создания.

Единственное место, где аргументы CLI и состояние Wizard превращаются в
``ContentCreationRequest``. Оба публичных входа — ``from_cli_namespace`` и
``from_wizard_state`` — собирают один и тот же контракт, поэтому канонический
CLI, compatibility CLI и Wizard не расходятся в семантике входа.

Responsibilities:
- сборка ``ContentCreationRequest`` и его вложенных конфигураций голоса,
  субтитров, музыки, тайминга, рендера и флагов выполнения;
- нормализация источника материала: ``--source-text`` / ``--source-text-file``
  и сохранённые aliases ``--pasted-script`` / ``--script-file`` отображаются в
  существующие поля ``pasted_script`` / ``script_path`` и существующие modes
  ``pasted_script`` / ``script_file``;
- проверка единственности authoritative source и совместимости явного
  ``--input-mode`` с выбранным источником;
- загрузка визуальных брифов из файла в поле запроса;
- нормализация явного сетевого разрешения ``--allow-network`` /
  ``state.allow_network`` в одно поле ``network`` запроса, одинаково для CLI и
  Wizard.

Does not own:
- определения аргументов и парсер — ``src.ai_youtube.cli`` и
  ``src.content_creation.cli``;
- модель запроса — ``src.content_creation.models``;
- правила валидации текста и файла сценария —
  ``src.content_creation.input_validation``;
- разрешение шаблона, канала и контекстную валидацию —
  ``src.content_creation.service``;
- сам script engine: модуль даёт вход, а не создаёт сценарий.

Inputs: разобранный ``argparse.Namespace`` либо состояние Wizard, плюс
разрешённые корни проектов и каналов.

Outputs: ``ContentCreationRequest``. Ни одного файла модуль не создаёт; он
только читает файл визуальных брифов, если путь передан.

Important invariants:
- ровно один authoritative источник материала на запрос; несколько
  одновременно — ``ContentCreationError``, а не молчаливый приоритет;
- явный ``--input-mode``, противоречащий выбранному источнику, отвергается до
  начала работы;
- новые публичные флаги остаются aliases того же parser destination: прежние
  имена продолжают работать и второй вход не создаётся;
- модуль не решает, выполним ли запрос по каналу и шаблону — эту ошибку
  формулирует service, поэтому неудачное предразрешение voice profile здесь не
  становится отказом;
- сетевое разрешение только переносится, но не выдаётся: пустое значение по
  умолчанию означает полный запрет, и ни credentials, ни ``--resume``, ни
  ``--approve-paid-generation`` его не создают. Владелец решения —
  ``src.runtime_network``.

See also: ``src/content_creation/service.py``,
``src/content_creation/input_validation.py``,
``src/content_creation/__init__.py``.
"""

from __future__ import annotations

from argparse import Namespace
from typing import Any

from src.runtime_network import NETWORK_ACTIONS

from src.content_creation import capabilities, input_validation
from src.content_creation.models import (
    ContentCreationError,
    ContentCreationRequest,
    ExecutionFlags,
    MusicRequestConfig,
    NetworkRequestConfig,
    RenderRequestConfig,
    SubtitleRequestConfig,
    TimingRequestConfig,
    VoiceRequestConfig,
)


def from_cli_namespace(
    args: Namespace,
    *,
    projects_root: str,
    project_fallback_roots: tuple[str, ...],
    channels_root: str,
) -> ContentCreationRequest:
    """Translate parsed CLI input into the application request contract."""
    script_path, pasted_script, content_input_mode = _normalize_cli_content_input(
        args
    )
    voice_profile = args.voice_profile
    if voice_profile and args.channel_id:
        try:
            voice_profile = capabilities.resolve_voice_profile(
                args.channel_id,
                args.voice_profile,
            )
        except Exception:
            # The service owns contextual validation and produces the public error.
            pass

    text: dict[str, str] = {}
    if getattr(args, "text", ""):
        text["top"] = args.text
    if getattr(args, "comment", ""):
        text["comment"] = args.comment

    return ContentCreationRequest(
        project_id=args.project_id,
        title=args.title,
        source_url=args.source_url,
        script_path=script_path,
        pasted_script=pasted_script,
        content_input_mode=content_input_mode,
        channel_id=args.channel_id,
        format_id=args.format_id or "",
        template_id=args.template_id or "",
        language=args.language,
        text=text,
        source_asset_path=args.source_asset_path,
        topic=args.topic,
        target_duration_sec=getattr(args, "target_duration_sec", 50),
        visual_briefs=load_visual_briefs(
            getattr(args, "visual_brief_path", ""),
        ),
        completion_mode=getattr(args, "completion_mode", ""),
        script_adaptation=getattr(args, "script_adaptation", ""),
        voice=VoiceRequestConfig(
            provider=args.voice_provider,
            profile=voice_profile,
            mode=args.voice_mode
            or ("disabled" if args.voice_provider == "disabled" else "scene_audio"),
            audio_file=args.audio_file,
            approve_paid_generation=args.approve_paid_generation,
        ),
        subtitles=SubtitleRequestConfig(style=args.subtitle_style),
        music=MusicRequestConfig(mode=args.music_mode, path=args.music_path),
        timing=TimingRequestConfig(mode=args.timing_mode),
        render=RenderRequestConfig(quality=args.quality),
        network=NetworkRequestConfig(
            allowed_actions=normalize_network_actions(
                getattr(args, "allow_network", None),
            ),
        ),
        execution=ExecutionFlags(
            dry_run=args.dry_run,
            prepare_only=args.prepare_only,
            resume=args.resume,
            force_stage=getattr(args, "force_stage", False),
            stage="",
            until_stage="",
        ),
        project_overrides={
            "projects_root": projects_root,
            "project_fallback_roots": list(project_fallback_roots),
            "channels_root": channels_root,
        },
    )


def _normalize_cli_content_input(args: Namespace) -> tuple[str, str, str]:
    """Validate CLI source ownership and reuse the existing internal modes."""
    raw_pasted_script = getattr(args, "pasted_script", None)
    raw_script_path = getattr(args, "script_path", None)
    pasted_script_provided = raw_pasted_script is not None
    script_path_provided = raw_script_path is not None
    pasted_script = str(raw_pasted_script or "")
    script_path = str(raw_script_path or "")
    content_input_mode = str(getattr(args, "content_input_mode", "") or "")

    if pasted_script_provided:
        result = input_validation.validate_pasted_script(pasted_script)
        if not result.valid:
            raise ContentCreationError(result.message, reason=result.reason)
    if script_path_provided:
        result = input_validation.validate_script_file(script_path)
        if not result.valid:
            raise ContentCreationError(result.message, reason=result.reason)

    authoritative_inputs: list[tuple[str, str]] = []
    if str(getattr(args, "topic", "") or "").strip():
        authoritative_inputs.append(("topic", "--topic"))
    if str(getattr(args, "source_url", "") or "").strip():
        authoritative_inputs.append(("article_url", "--source-url"))
    if pasted_script_provided:
        authoritative_inputs.append(("pasted_script", "--source-text"))
    if script_path_provided:
        authoritative_inputs.append(("script_file", "--source-text-file"))

    if len(authoritative_inputs) > 1:
        labels = ", ".join(label for _mode, label in authoritative_inputs)
        raise ContentCreationError(
            "Choose one authoritative content source; received " + labels + ".",
            reason="invalid_content",
        )

    selected_mode = authoritative_inputs[0][0] if authoritative_inputs else ""
    selected_label = authoritative_inputs[0][1] if authoritative_inputs else ""
    if content_input_mode and selected_mode and content_input_mode != selected_mode:
        raise ContentCreationError(
            f"--input-mode {content_input_mode!r} conflicts with {selected_label}; "
            f"use {selected_mode!r} or omit --input-mode.",
            reason="invalid_content",
        )

    if not content_input_mode and selected_mode in {"pasted_script", "script_file"}:
        content_input_mode = selected_mode

    return script_path, pasted_script, content_input_mode


def from_wizard_state(
    state: Any,
    *,
    project_overrides: dict[str, Any] | None = None,
) -> ContentCreationRequest:
    """Translate the wizard's presentation state into the same request contract."""
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
        network=NetworkRequestConfig(
            allowed_actions=normalize_network_actions(
                getattr(state, "allow_network", None),
            ),
        ),
        execution=ExecutionFlags(
            dry_run=state.dry_run,
            prepare_only=state.prepare_only,
            resume=bool(state.project_id),
        ),
        completion_mode="draft_complete" if video_first else "",
        script_adaptation="light" if video_first else "",
        project_overrides=dict(project_overrides or {}),
    )


def normalize_network_actions(actions: Any) -> tuple[str, ...]:
    """Normalize an explicit network approval into the request contract shape.

    CLI (`--allow-network`, repeatable) and Wizard (`state.allow_network`) both
    land here, so neither entry point can approve something the other cannot.
    Order and duplicates are dropped; an unknown id is rejected here rather than
    silently ignored, because a typo must never read as "approved" nor as a
    quietly empty approval that fails much deeper in the run.
    """
    if not actions:
        return ()
    if isinstance(actions, str):
        actions = [actions]
    selected: list[str] = []
    for item in actions:
        name = str(item or "").strip()
        if not name or name in selected:
            continue
        if name not in NETWORK_ACTIONS:
            raise ContentCreationError(
                f"--allow-network {name!r} is not a known network action; "
                "expected one of " + ", ".join(NETWORK_ACTIONS) + ".",
                reason="unknown_network_action",
            )
        selected.append(name)
    return tuple(selected)


def load_visual_briefs(path: str) -> dict[str, dict]:
    """Read one validated visual-brief file, or return an empty mapping."""
    if not str(path or "").strip():
        return {}
    result = input_validation.validate_visual_brief_file(path)
    if not result.valid:
        raise SystemExit(f"--visual-brief: {result.message}")
    return input_validation.load_visual_briefs(path)


__all__ = [
    "from_cli_namespace",
    "from_wizard_state",
    "load_visual_briefs",
    "normalize_network_actions",
]
