from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class NewsToShortDeliveryTests(unittest.TestCase):
    def test_subtitles_quality_preview_and_export_are_created_after_asset_search(self) -> None:
        from src.news.pipeline import create_news_to_short_job, run_news_to_short_job

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            job = create_news_to_short_job(
                projects_root=root,
                channel_id="nature_science_news_ru",
                topic="Почему киты поют в океане?",
                language="ru",
                now="2026-07-18T10:00:00+03:00",
            )
            with patch("src.news.asset_manager.create_default_asset_providers", return_value=[]):
                result = run_news_to_short_job(projects_root=root, job_id=job.job_id, until_stage="export", dry_run=False)
            project = root / job.job_id
            loc = project / "localizations" / "ru"

            self.assertEqual(result.status, "needs_review")
            self.assertTrue((loc / "subtitles" / "subtitles.srt").is_file())
            self.assertTrue((loc / "subtitles" / "subtitles.ass").is_file())
            self.assertFalse((project / "preview" / "preview.mp4").exists())
            self.assertTrue((project / "preview" / "preview_manifest.json").is_file())
            self.assertTrue((project / "quality" / "quality_report.json").is_file())
            self.assertTrue((loc / "output" / "project_manifest.json").is_file())
            self.assertTrue((loc / "output" / "sources.json").is_file())
            self.assertTrue((loc / "output" / "description.txt").is_file())

            quality = json.loads((project / "quality" / "quality_report.json").read_text(encoding="utf-8"))
            final_render = json.loads((project / "render" / "final_render_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(quality["status"], "failed")
            self.assertEqual(final_render["status"], "blocked")
            self.assertTrue(any("Voice stage requires" in item["message"] for item in quality["warnings"]))
            quality_messages = [item["message"] for item in quality["warnings"] + quality["errors"]]
            self.assertTrue(
                any("scene(s) still need approved assets" in message for message in quality_messages)
                or any("At least 8 real downloaded videos are required" in message for message in quality_messages)
            )

    def test_voice_stage_does_not_call_paid_tts_without_manual_approval(self) -> None:
        from src.news.pipeline import create_news_to_short_job, run_news_to_short_job

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            job = create_news_to_short_job(
                projects_root=root,
                channel_id="nature_science_news_ru",
                text="Короткий сценарий для проверки безопасной озвучки.",
                language="ru",
                now="2026-07-18T10:00:00+03:00",
            )
            with patch("src.news.asset_manager.create_default_asset_providers", return_value=[]):
                run_news_to_short_job(projects_root=root, job_id=job.job_id, until_stage="voice", dry_run=False)

            manifest_path = root / job.job_id / "localizations" / "ru" / "voice" / "voice_manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

            self.assertEqual(manifest["status"], "provider_selection_required")
            self.assertEqual(manifest["paid_provider"], "elevenlabs")
            self.assertTrue(manifest["paid_tts_requires_approval"])
            self.assertFalse(manifest["paid_call_performed"])

    def test_final_render_keeps_job_in_review_when_voice_is_not_completed(self) -> None:
        from src.news.models import INPUT_MODE_TOPIC, NewsJob
        from src.news.pipeline import run_news_to_short_job
        from src.news.project_store import NewsProjectStore

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            job = NewsJob.create(
                channel_id="nature_science_news_ru",
                input_mode=INPUT_MODE_TOPIC,
                topic="Тест",
                language="ru",
                now="2026-07-18T10:00:00+03:00",
            )
            store = NewsProjectStore(root)
            store.create_project(job)
            project = root / job.job_id
            store.write_json(project / "quality" / "quality_report.json", {"status": "needs_review", "errors": [], "warnings": [{"message": "Voice stage requires draft audio or approved final voice."}], "checks": []})

            result = run_news_to_short_job(projects_root=root, job_id=job.job_id, stage="final_render")

            manifest = json.loads((project / "render" / "final_render_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["status"], "blocked")
            self.assertEqual(result.status, "needs_review")


if __name__ == "__main__":
    unittest.main()
