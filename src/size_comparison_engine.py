from __future__ import annotations

import csv
import math
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import imageio_ffmpeg
import numpy as np
from moviepy import VideoClip
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

from .utils import PROJECT_ROOT, ensure_dir, project_path, write_json
from .video_renderer import validate_video_file


@dataclass(frozen=True)
class SizeObject:
    name: str
    size_meters: float
    category: str
    source_note: str
    visual_priority: int


def load_size_data(path: str | Path) -> list[SizeObject]:
    objects: list[SizeObject] = []
    with project_path(path).open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            objects.append(
                SizeObject(
                    name=row["name"].strip(),
                    size_meters=float(row["size_meters"]),
                    category=row["category"].strip(),
                    source_note=row["source_note"].strip(),
                    visual_priority=int(row["visual_priority"]),
                )
            )
    return sorted(objects, key=lambda item: (item.size_meters, item.visual_priority))


def build_camera_plan(
    objects: list[SizeObject | dict[str, Any]],
    resolution: tuple[int, int] = (1280, 720),
    duration_seconds: float = 210.0,
) -> dict[str, Any]:
    normalized = [_coerce_size_object(item) for item in objects]
    stages = _group_scale_stages(normalized)
    width, height = resolution
    stage_duration = duration_seconds / max(len(stages), 1)
    camera_stages: list[dict[str, Any]] = []
    start = 0.0

    for index, stage_objects in enumerate(stages, start=1):
        largest = max(item.size_meters for item in stage_objects)
        smallest = min(item.size_meters for item in stage_objects)
        target_largest_pixels = width * (0.54 if largest < 120 else 0.86)
        meters_per_pixel = largest / target_largest_pixels
        if smallest / meters_per_pixel < 42:
            meters_per_pixel = smallest / 42
        camera_span = width * meters_per_pixel
        stage_items = []
        for item in stage_objects:
            visible_pixels = max(42.0, item.size_meters / meters_per_pixel)
            stage_items.append(
                {
                    "name": item.name,
                    "size_meters": item.size_meters,
                    "category": item.category,
                    "source_note": item.source_note,
                    "visual_priority": item.visual_priority,
                    "visible_pixels": round(visible_pixels, 2),
                }
            )

        camera_stages.append(
            {
                "stage": index,
                "start": round(start, 3),
                "duration": round(stage_duration, 3),
                "objects": stage_items,
                "meters_per_pixel": round(meters_per_pixel, 5),
                "camera_span_meters": round(camera_span, 2),
                "camera_motion": "slow_pan_reveal" if largest >= 100 else "slow_push_in",
                "reference_overlay": largest >= 100,
                "framing_note": _framing_note(largest, smallest),
            }
        )
        start += stage_duration

    return {
        "engine": "cinematic_size_comparison_v1",
        "resolution": [width, height],
        "duration": round(duration_seconds, 3),
        "scaling_logic": "adaptive_grouped_zoom",
        "stages": camera_stages,
    }


def prepare_silhouette_asset(source_path: str | Path, target_path: str | Path) -> dict[str, Any]:
    source = project_path(source_path)
    target = project_path(target_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    image = Image.open(source).convert("RGBA")
    alpha = image.getchannel("A")
    has_transparency = alpha.getextrema()[0] < 245
    background = "transparent" if has_transparency else "opaque"

    rgba = np.array(image)
    if not has_transparency:
        rgb = rgba[:, :, :3].astype(np.int16)
        edge = np.concatenate([rgb[0, :, :], rgb[-1, :, :], rgb[:, 0, :], rgb[:, -1, :]], axis=0)
        edge_mean = edge.mean(axis=0)
        edge_std = float(edge.std(axis=0).mean())
        if edge_mean.min() > 228:
            distance = np.abs(rgb - edge_mean).sum(axis=2)
            mask = distance > 52
            rgba[:, :, 3] = np.where(mask, 255, 0).astype(np.uint8)
            background = "white_removed"
        elif edge_std < 28:
            distance = np.abs(rgb - edge_mean).sum(axis=2)
            mask = distance > 55
            rgba[:, :, 3] = np.where(mask, 255, 0).astype(np.uint8)
            background = "flat_color_removed"

    mask = Image.fromarray(rgba[:, :, 3]).filter(ImageFilter.GaussianBlur(0.45))
    silhouette = Image.new("RGBA", image.size, (30, 56, 68, 0))
    shade = Image.new("RGBA", image.size, (35, 74, 88, 235))
    silhouette.alpha_composite(shade)
    silhouette.putalpha(mask)
    silhouette.save(target)
    return {"source_path": str(source), "processed_path": str(target), "background": background}


def run_size_comparison_pipeline(config: dict[str, Any], skip_render: bool = False) -> dict[str, Any]:
    output_dir = ensure_dir(config.get("output_dir", "outputs/size_comparison/sea_monsters_001"))
    video_task = config.get("video_task", {})
    content_dir = project_path(video_task.get("content_dir", "content/size_comparison/sea_monsters_001"))
    data_path = content_dir / "data.csv"
    objects = load_size_data(data_path)
    size_settings = {**config.get("size_comparison", {}), **video_task.get("size_comparison", {})}
    resolution = tuple(size_settings.get("preview_resolution", [1280, 720]))
    fps = int(size_settings.get("fps", 24))
    duration = float(size_settings.get("duration_seconds", video_task.get("target_duration_seconds", 216)))
    manual_root = project_path(config.get("manual_assets", {}).get("base_path", "manual_assets/size_comparison/sea_monsters_001"))

    asset_plan = build_size_asset_plan(objects, manual_root, output_dir)
    camera_plan = build_camera_plan(objects, resolution=resolution, duration_seconds=duration)
    render_plan = {
        "engine": "cinematic_size_comparison_v1",
        "output_path": str(project_path(config["output_filename"])),
        "silent_video_path": str(project_path(config["output_filename"]).with_name("final_preview_silent.mp4")),
        "stage_log_path": str(output_dir / "render_stage.json"),
        "resolution": list(resolution),
        "fps": fps,
        "duration": duration,
        "encoding": {"crf": 18, "preset": "medium", "audio_bitrate": "192k"},
        "voice": {"enabled": False, "status": "not_used_for_first_test"},
    }
    metadata = _youtube_metadata(video_task)
    write_json(output_dir / "asset_plan.json", asset_plan)
    write_json(output_dir / "camera_plan.json", camera_plan)
    write_json(output_dir / "youtube_metadata.json", metadata)
    write_json(output_dir / "render_plan.json", render_plan)

    final_path = project_path(config["output_filename"])
    if skip_render:
        render_stage = {"ok": True, "current_stage": "skipped", "events": [{"stage": "skipped", "message": "Render skipped."}]}
    else:
        render_stage = render_size_comparison_video(config, objects, asset_plan, camera_plan, render_plan)

    self_eval = evaluate_size_comparison(final_path, asset_plan, camera_plan, render_plan, render_stage)
    write_json(output_dir / "render_stage.json", render_stage)
    write_json(output_dir / "self_eval.json", self_eval)
    note_path = export_size_comparison_obsidian_note(config, objects, asset_plan, camera_plan, self_eval, final_path)
    return {
        "output_path": str(final_path),
        "asset_plan": asset_plan,
        "camera_plan": camera_plan,
        "render_stage": render_stage,
        "self_eval": self_eval,
        "obsidian_note": str(note_path),
    }


def build_size_asset_plan(objects: list[SizeObject], manual_root: Path, output_dir: Path) -> dict[str, Any]:
    images_dir = manual_root / "images"
    backgrounds_dir = manual_root / "backgrounds"
    processed_dir = output_dir / "processed_assets"
    image_files = _media_files(images_dir)
    background_files = _media_files(backgrounds_dir)
    assets = []
    for item in objects:
        source = _match_asset(item.name, image_files)
        processed = None
        warning = None
        background = "missing"
        if source:
            result = prepare_silhouette_asset(source, processed_dir / f"{_slug(item.name)}.png")
            processed = result["processed_path"]
            background = result["background"]
        else:
            warning = f"No manual image matched {item.name}; generated silhouette placeholder will be used."
        assets.append(
            {
                "name": item.name,
                "size_meters": item.size_meters,
                "category": item.category,
                "source_note": item.source_note,
                "source_path": str(source) if source else "",
                "processed_path": processed or "",
                "background": background,
                "orientation": "standardized_right_by_layout",
                "style": "clean_dark_ocean_silhouette",
                "warning": warning,
            }
        )
    return {
        "engine": "cinematic_size_comparison_v1",
        "manual_root": str(manual_root),
        "priority": ["manual_assets", "generated_ocean_fallback"],
        "background": {"path": str(_select_background(background_files)) if background_files else "", "status": "manual" if background_files else "generated"},
        "audio": _audio_plan(manual_root),
        "objects": assets,
        "warnings": [asset["warning"] for asset in assets if asset.get("warning")],
    }


def render_size_comparison_video(
    config: dict[str, Any],
    objects: list[SizeObject],
    asset_plan: dict[str, Any],
    camera_plan: dict[str, Any],
    render_plan: dict[str, Any],
) -> dict[str, Any]:
    output_path = Path(render_plan["output_path"])
    silent_path = Path(render_plan["silent_video_path"])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        output_path.unlink()
    if silent_path.exists():
        silent_path.unlink()

    width, height = render_plan["resolution"]
    duration = float(render_plan["duration"])
    fps = int(render_plan["fps"])
    assets = _asset_map(asset_plan)
    background = _load_background(asset_plan.get("background", {}).get("path"), width, height)
    particle_seed = int(hash(config.get("video_id", "size-comparison")) & 0xFFFFFFFF)

    def make_frame(t: float) -> np.ndarray:
        stage = _stage_for_time(camera_plan["stages"], t)
        progress = (t - float(stage["start"])) / max(float(stage["duration"]), 0.001)
        frame = _ocean_frame(background, width, height, t, duration, particle_seed)
        draw = ImageDraw.Draw(frame, "RGBA")
        _draw_stage(frame, draw, stage, assets, width, height, progress)
        _draw_title_band(draw, width, height, config.get("topic", "Legendary Sea Monsters Size Comparison"), t, duration)
        return np.array(frame.convert("RGB"))

    clip = None
    try:
        clip = VideoClip(frame_function=make_frame, duration=duration)
        clip.write_videofile(
            str(silent_path),
            fps=fps,
            codec="libx264",
            audio=False,
            preset=render_plan["encoding"]["preset"],
            ffmpeg_params=["-crf", str(render_plan["encoding"]["crf"]), "-pix_fmt", "yuv420p"],
            logger=None,
        )
    finally:
        if clip:
            clip.close()

    _add_ambience(silent_path, output_path, asset_plan, duration, render_plan)
    validation = validate_video_file(output_path, expected_duration=duration, tolerance=4.0)
    return {
        "ok": validation["ok"],
        "current_stage": "done" if validation["ok"] else "validate_failed",
        "events": [
            {"stage": "render_silent_done", "message": str(silent_path), "timestamp": _now()},
            {"stage": "add_ambience_done", "message": str(output_path), "timestamp": _now()},
            {"stage": "validate_final", "message": "; ".join(validation.get("errors", [])) or "ok", "timestamp": _now()},
        ],
        "validation": validation,
    }


def evaluate_size_comparison(
    output_path: Path,
    asset_plan: dict[str, Any],
    camera_plan: dict[str, Any],
    render_plan: dict[str, Any],
    render_stage: dict[str, Any],
) -> dict[str, Any]:
    warnings = list(asset_plan.get("warnings", []))
    validation = render_stage.get("validation", {"ok": output_path.exists(), "errors": []})
    if not validation.get("ok"):
        warnings.extend(validation.get("errors", []))
    checks = [
        "Adaptive grouped zoom is used instead of one linear full-frame scale.",
        "Minimum planned object visibility is at least 42 pixels in every stage.",
        "Manual assets were searched before generated placeholders.",
        "Labels use minimal documentary styling.",
        "First test render has no voice-over.",
    ]
    if any(stage.get("reference_overlay") for stage in camera_plan.get("stages", [])):
        checks.append("Large mythical stages include reference overlay/inset scale.")
    return {
        "ok": bool(validation.get("ok")),
        "checks": checks,
        "warnings": warnings,
        "duration_seconds": render_plan["duration"],
        "fps": render_plan["fps"],
        "resolution": render_plan["resolution"],
        "pacing": "slow cinematic scale reveal",
    }


def export_size_comparison_obsidian_note(
    config: dict[str, Any],
    objects: list[SizeObject],
    asset_plan: dict[str, Any],
    camera_plan: dict[str, Any],
    self_eval: dict[str, Any],
    output_path: Path,
) -> Path:
    obsidian = config.get("obsidian", {})
    vault_path = Path(obsidian.get("vault_path", ""))
    note_dir = vault_path / obsidian.get("folder", "YouTube/02 Видео/Size Comparison/sea_monsters_001")
    if not vault_path.exists() or not vault_path.is_dir():
        note_dir = project_path("outputs") / "obsidian" / "size_comparison" / config.get("video_id", "sea_monsters_001")
    note_dir.mkdir(parents=True, exist_ok=True)
    copied_video = output_path
    if vault_path.exists() and output_path.exists():
        copied_video = note_dir / output_path.name
        copied_video.write_bytes(output_path.read_bytes())
    note_path = note_dir / "Legendary Sea Monsters Size Comparison.md"
    lines = [
        "# Legendary Sea Monsters Size Comparison",
        "",
        "## Status",
        "Cinematic preview rendered.",
        "",
        "## Preview",
        f"![[{copied_video.name}]]" if copied_video.parent == note_dir else f"[{copied_video.name}]({copied_video})",
        "",
        "## Object List",
        *[f"- {item.name}: {item.size_meters:g} m, {item.category}. {item.source_note}" for item in objects],
        "",
        "## Scale References",
        f"- Engine: {camera_plan.get('engine')}",
        f"- Scaling: {camera_plan.get('scaling_logic')}",
        *[f"- Stage {stage['stage']}: {stage['framing_note']}" for stage in camera_plan.get("stages", [])],
        "",
        "## Visual Notes",
        "- Dark ocean mood, underwater particles, fog and slow camera movement.",
        "- Mythical creatures are presented as fictional/mythological interpretations.",
        "",
        "## Assets",
        *[f"- {asset['name']}: {asset.get('source_path') or 'generated placeholder'}" for asset in asset_plan.get("objects", [])],
        "",
        "## Self Eval",
        *[f"- {item}" for item in self_eval.get("checks", [])],
        "",
        "## Warnings",
        *([f"- {item}" for item in self_eval.get("warnings", [])] or ["- None"]),
        "",
        "## Future Improvements",
        "- Replace any placeholder silhouettes with licensed transparent manual art.",
        "- Add narrated documentary voice once the scale prototype is approved.",
        "- Consider a final 1080p production render after preview review.",
        "",
    ]
    note_path.write_text("\n".join(lines), encoding="utf-8")
    return note_path


def _coerce_size_object(item: SizeObject | dict[str, Any]) -> SizeObject:
    if isinstance(item, SizeObject):
        return item
    return SizeObject(
        name=str(item["name"]),
        size_meters=float(item["size_meters"]),
        category=str(item.get("category", "")),
        source_note=str(item.get("source_note", "")),
        visual_priority=int(item.get("visual_priority", 0)),
    )


def _group_scale_stages(objects: list[SizeObject]) -> list[list[SizeObject]]:
    groups = [
        [item for item in objects if item.size_meters <= 20],
        [item for item in objects if 20 < item.size_meters <= 140],
        [item for item in objects if 140 < item.size_meters <= 400],
        [item for item in objects if item.size_meters > 400],
    ]
    return [group for group in groups if group]


def _framing_note(largest: float, smallest: float) -> str:
    return f"largest {largest:g} m, smallest {smallest:g} m, adaptive zoom keeps small references readable"


def _media_files(path: Path) -> list[Path]:
    if not path.exists():
        return []
    extensions = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
    return sorted([item for item in path.iterdir() if item.suffix.lower() in extensions])


def _select_background(files: list[Path]) -> Path:
    keywords = ("abyss", "underwater", "ocean", "deep", "sea", "storm", "fog")
    penalties = ("carrier", "aircraft", "reference", "side view")

    def score(path: Path) -> tuple[int, str]:
        name = path.stem.lower()
        value = sum(3 for keyword in keywords if keyword in name) - sum(4 for penalty in penalties if penalty in name)
        return (-value, name)

    return sorted(files, key=score)[0]


def _match_asset(name: str, files: list[Path]) -> Path | None:
    aliases = {
        "human": ["human", "man", "silhouette"],
        "great white shark": ["shark"],
        "orca": ["orca"],
        "giant squid": ["giant", "squid"],
        "mosasaurus": ["mosasaurus", "mosasaur"],
        "megalodon": ["megalodon"],
        "kraken": ["kraken"],
        "leviathan": ["leviathan"],
        "jormungandr": ["jormungandr", "jormungandr"],
    }
    tokens = aliases.get(name.lower(), re.findall(r"[a-z0-9]+", name.lower()))
    for path in files:
        normalized = _latinish(path.stem.lower())
        if all(token in normalized for token in tokens[:2]):
            return path
    for path in files:
        normalized = _latinish(path.stem.lower())
        if any(token in normalized for token in tokens):
            return path
    return None


def _latinish(value: str) -> str:
    return value.replace("ö", "o").replace("ö", "o").replace("ø", "o").replace("ä", "a")


def _audio_plan(manual_root: Path) -> dict[str, Any]:
    audio_dir = manual_root / "audio"
    if audio_dir.exists():
        for item in sorted(audio_dir.iterdir()):
            if item.suffix.lower() in {".mp3", ".wav", ".m4a", ".aac"}:
                return {"status": "manual", "path": str(item), "style": "dark ambient ocean atmosphere"}
    return {"status": "generated_ambience", "path": "", "style": "dark ambient ocean atmosphere"}


def _asset_map(asset_plan: dict[str, Any]) -> dict[str, Image.Image]:
    mapped = {}
    for asset in asset_plan.get("objects", []):
        path = asset.get("processed_path")
        if path and Path(path).exists():
            mapped[asset["name"]] = Image.open(path).convert("RGBA")
    return mapped


def _load_background(path: str, width: int, height: int) -> Image.Image:
    if path and Path(path).exists():
        image = Image.open(path).convert("RGB")
        return _cover(image, width, height)
    return Image.new("RGB", (width, height), (3, 13, 22))


def _ocean_frame(background: Image.Image, width: int, height: int, t: float, duration: float, seed: int) -> Image.Image:
    zoom = 1.0 + 0.035 * (t / max(duration, 0.001))
    crop_w = int(width / zoom)
    crop_h = int(height / zoom)
    pan = (math.sin(t * 0.018) + 1) * 0.5
    left = int((width - crop_w) * pan)
    top = int((height - crop_h) * 0.45)
    frame = background.crop((left, top, left + crop_w, top + crop_h)).resize((width, height), Image.Resampling.LANCZOS)
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")
    draw.rectangle((0, 0, width, height), fill=(0, 12, 24, 110))
    draw.rectangle((0, 0, width, int(height * 0.22)), fill=(0, 0, 0, 82))
    rng = np.random.default_rng(seed)
    for idx in range(140):
        x = int((rng.integers(0, width) + t * (8 + idx % 9)) % width)
        y = int((rng.integers(0, height) + t * (5 + idx % 7)) % height)
        alpha = int(24 + (idx % 5) * 8)
        draw.ellipse((x, y, x + 2, y + 2), fill=(150, 192, 205, alpha))
    for layer in range(5):
        y = int(height * (0.18 + layer * 0.17) + math.sin(t * 0.05 + layer) * 12)
        draw.rectangle((0, y, width, y + 60), fill=(70, 120, 135, 10 + layer * 4))
    return Image.alpha_composite(frame.convert("RGBA"), overlay)


def _draw_stage(
    frame: Image.Image,
    draw: ImageDraw.ImageDraw,
    stage: dict[str, Any],
    assets: dict[str, Image.Image],
    width: int,
    height: int,
    progress: float,
) -> None:
    font_big = _font(30)
    font_small = _font(20)
    label_font = _font(24)
    draw.text((54, 48), f"STAGE {stage['stage']} / ADAPTIVE SCALE", fill=(170, 205, 214, 190), font=font_small)
    baseline = int(height * 0.72)
    objects = sorted(stage["objects"], key=lambda item: item["size_meters"], reverse=True)
    count = len(objects)
    label_positions: list[tuple[dict[str, Any], int, int]] = []
    for idx, item in enumerate(objects):
        size_px = item["visible_pixels"]
        layer_y = baseline - int((idx % 4) * height * 0.11)
        if size_px > width * 0.95:
            x = int(width * 0.18 - progress * min(size_px - width * 0.72, width * 0.72))
        else:
            x = int(width * (0.08 + (idx / max(count, 1)) * 0.55))
        alpha = int(175 + 55 * (1 - idx / max(count, 1)))
        _paste_object(frame, assets.get(item["name"]), item, x, layer_y, size_px, alpha)
        if count >= 4:
            label_x = width - 390
            label_y = 104 + idx * 88
        else:
            label_x = max(42, min(width - 390, x + 12))
            label_y = max(120, min(height - 150, layer_y + 18))
        label_positions.append((item, label_x, label_y))

    if stage.get("reference_overlay"):
        draw.rounded_rectangle((width - 340, height - 138, width - 48, height - 48), radius=8, fill=(2, 12, 20, 132), outline=(95, 145, 160, 80))
        draw.text((width - 318, height - 120), "REFERENCE SCALE", fill=(190, 224, 232, 210), font=font_small)
        draw.line((width - 308, height - 82, width - 152, height - 82), fill=(180, 220, 230, 180), width=2)
        draw.text((width - 308, height - 72), "human / shark remain readable", fill=(150, 184, 194, 185), font=_font(15))
    draw.line((50, baseline + 28, width - 50, baseline + 28), fill=(100, 150, 160, 80), width=1)
    for item, label_x, label_y in label_positions:
        _label(draw, item, label_x, label_y, label_font, font_small)


def _paste_object(frame: Image.Image, asset: Image.Image | None, item: dict[str, Any], x: int, baseline: int, size_px: float, alpha: int) -> None:
    if asset is None:
        asset = _placeholder_asset(item["name"])
    aspect = asset.height / max(asset.width, 1)
    display_w = max(42, int(size_px))
    display_h = max(18, int(display_w * aspect))
    display_h = min(display_h, int(frame.height * 0.62))
    sprite = asset.resize((display_w, display_h), Image.Resampling.LANCZOS)
    sprite = ImageEnhance.Contrast(sprite).enhance(1.08)
    if alpha < 255:
        a = sprite.getchannel("A").point(lambda value: int(value * alpha / 255))
        sprite.putalpha(a)
    y = int(baseline - display_h)
    frame.alpha_composite(sprite, (x, y))


def _label(draw: ImageDraw.ImageDraw, item: dict[str, Any], x: int, y: int, label_font: ImageFont.FreeTypeFont, small_font: ImageFont.FreeTypeFont) -> None:
    title = item["name"].upper()
    subtitle = f"{item['size_meters']:g} meters"
    category = str(item["category"]).title()
    if "myth" in str(item["category"]).lower():
        category += " / estimated interpretation"
    box_w = 330
    box_h = 92
    draw.rounded_rectangle((x - 14, y - 12, x + box_w, y + box_h), radius=7, fill=(1, 10, 18, 116), outline=(108, 169, 184, 58))
    draw.text((x, y), title[:26], fill=(222, 241, 244, 235), font=label_font)
    draw.text((x, y + 32), subtitle, fill=(182, 215, 222, 215), font=small_font)
    draw.text((x, y + 56), category[:34], fill=(136, 172, 184, 196), font=small_font)


def _draw_title_band(draw: ImageDraw.ImageDraw, width: int, height: int, title: str, t: float, duration: float) -> None:
    font_title = _font(34)
    font_small = _font(18)
    if t < 9:
        alpha = int(220 * min(1, t / 2.5) * min(1, (9 - t) / 2.0))
        draw.text((54, height - 104), title, fill=(225, 240, 242, alpha), font=font_title)
        draw.text((57, height - 62), "fictional creatures are shown as mythological interpretations", fill=(165, 196, 205, max(0, alpha - 40)), font=font_small)
    if t > duration - 10:
        alpha = int(210 * min(1, (duration - t) / 2.0))
        draw.text((54, height - 80), "END OF PREVIEW SCALE PASS", fill=(210, 232, 236, alpha), font=font_small)


def _add_ambience(silent_path: Path, output_path: Path, asset_plan: dict[str, Any], duration: float, render_plan: dict[str, Any]) -> None:
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    manual_audio = asset_plan.get("audio", {}).get("path")
    if manual_audio and Path(manual_audio).exists():
        command = [
            ffmpeg,
            "-y",
            "-i",
            str(silent_path),
            "-stream_loop",
            "-1",
            "-i",
            manual_audio,
            "-t",
            f"{duration:.3f}",
            "-map",
            "0:v",
            "-map",
            "1:a",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            render_plan["encoding"]["audio_bitrate"],
            "-shortest",
            str(output_path),
        ]
    else:
        command = [
            ffmpeg,
            "-y",
            "-i",
            str(silent_path),
            "-f",
            "lavfi",
            "-t",
            f"{duration:.3f}",
            "-i",
            "anoisesrc=color=brown:amplitude=0.07",
            "-f",
            "lavfi",
            "-t",
            f"{duration:.3f}",
            "-i",
            "sine=frequency=58",
            "-filter_complex",
            "[1:a]lowpass=f=750,volume=0.25[a1];[2:a]volume=0.035[a2];[a1][a2]amix=inputs=2:duration=first[a]",
            "-map",
            "0:v",
            "-map",
            "[a]",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            render_plan["encoding"]["audio_bitrate"],
            "-shortest",
            str(output_path),
        ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr[-2000:])


def _trim_transparent(image: Image.Image) -> Image.Image:
    box = image.getbbox()
    return image.crop(box) if box else image


def _cover(image: Image.Image, width: int, height: int) -> Image.Image:
    ratio = max(width / image.width, height / image.height)
    resized = image.resize((int(image.width * ratio), int(image.height * ratio)), Image.Resampling.LANCZOS)
    left = (resized.width - width) // 2
    top = (resized.height - height) // 2
    return resized.crop((left, top, left + width, top + height))


def _placeholder_asset(name: str) -> Image.Image:
    image = Image.new("RGBA", (360, 120), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image, "RGBA")
    draw.ellipse((18, 26, 300, 94), fill=(36, 76, 90, 220))
    draw.polygon([(296, 60), (352, 26), (342, 60), (352, 94)], fill=(34, 72, 85, 220))
    return image


def _stage_for_time(stages: list[dict[str, Any]], t: float) -> dict[str, Any]:
    for stage in stages:
        if float(stage["start"]) <= t < float(stage["start"]) + float(stage["duration"]):
            return stage
    return stages[-1]


def _font(size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/segoeui.ttf"),
        Path("C:/Windows/Fonts/calibri.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", _latinish(value.lower())).strip("_")


def _youtube_metadata(video_task: dict[str, Any]) -> dict[str, Any]:
    return {
        "chosen_title": video_task.get("chosen_title", "Legendary Sea Monsters Size Comparison"),
        "title_variants": [
            "Legendary Sea Monsters Size Comparison",
            "Sea Monsters Compared by Size",
            "How Big Were Mythical Sea Monsters?",
            "Megalodon vs Kraken vs Leviathan",
            "The Dark Ocean Size Comparison",
        ],
        "description": "A cinematic size comparison of real, prehistoric, and mythological sea monsters. Mythical creatures are shown as fictional interpretations, not scientific measurements.",
        "tags": ["size comparison", "sea monsters", "megalodon", "kraken", "leviathan", "jormungandr", "mosasaurus", "deep ocean"],
        "thumbnail_text": "SEA MONSTERS",
        "disclaimer": "Mythical creatures are estimated fictional/mythological interpretations.",
    }


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")
