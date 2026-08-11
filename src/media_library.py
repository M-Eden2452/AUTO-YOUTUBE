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
        checksum_sha256=normalized.get("checksum_sha256", ""),
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
    checksum_sha256: str = "",
) -> dict[str, Any] | None:
    source_url = source_url or download_url
    normalized_path = _path_key(local_path)
    checksum_sha256 = str(checksum_sha256 or "").lower()
    for item in index.get("items", []):
        if checksum_sha256 and str(item.get("checksum_sha256") or "").lower() == checksum_sha256:
            return item
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


def build_media_library_migration_report(index: dict[str, Any]) -> dict[str, Any]:
    report, _proposal = _build_media_library_migration(index)
    return report


def analyse_media_library(
    *,
    index_path: str | Path = INDEX_PATH,
    report_path: str | Path | None = None,
) -> dict[str, Any]:
    index = load_media_index(index_path)
    report = build_media_library_migration_report(index)
    if report_path:
        _atomic_write_json(project_path(report_path), report)
    return report


def migrate_media_library(
    *,
    index_path: str | Path = INDEX_PATH,
    dry_run: bool = False,
    apply: bool = False,
    output_path: str | Path | None = None,
    report_path: str | Path | None = None,
    backup_path: str | Path | None = None,
    confirm_apply: bool = False,
) -> dict[str, Any]:
    if apply and dry_run:
        raise ValueError("Use either dry_run or apply, not both.")
    if not apply and not dry_run:
        raise ValueError("Migration requires dry_run=True or apply=True.")
    target_index = project_path(index_path)
    index = load_media_index(target_index)
    report, proposal = _build_media_library_migration(index)
    result = {
        "dry_run": bool(dry_run),
        "applied": False,
        "index_path": str(target_index),
        "output_path": str(project_path(output_path)) if output_path else "",
        "report_path": str(project_path(report_path)) if report_path else "",
        "backup_path": str(project_path(backup_path)) if backup_path else "",
        "records_total": report["records_total"],
        "safe_records": report["safe_records"],
        "review_records": report["review_records"],
        "quarantine_records": report["quarantine_records"],
        "errors": report["errors"],
    }
    if output_path:
        _atomic_write_json(project_path(output_path), proposal)
    if report_path:
        _atomic_write_json(project_path(report_path), report)
    if dry_run:
        return result
    if not confirm_apply:
        raise PermissionError("Media library migration apply requires confirm_apply=True.")
    if not output_path or not backup_path:
        raise ValueError("Media library migration apply requires explicit output_path and backup_path.")
    if report["errors"]:
        raise RuntimeError("Media library migration apply requires a dry-run report without errors.")
    backup = project_path(backup_path)
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(target_index, backup)
    _atomic_write_json(target_index, proposal)
    result["applied"] = True
    return result


def _build_media_library_migration(index: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    items = [dict(item) for item in index.get("items", [])]
    seen_urls: dict[str, str] = {}
    seen_checksums: dict[str, str] = {}
    report_items = []
    proposed_items = []
    for item in items:
        report_item = _classify_media_record(item, seen_urls=seen_urls, seen_checksums=seen_checksums)
        report_items.append(report_item)
        proposed_items.append(_propose_media_record(item, report_item))
    safe_records = sum(1 for item in report_items if item["proposed_status"] == "current_safe")
    quarantine_records = sum(1 for item in report_items if "quarantine_recommended" in item["classifications"])
    review_records = sum(1 for item in report_items if "manual_review_required" in item["classifications"])
    report = {
        "schema_version": 1,
        "dry_run": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "records_total": len(report_items),
        "total_items": len(report_items),
        "safe_records": safe_records,
        "review_records": review_records,
        "quarantine_records": quarantine_records,
        "errors": quarantine_records,
        "current_items": safe_records,
        "legacy_unknown_items": sum(1 for item in report_items if "legacy_incomplete" in item["classifications"] or "legacy_complete" in item["classifications"]),
        "items": report_items,
    }
    proposal = {
        "schema_version": 1,
        "source_version": index.get("version", 1),
        "generated_at": report["generated_at"],
        "items": proposed_items,
    }
    return report, proposal


def _classify_media_record(
    item: dict[str, Any],
    *,
    seen_urls: dict[str, str],
    seen_checksums: dict[str, str],
) -> dict[str, Any]:
    item_id = str(item.get("id") or item.get("asset_id") or "")
    provider = str(item.get("provider") or "")
    media_type = str(item.get("type") or item.get("media_type") or "")
    local_path = str(item.get("local_path") or item.get("path") or "")
    source_url = str(item.get("source_url") or item.get("source_page_url") or item.get("source_page") or "")
    license_value = item.get("license") if item.get("license") else item.get("license_note", "")
    checksum = str(item.get("checksum_sha256") or "").lower()
    schema_version = int(item.get("schema_version") or 0)
    missing_fields = [
        field
        for field, value in {
            "schema_version": item.get("schema_version"),
            "provider": provider,
            "type": media_type,
            "local_path": local_path,
            "source_url": source_url,
            "provider_asset_id": item.get("provider_asset_id"),
            "author": item.get("author"),
            "rights_status": item.get("rights_status"),
            "checksum_sha256": checksum,
            "license": item.get("license"),
            "provenance": item.get("provenance"),
        }.items()
        if not value
    ]
    classifications: list[str] = []
    has_license_object = isinstance(item.get("license"), dict)
    has_provenance = isinstance(item.get("provenance"), dict)
    if schema_version >= 1 and has_license_object and has_provenance and item.get("allowed_for_render") and not item.get("review_required"):
        classifications.append("current_safe")
    elif schema_version == 0:
        legacy_required = [provider, media_type, local_path, source_url, license_value]
        classifications.append("legacy_complete" if all(legacy_required) else "legacy_incomplete")
    if local_path and not project_path(local_path).exists():
        classifications.append("missing_file")
    if not source_url:
        classifications.append("missing_source")
    if not has_license_object or not item.get("rights_status") or item.get("review_required", True):
        classifications.append("unknown_rights")
    if source_url:
        if source_url in seen_urls:
            classifications.append("duplicate_url")
        else:
            seen_urls[source_url] = item_id
    if checksum:
        if checksum in seen_checksums:
            classifications.append("duplicate_checksum")
        else:
            seen_checksums[checksum] = item_id
    if provider in {"manual", "manual_asset", "user", "local"} and "current_safe" not in classifications:
        classifications.append("manual_review_required")
    if any(flag in classifications for flag in ("legacy_complete", "legacy_incomplete", "missing_file", "missing_source", "unknown_rights", "duplicate_url", "duplicate_checksum", "manual_review_required")):
        if "current_safe" not in classifications:
            classifications.append("quarantine_recommended")
    classifications = list(dict.fromkeys(classifications))
    if "current_safe" in classifications:
        proposed_status = "current_safe"
        proposed_action = "keep"
    elif "quarantine_recommended" in classifications:
        proposed_status = "quarantine_recommended"
        proposed_action = "quarantine_or_manual_review"
    else:
        proposed_status = "manual_review_required"
        proposed_action = "manual_review"
    reason = "|".join(classifications) if classifications else "no_classification"
    return {
        "id": item_id,
        "provider": provider,
        "type": media_type,
        "local_path": local_path,
        "source_url": source_url,
        "license": license_value,
        "checksum_sha256": checksum,
        "schema_version": schema_version,
        "missing_fields": missing_fields,
        "classifications": classifications,
        "proposed_status": proposed_status,
        "proposed_action": proposed_action,
        "reason": reason,
        "migration_status": "current" if proposed_status == "current_safe" else "legacy_unknown",
        "review_required": proposed_status != "current_safe",
        "commercial_use_allowed": bool((item.get("license") or {}).get("commercial_use_allowed", False)) if isinstance(item.get("license"), dict) else False,
    }


def _propose_media_record(item: dict[str, Any], report_item: dict[str, Any]) -> dict[str, Any]:
    proposed = dict(item)
    proposed.setdefault("schema_version", int(item.get("schema_version") or 0))
    if report_item["proposed_status"] != "current_safe":
        proposed["allowed_for_render"] = False
        proposed["review_required"] = True
        proposed.setdefault("rights_status", "legacy_unknown")
    proposed["migration"] = {
        "proposed_status": report_item["proposed_status"],
        "proposed_action": report_item["proposed_action"],
        "classifications": report_item["classifications"],
        "reason": report_item["reason"],
    }
    return proposed


def _atomic_write_json(path: Path, data: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)
    return path


def _normalize_asset(asset: dict[str, Any]) -> dict[str, Any]:
    item = {
        "schema_version": int(asset.get("schema_version") or 1),
        "id": asset.get("id") or asset.get("asset_id") or _asset_id(asset),
        "type": asset.get("type") or asset.get("media_type", ""),
        "provider": asset.get("provider", "local"),
        "provider_asset_id": asset.get("provider_asset_id") or asset.get("source_id", ""),
        "source_url": asset.get("source_url") or asset.get("source_page_url", ""),
        "source_page_url": asset.get("source_page_url") or asset.get("source_page") or asset.get("source_url", ""),
        "preview_url": asset.get("preview_url", ""),
        "download_url": asset.get("download_url") or asset.get("direct_download_url", ""),
        "local_path": asset.get("local_path") or asset.get("path", ""),
        "original_filename": asset.get("original_filename", ""),
        "thumbnail_path": asset.get("thumbnail_path", ""),
        "original_query": asset.get("original_query") or asset.get("query", ""),
        "keywords": _as_list(asset.get("keywords")),
        "tags": _as_list(asset.get("tags")),
        "mood": _as_list(asset.get("mood")),
        "channel_tags": _as_list(asset.get("channel_tags")),
        "scene_tags": _as_list(asset.get("scene_tags")),
        "width": int(asset.get("width") or 0),
        "height": int(asset.get("height") or 0),
        "duration": float(asset.get("duration") or asset.get("source_duration") or 0),
        "duration_sec": float(asset.get("duration_sec") or asset.get("duration") or asset.get("source_duration") or 0),
        "fps": float(asset.get("fps") or 0),
        "author": asset.get("author") or asset.get("author_name", ""),
        "author_url": asset.get("author_url", ""),
        "rights_status": asset.get("rights_status", ""),
        "allowed_for_render": bool(asset.get("allowed_for_render", False)),
        "review_required": bool(asset.get("review_required", False)),
        "license": asset.get("license") if isinstance(asset.get("license"), dict) else {},
        "license_name": asset.get("license_name") or (asset.get("license") if isinstance(asset.get("license"), str) else ""),
        "license_url": asset.get("license_url", ""),
        "provenance": asset.get("provenance") if isinstance(asset.get("provenance"), dict) else {},
        "checksum_sha256": asset.get("checksum_sha256", ""),
        "project_id": asset.get("project_id", ""),
        "scene_id": asset.get("scene_id", ""),
        "technical_validation": asset.get("technical_validation") if isinstance(asset.get("technical_validation"), dict) else {},
        "license_note": asset.get("license_note", ""),
        "downloaded_at": asset.get("downloaded_at") or datetime.now(timezone.utc).isoformat(),
        "used_in": list(asset.get("used_in", [])),
    }
    replaces_asset_id = str(asset.get("replaces_asset_id") or "")
    if replaces_asset_id:
        item["replaces_asset_id"] = replaces_asset_id
    if "vision_tags" in asset:
        item.update(
            {
                "vision_tags": _as_list(asset.get("vision_tags")),
                "vision_tags_asset_id": str(
                    asset.get("vision_tags_asset_id") or ""
                ),
                "vision_tags_source_sha256": str(
                    asset.get("vision_tags_source_sha256") or ""
                ),
                "vision_tags_cache_key": str(
                    asset.get("vision_tags_cache_key") or ""
                ),
            }
        )
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
