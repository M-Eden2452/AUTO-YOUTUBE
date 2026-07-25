from __future__ import annotations

import json
import math
import re
import struct
import subprocess
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

from PIL import Image


def _write_tone_wav(path: Path, seconds: float, frequency: int = 220, amplitude: float = 0.8) -> Path:
    """A short audible tone - silence would make a "is the bed present?" check vacuous."""
    rate = 48000
    frames = bytearray()
    for index in range(int(rate * seconds)):
        value = int(amplitude * 32767 * math.sin(2 * math.pi * frequency * index / rate))
        frames += struct.pack("<h", value)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(bytes(frames))
    return path


def _audio_stream_duration_sec(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return float((result.stdout or "0").strip() or 0.0)


def _mean_volume_db(path: Path, start: float, length: float) -> float:
    """Mean level of one window, in dB. -inf (returned as -120.0) means silence."""
    import imageio_ffmpeg

    result = subprocess.run(
        [imageio_ffmpeg.get_ffmpeg_exe(), "-v", "info", "-ss", f"{start:.3f}", "-t", f"{length:.3f}",
         "-i", str(path), "-af", "volumedetect", "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    match = re.search(r"mean_volume:\s*(-?[\d.]+|-inf) dB", result.stderr or "")
    if not match:
        return -120.0
    return -120.0 if match.group(1) == "-inf" else float(match.group(1))


class FinalRendererEndTailTests(unittest.TestCase):
    def test_final_render_trims_to_narration_plus_tail_not_visual_timeline(self) -> None:
        from src.assets.frame_sampling import ffprobe_media_info
        from src.audio.end_tail_policy import DEFAULT_TAIL_SEC
        from src.audio.voice_workflow import import_manual_audio
        from src.news.pipeline import create_news_to_short_job, run_news_to_short_job
        from src.news.project_store import NewsProjectStore

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

            manual_duration_sec = 3.0
            audio = root / "manual.wav"
            with wave.open(str(audio), "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(48000)
                wav.writeframes(b"\x00\x00" * int(48000 * manual_duration_sec))
            import_manual_audio(project_root=root / job.job_id, job_id=job.job_id, language="ru", audio_file=str(audio))

            run_news_to_short_job(projects_root=root, job_id=job.job_id, stage="subtitles")
            store = NewsProjectStore(root)
            project = root / job.job_id
            store.write_json(
                project / "quality" / "quality_report.json",
                {"status": "passed", "errors": [], "warnings": [], "checks": []},
            )
            run_news_to_short_job(projects_root=root, job_id=job.job_id, stage="final_render")
            final_manifest = json.loads((project / "render" / "final_render_manifest.json").read_text(encoding="utf-8"))

            self.assertEqual(final_manifest["status"], "completed")
            self.assertEqual(final_manifest["end_policy_id"], "narration_plus_tail")
            expected_target = manual_duration_sec + DEFAULT_TAIL_SEC
            self.assertAlmostEqual(final_manifest["target_duration_sec"], expected_target, places=2)
            # The pre-fix renderer left the video at the full visual-plan length
            # (tens of seconds); confirm it now really is short, not just reported so.
            self.assertLess(final_manifest["target_duration_sec"], final_manifest["visual_duration_sec"])

            info = ffprobe_media_info(Path(final_manifest["output_path"]))
            self.assertLess(abs(float(info["duration_sec"]) - expected_target), 0.3)


class MusicCoversEndTailTests(unittest.TestCase):
    """Regression for W1: with music, the audio track must not stop at the narration.

    Found by the V1 live-render validation: `amix=duration=first` truncated the mix
    to the narration, so a 60.233 s video carried 59.475 s of audio and the end tail
    was completely silent - even though the bed itself was already looped and
    trimmed to the full length. Runs a real render (no network, no TTS, no paid API).
    """

    def test_audio_and_music_reach_the_end_of_the_video(self) -> None:
        from src.audio.end_tail_policy import DEFAULT_TAIL_SEC
        from src.audio.music_manifest import prepare_project_music
        from src.audio.voice_workflow import import_manual_audio
        from src.news.pipeline import create_news_to_short_job, run_news_to_short_job
        from src.news.project_store import NewsProjectStore

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            images = []
            for index in range(6):
                image = root / f"scene_{index:03d}.jpg"
                Image.new("RGB", (1080, 1920), (30 + index * 7, 60, 90)).save(image)
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

            # Narration deliberately shorter than the output: that gap is the tail.
            narration_sec = 3.0
            narration = _write_tone_wav(root / "narration.wav", narration_sec, frequency=440)
            import_manual_audio(
                project_root=root / job.job_id, job_id=job.job_id, language="ru", audio_file=str(narration)
            )
            # 1 s bed under a 3.75 s output also proves the loop still works.
            prepare_project_music(root / job.job_id, _write_tone_wav(root / "bed.wav", 1.0), volume=0.5)

            run_news_to_short_job(projects_root=root, job_id=job.job_id, stage="subtitles")
            store = NewsProjectStore(root)
            project = root / job.job_id
            store.write_json(
                project / "quality" / "quality_report.json",
                {"status": "passed", "errors": [], "warnings": [], "checks": []},
            )
            run_news_to_short_job(projects_root=root, job_id=job.job_id, stage="final_render")
            manifest = json.loads((project / "render" / "final_render_manifest.json").read_text(encoding="utf-8"))

            self.assertEqual(manifest["status"], "completed")
            self.assertTrue(manifest["music_path"], "music manifest was not picked up by the renderer")
            expected_target = narration_sec + DEFAULT_TAIL_SEC
            self.assertAlmostEqual(manifest["target_duration_sec"], expected_target, places=2)

            output = Path(manifest["output_path"])
            audio_duration = _audio_stream_duration_sec(output)
            # Before the fix this was the narration length (3.0), leaving 0.75 s silent.
            self.assertGreater(
                audio_duration,
                narration_sec + DEFAULT_TAIL_SEC / 2,
                f"audio stream stops at {audio_duration:.3f}s, before the {expected_target:.3f}s output ends",
            )
            self.assertLess(abs(audio_duration - expected_target), 0.3)

            # ...and the tail carries the bed rather than silence.
            tail = _mean_volume_db(output, narration_sec + 0.15, 0.5)
            self.assertGreater(tail, -60.0, f"end tail is silent (mean {tail:.1f} dB) - music does not reach it")


if __name__ == "__main__":
    unittest.main()
