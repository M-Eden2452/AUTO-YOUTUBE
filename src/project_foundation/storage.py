from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from .models import ProjectFoundationError


def ensure_dir(path: str | Path) -> Path:
    target = Path(path)
    target.mkdir(parents=True, exist_ok=True)
    return target


def atomic_write_json(path: str | Path, data: dict[str, Any]) -> Path:
    """Write JSON deterministically (sorted keys off, insertion order kept) via temp file + os.replace."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=False) + "\n"

    fd, tmp_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=str(target.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(tmp_name, target)
    finally:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)
    return target


def read_json(path: str | Path) -> dict[str, Any]:
    target = Path(path)
    try:
        raw = target.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ProjectFoundationError(f"Corrupted JSON file at {target}: {exc}") from exc
    if not isinstance(data, dict):
        raise ProjectFoundationError(f"Expected a JSON object at {target}, got {type(data).__name__}.")
    return data


def read_json_if_exists(path: str | Path) -> dict[str, Any] | None:
    target = Path(path)
    if not target.exists():
        return None
    return read_json(target)
