from __future__ import annotations

import argparse
import sys

from src.ai_youtube.apps.content_creator.workflows.fullscreen_voiceover import (
    create_news_to_short_job,
    run_news_to_short_job,
)


def main(argv: list[str] | None = None) -> int:
    _configure_console_encoding()
    parser = argparse.ArgumentParser(description="news_to_short app")
    parser.add_argument("--workspace", default=None)
    parser.add_argument("--paths-config", default=None)
    parser.add_argument("--projects-root", default=None)
    parser.add_argument("--job-id")
    parser.add_argument("--action", choices=["create", "run", "resume"], default="create")
    parser.add_argument("--channel", default="nature_science_news_ru")
    parser.add_argument("--url")
    parser.add_argument("--topic")
    parser.add_argument("--text")
    parser.add_argument("--text-file")
    parser.add_argument("--assets", action="append")
    parser.add_argument("--language", default="ru")
    parser.add_argument("--target-duration", type=int, default=55)
    parser.add_argument("--until-stage")
    parser.add_argument("--stage")
    parser.add_argument("--force-stage", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--completion-mode", choices=["strict", "draft_complete"], default="")
    parser.add_argument("--script-adaptation", choices=["none", "light"], default="")
    args = parser.parse_args(argv)

    from src.config_resolver import resolve_application_paths

    application_paths = resolve_application_paths(
        workspace_root=args.workspace,
        paths_config=args.paths_config,
        projects_root=args.projects_root,
    )
    projects_root = application_paths.projects_root

    if args.action == "create":
        job = create_news_to_short_job(
            projects_root=projects_root,
            channel_id=args.channel,
            url=args.url,
            topic=args.topic,
            text=args.text,
            text_file=args.text_file,
            assets=args.assets,
            language=args.language,
            target_duration_sec=args.target_duration,
            completion_mode=args.completion_mode,
            script_adaptation=args.script_adaptation,
        )
        job_id = job.job_id
    else:
        if not args.job_id:
            raise SystemExit("--job-id is required for run/resume.")
        job_id = args.job_id
        projects_root = application_paths.find_project_root(job_id).parent

    result = run_news_to_short_job(
        projects_root=projects_root,
        job_id=job_id,
        dry_run=args.dry_run,
        until_stage=args.until_stage,
        stage=args.stage,
        resume=args.action == "resume",
        force_stage=args.force_stage,
        completion_mode=args.completion_mode,
        script_adaptation=args.script_adaptation,
    )
    print(f"[news-to-short-app] job_id={result.job_id}")
    print(f"[news-to-short-app] status={result.status}")
    print(f"[news-to-short-app] project={result.project_root}")
    return 0


def _configure_console_encoding() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
