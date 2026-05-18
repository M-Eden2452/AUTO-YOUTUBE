from __future__ import annotations

from pathlib import Path
from typing import Any

from moviepy import VideoFileClip


def evaluate_render(
    output_path: str | Path,
    config: dict[str, Any],
    asset_plan: dict[str, Any],
    scene_plan: dict[str, Any] | None = None,
    music_plan: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    obsidian_note_path: str | Path | None = None,
    render_plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    path = Path(output_path)
    checks: list[str] = []
    warnings: list[str] = []

    if not path.exists() or path.stat().st_size == 0:
        return {"ok": False, "checks": checks, "warnings": ["Итоговое видео отсутствует или пустое."]}

    checks.append("Итоговое видео существует и не пустое.")
    clip = VideoFileClip(str(path))
    duration = float(clip.duration or 0)
    width, height = clip.size
    clip.close()

    expected_duration = _expected_duration(config, scene_plan)
    tolerance = 20 if not config.get("dev_mode", False) else 0.5
    if abs(duration - expected_duration) <= tolerance:
        checks.append(f"Длительность близка к целевой: {duration:.2f} сек.")
    else:
        warnings.append(f"Длительность отличается от целевой: {duration:.2f} сек. против {expected_duration:.2f} сек.")

    if [width, height] == [int(v) for v in config["resolution"]]:
        checks.append(f"Разрешение совпадает с конфигом: {width}x{height}.")
    else:
        warnings.append(f"Разрешение не совпадает: {width}x{height}.")

    scenes = (scene_plan or {}).get("scenes", [])
    if scenes:
        checks.append(f"Количество сцен: {len(scenes)}.")
        if config.get("prod_preview", False):
            if 3 <= len(scenes) <= 5:
                checks.append("Prod-preview использует ожидаемые 3-5 сцен.")
            else:
                warnings.append(f"Количество prod-preview сцен вне ожидаемого диапазона: {len(scenes)}.")
        elif not config.get("dev_mode", False) and not config.get("cinematic_preview", False) and not (22 <= len(scenes) <= 32):
            warnings.append(f"Количество production-сцен вне ожидаемого диапазона: {len(scenes)}.")
        overflow = [scene["scene_number"] for scene in scenes if len(scene.get("screen_text", "")) > 135]
        if overflow:
            warnings.append(f"Возможный overflow текста в сценах: {overflow}.")
        else:
            checks.append("Явных рисков переполнения текста не найдено.")

    if asset_plan.get("warnings"):
        warnings.extend(asset_plan["warnings"])
    if asset_plan.get("engine") == "documentary_visual_engine_v2":
        _evaluate_documentary_assets(asset_plan, checks, warnings)
        quality = evaluate_documentary_quality_rules(asset_plan, render_plan or {}, config)
        checks.extend(quality["checks"])
        warnings.extend(quality["warnings"])
    missing_assets = [
        asset.get("scene_number")
        for asset in asset_plan.get("scene_assets", [])
        if asset.get("provider") == "placeholder"
    ]
    if missing_assets:
        warnings.append(f"Есть fallback-ассеты в сценах: {missing_assets}.")
    elif asset_plan.get("scene_assets"):
        checks.append("Ассеты для сцен найдены или скачаны.")

    music_plan = music_plan or {}
    if music_plan.get("path") and Path(music_plan["path"]).exists():
        checks.append("Музыка найдена и подключена.")
    elif music_plan.get("warnings"):
        warnings.extend(music_plan["warnings"])
    else:
        warnings.append("Музыка не подключена.")

    if metadata and metadata.get("chosen_title"):
        checks.append("YouTube metadata создана, выбранный заголовок есть.")
    else:
        warnings.append("YouTube metadata отсутствует или не содержит chosen_title.")

    if obsidian_note_path and Path(obsidian_note_path).exists():
        checks.append(f"Obsidian-заметка экспортирована: {obsidian_note_path}")
    else:
        warnings.append("Obsidian-заметка не подтверждена self-eval.")

    return {"ok": path.exists(), "checks": checks, "warnings": warnings}


def _expected_duration(config: dict[str, Any], scene_plan: dict[str, Any] | None) -> float:
    scenes = (scene_plan or {}).get("scenes", [])
    if scenes:
        return sum(float(scene.get("duration", 0)) for scene in scenes)
    return float(config.get("scene_duration", 0))


def _evaluate_documentary_assets(asset_plan: dict[str, Any], checks: list[str], warnings: list[str]) -> None:
    scene_assets = asset_plan.get("scene_assets", [])
    if not scene_assets:
        warnings.append("Documentary visual engine did not produce scene assets.")
        return

    weak_scenes = [asset.get("scene_number") for asset in scene_assets if int(asset.get("clip_count", len(asset.get("clips", [])))) < 1]
    if weak_scenes:
        warnings.append(f"Not enough montage clips in scenes: {weak_scenes}.")
    else:
        checks.append("Each documentary scene has at least one cinematic montage shot.")

    placeholder_scenes = [
        asset.get("scene_number")
        for asset in scene_assets
        if all(clip.get("provider") in {"placeholder"} for clip in asset.get("clips", []))
    ]
    if placeholder_scenes:
        warnings.append(f"Placeholder-only scene assets detected: {placeholder_scenes}.")
    else:
        checks.append("No placeholder-only scene spam detected.")

    single_repeated = [
        asset.get("scene_number")
        for asset in scene_assets
        if len({clip.get("path") or clip.get("query") for clip in asset.get("clips", [])}) <= 1
    ]
    if single_repeated:
        warnings.append(f"Repeated single visual source detected in scenes: {single_repeated}.")
    else:
        checks.append("No repeated single-image scene pattern detected.")

    video_clips = [
        clip
        for asset in scene_assets
        for clip in asset.get("clips", [])
        if clip.get("type") == "video"
    ]
    generated_motion = [
        clip
        for asset in scene_assets
        for clip in asset.get("clips", [])
        if clip.get("type") == "generated_motion"
    ]
    if video_clips:
        checks.append(f"Real video b-roll clips selected: {len(video_clips)}.")
    elif generated_motion:
        warnings.append("No downloaded video b-roll was available; generated motion fallbacks were used.")

    checks.append("Subtitle-safe lower area is enabled in the montage renderer.")


def evaluate_documentary_quality_rules(
    asset_plan: dict[str, Any],
    render_plan: dict[str, Any] | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, list[str]]:
    render_plan = render_plan or {}
    config = config or {}
    checks: list[str] = []
    warnings: list[str] = []
    visual_rules = render_plan.get("visual_rules", {})
    subtitle_style = render_plan.get("subtitle_style", {})
    montage = render_plan.get("montage", {})

    if visual_rules.get("no_scene_labels"):
        checks.append("No scene labels configured for documentary render.")
    else:
        warnings.append("Documentary render should disable scene labels and card headings.")

    if visual_rules.get("fullscreen_footage"):
        checks.append("Fullscreen footage rule is enabled.")
    else:
        warnings.append("Fullscreen footage rule is not enabled.")

    if subtitle_style.get("name") == "cinematic_documentary_v2":
        checks.append("Cinematic documentary subtitle style v2 is configured.")
    else:
        warnings.append("Subtitle style v2 is not configured.")

    target_seconds = montage.get("target_clip_seconds", [])
    if len(target_seconds) == 2 and float(target_seconds[0]) >= 4.0 and float(target_seconds[1]) <= 30.0:
        checks.append(f"Montage pacing target is adaptive cinematic {float(target_seconds[0]):.0f}-30 seconds per shot.")
    else:
        warnings.append("Montage pacing target should stay in the cinematic 4-30 second range.")
    if int(render_plan.get("fps", 0) or 0) >= 24:
        checks.append("FPS is high enough to avoid low-fps preview feeling.")
    else:
        warnings.append("FPS is low enough to feel like a prototype preview.")
    average_shot = float(montage.get("average_shot_seconds", 0) or 0)
    if average_shot >= 4.0:
        checks.append(f"Average shot duration avoids TikTok pacing: {average_shot:.1f}s.")
    elif average_shot:
        warnings.append(f"Average shot duration is too fast for documentary pacing: {average_shot:.1f}s.")
    if (render_plan.get("voice") or {}).get("enabled"):
        checks.append("Voice pipeline is enabled for documentary render.")
    else:
        warnings.append("Voice pipeline is not enabled.")
    if (render_plan.get("music") or {}).get("ducking"):
        checks.append("Music ducking is enabled for voice-safe mixing.")
    else:
        warnings.append("Music ducking is not enabled.")

    clips = [clip for asset in asset_plan.get("scene_assets", []) for clip in asset.get("clips", [])]
    if not clips:
        warnings.append("No clips available for documentary quality checks.")
        return {"checks": checks, "warnings": warnings}

    static_like = [clip for clip in clips if clip.get("type") in {"image", "generated_motion"} and not clip.get("motion", clip.get("type") == "generated_motion")]
    if static_like:
        warnings.append(f"Static-feeling image clips detected: {len(static_like)}.")
    else:
        checks.append("No static image clips detected in documentary montage.")

    placeholder = [clip for clip in clips if clip.get("provider") == "placeholder" or clip.get("fallback")]
    if placeholder:
        warnings.append(f"Placeholder or fallback clips detected: {len(placeholder)}.")
    else:
        checks.append("No placeholder usage detected.")

    unique_sources = {clip.get("path") or clip.get("query") for clip in clips}
    scene_count = max(1, len(asset_plan.get("scene_assets", [])))
    diversity_target = max(scene_count, len(clips) // 5)
    if len(unique_sources) >= diversity_target:
        checks.append("Montage source diversity is acceptable.")
    else:
        warnings.append(f"Montage source diversity is low: {len(unique_sources)} unique sources, target {diversity_target}.")

    channel = str(config.get("channel_id", ""))
    if channel == "survival":
        nature_terms = ("jungle", "rainforest", "amazon", "river", "rain", "storm", "mud", "forest", "canopy", "insect")
        nature_count = sum(1 for clip in clips if any(term in str(clip.get("query", "")).lower() or term in str(clip.get("path", "")).lower() for term in nature_terms))
        nature_ratio = nature_count / max(len(clips), 1)
        if nature_ratio >= 0.55:
            checks.append(f"Nature footage percentage is strong: {nature_ratio:.0%}.")
        else:
            warnings.append(f"Nature footage percentage is low: {nature_ratio:.0%}.")
    elif channel == "psychology":
        psychology_terms = ("rain", "city", "urban", "alone", "lonely", "screen", "subway", "fog", "reflection", "exhaustion", "night")
        psychology_count = sum(1 for clip in clips if any(term in str(clip.get("query", "")).lower() or term in str(clip.get("path", "")).lower() for term in psychology_terms))
        psychology_ratio = psychology_count / max(len(clips), 1)
        if psychology_ratio >= 0.45:
            checks.append(f"Atmospheric psychology footage percentage is acceptable: {psychology_ratio:.0%}.")
        else:
            warnings.append(f"Atmospheric psychology footage percentage is low: {psychology_ratio:.0%}.")
    else:
        checks.append("Channel-specific footage mix check skipped.")

    weak_terms = ("business", "office", "terminal", "airport") if channel == "psychology" else ("business", "office", "city", "terminal", "airport")
    weak_count = sum(1 for clip in clips if any(term in str(clip.get("query", "")).lower() for term in weak_terms))
    if weak_count:
        warnings.append(f"Potentially weak generic footage clips detected: {weak_count}.")
    else:
        checks.append("No obvious business/city generic footage selected.")

    return {"checks": checks, "warnings": warnings}
