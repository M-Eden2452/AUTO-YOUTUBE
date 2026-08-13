"""Стиль субтитров канала: ``config/channels/<id>/subtitle_style.json``.

До Q3 этот файл читал только legacy ``src/channel_loader.py``; новый рендер
субтитров его не открывал (зафиксировано в
``docs/handoff/PRODUCT_VISION_AND_ROADMAP.md`` как незакрытая часть этапа E2).
Здесь он подключается - **без второго реестра стилей**: список того, что вообще
существует, по-прежнему один, ``src.content_creation.capabilities.list_subtitle_styles``,
а `config_resolver` остаётся источником ответа «включены ли субтитры и какой стиль».
Этот модуль только превращает уже существующий файл канала в ``SubtitleStyle``.

Осознанное ограничение: ``safe_zone_bottom`` в поле канала (320) не превращается в
ASS ``MarginV`` (260 у проверенного рендера). Q3 - про единый контракт и правильный
тайминг, а не про смену дизайна; сдвинуть уже принятый пользователем кадр молча
нельзя. Отступ меняется только явным ``margin_v``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import SubtitleStyle

CHANNEL_STYLE_FILENAME = "subtitle_style.json"

# Ключи файла канала → поля SubtitleStyle. Всё, что в файле есть, но здесь не
# перечислено, сознательно игнорируется рендером и просто показывается в explain.
_DIRECT_KEYS: dict[str, str] = {
    "font": "font_family",
    "font_family": "font_family",
    "font_size": "font_size",
    "alignment": "alignment",
    "outline": "outline",
    "outline_width": "outline_width",
    "shadow_width": "shadow_width",
    "max_lines": "max_lines",
    "max_words_per_fragment": "max_words_per_fragment",
    "max_characters_per_line": "max_characters_per_line",
    "capitalization": "capitalization",
    "safe_zone_top": "safe_zone_top",
    "safe_zone_bottom": "safe_zone_bottom",
    "margin_v": "margin_bottom",
    "margin_left": "margin_left",
    "margin_right": "margin_right",
    "save_srt": "save_srt",
    "save_ass": "save_ass",
    "burned_in_default": "burned_in_default",
}

_INT_FIELDS = {
    "font_size",
    "outline_width",
    "shadow_width",
    "max_lines",
    "max_words_per_fragment",
    "max_characters_per_line",
    "safe_zone_top",
    "safe_zone_bottom",
    "margin_bottom",
    "margin_left",
    "margin_right",
}
_BOOL_FIELDS = {"outline", "save_srt", "save_ass", "burned_in_default"}


def _channels_root(channels_dir: str | Path | None) -> Path:
    if channels_dir is None:
        from src.config_resolver.paths import resolve_application_paths

        return resolve_application_paths().channels_root
    return Path(channels_dir)


def channel_style_path(channel_id: str, *, channels_dir: str | Path | None = None) -> Path:
    return _channels_root(channels_dir) / channel_id / CHANNEL_STYLE_FILENAME


def read_channel_style_file(
    channel_id: str, *, channels_dir: str | Path | None = None
) -> dict[str, Any]:
    """Содержимое файла канала или ``{}``. Никогда не бросает: канал без файла -
    это норма, а не ошибка (у большинства каналов его нет)."""
    path = channel_style_path(channel_id, channels_dir=channels_dir)
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def resolve_subtitle_style(
    *,
    channel_id: str = "",
    style_id: str = "documentary",
    resolution: dict[str, Any] | None = None,
    channels_dir: str | Path | None = None,
    overrides: dict[str, Any] | None = None,
) -> SubtitleStyle:
    """``SubtitleStyle`` для канала.

    Порядок: значения по умолчанию (= сегодняшний зашитый ASS-заголовок) →
    ``subtitle_style.json`` канала → разрешение из visual plan → явные overrides.
    Канал без файла получает ровно прежний вид.
    """
    values: dict[str, Any] = {"style_id": style_id or "documentary"}
    raw = read_channel_style_file(channel_id, channels_dir=channels_dir) if channel_id else {}
    for key, target in _DIRECT_KEYS.items():
        if key not in raw or raw[key] is None:
            continue
        values[target] = raw[key]
    if resolution:
        width = resolution.get("width")
        height = resolution.get("height")
        if width:
            values["play_res_x"] = width
        if height:
            values["play_res_y"] = height
    if overrides:
        values.update({key: value for key, value in overrides.items() if value is not None})

    cleaned: dict[str, Any] = {}
    for key, value in values.items():
        if key in _INT_FIELDS:
            try:
                cleaned[key] = int(value)
            except (TypeError, ValueError):
                continue
        elif key in _BOOL_FIELDS:
            cleaned[key] = bool(value)
        else:
            cleaned[key] = value
    cleaned["source"] = "channel_subtitle_style" if raw else "default"
    cleaned["origin"] = str(channel_style_path(channel_id, channels_dir=channels_dir)) if raw else ""
    # outline=false в файле канала означает «без обводки», а не «обводка нулевой
    # толщины по умолчанию»: иначе флаг ничего бы не делал.
    if cleaned.get("outline") is False:
        cleaned.setdefault("outline_width", 0)
        cleaned["outline_width"] = 0
    return SubtitleStyle(**cleaned)


__all__ = ["CHANNEL_STYLE_FILENAME", "channel_style_path", "read_channel_style_file", "resolve_subtitle_style"]
