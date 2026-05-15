from __future__ import annotations

from typing import Any


def build_intro_plan(config: dict[str, Any], metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    generation = config.get("intro_generation", {})
    return {
        "enabled": True,
        "title": (metadata or {}).get("chosen_title", "Мысли Jordan Peterson, которые тяжело принять"),
        "subtitle": "Психология ответственности, правды и внутреннего порядка",
        "duration": 12 if not config.get("dev_mode", False) else 0,
        "style": config.get("intro_style", "темный кинематографичный title reveal"),
        "generation": {
            "provider": generation.get("provider", "openai_image_later"),
            "enabled": bool(generation.get("enabled", False)),
            "style_prompt": generation.get(
                "style_prompt",
                "dark cinematic intellectual portrait, noir documentary, dramatic lighting",
            ),
        },
        "note": "Сейчас intro рендерится локально. Поле generation оставлено для будущей OpenAI image generation.",
    }
