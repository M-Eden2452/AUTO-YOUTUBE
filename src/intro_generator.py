from __future__ import annotations

from typing import Any


def build_intro_plan(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "enabled": False,
        "style": config.get("intro_style", "minimal cinematic"),
        "future_provider": "OpenAI image generation",
        "settings": config.get("openai_image_generation", {}),
        "note": "MVP skips intro rendering but keeps this plan boundary for production videos."
    }
