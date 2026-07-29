from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.project_foundation.storage import atomic_write_json, project_lock

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

    def is_stage_completed(self, job: NewsJob, stage: str) -> bool:
        state = job.stages.get(stage)
        if state is None or state.status != "completed":
            return False
        return self.validate_stage_output(job, stage)

    def validate_stage_output(self, job: NewsJob, stage: str) -> bool:
        root = self.project_root(job.job_id)
        if stage == "research":
            claims_path = root / "research" / "claims.json"
            if not claims_path.is_file():
                return False
            try:
                data = self.read_json(claims_path)
                return isinstance(data, dict) and isinstance(data.get("claims"), list)
            except Exception:
                return False
        if stage == "script":
            script_path = (
                root
                / "localizations"
                / job.language
                / "script"
                / "script.json"
            )
            if not script_path.is_file():
                return False
            try:
                data = self.read_json(script_path)
                scenes = data.get("scenes")
                narration_text = data.get("narration_text")
                return (
                    isinstance(data, dict)
                    and isinstance(narration_text, str)
                    and bool(narration_text.strip())
                    and isinstance(scenes, list)
                    and bool(scenes)
                    and all(isinstance(scene, dict) for scene in scenes)
                )
            except Exception:
                return False
        if stage == "visual_plan":
            visual_plan_path = (
                root
                / "localizations"
                / job.language
                / "visual"
                / "visual_plan.json"
            )
            if not visual_plan_path.is_file():
                return False
            try:
                data = self.read_json(visual_plan_path)
                scenes = data.get("scenes")
                return (
                    isinstance(data, dict)
                    and isinstance(scenes, list)
                    and bool(scenes)
                    and all(isinstance(scene, dict) for scene in scenes)
                )
            except Exception:
                return False
        if stage == "asset_search":
            manifest = self._read_json_object(root / "assets" / "assets_manifest.json")
            if manifest is None:
                return False
            scenes = manifest.get("scenes")
            missing_scenes = manifest.get("missing_scenes")
            if "schema_version" not in manifest and scenes is None:
                return (
                    isinstance(manifest.get("dry_run"), bool)
                    and isinstance(manifest.get("assets"), list)
                    and isinstance(missing_scenes, list)
                    and all(isinstance(scene, dict) for scene in missing_scenes)
                    and isinstance(manifest.get("warnings"), list)
                )
            return (
                isinstance(scenes, list)
                and bool(scenes)
                and all(isinstance(scene, dict) for scene in scenes)
                and isinstance(missing_scenes, list)
                and all(isinstance(scene, dict) for scene in missing_scenes)
            )
        if stage == "voice":
            manifest = self._read_json_object(
                root
                / "localizations"
                / job.language
                / "voice"
                / "voice_manifest.json"
            )
            if manifest is None:
                return False
            status = manifest.get("voice_stage_status") or manifest.get("status")
            audio_path = manifest.get("audio_path", "")
            if not isinstance(status, str) or not status.strip():
                return False
            if not isinstance(audio_path, str):
                return False
            if status == "completed":
                return self._declared_file_exists(root, audio_path)
            return True
        if stage == "subtitles":
            manifest = self._read_json_object(
                root
                / "localizations"
                / job.language
                / "subtitles"
                / "subtitles_manifest.json"
            )
            if manifest is None:
                return False
            status = manifest.get("status")
            cues = manifest.get("cues")
            segments = cues if isinstance(cues, list) and cues else manifest.get("segments")
            if not isinstance(status, str) or not status.strip():
                return False
            if manifest.get("protected") or manifest.get("source") == "user_supplied":
                return True
            if (
                not isinstance(segments, list)
                or not segments
                or not all(isinstance(segment, dict) for segment in segments)
            ):
                return False
            declared_paths = manifest.get("paths")
            if isinstance(declared_paths, dict) and declared_paths:
                paths = list(declared_paths.values())
            else:
                paths = [
                    manifest.get(name)
                    for name in ("srt_path", "ass_path")
                    if manifest.get(name)
                ]
            return bool(paths) and all(
                self._declared_file_exists(root, path) for path in paths
            )
        if stage == "preview_render":
            return self._is_nonempty_file(root / "preview" / "preview.mp4")
        if stage == "quality_check":
            report = self._read_json_object(root / "quality" / "quality_report.json")
            if report is None:
                return False
            return (
                report.get("status") in {"passed", "needs_review", "failed"}
                and isinstance(report.get("errors"), list)
                and isinstance(report.get("warnings"), list)
                and isinstance(report.get("checks"), list)
            )
        if stage == "final_render":
            manifest = self._read_json_object(
                root / "render" / "final_render_manifest.json"
            )
            return (
                manifest is not None
                and manifest.get("status") == "completed"
                and self._declared_file_exists(root, manifest.get("output_path"))
            )
        if stage == "export":
            manifest = self._read_json_object(
                root
                / "localizations"
                / job.language
                / "output"
                / "project_manifest.json"
            )
            required = {
                "job_id",
                "mode",
                "channel_id",
                "language",
                "status",
                "description_path",
                "sources_path",
                "quality_report",
                "outputs",
            }
            return (
                manifest is not None
                and required.issubset(manifest)
                and isinstance(manifest.get("language"), str)
                and bool(manifest["language"].strip())
                and isinstance(manifest.get("description_path"), str)
                and bool(manifest["description_path"].strip())
                and isinstance(manifest.get("sources_path"), str)
                and bool(manifest["sources_path"].strip())
                and isinstance(manifest.get("quality_report"), dict)
                and isinstance(manifest.get("outputs"), dict)
            )
        return True

    @staticmethod
    def _read_json_object(path: Path) -> dict[str, Any] | None:
        if not path.is_file():
            return None
        try:
            data = NewsProjectStore.read_json(path)
        except (OSError, ValueError, TypeError):
            return None
        return data if isinstance(data, dict) else None

    @staticmethod
    def _is_nonempty_file(path: Path) -> bool:
        try:
            return path.is_file() and path.stat().st_size > 0
        except OSError:
            return False

    def _declared_file_exists(self, root: Path, value: Any) -> bool:
        if not isinstance(value, str) or not value.strip():
            return False
        declared = Path(value)
        candidates = [declared]
        if not declared.is_absolute():
            candidates.extend((root / declared, self.projects_root.parent / declared))
        return any(self._is_nonempty_file(candidate) for candidate in candidates)

    def completed_stage_names(self, job: NewsJob) -> set[str]:
        return {name for name in job.stages if self.is_stage_completed(job, name)}

    def next_pending_stage(self, job: NewsJob) -> str | None:
        completed = self.completed_stage_names(job)
        for stage in NEWS_TO_SHORT_STAGES:
            if stage not in completed:
                return stage
        return None

    @staticmethod
    def write_json(path: Path, data: dict[str, Any]) -> None:
        target = Path(path)
        project_root = NewsProjectStore._project_root_for_write(target)
        with project_lock(project_root):
            atomic_write_json(target, data)

    @staticmethod
    def _project_root_for_write(path: Path) -> Path:
        if path.name == "job.json":
            return path.parent
        for parent in path.parents:
            if (parent / "job.json").is_file():
                return parent
        return path.parent

    @staticmethod
    def read_json(path: Path) -> dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))
