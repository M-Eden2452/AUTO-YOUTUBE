from __future__ import annotations

import unittest
import wave


class PausePolicyTests(unittest.TestCase):
    def test_format_defaults_registered_for_all_known_formats(self) -> None:
        from src.audio.pause_policy import FORMAT_DEFAULTS

        self.assertIn("vertical_short", FORMAT_DEFAULTS)
        self.assertIn("longform", FORMAT_DEFAULTS)
        self.assertIn("horizontal_clip", FORMAT_DEFAULTS)

    def test_pause_policy_for_unknown_format_returns_generic_default(self) -> None:
        from src.audio.pause_policy import PausePolicy, pause_policy_for_format

        policy = pause_policy_for_format("unknown_format")
        self.assertIsInstance(policy, PausePolicy)

    def test_clamp_respects_min_and_max(self) -> None:
        from src.audio.pause_policy import PausePolicy

        policy = PausePolicy(min_pause_sec=0.1, max_pause_sec=1.0)
        self.assertEqual(policy.clamp(-5.0), 0.1)
        self.assertEqual(policy.clamp(5.0), 1.0)
        self.assertEqual(policy.clamp(0.5), 0.5)

    def test_silence_wav_bytes_has_correct_duration(self) -> None:
        import io

        from src.audio.pause_policy import silence_wav_bytes

        data = silence_wav_bytes(0.5, sample_rate=48000, channels=1)
        with wave.open(io.BytesIO(data), "rb") as wav:
            duration = wav.getnframes() / float(wav.getframerate())
        self.assertAlmostEqual(duration, 0.5, places=2)

    def test_write_silence_wav_creates_file(self) -> None:
        import tempfile
        from pathlib import Path

        from src.audio.pause_policy import write_silence_wav

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sub" / "silence.wav"
            write_silence_wav(path, 0.25, sample_rate=48000, channels=1)
            self.assertTrue(path.is_file())
            with wave.open(str(path), "rb") as wav:
                duration = wav.getnframes() / float(wav.getframerate())
            self.assertAlmostEqual(duration, 0.25, places=2)


if __name__ == "__main__":
    unittest.main()
