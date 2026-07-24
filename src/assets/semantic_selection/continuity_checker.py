from __future__ import annotations

import re
from typing import Any


OCEAN = {"ocean", "sea", "water", "coast", "coastline", "whale", "underwater"}
DESERT = {"desert", "canyon", "savanna", "road"}
MOUNTAIN = {"mountain", "mountains", "valley"}


def check_continuity(scene_entries: list[dict[str, Any]]) -> dict[str, Any]:
    environments = [_environment_for_scene(scene) for scene in scene_entries]
    issues: list[dict[str, Any]] = []
    for index in range(1, len(environments) - 1):
        prev_env = environments[index - 1]
        current_env = environments[index]
        next_env = environments[index + 1]
        if prev_env == "ocean" and current_env in {"desert", "mountain"} and next_env == "ocean":
            issues.append(
                {
                    "scene_id": scene_entries[index].get("scene_id", ""),
                    "reason": f"illogical_ocean_{current_env}_ocean_transition",
                }
            )
    score = max(0, 100 - 40 * len(issues))
    return {
        "status": "passed" if score >= 70 else "failed",
        "continuity_score": score,
        "issues": issues,
        "environments": environments,
    }


def _environment_for_scene(scene: dict[str, Any]) -> str:
    asset = scene.get("selected_asset") or scene
    text = " ".join(str(asset.get(key, "")) for key in ("title", "description", "source_url", "source_page", "keywords", "search_query")).lower()
    tokens = set(re.findall(r"[a-z0-9]+", text))
    if tokens & DESERT:
        return "desert"
    if tokens & MOUNTAIN:
        return "mountain"
    if tokens & OCEAN:
        return "ocean"
    return "unknown"
