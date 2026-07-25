from __future__ import annotations

import re
from typing import Any


CONTEXT_PRONOUNS = {"он", "она", "это", "они", "тогда", "там", "его", "ее", "её", "he", "she", "it", "they", "then"}


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[A-Za-zА-Яа-яЁё]+", text.lower())


def _audio_values(audio_features: list[dict[str, Any]], start: float, end: float) -> list[float]:
    return [
        float(item.get("loudness", 0.0))
        for item in audio_features
        if float(item.get("end", 0.0)) > start and float(item.get("start", 0.0)) < end
    ]


def _audio_score(audio_features: list[dict[str, Any]], start: float, end: float) -> float:
    values = _audio_values(audio_features, start, end)
    if not values:
        return 0.0
    return min(1.0, (sum(values) / len(values)) * 0.7 + max(values) * 0.3)


def _duration_score(duration: float, min_duration: float, max_duration: float, target: float) -> float:
    if duration < min_duration or duration > max_duration:
        return 0.0
    spread = max(target - min_duration, max_duration - target, 1.0)
    return max(0.0, 1.0 - abs(duration - target) / spread)


def _overlap_ratio(left: dict[str, Any], right: dict[str, Any]) -> float:
    start = max(float(left["start"]), float(right["start"]))
    end = min(float(left["end"]), float(right["end"]))
    overlap = max(0.0, end - start)
    shorter = min(float(left["duration"]), float(right["duration"]))
    return overlap / shorter if shorter > 0 else 0.0


def _hook_score(segments: list[dict[str, Any]], emotional_words: set[str], start: float) -> float:
    early_text = " ".join(
        str(segment.get("text", ""))
        for segment in segments
        if float(segment.get("start", 0.0)) < start + 3.0
    )
    words = _tokenize(early_text)
    score = 0.0
    if "?" in early_text or "!" in early_text:
        score += 0.35
    if any(word in emotional_words for word in words):
        score += 0.45
    if len(words) >= 3:
        score += 0.2
    return min(1.0, score)


def _payoff_score(
    segments: list[dict[str, Any]],
    audio_features: list[dict[str, Any]],
    emotional_words: set[str],
    start: float,
    end: float,
) -> float:
    tail_start = start + (end - start) * 0.65
    tail_text = " ".join(str(segment.get("text", "")) for segment in segments if float(segment.get("end", 0.0)) >= tail_start)
    words = _tokenize(tail_text)
    score = 0.0
    if "?" in tail_text or "!" in tail_text:
        score += 0.25
    if any(word in emotional_words for word in words):
        score += 0.3
    tail_audio = _audio_score(audio_features, tail_start, end)
    score += tail_audio * 0.45
    return min(1.0, score)


def _context_score(segments: list[dict[str, Any]]) -> tuple[float, list[str]]:
    first_words = _tokenize(str(segments[0].get("text", "")))[:3]
    if first_words and first_words[0] in CONTEXT_PRONOUNS:
        return -0.35, ["начало может требовать контекст"]
    return 0.0, []


def _silence_penalty(speech_seconds: float, duration: float) -> float:
    silence_ratio = max(0.0, 1.0 - speech_seconds / max(duration, 1.0))
    return -min(0.35, silence_ratio * 0.5)


def _score_window(
    segments: list[dict[str, Any]],
    audio_features: list[dict[str, Any]],
    config: dict[str, Any],
    min_duration: float,
    max_duration: float,
) -> dict[str, Any] | None:
    start = float(segments[0]["start"])
    end = float(segments[-1]["end"])
    duration = round(end - start, 2)
    text = " ".join(str(segment.get("text", "")).strip() for segment in segments).strip()
    min_text_chars = int(config.get("candidate_scoring", {}).get("min_text_chars", 35))
    if duration < min_duration or duration > max_duration or len(text) < min_text_chars:
        return None

    speech_seconds = sum(max(0.0, float(segment["end"]) - float(segment["start"])) for segment in segments)
    speech_density = min(1.0, speech_seconds / max(duration, 1.0))
    words = _tokenize(text)
    emotional_words = {word.lower() for word in config.get("emotional_words", [])}
    emotional_hits = sum(1 for word in words if word in emotional_words)
    emotional_score = min(1.0, emotional_hits / 3.0)
    punctuation_hits = text.count("!") + text.count("?") + text.count("?!") + text.count("!?")
    punctuation_score = min(1.0, punctuation_hits / 3.0)
    audio_energy_score = _audio_score(audio_features, start, end)
    hook = _hook_score(segments, emotional_words, start)
    payoff = _payoff_score(segments, audio_features, emotional_words, start, end)
    context, warnings = _context_score(segments)
    silence_penalty = _silence_penalty(speech_seconds, duration)
    target_duration = float(config.get("candidate_scoring", {}).get("target_duration", (min_duration + max_duration) / 2))
    duration_fit = _duration_score(duration, min_duration, max_duration, target_duration)

    score = (
        speech_density * 0.18
        + emotional_score * 0.16
        + punctuation_score * 0.08
        + audio_energy_score * 0.16
        + duration_fit * 0.16
        + hook * 0.10
        + payoff * 0.14
        + context
        + silence_penalty
    )
    score = max(0.0, min(1.0, score))

    reasons: list[str] = []
    if hook >= 0.5:
        reasons.append("сильный хук в начале")
    if speech_density >= 0.55:
        reasons.append("плотная речь")
    if emotional_hits:
        reasons.append("эмоциональные слова")
        reasons.append("эмоциональная реплика")
    if punctuation_score > 0:
        reasons.append("вопросы или восклицания")
    if audio_energy_score >= float(config.get("candidate_scoring", {}).get("audio_peak_threshold", 0.65)):
        reasons.append("аудио пик")
    if payoff >= 0.55:
        reasons.append("аудио пик ближе к концу")
    if duration_fit >= 0.65:
        reasons.append("хорошая длина")
    if not reasons:
        reasons.append("сбалансированный фрагмент")

    return {
        "start": round(start, 2),
        "end": round(end, 2),
        "original_start": round(start, 2),
        "original_end": round(end, 2),
        "duration": duration,
        "score": round(float(score), 4),
        "score_breakdown": {
            "speech_density": round(speech_density, 4),
            "emotional_words": round(emotional_score, 4),
            "punctuation": round(punctuation_score, 4),
            "audio_energy": round(audio_energy_score, 4),
            "duration": round(duration_fit, 4),
            "hook": round(hook, 4),
            "payoff": round(payoff, 4),
            "context": round(context, 4),
            "silence_penalty": round(silence_penalty, 4),
        },
        "reason": reasons,
        "warnings": warnings,
        "subtitle_segments": [
            {"start": round(float(segment["start"]), 2), "end": round(float(segment["end"]), 2), "text": str(segment["text"]).strip()}
            for segment in segments
            if str(segment.get("text", "")).strip()
        ],
    }


def find_candidates(
    transcript: list[dict[str, Any]],
    audio_features: list[dict[str, Any]],
    config: dict[str, Any],
    max_clips: int = 10,
    min_duration: float = 20,
    max_duration: float = 45,
) -> list[dict[str, Any]]:
    windows: list[dict[str, Any]] = []
    ordered = sorted(transcript, key=lambda item: float(item.get("start", 0.0)))
    for start_index in range(len(ordered)):
        collected: list[dict[str, Any]] = []
        for segment in ordered[start_index:]:
            collected.append(segment)
            duration = float(collected[-1]["end"]) - float(collected[0]["start"])
            if duration > max_duration:
                break
            if duration >= min_duration:
                candidate = _score_window(collected, audio_features, config, min_duration, max_duration)
                if candidate:
                    windows.append(candidate)

    windows.sort(key=lambda item: float(item["score"]), reverse=True)
    selected: list[dict[str, Any]] = []
    overlap_threshold = float(config.get("candidate_scoring", {}).get("overlap_threshold", 0.55))
    for window in windows:
        overlapping_index = next(
            (index for index, existing in enumerate(selected) if _overlap_ratio(window, existing) >= overlap_threshold),
            None,
        )
        if overlapping_index is not None:
            existing = selected[overlapping_index]
            score_gap = float(existing["score"]) - float(window["score"])
            if float(window["start"]) < float(existing["start"]) and score_gap <= 0.08:
                selected[overlapping_index] = window
            continue
        selected.append(window)
        if len(selected) >= max_clips:
            break

    for index, candidate in enumerate(selected, start=1):
        candidate["id"] = index
    return selected
