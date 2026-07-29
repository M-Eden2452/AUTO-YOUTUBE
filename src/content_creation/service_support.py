from __future__ import annotations

from pathlib import Path
from typing import Callable

from src.content_creation.models import ContentCreationRequest


ProgressCallback = Callable[[str, str], None]


def notify(
    callback: ProgressCallback | None,
    stage: str,
    status: str,
) -> None:
    if callback is not None:
        callback(stage, status)


def request_path_context(
    request: ContentCreationRequest,
) -> tuple[Path, tuple[Path, ...], Path]:
    from src.config_resolver import resolve_application_paths

    explicit_projects_root = request.project_overrides.get("projects_root")
    paths = resolve_application_paths(
        workspace_root=request.project_overrides.get("workspace_root") or None,
        paths_config=request.project_overrides.get("paths_config") or None,
        projects_root=explicit_projects_root or None,
    )
    fallback_values = request.project_overrides.get("project_fallback_roots")
    if fallback_values is None:
        fallback_roots = paths.project_fallback_roots
    else:
        fallback_roots = tuple(Path(value) for value in fallback_values)
    channels_root = Path(
        request.project_overrides.get("channels_root") or paths.channels_root
    )
    return paths.projects_root, fallback_roots, channels_root
