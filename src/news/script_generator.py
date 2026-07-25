from __future__ import annotations

from typing import Any

from .models import NewsJob


EMOTIONS = ["intrigue", "context", "discovery", "explanation", "detail", "question"]


def build_script(job: NewsJob, research: dict[str, Any]) -> dict[str, Any]:
    claims = [claim for claim in research.get("claims", []) if claim.get("safe_for_script", True)]
    title = research.get("topic") or job.topic or "Научная новость"
    hook = _make_hook(title)
    scene_texts = _build_scene_texts(hook, claims, title)
    scenes = []
    target_durations = [3.5, 7.0, 10.0, 13.0, 10.0, 8.0]
    start = 0.0
    for index, narration in enumerate(scene_texts, start=1):
        duration = target_durations[min(index - 1, len(target_durations) - 1)]
        claim_ids = [claims[min(index - 1, len(claims) - 1)]["claim_id"]] if claims else []
        scenes.append(
            {
                "scene_id": f"scene_{index:03d}",
                "start_sec": round(start, 2),
                "target_duration_sec": duration,
                "narration": narration,
                "claim_ids": claim_ids,
                "visual_intent": _visual_intent(narration),
                "on_screen_text": _screen_text(narration),
                "emotion": EMOTIONS[min(index - 1, len(EMOTIONS) - 1)],
            }
        )
        start += duration
    narration_text = "\n".join(scene["narration"] for scene in scenes)
    return {
        "title": title,
        "hook": hook,
        "language": job.language,
        "target_duration_sec": job.target_duration_sec,
        "estimated_duration_sec": round(sum(scene["target_duration_sec"] for scene in scenes), 2),
        "narration_text": narration_text,
        "description": f"Короткий научный ролик: {title}",
        "source_claim_ids": [claim["claim_id"] for claim in claims],
        "scenes": scenes,
    }


def _make_hook(title: str) -> str:
    clean = title.strip().rstrip(".?!")
    if clean.startswith("Почему"):
        return f"{clean}?"
    return f"{clean}: что здесь самое необычное?"


def _build_scene_texts(hook: str, claims: list[dict[str, Any]], title: str) -> list[str]:
    claim_texts = [claim.get("text", "") for claim in claims if claim.get("text")]
    while len(claim_texts) < 5:
        claim_texts.append(title)
    return [
        hook,
        f"Наблюдение выглядит простым, но за ним стоит важная деталь: {claim_texts[0]}",
        f"Исследователи связывают историю с проверяемыми фактами: {claim_texts[1]}",
        _cautious_sentence(claims[2] if len(claims) > 2 else claims[0] if claims else None, claim_texts[2]),
        f"Главное здесь не эффектная картинка, а то, как меняется наше понимание темы: {claim_texts[3]}",
        "И пока появляются новые данные, самый интересный вопрос остается открытым: что мы упускаем в этой истории?",
    ]


def _cautious_sentence(claim: dict[str, Any] | None, text: str) -> str:
    if claim and claim.get("claim_type") in {"hypothesis", "interpretation", "uncertain"}:
        return f"Но это не доказанный факт: ученые предполагают, что {text}"
    return f"Основное объяснение звучит осторожно и без преувеличений: {text}"


def _visual_intent(narration: str) -> str:
    return narration[:160]


def _screen_text(narration: str) -> str:
    words = narration.replace(":", "").split()
    return " ".join(words[:5])

