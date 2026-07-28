from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from src.content_creation.commands.content import register_commands as _register_content


def register_commands(subparsers: Any, *, common: argparse.ArgumentParser) -> None:
    _register_content(subparsers, common=common)


def handle_create(args: argparse.Namespace, *, resolve_paths_fn: Any, print_json_fn: Any) -> int:
    from src.content_creation.models import ContentCreationError
    from src.content_creation.output_report import describe_output_file
    from src.content_creation.presentation import print_rights_lines
    from src.content_creation.request_builder import from_cli_namespace
    from src.content_creation.service import create_content

    resolve_paths_fn(args)
    request = from_cli_namespace(
        args,
        projects_root=args.projects_root,
        project_fallback_roots=tuple(getattr(args, "project_fallback_roots", ())),
        channels_root=getattr(args, "channels_root", ""),
    )

    if getattr(args, "debug", False):
        result = create_content(request)
    else:
        try:
            result = create_content(request)
        except ContentCreationError as exc:
            if args.json_output:
                print_json_fn({"status": "failed", "error": str(exc), "reason": exc.reason, "retryable": exc.retryable})
            else:
                print(f"[create] error: {exc} (reason={exc.reason})")
            return 1

    if args.json_output:
        print_json_fn(result.to_dict())
        return 0 if result.status != "failed" else 1

    print(f"[create] status={result.status}")
    print(f"[create] project_id={result.project_id}")
    print(f"[create] project_root={Path(result.project_root).resolve()}")
    for stage in result.stages:
        print(f"[create] stage {stage.get('stage')}: {stage.get('status')}")

    final_video = result.output_paths.get("final_video")
    if final_video:
        report = describe_output_file(final_video, project_root=result.project_root)
        print(f"[create] output_path={report['absolute_path']}")
        print(f"[create] output_project_relative={report['project_relative_path']}")
        print(f"[create] output_size_bytes={report['size_bytes']}")
        print(f"[create] output_duration_sec={report['duration_sec']}")
        print(f"[create] output_resolution={report['resolution']}")
        print(f"[create] output_audio_present={report['audio_present']}")

    print_rights_lines(result.evidence, prefix="[create] ")
    for warning in result.warnings:
        print(f"[create] warning: {warning}")
    for error in result.errors:
        print(f"[create] error: {error}")
    if result.rerun_commands:
        print(f"[create] rerun: {result.rerun_commands[0]}")
    return 0 if result.status != "failed" else 1


def handle_wizard(args: argparse.Namespace) -> int:
    from src.content_creation.wizard import run_wizard

    result = run_wizard(
        no_icons=getattr(args, "no_icons", False),
        projects_root=args.projects_root,
        project_fallback_roots=args.project_fallback_roots,
        channels_root=args.channels_root,
    )
    if result is None:
        return 0
    return 0 if result.status != "failed" else 1


__all__ = ["register_commands", "handle_create", "handle_wizard"]
