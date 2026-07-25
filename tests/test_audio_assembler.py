from __future__ import annotations

import tempfile
import unittest
import wave
from pathlib import Path


def _write_wav(path: Path, seconds: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(48000)
        wav.writeframes(b"\x00\x00" * int(48000 * seconds))


class AudioAssemblerTests(unittest.TestCase):
    def test_single_scene_no_pauses(self) -> None:
        from src.audio.audio_assembler import assemble_narration

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            scene = tmp / "scene_001.wav"
            _write_wav(scene, 1.0)
            out = tmp / "narration.wav"
            result = assemble_narration([scene], [], target_sample_rate=48000, target_channels=1, output_path=out)
            self.assertTrue(out.is_file())
            self.assertAlmostEqual(result.duration_sec, 1.0, delta=0.05)
            self.assertEqual(result.scene_count, 1)

    def test_concat_order_and_pause_duration(self) -> None:
        from src.audio.audio_assembler import assemble_narration

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            scenes = [tmp / f"scene_{i:03d}.wav" for i in range(1, 4)]
            for scene in scenes:
                _write_wav(scene, 1.0)
            out = tmp / "narration.wav"
            result = assemble_narration(scenes, [0.5, 0.25], target_sample_rate=48000, target_channels=1, output_path=out)
            self.assertAlmostEqual(result.duration_sec, 3.75, delta=0.05)
            self.assertAlmostEqual(result.pause_total_sec, 0.75, delta=0.01)

    def test_output_is_48khz_and_checksum_present(self) -> None:
        from src.assets.frame_sampling import ffprobe_media_info
        from src.audio.audio_assembler import assemble_narration

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            scene = tmp / "scene_001.wav"
            _write_wav(scene, 0.5)
            out = tmp / "narration.wav"
            result = assemble_narration([scene], [], target_sample_rate=48000, target_channels=1, output_path=out)
            self.assertEqual(result.sample_rate, 48000)
            self.assertTrue(result.checksum_sha256)
            info = ffprobe_media_info(out)
            self.assertEqual(info["status"], "passed")

    def test_no_scenes_raises(self) -> None:
        from src.audio.audio_assembler import assemble_narration

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "narration.wav"
            with self.assertRaises(ValueError):
                assemble_narration([], [], output_path=out)

    def test_never_leaves_completed_status_on_ffmpeg_failure(self) -> None:
        from src.audio.audio_assembler import assemble_narration

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            bad_scene = tmp / "scene_001.wav"
            bad_scene.write_bytes(b"not-real-audio")
            out = tmp / "narration.wav"
            with self.assertRaises(RuntimeError):
                assemble_narration([bad_scene], [], output_path=out)
            self.assertFalse(out.exists(), "a failed assembly must not leave any file at the final path")
            leftovers = list(tmp.glob(".*"))
            self.assertEqual(leftovers, [], "temp/partial files must be cleaned up on failure")

    def test_post_processing_disabled_by_default(self) -> None:
        from src.audio.audio_assembler import PostProcessingConfig

        config = PostProcessingConfig()
        self.assertFalse(config.enabled)

    def test_apply_compression_is_explicit_not_implemented(self) -> None:
        from src.audio.audio_assembler import apply_compression

        with self.assertRaises(NotImplementedError):
            apply_compression()


if __name__ == "__main__":
    unittest.main()
