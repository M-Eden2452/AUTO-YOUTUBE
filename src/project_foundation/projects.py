from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .models import ChannelProfile, ProjectFoundationError, ProjectManifest, utc_now_iso
from .storage import atomic_write_json, ensure_dir, read_json_if_exists

PROJECT_FILENAME = "project.json"

PROJECT_SUBDIRS = ("evidence", "assets", "outputs", "logs")


def _slugify(title: str) -> str:
    text = str(title or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    return text or "project"


def generate_project_id(title: str) -> str:
    suffix = uuid.uuid4().hex[:8]
    return f"{_slugify(title)}-{suffix}"


@dataclass
class ProjectCreationResult:
    manifest: ProjectManifest
    created_paths: list[str] = field(default_factory=list)
    dry_run: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "manifest": self.manifest.to_dict(),
            "created_paths": list(self.created_paths),
            "dry_run": self.dry_run,
        }


class ProjectFactory:
    """Creates minimal project structures on disk without downloading, rendering, or calling any API."""

    def __init__(self, base_dir: str | Path = "projects") -> None:
        self.base_dir = Path(base_dir)

    def _project_dir(self, project_id: str) -> Path:
        return self.base_dir / project_id

    def _project_file(self, project_id: str) -> Path:
        return self._project_dir(project_id) / PROJECT_FILENAME

    def exists(self, project_id: str) -> bool:
        return self._project_file(project_id).is_file()

    def create(
        self,
        channel: ChannelProfile,
        *,
        title: str,
        project_id: str | None = None,
        application_id: str | None = None,
        format_id: str | None = None,
        template_id: str | None = None,
        language: str | None = None,
        export_targets: list[str] | None = None,
        source_type: str = "manual",
        source_reference: str = "",
        metadata: dict[str, Any] | None = None,
        dry_run: bool = False,
    ) -> ProjectCreationResult:
        if not isinstance(channel, ChannelProfile):
            raise ProjectFoundationError("ProjectFactory.create requires a ChannelProfile instance.")
        title = str(title or "").strip()
        if not title:
            raise ProjectFoundationError("ProjectFactory.create requires a non-empty title.")

        resolved_project_id = str(project_id or generate_project_id(title))
        resolved_application_id = str(application_id or channel.default_application or "")
        resolved_format_id = str(format_id or channel.default_format or "")
        resolved_template_id = str(template_id or channel.default_template or "")
        resolved_language = str(language or channel.default_language or "ru")
        resolved_export_targets = list(export_targets) if export_targets is not None else list(channel.export_targets)

        if resolved_language not in channel.supported_languages:
            raise ProjectFoundationError(
                f"Language {resolved_language!r} is not in supported_languages of channel {channel.channel_id!r}: "
                f"{channel.supported_languages}."
            )
        if not resolved_application_id:
            raise ProjectFoundationError("application_id is required (explicitly or via channel.default_application).")
        if not resolved_format_id:
            raise ProjectFoundationError("format_id is required (explicitly or via channel.default_format).")
        if not resolved_template_id:
            raise ProjectFoundationError("template_id is required (explicitly or via channel.default_template).")

        if self.exists(resolved_project_id):
            raise ProjectFoundationError(f"Project {resolved_project_id!r} already exists and cannot be overwritten.")

        project_root = f"{self.base_dir.as_posix()}/{resolved_project_id}"
        localization_root = f"{project_root}/localizations/{resolved_language}"
        evidence_root = f"{project_root}/evidence"

        now = utc_now_iso()
        manifest = ProjectManifest(
            project_id=resolved_project_id,
            title=title,
            channel_id=channel.channel_id,
            application_id=resolved_application_id,
            format_id=resolved_format_id,
            template_id=resolved_template_id,
            language=resolved_language,
            export_targets=resolved_export_targets,
            status="draft",
            source_type=source_type,
            source_reference=source_reference,
            project_root=project_root,
            localization_root=localization_root,
            evidence_root=evidence_root,
            created_at=now,
            updated_at=now,
            metadata=dict(metadata or {}),
        )

        project_dir = self._project_dir(resolved_project_id)
        planned_paths = [
            str(project_dir),
            *(str(project_dir / sub) for sub in PROJECT_SUBDIRS),
            str(project_dir / "localizations" / resolved_language),
            str(self._project_file(resolved_project_id)),
        ]

        if dry_run:
            return ProjectCreationResult(manifest=manifest, created_paths=planned_paths, dry_run=True)

        ensure_dir(project_dir)
        for sub in PROJECT_SUBDIRS:
            ensure_dir(project_dir / sub)
        ensure_dir(project_dir / "localizations" / resolved_language)
        atomic_write_json(self._project_file(resolved_project_id), manifest.to_dict())

        return ProjectCreationResult(manifest=manifest, created_paths=planned_paths, dry_run=False)

    def get(self, project_id: str) -> ProjectManifest:
        data = read_json_if_exists(self._project_file(project_id))
        if data is None:
            raise ProjectFoundationError(f"Project {project_id!r} was not found.")
        return ProjectManifest.from_dict(data)

    def list(self) -> list[ProjectManifest]:
        if not self.base_dir.is_dir():
            return []
        manifests: list[ProjectManifest] = []
        for entry in sorted(self.base_dir.iterdir(), key=lambda item: item.name):
            project_file = entry / PROJECT_FILENAME
            if entry.is_dir() and project_file.is_file():
                manifests.append(ProjectManifest.from_dict(read_json_if_exists(project_file)))
        return manifests

    def save(self, manifest: ProjectManifest) -> ProjectManifest:
        if not self.exists(manifest.project_id):
            raise ProjectFoundationError(f"Project {manifest.project_id!r} does not exist and cannot be saved.")
        manifest.updated_at = utc_now_iso()
        atomic_write_json(self._project_file(manifest.project_id), manifest.to_dict())
        return manifest
