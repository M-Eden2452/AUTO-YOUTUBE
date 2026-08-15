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

This is also where the model-assisted semantic adapter becomes reachable at all. It is
asked for, never assumed: ``build_semantic_brief_adapter`` returns ``None`` unless the
standing paid policy in ``config/semantic_brief.json`` and this run's network approval
both allow it, and ``None`` is the shipped state of the repository. With ``None`` the
plan is the deterministic plan it has always been, so nothing about an ordinary run
changes by this module knowing the adapter exists.
"""

from __future__ import annotations

from typing import Any

from src.content.script_engine import from_legacy_script
from src.content.semantic_brief_openai import (
    build_semantic_brief_adapter,
    semantic_brief_project_usage,
)
from src.content.visual_planning import VisualPlanRequest, build_plan

__all__ = ["build_visual_plan", "build_visual_plan_result"]


def build_visual_plan(
    script: dict[str, Any],
    *,
    language: str,
    user_assets: list[str] | None = None,
    research: dict[str, Any] | None = None,
    prior_usage: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """The visual_plan.json payload for this script. Signature unchanged since Stage AB.

    ``research`` is optional and additive: claims sharpen which entity the video is
    actually about, but the plan is built from the script alone when they are absent
    (which is the case for every caller written before this stage).

    ``prior_usage`` is what this project has already spent on paid semantic briefs. A
    caller that rebuilds a plan for an existing project - the ``visual_plan`` stage on a
    rerun, either ``_replan`` of an adaptation pass - passes it so the project's ceiling
    is the project's, not this build's. Omitting it means "this is the project's first
    build", which is true for every caller written before this stage.
    """
    planning = build_visual_plan_result(
        script, language=language, research=research, prior_usage=prior_usage
    )
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
    prior_usage: dict[str, Any] | None = None,
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
    # The project's prior spend seeds the adapter's guards and, after the build, is the
    # same value the record is reconciled against. One variable, used twice, so the
    # ceiling the backend enforced and the number written to disk cannot disagree.
    brief_adapter = build_semantic_brief_adapter(prior_usage=prior_usage)
    planning = build_plan(
        request,
        source_text=str(research.get("summary") or ""),
        brief_adapter=brief_adapter,
    )
    usage = semantic_brief_project_usage(brief_adapter, prior_usage=prior_usage)
    if usage:
        planning.result.metadata["semantic_brief_usage"] = usage
    return planning
