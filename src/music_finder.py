from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from .music_engine import build_music_plan_v2
from .utils import project_path, write_json


def build_music_plan(config: dict[str, Any], scene_plan: dict[str, Any] | None = None) -> dict[str, Any]:
    if config.get("video_task"):
        return build_music_plan_v2(config, scene_plan)

    load_dotenv()
    search_config = config.get("music_search", {})
    fallback_path = project_path(search_config.get("fallback_path", config.get("music_path", "music/background.mp3")))
    queries = search_config.get("queries", [])
    volume = float(search_config.get("volume", config.get("music_volume", 0.16)))

    if fallback_path.exists():
        plan = {
            "enabled": True,
            "provider": "локальный_файл",
            "status": "найдена_локальная_музыка",
            "path": str(fallback_path),
            "volume": volume,
            "queries": queries,
            "warnings": [],
            "recommendations": [],
        }
        write_json(config["plans"].get("music_plan", "outputs/music_plan.json"), plan)
        return plan

    pixabay_key_available = bool(os.getenv("PIXABAY_API_KEY"))
    recommendations = [
        "dark cinematic ambient",
        "documentary piano",
        "slow dramatic piano",
        "atmospheric documentary music",
        "noir piano background",
    ]
    warning = (
        "Локальная музыка не найдена. Автоскачивание музыки через официальный API не выполнено: "
        "для надежности pipeline не использует scraping и собирает видео без музыки."
    )
    if not pixabay_key_available:
        warning = "Локальная музыка не найдена, PIXABAY_API_KEY недоступен, видео будет собрано без музыки."

    plan = {
        "enabled": bool(search_config.get("enabled", True)),
        "provider": search_config.get("provider", "pixabay"),
        "status": "музыка_не_найдена",
        "path": "",
        "volume": volume,
        "queries": queries,
        "warnings": [warning],
        "recommendations": recommendations,
    }
    write_json(config["plans"].get("music_plan", "outputs/music_plan.json"), plan)
    return plan
