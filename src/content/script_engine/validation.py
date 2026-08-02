"""Script validation: the checks that decide whether a script is worth rendering.

Runs on a ``ScriptResult``, so it applies to every provider equally - including a
future LLM one, whose output is exactly the case this exists for. Nothing here
touches the network, the filesystem, or any paid API.
"""

from __future__ import annotations

from .models import (
    SCENE_ROLE_CTA,
    SCENE_ROLE_HOOK,
    SCENE_ROLE_PAYOFF,
    SCENE_ROLES,
    SEVERITY_ERROR,
    SEVERITY_WARNING,
    ScriptConstraints,
    ScriptResult,
    ScriptValidationIssue,
    ScriptValidationResult,
)
from .text_analysis import detect_language, hook_score, normalize_for_compare, similarity

# Two scenes this similar are the same thought said twice.
DUPLICATE_SIMILARITY_THRESHOLD = 0.85
# Below this a hook does not do its job: too short to say anything.
MIN_HOOK_CHARS = 15
# A single scene longer than this is a wall of text regardless of the budget.
ABSOLUTE_MAX_SCENE_DURATION_SEC = 30.0
# How far the planned total may drift from the requested target before it matters.
DURATION_DRIFT_WARNING_RATIO = 0.35


def validate_script(
    result: ScriptResult,
    *,
    constraints: ScriptConstraints | None = None,
    expected_language: str = "",
    allow_legacy_fallback: bool = False,
) -> ScriptValidationResult:
    """Check one script and return every problem found, worst first by severity."""
    limits = constraints or ScriptConstraints(target_duration_sec=result.target_duration_sec or 55.0)
    issues: list[ScriptValidationIssue] = []

    issues.extend(
        _check_source_truth(
            result,
            allow_legacy_fallback=allow_legacy_fallback,
        )
    )
    issues.extend(_check_not_empty(result))
    if not result.scenes:
        # Every remaining check is about scenes; reporting them all would bury the
        # one problem the user actually has.
        return ScriptValidationResult(issues=issues)

    issues.extend(_check_roles(result))
    issues.extend(_check_hook(result))
    issues.extend(_check_payoff(result))
    issues.extend(_check_duplicates(result))
    issues.extend(_check_durations(result, limits))
    issues.extend(_check_language(result, expected_language or result.language))
    return ScriptValidationResult(issues=issues)


def _issue(code: str, message: str, *, severity: str = SEVERITY_ERROR, scene_id: str = "") -> ScriptValidationIssue:
    return ScriptValidationIssue(code=code, message=message, severity=severity, scene_id=scene_id)


def _check_source_truth(
    result: ScriptResult,
    *,
    allow_legacy_fallback: bool,
) -> list[ScriptValidationIssue]:
    metadata = result.metadata if isinstance(result.metadata, dict) else {}
    is_insufficient_source_fallback = (
        str(metadata.get("fallback_provider") or "") == "legacy_template"
        and str(metadata.get("fallback_reason") or "") == "insufficient_source_material"
    )
    if not is_insufficient_source_fallback or allow_legacy_fallback:
        return []
    return [
        _issue(
            "template_filler_in_strict_mode",
            "Legacy template filler cannot pass strict factual validation; provide an "
            "article URL or source text, or explicitly use draft/template mode.",
        )
    ]


def _check_not_empty(result: ScriptResult) -> list[ScriptValidationIssue]:
    issues: list[ScriptValidationIssue] = []
    if not result.scenes:
        issues.append(_issue("empty_script", "Сценарий не содержит ни одной сцены."))
        return issues
    for scene in result.scenes:
        if not (scene.narration or "").strip():
            issues.append(
                _issue("empty_narration", f"Сцена {scene.scene_id}: текст озвучки пустой.", scene_id=scene.scene_id)
            )
    if not result.narration_text.strip():
        issues.append(_issue("empty_script", "Во всём сценарии нет текста озвучки."))
    return issues


def _check_roles(result: ScriptResult) -> list[ScriptValidationIssue]:
    issues: list[ScriptValidationIssue] = []
    for scene in result.scenes:
        if scene.role not in SCENE_ROLES:
            issues.append(
                _issue(
                    "unknown_role",
                    f"Сцена {scene.scene_id}: неизвестная роль {scene.role!r}.",
                    scene_id=scene.scene_id,
                )
            )
    cta_scenes = result.scenes_by_role(SCENE_ROLE_CTA)
    if cta_scenes and cta_scenes[-1] is not result.scenes[-1]:
        issues.append(
            _issue(
                "cta_not_last",
                "Призыв к действию должен быть последней сценой.",
                severity=SEVERITY_WARNING,
                scene_id=cta_scenes[-1].scene_id,
            )
        )
    return issues


def _check_hook(result: ScriptResult) -> list[ScriptValidationIssue]:
    issues: list[ScriptValidationIssue] = []
    hooks = result.scenes_by_role(SCENE_ROLE_HOOK)
    if not hooks:
        issues.append(_issue("missing_hook", "В сценарии нет сцены-крючка (hook)."))
        return issues
    if hooks[0] is not result.scenes[0]:
        issues.append(
            _issue("hook_not_first", "Крючок должен быть первой сценой.", scene_id=hooks[0].scene_id)
        )
    hook = hooks[0]
    text = (hook.narration or "").strip()
    if len(text) < MIN_HOOK_CHARS:
        issues.append(
            _issue("weak_hook", f"Крючок слишком короткий ({len(text)} символов).", scene_id=hook.scene_id)
        )
    elif hook_score(text) <= 0:
        issues.append(
            _issue(
                "weak_hook",
                "Крючок не задаёт вопрос и не содержит зацепки — вероятно, слабое начало.",
                severity=SEVERITY_WARNING,
                scene_id=hook.scene_id,
            )
        )
    return issues


def _check_payoff(result: ScriptResult) -> list[ScriptValidationIssue]:
    if result.scenes_by_role(SCENE_ROLE_PAYOFF):
        return []
    return [_issue("missing_payoff", "В сценарии нет развязки (payoff): зритель не получает ответа.")]


def _check_duplicates(result: ScriptResult) -> list[ScriptValidationIssue]:
    issues: list[ScriptValidationIssue] = []
    seen: list[tuple[str, str]] = []
    for scene in result.scenes:
        normalized = normalize_for_compare(scene.narration)
        if not normalized:
            continue
        for other_id, other_text in seen:
            if normalized == other_text:
                issues.append(
                    _issue(
                        "duplicate_scene",
                        f"Сцена {scene.scene_id} дословно повторяет {other_id}.",
                        scene_id=scene.scene_id,
                    )
                )
                break
            if similarity(normalized, other_text) >= DUPLICATE_SIMILARITY_THRESHOLD:
                issues.append(
                    _issue(
                        "near_duplicate_scene",
                        f"Сцена {scene.scene_id} почти повторяет {other_id}.",
                        severity=SEVERITY_WARNING,
                        scene_id=scene.scene_id,
                    )
                )
                break
        seen.append((scene.scene_id, normalized))

    on_screen: dict[str, str] = {}
    for scene in result.scenes:
        key = normalize_for_compare(scene.on_screen_text)
        if not key:
            continue
        if key in on_screen:
            issues.append(
                _issue(
                    "duplicate_on_screen_text",
                    f"Надпись на экране в сцене {scene.scene_id} совпадает с {on_screen[key]}.",
                    severity=SEVERITY_WARNING,
                    scene_id=scene.scene_id,
                )
            )
        else:
            on_screen[key] = scene.scene_id
    return issues


def _check_durations(result: ScriptResult, limits: ScriptConstraints) -> list[ScriptValidationIssue]:
    issues: list[ScriptValidationIssue] = []
    for scene in result.scenes:
        duration = scene.duration_sec
        if not isinstance(duration, (int, float)) or duration != duration:  # NaN check
            issues.append(
                _issue("invalid_duration", f"Сцена {scene.scene_id}: длительность не число.", scene_id=scene.scene_id)
            )
            continue
        if duration <= 0:
            issues.append(
                _issue(
                    "invalid_duration",
                    f"Сцена {scene.scene_id}: длительность {duration} не больше нуля.",
                    scene_id=scene.scene_id,
                )
            )
            continue
        if duration > ABSOLUTE_MAX_SCENE_DURATION_SEC:
            issues.append(
                _issue(
                    "scene_too_long",
                    f"Сцена {scene.scene_id}: {duration:.1f} с — длиннее предельных "
                    f"{ABSOLUTE_MAX_SCENE_DURATION_SEC:.0f} с.",
                    scene_id=scene.scene_id,
                )
            )
        elif duration > limits.max_scene_duration_sec:
            issues.append(
                _issue(
                    "scene_too_long",
                    f"Сцена {scene.scene_id}: {duration:.1f} с при пределе "
                    f"{limits.max_scene_duration_sec:.1f} с.",
                    severity=SEVERITY_WARNING,
                    scene_id=scene.scene_id,
                )
            )
        elif duration < limits.min_scene_duration_sec:
            issues.append(
                _issue(
                    "scene_too_short",
                    f"Сцена {scene.scene_id}: {duration:.1f} с — короче минимума "
                    f"{limits.min_scene_duration_sec:.1f} с.",
                    severity=SEVERITY_WARNING,
                    scene_id=scene.scene_id,
                )
            )

    starts = [scene.start_sec for scene in result.scenes]
    if any(start < 0 for start in starts):
        issues.append(_issue("invalid_duration", "Отрицательное время начала сцены."))
    elif starts != sorted(starts):
        issues.append(_issue("invalid_duration", "Сцены идут не по возрастанию времени начала."))

    target = limits.target_duration_sec or result.target_duration_sec
    total = result.estimated_duration_sec
    if target > 0 and total > 0 and abs(total - target) / target > DURATION_DRIFT_WARNING_RATIO:
        issues.append(
            _issue(
                "duration_off_target",
                f"Расчётная длительность {total:.1f} с сильно отличается от цели {target:.1f} с.",
                severity=SEVERITY_WARNING,
            )
        )
    return issues


def _check_language(result: ScriptResult, expected_language: str) -> list[ScriptValidationIssue]:
    expected = (expected_language or "").split("-")[0].lower()
    if not expected:
        return []
    detected = detect_language(result.narration_text)
    if detected and detected != expected:
        return [
            _issue(
                "language_mismatch",
                f"Сценарий заявлен как {expected!r}, но текст выглядит как {detected!r}.",
            )
        ]
    issues: list[ScriptValidationIssue] = []
    for scene in result.scenes:
        scene_language = detect_language(scene.narration)
        if scene_language and scene_language != expected:
            issues.append(
                _issue(
                    "language_mismatch",
                    f"Сцена {scene.scene_id} написана на {scene_language!r}, а не на {expected!r}.",
                    severity=SEVERITY_WARNING,
                    scene_id=scene.scene_id,
                )
            )
    return issues


__all__ = [
    "ABSOLUTE_MAX_SCENE_DURATION_SEC",
    "DUPLICATE_SIMILARITY_THRESHOLD",
    "DURATION_DRIFT_WARNING_RATIO",
    "MIN_HOOK_CHARS",
    "validate_script",
]
