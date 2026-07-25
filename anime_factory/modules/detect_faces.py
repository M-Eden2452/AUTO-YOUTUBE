from __future__ import annotations

from pathlib import Path
from typing import Any

from .paths import write_json


def detect_faces(
    source_video: Path,
    start: float,
    end: float,
    output_json: Path,
    config: dict[str, Any],
    force: bool = False,
) -> list[dict[str, Any]]:
    if output_json.exists() and not force:
        from .paths import read_json

        print(f"Детекции лиц уже существуют, пропускаю: {output_json}")
        return read_json(output_json)

    try:
        import cv2
    except ImportError:
        print("OpenCV не установлен, face crop будет пропущен.")
        detections = _empty_detections(start, end, float(config.get("sample_fps", 2)))
        write_json(output_json, detections)
        return detections

    sample_fps = float(config.get("sample_fps", 2))
    interval = 1.0 / max(sample_fps, 0.1)
    capture = cv2.VideoCapture(str(source_video))
    if not capture.isOpened():
        print(f"Не удалось открыть видео для face detection: {source_video}")
        detections = _empty_detections(start, end, sample_fps)
        write_json(output_json, detections)
        return detections

    detector_backend = str(config.get("detector_backend", "anime")).lower()
    cascade_path = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
    classifier = cv2.CascadeClassifier(str(cascade_path)) if cascade_path.exists() else None
    if classifier is None and detector_backend == "haar":
        print("OpenCV Haar cascade не найден, face crop будет пропущен.")
        capture.release()
        detections = _empty_detections(start, end, sample_fps)
        write_json(output_json, detections)
        return detections
    detections: list[dict[str, Any]] = []
    current = float(start)
    while current < float(end):
        capture.set(cv2.CAP_PROP_POS_MSEC, current * 1000)
        ok, frame = capture.read()
        faces: list[dict[str, Any]] = []
        if ok:
            if classifier is not None:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                found = classifier.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(40, 40))
                for (x, y, w, h) in found:
                    faces.append({"x": int(x), "y": int(y), "w": int(w), "h": int(h), "confidence": 0.8, "backend": "haar"})
            if detector_backend in {"anime", "auto"}:
                faces.extend(_detect_anime_faces(frame, cv2, config))
            faces = _dedupe_faces(faces)
        detections.append({"time": round(current - float(start), 2), "faces": faces})
        current += interval

    capture.release()
    write_json(output_json, detections)
    print(f"Детекции лиц сохранены: {output_json}")
    return detections


def _empty_detections(start: float, end: float, sample_fps: float) -> list[dict[str, Any]]:
    interval = 1.0 / max(sample_fps, 0.1)
    duration = max(0.0, float(end) - float(start))
    samples: list[dict[str, Any]] = []
    current = 0.0
    while current < duration or not samples:
        samples.append({"time": round(current, 2), "faces": []})
        current += interval
    return samples


def _detect_anime_faces(frame: Any, cv2: Any, config: dict[str, Any]) -> list[dict[str, Any]]:
    # Lightweight anime-oriented heuristic: find high-contrast eye/hair/face clusters in the upper/mid frame.
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    height, width = gray.shape[:2]
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 60, 160)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (17, 11))
    closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
    contours, _hierarchy = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    min_area = width * height * float(config.get("anime_min_area_ratio", 0.004))
    max_area = width * height * float(config.get("anime_max_area_ratio", 0.18))
    faces: list[dict[str, Any]] = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        area = w * h
        if area < min_area or area > max_area:
            continue
        aspect = w / max(h, 1)
        if aspect < 0.45 or aspect > 1.8:
            continue
        if y > height * 0.78:
            continue
        pad_x = int(w * 0.25)
        pad_y = int(h * 0.35)
        fx = max(0, x - pad_x)
        fy = max(0, y - pad_y)
        fw = min(width - fx, w + pad_x * 2)
        fh = min(height - fy, h + pad_y * 2)
        confidence = min(0.72, 0.35 + area / max(width * height * 0.06, 1))
        faces.append({"x": int(fx), "y": int(fy), "w": int(fw), "h": int(fh), "confidence": round(confidence, 3), "backend": "anime_heuristic"})
    faces.sort(key=lambda face: face["w"] * face["h"] * face["confidence"], reverse=True)
    return faces[: int(config.get("anime_max_faces", 4))]


def _dedupe_faces(faces: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for face in sorted(faces, key=lambda item: item["w"] * item["h"] * item.get("confidence", 0.5), reverse=True):
        if any(_iou(face, existing) > 0.35 for existing in selected):
            continue
        selected.append(face)
    return selected


def _iou(left: dict[str, Any], right: dict[str, Any]) -> float:
    lx1, ly1 = float(left["x"]), float(left["y"])
    lx2, ly2 = lx1 + float(left["w"]), ly1 + float(left["h"])
    rx1, ry1 = float(right["x"]), float(right["y"])
    rx2, ry2 = rx1 + float(right["w"]), ry1 + float(right["h"])
    ix1, iy1 = max(lx1, rx1), max(ly1, ry1)
    ix2, iy2 = min(lx2, rx2), min(ly2, ry2)
    intersection = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    area = float(left["w"] * left["h"] + right["w"] * right["h"]) - intersection
    return intersection / area if area > 0 else 0.0
