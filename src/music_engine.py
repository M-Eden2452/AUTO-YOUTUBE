from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv

from .media_library import (
    avoid_duplicate_downloads,
    ensure_media_library,
    generate_semantic_filename,
    load_media_index,
    mark_asset_used_in_video,
    register_asset,
    save_media_index,
    search_local_assets,
)
from .utils import project_path, write_json


REQUEST_TIMEOUT = 24


def build_music_plan_v2(config: dict[str, Any], scene_plan: dict[str, Any] | None = None) -> dict[str, Any]:
    load_dotenv()
    total_duration = sum(float(scene.get("duration", 0)) for scene in (scene_plan or {}).get("scenes", []))
    search_config = config.get("music_search", {})
    library_config = _library_config(config)
    library_root = ensure_media_library(library_config.get("root", "assets/library"))
    media_index_path = library_root / "metadata/media_index.json"
    media_index = load_media_index(media_index_path)
    cache_dir = library_root / "music"
    cache_dir.mkdir(parents=True, exist_ok=True)
    volume = min(float(search_config.get("volume", config.get("music_volume", 0.14))), 0.16)
    queries = _music_queries(config, scene_plan)
    fallback_path = project_path(search_config.get("fallback_path", config.get("music_path", "music/background.mp3")))

    selected_track: dict[str, Any] | None = None
    warnings: list[str] = []
    local_matches: list[dict[str, Any]] = []
    if library_config["enabled"] and library_config["search_local_first"]:
        local_matches = search_local_assets(
            media_index,
            {
                "visual_keywords": queries,
                "mood": config.get("music_mood", ""),
                "duration": total_duration,
            },
            media_type="music",
            channel=str(config.get("channel_id", "")),
            min_score=int(library_config["min_local_score"]),
            limit=1,
        )
    if local_matches:
        asset = local_matches[0]["asset"]
        selected_track = {
            "provider": asset.get("provider", "local"),
            "query": asset.get("original_query", "local library"),
            "title": Path(asset.get("local_path", "")).stem,
            "path": asset.get("local_path", ""),
            "duration": float(asset.get("duration") or 0),
            "source_url": asset.get("source_url", ""),
            "downloaded": False,
            "asset_id": asset.get("id", ""),
            "asset_source": "local_library",
            "score": local_matches[0]["score"],
        }
        mark_asset_used_in_video(media_index, str(asset.get("id", "")), _video_usage_id(config))
    pixabay_key = os.getenv("PIXABAY_API_KEY")
    if not selected_track and pixabay_key and bool(search_config.get("auto_download", True)):
        selected_track = _search_and_cache_pixabay_music(pixabay_key, queries, cache_dir, media_index, config)
    if not selected_track and fallback_path.exists():
        asset = register_asset(
            media_index,
            {
                "type": "music",
                "provider": "local",
                "local_path": str(fallback_path),
                "keywords": queries,
                "mood": config.get("music_mood", ""),
                "channel_tags": [config.get("channel_id", "")],
                "license_note": "Local fallback music; verify license before publishing.",
            },
        )
        mark_asset_used_in_video(media_index, asset["id"], _video_usage_id(config))
        selected_track = {
            "provider": "local_file",
            "query": "local fallback",
            "title": fallback_path.stem,
            "path": str(fallback_path),
            "duration": 0,
            "source_url": "",
            "downloaded": False,
            "asset_id": asset["id"],
            "asset_source": "local_fallback",
        }
    if not selected_track:
        warnings.append("Music was not found through Pixabay and no local fallback exists.")

    path = selected_track.get("path", "") if selected_track else ""
    status = "found" if path else "music_not_found"
    plan = {
        "engine": "music_engine_v2",
        "enabled": True,
        "provider": selected_track.get("provider", "pixabay") if selected_track else "pixabay",
        "status": status,
        "track": selected_track or {},
        "asset_source": selected_track.get("asset_source", "api_or_fallback") if selected_track else "missing",
        "local_matches": local_matches,
        "path": path,
        "query": selected_track.get("query", queries[0]) if selected_track else queries[0],
        "queries": queries,
        "duration": total_duration,
        "fade_points": {"fade_in": 2.0, "fade_out": min(4.0, max(2.0, total_duration * 0.04))},
        "loop_used": _loop_needed(selected_track, total_duration),
        "volume": volume,
        "voice_over_ready": True,
        "normalization": {"target": "background_under_voice", "method": "moviepy_volume_scale"},
        "warnings": warnings,
    }
    write_json(config["plans"].get("music_plan", "outputs/music_plan.json"), plan)
    save_media_index(media_index, media_index_path)
    return plan


def _music_queries(config: dict[str, Any], scene_plan: dict[str, Any] | None) -> list[str]:
    if config.get("channel_id") == "survival":
        return [
            "dark ambient survival",
            "cinematic jungle tension",
            "documentary suspense",
            "rainforest ambient",
            "survival cinematic",
            "emotional documentary",
        ]
    configured = config.get("music_search", {}).get("queries", [])
    return configured or ["dark cinematic ambient", "documentary piano", "emotional documentary"]


def _search_and_cache_pixabay_music(
    api_key: str,
    queries: list[str],
    cache_dir: Path,
    media_index: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any] | None:
    for query in queries:
        params = {
            "key": api_key,
            "q": query,
            "audio_type": "music",
            "safesearch": "true",
            "per_page": 8,
        }
        try:
            response = requests.get("https://pixabay.com/api/audio/", params=params, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
        except requests.RequestException:
            continue
        hits = response.json().get("hits", [])
        for hit in sorted(hits, key=_music_score, reverse=True):
            url = hit.get("audio") or hit.get("previewURL")
            if not url:
                continue
            duplicate = avoid_duplicate_downloads(media_index, source_url=hit.get("pageURL", ""), download_url=url)
            target = project_path(duplicate.get("local_path", "")) if duplicate else _cache_music_path(cache_dir, hit, url, query, config)
            if not target.exists() and not _download_file(url, target):
                continue
            asset = duplicate or register_asset(
                media_index,
                {
                    "type": "music",
                    "provider": "pixabay",
                    "source_url": hit.get("pageURL", ""),
                    "download_url": url,
                    "local_path": str(target),
                    "original_query": query,
                    "keywords": [query],
                    "mood": config.get("music_mood", ""),
                    "channel_tags": [config.get("channel_id", "")],
                    "duration": float(hit.get("duration") or 0),
                    "license_note": "Pixabay API music asset; review Pixabay Content License before publishing.",
                },
            )
            mark_asset_used_in_video(media_index, asset["id"], _video_usage_id(config))
            return {
                "provider": "pixabay",
                "query": query,
                "title": hit.get("title", target.stem),
                "path": str(target),
                "duration": float(hit.get("duration") or 0),
                "source_url": hit.get("pageURL", ""),
                "downloaded": True,
                "asset_id": asset["id"],
                "asset_source": "local_library_duplicate" if duplicate else "downloaded",
            }
    return None


def _music_score(hit: dict[str, Any]) -> float:
    duration = float(hit.get("duration") or 0)
    return min(duration, 360) + float(hit.get("downloads") or 0) / 1000


def _cache_music_path(cache_dir: Path, hit: dict[str, Any], url: str, query: str, config: dict[str, Any]) -> Path:
    parsed = urlparse(url)
    suffix = Path(parsed.path).suffix or ".mp3"
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]
    filename = generate_semantic_filename(
        media_type="music",
        provider="pixabay",
        channel=str(config.get("channel_id", "")),
        mood=config.get("music_mood", query),
        genre=query,
        short_id=str(hit.get("id") or digest),
    )
    return cache_dir / Path(filename).with_suffix(suffix).name


def _download_file(url: str, target: Path) -> bool:
    try:
        with requests.get(url, stream=True, timeout=REQUEST_TIMEOUT) as response:
            response.raise_for_status()
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=1024 * 256):
                    if chunk:
                        handle.write(chunk)
        return target.exists() and target.stat().st_size > 1024
    except requests.RequestException:
        return False


def _loop_needed(track: dict[str, Any] | None, total_duration: float) -> bool:
    if not track:
        return False
    source_duration = float(track.get("duration") or 0)
    return source_duration > 0 and source_duration < total_duration


def _library_config(config: dict[str, Any]) -> dict[str, Any]:
    defaults = {
        "root": "assets/library",
        "enabled": True,
        "search_local_first": True,
        "min_local_score": 4,
    }
    return {**defaults, **config.get("asset_library", {})}


def _video_usage_id(config: dict[str, Any]) -> str:
    channel = str(config.get("channel_id", "default"))
    video = str(config.get("video_id", config.get("output_filename", "unknown")))
    return f"{channel}/{video}"
