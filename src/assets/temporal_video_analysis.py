from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageDraw

from .frame_sampling import ffprobe_media_info, sample_frames
from .perceptual_similarity import hamming_distance


DEFAULT_TEMPORAL_POSITIONS = [0.15, 0.50, 0.85]


def analyze_temporal_candidate(
    *,
    candidate_id: str,
    preview_path: str | Path,
    output_dir: str | Path,
    positions: list[float] | None = None,
) -> dict[str, Any]:
    source = Path(preview_path)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    requested_positions = list(positions or DEFAULT_TEMPORAL_POSITIONS)
    info = ffprobe_media_info(source)
    duration = float(info.get("duration_sec") or 0.0)
    frames = sample_frames(
        source,
        media_type="video",
        output_dir=output,
        sample_count=len(requested_positions),
        positions=requested_positions,
        duration_sec=duration,
    )
    frame_dicts: list[dict[str, Any]] = []
    for index, frame in enumerate(frames):
        data = frame.to_dict()
        data["requested_position"] = float(requested_positions[min(index, len(requested_positions) - 1)])
        frame_dicts.append(data)

    hashes = [str(item.get("perceptual_hash") or "") for item in frame_dicts if item.get("perceptual_hash")]
    sha_values = [str(item.get("sha256") or "") for item in frame_dicts if item.get("sha256")]
    hash_distances = _pairwise_hash_distances(hashes)
    pixel_diffs = _pairwise_pixel_differences([Path(str(item.get("local_frame_path") or "")) for item in frame_dicts])
    mean_hash_distance = round(sum(hash_distances) / len(hash_distances), 6) if hash_distances else 0.0
    mean_pixel_difference = round(sum(pixel_diffs) / len(pixel_diffs), 6) if pixel_diffs else 0.0
    temporal_independence = (
        len(frame_dicts) >= 3
        and len(set(sha_values)) >= len(frame_dicts)
        and (min(hash_distances or [0]) >= 3 or mean_pixel_difference >= 2.0)
    )
    visible_motion = bool(temporal_independence and (mean_hash_distance >= 4.0 or mean_pixel_difference >= 4.0))
    contact_sheet = output / "contact_sheet.jpg"
    _write_contact_sheet(contact_sheet, frame_dicts, title=candidate_id)
    return {
        "candidate_id": candidate_id,
        "preview_path": str(source),
        "preview_sha256": _safe_file_sha(source),
        "media_info": info,
        "duration_sec": duration,
        "positions": requested_positions,
        "frame_count": len(frame_dicts),
        "frames": frame_dicts,
        "frame_hashes": [{"sha256": item.get("sha256", ""), "perceptual_hash": item.get("perceptual_hash", "")} for item in frame_dicts],
        "perceptual_hash_distances": hash_distances,
        "mean_perceptual_hash_distance": mean_hash_distance,
        "mean_pixel_difference": mean_pixel_difference,
        "temporal_independence": temporal_independence,
        "visible_motion_evidence": visible_motion,
        "crop_suitability": _crop_suitability(frame_dicts),
        "contact_sheet_image": str(contact_sheet),
        "technical_metrics": {
            "frame_count": len(frame_dicts),
            "unique_sha256_count": len(set(sha_values)),
            "mean_perceptual_hash_distance": mean_hash_distance,
            "mean_pixel_difference": mean_pixel_difference,
        },
    }


def write_temporal_contact_sheet_html(
    analyses: list[dict[str, Any]],
    output_path: str | Path,
    *,
    project_root: str | Path | None = None,
) -> None:
    root = Path(project_root) if project_root else None
    lines = [
        "<!doctype html>",
        "<html><head><meta charset=\"utf-8\"><title>Owl Temporal Contact Sheet</title>",
        "<style>body{font-family:Arial,sans-serif;background:#10151b;color:#eef3f7;margin:24px}.candidate{border:1px solid #33404c;padding:16px;margin:0 0 20px;background:#171f27}.frames{display:flex;gap:10px;flex-wrap:wrap}.frames img,.sheet{max-width:100%;border:1px solid #40505d}code{color:#ffe082}small{color:#aebbc5}</style>",
        "</head><body><h1>Owl Temporal Contact Sheet</h1>",
    ]
    for analysis in analyses:
        lines.append("<section class=\"candidate\">")
        lines.append(f"<h2>{html.escape(str(analysis.get('candidate_id') or 'candidate'))}</h2>")
        lines.append(
            "<p>temporal_independence={independent}; visible_motion_evidence={motion}; mean_hash_distance={hash_distance}; mean_pixel_difference={pixel}</p>".format(
                independent=str(bool(analysis.get("temporal_independence"))).lower(),
                motion=str(bool(analysis.get("visible_motion_evidence"))).lower(),
                hash_distance=html.escape(str(analysis.get("mean_perceptual_hash_distance", 0))),
                pixel=html.escape(str(analysis.get("mean_pixel_difference", 0))),
            )
        )
        sheet = _html_path(str(analysis.get("contact_sheet_image") or ""), root)
        if sheet:
            lines.append(f"<img class=\"sheet\" src=\"{html.escape(sheet)}\" alt=\"contact sheet\">")
        lines.append("<div class=\"frames\">")
        for frame in analysis.get("frames", []) or []:
            frame_src = _html_path(str(frame.get("local_frame_path") or ""), root)
            if frame_src:
                lines.append(
                    "<figure><img src=\"{src}\" alt=\"frame\"><figcaption><small>{ts:.3f}s | sha <code>{sha}</code> | phash <code>{phash}</code></small></figcaption></figure>".format(
                        src=html.escape(frame_src),
                        ts=float(frame.get("actual_timestamp_sec") or 0.0),
                        sha=html.escape(str(frame.get("sha256") or "")[:12]),
                        phash=html.escape(str(frame.get("perceptual_hash") or "")),
                    )
                )
        lines.append("</div></section>")
    lines.append("</body></html>")
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write_text(target, "\n".join(lines) + "\n")


def _write_contact_sheet(path: Path, frames: list[dict[str, Any]], *, title: str) -> None:
    images: list[Image.Image] = []
    for item in frames:
        frame_path = Path(str(item.get("local_frame_path") or ""))
        if not frame_path.exists():
            continue
        with Image.open(frame_path) as image:
            thumb = image.convert("RGB")
            thumb.thumbnail((320, 220), Image.Resampling.LANCZOS)
            canvas = Image.new("RGB", (340, 280), (23, 31, 39))
            canvas.paste(thumb, ((340 - thumb.width) // 2, 18))
            draw = ImageDraw.Draw(canvas)
            label = f"{float(item.get('actual_timestamp_sec') or 0):.2f}s"
            draw.text((14, 234), label, fill=(238, 243, 247))
            draw.text((14, 254), str(item.get("perceptual_hash") or "")[:20], fill=(178, 190, 200))
            images.append(canvas)
    if not images:
        return
    width = max(340, len(images) * 340)
    sheet = Image.new("RGB", (width, 328), (16, 21, 27))
    draw = ImageDraw.Draw(sheet)
    draw.text((14, 10), title, fill=(238, 243, 247))
    for index, image in enumerate(images):
        sheet.paste(image, (index * 340, 44))
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path, format="JPEG", quality=88)


def _pairwise_hash_distances(hashes: list[str]) -> list[int]:
    distances: list[int] = []
    for first_index in range(len(hashes)):
        for second_index in range(first_index + 1, len(hashes)):
            distances.append(hamming_distance(hashes[first_index], hashes[second_index]))
    return distances


def _pairwise_pixel_differences(paths: list[Path]) -> list[float]:
    images: list[Image.Image] = []
    for path in paths:
        if not path.exists():
            continue
        with Image.open(path) as image:
            images.append(image.convert("L").resize((96, 96), Image.Resampling.BILINEAR))
    diffs: list[float] = []
    for first_index in range(len(images)):
        for second_index in range(first_index + 1, len(images)):
            diff = ImageChops.difference(images[first_index], images[second_index])
            histogram = diff.histogram()
            total = sum(value * count for value, count in enumerate(histogram))
            diffs.append(total / max(1, 96 * 96))
    return diffs


def _crop_suitability(frames: list[dict[str, Any]]) -> dict[str, Any]:
    scores = []
    for item in frames:
        width = int(item.get("width") or 0)
        height = int(item.get("height") or 0)
        if not width or not height:
            continue
        ratio = width / height
        target = 9 / 16
        resolution_score = min(1.0, (width * height) / (720 * 1280))
        ratio_score = max(0.0, 1.0 - min(1.0, abs(ratio - target) / 1.2))
        scores.append(round((resolution_score * 0.6 + ratio_score * 0.4), 6))
    score = round(sum(scores) / len(scores), 6) if scores else 0.0
    return {
        "target_aspect_ratio": "9:16",
        "heuristic_crop_suitability": score,
        "notes": "Geometry-only score; subject placement is verified separately from contact sheet and semantic review.",
    }


def _html_path(raw_path: str, root: Path | None) -> str:
    if not raw_path:
        return ""
    path = Path(raw_path)
    if root:
        try:
            return path.resolve().relative_to(root.resolve()).as_posix()
        except Exception:
            pass
    return path.as_posix()


def _safe_file_sha(path: Path) -> str:
    try:
        from .frame_sampling import sha256_file

        return sha256_file(path)
    except Exception:
        return ""


def _atomic_write_text(path: Path, text: str) -> None:
    temp = path.with_suffix(path.suffix + ".part")
    temp.write_text(text, encoding="utf-8")
    temp.replace(path)


def _atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    temp = path.with_suffix(path.suffix + ".part")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)
