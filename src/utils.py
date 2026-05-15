from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def project_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def ensure_dir(path: str | Path) -> Path:
    target = project_path(path)
    target.mkdir(parents=True, exist_ok=True)
    return target


def write_json(path: str | Path, data: dict[str, Any]) -> Path:
    target = project_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def read_json(path: str | Path) -> dict[str, Any]:
    target = project_path(path)
    return json.loads(target.read_text(encoding="utf-8"))
