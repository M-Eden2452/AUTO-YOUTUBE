from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from scripts.test_moss_voices import main as run_moss_voice_tests
from src.asset_finder import build_asset_plan
from src.assets.provider_diagnostics import (
    collect_provider_diagnostics,
    diagnostics_to_text,
)
from src.assets.semantic_visual_evaluation import run_semantic_visual_evaluation
from src.assets.semantic_visual_openai import openai_backend_diagnostics
from src.assets.semantic_visual_service import (
    analyse_semantic_visual_for_project,
    inspect_semantic_visual_project,
)
from src.assets.visual_preview import (
    inspect_visual_preview_project,
    prepare_visual_preview_for_project,
)
from src.audio.voice_cli import run_voice_cli
from src.channel_loader import load_channel_video_config
from src.config_loader import load_config
from src.intro_generator import build_intro_plan
from src.legacy_pipeline.cli import parse_args
from src.legacy_pipeline.maintenance import run_maintenance_command
from src.legacy_pipeline.workflow import run_legacy_video_pipeline
from src.media_library import (
    analyse_media_library,
    clean_temp_files,
    create_asset_report,
    ensure_media_library,
    index_existing_assets,
    migrate_media_library,
)
from src.music_finder import build_music_plan
from src.news.pipeline import run_news_to_short_cli
from src.obsidian_exporter import export_obsidian_note
from src.production_catalog.cli import run_production_catalog_cli
from src.production_plan.solar_vs_nuclear_render import (
    build_solar_vs_nuclear_video,
)
from src.production_plan.youtube_shorts import create_solar_vs_nuclear_plan
from src.providers.envato_manual_provider import EnvatoManualProvider
from src.quote_generator import build_quote_plan
from src.scene_planner import build_scene_plan
from src.self_eval import evaluate_render
from src.size_comparison_engine import run_size_comparison_pipeline
from src.thumbnail_generator import create_thumbnail
from src.tts_providers.moss_tts_provider import (
    MossTtsProviderError,
    run_test_synthesis,
)
from src.utils import ensure_dir, write_json
from src.video_renderer import (
    RenderStageError,
    build_render_plan,
    render_video,
)
from src.voice_engine import (
    align_voice_manifest_to_scene_plan,
    apply_voice_timing_to_scene_plan,
    build_voice_manifest,
)
from src.youtube_metadata import write_youtube_metadata


def configure_console_encoding() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def main() -> None:
    configure_console_encoding()
    args = parse_args()
    from src.config_resolver import resolve_application_paths

    application_paths = resolve_application_paths(
        workspace_root=args.workspace,
        paths_config=args.paths_config,
        projects_root=args.projects_root,
    )
    args.projects_root = str(application_paths.projects_root)
    args.config = args.config or str(
        application_paths.config_root / "video_style.json"
    )
    args.production_plan_root = args.production_plan_root or str(
        application_paths.repository_root
    )
    assets_root = application_paths.workspace.media_library.parent
    ensure_dir(application_paths.outputs_root)
    ensure_dir(assets_root / "images")
    ensure_dir(assets_root / "images" / "generated")
    ensure_media_library(application_paths.workspace.media_library)

    compatibility = globals()
    if run_maintenance_command(args, application_paths, compatibility):
        return
    run_legacy_video_pipeline(args, application_paths, compatibility)


def limit_scene_plan(
    scene_plan: dict[str, Any],
    max_scenes: int,
) -> dict[str, Any]:
    limited = {**scene_plan}
    scenes = list(scene_plan.get("scenes", []))[:max_scenes]
    limited["scenes"] = scenes
    limited["target_duration"] = sum(
        float(scene.get("duration", 0)) for scene in scenes
    )
    limited["preview_mode"] = "prod_preview"
    return limited


if __name__ == "__main__":
    main()
