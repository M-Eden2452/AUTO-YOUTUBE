from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any

import numpy as np
from moviepy import VideoClip, VideoFileClip
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from src.assets.frame_sampling import ffprobe_media_info
from src.config_resolver.paths import repository_path


DEFAULT_STORY_CARD_PRESET_PATH = repository_path(
    "config", "render_presets", "story_card_short_v1.json"
)


def load_story_card_preset(path: str | Path = DEFAULT_STORY_CARD_PRESET_PATH) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_story_card_layout(preset: dict[str, Any]) -> dict[str, Any]:
    """Build an adaptive layout for the single branded ``story_card_short_v1`` style.

    The vertical geometry is measured from the real rendered height of the top
    text, the channel block and the bottom comment. The remaining space is given
    to the central video, which is enlarged as much as possible while keeping a
    landscape aspect ratio that never crops the owl's head or eyes. There is no
    fixed ``video_y`` or fixed video height: everything follows the content.
    """
    width, height = [int(value) for value in preset["resolution"]]
    margins = dict(preset.get("safe_margins") or {})
    card = _rect(preset.get("card") or {})
    lay = dict(preset.get("layout") or {})

    text_inset = int(lay.get("text_side_inset", 44))
    video_inset = int(lay.get("video_side_inset", 12))
    top_pad = int(lay.get("top_pad", 54))
    bottom_pad = int(lay.get("bottom_pad", 44))
    gap_text_to_video = int(lay.get("gap_text_to_video", 26))
    gap_video_to_channel = int(lay.get("gap_video_to_channel", 30))
    gap_channel_to_comment = int(lay.get("gap_channel_to_comment", 28))
    min_video_aspect = float(lay.get("min_video_aspect", 1.18))
    min_video_height = int(lay.get("min_video_height", 40))
    corner_radius = int((preset.get("central_video") or {}).get("corner_radius", 20))

    text_cfg = dict(preset.get("text") or {})
    line_spacing = int(text_cfg.get("line_spacing", 12))
    font_name = str(text_cfg.get("font") or "DejaVuSans.ttf")
    top_font = _load_font(font_name, int(text_cfg.get("top_font_size", 46)))
    comment_font = _load_font(font_name, int(text_cfg.get("comment_font_size", 36)))
    username_font = _load_font(font_name, int(text_cfg.get("username_font_size", 26)))
    icon_size = int((preset.get("brand") or {}).get("icon_size", 64))

    measure_draw = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    text_left = card["x"] + text_inset
    text_max_width = card["width"] - 2 * text_inset
    top_text_y = card["y"] + top_pad
    top_text_height = _measure_wrapped_block(measure_draw, str(text_cfg.get("top") or ""), top_font, text_max_width, line_spacing)
    comment_height = _measure_wrapped_block(measure_draw, str(text_cfg.get("comment") or ""), comment_font, text_max_width, line_spacing)
    channel_height = max(icon_size, 2 + int(icon_size * 0.58) + _line_height(username_font))

    # Place from the bottom up so the comment sits close to the bottom edge.
    card_bottom = card["y"] + card["height"]
    comment_bottom = card_bottom - bottom_pad
    comment_y = comment_bottom - comment_height
    channel_bottom = comment_y - gap_channel_to_comment
    channel_icon_y = channel_bottom - channel_height
    video_bottom_limit = channel_icon_y - gap_video_to_channel

    video_top = top_text_y + top_text_height + gap_text_to_video
    available_video_height = video_bottom_limit - video_top
    video_width = card["width"] - 2 * video_inset
    head_safe_height = int(video_width / max(min_video_aspect, 0.1))
    video_height = min(available_video_height, head_safe_height)
    video_height = max(video_height, min_video_height)
    video_x = card["x"] + video_inset
    # Keep the top gap minimal; any head-safe slack falls below the video.
    video_y = video_top

    usable_height = card["height"] - top_pad - bottom_pad
    content_height = top_text_height + video_height + channel_height + comment_height
    unused_vertical_space = usable_height - content_height
    content_occupancy_ratio = round(content_height / usable_height, 4) if usable_height > 0 else 0.0
    bottom_gap = card_bottom - comment_bottom

    return {
        "resolution": {"width": width, "height": height},
        "safe_zone": {
            "left": int(margins.get("left", 0)),
            "right": int(margins.get("right", 0)),
            "top": int(margins.get("top", 0)),
            "bottom": int(margins.get("bottom", 0)),
        },
        "card": card,
        "top_text": {
            "x": text_left,
            "y": top_text_y,
            "max_width": text_max_width,
        },
        "central_video": {
            "x": video_x,
            "y": video_y,
            "width": video_width,
            "height": video_height,
            "corner_radius": corner_radius,
        },
        "channel": {
            "icon_x": text_left,
            "icon_y": channel_icon_y,
            "text_x": text_left + icon_size + 20,
            "text_y": channel_icon_y + 2,
        },
        "comment": {
            "x": text_left,
            "y": comment_y,
            "max_width": text_max_width,
        },
        "top_text_height": top_text_height,
        "video_x": video_x,
        "video_y": video_y,
        "video_width": video_width,
        "video_height": video_height,
        "brand_y": channel_icon_y,
        "comment_y": comment_y,
        "bottom_gap": bottom_gap,
        "unused_vertical_space": unused_vertical_space,
        "content_occupancy_ratio": content_occupancy_ratio,
    }


def _measure_wrapped_block(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    max_width: int,
    line_spacing: int,
) -> int:
    """Return the real height of a wrapped text block (bottom of the last line).

    Mirrors the vertical advance of ``_draw_rich_wrapped_text`` /
    ``_draw_plain_wrapped_text`` so the measured height never clips the drawing.
    """
    y = 0
    last_bottom = 0
    line_height = _line_height(font)
    for paragraph in str(text).split("\n"):
        for line in _wrap_line(draw, paragraph, font, max_width):
            last_bottom = y + line_height
            y += line_height + line_spacing
        y += max(0, line_spacing - 2)
    return last_bottom


def render_story_card_short(
    *,
    source_video: str | Path,
    output_path: str | Path,
    frame_preview_path: str | Path,
    preset: dict[str, Any] | None = None,
    selected_asset: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cfg = preset or load_story_card_preset()
    layout = build_story_card_layout(cfg)
    output = Path(output_path)
    preview = Path(frame_preview_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    preview.parent.mkdir(parents=True, exist_ok=True)
    source = Path(source_video)
    width, height = [int(value) for value in cfg["resolution"]]
    fps = int(cfg["fps"])
    duration = float(cfg["duration_sec"])
    fragment = dict(cfg.get("fragment") or {})
    fragment_start = float(fragment.get("start_sec", 0.0))
    fragment_duration = float(fragment.get("duration_sec") or duration)
    repeat_count = max(1, int(fragment.get("repeat_count") or 1))
    zoom_start = float(fragment.get("first_zoom") or 1.08)
    zoom_end = float(fragment.get("second_zoom") or 1.16)
    icon_path = output.with_name("channel_icon.png")
    _write_channel_icon(icon_path, int((cfg.get("brand") or {}).get("icon_size", 64)))

    video = VideoFileClip(str(source))

    def make_frame(t: float) -> np.ndarray:
        return _compose_frame(
            video=video,
            t=t,
            cfg=cfg,
            layout=layout,
            fragment_start=fragment_start,
            fragment_duration=fragment_duration,
            zoom_start=zoom_start,
            zoom_end=zoom_end,
            repeat_count=repeat_count,
            duration=duration,
            size=(width, height),
        )

    clip = None
    try:
        preview_frame = Image.fromarray(make_frame(min(duration - 0.05, max(0.0, duration * 0.62))))
        preview_frame.save(preview, format="PNG")
        clip = VideoClip(frame_function=make_frame, duration=duration)
        encoding = dict(cfg.get("encoding") or {})
        clip.write_videofile(
            str(output),
            fps=fps,
            codec=str(encoding.get("codec") or "libx264"),
            audio=False,
            preset=str(encoding.get("preset") or "veryfast"),
            ffmpeg_params=[
                "-crf",
                str(int(encoding.get("crf", 21))),
                "-pix_fmt",
                str(encoding.get("pix_fmt") or "yuv420p"),
                "-movflags",
                "+faststart",
            ],
            logger=None,
        )
    finally:
        if clip is not None:
            clip.close()
        video.close()

    info = ffprobe_media_info(output)
    manifest = {
        "schema_version": "story_card_render_manifest.v1",
        "status": "completed" if info.get("status") == "passed" else "failed",
        "renderer": "story_card_short_render_v1",
        "preset": cfg.get("name", ""),
        "output_path": str(output),
        "frame_preview_path": str(preview),
        "channel_icon_path": str(icon_path),
        "source_video": str(source),
        "selected_asset_id": (selected_asset or {}).get("asset_id", ""),
        "resolution": {"width": int(info.get("width") or width), "height": int(info.get("height") or height)},
        "fps": fps,
        "duration_sec": float(info.get("duration_sec") or duration),
        "central_fragment": {
            "start_sec": fragment_start,
            "duration_sec": fragment_duration,
            "repeat_count": repeat_count,
            "first_zoom": zoom_start,
            "second_zoom": zoom_end,
        },
        "audio": {"status": "silent_visual_preview", "tts_performed": False},
        "layout": layout,
    }
    return manifest


def _compose_frame(
    *,
    video: VideoFileClip,
    t: float,
    cfg: dict[str, Any],
    layout: dict[str, Any],
    fragment_start: float,
    fragment_duration: float,
    zoom_start: float,
    zoom_end: float,
    repeat_count: int,
    duration: float,
    size: tuple[int, int],
) -> np.ndarray:
    width, height = size
    phase = _pass_phase(t, duration, repeat_count)
    source_t = _source_time(fragment_start, fragment_duration, phase, video.duration or 0.0)
    raw_frame = Image.fromarray(video.get_frame(source_t)).convert("RGB")
    bg_cfg = dict(cfg.get("background") or {})
    bg_progress = t / max(duration, 0.001)
    bg_zoom = float(bg_cfg.get("zoom_start", 1.08)) + (float(bg_cfg.get("zoom_end", 1.16)) - float(bg_cfg.get("zoom_start", 1.08))) * bg_progress
    frame = _fit_cover(raw_frame, (width, height), zoom=bg_zoom)
    frame = frame.filter(ImageFilter.GaussianBlur(float(bg_cfg.get("blur_radius", 18))))
    shade = Image.new("RGBA", (width, height), (0, 0, 0, int(bg_cfg.get("darken_alpha", 160))))
    frame = Image.alpha_composite(frame.convert("RGBA"), shade)

    draw = ImageDraw.Draw(frame, "RGBA")
    card = layout["card"]
    _draw_card(draw, card, cfg)

    central = layout["central_video"]
    # Single continuous pass: gentle Ken-Burns zoom across the fragment.
    zoom = zoom_start + (zoom_end - zoom_start) * phase
    central_image = _fit_cover(raw_frame, (central["width"], central["height"]), zoom=zoom)
    _paste_rounded(frame, central_image, (central["x"], central["y"]), int(central.get("corner_radius", 18)))
    _draw_soft_video_border(draw, central)

    _draw_text_layers(draw, cfg, layout)
    return np.array(frame.convert("RGB"))


def _pass_phase(t: float, total_duration: float, repeat_count: int) -> float:
    """Progress in [0, 1] within the current pass (supports optional repeats)."""
    passes = max(1, int(repeat_count))
    pass_len = total_duration / passes if passes else total_duration
    if pass_len <= 0:
        return 0.0
    local = t - math.floor(t / pass_len) * pass_len
    return min(1.0, max(0.0, local / pass_len))


def _source_time(start: float, fragment_duration: float, phase: float, source_duration: float) -> float:
    src = start + phase * fragment_duration
    upper = max(0.0, source_duration - 0.05)
    return min(upper, max(0.0, src))


def _draw_card(draw: ImageDraw.ImageDraw, card: dict[str, int], cfg: dict[str, Any]) -> None:
    radius = int(card.get("radius", 24))
    shadow_alpha = int(card.get("shadow_alpha", 130))
    for offset, alpha in ((14, shadow_alpha // 3), (8, shadow_alpha // 2), (3, shadow_alpha)):
        draw.rounded_rectangle(
            (card["x"] + offset, card["y"] + offset, card["x"] + card["width"] + offset, card["y"] + card["height"] + offset),
            radius=radius,
            fill=(0, 0, 0, alpha),
        )
    draw.rounded_rectangle(
        (card["x"], card["y"], card["x"] + card["width"], card["y"] + card["height"]),
        radius=radius,
        fill=_rgba(str(card.get("background_color") or "#111a24"), 244),
    )


def _draw_soft_video_border(draw: ImageDraw.ImageDraw, rect: dict[str, int]) -> None:
    draw.rounded_rectangle(
        (rect["x"], rect["y"], rect["x"] + rect["width"], rect["y"] + rect["height"]),
        radius=int(rect.get("corner_radius", 18)),
        outline=(255, 255, 255, 34),
        width=2,
    )


def _draw_text_layers(draw: ImageDraw.ImageDraw, cfg: dict[str, Any], layout: dict[str, Any]) -> None:
    text_cfg = dict(cfg.get("text") or {})
    colors = dict(text_cfg.get("colors") or {})
    top_font = _load_font(str(text_cfg.get("font") or "DejaVuSans.ttf"), int(text_cfg.get("top_font_size", 38)))
    comment_font = _load_font(str(text_cfg.get("font") or "DejaVuSans.ttf"), int(text_cfg.get("comment_font_size", 30)))
    brand_font = _load_font(str(text_cfg.get("font") or "DejaVuSans.ttf"), int(text_cfg.get("brand_font_size", 34)), bold=True)
    username_font = _load_font(str(text_cfg.get("font") or "DejaVuSans.ttf"), int(text_cfg.get("username_font_size", 24)))
    line_spacing = int(text_cfg.get("line_spacing", 10))

    top = layout["top_text"]
    _draw_rich_wrapped_text(
        draw,
        str(text_cfg.get("top") or ""),
        dict(text_cfg.get("top_highlights") or {}),
        colors,
        (top["x"], top["y"]),
        top_font,
        int(top["max_width"]),
        line_spacing,
    )
    brand = dict(cfg.get("brand") or {})
    channel = layout["channel"]
    _draw_channel_icon(draw, channel["icon_x"], channel["icon_y"], int(brand.get("icon_size", 64)))
    draw.text((channel["text_x"], channel["text_y"]), str(brand.get("name") or ""), font=brand_font, fill=_rgba(colors.get("primary", "#ffffff"), 255))
    draw.text((channel["text_x"], channel["text_y"] + int(brand.get("icon_size", 64) * 0.58)), str(brand.get("username") or ""), font=username_font, fill=_rgba(colors.get("muted", "#b7c2cf"), 235))
    comment = layout["comment"]
    _draw_plain_wrapped_text(
        draw,
        str(text_cfg.get("comment") or ""),
        (comment["x"], comment["y"]),
        comment_font,
        int(comment["max_width"]),
        _rgba(colors.get("primary", "#ffffff"), 242),
        line_spacing,
    )


def _draw_rich_wrapped_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    highlights: dict[str, str],
    colors: dict[str, str],
    xy: tuple[int, int],
    font: ImageFont.FreeTypeFont,
    max_width: int,
    line_spacing: int,
) -> None:
    y = xy[1]
    for paragraph in text.split("\n"):
        for line in _wrap_line(draw, paragraph, font, max_width):
            x = xy[0]
            for segment, role in _highlight_segments(line, highlights):
                fill = _rgba(colors.get(role, colors.get("primary", "#ffffff")), 255)
                draw.text((x + 2, y + 2), segment, font=font, fill=(0, 0, 0, 120))
                draw.text((x, y), segment, font=font, fill=fill)
                x += int(draw.textlength(segment, font=font))
            y += _line_height(font) + line_spacing
        y += max(0, line_spacing - 2)


def _draw_plain_wrapped_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    xy: tuple[int, int],
    font: ImageFont.FreeTypeFont,
    max_width: int,
    fill: tuple[int, int, int, int],
    line_spacing: int,
) -> None:
    y = xy[1]
    for paragraph in text.split("\n"):
        for line in _wrap_line(draw, paragraph, font, max_width):
            draw.text((xy[0] + 2, y + 2), line, font=font, fill=(0, 0, 0, 120))
            draw.text((xy[0], y), line, font=font, fill=fill)
            y += _line_height(font) + line_spacing
        y += max(0, line_spacing - 2)


def _wrap_line(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    words = text.split(" ")
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if draw.textlength(candidate, font=font) <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _highlight_segments(line: str, highlights: dict[str, str]) -> list[tuple[str, str]]:
    ranges: list[tuple[int, int, str]] = []
    lower = line.lower()
    for role, phrase in highlights.items():
        phrase_text = str(phrase or "")
        if not phrase_text:
            continue
        start = lower.find(phrase_text.lower())
        if start >= 0:
            ranges.append((start, start + len(phrase_text), role))
    ranges.sort()
    segments: list[tuple[str, str]] = []
    cursor = 0
    for start, end, role in ranges:
        if start > cursor:
            segments.append((line[cursor:start], "primary"))
        segments.append((line[start:end], role))
        cursor = end
    if cursor < len(line):
        segments.append((line[cursor:], "primary"))
    return segments or [(line, "primary")]


def _paste_rounded(base: Image.Image, image: Image.Image, xy: tuple[int, int], radius: int) -> None:
    mask = Image.new("L", image.size, 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle((0, 0, image.width, image.height), radius=radius, fill=255)
    base.paste(image.convert("RGBA"), xy, mask)


def _fit_cover(image: Image.Image, size: tuple[int, int], *, zoom: float = 1.0) -> Image.Image:
    width, height = size
    scale = max(width / image.width, height / image.height) * max(1.0, float(zoom))
    resized = image.resize((max(1, math.ceil(image.width * scale)), max(1, math.ceil(image.height * scale))), Image.Resampling.LANCZOS)
    left = max(0, (resized.width - width) // 2)
    top = max(0, (resized.height - height) // 2)
    return resized.crop((left, top, left + width, top + height))


def _draw_channel_icon(draw: ImageDraw.ImageDraw, x: int, y: int, size: int) -> None:
    draw.ellipse((x, y, x + size, y + size), fill=(42, 115, 84, 255), outline=(142, 232, 168, 255), width=max(2, size // 18))
    pad = size * 0.18
    points = [
        (x + size * 0.22, y + size * 0.60),
        (x + size * 0.40, y + size * 0.42),
        (x + size * 0.52, y + size * 0.52),
        (x + size * 0.72, y + size * 0.28),
    ]
    draw.line(points, fill=(235, 255, 218, 255), width=max(3, size // 12), joint="curve")
    draw.arc((x + pad, y + pad, x + size - pad, y + size - pad), start=205, end=330, fill=(126, 203, 255, 230), width=max(2, size // 16))


def _write_channel_icon(path: Path, size: int) -> None:
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas, "RGBA")
    _draw_channel_icon(draw, 0, 0, size - 1)
    path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(path, format="PNG")


def _load_font(name: str, size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = []
    if bold:
        candidates.extend(["DejaVuSans-Bold.ttf", "arialbd.ttf", "C:/Windows/Fonts/arialbd.ttf"])
    candidates.extend([name, "DejaVuSans.ttf", "arial.ttf", "C:/Windows/Fonts/arial.ttf"])
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _line_height(font: ImageFont.FreeTypeFont) -> int:
    bbox = font.getbbox("Ag")
    return int(bbox[3] - bbox[1])


def _rect(data: dict[str, Any]) -> dict[str, int]:
    return {
        "x": int(data.get("x") or 0),
        "y": int(data.get("y") or 0),
        "width": int(data.get("width") or 0),
        "height": int(data.get("height") or 0),
        "radius": int(data.get("radius") or data.get("corner_radius") or 0),
        "corner_radius": int(data.get("corner_radius") or data.get("radius") or 0),
        "background_color": str(data.get("background_color") or "#111a24"),
        "shadow_alpha": int(data.get("shadow_alpha") or 0),
    }


def _rgba(value: str, alpha: int) -> tuple[int, int, int, int]:
    value = str(value or "#ffffff").lstrip("#")
    if not re.fullmatch(r"[0-9a-fA-F]{6}", value):
        value = "ffffff"
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16), int(alpha)
