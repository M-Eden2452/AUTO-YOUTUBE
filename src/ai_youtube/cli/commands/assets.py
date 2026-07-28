from __future__ import annotations

import argparse
from typing import Any


def register_commands(subparsers: Any, *, common: argparse.ArgumentParser) -> None:
    pass


def handle_assets(args: argparse.Namespace, *, print_json_fn: Any) -> int:
    from src.assets.completion.replacement import replace_visual_slot

    try:
        projects_root = args._application_paths.find_project_root(args.project_id).parent
        result = replace_visual_slot(
            projects_root=projects_root,
            project_id=args.project_id,
            scene_id=args.scene_id,
            slot_id=args.slot_id,
            source_file=args.file,
            source_url=args.source_url,
            license_file=args.license_file,
            confirm_user_owned=args.confirm_user_owned,
        )
    except Exception as exc:
        if getattr(args, "debug", False):
            raise
        if args.json_output:
            print_json_fn(
                {
                    "status": "failed",
                    "code": str(getattr(exc, "code", "") or "assets_replace_failed"),
                    "error": str(exc),
                }
            )
        else:
            print(f"[assets replace] error: {exc}")
        return 1
    if args.json_output:
        print_json_fn(result)
    else:
        print(f"[assets replace] status={result.get('status', 'completed')}")
        print(f"[assets replace] project_id={args.project_id}")
        print(f"[assets replace] scene_id={args.scene_id} slot_id={args.slot_id}")
        print(
            f"[assets replace] imported_path="
            f"{result.get('imported_path') or result.get('asset_path') or ''}"
        )
        print(f"[assets replace] checksum_sha256={result.get('checksum_sha256', '')}")
    return 0


__all__ = ["register_commands", "handle_assets"]
