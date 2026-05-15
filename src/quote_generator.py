from __future__ import annotations

from typing import Any


def build_quote_plan(config: dict[str, Any]) -> dict[str, Any]:
    """Return a deterministic quote plan for the MVP.

    Later this can call an LLM, a quote database, or a curated workflow. Keeping
    the structured plan now makes the renderer predictable and easy to debug.
    """
    return {
        "video_type": config["video_type"],
        "topic": config["topic"],
        "person": config["person"],
        "language": config.get("language", "ru"),
        "source": config.get("quote_source", "curated_test_quote"),
        "quotes": [
            {
                "quote": "Compare yourself to who you were yesterday, not to who someone else is today.",
                "quote_ru": "Сравнивай себя с тем, кем ты был вчера, а не с тем, кем кто-то другой является сегодня.",
                "author": "Jordan Peterson",
                "source_note": "Curated test quote for MVP rendering."
            }
        ]
    }
