from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from pathlib import Path
from statistics import mean
from typing import Any

from PIL import Image, ImageFilter, ImageOps, ImageStat

from .frame_sampling import SampledFrame


@dataclass
class TechnicalVisualMetrics:
    analysis_status: str = "passed"
    analysis_error: str = ""
    width: int = 0
    height: int = 0
    aspect_ratio: float = 0.0
    orientation: str = "unknown"
    duration_sec: float = 0.0
    file_size_bytes: int = 0
    brightness_mean: float = 0.0
    brightness_distribution: dict[str, float] = field(default_factory=dict)
    contrast: float = 0.0
    dark_frame_score: float = 0.0
    near_white_frame_score: float = 0.0
    sharpness_heuristic: float = 0.0
    detail_density: float = 0.0
    visual_activity: float = 0.0
    frozen_frame_ratio: float = 0.0
    repeated_frame_ratio: float = 0.0
    unique_frame_ratio: float = 0.0
    crop_suitability: dict[str, dict[str, Any]] = field(default_factory=dict)
    technical_quality_score: float = 0.0
    score_breakdown: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


def analyze_frame_metrics(path: str | Path) -> TechnicalVisualMetrics:
    target = Path(path)
    try:
        with Image.open(target) as original:
            image = original.convert("RGB")
        gray = ImageOps.grayscale(image)
        width, height = image.size
        stat = ImageStat.Stat(gray)
        brightness = float(stat.mean[0])
        contrast = float(stat.stddev[0])
        histogram = gray.histogram()
        total = max(1, width * height)
        dark = sum(histogram[:26]) / total
        white = sum(histogram[245:]) / total
        edges = gray.filter(ImageFilter.FIND_EDGES)
        edge_hist = edges.histogram()
        edge_pixels = sum(edge_hist[24:])
        detail_density = edge_pixels / total
        sharpness = _local_difference_score(gray)
        score_breakdown = _score_frame(width, height, brightness, contrast, sharpness, detail_density, crop_score=0.0)
        return TechnicalVisualMetrics(
            width=width,
            height=height,
            aspect_ratio=width / height if height else 0.0,
            orientation=_orientation(width, height),
            file_size_bytes=target.stat().st_size if target.exists() else 0,
            brightness_mean=brightness,
            brightness_distribution=_brightness_distribution(histogram, total),
            contrast=contrast,
            dark_frame_score=dark,
            near_white_frame_score=white,
            sharpness_heuristic=sharpness,
            detail_density=detail_density,
            technical_quality_score=sum(score_breakdown.values()),
            score_breakdown=score_breakdown,
        )
    except Exception as exc:
        return TechnicalVisualMetrics(analysis_status="failed", analysis_error=str(exc), technical_quality_score=0.0)


def analyze_video_frame_set(frames: list[SampledFrame]) -> TechnicalVisualMetrics:
    extracted = [frame for frame in frames if frame.extraction_status == "extracted" and frame.local_frame_path]
    if not extracted:
        return TechnicalVisualMetrics(analysis_status="failed", analysis_error="no_extracted_frames", technical_quality_score=0.0)
    per_frame = [analyze_frame_metrics(frame.local_frame_path) for frame in extracted]
    hashes = [frame.sha256 for frame in extracted if frame.sha256]
    unique = len(set(hashes)) if hashes else 0
    total = len(extracted)
    repeated_ratio = 1.0 - (unique / total) if total else 0.0
    frozen_ratio = 1.0 if unique <= 1 and total > 1 else repeated_ratio
    unique_ratio = unique / total if total else 0.0
    activity = _activity_from_hashes([frame.perceptual_hash for frame in extracted if frame.perceptual_hash])
    first = per_frame[0]
    brightness = mean(metric.brightness_mean for metric in per_frame)
    contrast = mean(metric.contrast for metric in per_frame)
    sharpness = mean(metric.sharpness_heuristic for metric in per_frame)
    detail = mean(metric.detail_density for metric in per_frame)
    crop = first.crop_suitability
    score_breakdown = _score_frame(first.width, first.height, brightness, contrast, sharpness, detail, crop_score=0.0, activity=activity)
    return TechnicalVisualMetrics(
        width=first.width,
        height=first.height,
        aspect_ratio=first.aspect_ratio,
        orientation=first.orientation,
        brightness_mean=brightness,
        brightness_distribution=first.brightness_distribution,
        contrast=contrast,
        dark_frame_score=mean(metric.dark_frame_score for metric in per_frame),
        near_white_frame_score=mean(metric.near_white_frame_score for metric in per_frame),
        sharpness_heuristic=sharpness,
        detail_density=detail,
        visual_activity=activity,
        frozen_frame_ratio=frozen_ratio,
        repeated_frame_ratio=repeated_ratio,
        unique_frame_ratio=unique_ratio,
        crop_suitability=crop,
        score_breakdown=score_breakdown,
        technical_quality_score=sum(score_breakdown.values()) - (frozen_ratio * 12.0),
    )


def analyze_visual_technical_quality(
    media_path: str | Path,
    *,
    media_type: str,
    sampled_frames: list[SampledFrame],
    target_aspect_ratios: list[str] | None = None,
    duration_sec: float = 0.0,
) -> TechnicalVisualMetrics:
    target = Path(media_path)
    try:
        metrics = analyze_frame_metrics(sampled_frames[0].local_frame_path) if media_type == "image" else analyze_video_frame_set(sampled_frames)
        metrics.duration_sec = float(duration_sec or metrics.duration_sec)
        metrics.file_size_bytes = target.stat().st_size if target.exists() else metrics.file_size_bytes
        crop_scores: dict[str, dict[str, Any]] = {}
        for aspect in target_aspect_ratios or ["9:16", "16:9", "1:1"]:
            crop_scores[aspect] = estimate_crop_suitability(sampled_frames[0].local_frame_path, aspect)
        metrics.crop_suitability = crop_scores
        crop_score = max((item.get("heuristic_crop_suitability", 0.0) for item in crop_scores.values()), default=0.0)
        metrics.score_breakdown = _score_frame(
            metrics.width,
            metrics.height,
            metrics.brightness_mean,
            metrics.contrast,
            metrics.sharpness_heuristic,
            metrics.detail_density,
            crop_score=crop_score,
            activity=metrics.visual_activity,
        )
        metrics.technical_quality_score = max(0.0, min(100.0, sum(metrics.score_breakdown.values()) - metrics.frozen_frame_ratio * 12.0))
        return metrics
    except Exception as exc:
        return TechnicalVisualMetrics(analysis_status="failed", analysis_error=str(exc), technical_quality_score=0.0)


def estimate_crop_suitability(path: str | Path, target_aspect_ratio: str) -> dict[str, Any]:
    try:
        with Image.open(path) as original:
            image = original.convert("L")
        width, height = image.size
        target_ratio = _aspect_value(target_aspect_ratio)
        if not width or not height or target_ratio <= 0:
            raise ValueError("invalid_dimensions_or_aspect")
        source_ratio = width / height
        if source_ratio > target_ratio:
            crop_height = height
            crop_width = int(height * target_ratio)
        else:
            crop_width = width
            crop_height = int(width / target_ratio)
        crop_width = max(1, min(width, crop_width))
        crop_height = max(1, min(height, crop_height))
        retained_area = (crop_width * crop_height) / max(1, width * height)
        left = (width - crop_width) // 2
        top = (height - crop_height) // 2
        center = image.crop((left, top, left + crop_width, top + crop_height))
        center_detail = _detail_density(center)
        full_detail = max(0.0001, _detail_density(image))
        detail_retention = max(0.0, min(1.0, (center_detail / full_detail) * retained_area))
        empty_area = _empty_area_score(center)
        min_resolution = min(crop_width / 1080.0, crop_height / 1080.0)
        score = (
            retained_area * 52.0
            + detail_retention * 26.0
            + min(1.0, min_resolution) * 14.0
            + (1.0 - empty_area) * 8.0
        )
        score = max(0.0, min(100.0, score))
        return {
            "target_aspect_ratio": target_aspect_ratio,
            "heuristic_crop_suitability": score,
            "estimated_detail_retention": detail_retention,
            "center_information_density": center_detail,
            "estimated_crop_area_retention": retained_area,
            "estimated_detail_loss": max(0.0, 1.0 - detail_retention),
            "large_empty_area_score": empty_area,
            "estimated_post_crop_resolution": {"width": crop_width, "height": crop_height},
            "explanation": "center crop heuristic based on aspect retention, local detail density and post-crop resolution",
        }
    except Exception as exc:
        return {
            "target_aspect_ratio": target_aspect_ratio,
            "heuristic_crop_suitability": 0.0,
            "estimated_detail_retention": 0.0,
            "center_information_density": 0.0,
            "estimated_crop_area_retention": 0.0,
            "estimated_detail_loss": 1.0,
            "large_empty_area_score": 1.0,
            "estimated_post_crop_resolution": {"width": 0, "height": 0},
            "explanation": f"crop heuristic failed: {exc}",
        }


def _brightness_distribution(histogram: list[int], total: int) -> dict[str, float]:
    return {
        "dark": sum(histogram[:64]) / total,
        "mid": sum(histogram[64:192]) / total,
        "bright": sum(histogram[192:]) / total,
    }


def _local_difference_score(gray: Image.Image) -> float:
    small = gray.resize((min(gray.width, 256), min(gray.height, 256)), Image.Resampling.LANCZOS)
    pixels = list(small.getdata())
    width, height = small.size
    if width < 2 or height < 2:
        return 0.0
    total = 0
    count = 0
    for y in range(height - 1):
        row = y * width
        next_row = (y + 1) * width
        for x in range(width - 1):
            value = pixels[row + x]
            total += abs(value - pixels[row + x + 1])
            total += abs(value - pixels[next_row + x])
            count += 2
    return total / max(1, count)


def _detail_density(image: Image.Image) -> float:
    edges = image.filter(ImageFilter.FIND_EDGES)
    hist = edges.histogram()
    return sum(hist[24:]) / max(1, image.width * image.height)


def _empty_area_score(image: Image.Image) -> float:
    stat = ImageStat.Stat(image)
    return 1.0 if stat.stddev[0] < 4.0 else max(0.0, min(1.0, 1.0 - (stat.stddev[0] / 64.0)))


def _activity_from_hashes(hashes: list[str]) -> float:
    if len(hashes) < 2:
        return 0.0
    from .perceptual_similarity import hamming_distance

    distances = [hamming_distance(hashes[index], hashes[index + 1]) for index in range(len(hashes) - 1)]
    return max(0.0, min(1.0, mean(distances) / 64.0))


def _score_frame(
    width: int,
    height: int,
    brightness: float,
    contrast: float,
    sharpness: float,
    detail: float,
    *,
    crop_score: float,
    activity: float = 0.0,
) -> dict[str, float]:
    brightness_score = max(0.0, 16.0 - abs(brightness - 128.0) / 8.0)
    contrast_score = min(18.0, contrast / 4.0)
    sharpness_score = min(18.0, sharpness / 3.0)
    detail_score = min(14.0, detail * 55.0)
    resolution_score = min(14.0, (width * height) / (1920 * 1080) * 14.0)
    activity_score = min(8.0, activity * 8.0)
    crop_component = min(12.0, crop_score / 100.0 * 12.0)
    return {
        "brightness": brightness_score,
        "contrast": contrast_score,
        "sharpness": sharpness_score,
        "detail_density": detail_score,
        "resolution": resolution_score,
        "activity": activity_score,
        "crop": crop_component,
    }


def _aspect_value(value: str) -> float:
    if ":" in value:
        left, right = value.split(":", 1)
        return float(left) / max(0.0001, float(right))
    return float(value)


def _orientation(width: int, height: int) -> str:
    if not width or not height:
        return "unknown"
    if height > width:
        return "vertical"
    if width > height:
        return "horizontal"
    return "square"
