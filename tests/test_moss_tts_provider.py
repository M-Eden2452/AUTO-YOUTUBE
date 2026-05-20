from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.tts_providers.moss_tts_provider import MossTtsProviderError, synthesize_text


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
                    "Привет",
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
            self.assertIn("Привет", command)
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
                    synthesize_text("Привет", root / "voice.wav", {"moss_tts_path": str(moss_path)})


if __name__ == "__main__":
    unittest.main()
