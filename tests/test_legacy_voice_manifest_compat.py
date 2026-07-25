from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path


class LegacyVoiceManifestCompatTests(unittest.TestCase):
    def test_reads_current_news_voice_stage_stub_shape(self) -> None:
        from src.audio.voice_manifest import read_voice_manifest

        # Exact shape written by src/news/voice_stage.py::build_safe_voice_manifest
        legacy = {
            "status": "provider_selection_required",
            "voice_stage_status": "provider_selection_required",
            "language": "ru",
            "draft_provider": "audio_file",
            "paid_provider": "elevenlabs",
            "paid_tts_requires_approval": True,
            "audition_requires_approval": True,
            "full_generation_requires_approval": True,
            "never_auto_fallback_to_paid": True,
            "paid_call_performed": False,
            "message": "Черновой источник озвучки не настроен.",
            "selection": {"provider": "elevenlabs", "voice_profile": "ru_dom"},
            "script_hash": "abc",
            "settings_hash": "def",
            "character_count": 620,
            "audio_path": "",
            "source_type": "",
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "voice_manifest.json"
            path.write_text(json.dumps(legacy, ensure_ascii=False), encoding="utf-8")
            loaded = read_voice_manifest(path)
            self.assertEqual(loaded["status"], "provider_selection_required")
            self.assertEqual(loaded["scenes"], [])
            self.assertIn("narration", loaded)
            self.assertIn("cache_summary", loaded)

    def test_reads_solar_vs_nuclear_ensure_final_voice_shape(self) -> None:
        from src.audio.voice_manifest import read_voice_manifest

        # Exact shape written by src/production_plan/solar_vs_nuclear_render.py::ensure_final_voice
        legacy = {
            "status": "completed",
            "provider": "elevenlabs",
            "voice_name": "Dom",
            "voice_id": "hDfThiytYnsDMuVgm6Qy",
            "model_id": "eleven_multilingual_v2",
            "audio_path": "G:/Projects/AI-YouTube/project_solar_vs_nuclear/02_voice/voice_final.wav",
            "mp3_path": "G:/Projects/AI-YouTube/project_solar_vs_nuclear/02_voice/voice_final.mp3",
            "duration_sec": 182.4,
            "characters": 2100,
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "voice_manifest.json"
            path.write_text(json.dumps(legacy, ensure_ascii=False), encoding="utf-8")
            loaded = read_voice_manifest(path)
            self.assertEqual(loaded["status"], "completed")
            self.assertEqual(loaded["audio_path"], legacy["audio_path"])
            self.assertEqual(loaded["narration"]["output_path"], legacy["audio_path"])
            self.assertIn("scenes", loaded)

    def test_read_voice_manifest_never_raises_on_missing_optional_fields(self) -> None:
        from src.audio.voice_manifest import read_voice_manifest

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "voice_manifest.json"
            path.write_text(json.dumps({}), encoding="utf-8")
            loaded = read_voice_manifest(path)
            self.assertEqual(loaded["status"], "unconfigured")


if __name__ == "__main__":
    unittest.main()
