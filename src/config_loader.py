from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from .utils import read_json
from .config_resolver.paths import repository_path


DEFAULT_CONFIG_PATH = repository_path("config", "video_style.json")


def load_config(
    config_path: str | Path = DEFAULT_CONFIG_PATH,
    dev: bool = False,
    prod: bool = False,
    prod_preview: bool = False,
    cinematic_preview: bool = False,
    outputs_root: str | Path | None = None,
) -> dict[str, Any]:
    config = read_json(config_path)
    if prod or prod_preview or cinematic_preview:
        config["dev_mode"] = False
    elif dev:
        config["dev_mode"] = True
    else:
        config["dev_mode"] = bool(config.get("dev_mode", False))

    if config["dev_mode"]:
        return _rebase_runtime_outputs(_apply_dev_defaults(config), outputs_root)

    updated = _apply_prod_defaults(config)
    if prod_preview:
        updated["output_filename"] = "outputs/final_prod_preview.mp4"
        updated["resolution"] = [1280, 720]
        updated["font_size"] = min(int(updated.get("font_size", 58)), 44)
        updated["prod_preview"] = True
        updated["prod_preview_scene_count"] = 5
    if cinematic_preview:
        updated["cinematic_preview"] = True
        updated["dev_mode"] = False
        updated["resolution"] = [1280, 720]
        updated["fps"] = int(updated.get("cinematic_preview_fps", 24))
        updated["cinematic_preview_fps"] = int(updated.get("cinematic_preview_fps", 24))
        updated["cinematic_preview_crf"] = int(updated.get("cinematic_preview_crf", 17))
        updated["cinematic_preview_preset"] = str(updated.get("cinematic_preview_preset", "slow"))
        updated["audio_bitrate"] = str(updated.get("audio_bitrate", "192k"))
        updated["output_filename"] = "outputs/final_preview.mp4"
        updated["font_size"] = min(int(updated.get("font_size", 58)), 44)
    return _rebase_runtime_outputs(updated, outputs_root)


def _rebase_runtime_outputs(
    value: Any,
    outputs_root: str | Path | None,
) -> Any:
    if outputs_root is None:
        return value
    root = Path(outputs_root).resolve(strict=False)
    if isinstance(value, dict):
        return {
            key: _rebase_runtime_outputs(item, root)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_rebase_runtime_outputs(item, root) for item in value]
    if isinstance(value, str):
        path = Path(value)
        if not path.is_absolute() and path.parts and path.parts[0].casefold() == "outputs":
            return str(root.joinpath(*path.parts[1:]))
    return value


def _apply_dev_defaults(config: dict[str, Any]) -> dict[str, Any]:
    updated = deepcopy(config)
    updated["scene_duration"] = min(float(updated.get("scene_duration", 7)), 10.0)
    updated["fps"] = min(int(updated.get("fps", 15)), 24)
    updated["output_filename"] = "outputs/final_preview.mp4"
    return updated


def _apply_prod_defaults(config: dict[str, Any]) -> dict[str, Any]:
    updated = deepcopy(config)
    if "prod_resolution" in updated:
        updated["resolution"] = updated["prod_resolution"]
    if "prod_fps" in updated:
        updated["fps"] = updated["prod_fps"]
    if "prod_scene_duration" in updated:
        updated["scene_duration"] = updated["prod_scene_duration"]
    if "prod_output_filename" in updated:
        updated["output_filename"] = updated["prod_output_filename"]
    if "prod_font_size" in updated:
        updated["font_size"] = updated["prod_font_size"]
    return updated
