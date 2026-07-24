from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

from PIL import Image


class OpenAISemanticVisualBackendTests(unittest.TestCase):
    def test_openai_backend_implements_protocol_methods(self) -> None:
        from src.assets.semantic_visual_openai import OpenAISemanticVisualBackend

        backend = OpenAISemanticVisualBackend({})

        self.assertEqual(backend.name, "openai")
        self.assertTrue(callable(backend.capabilities))
        self.assertTrue(callable(backend.analyse_candidate))
        self.assertTrue(callable(backend.health_check))
        self.assertEqual(backend.capabilities().backend, "openai")

    def test_request_builder_includes_multiple_frames(self) -> None:
        from src.assets.semantic_visual_openai import OpenAIRequestBuilder, OpenAISemanticConfig

        with tempfile.TemporaryDirectory() as tmp:
            request = _request(Path(tmp), frame_count=3)
            built = OpenAIRequestBuilder(OpenAISemanticConfig.from_config(_live_config())).build(
                request,
                model="gpt-5.6-terra",
                detail="low",
            )

            content = built.payload["input"][0]["content"]
            images = [item for item in content if item.get("type") == "input_image"]

            self.assertEqual(len(images), 3)
            self.assertEqual({item["detail"] for item in images}, {"low"})
            self.assertTrue(all(str(item["image_url"]).startswith("data:image/") for item in images))

    def test_absolute_paths_are_redacted_from_text_and_diagnostics(self) -> None:
        from src.assets.semantic_visual_openai import OpenAIRequestBuilder, OpenAISemanticConfig, sanitized_payload_for_diagnostics

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            request = _request(root, frame_count=1)
            request.candidate_metadata["local_path"] = str(root / "secret" / "asset.mp4")
            built = OpenAIRequestBuilder(OpenAISemanticConfig.from_config(_live_config())).build(
                request,
                model="gpt-5.6-terra",
                detail="low",
            )

            raw_text = json.dumps(sanitized_payload_for_diagnostics(built.payload), ensure_ascii=False)
            raw_diag = json.dumps(built.diagnostics, ensure_ascii=False)

            self.assertNotIn(str(root), raw_text)
            self.assertNotIn(str(root), raw_diag)
            self.assertNotIn("G:\\", raw_text)

    def test_api_key_is_absent_from_request_and_logs(self) -> None:
        from src.assets.semantic_visual_openai import OpenAIRequestBuilder, OpenAISemanticConfig, sanitized_payload_for_diagnostics

        with tempfile.TemporaryDirectory() as tmp:
            secret = "sk-test-SECRET-VALUE"
            old = os.environ.get("OPENAI_API_KEY")
            os.environ["OPENAI_API_KEY"] = secret
            try:
                built = OpenAIRequestBuilder(OpenAISemanticConfig.from_config(_live_config())).build(
                    _request(Path(tmp)),
                    model="gpt-5.6-terra",
                    detail="low",
                )
            finally:
                if old is None:
                    os.environ.pop("OPENAI_API_KEY", None)
                else:
                    os.environ["OPENAI_API_KEY"] = old

            diagnostic_text = json.dumps(
                {"payload": sanitized_payload_for_diagnostics(built.payload), "diagnostics": built.diagnostics},
                ensure_ascii=False,
            )

            self.assertNotIn(secret, diagnostic_text)
            self.assertNotIn("OPENAI_API_KEY", diagnostic_text)
            self.assertNotIn("api_key", diagnostic_text.lower())

    def test_base64_is_not_persisted_to_cache_or_diagnostics(self) -> None:
        from src.assets.semantic_visual_cache import SemanticVisualCache
        from src.assets.semantic_visual_openai import OpenAIRequestBuilder, OpenAISemanticConfig, adapt_openai_structured_result

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            request = _request(root)
            built = OpenAIRequestBuilder(OpenAISemanticConfig.from_config(_live_config())).build(
                request,
                model="gpt-5.6-terra",
                detail="low",
            )
            result = adapt_openai_structured_result(_fake_response(_semantic_payload()), request, model="gpt-5.6-terra")
            result.cache_key = "a" * 64
            cache = SemanticVisualCache(root / "cache")
            cache.write(result)
            cache_text = (root / "cache" / ("a" * 64) / "semantic_result.json").read_text(encoding="utf-8")
            diagnostic_text = json.dumps(built.diagnostics, ensure_ascii=False)

            self.assertNotIn("data:image", cache_text)
            self.assertNotIn("base64", cache_text.lower())
            self.assertNotIn("data:image", diagnostic_text)
            self.assertNotIn("base64", diagnostic_text.lower())

    def test_structured_output_maps_to_semantic_visual_result(self) -> None:
        from src.assets.semantic_visual_models import SemanticVisualResult
        from src.assets.semantic_visual_openai import adapt_openai_structured_result

        with tempfile.TemporaryDirectory() as tmp:
            result = adapt_openai_structured_result(
                _fake_response(_semantic_payload(confidence=0.91, subject_match=0.93)),
                _request(Path(tmp)),
                model="gpt-5.6-terra",
            )

            self.assertIsInstance(result, SemanticVisualResult)
            self.assertEqual(result.status, "success")
            self.assertGreater(result.aggregate_scores.subject_match, 0.9)
            self.assertEqual(result.raw_response_reference, "req_123")

    def test_completed_structured_status_is_normalized_to_success(self) -> None:
        from src.assets.semantic_visual_openai import adapt_openai_structured_result

        with tempfile.TemporaryDirectory() as tmp:
            payload = _semantic_payload()
            payload["status"] = "completed"
            result = adapt_openai_structured_result(_fake_response(payload), _request(Path(tmp)), model="gpt-5.6-terra")

            self.assertEqual(result.status, "success")
            self.assertGreater(result.semantic_score, 0.0)

    def test_invalid_structured_result_falls_back(self) -> None:
        from src.assets.semantic_visual_openai import adapt_openai_structured_result

        with tempfile.TemporaryDirectory() as tmp:
            payload = _semantic_payload(confidence=1.2)
            result = adapt_openai_structured_result(_fake_response(payload), _request(Path(tmp)), model="gpt-5.6-terra")

            self.assertEqual(result.status, "invalid_response")
            self.assertEqual(result.error.code, "invalid_schema")

    def test_refusal_is_handled(self) -> None:
        from src.assets.semantic_visual_openai import adapt_openai_structured_result

        with tempfile.TemporaryDirectory() as tmp:
            result = adapt_openai_structured_result(_fake_response(None, refusal="cannot comply"), _request(Path(tmp)), model="gpt-5.6-terra")

            self.assertEqual(result.status, "refused")
            self.assertEqual(result.error.code, "refusal")

    def test_timeout_is_handled(self) -> None:
        from src.assets.semantic_visual_openai import OpenAISemanticVisualBackend

        with tempfile.TemporaryDirectory() as tmp:
            client = _FakeOpenAIClient([TimeoutError("slow")])
            backend = OpenAISemanticVisualBackend(_live_config(maximum_retries=0), client=client)

            result = backend.analyse_candidate(_request(Path(tmp)))

            self.assertEqual(result.status, "timeout")
            self.assertEqual(result.error.code, "timeout")
            self.assertEqual(client.responses.call_count, 1)

    def test_429_retries_then_succeeds(self) -> None:
        from src.assets.semantic_visual_openai import OpenAISemanticVisualBackend

        with tempfile.TemporaryDirectory() as tmp:
            client = _FakeOpenAIClient([_FakeHTTPError(429), _fake_response(_semantic_payload())])
            backend = OpenAISemanticVisualBackend(_live_config(maximum_retries=2), client=client, sleep=lambda _: None)

            result = backend.analyse_candidate(_request(Path(tmp)))

            self.assertEqual(result.status, "success")
            self.assertEqual(client.responses.call_count, 2)

    def test_retry_after_is_respected(self) -> None:
        from src.assets.semantic_visual_openai import OpenAISemanticVisualBackend

        sleeps: list[float] = []
        with tempfile.TemporaryDirectory() as tmp:
            client = _FakeOpenAIClient([_FakeHTTPError(429, headers={"retry-after": "1.5"}), _fake_response(_semantic_payload())])
            backend = OpenAISemanticVisualBackend(_live_config(maximum_retries=2), client=client, sleep=sleeps.append)

            backend.analyse_candidate(_request(Path(tmp)))

            self.assertEqual(sleeps, [1.5])

    def test_401_does_not_retry(self) -> None:
        self._assert_no_retry_for_status(401, "authentication_error")

    def test_403_does_not_retry(self) -> None:
        self._assert_no_retry_for_status(403, "permission_denied")

    def test_400_does_not_retry(self) -> None:
        self._assert_no_retry_for_status(400, "bad_request")

    def test_5xx_limited_retry(self) -> None:
        from src.assets.semantic_visual_openai import OpenAISemanticVisualBackend

        with tempfile.TemporaryDirectory() as tmp:
            client = _FakeOpenAIClient([_FakeHTTPError(500), _FakeHTTPError(502), _FakeHTTPError(503)])
            backend = OpenAISemanticVisualBackend(_live_config(maximum_retries=2), client=client, sleep=lambda _: None)

            result = backend.analyse_candidate(_request(Path(tmp)))

            self.assertEqual(result.status, "server_error")
            self.assertEqual(client.responses.call_count, 3)

    def test_paid_calls_blocked_by_default(self) -> None:
        from src.assets.semantic_visual_openai import OpenAISemanticVisualBackend

        with tempfile.TemporaryDirectory() as tmp:
            client = _FakeOpenAIClient([_fake_response(_semantic_payload())])
            backend = OpenAISemanticVisualBackend({}, client=client)

            result = backend.analyse_candidate(_request(Path(tmp)))

            self.assertEqual(result.status, "configuration_error")
            self.assertEqual(result.error.code, "openai_backend_disabled")
            self.assertEqual(client.responses.call_count, 0)

    def test_zero_budget_blocks(self) -> None:
        from src.assets.semantic_visual_openai import OpenAISemanticVisualBackend

        with tempfile.TemporaryDirectory() as tmp:
            config = _live_config(maximum_budget_usd=0.0)
            backend = OpenAISemanticVisualBackend(config, client=_FakeOpenAIClient([_fake_response(_semantic_payload())]))

            result = backend.analyse_candidate(_request(Path(tmp)))

            self.assertEqual(result.error.code, "budget_violation")
            self.assertIn("maximum_budget_usd_required", result.error.message)

    def test_missing_confirmation_blocks(self) -> None:
        from src.assets.semantic_visual_openai import OpenAISemanticVisualBackend

        with tempfile.TemporaryDirectory() as tmp:
            config = _live_config(confirm_paid_vision="")
            backend = OpenAISemanticVisualBackend(config, client=_FakeOpenAIClient([_fake_response(_semantic_payload())]))

            result = backend.analyse_candidate(_request(Path(tmp)))

            self.assertEqual(result.error.code, "budget_violation")
            self.assertIn("confirm_paid_vision_required", result.error.message)

    def test_call_limit_blocks(self) -> None:
        from src.assets.semantic_visual_openai import OpenAISemanticVisualBackend

        with tempfile.TemporaryDirectory() as tmp:
            config = _live_config(maximum_calls_per_project=0)
            backend = OpenAISemanticVisualBackend(config, client=_FakeOpenAIClient([_fake_response(_semantic_payload())]))

            result = backend.analyse_candidate(_request(Path(tmp)))

            self.assertEqual(result.error.code, "budget_violation")
            self.assertIn("maximum_calls_per_project_required", result.error.message)

    def test_model_allowlist_blocks_unknown_model(self) -> None:
        from src.assets.semantic_visual_openai import VisionBudgetGuard, OpenAISemanticConfig

        guard = VisionBudgetGuard(OpenAISemanticConfig.from_config(_live_config()))
        decision = guard.check(model="unknown-model", detail="low", projected_calls=1, projected_image_count=1, candidate_count=1, frame_count=1)

        self.assertFalse(decision.allowed)
        self.assertIn("model_not_allowlisted", decision.reasons)

    def test_auto_detail_is_blocked(self) -> None:
        from src.assets.semantic_visual_openai import VisionBudgetGuard, OpenAISemanticConfig

        guard = VisionBudgetGuard(OpenAISemanticConfig.from_config(_live_config(initial_detail="auto")))
        decision = guard.check(model="gpt-5.6-terra", detail="auto", projected_calls=1, projected_image_count=1, candidate_count=1, frame_count=1)

        self.assertFalse(decision.allowed)
        self.assertIn("detail_not_allowed", decision.reasons)

    def test_original_detail_is_blocked(self) -> None:
        from src.assets.semantic_visual_openai import VisionBudgetGuard, OpenAISemanticConfig

        guard = VisionBudgetGuard(OpenAISemanticConfig.from_config(_live_config(initial_detail="original")))
        decision = guard.check(model="gpt-5.6-terra", detail="original", projected_calls=1, projected_image_count=1, candidate_count=1, frame_count=1)

        self.assertFalse(decision.allowed)
        self.assertIn("detail_not_allowed", decision.reasons)

    def test_low_detail_request(self) -> None:
        from src.assets.semantic_visual_openai import OpenAIRequestBuilder, OpenAISemanticConfig

        with tempfile.TemporaryDirectory() as tmp:
            built = OpenAIRequestBuilder(OpenAISemanticConfig.from_config(_live_config(initial_detail="low"))).build(
                _request(Path(tmp), frame_count=1),
                model="gpt-5.6-terra",
                detail="low",
            )
            image = next(item for item in built.payload["input"][0]["content"] if item.get("type") == "input_image")

            self.assertEqual(image["detail"], "low")

    def test_high_detail_escalation_mocked(self) -> None:
        from src.assets.semantic_visual_openai import OpenAIDetailPolicy, OpenAISemanticConfig

        policy = OpenAIDetailPolicy(OpenAISemanticConfig.from_config(_live_config()))
        decision = policy.escalation_decision(low_confidence=0.41, top_score_gap=0.02, strict_scene=True, must_have_uncertain=True)

        self.assertTrue(decision.should_escalate)
        self.assertEqual(decision.detail, "high")

    def test_maximum_frames_enforced(self) -> None:
        from src.assets.semantic_visual_openai import OpenAIRequestBuilder, OpenAISemanticConfig

        with tempfile.TemporaryDirectory() as tmp:
            config = OpenAISemanticConfig.from_config(_live_config(maximum_frames_per_candidate=2))
            built = OpenAIRequestBuilder(config).build(_request(Path(tmp), frame_count=5), model="gpt-5.6-terra", detail="low")
            images = [item for item in built.payload["input"][0]["content"] if item.get("type") == "input_image"]

            self.assertEqual(len(images), 2)

    def test_maximum_candidates_enforced_by_budget_guard(self) -> None:
        from src.assets.semantic_visual_openai import VisionBudgetGuard, OpenAISemanticConfig

        guard = VisionBudgetGuard(OpenAISemanticConfig.from_config(_live_config(maximum_candidates_per_scene=1)))
        decision = guard.check(model="gpt-5.6-terra", detail="low", projected_calls=2, projected_image_count=2, candidate_count=2, frame_count=1)

        self.assertFalse(decision.allowed)
        self.assertIn("maximum_candidates_per_scene_exceeded", decision.reasons)

    def test_usage_metadata_parsed(self) -> None:
        from src.assets.semantic_visual_openai import OpenAISemanticVisualBackend

        with tempfile.TemporaryDirectory() as tmp:
            response = _fake_response(
                _semantic_payload(),
                usage={"input_tokens": 123, "output_tokens": 45, "input_tokens_details": {"cached_tokens": 6}},
            )
            backend = OpenAISemanticVisualBackend(_live_config(), client=_FakeOpenAIClient([response]))

            result = backend.analyse_candidate(_request(Path(tmp), frame_count=2))

            self.assertEqual(result.status, "success")
            self.assertEqual(backend.usage_records[-1].input_tokens, 123)
            self.assertEqual(backend.usage_records[-1].output_tokens, 45)
            self.assertEqual(backend.usage_records[-1].cached_tokens, 6)
            self.assertEqual(backend.usage_records[-1].image_count, 2)
            self.assertEqual(backend.usage_records[-1].request_id, "req_123")

    def test_default_client_disables_sdk_retries(self) -> None:
        from src.assets.semantic_visual_openai import OpenAISemanticVisualBackend

        captured: dict[str, Any] = {}

        class FakeOpenAI:
            def __init__(self, **kwargs: Any) -> None:
                captured.update(kwargs)

        with mock.patch("openai.OpenAI", FakeOpenAI):
            client = OpenAISemanticVisualBackend(_live_config())._default_client()

        self.assertIsInstance(client, FakeOpenAI)
        self.assertEqual(captured["max_retries"], 0)

    def test_cache_compatibility(self) -> None:
        from src.assets.semantic_visual_cache import SemanticVisualCache, compute_semantic_cache_key
        from src.assets.semantic_visual_openai import OpenAISemanticVisualBackend

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            request = _request(root)
            backend = OpenAISemanticVisualBackend(_live_config(), client=_FakeOpenAIClient([_fake_response(_semantic_payload())]))
            result = backend.analyse_candidate(request)
            result.cache_key = compute_semantic_cache_key(request, semantic_config=_live_config(), prompt_template_version="openai.semantic.v1")
            cache = SemanticVisualCache(root / "semantic_cache")

            cache.write(result)
            cached = cache.read(result.cache_key)

            self.assertIsNotNone(cached)
            self.assertEqual(cached.backend, "openai")
            self.assertEqual(cached.status, "success")

    def _assert_no_retry_for_status(self, status_code: int, expected_code: str) -> None:
        from src.assets.semantic_visual_openai import OpenAISemanticVisualBackend

        with tempfile.TemporaryDirectory() as tmp:
            client = _FakeOpenAIClient([_FakeHTTPError(status_code)])
            backend = OpenAISemanticVisualBackend(_live_config(maximum_retries=2), client=client, sleep=lambda _: None)

            result = backend.analyse_candidate(_request(Path(tmp)))

            self.assertEqual(result.error.code, expected_code)
            self.assertEqual(client.responses.call_count, 1)


def _request(root: Path, *, frame_count: int = 3, case: str = "good_match"):
    from src.assets.semantic_visual_models import SceneVisualRequirements, SemanticFrameReference, SemanticVisualRequest

    frames = []
    for index in range(frame_count):
        path = root / f"frame_{index}.jpg"
        Image.new("RGB", (24, 32), (index * 20, 40, 80)).save(path)
        frames.append(
            SemanticFrameReference(
                frame_index=index,
                sha256=f"{index:064x}"[-64:],
                perceptual_hash=f"{index:016x}"[-16:],
                relative_path=f"assets/previews/frame_{index}.jpg",
                width=24,
                height=32,
                actual_timestamp_sec=float(index),
                is_poster_frame=frame_count == 1,
                private_local_path=str(path),
            )
        )
    return SemanticVisualRequest(
        project_id="project_001",
        scene_id="scene_001",
        backend="openai",
        requirements=SceneVisualRequirements(
            scene_id="scene_001",
            scene_text="A whale swims in the ocean.",
            subject="whale",
            action="swimming",
            environment=["ocean"],
            location=["coast"],
            exact_entity="whale",
            must_have=["whale", "ocean"],
            negative_elements=["desert"],
            semantic_strictness="strict",
        ),
        candidate_id=f"asset_{case}",
        provider="fake",
        candidate_metadata={"title": "Whale swimming in ocean", "semantic_fixture": case, "media_type": "video"},
        sampled_frame_references=frames,
        technical_metrics_summary={"technical_quality_score": 80.0},
        maximum_frames=frame_count,
        backend_options={"model": "gpt-5.6-terra"},
    )


def _semantic_payload(*, confidence: float = 0.9, subject_match: float = 0.9) -> dict[str, Any]:
    return {
        "result_version": "semantic_visual_result.v1",
        "backend": "openai",
        "model": "gpt-5.6-terra",
        "backend_version": "openai.responses.semantic.v1",
        "request_version": "semantic_visual_request.v1",
        "analysed_at": "2026-07-23T10:00:00+00:00",
        "status": "success",
        "confidence": confidence,
        "frames_analysed": 3,
        "frame_observations": [
            {
                "frame_index": 0,
                "subject_observations": ["whale"],
                "action_observations": ["swimming"],
                "environment_observations": ["ocean"],
                "location_observations": ["coast"],
                "shot_type_observations": [],
                "temporal_observations": [],
                "visible_text_or_logo_risk": False,
                "unwanted_element_observations": [],
                "confidence": confidence,
                "short_evidence_summary": "visible whale in water",
            }
        ],
        "aggregate_scores": {
            "subject_match": subject_match,
            "action_match": 0.9,
            "environment_match": 0.9,
            "location_match": 0.8,
            "exact_entity_match": 0.85,
            "must_have_match": 0.92,
            "negative_element_safety": 0.98,
            "shot_type_match": 1.0,
            "mood_match": 1.0,
            "temporal_match": 0.86,
            "overall_semantic_match": 0.9,
        },
        "must_have_results": [
            {"term": "whale", "present": True, "confidence": 0.93, "evidence": "visible", "frame_indices": [0]},
            {"term": "ocean", "present": True, "confidence": 0.94, "evidence": "visible", "frame_indices": [0]},
        ],
        "negative_element_results": [
            {"term": "desert", "present": False, "confidence": 0.91, "evidence": "not visible", "frame_indices": []}
        ],
        "mismatch_reasons": [],
        "review_required_reasons": [],
        "evidence": [{"kind": "visible", "summary": "whale and water visible", "frame_indices": [0], "confidence": confidence}],
        "semantic_score": 0.9,
        "hard_reject": False,
        "cache_key": "",
        "raw_response_reference": "",
        "error": None,
    }


def _live_config(**overrides: Any) -> dict[str, Any]:
    config: dict[str, Any] = {
        "openai": {
            "enabled": True,
            "primary_model": "gpt-5.6-terra",
            "comparison_model": "gpt-5.6-luna",
            "initial_detail": "low",
            "escalation_detail": "high",
            "allow_auto_detail": False,
            "allow_original_detail": False,
            "reasoning_effort": "low",
            "timeout_sec": 60,
            "maximum_retries": 1,
            "maximum_candidates_per_scene": 3,
            "maximum_frames_per_candidate": 3,
            "maximum_calls_per_project": 10,
            "maximum_budget_usd": 10.0,
            "allow_paid_vision": True,
        },
        "backend": "openai",
        "allow_paid_vision": True,
        "maximum_calls_per_project": 10,
        "maximum_budget_usd": 10.0,
        "allow_paid_vision_cli": True,
        "budget_usd_cli": 10.0,
        "max_calls_cli": 10,
        "confirm_paid_vision": "LIVE_VISION_APPROVED",
    }
    for key, value in overrides.items():
        if key in config["openai"]:
            config["openai"][key] = value
        else:
            config[key] = value
    return config


class _FakeHTTPError(Exception):
    def __init__(self, status_code: int, headers: dict[str, str] | None = None) -> None:
        super().__init__(f"HTTP {status_code}")
        self.status_code = status_code
        self.headers = headers or {}


class _FakeResponse:
    def __init__(self, parsed: dict[str, Any] | None, *, status: str = "completed", usage: dict[str, Any] | None = None, refusal: str = "") -> None:
        self.output_parsed = parsed
        self.output_text = json.dumps(parsed) if parsed is not None else ""
        self.status = status
        self.usage = usage or {}
        self.id = "resp_123"
        self._request_id = "req_123"
        self.output = []
        if refusal:
            self.output = [{"type": "message", "content": [{"type": "refusal", "refusal": refusal}]}]


def _fake_response(parsed: dict[str, Any] | None, *, usage: dict[str, Any] | None = None, refusal: str = "") -> _FakeResponse:
    return _FakeResponse(parsed, usage=usage, refusal=refusal)


class _FakeResponsesResource:
    def __init__(self, outcomes: list[Any]) -> None:
        self.outcomes = list(outcomes)
        self.call_count = 0
        self.last_kwargs: dict[str, Any] = {}

    def create(self, **kwargs: Any) -> Any:
        self.call_count += 1
        self.last_kwargs = kwargs
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


class _FakeOpenAIClient:
    def __init__(self, outcomes: list[Any]) -> None:
        self.responses = _FakeResponsesResource(outcomes)


if __name__ == "__main__":
    unittest.main()
