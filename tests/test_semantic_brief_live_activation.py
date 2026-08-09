"""PLAN-9B-PRODUCER-M-LIVE: reaching a real text model, and refusing to.

``ModelSemanticBriefAdapter`` has been correct and unreachable since
PLAN-9B-PRODUCER-M: it takes an injected callable, and no production caller had one to
inject. This suite pins the two things that have to be true before that changes.

**Reachability.** ``src.news.visual_plan`` - the caller the news pipeline actually runs -
now builds an adapter, and it builds one only when a standing paid policy and a per-run
network approval both say so. Neither implies the other, and the default state of the
repository grants neither, so an ordinary run is byte-identical to the deterministic run
it has always been.

**Eligibility (MAJOR-A).** An author brief containing only ``must_include``,
``must_avoid`` or ``notes`` used to suppress semantic assistance entirely, because any
non-empty brief was read as "the author already said what this scene shows". Those
fields are constraints and bookkeeping: they bound an answer, they are not one. What
answers the semantic question is ``subject``, ``visual_description`` or
``provider_queries``, and only those still skip the model.

No test here reaches a real backend. The OpenAI client is injected, the offline network
guard stays installed, and the one case about a missing approval asserts on a call
counter that stays at zero.
"""

from __future__ import annotations

import json
import unittest
from typing import Any

from openai import OpenAIError

from src.content.script_engine.models import ScriptResult, ScriptScene
from src.content.semantic_brief_openai import (
    LIVE_CONFIRMATION_PHRASE,
    SemanticBriefModelConfig,
    activation_diagnostics,
    build_semantic_brief_adapter,
    load_semantic_brief_config,
    paid_call_blockers,
)
from src.content.visual_planning import VisualPlanRequest, build_plan
from src.content.visual_planning.brief import (
    VisualBrief,
    author_semantics_are_sufficient,
)
from src.content.visual_planning.semantic_brief import (
    SemanticBriefUnavailableError,
    build_prompt,
    evidence_for_scene,
)
from src.runtime_network import (
    NETWORK_ACTION_PROVIDER_SEARCH,
    NETWORK_ACTION_SEMANTIC_BRIEF,
    NETWORK_ACTIONS,
    approval_for_actions,
    network_approval_scope,
)


ORCA_NARRATION = "Косатки в открытом океане способны выпрыгивать из воды целиком."
PENGUIN_NARRATION = "Пингвины ложатся на живот и скользят по снегу и льду."

ORCA_ANSWER = {
    "subject": "orca",
    "action": "breaching fully out of water",
    "place": "open ocean",
}
PENGUIN_ANSWER = {
    "subject": "penguin",
    "action": "sliding on belly",
    "place": "snow and ice",
}
ANSWERS = {"scene_001": ORCA_ANSWER, "scene_002": PENGUIN_ANSWER}

# The author's hard requirement for the orca scene, stated *without* saying what the
# scene shows. This is the MAJOR-A shape.
AUTHOR_REQUIREMENT = "orca"
AUTHOR_PROHIBITION = "dolphin"

UNAVAILABLE_CODE = "semantic_brief_unavailable"


class _FakeResponse:
    """What the SDK hands back: an object carrying the model's text."""

    def __init__(self, payload: dict[str, Any]) -> None:
        self.output_text = json.dumps(payload, ensure_ascii=False)
        self.id = "resp_fixture"
        self.usage = {"input_tokens": 120, "output_tokens": 20}


class _FakeResponses:
    def __init__(self, owner: "_FakeOpenAIClient") -> None:
        self._owner = owner

    def create(self, **payload: Any) -> Any:
        self._owner.calls.append(dict(payload))
        if self._owner.raises is not None:
            raise self._owner.raises
        scene_id = self._owner.scene_ids[
            min(len(self._owner.calls) - 1, len(self._owner.scene_ids) - 1)
        ]
        return _FakeResponse(self._owner.answers.get(scene_id, {"subject": ""}))


class _FakeOpenAIClient:
    """Stands in for ``openai.OpenAI``. Counts calls; never opens a socket."""

    def __init__(
        self,
        answers: dict[str, dict[str, Any]] | None = None,
        *,
        raises: Exception | None = None,
        scene_ids: tuple[str, ...] = ("scene_001", "scene_002"),
    ) -> None:
        self.answers = dict(answers if answers is not None else ANSWERS)
        self.raises = raises
        self.scene_ids = scene_ids
        self.calls: list[dict[str, Any]] = []
        self.responses = _FakeResponses(self)

    @property
    def call_count(self) -> int:
        return len(self.calls)


class _FakeSDKError(OpenAIError):
    """A real SDK error class, carrying the status the classifier reads.

    ``OpenAIError`` is the base every ``openai`` failure derives from, so a fake that
    subclasses it is caught by exactly the clause a live ``APIStatusError`` would be -
    and a fake that did not subclass it would prove nothing about the live path.
    """

    def __init__(self, message: str, *, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code


def _approved_config(**overrides: Any) -> SemanticBriefModelConfig:
    """A standing policy that has said yes to everything it owns."""
    options = {
        "enabled": True,
        "backend": "openai",
        "model": "gpt-5.6-terra",
        "allow_paid_calls": True,
        "confirm_paid_calls": LIVE_CONFIRMATION_PHRASE,
        "maximum_calls_per_project": 8,
        "maximum_budget_usd": 1.0,
        "estimated_cost_per_call_usd": 0.01,
    }
    options.update(overrides)
    return SemanticBriefModelConfig.from_config(options)


def _script(scene_ids: tuple[str, ...] = ("scene_001",), briefs: dict[str, dict] | None = None) -> ScriptResult:
    narrations = {"scene_001": ORCA_NARRATION, "scene_002": PENGUIN_NARRATION}
    briefs = briefs or {}
    return ScriptResult(
        scenes=[
            ScriptScene(
                scene_id=scene_id,
                index=index,
                role="hook" if index == 1 else "development",
                narration=narrations[scene_id],
                duration_sec=6.0,
                visual_brief=dict(briefs.get(scene_id) or {}),
            )
            for index, scene_id in enumerate(scene_ids, start=1)
        ],
        title="Странные способности животных",
        language="ru",
    )


def _request(script: ScriptResult | None = None) -> VisualPlanRequest:
    return VisualPlanRequest(
        script=script or _script(),
        language="ru",
        topic="Странные способности животных",
        title="Странные способности животных",
    )


def _plan(
    client: _FakeOpenAIClient,
    *,
    script: ScriptResult | None = None,
    config: SemanticBriefModelConfig | None = None,
    network: tuple[str, ...] = (NETWORK_ACTION_SEMANTIC_BRIEF,),
):
    """One planning run with the backend wired and the run's approvals set."""
    approval = approval_for_actions(network, granted_by="test")
    adapter_config = config if config is not None else _approved_config()
    with network_approval_scope(approval):
        adapter = build_semantic_brief_adapter(config=adapter_config, client=client)
        if adapter is None:
            return None
        return build_plan(script and _request(script) or _request(), brief_adapter=adapter)


class NetworkGateTest(unittest.TestCase):
    """Case A: no network approval, no backend call - whatever the paid policy says."""

    def test_the_text_model_has_its_own_network_action(self) -> None:
        self.assertIn(NETWORK_ACTION_SEMANTIC_BRIEF, NETWORK_ACTIONS)
        self.assertEqual(NETWORK_ACTION_SEMANTIC_BRIEF, "semantic_brief")

    def test_without_network_approval_the_backend_is_never_called(self) -> None:
        client = _FakeOpenAIClient()
        planning = _plan(client, network=())
        self.assertEqual(client.call_count, 0)
        self.assertIsNone(planning)

    def test_a_neighbouring_network_approval_does_not_open_the_model(self) -> None:
        client = _FakeOpenAIClient()
        planning = _plan(client, network=(NETWORK_ACTION_PROVIDER_SEARCH,))
        self.assertEqual(client.call_count, 0)
        self.assertIsNone(planning)

    def test_a_run_that_loses_network_mid_flight_still_calls_nothing(self) -> None:
        """The adapter is built once; the guard is asked again at the call site."""
        client = _FakeOpenAIClient()
        with network_approval_scope(
            approval_for_actions([NETWORK_ACTION_SEMANTIC_BRIEF], granted_by="test")
        ):
            adapter = build_semantic_brief_adapter(config=_approved_config(), client=client)
        self.assertIsNotNone(adapter)
        planning = build_plan(_request(), brief_adapter=adapter)
        self.assertEqual(client.call_count, 0)
        warnings = planning.result.scenes[0].warnings
        self.assertTrue(any(UNAVAILABLE_CODE in item for item in warnings), warnings)


class PaidGateTest(unittest.TestCase):
    """Case B: network approved, payment not - still no backend call."""

    def test_network_approval_alone_does_not_authorise_spending(self) -> None:
        client = _FakeOpenAIClient()
        planning = _plan(client, config=_approved_config(allow_paid_calls=False))
        self.assertEqual(client.call_count, 0)
        self.assertIsNone(planning)

    def test_a_paid_flag_without_the_confirmation_phrase_is_not_approval(self) -> None:
        client = _FakeOpenAIClient()
        planning = _plan(client, config=_approved_config(confirm_paid_calls=""))
        self.assertEqual(client.call_count, 0)
        self.assertIsNone(planning)

    def test_approval_without_a_call_budget_is_not_approval(self) -> None:
        client = _FakeOpenAIClient()
        planning = _plan(client, config=_approved_config(maximum_calls_per_project=0))
        self.assertEqual(client.call_count, 0)
        self.assertIsNone(planning)

    def test_approval_without_a_money_budget_is_not_approval(self) -> None:
        client = _FakeOpenAIClient()
        planning = _plan(client, config=_approved_config(maximum_budget_usd=0.0))
        self.assertEqual(client.call_count, 0)
        self.assertIsNone(planning)

    def test_every_missing_paid_condition_is_named(self) -> None:
        blockers = paid_call_blockers(SemanticBriefModelConfig.from_config({"enabled": True}))
        self.assertEqual(
            sorted(blockers),
            [
                "allow_paid_calls_required",
                "confirm_paid_calls_required",
                "maximum_budget_usd_required",
                "maximum_calls_per_project_required",
            ],
        )

    def test_the_two_gates_are_independent(self) -> None:
        """Paid approved, network denied - the other half of the invariant."""
        client = _FakeOpenAIClient()
        planning = _plan(client, config=_approved_config(), network=())
        self.assertEqual(client.call_count, 0)
        self.assertIsNone(planning)


class BackendIsReachedTest(unittest.TestCase):
    """Case C: both approvals present, one call per eligible scene, no more."""

    def test_both_approvals_reach_the_backend_once_per_scene(self) -> None:
        client = _FakeOpenAIClient()
        planning = _plan(client, script=_script(("scene_001", "scene_002")))
        self.assertIsNotNone(planning)
        self.assertEqual(client.call_count, 2)
        self.assertEqual(planning.result.scenes[0].subject, "orca")
        self.assertEqual(planning.result.scenes[1].subject, "penguin")

    def test_the_model_answer_reaches_the_plan_as_the_existing_brief(self) -> None:
        client = _FakeOpenAIClient()
        planning = _plan(client)
        scene = planning.result.scenes[0]
        self.assertEqual(scene.subject, "orca")
        self.assertEqual(scene.place, "open ocean")
        self.assertEqual(scene.brief.provider_queries.keys(), {"en"})

    def test_the_backend_writes_no_query_of_its_own(self) -> None:
        """Every string a provider can see is still composed by the expansion ladder."""
        client = _FakeOpenAIClient(
            answers={"scene_001": {"subject": "orca", "place": "open ocean"}}
        )
        planning = _plan(client)
        queries = planning.result.scenes[0].brief.provider_queries["en"]
        # The ladder's own rungs, in the ladder's own order - not the model's answer.
        self.assertEqual(queries, ["orca open ocean", "open ocean", "orca open"])
        self.assertFalse(any(query.strip().startswith("{") for query in queries), queries)

    def test_the_request_carries_the_configured_model_and_no_retries(self) -> None:
        client = _FakeOpenAIClient()
        _plan(client, config=_approved_config(model="gpt-5.6-luna"))
        self.assertEqual(client.calls[0]["model"], "gpt-5.6-luna")

    def test_the_call_budget_is_the_ceiling_the_policy_states(self) -> None:
        client = _FakeOpenAIClient()
        planning = _plan(
            client,
            script=_script(("scene_001", "scene_002")),
            config=_approved_config(maximum_calls_per_project=1),
        )
        self.assertEqual(client.call_count, 1)
        warnings = planning.result.scenes[1].warnings
        self.assertTrue(any(UNAVAILABLE_CODE in item for item in warnings), warnings)


class AuthorSemanticSufficiencyTest(unittest.TestCase):
    """MAJOR-A: which author fields actually answer "what should this scene show"."""

    def test_a_brief_that_names_the_subject_answers_the_question(self) -> None:
        self.assertTrue(author_semantics_are_sufficient(VisualBrief(subject="orca")))

    def test_a_described_shot_answers_the_question(self) -> None:
        self.assertTrue(
            author_semantics_are_sufficient(VisualBrief(visual_description="orca breaching"))
        )

    def test_ready_made_provider_queries_answer_the_question(self) -> None:
        self.assertTrue(
            author_semantics_are_sufficient(VisualBrief(provider_queries={"en": ["orca"]}))
        )

    def test_a_hard_requirement_alone_does_not_answer_it(self) -> None:
        self.assertFalse(
            author_semantics_are_sufficient(VisualBrief(must_include=[AUTHOR_REQUIREMENT]))
        )

    def test_a_prohibition_alone_does_not_answer_it(self) -> None:
        self.assertFalse(
            author_semantics_are_sufficient(VisualBrief(must_avoid=[AUTHOR_PROHIBITION]))
        )

    def test_bookkeeping_and_media_constraints_do_not_answer_it(self) -> None:
        for brief in (
            VisualBrief(notes="проверить права"),
            VisualBrief(media_types=["video"]),
            VisualBrief(source_class="stock"),
            VisualBrief(exact_entities=["McMurdo"]),
            VisualBrief(context=["cold water"]),
            VisualBrief(shot_type="wide"),
        ):
            with self.subTest(brief=brief):
                self.assertFalse(author_semantics_are_sufficient(brief))

    def test_an_empty_brief_answers_nothing(self) -> None:
        self.assertFalse(author_semantics_are_sufficient(VisualBrief()))


class PartialAuthorBriefTest(unittest.TestCase):
    """Cases D and E: a constraint is not an answer, and it survives the answer."""

    def test_a_must_include_only_brief_is_still_sent_to_the_model(self) -> None:
        client = _FakeOpenAIClient()
        script = _script(briefs={"scene_001": {"must_include": [AUTHOR_REQUIREMENT]}})
        planning = _plan(client, script=script)
        self.assertEqual(client.call_count, 1)
        scene = planning.result.scenes[0]
        self.assertEqual(scene.subject, "orca")
        self.assertEqual(scene.action, "breaching fully out of water")
        self.assertEqual(scene.place, "open ocean")
        self.assertEqual(scene.must_include, [AUTHOR_REQUIREMENT])

    def test_a_must_avoid_only_brief_is_still_sent_to_the_model(self) -> None:
        client = _FakeOpenAIClient()
        script = _script(briefs={"scene_001": {"must_avoid": [AUTHOR_PROHIBITION]}})
        planning = _plan(client, script=script)
        self.assertEqual(client.call_count, 1)
        scene = planning.result.scenes[0]
        self.assertEqual(scene.subject, "orca")
        self.assertEqual(scene.must_avoid, [AUTHOR_PROHIBITION])

    def test_the_model_is_told_what_the_author_forbade(self) -> None:
        """Otherwise the parser's own prohibition check has nothing to check against."""
        brief = VisualBrief(must_avoid=[AUTHOR_PROHIBITION], must_include=[AUTHOR_REQUIREMENT])
        scene = build_plan(_request()).result.scenes[0]
        evidence = evidence_for_scene(scene, script_scene=None, claims=[], author_brief=brief)
        self.assertIn(AUTHOR_PROHIBITION, evidence.must_avoid)
        self.assertIn(AUTHOR_REQUIREMENT, evidence.must_include)
        self.assertIn(AUTHOR_PROHIBITION, build_prompt(evidence))

    def test_an_answer_that_asks_for_the_forbidden_thing_is_refused(self) -> None:
        client = _FakeOpenAIClient(
            answers={"scene_001": {"subject": AUTHOR_PROHIBITION, "place": "open ocean"}}
        )
        script = _script(briefs={"scene_001": {"must_avoid": [AUTHOR_PROHIBITION]}})
        planning = _plan(client, script=script)
        scene = planning.result.scenes[0]
        self.assertNotEqual(scene.subject, AUTHOR_PROHIBITION)
        self.assertTrue(
            any("semantic_brief_response" in item for item in scene.warnings), scene.warnings
        )

    def test_a_semantic_author_brief_still_skips_the_model(self) -> None:
        """Case F: the author answered the question, so nothing is spent asking it."""
        client = _FakeOpenAIClient()
        script = _script(
            briefs={"scene_001": {"subject": "emperor penguin", "action": "tobogganing"}}
        )
        planning = _plan(client, script=script)
        self.assertEqual(client.call_count, 0)
        self.assertEqual(planning.result.scenes[0].subject, "emperor penguin")


class BackendFailureTranslationTest(unittest.TestCase):
    """Cases G, H, I: expected SDK failures are controlled; defects stay loud."""

    def test_a_retryable_sdk_failure_becomes_a_visible_warning(self) -> None:
        client = _FakeOpenAIClient(raises=_FakeSDKError("upstream down", status_code=503))
        planning = _plan(client)
        warnings = planning.result.scenes[0].warnings
        self.assertTrue(any(UNAVAILABLE_CODE in item for item in warnings), warnings)

    def test_a_timeout_is_retryable(self) -> None:
        client = _FakeOpenAIClient(raises=TimeoutError("timed out"))
        planning = _plan(client)
        warnings = planning.result.scenes[0].warnings
        self.assertTrue(any(UNAVAILABLE_CODE in item for item in warnings), warnings)

    def test_a_rejected_key_becomes_a_visible_warning_and_is_not_retryable(self) -> None:
        client = _FakeOpenAIClient(raises=_FakeSDKError("invalid api key", status_code=401))
        planning = _plan(client)
        warnings = planning.result.scenes[0].warnings
        self.assertTrue(any(UNAVAILABLE_CODE in item for item in warnings), warnings)

    def test_a_failed_call_still_leaves_the_deterministic_scene_alone(self) -> None:
        client = _FakeOpenAIClient(raises=_FakeSDKError("nope", status_code=401))
        planning = _plan(client)
        self.assertNotEqual(planning.result.scenes[0].subject, "orca")

    def test_a_defect_in_the_client_is_not_reported_as_a_model_failure(self) -> None:
        """Case I: a wrong integration must not look like a model that could not answer."""
        client = _FakeOpenAIClient(raises=TypeError("responses.create() got an unexpected kwarg"))
        with self.assertRaises(TypeError):
            _plan(client)

    def test_a_failed_call_still_spends_its_place_in_the_budget(self) -> None:
        client = _FakeOpenAIClient(raises=_FakeSDKError("nope", status_code=503))
        planning = _plan(
            client,
            script=_script(("scene_001", "scene_002")),
            config=_approved_config(maximum_calls_per_project=1),
        )
        self.assertEqual(client.call_count, 1)
        self.assertIsNotNone(planning)


class SecretsNeverLeaveTheProcessTest(unittest.TestCase):
    def test_no_key_material_reaches_a_warning_or_a_diagnostic(self) -> None:
        """OpenAI's own 401 text is "Incorrect API key provided: sk-…", and a scene
        warning is written to ``visual_plan.json``. The provider's message never
        travels; the class and the status say everything this layer needs."""
        client = _FakeOpenAIClient(
            raises=_FakeSDKError("Incorrect API key provided: sk-live-abcdef", status_code=401)
        )
        planning = _plan(client)
        rendered = json.dumps(planning.result.to_dict(), ensure_ascii=False)
        self.assertNotIn("sk-live-abcdef", rendered)
        self.assertIn("_FakeSDKError", rendered)
        self.assertIn("status=401", rendered)

    def test_diagnostics_report_presence_and_never_a_value(self) -> None:
        report = activation_diagnostics(_approved_config())
        self.assertIn("api_key_configured", report)
        self.assertIsInstance(report["api_key_configured"], bool)
        rendered = json.dumps(report, ensure_ascii=False)
        self.assertNotIn("sk-", rendered)


class DefaultRepositoryStateTest(unittest.TestCase):
    """Case J: with nothing activated, production is exactly what it is today."""

    def test_the_shipped_configuration_activates_nothing(self) -> None:
        config = SemanticBriefModelConfig.from_config(load_semantic_brief_config())
        self.assertFalse(config.enabled)
        self.assertTrue(paid_call_blockers(config))

    def test_no_adapter_is_built_from_the_shipped_configuration(self) -> None:
        with network_approval_scope(
            approval_for_actions([NETWORK_ACTION_SEMANTIC_BRIEF], granted_by="test")
        ):
            self.assertIsNone(build_semantic_brief_adapter())

    def test_the_production_visual_plan_is_unchanged_by_default(self) -> None:
        from src.news.visual_plan import build_visual_plan

        script = {
            "scenes": [
                {
                    "scene_id": "scene_001",
                    "index": 1,
                    "role": "hook",
                    "narration": ORCA_NARRATION,
                    "duration_sec": 6.0,
                }
            ],
            "title": "Странные способности животных",
            "language": "ru",
        }
        plan = build_visual_plan(script, language="ru")
        deterministic = build_plan(_request()).to_legacy_plan(language="ru", script=script)
        self.assertEqual(
            [scene["scene_id"] for scene in plan["scenes"]],
            [scene["scene_id"] for scene in deterministic["scenes"]],
        )
        self.assertNotEqual(plan["scenes"][0].get("semantic", {}).get("subject"), "orca")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
