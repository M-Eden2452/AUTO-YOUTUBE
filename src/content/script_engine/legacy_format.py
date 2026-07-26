"""Bridge between ``ScriptResult`` and the ``script.json`` already on disk.

The stored format is not replaced. Every key the pipeline writes today is still
written, with the same meaning, so ``visual_plan``, ``voice_adapter``,
``subtitles``, ``final_renderer``, ``quality_check`` and ``exporter`` keep working
untouched. The engine's own fields (``role``, ``keywords``, ``source_refs``,
provider identity) are added alongside them - old readers ignore what they do not
know, and ``from_legacy_script`` reads a pre-engine file without any migration.
"""

from __future__ import annotations

from typing import Any

from .models import (
    SCENE_ROLE_CTA,
    SCENE_ROLE_DEVELOPMENT,
    SCENE_ROLE_HOOK,
    SCENE_ROLE_PAYOFF,
    SCRIPT_SCHEMA_VERSION,
    SOURCE_RESEARCH,
    ScriptResult,
    ScriptScene,
)

# Keys the pipeline wrote before the engine existed. Anything outside this set is
# additive, which is what keeps old consumers working.
LEGACY_TOP_LEVEL_KEYS = (
    "title",
    "hook",
    "language",
    "target_duration_sec",
    "estimated_duration_sec",
    "narration_text",
    "description",
    "source_claim_ids",
    "scenes",
)
LEGACY_SCENE_KEYS = (
    "scene_id",
    "start_sec",
    "target_duration_sec",
    "narration",
    "claim_ids",
    "visual_intent",
    "on_screen_text",
    "emotion",
)


def scene_to_legacy(scene: ScriptScene, *, include_engine_fields: bool = True) -> dict[str, Any]:
    data: dict[str, Any] = {
        "scene_id": scene.scene_id,
        "start_sec": round(scene.start_sec, 2),
        "target_duration_sec": round(scene.duration_sec, 2),
        "narration": scene.narration,
        "claim_ids": list(scene.claim_ids),
        "visual_intent": scene.visual_intent,
        "on_screen_text": scene.on_screen_text,
        "emotion": scene.emotion,
    }
    if include_engine_fields:
        data["role"] = scene.role
        if scene.keywords:
            data["keywords"] = list(scene.keywords)
        if scene.source_refs:
            data["source_refs"] = list(scene.source_refs)
        if scene.pause_after_sec is not None:
            data["pause_after_sec"] = scene.pause_after_sec
        if scene.visual_brief:
            data["visual_brief"] = dict(scene.visual_brief)
    return data


def to_legacy_script(
    result: ScriptResult,
    *,
    target_duration_sec: float | int | None = None,
    include_engine_fields: bool = True,
) -> dict[str, Any]:
    """Render a ScriptResult as the script.json the pipeline already stores.

    ``target_duration_sec`` is the *job's* requested duration (an int in job.json),
    kept separate from the sum of scene durations, exactly as before.
    """
    target = target_duration_sec if target_duration_sec is not None else result.target_duration_sec
    script: dict[str, Any] = {
        "title": result.title,
        "hook": result.hook,
        "language": result.language,
        "target_duration_sec": target,
        "estimated_duration_sec": result.estimated_duration_sec,
        "narration_text": result.narration_text,
        "description": result.description,
        "source_claim_ids": list(result.source_claim_ids),
        "scenes": [scene_to_legacy(scene, include_engine_fields=include_engine_fields) for scene in result.scenes],
    }
    if include_engine_fields:
        script["script_schema_version"] = result.schema_version
        script["script_provider"] = result.provider_id
        script["script_provider_version"] = result.provider_version
        script["source_kind"] = result.source_kind
        script["scene_count"] = len(result.scenes)
        if result.warnings:
            script["script_warnings"] = list(result.warnings)
        if result.metadata:
            script["script_metadata"] = dict(result.metadata)
    return script


def infer_roles(scene_count: int) -> list[str]:
    """Roles for a script that never recorded any (every pre-engine script.json).

    First scene opens, last closes, the rest develop - which is what the old
    six-phrase generator produced in practice.
    """
    if scene_count <= 0:
        return []
    if scene_count == 1:
        return [SCENE_ROLE_HOOK]
    if scene_count == 2:
        return [SCENE_ROLE_HOOK, SCENE_ROLE_PAYOFF]
    return [SCENE_ROLE_HOOK] + [SCENE_ROLE_DEVELOPMENT] * (scene_count - 2) + [SCENE_ROLE_PAYOFF]


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def from_legacy_script(data: dict[str, Any]) -> ScriptResult:
    """Read any script.json - written before or after this engine existed.

    Prefers ``actual_duration_sec`` when the voice stage has already written the
    real timings (src.audio.scene_timeline), so a resumed project is described by
    what was actually spoken rather than by the plan.
    """
    raw_scenes = [scene for scene in (data.get("scenes") or []) if isinstance(scene, dict)]
    fallback_roles = infer_roles(len(raw_scenes))
    scenes: list[ScriptScene] = []
    for index, raw in enumerate(raw_scenes):
        role = str(raw.get("role") or (fallback_roles[index] if index < len(fallback_roles) else SCENE_ROLE_DEVELOPMENT))
        duration = _float(raw.get("actual_duration_sec")) or _float(raw.get("target_duration_sec"))
        scenes.append(
            ScriptScene(
                scene_id=str(raw.get("scene_id") or f"scene_{index + 1:03d}"),
                index=index + 1,
                role=role if role in {SCENE_ROLE_HOOK, SCENE_ROLE_DEVELOPMENT, SCENE_ROLE_PAYOFF, SCENE_ROLE_CTA} else SCENE_ROLE_DEVELOPMENT,
                narration=str(raw.get("narration") or ""),
                duration_sec=duration,
                start_sec=_float(raw.get("start_sec")),
                on_screen_text=str(raw.get("on_screen_text") or ""),
                visual_intent=str(raw.get("visual_intent") or ""),
                emotion=str(raw.get("emotion") or ""),
                keywords=[str(item) for item in (raw.get("keywords") or [])],
                claim_ids=[str(item) for item in (raw.get("claim_ids") or [])],
                source_refs=[str(item) for item in (raw.get("source_refs") or [])],
                pause_after_sec=raw.get("pause_after_sec"),
                visual_brief=dict(raw.get("visual_brief") or {}),
            )
        )
    return ScriptResult(
        scenes=scenes,
        title=str(data.get("title") or ""),
        hook=str(data.get("hook") or ""),
        description=str(data.get("description") or ""),
        language=str(data.get("language") or ""),
        source_kind=str(data.get("source_kind") or SOURCE_RESEARCH),
        provider_id=str(data.get("script_provider") or ""),
        provider_version=str(data.get("script_provider_version") or ""),
        target_duration_sec=_float(data.get("target_duration_sec")),
        source_claim_ids=[str(item) for item in (data.get("source_claim_ids") or [])],
        warnings=[str(item) for item in (data.get("script_warnings") or [])],
        metadata=dict(data.get("script_metadata") or {}),
        schema_version=int(data.get("script_schema_version") or 1),
    )


__all__ = [
    "LEGACY_SCENE_KEYS",
    "LEGACY_TOP_LEVEL_KEYS",
    "SCRIPT_SCHEMA_VERSION",
    "from_legacy_script",
    "infer_roles",
    "scene_to_legacy",
    "to_legacy_script",
]
