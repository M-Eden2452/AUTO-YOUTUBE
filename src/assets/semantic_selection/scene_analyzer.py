from __future__ import annotations

from typing import Any

from .models import (
    SCENE_ABSTRACT_EXPLANATION,
    SCENE_ENVIRONMENT,
    SCENE_EXACT_ACTION,
    SCENE_EXACT_SUBJECT,
    SCENE_RESEARCH_CONTEXT,
    SCENE_TRANSITION,
    SemanticScene,
)


# Landscapes that contradict an *ocean* scene. Named for what they are: this list is
# only meaningful when the scene really is marine. It used to be applied to every
# scene that had any subject at all, which meant a video about crows silently
# refused footage of cities, roads and farms - the places crows actually live.
MARINE_CONTEXT_NEGATIVES = ["desert", "mountain", "mountains", "canyon", "city", "road", "farm", "savanna"]
OCEAN_TERMS = ["ocean", "sea", "coast", "coastline", "coastal", "water", "underwater"]
CAMERA_TERMS = ["aerial", "drone", "underwater", "close"]
ACTION_TERMS = ["resting", "swimming", "rolling", "floating", "nursing", "migration", "observed", "monitoring"]


def analyze_scene(scene: dict[str, Any]) -> SemanticScene:
    explicit = scene.get("semantic") or {}
    # The author's brief, when there is one. Read directly as well as through
    # ``semantic`` because a plan written by ``scene_to_legacy`` carries both, and a
    # hand-written fixture may carry only one of them.
    brief = scene.get("visual_brief") if isinstance(scene.get("visual_brief"), dict) else {}
    text = " ".join(
        str(scene.get(key, ""))
        for key in ("primary_query", "visual_description", "visual_intent", "narration", "visual_type")
    ).lower()
    priority = str(scene.get("visual_priority") or explicit.get("visual_priority") or _infer_priority(text))
    subject = _stated(explicit, "subject", _infer_subject(text, priority))
    secondary = _stated(explicit, "secondary_subjects", _infer_secondary(text))
    action = _stated(explicit, "action", _infer_terms(text, ACTION_TERMS))
    environment = _stated(explicit, "environment", _infer_environment(text))
    location = _stated(explicit, "location", _infer_location(text))
    camera = _stated(explicit, "camera", _infer_terms(text, CAMERA_TERMS))
    mood = _stated(explicit, "mood", [])
    must_include = _stated(explicit, "must_include", _must_include(priority, subject, environment))
    should_include = _stated(explicit, "should_include", secondary + location + camera)
    if "must_not_include" in explicit:
        must_not = _as_list(explicit.get("must_not_include"))
    elif "must_avoid" in brief:
        # ``visual_brief.must_avoid`` is the author's canonical wording. Older and
        # hand-written plans may not duplicate it into the semantic block, but that
        # must never make the prohibition disappear for candidate selection.
        must_not = _as_list(brief.get("must_avoid"))
    else:
        must_not = _infer_must_not(subject, environment)
    fallback_level = int(scene.get("fallback_level") or explicit.get("fallback_level") or _default_fallback_level(priority))
    # Nothing below is ever inferred. A context the author did not state constrains
    # nothing, and a contradiction nobody declared is not a contradiction.
    context = _as_list(explicit.get("context") or brief.get("context"))
    conflicting_context = _as_list(explicit.get("conflicting_context") or brief.get("conflicting_context"))
    source_class = str(
        explicit.get("source_class") or scene.get("source_class") or brief.get("source_class") or ""
    ).strip()
    # Same dual-read as everything else above: a plan written by ``scene_to_legacy``
    # may duplicate it into ``semantic``, a hand-written fixture may carry only the
    # brief's own field.
    shot_type = str(explicit.get("shot_type") or brief.get("shot_type") or "").strip()
    return SemanticScene(
        scene_id=str(scene.get("scene_id", "")),
        subject=subject,
        secondary_subjects=secondary,
        action=action,
        environment=environment,
        location=location,
        camera=camera,
        mood=mood,
        must_include=must_include,
        should_include=should_include,
        must_not_include=must_not,
        context=context,
        conflicting_context=conflicting_context,
        source_class=source_class,
        visual_priority=priority,
        fallback_level=fallback_level,
        shot_type=shot_type,
    )


def _stated(explicit: dict[str, Any], key: str, fallback: list[str]) -> list[str]:
    """An explicit plan answers for every key it carries - including with silence.

    ``explicit.get(key) or fallback`` cannot tell "the planner said nothing" from "the
    planner said there is nothing", and the difference decides whether this layer is
    allowed to guess. It matters most for ``must_include``: once the planner stopped
    promoting a Russian stem into a hard requirement, the same stem came straight back
    here, re-derived from the scene's own subject, and every candidate was refused for a
    requirement no author ever wrote.

    A scene with no ``semantic`` block at all is untouched - the keyword inference below
    still serves hand-written fixtures and plans written before the planner existed.
    """
    if key in explicit:
        return _as_list(explicit.get(key))
    return [str(item) for item in fallback]


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _infer_priority(text: str) -> str:
    if "transition" in text:
        return SCENE_TRANSITION
    if any(term in text for term in ("researcher", "researchers", "biologist", "scientist", "drone observation")):
        return SCENE_RESEARCH_CONTEXT
    if any(term in text for term in ACTION_TERMS):
        return SCENE_EXACT_ACTION
    if any(term in text for term in ("coast", "ocean", "sea")):
        return SCENE_EXACT_SUBJECT if "whale" in text else SCENE_ENVIRONMENT
    return SCENE_ABSTRACT_EXPLANATION


def _infer_subject(text: str, priority: str) -> list[str]:
    if "southern right whale" in text:
        return ["southern right whale"]
    if "right whale" in text:
        return ["right whale"]
    if "whale" in text:
        return ["whale"]
    if priority in {SCENE_ENVIRONMENT, SCENE_TRANSITION, SCENE_RESEARCH_CONTEXT}:
        return []
    return []


def _infer_secondary(text: str) -> list[str]:
    values = []
    if "mother" in text and "calf" in text:
        values.append("mother and calf")
    elif "calf" in text:
        values.append("calf")
    return values


def _infer_environment(text: str) -> list[str]:
    terms = _infer_terms(text, OCEAN_TERMS)
    if any(term in terms for term in ("coast", "coastline", "coastal")) and "coastal waters" not in terms:
        terms.append("coastal waters")
    return terms


def _infer_location(text: str) -> list[str]:
    locations = []
    if "australia" in text or "australian" in text:
        locations.append("Australia")
    return locations


def _infer_terms(text: str, vocabulary: list[str]) -> list[str]:
    return [term for term in vocabulary if term in text]


def _must_include(priority: str, subject: list[str], environment: list[str]) -> list[str]:
    if priority in {SCENE_ENVIRONMENT, SCENE_TRANSITION, SCENE_RESEARCH_CONTEXT}:
        return ["ocean"] if _has_ocean(environment) else []
    values: list[str] = []
    if subject:
        values.append(_subject_token(subject[0]))
    if _has_ocean(environment):
        values.append("ocean")
    return values


def _infer_must_not(subject: list[str], environment: list[str]) -> list[str]:
    """Landscape negatives, and only for a scene that is actually set at sea.

    Inferring negatives from the mere presence of a subject cannot be right: what
    contradicts a frame depends on what the frame is of, and that is knowledge this
    keyword layer does not have. A planner that does know supplies ``must_not_include``
    explicitly (``src.content.visual_planning``), and an explicit value always wins.
    """
    if _has_ocean(environment):
        return MARINE_CONTEXT_NEGATIVES.copy()
    return []


def _has_ocean(environment: list[str]) -> bool:
    return any(term in OCEAN_TERMS for term in environment)


def _subject_token(subject: str) -> str:
    if "whale" in subject:
        return "whale"
    return subject


def _default_fallback_level(priority: str) -> int:
    if priority in {SCENE_ENVIRONMENT, SCENE_TRANSITION}:
        return 4
    if priority == SCENE_RESEARCH_CONTEXT:
        return 3
    return 1
