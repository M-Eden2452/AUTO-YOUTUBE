from __future__ import annotations

from typing import Any


def refine_candidate_boundaries(
    candidate: dict[str, Any],
    transcript: list[dict[str, Any]],
    audio_features: list[dict[str, Any]],
    scene_cuts: list[dict[str, Any]],
    trim_silence: bool = False,
    use_scene_cuts: bool = False,
) -> dict[str, Any]:
    refined = dict(candidate)
    original_start = float(candidate["start"])
    original_end = float(candidate["end"])
    start = original_start
    end = original_end
    reasons: list[str] = []

    overlapping = [
        segment
        for segment in transcript
        if float(segment.get("end", 0.0)) > original_start and float(segment.get("start", 0.0)) < original_end
    ]
    if overlapping:
        first = overlapping[0]
        last = overlapping[-1]
        first_start = float(first["start"])
        last_end = float(last["end"])
        if first_start < start < float(first["end"]):
            start = first_start
            reasons.append("start перенесен к началу реплики")
        if float(last["start"]) < end < last_end:
            end = last_end
            reasons.append("end перенесен к концу реплики")
        refined["subtitle_segments"] = [
            {"start": round(float(segment["start"]), 2), "end": round(float(segment["end"]), 2), "text": str(segment["text"]).strip()}
            for segment in overlapping
        ]

    if trim_silence:
        start, end, silence_reasons = _trim_edge_silence(start, end, overlapping, audio_features)
        reasons.extend(silence_reasons)

    if use_scene_cuts and scene_cuts:
        start, end, scene_reasons = _snap_to_scene_cuts(start, end, scene_cuts)
        reasons.extend(scene_reasons)

    refined["original_start"] = round(original_start, 2)
    refined["original_end"] = round(original_end, 2)
    refined["refined_start"] = round(start, 2)
    refined["refined_end"] = round(end, 2)
    refined["start"] = round(start, 2)
    refined["end"] = round(end, 2)
    refined["duration"] = round(max(0.0, end - start), 2)
    refined["boundary_reason"] = reasons or ["границы оставлены без изменений"]
    return refined


def refine_candidates(
    candidates: list[dict[str, Any]],
    transcript: list[dict[str, Any]],
    audio_features: list[dict[str, Any]],
    scene_cuts: list[dict[str, Any]],
    trim_silence: bool = False,
    use_scene_cuts: bool = False,
) -> list[dict[str, Any]]:
    return [
        refine_candidate_boundaries(candidate, transcript, audio_features, scene_cuts, trim_silence, use_scene_cuts)
        for candidate in candidates
    ]


def _trim_edge_silence(
    start: float,
    end: float,
    overlapping: list[dict[str, Any]],
    audio_features: list[dict[str, Any]],
) -> tuple[float, float, list[str]]:
    reasons: list[str] = []
    if overlapping:
        speech_start = float(overlapping[0]["start"])
        speech_end = float(overlapping[-1]["end"])
        if speech_start - start > 0.4:
            start = speech_start
            reasons.append("тишина в начале обрезана")
        if end - speech_end > 0.4:
            end = speech_end
            reasons.append("тишина в конце обрезана")
    loud = [
        item
        for item in audio_features
        if float(item.get("end", 0.0)) > start and float(item.get("start", 0.0)) < end and float(item.get("loudness", 0.0)) > 0.08
    ]
    if loud:
        first_loud = float(loud[0]["start"])
        last_loud = float(loud[-1]["end"])
        if first_loud - start > 0.5:
            start = first_loud
            reasons.append("тихое начало обрезано по audio")
        if end - last_loud > 0.5:
            end = last_loud
            reasons.append("тихий конец обрезан по audio")
    return start, end, reasons


def _snap_to_scene_cuts(start: float, end: float, scene_cuts: list[dict[str, Any]]) -> tuple[float, float, list[str]]:
    reasons: list[str] = []
    nearby_start = _nearest_cut(start, scene_cuts, max_distance=1.5)
    nearby_end = _nearest_cut(end, scene_cuts, max_distance=1.5)
    if nearby_start is not None:
        start = nearby_start
        reasons.append("start привязан к scene cut")
    if nearby_end is not None and nearby_end > start:
        end = nearby_end
        reasons.append("end привязан к scene cut")
    return start, end, reasons


def _nearest_cut(time: float, scene_cuts: list[dict[str, Any]], max_distance: float) -> float | None:
    times = [float(cut["time"]) for cut in scene_cuts]
    if not times:
        return None
    nearest = min(times, key=lambda item: abs(item - time))
    return nearest if abs(nearest - time) <= max_distance else None
