"""C98: a provider query is not allowed to lose the subject of the video's topic.

What is measured here
---------------------
The census the owner named as the acceptance of this slice: rebuild every provider
query of the two frozen runs through the production owner
(``src.assets.query_adapter.build_scene_queries``) and count how many distinct
queries carry no form of the topic at all. Measured on 2026-08-18 and recorded in
[ADR 0022](../docs/adr/0022-meaning-first-visual-retrieval.md): **15 of 42**.

Why the corpus and not ``projects/``
------------------------------------
The two source runs live in ``projects/``, which is ignored by Git in full, so a
test reading them would not run on a fresh clone. ``tests/data/plan9d/current_corpus_v2.json``
freezes the very scene records those runs fed to the query owner, and rebuilding
from them reproduces the saved ``query_plan`` entry for entry (asserted below), so
the census is the same census on committed data.

One thing the corpus does not carry is the plan container: it stores scenes, not
the ``visual_plan`` they came from. ``topic_entity`` = "панель" for both runs is
the value of the saved plans
(``…-2/localizations/ru/visual/visual_plan.json`` and ``…-3/…``), pinned in ADR
0022 and in ``docs/audits/PLAN_9D_FAILURE_DIAGNOSIS_2026-08-18.md``; it is
restated here because the frozen corpus dropped it, not invented for the test.

What this file does **not** measure: whether selection got better. The blind
harness replays selection over a frozen pool and re-issues no query, so it cannot
see this change at all - there it is a guard, not the acceptance.

One divergence worth stating: ``live_5/scene_003`` on disk now carries a differently
worded, equally subject-less brief (``factory production line`` rather than the frozen
``factory assembly line``). The corpus is what ADR 0022 measured and what this test
measures; the plan file has moved on, and the number belongs to the frozen evidence.

No network: text in, queries out.
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path
from typing import Any

from src.assets.query_adapter import (
    ANCHOR_SOURCE_SCENE_SUBJECTS,
    ANCHOR_SOURCE_TOPIC_ENTITY,
    ANCHOR_SOURCE_UNRESOLVED,
    STATUS_OK,
    STATUS_SUBJECT_UNVERIFIED,
    build_scene_queries,
    build_slot_queries,
    plan_topic_anchor,
)

CORPUS_PATH = Path(__file__).resolve().parent / "data" / "plan9d" / "current_corpus_v2.json"

#: The topic of both frozen runs, in every form the owner's census counted: the
#: English words a stock provider is searched with, and the Russian forms the plan
#: and the local library are written in. This is evaluation vocabulary - the
#: production rule does not read it, it compares against the plan's own evidence.
_TOPIC_FORMS = re.compile(r"solar|photovoltaic|panel|панел|солнеч|фотоэлектр", re.IGNORECASE)

#: What the saved plans of both runs state as the topic of the video. Russian, and
#: therefore unusable as a query for every provider in ``PROVIDER_QUERY_LANGUAGES``
#: except the local library.
_TOPIC_ENTITY = "панель"


def _load_runs() -> dict[str, dict[str, Any]]:
    """The frozen scenes, regrouped into the plan each run actually had."""

    corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    runs: dict[str, dict[str, Any]] = {}
    for scene in corpus["scenes"]:
        run = runs.setdefault(
            str(scene["run_id"]), {"topic_entity": _TOPIC_ENTITY, "scenes": []}
        )
        run["scenes"].append(scene)
    return runs


def _providers_of(scene: dict[str, Any]) -> list[str]:
    """The providers this scene was actually routed to, in the captured order."""

    ordered: list[str] = []
    for query in scene["query_plan"]["queries"]:
        if query["provider"] not in ordered:
            ordered.append(query["provider"])
    return ordered


def _rebuild(scene: dict[str, Any], **kwargs: Any) -> list[Any]:
    plan = build_scene_queries(
        scene,
        providers=_providers_of(scene),
        intent_language=str(scene["query_plan"].get("intent_language") or "ru"),
        **kwargs,
    )
    return plan.queries


def _census(queries_by_scene: list[list[Any]]) -> tuple[list[str], list[str]]:
    """Distinct sendable queries, and the ones carrying no form of the topic."""

    distinct: list[str] = []
    for queries in queries_by_scene:
        for item in queries:
            if item.status != STATUS_OK:
                continue
            key = " ".join(item.query.casefold().split())
            if key and key not in distinct:
                distinct.append(key)
    return distinct, [key for key in distinct if not _TOPIC_FORMS.search(key)]


class QuerySubjectCensus(unittest.TestCase):
    """The number this slice is accepted on, measured on committed data."""

    def test_rebuilding_the_frozen_scenes_reproduces_the_saved_query_plan(self) -> None:
        """The census below measures the production owner, not a copy of it."""

        for run in _load_runs().values():
            for scene in run["scenes"]:
                saved = [
                    (item["provider"], item["query"], item["kind"], item["source"])
                    for item in scene["query_plan"]["queries"]
                    if item["status"] == STATUS_OK
                ]
                rebuilt = [
                    (item.provider, item.query, item.kind, item.source)
                    for item in _rebuild(scene)
                    if item.status == STATUS_OK
                ]
                with self.subTest(scene=scene["scene_key"]):
                    self.assertEqual(rebuilt, saved)

    def test_without_a_topic_anchor_fifteen_of_fortytwo_queries_lose_the_subject(
        self,
    ) -> None:
        """The state measured on 2026-08-18, kept reproducible after the repair."""

        distinct, subjectless = _census(
            [_rebuild(scene) for run in _load_runs().values() for scene in run["scenes"]]
        )
        self.assertEqual(len(distinct), 42)
        self.assertEqual(len(subjectless), 15)

    def test_with_the_plan_anchor_no_query_loses_the_subject(self) -> None:
        """The acceptance of C98: the same plans, the same scenes, 15 -> 0."""

        rebuilt = []
        for run in _load_runs().values():
            anchor = plan_topic_anchor(run)
            self.assertIsNotNone(anchor)
            self.assertEqual(anchor.text, "solar panel")
            for scene in run["scenes"]:
                rebuilt.append(_rebuild(scene, topic_anchor=anchor))
        distinct, subjectless = _census(rebuilt)
        self.assertEqual(subjectless, [])
        # 42 distinct queries become 41: anchoring can make two of them collide,
        # and the pair is then sent once rather than twice on the scene's budget.
        # It never adds a query - the anchor rewrites, it does not widen the ladder.
        self.assertEqual(len(distinct), 41)

    def test_the_anchor_only_touches_queries_that_dropped_the_topic(self) -> None:
        """The queries that already named the topic are still sent, unchanged."""

        for run in _load_runs().values():
            anchor = plan_topic_anchor(run)
            for scene in run["scenes"]:
                before = {
                    item.query
                    for item in _rebuild(scene)
                    if item.status == STATUS_OK and _TOPIC_FORMS.search(item.query)
                }
                after = {
                    item.query
                    for item in _rebuild(scene, topic_anchor=anchor)
                    if item.status == STATUS_OK
                }
                with self.subTest(scene=scene["scene_key"]):
                    self.assertTrue(before <= after)


class TopicAnchorDerivation(unittest.TestCase):
    """Where the English form of a Russian topic is allowed to come from."""

    def test_a_russian_topic_is_anchored_by_the_english_subjects_of_its_plan(self) -> None:
        anchor = plan_topic_anchor(
            {
                "topic_entity": "панель",
                "scenes": [
                    {"visual_brief": {"subject": "solar panel"}},
                    {"visual_brief": {"subject": "solar panel rows"}},
                    {"visual_brief": {"subject": "battery pack"}},
                ],
            }
        )
        self.assertEqual(anchor.text, "solar panel")
        self.assertEqual(anchor.source, ANCHOR_SOURCE_SCENE_SUBJECTS)
        self.assertEqual(anchor.topic_entity, "панель")

    def test_an_english_topic_entity_is_the_anchor_itself(self) -> None:
        anchor = plan_topic_anchor(
            {
                "topic_entity": "solar panel",
                "scenes": [{"visual_brief": {"subject": "sunset"}}],
            }
        )
        self.assertEqual(anchor.text, "solar panel")
        self.assertEqual(anchor.source, ANCHOR_SOURCE_TOPIC_ENTITY)

    def test_a_subject_appearing_in_one_scene_only_is_not_the_topic(self) -> None:
        """Otherwise the first scene's subject would be pushed into every query."""

        anchor = plan_topic_anchor(
            {
                "topic_entity": "панель",
                "scenes": [
                    {"visual_brief": {"subject": "solar panel"}},
                    {"visual_brief": {"subject": "battery pack"}},
                ],
            }
        )
        self.assertFalse(anchor.resolved)
        self.assertEqual(anchor.source, ANCHOR_SOURCE_UNRESOLVED)

    def test_a_russian_topic_with_no_english_evidence_is_never_translated(self) -> None:
        """K9: the anchor reaches every query of the plan, so a guess here is worse."""

        anchor = plan_topic_anchor(
            {
                "topic_entity": "панель",
                "scenes": [
                    {"visual_brief": {"subject": "солнечная панель"}},
                    {"visual_brief": {"subject": "солнечная панель"}},
                ],
            }
        )
        self.assertFalse(anchor.resolved)
        self.assertEqual(anchor.text, "")

    def test_a_plan_that_states_no_topic_asks_for_nothing(self) -> None:
        self.assertIsNone(
            plan_topic_anchor({"scenes": [{"visual_brief": {"subject": "sunset"}}]})
        )

    def test_place_and_action_are_not_topic_evidence(self) -> None:
        """A place recurring as "sunset" is how "sunset" became a query at all."""

        anchor = plan_topic_anchor(
            {
                "topic_entity": "панель",
                "scenes": [
                    {"visual_brief": {"subject": "battery pack", "place": "sunset"}},
                    {"visual_brief": {"subject": "factory machines", "place": "sunset"}},
                ],
            }
        )
        self.assertFalse(anchor.resolved)


class AnchorApplication(unittest.TestCase):
    """What an anchor does to a scene's queries, and what it refuses to do."""

    PLAN = {
        "topic_entity": "панель",
        "scenes": [
            {"visual_brief": {"subject": "solar panel"}},
            {"visual_brief": {"subject": "solar panels"}},
        ],
    }

    def _queries(
        self, scene: dict[str, Any], provider: str = "pexels", **kwargs: Any
    ) -> list[Any]:
        return build_scene_queries(
            scene, providers=[provider], intent_language="ru", **kwargs
        ).queries

    def test_a_query_without_the_topic_is_sent_with_the_topic_in_front(self) -> None:
        scene = {
            "scene_id": "scene_003",
            "visual_brief": {
                "subject": "factory machines",
                "place": "industrial production line",
                "provider_queries": {
                    "en": ["factory machines industrial production line"]
                },
            },
        }
        sent = [
            item.query
            for item in self._queries(scene, topic_anchor=plan_topic_anchor(self.PLAN))
            if item.status == STATUS_OK
        ]
        self.assertIn("solar panel factory machines industrial production line", sent)
        self.assertTrue(all(_TOPIC_FORMS.search(query) for query in sent))

    def test_the_repair_is_written_down_with_the_query_it_replaced(self) -> None:
        scene = {"scene_id": "s", "visual_brief": {"subject": "battery pack"}}
        repaired = [
            item
            for item in self._queries(scene, topic_anchor=plan_topic_anchor(self.PLAN))
            if item.status == STATUS_OK and item.notes
        ]
        self.assertTrue(repaired)
        self.assertIn("battery pack", repaired[0].notes)
        self.assertIn("панель", repaired[0].notes)

    def test_a_query_that_already_names_the_topic_is_untouched(self) -> None:
        scene = {
            "scene_id": "s",
            "visual_brief": {"subject": "solar panels", "place": "solar power plant"},
        }
        without = [item.to_dict() for item in self._queries(scene)]
        with_anchor = [
            item.to_dict()
            for item in self._queries(scene, topic_anchor=plan_topic_anchor(self.PLAN))
        ]
        self.assertEqual(with_anchor, without)

    def test_a_russian_query_never_gets_an_english_anchor_glued_to_it(self) -> None:
        """The local library searches Russian; a mixed-script query searches nothing."""

        scene = {"scene_id": "s", "primary_query": "заводская линия", "visual_brief": {}}
        sent = [
            item.query
            for item in self._queries(
                scene,
                provider="local_library",
                topic_anchor=plan_topic_anchor(self.PLAN),
            )
            if item.status == STATUS_OK
        ]
        self.assertEqual(sent, ["заводская линия"])

    def test_an_unresolvable_topic_is_marked_rather_than_sent_in_silence(self) -> None:
        """A stated topic nobody could check against is a fact, not a non-event."""

        plan = {
            "topic_entity": "панель",
            "scenes": [{"visual_brief": {"subject": "солнечная панель"}}],
        }
        scene = {
            "scene_id": "s",
            "visual_brief": {"provider_queries": {"en": ["manufacturing plant"]}},
        }
        queries = self._queries(scene, topic_anchor=plan_topic_anchor(plan))
        sendable = [item for item in queries if item.status == STATUS_OK]
        marks = [item for item in queries if item.status == STATUS_SUBJECT_UNVERIFIED]
        self.assertEqual([item.query for item in sendable], ["manufacturing plant"])
        self.assertEqual(len(marks), 1)
        self.assertIn("панель", marks[0].notes)

    def test_a_narrowed_slot_query_keeps_the_topic_too(self) -> None:
        """The "location" slot of a scene placed at sunset otherwise asks for sunset."""

        scene = {
            "scene_id": "s",
            "visual_brief": {"subject": "solar panels", "place": "sunset"},
        }
        plan = build_slot_queries(
            scene,
            "location",
            providers=["pexels"],
            topic_anchor=plan_topic_anchor(self.PLAN),
        )
        self.assertEqual(plan.queries[0].query, "solar panel sunset")


if __name__ == "__main__":
    unittest.main()
