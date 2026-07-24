from __future__ import annotations

import dataclasses
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SEMANTIC_REQUEST_VERSION = "semantic_visual_request.v1"
SEMANTIC_RESULT_VERSION = "semantic_visual_result.v1"
SEMANTIC_STRICTNESS_VALUES = {"strict", "balanced", "illustrative"}
SECRET_KEY_MARKERS = ("api_key", "apikey", "token", "secret", "password", "certificate", "proof", "env")
PATH_KEYS = {"path", "local_path", "downloaded_path", "private_local_path"}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class SceneVisualRequirements:
    scene_id: str = ""
    scene_text: str = ""
    subject: str = ""
    secondary_subjects: list[str] = field(default_factory=list)
    action: str = ""
    environment: list[str] = field(default_factory=list)
    location: list[str] = field(default_factory=list)
    exact_entity: str = ""
    must_have: list[str] = field(default_factory=list)
    negative_elements: list[str] = field(default_factory=list)
    shot_type: str = ""
    camera_view: str = ""
    mood: list[str] = field(default_factory=list)
    time_period: str = ""
    weather: str = ""
    target_aspect_ratio: str = "9:16"
    scene_purpose: str = ""
    acceptable_alternatives: list[str] = field(default_factory=list)
    semantic_strictness: str = "balanced"

    def __post_init__(self) -> None:
        self.secondary_subjects = _as_list(self.secondary_subjects)
        self.environment = _as_list(self.environment)
        self.location = _as_list(self.location)
        self.must_have = _as_list(self.must_have)
        self.negative_elements = _as_list(self.negative_elements)
        self.mood = _as_list(self.mood)
        self.acceptable_alternatives = _as_list(self.acceptable_alternatives)
        if self.semantic_strictness not in SEMANTIC_STRICTNESS_VALUES:
            self.semantic_strictness = "balanced"

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "SceneVisualRequirements":
        if not isinstance(data, dict):
            return cls()
        return cls(
            scene_id=str(data.get("scene_id") or ""),
            scene_text=str(data.get("scene_text") or ""),
            subject=_first_text(data.get("subject")),
            secondary_subjects=_as_list(data.get("secondary_subjects")),
            action=_first_text(data.get("action")),
            environment=_as_list(data.get("environment")),
            location=_as_list(data.get("location")),
            exact_entity=str(data.get("exact_entity") or ""),
            must_have=_as_list(data.get("must_have")),
            negative_elements=_as_list(data.get("negative_elements") or data.get("must_not_include")),
            shot_type=str(data.get("shot_type") or ""),
            camera_view=str(data.get("camera_view") or ""),
            mood=_as_list(data.get("mood")),
            time_period=str(data.get("time_period") or ""),
            weather=str(data.get("weather") or ""),
            target_aspect_ratio=str(data.get("target_aspect_ratio") or "9:16"),
            scene_purpose=str(data.get("scene_purpose") or ""),
            acceptable_alternatives=_as_list(data.get("acceptable_alternatives")),
            semantic_strictness=str(data.get("semantic_strictness") or "balanced"),
        )

    @classmethod
    def from_current_semantic_scene(
        cls,
        semantic_scene: Any,
        *,
        scene: dict[str, Any] | None = None,
    ) -> "SceneVisualRequirements":
        data = semantic_scene.to_dict() if hasattr(semantic_scene, "to_dict") else dict(semantic_scene or {})
        raw_scene = scene or {}
        explicit = raw_scene.get("semantic") if isinstance(raw_scene.get("semantic"), dict) else {}
        visual_priority = str(data.get("visual_priority") or explicit.get("visual_priority") or raw_scene.get("visual_priority") or "")
        subject = _first_text(data.get("subject"))
        action = _first_text(data.get("action"))
        camera = _first_text(data.get("camera"))
        scene_text = _first_non_empty(
            raw_scene.get("scene_text"),
            raw_scene.get("narration"),
            raw_scene.get("visual_description"),
            raw_scene.get("visual_intent"),
            raw_scene.get("primary_query"),
        )
        exact_entity = str(explicit.get("exact_entity") or raw_scene.get("exact_entity") or "")
        if not exact_entity and visual_priority in {"exact_subject", "exact_action"}:
            exact_entity = subject
        return cls(
            scene_id=str(data.get("scene_id") or raw_scene.get("scene_id") or ""),
            scene_text=scene_text,
            subject=subject,
            secondary_subjects=_as_list(data.get("secondary_subjects")),
            action=action,
            environment=_as_list(data.get("environment")),
            location=_as_list(data.get("location")),
            exact_entity=exact_entity,
            must_have=_as_list(data.get("must_include")),
            negative_elements=_as_list(data.get("must_not_include")),
            shot_type=str(explicit.get("shot_type") or raw_scene.get("shot_type") or ""),
            camera_view=str(explicit.get("camera_view") or raw_scene.get("camera_view") or camera),
            mood=_as_list(data.get("mood")),
            time_period=str(explicit.get("time_period") or raw_scene.get("time_period") or ""),
            weather=str(explicit.get("weather") or raw_scene.get("weather") or ""),
            target_aspect_ratio=str(raw_scene.get("target_aspect_ratio") or explicit.get("target_aspect_ratio") or "9:16"),
            scene_purpose=str(explicit.get("scene_purpose") or raw_scene.get("visual_priority") or visual_priority),
            acceptable_alternatives=_as_list(explicit.get("acceptable_alternatives") or raw_scene.get("acceptable_alternatives")),
            semantic_strictness=_strictness_from_priority(visual_priority),
        )

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass
class SemanticFrameReference:
    frame_index: int
    sha256: str = ""
    perceptual_hash: str = ""
    relative_path: str = ""
    width: int = 0
    height: int = 0
    requested_timestamp_sec: float = 0.0
    actual_timestamp_sec: float = 0.0
    extraction_status: str = ""
    is_poster_frame: bool = False
    technical_metrics: dict[str, Any] = field(default_factory=dict)
    private_local_path: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "SemanticFrameReference":
        raw = data or {}
        return cls(
            frame_index=int(raw.get("frame_index") or 0),
            sha256=str(raw.get("sha256") or ""),
            perceptual_hash=str(raw.get("perceptual_hash") or ""),
            relative_path=str(raw.get("relative_path") or ""),
            width=int(raw.get("width") or 0),
            height=int(raw.get("height") or 0),
            requested_timestamp_sec=float(raw.get("requested_timestamp_sec") or 0.0),
            actual_timestamp_sec=float(raw.get("actual_timestamp_sec") or 0.0),
            extraction_status=str(raw.get("extraction_status") or ""),
            is_poster_frame=bool(raw.get("is_poster_frame", False)),
            technical_metrics=dict(raw.get("technical_metrics") or {}),
            private_local_path=str(raw.get("private_local_path") or ""),
        )

    @classmethod
    def from_review_frame(cls, data: dict[str, Any], *, project_root: str | Path | None = None, media_type: str = "") -> "SemanticFrameReference":
        raw_path = str(data.get("local_frame_path") or data.get("relative_path") or "")
        relative_path = str(data.get("relative_path") or "")
        if not relative_path:
            relative_path = _relative_to_project(raw_path, project_root)
        frame_count_marker = bool(data.get("is_poster_frame", False))
        return cls(
            frame_index=int(data.get("frame_index") or 0),
            sha256=str(data.get("sha256") or ""),
            perceptual_hash=str(data.get("perceptual_hash") or ""),
            relative_path=relative_path,
            width=int(data.get("width") or 0),
            height=int(data.get("height") or 0),
            requested_timestamp_sec=float(data.get("requested_timestamp_sec") or 0.0),
            actual_timestamp_sec=float(data.get("actual_timestamp_sec") or 0.0),
            extraction_status=str(data.get("extraction_status") or ""),
            is_poster_frame=frame_count_marker or (media_type == "video" and len([data]) == 1),
            technical_metrics=dict(data.get("technical_metrics") or {}),
            private_local_path=raw_path if _looks_like_path(raw_path) else "",
        )

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "frame_index": self.frame_index,
            "sha256": self.sha256,
            "perceptual_hash": self.perceptual_hash,
            "relative_path": self.relative_path if not _looks_absolute(self.relative_path) else "",
            "width": self.width,
            "height": self.height,
            "requested_timestamp_sec": self.requested_timestamp_sec,
            "actual_timestamp_sec": self.actual_timestamp_sec,
            "extraction_status": self.extraction_status,
            "is_poster_frame": self.is_poster_frame,
            "technical_metrics": _sanitize_public(self.technical_metrics),
        }

    def to_dict(self) -> dict[str, Any]:
        return self.to_public_dict()


@dataclass
class AggregateSemanticScores:
    subject_match: float = 0.0
    action_match: float = 0.0
    environment_match: float = 0.0
    location_match: float = 0.0
    exact_entity_match: float = 0.0
    must_have_match: float = 0.0
    negative_element_safety: float = 1.0
    shot_type_match: float = 0.0
    mood_match: float = 0.0
    temporal_match: float = 0.0
    overall_semantic_match: float = 0.0

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "AggregateSemanticScores":
        raw = data or {}
        return cls(**{field.name: float(raw.get(field.name) or 0.0) for field in dataclasses.fields(cls)})

    def to_dict(self) -> dict[str, float]:
        return dataclasses.asdict(self)

    def validation_errors(self, prefix: str = "aggregate_scores") -> list[str]:
        errors: list[str] = []
        for key, value in self.to_dict().items():
            if not _is_score(value):
                errors.append(f"{prefix}.{key} must be between 0.0 and 1.0")
        return errors


@dataclass
class TermSemanticCheckResult:
    term: str
    present: bool
    confidence: float = 0.0
    evidence: str = ""
    frame_indices: list[int] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "TermSemanticCheckResult":
        raw = data or {}
        return cls(
            term=str(raw.get("term") or ""),
            present=bool(raw.get("present", False)),
            confidence=float(raw.get("confidence") or 0.0),
            evidence=str(raw.get("evidence") or ""),
            frame_indices=[int(item) for item in raw.get("frame_indices") or []],
        )

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass
class SemanticEvidence:
    kind: str
    summary: str
    frame_indices: list[int] = field(default_factory=list)
    confidence: float = 0.0

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "SemanticEvidence":
        raw = data or {}
        return cls(
            kind=str(raw.get("kind") or ""),
            summary=str(raw.get("summary") or ""),
            frame_indices=[int(item) for item in raw.get("frame_indices") or []],
            confidence=float(raw.get("confidence") or 0.0),
        )

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass
class FrameSemanticObservation:
    frame_index: int
    subject_observations: list[str] = field(default_factory=list)
    action_observations: list[str] = field(default_factory=list)
    environment_observations: list[str] = field(default_factory=list)
    location_observations: list[str] = field(default_factory=list)
    shot_type_observations: list[str] = field(default_factory=list)
    temporal_observations: list[str] = field(default_factory=list)
    visible_text_or_logo_risk: bool = False
    unwanted_element_observations: list[str] = field(default_factory=list)
    confidence: float = 0.0
    short_evidence_summary: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "FrameSemanticObservation":
        raw = data or {}
        return cls(
            frame_index=int(raw.get("frame_index") or 0),
            subject_observations=_as_list(raw.get("subject_observations")),
            action_observations=_as_list(raw.get("action_observations")),
            environment_observations=_as_list(raw.get("environment_observations")),
            location_observations=_as_list(raw.get("location_observations")),
            shot_type_observations=_as_list(raw.get("shot_type_observations")),
            temporal_observations=_as_list(raw.get("temporal_observations")),
            visible_text_or_logo_risk=bool(raw.get("visible_text_or_logo_risk", False)),
            unwanted_element_observations=_as_list(raw.get("unwanted_element_observations")),
            confidence=float(raw.get("confidence") or 0.0),
            short_evidence_summary=str(raw.get("short_evidence_summary") or ""),
        )

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass
class SemanticVisualError:
    code: str
    message: str = ""
    retryable: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "SemanticVisualError | None":
        if not isinstance(data, dict) or not data.get("code"):
            return None
        return cls(code=str(data.get("code") or ""), message=str(data.get("message") or ""), retryable=bool(data.get("retryable", False)))

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass
class SemanticVisualRequest:
    project_id: str
    scene_id: str
    backend: str
    requirements: SceneVisualRequirements
    candidate_id: str
    provider: str
    candidate_metadata: dict[str, Any] = field(default_factory=dict)
    sampled_frame_references: list[SemanticFrameReference] = field(default_factory=list)
    technical_metrics_summary: dict[str, Any] = field(default_factory=dict)
    maximum_frames: int = 5
    backend_options: dict[str, Any] = field(default_factory=dict)
    request_version: str = SEMANTIC_REQUEST_VERSION

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SemanticVisualRequest":
        return cls(
            project_id=str(data.get("project_id") or ""),
            scene_id=str(data.get("scene_id") or ""),
            backend=str(data.get("backend") or ""),
            requirements=SceneVisualRequirements.from_dict(data.get("requirements")),
            candidate_id=str(data.get("candidate_id") or ""),
            provider=str(data.get("provider") or ""),
            candidate_metadata=dict(data.get("candidate_metadata") or {}),
            sampled_frame_references=[SemanticFrameReference.from_dict(item) for item in data.get("sampled_frame_references") or []],
            technical_metrics_summary=dict(data.get("technical_metrics_summary") or {}),
            maximum_frames=int(data.get("maximum_frames") or 5),
            backend_options=dict(data.get("backend_options") or {}),
            request_version=str(data.get("request_version") or SEMANTIC_REQUEST_VERSION),
        )

    def to_public_dict(self) -> dict[str, Any]:
        frames = self.sampled_frame_references[: max(0, int(self.maximum_frames or 0))]
        return {
            "request_version": self.request_version,
            "project_id": self.project_id,
            "scene_id": self.scene_id,
            "backend": self.backend,
            "requirements": self.requirements.to_dict(),
            "candidate_id": self.candidate_id,
            "provider": self.provider,
            "candidate_metadata": _sanitize_public(self.candidate_metadata),
            "sampled_frame_references": [frame.to_public_dict() for frame in frames],
            "technical_metrics_summary": _sanitize_public(self.technical_metrics_summary),
            "maximum_frames": self.maximum_frames,
            "backend_options": _sanitize_public(self.backend_options),
        }

    def to_dict(self) -> dict[str, Any]:
        return self.to_public_dict()


@dataclass
class SemanticVisualResult:
    backend: str
    model: str
    backend_version: str
    request_version: str
    analysed_at: str = field(default_factory=utc_now_iso)
    result_version: str = SEMANTIC_RESULT_VERSION
    status: str = "success"
    confidence: float = 0.0
    frames_analysed: int = 0
    frame_observations: list[FrameSemanticObservation] = field(default_factory=list)
    aggregate_scores: AggregateSemanticScores = field(default_factory=AggregateSemanticScores)
    must_have_results: list[TermSemanticCheckResult] = field(default_factory=list)
    negative_element_results: list[TermSemanticCheckResult] = field(default_factory=list)
    mismatch_reasons: list[str] = field(default_factory=list)
    review_required_reasons: list[str] = field(default_factory=list)
    evidence: list[SemanticEvidence] = field(default_factory=list)
    semantic_score: float = 0.0
    hard_reject: bool = False
    cache_key: str = ""
    raw_response_reference: str = ""
    error: SemanticVisualError | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "SemanticVisualResult":
        raw = data or {}
        return cls(
            backend=str(raw.get("backend") or ""),
            model=str(raw.get("model") or ""),
            backend_version=str(raw.get("backend_version") or ""),
            request_version=str(raw.get("request_version") or SEMANTIC_REQUEST_VERSION),
            analysed_at=str(raw.get("analysed_at") or utc_now_iso()),
            result_version=str(raw.get("result_version") or SEMANTIC_RESULT_VERSION),
            status=str(raw.get("status") or "success"),
            confidence=float(raw.get("confidence") or 0.0),
            frames_analysed=int(raw.get("frames_analysed") or 0),
            frame_observations=[FrameSemanticObservation.from_dict(item) for item in raw.get("frame_observations") or []],
            aggregate_scores=AggregateSemanticScores.from_dict(raw.get("aggregate_scores")),
            must_have_results=[TermSemanticCheckResult.from_dict(item) for item in raw.get("must_have_results") or []],
            negative_element_results=[TermSemanticCheckResult.from_dict(item) for item in raw.get("negative_element_results") or []],
            mismatch_reasons=_as_list(raw.get("mismatch_reasons")),
            review_required_reasons=_as_list(raw.get("review_required_reasons")),
            evidence=[SemanticEvidence.from_dict(item) for item in raw.get("evidence") or []],
            semantic_score=float(raw.get("semantic_score") or 0.0),
            hard_reject=bool(raw.get("hard_reject", False)),
            cache_key=str(raw.get("cache_key") or ""),
            raw_response_reference=str(raw.get("raw_response_reference") or ""),
            error=SemanticVisualError.from_dict(raw.get("error")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_version": self.result_version,
            "backend": self.backend,
            "model": self.model,
            "backend_version": self.backend_version,
            "request_version": self.request_version,
            "analysed_at": self.analysed_at,
            "status": self.status,
            "confidence": self.confidence,
            "frames_analysed": self.frames_analysed,
            "frame_observations": [item.to_dict() for item in self.frame_observations],
            "aggregate_scores": self.aggregate_scores.to_dict(),
            "must_have_results": [item.to_dict() for item in self.must_have_results],
            "negative_element_results": [item.to_dict() for item in self.negative_element_results],
            "mismatch_reasons": self.mismatch_reasons,
            "review_required_reasons": self.review_required_reasons,
            "evidence": [item.to_dict() for item in self.evidence],
            "semantic_score": self.semantic_score,
            "hard_reject": self.hard_reject,
            "cache_key": self.cache_key,
            "raw_response_reference": self.raw_response_reference,
            "error": self.error.to_dict() if self.error else None,
        }

    def to_review_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "backend": self.backend,
            "model": self.model,
            "confidence": self.confidence,
            "aggregate_scores": self.aggregate_scores.to_dict(),
            "must_have_results": [item.to_dict() for item in self.must_have_results],
            "negative_element_results": [item.to_dict() for item in self.negative_element_results],
            "mismatch_reasons": self.mismatch_reasons,
            "review_required_reasons": self.review_required_reasons,
            "evidence": [item.to_dict() for item in self.evidence],
            "semantic_score": self.semantic_score,
            "hard_reject": self.hard_reject,
            "cache_key": self.cache_key,
        }

    def validation_errors(self) -> list[str]:
        errors = self.aggregate_scores.validation_errors()
        for field_name in ("confidence", "semantic_score"):
            if not _is_score(float(getattr(self, field_name))):
                errors.append(f"{field_name} must be between 0.0 and 1.0")
        for index, observation in enumerate(self.frame_observations):
            if not _is_score(observation.confidence):
                errors.append(f"frame_observations[{index}].confidence must be between 0.0 and 1.0")
        for collection_name, collection in (
            ("must_have_results", self.must_have_results),
            ("negative_element_results", self.negative_element_results),
            ("evidence", self.evidence),
        ):
            for index, item in enumerate(collection):
                confidence = float(getattr(item, "confidence", 0.0))
                if not _is_score(confidence):
                    errors.append(f"{collection_name}[{index}].confidence must be between 0.0 and 1.0")
        return errors

    def assert_valid(self) -> None:
        errors = self.validation_errors()
        if errors:
            raise ValueError("; ".join(errors))


def apply_semantic_aggregation_rules(
    result: SemanticVisualResult,
    request: SemanticVisualRequest,
    *,
    minimum_confidence: float = 0.65,
    hard_reject_confidence: float = 0.90,
) -> SemanticVisualResult:
    if result.status != "success":
        result.semantic_score = 0.0
        result.hard_reject = False
        return result

    frame_count = result.frames_analysed or len(result.frame_observations) or len(request.sampled_frame_references)
    result.frames_analysed = frame_count
    reasons = list(result.review_required_reasons)
    mismatches = list(result.mismatch_reasons)
    scores = result.aggregate_scores

    if frame_count <= 1 and request.requirements.action:
        scores.action_match = min(scores.action_match, 0.65)
        reasons.append("single_frame_action_limited")
    if _has_limited_temporal_evidence(request, frame_count):
        scores.temporal_match = min(scores.temporal_match or 1.0, 0.65)
        reasons.append("limited_temporal_evidence")

    for item in result.must_have_results:
        if not item.present:
            if item.confidence >= minimum_confidence:
                mismatches.append(f"must_have_missing:{item.term}")
                scores.must_have_match = min(scores.must_have_match, max(0.0, 1.0 - item.confidence))
            else:
                reasons.append(f"must_have_low_confidence_missing:{item.term}")

    for item in result.negative_element_results:
        if not item.present:
            continue
        if item.confidence >= hard_reject_confidence and _negative_evidence_is_consistent(item, frame_count):
            result.hard_reject = True
            scores.negative_element_safety = min(scores.negative_element_safety, max(0.0, 1.0 - item.confidence))
            mismatches.append(f"negative_element_detected:{item.term}")
        else:
            reasons.append(f"negative_element_low_confidence:{item.term}")

    if result.confidence < minimum_confidence:
        reasons.append("low_confidence")

    scores.overall_semantic_match = _weighted_semantic_score(scores, request.requirements)
    result.semantic_score = scores.overall_semantic_match
    result.review_required_reasons = _unique(reasons)
    result.mismatch_reasons = _unique(mismatches)
    return result


def fallback_semantic_result(
    *,
    backend: str,
    model: str = "",
    backend_version: str = "",
    request_version: str = SEMANTIC_REQUEST_VERSION,
    status: str,
    error_code: str,
    message: str,
    cache_key: str = "",
    retryable: bool = False,
) -> SemanticVisualResult:
    return SemanticVisualResult(
        backend=backend,
        model=model,
        backend_version=backend_version,
        request_version=request_version,
        status=status,
        confidence=0.0,
        frames_analysed=0,
        aggregate_scores=AggregateSemanticScores(),
        semantic_score=0.0,
        hard_reject=False,
        cache_key=cache_key,
        review_required_reasons=[error_code],
        error=SemanticVisualError(code=error_code, message=message, retryable=retryable),
    )


def _weighted_semantic_score(scores: AggregateSemanticScores, requirements: SceneVisualRequirements) -> float:
    strictness = requirements.semantic_strictness
    if strictness == "strict":
        weights = {
            "subject_match": 0.20,
            "action_match": 0.10,
            "environment_match": 0.07,
            "location_match": 0.05,
            "exact_entity_match": 0.13,
            "must_have_match": 0.20,
            "negative_element_safety": 0.17,
            "shot_type_match": 0.03,
            "mood_match": 0.02,
            "temporal_match": 0.03,
        }
    elif strictness == "illustrative":
        weights = {
            "subject_match": 0.10,
            "action_match": 0.10,
            "environment_match": 0.20,
            "location_match": 0.08,
            "exact_entity_match": 0.04,
            "must_have_match": 0.12,
            "negative_element_safety": 0.18,
            "shot_type_match": 0.06,
            "mood_match": 0.08,
            "temporal_match": 0.04,
        }
    else:
        weights = {
            "subject_match": 0.18,
            "action_match": 0.16,
            "environment_match": 0.14,
            "location_match": 0.08,
            "exact_entity_match": 0.10,
            "must_have_match": 0.16,
            "negative_element_safety": 0.14,
            "shot_type_match": 0.05,
            "mood_match": 0.04,
            "temporal_match": 0.05,
        }
    values = scores.to_dict()
    values["subject_match"] = values["subject_match"] if requirements.subject else 1.0
    values["action_match"] = values["action_match"] if requirements.action else 1.0
    values["environment_match"] = values["environment_match"] if requirements.environment else 1.0
    values["location_match"] = values["location_match"] if requirements.location else 1.0
    values["exact_entity_match"] = values["exact_entity_match"] if requirements.exact_entity else 1.0
    values["must_have_match"] = values["must_have_match"] if requirements.must_have else 1.0
    values["shot_type_match"] = values["shot_type_match"] if requirements.shot_type else 1.0
    values["mood_match"] = values["mood_match"] if requirements.mood else 1.0
    values["temporal_match"] = values["temporal_match"] if requirements.time_period or requirements.action else max(values["temporal_match"], 1.0)
    score = sum(values[key] * weight for key, weight in weights.items())
    return max(0.0, min(1.0, score))


def _negative_evidence_is_consistent(item: TermSemanticCheckResult, frame_count: int) -> bool:
    if frame_count <= 1:
        return True
    return len(set(item.frame_indices)) >= 2 or item.confidence >= 0.98


def _has_limited_temporal_evidence(request: SemanticVisualRequest, frame_count: int) -> bool:
    if frame_count <= 0:
        return True
    media_type = str(request.candidate_metadata.get("media_type") or "").lower()
    if media_type != "video":
        return False
    if frame_count == 1:
        return True
    return bool(request.sampled_frame_references) and all(frame.is_poster_frame for frame in request.sampled_frame_references)


def _sanitize_public(value: Any) -> Any:
    if dataclasses.is_dataclass(value):
        value = dataclasses.asdict(value)
    if isinstance(value, dict):
        cleaned: dict[str, Any] = {}
        for key, item in value.items():
            normalized = str(key).lower()
            if normalized in PATH_KEYS or any(marker in normalized for marker in SECRET_KEY_MARKERS):
                continue
            if normalized == "raw_metadata":
                continue
            cleaned[str(key)] = _sanitize_public(item)
        return cleaned
    if isinstance(value, list):
        return [_sanitize_public(item) for item in value]
    if isinstance(value, str):
        if _looks_absolute(value):
            return ""
        return value
    return value


def _relative_to_project(raw_path: str, project_root: str | Path | None) -> str:
    if not raw_path:
        return ""
    path = Path(raw_path)
    if project_root:
        try:
            return path.resolve().relative_to(Path(project_root).resolve()).as_posix()
        except Exception:
            pass
    return "" if _looks_absolute(raw_path) else raw_path.replace("\\", "/")


def _looks_like_path(value: str) -> bool:
    return bool(value and ("/" in value or "\\" in value or re.match(r"^[A-Za-z]:", value)))


def _looks_absolute(value: str) -> bool:
    if not value:
        return False
    return bool(re.match(r"^[A-Za-z]:[\\/]", value) or value.startswith("\\\\") or value.startswith("/"))


def _strictness_from_priority(priority: str) -> str:
    if priority in {"exact_subject", "exact_action"}:
        return "strict"
    if priority in {"environment", "research_context"}:
        return "balanced"
    return "illustrative"


def _first_text(value: Any) -> str:
    values = _as_list(value)
    return values[0] if values else str(value or "")


def _first_non_empty(*values: Any) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, tuple | set):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and "," in value:
        return [item.strip() for item in value.split(",") if item.strip()]
    text = str(value).strip()
    return [text] if text else []


def _is_score(value: float) -> bool:
    return 0.0 <= float(value) <= 1.0


def _unique(values: list[str]) -> list[str]:
    return [item for item in dict.fromkeys(str(value) for value in values if str(value))]
