from __future__ import annotations

import argparse

from src.asset_finder import build_asset_plan
from src.config_loader import load_config
from src.intro_generator import build_intro_plan
from src.obsidian_exporter import export_obsidian_note
from src.quote_generator import build_quote_plan
from src.scene_planner import build_scene_plan
from src.self_eval import evaluate_render
from src.utils import ensure_dir, write_json
from src.video_renderer import build_render_plan, render_video
from src.youtube_metadata import write_youtube_metadata


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AI-YouTube structured video pipeline")
    parser.add_argument("--config", default="config/video_style.json", help="Path to video style config.")
    parser.add_argument("--dev", action="store_true", help="Render a short fast preview.")
    parser.add_argument("--prod", action="store_true", help="Use production render settings.")
    parser.add_argument("--export-obsidian", action="store_true", help="Only export an Obsidian note from existing outputs.")
    parser.add_argument("--no-obsidian", action="store_true", help="Disable Obsidian export for this run.")
    parser.add_argument("--skip-render", action="store_true", help="Skip video rendering and update metadata/Obsidian only.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ensure_dir("outputs")
    ensure_dir("assets/images")

    config = load_config(args.config, dev=args.dev, prod=args.prod)
    print(f"[config] Loaded {args.config} | dev_mode={config['dev_mode']}")

    if args.export_obsidian:
        metadata = write_youtube_metadata(config)
        print(f"[metadata] Wrote outputs/youtube_metadata.json with {len(metadata['title_variants'])} title ideas")
        note_path = export_obsidian_note(config)
        print(f"[obsidian] Exported note: {note_path}")
        return

    quote_plan = build_quote_plan(config)
    scene_plan = build_scene_plan(config, quote_plan)
    intro_plan = build_intro_plan(config)
    asset_plan = build_asset_plan(config, scene_plan)
    render_plan = build_render_plan(config, scene_plan, asset_plan)

    plans = config["plans"]
    write_json(plans["quote_plan"], quote_plan)
    write_json(plans["scene_plan"], scene_plan)
    write_json(plans["asset_plan"], asset_plan)
    write_json(plans["render_plan"], {**render_plan, "intro": intro_plan})
    print("[plans] Wrote quote_plan, scene_plan, asset_plan, render_plan")

    if args.skip_render:
        output_path = render_plan["output_path"]
        eval_result = {"ok": True, "checks": ["Render skipped by --skip-render."], "warnings": []}
        write_json("outputs/self_eval.json", eval_result)
        print("[render] Skipped by --skip-render")
    else:
        output_path = render_video(config, scene_plan, asset_plan, render_plan)
        eval_result = evaluate_render(output_path, config, asset_plan)
        write_json("outputs/self_eval.json", eval_result)

        print(f"[render] Output: {output_path}")
        for item in eval_result["checks"]:
            print(f"[self-eval] OK: {item}")
        for item in eval_result["warnings"]:
            print(f"[self-eval] Note: {item}")

    metadata = write_youtube_metadata(config, quote_plan, scene_plan)
    print(f"[metadata] Wrote outputs/youtube_metadata.json with {len(metadata['title_variants'])} title ideas")

    obsidian_enabled = config.get("obsidian", {}).get("enabled", False)
    if obsidian_enabled and not args.no_obsidian:
        note_path = export_obsidian_note(config)
        print(f"[obsidian] Exported note: {note_path}")
    elif args.no_obsidian:
        print("[obsidian] Skipped by --no-obsidian")


if __name__ == "__main__":
    main()
