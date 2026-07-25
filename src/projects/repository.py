"""One read interface over the two project systems that coexist in ``projects/``.

Why this exists
---------------
``projects/`` currently holds both shapes side by side:

- ``job.json``     - written by src.news.project_store.NewsProjectStore (fullscreen_voiceover_v1
                     / news_to_short): 12 stages, localizations, quality report, render manifest;
- ``project.json`` - written by src.project_foundation.projects.ProjectFactory (story_card_
                     text_only_v1): a ProjectManifest with template/application/format ids and
                     an EvidenceBundle, but no stage state.

Nothing could read both, so ``content-creation project status`` crashed with a raw
traceback on 19 of the 21 project folders, and any future UI would have had to
implement the split twice.

Design constraints (from docs/handoff/AUTONOMOUS_ARCHITECTURE_AUDIT.md §7)
-------------------------------------------------------------------------
This module is **read-only on purpose**. It is explicitly *not* a third project
system: it owns no storage format, writes nothing, migrates nothing, and creates
nothing. It reads the two existing manifests through their own owners
(``NewsJob.from_dict`` / ``ProjectManifest.from_dict``) and normalizes them into one
``ProjectView``. Adding a writer here would recreate exactly the duplication it is
meant to hide - a write path must go through the owning system.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

PROJECT_KIND_NEWS_JOB = "news_job"
PROJECT_KIND_PROJECT_MANIFEST = "project_manifest"
PROJECT_KIND_UNKNOWN = "unknown"

JOB_FILENAME = "job.json"
PROJECT_FILENAME = "project.json"

# Templates each storage system actually backs today (see the audit's §4 matrix).
_NEWS_JOB_TEMPLATE_ID = "fullscreen_voiceover_v1"


class ProjectNotFoundError(LookupError):
    """Raised when no project with the given id exists under the projects root."""


@dataclass
class ProjectStage:
    stage: str
    status: str = "pending"
    result_path: str = ""
    error: str = ""
    attempts: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "status": self.status,
            "result_path": self.result_path,
            "error": self.error,
            "attempts": self.attempts,
        }


@dataclass
class ProjectView:
    """Normalized, read-only description of one project on disk."""

    project_id: str
    kind: str
    project_root: str
    title: str = ""
    channel_id: str = ""
    application_id: str = ""
    format_id: str = ""
    template_id: str = ""
    language: str = ""
    status: str = "unknown"
    created_at: str = ""
    updated_at: str = ""
    stages: list[ProjectStage] = field(default_factory=list)
    output_paths: dict[str, str] = field(default_factory=dict)
    final_video: str = ""
    quality_status: str = ""
    evidence_paths: list[str] = field(default_factory=list)
    manifest_path: str = ""
    warnings: list[str] = field(default_factory=list)

    @property
    def completed_stages(self) -> list[str]:
        return [stage.stage for stage in self.stages if stage.status == "completed"]

    @property
    def last_completed_stage(self) -> str:
        """The furthest stage that finished, in pipeline order.

        `stages` is stored in the pipeline's own order, so the last completed entry
        is the right answer; an empty string means nothing has finished yet (or the
        project kind has no stages at all, like story card).
        """
        completed = self.completed_stages
        return completed[-1] if completed else ""

    @property
    def is_finished(self) -> bool:
        """A project is done when it has a playable file, not when a flag says so."""
        return bool(self.final_video)

    @property
    def blocking_stages(self) -> list[str]:
        return [stage.stage for stage in self.stages if stage.status in {"failed", "needs_review", "blocked"}]

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "kind": self.kind,
            "project_root": self.project_root,
            "title": self.title,
            "channel_id": self.channel_id,
            "application_id": self.application_id,
            "format_id": self.format_id,
            "template_id": self.template_id,
            "language": self.language,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "stages": [stage.to_dict() for stage in self.stages],
            "completed_stages": self.completed_stages,
            "last_completed_stage": self.last_completed_stage,
            "is_finished": self.is_finished,
            "blocking_stages": self.blocking_stages,
            "output_paths": dict(self.output_paths),
            "final_video": self.final_video,
            "quality_status": self.quality_status,
            "evidence_paths": list(self.evidence_paths),
            "manifest_path": self.manifest_path,
            "warnings": list(self.warnings),
        }


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


class ProjectRepository:
    """Lists and reads projects of either kind under one root. Never writes."""

    def __init__(self, projects_root: str | Path = "projects") -> None:
        self.projects_root = Path(projects_root)

    # -- discovery ----------------------------------------------------------

    def project_root(self, project_id: str) -> Path:
        return self.projects_root / project_id

    def detect_kind(self, project_id: str) -> str:
        root = self.project_root(project_id)
        if (root / JOB_FILENAME).is_file():
            return PROJECT_KIND_NEWS_JOB
        if (root / PROJECT_FILENAME).is_file():
            return PROJECT_KIND_PROJECT_MANIFEST
        return PROJECT_KIND_UNKNOWN

    def exists(self, project_id: str) -> bool:
        return self.project_root(project_id).is_dir()

    def list_ids(self) -> list[str]:
        if not self.projects_root.is_dir():
            return []
        return [entry.name for entry in sorted(self.projects_root.iterdir(), key=lambda item: item.name) if entry.is_dir()]

    def list(self, *, include_unknown: bool = False) -> list[ProjectView]:
        views: list[ProjectView] = []
        for project_id in self.list_ids():
            kind = self.detect_kind(project_id)
            if kind == PROJECT_KIND_UNKNOWN and not include_unknown:
                continue
            views.append(self.get(project_id))
        return views

    # -- reading ------------------------------------------------------------

    def get(self, project_id: str) -> ProjectView:
        root = self.project_root(project_id)
        if not root.is_dir():
            raise ProjectNotFoundError(
                f"Project {project_id!r} was not found in {self.projects_root.as_posix()!r}."
            )
        kind = self.detect_kind(project_id)
        if kind == PROJECT_KIND_NEWS_JOB:
            return self._read_news_job(project_id, root)
        if kind == PROJECT_KIND_PROJECT_MANIFEST:
            return self._read_project_manifest(project_id, root)
        return ProjectView(
            project_id=project_id,
            kind=PROJECT_KIND_UNKNOWN,
            project_root=str(root),
            title=project_id,
            warnings=[f"Neither {JOB_FILENAME} nor {PROJECT_FILENAME} was found in this folder."],
        )

    def _read_news_job(self, project_id: str, root: Path) -> ProjectView:
        from src.news.models import NewsJob

        manifest_path = root / JOB_FILENAME
        data = _read_json(manifest_path)
        warnings: list[str] = []
        if data is None:
            return ProjectView(
                project_id=project_id,
                kind=PROJECT_KIND_NEWS_JOB,
                project_root=str(root),
                manifest_path=str(manifest_path),
                warnings=[f"{JOB_FILENAME} could not be read as JSON."],
            )
        try:
            job = NewsJob.from_dict(data)
        except TypeError as exc:
            # A job.json written by an older/newer schema: still show what we can
            # rather than failing the whole listing.
            warnings.append(f"job.json did not match the current NewsJob schema ({exc}); showing raw fields.")
            job = None

        stages = [
            ProjectStage(
                stage=name,
                status=str(state.get("status", "pending")),
                result_path=str(state.get("result_path") or ""),
                error=str(state.get("error") or ""),
                attempts=int(state.get("attempts") or 0),
            )
            for name, state in (data.get("stages") or {}).items()
            if isinstance(state, dict)
        ]

        language = str((job.language if job else data.get("language")) or "ru")
        quality = _read_json(root / "quality" / "quality_report.json") or {}
        final_render = _read_json(root / "render" / "final_render_manifest.json") or {}
        outputs = {str(key): str(value) for key, value in (final_render.get("outputs") or {}).items()}
        final_video = str(final_render.get("output_path") or "")
        if final_video and not Path(final_video).exists():
            warnings.append("final_render_manifest points at an output file that no longer exists.")
            final_video = ""

        evidence_paths = [
            str(path)
            for path in (
                root / "assets" / "assets_manifest.json",
                root / "assets" / "sources.json",
                root / "assets" / "ATTRIBUTION.md",
            )
            if path.is_file()
        ]

        return ProjectView(
            project_id=project_id,
            kind=PROJECT_KIND_NEWS_JOB,
            project_root=str(root),
            # A job.json written before NewsJob gained `title` has none; the topic is
            # what those projects were named after, so it stays the fallback.
            title=str((job.title if job else data.get("title")) or (job.topic if job else data.get("topic")) or project_id),
            channel_id=str((job.channel_id if job else data.get("channel_id")) or ""),
            application_id="content_creator",
            format_id="vertical_short",
            template_id=_NEWS_JOB_TEMPLATE_ID,
            language=language,
            status=str((job.status if job else data.get("status")) or "unknown"),
            created_at=str((job.created_at if job else data.get("created_at")) or ""),
            updated_at=str((job.updated_at if job else data.get("updated_at")) or ""),
            stages=stages,
            output_paths=outputs,
            final_video=final_video,
            quality_status=str(quality.get("status") or ""),
            evidence_paths=evidence_paths,
            manifest_path=str(manifest_path),
            warnings=warnings,
        )

    def _read_project_manifest(self, project_id: str, root: Path) -> ProjectView:
        from src.project_foundation.models import ProjectFoundationError, ProjectManifest

        manifest_path = root / PROJECT_FILENAME
        data = _read_json(manifest_path)
        if data is None:
            return ProjectView(
                project_id=project_id,
                kind=PROJECT_KIND_PROJECT_MANIFEST,
                project_root=str(root),
                manifest_path=str(manifest_path),
                warnings=[f"{PROJECT_FILENAME} could not be read as JSON."],
            )
        try:
            manifest = ProjectManifest.from_dict(data)
        except ProjectFoundationError as exc:
            return ProjectView(
                project_id=project_id,
                kind=PROJECT_KIND_PROJECT_MANIFEST,
                project_root=str(root),
                manifest_path=str(manifest_path),
                warnings=[f"project.json is not a valid ProjectManifest: {exc}"],
            )

        outputs_dir = root / "outputs"
        outputs = (
            {path.name: str(path) for path in sorted(outputs_dir.iterdir()) if path.is_file()}
            if outputs_dir.is_dir()
            else {}
        )
        final_video = next((path for name, path in outputs.items() if name.endswith(".mp4")), "")
        evidence_dir = root / "evidence"
        evidence_paths = (
            [str(path) for path in sorted(evidence_dir.iterdir()) if path.is_file()] if evidence_dir.is_dir() else []
        )

        return ProjectView(
            project_id=project_id,
            kind=PROJECT_KIND_PROJECT_MANIFEST,
            project_root=str(root),
            title=manifest.title,
            channel_id=manifest.channel_id,
            application_id=manifest.application_id,
            format_id=manifest.format_id,
            template_id=manifest.template_id,
            language=manifest.language,
            status=manifest.status,
            created_at=manifest.created_at,
            updated_at=manifest.updated_at,
            # ProjectFactory projects have no stage state at all; an empty list is the
            # honest answer, not a fabricated "completed".
            stages=[],
            output_paths=outputs,
            final_video=final_video,
            evidence_paths=evidence_paths,
            manifest_path=str(manifest_path),
        )


__all__ = [
    "PROJECT_KIND_NEWS_JOB",
    "PROJECT_KIND_PROJECT_MANIFEST",
    "PROJECT_KIND_UNKNOWN",
    "ProjectNotFoundError",
    "ProjectRepository",
    "ProjectStage",
    "ProjectView",
]
