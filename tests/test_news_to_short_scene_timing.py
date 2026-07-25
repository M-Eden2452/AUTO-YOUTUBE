"""The voice stage must write real narration timings back onto script.json.

Covers the defect found in the 2026-07-25 audit: actual_duration_sec was read by
final_renderer/subtitles but written by nobody, so the visual timeline followed the
script's estimate while the audio followed the real narration.

No network (tests.network_guard is installed package-wide), no provider, no paid
call: build_or_generate_voice_manifest is patched with a canned schema-v2 manifest.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


def _completed_voice_manifest(scene_ids: list[str], durations: list[float], pause: float) -> dict:
    return {
        "schema_version": 2,
        "status": "completed",
        "voice_stage_status": "completed",
        "format_id": "vertical_short",
        "audio_path": "narration.wav",
        "scenes": [
            {
                "scene_id": scene_id,
                "scene_index": index,
                "duration_seconds": duration,
                "generation_status": "completed",
            }
            for index, (scene_id, duration) in enumerate(zip(scene_ids, durations, strict=True))
        ],
        "narration": {
            "output_path": "narration.wav",
            "duration_sec": sum(durations) + pause * (len(durations) - 1),
            "pause_total_sec": pause * (len(durations) - 1),
        },
    }


class VoiceStageSceneTimingTests(unittest.TestCase):
    def _prepare_job(self, root: Path):
        from src.news.pipeline import create_news_to_short_job, run_news_to_short_job

        job = create_news_to_short_job(
            projects_root=root,
            channel_id="nature_science_news_ru",
            text="Короткий текст новости. Ученые сообщают о новом наблюдении в океане.",
            language="ru",
            now="2026-07-25T09:30:00+03:00",
        )
        run_news_to_short_job(projects_root=root, job_id=job.job_id, until_stage="script", dry_run=True)
        return job

    def test_voice_stage_writes_actual_durations_onto_the_script(self) -> None:
        from src.news.pipeline import run_news_to_short_job

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            job = self._prepare_job(root)
            script_path = root / job.job_id / "localizations" / "ru" / "script" / "script.json"
            planned = json.loads(script_path.read_text(encoding="utf-8"))
            scene_ids = [scene["scene_id"] for scene in planned["scenes"]]
            # Deliberately unlike the plan, exactly as real TTS output was.
            spoken = [round(3.0 + index * 1.7, 2) for index in range(len(scene_ids))]
            manifest = _completed_voice_manifest(scene_ids, spoken, pause=0.35)

            with patch("src.news.pipeline.build_or_generate_voice_manifest", return_value=manifest):
                run_news_to_short_job(projects_root=root, job_id=job.job_id, stage="voice")

            updated = json.loads(script_path.read_text(encoding="utf-8"))
            self.assertEqual(updated["timing_source"], "voice_manifest")
            for index, scene in enumerate(updated["scenes"]):
                self.assertIn("actual_duration_sec", scene)
                self.assertAlmostEqual(scene["speech_duration_sec"], spoken[index], places=2)
                # the plan is preserved, not overwritten
                self.assertEqual(scene["target_duration_sec"], planned["scenes"][index]["target_duration_sec"])

            expected_total = sum(spoken) + 0.35 * (len(spoken) - 1)
            self.assertAlmostEqual(updated["actual_duration_sec"], expected_total, places=2)

            timeline_path = root / job.job_id / "localizations" / "ru" / "voice" / "scene_timeline.json"
            self.assertTrue(timeline_path.is_file())
            timeline = json.loads(timeline_path.read_text(encoding="utf-8"))
            self.assertEqual(timeline["scene_count"], len(scene_ids))

    def test_visual_timeline_now_matches_the_narration(self) -> None:
        """The concrete regression: _script_duration used to fall ~8s short of narration."""
        from src.news.final_renderer import _script_duration
        from src.news.pipeline import run_news_to_short_job

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            job = self._prepare_job(root)
            script_path = root / job.job_id / "localizations" / "ru" / "script" / "script.json"
            planned = json.loads(script_path.read_text(encoding="utf-8"))
            scene_ids = [scene["scene_id"] for scene in planned["scenes"]]
            spoken = [round(4.0 + index * 2.1, 2) for index in range(len(scene_ids))]
            manifest = _completed_voice_manifest(scene_ids, spoken, pause=0.35)

            self.assertLess(_script_duration(planned), manifest["narration"]["duration_sec"])

            with patch("src.news.pipeline.build_or_generate_voice_manifest", return_value=manifest):
                run_news_to_short_job(projects_root=root, job_id=job.job_id, stage="voice")

            updated = json.loads(script_path.read_text(encoding="utf-8"))
            self.assertAlmostEqual(
                _script_duration(updated), manifest["narration"]["duration_sec"], delta=0.05
            )

    def test_subtitles_follow_the_real_timing(self) -> None:
        from src.news.pipeline import run_news_to_short_job
        from src.news.subtitles import build_subtitles

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            job = self._prepare_job(root)
            script_path = root / job.job_id / "localizations" / "ru" / "script" / "script.json"
            planned = json.loads(script_path.read_text(encoding="utf-8"))
            scene_ids = [scene["scene_id"] for scene in planned["scenes"]]
            spoken = [round(5.0 + index * 1.3, 2) for index in range(len(scene_ids))]
            manifest = _completed_voice_manifest(scene_ids, spoken, pause=0.35)

            with patch("src.news.pipeline.build_or_generate_voice_manifest", return_value=manifest):
                run_news_to_short_job(projects_root=root, job_id=job.job_id, stage="voice")

            updated = json.loads(script_path.read_text(encoding="utf-8"))
            result = build_subtitles(updated, root / "subs")
            last_end = result["segments"][-1]["end"]
            self.assertAlmostEqual(last_end, manifest["narration"]["duration_sec"], delta=0.05)

    def test_unapproved_stub_manifest_leaves_the_script_untouched(self) -> None:
        """No narration -> no timings written, existing behaviour preserved exactly."""
        from src.news.pipeline import run_news_to_short_job

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            job = self._prepare_job(root)
            script_path = root / job.job_id / "localizations" / "ru" / "script" / "script.json"
            before = script_path.read_text(encoding="utf-8")
            stub = {
                "status": "provider_selection_required",
                "voice_stage_status": "provider_selection_required",
                "audio_path": "",
                "scenes": [],
            }

            with patch("src.news.pipeline.build_or_generate_voice_manifest", return_value=stub):
                run_news_to_short_job(projects_root=root, job_id=job.job_id, stage="voice")

            self.assertEqual(script_path.read_text(encoding="utf-8"), before)
            self.assertFalse(
                (root / job.job_id / "localizations" / "ru" / "voice" / "scene_timeline.json").exists()
            )


if __name__ == "__main__":
    unittest.main()
