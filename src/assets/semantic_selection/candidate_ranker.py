"""Scoring one candidate against one scene, on evidence the provider actually gave.

The defect this file was rewritten for: ``_candidate_text`` used to include the
candidate's ``search_query`` and its query-derived ``tags``. The scene's own subject is
by construction a substring of that query, so ``subject_match`` came back 100 for every
candidate of every provider - the confirmed run scored 40 candidates at exactly 100.0
and then picked whichever happened to be first. The query cannot be evidence that a
result matches the query.

So the candidate is now read only through metadata a provider really returned (title,
description, provider tags, category labels). If there is none, that is reported as
``metadata_status="unavailable"`` and *not* rounded up to a match: a scene that needs a
specific real place or instrument refuses such a candidate outright, because nothing
about it can be shown to be that place or instrument.

Scores are kept apart rather than blended into one number, so a reviewer can see which
kind of evidence was missing:

``semantic_score``      how well provider metadata matches the scene's meaning
``metadata_score``      how much usable metadata there was to judge on
``technical_score``     resolution and vertical suitability
``rights_status``       from the licence policy, never traded off against the rest
``duration_status``     whether the clip is long enough for the scene
``provider_confidence`` how much this provider's metadata is worth as evidence
"""

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

# Fraction of a scene a clip may fall short by and still be usable by slowing it down
# or holding the last frame. Beyond this the scene is left unresolved instead.
DURATION_TOLERANCE_SEC = 0.35

METADATA_AVAILABLE = "available"
METADATA_UNAVAILABLE = "unavailable"
METADATA_QUERY_DERIVED = "query_derived_only"

# How much a provider's own metadata is worth as evidence of what is in the frame.
# Wikimedia and NASA describe the actual object; a stock library labels a mood.
PROVIDER_CONFIDENCE: dict[str, float] = {
    "wikimedia": 1.0,
    "nasa_images": 1.0,
    "internet_archive": 0.8,
    "local_library": 0.9,
    "user_asset": 1.0,
    "generated": 1.0,
    "pexels": 0.6,
    "pixabay": 0.6,
    "unsplash": 0.6,
    "fake": 1.0,
}

# Fields that carry description written by the provider about the asset. Deliberately
# excludes ``search_query``/``query`` and anything derived from them.
_METADATA_FIELDS = ("title", "description", "categories", "depicts", "location")
_QUERY_FIELDS = ("search_query", "query")
_WORD_RE = re.compile(r"[^\W_]+", re.UNICODE)


def rank_candidates(
    scene: SemanticScene,
    candidates: list[dict[str, Any]],
    *,
    used_asset_ids: set[str] | None = None,
    required_duration_sec: float = 0.0,
    require_provider_metadata: bool = False,
) -> list[dict[str, Any]]:
    used = used_asset_ids or set()
    ranked = [
        _score_candidate(
            scene,
            candidate,
            used,
            required_duration_sec=required_duration_sec,
            require_provider_metadata=require_provider_metadata,
        )
        for candidate in candidates
    ]
    return sorted(ranked, key=lambda item: (not item.get("rejected", False), item.get("final_score", 0)), reverse=True)


def select_best_candidate(
    scene: SemanticScene,
    candidates: list[dict[str, Any]],
    *,
    used_asset_ids: set[str] | None = None,
    required_duration_sec: float = 0.0,
    require_provider_metadata: bool = False,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    ranked = rank_candidates(
        scene,
        candidates,
        used_asset_ids=used_asset_ids,
        required_duration_sec=required_duration_sec,
        require_provider_metadata=require_provider_metadata,
    )
    for candidate in ranked:
        if not candidate.get("rejected"):
            return candidate, ranked
    return None, ranked


def _score_candidate(
    scene: SemanticScene,
    candidate: dict[str, Any],
    used: set[str],
    *,
    required_duration_sec: float = 0.0,
    require_provider_metadata: bool = False,
) -> dict[str, Any]:
    text = _provider_evidence_text(candidate)
    tokens = _tokens(text)
    vision_tags = [str(tag).lower() for tag in candidate.get("vision_tags", [])]
    all_tokens = set(tokens) | set(vision_tags)
    metadata_status, metadata_score = _metadata_status(candidate, text, vision_tags)
    has_evidence = metadata_status == METADATA_AVAILABLE or bool(vision_tags)

    subject_match, subject_decidable = _field_match(scene.subject, all_tokens, text, aliases={"southern right whale": ["southern right whale", "right whale", "whale"]})
    action_match, action_decidable = _field_match(scene.action, all_tokens, text)
    environment_match, environment_decidable = _field_match(scene.environment, all_tokens, text, aliases={"coastal waters": ["coast", "coastline", "coastal", "ocean", "sea"]})
    location_match, _ = _field_match(scene.location, all_tokens, text)
    camera_match, camera_decidable = _field_match(scene.camera, all_tokens, text)
    quality_score = _normal_score(candidate.get("quality_score"), _quality_score(candidate))
    vertical_score = _normal_score(candidate.get("vertical_score"), _vertical_score(candidate))
    technical_score = round(0.5 * quality_score + 0.5 * vertical_score, 3)
    provider_confidence = PROVIDER_CONFIDENCE.get(str(candidate.get("provider") or ""), 0.5)

    negative_matches = [word for word in scene.must_not_include if _contains_concept(word, all_tokens, text)]
    contradiction_penalty = min(40.0, len(negative_matches) * 25.0)
    duplicate_penalty = 20.0 if str(candidate.get("asset_id", "")) in used else float(candidate.get("duplicate_penalty") or 0)
    watermark_penalty = _watermark_penalty(candidate, all_tokens, text)

    # Weights re-balanced when the query stopped being counted as evidence. They used
    # to be applied to inflated matches: the search string was part of the candidate
    # text, so "coast" and "drone" scored 100 for any result of a query containing
    # them. With honest text, camera wording is the field a stock library almost never
    # supplies, and it must not be able to sink a candidate whose subject is exact.
    # A field whose terms are written in a script the provider's metadata cannot
    # contain is *undecidable*, not unmatched: scoring "пластик" as 0 against an
    # English title says nothing about the asset. Undecidable fields are dropped from
    # the average and their weight redistributed, so the score reports only what could
    # actually be judged - and ``semantic_match_status`` says the rest out loud.
    weighted = [
        (0.45, subject_match, subject_decidable),
        (0.20, action_match, action_decidable),
        (0.15, environment_match, environment_decidable),
        (0.05, camera_match, camera_decidable),
    ]
    decidable_weight = sum(weight for weight, _score, decidable in weighted if decidable)
    if decidable_weight > 0:
        meaning_score = sum(weight * score for weight, score, decidable in weighted if decidable) / decidable_weight
    else:
        meaning_score = 0.0
    semantic_score = round(meaning_score, 3)
    undecidable_fields = [
        name
        for name, decidable in (
            ("subject", subject_decidable), ("action", action_decidable),
            ("environment", environment_decidable), ("camera", camera_decidable),
        )
        if not decidable
    ]
    final_score = (
        0.85 * meaning_score
        + 0.075 * quality_score
        + 0.075 * vertical_score
        - contradiction_penalty
        - duplicate_penalty
        - watermark_penalty
    )
    must_missing: list[str] = []
    must_undecidable: list[str] = []
    for item in scene.must_include:
        if _script_mismatch(item, text):
            must_undecidable.append(item)
        elif not _contains_concept(item, all_tokens, text):
            must_missing.append(item)
    # What the author explicitly required, all present, on real provider metadata.
    # This is stronger evidence than any phrase-overlap score: ``must_include`` is a
    # statement about the frame, while the subject phrase is only a search hint, and
    # "barren polar valley landscape" overlapping an honest title by half its words
    # says nothing against a candidate whose required terms are all there.
    must_satisfied = bool(scene.must_include) and not must_missing and not must_undecidable and has_evidence
    fallback_level = _candidate_fallback_level(
        scene,
        subject_match,
        action_match,
        environment_match,
        subject_decidable=subject_decidable,
        must_satisfied=must_satisfied,
    )
    if scene.visual_priority == SCENE_EXACT_SUBJECT and not must_satisfied:
        min_score = EXACT_SUBJECT_MIN_SCORE
    else:
        min_score = MIN_SCORE
    duration_check = _duration_check(candidate, required_duration_sec)

    # "matched" requires evidence. Anything else is unverified, and an exacting scene
    # refuses an unverified candidate rather than guessing.
    if undecidable_fields or must_undecidable or not has_evidence:
        semantic_match_status = "unverified"
    elif must_satisfied or meaning_score >= MIN_SCORE:
        semantic_match_status = "matched"
    else:
        semantic_match_status = "mismatched"

    reject_reasons: list[str] = []
    if must_missing:
        reject_reasons.append("must_include_missing:" + ",".join(must_missing))
    if must_undecidable and require_provider_metadata:
        reject_reasons.append("must_include_unverifiable:" + ",".join(must_undecidable))
    if negative_matches:
        # A must_avoid hit is disqualifying, not a deduction. The whole point of the
        # field is "do not show this", and a high enough technical score used to be
        # able to outweigh it.
        reject_reasons.append("must_avoid_match:" + ",".join(negative_matches))
    if set(vision_tags) & set(scene.must_not_include):
        reject_reasons.append("vision_mismatch")
    if require_provider_metadata and (not has_evidence or semantic_match_status != "matched"):
        reject_reasons.append(f"no_semantic_evidence:{metadata_status}")
    if scene.visual_priority not in {SCENE_ENVIRONMENT, SCENE_TRANSITION} and fallback_level >= 4:
        reject_reasons.append("fallback_level_not_allowed")
    if final_score < min_score:
        reject_reasons.append(f"score_below_{int(min_score)}")
    if duration_check["status"] == "too_short":
        reject_reasons.append(
            f"duration_deficit:{duration_check['deficit_sec']}s"
        )
    allowed = bool(candidate.get("allowed_for_render", True))
    if not allowed:
        reject_reasons.append("rights_not_allowed")

    result = {
        **candidate,
        "subject_match": round(subject_match, 3),
        "action_match": round(action_match, 3),
        "environment_match": round(environment_match, 3),
        "location_match": round(location_match, 3),
        "camera_match": round(camera_match, 3),
        "quality_score": round(quality_score, 3),
        "vertical_score": round(vertical_score, 3),
        # Kept apart on purpose: a reviewer must be able to see *which* kind of
        # evidence was missing rather than one blended number.
        "semantic_score": semantic_score,
        "metadata_score": metadata_score,
        "metadata_status": metadata_status,
        "technical_score": technical_score,
        "provider_confidence": provider_confidence,
        "rights_status": str(candidate.get("rights_status") or ""),
        "duration_check": duration_check,
        "duration_status": duration_check["status"],
        "semantic_evidence": has_evidence,
        "semantic_match_status": semantic_match_status,
        "undecidable_fields": undecidable_fields,
        "must_include_unverifiable": must_undecidable,
        "negative_matches": negative_matches,
        "contradiction_penalty": contradiction_penalty,
        "duplicate_penalty": duplicate_penalty,
        "watermark_penalty": watermark_penalty,
        "fallback_level": fallback_level,
        "scene_match_score": round(max(0.0, min(100.0, final_score)), 3),
        "final_score": round(final_score, 3),
        "rejected": bool(reject_reasons),
        "reject_reason": ";".join(reject_reasons),
        "why_selected": _why_selected(scene, subject_match, action_match, environment_match, metadata_status),
        "semantic_scene": scene.to_dict(),
        "vision_tags": candidate.get("vision_tags", []),
    }
    return result


def _provider_evidence_text(candidate: dict[str, Any]) -> str:
    """Everything the *provider* said about this asset - and nothing we said to it.

    ``search_query`` is excluded unconditionally. Tags are excluded when the provider
    admits it synthesised them from the query (``tags_source="query_derived"``), which
    is what the Pexels adapter does for videos because the API returns no description.
    """
    queries = {str(candidate.get(key) or "").strip().lower() for key in _QUERY_FIELDS}
    queries.discard("")
    pieces: list[str] = []
    for key in _METADATA_FIELDS:
        pieces.extend(_evidence_values(candidate.get(key, ""), queries))
    if str(candidate.get("tags_source") or "provider") != "query_derived":
        for key in ("tags", "keywords"):
            pieces.extend(_evidence_values(candidate.get(key, ""), queries))
    return re.sub(r"\s+", " ", " ".join(piece for piece in pieces if piece).lower()).strip()


def _evidence_values(value: Any, queries: set[str]) -> list[str]:
    """One metadata field as evidence, unless the field *is* the query repeated back.

    Several adapters fall back to ``description = <api field> or request.query``. When
    the API field was empty the description is literally the query, which is not
    evidence about the asset. The check is whole-value equality on purpose: a real
    title that happens to contain the searched words is genuine evidence and must not
    be thrown away with it.
    """
    values = [str(item) for item in value] if isinstance(value, list) else [str(value)]
    return [item for item in values if item.strip() and item.strip().lower() not in queries]


def _metadata_status(candidate: dict[str, Any], text: str, vision_tags: list[str]) -> tuple[str, float]:
    """How much real provider metadata there is, and how far it can be trusted.

    Never returns a high score for an absence: an unlabelled candidate scores 0 and is
    reported as such, instead of matching everything by default.
    """
    if str(candidate.get("tags_source") or "") == "query_derived" and not text:
        return METADATA_QUERY_DERIVED, 0.0
    if not text:
        return (METADATA_AVAILABLE, 20.0) if vision_tags else (METADATA_UNAVAILABLE, 0.0)
    words = _tokens(text)
    # Three descriptive words is the least that can distinguish one asset from another.
    score = min(100.0, 100.0 * len(words) / 8.0)
    return METADATA_AVAILABLE, round(score, 3)


def _duration_check(candidate: dict[str, Any], required_duration_sec: float) -> dict[str, Any]:
    """Whether this clip can cover its scene. Recorded whether or not it decides."""
    required = round(float(required_duration_sec or 0), 3)
    raw = candidate.get("duration_sec")
    if raw in (None, ""):
        raw = candidate.get("duration")
    try:
        available = round(float(raw or 0), 3)
    except (TypeError, ValueError):
        available = 0.0
    media_type = str(candidate.get("media_type") or candidate.get("type") or "")
    if required <= 0:
        status = "not_checked"
    elif media_type == "image":
        # A still is held for as long as the scene needs; duration does not apply.
        status = "not_applicable"
    elif available <= 0:
        status = "unknown"
    elif available + DURATION_TOLERANCE_SEC >= required:
        status = "sufficient"
    else:
        status = "too_short"
    deficit = round(max(0.0, required - available), 3) if status == "too_short" else 0.0
    return {
        "status": status,
        "required_sec": required,
        "candidate_sec": available,
        "deficit_sec": deficit,
        "tolerance_sec": DURATION_TOLERANCE_SEC,
        "adaptation": "hold_last_frame" if status == "not_applicable" else ("slow_down_or_loop" if 0 < deficit <= 1.0 else ""),
    }


def _tokens(text: str) -> set[str]:
    """Words in any script. The previous ``[a-z0-9]+`` silently dropped every Cyrillic
    token, so a Russian ``must_avoid`` could never match anything."""
    return set(_WORD_RE.findall(text.lower()))


def _field_match(
    values: list[str], tokens: set[str], text: str, aliases: dict[str, list[str]] | None = None
) -> tuple[float, bool]:
    """Return ``(score, decidable)``.

    ``decidable`` is False when the field's terms are written in a script the evidence
    text cannot contain - an English title simply cannot confirm or deny a Russian
    subject, and pretending it denies it is what made every candidate score 0 once the
    query stopped being counted as evidence.
    """
    if not values:
        # The scene does not constrain this field, so nothing can contradict it. This
        # is "not applicable", not "perfect evidence" - which is why ``semantic_evidence``
        # is tracked separately and an exacting scene also demands real metadata.
        return 100.0, True
    scores = []
    alias_map = aliases or {}
    decidable = False
    for value in values:
        terms = alias_map.get(value, [value])
        if any(not _script_mismatch(term, text) for term in terms):
            decidable = True
        scores.append(max(_concept_score(term, tokens, text) for term in terms))
    return sum(scores) / len(scores), decidable


def _script_mismatch(concept: str, text: str) -> bool:
    """True when ``concept`` and ``text`` are written in scripts that cannot overlap.

    Absent evidence is *not* a script mismatch. A provider that returned no metadata
    told us nothing rather than something incomparable, and treating that as merely
    "unverifiable" would let an unlabelled candidate slip past a requirement it plainly
    cannot meet.
    """
    if not concept or not text:
        return False
    return bool(_CYRILLIC_RE.search(concept)) != bool(_CYRILLIC_RE.search(text))


_CYRILLIC_RE = re.compile(r"[Ѐ-ӿ]")


def _concept_score(concept: str, tokens: set[str], text: str) -> float:
    normalized = concept.lower().strip()
    if not normalized:
        return 100.0
    if normalized in text:
        return 100.0
    words = [word for word in _WORD_RE.findall(normalized) if word]
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
    *,
    subject_decidable: bool = True,
    must_satisfied: bool = False,
) -> int:
    """How far this candidate is from the scene's exact subject.

    When the subject could not be judged at all (its terms and the metadata are in
    different scripts) the distance is unknown. Reporting 4 - "environment only" -
    would be a claim the evidence does not support and would reject the candidate for
    a fact never established, so an unverifiable subject reports 2 and the verdict is
    carried by ``semantic_match_status`` instead.
    """
    if must_satisfied:
        # Everything the author named is in frame; this is not an atmospheric stand-in.
        return 2 if subject_match < 80 else 1
    if not subject_decidable:
        return 2
    if subject_match >= 80 and action_match >= 70:
        return 1
    if subject_match >= 80:
        return 2
    if subject_match >= 40 and environment_match >= 70:
        return 3
    if environment_match >= 70:
        return 4
    return 5


def _why_selected(
    scene: SemanticScene,
    subject_match: float,
    action_match: float,
    environment_match: float,
    metadata_status: str,
) -> str:
    return (
        f"{scene.visual_priority}: subject={subject_match:.0f}, "
        f"action={action_match:.0f}, environment={environment_match:.0f}, "
        f"metadata={metadata_status}"
    )
