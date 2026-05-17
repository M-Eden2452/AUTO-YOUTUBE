from __future__ import annotations

import argparse
import sys
from typing import Any

from src.asset_finder import build_asset_plan
from src.channel_loader import load_channel_video_config
from src.config_loader import load_config
from src.intro_generator import build_intro_plan
from src.music_finder import build_music_plan
from src.obsidian_exporter import export_obsidian_note
from src.quote_generator import build_quote_plan
from src.scene_planner import build_scene_plan
from src.self_eval import evaluate_render
from src.thumbnail_generator import create_thumbnail
from src.utils import ensure_dir, write_json
from src.video_renderer import RenderStageError, build_render_plan, render_video
from src.youtube_metadata import write_youtube_metadata
from src.media_library import clean_temp_files, create_asset_report, ensure_media_library, index_existing_assets


def configure_console_encoding() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Structured AI-YouTube pipeline")
    parser.add_argument("--config", default="config/video_style.json", help="Path to base video style config.")
    parser.add_argument("--channel", help="Channel profile id, for example quotes.")
    parser.add_argument("--video", help="Video task id, for example thoughts_too_late_001.")
    parser.add_argument("--dev", action="store_true", help="Build a fast preview render.")
    parser.add_argument("--prod", action="store_true", help="Use production render settings.")
    parser.add_argument("--prod-preview", action="store_true", help="Run production settings on the first scenes.")
    parser.add_argument("--export-obsidian", action="store_true", help="Only export an Obsidian note from existing outputs.")
    parser.add_argument("--no-obsidian", action="store_true", help="Disable Obsidian export for this run.")
    parser.add_argument("--skip-render", action="store_true", help="Skip render and update only plans/metadata/Obsidian.")
    parser.add_argument("--find-music", action="store_true", help="Update only music_plan.json.")
    parser.add_argument("--refresh-assets", action="store_true", help="Search/download assets again.")
    parser.add_argument("--index-assets", action="store_true", help="Scan assets/library and update media_index.json.")
    parser.add_argument("--clean-temp", action="store_true", help="Remove render_temp and partial temporary files.")
    parser.add_argument("--asset-report", action="store_true", help="Create outputs/asset_library_report.md.")
    return parser.parse_args()


def main() -> None:
    configure_console_encoding()
    args = parse_args()
    ensure_dir("outputs")
    ensure_dir("assets/images")
    ensure_dir("assets/images/generated")
    ensure_media_library()

    if args.index_assets:
        index = index_existing_assets()
        print(f"[assets] Indexed media library items: {len(index.get('items', []))}")
        return
    if args.clean_temp:
        removed = clean_temp_files()
        print(f"[cleanup] Removed temp paths: {len(removed)}")
        return
    if args.asset_report:
        report_path = create_asset_report()
        print(f"[assets] Report created: {report_path}")
        return

    config = load_config(args.config, dev=args.dev, prod=args.prod, prod_preview=args.prod_preview)
    if args.channel or args.video:
        if not args.channel or not args.video:
            raise SystemExit("--channel and --video must be passed together.")
        config = load_channel_video_config(config, args.channel, args.video)
    plans = config["plans"]
    print(
        f"[config] Loaded {args.config} | channel={config.get('channel_id', 'default')} "
        f"| video={config.get('video_id', 'default')} | dev_mode={config['dev_mode']} "
        f"| prod_preview={config.get('prod_preview', False)}"
    )

    if args.find_music:
        music_plan = build_music_plan(config)
        print(f"[music] Music plan updated: {music_plan.get('status')}")
        return

    if args.export_obsidian:
        note_path = export_obsidian_note(config)
        print(f"[obsidian] Note exported: {note_path}")
        return

    quote_plan = build_quote_plan(config)
    metadata = write_youtube_metadata(config, quote_plan, output_path=plans.get("youtube_metadata", "outputs/youtube_metadata.json"))
    scene_plan = build_scene_plan(config, quote_plan, metadata)
    if args.prod_preview:
        scene_plan = limit_scene_plan(scene_plan, int(config.get("prod_preview_scene_count", 5)))
    intro_plan = build_intro_plan(config, metadata)
    music_plan = build_music_plan(config, scene_plan)
    asset_plan = build_asset_plan(config, scene_plan, refresh=args.refresh_assets)
    render_plan = build_render_plan(config, scene_plan, asset_plan, music_plan)
    thumbnail_path = None
    if config.get("video_task"):
        thumbnail_path = create_thumbnail(config, asset_plan)
        metadata["thumbnail_path"] = str(thumbnail_path)
        write_json(plans.get("youtube_metadata", "outputs/youtube_metadata.json"), metadata)

    write_json(plans["quote_plan"], quote_plan)
    write_json(plans["scene_plan"], scene_plan)
    write_json(plans["asset_plan"], asset_plan)
    write_json(plans["render_plan"], {**render_plan, "intro": intro_plan})
    write_json(plans.get("music_plan", "outputs/music_plan.json"), music_plan)
    print("[plans] Created quote_plan, scene_plan, asset_plan, render_plan, music_plan")

    output_path = render_plan["output_path"]
    if args.skip_render:
        eval_result = {
            "ok": True,
            "checks": ["Render skipped via --skip-render."],
            "warnings": [],
        }
        write_json(plans.get("self_eval", "outputs/self_eval.json"), eval_result)
        print("[render] Skipped via --skip-render")
    else:
        try:
            output_path = render_video(config, scene_plan, asset_plan, render_plan, music_plan)
            eval_result = evaluate_render(output_path, config, asset_plan, scene_plan, music_plan, metadata)
            write_json(plans.get("self_eval", "outputs/self_eval.json"), eval_result)
            print(f"[render] Output file: {output_path}")
        except RenderStageError as exc:
            eval_result = {
                "ok": False,
                "checks": [],
                "warnings": [
                    f"Render stopped at stage {exc.stage}: {exc.message}",
                    "Music was not added because silent video did not pass the safe render/validate pipeline.",
                ],
            }
            write_json(plans.get("self_eval", "outputs/self_eval.json"), eval_result)
            print(f"[render] Stage error {exc.stage}: {exc.message}")
            return

    note_path = None
    obsidian_enabled = config.get("obsidian", {}).get("enabled", False)
    if obsidian_enabled and not args.no_obsidian:
        note_path = export_obsidian_note(config)
        print(f"[obsidian] Note exported: {note_path}")
    elif args.no_obsidian:
        print("[obsidian] Skipped via --no-obsidian")

    if not args.skip_render:
        eval_result = evaluate_render(output_path, config, asset_plan, scene_plan, music_plan, metadata, note_path)
        write_json(plans.get("self_eval", "outputs/self_eval.json"), eval_result)
        if note_path:
            export_obsidian_note(config)
        for item in eval_result["checks"]:
            print(f"[self-eval] OK: {item}")
        for item in eval_result["warnings"]:
            print(f"[self-eval] Note: {item}")

    print(f"[metadata] Created {plans.get('youtube_metadata', 'outputs/youtube_metadata.json')}, chosen title: {metadata.get('chosen_title')}")


def limit_scene_plan(scene_plan: dict[str, Any], max_scenes: int) -> dict[str, Any]:
    limited = {**scene_plan}
    scenes = list(scene_plan.get("scenes", []))[:max_scenes]
    limited["scenes"] = scenes
    limited["target_duration"] = sum(float(scene.get("duration", 0)) for scene in scenes)
    limited["preview_mode"] = "prod_preview"
    return limited


if __name__ == "__main__":
    main()
