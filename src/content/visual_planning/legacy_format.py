"""Bridge between ``VisualPlanResult`` and the ``visual_plan.json`` already on disk.

The stored format is not replaced. Every key the pipeline writes today is still
written, with the same meaning, so ``asset_manager``, ``final_renderer`` and
``visual_preview`` keep working untouched.

Two additions carry the new plan downstream:

- ``semantic`` - the block ``src.assets.semantic_selection.analyze_scene`` already
  reads as an explicit override (``explicit = scene.get("semantic") or {}``). Filling
  it in is what makes the whole existing search path use the plan **without changing
  a single provider**: without it, ``analyze_scene`` falls back to the whale-and-ocean
  keyword guesses it was prototyped with.
- ``visual_intents`` - the structured, language-tagged intents, for callers that want
  more than a flat string.

Old plans, written before any of this existed, are read by ``from_legacy_visual_plan``
without migration: their ``primary_query``/``alternative_queries`` become intents so
the same validation can run on them.
"""

from __future__ import annotations

from typing import Any

from src.assets.semantic_selection.models import (
    SCENE_ABSTRACT_EXPLANATION,
    SCENE_ENVIRONMENT,
    SCENE_EXACT_ACTION,
    SCENE_EXACT_SUBJECT,
    SCENE_RESEARCH_CONTEXT,
    SemanticScene,
)

from .brief import parse_brief
from .expansion import (
    MAX_PROVIDER_QUERIES,
    expand_queries,
    planning_input,
    planning_input_from_scene,
)
from .models import (
    INTENT_ALTERNATIVE,
    INTENT_PRIMARY,
    MEDIA_KIND_SEARCH_TYPE,
    MEDIA_ANIMATED_IMAGE,
    MEDIA_VIDEO,
    SHOT_ACTION,
    SHOT_CONTEXT,
    SHOT_DETAIL,
    SHOT_ESTABLISHING,
    SHOT_EVIDENCE,
    SHOT_PAYOFF,
    SceneVisualPlan,
    VisualPlanResult,
    VisualSearchIntent,
)

# Technical rejects that have nothing to do with the subject. Unchanged from the
# pre-Q2 plan builder - they are the only negatives that are safe without knowing
# the domain.
DEFAULT_NEGATIVE_KEYWORDS = ["watermark", "logo", "low resolution"]

# Keys the pipeline wrote before this layer existed. Anything outside this set is
# additive, which is what keeps old consumers working.
LEGACY_SCENE_KEYS = (
    "scene_id",
    "narration",
    "target_duration_sec",
    "visual_type",
    "visual_description",
    "primary_query",
    "alternative_queries",
    "negative_keywords",
    "preferred_asset_ids",
    "allow_user_asset",
    "allow_stock",
    "allow_article_asset",
    "fallback_type",
    "camera_effect",
    "transition",
)

# How a shot type reaches the vocabulary semantic_selection already uses.
_SHOT_TO_PRIORITY = {
    SHOT_ACTION: SCENE_EXACT_ACTION,
    SHOT_DETAIL: SCENE_EXACT_SUBJECT,
    SHOT_EVIDENCE: SCENE_RESEARCH_CONTEXT,
}


def semantic_scene_queries(scene: SemanticScene) -> list[dict[str, Any]]:
    """The expansion ladder for a scene ``analyze_scene`` has already parsed.

    A shape adapter, not a second query owner: every string here is produced by
    ``expansion``. It exists because the asset manifest and the production plan store
    queries as ``{kind, fallback_level, query}`` items and hold a ``SemanticScene``
    rather than the ``SceneVisualPlan`` ``planning_input_from_scene`` reads.

    What it replaced generated four queries per scene from fixed parts - subject plus
    camera, environment plus the literal word "nature", and a hardcoded ``whale``
    category when a scene had no subject at all - without ever asking whether any of
    it was in a language the provider could search. A scene stating its meaning only
    in the script's own language now yields nothing here, and nothing is the honest
    answer: the Envato manual provider still builds its own request from the scene
    text, and the stored fields record no query rather than an unanswerable one.
    """
    queries = expand_queries(
        planning_input(
            subject=_leading(scene.subject),
            action=_leading(scene.action),
            place=_leading(scene.location) or _leading(scene.environment),
            entities=list(scene.secondary_subjects),
            context=[*scene.context, *scene.must_include],
            must_avoid=list(scene.must_not_include),
        ),
        limit=MAX_PROVIDER_QUERIES,
    )
    return [
        {
            "kind": INTENT_PRIMARY if level == 1 else INTENT_ALTERNATIVE,
            "fallback_level": level,
            "query": query,
        }
        for level, query in enumerate(queries, start=1)
    ]


def _leading(values: list[str]) -> str:
    return str(values[0]) if values else ""


def intent_to_query(intent: VisualSearchIntent) -> str:
    """A provider-ready string for one intent. Terms only, most specific first."""
    return " ".join(intent.terms)


def visual_priority_for(scene: SceneVisualPlan) -> str:
    """Map a shot type onto the priority vocabulary semantic_selection understands."""
    mapped = _SHOT_TO_PRIORITY.get(scene.shot_type)
    if mapped:
        return mapped
    if scene.shot_type in {SHOT_ESTABLISHING, SHOT_PAYOFF}:
        return SCENE_EXACT_SUBJECT if scene.subject else SCENE_ENVIRONMENT
    if scene.shot_type == SHOT_CONTEXT:
        return SCENE_ENVIRONMENT if scene.place else SCENE_ABSTRACT_EXPLANATION
    return SCENE_ABSTRACT_EXPLANATION


def semantic_block(scene: SceneVisualPlan) -> dict[str, Any]:
    """The explicit override ``analyze_scene`` consumes instead of guessing."""
    brief = getattr(scene, "brief", None)
    # Only an author states these, so they are read straight off the brief rather than
    # mirrored onto SceneVisualPlan: a field the planner can never fill has no business
    # being a planner field.
    context = [str(item) for item in (getattr(brief, "context", None) or [])]
    conflicting = [str(item) for item in (getattr(brief, "conflicting_context", None) or [])]
    source_class = str(getattr(brief, "source_class", "") or "")
    return {
        "subject": [scene.subject] if scene.subject else [],
        "secondary_subjects": list(scene.secondary_subjects),
        "action": [scene.action] if scene.action else [],
        "environment": [scene.place] if scene.place else [],
        "location": [scene.place] if scene.place else [],
        "camera": [],
        "mood": [],
        "must_include": list(scene.must_include),
        "should_include": [term for term in (*scene.secondary_subjects, scene.place) if term],
        "must_not_include": list(scene.must_avoid),
        "context": context,
        "conflicting_context": conflicting,
        "source_class": source_class,
        "visual_priority": visual_priority_for(scene),
        "fallback_level": scene.intents[0].fallback_level if scene.intents else 1,
    }


def _brief_provider_queries(scene: SceneVisualPlan) -> list[str]:
    """The scene's own provider-ready queries, whoever wrote them.

    These lead the expansion because nothing derived from the scene's fields can be
    more exact than a query the author - or the producer, from linked evidence -
    stated outright. They keep reaching the adapter through ``visual_brief`` either
    way; mirroring them here is what lets a pre-Q2 reader see them at all.
    """
    brief = getattr(scene, "brief", None)
    mapping = getattr(brief, "provider_queries", None) or {}
    return [
        str(query)
        for values in mapping.values()
        for query in (values or [])
        if str(query).strip()
    ]


def scene_to_legacy(
    scene: SceneVisualPlan,
    *,
    script_scene: dict[str, Any] | None = None,
    preferred_asset_ids: list[str] | None = None,
    include_planning_fields: bool = True,
) -> dict[str, Any]:
    """One scene of the stored plan, in the order the pipeline has always written."""
    narration = str((script_scene or {}).get("narration") or scene.meaning)
    queries = [intent_to_query(intent) for intent in scene.intents]
    primary_query = queries[0] if queries else ""
    alternatives = [query for query in queries[1:] if query]

    # The flat query fields are what a pre-Q2 reader has, so the ladder is mirrored
    # into them: the intents say what the scene is about in its own language, and the
    # expansion says it again, wider, in the language a provider can search. Where
    # there is no provider-language evidence this adds nothing - which is the point.
    # It used to add the retired broad query instead, i.e. a whale.
    expansion = expand_queries(
        planning_input_from_scene(scene),
        seeds=_brief_provider_queries(scene),
    )
    for query in expansion:
        if query != primary_query and query not in alternatives:
            alternatives.append(query)
    if not primary_query and alternatives:
        primary_query = alternatives.pop(0)

    data: dict[str, Any] = {
        "scene_id": scene.scene_id,
        "narration": narration,
        "on_screen_text": str((script_scene or {}).get("on_screen_text") or ""),
        "target_duration_sec": float((script_scene or {}).get("target_duration_sec") or scene.duration_sec or 3.5),
        "visual_type": MEDIA_KIND_SEARCH_TYPE.get(scene.preferred_media_kind, "video")
        if scene.preferred_media_kind != MEDIA_ANIMATED_IMAGE
        else MEDIA_ANIMATED_IMAGE,
        "visual_description": scene.meaning,
        "primary_query": primary_query,
        "alternative_queries": alternatives,
        "negative_keywords": [*DEFAULT_NEGATIVE_KEYWORDS, *scene.must_avoid],
        "preferred_asset_ids": list(preferred_asset_ids or []),
        "allow_user_asset": True,
        "allow_stock": True,
        "allow_article_asset": False,
        "fallback_type": "text_card" if scene.index == 1 else "animated_image",
        "camera_effect": "slow_zoom_in",
        "transition": "cut",
    }
    if include_planning_fields:
        data["semantic"] = semantic_block(scene)
        data["visual_priority"] = data["semantic"]["visual_priority"]
        data["fallback_level"] = data["semantic"]["fallback_level"]
        data["shot_type"] = scene.shot_type
        data["allowed_media_kinds"] = list(scene.allowed_media_kinds)
        data["visual_intents"] = [intent.to_dict() for intent in scene.intents]
        if scene.claim_ids:
            data["claim_ids"] = list(scene.claim_ids)
        if scene.source_refs:
            data["source_refs"] = list(scene.source_refs)
        if scene.period:
            data["period"] = scene.period
        if scene.warnings:
            data["planning_warnings"] = list(scene.warnings)
        if getattr(scene, "brief", None) is not None:
            # Carried into the stored plan so retrieval sees the final brief after
            # automatic production and the last-wins author overlay. Source class
            # routes providers and provider queries bypass query building entirely.
            brief_data = scene.brief.to_dict()
            if brief_data:
                data["visual_brief"] = brief_data
                if brief_data.get("source_class"):
                    data["source_class"] = brief_data["source_class"]
                if brief_data.get("provider_queries"):
                    data["provider_queries"] = brief_data["provider_queries"]
    return data


def to_legacy_visual_plan(
    result: VisualPlanResult,
    *,
    language: str = "",
    script: dict[str, Any] | None = None,
    user_assets: list[str] | None = None,
    include_planning_fields: bool = True,
) -> dict[str, Any]:
    """Render a VisualPlanResult as the visual_plan.json the pipeline already stores."""
    user_assets = user_assets or []
    script_scenes = {
        str(scene.get("scene_id") or ""): scene
        for scene in ((script or {}).get("scenes") or [])
        if isinstance(scene, dict)
    }
    scenes = [
        scene_to_legacy(
            scene,
            script_scene=script_scenes.get(scene.scene_id),
            preferred_asset_ids=[f"user_asset_{scene.index:03d}"] if scene.index <= len(user_assets) else [],
            include_planning_fields=include_planning_fields,
        )
        for scene in result.scenes
    ]
    plan: dict[str, Any] = {
        "language": language or result.language,
        "aspect_ratio": result.aspect_ratio,
        "resolution": {"width": 1080, "height": 1920},
        "scenes": scenes,
    }
    if include_planning_fields:
        plan["visual_plan_schema_version"] = result.schema_version
        plan["planner_id"] = result.planner_id
        plan["planner_version"] = result.planner_version
        plan["topic_entity"] = result.topic_entity
        plan["intent_language"] = result.language
        if result.warnings:
            plan["planning_warnings"] = list(result.warnings)
        if result.metadata:
            plan["planning_metadata"] = dict(result.metadata)
    return plan


def _intent_from_query(query: str, *, kind: str, level: int, language: str) -> VisualSearchIntent:
    terms = [term for term in str(query or "").split() if term]
    return VisualSearchIntent(
        kind=kind,
        subject=terms[0] if terms else "",
        modifiers=[],
        context=terms[1:],
        language=language,
        fallback_level=level,
    )


def from_legacy_visual_plan(data: dict[str, Any]) -> VisualPlanResult:
    """Read any visual_plan.json - written before or after this layer existed."""
    language = str(data.get("intent_language") or data.get("language") or "ru")
    scenes: list[SceneVisualPlan] = []
    for index, raw in enumerate((data.get("scenes") or []), start=1):
        if not isinstance(raw, dict):
            continue
        semantic = raw.get("semantic") if isinstance(raw.get("semantic"), dict) else {}
        subjects = [str(item) for item in (semantic.get("subject") or []) if item]
        actions = [str(item) for item in (semantic.get("action") or []) if item]
        locations = [str(item) for item in (semantic.get("location") or []) if item]

        raw_intents = raw.get("visual_intents")
        if isinstance(raw_intents, list) and raw_intents:
            intents = [
                VisualSearchIntent(
                    kind=str(entry.get("kind") or INTENT_PRIMARY),
                    subject=str(entry.get("subject") or ""),
                    modifiers=[str(item) for item in (entry.get("modifiers") or [])],
                    context=[str(item) for item in (entry.get("context") or [])],
                    language=str(entry.get("language") or language),
                    fallback_level=int(entry.get("fallback_level") or 1),
                    requires_translation=bool(entry.get("requires_translation", False)),
                    notes=str(entry.get("notes") or ""),
                )
                for entry in raw_intents
                if isinstance(entry, dict)
            ]
        else:
            # A pre-Q2 plan: its flat query strings are the only intents it has.
            intents = []
            if raw.get("primary_query"):
                intents.append(
                    _intent_from_query(raw["primary_query"], kind=INTENT_PRIMARY, level=1, language=language)
                )
            for position, query in enumerate((raw.get("alternative_queries") or []), start=2):
                intents.append(
                    _intent_from_query(query, kind=INTENT_ALTERNATIVE, level=position, language=language)
                )

        raw_brief = raw.get("visual_brief")
        brief_data = dict(raw_brief) if isinstance(raw_brief, dict) else {}
        if raw.get("provider_queries") and not brief_data.get("provider_queries"):
            brief_data["provider_queries"] = raw["provider_queries"]
        brief = parse_brief(brief_data)

        scenes.append(
            SceneVisualPlan(
                scene_id=str(raw.get("scene_id") or f"scene_{index:03d}"),
                index=index,
                meaning=str(raw.get("visual_description") or raw.get("narration") or ""),
                subject=subjects[0] if subjects else "",
                secondary_subjects=[str(item) for item in (semantic.get("secondary_subjects") or [])],
                action=actions[0] if actions else "",
                place=locations[0] if locations else "",
                period=str(raw.get("period") or ""),
                shot_type=str(raw.get("shot_type") or SHOT_CONTEXT),
                allowed_media_kinds=[str(item) for item in (raw.get("allowed_media_kinds") or [])],
                preferred_media_kind=str(raw.get("visual_type") or MEDIA_VIDEO),
                must_include=[str(item) for item in (semantic.get("must_include") or [])],
                must_avoid=[str(item) for item in (semantic.get("must_not_include") or [])],
                intents=intents,
                claim_ids=[str(item) for item in (raw.get("claim_ids") or [])],
                source_refs=[str(item) for item in (raw.get("source_refs") or [])],
                duration_sec=float(raw.get("target_duration_sec") or 0.0),
                warnings=[str(item) for item in (raw.get("planning_warnings") or [])],
                brief=brief if not brief.is_empty else None,
            )
        )

    return VisualPlanResult(
        scenes=scenes,
        language=language,
        topic_entity=str(data.get("topic_entity") or ""),
        planner_id=str(data.get("planner_id") or ""),
        planner_version=str(data.get("planner_version") or ""),
        aspect_ratio=str(data.get("aspect_ratio") or "9:16"),
        warnings=[str(item) for item in (data.get("planning_warnings") or [])],
        metadata=dict(data.get("planning_metadata") or {}),
        schema_version=int(data.get("visual_plan_schema_version") or 1),
    )


__all__ = [
    "DEFAULT_NEGATIVE_KEYWORDS",
    "LEGACY_SCENE_KEYS",
    "from_legacy_visual_plan",
    "intent_to_query",
    "scene_to_legacy",
    "semantic_block",
    "semantic_scene_queries",
    "to_legacy_visual_plan",
    "visual_priority_for",
]
