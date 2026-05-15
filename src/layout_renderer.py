from __future__ import annotations

import math
import textwrap
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

from .image_tools import fit_cover, load_font


def render_quote_frame(
    config: dict[str, Any],
    scene: dict[str, Any],
    image_path: str | Path,
    frame_index: int,
    total_frames: int,
) -> np.ndarray:
    width, height = [int(v) for v in config["resolution"]]
    progress = frame_index / max(total_frames - 1, 1)
    frame = _background(width, height, config)
    draw = ImageDraw.Draw(frame, "RGBA")

    margin = int(width * 0.07)
    gap = int(width * 0.055)
    portrait_w = int(width * 0.36)
    portrait_h = int(height * 0.74)
    portrait_x = margin
    portrait_y = int(height * 0.14)
    text_x = portrait_x + portrait_w + gap
    text_w = width - text_x - margin

    _draw_portrait(frame, image_path, (portrait_x, portrait_y, portrait_w, portrait_h), progress)
    _draw_quote(draw, config, scene, (text_x, portrait_y, text_w, portrait_h), progress)
    _draw_letterbox(draw, width, height)
    return np.array(frame.convert("RGB"))


def _background(width: int, height: int, config: dict[str, Any]) -> Image.Image:
    base = Image.new("RGB", (width, height), config["background_color"])
    draw = ImageDraw.Draw(base)
    for y in range(height):
        t = y / max(height - 1, 1)
        r = int(7 + 16 * t)
        g = int(9 + 13 * t)
        b = int(15 + 20 * t)
        draw.line((0, y, width, y), fill=(r, g, b))

    glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.ellipse((-width * 0.2, -height * 0.35, width * 0.72, height * 1.15), fill=(110, 90, 55, 58))
    glow_draw.ellipse((width * 0.52, height * 0.12, width * 1.28, height * 1.05), fill=(20, 35, 55, 70))
    glow = glow.filter(ImageFilter.GaussianBlur(int(width * 0.075)))
    return Image.alpha_composite(base.convert("RGBA"), glow)


def _draw_portrait(frame: Image.Image, image_path: str | Path, box: tuple[int, int, int, int], progress: float) -> None:
    x, y, w, h = box
    zoom = 1.0 + 0.035 * progress
    image = Image.open(image_path)
    crop = fit_cover(image, (int(w / zoom), int(h / zoom)))
    portrait = crop.resize((w, h), Image.Resampling.LANCZOS)
    portrait = ImageEnhance.Contrast(portrait).enhance(1.06)
    portrait = ImageEnhance.Color(portrait).enhance(0.82)

    mask = Image.new("L", (w, h), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle((0, 0, w, h), radius=int(w * 0.055), fill=255)

    shadow = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.rounded_rectangle((x + 12, y + 16, x + w + 12, y + h + 16), radius=int(w * 0.055), fill=(0, 0, 0, 135))
    shadow = shadow.filter(ImageFilter.GaussianBlur(20))
    frame.alpha_composite(shadow)
    frame.paste(portrait, (x, y), mask)

    draw = ImageDraw.Draw(frame, "RGBA")
    draw.rounded_rectangle((x, y, x + w, y + h), radius=int(w * 0.055), outline=(200, 169, 106, 150), width=2)


def _draw_quote(
    draw: ImageDraw.ImageDraw,
    config: dict[str, Any],
    scene: dict[str, Any],
    box: tuple[int, int, int, int],
    progress: float,
) -> None:
    x, y, w, h = box
    font_size = int(config.get("font_size", 42))
    quote_font = load_font(config["font_path"], font_size)
    ru_font = load_font(config["font_path"], max(24, int(font_size * 0.62)))
    label_font = load_font(config["font_path"], max(18, int(font_size * 0.42)))
    author_font = load_font(config["font_path"], int(config.get("author_font_size", 24)))

    alpha = int(210 + 45 * math.sin(progress * math.pi / 2))
    accent = config.get("accent_color", "#C8A96A")
    draw.line((x, y + 4, x + int(w * 0.18), y + 4), fill=accent, width=3)
    draw.text((x, y + 30), "POWERFUL THOUGHTS", font=label_font, fill=_hex_to_rgba(config["muted_text_color"], alpha))

    quote_text = "\n".join(_wrap_text(scene["quote"], 29))
    ru_text = "\n".join(_wrap_text(scene["quote_ru"], 34))

    quote_y = y + int(h * 0.18)
    draw.text((x, quote_y), "“", font=load_font(config["font_path"], font_size + 28), fill=_hex_to_rgba(accent, 210))
    draw.multiline_text((x + 36, quote_y + 18), quote_text, font=quote_font, fill=_hex_to_rgba(config["text_color"], alpha), spacing=9)

    ru_y = quote_y + _text_block_height(draw, quote_text, quote_font, 9) + int(h * 0.09)
    draw.multiline_text((x + 38, ru_y), ru_text, font=ru_font, fill=_hex_to_rgba(config["muted_text_color"], alpha), spacing=7)

    author_y = y + h - 58
    draw.line((x, author_y - 18, x + int(w * 0.32), author_y - 18), fill=_hex_to_rgba(accent, 140), width=1)
    draw.text((x, author_y), f"- {scene['author']}", font=author_font, fill=_hex_to_rgba(config["text_color"], alpha))


def _draw_letterbox(draw: ImageDraw.ImageDraw, width: int, height: int) -> None:
    bar_h = max(18, int(height * 0.035))
    draw.rectangle((0, 0, width, bar_h), fill=(0, 0, 0, 110))
    draw.rectangle((0, height - bar_h, width, height), fill=(0, 0, 0, 110))


def _wrap_text(text: str, width: int) -> list[str]:
    return textwrap.wrap(text, width=width, break_long_words=False, replace_whitespace=False)


def _text_block_height(draw: ImageDraw.ImageDraw, text: str, font: Any, spacing: int) -> int:
    bbox = draw.multiline_textbbox((0, 0), text, font=font, spacing=spacing)
    return bbox[3] - bbox[1]


def _hex_to_rgba(value: str, alpha: int) -> tuple[int, int, int, int]:
    value = value.lstrip("#")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16), alpha
