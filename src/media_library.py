from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import imageio_ffmpeg

from .utils import project_path


LIBRARY_ROOT = Path("assets/library")
INDEX_PATH = LIBRARY_ROOT / "metadata/media_index.json"
MEDIA_EXTENSIONS = {
    "video": {".mp4", ".mov", ".m4v"},
    "image": {".jpg", ".jpeg", ".png", ".webp"},
    "music": {".mp3", ".wav", ".m4a"},
}


def ensure_media_library(root: str | Path = LIBRARY_ROOT) -> Path:
    base = project_path(root)
    for name in ("videos", "images", "music", "thumbnails", "metadata"):
        (base / name).mkdir(parents=True, exist_ok=True)
    index_path = base / "metadata/media_index.json"
    if not index_path.exists():
        save_media_index({"version": 1, "items": []}, index_path)
    return base


def load_media_index(index_path: str | Path = INDEX_PATH) -> dict[str, Any]:
    target = project_path(index_path)
    if not target.exists():
        return {"version": 1, "items": []}
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"version": 1, "items": []}
    if not isinstance(data, dict):
        return {"version": 1, "items": []}
    data.setdefault("version", 1)
    data.setdefault("items", [])
    return data


def save_media_index(index: dict[str, Any], index_path: str | Path = INDEX_PATH) -> Path:
    target = project_path(index_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def register_asset(index: dict[str, Any], asset: dict[str, Any]) -> dict[str, Any]:
    normalized = _normalize_asset(asset)
    duplicate = avoid_duplicate_downloads(
        index,
        source_url=normalized.get("source_url") or normalized.get("download_url", ""),
        local_path=normalized.get("local_path", ""),
    )
    if duplicate:
        duplicate.update({key: value for key, value in normalized.items() if value not in ("", [], 0, None)})
        duplicate.setdefault("used_in", [])
        return duplicate
    index.setdefault("items", []).append(normalized)
    return normalized


def search_local_assets(
    index: dict[str, Any],
    scene: dict[str, Any],
    media_type: str,
    channel: str = "",
    min_score: int = 4,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for item in index.get("items", []):
        if media_type and item.get("type") != media_type:
            continue
        path = str(item.get("local_path", ""))
        if path and not project_path(path).exists():
            continue
        score, reasons = _score_asset(item, scene, media_type, channel)
        if score >= min_score:
            matches.append({"asset": item, "score": score, "reasons": reasons})
    matches.sort(key=lambda match: (match["score"], float(match["asset"].get("duration") or 0)), reverse=True)
    return matches[:limit] if limit else matches


def generate_semantic_filename(
    media_type: str,
    provider: str,
    channel: str = "",
    keywords: list[str] | str | None = None,
    mood: list[str] | str | None = None,
    width: int = 0,
    height: int = 0,
    short_id: str = "",
    genre: str = "",
) -> str:
    extension = {"video": ".mp4", "image": ".jpg", "music": ".mp3"}.get(media_type, "")
    parts = [_slug(provider or "local"), _slug(media_type)]
    if media_type in {"video", "image"}:
        parts.extend([_slug(channel), _slug_list(keywords), _slug_list(mood)])
        if width and height:
            parts.append(f"{int(width)}x{int(height)}")
        parts.append(_slug(short_id or "asset"))
    elif media_type == "music":
        parts.extend([_slug(channel), _slug_list(mood), _slug(genre), _slug(short_id or "track")])
    else:
        parts.append(_slug(short_id or "asset"))
    stem = "_".join(part for part in parts if part)
    stem = re.sub(r"_+", "_", stem).strip("._-")[:132].strip("._-")
    return f"{stem}{extension}"


def create_video_thumbnail(video_path: str | Path, asset_id: str, library_root: str | Path = LIBRARY_ROOT) -> str:
    source = project_path(video_path)
    target = project_path(library_root) / "thumbnails" / f"{asset_id}.jpg"
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and target.stat().st_size > 0:
        return str(target)
    command = [
        imageio_ffmpeg.get_ffmpeg_exe(),
        "-y",
        "-v",
        "error",
        "-ss",
        "00:00:01",
        "-i",
        str(source),
        "-frames:v",
        "1",
        "-q:v",
        "3",
        str(target),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    return str(target) if result.returncode == 0 and target.exists() else ""


def avoid_duplicate_downloads(
    index: dict[str, Any],
    source_url: str = "",
    local_path: str = "",
    download_url: str = "",
) -> dict[str, Any] | None:
    source_url = source_url or download_url
    normalized_path = _path_key(local_path)
    for item in index.get("items", []):
        if source_url and source_url in {item.get("source_url"), item.get("download_url")}:
            return item
        if normalized_path and _path_key(str(item.get("local_path", ""))) == normalized_path:
            return item
    return None


def mark_asset_used_in_video(index: dict[str, Any], asset_id: str, video_id: str) -> bool:
    for item in index.get("items", []):
        if item.get("id") != asset_id:
            continue
        used_in = item.setdefault("used_in", [])
        if video_id and video_id not in used_in:
            used_in.append(video_id)
        return True
    return False


def index_existing_assets(library_root: str | Path = LIBRARY_ROOT, index_path: str | Path = INDEX_PATH) -> dict[str, Any]:
    ensure_media_library(library_root)
    index = load_media_index(index_path)
    base = project_path(library_root)
    for media_type, extensions in MEDIA_EXTENSIONS.items():
        folder = base / f"{media_type}s" if media_type != "music" else base / "music"
        for path in folder.glob("*"):
            if path.suffix.lower() not in extensions or not path.is_file():
                continue
            register_asset(
                index,
                {
                    "type": media_type,
                    "provider": "local",
                    "local_path": str(path),
                    "keywords": _tokens(path.stem),
                    "license_note": "Local asset; verify license before publishing.",
                },
            )
    save_media_index(index, index_path)
    return index


def clean_temp_files(paths: list[str | Path] | None = None) -> list[str]:
    targets = paths or ["outputs/render_temp"]
    removed: list[str] = []
    for raw_path in targets:
        path = project_path(raw_path)
        if path.exists() and path.is_dir():
            shutil.rmtree(path)
            removed.append(str(path))
    for pattern in ("*.TEMP*", "*TEMP*", "*.part"):
        for path in project_path("outputs").glob(pattern):
            if path.is_file():
                path.unlink()
                removed.append(str(path))
    return removed


def create_asset_report(index_path: str | Path = INDEX_PATH, output_path: str | Path = "outputs/asset_library_report.md") -> Path:
    index = load_media_index(index_path)
    items = index.get("items", [])
    counts: dict[str, int] = {}
    for item in items:
        counts[item.get("type", "unknown")] = counts.get(item.get("type", "unknown"), 0) + 1
    lines = ["# Asset Library Report", "", f"Total assets: {len(items)}", ""]
    for media_type in sorted(counts):
        lines.append(f"- {media_type}: {counts[media_type]}")
    lines.extend(["", "## Recent Assets", ""])
    for item in items[-25:]:
        lines.append(f"- `{item.get('id')}` | {item.get('type')} | {item.get('provider')} | {item.get('local_path')}")
    target = project_path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target


def _normalize_asset(asset: dict[str, Any]) -> dict[str, Any]:
    item = {
        "id": asset.get("id") or _asset_id(asset),
        "type": asset.get("type", ""),
        "provider": asset.get("provider", "local"),
        "source_url": asset.get("source_url", ""),
        "download_url": asset.get("download_url", ""),
        "local_path": asset.get("local_path") or asset.get("path", ""),
        "thumbnail_path": asset.get("thumbnail_path", ""),
        "original_query": asset.get("original_query") or asset.get("query", ""),
        "keywords": _as_list(asset.get("keywords")),
        "mood": _as_list(asset.get("mood")),
        "channel_tags": _as_list(asset.get("channel_tags")),
        "scene_tags": _as_list(asset.get("scene_tags")),
        "width": int(asset.get("width") or 0),
        "height": int(asset.get("height") or 0),
        "duration": float(asset.get("duration") or asset.get("source_duration") or 0),
        "fps": float(asset.get("fps") or 0),
        "license_note": asset.get("license_note", ""),
        "downloaded_at": asset.get("downloaded_at") or datetime.now(timezone.utc).isoformat(),
        "used_in": list(asset.get("used_in", [])),
    }
    return item


def _asset_id(asset: dict[str, Any]) -> str:
    raw = "|".join(
        [
            str(asset.get("provider", "")),
            str(asset.get("type", "")),
            str(asset.get("source_url") or asset.get("download_url") or asset.get("local_path") or asset.get("path", "")),
        ]
    )
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def _score_asset(item: dict[str, Any], scene: dict[str, Any], media_type: str, channel: str) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []
    item_keywords = set(_tokens(item.get("keywords", [])))
    scene_keywords = set(_tokens(scene.get("visual_keywords", []) or scene.get("image_query", "")))
    keyword_hits = item_keywords & scene_keywords
    if keyword_hits:
        score += 3 * len(keyword_hits)
        reasons.append(f"keyword:{','.join(sorted(keyword_hits))}")
    item_mood = set(_tokens(item.get("mood", [])))
    scene_mood = set(_tokens(scene.get("mood", "")))
    if item_mood & scene_mood:
        score += 2
        reasons.append("mood")
    if channel and _slug(channel) in set(_tokens(item.get("channel_tags", []))):
        score += 2
        reasons.append("channel")
    if item.get("type") == media_type:
        score += 1
        reasons.append("type")
    width, height = int(item.get("width") or 0), int(item.get("height") or 0)
    if width and height and abs((width / max(height, 1)) - (16 / 9)) <= 0.18:
        score += 1
        reasons.append("aspect_16_9")
    needed = float(scene.get("duration") or scene.get("needed_duration") or 0)
    if needed and float(item.get("duration") or 0) >= needed:
        score += 1
        reasons.append("duration")
    scene_type = _slug(str(scene.get("scene_type") or scene.get("type") or ""))
    if scene_type and scene_type in set(_tokens(item.get("scene_tags", []))):
        score += 1
        reasons.append("scene_type")
    return score, reasons


def _slug_list(value: list[str] | str | None) -> str:
    return "_".join(_slug(item) for item in _as_list(value)[:4] if _slug(item))


def _slug(value: Any) -> str:
    text = str(value or "").lower()
    text = re.sub(r"[^a-z0-9_-]+", "_", text)
    text = re.sub(r"_+", "_", text)
    return text.strip("_-")


def _tokens(value: Any) -> list[str]:
    raw = _as_list(value)
    tokens: list[str] = []
    for item in raw:
        tokens.extend(part for part in re.split(r"[^a-zA-Z0-9]+", str(item).lower()) if part)
    return tokens


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, tuple | set):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()] if str(value).strip() else []


def _path_key(value: str) -> str:
    if not value:
        return ""
    try:
        return str(project_path(value).resolve()).lower()
    except OSError:
        return value.replace("\\", "/").lower()
