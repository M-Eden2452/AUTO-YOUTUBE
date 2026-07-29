"""Compatibility facade for the canonical CLI diagnostic command families."""

from __future__ import annotations

import argparse
from typing import Any

from src.ai_youtube.cli import presentation
from src.ai_youtube.cli.commands import authoring, catalog, localization
from src.content_creation.commands import authoring as _register_authoring
from src.content_creation.commands import catalog as _register_catalog


def register_commands(
    subparsers: Any,
    *,
    common: argparse.ArgumentParser,
) -> None:
    _register_catalog.register_commands(subparsers, common=common)
    _register_authoring.register_commands(subparsers, common=common)


def handle_diagnostics(
    args: argparse.Namespace,
    *,
    resolve_paths_fn: Any,
    print_json_fn: Any,
) -> int:
    del resolve_paths_fn
    command = args.command

    if command in catalog.COMMANDS:
        return catalog.handle_catalog(args, print_json_fn=print_json_fn)
    if command in localization.COMMANDS:
        if command == "channels" and args.action == "show" and args.explain:
            return _channels_explain(args, print_json_fn=print_json_fn)
        if command == "voices" and args.action == "explain":
            return _voices_explain(args, print_json_fn=print_json_fn)
        if command == "subtitles" and args.action in {"explain", "validate"}:
            handler = (
                _subtitles_explain
                if args.action == "explain"
                else _subtitles_validate
            )
            return handler(args, print_json_fn=print_json_fn)
        return localization.handle_localization(
            args,
            print_json_fn=print_json_fn,
        )
    if command == "script":
        return _run_script_command(args, print_json_fn=print_json_fn)
    if command == "visual-plan":
        return _run_visual_plan_command(
            args,
            print_json_fn=print_json_fn,
        )
    if command in authoring.COMMANDS:
        return authoring.handle_authoring(
            args,
            print_json_fn=print_json_fn,
        )
    raise SystemExit(f"Unknown command: {command!r}")


# Preserve the historical module-level patch points while implementation lives
# behind the new domain boundaries.
_channels_explain = localization.channels_explain
_voices_explain = localization.voices_explain
_subtitles_explain = localization.subtitles_explain
_subtitles_validate = localization.subtitles_validate
_run_script_command = authoring.run_script_command
_run_visual_plan_command = authoring.run_visual_plan_command
_print_plain = presentation.print_plain
_print_plan_validation = presentation.print_plan_validation
_print_script_validation = presentation.print_script_validation


__all__ = ["register_commands", "handle_diagnostics"]
