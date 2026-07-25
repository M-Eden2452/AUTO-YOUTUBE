"""Tests for src.audio.scene_timeline - pure arithmetic over manifests.

No network, no ffmpeg, no provider, no writes outside tempfile.
"""

from __future__ import annotations

import unittest

from src.audio.scene_timeline import (
    DURATION_TOLERANCE_SEC,
    apply_timeline_to_script,
    build_scene_timeline,
    scene_render_duration,
)


def _voice_manifest(durations: list[float], *, pause_total: float, status: str = "completed") -> dict:
    return {
        "schema_version": 2,
        "status": status,
        "format_id": "vertical_short",
        "scenes": [
            {
                "scene_id": f"scene_{index + 1:03d}",
                "scene_index": index,
                "duration_seconds": duration,
                "generation_status": "completed",
            }
            for index, duration in enumerate(durations)
        ],
        "narration": {
            "output_path": "narration.wav",
            "duration_sec": sum(durations) + pause_total,
            "pause_total_sec": pause_total,
        },
    }


def _script(targets: list[float]) -> dict:
    scenes = []
    start = 0.0
    for index, target in enumerate(targets):
        scenes.append(
            {
                "scene_id": f"scene_{index + 1:03d}",
                "start_sec": start,
                "target_duration_sec": target,
                "narration": f"Текст сцены {index + 1}",
            }
        )
        start += target
    return {"scenes": scenes, "target_duration_sec": 55, "estimated_duration_sec": sum(targets)}


class BuildSceneTimelineTests(unittest.TestCase):
    def test_timeline_matches_the_real_narration_duration(self) -> None:
        # Numbers taken from the first confirmed live run: 6 scenes, 5 pauses of
        # 0.35 s (vertical_short between_scenes_sec), narration 59.474813 s.
        durations = [7.24, 9.10, 11.30, 10.05, 12.02, 8.00]
        manifest = _voice_manifest(durations, pause_total=1.75)
        timeline = build_scene_timeline(manifest, script=_script([3.5, 7.0, 10.0, 8.0, 9.0, 6.0]))

        self.assertTrue(timeline)
        self.assertEqual(timeline.source, "voice_manifest")
        self.assertEqual(len(timeline.scenes), 6)
        self.assertAlmostEqual(
            timeline.total_duration_sec, sum(durations) + 1.75, delta=DURATION_TOLERANCE_SEC
        )
        self.assertAlmostEqual(timeline.pause_total_sec, 1.75, places=3)

    def test_scenes_are_contiguous_and_start_at_zero(self) -> None:
        timeline = build_scene_timeline(_voice_manifest([4.0, 5.0, 6.0], pause_total=0.7))
        self.assertEqual(timeline.scenes[0].start_sec, 0.0)
        for previous, current in zip(timeline.scenes, timeline.scenes[1:], strict=False):
            self.assertAlmostEqual(previous.end_sec, current.start_sec, places=6)

    def test_last_scene_has_no_trailing_pause(self) -> None:
        timeline = build_scene_timeline(_voice_manifest([4.0, 5.0], pause_total=0.35))
        self.assertEqual(timeline.scenes[-1].pause_after_sec, 0.0)
        self.assertAlmostEqual(timeline.scenes[0].pause_after_sec, 0.35, places=3)

    def test_recorded_pause_total_wins_over_the_policy_prediction(self) -> None:
        """The manifest is evidence of what was rendered; the policy is a prediction."""
        timeline = build_scene_timeline(_voice_manifest([4.0, 5.0, 6.0], pause_total=2.0))
        self.assertAlmostEqual(timeline.pause_total_sec, 2.0, places=3)
        self.assertAlmostEqual(timeline.scenes[0].pause_after_sec, 1.0, places=3)

    def test_last_scene_absorbs_a_narration_mismatch(self) -> None:
        manifest = _voice_manifest([4.0, 5.0], pause_total=0.35)
        manifest["narration"]["duration_sec"] = 12.0  # ffprobe says longer than the parts
        timeline = build_scene_timeline(manifest)
        self.assertAlmostEqual(timeline.total_duration_sec, 12.0, delta=DURATION_TOLERANCE_SEC)
        self.assertTrue(timeline.warnings)

    def test_single_scene_timeline(self) -> None:
        timeline = build_scene_timeline(_voice_manifest([7.5], pause_total=0.0))
        self.assertEqual(len(timeline.scenes), 1)
        self.assertAlmostEqual(timeline.total_duration_sec, 7.5, places=3)

    def test_scene_order_follows_scene_index_not_list_order(self) -> None:
        manifest = _voice_manifest([4.0, 5.0, 6.0], pause_total=0.7)
        manifest["scenes"].reverse()
        timeline = build_scene_timeline(manifest)
        self.assertEqual([scene.scene_id for scene in timeline.scenes], ["scene_001", "scene_002", "scene_003"])


class EmptyTimelineTests(unittest.TestCase):
    """Every one of these must be a safe no-op, never an exception."""

    def test_none_manifest(self) -> None:
        self.assertFalse(build_scene_timeline(None))

    def test_empty_manifest(self) -> None:
        self.assertFalse(build_scene_timeline({}))

    def test_stub_manifest_from_the_unapproved_voice_stage(self) -> None:
        stub = {"status": "provider_selection_required", "audio_path": "", "scenes": []}
        self.assertFalse(build_scene_timeline(stub))

    def test_partially_completed_manifest_is_rejected(self) -> None:
        manifest = _voice_manifest([4.0, 5.0], pause_total=0.35, status="partially_completed")
        timeline = build_scene_timeline(manifest)
        self.assertFalse(timeline)
        self.assertTrue(timeline.warnings)

    def test_scenes_without_durations_are_rejected(self) -> None:
        manifest = _voice_manifest([4.0, 5.0], pause_total=0.35)
        manifest["scenes"][1].pop("duration_seconds")
        self.assertFalse(build_scene_timeline(manifest))

    def test_legacy_duration_sec_spelling_is_accepted(self) -> None:
        manifest = _voice_manifest([4.0, 5.0], pause_total=0.35)
        for scene in manifest["scenes"]:
            scene["duration_sec"] = scene.pop("duration_seconds")
        self.assertTrue(build_scene_timeline(manifest))


class ApplyTimelineToScriptTests(unittest.TestCase):
    def test_actual_durations_are_written_and_planned_ones_preserved(self) -> None:
        script = _script([3.5, 7.0])
        timeline = build_scene_timeline(_voice_manifest([7.24, 9.10], pause_total=0.35), script=script)
        updated = apply_timeline_to_script(script, timeline)

        first, second = updated["scenes"]
        self.assertAlmostEqual(first["actual_duration_sec"], 7.59, places=2)  # 7.24 speech + 0.35 pause
        self.assertAlmostEqual(first["speech_duration_sec"], 7.24, places=2)
        self.assertEqual(first["target_duration_sec"], 3.5)  # the plan is not rewritten
        self.assertEqual(first["start_sec"], 0.0)
        self.assertAlmostEqual(second["start_sec"], 7.59, places=2)
        self.assertEqual(updated["timing_source"], "voice_manifest")

    def test_original_script_is_not_mutated(self) -> None:
        script = _script([3.5, 7.0])
        timeline = build_scene_timeline(_voice_manifest([7.24, 9.10], pause_total=0.35), script=script)
        apply_timeline_to_script(script, timeline)
        self.assertNotIn("actual_duration_sec", script["scenes"][0])

    def test_empty_timeline_returns_the_script_unchanged(self) -> None:
        script = _script([3.5, 7.0])
        self.assertIs(apply_timeline_to_script(script, build_scene_timeline(None)), script)

    def test_scenes_without_narration_are_left_alone(self) -> None:
        script = _script([3.5, 7.0, 4.0])
        timeline = build_scene_timeline(_voice_manifest([7.24, 9.10], pause_total=0.35), script=script)
        updated = apply_timeline_to_script(script, timeline)
        self.assertNotIn("actual_duration_sec", updated["scenes"][2])
        self.assertEqual(updated["scenes"][2]["target_duration_sec"], 4.0)


class SceneRenderDurationTests(unittest.TestCase):
    def test_actual_wins_over_target(self) -> None:
        self.assertEqual(scene_render_duration({"actual_duration_sec": 7.5, "target_duration_sec": 3.5}), 7.5)

    def test_falls_back_to_target_when_actual_is_absent(self) -> None:
        self.assertEqual(scene_render_duration({"target_duration_sec": 3.5}), 3.5)

    def test_falls_back_to_default_when_nothing_is_known(self) -> None:
        self.assertEqual(scene_render_duration({}), 3.0)

    def test_minimum_is_enforced(self) -> None:
        self.assertEqual(scene_render_duration({"actual_duration_sec": 0.2}), 1.0)
        self.assertAlmostEqual(scene_render_duration({"actual_duration_sec": 0.2}, minimum_sec=0.1), 0.2)

    def test_unparseable_values_do_not_raise(self) -> None:
        self.assertEqual(scene_render_duration({"actual_duration_sec": "нет", "target_duration_sec": 4.0}), 4.0)


if __name__ == "__main__":
    unittest.main()
