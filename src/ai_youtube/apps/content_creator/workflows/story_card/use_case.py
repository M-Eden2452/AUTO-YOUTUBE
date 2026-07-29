"""Canonical Story Card application use case."""

from __future__ import annotations

from typing import Any

from src.content_creation.models import (
    ContentCreationError,
    ContentCreationRequest,
    ContentCreationResult,
)
from src.content_creation.service_support import (
    ProgressCallback,
    notify,
    request_path_context,
)
from src.project_foundation.channels import ChannelRegistry
from src.project_foundation.projects import ProjectFactory
from src.templates.story_card.integration import (
    StoryCardIntegrationError,
    prepare_story_card_render,
)


def create_story_card(
    request: ContentCreationRequest,
    template,
    progress_callback: ProgressCallback | None = None,
) -> ContentCreationResult:
    if not request.channel_id:
        raise ContentCreationError(
            "channel_id is required for story_card_text_only_v1."
        )
    if not request.source_asset_path:
        raise ContentCreationError(
            "source_asset_path is required for story_card_text_only_v1 (asset search is not "
            "wired into this workflow yet - pass a local video file with --source-asset)."
        )
    projects_root, fallback_roots, channels_root = request_path_context(request)
    channel = ChannelRegistry(channels_root).get(request.channel_id)
    if request.execution.resume and request.project_id:
        from src.projects import ProjectRepository

        projects_root = ProjectRepository(
            projects_root,
            fallback_roots=fallback_roots,
        ).project_root(request.project_id).parent
    factory = ProjectFactory(base_dir=projects_root)
    dry_run = bool(request.execution.dry_run)

    notify(progress_callback, "project_create", "running")
    if request.execution.resume and request.project_id:
        manifest = factory.get(request.project_id)
    else:
        creation = factory.create(
            channel,
            title=request.title or request.topic or "story_card",
            project_id=request.project_id or None,
            application_id=template.application_id,
            format_id=template.format_id,
            template_id=template.template_id,
            language=request.language or channel.default_language,
            dry_run=dry_run,
        )
        manifest = creation.manifest
    notify(progress_callback, "project_create", "completed")

    if dry_run:
        return ContentCreationResult(
            status="dry_run_completed",
            project_id=manifest.project_id,
            project_root=manifest.project_root,
            stages=[{"stage": "project_create", "status": "dry_run"}],
            output_paths={},
            rerun_commands=[story_card_rerun_command(request)],
        )

    notify(progress_callback, "render", "running")
    try:
        render_result = prepare_story_card_render(
            manifest,
            channel=channel,
            source_asset_path=request.source_asset_path,
            text=request.text,
            dry_run=False,
            render=not request.execution.prepare_only,
            allow_overwrite=bool(
                request.project_overrides.get("allow_overwrite", False)
            ),
        )
    except StoryCardIntegrationError as exc:
        notify(progress_callback, "render", "failed")
        return ContentCreationResult(
            status="failed",
            project_id=manifest.project_id,
            project_root=manifest.project_root,
            errors=[str(exc)],
            rerun_commands=[story_card_rerun_command(request)],
        )
    notify(progress_callback, "render", "completed")

    status = {
        "dry_run": "dry_run_completed",
        "prepared": "prepared_awaiting_render",
        "rendered": "completed",
        "skipped_existing_output": "skipped_existing_output",
        "failed": "failed",
    }.get(render_result.render_status, render_result.render_status)

    output_paths: dict[str, Any] = {}
    if render_result.render_status == "rendered":
        output_paths["final_video"] = render_result.output_path
    output_paths["render_request"] = render_result.render_request_path

    evidence = dict(render_result.metadata.get("evidence") or {})
    if evidence.get("evidence_manifest_path"):
        output_paths["evidence_manifest"] = evidence["evidence_manifest_path"]

    return ContentCreationResult(
        status=status,
        project_id=manifest.project_id,
        project_root=manifest.project_root,
        stages=[
            {
                "stage": "story_card_render",
                "status": render_result.render_status,
            }
        ],
        output_paths=output_paths,
        warnings=list(render_result.warnings),
        errors=(
            []
            if render_result.render_status != "failed"
            else ["story_card render failed; see metadata.render_manifest."]
        ),
        evidence=evidence,
        quality_report={},
        rerun_commands=[story_card_rerun_command(request)],
    )


def story_card_rerun_command(request: ContentCreationRequest) -> str:
    parts = [
        "./venv/Scripts/python.exe -m ai_youtube create",
        "--format vertical_short",
        "--template story_card_text_only_v1",
        f"--channel {request.channel_id}",
        f"--language {request.language}",
    ]
    if request.text.get("top"):
        parts.append(f'--text "{request.text["top"]}"')
    if request.source_asset_path:
        parts.append(f"--source-asset {request.source_asset_path}")
    parts.append("--voice-provider disabled --subtitles disabled")
    return " ".join(parts)
