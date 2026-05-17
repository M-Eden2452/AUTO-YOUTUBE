from __future__ import annotations

from typing import Any

import requests


REQUEST_TIMEOUT = 24


def search_videos(api_key: str, query: str, per_page: int = 10) -> list[dict[str, Any]]:
    if not api_key:
        return []
    response = requests.get(
        "https://api.pexels.com/videos/search",
        headers={"Authorization": api_key},
        params={"query": query, "orientation": "landscape", "per_page": per_page},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.json().get("videos", [])


def search_images(api_key: str, query: str, per_page: int = 10) -> list[dict[str, Any]]:
    if not api_key:
        return []
    response = requests.get(
        "https://api.pexels.com/v1/search",
        headers={"Authorization": api_key},
        params={"query": query, "orientation": "landscape", "per_page": per_page},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.json().get("photos", [])
