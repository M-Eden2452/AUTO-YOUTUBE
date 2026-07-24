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


WHALE_NEGATIVES = ["desert", "mountain", "mountains", "canyon", "city", "road", "farm", "savanna"]
OCEAN_TERMS = ["ocean", "sea", "coast", "coastline", "coastal", "water", "underwater"]
CAMERA_TERMS = ["aerial", "drone", "underwater", "close"]
ACTION_TERMS = ["resting", "swimming", "rolling", "floating", "nursing", "migration", "observed", "monitoring"]


def analyze_scene(scene: dict[str, Any]) -> SemanticScene:
    explicit = scene.get("semantic") or {}
    text = " ".join(
        str(scene.get(key, ""))
        for key in ("primary_query", "visual_description", "visual_intent", "narration", "visual_type")
    ).lower()
    priority = str(scene.get("visual_priority") or explicit.get("visual_priority") or _infer_priority(text))
    subject = list(explicit.get("subject") or _infer_subject(text, priority))
    secondary = list(explicit.get("secondary_subjects") or _infer_secondary(text))
    action = list(explicit.get("action") or _infer_terms(text, ACTION_TERMS))
    environment = list(explicit.get("environment") or _infer_environment(text))
    location = list(explicit.get("location") or _infer_location(text))
    camera = list(explicit.get("camera") or _infer_terms(text, CAMERA_TERMS))
    mood = list(explicit.get("mood") or [])
    must_include = list(explicit.get("must_include") or _must_include(priority, subject, environment))
    should_include = list(explicit.get("should_include") or secondary + location + camera)
    must_not = list(explicit.get("must_not_include") or _infer_must_not(subject, environment))
    fallback_level = int(scene.get("fallback_level") or explicit.get("fallback_level") or _default_fallback_level(priority))
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
        visual_priority=priority,
        fallback_level=fallback_level,
    )


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
    if subject or _has_ocean(environment):
        return WHALE_NEGATIVES.copy()
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
