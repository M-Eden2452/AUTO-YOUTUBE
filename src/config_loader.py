from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from .utils import read_json


DEFAULT_CONFIG_PATH = Path("config/video_style.json")


def load_config(
    config_path: str | Path = DEFAULT_CONFIG_PATH,
    dev: bool = False,
    prod: bool = False,
) -> dict[str, Any]:
    config = read_json(config_path)
    if prod:
        config["dev_mode"] = False
    elif dev:
        config["dev_mode"] = True
    else:
        config["dev_mode"] = bool(config.get("dev_mode", False))

    if config["dev_mode"]:
        return _apply_dev_defaults(config)
    return _apply_prod_defaults(config)


def _apply_dev_defaults(config: dict[str, Any]) -> dict[str, Any]:
    updated = deepcopy(config)
    updated["scene_duration"] = min(float(updated.get("scene_duration", 7)), 10.0)
    updated["fps"] = min(int(updated.get("fps", 15)), 24)
    return updated


def _apply_prod_defaults(config: dict[str, Any]) -> dict[str, Any]:
    updated = deepcopy(config)
    if "prod_resolution" in updated:
        updated["resolution"] = updated["prod_resolution"]
    if "prod_fps" in updated:
        updated["fps"] = updated["prod_fps"]
    if "prod_scene_duration" in updated:
        updated["scene_duration"] = updated["prod_scene_duration"]
    return updated
