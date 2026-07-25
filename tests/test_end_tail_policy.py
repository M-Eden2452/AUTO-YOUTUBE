from __future__ import annotations

import unittest

from src.audio.end_tail_policy import (
    DEFAULT_TAIL_SEC,
    END_POLICY_FIXED_DURATION,
    END_POLICY_MATCH_NARRATION,
    END_POLICY_NARRATION_PLUS_TAIL,
    END_POLICY_PRESERVE_VISUAL_TIMELINE,
    EndTailPolicyError,
    clamp_tail_sec,
    compute_target_duration,
    narration_duration_from_voice_manifest,
    resolve_end_policy,
)


class ResolveEndPolicyTests(unittest.TestCase):
    def test_fullscreen_voiceover_defaults_to_narration_plus_tail(self) -> None:
        self.assertEqual(resolve_end_policy("fullscreen_voiceover_v1"), END_POLICY_NARRATION_PLUS_TAIL)

    def test_unknown_template_defaults_to_preserve_visual_timeline(self) -> None:
        self.assertEqual(resolve_end_policy("story_card_text_only_v1"), END_POLICY_PRESERVE_VISUAL_TIMELINE)
        self.assertEqual(resolve_end_policy(None), END_POLICY_PRESERVE_VISUAL_TIMELINE)


class ClampTailSecTests(unittest.TestCase):
    def test_clamps_within_recommended_range(self) -> None:
        self.assertEqual(clamp_tail_sec(0.0), 0.5)
        self.assertEqual(clamp_tail_sec(5.0), 1.0)
        self.assertEqual(clamp_tail_sec(0.75), 0.75)


class ComputeTargetDurationTests(unittest.TestCase):
    def test_narration_plus_tail_adds_default_tail(self) -> None:
        duration = compute_target_duration(
            END_POLICY_NARRATION_PLUS_TAIL,
            narration_duration_sec=25.18,
            visual_duration_sec=38.0,
        )
        self.assertAlmostEqual(duration, 25.18 + DEFAULT_TAIL_SEC, places=3)

    def test_narration_plus_tail_can_exceed_visual_timeline(self) -> None:
        # Narration longer than the planned visual timeline must never be cut short;
        # the caller is expected to extend (hold last frame), not the audio.
        duration = compute_target_duration(
            END_POLICY_NARRATION_PLUS_TAIL,
            narration_duration_sec=40.0,
            visual_duration_sec=38.0,
        )
        self.assertAlmostEqual(duration, 40.75, places=3)

    def test_match_narration_ignores_tail(self) -> None:
        duration = compute_target_duration(
            END_POLICY_MATCH_NARRATION,
            narration_duration_sec=25.18,
            visual_duration_sec=38.0,
        )
        self.assertAlmostEqual(duration, 25.18, places=3)

    def test_preserve_visual_timeline_ignores_narration(self) -> None:
        duration = compute_target_duration(
            END_POLICY_PRESERVE_VISUAL_TIMELINE,
            narration_duration_sec=25.18,
            visual_duration_sec=38.0,
        )
        self.assertAlmostEqual(duration, 38.0, places=3)

    def test_no_narration_always_uses_visual_timeline_regardless_of_policy(self) -> None:
        for policy in (END_POLICY_NARRATION_PLUS_TAIL, END_POLICY_MATCH_NARRATION):
            duration = compute_target_duration(policy, narration_duration_sec=0.0, visual_duration_sec=14.0)
            self.assertAlmostEqual(duration, 14.0, places=3)

    def test_fixed_duration_requires_explicit_value(self) -> None:
        with self.assertRaises(EndTailPolicyError):
            compute_target_duration(END_POLICY_FIXED_DURATION, narration_duration_sec=10.0, visual_duration_sec=10.0)
        duration = compute_target_duration(
            END_POLICY_FIXED_DURATION,
            narration_duration_sec=10.0,
            visual_duration_sec=10.0,
            fixed_duration_sec=20.0,
        )
        self.assertEqual(duration, 20.0)

    def test_unknown_policy_rejected(self) -> None:
        with self.assertRaises(EndTailPolicyError):
            compute_target_duration("not_a_policy", narration_duration_sec=1.0, visual_duration_sec=1.0)


class NarrationDurationFromVoiceManifestTests(unittest.TestCase):
    def test_reads_schema_v2_nested_duration(self) -> None:
        manifest = {"narration": {"duration_sec": 25.177}}
        self.assertAlmostEqual(narration_duration_from_voice_manifest(manifest), 25.177, places=3)

    def test_reads_legacy_top_level_duration(self) -> None:
        manifest = {"status": "completed", "duration_sec": 3.0}
        self.assertAlmostEqual(narration_duration_from_voice_manifest(manifest), 3.0, places=3)

    def test_missing_or_empty_manifest_returns_zero(self) -> None:
        self.assertEqual(narration_duration_from_voice_manifest({}), 0.0)
        self.assertEqual(narration_duration_from_voice_manifest(None), 0.0)


if __name__ == "__main__":
    unittest.main()
