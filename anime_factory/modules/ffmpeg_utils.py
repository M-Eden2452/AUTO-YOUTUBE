from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def ensure_ffmpeg() -> None:
    missing = [name for name in ("ffmpeg", "ffprobe") if shutil.which(name) is None]
    if missing:
        raise RuntimeError(
            "Не найден ffmpeg/ffprobe в PATH. Установите ffmpeg и проверьте команды: ffmpeg -version, ffprobe -version."
        )


def run_ffmpeg(args: list[str]) -> None:
    ensure_ffmpeg()
    command = ["ffmpeg", "-hide_banner", "-y", *args]
    try:
        result = subprocess.run(command, check=False, capture_output=True, text=True, encoding="utf-8", errors="replace")
    except FileNotFoundError as exc:
        raise RuntimeError("Не удалось запустить ffmpeg. Проверьте установку ffmpeg и PATH.") from exc
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"ffmpeg завершился с ошибкой:\n{message}")


def probe_video_size(video_path: Path) -> tuple[int, int]:
    ensure_ffmpeg()
    command = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height",
        "-of",
        "csv=s=x:p=0",
        str(video_path),
    ]
    result = subprocess.run(command, check=False, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe не смог прочитать размер видео: {result.stderr.strip()}")
    width_text, height_text = result.stdout.strip().split("x")
    return int(width_text), int(height_text)


def ffmpeg_filter_path(path: Path) -> str:
    value = path.resolve().as_posix()
    value = value.replace(":", r"\:")
    value = value.replace("'", r"\'")
    return value
