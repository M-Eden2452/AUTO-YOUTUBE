from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path


class VoiceManifestSchemaTests(unittest.TestCase):
    def _request(self):
        from src.audio.narration_models import build_narration_request_from_scenes
        from src.audio.tts.models import VoiceProfile
        from src.audio.voice_policy import VoicePolicy

        profile = VoiceProfile(profile_id="ru_dom", display_name="Dom", provider="elevenlabs", voice_id="v1", model_id="m1", language="ru")
        policy = VoicePolicy(enabled=True, output_mode="scene_audio", scene_level_generation=True)
        scenes = [{"scene_id": "scene_001", "text": "Текст."}]
        return build_narration_request_from_scenes(
            project_id="p1", job_id="j1", channel_id="c1", localization_id="ru", language="ru",
            format_id="vertical_short", template_id="fullscreen_voiceover_v1",
            voice_profile=profile, policy=policy, scenes=scenes, full_text="Текст.", output_root="/tmp/unused",
        )

    def test_manifest_has_full_schema_and_no_secrets(self) -> None:
        from src.audio.voice_manifest import SCHEMA_VERSION, build_voice_manifest

        request = self._request()
        manifest = build_voice_manifest(request, status="completed", scenes_meta=[])

        for key in (
            "schema_version", "status", "voice_stage_status", "project_id", "localization", "provider",
            "voice_profile", "voice_id", "voice_name", "model_id", "output_mode", "timing_mode", "approval",
            "preflight", "character_count", "scenes", "narration", "cache_summary", "generation_summary",
            "post_processing", "errors", "warnings", "created_at", "updated_at",
        ):
            self.assertIn(key, manifest, f"missing manifest field: {key}")
        self.assertEqual(manifest["schema_version"], SCHEMA_VERSION)
        serialized = json.dumps(manifest, ensure_ascii=False)
        self.assertNotIn("api_key", serialized.lower())
        self.assertNotIn("xi-api-key", serialized.lower())

    def test_manifest_sets_legacy_compatible_audio_path_for_renderer(self) -> None:
        from src.audio.audio_assembler import AssemblyResult
        from src.audio.voice_manifest import build_voice_manifest

        request = self._request()
        assembly = AssemblyResult(
            output_path="/tmp/project/localizations/ru/voice/narration.wav", duration_sec=3.2,
            checksum_sha256="abc123", sample_rate=48000, channels=1, scene_count=1,
        )
        manifest = build_voice_manifest(request, status="completed", assembly=assembly)
        self.assertEqual(manifest["audio_path"], assembly.output_path)
        self.assertEqual(manifest["status"], "completed")

    def test_read_voice_manifest_round_trips_new_schema(self) -> None:
        from src.audio.voice_manifest import build_voice_manifest, read_voice_manifest

        request = self._request()
        manifest = build_voice_manifest(request, status="completed", scenes_meta=[])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "voice_manifest.json"
            path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
            loaded = read_voice_manifest(path)
            self.assertEqual(loaded["schema_version"], manifest["schema_version"])
            self.assertEqual(loaded["status"], "completed")


if __name__ == "__main__":
    unittest.main()
