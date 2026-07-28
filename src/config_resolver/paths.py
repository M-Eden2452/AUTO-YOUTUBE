"""Canonical application and runtime path resolution.

The repository still contains runtime data, so the default workspace remains the
repository root until rescue stage 9 performs a verified copy/switch.  This module
only makes the boundary explicit and lets callers opt into another workspace without
moving anything.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Mapping


ENV_WORKSPACE_ROOT = "AI_YOUTUBE_WORKSPACE"
ENV_PATHS_CONFIG = "AI_YOUTUBE_PATHS_CONFIG"
DEFAULT_PATHS_CONFIG = Path("config/system/paths.json")

_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


class PathConfigurationError(ValueError):
    """Raised when an explicit path configuration cannot be read or is invalid."""


def _absolute(path: str | Path, *, base: Path) -> Path:
    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        candidate = base / candidate
    return candidate.resolve(strict=False)


def repository_path(*parts: str | Path) -> Path:
    """Return a versioned repository resource without consulting cwd."""

    return _REPOSITORY_ROOT.joinpath(*(Path(part) for part in parts))


def _same_path(left: Path, right: Path) -> bool:
    return os.path.normcase(str(left.resolve(strict=False))) == os.path.normcase(
        str(right.resolve(strict=False))
    )


def _read_path_config(path: Path, *, required: bool) -> dict[str, Any]:
    if not path.is_file():
        if required:
            raise PathConfigurationError(f"Path config does not exist: {path}")
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PathConfigurationError(f"Path config is not valid JSON: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise PathConfigurationError(f"Path config must contain a JSON object: {path}")
    nested = data.get("paths")
    if nested is not None:
        if not isinstance(nested, dict):
            raise PathConfigurationError(f"The 'paths' value must be a JSON object: {path}")
        data = nested
    return data


def _configured_child(config: Mapping[str, Any], key: str, default: str, *, root: Path) -> Path:
    value = config.get(key, default)
    if not isinstance(value, (str, os.PathLike)) or not str(value).strip():
        raise PathConfigurationError(f"Path setting {key!r} must be a non-empty path.")
    return _absolute(value, base=root)


@dataclass(frozen=True)
class WorkspacePaths:
    """Writable runtime locations under one selected workspace."""

    root: Path
    projects: Path
    outputs: Path
    exports: Path
    artifacts: Path
    media_library: Path
    manual_assets: Path
    music: Path
    provider_cache: Path
    temp: Path
    runtime_reports: Path
    user_config: Path

    @classmethod
    def from_root(
        cls,
        root: str | Path,
        *,
        config: Mapping[str, Any] | None = None,
    ) -> "WorkspacePaths":
        resolved_root = _absolute(root, base=_REPOSITORY_ROOT)
        values = config or {}
        return cls(
            root=resolved_root,
            projects=_configured_child(values, "projects_dir", "projects", root=resolved_root),
            outputs=_configured_child(values, "outputs_dir", "outputs", root=resolved_root),
            exports=_configured_child(values, "exports_dir", "exports", root=resolved_root),
            artifacts=_configured_child(values, "artifacts_dir", "artifacts", root=resolved_root),
            media_library=_configured_child(
                values, "media_library_dir", "assets/library", root=resolved_root
            ),
            manual_assets=_configured_child(
                values, "manual_assets_dir", "manual_assets", root=resolved_root
            ),
            music=_configured_child(values, "music_dir", "music", root=resolved_root),
            provider_cache=_configured_child(
                values, "provider_cache_dir", "assets/cache", root=resolved_root
            ),
            temp=_configured_child(values, "temp_dir", "temp", root=resolved_root),
            runtime_reports=_configured_child(
                values, "runtime_reports_dir", "runtime_reports", root=resolved_root
            ),
            user_config=_configured_child(
                values, "user_config_dir", "user_config", root=resolved_root
            ),
        )


@dataclass(frozen=True)
class ApplicationPaths:
    """Versioned application resources plus the selected runtime workspace."""

    repository_root: Path
    config_root: Path
    channels_root: Path
    content_root: Path
    workspace: WorkspacePaths
    legacy_projects_root: Path
    legacy_outputs_root: Path
    path_config_file: Path | None = None
    workspace_source: str = "legacy_repository_default"
    include_legacy_project_fallback: bool = True

    @property
    def projects_root(self) -> Path:
        return self.workspace.projects

    @property
    def outputs_root(self) -> Path:
        return self.workspace.outputs

    @property
    def project_read_roots(self) -> tuple[Path, ...]:
        roots = [self.projects_root]
        if (
            self.include_legacy_project_fallback
            and not _same_path(self.projects_root, self.legacy_projects_root)
        ):
            roots.append(self.legacy_projects_root)
        return tuple(roots)

    @property
    def output_read_roots(self) -> tuple[Path, ...]:
        roots = [self.outputs_root]
        if not _same_path(self.outputs_root, self.legacy_outputs_root):
            roots.append(self.legacy_outputs_root)
        return tuple(roots)

    @property
    def project_fallback_roots(self) -> tuple[Path, ...]:
        return self.project_read_roots[1:]

    def find_project_root(self, project_id: str) -> Path:
        for root in self.project_read_roots:
            candidate = root / project_id
            if candidate.is_dir():
                return candidate
        return self.projects_root / project_id

    def find_output(self, relative_path: str | Path) -> Path:
        relative = Path(relative_path)
        if relative.is_absolute():
            return relative
        for root in self.output_read_roots:
            candidate = root / relative
            if candidate.exists():
                return candidate
        return self.outputs_root / relative

    def with_projects_root(self, projects_root: str | Path) -> "ApplicationPaths":
        """Preserve the old explicit ``--projects-root`` contract.

        An explicit root is intentionally isolated: compatibility tests and
        maintenance commands that name a fixture directory must not also see the
        repository's real projects.
        """

        resolved = _absolute(projects_root, base=self.repository_root)
        return replace(
            self,
            workspace=replace(self.workspace, projects=resolved),
            include_legacy_project_fallback=False,
        )


def resolve_application_paths(
    *,
    workspace_root: str | Path | None = None,
    paths_config: str | Path | None = None,
    projects_root: str | Path | None = None,
    environment: Mapping[str, str] | None = None,
    repository_root: str | Path | None = None,
) -> ApplicationPaths:
    """Resolve paths with ``CLI > environment > config > legacy default`` precedence.

    Relative CLI/environment paths are anchored to the repository, not ``Path.cwd()``.
    A ``workspace_root`` inside a JSON config is relative to that config file.
    """

    repository = (
        _absolute(repository_root, base=_REPOSITORY_ROOT)
        if repository_root is not None
        else _REPOSITORY_ROOT
    )
    env = os.environ if environment is None else environment

    env_config = str(env.get(ENV_PATHS_CONFIG, "") or "").strip()
    explicit_config = paths_config is not None or bool(env_config)
    config_value = paths_config if paths_config is not None else env_config or DEFAULT_PATHS_CONFIG
    config_file = _absolute(config_value, base=repository)
    config = _read_path_config(config_file, required=explicit_config)
    used_config_file = config_file if config_file.is_file() else None

    cli_workspace = str(workspace_root or "").strip()
    env_workspace = str(env.get(ENV_WORKSPACE_ROOT, "") or "").strip()
    config_workspace = config.get("workspace_root")
    if config_workspace is not None and not isinstance(
        config_workspace, (str, os.PathLike)
    ):
        raise PathConfigurationError("Path setting 'workspace_root' must be a path.")
    if cli_workspace:
        resolved_workspace = _absolute(cli_workspace, base=repository)
        source = "cli"
    elif env_workspace:
        resolved_workspace = _absolute(env_workspace, base=repository)
        source = "environment"
    elif config_workspace is not None and str(config_workspace).strip():
        resolved_workspace = _absolute(config_workspace, base=config_file.parent)
        source = "config"
    else:
        resolved_workspace = repository
        source = "legacy_repository_default"

    workspace = WorkspacePaths.from_root(resolved_workspace, config=config)
    paths = ApplicationPaths(
        repository_root=repository,
        config_root=repository / "config",
        channels_root=repository / "channels",
        content_root=repository / "content",
        workspace=workspace,
        legacy_projects_root=repository / "projects",
        legacy_outputs_root=repository / "outputs",
        path_config_file=used_config_file,
        workspace_source=source,
        include_legacy_project_fallback=True,
    )
    if projects_root is not None and str(projects_root).strip():
        paths = paths.with_projects_root(projects_root)
    return paths


__all__ = [
    "DEFAULT_PATHS_CONFIG",
    "ENV_PATHS_CONFIG",
    "ENV_WORKSPACE_ROOT",
    "ApplicationPaths",
    "PathConfigurationError",
    "WorkspacePaths",
    "repository_path",
    "resolve_application_paths",
]
