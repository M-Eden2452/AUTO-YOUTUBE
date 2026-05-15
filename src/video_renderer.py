from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

import imageio_ffmpeg
from moviepy import VideoClip, VideoFileClip

from .layout_renderer import render_documentary_frame
from .music_tools import add_background_music
from .utils import project_path, write_json


class RenderStageError(RuntimeError):
    def __init__(self, stage: str, message: str):
        super().__init__(message)
        self.stage = stage
        self.message = message


def build_render_plan(
    config: dict[str, Any],
    scene_plan: dict[str, Any],
    asset_plan: dict[str, Any],
    music_plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    output_path = project_path(config["output_filename"])
    silent_path = output_path.with_name(output_path.stem + "_silent.mp4")
    partial_path = output_path.with_name(output_path.stem + "_silent.partial.mp4")
    temp_dir = output_path.parent / "render_temp"
    total_duration = sum(float(scene["duration"]) for scene in scene_plan.get("scenes", []))
    return {
        "output_path": str(output_path),
        "silent_video_path": str(silent_path),
        "partial_silent_video_path": str(partial_path),
        "temp_dir": str(temp_dir),
        "stage_log_path": str(project_path("outputs/render_stage.json")),
        "resolution": config["resolution"],
        "fps": int(config["fps"]),
        "duration": total_duration,
        "scene_count": len(scene_plan.get("scenes", [])),
        "layout": config["layout"],
        "animation": config["animation_type"],
        "music": music_plan or asset_plan["music"],
        "render_strategy": "scene_temp_clips_concat" if not config.get("dev_mode", False) else "single_scene_temp_clip",
        "preset": "ultrafast" if not config.get("dev_mode", False) else "medium",
    }


def render_video(
    config: dict[str, Any],
    scene_plan: dict[str, Any],
    asset_plan: dict[str, Any],
    render_plan: dict[str, Any],
    music_plan: dict[str, Any] | None = None,
) -> Path:
    output_path = Path(render_plan["output_path"])
    silent_path = Path(render_plan["silent_video_path"])
    partial_path = Path(render_plan["partial_silent_video_path"])
    temp_dir = Path(render_plan["temp_dir"])
    stage_log_path = Path(render_plan["stage_log_path"])

    _start_stage_log(stage_log_path, render_plan)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_dir.mkdir(parents=True, exist_ok=True)
    _unlink_if_exists(output_path)
    _unlink_if_exists(silent_path)
    _unlink_if_exists(partial_path)

    fps = int(render_plan["fps"])
    scene_assets = _scene_asset_map(asset_plan)
    fallback_image = asset_plan.get("image", {}).get("path")

    try:
        _stage(stage_log_path, "render_silent_started", "Начат рендер silent video по сценам.")
        scene_files = _render_scene_clips(config, scene_plan, scene_assets, fallback_image, temp_dir, fps, render_plan["preset"])
        _concat_scene_clips(scene_files, partial_path, temp_dir)
        _stage(stage_log_path, "render_silent_done", f"Silent partial создан: {partial_path}")

        _stage(stage_log_path, "validate_silent_started", "Проверка silent partial.")
        validation = validate_video_file(partial_path, expected_duration=float(render_plan["duration"]))
        if not validation["ok"]:
            raise RenderStageError("validate_silent_failed", "; ".join(validation["errors"]))
        _replace_file(partial_path, silent_path)
        _stage(stage_log_path, "validate_silent_done", f"Silent video валиден: {silent_path}")

        active_music = music_plan or render_plan.get("music") or {}
        music_path = active_music.get("path") or asset_plan.get("music", {}).get("path", "")
        music_status = active_music.get("status") or asset_plan.get("music", {}).get("status")
        if music_path and music_status in {"найдено", "найдена_локальная_музыка"}:
            _stage(stage_log_path, "add_music_started", f"Добавление музыки: {music_path}")
            added = add_background_music(silent_path, music_path, output_path, float(active_music.get("volume", 0.16)))
            if not added:
                raise RenderStageError("add_music_failed", "Музыкальный файл не найден или не был добавлен.")
            _stage(stage_log_path, "add_music_done", f"Финальное видео создано: {output_path}")
            return output_path

        _replace_file(silent_path, output_path)
        _stage(stage_log_path, "add_music_done", "Музыка не подключена, silent video использован как финальный файл.")
        return output_path
    except Exception as exc:
        stage = exc.stage if isinstance(exc, RenderStageError) else "failed"
        message = exc.message if isinstance(exc, RenderStageError) else str(exc)
        _stage(stage_log_path, "failed", message, failed_stage=stage)
        _unlink_if_exists(partial_path)
        raise RenderStageError(stage, message) from exc


def validate_video_file(path: str | Path, expected_duration: float, tolerance: float = 2.0) -> dict[str, Any]:
    target = Path(path)
    errors: list[str] = []
    if not target.exists() or target.stat().st_size == 0:
        return {"ok": False, "errors": ["Файл отсутствует или пустой."]}

    clip = None
    try:
        clip = VideoFileClip(str(target))
        duration = float(clip.duration or 0)
        if abs(duration - expected_duration) > tolerance:
            errors.append(f"Длительность {duration:.2f} сек. не совпадает с ожидаемой {expected_duration:.2f} сек.")
        if not clip.size or clip.size[0] <= 0 or clip.size[1] <= 0:
            errors.append("Видео не содержит валидный размер кадра.")
    except Exception as exc:
        errors.append(f"Видео не читается: {exc}")
    finally:
        if clip:
            clip.close()
    return {"ok": not errors, "errors": errors}


def _render_scene_clips(
    config: dict[str, Any],
    scene_plan: dict[str, Any],
    scene_assets: dict[int, str],
    fallback_image: str | None,
    temp_dir: Path,
    fps: int,
    preset: str,
) -> list[Path]:
    scene_files: list[Path] = []
    for scene in scene_plan.get("scenes", []):
        scene_number = int(scene.get("scene_number", len(scene_files) + 1))
        scene_path = temp_dir / f"scene_{scene_number:03d}.mp4"
        image_path = scene_assets.get(scene_number, fallback_image)
        duration = float(scene["duration"])

        def make_frame(t: float, current_scene=scene, current_image=image_path, current_duration=duration):
            progress = t / max(current_duration, 0.001)
            return render_documentary_frame(config, current_scene, current_image, min(progress, 1.0))

        clip = VideoClip(frame_function=make_frame, duration=duration)
        clip.write_videofile(str(scene_path), fps=fps, codec="libx264", audio=False, preset=preset, logger=None)
        clip.close()

        validation = validate_video_file(scene_path, expected_duration=duration, tolerance=1.0)
        if not validation["ok"]:
            raise RenderStageError("render_scene_failed", f"Сцена {scene_number}: {'; '.join(validation['errors'])}")
        scene_files.append(scene_path)
    return scene_files


def _concat_scene_clips(scene_files: list[Path], output_path: Path, temp_dir: Path) -> None:
    concat_list = temp_dir / "concat_list.txt"
    concat_list.write_text(
        "\n".join(f"file '{path.as_posix()}'" for path in scene_files),
        encoding="utf-8",
    )
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    command = [
        ffmpeg,
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_list),
        "-c",
        "copy",
        str(output_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RenderStageError("concat_failed", result.stderr[-2000:])


def _scene_asset_map(asset_plan: dict[str, Any]) -> dict[int, str]:
    return {
        int(asset["scene_number"]): asset["path"]
        for asset in asset_plan.get("scene_assets", [])
        if asset.get("path")
    }


def _start_stage_log(path: Path, render_plan: dict[str, Any]) -> None:
    write_json(
        path,
        {
            "ok": None,
            "current_stage": "initialized",
            "render_plan": render_plan,
            "events": [],
        },
    )


def _stage(path: Path, stage: str, message: str, **extra: Any) -> None:
    data = {}
    if path.exists():
        from .utils import read_json

        data = read_json(path)
    events = data.get("events", [])
    events.append(
        {
            "stage": stage,
            "message": message,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            **extra,
        }
    )
    data["events"] = events
    data["current_stage"] = stage
    data["ok"] = False if stage == "failed" else data.get("ok")
    if stage in {"add_music_done", "validate_silent_done"}:
        data["ok"] = True
    write_json(path, data)


def _replace_file(source: Path, target: Path) -> None:
    if target.exists():
        target.unlink()
    source.replace(target)


def _unlink_if_exists(path: Path) -> None:
    if path.exists():
        path.unlink()
