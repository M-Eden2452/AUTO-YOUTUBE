from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


def load_script_module():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "test_moss_voices.py"
    spec = importlib.util.spec_from_file_location("test_moss_voices_script", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class MossVoiceTesterTests(unittest.TestCase):
    def test_discovers_voice_samples_from_multiple_roots(self) -> None:
        module = load_script_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            first = root / "assets" / "voice_samples"
            second = root / "MOSS_TTS_Nano" / "assets" / "voice_samples"
            first.mkdir(parents=True)
            second.mkdir(parents=True)
            (first / "moss_test_01.wav").write_bytes(b"RIFF")
            (second / "moss_test_02.mp3").write_bytes(b"ID3")

            samples = module.discover_voice_samples([first, second])

        self.assertEqual([sample.sample_id for sample in samples], ["moss_test_01", "moss_test_02"])

    def test_empty_report_explains_how_to_add_samples(self) -> None:
        module = load_script_module()
        markdown = module.build_report([], [], {"backend": "onnx", "python": "python.exe"}, no_samples=True)

        self.assertIn("No voice samples found", markdown)
        self.assertIn("5-20 seconds", markdown)

    def test_report_includes_manual_quality_fields(self) -> None:
        module = load_script_module()
        sample = module.VoiceSample(sample_id="moss_test_01", path=Path("voice.wav"))
        result = module.GenerationResult(
            sample=sample,
            test_id="ru_short",
            text="\u041f\u0440\u0438\u0432\u0435\u0442",
            output_path=Path("out.wav"),
            duration_seconds=1.25,
            file_size_bytes=1234,
            backend="onnx",
            speed="2.0x realtime",
            error="",
        )

        markdown = module.build_report([sample], [result], {"backend": "onnx", "python": "python.exe"})

        self.assertIn("naturalness:", markdown)
        self.assertIn("usable_for_youtube: yes/no", markdown)
        self.assertIn("moss_test_01_ru_short.wav", markdown)


if __name__ == "__main__":
    unittest.main()
