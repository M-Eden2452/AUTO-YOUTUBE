from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from src.assets.frame_sampling import ffprobe_media_info


def describe_output_file(path: str | Path, *, project_root: str | Path | None = None) -> dict[str, Any]:
    """Build the Phase-13 output report for one produced file.

    Always returns absolute_path/project_relative_path/filename/exists even
    when the file is missing (e.g. a prepare_only/dry_run result), so callers
    never have to guess a path themselves.
    """
    resolved = Path(path).resolve()
    report: dict[str, Any] = {
        "absolute_path": str(resolved),
        "filename": resolved.name,
        "project_relative_path": "",
        "exists": resolved.is_file(),
        "type": resolved.suffix.lstrip(".") or "unknown",
        "size_bytes": 0,
        "duration_sec": None,
        "resolution": None,
        "audio_present": None,
    }
    if project_root:
        try:
            report["project_relative_path"] = str(resolved.relative_to(Path(project_root).resolve()))
        except ValueError:
            report["project_relative_path"] = str(resolved)
    if not report["exists"]:
        return report
    report["size_bytes"] = resolved.stat().st_size
    if report["type"] in {"mp4", "mov", "m4v", "wav", "mp3"}:
        info = ffprobe_media_info(resolved)
        if info.get("status") == "passed":
            report["duration_sec"] = info.get("duration_sec")
            if info.get("width") and info.get("height"):
                report["resolution"] = f"{info['width']}x{info['height']}"
        report["audio_present"] = _has_audio_stream(resolved)
    return report


def _has_audio_stream(path: Path) -> bool | None:
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", str(path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode != 0:
            return None
        data = json.loads(result.stdout or "{}")
        return any(stream.get("codec_type") == "audio" for stream in data.get("streams", []))
    except Exception:
        return None
