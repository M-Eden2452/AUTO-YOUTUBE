from __future__ import annotations

import dataclasses
import html
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.assets.semantic_selection.decision import DECISION_KEY, has_decision, read_decision


REVIEW_BUNDLE_REQUIRED_FIELDS = [
    "project_id",
    "scene_id",
    "scene_text",
    "semantic_scene",
    "target_duration_sec",
    "target_aspect_ratio",
    "metadata_queries",
    "provider_routing",
    "shortlist",
    "selected_candidate",
    "alternatives",
    "manual_fallback_status",
]


@dataclass
class SceneReviewBundle:
    project_id: str
    scene_id: str
    scene_text: str = ""
    semantic_scene: dict[str, Any] = field(default_factory=dict)
    target_duration_sec: float = 0.0
    target_aspect_ratio: str = "9:16"
    metadata_queries: list[dict[str, Any]] = field(default_factory=list)
    provider_routing: dict[str, Any] = field(default_factory=dict)
    shortlist: list[dict[str, Any]] = field(default_factory=list)
    preview_status: dict[str, Any] = field(default_factory=dict)
    sampled_frames: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    technical_scores: dict[str, Any] = field(default_factory=dict)
    duplicate_scores: dict[str, Any] = field(default_factory=dict)
    crop_scores: dict[str, Any] = field(default_factory=dict)
    selected_candidate: dict[str, Any] = field(default_factory=dict)
    alternatives: list[dict[str, Any]] = field(default_factory=list)
    manual_fallback_status: dict[str, Any] = field(default_factory=dict)
    reranking: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


def create_scene_review_bundle(
    *,
    project_id: str,
    scene: dict[str, Any],
    semantic_scene: dict[str, Any],
    metadata_queries: list[dict[str, Any]],
    provider_routing: dict[str, Any],
    candidates: list[dict[str, Any]],
    analyses: list[dict[str, Any]],
    selected_candidate_id: str,
    target_aspect_ratio: str,
    manual_request: dict[str, Any] | None = None,
    technical_rerank_enabled: bool = False,
) -> SceneReviewBundle:
    analysis_by_id = {str(item.get("asset_id") or ""): item for item in analyses}
    shortlist: list[dict[str, Any]] = []
    for rank, candidate in enumerate(candidates, start=1):
        asset_id = str(candidate.get("asset_id") or "")
        analysis = analysis_by_id.get(asset_id, {})
        technical = analysis.get("technical_metrics") if isinstance(analysis.get("technical_metrics"), dict) else {}
        crop_scores = analysis.get("crop_scores") if isinstance(analysis.get("crop_scores"), dict) else {}
        duplicate_scores = analysis.get("duplicate_scores") if isinstance(analysis.get("duplicate_scores"), list) else []
        entry = {
            "asset_id": asset_id,
            "provider": candidate.get("provider", ""),
            "provider_asset_id": candidate.get("provider_asset_id", ""),
            "source_page_url": candidate.get("source_page_url") or candidate.get("source_page") or candidate.get("source_url", ""),
            "author_name": candidate.get("author_name") or candidate.get("author", ""),
            "license": _safe_license(candidate.get("license")),
            "vision_tags": list(candidate.get("vision_tags") or []),
            "vision_tags_asset_id": str(candidate.get("vision_tags_asset_id") or ""),
            "vision_tags_source_sha256": str(
                candidate.get("vision_tags_source_sha256") or ""
            ),
            "vision_tags_cache_key": str(candidate.get("vision_tags_cache_key") or ""),
            "policy_status": _policy_status(candidate),
            "metadata_rank": rank,
            "metadata_score": float(candidate.get("final_score") or candidate.get("total_score") or candidate.get("relevance_score") or 0.0),
            "technical_score": float(analysis.get("technical_quality_score") or technical.get("technical_quality_score") or 0.0),
            "duplicate_scores": duplicate_scores,
            "crop_scores": crop_scores,
            "preview_status": analysis.get("analysis_status", "not_analysed"),
            "sampled_frames": analysis.get("sampled_frames", []),
            "rejection_reasons": _rejection_reasons(candidate, analysis),
            "review_required_reasons": _review_required_reasons(candidate, analysis),
            "score_breakdown": technical.get("score_breakdown", {}),
            "combined_score": _combined_score(candidate, analysis, target_aspect_ratio),
        }
        entry.update(_semantic_fields(analysis))
        entry.update(_decision_fields(candidate))
        shortlist.append(entry)
    selected = next((candidate for candidate in shortlist if candidate["asset_id"] == selected_candidate_id), shortlist[0] if shortlist else {})
    alternatives = [candidate for candidate in shortlist if candidate.get("asset_id") != selected.get("asset_id")][:4]
    return SceneReviewBundle(
        project_id=project_id,
        scene_id=str(scene.get("scene_id") or ""),
        scene_text=str(scene.get("narration") or scene.get("primary_query") or scene.get("visual_description") or ""),
        semantic_scene=semantic_scene,
        target_duration_sec=float(scene.get("target_duration_sec") or scene.get("duration") or 0.0),
        target_aspect_ratio=target_aspect_ratio,
        metadata_queries=metadata_queries,
        provider_routing=provider_routing,
        shortlist=shortlist,
        preview_status={item["asset_id"]: item["preview_status"] for item in shortlist},
        sampled_frames={item["asset_id"]: item["sampled_frames"] for item in shortlist},
        technical_scores={item["asset_id"]: item["technical_score"] for item in shortlist},
        duplicate_scores={item["asset_id"]: item["duplicate_scores"] for item in shortlist},
        crop_scores={item["asset_id"]: item["crop_scores"] for item in shortlist},
        selected_candidate=selected,
        alternatives=alternatives,
        manual_fallback_status=_manual_status(manual_request),
        reranking={"technical_rerank_enabled": technical_rerank_enabled},
    )


def write_review_bundle(project_root: str | Path, bundles: list[SceneReviewBundle], *, write_html: bool = True) -> dict[str, str]:
    root = Path(project_root)
    review_dir = root / "assets" / "review"
    review_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = review_dir / "visual_review_manifest.json"
    html_path = review_dir / "visual_review_board.html"
    manifest = {
        "schema_version": 1,
        "project_id": bundles[0].project_id if bundles else root.name,
        "scene_count": len(bundles),
        "scenes": [bundle.to_dict() for bundle in bundles],
    }
    _atomic_write_json(manifest_path, manifest)
    if write_html:
        html_path.write_text(_html_board(root, manifest), encoding="utf-8")
    return {"json_path": str(manifest_path), "html_path": str(html_path) if write_html else ""}


def write_review_manifest_data(project_root: str | Path, manifest: dict[str, Any], *, write_html: bool = True) -> dict[str, str]:
    root = Path(project_root)
    review_dir = root / "assets" / "review"
    review_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = review_dir / "visual_review_manifest.json"
    html_path = review_dir / "visual_review_board.html"
    _atomic_write_json(manifest_path, manifest)
    if write_html:
        html_path.write_text(_html_board(root, manifest), encoding="utf-8")
    return {"json_path": str(manifest_path), "html_path": str(html_path) if write_html else ""}


def inspect_review_manifest(path: str | Path) -> dict[str, Any]:
    target = Path(path)
    if not target.exists():
        return {
            "scene_count": 0,
            "analysed_candidates": 0,
            "preview_cache_hits": 0,
            "preview_cache_misses": 0,
            "failed_previews": 0,
            "exact_duplicates": 0,
            "near_duplicates": 0,
            "review_required_candidates": 0,
            "selected_candidates": 0,
            "missing_scenes": 0,
            "html_board_path": "",
        }
    data = json.loads(target.read_text(encoding="utf-8"))
    scenes = data.get("scenes", [])
    candidates = [candidate for scene in scenes for candidate in scene.get("shortlist", [])]
    duplicate_items = [score for candidate in candidates for score in candidate.get("duplicate_scores", [])]
    return {
        "scene_count": len(scenes),
        "analysed_candidates": len(candidates),
        "preview_cache_hits": sum(1 for candidate in candidates if candidate.get("preview_status") == "passed"),
        "preview_cache_misses": sum(1 for candidate in candidates if candidate.get("preview_status") == "not_analysed"),
        "failed_previews": sum(1 for candidate in candidates if candidate.get("preview_status") == "failed"),
        "exact_duplicates": sum(1 for item in duplicate_items if item.get("classification") == "exact_duplicate"),
        "near_duplicates": sum(1 for item in duplicate_items if item.get("classification") in {"near_duplicate", "likely_same_source_different_rendition"}),
        "review_required_candidates": sum(1 for candidate in candidates if candidate.get("review_required_reasons")),
        "selected_candidates": sum(1 for scene in scenes if scene.get("selected_candidate")),
        "missing_scenes": sum(1 for scene in scenes if not scene.get("selected_candidate")),
        "html_board_path": str(target.with_name("visual_review_board.html")),
    }


def select_candidate_after_review(
    candidates: list[dict[str, Any]],
    analyses: list[dict[str, Any]],
    *,
    metadata_selected_id: str,
    technical_rerank: bool,
    target_aspect_ratio: str = "9:16",
) -> dict[str, Any]:
    if not technical_rerank:
        return next((candidate for candidate in candidates if candidate.get("asset_id") == metadata_selected_id), candidates[0] if candidates else {})
    analysis_by_id = {str(item.get("asset_id") or ""): item for item in analyses}
    scored = []
    for index, candidate in enumerate(candidates):
        if candidate.get("review_required") or not candidate.get("allowed_for_render", True):
            continue
        analysis = analysis_by_id.get(str(candidate.get("asset_id") or ""), {})
        if analysis.get("analysis_status") != "passed":
            continue
        score = _combined_score(candidate, analysis, target_aspect_ratio)
        scored.append((score, -index, candidate))
    if not scored:
        return next((candidate for candidate in candidates if candidate.get("asset_id") == metadata_selected_id), candidates[0] if candidates else {})
    scored.sort(reverse=True)
    selected = dict(scored[0][2])
    selected["selected_by"] = "technical_rerank"
    selected["visual_combined_score"] = scored[0][0]
    return selected


def compute_repetition_penalties(
    candidate: dict[str, Any],
    *,
    neighbor_assets: list[dict[str, Any]],
    project_assets: list[dict[str, Any]],
) -> dict[str, Any]:
    reasons: list[str] = []
    duplicate_penalty = 0.0
    neighbor_penalty = 0.0
    asset_id = str(candidate.get("asset_id") or "")
    source = str(candidate.get("source_page_url") or candidate.get("source_page") or candidate.get("source_url") or "")
    checksum = str(candidate.get("checksum_sha256") or "")
    for item in neighbor_assets:
        if asset_id and asset_id == str(item.get("asset_id") or ""):
            duplicate_penalty += 60.0
            reasons.append("same_asset_id")
        if source and source == str(item.get("source_page_url") or item.get("source_page") or item.get("source_url") or ""):
            neighbor_penalty += 35.0
            reasons.append("same_source_url")
        if checksum and checksum == str(item.get("checksum_sha256") or ""):
            duplicate_penalty += 60.0
            reasons.append("same_checksum")
    project_count = 0
    for item in project_assets:
        if source and source == str(item.get("source_page_url") or item.get("source_page") or item.get("source_url") or ""):
            project_count += 1
        if asset_id and asset_id == str(item.get("asset_id") or ""):
            project_count += 1
    if project_count:
        neighbor_penalty += min(40.0, project_count * 12.0)
        reasons.append("project_repetition")
    return {
        "duplicate_penalty": duplicate_penalty,
        "neighbor_similarity_penalty": neighbor_penalty,
        "project_repetition_count": project_count,
        "reason": "|".join(dict.fromkeys(reasons)) or "no_repetition_detected",
        "overridden_by_user": False,
    }


def _combined_score(candidate: dict[str, Any], analysis: dict[str, Any], target_aspect_ratio: str) -> float:
    metadata = float(candidate.get("final_score") or candidate.get("total_score") or candidate.get("relevance_score") or 0.0)
    technical = float(analysis.get("technical_quality_score") or 0.0)
    crop_scores = analysis.get("crop_scores") if isinstance(analysis.get("crop_scores"), dict) else {}
    crop = float((crop_scores.get(target_aspect_ratio) or {}).get("heuristic_crop_suitability") or 0.0)
    duplicate_penalty = max((float(item.get("aggregate_similarity", 0.0)) * 20.0 for item in analysis.get("duplicate_scores", []) or []), default=0.0)
    return metadata * 0.42 + technical * 0.28 + crop * 0.18 - duplicate_penalty * 0.08


def _html_board(root: Path, manifest: dict[str, Any]) -> str:
    lines = [
        "<!doctype html>",
        "<html><head><meta charset=\"utf-8\"><title>Visual Review Board</title>",
        "<style>body{font-family:Arial,sans-serif;margin:24px;background:#f6f7f8;color:#1d252c}.scene{margin:0 0 28px;padding:16px;background:#fff;border:1px solid #d8dde3}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}.candidate{border:1px solid #d8dde3;padding:10px}.frames{display:flex;gap:6px;flex-wrap:wrap}.frames img{max-width:96px;max-height:130px;object-fit:cover}.selected{border-color:#2d6cdf}small{color:#53606b}a{color:#174ea6}"
        ".decision{margin:8px 0;padding:8px;background:#fafbfc;border:1px dashed #c5ced6;font-size:12px}"
        ".decision p{margin:4px 0}"
        ".badge{display:inline-block;padding:2px 8px;border-radius:10px;background:#e4e9ee;font-size:11px;margin:0 6px 2px 0}"
        ".b-full_support{background:#1e7d4f;color:#fff}.b-partial_support{background:#c88a12;color:#fff}"
        ".b-manual_confirmation_required{background:#8a4fbd;color:#fff}.b-unverified{background:#7a8894;color:#fff}"
        ".b-unsupported{background:#b23b3b;color:#fff}.b-relevant_but_rights_blocked{background:#2f6f9e;color:#fff}"
        ".slot-matched_slots{color:#1e7d4f}.slot-missing_slots{color:#b2661d}"
        ".slot-conflicting_slots{color:#8a4fbd}.slot-undecidable_slots{color:#66727d}</style>",
        "</head><body>",
        f"<h1>{html.escape(str(manifest.get('project_id') or 'Project'))}</h1>",
    ]
    for scene in manifest.get("scenes", []):
        lines.append("<section class=\"scene\">")
        lines.append(f"<h2>{html.escape(str(scene.get('scene_id') or 'scene'))}</h2>")
        lines.append(f"<p>{html.escape(str(scene.get('scene_text') or ''))}</p>")
        lines.append(f"<small>Target aspect: {html.escape(str(scene.get('target_aspect_ratio') or ''))}</small>")
        lines.append("<div class=\"grid\">")
        selected_id = str((scene.get("selected_candidate") or {}).get("asset_id") or "")
        for candidate in scene.get("shortlist", []):
            classes = "candidate selected" if candidate.get("asset_id") == selected_id else "candidate"
            lines.append(f"<article class=\"{classes}\">")
            lines.append(f"<h3>{html.escape(str(candidate.get('asset_id') or 'candidate'))}</h3>")
            lines.append(f"<p>{html.escape(str(candidate.get('provider') or ''))}</p>")
            source = str(candidate.get("source_page_url") or "")
            if source.startswith("http"):
                lines.append(f"<p><a href=\"{html.escape(source)}\">Source page</a></p>")
            license_data = candidate.get("license") if isinstance(candidate.get("license"), dict) else {}
            lines.append(f"<p>{html.escape(str(candidate.get('author_name') or ''))} | {html.escape(str(license_data.get('license_name') or ''))}</p>")
            lines.append(
                f"<p>metadata {float(candidate.get('metadata_score') or 0):.1f} | technical {float(candidate.get('technical_score') or 0):.1f} | combined {float(candidate.get('combined_score') or 0):.1f}</p>"
            )
            lines.append("<div class=\"frames\">")
            for frame in candidate.get("sampled_frames", [])[:5]:
                frame_path = str(frame.get("local_frame_path") or "")
                rel = _relative_path(root, frame_path)
                if rel:
                    lines.append(f"<img src=\"{html.escape(rel)}\" alt=\"sampled frame\">")
            lines.append("</div>")
            lines.extend(_decision_html(candidate))
            reasons = ", ".join(candidate.get("rejection_reasons") or candidate.get("review_required_reasons") or [])
            if reasons:
                lines.append(f"<small>{html.escape(reasons)}</small>")
            semantic = candidate.get("semantic_analysis") if isinstance(candidate.get("semantic_analysis"), dict) else {}
            if semantic:
                scores = semantic.get("aggregate_scores") if isinstance(semantic.get("aggregate_scores"), dict) else {}
                must_have = ", ".join(str(item.get("term") or "") for item in semantic.get("must_have_results", []) if isinstance(item, dict) and item.get("term"))
                negatives = ", ".join(str(item.get("term") or "") for item in semantic.get("negative_element_results", []) if isinstance(item, dict) and item.get("present"))
                mismatch = ", ".join(str(item) for item in semantic.get("mismatch_reasons", []) if str(item))
                evidence = "; ".join(str(item.get("summary") or "") for item in semantic.get("evidence", []) if isinstance(item, dict) and item.get("summary"))
                lines.append("<div class=\"semantic\">")
                lines.append("<strong>Semantic</strong>")
                lines.append(
                    f"<p>confidence {float(semantic.get('confidence') or 0):.2f} | semantic score {float(semantic.get('semantic_score') or 0):.2f}</p>"
                )
                lines.append(
                    "<p>"
                    f"subject {float(scores.get('subject_match') or 0):.2f} | "
                    f"action {float(scores.get('action_match') or 0):.2f} | "
                    f"environment {float(scores.get('environment_match') or 0):.2f}"
                    "</p>"
                )
                if must_have:
                    lines.append(f"<p>must-have: {html.escape(must_have)}</p>")
                if negatives:
                    lines.append(f"<p>negatives: {html.escape(negatives)}</p>")
                if mismatch:
                    lines.append(f"<p>mismatch: {html.escape(mismatch)}</p>")
                if evidence:
                    lines.append(f"<p>evidence: {html.escape(evidence)}</p>")
                lines.append("</div>")
            lines.append("</article>")
        lines.append("</div>")
        manual = scene.get("manual_fallback_status") or {}
        if manual.get("provider") == "envato_manual":
            lines.append("<p>Envato manual fallback: manual import required.</p>")
        lines.append("</section>")
    lines.append("</body></html>")
    return "\n".join(lines) + "\n"


def _safe_license(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {"license_name": str(value or "")}
    allowed = {"license_name", "license_url", "provider_terms_url", "rights_status", "allowed_for_render", "review_required", "attribution_text"}
    return {key: value.get(key) for key in allowed if key in value}


def _decision_fields(candidate: dict[str, Any]) -> dict[str, Any]:
    """The selection decision, carried onto the board entry that shows the candidate.

    The board reads it from the candidate itself. It never reconstructs it out of
    ``ranked_candidates``, which is what it had to do while the decision was being
    dropped between selection and the manifest.
    """
    if not has_decision(candidate):
        return {}
    decision = read_decision(candidate)
    slots = decision.slots if isinstance(decision.slots, dict) else {}
    return {
        DECISION_KEY: dict(candidate[DECISION_KEY]),
        "support_status": decision.support_status,
        "support_requirements": list(decision.support_requirements),
        "slot_verdict": decision.slot_verdict,
        "missing_slots": [str(item) for item in (slots.get("missing_slots") or [])],
        "conflicting_slots": [str(item) for item in (slots.get("conflicting_slots") or [])],
        "technical_status": decision.technical_status,
        "render_ready": decision.render_ready,
    }


_SLOT_LABELS = {
    "matched_slots": "подтверждено",
    "missing_slots": "не подтверждено",
    "conflicting_slots": "противоречит",
    "undecidable_slots": "нечем проверить",
}

_FRAMING_LABELS = {
    "vertical_ready": "уже 9:16, резать не нужно",
    "crop_review_required": "придётся резать - нужен глаз человека",
    "low_resolution_after_crop": "после кропа слишком мало пикселей",
    "technical_rejected": "исходник мал сам по себе",
    "aspect_ratio_mismatch": "панорама, в 9:16 не ложится",
    "unknown": "размеры неизвестны",
}


def _decision_html(candidate: dict[str, Any]) -> list[str]:
    """The verdict, on the page a person actually opens.

    Everything here is read off the candidate's own stored decision. The board used to
    print three scores and a list of reject codes, which is the one thing a reviewer
    cannot act on: it said a candidate was refused without saying *which requirement of
    the scene* went unanswered, or whether the frame survives a 9:16 crop.
    """
    if not has_decision(candidate):
        return []
    decision = read_decision(candidate)
    slots = decision.slots if isinstance(decision.slots, dict) else {}
    support = decision.support_status or "unverified"

    lines = ["<div class=\"decision\">"]
    lines.append(
        f"<p><span class=\"badge b-{html.escape(support)}\">{html.escape(support)}</span>"
        f"<span class=\"badge\">{html.escape(decision.slot_verdict or 'unverified')}</span>"
        f"<span class=\"badge\">render-ready: {'да' if decision.render_ready else 'нет'}</span></p>"
    )
    if decision.support_requirements:
        lines.append(
            f"<p><b>осталось сделать:</b> {html.escape(', '.join(decision.support_requirements))}</p>"
        )

    for key, label in _SLOT_LABELS.items():
        names = [str(item) for item in (slots.get(key) or [])]
        if names:
            lines.append(f"<p class=\"slot-{key}\"><b>{label}:</b> {html.escape(', '.join(names))}</p>")

    framing = decision.framing if isinstance(decision.framing, dict) else {}
    status = str(decision.technical_status or framing.get("status") or "unknown")
    explanation = _FRAMING_LABELS.get(status, status)
    size = ""
    if framing.get("source_width") and framing.get("source_height"):
        size = (
            f" - {int(framing['source_width'])}x{int(framing['source_height'])}"
            f" → {int(framing.get('effective_width') or 0)}x{int(framing.get('effective_height') or 0)}"
        )
    lines.append(f"<p><b>кроп:</b> {html.escape(status)} — {html.escape(explanation)}{html.escape(size)}</p>")

    rights = f"{decision.rights_status or 'unknown'}"
    if not decision.rights_allowed_for_render:
        rights += " (нельзя в рендер)"
    elif decision.rights_review_required:
        rights += " (нужна проверка)"
    lines.append(f"<p><b>права:</b> {html.escape(rights)}</p>")
    lines.append("</div>")
    return lines


def attach_selected_asset(bundle: "SceneReviewBundle", selected: dict[str, Any] | None) -> "SceneReviewBundle":
    """Point the bundle's selected entry at the asset that was really used.

    Called after the download, which is the step that replaces the ranked candidate
    with a record of the file on disk. The decision travels with it, so the board shows
    the verdict for the asset a viewer can actually open.
    """
    if not isinstance(selected, dict) or not selected:
        return bundle
    selected_id = str(selected.get("asset_id") or "")
    entry = next(
        (
            dict(candidate)
            for candidate in bundle.shortlist
            if str(candidate.get("asset_id") or "") == selected_id
        ),
        {},
    )
    entry.update(
        {
            "asset_id": selected_id,
            "provider": selected.get("provider", ""),
            "provider_asset_id": selected.get("provider_asset_id", ""),
            "source_page_url": (
                selected.get("source_page_url")
                or selected.get("source_page")
                or selected.get("source_url", "")
            ),
            "author_name": selected.get("author_name")
            or selected.get("author", ""),
            "license": _safe_license(selected.get("license")),
            "policy_status": _policy_status(selected),
            "vision_tags": list(selected.get("vision_tags") or []),
            "vision_tags_asset_id": str(selected.get("vision_tags_asset_id") or ""),
            "vision_tags_source_sha256": str(
                selected.get("vision_tags_source_sha256") or ""
            ),
            "vision_tags_cache_key": str(selected.get("vision_tags_cache_key") or ""),
        }
    )
    replaces_asset_id = str(selected.get("replaces_asset_id") or "")
    if replaces_asset_id:
        entry["replaces_asset_id"] = replaces_asset_id
    entry.update(_decision_fields(selected))
    entry["local_path"] = str(selected.get("path") or selected.get("local_path") or "")
    entry["download_status"] = str(selected.get("download_status") or "")
    bundle.selected_candidate = entry
    bundle.alternatives = [
        dict(candidate)
        for candidate in bundle.shortlist
        if str(candidate.get("asset_id") or "") != selected_id
    ][:4]
    return bundle


def _semantic_fields(analysis: dict[str, Any]) -> dict[str, Any]:
    semantic = analysis.get("semantic_analysis") if isinstance(analysis.get("semantic_analysis"), dict) else {}
    if not semantic:
        return {}
    return {
        "semantic_analysis": semantic,
        "semantic_rank": analysis.get("semantic_rank", 0),
        "semantic_score": float(semantic.get("semantic_score") or analysis.get("semantic_score") or 0.0),
        "semantic_status": str(semantic.get("status") or analysis.get("semantic_status") or ""),
        "semantic_review_required": bool(
            semantic.get("review_required_reasons")
            or str(semantic.get("status") or "") not in {"", "success"}
        ),
    }


def _policy_status(candidate: dict[str, Any]) -> str:
    decision = candidate.get("policy_decision") if isinstance(candidate.get("policy_decision"), dict) else {}
    if decision.get("status"):
        return str(decision["status"])
    if candidate.get("review_required"):
        return "review_required"
    if candidate.get("allowed_for_render"):
        return "allowed"
    return "unknown"


def _rejection_reasons(candidate: dict[str, Any], analysis: dict[str, Any]) -> list[str]:
    reasons = []
    if candidate.get("rejected") and candidate.get("reject_reason"):
        reasons.append(str(candidate["reject_reason"]))
    if analysis.get("analysis_status") == "failed":
        reasons.append(str(analysis.get("analysis_error") or "preview_analysis_failed"))
    return reasons


def _review_required_reasons(candidate: dict[str, Any], analysis: dict[str, Any]) -> list[str]:
    reasons = []
    if candidate.get("review_required"):
        reasons.append("license_review_required")
    if not candidate.get("allowed_for_render", True):
        reasons.append("not_allowed_for_render")
    if analysis.get("analysis_status") == "failed":
        reasons.append("preview_analysis_failed")
    return list(dict.fromkeys(reasons))


def _manual_status(manual_request: dict[str, Any] | None) -> dict[str, Any]:
    if not manual_request:
        return {"status": "not_requested"}
    return {
        "status": "manual_action_required",
        "provider": manual_request.get("provider", ""),
        "search_urls": manual_request.get("search_urls", []),
        "automatic_download": bool(manual_request.get("automatic_download", False)),
    }


def _relative_path(root: Path, raw_path: str) -> str:
    if not raw_path:
        return ""
    try:
        return Path(raw_path).resolve().relative_to(root.resolve()).as_posix()
    except Exception:
        return ""


def _atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    temp = path.with_suffix(path.suffix + ".part")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)
