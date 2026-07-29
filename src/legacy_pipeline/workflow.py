from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


CompatibilityNamespace = Mapping[str, Any]


@dataclass(frozen=True)
class LegacyPipelineArtifacts:
    plans: dict[str, Any]
    quote_plan: dict[str, Any]
    metadata: dict[str, Any]
    scene_plan: dict[str, Any]
    music_plan: dict[str, Any]
    asset_plan: dict[str, Any]
    render_plan: dict[str, Any]


def run_legacy_video_pipeline(
    args: Any,
    application_paths: Any,
    compatibility: CompatibilityNamespace,
) -> None:
    """Run the historical channel/video workflow behind the root facade."""

    config = _load_legacy_config(args, application_paths, compatibility)
    if _run_config_action(args, config, compatibility):
        return

    artifacts = _build_pipeline_artifacts(args, config, compatibility)
    output_path, render_completed = _render_or_skip(
        args,
        config,
        artifacts,
        compatibility,
    )
    if not render_completed:
        return

    note_path = _export_obsidian(args, config, compatibility)
    if not args.skip_render:
        _run_final_evaluation(
            config,
            artifacts,
            output_path,
            note_path,
            compatibility,
        )
    print(
        f"[metadata] Created "
        f"{artifacts.plans.get('youtube_metadata', 'outputs/youtube_metadata.json')}, "
        f"chosen title: {artifacts.metadata.get('chosen_title')}"
    )


def _load_legacy_config(
    args: Any,
    application_paths: Any,
    compatibility: CompatibilityNamespace,
) -> dict[str, Any]:
    config = compatibility["load_config"](
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
        config = compatibility["load_channel_video_config"](
            config,
            args.channel,
            args.video,
            application_paths=application_paths,
            obsidian_vault=args.obsidian_vault,
        )
    print(
        f"[config] Loaded {args.config} | channel={config.get('channel_id', 'default')} "
        f"| video={config.get('video_id', 'default')} | dev_mode={config['dev_mode']} "
        f"| prod_preview={config.get('prod_preview', False)} "
        f"| cinematic_preview={config.get('cinematic_preview', False)}"
    )
    return config


def _run_config_action(
    args: Any,
    config: dict[str, Any],
    compatibility: CompatibilityNamespace,
) -> bool:
    if config.get("video_type") == "cinematic_size_comparison":
        _run_size_comparison(args, config, compatibility)
        return True
    if args.find_music:
        music_plan = compatibility["build_music_plan"](config)
        print(f"[music] Music plan updated: {music_plan.get('status')}")
        return True
    if args.export_obsidian:
        note_path = compatibility["export_obsidian_note"](config)
        print(f"[obsidian] Note exported: {note_path}")
        return True
    return False


def _run_size_comparison(
    args: Any,
    config: dict[str, Any],
    compatibility: CompatibilityNamespace,
) -> None:
    vault_path = str(config.get("obsidian", {}).get("vault_path") or "").rstrip(
        "/\\"
    )
    note_folder = (
        f"YouTube/02 Видео/Size Comparison/"
        f"{config.get('video_id', 'sea_monsters_001')}"
    )
    config["obsidian"] = {
        **config.get("obsidian", {}),
        "folder": note_folder,
        "video_note_dir": f"{vault_path}/{note_folder}" if vault_path else "",
    }
    result = compatibility["run_size_comparison_pipeline"](
        config,
        skip_render=args.skip_render,
    )
    print(f"[size-comparison] Output file: {result['output_path']}")
    print(f"[size-comparison] Obsidian note: {result['obsidian_note']}")
    for item in result["self_eval"].get("checks", []):
        print(f"[self-eval] OK: {item}")
    for item in result["self_eval"].get("warnings", []):
        print(f"[self-eval] Note: {item}")


def _build_pipeline_artifacts(
    args: Any,
    config: dict[str, Any],
    compatibility: CompatibilityNamespace,
) -> LegacyPipelineArtifacts:
    plans = config["plans"]
    quote_plan = compatibility["build_quote_plan"](config)
    metadata = compatibility["write_youtube_metadata"](
        config,
        quote_plan,
        output_path=plans.get(
            "youtube_metadata",
            "outputs/youtube_metadata.json",
        ),
    )
    scene_plan = compatibility["build_scene_plan"](
        config,
        quote_plan,
        metadata,
    )
    if args.prod_preview:
        scene_plan = compatibility["limit_scene_plan"](
            scene_plan,
            int(config.get("prod_preview_scene_count", 5)),
        )
    voice_manifest = compatibility["build_voice_manifest"](
        config,
        scene_plan,
        reuse_voice=args.reuse_voice,
        skip_voice=args.skip_voice,
    )
    config["voice_manifest"] = voice_manifest
    scene_plan = compatibility["apply_voice_timing_to_scene_plan"](
        scene_plan,
        voice_manifest,
        cinematic_preview=bool(config.get("cinematic_preview", False)),
    )
    voice_manifest = compatibility["align_voice_manifest_to_scene_plan"](
        voice_manifest,
        scene_plan,
    )
    config["voice_manifest"] = voice_manifest
    intro_plan = compatibility["build_intro_plan"](config, metadata)
    music_plan = compatibility["build_music_plan"](config, scene_plan)
    asset_plan = compatibility["build_asset_plan"](
        config,
        scene_plan,
        refresh=args.refresh_assets,
    )
    render_plan = compatibility["build_render_plan"](
        config,
        scene_plan,
        asset_plan,
        music_plan,
    )
    _write_pipeline_artifacts(
        config,
        plans,
        quote_plan,
        metadata,
        scene_plan,
        voice_manifest,
        intro_plan,
        music_plan,
        asset_plan,
        render_plan,
        compatibility,
    )
    return LegacyPipelineArtifacts(
        plans=plans,
        quote_plan=quote_plan,
        metadata=metadata,
        scene_plan=scene_plan,
        music_plan=music_plan,
        asset_plan=asset_plan,
        render_plan=render_plan,
    )


def _write_pipeline_artifacts(
    config: dict[str, Any],
    plans: dict[str, Any],
    quote_plan: dict[str, Any],
    metadata: dict[str, Any],
    scene_plan: dict[str, Any],
    voice_manifest: dict[str, Any],
    intro_plan: dict[str, Any],
    music_plan: dict[str, Any],
    asset_plan: dict[str, Any],
    render_plan: dict[str, Any],
    compatibility: CompatibilityNamespace,
) -> None:
    if config.get("video_task"):
        thumbnail_path = compatibility["create_thumbnail"](config, asset_plan)
        metadata["thumbnail_path"] = str(thumbnail_path)
        compatibility["write_json"](
            plans.get("youtube_metadata", "outputs/youtube_metadata.json"),
            metadata,
        )
    compatibility["write_json"](plans["quote_plan"], quote_plan)
    compatibility["write_json"](plans["scene_plan"], scene_plan)
    compatibility["write_json"](plans["asset_plan"], asset_plan)
    compatibility["write_json"](
        plans["render_plan"],
        {**render_plan, "intro": intro_plan},
    )
    compatibility["write_json"](
        plans.get("music_plan", "outputs/music_plan.json"),
        music_plan,
    )
    compatibility["write_json"](
        plans.get("voice_manifest", "outputs/voice_manifest.json"),
        voice_manifest,
    )
    print(
        "[plans] Created quote_plan, scene_plan, asset_plan, "
        "render_plan, music_plan"
    )


def _render_or_skip(
    args: Any,
    config: dict[str, Any],
    artifacts: LegacyPipelineArtifacts,
    compatibility: CompatibilityNamespace,
) -> tuple[Any, bool]:
    output_path = artifacts.render_plan["output_path"]
    if args.skip_render:
        eval_result = {
            "ok": True,
            "checks": ["Render skipped via --skip-render."],
            "warnings": [],
        }
        compatibility["write_json"](
            artifacts.plans.get("self_eval", "outputs/self_eval.json"),
            eval_result,
        )
        print("[render] Skipped via --skip-render")
        return output_path, True

    render_stage_error = compatibility["RenderStageError"]
    try:
        output_path = compatibility["render_video"](
            config,
            artifacts.scene_plan,
            artifacts.asset_plan,
            artifacts.render_plan,
            artifacts.music_plan,
        )
        eval_result = compatibility["evaluate_render"](
            output_path,
            config,
            artifacts.asset_plan,
            artifacts.scene_plan,
            artifacts.music_plan,
            artifacts.metadata,
            render_plan=artifacts.render_plan,
        )
        compatibility["write_json"](
            artifacts.plans.get("self_eval", "outputs/self_eval.json"),
            eval_result,
        )
        print(f"[render] Output file: {output_path}")
        return output_path, True
    except render_stage_error as exc:
        _record_render_failure(exc, artifacts.plans, compatibility)
        return output_path, False


def _record_render_failure(
    error: Any,
    plans: dict[str, Any],
    compatibility: CompatibilityNamespace,
) -> None:
    eval_result = {
        "ok": False,
        "checks": [],
        "warnings": [
            f"Render stopped at stage {error.stage}: {error.message}",
            "Music was not added because silent video did not pass the safe "
            "render/validate pipeline.",
        ],
    }
    compatibility["write_json"](
        plans.get("self_eval", "outputs/self_eval.json"),
        eval_result,
    )
    print(f"[render] Stage error {error.stage}: {error.message}")


def _export_obsidian(
    args: Any,
    config: dict[str, Any],
    compatibility: CompatibilityNamespace,
) -> Any:
    note_path = None
    obsidian_enabled = config.get("obsidian", {}).get("enabled", False)
    if obsidian_enabled and not args.no_obsidian:
        note_path = compatibility["export_obsidian_note"](config)
        print(f"[obsidian] Note exported: {note_path}")
    elif args.no_obsidian:
        print("[obsidian] Skipped via --no-obsidian")
    return note_path


def _run_final_evaluation(
    config: dict[str, Any],
    artifacts: LegacyPipelineArtifacts,
    output_path: Any,
    note_path: Any,
    compatibility: CompatibilityNamespace,
) -> None:
    eval_result = compatibility["evaluate_render"](
        output_path,
        config,
        artifacts.asset_plan,
        artifacts.scene_plan,
        artifacts.music_plan,
        artifacts.metadata,
        note_path,
        render_plan=artifacts.render_plan,
    )
    compatibility["write_json"](
        artifacts.plans.get("self_eval", "outputs/self_eval.json"),
        eval_result,
    )
    if note_path:
        compatibility["export_obsidian_note"](config)
    for item in eval_result["checks"]:
        print(f"[self-eval] OK: {item}")
    for item in eval_result["warnings"]:
        print(f"[self-eval] Note: {item}")
