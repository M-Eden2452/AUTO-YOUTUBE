"""Контракты единого движка субтитров (этап Q3).

Что здесь разделено намеренно и объединять это нельзя:

1. **Текст и время** - ``SubtitleSegment`` (кусок текста сцены, ещё без времени) и
   ``SubtitleCue`` (тот же кусок, у которого уже есть start/end и указан источник
   тайминга). Ни в том, ни в другом нет ни одного параметра рендера.
2. **Политика нарезки** - ``SubtitlePolicy``: сколько символов в строке, сколько
   строк, какая скорость чтения допустима. Влияет на то, *где* рвётся текст.
3. **Стиль рендера** - ``SubtitleStyle``: шрифт, размер, отступы, обводка. Влияет
   только на то, *как* субтитр выглядит, и читается из
   ``config/channels/<id>/subtitle_style.json`` (этап E2). В cue не попадает.
4. **Сериализация** - ``src.subtitles.serialization``: SRT и ASS. Cue не знает ни
   про ASS-заголовок, ни про FFmpeg.

Единственный источник границ сцен - ``src.audio.scene_timeline`` (этап B1). Свой
расчёт длительностей этот пакет не делает и делать не должен.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from typing import Any

# --- источники тайминга -------------------------------------------------------
# Порядок по фактической точности. Ни один из них не выдумывается: если данных нет,
# движок опускается на следующий уровень и честно пишет, какой уровень использован.
TIMING_SOURCE_WORD = "word_timestamps"
TIMING_SOURCE_SEGMENT = "segment_timestamps"
TIMING_SOURCE_SCENE_TIMELINE = "scene_timeline"
TIMING_SOURCE_LEGACY_PLANNED = "legacy_planned"
TIMING_SOURCE_UNAVAILABLE = "unavailable"

TIMING_SOURCE_PRECISION = {
    TIMING_SOURCE_WORD: 4,
    TIMING_SOURCE_SEGMENT: 3,
    TIMING_SOURCE_SCENE_TIMELINE: 2,
    TIMING_SOURCE_LEGACY_PLANNED: 1,
    TIMING_SOURCE_UNAVAILABLE: 0,
}

TIMING_SOURCES = frozenset(TIMING_SOURCE_PRECISION)

# --- форматы ------------------------------------------------------------------
# Только те, что действительно кто-то читает: ASS вжигает
# src/news/final_renderer.py, SRT забирает src/news/exporter.py. VTT в репозитории
# не используется ничем и поэтому не поддерживается.
FORMAT_SRT = "srt"
FORMAT_ASS = "ass"
SUPPORTED_FORMATS = (FORMAT_SRT, FORMAT_ASS)

# --- поля сценария, из которых берётся текст ----------------------------------
TEXT_FIELD_NARRATION = "narration"
TEXT_FIELD_ON_SCREEN = "on_screen_text"

# --- коды проблем -------------------------------------------------------------
# Стиль тот же, что у src.localization.models: стабильный машинный код + severity,
# чтобы CLI и пайплайн не разбирали текст сообщения.
ERR_MISSING_SCRIPT = "missing_script"
ERR_NO_SCENES = "no_scenes"
ERR_NO_CUES = "no_cues"
ERR_EMPTY_CUE_TEXT = "empty_cue_text"
ERR_DUPLICATE_SCENE_ID = "duplicate_scene_id"
ERR_UNKNOWN_SCENE_ID = "unknown_scene_id"
ERR_CUE_WITHOUT_SCENE = "cue_without_scene"
ERR_CUE_ORDER_INVALID = "cue_order_invalid"
ERR_NEGATIVE_TIME = "negative_time"
ERR_NON_FINITE_TIME = "non_finite_time"
ERR_END_NOT_AFTER_START = "end_not_after_start"
ERR_CUE_OVERLAP = "cue_overlap"
ERR_CUE_OUTSIDE_SCENE = "cue_outside_scene"
ERR_CUE_OUTSIDE_NARRATION = "cue_outside_narration"
ERR_TEXT_NOT_COVERED = "text_not_covered"
ERR_LANGUAGE_MISMATCH = "language_mismatch"
ERR_NARRATION_MISMATCH = "narration_reference_mismatch"
ERR_DUPLICATE_PATH = "duplicate_subtitle_path"
ERR_UNSUPPORTED_FORMAT = "unsupported_format"
ERR_PROTECTED_ARTIFACT = "protected_artifact_overwrite"
ERR_MISSING_LOCALIZATION = "missing_localization"

WARN_CUE_TOO_SHORT = "cue_too_short"
WARN_CUE_TOO_LONG = "cue_too_long"
WARN_READING_SPEED = "reading_speed_too_high"
WARN_LINE_TOO_LONG = "line_too_long"
WARN_TOO_MANY_LINES = "too_many_lines"
WARN_ORPHAN_LINE = "orphan_short_line"
WARN_GAP_TOO_LARGE = "gap_too_large"
WARN_DUPLICATE_TEXT = "duplicate_cue_text"
WARN_LEGACY_TIMING = "legacy_timing_source"
WARN_NARRATION_DURATION_UNKNOWN = "narration_duration_unknown"
WARN_ON_SCREEN_TEXT_USED = "on_screen_text_used"
WARN_MISSING_SCENE_PLAN = "missing_scene_plan"
WARN_LEGACY_ARTIFACT = "legacy_artifact_without_metadata"

SEVERITY_ERROR = "error"
SEVERITY_WARNING = "warning"


class SubtitleError(ValueError):
    """Запрос субтитров невозможно выполнить. ``reason`` - один из кодов выше."""

    def __init__(self, message: str, *, reason: str = "generic") -> None:
        super().__init__(message)
        self.reason = reason


@dataclass(frozen=True)
class SubtitleIssue:
    code: str
    severity: str
    message: str
    scene_id: str = ""
    cue_id: str = ""

    @property
    def is_error(self) -> bool:
        return self.severity == SEVERITY_ERROR

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "scene_id": self.scene_id,
            "cue_id": self.cue_id,
        }


def error(code: str, message: str, *, scene_id: str = "", cue_id: str = "") -> SubtitleIssue:
    return SubtitleIssue(code=code, severity=SEVERITY_ERROR, message=message, scene_id=scene_id, cue_id=cue_id)


def warning(code: str, message: str, *, scene_id: str = "", cue_id: str = "") -> SubtitleIssue:
    return SubtitleIssue(code=code, severity=SEVERITY_WARNING, message=message, scene_id=scene_id, cue_id=cue_id)


@dataclass(frozen=True)
class SubtitleValidationResult:
    issues: tuple[SubtitleIssue, ...] = ()

    @property
    def errors(self) -> tuple[SubtitleIssue, ...]:
        return tuple(issue for issue in self.issues if issue.is_error)

    @property
    def warnings(self) -> tuple[SubtitleIssue, ...]:
        return tuple(issue for issue in self.issues if not issue.is_error)

    @property
    def ok(self) -> bool:
        return not self.errors

    @property
    def status(self) -> str:
        if self.errors:
            return "failed"
        if self.warnings:
            return "needs_review"
        return "passed"

    def codes(self) -> tuple[str, ...]:
        return tuple(issue.code for issue in self.issues)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "issues": [issue.to_dict() for issue in self.issues],
        }


@dataclass(frozen=True)
class SubtitleStyle:
    """Оформление субтитра. Читается из ``config/channels/<id>/subtitle_style.json``.

    Значения по умолчанию - **ровно то**, что до Q3 было зашито в ASS-заголовок
    ``src/news/subtitles.py`` (``Arial,72,...,1,4,0,2,80,80,260,1``). Канал, у
    которого ``subtitle_style.json`` совпадает с этими значениями, получает
    байт-идентичный заголовок: подключение E2 само по себе не меняет картинку.

    ``safe_zone_top``/``safe_zone_bottom`` из файла канала здесь только хранятся и
    показываются: превращать их в ``margin_bottom`` значило бы сдвинуть субтитры
    уже проверенного канала (320 вместо 260). Отступ меняется только явным
    ``margin_v`` в файле канала.
    """

    style_id: str = "documentary"
    font_family: str = "Arial"
    font_size: int = 72
    alignment: str = "center"
    outline: bool = True
    outline_width: int = 4
    shadow_width: int = 0
    border_style: int = 1
    margin_left: int = 80
    margin_right: int = 80
    margin_bottom: int = 260
    primary_colour: str = "&H00FFFFFF"
    outline_colour: str = "&H00000000"
    encoding: int = 1
    play_res_x: int = 1080
    play_res_y: int = 1920
    max_lines: int = 2
    max_words_per_fragment: int = 6
    max_characters_per_line: int = 0  # 0 = вывести из размера шрифта и полей
    capitalization: str = "none"
    safe_zone_top: int = 0
    safe_zone_bottom: int = 0
    save_srt: bool = True
    save_ass: bool = True
    burned_in_default: bool = True
    source: str = "default"
    origin: str = ""

    ASS_ALIGNMENT = {"left": 1, "center": 2, "centre": 2, "right": 3}

    @property
    def ass_alignment(self) -> int:
        return self.ASS_ALIGNMENT.get(str(self.alignment).lower(), 2)

    @property
    def effective_characters_per_line(self) -> int:
        """Сколько символов физически влезает в строку.

        Оценка, а не измерение шрифта: средняя ширина строчного глифа Arial (и
        латиницы, и кириллицы) - около половины кегля. При 1080 px, полях 80+80 и
        кегле 72 это даёт 25 символов. Запас надёжности даёт не эта оценка, а
        ``max_words_per_cue``: даже при промахе в ширине cue остаётся коротким.
        Канал может задать точное число ключом ``max_characters_per_line``.
        """
        if self.max_characters_per_line > 0:
            return self.max_characters_per_line
        usable = max(1, self.play_res_x - self.margin_left - self.margin_right)
        glyph = max(1.0, self.font_size * 0.5)
        return max(12, int(usable / glyph))

    def to_dict(self) -> dict[str, Any]:
        return {
            "style_id": self.style_id,
            "font_family": self.font_family,
            "font_size": self.font_size,
            "alignment": self.alignment,
            "outline": self.outline,
            "outline_width": self.outline_width,
            "shadow_width": self.shadow_width,
            "margin_left": self.margin_left,
            "margin_right": self.margin_right,
            "margin_bottom": self.margin_bottom,
            "max_lines": self.max_lines,
            "max_words_per_fragment": self.max_words_per_fragment,
            "max_characters_per_line": self.effective_characters_per_line,
            "capitalization": self.capitalization,
            "safe_zone_top": self.safe_zone_top,
            "safe_zone_bottom": self.safe_zone_bottom,
            "play_res_x": self.play_res_x,
            "play_res_y": self.play_res_y,
            "save_srt": self.save_srt,
            "save_ass": self.save_ass,
            "burned_in_default": self.burned_in_default,
            "source": self.source,
            "origin": self.origin,
        }


@dataclass(frozen=True)
class SubtitlePolicy:
    """Ограничения нарезки и чтения. Отвечает за *где рвётся текст*, не за вид.

    Нарушения длительности и скорости чтения - предупреждения, а не ошибки: cue
    живёт внутри своей сцены, а длину сцены задаёт озвучка. Двигать её движок
    субтитров не имеет права, поэтому единственное, что он может, - честно сказать
    «здесь читать быстро».
    """

    max_characters_per_line: int = 22
    max_lines: int = 2
    max_words_per_cue: int = 6
    min_cue_duration_sec: float = 0.7
    max_cue_duration_sec: float = 6.0
    max_reading_speed_cps: float = 22.0
    min_gap_sec: float = 0.0
    max_gap_sec: float = 4.0
    allow_overlap: bool = False
    min_line_characters: int = 6
    text_field_priority: tuple[str, ...] = (TEXT_FIELD_NARRATION, TEXT_FIELD_ON_SCREEN)

    @property
    def max_characters_per_cue(self) -> int:
        return max(1, self.max_characters_per_line * max(1, self.max_lines))

    @classmethod
    def from_style(cls, style: SubtitleStyle, **overrides: Any) -> "SubtitlePolicy":
        """Политика, согласованная со стилем канала: одна и та же ширина строки и
        одно и то же число строк, вместо двух независимых наборов чисел."""
        policy = cls(
            max_characters_per_line=style.effective_characters_per_line,
            max_lines=max(1, style.max_lines),
            max_words_per_cue=max(1, style.max_words_per_fragment),
        )
        return replace(policy, **overrides) if overrides else policy

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_characters_per_line": self.max_characters_per_line,
            "max_characters_per_cue": self.max_characters_per_cue,
            "max_lines": self.max_lines,
            "max_words_per_cue": self.max_words_per_cue,
            "min_cue_duration_sec": self.min_cue_duration_sec,
            "max_cue_duration_sec": self.max_cue_duration_sec,
            "max_reading_speed_cps": self.max_reading_speed_cps,
            "min_gap_sec": self.min_gap_sec,
            "max_gap_sec": self.max_gap_sec,
            "allow_overlap": self.allow_overlap,
            "text_field_priority": list(self.text_field_priority),
        }


@dataclass(frozen=True)
class SubtitleSegment:
    """Кусок текста одной сцены, у которого ещё нет времени.

    ``char_start``/``char_end`` - срез исходной строки сцены, по которому
    валидатор проверяет, что ни одно слово не потеряно и не продублировано.
    """

    scene_id: str
    scene_index: int
    index: int
    text: str
    source_field: str
    char_start: int
    char_end: int
    ends_sentence: bool = False

    @property
    def weight(self) -> float:
        """Доля времени сцены, которую занимает этот кусок. Символы, а не слова:
        именно символы оказались стабильным предсказателем длительности речи
        (см. ``src.content.script_engine.text_analysis.estimate_duration_sec``)."""
        return float(max(1, len(self.text.replace("\n", " "))))


@dataclass(frozen=True)
class SubtitleCue:
    cue_id: str
    scene_id: str
    index: int
    scene_cue_index: int
    text: str
    start_sec: float
    end_sec: float
    language: str = ""
    timing_source: str = TIMING_SOURCE_UNAVAILABLE
    source_field: str = TEXT_FIELD_NARRATION
    source_char_start: int = 0
    source_char_end: int = 0
    warnings: tuple[str, ...] = ()

    @property
    def duration_sec(self) -> float:
        return self.end_sec - self.start_sec

    @property
    def lines(self) -> list[str]:
        return self.text.split("\n")

    @property
    def plain_text(self) -> str:
        return " ".join(self.text.split())

    @property
    def reading_speed_cps(self) -> float:
        duration = self.duration_sec
        if duration <= 0:
            return math.inf
        return len(self.plain_text) / duration

    def to_dict(self) -> dict[str, Any]:
        return {
            "cue_id": self.cue_id,
            "scene_id": self.scene_id,
            "index": self.index,
            "scene_cue_index": self.scene_cue_index,
            "text": self.text,
            "start_sec": round(self.start_sec, 3),
            "end_sec": round(self.end_sec, 3),
            "duration_sec": round(self.duration_sec, 3),
            "language": self.language,
            "timing_source": self.timing_source,
            "source_field": self.source_field,
            "source_char_start": self.source_char_start,
            "source_char_end": self.source_char_end,
            "warnings": list(self.warnings),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SubtitleCue":
        return cls(
            cue_id=str(data.get("cue_id") or ""),
            scene_id=str(data.get("scene_id") or ""),
            index=int(data.get("index") or 0),
            scene_cue_index=int(data.get("scene_cue_index") or 0),
            text=str(data.get("text") or ""),
            start_sec=float(data.get("start_sec") or 0.0),
            end_sec=float(data.get("end_sec") or 0.0),
            language=str(data.get("language") or ""),
            timing_source=str(data.get("timing_source") or TIMING_SOURCE_UNAVAILABLE),
            source_field=str(data.get("source_field") or TEXT_FIELD_NARRATION),
            source_char_start=int(data.get("source_char_start") or 0),
            source_char_end=int(data.get("source_char_end") or 0),
            warnings=tuple(str(item) for item in (data.get("warnings") or [])),
        )


@dataclass(frozen=True)
class SubtitleRequest:
    """Всё, из чего собираются субтитры одной локализации.

    ``voice_manifest`` передаётся как есть; границы сцен из него считает
    ``src.audio.scene_timeline.build_scene_timeline``, а не этот пакет.
    """

    script: dict[str, Any]
    localization_id: str = ""
    language: str = ""
    subtitle_language: str = ""
    voice_manifest: dict[str, Any] | None = None
    narration_path: str = ""
    narration_duration_sec: float = 0.0
    policy: SubtitlePolicy = field(default_factory=SubtitlePolicy)
    style: SubtitleStyle = field(default_factory=SubtitleStyle)
    formats: tuple[str, ...] = SUPPORTED_FORMATS
    format_id: str = "vertical_short"

    @property
    def effective_language(self) -> str:
        """Язык субтитров. Отдельный от языка озвучки намеренно: контракт
        ``ResolvedLocalization.subtitle_language`` этого не запрещает."""
        return self.subtitle_language or self.language or str(self.script.get("language") or "")


@dataclass(frozen=True)
class SubtitleResult:
    cues: tuple[SubtitleCue, ...]
    language: str
    localization_id: str
    timing_source: str
    validation: SubtitleValidationResult
    policy: SubtitlePolicy
    style: SubtitleStyle
    narration_path: str = ""
    narration_duration_sec: float = 0.0
    scene_timeline_source: str = TIMING_SOURCE_UNAVAILABLE
    script_fingerprint: str = ""
    narration_fingerprint: str = ""
    scene_count: int = 0
    formats: tuple[str, ...] = SUPPORTED_FORMATS
    warnings: tuple[str, ...] = ()

    @property
    def status(self) -> str:
        return "completed" if self.validation.ok else "needs_review"

    @property
    def total_duration_sec(self) -> float:
        return self.cues[-1].end_sec if self.cues else 0.0

    def cues_by_scene(self) -> dict[str, list[SubtitleCue]]:
        grouped: dict[str, list[SubtitleCue]] = {}
        for cue in self.cues:
            grouped.setdefault(cue.scene_id, []).append(cue)
        return grouped

    def to_segments(self) -> list[dict[str, Any]]:
        """Совместимый со всеми существующими читателями блок ``segments``
        (``{start, end, text}``), который до Q3 писал ``src/news/subtitles.py``."""
        return [
            {"start": round(cue.start_sec, 3), "end": round(cue.end_sec, 3), "text": cue.plain_text}
            for cue in self.cues
        ]


__all__ = [
    "ERR_CUE_ORDER_INVALID",
    "ERR_CUE_OUTSIDE_NARRATION",
    "ERR_CUE_OUTSIDE_SCENE",
    "ERR_CUE_OVERLAP",
    "ERR_CUE_WITHOUT_SCENE",
    "ERR_DUPLICATE_PATH",
    "ERR_DUPLICATE_SCENE_ID",
    "ERR_EMPTY_CUE_TEXT",
    "ERR_END_NOT_AFTER_START",
    "ERR_LANGUAGE_MISMATCH",
    "ERR_MISSING_LOCALIZATION",
    "ERR_MISSING_SCRIPT",
    "ERR_NARRATION_MISMATCH",
    "ERR_NEGATIVE_TIME",
    "ERR_NON_FINITE_TIME",
    "ERR_NO_CUES",
    "ERR_NO_SCENES",
    "ERR_PROTECTED_ARTIFACT",
    "ERR_TEXT_NOT_COVERED",
    "ERR_UNKNOWN_SCENE_ID",
    "ERR_UNSUPPORTED_FORMAT",
    "FORMAT_ASS",
    "FORMAT_SRT",
    "SEVERITY_ERROR",
    "SEVERITY_WARNING",
    "SUPPORTED_FORMATS",
    "TEXT_FIELD_NARRATION",
    "TEXT_FIELD_ON_SCREEN",
    "TIMING_SOURCES",
    "TIMING_SOURCE_LEGACY_PLANNED",
    "TIMING_SOURCE_PRECISION",
    "TIMING_SOURCE_SCENE_TIMELINE",
    "TIMING_SOURCE_SEGMENT",
    "TIMING_SOURCE_UNAVAILABLE",
    "TIMING_SOURCE_WORD",
    "WARN_CUE_TOO_LONG",
    "WARN_CUE_TOO_SHORT",
    "WARN_DUPLICATE_TEXT",
    "WARN_GAP_TOO_LARGE",
    "WARN_LEGACY_ARTIFACT",
    "WARN_LEGACY_TIMING",
    "WARN_LINE_TOO_LONG",
    "WARN_MISSING_SCENE_PLAN",
    "WARN_NARRATION_DURATION_UNKNOWN",
    "WARN_ON_SCREEN_TEXT_USED",
    "WARN_ORPHAN_LINE",
    "WARN_READING_SPEED",
    "WARN_TOO_MANY_LINES",
    "SubtitleCue",
    "SubtitleError",
    "SubtitleIssue",
    "SubtitlePolicy",
    "SubtitleRequest",
    "SubtitleResult",
    "SubtitleSegment",
    "SubtitleStyle",
    "SubtitleValidationResult",
    "error",
    "warning",
]
