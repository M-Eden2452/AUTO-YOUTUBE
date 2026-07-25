from __future__ import annotations

from pathlib import Path
from typing import Any

from .paths import read_json, write_json


def detect_scene_cuts(
    source_video: Path,
    output_json: Path,
    sample_fps: float = 2.0,
    threshold: float = 0.55,
    force: bool = False,
) -> list[dict[str, Any]]:
    if output_json.exists() and not force:
        print(f"Scene cuts уже существуют, пропускаю: {output_json}")
        return read_json(output_json)
    try:
        import cv2
        import numpy as np
    except ImportError:
        print("OpenCV/numpy недоступны, scene detection пропущен.")
        write_json(output_json, [])
        return []

    capture = cv2.VideoCapture(str(source_video))
    if not capture.isOpened():
        print(f"Не удалось открыть видео для scene detection: {source_video}")
        write_json(output_json, [])
        return []

    interval = 1.0 / max(sample_fps, 0.1)
    duration_ms = capture.get(cv2.CAP_PROP_FRAME_COUNT) / max(capture.get(cv2.CAP_PROP_FPS) or 24.0, 1.0) * 1000
    previous_hist = None
    cuts: list[dict[str, Any]] = []
    current = 0.0
    while current * 1000 < duration_ms:
        capture.set(cv2.CAP_PROP_POS_MSEC, current * 1000)
        ok, frame = capture.read()
        if not ok:
            break
        small = cv2.resize(frame, (160, 90), interpolation=cv2.INTER_AREA)
        hist = cv2.calcHist([small], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
        cv2.normalize(hist, hist)
        if previous_hist is not None:
            score = float(cv2.compareHist(previous_hist, hist, cv2.HISTCMP_BHATTACHARYYA))
            if score >= threshold:
                cuts.append({"time": round(current, 2), "score": round(min(score, 1.0), 4)})
        previous_hist = hist
        current += interval

    capture.release()
    write_json(output_json, cuts)
    print(f"Scene cuts сохранены: {output_json}")
    return cuts
