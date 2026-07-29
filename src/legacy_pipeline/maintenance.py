from __future__ import annotations

import json
from typing import Any, Mapping


CompatibilityNamespace = Mapping[str, Any]


def run_maintenance_command(
    args: Any,
    application_paths: Any,
    compatibility: CompatibilityNamespace,
) -> bool:
    """Dispatch root-pipeline maintenance modes.

    Dependencies come from the root module namespace so historical monkeypatch
    points such as ``pipeline.run_production_catalog_cli`` remain effective.
    """

    if args.command == "provider-diagnostics":
        diagnostics = compatibility["collect_provider_diagnostics"](
            live=args.live,
            provider=args.provider,
        )
        print(compatibility["diagnostics_to_text"](diagnostics))
        return True
    if args.command == "visual-preview":
        _run_visual_preview(args, application_paths, compatibility)
        return True
    if args.command == "semantic-backend":
        _run_semantic_backend(args, compatibility)
        return True
    if args.command == "semantic-visual":
        _run_semantic_visual(args, application_paths, compatibility)
        return True
    if args.command in ("applications", "formats", "templates", "export-targets"):
        raise SystemExit(compatibility["run_production_catalog_cli"](args))
    if args.command == "envato-manual":
        _run_envato_manual(args, application_paths, compatibility)
        return True
    if args.command == "media-library":
        _run_media_library(args, application_paths, compatibility)
        return True
    return _run_legacy_action(args, application_paths, compatibility)


def _run_visual_preview(
    args: Any,
    application_paths: Any,
    compatibility: CompatibilityNamespace,
) -> None:
    if not args.project_id:
        raise SystemExit("visual-preview requires --project-id.")
    project_root = application_paths.find_project_root(args.project_id)
    if args.subcommand == "prepare":
        if not args.scene_id and not args.all_scenes:
            raise SystemExit("visual-preview prepare requires --scene-id or --all-scenes.")
        result = compatibility["prepare_visual_preview_for_project"](
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
        summary = compatibility["inspect_visual_preview_project"](project_root)
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


def _run_semantic_backend(
    args: Any,
    compatibility: CompatibilityNamespace,
) -> None:
    backend_name = args.backend or "openai"
    if args.subcommand == "diagnostics":
        if backend_name != "openai":
            raise SystemExit("semantic-backend diagnostics currently supports --backend openai.")
        diagnostics = compatibility["openai_backend_diagnostics"]()
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
        _run_semantic_evaluation(args, backend_name, compatibility)
        return
    raise SystemExit("semantic-backend requires subcommand: diagnostics or evaluate.")


def _run_semantic_evaluation(
    args: Any,
    backend_name: str,
    compatibility: CompatibilityNamespace,
) -> None:
    config_overrides = {
        "allow_paid_vision_cli": bool(args.allow_paid_vision),
        "budget_usd_cli": float(args.budget_usd or 0.0),
        "max_calls_cli": int(args.max_calls or 0),
        "confirm_paid_vision": str(args.confirm_paid_vision or ""),
    }
    result = compatibility["run_semantic_visual_evaluation"](
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


def _run_semantic_visual(
    args: Any,
    application_paths: Any,
    compatibility: CompatibilityNamespace,
) -> None:
    if not args.project_id:
        raise SystemExit("semantic-visual requires --project-id.")
    project_root = application_paths.find_project_root(args.project_id)
    if args.subcommand == "analyse":
        if not args.scene_id and not args.all_scenes:
            raise SystemExit("semantic-visual analyse requires --scene-id or --all-scenes.")
        result = compatibility["analyse_semantic_visual_for_project"](
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
        summary = compatibility["inspect_semantic_visual_project"](project_root)
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


def _run_envato_manual(
    args: Any,
    application_paths: Any,
    compatibility: CompatibilityNamespace,
) -> None:
    if not args.project_id or not args.scene_id:
        raise SystemExit("envato-manual requires --project-id and --scene-id.")
    provider = compatibility["EnvatoManualProvider"](
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
        _run_envato_import(args, provider)
        return
    raise SystemExit("envato-manual requires subcommand: prepare or import.")


def _run_envato_import(args: Any, provider: Any) -> None:
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
    import_status = (
        "allowed"
        if imported.license.allowed_for_render
        and not imported.license.review_required
        else "review_required"
    )
    print(f"[envato-manual] import_status={import_status}")
    print(f"[envato-manual] local_path={imported.local_path}")
    print(f"[envato-manual] checksum_sha256={imported.checksum_sha256}")
    print(f"[envato-manual] policy_reason={imported.policy_decision.get('reason', '')}")


def _run_media_library(
    args: Any,
    application_paths: Any,
    compatibility: CompatibilityNamespace,
) -> None:
    media_index_path = (
        application_paths.workspace.media_library / "metadata" / "media_index.json"
    )
    if args.subcommand == "analyse":
        report = compatibility["analyse_media_library"](
            index_path=args.index_path or media_index_path,
            report_path=args.report_path,
        )
        print(f"[media-library] records_total={report['records_total']}")
        print(f"[media-library] safe_records={report['safe_records']}")
        print(f"[media-library] review_records={report['review_records']}")
        print(f"[media-library] quarantine_records={report['quarantine_records']}")
        return
    if args.subcommand == "migrate":
        result = compatibility["migrate_media_library"](
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


def _run_legacy_action(
    args: Any,
    application_paths: Any,
    compatibility: CompatibilityNamespace,
) -> bool:
    if args.voice_action:
        if args.job_id:
            args.projects_root = str(
                application_paths.find_project_root(args.job_id).parent
            )
        raise SystemExit(compatibility["run_voice_cli"](args))
    if args.production_plan == "solar_vs_nuclear":
        project = compatibility["create_solar_vs_nuclear_plan"](
            args.production_plan_root
        )
        print(f"[production-plan] project_id={project['config']['project_id']}")
        print(f"[production-plan] root={project['root']}")
        print(f"[production-plan] readiness={project['readiness']['status']}")
        print(f"[production-plan] preview={project['root'] / 'preview.html'}")
        return True
    if args.render_production_plan:
        _run_production_plan_render(args, compatibility)
        return True
    if args.news_to_short:
        _run_news_to_short(args, application_paths, compatibility)
        return True
    if _run_media_action(args, application_paths, compatibility):
        return True
    return _run_moss_action(args, application_paths, compatibility)


def _run_production_plan_render(
    args: Any,
    compatibility: CompatibilityNamespace,
) -> None:
    result = compatibility["build_solar_vs_nuclear_video"](
        args.render_production_plan
    )
    print(f"[production-render] status={result['status']}")
    if result["status"] == "completed":
        print(f"[production-render] output={result['render']['output_path']}")
    else:
        print(
            "[production-render] errors="
            + ", ".join(result["readiness"].get("errors", []))
        )


def _run_news_to_short(
    args: Any,
    application_paths: Any,
    compatibility: CompatibilityNamespace,
) -> None:
    if args.job_id and (args.news_action in {"run", "resume"} or args.resume):
        args.projects_root = str(
            application_paths.find_project_root(args.job_id).parent
        )
    result = compatibility["run_news_to_short_cli"](args)
    print(f"[news-to-short] job_id={result.job_id}")
    print(f"[news-to-short] status={result.status}")
    print(f"[news-to-short] project={result.project_root}")
    if result.completed_stages:
        print(f"[news-to-short] completed_stages={', '.join(result.completed_stages)}")


def _run_media_action(
    args: Any,
    application_paths: Any,
    compatibility: CompatibilityNamespace,
) -> bool:
    if args.index_assets:
        index = compatibility["index_existing_assets"](
            library_root=application_paths.workspace.media_library,
            index_path=application_paths.workspace.media_library
            / "metadata"
            / "media_index.json",
        )
        print(f"[assets] Indexed media library items: {len(index.get('items', []))}")
        return True
    if args.clean_temp:
        removed = compatibility["clean_temp_files"](
            [application_paths.outputs_root / "render_temp"]
        )
        print(f"[cleanup] Removed temp paths: {len(removed)}")
        return True
    if args.asset_report:
        report_path = compatibility["create_asset_report"](
            index_path=application_paths.workspace.media_library
            / "metadata"
            / "media_index.json",
            output_path=application_paths.outputs_root
            / "asset_library_report.md",
        )
        print(f"[assets] Report created: {report_path}")
        return True
    return False


def _run_moss_action(
    args: Any,
    application_paths: Any,
    compatibility: CompatibilityNamespace,
) -> bool:
    if args.test_moss_tts:
        config = compatibility["load_config"](
            args.config,
            dev=args.dev,
            prod=args.prod,
            prod_preview=args.prod_preview,
            cinematic_preview=args.cinematic_preview,
            outputs_root=application_paths.outputs_root,
        )
        moss_error = compatibility["MossTtsProviderError"]
        try:
            output_path = compatibility["run_test_synthesis"](config)
        except moss_error as exc:
            raise SystemExit(f"[moss-tts] {exc}") from exc
        print(f"[moss-tts] Test audio created: {output_path}")
        return True
    if args.test_moss_voices:
        raise SystemExit(compatibility["run_moss_voice_tests"]())
    return False
