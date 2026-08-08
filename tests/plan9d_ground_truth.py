"""Offline ground-truth benchmark for the existing asset decision path (PLAN-9D-A).

Why this module exists
----------------------
PLAN-9D has to prove that Vision evidence *improves* the decision path, on data
that already exists. It cannot be proved against the only real Vision run in the
repository: that run covers three scenes and six candidates, none of which has a
strong metadata-only answer, so there is nothing there that a change could make
worse. A claim of improvement needs a benchmark that can also show a regression.

This module owns the offline benchmark's data contract and its measurement, and
nothing else. Three properties are deliberate:

*The ground truth is human, frozen and independent.* Nothing here decides which
candidate is right. The corpus is selected by *technical* category, the
candidates are blinded, and the owner records the preference once. Only then is
anything measured, and the measurement never writes back into the annotations.

*After that single annotation pass the benchmark is fully automatic.* The
harness consumes ``annotations_v1.json``; it never asks a human anything at run
time. Re-running it is a pure function of two frozen files.

*The decision owner stays single.* ``rank_candidates`` /
``select_best_candidate`` in ``src.assets.semantic_selection.candidate_ranker``
is asked, through the same ``select_best_with_video`` wrapper production uses.
No second selector, no scoring of our own, and no confidence number that the
product contract does not already have.

The evaluation constants, stated rather than hidden:

``used_asset_ids`` is empty
    Every benchmark scene is judged on its own. Production carries cross-scene
    de-duplication state; a per-scene benchmark cannot and must not.

Preview pixels are not asset pixels
    ``framing_decision`` reads the candidate's *declared* provider dimensions,
    which the corpus carries verbatim. The locally cached preview is only what
    the annotator looks at. Candidates whose provider never declared a size are
    tagged ``technical_dimensions_unknown`` and left to the production gate,
    which reports ``framing_unknown`` and does not reject on it.

What this module does not do: it does not read ``projects/``, does not open
image files and does not build the corpus. That belongs to
``tests.plan9d_corpus_builder``, which is run by hand.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from src.assets.semantic_selection.decision import (
    SUPPORT_FULL,
    SUPPORT_MANUAL,
    SUPPORT_PARTIAL,
    SUPPORT_RIGHTS_BLOCKED,
    SUPPORT_UNVERIFIED,
)
from src.assets.semantic_selection.models import SemanticScene
from src.news.asset_manifest_builder import FIXTURE_SEMANTIC_BACKENDS, select_best_with_video


DATA_ROOT = Path(__file__).resolve().parent / "data" / "plan9d"
CORPUS_PATH = DATA_ROOT / "corpus_v1.json"
ANNOTATIONS_PATH = DATA_ROOT / "annotations_v1.json"

CORPUS_SCHEMA_VERSION = "plan9d-corpus-1"
ANNOTATIONS_SCHEMA_VERSION = "plan9d-annotations-1"

#: Salt for the blind identifier order. Fixed, so the mapping is reproducible;
#: unrelated to any ranking, so the order carries no signal about the answer.
BLIND_SALT = "plan9d-blind-2026-08-08"

STATUS_WAITING = "WAITING_FOR_OWNER_ANNOTATION"
STATUS_COMPLETE = "COMPLETE"

PREFERENCE_NONE_ACCEPTABLE = "none_acceptable"
PREFERENCE_UNDECIDABLE = "undecidable"

COVERAGE_VALUES = ("matched", "partial", "missing", "undecidable")
PRESENCE_VALUES = ("present", "absent", "undecidable")
YES_NO_VALUES = ("yes", "no", "undecidable")
ENTITY_VALUES = ("yes", "no", "undecidable", "not_applicable")

CANDIDATE_FLAG_SPEC: dict[str, tuple[str, ...]] = {
    "subject_coverage": COVERAGE_VALUES,
    "action_coverage": COVERAGE_VALUES,
    "environment_coverage": COVERAGE_VALUES,
    "location_coverage": COVERAGE_VALUES,
    "must_include": PRESENCE_VALUES,
    "must_avoid": PRESENCE_VALUES,
    "non_real_footage": YES_NO_VALUES,
    "crop_survives_9_16": YES_NO_VALUES,
    "visible_text_or_logo": YES_NO_VALUES,
    "exact_entity_match": ENTITY_VALUES,
}

#: Every technical category the corpus can carry. ``non_real_footage_risk`` is
#: part of the vocabulary and is *absent* from the current corpus: no candidate
#: in any local project carries non-real-footage wording in provider evidence.
#: Fabricating such a scene to fill the quota would make the benchmark a fiction,
#: so the gap is recorded instead.
CORPUS_CATEGORIES = (
    "subject_mismatch_risk",
    "must_include_declared",
    "must_avoid_declared",
    "environment_conflict_risk",
    "non_real_footage_risk",
    "declared_conflicting_context",
    "crop_framing_concern",
    "visible_text_or_logo_risk",
    "ambiguous_needs_review",
    "rights_blocked_candidate",
    "technical_dimensions_unknown",
    "no_acceptable_candidate",
    "regression_capable",
)

#: Fields the annotator must never see. The blind pack is built from the corpus,
#: so the property has to be enforced against the corpus record, key by key.
BLINDED_CANDIDATE_KEYS = frozenset(
    {
        "asset_id",
        "provider",
        "provider_asset_id",
        "title",
        "description",
        "keywords",
        "tags",
        "author",
        "author_name",
        "license",
        "license_name",
        "rights_status",
        "source_url",
        "source_page",
        "source_page_url",
        "metadata_rank",
        "metadata_score",
        "quality_score",
        "vertical_score",
        "search_query",
        "raw_metadata",
        "provenance",
        "canonical_asset",
        "policy_decision",
    }
)

#: Evidence produced by a fixture, a mock or a scripted stand-in can prove
#: wiring. It can never prove visual quality, because it did not look at a
#: picture. PLAN-9D says so outright, and the harness refuses such an arm.
#: ``FIXTURE_SEMANTIC_BACKENDS`` is imported rather than restated: production
#: already owns the list of backends that invent their answer.
NON_ADMISSIBLE_EVIDENCE_BACKENDS = frozenset(FIXTURE_SEMANTIC_BACKENDS) | {
    "scripted",
    "fake",
    "stub",
    "fixture",
    "dummy",
}

#: The metadata-only arm: no Vision evidence reaches the decision owner at all.
ARM_METADATA_ONLY = "metadata_only"

#: Support statuses a future autonomous policy could accept without a human.
#: Recorded here as an *evaluation* reading of an existing production field, not
#: as a new product contract: PLAN-9D-A implements no product mode. The values
#: are imported from the decision layer, never spelled out again - a restated
#: ``"rights_blocked"`` silently missed the real ``relevant_but_rights_blocked``.
AUTO_SAFE_SUPPORT = frozenset({SUPPORT_FULL})
REVIEW_SUPPORT = frozenset(
    {SUPPORT_PARTIAL, SUPPORT_MANUAL, SUPPORT_UNVERIFIED, SUPPORT_RIGHTS_BLOCKED}
)


class BenchmarkError(RuntimeError):
    """The frozen benchmark data cannot be trusted as it stands."""


# --------------------------------------------------------------------------- #
# Provenance
# --------------------------------------------------------------------------- #


def canonical_json(payload: Any) -> str:
    """One byte-for-byte spelling of a payload, so a hash of it means something."""

    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def corpus_digest(corpus: dict[str, Any]) -> str:
    """SHA256 of everything in the corpus except the recorded digest itself."""

    payload = {key: value for key, value in corpus.items() if key != "corpus_sha256"}
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def blind_order_key(scene_key: str, asset_id: str) -> str:
    """Deterministic, ranking-independent ordering value for one candidate."""

    raw = f"{BLIND_SALT}|{scene_key}|{asset_id}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def assign_blind_ids(scene_key: str, asset_ids: Iterable[str]) -> dict[str, str]:
    """Map each real asset id to ``C1..Cn`` in hash order, not in rank order."""

    ordered = sorted(dict.fromkeys(asset_ids), key=lambda item: blind_order_key(scene_key, item))
    return {asset_id: f"C{index}" for index, asset_id in enumerate(ordered, start=1)}


# --------------------------------------------------------------------------- #
# Loading and validation
# --------------------------------------------------------------------------- #


def load_corpus(path: Path = CORPUS_PATH) -> dict[str, Any]:
    corpus = json.loads(path.read_text(encoding="utf-8"))
    validate_corpus(corpus)
    return corpus


def load_annotations(path: Path = ANNOTATIONS_PATH) -> dict[str, Any]:
    annotations = json.loads(path.read_text(encoding="utf-8"))
    validate_annotations(annotations)
    return annotations


def validate_corpus(corpus: dict[str, Any]) -> None:
    if corpus.get("schema_version") != CORPUS_SCHEMA_VERSION:
        raise BenchmarkError(f"unexpected corpus schema_version: {corpus.get('schema_version')!r}")
    for field_name in ("corpus_version", "built_at_utc", "corpus_sha256", "scenes"):
        if not corpus.get(field_name):
            raise BenchmarkError(f"corpus is missing {field_name}")
    recorded = str(corpus["corpus_sha256"])
    actual = corpus_digest(corpus)
    if recorded != actual:
        raise BenchmarkError(f"corpus digest mismatch: recorded {recorded}, computed {actual}")

    seen_keys: set[str] = set()
    for scene in corpus["scenes"]:
        key = str(scene.get("scene_key") or "")
        if not key:
            raise BenchmarkError("corpus scene without scene_key")
        if key in seen_keys:
            raise BenchmarkError(f"duplicate scene_key in corpus: {key}")
        seen_keys.add(key)
        for name in ("project", "scene_id", "scene_text", "semantic_scene", "candidates"):
            if name not in scene:
                raise BenchmarkError(f"{key}: corpus scene is missing {name}")
        unknown = set(scene.get("categories") or []) - set(CORPUS_CATEGORIES)
        if unknown:
            raise BenchmarkError(f"{key}: unknown corpus categories {sorted(unknown)}")
        candidates = scene["candidates"]
        if len(candidates) < 2:
            raise BenchmarkError(f"{key}: a benchmark scene needs at least two candidates")
        expected = assign_blind_ids(key, [str(c.get("asset_id") or "") for c in candidates])
        seen_blind: set[str] = set()
        for index, candidate in enumerate(candidates, start=1):
            asset_id = str(candidate.get("asset_id") or "")
            blind_id = str(candidate.get("blind_id") or "")
            if not asset_id or not blind_id:
                raise BenchmarkError(f"{key}: candidate without asset_id/blind_id")
            if blind_id in seen_blind:
                raise BenchmarkError(f"{key}: duplicate blind id {blind_id}")
            seen_blind.add(blind_id)
            if expected[asset_id] != blind_id:
                raise BenchmarkError(
                    f"{key}: blind id {blind_id} for {asset_id} does not match the derived mapping"
                )
            if blind_id != f"C{index}":
                raise BenchmarkError(
                    f"{key}: candidates must be stored in blind-id order, got {blind_id} at position {index}"
                )
            if not isinstance(candidate.get("candidate"), dict):
                raise BenchmarkError(f"{key}/{blind_id}: missing the raw candidate record")
            if not isinstance(candidate.get("input_order"), int):
                raise BenchmarkError(f"{key}/{blind_id}: missing input_order")
            if candidate["candidate"].get("vision_tags"):
                raise BenchmarkError(
                    f"{key}/{blind_id}: the corpus is the metadata-only arm and must carry no vision_tags"
                )
            for frame in candidate.get("frames") or []:
                for name in ("local_frame_path", "sha256"):
                    if not frame.get(name):
                        raise BenchmarkError(f"{key}/{blind_id}: frame without {name}")
        orders = sorted(int(c["input_order"]) for c in candidates)
        if orders != list(range(len(candidates))):
            raise BenchmarkError(f"{key}: input_order must be a permutation of 0..n-1, got {orders}")


def validate_annotations(annotations: dict[str, Any]) -> None:
    if annotations.get("schema_version") != ANNOTATIONS_SCHEMA_VERSION:
        raise BenchmarkError(
            f"unexpected annotations schema_version: {annotations.get('schema_version')!r}"
        )
    if annotations.get("blind") is not True:
        raise BenchmarkError("annotations must record blind=true")
    status = str(annotations.get("status") or "")
    if status not in {STATUS_WAITING, STATUS_COMPLETE}:
        raise BenchmarkError(f"unexpected annotations status: {status!r}")
    if not annotations.get("corpus_sha256"):
        raise BenchmarkError("annotations must record the corpus_sha256 they were made against")
    for scene in annotations.get("scenes") or []:
        key = str(scene.get("scene_key") or "")
        if not key:
            raise BenchmarkError("annotation entry without scene_key")
        preference = str(scene.get("preferred_candidate") or "")
        if status == STATUS_COMPLETE and not preference:
            raise BenchmarkError(f"{key}: preferred_candidate is empty in a COMPLETE annotation set")
        for blind_id, flags in (scene.get("candidates") or {}).items():
            for name, allowed in CANDIDATE_FLAG_SPEC.items():
                value = str(flags.get(name) or "")
                if value and value not in allowed:
                    raise BenchmarkError(f"{key}/{blind_id}: {name}={value!r} is not one of {allowed}")


def annotations_are_complete(corpus: dict[str, Any], annotations: dict[str, Any]) -> tuple[bool, list[str]]:
    """Is this annotation set usable, and if not, exactly what is missing?"""

    problems: list[str] = []
    if str(annotations.get("status")) != STATUS_COMPLETE:
        problems.append(f"status={annotations.get('status')!r}")
    if str(annotations.get("corpus_sha256")) != str(corpus.get("corpus_sha256")):
        problems.append("corpus_sha256 does not match the frozen corpus")
    if not str(annotations.get("annotator") or "").strip():
        problems.append("annotator is empty")
    by_key = {str(s.get("scene_key")): s for s in annotations.get("scenes") or []}
    for scene in corpus["scenes"]:
        key = str(scene["scene_key"])
        entry = by_key.get(key)
        if entry is None:
            problems.append(f"{key}: no annotation entry")
            continue
        preference = str(entry.get("preferred_candidate") or "")
        if not preference:
            problems.append(f"{key}: preferred_candidate is empty")
            continue
        known = {str(c["blind_id"]) for c in scene["candidates"]}
        if preference not in known | {PREFERENCE_NONE_ACCEPTABLE, PREFERENCE_UNDECIDABLE}:
            problems.append(f"{key}: preferred_candidate={preference!r} is not a candidate of this scene")
        unknown = {str(v) for v in entry.get("unacceptable_candidates") or []} - known
        if unknown:
            problems.append(f"{key}: unacceptable_candidates refers to {sorted(unknown)}")
    return (not problems), problems


# --------------------------------------------------------------------------- #
# The metadata-only baseline arm
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class SceneSelection:
    """What the existing decision owner did with one benchmark scene."""

    scene_key: str
    selected_blind_id: str | None
    support_status: str
    slot_verdict: str
    blocking_reject_reasons: tuple[str, ...] = ()
    advisory_reject_reasons: tuple[str, ...] = ()
    rights_status: str = ""
    rights_review_required: bool = False
    semantic_match_status: str = ""
    semantic_evidence: bool = False
    undecidable_fields: tuple[str, ...] = ()
    framing_status: str = ""
    per_candidate: dict[str, dict[str, Any]] = field(default_factory=dict)

    @property
    def abstained(self) -> bool:
        return self.selected_blind_id is None


def scene_from_corpus(scene: dict[str, Any]) -> SemanticScene:
    stored = dict(scene.get("semantic_scene") or {})
    known = {name: stored[name] for name in SemanticScene.__dataclass_fields__ if name in stored}
    return SemanticScene(**known)


def run_metadata_baseline(corpus: dict[str, Any]) -> dict[str, SceneSelection]:
    """Ask the existing decision owner, with no Vision evidence present.

    Deliberately the *production* entry point: ``select_best_with_video`` wraps
    ``select_best_candidate``, which is the single decision owner. Nothing here
    ranks, scores or overrides anything.
    """

    results: dict[str, SceneSelection] = {}
    for scene in corpus["scenes"]:
        key = str(scene["scene_key"])
        blind_by_asset = {str(c["asset_id"]): str(c["blind_id"]) for c in scene["candidates"]}
        # Candidates are *stored* in blind-id order, so the frozen file itself
        # reveals no ranking. They are *fed* in the order the project manifest
        # recorded, because ``rank_candidates`` sorts stably and the input order
        # is therefore the tie-break. Feeding the blind order instead would make
        # an arbitrary hash decide every tie - which it did, until this was fixed.
        ordered = sorted(scene["candidates"], key=lambda item: int(item["input_order"]))
        candidates = [dict(item["candidate"]) for item in ordered]
        for candidate in candidates:
            candidate["vision_tags"] = []
        selected, ranked = select_best_with_video(
            scene_from_corpus(scene),
            candidates,
            prefer_video=bool(scene.get("prefer_video")),
            used_asset_ids=set(),
            required_duration_sec=float(scene.get("required_duration_sec") or 0.0),
            require_provider_metadata=bool(scene.get("require_provider_metadata")),
            source_class=str(scene.get("source_class") or ""),
        )
        per_candidate = {
            blind_by_asset.get(str(item.get("asset_id")), str(item.get("asset_id"))): {
                "rejected": bool(item.get("rejected")),
                "support_status": str(item.get("support_status") or ""),
                "slot_verdict": str(item.get("slot_verdict") or ""),
                "blocking_reject_reasons": list(item.get("blocking_reject_reasons") or []),
                "advisory_reject_reasons": list(item.get("advisory_reject_reasons") or []),
                "framing_status": str(item.get("framing_status") or ""),
                "semantic_match_status": str(item.get("semantic_match_status") or ""),
                "semantic_evidence": bool(item.get("semantic_evidence")),
                "rights_status": str(item.get("rights_status") or ""),
                "rights_review_required": bool(item.get("review_required")),
            }
            for item in ranked
        }
        results[key] = SceneSelection(
            scene_key=key,
            selected_blind_id=(
                blind_by_asset.get(str(selected.get("asset_id"))) if selected else None
            ),
            support_status=str((selected or {}).get("support_status") or ""),
            slot_verdict=str((selected or {}).get("slot_verdict") or ""),
            blocking_reject_reasons=tuple((selected or {}).get("blocking_reject_reasons") or ()),
            advisory_reject_reasons=tuple((selected or {}).get("advisory_reject_reasons") or ()),
            rights_status=str((selected or {}).get("rights_status") or ""),
            rights_review_required=bool((selected or {}).get("review_required") or False),
            semantic_match_status=str((selected or {}).get("semantic_match_status") or ""),
            semantic_evidence=bool((selected or {}).get("semantic_evidence") or False),
            undecidable_fields=tuple((selected or {}).get("undecidable_fields") or ()),
            framing_status=str((selected or {}).get("framing_status") or ""),
            per_candidate=per_candidate,
        )
    return results


def assert_admissible_evidence(arm_name: str, evidence_source: str) -> None:
    """A mock may prove wiring; it may never prove visual quality (PLAN-9D)."""

    backend = str(evidence_source or "").strip().casefold()
    if backend.startswith("vision:"):
        backend = backend.split(":", 1)[1].strip()
    if backend in NON_ADMISSIBLE_EVIDENCE_BACKENDS:
        raise BenchmarkError(
            f"arm {arm_name!r}: evidence source {evidence_source!r} is a fixture backend and is "
            "not admissible as visual-quality evidence"
        )


# --------------------------------------------------------------------------- #
# Measurement against the frozen human ground truth
# --------------------------------------------------------------------------- #


def evaluate_arm(
    corpus: dict[str, Any],
    annotations: dict[str, Any],
    selections: dict[str, SceneSelection],
    *,
    arm_name: str = ARM_METADATA_ONLY,
    evidence_source: str = ARM_METADATA_ONLY,
) -> dict[str, Any]:
    """Score one arm against the frozen annotations. No human input at run time.

    Returns ``status=WAITING_FOR_OWNER_ANNOTATION`` and measures nothing when the
    ground truth is not yet frozen. It never invents a label to fill the gap.
    """

    assert_admissible_evidence(arm_name, evidence_source)
    complete, problems = annotations_are_complete(corpus, annotations)
    if not complete:
        return {
            "status": STATUS_WAITING,
            "arm": arm_name,
            "evidence_source": evidence_source,
            "corpus_sha256": corpus["corpus_sha256"],
            "blocking": problems,
            "scenes": [],
            "aggregate": {},
        }

    by_key = {str(s["scene_key"]): s for s in annotations["scenes"]}
    rows: list[dict[str, Any]] = []
    for scene in corpus["scenes"]:
        key = str(scene["scene_key"])
        entry = by_key[key]
        selection = selections[key]
        preferred = str(entry.get("preferred_candidate") or "")
        unacceptable = {str(v) for v in entry.get("unacceptable_candidates") or []}
        flags = entry.get("candidates") or {}
        chosen = selection.selected_blind_id

        human_says_nothing_acceptable = preferred == PREFERENCE_NONE_ACCEPTABLE
        undecidable = preferred == PREFERENCE_UNDECIDABLE
        chosen_flags = dict(flags.get(chosen) or {}) if chosen else {}

        rows.append(
            {
                "scene_key": key,
                "categories": list(scene.get("categories") or []),
                "system_selected": chosen,
                "human_preferred": preferred,
                "selection_matches_preferred": bool(chosen and chosen == preferred),
                "unacceptable_selected": bool(chosen and chosen in unacceptable),
                "correct_abstention": bool(chosen is None and human_says_nothing_acceptable),
                "wrong_abstention": bool(
                    chosen is None and not human_says_nothing_acceptable and not undecidable
                ),
                "must_avoid_escaped": str(chosen_flags.get("must_avoid") or "") == "present",
                "non_real_footage_selected": str(chosen_flags.get("non_real_footage") or "") == "yes",
                "safe_escalation_to_review": bool(
                    chosen is not None and selection.support_status in REVIEW_SUPPORT
                ),
                "auto_safe": bool(chosen is not None and selection.support_status in AUTO_SAFE_SUPPORT),
                "undecidable": undecidable,
                "support_status": selection.support_status,
                "slot_verdict": selection.slot_verdict,
                "blocking_reject_reasons": list(selection.blocking_reject_reasons),
            }
        )

    aggregate = {
        "scenes": len(rows),
        "preferred_matches": sum(1 for r in rows if r["selection_matches_preferred"]),
        "unacceptable_selected": sum(1 for r in rows if r["unacceptable_selected"]),
        "abstentions": sum(1 for r in rows if r["system_selected"] is None),
        "correct_abstentions": sum(1 for r in rows if r["correct_abstention"]),
        "wrong_abstentions": sum(1 for r in rows if r["wrong_abstention"]),
        "must_avoid_escaped": sum(1 for r in rows if r["must_avoid_escaped"]),
        "non_real_footage_selected": sum(1 for r in rows if r["non_real_footage_selected"]),
        "safe_escalations_to_review": sum(1 for r in rows if r["safe_escalation_to_review"]),
        "auto_safe": sum(1 for r in rows if r["auto_safe"]),
        "undecidable_cases": sum(1 for r in rows if r["undecidable"]),
    }
    return {
        "status": STATUS_COMPLETE,
        "arm": arm_name,
        "evidence_source": evidence_source,
        "corpus_sha256": corpus["corpus_sha256"],
        "annotator": annotations.get("annotator"),
        "annotated_at_utc": annotations.get("annotated_at_utc"),
        "blocking": [],
        "scenes": rows,
        "aggregate": aggregate,
    }


def compare_arms(baseline: dict[str, Any], candidate_arm: dict[str, Any]) -> dict[str, Any]:
    """Improvement and regression between two already-measured arms.

    Kept as a pure function so that the A/B step of PLAN-9D adds an arm rather
    than a second measurement system. It is not exercised on real data here:
    PLAN-9D-A produces exactly one arm.

    A regression is *blocking* when the new arm lets through something the
    product may never let through - a candidate the annotator called
    unacceptable, a ``must_avoid`` hit, non-real footage - or when it stops
    abstaining where abstention was right. Everything else that got worse is a
    safe regression: the answer is weaker, but no gate was bypassed.
    """

    for arm in (baseline, candidate_arm):
        if arm.get("status") != STATUS_COMPLETE:
            return {"status": STATUS_WAITING, "blocking": list(arm.get("blocking") or [])}
    if baseline["corpus_sha256"] != candidate_arm["corpus_sha256"]:
        raise BenchmarkError("cannot compare arms measured against different corpora")

    base_rows = {r["scene_key"]: r for r in baseline["scenes"]}
    improvements: list[str] = []
    safe_regressions: list[str] = []
    blocking_regressions: list[str] = []
    for row in candidate_arm["scenes"]:
        key = row["scene_key"]
        before = base_rows.get(key)
        if before is None:
            raise BenchmarkError(f"arm covers a scene the baseline does not: {key}")
        got_worse_hard = (
            (row["unacceptable_selected"] and not before["unacceptable_selected"])
            or (row["must_avoid_escaped"] and not before["must_avoid_escaped"])
            or (row["non_real_footage_selected"] and not before["non_real_footage_selected"])
            or (row["wrong_abstention"] and not before["wrong_abstention"])
        )
        got_better = (
            (row["selection_matches_preferred"] and not before["selection_matches_preferred"])
            or (row["correct_abstention"] and not before["correct_abstention"])
            or (before["unacceptable_selected"] and not row["unacceptable_selected"])
            or (before["must_avoid_escaped"] and not row["must_avoid_escaped"])
        )
        got_worse_soft = (
            before["selection_matches_preferred"] and not row["selection_matches_preferred"]
        ) or (before["correct_abstention"] and not row["correct_abstention"])

        if got_worse_hard:
            blocking_regressions.append(key)
        elif got_better:
            improvements.append(key)
        elif got_worse_soft:
            safe_regressions.append(key)

    return {
        "status": STATUS_COMPLETE,
        "baseline_arm": baseline["arm"],
        "candidate_arm": candidate_arm["arm"],
        "corpus_sha256": baseline["corpus_sha256"],
        "improvements": improvements,
        "safe_regressions": safe_regressions,
        "blocking_regressions": blocking_regressions,
        "aggregate": {
            "improvements": len(improvements),
            "safe_regressions": len(safe_regressions),
            "blocking_regressions": len(blocking_regressions),
        },
    }
