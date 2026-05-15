from __future__ import annotations

from typing import Any


def build_quote_plan(config: dict[str, Any]) -> dict[str, Any]:
    """Возвращает детерминированный план цитаты для MVP.

    Позже здесь можно подключить LLM, базу цитат или редакционный процесс.
    Структурный план уже сейчас делает рендер предсказуемым и удобным для отладки.
    """
    return {
        "video_type": config["video_type"],
        "topic": config["topic"],
        "person": config["person"],
        "language": config.get("language", "ru"),
        "source": config.get("quote_source", "curated_test_quote"),
        "quotes": [
            {
                "quote": "Сравнивай себя с тем, кем ты был вчера, а не с тем, кем кто-то другой является сегодня.",
                "quote_ru": "Сравнивай себя с тем, кем ты был вчера, а не с тем, кем кто-то другой является сегодня.",
                "author": "Jordan Peterson",
                "source_note": "Подготовленная тестовая цитата для MVP-рендера."
            }
        ]
    }
