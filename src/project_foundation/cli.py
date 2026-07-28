"""Standalone CLI for the Project / Channel / Evidence Foundation (Stage 2B).

Run as: python -m src.project_foundation.cli <command> ...

This CLI is intentionally independent from pipeline.py. It never touches the
network, never renders, and never requires API keys.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from .channels import ChannelRegistry
from .evidence import EvidenceBundle
from .models import ChannelProfile, ProjectFoundationError, ProjectManifest
from .policies import ChannelOutputPolicy
from .policies import validate as validate_output_policy
from .projects import ProjectFactory
from .storage import read_json


def _print_json(payload: Any) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False))


def _print_error(message: str) -> None:
    print(json.dumps({"error": message}, ensure_ascii=False), file=sys.stderr)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m src.project_foundation.cli")
    parser.add_argument("--workspace", default=None, help="Runtime workspace root.")
    parser.add_argument("--paths-config", default=None, help="Optional JSON path configuration.")
    parser.add_argument("--channels-root", default=None, help="Root directory for channel storage.")
    parser.add_argument("--projects-root", default=None, help="Root directory for project storage.")

    subparsers = parser.add_subparsers(dest="group", required=True)

    channels_parser = subparsers.add_parser("channels", help="Channel commands.")
    channels_sub = channels_parser.add_subparsers(dest="command", required=True)
    channels_sub.add_parser("list", help="List all channels.")
    show_parser = channels_sub.add_parser("show", help="Show a single channel.")
    show_parser.add_argument("channel_id")
    create_parser = channels_sub.add_parser("create", help="Create a new channel from a JSON config file.")
    create_parser.add_argument("--config", required=True, help="Path to a JSON file describing the channel.")
    validate_parser = channels_sub.add_parser("validate", help="Validate a channel JSON config without creating it.")
    validate_parser.add_argument("--config", required=True, help="Path to a JSON file describing the channel.")

    projects_parser = subparsers.add_parser("projects", help="Project commands.")
    projects_sub = projects_parser.add_subparsers(dest="command", required=True)

    projects_create_parser = projects_sub.add_parser("create", help="Create a new project from a JSON config file.")
    projects_create_parser.add_argument("--config", required=True, help="Path to a JSON file describing the project.")
    projects_create_parser.add_argument("--dry-run", action="store_true", help="Do not write any files.")

    projects_show_parser = projects_sub.add_parser("show", help="Show a single project manifest.")
    projects_show_parser.add_argument("project_id")

    projects_sub.add_parser("list", help="List all projects.")

    evidence_list_parser = projects_sub.add_parser("evidence-list", help="List evidence records for a project.")
    evidence_list_parser.add_argument("project_id")

    rights_report_parser = projects_sub.add_parser("rights-report", help="Generate and save a rights report.")
    rights_report_parser.add_argument("project_id")

    project_validate_parser = projects_sub.add_parser("validate", help="Validate a project against its channel policy.")
    project_validate_parser.add_argument("project_id")

    return parser


def _channels_list(registry: ChannelRegistry) -> int:
    _print_json([profile.to_dict() for profile in registry.list()])
    return 0


def _channels_show(registry: ChannelRegistry, channel_id: str) -> int:
    profile = registry.get(channel_id)
    _print_json(profile.to_dict())
    return 0


def _channels_create(registry: ChannelRegistry, config_path: str) -> int:
    data = read_json(config_path)
    profile = ChannelProfile.from_dict(data)
    registry.create(profile)
    _print_json(profile.to_dict())
    return 0


def _channels_validate(config_path: str) -> int:
    data = read_json(config_path)
    errors: list[str] = []
    profile: ChannelProfile | None = None
    try:
        profile = ChannelProfile.from_dict(data)
    except ProjectFoundationError as exc:
        errors.append(str(exc))

    if profile is not None:
        try:
            ChannelOutputPolicy.from_dict(profile.output_policy)
        except ProjectFoundationError as exc:
            errors.append(str(exc))

    _print_json({"valid": not errors, "errors": errors})
    return 0 if not errors else 1


def _load_channel_for_project(channels_root: str, channel_id: str) -> ChannelProfile:
    registry = ChannelRegistry(base_dir=channels_root)
    return registry.get(channel_id)


def _projects_create(factory: ProjectFactory, channels_root: str, config_path: str, dry_run: bool) -> int:
    data = read_json(config_path)
    channel_id = str(data.get("channel_id") or "")
    if not channel_id:
        raise ProjectFoundationError("Project config must include channel_id.")
    channel = _load_channel_for_project(channels_root, channel_id)

    result = factory.create(
        channel,
        title=data.get("title", ""),
        project_id=data.get("project_id"),
        application_id=data.get("application_id"),
        format_id=data.get("format_id"),
        template_id=data.get("template_id"),
        language=data.get("language"),
        export_targets=data.get("export_targets"),
        source_type=data.get("source_type", "manual"),
        source_reference=data.get("source_reference", ""),
        metadata=data.get("metadata"),
        dry_run=dry_run,
    )
    _print_json(result.to_dict())
    return 0


def _projects_show(factory: ProjectFactory, project_id: str) -> int:
    manifest = factory.get(project_id)
    _print_json(manifest.to_dict())
    return 0


def _projects_list(factory: ProjectFactory) -> int:
    _print_json([manifest.to_dict() for manifest in factory.list()])
    return 0


def _projects_evidence_list(factory: ProjectFactory, project_id: str) -> int:
    manifest = factory.get(project_id)
    bundle = EvidenceBundle.load(manifest.project_root, manifest.project_id)
    _print_json([record.to_dict() for record in bundle.list()])
    return 0


def _projects_rights_report(factory: ProjectFactory, project_id: str) -> int:
    manifest = factory.get(project_id)
    bundle = EvidenceBundle.load(manifest.project_root, manifest.project_id)
    report = bundle.rights_report()
    bundle.save_rights_report(manifest.project_root)
    _print_json(report)
    return 0


def _projects_validate(factory: ProjectFactory, channels_root: str, project_id: str) -> int:
    manifest = factory.get(project_id)
    channel = _load_channel_for_project(channels_root, manifest.channel_id)
    policy = ChannelOutputPolicy.from_dict(channel.output_policy)
    bundle = EvidenceBundle.load(manifest.project_root, manifest.project_id)
    result = validate_output_policy(policy, channel, manifest, bundle.summary())
    _print_json(result.to_dict())
    return 0 if result.allowed else 1


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    from src.config_resolver import resolve_application_paths

    application_paths = resolve_application_paths(
        workspace_root=args.workspace,
        paths_config=args.paths_config,
        projects_root=args.projects_root,
    )
    args.channels_root = args.channels_root or str(application_paths.channels_root)
    args.projects_root = str(application_paths.projects_root)
    channels_registry = ChannelRegistry(base_dir=args.channels_root)
    projects_factory = ProjectFactory(base_dir=args.projects_root)

    try:
        if args.group == "channels":
            if args.command == "list":
                return _channels_list(channels_registry)
            if args.command == "show":
                return _channels_show(channels_registry, args.channel_id)
            if args.command == "create":
                return _channels_create(channels_registry, args.config)
            if args.command == "validate":
                return _channels_validate(args.config)
        elif args.group == "projects":
            if args.command == "create":
                return _projects_create(projects_factory, args.channels_root, args.config, args.dry_run)
            if args.command == "show":
                return _projects_show(projects_factory, args.project_id)
            if args.command == "list":
                return _projects_list(projects_factory)
            if args.command == "evidence-list":
                return _projects_evidence_list(projects_factory, args.project_id)
            if args.command == "rights-report":
                return _projects_rights_report(projects_factory, args.project_id)
            if args.command == "validate":
                return _projects_validate(projects_factory, args.channels_root, args.project_id)
    except ProjectFoundationError as exc:
        _print_error(str(exc))
        return 1
    except FileNotFoundError as exc:
        _print_error(f"File not found: {exc}")
        return 1

    parser.print_help(sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
