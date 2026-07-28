"""Compatibility layer for legacy callers of src.content_creation.cli.

This module is maintained for backward compatibility.
The canonical CLI dispatcher and commands live in ``src.ai_youtube.cli``.
Do not add new CLI features here; update ``src.ai_youtube.cli`` instead.
"""

from __future__ import annotations

import argparse
from typing import Any

from src.content_creation.commands.content import add_create_arguments as _add_create_arguments_impl
from src.ai_youtube.cli.main import (
    _resolve_cli_paths as _resolve_cli_paths_impl,
    build_parser as _build_parser_impl,
    configure_console_encoding as _configure_console_encoding_impl,
    main as _main_impl,
    run_content_creation_cli as _run_content_creation_cli_impl,
)
from src.content_creation.models import ContentCreationRequest
from src.content_creation.presentation import print_rights_lines as _print_rights_lines_impl
from src.content_creation.request_builder import from_cli_namespace, load_visual_briefs


def configure_console_encoding() -> None:
    _configure_console_encoding_impl()


def build_parser(*, prog: str = "content-creation") -> argparse.ArgumentParser:
    return _build_parser_impl(prog=prog)


def run_content_creation_cli(args: argparse.Namespace) -> int:
    return _run_content_creation_cli_impl(args)


def main(argv: list[str] | None = None) -> int:
    return _main_impl(argv)


def _add_create_arguments(parser: argparse.ArgumentParser) -> None:
    _add_create_arguments_impl(parser)


def _resolve_cli_paths(args: argparse.Namespace):
    return _resolve_cli_paths_impl(args)


def _request_from_args(args: argparse.Namespace) -> ContentCreationRequest:
    _resolve_cli_paths(args)
    return from_cli_namespace(
        args,
        projects_root=args.projects_root,
        project_fallback_roots=tuple(
            getattr(args, "project_fallback_roots", ()),
        ),
        channels_root=getattr(args, "channels_root", ""),
    )


def _load_visual_briefs(path: str) -> dict[str, dict]:
    return load_visual_briefs(path)


def _print_rights_lines(evidence: dict[str, Any], *, prefix: str = "") -> None:
    _print_rights_lines_impl(evidence, prefix=prefix)


__all__ = [
    "build_parser",
    "configure_console_encoding",
    "main",
    "run_content_creation_cli",
]
