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
    background_frame: np.ndarray | None = None,
) -> np.ndarray:
    width, height = [int(v) for v in config["resolution"]]
    frame = _cinematic_background(width, height, config, image_path, local_progress, scene.get("animation", "slow_zoom"), background_frame)
    draw = ImageDraw.Draw(frame, "RGBA")

    if _subtitles_only(config):
        subtitle = scene.get("subtitle_text") or scene.get("subtitle", "")
        if subtitle:
            _draw_subtitle_v2(draw, config, subtitle, width, height, _fade_alpha(local_progress))
    else:
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


def render_text_overlay(config: dict[str, Any], scene: dict[str, Any], width: int, height: int) -> Image.Image:
    frame = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(frame, "RGBA")
    if _subtitles_only(config):
        _draw_subtle_readability_gradient(draw, width, height)
        subtitle = scene.get("subtitle_text") or scene.get("subtitle", "")
        if subtitle:
            _draw_subtitle_v2(draw, config, subtitle, width, height, 238)
        frame.info["subtitle_style"] = "cinematic_documentary_v2"
        frame.info["scene_labels"] = "disabled"
    else:
        shade = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        shade_draw = ImageDraw.Draw(shade, "RGBA")
        shade_draw.rectangle((0, 0, int(width * 0.60), height), fill=(0, 0, 0, 84))
        shade_draw.rectangle((0, int(height * 0.64), width, height), fill=(0, 0, 0, 84))
        frame = Image.alpha_composite(frame, shade)
        draw = ImageDraw.Draw(frame, "RGBA")
        scene_type = scene.get("scene_type", "thought")
        if scene_type == "intro":
            _draw_intro(draw, config, scene, width, height, 0.55)
        elif scene_type == "final":
            _draw_final(draw, config, scene, width, height, 0.55)
        else:
            _draw_thought(draw, config, scene, width, height, 0.55)
    _draw_film_layers(draw, width, height)
    return frame


def _cinematic_background(
    width: int,
    height: int,
    config: dict[str, Any],
    image_path: str | Path | None,
    progress: float,
    animation: str,
    background_frame: np.ndarray | None = None,
) -> Image.Image:
    if background_frame is not None:
        image = Image.fromarray(background_frame).convert("RGB")
        bg = fit_cover(image, (width, height)).resize((width, height), Image.Resampling.LANCZOS)
        bg = _documentary_grade(bg)
    elif image_path and Path(image_path).exists():
        image = _load_image(str(image_path))
        zoom = 1.0 + 0.055 * progress
        if animation == "subtle_pan":
            zoom = 1.05
        crop = fit_cover(image, (int(width / zoom), int(height / zoom)))
        bg = crop.resize((width, height), Image.Resampling.LANCZOS)
        bg = _documentary_grade(bg)
    else:
        bg = Image.new("RGB", (width, height), config.get("background_color", "#090B10"))

    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for y in range(height):
        alpha = int(18 + 66 * (y / max(height - 1, 1)))
        draw.line((0, y, width, y), fill=(4, 6, 10, alpha))
    draw.rectangle((0, 0, width, height), outline=(0, 0, 0, 42), width=max(8, int(width * 0.010)))
    overlay = overlay.filter(ImageFilter.GaussianBlur(8))
    return Image.alpha_composite(bg.convert("RGBA"), overlay)


def _documentary_grade(image: Image.Image) -> Image.Image:
    graded = ImageEnhance.Color(image).enhance(0.84)
    graded = ImageEnhance.Contrast(graded).enhance(1.10)
    graded = ImageEnhance.Brightness(graded).enhance(0.78)
    tone = Image.new("RGBA", graded.size, (8, 32, 34, 26))
    return Image.alpha_composite(graded.convert("RGBA"), tone).convert("RGB")


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
    subtitle = scene.get("subtitle_text") or scene.get("subtitle", "")
    draw.multiline_text(
        (left, top + int(height * 0.25)),
        "\n".join(textwrap.wrap(subtitle, width=76, break_long_words=False)),
        font=subtitle_font,
        fill=_rgba(config["muted_text_color"], alpha),
        spacing=7,
    )


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
    subtitle = scene.get("subtitle_text", "")
    if subtitle:
        _draw_subtitle(draw, config, subtitle, left, int(height * 0.70), width, alpha)
    else:
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
    footer = scene.get("subtitle_text") or "Проверить цитаты. Проверить авторские права. Добавить озвучку."
    footer_bbox = draw.textbbox((0, 0), footer, font=small_font)
    if scene.get("subtitle_text"):
        wrapped = "\n".join(textwrap.wrap(footer, width=86, break_long_words=False))
        footer_bbox = draw.multiline_textbbox((0, 0), wrapped, font=small_font, spacing=7)
        draw.multiline_text(
            ((width - (footer_bbox[2] - footer_bbox[0])) / 2, height * 0.72),
            wrapped,
            font=small_font,
            fill=_rgba(config["muted_text_color"], alpha),
            spacing=7,
            align="center",
        )
    else:
        draw.text(((width - (footer_bbox[2] - footer_bbox[0])) / 2, height * 0.76), footer, font=small_font, fill=_rgba(config["muted_text_color"], alpha))


def _draw_subtitle(draw: ImageDraw.ImageDraw, config: dict[str, Any], subtitle: str, left: int, top: int, width: int, alpha: int) -> None:
    subtitle_font = load_font(config["font_path"], max(24, int(width * 0.020)))
    wrapped = "\n".join(textwrap.wrap(subtitle, width=72 if width >= 1600 else 58, break_long_words=False))
    bbox = draw.multiline_textbbox((0, 0), wrapped, font=subtitle_font, spacing=7)
    pad_x = 18
    pad_y = 12
    draw.rounded_rectangle(
        (left - pad_x, top - pad_y, left + (bbox[2] - bbox[0]) + pad_x, top + (bbox[3] - bbox[1]) + pad_y),
        radius=8,
        fill=(0, 0, 0, min(alpha, 132)),
    )
    draw.multiline_text((left, top), wrapped, font=subtitle_font, fill=_rgba(config["text_color"], alpha), spacing=7)


def _draw_subtitle_v2(draw: ImageDraw.ImageDraw, config: dict[str, Any], subtitle: str, width: int, height: int, alpha: int) -> None:
    subtitle_cfg = config.get("subtitle_style", {})
    font_size = int(subtitle_cfg.get("font_size", max(28, min(38, width * 0.028))))
    subtitle_font = load_font(config["font_path"], font_size)
    wrap_chars = int(subtitle_cfg.get("wrap_chars", 54 if width < 1600 else 68))
    wrapped = "\n".join(textwrap.wrap(subtitle, width=wrap_chars, break_long_words=False))
    spacing = int(subtitle_cfg.get("spacing", 8))
    bbox = draw.multiline_textbbox((0, 0), wrapped, font=subtitle_font, spacing=spacing)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    pad_x = int(subtitle_cfg.get("padding_x", 18))
    pad_y = int(subtitle_cfg.get("padding_y", 10))
    x = int((width - text_w) / 2)
    y = int(height * float(subtitle_cfg.get("y_ratio", 0.765)))
    draw.rounded_rectangle(
        (x - pad_x, y - pad_y, x + text_w + pad_x, y + text_h + pad_y),
        radius=int(subtitle_cfg.get("radius", 9)),
        fill=(0, 0, 0, min(alpha, int(subtitle_cfg.get("background_alpha", 118)))),
    )
    draw.multiline_text((x + 1, y + 1), wrapped, font=subtitle_font, fill=(0, 0, 0, min(alpha, 160)), spacing=spacing, align="center")
    draw.multiline_text((x, y), wrapped, font=subtitle_font, fill=_rgba(config.get("text_color", "#F4EFE7"), alpha), spacing=spacing, align="center")


def _draw_subtle_readability_gradient(draw: ImageDraw.ImageDraw, width: int, height: int) -> None:
    top = int(height * 0.58)
    for y in range(top, height):
        alpha = int(8 + 58 * ((y - top) / max(height - top, 1)))
        draw.line((0, y, width, y), fill=(0, 0, 0, alpha))


def _draw_film_layers(draw: ImageDraw.ImageDraw, width: int, height: int) -> None:
    bar_h = int(height * 0.045)
    draw.rectangle((0, 0, width, bar_h), fill=(0, 0, 0, 92))
    draw.rectangle((0, height - bar_h, width, height), fill=(0, 0, 0, 92))
    draw.rectangle((0, 0, width, height), outline=(0, 0, 0, 58), width=max(5, int(width * 0.006)))


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


def _subtitles_only(config: dict[str, Any]) -> bool:
    return bool(config.get("documentary_subtitles_only") or config.get("channel_id") == "survival")


@lru_cache(maxsize=64)
def _load_image(path: str) -> Image.Image:
    return Image.open(path).convert("RGB")
