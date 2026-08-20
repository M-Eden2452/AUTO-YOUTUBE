"""One canonical, explainable verdict on one candidate for one scene.

Stage Q2.1 stopped the pipeline scoring every candidate at 100. Stage Q2.2A-2 stops
the remaining, quieter failure: a candidate that matched *part* of what the scene asked
for was accepted as if it had matched all of it, and the reasoning was thrown away
before the manifest was written.

The retest produced two of those. A NASA press-day photograph whose description says
"mass spectrometer" answered an ordinary laboratory scene, because one term of a long
and otherwise unrelated description was enough. A clip of an iceberg breaking off
answered a scene about a research station and airborne transport, because both the
scene and the clip say "Antarctica".

Neither is a scoring bug. Both are the same missing idea: a scene states *several*
requirements, and a candidate must be judged against all of them, one at a time, with
the answer for each kept. That is what a slot is here - one requirement of the scene,
with the evidence for or against it.

What this module deliberately does not do
-----------------------------------------
It does not look at the picture. Every judgement below is made on provider metadata,
which is why a candidate whose composition cannot be settled from words comes back as
``crop_review_required`` or ``manual_confirmation_required`` rather than as a verdict
this layer is not entitled to give. There is no NLP model, no LLM and no knowledge
base: a contradiction has to be stated by the scene's own author before it counts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.assets.scene_strategy import (
    CLASS_ARCHIVE,
    CLASS_DATA_INFOGRAPHIC,
    CLASS_EXACT_LOCATION,
    CLASS_GENERIC_BROLL,
    CLASS_MANUAL_REQUIRED,
    CLASS_RESEARCH_ACTIVITY,
    CLASS_SATELLITE,
    CLASS_SCIENTIFIC_EQUIPMENT,
    CLASS_SCIENTIFIC_VISUALIZATION,
    CLASS_SPECIFIC_OBJECT,
    EXACTING_CLASSES,
)

from .evidence import CandidateEvidence

DECISION_SCHEMA_VERSION = 1

# --- Slot kinds --------------------------------------------------------------
SLOT_SUBJECT = "subject"
SLOT_ACTION = "action"
SLOT_LOCATION = "location"
SLOT_CONTEXT = "context"
# The author's literal requirement (``must_include``, which carries ``exact_entities``).
# Checked verbatim, never leniently: a name that has to survive into the query has to
# survive into the evidence too.
SLOT_REQUIREMENT = "requirement"
# Stated by the scene but not demanded by it (``should_include``).
SLOT_SUPPORTING = "supporting"
# Something the author said would contradict the scene, found in the metadata.
SLOT_CONFLICT = "conflict"

# --- Slot statuses -----------------------------------------------------------
SLOT_MATCHED = "matched"
SLOT_PARTIAL = "partial"
SLOT_MISSING = "missing"
SLOT_UNDECIDABLE = "undecidable"
SLOT_CONFLICTING = "conflicting"

# --- Slot verdicts -----------------------------------------------------------
VERDICT_COMPLETE = "complete"
VERDICT_PARTIAL = "partial"
VERDICT_INCOMPLETE = "incomplete"
VERDICT_CONFLICTING = "conflicting"
VERDICT_UNVERIFIED = "unverified"

# --- Support statuses --------------------------------------------------------
SUPPORT_FULL = "full_support"
SUPPORT_PARTIAL = "partial_support"
SUPPORT_MANUAL = "manual_confirmation_required"
SUPPORT_RIGHTS_BLOCKED = "relevant_but_rights_blocked"
SUPPORT_UNVERIFIED = "unverified"
SUPPORT_UNSUPPORTED = "unsupported"

# --- Follow-up work a support status implies ---------------------------------
NEEDS_ADDITIONAL_ASSET = "needs_additional_asset"
NEEDS_MULTI_ASSET = "needs_multi_asset"
NEEDS_CROP_REVIEW = "needs_crop_review"
NEEDS_MANUAL_CONFIRMATION = "needs_manual_confirmation"
NEEDS_RIGHTS_CLEARANCE = "needs_rights_clearance"

# --- Scene resolution --------------------------------------------------------
RESOLVED = "resolved"
RESOLVED_NEEDS_REVIEW = "resolved_needs_review"
UNRESOLVED_NO_CANDIDATE = "unresolved_no_candidate"
UNRESOLVED_UNVERIFIED = "unresolved_unverified"
UNRESOLVED_GENERATOR_FAILED = "unresolved_generator_failed"
UNRESOLVED_RIGHTS_BLOCKED = "unresolved_rights_blocked"
MANUAL_ACTION_REQUIRED = "manual_action_required"

# --- Crop / framing decision -------------------------------------------------
FRAMING_VERTICAL_READY = "vertical_ready"
FRAMING_CROP_REVIEW = "crop_review_required"
FRAMING_LOW_RESOLUTION = "low_resolution_after_crop"
FRAMING_ASPECT_MISMATCH = "aspect_ratio_mismatch"
FRAMING_REJECTED = "technical_rejected"
FRAMING_UNKNOWN = "unknown"

FRAMING_HARD_REJECT = frozenset({FRAMING_LOW_RESOLUTION, FRAMING_ASPECT_MISMATCH, FRAMING_REJECTED})

# Which of the scene's own descriptive fields a class must have confirmed before a
# candidate may be called a full match. A field only becomes a required slot when the
# scene actually states it - an empty field constrains nothing.
#
# ``generic_broll`` requires none of them on purpose: atmospheric footage is allowed to
# show part of what the narration lists, which is exactly what "partial support" is for.
# ``data_infographic`` requires none either, because it is never answered by a search.
REQUIRED_SLOT_KINDS: dict[str, tuple[str, ...]] = {
    CLASS_EXACT_LOCATION: (SLOT_LOCATION, SLOT_SUBJECT, SLOT_ACTION, SLOT_CONTEXT),
    CLASS_SATELLITE: (SLOT_LOCATION, SLOT_SUBJECT),
    CLASS_SCIENTIFIC_EQUIPMENT: (SLOT_SUBJECT,),
    CLASS_SPECIFIC_OBJECT: (SLOT_SUBJECT,),
    CLASS_RESEARCH_ACTIVITY: (SLOT_SUBJECT, SLOT_ACTION, SLOT_LOCATION),
    CLASS_ARCHIVE: (SLOT_SUBJECT,),
    CLASS_GENERIC_BROLL: (),
    CLASS_DATA_INFOGRAPHIC: (),
    # A visualisation is judged on the one thing it exists to show. Its "action" and
    # "place" are how the animator drew it, and no catalogue states them.
    CLASS_SCIENTIFIC_VISUALIZATION: (SLOT_SUBJECT,),
    CLASS_MANUAL_REQUIRED: (),
}
# A scene whose class was never decided constrains nothing beyond its own explicit
# requirements. Guessing here would reject material for a class nobody assigned.
DEFAULT_REQUIRED_SLOT_KINDS: tuple[str, ...] = ()

# Above this share of a phrase's words the phrase is confirmed; below the lower bound
# nothing of it was found. In between the evidence shows part of the description -
# enough to keep the candidate, never enough to call it a full match. The iceberg
# scored 33 on "antarctic research station" because only the continent was there.
SLOT_MATCH_SCORE = 99.0
SLOT_PARTIAL_SCORE = 50.0


@dataclass
class SlotDecision:
    """One requirement of the scene, and what the metadata says about it."""

    name: str
    kind: str
    required: bool = False
    terms: list[str] = field(default_factory=list)
    status: str = SLOT_MISSING
    score: float = 0.0
    matched_terms: list[str] = field(default_factory=list)
    missing_terms: list[str] = field(default_factory=list)
    evidence_terms: list[str] = field(default_factory=list)
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind,
            "required": self.required,
            "terms": list(self.terms),
            "status": self.status,
            "score": round(float(self.score), 3),
            "matched_terms": list(self.matched_terms),
            "missing_terms": list(self.missing_terms),
            "evidence_terms": list(self.evidence_terms),
            "note": self.note,
        }


@dataclass
class SlotVerdict:
    """Every slot of one scene, judged against one candidate."""

    slots: list[SlotDecision] = field(default_factory=list)
    verdict: str = VERDICT_UNVERIFIED

    @property
    def required_slots(self) -> list[str]:
        return [slot.name for slot in self.slots if slot.required]

    @property
    def matched_slots(self) -> list[str]:
        return [slot.name for slot in self.slots if slot.status == SLOT_MATCHED]

    @property
    def missing_slots(self) -> list[str]:
        return [slot.name for slot in self.slots if slot.status in {SLOT_MISSING, SLOT_PARTIAL}]

    @property
    def conflicting_slots(self) -> list[str]:
        return [slot.name for slot in self.slots if slot.status == SLOT_CONFLICTING]

    @property
    def undecidable_slots(self) -> list[str]:
        return [slot.name for slot in self.slots if slot.status == SLOT_UNDECIDABLE]

    @property
    def missing_required_slots(self) -> list[str]:
        """Required slots that are not fully confirmed - partial ones included.

        Enough to refuse a *full* match; not enough on its own to refuse the candidate.
        """
        return [
            slot.name
            for slot in self.slots
            if slot.required and slot.status in {SLOT_MISSING, SLOT_PARTIAL}
        ]

    @property
    def absent_required_slots(self) -> list[str]:
        """Required slots of which the metadata shows nothing at all.

        This is the line between "the wording is a little off" and "the thing is not
        there". ``barren polar valley landscape`` against a title reading ``barren
        antarctic dry valley rocks`` is the first; ``antarctic research station``
        against an iceberg breaking off Antarctica is the second, and only the second
        may refuse a candidate outright.
        """
        return [slot.name for slot in self.slots if slot.required and slot.status == SLOT_MISSING]

    @property
    def undecidable_required_slots(self) -> list[str]:
        return [slot.name for slot in self.slots if slot.required and slot.status == SLOT_UNDECIDABLE]

    @property
    def conflicting_terms(self) -> list[str]:
        return [term for slot in self.slots if slot.status == SLOT_CONFLICTING for term in slot.evidence_terms]

    @property
    def declared_conflict_terms(self) -> list[str]:
        """Only the softer ``conflicting_context`` hits.

        A ``must_avoid`` hit is reported by the gate that already owns it; repeating it
        here would give one fact two reject reasons.
        """
        return [
            term
            for slot in self.slots
            if slot.note == "declared_conflicting_context"
            for term in slot.evidence_terms
        ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "required_slots": self.required_slots,
            "matched_slots": self.matched_slots,
            "missing_slots": self.missing_slots,
            "missing_required_slots": self.missing_required_slots,
            "absent_required_slots": self.absent_required_slots,
            "conflicting_slots": self.conflicting_slots,
            "undecidable_slots": self.undecidable_slots,
            "verdict": self.verdict,
            "details": [slot.to_dict() for slot in self.slots],
        }


def required_slot_kinds(source_class: str) -> tuple[str, ...]:
    return REQUIRED_SLOT_KINDS.get(str(source_class or ""), DEFAULT_REQUIRED_SLOT_KINDS)


def build_slot_verdict(scene: Any, evidence: CandidateEvidence, *, source_class: str = "") -> SlotVerdict:
    """Judge every requirement the scene states, one slot at a time."""
    required_kinds = required_slot_kinds(source_class or getattr(scene, "source_class", ""))
    slots: list[SlotDecision] = []

    described = (
        (SLOT_SUBJECT, list(getattr(scene, "subject", []) or [])),
        (SLOT_ACTION, list(getattr(scene, "action", []) or [])),
        (SLOT_LOCATION, list(getattr(scene, "location", []) or [])),
        (SLOT_CONTEXT, list(getattr(scene, "context", []) or [])),
    )
    for kind, terms in described:
        if not terms:
            continue
        slots.append(_describe_slot(kind, kind, terms, evidence, required=kind in required_kinds, literal=False))

    # The author's own requirements. Always required, whatever the class, and matched
    # verbatim - this is the same test the existing must_include gate applies.
    for term in list(getattr(scene, "must_include", []) or []):
        slots.append(
            _describe_slot(f"{SLOT_REQUIREMENT}:{term}", SLOT_REQUIREMENT, [term], evidence, required=True, literal=True)
        )

    # ``should_include`` is deliberately not a slot: the planner fills it with the
    # secondary subjects and the place, which are already judged above, and a second
    # copy of the same terms would double every miss.
    slots.extend(_conflict_slots(scene, evidence))
    return SlotVerdict(slots=slots, verdict=_verdict(slots, evidence))


def _describe_slot(
    name: str,
    kind: str,
    terms: list[str],
    evidence: CandidateEvidence,
    *,
    required: bool,
    literal: bool,
) -> SlotDecision:
    matched: list[str] = []
    missing: list[str] = []
    undecidable: list[str] = []
    scores: list[float] = []
    for term in terms:
        text = str(term).strip()
        if not text:
            continue
        if evidence.is_undecidable(text):
            undecidable.append(text)
            continue
        score = (
            evidence.literal_score(text)
            if literal
            else evidence.semantic_stem_score(text)
        )
        scores.append(score)
        (matched if score >= SLOT_MATCH_SCORE else missing).append(text)
    average = sum(scores) / len(scores) if scores else 0.0

    if not scores:
        status = SLOT_UNDECIDABLE
    elif not missing:
        status = SLOT_MATCHED
    elif average >= SLOT_PARTIAL_SCORE:
        status = SLOT_PARTIAL
    else:
        status = SLOT_MISSING
    note = ""
    if status in {SLOT_PARTIAL, SLOT_MISSING} and average > 0:
        # Part of the phrase is in the evidence and the rest is not. For a place this
        # is the continent-instead-of-valley case the stage exists to refuse.
        note = "broader_context_only" if kind == SLOT_LOCATION else "partial_phrase_only"
    return SlotDecision(
        name=name,
        kind=kind,
        required=required,
        terms=[str(term) for term in terms],
        status=status,
        score=average,
        matched_terms=matched,
        missing_terms=missing + undecidable,
        note=note,
    )


def _conflict_slots(scene: Any, evidence: CandidateEvidence) -> list[SlotDecision]:
    """Contradictions the scene's author stated, found verbatim in the metadata.

    Two sources, both explicit. ``must_not_include`` already disqualifies a candidate
    outright and is recorded here so the decision record is complete. ``conflicting
    context`` is the softer statement: material that is *explicitly* something else -
    a Mars mission press day where the scene wants an ordinary laboratory - which
    blocks an automatic full match but can be confirmed by a person.

    Nothing is inferred. A term the author never wrote can never conflict, and metadata
    that simply fails to mention the scene's place is missing evidence, not a conflict.
    """
    slots: list[SlotDecision] = []
    for term in list(getattr(scene, "must_not_include", []) or []):
        text = str(term).strip()
        if text and not evidence.is_undecidable(text) and evidence.contains(text):
            slots.append(
                SlotDecision(
                    name=f"must_avoid:{text}",
                    kind=SLOT_CONFLICT,
                    required=False,
                    terms=[text],
                    status=SLOT_CONFLICTING,
                    score=100.0,
                    evidence_terms=[text],
                    note="must_avoid_present",
                )
            )
    for term in list(getattr(scene, "conflicting_context", []) or []):
        text = str(term).strip()
        if text and not evidence.is_undecidable(text) and evidence.stem_score(text) >= SLOT_MATCH_SCORE:
            slots.append(
                SlotDecision(
                    name=f"conflicting_context:{text}",
                    kind=SLOT_CONFLICT,
                    required=False,
                    terms=[text],
                    status=SLOT_CONFLICTING,
                    score=100.0,
                    evidence_terms=[text],
                    note="declared_conflicting_context",
                )
            )
    return slots


def _verdict(slots: list[SlotDecision], evidence: CandidateEvidence) -> str:
    if any(slot.status == SLOT_CONFLICTING for slot in slots):
        return VERDICT_CONFLICTING
    if not evidence.has_metadata:
        return VERDICT_UNVERIFIED
    judged = [slot for slot in slots if slot.kind != SLOT_CONFLICT]
    if not judged:
        # Nothing was stated and nothing contradicts. The scene constrains nothing,
        # so there is nothing to be incomplete about.
        return VERDICT_COMPLETE
    if any(slot.required and slot.status == SLOT_UNDECIDABLE for slot in judged):
        return VERDICT_UNVERIFIED
    if any(slot.required and slot.status in {SLOT_MISSING, SLOT_PARTIAL} for slot in judged):
        return VERDICT_INCOMPLETE
    if any(slot.status in {SLOT_MISSING, SLOT_PARTIAL} for slot in judged):
        return VERDICT_PARTIAL
    if all(slot.status == SLOT_UNDECIDABLE for slot in judged):
        return VERDICT_UNVERIFIED
    return VERDICT_COMPLETE


def support_status(
    verdict: SlotVerdict,
    *,
    framing_status: str,
    rights_allowed: bool,
    rights_review_required: bool,
    source_class: str = "",
    provider: str = "",
    semantically_disqualified: bool = False,
) -> tuple[str, list[str]]:
    """How much of the scene this candidate actually supports, and what is still owed.

    Returned as ``(status, requirements)``. The requirements are follow-up work, not
    alternative statuses: a partial match that also needs its crop looked at carries
    both, and neither of them makes it render-ready.
    """
    requirements: list[str] = []
    if framing_status == FRAMING_CROP_REVIEW:
        requirements.append(NEEDS_CROP_REVIEW)

    if source_class == CLASS_DATA_INFOGRAPHIC and provider != "generated":
        # There is no footage of a statistic. Whatever a search returned for the words
        # of the figure, it is not the figure.
        return SUPPORT_UNSUPPORTED, requirements

    if semantically_disqualified or framing_status in FRAMING_HARD_REJECT:
        return SUPPORT_UNSUPPORTED, requirements

    missing = verdict.missing_slots
    if len(missing) >= 2:
        requirements.append(NEEDS_MULTI_ASSET)
    if missing:
        requirements.append(NEEDS_ADDITIONAL_ASSET)

    if verdict.verdict == VERDICT_CONFLICTING:
        requirements.append(NEEDS_MANUAL_CONFIRMATION)
        return SUPPORT_MANUAL, _unique(requirements)
    if verdict.verdict == VERDICT_UNVERIFIED:
        return SUPPORT_UNVERIFIED, _unique(requirements)
    if not rights_allowed or rights_review_required:
        requirements.append(NEEDS_RIGHTS_CLEARANCE)
        return SUPPORT_RIGHTS_BLOCKED, _unique(requirements)
    if verdict.verdict in {VERDICT_INCOMPLETE, VERDICT_PARTIAL}:
        return SUPPORT_PARTIAL, _unique(requirements)
    if framing_status == FRAMING_CROP_REVIEW:
        # Every word of the scene is confirmed, and nothing here can say whether the
        # subject survives a 9:16 crop. That question needs the picture, not metadata.
        requirements.append(NEEDS_MANUAL_CONFIRMATION)
        return SUPPORT_MANUAL, _unique(requirements)
    return SUPPORT_FULL, _unique(requirements)


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


@dataclass
class SelectionDecision:
    """The single record that travels from ranking to the manifest and the board.

    Everything a reviewer needs to see why this asset is in this scene, kept together
    so that rebuilding the asset entry after a download cannot silently drop half of it
    - which is exactly what used to happen.
    """

    schema_version: int = DECISION_SCHEMA_VERSION
    scene_id: str = ""
    asset_id: str = ""
    provider: str = ""
    source_class: str = ""
    provider_confidence: float = 0.0
    semantic_score: float = 0.0
    semantic_status: str = ""
    metadata_score: float = 0.0
    metadata_status: str = ""
    technical_score: float = 0.0
    technical_status: str = FRAMING_UNKNOWN
    framing: dict[str, Any] = field(default_factory=dict)
    duration_status: str = ""
    duration: dict[str, Any] = field(default_factory=dict)
    rights_status: str = ""
    rights_allowed_for_render: bool = False
    rights_review_required: bool = False
    slots: dict[str, Any] = field(default_factory=dict)
    slot_verdict: str = VERDICT_UNVERIFIED
    support_status: str = SUPPORT_UNVERIFIED
    support_requirements: list[str] = field(default_factory=list)
    selection_reasons: list[str] = field(default_factory=list)
    reject_reasons: list[str] = field(default_factory=list)

    @property
    def render_ready(self) -> bool:
        """Only a full match on cleared rights with a settled crop is render-ready."""
        return self.support_status == SUPPORT_FULL and not self.support_requirements

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "scene_id": self.scene_id,
            "asset_id": self.asset_id,
            "provider": self.provider,
            "source_class": self.source_class,
            "provider_confidence": round(float(self.provider_confidence), 3),
            "semantic": {
                "score": round(float(self.semantic_score), 3),
                "status": self.semantic_status,
                "metadata_score": round(float(self.metadata_score), 3),
                "metadata_status": self.metadata_status,
            },
            "technical": {
                "score": round(float(self.technical_score), 3),
                "status": self.technical_status,
                "framing": dict(self.framing),
            },
            "duration": {"status": self.duration_status, **dict(self.duration)},
            "rights": {
                "status": self.rights_status,
                "allowed_for_render": bool(self.rights_allowed_for_render),
                "review_required": bool(self.rights_review_required),
            },
            "slots": dict(self.slots),
            "slot_verdict": self.slot_verdict,
            "support_status": self.support_status,
            "support_requirements": list(self.support_requirements),
            "render_ready": self.render_ready,
            "selection_reasons": list(self.selection_reasons),
            "reject_reasons": list(self.reject_reasons),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "SelectionDecision":
        """Read a stored record. An asset written before this stage yields an empty
        decision that says ``unverified`` rather than claiming anything."""
        if not isinstance(data, dict) or not data:
            return cls()
        semantic = data.get("semantic") if isinstance(data.get("semantic"), dict) else {}
        technical = data.get("technical") if isinstance(data.get("technical"), dict) else {}
        duration = dict(data.get("duration") or {}) if isinstance(data.get("duration"), dict) else {}
        rights = data.get("rights") if isinstance(data.get("rights"), dict) else {}
        return cls(
            schema_version=int(data.get("schema_version") or DECISION_SCHEMA_VERSION),
            scene_id=str(data.get("scene_id") or ""),
            asset_id=str(data.get("asset_id") or ""),
            provider=str(data.get("provider") or ""),
            source_class=str(data.get("source_class") or ""),
            provider_confidence=float(data.get("provider_confidence") or 0.0),
            semantic_score=float(semantic.get("score") or 0.0),
            semantic_status=str(semantic.get("status") or ""),
            metadata_score=float(semantic.get("metadata_score") or 0.0),
            metadata_status=str(semantic.get("metadata_status") or ""),
            technical_score=float(technical.get("score") or 0.0),
            technical_status=str(technical.get("status") or FRAMING_UNKNOWN),
            framing=dict(technical.get("framing") or {}),
            duration_status=str(duration.pop("status", "") or ""),
            duration=duration,
            rights_status=str(rights.get("status") or ""),
            rights_allowed_for_render=bool(rights.get("allowed_for_render", False)),
            rights_review_required=bool(rights.get("review_required", False)),
            slots=dict(data.get("slots") or {}),
            slot_verdict=str(data.get("slot_verdict") or VERDICT_UNVERIFIED),
            support_status=str(data.get("support_status") or SUPPORT_UNVERIFIED),
            support_requirements=[str(item) for item in (data.get("support_requirements") or [])],
            selection_reasons=[str(item) for item in (data.get("selection_reasons") or [])],
            reject_reasons=[str(item) for item in (data.get("reject_reasons") or [])],
        )


DECISION_KEY = "selection_decision"


def read_decision(asset: dict[str, Any] | None) -> SelectionDecision:
    """The decision an asset carries, or an empty one for an asset written before it."""
    if not isinstance(asset, dict):
        return SelectionDecision()
    return SelectionDecision.from_dict(asset.get(DECISION_KEY))


def has_decision(asset: dict[str, Any] | None) -> bool:
    return isinstance(asset, dict) and isinstance(asset.get(DECISION_KEY), dict) and bool(asset[DECISION_KEY])


def carry_decision(source: dict[str, Any] | None, target: dict[str, Any]) -> dict[str, Any]:
    """Copy the decision from a ranked candidate onto the asset record that replaces it.

    ``_ensure_selected_asset_downloaded`` rebuilds the selected asset out of what the
    provider returned from ``download``, which knows nothing about why the asset was
    chosen. Without this the whole decision was lost between selection and the
    manifest, and the review board had to guess it back out of ``ranked_candidates``.
    """
    if has_decision(source) and not has_decision(target):
        target[DECISION_KEY] = dict(source[DECISION_KEY])  # type: ignore[index]
    for key in ("support_status", "slot_verdict"):
        if isinstance(source, dict) and source.get(key) and not target.get(key):
            target[key] = source[key]
    return target


def validate_decision(decision: SelectionDecision) -> list[str]:
    """Machine-readable inconsistencies in a stored decision.

    A decision is the thing later stages trust, so it has to be checkable on its own:
    a record claiming a full match while listing a missing requirement is worse than no
    record at all.
    """
    problems: list[str] = []
    slots = decision.slots if isinstance(decision.slots, dict) else {}
    missing_required = [str(item) for item in (slots.get("missing_required_slots") or [])]
    conflicting = [str(item) for item in (slots.get("conflicting_slots") or [])]
    if decision.support_status == SUPPORT_FULL and (missing_required or slots.get("absent_required_slots")):
        problems.append("full_support_with_missing_required_slot")
    if decision.support_status == SUPPORT_FULL and conflicting:
        problems.append("full_support_with_conflicting_slot")
    if decision.support_status == SUPPORT_FULL and decision.slot_verdict != VERDICT_COMPLETE:
        problems.append("full_support_without_complete_verdict")
    if decision.support_status == SUPPORT_FULL and decision.technical_status == FRAMING_CROP_REVIEW:
        problems.append("full_support_with_unreviewed_crop")
    if decision.render_ready and decision.support_status != SUPPORT_FULL:
        problems.append("render_ready_without_full_support")
    if decision.support_status == SUPPORT_PARTIAL and decision.render_ready:
        problems.append("partial_support_marked_render_ready")
    if NEEDS_CROP_REVIEW in decision.support_requirements and decision.technical_status != FRAMING_CROP_REVIEW:
        problems.append("crop_review_requirement_without_crop_review_status")
    return problems


def scene_resolution_status(
    *,
    selected: dict[str, Any] | None,
    candidates: list[dict[str, Any]] | None = None,
    source_class: str = "",
    manual_request: bool = False,
) -> str:
    """One machine-readable answer for what happened to a scene."""
    if manual_request:
        return MANUAL_ACTION_REQUIRED
    if selected:
        decision = read_decision(selected)
        if decision.support_status in {SUPPORT_FULL, ""}:
            return RESOLVED
        return RESOLVED_NEEDS_REVIEW
    items = candidates or []
    if not items:
        return UNRESOLVED_NO_CANDIDATE
    if source_class == CLASS_DATA_INFOGRAPHIC:
        return UNRESOLVED_GENERATOR_FAILED
    statuses = {read_decision(item).support_status for item in items}
    if SUPPORT_RIGHTS_BLOCKED in statuses:
        return UNRESOLVED_RIGHTS_BLOCKED
    return UNRESOLVED_UNVERIFIED


def framing_decision(
    candidate: dict[str, Any],
    *,
    target_aspect_ratio: str = "9:16",
    min_short_edge: int = 540,
    output_width: int = 1080,
    output_height: int = 1920,
    max_source_aspect_ratio: float = 3.0,
) -> dict[str, Any]:
    """What is left of this asset after cropping it to the target aspect ratio.

    Reported for every candidate, and disqualifying only when the crop cannot fill the
    frame. This is deliberately not a score: no amount of semantic relevance makes a
    405-pixel-wide strip usable in a 1080-wide video.

    The one thing it refuses to claim is that the *subject* survives the crop. Nothing
    here has looked at the picture, so a frame that has to be cropped at all comes back
    as ``crop_review_required``, and only a frame already at the target ratio is called
    ``vertical_ready``.
    """
    width = _int(candidate.get("width"))
    height = _int(candidate.get("height"))
    ratio = _aspect_ratio(target_aspect_ratio)
    media_type = str(candidate.get("media_type") or candidate.get("type") or "")
    base = {
        "status": FRAMING_UNKNOWN,
        "target_aspect_ratio": target_aspect_ratio,
        "source_width": width,
        "source_height": height,
        "source_aspect_ratio": round(width / height, 4) if width and height else 0.0,
        "effective_width": 0,
        "effective_height": 0,
        "min_short_edge": min_short_edge,
        "expected_output_width": output_width,
        "expected_output_height": output_height,
        "upscale_factor": 0.0,
        "pan_zoom_possible": False,
        "render_ready": False,
        "reason": "",
    }
    if not width or not height or ratio <= 0:
        base["reason"] = "dimensions_unknown"
        return base

    source_ratio = width / height
    if source_ratio > ratio:
        effective_height = height
        effective_width = int(height * ratio)
    else:
        effective_width = width
        effective_height = int(width / ratio)
    upscale = round(output_width / effective_width, 3) if effective_width else 0.0
    base.update(
        {
            "effective_width": effective_width,
            "effective_height": effective_height,
            "upscale_factor": upscale,
            # A still that is wider or taller than the crop can be moved inside it; a
            # clip cannot without a motion pass this stage does not own.
            "pan_zoom_possible": media_type == "image" and (width > effective_width or height > effective_height),
        }
    )

    if source_ratio > max_source_aspect_ratio:
        base["status"] = FRAMING_ASPECT_MISMATCH
        base["reason"] = f"source_aspect_{source_ratio:.2f}_beyond_{max_source_aspect_ratio}"
        return base
    if effective_width < min_short_edge:
        crop_removed = effective_width < width
        base["status"] = FRAMING_LOW_RESOLUTION if crop_removed else FRAMING_REJECTED
        base["reason"] = "crop_leaves_too_few_pixels" if crop_removed else "source_resolution_too_low"
        return base
    if abs(source_ratio - ratio) <= ratio * 0.02:
        base["status"] = FRAMING_VERTICAL_READY
        base["render_ready"] = True
        base["reason"] = "already_at_target_aspect_ratio"
        return base
    base["status"] = FRAMING_CROP_REVIEW
    base["reason"] = "composition_after_crop_not_verifiable_from_metadata"
    return base


def _aspect_ratio(value: str) -> float:
    try:
        left, right = str(value).split(":", 1)
        return float(left) / float(right)
    except (ValueError, ZeroDivisionError):
        return 0.0


def _int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


__all__ = [
    "DECISION_KEY",
    "DECISION_SCHEMA_VERSION",
    "EXACTING_CLASSES",
    "FRAMING_ASPECT_MISMATCH",
    "FRAMING_CROP_REVIEW",
    "FRAMING_HARD_REJECT",
    "FRAMING_LOW_RESOLUTION",
    "FRAMING_REJECTED",
    "FRAMING_UNKNOWN",
    "FRAMING_VERTICAL_READY",
    "MANUAL_ACTION_REQUIRED",
    "NEEDS_ADDITIONAL_ASSET",
    "NEEDS_CROP_REVIEW",
    "NEEDS_MANUAL_CONFIRMATION",
    "NEEDS_MULTI_ASSET",
    "NEEDS_RIGHTS_CLEARANCE",
    "REQUIRED_SLOT_KINDS",
    "RESOLVED",
    "RESOLVED_NEEDS_REVIEW",
    "SLOT_ACTION",
    "SLOT_CONFLICT",
    "SLOT_CONFLICTING",
    "SLOT_CONTEXT",
    "SLOT_LOCATION",
    "SLOT_MATCHED",
    "SLOT_MISSING",
    "SLOT_PARTIAL",
    "SLOT_REQUIREMENT",
    "SLOT_SUBJECT",
    "SLOT_SUPPORTING",
    "SLOT_UNDECIDABLE",
    "SUPPORT_FULL",
    "SUPPORT_MANUAL",
    "SUPPORT_PARTIAL",
    "SUPPORT_RIGHTS_BLOCKED",
    "SUPPORT_UNSUPPORTED",
    "SUPPORT_UNVERIFIED",
    "UNRESOLVED_GENERATOR_FAILED",
    "UNRESOLVED_NO_CANDIDATE",
    "UNRESOLVED_RIGHTS_BLOCKED",
    "UNRESOLVED_UNVERIFIED",
    "VERDICT_COMPLETE",
    "VERDICT_CONFLICTING",
    "VERDICT_INCOMPLETE",
    "VERDICT_PARTIAL",
    "VERDICT_UNVERIFIED",
    "SelectionDecision",
    "SlotDecision",
    "SlotVerdict",
    "build_slot_verdict",
    "carry_decision",
    "framing_decision",
    "has_decision",
    "read_decision",
    "required_slot_kinds",
    "scene_resolution_status",
    "support_status",
    "validate_decision",
]
