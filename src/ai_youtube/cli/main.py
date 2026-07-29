from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from src.ai_youtube.cli.commands import assets, create, diagnostics, project


def configure_console_encoding() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def _json_flag_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", dest="json_output", action="store_true", help="Print machine-readable JSON.")
    common.add_argument(
        "--debug", action="store_true", help="Show full tracebacks instead of a short error message."
    )
    common.add_argument(
        "--no-icons", action="store_true", help="Use ASCII markers instead of emoji (wizard only)."
    )
    common.add_argument(
        "--workspace",
        default=None,
        help=(
            "Runtime workspace root. Relative paths are anchored to the repository; "
            "overrides AI_YOUTUBE_WORKSPACE and path config."
        ),
    )
    common.add_argument(
        "--paths-config",
        default=None,
        help="Optional JSON path configuration; overrides AI_YOUTUBE_PATHS_CONFIG.",
    )
    return common


def build_parser(*, prog: str = "python -m ai_youtube") -> argparse.ArgumentParser:
    json_flag = _json_flag_parser()
    parser = argparse.ArgumentParser(
        prog=prog,
        description=(
            "Unified content-creation CLI: one create/wizard command over the existing "
            "Production Catalog, Project Foundation, VoiceProfileRegistry and renderers. "
            "Never runs paid TTS without --approve-paid-generation."
        ),
        parents=[json_flag],
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    create.register_commands(subparsers, common=json_flag)
    project.register_commands(subparsers, common=json_flag)
    assets.register_commands(subparsers, common=json_flag)
    diagnostics.register_commands(subparsers, common=json_flag)
    return parser


def _resolve_cli_paths(args: argparse.Namespace):
    existing = getattr(args, "_application_paths", None)
    if existing is not None:
        return existing
    from src.config_resolver import resolve_application_paths

    paths = resolve_application_paths(
        workspace_root=getattr(args, "workspace", None),
        paths_config=getattr(args, "paths_config", None),
        projects_root=getattr(args, "projects_root", None),
    )
    args.projects_root = str(paths.projects_root)
    args.project_fallback_roots = tuple(str(path) for path in paths.project_fallback_roots)
    args.channels_root = str(paths.channels_root)
    args._application_paths = paths
    return paths


def _print_json(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2, default=str))


def run_content_creation_cli(
    args: argparse.Namespace,
    *,
    create_content_fn: Any = None,
) -> int:
    _resolve_cli_paths(args)
    command = args.command

    if command == "create" or command == "resume":
        if command == "resume":
            args.resume = True
        return create.handle_create(
            args,
            resolve_paths_fn=_resolve_cli_paths,
            print_json_fn=_print_json,
            create_content_fn=create_content_fn,
        )

    if command == "wizard":
        return create.handle_wizard(args)

    if command == "project":
        return project.handle_project(args, resolve_paths_fn=_resolve_cli_paths, print_json_fn=_print_json)

    if command == "assets":
        return assets.handle_assets(args, print_json_fn=_print_json)

    return diagnostics.handle_diagnostics(args, resolve_paths_fn=_resolve_cli_paths, print_json_fn=_print_json)


def main(argv: list[str] | None = None) -> int:
    configure_console_encoding()
    parser = build_parser()
    args = parser.parse_args(argv)
    return run_content_creation_cli(args)


__all__ = ["build_parser", "configure_console_encoding", "main", "run_content_creation_cli"]
