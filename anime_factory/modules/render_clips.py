from __future__ import annotations

from pathlib import Path
from typing import Any

from .detect_faces import detect_faces
from .dynamic_crop import (
    build_crop_path,
    build_smart_static_crop_path,
    build_static_crop_path,
    mux_audio_and_subtitles,
    render_dynamic_video,
    save_crop_path,
)
from .ffmpeg_utils import ffmpeg_filter_path, probe_video_size, run_ffmpeg
from .subtitles import write_short_subtitles


def render_clips(
    source_video: Path,
    candidates: list[dict[str, Any]],
    output_dir: Path,
    artifacts_dir: Path,
    config: dict[str, Any],
    force: bool = False,
    crop_mode: str = "auto",
    disable_face_crop: bool = False,
    crop_debug: bool = False,
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    crops_dir = artifacts_dir / "crops"
    crops_dir.mkdir(parents=True, exist_ok=True)
    render_config = config.get("render", {})
    dynamic_config = config.get("dynamic_crop", {})
    width = int(render_config.get("output_width", render_config.get("width", 1080)))
    height = int(render_config.get("output_height", render_config.get("height", 1920)))
    bitrate = str(render_config.get("video_bitrate", "8M"))
    video_width, video_height = probe_video_size(source_video)
    outputs: list[Path] = []

    for candidate in candidates:
        short_id = int(candidate["id"])
        output_path = output_dir / f"short_{short_id:03}.mp4"
        if output_path.exists() and not force:
            print(f"Ролик уже существует, пропускаю рендер: {output_path}")
            outputs.append(output_path)
            continue

        print(f"Рендерю short_{short_id:03}.mp4, crop mode: {crop_mode}...")
        _srt_path, ass_path = write_short_subtitles(candidate, output_dir, config)
        crop_path_file = crops_dir / f"short_{short_id:03}_crop_path.json"
        faces_file = crops_dir / f"short_{short_id:03}_faces.json"
        effective_mode = "center" if disable_face_crop and crop_mode in {"dynamic", "auto", "smart_static"} else crop_mode
        crop_info = _prepare_crop_info(
            source_video=source_video,
            candidate=candidate,
            faces_file=faces_file,
            crop_path_file=crop_path_file,
            requested_mode=effective_mode,
            video_width=video_width,
            video_height=video_height,
            config=config,
            force=force,
        )

        try:
            if crop_info["render_mode"] == "dynamic":
                temp_video = output_dir / f"short_{short_id:03}_dynamic_silent.mp4"
                render_dynamic_video(source_video, candidate, crop_info["crop_path"], temp_video, width, height)
                mux_audio_and_subtitles(source_video, temp_video, output_path, ass_path, candidate, bitrate)
                if not crop_debug and temp_video.exists():
                    temp_video.unlink()
            elif crop_info["render_mode"] == "blur":
                _render_blur_clip(source_video, candidate, output_path, ass_path, width, height, bitrate)
            elif crop_info["render_mode"] == "static_path":
                _render_static_path_clip(source_video, candidate, output_path, ass_path, width, height, bitrate, crop_info["crop_path"])
            else:
                _render_center_clip(source_video, candidate, output_path, ass_path, width, height, bitrate)
        except Exception as exc:
            if crop_info["render_mode"] == "dynamic":
                print(f"Dynamic crop не сработал, использую center crop: {exc}")
                crop_info = _center_crop_info(video_width, video_height, candidate, crop_path_file, "dynamic crop упал, использован center crop")
                _render_center_clip(source_video, candidate, output_path, ass_path, width, height, bitrate)
            else:
                raise

        candidate["crop"] = {
            "crop_mode": crop_info["report_mode"],
            "render_mode": crop_info["render_mode"],
            "face_detection_count": crop_info["face_detection_count"],
            "crop_quality": crop_info["crop_quality"],
            "crop_path": str(crop_path_file),
            "faces_path": str(faces_file) if faces_file.exists() else "",
            "warnings": crop_info["warnings"],
        }
        candidate["output_path"] = str(output_path)
        outputs.append(output_path)
        print(f"Ролик сохранен: {output_path}")

    return outputs


def _prepare_crop_info(
    source_video: Path,
    candidate: dict[str, Any],
    faces_file: Path,
    crop_path_file: Path,
    requested_mode: str,
    video_width: int,
    video_height: int,
    config: dict[str, Any],
    force: bool,
) -> dict[str, Any]:
    if requested_mode == "center":
        return _center_crop_info(video_width, video_height, candidate, crop_path_file, "center crop использован")
    if requested_mode == "blur":
        crop_path = build_static_crop_path(video_width, video_height, float(candidate["duration"]), mode="blur")
        save_crop_path(crop_path, crop_path_file)
        return {
            "render_mode": "blur",
            "report_mode": "blur",
            "crop_path": crop_path,
            "face_detection_count": 0,
            "crop_quality": "fallback",
            "warnings": ["использован blur fallback"],
        }
    if requested_mode == "smart_static":
        detections = detect_faces(
            source_video,
            float(candidate["start"]),
            float(candidate["end"]),
            faces_file,
            config.get("dynamic_crop", {}),
            force=force,
        )
        result = build_smart_static_crop_path(
            detections,
            video_width,
            video_height,
            float(candidate["duration"]),
            min_face_detections_ratio=float(config.get("dynamic_crop", {}).get("smart_static_min_face_ratio", 0.10)),
        )
        crop_path = result["crop_path"]
        quality = result["quality"]
        save_crop_path(crop_path, crop_path_file)
        return {
            "render_mode": "static_path" if quality["mode"] == "smart_static" else "center",
            "report_mode": "smart_static",
            "crop_path": crop_path,
            "face_detection_count": quality["face_detection_count"],
            "crop_quality": quality["crop_quality"],
            "warnings": quality["warnings"],
        }

    detections = detect_faces(
        source_video,
        float(candidate["start"]),
        float(candidate["end"]),
        faces_file,
        config.get("dynamic_crop", {}),
        force=force,
    )
    result = build_crop_path(
        detections=detections,
        video_width=video_width,
        video_height=video_height,
        clip_duration=float(candidate["duration"]),
        config=config.get("dynamic_crop", {}),
    )
    crop_path = result["crop_path"]
    quality = result["quality"]
    save_crop_path(crop_path, crop_path_file)
    if quality["mode"] == "dynamic":
        return {
            "render_mode": "dynamic",
            "report_mode": requested_mode,
            "crop_path": crop_path,
            "face_detection_count": quality["face_detection_count"],
            "crop_quality": quality["crop_quality"],
            "warnings": quality["warnings"],
        }
    if requested_mode == "auto" and quality["face_detection_count"] == 0 and config.get("render", {}).get("auto_blur_fallback", True):
        blur_path = build_static_crop_path(video_width, video_height, float(candidate["duration"]), mode="blur")
        save_crop_path(blur_path, crop_path_file)
        return {
            "render_mode": "blur",
            "report_mode": "auto",
            "crop_path": blur_path,
            "face_detection_count": 0,
            "crop_quality": "fallback",
            "warnings": ["лица не найдены, использован blur fallback"],
        }
    if requested_mode == "auto":
        smart = build_smart_static_crop_path(
            detections,
            video_width,
            video_height,
            float(candidate["duration"]),
            min_face_detections_ratio=float(config.get("dynamic_crop", {}).get("smart_static_min_face_ratio", 0.10)),
        )
        if smart["quality"]["mode"] == "smart_static":
            save_crop_path(smart["crop_path"], crop_path_file)
            return {
                "render_mode": "static_path",
                "report_mode": "auto:smart_static",
                "crop_path": smart["crop_path"],
                "face_detection_count": smart["quality"]["face_detection_count"],
                "crop_quality": smart["quality"]["crop_quality"],
                "warnings": smart["quality"]["warnings"],
            }
    return {
        "render_mode": "center",
        "report_mode": requested_mode,
        "crop_path": crop_path,
        "face_detection_count": quality["face_detection_count"],
        "crop_quality": quality["crop_quality"],
        "warnings": quality["warnings"],
    }


def _center_crop_info(
    video_width: int,
    video_height: int,
    candidate: dict[str, Any],
    crop_path_file: Path,
    warning: str,
) -> dict[str, Any]:
    crop_path = build_static_crop_path(video_width, video_height, float(candidate["duration"]), mode="center")
    save_crop_path(crop_path, crop_path_file)
    return {
        "render_mode": "center",
        "report_mode": "center",
        "crop_path": crop_path,
        "face_detection_count": 0,
        "crop_quality": "fallback",
        "warnings": [warning],
    }


def _render_center_clip(
    source_video: Path,
    candidate: dict[str, Any],
    output_path: Path,
    ass_path: Path,
    width: int,
    height: int,
    bitrate: str,
) -> None:
    video_filter = (
        f"scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},setsar=1,"
        f"ass='{ffmpeg_filter_path(ass_path)}'"
    )
    _render_ffmpeg_clip(source_video, candidate, output_path, video_filter, bitrate)


def _render_blur_clip(
    source_video: Path,
    candidate: dict[str, Any],
    output_path: Path,
    ass_path: Path,
    width: int,
    height: int,
    bitrate: str,
) -> None:
    video_filter = (
        f"[0:v]scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},gblur=sigma=28[bg];"
        f"[0:v]scale={width}:{height}:force_original_aspect_ratio=decrease[fg];"
        f"[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1,"
        f"ass='{ffmpeg_filter_path(ass_path)}'"
    )
    _render_ffmpeg_clip(source_video, candidate, output_path, video_filter, bitrate)


def _render_static_path_clip(
    source_video: Path,
    candidate: dict[str, Any],
    output_path: Path,
    ass_path: Path,
    width: int,
    height: int,
    bitrate: str,
    crop_path: list[dict[str, Any]],
) -> None:
    crop = crop_path[0]
    video_filter = (
        f"crop={int(crop['crop_w'])}:{int(crop['crop_h'])}:{int(crop['crop_x'])}:{int(crop['crop_y'])},"
        f"scale={width}:{height},setsar=1,"
        f"ass='{ffmpeg_filter_path(ass_path)}'"
    )
    _render_ffmpeg_clip(source_video, candidate, output_path, video_filter, bitrate)


def _render_ffmpeg_clip(
    source_video: Path,
    candidate: dict[str, Any],
    output_path: Path,
    video_filter: str,
    bitrate: str,
) -> None:
    run_ffmpeg(
        [
            "-ss",
            str(candidate["start"]),
            "-t",
            str(candidate["duration"]),
            "-i",
            str(source_video),
            "-filter_complex" if video_filter.startswith("[") else "-vf",
            video_filter,
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-b:v",
            bitrate,
            "-c:a",
            "aac",
            "-b:a",
            "160k",
            "-movflags",
            "+faststart",
            str(output_path),
        ]
    )
