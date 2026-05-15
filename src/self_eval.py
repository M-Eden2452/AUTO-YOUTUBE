from __future__ import annotations

from pathlib import Path
from typing import Any

from moviepy import VideoFileClip


def evaluate_render(output_path: str | Path, config: dict[str, Any], asset_plan: dict[str, Any]) -> dict[str, Any]:
    path = Path(output_path)
    checks: list[str] = []
    warnings: list[str] = []

    if not path.exists() or path.stat().st_size == 0:
        return {"ok": False, "checks": checks, "warnings": ["Output video is missing or empty."]}

    checks.append("Output video exists and is not empty.")
    clip = VideoFileClip(str(path))
    duration = float(clip.duration or 0)
    width, height = clip.size
    clip.close()

    expected_duration = float(config["scene_duration"])
    if abs(duration - expected_duration) <= 0.35:
        checks.append(f"Duration is close to target: {duration:.2f}s.")
    else:
        warnings.append(f"Duration differs from target: {duration:.2f}s vs {expected_duration:.2f}s.")

    if [width, height] == [int(v) for v in config["resolution"]]:
        checks.append(f"Resolution matches config: {width}x{height}.")
    else:
        warnings.append(f"Resolution mismatch: {width}x{height}.")

    if asset_plan["image"]["status"] != "found_local":
        warnings.append("Used generated portrait placeholder because no local Jordan Peterson image was found.")
    if asset_plan["music"]["status"] != "found":
        warnings.append("Rendered silent fallback because music file was not found.")

    return {"ok": path.exists(), "checks": checks, "warnings": warnings}
