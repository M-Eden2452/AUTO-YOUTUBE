from __future__ import annotations

from typing import Any


DEFAULT_PROVIDER_ORDER = [
    "local_library",
    "pexels",
    "pixabay",
    "wikimedia",
    "nasa_images",
    "internet_archive",
    "envato_manual",
]


def route_providers(
    scene: dict[str, Any],
    *,
    provider_names: list[str] | None = None,
    provider_enabled: dict[str, bool] | None = None,
    policy_eligible: dict[str, bool] | None = None,
    capabilities: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    names = list(provider_names or DEFAULT_PROVIDER_ORDER)
    enabled = provider_enabled or {}
    eligible = policy_eligible or {}
    caps = capabilities or {}
    text = _scene_text(scene)
    media_type = _scene_media_type(scene)
    scored: list[tuple[int, int, str]] = []
    reasons: dict[str, list[str]] = {}
    skipped: dict[str, str] = {}

    for original_index, provider in enumerate(names):
        if enabled.get(provider, True) is False:
            skipped[provider] = "disabled"
            continue
        if eligible.get(provider, True) is False:
            skipped[provider] = "policy_blocked"
            continue
        provider_caps = caps.get(provider, {})
        if provider_caps and media_type not in provider_caps.get("media_types", [media_type]):
            skipped[provider] = "unsupported_media_type"
            continue
        score, provider_reasons = _score_provider(provider, text, media_type)
        reasons[provider] = provider_reasons
        scored.append((score, -original_index, provider))

    scored.sort(reverse=True)
    automatic = [provider for _score, _index, provider in scored if provider != "envato_manual"]
    fallback = [provider for _score, _index, provider in scored]
    if "envato_manual" in fallback:
        fallback = [provider for provider in fallback if provider != "envato_manual"] + ["envato_manual"]
    ordered = automatic + (["envato_manual"] if "envato_manual" in fallback else [])
    return {
        "scene_id": scene.get("scene_id", ""),
        "media_type": media_type,
        "ordered_providers": ordered,
        "reasons": reasons,
        "skipped_providers": skipped,
        "fallback_order": fallback,
    }


def _score_provider(provider: str, text: str, media_type: str) -> tuple[int, list[str]]:
    reasons: list[str] = []
    score = 10
    if provider == "local_library":
        return 100, ["local_policy_safe_first"]
    if provider == "envato_manual":
        return -100, ["manual_fallback_only"]
    if provider in {"pexels", "pixabay"}:
        if _has_any(text, GENERIC_STOCK_TERMS):
            score += 55
            reasons.append("generic_cinematic_broll")
        if _has_any(text, NATURE_TERMS):
            score += 30
            reasons.append("nature_animals_cities_people_common_tech")
        return score, reasons or ["general_stock_fallback"]
    if provider == "wikimedia":
        if _has_any(text, WIKIMEDIA_TERMS):
            score += 70
            reasons.append("specific_or_rare_subject")
        if _has_any(text, HISTORICAL_TERMS):
            score += 45
            reasons.append("historical_or_named_subject")
        if media_type == "image" and _has_any(text, {"map", "diagram", "chart", "illustration"}):
            score += 35
            reasons.append("maps_diagrams_reference")
        return score, reasons or ["reference_source_fallback"]
    if provider == "nasa_images":
        if _has_any(text, NASA_TERMS):
            score += 85
            reasons.append("space_or_earth_observation")
        return score, reasons or ["nasa_topic_fallback"]
    if provider == "internet_archive":
        if _has_any(text, HISTORICAL_TERMS | ARCHIVE_TERMS):
            score += 80
            reasons.append("historical_or_archival")
        if media_type == "video":
            score += 10
        return score, reasons or ["archive_fallback"]
    return score, ["default_order"]


def _scene_text(scene: dict[str, Any]) -> str:
    semantic = scene.get("semantic") if isinstance(scene.get("semantic"), dict) else {}
    pieces = [
        scene.get("primary_query", ""),
        scene.get("visual_description", ""),
        scene.get("visual_intent", ""),
        scene.get("narration", ""),
        scene.get("location", ""),
        " ".join(str(item) for item in scene.get("keywords", []) or []),
        " ".join(str(item) for item in semantic.get("subject", []) or []),
        " ".join(str(item) for item in semantic.get("action", []) or []),
        " ".join(str(item) for item in semantic.get("environment", []) or []),
        " ".join(str(item) for item in semantic.get("location", []) or []),
    ]
    return " ".join(str(piece) for piece in pieces).lower()


def _scene_media_type(scene: dict[str, Any]) -> str:
    visual_type = str(scene.get("visual_type") or "").lower()
    return "image" if visual_type in {"image", "animated_image", "diagram"} else "video"


def _has_any(text: str, terms: set[str]) -> bool:
    return any(term in text for term in terms)


GENERIC_STOCK_TERMS = {
    "cinematic",
    "b-roll",
    "broll",
    "generic",
    "city",
    "people",
    "technology",
    "energy infrastructure",
    "renewable",
    "forest",
    "river",
    "nature",
}
NATURE_TERMS = {"animal", "animals", "nature", "forest", "river", "ocean", "city", "people", "solar", "wind", "factory"}
WIKIMEDIA_TERMS = {
    "specific",
    "rare",
    "named",
    "location",
    "map",
    "diagram",
    "scientific equipment",
    "rare species",
    "exact",
    "observatory",
    "infrastructure",
}
NASA_TERMS = {
    "space",
    "nasa",
    "earth observation",
    "satellite",
    "hurricane",
    "storm",
    "atmosphere",
    "climate",
    "ocean data",
    "glacier",
    "aviation",
    "mars",
    "moon",
}
HISTORICAL_TERMS = {"historical", "history", "archive", "archival", "old", "1930", "1940", "1950", "public domain"}
ARCHIVE_TERMS = {"footage", "film", "educational film", "record", "prelinger", "newsreel"}
