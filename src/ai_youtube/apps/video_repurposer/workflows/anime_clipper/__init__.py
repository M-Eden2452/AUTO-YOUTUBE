"""Canonical Anime Clipper adapter boundary.

The existing ``anime_factory`` package remains the owner of workflow behavior,
episode paths, and output layout. This boundary exposes those contracts without
copying the implementation or changing the planned/disabled catalog status.
"""

from importlib import import_module


_EXPORT_MODULES = {
    "PROJECT_ROOT": "anime_factory.modules.paths",
    "EpisodePaths": "anime_factory.modules.paths",
    "get_episode_paths": "anime_factory.modules.paths",
    "main": "anime_factory.pipeline",
    "parse_args": "anime_factory.pipeline",
    "run_pipeline": "anime_factory.pipeline",
}

__all__ = [
    "PROJECT_ROOT",
    "EpisodePaths",
    "get_episode_paths",
    "main",
    "parse_args",
    "run_pipeline",
]


def __getattr__(name: str):
    module_name = _EXPORT_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    return getattr(import_module(module_name), name)
