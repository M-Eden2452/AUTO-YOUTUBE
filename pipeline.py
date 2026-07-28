from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
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
from src.size_comparison_engine import run_size_comparison_pipeline
from src.thumbnail_generator import create_thumbnail
from src.tts_providers.moss_tts_provider import MossTtsProviderError, run_test_synthesis
from src.utils import ensure_dir, write_json
from src.video_renderer import RenderStageError, build_render_plan, render_video
from src.voice_engine import align_voice_manifest_to_scene_plan, apply_voice_timing_to_scene_plan, build_voice_manifest
from src.youtube_metadata import write_youtube_metadata
from src.assets.provider_diagnostics import collect_provider_diagnostics, diagnostics_to_text
from src.assets.semantic_visual_evaluation import run_semantic_visual_evaluation
from src.assets.semantic_visual_openai import openai_backend_diagnostics
from src.assets.semantic_visual_service import analyse_semantic_visual_for_project, inspect_semantic_visual_project
from src.assets.visual_preview import inspect_visual_preview_project, prepare_visual_preview_for_project
from src.media_library import analyse_media_library, clean_temp_files, create_asset_report, ensure_media_library, index_existing_assets, migrate_media_library
from src.production_catalog.cli import run_production_catalog_cli
from src.providers.envato_manual_provider import EnvatoManualProvider
from scripts.test_moss_voices import main as run_moss_voice_tests
from src.audio.voice_cli import run_voice_cli
from src.news.pipeline import run_news_to_short_cli
from src.production_plan.solar_vs_nuclear_render import build_solar_vs_nuclear_video
from src.production_plan.youtube_shorts import create_solar_vs_nuclear_plan


def configure_console_encoding() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Structured AI-YouTube pipeline")
    parser.add_argument(
        "command",
        nargs="?",
        choices=[
            "media-library",
            "provider-diagnostics",
            "envato-manual",
            "visual-preview",
            "semantic-visual",
            "semantic-backend",
            "applications",
            "formats",
            "templates",
            "export-targets",
        ],
        help="Optional maintenance command.",
    )
    parser.add_argument("subcommand", nargs="?", help="Maintenance subcommand, for example analyse or migrate.")
    parser.add_argument("--workspace", default=None, help="Runtime workspace root.")
    parser.add_argument("--paths-config", default=None, help="Optional JSON path configuration.")
    parser.add_argument("--config", default=None, help="Path to base video style config.")
    parser.add_argument(
        "--obsidian-vault",
        default=None,
        help="Optional Obsidian vault root (or set AI_YOUTUBE_OBSIDIAN_VAULT).",
    )
    parser.add_argument("--channel", help="Channel profile id, for example quotes.")
    parser.add_argument("--video", help="Video task id, for example thoughts_too_late_001.")
    parser.add_argument("--dev", action="store_true", help="Build a fast preview render.")
    parser.add_argument("--prod", action="store_true", help="Use production render settings.")
    parser.add_argument("--prod-preview", action="store_true", help="Run production settings on the first scenes.")
    parser.add_argument("--cinematic-preview", action="store_true", help="Render a higher-quality cinematic documentary preview.")
    parser.add_argument("--export-obsidian", action="store_true", help="Only export an Obsidian note from existing outputs.")
    parser.add_argument("--no-obsidian", action="store_true", help="Disable Obsidian export for this run.")
    parser.add_argument("--skip-render", action="store_true", help="Skip render and update only plans/metadata/Obsidian.")
    parser.add_argument("--find-music", action="store_true", help="Update only music_plan.json.")
    parser.add_argument("--refresh-assets", action="store_true", help="Search/download assets again.")
    parser.add_argument("--index-assets", action="store_true", help="Scan assets/library and update media_index.json.")
    parser.add_argument("--clean-temp", action="store_true", help="Remove render_temp and partial temporary files.")
    parser.add_argument("--asset-report", action="store_true", help="Create outputs/asset_library_report.md.")
    parser.add_argument("--test-moss-tts", action="store_true", help="Generate a short Russian audio sample with MOSS-TTS-Nano.")
    parser.add_argument("--test-moss-voices", action="store_true", help="Generate MOSS-TTS-Nano voice-clone tests for local reference samples.")
    parser.add_argument("--reuse-voice", action="store_true", default=True, help="Reuse cached scene voice files when text/settings match.")
    parser.add_argument("--skip-voice", action="store_true", help="Skip voice generation and render with music/subtitles only.")
    parser.add_argument("--news-to-short", action="store_true", help="Run the news_to_short mode instead of the legacy pipeline.")
    parser.add_argument("--news-action", choices=["create", "run", "resume"], default="create", help="news_to_short action.")
    parser.add_argument("--projects-root", default=None, help="Root folder for news_to_short jobs.")
    parser.add_argument("--job-id", help="Existing news_to_short job id for run/resume.")
    parser.add_argument("--news-channel", default="nature_science_news_ru", help="Channel profile for news_to_short.")
    parser.add_argument("--url", help="Article URL for news_to_short.")
    parser.add_argument("--urls", action="append", help="Additional article URL for news_to_short.")
    parser.add_argument("--topic", help="Topic or idea for news_to_short.")
    parser.add_argument("--text", help="Inline text input for news_to_short.")
    parser.add_argument("--text-file", help="Text file input for news_to_short.")
    parser.add_argument("--assets", action="append", help="User-owned image/video/audio asset for news_to_short.")
    parser.add_argument("--language", default="ru", help="Localization language for news_to_short.")
    parser.add_argument("--target-duration", type=int, default=55, help="Target duration in seconds for news_to_short.")
    parser.add_argument("--until-stage", help="Run news_to_short until this stage.")
    parser.add_argument("--stage", help="Run only one news_to_short stage.")
    parser.add_argument("--resume", action="store_true", help="Resume a news_to_short job.")
    parser.add_argument("--force-stage", action="store_true", help="Force regeneration of the requested news_to_short stage.")
    parser.add_argument("--dry-run", action="store_true", help="Create cheap news_to_short artifacts without paid APIs or heavy downloads.")
    parser.add_argument(
        "--completion-mode",
        choices=["strict", "draft_complete"],
        default="",
        help="strict (default) or opt-in autonomous draft completion.",
    )
    parser.add_argument(
        "--script-adaptation",
        choices=["none", "light"],
        default="",
        help="Asset-aware script adaptation; empty keeps the project/default setting.",
    )
    parser.add_argument(
        "--execute-voice",
        action="store_true",
        help="Allow the news_to_short voice stage to run real generation. Still requires an existing approval record; without one the safe stub manifest is produced.",
    )
    parser.add_argument("--live", action="store_true", help="Run explicit live diagnostics where supported.")
    parser.add_argument("--open-browser", action="store_true", help="Open Envato public search URL after explicit user request.")
    parser.add_argument("--query", action="append", help="Manual provider query; can be passed more than once.")
    parser.add_argument("--limit", type=int, default=6, help="Manual provider query/result limit.")
    parser.add_argument("--top-k", type=int, default=5, help="Visual preview metadata shortlist size.")
    parser.add_argument("--all-scenes", action="store_true", help="Prepare visual previews for all known scenes.")
    parser.add_argument("--refresh", action="store_true", help="Refresh visual preview cache records.")
    parser.add_argument("--technical-rerank", action="store_true", help="Enable deterministic technical reranking for visual preview.")
    parser.add_argument("--target-aspect", default="9:16", help="Target aspect ratio for visual preview analysis.")
    parser.add_argument("--no-html", action="store_true", help="Skip static HTML visual preview board generation.")
    parser.add_argument("--offline", action="store_true", help="Use cached/local preview assets only.")
    parser.add_argument("--backend", default="", help="Semantic visual backend name for semantic-visual commands.")
    parser.add_argument("--model", default="", help="Semantic backend model for diagnostics/evaluation.")
    parser.add_argument("--dataset", default="", help="Explicit semantic backend evaluation dataset path.")
    parser.add_argument("--allow-paid-vision", action="store_true", help="Future explicit paid Vision gate. Does not enable live calls alone.")
    parser.add_argument("--budget-usd", type=float, default=0.0, help="Future explicit paid Vision budget gate.")
    parser.add_argument("--max-calls", type=int, default=0, help="Future explicit paid Vision call-limit gate.")
    parser.add_argument("--confirm-paid-vision", default="", help="Future explicit paid Vision confirmation phrase.")
    parser.add_argument("--mocked", action="store_true", help="Run semantic backend evaluation using mocked provider responses.")
    parser.add_argument("--maximum-candidates", type=int, help="Maximum candidates for semantic visual analysis.")
    parser.add_argument("--maximum-frames", type=int, help="Maximum sampled frames per candidate for semantic visual analysis.")
    parser.add_argument("--project-id", help="Project id for manual provider commands.")
    parser.add_argument("--scene-id", help="Scene id for manual provider commands.")
    parser.add_argument("--file", help="Local file to import for manual provider commands.")
    parser.add_argument("--source-url", help="Source item URL for manual provider import.")
    parser.add_argument("--item-id", help="Provider item id for manual provider import.")
    parser.add_argument("--author", help="Provider author for manual provider import.")
    parser.add_argument("--license-proof", help="Local certificate/proof file for manual provider import.")
    parser.add_argument("--confirm-project-registration", action="store_true", help="Confirm manual asset is registered to this project.")
    parser.add_argument("--apply", dest="apply_migration", action="store_true", help="Apply media-library migration with explicit safeguards.")
    parser.add_argument("--index-path", help="Media-library index path for analyse/migrate commands.")
    parser.add_argument("--output-path", help="Output path for proposed migrated media index.")
    parser.add_argument("--report-path", help="Output path for media-library analyse/migration report.")
    parser.add_argument("--backup-path", help="Backup path required for media-library migrate --apply.")
    parser.add_argument("--confirm-apply", action="store_true", help="Required with media-library migrate --apply.")
    parser.add_argument("--voice-action", choices=["list", "inspect", "preflight", "import-audio", "approve", "audition"], help="Run safe voice catalog/preflight commands.")
    parser.add_argument("--voice-profile", help="Saved local voice profile id, for example ru_dom.")
    parser.add_argument("--voice-id", help="Provider voice id for voice inspect/preflight.")
    parser.add_argument("--provider", help="Voice provider name for voice commands.")
    parser.add_argument("--audio-file", help="Manual WAV narration file for --voice-action import-audio.")
    parser.add_argument("--approval-scope", choices=["once", "job", "channel_voice_default"], default="job", help="Voice approval scope.")
    parser.add_argument("--application", help="Application id for applications/templates catalog commands.")
    parser.add_argument("--format", help="Format id for formats/templates catalog commands.")
    parser.add_argument("--template", help="Template id or legacy alias for templates inspect.")
    parser.add_argument("--target", help="Export target id for export-targets inspect.")
    parser.add_argument("--json", dest="json_output", action="store_true", help="Print machine-readable JSON for read-only catalog commands.")
    parser.add_argument("--production-plan", choices=["solar_vs_nuclear"], help="Create a reusable YouTube Shorts production plan.")
    parser.add_argument("--production-plan-root", default=None, help="Folder where the production plan project folder will be created.")
    parser.add_argument("--render-production-plan", help="Render an existing production plan project folder.")
    return parser.parse_args(argv)


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
    args.config = args.config or str(application_paths.config_root / "video_style.json")
    args.production_plan_root = args.production_plan_root or str(application_paths.repository_root)
    assets_root = application_paths.workspace.media_library.parent
    ensure_dir(application_paths.outputs_root)
    ensure_dir(assets_root / "images")
    ensure_dir(assets_root / "images" / "generated")
    ensure_media_library(application_paths.workspace.media_library)

    if args.command == "provider-diagnostics":
        diagnostics = collect_provider_diagnostics(live=args.live, provider=args.provider)
        print(diagnostics_to_text(diagnostics))
        return

    if args.command == "visual-preview":
        if not args.project_id:
            raise SystemExit("visual-preview requires --project-id.")
        project_root = application_paths.find_project_root(args.project_id)
        if args.subcommand == "prepare":
            if not args.scene_id and not args.all_scenes:
                raise SystemExit("visual-preview prepare requires --scene-id or --all-scenes.")
            result = prepare_visual_preview_for_project(
                project_root=project_root,
                project_id=args.project_id,
                scene_id=args.scene_id or "",
                all_scenes=args.all_scenes,
                top_k=args.top_k,
                refresh=args.refresh,
                technical_rerank=args.technical_rerank,
                target_aspect_ratio=args.target_aspect,
                no_html=args.no_html,
                offline=args.offline,
            )
            print(f"[visual-preview] status={result['status']}")
            print(f"[visual-preview] scenes={result['scene_count']}")
            print(f"[visual-preview] manifest={result.get('json_path', '')}")
            if result.get("html_path"):
                print(f"[visual-preview] html={result['html_path']}")
            return
        if args.subcommand == "inspect":
            summary = inspect_visual_preview_project(project_root)
            for key in (
                "scene_count",
                "analysed_candidates",
                "preview_cache_hits",
                "preview_cache_misses",
                "failed_previews",
                "exact_duplicates",
                "near_duplicates",
                "review_required_candidates",
                "selected_candidates",
                "missing_scenes",
                "html_board_path",
            ):
                print(f"[visual-preview] {key}={summary.get(key, '')}")
            return
        raise SystemExit("visual-preview requires subcommand: prepare or inspect.")

    if args.command == "semantic-backend":
        backend_name = args.backend or "openai"
        if args.subcommand == "diagnostics":
            if backend_name != "openai":
                raise SystemExit("semantic-backend diagnostics currently supports --backend openai.")
            diagnostics = openai_backend_diagnostics()
            for key in (
                "configured",
                "key_configured",
                "enabled",
                "primary_model",
                "comparison_model",
                "detail_policy",
                "paid_calls_allowed",
                "budget_usd",
                "call_limit",
                "live_status",
            ):
                value = diagnostics.get(key)
                if isinstance(value, (dict, list)):
                    value = json.dumps(value, ensure_ascii=False, sort_keys=True)
                print(f"[semantic-backend] {key}={value}")
            return
        if args.subcommand == "evaluate":
            config_overrides = {
                "allow_paid_vision_cli": bool(args.allow_paid_vision),
                "budget_usd_cli": float(args.budget_usd or 0.0),
                "max_calls_cli": int(args.max_calls or 0),
                "confirm_paid_vision": str(args.confirm_paid_vision or ""),
            }
            result = run_semantic_visual_evaluation(
                backend=backend_name,
                model=args.model or "gpt-5.6-terra",
                dry_run=bool(args.dry_run),
                mocked=bool(args.mocked),
                config=config_overrides,
                dataset_path=args.dataset or None,
            )
            metrics = result.get("metrics") if isinstance(result.get("metrics"), dict) else {}
            for key in (
                "status",
                "backend",
                "model",
                "dry_run",
                "mocked",
                "dataset_path",
                "scenes",
                "candidates",
                "dataset_cases",
                "projected_calls",
                "projected_image_count",
                "requests_built",
                "valid_requests",
                "invalid_requests",
                "schema_valid",
                "runtime_authorized",
                "runtime_block_reasons",
                "budget_allowed",
                "live_blocked_reasons",
                "calls_attempted",
                "calls_succeeded",
                "calls_failed",
                "external_http_attempts",
                "images_sent",
                "retries_observed",
                "total_input_tokens",
                "total_output_tokens",
                "total_cached_tokens",
                "total_calculated_cost_usd",
                "budget_exceeded",
                "semantic_rerank_enabled",
                "production_selection_changed",
                "stop_reasons",
                "paid_calls_performed",
                "live_vision_calls_performed",
                "results_dir",
                "report_path",
                "comparison_path",
                "checkpoint_path",
            ):
                if key not in result:
                    continue
                value = result.get(key)
                if isinstance(value, list):
                    value = ",".join(str(item) for item in value)
                print(f"[semantic-backend] {key}={value}")
            for key in sorted(metrics):
                print(f"[semantic-backend] {key}={metrics[key]}")
            return
        raise SystemExit("semantic-backend requires subcommand: diagnostics or evaluate.")

    if args.command == "semantic-visual":
        if not args.project_id:
            raise SystemExit("semantic-visual requires --project-id.")
        project_root = application_paths.find_project_root(args.project_id)
        if args.subcommand == "analyse":
            if not args.scene_id and not args.all_scenes:
                raise SystemExit("semantic-visual analyse requires --scene-id or --all-scenes.")
            result = analyse_semantic_visual_for_project(
                project_root=project_root,
                project_id=args.project_id,
                scene_id=args.scene_id or "",
                all_scenes=args.all_scenes,
                backend_name=args.backend or "mock",
                refresh=args.refresh,
                offline=args.offline,
                maximum_candidates=args.maximum_candidates,
                maximum_frames=args.maximum_frames,
                no_html=args.no_html,
            )
            for key in (
                "status",
                "scenes_processed",
                "candidates_processed",
                "cache_hits",
                "cache_misses",
                "backend_calls",
                "successful_analyses",
                "failed_analyses",
                "hard_rejects",
                "review_required",
                "estimated_cost",
                "paid_calls_performed",
                "manifest_path",
                "html_path",
            ):
                print(f"[semantic-visual] {key}={result.get(key, '')}")
            return
        if args.subcommand == "inspect":
            summary = inspect_semantic_visual_project(project_root)
            for key in (
                "scenes",
                "analysed_candidates",
                "cache_hits",
                "cache_misses",
                "successful",
                "failed",
                "hard_rejects",
                "review_required",
                "backend",
                "paid_calls",
                "review_manifest_path",
                "html_board_path",
            ):
                print(f"[semantic-visual] {key}={summary.get(key, '')}")
            return
        raise SystemExit("semantic-visual requires subcommand: analyse or inspect.")

    if args.command in ("applications", "formats", "templates", "export-targets"):
        raise SystemExit(run_production_catalog_cli(args))

    if args.command == "envato-manual":
        if not args.project_id or not args.scene_id:
            raise SystemExit("envato-manual requires --project-id and --scene-id.")
        provider = EnvatoManualProvider(
            projects_root=application_paths.find_project_root(args.project_id).parent
        )
        if args.subcommand == "prepare":
            manifest = provider.prepare_request(
                project_id=args.project_id,
                scene_id=args.scene_id,
                scene={"primary_query": " ".join(args.query or [])},
                queries=args.query,
                limit=args.limit,
                open_browser=args.open_browser,
            )
            print(f"[envato-manual] scene_id={manifest['scene_id']}")
            print(f"[envato-manual] semantic_description={manifest['semantic_description']}")
            print(f"[envato-manual] destination_import_folder={manifest['destination_import_folder']}")
            print("[envato-manual] search_queries=" + json.dumps(manifest["search_queries"], ensure_ascii=False))
            print("[envato-manual] search_urls=" + json.dumps(manifest["search_urls"], ensure_ascii=False))
            print("[envato-manual] required_metadata_checklist=" + json.dumps(manifest["required_metadata_checklist"], ensure_ascii=False))
            return
        if args.subcommand == "import":
            missing = [
                name
                for name, value in {
                    "--file": args.file,
                    "--source-url": args.source_url,
                    "--item-id": args.item_id,
                    "--author": args.author,
                    "--license-proof": args.license_proof,
                }.items()
                if not value
            ]
            if missing:
                raise SystemExit("envato-manual import missing required option(s): " + ", ".join(missing))
            imported = provider.import_asset(
                project_id=args.project_id,
                scene_id=args.scene_id,
                file=args.file,
                source_url=args.source_url,
                item_id=args.item_id,
                author=args.author,
                license_proof=args.license_proof,
                confirm_project_registration=args.confirm_project_registration,
            )
            print(f"[envato-manual] import_status={'allowed' if imported.license.allowed_for_render and not imported.license.review_required else 'review_required'}")
            print(f"[envato-manual] local_path={imported.local_path}")
            print(f"[envato-manual] checksum_sha256={imported.checksum_sha256}")
            print(f"[envato-manual] policy_reason={imported.policy_decision.get('reason', '')}")
            return
        raise SystemExit("envato-manual requires subcommand: prepare or import.")

    if args.command == "media-library":
        media_index_path = (
            application_paths.workspace.media_library / "metadata" / "media_index.json"
        )
        if args.subcommand == "analyse":
            report = analyse_media_library(
                index_path=args.index_path or media_index_path,
                report_path=args.report_path,
            )
            print(f"[media-library] records_total={report['records_total']}")
            print(f"[media-library] safe_records={report['safe_records']}")
            print(f"[media-library] review_records={report['review_records']}")
            print(f"[media-library] quarantine_records={report['quarantine_records']}")
            return
        if args.subcommand == "migrate":
            result = migrate_media_library(
                index_path=args.index_path or media_index_path,
                dry_run=args.dry_run and not args.apply_migration,
                apply=args.apply_migration,
                output_path=args.output_path,
                report_path=args.report_path,
                backup_path=args.backup_path,
                confirm_apply=args.confirm_apply,
            )
            print(f"[media-library] dry_run={result['dry_run']}")
            print(f"[media-library] applied={result['applied']}")
            print(f"[media-library] records_total={result['records_total']}")
            print(f"[media-library] safe_records={result['safe_records']}")
            print(f"[media-library] review_records={result['review_records']}")
            print(f"[media-library] quarantine_records={result['quarantine_records']}")
            return
        raise SystemExit("media-library requires subcommand: analyse or migrate.")

    if args.voice_action:
        if args.job_id:
            args.projects_root = str(
                application_paths.find_project_root(args.job_id).parent
            )
        raise SystemExit(run_voice_cli(args))

    if args.production_plan == "solar_vs_nuclear":
        project = create_solar_vs_nuclear_plan(args.production_plan_root)
        print(f"[production-plan] project_id={project['config']['project_id']}")
        print(f"[production-plan] root={project['root']}")
        print(f"[production-plan] readiness={project['readiness']['status']}")
        print(f"[production-plan] preview={project['root'] / 'preview.html'}")
        return

    if args.render_production_plan:
        result = build_solar_vs_nuclear_video(args.render_production_plan)
        print(f"[production-render] status={result['status']}")
        if result["status"] == "completed":
            print(f"[production-render] output={result['render']['output_path']}")
        else:
            print(f"[production-render] errors={', '.join(result['readiness'].get('errors', []))}")
        return

    if args.news_to_short:
        if args.job_id and (args.news_action in {"run", "resume"} or args.resume):
            args.projects_root = str(
                application_paths.find_project_root(args.job_id).parent
            )
        result = run_news_to_short_cli(args)
        print(f"[news-to-short] job_id={result.job_id}")
        print(f"[news-to-short] status={result.status}")
        print(f"[news-to-short] project={result.project_root}")
        if result.completed_stages:
            print(f"[news-to-short] completed_stages={', '.join(result.completed_stages)}")
        return

    if args.index_assets:
        index = index_existing_assets(
            library_root=application_paths.workspace.media_library,
            index_path=application_paths.workspace.media_library
            / "metadata"
            / "media_index.json",
        )
        print(f"[assets] Indexed media library items: {len(index.get('items', []))}")
        return
    if args.clean_temp:
        removed = clean_temp_files([application_paths.outputs_root / "render_temp"])
        print(f"[cleanup] Removed temp paths: {len(removed)}")
        return
    if args.asset_report:
        report_path = create_asset_report(
            index_path=application_paths.workspace.media_library
            / "metadata"
            / "media_index.json",
            output_path=application_paths.outputs_root / "asset_library_report.md",
        )
        print(f"[assets] Report created: {report_path}")
        return
    if args.test_moss_tts:
        config = load_config(
            args.config,
            dev=args.dev,
            prod=args.prod,
            prod_preview=args.prod_preview,
            cinematic_preview=args.cinematic_preview,
            outputs_root=application_paths.outputs_root,
        )
        try:
            output_path = run_test_synthesis(config)
        except MossTtsProviderError as exc:
            raise SystemExit(f"[moss-tts] {exc}") from exc
        print(f"[moss-tts] Test audio created: {output_path}")
        return
    if args.test_moss_voices:
        raise SystemExit(run_moss_voice_tests())

    config = load_config(
        args.config,
        dev=args.dev,
        prod=args.prod,
        prod_preview=args.prod_preview,
        cinematic_preview=args.cinematic_preview,
        outputs_root=application_paths.outputs_root,
    )
    if args.channel or args.video:
        if not args.channel or not args.video:
            raise SystemExit("--channel and --video must be passed together.")
        config = load_channel_video_config(
            config,
            args.channel,
            args.video,
            application_paths=application_paths,
            obsidian_vault=args.obsidian_vault,
        )
    plans = config["plans"]
    print(
        f"[config] Loaded {args.config} | channel={config.get('channel_id', 'default')} "
        f"| video={config.get('video_id', 'default')} | dev_mode={config['dev_mode']} "
        f"| prod_preview={config.get('prod_preview', False)} | cinematic_preview={config.get('cinematic_preview', False)}"
    )

    if config.get("video_type") == "cinematic_size_comparison":
        vault_path = str(config.get("obsidian", {}).get("vault_path") or "").rstrip("/\\")
        note_folder = (
            f"YouTube/02 Видео/Size Comparison/"
            f"{config.get('video_id', 'sea_monsters_001')}"
        )
        config["obsidian"] = {
            **config.get("obsidian", {}),
            "folder": note_folder,
            "video_note_dir": f"{vault_path}/{note_folder}" if vault_path else "",
        }
        result = run_size_comparison_pipeline(config, skip_render=args.skip_render)
        print(f"[size-comparison] Output file: {result['output_path']}")
        print(f"[size-comparison] Obsidian note: {result['obsidian_note']}")
        for item in result["self_eval"].get("checks", []):
            print(f"[self-eval] OK: {item}")
        for item in result["self_eval"].get("warnings", []):
            print(f"[self-eval] Note: {item}")
        return

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
    voice_manifest = build_voice_manifest(config, scene_plan, reuse_voice=args.reuse_voice, skip_voice=args.skip_voice)
    config["voice_manifest"] = voice_manifest
    scene_plan = apply_voice_timing_to_scene_plan(scene_plan, voice_manifest, cinematic_preview=bool(config.get("cinematic_preview", False)))
    voice_manifest = align_voice_manifest_to_scene_plan(voice_manifest, scene_plan)
    config["voice_manifest"] = voice_manifest
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
    write_json(plans.get("voice_manifest", "outputs/voice_manifest.json"), voice_manifest)
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
            eval_result = evaluate_render(output_path, config, asset_plan, scene_plan, music_plan, metadata, render_plan=render_plan)
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
        eval_result = evaluate_render(output_path, config, asset_plan, scene_plan, music_plan, metadata, note_path, render_plan=render_plan)
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
