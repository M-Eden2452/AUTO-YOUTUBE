from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from .utils import read_json


OBSIDIAN_VAULT_PATH = "G:/ObsidianBase/ObsidianBase"


def load_channel_video_config(base_config: dict[str, Any], channel: str, video: str) -> dict[str, Any]:
    channel_dir = Path("channels") / channel
    content_path = Path("content") / channel / f"{video}.json"
    channel_config = read_json(channel_dir / "channel_config.json")
    style = read_json(channel_dir / "style.json")
    video_task = read_json(content_path)

    if video_task.get("channel") != channel:
        raise ValueError(f"Video task {content_path} belongs to channel {video_task.get('channel')!r}, not {channel!r}.")
    if video_task.get("video_id") != video:
        raise ValueError(f"Video task {content_path} has video_id {video_task.get('video_id')!r}, not {video!r}.")

    output_dir = Path("outputs") / channel / video
    updated = deepcopy(base_config)
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
            "documentary_subtitles_only": bool(style.get("documentary_subtitles_only", updated.get("documentary_subtitles_only", False))),
            "documentary_music_volume": style.get("documentary_music_volume", updated.get("documentary_music_volume", 0.12)),
            "subtitle_style": style.get("subtitle_style", updated.get("subtitle_style", {})),
            "output_dir": str(output_dir),
            "output_filename": str(output_dir / ("final_preview.mp4" if updated.get("dev_mode", False) else "final_video.mp4")),
            "prod_output_filename": str(output_dir / "final_video.mp4"),
            "thumbnail_path": str(output_dir / "thumbnail.png"),
            "plans": {
                "quote_plan": str(output_dir / "quote_plan.json"),
                "scene_plan": str(output_dir / "scene_plan.json"),
                "asset_plan": str(output_dir / "asset_plan.json"),
                "render_plan": str(output_dir / "render_plan.json"),
                "music_plan": str(output_dir / "music_plan.json"),
                "youtube_metadata": str(output_dir / "youtube_metadata.json"),
                "self_eval": str(output_dir / "self_eval.json"),
                "visual_debug": str(output_dir / "visual_debug.json"),
            },
        }
    )

    obsidian = deepcopy(updated.get("obsidian", {}))
    channel_name = channel_config.get("channel_name", channel)
    obsidian.update(
        {
            "enabled": True,
            "vault_path": OBSIDIAN_VAULT_PATH,
            "folder": f"YouTube/02 Видео/{channel_name}/{video}",
            "channel_folder": channel_config.get("obsidian_folder", f"YouTube/01 Каналы/{channel_name}"),
            "video_note_dir": f"{OBSIDIAN_VAULT_PATH}/YouTube/02 Видео/{channel_name}/{video}",
            "video_embed": True,
            "fallback_to_outputs": True,
        }
    )
    updated["obsidian"] = obsidian
    return updated
