from __future__ import annotations

import shutil
from pathlib import Path

from .ffmpeg_utils import run_ffmpeg


def copy_source_video(input_video: Path, destination: Path, force: bool = False) -> Path:
    if not input_video.exists():
        raise FileNotFoundError(f"Не найден исходный видеофайл: {input_video}")
    if destination.exists() and not force:
        print(f"Видео уже скопировано, пропускаю: {destination}")
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(input_video, destination)
    print(f"Исходное видео скопировано: {destination}")
    return destination


def extract_audio(source_video: Path, audio_wav: Path, force: bool = False) -> Path:
    if audio_wav.exists() and not force:
        print(f"Аудио уже существует, пропускаю извлечение: {audio_wav}")
        return audio_wav
    print("Извлекаю аудио через ffmpeg...")
    audio_wav.parent.mkdir(parents=True, exist_ok=True)
    run_ffmpeg([
        "-i",
        str(source_video),
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        "16000",
        "-ac",
        "1",
        str(audio_wav),
    ])
    print(f"Аудио сохранено: {audio_wav}")
    return audio_wav
