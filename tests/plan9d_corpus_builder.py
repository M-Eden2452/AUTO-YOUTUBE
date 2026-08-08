"""Hand-run PLAN-9D data tooling: harvest, curate, and render the blind pack.

Not a test; nothing imports it at test time except the locks that exercise its
pure functions. Three commands, in the order they are actually used:

    build    projects/ -> a historical project corpus (intermediate, not committed)
    curate   that corpus + the manifests -> the compact historical failure evidence
    pack     a *current* frozen corpus -> the owner's blind annotation page

    .\\venv\\Scripts\\python.exe -B -m tests.plan9d_corpus_builder build --out %TEMP%\\hist.json
    .\\venv\\Scripts\\python.exe -B -m tests.plan9d_corpus_builder curate --source-corpus %TEMP%\\hist.json
    .\\venv\\Scripts\\python.exe -B -m tests.plan9d_corpus_builder pack --corpus <current> --out %TEMP%\\pack.html

Offline by construction: it reads ``projects/*/assets/assets_manifest.json`` and
``projects/*/assets/review/visual_review_manifest.json``, both already on disk,
and opens no socket. No provider search, no download, no Vision, no paid call.

Anything harvested from ``projects/`` is stamped ``historical_pre_query_fixes``
------------------------------------------------------------------------------
Every runtime project on disk predates the query work of PLAN-9B-1..9B-3 and
PLAN-9C, so ``build`` cannot produce a current benchmark no matter what it is
pointed at, and it says so in the payload rather than leaving the reader to
work it out. ``pack`` refuses anything that is not a current capture: blind
owner annotation belongs to the current corpus (PLAN-9D-D), and annotating a
historical pool would freeze a human answer to a question the product no longer
asks.

``curate`` is the one-way step. It runs while the runtime tree still exists and
keeps only what proves a defect was real - the scene's requirement, the query
that actually reached the provider, the pool that came back, and one frame per
candidate as provenance. After it, PLAN-9D needs a few manifests and a few dozen
JPEGs instead of gigabytes; the rest of the harvest is released.

Three things it deliberately does not do.

*It does not decide which candidate is right.* Benchmark scenes are chosen by
technical category coverage; historical cases are chosen by which failure they
demonstrate. The semantic question is left entirely to the owner's blind pass on
the current corpus.

*It does not repair history.* A curated case records what happened, including
queries that were wrong, empty and in the wrong language.

*It does not copy pictures into the repository.* The cached previews are
third-party licensed provider material and ``projects/`` is deliberately
untracked. Frames are carried as path, size and SHA256, so the frozen data can
be verified and the tests never need the image bytes.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

from src.assets.semantic_selection.candidate_ranker import NON_REAL_VIDEO_TERMS
from src.assets.semantic_selection.decision import (
    FRAMING_CROP_REVIEW,
    FRAMING_HARD_REJECT,
    SUPPORT_FULL,
    SUPPORT_MANUAL,
    SUPPORT_PARTIAL,
    SUPPORT_UNVERIFIED,
)
from src.assets.semantic_selection.evidence import build_evidence, contains_concept
from src.assets.semantic_selection.models import SemanticScene
from src.news.asset_manifest_builder import select_best_with_video

from .plan9d_ground_truth import (
    ANNOTATIONS_SCHEMA_VERSION,
    CANDIDATE_FLAG_SPEC,
    CORPUS_SCHEMA_VERSION,
    FIXTURE_KIND_HISTORICAL_CORPUS,
    FIXTURE_KIND_HISTORICAL_EVIDENCE,
    GENERATION_HISTORICAL,
    HISTORICAL_EVIDENCE_PATH,
    HISTORICAL_EVIDENCE_SCHEMA_VERSION,
    HISTORICAL_FAILURE_MODES,
    STATUS_WAITING,
    BenchmarkError,
    assert_current_benchmark_input,
    assign_blind_ids,
    canonical_json,
    corpus_digest,
    generation_class_of,
    historical_digest,
    validate_corpus,
    validate_historical_evidence,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
PROJECTS_ROOT = REPO_ROOT / "projects"

CORPUS_VERSION = "plan9d-a-2026-08-08"
HISTORICAL_EVIDENCE_VERSION = "plan9d-historical-2026-08-08"

#: The frozen historical corpus this fixture supersedes. It is not in the tree
#: any more - PLAN-9D-A replaced 451 KB of ambiguous benchmark-shaped data with
#: the curated evidence - so the anchor is recorded as a commit, and
#: ``git show <commit>:<path>`` still reproduces the exact bytes.
SUPERSEDED_CORPUS_COMMIT = "04fe035e6ac07dbbe4a80257c3ed9d971976457e"
SUPERSEDED_CORPUS_PATH = "tests/data/plan9d/corpus_v1.json"

#: Ranker output written back into the stored manifest. Feeding it back in would
#: let the benchmark inherit a verdict instead of recomputing one, so every key
#: the ranker produces is stripped and the candidate is reduced to what a
#: provider (plus the licence policy) actually supplied.
RANKER_OUTPUT_KEYS = frozenset(
    {
        "subject_match", "action_match", "environment_match", "location_match", "camera_match",
        "semantic_score", "metadata_score", "metadata_status", "technical_score",
        "provider_confidence", "duration_check", "duration_status", "framing_check",
        "framing_status", "semantic_evidence", "semantic_match_status", "undecidable_fields",
        "must_include_unverifiable", "negative_matches", "contradiction_penalty",
        "duplicate_penalty", "watermark_penalty", "fallback_level", "scene_match_score",
        "final_score", "rejected", "reject_reason", "blocking_reject_reasons",
        "advisory_reject_reasons", "why_selected", "semantic_scene", "slot_verdict",
        "support_status", "support_requirements", "selection_decision", "selected_by",
        "total_score", "relevance_score", "rights_score",
    }
)

#: Nested archival copies of the same provider record. ``canonical_asset`` alone
#: is three quarters of the stored corpus and repeats ``provenance`` and
#: ``raw_metadata`` inside itself. The selection path never reads any of them -
#: ``build_evidence`` reads only top-level ``title``/``description``/
#: ``categories``/``depicts``/``location``/``tags``/``keywords``, and the scores
#: read only top-level ``width``/``height``/``quality_score``/``vertical_score``
#: - and the builder proves that by rebuilding the arm with and without them.
#: Dropping them keeps the frozen corpus honest and an order of magnitude
#: smaller; every field the decision owner can see stays verbatim.
ARCHIVAL_ONLY_KEYS = frozenset({"canonical_asset", "provenance", "raw_metadata"})

#: Wording that hints at a category the annotator will judge for real. Used only
#: to make sure such scenes are *present* in the corpus; it decides nothing.
TEXT_LOGO_TERMS = ("logo", "watermark", "text", "sign", "banner", "label", "title card")
CAPTIVE_TERMS = ("zoo", "aquarium", "captive", "captivity", "enclosure", "tank", "sanctuary")

#: Imported, never restated: the decision layer owns these vocabularies, and a
#: hand-copied status that no longer matches would silently mis-tag the corpus.
FRAMING_CONCERN = frozenset(FRAMING_HARD_REJECT) | {FRAMING_CROP_REVIEW}
REVIEW_SUPPORT = frozenset({SUPPORT_MANUAL, SUPPORT_UNVERIFIED})
STRONG_SUPPORT = frozenset({SUPPORT_FULL, SUPPORT_PARTIAL})

TARGET_SCENES = 16
MAX_SCENES_PER_PROJECT = 3


# --------------------------------------------------------------------------- #
# Reading what is already on disk
# --------------------------------------------------------------------------- #


def _strip_ranker_output(candidate: dict[str, Any], *, drop_archival: bool = False) -> dict[str, Any]:
    drop = RANKER_OUTPUT_KEYS | (ARCHIVAL_ONLY_KEYS if drop_archival else frozenset())
    stripped = {key: value for key, value in candidate.items() if key not in drop}
    stripped["vision_tags"] = []
    return stripped


def _semantic_scene(stored: dict[str, Any]) -> SemanticScene:
    known = {name: stored[name] for name in SemanticScene.__dataclass_fields__ if name in stored}
    return SemanticScene(**known)


def _normalized_text(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", str(text).casefold())).strip()


def collect_scenes() -> list[dict[str, Any]]:
    """Every local scene that has at least two candidates with a cached frame."""

    collected: list[dict[str, Any]] = []
    for project in sorted(PROJECTS_ROOT.iterdir()):
        manifest_path = project / "assets" / "assets_manifest.json"
        review_path = project / "assets" / "review" / "visual_review_manifest.json"
        if not manifest_path.is_file() or not review_path.is_file():
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        review = json.loads(review_path.read_text(encoding="utf-8"))
        prefer_video = str(manifest.get("visual_mode") or "") == "video_first"
        frames_by_scene = {
            str(scene.get("scene_id")): (scene.get("sampled_frames") or {})
            for scene in review.get("scenes") or []
        }
        text_by_scene = {
            str(scene.get("scene_id")): str(scene.get("scene_text") or "")
            for scene in review.get("scenes") or []
        }
        for scene in manifest.get("scenes") or []:
            scene_id = str(scene.get("scene_id") or "")
            available = _available_frames(frames_by_scene.get(scene_id, {}))
            candidates = _unique_candidates(scene.get("candidates") or [], available)
            if len(candidates) < 2:
                continue
            collected.append(
                {
                    "project": project.name,
                    "scene_id": scene_id,
                    "scene_key": f"{project.name}/{scene_id}",
                    "scene_text": text_by_scene.get(scene_id, ""),
                    "semantic_scene": scene.get("semantic_scene") or {},
                    "required_duration_sec": float(scene.get("required_duration_sec") or 0.0),
                    "source_class": str(scene.get("source_class") or ""),
                    "require_provider_metadata": bool(
                        (scene.get("provider_routing") or {}).get("requires_provider_metadata")
                    ),
                    "prefer_video": prefer_video,
                    "target_aspect_ratio": "9:16",
                    "raw_candidates": candidates,
                    "frames": available,
                }
            )
    return collected


def _available_frames(sampled: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    available: dict[str, list[dict[str, Any]]] = {}
    for asset_id, frames in sampled.items():
        existing = [
            {
                "local_frame_path": str(frame["local_frame_path"]).replace("\\", "/"),
                "sha256": str(frame.get("sha256") or ""),
                "width": int(frame.get("width") or 0),
                "height": int(frame.get("height") or 0),
                "frame_index": int(frame.get("frame_index") or 0),
            }
            for frame in frames
            if frame.get("local_frame_path")
            and (REPO_ROOT / str(frame["local_frame_path"])).is_file()
        ]
        if existing:
            available[str(asset_id)] = existing
    return available


def _unique_candidates(
    candidates: Iterable[dict[str, Any]], available: dict[str, list[dict[str, Any]]]
) -> list[dict[str, Any]]:
    """One entry per asset id: a stored scene can list the same asset twice."""

    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for candidate in candidates:
        asset_id = str(candidate.get("asset_id") or "")
        if asset_id and asset_id in available and asset_id not in seen:
            seen.add(asset_id)
            unique.append(candidate)
    return unique


# --------------------------------------------------------------------------- #
# Technical categories and the coverage-driven shortlist
# --------------------------------------------------------------------------- #


def categorize(scene: dict[str, Any]) -> tuple[set[str], str | None, str]:
    """Technical tags for one scene, plus what the metadata-only arm does with it."""

    semantic = _semantic_scene(scene["semantic_scene"])
    candidates = [_strip_ranker_output(c) for c in scene["raw_candidates"]]
    selected, ranked = select_best_with_video(
        semantic,
        candidates,
        prefer_video=scene["prefer_video"],
        used_asset_ids=set(),
        required_duration_sec=scene["required_duration_sec"],
        require_provider_metadata=scene["require_provider_metadata"],
        source_class=scene["source_class"],
    )
    ranked_by_id = {str(item.get("asset_id")): item for item in ranked}

    categories: set[str] = set()
    if semantic.must_include:
        categories.add("must_include_declared")
    if semantic.must_not_include:
        categories.add("must_avoid_declared")
    if semantic.conflicting_context:
        categories.add("declared_conflicting_context")
    if semantic.visual_priority in {"exact_subject", "exact_action"}:
        categories.add("subject_mismatch_risk")

    for candidate in candidates:
        evidence = build_evidence(candidate)
        media_type = str(candidate.get("media_type") or candidate.get("type") or "")
        if media_type == "video" and any(
            contains_concept(term, evidence.token_set, evidence.text) for term in NON_REAL_VIDEO_TERMS
        ):
            categories.add("non_real_footage_risk")
        if any(contains_concept(term, evidence.token_set, evidence.text) for term in TEXT_LOGO_TERMS):
            categories.add("visible_text_or_logo_risk")
        if any(contains_concept(term, evidence.token_set, evidence.text) for term in CAPTIVE_TERMS):
            categories.add("environment_conflict_risk")
        if not (candidate.get("width") and candidate.get("height")):
            categories.add("technical_dimensions_unknown")
        if not candidate.get("allowed_for_render", True) or candidate.get("review_required"):
            categories.add("rights_blocked_candidate")
        scored = ranked_by_id.get(str(candidate.get("asset_id")), {})
        if str(scored.get("framing_status") or "") in FRAMING_CONCERN:
            categories.add("crop_framing_concern")
        if str(scored.get("support_status") or "") in REVIEW_SUPPORT:
            categories.add("ambiguous_needs_review")

    support = str((selected or {}).get("support_status") or "")
    if selected is None:
        categories.add("no_acceptable_candidate")
    elif support in STRONG_SUPPORT:
        # The metadata-only arm already has a defensible answer here, so a future
        # Vision arm has something real to break. Without such scenes an A/B can
        # only ever look neutral or better, which would make it worthless.
        categories.add("regression_capable")
    return categories, (str(selected.get("asset_id")) if selected else None), support


def shortlist(scenes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Independent scenes covering as many technical categories as the data allows."""

    best_by_text: dict[str, dict[str, Any]] = {}
    for scene in scenes:
        key = _normalized_text(scene["scene_text"])
        current = best_by_text.get(key)
        rank = (len(scene["raw_candidates"]), len(scene["categories"]))
        if current is None or rank > (len(current["raw_candidates"]), len(current["categories"])):
            best_by_text[key] = scene
    pool = sorted(best_by_text.values(), key=lambda s: s["scene_key"])

    chosen: list[dict[str, Any]] = []
    per_project: Counter = Counter()
    covered: set[str] = set()
    while pool and len(chosen) < TARGET_SCENES:
        pool.sort(
            key=lambda s: (
                -len(s["categories"] - covered),
                per_project[s["project"]],
                -len(s["raw_candidates"]),
                s["scene_key"],
            )
        )
        picked = next((s for s in pool if per_project[s["project"]] < MAX_SCENES_PER_PROJECT), None)
        if picked is None:
            break
        pool.remove(picked)
        chosen.append(picked)
        per_project[picked["project"]] += 1
        covered |= picked["categories"]
    return sorted(chosen, key=lambda s: s["scene_key"])


# --------------------------------------------------------------------------- #
# Freezing
# --------------------------------------------------------------------------- #


def _rank(scene: dict[str, Any], *, drop_archival: bool) -> list[dict[str, Any]]:
    _selected, ranked = select_best_with_video(
        _semantic_scene(scene["semantic_scene"]),
        [_strip_ranker_output(c, drop_archival=drop_archival) for c in scene["raw_candidates"]],
        prefer_video=scene["prefer_video"],
        used_asset_ids=set(),
        required_duration_sec=scene["required_duration_sec"],
        require_provider_metadata=scene["require_provider_metadata"],
        source_class=scene["source_class"],
    )
    return ranked


def _assert_archival_keys_are_inert(scene: dict[str, Any]) -> None:
    """Prove, per scene, that the dropped archival copies change no verdict."""

    def signature(ranked: list[dict[str, Any]]) -> list[tuple[Any, ...]]:
        return [
            (
                str(item.get("asset_id")),
                bool(item.get("rejected")),
                str(item.get("support_status")),
                str(item.get("slot_verdict")),
                item.get("final_score"),
                tuple(item.get("blocking_reject_reasons") or ()),
            )
            for item in ranked
        ]

    full = signature(_rank(scene, drop_archival=False))
    reduced = signature(_rank(scene, drop_archival=True))
    if full != reduced:
        raise RuntimeError(
            f"{scene['scene_key']}: dropping archival keys changed the decision; keep them"
        )


def build_corpus() -> dict[str, Any]:
    scenes = collect_scenes()
    for scene in scenes:
        categories, _selected, _support = categorize(scene)
        scene["categories"] = categories
    picked = shortlist(scenes)

    corpus_scenes: list[dict[str, Any]] = []
    for scene in picked:
        key = scene["scene_key"]
        asset_ids = [str(c.get("asset_id") or "") for c in scene["raw_candidates"]]
        blind = assign_blind_ids(key, asset_ids)
        _assert_archival_keys_are_inert(scene)
        entries = [
            {
                "blind_id": blind[str(candidate.get("asset_id"))],
                "asset_id": str(candidate.get("asset_id")),
                # Where this candidate sat in the project manifest. Kept because
                # ranking is a stable sort, so the input order breaks ties; the
                # stored order is blind so the file itself shows no ranking.
                "input_order": index,
                "frames": scene["frames"][str(candidate.get("asset_id"))],
                "candidate": _strip_ranker_output(candidate, drop_archival=True),
            }
            for index, candidate in enumerate(scene["raw_candidates"])
        ]
        entries.sort(key=lambda entry: int(entry["blind_id"][1:]))
        corpus_scenes.append(
            {
                "scene_key": key,
                "project": scene["project"],
                "scene_id": scene["scene_id"],
                "scene_text": scene["scene_text"],
                "semantic_scene": scene["semantic_scene"],
                "required_duration_sec": scene["required_duration_sec"],
                "source_class": scene["source_class"],
                "require_provider_metadata": scene["require_provider_metadata"],
                "prefer_video": scene["prefer_video"],
                "target_aspect_ratio": scene["target_aspect_ratio"],
                "categories": sorted(scene["categories"]),
                "candidates": entries,
            }
        )

    corpus: dict[str, Any] = {
        "schema_version": CORPUS_SCHEMA_VERSION,
        "corpus_version": CORPUS_VERSION,
        # Stamped, not inferred: everything under ``projects/`` predates the
        # current query stack, so a harvest of it can only ever be historical.
        "fixture_kind": FIXTURE_KIND_HISTORICAL_CORPUS,
        "generation_class": GENERATION_HISTORICAL,
        "built_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "plan_step": "PLAN-9D-A",
        "source": "local project asset manifests and review manifests; no network or paid call",
        "evaluation_constants": {
            "used_asset_ids": "empty - every benchmark scene is judged on its own",
            "vision_tags": "empty - this corpus is the metadata-only arm",
            "framing": "production dimensions come from the candidate record, never from the cached preview",
        },
        "scene_count": len(corpus_scenes),
        "observation_count": sum(len(s["candidates"]) for s in corpus_scenes),
        "scenes": corpus_scenes,
        "corpus_sha256": "",
    }
    corpus["corpus_sha256"] = corpus_digest(corpus)
    return corpus


def annotation_template(corpus: dict[str, Any]) -> dict[str, Any]:
    """An empty label sheet for a *current* capture, and for nothing else.

    Blind owner annotation is expensive and happens once (PLAN-9D-D). Spending it
    on a historical pool would freeze a human answer about candidates the current
    retrieval path would never return, so the gate is here rather than in a note.
    """

    assert_current_benchmark_input(corpus, context="annotation template")
    return {
        "schema_version": ANNOTATIONS_SCHEMA_VERSION,
        "corpus_version": corpus["corpus_version"],
        "corpus_sha256": corpus["corpus_sha256"],
        "blind": True,
        "annotator": "",
        "annotated_at_utc": "",
        "status": STATUS_WAITING,
        "scenes": [
            {
                "scene_key": scene["scene_key"],
                "preferred_candidate": "",
                "unacceptable_candidates": [],
                "note": "",
                "candidates": {
                    candidate["blind_id"]: {name: "" for name in CANDIDATE_FLAG_SPEC}
                    for candidate in scene["candidates"]
                },
            }
            for scene in corpus["scenes"]
        ],
    }


# --------------------------------------------------------------------------- #
# Curating the historical failure evidence
# --------------------------------------------------------------------------- #

#: Which historical scenes are kept, and what each one is kept *for*.
#:
#: Curation, not sampling. Several scenes demonstrate the same defect - five
#: separate projects were served by the same retired broad literal - and keeping
#: all of them would archive the runtime tree rather than preserve the proof.
#: Three are kept where the repetition itself is the evidence, one per remaining
#: distinct failure. Everything a case claims is checkable against the record
#: curated with it; ``expected_subject_terms`` is the curator's reading of the
#: scene text, and is labelled as such rather than presented as a system output.
#:
#: The project names live here, in the hand-run tool, and never in the harness:
#: the harness has to outlive this data.
HISTORICAL_CASES: tuple[dict[str, Any], ...] = (
    {
        "case_id": "gecko_subject_free_broad_query",
        "project": "почему_геккон_не_падает_с_гладкого_стекла_20260723T172318",
        "scene_id": "scene_001",
        "expected_subject_terms": ("геккон", "gecko"),
        "failure_modes": (
            "subject_absent_from_provider_query",
            "retired_broad_query_literal",
            "shared_generic_candidate_pool",
        ),
        "retired_query_class": "C36",
        "note": (
            "The scene asks why a gecko does not fall off glass. No visual brief was produced, "
            "and every provider was asked the same subject-free literal."
        ),
    },
    {
        "case_id": "hummingbird_subject_free_broad_query",
        "project": "почему_колибри_может_зависать_в_воздухе_и_лететь_назад_20260723T172315",
        "scene_id": "scene_001",
        "expected_subject_terms": ("колибри", "hummingbird"),
        "failure_modes": (
            "subject_absent_from_provider_query",
            "retired_broad_query_literal",
            "shared_generic_candidate_pool",
        ),
        "retired_query_class": "C36",
        "note": "A different project, a different subject, the same literal and the same pool.",
    },
    {
        "case_id": "penguin_subject_free_broad_query",
        "project": "почему_пингвины_скользят_по_снегу_на_животе_20260723T172320",
        "scene_id": "scene_001",
        "expected_subject_terms": ("пингвин", "penguin"),
        "failure_modes": (
            "subject_absent_from_provider_query",
            "retired_broad_query_literal",
            "shared_generic_candidate_pool",
        ),
        "retired_query_class": "C36",
        "note": (
            "The third independent project served by the same pool. Three subjects that share "
            "one candidate set is the defect, not a coincidence worth deduplicating away."
        ),
    },
    {
        "case_id": "cyrillic_query_to_latin_provider",
        "project": "2026-07-26_nanoplastik-nayden-v-pochvah-antarktidy",
        "scene_id": "scene_007",
        "expected_subject_terms": ("plastic",),
        "failure_modes": ("non_provider_language_query",),
        "retired_query_class": "CRITICAL-1 (before PLAN-9B-1)",
        "note": (
            "A Russian query was sent verbatim to English-language stock indexes. Three providers "
            "returned nothing at all; the two that answered matched on nothing the scene declared."
        ),
    },
    {
        "case_id": "subject_lost_between_primary_query_and_provider",
        "project": "почему_кошка_иногда_смотрит_в_пустой_угол_20260724T151947",
        "scene_id": "scene_001",
        "expected_subject_terms": ("cat", "кошка"),
        "failure_modes": (
            "degenerate_single_token_query",
            "subject_lost_after_primary_query",
            "subject_absent_from_provider_query",
        ),
        "retired_query_class": "degenerate query ladder (before PLAN-9B-1)",
        "note": (
            "The strongest single case: the scene *did* produce a usable primary query naming the "
            "subject, and every provider was nevertheless asked one adjective."
        ),
    },
    {
        "case_id": "glossary_substitute_for_extracted_stopwords",
        "project": "2026-07-27_pochemu-kosatki-vzryvayut-ogromnyh-ryb",
        "scene_id": "scene_006",
        "expected_subject_terms": (),
        "failure_modes": ("garbage_subject_extraction", "degenerate_single_token_query"),
        "retired_query_class": "deterministic_glossary substitution (before PLAN-9B-1)",
        "note": (
            "The semantic scene took Russian function words as subject and action, and the "
            "glossary turned that into one English token."
        ),
    },
    {
        "case_id": "orca_topic_query_hardcode",
        "project": "2026-07-28_pochemu-kosatki-vzryvayut-ogromnyh-ryb-2",
        "scene_id": "scene_002",
        "expected_subject_terms": ("orca",),
        "failure_modes": (
            "retired_topic_query_hardcode",
            "degenerate_single_token_query",
            "mislabelled_query_language",
        ),
        "retired_query_class": "C35",
        "note": (
            "The visual brief carries the retired one-topic hardcode verbatim, down to the German "
            "Wikimedia query that the attempt record labels as English."
        ),
    },
)

#: Retired query classes the preserved cases demonstrate. Recorded as data rather
#: than checked against production: the compatibility guard that still recognises
#: the broad literal has its own exit condition, and this evidence has to survive
#: that removal.
RETIRED_QUERY_CLASSES: tuple[dict[str, Any], ...] = (
    {
        "registry_id": "C36",
        "literal": "nature science wildlife observation",
        "what": "subject-free broad literal appended to every scene of a legacy visual plan",
        "retired_in_commit": "72221e1",
        "still_recognised_by": "src/assets/query_adapter.py::_LEGACY_BROAD_QUERIES (persisted-plan guard)",
    },
    {
        "registry_id": "C35",
        "literal": "",
        "what": "one-topic (orca) provider_queries hardcode in src/news/script_generator.py",
        "retired_in_commit": "72221e1",
        "still_recognised_by": "",
    },
)


def _manifest_scene(project: str, scene_id: str) -> dict[str, Any]:
    path = PROJECTS_ROOT / project / "assets" / "assets_manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    for scene in manifest.get("scenes") or []:
        if str(scene.get("scene_id")) == scene_id:
            return scene
    raise RuntimeError(f"{project}/{scene_id}: not found in {path}")


def _unique_attempts(scene: dict[str, Any]) -> list[dict[str, Any]]:
    """What actually reached each provider, once per distinct attempt.

    Retries repeat verbatim in the stored manifest; the repetition says nothing
    about the defect, and the distinct set is what the evidence rests on.
    """

    seen: list[dict[str, Any]] = []
    for attempt in scene.get("provider_attempts") or []:
        record = {
            "provider": str(attempt.get("provider") or ""),
            "query": str(attempt.get("query") or ""),
            "query_language": str(attempt.get("query_language") or ""),
            "query_source": str(attempt.get("query_source") or ""),
            "result_count": int(attempt.get("result_count") or 0),
        }
        if record not in seen:
            seen.append(record)
    return seen


def _minimal_candidate(candidate: dict[str, Any], frames: list[dict[str, Any]]) -> dict[str, Any]:
    """Enough provider metadata to show what came back, and nothing more.

    Rights, scores, download paths and the archival copies of the same record are
    dropped: this fixture is never fed to the decision owner, so the fields that
    exist for the decision owner would be dead weight that only invites the
    misuse PLAN-9D-A exists to prevent.
    """

    record: dict[str, Any] = {
        "asset_id": str(candidate.get("asset_id") or ""),
        "provider": str(candidate.get("provider") or ""),
        "provider_asset_id": str(candidate.get("provider_asset_id") or ""),
        "media_type": str(candidate.get("media_type") or candidate.get("type") or ""),
        "title": str(candidate.get("title") or ""),
        "tags": [str(tag) for tag in (candidate.get("tags") or candidate.get("keywords") or [])],
        # Kept because it is itself part of the evidence: where the pools came
        # from a subject-free query, the stored "tags" are that query echoed
        # back, so the metadata gate had nothing of the provider's to read.
        "tags_source": str(candidate.get("tags_source") or ""),
        "width": int(candidate.get("width") or 0),
        "height": int(candidate.get("height") or 0),
        "search_query": str(candidate.get("search_query") or ""),
        "source_url": str(candidate.get("source_page_url") or candidate.get("source_url") or ""),
    }
    representative = min(frames, key=lambda frame: int(frame.get("frame_index") or 0), default=None)
    record["representative_frame"] = (
        {
            "local_frame_path": str(representative["local_frame_path"]),
            "sha256": str(representative["sha256"]),
            "width": int(representative.get("width") or 0),
            "height": int(representative.get("height") or 0),
            "frame_index": int(representative.get("frame_index") or 0),
        }
        if representative
        else None
    )
    return record


def curate_historical_evidence(
    source_corpus: dict[str, Any],
    *,
    manifest_reader: Callable[[str, str], dict[str, Any]] = _manifest_scene,
) -> dict[str, Any]:
    """Compact the frozen historical corpus down to the proof it contains.

    The frozen corpus supplies the candidate pools and the frames, exactly as
    they were audited; the project manifests supply what the corpus never
    recorded and the evidence needs most - the visual brief, the query ladder and
    the attempt log showing which query each provider was actually given.

    ``manifest_reader`` is injectable so the curation rules stay testable once
    the runtime tree this was curated from is gone.
    """

    by_key = {str(scene["scene_key"]): scene for scene in source_corpus["scenes"]}
    preserved_keys: set[str] = set()
    cases: list[dict[str, Any]] = []

    for spec in HISTORICAL_CASES:
        scene_key = f"{spec['project']}/{spec['scene_id']}"
        frozen = by_key.get(scene_key)
        if frozen is None:
            raise RuntimeError(f"{scene_key}: not present in the source corpus")
        preserved_keys.add(scene_key)
        manifest_scene = manifest_reader(spec["project"], spec["scene_id"])
        brief = manifest_scene.get("visual_brief")

        candidates = [
            _minimal_candidate(entry["candidate"], entry.get("frames") or [])
            for entry in sorted(frozen["candidates"], key=lambda item: int(item["input_order"]))
        ]
        frozen_assets = {str(entry["asset_id"]) for entry in frozen["candidates"]}
        if {c["asset_id"] for c in candidates} != frozen_assets:
            raise RuntimeError(f"{scene_key}: curated pool does not match the frozen pool")

        cases.append(
            {
                "case_id": spec["case_id"],
                "failure_modes": list(spec["failure_modes"]),
                "note": spec["note"],
                "source_project": spec["project"],
                "source_scene_id": spec["scene_id"],
                "scene_key": scene_key,
                "scene_text": frozen["scene_text"],
                "expected_subject_terms": list(spec["expected_subject_terms"]),
                "expected_subject_terms_source": "curator, read from scene_text",
                "historical_semantic_scene": frozen["semantic_scene"],
                "visual_brief_present": bool(brief),
                "visual_brief_provider_queries": (brief or {}).get("provider_queries") or {},
                "historical_primary_query": str(manifest_scene.get("primary_query") or ""),
                "historical_query_ladder": [
                    {
                        "kind": str(entry.get("kind") or ""),
                        "fallback_level": int(entry.get("fallback_level") or 0),
                        "query": str(entry.get("query") or ""),
                    }
                    for entry in manifest_scene.get("queries") or []
                ],
                "historical_provider_attempts": _unique_attempts(manifest_scene),
                "retired_query_class": spec["retired_query_class"],
                "historical_selected_asset_id": str(
                    (manifest_scene.get("selected_asset") or {}).get("asset_id") or ""
                ),
                "source_manifests": [
                    f"projects/{spec['project']}/assets/assets_manifest.json",
                    f"projects/{spec['project']}/assets/review/visual_review_manifest.json",
                ],
                "candidates": candidates,
            }
        )

    preserved_literals = {
        str(attempt["query"]) for case in cases for attempt in case["historical_provider_attempts"]
    }
    dropped = []
    for scene_key, scene in sorted(by_key.items()):
        if scene_key in preserved_keys:
            continue
        literals = sorted(
            {
                str(entry["candidate"].get("search_query") or "")
                for entry in scene["candidates"]
                if entry["candidate"].get("search_query")
            }
        )
        duplicate = sorted(set(literals) & preserved_literals)
        dropped.append(
            {
                "scene_key": scene_key,
                "queries": literals,
                "reason": (
                    "duplicate_evidence: the same retired query is already preserved by a curated case"
                    if duplicate
                    else "no_curated_failure_mode: nothing in this scene demonstrates a retrieval "
                    "failure from the curated vocabulary"
                ),
                "duplicates_preserved_query": duplicate,
            }
        )

    fixture: dict[str, Any] = {
        "schema_version": HISTORICAL_EVIDENCE_SCHEMA_VERSION,
        "fixture_kind": FIXTURE_KIND_HISTORICAL_EVIDENCE,
        "generation_class": GENERATION_HISTORICAL,
        "fixture_version": HISTORICAL_EVIDENCE_VERSION,
        "plan_step": "PLAN-9D-A",
        "built_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "not_a_benchmark": (
            "Historical failure evidence, retrieved by the query stack that PLAN-9B-1..9B-3 and "
            "PLAN-9C retired. It proves the defects were real. It measures nothing about current "
            "decision quality and must never be used as a benchmark input; the current capture is "
            "PLAN-9D-B and the owner ground truth is PLAN-9D-D."
        ),
        "derived_from": {
            "corpus_version": str(source_corpus["corpus_version"]),
            "corpus_sha256": str(source_corpus["corpus_sha256"]),
            "corpus_path": SUPERSEDED_CORPUS_PATH,
            "corpus_commit": SUPERSEDED_CORPUS_COMMIT,
            "corpus_scene_count": int(source_corpus["scene_count"]),
            "corpus_observation_count": int(source_corpus["observation_count"]),
        },
        "source": "local project asset manifests and review manifests; no network or paid call",
        "retired_query_classes": [dict(entry) for entry in RETIRED_QUERY_CLASSES],
        "failure_mode_vocabulary": list(HISTORICAL_FAILURE_MODES),
        "case_count": len(cases),
        "candidate_count": sum(len(case["candidates"]) for case in cases),
        "frame_count": sum(
            1 for case in cases for c in case["candidates"] if c.get("representative_frame")
        ),
        "cases": cases,
        "dropped_source_scenes": dropped,
        "fixture_sha256": "",
    }
    fixture["fixture_sha256"] = historical_digest(fixture)
    return fixture


# --------------------------------------------------------------------------- #
# The blind annotation pack
# --------------------------------------------------------------------------- #

_PACK_STYLE = """
body{font:15px/1.5 system-ui,sans-serif;margin:0;padding:24px;background:#12141a;color:#e7e9ee}
h1{font-size:20px}h2{font-size:17px;margin:0 0 8px}
.scene{border:1px solid #2b2f3a;border-radius:10px;padding:16px;margin:0 0 22px;background:#181b23}
.req{background:#11131a;border-left:3px solid #4c6ef5;padding:10px 12px;margin:0 0 14px;border-radius:4px}
.req dt{font-weight:600;color:#9aa4bf;float:left;clear:left;width:190px}
.req dd{margin:0 0 4px 200px}
.cands{display:flex;flex-wrap:wrap;gap:14px}
.cand{border:1px solid #2b2f3a;border-radius:8px;padding:10px;background:#1e222c;width:260px}
.cand h3{margin:0 0 8px;font-size:15px}
.cand img{max-width:100%;border-radius:4px;display:block;margin:0 0 4px;background:#000}
.flags label{display:block;font-size:12px;color:#9aa4bf;margin:6px 0 0}
.flags select{width:100%;background:#12141a;color:#e7e9ee;border:1px solid #333947;border-radius:4px;padding:3px}
.best{margin:12px 0 0}.best select{background:#12141a;color:#e7e9ee;border:1px solid #4c6ef5;border-radius:4px;padding:5px}
.note{width:100%;background:#12141a;color:#e7e9ee;border:1px solid #333947;border-radius:4px;padding:6px;margin:8px 0 0}
.bar{position:sticky;top:0;background:#12141a;padding:12px 0;border-bottom:1px solid #2b2f3a;margin:0 0 20px;z-index:5}
button{background:#4c6ef5;color:#fff;border:0;border-radius:6px;padding:9px 16px;font-size:14px;cursor:pointer}
.warn{color:#ffa94d}
"""

_PACK_SCRIPT = """
function collect(){
  const scenes=[...document.querySelectorAll('.scene')].map(el=>{
    const cands={};
    el.querySelectorAll('.cand').forEach(c=>{
      const id=c.dataset.blind;const flags={};
      c.querySelectorAll('select[data-flag]').forEach(s=>{flags[s.dataset.flag]=s.value;});
      cands[id]=flags;
    });
    return {
      scene_key:el.dataset.key,
      preferred_candidate:el.querySelector('select[data-best]').value,
      unacceptable_candidates:[...el.querySelectorAll('input[data-bad]:checked')].map(i=>i.dataset.bad),
      note:el.querySelector('textarea').value,
      candidates:cands
    };
  });
  return {
    schema_version:PACK.schema_version,
    corpus_version:PACK.corpus_version,
    corpus_sha256:PACK.corpus_sha256,
    blind:true,
    annotator:document.getElementById('annotator').value.trim(),
    annotated_at_utc:new Date().toISOString().replace(/\\.\\d+Z$/,'Z'),
    status:'COMPLETE',
    scenes:scenes
  };
}
function save(){
  const data=collect();
  const missing=data.scenes.filter(s=>!s.preferred_candidate).map(s=>s.scene_key);
  if(!data.annotator){alert('Укажите annotator.');return;}
  if(missing.length){alert('Не заполнено BEST в сценах:\\n'+missing.join('\\n'));return;}
  const blob=new Blob([JSON.stringify(data,null,1)],{type:'application/json'});
  const a=document.createElement('a');
  a.href=URL.createObjectURL(blob);a.download='annotations_v1.json';a.click();
}
"""


def render_pack(corpus: dict[str, Any]) -> str:
    """A disposable, offline, evaluation-only page. Not a product frontend.

    What it shows is the whole point: the scene's stated requirement and the
    pictures, under blind identifiers. Provider, title, description, licence,
    every score, the ranker's answer and the corpus categories all stay behind.

    Same gate as the template it feeds: a pack is only ever rendered for the
    frozen current capture.
    """

    assert_current_benchmark_input(corpus, context="annotation pack")
    parts: list[str] = [
        "<!doctype html><meta charset='utf-8'>",
        "<title>PLAN-9D-A blind annotation pack</title>",
        f"<style>{_PACK_STYLE}</style>",
        "<div class='bar'><h1>PLAN-9D-A — слепая разметка</h1>",
        "<p>Выберите лучший кандидат по <b>смыслу сцены</b>. Права, лицензии, "
        "технические размеры и качество метаданных оценивать не нужно — это решает система. "
        "<span class='warn'>Кандидаты обезличены; порядок не отражает оценку системы.</span></p>",
        "<p>Annotator: <input id='annotator' placeholder='имя или псевдоним'> "
        "<button onclick='save()'>Сохранить annotations_v1.json</button></p></div>",
    ]
    for scene in corpus["scenes"]:
        semantic = scene.get("semantic_scene") or {}
        parts.append(
            f"<div class='scene' data-key=\"{html.escape(scene['scene_key'])}\">"
            f"<h2>{html.escape(scene['scene_text'] or scene['scene_key'])}</h2><dl class='req'>"
        )
        for label, key in (
            ("Субъект", "subject"),
            ("Действие", "action"),
            ("Среда", "environment"),
            ("Место", "location"),
            ("Должно быть в кадре", "must_include"),
            ("Не должно быть в кадре", "must_not_include"),
            ("Заявленный контекст", "context"),
            ("Заявленное противоречие", "conflicting_context"),
        ):
            values = [str(v) for v in (semantic.get(key) or []) if str(v).strip()]
            if values:
                parts.append(
                    f"<dt>{label}</dt><dd>{html.escape(', '.join(values))}</dd>"
                )
        parts.append(
            f"<dt>Кадр</dt><dd>{html.escape(str(scene.get('target_aspect_ratio') or ''))}, "
            f"{scene.get('required_duration_sec', 0)} с</dd></dl><div class='cands'>"
        )
        for candidate in scene["candidates"]:
            blind_id = html.escape(str(candidate["blind_id"]))
            parts.append(f"<div class='cand' data-blind='{blind_id}'><h3>{blind_id}</h3>")
            for frame in candidate["frames"]:
                url = (REPO_ROOT / frame["local_frame_path"]).resolve().as_uri()
                parts.append(f"<img loading='lazy' src=\"{html.escape(url)}\" alt='{blind_id}'>")
            parts.append(
                f"<label><input type='checkbox' data-bad='{blind_id}'> неприемлем</label><div class='flags'>"
            )
            for name, allowed in CANDIDATE_FLAG_SPEC.items():
                options = "".join(f"<option value='{v}'>{v}</option>" for v in ("", *allowed))
                parts.append(
                    f"<label>{html.escape(name)}<select data-flag='{html.escape(name)}'>{options}</select></label>"
                )
            parts.append("</div></div>")
        best_options = "".join(
            f"<option value='{html.escape(str(c['blind_id']))}'>{html.escape(str(c['blind_id']))}</option>"
            for c in scene["candidates"]
        )
        parts.append(
            "</div><div class='best'><b>BEST:</b> <select data-best><option value=''>—</option>"
            f"{best_options}<option value='none_acceptable'>none_acceptable</option>"
            "<option value='undecidable'>undecidable</option></select></div>"
            "<textarea class='note' rows='2' placeholder='комментарий (необязательно)'></textarea></div>"
        )
    pack_meta = {
        "schema_version": ANNOTATIONS_SCHEMA_VERSION,
        "corpus_version": corpus["corpus_version"],
        "corpus_sha256": corpus["corpus_sha256"],
    }
    parts.append(f"<script>const PACK={canonical_json(pack_meta)};{_PACK_SCRIPT}</script>")
    return "".join(parts)


_REVIEW_STYLE = """
body{font:15px/1.5 system-ui,sans-serif;margin:0;padding:24px;background:#12141a;color:#e7e9ee}
h1{font-size:20px;margin:0 0 6px}h2{font-size:17px;margin:0 0 8px}
.scene{border:1px solid #2b2f3a;border-radius:10px;padding:16px;margin:0 0 22px;background:#181b23}
.req{background:#11131a;border-left:3px solid #4c6ef5;padding:10px 12px;margin:0 0 14px;border-radius:4px}
.req dt{font-weight:600;color:#9aa4bf;float:left;clear:left;width:190px}
.req dd{margin:0 0 4px 200px}
.cands{display:flex;flex-wrap:wrap;gap:14px}
.cand{border:1px solid #2b2f3a;border-radius:8px;padding:10px;background:#1e222c;width:260px}
.cand h3{margin:0 0 8px;font-size:15px}
.cand img{max-width:100%;border-radius:4px;display:block;margin:0 0 4px;background:#000}
.bar{position:sticky;top:0;background:#12141a;padding:12px 0;border-bottom:1px solid #2b2f3a;margin:0 0 20px;z-index:5}
.warn{color:#ffa94d}.muted{color:#9aa4bf;font-size:13px}
"""


def render_review_pack(corpus: dict[str, Any]) -> str:
    """A read-only contact sheet over a frozen current capture (PLAN-9D-C).

    Deliberately *not* the annotation pack. There is no field to fill in, no BEST
    selector, no save button and no unacceptable checkbox: PLAN-9D-D is the one
    place an owner label may be produced, once, and producing one here would spend
    that pass on a page nobody promised to freeze.

    It shows what a reviewer needs to judge whether the pool is worth measuring at
    all - the scene's stated requirement and the pictures - and withholds
    everything that would tell them the answer: the provider, the title, the
    licence, every score, the ranker's choice and any Vision evidence. Candidates
    keep their blind identifiers, so a finding here can still be named in a way
    PLAN-9D-D will recognise.
    """

    assert_current_benchmark_input(corpus, context="review pack")
    parts: list[str] = [
        "<!doctype html><meta charset='utf-8'>",
        "<title>PLAN-9D-C candidate review pack</title>",
        f"<style>{_REVIEW_STYLE}</style>",
        "<div class='bar'><h1>PLAN-9D-C — просмотр пула кандидатов</h1>",
        "<p class='muted'>Материал для чтения, не разметка. Кандидаты обезличены; "
        "порядок не отражает оценку системы. Выбор системы, провайдер, лицензия, "
        "метаданные, любые оценки и Vision-выводы намеренно не показаны. "
        "<span class='warn'>Ground truth здесь не собирается — это PLAN-9D-D.</span></p>",
        f"<p class='muted'>corpus_version {html.escape(str(corpus.get('corpus_version') or ''))} · "
        f"capture_head_sha {html.escape(str(corpus.get('capture_head_sha') or ''))} · "
        f"corpus_sha256 {html.escape(str(corpus.get('corpus_sha256') or ''))}</p></div>",
    ]
    for scene in corpus["scenes"]:
        semantic = scene.get("semantic_scene") or {}
        parts.append(
            f"<div class='scene' data-key=\"{html.escape(str(scene['scene_key']))}\">"
            f"<h2>{html.escape(str(scene.get('scene_text') or scene['scene_key']))}</h2><dl class='req'>"
        )
        for label, key in (
            ("Субъект", "subject"),
            ("Действие", "action"),
            ("Среда", "environment"),
            ("Место", "location"),
            ("Должно быть в кадре", "must_include"),
            ("Не должно быть в кадре", "must_not_include"),
            ("Заявленный контекст", "context"),
            ("Заявленное противоречие", "conflicting_context"),
        ):
            values = [str(item) for item in (semantic.get(key) or []) if str(item).strip()]
            if values:
                parts.append(f"<dt>{label}</dt><dd>{html.escape(', '.join(values))}</dd>")
        parts.append(
            f"<dt>Кадр</dt><dd>{html.escape(str(scene.get('target_aspect_ratio') or ''))}, "
            f"{scene.get('required_duration_sec', 0)} с</dd>"
            f"<dt>Кандидатов в пуле</dt><dd>{len(scene['candidates'])}</dd>"
            "</dl><div class='cands'>"
        )
        for candidate in scene["candidates"]:
            blind_id = html.escape(str(candidate["blind_id"]))
            parts.append(f"<div class='cand' data-blind='{blind_id}'><h3>{blind_id}</h3>")
            frames = candidate.get("frames") or []
            if not frames:
                parts.append("<p class='muted'>превью не снималось</p>")
            for frame in frames:
                url = (REPO_ROOT / frame["local_frame_path"]).resolve().as_uri()
                parts.append(f"<img loading='lazy' src=\"{html.escape(url)}\" alt='{blind_id}'>")
            parts.append("</div>")
        parts.append("</div></div>")
    return "".join(parts)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def load_historical_corpus(path: Path) -> dict[str, Any]:
    """Read a historical project corpus, refusing anything that is not one."""

    corpus = json.loads(path.read_text(encoding="utf-8"))
    if corpus.get("schema_version") != CORPUS_SCHEMA_VERSION:
        raise BenchmarkError(f"{path}: unexpected schema_version {corpus.get('schema_version')!r}")
    if generation_class_of(corpus) != GENERATION_HISTORICAL:
        raise BenchmarkError(f"{path}: not a historical corpus, refusing to curate it as one")
    recorded = str(corpus.get("corpus_sha256") or "")
    actual = corpus_digest(corpus)
    if recorded != actual:
        raise BenchmarkError(f"{path}: digest mismatch, recorded {recorded}, computed {actual}")
    return corpus


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PLAN-9D offline evaluation data tooling")
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build", help="harvest a historical project corpus from projects/")
    build.add_argument("--out", required=True, help="destination .json path (intermediate; keep it outside the repo)")
    curate = sub.add_parser("curate", help="compact a historical corpus into the failure evidence")
    curate.add_argument("--source-corpus", required=True, help="historical corpus produced by build")
    curate.add_argument("--out", default=str(HISTORICAL_EVIDENCE_PATH), help="destination fixture")
    pack = sub.add_parser("pack", help="render the blind annotation pack from a frozen current corpus")
    pack.add_argument("--corpus", required=True, help="frozen current corpus (PLAN-9D-B)")
    pack.add_argument("--out", required=True, help="destination .html path (keep it outside the repo)")
    review = sub.add_parser("review", help="render the read-only PLAN-9D-C candidate review pack")
    review.add_argument("--corpus", required=True, help="frozen current corpus (PLAN-9D-B)")
    review.add_argument("--out", required=True, help="destination .html path (keep it outside the repo)")
    args = parser.parse_args(argv)

    if args.command == "build":
        corpus = build_corpus()
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(corpus, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        covered = sorted({c for scene in corpus["scenes"] for c in scene["categories"]})
        print(f"historical corpus written to {out}")
        print(f"scenes={corpus['scene_count']} observations={corpus['observation_count']}")
        print(f"sha256={corpus['corpus_sha256']}")
        print("categories=" + ", ".join(covered))
        return 0

    if args.command == "curate":
        fixture = curate_historical_evidence(load_historical_corpus(Path(args.source_corpus)))
        validate_historical_evidence(fixture)
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(fixture, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"historical failure evidence written to {out}")
        print(
            f"cases={fixture['case_count']} candidates={fixture['candidate_count']} "
            f"frames={fixture['frame_count']} dropped={len(fixture['dropped_source_scenes'])}"
        )
        print(f"sha256={fixture['fixture_sha256']}")
        return 0

    corpus = json.loads(Path(args.corpus).read_text(encoding="utf-8"))
    validate_corpus(corpus)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    if args.command == "review":
        out.write_text(render_review_pack(corpus), encoding="utf-8")
        print(f"review pack written to {out}")
        return 0
    out.write_text(render_pack(corpus), encoding="utf-8")
    print(f"annotation pack written to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
