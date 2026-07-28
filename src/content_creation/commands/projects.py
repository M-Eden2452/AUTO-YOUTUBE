from __future__ import annotations

import argparse


def register_commands(
    subparsers: argparse._SubParsersAction,
    *,
    common: argparse.ArgumentParser,
) -> None:
    project = subparsers.add_parser(
        "project",
        help="Inspect existing projects.",
        parents=[common],
    )
    project.add_argument("action", choices=["list", "status", "validate", "rights-report"])
    project.add_argument("--project-id", help="Required for every action except 'list'.")
    project.add_argument("--projects-root", default=None)

    assets = subparsers.add_parser(
        "assets",
        help="Manage visual slots in an existing news project.",
        parents=[common],
    )
    assets.add_argument("action", choices=["replace"])
    assets.add_argument("--project-id", required=True)
    assets.add_argument("--scene-id", required=True)
    assets.add_argument("--slot-id", required=True)
    assets.add_argument(
        "--file",
        required=True,
        help="Local media to import without modifying the original.",
    )
    assets.add_argument("--source-url", default="", help="Optional provenance URL.")
    assets.add_argument(
        "--license-file",
        default="",
        help="Optional local rights/license proof.",
    )
    assets.add_argument(
        "--confirm-user-owned",
        action="store_true",
        help="Explicitly confirm that you own or control the supplied media rights.",
    )
    assets.add_argument("--projects-root", default=None)
