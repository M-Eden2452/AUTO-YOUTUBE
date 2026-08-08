"""Offline ground-truth benchmark for the existing asset decision path (PLAN-9D).

Why this module exists
----------------------
PLAN-9D has to prove that Vision evidence *improves* the decision path. It cannot
be proved against the only real Vision run in the repository: that run covers
three scenes and six candidates, none of which has a strong metadata-only answer,
so there is nothing there that a change could make worse. A claim of improvement
needs a benchmark that can also show a regression.

Historical evidence is not that benchmark
-----------------------------------------
Owner direction 2026-08-08 settled where the benchmark's data may come from. A
candidate pool only says something about *decision* quality if the pool itself
represents what retrieval does now. Every runtime project on disk predates the
query work of PLAN-9B-1..9B-3 and PLAN-9C, so a corpus harvested from those
projects measures the choice between candidates that the retired query stack
happened to return - which is a statement about the old queries, not about the
decision owner.

So this module knows two kinds of frozen data and keeps them apart by contract:

``current_head_capture``
    The benchmark input. Captured from the current production retrieval path by
    PLAN-9D-B, then frozen. Only this may be measured.

``historical_pre_query_fixes``
    Evidence that a defect really existed - a scene requirement, the query that
    actually reached the provider, the pool that came back. Curated by PLAN-9D-A
    into ``historical_failure_evidence_v1.json``. It is never measured, and
    ``assert_current_benchmark_input`` is the single gate that says so.

The gate is deliberately unforgiving about *unstamped* data too: the pre-9D-A
corpus carried no provenance at all, so anything that fails to declare itself a
current capture is refused rather than assumed.

This module owns both data contracts and the measurement, and nothing else.
Three properties of the benchmark are deliberate:

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
image files, does not build the corpus and does not curate the historical
evidence. That belongs to ``tests.plan9d_corpus_builder``, which is run by hand.
Nothing here names a historical project: the generic harness must outlive the
runtime data it was once built from.
"""

from __future__ import annotations

import hashlib
import json
import re
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

#: The benchmark input. Captured and frozen by PLAN-9D-B; absent until then, and
#: its absence is reported rather than papered over.
CURRENT_CORPUS_PATH = DATA_ROOT / "current_corpus_v1.json"
#: The owner's blind labels for that capture. Written once by PLAN-9D-D.
CURRENT_ANNOTATIONS_PATH = DATA_ROOT / "current_annotations_v1.json"
#: Curated proof that the pre-9B/9C retrieval defects were real (PLAN-9D-A).
HISTORICAL_EVIDENCE_PATH = DATA_ROOT / "historical_failure_evidence_v1.json"

CORPUS_SCHEMA_VERSION = "plan9d-corpus-1"
ANNOTATIONS_SCHEMA_VERSION = "plan9d-annotations-1"
HISTORICAL_EVIDENCE_SCHEMA_VERSION = "plan9d-historical-evidence-1"

#: Where a frozen payload came from. The distinction is the whole point of the
#: 2026-08-08 reconciliation, so it is data, not a naming convention.
GENERATION_CURRENT = "current_head_capture"
GENERATION_HISTORICAL = "historical_pre_query_fixes"

#: What a frozen payload is *for*. ``historical_project_corpus`` is the raw
#: project harvest the builder produces; ``historical_failure_evidence`` is the
#: compact curated form that PLAN-9D-A commits.
FIXTURE_KIND_CURRENT_BENCHMARK = "current_retrieval_benchmark"
FIXTURE_KIND_HISTORICAL_CORPUS = "historical_project_corpus"
FIXTURE_KIND_HISTORICAL_EVIDENCE = "historical_failure_evidence"

HISTORICAL_KINDS = frozenset({FIXTURE_KIND_HISTORICAL_CORPUS, FIXTURE_KIND_HISTORICAL_EVIDENCE})

#: Failure classes the historical evidence is allowed to claim. Each one is
#: checkable against the record it is attached to, so a label cannot be a
#: free-text opinion. ``shared_generic_candidate_pool`` is deliberately a
#: property of a *set* of cases: the repetition is the evidence.
HISTORICAL_FAILURE_MODES = (
    "subject_absent_from_provider_query",
    "retired_broad_query_literal",
    "retired_topic_query_hardcode",
    "shared_generic_candidate_pool",
    "degenerate_single_token_query",
    "subject_lost_after_primary_query",
    "non_provider_language_query",
    "mislabelled_query_language",
    "garbage_subject_extraction",
)

#: Owner-annotation vocabulary. Historical evidence carrying any of it would be a
#: label nobody made, so the historical validator refuses these keys outright.
OWNER_ANNOTATION_KEYS = frozenset(
    {"preferred_candidate", "unacceptable_candidates", "annotator", "annotated_at_utc"}
)

#: Broad, subject-free literals the query stack used to append to every scene of a
#: legacy plan (registry C36, retired in ``72221e1``). Recorded here as data rather
#: than imported from the production guard that still recognises them: that guard
#: has its own exit condition, and a capture must still be refusable for having
#: sent one of these after the guard is gone.
LEGACY_BROAD_QUERY_LITERALS = frozenset(
    {
        "whale mother calf aerial ocean",
        "scientific researchers nature field observation",
        "ocean wildlife aerial waves",
        "nature science wildlife observation",
    }
)

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


def generation_class_of(payload: dict[str, Any]) -> str:
    """Where this payload came from, reading an unstamped payload honestly.

    The corpus frozen before the 2026-08-08 reconciliation declared no
    provenance. It was built from ``projects/``, so the only truthful reading of
    a missing stamp is *historical* - never "current, presumably".
    """

    declared = str(payload.get("generation_class") or "").strip()
    if declared:
        return declared
    if payload.get("schema_version") == CORPUS_SCHEMA_VERSION:
        return GENERATION_HISTORICAL
    return ""


def fixture_kind_of(payload: dict[str, Any]) -> str:
    """What this payload is for, with the same reading of an unstamped payload."""

    declared = str(payload.get("fixture_kind") or "").strip()
    if declared:
        return declared
    if payload.get("schema_version") == CORPUS_SCHEMA_VERSION:
        return FIXTURE_KIND_HISTORICAL_CORPUS
    return ""


def assert_current_benchmark_input(payload: dict[str, Any], *, context: str = "benchmark") -> None:
    """The single gate between historical evidence and a quality measurement.

    Historical pools answer "what did the retired queries return"; the benchmark
    asks "how good is the decision". Feeding one to the other is the exact
    mistake PLAN-9D was reconciled to prevent, so it fails loudly here rather
    than producing a number that reads like a quality result.
    """

    kind = fixture_kind_of(payload)
    generation = generation_class_of(payload)
    if kind in HISTORICAL_KINDS or generation == GENERATION_HISTORICAL:
        raise BenchmarkError(
            f"{context}: refusing historical evidence as benchmark input "
            f"(fixture_kind={kind!r}, generation_class={generation!r}). Historical pools were "
            "retrieved by the retired query stack and cannot measure current decision quality; "
            "the current capture is owned by PLAN-9D-B."
        )
    if kind != FIXTURE_KIND_CURRENT_BENCHMARK or generation != GENERATION_CURRENT:
        raise BenchmarkError(
            f"{context}: benchmark input must declare fixture_kind="
            f"{FIXTURE_KIND_CURRENT_BENCHMARK!r} and generation_class={GENERATION_CURRENT!r}, "
            f"got {kind!r}/{generation!r}"
        )


def load_current_corpus(path: Path = CURRENT_CORPUS_PATH) -> dict[str, Any]:
    if not path.is_file():
        raise BenchmarkError(
            f"no current retrieval corpus at {path}: capturing it from the current production "
            "retrieval path is PLAN-9D-B, which is a separate owner-approved slice. The curated "
            "historical evidence is not a substitute."
        )
    corpus = json.loads(path.read_text(encoding="utf-8"))
    validate_corpus(corpus)
    return corpus


def load_annotations(path: Path = CURRENT_ANNOTATIONS_PATH) -> dict[str, Any]:
    annotations = json.loads(path.read_text(encoding="utf-8"))
    validate_annotations(annotations)
    return annotations


def validate_corpus(corpus: dict[str, Any]) -> None:
    assert_current_benchmark_input(corpus, context="corpus")
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


#: Provenance a current capture must declare on top of the generic corpus shape.
#: The generic validator only proves a payload is *a* corpus; these fields are what
#: make it answerable later - which HEAD produced the pools, when, into which
#: workspace, and under which network approval.
CURRENT_CAPTURE_REQUIRED_FIELDS = (
    "capture_head_sha",
    "capture_timestamp_utc",
    "capture_workspace",
    "evaluation_set_version",
    "plan_step",
    "production_stages",
    "stages_not_run",
    "network",
    "providers",
    "capture_statistics",
)

_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")

#: Field names that carry a credential rather than evidence. Applied to *keys*
#: only. A capture writes provider URLs and provider metadata verbatim, so the
#: corpus is scanned before it is frozen: a provider that put a key in a URL must
#: fail the freeze rather than be discovered later in a committed file.
SECRET_MARKERS = (
    "api_key",
    "apikey",
    "api-key",
    "access_token",
    "access-token",
    "auth_token",
    "authorization",
    "client_secret",
    "private_key",
    "secret_key",
    "session_token",
    "x-api-key",
)

#: A *value* is only suspicious when it is shaped like a credential in use.
#: Matching the marker word alone would flag ordinary provider prose - an archive
#: description really can contain the word "authorization" - and a check that
#: cries wolf on a catalogue entry is a check that gets switched off.
_SECRET_PARAM_RE = re.compile(
    r"(?i)[?&](?:key|api_?key|apikey|token|access_?key|access_?token|secret|password|pwd|sig|signature)="
    r"[^&\s]{6,}"
)
_SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)\b(?:api[_-]?key|apikey|access[_-]?token|auth[_-]?token|authorization|client[_-]?secret|"
    r"private[_-]?key|secret[_-]?key|session[_-]?token|x-api-key|password|passwd)\b\s*[:=]\s*\S{6,}"
)
#: An ``Authorization`` header value, not the English words. The scheme name has
#: to be followed by something that is actually token-shaped - long, and carrying
#: a digit or a base64/URL symbol. Requiring only letters matched "Basic
#: Construction" in an Internet Archive bibliography and stopped a capture.
_BEARER_RE = re.compile(
    r"(?i)\b(?:bearer|basic)\s+(?=[A-Za-z0-9._~+/=-]*[0-9._~+/=-])[A-Za-z0-9._~+/=-]{16,}"
)


def secret_like_findings(payload: Any, *, path: str = "$") -> list[str]:
    """Every place in ``payload`` that looks like a credential. Empty is the only pass.

    Deliberately reports the *location*, never the value: a finding is a reason to
    stop, and printing the thing found would defeat the check that produced it.
    """

    findings: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            lowered = str(key).casefold()
            if any(marker in lowered for marker in SECRET_MARKERS):
                findings.append(f"{path}.{key}: key name looks like a credential")
            findings.extend(secret_like_findings(value, path=f"{path}.{key}"))
        return findings
    if isinstance(payload, (list, tuple)):
        for index, item in enumerate(payload):
            findings.extend(secret_like_findings(item, path=f"{path}[{index}]"))
        return findings
    if isinstance(payload, str):
        if _SECRET_PARAM_RE.search(payload):
            findings.append(f"{path}: string carries a credential-shaped query parameter")
        elif _SECRET_ASSIGNMENT_RE.search(payload):
            findings.append(f"{path}: string assigns a value to a credential name")
        elif _BEARER_RE.search(payload):
            findings.append(f"{path}: string carries an authorization header value")
    return findings


def validate_current_capture(corpus: dict[str, Any]) -> None:
    """Everything a PLAN-9D-B capture has to be able to answer about itself.

    Separate from ``validate_corpus`` on purpose: that one owns the shape every
    corpus shares, this one owns what makes a capture *current*. A payload that
    passes the first and fails this is a corpus with no traceable origin, which is
    exactly the state PLAN-9D-A found the retired ``corpus_v1.json`` in.
    """

    assert_current_benchmark_input(corpus, context="current capture")
    for name in CURRENT_CAPTURE_REQUIRED_FIELDS:
        if not corpus.get(name):
            raise BenchmarkError(f"current capture is missing {name}")

    head = str(corpus["capture_head_sha"])
    if not _SHA1_RE.match(head):
        raise BenchmarkError(f"capture_head_sha is not a full commit sha: {head!r}")

    workspace = str(corpus["capture_workspace"]).replace("\\", "/").rstrip("/")
    if not workspace:
        raise BenchmarkError("capture_workspace is empty")

    network = corpus["network"] if isinstance(corpus.get("network"), dict) else {}
    approved = {str(item) for item in (network.get("approved_actions") or [])}
    if not approved:
        raise BenchmarkError("current capture must record which network actions were approved")
    if "asset_download" in approved or network.get("asset_download_used"):
        raise BenchmarkError(
            "PLAN-9D-B captures frame evidence from the bounded preview path; a corpus that "
            "records an asset download was produced under an approval this step never had"
        )

    findings = secret_like_findings(corpus)
    if findings:
        raise BenchmarkError(f"current capture carries secret-like values: {findings}")

    for scene in corpus["scenes"]:
        key = str(scene.get("scene_key") or "")
        for name in ("case_id", "visual_brief", "query_plan", "routing", "provider_attempts"):
            if name not in scene:
                raise BenchmarkError(f"{key}: captured scene is missing {name}")
        if not scene["visual_brief"]:
            raise BenchmarkError(f"{key}: captured scene carries no visual brief")
        subjects = [item for item in (scene.get("semantic_scene") or {}).get("subject") or [] if str(item).strip()]
        if not subjects:
            raise BenchmarkError(f"{key}: captured scene has an empty semantic subject")
        queries = [
            str(item.get("query") or "")
            for item in (scene["query_plan"].get("queries") or [])
            if str(item.get("status") or "") == "ok"
        ]
        if not queries:
            raise BenchmarkError(f"{key}: no provider-ready query was recorded")
        for query in queries:
            if " ".join(query.casefold().split()) in LEGACY_BROAD_QUERY_LITERALS:
                raise BenchmarkError(f"{key}: a retired broad literal reached a provider: {query!r}")
        for candidate in scene["candidates"]:
            blind_id = str(candidate.get("blind_id") or "")
            for frame in candidate.get("frames") or []:
                path = str(frame.get("local_frame_path") or "").replace("\\", "/")
                if not path.startswith(f"{workspace}/"):
                    raise BenchmarkError(
                        f"{key}/{blind_id}: frame {path!r} is outside the capture workspace "
                        f"{workspace!r}; a current corpus may not reference historical runtime data"
                    )


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


def annotation_status(path: Path = CURRENT_ANNOTATIONS_PATH) -> str:
    """Where the owner's blind pass stands, reading an absent file honestly.

    No annotation file means the pass has not happened, which is the same state
    an empty one describes - never "complete by default". PLAN-9D-D is the only
    step allowed to change this answer, and only the owner may produce the labels.
    """

    if not path.is_file():
        return STATUS_WAITING
    annotations = json.loads(path.read_text(encoding="utf-8"))
    status = str(annotations.get("status") or "")
    if status == STATUS_COMPLETE and str(annotations.get("annotator") or "").strip():
        return STATUS_COMPLETE
    return STATUS_WAITING


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
# Historical failure evidence
# --------------------------------------------------------------------------- #


def historical_digest(fixture: dict[str, Any]) -> str:
    """SHA256 of the whole fixture except the recorded digest itself."""

    payload = {key: value for key, value in fixture.items() if key != "fixture_sha256"}
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def load_historical_evidence(path: Path = HISTORICAL_EVIDENCE_PATH) -> dict[str, Any]:
    fixture = json.loads(path.read_text(encoding="utf-8"))
    validate_historical_evidence(fixture)
    return fixture


def validate_historical_evidence(fixture: dict[str, Any]) -> None:
    """Everything the fixture claims has to be present and self-consistent.

    The fixture's job is narrow: keep the proof that a retrieval defect existed
    after the gigabytes that produced it are gone. So the validator checks
    provenance (where each case came from and what it was derived from), the
    query record (what actually reached the provider), and that no owner label
    has crept in - never whether a candidate was "good", which nobody here is
    entitled to say.
    """

    if fixture.get("schema_version") != HISTORICAL_EVIDENCE_SCHEMA_VERSION:
        raise BenchmarkError(
            f"unexpected historical schema_version: {fixture.get('schema_version')!r}"
        )
    if fixture.get("fixture_kind") != FIXTURE_KIND_HISTORICAL_EVIDENCE:
        raise BenchmarkError(f"unexpected fixture_kind: {fixture.get('fixture_kind')!r}")
    if fixture.get("generation_class") != GENERATION_HISTORICAL:
        raise BenchmarkError(
            f"historical evidence must declare generation_class={GENERATION_HISTORICAL!r}, "
            f"got {fixture.get('generation_class')!r}"
        )
    for name in ("fixture_version", "built_at_utc", "plan_step", "cases", "fixture_sha256"):
        if not fixture.get(name):
            raise BenchmarkError(f"historical evidence is missing {name}")

    recorded = str(fixture["fixture_sha256"])
    actual = historical_digest(fixture)
    if recorded != actual:
        raise BenchmarkError(
            f"historical evidence digest mismatch: recorded {recorded}, computed {actual}"
        )

    derived = fixture.get("derived_from") or {}
    for name in ("corpus_version", "corpus_sha256", "corpus_path", "corpus_commit"):
        if not derived.get(name):
            raise BenchmarkError(f"derived_from is missing {name}")

    stray = OWNER_ANNOTATION_KEYS & set(fixture)
    if stray:
        raise BenchmarkError(f"historical evidence carries owner annotation keys {sorted(stray)}")

    seen_ids: set[str] = set()
    for case in fixture["cases"]:
        case_id = str(case.get("case_id") or "")
        if not case_id:
            raise BenchmarkError("historical case without case_id")
        if case_id in seen_ids:
            raise BenchmarkError(f"duplicate historical case_id: {case_id}")
        seen_ids.add(case_id)

        stray = OWNER_ANNOTATION_KEYS & set(case)
        if stray:
            raise BenchmarkError(f"{case_id}: case carries owner annotation keys {sorted(stray)}")

        for name in (
            "source_project",
            "source_scene_id",
            "scene_key",
            "scene_text",
            "historical_semantic_scene",
            "historical_primary_query",
            "historical_provider_attempts",
            "source_manifests",
            "candidates",
        ):
            if name not in case:
                raise BenchmarkError(f"{case_id}: historical case is missing {name}")

        modes = tuple(case.get("failure_modes") or ())
        if not modes:
            raise BenchmarkError(f"{case_id}: a historical case must name at least one failure mode")
        unknown = set(modes) - set(HISTORICAL_FAILURE_MODES)
        if unknown:
            raise BenchmarkError(f"{case_id}: unknown failure modes {sorted(unknown)}")

        if "visual_brief_present" not in case:
            raise BenchmarkError(f"{case_id}: historical case must record visual_brief_present")

        attempts = case["historical_provider_attempts"]
        if not attempts:
            raise BenchmarkError(f"{case_id}: no provider attempt was preserved")
        for attempt in attempts:
            for name in ("provider", "query"):
                if not attempt.get(name):
                    raise BenchmarkError(f"{case_id}: provider attempt without {name}")
            if "result_count" not in attempt:
                raise BenchmarkError(f"{case_id}: provider attempt without result_count")

        if not case["source_manifests"]:
            raise BenchmarkError(f"{case_id}: no source manifest recorded")

        candidates = case["candidates"]
        if len(candidates) < 2:
            raise BenchmarkError(f"{case_id}: a historical pool needs at least two candidates")
        seen_assets: set[str] = set()
        for candidate in candidates:
            asset_id = str(candidate.get("asset_id") or "")
            if not asset_id:
                raise BenchmarkError(f"{case_id}: candidate without asset_id")
            if asset_id in seen_assets:
                raise BenchmarkError(f"{case_id}: duplicate candidate {asset_id}")
            seen_assets.add(asset_id)
            if not candidate.get("provider"):
                raise BenchmarkError(f"{case_id}/{asset_id}: candidate without provider")
            if candidate.get("vision_tags"):
                raise BenchmarkError(
                    f"{case_id}/{asset_id}: historical evidence carries no Vision result"
                )
            frame = candidate.get("representative_frame")
            if frame is None:
                continue
            for name in ("local_frame_path", "sha256"):
                if not frame.get(name):
                    raise BenchmarkError(f"{case_id}/{asset_id}: representative frame without {name}")


def historical_runtime_paths(fixture: dict[str, Any]) -> list[str]:
    """Every path under ``projects/`` this fixture still points at.

    This is the list the cleanup sequencing of PLAN-9D needs: what must survive
    until PLAN-9D closes, as opposed to the rest of the runtime tree, which the
    curated fixture has already released.
    """

    paths: list[str] = []
    for case in fixture.get("cases") or []:
        paths.extend(str(path) for path in case.get("source_manifests") or [])
        for candidate in case.get("candidates") or []:
            frame = candidate.get("representative_frame") or {}
            if frame.get("local_frame_path"):
                paths.append(str(frame["local_frame_path"]))
    return sorted(dict.fromkeys(paths))


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

    Gated on provenance before anything is selected: running the decision owner
    over a historical pool would produce a perfectly real-looking aggregate about
    a retrieval stack that no longer exists.
    """

    assert_current_benchmark_input(corpus, context="metadata baseline")
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
    assert_current_benchmark_input(corpus, context=f"arm {arm_name!r}")
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
