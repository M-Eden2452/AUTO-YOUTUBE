from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.tts_providers.moss_tts_provider import DEFAULT_MOSS_TTS_TEST_TEXT, MossTtsProviderError, synthesize_text


class MossTtsProviderTests(unittest.TestCase):
    def test_synthesize_text_runs_moss_cli_from_dedicated_venv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            moss_path = root / "MOSS_TTS_Nano"
            python_exe = moss_path / ".venv" / "Scripts" / "python.exe"
            python_exe.parent.mkdir(parents=True)
            python_exe.write_text("", encoding="utf-8")
            (moss_path / "infer.py").write_text("", encoding="utf-8")
            (moss_path / "requirements.txt").write_text("", encoding="utf-8")
            output_path = root / "out" / "voice.wav"

            def fake_run(command, **kwargs):
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(b"RIFFfake-wave")
                return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")

            with patch("src.tts_providers.moss_tts_provider.subprocess.run", side_effect=fake_run) as run:
                result = synthesize_text(
                    "\u041f\u0440\u0438\u0432\u0435\u0442",
                    output_path,
                    {
                        "moss_tts_path": str(moss_path),
                        "max_new_frames": 64,
                        "execution_provider": "cpu",
                    },
                )

            self.assertEqual(result, output_path)
            command = run.call_args.args[0]
            self.assertEqual(Path(command[0]), python_exe)
            self.assertIn("moss_tts_nano", command)
            self.assertIn("--backend", command)
            self.assertIn("onnx", command)
            self.assertIn("--text", command)
            self.assertIn("\u041f\u0440\u0438\u0432\u0435\u0442", command)
            self.assertIn("--output-audio-path", command)
            self.assertIn(str(output_path), command)
            self.assertEqual(run.call_args.kwargs["cwd"], moss_path)

    def test_synthesize_text_raises_clear_error_when_cli_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            moss_path = root / "MOSS_TTS_Nano"
            python_exe = moss_path / ".venv" / "Scripts" / "python.exe"
            python_exe.parent.mkdir(parents=True)
            python_exe.write_text("", encoding="utf-8")
            (moss_path / "infer.py").write_text("", encoding="utf-8")
            (moss_path / "requirements.txt").write_text("", encoding="utf-8")

            completed = subprocess.CompletedProcess(["python"], 2, stdout="", stderr="bad model")
            with patch("src.tts_providers.moss_tts_provider.subprocess.run", return_value=completed):
                with self.assertRaisesRegex(MossTtsProviderError, "bad model"):
                    synthesize_text("\u041f\u0440\u0438\u0432\u0435\u0442", root / "voice.wav", {"moss_tts_path": str(moss_path)})

    def test_prompt_audio_enables_voice_clone_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            moss_path = root / "MOSS_TTS_Nano"
            python_exe = moss_path / ".venv" / "Scripts" / "python.exe"
            prompt = root / "sample.wav"
            python_exe.parent.mkdir(parents=True)
            python_exe.write_text("", encoding="utf-8")
            prompt.write_bytes(b"RIFF")
            (moss_path / "infer.py").write_text("", encoding="utf-8")
            (moss_path / "requirements.txt").write_text("", encoding="utf-8")
            output_path = root / "voice.wav"

            def fake_run(command, **kwargs):
                output_path.write_bytes(b"RIFFfake-wave")
                return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")

            with patch("src.tts_providers.moss_tts_provider.subprocess.run", side_effect=fake_run) as run:
                synthesize_text(
                    "\u041f\u0440\u0438\u0432\u0435\u0442",
                    output_path,
                    {
                        "moss_tts_path": str(moss_path),
                        "voice_clone_enabled": True,
                        "prompt_audio_path": str(prompt),
                    },
                )

            command = run.call_args.args[0]
            self.assertIn("--mode", command)
            self.assertIn("voice_clone", command)
            self.assertIn("--prompt-audio-path", command)
            self.assertIn(str(prompt), command)

    def test_default_test_text_is_readable_russian(self) -> None:
        self.assertIn("\u0422\u044b \u043d\u0435 \u043b\u0435\u043d\u0438\u0432\u044b\u0439", DEFAULT_MOSS_TTS_TEST_TEXT)
        self.assertNotIn("Ð", DEFAULT_MOSS_TTS_TEST_TEXT)


if __name__ == "__main__":
    unittest.main()
