from __future__ import annotations

import hashlib
import math
import os
import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
import imageio_ffmpeg
from dotenv import load_dotenv

from .image_tools import create_person_placeholder
from .media_library import (
    avoid_duplicate_downloads,
    create_video_thumbnail,
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
MIN_VIDEO_WIDTH = 960
MIN_VIDEO_HEIGHT = 540
MAX_VIDEO_WIDTH = 2560


def build_documentary_asset_plan(config: dict[str, Any], scene_plan: dict[str, Any], refresh: bool = False) -> dict[str, Any]:
    load_dotenv()
    library_config = _library_config(config)
    library_root = ensure_media_library(library_config.get("root", "assets/library"))
    media_index_path = library_root / "metadata/media_index.json"
    media_index = load_media_index(media_index_path)
    video_cache = library_root / "videos"
    image_cache = project_path(config.get("image_cache_dir", "assets/cache/images"))
    video_cache.mkdir(parents=True, exist_ok=True)
    image_cache.mkdir(parents=True, exist_ok=True)

    search_enabled = bool(config.get("documentary_asset_search", {}).get("enabled", True))
    pexels_key = os.getenv("PEXELS_API_KEY")
    pixabay_key = os.getenv("PIXABAY_API_KEY")
    scene_assets: list[dict[str, Any]] = []
    visual_debug: list[dict[str, Any]] = []

    for scene in scene_plan.get("scenes", []):
        scene_number = int(scene.get("scene_number", len(scene_assets) + 1))
        queries = build_query_variants(scene, config)
        scene_duration = float(scene.get("duration", 0))
        target_count = _target_clip_count(scene_duration)
        candidates: list[dict[str, Any]] = []
        rejected: list[dict[str, Any]] = []
        local_matches: list[dict[str, Any]] = []

        if library_config["enabled"] and library_config["search_local_first"] and not refresh:
            local_matches = search_local_assets(
                media_index,
                scene,
                media_type="video",
                channel=str(config.get("channel_id", "")),
                min_score=int(library_config["min_local_score"]),
                limit=int(library_config["max_local_assets_per_scene"]),
            )

        selected = _clips_from_local_matches(local_matches, scene_number, target_count)
        for match in local_matches[:target_count]:
            mark_asset_used_in_video(media_index, str(match["asset"].get("id", "")), _video_usage_id(config))
        needs_download = len(selected) < target_count and library_config["download_if_not_enough"]

        if search_enabled and needs_download:
            for query in queries[:4]:
                if pexels_key and config.get("pexels_search", {}).get("enabled", True):
                    found, bad = _search_pexels_videos(pexels_key, query)
                    candidates.extend(found)
                    rejected.extend(bad)
                if pixabay_key and config.get("pixabay_search", {}).get("enabled", True):
                    found, bad = _search_pixabay_videos(pixabay_key, query)
                    candidates.extend(found)
                    rejected.extend(bad)
                if len(candidates) >= target_count * 3:
                    break

        new_limit = max(0, min(target_count - len(selected), int(library_config["max_new_downloads_per_scene"])))
        selected.extend(
            _select_and_cache_clips(
                candidates,
                video_cache,
                scene_number,
                new_limit,
                refresh,
                media_index,
                config,
                scene,
                library_root,
                bool(library_config["create_thumbnails"]),
            )
        )
        fallback_used = len(selected) < target_count
        if fallback_used:
            selected.extend(_generated_motion_clips(scene, target_count - len(selected)))

        selected = _fit_clip_durations(selected[:target_count], scene_duration)
        entry = {
            "scene_number": scene_number,
            "scene_id": scene.get("scene_id", ""),
            "scene_type": scene.get("scene_type", scene.get("type", "story")),
            "mood": scene.get("mood", ""),
            "visual_keywords": scene.get("visual_keywords", []),
            "queries": queries,
            "provider": _dominant_provider(selected),
            "query": queries[0] if queries else "",
            "asset_source": "local_library" if local_matches and not needs_download else "mixed" if local_matches else "api_or_fallback",
            "local_matches": [
                {
                    "asset_id": match["asset"].get("id"),
                    "path": match["asset"].get("local_path", ""),
                    "score": match["score"],
                    "thumbnail_path": match["asset"].get("thumbnail_path", ""),
                }
                for match in local_matches
            ],
            "clips": selected,
            "clip_count": len(selected),
            "confidence": _confidence(selected, fallback_used),
            "fallback_used": fallback_used,
            "fallback_reason": "not_enough_relevant_local_or_api_assets" if fallback_used else "",
            "path": selected[0].get("path", "") if selected else "",
        }
        scene_assets.append(entry)
        visual_debug.append(
            {
                "scene_number": scene_number,
                "scene_id": scene.get("scene_id", ""),
                "queries": queries,
                "selected_clips": selected,
                "rejected_clips": rejected[:20],
                "fallback_used": fallback_used,
            }
        )

    visual_debug_path = config.get("plans", {}).get("visual_debug") or str(project_path(config["output_filename"]).with_name("visual_debug.json"))
    plan = {
        "engine": "documentary_visual_engine_v2",
        "provider_priority": ["local_library", "pexels_video", "pixabay_video", "generated_motion"],
        "cache_dirs": {"videos": str(video_cache), "images": str(image_cache), "media_index": str(media_index_path)},
        "scene_assets": scene_assets,
        "broll": scene_assets,
        "visual_debug": visual_debug,
        "visual_debug_path": visual_debug_path,
        "warnings": _warnings(scene_assets, bool(pexels_key), bool(pixabay_key)),
    }
    write_json(visual_debug_path, {"engine": plan["engine"], "scenes": visual_debug})
    save_media_index(media_index, media_index_path)
    return plan


def build_query_variants(scene: dict[str, Any], config: dict[str, Any] | None = None) -> list[str]:
    keywords = [str(item).strip() for item in scene.get("visual_keywords", []) if str(item).strip()]
    mood = str(scene.get("mood", "")).strip()
    base_terms = keywords or [str(scene.get("image_query", "")).strip() or "cinematic documentary"]
    variants: list[str] = []
    suffixes = ["cinematic", "documentary footage", "slow motion", "dark atmosphere"]
    for term in base_terms:
        variants.append(term)
        for suffix in suffixes[:2]:
            variants.append(f"{term} {suffix}")
        words = term.split()
        if len(words) > 2:
            variants.append(" ".join(words[:2]))
    if mood:
        variants.append(f"{mood} documentary")
    channel = (config or {}).get("channel_id")
    if channel == "survival":
        variants.extend(
            [
                "amazon rainforest",
                "tropical jungle rain",
                "jungle river documentary",
                "storm clouds cinematic",
                "survival documentary",
            ]
        )
    return _unique(variants)[:12]


def _library_config(config: dict[str, Any]) -> dict[str, Any]:
    defaults = {
        "root": "assets/library",
        "enabled": True,
        "search_local_first": True,
        "min_local_score": 4,
        "download_if_not_enough": True,
        "create_thumbnails": True,
        "max_new_downloads_per_scene": 3,
        "max_local_assets_per_scene": 4,
        "providers": ["pexels", "pixabay", "unsplash"],
    }
    return {**defaults, **config.get("asset_library", {})}


def _clips_from_local_matches(matches: list[dict[str, Any]], scene_number: int, target_count: int) -> list[dict[str, Any]]:
    clips: list[dict[str, Any]] = []
    for match in matches[:target_count]:
        asset = match["asset"]
        clips.append(
            {
                "type": "video",
                "provider": asset.get("provider", "local"),
                "query": asset.get("original_query", ""),
                "path": asset.get("local_path", ""),
                "local_cache_path": asset.get("local_path", ""),
                "source_url": asset.get("source_url", ""),
                "source_duration": float(asset.get("duration") or 0),
                "width": int(asset.get("width") or 0),
                "height": int(asset.get("height") or 0),
                "score": match["score"],
                "local_score": match["score"],
                "asset_id": asset.get("id", ""),
                "asset_source": "local_library",
                "thumbnail_path": asset.get("thumbnail_path", ""),
                "scene_number": scene_number,
                "fallback_reason": "",
                "confidence": min(0.96, 0.68 + match["score"] / 40),
            }
        )
    return clips


def _search_pexels_videos(api_key: str, query: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    headers = {"Authorization": api_key}
    params = {"query": query, "orientation": "landscape", "per_page": 10}
    try:
        response = requests.get("https://api.pexels.com/videos/search", headers=headers, params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as exc:
        return [], [{"provider": "pexels", "query": query, "reason": f"request_failed: {exc.__class__.__name__}"}]

    selected: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for video in response.json().get("videos", []):
        duration = float(video.get("duration") or 0)
        file_info = _best_pexels_file(video.get("video_files", []))
        if not file_info:
            rejected.append({"provider": "pexels", "query": query, "id": video.get("id"), "reason": "no_landscape_hd_file"})
            continue
        width = int(file_info.get("width") or 0)
        height = int(file_info.get("height") or 0)
        if not _passes_video_filter(width, height, duration):
            rejected.append({"provider": "pexels", "query": query, "id": video.get("id"), "reason": "filtered_resolution_or_duration"})
            continue
        selected.append(
            {
                "provider": "pexels",
                "query": query,
                "source_id": str(video.get("id", "")),
                "source_url": video.get("url", ""),
                "download_url": file_info.get("link", ""),
                "width": width,
                "height": height,
                "source_duration": duration,
                "score": _score_candidate(width, height, duration),
            }
        )
    return selected, rejected


def _search_pixabay_videos(api_key: str, query: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    params = {"key": api_key, "q": query, "video_type": "film", "safesearch": "true", "per_page": 10}
    try:
        response = requests.get("https://pixabay.com/api/videos/", params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as exc:
        return [], [{"provider": "pixabay", "query": query, "reason": f"request_failed: {exc.__class__.__name__}"}]

    selected: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for hit in response.json().get("hits", []):
        video_file = _best_pixabay_file(hit.get("videos", {}))
        if not video_file:
            rejected.append({"provider": "pixabay", "query": query, "id": hit.get("id"), "reason": "no_usable_video_file"})
            continue
        width = int(video_file.get("width") or 0)
        height = int(video_file.get("height") or 0)
        duration = float(hit.get("duration") or 0)
        if not _passes_video_filter(width, height, duration):
            rejected.append({"provider": "pixabay", "query": query, "id": hit.get("id"), "reason": "filtered_resolution_or_duration"})
            continue
        selected.append(
            {
                "provider": "pixabay",
                "query": query,
                "source_id": str(hit.get("id", "")),
                "source_url": hit.get("pageURL", ""),
                "download_url": video_file.get("url", ""),
                "width": width,
                "height": height,
                "source_duration": duration,
                "score": _score_candidate(width, height, duration),
            }
        )
    return selected, rejected


def _best_pexels_file(files: list[dict[str, Any]]) -> dict[str, Any] | None:
    landscape = [item for item in files if int(item.get("width") or 0) >= int(item.get("height") or 1)]
    usable = [item for item in landscape if item.get("link") and int(item.get("width") or 0) >= MIN_VIDEO_WIDTH]
    preferred = [item for item in usable if int(item.get("width") or 0) <= 1920]
    pool = preferred or [item for item in usable if int(item.get("width") or 0) <= MAX_VIDEO_WIDTH]
    return sorted(pool, key=lambda item: int(item.get("width") or 0), reverse=True)[0] if pool else None


def _best_pixabay_file(videos: dict[str, Any]) -> dict[str, Any] | None:
    choices = [videos.get(name) for name in ("large", "medium", "small") if videos.get(name)]
    usable = [item for item in choices if item.get("url") and int(item.get("width") or 0) >= MIN_VIDEO_WIDTH]
    preferred = [item for item in usable if int(item.get("width") or 0) <= 1920]
    pool = preferred or [item for item in usable if int(item.get("width") or 0) <= MAX_VIDEO_WIDTH]
    return sorted(pool, key=lambda item: int(item.get("width") or 0), reverse=True)[0] if pool else None


def _passes_video_filter(width: int, height: int, duration: float) -> bool:
    if width < MIN_VIDEO_WIDTH or height < MIN_VIDEO_HEIGHT or width > MAX_VIDEO_WIDTH:
        return False
    aspect = width / max(height, 1)
    if aspect < 1.45 or aspect > 2.35:
        return False
    return duration >= 2.5


def _select_and_cache_clips(
    candidates: list[dict[str, Any]],
    cache_dir: Path,
    scene_number: int,
    target_count: int,
    refresh: bool,
    media_index: dict[str, Any],
    config: dict[str, Any],
    scene: dict[str, Any],
    library_root: Path,
    create_thumbnails: bool,
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    if target_count <= 0:
        return selected
    for candidate in sorted(candidates, key=lambda item: float(item.get("score", 0)), reverse=True):
        download_url = candidate.get("download_url", "")
        if not download_url or download_url in seen:
            continue
        seen.add(download_url)
        duplicate = avoid_duplicate_downloads(media_index, source_url=candidate.get("source_url", ""), download_url=download_url)
        if duplicate:
            local_path = project_path(duplicate.get("local_path", ""))
        else:
            local_path = _cached_video_path(cache_dir, candidate, scene_number, config, scene)
        if refresh or not local_path.exists():
            if not _download_file(download_url, local_path):
                continue
        if not _valid_video_file(local_path):
            continue
        asset = duplicate or register_asset(
            media_index,
            {
                **candidate,
                "type": "video",
                "local_path": str(local_path),
                "download_url": download_url,
                "original_query": candidate.get("query", ""),
                "keywords": scene.get("visual_keywords", []),
                "mood": scene.get("mood", ""),
                "channel_tags": [config.get("channel_id", "")],
                "scene_tags": [scene.get("scene_type", scene.get("type", ""))],
                "license_note": _license_note(candidate.get("provider", "")),
            },
        )
        thumbnail_path = asset.get("thumbnail_path", "")
        if create_thumbnails and not thumbnail_path:
            thumbnail_path = create_video_thumbnail(local_path, asset["id"], library_root)
            if thumbnail_path:
                asset["thumbnail_path"] = thumbnail_path
        mark_asset_used_in_video(media_index, asset["id"], _video_usage_id(config))
        item = {**candidate}
        item["type"] = "video"
        item["path"] = str(local_path)
        item["local_cache_path"] = str(local_path)
        item["asset_id"] = asset["id"]
        item["asset_source"] = "local_library_duplicate" if duplicate else "downloaded"
        item["thumbnail_path"] = thumbnail_path
        item["fallback_reason"] = ""
        item["confidence"] = min(0.95, 0.62 + float(candidate.get("score", 0)) / 10000)
        selected.append(item)
        if len(selected) >= target_count:
            break
    return selected


def _valid_video_file(path: Path) -> bool:
    if not path.exists() or path.stat().st_size < 1024:
        return False
    command = [
        imageio_ffmpeg.get_ffmpeg_exe(),
        "-v",
        "error",
        "-t",
        "2",
        "-i",
        str(path),
        "-f",
        "null",
        "-",
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    return result.returncode == 0


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


def _cached_video_path(cache_dir: Path, candidate: dict[str, Any], scene_number: int, config: dict[str, Any], scene: dict[str, Any]) -> Path:
    parsed = urlparse(candidate.get("download_url", ""))
    suffix = Path(parsed.path).suffix or ".mp4"
    digest = hashlib.sha1(candidate.get("download_url", "").encode("utf-8")).hexdigest()[:12]
    filename = generate_semantic_filename(
        media_type="video",
        provider=str(candidate.get("provider", "local")),
        channel=str(config.get("channel_id", "")),
        keywords=list(scene.get("visual_keywords", []))[:3] or [candidate.get("query", "")],
        mood=scene.get("mood", ""),
        width=int(candidate.get("width") or 0),
        height=int(candidate.get("height") or 0),
        short_id=str(candidate.get("source_id") or digest),
    )
    return cache_dir / (Path(filename).with_suffix(suffix).name)


def _generated_motion_clips(scene: dict[str, Any], count: int) -> list[dict[str, Any]]:
    clips: list[dict[str, Any]] = []
    keywords = scene.get("visual_keywords", []) or [scene.get("image_query", "dark documentary")]
    for index in range(count):
        clips.append(
            {
                "type": "generated_motion",
                "provider": "generated_motion",
                "query": str(keywords[index % len(keywords)]),
                "path": "",
                "local_cache_path": "",
                "source_url": "",
                "confidence": 0.32,
                "fallback": True,
            }
        )
    return clips


def _fit_clip_durations(clips: list[dict[str, Any]], scene_duration: float) -> list[dict[str, Any]]:
    if not clips:
        return clips
    base = scene_duration / len(clips)
    durations: list[float] = []
    for clip in clips:
        source_duration = float(clip.get("source_duration") or 0)
        max_duration = max(2.0, source_duration - 0.15) if source_duration else 5.5
        durations.append(max(2.0, min(5.5, base, max_duration)))
    scale = scene_duration / sum(durations)
    fitted: list[dict[str, Any]] = []
    for clip, duration in zip(clips, durations):
        item = {**clip}
        item["duration"] = round(duration * scale, 3)
        item["start_offset"] = 0.0
        fitted.append(item)
    return fitted


def _target_clip_count(duration: float) -> int:
    return max(3, min(6, math.ceil(duration / 4.0)))


def _score_candidate(width: int, height: int, duration: float) -> float:
    aspect = width / max(height, 1)
    aspect_score = max(0, 100 - abs(aspect - 1.777) * 80)
    duration_score = min(duration, 18) * 8
    resolution_score = min(width, 1920) / 24
    return aspect_score + duration_score + resolution_score


def _dominant_provider(clips: list[dict[str, Any]]) -> str:
    for clip in clips:
        if clip.get("provider") not in {"generated_motion", "placeholder"}:
            return str(clip.get("provider"))
    return "generated_motion"


def _confidence(clips: list[dict[str, Any]], fallback_used: bool) -> float:
    if not clips:
        return 0.0
    avg = sum(float(clip.get("confidence", 0.4)) for clip in clips) / len(clips)
    return round(avg - (0.12 if fallback_used else 0), 3)


def _warnings(scene_assets: list[dict[str, Any]], has_pexels: bool, has_pixabay: bool) -> list[str]:
    warnings: list[str] = []
    fallback_scenes = [asset["scene_number"] for asset in scene_assets if asset.get("fallback_used")]
    if fallback_scenes:
        warnings.append(f"Fallback motion assets used in scenes: {fallback_scenes}.")
    if not has_pexels and not has_pixabay:
        warnings.append("No Pexels/Pixabay API keys available; generated motion fallbacks were used.")
    return warnings


def _license_note(provider: str) -> str:
    if provider == "pexels":
        return "Pexels API asset; review Pexels license and attribution expectations before publishing."
    if provider == "pixabay":
        return "Pixabay API asset; review Pixabay Content License before publishing."
    return "Local asset; verify license before publishing."


def _video_usage_id(config: dict[str, Any]) -> str:
    channel = str(config.get("channel_id", "default"))
    video = str(config.get("video_id", config.get("output_filename", "unknown")))
    return f"{channel}/{video}"


def _unique(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = " ".join(value.lower().split())
        if normalized and normalized not in seen:
            result.append(value)
            seen.add(normalized)
    return result
