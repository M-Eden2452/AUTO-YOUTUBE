from __future__ import annotations

import math
import textwrap
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

from .image_tools import fit_cover, load_font


def render_documentary_frame(
    config: dict[str, Any],
    scene: dict[str, Any],
    image_path: str | Path | None,
    local_progress: float,
) -> np.ndarray:
    width, height = [int(v) for v in config["resolution"]]
    frame = _cinematic_background(width, height, config, image_path, local_progress, scene.get("animation", "slow_zoom"))
    draw = ImageDraw.Draw(frame, "RGBA")

    scene_type = scene.get("scene_type", "thought")
    if scene_type == "intro":
        _draw_intro(draw, config, scene, width, height, local_progress)
    elif scene_type == "final":
        _draw_final(draw, config, scene, width, height, local_progress)
    else:
        _draw_thought(draw, config, scene, width, height, local_progress)

    _draw_film_layers(draw, width, height)
    return np.array(frame.convert("RGB"))


def render_quote_frame(
    config: dict[str, Any],
    scene: dict[str, Any],
    image_path: str | Path,
    frame_index: int,
    total_frames: int,
) -> np.ndarray:
    progress = frame_index / max(total_frames - 1, 1)
    return render_documentary_frame(config, scene, image_path, progress)


def _cinematic_background(
    width: int,
    height: int,
    config: dict[str, Any],
    image_path: str | Path | None,
    progress: float,
    animation: str,
) -> Image.Image:
    if image_path and Path(image_path).exists():
        image = _load_image(str(image_path))
        zoom = 1.0 + 0.055 * progress
        if animation == "subtle_pan":
            zoom = 1.05
        crop = fit_cover(image, (int(width / zoom), int(height / zoom)))
        bg = crop.resize((width, height), Image.Resampling.LANCZOS)
        bg = ImageEnhance.Color(bg).enhance(0.62)
        bg = ImageEnhance.Contrast(bg).enhance(1.15)
        bg = ImageEnhance.Brightness(bg).enhance(0.48)
    else:
        bg = Image.new("RGB", (width, height), config.get("background_color", "#090B10"))

    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for y in range(height):
        alpha = int(95 + 105 * (y / max(height - 1, 1)))
        draw.line((0, y, width, y), fill=(4, 6, 10, alpha))
    draw.rectangle((0, 0, int(width * 0.58), height), fill=(0, 0, 0, 72))
    draw.ellipse((-width * 0.22, -height * 0.35, width * 0.8, height * 1.2), fill=(130, 98, 45, 32))
    overlay = overlay.filter(ImageFilter.GaussianBlur(12))
    return Image.alpha_composite(bg.convert("RGBA"), overlay)


def _draw_intro(draw: ImageDraw.ImageDraw, config: dict[str, Any], scene: dict[str, Any], width: int, height: int, progress: float) -> None:
    title_font = load_font(config["font_path"], int(width * 0.052))
    subtitle_font = load_font(config["font_path"], int(width * 0.018))
    label_font = load_font(config["font_path"], int(width * 0.014))
    accent = config.get("accent_color", "#C8A96A")
    alpha = _fade_alpha(progress)

    left = int(width * 0.11)
    top = int(height * 0.32)
    draw.text((left, top - 78), "JORDAN PETERSON", font=label_font, fill=_rgba(config["muted_text_color"], alpha))
    draw.line((left, top - 36, left + int(width * 0.18), top - 36), fill=_rgba(accent, alpha), width=3)
    title = "\n".join(textwrap.wrap(scene.get("title") or scene.get("screen_text", ""), width=28))
    draw.multiline_text((left, top), title, font=title_font, fill=_rgba(config["text_color"], alpha), spacing=12)
    draw.text((left, top + int(height * 0.25)), scene.get("subtitle", ""), font=subtitle_font, fill=_rgba(config["muted_text_color"], alpha))


def _draw_thought(draw: ImageDraw.ImageDraw, config: dict[str, Any], scene: dict[str, Any], width: int, height: int, progress: float) -> None:
    font_size = int(config.get("font_size", 58))
    text_font = load_font(config["font_path"], font_size)
    meta_font = load_font(config["font_path"], max(23, int(font_size * 0.36)))
    small_font = load_font(config["font_path"], max(19, int(font_size * 0.28)))
    accent = config.get("accent_color", "#C8A96A")
    alpha = _fade_alpha(progress)
    left = int(width * 0.105)
    top = int(height * 0.28)
    max_chars = 31 if width >= 1600 else 27

    content_label = _content_label(scene.get("content_type", "idea"))
    draw.text((left, top - 70), content_label, font=small_font, fill=_rgba(config["muted_text_color"], alpha))
    draw.line((left, top - 30, left + int(width * 0.15), top - 30), fill=_rgba(accent, alpha), width=3)
    lines = "\n".join(textwrap.wrap(scene.get("screen_text") or scene.get("quote_ru", ""), width=max_chars, break_long_words=False))
    draw.multiline_text((left, top), lines, font=text_font, fill=_rgba(config["text_color"], alpha), spacing=13)

    source_y = int(height * 0.78)
    draw.text((left, source_y), scene.get("person", "Jordan Peterson"), font=meta_font, fill=_rgba(config["muted_text_color"], alpha))
    draw.text((left, source_y + 42), scene.get("source_note", ""), font=small_font, fill=_rgba("#8D8373", min(alpha, 175)))


def _draw_final(draw: ImageDraw.ImageDraw, config: dict[str, Any], scene: dict[str, Any], width: int, height: int, progress: float) -> None:
    text_font = load_font(config["font_path"], int(width * 0.04))
    small_font = load_font(config["font_path"], int(width * 0.017))
    alpha = _fade_alpha(progress)
    text = "\n".join(textwrap.wrap(scene.get("screen_text", ""), width=34, break_long_words=False))
    bbox = draw.multiline_textbbox((0, 0), text, font=text_font, spacing=12)
    x = (width - (bbox[2] - bbox[0])) / 2
    y = height * 0.37
    draw.multiline_text((x, y), text, font=text_font, fill=_rgba(config["text_color"], alpha), spacing=12, align="center")
    footer = "Проверить цитаты. Проверить авторские права. Добавить озвучку."
    footer_bbox = draw.textbbox((0, 0), footer, font=small_font)
    draw.text(((width - (footer_bbox[2] - footer_bbox[0])) / 2, height * 0.76), footer, font=small_font, fill=_rgba(config["muted_text_color"], alpha))


def _draw_film_layers(draw: ImageDraw.ImageDraw, width: int, height: int) -> None:
    bar_h = int(height * 0.065)
    draw.rectangle((0, 0, width, bar_h), fill=(0, 0, 0, 150))
    draw.rectangle((0, height - bar_h, width, height), fill=(0, 0, 0, 150))
    draw.rectangle((0, 0, width, height), outline=(0, 0, 0, 120), width=int(width * 0.015))


def _fade_alpha(progress: float) -> int:
    fade_in = min(1.0, progress / 0.18)
    fade_out = min(1.0, (1.0 - progress) / 0.14)
    return int(255 * max(0.25, min(fade_in, fade_out)))


def _content_label(content_type: str) -> str:
    labels = {
        "quote": "БЛИЗКАЯ ЦИТАТА",
        "idea": "ПЕРЕСКАЗ ИДЕИ",
        "narration_card": "МЫСЛЬ ДЛЯ ЭКРАНА",
    }
    return labels.get(content_type, "МЫСЛЬ")


def _rgba(value: str, alpha: int) -> tuple[int, int, int, int]:
    value = value.lstrip("#")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16), alpha


@lru_cache(maxsize=64)
def _load_image(path: str) -> Image.Image:
    return Image.open(path).convert("RGB")
