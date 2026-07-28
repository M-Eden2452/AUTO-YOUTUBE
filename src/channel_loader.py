from __future__ import annotations

from copy import deepcopy
import os
from pathlib import Path
from typing import Any

from .utils import read_json


ENV_OBSIDIAN_VAULT = "AI_YOUTUBE_OBSIDIAN_VAULT"


def load_channel_video_config(
    base_config: dict[str, Any],
    channel: str,
    video: str,
    *,
    application_paths=None,
    obsidian_vault: str | Path | None = None,
) -> dict[str, Any]:
    if application_paths is None:
        from src.config_resolver.paths import resolve_application_paths

        application_paths = resolve_application_paths()
    channel_dir = application_paths.channels_root / channel
    content_path = _content_task_path(channel, video, content_root=application_paths.content_root)
    channel_config = read_json(channel_dir / "channel_config.json")
    style = read_json(channel_dir / "style.json")
    video_task = read_json(content_path)

    if video_task.get("channel") != channel:
        raise ValueError(f"Video task {content_path} belongs to channel {video_task.get('channel')!r}, not {channel!r}.")
    if video_task.get("video_id") != video:
        raise ValueError(f"Video task {content_path} has video_id {video_task.get('video_id')!r}, not {video!r}.")

    updated = deepcopy(base_config)
    output_dir = application_paths.outputs_root / channel / video
    preview_output = bool(updated.get("dev_mode", False) or updated.get("cinematic_preview", False))
    updated.update(
        {
            "channel_id": channel,
            "video_id": video,
            "channel_config": channel_config,
            "style_profile": style,
            "video_task": video_task,
            "video_type": video_task.get("video_type", channel_config.get("video_format", updated.get("video_type"))),
            "topic": video_task["chosen_title"],
            "person": channel_config.get("channel_name", updated.get("person", "")),
            "language": video_task.get("language", channel_config.get("default_language", updated.get("language", "ru"))),
            "quote_source": f"content/{channel}/{video}.json",
            "visual_style": style.get("visual_style", updated.get("visual_style", "")),
            "image_style": style.get("image_style", updated.get("image_style", "")),
            "intro_style": style.get("intro_style", updated.get("intro_style", "")),
            "text_style": style.get("text_style", updated.get("text_style", "")),
            "documentary_subtitles_only": bool(
                video_task.get(
                    "documentary_subtitles_only",
                    style.get("documentary_subtitles_only", updated.get("documentary_subtitles_only", False)),
                )
            ),
            "documentary_music_volume": video_task.get(
                "documentary_music_volume",
                style.get("documentary_music_volume", updated.get("documentary_music_volume", 0.12)),
            ),
            "subtitle_style": {
                **updated.get("subtitle_style", {}),
                **style.get("subtitle_style", {}),
                **video_task.get("subtitle_style", {}),
            },
            "voice": {
                **updated.get("voice", {}),
                **style.get("voice", {}),
                **video_task.get("voice", {}),
            },
            "music_search": {
                **updated.get("music_search", {}),
                **style.get("music_search", {}),
                **video_task.get("music_search", {}),
            },
            "asset_library": {
                **updated.get("asset_library", {}),
                **style.get("asset_library", {}),
                **video_task.get("asset_library", {}),
            },
            "manual_assets": {
                **updated.get("manual_assets", {}),
                **style.get("manual_assets", {}),
                **video_task.get("manual_assets", {}),
            },
            "output_dir": str(output_dir),
            "output_filename": str(output_dir / ("final_preview.mp4" if preview_output else "final_video.mp4")),
            "prod_output_filename": str(output_dir / "final_video.mp4"),
            "thumbnail_path": str(output_dir / "thumbnail.png"),
            "plans": {
                "quote_plan": str(output_dir / "quote_plan.json"),
                "scene_plan": str(output_dir / "scene_plan.json"),
                "asset_plan": str(output_dir / "asset_plan.json"),
                "render_plan": str(output_dir / "render_plan.json"),
                "music_plan": str(output_dir / "music_plan.json"),
                "voice_manifest": str(output_dir / "voice_manifest.json"),
                "youtube_metadata": str(output_dir / "youtube_metadata.json"),
                "self_eval": str(output_dir / "self_eval.json"),
                "visual_debug": str(output_dir / "visual_debug.json"),
            },
        }
    )

    obsidian = deepcopy(updated.get("obsidian", {}))
    channel_name = channel_config.get("channel_name", channel)
    vault_path = str(obsidian_vault or os.getenv(ENV_OBSIDIAN_VAULT, "") or "").rstrip("/\\")
    note_folder = f"YouTube/02 Видео/{channel_name}/{video}"
    obsidian.update(
        {
            "enabled": bool(vault_path),
            "vault_path": vault_path,
            "folder": note_folder,
            "channel_folder": channel_config.get("obsidian_folder", f"YouTube/01 Каналы/{channel_name}"),
            "video_note_dir": f"{vault_path}/{note_folder}" if vault_path else "",
            "video_embed": True,
            "fallback_to_outputs": True,
        }
    )
    updated["obsidian"] = obsidian
    return updated


def _content_task_path(channel: str, video: str, *, content_root: str | Path | None = None) -> Path:
    if content_root is None:
        from src.config_resolver.paths import resolve_application_paths

        content_root = resolve_application_paths().content_root
    root = Path(content_root)
    legacy_path = root / channel / f"{video}.json"
    if legacy_path.exists():
        return legacy_path

    package_path = root / channel / video / "scene_notes.json"
    if package_path.exists():
        return package_path

    raise FileNotFoundError(f"Video task not found: {legacy_path} or {package_path}")
