from __future__ import annotations

from pathlib import Path
from typing import Any

from moviepy import VideoFileClip


def evaluate_render(output_path: str | Path, config: dict[str, Any], asset_plan: dict[str, Any]) -> dict[str, Any]:
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

    expected_duration = float(config["scene_duration"])
    if abs(duration - expected_duration) <= 0.35:
        checks.append(f"Длительность близка к целевой: {duration:.2f} сек.")
    else:
        warnings.append(f"Длительность отличается от целевой: {duration:.2f} сек. против {expected_duration:.2f} сек.")

    if [width, height] == [int(v) for v in config["resolution"]]:
        checks.append(f"Разрешение совпадает с конфигом: {width}x{height}.")
    else:
        warnings.append(f"Разрешение не совпадает: {width}x{height}.")

    if asset_plan["image"]["status"] != "найдено_локально":
        warnings.append("Использована placeholder-картинка, потому что локальный портрет Jordan Peterson не найден.")
    if asset_plan["music"]["status"] != "найдено":
        warnings.append("Видео отрендерено без музыки, потому что музыкальный файл не найден.")

    return {"ok": path.exists(), "checks": checks, "warnings": warnings}
