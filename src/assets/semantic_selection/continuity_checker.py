"""Cross-scene environment continuity, reported and never enforced.

Asks one question of each scene -- "what environment does the chosen asset
actually show?" -- and reports transitions that read as a mistake, such as
ocean -> desert -> ocean inside a single Short.

Two boundaries keep that report honest:

- **Evidence.** The environment is read through the canonical evidence owner
  ``evidence.build_evidence``: what the provider wrote about the asset, plus
  validated Vision tags. A ``search_query``, a ``source_url``, a source page or
  a file path records where material came from and why it was looked for, never
  what it depicts. Reading those made a scene searched for with the word
  "desert" come back as proof of a desert, so the system could confirm its own
  request.
- **Authority.** This module reports and decides nothing. Scene resolution is
  owned by the manifest builder's scene loop and completion by
  ``assets.completion``; a cross-scene keyword heuristic overrules neither.

The inference itself is deliberately small and unchanged: three English word
sets and one transition pattern.
"""

from __future__ import annotations

from typing import Any

from .evidence import build_evidence

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
    """What the chosen asset shows -- not what was asked of the provider."""
    asset = scene.get("selected_asset") or scene
    observed = set(build_evidence(asset).token_set)
    if observed & DESERT:
        return "desert"
    if observed & MOUNTAIN:
        return "mountain"
    if observed & OCEAN:
        return "ocean"
    return "unknown"
