"""Visual plan validation: the checks that decide whether a plan is worth searching on.

Runs on a ``VisualPlanResult``, so it applies to every planner equally - including a
future LLM one, whose output is exactly the case the "entity not in the source"
check exists for. Nothing here touches the network, the filesystem or any paid API.

Errors are things that are broken: a scene with no plan, a plan for a scene that
does not exist, a search with nothing in it, a demand the plan contradicts a line
later. Warnings are things that are merely weak: a broad query, a thin fallback.
Deciding what to show is creative, and a validator that fails creative choices is a
validator people learn to ignore.
"""

from __future__ import annotations

from typing import Any

from src.content.script_engine.models import SEVERITY_ERROR, SEVERITY_WARNING

from .entities import content_tokens, stem
from .models import (
    MEDIA_KINDS,
    SHOT_TYPES,
    SceneVisualPlan,
    VisualPlanResult,
    VisualPlanValidationIssue,
    VisualPlanValidationResult,
)

# A primary search made of one word is a category, not a subject.
MIN_PRIMARY_INTENT_TERMS = 2


def validate_visual_plan(
    plan: VisualPlanResult,
    *,
    script: Any = None,
    source_text: str = "",
) -> VisualPlanValidationResult:
    """Check one plan and return every problem found.

    ``script`` is the ``ScriptResult`` the plan claims to describe; without it the
    scene-correspondence checks are skipped rather than guessed at. ``source_text``
    is extra material (article, claims) that a plan is also allowed to draw on.
    """
    issues: list[VisualPlanValidationIssue] = []

    if not plan.scenes:
        issues.append(_issue("empty_plan", "Визуальный план не содержит ни одной сцены."))
        return VisualPlanValidationResult(issues=issues)

    issues.extend(_check_scene_identity(plan, script))
    issues.extend(_check_scene_content(plan))
    issues.extend(_check_intents(plan))
    issues.extend(_check_grounding(plan, script, source_text))
    return VisualPlanValidationResult(issues=issues)


def _issue(code: str, message: str, *, severity: str = SEVERITY_ERROR, scene_id: str = "") -> VisualPlanValidationIssue:
    return VisualPlanValidationIssue(code=code, message=message, severity=severity, scene_id=scene_id)


def _check_scene_identity(plan: VisualPlanResult, script: Any) -> list[VisualPlanValidationIssue]:
    issues: list[VisualPlanValidationIssue] = []

    seen: set[str] = set()
    for scene in plan.scenes:
        if not scene.scene_id:
            issues.append(_issue("missing_scene_id", "У сцены плана нет scene_id."))
            continue
        if scene.scene_id in seen:
            issues.append(
                _issue("duplicate_scene_id", f"scene_id {scene.scene_id!r} встречается дважды.", scene_id=scene.scene_id)
            )
        seen.add(scene.scene_id)

    indexes = [scene.index for scene in plan.scenes]
    if indexes != sorted(indexes):
        issues.append(_issue("scenes_out_of_order", "Сцены плана идут не по возрастанию индекса."))

    script_scenes = list(getattr(script, "scenes", None) or [])
    if not script_scenes:
        return issues

    script_ids = [str(getattr(scene, "scene_id", "")) for scene in script_scenes]
    if len(plan.scenes) != len(script_ids):
        issues.append(
            _issue(
                "scene_count_mismatch",
                f"В сценарии {len(script_ids)} сцен, а в плане {len(plan.scenes)}.",
            )
        )
    for scene_id in script_ids:
        if scene_id not in seen:
            issues.append(_issue("missing_scene_plan", f"Для сцены {scene_id} нет визуального плана.", scene_id=scene_id))
    for scene in plan.scenes:
        if scene.scene_id and scene.scene_id not in script_ids:
            issues.append(
                _issue("unknown_scene_id", f"В плане есть сцена {scene.scene_id!r}, которой нет в сценарии.", scene_id=scene.scene_id)
            )
    if [scene.scene_id for scene in plan.scenes] != script_ids and not issues:
        issues.append(_issue("scenes_out_of_order", "Порядок сцен плана не совпадает с порядком сценария."))
    return issues


def _check_scene_content(plan: VisualPlanResult) -> list[VisualPlanValidationIssue]:
    issues: list[VisualPlanValidationIssue] = []
    for scene in plan.scenes:
        if not (scene.meaning or "").strip():
            issues.append(
                _issue("empty_visual_intent", f"Сцена {scene.scene_id}: не сказано, что показывать.", scene_id=scene.scene_id)
            )
        if scene.shot_type not in SHOT_TYPES:
            issues.append(
                _issue(
                    "unsupported_shot_type",
                    f"Сцена {scene.scene_id}: неизвестный тип кадра {scene.shot_type!r}.",
                    scene_id=scene.scene_id,
                )
            )
        for kind in [scene.preferred_media_kind, *scene.allowed_media_kinds]:
            if kind and kind not in MEDIA_KINDS:
                issues.append(
                    _issue(
                        "unsupported_media_kind",
                        f"Сцена {scene.scene_id}: неизвестный тип материала {kind!r}.",
                        scene_id=scene.scene_id,
                    )
                )
        if scene.preferred_media_kind and scene.allowed_media_kinds:
            if scene.preferred_media_kind not in scene.allowed_media_kinds:
                issues.append(
                    _issue(
                        "preferred_media_not_allowed",
                        f"Сцена {scene.scene_id}: предпочтительный тип {scene.preferred_media_kind!r} "
                        "не входит в список допустимых.",
                        scene_id=scene.scene_id,
                    )
                )
        issues.extend(_check_constraints(scene))
    return issues


def _check_constraints(scene: SceneVisualPlan) -> list[VisualPlanValidationIssue]:
    issues: list[VisualPlanValidationIssue] = []
    avoid = {term.casefold() for term in scene.must_avoid if term}
    for term in scene.must_include:
        if term.casefold() in avoid:
            issues.append(
                _issue(
                    "conflicting_constraints",
                    f"Сцена {scene.scene_id}: {term!r} одновременно обязателен и запрещён.",
                    scene_id=scene.scene_id,
                )
            )

    if not scene.must_include:
        return issues
    searchable = {
        term.casefold()
        for intent in scene.intents
        for term in intent.terms
    }
    for term in scene.must_include:
        if term.casefold() not in searchable:
            issues.append(
                _issue(
                    "must_include_not_searched",
                    f"Сцена {scene.scene_id}: {term!r} обязателен в кадре, но его нет ни в одном запросе.",
                    scene_id=scene.scene_id,
                )
            )
    return issues


def _check_intents(plan: VisualPlanResult) -> list[VisualPlanValidationIssue]:
    issues: list[VisualPlanValidationIssue] = []
    primary_keys: list[tuple[str, ...]] = []

    for scene in plan.scenes:
        if not scene.intents:
            issues.append(
                _issue("no_search_intents", f"Сцена {scene.scene_id}: нет ни одного поискового запроса.", scene_id=scene.scene_id)
            )
            continue

        seen: set[tuple[str, ...]] = set()
        for intent in scene.intents:
            key = tuple(term.casefold() for term in intent.terms)
            if not key:
                issues.append(
                    _issue("empty_search_intent", f"Сцена {scene.scene_id}: пустой поисковый запрос.", scene_id=scene.scene_id)
                )
                continue
            if key in seen:
                issues.append(
                    _issue(
                        "duplicate_fallback_intent",
                        f"Сцена {scene.scene_id}: запасной запрос дословно повторяет предыдущий.",
                        severity=SEVERITY_WARNING,
                        scene_id=scene.scene_id,
                    )
                )
            seen.add(key)

        primary = scene.primary_intent
        if primary is not None and primary.terms:
            primary_keys.append(tuple(term.casefold() for term in primary.terms))
            if len(primary.terms) < MIN_PRIMARY_INTENT_TERMS:
                issues.append(
                    _issue(
                        "intent_too_broad",
                        f"Сцена {scene.scene_id}: основной запрос из одного слова "
                        f"({primary.terms[0]!r}) найдёт что угодно.",
                        severity=SEVERITY_WARNING,
                        scene_id=scene.scene_id,
                    )
                )
            if not scene.fallback_intents:
                issues.append(
                    _issue(
                        "no_fallback_intent",
                        f"Сцена {scene.scene_id}: нет запасного запроса — при неудаче искать нечем.",
                        severity=SEVERITY_WARNING,
                        scene_id=scene.scene_id,
                    )
                )

    if len(primary_keys) > 1 and len(set(primary_keys)) == 1:
        issues.append(
            _issue(
                "identical_scene_intents",
                "У всех сцен одинаковый основной запрос: видео получится однообразным.",
                severity=SEVERITY_WARNING,
            )
        )
    return issues


def _check_grounding(plan: VisualPlanResult, script: Any, source_text: str) -> list[VisualPlanValidationIssue]:
    """Nothing may be shown that the material never mentioned.

    The check that matters for any planner that can write freely: a model asked for
    a frame about crows must not quietly ask for a raven, a different country or a
    year nobody wrote down.
    """
    script_scenes = list(getattr(script, "scenes", None) or [])
    if not script_scenes and not source_text:
        return []

    grounded: set[str] = set()
    for scene in script_scenes:
        for token in content_tokens(str(getattr(scene, "narration", "") or "")):
            grounded.add(stem(token))
    for token in content_tokens(source_text or ""):
        grounded.add(stem(token))
    if not grounded:
        return []

    issues: list[VisualPlanValidationIssue] = []
    for scene in plan.scenes:
        claimed = [term for term in (scene.subject, scene.place, scene.period, *scene.must_include) if term]
        for term in claimed:
            tokens = content_tokens(term)
            if not tokens:
                continue
            if any(stem(token) in grounded for token in tokens):
                continue
            issues.append(
                _issue(
                    "entity_not_in_source",
                    f"Сцена {scene.scene_id}: план требует показать {term!r}, "
                    "но этого нет ни в сценарии, ни в исходном материале.",
                    scene_id=scene.scene_id,
                )
            )
    return issues


__all__ = ["MIN_PRIMARY_INTENT_TERMS", "validate_visual_plan"]
