from __future__ import annotations

from argparse import Namespace
from typing import Any

from src.content_creation import capabilities, input_validation
from src.content_creation.models import (
    ContentCreationRequest,
    ExecutionFlags,
    MusicRequestConfig,
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
        script_path=args.script_path,
        pasted_script=getattr(args, "pasted_script", ""),
        content_input_mode=getattr(args, "content_input_mode", ""),
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
        execution=ExecutionFlags(
            dry_run=state.dry_run,
            prepare_only=state.prepare_only,
            resume=bool(state.project_id),
        ),
        completion_mode="draft_complete" if video_first else "",
        script_adaptation="light" if video_first else "",
        project_overrides=dict(project_overrides or {}),
    )


def load_visual_briefs(path: str) -> dict[str, dict]:
    """Read one validated visual-brief file, or return an empty mapping."""
    if not str(path or "").strip():
        return {}
    result = input_validation.validate_visual_brief_file(path)
    if not result.valid:
        raise SystemExit(f"--visual-brief: {result.message}")
    return input_validation.load_visual_briefs(path)


__all__ = ["from_cli_namespace", "from_wizard_state", "load_visual_briefs"]
