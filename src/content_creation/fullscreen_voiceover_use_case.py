"""Compatibility wrapper for the canonical Fullscreen Voiceover use case."""

from src.ai_youtube.apps.content_creator.workflows.fullscreen_voiceover.use_case import (
    FullscreenVoiceoverUseCase,
    _RETRYABLE_ARTICLE_REASONS,
    build_paid_preflight_summary,
    completed_narration,
    create_fullscreen_voiceover,
    create_paid_voice_approval,
    fullscreen_rerun_command,
    resolve_content_inputs,
    resolve_localization,
    resolve_script_source,
    resolve_voice_inputs,
)


__all__ = [
    "FullscreenVoiceoverUseCase",
    "build_paid_preflight_summary",
    "completed_narration",
    "create_fullscreen_voiceover",
    "create_paid_voice_approval",
    "fullscreen_rerun_command",
    "resolve_content_inputs",
    "resolve_localization",
    "resolve_script_source",
    "resolve_voice_inputs",
]
