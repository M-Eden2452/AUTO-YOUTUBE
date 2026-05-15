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
        elif not config.get("dev_mode", False) and not (22 <= len(scenes) <= 32):
            warnings.append(f"Количество production-сцен вне ожидаемого диапазона: {len(scenes)}.")
        overflow = [scene["scene_number"] for scene in scenes if len(scene.get("screen_text", "")) > 135]
        if overflow:
            warnings.append(f"Возможный overflow текста в сценах: {overflow}.")
        else:
            checks.append("Явных рисков переполнения текста не найдено.")

    if asset_plan.get("warnings"):
        warnings.extend(asset_plan["warnings"])
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
