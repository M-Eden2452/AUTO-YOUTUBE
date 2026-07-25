from __future__ import annotations

from bisect import bisect_right
from pathlib import Path
from typing import Any

from .ffmpeg_utils import ffmpeg_filter_path, run_ffmpeg
from .paths import write_json


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _center_crop_x(video_width: int, crop_w: int) -> int:
    return int(round((video_width - crop_w) / 2))


def _choose_face(
    faces: list[dict[str, Any]],
    video_width: int,
    video_height: int,
    previous_target_x: float | None,
    config: dict[str, Any],
) -> dict[str, Any] | None:
    if not faces:
        return None
    size_weight = float(config.get("face_size_weight", 0.5))
    center_weight = float(config.get("center_weight", 0.3))
    stability_weight = float(config.get("stability_weight", 0.2))
    frame_center = video_width / 2
    diagonal = max((video_width**2 + video_height**2) ** 0.5, 1.0)

    best_face: dict[str, Any] | None = None
    best_score = -1.0
    for face in faces:
        face_w = float(face.get("w", 0))
        face_h = float(face.get("h", 0))
        target_x = float(face.get("x", 0)) + face_w / 2
        target_y = float(face.get("y", 0)) + face_h / 2
        size_score = clamp((face_w * face_h) / max(video_width * video_height * 0.08, 1), 0.0, 1.0)
        center_score = 1.0 - clamp(abs(target_x - frame_center) / max(frame_center, 1), 0.0, 1.0)
        if previous_target_x is None:
            stability_score = 0.5
        else:
            stability_score = 1.0 - clamp(abs(target_x - previous_target_x) / diagonal, 0.0, 1.0)
        confidence = float(face.get("confidence", 0.5))
        score = (size_score * size_weight + center_score * center_weight + stability_score * stability_weight) * confidence
        if score > best_score:
            best_score = score
            best_face = {**face, "target_x": target_x, "target_y": target_y, "score": round(score, 4)}
    return best_face


def build_crop_path(
    detections: list[dict[str, Any]],
    video_width: int,
    video_height: int,
    clip_duration: float,
    config: dict[str, Any],
) -> dict[str, Any]:
    crop_h = int(video_height)
    crop_w = int(video_height * 9 / 16)
    if crop_w > video_width:
        crop_w = video_width
        crop_h = int(round(video_width * 16 / 9))
    max_x = max(0, video_width - crop_w)
    center_x = _center_crop_x(video_width, crop_w)
    smoothing = float(config.get("smoothing", 0.85))
    max_shift = float(config.get("max_shift_px", 60))
    min_ratio = float(config.get("min_face_detections_ratio", 0.25))
    samples = sorted(detections, key=lambda item: float(item.get("time", 0.0)))
    if not samples:
        samples = [{"time": 0.0, "faces": []}]

    face_samples = sum(1 for sample in samples if sample.get("faces"))
    face_ratio = face_samples / max(len(samples), 1)
    force_center = face_ratio < min_ratio
    warnings: list[str] = []
    if force_center:
        warnings.append("лица почти не найдены, использован center crop")

    crop_path: list[dict[str, Any]] = []
    previous_x = float(center_x)
    previous_target_x: float | None = None
    for sample in samples:
        time = round(float(sample.get("time", 0.0)), 2)
        selected = None if force_center else _choose_face(sample.get("faces", []), video_width, video_height, previous_target_x, config)
        if selected:
            target_x = float(selected["target_x"])
            target_y = float(selected["target_y"])
            desired_x = clamp(target_x - crop_w / 2, 0, max_x)
            smoothed_x = previous_x * smoothing + desired_x * (1.0 - smoothing)
            delta = clamp(smoothed_x - previous_x, -max_shift, max_shift)
            crop_x = clamp(previous_x + delta, 0, max_x)
            previous_target_x = target_x
            mode = "face"
        else:
            target_x = previous_target_x if previous_target_x is not None else video_width / 2
            target_y = video_height / 2
            desired_x = previous_x if not force_center else center_x
            delta = clamp(desired_x - previous_x, -max_shift, max_shift)
            crop_x = clamp(previous_x + delta, 0, max_x)
            mode = "center" if force_center else "hold"
        previous_x = crop_x
        crop_path.append(
            {
                "time": time,
                "crop_x": int(round(crop_x)),
                "crop_y": 0,
                "crop_w": int(crop_w),
                "crop_h": int(crop_h),
                "target_x": int(round(target_x)),
                "target_y": int(round(target_y)),
                "mode": mode,
            }
        )

    mode = "center" if force_center else "dynamic"
    if mode == "dynamic":
        warnings.append("dynamic crop использован")
    return {
        "crop_path": crop_path,
        "quality": {
            "mode": mode,
            "face_detection_count": face_samples,
            "face_detection_ratio": round(face_ratio, 4),
            "crop_quality": "good" if mode == "dynamic" else "fallback",
            "warnings": warnings,
        },
    }


def save_crop_path(crop_path: list[dict[str, Any]], path: Path) -> Path:
    write_json(path, crop_path)
    return path


def build_static_crop_path(
    video_width: int,
    video_height: int,
    clip_duration: float,
    mode: str = "center",
) -> list[dict[str, Any]]:
    crop_h = int(video_height)
    crop_w = int(video_height * 9 / 16)
    if crop_w > video_width:
        crop_w = video_width
        crop_h = int(round(video_width * 16 / 9))
    crop_x = _center_crop_x(video_width, crop_w)
    return [
        {
            "time": 0.0,
            "crop_x": crop_x,
            "crop_y": 0,
            "crop_w": int(crop_w),
            "crop_h": int(crop_h),
            "target_x": int(video_width / 2),
            "target_y": int(video_height / 2),
            "mode": mode,
        },
        {
            "time": round(float(clip_duration), 2),
            "crop_x": crop_x,
            "crop_y": 0,
            "crop_w": int(crop_w),
            "crop_h": int(crop_h),
            "target_x": int(video_width / 2),
            "target_y": int(video_height / 2),
            "mode": mode,
        },
    ]


def build_smart_static_crop_path(
    detections: list[dict[str, Any]],
    video_width: int,
    video_height: int,
    clip_duration: float,
    min_face_detections_ratio: float = 0.10,
) -> dict[str, Any]:
    crop_h = int(video_height)
    crop_w = int(video_height * 9 / 16)
    if crop_w > video_width:
        crop_w = video_width
        crop_h = int(round(video_width * 16 / 9))
    max_x = max(0, video_width - crop_w)
    center_x = _center_crop_x(video_width, crop_w)
    samples = sorted(detections, key=lambda item: float(item.get("time", 0.0)))
    faces = [face for sample in samples for face in sample.get("faces", [])]
    face_ratio = sum(1 for sample in samples if sample.get("faces")) / max(len(samples), 1)
    if not faces or face_ratio < min_face_detections_ratio:
        crop_path = build_static_crop_path(video_width, video_height, clip_duration, mode="center")
        return {
            "crop_path": crop_path,
            "quality": {
                "mode": "center",
                "face_detection_count": len(faces),
                "face_detection_ratio": round(face_ratio, 4),
                "crop_quality": "fallback",
                "warnings": ["лица почти не найдены, использован center crop"],
            },
        }
    weighted_sum = 0.0
    total_weight = 0.0
    for face in faces:
        face_w = float(face.get("w", 0))
        face_h = float(face.get("h", 0))
        confidence = float(face.get("confidence", 0.5))
        target_x = float(face.get("x", 0)) + face_w / 2
        weight = max(face_w * face_h, 1.0) * confidence
        weighted_sum += target_x * weight
        total_weight += weight
    target_x = weighted_sum / max(total_weight, 1.0)
    crop_x = int(round(clamp(target_x - crop_w / 2, 0, max_x)))
    crop_path = [
        {
            "time": 0.0,
            "crop_x": crop_x,
            "crop_y": 0,
            "crop_w": int(crop_w),
            "crop_h": int(crop_h),
            "target_x": int(round(target_x)),
            "target_y": int(video_height / 2),
            "mode": "smart_static",
        },
        {
            "time": round(float(clip_duration), 2),
            "crop_x": crop_x,
            "crop_y": 0,
            "crop_w": int(crop_w),
            "crop_h": int(crop_h),
            "target_x": int(round(target_x)),
            "target_y": int(video_height / 2),
            "mode": "smart_static",
        },
    ]
    return {
        "crop_path": crop_path,
        "quality": {
            "mode": "smart_static",
            "face_detection_count": len(faces),
            "face_detection_ratio": round(face_ratio, 4),
            "crop_quality": "good",
            "warnings": ["smart static crop использован"],
        },
    }


def _crop_for_time(crop_path: list[dict[str, Any]], time: float) -> dict[str, Any]:
    times = [float(item["time"]) for item in crop_path]
    index = max(0, bisect_right(times, time) - 1)
    return crop_path[index]


def render_dynamic_video(
    source_video: Path,
    candidate: dict[str, Any],
    crop_path: list[dict[str, Any]],
    temp_video: Path,
    width: int,
    height: int,
) -> Path:
    try:
        import cv2
    except ImportError as exc:
        raise RuntimeError("Не установлена зависимость opencv-python. Выполните: pip install -r anime_factory/requirements.txt") from exc

    capture = cv2.VideoCapture(str(source_video))
    if not capture.isOpened():
        raise RuntimeError(f"Не удалось открыть видео через OpenCV: {source_video}")
    fps = capture.get(cv2.CAP_PROP_FPS) or 24.0
    start = float(candidate["start"])
    duration = float(candidate["duration"])
    end = start + duration
    capture.set(cv2.CAP_PROP_POS_MSEC, start * 1000)
    temp_video.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(str(temp_video), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
    if not writer.isOpened():
        capture.release()
        raise RuntimeError(f"Не удалось создать временное видео: {temp_video}")

    while True:
        ok, frame = capture.read()
        if not ok:
            break
        position_seconds = capture.get(cv2.CAP_PROP_POS_MSEC) / 1000
        if position_seconds > end:
            break
        relative_time = max(0.0, position_seconds - start)
        crop = _crop_for_time(crop_path, relative_time)
        x = int(crop["crop_x"])
        y = int(crop["crop_y"])
        crop_w = int(crop["crop_w"])
        crop_h = int(crop["crop_h"])
        cropped = frame[y : y + crop_h, x : x + crop_w]
        resized = cv2.resize(cropped, (width, height), interpolation=cv2.INTER_AREA)
        writer.write(resized)

    writer.release()
    capture.release()
    return temp_video


def mux_audio_and_subtitles(
    source_video: Path,
    silent_video: Path,
    output_path: Path,
    ass_path: Path,
    candidate: dict[str, Any],
    video_bitrate: str,
) -> None:
    video_filter = f"ass='{ffmpeg_filter_path(ass_path)}'"
    run_ffmpeg(
        [
            "-i",
            str(silent_video),
            "-ss",
            str(candidate["start"]),
            "-t",
            str(candidate["duration"]),
            "-i",
            str(source_video),
            "-vf",
            video_filter,
            "-map",
            "0:v:0",
            "-map",
            "1:a:0?",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-b:v",
            video_bitrate,
            "-c:a",
            "aac",
            "-b:a",
            "160k",
            "-shortest",
            "-movflags",
            "+faststart",
            str(output_path),
        ]
    )
