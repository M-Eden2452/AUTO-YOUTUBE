"""Read-only ProjectRepository over both project systems.

Everything runs against tempfile-backed project folders: no network, no writes to
the real projects/ tree, no ffmpeg, no provider.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.projects import (
    PROJECT_KIND_NEWS_JOB,
    PROJECT_KIND_PROJECT_MANIFEST,
    PROJECT_KIND_UNKNOWN,
    ProjectNotFoundError,
    ProjectRepository,
)


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _make_news_job(root: Path, project_id: str, *, status: str = "completed", with_video: bool = True) -> Path:
    from src.news.models import NewsJob

    job = NewsJob.create(channel_id="nature_science_news_ru", input_mode="topic", topic="Тестовая тема")
    job.job_id = project_id
    job.status = status
    for name in job.stages:
        job.stages[name].status = "completed"
    project_root = root / project_id
    _write(project_root / "job.json", job.to_dict())
    _write(project_root / "quality" / "quality_report.json", {"status": "passed", "errors": [], "warnings": []})
    if with_video:
        video = project_root / "localizations" / "ru" / "output" / "master_1080x1920.mp4"
        video.parent.mkdir(parents=True, exist_ok=True)
        video.write_bytes(b"not-a-real-mp4")
        _write(
            project_root / "render" / "final_render_manifest.json",
            {"status": "completed", "output_path": str(video), "outputs": {"master_1080x1920": str(video)}},
        )
    _write(project_root / "assets" / "assets_manifest.json", {"schema_version": 1, "scenes": []})
    return project_root


def _make_project_manifest(root: Path, project_id: str) -> Path:
    from src.project_foundation.models import ProjectManifest

    project_root = root / project_id
    manifest = ProjectManifest(
        project_id=project_id,
        title="Карточка про сову",
        channel_id="nature_pulse",
        application_id="content_creator",
        format_id="vertical_short",
        template_id="story_card_text_only_v1",
        language="ru",
        project_root=str(project_root),
    )
    _write(project_root / "project.json", manifest.to_dict())
    output = project_root / "outputs" / "story_card_short.mp4"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(b"not-a-real-mp4")
    (project_root / "evidence").mkdir(parents=True, exist_ok=True)
    _write(project_root / "evidence" / "evidence_manifest.json", {"records": []})
    return project_root


class DetectionTests(unittest.TestCase):
    def test_detects_both_kinds_and_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_news_job(root, "news_one")
            _make_project_manifest(root, "card_one")
            (root / "leftover_folder").mkdir()
            repo = ProjectRepository(root)

            self.assertEqual(repo.detect_kind("news_one"), PROJECT_KIND_NEWS_JOB)
            self.assertEqual(repo.detect_kind("card_one"), PROJECT_KIND_PROJECT_MANIFEST)
            self.assertEqual(repo.detect_kind("leftover_folder"), PROJECT_KIND_UNKNOWN)

    def test_missing_project_raises_a_typed_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ProjectNotFoundError):
                ProjectRepository(tmp).get("nope")

    def test_missing_root_lists_nothing(self) -> None:
        self.assertEqual(ProjectRepository(Path("no") / "such" / "root").list(), [])


class NewsJobReadingTests(unittest.TestCase):
    def test_news_job_exposes_stages_outputs_and_quality(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_news_job(root, "news_one")
            view = ProjectRepository(root).get("news_one")

            self.assertEqual(view.kind, PROJECT_KIND_NEWS_JOB)
            self.assertEqual(view.template_id, "fullscreen_voiceover_v1")
            self.assertEqual(view.channel_id, "nature_science_news_ru")
            self.assertEqual(view.quality_status, "passed")
            self.assertEqual(len(view.completed_stages), 12)
            self.assertEqual(view.blocking_stages, [])
            self.assertTrue(view.final_video.endswith("master_1080x1920.mp4"))
            self.assertIn("master_1080x1920", view.output_paths)
            self.assertTrue(any(path.endswith("assets_manifest.json") for path in view.evidence_paths))

    def test_declared_output_that_no_longer_exists_is_reported_not_claimed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project_root = _make_news_job(root, "news_one")
            Path(json.loads((project_root / "render" / "final_render_manifest.json").read_text(encoding="utf-8"))["output_path"]).unlink()
            view = ProjectRepository(root).get("news_one")

            self.assertEqual(view.final_video, "")
            self.assertTrue(view.warnings)

    def test_blocking_stages_are_surfaced(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project_root = _make_news_job(root, "news_one", status="needs_review")
            data = json.loads((project_root / "job.json").read_text(encoding="utf-8"))
            data["stages"]["voice"]["status"] = "needs_review"
            data["stages"]["final_render"]["status"] = "failed"
            data["stages"]["final_render"]["error"] = "quality_check_requires_review"
            data["stages"]["preview_render"]["status"] = "stale"
            _write(project_root / "job.json", data)
            view = ProjectRepository(root).get("news_one")

            self.assertEqual(
                sorted(view.blocking_stages),
                ["final_render", "preview_render", "voice"],
            )
            self.assertEqual(view.status, "needs_review")

    def test_blocked_stage_records_a_finished_timestamp(self) -> None:
        from src.news.project_store import NewsProjectStore

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_news_job(root, "news_one", status="in_progress", with_video=False)
            store = NewsProjectStore(root)
            job = store.load_job("news_one")

            store.update_stage(
                job,
                "voice",
                status="blocked",
                result_path=str(root / "news_one" / "voice_manifest.json"),
            )

            stored = store.load_job("news_one")
            self.assertEqual(stored.stages["voice"].status, "blocked")
            self.assertIsNotNone(stored.stages["voice"].finished_at)

    def test_unreadable_job_json_does_not_raise(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "broken").mkdir()
            (root / "broken" / "job.json").write_text("{ not json", encoding="utf-8")
            view = ProjectRepository(root).get("broken")

            self.assertEqual(view.kind, PROJECT_KIND_NEWS_JOB)
            self.assertTrue(view.warnings)


class ProjectManifestReadingTests(unittest.TestCase):
    def test_story_card_project_is_read_through_its_own_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_project_manifest(root, "card_one")
            view = ProjectRepository(root).get("card_one")

            self.assertEqual(view.kind, PROJECT_KIND_PROJECT_MANIFEST)
            self.assertEqual(view.template_id, "story_card_text_only_v1")
            self.assertEqual(view.title, "Карточка про сову")
            self.assertTrue(view.final_video.endswith("story_card_short.mp4"))
            self.assertTrue(view.evidence_paths)

    def test_project_manifest_projects_report_no_stages_rather_than_fake_ones(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_project_manifest(root, "card_one")
            self.assertEqual(ProjectRepository(root).get("card_one").stages, [])


class ListingTests(unittest.TestCase):
    def test_list_covers_both_systems_in_one_call(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_news_job(root, "news_one")
            _make_project_manifest(root, "card_one")
            kinds = {view.project_id: view.kind for view in ProjectRepository(root).list()}

            self.assertEqual(kinds, {"news_one": PROJECT_KIND_NEWS_JOB, "card_one": PROJECT_KIND_PROJECT_MANIFEST})

    def test_folders_without_a_manifest_are_hidden_unless_asked_for(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_news_job(root, "news_one")
            (root / "story_card_owl_test").mkdir()
            repo = ProjectRepository(root)

            self.assertEqual([view.project_id for view in repo.list()], ["news_one"])
            with_unknown = {view.project_id: view.kind for view in repo.list(include_unknown=True)}
            self.assertEqual(with_unknown["story_card_owl_test"], PROJECT_KIND_UNKNOWN)

    def test_view_serializes_to_json_safe_primitives(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_news_job(root, "news_one")
            payload = ProjectRepository(root).get("news_one").to_dict()
            json.dumps(payload, ensure_ascii=False)  # must not raise
            self.assertIn("completed_stages", payload)
            self.assertIn("blocking_stages", payload)


class NoWriteGuaranteeTests(unittest.TestCase):
    def test_reading_never_modifies_the_project_folder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_news_job(root, "news_one")
            _make_project_manifest(root, "card_one")
            before = {
                path.relative_to(root).as_posix(): path.stat().st_mtime_ns
                for path in sorted(root.rglob("*"))
                if path.is_file()
            }
            repo = ProjectRepository(root)
            repo.list(include_unknown=True)
            repo.get("news_one")
            repo.get("card_one")
            after = {
                path.relative_to(root).as_posix(): path.stat().st_mtime_ns
                for path in sorted(root.rglob("*"))
                if path.is_file()
            }
            self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
