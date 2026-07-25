from __future__ import annotations

import unittest


class NarrationModelsTests(unittest.TestCase):
    def test_generation_key_changes_for_provider_voice_model_language_settings_format_speed(self) -> None:
        from src.audio.narration_models import compute_generation_key

        base = dict(
            text="Привет",
            provider="elevenlabs",
            voice_id="v1",
            model_id="m1",
            language="ru",
            settings={"stability": 0.6},
            output_format="wav",
            speed=1.0,
            post_processing_version="",
        )
        base_key = compute_generation_key(**base)

        self.assertNotEqual(base_key, compute_generation_key(**{**base, "provider": "audio_file"}))
        self.assertNotEqual(base_key, compute_generation_key(**{**base, "voice_id": "v2"}))
        self.assertNotEqual(base_key, compute_generation_key(**{**base, "model_id": "m2"}))
        self.assertNotEqual(base_key, compute_generation_key(**{**base, "language": "en"}))
        self.assertNotEqual(base_key, compute_generation_key(**{**base, "settings": {"stability": 0.9}}))
        self.assertNotEqual(base_key, compute_generation_key(**{**base, "output_format": "mp3_44100_128"}))
        self.assertNotEqual(base_key, compute_generation_key(**{**base, "speed": 1.2}))
        self.assertNotEqual(base_key, compute_generation_key(**{**base, "post_processing_version": "v2"}))
        self.assertEqual(base_key, compute_generation_key(**base))

    def test_build_narration_request_from_scenes_maps_news_scene_shape(self) -> None:
        from src.audio.narration_models import build_narration_request_from_scenes
        from src.audio.tts.models import VoiceProfile
        from src.audio.voice_policy import VoicePolicy

        profile = VoiceProfile(profile_id="ru_dom", display_name="Dom", provider="elevenlabs", voice_id="v1", model_id="m1", language="ru")
        policy = VoicePolicy(enabled=True, output_mode="scene_audio", scene_level_generation=True)
        scenes = [
            {"scene_id": "scene_001", "narration": "Первая сцена.", "target_duration_sec": 5.0},
            {"scene_id": "scene_002", "narration": "Вторая сцена.", "target_duration_sec": 6.0},
        ]
        request = build_narration_request_from_scenes(
            project_id="job_001", job_id="job_001", channel_id="nature_science_news_ru", localization_id="ru",
            language="ru", format_id="vertical_short", template_id="fullscreen_voiceover_v1",
            voice_profile=profile, policy=policy, scenes=scenes, output_root="/tmp/does_not_matter",
        )
        self.assertEqual(len(request.scenes), 2)
        self.assertEqual(request.scenes[0].text, "Первая сцена.")
        self.assertEqual(request.scenes[0].scene_index, 0)
        self.assertTrue(request.scenes[0].generation_key)
        self.assertNotEqual(request.scenes[0].generation_key, request.scenes[1].generation_key)

    def test_scene_text_hash_is_deterministic(self) -> None:
        from src.audio.narration_models import NarrationScene
        from src.audio.tts.models import compute_text_hash

        scene = NarrationScene(scene_id="s1", scene_index=0, text="Текст сцены")
        self.assertEqual(scene.text_hash, compute_text_hash("Текст сцены"))


if __name__ == "__main__":
    unittest.main()
