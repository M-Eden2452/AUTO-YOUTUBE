from __future__ import annotations

from typing import Any


def build_scene_plan(config: dict[str, Any], quote_plan: dict[str, Any]) -> dict[str, Any]:
    quote = quote_plan["quotes"][0]
    return {
        "video_type": config["video_type"],
        "topic": config["person"],
        "style": config["visual_style"],
        "hard_rules": [
            "Рендер не должен падать, если необязательные ассеты отсутствуют.",
            "Кириллица должна рендериться через явный путь к Windows-шрифту.",
            "Превью в режиме разработки должно оставаться коротким.",
            "Все стилевые решения должны идти из конфига."
        ],
        "scenes": [
            {
                "scene_number": 1,
                "duration": float(config["scene_duration"]),
                "layout": config["layout"],
                "person": config["person"],
                "quote": quote["quote"],
                "quote_ru": quote["quote_ru"],
                "author": quote["author"],
                "image_query": f"портрет {config['person']}",
                "background_mood": config["visual_style"],
                "animation": config["animation_type"],
                "transition": config["transition_type"]
            }
        ]
    }
