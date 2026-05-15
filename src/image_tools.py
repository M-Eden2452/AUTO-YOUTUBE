from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .utils import project_path


def load_font(font_path: str | Path, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype(str(project_path(font_path)), size=size)
    except OSError:
        return ImageFont.load_default()


def create_person_placeholder(person: str, output_path: str | Path, config: dict[str, Any]) -> Path:
    target = project_path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    width, height = 900, 1100
    image = Image.new("RGB", (width, height), "#080A0F")
    draw = ImageDraw.Draw(image)

    for y in range(height):
        shade = int(8 + (y / height) * 28)
        draw.line((0, y, width, y), fill=(shade, shade + 2, shade + 7))

    halo = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    halo_draw = ImageDraw.Draw(halo)
    halo_draw.ellipse((120, 90, 780, 760), fill=(200, 169, 106, 42))
    halo = halo.filter(ImageFilter.GaussianBlur(90))
    image = Image.alpha_composite(image.convert("RGBA"), halo)
    draw = ImageDraw.Draw(image)

    draw.rounded_rectangle((165, 185, 735, 820), radius=44, outline=(200, 169, 106, 120), width=3)
    draw.ellipse((310, 270, 590, 550), fill=(31, 35, 45), outline=(200, 169, 106, 150), width=3)
    draw.rounded_rectangle((245, 565, 655, 790), radius=75, fill=(31, 35, 45), outline=(200, 169, 106, 120), width=3)

    title_font = load_font(config["font_path"], 58)
    subtitle_font = load_font(config["font_path"], 26)
    _center_text(draw, (0, 875, width, 950), person, title_font, "#F4EFE7")
    _center_text(draw, (0, 954, width, 1005), "portrait placeholder", subtitle_font, "#B7AA98")

    image.convert("RGB").save(target, quality=94)
    return target


def fit_cover(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    target_w, target_h = size
    src = image.convert("RGB")
    src_w, src_h = src.size
    scale = max(target_w / src_w, target_h / src_h)
    resized = src.resize((int(src_w * scale), int(src_h * scale)), Image.Resampling.LANCZOS)
    left = (resized.width - target_w) // 2
    top = (resized.height - target_h) // 2
    return resized.crop((left, top, left + target_w, top + target_h))


def _center_text(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    text: str,
    font: ImageFont.ImageFont,
    fill: str,
) -> None:
    bbox = draw.textbbox((0, 0), text, font=font)
    x = box[0] + ((box[2] - box[0]) - (bbox[2] - bbox[0])) / 2
    y = box[1] + ((box[3] - box[1]) - (bbox[3] - bbox[1])) / 2
    draw.text((x, y), text, font=font, fill=fill)
