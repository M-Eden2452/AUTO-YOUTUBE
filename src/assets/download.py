from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from PIL import Image

from .http_client import ProviderHttpClient
from .models import AssetCandidate, DownloadedAsset, orientation_from_dimensions, utc_now_iso
from .provider_contract import DownloadContext, ProviderDownloadError, ProviderValidationError, ensure_license_allows_render


IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
VIDEO_CONTENT_TYPES = {"video/mp4", "video/quicktime", "video/webm", "video/ogg", "application/ogg", "application/octet-stream"}


def download_candidate_asset(
    candidate: AssetCandidate,
    destination: str | Path,
    context: DownloadContext,
    *,
    http: ProviderHttpClient | None = None,
) -> DownloadedAsset:
    ensure_license_allows_render(candidate)
    target = Path(destination) / _filename_for_candidate(candidate)
    client = http or ProviderHttpClient(timeout=context.timeout_sec)
    allowed = IMAGE_CONTENT_TYPES if candidate.media_type == "image" else VIDEO_CONTENT_TYPES
    result = client.download_stream(
        candidate.download_url,
        target,
        allowed_content_types=allowed,
        max_bytes=context.max_file_size_bytes,
        min_bytes=context.min_file_size_bytes,
        timeout=context.timeout_sec,
    )
    validation = validate_local_asset(target, candidate.media_type)
    return _downloaded_from_validation(candidate, target, result["checksum_sha256"], validation, context)


def copy_candidate_fixture(candidate: AssetCandidate, fixture: str | Path, destination: str | Path, context: DownloadContext) -> DownloadedAsset:
    ensure_license_allows_render(candidate)
    source = Path(fixture)
    if not source.exists():
        raise ProviderDownloadError(f"Fixture does not exist: {source}")
    target = Path(destination) / _filename_for_candidate(candidate, source.suffix)
    target.parent.mkdir(parents=True, exist_ok=True)
    part = target.with_suffix(target.suffix + ".part")
    if part.exists():
        part.unlink()
    shutil.copyfile(source, part)
    part.replace(target)
    checksum = sha256_file(target)
    validation = validate_local_asset(target, candidate.media_type)
    return _downloaded_from_validation(candidate, target, checksum, validation, context)


def validate_local_asset(path: str | Path, media_type: str) -> dict[str, Any]:
    target = Path(path)
    if not target.exists() or target.stat().st_size <= 0:
        raise ProviderValidationError(f"Asset file is missing or empty: {target}")
    if media_type == "image":
        return _validate_image(target)
    if media_type == "video":
        return _validate_video(target)
    raise ProviderValidationError(f"Unsupported media type for validation: {media_type}")


def sha256_file(path: str | Path) -> str:
    sha = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            sha.update(chunk)
    return sha.hexdigest()


def _validate_image(path: Path) -> dict[str, Any]:
    try:
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            width, height = image.size
            mode = image.mode
    except Exception as exc:
        raise ProviderValidationError(f"Image validation failed: {path}") from exc
    return {
        "status": "passed",
        "media_type": "image",
        "width": int(width),
        "height": int(height),
        "orientation": orientation_from_dimensions(int(width), int(height)),
        "mode": mode,
    }


def _validate_video(path: Path) -> dict[str, Any]:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_streams",
        "-show_format",
        str(path),
    ]
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise ProviderValidationError((result.stderr or "").strip() or f"Video validation failed: {path}")
    try:
        data = json.loads(result.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise ProviderValidationError(f"FFprobe returned invalid JSON for {path}") from exc
    video_stream = next((stream for stream in data.get("streams", []) if stream.get("codec_type") == "video"), None)
    if not video_stream:
        raise ProviderValidationError(f"No video stream found in {path}")
    width = int(video_stream.get("width") or 0)
    height = int(video_stream.get("height") or 0)
    duration = float(video_stream.get("duration") or data.get("format", {}).get("duration") or 0)
    return {
        "status": "passed",
        "media_type": "video",
        "width": width,
        "height": height,
        "duration_sec": duration,
        "orientation": orientation_from_dimensions(width, height),
        "codec": str(video_stream.get("codec_name") or ""),
    }


def _downloaded_from_validation(
    candidate: AssetCandidate,
    target: Path,
    checksum: str,
    validation: dict[str, Any],
    context: DownloadContext,
) -> DownloadedAsset:
    candidate.width = int(validation.get("width") or candidate.width)
    candidate.height = int(validation.get("height") or candidate.height)
    candidate.orientation = str(validation.get("orientation") or candidate.orientation)
    if validation.get("duration_sec"):
        candidate.duration_sec = float(validation["duration_sec"])
    candidate.project_id = candidate.project_id or context.project_id
    candidate.scene_id = candidate.scene_id or context.scene_id
    candidate.provenance.project_id = candidate.project_id
    candidate.provenance.scene_id = candidate.scene_id
    candidate.provenance.search_query = candidate.provenance.search_query or context.search_query or candidate.search_query
    candidate.provenance.download_url = candidate.provenance.download_url or candidate.download_url
    candidate.provenance.source_page_url = candidate.provenance.source_page_url or candidate.source_page_url
    return DownloadedAsset.from_candidate(
        candidate,
        local_path=str(target),
        checksum_sha256=checksum,
        downloaded_at=utc_now_iso(),
        technical_validation=validation,
    )


def _filename_for_candidate(candidate: AssetCandidate, suffix_override: str = "") -> str:
    suffix = suffix_override or _suffix_from_url(candidate.download_url) or (".jpg" if candidate.media_type == "image" else ".mp4")
    stem = "_".join(
        part
        for part in (
            _safe(candidate.scene_id or "scene"),
            _safe(candidate.provider),
            _safe(candidate.provider_asset_id or candidate.asset_id),
        )
        if part
    )
    return f"{stem[:120] or 'asset'}{suffix}"


def _suffix_from_url(url: str) -> str:
    path = url.split("?", 1)[0].rstrip("/")
    suffix = Path(path).suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".webp", ".mp4", ".mov", ".m4v", ".webm", ".ogv", ".mpeg", ".mpg"}:
        return suffix
    return ""


def _safe(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", str(value or "")).strip("_")[:80]
