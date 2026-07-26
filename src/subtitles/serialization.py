"""SRT и ASS: единственное место, где cue превращается в файл.

Поддерживаются ровно два формата, потому что ровно два кто-то читает: ASS вжигает
``src/news/final_renderer.py`` (фильтр ``subtitles=``), SRT забирает
``src/news/exporter.py`` в папку выдачи. VTT в репозитории не используется ничем и
поэтому здесь отсутствует - сериализаторов «на будущее» тут нет.

Cue не знает про ASS: стиль приходит отдельным ``SubtitleStyle``, а перенос строки
внутри cue - обычный ``\\n``, который в ASS превращается в ``\\N``, а в SRT
остаётся как есть.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .models import (
    FORMAT_ASS,
    FORMAT_SRT,
    SUPPORTED_FORMATS,
    SubtitleCue,
    SubtitleError,
    SubtitleStyle,
    ERR_UNSUPPORTED_FORMAT,
)

# Всегда "\n": файл читают ffmpeg и экспортер, а не Notepad, и одинаковый перевод
# строки на всех платформах - условие воспроизводимости артефакта.
NEWLINE = "\n"

_SRT_TIME_RE = re.compile(r"(\d{2}):(\d{2}):(\d{2})[,.](\d{1,3})")


def format_srt_time(seconds: float) -> str:
    millis = max(0, int(round(seconds * 1000)))
    hours, rest = divmod(millis, 3_600_000)
    minutes, rest = divmod(rest, 60_000)
    secs, ms = divmod(rest, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def format_ass_time(seconds: float) -> str:
    centis = max(0, int(round(seconds * 100)))
    hours, rest = divmod(centis, 360_000)
    minutes, rest = divmod(rest, 6_000)
    secs, cs = divmod(rest, 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{cs:02d}"


def parse_srt_time(value: str) -> float:
    match = _SRT_TIME_RE.search(value)
    if not match:
        raise SubtitleError(f"Не удалось прочитать время SRT: {value!r}", reason=ERR_UNSUPPORTED_FORMAT)
    hours, minutes, seconds, millis = match.groups()
    return int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(millis.ljust(3, "0")) / 1000


def _apply_capitalization(text: str, style: SubtitleStyle) -> str:
    """Регистр - оформление, а не текст: применяется только при сериализации, чтобы
    cue оставался дословной копией реплики и проверка полноты покрытия работала."""
    mode = (style.capitalization or "none").lower()
    if mode in {"upper", "uppercase"}:
        return text.upper()
    if mode in {"lower", "lowercase"}:
        return text.lower()
    return text


def to_srt(cues: tuple[SubtitleCue, ...] | list[SubtitleCue], *, style: SubtitleStyle | None = None) -> str:
    effective = style or SubtitleStyle()
    blocks: list[str] = []
    for number, cue in enumerate(cues, start=1):
        text = _apply_capitalization(cue.text, effective)
        blocks.append(
            f"{number}{NEWLINE}"
            f"{format_srt_time(cue.start_sec)} --> {format_srt_time(cue.end_sec)}{NEWLINE}"
            f"{text}{NEWLINE}"
        )
    return NEWLINE.join(blocks)


def ass_style_line(style: SubtitleStyle) -> str:
    """Строка ``Style:`` ASS.

    При значениях по умолчанию даёт в точности тот заголовок, который вжигался до
    Q3 (``Default,Arial,72,&H00FFFFFF,&H00000000,1,4,0,2,80,80,260,1``), поэтому
    подключение стиля канала само по себе не меняет картинку.
    """
    return (
        f"Style: Default,{style.font_family},{style.font_size},"
        f"{style.primary_colour},{style.outline_colour},{style.border_style},"
        f"{style.outline_width if style.outline else 0},{style.shadow_width},"
        f"{style.ass_alignment},{style.margin_left},{style.margin_right},"
        f"{style.margin_bottom},{style.encoding}"
    )


def _ass_escape(text: str) -> str:
    return text.replace("{", "").replace("}", "").replace("\r", "").replace(NEWLINE, "\\N")


def to_ass(cues: tuple[SubtitleCue, ...] | list[SubtitleCue], *, style: SubtitleStyle | None = None) -> str:
    effective = style or SubtitleStyle()
    header = [
        "[Script Info]",
        "ScriptType: v4.00+",
        f"PlayResX: {effective.play_res_x}",
        f"PlayResY: {effective.play_res_y}",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding",
        ass_style_line(effective),
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    events = [
        f"Dialogue: 0,{format_ass_time(cue.start_sec)},{format_ass_time(cue.end_sec)},Default,,0,0,0,,"
        f"{_ass_escape(_apply_capitalization(cue.text, effective))}"
        for cue in cues
    ]
    return NEWLINE.join(header + events) + NEWLINE


def serialize(
    cues: tuple[SubtitleCue, ...] | list[SubtitleCue],
    subtitle_format: str,
    *,
    style: SubtitleStyle | None = None,
) -> str:
    if subtitle_format == FORMAT_SRT:
        return to_srt(cues, style=style)
    if subtitle_format == FORMAT_ASS:
        return to_ass(cues, style=style)
    raise SubtitleError(
        f"Формат субтитров {subtitle_format!r} не поддерживается (есть {', '.join(SUPPORTED_FORMATS)}).",
        reason=ERR_UNSUPPORTED_FORMAT,
    )


def write_subtitle_file(
    path: str | Path,
    cues: tuple[SubtitleCue, ...] | list[SubtitleCue],
    subtitle_format: str,
    *,
    style: SubtitleStyle | None = None,
) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    # newline="" - иначе Windows превратил бы "\n" в "\r\n" и один и тот же набор
    # cues давал бы разные байты на разных машинах.
    with open(target, "w", encoding="utf-8", newline="") as handle:
        handle.write(serialize(cues, subtitle_format, style=style))
    return target


def read_srt(path: str | Path, *, language: str = "", scene_id: str = "") -> list[SubtitleCue]:
    """Прочитать SRT обратно в cues.

    Нужно для ``subtitles validate``: старый файл, у которого нет ни манифеста, ни
    ``scene_id``, всё равно можно проверить на время, порядок и пересечения.
    ``scene_id`` в таком файле физически отсутствует, поэтому подставляется тот,
    что передал вызывающий (по умолчанию пустой).
    """
    text = Path(path).read_text(encoding="utf-8-sig")
    cues: list[SubtitleCue] = []
    for raw_block in re.split(r"\n\s*\n", text.replace("\r\n", "\n").strip()):
        lines = [line for line in raw_block.split("\n") if line.strip() != ""]
        if len(lines) < 2:
            continue
        offset = 1 if lines[0].strip().isdigit() else 0
        if "-->" not in lines[offset]:
            continue
        left, _, right = lines[offset].partition("-->")
        body = NEWLINE.join(lines[offset + 1 :])
        index = len(cues) + 1
        cues.append(
            SubtitleCue(
                cue_id=f"{scene_id or 'srt'}#{index:02d}",
                scene_id=scene_id,
                index=index,
                scene_cue_index=index,
                text=body,
                start_sec=parse_srt_time(left),
                end_sec=parse_srt_time(right),
                language=language,
            )
        )
    return cues


def subtitle_filename(subtitle_format: str) -> str:
    """Имя файла. Совпадает с тем, что уже лежит в проектах и что копирует
    ``src/news/exporter.py`` - переименование сломало бы старые проекты."""
    if subtitle_format not in SUPPORTED_FORMATS:
        raise SubtitleError(f"Формат {subtitle_format!r} не поддерживается.", reason=ERR_UNSUPPORTED_FORMAT)
    return f"subtitles.{subtitle_format}"


def describe_formats() -> list[dict[str, Any]]:
    return [
        {"format": FORMAT_SRT, "filename": subtitle_filename(FORMAT_SRT), "consumer": "src.news.exporter"},
        {"format": FORMAT_ASS, "filename": subtitle_filename(FORMAT_ASS), "consumer": "src.news.final_renderer"},
    ]


__all__ = [
    "NEWLINE",
    "ass_style_line",
    "describe_formats",
    "format_ass_time",
    "format_srt_time",
    "parse_srt_time",
    "read_srt",
    "serialize",
    "subtitle_filename",
    "to_ass",
    "to_srt",
    "write_subtitle_file",
]
