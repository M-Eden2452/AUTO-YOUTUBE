from __future__ import annotations

import base64
import dataclasses
import json
import mimetypes
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from .semantic_visual_backend import SemanticBackendCapabilities, SemanticBackendHealth
from .semantic_visual_models import (
    AggregateSemanticScores,
    FrameSemanticObservation,
    SemanticEvidence,
    SemanticFrameReference,
    SemanticVisualRequest,
    SemanticVisualResult,
    TermSemanticCheckResult,
    apply_semantic_aggregation_rules,
    fallback_semantic_result,
)


OPENAI_BACKEND_VERSION = "openai.responses.semantic.v1"
OPENAI_PROMPT_TEMPLATE_VERSION = "openai.semantic_visual_prompt.v1"
OPENAI_ALLOWED_DETAILS = {"low", "high"}
LIVE_CONFIRMATION_PHRASE = "LIVE_VISION_APPROVED"
DEFAULT_OPENAI_MODELS = ("gpt-5.6-terra", "gpt-5.6-luna")


@dataclass
class OpenAISemanticConfig:
    enabled: bool = False
    primary_model: str = "gpt-5.6-terra"
    comparison_model: str = "gpt-5.6-luna"
    initial_detail: str = "low"
    escalation_detail: str = "high"
    allow_auto_detail: bool = False
    allow_original_detail: bool = False
    reasoning_effort: str = "low"
    timeout_sec: float = 60.0
    maximum_retries: int = 2
    maximum_candidates_per_scene: int = 3
    maximum_frames_per_candidate: int = 3
    maximum_calls_per_project: int = 0
    maximum_budget_usd: float = 0.0
    allow_paid_vision: bool = False
    allow_paid_vision_cli: bool = False
    budget_usd_cli: float = 0.0
    max_calls_cli: int = 0
    confirm_paid_vision: str = ""
    model_allowlist: set[str] = field(default_factory=set)
    estimated_cost_per_call_usd: float = 0.0
    estimated_cost_per_image_usd: float = 0.0
    input_cost_per_1k_tokens_usd: float = 0.0
    output_cost_per_1k_tokens_usd: float = 0.0
    minimum_confidence_for_escalation: float = 0.65
    close_score_gap_for_escalation: float = 0.05

    @classmethod
    def from_config(cls, config: dict[str, Any] | None) -> "OpenAISemanticConfig":
        raw = dict(config or {})
        openai = dict(raw.get("openai") or {})
        allowlist = openai.get("model_allowlist") or raw.get("openai_model_allowlist") or []
        primary = str(openai.get("primary_model") or "gpt-5.6-terra")
        comparison = str(openai.get("comparison_model") or "gpt-5.6-luna")
        model_allowlist = {primary, comparison}
        model_allowlist.update(str(item) for item in allowlist if str(item))
        return cls(
            enabled=bool(openai.get("enabled", False)),
            primary_model=primary,
            comparison_model=comparison,
            initial_detail=str(openai.get("initial_detail") or "low"),
            escalation_detail=str(openai.get("escalation_detail") or "high"),
            allow_auto_detail=bool(openai.get("allow_auto_detail", False)),
            allow_original_detail=bool(openai.get("allow_original_detail", False)),
            reasoning_effort=str(openai.get("reasoning_effort") or "low"),
            timeout_sec=float(openai.get("timeout_sec") or 60.0),
            maximum_retries=max(0, int(openai.get("maximum_retries", 2))),
            maximum_candidates_per_scene=max(0, int(openai.get("maximum_candidates_per_scene") or 3)),
            maximum_frames_per_candidate=max(0, int(openai.get("maximum_frames_per_candidate") or 3)),
            maximum_calls_per_project=max(0, int(_config_value(openai, raw, "maximum_calls_per_project", 0))),
            maximum_budget_usd=max(0.0, float(_config_value(openai, raw, "maximum_budget_usd", 0.0))),
            allow_paid_vision=bool(openai.get("allow_paid_vision", raw.get("allow_paid_vision", False))),
            allow_paid_vision_cli=bool(raw.get("allow_paid_vision_cli", False)),
            budget_usd_cli=max(0.0, float(raw.get("budget_usd_cli") or 0.0)),
            max_calls_cli=max(0, int(raw.get("max_calls_cli") or 0)),
            confirm_paid_vision=str(raw.get("confirm_paid_vision") or ""),
            model_allowlist=model_allowlist,
            estimated_cost_per_call_usd=max(0.0, float(openai.get("estimated_cost_per_call_usd") or 0.0)),
            estimated_cost_per_image_usd=max(0.0, float(openai.get("estimated_cost_per_image_usd") or 0.0)),
            input_cost_per_1k_tokens_usd=max(0.0, float(openai.get("input_cost_per_1k_tokens_usd") or 0.0)),
            output_cost_per_1k_tokens_usd=max(0.0, float(openai.get("output_cost_per_1k_tokens_usd") or 0.0)),
            minimum_confidence_for_escalation=float(openai.get("minimum_confidence_for_escalation") or 0.65),
            close_score_gap_for_escalation=float(openai.get("close_score_gap_for_escalation") or 0.05),
        )

    @property
    def allowed_details(self) -> set[str]:
        details = {"low", "high"}
        if self.allow_auto_detail:
            details.add("auto")
        if self.allow_original_detail:
            details.add("original")
        return details & OPENAI_ALLOWED_DETAILS

    def detail_policy_summary(self) -> dict[str, Any]:
        return {
            "initial_detail": self.initial_detail,
            "escalation_detail": self.escalation_detail,
            "allowed_details": sorted(self.allowed_details),
            "allow_auto_detail": self.allow_auto_detail,
            "allow_original_detail": self.allow_original_detail,
        }


@dataclass
class DetailEscalationDecision:
    should_escalate: bool
    detail: str
    reasons: list[str] = field(default_factory=list)


class OpenAIDetailPolicy:
    def __init__(self, config: OpenAISemanticConfig) -> None:
        self.config = config

    def initial_detail(self) -> str:
        return "low" if self.config.initial_detail not in OPENAI_ALLOWED_DETAILS else self.config.initial_detail

    def escalation_decision(
        self,
        *,
        low_confidence: float,
        top_score_gap: float,
        strict_scene: bool,
        must_have_uncertain: bool,
    ) -> DetailEscalationDecision:
        reasons: list[str] = []
        if low_confidence < self.config.minimum_confidence_for_escalation:
            reasons.append("confidence_below_threshold")
        if top_score_gap <= self.config.close_score_gap_for_escalation:
            reasons.append("top_candidates_close")
        if strict_scene:
            reasons.append("strict_scene_requires_exact_entity")
        if must_have_uncertain:
            reasons.append("must_have_uncertain")
        detail = "high" if self.config.escalation_detail == "high" else "low"
        return DetailEscalationDecision(should_escalate=bool(reasons) and detail == "high", detail=detail, reasons=reasons)


@dataclass
class BudgetDecision:
    allowed: bool
    reasons: list[str]
    projected_calls: int
    projected_image_count: int
    projected_budget_usd: float

    @property
    def message(self) -> str:
        return ",".join(self.reasons)


class VisionBudgetGuard:
    def __init__(self, config: OpenAISemanticConfig) -> None:
        self.config = config

    def check(
        self,
        *,
        model: str,
        detail: str,
        projected_calls: int,
        projected_image_count: int,
        candidate_count: int,
        frame_count: int,
        project_usage_calls: int = 0,
        project_usage_budget_usd: float = 0.0,
    ) -> BudgetDecision:
        reasons: list[str] = []
        if not self.config.allow_paid_vision:
            reasons.append("allow_paid_vision_required")
        if not self.config.allow_paid_vision_cli:
            reasons.append("allow_paid_vision_cli_required")
        if self.config.maximum_budget_usd <= 0:
            reasons.append("maximum_budget_usd_required")
        if self.config.budget_usd_cli <= 0:
            reasons.append("budget_usd_cli_required")
        if self.config.maximum_calls_per_project <= 0:
            reasons.append("maximum_calls_per_project_required")
        if self.config.max_calls_cli <= 0:
            reasons.append("max_calls_cli_required")
        if self.config.confirm_paid_vision != LIVE_CONFIRMATION_PHRASE:
            reasons.append("confirm_paid_vision_required")
        if model not in self.config.model_allowlist:
            reasons.append("model_not_allowlisted")
        if detail not in OPENAI_ALLOWED_DETAILS:
            reasons.append("detail_not_allowed")
        if candidate_count > self.config.maximum_candidates_per_scene:
            reasons.append("maximum_candidates_per_scene_exceeded")
        if frame_count > self.config.maximum_frames_per_candidate:
            reasons.append("maximum_frames_per_candidate_exceeded")

        projected_calls = max(0, int(projected_calls))
        projected_image_count = max(0, int(projected_image_count))
        projected_budget = self.projected_budget(projected_calls=projected_calls, projected_image_count=projected_image_count)
        effective_call_limit = min(_positive_or_large(self.config.maximum_calls_per_project), _positive_or_large(self.config.max_calls_cli))
        effective_budget = min(_positive_or_large_float(self.config.maximum_budget_usd), _positive_or_large_float(self.config.budget_usd_cli))
        if project_usage_calls + projected_calls > effective_call_limit:
            reasons.append("maximum_calls_per_project_exceeded")
        if project_usage_budget_usd + projected_budget > effective_budget:
            reasons.append("projected_budget_exceeded")
        return BudgetDecision(
            allowed=not reasons,
            reasons=list(dict.fromkeys(reasons)),
            projected_calls=projected_calls,
            projected_image_count=projected_image_count,
            projected_budget_usd=projected_budget,
        )

    def projected_budget(self, *, projected_calls: int, projected_image_count: int) -> float:
        return round(
            projected_calls * self.config.estimated_cost_per_call_usd
            + projected_image_count * self.config.estimated_cost_per_image_usd,
            6,
        )


@dataclass
class BuiltOpenAIRequest:
    payload: dict[str, Any]
    diagnostics: dict[str, Any]
    image_count: int
    detail_levels: list[str]


class OpenAIRequestBuilder:
    def __init__(self, config: OpenAISemanticConfig) -> None:
        self.config = config

    def build(self, request: SemanticVisualRequest, *, model: str, detail: str) -> BuiltOpenAIRequest:
        if detail not in OPENAI_ALLOWED_DETAILS:
            raise ValueError(f"OpenAI image detail must be one of {sorted(OPENAI_ALLOWED_DETAILS)}")
        frames = request.sampled_frame_references[: max(0, min(int(request.maximum_frames or 0), self.config.maximum_frames_per_candidate))]
        public_request = request.to_public_dict()
        public_request["sampled_frame_references"] = [frame.to_public_dict() for frame in frames]
        context = _semantic_context_for_model(public_request)
        content: list[dict[str, Any]] = [
            {
                "type": "input_text",
                "text": json.dumps(context, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
            }
        ]
        detail_levels: list[str] = []
        for frame in frames:
            content.append(
                {
                    "type": "input_text",
                    "text": _frame_marker_text(frame),
                }
            )
            content.append(
                {
                    "type": "input_image",
                    "image_url": _frame_to_data_url(frame),
                    "detail": detail,
                }
            )
            detail_levels.append(detail)
        payload = {
            "model": model,
            "instructions": _system_instruction(),
            "reasoning": {"effort": self.config.reasoning_effort},
            "input": [{"role": "user", "content": content}],
            "text": {"format": semantic_visual_result_text_format_schema()},
        }
        diagnostics = {
            "backend": "openai",
            "model": model,
            "prompt_template_version": OPENAI_PROMPT_TEMPLATE_VERSION,
            "image_count": len(frames),
            "detail_levels": detail_levels,
            "frame_references": [frame.to_public_dict() for frame in frames],
            "request_context": context,
            "schema_name": "semantic_visual_result",
        }
        return BuiltOpenAIRequest(payload=payload, diagnostics=diagnostics, image_count=len(frames), detail_levels=detail_levels)


@dataclass
class OpenAIUsageRecord:
    model: str
    image_count: int
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    estimated_cost_usd: float = 0.0
    actual_calculated_cost_usd: float = 0.0
    request_id: str = ""
    duration_sec: float = 0.0
    detail_levels: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


class OpenAISemanticVisualBackend:
    name = "openai"

    def __init__(
        self,
        config: dict[str, Any] | None,
        *,
        client: Any | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.perf_counter,
    ) -> None:
        self.raw_config = dict(config or {})
        self.config = OpenAISemanticConfig.from_config(self.raw_config)
        self.client = client
        self.sleep = sleep
        self.clock = clock
        self.usage_records: list[OpenAIUsageRecord] = []
        self.last_diagnostics: dict[str, Any] = {}

    def capabilities(self) -> SemanticBackendCapabilities:
        return SemanticBackendCapabilities(
            backend=self.name,
            model=self.config.primary_model,
            backend_version=OPENAI_BACKEND_VERSION,
            supports_images=True,
            supports_video_frames=True,
            supports_batch=False,
            maximum_frames=self.config.maximum_frames_per_candidate,
            batch_limit=1,
            paid_backend=True,
            estimated_cost_per_call_usd=self.config.estimated_cost_per_call_usd,
        )

    def health_check(self) -> SemanticBackendHealth:
        if not self.config.enabled:
            return SemanticBackendHealth(backend=self.name, configured=False, status="disabled", message="OpenAI semantic backend disabled")
        if not os.getenv("OPENAI_API_KEY") and self.client is None:
            return SemanticBackendHealth(backend=self.name, configured=False, status="configuration_error", message="OPENAI_API_KEY not configured")
        return SemanticBackendHealth(backend=self.name, configured=True, status="not_checked", message="live status not checked")

    def analyse_candidate(self, request: SemanticVisualRequest) -> SemanticVisualResult:
        model = str(request.backend_options.get("model") or self.config.primary_model)
        detail = OpenAIDetailPolicy(self.config).initial_detail()
        if not self.config.enabled:
            return self._fallback(request, "configuration_error", "openai_backend_disabled", "OpenAI semantic backend is disabled.")
        frame_count = min(len(request.sampled_frame_references), self.config.maximum_frames_per_candidate)
        budget = VisionBudgetGuard(self.config).check(
            model=model,
            detail=detail,
            projected_calls=1,
            projected_image_count=frame_count,
            candidate_count=1,
            frame_count=frame_count,
        )
        if not budget.allowed:
            return self._fallback(request, "configuration_error", "budget_violation", budget.message)
        try:
            built = OpenAIRequestBuilder(self.config).build(request, model=model, detail=detail)
        except (FileNotFoundError, ValueError) as exc:
            return self._fallback(request, "configuration_error", "request_build_failed", str(exc))
        self.last_diagnostics = built.diagnostics
        client = self.client
        if client is None:
            try:
                client = self._default_client()
            except Exception as exc:
                return self._fallback(request, "configuration_error", "openai_sdk_unavailable", str(exc))
        started = self.clock()
        attempts = 0
        while True:
            try:
                response = client.responses.create(**built.payload, timeout=self.config.timeout_sec)
                duration = max(0.0, self.clock() - started)
                result = adapt_openai_structured_result(response, request, model=model, backend_version=OPENAI_BACKEND_VERSION)
                result = apply_semantic_aggregation_rules(result, request)
                result.assert_valid()
                self.usage_records.append(self._usage_record(response, model=model, built=built, duration=duration, projected_budget=budget.projected_budget_usd))
                return result
            except Exception as exc:
                classification = _classify_openai_exception(exc)
                if classification["retryable"] and attempts < self.config.maximum_retries:
                    attempts += 1
                    self.sleep(float(classification.get("retry_after") or 0.0))
                    continue
                return self._fallback(
                    request,
                    str(classification["status"]),
                    str(classification["code"]),
                    str(classification["message"]),
                    retryable=bool(classification["retryable"]),
                )

    def _usage_record(
        self,
        response: Any,
        *,
        model: str,
        built: BuiltOpenAIRequest,
        duration: float,
        projected_budget: float,
    ) -> OpenAIUsageRecord:
        usage = _as_dict(getattr(response, "usage", None))
        input_tokens = int(usage.get("input_tokens") or usage.get("prompt_tokens") or 0)
        output_tokens = int(usage.get("output_tokens") or usage.get("completion_tokens") or 0)
        details = _as_dict(usage.get("input_tokens_details") or usage.get("prompt_tokens_details"))
        cached_tokens = int(details.get("cached_tokens") or 0)
        actual_cost = round(
            (input_tokens / 1000.0) * self.config.input_cost_per_1k_tokens_usd
            + (output_tokens / 1000.0) * self.config.output_cost_per_1k_tokens_usd,
            6,
        )
        return OpenAIUsageRecord(
            model=model,
            image_count=built.image_count,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_tokens=cached_tokens,
            estimated_cost_usd=projected_budget,
            actual_calculated_cost_usd=actual_cost,
            request_id=_request_id_from_response(response),
            duration_sec=duration,
            detail_levels=built.detail_levels,
        )

    def _default_client(self) -> Any:
        from openai import OpenAI  # type: ignore

        return OpenAI(api_key=os.getenv("OPENAI_API_KEY"), timeout=self.config.timeout_sec, max_retries=0)

    def _fallback(self, request: SemanticVisualRequest, status: str, code: str, message: str, *, retryable: bool = False) -> SemanticVisualResult:
        return fallback_semantic_result(
            backend=self.name,
            model=str(request.backend_options.get("model") or self.config.primary_model),
            backend_version=OPENAI_BACKEND_VERSION,
            request_version=request.request_version,
            status=status,
            error_code=code,
            message=message,
            retryable=retryable,
        )


def adapt_openai_structured_result(
    response: Any,
    request: SemanticVisualRequest,
    *,
    model: str,
    backend_version: str = OPENAI_BACKEND_VERSION,
) -> SemanticVisualResult:
    if _response_is_refusal(response):
        return fallback_semantic_result(
            backend="openai",
            model=model,
            backend_version=backend_version,
            request_version=request.request_version,
            status="refused",
            error_code="refusal",
            message="OpenAI response contained a refusal.",
        )
    status = str(getattr(response, "status", "") or "")
    if status == "incomplete" or getattr(response, "incomplete_details", None):
        return fallback_semantic_result(
            backend="openai",
            model=model,
            backend_version=backend_version,
            request_version=request.request_version,
            status="incomplete",
            error_code="incomplete_response",
            message="OpenAI response was incomplete.",
            retryable=True,
        )
    payload = _structured_payload_from_response(response)
    if payload is None:
        return fallback_semantic_result(
            backend="openai",
            model=model,
            backend_version=backend_version,
            request_version=request.request_version,
            status="invalid_response",
            error_code="empty_output",
            message="OpenAI response contained no structured output.",
        )
    try:
        result = SemanticVisualResult.from_dict(payload)
        result.backend = "openai"
        result.model = model
        result.backend_version = backend_version
        result.request_version = request.request_version
        if result.status == "completed":
            result.status = "success"
        result.raw_response_reference = _request_id_from_response(response)
        result.assert_valid()
        return result
    except Exception as exc:
        return fallback_semantic_result(
            backend="openai",
            model=model,
            backend_version=backend_version,
            request_version=request.request_version,
            status="invalid_response",
            error_code="invalid_schema",
            message=str(exc),
        )


def semantic_visual_result_text_format_schema() -> dict[str, Any]:
    return {
        "type": "json_schema",
        "name": "semantic_visual_result",
        "strict": True,
        "schema": semantic_visual_result_json_schema(),
    }


def semantic_visual_result_json_schema() -> dict[str, Any]:
    score = {"type": "number", "minimum": 0.0, "maximum": 1.0}
    string_array = {"type": "array", "items": {"type": "string"}}
    integer_array = {"type": "array", "items": {"type": "integer"}}
    aggregate = _object_schema(
        {
            "subject_match": score,
            "action_match": score,
            "environment_match": score,
            "location_match": score,
            "exact_entity_match": score,
            "must_have_match": score,
            "negative_element_safety": score,
            "shot_type_match": score,
            "mood_match": score,
            "temporal_match": score,
            "overall_semantic_match": score,
        }
    )
    term = _object_schema(
        {
            "term": {"type": "string"},
            "present": {"type": "boolean"},
            "confidence": score,
            "evidence": {"type": "string"},
            "frame_indices": integer_array,
        }
    )
    observation = _object_schema(
        {
            "frame_index": {"type": "integer"},
            "subject_observations": string_array,
            "action_observations": string_array,
            "environment_observations": string_array,
            "location_observations": string_array,
            "shot_type_observations": string_array,
            "temporal_observations": string_array,
            "visible_text_or_logo_risk": {"type": "boolean"},
            "unwanted_element_observations": string_array,
            "confidence": score,
            "short_evidence_summary": {"type": "string"},
        }
    )
    evidence = _object_schema(
        {
            "kind": {"type": "string"},
            "summary": {"type": "string"},
            "frame_indices": integer_array,
            "confidence": score,
        }
    )
    error = _object_schema(
        {
            "code": {"type": "string"},
            "message": {"type": "string"},
            "retryable": {"type": "boolean"},
        }
    )
    return _object_schema(
        {
            "result_version": {"type": "string"},
            "backend": {"type": "string"},
            "model": {"type": "string"},
            "backend_version": {"type": "string"},
            "request_version": {"type": "string"},
            "analysed_at": {"type": "string"},
            "status": {"type": "string"},
            "confidence": score,
            "frames_analysed": {"type": "integer", "minimum": 0},
            "frame_observations": {"type": "array", "items": observation},
            "aggregate_scores": aggregate,
            "must_have_results": {"type": "array", "items": term},
            "negative_element_results": {"type": "array", "items": term},
            "mismatch_reasons": string_array,
            "review_required_reasons": string_array,
            "evidence": {"type": "array", "items": evidence},
            "semantic_score": score,
            "hard_reject": {"type": "boolean"},
            "cache_key": {"type": "string"},
            "raw_response_reference": {"type": "string"},
            "error": {"anyOf": [error, {"type": "null"}]},
        }
    )


def sanitized_payload_for_diagnostics(payload: dict[str, Any]) -> dict[str, Any]:
    def clean(value: Any) -> Any:
        if isinstance(value, dict):
            return {str(key): clean(item) for key, item in value.items()}
        if isinstance(value, list):
            return [clean(item) for item in value]
        if isinstance(value, str) and value.startswith("data:image/"):
            return "[redacted_image_data_url]"
        return value

    return clean(payload)


def openai_backend_diagnostics(config: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = OpenAISemanticConfig.from_config(config or _load_default_semantic_config())
    return {
        "configured": True,
        "key_configured": bool(os.getenv("OPENAI_API_KEY")),
        "enabled": cfg.enabled,
        "primary_model": cfg.primary_model,
        "comparison_model": cfg.comparison_model,
        "detail_policy": cfg.detail_policy_summary(),
        "paid_calls_allowed": cfg.allow_paid_vision,
        "budget_usd": cfg.maximum_budget_usd,
        "call_limit": cfg.maximum_calls_per_project,
        "live_status": "not_checked",
    }


def _load_default_semantic_config() -> dict[str, Any]:
    path = Path("config/semantic_visual.json")
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _system_instruction() -> str:
    return (
        "You are a semantic visual analysis backend. Evaluate only visible content in the provided sampled frames. "
        "Do not infer hidden events, unseen locations, identities, private attributes, licenses, or provenance. "
        "Do not identify people. Report uncertainty explicitly. Return only strict JSON matching the supplied schema."
    )


def _semantic_context_for_model(public_request: dict[str, Any]) -> dict[str, Any]:
    return {
        "task": "semantic_visual_candidate_analysis",
        "scene_requirements": public_request.get("requirements", {}),
        "semantic_strictness": (public_request.get("requirements") or {}).get("semantic_strictness", "balanced"),
        "candidate_metadata": public_request.get("candidate_metadata", {}),
        "sampled_frames": [
            {
                "frame_index": frame.get("frame_index"),
                "timestamp_sec": frame.get("actual_timestamp_sec"),
                "requested_timestamp_sec": frame.get("requested_timestamp_sec"),
                "is_poster_frame": bool(frame.get("is_poster_frame", False)),
                "sha256": frame.get("sha256", ""),
                "perceptual_hash": frame.get("perceptual_hash", ""),
                "width": frame.get("width", 0),
                "height": frame.get("height", 0),
                "extraction_status": frame.get("extraction_status", ""),
                "technical_metrics": frame.get("technical_metrics", {}),
            }
            for frame in public_request.get("sampled_frame_references", [])
        ],
        "technical_context": public_request.get("technical_metrics_summary", {}),
        "analysis_rules": {
            "evaluate_only_visible_data": True,
            "do_not_guess_unseen_content": True,
            "report_uncertainty": True,
            "do_not_identify_people": True,
            "do_not_use_absolute_paths_or_provenance": True,
        },
    }


def _frame_marker_text(frame: SemanticFrameReference) -> str:
    return (
        f"Frame index={frame.frame_index}; timestamp={frame.actual_timestamp_sec:.3f}s; "
        f"requested_timestamp={frame.requested_timestamp_sec:.3f}s; poster_frame={bool(frame.is_poster_frame)}. "
        "Use this image only for visible evidence."
    )


def _frame_to_data_url(frame: SemanticFrameReference) -> str:
    path = Path(frame.private_local_path)
    if not frame.private_local_path or not path.exists() or not path.is_file():
        raise FileNotFoundError(f"sampled frame missing for frame_index={frame.frame_index}")
    mime_type = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def _structured_payload_from_response(response: Any) -> dict[str, Any] | None:
    parsed = getattr(response, "output_parsed", None)
    if isinstance(parsed, dict):
        return parsed
    if dataclasses.is_dataclass(parsed):
        return dataclasses.asdict(parsed)
    text = str(getattr(response, "output_text", "") or "").strip()
    if text:
        try:
            loaded = json.loads(text)
            return loaded if isinstance(loaded, dict) else None
        except json.JSONDecodeError:
            return None
    for item in _as_list_any(getattr(response, "output", [])):
        for content in _as_list_any(_as_dict(item).get("content")):
            content_data = _as_dict(content)
            if isinstance(content_data.get("parsed"), dict):
                return content_data["parsed"]
            text_value = content_data.get("text")
            if isinstance(text_value, str) and text_value.strip():
                try:
                    loaded = json.loads(text_value)
                    return loaded if isinstance(loaded, dict) else None
                except json.JSONDecodeError:
                    return None
    return None


def _response_is_refusal(response: Any) -> bool:
    if getattr(response, "refusal", None):
        return True
    for item in _as_list_any(getattr(response, "output", [])):
        for content in _as_list_any(_as_dict(item).get("content")):
            content_data = _as_dict(content)
            if content_data.get("type") == "refusal" or content_data.get("refusal"):
                return True
    return False


def _request_id_from_response(response: Any) -> str:
    for attr in ("_request_id", "request_id", "id"):
        value = getattr(response, attr, "")
        if value:
            return str(value)
    headers = _as_dict(getattr(response, "headers", None))
    return str(headers.get("x-request-id") or "")


def _classify_openai_exception(exc: Exception) -> dict[str, Any]:
    status_code = _status_code(exc)
    retry_after = _retry_after(exc)
    message = str(exc)
    if isinstance(exc, TimeoutError):
        return {"status": "timeout", "code": "timeout", "message": message, "retryable": True, "retry_after": retry_after}
    if isinstance(exc, ConnectionError):
        return {"status": "connection_error", "code": "connection_error", "message": message, "retryable": True, "retry_after": retry_after}
    if status_code == 429:
        return {"status": "rate_limited", "code": "rate_limited", "message": message, "retryable": True, "retry_after": retry_after}
    if status_code in {401}:
        return {"status": "authentication_error", "code": "authentication_error", "message": message, "retryable": False, "retry_after": 0.0}
    if status_code in {403}:
        return {"status": "permission_denied", "code": "permission_denied", "message": message, "retryable": False, "retry_after": 0.0}
    if status_code in {400}:
        return {"status": "invalid_request", "code": "bad_request", "message": message, "retryable": False, "retry_after": 0.0}
    if status_code >= 500:
        return {"status": "server_error", "code": "server_error", "message": message, "retryable": True, "retry_after": retry_after}
    return {"status": "unexpected_error", "code": "unexpected_error", "message": message, "retryable": False, "retry_after": 0.0}


def _status_code(exc: Exception) -> int:
    value = getattr(exc, "status_code", None)
    if value is None and getattr(exc, "response", None) is not None:
        value = getattr(exc.response, "status_code", None)
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _retry_after(exc: Exception) -> float:
    headers = _as_dict(getattr(exc, "headers", None))
    if not headers and getattr(exc, "response", None) is not None:
        headers = _as_dict(getattr(exc.response, "headers", None))
    value = headers.get("retry-after") or headers.get("Retry-After") or 0.0
    try:
        return max(0.0, float(value))
    except (TypeError, ValueError):
        return 0.0


def _object_schema(properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


def _config_value(openai: dict[str, Any], raw: dict[str, Any], key: str, default: Any) -> Any:
    if key in openai:
        return openai[key]
    if key in raw:
        return raw[key]
    return default


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if dataclasses.is_dataclass(value):
        return dataclasses.asdict(value)
    if value is None:
        return {}
    data: dict[str, Any] = {}
    for key in dir(value):
        if key.startswith("_"):
            continue
        try:
            item = getattr(value, key)
        except Exception:
            continue
        if not callable(item):
            data[key] = item
    return data


def _as_list_any(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _positive_or_large(value: int) -> int:
    return value if value > 0 else 10**12


def _positive_or_large_float(value: float) -> float:
    return value if value > 0 else 10**12


def mocked_openai_semantic_payload(
    *,
    model: str,
    case_id: str,
    category: str,
    strictness: str,
    frame_count: int,
) -> dict[str, Any]:
    subject = 0.9
    action = 0.9
    environment = 0.9
    location = 0.9
    exact = 0.9
    must = 0.92
    negative_safety = 0.96
    confidence = 0.9
    hard_reject = False
    mismatch: list[str] = []
    review: list[str] = []
    must_present = True
    negative_present = False
    negative_conf = 0.91
    if category == "wrong_subject":
        subject = 0.2
        exact = 0.2
        mismatch.append("subject_mismatch")
    elif category == "wrong_action":
        action = 0.22
        mismatch.append("action_mismatch")
    elif category == "wrong_location":
        location = 0.18
        mismatch.append("location_mismatch")
    elif category == "exact_entity_mismatch":
        exact = 0.16
        mismatch.append("exact_entity_mismatch")
    elif category == "missing_must_have":
        must = 0.25
        must_present = False
        mismatch.append("must_have_missing:ocean")
    elif category == "negative_element_present":
        negative_safety = 0.05
        negative_present = True
        negative_conf = 0.96
        hard_reject = True
        mismatch.append("negative_element_detected:desert")
    elif category == "one_misleading_frame":
        negative_safety = 0.72
        negative_present = True
        negative_conf = 0.58
        review.append("one_misleading_frame")
    elif category == "poster_only_video":
        action = 0.65
        review.append("limited_temporal_evidence")
    elif category == "low_confidence":
        confidence = 0.45
        subject = min(subject, 0.55)
        action = min(action, 0.55)
        review.append("low_confidence")
    aggregate = AggregateSemanticScores(
        subject_match=subject,
        action_match=action,
        environment_match=environment,
        location_match=location,
        exact_entity_match=exact,
        must_have_match=must,
        negative_element_safety=negative_safety,
        shot_type_match=1.0,
        mood_match=1.0,
        temporal_match=0.86,
        overall_semantic_match=0.0,
    )
    result = SemanticVisualResult(
        backend="openai",
        model=model,
        backend_version=OPENAI_BACKEND_VERSION,
        request_version="semantic_visual_request.v1",
        status="success",
        confidence=confidence,
        frames_analysed=frame_count,
        frame_observations=[
            FrameSemanticObservation(
                frame_index=index,
                subject_observations=["whale"] if subject >= 0.5 else ["desert vehicle"],
                action_observations=["swimming"] if action >= 0.5 else ["standing"],
                environment_observations=["ocean"] if environment >= 0.5 else ["desert"],
                location_observations=["coast"] if location >= 0.5 else ["unknown inland"],
                confidence=confidence,
                unwanted_element_observations=["desert"] if negative_present and index == 0 else [],
                short_evidence_summary=f"mocked OpenAI case {case_id}",
            )
            for index in range(max(1, frame_count))
        ],
        aggregate_scores=aggregate,
        must_have_results=[
            TermSemanticCheckResult(term="whale", present=True, confidence=0.93, evidence="visible", frame_indices=[0]),
            TermSemanticCheckResult(term="ocean", present=must_present, confidence=0.91, evidence="mocked", frame_indices=[0] if must_present else []),
        ],
        negative_element_results=[
            TermSemanticCheckResult(
                term="desert",
                present=negative_present,
                confidence=negative_conf,
                evidence="mocked negative check",
                frame_indices=[0] if negative_present else [],
            )
        ],
        mismatch_reasons=mismatch,
        review_required_reasons=review,
        evidence=[SemanticEvidence(kind="mocked_openai", summary=f"mocked case {category}", frame_indices=list(range(max(1, frame_count))), confidence=confidence)],
        hard_reject=hard_reject,
    )
    result.aggregate_scores.overall_semantic_match = max(0.0, min(1.0, (subject + action + environment + location + exact + must + negative_safety) / 7.0))
    result.semantic_score = result.aggregate_scores.overall_semantic_match
    if strictness in {"strict", "balanced", "illustrative"}:
        result.review_required_reasons = list(dict.fromkeys(result.review_required_reasons))
    return result.to_dict()
