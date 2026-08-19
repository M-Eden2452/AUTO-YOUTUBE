"""Class 5 of PLAN-9D: meaning does not separate the survivors, and no record said so.

Measured input, not a guess. On the two frozen corpora, among the scenes that still
have two or more selectable candidates after the gates, the first two carry an
*identical* reading of every requirement the scene stated - the same
``subject_match``/``action_match``/``environment_match``/``camera_match``, the same
``semantic_score``, the same ``support_status``/``slot_verdict``, the same
``fallback_level``, the same shot-scale adjustment. v2: 5 such scenes of the 9 with
two or more survivors. v1: 6 (a seventh, ``scene_006``, ties on ``semantic_score``
alone - there ``C99``'s shot-scale signal really does separate the two, which is why
it is counted apart rather than folded in).

What broke those ties instead:

* ``0.075 * vertical_score`` - the declared width and height. In
  ``live_5/scene_004`` the whole margin is **0.001** of ``final_score``, produced by
  2204x3307 against 2208x3312: four pixels of declared height;
* nothing at all, in three scenes across the two corpora
  (``plan9d_current_capture_v1/scene_010``, ``plan9d_current_capture_v1/scene_011``,
  ``local_after_fix/scene_002``). Every candidate in the group carries exactly the
  same ``final_score``, and the winner is whichever the manifest recorded first.

Two rules were tried against the same evidence before this one and measured out,
recorded here so a later edit does not re-propose them:

* *corroboration across the record's own fields* ("does the title agree with the
  tags") - after de-duplicating identical field text, a pexels record has **one**
  distinct field (title, description, tags and keywords carry the same sentence) and
  a wikimedia record has **three**. Counting agreeing fields would score the
  provider's export format, not the evidence;
* *specificity* ("how much of the record is about something else") - in
  ``live_5/scene_004`` it orders a 20-word keyword dump about drills above a 25-word
  one about smartphones, on dump length. Neither dump says anything about the frame.

So this file does not add a preference. It asserts that the ranker **names** the
group meaning could not split and **names what actually broke the order**, instead of
returning a confident winner with the reason invisible. The rule is deliberately
allowed to leave exact equalities standing - it may not leave them silent.

Selection itself is unchanged, and ``SelectionIsUnchangedTests`` is what proves it:
``_ranking_key``, ``final_score`` and ``semantic_score`` are untouched, so the frozen
acceptance numbers in ``tests/test_plan9d_ground_truth_baseline.py`` cannot move.

Not covered here: the ``blind agreement`` ratios, which stay in that baseline file
with every other PLAN-9D measurement; and the cross-script bridge, which is the one
place where a tied pair really does carry distinguishing evidence
(``local_after_fix/scene_002``: three Russian titles that differ exactly on the
scene's ``environment`` and ``action``, unreadable against an English requirement).
That is ``C105``'s second half and is out of this slice.
"""

from __future__ import annotations

import unittest
from pathlib import Path
from typing import Any

from src.assets.semantic_selection.candidate_ranker import (
    SUPPORT_RANK,
    TIE_BROKEN_BY_INPUT_ORDER,
    TIE_BROKEN_BY_NON_MEANING_SCORE,
    rank_candidates,
)
from src.assets.semantic_selection.models import SemanticScene
from tests.plan9d_corpus_builder import RANKER_OUTPUT_KEYS
from tests.plan9d_ground_truth import load_current_corpus, scene_from_corpus

CORPUS_V1 = Path("tests/data/plan9d/current_corpus_v1.json")
CORPUS_V2 = Path("tests/data/plan9d/current_corpus_v2.json")


def _candidate(
    asset_id: str,
    *,
    title: str = "",
    description: str = "",
    width: int = 1080,
    height: int = 1920,
    tags: list[str] | None = None,
    **extra: Any,
) -> dict[str, Any]:
    candidate: dict[str, Any] = {
        "asset_id": asset_id,
        "provider": "fake",
        "media_type": "image",
        "title": title,
        "description": description,
        "tags": list(tags or []),
        "width": width,
        "height": height,
        "rights_status": "public_domain",
        "allowed_for_render": True,
    }
    candidate.update(extra)
    return candidate


def _ranked(scene: SemanticScene, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return rank_candidates(scene, candidates, source_class="generic_broll")


def _by_id(ranked: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(item["asset_id"]): item for item in ranked}


class MeaningTieDisclosureTests(unittest.TestCase):
    """The record says which candidates meaning could not tell apart, and why it chose."""

    def test_two_records_meaning_reads_identically_name_each_other(self) -> None:
        scene = SemanticScene(
            scene_id="s1", subject=["solar panel"], action=["capturing sunlight"]
        )
        ranked = _ranked(
            scene,
            [
                _candidate("a", title="solar panel capturing sunlight", width=2204, height=3307),
                _candidate("b", title="solar panel capturing sunlight", width=2208, height=3312),
            ],
        )
        items = _by_id(ranked)
        self.assertEqual(items["a"]["semantic_score"], items["b"]["semantic_score"])
        self.assertEqual(["b"], list(items["a"]["meaning_tie_peers"]))
        self.assertEqual(["a"], list(items["b"]["meaning_tie_peers"]))

    def test_a_different_framing_verdict_is_not_a_meaning_tie(self) -> None:
        """The guard against calling the group wider than meaning actually made it.

        1080x1920 is ``vertical_ready`` and fully supported; 1200x1920 needs a crop and
        is only manually confirmable. That is a different answer to the scene, not the
        same one ordered by pixels, and the two must not be named as peers.
        """

        scene = SemanticScene(scene_id="s1", subject=["solar panel"])
        ranked = _ranked(
            scene,
            [
                _candidate("ready", title="solar panel in full sun", width=1080, height=1920),
                _candidate("cropped", title="solar panel in full sun", width=1200, height=1920),
            ],
        )
        items = _by_id(ranked)
        self.assertNotEqual(
            items["ready"]["support_status"], items["cropped"]["support_status"]
        )
        self.assertEqual([], list(items["ready"]["meaning_tie_peers"]))
        self.assertEqual([], list(items["cropped"]["meaning_tie_peers"]))

    def test_a_tie_broken_by_declared_pixels_is_named_as_such(self) -> None:
        """The ``live_5/scene_004`` shape: same meaning, different declared frame."""

        scene = SemanticScene(scene_id="s1", subject=["battery pack"])
        ranked = _ranked(
            scene,
            [
                _candidate("wide", title="battery pack on a bench", width=2204, height=3307),
                _candidate("tall", title="battery pack on a bench", width=2208, height=3312),
            ],
        )
        items = _by_id(ranked)
        self.assertEqual(
            0.001, round(items["wide"]["final_score"] - items["tall"]["final_score"], 3)
        )
        for asset_id in ("wide", "tall"):
            self.assertEqual(
                TIE_BROKEN_BY_NON_MEANING_SCORE, items[asset_id]["meaning_tie_broken_by"]
            )

    def test_an_exact_equality_is_named_instead_of_handed_to_input_order(self) -> None:
        """The ``local_after_fix/scene_002`` shape: nothing separates them at all."""

        scene = SemanticScene(scene_id="s1", subject=["battery pack"])
        ranked = _ranked(
            scene,
            [
                _candidate("first", title="battery pack on a bench"),
                _candidate("second", title="battery pack on a bench"),
                _candidate("third", title="battery pack on a bench"),
            ],
        )
        items = _by_id(ranked)
        self.assertEqual(1, len({item["final_score"] for item in ranked}))
        for asset_id in ("first", "second", "third"):
            self.assertEqual(
                TIE_BROKEN_BY_INPUT_ORDER, items[asset_id]["meaning_tie_broken_by"]
            )
            self.assertEqual(2, len(items[asset_id]["meaning_tie_peers"]))

    def test_a_candidate_meaning_distinguishes_names_no_peer(self) -> None:
        scene = SemanticScene(
            scene_id="s1", subject=["solar panel"], action=["capturing sunlight"]
        )
        ranked = _ranked(
            scene,
            [
                _candidate("exact", title="solar panel capturing sunlight"),
                _candidate("partial", title="solar panel on a roof"),
            ],
        )
        items = _by_id(ranked)
        self.assertNotEqual(items["exact"]["semantic_score"], items["partial"]["semantic_score"])
        for asset_id in ("exact", "partial"):
            self.assertEqual([], list(items[asset_id]["meaning_tie_peers"]))
            self.assertEqual("", items[asset_id]["meaning_tie_broken_by"])

    def test_a_refused_candidate_is_not_a_peer_because_it_is_not_competing(self) -> None:
        scene = SemanticScene(
            scene_id="s1", subject=["battery pack"], must_not_include=["smartphone"]
        )
        ranked = _ranked(
            scene,
            [
                _candidate("kept", title="battery pack on a bench"),
                _candidate("banned", title="battery pack beside a smartphone"),
            ],
        )
        items = _by_id(ranked)
        self.assertTrue(items["banned"]["rejected"])
        self.assertEqual([], list(items["kept"]["meaning_tie_peers"]))
        self.assertEqual([], list(items["banned"]["meaning_tie_peers"]))
        self.assertEqual("", items["banned"]["meaning_tie_broken_by"])

    def test_the_two_keys_exist_on_every_record_including_refused_ones(self) -> None:
        scene = SemanticScene(scene_id="s1", subject=["battery pack"])
        ranked = _ranked(
            scene,
            [_candidate("a", title="battery pack"), _candidate("b", title="nothing relevant")],
        )
        for item in ranked:
            self.assertIn("meaning_tie_peers", item)
            self.assertIn("meaning_tie_broken_by", item)

    def test_the_new_keys_are_declared_as_ranker_output(self) -> None:
        """C120: a ranker verdict fed back into a rebuilt corpus is not provider evidence."""

        self.assertLessEqual(
            {"meaning_tie_peers", "meaning_tie_broken_by"}, set(RANKER_OUTPUT_KEYS)
        )


class SelectionIsUnchangedTests(unittest.TestCase):
    """What this slice is not allowed to move."""

    def test_a_must_avoid_hit_is_still_a_refusal_and_not_a_deduction(self) -> None:
        scene = SemanticScene(
            scene_id="s1", subject=["battery pack"], must_not_include=["smartphone"]
        )
        ranked = _ranked(scene, [_candidate("x", title="battery pack beside a smartphone")])
        item = ranked[0]
        self.assertTrue(item["rejected"])
        self.assertIn("must_avoid_match:smartphone", item["reject_reason"])
        self.assertIn("must_avoid_match:smartphone", item["blocking_reject_reasons"])

    def test_the_disqualifying_ban_stays_unconditional_on_provability(self) -> None:
        """C97, restated here because a tie rule is exactly where it could be softened."""

        scene = SemanticScene(
            scene_id="s1", subject=["battery pack"], must_not_include=["смартфон"]
        )
        ranked = _ranked(scene, [_candidate("x", title="battery pack beside a smartphone")])
        item = ranked[0]
        self.assertEqual([], item["negative_matches"])
        self.assertEqual(
            ["смартфон"],
            list(item["must_avoid_unverifiable"]),
        )
        self.assertNotIn("must_avoid_match", item["reject_reason"])

    def test_an_undecidable_field_stays_undecidable_and_is_not_scored_zero(self) -> None:
        scene = SemanticScene(
            scene_id="s1",
            subject=["solar panel"],
            action=["поглощает свет"],
        )
        ranked = _ranked(scene, [_candidate("x", title="solar panel on a roof")])
        item = ranked[0]
        self.assertIn("action", item["undecidable_fields"])
        self.assertGreater(item["semantic_score"], 0.0)

    def test_support_status_still_outranks_the_score(self) -> None:
        """A better-supported candidate stays first even when another scores higher.

        Asserted through ``SUPPORT_RANK`` rather than through the alphabet: sorting the
        status *strings* would put ``manual_confirmation_required`` above
        ``full_support`` and the test would pass while saying nothing.
        """

        scene = SemanticScene(
            scene_id="s1",
            subject=["solar panel"],
            must_include=["solar panel"],
            visual_priority="exact_subject",
        )
        ranked = _ranked(
            scene,
            [
                _candidate(
                    "supported",
                    title="solar panel in full sun",
                    width=1080,
                    height=1920,
                    watermark_penalty=30.0,
                ),
                _candidate(
                    "higher_scoring", title="solar panel in full sun", width=1200, height=1920
                ),
            ],
        )
        items = _by_id(ranked)
        self.assertGreater(
            items["higher_scoring"]["final_score"], items["supported"]["final_score"]
        )
        self.assertGreater(
            SUPPORT_RANK[items["supported"]["support_status"]],
            SUPPORT_RANK[items["higher_scoring"]["support_status"]],
        )
        self.assertEqual("supported", str(ranked[0]["asset_id"]))


class FrozenCorpusMeaningTieTests(unittest.TestCase):
    """The measurement this slice exists for, locked scene by scene on both corpora.

    Reads the corpora only. The owner's labels are the acceptance instrument and are
    deliberately not opened here: a rule fitted to them would measure itself.
    """

    #: Ranking v1 means scoring 1064 candidates; six test methods asking for it
    #: separately is six times the same work for the same frozen answer.
    _cache: dict[Path, dict[str, list[dict[str, Any]]]] = {}

    @classmethod
    def _survivors(cls, corpus_path: Path) -> dict[str, list[dict[str, Any]]]:
        if corpus_path not in cls._cache:
            cls._cache[corpus_path] = cls._rank_all(corpus_path)
        return cls._cache[corpus_path]

    @staticmethod
    def _rank_all(corpus_path: Path) -> dict[str, list[dict[str, Any]]]:
        corpus = load_current_corpus(corpus_path)
        out: dict[str, list[dict[str, Any]]] = {}
        for scene in corpus["scenes"]:
            ordered = sorted(scene["candidates"], key=lambda item: int(item["input_order"]))
            candidates = []
            for stored in ordered:
                candidate = dict(stored["candidate"])
                candidate["vision_tags"] = []
                candidates.append(candidate)
            ranked = rank_candidates(
                scene_from_corpus(scene),
                candidates,
                used_asset_ids=set(),
                required_duration_sec=float(scene.get("required_duration_sec") or 0.0),
                require_provider_metadata=bool(scene.get("require_provider_metadata")),
                source_class=str(scene.get("source_class") or ""),
            )
            out[str(scene["scene_key"])] = [item for item in ranked if not item.get("rejected")]
        return out

    def test_v2_names_the_five_scenes_meaning_could_not_split(self) -> None:
        survivors = self._survivors(CORPUS_V2)
        with_choice = {key: rows for key, rows in survivors.items() if len(rows) >= 2}
        self.assertEqual(9, len(with_choice))
        tied = {
            key: len(rows[0]["meaning_tie_peers"]) + 1
            for key, rows in with_choice.items()
            if rows[0]["meaning_tie_peers"]
        }
        self.assertEqual(
            {
                "live_5/scene_003": 2,
                "live_5/scene_004": 4,
                "local_after_fix/scene_001": 2,
                "local_after_fix/scene_002": 3,
                "local_after_fix/scene_005": 4,
            },
            tied,
        )

    def test_v1_names_the_six_scenes_meaning_could_not_split(self) -> None:
        survivors = self._survivors(CORPUS_V1)
        with_choice = {key: rows for key, rows in survivors.items() if len(rows) >= 2}
        self.assertEqual(8, len(with_choice))
        tied = {
            key: len(rows[0]["meaning_tie_peers"]) + 1
            for key, rows in with_choice.items()
            if rows[0]["meaning_tie_peers"]
        }
        self.assertEqual(
            {
                "plan9d_current_capture_v1/scene_001": 6,
                "plan9d_current_capture_v1/scene_002": 2,
                "plan9d_current_capture_v1/scene_009": 2,
                "plan9d_current_capture_v1/scene_010": 2,
                "plan9d_current_capture_v1/scene_011": 12,
                "plan9d_current_capture_v1/scene_013": 2,
            },
            tied,
        )

    def test_the_one_v1_scene_c99_really_does_separate_is_not_counted_as_tied(self) -> None:
        """``scene_006``: ``semantic_score`` ties, the shot-scale signal does not."""

        rows = self._survivors(CORPUS_V1)["plan9d_current_capture_v1/scene_006"]
        self.assertEqual(rows[0]["semantic_score"], rows[1]["semantic_score"])
        self.assertNotEqual(rows[0]["shot_scale_adjustment"], rows[1]["shot_scale_adjustment"])
        self.assertEqual([], list(rows[0]["meaning_tie_peers"]))

    def test_three_frozen_scenes_are_decided_by_nothing_but_input_order(self) -> None:
        decided: dict[str, str] = {}
        for path in (CORPUS_V1, CORPUS_V2):
            for key, rows in self._survivors(path).items():
                if rows and rows[0]["meaning_tie_broken_by"]:
                    decided[key] = str(rows[0]["meaning_tie_broken_by"])
        self.assertEqual(
            {
                "plan9d_current_capture_v1/scene_010": TIE_BROKEN_BY_INPUT_ORDER,
                "plan9d_current_capture_v1/scene_011": TIE_BROKEN_BY_INPUT_ORDER,
                "local_after_fix/scene_002": TIE_BROKEN_BY_INPUT_ORDER,
            },
            {
                key: value
                for key, value in decided.items()
                if value == TIE_BROKEN_BY_INPUT_ORDER
            },
        )

    def test_two_ten_thousandths_of_aspect_ratio_decide_live_5_scene_004(self) -> None:
        """One correction to the audit that named this scene, kept as a test.

        `PLAN_9D_SLICE_REACHABILITY_2026-08-19.md` §4 reads "2204x3307 against
        2208x3312 give ``vertical_score`` 89.603 against 89.583". Both scores are
        right and the 0.001 margin is right, but 2208x3312 is ``C1``, which ranks
        *third*. The record actually in second place is ``C7`` at 3840x5760 - the same
        2:3 ratio as ``C1``, hence the same ``vertical_score``, hence the same margin.
        The deciding quantity is two ten-thousandths of aspect ratio, which no count of
        pixels of any one record states. The audit's conclusion is untouched.
        """

        rows = self._survivors(CORPUS_V2)["live_5/scene_004"]
        first, second = rows[0], rows[1]
        self.assertEqual(TIE_BROKEN_BY_NON_MEANING_SCORE, first["meaning_tie_broken_by"])
        self.assertEqual(0.001, round(first["final_score"] - second["final_score"], 3))
        self.assertEqual((2204, 3307), (first["width"], first["height"]))
        self.assertEqual((3840, 5760), (second["width"], second["height"]))
        self.assertEqual(89.603, first["vertical_score"])
        self.assertEqual(89.583, second["vertical_score"])
        self.assertEqual(
            [(2208, 3312)], [(row["width"], row["height"]) for row in rows[2:3]]
        )


if __name__ == "__main__":
    unittest.main()
