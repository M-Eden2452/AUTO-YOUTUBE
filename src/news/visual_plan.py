from __future__ import annotations

from typing import Any


def build_visual_plan(script: dict[str, Any], *, language: str, user_assets: list[str] | None = None) -> dict[str, Any]:
    scenes = []
    user_assets = user_assets or []
    for index, scene in enumerate(script.get("scenes", []), start=1):
        query = make_stock_query(scene.get("visual_intent") or scene.get("narration", "nature science"))
        scenes.append(
            {
                "scene_id": scene["scene_id"],
                "narration": scene.get("narration", ""),
                "target_duration_sec": scene.get("target_duration_sec", 3.5),
                "visual_type": "video" if index % 3 else "animated_image",
                "visual_description": scene.get("visual_intent", ""),
                "primary_query": query,
                "alternative_queries": [query.replace("scientific", "nature"), "wildlife observation close up"],
                "negative_keywords": ["watermark", "logo", "low resolution"],
                "preferred_asset_ids": [f"user_asset_{index:03d}"] if index <= len(user_assets) else [],
                "allow_user_asset": True,
                "allow_stock": True,
                "allow_article_asset": False,
                "fallback_type": "text_card" if index == 1 else "animated_image",
                "camera_effect": "slow_zoom_in",
                "transition": "cut",
            }
        )
    return {
        "language": language,
        "aspect_ratio": "9:16",
        "resolution": {"width": 1080, "height": 1920},
        "scenes": scenes,
    }


def make_stock_query(text: str) -> str:
    lowered = text.lower()
    if "кит" in lowered or "whale" in lowered:
        return "whale mother calf aerial ocean"
    if "учен" in lowered or "research" in lowered:
        return "scientific researchers nature field observation"
    if "океан" in lowered or "ocean" in lowered:
        return "ocean wildlife aerial waves"
    return "nature science wildlife observation"

