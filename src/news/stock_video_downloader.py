from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

from src.assets.semantic_selection import analyze_scene, check_continuity, ordered_queries, select_best_candidate
from src.news.asset_manager import build_news_asset_manifest
from src.providers import pexels_provider, pixabay_provider


REQUEST_TIMEOUT = 30
MIN_WIDTH = 1280
MIN_HEIGHT = 720


def download_stock_videos_for_project(project_root: str | Path, *, max_scenes: int = 10) -> dict[str, Any]:
    load_dotenv()
    root = Path(project_root)
    visual_plan = _read_json(root / "localizations" / "ru" / "visual" / "visual_plan.json")
    limited_plan = {**visual_plan, "scenes": list(visual_plan.get("scenes", []))[:max_scenes]}
    manifest = build_news_asset_manifest(
        visual_plan=limited_plan,
        user_assets=[],
        dry_run=False,
        project_root=root,
        project_id=root.name,
    )
    _write_json(root / "assets" / "assets_manifest.json", manifest)
    _write_json(root / "assets" / "missing_assets.json", {"missing_scenes": manifest.get("missing_scenes", [])})
    return manifest


def _legacy_download_stock_videos_for_project(project_root: str | Path, *, max_scenes: int = 10) -> dict[str, Any]:
    load_dotenv()
    root = Path(project_root)
    visual_plan = _read_json(root / "localizations" / "ru" / "visual" / "visual_plan.json")
    target_dir = root / "assets" / "stock_videos"
    target_dir.mkdir(parents=True, exist_ok=True)
    providers_used: set[str] = set()
    downloaded: list[dict[str, Any]] = []
    scene_entries: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    used_source_ids: set[str] = set()

    for scene in visual_plan.get("scenes", [])[:max_scenes]:
        semantic_scene = analyze_scene(scene)
        semantic_queries = ordered_queries(semantic_scene)
        queries = [str(item["query"]) for item in semantic_queries if int(item["fallback_level"]) < 4 or semantic_scene.visual_priority in {"environment", "transition"}]
        queries.extend(scene.get("alternative_queries") or [])
        queries = _dedupe_queries([query for query in queries if query and not query.startswith("create_custom_animation")])
        selected: dict[str, Any] | None = None
        candidates: list[dict[str, Any]] = []
        for query in queries:
            hits = _search_real_video_candidates(query)
            candidates.extend([{**hit, "search_query": query} for hit in hits])
        candidates = [candidate for candidate in candidates if candidate["source_id"] not in used_source_ids]
        ranked = select_best_candidate(semantic_scene, candidates, used_asset_ids={f"{item}" for item in used_source_ids})[1]
        best = next((candidate for candidate in ranked if not candidate.get("rejected")), None)
        if best:
            path = target_dir / f"{scene['scene_id']}_{_safe(best['provider'])}_{_safe(best['source_id'])}.mp4"
            if _download_file(best["direct_download_url"], path):
                selected = {
                    **best,
                    "asset_id": f"{best['provider']}_{best['source_id']}",
                    "path": str(path),
                    "downloaded_path": str(path),
                    "type": "video",
                    "scene_id": scene["scene_id"],
                    "scene_assignment": scene["scene_id"],
                    "rights_status": "licensed",
                    "allowed_for_render": True,
                    "selected_by": "semantic_stock_video_download",
                }
                used_source_ids.add(best["source_id"])
                providers_used.add(best["provider"])
                downloaded.append(selected)
        if selected:
            scene_entries.append(
                {
                    "scene_id": scene["scene_id"],
                    "primary_query": scene.get("primary_query", ""),
                    "visual_type": "video",
                    "semantic_scene": semantic_scene.to_dict(),
                    "selected_asset": selected,
                    "candidates": ranked[:5],
                    "rejected_candidates": [candidate for candidate in ranked if candidate.get("rejected")][:5],
                }
            )
        else:
            missing.append(
                {
                    "scene_id": scene["scene_id"],
                    "queries": queries,
                    "semantic_scene": semantic_scene.to_dict(),
                    "reason": "no_semantic_video_above_threshold",
                }
            )
            scene_entries.append(
                {
                    "scene_id": scene["scene_id"],
                    "primary_query": scene.get("primary_query", ""),
                    "visual_type": scene.get("visual_type", ""),
                    "semantic_scene": semantic_scene.to_dict(),
                    "selected_asset": None,
                    "candidates": ranked[:5] if candidates else [],
                }
            )
    continuity = check_continuity(scene_entries)
    if continuity["status"] == "failed":
        missing.extend({"scene_id": issue["scene_id"], "reason": issue["reason"]} for issue in continuity["issues"])

    manifest = {
        "mode": "news_to_short",
        "dry_run": False,
        "asset_selection": {
            "mode": "semantic",
            "legacy_fallback_enabled": False,
            "vision_validation_enabled": False,
        },
        "providers_used": sorted(providers_used),
        "provider_order": ["user_assets", "local_library", "pexels", "pixabay"],
        "assets": downloaded,
        "scenes": scene_entries,
        "missing_scenes": missing,
        "continuity": continuity,
        "provider_errors": [],
        "warnings": [] if not missing else [f"{len(missing)} scene(s) still need real video assets."],
    }
    _write_json(root / "assets" / "assets_manifest.json", manifest)
    _write_json(root / "assets" / "missing_assets.json", {"missing_scenes": missing})
    return manifest


def _search_real_video_candidates(query: str) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    pexels_key = os.getenv("PEXELS_API_KEY", "")
    pixabay_key = os.getenv("PIXABAY_API_KEY", "")
    if pexels_key:
        try:
            for video in pexels_provider.search_videos(pexels_key, query, per_page=6):
                best = _best_pexels_file(video.get("video_files", []))
                if not best:
                    continue
                candidates.append(
                    {
                        "provider": "pexels",
                        "source_id": str(video.get("id", "")),
                        "source_page": video.get("url", ""),
                        "source_url": video.get("url", ""),
                        "direct_download_url": best.get("link", ""),
                        "author": video.get("user", {}).get("name", ""),
                        "license": "pexels",
                        "width": int(best.get("width") or video.get("width") or 0),
                        "height": int(best.get("height") or video.get("height") or 0),
                        "duration": float(video.get("duration") or 0),
                        "orientation": _orientation(int(best.get("width") or 0), int(best.get("height") or 0)),
                    }
                )
        except Exception:
            pass
    if pixabay_key:
        try:
            for hit in pixabay_provider.search_videos(pixabay_key, query, per_page=6):
                video = _best_pixabay_file(hit.get("videos", {}))
                if not video:
                    continue
                candidates.append(
                    {
                        "provider": "pixabay",
                        "source_id": str(hit.get("id", "")),
                        "source_page": hit.get("pageURL", ""),
                        "source_url": hit.get("pageURL", ""),
                        "direct_download_url": video.get("url", ""),
                        "author": hit.get("user", ""),
                        "license": "pixabay",
                        "width": int(video.get("width") or 0),
                        "height": int(video.get("height") or 0),
                        "duration": float(hit.get("duration") or 0),
                        "orientation": _orientation(int(video.get("width") or 0), int(video.get("height") or 0)),
                    }
                )
        except Exception:
            pass
    candidates = [item for item in candidates if item.get("direct_download_url") and int(item.get("width") or 0) >= MIN_WIDTH and int(item.get("height") or 0) >= MIN_HEIGHT]
    candidates.sort(key=lambda item: (_orientation_rank(item["orientation"]), item["width"] * item["height"]), reverse=True)
    return candidates


def _best_pexels_file(files: list[dict[str, Any]]) -> dict[str, Any] | None:
    valid = [item for item in files if item.get("link") and item.get("file_type", "").startswith("video")]
    valid.sort(key=lambda item: (_orientation_rank(_orientation(int(item.get("width") or 0), int(item.get("height") or 0))), int(item.get("width") or 0) * int(item.get("height") or 0)), reverse=True)
    return valid[0] if valid else None


def _best_pixabay_file(videos: dict[str, Any]) -> dict[str, Any] | None:
    valid = [item for item in videos.values() if isinstance(item, dict) and item.get("url")]
    valid.sort(key=lambda item: (_orientation_rank(_orientation(int(item.get("width") or 0), int(item.get("height") or 0))), int(item.get("width") or 0) * int(item.get("height") or 0)), reverse=True)
    return valid[0] if valid else None


def _download_file(url: str, target: Path) -> bool:
    if target.exists() and target.stat().st_size > 100_000:
        return True
    try:
        with requests.get(url, stream=True, timeout=REQUEST_TIMEOUT) as response:
            response.raise_for_status()
            with target.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=1024 * 512):
                    if chunk:
                        handle.write(chunk)
        return target.exists() and target.stat().st_size > 100_000
    except Exception:
        if target.exists():
            target.unlink()
        return False


def _orientation(width: int, height: int) -> str:
    if height > width:
        return "vertical"
    if width > height:
        return "horizontal"
    return "square"


def _orientation_rank(orientation: str) -> int:
    return {"vertical": 3, "horizontal": 2, "square": 1}.get(orientation, 0)


def _safe(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", value).strip("_")[:80] or "asset"


def _dedupe_queries(queries: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for query in queries:
        normalized = query.lower().strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(query)
    return result


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
