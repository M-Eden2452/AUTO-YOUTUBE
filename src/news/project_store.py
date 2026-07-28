from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.project_foundation.storage import atomic_write_json

from .models import NewsJob, NEWS_TO_SHORT_STAGES, utc_now_iso


@dataclass
class NewsProject:
    root: Path
    job: NewsJob


class NewsProjectStore:
    def __init__(self, projects_root: str | Path | None = None) -> None:
        if projects_root is None:
            from src.config_resolver.paths import resolve_application_paths

            projects_root = resolve_application_paths().projects_root
        self.projects_root = Path(projects_root)

    def project_root(self, job_id: str) -> Path:
        return self.projects_root / job_id

    def create_project(self, job: NewsJob) -> NewsProject:
        root = self.project_root(job.job_id)
        self._create_dirs(root, job)
        self.write_json(root / "job.json", job.to_dict())
        self.write_json(
            root / "input" / "input.json",
            {
                "input_mode": job.input_mode,
                "topic": job.topic,
                "source_urls": job.source_urls,
                "input_text": job.input_text,
                "user_assets": job.user_assets,
                "language": job.language,
            },
        )
        self.write_json(root / "master" / "sources.json", {"fact_sources": [], "asset_sources": []})
        return NewsProject(root=root, job=job)

    def _create_dirs(self, root: Path, job: NewsJob) -> None:
        for folder in ("input", "article", "research", "assets", "master", "logs"):
            (root / folder).mkdir(parents=True, exist_ok=True)
        for language in job.localizations:
            language_root = root / "localizations" / language
            for folder in ("script", "voice", "voice/previews", "subtitles", "visual", "output"):
                (language_root / folder).mkdir(parents=True, exist_ok=True)

    def load_job(self, job_id: str) -> NewsJob:
        return NewsJob.from_dict(self.read_json(self.project_root(job_id) / "job.json"))

    def save_job(self, job: NewsJob) -> None:
        job.updated_at = utc_now_iso()
        self.write_json(self.project_root(job.job_id) / "job.json", job.to_dict())

    def update_stage(
        self,
        job: NewsJob,
        stage: str,
        *,
        status: str,
        result_path: str | None = None,
        error: str | None = None,
        settings: dict[str, Any] | None = None,
    ) -> None:
        state = job.stages[stage]
        state.status = status
        state.error = error
        state.settings = settings or state.settings
        if status == "running":
            state.started_at = utc_now_iso()
            state.finished_at = None
            state.attempts += 1
        if status in {"completed", "failed", "skipped", "needs_review", "blocked"}:
            state.finished_at = utc_now_iso()
        if result_path:
            state.result_path = result_path
        job.current_stage = stage
        self.save_job(job)

    def completed_stage_names(self, job: NewsJob) -> set[str]:
        return {name for name, state in job.stages.items() if state.status == "completed"}

    def next_pending_stage(self, job: NewsJob) -> str | None:
        completed = self.completed_stage_names(job)
        for stage in NEWS_TO_SHORT_STAGES:
            if stage not in completed:
                return stage
        return None

    @staticmethod
    def write_json(path: Path, data: dict[str, Any]) -> None:
        atomic_write_json(path, data)

    @staticmethod
    def read_json(path: Path) -> dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))
