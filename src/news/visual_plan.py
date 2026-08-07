"""Adapter between the news_to_short pipeline and the shared visual planning layer.

This module used to *be* the planner: a four-branch ``if`` that returned one of four
fixed English strings ("whale mother calf aerial ocean", "scientific researchers
nature field observation", "ocean wildlife aerial waves", "nature science wildlife
observation") for every video ever made, and a ``visual_type`` that alternated on
``index % 3``.

``build_visual_plan(script, language=..., user_assets=...)`` keeps its exact
signature and still returns the ``visual_plan.json`` dict the rest of the pipeline
reads, so ``asset_manager``, ``final_renderer`` and ``visual_preview`` did not
have to change.
"""

from __future__ import annotations

from typing import Any

from src.content.script_engine import from_legacy_script
from src.content.visual_planning import VisualPlanRequest, build_plan

__all__ = ["build_visual_plan", "build_visual_plan_result"]


def build_visual_plan(
    script: dict[str, Any],
    *,
    language: str,
    user_assets: list[str] | None = None,
    research: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """The visual_plan.json payload for this script. Signature unchanged since Stage AB.

    ``research`` is optional and additive: claims sharpen which entity the video is
    actually about, but the plan is built from the script alone when they are absent
    (which is the case for every caller written before this stage).
    """
    planning = build_visual_plan_result(script, language=language, research=research)
    return planning.to_legacy_plan(
        language=language,
        script=script,
        user_assets=user_assets or [],
    )


def build_visual_plan_result(
    script: dict[str, Any],
    *,
    language: str,
    research: dict[str, Any] | None = None,
):
    """Full planning outcome (plan + validation), for callers that want both."""
    research = research or {}
    result = from_legacy_script(script or {})
    request = VisualPlanRequest(
        script=result,
        language=language or result.language,
        topic=str(research.get("topic") or result.title or ""),
        title=str(result.title or ""),
        claims=list(research.get("claims") or []),
        format_id="vertical_short",
        template_id="fullscreen_voiceover_v1",
    )
    return build_plan(request, source_text=str(research.get("summary") or ""))
