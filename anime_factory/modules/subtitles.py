from __future__ import annotations

import re
import textwrap
from pathlib import Path
from typing import Any

from .transcribe import format_srt_time


def _ass_time(seconds: float) -> str:
    centiseconds = int(round(seconds * 100))
    hours, rem = divmod(centiseconds, 360_000)
    minutes, rem = divmod(rem, 6_000)
    secs, centis = divmod(rem, 100)
    return f"{hours}:{minutes:02}:{secs:02}.{centis:02}"


def _split_text(text: str, max_chars: int = 24, max_lines: int = 2) -> str:
    clean = re.sub(r"\s+", " ", text).strip()
    if not clean:
        return ""
    wrapped = textwrap.wrap(clean, width=max_chars, break_long_words=False, break_on_hyphens=False)
    if len(wrapped) <= max_lines:
        return "\n".join(wrapped)
    first = wrapped[0]
    second = " ".join(wrapped[1:])
    second_wrapped = textwrap.wrap(second, width=max_chars, break_long_words=False, break_on_hyphens=False)
    return "\n".join([first, second_wrapped[0] if second_wrapped else ""])


def _relative_segments(candidate: dict[str, Any], max_chars: int, max_lines: int) -> list[dict[str, Any]]:
    clip_start = float(candidate["start"])
    duration = float(candidate["duration"])
    output: list[dict[str, Any]] = []
    for segment in candidate.get("subtitle_segments", []):
        start = max(0.0, float(segment["start"]) - clip_start)
        end = min(duration, float(segment["end"]) - clip_start)
        text = _split_text(str(segment.get("text", "")), max_chars=max_chars, max_lines=max_lines)
        if text and end > start:
            output.append({"start": start, "end": end, "text": text})
    return output


def write_short_subtitles(candidate: dict[str, Any], output_dir: Path, config: dict[str, Any]) -> tuple[Path, Path]:
    subtitle_config = config.get("subtitles", {})
    max_chars = int(subtitle_config.get("max_chars_per_line", 24))
    max_lines = int(subtitle_config.get("max_lines", 2))
    short_id = int(candidate["id"])
    srt_path = output_dir / f"short_{short_id:03}.srt"
    ass_path = output_dir / f"short_{short_id:03}.ass"
    segments = _relative_segments(candidate, max_chars=max_chars, max_lines=max_lines)

    srt_lines: list[str] = []
    for index, segment in enumerate(segments, start=1):
        srt_lines.append(str(index))
        srt_lines.append(f"{format_srt_time(segment['start'])} --> {format_srt_time(segment['end'])}")
        srt_lines.append(segment["text"])
        srt_lines.append("")
    srt_path.write_text("\n".join(srt_lines), encoding="utf-8")

    font_name = subtitle_config.get("font_name", "Arial")
    font_size = int(subtitle_config.get("font_size", 72))
    ass_lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 1080",
        "PlayResY: 1920",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Default,{font_name},{font_size},&H00FFFFFF,&H000000FF,&H00000000,&HAA000000,-1,0,0,0,100,100,0,0,3,4,0,2,80,80,180,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    for segment in segments:
        text = segment["text"].replace("{", "(").replace("}", ")").replace("\n", r"\N")
        ass_lines.append(f"Dialogue: 0,{_ass_time(segment['start'])},{_ass_time(segment['end'])},Default,,0,0,0,,{text}")
    ass_path.write_text("\n".join(ass_lines), encoding="utf-8")
    return srt_path, ass_path
