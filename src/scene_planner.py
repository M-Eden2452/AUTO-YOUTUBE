from __future__ import annotations

from typing import Any


def build_scene_plan(config: dict[str, Any], quote_plan: dict[str, Any]) -> dict[str, Any]:
    quote = quote_plan["quotes"][0]
    return {
        "video_type": config["video_type"],
        "topic": config["person"],
        "style": config["visual_style"],
        "hard_rules": [
            "Render must not fail when optional assets are missing.",
            "Cyrillic text must use an explicit Windows font path.",
            "Dev preview must stay short.",
            "All style decisions should come from config."
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
                "image_query": f"{config['person']} portrait",
                "background_mood": config["visual_style"],
                "animation": config["animation_type"],
                "transition": config["transition_type"]
            }
        ]
    }
