from __future__ import annotations

from typing import Any


BROLL_QUERIES = [
    "dark library",
    "man thinking dark room",
    "night city rain",
    "lonely walk silhouette",
    "books philosophy",
    "dark office window",
    "rain window",
    "abstract dark",
    "city night",
    "old books",
    "silhouette walking",
    "dramatic shadows",
]


def build_scene_plan(config: dict[str, Any], quote_plan: dict[str, Any], metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    if config.get("video_task"):
        return _build_video_task_scene_plan(config, metadata or {})
    if config.get("dev_mode", False):
        return _build_dev_scene_plan(config, quote_plan)
    return _build_prod_scene_plan(config, quote_plan, metadata or {})


def _build_dev_scene_plan(config: dict[str, Any], quote_plan: dict[str, Any]) -> dict[str, Any]:
    quote = quote_plan["quotes"][0]
    return {
        "video_type": config["video_type"],
        "topic": config["topic"],
        "style": config["visual_style"],
        "hard_rules": _hard_rules(),
        "scenes": [
            {
                "scene_number": 1,
                "scene_type": "quote",
                "content_type": quote["content_type"],
                "duration": float(config["scene_duration"]),
                "layout": config["layout"],
                "person": config["person"],
                "quote": quote["quote"],
                "quote_ru": quote["quote_ru"],
                "screen_text": quote["quote_ru"],
                "author": quote["author"],
                "image_query": f"портрет {config['person']}",
                "background_mood": config["visual_style"],
                "animation": config["animation_type"],
                "transition": config["transition_type"],
                "source_note": quote["source_note"],
            }
        ],
    }


def _build_video_task_scene_plan(config: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
    task = config["video_task"]
    scenes: list[dict[str, Any]] = []
    for index, scene in enumerate(task.get("scenes", []), start=1):
        visual_keywords = scene.get("visual_keywords", [])
        scenes.append(
            {
                "scene_number": index,
                "scene_id": scene.get("scene_id", f"scene_{index:03d}"),
                "scene_type": scene.get("type", "thought"),
                "content_type": scene.get("content_type", scene.get("type", "idea")),
                "duration": float(scene.get("duration", config.get("scene_duration", 8))),
                "layout": config["layout"],
                "person": config.get("person", ""),
                "quote": scene.get("screen_text", ""),
                "quote_ru": scene.get("screen_text", ""),
                "screen_text": scene.get("screen_text", ""),
                "author": scene.get("author", ""),
                "image_query": visual_keywords[0] if visual_keywords else task.get("visual_direction", config.get("image_style", "")),
                "visual_keywords": visual_keywords,
                "background_mood": scene.get("mood", task.get("visual_direction", config["visual_style"])),
                "animation": scene.get("animation", config["animation_type"]),
                "transition": scene.get("transition", config["transition_type"]),
                "source_note": task.get("disclaimer", ""),
            }
        )

    return {
        "video_type": task.get("video_type", config["video_type"]),
        "topic": task["chosen_title"],
        "style": config["visual_style"],
        "chosen_title": metadata.get("chosen_title", task["chosen_title"]),
        "target_duration": sum(scene["duration"] for scene in scenes),
        "hard_rules": _hard_rules(),
        "scenes": scenes,
    }


def _build_prod_scene_plan(config: dict[str, Any], quote_plan: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
    chosen_title = metadata.get("chosen_title") or "Мысли Jordan Peterson, которые тяжело принять"
    scenes: list[dict[str, Any]] = []
    scene_number = 1

    scenes.append(
        {
            "scene_number": scene_number,
            "scene_type": "intro",
            "content_type": "narration_card",
            "duration": 12.0,
            "layout": "intro_title_reveal",
            "person": config["person"],
            "title": chosen_title,
            "subtitle": "Психология ответственности, правды и внутреннего порядка",
            "screen_text": chosen_title,
            "quote": "",
            "quote_ru": "",
            "author": config["person"],
            "image_query": "dark intellectual portrait library",
            "background_mood": "dark cinematic title reveal",
            "animation": "slow_zoom",
            "transition": "fade",
            "source_note": "Редакционная intro-карточка.",
        }
    )
    scene_number += 1

    quote_items = quote_plan["quotes"]
    for index, quote in enumerate(quote_items, start=1):
        duration = 9.0
        query = BROLL_QUERIES[(index - 1) % len(BROLL_QUERIES)]
        scenes.append(
            {
                "scene_number": scene_number,
                "scene_type": "thought",
                "content_type": quote["content_type"],
                "duration": duration,
                "layout": "cinematic_text_over_broll",
                "person": config["person"],
                "quote": quote["quote"],
                "quote_ru": quote["quote_ru"],
                "screen_text": _shorten_for_screen(quote["quote_ru"]),
                "author": quote["author"],
                "image_query": query,
                "background_mood": config["visual_style"],
                "animation": "slow_zoom" if index % 2 else "subtle_pan",
                "transition": "crossfade",
                "source_note": quote["source_note"],
            }
        )
        scene_number += 1

    scenes.append(
        {
            "scene_number": scene_number,
            "scene_type": "final",
            "content_type": "narration_card",
            "duration": 12.0,
            "layout": "final_reflection",
            "person": config["person"],
            "quote": "",
            "quote_ru": "",
            "screen_text": "Если мысль задела — возможно, она показала то, что давно требовало внимания.",
            "author": config["person"],
            "image_query": "night rain window reflection",
            "background_mood": "quiet dark final reflection",
            "animation": "slow_zoom",
            "transition": "fade",
            "source_note": "Финальная редакционная карточка.",
        }
    )

    return {
        "video_type": config["video_type"],
        "topic": config["topic"],
        "style": config["visual_style"],
        "chosen_title": chosen_title,
        "target_duration": sum(scene["duration"] for scene in scenes),
        "hard_rules": _hard_rules(),
        "scenes": scenes,
    }


def _hard_rules() -> list[str]:
    return [
        "Рендер не должен падать, если необязательные ассеты отсутствуют.",
        "Кириллица должна рендериться через явный путь к Windows-шрифту.",
        "Dev preview должен оставаться коротким.",
        "Production-ролик должен использовать структурные планы, а не сырые видео как источник логики.",
        "Пересказанные идеи должны быть помечены как idea или narration_card, а не как дословные цитаты.",
    ]


def _shorten_for_screen(text: str, limit: int = 118) -> str:
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0]
    return f"{cut}..."
