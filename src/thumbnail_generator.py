from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

from .image_tools import fit_cover, load_font
from .utils import project_path


def create_thumbnail(config: dict[str, Any], asset_plan: dict[str, Any], output_path: str | Path | None = None) -> Path:
    target = project_path(output_path or config.get("thumbnail_path", "outputs/thumbnail.png"))
    target.parent.mkdir(parents=True, exist_ok=True)

    width, height = 1280, 720
    background = _load_background(asset_plan, width, height)
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")
    draw.rectangle((0, 0, width, height), fill=(0, 0, 0, 108))
    draw.rectangle((0, 0, int(width * 0.62), height), fill=(0, 0, 0, 126))
    draw.rectangle((0, int(height * 0.74), width, height), fill=(0, 0, 0, 156))
    background = Image.alpha_composite(background.convert("RGBA"), overlay)

    draw = ImageDraw.Draw(background, "RGBA")
    task = config.get("video_task", {})
    main_text = task.get("thumbnail_text", config.get("topic", "VIDEO"))
    small_text = "РЕАЛЬНАЯ ИСТОРИЯ" if config.get("channel_id") == "survival" else config.get("channel_config", {}).get("channel_name", "")
    font_path = config.get("font_path", "C:/Windows/Fonts/arial.ttf")
    main_font = load_font(font_path, 82)
    small_font = load_font(font_path, 34)
    accent_font = load_font(font_path, 28)

    left = 70
    top = 250
    draw.text((left, top - 70), small_text, font=small_font, fill=(224, 232, 226, 242))
    draw.line((left, top - 22, left + 390, top - 22), fill=(180, 210, 186, 232), width=5)

    lines = _wrap_thumbnail_text(main_text)
    y = top
    for line in lines:
        stroke = 4
        draw.text((left, y), line, font=main_font, fill=(246, 247, 242, 255), stroke_width=stroke, stroke_fill=(0, 0, 0, 215))
        y += 88

    draw.text((left, height - 84), "LANSA FLIGHT 508  |  AMAZON RAINFOREST", font=accent_font, fill=(192, 205, 198, 218))
    draw.rectangle((0, 0, width, height), outline=(0, 0, 0, 210), width=18)
    background.convert("RGB").save(target, "PNG")
    return target


def _load_background(asset_plan: dict[str, Any], width: int, height: int) -> Image.Image:
    candidates = [
        asset.get("path", "")
        for asset in asset_plan.get("scene_assets", [])
        if asset.get("path")
    ]
    image_path = next((project_path(path) for path in candidates if project_path(path).exists()), None)
    if image_path:
        image = Image.open(image_path).convert("RGB")
        image = fit_cover(image, (width, height))
        image = ImageEnhance.Color(image).enhance(0.58)
        image = ImageEnhance.Contrast(image).enhance(1.25)
        image = ImageEnhance.Brightness(image).enhance(0.62)
        return image.filter(ImageFilter.GaussianBlur(1.2))

    image = Image.new("RGB", (width, height), "#07100C")
    draw = ImageDraw.Draw(image)
    for y in range(height):
        green = int(18 + 30 * (1 - y / max(height - 1, 1)))
        blue = int(20 + 35 * (y / max(height - 1, 1)))
        draw.line((0, y, width, y), fill=(4, green, blue))
    for x in range(0, width, 34):
        draw.line((x, 0, x - 180, height), fill=(12, 42, 31), width=9)
    return image.filter(ImageFilter.GaussianBlur(2.0))


def _wrap_thumbnail_text(value: str) -> list[str]:
    words = value.split()
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        candidate = " ".join([*current, word])
        if len(candidate) > 13 and current:
            lines.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(" ".join(current))
    return lines[:3]
