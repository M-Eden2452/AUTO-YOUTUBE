from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import imageio_ffmpeg


def render_preview(project_root: str | Path, script: dict[str, Any], *, width: int = 360, height: int = 640) -> dict[str, Any]:
    root = Path(project_root)
    target = root / "preview" / "preview.mp4"
    target.parent.mkdir(parents=True, exist_ok=True)
    final_video = root / "localizations" / str(script.get("language", "ru")) / "output" / "master_1080x1920.mp4"
    if not final_video.exists():
        return {
            "status": "blocked",
            "reason": "preview_requires_real_rendered_video",
            "path": "",
            "preview_type": "blocked_no_placeholders",
        }
    duration = max(1.0, min(12.0, float(script.get("estimated_duration_sec") or 6.0)))
    command = [
        imageio_ffmpeg.get_ffmpeg_exe(),
        "-y",
        "-v",
        "error",
        "-i",
        str(final_video),
        "-t",
        f"{duration:.3f}",
        "-vf",
        f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},setsar=1,fps=30,format=yuv420p",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "26",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        str(target),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "FFmpeg preview render failed.")
    return {
        "status": "completed",
        "path": str(target),
        "duration_sec": duration,
        "resolution": {"width": width, "height": height},
        "preview_type": "real_video_excerpt",
    }
