from __future__ import annotations

from typing import Any

import requests


REQUEST_TIMEOUT = 24


def search_videos(api_key: str, query: str, per_page: int = 10) -> list[dict[str, Any]]:
    if not api_key:
        return []
    response = requests.get(
        "https://pixabay.com/api/videos/",
        params={"key": api_key, "q": query, "video_type": "film", "safesearch": "true", "per_page": per_page},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.json().get("hits", [])


def search_images(api_key: str, query: str, per_page: int = 10) -> list[dict[str, Any]]:
    if not api_key:
        return []
    response = requests.get(
        "https://pixabay.com/api/",
        params={
            "key": api_key,
            "q": query,
            "image_type": "photo",
            "orientation": "horizontal",
            "safesearch": "true",
            "per_page": per_page,
        },
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.json().get("hits", [])


def search_music(api_key: str, query: str, per_page: int = 8) -> list[dict[str, Any]]:
    if not api_key:
        return []
    response = requests.get(
        "https://pixabay.com/api/audio/",
        params={"key": api_key, "q": query, "audio_type": "music", "safesearch": "true", "per_page": per_page},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.json().get("hits", [])
