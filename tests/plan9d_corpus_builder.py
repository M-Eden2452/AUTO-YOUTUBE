"""Build the PLAN-9D-A corpus and render its blind annotation pack.

Run by hand, twice in the life of the benchmark: once to freeze the corpus, and
whenever the owner needs the annotation pack regenerated from that frozen
corpus. It is not a test and nothing imports it at test time.

    .\\venv\\Scripts\\python.exe -B -m tests.plan9d_corpus_builder build
    .\\venv\\Scripts\\python.exe -B -m tests.plan9d_corpus_builder pack --out <path-outside-the-repo>\\pack.html

Offline by construction: it reads ``projects/*/assets/assets_manifest.json`` and
``projects/*/assets/review/visual_review_manifest.json``, both already on disk,
and opens no socket. No provider search, no download, no Vision, no paid call.

Two things it deliberately does not do.

*It does not decide which candidate is right.* Scenes are chosen by technical
category coverage - what a scene declares, what the licence says, whether the
provider declared dimensions, whether the existing decision owner already has a
strong answer that a change could break. The semantic question is left entirely
to the owner's blind pass.

*It does not copy pictures into the repository.* The cached previews are
third-party licensed provider material and ``projects/`` is deliberately
untracked. The corpus carries each frame's path, size and SHA256, so the frozen
data can be verified, and the tests never need the image bytes.
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
from typing import Any, Iterable

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
    ANNOTATIONS_PATH,
    ANNOTATIONS_SCHEMA_VERSION,
    CANDIDATE_FLAG_SPEC,
    CORPUS_PATH,
    CORPUS_SCHEMA_VERSION,
    STATUS_WAITING,
    assign_blind_ids,
    canonical_json,
    corpus_digest,
    load_corpus,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
PROJECTS_ROOT = REPO_ROOT / "projects"

CORPUS_VERSION = "plan9d-a-2026-08-08"

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
    """

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


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PLAN-9D-A offline benchmark tooling")
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build", help="freeze the corpus and the empty annotation template")
    build.add_argument("--force", action="store_true", help="overwrite an existing frozen corpus")
    pack = sub.add_parser("pack", help="render the blind annotation pack from the frozen corpus")
    pack.add_argument("--out", required=True, help="destination .html path (keep it outside the repo)")
    args = parser.parse_args(argv)

    if args.command == "build":
        if CORPUS_PATH.exists() and not args.force:
            print(f"refusing to overwrite frozen corpus {CORPUS_PATH} (use --force)")
            return 1
        corpus = build_corpus()
        CORPUS_PATH.parent.mkdir(parents=True, exist_ok=True)
        CORPUS_PATH.write_text(
            json.dumps(corpus, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
        )
        ANNOTATIONS_PATH.write_text(
            json.dumps(annotation_template(corpus), ensure_ascii=False, indent=1) + "\n",
            encoding="utf-8",
        )
        covered = sorted({c for scene in corpus["scenes"] for c in scene["categories"]})
        print(f"scenes={corpus['scene_count']} observations={corpus['observation_count']}")
        print(f"sha256={corpus['corpus_sha256']}")
        print("categories=" + ", ".join(covered))
        return 0

    corpus = load_corpus()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_pack(corpus), encoding="utf-8")
    print(f"annotation pack written to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
