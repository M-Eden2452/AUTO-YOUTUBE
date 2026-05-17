from __future__ import annotations

from typing import Any

import requests


REQUEST_TIMEOUT = 24


def search_images(access_key: str, query: str, per_page: int = 10) -> list[dict[str, Any]]:
    if not access_key:
        return []
    response = requests.get(
        "https://api.unsplash.com/search/photos",
        headers={"Authorization": f"Client-ID {access_key}"},
        params={"query": query, "orientation": "landscape", "per_page": per_page},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.json().get("results", [])
