from __future__ import annotations

import math
import shutil
import subprocess
from pathlib import Path
from typing import Any

import imageio_ffmpeg
from PIL import Image, ImageFilter, ImageOps

from src.assets.completion.modes import (
    DEFAULT_COMPLETION_MODE,
    MODE_DRAFT_COMPLETE,
    evaluate_usability,
    normalize_mode,
)
from src.audio.end_tail_policy import (
    DEFAULT_TAIL_SEC,
    END_POLICY_NARRATION_PLUS_TAIL,
    clamp_tail_sec,
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
    completion_mode: str = DEFAULT_COMPLETION_MODE,
) -> dict[str, Any]:
    completion_mode = normalize_mode(completion_mode)
    is_draft = completion_mode == MODE_DRAFT_COMPLETE
    completion_summary = (
        assets_manifest.get("completion")
        if isinstance(assets_manifest.get("completion"), dict)
        else {}
    )
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
        completion_mode=completion_mode,
    )
    concat_path = render_dir / "frames.txt"
    _write_concat_file(concat_path, segments)
    silent_video = render_dir / "silent_master.mp4"
    master = output_dir / ("draft_1080x1920.mp4" if is_draft else "master_1080x1920.mp4")
    no_subtitles = output_dir / ("draft_no_subtitles.mp4" if is_draft else "no_subtitles.mp4")
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
    effective_tail_sec = (
        clamp_tail_sec(tail_sec)
        if end_policy_id == END_POLICY_NARRATION_PLUS_TAIL
        else float(tail_sec)
    )
    target_duration = compute_target_duration(
        end_policy_id,
        narration_duration_sec=narration_duration_sec,
        visual_duration_sec=duration,
        tail_sec=effective_tail_sec,
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
            _mux_voice_only(
                silent_video,
                Path(audio_path),
                no_subtitles,
                target_duration,
                duration,
            )
    else:
        _run_ffmpeg(["-y", "-v", "error", "-i", str(silent_video), "-c:v", "copy", str(no_subtitles)])
    subtitles_manifest = _load_subtitles_manifest(root, language)
    subtitle_path = subtitles_manifest.get("ass_path") or ""
    render_subtitle_path = ""
    subtitles_embedded = False
    if subtitle_path and Path(subtitle_path).exists():
        subtitle_source = Path(subtitle_path)
        render_subtitle_path = str(subtitle_source)
        _burn_ass_subtitles(no_subtitles, subtitle_source, master)
        subtitles_embedded = True
    else:
        shutil.copyfile(no_subtitles, master)
    outputs = _copy_platform_outputs(master, no_subtitles, output_dir, draft=is_draft)
    return {
        "status": "completed",
        "render_status": "draft_completed" if is_draft else "completed",
        "completion_mode": completion_mode,
        "output_kind": "draft" if is_draft else "standard",
        "publish_ready": False if is_draft else bool(completion_summary.get("publish_ready", True)),
        "output_path": str(master),
        "outputs": outputs,
        # One segment per visual slot since Q2.2B; for a single-asset video these are
        # the same number, which is what every earlier project and test sees.
        "scene_count": len({str(item.get("scene_id") or item["path"]) for item in segments}),
        "segment_count": len(segments),
        "segments": [
            {
                "scene_id": str(item.get("scene_id") or ""),
                "slot_id": str(item.get("slot_id") or ""),
                "duration_sec": round(float(item.get("duration") or 0.0), 3),
                "start_offset_sec": round(float(item.get("start_offset_sec") or 0.0), 3),
                "end_offset_sec": round(float(item.get("end_offset_sec") or 0.0), 3),
                "quality_tier": str(item.get("quality_tier") or ""),
                "crop_decision": dict(item.get("crop_decision") or {}),
            }
            for item in segments
        ],
        "resolution": {"width": width, "height": height},
        "audio_path": str(audio_path),
        "music_path": str(music_path),
        "subtitle_path": str(subtitle_path),
        "render_subtitle_path": render_subtitle_path,
        "subtitle_layers": 1 if subtitles_embedded else 0,
        "renderer": "news_to_short_final_renderer_v2",
        "visual_duration_sec": duration,
        "narration_duration_sec": narration_duration_sec,
        "end_policy_id": end_policy_id,
        "tail_sec": effective_tail_sec,
        "target_duration_sec": target_duration if (audio_path and Path(audio_path).exists()) else duration,
        "audio_timing_policy": "preserve_source_duration",
        "audio_time_stretched": False,
        "speech_tempo": 1.0,
        "response_hold_sec": 0.0,
        "duration_floor_sec": 0.0,
    }


def _create_scene_segments(
    *,
    segments_dir: Path,
    width: int,
    height: int,
    script: dict[str, Any],
    assets_manifest: dict[str, Any],
    completion_mode: str = DEFAULT_COMPLETION_MODE,
) -> list[dict[str, Any]]:
    """One segment per visual slot, laid on the scene's own timeline.

    A scene written before stage Q2.2B carries one ``selected_asset`` and is read as a
    one-slot assembly, which produces exactly the segment this function always produced.
    A multi-slot scene keeps its stored relative boundaries and scales them to the
    scene's *real* duration here, because the assembly was built while only the planned
    duration was known and the voice stage may have replaced it since.
    """
    from src.assets.completion import read_assembly
    from src.assets.completion.assembly import scaled_slot_windows

    completion_mode = normalize_mode(completion_mode)
    is_draft = completion_mode == MODE_DRAFT_COMPLETE
    entry_by_scene = {
        str(entry.get("scene_id") or ""): entry for entry in assets_manifest.get("scenes", []) if isinstance(entry, dict)
    }
    segments: list[dict[str, Any]] = []
    for index, scene in enumerate(script.get("scenes", []), start=1):
        scene_id = str(scene.get("scene_id") or f"scene_{index:03d}")
        # actual_duration_sec (written by the voice stage from the real narration)
        # wins over the planned target_duration_sec; see src.audio.scene_timeline.
        duration = scene_render_duration(scene)
        assembly = read_assembly(entry_by_scene.get(scene_id, {}), scene_duration_sec=duration)
        if not assembly.slots:
            raise RuntimeError(f"Scene {scene_id} has no renderable visual asset.")
        problems = assembly.validate()
        if problems:
            raise RuntimeError(f"Scene {scene_id} has an invalid visual assembly: {', '.join(problems)}")
        try:
            timed_slots = scaled_slot_windows(assembly, duration)
        except ValueError as exc:
            raise RuntimeError(f"Scene {scene_id} has an invalid visual assembly: {exc}") from exc
        for position, (slot, start_offset, end_offset) in enumerate(timed_slots, start=1):
            source_path = slot.media_path
            if not source_path or not Path(source_path).is_file():
                raise RuntimeError(f"Scene {scene_id} slot {slot.slot_id} has no renderable file: {source_path}")
            if is_draft:
                # Never trust the serialized slot verdict as a render authorization.
                # Files, rights metadata, and nested policy records can change after an
                # assembly was written, so the final boundary re-evaluates the asset.
                readiness = evaluate_usability(
                    slot.selected_asset,
                    mode=MODE_DRAFT_COMPLETE,
                    quality_tier=slot.quality_tier,
                    require_local_file=True,
                    reuse_count=1 if slot.reuse_of_asset else 0,
                )
                if not readiness.usable_in_draft or not readiness.automatic_render_allowed:
                    detail = ",".join(readiness.block_reasons) or "slot_not_usable_in_draft"
                    raise RuntimeError(f"Scene {scene_id} slot {slot.slot_id} is blocked: {detail}")
            slot_duration = round(end_offset - start_offset, 3)
            if not math.isfinite(slot_duration) or slot_duration <= 0:
                raise RuntimeError(
                    f"Scene {scene_id} slot {slot.slot_id} has a non-positive "
                    f"render duration: {slot_duration}"
                )
            suffix = "" if len(timed_slots) == 1 else f"_{position:03d}"
            segment_path = segments_dir / f"{scene_id}{suffix}.mp4"
            media_type = str(slot.selected_asset.get("type") or slot.selected_asset.get("media_type") or "")
            if media_type == "video" or Path(source_path).suffix.lower() in {".mp4", ".mov", ".m4v"}:
                _render_video_segment(
                    Path(source_path),
                    segment_path,
                    slot_duration,
                    width,
                    height,
                    crop_decision=slot.crop_decision,
                )
            else:
                frame_path = segments_dir / f"{scene_id}{suffix}.png"
                _base_frame(
                    source_path,
                    width,
                    height,
                    crop_decision=slot.crop_decision,
                ).save(frame_path)
                _render_image_segment(frame_path, segment_path, slot_duration, width, height)
            segments.append(
                {
                    "path": segment_path,
                    "duration": slot_duration,
                    "start_offset_sec": start_offset,
                    "end_offset_sec": end_offset,
                    "scene_id": scene_id,
                    "slot_id": slot.slot_id,
                    "quality_tier": slot.quality_tier,
                    "crop_decision": dict(slot.crop_decision),
                }
            )
    return segments


def _render_video_segment(
    source: Path,
    target: Path,
    duration: float,
    width: int,
    height: int,
    *,
    crop_decision: dict[str, Any] | None = None,
) -> None:
    vf = _video_filter(width, height, crop_decision=crop_decision)
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
    # The base frame is already cropped to the delivery canvas. A restrained
    # centre-weighted push keeps licensed stills documentary-looking without turning
    # them into static cards or revealing pixels outside the approved crop.
    vf = (
        f"scale={width}:{height},"
        "zoompan="
        "z='min(max(zoom,pzoom)+0.00018,1.08)':"
        "x='iw/2-(iw/zoom/2)':"
        "y='ih/2-(ih/zoom/2)':"
        f"d=1:s={width}x{height}:fps=30,"
        "setsar=1,format=yuv420p"
    )
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


def _base_frame(
    source_path: str,
    width: int,
    height: int,
    *,
    crop_decision: dict[str, Any] | None = None,
) -> Image.Image:
    try:
        image = Image.open(source_path).convert("RGB")
    except Exception as exc:
        raise RuntimeError(f"Image asset could not be opened: {source_path}") from exc
    transform = _reuse_transform(crop_decision)
    if transform:
        # Reuse must be visibly different, not just differently labelled in a report.
        # Fit the source toward the requested anchor, then crop a deterministic zoomed
        # frame. This is local Pillow work and is identical on every provider order.
        zoom = transform["zoom"]
        scaled_width = max(width, _even_ceil(width * zoom))
        scaled_height = max(height, _even_ceil(height * zoom))
        anchor = transform["anchor"]
        center_x = 0.0 if anchor == "left" else 1.0 if anchor == "right" else 0.5
        center_y = 0.0 if anchor == "top" else 1.0 if anchor == "bottom" else 0.5
        fitted = ImageOps.fit(
            image,
            (scaled_width, scaled_height),
            method=Image.Resampling.LANCZOS,
            centering=(center_x, center_y),
        )
        left = 0 if anchor == "left" else scaled_width - width if anchor == "right" else (scaled_width - width) // 2
        top = 0 if anchor == "top" else scaled_height - height if anchor == "bottom" else (scaled_height - height) // 2
        return fitted.crop((left, top, left + width, top + height)).convert("RGB")
    image.thumbnail((width, height), Image.Resampling.LANCZOS)
    bg = image.resize((width, height)).filter(ImageFilter.GaussianBlur(28))
    x = (width - image.width) // 2
    y = (height - image.height) // 2
    bg.paste(image, (x, y))
    return bg


def _video_filter(
    width: int,
    height: int,
    *,
    crop_decision: dict[str, Any] | None = None,
) -> str:
    """FFmpeg filter with a real alternate crop for a reused visual.

    The no-transform branch stays byte-for-byte compatible with the pre-Q2.2B
    renderer. A reuse transform scales past the output frame and anchors the crop at a
    deterministic edge, so two uses no longer render the same pixels.
    """

    transform = _reuse_transform(crop_decision)
    if not transform:
        return (
            f"scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},setsar=1,fps=30,format=yuv420p"
        )
    zoom = transform["zoom"]
    scaled_width = max(width, _even_ceil(width * zoom))
    scaled_height = max(height, _even_ceil(height * zoom))
    anchor = transform["anchor"]
    crop_x = "0" if anchor == "left" else "iw-ow" if anchor == "right" else "(iw-ow)/2"
    crop_y = "0" if anchor == "top" else "ih-oh" if anchor == "bottom" else "(ih-oh)/2"
    return (
        f"scale={scaled_width}:{scaled_height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height}:{crop_x}:{crop_y},"
        "setsar=1,fps=30,format=yuv420p"
    )


def _reuse_transform(crop_decision: dict[str, Any] | None) -> dict[str, Any]:
    decision = crop_decision if isinstance(crop_decision, dict) else {}
    raw = decision.get("reuse_transform")
    if not isinstance(raw, dict):
        return {}
    anchor = str(raw.get("anchor") or "").strip().lower()
    if anchor not in {"left", "right", "top", "bottom"}:
        return {}
    try:
        zoom = float(raw.get("zoom") or 1.0)
    except (TypeError, ValueError, OverflowError):
        return {}
    if not math.isfinite(zoom):
        return {}
    return {"anchor": anchor, "zoom": min(1.25, max(1.01, zoom))}


def _even_ceil(value: float) -> int:
    rounded = int(math.ceil(float(value)))
    return rounded if rounded % 2 == 0 else rounded + 1


def _write_concat_file(path: Path, segments: list[dict[str, Any]]) -> None:
    lines: list[str] = []
    for item in segments:
        normalized = str(Path(item["path"]).resolve()).replace("\\", "/")
        # FFmpeg's concat demuxer uses its own quoting rules, not shell quoting. A
        # literal apostrophe must close the quoted token, be backslash-escaped, then
        # reopen it. This matters for ordinary Windows profile/project names such as
        # ``D:/O'Brien/video.mp4``.
        escaped = normalized.replace("'", "'\\''")
        lines.append(f"file '{escaped}'")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _copy_platform_outputs(
    master: Path,
    no_subtitles: Path,
    output_dir: Path,
    *,
    draft: bool = False,
) -> dict[str, str]:
    if draft:
        draft_no_subtitles = output_dir / "draft_no_subtitles.mp4"
        if no_subtitles.resolve() != draft_no_subtitles.resolve():
            shutil.copyfile(no_subtitles, draft_no_subtitles)
        return {
            "draft_1080x1920": str(master),
            "draft_no_subtitles": str(draft_no_subtitles),
        }

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


def _mux_voice_only(
    video: Path,
    voice: Path,
    target: Path,
    target_duration: float,
    visual_duration: float,
) -> None:
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


def _duration_control_args(
    target_duration: float,
    visual_duration: float,
) -> list[str]:
    """Build ffmpeg args that hit target_duration exactly.

    ``-shortest`` combined with ``-c:v copy`` is a known-fragile combination:
    stream copy can only cut on keyframe boundaries, so it silently overshoots
    the shorter stream instead of stopping exactly at it (this is what
    produced the pre-existing ~2.75s tail on the first live fullscreen-voiceover
    render). Re-encoding lets us cut precisely and, when narration is longer
    than the visual timeline, extend the last frame with tpad instead of
    letting the video end before the audio does.
    """
    filters = []
    extra = max(0.0, target_duration - visual_duration)
    if extra > 0.0:
        filters.append(f"tpad=stop_mode=clone:stop_duration={extra:.3f}")
    vf = ",".join(filters) if filters else "null"
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
