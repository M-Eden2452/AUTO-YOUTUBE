from __future__ import annotations

from pathlib import Path
from typing import Any

from moviepy import ImageSequenceClip

from .layout_renderer import render_quote_frame
from .music_tools import add_background_music
from .utils import project_path


def build_render_plan(config: dict[str, Any], scene_plan: dict[str, Any], asset_plan: dict[str, Any]) -> dict[str, Any]:
    output_path = project_path(config["output_filename"])
    silent_path = output_path.with_name(output_path.stem + "_silent.mp4")
    return {
        "output_path": str(output_path),
        "silent_video_path": str(silent_path),
        "resolution": config["resolution"],
        "fps": int(config["fps"]),
        "duration": float(scene_plan["scenes"][0]["duration"]),
        "layout": config["layout"],
        "animation": config["animation_type"],
        "music": asset_plan["music"]
    }


def render_video(config: dict[str, Any], scene_plan: dict[str, Any], asset_plan: dict[str, Any], render_plan: dict[str, Any]) -> Path:
    output_path = Path(render_plan["output_path"])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    silent_path = Path(render_plan["silent_video_path"])

    fps = int(render_plan["fps"])
    duration = float(render_plan["duration"])
    total_frames = max(1, int(round(fps * duration)))
    scene = scene_plan["scenes"][0]
    image_path = asset_plan["image"]["path"]

    frames = [
        render_quote_frame(config, scene, image_path, index, total_frames)
        for index in range(total_frames)
    ]
    clip = ImageSequenceClip(frames, fps=fps)
    clip.write_videofile(str(silent_path), fps=fps, codec="libx264", audio=False)
    clip.close()

    music = asset_plan["music"]
    if music["status"] == "found":
        added = add_background_music(silent_path, music["path"], output_path, float(music["volume"]))
        if added:
            return output_path

    if output_path.exists():
        output_path.unlink()
    silent_path.replace(output_path)
    return output_path
