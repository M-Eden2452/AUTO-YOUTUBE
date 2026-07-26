"""The pre-engine generator, preserved verbatim behind the provider contract.

This is the six fixed phrases and the ``[3.5, 7.0, 10.0, 13.0, 10.0, 8.0]``
duration table that every video used to be built from. It is kept - unchanged,
not "roughly equivalent" - for exactly two reasons:

1. it is the reference the regression tests compare the engine against, so any
   future change to the storage format is caught on known output;
2. a project made with it can be reproduced.

It is no longer the default. ``deterministic_local`` is.
"""

from __future__ import annotations

from typing import Any

from ..contract import BaseScriptProvider, ScriptProviderCapabilities
from ..models import (
    SCENE_ROLE_DEVELOPMENT,
    SCENE_ROLE_HOOK,
    SCENE_ROLE_PAYOFF,
    SOURCE_KINDS,
    ScriptRequest,
    ScriptResult,
    ScriptScene,
)

PROVIDER_ID = "legacy_template"

# Verbatim from the original src.news.script_generator.
EMOTIONS = ["intrigue", "context", "discovery", "explanation", "detail", "question"]
TARGET_DURATIONS = [3.5, 7.0, 10.0, 13.0, 10.0, 8.0]


class LegacyTemplateScriptProvider(BaseScriptProvider):
    capabilities_spec = ScriptProviderCapabilities(
        provider_id=PROVIDER_ID,
        display_name="Шаблонный сценарий (прежний)",
        description=(
            "Шесть заранее написанных фраз и фиксированные длительности. "
            "Сохранён для воспроизводимости старых проектов и как эталон регрессии."
        ),
        supported_source_kinds=SOURCE_KINDS,
        requires_network=False,
        requires_paid_api=False,
        deterministic=True,
        implementation_status="legacy",
    )

    def generate(self, request: ScriptRequest) -> ScriptResult:
        claims = [claim for claim in request.claims if claim.get("safe_for_script", True)]
        # Exactly the old chain: research topic, then the job's topic (both arrive
        # already merged in request.topic), then the constant. request.title is
        # deliberately *not* consulted - the previous generator never looked at it,
        # and since stage B3 a job always has a generated title ("Без названия" at
        # worst), so honouring it here would silently replace the old constant.
        title = request.topic or "Научная новость"
        hook = _make_hook(title)
        scene_texts = _build_scene_texts(hook, claims, title)

        scenes: list[ScriptScene] = []
        start = 0.0
        for index, narration in enumerate(scene_texts, start=1):
            duration = TARGET_DURATIONS[min(index - 1, len(TARGET_DURATIONS) - 1)]
            claim_ids = [claims[min(index - 1, len(claims) - 1)]["claim_id"]] if claims else []
            if index == 1:
                role = SCENE_ROLE_HOOK
            elif index == len(scene_texts):
                role = SCENE_ROLE_PAYOFF
            else:
                role = SCENE_ROLE_DEVELOPMENT
            scenes.append(
                ScriptScene(
                    scene_id=f"scene_{index:03d}",
                    index=index,
                    role=role,
                    narration=narration,
                    duration_sec=duration,
                    start_sec=round(start, 2),
                    on_screen_text=_screen_text(narration),
                    visual_intent=_visual_intent(narration),
                    emotion=EMOTIONS[min(index - 1, len(EMOTIONS) - 1)],
                    claim_ids=claim_ids,
                )
            )
            start += duration

        return ScriptResult(
            scenes=scenes,
            title=title,
            hook=hook,
            description=f"Короткий научный ролик: {title}",
            language=request.language,
            source_kind=request.source_kind,
            provider_id=PROVIDER_ID,
            provider_version="1.0",
            target_duration_sec=request.target_duration_sec,
            source_claim_ids=[claim["claim_id"] for claim in claims],
        )


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


__all__ = ["EMOTIONS", "PROVIDER_ID", "TARGET_DURATIONS", "LegacyTemplateScriptProvider"]
