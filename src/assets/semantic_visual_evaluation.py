from __future__ import annotations

import hashlib
import html
import json
import math
import os
import statistics
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from PIL import Image

from .semantic_visual_models import SceneVisualRequirements, SemanticFrameReference, SemanticVisualRequest, SemanticVisualResult
from .semantic_visual_mock import MockSemanticVisualBackend
from .semantic_visual_openai import (
    LIVE_CONFIRMATION_PHRASE,
    OPENAI_ALLOWED_DETAILS,
    OpenAIRequestBuilder,
    OpenAISemanticVisualBackend,
    OpenAISemanticConfig,
    VisionBudgetGuard,
    mocked_openai_semantic_payload,
    semantic_visual_result_json_schema,
)


DEFAULT_EVAL_CONFIG_PATH = Path("config/semantic_visual_eval.json")
DEFAULT_EVAL_FRAME_ROOT = Path(tempfile.gettempdir()) / "ai_youtube_semantic_visual_eval_frames"
CONTROLLED_LIVE_EVAL_DATASET_PATH = Path("docs/implementation/openai_live_evaluation/LIVE_EVAL_DATASET.json")
CONTROLLED_LIVE_MODEL = "gpt-5.6-terra"
CONTROLLED_LIVE_DETAIL = "low"
CONTROLLED_LIVE_SCENES = 3
CONTROLLED_LIVE_CANDIDATES = 6
CONTROLLED_LIVE_CALLS = 6
CONTROLLED_LIVE_IMAGES = 6
CONTROLLED_LIVE_MAX_FRAMES_PER_CANDIDATE = 1
CONTROLLED_LIVE_BUDGET_CAP_USD = 0.50
CONTROLLED_LIVE_MAX_CALL_CAP = 6
CONTROLLED_LIVE_RESULTS_DIR = Path("docs/implementation/openai_live_evaluation/results")
CONTROLLED_LIVE_RESULT_THRESHOLD = 0.65
CONTROLLED_LIVE_INPUT_COST_PER_1K_TOKENS_USD = 0.0025
CONTROLLED_LIVE_OUTPUT_COST_PER_1K_TOKENS_USD = 0.015


@dataclass
class EvaluationCase:
    case_id: str
    category: str
    strictness: str
    frame_count: int
    media_type: str = "video"
    expected: dict[str, Any] = field(default_factory=dict)
    scene_id: str = ""
    candidate_id: str = ""
    provider: str = "evaluation_fixture"
    requirements: dict[str, Any] = field(default_factory=dict)
    candidate_metadata: dict[str, Any] = field(default_factory=dict)
    sampled_frames: list[dict[str, Any]] = field(default_factory=list)
    technical_metrics_summary: dict[str, Any] = field(default_factory=dict)
    limited_temporal_evidence: bool = False
    dataset_path: str = ""


@dataclass
class EvaluationDataset:
    schema_version: str
    cases: list[EvaluationCase]
    models: list[str] = field(default_factory=list)
    scene_count: int = 0
    candidate_count: int = 0
    dataset_path: str = ""
    constraints: dict[str, Any] = field(default_factory=dict)
    explicit_dataset: bool = False


def load_semantic_visual_eval_config(path: str | Path = DEFAULT_EVAL_CONFIG_PATH, *, require_exists: bool = False) -> EvaluationDataset:
    target = Path(path)
    if target.exists():
        data = json.loads(target.read_text(encoding="utf-8"))
    elif require_exists:
        raise FileNotFoundError(f"semantic evaluation dataset not found: {target}")
    else:
        data = _default_eval_config()
    if isinstance(data.get("scenes"), list):
        return _load_prepared_live_eval_dataset(data, target=target, explicit_dataset=require_exists)
    cases = [
        EvaluationCase(
            case_id=str(item.get("case_id") or ""),
            category=str(item.get("category") or ""),
            strictness=str(item.get("strictness") or "balanced"),
            frame_count=max(1, int(item.get("frame_count") or 3)),
            media_type=str(item.get("media_type") or "video"),
            expected=dict(item.get("expected") or {}),
            dataset_path=str(target) if target.exists() else "",
        )
        for item in data.get("cases") or []
    ]
    return EvaluationDataset(
        schema_version=str(data.get("schema_version") or "semantic_visual_eval.v1"),
        models=[str(item) for item in data.get("models") or ["mock", "gpt-5.6-terra", "gpt-5.6-luna"]],
        cases=cases,
        scene_count=len(cases),
        candidate_count=len(cases),
        dataset_path=str(target) if target.exists() else "",
        explicit_dataset=require_exists,
    )


def build_evaluation_requests(
    dataset: EvaluationDataset,
    *,
    backend: str,
    model: str,
    frame_root: str | Path = DEFAULT_EVAL_FRAME_ROOT,
) -> list[SemanticVisualRequest]:
    root = Path(frame_root)
    requests: list[SemanticVisualRequest] = []
    for case in dataset.cases:
        frames = _prepared_frames_for_case(case) if case.sampled_frames else _frames_for_case(case, root)
        requirements = (
            SceneVisualRequirements.from_dict(case.requirements)
            if case.requirements
            else SceneVisualRequirements(
                scene_id=case.case_id,
                scene_text=f"Evaluation case {case.case_id}: whale swimming in ocean.",
                subject="whale",
                action="swimming",
                environment=["ocean"],
                location=["coast"],
                exact_entity="whale",
                must_have=["whale", "ocean"],
                negative_elements=["desert"],
                semantic_strictness=case.strictness,
            )
        )
        candidate_metadata = {
            "asset_id": f"candidate_{case.case_id}",
            "provider": "evaluation_fixture",
            "media_type": case.media_type,
            "title": "Whale swimming in ocean",
            "semantic_fixture": _mock_fixture_for_case(case.category),
            "evaluation_category": case.category,
        }
        candidate_metadata.update(case.candidate_metadata)
        candidate_metadata["media_type"] = case.media_type
        if case.limited_temporal_evidence:
            candidate_metadata["limited_temporal_evidence"] = True
        requests.append(
            SemanticVisualRequest(
                project_id="openai_live_eval_prepared" if case.sampled_frames else "semantic_eval",
                scene_id=case.scene_id or case.case_id,
                backend=backend,
                requirements=requirements,
                candidate_id=case.candidate_id or f"candidate_{case.case_id}",
                provider=case.provider,
                candidate_metadata=candidate_metadata,
                sampled_frame_references=frames,
                technical_metrics_summary=case.technical_metrics_summary or {"technical_quality_score": 80.0, "source": "evaluation_fixture"},
                maximum_frames=case.frame_count,
                backend_options={"model": model},
            )
        )
    return requests


def mocked_results_for_dataset(dataset: EvaluationDataset, *, backend: str, model: str) -> dict[str, SemanticVisualResult]:
    results: dict[str, SemanticVisualResult] = {}
    if backend == "mock":
        requests = build_evaluation_requests(dataset, backend="mock", model="mock-semantic-v1")
        mock_backend = MockSemanticVisualBackend()
        for request in requests:
            results[request.scene_id] = mock_backend.analyse_candidate(request)
        return results
    for case in dataset.cases:
        payload = mocked_openai_semantic_payload(
            model=model,
            case_id=case.case_id,
            category=case.category,
            strictness=case.strictness,
            frame_count=case.frame_count,
        )
        result = SemanticVisualResult.from_dict(payload)
        result.assert_valid()
        results[case.case_id] = result
    return results


def compute_evaluation_metrics(dataset: EvaluationDataset, results: dict[str, SemanticVisualResult]) -> dict[str, float]:
    subject_pairs: list[tuple[bool, bool]] = []
    action_pairs: list[tuple[bool, bool]] = []
    environment_pairs: list[tuple[bool, bool]] = []
    exact_pairs: list[tuple[bool, bool]] = []
    must_expected = must_actual = must_true_positive = 0
    negative_expected = negative_actual = negative_true_positive = 0
    hard_false_positive = hard_negative_count = review_required = valid = 0
    scores: list[float] = []
    latencies: list[float] = []
    estimated_cost = 0.0
    for case in dataset.cases:
        result = results.get(case.case_id)
        if not result:
            continue
        expected = case.expected
        subject_expected = _expected_bool(expected.get("subject", "match"))
        action_expected = _expected_bool(expected.get("action", "match"))
        environment_expected = _expected_bool(expected.get("environment", "match"))
        exact_expected = _expected_bool(expected.get("exact_entity", "match"))
        if subject_expected is not None:
            subject_pairs.append((subject_expected, result.aggregate_scores.subject_match >= 0.65))
        if action_expected is not None:
            action_pairs.append((action_expected, result.aggregate_scores.action_match >= 0.65))
        if environment_expected is not None:
            environment_pairs.append((environment_expected, result.aggregate_scores.environment_match >= 0.65))
        if exact_expected is not None:
            exact_pairs.append((exact_expected, result.aggregate_scores.exact_entity_match >= 0.65))
        expected_must_present = bool(expected.get("must_have_present", True))
        actual_must_present = all(item.present for item in result.must_have_results) if result.must_have_results else True
        must_expected += int(expected_must_present)
        must_actual += int(actual_must_present)
        must_true_positive += int(expected_must_present and actual_must_present)
        expected_negative_present = bool(expected.get("negative_present", False))
        actual_negative_present = any(item.present for item in result.negative_element_results)
        negative_expected += int(expected_negative_present)
        negative_actual += int(actual_negative_present)
        negative_true_positive += int(expected_negative_present and actual_negative_present)
        if not expected_negative_present:
            hard_negative_count += 1
            hard_false_positive += int(result.hard_reject)
        review_required += int(bool(result.review_required_reasons) or result.status != "success")
        valid += int(not result.validation_errors())
        scores.append(float(result.semantic_score))
        latencies.append(float(getattr(result, "latency_sec", 0.0) or 0.0))
    total = max(1, len(dataset.cases))
    return {
        "subject_classification_accuracy": _accuracy(subject_pairs),
        "action_classification_accuracy": _accuracy(action_pairs),
        "environment_accuracy": _accuracy(environment_pairs),
        "exact_entity_accuracy": _accuracy(exact_pairs),
        "subject_evaluation_count": float(len(subject_pairs)),
        "action_evaluation_count": float(len(action_pairs)),
        "environment_evaluation_count": float(len(environment_pairs)),
        "exact_entity_evaluation_count": float(len(exact_pairs)),
        "must_have_precision": _safe_div(must_true_positive, must_actual),
        "must_have_recall": _safe_div(must_true_positive, must_expected),
        "negative_detection_precision": _safe_div(negative_true_positive, negative_actual),
        "negative_detection_recall": _safe_div(negative_true_positive, negative_expected),
        "hard_reject_false_positive_rate": _safe_div(hard_false_positive, hard_negative_count),
        "review_required_rate": _safe_div(review_required, total),
        "structured_output_validity": _safe_div(valid, total),
        "cache_hit_rate": 0.0,
        "latency": statistics.mean(latencies) if latencies else 0.0,
        "estimated_cost": estimated_cost,
        "score_stability": _score_stability(scores),
    }


def run_semantic_visual_evaluation(
    *,
    backend: str,
    model: str,
    dry_run: bool = False,
    mocked: bool = False,
    config: dict[str, Any] | None = None,
    dataset_path: str | Path | None = None,
    client: Any | None = None,
    results_dir: str | Path | None = None,
) -> dict[str, Any]:
    try:
        dataset = load_semantic_visual_eval_config(dataset_path or DEFAULT_EVAL_CONFIG_PATH, require_exists=bool(dataset_path))
    except FileNotFoundError as exc:
        return {
            "status": "blocked",
            "backend": backend,
            "model": model,
            "dry_run": bool(dry_run),
            "mocked": bool(mocked),
            "dataset_path": str(dataset_path or ""),
            "scenes": 0,
            "candidates": 0,
            "dataset_cases": 0,
            "projected_calls": 0,
            "projected_image_count": 0,
            "valid_requests": 0,
            "invalid_requests": 0,
            "runtime_authorized": False,
            "runtime_block_reasons": ["dataset_not_found"],
            "budget_allowed": False,
            "live_blocked_reasons": ["dataset_not_found"],
            "error": str(exc),
            "paid_calls_performed": False,
            "live_vision_calls_performed": False,
        }
    requests = build_evaluation_requests(dataset, backend=backend, model=model)
    image_count = sum(len(request.sampled_frame_references) for request in requests)
    detail = CONTROLLED_LIVE_DETAIL
    max_frame_count = max((len(request.sampled_frame_references) for request in requests), default=0)
    base_semantic_config = _load_semantic_config()
    cli_config = dict(config or {})
    runtime_reasons = _controlled_runtime_authorization_reasons(
        dataset=dataset,
        cli_config=cli_config,
        base_config=base_semantic_config,
        model=model,
        detail=detail,
        projected_calls=len(requests),
        projected_image_count=image_count,
        max_frame_count=max_frame_count,
    )
    runtime_authorized = not runtime_reasons
    semantic_config = _effective_semantic_config(base_semantic_config, cli_config, runtime_authorized=runtime_authorized)
    cfg = OpenAISemanticConfig.from_config(semantic_config)
    limit_reasons = _dataset_limit_reasons(dataset, cfg=cfg, projected_calls=len(requests), projected_image_count=image_count)
    if dry_run:
        builder = OpenAIRequestBuilder(cfg)
        schema = semantic_visual_result_json_schema()
        built_count = invalid_count = 0
        for request in requests:
            try:
                builder.build(request, model=model, detail=detail)
                built_count += 1
            except (FileNotFoundError, ValueError):
                invalid_count += 1
        reasons = []
        if not cfg.enabled:
            reasons.append("openai_backend_disabled")
        budget = VisionBudgetGuard(cfg).check(
            model=model,
            detail=detail,
            projected_calls=len(requests),
            projected_image_count=image_count,
            candidate_count=_budget_candidate_count(dataset, len(requests), cfg),
            frame_count=max_frame_count,
        )
        reasons.extend(limit_reasons)
        reasons.extend(runtime_reasons)
        reasons.extend(budget.reasons)
        reasons = _unique_reasons(reasons)
        return {
            "status": "dry_run",
            "backend": backend,
            "model": model,
            "dry_run": True,
            "mocked": False,
            "dataset_path": dataset.dataset_path,
            "scenes": dataset.scene_count,
            "candidates": dataset.candidate_count,
            "dataset_cases": len(dataset.cases),
            "requests_built": built_count,
            "valid_requests": built_count,
            "invalid_requests": invalid_count,
            "projected_calls": len(requests),
            "projected_image_count": image_count,
            "schema_valid": bool(schema.get("additionalProperties") is False),
            "runtime_authorized": runtime_authorized,
            "runtime_block_reasons": _unique_reasons(runtime_reasons),
            "budget_allowed": bool(runtime_authorized) and budget.allowed and not reasons,
            "live_blocked_reasons": reasons,
            "semantic_rerank_enabled": bool(base_semantic_config.get("semantic_rerank_enabled", False)),
            "production_selection_changed": bool(dataset.constraints.get("production_selection_changed", False)),
            "paid_calls_performed": False,
            "live_vision_calls_performed": False,
        }
    if dataset.explicit_dataset and (limit_reasons or runtime_reasons) and not mocked and backend != "mock":
        reasons = _unique_reasons([*limit_reasons, *runtime_reasons])
        return {
            "status": "blocked",
            "backend": backend,
            "model": model,
            "dry_run": False,
            "mocked": False,
            "dataset_path": dataset.dataset_path,
            "scenes": dataset.scene_count,
            "candidates": dataset.candidate_count,
            "dataset_cases": len(dataset.cases),
            "projected_calls": len(requests),
            "projected_image_count": image_count,
            "valid_requests": 0,
            "invalid_requests": 0,
            "runtime_authorized": runtime_authorized,
            "runtime_block_reasons": _unique_reasons(runtime_reasons),
            "budget_allowed": False,
            "live_blocked_reasons": reasons,
            "paid_calls_performed": False,
            "live_vision_calls_performed": False,
        }
    if mocked or backend == "mock":
        started = time.perf_counter()
        results = mocked_results_for_dataset(dataset, backend=backend, model=model)
        metrics = compute_evaluation_metrics(dataset, results)
        metrics["latency"] = round(time.perf_counter() - started, 6)
        return {
            "status": "completed",
            "backend": backend,
            "model": model,
            "dry_run": False,
            "mocked": bool(mocked),
            "dataset_path": dataset.dataset_path,
            "scenes": dataset.scene_count,
            "candidates": dataset.candidate_count,
            "dataset_cases": len(dataset.cases),
            "projected_calls": len(requests),
            "projected_image_count": image_count,
            "runtime_authorized": runtime_authorized,
            "budget_allowed": False,
            "metrics": metrics,
            "paid_calls_performed": False,
            "live_vision_calls_performed": False,
        }
    if backend != "openai":
        return {
            "status": "blocked",
            "backend": backend,
            "model": model,
            "dry_run": False,
            "mocked": False,
            "dataset_path": dataset.dataset_path,
            "scenes": dataset.scene_count,
            "candidates": dataset.candidate_count,
            "dataset_cases": len(dataset.cases),
            "projected_calls": len(requests),
            "projected_image_count": image_count,
            "valid_requests": 0,
            "invalid_requests": 0,
            "runtime_authorized": runtime_authorized,
            "runtime_block_reasons": _unique_reasons(runtime_reasons),
            "budget_allowed": False,
            "live_blocked_reasons": ["live_evaluation_backend_not_supported"],
            "paid_calls_performed": False,
            "live_vision_calls_performed": False,
        }
    return _run_controlled_openai_live_evaluation(
        dataset=dataset,
        requests=requests,
        semantic_config=semantic_config,
        model=model,
        detail=detail,
        runtime_authorized=runtime_authorized,
        runtime_reasons=runtime_reasons,
        projected_image_count=image_count,
        client=client,
        results_dir=Path(results_dir) if results_dir is not None else CONTROLLED_LIVE_RESULTS_DIR,
    )


class _ExternalAttemptLimitExceeded(Exception):
    pass


class _ExternalAttemptBudget:
    def __init__(self, *, max_attempts: int, max_images: int) -> None:
        self.max_attempts = max(0, int(max_attempts))
        self.max_images = max(0, int(max_images))
        self.attempts = 0
        self.images_sent = 0

    @property
    def remaining_attempts(self) -> int:
        return max(0, self.max_attempts - self.attempts)

    def reserve(self, *, image_count: int) -> None:
        if self.attempts + 1 > self.max_attempts:
            raise _ExternalAttemptLimitExceeded("external_attempt_limit_reached")
        if self.images_sent + image_count > self.max_images:
            raise _ExternalAttemptLimitExceeded("external_image_limit_reached")
        self.attempts += 1
        self.images_sent += image_count


class _AttemptLimitedResponsesResource:
    def __init__(self, inner: Any, budget: _ExternalAttemptBudget) -> None:
        self._inner = inner
        self._budget = budget

    def create(self, **kwargs: Any) -> Any:
        self._budget.reserve(image_count=_openai_payload_image_count(kwargs))
        return self._inner.create(**kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


class _AttemptLimitedOpenAIClient:
    def __init__(self, inner: Any, budget: _ExternalAttemptBudget) -> None:
        self._inner = inner
        self.responses = _AttemptLimitedResponsesResource(inner.responses, budget)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


def _run_controlled_openai_live_evaluation(
    *,
    dataset: EvaluationDataset,
    requests: list[SemanticVisualRequest],
    semantic_config: dict[str, Any],
    model: str,
    detail: str,
    runtime_authorized: bool,
    runtime_reasons: list[str],
    projected_image_count: int,
    client: Any | None,
    results_dir: Path,
) -> dict[str, Any]:
    cfg = OpenAISemanticConfig.from_config(semantic_config)
    if not runtime_authorized:
        return {
            "status": "blocked",
            "backend": "openai",
            "model": model,
            "dry_run": False,
            "mocked": False,
            "dataset_path": dataset.dataset_path,
            "scenes": dataset.scene_count,
            "candidates": dataset.candidate_count,
            "dataset_cases": len(dataset.cases),
            "projected_calls": len(requests),
            "projected_image_count": projected_image_count,
            "valid_requests": 0,
            "invalid_requests": 0,
            "runtime_authorized": False,
            "runtime_block_reasons": _unique_reasons(runtime_reasons),
            "budget_allowed": False,
            "live_blocked_reasons": _unique_reasons(runtime_reasons),
            "paid_calls_performed": False,
            "live_vision_calls_performed": False,
        }

    existing_checkpoint = results_dir / "LIVE_EVAL_EXECUTION_CHECKPOINT.json"
    if existing_checkpoint.exists():
        try:
            existing = json.loads(existing_checkpoint.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = {}
        if existing.get("paid_calls_performed") and int(existing.get("calls_succeeded") or 0) > 0:
            return {
                "status": "blocked",
                "backend": "openai",
                "model": model,
                "dry_run": False,
                "mocked": False,
                "dataset_path": dataset.dataset_path,
                "scenes": dataset.scene_count,
                "candidates": dataset.candidate_count,
                "dataset_cases": len(dataset.cases),
                "projected_calls": len(requests),
                "projected_image_count": projected_image_count,
                "runtime_authorized": True,
                "budget_allowed": False,
                "live_blocked_reasons": ["existing_paid_execution_checkpoint"],
                "paid_calls_performed": False,
                "live_vision_calls_performed": False,
            }

    results_dir.mkdir(parents=True, exist_ok=True)
    attempt_budget = _ExternalAttemptBudget(max_attempts=cfg.max_calls_cli, max_images=CONTROLLED_LIVE_IMAGES)
    backend = OpenAISemanticVisualBackend(semantic_config)
    if client is None:
        try:
            client = backend._default_client()
        except Exception as exc:
            return {
                "status": "blocked",
                "backend": "openai",
                "model": model,
                "dry_run": False,
                "mocked": False,
                "dataset_path": dataset.dataset_path,
                "scenes": dataset.scene_count,
                "candidates": dataset.candidate_count,
                "dataset_cases": len(dataset.cases),
                "projected_calls": len(requests),
                "projected_image_count": projected_image_count,
                "runtime_authorized": True,
                "budget_allowed": False,
                "live_blocked_reasons": ["openai_client_unavailable"],
                "error": str(exc),
                "paid_calls_performed": False,
                "live_vision_calls_performed": False,
            }
    backend.client = _AttemptLimitedOpenAIClient(client, attempt_budget)
    original_maximum_retries = backend.config.maximum_retries
    candidate_results: list[dict[str, Any]] = []
    usage_rows: list[dict[str, Any]] = []
    stop_reasons: list[str] = []
    logical_attempts = succeeded = failed = 0

    _write_live_execution_checkpoint(
        results_dir,
        phase="running",
        live_calls_performed=False,
        paid_calls_performed=False,
        calls_attempted=0,
        calls_succeeded=0,
        calls_failed=0,
        images_sent=0,
        total_cost_usd=0.0,
        budget_exceeded=False,
        ready_for_result_review=False,
        stop_reasons=[],
    )

    for case, request in zip(dataset.cases, requests, strict=True):
        if attempt_budget.remaining_attempts <= 0:
            stop_reasons.append("external_attempt_limit_reached")
            break
        backend.config.maximum_retries = max(0, min(original_maximum_retries, attempt_budget.remaining_attempts - 1))
        before_usage = len(backend.usage_records)
        started = time.perf_counter()
        result = backend.analyse_candidate(request)
        duration = max(0.0, time.perf_counter() - started)
        logical_attempts += 1
        if result.status == "success":
            succeeded += 1
        else:
            failed += 1
        usage_record = backend.usage_records[-1] if len(backend.usage_records) > before_usage else None
        candidate_row = _candidate_live_result_row(case, request, result, usage_record=usage_record, duration=duration, model=model, detail=detail)
        candidate_results.append(candidate_row)
        if usage_record is not None:
            usage_rows.append({**usage_record.to_dict(), "scene_id": request.scene_id, "candidate_id": request.candidate_id, "status": result.status})
        if result.error and result.error.code in {"authentication_error", "permission_denied"}:
            stop_reasons.append(result.error.code)
            _write_live_execution_checkpoint(
                results_dir,
                phase="running",
                live_calls_performed=attempt_budget.attempts > 0,
                paid_calls_performed=attempt_budget.attempts > 0,
                calls_attempted=logical_attempts,
                calls_succeeded=succeeded,
                calls_failed=failed,
                images_sent=attempt_budget.images_sent,
                total_cost_usd=round(sum(float(row.get("calculated_cost_usd") or 0.0) for row in candidate_results), 6),
                budget_exceeded=False,
                ready_for_result_review=False,
                stop_reasons=stop_reasons,
            )
            break
        _write_live_execution_checkpoint(
            results_dir,
            phase="running",
            live_calls_performed=attempt_budget.attempts > 0,
            paid_calls_performed=attempt_budget.attempts > 0,
            calls_attempted=logical_attempts,
            calls_succeeded=succeeded,
            calls_failed=failed,
            images_sent=attempt_budget.images_sent,
            total_cost_usd=round(sum(float(row.get("calculated_cost_usd") or 0.0) for row in candidate_results), 6),
            budget_exceeded=False,
            ready_for_result_review=False,
            stop_reasons=stop_reasons,
        )

    if attempt_budget.remaining_attempts <= 0 and logical_attempts < len(requests):
        stop_reasons.append("external_attempt_limit_reached")
    stop_reasons = _unique_reasons(stop_reasons)
    metrics = _compute_live_metrics(dataset, candidate_results)
    total_cost = round(sum(float(row.get("calculated_cost_usd") or 0.0) for row in candidate_results), 6)
    summary = {
        "status": "completed" if logical_attempts == len(requests) else "partial",
        "backend": "openai",
        "model": model,
        "detail": detail,
        "mode": "analyse_and_report",
        "dataset_path": dataset.dataset_path,
        "scenes": dataset.scene_count,
        "candidates": dataset.candidate_count,
        "dataset_cases": len(dataset.cases),
        "projected_calls": len(requests),
        "projected_image_count": projected_image_count,
        "calls_attempted": logical_attempts,
        "calls_succeeded": succeeded,
        "calls_failed": failed,
        "external_http_attempts": attempt_budget.attempts,
        "images_sent": attempt_budget.images_sent,
        "retries_observed": max(0, attempt_budget.attempts - logical_attempts),
        "total_input_tokens": sum(int(row.get("input_tokens") or 0) for row in candidate_results),
        "total_output_tokens": sum(int(row.get("output_tokens") or 0) for row in candidate_results),
        "total_cached_tokens": sum(int(row.get("cached_tokens") or 0) for row in candidate_results),
        "total_calculated_cost_usd": total_cost,
        "budget_exceeded": total_cost > CONTROLLED_LIVE_BUDGET_CAP_USD,
        "semantic_rerank_enabled": False,
        "production_selection_changed": False,
        "stop_reasons": stop_reasons,
        "runtime_authorized": True,
        "budget_allowed": total_cost <= CONTROLLED_LIVE_BUDGET_CAP_USD,
        "live_vision_calls_performed": attempt_budget.attempts > 0,
        "paid_calls_performed": attempt_budget.attempts > 0,
    }
    artifact_paths = _write_controlled_live_eval_artifacts(
        results_dir=results_dir,
        dataset=dataset,
        summary=summary,
        metrics=metrics,
        candidate_results=candidate_results,
        usage_rows=usage_rows,
    )
    ready_for_result_review = all(Path(path).exists() for path in artifact_paths.values() if path)
    _write_live_execution_checkpoint(
        results_dir,
        phase="completed",
        live_calls_performed=attempt_budget.attempts > 0,
        paid_calls_performed=attempt_budget.attempts > 0,
        calls_attempted=logical_attempts,
        calls_succeeded=succeeded,
        calls_failed=failed,
        images_sent=attempt_budget.images_sent,
        total_cost_usd=total_cost,
        budget_exceeded=total_cost > CONTROLLED_LIVE_BUDGET_CAP_USD,
        ready_for_result_review=ready_for_result_review,
        stop_reasons=stop_reasons,
    )
    return {
        **summary,
        "dry_run": False,
        "mocked": False,
        "valid_requests": len(requests),
        "invalid_requests": 0,
        "runtime_block_reasons": [],
        "live_blocked_reasons": [],
        "metrics": metrics,
        "candidate_results": candidate_results,
        "usage_records": usage_rows,
        "results_dir": _public_path(results_dir),
        "results_path": artifact_paths["results"],
        "usage_path": artifact_paths["usage"],
        "report_path": artifact_paths["report"],
        "comparison_path": artifact_paths["comparison"],
        "checkpoint_path": artifact_paths["checkpoint"],
    }


def _candidate_live_result_row(
    case: EvaluationCase,
    request: SemanticVisualRequest,
    result: SemanticVisualResult,
    *,
    usage_record: Any | None,
    duration: float,
    model: str,
    detail: str,
) -> dict[str, Any]:
    expected_classification = str(case.category or "")
    returned_classification = _returned_classification(result)
    usage = usage_record.to_dict() if usage_record is not None else {}
    aggregate = result.aggregate_scores
    expected = dict(case.expected or {})
    expected_must = _expected_terms_from_case(case, "expected_must_have")
    expected_negative = _expected_terms_from_case(case, "expected_negative_elements")
    return {
        "scene_id": request.scene_id,
        "candidate_id": request.candidate_id,
        "expected_classification": expected_classification,
        "returned_classification": returned_classification,
        "semantic_score": round(float(result.semantic_score), 6),
        "confidence": round(float(result.confidence), 6),
        "subject_match": aggregate.subject_match >= CONTROLLED_LIVE_RESULT_THRESHOLD,
        "action_match": None if expected.get("action") is None else aggregate.action_match >= CONTROLLED_LIVE_RESULT_THRESHOLD,
        "environment_match": aggregate.environment_match >= CONTROLLED_LIVE_RESULT_THRESHOLD,
        "exact_entity_match": None if expected.get("exact_entity") is None else aggregate.exact_entity_match >= CONTROLLED_LIVE_RESULT_THRESHOLD,
        "must_have_results": [item.to_dict() for item in result.must_have_results],
        "negative_element_results": [item.to_dict() for item in result.negative_element_results],
        "expected_must_have": expected_must,
        "expected_negative_elements": expected_negative,
        "must_have_match": _term_presence_matches(expected_must, result.must_have_results),
        "negative_element_match": _term_presence_matches(expected_negative, result.negative_element_results),
        "mismatch_reasons": list(result.mismatch_reasons),
        "hard_reject": bool(result.hard_reject),
        "review_required": bool(result.review_required_reasons),
        "review_required_reasons": list(result.review_required_reasons),
        "short_evidence": _short_evidence(result),
        "request_id": str(usage.get("request_id") or result.raw_response_reference or ""),
        "model": model,
        "detail": detail,
        "input_tokens": int(usage.get("input_tokens") or 0),
        "output_tokens": int(usage.get("output_tokens") or 0),
        "cached_tokens": int(usage.get("cached_tokens") or 0),
        "calculated_cost_usd": round(float(usage.get("actual_calculated_cost_usd") or 0.0), 6),
        "duration_sec": round(float(usage.get("duration_sec") or duration), 6),
        "status": result.status,
        "error": result.error.to_dict() if result.error else None,
        "structured_response_valid": not result.validation_errors(),
    }


def _returned_classification(result: SemanticVisualResult) -> str:
    if result.status != "success":
        return "error"
    if result.hard_reject or result.semantic_score < CONTROLLED_LIVE_RESULT_THRESHOLD:
        return "unsuitable"
    if result.review_required_reasons:
        return "review"
    return "suitable"


def _short_evidence(result: SemanticVisualResult) -> str:
    for item in result.evidence:
        if item.summary:
            return item.summary[:500]
    for observation in result.frame_observations:
        if observation.short_evidence_summary:
            return observation.short_evidence_summary[:500]
    if result.error and result.error.message:
        return result.error.message[:500]
    return ""


def _expected_terms_from_case(case: EvaluationCase, key: str) -> list[dict[str, Any]]:
    for scene in _load_live_dataset_scenes(case.dataset_path):
        if str(scene.get("scene_id") or "") != case.scene_id:
            continue
        for candidate in scene.get("candidates") or []:
            if str(candidate.get("candidate_id") or "") != case.candidate_id:
                continue
            items = (candidate.get("ground_truth") or {}).get(key) or []
            return [{"term": str(item.get("term") or ""), "present": bool(item.get("present"))} for item in items if isinstance(item, dict)]
    return []


def _load_live_dataset_scenes(dataset_path: str) -> list[dict[str, Any]]:
    if not dataset_path:
        return []
    try:
        data = json.loads(Path(dataset_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    scenes = data.get("scenes") if isinstance(data.get("scenes"), list) else []
    return [dict(scene) for scene in scenes if isinstance(scene, dict)]


def _term_presence_matches(expected_terms: list[dict[str, Any]], actual_terms: list[Any]) -> bool:
    actual = {str(item.term).strip().lower(): bool(item.present) for item in actual_terms if str(item.term).strip()}
    for expected in expected_terms:
        term = str(expected.get("term") or "").strip().lower()
        if not term:
            continue
        if actual.get(term) != bool(expected.get("present")):
            return False
    return True


def _compute_live_metrics(dataset: EvaluationDataset, candidate_results: list[dict[str, Any]]) -> dict[str, Any]:
    rows_by_candidate = {str(row.get("candidate_id") or ""): row for row in candidate_results}
    classification_pairs: list[tuple[str, str]] = []
    suitable_pairs: list[tuple[str, str]] = []
    unsuitable_pairs: list[tuple[str, str]] = []
    subject_pairs: list[tuple[bool, bool]] = []
    action_pairs: list[tuple[bool, bool]] = []
    environment_pairs: list[tuple[bool, bool]] = []
    exact_pairs: list[tuple[bool, bool]] = []
    must_pairs: list[tuple[bool, bool]] = []
    negative_pairs: list[tuple[bool, bool]] = []
    false_hard_reject_count = 0
    false_suitable_count = 0
    review_case_result = ""
    for case in dataset.cases:
        row = rows_by_candidate.get(case.candidate_id)
        if not row:
            continue
        expected_classification = str(row.get("expected_classification") or "")
        returned_classification = str(row.get("returned_classification") or "")
        classification_pairs.append((expected_classification, returned_classification))
        if expected_classification == "suitable":
            suitable_pairs.append((expected_classification, returned_classification))
        if expected_classification == "unsuitable":
            unsuitable_pairs.append((expected_classification, returned_classification))
        if expected_classification == "review":
            review_case_result = returned_classification
        expected = dict(case.expected or {})
        _append_bool_pair(subject_pairs, expected.get("subject"), row.get("subject_match"))
        _append_bool_pair(action_pairs, expected.get("action"), row.get("action_match"))
        _append_bool_pair(environment_pairs, expected.get("environment"), row.get("environment_match"))
        _append_bool_pair(exact_pairs, expected.get("exact_entity"), row.get("exact_entity_match"))
        must_pairs.append((True, bool(row.get("must_have_match"))))
        negative_pairs.append((True, bool(row.get("negative_element_match"))))
        if bool(row.get("hard_reject")) and expected_classification != "unsuitable":
            false_hard_reject_count += 1
        if returned_classification == "suitable" and expected_classification == "unsuitable":
            false_suitable_count += 1
    total = max(1, len(candidate_results))
    return {
        "classification_accuracy": _label_accuracy(classification_pairs),
        "suitable_accuracy": _label_accuracy(suitable_pairs),
        "unsuitable_accuracy": _label_accuracy(unsuitable_pairs),
        "review_case_result": review_case_result,
        "subject_accuracy": _accuracy(subject_pairs),
        "action_accuracy": _accuracy(action_pairs),
        "action_applicable_cases": len(action_pairs),
        "environment_accuracy": _accuracy(environment_pairs),
        "exact_entity_accuracy": _accuracy(exact_pairs),
        "exact_entity_applicable_cases": len(exact_pairs),
        "must_have_accuracy": _accuracy(must_pairs),
        "negative_element_accuracy": _accuracy(negative_pairs),
        "false_hard_reject_count": false_hard_reject_count,
        "false_suitable_count": false_suitable_count,
        "structured_response_validity": _safe_div(
            sum(1 for row in candidate_results if bool(row.get("structured_response_valid"))),
            total,
        ),
        "failed_calls": sum(1 for row in candidate_results if row.get("status") != "success"),
        "total_input_tokens": sum(int(row.get("input_tokens") or 0) for row in candidate_results),
        "total_output_tokens": sum(int(row.get("output_tokens") or 0) for row in candidate_results),
        "total_calculated_cost_usd": round(sum(float(row.get("calculated_cost_usd") or 0.0) for row in candidate_results), 6),
    }


def _append_bool_pair(pairs: list[tuple[bool, bool]], expected: Any, actual: Any) -> None:
    if expected is None or actual is None:
        return
    pairs.append((bool(expected), bool(actual)))


def _label_accuracy(pairs: list[tuple[str, str]]) -> float:
    if not pairs:
        return 0.0
    return _safe_div(sum(1 for expected, actual in pairs if expected == actual), len(pairs))


def _write_controlled_live_eval_artifacts(
    *,
    results_dir: Path,
    dataset: EvaluationDataset,
    summary: dict[str, Any],
    metrics: dict[str, Any],
    candidate_results: list[dict[str, Any]],
    usage_rows: list[dict[str, Any]],
) -> dict[str, str]:
    results = {
        "schema_version": "openai_live_eval_results.v1",
        "summary": summary,
        "metrics": metrics,
        "candidate_results": candidate_results,
        "safety": _live_safety_summary(summary),
    }
    usage = {
        "schema_version": "openai_live_eval_usage.v1",
        "summary": {
            "calls_attempted": summary["calls_attempted"],
            "calls_succeeded": summary["calls_succeeded"],
            "calls_failed": summary["calls_failed"],
            "external_http_attempts": summary["external_http_attempts"],
            "images_sent": summary["images_sent"],
            "total_input_tokens": summary["total_input_tokens"],
            "total_output_tokens": summary["total_output_tokens"],
            "total_cached_tokens": summary["total_cached_tokens"],
            "total_calculated_cost_usd": summary["total_calculated_cost_usd"],
        },
        "usage_records": usage_rows,
    }
    paths = {
        "results": results_dir / "LIVE_EVAL_RESULTS.json",
        "usage": results_dir / "LIVE_EVAL_USAGE.json",
        "report": results_dir / "LIVE_EVAL_REPORT.md",
        "comparison": results_dir / "LIVE_EVAL_COMPARISON.html",
        "checkpoint": results_dir / "LIVE_EVAL_EXECUTION_CHECKPOINT.json",
    }
    _write_json(paths["results"], results)
    _write_json(paths["usage"], usage)
    paths["report"].write_text(_live_report_markdown(summary, metrics, candidate_results), encoding="utf-8")
    paths["comparison"].write_text(_live_comparison_html(dataset, summary, metrics, candidate_results), encoding="utf-8")
    return {key: _public_path(value) for key, value in paths.items()}


def _live_safety_summary(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "budget_limit_usd": CONTROLLED_LIVE_BUDGET_CAP_USD,
        "budget_exceeded": bool(summary.get("budget_exceeded")),
        "calls_within_limit": int(summary.get("external_http_attempts") or 0) <= CONTROLLED_LIVE_MAX_CALL_CAP,
        "images_within_limit": int(summary.get("images_sent") or 0) <= CONTROLLED_LIVE_IMAGES,
        "semantic_rerank_enabled": False,
        "production_selection_changed": False,
        "detail": summary.get("detail"),
        "model": summary.get("model"),
    }


def _live_report_markdown(summary: dict[str, Any], metrics: dict[str, Any], candidate_results: list[dict[str, Any]]) -> str:
    pair_answers = _pair_answers(candidate_results)
    lines = [
        "# OpenAI Semantic Vision Controlled Live Evaluation",
        "",
        "## Summary",
        "",
        f"- Live evaluation executed: {str(bool(summary.get('live_vision_calls_performed'))).lower()}",
        f"- Calls attempted/succeeded/failed: {summary.get('calls_attempted')}/{summary.get('calls_succeeded')}/{summary.get('calls_failed')}",
        f"- External HTTP attempts: {summary.get('external_http_attempts')}",
        f"- Images sent: {summary.get('images_sent')}",
        f"- Total calculated cost USD: {summary.get('total_calculated_cost_usd')}",
        f"- Classification accuracy: {metrics.get('classification_accuracy')}",
        f"- Stop reasons: {', '.join(summary.get('stop_reasons') or []) or 'none'}",
        "",
        "## Metrics",
        "",
    ]
    for key in (
        "suitable_accuracy",
        "unsuitable_accuracy",
        "review_case_result",
        "subject_accuracy",
        "action_accuracy",
        "environment_accuracy",
        "exact_entity_accuracy",
        "must_have_accuracy",
        "negative_element_accuracy",
        "false_hard_reject_count",
        "false_suitable_count",
        "structured_response_validity",
        "failed_calls",
        "total_input_tokens",
        "total_output_tokens",
        "total_calculated_cost_usd",
    ):
        lines.append(f"- {key}: {metrics.get(key)}")
    lines.extend(["", "## Required Answers", ""])
    for question, answer in pair_answers.items():
        lines.append(f"- {question}: {answer}")
    lines.extend(["", "## Candidate Results", ""])
    for row in candidate_results:
        lines.append(
            "- "
            f"{row['scene_id']} / {row['candidate_id']}: expected={row['expected_classification']}, "
            f"returned={row['returned_classification']}, score={row['semantic_score']}, "
            f"confidence={row['confidence']}, status={row['status']}, request_id={row['request_id'] or 'n/a'}"
        )
        if row.get("mismatch_reasons"):
            lines.append(f"  mismatch_reasons: {', '.join(row['mismatch_reasons'])}")
        if row.get("review_required_reasons"):
            lines.append(f"  review_required_reasons: {', '.join(row['review_required_reasons'])}")
        if row.get("short_evidence"):
            lines.append(f"  evidence: {row['short_evidence']}")
    lines.append("")
    return "\n".join(lines)


def _pair_answers(candidate_results: list[dict[str, Any]]) -> dict[str, str]:
    by_id = {str(row.get("candidate_id") or ""): row for row in candidate_results}
    saturn = by_id.get("scene01_A_saturn_v_launch", {})
    shuttle = by_id.get("scene01_B_space_shuttle_launch", {})
    bear_fish = by_id.get("scene02_A_bear_catching_salmon", {})
    bear_no_fish = by_id.get("scene02_B_bear_standing_river", {})
    forest = by_id.get("scene03_A_misty_forest_canopy", {})
    desert = by_id.get("scene03_B_desert_dunes", {})
    action_confidence_high = any(
        row.get("candidate_id") == "scene02_B_bear_standing_river"
        and float(row.get("confidence") or 0.0) > 0.85
        and row.get("returned_classification") == "suitable"
        for row in candidate_results
    )
    return {
        "Отличила ли модель Saturn V от Space Shuttle": _yes_no(
            saturn.get("returned_classification") in {"suitable", "review"}
            and shuttle.get("returned_classification") == "unsuitable"
            and bool(shuttle.get("exact_entity_match")) is False
        ),
        "Отличила ли модель медведя с рыбой от медведя без рыбы": _yes_no(
            bear_fish.get("returned_classification") in {"suitable", "review"}
            and bear_no_fish.get("returned_classification") in {"review", "unsuitable"}
            and bool(bear_no_fish.get("action_match")) is False
        ),
        "Отличила ли модель лес от пустыни": _yes_no(
            forest.get("returned_classification") in {"suitable", "review"}
            and desert.get("returned_classification") == "unsuitable"
            and bool(desert.get("environment_match")) is False
        ),
        "Не завысила ли confidence для действия на одном изображении": _yes_no(not action_confidence_high),
        "Корректно ли обработала illustrative scene": _yes_no(
            forest.get("returned_classification") in {"suitable", "review"} and desert.get("returned_classification") == "unsuitable"
        ),
        "Подходит ли detail=low для дальнейшего использования": "yes" if _low_detail_sufficient(candidate_results) else "no",
        "Нужен ли повтор отдельных случаев на detail=high": "yes" if _high_detail_repeat_needed(candidate_results) else "no",
    }


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def _low_detail_sufficient(candidate_results: list[dict[str, Any]]) -> bool:
    return bool(candidate_results) and all(row.get("status") == "success" for row in candidate_results) and _high_detail_repeat_needed(candidate_results) is False


def _high_detail_repeat_needed(candidate_results: list[dict[str, Any]]) -> bool:
    return any(
        row.get("status") != "success"
        or row.get("returned_classification") == "review"
        or float(row.get("confidence") or 0.0) < CONTROLLED_LIVE_RESULT_THRESHOLD
        for row in candidate_results
    )


def _live_comparison_html(
    dataset: EvaluationDataset,
    summary: dict[str, Any],
    metrics: dict[str, Any],
    candidate_results: list[dict[str, Any]],
) -> str:
    frame_by_candidate = _candidate_frame_map(dataset)
    rows = []
    for row in candidate_results:
        candidate_id = str(row.get("candidate_id") or "")
        image_src = _comparison_image_src(frame_by_candidate.get(candidate_id, ""))
        image_html = (
            f'<img src="{html.escape(image_src)}" alt="candidate frame">'
            if image_src
            else ""
        )
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(row.get('scene_id') or ''))}</td>"
            f"<td>{html.escape(candidate_id)}</td>"
            f"<td>{html.escape(str(row.get('expected_classification') or ''))}</td>"
            f"<td>{html.escape(str(row.get('returned_classification') or ''))}</td>"
            f"<td>{html.escape(str(row.get('semantic_score') or ''))}</td>"
            f"<td>{html.escape(str(row.get('confidence') or ''))}</td>"
            f"<td>{html.escape(str(row.get('status') or ''))}</td>"
            f"<td>{html.escape(str(row.get('request_id') or ''))}</td>"
            f"<td>{image_html}</td>"
            f"<td>{html.escape(str(row.get('short_evidence') or ''))}</td>"
            "</tr>"
        )
    return "\n".join(
        [
            "<!doctype html>",
            "<html lang=\"en\">",
            "<head>",
            "<meta charset=\"utf-8\">",
            "<title>OpenAI Semantic Vision Live Evaluation</title>",
            "<style>",
            "body{font-family:Arial,sans-serif;margin:24px;color:#1f2933;background:#f7f9fb}",
            "table{border-collapse:collapse;width:100%;background:white}",
            "th,td{border:1px solid #d9e2ec;padding:8px;vertical-align:top;font-size:13px}",
            "th{background:#e6edf5;text-align:left}",
            "img{max-width:160px;max-height:160px;object-fit:contain}",
            ".summary{margin-bottom:18px}",
            "</style>",
            "</head>",
            "<body>",
            "<h1>OpenAI Semantic Vision Live Evaluation</h1>",
            "<div class=\"summary\">",
            f"<p>Model: {html.escape(str(summary.get('model') or ''))}; detail: {html.escape(str(summary.get('detail') or ''))}; calls: {summary.get('calls_attempted')}/{summary.get('calls_succeeded')}/{summary.get('calls_failed')}; cost: {summary.get('total_calculated_cost_usd')}</p>",
            f"<p>Classification accuracy: {metrics.get('classification_accuracy')}; structured validity: {metrics.get('structured_response_validity')}</p>",
            "</div>",
            "<table>",
            "<thead><tr><th>Scene</th><th>Candidate</th><th>Expected</th><th>Returned</th><th>Score</th><th>Confidence</th><th>Status</th><th>Request ID</th><th>Frame</th><th>Evidence</th></tr></thead>",
            "<tbody>",
            *rows,
            "</tbody>",
            "</table>",
            "</body>",
            "</html>",
        ]
    )


def _candidate_frame_map(dataset: EvaluationDataset) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for case in dataset.cases:
        if not case.sampled_frames:
            continue
        frame = dict(case.sampled_frames[0])
        mapping[case.candidate_id] = str(frame.get("dataset_relative_path") or frame.get("relative_path") or "")
    return mapping


def _comparison_image_src(dataset_relative_path: str) -> str:
    if not dataset_relative_path:
        return ""
    value = dataset_relative_path.replace("\\", "/")
    if _looks_absolute_live(value) or value.startswith("data:"):
        return ""
    if value.startswith("docs/implementation/openai_live_evaluation/"):
        return "../" + value.removeprefix("docs/implementation/openai_live_evaluation/")
    return "../" + value.lstrip("/")


def _looks_absolute_live(value: str) -> bool:
    return bool(value.startswith("/") or value.startswith("\\\\") or (len(value) > 2 and value[1] == ":" and value[2] in {"\\", "/"}))


def _openai_payload_image_count(kwargs: dict[str, Any]) -> int:
    count = 0
    for item in kwargs.get("input") or []:
        for content in (item or {}).get("content") or []:
            if isinstance(content, dict) and content.get("type") == "input_image":
                count += 1
    return count


def _write_live_execution_checkpoint(
    results_dir: Path,
    *,
    phase: str,
    live_calls_performed: bool,
    paid_calls_performed: bool,
    calls_attempted: int,
    calls_succeeded: int,
    calls_failed: int,
    images_sent: int,
    total_cost_usd: float,
    budget_exceeded: bool,
    ready_for_result_review: bool,
    stop_reasons: list[str],
) -> None:
    checkpoint = {
        "phase": phase,
        "live_calls_performed": bool(live_calls_performed),
        "paid_calls_performed": bool(paid_calls_performed),
        "calls_attempted": int(calls_attempted),
        "calls_succeeded": int(calls_succeeded),
        "calls_failed": int(calls_failed),
        "images_sent": int(images_sent),
        "total_cost_usd": round(float(total_cost_usd), 6),
        "budget_exceeded": bool(budget_exceeded),
        "production_selection_changed": False,
        "semantic_rerank_enabled": False,
        "ready_for_result_review": bool(ready_for_result_review),
        "stop_reasons": stop_reasons,
    }
    _write_json(results_dir / "LIVE_EVAL_EXECUTION_CHECKPOINT.json", checkpoint)


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(_public_json(data), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _public_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _public_json(item) for key, item in value.items() if not _private_key(str(key))}
    if isinstance(value, list):
        return [_public_json(item) for item in value]
    if isinstance(value, str):
        if value.startswith("data:") or "base64," in value:
            return "[redacted]"
        if _looks_absolute_live(value):
            return ""
        return value
    return value


def _private_key(key: str) -> bool:
    normalized = key.lower()
    return any(marker in normalized for marker in ("api_key", "apikey", "secret", "password", "private_local_path"))


def _public_path(path: str | Path) -> str:
    text = str(path).replace("\\", "/")
    if text.startswith("G:/Projects/AI-YouTube/"):
        return text.removeprefix("G:/Projects/AI-YouTube/")
    return "" if _looks_absolute_live(text) else text


def _frames_for_case(case: EvaluationCase, root: Path) -> list[SemanticFrameReference]:
    frames: list[SemanticFrameReference] = []
    folder = root / case.case_id
    folder.mkdir(parents=True, exist_ok=True)
    for index in range(case.frame_count):
        path = folder / f"frame_{index:03d}.jpg"
        if not path.exists():
            color = _case_color(case.category, index)
            Image.new("RGB", (32, 48), color).save(path)
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        frames.append(
            SemanticFrameReference(
                frame_index=index,
                sha256=sha,
                perceptual_hash=f"{index:016x}"[-16:],
                relative_path=f"semantic_visual_eval_frames/{case.case_id}/frame_{index:03d}.jpg",
                width=32,
                height=48,
                actual_timestamp_sec=float(index),
                is_poster_frame=case.category == "poster_only_video" or case.frame_count == 1,
                private_local_path=str(path),
            )
        )
    return frames


def _prepared_frames_for_case(case: EvaluationCase) -> list[SemanticFrameReference]:
    if not case.sampled_frames:
        return []
    raw = dict(case.sampled_frames[0])
    frame_path = _resolve_prepared_frame_path(raw, case)
    return [
        SemanticFrameReference(
            frame_index=0,
            sha256=str(raw.get("sha256") or ""),
            perceptual_hash=str(raw.get("perceptual_hash") or ""),
            relative_path=str(raw.get("relative_path") or ""),
            width=int(raw.get("width") or 0),
            height=int(raw.get("height") or 0),
            requested_timestamp_sec=0.0,
            actual_timestamp_sec=0.0,
            extraction_status=str(raw.get("extraction_status") or "ok"),
            is_poster_frame=True,
            technical_metrics=dict(raw.get("technical_metrics") or {}),
            private_local_path=str(frame_path),
        )
    ]


def _resolve_prepared_frame_path(raw: dict[str, Any], case: EvaluationCase) -> Path:
    candidates = [str(raw.get("dataset_relative_path") or ""), str(raw.get("relative_path") or "")]
    dataset_parent = Path(case.dataset_path).parent if case.dataset_path else Path(".")
    for value in candidates:
        if not value:
            continue
        path = Path(value)
        if path.is_absolute() and path.exists():
            return path
        if path.exists():
            return path
        parent_path = dataset_parent / path
        if parent_path.exists():
            return parent_path
    return Path(candidates[0])


def _load_prepared_live_eval_dataset(data: dict[str, Any], *, target: Path, explicit_dataset: bool) -> EvaluationDataset:
    scenes = data.get("scenes") if isinstance(data.get("scenes"), list) else []
    cases: list[EvaluationCase] = []
    for scene in scenes:
        requirements = dict(scene.get("requirements") or {})
        scene_id = str(scene.get("scene_id") or requirements.get("scene_id") or "")
        strictness = str(requirements.get("semantic_strictness") or scene.get("scene_type") or "balanced")
        for candidate in scene.get("candidates") or []:
            candidate_id = str(candidate.get("candidate_id") or "")
            ground_truth = dict(candidate.get("ground_truth") or {})
            expected_action = _ground_truth_bool(ground_truth.get("expected_action_match"))
            expected_exact = _ground_truth_bool(ground_truth.get("expected_exact_entity_match"))
            if not str(requirements.get("action") or "").strip():
                expected_action = None
            if not str(requirements.get("exact_entity") or "").strip():
                expected_exact = None
            cases.append(
                EvaluationCase(
                    case_id=candidate_id,
                    scene_id=scene_id,
                    candidate_id=candidate_id,
                    category=str(ground_truth.get("expected_classification") or "prepared_live_eval"),
                    strictness=strictness,
                    frame_count=1,
                    media_type="image",
                    expected={
                        "subject": _ground_truth_bool(ground_truth.get("expected_subject_match")),
                        "action": expected_action,
                        "environment": _ground_truth_bool(ground_truth.get("expected_environment_match")),
                        "exact_entity": expected_exact,
                        "must_have_present": _all_terms_present(ground_truth.get("expected_must_have")),
                        "negative_present": _any_terms_present(ground_truth.get("expected_negative_elements")),
                    },
                    provider=str(candidate.get("provider") or "prepared_dataset"),
                    requirements=requirements,
                    candidate_metadata={
                        "asset_id": candidate_id,
                        "provider": str(candidate.get("provider") or "prepared_dataset"),
                        "provider_asset_id": str(candidate.get("provider_asset_id") or ""),
                        "media_type": "image",
                        "title": str(candidate.get("title") or candidate_id),
                        "source_page": str(candidate.get("source_page") or ""),
                        "preview_use": str(candidate.get("preview_use") or ""),
                        "limited_temporal_evidence": True,
                        "image_variant_policy": "canonical_frame_only",
                    },
                    sampled_frames=[dict(item) for item in candidate.get("sampled_frames") or []],
                    technical_metrics_summary={**dict(candidate.get("technical_analysis") or {}), "limited_temporal_evidence": True},
                    limited_temporal_evidence=True,
                    dataset_path=str(target),
                )
            )
    return EvaluationDataset(
        schema_version=str(data.get("schema_version") or "openai_live_eval_dataset.v1"),
        cases=cases,
        models=["gpt-5.6-terra"],
        scene_count=len(scenes),
        candidate_count=len(cases),
        dataset_path=str(target),
        constraints=dict(data.get("constraints") or {}),
        explicit_dataset=explicit_dataset,
    )


def _controlled_runtime_authorization_reasons(
    *,
    dataset: EvaluationDataset,
    cli_config: dict[str, Any],
    base_config: dict[str, Any],
    model: str,
    detail: str,
    projected_calls: int,
    projected_image_count: int,
    max_frame_count: int,
) -> list[str]:
    reasons: list[str] = []
    cfg = OpenAISemanticConfig.from_config(_effective_semantic_config(base_config, cli_config, runtime_authorized=False))
    reasons.extend(_persistent_default_reasons(base_config))

    if not dataset.explicit_dataset or not dataset.dataset_path:
        reasons.append("runtime_dataset_required")
    elif not Path(dataset.dataset_path).exists():
        reasons.append("runtime_dataset_required")
    elif not _is_controlled_live_eval_dataset(dataset.dataset_path):
        reasons.append("runtime_dataset_not_allowlisted")

    if (
        dataset.scene_count != CONTROLLED_LIVE_SCENES
        or dataset.candidate_count != CONTROLLED_LIVE_CANDIDATES
        or projected_calls != CONTROLLED_LIVE_CALLS
        or projected_image_count != CONTROLLED_LIVE_IMAGES
    ):
        reasons.append("runtime_dataset_counts_mismatch")

    constraints = dataset.constraints
    if _optional_int(constraints.get("scenes")) not in (None, CONTROLLED_LIVE_SCENES):
        reasons.append("runtime_dataset_counts_mismatch")
    if _optional_int(constraints.get("candidates_per_scene")) not in (None, CONTROLLED_LIVE_CANDIDATES // CONTROLLED_LIVE_SCENES):
        reasons.append("runtime_dataset_counts_mismatch")
    if _optional_int(constraints.get("maximum_future_api_calls")) not in (None, CONTROLLED_LIVE_CALLS):
        reasons.append("runtime_dataset_counts_mismatch")
    if _optional_int(constraints.get("maximum_future_images")) not in (None, CONTROLLED_LIVE_IMAGES):
        reasons.append("runtime_dataset_counts_mismatch")

    if model != CONTROLLED_LIVE_MODEL:
        reasons.append("runtime_model_not_controlled")
    if model not in cfg.model_allowlist:
        reasons.append("model_not_allowlisted")
    if str(constraints.get("model") or CONTROLLED_LIVE_MODEL) != CONTROLLED_LIVE_MODEL:
        reasons.append("runtime_dataset_model_mismatch")

    if detail != CONTROLLED_LIVE_DETAIL:
        reasons.append("runtime_detail_not_controlled")
    if detail not in OPENAI_ALLOWED_DETAILS or detail not in cfg.allowed_details:
        reasons.append("detail_not_allowed")
    if str(constraints.get("detail") or CONTROLLED_LIVE_DETAIL) != CONTROLLED_LIVE_DETAIL:
        reasons.append("runtime_dataset_detail_mismatch")

    expected_max_frames = _optional_int(constraints.get("maximum_frames_per_candidate"))
    if max_frame_count != CONTROLLED_LIVE_MAX_FRAMES_PER_CANDIDATE or expected_max_frames not in (None, CONTROLLED_LIVE_MAX_FRAMES_PER_CANDIDATE):
        reasons.append("runtime_frame_limit_mismatch")

    if not cfg.allow_paid_vision_cli:
        reasons.append("runtime_allow_paid_vision_required")
    if cfg.budget_usd_cli <= 0:
        reasons.append("runtime_budget_usd_required")
    elif cfg.budget_usd_cli > CONTROLLED_LIVE_BUDGET_CAP_USD:
        reasons.append("runtime_budget_cap_exceeded")
    if cfg.max_calls_cli <= 0:
        reasons.append("runtime_max_calls_required")
    elif cfg.max_calls_cli > CONTROLLED_LIVE_MAX_CALL_CAP:
        reasons.append("runtime_call_limit_exceeded")
    elif projected_calls > cfg.max_calls_cli:
        reasons.append("runtime_call_limit_below_dataset")
    if cfg.confirm_paid_vision != LIVE_CONFIRMATION_PHRASE:
        reasons.append("runtime_confirmation_required")

    if not os.getenv("OPENAI_API_KEY"):
        reasons.append("runtime_openai_key_required")
    if bool(constraints.get("semantic_rerank_enabled", False)):
        reasons.append("runtime_semantic_rerank_enabled")
    if bool(constraints.get("production_selection_changed", False)):
        reasons.append("runtime_production_selection_changed")

    return _unique_reasons(reasons)


def _effective_semantic_config(base_config: dict[str, Any], cli_config: dict[str, Any], *, runtime_authorized: bool) -> dict[str, Any]:
    effective = dict(base_config or {})
    openai = dict(effective.get("openai") or {})
    effective["openai"] = openai
    effective["allow_paid_vision_cli"] = bool(cli_config.get("allow_paid_vision_cli", False))
    effective["budget_usd_cli"] = max(0.0, float(cli_config.get("budget_usd_cli") or 0.0))
    effective["max_calls_cli"] = max(0, int(cli_config.get("max_calls_cli") or 0))
    effective["confirm_paid_vision"] = str(cli_config.get("confirm_paid_vision") or "")

    if runtime_authorized:
        runtime_budget = min(effective["budget_usd_cli"], CONTROLLED_LIVE_BUDGET_CAP_USD)
        runtime_max_calls = min(effective["max_calls_cli"], CONTROLLED_LIVE_MAX_CALL_CAP)
        openai.update(
            {
                "enabled": True,
                "primary_model": CONTROLLED_LIVE_MODEL,
                "initial_detail": CONTROLLED_LIVE_DETAIL,
                "reasoning_effort": "low",
                "allow_paid_vision": True,
                "maximum_budget_usd": runtime_budget,
                "maximum_calls_per_project": runtime_max_calls,
                "maximum_candidates_per_scene": CONTROLLED_LIVE_CANDIDATES // CONTROLLED_LIVE_SCENES,
                "maximum_frames_per_candidate": CONTROLLED_LIVE_MAX_FRAMES_PER_CANDIDATE,
                "input_cost_per_1k_tokens_usd": CONTROLLED_LIVE_INPUT_COST_PER_1K_TOKENS_USD,
                "output_cost_per_1k_tokens_usd": CONTROLLED_LIVE_OUTPUT_COST_PER_1K_TOKENS_USD,
            }
        )
        effective["allow_paid_vision"] = True
        effective["maximum_budget_usd"] = runtime_budget
        effective["maximum_calls_per_project"] = runtime_max_calls
    return effective


def _persistent_default_reasons(config: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    raw = dict(config or {})
    openai = dict(raw.get("openai") or {})
    if bool(openai.get("enabled", False)):
        reasons.append("persistent_openai_enabled")
    if bool(openai.get("allow_paid_vision", raw.get("allow_paid_vision", False))):
        reasons.append("persistent_paid_vision_enabled")
    if _optional_float(openai.get("maximum_budget_usd", raw.get("maximum_budget_usd", 0.0))) != 0.0:
        reasons.append("persistent_budget_nonzero")
    if _optional_int(openai.get("maximum_calls_per_project", raw.get("maximum_calls_per_project", 0))) not in (None, 0):
        reasons.append("persistent_call_limit_nonzero")
    if bool(raw.get("semantic_rerank_enabled", False)):
        reasons.append("runtime_semantic_rerank_enabled")
    return reasons


def _is_controlled_live_eval_dataset(path: str | Path) -> bool:
    try:
        return Path(path).resolve() == CONTROLLED_LIVE_EVAL_DATASET_PATH.resolve()
    except OSError:
        return False


def _dataset_limit_reasons(
    dataset: EvaluationDataset,
    *,
    cfg: OpenAISemanticConfig,
    projected_calls: int,
    projected_image_count: int,
) -> list[str]:
    if not dataset.explicit_dataset:
        return []
    reasons: list[str] = []
    constraints = dataset.constraints
    expected_scenes = _optional_int(constraints.get("scenes"))
    expected_candidates_per_scene = _optional_int(constraints.get("candidates_per_scene"))
    expected_calls = _optional_int(constraints.get("maximum_future_api_calls"))
    expected_images = _optional_int(constraints.get("maximum_future_images"))
    if expected_scenes is not None and expected_scenes != dataset.scene_count:
        reasons.append("dataset_scenes_mismatch")
    if expected_candidates_per_scene is not None and expected_candidates_per_scene * max(1, dataset.scene_count) != dataset.candidate_count:
        reasons.append("dataset_candidates_mismatch")
    if expected_calls is not None and expected_calls != projected_calls:
        reasons.append("dataset_calls_mismatch")
    if expected_images is not None and expected_images != projected_image_count:
        reasons.append("dataset_images_mismatch")
    if cfg.max_calls_cli > 0 and cfg.max_calls_cli != projected_calls:
        reasons.append("cli_max_calls_mismatch")
    if reasons:
        return ["dataset_limits_mismatch", *_unique_reasons(reasons)]
    return []


def _budget_candidate_count(dataset: EvaluationDataset, request_count: int, cfg: OpenAISemanticConfig) -> int:
    if dataset.explicit_dataset:
        return _optional_int(dataset.constraints.get("candidates_per_scene")) or 1
    return min(request_count, max(0, cfg.maximum_candidates_per_scene + 1))


def _optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _optional_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _all_terms_present(value: Any) -> bool:
    items = value if isinstance(value, list) else []
    return all(bool(item.get("present")) for item in items if isinstance(item, dict))


def _any_terms_present(value: Any) -> bool:
    items = value if isinstance(value, list) else []
    return any(bool(item.get("present")) for item in items if isinstance(item, dict))


def _ground_truth_bool(value: Any) -> bool | None:
    if value in (None, "not_applicable", "n/a", "na"):
        return None
    return bool(value)


def _case_color(category: str, index: int) -> tuple[int, int, int]:
    base = {
        "wrong_subject": (150, 110, 40),
        "wrong_action": (60, 90, 150),
        "wrong_location": (130, 100, 50),
        "negative_element_present": (180, 120, 50),
        "low_confidence": (40, 45, 50),
    }.get(category, (20, 80, 140))
    return tuple(max(0, min(255, value + index * 7)) for value in base)


def _mock_fixture_for_case(category: str) -> str:
    return {
        "wrong_subject": "subject_mismatch",
        "wrong_action": "action_mismatch",
        "missing_must_have": "must_have_missing",
        "negative_element_present": "negative_violation",
        "one_misleading_frame": "one_anomalous_frame",
        "low_confidence": "low_confidence",
    }.get(category, "good_match")


def _expected_bool(value: Any) -> bool | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in {"not_applicable", "n/a", "na"}:
        return None
    if value == "mismatch":
        return False
    if value == "match":
        return True
    if isinstance(value, bool):
        return value
    return bool(value)


def _accuracy(pairs: list[tuple[bool, bool]]) -> float:
    if not pairs:
        return 0.0
    return _safe_div(sum(1 for expected, actual in pairs if expected == actual), len(pairs))


def _safe_div(numerator: float, denominator: float) -> float:
    return round(float(numerator) / float(denominator), 6) if denominator else 0.0


def _score_stability(scores: list[float]) -> float:
    if len(scores) <= 1:
        return 1.0
    return round(max(0.0, 1.0 - statistics.pstdev(scores)), 6)


def _unique_reasons(values: list[str]) -> list[str]:
    return [item for item in dict.fromkeys(values) if item]


def _load_semantic_config() -> dict[str, Any]:
    path = Path("config/semantic_visual.json")
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _default_eval_config() -> dict[str, Any]:
    return {
        "schema_version": "semantic_visual_eval.v1",
        "models": ["mock", "gpt-5.6-terra", "gpt-5.6-luna"],
        "cases": [
            _case("case_correct", "correct_subject_action_environment", "balanced"),
            _case("case_wrong_subject", "wrong_subject", "strict", subject="mismatch"),
            _case("case_wrong_action", "wrong_action", "strict", action="mismatch"),
            _case("case_wrong_location", "wrong_location", "balanced"),
            _case("case_exact_entity", "exact_entity_mismatch", "strict"),
            _case("case_missing_must", "missing_must_have", "strict", must_have_present=False),
            _case("case_negative", "negative_element_present", "strict", negative_present=True),
            _case("case_generic_broll", "generic_acceptable_b_roll", "illustrative"),
            _case("case_misleading_frame", "one_misleading_frame", "balanced"),
            _case("case_poster_only", "poster_only_video", "balanced", frame_count=1),
            _case("case_low_confidence", "low_confidence", "balanced"),
            _case("case_strict_scene", "strict_scene", "strict"),
            _case("case_balanced_scene", "balanced_scene", "balanced"),
            _case("case_illustrative_scene", "illustrative_scene", "illustrative"),
        ],
    }


def _case(
    case_id: str,
    category: str,
    strictness: str,
    *,
    frame_count: int = 3,
    subject: str = "match",
    action: str = "match",
    environment: str = "match",
    must_have_present: bool = True,
    negative_present: bool = False,
) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "category": category,
        "strictness": strictness,
        "frame_count": frame_count,
        "media_type": "video",
        "expected": {
            "subject": subject,
            "action": action,
            "environment": environment,
            "must_have_present": must_have_present,
            "negative_present": negative_present,
        },
    }
