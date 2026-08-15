from __future__ import annotations

import unittest

from src.assets.scene_strategy import CLASS_SPECIFIC_OBJECT
from src.assets.semantic_selection.candidate_ranker import rank_candidates
from src.assets.semantic_selection.evidence import (
    LOCAL_MATCH_MAX_GAP,
    METADATA_FIELDS,
    build_evidence,
)
from src.assets.semantic_selection.models import SemanticScene


def _candidate(
    asset_id: str,
    *,
    provider: str = "fake",
    title: str = "",
    description: str = "",
    tags: list[str] | None = None,
) -> dict[str, object]:
    return {
        "asset_id": asset_id,
        "provider": provider,
        "media_type": "image",
        "title": title,
        "description": description,
        "tags": list(tags or []),
        "tags_source": "provider",
        "width": 1080,
        "height": 1920,
        "allowed_for_render": True,
        "review_required": False,
        "rights_status": "licensed",
    }


def _rank(
    candidate: dict[str, object],
    *,
    subject: str,
    action: str = "",
    environment: str = "",
) -> dict[str, object]:
    scene = SemanticScene(
        scene_id="scene_metadata_evidence",
        subject=[subject] if subject else [],
        action=[action] if action else [],
        environment=[environment] if environment else [],
        source_class=CLASS_SPECIFIC_OBJECT,
    )
    return rank_candidates(scene, [candidate], source_class=scene.source_class)[0]


def _slot(result: dict[str, object], kind: str) -> dict[str, object]:
    decision = result["selection_decision"]
    assert isinstance(decision, dict)
    slots = decision["slots"]
    assert isinstance(slots, dict)
    details = slots["details"]
    assert isinstance(details, list)
    return next(item for item in details if item["kind"] == kind)


class MetadataEvidenceRepairTest(unittest.TestCase):
    def test_dispersed_multiword_tokens_are_not_full_strength_evidence(self) -> None:
        candidate = _candidate(
            "dispersed",
            title="Volcanic archive survey",
            description=(
                "A rare mineral was recorded during the first survey. "
                + "unrelated catalogue material " * 20
                + "Coastal weather observations followed many years later. "
                + "more unrelated catalogue material " * 20
                + "The final appendix indexes animal migration records."
            ),
        )

        result = _rank(candidate, subject="rare coastal animal")

        self.assertLess(result["subject_match"], 99.0)
        self.assertNotEqual(_slot(result, "subject")["status"], "matched")

    def test_direct_phrase_in_title_remains_full_strength(self) -> None:
        result = _rank(
            _candidate("direct", title="Rare coastal animal in its nesting grounds"),
            subject="rare coastal animal",
        )

        self.assertEqual(result["subject_match"], 100.0)
        self.assertEqual(_slot(result, "subject")["status"], "matched")

    def test_description_locality_window_accepts_documented_boundary(self) -> None:
        filler = " ".join(f"bridge{index}" for index in range(LOCAL_MATCH_MAX_GAP))
        result = _rank(
            _candidate(
                "local_boundary",
                title="Field observation",
                description=f"Rare {filler} coastal animal in view.",
            ),
            subject="rare coastal animal",
        )

        self.assertEqual(result["subject_match"], 100.0)

    def test_description_locality_window_rejects_one_token_beyond_boundary(self) -> None:
        filler = " ".join(
            f"bridge{index}" for index in range(LOCAL_MATCH_MAX_GAP + 1)
        )
        result = _rank(
            _candidate(
                "outside_boundary",
                title="Field observation",
                description=f"Rare {filler} coastal animal in view.",
            ),
            subject="rare coastal animal",
        )

        self.assertLess(result["subject_match"], 99.0)

    def test_explicit_single_word_entity_in_title_remains_full_strength(self) -> None:
        result = _rank(
            _candidate("single", title="Hummingbird feeding beside red flowers"),
            subject="hummingbird",
        )

        self.assertEqual(result["subject_match"], 100.0)
        self.assertEqual(_slot(result, "subject")["status"], "matched")

    def test_live4_lava_catalogue_prose_does_not_match_unusual_animals(self) -> None:
        # Deterministic extraction of the causal pattern in LIVE-4
        # internet_archive_galapagos_ast_2005306. The persisted description mentions
        # habitat, animals and unusual in different statements about a lava image.
        candidate = _candidate(
            "internet_archive_galapagos_ast_2005306",
            provider="internet_archive",
            title="Lava at Sierra Negra Summit: Image of the Day",
            description=(
                "The Sierra Negra volcano erupted and a thermal satellite recorded "
                "the lava flow. Once the lava cools it may eventually provide a "
                "habitat for Galapagos wildlife. "
                + "volcano observation and catalogue notes " * 30
                + "Today the animals on these islands count among the world's most "
                "unusual and colorful species."
            ),
            tags=["ASTER", "Terra"],
        )

        result = _rank(candidate, subject="unusual animals", environment="natural habitat")

        self.assertLess(result["subject_match"], 99.0)
        self.assertNotEqual(_slot(result, "subject")["status"], "matched")

    def test_live4_life_on_earth_catalogue_prose_does_not_match_hummingbird(self) -> None:
        # Deterministic extraction of the causal pattern in LIVE-4
        # internet_archive_life_on_earth: one animal mention inside a catalogue of a
        # complete television series is not evidence that the selected asset depicts it.
        candidate = _candidate(
            "internet_archive_life_on_earth",
            provider="internet_archive",
            title="Life On Earth BBC Nature series with complete episodes",
            description=(
                "This catalogue describes a complete natural-history television series. "
                + "Episode synopsis and production notes cover many unrelated species. " * 35
                + "One chapter mentions the elongated mouth of the hummingbird. "
                + "Further episode synopsis and production notes follow. " * 35
            ),
            tags=["Biology", "BBC Earth", "Complete Series", "Educational"],
        )

        result = _rank(candidate, subject="hummingbird", action="hovering midair")

        self.assertLess(result["subject_match"], 99.0)
        self.assertNotEqual(_slot(result, "subject")["status"], "matched")

    def test_live4_style_hummingbird_phrase_remains_strong(self) -> None:
        result = _rank(
            _candidate(
                "pexels_hummingbird",
                provider="pexels",
                title="Detailed photo of a hummingbird hovering midair",
            ),
            subject="hummingbird",
            action="hovering midair",
        )

        self.assertEqual(result["subject_match"], 100.0)
        self.assertEqual(result["action_match"], 100.0)
        self.assertEqual(_slot(result, "subject")["status"], "matched")
        self.assertEqual(_slot(result, "action")["status"], "matched")

    def test_live4_style_orca_title_remains_strong(self) -> None:
        result = _rank(
            _candidate(
                "pexels_orcas",
                provider="pexels",
                title="A pod of orcas swimming in the open ocean",
            ),
            subject="orcas",
        )

        self.assertEqual(result["subject_match"], 100.0)
        self.assertEqual(_slot(result, "subject")["status"], "matched")

    def test_coherent_metadata_outranks_provider_neutral_dispersed_prose(self) -> None:
        scene = SemanticScene(
            scene_id="scene_provider_neutral",
            subject=["glasswing butterfly"],
            source_class=CLASS_SPECIFIC_OBJECT,
        )
        dispersed = _candidate(
            "dispersed_generic",
            title="General natural history catalogue",
            description=(
                "Glasswing appears in an index entry. "
                + "unrelated archive prose " * 40
                + "A separate chapter describes butterfly migration."
            ),
        )
        coherent = _candidate(
            "coherent_generic",
            title="Glasswing butterfly resting on a green leaf",
        )

        ranked = rank_candidates(
            scene,
            [dispersed, coherent],
            source_class=scene.source_class,
        )

        self.assertEqual(ranked[0]["asset_id"], "coherent_generic")
        self.assertEqual(ranked[0]["subject_match"], 100.0)
        by_id = {item["asset_id"]: item for item in ranked}
        self.assertLess(by_id["dispersed_generic"]["subject_match"], 99.0)

    def test_metadata_fields_match_the_canonical_asset_contract(self) -> None:
        self.assertEqual(METADATA_FIELDS, ("title", "description"))
        evidence = build_evidence(
            {
                "categories": ["hummingbird"],
                "depicts": ["hummingbird"],
                "location": "open air",
            }
        )
        self.assertFalse(evidence.has_metadata)

    def test_provider_brand_does_not_change_semantic_or_final_score(self) -> None:
        scene = SemanticScene(
            scene_id="scene_provider_neutral_scores",
            subject=["hummingbird"],
            source_class=CLASS_SPECIFIC_OBJECT,
        )
        ranked = rank_candidates(
            scene,
            [
                _candidate("ia", provider="internet_archive", title="Hummingbird in flight"),
                _candidate("pexels", provider="pexels", title="Hummingbird in flight"),
            ],
            source_class=scene.source_class,
        )
        by_id = {item["asset_id"]: item for item in ranked}

        self.assertEqual(by_id["ia"]["subject_match"], by_id["pexels"]["subject_match"])
        self.assertEqual(by_id["ia"]["semantic_score"], by_id["pexels"]["semantic_score"])
        self.assertEqual(by_id["ia"]["final_score"], by_id["pexels"]["final_score"])
        self.assertNotEqual(by_id["ia"]["provider_confidence"], by_id["pexels"]["provider_confidence"])


class RussianMorphologyMatchingTest(unittest.TestCase):
    """C79 - the scene's own words, inflected, in the provider's own metadata.

    Extraction has always stemmed: ``visual_planning.entities`` groups ``панель`` and
    ``панелей`` under one key and picks the scene's subject from that group. Matching
    did not, and the two relations it did have cannot express Russian inflection - a
    literal comparison misses ``панелей`` outright, and the prefix relation misses it
    too, because Russian changes the character *at* the boundary (``ь`` becomes ``е``).

    Measured on the solar run these cases are written from: a local record whose title
    names the scene's subject in the genitive plural scored 7.5, and a car dashboard
    won the scene at 72.9 - on the strength of sharing one uninflected word.

    What this class does *not* claim is that the scene is now won. The repair reaches
    every question ``semantic_stem_score`` answers - the slot verdict, the support
    status, the required-slot refusal - and stops there, because the weighted average
    that gates ``score_below_*`` is still computed from the literal primitive. Both
    halves are pinned below, the closed one and the open one, so the open one cannot
    quietly be read as closed. See ``C79`` and ``C89`` in the cleanup registry.
    """

    RIGHT = "local_solar_assembly_line"
    WRONG = "stock_car_dashboard"

    def _scene(self, **overrides: list[str]) -> SemanticScene:
        return SemanticScene(
            scene_id="scene_solar_panel_assembly",
            subject=["панель"],
            action=["сборка"],
            environment=["завод"],
            source_class=CLASS_SPECIFIC_OBJECT,
            **overrides,
        )

    def _ranked(
        self, scene: SemanticScene
    ) -> tuple[dict[str, dict[str, object]], list[dict[str, object]]]:
        candidates = [
            _candidate(
                self.RIGHT,
                provider="local_library",
                title="Автоматизированная линия сборки солнечных панелей",
                description="Роботизированная линия сборки солнечных панелей на заводе",
            ),
            _candidate(
                self.WRONG,
                provider="pexels",
                title="Панель приборов автомобиля",
                description="Панель приборов и руль автомобиля крупным планом",
            ),
        ]
        ranked = rank_candidates(scene, candidates, source_class=scene.source_class)
        return {str(item["asset_id"]): item for item in ranked}, ranked

    def test_inflected_subject_is_a_matched_slot_not_an_absent_requirement(self) -> None:
        """Closed by C79: every question the stem primitive answers now answers it.

        The subject and the action are named by the metadata in another case, and the
        slot layer says so. An exacting class used to refuse this candidate outright
        for a requirement its own evidence met.
        """
        by_id, _ = self._ranked(self._scene())
        right = by_id[self.RIGHT]

        self.assertEqual(_slot(right, "subject")["status"], "matched")
        self.assertEqual(_slot(right, "action")["status"], "matched")
        decision = right["selection_decision"]
        assert isinstance(decision, dict)
        self.assertNotIn(
            "required_slot_missing:subject", decision["reject_reasons"]
        )
        self.assertEqual(right["slot_verdict"], "complete")

    def test_the_score_that_gates_selection_is_still_morphology_blind(self) -> None:
        """Open, and pinned so it stays visible: C89.

        ``candidate_ranker._field_match`` asks ``semantic_literal_score`` about the
        scene's *derived* description, so the average that gates ``score_below_*``
        still scores an inflected subject at zero. The consequence is the whole
        product defect: the slot layer calls the subject matched, the average calls it
        absent, the candidate stays ``unsupported`` and refused, and the record that
        merely shares an uninflected word outranks the one that names the subject.

        Making this a passing assertion rather than a fixed test is deliberate. The
        one-line swap to the stem primitive was measured against the frozen PLAN-9D
        ground truth and moved scene_009 off the annotator's preferred candidate, so
        it is not a change this slice may make on the way past.
        """
        by_id, ranked = self._ranked(self._scene())
        right = by_id[self.RIGHT]

        self.assertEqual(right["subject_match"], 0.0)
        self.assertTrue(right["rejected"])
        self.assertEqual(ranked[0]["asset_id"], self.WRONG)

    def test_english_prefix_variants_are_still_decided_by_the_prefix_relation(self) -> None:
        """``Antarctica``/``antarctic`` share no stem - only a prefix. Both survive.

        The stemmer strips Cyrillic endings only, so it reduces to plain equality on a
        Latin word. The repair is additive precisely so this case keeps its old answer:
        replacing the prefix relation with stem equality would have broken it.
        """
        result = _rank(
            _candidate(
                "antarctic_station",
                title="Research station on the antarctic plateau",
            ),
            subject="antarctica",
        )

        self.assertEqual(_slot(result, "subject")["status"], "matched")

    def test_english_words_that_merely_look_alike_are_still_refused(self) -> None:
        """``sampling``/``samples`` is the pair the module names as a non-match.

        Neither relation reaches it: they share no prefix, and the stemmer strips
        Cyrillic endings only, so on a Latin pair stem equality is plain equality.
        """
        result = _rank(
            _candidate("lab_sampling", title="Sampling procedure in the laboratory"),
            subject="samples",
        )

        self.assertNotEqual(_slot(result, "subject")["status"], "matched")

    def test_the_authors_literal_requirement_is_not_stemmed_with_the_rest(self) -> None:
        """``must_include`` stays verbatim. This repair is not a way around it.

        The same inflection the subject is now forgiven is still fatal here, because
        ``must_include`` is a statement about the frame that the author wrote, not a
        derived paraphrase of the scene.
        """
        by_id, _ = self._ranked(self._scene(must_include=["панель"]))
        right = by_id[self.RIGHT]
        decision = right["selection_decision"]
        assert isinstance(decision, dict)

        self.assertTrue(right["rejected"])
        self.assertIn("must_include_missing:панель", decision["reject_reasons"])

    def test_a_prohibition_written_in_another_case_is_still_a_prohibition(self) -> None:
        """``must_not_include`` is literal, and nothing here loosened it."""
        by_id, _ = self._ranked(self._scene(must_not_include=["панель"]))

        wrong = by_id[self.WRONG]
        decision = wrong["selection_decision"]
        assert isinstance(decision, dict)
        self.assertTrue(wrong["rejected"])
        self.assertIn("must_avoid_match:панель", decision["reject_reasons"])

    def test_a_declared_conflict_now_catches_its_own_inflections(self) -> None:
        """``conflicting_context`` already used the stem relation, so it moves too.

        It moves in the safe direction: a conflict the author declared is *found* in
        one more wording rather than missed. Recorded here so the change is not silent.
        """
        by_id, _ = self._ranked(self._scene(conflicting_context=["автомобиль"]))

        wrong = by_id[self.WRONG]
        decision = wrong["selection_decision"]
        assert isinstance(decision, dict)
        self.assertTrue(wrong["rejected"])
        self.assertIn("conflicting_context:автомобиль", decision["reject_reasons"])


if __name__ == "__main__":
    unittest.main()
