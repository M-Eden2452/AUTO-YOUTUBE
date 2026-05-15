from __future__ import annotations

from pathlib import Path
from typing import Any

from .image_tools import create_person_placeholder
from .utils import project_path


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def build_asset_plan(config: dict[str, Any], scene_plan: dict[str, Any]) -> dict[str, Any]:
    scene = scene_plan["scenes"][0]
    image_path, image_status = find_person_image(config["person"], config)
    music_path = project_path(config["music_path"])
    music_status = "found" if music_path.exists() else "missing_silent_fallback"

    return {
        "person": config["person"],
        "image": {
            "path": str(image_path),
            "status": image_status,
            "query": scene["image_query"]
        },
        "music": {
            "path": str(music_path),
            "status": music_status,
            "volume": float(config.get("music_volume", 0.18))
        },
        "broll": [],
        "intro_image": {
            "enabled": False,
            "status": "reserved_for_future_openai_image_generation"
        }
    }


def find_person_image(person: str, config: dict[str, Any]) -> tuple[Path, str]:
    image_dir = project_path("assets/images")
    image_dir.mkdir(parents=True, exist_ok=True)
    tokens = [part.lower() for part in person.replace("-", " ").split() if part]

    for candidate in image_dir.iterdir():
        if not candidate.is_file() or candidate.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        name = candidate.stem.lower()
        if all(token in name for token in tokens) or any(token in name for token in tokens):
            return candidate, "found_local"

    placeholder = image_dir / "jordan_peterson_placeholder.jpg"
    if not placeholder.exists():
        create_person_placeholder(person, placeholder, config)
    return placeholder, "created_placeholder"
