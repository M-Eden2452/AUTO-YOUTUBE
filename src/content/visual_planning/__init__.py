"""Visual planning: one extensible way to decide what a scene should show.

Sits between the script engine and the existing asset search, and does none of
their work: it never downloads, never picks the final file, never renders and never
calls Vision.

    request  = VisualPlanRequest(script=script_result, topic=..., claims=...)
    planning = build_plan(request)              # -> VisualPlanning
    plan     = planning.to_legacy_plan(...)     # -> the visual_plan.json the pipeline stores

Replaces ``src.news.visual_plan.make_stock_query`` - four ``if`` branches returning
one of four fixed English strings for every video - with a plan built from the
script's own words: subject, action, place and period per scene, a shot type, the
kinds of material that would work, and a primary search intent with fallbacks that
actually widen.

The stored ``visual_plan.json`` is extended, never replaced (see ``legacy_format``),
and the ``semantic`` block it now carries is the one
``src.assets.semantic_selection.analyze_scene`` already knew how to read - so the
existing providers, ranking and selection are reused untouched.
"""

from __future__ import annotations

from .contract import (
    BaseVisualPlanner,
    VisualPlanner,
    VisualPlannerCapabilities,
    VisualPlannerError,
    VisualPlannerInputError,
    VisualPlannerUnavailableError,
)
from .engine import VisualPlanning, build_plan
from .legacy_format import (
    from_legacy_visual_plan,
    intent_to_query,
    legacy_broad_query,
    semantic_block,
    to_legacy_visual_plan,
)
from .models import (
    INTENT_ALTERNATIVE,
    INTENT_ATMOSPHERIC_FALLBACK,
    INTENT_CONTEXT_FALLBACK,
    INTENT_KINDS,
    INTENT_PRIMARY,
    MEDIA_ANIMATED_IMAGE,
    MEDIA_ARCHIVE_FOOTAGE,
    MEDIA_DIAGRAM,
    MEDIA_IMAGE,
    MEDIA_KIND_SEARCH_TYPE,
    MEDIA_KINDS,
    MEDIA_MAP,
    MEDIA_VIDEO,
    SHOT_ACTION,
    SHOT_CONTEXT,
    SHOT_DETAIL,
    SHOT_ESTABLISHING,
    SHOT_EVIDENCE,
    SHOT_PAYOFF,
    SHOT_TYPES,
    VISUAL_PLAN_SCHEMA_VERSION,
    SceneVisualPlan,
    VisualEntity,
    VisualPlanRequest,
    VisualPlanResult,
    VisualPlanValidationIssue,
    VisualPlanValidationResult,
    VisualSearchIntent,
)
from .registry import (
    DEFAULT_PLANNER_ID,
    get_planner,
    list_capabilities,
    list_planner_ids,
    resolve_planner_id,
)
from .validation import validate_visual_plan

__all__ = [
    "DEFAULT_PLANNER_ID",
    "INTENT_ALTERNATIVE",
    "INTENT_ATMOSPHERIC_FALLBACK",
    "INTENT_CONTEXT_FALLBACK",
    "INTENT_KINDS",
    "INTENT_PRIMARY",
    "MEDIA_ANIMATED_IMAGE",
    "MEDIA_ARCHIVE_FOOTAGE",
    "MEDIA_DIAGRAM",
    "MEDIA_IMAGE",
    "MEDIA_KINDS",
    "MEDIA_KIND_SEARCH_TYPE",
    "MEDIA_MAP",
    "MEDIA_VIDEO",
    "SHOT_ACTION",
    "SHOT_CONTEXT",
    "SHOT_DETAIL",
    "SHOT_ESTABLISHING",
    "SHOT_EVIDENCE",
    "SHOT_PAYOFF",
    "SHOT_TYPES",
    "VISUAL_PLAN_SCHEMA_VERSION",
    "BaseVisualPlanner",
    "SceneVisualPlan",
    "VisualEntity",
    "VisualPlanRequest",
    "VisualPlanResult",
    "VisualPlanValidationIssue",
    "VisualPlanValidationResult",
    "VisualPlanner",
    "VisualPlannerCapabilities",
    "VisualPlannerError",
    "VisualPlannerInputError",
    "VisualPlannerUnavailableError",
    "VisualPlanning",
    "VisualSearchIntent",
    "build_plan",
    "from_legacy_visual_plan",
    "get_planner",
    "intent_to_query",
    "legacy_broad_query",
    "list_capabilities",
    "list_planner_ids",
    "resolve_planner_id",
    "semantic_block",
    "to_legacy_visual_plan",
    "validate_visual_plan",
]
