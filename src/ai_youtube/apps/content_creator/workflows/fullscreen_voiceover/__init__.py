"""Canonical Fullscreen Voiceover application boundary.

The application use case lives here. The existing ``src.news`` modules remain
the owners of the workflow, project manifest, and storage contracts; they are
re-exported rather than duplicated during the vertical migration.
"""

from importlib import import_module


_EXPORT_MODULES = {
    "NEWS_JOB_SCHEMA_VERSION": "src.news.models",
    "FullscreenVoiceoverUseCase": (
        "src.ai_youtube.apps.content_creator.workflows."
        "fullscreen_voiceover.use_case"
    ),
    "NewsJob": "src.news.models",
    "NewsPipelineResult": "src.news.pipeline",
    "NewsProject": "src.news.project_store",
    "NewsProjectStore": "src.news.project_store",
    "create_fullscreen_voiceover": (
        "src.ai_youtube.apps.content_creator.workflows."
        "fullscreen_voiceover.use_case"
    ),
    "create_news_to_short_job": "src.news.pipeline",
    "run_news_to_short_job": "src.news.pipeline",
}


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


def __getattr__(name: str):
    module_name = _EXPORT_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value
