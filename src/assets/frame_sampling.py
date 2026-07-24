from __future__ import annotations

import dataclasses
import hashlib
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import imageio_ffmpeg
from PIL import Image


@dataclass
class SampledFrame:
    frame_index: int
    requested_timestamp_sec: float = 0.0
    actual_timestamp_sec: float = 0.0
    local_frame_path: str = ""
    width: int = 0
    height: int = 0
    sha256: str = ""
    extraction_status: str = "pending"
    extraction_error: str = ""
    perceptual_hash: str = ""
    technical_metrics: dict[str, Any] = dataclasses.field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


def planned_sample_timestamps(
    *,
    duration_sec: float,
    sample_count: int = 5,
    positions: list[float] | None = None,
) -> list[float]:
    count = max(1, int(sample_count or 1))
    base_positions = list(positions or [0.1, 0.3, 0.5, 0.7, 0.9])
    if len(base_positions) < count:
        base_positions = _even_positions(count)
    else:
        base_positions = base_positions[:count]
    duration = max(0.0, float(duration_sec or 0.0))
    if duration <= 0:
        return [0.0]
    timestamps: list[float] = []
    seen: set[float] = set()
    for position in base_positions:
        clamped = min(0.98, max(0.0, float(position)))
        timestamp = round(min(duration, max(0.0, duration * clamped)), 3)
        if timestamp not in seen:
            timestamps.append(timestamp)
            seen.add(timestamp)
    if not timestamps:
        timestamps = [0.0]
    return timestamps


def sample_frames(
    media_path: str | Path,
    *,
    media_type: str,
    output_dir: str | Path,
    sample_count: int = 5,
    positions: list[float] | None = None,
    duration_sec: float | None = None,
) -> list[SampledFrame]:
    source = Path(media_path)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    if media_type == "image" or source.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
        return [_image_as_frame(source, output)]
    duration = float(duration_sec or ffprobe_media_info(source).get("duration_sec") or 0.0)
    timestamps = planned_sample_timestamps(duration_sec=duration, sample_count=sample_count, positions=positions)
    frames: list[SampledFrame] = []
    for index, timestamp in enumerate(timestamps):
        target = output / f"frame_{index:03d}.jpg"
        frame = SampledFrame(frame_index=index, requested_timestamp_sec=timestamp, actual_timestamp_sec=timestamp, local_frame_path=str(target))
        command = [
            imageio_ffmpeg.get_ffmpeg_exe(),
            "-y",
            "-v",
            "error",
            "-ss",
            f"{timestamp:.3f}",
            "-i",
            str(source),
            "-frames:v",
            "1",
            "-q:v",
            "3",
            str(target),
        ]
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if result.returncode != 0 or not target.exists() or target.stat().st_size <= 0:
            frame.extraction_status = "failed"
            frame.extraction_error = (result.stderr or "").strip() or "ffmpeg_frame_extraction_failed"
            frames.append(frame)
            continue
        _fill_frame_metadata(frame, target)
        frames.append(frame)
    return frames


def ffprobe_media_info(path: str | Path) -> dict[str, Any]:
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
        return {"status": "failed", "error": (result.stderr or "").strip()}
    try:
        data = json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        return {"status": "failed", "error": "invalid_ffprobe_json"}
    stream = next((item for item in data.get("streams", []) if item.get("codec_type") == "video"), {})
    return {
        "status": "passed",
        "width": int(stream.get("width") or 0),
        "height": int(stream.get("height") or 0),
        "duration_sec": float(stream.get("duration") or data.get("format", {}).get("duration") or 0.0),
        "codec": str(stream.get("codec_name") or ""),
        "format_name": str(data.get("format", {}).get("format_name") or ""),
    }


def sha256_file(path: str | Path) -> str:
    sha = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            sha.update(chunk)
    return sha.hexdigest()


def _image_as_frame(source: Path, output: Path) -> SampledFrame:
    frame = SampledFrame(frame_index=0, requested_timestamp_sec=0.0, actual_timestamp_sec=0.0, local_frame_path=str(source))
    if not source.exists():
        frame.extraction_status = "failed"
        frame.extraction_error = "image_file_missing"
        return frame
    _fill_frame_metadata(frame, source)
    return frame


def _fill_frame_metadata(frame: SampledFrame, path: Path) -> None:
    try:
        with Image.open(path) as image:
            frame.width, frame.height = image.size
        frame.sha256 = sha256_file(path)
        from .perceptual_similarity import image_perceptual_hash

        frame.perceptual_hash = image_perceptual_hash(path)
        frame.extraction_status = "extracted"
    except Exception as exc:
        frame.extraction_status = "failed"
        frame.extraction_error = str(exc)


def _even_positions(count: int) -> list[float]:
    if count <= 1:
        return [0.5]
    step = 1.0 / (count + 1)
    return [round(step * (index + 1), 3) for index in range(count)]
