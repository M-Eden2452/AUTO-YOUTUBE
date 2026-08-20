"""C126: a phrase inside a catalogue page is not the same claim as a title that names it.

Measured 2026-08-20 on the saved runs ``projects/2026-08-20_sleep-anchor-recheck`` and
``projects/2026-08-20_sleep-viz-probe`` (offline, from the stored manifests, no provider
call). Two records of the same scene:

- ``scene_004``, subject ``human brain``. ``wikimedia_142165496`` is titled *Animation of
  the anatomy and physiology of the human brain*; ``internet_archive_60034BringTheWorld
  ToYourClassroomVwr`` is a 1950s promotional reel whose 604-token catalogue description
  says ``the sound of the human brain at rest`` once, and whose title and tags say
  nothing about a brain. Both scored ``subject_match = 100.0`` and both scored
  ``semantic_score = 58.824`` - four candidates of that scene shared one number.
- ``scene_010``, subject ``closed eyes``. The run's highest score, **90.588**, went to
  ``internet_archive_TribalMedicinesOfChhattisgarhAndOdisha...``: its title says nothing,
  its 2412-token description says nothing, and a **1370-token** keyword dump carries
  ``closed eyes`` and ``bed``. A keyword dump that size was read as a bounded provider
  label and scored at full strength with no locality window at all.

The rule this file pins is not "refuse a scattered match". Most full-strength scatter is
correct - ``a woman sleeping in a bed`` really does answer the subject ``sleeping
woman`` - and the repair must keep it. What is pinned is that a field large enough to be
a catalogue page cannot *name* what one asset shows; it can only support the claim.

Fixtures carry the real wording of those records so the numbers stay traceable. The rule
under test knows nothing about sleep, brains or eyes.
"""

from __future__ import annotations

import unittest
from typing import Any

from src.assets.semantic_selection import SemanticScene, rank_candidates
from src.assets.semantic_selection.decision import (
    SLOT_CONFLICTING,
    VERDICT_CONFLICTING,
    build_slot_verdict,
)
from src.assets.semantic_selection.evidence import build_evidence


def _page(*, tokens: int, carrying: str = "") -> str:
    """Deterministic filler the size of a catalogue page, with no bearing on any scene.

    ``internet_archive`` descriptions in the saved runs are 604 - 43496 tokens; the
    largest field any provider writes about one single asset is 100.
    """
    filler = [f"catalogue{index}" for index in range(tokens)]
    if carrying:
        filler[tokens // 2 : tokens // 2] = carrying.split()
    return " ".join(filler)


def _candidate(asset_id: str, **fields: Any) -> dict[str, Any]:
    candidate: dict[str, Any] = {
        "asset_id": asset_id,
        "provider": "wikimedia",
        "media_type": "image",
        "title": "",
        "description": "",
        "tags": [],
        "keywords": [],
        "width": 2160,
        "height": 3840,
        "allowed_for_render": True,
        "license": "cc-by-4.0",
    }
    candidate.update(fields)
    return candidate


def _subject_match(scene: SemanticScene, candidate: dict[str, Any]) -> float:
    return float(rank_candidates(scene, [dict(candidate)])[0]["subject_match"])


BRAIN = SemanticScene(
    scene_id="scene_004",
    subject=["human brain"],
    action=["glowing anatomical model"],
    environment=["dark studio"],
)
EYES = SemanticScene(
    scene_id="scene_010",
    subject=["closed eyes"],
    action=["eyes moving under closed eyelids"],
    environment=["bed"],
)

#: The four ``scene_004`` records, in the shape the stored manifest holds them.
NAMED_IN_TITLE = _candidate(
    "wikimedia_142165496",
    title="Animation of the anatomy and physiology of the human brain AS.webm",
    description=(
        "animation of the anatomy and physiology of the human brain showing the "
        "cerebral hemispheres, brain stem and cerebellum, surrounded by arteries, "
        "venous sinuses and small blood vessels."
    ),
)
LISTED_IN_LABELS = _candidate(
    "pixabay_video_4122",
    provider="pixabay",
    title="pixabay video 4122",
    tags=[
        "skull", "cat scan", "medical", "anatomy", "x-ray", "human", "head", "brain",
        "patient", "examination", "cranium", "ct", "scan", "healthcare", "body",
    ],
)
MENTIONED_IN_A_PAGE = _candidate(
    "internet_archive_60034BringTheWorldToYourClassroomVwr",
    provider="internet_archive",
    title="USE OF 16mm EDUCATIONAL FILMS IN THE CLASSROOM 1950s PROMOTIONAL MOVIE 60034",
    description=_page(tokens=604, carrying="the sound of the human brain at rest"),
    tags=["classroom", "16mm", "educational", "film"],
)
MENTIONED_IN_A_LONGER_PAGE = _candidate(
    "internet_archive_BrainPartsSongVideoByAaronWolf",
    provider="internet_archive",
    title="Brain Parts Song by Aaron Wolf",
    description=_page(tokens=1092, carrying="parts of the human being and the brain"),
    tags=["brain", "anatomy", "song", "memory", "movement", "balance", "learning"],
)


class ACatalogueMentionIsNotANaming(unittest.TestCase):
    """Requirement 1: the same phrase, in two fields of different size."""

    def test_a_title_that_names_the_subject_beats_a_mention_in_a_catalogue_page(
        self,
    ) -> None:
        named = _subject_match(BRAIN, NAMED_IN_TITLE)
        mentioned = _subject_match(BRAIN, MENTIONED_IN_A_PAGE)
        self.assertEqual(100.0, named)
        self.assertLess(mentioned, named)

    def test_a_keyword_dump_the_size_of_a_page_cannot_name_the_subject(self) -> None:
        """``scene_010``'s top score came from a 1370-token keyword dump."""
        dump = _page(tokens=1370, carrying="closed eyes bed").split()
        candidate = _candidate(
            "internet_archive_TribalMedicines",
            provider="internet_archive",
            title="Tribal Medicines of Chhattisgarh and Odisha",
            description=_page(tokens=2412),
            keywords=dump,
            tags=dump,
        )
        self.assertLess(_subject_match(EYES, candidate), 100.0)

    def test_the_same_phrase_in_a_field_written_about_one_asset_is_still_full(
        self,
    ) -> None:
        """Nothing here punishes a real description; only a field that is a page."""
        described = _candidate(
            "wikimedia_197516596",
            title="Depressed woman lying on bed in a cozy indoor setting.jpg",
            description=(
                "a woman rests on a bed, her eyes closed and hair tousled. she wears a "
                "grey shirt and is surrounded by soft pillows and blankets."
            ),
        )
        self.assertEqual(100.0, _subject_match(EYES, described))


class WordOrderInsideAShortStrongFieldIsStillAFullMatch(unittest.TestCase):
    """Requirement 2: 30 of the 43 full subject matches in the run were scattered.

    Most of them are correct, and the repair must not reach them.
    """

    SLEEPER = SemanticScene(scene_id="scene_001", subject=["sleeping woman"])

    def test_a_permuted_phrase_in_a_short_title_is_a_full_match(self) -> None:
        for text in (
            "a woman sleeping in a bed",
            "close-up of a young woman sleeping peacefully in warm light",
            "asian woman peacefully resting on bed, sleeping",
        ):
            with self.subTest(text=text):
                self.assertEqual(
                    100.0, _subject_match(self.SLEEPER, _candidate("a1", title=text))
                )

    def test_a_permuted_phrase_in_a_short_label_list_is_a_full_match(self) -> None:
        candidate = _candidate(
            "a2",
            provider="pixabay",
            title="pixabay image 5275512",
            tags=["portrait", "woman", "people", "person", "sleeping", "model", "hair"],
        )
        self.assertEqual(100.0, _subject_match(self.SLEEPER, candidate))


class SilenceCannotOutrankANaming(unittest.TestCase):
    """Requirement 3."""

    SILENT = _candidate("silent", title="", description="", tags=[], keywords=[])

    def test_a_record_without_metadata_scores_below_one_that_names_the_subject(
        self,
    ) -> None:
        self.assertLess(
            _subject_match(BRAIN, self.SILENT), _subject_match(BRAIN, NAMED_IN_TITLE)
        )

    def test_a_record_without_metadata_scores_below_a_catalogue_mention(self) -> None:
        self.assertLess(
            _subject_match(BRAIN, self.SILENT), _subject_match(BRAIN, MENTIONED_IN_A_PAGE)
        )


class EvidenceThatDiffersMustNotProduceOneScore(unittest.TestCase):
    """Requirement 4: ``scene_004`` returned 58.824 for all four of these records."""

    GROUP = [
        NAMED_IN_TITLE,
        LISTED_IN_LABELS,
        MENTIONED_IN_A_PAGE,
        MENTIONED_IN_A_LONGER_PAGE,
    ]

    def _scores(self) -> dict[str, float]:
        ranked = rank_candidates(BRAIN, [dict(item) for item in self.GROUP])
        return {str(item["asset_id"]): float(item["semantic_score"]) for item in ranked}

    def test_the_group_no_longer_shares_a_single_semantic_score(self) -> None:
        scores = self._scores()
        self.assertGreaterEqual(
            len(set(scores.values())),
            2,
            f"evidence differs but every candidate scored the same: {scores}",
        )

    def test_the_record_that_names_the_subject_leads_the_group(self) -> None:
        scores = self._scores()
        self.assertGreater(
            scores["wikimedia_142165496"],
            scores["internet_archive_60034BringTheWorldToYourClassroomVwr"],
        )
        self.assertGreater(
            scores["wikimedia_142165496"],
            scores["internet_archive_BrainPartsSongVideoByAaronWolf"],
        )


class NoRefusalBecomesSofter(unittest.TestCase):
    """Requirement 5: negative evidence and rights are untouched by this slice."""

    def test_must_avoid_still_disqualifies_when_the_term_is_in_a_page(self) -> None:
        scene = SemanticScene(
            scene_id="s", subject=["human brain"], must_not_include=["cartoon"]
        )
        candidate = _candidate(
            "banned",
            provider="internet_archive",
            title="Animation of the human brain",
            description=_page(tokens=900, carrying="a cartoon for children"),
        )
        ranked = rank_candidates(scene, [candidate])[0]
        self.assertIn("cartoon", list(ranked["negative_matches"]))
        self.assertTrue(ranked["rejected"])

    def test_conflicting_context_still_conflicts_when_stated_in_a_page(self) -> None:
        scene = SemanticScene(
            scene_id="s",
            subject=["human brain"],
            conflicting_context=["mars mission"],
        )
        candidate = _candidate(
            "conflicted",
            provider="internet_archive",
            title="Animation of the human brain",
            description=_page(tokens=900, carrying="filmed at a mars mission press day"),
        )
        verdict = build_slot_verdict(scene, build_evidence(candidate))
        self.assertEqual(VERDICT_CONFLICTING, verdict.verdict)
        self.assertTrue(
            [slot for slot in verdict.slots if slot.status == SLOT_CONFLICTING]
        )

    def test_a_rights_refusal_stays_a_refusal(self) -> None:
        candidate = _candidate(
            "blocked",
            title="Animation of the anatomy and physiology of the human brain",
            allowed_for_render=False,
            license="",
            rights_status="unknown",
        )
        ranked = rank_candidates(BRAIN, [candidate])[0]
        self.assertTrue(ranked["rejected"])
        self.assertIn(
            "rights_not_allowed", list(ranked["blocking_reject_reasons"] or [])
        )


if __name__ == "__main__":
    unittest.main()
