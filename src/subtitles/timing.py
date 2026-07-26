"""Откуда берётся время субтитра. Только арифметика над уже готовыми данными.

Иерархия источников - от точного к безопасному:

1. ``word_timestamps`` - потайминги отдельных слов из voice manifest. **Ни один
   модуль репозитория их сегодня не пишет** (проверено поиском по ``src/``), и
   выдумывать их движок субтитров не будет: этот уровень включается только если
   данные физически лежат в манифесте и их количество совпадает с количеством
   слов сцены. Whisper, forced alignment и любые модели - вне Q3.
2. ``segment_timestamps`` - потайминги фраз, если провайдер их вернул. Те же
   условия: используются только при фактическом наличии.
3. ``scene_timeline`` - основной рабочий уровень. Границы сцен приходят из
   ``src.audio.scene_timeline`` (этап B1): либо из voice manifest напрямую, либо
   из ``actual_duration_sec``, который тот же B1 уже записал в ``script.json``.
   Второго расчёта длительностей здесь нет.
4. ``legacy_planned`` - только плановый ``target_duration_sec`` старого проекта.
   Помечается как legacy и по умолчанию для новых проектов не выбирается, потому
   что появляется лишь тогда, когда реальной озвучки нет вообще.

Текст сцены раскладывается внутри её *речевого* отрезка: пауза между сценами
остаётся без субтитра, иначе последняя реплика висит в тишине.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from src.audio.scene_timeline import SceneTimeline, build_scene_timeline, scene_render_duration

from .models import (
    TIMING_SOURCE_LEGACY_PLANNED,
    TIMING_SOURCE_SCENE_TIMELINE,
    TIMING_SOURCE_SEGMENT,
    TIMING_SOURCE_UNAVAILABLE,
    TIMING_SOURCE_WORD,
    TIMING_SOURCE_PRECISION,
    SubtitleCue,
    SubtitleSegment,
)
from .segmentation import tokenize

# Минимальная длительность одного cue, которую движок вообще может выдать. Не
# политика, а защита от нулевых и отрицательных интервалов в SRT/ASS.
MIN_CUE_SEC = 0.04


@dataclass(frozen=True)
class SceneSpan:
    """Границы одной сцены на общей оси видео."""

    scene_id: str
    scene_index: int
    start_sec: float
    end_sec: float
    speech_end_sec: float
    timing_source: str = TIMING_SOURCE_SCENE_TIMELINE
    # Локальные (от начала сцены) потайминги, если провайдер их дал.
    word_times: tuple[tuple[float, float], ...] = ()
    segment_times: tuple[tuple[float, float], ...] = ()

    @property
    def speech_duration_sec(self) -> float:
        return max(0.0, self.speech_end_sec - self.start_sec)


@dataclass(frozen=True)
class SceneTimingPlan:
    spans: tuple[SceneSpan, ...] = ()
    timing_source: str = TIMING_SOURCE_UNAVAILABLE
    timeline_source: str = "unavailable"
    narration_duration_sec: float = 0.0
    warnings: tuple[str, ...] = ()

    def by_scene_id(self) -> dict[str, SceneSpan]:
        return {span.scene_id: span for span in self.spans}


def _finite(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _local_intervals(entries: Any) -> tuple[tuple[float, float], ...]:
    """``[{start, end}, ...]`` → упорядоченные локальные интервалы.

    Возвращает пустой кортеж при любой некорректности: пропущенное поле, не
    число, NaN, конец раньше начала, нарушенный порядок. Частично разобранным
    данным доверять нельзя - это привело бы к субтитрам, «почти» совпадающим с
    голосом, что хуже честного отката на уровень сцены.
    """
    if not isinstance(entries, list) or not entries:
        return ()
    intervals: list[tuple[float, float]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            return ()
        start = _finite(entry.get("start_sec", entry.get("start")))
        end = _finite(entry.get("end_sec", entry.get("end")))
        if start is None or end is None or end <= start or start < 0:
            return ()
        if intervals and start < intervals[-1][0]:
            return ()
        intervals.append((start, end))
    return tuple(intervals)


def _manifest_scene_entries(voice_manifest: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    scenes = (voice_manifest or {}).get("scenes")
    if not isinstance(scenes, list):
        return {}
    return {str(entry.get("scene_id", "")): entry for entry in scenes if isinstance(entry, dict)}


def _span_from_timeline(
    timing: Any,
    entry: dict[str, Any],
    scene_text_token_count: int,
) -> SceneSpan:
    """Одна сцена: границы из B1 + повышение точности, если данные реально есть."""
    speech = float(timing.speech_duration_sec or 0.0)
    speech_end = timing.start_sec + (speech if speech > 0 else timing.duration_sec)
    words = _local_intervals(entry.get("word_timestamps"))
    segments = _local_intervals(entry.get("segment_timestamps") or entry.get("segments"))
    source = TIMING_SOURCE_SCENE_TIMELINE
    if words and scene_text_token_count and len(words) == scene_text_token_count:
        source = TIMING_SOURCE_WORD
    else:
        words = ()
        if segments:
            source = TIMING_SOURCE_SEGMENT
    return SceneSpan(
        scene_id=timing.scene_id,
        scene_index=timing.scene_index,
        start_sec=timing.start_sec,
        end_sec=timing.end_sec,
        speech_end_sec=min(speech_end, timing.end_sec),
        timing_source=source,
        word_times=words,
        segment_times=segments if source == TIMING_SOURCE_SEGMENT else (),
    )


def _spans_from_script(script: dict[str, Any]) -> tuple[tuple[SceneSpan, ...], str, list[str]]:
    """Границы сцен по самому ``script.json``, когда voice manifest не передан.

    ``actual_duration_sec`` пишет тот же B1 (``apply_timeline_to_script``), поэтому
    это не второй расчёт, а чтение его результата. Длительность берётся через общий
    ``scene_render_duration`` - тем же вызовом, что у ``final_renderer``.
    """
    scenes = [scene for scene in (script.get("scenes") or []) if isinstance(scene, dict)]
    if not scenes:
        return (), TIMING_SOURCE_UNAVAILABLE, ["script has no scenes"]
    real = any(_finite(scene.get("actual_duration_sec")) for scene in scenes)
    source = TIMING_SOURCE_SCENE_TIMELINE if real else TIMING_SOURCE_LEGACY_PLANNED
    warnings: list[str] = []
    if not real:
        warnings.append("script has no actual_duration_sec; planned durations are used (legacy timing)")
    spans: list[SceneSpan] = []
    cursor = 0.0
    for index, scene in enumerate(scenes):
        scene_id = str(scene.get("scene_id") or f"scene_{index + 1:03d}")
        declared_start = _finite(scene.get("start_sec"))
        # Плановый start_sec старых сценариев не всегда согласован с длительностями;
        # доверяем ему только если он не уводит сцены назад по времени.
        start = declared_start if declared_start is not None and declared_start >= cursor - 1e-6 else cursor
        duration = scene_render_duration(scene, minimum_sec=MIN_CUE_SEC, fallback_sec=3.0)
        pause = _finite(scene.get("pause_after_sec")) or 0.0
        speech = _finite(scene.get("speech_duration_sec"))
        speech_end = start + (speech if speech and speech > 0 else max(MIN_CUE_SEC, duration - pause))
        spans.append(
            SceneSpan(
                scene_id=scene_id,
                scene_index=index,
                start_sec=start,
                end_sec=start + duration,
                speech_end_sec=min(speech_end, start + duration),
                timing_source=source,
            )
        )
        cursor = start + duration
    return tuple(spans), source, warnings


def resolve_scene_spans(
    script: dict[str, Any],
    *,
    voice_manifest: dict[str, Any] | None = None,
    format_id: str = "",
    narration_duration_sec: float = 0.0,
) -> SceneTimingPlan:
    """Границы всех сцен и фактический источник тайминга.

    Никогда не бросает исключение: при полном отсутствии данных возвращает пустой
    план с ``timing_source=unavailable``, и вызывающий сам решает, это ожидание
    озвучки или ошибка.
    """
    timeline: SceneTimeline | None = None
    if voice_manifest:
        timeline = build_scene_timeline(voice_manifest, script=script, format_id=format_id)
    warnings: list[str] = []
    if timeline:
        entries = _manifest_scene_entries(voice_manifest)
        token_counts = {
            str(scene.get("scene_id") or ""): len(tokenize(str(scene.get("narration") or "")))
            for scene in (script.get("scenes") or [])
            if isinstance(scene, dict)
        }
        spans = tuple(
            _span_from_timeline(timing, entries.get(timing.scene_id, {}), token_counts.get(timing.scene_id, 0))
            for timing in timeline.scenes
        )
        source = min(
            (span.timing_source for span in spans),
            key=lambda name: TIMING_SOURCE_PRECISION.get(name, 0),
            default=TIMING_SOURCE_SCENE_TIMELINE,
        )
        return SceneTimingPlan(
            spans=spans,
            timing_source=source,
            timeline_source=timeline.source,
            narration_duration_sec=narration_duration_sec or timeline.narration_duration_sec,
            warnings=tuple(timeline.warnings),
        )
    if voice_manifest:
        warnings.append("voice_manifest gave no usable timeline; script durations are used instead")
    spans, source, script_warnings = _spans_from_script(script)
    warnings.extend(script_warnings)
    total = spans[-1].end_sec if spans else 0.0
    return SceneTimingPlan(
        spans=spans,
        timing_source=source,
        timeline_source="script" if spans else "unavailable",
        narration_duration_sec=narration_duration_sec or total,
        warnings=tuple(warnings),
    )


def _token_range(segment: SubtitleSegment, tokens: list[tuple[str, int, int]]) -> tuple[int, int]:
    first = next(
        (index for index, token in enumerate(tokens) if token[1] >= segment.char_start),
        0,
    )
    last = first
    for index in range(first, len(tokens)):
        if tokens[index][2] <= segment.char_end:
            last = index
        else:
            break
    return first, last


def _cue_bounds_from_words(
    segment: SubtitleSegment,
    tokens: list[tuple[str, int, int]],
    span: SceneSpan,
) -> tuple[float, float]:
    first, last = _token_range(segment, tokens)
    start_local, _ = span.word_times[min(first, len(span.word_times) - 1)]
    _, end_local = span.word_times[min(last, len(span.word_times) - 1)]
    return span.start_sec + start_local, span.start_sec + end_local


def _proportional_bounds(
    segments: list[SubtitleSegment],
    span: SceneSpan,
) -> list[tuple[float, float]]:
    """Разложить куски внутри речевого отрезка сцены пропорционально их длине.

    Куски идут вплотную и точно заполняют отрезок: последний cue заканчивается
    ровно на ``speech_end_sec``, поэтому пересечений и выхода за сцену не бывает
    по построению.
    """
    total_weight = sum(segment.weight for segment in segments) or 1.0
    available = max(MIN_CUE_SEC * len(segments), span.speech_duration_sec)
    bounds: list[tuple[float, float]] = []
    cursor = span.start_sec
    for position, segment in enumerate(segments):
        if position == len(segments) - 1:
            end = span.start_sec + available
        else:
            end = cursor + available * (segment.weight / total_weight)
        end = max(end, cursor + MIN_CUE_SEC)
        bounds.append((cursor, end))
        cursor = end
    return bounds


def build_cues(
    segments_by_scene: dict[str, list[SubtitleSegment]],
    scene_texts: dict[str, str],
    plan: SceneTimingPlan,
    *,
    language: str,
) -> tuple[SubtitleCue, ...]:
    """Собрать cues в порядке сцен плана. Порядок ``scene_id`` = порядок сценария."""
    cues: list[SubtitleCue] = []
    index = 0
    for span in plan.spans:
        segments = segments_by_scene.get(span.scene_id) or []
        if not segments:
            continue
        tokens = tokenize(scene_texts.get(span.scene_id, ""))
        if span.timing_source == TIMING_SOURCE_WORD and span.word_times:
            bounds = [_cue_bounds_from_words(segment, tokens, span) for segment in segments]
        elif span.timing_source == TIMING_SOURCE_SEGMENT and len(span.segment_times) == len(segments):
            bounds = [
                (span.start_sec + start, span.start_sec + end) for start, end in span.segment_times
            ]
        else:
            bounds = _proportional_bounds(segments, span)
        for position, (segment, (start, end)) in enumerate(zip(segments, bounds, strict=True), start=1):
            # Ни один cue не выходит за свою сцену - ограничение стоит здесь, а не
            # в валидаторе, чтобы такой артефакт вообще не мог попасть на диск.
            start = min(max(start, span.start_sec), span.end_sec)
            end = min(max(end, start + MIN_CUE_SEC), span.end_sec)
            index += 1
            cues.append(
                SubtitleCue(
                    cue_id=f"{span.scene_id}#{position:02d}",
                    scene_id=span.scene_id,
                    index=index,
                    scene_cue_index=position,
                    text=segment.text,
                    start_sec=round(start, 3),
                    end_sec=round(end, 3),
                    language=language,
                    timing_source=span.timing_source,
                    source_field=segment.source_field,
                    source_char_start=segment.char_start,
                    source_char_end=segment.char_end,
                )
            )
    return tuple(cues)


__all__ = [
    "MIN_CUE_SEC",
    "SceneSpan",
    "SceneTimingPlan",
    "build_cues",
    "resolve_scene_spans",
]
