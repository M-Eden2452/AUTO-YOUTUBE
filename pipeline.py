from __future__ import annotations

import argparse

from src.asset_finder import build_asset_plan
from src.config_loader import load_config
from src.intro_generator import build_intro_plan
from src.quote_generator import build_quote_plan
from src.scene_planner import build_scene_plan
from src.self_eval import evaluate_render
from src.utils import ensure_dir, write_json
from src.video_renderer import build_render_plan, render_video


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AI-YouTube structured video pipeline")
    parser.add_argument("--config", default="config/video_style.json", help="Path to video style config.")
    parser.add_argument("--dev", action="store_true", help="Render a short fast preview.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ensure_dir("outputs")
    ensure_dir("assets/images")

    config = load_config(args.config, dev=args.dev)
    print(f"[config] Loaded {args.config} | dev_mode={config['dev_mode']}")

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

    output_path = render_video(config, scene_plan, asset_plan, render_plan)
    eval_result = evaluate_render(output_path, config, asset_plan)
    write_json("outputs/self_eval.json", eval_result)

    print(f"[render] Output: {output_path}")
    for item in eval_result["checks"]:
        print(f"[self-eval] OK: {item}")
    for item in eval_result["warnings"]:
        print(f"[self-eval] Note: {item}")


if __name__ == "__main__":
    main()
