from __future__ import annotations

from pathlib import Path
from typing import Any

from .paths import read_json, write_json


def load_selected_candidates(selected_json: Path, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    data = read_json(selected_json)
    ids = data.get("selected_candidate_ids", [])
    if not isinstance(ids, list):
        raise ValueError("selected.json должен содержать список selected_candidate_ids.")
    by_id = {int(candidate["id"]): candidate for candidate in candidates}
    selected: list[dict[str, Any]] = []
    missing: list[int] = []
    for raw_id in ids:
        candidate_id = int(raw_id)
        if candidate_id in by_id:
            selected.append(by_id[candidate_id])
        else:
            missing.append(candidate_id)
    if missing:
        raise ValueError(f"В selected.json есть неизвестные candidate ids: {missing}")
    return selected


def write_selected_example(path: Path, candidates: list[dict[str, Any]], max_clips: int) -> Path:
    ids = [int(candidate["id"]) for candidate in candidates[:max_clips]]
    write_json(path, {"selected_candidate_ids": ids})
    return path
