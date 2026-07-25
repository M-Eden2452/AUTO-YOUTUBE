from __future__ import annotations

import json
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch
from PIL import Image


class NewsToShortRendererTests(unittest.TestCase):
    def test_final_render_creates_vertical_mp4_when_manual_voice_exists(self) -> None:
        from src.audio.voice_workflow import import_manual_audio
        from src.news.pipeline import create_news_to_short_job, run_news_to_short_job

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            images = []
            for index in range(12):
                image = root / f"forest_{index:03d}.jpg"
                Image.new("RGB", (1080, 1920), (22 + index, 70, 55)).save(image)
                images.append(
                    {
                        "path": str(image),
                        "rights_declaration": {
                            "confirmation_status": "approved",
                            "owner_approval_status": "approved",
                            "license_name": "user_owned",
                            "rights_status": "user_owned",
                        },
                    }
                )
            job = create_news_to_short_job(
                projects_root=root,
                channel_id="nature_science_news_ru",
                topic="Почему леса охлаждают планету?",
                assets=images,
                language="ru",
                now="2026-07-18T11:00:00+03:00",
            )
            with patch("src.news.asset_manager.create_default_asset_providers", return_value=[]):
                run_news_to_short_job(projects_root=root, job_id=job.job_id, until_stage="voice")
            audio = root / "manual.wav"
            with wave.open(str(audio), "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(48000)
                wav.writeframes(b"\x00\x00" * 48000 * 3)
            import_manual_audio(project_root=root / job.job_id, job_id=job.job_id, language="ru", audio_file=str(audio))

            run_news_to_short_job(projects_root=root, job_id=job.job_id, stage="subtitles")
            from src.news.project_store import NewsProjectStore
            store = NewsProjectStore(root)
            project = root / job.job_id
            store.write_json(project / "quality" / "quality_report.json", {"status": "passed", "errors": [], "warnings": [], "checks": []})
            result = run_news_to_short_job(projects_root=root, job_id=job.job_id, stage="final_render")
            final_manifest = json.loads((project / "render" / "final_render_manifest.json").read_text(encoding="utf-8"))

            self.assertEqual(final_manifest["status"], "completed")
            self.assertTrue(Path(final_manifest["output_path"]).is_file())
            self.assertEqual(result.status, "completed")
            self.assertTrue((project / "localizations" / "ru" / "output" / "youtube_shorts.mp4").is_file())

    def test_renderer_does_not_draw_app_branding(self) -> None:
        source = Path("src/news/final_renderer.py").read_text(encoding="utf-8")

        self.assertNotIn('"AI-YouTube"', source)
        self.assertNotIn("footer =", source)


if __name__ == "__main__":
    unittest.main()
