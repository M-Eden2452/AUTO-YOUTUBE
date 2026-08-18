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

Stage Q2.2A-2 added the part these scores could not express: *which* of the scene's
requirements were met. The slot verdict and the support status live in
``src.assets.semantic_selection.decision`` and are attached to every ranked candidate
as one record, so that nothing between here and the manifest has to reconstruct them.
"""

from __future__ import annotations

import re
from typing import Any

from .decision import (
    DECISION_KEY,
    EXACTING_CLASSES,
    FRAMING_HARD_REJECT,
    SUPPORT_FULL,
    SUPPORT_MANUAL,
    SUPPORT_PARTIAL,
    SUPPORT_RIGHTS_BLOCKED,
    SUPPORT_UNSUPPORTED,
    SUPPORT_UNVERIFIED,
    SelectionDecision,
    build_slot_verdict,
    framing_decision,
    support_status,
)
from .evidence import (
    CandidateEvidence,
    build_evidence,
    contains_concept,
)
from .models import (
    SCENE_ENVIRONMENT,
    SCENE_EXACT_SUBJECT,
    SCENE_TRANSITION,
    SemanticScene,
)

MIN_SCORE = 60.0
EXACT_SUBJECT_MIN_SCORE = 75.0
NON_REAL_VIDEO_TERMS = (
    "animation",
    "animated",
    "cartoon",
    "disney",
    "little einsteins",
    "gameplay",
)

# The averaged relevance score is the oldest gate in this file and the one least able
# to say what it objects to. Once the slot layer has judged the candidate against every
# requirement the scene states and found the scene *partly* supported, that average may
# no longer overrule it: the retest dropped three clips whose only fault was a number
# (a close-up of plastic bottles answering a scene about plastic, `score_below_60`)
# while the slot record for the same clip read "requirement:plastic matched, subject and
# context missing" - which is not a refusal, it is a description of what still has to be
# found. Such a candidate is now kept and carried into the project as partial support,
# never as render-ready.
#
# Only the score thresholds are softened. Everything the slot layer itself refuses -
# a missing required slot, a declared conflict, a must_avoid hit, unverifiable evidence,
# an unusable crop, blocked rights - stays a refusal, because those are the checks this
# stage exists to make.
SOFT_REJECT_PREFIXES: tuple[str, ...] = ("score_below_",)

# Which support statuses may keep a candidate despite a soft objection. A candidate the
# slot layer could not verify at all is not rescued by lowering a threshold.
SOFT_REJECT_ELIGIBLE = frozenset({SUPPORT_FULL, SUPPORT_PARTIAL})

# How good an answer each status is, when several candidates survive. Selection used to
# be "first one that was not rejected, by score"; with partial support now selectable, a
# fully supported candidate must not lose to a partial one that happens to score higher.
SUPPORT_RANK: dict[str, int] = {
    SUPPORT_FULL: 5,
    SUPPORT_PARTIAL: 4,
    SUPPORT_MANUAL: 3,
    SUPPORT_RIGHTS_BLOCKED: 2,
    SUPPORT_UNVERIFIED: 1,
    SUPPORT_UNSUPPORTED: 0,
}

# Fraction of a scene a clip may fall short by and still be usable by slowing it down
# or holding the last frame. Beyond this the scene is left unresolved instead.
DURATION_TOLERANCE_SEC = 0.35

# A vertical short is 1080x1920. A landscape frame cropped to 9:16 keeps only its
# middle strip, and the question is how far that strip has to be stretched to fill the
# frame. 540px is a 2x upscale - soft but usable for b-roll; below that the picture is
# gone. 1280x720 crops to 405px (2.7x) and is refused; 1920x1080 crops to 607px and is
# not. The retest accepted a 405px strip because nothing checked the crop at all - only
# the aspect *deviation*, which is a score and not a gate.
TARGET_ASPECT_RATIO = "9:16"
MIN_SHORT_EDGE_PX = 540

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

# Shot-scale vocabulary a provider's own title or description sometimes states
# outright (C99). Read the same way ``_watermark_penalty`` reads ``tokens``/``text``
# below - a small closed list, never inferred from what the scene asked for, and
# silent whenever neither list appears: a record that says nothing about framing is
# not evidence against it.
WIDE_SHOT_TERMS = (
    "wide shot", "wide angle", "establishing shot", "aerial", "aerial view",
    "aerial shot", "drone shot", "bird's eye", "panoramic", "panorama", "long shot",
)
CLOSE_SHOT_TERMS = (
    "close-up", "close up", "closeup", "extreme close-up", "macro", "macro shot",
)
SHOT_SCALE_WIDE = "wide"
SHOT_SCALE_CLOSE = "close"

# What each dramaturgical shot type (src.content.visual_planning.models.SHOT_TYPES -
# "what the frame has to do dramatically", per that module's own definition) implies
# about scale, when it implies anything at all. Only the two pairs where the
# definition itself is close to unambiguous are mapped: an establishing or context
# shot is conventionally wide almost by definition, and a detail shot is close almost
# by definition. ``payoff`` was tried and measured out: on the frozen v2 corpus it
# predicted the owner's pick correctly in ``local_after_fix/scene_005`` (a close-up
# was preferred) and *wrongly* in ``live_5/scene_005`` (an aerial/wide shot was
# preferred for another payoff scene about the same subject) - one win, one loss on
# the only two "payoff" scenes measurable, which is exactly "not reliably
# distinguishable by this signal" rather than a rule. ``action`` and ``evidence`` were
# never mapped for the same reason, stated in advance rather than found by measuring:
# guessing a scale for them would be the "fix it with weights, blindly" the C99
# registry row forbids.
SHOT_TYPE_SCALE_INTENT: dict[str, str] = {
    "establishing": SHOT_SCALE_WIDE,
    "context": SHOT_SCALE_WIDE,
    "detail": SHOT_SCALE_CLOSE,
}

# A should, not a must: small enough that a scene's actual subject and action always
# still decide the winner first (0.85 weight on ``meaning_score`` alone spans 0-85
# points), large enough to break the kind of near-tie C99 measured (two candidates a
# point or two apart in meaning, or perfectly tied). Applied to ``final_score``
# directly rather than folded into ``meaning_score``, so ``semantic_score`` keeps
# reporting meaning alone and this signal cannot be mistaken for a bigger claim about
# subject match than it is.
SHOT_SCALE_ADJUSTMENT = 8.0


def rank_candidates(
    scene: SemanticScene,
    candidates: list[dict[str, Any]],
    *,
    used_asset_ids: set[str] | None = None,
    required_duration_sec: float = 0.0,
    require_provider_metadata: bool = False,
    target_aspect_ratio: str = TARGET_ASPECT_RATIO,
    min_short_edge: int = MIN_SHORT_EDGE_PX,
    source_class: str = "",
) -> list[dict[str, Any]]:
    used = used_asset_ids or set()
    ranked = [
        _score_candidate(
            scene,
            candidate,
            used,
            required_duration_sec=required_duration_sec,
            require_provider_metadata=require_provider_metadata,
            target_aspect_ratio=target_aspect_ratio,
            min_short_edge=min_short_edge,
            source_class=source_class or scene.source_class,
        )
        for candidate in candidates
    ]
    return sorted(ranked, key=_ranking_key, reverse=True)


def _ranking_key(item: dict[str, Any]) -> tuple[int, int, float]:
    """Best answer first: usable before refused, better supported before higher scoring.

    The support rank sits above the score on purpose. Since a partially supported
    candidate can now be selected, ordering by score alone could hand a scene to a
    partial match while a fully supported one waited two places below it.
    """
    return (
        0 if item.get("rejected", False) else 1,
        SUPPORT_RANK.get(str(item.get("support_status") or ""), 0),
        float(item.get("final_score") or 0.0),
    )


def select_best_candidate(
    scene: SemanticScene,
    candidates: list[dict[str, Any]],
    *,
    used_asset_ids: set[str] | None = None,
    required_duration_sec: float = 0.0,
    require_provider_metadata: bool = False,
    target_aspect_ratio: str = TARGET_ASPECT_RATIO,
    min_short_edge: int = MIN_SHORT_EDGE_PX,
    source_class: str = "",
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    ranked = rank_candidates(
        scene,
        candidates,
        used_asset_ids=used_asset_ids,
        required_duration_sec=required_duration_sec,
        require_provider_metadata=require_provider_metadata,
        target_aspect_ratio=target_aspect_ratio,
        min_short_edge=min_short_edge,
        source_class=source_class,
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
    target_aspect_ratio: str = TARGET_ASPECT_RATIO,
    min_short_edge: int = MIN_SHORT_EDGE_PX,
    source_class: str = "",
) -> dict[str, Any]:
    evidence = build_evidence(candidate)
    text = evidence.text
    vision_tags = list(evidence.vision_tags)
    all_tokens = set(evidence.token_set)
    metadata_status, metadata_score = evidence.metadata_status, evidence.metadata_score
    has_evidence = evidence.has_metadata

    subject_match, subject_decidable = _field_match(scene.subject, evidence, aliases={"southern right whale": ["southern right whale", "right whale", "whale"]})
    action_match, action_decidable = _field_match(scene.action, evidence)
    environment_match, environment_decidable = _field_match(scene.environment, evidence, aliases={"coastal waters": ["coast", "coastline", "coastal", "ocean", "sea"]})
    location_match, _ = _field_match(scene.location, evidence)
    camera_match, camera_decidable = _field_match(scene.camera, evidence)
    quality_score = _normal_score(candidate.get("quality_score"), _quality_score(candidate))
    vertical_score = _normal_score(candidate.get("vertical_score"), _vertical_score(candidate))
    technical_score = round(0.5 * quality_score + 0.5 * vertical_score, 3)
    provider_confidence = PROVIDER_CONFIDENCE.get(str(candidate.get("provider") or ""), 0.5)

    negative_matches = [word for word in scene.must_not_include if _contains_concept(word, all_tokens, text)]
    media_type = str(candidate.get("media_type") or candidate.get("type") or "").casefold()
    # Commons can categorize an exact orca clip under "People with dolphins" because
    # Orcinus orca belongs to the dolphin family. That broader taxonomy must not
    # overrule a title/description that explicitly identifies the animal as an orca.
    # A primary description that actually says "dolphin" remains disqualifying.
    primary_text = " ".join(
        str(candidate.get(field) or "") for field in ("title", "description")
    ).casefold()
    exact_orca_scene = any(
        "orca" in str(subject).casefold() or "killer whale" in str(subject).casefold()
        for subject in scene.subject
    )
    exact_orca_evidence = bool(
        re.search(r"\b(?:orcas?|killer\s+whales?|orcinus\s+orca)\b", text)
    )
    primary_mentions_dolphin = bool(re.search(r"\bdolphins?\b", primary_text))
    missing_orca_evidence_for_orca_video = bool(
        exact_orca_scene
        and media_type == "video"
        and not exact_orca_evidence
    )
    ambiguous_whale_for_orca = bool(
        missing_orca_evidence_for_orca_video
        and re.search(r"\bwhales?\b", primary_text)
    )
    if exact_orca_scene and exact_orca_evidence and not primary_mentions_dolphin:
        negative_matches = [
            word for word in negative_matches if str(word).strip().casefold() != "dolphin"
        ]
    non_real_video_matches = (
        [
            term
            for term in NON_REAL_VIDEO_TERMS
            if _contains_concept(term, all_tokens, text)
        ]
        if media_type == "video"
        else []
    )
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
    # A field the scene never constrained scores 100 as "not applicable" (``_field_match``
    # returns it for an empty list). That is a statement about the scene, not evidence
    # about the asset, and it must not be able to *become* the score. Dropping every
    # undecidable field can leave nothing else in the average: when the scene did state
    # requirements and not one of them could be judged, the weighted mean is taken over
    # the fields nobody asked about and reports a perfect match.
    #
    # Reproduced on the 2026-08-14 local repeat: a Russian scene about the rainforest
    # canopy stated ``subject`` and ``action`` and left ``environment``/``camera`` empty.
    # Against English-only metadata both stated fields were undecidable, so a clip of
    # browser tabs on a desk scored 100 while a checkable candidate honestly scored 23.5.
    # The incentive was inverted - metadata too poor to contradict the scene won - which
    # penalised exactly the bilingual records the library curation had just produced.
    stated_decidability = [
        decidable
        for terms, decidable in (
            (scene.subject, subject_decidable),
            (scene.action, action_decidable),
            (scene.environment, environment_decidable),
            (scene.camera, camera_decidable),
        )
        if terms
    ]
    if stated_decidability and not any(stated_decidability):
        # Nothing the scene asked about could be compared: absence of evidence, which the
        # rest of this function already represents as 0.0.
        meaning_score = 0.0
    elif decidable_weight > 0:
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
    # Outside ``meaning_score`` on purpose (C99): a should about which frame reads
    # better, not a claim about whether the subject is even present. Keeping it out of
    # the weighted average means ``semantic_score`` keeps reporting meaning alone, and
    # a scene with no ``shot_type`` or a candidate whose text names no scale gets
    # exactly 0.0 - additive by construction, not just by measurement.
    shot_scale_observed, shot_scale_intent, shot_scale_adjustment = _shot_scale_signal(
        scene.shot_type, text
    )
    final_score = (
        0.85 * meaning_score
        + 0.075 * quality_score
        + 0.075 * vertical_score
        - contradiction_penalty
        - duplicate_penalty
        - watermark_penalty
        + shot_scale_adjustment
    )
    must_missing: list[str] = []
    must_undecidable: list[str] = []
    for item in scene.must_include:
        # Asked of the evidence rather than of the glued text, so this loop answers the
        # same question as the slot layer and the score. It used to call the primitive
        # on ``text`` directly, which is why repairing ``is_undecidable`` alone left the
        # rejection standing: the requirement slot flipped to matched while the record
        # stayed refused as ``semantic_unverified`` for a term its title states word for
        # word. ``has_evidence`` stays the caller's own condition - a record with no
        # metadata is refused two branches below and reports its status there, and
        # listing every requirement as undecidable would replace that status with a term
        # list that says nothing new.
        if has_evidence and evidence.is_undecidable(item):
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
    framing_check = framing_decision(
        candidate, target_aspect_ratio=target_aspect_ratio, min_short_edge=min_short_edge
    )
    # Every requirement the scene states, judged one at a time. This is what the score
    # above cannot say: it averages, and an average cannot tell "the station is not in
    # the frame" from "the wording is a little off".
    slot_verdict = build_slot_verdict(scene, evidence, source_class=source_class)

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
    if non_real_video_matches:
        reject_reasons.append(
            "non_real_video_footage:" + ",".join(non_real_video_matches)
        )
    if ambiguous_whale_for_orca:
        reject_reasons.append("ambiguous_whale_for_orca_scene")
    elif missing_orca_evidence_for_orca_video:
        reject_reasons.append("missing_orca_evidence_for_orca_scene")
    if set(vision_tags) & set(scene.must_not_include):
        reject_reasons.append("vision_mismatch")
    # A candidate may only be chosen automatically once the scene's *requirements* have
    # actually been checked against it. Two things make that impossible: the provider
    # said nothing about the asset at all, or a required term is written in a script its
    # metadata cannot contain. Either way there is no evidence the requirement is met,
    # and selecting anyway is how a photograph of Mars answered a scene stating a
    # percentage - it was chosen while its own record said the requirement was
    # unverifiable.
    #
    # An incidental field that could not be checked (an auto-extracted verb, a camera
    # move a stock library never labels) is reported in ``semantic_match_status`` but is
    # not disqualifying: refusing a candidate whose stated requirements are all met,
    # because a word nobody asked for could not be compared, rejects good material for
    # a fact that was never required.
    if not has_evidence or must_undecidable:
        detail = ",".join(must_undecidable) or metadata_status
        reject_reasons.append(f"semantic_unverified:{detail}")
    elif require_provider_metadata and semantic_match_status != "matched":
        reject_reasons.append(f"no_semantic_evidence:{metadata_status}")
    if framing_check["status"] in FRAMING_HARD_REJECT:
        reject_reasons.append(
            f"framing_unusable:{framing_check['status']}:"
            f"{framing_check['effective_width']}x{framing_check['effective_height']}"
        )
    # A class whose whole point is a specific real thing may not be answered by a
    # candidate that shows only part of it. This is the iceberg: the scene asked for a
    # research station in Antarctica with airborne transport, the clip shared exactly
    # one word with it, and the average score was comfortably above the threshold.
    if source_class in EXACTING_CLASSES and slot_verdict.absent_required_slots:
        reject_reasons.append("required_slot_missing:" + ",".join(slot_verdict.absent_required_slots))
    # Something the author declared to be a contradiction is in the metadata verbatim.
    # Not a permanent refusal like ``must_avoid`` - a person may still confirm it - but
    # never an automatic full match.
    if slot_verdict.declared_conflict_terms:
        reject_reasons.append("conflicting_context:" + ",".join(dict.fromkeys(slot_verdict.declared_conflict_terms)))
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

    review_required = bool(candidate.get("review_required", False))
    support, requirements = support_status(
        slot_verdict,
        framing_status=framing_check["status"],
        rights_allowed=allowed,
        rights_review_required=review_required,
        source_class=source_class,
        provider=str(candidate.get("provider") or ""),
        semantically_disqualified=(
            bool(negative_matches)
            or bool(non_real_video_matches)
            or semantic_match_status == "mismatched"
        ),
    )
    # An objection that the slot verdict has already answered stops being a refusal and
    # becomes advisory. Both lists are kept: a reviewer must still see that the average
    # was low, and ``reject_reasons`` on the stored decision stays complete.
    advisory_reasons = [
        reason
        for reason in reject_reasons
        if reason.startswith(SOFT_REJECT_PREFIXES) and support in SOFT_REJECT_ELIGIBLE
    ]
    blocking_reasons = [reason for reason in reject_reasons if reason not in advisory_reasons]

    decision = SelectionDecision(
        scene_id=scene.scene_id,
        asset_id=str(candidate.get("asset_id") or ""),
        provider=str(candidate.get("provider") or ""),
        source_class=source_class,
        provider_confidence=provider_confidence,
        semantic_score=semantic_score,
        semantic_status=semantic_match_status,
        metadata_score=metadata_score,
        metadata_status=metadata_status,
        technical_score=technical_score,
        technical_status=str(framing_check["status"]),
        framing=framing_check,
        duration_status=str(duration_check["status"]),
        duration={key: value for key, value in duration_check.items() if key != "status"},
        rights_status=str(candidate.get("rights_status") or ""),
        rights_allowed_for_render=allowed,
        rights_review_required=review_required,
        slots=slot_verdict.to_dict(),
        slot_verdict=slot_verdict.verdict,
        support_status=support,
        support_requirements=requirements,
        selection_reasons=_selection_reasons(scene, slot_verdict, must_satisfied, metadata_status),
        reject_reasons=list(reject_reasons),
    )

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
        "framing_check": framing_check,
        "framing_status": framing_check["status"],
        "semantic_evidence": has_evidence,
        "semantic_match_status": semantic_match_status,
        "undecidable_fields": undecidable_fields,
        "must_include_unverifiable": must_undecidable,
        "negative_matches": negative_matches,
        "contradiction_penalty": contradiction_penalty,
        "duplicate_penalty": duplicate_penalty,
        "watermark_penalty": watermark_penalty,
        "shot_scale_intent": shot_scale_intent,
        "shot_scale_observed": shot_scale_observed,
        "shot_scale_adjustment": shot_scale_adjustment,
        "fallback_level": fallback_level,
        "scene_match_score": round(max(0.0, min(100.0, final_score)), 3),
        "final_score": round(final_score, 3),
        "rejected": bool(blocking_reasons),
        # The full list, unchanged: existing readers assert on these strings, and a
        # reviewer is entitled to every objection raised, not only the fatal ones.
        "reject_reason": ";".join(reject_reasons),
        "blocking_reject_reasons": blocking_reasons,
        "advisory_reject_reasons": advisory_reasons,
        "why_selected": _why_selected(scene, subject_match, action_match, environment_match, metadata_status),
        "semantic_scene": scene.to_dict(),
        "vision_tags": candidate.get("vision_tags", []),
        # The headline of the record, flat, so a manifest or a board can read the
        # verdict without unpacking the whole decision.
        "slot_verdict": slot_verdict.verdict,
        "support_status": support,
        "support_requirements": requirements,
        # The record itself. One key, one owner - see decision.carry_decision for why
        # it has to survive the download step.
        DECISION_KEY: decision.to_dict(),
    }
    return result


def _selection_reasons(
    scene: SemanticScene, slot_verdict: Any, must_satisfied: bool, metadata_status: str
) -> list[str]:
    """Why this candidate is where it is, in codes a manifest can be filtered on."""
    reasons = [f"slot_verdict:{slot_verdict.verdict}", f"metadata:{metadata_status}"]
    if scene.source_class:
        reasons.append(f"source_class:{scene.source_class}")
    if must_satisfied:
        reasons.append("author_requirements_satisfied")
    for name in slot_verdict.matched_slots:
        reasons.append(f"matched:{name}")
    for name in slot_verdict.missing_slots:
        reasons.append(f"missing:{name}")
    for name in slot_verdict.undecidable_slots:
        reasons.append(f"undecidable:{name}")
    return reasons


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


def _field_match(
    values: list[str], evidence: CandidateEvidence, aliases: dict[str, list[str]] | None = None
) -> tuple[float, bool]:
    """Return ``(score, decidable)``.

    ``decidable`` is False when the field's terms are written in a script the evidence
    text cannot contain - an English title simply cannot confirm or deny a Russian
    subject, and pretending it denies it is what made every candidate score 0 once the
    query stopped being counted as evidence.

    The score is ``semantic_inflection_score``: literal, plus a word the stemmer confirms
    is the same word in another ending. It is deliberately *not* the slot layer's
    ``semantic_stem_score``, which also credits a shared prefix. This function's result is
    summed into a weighted average and compared between candidates, and a prefix
    allowance that is harmless as a yes/no answer becomes an argument once it is scored:
    ``powered`` would count as evidence of a ``power plant``. The asymmetry is named in
    ``evidence``'s module docstring, which owns both relations.
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
        if any(not evidence.is_undecidable(term) for term in terms):
            decidable = True
        scores.append(max(evidence.semantic_inflection_score(term) for term in terms))
    return sum(scores) / len(scores), decidable


# The matching primitives live in ``evidence`` so that the slot layer asks the same
# questions of the same text. This alias keeps the wording of this file intact.
# ``_script_mismatch`` stood here until the ``must_include`` loop stopped asking the
# glued text; it is removed with its last caller rather than left behind as a second
# way to ask a question the evidence now answers.
_contains_concept = contains_concept


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


def _shot_scale_signal(shot_type: str, text: str) -> tuple[str, str, float]:
    """(observed_scale, intent, adjustment) for the scene's declared shot type.

    Returns ``("", intent, 0.0)`` whenever the candidate's own text names no shot
    scale at all - most provider records say nothing about framing, and silence is
    not evidence of a mismatch. Returns ``("ambiguous", intent, 0.0)`` when a record
    names both a wide and a close phrase (a compilation description, typically) - two
    contradicting claims are not evidence either way. ``intent`` is reported even when
    it is empty, so a caller can tell "no preference for this shot_type" apart from
    "no evidence in this text".
    """
    intent = SHOT_TYPE_SCALE_INTENT.get(str(shot_type or "").strip().casefold(), "")
    if not intent:
        return "", intent, 0.0
    observed_wide = any(term in text for term in WIDE_SHOT_TERMS)
    observed_close = any(term in text for term in CLOSE_SHOT_TERMS)
    if observed_wide == observed_close:
        # Both true (contradicting claims) or both false (no evidence) - neither
        # supports an adjustment.
        return ("ambiguous" if observed_wide else "", intent, 0.0)
    observed = SHOT_SCALE_WIDE if observed_wide else SHOT_SCALE_CLOSE
    adjustment = SHOT_SCALE_ADJUSTMENT if observed == intent else -SHOT_SCALE_ADJUSTMENT
    return observed, intent, adjustment


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
