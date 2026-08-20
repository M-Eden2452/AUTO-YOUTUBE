"""C127: a silent catalogue is not a catalogue saying no.

Owner decision of 2026-08-20. `MIN_SCORE`, `EXACT_SUBJECT_MIN_SCORE` and the weights
`0.45/0.20/0.15/0.05` are explicitly not to be touched, and the threshold is explicitly
not to be lowered to fit `58.824`. The principle instead:

    absence of evidence in stock metadata != evidence of mismatch.

Three states, not two: MATCH (metadata confirms), CONFLICT (metadata gives evidence
against), UNKNOWN (metadata does not answer). UNKNOWN must not be penalised as a
mismatch, must not be counted as a match, and must not raise confidence by itself.

Measured 2026-08-20, offline, on the saved runs and both frozen corpora - 1419 scored
candidates. A candidate whose subject is named outright and whose metadata simply says
nothing about the action or the place scores exactly
``(0.45*100 + 0.05*100) / 0.85 = 58.824`` and is refused by ``score_below_60``. The
refusal is circular, and that is what this file pins:

    meaning_score < MIN_SCORE
      -> semantic_match_status = "mismatched"
      -> semantically_disqualified = True
      -> support_status = SUPPORT_UNSUPPORTED
      -> support not in SOFT_REJECT_ELIGIBLE
      -> "score_below_60" stays a *blocking* refusal

``SOFT_REJECT_PREFIXES``/``SOFT_REJECT_ELIGIBLE`` exist precisely so the slot verdict
can overrule a low average, and this loop is what keeps them from ever doing it for the
candidates they were written for.

Eligibility is not confidence. Such a candidate becomes selectable at *partial* support
and never render-ready; the existing invariant ``partial_support_marked_render_ready``
already enforces that, and this slice does not touch it.

Scope, measured rather than assumed: of the four scenes standing on the ceiling
(004, 009, 012, 013), only ``scene_004`` is blocked by UNKNOWN. In 009/012/013 the
subject itself is never proven - the best subject evidence is 50, 60 and 66.7 - so this
rule deliberately does not reach them, and the cartoons sitting at the top of 012 and
013 stay refused.
"""

from __future__ import annotations

import unittest
from typing import Any

from src.assets.semantic_selection import SemanticScene, rank_candidates
from src.assets.semantic_selection.candidate_ranker import SOFT_REJECT_ELIGIBLE
from src.assets.semantic_selection.decision import SUPPORT_PARTIAL, SUPPORT_UNSUPPORTED

#: Subject named outright, action and place stated by the scene and unmentioned by the
#: catalogue - the shape of ``scene_004`` in both saved sleep runs.
BRAIN = SemanticScene(
    scene_id="scene_004",
    subject=["human brain"],
    action=["glowing anatomical model"],
    environment=["dark studio"],
    visual_priority="exact_action",
)


def _candidate(asset_id: str = "named", **fields: Any) -> dict[str, Any]:
    candidate: dict[str, Any] = {
        "asset_id": asset_id,
        "provider": "wikimedia",
        "media_type": "image",
        "title": "Anatomy and physiology of the human brain AS.jpg",
        "description": "",
        "tags": [],
        "keywords": [],
        # The real ``wikimedia_142165496``: 1920x1080, so ``vertical_score`` is 0 and
        # ``final_score`` lands at 57.5 - below the bar on its own. A vertical fixture
        # would clear the threshold on technical merit and test nothing.
        "width": 1920,
        "height": 1080,
        "allowed_for_render": True,
        "license": "cc-by-4.0",
    }
    candidate.update(fields)
    return candidate


def _page(*, tokens: int, carrying: str = "") -> str:
    filler = [f"catalogue{index}" for index in range(tokens)]
    if carrying:
        filler[tokens // 2 : tokens // 2] = carrying.split()
    return " ".join(filler)


def _rank(scene: SemanticScene, candidate: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    return rank_candidates(scene, [dict(candidate)], **kwargs)[0]


class SilenceStopsBeingARefusal(unittest.TestCase):
    """The one case the owner's decision unblocks, and what it costs."""

    def test_the_named_subject_survives_a_catalogue_that_says_nothing_else(self) -> None:
        ranked = _rank(BRAIN, _candidate())
        self.assertEqual(100.0, ranked["subject_match"])
        self.assertEqual(0.0, ranked["action_match"])
        self.assertEqual(0.0, ranked["environment_match"])
        self.assertFalse(
            ranked["rejected"],
            f"still refused by {list(ranked['blocking_reject_reasons'] or [])}",
        )

    def test_the_low_average_is_recorded_as_advisory_not_erased(self) -> None:
        ranked = _rank(BRAIN, _candidate())
        self.assertIn("score_below_60", list(ranked["advisory_reject_reasons"] or []))
        self.assertNotIn("score_below_60", list(ranked["blocking_reject_reasons"] or []))

    def test_unknown_does_not_become_a_match(self) -> None:
        """The score is untouched: no weight moved, no threshold moved."""
        ranked = _rank(BRAIN, _candidate())
        self.assertEqual(58.824, ranked["semantic_score"])

    def test_eligibility_is_not_confidence(self) -> None:
        ranked = _rank(BRAIN, _candidate())
        self.assertEqual(SUPPORT_PARTIAL, ranked["support_status"])
        self.assertIn(SUPPORT_PARTIAL, SOFT_REJECT_ELIGIBLE)
        self.assertFalse(ranked["selection_decision"]["render_ready"])


class OnlySilenceCounts(unittest.TestCase):
    """A catalogue that answered badly is not a catalogue that stayed silent."""

    #: Same scene, judged at ``exact_subject``: the bar is 75, so a record that *did*
    #: speak about the place can still fall short. That is the case that separates
    #: "the catalogue said nothing" from "the catalogue said something else".
    EXACTING = SemanticScene(
        scene_id="scene_013",
        subject=["human brain"],
        action=["glowing anatomical model"],
        environment=["dark studio"],
        visual_priority="exact_subject",
    )

    #: Seventeen words, so one matching word is worth 5.882 - small enough to leave the
    #: average below 60 and still be evidence. Contrived on purpose: with a named
    #: subject the base is already 58.824, so ordinary partial evidence lifts a
    #: candidate over the bar by itself and never reaches this rule.
    ROOM = (
        "dark studio with black backdrop and softboxes arranged around a rotating "
        "pedestal under low ambient light indoors"
    )
    SPECIFIC_ROOM = SemanticScene(
        scene_id="scene_004",
        subject=["human brain"],
        action=["glowing anatomical model"],
        environment=[ROOM],
        visual_priority="exact_action",
    )

    def test_a_record_that_spoke_and_missed_is_not_rescued(self) -> None:
        """``indoors`` present, sixteen other words absent: evidence, and it missed."""
        candidate = _candidate("spoke", title="Human brain photographed indoors")
        ranked = _rank(self.SPECIFIC_ROOM, candidate)
        self.assertGreater(ranked["environment_match"], 0.0)
        self.assertLess(ranked["semantic_score"], 60.0)
        self.assertTrue(
            ranked["rejected"],
            "a record whose evidence missed must not be rescued as unanswered",
        )
        self.assertIn("score_below_60", list(ranked["blocking_reject_reasons"] or []))

    def test_the_control_for_it_is_the_record_that_said_nothing(self) -> None:
        """Same scene, same bar, same weights - only the silence differs."""
        candidate = _candidate("silent_room", title="The human brain")
        ranked = _rank(self.SPECIFIC_ROOM, candidate)
        self.assertEqual(0.0, ranked["environment_match"])
        self.assertFalse(ranked["rejected"])

    def test_silence_at_the_same_bar_is_still_only_eligible_when_nothing_spoke(
        self,
    ) -> None:
        """The control for the test above: silence, same scene, same bar."""
        ranked = _rank(self.EXACTING, _candidate())
        self.assertEqual(0.0, ranked["action_match"])
        self.assertEqual(0.0, ranked["environment_match"])
        self.assertFalse(ranked["rejected"])

    def test_a_subject_known_only_from_a_catalogue_page_is_not_named(self) -> None:
        """C126 caps such a field at 75, and 75 is not a naming."""
        candidate = _candidate(
            "mentioned",
            provider="internet_archive",
            title="USE OF 16mm EDUCATIONAL FILMS IN THE CLASSROOM 1950s PROMOTIONAL MOVIE",
            description=_page(tokens=604, carrying="the sound of the human brain at rest"),
        )
        ranked = _rank(BRAIN, candidate)
        self.assertLess(ranked["subject_match"], 99.0)
        self.assertTrue(ranked["rejected"])

    def test_a_record_with_no_metadata_is_not_rescued(self) -> None:
        candidate = _candidate("silent", title="", description="", tags=[], keywords=[])
        ranked = _rank(BRAIN, candidate)
        self.assertTrue(ranked["rejected"])
        self.assertNotIn(ranked["support_status"], SOFT_REJECT_ELIGIBLE)


class NothingElseBecomesSofter(unittest.TestCase):
    """Every refusal that is not the average stays exactly as hard as it was."""

    def test_must_avoid_still_disqualifies(self) -> None:
        scene = SemanticScene(
            scene_id="s",
            subject=["human brain"],
            action=["glowing anatomical model"],
            environment=["dark studio"],
            visual_priority="exact_action",
            must_not_include=["cartoon"],
        )
        candidate = _candidate(
            "banned",
            title="Animation of the human brain, a cartoon for children",
        )
        ranked = _rank(scene, candidate)
        self.assertIn("cartoon", list(ranked["negative_matches"]))
        self.assertTrue(ranked["rejected"])
        self.assertEqual(SUPPORT_UNSUPPORTED, ranked["support_status"])

    def test_an_exacting_class_still_refuses_silence(self) -> None:
        """A class defined by refusing to guess does not get "silence is not a no".

        ``specific_object`` sets ``requires_provider_metadata``. The C89 case is the
        measured one: ``панель`` is both a solar panel and a car dashboard, the
        dashboard's title names the subject in a bounded field, and the assembly and
        the factory are simply unmentioned - the exact shape this slice rescues
        everywhere else. Here it must stay refused, because the class asked to be shown.
        """
        scene = SemanticScene(
            scene_id="scene_solar_panel_assembly",
            subject=["панель"],
            action=["сборка"],
            environment=["завод"],
            source_class="specific_object",
        )
        dashboard = _candidate(
            "stock_car_dashboard",
            provider="pexels",
            title="Панель приборов автомобиля",
            description="Панель приборов и руль автомобиля крупным планом",
        )
        ranked = _rank(scene, dashboard, source_class="specific_object")
        self.assertEqual(100.0, ranked["subject_match"])
        self.assertEqual(0.0, ranked["action_match"])
        self.assertTrue(ranked["rejected"])

    def test_conflicting_context_still_blocks_the_automatic_match(self) -> None:
        scene = SemanticScene(
            scene_id="s",
            subject=["human brain"],
            action=["glowing anatomical model"],
            environment=["dark studio"],
            visual_priority="exact_action",
            conflicting_context=["mars mission"],
        )
        candidate = _candidate(
            "conflicted",
            title="Human brain scanned during a mars mission press day",
        )
        ranked = _rank(scene, candidate)
        self.assertTrue(ranked["rejected"])

    def test_rights_still_block(self) -> None:
        ranked = _rank(BRAIN, _candidate("blocked", allowed_for_render=False))
        self.assertTrue(ranked["rejected"])
        self.assertIn("rights_not_allowed", list(ranked["blocking_reject_reasons"] or []))

    def test_duration_still_blocks(self) -> None:
        candidate = _candidate("short", media_type="video", duration_sec=1.0)
        ranked = _rank(BRAIN, candidate, required_duration_sec=12.0)
        self.assertTrue(ranked["rejected"])
        self.assertTrue(
            [r for r in (ranked["blocking_reject_reasons"] or []) if r.startswith("duration_deficit")]
        )

    def test_entertainment_footage_policy_still_blocks(self) -> None:
        candidate = _candidate(
            "toon",
            media_type="video",
            title="Human brain cartoon episode for children",
            duration_sec=60.0,
        )
        ranked = _rank(BRAIN, candidate)
        self.assertTrue(ranked["rejected"])
        self.assertTrue(
            [
                r
                for r in (ranked["blocking_reject_reasons"] or [])
                if r.startswith("non_real_video_footage")
            ]
        )

    def test_a_class_that_requires_the_place_still_refuses_silence(self) -> None:
        """``exact_location`` asks for action and location; UNKNOWN there is still fatal.

        This is the safety property the measurement turned on: all of corpus v1's
        ``exact_location`` scenes match the predicate and every one of them stays
        refused by ``required_slot_missing``.
        """
        scene = SemanticScene(
            scene_id="s",
            subject=["penguin"],
            action=["swimming"],
            environment=["antarctic coast"],
            location=["antarctic coast"],
            visual_priority="exact_action",
            source_class="exact_location",
        )
        candidate = _candidate("penguin", title="A penguin")
        ranked = _rank(scene, candidate, source_class="exact_location")
        self.assertTrue(ranked["rejected"])
        self.assertTrue(
            [
                r
                for r in (ranked["blocking_reject_reasons"] or [])
                if r.startswith("required_slot_missing")
            ]
        )


if __name__ == "__main__":
    unittest.main()
