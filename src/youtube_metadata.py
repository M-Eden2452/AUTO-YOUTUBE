from __future__ import annotations

from typing import Any

from .utils import project_path, read_json, write_json


DEFAULT_METADATA_PATH = "outputs/youtube_metadata.json"


def generate_youtube_metadata(
    config: dict[str, Any],
    quote_plan: dict[str, Any] | None = None,
    scene_plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if config.get("video_task"):
        return _generate_video_task_metadata(config, quote_plan)

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


def _generate_video_task_metadata(config: dict[str, Any], quote_plan: dict[str, Any] | None = None) -> dict[str, Any]:
    task = config["video_task"]
    quote_plan = quote_plan or {"items": []}
    title_variants = task.get("title_variants", [task["chosen_title"]])
    source_notes = task.get("source_notes") or [
        item.get("source_note", "")
        for item in quote_plan.get("items", [])
        if item.get("source_note")
    ]
    chapters = _build_chapters(task.get("scenes", []))
    tags = _video_task_tags(config, task)
    keywords = _video_task_keywords(task)
    description = _video_task_description(task, chapters)
    return {
        "title_variants": title_variants,
        "chosen_title": task["chosen_title"],
        "description": description,
        "tags": tags,
        "keywords": keywords,
        "thumbnail_text": task.get("thumbnail_text", ""),
        "thumbnail_idea": task.get("thumbnail_idea", ""),
        "thumbnail_prompt": _thumbnail_prompt(task),
        "chapters": chapters,
        "pinned_comment": _pinned_comment(task),
        "shorts_hooks": _shorts_hooks(task),
        "upload_ready_fields": {
            "title": task["chosen_title"],
            "description": description,
            "tags": tags,
            "category_suggestion": "Education",
            "language": task.get("language", config.get("language", "ru")),
            "visibility_default": "private",
            "made_for_kids": False,
            "disclaimer": task.get("disclaimer", ""),
            "source_notes": source_notes,
        },
        "shorts_hook": "",
        "community_post": "",
        "source_notes": source_notes,
        "disclaimer": task.get("disclaimer", ""),
    }


def _build_chapters(scenes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    chapters: list[dict[str, Any]] = []
    current = 0
    for scene in scenes:
        chapters.append(
            {
                "time": _format_time(current),
                "title": scene.get("screen_text", "").splitlines()[0] or scene.get("scene_id", "Scene"),
                "scene_id": scene.get("scene_id", ""),
            }
        )
        current += int(scene.get("duration", 0))
    return chapters


def _format_time(seconds: int) -> str:
    minutes, sec = divmod(seconds, 60)
    return f"{minutes:02d}:{sec:02d}"


def _video_task_tags(config: dict[str, Any], task: dict[str, Any]) -> list[str]:
    if task.get("tags"):
        return [str(item) for item in task.get("tags", []) if str(item).strip()]
    if config.get("channel_id") == "survival":
        return [
            "Джулиана Кёпке",
            "Juliane Koepcke",
            "LANSA Flight 508",
            "выживание",
            "реальная история",
            "Амазония",
            "Перу",
            "авиакатастрофа",
            "истории выживания",
            "документальная история",
            "survival story",
            "Amazon rainforest",
        ]
    return [
        config.get("channel_id", ""),
        task.get("video_type", ""),
        "цитаты",
        "мысли",
        "cinematic",
    ]


def _video_task_keywords(task: dict[str, Any]) -> list[str]:
    keywords = [
        task["chosen_title"],
        task.get("visual_direction", ""),
        task.get("music_direction", ""),
    ]
    keywords.extend(task.get("source_notes", []))
    return [item for item in keywords if item]


def _video_task_description(task: dict[str, Any], chapters: list[dict[str, Any]]) -> str:
    chapter_lines = "\n".join(f"{chapter['time']} {chapter['title']}" for chapter in chapters)
    source_lines = "\n".join(f"- {item}" for item in task.get("source_notes", []))
    return "\n\n".join(
        part
        for part in [
            task.get("description", ""),
            task.get("disclaimer", ""),
            f"Главы:\n{chapter_lines}" if chapter_lines else "",
            f"Source notes:\n{source_lines}" if source_lines else "",
        ]
        if part
    )


def _thumbnail_prompt(task: dict[str, Any]) -> str:
    return (
        f"{task.get('thumbnail_idea', '')} "
        f"Крупный текст: {task.get('thumbnail_text', '')}. "
        "Cinematic documentary YouTube thumbnail, high contrast, readable Russian text."
    ).strip()


def _pinned_comment(task: dict[str, Any]) -> str:
    if task.get("source_notes"):
        return "Видео основано на открытых источниках. Если хотите, следующим шагом можно разобрать факты и источники подробнее."
    return "Какой момент этой истории зацепил вас сильнее всего?"


def _shorts_hooks(task: dict[str, Any]) -> list[str]:
    title = task.get("chosen_title", "")
    if task.get("channel") == "survival":
        return [
            "17-летняя девушка пережила авиакатастрофу и осталась одна в Амазонии.",
            "Она упала с неба и 11 дней шла через джунгли.",
            title,
        ]
    return [title] if title else []


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
