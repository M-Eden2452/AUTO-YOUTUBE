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

The second repair pass, again before any model was wired, closes the two findings that
survived it:

- *naming* a provider-language subject was still being read as *knowing* the subject.
  An ordinary English sentence hands deterministic extraction ``antarctic`` for a scene
  about a penguin colony, and the scene then refused the only help that could correct
  it. Sufficiency is now decided by where the subject came from - the topic the producer
  stated for this video, which ``collect_entities`` already records on the entity - and
  never by what the word looks like;
- a backend that really ran and failed permanently recorded nothing, because
  ``retryable`` was being read as "was anything asked". Whether a backend was reached is
  now decided before it is called, so every controlled failure of a real attempt leaves
  its warning and every adapter that never ran still leaves the plan untouched.

The third repair pass, still before any model was wired, closes the last blocker in
front of live activation. Both halves are about *authority*, not about meaning:

- correcting the subject could not finish the job, because the requirement the planner
  had guessed outlived the correction. ``must_include`` refuses candidates outright, and
  the deterministic planner was writing it from its own extraction whenever the word was
  Latin - so the right penguin footage was refused at 100% subject match for missing
  ``NASA``. The planner no longer states requirements; an author still does, and that is
  still hard and still blocking;
- ``ENTITY_KIND_TOPIC`` on the subject is no longer read as "planning knows what this
  scene shows". A topic is a statement about the video, and one that names both the
  subject and its surroundings marks them alike, so it cannot choose between them.

No network (``tests.network_guard`` is installed package-wide), no provider call, no
model call: every "model" here is a dictionary.
"""

from __future__ import annotations

import ast
import json
import unittest
from pathlib import Path

from src.assets.query_adapter import STATUS_OK, STATUS_TRANSLATION_REQUIRED, build_scene_queries
from src.assets.semantic_selection.candidate_ranker import rank_candidates
from src.assets.semantic_selection.scene_analyzer import analyze_scene
from src.content.script_engine import ScriptResult, ScriptScene
from src.content.visual_planning import (
    SHOT_ACTION,
    VisualPlanRequest,
    VisualPlannerError,
    build_plan,
)
from src.content.visual_planning.brief import VisualBrief, apply_brief
from src.content.visual_planning.models import ENTITY_KIND_TOPIC
from src.content.visual_planning.expansion import PROVIDER_LANGUAGE
from src.content.visual_planning.semantic_brief import (
    MAX_CONTEXT_ITEMS,
    MAX_FIELD_TERMS,
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
# names *a* subject here - and names the wrong one: the sentence is about the colony and
# ``antarctic`` is merely where it is. Latin, queryable, and not what the frame is about.
PROVIDER_LANGUAGE_NARRATION = "An emperor penguin colony crosses the antarctic sea ice."
UNDECLARED_EXTRACTED_SUBJECT = "antarctic"

# The same scene under a topic that states what the video is about. ``collect_entities``
# marks the entity the topic names, which is how the plan can say *why* it believes its
# subject rather than only that it has one.
DECLARING_TOPIC = "How the penguin survives"
DECLARED_SUBJECT = "penguin"

# A provider-language scene with research linked to it. The cited prose names the coast
# as readily as the animal, so "some claim mentions this word" corroborates the wrong
# subject just as happily as the right one.
RESEARCH_NARRATION = "The orca breaches completely out of the cold water off the coast."
RESEARCH_EXTRACTED_SUBJECT = "coast"
COAST_CLAIM = {
    "claim_id": "claim_002",
    "text": "Orca pods were observed hunting along the coast.",
    "safe_for_script": True,
}

# An ordinary Russian scene that happens to name a place in Latin script. Extraction
# ranks that name above every Cyrillic word in the sentence, because a Latin token needs
# no translation to reach a provider - so it becomes the subject of a scene that is not
# about it.
HARD_ENTITY_NARRATION = (
    "Полярная станция McMurdo стоит на краю ледника, и учёные каждый день выходят на лёд."
)
HARD_ENTITY = "McMurdo"

# The same shape, production-reachable: an ordinary Russian sentence about penguins that
# cites a satellite programme. ``NASA`` is Latin, so extraction makes it the subject, and
# the scene is not about NASA at all. What the frame must contain here was never stated
# by anyone - it was inferred from one word's alphabet.
HEURISTIC_LATIN_NARRATION = (
    "Спутники NASA показали, как пингвины на льду собираются в большую колонию."
)
HEURISTIC_EXTRACTED_SUBJECT = "NASA"
PENGUIN_ANSWER = {
    "subject": "penguin colony",
    "action": "gathering on sea ice",
    "place": "antarctic ice",
}
# The candidate a person would call correct for that scene. Stock metadata as a provider
# writes it, so the ranker judges real text rather than the query it came from.
PENGUIN_CANDIDATE = {
    "asset_id": "stock-penguin-1",
    "provider": "pexels",
    "title": "Emperor penguin colony gathering on Antarctic sea ice",
    "description": "A large colony of emperor penguins gathering on the sea ice in Antarctica.",
    "media_type": "video",
    "width": 1080,
    "height": 1920,
    "duration_sec": 12.0,
    "allowed_for_render": True,
}

# A topic that names the subject *and* its surroundings. Both words are marked
# ``topic_entity``, so "the topic names this word" cannot tell which of them the scene is
# about - and extraction picks the wrong one.
MULTI_ROLE_TOPIC = "Antarctic penguin colonies"

# What an author states when they mean it: a scene-level brief, written beside the
# narration. This is the only structured scene-level source in the repository that
# carries authority over what the frame must contain.
AUTHOR_REQUIREMENT = "research station"

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


class PromptStatesTheParserContractTest(unittest.TestCase):
    """The first live run: three of six usable answers refused by unstated rules.

    ``gpt-4.1`` understood every scene. What it did not know was that ``action`` is a
    phrase and not a clause, that a ``context`` item is bound by the same ceiling, and
    that the on-screen text it was shown is evidence rather than something to repeat.
    Each of those was already enforced by ``parse_response`` and stated nowhere the
    model could read it. The fix is on the asking side: the parser below is unchanged.
    """

    def _prompt(self, **overrides) -> str:
        base = {
            "scene_id": "scene_001",
            "narration": NARRATIONS["scene_001"],
            "on_screen_text": "Геккон бежит по стеклу",
        }
        base.update(overrides)
        return build_prompt(SceneBriefEvidence(**base))

    def _rules(self, **overrides) -> str:
        """The instructions only - the schema dump is asserted on separately."""
        return self._prompt(**overrides).split("Ответ — строго JSON")[0]

    def test_the_word_ceiling_the_parser_enforces_is_stated_to_the_model(self) -> None:
        self.assertIn(str(MAX_FIELD_TERMS), self._rules())

    def test_the_context_item_ceiling_is_stated_to_the_model(self) -> None:
        self.assertIn(str(MAX_CONTEXT_ITEMS), self._rules())

    def test_the_provider_language_requirement_is_stated_to_the_model(self) -> None:
        self.assertIn(PROVIDER_LANGUAGE, self._rules())

    def test_the_model_is_told_the_values_are_search_phrases(self) -> None:
        rules = self._rules()
        self.assertIn("поисков", rules)
        self.assertIn("не предложение", rules)

    def test_the_model_is_told_not_to_quote_the_narration(self) -> None:
        self.assertIn("не цитируй", self._rules().casefold())

    def test_the_model_is_told_not_to_repeat_the_on_screen_text(self) -> None:
        rules = self._rules()
        self.assertIn("текст на экране", rules)
        self.assertIn("не переноси", rules.casefold())
        # The evidence is still sent: it is material to understand, not to copy.
        self.assertIn("Геккон бежит по стеклу", self._prompt())

    def test_the_model_is_told_not_to_explain_itself(self) -> None:
        self.assertIn("пояснен", self._rules())

    def test_the_contract_itself_carries_the_limits_it_is_judged_by(self) -> None:
        """The schema dump travels with the prompt, so it may not contradict it."""
        for field in ("subject", "action", "place"):
            with self.subTest(field=field):
                self.assertIn(str(MAX_FIELD_TERMS), RESPONSE_CONTRACT[field])
                self.assertIn(PROVIDER_LANGUAGE, RESPONSE_CONTRACT[field])
        context = RESPONSE_CONTRACT["context"][0]
        self.assertIn(str(MAX_FIELD_TERMS), context)
        self.assertIn(str(MAX_CONTEXT_ITEMS), context)

    def test_the_limits_are_not_copied_by_hand_beside_the_constants(self) -> None:
        """A number written twice is a number that drifts once."""
        source = Path("src/content/visual_planning/semantic_brief.py").read_text(encoding="utf-8")
        body = source.split("MAX_CONTEXT_ITEMS = ", 1)[1].split("\n", 1)[1]
        for literal in (str(MAX_FIELD_TERMS), str(MAX_CONTEXT_ITEMS)):
            with self.subTest(literal=literal):
                self.assertNotIn(f" {literal} слов", body)
                self.assertNotIn(f" {literal} элемент", body)


class LiveRejectionsStayRejectionsTest(unittest.TestCase):
    """The parser was not loosened to make the refused answers pass.

    These are the three shapes the first real Russian diagnostic produced. Telling the
    model about a rule is the repair; accepting the answers that broke it would be the
    opposite of one.
    """

    def _evidence(self) -> SceneBriefEvidence:
        return SceneBriefEvidence(scene_id="scene_001", narration=NARRATIONS["scene_001"])

    def test_a_context_item_longer_than_a_phrase_is_still_refused(self) -> None:
        with self.assertRaises(SemanticBriefResponseError):
            parse_response(
                {
                    "subject": "gecko",
                    "context": ["a close-up view of the gecko toes gripping the smooth glass"],
                },
                evidence=self._evidence(),
            )

    def test_an_action_longer_than_a_phrase_is_still_refused(self) -> None:
        with self.assertRaises(SemanticBriefResponseError):
            parse_response(
                {
                    "subject": "penguin",
                    "action": "lying down on its belly and sliding across the snow and ice",
                },
                evidence=self._evidence(),
            )

    def test_the_scenes_own_on_screen_text_is_still_refused_as_context(self) -> None:
        with self.assertRaises(SemanticBriefResponseError):
            parse_response(
                {
                    "subject": "gecko",
                    "context": ["visual text: 'Каждый из этих трюков выглядит'"],
                },
                evidence=self._evidence(),
            )

    def test_more_context_items_than_the_contract_allows_is_still_refused(self) -> None:
        with self.assertRaises(SemanticBriefResponseError):
            parse_response(
                {"subject": "gecko", "context": ["glass"] * (MAX_CONTEXT_ITEMS + 1)},
                evidence=self._evidence(),
            )

    def test_an_answer_that_obeys_every_stated_rule_is_accepted(self) -> None:
        brief = parse_response(
            {
                "subject": "gecko",
                "action": "running on glass",
                "place": "smooth glass pane",
                "context": ["gecko feet", "transparent surface"],
            },
            evidence=self._evidence(),
        )
        self.assertEqual(brief.subject, "gecko")
        self.assertEqual(brief.context, ["gecko feet", "transparent surface"])


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

    def test_a_provider_language_scene_is_untouched_by_an_adapter_that_never_ran(self) -> None:
        script = _one_scene_script(PROVIDER_LANGUAGE_NARRATION, language="en")
        self.assertEqual(
            build_plan(_request(script, language="en")).result.to_dict(),
            build_plan(
                _request(script, language="en"),
                brief_adapter=ModelSemanticBriefAdapter(approved=True),
            ).result.to_dict(),
        )


class DeterministicSubjectSufficiencyTest(unittest.TestCase):
    """When a deterministic subject is trusted enough to skip the model, and *why*.

    "The brief names a provider-language subject" was being read as "deterministic
    planning understood what this scene is about". The repository says those are not the
    same fact: the planner ranks the words a sentence uses, so an ordinary English
    sentence hands it the place instead of the thing standing in it - and a subject that
    is wrong but Latin was suppressing the only help that could correct it.

    What replaces it is not a judgement about the word either. Provenance decides, and the
    owner decision of this repair narrows what counts: a word occurring inside the *global*
    topic string is not a scene-level statement about *this* scene. ``Antarctic penguin
    colonies`` marks ``antarctic`` and ``penguin`` alike, so the topic cannot say which of
    them the scene is about - and extraction, left to choose, chose the place.

    The only structured scene-level source in the repository that carries real authority
    over what a scene shows is the author's own ``visual_brief``, which already skips the
    model (``AuthorBriefCostsNoModelCallTest``). No second one was invented for this
    repair: no confidence field, no score, no provenance enum, no classifier. An ordinary
    automatically-planned scene is simply eligible for one model call.
    """

    SEMANTIC_ANSWER = {"subject": "emperor penguin", "action": "walking on sea ice"}

    def _subject_entities(self, planning) -> list:
        """The planner's own record for the entity it made the subject."""
        scene = planning.result.scenes[0]
        return [entity for entity in scene.entities if entity.surface == scene.subject]

    def test_a_provider_language_subject_nothing_declared_does_not_suppress_help(self) -> None:
        script = _one_scene_script(PROVIDER_LANGUAGE_NARRATION, language="en")
        deterministic = build_plan(_request(script, language="en"))
        scene = deterministic.result.scenes[0]
        # The reproduction: a brief that names a subject, in the provider's language, and
        # names the wrong one. Nothing but the sentence's own word order chose it.
        self.assertEqual(scene.brief.subject, UNDECLARED_EXTRACTED_SUBJECT)
        self.assertEqual([entity.kind for entity in self._subject_entities(deterministic)], ["entity"])

        model = _FakeSemanticModel({"scene_001": self.SEMANTIC_ANSWER})
        planning = build_plan(_request(script, language="en"), brief_adapter=_adapter(model))
        self.assertEqual(len(model.calls), 1)
        assisted = planning.result.scenes[0]
        self.assertEqual(assisted.brief.subject, self.SEMANTIC_ANSWER["subject"])
        self.assertTrue(
            any(self.SEMANTIC_ANSWER["subject"] in query for query in assisted.brief.provider_queries["en"]),
            assisted.brief.provider_queries,
        )
        # The requirement extraction used to state on its own behalf. It is not the
        # model's to delete - and it is no longer the planner's to write.
        self.assertEqual(assisted.must_include, [])

    def test_a_word_the_global_topic_names_does_not_settle_what_a_scene_shows(self) -> None:
        """The topic route, withdrawn: one word of it is not a scene-level statement.

        ``DECLARING_TOPIC`` names exactly one thing, which is the easiest case the
        withdrawn rule had, and even here the topic is a statement about the *video*. The
        scene is still planned automatically, so it is still eligible for the one call
        that can confirm or correct the guess.
        """
        script = _one_scene_script(PROVIDER_LANGUAGE_NARRATION, language="en")
        model = _FakeSemanticModel({"scene_001": self.SEMANTIC_ANSWER})
        planning = build_plan(
            _request(script, language="en", topic=DECLARING_TOPIC, title=DECLARING_TOPIC),
            brief_adapter=_adapter(model),
        )
        deterministic = build_plan(
            _request(script, language="en", topic=DECLARING_TOPIC, title=DECLARING_TOPIC)
        )
        # The entity record is unchanged - this repair withdrew a use of it, not the mark.
        self.assertEqual(
            [entity.kind for entity in self._subject_entities(deterministic)], ["topic_entity"]
        )
        self.assertEqual(deterministic.result.scenes[0].brief.subject, DECLARED_SUBJECT)

        self.assertEqual(len(model.calls), 1)
        self.assertEqual(planning.result.scenes[0].brief.subject, self.SEMANTIC_ANSWER["subject"])

    def test_a_topic_naming_both_the_subject_and_its_surroundings_cannot_choose(self) -> None:
        """Why one topic word was never enough, reproduced.

        The topic states the subject *and* where it is, so both words are marked
        ``topic_entity`` and extraction still takes the place. Under the withdrawn rule
        that mark was read as "the producer declared this subject" and the scene refused
        assistance - the wrong subject protected by the presence of the right one.
        """
        script = _one_scene_script(PROVIDER_LANGUAGE_NARRATION, language="en")
        request = _request(script, language="en", topic=MULTI_ROLE_TOPIC, title=MULTI_ROLE_TOPIC)
        deterministic = build_plan(request).result.scenes[0]
        self.assertEqual(deterministic.subject, UNDECLARED_EXTRACTED_SUBJECT)
        # Both roles carry the same mark, which is why the mark cannot separate them.
        marked = {
            entity.surface.casefold()
            for entity in deterministic.entities
            if entity.kind == ENTITY_KIND_TOPIC
        }
        self.assertIn(UNDECLARED_EXTRACTED_SUBJECT, marked)
        self.assertIn(DECLARED_SUBJECT, marked)

        model = _FakeSemanticModel({"scene_001": self.SEMANTIC_ANSWER})
        planning = build_plan(request, brief_adapter=_adapter(model))
        self.assertEqual(len(model.calls), 1)
        self.assertEqual(planning.result.scenes[0].brief.subject, self.SEMANTIC_ANSWER["subject"])

    def test_research_the_scene_cites_is_not_a_declaration_of_what_to_show(self) -> None:
        """Corroboration is not declaration, so ``source_refs`` is not a second route.

        A claim reference records that cited prose contains the word. Cited prose contains
        the scene's environment too, and here it corroborates the coast - the same
        wrong-subject shape the topic route exists to catch. Pinned so a later widening
        has to argue with a reproduction rather than with a preference.
        """
        script = _one_scene_script(
            RESEARCH_NARRATION, language="en", claim_ids=[COAST_CLAIM["claim_id"]]
        )
        deterministic = build_plan(_request(script, language="en", claims=[COAST_CLAIM]))
        self.assertEqual(deterministic.result.scenes[0].brief.subject, RESEARCH_EXTRACTED_SUBJECT)
        self.assertEqual(
            [entity.source_refs for entity in self._subject_entities(deterministic)],
            [[COAST_CLAIM["claim_id"]]],
        )

        model = _FakeSemanticModel({"scene_001": {"subject": "orca", "action": "breaching out of water"}})
        planning = build_plan(
            _request(script, language="en", claims=[COAST_CLAIM]), brief_adapter=_adapter(model)
        )
        self.assertEqual(len(model.calls), 1)
        self.assertEqual(planning.result.scenes[0].brief.subject, "orca")


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

    def test_the_planner_states_no_requirement_of_its_own_any_more(self) -> None:
        """The intentional delta, and the proof it costs no information.

        ``McMurdo`` used to become a hard requirement here purely because it is Latin.
        It still becomes the subject and still leads every intent - what it no longer does
        is refuse candidates. Authority was withdrawn; the extraction was not.
        """
        script = _one_scene_script(HARD_ENTITY_NARRATION)
        scene = build_plan(_request(script)).result.scenes[0]
        self.assertEqual(scene.must_include, [])
        self.assertEqual(scene.subject, HARD_ENTITY)
        self.assertEqual(scene.intents[0].subject, HARD_ENTITY)

    def test_a_semantic_brief_cannot_drop_a_constraint_it_was_never_asked_about(self) -> None:
        """The preservation contract itself, exercised directly.

        Since the planner stopped writing constraints, the only scenes carrying one are
        the ones an author briefed - and those are never sent to a model. So this is now a
        guard on the rule rather than a reproduction of a live path: whoever gives
        ``apply_semantic_brief`` a scene with constraints gets them back.
        """
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


class AttemptedBackendFailureIsVisibleTest(unittest.TestCase):
    """A backend that ran and failed is a different event from an adapter that never ran.

    ``retryable`` answers "would asking again help". It was being read as "was anything
    asked at all", and those come apart precisely where it matters: every precondition of
    the adapter raises the same non-retryable unavailable error that a backend raises when
    it says *permanently* no - a rejected key, a model the account may not select. A real
    call that failed for good therefore left the plan byte-identical to a run with no
    adapter, which is the one distinction a later diagnostic has to be able to make.

    Whether a backend was reached is decided from the adapter's own preconditions, before
    it is called, so the two questions stop being answered by the same flag.
    """

    NARRATION = NARRATIONS["scene_004"]

    def _warnings(self, adapter) -> list[str]:
        return _scene_warnings(
            build_plan(_request(_one_scene_script(self.NARRATION)), brief_adapter=adapter)
        )

    def test_a_backend_that_failed_for_good_is_recorded_like_one_that_may_recover(self) -> None:
        for retryable in (True, False):
            with self.subTest(retryable=retryable):
                def refuse(prompt: str, options: dict, retryable: bool = retryable) -> str:
                    raise SemanticBriefUnavailableError(
                        "модель недоступна", planner="fixture", retryable=retryable
                    )

                warnings = self._warnings(_adapter(refuse))
                self.assertTrue(
                    any(warning.startswith(f"{UNAVAILABLE_CODE}:") for warning in warnings), warnings
                )

    def test_an_adapter_that_never_reached_a_backend_still_records_nothing(self) -> None:
        silent = _scene_warnings(build_plan(_request(_one_scene_script(self.NARRATION))))
        for label, adapter in (
            ("unwired", ModelSemanticBriefAdapter(approved=True)),
            ("unapproved", ModelSemanticBriefAdapter(_FakeSemanticModel(), approved=False)),
        ):
            with self.subTest(adapter=label):
                self.assertEqual(self._warnings(adapter), silent)

    def test_a_scene_with_nothing_to_ask_about_is_not_an_attempt(self) -> None:
        """The remaining precondition, and the one that must stay silent."""
        script = _one_scene_script("")
        model = _FakeSemanticModel()
        planning = build_plan(_request(script), brief_adapter=_adapter(model))
        self.assertEqual(model.calls, [])
        self.assertEqual(_scene_warnings(planning), _scene_warnings(build_plan(_request(script))))


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

    def test_a_script_briefed_throughout_costs_no_model_call_at_all(self) -> None:
        script = _script(briefs={scene_id: self.AUTHOR for scene_id in NARRATIONS})
        model = _FakeSemanticModel()
        build_plan(_request(script), brief_adapter=_adapter(model))
        self.assertEqual(model.calls, [])

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


class HeuristicRequirementIsNotAuthorAuthorityTest(unittest.TestCase):
    """A guess may not be enforced like a statement.

    ``must_include`` is a hard requirement: ``candidate_ranker`` refuses any candidate
    whose provider metadata does not contain every term, whatever else it scores. The
    repository describes that authority as the author's throughout - ``decision``,
    ``evidence`` and the ranker itself all call it "what the author explicitly required" -
    but the deterministic planner was writing it from its own extraction, purely because
    the word happened to be Latin.

    That made semantic correction unable to finish its job. The model rewrites what the
    scene is *about*; it holds no authority over constraints and therefore cannot clear
    one, so the guess outlived the correction and refused the very candidate the
    correction was for.

    These tests run the whole path a Short runs - plan, legacy plan, ``analyze_scene``,
    ``rank_candidates`` - because a field-level assertion cannot show that the *blocking*
    consequence is gone.
    """

    def _ranked(self, planning, script: ScriptResult, candidate: dict) -> dict:
        plan = planning.to_legacy_plan(language="ru", script=script.to_dict())
        semantic_scene = analyze_scene(plan["scenes"][0])
        ranked = rank_candidates(
            semantic_scene, [dict(candidate)], require_provider_metadata=True
        )
        # Named apart from the ranker's own ``semantic_scene``, which is that object
        # already flattened to a dict.
        return {**ranked[0], "analyzed_scene": semantic_scene}

    def test_the_extracted_subject_is_not_promoted_to_a_hard_requirement(self) -> None:
        """The source of the defect: extraction stating what the frame must contain."""
        script = _one_scene_script(HEURISTIC_LATIN_NARRATION)
        scene = build_plan(_request(script)).result.scenes[0]
        # Unchanged: this *is* still the subject extraction picks, and picking it is not
        # what this repair is about. Pinned so the reproduction stays honest.
        self.assertEqual(scene.subject, HEURISTIC_EXTRACTED_SUBJECT)
        self.assertEqual(scene.must_include, [])

    def test_a_corrected_subject_is_not_refused_over_the_guess_it_replaced(self) -> None:
        """The reproduction, end to end, at the owner of the decision.

        Before this repair the same candidate came back
        ``blocking_reject_reasons=['must_include_missing:NASA']`` at
        ``subject_match=100.0`` - the ranker refusing the right penguin footage for a
        space agency nobody asked to see.
        """
        script = _one_scene_script(HEURISTIC_LATIN_NARRATION)
        model = _FakeSemanticModel({"scene_001": PENGUIN_ANSWER})
        planning = build_plan(_request(script), brief_adapter=_adapter(model))

        scene = planning.result.scenes[0]
        self.assertEqual(scene.subject, PENGUIN_ANSWER["subject"])
        self.assertEqual(scene.must_include, [])

        result = self._ranked(planning, script, PENGUIN_CANDIDATE)
        self.assertEqual(result["analyzed_scene"].must_include, [])
        self.assertEqual(result["subject_match"], 100.0)
        self.assertEqual(result["blocking_reject_reasons"], [])
        self.assertFalse(result["rejected"])

    def _authored(self, required: str) -> dict:
        """The same scene an author described, differing only in what they required.

        The brief states the shot as well, so the only variable between the two tests
        below is the required term - and neither depends on a model having run.
        """
        script = _one_scene_script(
            HEURISTIC_LATIN_NARRATION, visual_brief={**PENGUIN_ANSWER, "must_include": [required]}
        )
        planning = build_plan(_request(script))
        self.assertEqual(planning.result.scenes[0].must_include, [required])
        return self._ranked(planning, script, PENGUIN_CANDIDATE)

    def test_an_explicit_author_requirement_still_refuses_a_candidate_that_misses_it(self) -> None:
        """The other half: hard constraints are not weakened, only re-sourced.

        The candidate is the right footage for the scene and scores as such. It is refused
        anyway, because a person wrote down something the frame must contain and this frame
        does not contain it. That is what ``must_include`` is for, and it still works.
        """
        result = self._authored(AUTHOR_REQUIREMENT)
        self.assertEqual(result["analyzed_scene"].must_include, [AUTHOR_REQUIREMENT])
        self.assertEqual(result["subject_match"], 100.0)
        self.assertIn(
            f"must_include_missing:{AUTHOR_REQUIREMENT}", result["blocking_reject_reasons"]
        )
        self.assertTrue(result["rejected"])

    def test_an_author_requirement_the_candidate_satisfies_is_not_a_refusal(self) -> None:
        """So the test above is proved to be about the requirement, not about the fixture."""
        result = self._authored("sea ice")
        self.assertEqual(result["analyzed_scene"].must_include, ["sea ice"])
        self.assertEqual(result["blocking_reject_reasons"], [])
        self.assertFalse(result["rejected"])


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
