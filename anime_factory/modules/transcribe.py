from __future__ import annotations

from pathlib import Path
from typing import Any

from .paths import read_json, write_json


def format_srt_time(seconds: float) -> str:
    milliseconds = int(round(seconds * 1000))
    hours, rem = divmod(milliseconds, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    secs, millis = divmod(rem, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"


def save_srt(segments: list[dict[str, Any]], path: Path) -> None:
    lines: list[str] = []
    for index, segment in enumerate(segments, start=1):
        lines.append(str(index))
        lines.append(f"{format_srt_time(float(segment['start']))} --> {format_srt_time(float(segment['end']))}")
        lines.append(str(segment["text"]).strip())
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def transcribe_audio(
    audio_wav: Path,
    transcript_json: Path,
    subtitles_raw_srt: Path,
    model_name: str = "small",
    force: bool = False,
) -> list[dict[str, Any]]:
    if transcript_json.exists() and subtitles_raw_srt.exists() and not force:
        print(f"Транскрипт уже существует, пропускаю транскрибацию: {transcript_json}")
        return read_json(transcript_json)

    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError(
            "Не установлена зависимость faster-whisper. Выполните: pip install -r anime_factory/requirements.txt"
        ) from exc

    print(f"Запускаю транскрибацию faster-whisper, модель: {model_name}")
    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    raw_segments, _info = model.transcribe(str(audio_wav), beam_size=5)
    segments: list[dict[str, Any]] = []
    for index, segment in enumerate(raw_segments):
        text = segment.text.strip()
        if not text:
            continue
        segments.append({"id": index, "start": round(float(segment.start), 2), "end": round(float(segment.end), 2), "text": text})

    write_json(transcript_json, segments)
    save_srt(segments, subtitles_raw_srt)
    print(f"Транскрипт сохранен: {transcript_json}")
    print(f"Сырые субтитры сохранены: {subtitles_raw_srt}")
    return segments
