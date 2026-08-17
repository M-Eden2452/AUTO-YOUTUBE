from __future__ import annotations

import unittest

from src.assets.scene_strategy import CLASS_SPECIFIC_OBJECT
from src.assets.semantic_selection.candidate_ranker import rank_candidates
from src.assets.semantic_selection.evidence import (
    LOCAL_MATCH_MAX_GAP,
    METADATA_FIELDS,
    build_evidence,
    script_mismatch,
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

    C79 repaired the slot layer's half; C89 carried it to the weighted average that
    actually selects, so the scene is now won on the production path. What made C89 a
    slice of its own rather than a one-line swap is *which* tolerance the average may
    have: the ranker credits a confirmed shared stem and refuses the slot layer's prefix
    allowance. ``EnglishPrefixCreditGuardTest`` below is the other half of this pair and
    holds that line.

    What this class still does not claim is anything about English retrieval quality.
    The scene here is Russian and synthetic; the measured corpus (PLAN-9D, 14 scenes) is
    English and contains no inflection case at all.
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

    def test_the_score_that_gates_selection_reads_the_inflected_subject(self) -> None:
        """Closed by C89: the average that selects sees what the slot layer sees.

        This used to be the pinned open state. ``candidate_ranker._field_match`` asked
        ``semantic_literal_score`` about the scene's *derived* description, so the
        average that gates ``score_below_*`` scored an inflected subject at zero: the
        slot layer called the subject matched, the average called it absent, the
        candidate stayed refused, and the record that merely shares an uninflected word
        outranked the one that names the subject.

        It now asks ``semantic_inflection_score``, and the whole defect closes at once -
        the subject is a full match, the right record is not rejected, and it wins.
        Measured on this synthetic Russian case only; see the class docstring.
        """
        by_id, ranked = self._ranked(self._scene())
        right = by_id[self.RIGHT]

        self.assertEqual(right["subject_match"], 100.0)
        self.assertFalse(right["rejected"])
        self.assertEqual(ranked[0]["asset_id"], self.RIGHT)
        self.assertTrue(by_id[self.WRONG]["rejected"])

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


class EnglishPrefixCreditGuardTest(unittest.TestCase):
    """A guard, not a RED: green before C89 and green after it.

    Its job is to fail for the *next* person. The obvious way to close C89 was to point
    ``_field_match`` at the slot layer's ``semantic_stem_score``. That was written,
    measured and reverted: it moved PLAN-9D's ``scene_009`` off the annotator's preferred
    candidate (``preferred_matches`` 4 -> 3), and the cause was not the stemmer but the
    prefix relation, which credits ``power`` to ``powered``.

    The case below is that scene distilled to two candidates and one requirement, so the
    failure is visible without the frozen corpus:

    ================  ==========  ==========  =============
    relation          A (right)   B (wrong)   verdict
    ================  ==========  ==========  =============
    literal            33.33       33.33      tied
    stem + prefix      33.33       66.67      B wins on ``power`` in ``powered``
    stem only          33.33       33.33      tied - what ranking asks for
    ================  ==========  ==========  =============

    A shows a photovoltaic installation; B shows a portable light tower that merely runs
    *on* solar panels. Nothing here says the ranker should prefer A - the two are tied on
    this field and other evidence decides. It says only that ``powered`` may not be
    scored as evidence of a ``power plant``.
    """

    RIGHT = "photovoltaic_installation"
    WRONG = "portable_light_tower"

    def _ranked(self) -> dict[str, dict[str, object]]:
        scene = SemanticScene(
            scene_id="scene_solar_power_plant",
            subject=["solar power plant"],
            action=["aerial view of panel rows"],
            source_class=CLASS_SPECIFIC_OBJECT,
        )
        candidates = [
            _candidate(
                self.RIGHT,
                title="Photovoltaic panel at the National Solar Energy Center",
                description=(
                    "Solar cells on a photovoltaic panel at the National Solar Energy "
                    "Center in the Negev Desert."
                ),
            ),
            _candidate(
                self.WRONG,
                title="A portable light tower powered by solar panels",
                description=(
                    "A portable light tower powered by solar panels stands in a desert "
                    "landscape, showcasing renewable energy technology."
                ),
            ),
        ]
        ranked = rank_candidates(scene, candidates, source_class=scene.source_class)
        return {str(item["asset_id"]): item for item in ranked}

    def test_a_prefix_is_not_scored_as_evidence_of_the_word_it_prefixes(self) -> None:
        """``powered`` is not a ``power plant``, and ``panels`` is not ``panel rows``.

        Both fields are asserted, because the reverted change credited both: the subject
        through ``power`` in ``powered`` and the action through ``panel`` in ``panels``.
        """
        by_id = self._ranked()
        right, wrong = by_id[self.RIGHT], by_id[self.WRONG]

        self.assertEqual(33.333, right["subject_match"])
        self.assertEqual(33.333, wrong["subject_match"])
        self.assertEqual(0.0, wrong["action_match"])

    def test_the_wrong_candidate_does_not_outscore_the_right_one_on_the_subject(self) -> None:
        """The comparison the average actually makes, stated as a comparison.

        The numbers above pin today's arithmetic; this pins the property that survives a
        re-weighting - a candidate may not overtake on a field it only prefix-matches.
        """
        by_id = self._ranked()

        self.assertLessEqual(
            float(by_id[self.WRONG]["subject_match"]),
            float(by_id[self.RIGHT]["subject_match"]),
        )


class GluedEvidenceDecidabilityRepairTest(unittest.TestCase):
    """Closed by ``C91``: decidability is asked of the fields, not of the glued record.

    This class landed one commit earlier under the name
    ``GluedEvidenceDecidabilityCharacterizationTest`` and froze the *defect*, because
    neither ``script_mismatch`` nor ``is_undecidable`` was named by a single test module
    in this repository: the question "is this term comparable with this metadata at all"
    gated selection and was pinned nowhere. The numbers it recorded then are kept below
    beside the ones it asserts now, so the repair is readable as a difference rather
    than as a fresh set of expectations.

    Both primitives used to read ``CandidateEvidence.text``: every provider field glued
    into one string. Decidability was therefore a property of the *record*, while a
    match is a property of a *field* - and on a record written in two scripts those two
    readings disagreed. The case below is the disagreement at its plainest: an English
    title that states the subject verbatim, plus one Russian tag. The tag made the whole
    record "incomparable" with the English subject its own title names.

    ``BILINGUAL`` and ``ENGLISH_ONLY`` differ in exactly one thing - the language of the
    ``tags`` field. Nothing else, including every word the subject is matched against,
    changes between them. Before the repair that one tag cost the bilingual record 85
    points (``final_score`` 13.875 against 98.875), the ``subject`` slot (``undecidable``
    against ``matched``) and selection itself (``score_below_75``); with the subject also
    stated as ``must_include`` it was refused ``semantic_unverified:cooling tower`` for a
    requirement its title meets word for word. After it the two records are equal at
    98.875 and both are selectable, which is what "the language of a tag is not evidence
    about the frame" has to mean arithmetically.

    Two call sites had to move, and the second is why this is not a one-line repair:
    ``CandidateEvidence.is_undecidable`` now asks each field, and the ``must_include``
    loop in ``candidate_ranker`` now asks the evidence instead of calling the module
    primitive on the glued text itself. Measured with only the first applied: the
    requirement slot flips to ``matched`` while the rejection survives unchanged - the
    record still refused for a requirement it plainly meets, now without even a slot
    saying why. Both assertions of that test are kept for exactly this reason.

    ``script_mismatch`` itself is deliberately unchanged and still answers about the
    text it is handed - the glued text of this record really is written in two scripts.
    What changed is which text the selection path hands it.

    What this class does not claim: that the Russian direction is symmetric (it is not -
    see the last test), or anything about how often mixed records occur in the field.
    Two synthetic records prove a mechanism, not a rate.
    """

    SUBJECT = "cooling tower"
    TITLE = "Cooling tower at a power plant"
    DESCRIPTION = "Steam rising from the cooling tower of a thermal power plant"
    BILINGUAL = "bilingual_cooling_tower"
    ENGLISH_ONLY = "english_cooling_tower"

    def _candidates(self) -> list[dict[str, object]]:
        return [
            _candidate(
                self.BILINGUAL,
                provider="local_library",
                title=self.TITLE,
                description=self.DESCRIPTION,
                tags=["градирня", "тепловая электростанция"],
            ),
            _candidate(
                self.ENGLISH_ONLY,
                provider="local_library",
                title=self.TITLE,
                description=self.DESCRIPTION,
                tags=["cooling tower", "thermal power station"],
            ),
        ]

    def _ranked(self, **overrides: list[str]) -> dict[str, dict[str, object]]:
        scene = SemanticScene(
            scene_id="scene_bilingual_metadata",
            subject=[self.SUBJECT],
            source_class=CLASS_SPECIFIC_OBJECT,
            **overrides,
        )
        ranked = rank_candidates(scene, self._candidates(), source_class=scene.source_class)
        return {str(item["asset_id"]): item for item in ranked}

    def test_one_foreign_tag_no_longer_makes_a_record_incomparable_with_its_own_title(
        self,
    ) -> None:
        """The glued read still says "incomparable"; the primitive no longer asks it.

        All three asserted together on purpose. The first line is the unchanged module
        primitive answering about the string it is given, the second is the repair, and
        the map underneath is the reason the repair is sound rather than lenient: one
        field out of three is out of script, and two can answer.
        """
        evidence = build_evidence(self._candidates()[0])

        self.assertTrue(script_mismatch(self.SUBJECT, evidence.text))
        self.assertFalse(evidence.is_undecidable(self.SUBJECT))
        self.assertEqual(
            {"title": False, "description": False, "tags": True},
            {field.name: script_mismatch(self.SUBJECT, field.text) for field in evidence.fields},
        )

    def test_the_same_record_scores_a_full_match_on_every_reading_of_the_text(self) -> None:
        """Undecidable and 100.0 at once - the state the ranker then has to resolve.

        All three readings are asserted because the scoring path and the slot path ask
        different ones, and the contradiction is present in all of them.
        """
        evidence = build_evidence(self._candidates()[0])

        self.assertEqual(100.0, evidence.literal_score(self.SUBJECT))
        self.assertEqual(100.0, evidence.semantic_literal_score(self.SUBJECT))
        self.assertEqual(100.0, evidence.semantic_inflection_score(self.SUBJECT))

    def test_the_ranker_now_scores_the_two_records_the_same(self) -> None:
        """The 85-point gap between two records that differ by one tag's language.

        ``subject_match`` was 100.0 on both records before the repair too - the field
        comparison finds the subject in the English title either way. What differed was
        ``semantic_score``: the scene's only stated field was undecidable, so the
        weighted average was zeroed and ``final_score`` 13.875 was the technical part
        alone, below the selection threshold. Equality here is the assertion; the
        absolute 98.875 is pinned with it so that a change of weights cannot make the
        two records equal by moving both.
        """
        by_id = self._ranked()
        bilingual, english = by_id[self.BILINGUAL], by_id[self.ENGLISH_ONLY]

        self.assertEqual(100.0, bilingual["subject_match"])
        self.assertEqual(100.0, english["subject_match"])
        self.assertEqual(100.0, bilingual["semantic_score"])
        self.assertEqual(100.0, english["semantic_score"])
        self.assertEqual(98.875, bilingual["final_score"])
        self.assertEqual(98.875, english["final_score"])
        self.assertFalse(bilingual["rejected"])
        self.assertFalse(english["rejected"])
        self.assertEqual("", bilingual["reject_reason"])
        self.assertEqual("matched", _slot(bilingual, "subject")["status"])

    def test_a_requirement_the_title_states_verbatim_is_accepted(self) -> None:
        """The author's own ``must_include``, present in the title, honoured.

        The second call site: the ``must_include`` loop used to call the module
        primitive on the glued text and refuse the record for a requirement its title
        meets word for word. Both lines are asserted because they moved apart under a
        method-only repair - the slot flipped while the rejection stayed - so the second
        line is what proves the loop itself was moved and not just its neighbour.
        """
        by_id = self._ranked(must_include=[self.SUBJECT])
        decision = by_id[self.BILINGUAL]["selection_decision"]
        assert isinstance(decision, dict)

        self.assertEqual([], decision["reject_reasons"])
        self.assertEqual("matched", _slot(by_id[self.BILINGUAL], "requirement")["status"])
        english_decision = by_id[self.ENGLISH_ONLY]["selection_decision"]
        assert isinstance(english_decision, dict)
        self.assertEqual([], english_decision["reject_reasons"])

    def test_the_russian_direction_of_the_same_record_is_already_decidable(self) -> None:
        """A guard: the defect is one-directional, and the repair must not invert it.

        Against the same bilingual record a Russian subject is comparable today - the
        glued text carries Cyrillic - and stays comparable under a per-field read,
        because the Russian ``tags`` field answers. Pinned so that a repair aimed at
        the English direction is not allowed to break this one on the way.
        """
        evidence = build_evidence(self._candidates()[0])

        self.assertFalse(script_mismatch("градирня", evidence.text))
        self.assertFalse(evidence.is_undecidable("градирня"))
        self.assertFalse(
            all(script_mismatch("градирня", field.text) for field in evidence.fields)
        )


if __name__ == "__main__":
    unittest.main()
