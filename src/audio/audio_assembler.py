from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import imageio_ffmpeg

from src.assets.frame_sampling import ffprobe_media_info, sha256_file

from .pause_policy import write_silence_wav


@dataclass
class PostProcessingConfig:
    version: str = "v1"
    enabled: bool = False
    trim_silence: bool = False
    loudness_normalize: bool = False
    loudness_target_lufs: float | None = None
    peak_limit_db: float | None = None
    sample_rate: int = 48000
    channels: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "enabled": self.enabled,
            "trim_silence": self.trim_silence,
            "loudness_normalize": self.loudness_normalize,
            "loudness_target_lufs": self.loudness_target_lufs,
            "peak_limit_db": self.peak_limit_db,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
        }


def apply_compression(*_args: Any, **_kwargs: Any) -> None:
    raise NotImplementedError(
        "Gentle compression is explicitly out of scope for Stage 2D - no proven "
        "implementation exists anywhere in this repo yet (see MIGRATION_NOTES.md)."
    )


@dataclass
class AssemblyResult:
    output_path: str
    duration_sec: float
    checksum_sha256: str
    sample_rate: int
    channels: int
    scene_count: int
    pause_total_sec: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "output_path": self.output_path,
            "duration_sec": self.duration_sec,
            "checksum_sha256": self.checksum_sha256,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "scene_count": self.scene_count,
            "pause_total_sec": self.pause_total_sec,
        }


def _db_to_linear(db: float) -> float:
    return 10 ** (db / 20)


def _run_ffmpeg(args: list[str]) -> None:
    command = [imageio_ffmpeg.get_ffmpeg_exe(), *args]
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise RuntimeError((result.stderr or "").strip() or "FFmpeg failed.")


def assemble_narration(
    scene_files: list[str | Path],
    pauses: list[float],
    *,
    target_sample_rate: int = 48000,
    target_channels: int = 1,
    output_path: str | Path,
    post_processing: PostProcessingConfig | None = None,
) -> AssemblyResult:
    """Concatenate scene audio (in order) with policy pauses, resample to the production
    format, validate the result, and atomically replace the final narration file.

    Never leaves a partial/invalid file at ``output_path`` - the file is only replaced
    after ffprobe confirms duration > 0 on a temp file in the same directory (so the
    final os.replace() is atomic on the same filesystem).
    """
    if not scene_files:
        raise ValueError("assemble_narration requires at least one scene audio file.")
    post_processing = post_processing or PostProcessingConfig()
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_output = output_path.parent / f".{output_path.stem}.partial{output_path.suffix}"

    inputs: list[Path] = []
    pause_total = 0.0
    silence_paths: list[Path] = []
    try:
        for index, scene_file in enumerate(scene_files):
            inputs.append(Path(scene_file))
            if index < len(scene_files) - 1:
                pause_sec = pauses[index] if index < len(pauses) else 0.0
                if pause_sec > 0:
                    silence_path = output_path.parent / f".pause_{index:03d}.wav"
                    write_silence_wav(silence_path, pause_sec, sample_rate=target_sample_rate, channels=target_channels)
                    silence_paths.append(silence_path)
                    inputs.append(silence_path)
                    pause_total += pause_sec

        filter_inputs = "".join(f"[{i}:a]" for i in range(len(inputs)))
        af_chain = [f"aresample={target_sample_rate}"]
        if post_processing.enabled and post_processing.trim_silence:
            af_chain.append(
                "silenceremove=start_periods=1:start_silence=0.05:start_threshold=-45dB:detection=peak,"
                "areverse,silenceremove=start_periods=1:start_silence=0.05:start_threshold=-45dB:detection=peak,areverse"
            )
        if post_processing.enabled and post_processing.loudness_normalize and post_processing.loudness_target_lufs is not None:
            af_chain.append(f"loudnorm=I={post_processing.loudness_target_lufs}:TP=-1.5:LRA=11")
        if post_processing.enabled and post_processing.peak_limit_db is not None:
            af_chain.append(f"alimiter=limit={_db_to_linear(post_processing.peak_limit_db):.6f}")
        af_chain.append(f"aformat=channel_layouts={'mono' if target_channels == 1 else 'stereo'}")
        filter_complex = f"{filter_inputs}concat=n={len(inputs)}:v=0:a=1[acat];[acat]{','.join(af_chain)}[aout]"

        args = ["-y", "-v", "error"]
        for input_path in inputs:
            args += ["-i", str(input_path)]
        args += [
            "-filter_complex",
            filter_complex,
            "-map",
            "[aout]",
            "-ar",
            str(target_sample_rate),
            "-ac",
            str(target_channels),
            str(tmp_output),
        ]
        _run_ffmpeg(args)

        info = ffprobe_media_info(tmp_output)
        duration = float(info.get("duration_sec") or 0.0)
        if info.get("status") != "passed" or duration <= 0:
            raise RuntimeError(f"Audio assembly produced an invalid narration file: {info}")
        checksum = sha256_file(tmp_output)
        result = AssemblyResult(
            output_path=str(output_path),
            duration_sec=duration,
            checksum_sha256=checksum,
            sample_rate=target_sample_rate,
            channels=target_channels,
            scene_count=len(scene_files),
            pause_total_sec=pause_total,
        )
        os.replace(tmp_output, output_path)
        return result
    finally:
        for stale in (*silence_paths, tmp_output):
            if stale.exists() and stale != output_path:
                try:
                    stale.unlink()
                except OSError:
                    pass
