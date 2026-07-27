"""Stage Q2: the visual planning layer, its planner and its validator.

The layer replaced ``src.news.visual_plan.make_stock_query`` - four ``if`` branches
returning one of four fixed English strings for every video ever made. Two things
therefore have to be true and are pinned here:

- one plan entry per script scene, in script order, bound by ``scene_id``;
- what a scene searches for comes from that scene's own words, so two scenes about
  different things do not get the same query.

No network (``tests.network_guard`` is installed package-wide), no downloads, no
Vision, no render, no asset selection: the planner is pure text in, plan out.
"""

from __future__ import annotations

import json
import unittest

from src.content.script_engine import ScriptResult, ScriptScene
from src.content.visual_planning import (
    DEFAULT_PLANNER_ID,
    INTENT_PRIMARY,
    MEDIA_ARCHIVE_FOOTAGE,
    MEDIA_KINDS,
    MEDIA_VIDEO,
    SHOT_ESTABLISHING,
    SHOT_PAYOFF,
    SHOT_TYPES,
    VISUAL_PLAN_SCHEMA_VERSION,
    SceneVisualPlan,
    VisualPlanRequest,
    VisualPlanResult,
    VisualPlannerInputError,
    VisualPlannerUnavailableError,
    VisualSearchIntent,
    build_plan,
    from_legacy_visual_plan,
    get_planner,
    intent_to_query,
    list_capabilities,
    list_planner_ids,
    to_legacy_visual_plan,
    validate_visual_plan,
)
from src.content.visual_planning.entities import (
    collect_entities,
    extract_actions,
    extract_period,
    extract_places,
    stem,
)

NARRATIONS = [
    "Почему вороны узнают лица людей и помнят их годами?",
    "Исследователи в Вашингтонском университете надевали одну и ту же маску и ловили птиц.",
    "Вороны запоминали эту маску и потом кричали на человека, который её носил.",
    "Реакция сохранялась больше пяти лет, хотя птиц никто не трогал.",
    "Вороны передавали информацию сородичам, которые сами не попадали в ловушку.",
    "Это значит, что у ворон работает социальная передача знания об угрозе.",
]

ROLES = ["hook", "development", "development", "development", "development", "payoff"]


def _script(narrations: list[str] | None = None, roles: list[str] | None = None) -> ScriptResult:
    narrations = narrations or NARRATIONS
    roles = roles or (ROLES if len(narrations) == len(ROLES) else ["hook"] + ["development"] * (len(narrations) - 2) + ["payoff"])
    scenes = [
        ScriptScene(
            scene_id=f"scene_{index:03d}",
            index=index,
            role=roles[index - 1] if index - 1 < len(roles) else "development",
            narration=text,
            duration_sec=4.0 + index * 0.5,
            claim_ids=[f"claim_{index:03d}"],
        )
        for index, text in enumerate(narrations, start=1)
    ]
    return ScriptResult(scenes=scenes, title="Почему вороны узнают лица", language="ru")


def _request(**overrides) -> VisualPlanRequest:
    base = {"script": _script(), "language": "ru", "topic": "Почему вороны узнают лица"}
    base.update(overrides)
    return VisualPlanRequest(**base)


class EntityExtractionTest(unittest.TestCase):
    """The parts that decide what a scene is about. Everything here is a substring
    of the input - nothing is translated, generalised or invented."""

    def test_inflections_of_one_word_share_a_stem(self) -> None:
        for group in (("ворона", "вороны", "ворону", "ворон"), ("маска", "маски", "маску")):
            with self.subTest(group=group):
                stems = {stem(word) for word in group}
                self.assertEqual(len(stems), 1, f"{group} должны считаться одной сущностью: {stems}")

    def test_the_topic_entity_ranks_first(self) -> None:
        entities = collect_entities(
            scene_texts={f"scene_{i:03d}": text for i, text in enumerate(NARRATIONS, start=1)},
            topic="Почему вороны узнают лица",
        )
        self.assertTrue(entities)
        self.assertEqual(stem(entities[0].surface), stem("вороны"))

    def test_function_words_are_never_entities(self) -> None:
        entities = collect_entities(
            scene_texts={"scene_001": "Это значит, что подряд больше никто не трогал который год."}
        )
        surfaces = {entity.surface.lower() for entity in entities}
        for junk in ("который", "больше", "никто", "значит", "подряд", "год"):
            self.assertNotIn(junk, surfaces)

    def test_places_need_a_locative_preposition(self) -> None:
        self.assertEqual(extract_places("Исследователи в Вашингтонском университете ловили птиц."), ["Вашингтонском"])
        # A capitalised name without one could equally be a person or a company.
        self.assertEqual(extract_places("Вашингтонский университет опубликовал отчёт."), [])

    def test_actions_prefer_lowercase_verbs_over_capitalised_nouns(self) -> None:
        """'Исследователи' ends in a verb-like suffix; 'надевали' is the real verb."""
        actions = extract_actions("Исследователи надевали маску и ловили птиц.")
        self.assertEqual(actions[0], "надевали")
        self.assertNotIn("Исследователи", actions)

    def test_abstract_reporting_relation_is_not_a_filmable_action(self) -> None:
        actions = extract_actions(
            "Исследователи связывают историю с проверяемыми фактами."
        )
        self.assertEqual(actions, [])

    def test_periods_are_read_only_when_written(self) -> None:
        for text, expected in (
            ("Наблюдение началось в 1984 году и продолжается.", "1984 год"),
            ("Это происходило в девятнадцатом веке.", ""),
            ("Вороны запоминали маску.", ""),
        ):
            with self.subTest(text=text):
                self.assertEqual(extract_period(text)[: len(expected)] if expected else extract_period(text), expected)


class DeterministicPlannerTest(unittest.TestCase):
    def test_is_the_default_and_is_free_and_offline(self) -> None:
        self.assertEqual(DEFAULT_PLANNER_ID, "deterministic_local")
        capabilities = get_planner(DEFAULT_PLANNER_ID).capabilities
        self.assertFalse(capabilities.requires_network)
        self.assertFalse(capabilities.requires_paid_api)
        self.assertTrue(capabilities.deterministic)

    def test_one_plan_per_script_scene_in_order(self) -> None:
        script = _script()
        plan = build_plan(_request(script=script)).result
        self.assertEqual(plan.scene_ids, [scene.scene_id for scene in script.scenes])
        self.assertEqual([scene.index for scene in plan.scenes], list(range(1, len(script.scenes) + 1)))

    def test_works_for_any_scene_count(self) -> None:
        for count in (1, 2, 3, 6, 9, 14):
            with self.subTest(scenes=count):
                script = _script([NARRATIONS[index % len(NARRATIONS)] + f" Деталь номер {index}." for index in range(count)])
                plan = build_plan(_request(script=script)).result
                self.assertEqual(len(plan.scenes), count)

    def test_is_reproducible(self) -> None:
        first = build_plan(_request()).result.to_dict()
        second = build_plan(_request()).result.to_dict()
        self.assertEqual(first, second)

    def test_scenes_do_not_all_search_for_the_same_thing(self) -> None:
        """The defect Q2 exists to remove: four fixed strings for every video."""
        plan = build_plan(_request()).result
        primaries = [tuple(scene.intents[0].terms) for scene in plan.scenes if scene.intents]
        self.assertGreater(len(set(primaries)), 1)

    def test_every_planned_term_comes_from_the_script(self) -> None:
        """Nothing invented: no synonym, no general category, no new country."""
        script = _script()
        plan = build_plan(_request(script=script)).result
        source = " ".join(scene.narration for scene in script.scenes).lower()
        for scene in plan.scenes:
            for term in [scene.subject, scene.action, scene.place, *scene.must_include]:
                if term:
                    with self.subTest(scene=scene.scene_id, term=term):
                        self.assertIn(term.lower(), source)

    def test_the_video_subject_wins_over_a_rarer_word(self) -> None:
        """Continuity: a scene naming the crow shows the crow, not the mask."""
        plan = build_plan(_request()).result
        subjects = [scene.subject for scene in plan.scenes if scene.subject]
        self.assertTrue(any(stem(subject) == stem("вороны") for subject in subjects))

    def test_a_place_is_not_mistaken_for_the_subject(self) -> None:
        script = _script(["Исследователи в Вашингтонском университете надевали маску и ловили птиц."])
        scene = build_plan(_request(script=script)).result.scenes[0]
        self.assertEqual(scene.place, "Вашингтонском")
        self.assertNotEqual(scene.subject, "Вашингтонском")

    def test_shot_type_follows_the_scenes_job_not_its_index(self) -> None:
        plan = build_plan(_request()).result
        self.assertEqual(plan.scenes[0].shot_type, SHOT_ESTABLISHING)
        self.assertEqual(plan.scenes[-1].shot_type, SHOT_PAYOFF)
        for scene in plan.scenes:
            self.assertIn(scene.shot_type, SHOT_TYPES)

    def test_a_dated_scene_may_use_archive_material(self) -> None:
        script = _script(["Наблюдение началось в 1984 году и продолжается до сих пор в том же районе."])
        scene = build_plan(_request(script=script)).result.scenes[0]
        self.assertTrue(scene.period)
        self.assertIn(MEDIA_ARCHIVE_FOOTAGE, scene.allowed_media_kinds)

    def test_media_kinds_stay_inside_the_supported_vocabulary(self) -> None:
        plan = build_plan(_request()).result
        for scene in plan.scenes:
            with self.subTest(scene=scene.scene_id):
                self.assertIn(scene.preferred_media_kind, MEDIA_KINDS)
                self.assertIn(scene.preferred_media_kind, scene.allowed_media_kinds)

    def test_fallbacks_differ_from_the_primary_and_widen(self) -> None:
        plan = build_plan(_request()).result
        for scene in plan.scenes:
            with self.subTest(scene=scene.scene_id):
                keys = [tuple(intent.terms) for intent in scene.intents]
                self.assertEqual(len(keys), len(set(keys)), "запасной запрос не должен повторять предыдущий")
                levels = [intent.fallback_level for intent in scene.intents]
                self.assertEqual(levels, sorted(levels))

    def test_intents_declare_their_language_and_translation_need(self) -> None:
        plan = build_plan(_request()).result
        intent = plan.scenes[0].intents[0]
        self.assertEqual(intent.language, "ru")
        self.assertTrue(intent.requires_translation, "русские термины нельзя отдать англоязычному стоку как есть")

    def test_latin_terms_need_no_translation(self) -> None:
        script = _script(["The crow remembers human faces for years after the first encounter."])
        scene = build_plan(_request(script=script, language="en", topic="crow memory")).result.scenes[0]
        self.assertFalse(scene.intents[0].requires_translation)

    def test_claim_ids_travel_with_the_scene(self) -> None:
        plan = build_plan(_request()).result
        self.assertEqual(plan.scenes[0].claim_ids, ["claim_001"])

    def test_an_empty_script_is_a_clear_error(self) -> None:
        with self.assertRaises(VisualPlannerInputError):
            build_plan(_request(script=ScriptResult(scenes=[])))

    def test_no_negatives_are_invented(self) -> None:
        """The prototype refused deserts and mountains for every video because one
        of them was about whales. Nothing goes in must_avoid without knowing why."""
        plan = build_plan(_request()).result
        self.assertEqual([scene.must_avoid for scene in plan.scenes], [[] for _ in plan.scenes])


class RegistryTest(unittest.TestCase):
    def test_the_default_planner_is_registered(self) -> None:
        self.assertEqual(list_planner_ids(), ["deterministic_local"])

    def test_unknown_planner_names_the_available_ones(self) -> None:
        with self.assertRaises(VisualPlannerUnavailableError) as caught:
            get_planner("нет такого")
        self.assertIn("deterministic_local", str(caught.exception))

    def test_capabilities_are_serialisable(self) -> None:
        for capability in list_capabilities():
            json.dumps(capability.to_dict(), ensure_ascii=False)


class ValidationTest(unittest.TestCase):
    """Errors are things that are broken; warnings are things that are merely weak."""

    def _plan(self, scenes: list[SceneVisualPlan]) -> VisualPlanResult:
        return VisualPlanResult(scenes=scenes, language="ru")

    def _scene(self, **overrides) -> SceneVisualPlan:
        base = {
            "scene_id": "scene_001",
            "index": 1,
            "meaning": "Вороны запоминают лица людей",
            "subject": "вороны",
            "shot_type": SHOT_ESTABLISHING,
            "preferred_media_kind": MEDIA_VIDEO,
            "allowed_media_kinds": [MEDIA_VIDEO],
            "must_include": ["вороны"],
            "intents": [
                VisualSearchIntent(kind=INTENT_PRIMARY, subject="вороны", context=["лица"], fallback_level=1),
                VisualSearchIntent(kind="alternative", subject="вороны", fallback_level=2),
            ],
        }
        base.update(overrides)
        return SceneVisualPlan(**base)

    def _codes(self, plan: VisualPlanResult, **kwargs) -> list[str]:
        return validate_visual_plan(plan, **kwargs).codes()

    def test_a_sound_plan_passes(self) -> None:
        validation = validate_visual_plan(self._plan([self._scene()]))
        self.assertTrue(validation.valid, validation.codes())

    def test_empty_plan_is_an_error(self) -> None:
        self.assertIn("empty_plan", self._codes(self._plan([])))

    def test_scene_problems_are_errors(self) -> None:
        script = _script(NARRATIONS[:2])
        cases = {
            "missing_scene_plan": self._plan([self._scene()]),
            "unknown_scene_id": self._plan(
                [self._scene(), self._scene(scene_id="scene_002", index=2), self._scene(scene_id="scene_099", index=3)]
            ),
            "duplicate_scene_id": self._plan([self._scene(), self._scene(index=2)]),
        }
        for code, plan in cases.items():
            with self.subTest(code=code):
                self.assertIn(code, self._codes(plan, script=script))

    def test_scene_count_mismatch_is_reported(self) -> None:
        self.assertIn("scene_count_mismatch", self._codes(self._plan([self._scene()]), script=_script()))

    def test_scenes_out_of_order_are_reported(self) -> None:
        plan = self._plan([self._scene(index=5), self._scene(scene_id="scene_002", index=1)])
        self.assertIn("scenes_out_of_order", self._codes(plan))

    def test_empty_content_is_an_error(self) -> None:
        for code, scene in (
            ("empty_visual_intent", self._scene(meaning="  ")),
            ("no_search_intents", self._scene(intents=[])),
            ("empty_search_intent", self._scene(intents=[VisualSearchIntent(subject="  ")])),
        ):
            with self.subTest(code=code):
                self.assertIn(code, self._codes(self._plan([scene])))

    def test_unsupported_vocabulary_is_an_error(self) -> None:
        for code, scene in (
            ("unsupported_media_kind", self._scene(allowed_media_kinds=["hologram"], preferred_media_kind="hologram")),
            ("unsupported_shot_type", self._scene(shot_type="нечто")),
            ("preferred_media_not_allowed", self._scene(preferred_media_kind="image", allowed_media_kinds=[MEDIA_VIDEO])),
        ):
            with self.subTest(code=code):
                self.assertIn(code, self._codes(self._plan([scene])))

    def test_conflicting_constraints_are_an_error(self) -> None:
        scene = self._scene(must_include=["вороны"], must_avoid=["Вороны"])
        self.assertIn("conflicting_constraints", self._codes(self._plan([scene])))

    def test_a_required_entity_must_actually_be_searched_for(self) -> None:
        scene = self._scene(must_include=["вороны", "гнездо"])
        self.assertIn("must_include_not_searched", self._codes(self._plan([scene])))

    def test_an_entity_absent_from_the_source_is_an_error(self) -> None:
        """The check a freely-writing planner needs: crows must not become ravens."""
        scene = self._scene(subject="ворон", must_include=["ворон", "пингвин"])
        codes = self._codes(self._plan([scene]), script=_script())
        self.assertIn("entity_not_in_source", codes)

    def test_weak_choices_are_warnings_not_errors(self) -> None:
        cases = {
            "intent_too_broad": self._scene(
                must_include=[], intents=[VisualSearchIntent(subject="природа", fallback_level=1),
                                          VisualSearchIntent(subject="природа", context=["лес"], fallback_level=2)]
            ),
            "no_fallback_intent": self._scene(
                intents=[VisualSearchIntent(subject="вороны", context=["лица"], fallback_level=1)]
            ),
            "duplicate_fallback_intent": self._scene(
                intents=[
                    VisualSearchIntent(subject="вороны", context=["лица"], fallback_level=1),
                    VisualSearchIntent(subject="вороны", context=["лица"], fallback_level=2),
                ]
            ),
        }
        for code, scene in cases.items():
            with self.subTest(code=code):
                validation = validate_visual_plan(self._plan([scene]))
                self.assertIn(code, validation.codes())
                self.assertTrue(validation.valid, f"{code} должен быть предупреждением, а не ошибкой")

    def test_identical_intents_across_scenes_are_a_warning(self) -> None:
        plan = self._plan([self._scene(), self._scene(scene_id="scene_002", index=2)])
        validation = validate_visual_plan(plan)
        self.assertIn("identical_scene_intents", validation.codes())
        self.assertTrue(validation.valid)

    def test_a_real_plan_validates_against_its_own_script(self) -> None:
        script = _script()
        planning = build_plan(_request(script=script))
        self.assertTrue(planning.validation.valid, planning.validation.codes())


class LegacyFormatTest(unittest.TestCase):
    """visual_plan.json is extended, never replaced."""

    PRE_Q2_PLAN = {
        "language": "ru",
        "aspect_ratio": "9:16",
        "resolution": {"width": 1080, "height": 1920},
        "scenes": [
            {
                "scene_id": "scene_001",
                "narration": "Эта ворона может помнить твоё лицо годами.",
                "target_duration_sec": 5.5,
                "visual_type": "video",
                "visual_description": "Close-up portrait of a crow",
                "primary_query": "crow close up portrait",
                "alternative_queries": ["crow head close up", "raven close up"],
                "negative_keywords": ["watermark", "logo", "low resolution"],
                "preferred_asset_ids": [],
                "allow_user_asset": True,
                "allow_stock": True,
                "allow_article_asset": False,
                "fallback_type": "text_card",
                "camera_effect": "slow_zoom_in",
                "transition": "cut",
            }
        ],
    }

    def _stored(self) -> dict:
        return to_legacy_visual_plan(build_plan(_request()).result, language="ru")

    def test_every_key_old_readers_use_is_still_written(self) -> None:
        stored = self._stored()
        for key in ("language", "aspect_ratio", "resolution", "scenes"):
            self.assertIn(key, stored)
        for key in self.PRE_Q2_PLAN["scenes"][0]:
            self.assertIn(key, stored["scenes"][0])

    def test_planning_fields_are_additive(self) -> None:
        stored = self._stored()
        self.assertEqual(stored["visual_plan_schema_version"], VISUAL_PLAN_SCHEMA_VERSION)
        self.assertEqual(stored["planner_id"], "deterministic_local")
        self.assertIn("semantic", stored["scenes"][0])

    def test_the_semantic_block_is_what_analyze_scene_reads(self) -> None:
        """The whole point of the integration: the existing search path consumes the
        plan through a block it already knew how to read."""
        from src.assets.semantic_selection import analyze_scene, ordered_queries

        scene = self._stored()["scenes"][0]
        semantic = analyze_scene(scene)
        self.assertEqual(semantic.scene_id, scene["scene_id"])
        self.assertEqual(semantic.subject, scene["semantic"]["subject"])
        self.assertEqual(semantic.visual_priority, scene["semantic"]["visual_priority"])
        self.assertTrue(ordered_queries(semantic), "план должен давать существующему слою запросы")

    def test_the_old_broad_english_query_survives_as_the_last_resort(self) -> None:
        """No translator exists, so the plan may only add to what search had before."""
        scene = self._stored()["scenes"][0]
        self.assertIn("nature science wildlife observation", scene["alternative_queries"])

    def test_a_pre_q2_plan_is_read_without_migration(self) -> None:
        plan = from_legacy_visual_plan(self.PRE_Q2_PLAN)
        self.assertEqual(len(plan.scenes), 1)
        self.assertEqual(plan.schema_version, 1)
        self.assertEqual([intent_to_query(intent) for intent in plan.scenes[0].intents][0], "crow close up portrait")
        self.assertEqual(len(plan.scenes[0].intents), 3)

    def test_a_pre_q2_plan_can_be_validated(self) -> None:
        validation = validate_visual_plan(from_legacy_visual_plan(self.PRE_Q2_PLAN))
        self.assertIn(validation.status, {"passed", "needs_review", "failed"})

    def test_round_trip_preserves_scenes_and_intents(self) -> None:
        original = build_plan(_request()).result
        restored = from_legacy_visual_plan(to_legacy_visual_plan(original, language="ru"))
        self.assertEqual(restored.scene_ids, original.scene_ids)
        for before, after in zip(original.scenes, restored.scenes, strict=True):
            self.assertEqual([intent.terms for intent in after.intents], [intent.terms for intent in before.intents])

    def test_the_stored_plan_is_serialisable(self) -> None:
        json.loads(json.dumps(self._stored(), ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()
