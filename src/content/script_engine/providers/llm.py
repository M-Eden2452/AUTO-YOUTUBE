"""Interface for a future LLM-written script. Nothing here calls an API.

Stage Q1 prepares the seam and stops there, on purpose:

- there is **no API client, no key lookup, no network import** in this module;
- the model call is an injected callable (``completion_fn``), so the only way to
  run this provider is for a caller to hand it one;
- without that callable it raises ``ScriptProviderUnavailableError``;
- even with one it refuses to run unless ``approved=True`` is passed explicitly,
  mirroring the on-disk approval gate that already protects paid TTS
  (``src.audio.voice_workflow``).

What *is* implemented is the part that has to be right before any money is spent:
the response contract and its parser. A model answer that does not match is a
``ScriptProviderResponseError``, never a half-built script - so the caller can
fall back to a local provider instead of rendering nonsense.
"""

from __future__ import annotations

import json
from typing import Any, Callable

from ..contract import (
    BaseScriptProvider,
    ScriptProviderCapabilities,
    ScriptProviderResponseError,
    ScriptProviderUnavailableError,
)
from ..models import (
    SCENE_ROLES,
    SCENE_ROLE_DEVELOPMENT,
    SOURCE_KINDS,
    ScriptRequest,
    ScriptResult,
    ScriptScene,
)
from ..text_analysis import estimate_duration_sec, first_words, keywords, shorten

PROVIDER_ID = "llm"

# The exact JSON a model must return. Kept next to the parser so the two cannot
# drift apart; a prompt builder lives here too for the same reason.
RESPONSE_CONTRACT = {
    "title": "str",
    "description": "str",
    "scenes": [
        {
            "role": "hook | development | payoff | cta",
            "narration": "str - what is actually spoken",
            "on_screen_text": "str, optional",
            "visual_intent": "str, optional - what to show",
        }
    ],
}

CompletionFn = Callable[[str, dict[str, Any]], str]


class LLMScriptProvider(BaseScriptProvider):
    """Not wired to any vendor. See the module docstring for why."""

    capabilities_spec = ScriptProviderCapabilities(
        provider_id=PROVIDER_ID,
        display_name="Сценарий языковой моделью",
        description=(
            "Интерфейс подготовлен, вызов модели не подключён. Требует отдельного "
            "подтверждения оплаты, как и платная озвучка."
        ),
        supported_source_kinds=SOURCE_KINDS,
        requires_network=True,
        requires_paid_api=True,
        deterministic=False,
        implementation_status="planned",
    )

    def __init__(
        self,
        completion_fn: CompletionFn | None = None,
        *,
        approved: bool = False,
        model_id: str = "",
    ) -> None:
        self._completion_fn = completion_fn
        self._approved = approved
        self._model_id = model_id

    def is_available(self) -> bool:
        """Wired to a model *and* approved to spend money on it."""
        return self._completion_fn is not None and self._approved

    # supports() is deliberately left as the base implementation - it answers "can
    # this provider handle this kind of input", not "is it switched on here".
    # Folding availability into it made every unwired call report the source kind
    # as unsupported, which is not what went wrong; generate() below says the truth.

    def generate(self, request: ScriptRequest) -> ScriptResult:
        if self._completion_fn is None:
            raise ScriptProviderUnavailableError(
                "LLM-провайдер сценария не подключён: вызов модели не реализован на этом этапе.",
                provider=PROVIDER_ID,
            )
        if not self._approved:
            raise ScriptProviderUnavailableError(
                "Генерация сценария моделью требует явного подтверждения оплаты.",
                provider=PROVIDER_ID,
            )
        prompt = build_prompt(request)
        raw = self._completion_fn(prompt, {"model_id": self._model_id, "language": request.language})
        return parse_response(raw, request, provider_id=PROVIDER_ID, model_id=self._model_id)


def build_prompt(request: ScriptRequest) -> str:
    """The instruction a model would receive. Pure string building, no I/O."""
    limits = request.constraints
    source = request.raw_text or request.summary or request.topic
    claims = "\n".join(f"- {claim.get('text', '')}" for claim in request.claims if claim.get("text"))
    return "\n".join(
        [
            f"Язык сценария: {request.language}.",
            f"Формат: {request.format_id}. Целевая длительность: {limits.target_duration_sec:.0f} секунд.",
            "Структура: крючок (hook), развитие (development), развязка (payoff).",
            (
                "Добавь короткий призыв к действию (cta) последней сценой."
                if request.include_cta
                else "Призыв к действию НЕ добавляй."
            ),
            f"Сцена длится от {limits.min_scene_duration_sec:.0f} до {limits.max_scene_duration_sec:.0f} секунд;"
            " количество сцен определяется смыслом, а не фиксировано.",
            "Не выдумывай фактов, чисел и источников: опирайся только на материал ниже.",
            "Ответ — строго JSON по схеме:",
            json.dumps(RESPONSE_CONTRACT, ensure_ascii=False, indent=2),
            "",
            f"Тема: {request.topic}",
            f"Материал:\n{source}",
            f"Проверенные утверждения:\n{claims}" if claims else "",
        ]
    ).strip()


def parse_response(
    raw: str | dict[str, Any],
    request: ScriptRequest,
    *,
    provider_id: str = PROVIDER_ID,
    model_id: str = "",
) -> ScriptResult:
    """Turn a model answer into a ScriptResult, or fail loudly.

    Durations are *not* taken from the model: they are computed from the text at
    the same characters-per-second rate every other provider uses, so a model
    cannot claim a 3-second scene for a 40-word sentence.
    """
    if isinstance(raw, str):
        text = raw.strip()
        if text.startswith("```"):
            text = text.strip("`")
            text = text.split("\n", 1)[1] if "\n" in text else text
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ScriptProviderResponseError(
                f"Ответ модели не является корректным JSON: {exc}", provider=provider_id
            ) from exc
    elif isinstance(raw, dict):
        data = raw
    else:
        raise ScriptProviderResponseError(
            f"Ответ модели имеет неподдерживаемый тип {type(raw).__name__}.", provider=provider_id
        )

    raw_scenes = data.get("scenes")
    if not isinstance(raw_scenes, list) or not raw_scenes:
        raise ScriptProviderResponseError("В ответе модели нет сцен.", provider=provider_id)

    limits = request.constraints
    scenes: list[ScriptScene] = []
    for index, entry in enumerate(raw_scenes, start=1):
        if not isinstance(entry, dict):
            raise ScriptProviderResponseError(
                f"Сцена {index} в ответе модели не является объектом.", provider=provider_id
            )
        narration = str(entry.get("narration") or "").strip()
        if not narration:
            raise ScriptProviderResponseError(
                f"Сцена {index} в ответе модели без текста озвучки.", provider=provider_id
            )
        role = str(entry.get("role") or "").strip().lower()
        if role not in SCENE_ROLES:
            role = SCENE_ROLE_DEVELOPMENT
        scenes.append(
            ScriptScene(
                scene_id=f"scene_{index:03d}",
                index=index,
                role=role,
                narration=narration,
                duration_sec=round(
                    limits.clamp_duration(
                        estimate_duration_sec(narration, chars_per_sec=limits.speech_chars_per_sec)
                    ),
                    2,
                ),
                on_screen_text=str(entry.get("on_screen_text") or first_words(narration)),
                visual_intent=str(entry.get("visual_intent") or shorten(narration, 160)),
                emotion=str(entry.get("emotion") or ""),
                keywords=keywords(narration),
                source_refs=[f"llm_scene_{index:03d}"],
            )
        )

    return ScriptResult(
        scenes=scenes,
        title=str(data.get("title") or request.title or request.topic),
        hook=scenes[0].narration,
        description=str(data.get("description") or ""),
        language=request.language,
        source_kind=request.source_kind,
        provider_id=provider_id,
        provider_version=model_id or "unspecified",
        target_duration_sec=request.target_duration_sec,
        source_claim_ids=[str(claim.get("claim_id")) for claim in request.claims if claim.get("claim_id")],
        metadata={"model_id": model_id} if model_id else {},
    ).renumber()


__all__ = [
    "PROVIDER_ID",
    "RESPONSE_CONTRACT",
    "CompletionFn",
    "LLMScriptProvider",
    "build_prompt",
    "parse_response",
]
