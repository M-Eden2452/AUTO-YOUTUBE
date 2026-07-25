from __future__ import annotations

import argparse
import sys

from src.news.pipeline import create_news_to_short_job, run_news_to_short_job


def main(argv: list[str] | None = None) -> int:
    _configure_console_encoding()
    parser = argparse.ArgumentParser(description="news_to_short app")
    parser.add_argument("--projects-root", default="projects")
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
    args = parser.parse_args(argv)

    if args.action == "create":
        job = create_news_to_short_job(
            projects_root=args.projects_root,
            channel_id=args.channel,
            url=args.url,
            topic=args.topic,
            text=args.text,
            text_file=args.text_file,
            assets=args.assets,
            language=args.language,
            target_duration_sec=args.target_duration,
        )
        job_id = job.job_id
    else:
        if not args.job_id:
            raise SystemExit("--job-id is required for run/resume.")
        job_id = args.job_id

    result = run_news_to_short_job(
        projects_root=args.projects_root,
        job_id=job_id,
        dry_run=args.dry_run,
        until_stage=args.until_stage,
        stage=args.stage,
        resume=args.action == "resume",
        force_stage=args.force_stage,
    )
    print(f"[news-to-short-app] job_id={result.job_id}")
    print(f"[news-to-short-app] status={result.status}")
    print(f"[news-to-short-app] project={result.project_root}")
    return 0


def _configure_console_encoding() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
