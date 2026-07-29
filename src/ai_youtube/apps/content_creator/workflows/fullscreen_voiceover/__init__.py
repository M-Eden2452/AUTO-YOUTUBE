"""Canonical Fullscreen Voiceover application boundary.

The application use case lives here. The existing ``src.news`` modules remain
the owners of the workflow, project manifest, and storage contracts; they are
re-exported rather than duplicated during the vertical migration.
"""

from src.ai_youtube.apps.content_creator.workflows.fullscreen_voiceover.use_case import (
    FullscreenVoiceoverUseCase,
    create_fullscreen_voiceover,
)
from src.news.models import NEWS_JOB_SCHEMA_VERSION, NewsJob
from src.news.pipeline import (
    NewsPipelineResult,
    create_news_to_short_job,
    run_news_to_short_job,
)
from src.news.project_store import NewsProject, NewsProjectStore


__all__ = [
    "NEWS_JOB_SCHEMA_VERSION",
    "FullscreenVoiceoverUseCase",
    "NewsJob",
    "NewsPipelineResult",
    "NewsProject",
    "NewsProjectStore",
    "create_fullscreen_voiceover",
    "create_news_to_short_job",
    "run_news_to_short_job",
]
