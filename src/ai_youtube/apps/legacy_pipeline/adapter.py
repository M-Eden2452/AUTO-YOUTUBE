"""Lazy application adapter for the historical root pipeline.

The adapter exposes the existing root command facade and split workflow
contracts without importing or copying their implementation. Resolving exports
at access time also preserves historical monkeypatch points on ``pipeline``.
"""

from importlib import import_module


_EXPORT_MODULES = {
    "LegacyPipelineArtifacts": "src.legacy_pipeline.workflow",
    "limit_scene_plan": "pipeline",
    "main": "pipeline",
    "parse_args": "pipeline",
    "run_legacy_video_pipeline": "pipeline",
    "run_maintenance_command": "pipeline",
}

__all__ = [
    "LegacyPipelineArtifacts",
    "limit_scene_plan",
    "main",
    "parse_args",
    "run_legacy_video_pipeline",
    "run_maintenance_command",
]


def __getattr__(name: str):
    module_name = _EXPORT_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    return getattr(import_module(module_name), name)
