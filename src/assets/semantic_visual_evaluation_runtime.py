from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.config_resolver.paths import repository_path

from .semantic_visual_evaluation_tooling import (
    CONTROLLED_LIVE_BUDGET_CAP_USD,
    CONTROLLED_LIVE_CALLS,
    CONTROLLED_LIVE_CANDIDATES,
    CONTROLLED_LIVE_DETAIL,
    CONTROLLED_LIVE_EVAL_DATASET_PATH,
    CONTROLLED_LIVE_IMAGES,
    CONTROLLED_LIVE_INPUT_COST_PER_1K_TOKENS_USD,
    CONTROLLED_LIVE_MAX_CALL_CAP,
    CONTROLLED_LIVE_MAX_FRAMES_PER_CANDIDATE,
    CONTROLLED_LIVE_MODEL,
    CONTROLLED_LIVE_OUTPUT_COST_PER_1K_TOKENS_USD,
    CONTROLLED_LIVE_RESULTS_DIR,
    CONTROLLED_LIVE_SCENES,
    DEFAULT_EVAL_CONFIG_PATH,
    EvaluationCase,
    EvaluationDataset,
    _candidate_live_result_row,
    _compute_live_metrics,
    _public_path,
    _write_controlled_live_eval_artifacts,
    _write_json,
    build_evaluation_requests,
    compute_evaluation_metrics,
    load_semantic_visual_eval_config,
    mocked_results_for_dataset,
)
from .semantic_visual_models import SemanticVisualRequest
from .semantic_visual_openai import (
    LIVE_CONFIRMATION_PHRASE,
    OPENAI_ALLOWED_DETAILS,
    OpenAIRequestBuilder,
    OpenAISemanticVisualBackend,
    OpenAISemanticConfig,
    VisionBudgetGuard,
    semantic_visual_result_json_schema,
)


@dataclass
class _EvaluationContext:
    dataset: EvaluationDataset
    requests: list[SemanticVisualRequest]
    image_count: int
    detail: str
    base_semantic_config: dict[str, Any]
    runtime_reasons: list[str]
    runtime_authorized: bool
    semantic_config: dict[str, Any]
    backend_config: OpenAISemanticConfig
    limit_reasons: list[str]


@dataclass
class _LiveExecutionState:
    attempt_budget: "_ExternalAttemptBudget"
    original_maximum_retries: int
    candidate_results: list[dict[str, Any]] = field(default_factory=list)
    usage_rows: list[dict[str, Any]] = field(default_factory=list)
    stop_reasons: list[str] = field(default_factory=list)
    logical_attempts: int = 0
    succeeded: int = 0
    failed: int = 0

    @property
    def total_cost(self) -> float:
        return round(
            sum(float(row.get("calculated_cost_usd") or 0.0) for row in self.candidate_results),
            6,
        )


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
        dataset = load_semantic_visual_eval_config(
            dataset_path or DEFAULT_EVAL_CONFIG_PATH,
            require_exists=bool(dataset_path),
        )
    except FileNotFoundError as exc:
        return _missing_dataset_result(
            backend=backend,
            model=model,
            dry_run=dry_run,
            mocked=mocked,
            dataset_path=dataset_path,
            error=exc,
        )

    context = _prepare_evaluation_context(
        dataset,
        backend=backend,
        config=config,
        model=model,
    )
    if dry_run:
        return _dry_run_result(context, backend=backend, model=model)
    if dataset.explicit_dataset and (context.limit_reasons or context.runtime_reasons) and not mocked and backend != "mock":
        return _blocked_result(
            context,
            backend=backend,
            model=model,
            reasons=[*context.limit_reasons, *context.runtime_reasons],
        )
    if mocked or backend == "mock":
        return _mocked_result(context, backend=backend, model=model, mocked=mocked)
    if backend != "openai":
        return _blocked_result(
            context,
            backend=backend,
            model=model,
            reasons=["live_evaluation_backend_not_supported"],
        )
    return _run_controlled_openai_live_evaluation(
        context=context,
        model=model,
        client=client,
        results_dir=Path(results_dir) if results_dir is not None else CONTROLLED_LIVE_RESULTS_DIR,
    )


def _prepare_evaluation_context(
    dataset: EvaluationDataset,
    *,
    backend: str,
    config: dict[str, Any] | None,
    model: str,
) -> _EvaluationContext:
    requests = build_evaluation_requests(dataset, backend=backend, model=model)
    image_count = sum(len(request.sampled_frame_references) for request in requests)
    max_frame_count = max((len(request.sampled_frame_references) for request in requests), default=0)
    base_semantic_config = _load_semantic_config()
    cli_config = dict(config or {})
    runtime_reasons = _controlled_runtime_authorization_reasons(
        dataset=dataset,
        cli_config=cli_config,
        base_config=base_semantic_config,
        model=model,
        detail=CONTROLLED_LIVE_DETAIL,
        projected_calls=len(requests),
        projected_image_count=image_count,
        max_frame_count=max_frame_count,
    )
    runtime_authorized = not runtime_reasons
    semantic_config = _effective_semantic_config(
        base_semantic_config,
        cli_config,
        runtime_authorized=runtime_authorized,
    )
    backend_config = OpenAISemanticConfig.from_config(semantic_config)
    limit_reasons = _dataset_limit_reasons(
        dataset,
        cfg=backend_config,
        projected_calls=len(requests),
        projected_image_count=image_count,
    )
    return _EvaluationContext(
        dataset=dataset,
        requests=requests,
        image_count=image_count,
        detail=CONTROLLED_LIVE_DETAIL,
        base_semantic_config=base_semantic_config,
        runtime_reasons=runtime_reasons,
        runtime_authorized=runtime_authorized,
        semantic_config=semantic_config,
        backend_config=backend_config,
        limit_reasons=limit_reasons,
    )


def _dry_run_result(
    context: _EvaluationContext,
    *,
    backend: str,
    model: str,
) -> dict[str, Any]:
    builder = OpenAIRequestBuilder(context.backend_config)
    schema = semantic_visual_result_json_schema()
    built_count = invalid_count = 0
    for request in context.requests:
        try:
            builder.build(request, model=model, detail=context.detail)
            built_count += 1
        except (FileNotFoundError, ValueError):
            invalid_count += 1

    reasons = []
    if not context.backend_config.enabled:
        reasons.append("openai_backend_disabled")
    budget = VisionBudgetGuard(context.backend_config).check(
        model=model,
        detail=context.detail,
        projected_calls=len(context.requests),
        projected_image_count=context.image_count,
        candidate_count=_budget_candidate_count(
            context.dataset,
            len(context.requests),
            context.backend_config,
        ),
        frame_count=max(
            (len(request.sampled_frame_references) for request in context.requests),
            default=0,
        ),
    )
    reasons = _unique_reasons(
        [*reasons, *context.limit_reasons, *context.runtime_reasons, *budget.reasons]
    )
    return {
        **_context_fields(context, backend=backend, model=model),
        "status": "dry_run",
        "dry_run": True,
        "mocked": False,
        "requests_built": built_count,
        "valid_requests": built_count,
        "invalid_requests": invalid_count,
        "schema_valid": bool(schema.get("additionalProperties") is False),
        "runtime_authorized": context.runtime_authorized,
        "runtime_block_reasons": _unique_reasons(context.runtime_reasons),
        "budget_allowed": bool(context.runtime_authorized) and budget.allowed and not reasons,
        "live_blocked_reasons": reasons,
        "semantic_rerank_enabled": bool(
            context.base_semantic_config.get("semantic_rerank_enabled", False)
        ),
        "production_selection_changed": bool(
            context.dataset.constraints.get("production_selection_changed", False)
        ),
        "paid_calls_performed": False,
        "live_vision_calls_performed": False,
    }


def _mocked_result(
    context: _EvaluationContext,
    *,
    backend: str,
    model: str,
    mocked: bool,
) -> dict[str, Any]:
    started = time.perf_counter()
    results = mocked_results_for_dataset(context.dataset, backend=backend, model=model)
    metrics = compute_evaluation_metrics(context.dataset, results)
    metrics["latency"] = round(time.perf_counter() - started, 6)
    return {
        **_context_fields(context, backend=backend, model=model),
        "status": "completed",
        "dry_run": False,
        "mocked": bool(mocked),
        "runtime_authorized": context.runtime_authorized,
        "budget_allowed": False,
        "metrics": metrics,
        "paid_calls_performed": False,
        "live_vision_calls_performed": False,
    }


def _missing_dataset_result(
    *,
    backend: str,
    model: str,
    dry_run: bool,
    mocked: bool,
    dataset_path: str | Path | None,
    error: FileNotFoundError,
) -> dict[str, Any]:
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
        "error": str(error),
        "paid_calls_performed": False,
        "live_vision_calls_performed": False,
    }


def _blocked_result(
    context: _EvaluationContext,
    *,
    backend: str,
    model: str,
    reasons: list[str],
    error: str = "",
) -> dict[str, Any]:
    result = {
        **_context_fields(context, backend=backend, model=model),
        "status": "blocked",
        "dry_run": False,
        "mocked": False,
        "valid_requests": 0,
        "invalid_requests": 0,
        "runtime_authorized": context.runtime_authorized,
        "runtime_block_reasons": _unique_reasons(context.runtime_reasons),
        "budget_allowed": False,
        "live_blocked_reasons": _unique_reasons(reasons),
        "paid_calls_performed": False,
        "live_vision_calls_performed": False,
    }
    if error:
        result["error"] = error
    return result


def _context_fields(
    context: _EvaluationContext,
    *,
    backend: str,
    model: str,
) -> dict[str, Any]:
    return {
        "backend": backend,
        "model": model,
        "dataset_path": context.dataset.dataset_path,
        "scenes": context.dataset.scene_count,
        "candidates": context.dataset.candidate_count,
        "dataset_cases": len(context.dataset.cases),
        "projected_calls": len(context.requests),
        "projected_image_count": context.image_count,
    }


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
    context: _EvaluationContext,
    model: str,
    client: Any | None,
    results_dir: Path,
) -> dict[str, Any]:
    if not context.runtime_authorized:
        return _blocked_result(
            context,
            backend="openai",
            model=model,
            reasons=context.runtime_reasons,
        )
    if _paid_execution_checkpoint_exists(results_dir):
        return _blocked_result(
            context,
            backend="openai",
            model=model,
            reasons=["existing_paid_execution_checkpoint"],
        )

    results_dir.mkdir(parents=True, exist_ok=True)
    backend, attempt_budget, error = _create_controlled_backend(
        semantic_config=context.semantic_config,
        client=client,
        max_attempts=context.backend_config.max_calls_cli,
    )
    if backend is None or attempt_budget is None:
        return _blocked_result(
            context,
            backend="openai",
            model=model,
            reasons=["openai_client_unavailable"],
            error=error,
        )

    state = _LiveExecutionState(
        attempt_budget=attempt_budget,
        original_maximum_retries=backend.config.maximum_retries,
    )
    _write_execution_checkpoint(results_dir, state=state, phase="running")
    _execute_live_candidates(
        context=context,
        backend=backend,
        state=state,
        model=model,
        results_dir=results_dir,
    )
    return _complete_live_execution(
        context=context,
        state=state,
        model=model,
        results_dir=results_dir,
    )


def _paid_execution_checkpoint_exists(results_dir: Path) -> bool:
    existing_checkpoint = results_dir / "LIVE_EVAL_EXECUTION_CHECKPOINT.json"
    if not existing_checkpoint.exists():
        return False
    try:
        existing = json.loads(existing_checkpoint.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    return bool(
        existing.get("paid_calls_performed")
        and int(existing.get("calls_succeeded") or 0) > 0
    )


def _create_controlled_backend(
    *,
    semantic_config: dict[str, Any],
    client: Any | None,
    max_attempts: int,
) -> tuple[
    OpenAISemanticVisualBackend | None,
    _ExternalAttemptBudget | None,
    str,
]:
    backend = OpenAISemanticVisualBackend(semantic_config)
    if client is None:
        try:
            client = backend._default_client()
        except Exception as exc:
            return None, None, str(exc)
    attempt_budget = _ExternalAttemptBudget(
        max_attempts=max_attempts,
        max_images=CONTROLLED_LIVE_IMAGES,
    )
    limited_client = _AttemptLimitedOpenAIClient(client, attempt_budget)
    backend.client = limited_client
    return backend, attempt_budget, ""


def _execute_live_candidates(
    *,
    context: _EvaluationContext,
    backend: OpenAISemanticVisualBackend,
    state: _LiveExecutionState,
    model: str,
    results_dir: Path,
) -> None:
    for case, request in zip(context.dataset.cases, context.requests, strict=True):
        if state.attempt_budget.remaining_attempts <= 0:
            state.stop_reasons.append("external_attempt_limit_reached")
            break
        backend.config.maximum_retries = max(
            0,
            min(
                state.original_maximum_retries,
                state.attempt_budget.remaining_attempts - 1,
            ),
        )
        before_usage = len(backend.usage_records)
        started = time.perf_counter()
        result = backend.analyse_candidate(request)
        duration = max(0.0, time.perf_counter() - started)
        state.logical_attempts += 1
        if result.status == "success":
            state.succeeded += 1
        else:
            state.failed += 1
        usage_record = (
            backend.usage_records[-1]
            if len(backend.usage_records) > before_usage
            else None
        )
        state.candidate_results.append(
            _candidate_live_result_row(
                case,
                request,
                result,
                usage_record=usage_record,
                duration=duration,
                model=model,
                detail=context.detail,
            )
        )
        if usage_record is not None:
            state.usage_rows.append(
                {
                    **usage_record.to_dict(),
                    "scene_id": request.scene_id,
                    "candidate_id": request.candidate_id,
                    "status": result.status,
                }
            )
        if result.error and result.error.code in {
            "authentication_error",
            "permission_denied",
        }:
            state.stop_reasons.append(result.error.code)
            _write_execution_checkpoint(results_dir, state=state, phase="running")
            break
        _write_execution_checkpoint(results_dir, state=state, phase="running")

    if (
        state.attempt_budget.remaining_attempts <= 0
        and state.logical_attempts < len(context.requests)
    ):
        state.stop_reasons.append("external_attempt_limit_reached")
    state.stop_reasons = _unique_reasons(state.stop_reasons)


def _complete_live_execution(
    *,
    context: _EvaluationContext,
    state: _LiveExecutionState,
    model: str,
    results_dir: Path,
) -> dict[str, Any]:
    metrics = _compute_live_metrics(context.dataset, state.candidate_results)
    summary = _live_summary(context=context, state=state, model=model)
    artifact_paths = _write_controlled_live_eval_artifacts(
        results_dir=results_dir,
        dataset=context.dataset,
        summary=summary,
        metrics=metrics,
        candidate_results=state.candidate_results,
        usage_rows=state.usage_rows,
    )
    ready_for_result_review = all(
        Path(path).exists() for path in artifact_paths.values() if path
    )
    _write_execution_checkpoint(
        results_dir,
        state=state,
        phase="completed",
        ready_for_result_review=ready_for_result_review,
    )
    return {
        **summary,
        "dry_run": False,
        "mocked": False,
        "valid_requests": len(context.requests),
        "invalid_requests": 0,
        "runtime_block_reasons": [],
        "live_blocked_reasons": [],
        "metrics": metrics,
        "candidate_results": state.candidate_results,
        "usage_records": state.usage_rows,
        "results_dir": _public_path(results_dir),
        "results_path": artifact_paths["results"],
        "usage_path": artifact_paths["usage"],
        "report_path": artifact_paths["report"],
        "comparison_path": artifact_paths["comparison"],
        "checkpoint_path": artifact_paths["checkpoint"],
    }


def _live_summary(
    *,
    context: _EvaluationContext,
    state: _LiveExecutionState,
    model: str,
) -> dict[str, Any]:
    return {
        **_context_fields(context, backend="openai", model=model),
        "status": (
            "completed"
            if state.logical_attempts == len(context.requests)
            else "partial"
        ),
        "detail": context.detail,
        "mode": "analyse_and_report",
        "calls_attempted": state.logical_attempts,
        "calls_succeeded": state.succeeded,
        "calls_failed": state.failed,
        "external_http_attempts": state.attempt_budget.attempts,
        "images_sent": state.attempt_budget.images_sent,
        "retries_observed": max(
            0,
            state.attempt_budget.attempts - state.logical_attempts,
        ),
        "total_input_tokens": sum(
            int(row.get("input_tokens") or 0) for row in state.candidate_results
        ),
        "total_output_tokens": sum(
            int(row.get("output_tokens") or 0) for row in state.candidate_results
        ),
        "total_cached_tokens": sum(
            int(row.get("cached_tokens") or 0) for row in state.candidate_results
        ),
        "total_calculated_cost_usd": state.total_cost,
        "budget_exceeded": state.total_cost > CONTROLLED_LIVE_BUDGET_CAP_USD,
        "semantic_rerank_enabled": False,
        "production_selection_changed": False,
        "stop_reasons": state.stop_reasons,
        "runtime_authorized": True,
        "budget_allowed": state.total_cost <= CONTROLLED_LIVE_BUDGET_CAP_USD,
        "live_vision_calls_performed": state.attempt_budget.attempts > 0,
        "paid_calls_performed": state.attempt_budget.attempts > 0,
    }


def _write_execution_checkpoint(
    results_dir: Path,
    *,
    state: _LiveExecutionState,
    phase: str,
    ready_for_result_review: bool = False,
) -> None:
    _write_json(
        results_dir / "LIVE_EVAL_EXECUTION_CHECKPOINT.json",
        {
            "phase": phase,
            "live_calls_performed": state.attempt_budget.attempts > 0,
            "paid_calls_performed": state.attempt_budget.attempts > 0,
            "calls_attempted": state.logical_attempts,
            "calls_succeeded": state.succeeded,
            "calls_failed": state.failed,
            "images_sent": state.attempt_budget.images_sent,
            "total_cost_usd": state.total_cost,
            "budget_exceeded": state.total_cost > CONTROLLED_LIVE_BUDGET_CAP_USD,
            "production_selection_changed": False,
            "semantic_rerank_enabled": False,
            "ready_for_result_review": bool(ready_for_result_review),
            "stop_reasons": state.stop_reasons,
        },
    )


def _openai_payload_image_count(kwargs: dict[str, Any]) -> int:
    count = 0
    for item in kwargs.get("input") or []:
        for content in (item or {}).get("content") or []:
            if isinstance(content, dict) and content.get("type") == "input_image":
                count += 1
    return count


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
    cfg = OpenAISemanticConfig.from_config(
        _effective_semantic_config(
            base_config,
            cli_config,
            runtime_authorized=False,
        )
    )
    reasons.extend(_persistent_default_reasons(base_config))
    reasons.extend(_dataset_authorization_reasons(dataset, projected_calls, projected_image_count))
    reasons.extend(_model_detail_authorization_reasons(dataset, cfg, model, detail))
    reasons.extend(_runtime_limit_authorization_reasons(cfg, projected_calls))

    expected_max_frames = _optional_int(
        dataset.constraints.get("maximum_frames_per_candidate")
    )
    if (
        max_frame_count != CONTROLLED_LIVE_MAX_FRAMES_PER_CANDIDATE
        or expected_max_frames
        not in (None, CONTROLLED_LIVE_MAX_FRAMES_PER_CANDIDATE)
    ):
        reasons.append("runtime_frame_limit_mismatch")
    if not os.getenv("OPENAI_API_KEY"):
        reasons.append("runtime_openai_key_required")
    if bool(dataset.constraints.get("semantic_rerank_enabled", False)):
        reasons.append("runtime_semantic_rerank_enabled")
    if bool(dataset.constraints.get("production_selection_changed", False)):
        reasons.append("runtime_production_selection_changed")
    return _unique_reasons(reasons)


def _dataset_authorization_reasons(
    dataset: EvaluationDataset,
    projected_calls: int,
    projected_image_count: int,
) -> list[str]:
    reasons: list[str] = []
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
    if _optional_int(constraints.get("scenes")) not in (
        None,
        CONTROLLED_LIVE_SCENES,
    ):
        reasons.append("runtime_dataset_counts_mismatch")
    if _optional_int(constraints.get("candidates_per_scene")) not in (
        None,
        CONTROLLED_LIVE_CANDIDATES // CONTROLLED_LIVE_SCENES,
    ):
        reasons.append("runtime_dataset_counts_mismatch")
    if _optional_int(constraints.get("maximum_future_api_calls")) not in (
        None,
        CONTROLLED_LIVE_CALLS,
    ):
        reasons.append("runtime_dataset_counts_mismatch")
    if _optional_int(constraints.get("maximum_future_images")) not in (
        None,
        CONTROLLED_LIVE_IMAGES,
    ):
        reasons.append("runtime_dataset_counts_mismatch")
    return reasons


def _model_detail_authorization_reasons(
    dataset: EvaluationDataset,
    cfg: OpenAISemanticConfig,
    model: str,
    detail: str,
) -> list[str]:
    reasons: list[str] = []
    constraints = dataset.constraints
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
    return reasons


def _runtime_limit_authorization_reasons(
    cfg: OpenAISemanticConfig,
    projected_calls: int,
) -> list[str]:
    reasons: list[str] = []
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
    return reasons


def _effective_semantic_config(
    base_config: dict[str, Any],
    cli_config: dict[str, Any],
    *,
    runtime_authorized: bool,
) -> dict[str, Any]:
    effective = dict(base_config or {})
    openai = dict(effective.get("openai") or {})
    effective["openai"] = openai
    effective["allow_paid_vision_cli"] = bool(
        cli_config.get("allow_paid_vision_cli", False)
    )
    effective["budget_usd_cli"] = max(
        0.0,
        float(cli_config.get("budget_usd_cli") or 0.0),
    )
    effective["max_calls_cli"] = max(
        0,
        int(cli_config.get("max_calls_cli") or 0),
    )
    effective["confirm_paid_vision"] = str(
        cli_config.get("confirm_paid_vision") or ""
    )
    if runtime_authorized:
        runtime_budget = min(
            effective["budget_usd_cli"],
            CONTROLLED_LIVE_BUDGET_CAP_USD,
        )
        runtime_max_calls = min(
            effective["max_calls_cli"],
            CONTROLLED_LIVE_MAX_CALL_CAP,
        )
        openai.update(
            {
                "enabled": True,
                "primary_model": CONTROLLED_LIVE_MODEL,
                "initial_detail": CONTROLLED_LIVE_DETAIL,
                "reasoning_effort": "low",
                "allow_paid_vision": True,
                "maximum_budget_usd": runtime_budget,
                "maximum_calls_per_project": runtime_max_calls,
                "maximum_candidates_per_scene": (
                    CONTROLLED_LIVE_CANDIDATES // CONTROLLED_LIVE_SCENES
                ),
                "maximum_frames_per_candidate": (
                    CONTROLLED_LIVE_MAX_FRAMES_PER_CANDIDATE
                ),
                "input_cost_per_1k_tokens_usd": (
                    CONTROLLED_LIVE_INPUT_COST_PER_1K_TOKENS_USD
                ),
                "output_cost_per_1k_tokens_usd": (
                    CONTROLLED_LIVE_OUTPUT_COST_PER_1K_TOKENS_USD
                ),
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
    if (
        _optional_float(
            openai.get(
                "maximum_budget_usd",
                raw.get("maximum_budget_usd", 0.0),
            )
        )
        != 0.0
    ):
        reasons.append("persistent_budget_nonzero")
    if _optional_int(
        openai.get(
            "maximum_calls_per_project",
            raw.get("maximum_calls_per_project", 0),
        )
    ) not in (None, 0):
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
    expected_candidates_per_scene = _optional_int(
        constraints.get("candidates_per_scene")
    )
    expected_calls = _optional_int(constraints.get("maximum_future_api_calls"))
    expected_images = _optional_int(constraints.get("maximum_future_images"))
    if expected_scenes is not None and expected_scenes != dataset.scene_count:
        reasons.append("dataset_scenes_mismatch")
    if (
        expected_candidates_per_scene is not None
        and expected_candidates_per_scene * max(1, dataset.scene_count)
        != dataset.candidate_count
    ):
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


def _budget_candidate_count(
    dataset: EvaluationDataset,
    request_count: int,
    cfg: OpenAISemanticConfig,
) -> int:
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


def _unique_reasons(values: list[str]) -> list[str]:
    return [item for item in dict.fromkeys(values) if item]


def _load_semantic_config() -> dict[str, Any]:
    path = repository_path("config", "semantic_visual.json")
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


__all__ = ["run_semantic_visual_evaluation"]
