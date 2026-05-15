from __future__ import annotations

import argparse
import sys
from typing import Any

from src.asset_finder import build_asset_plan
from src.config_loader import load_config
from src.intro_generator import build_intro_plan
from src.music_finder import build_music_plan
from src.obsidian_exporter import export_obsidian_note
from src.quote_generator import build_quote_plan
from src.scene_planner import build_scene_plan
from src.self_eval import evaluate_render
from src.utils import ensure_dir, write_json
from src.video_renderer import RenderStageError, build_render_plan, render_video
from src.youtube_metadata import write_youtube_metadata


def configure_console_encoding() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Структурный pipeline AI-YouTube")
    parser.add_argument("--config", default="config/video_style.json", help="Путь к конфигу стиля видео.")
    parser.add_argument("--dev", action="store_true", help="Собрать короткое быстрое превью.")
    parser.add_argument("--prod", action="store_true", help="Использовать production-настройки рендера.")
    parser.add_argument("--prod-preview", action="store_true", help="Прогнать production pipeline на первых 3-5 сценах.")
    parser.add_argument("--export-obsidian", action="store_true", help="Только экспортировать Obsidian-заметку из готовых outputs.")
    parser.add_argument("--no-obsidian", action="store_true", help="Отключить Obsidian-экспорт для этого запуска.")
    parser.add_argument("--skip-render", action="store_true", help="Пропустить рендер и обновить только metadata/Obsidian.")
    parser.add_argument("--find-music", action="store_true", help="Обновить только music_plan.json.")
    parser.add_argument("--refresh-assets", action="store_true", help="Повторно искать и скачивать ассеты для сцен.")
    return parser.parse_args()


def main() -> None:
    configure_console_encoding()
    args = parse_args()
    ensure_dir("outputs")
    ensure_dir("assets/images")
    ensure_dir("assets/images/generated")

    config = load_config(args.config, dev=args.dev, prod=args.prod, prod_preview=args.prod_preview)
    print(f"[config] Загружен {args.config} | dev_mode={config['dev_mode']} | prod_preview={config.get('prod_preview', False)}")

    if args.find_music:
        music_plan = build_music_plan(config)
        print(f"[music] План музыки обновлен: {music_plan.get('status')}")
        return

    if args.export_obsidian:
        note_path = export_obsidian_note(config)
        print(f"[obsidian] Заметка экспортирована: {note_path}")
        return

    quote_plan = build_quote_plan(config)
    metadata = write_youtube_metadata(config, quote_plan)
    scene_plan = build_scene_plan(config, quote_plan, metadata)
    if args.prod_preview:
        scene_plan = limit_scene_plan(scene_plan, int(config.get("prod_preview_scene_count", 5)))
    intro_plan = build_intro_plan(config, metadata)
    music_plan = build_music_plan(config)
    asset_plan = build_asset_plan(config, scene_plan, refresh=args.refresh_assets)
    render_plan = build_render_plan(config, scene_plan, asset_plan, music_plan)

    plans = config["plans"]
    write_json(plans["quote_plan"], quote_plan)
    write_json(plans["scene_plan"], scene_plan)
    write_json(plans["asset_plan"], asset_plan)
    write_json(plans["render_plan"], {**render_plan, "intro": intro_plan})
    write_json(plans.get("music_plan", "outputs/music_plan.json"), music_plan)
    print("[plans] Созданы quote_plan, scene_plan, asset_plan, render_plan, music_plan")

    output_path = render_plan["output_path"]
    if args.skip_render:
        eval_result = {
            "ok": True,
            "checks": ["Рендер пропущен через --skip-render."],
            "warnings": [],
        }
        write_json("outputs/self_eval.json", eval_result)
        print("[render] Пропущен через --skip-render")
    else:
        try:
            output_path = render_video(config, scene_plan, asset_plan, render_plan, music_plan)
            eval_result = evaluate_render(output_path, config, asset_plan, scene_plan, music_plan, metadata)
            write_json("outputs/self_eval.json", eval_result)
            print(f"[render] Итоговый файл: {output_path}")
        except RenderStageError as exc:
            eval_result = {
                "ok": False,
                "checks": [],
                "warnings": [
                    f"Рендер остановлен на этапе {exc.stage}: {exc.message}",
                    "Музыка не добавлялась, потому что silent video не прошел полный безопасный render/validate pipeline.",
                ],
            }
            write_json("outputs/self_eval.json", eval_result)
            print(f"[render] Ошибка этапа {exc.stage}: {exc.message}")
            return

    note_path = None
    obsidian_enabled = config.get("obsidian", {}).get("enabled", False)
    if obsidian_enabled and not args.no_obsidian:
        note_path = export_obsidian_note(config)
        print(f"[obsidian] Заметка экспортирована: {note_path}")
    elif args.no_obsidian:
        print("[obsidian] Пропущено через --no-obsidian")

    if not args.skip_render:
        eval_result = evaluate_render(output_path, config, asset_plan, scene_plan, music_plan, metadata, note_path)
        write_json("outputs/self_eval.json", eval_result)
        if note_path:
            export_obsidian_note(config)
        for item in eval_result["checks"]:
            print(f"[self-eval] OK: {item}")
        for item in eval_result["warnings"]:
            print(f"[self-eval] Заметка: {item}")

    print(f"[metadata] Создан outputs/youtube_metadata.json, выбранный заголовок: {metadata.get('chosen_title')}")


def limit_scene_plan(scene_plan: dict[str, Any], max_scenes: int) -> dict[str, Any]:
    limited = {**scene_plan}
    scenes = list(scene_plan.get("scenes", []))[:max_scenes]
    limited["scenes"] = scenes
    limited["target_duration"] = sum(float(scene.get("duration", 0)) for scene in scenes)
    limited["preview_mode"] = "prod_preview"
    return limited


if __name__ == "__main__":
    main()
