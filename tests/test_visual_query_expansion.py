"""PLAN-9B-2: the controlled expansion ladder and the hardcodes it replaces.

Three things have to be true and are pinned here:

- the ladder widens a provider-language idea into several genuinely different
  queries, and does it for any domain rather than for one topic somebody wired in;
- what the migrated topic hardcodes used to be needed for - a three-level query
  structure, ``must_avoid`` treated as part of the query's meaning, and a stored plan
  that carries more than one fixed English string - is now produced generically;
- nothing widens when there is no provider-language evidence, because a wider guess
  is still a guess.

No network (``tests.network_guard`` is installed package-wide), no provider call, no
downloads: the ladder is text in, queries out.
"""

from __future__ import annotations

import unittest

from src.assets.query_adapter import SOURCE_EXPLICIT, build_scene_queries
from src.content.script_engine import ScriptResult, ScriptScene
from src.content.visual_planning import (
    MAX_EXPANSION_QUERIES,
    MAX_PROVIDER_QUERIES,
    SceneVisualPlan,
    VisualPlanRequest,
    VisualPlanResult,
    VisualSearchIntent,
    build_plan,
    expand_queries,
    planning_input,
    planning_input_from_scene,
    to_legacy_visual_plan,
)
from src.content.visual_planning.brief import VisualBrief, produce_brief
from src.content.visual_planning.contract import VisualPlannerCapabilities
from src.content.visual_planning.expansion import mentions_avoided


class _PreparedPlanner:
    """Returns a scene somebody already planned, so the ladder is what is measured."""

    capabilities = VisualPlannerCapabilities(
        planner_id="prepared_fixture",
        display_name="Prepared evidence fixture",
        requires_network=False,
        requires_paid_api=False,
        deterministic=True,
    )

    def __init__(self, result: VisualPlanResult) -> None:
        self._result = result

    def supports(self, request: VisualPlanRequest) -> bool:
        return True

    def plan(self, request: VisualPlanRequest) -> VisualPlanResult:
        return self._result


def _orca_input():
    """The exact meaning the migrated orca hardcode used to state by hand."""
    return planning_input(
        subject="orca killer whale",
        action="coordinated hunting",
        place="open ocean",
        entities=["Orcinus orca"],
        context=["ocean sunfish"],
        must_avoid=["dolphin", "humpback whale", "blue whale"],
    )


class LadderShapeTest(unittest.TestCase):
    def test_the_ladder_widens_step_by_step_from_the_exact_subject(self) -> None:
        queries = expand_queries(_orca_input())

        self.assertIn("Orcinus orca killer whale", queries)
        self.assertIn("orca killer whale coordinated hunting", queries)
        self.assertIn("orca killer whale coordinated hunting open ocean", queries)
        self.assertIn("Orcinus orca", queries)
        self.assertIn("orca killer whale open ocean", queries)
        # The same idea seen as its environment rather than as its subject.
        self.assertTrue(any(query.startswith("open ocean") for query in queries))

    def test_the_exact_subject_leads_and_the_environment_trails(self) -> None:
        queries = expand_queries(_orca_input())
        exact = queries.index("orca killer whale coordinated hunting open ocean")
        environment = min(
            index for index, query in enumerate(queries) if query.startswith("open ocean")
        )
        self.assertLess(exact, environment)

    def test_the_ladder_is_not_bound_to_one_topic(self) -> None:
        """The hardcodes it replaces fired on one subject. This fires on the shape."""
        cases = {
            "animals/wildlife": planning_input(
                subject="snow leopard", action="crossing ridge", place="mountain slope"
            ),
            "energy/technology": planning_input(
                subject="solar farm", action="charging battery storage", place="desert plateau"
            ),
            "geography/infrastructure": planning_input(
                subject="shipping canal", action="lifting cargo ships", place="isthmus lock"
            ),
        }
        for domain, data in cases.items():
            with self.subTest(domain=domain):
                queries = expand_queries(data)
                self.assertGreaterEqual(len(queries), 4)
                self.assertEqual(queries[0], data.subject)
                self.assertIn(f"{data.subject} {data.action}", queries)
                self.assertIn(f"{data.subject} {data.action} {data.place}", queries)
                self.assertIn(f"{data.subject} {data.place}", queries)

    def test_expansion_is_deterministic(self) -> None:
        self.assertEqual(expand_queries(_orca_input()), expand_queries(_orca_input()))

    def test_nothing_widens_without_provider_language_evidence(self) -> None:
        russian = planning_input(subject="косатка", action="охотится", place="открытый океан")
        self.assertEqual(expand_queries(russian), [])
        self.assertEqual(expand_queries(planning_input()), [])

    def test_a_single_term_idea_is_not_promoted_into_a_query(self) -> None:
        """"orca" alone is a category, not a scene; the fail-closed floor stays."""
        self.assertEqual(expand_queries(planning_input(subject="orca")), [])

    def test_near_duplicate_rungs_do_not_inflate_the_ladder(self) -> None:
        """Every rung of this idea collapses onto the same two terms."""
        data = planning_input(subject="solar farm", entities=["Solar Farm"], context=["solar  farm"])
        self.assertEqual([query.casefold() for query in expand_queries(data)], ["solar farm"])

    def test_the_ladder_stays_bounded(self) -> None:
        data = planning_input(
            subject="shipping canal",
            action="lifting cargo ships",
            place="isthmus lock chamber",
            entities=[f"entity{index} canal" for index in range(12)],
            context=[f"context{index} lock" for index in range(12)],
        )
        queries = expand_queries(data)
        self.assertLessEqual(len(queries), MAX_EXPANSION_QUERIES)
        self.assertEqual(len(queries), len({query.casefold() for query in queries}))
        self.assertLessEqual(len(expand_queries(data, limit=3)), 3)

    def test_stated_queries_lead_and_are_also_offered_truncated(self) -> None:
        """The legacy ladder's truncation rung, kept: a long query and its short form
        fail differently, so both are worth asking."""
        queries = expand_queries(
            planning_input(), seeds=["solar farm battery storage electrical grid"]
        )
        self.assertEqual(queries[0], "solar farm battery storage electrical grid")
        self.assertIn("solar farm", queries)


class MustAvoidIsPartOfTheQueryTest(unittest.TestCase):
    """Salvaged from the orca hardcode: ``must_avoid`` shapes what is asked for."""

    def test_an_avoided_subject_is_never_asked_for(self) -> None:
        data = planning_input(
            subject="killer whale",
            action="hunting",
            place="open ocean",
            entities=["bottlenose dolphin pod"],
            must_avoid=["bottlenose dolphin"],
        )
        queries = expand_queries(data)
        self.assertTrue(queries)
        self.assertTrue(all("dolphin" not in query.casefold() for query in queries))

    def test_avoidance_matches_the_phrase_and_not_a_shared_word(self) -> None:
        """"Suez Canal" must not veto the Panama Canal, or avoidance becomes a mute."""
        data = planning_input(
            subject="Panama Canal locks",
            action="lifting cargo ships",
            must_avoid=["Suez Canal"],
        )
        queries = expand_queries(data)
        self.assertIn("Panama Canal locks lifting cargo ships", queries)

    def test_punctuation_does_not_smuggle_an_avoided_phrase_past_the_match(self) -> None:
        """F1: a raw whitespace split leaves punctuation glued to a word, so
        "Panama Canal," or a truncated "Panama Canal." never matched the
        ``must_avoid`` tokens even though the query plainly names the avoided
        subject. Both sides of the comparison must use the same provider-token
        normalisation the ladder already builds queries with."""
        cases = {
            "trailing comma": ("Panama Canal, wide aerial shot", ["Panama Canal"], True),
            "case and punctuation together": (
                "PANAMA CANAL, wide aerial shot",
                ["panama canal"],
                True,
            ),
            "trailing sentence period": (
                "wide aerial shot of the Panama Canal.",
                ["Panama Canal"],
                True,
            ),
            "an unrelated canal is not vetoed": (
                "Suez Canal wide aerial shot",
                ["Panama Canal"],
                False,
            ),
            "a shared single word does not veto the query": (
                "wide aerial shot of the Canal",
                ["Panama Canal"],
                False,
            ),
            "punctuation around the surrounding words": (
                "aerial, Panama Canal, wide shot",
                ["Panama Canal"],
                True,
            ),
        }
        for label, (seed, must_avoid, expect_blocked) in cases.items():
            with self.subTest(label=label):
                queries = expand_queries(planning_input(must_avoid=must_avoid), seeds=[seed])
                self.assertEqual(seed not in queries, expect_blocked)

    def test_a_ban_written_in_the_scenes_own_script_vetoes_a_query_in_that_script(self) -> None:
        """C104: the comparison had no mechanism for the alphabet at all.

        ``_avoided_match_tokens`` tokenised both sides with the tokeniser that *builds*
        provider queries, so a Cyrillic ban tokenised to nothing and vetoed nothing -
        not only an English query, but a Russian one naming the forbidden thing
        verbatim. Measured on 43 saved plans this changes no stored query (the ladder
        composes in the provider's language and a Cyrillic string can only enter it as
        an author's own seed), which is why the ban is pinned here by direct call.
        """
        self.assertTrue(mentions_avoided("люди идут по мосту", ["люди"]))
        self.assertTrue(mentions_avoided("дельфин выпрыгивает из воды", ["дельфин"]))
        self.assertEqual(
            [],
            expand_queries(planning_input(must_avoid=["люди"]), seeds=["люди идут по мосту"]),
        )

    def test_a_ban_still_matches_a_phrase_and_not_a_shared_word_in_any_script(self) -> None:
        """The phrase rule is what keeps the ban from becoming a mute, and it is not a
        property of the Latin alphabet: "текст в кадре" must not veto a query about
        текст, exactly as "Suez Canal" does not veto the Panama Canal."""
        self.assertFalse(mentions_avoided("текст на экране", ["текст в кадре"]))
        self.assertTrue(mentions_avoided("крупный текст в кадре", ["текст в кадре"]))
        self.assertFalse(mentions_avoided("горная река", ["горы"]))

    def test_a_ban_in_another_script_than_the_query_still_cannot_match(self) -> None:
        """The half this does *not* close, pinned so nobody reads more into it.

        A Russian ban against an English query is a translation question, not a
        tokenisation one: ``C105`` owns the bridge, and until it exists a Russian
        author's ban is enforced downstream (ranking, slots) rather than here.
        """
        self.assertFalse(mentions_avoided("people walking on a bridge", ["люди"]))
        self.assertFalse(mentions_avoided("люди идут по мосту", ["people"]))

    def test_the_truncation_rung_does_not_leak_the_avoided_phrase(self) -> None:
        """Rung 7 offers the leading stated query truncated to its two most specific
        terms; that truncated string must be screened by the same must_avoid check as
        every other rung, not just the untruncated seed it was cut from."""
        queries = expand_queries(
            planning_input(must_avoid=["Panama Canal"]),
            seeds=["Panama Canal, aerial establishing shot"],
        )
        self.assertFalse(queries)


class PlanningInputTest(unittest.TestCase):
    def test_a_brief_wins_over_the_planners_own_fields(self) -> None:
        scene = SceneVisualPlan(
            scene_id="scene_001",
            index=1,
            subject="ворона",
            place="парк",
            must_avoid=["игрушка"],
            brief=VisualBrief(subject="carrion crow", place="urban park", must_avoid=["toy bird"]),
        )
        data = planning_input_from_scene(scene)
        self.assertEqual(data.subject, "carrion crow")
        self.assertEqual(data.place, "urban park")
        self.assertIn("toy bird", data.must_avoid)

    def test_source_language_fields_are_dropped_rather_than_guessed_at(self) -> None:
        scene = SceneVisualPlan(scene_id="scene_001", index=1, subject="ворона", place="парк")
        data = planning_input_from_scene(scene)
        self.assertEqual(data.subject, "")
        self.assertEqual(data.place, "")
        self.assertTrue(data.is_empty)

    def test_a_locator_is_not_a_search_term(self) -> None:
        data = planning_input(subject="assets/library/crow_01.mp4", place="https://example.org")
        self.assertTrue(data.is_empty)


class ProducerUsesTheLadderTest(unittest.TestCase):
    """The producer is the provider-language source the ladder must be preceded by."""

    def _produce(self, scene: SceneVisualPlan, *, script_scene=None) -> VisualBrief:
        return produce_brief(scene, script_scene=script_scene)

    def test_an_automatic_brief_carries_more_than_the_exact_query(self) -> None:
        brief = self._produce(
            SceneVisualPlan(
                scene_id="scene_001",
                index=1,
                subject="tidal turbine",
                action="spinning underwater",
                place="coastal channel",
                intents=[VisualSearchIntent(subject="приливная турбина", language="ru")],
            )
        )
        queries = brief.provider_queries["en"]
        self.assertGreater(len(queries), 1)
        self.assertLessEqual(len(queries), MAX_PROVIDER_QUERIES)
        self.assertEqual(queries[0], "tidal turbine")
        self.assertIn("tidal turbine spinning underwater", queries)

    def test_stated_evidence_still_leads_the_automatic_brief(self) -> None:
        brief = self._produce(
            SceneVisualPlan(scene_id="scene_001", index=1, subject="solar farm"),
            script_scene=ScriptScene(
                scene_id="scene_001",
                index=1,
                role="hook",
                narration="Солнечная станция заряжает хранилище.",
                duration_sec=5.0,
                keywords=["solar farm", "battery storage", "electrical grid"],
            ),
        )
        queries = brief.provider_queries["en"]
        self.assertEqual(queries[0], "solar farm battery storage electrical grid")
        self.assertIn("solar farm", queries)

    def test_an_idea_with_no_english_evidence_still_produces_no_brief(self) -> None:
        brief = self._produce(
            SceneVisualPlan(
                scene_id="scene_001",
                index=1,
                subject="кваркозавр",
                action="мерцает",
                place="флуксатор",
                intents=[VisualSearchIntent(subject="кваркозавр", language="ru")],
            )
        )
        self.assertTrue(brief.is_empty)


class HardcodeMigrationTest(unittest.TestCase):
    """What the migrated topic hardcodes were needed for, produced generically."""

    def _plan(self, brief: dict, narration: str) -> dict:
        script = ScriptResult(
            scenes=[
                ScriptScene(
                    scene_id="scene_001",
                    index=1,
                    role="hook",
                    narration=narration,
                    duration_sec=5.0,
                    visual_brief=brief,
                )
            ],
            language="ru",
        )
        planned = VisualPlanResult(
            scenes=[SceneVisualPlan(scene_id="scene_001", index=1, meaning=narration)],
            language="ru",
            planner_id="prepared_fixture",
        )
        result = build_plan(
            VisualPlanRequest(script=script, language="ru"),
            planner=_PreparedPlanner(planned),
        ).result
        return to_legacy_visual_plan(result, language="ru")["scenes"][0]

    def test_the_three_level_structure_is_reproduced_without_the_topic_literals(self) -> None:
        """The retired topic auto-brief hand-wrote exact subject -> group ->
        environment for one animal. The same shape now comes out of the ladder, and
        the words come from the brief rather than from an ``if`` on the topic."""
        scene = self._plan(
            {
                "subject": "orca killer whale",
                "action": "coordinated hunting",
                "place": "open ocean",
                "exact_entities": ["Orcinus orca"],
                "must_avoid": ["dolphin", "humpback whale", "blue whale"],
            },
            "Косатки координируют охоту в открытом океане.",
        )
        written = [scene["primary_query"], *scene["alternative_queries"]]
        exact = [query for query in written if "Orcinus orca" in query]
        group = [query for query in written if "coordinated hunting" in query]
        environment = [query for query in written if query.startswith("open ocean")]

        self.assertTrue(exact)
        self.assertTrue(group)
        self.assertTrue(environment)
        self.assertTrue(all("dolphin" not in query.casefold() for query in written))

    def test_the_same_shape_comes_out_for_an_unrelated_domain(self) -> None:
        scene = self._plan(
            {
                "subject": "geothermal power plant",
                "action": "venting steam",
                "place": "volcanic valley",
                "exact_entities": ["Hellisheidi station"],
            },
            "Геотермальная станция выпускает пар в долине.",
        )
        written = [scene["primary_query"], *scene["alternative_queries"]]
        self.assertIn("Hellisheidi station geothermal power plant", written)
        self.assertIn("geothermal power plant venting steam volcanic valley", written)
        self.assertTrue(any(query.startswith("volcanic valley") for query in written))

    def test_source_and_rights_references_survive_the_migration(self) -> None:
        script = ScriptResult(
            scenes=[
                ScriptScene(
                    scene_id="scene_001",
                    index=1,
                    role="hook",
                    narration="Косатки координируют охоту.",
                    duration_sec=5.0,
                    visual_brief={"subject": "orca killer whale", "action": "coordinated hunting"},
                )
            ],
            language="ru",
        )
        planned = VisualPlanResult(
            scenes=[
                SceneVisualPlan(
                    scene_id="scene_001",
                    index=1,
                    meaning="Косатки координируют охоту.",
                    claim_ids=["claim_001"],
                    source_refs=["source_001"],
                )
            ],
            language="ru",
            planner_id="prepared_fixture",
        )
        result = build_plan(
            VisualPlanRequest(script=script, language="ru"),
            planner=_PreparedPlanner(planned),
        ).result
        scene = to_legacy_visual_plan(result, language="ru")["scenes"][0]

        self.assertEqual(scene["claim_ids"], ["claim_001"])
        self.assertEqual(scene["source_refs"], ["source_001"])
        self.assertEqual(scene["negative_keywords"][:3], ["watermark", "logo", "low resolution"])

    def test_an_author_brief_still_wins_over_everything_the_ladder_derives(self) -> None:
        """The ladder widens; it never outranks a query the author wrote themselves."""
        scene = self._plan(
            {
                "subject": "orca killer whale",
                "action": "coordinated hunting",
                "provider_queries": {"en": ["author exact orca pod"]},
            },
            "Косатки координируют охоту.",
        )
        self.assertEqual(scene["visual_brief"]["provider_queries"], {"en": ["author exact orca pod"]})
        self.assertIn("author exact orca pod", scene["alternative_queries"])

        sent = build_scene_queries(scene, providers=["pexels"], intent_language="ru").for_provider("pexels")
        self.assertEqual(sent[0].query, "author exact orca pod")
        self.assertEqual(sent[0].source, SOURCE_EXPLICIT)

    def test_a_scene_with_nothing_to_say_writes_no_query_at_all(self) -> None:
        scene = self._plan({}, "Кваркозавр мерцает возле флуксатора.")
        self.assertEqual(scene["primary_query"], "")
        self.assertEqual(scene["alternative_queries"], [])


if __name__ == "__main__":
    unittest.main()
