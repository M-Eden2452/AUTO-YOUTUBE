"""C84-C86: the paid semantic-brief budget belongs to the project, not to an instance.

``maximum_calls_per_project`` says *project* in its own name, but the counter it is
compared against was created by ``OpenAISemanticBriefBackend.__init__`` and died with
that instance. Production builds a plan more than once for the same project - the
``visual_plan`` stage builds one, and a single adaptation pass builds two more - and
every build asks ``build_semantic_brief_adapter()`` for a new adapter, so every build
started from zero. Rerunning the stage (``--force-stage``, resume, restart) did the same
and additionally overwrote the persisted record with the last build's own count.

Three defects, one root: nothing carried the project's spend across a lifecycle boundary.

- **C84** - the call ceiling was per adapter instance, so N was really N per build.
- **C85** - ``maximum_budget_usd`` was only checked for being positive when the adapter
  was built (``paid_call_blockers``) and never consulted again.
- **C86** - a rerun of the planning stage refilled the quota and shrank the record.

Every test here counts requests on **the stub client**, which outlives every backend
instance, and drives real production entry points (``_dispatch_stage``,
``run_adaptation_pass``, ``build_visual_plan``). A test that counted ``self.calls`` of one
pre-built adapter cannot see any of this, which is exactly why the defect survived the
existing suite.

What is *not* claimed anywhere here: that ``maximum_budget_usd`` bounds the amount OpenAI
actually bills. The response is read through ``output_text`` alone, no token count is
read, and the real price is unavailable to this process. The USD ceiling is an
**estimated pre-call guard** computed from ``estimated_cost_per_call_usd``.

No socket is opened: the OpenAI client is a stub, the network guard stays installed, and
the paid policy is supplied to the factory as an in-memory config.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator
from unittest.mock import patch

from openai import OpenAIError

from src.assets.completion import MODE_DRAFT_COMPLETE
from src.content.semantic_brief_openai import (
    LIVE_CONFIRMATION_PHRASE,
    OpenAISemanticBriefBackend,
    SemanticBriefModelConfig,
    build_semantic_brief_adapter,
)
from src.content.visual_planning.semantic_brief import SemanticBriefUnavailableError
from src.news.draft_completion import run_adaptation_pass
from src.news.models import INPUT_MODE_TEXT, NewsJob
from src.news.pipeline import _dispatch_stage
from src.news.project_store import NewsProjectStore
from src.runtime_network import (
    NETWORK_ACTION_SEMANTIC_BRIEF,
    approval_for_actions,
    network_approval_scope,
)

LANGUAGE = "ru"

NARRATIONS = (
    "Косатки в открытом океане способны выпрыгивать из воды целиком.",
    "Пингвины ложатся на живот и скользят по снегу и льду.",
    "Морские черепахи возвращаются на тот же пляж через десятилетия.",
    "Горбатые киты поднимают со дна сеть из пузырей.",
)

ANSWER = {"subject": "orca", "action": "breaching", "place": "open ocean"}


class _StubResponses:
    def __init__(self, owner: "_ProjectClient") -> None:
        self._owner = owner

    def create(self, **payload: Any) -> Any:
        self._owner.calls.append(dict(payload))
        if self._owner.raises is not None:
            raise self._owner.raises
        return _StubResponse(ANSWER)


class _StubResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.output_text = json.dumps(payload, ensure_ascii=False)


class _ProjectClient:
    """One stub client for a whole project. It outlives every backend instance.

    This is the whole point of the fixture: the counter that matters is here, not on an
    adapter, so a second adapter built halfway through the project cannot hide behind a
    fresh ``self.calls``.
    """

    def __init__(self, *, raises: Exception | None = None) -> None:
        self.calls: list[dict[str, Any]] = []
        self.raises = raises
        self.responses = _StubResponses(self)

    @property
    def call_count(self) -> int:
        return len(self.calls)


class _StubSDKError(OpenAIError):
    def __init__(self, message: str, *, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code


def _approved_config(**overrides: Any) -> SemanticBriefModelConfig:
    options: dict[str, Any] = {
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


def _approval() -> Any:
    return approval_for_actions([NETWORK_ACTION_SEMANTIC_BRIEF], granted_by="test")


def _script(scene_count: int = 2) -> dict[str, Any]:
    scenes = [
        {
            "scene_id": f"scene_{index:03d}",
            "index": index,
            "role": "hook" if index == 1 else "development",
            "narration": NARRATIONS[index - 1],
            "target_duration_sec": 6.0,
            "duration_sec": 6.0,
        }
        for index in range(1, scene_count + 1)
    ]
    return {
        "title": "Странные способности животных",
        "language": LANGUAGE,
        "narration_text": " ".join(NARRATIONS[:scene_count]),
        "estimated_duration_sec": 6.0 * scene_count,
        "scenes": scenes,
    }


def _job(title: str) -> NewsJob:
    return NewsJob.create(
        channel_id="offline_fixture",
        input_mode=INPUT_MODE_TEXT,
        title=title,
        topic="Animal abilities",
        input_text="Offline fixture input.",
        completion_mode=MODE_DRAFT_COMPLETE,
        now="2026-08-15T10:00:00+00:00",
    )


@contextmanager
def _live_backend(client: _ProjectClient, config: SemanticBriefModelConfig) -> Iterator[None]:
    """Production wiring with one stub client behind it.

    The factory is patched, not the adapter: every planning build still asks for its own
    adapter and gets a **new** backend instance, exactly as production does. Whatever
    keyword arguments the caller passes to the factory are forwarded, so this fixture
    neither supplies nor hides the project's prior spend on the caller's behalf.
    """

    def factory(**kwargs: Any) -> Any:
        return build_semantic_brief_adapter(config=config, client=client, **kwargs)

    with (
        network_approval_scope(_approval()),
        patch(
            "src.news.visual_plan.build_semantic_brief_adapter",
            side_effect=factory,
        ),
    ):
        yield


@contextmanager
def _project(title: str, *, scene_count: int = 2) -> Iterator[tuple[Any, NewsJob, Path]]:
    """A project on disk with a script, empty research and an empty asset manifest."""
    with tempfile.TemporaryDirectory() as tmp:
        store = NewsProjectStore(Path(tmp) / "projects")
        job = _job(title)
        root = store.create_project(job).root
        store.write_json(
            root / "localizations" / LANGUAGE / "script" / "script.json",
            _script(scene_count),
        )
        store.write_json(root / "research" / "claims.json", {"claims": []})
        store.write_json(
            root / "assets" / "assets_manifest.json",
            {
                "schema_version": 1,
                "scenes": [],
                "missing_scenes": [],
                "completion": {"mode": MODE_DRAFT_COMPLETE, "reuse": {}},
            },
        )
        yield store, job, root


def _plan_path(root: Path) -> Path:
    return root / "localizations" / LANGUAGE / "visual" / "visual_plan.json"


def _persisted_usage(store: Any, root: Path) -> dict[str, Any]:
    plan = store.read_json(_plan_path(root))
    return dict((plan.get("planning_metadata") or {}).get("semantic_brief_usage") or {})


class ProjectCallCapTest(unittest.TestCase):
    """C84: N is the project's ceiling, whatever a lifecycle does to build a plan."""

    def test_a_project_never_sends_more_requests_than_its_cap(self) -> None:
        """The stage plus one adaptation pass: three plan builds, one ceiling.

        ``run_adaptation_pass`` calls ``_replan`` twice by construction - once for the
        proposal, once for what was accepted - so a two-scene project used to send six
        requests under a ceiling of three.
        """
        client = _ProjectClient()
        with _project("Project call cap") as (store, job, root):
            with _live_backend(client, _approved_config(maximum_calls_per_project=3)):
                _dispatch_stage("visual_plan", store, job, root, dry_run=True)
                result = run_adaptation_pass(
                    store=store, job=job, root=root, research_scenes=None
                )
            usage = _persisted_usage(store, root)

        self.assertEqual(result["status"], "no_change")
        self.assertLessEqual(client.call_count, 3)
        self.assertEqual(usage["calls"], client.call_count)

    def test_the_record_counts_what_was_sent_and_never_counts_it_twice(self) -> None:
        """The other direction of the same invariant: no inflation either.

        The plan is written to two places - the localized plan and the master snapshot -
        and a merge that read both would report double what the project spent.
        """
        client = _ProjectClient()
        with _project("Project spend record") as (store, job, root):
            with _live_backend(client, _approved_config(maximum_calls_per_project=8)):
                _dispatch_stage("visual_plan", store, job, root, dry_run=True)
                run_adaptation_pass(store=store, job=job, root=root, research_scenes=None)
            usage = _persisted_usage(store, root)
            master = store.read_json(root / "master" / "master_visual_plan.json")

        self.assertEqual(usage["calls"], client.call_count)
        self.assertEqual(
            usage["estimated_cost_usd"], round(client.call_count * 0.01, 6)
        )
        master_usage = (master.get("planning_metadata") or {}).get("semantic_brief_usage")
        self.assertLessEqual(int((master_usage or {}).get("calls") or 0), usage["calls"])

    def test_several_backend_instances_share_one_ceiling(self) -> None:
        """The narrowest statement of C84, without any pipeline stage involved."""
        cap = 3
        client = _ProjectClient()
        config = _approved_config(maximum_calls_per_project=cap)
        prior: dict[str, Any] = {}
        with network_approval_scope(_approval()):
            for _ in range(4):
                backend = OpenAISemanticBriefBackend(
                    config, client=client, prior_usage=prior
                )
                for index in range(2):
                    try:
                        backend(f"prompt {index}", {"scene_id": f"scene_{index:03d}"})
                    except SemanticBriefUnavailableError:
                        pass
                prior = backend.usage_summary()

        self.assertEqual(client.call_count, cap)
        self.assertEqual(prior["calls"], cap)


class CallCapBoundaryTest(unittest.TestCase):
    """C84 boundaries, stated on the backend that owns the counter."""

    def _spend(
        self,
        *,
        cap: int,
        prior_calls: int,
        attempts: int,
        client: _ProjectClient | None = None,
    ) -> tuple[_ProjectClient, list[bool]]:
        client = client or _ProjectClient()
        backend = OpenAISemanticBriefBackend(
            _approved_config(maximum_calls_per_project=cap),
            client=client,
            prior_usage={"calls": prior_calls, "estimated_cost_usd": prior_calls * 0.01},
        )
        outcomes: list[bool] = []
        with network_approval_scope(_approval()):
            for index in range(attempts):
                try:
                    backend(f"prompt {index}", {"scene_id": f"scene_{index:03d}"})
                    outcomes.append(True)
                except SemanticBriefUnavailableError:
                    outcomes.append(False)
        return client, outcomes

    def test_a_cap_of_one_allows_exactly_one_request(self) -> None:
        client, outcomes = self._spend(cap=1, prior_calls=0, attempts=3)
        self.assertEqual(client.call_count, 1)
        self.assertEqual(outcomes, [True, False, False])

    def test_the_last_request_inside_the_cap_is_still_sent(self) -> None:
        client, outcomes = self._spend(cap=4, prior_calls=1, attempts=3)
        self.assertEqual(client.call_count, 3)
        self.assertEqual(outcomes, [True, True, True])

    def test_the_first_request_beyond_the_cap_is_refused_before_it_is_sent(self) -> None:
        client, outcomes = self._spend(cap=4, prior_calls=1, attempts=4)
        self.assertEqual(client.call_count, 3)
        self.assertEqual(outcomes, [True, True, True, False])

    def test_a_project_already_at_its_cap_sends_nothing(self) -> None:
        client, outcomes = self._spend(cap=3, prior_calls=3, attempts=2)
        self.assertEqual(client.call_count, 0)
        self.assertEqual(outcomes, [False, False])

    def test_a_cap_lowered_below_what_was_already_spent_sends_nothing(self) -> None:
        """Spent 15, ceiling later lowered to 12: refuse, never a negative remainder."""
        client, outcomes = self._spend(cap=12, prior_calls=15, attempts=2)
        self.assertEqual(client.call_count, 0)
        self.assertEqual(outcomes, [False, False])

    def test_a_project_with_no_recorded_spend_gets_its_whole_cap(self) -> None:
        """An older project's plan has no ``semantic_brief_usage`` at all: that is zero."""
        client = _ProjectClient()
        backend = OpenAISemanticBriefBackend(
            _approved_config(maximum_calls_per_project=2), client=client, prior_usage={}
        )
        with network_approval_scope(_approval()):
            backend("prompt", {"scene_id": "scene_001"})
            backend("prompt", {"scene_id": "scene_002"})
        self.assertEqual(client.call_count, 2)
        self.assertEqual(backend.usage_summary()["calls"], 2)

    def test_a_failed_request_still_spends_its_place_in_the_project_budget(self) -> None:
        """Unchanged semantics: the budget is spent *before* the call, so a failure costs."""
        client = _ProjectClient(raises=_StubSDKError("upstream down", status_code=503))
        _, outcomes = self._spend(cap=1, prior_calls=0, attempts=2, client=client)
        self.assertEqual(client.call_count, 1)
        self.assertEqual(outcomes, [False, False])


class EstimatedMoneyGuardTest(unittest.TestCase):
    """C85: the configured USD ceiling refuses the next request before it is sent.

    Estimated, from ``estimated_cost_per_call_usd``. Nothing here reads a token count or
    a price, and nothing here claims the provider's invoice is bounded.
    """

    def test_the_money_ceiling_stops_a_run_the_call_cap_would_allow(self) -> None:
        client = _ProjectClient()
        config = _approved_config(
            maximum_calls_per_project=99,
            maximum_budget_usd=0.03,
            estimated_cost_per_call_usd=0.01,
        )
        with _project("Estimated money guard", scene_count=4) as (store, job, root):
            with _live_backend(client, config):
                _dispatch_stage("visual_plan", store, job, root, dry_run=True)
            usage = _persisted_usage(store, root)

        self.assertEqual(client.call_count, 3)
        self.assertEqual(usage["estimated_cost_usd"], 0.03)

    def test_the_request_that_lands_exactly_on_the_ceiling_is_sent(self) -> None:
        client = _ProjectClient()
        backend = OpenAISemanticBriefBackend(
            _approved_config(
                maximum_calls_per_project=99,
                maximum_budget_usd=0.03,
                estimated_cost_per_call_usd=0.01,
            ),
            client=client,
            prior_usage={"calls": 2, "estimated_cost_usd": 0.02},
        )
        with network_approval_scope(_approval()):
            backend("prompt", {"scene_id": "scene_003"})
            with self.assertRaises(SemanticBriefUnavailableError):
                backend("prompt", {"scene_id": "scene_004"})
        self.assertEqual(client.call_count, 1)
        self.assertEqual(backend.usage_summary()["estimated_cost_usd"], 0.03)

    def test_a_project_already_over_the_ceiling_sends_nothing(self) -> None:
        client = _ProjectClient()
        backend = OpenAISemanticBriefBackend(
            _approved_config(
                maximum_calls_per_project=99,
                maximum_budget_usd=0.03,
                estimated_cost_per_call_usd=0.01,
            ),
            client=client,
            prior_usage={"calls": 9, "estimated_cost_usd": 0.09},
        )
        with network_approval_scope(_approval()):
            with self.assertRaises(SemanticBriefUnavailableError):
                backend("prompt", {"scene_id": "scene_001"})
        self.assertEqual(client.call_count, 0)

    def test_without_a_per_call_estimate_nothing_is_sent_at_all(self) -> None:
        """C87, closed 2026-08-17 by owner decision: no estimate is now a refusal.

        This test previously froze the opposite - that a missing estimate simply
        left the call cap as the only bound, so two calls went out under a
        declared 0.03 USD ceiling that could never bind. That was the defect:
        ``_projected_cost_usd`` adds zero per call, so the money guard was
        silently off while ``activation_diagnostics`` showed a budget and no
        blockers. The owner chose the blocker over a documented caveat, so a
        declared budget without an estimate now stops before the first call
        rather than after the last one the counter allows.
        """
        client = _ProjectClient()
        backend = OpenAISemanticBriefBackend(
            _approved_config(
                maximum_calls_per_project=2,
                maximum_budget_usd=0.03,
                estimated_cost_per_call_usd=0.0,
            ),
            client=client,
        )
        with network_approval_scope(_approval()):
            with self.assertRaises(SemanticBriefUnavailableError) as ctx:
                backend("prompt", {"scene_id": "scene_001"})
        self.assertIn("estimated_cost_per_call_usd_required", str(ctx.exception))
        self.assertEqual(client.call_count, 0)
        self.assertEqual(backend.usage_summary()["estimated_cost_usd"], 0.0)


class RerunKeepsTheProjectRecordTest(unittest.TestCase):
    """C86: rerunning the planning stage refills nothing and shrinks nothing.

    ``--force-stage visual_plan``, a resume that reaches the stage again and a restarted
    process all re-enter ``_dispatch_stage``, which is what these tests run twice.
    """

    def test_a_second_planning_run_neither_refills_the_quota_nor_shrinks_the_record(
        self,
    ) -> None:
        client = _ProjectClient()
        with _project("Rerun planning stage") as (store, job, root):
            with _live_backend(client, _approved_config(maximum_calls_per_project=3)):
                _dispatch_stage("visual_plan", store, job, root, dry_run=True)
                first = _persisted_usage(store, root)
                _dispatch_stage("visual_plan", store, job, root, dry_run=True)
                second = _persisted_usage(store, root)

        self.assertEqual(first["calls"], 2)
        self.assertLessEqual(client.call_count, 3)
        self.assertGreaterEqual(second["calls"], first["calls"])
        self.assertEqual(second["calls"], client.call_count)

    def test_a_run_without_a_paid_backend_keeps_what_the_project_already_spent(
        self,
    ) -> None:
        """The critical case: no adapter is built at all, and the record must survive.

        With payment or network switched off ``build_semantic_brief_adapter`` returns
        ``None`` and the new build reports no usage of its own. That is not a reason to
        forget what the project spent yesterday.
        """
        client = _ProjectClient()
        with _project("Rerun without a backend") as (store, job, root):
            with _live_backend(client, _approved_config(maximum_calls_per_project=8)):
                _dispatch_stage("visual_plan", store, job, root, dry_run=True)
            spent = _persisted_usage(store, root)
            _dispatch_stage("visual_plan", store, job, root, dry_run=True)
            after = _persisted_usage(store, root)

        self.assertEqual(spent["calls"], 2)
        self.assertEqual(after.get("calls"), 2)
        self.assertEqual(client.call_count, 2)

    def test_an_unreadable_plan_rebuilds_the_stage_instead_of_stopping_the_run(
        self,
    ) -> None:
        """Reading the seed must not turn a corrupt artifact into a failed stage.

        A corrupt stage output is required to re-execute its stage and repair itself
        (``test_visual_plan_stage_idempotency_missing_and_corrupt_output``). The price is
        named in the registry under C86: a record that no longer states a number cannot
        bound the budget it stated, so this build starts from zero.
        """
        client = _ProjectClient()
        with _project("Unreadable plan") as (store, job, root):
            with _live_backend(client, _approved_config(maximum_calls_per_project=8)):
                _dispatch_stage("visual_plan", store, job, root, dry_run=True)
                _plan_path(root).write_text("{not valid json", encoding="utf-8")
                _dispatch_stage("visual_plan", store, job, root, dry_run=True)
            usage = _persisted_usage(store, root)

        self.assertEqual(usage["calls"], 2)
        self.assertEqual(client.call_count, 4)

    def test_an_adaptation_pass_after_a_rerun_still_shares_the_one_ceiling(self) -> None:
        """Stage, stage again, then the pass: five builds, still one project budget."""
        client = _ProjectClient()
        with _project("Rerun then adapt") as (store, job, root):
            with _live_backend(client, _approved_config(maximum_calls_per_project=4)):
                _dispatch_stage("visual_plan", store, job, root, dry_run=True)
                _dispatch_stage("visual_plan", store, job, root, dry_run=True)
                run_adaptation_pass(store=store, job=job, root=root, research_scenes=None)
            usage = _persisted_usage(store, root)

        self.assertLessEqual(client.call_count, 4)
        self.assertEqual(usage["calls"], client.call_count)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
