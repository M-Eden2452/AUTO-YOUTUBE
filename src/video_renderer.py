from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance
from moviepy import VideoClip, VideoFileClip

from .layout_renderer import render_documentary_frame, render_text_overlay
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
    documentary_montage = asset_plan.get("engine") == "documentary_visual_engine_v2"
    visual_rules_config = config.get("video_task", {}).get("visual_rules", {})
    shot_duration_config = visual_rules_config.get("shot_duration", {}) if isinstance(visual_rules_config, dict) else {}
    min_shot_seconds = float(shot_duration_config.get("minimum_seconds", 4.0))
    fps = int(config["fps"])
    if documentary_montage and config.get("cinematic_preview", False):
        fps = int(config.get("cinematic_preview_fps", 24))
    elif documentary_montage and config.get("dev_mode", False):
        fps = min(fps, 10)
    if documentary_montage and config.get("cinematic_preview", False):
        preset = str(config.get("cinematic_preview_preset", "medium"))
    else:
        preset = "ultrafast" if documentary_montage or not config.get("dev_mode", False) else "medium"
    active_music = dict(music_plan or asset_plan["music"])
    if documentary_montage and active_music:
        active_music["volume"] = min(float(active_music.get("volume", 0.16)), float(config.get("documentary_music_volume", 0.12)))
        active_music["ducking"] = True
    return {
        "output_path": str(output_path),
        "silent_video_path": str(silent_path),
        "partial_silent_video_path": str(partial_path),
        "temp_dir": str(temp_dir),
        "stage_log_path": str(output_path.parent / "render_stage.json"),
        "resolution": config["resolution"],
        "fps": fps,
        "duration": total_duration,
        "scene_count": len(scene_plan.get("scenes", [])),
        "layout": config["layout"],
        "animation": config["animation_type"],
        "music": active_music,
        "render_strategy": "documentary_scene_montage"
        if documentary_montage
        else ("scene_temp_clips_concat" if not config.get("dev_mode", False) else "single_scene_temp_clip"),
        "subtitle_safe_area": True,
        "render_profile": "cinematic_preview" if config.get("cinematic_preview", False) else ("documentary_dev" if documentary_montage else "standard"),
        "encoding": {
            "crf": int(config.get("cinematic_preview_crf", 18 if config.get("cinematic_preview", False) else 23)),
            "audio_bitrate": config.get("audio_bitrate", "160k"),
        },
        "voice": config.get("voice_manifest", {}),
        "visual_rules": {
            "no_scene_labels": documentary_montage,
            "fullscreen_footage": documentary_montage,
            "subtitles_only": documentary_montage and bool(config.get("documentary_subtitles_only") or config.get("channel_id") == "survival"),
            "image_motion_required": documentary_montage,
            "avoid_ui_blocks": documentary_montage,
        },
        "subtitle_style": {
            "name": "cinematic_documentary_v2" if documentary_montage else "classic_quote_card",
            "background_alpha": 118,
            "y_ratio": 0.765,
            "padding": [18, 10],
            "rounded_radius": 9,
        },
        "montage": {
            "enabled": documentary_montage,
            "transition": config.get("transition_type", "crossfade"),
            "clip_count": sum(int(scene.get("clip_count", len(scene.get("clips", [])))) for scene in asset_plan.get("scene_assets", [])),
            "target_clip_seconds": [min_shot_seconds, 30.0],
            "average_shot_seconds": _average_shot_seconds(asset_plan),
            "color_grading": "subtle_dark_green_blue_documentary",
            "pacing": "adaptive_cinematic",
        },
        "preset": preset,
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
        scene_files = _render_scene_clips(config, scene_plan, scene_assets, fallback_image, temp_dir, fps, render_plan["preset"], render_plan.get("encoding", {}))
        _concat_scene_clips(scene_files, partial_path, temp_dir)
        _stage(stage_log_path, "render_silent_done", f"Silent partial создан: {partial_path}")

        _stage(stage_log_path, "validate_silent_started", "Проверка silent partial.")
        validation = validate_video_file(partial_path, expected_duration=float(render_plan["duration"]))
        if not validation["ok"]:
            raise RenderStageError("validate_silent_failed", "; ".join(validation["errors"]))
        _replace_file(partial_path, silent_path)
        _stage(stage_log_path, "validate_silent_done", f"Silent video валиден: {silent_path}")

        active_music = music_plan or render_plan.get("music") or {}
        if asset_plan.get("engine") == "documentary_visual_engine_v2" and active_music:
            active_music = {**active_music, "volume": min(float(active_music.get("volume", 0.16)), float(config.get("documentary_music_volume", 0.12)))}
        music_path = active_music.get("path") or asset_plan.get("music", {}).get("path", "")
        music_status = active_music.get("status") or asset_plan.get("music", {}).get("status")
        if music_path and music_status in {"найдено", "найдена_локальная_музыка", "found"}:
            _stage(stage_log_path, "add_music_started", f"Добавление музыки: {music_path}")
            added = add_background_music(
                silent_path,
                music_path,
                output_path,
                float(active_music.get("volume", 0.16)),
                voice_manifest=render_plan.get("voice") or config.get("voice_manifest"),
                duck_music=bool((render_plan.get("music") or {}).get("ducking", True)),
                preset=str(render_plan.get("preset", "medium")),
                crf=int(render_plan.get("encoding", {}).get("crf", 18)),
                audio_bitrate=str(render_plan.get("encoding", {}).get("audio_bitrate", "192k")),
            )
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
    scene_assets: dict[int, Any],
    fallback_image: str | None,
    temp_dir: Path,
    fps: int,
    preset: str,
    encoding: dict[str, Any] | None = None,
) -> list[Path]:
    scene_files: list[Path] = []
    for scene in scene_plan.get("scenes", []):
        scene_number = int(scene.get("scene_number", len(scene_files) + 1))
        scene_path = temp_dir / f"scene_{scene_number:03d}.mp4"
        scene_asset = scene_assets.get(scene_number, fallback_image)
        duration = float(scene["duration"])
        if _can_fast_render_scene(scene_asset):
            _render_scene_with_ffmpeg_overlay(config, scene, scene_asset, scene_path, temp_dir, fps, preset, encoding or {})
            validation = validate_video_file(scene_path, expected_duration=duration, tolerance=1.0)
            if not validation["ok"]:
                raise RenderStageError("render_scene_failed", f"Сцена {scene_number}: {'; '.join(validation['errors'])}")
            scene_files.append(scene_path)
            continue

        montage_clips = _prepare_montage_clips(scene_asset)

        def make_frame(t: float, current_scene=scene, current_asset=scene_asset, current_duration=duration, current_montage=montage_clips):
            progress = t / max(current_duration, 0.001)
            background_frame = _montage_frame(current_scene, current_montage, t, config)
            current_image = current_asset if isinstance(current_asset, str) else None
            return render_documentary_frame(config, current_scene, current_image, min(progress, 1.0), background_frame=background_frame)

        clip = None
        try:
            clip = VideoClip(frame_function=make_frame, duration=duration)
            clip.write_videofile(str(scene_path), fps=fps, codec="libx264", audio=False, preset=preset, logger=None)
        finally:
            if clip:
                clip.close()
            _close_montage_clips(montage_clips)

        validation = validate_video_file(scene_path, expected_duration=duration, tolerance=1.0)
        if not validation["ok"]:
            raise RenderStageError("render_scene_failed", f"Сцена {scene_number}: {'; '.join(validation['errors'])}")
        scene_files.append(scene_path)
    return scene_files


def _can_fast_render_scene(scene_asset: Any) -> bool:
    if not isinstance(scene_asset, dict):
        return False
    clips = scene_asset.get("clips", [])
    return bool(clips) and all(clip.get("type") == "video" and clip.get("path") and Path(clip["path"]).exists() for clip in clips)


def _render_scene_with_ffmpeg_overlay(
    config: dict[str, Any],
    scene: dict[str, Any],
    scene_asset: dict[str, Any],
    scene_path: Path,
    temp_dir: Path,
    fps: int,
    preset: str,
    encoding: dict[str, Any] | None = None,
) -> None:
    width, height = [int(v) for v in config["resolution"]]
    scene_number = int(scene.get("scene_number", 0))
    overlay_path = temp_dir / f"scene_{scene_number:03d}_overlay.png"
    render_text_overlay(config, scene, width, height).save(overlay_path, "PNG")

    command = [imageio_ffmpeg.get_ffmpeg_exe(), "-y"]
    clips = scene_asset.get("clips", [])
    total_duration = sum(float(clip.get("duration", 0)) for clip in clips)
    for clip in clips:
        command.extend(["-ss", str(float(clip.get("start_offset", 0))), "-t", f"{float(clip.get('duration', 0)):.3f}", "-i", str(Path(clip["path"]))])
    command.extend(["-loop", "1", "-t", f"{total_duration:.3f}", "-i", str(overlay_path)])

    filters: list[str] = []
    labels: list[str] = []
    for index, _clip in enumerate(clips):
        label = f"v{index}"
        filters.append(
            f"[{index}:v]scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},eq=contrast=1.08:brightness=-0.055:saturation=0.86,"
            f"colorchannelmixer=rr=0.94:gg=1.03:bb=1.06,setsar=1,fps={fps},format=rgba[{label}]"
        )
        labels.append(f"[{label}]")
    overlay_index = len(clips)
    filters.append(f"{''.join(labels)}concat=n={len(clips)}:v=1:a=0[vcat]")
    filters.append(f"[vcat][{overlay_index}:v]overlay=0:0:shortest=1,format=yuv420p[vout]")
    command.extend(
        [
            "-filter_complex",
            ";".join(filters),
            "-map",
            "[vout]",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            preset,
            "-crf",
            str((encoding or {}).get("crf", 23)),
            "-r",
            str(fps),
            str(scene_path),
        ]
    )
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RenderStageError("render_scene_failed", f"ffmpeg return code {result.returncode}: {result.stderr[-4000:]}")


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


def _scene_asset_map(asset_plan: dict[str, Any]) -> dict[int, Any]:
    mapped: dict[int, Any] = {}
    for asset in asset_plan.get("scene_assets", []):
        scene_number = int(asset["scene_number"])
        if asset.get("clips"):
            mapped[scene_number] = asset
        elif asset.get("path"):
            mapped[scene_number] = asset["path"]
    return mapped


def _average_shot_seconds(asset_plan: dict[str, Any]) -> float:
    durations = [
        float(clip.get("duration", 0))
        for asset in asset_plan.get("scene_assets", [])
        for clip in asset.get("clips", [])
        if float(clip.get("duration", 0) or 0) > 0
    ]
    return round(sum(durations) / len(durations), 3) if durations else 0.0


def _prepare_montage_clips(scene_asset: Any) -> list[dict[str, Any]]:
    if not isinstance(scene_asset, dict):
        return []
    prepared: list[dict[str, Any]] = []
    cursor = 0.0
    for item in scene_asset.get("clips", []):
        clip = {**item, "timeline_start": cursor}
        cursor += float(item.get("duration", 0))
        path = item.get("path", "")
        if item.get("type") == "video" and path and Path(path).exists():
            try:
                clip["video_clip"] = VideoFileClip(path)
            except Exception:
                clip["type"] = "generated_motion"
                clip["video_clip"] = None
        prepared.append(clip)
    return prepared


def _close_montage_clips(clips: list[dict[str, Any]]) -> None:
    for item in clips:
        video = item.get("video_clip")
        if video is not None:
            video.close()


def _montage_frame(scene: dict[str, Any], clips: list[dict[str, Any]], t: float, config: dict[str, Any]) -> np.ndarray | None:
    if not clips:
        return None
    active = clips[-1]
    for item in clips:
        start = float(item.get("timeline_start", 0))
        end = start + float(item.get("duration", 0))
        if start <= t < end:
            active = item
            break

    local_t = max(0.0, t - float(active.get("timeline_start", 0)))
    video = active.get("video_clip")
    if video is not None:
        source_duration = max(float(video.duration or 0), 0.001)
        sample_t = min(source_duration - 0.05, local_t + float(active.get("start_offset", 0)))
        frame = video.get_frame(max(0.0, sample_t))
        return _mild_motion_frame(frame, local_t, float(active.get("duration", 1)), config)
    return _generated_motion_frame(scene, active, local_t, float(active.get("duration", 1)), config)


def _mild_motion_frame(frame: np.ndarray, t: float, duration: float, config: dict[str, Any]) -> np.ndarray:
    image = Image.fromarray(frame).convert("RGB")
    progress = t / max(duration, 0.001)
    zoom = 1.0 + 0.018 * progress
    width, height = image.size
    crop_w = max(1, int(width / zoom))
    crop_h = max(1, int(height / zoom))
    left = int((width - crop_w) * 0.5)
    top = int((height - crop_h) * 0.5)
    image = image.crop((left, top, left + crop_w, top + crop_h)).resize((width, height), Image.Resampling.LANCZOS)
    return np.array(image)


def _generated_motion_frame(scene: dict[str, Any], clip: dict[str, Any], t: float, duration: float, config: dict[str, Any]) -> np.ndarray:
    width, height = [int(v) for v in config["resolution"]]
    seed = int(hash(str(scene.get("scene_id", "")) + str(clip.get("query", ""))) & 0xFFFFFFFF)
    rng = np.random.default_rng(seed)
    base = Image.new("RGB", (width, height), _scene_color(scene))
    draw = ImageDraw.Draw(base, "RGBA")
    progress = t / max(duration, 0.001)
    for layer in range(9):
        x = int((rng.integers(-width // 2, width) + progress * width * (0.08 + layer * 0.01)) % int(width * 1.5) - width * 0.25)
        y = int(rng.integers(0, height))
        radius = int(rng.integers(height // 9, height // 3))
        color = (20 + layer * 4, 45 + layer * 5, 38 + layer * 3, 28)
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color)
    if "storm" in " ".join(scene.get("visual_keywords", [])).lower() or "lightning" in str(clip.get("query", "")).lower():
        draw.line((int(width * 0.68), 0, int(width * 0.57), int(height * 0.32), int(width * 0.62), int(height * 0.55)), fill=(210, 220, 235, 105), width=4)
    for _ in range(120):
        x = int(rng.integers(0, width))
        y = int((rng.integers(-height, height) + progress * height * 1.8) % height)
        draw.line((x, y, x - 5, y + 18), fill=(160, 180, 190, 42), width=1)
    base = ImageEnhance.Contrast(base).enhance(1.25)
    base = ImageEnhance.Brightness(base).enhance(0.82)
    return np.array(base)


def _scene_color(scene: dict[str, Any]) -> tuple[int, int, int]:
    text = " ".join(scene.get("visual_keywords", [])).lower()
    if "river" in text or "water" in text:
        return (8, 24, 30)
    if "storm" in text or "rain" in text:
        return (9, 12, 18)
    if "hut" in text or "camp" in text:
        return (24, 20, 14)
    return (8, 22, 16)


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
