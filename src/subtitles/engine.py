"""Единый движок субтитров: ``SubtitleRequest`` → проверенные ``SubtitleCue``.

Что движок делает: берёт уже готовый сценарий, уже посчитанный этапом B1 timeline
и уже разрешённую локализацию, режет текст, расставляет время, проверяет результат.

Что он не делает и делать не должен: не синтезирует речь, не переводит текст, не
зовёт LLM, не распознаёт речь, не выравнивает по словам, не скачивает модели, не
рендерит, не ходит в сеть, не меняет визуальный план и не выбирает ассеты. Всё,
что здесь есть, - чистая арифметика и работа со строками.
"""

from __future__ import annotations

import hashlib
from typing import Any

from .models import (
    SUPPORTED_FORMATS,
    TIMING_SOURCE_UNAVAILABLE,
    SubtitleRequest,
    SubtitleResult,
    SubtitleSegment,
    SubtitleValidationResult,
    ERR_MISSING_SCRIPT,
    ERR_NO_SCENES,
    error,
    warning,
    WARN_MISSING_SCENE_PLAN,
)
from .segmentation import scene_text, split_scene_text
from .timing import build_cues, resolve_scene_spans
from .validation import merge, validate_cues


def script_fingerprint(script: dict[str, Any]) -> str:
    """Отпечаток текстовой части сценария.

    Считается по тому, что действительно влияет на субтитры: язык и упорядоченная
    пара ``scene_id`` + произносимый текст. Правка визуального интента или
    ключевых слов субтитры не меняет и не должна вызывать перегенерацию.
    """
    parts = [str(script.get("language") or "")]
    for scene in script.get("scenes") or []:
        if not isinstance(scene, dict):
            continue
        parts.append(str(scene.get("scene_id") or ""))
        parts.append(str(scene.get("narration") or ""))
        parts.append(str(scene.get("on_screen_text") or ""))
    return hashlib.sha256("␟".join(parts).encode("utf-8")).hexdigest()[:32]


def narration_fingerprint(*, narration_path: str, duration_sec: float, timing_source: str) -> str:
    """Отпечаток озвучки: путь, длительность и уровень точности тайминга.

    Аудиофайл не открывается и не хешируется - это дорого и не нужно: другая
    озвучка всегда даёт другую длительность или другой путь, а смена уровня
    тайминга (появились потайминги слов) обязана перестроить субтитры.
    """
    payload = f"{narration_path}|{duration_sec:.3f}|{timing_source}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]


def _narration_from_manifest(voice_manifest: dict[str, Any] | None) -> tuple[str, float]:
    manifest = voice_manifest or {}
    narration = manifest.get("narration") if isinstance(manifest.get("narration"), dict) else {}
    path = str(narration.get("output_path") or manifest.get("audio_path") or "")
    duration = narration.get("duration_sec") or manifest.get("duration_sec") or 0.0
    try:
        return path, max(0.0, float(duration))
    except (TypeError, ValueError):
        return path, 0.0


def build_subtitle_result(request: SubtitleRequest) -> SubtitleResult:
    """Собрать и проверить субтитры одной локализации. Ничего не пишет на диск."""
    script = request.script or {}
    language = request.effective_language
    policy = request.policy
    style = request.style
    extra: list[Any] = []

    if not script:
        return _empty_result(request, [error(ERR_MISSING_SCRIPT, "Сценарий не передан.")])
    raw_scenes = [scene for scene in (script.get("scenes") or []) if isinstance(scene, dict)]
    if not raw_scenes:
        return _empty_result(request, [error(ERR_NO_SCENES, "В сценарии нет сцен.")])

    narration_path, manifest_duration = _narration_from_manifest(request.voice_manifest)
    plan = resolve_scene_spans(
        script,
        voice_manifest=request.voice_manifest,
        format_id=request.format_id,
        narration_duration_sec=request.narration_duration_sec or manifest_duration,
    )

    scene_texts: dict[str, str] = {}
    segments_by_scene: dict[str, list[SubtitleSegment]] = {}
    planned_ids = plan.by_scene_id()
    for index, scene in enumerate(raw_scenes):
        scene_id = str(scene.get("scene_id") or f"scene_{index + 1:03d}")
        text, source_field = scene_text(scene, policy)
        if not text:
            continue
        if scene_id not in planned_ids:
            # Сцена есть в сценарии, но не попала в timeline: она не озвучена. Молча
            # её выбросить нельзя - иначе часть текста исчезнет без объяснения.
            extra.append(
                warning(WARN_MISSING_SCENE_PLAN, f"{scene_id}: сцены нет в timeline озвучки, субтитров не будет.",
                        scene_id=scene_id)
            )
            continue
        scene_texts[scene_id] = text
        segments_by_scene[scene_id] = split_scene_text(
            text,
            scene_id=scene_id,
            scene_index=index,
            source_field=source_field,
            policy=policy,
        )

    cues = build_cues(segments_by_scene, scene_texts, plan, language=language)
    validation = merge(
        validate_cues(
            cues,
            policy=policy,
            language=language,
            scene_order=tuple(str(scene.get("scene_id") or "") for scene in raw_scenes),
            scene_bounds={span.scene_id: (span.start_sec, span.end_sec) for span in plan.spans},
            scene_texts=scene_texts,
            narration_duration_sec=plan.narration_duration_sec,
        ),
        SubtitleValidationResult(tuple(extra)),
    )
    return SubtitleResult(
        cues=cues,
        language=language,
        localization_id=request.localization_id or language,
        timing_source=plan.timing_source,
        validation=validation,
        policy=policy,
        style=style,
        narration_path=request.narration_path or narration_path,
        narration_duration_sec=plan.narration_duration_sec,
        scene_timeline_source=plan.timeline_source,
        script_fingerprint=script_fingerprint(script),
        narration_fingerprint=narration_fingerprint(
            narration_path=request.narration_path or narration_path,
            duration_sec=plan.narration_duration_sec,
            timing_source=plan.timing_source,
        ),
        scene_count=len(plan.spans) or len(raw_scenes),
        formats=tuple(request.formats or SUPPORTED_FORMATS),
        warnings=tuple(plan.warnings),
    )


def _empty_result(request: SubtitleRequest, issues: list[Any]) -> SubtitleResult:
    return SubtitleResult(
        cues=(),
        language=request.effective_language,
        localization_id=request.localization_id or request.effective_language,
        timing_source=TIMING_SOURCE_UNAVAILABLE,
        validation=SubtitleValidationResult(tuple(issues)),
        policy=request.policy,
        style=request.style,
        formats=tuple(request.formats or SUPPORTED_FORMATS),
    )


def explain_scene_mapping(result: SubtitleResult) -> list[dict[str, Any]]:
    """«сцена → её cues» для CLI и отчётов. Без рендера и без записи."""
    rows: list[dict[str, Any]] = []
    for scene_id, cues in result.cues_by_scene().items():
        rows.append(
            {
                "scene_id": scene_id,
                "cue_count": len(cues),
                "start_sec": round(cues[0].start_sec, 3),
                "end_sec": round(cues[-1].end_sec, 3),
                "timing_source": cues[0].timing_source,
                "cues": [cue.to_dict() for cue in cues],
            }
        )
    return rows


__all__ = [
    "build_subtitle_result",
    "explain_scene_mapping",
    "narration_fingerprint",
    "script_fingerprint",
]
