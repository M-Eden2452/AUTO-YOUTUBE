from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Any

from src.audio.scene_timeline import scene_render_duration


def build_subtitles(script: dict[str, Any], output_dir: str | Path) -> dict[str, Any]:
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    segments = _segments_from_script(script)
    srt_path = target / "subtitles.srt"
    ass_path = target / "subtitles.ass"
    srt_path.write_text(_to_srt(segments), encoding="utf-8")
    ass_path.write_text(_to_ass(segments), encoding="utf-8")
    return {
        "status": "completed",
        "language": script.get("language", ""),
        "srt_path": str(srt_path),
        "ass_path": str(ass_path),
        "segments": segments,
    }


def _segments_from_script(script: dict[str, Any]) -> list[dict[str, Any]]:
    segments: list[dict[str, Any]] = []
    for scene in script.get("scenes", []):
        start = float(scene.get("start_sec", 0))
        # Same rule as the renderer (src.audio.scene_timeline): real narration timing
        # wins over the planned estimate, so subtitles and picture cannot drift apart.
        duration = scene_render_duration(scene, minimum_sec=0.1, fallback_sec=3.0)
        text = scene.get("on_screen_text") or scene.get("narration", "")
        chunks = _short_chunks(text)
        chunk_duration = duration / max(1, len(chunks))
        for chunk in chunks:
            end = start + chunk_duration
            segments.append({"start": round(start, 3), "end": round(end, 3), "text": chunk})
            start = end
    return segments


def _short_chunks(text: str, words_per_chunk: int = 5) -> list[str]:
    words = text.split()
    if not words:
        return []
    lines = []
    for index in range(0, len(words), words_per_chunk):
        lines.append(" ".join(words[index : index + words_per_chunk]))
    return lines or textwrap.wrap(text, width=28)


def _to_srt(segments: list[dict[str, Any]]) -> str:
    blocks = []
    for index, segment in enumerate(segments, start=1):
        blocks.append(
            f"{index}\n{_format_srt_time(segment['start'])} --> {_format_srt_time(segment['end'])}\n{segment['text']}\n"
        )
    return "\n".join(blocks)


def _to_ass(segments: list[dict[str, Any]]) -> str:
    header = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 1080",
        "PlayResY: 1920",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: Default,Arial,72,&H00FFFFFF,&H00000000,1,4,0,2,80,80,260,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    events = [
        f"Dialogue: 0,{_format_ass_time(item['start'])},{_format_ass_time(item['end'])},Default,,0,0,0,,{item['text']}"
        for item in segments
    ]
    return "\n".join(header + events) + "\n"


def _format_srt_time(seconds: float) -> str:
    millis = int(round(seconds * 1000))
    hours, rest = divmod(millis, 3_600_000)
    minutes, rest = divmod(rest, 60_000)
    secs, ms = divmod(rest, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def _format_ass_time(seconds: float) -> str:
    centis = int(round(seconds * 100))
    hours, rest = divmod(centis, 360_000)
    minutes, rest = divmod(rest, 6_000)
    secs, cs = divmod(rest, 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{cs:02d}"
