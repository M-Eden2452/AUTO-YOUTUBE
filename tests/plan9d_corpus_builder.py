"""Hand-run PLAN-9D data tooling: harvest, curate, and render the blind pack.

Not a test; nothing imports it at test time except the locks that exercise its
pure functions. Four commands, in the order they are actually used:

    build     projects/ -> a historical project corpus (intermediate, not committed)
    curate    that corpus + the manifests -> the compact historical failure evidence
    build-v2  two saved runs -> the bilingual corpus v2 (PLAN-9D-H)
    pack      a *current* frozen corpus -> the owner's blind annotation page

    .\\venv\\Scripts\\python.exe -B -m tests.plan9d_corpus_builder build --out %TEMP%\\hist.json
    .\\venv\\Scripts\\python.exe -B -m tests.plan9d_corpus_builder curate --source-corpus %TEMP%\\hist.json
    .\\venv\\Scripts\\python.exe -B -m tests.plan9d_corpus_builder build-v2
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
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
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
    CORPUS_CLASS_BLIND,
    CORPUS_CLASS_INCIDENT,
    CORPUS_SCHEMA_VERSION,
    CURRENT_ANNOTATIONS_PATH,
    CURRENT_ANNOTATIONS_V2_PATH,
    CURRENT_CORPUS_V2_PATH,
    EVIDENCE_KIND_LOCAL_FILE,
    EVIDENCE_KIND_PREVIEW,
    FIXTURE_KIND_CURRENT_BENCHMARK,
    FIXTURE_KIND_HISTORICAL_CORPUS,
    FIXTURE_KIND_HISTORICAL_EVIDENCE,
    GENERATION_CURRENT,
    GENERATION_HISTORICAL,
    HISTORICAL_EVIDENCE_PATH,
    HISTORICAL_EVIDENCE_SCHEMA_VERSION,
    HISTORICAL_FAILURE_MODES,
    STATUS_WAITING,
    BenchmarkError,
    assert_current_benchmark_input,
    annotation_identity_digest,
    assign_blind_ids,
    candidate_is_visible,
    canonical_json,
    corpus_class_of,
    corpus_digest,
    generation_class_of,
    historical_digest,
    scene_token,
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
        "must_include_unverifiable", "negative_matches", "must_avoid_unverifiable",
        "contradiction_penalty",
        "duplicate_penalty", "watermark_penalty", "fallback_level", "scene_match_score",
        "final_score", "rejected", "reject_reason", "blocking_reject_reasons",
        "advisory_reject_reasons", "why_selected", "semantic_scene", "slot_verdict",
        "meaning_tie_peers", "meaning_tie_broken_by",
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

#: Same question the query adapter asks of a string, asked here of a stored record.
#: Imported rather than restated would be better, but the adapter's copy is private
#: to it, and this one is used for counting rather than for a decision.
_CYRILLIC_RE = re.compile(r"[Ѐ-ӿ]")


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
        "annotation_identity_sha256": annotation_identity_digest(corpus),
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
# Corpus v2 - the two runs the current stack produced (PLAN-9D-H)
#
# v1 cannot see language. Its 14 subjects are English, its media index is empty,
# and 2 of 1064 candidate records carry any Cyrillic at all, so a language or
# provability fix measured on it moves nothing and passes on any edit (language
# audit 2026-08-16, K12). v2 is built from the two runs on disk that the current
# retrieval stack produced, and it is built *offline*: both projects already store
# every candidate they ranked, and re-running either one is a paid network action
# this step does not have.
#
# What this can and cannot ask, stated once so no later reader has to guess: a run
# saves the ten candidates it shortlisted and rejected per scene, not the pool it
# searched. LIVE-5 made 234 provider attempts and saw 1303 results; 100 records
# survive in its manifest. So v2 can ask "of the ten it kept, did it keep the right
# one" and can never ask "was the right answer at rank forty".
# --------------------------------------------------------------------------- #

CORPUS_V2_VERSION = "plan9d-h-2026-08-17"

#: The material owner decision 2026-08-17 named. Two runs, both after the query
#: fixes of PLAN-9B/9C, so both are current benchmark input; each carries the HEAD
#: it ran on and the report that describes it, because the two differ and a reader
#: must not have to assume one HEAD for the whole corpus.
CURRENT_RUNS: tuple[dict[str, Any], ...] = (
    {
        "run_id": "live_5",
        "project": "2026-08-15_solnechnaya-panel-lovit-svet-tolko-dnem-nochyu-2",
        "head_sha": "68c46cdd254198ba082c6d1495879badbdbcd00a",
        "run_date": "2026-08-15",
        "evidence": "docs/audits/LIVE_5_2026-08-15.md",
        "what_it_was": (
            "paid live run: providers searched and previews downloaded, 5 scenes, "
            "verdict PARTIAL (2 of 5 scenes right by meaning)"
        ),
    },
    {
        "run_id": "local_after_fix",
        "project": "2026-08-14_solnechnaya-panel-lovit-svet-tolko-dnem-nochyu-3",
        "head_sha": "a8549ff995c64ace5a5e3a32521df104a2e06ba3",
        "run_date": "2026-08-14",
        "evidence": "docs/audits/FIRST_OWNER_SHORT_LOCAL_SOLAR_AFTER_CYRILLIC_FIX_2026-08-14.md",
        "what_it_was": (
            "local diagnostic after the Cyrillic tokenisation fix: the curated local "
            "library answered 5 of 5 scenes, 2 frames good and 2 bad by eye"
        ),
    },
)

#: Requirements written by hand on a real pool, to reproduce one named mechanism.
#: Both runs declared **no** prohibition at all - ``must_not_include`` is empty in
#: all ten scenes - so the ban layer cannot be measured from captured data, and the
#: MAJOR of the package-A review ("the author's ban does not see declensions")
#: would have nothing to be accepted against.
#:
#: The one case here is chosen because the contrast lives *inside* the scene: on the
#: same ban word, one real candidate is caught literally and its twin is not. Both
#: carry Russian metadata from the same curated library; the only difference is the
#: grammatical case the provider's title happens to use.
INCIDENT_SCENES: tuple[dict[str, Any], ...] = (
    {
        "case_id": "ban_declension_cooling_tower",
        "run_id": "local_after_fix",
        "scene_id": "scene_004",
        "scene_text": (
            "Покажите электростанцию, вырабатывающую электричество, "
            "но без градирен в кадре."
        ),
        "semantic_scene": {
            "subject": ["электростанция"],
            "action": ["вырабатывает электричество"],
            "environment": ["энергетика"],
            "location": [],
            "must_include": [],
            "must_not_include": ["градирня"],
            "should_include": [],
            "context": [],
            "conflicting_context": [],
            "secondary_subjects": [],
            "camera": [],
            "mood": [],
            "visual_priority": "exact_subject",
            "fallback_level": 1,
        },
        "categories": ["must_avoid_declared", "subject_mismatch_risk"],
        "incident_note": (
            "Требование и запрет написаны рукой (PLAN-9D-H), кандидаты и их "
            "метаданные - настоящие, из прогона local_after_fix/scene_004. "
            "Воспроизводит MAJOR-1 ревью пакета A: запрет 'градирня' буквально "
            "совпадает с записью pexels_6468629 ('атомная станция ... градирнями' "
            "плюс ключевое слово в именительном) и не совпадает с pexels_29491854 "
            "('Градирни атомной станции на закате'), хотя положительная сторона "
            "оценки после C79 считает обе записи полным совпадением слова. "
            "Русское требование здесь не украшение: v1 не содержит ни одного "
            "русского субъекта, а §4A языкового аудита показал, что русское "
            "требование делает semantic_unverified блокирующим для всего пула."
        ),
    },
)


def _run_project_root(run: dict[str, Any]) -> Path:
    return PROJECTS_ROOT / str(run["project"])


def _preview_cache_index(project_root: Path) -> dict[str, dict[str, Any]]:
    """Cached provider previews of one run, keyed by the URL they were fetched from.

    The record carries the size and the digest the run itself computed, so nothing
    here re-reads or re-downloads a picture to describe it.
    """

    index: dict[str, dict[str, Any]] = {}
    previews = project_root / "assets" / "previews"
    if not previews.is_dir():
        return index
    for directory in sorted(previews.iterdir()):
        record_path = directory / "preview_record.json"
        if not record_path.is_file():
            continue
        record = json.loads(record_path.read_text(encoding="utf-8"))
        url = str(record.get("preview_source_url") or "")
        local = Path(str(record.get("local_path") or ""))
        if not url or not local.is_file():
            continue
        index[url] = {
            "local_path": local,
            "sha256": str(record.get("sha256") or ""),
            "width": int(record.get("width") or 0),
            "height": int(record.get("height") or 0),
            "media_type": str(record.get("preview_media_type") or ""),
        }
    return index


def _file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _repo_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _visual_evidence(
    candidate: dict[str, Any],
    *,
    previews: dict[str, dict[str, Any]],
    frames: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Pixels that already exist on disk for this candidate, or nothing.

    Sampled frames win when the run produced them - that is the v1 channel and the
    measurement already counts it. Otherwise two sources cost no network: the
    preview the run cached, and the file of a local-library candidate, which is the
    asset itself. A candidate the run never previewed stays without pixels; that is
    a limit of the saved data and is reported rather than filled in.
    """

    if frames:
        return []
    url = str(candidate.get("preview_url") or "")
    cached = previews.get(url)
    if cached:
        return [
            {
                "kind": EVIDENCE_KIND_PREVIEW,
                "local_path": _repo_relative(cached["local_path"]),
                "sha256": cached["sha256"] or _file_digest(cached["local_path"]),
                "width": cached["width"],
                "height": cached["height"],
                "media_type": cached["media_type"] or "image",
            }
        ]
    for key in ("path", "local_path", "downloaded_path"):
        raw = str(candidate.get(key) or "")
        if not raw:
            continue
        local = Path(raw)
        if not local.is_file():
            continue
        return [
            {
                "kind": EVIDENCE_KIND_LOCAL_FILE,
                "local_path": _repo_relative(local),
                "sha256": str(candidate.get("checksum_sha256") or "") or _file_digest(local),
                "width": int(candidate.get("width") or 0),
                "height": int(candidate.get("height") or 0),
                "media_type": str(candidate.get("media_type") or candidate.get("type") or ""),
                "duration_sec": float(candidate.get("duration_sec") or candidate.get("duration") or 0.0),
            }
        ]
    return []


def _captured_provider(candidate: dict[str, Any]) -> str:
    """The provider that really supplied this candidate.

    Read from the stored decision first. The asset id prefix is not the provider
    and never was: ``pexels_32386564`` in LIVE-5 scene_003 carries
    ``provider: local_library``, and an external review built a whole
    recommendation on reading the prefix instead.
    """

    decision = candidate.get("selection_decision")
    if isinstance(decision, dict) and str(decision.get("provider") or "").strip():
        return str(decision["provider"]).strip()
    return str(candidate.get("provider") or "").strip()


def _captured_decision(candidate: dict[str, Any], *, taken: bool) -> dict[str, Any]:
    """What the run recorded about this candidate. Evidence, never an input.

    ``run_metadata_baseline`` builds its pool from ``entry["candidate"]`` alone, so
    a sibling key cannot reach the decision owner; the blind pack renders the
    requirement and the pictures, so it cannot reach the annotator either. It is
    here because the case this corpus exists for is stated in these numbers.
    """

    return {
        "provider": _captured_provider(candidate),
        "media_type": str(candidate.get("media_type") or candidate.get("type") or ""),
        "shortlisted": taken,
        "final_score": candidate.get("final_score"),
        "semantic_score": candidate.get("semantic_score"),
        "semantic_match_status": str(candidate.get("semantic_match_status") or ""),
        "subject_match": candidate.get("subject_match"),
        "quality_score": candidate.get("quality_score"),
        "vertical_score": candidate.get("vertical_score"),
        "rejected": bool(candidate.get("rejected")),
        "blocking_reject_reasons": [
            str(item) for item in (candidate.get("blocking_reject_reasons") or [])
        ],
    }


def _run_scene_pool(scene: dict[str, Any]) -> list[tuple[dict[str, Any], bool]]:
    """The ten saved candidates of one scene, deduplicated by asset id.

    A saved scene lists the same asset more than once - inside ``candidates`` and
    across the two lists - so the ten records of a scene are not ten assets. The
    first occurrence wins and its list is remembered, because "the run kept this
    one" is part of the evidence.
    """

    pool: list[tuple[dict[str, Any], bool]] = []
    seen: set[str] = set()
    for candidates, taken in ((scene.get("candidates") or [], True), (scene.get("rejected_candidates") or [], False)):
        for candidate in candidates:
            asset_id = str(candidate.get("asset_id") or "")
            if not asset_id or asset_id in seen:
                continue
            seen.add(asset_id)
            pool.append((candidate, taken))
    return pool


def _attempt_statistics(scene: dict[str, Any]) -> dict[str, int]:
    attempts = [item for item in (scene.get("provider_attempts") or []) if isinstance(item, dict)]
    return {
        "provider_attempts": len(attempts),
        "provider_results": sum(int(item.get("result_count") or 0) for item in attempts),
        "saved_candidate_records": len(scene.get("candidates") or [])
        + len(scene.get("rejected_candidates") or []),
    }


def _v2_scene(
    run: dict[str, Any],
    scene: dict[str, Any],
    *,
    scene_text: str,
    previews: dict[str, dict[str, Any]],
    frames_by_asset: dict[str, list[dict[str, Any]]],
    prefer_video: bool,
    scene_key: str | None = None,
    semantic_scene: dict[str, Any] | None = None,
    corpus_class: str = CORPUS_CLASS_BLIND,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """One corpus scene out of one saved scene of one run."""

    key = scene_key or f"{run['run_id']}/{scene['scene_id']}"
    pool = _run_scene_pool(scene)
    # Same proof v1 makes: the archival copies of the provider record are dropped
    # only after this scene has been ranked with and without them and answered
    # identically. Otherwise the frozen corpus would be a different pool than the
    # one the run decided on, and every number taken from it would be about a
    # corpus rather than about a run.
    _assert_archival_keys_are_inert(
        {
            "scene_key": key,
            "semantic_scene": semantic_scene or scene.get("semantic_scene") or {},
            "raw_candidates": [candidate for candidate, _ in pool],
            "prefer_video": prefer_video,
            "required_duration_sec": float(scene.get("required_duration_sec") or 0.0),
            "require_provider_metadata": bool(
                (scene.get("provider_routing") or {}).get("requires_provider_metadata")
            ),
            "source_class": str(scene.get("source_class") or ""),
        }
    )
    blind = assign_blind_ids(key, [str(candidate.get("asset_id")) for candidate, _ in pool])
    entries: list[dict[str, Any]] = []
    for index, (candidate, taken) in enumerate(pool):
        asset_id = str(candidate.get("asset_id"))
        frames = frames_by_asset.get(asset_id) or []
        entries.append(
            {
                "blind_id": blind[asset_id],
                "asset_id": asset_id,
                "input_order": index,
                "frames": frames,
                "visual_evidence": _visual_evidence(candidate, previews=previews, frames=frames),
                "captured_decision": _captured_decision(candidate, taken=taken),
                "candidate": _strip_ranker_output(candidate, drop_archival=True),
            }
        )
    entries.sort(key=lambda entry: int(entry["blind_id"][1:]))
    selected_asset_id = str((scene.get("selected_asset") or {}).get("asset_id") or "")
    stored_semantic = dict(semantic_scene or scene.get("semantic_scene") or {})
    stored_semantic.setdefault("scene_id", str(scene.get("scene_id") or ""))
    record: dict[str, Any] = {
        "scene_key": key,
        "corpus_class": corpus_class,
        "run_id": str(run["run_id"]),
        "project": str(run["project"]),
        "scene_id": str(scene.get("scene_id") or ""),
        "scene_text": scene_text,
        "semantic_scene": stored_semantic,
        "visual_brief": scene.get("visual_brief") or {},
        "primary_query": str(scene.get("primary_query") or ""),
        "query_plan": scene.get("query_plan") or {},
        "required_duration_sec": float(scene.get("required_duration_sec") or 0.0),
        "source_class": str(scene.get("source_class") or ""),
        "require_provider_metadata": bool(
            (scene.get("provider_routing") or {}).get("requires_provider_metadata")
        ),
        "prefer_video": prefer_video,
        "target_aspect_ratio": "9:16",
        "categories": [],
        "captured_attempt_statistics": _attempt_statistics(scene),
        "selected_blind_id": blind.get(selected_asset_id, ""),
        "candidates": entries,
    }
    record.update(extra or {})
    return record


def build_corpus_v2() -> dict[str, Any]:
    """Freeze the bilingual corpus. Offline, and it writes nothing to ``projects/``."""

    scenes: list[dict[str, Any]] = []
    by_run_scene: dict[tuple[str, str], tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, list[dict[str, Any]]], bool, str]] = {}
    for run in CURRENT_RUNS:
        root = _run_project_root(run)
        manifest = json.loads((root / "assets" / "assets_manifest.json").read_text(encoding="utf-8"))
        review_path = root / "assets" / "review" / "visual_review_manifest.json"
        review = json.loads(review_path.read_text(encoding="utf-8")) if review_path.is_file() else {}
        previews = _preview_cache_index(root)
        prefer_video = str(manifest.get("visual_mode") or "") == "video_first"
        text_by_scene = {
            str(item.get("scene_id")): str(item.get("scene_text") or "")
            for item in review.get("scenes") or []
        }
        frames_by_scene = {
            str(item.get("scene_id")): _available_frames(item.get("sampled_frames") or {})
            for item in review.get("scenes") or []
        }
        for scene in manifest.get("scenes") or []:
            scene_id = str(scene.get("scene_id") or "")
            scene_text = text_by_scene.get(scene_id, "")
            if not scene_text:
                # The review manifest is written per prepared scene, so a scene it
                # never covered has no narration there. The requirement is what the
                # annotator judges against, so it is taken from the brief rather
                # than left blank.
                brief = scene.get("visual_brief") if isinstance(scene.get("visual_brief"), dict) else {}
                scene_text = " ".join(
                    part
                    for part in (
                        str(brief.get("subject") or ""),
                        str(brief.get("action") or ""),
                        str(brief.get("place") or ""),
                    )
                    if part
                ).strip() or scene_id
            frames = frames_by_scene.get(scene_id, {})
            record = _v2_scene(
                run,
                scene,
                scene_text=scene_text,
                previews=previews,
                frames_by_asset=frames,
                prefer_video=prefer_video,
            )
            scenes.append(record)
            by_run_scene[(str(run["run_id"]), scene_id)] = (
                run,
                scene,
                previews,
                frames,
                prefer_video,
                scene_text,
            )

    for spec in INCIDENT_SCENES:
        found = by_run_scene.get((str(spec["run_id"]), str(spec["scene_id"])))
        if found is None:
            raise RuntimeError(f"{spec['case_id']}: {spec['run_id']}/{spec['scene_id']} is not in the runs")
        run, scene, previews, frames, prefer_video, _text = found
        base = dict(scene.get("semantic_scene") or {})
        base.update(spec["semantic_scene"])
        scenes.append(
            _v2_scene(
                run,
                scene,
                scene_text=str(spec["scene_text"]),
                previews=previews,
                frames_by_asset=frames,
                prefer_video=prefer_video,
                scene_key=f"{spec['run_id']}/{spec['scene_id']}#{spec['case_id']}",
                semantic_scene=base,
                corpus_class=CORPUS_CLASS_INCIDENT,
                extra={
                    "case_id": str(spec["case_id"]),
                    "incident_note": str(spec["incident_note"]),
                    "derived_from_scene_key": f"{spec['run_id']}/{spec['scene_id']}",
                    "categories": sorted(set(spec.get("categories") or [])),
                },
            )
        )

    for record in scenes:
        if record["corpus_class"] == CORPUS_CLASS_INCIDENT:
            continue
        categories, _selected, _support = categorize(
            {
                "semantic_scene": record["semantic_scene"],
                "raw_candidates": [entry["candidate"] for entry in record["candidates"]],
                "prefer_video": record["prefer_video"],
                "required_duration_sec": record["required_duration_sec"],
                "require_provider_metadata": record["require_provider_metadata"],
                "source_class": record["source_class"],
            }
        )
        record["categories"] = sorted(categories)

    corpus: dict[str, Any] = {
        "schema_version": CORPUS_SCHEMA_VERSION,
        "corpus_version": CORPUS_V2_VERSION,
        "fixture_kind": FIXTURE_KIND_CURRENT_BENCHMARK,
        "generation_class": GENERATION_CURRENT,
        "generation_class_reason": (
            "both runs are later than the query work of PLAN-9B-1..9B-3 and PLAN-9C, "
            "so their pools were retrieved by the current stack; the per-run HEAD is "
            "declared in source_runs because the two runs differ"
        ),
        "corpus_class": CORPUS_CLASS_BLIND,
        "annotations_filename": CURRENT_ANNOTATIONS_V2_PATH.name,
        "built_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "plan_step": "PLAN-9D-H",
        "source": (
            "saved candidate records of two local runs; no network, no provider search, "
            "no download, no re-run"
        ),
        "source_runs": [dict(run) for run in CURRENT_RUNS],
        "evaluation_constants": {
            "used_asset_ids": "empty - every scene is judged on its own",
            "vision_tags": "empty - this corpus is the metadata-only arm",
            "framing": "production dimensions come from the candidate record, never from a preview",
            "input_order": (
                "position in the saved manifest (candidates, then rejected_candidates, "
                "deduplicated by asset id); ranking is a stable sort, so this order is "
                "the tie-break, exactly as in v1"
            ),
        },
        "known_limits": [
            "This is the tail a run saved, not the pool it searched: 10 records per "
            "scene against 234 provider attempts and 1303 results in LIVE-5 alone. "
            "A question of the form 'the right candidate was at rank forty' cannot be "
            "asked of this corpus, and no offline material can answer it - the only "
            "way to widen the pool is another paid run.",
            "Pixels exist only where the run left them: a sampled frame, a cached "
            "preview, or the file of a local-library candidate. Candidates the run "
            "never previewed carry no picture and are on the board as cards a person "
            "cannot judge; they stay in the measured pool because the ranker saw them.",
            "A video candidate is shown as stills. A label on such a card is a "
            "judgement about frames, not about motion.",
            "Neither run declared a single prohibition, so every ban case here is an "
            "incident scene with a hand-written requirement.",
        ],
        "scene_count": len(scenes),
        "observation_count": sum(len(record["candidates"]) for record in scenes),
        "card_statistics": _v2_card_statistics(scenes),
        "language_statistics": _v2_language_statistics(scenes),
        "scenes": scenes,
        "corpus_sha256": "",
    }
    corpus["corpus_sha256"] = corpus_digest(corpus)
    return corpus


def _v2_card_statistics(scenes: list[dict[str, Any]]) -> dict[str, int]:
    """How many cards there are, and how many a person can actually judge.

    Counted here rather than in prose because the two numbers are quoted together
    and once drifted apart in v1's own docstring: cards and frames are different
    units, and so are "in the corpus" and "on the page".
    """

    cards = [(scene, entry) for scene in scenes for entry in scene["candidates"]]
    return {
        "cards": len(cards),
        "blind_annotation_cards": sum(
            len(scene["candidates"]) for scene in scenes if scene["corpus_class"] == CORPUS_CLASS_BLIND
        ),
        "incident_cards": sum(
            len(scene["candidates"]) for scene in scenes if scene["corpus_class"] == CORPUS_CLASS_INCIDENT
        ),
        "distinct_asset_ids": len({entry["asset_id"] for _scene, entry in cards}),
        "cards_with_pictures": sum(1 for _scene, entry in cards if candidate_is_visible(entry)),
        "cards_without_pictures": sum(1 for _scene, entry in cards if not candidate_is_visible(entry)),
        "cards_from_sampled_frames": sum(1 for _scene, entry in cards if entry["frames"]),
        "cards_from_cached_preview": sum(
            1
            for _scene, entry in cards
            if any(ev["kind"] == EVIDENCE_KIND_PREVIEW for ev in entry["visual_evidence"])
        ),
        "cards_from_local_file": sum(
            1
            for _scene, entry in cards
            if any(ev["kind"] == EVIDENCE_KIND_LOCAL_FILE for ev in entry["visual_evidence"])
        ),
    }


def _v2_language_statistics(scenes: list[dict[str, Any]]) -> dict[str, Any]:
    """What v1 could not answer: is there any Cyrillic in the way of a decision?

    v1 had 14 English subjects out of 14, an empty media index and 2 candidate
    records with Cyrillic out of 1064, which is why a language fix measured on it
    could not move. These counters are the same question asked of v2.
    """

    cyrillic_records = 0
    russian_subject_scenes: list[str] = []
    providers: Counter = Counter()
    for scene in scenes:
        subject = " ".join(str(item) for item in (scene["semantic_scene"].get("subject") or []))
        if _CYRILLIC_RE.search(subject):
            russian_subject_scenes.append(str(scene["scene_key"]))
        for entry in scene["candidates"]:
            candidate = entry["candidate"]
            text = " ".join(
                [
                    str(candidate.get("title") or ""),
                    str(candidate.get("description") or ""),
                    " ".join(str(item) for item in (candidate.get("keywords") or [])),
                    " ".join(str(item) for item in (candidate.get("tags") or [])),
                ]
            )
            if _CYRILLIC_RE.search(text):
                cyrillic_records += 1
            providers[entry["captured_decision"]["provider"]] += 1
    return {
        "candidate_records_with_cyrillic_metadata": cyrillic_records,
        "scenes_with_a_russian_subject": russian_subject_scenes,
        "scenes_with_a_russian_prohibition": [
            str(scene["scene_key"])
            for scene in scenes
            if any(
                _CYRILLIC_RE.search(str(item))
                for item in (scene["semantic_scene"].get("must_not_include") or [])
            )
        ],
        "cards_by_provider": dict(sorted(providers.items())),
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
    annotation_identity_sha256:PACK.annotation_identity_sha256,
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
  a.href=URL.createObjectURL(blob);a.download='__ANNOTATIONS_FILENAME__';a.click();
}
"""

#: The pack is the only producer of the owner's ground truth and
#: ``CURRENT_ANNOTATIONS_PATH`` is its only consumer, so the download name is
#: taken from the harness instead of being spelled twice. The two spellings did
#: drift, and the cost was the whole point of the step: a finished blind pass
#: saved as ``annotations_v1.json`` sat unread beside a harness looking for
#: ``current_annotations_v1.json``, which went on answering
#: ``WAITING_FOR_OWNER_ANNOTATION`` as if the owner had never done the work.
ANNOTATIONS_FILENAME = CURRENT_ANNOTATIONS_PATH.name


#: How many stills a local video contributes to a card. The run itself sampled five
#: for the two clips it previewed; three is enough to see what a clip is of, and the
#: card stays readable.
LOCAL_VIDEO_STILL_POSITIONS = (0.1, 0.5, 0.9)


def materialize_blind_media(corpus: dict[str, Any], media_dir: Path) -> dict[tuple[str, str], list[str]]:
    """Copy the pictures the pack shows into blind-named files beside the page.

    Necessary rather than tidy. A cached preview lives under a content-addressed
    directory and leaks nothing, but a local-library candidate is a file called
    ``pexels_video_solar_panel_assembly_line_factory_conveyor_...mp4``: pointing the
    page at it would put the answer in the ``src`` attribute of the card the owner
    is being asked to judge. Names here are derived from the blind id only.

    Offline: it copies files already on disk and, for a local clip, asks ``ffmpeg``
    for stills. No network, no provider, no project directory is written to.
    """

    media_dir.mkdir(parents=True, exist_ok=True)
    by_card: dict[tuple[str, str], list[str]] = {}
    for scene in corpus["scenes"]:
        # The opaque token, not the scene key. A file called
        # ``local_after_fix_scene_004_ban_declension_cooling_tower_C1_0.jpg`` sits in
        # an <img src> on the page and says, before the owner has looked at
        # anything, that this scene was made by hand and what it bans.
        scene_slug = scene_token(str(scene["scene_key"]))
        for entry in scene["candidates"]:
            blind_id = str(entry["blind_id"])
            names: list[str] = []
            for index, frame in enumerate(entry.get("frames") or []):
                source = REPO_ROOT / str(frame["local_frame_path"])
                if not source.is_file():
                    continue
                target = media_dir / f"{scene_slug}_{blind_id}_f{index}{source.suffix.lower()}"
                if not target.exists():
                    shutil.copyfile(source, target)
                names.append(target.name)
            for index, evidence in enumerate(entry.get("visual_evidence") or []):
                source = REPO_ROOT / str(evidence["local_path"])
                if not source.is_file():
                    continue
                if str(evidence.get("media_type") or "") == "video":
                    names.extend(_local_video_stills(source, evidence, media_dir, f"{scene_slug}_{blind_id}_v{index}"))
                    continue
                target = media_dir / f"{scene_slug}_{blind_id}_p{index}{source.suffix.lower()}"
                if not target.exists():
                    shutil.copyfile(source, target)
                names.append(target.name)
            if names:
                by_card[(str(scene["scene_key"]), blind_id)] = names
    return by_card


def media_urls_relative_to(
    media: dict[tuple[str, str], list[str]], *, media_dir: Path, page: Path
) -> dict[tuple[str, str], list[str]]:
    """Turn bare file names into references a browser opening ``page`` can follow.

    ``materialize_blind_media`` names files, not paths, and the page is normally
    written *beside* the directory rather than inside it - so the raw names
    resolved to nothing and every card came up blank in a real browser. The first
    check of this missed it by joining the media directory itself before asking
    whether the file existed, which tested the directory rather than the page.
    """

    prefix = Path(os.path.relpath(media_dir, page.parent)).as_posix()
    if prefix in {"", "."}:
        return {key: list(names) for key, names in media.items()}
    return {
        key: [f"{prefix}/{name}" for name in names] for key, names in media.items()
    }


def _local_video_stills(
    source: Path, evidence: dict[str, Any], media_dir: Path, stem: str
) -> list[str]:
    """Stills from a local clip, sampled at fixed positions. Skipped if already there."""

    duration = float(evidence.get("duration_sec") or 0.0)
    names: list[str] = []
    for index, position in enumerate(LOCAL_VIDEO_STILL_POSITIONS):
        target = media_dir / f"{stem}_{index}.jpg"
        if not target.exists():
            offset = duration * position if duration > 0 else float(index + 1)
            command = [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-ss",
                f"{offset:.3f}",
                "-i",
                str(source),
                "-frames:v",
                "1",
                "-vf",
                "scale=480:-2",
                "-y",
                str(target),
            ]
            result = subprocess.run(command, capture_output=True, text=True)
            if result.returncode != 0 or not target.exists():
                continue
        names.append(target.name)
    return names


def render_pack(corpus: dict[str, Any], *, media: dict[tuple[str, str], list[str]] | None = None) -> str:
    """A disposable, offline, evaluation-only page. Not a product frontend.

    What it shows is the whole point: the scene's stated requirement and the
    pictures, under blind identifiers. Provider, title, description, licence,
    every score, the ranker's answer and the corpus categories all stay behind.

    Same gate as the template it feeds: a pack is only ever rendered for the
    frozen current capture.

    Scenes appear under an opaque token rather than under ``scene_key``: the key
    names the run and, for an incident scene, the case, and a blind pass may not
    carry that hint in a DOM attribute or a picture's file name. The saved labels
    come back carrying the token and the harness maps it back.

    What the resulting ground truth may be used to claim
    ----------------------------------------------------
    Only candidates with a picture are shown, and a run only ever previewed a
    shortlist. So a label produced here reads *the best visually checkable
    candidate inside what the run saved* - never "the best asset in the pool".
    Two consequences are load-bearing and must not be argued away by a later
    reader: the benchmark cannot show that retrieval missed a better candidate
    before the shortlist, and it cannot speak for a media type the run barely
    previewed.

    Cards and frames are different units, and an earlier version of this
    paragraph mixed them - it read "54 images and 2 videos" against a corpus
    holding 43 image cards and 13 video cards. So the counts are not repeated
    here at all: every corpus carries its own ``card_statistics``, and v1 and v2
    have different ones (56 of 1064 in v1, 55 of 78 in v2). The limit the
    sentence was reaching for is the durable part and survives: a video card
    shows stills, so a label on it is a judgement of frames, not of motion, and
    these labels do not measure video selection, video-first or composite
    assembly.
    """

    assert_current_benchmark_input(corpus, context="annotation pack")
    # The corpus names the file its labels belong in. Spelling it here as well is
    # how the two drifted once and cost a whole blind pass, so v2 carries the name
    # and an older corpus keeps the only name it ever had.
    annotations_filename = str(corpus.get("annotations_filename") or "") or ANNOTATIONS_FILENAME
    step = str(corpus.get("plan_step") or "PLAN-9D-A")
    parts: list[str] = [
        "<!doctype html><meta charset='utf-8'>",
        f"<title>{html.escape(step)} blind annotation pack</title>",
        f"<style>{_PACK_STYLE}</style>",
        f"<div class='bar'><h1>{html.escape(step)} — слепая разметка</h1>",
        "<p>Выберите лучший кандидат по <b>смыслу сцены</b>. Права, лицензии, "
        "технические размеры и качество метаданных оценивать не нужно — это решает система. "
        "<span class='warn'>Кандидаты обезличены; порядок не отражает оценку системы.</span></p>",
        "<p>Annotator: <input id='annotator' placeholder='имя или псевдоним'> "
        f"<button onclick='save()'>Сохранить {annotations_filename}</button></p></div>",
    ]
    for scene in corpus["scenes"]:
        semantic = scene.get("semantic_scene") or {}
        token = scene_token(str(scene["scene_key"]))
        parts.append(
            f"<div class='scene' data-key=\"{html.escape(token)}\">"
            f"<h2>{html.escape(scene['scene_text'] or token)}</h2><dl class='req'>"
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
        # Only a candidate with a picture is a question a human can answer. A run
        # previews a shortlist, so much of the pool carries no picture at all - 64
        # frames against 1064 candidates in v1. Those stay in the corpus, which is
        # what gets measured, and off the page, which is what the owner is asked to
        # judge: choosing BEST between blind identifiers with nothing to look at
        # would produce a label about nothing. v2 widens *what counts as a picture*
        # - a cached preview and a local-library file are pixels already on disk -
        # and the corpus records which, so page and measurement agree.
        visible = [entry for entry in scene["candidates"] if candidate_is_visible(entry)]
        withheld = len(scene["candidates"]) - len(visible)
        for candidate in visible:
            blind_id = html.escape(str(candidate["blind_id"]))
            parts.append(f"<div class='cand' data-blind='{blind_id}'><h3>{blind_id}</h3>")
            for url in _card_picture_urls(scene, candidate, media):
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
            for c in visible
        )
        parts.append(
            "</div><div class='best'><b>BEST:</b> <select data-best><option value=''>—</option>"
            f"{best_options}<option value='none_acceptable'>none_acceptable</option>"
            "<option value='undecidable'>undecidable</option></select></div>"
        )
        if withheld:
            # Said out loud on the page. A silent omission would read as "the pool
            # was this small", and the owner's BEST would be quoted against a pool
            # that had more in it.
            parts.append(
                f"<p class='warn'>Ещё {withheld} кандидат(ов) этой сцены прогон не "
                "предпросматривал — картинки нет, поэтому их здесь нет. Они остаются "
                "в измеряемом пуле.</p>"
            )
        parts.append(
            "<textarea class='note' rows='2' placeholder='комментарий (необязательно)'></textarea></div>"
        )
    pack_meta = {
        "schema_version": ANNOTATIONS_SCHEMA_VERSION,
        "corpus_version": corpus["corpus_version"],
        "corpus_sha256": corpus["corpus_sha256"],
        # What the saved labels are bound to. The page carries it because the page
        # is the only producer of the owner's ground truth, and a pass saved
        # without it is refused by the harness rather than silently unbound.
        "annotation_identity_sha256": annotation_identity_digest(corpus),
    }
    script = _PACK_SCRIPT.replace("__ANNOTATIONS_FILENAME__", annotations_filename)
    parts.append(f"<script>const PACK={canonical_json(pack_meta)};{script}</script>")
    return "".join(parts)


def _card_picture_urls(
    scene: dict[str, Any],
    entry: dict[str, Any],
    media: dict[tuple[str, str], list[str]] | None,
) -> list[str]:
    """Where this card's pictures come from on the rendered page.

    With a media directory the page is self-contained and every name is derived
    from the blind id, which is the only form safe for a local-library file whose
    own name describes the shot. Without one the behaviour is what it always was:
    a ``file://`` link into the content-addressed preview cache.
    """

    if media is not None:
        return media.get((str(scene["scene_key"]), str(entry["blind_id"])), [])
    if any(
        str(evidence.get("media_type") or "") == "video"
        for evidence in entry.get("visual_evidence") or []
    ):
        # A clip cannot be an <img>, and a page that silently drops its picture
        # would ask the owner to judge a card with nothing on it. Stills come from
        # ``materialize_blind_media``, which is also the only form safe for a local
        # file whose name describes the shot.
        raise BenchmarkError(
            f"{scene['scene_key']}/{entry['blind_id']}: this candidate is a local clip; "
            "render the pack with a media directory so its stills exist"
        )
    urls: list[str] = []
    for frame in entry.get("frames") or []:
        urls.append((REPO_ROOT / frame["local_frame_path"]).resolve().as_uri())
    for evidence in entry.get("visual_evidence") or []:
        if str(evidence.get("media_type") or "") == "video":
            continue
        urls.append((REPO_ROOT / str(evidence["local_path"])).resolve().as_uri())
    return urls


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
            f"<div class='scene' data-key=\"{html.escape(scene_token(str(scene['scene_key'])))}\">"
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
    build_v2 = sub.add_parser(
        "build-v2", help="freeze the bilingual corpus v2 from the two saved runs (PLAN-9D-H)"
    )
    build_v2.add_argument("--out", default=str(CURRENT_CORPUS_V2_PATH), help="destination corpus")
    pack = sub.add_parser("pack", help="render the blind annotation pack from a frozen current corpus")
    pack.add_argument("--corpus", required=True, help="frozen current corpus (PLAN-9D-B)")
    pack.add_argument("--out", required=True, help="destination .html path (keep it outside the repo)")
    pack.add_argument(
        "--media-dir",
        default="",
        help=(
            "copy every picture the page shows into this directory under blind names "
            "and reference them relatively; required for a corpus carrying "
            "local-library candidates, whose own file names describe the shot"
        ),
    )
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

    if args.command == "build-v2":
        corpus = build_corpus_v2()
        validate_corpus(corpus)
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(corpus, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        classes = Counter(corpus_class_of(corpus, scene) for scene in corpus["scenes"])
        stats = corpus["card_statistics"]
        print(f"corpus v2 written to {out}")
        print(
            f"scenes={corpus['scene_count']} cards={stats['cards']} "
            f"(blind {stats['blind_annotation_cards']} + incident {stats['incident_cards']}) "
            f"with_pictures={stats['cards_with_pictures']} "
            f"without={stats['cards_without_pictures']}"
        )
        print(
            "cyrillic_candidate_records="
            f"{corpus['language_statistics']['candidate_records_with_cyrillic_metadata']}"
        )
        print("classes=" + ", ".join(f"{name}:{count}" for name, count in sorted(classes.items())))
        print(f"sha256={corpus['corpus_sha256']}")
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
    media = None
    if args.media_dir:
        media_dir = Path(args.media_dir)
        media = media_urls_relative_to(
            materialize_blind_media(corpus, media_dir), media_dir=media_dir, page=out
        )
    out.write_text(render_pack(corpus, media=media), encoding="utf-8")
    cards = sum(
        1
        for scene in corpus["scenes"]
        for entry in scene["candidates"]
        if candidate_is_visible(entry)
    )
    print(f"annotation pack written to {out}")
    print(f"scenes={len(corpus['scenes'])} cards_with_pictures={cards}")
    if media is not None:
        print(f"blind media in {Path(args.media_dir)}: {sum(len(v) for v in media.values())} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
