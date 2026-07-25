from __future__ import annotations

import subprocess
import shutil
from pathlib import Path
from typing import Any

import imageio_ffmpeg
from PIL import Image, ImageFilter

from src.audio.end_tail_policy import (
    DEFAULT_TAIL_SEC,
    END_POLICY_NARRATION_PLUS_TAIL,
    compute_target_duration,
    narration_duration_from_voice_manifest,
)
from src.audio.music_manifest import DEFAULT_VOLUME as DEFAULT_MUSIC_VOLUME, clamp_volume, read_music_manifest
from src.audio.scene_timeline import scene_render_duration


def render_final_video(
    *,
    project_root: str | Path,
    language: str,
    script: dict[str, Any],
    visual_plan: dict[str, Any],
    assets_manifest: dict[str, Any],
    voice_manifest: dict[str, Any],
    end_policy_id: str = END_POLICY_NARRATION_PLUS_TAIL,
    tail_sec: float = DEFAULT_TAIL_SEC,
) -> dict[str, Any]:
    root = Path(project_root)
    output_dir = root / "localizations" / language / "output"
    render_dir = root / "render"
    segments_dir = render_dir / "segments"
    output_dir.mkdir(parents=True, exist_ok=True)
    segments_dir.mkdir(parents=True, exist_ok=True)
    width = int(visual_plan.get("resolution", {}).get("width", 1080))
    height = int(visual_plan.get("resolution", {}).get("height", 1920))
    duration = _script_duration(script)
    segments = _create_scene_segments(
        segments_dir=segments_dir,
        width=width,
        height=height,
        script=script,
        assets_manifest=assets_manifest,
    )
    concat_path = render_dir / "frames.txt"
    _write_concat_file(concat_path, segments)
    silent_video = render_dir / "silent_master.mp4"
    master = output_dir / "master_1080x1920.mp4"
    no_subtitles = output_dir / "no_subtitles.mp4"
    _run_ffmpeg(
        [
            "-y",
            "-v",
            "error",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_path),
            "-c:v",
            "copy",
            str(silent_video),
        ]
    )
    audio_path = voice_manifest.get("audio_path", "")
    music_manifest = _load_music_manifest(root)
    music_path = music_manifest.get("path") or ""
    narration_duration_sec = narration_duration_from_voice_manifest(voice_manifest)
    target_duration = compute_target_duration(
        end_policy_id,
        narration_duration_sec=narration_duration_sec,
        visual_duration_sec=duration,
        tail_sec=tail_sec,
    )
    if audio_path and Path(audio_path).exists():
        if music_path and Path(music_path).exists():
            _mux_voice_and_music(
                silent_video,
                Path(audio_path),
                Path(music_path),
                no_subtitles,
                duration,
                target_duration,
                volume=clamp_volume(music_manifest.get("volume")),
                ducking=bool(music_manifest.get("ducking", True)),
            )
        else:
            _mux_voice_only(silent_video, Path(audio_path), no_subtitles, target_duration, duration)
    else:
        _run_ffmpeg(["-y", "-v", "error", "-i", str(silent_video), "-c:v", "copy", str(no_subtitles)])
    subtitles_manifest = _load_subtitles_manifest(root, language)
    subtitle_path = subtitles_manifest.get("ass_path") or ""
    subtitles_embedded = False
    if subtitle_path and Path(subtitle_path).exists():
        _burn_ass_subtitles(no_subtitles, Path(subtitle_path), master)
        subtitles_embedded = True
    else:
        shutil.copyfile(no_subtitles, master)
    outputs = _copy_platform_outputs(master, no_subtitles, output_dir)
    return {
        "status": "completed",
        "output_path": str(master),
        "outputs": outputs,
        "scene_count": len(segments),
        "resolution": {"width": width, "height": height},
        "audio_path": str(audio_path),
        "music_path": str(music_path),
        "subtitle_path": str(subtitle_path),
        "subtitle_layers": 1 if subtitles_embedded else 0,
        "renderer": "news_to_short_final_renderer_v2",
        "visual_duration_sec": duration,
        "narration_duration_sec": narration_duration_sec,
        "end_policy_id": end_policy_id,
        "tail_sec": tail_sec,
        "target_duration_sec": target_duration if (audio_path and Path(audio_path).exists()) else duration,
    }


def _create_scene_segments(
    *,
    segments_dir: Path,
    width: int,
    height: int,
    script: dict[str, Any],
    assets_manifest: dict[str, Any],
) -> list[dict[str, Any]]:
    asset_by_scene = {
        scene.get("scene_id"): (scene.get("selected_asset") or {})
        for scene in assets_manifest.get("scenes", [])
    }
    segments: list[dict[str, Any]] = []
    for index, scene in enumerate(script.get("scenes", []), start=1):
        scene_id = scene.get("scene_id", f"scene_{index:03d}")
        selected = asset_by_scene.get(scene_id, {})
        source_path = selected.get("path") or selected.get("local_path") or selected.get("downloaded_path") or ""
        if not source_path or not Path(source_path).exists():
            raise RuntimeError(f"Scene {scene_id} has no renderable visual asset.")
        # actual_duration_sec (written by the voice stage from the real narration)
        # wins over the planned target_duration_sec; see src.audio.scene_timeline.
        duration = scene_render_duration(scene)
        segment_path = segments_dir / f"{scene_id}.mp4"
        if selected.get("type") == "video" or Path(source_path).suffix.lower() in {".mp4", ".mov", ".m4v"}:
            _render_video_segment(Path(source_path), segment_path, duration, width, height)
        else:
            frame_path = segments_dir / f"{scene_id}.png"
            _base_frame(source_path, width, height).save(frame_path)
            _render_image_segment(frame_path, segment_path, duration, width, height)
        segments.append({"path": segment_path, "duration": duration})
    return segments


def _render_video_segment(source: Path, target: Path, duration: float, width: int, height: int) -> None:
    vf = f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},setsar=1,fps=30,format=yuv420p"
    _run_ffmpeg(
        [
            "-y",
            "-v",
            "error",
            "-stream_loop",
            "-1",
            "-i",
            str(source),
            "-t",
            f"{duration:.3f}",
            "-an",
            "-vf",
            vf,
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "23",
            str(target),
        ]
    )


def _render_image_segment(source: Path, target: Path, duration: float, width: int, height: int) -> None:
    vf = f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},setsar=1,fps=30,format=yuv420p"
    _run_ffmpeg(
        [
            "-y",
            "-v",
            "error",
            "-loop",
            "1",
            "-i",
            str(source),
            "-t",
            f"{duration:.3f}",
            "-an",
            "-vf",
            vf,
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "23",
            str(target),
        ]
    )


def _base_frame(source_path: str, width: int, height: int) -> Image.Image:
    try:
        image = Image.open(source_path).convert("RGB")
    except Exception as exc:
        raise RuntimeError(f"Image asset could not be opened: {source_path}") from exc
    image.thumbnail((width, height), Image.Resampling.LANCZOS)
    bg = image.resize((width, height)).filter(ImageFilter.GaussianBlur(28))
    x = (width - image.width) // 2
    y = (height - image.height) // 2
    bg.paste(image, (x, y))
    return bg


def _write_concat_file(path: Path, segments: list[dict[str, Any]]) -> None:
    lines: list[str] = []
    for item in segments:
        normalized = str(Path(item["path"]).resolve()).replace("\\", "/")
        lines.append(f"file '{normalized}'")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _copy_platform_outputs(master: Path, no_subtitles: Path, output_dir: Path) -> dict[str, str]:
    outputs = {"master_1080x1920": str(master)}
    for name in ("youtube_shorts.mp4", "instagram_reels.mp4", "facebook_reels.mp4"):
        target = output_dir / name
        shutil.copyfile(master, target)
        outputs[name.removesuffix(".mp4")] = str(target)
    no_subtitles_target = output_dir / "no_subtitles.mp4"
    if no_subtitles.resolve() != no_subtitles_target.resolve():
        shutil.copyfile(no_subtitles, no_subtitles_target)
    outputs["no_subtitles"] = str(no_subtitles_target)
    return outputs


def _mux_voice_only(video: Path, voice: Path, target: Path, target_duration: float, visual_duration: float) -> None:
    args = ["-y", "-v", "error", "-i", str(video), "-i", str(voice)]
    args += _duration_control_args(target_duration, visual_duration)
    args += ["-c:a", "aac", "-b:a", "192k", str(target)]
    _run_ffmpeg(args)


def _mux_voice_and_music(
    video: Path,
    voice: Path,
    music: Path,
    target: Path,
    duration: float,
    target_duration: float,
    *,
    volume: float = DEFAULT_MUSIC_VOLUME,
    ducking: bool = True,
) -> None:
    """Loop the music bed under the narration, optionally ducking it under speech.

    volume/ducking come from assets/music/music_manifest.json (written by
    src.audio.music_manifest) instead of being hardcoded, so the user's chosen
    level is what actually ends up in the render.
    """
    # The bed must cover the *final* duration, not just the visual timeline -
    # narration_plus_tail can extend the output past the last scene.
    duration_arg = f"{max(0.1, max(duration, target_duration)):.3f}"
    # ...and so must the mix itself. `amix=duration=first` ends the mixed stream
    # with its first input, so without this pad the whole audio track stopped at
    # the narration and the end tail came out silent even though the bed above was
    # already prepared for the full length (measured on a real render: 60.233 s of
    # video against 59.475 s of audio). Padding the narration with silence up to
    # the same length makes "first" span the whole output; it also feeds the
    # sidechain silence over the tail, so the bed rises back to its full level
    # there instead of staying ducked. No-op whenever the narration is already
    # that long, so a render without a tail is bit-for-bit unchanged.
    voice_chain = f"volume=1.0,aresample=48000,apad=whole_dur={duration_arg}"
    if ducking:
        filter_complex = (
            f"[1:a]{voice_chain},asplit=2[voice_mix][voice_sidechain];"
            f"[2:a]volume={volume:.3f},aloop=loop=-1:size=2147483647,atrim=0:{duration_arg},aresample=48000[musicbase];"
            "[musicbase][voice_sidechain]sidechaincompress=threshold=0.035:ratio=8:attack=30:release=500[musicduck];"
            "[voice_mix][musicduck]amix=inputs=2:duration=first:normalize=0[aout]"
        )
    else:
        filter_complex = (
            f"[1:a]{voice_chain}[voice_mix];"
            f"[2:a]volume={volume:.3f},aloop=loop=-1:size=2147483647,atrim=0:{duration_arg},aresample=48000[musicbase];"
            "[voice_mix][musicbase]amix=inputs=2:duration=first:normalize=0[aout]"
        )
    args = ["-y", "-v", "error", "-i", str(video), "-i", str(voice), "-i", str(music)]
    args += ["-filter_complex", filter_complex, "-map", "0:v:0", "-map", "[aout]"]
    args += _duration_control_args(target_duration, duration)
    args += ["-c:a", "aac", "-b:a", "192k", str(target)]
    _run_ffmpeg(args)


def _duration_control_args(target_duration: float, visual_duration: float) -> list[str]:
    """Build ffmpeg args that hit target_duration exactly.

    ``-shortest`` combined with ``-c:v copy`` is a known-fragile combination:
    stream copy can only cut on keyframe boundaries, so it silently overshoots
    the shorter stream instead of stopping exactly at it (this is what
    produced the pre-existing ~2.75s tail on the first live fullscreen-voiceover
    render). Re-encoding lets us cut precisely and, when narration is longer
    than the visual timeline, extend the last frame with tpad instead of
    letting the video end before the audio does.
    """
    extra = max(0.0, target_duration - visual_duration)
    vf = f"tpad=stop_mode=clone:stop_duration={extra:.3f}" if extra > 0.0 else "null"
    return [
        "-t",
        f"{max(0.1, target_duration):.3f}",
        "-vf",
        vf,
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "20",
    ]


def _burn_ass_subtitles(source: Path, subtitles: Path, target: Path) -> None:
    subtitle_filter = f"subtitles='{_escape_subtitle_path(subtitles)}'"
    _run_ffmpeg(
        [
            "-y",
            "-v",
            "error",
            "-i",
            str(source),
            "-vf",
            subtitle_filter,
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "21",
            "-c:a",
            "copy",
            str(target),
        ]
    )


def _escape_subtitle_path(path: Path) -> str:
    normalized = str(path.resolve()).replace("\\", "/")
    return normalized.replace(":", "\\:").replace("'", "\\'")


def _script_duration(script: dict[str, Any]) -> float:
    total = 0.0
    for scene in script.get("scenes", []):
        start = float(scene.get("start_sec") or 0.0)
        duration = float(scene.get("actual_duration_sec") or scene.get("target_duration_sec") or 0.0)
        total = max(total, start + duration)
    return total


def _load_subtitles_manifest(root: Path, language: str) -> dict[str, Any]:
    path = root / "localizations" / language / "subtitles" / "subtitles_manifest.json"
    if not path.exists():
        return {}
    try:
        import json

        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _load_music_manifest(root: Path) -> dict[str, Any]:
    """Kept as a thin wrapper so existing callers/tests keep working; the tolerant
    reader itself now lives next to the writer in src.audio.music_manifest."""
    return read_music_manifest(root)


def _run_ffmpeg(args: list[str]) -> None:
    command = [imageio_ffmpeg.get_ffmpeg_exe(), *args]
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise RuntimeError((result.stderr or "").strip() or "FFmpeg failed.")
