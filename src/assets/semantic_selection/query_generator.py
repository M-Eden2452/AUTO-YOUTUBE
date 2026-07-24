from __future__ import annotations

from .models import SemanticScene


def generate_queries(scene: SemanticScene) -> dict[str, str]:
    subject = " ".join(scene.subject[:1])
    secondary = " ".join(scene.secondary_subjects[:1])
    action = " ".join(scene.action[:1])
    environment = " ".join(scene.environment[:2])
    camera = " ".join(scene.camera[:1])
    location = " ".join(scene.location[:1])
    exact_parts = [subject, secondary, action, location, environment, camera]
    broad_parts = [subject or _animal_category(scene), secondary, environment, camera]
    fallback_parts = [location, environment, camera]
    atmospheric_parts = [environment, "nature", camera]
    return {
        "exact": _clean_query(exact_parts),
        "broad": _clean_query(broad_parts),
        "environment_fallback": _clean_query(fallback_parts),
        "atmospheric_fallback": _clean_query(atmospheric_parts),
    }


def ordered_queries(scene: SemanticScene) -> list[dict[str, str | int]]:
    queries = generate_queries(scene)
    levels = [
        ("exact", 1),
        ("broad", 2),
        ("environment_fallback", 4),
        ("atmospheric_fallback", 4),
    ]
    return [
        {"kind": kind, "fallback_level": level, "query": query}
        for kind, level in levels
        if (query := queries.get(kind, ""))
    ]


def _animal_category(scene: SemanticScene) -> str:
    if any("whale" in subject for subject in scene.subject):
        return "whale"
    return ""


def _clean_query(parts: list[str]) -> str:
    seen: set[str] = set()
    words: list[str] = []
    for part in parts:
        for word in str(part).split():
            normalized = word.lower()
            if normalized and normalized not in seen:
                seen.add(normalized)
                words.append(word)
    return " ".join(words)
