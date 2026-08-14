"""Completion modes, quality tiers, and the several different meanings of "ready".

Why this module exists
----------------------
Until stage Q2.2B the project had exactly one answer to "may this asset be used":
``SelectionDecision.render_ready``, which is true only for a full match on cleared
rights with a settled crop. Everything else became ``unresolved``, and one unresolved
scene stopped the whole video. For an eight-scene short assembled from stock libraries
that is almost always at least one scene, so the honest gate produced no video at all.

The gate was not wrong; it was answering the wrong number of questions. "Can this be
shown in a draft the author is about to review" and "can this be published" are
different questions with different answers, and collapsing them into one flag is what
made autonomous completion impossible.

So readiness is split here into named, independently-checkable facts:

``usable_in_draft``                 may appear in a draft render
``automatic_render_allowed``        may be chosen automatically with no human involved
``publish_ready``                   may go out as-is
``manual_replacement_recommended``  works, but the author should look at it
``manual_replacement_required``     a stand-in; the author has to decide
``blocked`` + ``block_reasons``     may never be used, in any mode

What this module deliberately does not do
-----------------------------------------
It does not look at the picture and it does not lower any existing bar. Every fact it
reads was already established by ``src.assets.semantic_selection.decision`` and the
licence policy. The only new thing is that a *partial* match, on cleared rights, with a
usable file and no stated contradiction, is now allowed to be in a draft - flagged, with
a replacement recommendation, and never called publish-ready.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

from src.assets.models import RIGHTS_ALLOWED_STATUSES, RIGHTS_LEGACY_CLEARED
from src.assets.scene_strategy import CLASS_DATA_INFOGRAPHIC
from src.assets.semantic_selection.decision import (
    DECISION_KEY,
    FRAMING_CROP_REVIEW,
    FRAMING_HARD_REJECT,
    NEEDS_CROP_REVIEW,
    NEEDS_MANUAL_CONFIRMATION,
    NEEDS_RIGHTS_CLEARANCE,
    SUPPORT_FULL,
    SUPPORT_MANUAL,
    SUPPORT_PARTIAL,
    SUPPORT_RIGHTS_BLOCKED,
    SUPPORT_UNSUPPORTED,
    SUPPORT_UNVERIFIED,
    VERDICT_CONFLICTING,
    read_decision,
)

COMPLETION_SCHEMA_VERSION = 1

# --- Completion modes --------------------------------------------------------
# ``strict`` is the behaviour every command and every existing project had before this
# stage, and stays the default everywhere. ``draft_complete`` is opt-in.
MODE_STRICT = "strict"
MODE_DRAFT_COMPLETE = "draft_complete"
COMPLETION_MODES = (MODE_STRICT, MODE_DRAFT_COMPLETE)
DEFAULT_COMPLETION_MODE = MODE_STRICT

# --- Quality tiers -----------------------------------------------------------
# How the material answers the scene. Additional to, never a replacement for, the
# support status and the rights verdict: a tier says how good the answer is, the
# support status says what was actually checked, and rights say what is allowed.
TIER_EXACT = "A_exact"
TIER_COMPOSITE = "B_composite"
TIER_GOOD_CONTEXT = "C_good_context"
TIER_PARTIAL = "D_partial"
TIER_GENERATED = "E_generated"
TIER_EMERGENCY = "F_emergency"
TIER_NONE = ""

QUALITY_TIERS = (TIER_EXACT, TIER_COMPOSITE, TIER_GOOD_CONTEXT, TIER_PARTIAL, TIER_GENERATED, TIER_EMERGENCY)

# Best first. Used for ordering and for reports, never as a score.
TIER_RANK: dict[str, int] = {
    TIER_EXACT: 0,
    TIER_COMPOSITE: 1,
    TIER_GOOD_CONTEXT: 2,
    TIER_PARTIAL: 3,
    TIER_GENERATED: 4,
    TIER_EMERGENCY: 5,
    TIER_NONE: 6,
}

# --- Replacement priority ----------------------------------------------------
PRIORITY_NONE = "none"
PRIORITY_LOW = "low"
PRIORITY_MEDIUM = "medium"
PRIORITY_HIGH = "high"
PRIORITY_CRITICAL = "critical"

PRIORITY_RANK: dict[str, int] = {
    PRIORITY_CRITICAL: 0,
    PRIORITY_HIGH: 1,
    PRIORITY_MEDIUM: 2,
    PRIORITY_LOW: 3,
    PRIORITY_NONE: 4,
}

_TIER_PRIORITY: dict[str, str] = {
    TIER_EXACT: PRIORITY_NONE,
    TIER_COMPOSITE: PRIORITY_LOW,
    TIER_GOOD_CONTEXT: PRIORITY_LOW,
    TIER_GENERATED: PRIORITY_NONE,
    TIER_PARTIAL: PRIORITY_MEDIUM,
    TIER_EMERGENCY: PRIORITY_HIGH,
}

# --- Blocking reasons --------------------------------------------------------
# The complete list of reasons material may not be used *even in a draft*. Nothing
# outside this list blocks: "not proven to be the named place" is a reason to flag a
# fragment for replacement, not a reason to refuse to make the video.
BLOCK_RIGHTS = "rights_blocked"
BLOCK_TECHNICAL = "technical_blocked"
BLOCK_MISSING_FILE = "no_usable_media_file"
BLOCK_MUST_AVOID = "must_avoid_violation"
BLOCK_FACTUALLY_MISLEADING = "factually_misleading"
BLOCK_USER_CONSTRAINT = "user_constraint_violation"

BLOCK_REASONS = (
    BLOCK_RIGHTS,
    BLOCK_TECHNICAL,
    BLOCK_MISSING_FILE,
    BLOCK_MUST_AVOID,
    BLOCK_FACTUALLY_MISLEADING,
    BLOCK_USER_CONSTRAINT,
)

# Support statuses that describe material which answers *something* about the scene.
# ``unverified`` is deliberately absent.  "Nothing in metadata contradicts this clip"
# is not evidence that the clip belongs in the scene; admitting it would turn the last
# rung into random provider footage instead of the safe project-owned backdrop.
_DRAFTABLE_SUPPORT = frozenset({SUPPORT_FULL, SUPPORT_PARTIAL, SUPPORT_MANUAL})
# ``cleared`` is the pre-schema spelling still carried by generated story-card
# evidence.  It is explicit permission, unlike ``legacy_unknown`` or an empty value.
# This is the only sanctioned extension of the canonical vocabulary, and it is
# local to this gate: the owner declares the spelling but deliberately keeps it
# out of ``RIGHTS_ALLOWED_STATUSES``.  Pinned by tests/test_rights_status_vocabulary.py.
_ALLOWED_RIGHTS_STATUSES = frozenset({*RIGHTS_ALLOWED_STATUSES, RIGHTS_LEGACY_CLEARED})


@dataclass
class UsabilityVerdict:
    """What one asset may be used for, in one scene, under one completion mode."""

    usable_in_draft: bool = False
    automatic_render_allowed: bool = False
    publish_ready: bool = False
    manual_replacement_recommended: bool = False
    manual_replacement_required: bool = False
    blocked: bool = False
    rights_blocked: bool = False
    technical_blocked: bool = False
    factually_misleading: bool = False
    must_avoid_blocked: bool = False
    block_reasons: list[str] = field(default_factory=list)
    replacement_priority: str = PRIORITY_NONE
    quality_tier: str = TIER_NONE
    support_status: str = ""
    limitations: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "usable_in_draft": bool(self.usable_in_draft),
            "automatic_render_allowed": bool(self.automatic_render_allowed),
            "publish_ready": bool(self.publish_ready),
            "manual_replacement_recommended": bool(self.manual_replacement_recommended),
            "manual_replacement_required": bool(self.manual_replacement_required),
            "blocked": bool(self.blocked),
            "rights_blocked": bool(self.rights_blocked),
            "technical_blocked": bool(self.technical_blocked),
            "factually_misleading": bool(self.factually_misleading),
            "must_avoid_blocked": bool(self.must_avoid_blocked),
            "block_reasons": list(self.block_reasons),
            "replacement_priority": self.replacement_priority,
            "quality_tier": self.quality_tier,
            "support_status": self.support_status,
            "limitations": list(self.limitations),
            "reasons": list(self.reasons),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "UsabilityVerdict":
        data = data if isinstance(data, dict) else {}
        block_reasons = [str(item) for item in (data.get("block_reasons") or [])]
        return cls(
            usable_in_draft=bool(data.get("usable_in_draft", False)),
            automatic_render_allowed=bool(data.get("automatic_render_allowed", False)),
            publish_ready=bool(data.get("publish_ready", False)),
            manual_replacement_recommended=bool(data.get("manual_replacement_recommended", False)),
            manual_replacement_required=bool(data.get("manual_replacement_required", False)),
            blocked=bool(data.get("blocked", False) or block_reasons),
            rights_blocked=bool(data.get("rights_blocked", False) or BLOCK_RIGHTS in block_reasons),
            technical_blocked=bool(
                data.get("technical_blocked", False)
                or BLOCK_TECHNICAL in block_reasons
                or BLOCK_MISSING_FILE in block_reasons
            ),
            factually_misleading=bool(
                data.get("factually_misleading", False)
                or BLOCK_FACTUALLY_MISLEADING in block_reasons
            ),
            must_avoid_blocked=bool(
                data.get("must_avoid_blocked", False) or BLOCK_MUST_AVOID in block_reasons
            ),
            block_reasons=block_reasons,
            replacement_priority=str(data.get("replacement_priority") or PRIORITY_NONE),
            quality_tier=str(data.get("quality_tier") or TIER_NONE),
            support_status=str(data.get("support_status") or ""),
            limitations=[str(item) for item in (data.get("limitations") or [])],
            reasons=[str(item) for item in (data.get("reasons") or [])],
        )


def normalize_mode(value: str | None) -> str:
    """A mode string, or the strict default. An unknown value never silently relaxes."""
    text = str(value or "").strip().lower()
    return text if text in COMPLETION_MODES else DEFAULT_COMPLETION_MODE


def blocking_reasons(
    candidate: dict[str, Any] | None,
    *,
    require_local_file: bool = False,
    fresh_local_file_validation: bool = False,
) -> list[str]:
    """Why this material may never be used, in any mode. Empty means it may.

    Mode-independent on purpose: ``draft_complete`` lowers the bar for *how well* a
    frame has to answer a scene, never for rights, file integrity, a stated
    contradiction, or a claim the evidence refutes.
    """
    if not isinstance(candidate, dict) or not candidate:
        return [BLOCK_MISSING_FILE]
    decision = read_decision(candidate)
    reasons: list[str] = []

    # --- rights -------------------------------------------------------------
    # A manifest carries compatibility copies of the rights verdict at the asset root,
    # inside ``license``, inside ``policy_decision``, and in the semantic decision.
    # They must never be alternatives where the most permissive copy wins.  Every
    # explicitly present record has veto power; at least one must positively establish
    # an allowed status.  This also makes stale/tampered mixed-schema records fail closed.
    if not _rights_are_allowed(candidate):
        reasons.append(BLOCK_RIGHTS)

    # --- technical ----------------------------------------------------------
    framing_status = str(decision.technical_status or candidate.get("framing_status") or "")
    if framing_status in FRAMING_HARD_REJECT:
        reasons.append(BLOCK_TECHNICAL)
    validation = candidate.get("technical_validation")
    validation_status = (
        str(validation.get("status") or "").strip().lower()
        if isinstance(validation, dict)
        else ""
    )
    if validation_status == "failed":
        reasons.append(BLOCK_TECHNICAL)
    if require_local_file:
        local_path = _local_path(candidate)
        if not local_path or not _is_file(local_path):
            reasons.append(BLOCK_MISSING_FILE)
        # The render gate asks for a real file, so "validation absent" is not success.
        # Search-time candidates intentionally do not use this stricter branch: their
        # provider download has not happened yet.
        if validation_status != "passed":
            reasons.append(BLOCK_TECHNICAL)
        elif local_path and _is_file(local_path) and not _local_file_is_valid(
            candidate,
            local_path,
            validation=validation if isinstance(validation, dict) else {},
            fresh=fresh_local_file_validation,
        ):
            # A stored ``passed`` record is evidence about the bytes that were imported,
            # not a permanent permission for whatever currently occupies that path.
            # Non-final gates may reuse a stat-keyed validation; the final renderer
            # explicitly bypasses it because filesystem metadata is not byte identity.
            reasons.append(BLOCK_TECHNICAL)

    # --- stated contradictions ---------------------------------------------
    reject_reasons = _reject_reasons(candidate, decision)
    decision_slots = decision.slots if isinstance(decision.slots, dict) else {}
    conflicting_slots = [
        str(item).strip()
        for item in (decision_slots.get("conflicting_slots") or [])
        if str(item).strip()
    ]
    if any(reason.startswith("must_avoid_match:") or reason == "vision_mismatch" for reason in reject_reasons):
        reasons.append(BLOCK_MUST_AVOID)
    if any(name.startswith("must_avoid:") for name in conflicting_slots):
        reasons.append(BLOCK_MUST_AVOID)
    if any(
        reason == "ambiguous_whale_for_orca_scene"
        or reason == "missing_orca_evidence_for_orca_scene"
        or reason.startswith("non_real_video_footage:")
        for reason in reject_reasons
    ):
        reasons.append(BLOCK_FACTUALLY_MISLEADING)
    if conflicting_slots or decision.slot_verdict == VERDICT_CONFLICTING or any(
        reason.startswith("conflicting_context:") for reason in reject_reasons
    ):
        # The author declared this material to be explicitly something else. Showing it
        # under this narration would be a documentary claim the project cannot make.
        reasons.append(BLOCK_FACTUALLY_MISLEADING)
    if decision.semantic_status == "mismatched":
        reasons.append(BLOCK_FACTUALLY_MISLEADING)
    if decision.support_status == SUPPORT_UNSUPPORTED and BLOCK_TECHNICAL not in reasons:
        # ``unsupported`` on a data figure means a search answered a statistic with
        # footage; anywhere else it means the evidence points at a different thing.
        reasons.append(BLOCK_FACTUALLY_MISLEADING)
    if decision.source_class == CLASS_DATA_INFOGRAPHIC and str(candidate.get("provider") or "") != "generated":
        reasons.append(BLOCK_FACTUALLY_MISLEADING)

    return list(dict.fromkeys(reasons))


def evaluate_usability(
    candidate: dict[str, Any] | None,
    *,
    mode: str = DEFAULT_COMPLETION_MODE,
    quality_tier: str = TIER_NONE,
    require_local_file: bool = False,
    fresh_local_file_validation: bool = False,
    reuse_count: int = 0,
) -> UsabilityVerdict:
    """The full readiness answer for one candidate in one scene.

    ``quality_tier`` is supplied by the fallback ladder, which is the only place that
    knows *why* this candidate was reached. It affects the replacement priority and
    whether the fragment is a stand-in, never whether the material is legal or true.
    """
    mode = normalize_mode(mode)
    blocks = blocking_reasons(
        candidate,
        require_local_file=require_local_file,
        fresh_local_file_validation=fresh_local_file_validation,
    )
    decision = read_decision(candidate if isinstance(candidate, dict) else None)
    support = decision.support_status or ""
    verdict = UsabilityVerdict(support_status=support, quality_tier=quality_tier)

    if blocks:
        verdict.blocked = True
        verdict.block_reasons = blocks
        verdict.rights_blocked = BLOCK_RIGHTS in blocks
        verdict.technical_blocked = BLOCK_TECHNICAL in blocks or BLOCK_MISSING_FILE in blocks
        verdict.factually_misleading = BLOCK_FACTUALLY_MISLEADING in blocks
        verdict.must_avoid_blocked = BLOCK_MUST_AVOID in blocks
        verdict.replacement_priority = PRIORITY_CRITICAL
        verdict.manual_replacement_required = True
        verdict.reasons = [f"blocked:{reason}" for reason in blocks]
        return verdict

    requirements = list(decision.support_requirements)
    verdict.limitations = _limitations(decision)

    # Everything the strict path already allowed, unchanged.
    automatic = support == SUPPORT_FULL and not requirements
    verdict.automatic_render_allowed = automatic
    verdict.publish_ready = automatic and quality_tier != TIER_EMERGENCY

    if mode == MODE_STRICT:
        verdict.usable_in_draft = automatic
        verdict.manual_replacement_recommended = not automatic
        verdict.manual_replacement_required = not automatic
        verdict.replacement_priority = PRIORITY_NONE if automatic else PRIORITY_HIGH
        verdict.reasons.append(f"strict_mode:{'accepted' if automatic else 'manual_decision_required'}")
        return verdict

    # draft_complete: partial support, cleared rights, a valid file and no stated
    # contradiction is enough to appear in a draft - and never enough to publish.
    draftable = support in _DRAFTABLE_SUPPORT
    verdict.usable_in_draft = draftable
    verdict.automatic_render_allowed = draftable
    if not draftable:
        verdict.replacement_priority = PRIORITY_CRITICAL
        verdict.manual_replacement_required = True
        verdict.reasons.append("draft_mode:no_support_status")
        return verdict

    verdict.manual_replacement_required = quality_tier == TIER_EMERGENCY
    verdict.manual_replacement_recommended = not verdict.publish_ready and not verdict.manual_replacement_required
    verdict.replacement_priority = replacement_priority(
        quality_tier=quality_tier,
        support_status=support,
        publish_ready=verdict.publish_ready,
        reuse_count=reuse_count,
    )
    verdict.reasons.append(f"draft_mode:{support or 'unknown'}")
    if quality_tier:
        verdict.reasons.append(f"tier:{quality_tier}")
    if reuse_count > 0:
        verdict.reasons.append(f"reused_times:{reuse_count}")
    return verdict


def replacement_priority(
    *,
    quality_tier: str,
    support_status: str,
    publish_ready: bool,
    reuse_count: int = 0,
) -> str:
    """How urgently a human should look at this fragment."""
    if publish_ready and reuse_count <= 1:
        return PRIORITY_NONE
    base = _TIER_PRIORITY.get(quality_tier, PRIORITY_MEDIUM)
    if support_status in {SUPPORT_UNVERIFIED, SUPPORT_MANUAL, SUPPORT_RIGHTS_BLOCKED}:
        base = _raise_priority(base)
    if reuse_count >= 2:
        base = _raise_priority(base)
    return base


def _raise_priority(value: str) -> str:
    order = [PRIORITY_NONE, PRIORITY_LOW, PRIORITY_MEDIUM, PRIORITY_HIGH, PRIORITY_CRITICAL]
    try:
        index = order.index(value)
    except ValueError:
        return PRIORITY_MEDIUM
    return order[min(index + 1, len(order) - 1)]


def _limitations(decision: Any) -> list[str]:
    """What this material does *not* answer, in codes the report can print."""
    limitations: list[str] = []
    slots = decision.slots if isinstance(decision.slots, dict) else {}
    for name in slots.get("missing_required_slots") or []:
        limitations.append(f"missing_required:{name}")
    for name in slots.get("missing_slots") or []:
        code = f"missing:{name}"
        if f"missing_required:{name}" not in limitations and code not in limitations:
            limitations.append(code)
    for name in slots.get("undecidable_slots") or []:
        limitations.append(f"unverifiable:{name}")
    if NEEDS_CROP_REVIEW in decision.support_requirements or decision.technical_status == FRAMING_CROP_REVIEW:
        limitations.append("crop_not_verified")
    if NEEDS_MANUAL_CONFIRMATION in decision.support_requirements:
        limitations.append("needs_manual_confirmation")
    if NEEDS_RIGHTS_CLEARANCE in decision.support_requirements:
        limitations.append("needs_rights_clearance")
    return list(dict.fromkeys(limitations))


def _reject_reasons(candidate: dict[str, Any], decision: Any) -> list[str]:
    reasons = list(decision.reject_reasons)
    raw = candidate.get("reject_reason")
    if isinstance(raw, str) and raw:
        reasons.extend(part for part in raw.split(";") if part)
    reasons.extend(str(item) for item in (candidate.get("blocking_reject_reasons") or []))
    return list(dict.fromkeys(reasons))


def _rights_are_allowed(candidate: dict[str, Any]) -> bool:
    """Resolve all stored rights copies conservatively.

    A positive root-level flag must not erase a blocked policy decision (or vice versa).
    Records are only considered when they actually carry the relevant key, preserving
    compatibility with older manifests that have one canonical root-level declaration.
    """

    license_value = candidate.get("license")
    if isinstance(license_value, dict):
        license_name = str(
            license_value.get("license_name") or license_value.get("name") or ""
        ).strip()
    else:
        license_name = str(candidate.get("license_name") or license_value or "").strip()
    if not license_name or license_name.lower() in {"unknown", "legacy_unknown", "unconfirmed"}:
        return False

    records: list[dict[str, Any]] = []
    root = {
        key: candidate[key]
        for key in ("rights_status", "allowed_for_render", "review_required")
        if key in candidate
    }
    if root:
        records.append(root)

    license_data = candidate.get("license")
    if isinstance(license_data, dict):
        record = {
            key: license_data[key]
            for key in ("rights_status", "allowed_for_render", "review_required")
            if key in license_data
        }
        if record:
            records.append(record)

    policy = candidate.get("policy_decision")
    if isinstance(policy, dict) and policy:
        record = {
            key: policy[key]
            for key in ("allowed_for_render", "review_required", "status")
            if key in policy
        }
        if record:
            records.append(record)

    stored_decision = candidate.get(DECISION_KEY)
    if isinstance(stored_decision, dict) and stored_decision:
        rights = stored_decision.get("rights")
        if isinstance(rights, dict):
            record = {
                key: rights[key]
                for key in ("status", "allowed_for_render", "review_required")
                if key in rights
            }
            if record:
                records.append(record)

    if not records:
        return False

    has_positive_status = False
    has_positive_permission = False
    for record in records:
        if "allowed_for_render" in record:
            # JSON booleans are part of the rights contract. Values such as the string
            # ``"false"`` must not become truthy through Python coercion at this final
            # safety boundary.
            if record["allowed_for_render"] is not True:
                return False
            has_positive_permission = True
        if "review_required" in record and record["review_required"] is not False:
            return False

        policy_status = str(record.get("status") or "").strip().lower()
        if policy_status:
            # A semantic decision calls this field the rights status; a policy record
            # calls it allowed/blocked/review_required.
            if policy_status in _ALLOWED_RIGHTS_STATUSES:
                has_positive_status = True
            elif policy_status == "allowed":
                has_positive_permission = True
            else:
                return False

        rights_status = str(record.get("rights_status") or "").strip().lower()
        if rights_status:
            if rights_status not in _ALLOWED_RIGHTS_STATUSES:
                return False
            has_positive_status = True

    return has_positive_permission and has_positive_status


def _is_file(value: str) -> bool:
    try:
        return Path(value).is_file()
    except (OSError, ValueError):
        return False


def _local_file_is_valid(
    candidate: dict[str, Any],
    local_path: str,
    *,
    validation: dict[str, Any],
    fresh: bool = False,
) -> bool:
    """Verify local bytes, optionally bypassing metadata-keyed validation cache."""

    try:
        path = Path(local_path)
        stat = path.stat()
        if not path.is_file() or stat.st_size <= 0:
            return False
        media_type = _media_type_for_validation(candidate, validation, path)
        if not media_type:
            return False
        validator = (
            _validate_local_file_uncached
            if fresh
            else _validate_local_file_cached
        )
        actual_checksum, technically_valid = validator(
            str(path.resolve()),
            media_type,
            int(stat.st_size),
            int(stat.st_mtime_ns),
        )
    except (OSError, RuntimeError, ValueError):
        return False
    if not technically_valid:
        return False

    # Root and provenance copies are both part of the manifest contract. If both are
    # present, neither may disagree with the bytes handed to the renderer.
    expected_checksums = _stored_checksums(candidate)
    return all(value == actual_checksum for value in expected_checksums)


@lru_cache(maxsize=512)
def _validate_local_file_cached(
    resolved_path: str,
    media_type: str,
    file_size: int,
    modified_ns: int,
) -> tuple[str, bool]:
    """Reuse checksum + decode verdict when ordinary filesystem metadata differs.

    ``file_size`` and ``modified_ns`` intentionally participate in the cache key. They
    avoid another checksum/Pillow/FFprobe pass for ordinary unchanged assets. The final
    render boundary does not trust these metadata as byte identity and bypasses this
    cache through ``_validate_local_file_uncached``.
    """

    return _validate_local_file_uncached(
        resolved_path, media_type, file_size, modified_ns
    )


def _validate_local_file_uncached(
    resolved_path: str,
    media_type: str,
    file_size: int,
    modified_ns: int,
) -> tuple[str, bool]:
    """Decode and hash the bytes currently stored at ``resolved_path``."""

    del file_size, modified_ns
    try:
        # Imported lazily so completion-mode schema imports cannot create a cycle with
        # provider/download modules.
        from src.assets.download import sha256_file, validate_local_asset

        facts = validate_local_asset(resolved_path, media_type)
        if str(facts.get("status") or "").strip().lower() != "passed":
            return "", False
        return sha256_file(resolved_path).strip().lower(), True
    except Exception:
        # ProviderValidationError is the expected failure, but the render authorization
        # boundary is deliberately fail-closed for missing decoders and OS errors too.
        return "", False


def _stored_checksums(candidate: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for raw in (
        candidate.get("checksum_sha256"),
        (
            candidate.get("provenance", {}).get("checksum_sha256")
            if isinstance(candidate.get("provenance"), dict)
            else ""
        ),
    ):
        text = str(raw or "").strip().lower()
        if text and text not in values:
            values.append(text)
    return values


def _media_type_for_validation(
    candidate: dict[str, Any],
    validation: dict[str, Any],
    path: Path,
) -> str:
    for raw in (
        candidate.get("media_type"),
        candidate.get("type"),
        validation.get("media_type"),
    ):
        value = str(raw or "").strip().lower()
        if value in {"image", "video"}:
            return value
    suffix = path.suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tif", ".tiff"}:
        return "image"
    if suffix in {".mp4", ".mov", ".m4v", ".webm", ".ogv", ".ogg"}:
        return "video"
    return ""


def _local_path(candidate: dict[str, Any]) -> str:
    for key in ("path", "local_path", "downloaded_path"):
        value = candidate.get(key)
        if value:
            return str(value)
    return ""


__all__ = [
    "BLOCK_FACTUALLY_MISLEADING",
    "BLOCK_MISSING_FILE",
    "BLOCK_MUST_AVOID",
    "BLOCK_REASONS",
    "BLOCK_RIGHTS",
    "BLOCK_TECHNICAL",
    "BLOCK_USER_CONSTRAINT",
    "COMPLETION_MODES",
    "COMPLETION_SCHEMA_VERSION",
    "DEFAULT_COMPLETION_MODE",
    "MODE_DRAFT_COMPLETE",
    "MODE_STRICT",
    "PRIORITY_CRITICAL",
    "PRIORITY_HIGH",
    "PRIORITY_LOW",
    "PRIORITY_MEDIUM",
    "PRIORITY_NONE",
    "PRIORITY_RANK",
    "QUALITY_TIERS",
    "TIER_COMPOSITE",
    "TIER_EMERGENCY",
    "TIER_EXACT",
    "TIER_GENERATED",
    "TIER_GOOD_CONTEXT",
    "TIER_NONE",
    "TIER_PARTIAL",
    "TIER_RANK",
    "UsabilityVerdict",
    "blocking_reasons",
    "evaluate_usability",
    "normalize_mode",
    "replacement_priority",
]
