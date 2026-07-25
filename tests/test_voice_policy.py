from __future__ import annotations

import unittest


class VoicePolicyTests(unittest.TestCase):
    def test_defaults_are_safe_and_disabled(self) -> None:
        from src.audio.voice_policy import VoicePolicy

        policy = VoicePolicy()
        self.assertEqual(policy.output_mode, "disabled")
        self.assertEqual(policy.fallback_policy, "none")
        self.assertTrue(policy.approval_required)

    def test_invalid_output_mode_rejected(self) -> None:
        from src.audio.voice_policy import VoicePolicy, VoicePolicyError

        with self.assertRaises(VoicePolicyError):
            VoicePolicy(output_mode="not_a_real_mode")

    def test_invalid_timing_mode_rejected(self) -> None:
        from src.audio.voice_policy import VoicePolicy, VoicePolicyError

        with self.assertRaises(VoicePolicyError):
            VoicePolicy(timing_mode="not_a_real_mode")

    def test_invalid_fallback_policy_rejected(self) -> None:
        from src.audio.voice_policy import VoicePolicy, VoicePolicyError

        with self.assertRaises(VoicePolicyError):
            VoicePolicy(fallback_policy="not_a_real_policy")

    def test_resolve_precedence_channel_then_template_then_project_then_localization(self) -> None:
        from src.audio.voice_policy import resolve_voice_policy

        policy = resolve_voice_policy(
            channel_defaults={"provider": "elevenlabs", "output_mode": "single_narration", "target_sample_rate": 44100},
            template_defaults={"output_mode": "scene_audio", "scene_level_generation": True},
            project_overrides={"target_sample_rate": 48000},
            localization_overrides={"language": "ru"},
        )
        # provider only set at channel layer -> survives
        self.assertEqual(policy.provider, "elevenlabs")
        # output_mode overridden by template layer -> template wins over channel
        self.assertEqual(policy.output_mode, "scene_audio")
        self.assertTrue(policy.scene_level_generation)
        # target_sample_rate overridden by project layer -> project wins over channel
        self.assertEqual(policy.target_sample_rate, 48000)
        # language only set at localization layer -> survives
        self.assertEqual(policy.language, "ru")

    def test_partial_layer_does_not_reset_unset_fields(self) -> None:
        from src.audio.voice_policy import resolve_voice_policy

        policy = resolve_voice_policy(
            channel_defaults={"provider": "elevenlabs", "voice_profile": "ru_dom"},
            localization_overrides={"language": "ru"},
        )
        self.assertEqual(policy.provider, "elevenlabs")
        self.assertEqual(policy.voice_profile, "ru_dom")

    def test_voice_policy_from_channel_config_reads_existing_shape(self) -> None:
        from src.audio.voice_policy import voice_policy_from_channel_config

        voice_cfg = {
            "provider": "elevenlabs",
            "voice_profile": "ru_dom",
            "voice_id": "hDfThiytYnsDMuVgm6Qy",
            "model": "eleven_multilingual_v2",
            "settings": {"speed": 1.02},
        }
        workflow_cfg = {"paid_tts_requires_approval": True, "never_auto_fallback_to_paid": True}
        normalized = voice_policy_from_channel_config(voice_cfg, workflow_cfg)
        self.assertEqual(normalized["provider"], "elevenlabs")
        self.assertEqual(normalized["model_id"], "eleven_multilingual_v2")
        self.assertEqual(normalized["fallback_policy"], "none")
        self.assertTrue(normalized["approval_required"])
        self.assertEqual(normalized["speed"], 1.02)

    def test_fullscreen_voiceover_default_requires_and_enables_voice(self) -> None:
        from src.audio.voice_policy import AUDIO_POLICY_DEFAULTS, VoicePolicy

        policy = VoicePolicy.from_dict(AUDIO_POLICY_DEFAULTS["fullscreen_voiceover_default"])
        self.assertTrue(policy.enabled)
        self.assertTrue(policy.required)
        self.assertEqual(policy.output_mode, "scene_audio")
        self.assertTrue(policy.scene_level_generation)

    def test_story_card_no_voice_default_is_disabled(self) -> None:
        from src.audio.voice_policy import AUDIO_POLICY_DEFAULTS, VoicePolicy

        policy = VoicePolicy.from_dict(AUDIO_POLICY_DEFAULTS["story_card_no_voice"])
        self.assertFalse(policy.enabled)
        self.assertEqual(policy.output_mode, "disabled")


if __name__ == "__main__":
    unittest.main()
