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
    person = config.get("person", "Jordan Peterson")
    topic = config.get("topic", person)
    disclaimer = quote_plan.get(
        "disclaimer",
        "Некоторые формулировки являются пересказом идей Jordan Peterson, а не дословными цитатами.",
    )

    title_variants = [
        "Мысли Jordan Peterson, которые тяжело принять",
        "Jordan Peterson сказал то, что люди боятся признать",
        "Слова Jordan Peterson, которые заставляют посмотреть на себя иначе",
        "10 мыслей, после которых трудно остаться прежним",
        "Фразы Jordan Peterson, которые бьют точно",
        "Почему правда Peterson звучит так неудобно",
        "Jordan Peterson: жесткие мысли о жизни, ответственности и хаосе",
        "Эти идеи Jordan Peterson могут изменить твой взгляд на себя",
        "Когда порядок начинается с честности: мысли Jordan Peterson",
        "То, что Peterson говорит о слабости, ответственности и правде",
    ]
    chosen_title = title_variants[0]

    source_notes = [
        item.get("source_note", "")
        for item in quote_plan.get("items", [])
        if item.get("source_note")
    ]

    return {
        "title_variants": title_variants,
        "chosen_title": chosen_title,
        "description": (
            f"{chosen_title}\n\n"
            "Кинематографичное интеллектуальное видео на русском языке о мыслях Jordan Peterson: "
            "ответственность, правда, порядок, хаос, дисциплина и взросление.\n\n"
            f"{disclaimer}\n\n"
            "Видео создано как production-style preview без озвучки, с расчетом на будущий voice-over."
        ),
        "tags": [
            "Jordan Peterson",
            "Джордан Питерсон",
            "психология",
            "философия",
            "ответственность",
            "дисциплина",
            "мотивация без кринжа",
            "сильные мысли",
            "цитаты",
            "саморазвитие",
        ],
        "keywords": [
            topic,
            "мысли Jordan Peterson",
            "цитаты Джордана Питерсона",
            "ответственность и дисциплина",
            "порядок и хаос",
            "психологическое документальное видео",
            "dark cinematic intellectual",
        ],
        "thumbnail_idea": (
            "Темный портретный силуэт, дождь или библиотека на фоне, крупный заголовок: "
            "«Тяжело принять», золотой акцент, минимальный premium documentary стиль."
        ),
        "thumbnail_prompt": (
            "dark cinematic intellectual documentary thumbnail, Jordan Peterson inspired portrait silhouette, "
            "rainy window, library shadows, gold accent, serious psychological mood, premium YouTube documentary"
        ),
        "shorts_hook": "Одна из самых неудобных мыслей Peterson: порядок начинается с того, что ты перестаешь себе лгать.",
        "community_post": (
            "Какая мысль Jordan Peterson звучит для тебя тяжелее всего: про ответственность, правду или дисциплину?"
        ),
        "source_notes": source_notes,
        "disclaimer": disclaimer,
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
        "chosen_title": "",
        "description": "",
        "tags": [],
        "keywords": [],
        "thumbnail_idea": "",
        "thumbnail_prompt": "",
        "shorts_hook": "",
        "community_post": "",
        "source_notes": [],
        "disclaimer": "",
    }


def generate_with_ai_later() -> None:
    """Точка расширения для будущей AI-генерации метаданных."""
    raise NotImplementedError("AI-генерация метаданных намеренно не подключена в этом production MVP.")
