from __future__ import annotations

from typing import Any

from .semantic_visual_backend import SemanticBackendCapabilities, SemanticBackendHealth
from .semantic_visual_models import (
    AggregateSemanticScores,
    FrameSemanticObservation,
    SemanticEvidence,
    SemanticVisualRequest,
    SemanticVisualResult,
    TermSemanticCheckResult,
    apply_semantic_aggregation_rules,
    fallback_semantic_result,
)


class MockSemanticVisualBackend:
    name = "mock"

    def __init__(self, *, model: str = "mock-semantic-v1", backend_version: str = "mock.semantic.v1") -> None:
        self.model = model
        self.backend_version = backend_version
        self.call_count = 0
        self.requests_seen: list[SemanticVisualRequest] = []

    def capabilities(self) -> SemanticBackendCapabilities:
        return SemanticBackendCapabilities(
            backend=self.name,
            model=self.model,
            backend_version=self.backend_version,
            supports_images=True,
            supports_video_frames=True,
            supports_batch=True,
            maximum_frames=8,
            batch_limit=20,
            paid_backend=False,
            estimated_cost_per_call_usd=0.0,
        )

    def health_check(self) -> SemanticBackendHealth:
        return SemanticBackendHealth(backend=self.name, configured=True, status="ready", message="deterministic mock backend")

    def analyse_candidate(self, request: SemanticVisualRequest) -> SemanticVisualResult:
        self.call_count += 1
        self.requests_seen.append(request)
        case = _fixture_case(request)
        if case == "timeout":
            return fallback_semantic_result(
                backend=self.name,
                model=self.model,
                backend_version=self.backend_version,
                request_version=request.request_version,
                status="timeout",
                error_code="timeout",
                message="mock semantic timeout",
                retryable=True,
            )
        if case == "invalid_response":
            return fallback_semantic_result(
                backend=self.name,
                model=self.model,
                backend_version=self.backend_version,
                request_version=request.request_version,
                status="invalid_response",
                error_code="invalid_response",
                message="mock invalid structured response",
            )

        frame_count = max(1, len(request.sampled_frame_references))
        subject_score = 0.92
        action_score = 0.90
        environment_score = 0.92
        location_score = 0.80 if request.requirements.location else 1.0
        exact_score = 0.88 if request.requirements.exact_entity else 1.0
        must_score = 0.94
        negative_safety = 0.96
        confidence = 0.92
        mismatch_reasons: list[str] = []
        review_required: list[str] = []
        unwanted: list[str] = []
        negative_results = [
            TermSemanticCheckResult(term=term, present=False, confidence=0.93, evidence="not observed", frame_indices=[])
            for term in request.requirements.negative_elements
        ]

        if case == "subject_mismatch":
            subject_score = 0.18
            exact_score = min(exact_score, 0.18)
            mismatch_reasons.append("subject_mismatch")
        elif case == "action_mismatch":
            action_score = 0.22
            mismatch_reasons.append("action_mismatch")
        elif case == "negative_violation":
            negative_safety = 0.05
            unwanted = [request.requirements.negative_elements[0] if request.requirements.negative_elements else "unwanted"]
            negative_results = [TermSemanticCheckResult(term=unwanted[0], present=True, confidence=0.95, evidence="visible in multiple frames", frame_indices=list(range(min(2, frame_count))))]
        elif case == "low_confidence_negative":
            negative_safety = 0.72
            unwanted = [request.requirements.negative_elements[0] if request.requirements.negative_elements else "unwanted"]
            negative_results = [TermSemanticCheckResult(term=unwanted[0], present=True, confidence=0.55, evidence="uncertain single-frame shape", frame_indices=[0])]
        elif case == "one_anomalous_frame":
            negative_safety = 0.78
            unwanted = [request.requirements.negative_elements[0] if request.requirements.negative_elements else "unwanted"]
            negative_results = [TermSemanticCheckResult(term=unwanted[0], present=True, confidence=0.72, evidence="one anomalous sampled frame", frame_indices=[frame_count - 1])]
            review_required.append("anomalous_frame_observed")
        elif case == "low_confidence":
            confidence = 0.48
            subject_score = 0.58
            action_score = 0.52
            review_required.append("low_confidence")

        must_results = [
            TermSemanticCheckResult(term=term, present=case != "must_have_missing", confidence=0.90, evidence="mock fixture term check", frame_indices=list(range(frame_count)))
            for term in request.requirements.must_have
        ]
        if case == "must_have_missing":
            must_score = 0.20

        observations = _observations(request, frame_count, confidence, unwanted=unwanted if case != "one_anomalous_frame" else [])
        if case == "one_anomalous_frame" and observations:
            observations[-1].unwanted_element_observations = unwanted
            observations[-1].confidence = 0.72

        result = SemanticVisualResult(
            backend=self.name,
            model=self.model,
            backend_version=self.backend_version,
            request_version=request.request_version,
            status="success",
            confidence=confidence,
            frames_analysed=frame_count,
            frame_observations=observations,
            aggregate_scores=AggregateSemanticScores(
                subject_match=subject_score,
                action_match=action_score,
                environment_match=environment_score,
                location_match=location_score,
                exact_entity_match=exact_score,
                must_have_match=must_score,
                negative_element_safety=negative_safety,
                shot_type_match=0.82 if request.requirements.shot_type else 1.0,
                mood_match=0.86 if request.requirements.mood else 1.0,
                temporal_match=0.88,
                overall_semantic_match=0.0,
            ),
            must_have_results=must_results,
            negative_element_results=negative_results,
            mismatch_reasons=mismatch_reasons,
            review_required_reasons=review_required,
            evidence=[
                SemanticEvidence(
                    kind="mock_fixture",
                    summary=f"deterministic semantic fixture: {case}",
                    frame_indices=list(range(frame_count)),
                    confidence=confidence,
                )
            ],
        )
        return apply_semantic_aggregation_rules(result, request)


def _fixture_case(request: SemanticVisualRequest) -> str:
    value = request.candidate_metadata.get("semantic_fixture") or request.candidate_metadata.get("mock_semantic_case")
    if isinstance(value, dict):
        return str(value.get("case") or "good_match")
    if value:
        return str(value)
    text = " ".join(
        str(item)
        for item in (
            request.candidate_metadata.get("title", ""),
            request.candidate_metadata.get("description", ""),
            " ".join(str(tag) for tag in request.candidate_metadata.get("tags", []) or []),
        )
    ).lower()
    if request.requirements.subject and request.requirements.subject.lower() not in text:
        return "subject_mismatch"
    if request.requirements.action and request.requirements.action.lower() not in text:
        return "action_mismatch"
    if any(term.lower() in text for term in request.requirements.negative_elements):
        return "negative_violation"
    return "good_match"


def _observations(
    request: SemanticVisualRequest,
    frame_count: int,
    confidence: float,
    *,
    unwanted: list[str],
) -> list[FrameSemanticObservation]:
    observations: list[FrameSemanticObservation] = []
    for index in range(frame_count):
        observations.append(
            FrameSemanticObservation(
                frame_index=index,
                subject_observations=[request.requirements.subject] if request.requirements.subject else [],
                action_observations=[request.requirements.action] if request.requirements.action else [],
                environment_observations=list(request.requirements.environment),
                location_observations=list(request.requirements.location),
                shot_type_observations=[request.requirements.shot_type] if request.requirements.shot_type else [],
                temporal_observations=[request.requirements.time_period] if request.requirements.time_period else [],
                unwanted_element_observations=unwanted,
                confidence=confidence,
                short_evidence_summary="mock frame observation",
            )
        )
    return observations
