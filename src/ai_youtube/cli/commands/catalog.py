from __future__ import annotations

import argparse
from typing import Any

from src.ai_youtube.cli import presentation
from src.content_creation import capabilities
from src.production_catalog.catalog import get_default_catalog
from src.production_catalog.models import CatalogValidationError


COMMANDS = frozenset({"applications", "capabilities", "formats", "templates"})


def handle_catalog(args: argparse.Namespace, *, print_json_fn: Any) -> int:
    command = args.command

    if command == "applications":
        catalog = get_default_catalog()
        if args.action == "show":
            if not args.application:
                raise SystemExit("applications show requires --application.")
            data = catalog.applications.get(args.application).to_dict()
        else:
            applications = catalog.applications.list_all()
            if not args.all:
                applications = [
                    app
                    for app in applications
                    if app.enabled and app.implementation_status == "active"
                ]
            data = [app.to_dict() for app in applications]
        print_json_fn(data) if args.json_output else presentation.print_plain(data)
        return 0

    if command == "capabilities":
        report = capabilities.build_capabilities_report()
        if args.json_output:
            print_json_fn(report)
        else:
            presentation.print_capabilities(report)
        return 0

    if command == "formats":
        catalog = get_default_catalog()
        if args.action == "show":
            if not args.format:
                raise SystemExit("formats show requires --format.")
            data = catalog.formats.get(args.format).to_dict()
        else:
            data = catalog.formats.serialize()
        print_json_fn(data) if args.json_output else presentation.print_plain(data)
        return 0

    if command == "templates":
        catalog = get_default_catalog()
        try:
            if args.action == "show":
                if not args.template:
                    raise SystemExit("templates show requires --template.")
                data = catalog.templates.get(args.template).to_dict()
            elif args.format:
                data = [
                    template.to_dict()
                    for template in catalog.templates.filter_by_format(args.format)
                ]
            else:
                data = catalog.templates.serialize()
        except CatalogValidationError as exc:
            raise SystemExit(str(exc)) from exc
        print_json_fn(data) if args.json_output else presentation.print_plain(data)
        return 0

    raise SystemExit(f"Unknown catalog command: {command!r}")


__all__ = ["COMMANDS", "handle_catalog"]
