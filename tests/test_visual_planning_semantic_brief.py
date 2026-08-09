"""PLAN-9B-PRODUCER-M: the model-assisted semantic VisualBrief adapter.

An ordinary prepared Russian script carries no provider-language evidence at all, so
``brief.produce_brief`` correctly returns nothing and the scene reaches the query
adapter as ``query_translation_required``. Deterministic extraction cannot rescue it:
it ranks the word the sentence repeats, not the word that names the shot - the
hummingbird scene came out as ``воздухе``, the penguin scene as ``живот`` and the orca
scene as ``воды``. Those are the literals this suite exists to keep out of a query.

What is pinned here:

- an injected model states *meaning* for one scene, and the existing producer, the
  existing ladder and the existing query adapter turn it into provider queries - the
  adapter itself never builds a query string;
- an ordinary non-English script reaches an executable, English, subject-bearing
  provider query when a valid semantic result is injected;
- everything that can go wrong fails closed: no model, no approval, a raised call, a
  malformed answer, an answer that is not in the provider's language, an answer made
  only of production vocabulary, and an answer that asks for what the scene forbids;
- with no adapter the deterministic plan is byte-identical to what it is today;
- the author's explicit brief still wins, applied last, on the path that actually
  delivers one.

The repair pass adds four more, all found by independent review before any model was
wired:

- assistance is offered when the deterministic brief does not *name a subject*, not
  merely when it is empty - a linked English claim or a bag of prepared keywords makes
  a brief technically non-empty while the plan still calls the scene ``воды``;
- a model states meaning and holds no authority over constraints, so overlaying its
  answer can never drop a ``must_include`` or a ``must_avoid`` the scene already had;
- an expected model failure and a defect in the injected callable are different
  outcomes, and only the first one is caught;
- a scene the author already briefed is not sent to a model whose answer that brief
  would overwrite anyway.

No network (``tests.network_guard`` is installed package-wide), no provider call, no
model call: every "model" here is a dictionary.
"""

from __future__ import annotations

import ast
import json
import unittest
from pathlib import Path

from src.assets.query_adapter import STATUS_OK, STATUS_TRANSLATION_REQUIRED, build_scene_queries
from src.content.script_engine import ScriptResult, ScriptScene
from src.content.visual_planning import (
    SHOT_ACTION,
    VisualPlanRequest,
    VisualPlannerError,
    build_plan,
)
from src.content.visual_planning.brief import VisualBrief, apply_brief
from src.content.visual_planning.semantic_brief import (
    RESPONSE_CONTRACT,
    ModelSemanticBriefAdapter,
    SceneBriefEvidence,
    SemanticBriefResponseError,
    SemanticBriefUnavailableError,
    apply_semantic_brief,
    build_prompt,
    evidence_for_scene,
    parse_response,
)

# The words the sentence repeats, which deterministic extraction promoted to subject.
# Literals here so the guard outlives whatever produced them.
MISLEADING_EXTRACTED_SUBJECTS = ("живот", "воды", "воздухе", "бежать", "срывается")

# Nothing in the visual planning package may know these. They are one diagnostic
# script, not a domain the product supports.
DIAGNOSTIC_TERMS = (
    "gecko",
    "hummingbird",
    "penguin",
    "orca",
    "геккон",
    "колибри",
    "пингвин",
    "косатк",
)

NARRATIONS = {
    "scene_001": "Геккон способен бежать по совершенно гладкому стеклу и не срывается вниз.",
    "scene_002": "Колибри может зависнуть на одном месте в воздухе, пока его крылья работают с огромной скоростью.",
    "scene_003": "Пингвины экономят силы иначе: ложатся на живот и скользят по снегу и льду.",
    "scene_004": "Косатки в открытом океане способны выпрыгивать из воды целиком.",
}
ROLES = {"scene_001": "hook", "scene_002": "development", "scene_003": "development", "scene_004": "payoff"}

# What a model that understood the scene would answer. The point of the fixture is the
# data flow, not the model's intelligence.
SEMANTIC_ANSWERS = {
    "scene_001": {
        "subject": "gecko",
        "action": "clinging and running on smooth glass",
        "place": "vertical glass pane",
    },
    "scene_002": {
        "subject": "hummingbird",
        "action": "hovering in mid air",
        "context": ["wildlife"],
    },
    "scene_003": {
        "subject": "penguin",
        "action": "sliding on belly",
        "place": "snow and ice",
    },
    "scene_004": {
        "subject": "orca",
        "action": "breaching fully out of water",
        "place": "open ocean",
    },
}
# Each scene's own subject, for asserting the query is about that scene.
EXPECTED_SUBJECTS = {scene_id: answer["subject"] for scene_id, answer in SEMANTIC_ANSWERS.items()}

# A scene whose own words are already the provider's words. Deterministic extraction
# names the subject here, so the deterministic brief states what the frame is about and
# there is nothing a model needs to add.
PROVIDER_LANGUAGE_NARRATION = "An emperor penguin colony crosses the antarctic sea ice."

# An ordinary Russian scene that happens to name a place in Latin script. The
# deterministic planner promotes that name to a hard requirement and then cannot build a
# query from it alone - which is exactly the shape in which the semantic overlay used to
# erase the requirement on its way past.
HARD_ENTITY_NARRATION = (
    "Полярная станция McMurdo стоит на краю ледника, и учёные каждый день выходят на лёд."
)
HARD_ENTITY = "McMurdo"

# What research linked to a scene looks like: English prose about a fact, not a
# statement of what to put in frame.
LINKED_CLAIM = {
    "claim_id": "claim_001",
    "text": "Field observations were recorded during the survey season.",
    "safe_for_script": True,
}

# The warning codes the plan carries when semantic assistance did not help. They are how
# a later diagnostic tells "the model had no answer" from "the model never answered".
NO_ANSWER_CODE = "semantic_brief_no_answer"
UNAVAILABLE_CODE = "semantic_brief_unavailable"
RESPONSE_CODE = "semantic_brief_response"


class _FakeSemanticModel:
    """A model that already understood the scene. Answers by ``scene_id``, records calls."""

    def __init__(self, answers: dict[str, object] | None = None) -> None:
        self.answers = answers if answers is not None else dict(SEMANTIC_ANSWERS)
        self.calls: list[tuple[str, dict]] = []

    def __call__(self, prompt: str, options: dict) -> str:
        self.calls.append((prompt, dict(options)))
        answer = self.answers.get(str(options.get("scene_id") or ""))
        if answer is None:
            # No opinion is a legitimate answer, and it must not become a brief.
            return json.dumps({"subject": ""})
        return answer if isinstance(answer, str) else json.dumps(answer, ensure_ascii=False)


def _script(scene_ids: list[str] | None = None, briefs: dict[str, dict] | None = None) -> ScriptResult:
    scene_ids = scene_ids or list(NARRATIONS)
    briefs = briefs or {}
    scenes = [
        ScriptScene(
            scene_id=scene_id,
            index=index,
            role=ROLES[scene_id],
            narration=NARRATIONS[scene_id],
            duration_sec=5.0,
            visual_brief=dict(briefs.get(scene_id) or {}),
        )
        for index, scene_id in enumerate(scene_ids, start=1)
    ]
    return ScriptResult(scenes=scenes, title="Странные способности животных", language="ru")


def _one_scene_script(narration: str, *, language: str = "ru", **scene_fields) -> ScriptResult:
    """One scene written out in full, for the cases the shared fixture cannot express."""
    return ScriptResult(
        scenes=[
            ScriptScene(
                scene_id="scene_001",
                index=1,
                role="hook",
                narration=narration,
                duration_sec=6.0,
                **scene_fields,
            )
        ],
        title="Странные способности животных",
        language=language,
    )


def _request(script: ScriptResult | None = None, **overrides) -> VisualPlanRequest:
    base = {
        "script": script or _script(),
        "language": "ru",
        "topic": "Странные способности животных",
        "title": "Странные способности животных",
    }
    base.update(overrides)
    return VisualPlanRequest(**base)


def _adapter(model: _FakeSemanticModel | None = None, **overrides) -> ModelSemanticBriefAdapter:
    options = {"approved": True, "model_id": "fixture"}
    options.update(overrides)
    return ModelSemanticBriefAdapter(model if model is not None else _FakeSemanticModel(), **options)


def _plan_without_warnings(planning) -> dict:
    """The plan itself, with the notes about *why* semantic assistance did not help removed."""
    plan = planning.result.to_dict()
    plan.pop("warnings", None)
    for scene in plan.get("scenes") or []:
        scene.pop("warnings", None)
    return plan


def _scene_warnings(planning, index: int = 0) -> list[str]:
    return list(planning.result.scenes[index].warnings)


def _provider_queries(planning, script: ScriptResult, scene_id: str, provider: str = "pexels"):
    """Everything the existing query adapter would send for one planned scene."""
    plan = planning.to_legacy_plan(language="ru", script=script.to_dict())
    scene = next(item for item in plan["scenes"] if item["scene_id"] == scene_id)
    return build_scene_queries(scene, providers=[provider], intent_language="ru")


class SceneEvidenceTest(unittest.TestCase):
    """What the adapter is allowed to know about a scene."""

    def _evidence(self, **overrides) -> SceneBriefEvidence:
        planning = build_plan(_request())
        scene = planning.result.scenes[1]
        script_scene = _script().scenes[1]
        for key, value in overrides.items():
            setattr(script_scene, key, value)
        return evidence_for_scene(scene, script_scene=script_scene, claims=[])

    def test_the_scenes_own_words_are_the_evidence(self) -> None:
        evidence = self._evidence()
        self.assertEqual(evidence.scene_id, "scene_002")
        self.assertIn("Колибри", evidence.narration)

    def test_prepared_keywords_and_on_screen_text_travel_with_the_scene(self) -> None:
        evidence = self._evidence(keywords=["hovering bird"], on_screen_text="80 взмахов")
        self.assertIn("hovering bird", evidence.keywords)
        self.assertEqual(evidence.on_screen_text, "80 взмахов")

    def test_only_claims_the_scene_names_are_included(self) -> None:
        planning = build_plan(_request())
        scene = planning.result.scenes[0]
        scene.claim_ids = ["linked"]
        evidence = evidence_for_scene(
            scene,
            script_scene=_script().scenes[0],
            claims=[
                {"claim_id": "linked", "text": "Adhesion comes from van der Waals forces.", "safe_for_script": True},
                {"claim_id": "other", "text": "Unrelated claim.", "safe_for_script": True},
                {"claim_id": "linked", "text": "Unsafe claim.", "safe_for_script": False},
            ],
        )
        self.assertEqual(evidence.claims, ("Adhesion comes from van der Waals forces.",))

    def test_the_prompt_carries_the_evidence_and_not_the_channel_topic(self) -> None:
        prompt = build_prompt(self._evidence(keywords=["hovering bird"]))
        self.assertIn("Колибри", prompt)
        self.assertIn("hovering bird", prompt)
        self.assertNotIn("Странные способности животных", prompt)
        for field in RESPONSE_CONTRACT:
            self.assertIn(field, prompt)


class SemanticResponseContractTest(unittest.TestCase):
    """The parser is the part that has to be right before any money is spent."""

    def _evidence(self, **overrides) -> SceneBriefEvidence:
        base = {"scene_id": "scene_001", "narration": NARRATIONS["scene_001"]}
        base.update(overrides)
        return SceneBriefEvidence(**base)

    def test_a_structured_answer_becomes_the_existing_brief(self) -> None:
        brief = parse_response(json.dumps(SEMANTIC_ANSWERS["scene_003"]), evidence=self._evidence())
        self.assertEqual(brief.subject, "penguin")
        self.assertEqual(brief.action, "sliding on belly")
        self.assertEqual(brief.place, "snow and ice")

    def test_a_shot_type_must_come_from_the_existing_vocabulary(self) -> None:
        brief = parse_response(
            {"subject": "penguin", "action": "sliding on belly", "shot_type": SHOT_ACTION},
            evidence=self._evidence(),
        )
        self.assertEqual(brief.shot_type, SHOT_ACTION)
        with self.assertRaises(SemanticBriefResponseError):
            parse_response({"subject": "penguin", "shot_type": "dramatic"}, evidence=self._evidence())

    def test_an_unresolved_scene_produces_no_brief_at_all(self) -> None:
        for answer in ({"subject": ""}, {"action": "sliding on belly", "place": "snow and ice"}):
            with self.subTest(answer=answer):
                self.assertTrue(parse_response(answer, evidence=self._evidence()).is_empty)

    def test_a_malformed_answer_is_refused(self) -> None:
        for raw in ("not json at all", "[]", 17, {"scenes": []}):
            with self.subTest(raw=raw):
                with self.assertRaises(SemanticBriefResponseError):
                    parse_response(raw, evidence=self._evidence())

    def test_an_unknown_field_is_refused_rather_than_ignored(self) -> None:
        with self.assertRaises(SemanticBriefResponseError):
            parse_response(
                {"subject": "penguin", "action": "sliding on belly", "provider_queries": {"en": ["penguin"]}},
                evidence=self._evidence(),
            )

    def test_a_field_of_the_wrong_type_is_refused(self) -> None:
        for answer in ({"subject": ["penguin"]}, {"subject": "penguin", "context": "snow"}):
            with self.subTest(answer=answer):
                with self.assertRaises(SemanticBriefResponseError):
                    parse_response(answer, evidence=self._evidence())

    def test_source_language_leaking_into_the_answer_is_refused(self) -> None:
        for answer in (
            {"subject": "пингвин", "action": "sliding on belly"},
            {"subject": "penguin", "action": "скользит на животе"},
            {"subject": "penguin", "context": ["снег"]},
        ):
            with self.subTest(answer=answer):
                with self.assertRaises(SemanticBriefResponseError):
                    parse_response(answer, evidence=self._evidence())

    def test_generic_production_vocabulary_is_not_a_subject(self) -> None:
        for subject in ("nature footage", "cinematic scene", "generic video content"):
            with self.subTest(subject=subject):
                with self.assertRaises(SemanticBriefResponseError):
                    parse_response({"subject": subject}, evidence=self._evidence())

    def test_a_field_longer_than_a_phrase_is_refused(self) -> None:
        with self.assertRaises(SemanticBriefResponseError):
            parse_response(
                {"subject": "a bird that lives on the ice and swims very well indeed"},
                evidence=self._evidence(),
            )

    def test_an_answer_that_asks_for_what_the_scene_forbids_is_refused(self) -> None:
        with self.assertRaises(SemanticBriefResponseError):
            parse_response(
                {"subject": "sea lion", "place": "open ocean"},
                evidence=self._evidence(must_avoid=("sea lion",)),
            )


class SemanticAdapterAvailabilityTest(unittest.TestCase):
    """An adapter is a wired *and* approved model, or it is nothing."""

    def test_without_a_model_call_the_adapter_is_unavailable(self) -> None:
        adapter = ModelSemanticBriefAdapter(approved=True)
        self.assertFalse(adapter.is_available())
        with self.assertRaises(SemanticBriefUnavailableError):
            adapter.brief_for(SceneBriefEvidence(scene_id="scene_001", narration=NARRATIONS["scene_001"]))

    def test_without_approval_a_wired_model_is_still_refused(self) -> None:
        model = _FakeSemanticModel()
        adapter = ModelSemanticBriefAdapter(model, approved=False)
        self.assertFalse(adapter.is_available())
        with self.assertRaises(SemanticBriefUnavailableError):
            adapter.brief_for(SceneBriefEvidence(scene_id="scene_001", narration=NARRATIONS["scene_001"]))
        self.assertEqual(model.calls, [])

    def test_a_backend_that_does_not_answer_becomes_a_controlled_planner_error(self) -> None:
        def explode(prompt: str, options: dict) -> str:
            raise ConnectionError("connection reset")

        adapter = _adapter(explode)
        with self.assertRaises(SemanticBriefUnavailableError) as caught:
            adapter.brief_for(SceneBriefEvidence(scene_id="scene_001", narration=NARRATIONS["scene_001"]))
        self.assertIsInstance(caught.exception, VisualPlannerError)
        self.assertTrue(caught.exception.retryable)

    def test_a_scene_with_no_evidence_is_never_sent_to_a_model(self) -> None:
        model = _FakeSemanticModel()
        with self.assertRaises(SemanticBriefUnavailableError):
            _adapter(model).brief_for(SceneBriefEvidence(scene_id="scene_001"))
        self.assertEqual(model.calls, [])


class SemanticBriefReachesTheProviderTest(unittest.TestCase):
    """The whole point: an ordinary Russian script gets an executable English query."""

    def test_today_the_same_script_cannot_reach_a_provider(self) -> None:
        script = _script()
        planning = build_plan(_request(script))
        statuses = {
            scene_id: {query.status for query in _provider_queries(planning, script, scene_id).queries}
            for scene_id in NARRATIONS
        }
        self.assertEqual(statuses["scene_002"], {STATUS_TRANSLATION_REQUIRED})
        self.assertEqual(statuses["scene_004"], {STATUS_TRANSLATION_REQUIRED})

    def test_every_scene_reaches_the_provider_with_its_own_subject(self) -> None:
        script = _script()
        model = _FakeSemanticModel()
        planning = build_plan(_request(script), brief_adapter=_adapter(model))
        self.assertEqual(len(model.calls), len(NARRATIONS))

        for scene_id, subject in EXPECTED_SUBJECTS.items():
            with self.subTest(scene_id=scene_id):
                plan = _provider_queries(planning, script, scene_id)
                executable = [query for query in plan.queries if query.status == STATUS_OK]
                self.assertTrue(executable, f"{scene_id} sent nothing to the provider")
                self.assertEqual(plan.untranslatable_providers, [])
                self.assertTrue(
                    any(subject in query.query for query in executable),
                    f"{scene_id} never asked for {subject}: {[q.query for q in executable]}",
                )
                for query in executable:
                    self.assertEqual(query.language, "en")
                    self.assertFalse(any("Ѐ" <= char <= "ӿ" for char in query.query))
                    for misleading in MISLEADING_EXTRACTED_SUBJECTS:
                        self.assertNotIn(misleading, query.query)

    def test_what_the_subject_is_doing_reaches_the_query(self) -> None:
        script = _script()
        planning = build_plan(_request(script), brief_adapter=_adapter())
        queries = {
            scene_id: " ".join(
                query.query for query in _provider_queries(planning, script, scene_id).queries
            )
            for scene_id in NARRATIONS
        }
        self.assertIn("hovering", queries["scene_002"])
        self.assertIn("sliding", queries["scene_003"])
        self.assertIn("snow", queries["scene_003"])
        self.assertIn("breaching", queries["scene_004"])
        self.assertIn("ocean", queries["scene_004"])

    def test_the_brief_the_adapter_produced_is_the_existing_one(self) -> None:
        planning = build_plan(_request(), brief_adapter=_adapter())
        scene = planning.result.scenes[2]
        self.assertEqual(scene.brief.subject, "penguin")
        self.assertEqual(scene.brief.provider_queries.keys(), {"en"})
        self.assertTrue(scene.brief.provider_queries["en"])
        stored = planning.to_legacy_plan(language="ru", script=_script().to_dict())["scenes"][2]
        self.assertEqual(stored["visual_brief"]["subject"], "penguin")
        self.assertEqual(stored["semantic"]["subject"], ["penguin"])

    def test_the_adapter_writes_no_queries_of_its_own(self) -> None:
        """Every string a provider sees is still built by the existing ladder."""
        brief = parse_response(SEMANTIC_ANSWERS["scene_004"], evidence=SceneBriefEvidence(
            scene_id="scene_004", narration=NARRATIONS["scene_004"]
        ))
        self.assertEqual(brief.provider_queries, {})


class DeterministicPathIsUnchangedTest(unittest.TestCase):
    """The model is an addition, never a dependency and never a default."""

    def test_without_an_adapter_the_plan_is_what_it_is_today(self) -> None:
        self.assertEqual(
            build_plan(_request()).result.to_dict(),
            build_plan(_request(), brief_adapter=None).result.to_dict(),
        )

    def test_an_unavailable_adapter_changes_nothing(self) -> None:
        unwired = ModelSemanticBriefAdapter(approved=True)
        self.assertEqual(
            build_plan(_request()).result.to_dict(),
            build_plan(_request(), brief_adapter=unwired).result.to_dict(),
        )

    def test_a_model_answer_that_fails_validation_leaves_the_scene_alone(self) -> None:
        # ``wildlife`` passes the parser and is still refused, one gate later: the ladder
        # will not build a query from a single category term, so nothing is overlaid.
        #
        # Compared with the warnings normalised away, because a refused answer *is*
        # recorded: what must be identical is the plan - the meaning, the intents and the
        # brief a provider is searched with - not the note saying the model did not help.
        for answer in (
            {"subject": "пингвин"},
            {"subject": "nature footage"},
            {"subject": "wildlife"},
            "not json",
            {"subject": ""},
        ):
            with self.subTest(answer=answer):
                refused = _FakeSemanticModel({scene_id: answer for scene_id in NARRATIONS})
                self.assertEqual(
                    _plan_without_warnings(build_plan(_request())),
                    _plan_without_warnings(
                        build_plan(_request(), brief_adapter=_adapter(refused))
                    ),
                )

    def test_a_deterministic_subject_is_answer_enough_and_no_model_is_asked(self) -> None:
        """The scene's own words are already the provider's words: nothing to add.

        This is the readiness contract stated positively. A deterministic brief that
        *names the subject* is what the scene is about; the repair widened assistance to
        everything short of that, and this is the line it must not cross.
        """
        script = _one_scene_script(PROVIDER_LANGUAGE_NARRATION, language="en")
        model = _FakeSemanticModel()
        planning = build_plan(_request(script, language="en"), brief_adapter=_adapter(model))
        self.assertEqual(model.calls, [])
        brief = planning.result.scenes[0].brief
        self.assertEqual(brief.subject, "antarctic")
        self.assertTrue(brief.provider_queries["en"])


class AuthorBriefStillWinsTest(unittest.TestCase):
    """Author override is the acceptance criterion the model may not weaken."""

    def test_the_explicit_author_brief_is_applied_after_the_model_brief(self) -> None:
        author = {
            "subject": "emperor penguin",
            "action": "tobogganing across sea ice",
            "provider_queries": {"en": ["author emperor penguin tobogganing"]},
        }
        script = _script(briefs={"scene_003": author})
        planning = build_plan(_request(script), brief_adapter=_adapter())
        scene = planning.result.scenes[2]
        self.assertEqual(scene.subject, "emperor penguin")
        self.assertEqual(scene.brief.subject, "emperor penguin")
        self.assertEqual(scene.brief.provider_queries, {"en": ["author emperor penguin tobogganing"]})

        executable = [
            query for query in _provider_queries(planning, script, "scene_003").queries
            if query.status == STATUS_OK
        ]
        self.assertEqual(executable[0].query, "author emperor penguin tobogganing")

    def test_the_model_brief_is_never_written_back_into_the_authors_script(self) -> None:
        script = _script()
        build_plan(_request(script), brief_adapter=_adapter())
        self.assertEqual([scene.visual_brief for scene in script.scenes], [{}] * len(script.scenes))


class SemanticReadinessTest(unittest.TestCase):
    """When assistance is offered at all - the finding that gated it on ``is_empty``.

    A brief becomes technically non-empty as soon as *any* provider-language evidence
    produces a query, and a linked English claim or a bag of prepared keywords does that
    without the plan ever learning what the scene is about. Gating on emptiness meant the
    scenes that most needed a subject were exactly the ones never offered one.
    """

    def test_an_english_claim_does_not_suppress_assistance_for_a_russian_scene(self) -> None:
        script = _one_scene_script(NARRATIONS["scene_004"], claim_ids=[LINKED_CLAIM["claim_id"]])
        model = _FakeSemanticModel({"scene_001": SEMANTIC_ANSWERS["scene_004"]})
        planning = build_plan(
            _request(script, claims=[LINKED_CLAIM]), brief_adapter=_adapter(model)
        )

        # Without the repair the brief was non-empty - it carried the claim as a query -
        # so the model was never asked and the plan kept `воды` as its subject.
        deterministic = build_plan(_request(script, claims=[LINKED_CLAIM]))
        self.assertFalse(deterministic.result.scenes[0].brief.is_empty)
        self.assertEqual(deterministic.result.scenes[0].brief.subject, "")
        self.assertIn(deterministic.result.scenes[0].subject, MISLEADING_EXTRACTED_SUBJECTS)

        self.assertEqual(len(model.calls), 1)
        scene = planning.result.scenes[0]
        self.assertEqual(scene.brief.subject, "orca")
        executable = [
            query
            for query in _provider_queries(planning, script, "scene_001").queries
            if query.status == STATUS_OK
        ]
        self.assertTrue(executable)
        self.assertTrue(any("orca" in query.query for query in executable))
        for query in executable:
            for misleading in MISLEADING_EXTRACTED_SUBJECTS:
                self.assertNotIn(misleading, query.query)

    def test_weak_prepared_keywords_do_not_suppress_assistance(self) -> None:
        script = _one_scene_script(NARRATIONS["scene_004"], keywords=["amazing animal moments"])
        deterministic = build_plan(_request(script))
        self.assertFalse(deterministic.result.scenes[0].brief.is_empty)
        self.assertEqual(deterministic.result.scenes[0].brief.subject, "")

        model = _FakeSemanticModel({"scene_001": SEMANTIC_ANSWERS["scene_004"]})
        planning = build_plan(_request(script), brief_adapter=_adapter(model))
        self.assertEqual(len(model.calls), 1)
        self.assertEqual(planning.result.scenes[0].brief.subject, "orca")

    def test_evidence_the_deterministic_producer_found_survives_a_refused_answer(self) -> None:
        """Offering assistance may not cost the scene what it already had.

        The wider gate reaches scenes whose deterministic brief is *not* empty, so a
        refused semantic answer now has something to destroy that it never had before.
        """
        script = _one_scene_script(NARRATIONS["scene_004"], claim_ids=[LINKED_CLAIM["claim_id"]])
        refused = _FakeSemanticModel({"scene_001": "not json"})
        planning = build_plan(
            _request(script, claims=[LINKED_CLAIM]), brief_adapter=_adapter(refused)
        )
        deterministic = build_plan(_request(script, claims=[LINKED_CLAIM]))
        self.assertEqual(
            planning.result.scenes[0].brief.provider_queries,
            deterministic.result.scenes[0].brief.provider_queries,
        )
        self.assertTrue(planning.result.scenes[0].brief.provider_queries["en"])


class HardConstraintsSurviveSemanticOverlayTest(unittest.TestCase):
    """A model states meaning. It was never offered authority, so it cannot spend any."""

    def test_a_hard_requirement_the_planner_set_survives_the_semantic_overlay(self) -> None:
        script = _one_scene_script(HARD_ENTITY_NARRATION)
        deterministic = build_plan(_request(script))
        self.assertEqual(deterministic.result.scenes[0].must_include, [HARD_ENTITY])
        # The name alone is one term, and the ladder's two-term floor rejects it: without
        # a model this scene reaches the adapter with no brief at all.
        self.assertIsNone(deterministic.result.scenes[0].brief)

        model = _FakeSemanticModel(
            {"scene_001": {"subject": "research station", "action": "standing on ice"}}
        )
        planning = build_plan(_request(script), brief_adapter=_adapter(model))
        scene = planning.result.scenes[0]
        self.assertEqual(scene.subject, "research station")
        self.assertEqual(scene.must_include, [HARD_ENTITY])
        self.assertEqual(scene.brief.must_include, [HARD_ENTITY])
        self.assertEqual(scene.brief.exact_entities, [HARD_ENTITY])
        self.assertTrue(
            any(HARD_ENTITY in query for query in scene.brief.provider_queries["en"]),
            scene.brief.provider_queries,
        )

    def test_a_semantic_brief_cannot_drop_a_constraint_it_was_never_asked_about(self) -> None:
        scene = build_plan(_request()).result.scenes[0]
        scene.must_include = [HARD_ENTITY]
        scene.must_avoid = ["sea lion"]
        apply_semantic_brief(scene, VisualBrief(subject="research station", place="polar coast"))
        self.assertEqual(scene.subject, "research station")
        self.assertEqual(scene.place, "polar coast")
        self.assertEqual(scene.must_include, [HARD_ENTITY])
        self.assertEqual(scene.must_avoid, ["sea lion"])

    def test_the_authors_own_overlay_semantics_are_left_exactly_as_they_were(self) -> None:
        """The author *was* asked, so their silence is still an answer. Unchanged."""
        scene = build_plan(_request()).result.scenes[0]
        scene.must_include = [HARD_ENTITY]
        scene.must_avoid = ["sea lion"]
        apply_brief(scene, VisualBrief(subject="emperor penguin"))
        self.assertEqual(scene.must_include, [])
        self.assertEqual(scene.must_avoid, ["sea lion"])


class ExpectedFailureIsNotAProgrammingDefectTest(unittest.TestCase):
    """Four ways semantic assistance can fail to help, and four distinguishable outcomes."""

    def _evidence(self) -> SceneBriefEvidence:
        return SceneBriefEvidence(scene_id="scene_001", narration=NARRATIONS["scene_001"])

    def test_a_backend_that_declares_itself_unavailable_is_passed_through(self) -> None:
        def unavailable(prompt: str, options: dict) -> str:
            raise SemanticBriefUnavailableError("модель недоступна", planner="fixture", retryable=True)

        with self.assertRaises(SemanticBriefUnavailableError) as caught:
            _adapter(unavailable).brief_for(self._evidence())
        self.assertTrue(caught.exception.retryable)

    def test_a_malformed_answer_is_a_response_error_not_an_unavailable_model(self) -> None:
        with self.assertRaises(SemanticBriefResponseError):
            _adapter(_FakeSemanticModel({"scene_001": "not json"})).brief_for(self._evidence())

    def test_a_callable_with_the_wrong_signature_is_not_reported_as_a_model_failure(self) -> None:
        def wrong_arity(prompt: str) -> str:  # the integration is wrong, not the model
            return "{}"

        with self.assertRaises(TypeError):
            _adapter(wrong_arity).brief_for(self._evidence())

    def test_a_defect_inside_the_callable_is_not_reported_as_a_model_failure(self) -> None:
        def defect(prompt: str, options: dict) -> str:
            return {}["absent"]

        with self.assertRaises(KeyError):
            _adapter(defect).brief_for(self._evidence())

    def test_each_expected_outcome_leaves_its_own_evidence_on_the_plan(self) -> None:
        def unreachable(prompt: str, options: dict) -> str:
            raise ConnectionError("connection reset")

        cases = {
            UNAVAILABLE_CODE: unreachable,
            RESPONSE_CODE: _FakeSemanticModel({"scene_001": "not json"}),
            NO_ANSWER_CODE: _FakeSemanticModel({"scene_001": {"subject": ""}}),
        }
        script = _one_scene_script(NARRATIONS["scene_004"])
        for code, model in cases.items():
            with self.subTest(code=code):
                planning = build_plan(_request(script), brief_adapter=_adapter(model))
                warnings = _scene_warnings(planning)
                self.assertTrue(
                    any(warning.startswith(f"{code}:") for warning in warnings), warnings
                )
                other = {UNAVAILABLE_CODE, RESPONSE_CODE, NO_ANSWER_CODE} - {code}
                for warning in warnings:
                    self.assertFalse(warning.startswith(tuple(f"{item}:" for item in other)), warning)

    def test_an_adapter_that_never_ran_records_nothing_at_all(self) -> None:
        """An unwired adapter has to be indistinguishable from no adapter, warnings included."""
        for adapter in (
            ModelSemanticBriefAdapter(approved=True),
            ModelSemanticBriefAdapter(_FakeSemanticModel(), approved=False),
        ):
            with self.subTest(adapter=adapter):
                self.assertEqual(
                    build_plan(_request()).result.to_dict(),
                    build_plan(_request(), brief_adapter=adapter).result.to_dict(),
                )


class AuthorBriefCostsNoModelCallTest(unittest.TestCase):
    """A scene whose answer is already written is not a question worth paying for."""

    AUTHOR = {
        "subject": "emperor penguin",
        "action": "tobogganing across sea ice",
        "provider_queries": {"en": ["author emperor penguin tobogganing"]},
    }

    def test_a_scene_the_author_already_briefed_is_never_sent_to_a_model(self) -> None:
        script = _script(briefs={"scene_003": self.AUTHOR})
        model = _FakeSemanticModel()
        build_plan(_request(script), brief_adapter=_adapter(model))
        asked = [options["scene_id"] for _, options in model.calls]
        self.assertNotIn("scene_003", asked)
        self.assertEqual(sorted(asked), ["scene_001", "scene_002", "scene_004"])

    def test_what_the_author_asked_for_is_exactly_what_it_was_before(self) -> None:
        script = _script(briefs={"scene_003": self.AUTHOR})
        model = _FakeSemanticModel()
        planning = build_plan(_request(script), brief_adapter=_adapter(model))
        scene = planning.result.scenes[2]
        self.assertEqual(scene.subject, "emperor penguin")
        self.assertEqual(scene.brief.subject, "emperor penguin")
        self.assertEqual(scene.brief.provider_queries, {"en": ["author emperor penguin tobogganing"]})

        without_model = build_plan(_request(_script(briefs={"scene_003": self.AUTHOR})))
        self.assertEqual(scene.to_dict(), without_model.result.scenes[2].to_dict())


class NoDiagnosticHardcodeTest(unittest.TestCase):
    """C35/C36 were topic literals in production code. None come back here.

    Checked against the string constants the code can actually compare against, not
    against prose: a comment naming an example is documentation, a literal is a branch.
    """

    @staticmethod
    def _string_constants(module: Path) -> list[str]:
        tree = ast.parse(module.read_text(encoding="utf-8"))
        documented = {
            id(node.body[0].value)
            for node in ast.walk(tree)
            if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
            and node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)
        }
        return [
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in documented
        ]

    def test_the_visual_planning_package_knows_no_diagnostic_subject(self) -> None:
        package = Path(__file__).resolve().parents[1] / "src" / "content" / "visual_planning"
        for module in sorted(package.rglob("*.py")):
            literals = " ".join(self._string_constants(module)).casefold()
            for term in DIAGNOSTIC_TERMS:
                with self.subTest(module=module.name, term=term):
                    self.assertNotIn(term, literals)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
