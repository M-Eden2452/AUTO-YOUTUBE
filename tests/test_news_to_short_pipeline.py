from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

import imageio_ffmpeg
from PIL import Image


class NewsToShortPipelineTests(unittest.TestCase):
    def test_dry_run_from_topic_saves_ab_artifacts_without_paid_tts(self) -> None:
        from src.news.pipeline import create_news_to_short_job, run_news_to_short_job

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            job = create_news_to_short_job(
                projects_root=root,
                channel_id="nature_science_news_ru",
                topic="Почему киты-матери переворачиваются брюхом вверх?",
                language="ru",
                now="2026-07-18T09:30:00+03:00",
            )
            result = run_news_to_short_job(projects_root=root, job_id=job.job_id, dry_run=True)
            project_root = root / job.job_id

            self.assertEqual(result.status, "dry_run_completed")
            self.assertTrue((project_root / "article" / "article.json").is_file())
            self.assertTrue((project_root / "research" / "claims.json").is_file())
            self.assertTrue((project_root / "localizations" / "ru" / "script" / "script.json").is_file())
            self.assertTrue((project_root / "localizations" / "ru" / "script" / "narration.txt").is_file())
            self.assertTrue((project_root / "master" / "master_visual_plan.json").is_file())
            self.assertTrue((project_root / "localizations" / "ru" / "visual" / "visual_plan.json").is_file())
            self.assertFalse((project_root / "localizations" / "ru" / "voice" / "voice_manifest.json").exists())

            claims = json.loads((project_root / "research" / "claims.json").read_text(encoding="utf-8"))
            script = json.loads((project_root / "localizations" / "ru" / "script" / "script.json").read_text(encoding="utf-8"))
            visual = json.loads((project_root / "localizations" / "ru" / "visual" / "visual_plan.json").read_text(encoding="utf-8"))

            self.assertGreaterEqual(len(claims["claims"]), 1)
            self.assertEqual(script["language"], "ru")
            self.assertTrue(script["narration_text"])
            self.assertEqual(visual["language"], "ru")
            self.assertGreaterEqual(len(visual["scenes"]), 1)

    def test_resume_continues_existing_job_without_recreating_input(self) -> None:
        from src.news.pipeline import create_news_to_short_job, run_news_to_short_job
        from src.news.project_store import NewsProjectStore

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            job = create_news_to_short_job(
                projects_root=root,
                channel_id="nature_science_news_ru",
                text="Короткий текст новости. Ученые сообщают о новом наблюдении.",
                language="ru",
                now="2026-07-18T09:30:00+03:00",
            )
            run_news_to_short_job(projects_root=root, job_id=job.job_id, until_stage="research", dry_run=True)

            store = NewsProjectStore(root)
            before = json.loads((root / job.job_id / "input" / "input.json").read_text(encoding="utf-8"))
            result = run_news_to_short_job(projects_root=root, job_id=job.job_id, resume=True, dry_run=True)
            after = json.loads((root / job.job_id / "input" / "input.json").read_text(encoding="utf-8"))

            self.assertEqual(before, after)
            self.assertEqual(result.status, "dry_run_completed")
            self.assertEqual(store.load_job(job.job_id).status, "dry_run_completed")

    def test_fake_provider_no_network_pipeline_reaches_final_render_with_local_paths(self) -> None:
        from src.audio.voice_workflow import import_manual_audio
        from src.news.pipeline import create_news_to_short_job, run_news_to_short_job
        from src.providers.fake_provider import FakeStockProvider

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image_fixture = root / "fixture.jpg"
            video_fixture = root / "fixture.mp4"
            Image.new("RGB", (1080, 1920), (18, 70, 120)).save(image_fixture)
            if not _write_tiny_video(video_fixture):
                self.skipTest("FFmpeg is unavailable for the render smoke test.")
            provider = FakeStockProvider(image_fixture=image_fixture, video_fixture=video_fixture)
            job = create_news_to_short_job(
                projects_root=root,
                channel_id="nature_science_news_ru",
                topic="Why whales swim in the ocean",
                language="ru",
                now="2026-07-18T09:30:00+03:00",
            )

            with patch("src.news.asset_manager.create_default_asset_providers", return_value=[provider]):
                run_news_to_short_job(projects_root=root, job_id=job.job_id, until_stage="asset_search")

            project = root / job.job_id
            manifest = json.loads((project / "assets" / "assets_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["schema_version"], 1)
            self.assertFalse(manifest["missing_scenes"])
            for scene in manifest["scenes"]:
                selected = scene["selected_asset"]
                self.assertTrue(Path(selected["path"]).is_file())
                self.assertEqual(selected["download_status"], "downloaded")
                self.assertEqual(selected["technical_validation"]["status"], "passed")
                self.assertEqual(len(selected["checksum_sha256"]), 64)

            audio = root / "manual.wav"
            with wave.open(str(audio), "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(48000)
                wav.writeframes(b"\x00\x00" * 48000 * 5)
            import_manual_audio(project_root=project, job_id=job.job_id, language="ru", audio_file=str(audio))

            run_news_to_short_job(projects_root=root, job_id=job.job_id, stage="subtitles")
            run_news_to_short_job(projects_root=root, job_id=job.job_id, stage="quality_check")
            quality = json.loads((project / "quality" / "quality_report.json").read_text(encoding="utf-8"))
            self.assertEqual(quality["status"], "passed")

            result = run_news_to_short_job(projects_root=root, job_id=job.job_id, stage="final_render")
            final_manifest = json.loads((project / "render" / "final_render_manifest.json").read_text(encoding="utf-8"))

            self.assertEqual(final_manifest["status"], "completed")
            self.assertTrue(Path(final_manifest["output_path"]).is_file())
            self.assertEqual(result.status, "completed")

    def test_research_stage_idempotency_normal_and_resume(self) -> None:
        from src.news.pipeline import create_news_to_short_job, run_news_to_short_job

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            job = create_news_to_short_job(
                projects_root=root,
                channel_id="nature_science_news_ru",
                topic="Исследование поведения дельфинов в открытом море",
                language="ru",
                now="2026-07-28T12:00:00+03:00",
            )

            # Normal run
            res1 = run_news_to_short_job(projects_root=root, job_id=job.job_id, until_stage="research", dry_run=True)
            self.assertIn("research", res1.completed_stages)
            claims_path = root / job.job_id / "research" / "claims.json"
            self.assertTrue(claims_path.is_file())

            # Repeated normal run without force_stage
            res2 = run_news_to_short_job(projects_root=root, job_id=job.job_id, until_stage="research", dry_run=True)
            self.assertNotIn("research", res2.completed_stages)

            # Resume run without force_stage
            res3 = run_news_to_short_job(projects_root=root, job_id=job.job_id, resume=True, until_stage="research", dry_run=True)
            self.assertNotIn("research", res3.completed_stages)

            # Force stage re-executes research stage
            res4 = run_news_to_short_job(projects_root=root, job_id=job.job_id, stage="research", force_stage=True, dry_run=True)
            self.assertIn("research", res4.completed_stages)

    def test_research_stage_idempotency_missing_and_invalid_output(self) -> None:
        from src.news.pipeline import create_news_to_short_job, run_news_to_short_job
        from src.news.project_store import NewsProjectStore

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            job = create_news_to_short_job(
                projects_root=root,
                channel_id="nature_science_news_ru",
                topic="Новые гипотезы в океанологии",
                language="ru",
                now="2026-07-28T12:00:00+03:00",
            )

            run_news_to_short_job(projects_root=root, job_id=job.job_id, until_stage="research", dry_run=True)
            claims_path = root / job.job_id / "research" / "claims.json"
            self.assertTrue(claims_path.is_file())

            store = NewsProjectStore(root)
            loaded_job = store.load_job(job.job_id)
            self.assertEqual(loaded_job.stages["research"].status, "completed")

            # Missing output: remove claims.json
            claims_path.unlink()
            res_missing = run_news_to_short_job(projects_root=root, job_id=job.job_id, until_stage="research", dry_run=True)
            self.assertIn("research", res_missing.completed_stages)
            self.assertTrue(claims_path.is_file())

            # Invalid output: overwrite claims.json with empty JSON dict {} missing 'claims' key
            store.write_json(claims_path, {})
            res_invalid = run_news_to_short_job(projects_root=root, job_id=job.job_id, until_stage="research", dry_run=True)
            self.assertIn("research", res_invalid.completed_stages)
            data = store.read_json(claims_path)
            self.assertIn("claims", data)
            self.assertIsInstance(data["claims"], list)

    def test_script_stage_idempotency_normal_resume_and_force(self) -> None:
        from src.news.pipeline import create_news_to_short_job, run_news_to_short_job

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            job = create_news_to_short_job(
                projects_root=root,
                channel_id="nature_science_news_ru",
                topic="Как морские птицы ориентируются над открытым океаном",
                language="ru",
                now="2026-07-29T12:00:00+03:00",
            )

            first = run_news_to_short_job(
                projects_root=root,
                job_id=job.job_id,
                until_stage="script",
                dry_run=True,
            )
            self.assertIn("script", first.completed_stages)

            repeated = run_news_to_short_job(
                projects_root=root,
                job_id=job.job_id,
                until_stage="script",
                dry_run=True,
            )
            self.assertNotIn("script", repeated.completed_stages)

            resumed = run_news_to_short_job(
                projects_root=root,
                job_id=job.job_id,
                resume=True,
                until_stage="script",
                dry_run=True,
            )
            self.assertNotIn("script", resumed.completed_stages)

            forced = run_news_to_short_job(
                projects_root=root,
                job_id=job.job_id,
                stage="script",
                force_stage=True,
                dry_run=True,
            )
            self.assertIn("script", forced.completed_stages)

    def test_script_stage_idempotency_missing_and_invalid_output(self) -> None:
        from src.news.pipeline import create_news_to_short_job, run_news_to_short_job
        from src.news.project_store import NewsProjectStore

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            job = create_news_to_short_job(
                projects_root=root,
                channel_id="nature_science_news_ru",
                topic="Наблюдения за миграцией морских черепах",
                language="ru",
                now="2026-07-29T12:00:00+03:00",
            )

            run_news_to_short_job(
                projects_root=root,
                job_id=job.job_id,
                until_stage="script",
                dry_run=True,
            )
            script_path = (
                root
                / job.job_id
                / "localizations"
                / "ru"
                / "script"
                / "script.json"
            )
            self.assertTrue(script_path.is_file())

            store = NewsProjectStore(root)
            loaded_job = store.load_job(job.job_id)
            self.assertEqual(loaded_job.stages["script"].status, "completed")

            script_path.unlink()
            missing = run_news_to_short_job(
                projects_root=root,
                job_id=job.job_id,
                until_stage="script",
                dry_run=True,
            )
            self.assertIn("script", missing.completed_stages)
            self.assertTrue(script_path.is_file())

            store.write_json(script_path, {})
            invalid = run_news_to_short_job(
                projects_root=root,
                job_id=job.job_id,
                resume=True,
                until_stage="script",
                dry_run=True,
            )
            self.assertIn("script", invalid.completed_stages)
            data = store.read_json(script_path)
            self.assertTrue(data["narration_text"].strip())
            self.assertTrue(data["scenes"])



def _write_tiny_video(path: Path) -> bool:
    command = [
        imageio_ffmpeg.get_ffmpeg_exe(),
        "-y",
        "-v",
        "error",
        "-f",
        "lavfi",
        "-i",
        "color=c=0x224466:s=1080x1920:d=1:r=30",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        str(path),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    return result.returncode == 0 and path.exists()


if __name__ == "__main__":
    unittest.main()
