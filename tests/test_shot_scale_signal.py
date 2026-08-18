"""C99: shot scale as a should, not a mismeasured must.

Registry finding: ranking did not distinguish shot framing/composition when
candidates were otherwise semantically equal or close - ``live_5/scene_001`` took
a close-up over an owner-preferred wide/establishing shot even though the scene's
own ``visual_brief.shot_type`` said "establishing"; the ranker had no path from
that field to the score at all. Owner decision 2026-08-18: add a cheap,
deterministic, offline shot-scale signal grounded in the scene's own declared shot
type (``src.content.visual_planning.models.SHOT_TYPES``) - never "closer/wider is
always better" - and never allowed to outrank meaning.

What this file covers: the primitive itself (``candidate_ranker._shot_scale_signal``
and the constants around it), exercised only through ``rank_candidates`` - the same
seam every other test in this package uses, never imported privately. What it does
not cover: the frozen-corpus acceptance numbers, which live in
``tests/test_plan9d_ground_truth_baseline.py`` (``FrozenBaselineMeasurementTests``,
``FrozenBilingualMeasurementTests``) alongside every other PLAN-9D measurement, and
the ``measure --baseline`` run recorded in ``docs/current/CLEANUP_REGISTRY.md`` C99.

One finding this file documents rather than hides: ``"payoff"`` was tried as a
close-up intent and measured out. On the frozen v2 corpus it predicted the owner's
pick correctly for one payoff scene (``local_after_fix/scene_005``) and *wrongly*
for another (``live_5/scene_005``) - one win, one loss on the only two payoff
scenes measurable, which is "not reliably distinguishable" rather than a rule. It
is not in ``SHOT_TYPE_SCALE_INTENT``, and this file asserts that a payoff scene
gets no adjustment so a future edit cannot quietly reintroduce a rule that was
already falsified once.
"""

from __future__ import annotations

import unittest

from src.assets.semantic_selection.candidate_ranker import (
    SHOT_SCALE_ADJUSTMENT,
    SHOT_TYPE_SCALE_INTENT,
    rank_candidates,
)
from src.assets.semantic_selection.models import SemanticScene


def _candidate(asset_id: str, *, title: str = "", description: str = "") -> dict[str, object]:
    return {
        "asset_id": asset_id,
        "provider": "fake",
        "media_type": "image",
        "title": title,
        "description": description,
        "tags": [],
        "tags_source": "provider",
        "width": 1920,
        "height": 1080,
        "allowed_for_render": True,
        "review_required": False,
        "rights_status": "licensed",
    }


def _scene(shot_type: str = "", **overrides: object) -> SemanticScene:
    overrides.setdefault("subject", ["solar panel"])
    return SemanticScene(scene_id="scene", shot_type=shot_type, **overrides)


def _ranked(
    scene: SemanticScene, candidates: list[dict[str, object]]
) -> dict[str, dict[str, object]]:
    return {str(item["asset_id"]): item for item in rank_candidates(scene, candidates, source_class="")}


class ShotTypeScaleIntentTests(unittest.TestCase):
    """The mapping itself: what is in it, what was tried and dropped, and why."""

    def test_only_the_near_tautological_pairs_are_mapped(self) -> None:
        self.assertEqual(
            {"establishing": "wide", "context": "wide", "detail": "close"},
            SHOT_TYPE_SCALE_INTENT,
        )

    def test_payoff_action_and_evidence_carry_no_scale_preference(self) -> None:
        for shot_type in ("payoff", "action", "evidence", "", "unknown_future_type"):
            self.assertNotIn(shot_type, SHOT_TYPE_SCALE_INTENT)


class ShotScaleSignalTests(unittest.TestCase):
    def test_a_scene_with_no_shot_type_gives_neither_candidate_an_adjustment(self) -> None:
        wide = _candidate("wide", title="Aerial shot of a solar farm at dawn")
        close = _candidate("close", title="Close-up of a solar panel cell")
        ranked = _ranked(_scene(shot_type=""), [wide, close])
        self.assertEqual(0.0, ranked["wide"]["shot_scale_adjustment"])
        self.assertEqual(0.0, ranked["close"]["shot_scale_adjustment"])
        self.assertEqual("", ranked["wide"]["shot_scale_intent"])

    def test_an_establishing_scene_rewards_wide_and_penalises_close(self) -> None:
        # Same subject wording on both sides - the only thing that differs is the
        # shot-scale phrase, so a `subject_match` gap cannot be mistaken for this
        # signal's own effect.
        wide = _candidate("wide", title="Aerial shot of a solar panel array in daylight")
        close = _candidate("close", title="Close-up of a solar panel array in daylight")
        ranked = _ranked(_scene(shot_type="establishing"), [wide, close])
        self.assertEqual(SHOT_SCALE_ADJUSTMENT, ranked["wide"]["shot_scale_adjustment"])
        self.assertEqual(-SHOT_SCALE_ADJUSTMENT, ranked["close"]["shot_scale_adjustment"])
        self.assertEqual("wide", ranked["wide"]["shot_scale_intent"])
        self.assertEqual("wide", ranked["wide"]["shot_scale_observed"])
        self.assertGreater(ranked["wide"]["final_score"], ranked["close"]["final_score"])

    def test_a_detail_scene_rewards_close_and_penalises_wide(self) -> None:
        wide = _candidate("wide", title="Aerial shot of a solar farm at dawn")
        close = _candidate("close", title="Close-up of a solar panel cell")
        ranked = _ranked(_scene(shot_type="detail"), [wide, close])
        self.assertEqual(SHOT_SCALE_ADJUSTMENT, ranked["close"]["shot_scale_adjustment"])
        self.assertEqual(-SHOT_SCALE_ADJUSTMENT, ranked["wide"]["shot_scale_adjustment"])

    def test_a_candidate_silent_about_scale_gets_no_adjustment_either_way(self) -> None:
        silent = _candidate("silent", title="Solar panel installation on a rooftop")
        ranked = _ranked(_scene(shot_type="establishing"), [silent])
        self.assertEqual(0.0, ranked["silent"]["shot_scale_adjustment"])
        self.assertEqual("", ranked["silent"]["shot_scale_observed"])

    def test_a_record_naming_both_scales_is_ambiguous_and_not_scored(self) -> None:
        both = _candidate("both", title="Aerial shot cutting to a close-up of the array")
        ranked = _ranked(_scene(shot_type="establishing"), [both])
        self.assertEqual(0.0, ranked["both"]["shot_scale_adjustment"])
        self.assertEqual("ambiguous", ranked["both"]["shot_scale_observed"])

    def test_a_payoff_scene_gives_no_adjustment_despite_declared_vocabulary(self) -> None:
        wide = _candidate("wide", title="Aerial shot of a solar farm at dawn")
        close = _candidate("close", title="Close-up of a solar panel cell")
        ranked = _ranked(_scene(shot_type="payoff"), [wide, close])
        self.assertEqual(0.0, ranked["wide"]["shot_scale_adjustment"])
        self.assertEqual(0.0, ranked["close"]["shot_scale_adjustment"])
        self.assertEqual("", ranked["wide"]["shot_scale_intent"])

    def test_meaning_still_outranks_shot_scale(self) -> None:
        """A strong subject mismatch is not something a shot-scale bonus may cover."""

        scene = _scene(shot_type="establishing", subject=["solar panel"])
        strong_match_wrong_scale = _candidate(
            "strong", title="Close-up of a solar panel mounted on a rooftop"
        )
        weak_match_right_scale = _candidate(
            "weak", title="Aerial shot of a wind turbine farm at dusk"
        )
        ranked = _ranked(scene, [strong_match_wrong_scale, weak_match_right_scale])
        self.assertEqual(-SHOT_SCALE_ADJUSTMENT, ranked["strong"]["shot_scale_adjustment"])
        self.assertEqual(SHOT_SCALE_ADJUSTMENT, ranked["weak"]["shot_scale_adjustment"])
        self.assertGreater(ranked["strong"]["final_score"], ranked["weak"]["final_score"])


class SceneAnalyzerShotTypeTests(unittest.TestCase):
    """The production dual-read (C99): ``analyze_scene`` also has to see the field."""

    def test_shot_type_is_read_from_the_visual_brief(self) -> None:
        from src.assets.semantic_selection.scene_analyzer import analyze_scene

        scene = analyze_scene({"visual_brief": {"shot_type": "establishing"}})
        self.assertEqual("establishing", scene.shot_type)

    def test_an_explicit_semantic_shot_type_overrides_the_brief(self) -> None:
        from src.assets.semantic_selection.scene_analyzer import analyze_scene

        scene = analyze_scene(
            {"semantic": {"shot_type": "detail"}, "visual_brief": {"shot_type": "establishing"}}
        )
        self.assertEqual("detail", scene.shot_type)

    def test_a_scene_without_either_source_carries_no_shot_type(self) -> None:
        from src.assets.semantic_selection.scene_analyzer import analyze_scene

        scene = analyze_scene({})
        self.assertEqual("", scene.shot_type)


if __name__ == "__main__":
    unittest.main()
