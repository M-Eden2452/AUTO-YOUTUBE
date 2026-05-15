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
            f"{person}: Words That Hit Hard",
            f"{person} Quote That Changes Your Perspective",
            f"Powerful Thought from {person}",
            f"Фраза {person}, которая остается в голове",
            f"Сильная мысль: {person}"
        ],
        "description": (
            f"A short cinematic quote video about {topic}. "
            f"Quote: {quote.get('quote', scene.get('quote', ''))}"
        ),
        "tags": [
            person,
            "quotes",
            "motivation",
            "psychology",
            "philosophy",
            "cinematic quotes"
        ],
        "keywords": [
            topic,
            f"{person} quotes",
            "powerful thoughts",
            "words that hit hard",
            style
        ],
        "thumbnail_idea": (
            f"Dark cinematic portrait of {person} on the left, large quote text on the right, "
            "warm gold accent line, intellectual mood."
        ),
        "shorts_hook": f"One thought from {person} that hits harder than expected.",
        "community_post": f"What do you think about this line from {person}?\n\n{quote.get('quote', scene.get('quote', ''))}"
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
    """Reserved seam for future OpenAI-powered metadata generation."""
    raise NotImplementedError("AI metadata generation is intentionally not connected in the MVP.")
