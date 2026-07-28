from __future__ import annotations

import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch


class NewsToShortModelTests(unittest.TestCase):
    def test_news_job_schema_version_is_additive_for_legacy_manifests(self) -> None:
        from src.news.models import NEWS_JOB_SCHEMA_VERSION, NewsJob

        legacy_payload = {
            "job_id": "legacy_news_job",
            "mode": "news_to_short",
            "channel_id": "legacy_channel",
            "input_mode": "topic",
        }

        restored = NewsJob.from_dict(legacy_payload)

        self.assertEqual(restored.schema_version, NEWS_JOB_SCHEMA_VERSION)
        self.assertEqual(restored.to_dict()["schema_version"], NEWS_JOB_SCHEMA_VERSION)

    def test_job_model_defaults_include_localization_and_stage_order(self) -> None:
        from src.news.models import (
            INPUT_MODE_TOPIC,
            NEWS_JOB_SCHEMA_VERSION,
            NEWS_TO_SHORT_STAGES,
            NewsJob,
        )

        job = NewsJob.create(
            channel_id="nature_science_news_ru",
            input_mode=INPUT_MODE_TOPIC,
            topic="Почему киты поют?",
            language="ru",
            now="2026-07-18T09:30:00+03:00",
        )

        self.assertEqual(job.mode, "news_to_short")
        self.assertEqual(job.schema_version, NEWS_JOB_SCHEMA_VERSION)
        self.assertEqual(job.to_dict()["schema_version"], NEWS_JOB_SCHEMA_VERSION)
        self.assertEqual(job.language, "ru")
        self.assertEqual(job.target_duration_sec, 55)
        self.assertEqual(job.resolution["width"], 1080)
        self.assertEqual(job.localizations["ru"].language, "ru")
        self.assertIn("en", job.localizations)
        self.assertIn("es", job.localizations)
        self.assertEqual(NEWS_TO_SHORT_STAGES[:4], ["input", "article_ingestion", "research", "script"])

    def test_project_store_creates_master_and_language_boundaries(self) -> None:
        from src.news.models import INPUT_MODE_TOPIC, NewsJob
        from src.news.project_store import NewsProjectStore

        with tempfile.TemporaryDirectory() as tmp:
            store = NewsProjectStore(Path(tmp))
            job = NewsJob.create(
                channel_id="nature_science_news_ru",
                input_mode=INPUT_MODE_TOPIC,
                topic="Тестовая научная новость",
                language="ru",
                now="2026-07-18T09:30:00+03:00",
            )
            project = store.create_project(job)

            self.assertTrue((project.root / "research").is_dir())
            self.assertTrue((project.root / "assets").is_dir())
            self.assertTrue((project.root / "master" / "sources.json").is_file())
            for language in ("ru", "en", "es"):
                root = project.root / "localizations" / language
                self.assertTrue((root / "script").is_dir())
                self.assertTrue((root / "voice").is_dir())
                self.assertTrue((root / "subtitles").is_dir())
                self.assertTrue((root / "output").is_dir())

            loaded = store.load_job(job.job_id)
            self.assertEqual(loaded.job_id, job.job_id)
            self.assertEqual(loaded.current_stage, "input")

    def test_project_store_writes_json_atomically_without_changing_format(self) -> None:
        from src.news.project_store import NewsProjectStore
        from src.project_foundation import storage

        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "nested" / "manifest.json"
            data = {"title": "Почему киты поют?", "count": 2}
            replace = storage.os.replace

            with patch.object(storage.os, "replace", wraps=replace) as replace_spy:
                NewsProjectStore.write_json(target, data)

            self.assertEqual(
                target.read_text(encoding="utf-8"),
                '{\n  "title": "Почему киты поют?",\n  "count": 2\n}\n',
            )
            replace_spy.assert_called_once()
            self.assertEqual(replace_spy.call_args.args[1], target)
            self.assertEqual(list(target.parent.glob(f".{target.name}.*.tmp")), [])

    def test_project_store_rejects_write_while_project_lock_is_active(self) -> None:
        from src.news.project_store import NewsProjectStore
        from src.project_foundation.storage import ProjectLockError, project_lock

        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "projects" / "locked_news_job"
            project_root.mkdir(parents=True)
            (project_root / "job.json").write_text('{"job_id": "locked_news_job"}\n', encoding="utf-8")
            target = project_root / "assets" / "assets_manifest.json"
            store = NewsProjectStore(Path(tmp) / "projects")

            with project_lock(project_root):
                with self.assertRaisesRegex(ProjectLockError, "locked_news_job"):
                    store.write_json(target, {"job_id": "locked_news_job"})
                self.assertFalse(target.exists())

            store.write_json(target, {"job_id": "locked_news_job"})
            self.assertTrue(target.is_file())

    def test_project_store_reclaims_lock_only_after_stale_threshold(self) -> None:
        from src.news.project_store import NewsProjectStore
        from src.project_foundation.storage import (
            PROJECT_LOCK_FILENAME,
            PROJECT_LOCK_STALE_AFTER_SECONDS,
        )

        with tempfile.TemporaryDirectory() as tmp:
            projects_root = Path(tmp) / "projects"
            project_root = projects_root / "stale_news_job"
            project_root.mkdir(parents=True)
            lock_path = project_root / PROJECT_LOCK_FILENAME
            lock_path.write_text('{"token": "abandoned"}\n', encoding="utf-8")
            stale_mtime = time.time() - PROJECT_LOCK_STALE_AFTER_SECONDS - 1
            os.utime(lock_path, (stale_mtime, stale_mtime))

            NewsProjectStore(projects_root).write_json(
                project_root / "job.json",
                {"job_id": "stale_news_job"},
            )

            self.assertFalse(lock_path.exists())
            self.assertEqual(
                (project_root / "job.json").read_text(encoding="utf-8"),
                '{\n  "job_id": "stale_news_job"\n}\n',
            )
            self.assertEqual(list(project_root.glob(".job.json.*.tmp")), [])

    def test_rights_status_blocks_reference_only_assets(self) -> None:
        from src.news.models import AssetRights, RIGHTS_REFERENCE_ONLY, RIGHTS_USER_OWNED

        reference = AssetRights(asset_id="asset_001", rights_status=RIGHTS_REFERENCE_ONLY)
        owned = AssetRights(asset_id="asset_002", rights_status=RIGHTS_USER_OWNED)

        self.assertFalse(reference.allowed_for_render)
        self.assertTrue(owned.allowed_for_render)


if __name__ == "__main__":
    unittest.main()
