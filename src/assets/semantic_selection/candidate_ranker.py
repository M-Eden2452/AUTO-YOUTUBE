from __future__ import annotations

import re
from typing import Any

from .models import (
    SCENE_ENVIRONMENT,
    SCENE_EXACT_SUBJECT,
    SCENE_TRANSITION,
    SemanticScene,
)


MIN_SCORE = 60.0
EXACT_SUBJECT_MIN_SCORE = 75.0


def rank_candidates(
    scene: SemanticScene,
    candidates: list[dict[str, Any]],
    *,
    used_asset_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    used = used_asset_ids or set()
    ranked = [_score_candidate(scene, candidate, used) for candidate in candidates]
    return sorted(ranked, key=lambda item: (not item.get("rejected", False), item.get("final_score", 0)), reverse=True)


def select_best_candidate(
    scene: SemanticScene,
    candidates: list[dict[str, Any]],
    *,
    used_asset_ids: set[str] | None = None,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    ranked = rank_candidates(scene, candidates, used_asset_ids=used_asset_ids)
    for candidate in ranked:
        if not candidate.get("rejected"):
            return candidate, ranked
    return None, ranked


def _score_candidate(scene: SemanticScene, candidate: dict[str, Any], used: set[str]) -> dict[str, Any]:
    text = _candidate_text(candidate)
    tokens = _tokens(text)
    vision_tags = [str(tag).lower() for tag in candidate.get("vision_tags", [])]
    all_tokens = set(tokens) | set(vision_tags)
    subject_match = _field_match(scene.subject, all_tokens, text, aliases={"southern right whale": ["southern right whale", "right whale", "whale"]})
    action_match = _field_match(scene.action, all_tokens, text)
    environment_match = _field_match(scene.environment, all_tokens, text, aliases={"coastal waters": ["coast", "coastline", "coastal", "ocean", "sea"]})
    camera_match = _field_match(scene.camera, all_tokens, text)
    quality_score = _normal_score(candidate.get("quality_score"), _quality_score(candidate))
    vertical_score = _normal_score(candidate.get("vertical_score"), _vertical_score(candidate))
    negative_matches = [word for word in scene.must_not_include if _contains_concept(word, all_tokens, text)]
    contradiction_penalty = min(40.0, len(negative_matches) * 25.0)
    duplicate_penalty = 20.0 if str(candidate.get("asset_id", "")) in used else float(candidate.get("duplicate_penalty") or 0)
    watermark_penalty = _watermark_penalty(candidate, all_tokens, text)
    final_score = (
        0.35 * subject_match
        + 0.20 * action_match
        + 0.15 * environment_match
        + 0.10 * camera_match
        + 0.10 * quality_score
        + 0.10 * vertical_score
        - contradiction_penalty
        - duplicate_penalty
        - watermark_penalty
    )
    must_missing = [item for item in scene.must_include if not _contains_concept(item, all_tokens, text)]
    fallback_level = _candidate_fallback_level(scene, subject_match, action_match, environment_match)
    min_score = EXACT_SUBJECT_MIN_SCORE if scene.visual_priority == SCENE_EXACT_SUBJECT else MIN_SCORE
    reject_reasons: list[str] = []
    if must_missing:
        reject_reasons.append("must_include_missing:" + ",".join(must_missing))
    if negative_matches:
        reject_reasons.append("negative_matches:" + ",".join(negative_matches))
    if set(vision_tags) & set(scene.must_not_include):
        reject_reasons.append("vision_mismatch")
    if scene.visual_priority not in {SCENE_ENVIRONMENT, SCENE_TRANSITION} and fallback_level >= 4:
        reject_reasons.append("fallback_level_not_allowed")
    if final_score < min_score:
        reject_reasons.append(f"score_below_{int(min_score)}")
    allowed = bool(candidate.get("allowed_for_render", True))
    if not allowed:
        reject_reasons.append("rights_not_allowed")
    result = {
        **candidate,
        "subject_match": round(subject_match, 3),
        "action_match": round(action_match, 3),
        "environment_match": round(environment_match, 3),
        "camera_match": round(camera_match, 3),
        "quality_score": round(quality_score, 3),
        "vertical_score": round(vertical_score, 3),
        "negative_matches": negative_matches,
        "contradiction_penalty": contradiction_penalty,
        "duplicate_penalty": duplicate_penalty,
        "watermark_penalty": watermark_penalty,
        "fallback_level": fallback_level,
        "scene_match_score": round(max(0.0, min(100.0, final_score)), 3),
        "final_score": round(final_score, 3),
        "rejected": bool(reject_reasons),
        "reject_reason": ";".join(reject_reasons),
        "why_selected": _why_selected(scene, subject_match, action_match, environment_match),
        "semantic_scene": scene.to_dict(),
        "vision_tags": candidate.get("vision_tags", []),
    }
    return result


def _candidate_text(candidate: dict[str, Any]) -> str:
    pieces = []
    for key in ("title", "description", "source_url", "source_page", "search_query", "query", "keywords", "tags"):
        value = candidate.get(key, "")
        if isinstance(value, list):
            pieces.extend(str(item) for item in value)
        else:
            pieces.append(str(value))
    return " ".join(pieces).lower()


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _field_match(values: list[str], tokens: set[str], text: str, aliases: dict[str, list[str]] | None = None) -> float:
    if not values:
        return 100.0
    scores = []
    alias_map = aliases or {}
    for value in values:
        terms = alias_map.get(value, [value])
        scores.append(max(_concept_score(term, tokens, text) for term in terms))
    return sum(scores) / len(scores)


def _concept_score(concept: str, tokens: set[str], text: str) -> float:
    normalized = concept.lower().strip()
    if not normalized:
        return 100.0
    if normalized in text:
        return 100.0
    words = [word for word in re.findall(r"[a-z0-9]+", normalized) if word]
    if not words:
        return 0.0
    matched = sum(1 for word in words if word in tokens)
    return 100.0 * matched / len(words)


def _contains_concept(concept: str, tokens: set[str], text: str) -> bool:
    return _concept_score(concept, tokens, text) >= 99.0


def _normal_score(value: Any, fallback: float) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        score = fallback
    if score <= 10:
        score *= 10
    return max(0.0, min(100.0, score))


def _quality_score(candidate: dict[str, Any]) -> float:
    width = int(candidate.get("width") or 0)
    height = int(candidate.get("height") or 0)
    pixels = width * height
    if pixels >= 3840 * 2160:
        return 100.0
    if pixels >= 1920 * 1080:
        return 85.0
    if pixels >= 1280 * 720:
        return 65.0
    return 25.0 if pixels else 10.0


def _vertical_score(candidate: dict[str, Any]) -> float:
    width = int(candidate.get("width") or 0)
    height = int(candidate.get("height") or 0)
    if not width or not height:
        return 0.0
    ratio = width / height
    return max(0.0, min(100.0, 100.0 - abs(ratio - (9 / 16)) * 100.0))


def _watermark_penalty(candidate: dict[str, Any], tokens: set[str], text: str) -> float:
    if float(candidate.get("watermark_penalty") or 0):
        return float(candidate.get("watermark_penalty") or 0)
    if {"watermark", "logo"} & tokens or "stock logo" in text:
        return 35.0
    return 0.0


def _candidate_fallback_level(
    scene: SemanticScene,
    subject_match: float,
    action_match: float,
    environment_match: float,
) -> int:
    if subject_match >= 80 and action_match >= 70:
        return 1
    if subject_match >= 80:
        return 2
    if subject_match >= 40 and environment_match >= 70:
        return 3
    if environment_match >= 70:
        return 4
    return 5


def _why_selected(scene: SemanticScene, subject_match: float, action_match: float, environment_match: float) -> str:
    return (
        f"{scene.visual_priority}: subject={subject_match:.0f}, "
        f"action={action_match:.0f}, environment={environment_match:.0f}"
    )
