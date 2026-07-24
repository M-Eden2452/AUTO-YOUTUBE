"""Story Card template integration with the Project/Channel Foundation (Stage 2C).

Self-contained: does not import pipeline.py, src.news, src.audio, or
src.production_catalog. It bridges src.project_foundation (ChannelProfile /
ProjectManifest) to the existing src.production_plan.story_card_short_render
renderer without duplicating renderer, provider, semantic, preview, or voice
architecture.
"""

from .integration import (
    RENDER_STATUS_DRY_RUN,
    RENDER_STATUS_FAILED,
    RENDER_STATUS_PREPARED,
    RENDER_STATUS_RENDERED,
    RENDER_STATUS_SKIPPED_EXISTING_OUTPUT,
    STORY_CARD_CANONICAL_TEMPLATE_ID,
    STORY_CARD_LEGACY_ALIASES,
    STORY_CARD_SUPPORTED_FORMAT_ID,
    StoryCardIntegrationError,
    StoryCardIntegrationResult,
    canonicalize_story_card_template_id,
    prepare_story_card_render,
)

__all__ = [
    "RENDER_STATUS_DRY_RUN",
    "RENDER_STATUS_FAILED",
    "RENDER_STATUS_PREPARED",
    "RENDER_STATUS_RENDERED",
    "RENDER_STATUS_SKIPPED_EXISTING_OUTPUT",
    "STORY_CARD_CANONICAL_TEMPLATE_ID",
    "STORY_CARD_LEGACY_ALIASES",
    "STORY_CARD_SUPPORTED_FORMAT_ID",
    "StoryCardIntegrationError",
    "StoryCardIntegrationResult",
    "canonicalize_story_card_template_id",
    "prepare_story_card_render",
]
