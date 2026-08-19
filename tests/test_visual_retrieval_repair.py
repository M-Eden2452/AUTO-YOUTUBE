"""Stage Q2.1: the parts of visual retrieval that the first real run proved broken.

Every defect below was observed in a confirmed end-to-end run, not imagined:
eight scenes, eight downloaded files, zero of them showing what the scene was about.
Each test names the mechanism it pins down. No network, no paid API, no downloads.
"""

from __future__ import annotations

import unittest

from src.assets.query_adapter import (
    SOURCE_BRIEF_FIELDS,
    SOURCE_EXPLICIT,
    SOURCE_GLOSSARY,
    SOURCE_SAME_LANGUAGE,
    STATUS_LANGUAGE_UNSUPPORTED,
    STATUS_OK,
    STATUS_TRANSLATION_REQUIRED,
    build_scene_queries,
    provider_query_languages,
)
from src.assets.scene_strategy import (
    CLASS_DATA_INFOGRAPHIC,
    CLASS_EXACT_LOCATION,
    CLASS_GENERIC_BROLL,
    CLASS_SCIENTIFIC_EQUIPMENT,
    build_strategy,
    classify_scene,
)
from src.assets.semantic_selection import SemanticScene, rank_candidates
from src.assets.semantic_selection.decision import build_slot_verdict
from src.assets.semantic_selection.evidence import build_evidence
from src.content.script_engine import ScriptConstraints, ScriptRequest, generate_script
from src.content.visual_planning.brief import apply_brief, parse_brief
from src.content.visual_planning.models import SceneVisualPlan

ALL_PROVIDERS = ["local_library", "pexels", "pixabay", "wikimedia", "nasa_images", "internet_archive"]

ANTARCTIC_BRIEF = {
    "subject": "barren polar valley",
    "action": "wide aerial pan",
    "place": "McMurdo Dry Valleys Antarctica",
    "exact_entities": ["McMurdo Dry Valleys", "Antarctica"],
    "must_avoid": ["tropical forest", "green vegetation", "city", "beach resort", "penguin"],
    "source_class": "exact_location",
    "shot_type": "establishing",
}
LAB_BRIEF = {
    "subject": "mass spectrometer",
    "action": "sample analysis",
    "place": "laboratory",
    "exact_entities": ["mass spectrometer"],
    "must_avoid": ["beauty salon", "cosmetic treatment", "hair care", "medical spa"],
    "source_class": "scientific_equipment",
}


def _scene(scene_id: str = "scene_001", **overrides) -> dict:
    scene = {
        "scene_id": scene_id,
        "visual_type": "video",
        "narration": "В январе 2023 года они собрали образцы в Сухих долинах Мак-Мердо.",
        "primary_query": "долинах собрали Сухих",
        "target_duration_sec": 8.0,
    }
    scene.update(overrides)
    return scene


def _candidate(asset_id: str, title: str, *, provider: str = "wikimedia", tags: list[str] | None = None, **overrides) -> dict:
    candidate = {
        "asset_id": asset_id,
        "provider": provider,
        "provider_asset_id": asset_id,
        "media_type": "video",
        "type": "video",
        "title": title,
        "description": title,
        "tags": tags if tags is not None else title.lower().split(),
        "tags_source": "provider",
        "source_page_url": f"https://example.test/{asset_id}",
        "license": {"license_name": "test", "rights_status": "licensed", "allowed_for_render": True, "review_required": False},
        "rights_status": "licensed",
        "allowed_for_render": True,
        "review_required": False,
        "width": 1080,
        "height": 1920,
        "duration_sec": 20.0,
        "quality_score": 8.5,
        "vertical_score": 10,
    }
    candidate.update(overrides)
    return candidate


class VisualBriefOverrideTests(unittest.TestCase):
    """An explicit brief beats extraction, which produced `одном` and `которую`."""

    def test_location_survives_verbatim_instead_of_becoming_a_stem(self) -> None:
        plan = SceneVisualPlan(scene_id="scene_002", index=2, subject="долинах", place="Сухих")
        apply_brief(plan, parse_brief(ANTARCTIC_BRIEF))
        self.assertEqual(plan.place, "McMurdo Dry Valleys Antarctica")
        self.assertNotEqual(plan.place, "Сухих")
        self.assertIn("McMurdo Dry Valleys", plan.must_include)

    def test_subject_survives_instead_of_a_function_word(self) -> None:
        plan = SceneVisualPlan(scene_id="scene_003", index=3, subject="одном", action="Результат")
        apply_brief(plan, parse_brief({"subject": "nanoplastic particles", "action": "laboratory microscopy"}))
        self.assertEqual(plan.subject, "nanoplastic particles")
        self.assertNotEqual(plan.subject, "одном")
        self.assertEqual(plan.action, "laboratory microscopy")

    def test_must_avoid_is_preserved(self) -> None:
        plan = SceneVisualPlan(scene_id="scene_001", index=1)
        apply_brief(plan, parse_brief(ANTARCTIC_BRIEF))
        self.assertIn("tropical forest", plan.must_avoid)
        self.assertIn("penguin", plan.must_avoid)

    def test_a_brief_only_replaces_what_it_states(self) -> None:
        plan = SceneVisualPlan(scene_id="scene_001", index=1, subject="extracted", action="kept", place="kept place")
        apply_brief(plan, parse_brief({"subject": "explicit"}))
        self.assertEqual(plan.subject, "explicit")
        self.assertEqual(plan.action, "kept")
        self.assertEqual(plan.place, "kept place")

    def test_a_scene_without_a_brief_is_untouched(self) -> None:
        plan = SceneVisualPlan(scene_id="scene_001", index=1, subject="extracted", place="somewhere")
        apply_brief(plan, parse_brief(None))
        self.assertEqual(plan.subject, "extracted")
        self.assertEqual(plan.place, "somewhere")

    def test_user_supplied_carries_briefs_without_touching_narration(self) -> None:
        text = "Первая сцена про Антарктиду.\n\nВторая сцена про лабораторию."
        request = ScriptRequest(
            source_kind="user_script",
            raw_text=text,
            language="ru",
            constraints=ScriptConstraints(target_duration_sec=20),
            visual_briefs={"1": ANTARCTIC_BRIEF, "scene_002": LAB_BRIEF},
        )
        result = generate_script(request).result
        self.assertEqual(len(result.scenes), 2)
        self.assertEqual(result.scenes[0].narration, "Первая сцена про Антарктиду.")
        self.assertEqual(result.scenes[1].narration, "Вторая сцена про лабораторию.")
        self.assertEqual(result.scenes[0].visual_brief["place"], "McMurdo Dry Valleys Antarctica")
        self.assertEqual(result.scenes[1].visual_brief["subject"], "mass spectrometer")
        # Nothing from the brief may reach what is spoken.
        self.assertNotIn("McMurdo", result.narration_text)
        self.assertNotIn("spectrometer", result.narration_text)

    def test_briefs_round_trip_through_script_json(self) -> None:
        from src.content.script_engine import from_legacy_script

        request = ScriptRequest(
            source_kind="user_script",
            raw_text="Одна сцена.",
            constraints=ScriptConstraints(target_duration_sec=10),
            visual_briefs={"1": ANTARCTIC_BRIEF},
        )
        stored = generate_script(request).to_legacy_script()
        reloaded = from_legacy_script(stored)
        self.assertEqual(reloaded.scenes[0].visual_brief["place"], "McMurdo Dry Valleys Antarctica")

    def test_a_stored_script_without_briefs_still_reads(self) -> None:
        from src.content.script_engine import from_legacy_script

        result = from_legacy_script({"scenes": [{"scene_id": "scene_001", "narration": "текст", "target_duration_sec": 5}]})
        self.assertEqual(result.scenes[0].visual_brief, {})


class SceneStrategyTests(unittest.TestCase):
    """Providers are chosen per scene, not by registration order plus a video bonus."""

    def test_exact_geography_prefers_nasa_and_wikimedia_over_stock(self) -> None:
        strategy = build_strategy(_scene(visual_brief=ANTARCTIC_BRIEF), available_providers=ALL_PROVIDERS)
        self.assertEqual(strategy.source_class, CLASS_EXACT_LOCATION)
        order = strategy.provider_order
        self.assertLess(order.index("nasa_images"), order.index("pexels"))
        self.assertLess(order.index("wikimedia"), order.index("pexels"))
        self.assertLess(order.index("wikimedia"), order.index("pixabay"))

    def test_scientific_equipment_prefers_wikimedia_over_stock(self) -> None:
        strategy = build_strategy(_scene(visual_brief=LAB_BRIEF), available_providers=ALL_PROVIDERS)
        self.assertEqual(strategy.source_class, CLASS_SCIENTIFIC_EQUIPMENT)
        order = strategy.provider_order
        self.assertLess(order.index("wikimedia"), order.index("pexels"))
        self.assertTrue(strategy.requires_provider_metadata)

    def test_generic_broll_may_lead_with_stock(self) -> None:
        scene = _scene(narration="cinematic city street people walking", primary_query="cinematic city people", visual_brief={})
        strategy = build_strategy(scene, available_providers=ALL_PROVIDERS)
        self.assertEqual(strategy.source_class, CLASS_GENERIC_BROLL)
        self.assertEqual(strategy.provider_order[:3], ["local_library", "pexels", "pixabay"])
        self.assertFalse(strategy.requires_provider_metadata)

    def test_a_data_scene_is_never_sent_to_a_stock_library(self) -> None:
        scene = _scene(visual_brief={"source_class": "data_infographic"})
        strategy = build_strategy(scene, available_providers=ALL_PROVIDERS)
        self.assertEqual(strategy.source_class, CLASS_DATA_INFOGRAPHIC)
        self.assertNotIn("pexels", strategy.provider_order)
        self.assertNotIn("pixabay", strategy.provider_order)
        self.assertFalse(strategy.allows_generic_stock)

    def test_declared_source_class_wins_over_keywords(self) -> None:
        scene = _scene(narration="laboratory microscope", visual_brief={"source_class": "archive"})
        self.assertEqual(classify_scene(scene)[0], "archive")

    def test_the_decision_records_why(self) -> None:
        strategy = build_strategy(_scene(visual_brief=ANTARCTIC_BRIEF), available_providers=ALL_PROVIDERS)
        self.assertTrue(strategy.classification_reason)
        self.assertEqual(strategy.classified_from, "visual_brief")
        self.assertTrue(strategy.reasons["nasa_images"])

    def test_disabled_and_blocked_providers_are_reported(self) -> None:
        strategy = build_strategy(
            _scene(visual_brief=ANTARCTIC_BRIEF),
            available_providers=ALL_PROVIDERS,
            provider_enabled={"nasa_images": False},
            policy_eligible={"pexels": False},
        )
        self.assertEqual(strategy.skipped_providers["nasa_images"], "disabled")
        self.assertEqual(strategy.skipped_providers["pexels"], "policy_blocked")


class GenericEnvironmentIsNotAnExactLocationTests(unittest.TestCase):
    """A ``place`` that describes surroundings is not a place anyone can identify.

    Observed in ``projects/2026-08-09_diagnostic-ru-semantic-live-2``: five of six
    scenes were classified ``exact_location`` because the semantic brief had filled
    ``place`` at all - ``open ocean``, ``nature outdoors``, ``snowy icy ground`` - and
    each decision claimed it came from the glossary while no glossary term matched.
    ``place`` is documented as "where it happens", a stock-search phrase, and
    ``brief.author_semantics_are_sufficient`` already refuses it as an answer on its
    own for exactly this reason.
    """

    # The wording the live run produced, verbatim.
    GENERIC_PLACES = (
        "nature outdoors",
        "snowy icy ground",
        "open ocean",
        "outdoor natural setting",
        "indoor glass wall",
    )

    @staticmethod
    def _brief_scene(place: str, subject: str = "animal moving") -> dict:
        """A scene whose only location evidence is ``place``. No declared class."""
        return _scene(
            narration="Об этом мало кто задумывается.",
            primary_query="",
            visual_brief={"subject": subject, "place": place},
        )

    def test_a_generic_environment_is_not_an_exact_location(self) -> None:
        for place in self.GENERIC_PLACES:
            with self.subTest(place=place):
                source_class, _, _ = classify_scene(self._brief_scene(place))
                self.assertNotEqual(source_class, CLASS_EXACT_LOCATION)
                self.assertEqual(source_class, CLASS_GENERIC_BROLL)

    def test_a_generic_environment_says_it_had_no_evidence(self) -> None:
        """The recorded reason and source must name the rule that actually fired."""
        for place in self.GENERIC_PLACES:
            with self.subTest(place=place):
                _, reason, classified_from = classify_scene(self._brief_scene(place))
                self.assertEqual(classified_from, "default")
                self.assertNotIn("named place", reason)

    def test_a_generic_environment_mirrored_into_semantic_is_still_generic(self) -> None:
        """``semantic.location`` is ``[scene.place]`` - the same value, not a second source."""
        scene = self._brief_scene("open ocean")
        scene["semantic"] = {"location": ["open ocean"], "environment": ["open ocean"]}
        self.assertEqual(classify_scene(scene)[0], CLASS_GENERIC_BROLL)

    def test_a_generic_environment_is_routed_to_stock_like_any_other_broll(self) -> None:
        strategy = build_strategy(self._brief_scene("open ocean"), available_providers=ALL_PROVIDERS)
        self.assertEqual(strategy.provider_order[:3], ["local_library", "pexels", "pixabay"])
        self.assertFalse(strategy.requires_provider_metadata)

    def test_geography_the_glossary_recognises_is_still_an_exact_location(self) -> None:
        """The canonical Antarctic scene, with the declared class removed on purpose.

        Nothing here is hardcoded to the string: ``antarctica`` and ``valley`` are
        entries of the existing ``_LOCATION_TERMS`` vocabulary, which is the evidence
        that survives this repair.
        """
        scene = self._brief_scene(ANTARCTIC_BRIEF["place"], subject=ANTARCTIC_BRIEF["subject"])
        source_class, _, classified_from = classify_scene(scene)
        self.assertEqual(source_class, CLASS_EXACT_LOCATION)
        self.assertEqual(classified_from, "glossary")

    def test_a_declared_exact_location_still_wins_without_any_glossary_term(self) -> None:
        """An author naming the class is untouched by this repair."""
        scene = self._brief_scene("open ocean")
        scene["visual_brief"]["source_class"] = CLASS_EXACT_LOCATION
        self.assertEqual(classify_scene(scene), (CLASS_EXACT_LOCATION, "declared in visual brief", "visual_brief"))

    def test_the_other_glossary_classes_are_unchanged(self) -> None:
        for narration, expected in (
            ("orbital satellite imagery", "satellite_or_earth_observation"),
            ("mass spectrometer in a laboratory", CLASS_SCIENTIFIC_EQUIPMENT),
            ("archival newsreel footage", "archive"),
            ("researchers on an expedition", "research_activity"),
        ):
            with self.subTest(narration=narration):
                scene = _scene(narration=narration, primary_query="", visual_brief={"place": "open ocean"})
                self.assertEqual(classify_scene(scene)[0], expected)


class ProviderQueryLanguageTests(unittest.TestCase):
    """Wikimedia and NASA answered 16 Russian requests each with 0 results."""

    def test_english_only_providers_are_declared_as_such(self) -> None:
        for provider in ("pexels", "pixabay", "wikimedia", "nasa_images", "internet_archive"):
            self.assertEqual(provider_query_languages(provider), ("en",))

    def test_a_russian_query_is_never_sent_to_an_english_only_provider(self) -> None:
        plan = build_scene_queries(_scene(), providers=["wikimedia", "pexels"], intent_language="ru")
        for query in plan.queries:
            if query.status == STATUS_OK:
                self.assertNotRegex(query.query, r"[Ѐ-ӿ]")

    def test_without_english_evidence_the_scene_is_flagged_not_guessed(self) -> None:
        scene = _scene(narration="совершенно непереводимое", primary_query="непереводимое слово")
        plan = build_scene_queries(scene, providers=["wikimedia"], intent_language="ru")
        self.assertIn("wikimedia", plan.untranslatable_providers)
        self.assertEqual(plan.queries[0].status, STATUS_TRANSLATION_REQUIRED)
        self.assertEqual(plan.queries[0].query, "")

    def test_a_query_refused_for_its_language_is_recorded_in_the_plan(self) -> None:
        """K9: the scene still searched, so nothing said its best query was lost.

        Characterized before the change: the mixed-alphabet leading query of every
        LIVE-5 scene was skipped inside ``_provider_ready_candidates`` and the plan
        came back with three ``ok`` rows and nothing else, so the saved evidence of
        a language failure was identical to that of a deliberately narrower plan.
        The record has to name the query itself - "some query was dropped" cannot
        be acted on - and it must stay unsendable.
        """

        scene = _scene(
            narration="Солнечная панель ловит свет только днём.",
            primary_query="solar panel in daylight Солнечная",
            visual_brief={
                "subject": "solar panel",
                "action": "catching sunlight",
                "place": "rooftop",
            },
        )
        plan = build_scene_queries(scene, providers=["pexels"], intent_language="ru")

        sendable = plan.for_provider("pexels")
        self.assertTrue(sendable)
        self.assertTrue(all(query.language == "en" for query in sendable))
        refused = [
            query for query in plan.queries if query.status == STATUS_LANGUAGE_UNSUPPORTED
        ]
        self.assertEqual(
            ["solar panel in daylight Солнечная"], [query.query for query in refused]
        )
        self.assertEqual(["ru"], [query.language for query in refused])
        self.assertNotIn(refused[0], sendable)
        self.assertIn("не отправлен", refused[0].notes)
        self.assertEqual(plan.untranslatable_providers, [])

    def test_the_refused_record_never_becomes_a_request(self) -> None:
        """The trace is evidence, not a queue: only ``ok`` may be sent.

        ``for_provider`` is the single door between the plan and the network, and
        the request budget is spent from what comes through it, so a plan that
        gained rows must not have gained requests.
        """

        scene = _scene(
            primary_query="долинах собрали Сухих",
            visual_brief=ANTARCTIC_BRIEF,
        )
        plan = build_scene_queries(scene, providers=["pexels", "wikimedia"], intent_language="ru")
        for provider in ("pexels", "wikimedia"):
            sendable = plan.for_provider(provider)
            self.assertTrue(sendable)
            self.assertTrue(
                all(query.status == STATUS_OK for query in sendable), provider
            )
            self.assertTrue(
                any(
                    query.status == STATUS_LANGUAGE_UNSUPPORTED
                    for query in plan.queries
                    if query.provider == provider
                ),
                provider,
            )
        persisted = plan.to_dict()
        self.assertEqual(
            {STATUS_OK, STATUS_LANGUAGE_UNSUPPORTED},
            {item["status"] for item in persisted["queries"]},
        )

    def test_a_fully_blocked_scene_still_leads_with_its_translation_verdict(self) -> None:
        """Order is a contract: readers take the first entry as the scene's verdict.

        ``asset_manifest_builder`` writes the ledger line for a blocked scene from
        the ``query_translation_required`` entry, and existing tests read
        ``queries[0]``. The refusal rows are appended after it for that reason.
        """

        scene = _scene(narration="совершенно непереводимое", primary_query="непереводимое слово")
        plan = build_scene_queries(scene, providers=["wikimedia"], intent_language="ru")
        self.assertEqual(plan.queries[0].status, STATUS_TRANSLATION_REQUIRED)
        self.assertEqual(plan.queries[0].query, "")
        self.assertIn("wikimedia", plan.untranslatable_providers)
        self.assertEqual(
            ["непереводимое слово"],
            [
                query.query
                for query in plan.queries
                if query.status == STATUS_LANGUAGE_UNSUPPORTED
            ],
        )
        self.assertEqual([], plan.for_provider("wikimedia"))

    def test_t1a_prepared_queries_are_filtered_and_stably_deduplicated(self) -> None:
        brief = {
            "subject": "corvid bird",
            "action": "recognizing human face",
            "place": "urban park",
            "provider_queries": {
                "default": [
                    "corvid bird recognizing human face",
                    "crow watching person outdoors",
                    "  CORVID   BIRD recognizing human face  ",
                    "ворона узнаёт лицо",
                ]
            },
        }
        plan = build_scene_queries(
            _scene(
                narration="Ворона узнаёт лицо человека.",
                primary_query="ворона узнаёт лицо",
                visual_brief=brief,
            ),
            providers=["wikimedia"],
            intent_language="ru",
        )
        queries = plan.for_provider("wikimedia")
        self.assertEqual(
            [query.query for query in queries[:2]],
            [
                "corvid bird recognizing human face",
                "crow watching person outdoors",
            ],
        )
        self.assertEqual(
            sum(query.source == SOURCE_EXPLICIT for query in queries),
            2,
        )
        self.assertIn(SOURCE_BRIEF_FIELDS, {query.source for query in queries})
        self.assertEqual(
            len({" ".join(query.query.casefold().split()) for query in queries}),
            len(queries),
        )
        self.assertTrue(all(query.language == "en" for query in queries))
        self.assertTrue(all("ворона" not in query.query for query in queries))

    def test_t1b_structured_intents_exclude_the_unproven_legacy_broad_query(self) -> None:
        scene = _scene(
            narration="квазиморфный объект флуктуирует",
            primary_query="квазиморфный объект",
            alternative_queries=["nature science wildlife observation"],
            visual_brief={},
        )
        plan = build_scene_queries(
            scene,
            providers=["wikimedia"],
            intent_language="ru",
        )
        self.assertEqual(plan.for_provider("wikimedia"), [])
        self.assertEqual(plan.untranslatable_providers, ["wikimedia"])
        self.assertEqual(plan.queries[0].status, STATUS_TRANSLATION_REQUIRED)
        self.assertNotIn(
            "nature science wildlife observation",
            {query.query for query in plan.queries},
        )

    def test_t2_glossary_does_not_match_inside_an_unrelated_word(self) -> None:
        plan = build_scene_queries(
            _scene(
                narration="Исследователи связывают историю с фактами.",
                primary_query="исследователи факты",
                alternative_queries=[],
                visual_brief={},
            ),
            providers=["wikimedia"],
            intent_language="ru",
        )
        words = {
            word.casefold()
            for query in plan.for_provider("wikimedia")
            for word in query.query.split()
        }
        self.assertNotIn("ice", words)

    def test_t3_english_alternative_survives_a_russian_primary(self) -> None:
        plan = build_scene_queries(
            _scene(
                narration="Вороны узнают лица людей.",
                primary_query="вороны узнают лица",
                alternative_queries=[
                    "corvid bird facial recognition",
                    "crow watching human face",
                ],
                visual_brief={},
            ),
            providers=["pexels"],
            intent_language="ru",
        )
        queries = plan.for_provider("pexels")
        self.assertEqual(
            [query.query for query in queries],
            [
                "corvid bird facial recognition",
                "crow watching human face",
            ],
        )
        self.assertTrue(
            all(query.source == SOURCE_SAME_LANGUAGE for query in queries)
        )
        self.assertTrue(all(query.language == "en" for query in queries))

    def test_t4_glossary_recognizes_safe_morphological_forms(self) -> None:
        for form in ("пустыню", "пустыни", "пустыней"):
            with self.subTest(form=form):
                plan = build_scene_queries(
                    _scene(
                        narration=f"Камера показывает {form}.",
                        primary_query=form,
                        alternative_queries=[],
                        visual_brief={},
                    ),
                    providers=["wikimedia"],
                    intent_language="ru",
                )
                self.assertTrue(
                    any(
                        query.query == "desert"
                        and query.source == SOURCE_GLOSSARY
                        for query in plan.for_provider("wikimedia")
                    )
                )

    def test_t5_unknown_intent_remains_fail_closed(self) -> None:
        plan = build_scene_queries(
            _scene(
                narration="квазиморфный объект флуктуирует",
                primary_query="квазиморфный объект",
                alternative_queries=[],
                visual_brief={},
            ),
            providers=["wikimedia"],
            intent_language="ru",
        )
        self.assertEqual(plan.for_provider("wikimedia"), [])
        self.assertEqual(plan.untranslatable_providers, ["wikimedia"])
        self.assertEqual(plan.queries[0].status, STATUS_TRANSLATION_REQUIRED)
        self.assertEqual(plan.queries[0].query, "")

    def test_exact_entities_survive_into_the_provider_query(self) -> None:
        plan = build_scene_queries(_scene(visual_brief=ANTARCTIC_BRIEF), providers=["wikimedia"], intent_language="ru")
        primary = plan.for_provider("wikimedia")[0]
        self.assertIn("McMurdo Dry Valleys", primary.query)
        self.assertIn("Antarctica", primary.query)
        self.assertNotIn("Сухих", primary.query)

    def test_an_explicit_provider_query_is_used_as_written(self) -> None:
        brief = dict(ANTARCTIC_BRIEF, provider_queries={"en": ["McMurdo Dry Valleys Antarctica aerial satellite"]})
        plan = build_scene_queries(_scene(visual_brief=brief), providers=["nasa_images"], intent_language="ru")
        self.assertEqual(plan.for_provider("nasa_images")[0].query, "McMurdo Dry Valleys Antarctica aerial satellite")
        self.assertEqual(plan.for_provider("nasa_images")[0].source, "explicit_override")

    def test_a_provider_specific_query_beats_the_generic_one(self) -> None:
        brief = dict(ANTARCTIC_BRIEF, provider_queries={"en": ["generic"], "pexels": ["antarctic landscape"]})
        plan = build_scene_queries(_scene(visual_brief=brief), providers=["pexels", "wikimedia"], intent_language="ru")
        self.assertEqual(plan.for_provider("pexels")[0].query, "antarctic landscape")
        self.assertEqual(plan.for_provider("wikimedia")[0].query, "generic")

    def test_a_query_carries_no_stray_narration_words(self) -> None:
        plan = build_scene_queries(_scene(visual_brief=ANTARCTIC_BRIEF), providers=["wikimedia"], intent_language="ru")
        words = plan.for_provider("wikimedia")[0].query.lower().split()
        self.assertNotIn("собрали", words)
        self.assertNotIn("которую", words)

    def test_an_already_english_plan_reaches_the_provider_untouched(self) -> None:
        scene = _scene(primary_query="antarctic dry valley landscape", narration="antarctic valley")
        plan = build_scene_queries(scene, providers=["pexels"], intent_language="ru")
        self.assertEqual(plan.for_provider("pexels")[0].query, "antarctic dry valley landscape")


class HonestMetadataScoreTests(unittest.TestCase):
    """40 candidates scored exactly 100.0 because the query was counted as evidence."""

    def test_query_derived_tags_are_not_evidence(self) -> None:
        scene = SemanticScene(scene_id="s", subject=["antarctica"], must_include=["antarctica"], visual_priority="exact_subject")
        candidate = _candidate(
            "echo", "", provider="pexels", tags=["antarctica", "valley"], tags_source="query_derived",
            description="", search_query="antarctica valley",
        )
        ranked = rank_candidates(scene, [candidate])
        self.assertTrue(ranked[0]["rejected"])
        self.assertNotEqual(ranked[0]["metadata_status"], "available")
        self.assertLess(ranked[0]["metadata_score"], 100)

    def test_a_description_that_is_only_the_query_is_not_evidence(self) -> None:
        scene = SemanticScene(scene_id="s", subject=["antarctica"], must_include=["antarctica"], visual_priority="exact_subject")
        candidate = _candidate("echo2", "", provider="pexels", tags=[], description="antarctica valley", search_query="antarctica valley")
        ranked = rank_candidates(scene, [candidate])
        self.assertTrue(ranked[0]["rejected"])

    def test_a_real_title_containing_the_searched_words_is_still_evidence(self) -> None:
        scene = SemanticScene(scene_id="s", subject=["antarctica"], must_include=["antarctica"], visual_priority="exact_subject")
        candidate = _candidate("real", "Aerial view of Antarctica dry valley rocks", search_query="antarctica valley")
        ranked = rank_candidates(scene, [candidate])
        self.assertFalse(ranked[0]["rejected"])
        self.assertEqual(ranked[0]["metadata_status"], "available")

    def test_missing_metadata_is_reported_not_scored_as_a_match(self) -> None:
        scene = SemanticScene(scene_id="s", subject=["antarctica"], visual_priority="environment")
        candidate = _candidate("blank", "", tags=[], description="")
        ranked = rank_candidates(scene, [candidate])
        self.assertEqual(ranked[0]["metadata_status"], "unavailable")
        self.assertEqual(ranked[0]["metadata_score"], 0.0)

    def test_an_exacting_scene_refuses_a_candidate_with_no_evidence(self) -> None:
        scene = SemanticScene(scene_id="s", subject=["mass spectrometer"], visual_priority="exact_subject")
        candidate = _candidate("blank", "", tags=[], description="")
        ranked = rank_candidates(scene, [candidate], require_provider_metadata=True)
        self.assertTrue(ranked[0]["rejected"])
        # Q2.2A made this the universal gate: nothing unverified may be auto-selected,
        # so the reason is now the stricter one rather than the exacting-class one.
        self.assertIn("semantic_unverified", ranked[0]["reject_reason"])

    def test_scores_stay_separate_instead_of_one_blended_number(self) -> None:
        scene = SemanticScene(scene_id="s", subject=["antarctica"], visual_priority="environment")
        ranked = rank_candidates(scene, [_candidate("c", "Antarctica dry valley")], required_duration_sec=5.0)
        for key in (
            "semantic_score", "metadata_score", "metadata_status", "technical_score",
            "rights_status", "duration_status", "provider_confidence", "semantic_match_status",
        ):
            self.assertIn(key, ranked[0])

    def test_technical_quality_cannot_outweigh_a_forbidden_subject(self) -> None:
        scene = SemanticScene(
            scene_id="s", subject=["antarctica"], must_not_include=["tropical forest"], visual_priority="environment"
        )
        pretty = _candidate("forest", "Drone view of lush tropical forest", width=3840, height=2160, quality_score=10, vertical_score=10)
        ranked = rank_candidates(scene, [pretty])
        self.assertTrue(ranked[0]["rejected"])
        self.assertIn("must_avoid_match", ranked[0]["reject_reason"])

    def test_a_russian_term_against_english_metadata_is_unverified_not_absent(self) -> None:
        scene = SemanticScene(scene_id="s", subject=["пластик"], must_include=["пластик"], visual_priority="environment")
        ranked = rank_candidates(scene, [_candidate("c", "Plastic bottles on a conveyor belt")])
        self.assertEqual(ranked[0]["semantic_match_status"], "unverified")
        self.assertIn("subject", ranked[0]["undecidable_fields"])
        self.assertIn("пластик", ranked[0]["must_include_unverifiable"])

    def test_an_exacting_scene_refuses_an_unverifiable_requirement(self) -> None:
        scene = SemanticScene(scene_id="s", subject=["пластик"], must_include=["пластик"], visual_priority="exact_subject")
        ranked = rank_candidates(scene, [_candidate("c", "Plastic bottles")], require_provider_metadata=True)
        self.assertTrue(ranked[0]["rejected"])
        self.assertIn("must_include_unverifiable", ranked[0]["reject_reason"])


class MustIncludeAndAvoidTests(unittest.TestCase):
    def test_must_include_is_enforced(self) -> None:
        scene = SemanticScene(scene_id="s", subject=["antarctica"], must_include=["antarctica"], visual_priority="environment")
        ranked = rank_candidates(scene, [_candidate("c", "Autumn forest drone view in Kayseri")])
        self.assertTrue(ranked[0]["rejected"])
        self.assertIn("must_include_missing", ranked[0]["reject_reason"])

    def test_must_avoid_is_a_rejection_not_a_deduction(self) -> None:
        scene = SemanticScene(
            scene_id="s", subject=["laboratory"], must_include=["laboratory"],
            must_not_include=["hair care", "beauty salon"], visual_priority="environment",
        )
        ranked = rank_candidates(scene, [_candidate("c", "Laboratory hair care demonstration")])
        self.assertTrue(ranked[0]["rejected"])
        self.assertIn("hair care", ranked[0]["negative_matches"])

    def test_must_avoid_matches_cyrillic_terms_too(self) -> None:
        scene = SemanticScene(scene_id="s", must_not_include=["пингвины"], visual_priority="environment")
        ranked = rank_candidates(scene, [_candidate("c", "Антарктида пингвины на снегу")])
        self.assertTrue(ranked[0]["rejected"])
        self.assertIn("пингвины", ranked[0]["negative_matches"])

    def test_a_ban_the_metadata_cannot_answer_is_not_a_cleared_ban(self) -> None:
        """C105, ban half: a Russian prohibition against English metadata.

        ``must_include`` has said this since Q2.2A - a term written in a script the
        provider's metadata cannot contain is *unverifiable*, and the record says so in
        ``must_include_unverifiable``. The ban field said nothing at all: the term
        matched nothing, ``negative_matches`` came back empty, and the record was
        indistinguishable from one where the author's prohibition was checked and
        found absent. Measured 2026-08-19 on the 44 saved plans: 26 such bans in 5
        scenes of ``2026-08-13_polog-dozhdevogo-lesa``.

        Reported, not enforced. Making the ban conditional on decidability is the
        separate owner decision pinned by the test below (``C97``, 2026-08-18), and
        rejecting on an unanswerable ban would refuse every English candidate of a
        Russian scene. So the candidate stays selectable and the record stops claiming
        the ban was cleared.
        """
        scene = SemanticScene(
            scene_id="s", subject=["laboratory"], must_not_include=["люди"],
            visual_priority="environment",
        )
        ranked = rank_candidates(scene, [_candidate("c", "Laboratory people at work")])

        self.assertEqual([], ranked[0]["negative_matches"])
        self.assertNotIn("must_avoid_match", ranked[0]["reject_reason"])
        self.assertFalse(ranked[0]["rejected"])
        self.assertEqual(["люди"], ranked[0]["must_avoid_unverifiable"])

    def test_a_ban_that_literally_matched_is_not_also_reported_unverifiable(self) -> None:
        """One term, one verdict: the mixed-script record of ``C97`` stays a match."""
        scene = SemanticScene(scene_id="s", must_not_include=["penguin"], visual_priority="environment")
        ranked = rank_candidates(scene, [_candidate("mixed", "Антарктида penguin colony")])
        self.assertIn("penguin", ranked[0]["negative_matches"])
        self.assertEqual([], ranked[0]["must_avoid_unverifiable"])

    def test_the_disqualifying_ban_does_not_ask_whether_the_term_was_provable(self) -> None:
        """C97, owner decision 2026-08-18: the split between the two ban paths stays.

        The slot layer asks ``is_undecidable`` before ``contains``; the ranker, which
        is the path that actually disqualifies, asks only whether the word is there.
        The two can disagree on exactly one shape of record - a field written in two
        scripts at once, which is out of script with the term and still contains it
        verbatim - and that shape is pinned here on both layers.

        Measured before the decision, not after: aligning them changes 0 of 1928
        candidates in 212 saved scenes and 0 of 599 (v1) and 5 (v2) corpus triples, and
        the only available alignment silences a ban that literally matched. So the
        ranker keeps the strict question, and this test is what a future slice has to
        argue with before making the ban conditional on decidability.
        """
        scene = SemanticScene(
            scene_id="s", must_not_include=["penguin"], visual_priority="environment"
        )
        candidate = _candidate("mixed", "Антарктида penguin colony")
        evidence = build_evidence(candidate)

        self.assertTrue(evidence.is_undecidable("penguin"))
        self.assertTrue(evidence.contains("penguin"))

        ranked = rank_candidates(scene, [candidate])
        self.assertIn("penguin", ranked[0]["negative_matches"])
        self.assertIn("must_avoid_match:penguin", ranked[0]["reject_reason"])

        verdict = build_slot_verdict(scene, evidence, source_class=scene.source_class)
        self.assertEqual([], verdict.conflicting_slots)


class DurationSuitabilityTests(unittest.TestCase):
    def test_a_clip_shorter_than_its_scene_is_refused(self) -> None:
        scene = SemanticScene(scene_id="s", visual_priority="environment")
        ranked = rank_candidates(scene, [_candidate("short", "Ocean waves", duration_sec=6.54)], required_duration_sec=7.92)
        self.assertTrue(ranked[0]["rejected"])
        self.assertEqual(ranked[0]["duration_status"], "too_short")
        self.assertAlmostEqual(ranked[0]["duration_check"]["deficit_sec"], 1.38, places=2)

    def test_the_verdict_records_what_was_required_and_what_was_offered(self) -> None:
        scene = SemanticScene(scene_id="s", visual_priority="environment")
        check = rank_candidates(scene, [_candidate("c", "Ocean waves", duration_sec=6.0)], required_duration_sec=7.0)[0]["duration_check"]
        self.assertEqual(check["required_sec"], 7.0)
        self.assertEqual(check["candidate_sec"], 6.0)
        self.assertEqual(check["deficit_sec"], 1.0)
        self.assertEqual(check["adaptation"], "slow_down_or_loop")

    def test_a_long_enough_clip_passes(self) -> None:
        scene = SemanticScene(scene_id="s", visual_priority="environment")
        ranked = rank_candidates(scene, [_candidate("ok", "Ocean waves", duration_sec=12.0)], required_duration_sec=7.92)
        self.assertEqual(ranked[0]["duration_status"], "sufficient")
        self.assertFalse(ranked[0]["rejected"])

    def test_a_still_image_is_not_judged_on_duration(self) -> None:
        scene = SemanticScene(scene_id="s", visual_priority="environment")
        still = _candidate("img", "Antarctic valley", media_type="image", type="image", duration_sec=0.0)
        ranked = rank_candidates(scene, [still], required_duration_sec=9.0)
        self.assertEqual(ranked[0]["duration_status"], "not_applicable")
        self.assertFalse(ranked[0]["rejected"])


class GeneratedInfographicTests(unittest.TestCase):
    def test_a_figure_is_drawn_from_the_scene_spec(self) -> None:
        from src.assets.generated_infographic import render_svg, spec_from_scene

        scene = _scene(visual_brief={"source_class": "data_infographic", "infographic": {
            "headline_value": "54%", "caption": "участков верхнего слоя",
            "total_points": 13, "active_points": 7,
            "top_layer_label": "верхний слой", "top_layer_marks": 7,
            "deep_layer_label": "глубокий слой", "deep_layer_marks": 2,
        }})
        spec = spec_from_scene(scene)
        self.assertIsNotNone(spec)
        svg = render_svg(spec)
        self.assertTrue(svg.startswith("<svg"))
        self.assertIn("54%", svg)
        self.assertIn('width="1080"', svg)
        self.assertIn('height="1920"', svg)
        self.assertEqual(svg.count("<circle"), 13 + 7 + 2)

    def test_output_is_deterministic(self) -> None:
        from src.assets.generated_infographic import render_svg, spec_from_scene

        scene = _scene(visual_brief={"infographic": {"headline_value": "54%", "total_points": 4, "active_points": 2}})
        spec = spec_from_scene(scene)
        self.assertEqual(render_svg(spec), render_svg(spec))

    def test_no_spec_means_no_figure_is_invented(self) -> None:
        from src.assets.generated_infographic import spec_from_scene

        self.assertIsNone(spec_from_scene(_scene(visual_brief={"source_class": "data_infographic"})))

    def test_the_generated_asset_is_project_owned_with_provenance(self) -> None:
        import tempfile
        from pathlib import Path

        from src.assets.generated_infographic import build_generated_asset, spec_from_scene

        scene = _scene(visual_brief={"infographic": {"headline_value": "54%", "total_points": 13, "active_points": 7}})
        with tempfile.TemporaryDirectory() as tmp:
            asset = build_generated_asset(
                spec_from_scene(scene), project_root=Path(tmp), project_id="p", scene_id="scene_004"
            )
        self.assertEqual(asset["provider"], "generated")
        self.assertEqual(asset["rights_status"], "user_owned")
        self.assertTrue(asset["allowed_for_render"])
        self.assertFalse(asset["license"]["attribution_required"])
        self.assertEqual(len(asset["checksum_sha256"]), 64)
        self.assertTrue(asset["provenance"]["metadata_snapshot"]["generated_by_project"])


if __name__ == "__main__":
    unittest.main()
