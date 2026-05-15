from __future__ import annotations

from typing import Any

from .utils import project_path, read_json, write_json


DEFAULT_METADATA_PATH = "outputs/youtube_metadata.json"


def generate_youtube_metadata(
    config: dict[str, Any],
    quote_plan: dict[str, Any] | None = None,
    scene_plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    quote_plan = quote_plan or read_json(config["plans"]["quote_plan"])
    scene_plan = scene_plan or read_json(config["plans"]["scene_plan"])

    scene = scene_plan["scenes"][0]
    quote = quote_plan["quotes"][0]
    person = scene.get("person") or config.get("person", "")
    topic = config.get("topic", person)
    style = config.get("visual_style", "")

    return {
        "title_variants": [
            f"{person}: фраза, которая бьет точно",
            f"Мысль {person}, которая меняет взгляд",
            f"Сильная цитата {person}",
            f"Фраза {person}, которая остается в голове",
            f"Сильная мысль: {person}"
        ],
        "description": (
            f"Короткое кинематографичное видео с цитатой на тему: {topic}. "
            f"Текст: {quote.get('quote_ru') or quote.get('quote', scene.get('quote', ''))}"
        ),
        "tags": [
            person,
            "цитаты",
            "мотивация",
            "психология",
            "философия",
            "сильные мысли"
        ],
        "keywords": [
            topic,
            f"цитаты {person}",
            "сильные мысли",
            "фразы которые остаются в голове",
            style
        ],
        "thumbnail_idea": (
            f"Темный кинематографичный портрет {person} слева, крупный текст цитаты справа, "
            "теплая золотая акцентная линия, интеллектуальное настроение."
        ),
        "shorts_hook": f"Одна мысль {person}, которая звучит сильнее, чем кажется сначала.",
        "community_post": f"Что думаешь об этой фразе {person}?\n\n{quote.get('quote_ru') or quote.get('quote', scene.get('quote', ''))}"
    }


def write_youtube_metadata(
    config: dict[str, Any],
    quote_plan: dict[str, Any] | None = None,
    scene_plan: dict[str, Any] | None = None,
    output_path: str = DEFAULT_METADATA_PATH,
) -> dict[str, Any]:
    metadata = generate_youtube_metadata(config, quote_plan, scene_plan)
    write_json(output_path, metadata)
    return metadata


def load_youtube_metadata(path: str = DEFAULT_METADATA_PATH) -> dict[str, Any]:
    target = project_path(path)
    if target.exists():
        return read_json(target)
    return {
        "title_variants": [],
        "description": "",
        "tags": [],
        "keywords": [],
        "thumbnail_idea": "",
        "shorts_hook": "",
        "community_post": ""
    }


def generate_with_ai_later() -> None:
    """Точка расширения для будущей AI-генерации метаданных."""
    raise NotImplementedError("AI-генерация метаданных намеренно не подключена в MVP.")
