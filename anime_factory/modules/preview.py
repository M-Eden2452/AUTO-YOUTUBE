from __future__ import annotations

from pathlib import Path
from typing import Any

from .ffmpeg_utils import ffmpeg_filter_path, run_ffmpeg
from .subtitles import write_short_subtitles


def create_previews(
    source_video: Path,
    candidates: list[dict[str, Any]],
    previews_dir: Path,
    config: dict[str, Any],
    force: bool = False,
    crop_mode: str = "center",
    preview_quality: str = "fast",
    compare_crops: bool = False,
) -> list[Path]:
    previews_dir.mkdir(parents=True, exist_ok=True)
    output_paths: list[Path] = []
    for candidate in candidates:
        short_id = int(candidate["id"])
        score = int(round(float(candidate.get("score", 0.0)) * 100))
        output_path = previews_dir / f"candidate_{short_id:03}_score_{score:03}.mp4"
        candidate["preview_path"] = str(output_path)
        if output_path.exists() and not force:
            print(f"Preview уже существует, пропускаю: {output_path}")
            output_paths.append(output_path)
            continue
        try:
            print(f"Создаю preview candidate_{short_id:03}...")
            _srt_path, ass_path = write_short_subtitles(candidate, previews_dir, _preview_subtitle_config(config))
            _render_preview(source_video, candidate, output_path, ass_path, crop_mode, preview_quality)
            if compare_crops:
                try:
                    comparison_path = previews_dir / f"candidate_{short_id:03}_crop_comparison.mp4"
                    candidate["comparison_preview_path"] = str(comparison_path)
                    _render_crop_comparison(source_video, candidate, comparison_path, ass_path, preview_quality)
                except Exception as exc:
                    warning = f"crop comparison не удалось создать: {exc}"
                    candidate.setdefault("warnings", []).append(warning)
                    print(f"Предупреждение: candidate {short_id}: {warning}")
            output_paths.append(output_path)
        except Exception as exc:
            warning = f"preview не удалось создать: {exc}"
            candidate.setdefault("warnings", []).append(warning)
            print(f"Предупреждение: candidate {short_id}: {warning}")
    return output_paths


def build_comparison_labels(modes: list[str]) -> str:
    return " | ".join(modes)


def _preview_subtitle_config(config: dict[str, Any]) -> dict[str, Any]:
    clone = dict(config)
    subtitles = dict(config.get("subtitles", {}))
    subtitles["font_size"] = min(int(subtitles.get("font_size", 72)), 54)
    clone["subtitles"] = subtitles
    return clone


def _render_preview(
    source_video: Path,
    candidate: dict[str, Any],
    output_path: Path,
    ass_path: Path,
    crop_mode: str,
    preview_quality: str,
) -> None:
    width, height = 720, 1280
    bitrate = "1400k" if preview_quality == "fast" else "2400k"
    preset = "ultrafast" if preview_quality == "fast" else "veryfast"
    if crop_mode == "blur":
        video_filter = (
            f"[0:v]scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},gblur=sigma=20[bg];"
            f"[0:v]scale={width}:{height}:force_original_aspect_ratio=decrease[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1,"
            f"ass='{ffmpeg_filter_path(ass_path)}'"
        )
        filter_flag = "-filter_complex"
    else:
        video_filter = (
            f"scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},setsar=1,"
            f"ass='{ffmpeg_filter_path(ass_path)}'"
        )
        filter_flag = "-vf"
    run_ffmpeg(
        [
            "-ss",
            str(candidate["start"]),
            "-t",
            str(candidate["duration"]),
            "-i",
            str(source_video),
            filter_flag,
            video_filter,
            "-c:v",
            "libx264",
            "-preset",
            preset,
            "-b:v",
            bitrate,
            "-c:a",
            "aac",
            "-b:a",
            "96k",
            "-movflags",
            "+faststart",
            str(output_path),
        ]
    )


def _render_crop_comparison(
    source_video: Path,
    candidate: dict[str, Any],
    output_path: Path,
    ass_path: Path,
    preview_quality: str,
) -> None:
    tile_w, tile_h = 360, 640
    bitrate = "2200k" if preview_quality == "fast" else "3600k"
    preset = "ultrafast" if preview_quality == "fast" else "veryfast"
    labels = build_comparison_labels(["center", "smart_static", "blur"])
    candidate["comparison_labels"] = labels
    filter_complex = (
        f"[0:v]scale={tile_w}:{tile_h}:force_original_aspect_ratio=increase,crop={tile_w}:{tile_h},setsar=1[c];"
        f"[0:v]scale={tile_w}:{tile_h}:force_original_aspect_ratio=increase,crop={tile_w}:{tile_h},setsar=1[s];"
        f"[0:v]scale={tile_w}:{tile_h}:force_original_aspect_ratio=increase,crop={tile_w}:{tile_h},gblur=sigma=18[bbg];"
        f"[0:v]scale={tile_w}:{tile_h}:force_original_aspect_ratio=decrease[bfg];"
        f"[bbg][bfg]overlay=(W-w)/2:(H-h)/2[b];"
        f"[c][s][b]hstack=inputs=3,ass='{ffmpeg_filter_path(ass_path)}'"
    )
    run_ffmpeg(
        [
            "-ss",
            str(candidate["start"]),
            "-t",
            str(candidate["duration"]),
            "-i",
            str(source_video),
            "-filter_complex",
            filter_complex,
            "-c:v",
            "libx264",
            "-preset",
            preset,
            "-b:v",
            bitrate,
            "-c:a",
            "aac",
            "-b:a",
            "96k",
            "-movflags",
            "+faststart",
            str(output_path),
        ]
    )
