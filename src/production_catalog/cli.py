from __future__ import annotations

import json
from typing import Any

from .catalog import ProductionCatalog, get_default_catalog
from .models import ApplicationDefinition, CatalogValidationError, ExportTargetDefinition, FormatDefinition, TemplateDefinition


def run_production_catalog_cli(args: Any) -> int:
    """Dispatch the read-only production catalog CLI commands.

    Covers ``applications``, ``formats``, ``templates`` and ``export-targets``.
    Every branch is pure in-memory lookup: no network, no provider/Vision/TTS
    calls, no project or render files are created.
    """
    command = args.command
    subcommand = getattr(args, "subcommand", None)
    as_json = bool(getattr(args, "json_output", False))
    catalog = get_default_catalog()

    try:
        if command == "applications":
            return _run_applications(catalog, subcommand, args, as_json)
        if command == "formats":
            return _run_formats(catalog, subcommand, args, as_json)
        if command == "templates":
            return _run_templates(catalog, subcommand, args, as_json)
        if command == "export-targets":
            return _run_export_targets(catalog, subcommand, args, as_json)
    except CatalogValidationError as exc:
        raise SystemExit(str(exc)) from exc

    raise SystemExit(f"Unknown production catalog command: {command!r}.")


def _print_json(payload: Any) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _run_applications(catalog: ProductionCatalog, subcommand: str | None, args: Any, as_json: bool) -> int:
    if subcommand == "list":
        applications = catalog.applications.list_all()
        if as_json:
            _print_json(catalog.applications.serialize())
            return 0
        print(f"Приложения ({len(applications)}):")
        for application in applications:
            print(_application_summary_line(application))
        return 0

    if subcommand == "inspect":
        application_id = getattr(args, "application", None)
        if not application_id:
            raise SystemExit("applications inspect requires --application.")
        application = catalog.applications.get(application_id)
        if as_json:
            _print_json(application.to_dict())
            return 0
        _print_application_details(application)
        return 0

    raise SystemExit("applications requires subcommand: list or inspect.")


def _run_formats(catalog: ProductionCatalog, subcommand: str | None, args: Any, as_json: bool) -> int:
    if subcommand == "list":
        formats = catalog.formats.list_all()
        if as_json:
            _print_json(catalog.formats.serialize())
            return 0
        print(f"Форматы ({len(formats)}):")
        for format_definition in formats:
            print(_format_summary_line(format_definition))
        return 0

    if subcommand == "inspect":
        format_id = getattr(args, "format", None)
        if not format_id:
            raise SystemExit("formats inspect requires --format.")
        format_definition = catalog.formats.get(format_id)
        if as_json:
            _print_json(format_definition.to_dict())
            return 0
        _print_format_details(format_definition)
        return 0

    raise SystemExit("formats requires subcommand: list or inspect.")


def _run_templates(catalog: ProductionCatalog, subcommand: str | None, args: Any, as_json: bool) -> int:
    if subcommand == "list":
        templates = catalog.templates.list_all()
        application_id = getattr(args, "application", None)
        format_id = getattr(args, "format", None)
        if application_id:
            templates = [t for t in templates if t.application_id == application_id]
        if format_id:
            templates = [t for t in templates if t.format_id == format_id]
        if as_json:
            _print_json([t.to_dict() for t in templates])
            return 0
        print(f"Шаблоны ({len(templates)}):")
        for template in templates:
            print(_template_summary_line(template))
        return 0

    if subcommand == "inspect":
        requested_id = getattr(args, "template", None)
        if not requested_id:
            raise SystemExit("templates inspect requires --template.")
        canonical_id = catalog.templates.resolve_id(requested_id)
        template = catalog.templates.get(requested_id)
        if as_json:
            payload = template.to_dict()
            payload["requested_id"] = requested_id
            payload["resolved_from_legacy_alias"] = requested_id != canonical_id
            _print_json(payload)
            return 0
        if requested_id != canonical_id:
            print(f"'{requested_id}' — это legacy alias. Канонический template_id: '{canonical_id}'.")
        _print_template_details(template)
        return 0

    raise SystemExit("templates requires subcommand: list or inspect.")


def _run_export_targets(catalog: ProductionCatalog, subcommand: str | None, args: Any, as_json: bool) -> int:
    if subcommand == "list":
        targets = catalog.export_targets.list_all()
        if as_json:
            _print_json(catalog.export_targets.serialize())
            return 0
        print(f"Export targets ({len(targets)}):")
        for target in targets:
            print(_export_target_summary_line(target))
        return 0

    if subcommand == "inspect":
        target_id = getattr(args, "target", None)
        if not target_id:
            raise SystemExit("export-targets inspect requires --target.")
        target = catalog.export_targets.get(target_id)
        if as_json:
            _print_json(target.to_dict())
            return 0
        _print_export_target_details(target)
        return 0

    raise SystemExit("export-targets requires subcommand: list or inspect.")


def _application_summary_line(application: ApplicationDefinition) -> str:
    return (
        f"- {application.application_id} | {application.display_name} | "
        f"enabled={str(application.enabled).lower()} | status={application.implementation_status}"
    )


def _print_application_details(application: ApplicationDefinition) -> None:
    print(f"Приложение: {application.application_id}")
    print(f"  Название: {application.display_name}")
    print(f"  Описание: {application.description}")
    print(f"  Включено: {str(application.enabled).lower()}")
    print(f"  Статус реализации: {application.implementation_status}")
    print(f"  Поддерживаемые входы: {', '.join(application.supported_input_types)}")
    print(f"  Поддерживаемые форматы: {', '.join(application.supported_format_ids)}")


def _format_summary_line(format_definition: FormatDefinition) -> str:
    return (
        f"- {format_definition.format_id} | {format_definition.display_name} | "
        f"{format_definition.width}x{format_definition.height} ({format_definition.aspect_ratio}) | "
        f"enabled={str(format_definition.enabled).lower()} | status={format_definition.implementation_status}"
    )


def _print_format_details(format_definition: FormatDefinition) -> None:
    print(f"Формат: {format_definition.format_id}")
    print(f"  Название: {format_definition.display_name}")
    print(f"  Разрешение: {format_definition.width}x{format_definition.height}")
    print(f"  Соотношение сторон: {format_definition.aspect_ratio}")
    print(f"  Включено: {str(format_definition.enabled).lower()}")
    print(f"  Статус реализации: {format_definition.implementation_status}")


def _template_summary_line(template: TemplateDefinition) -> str:
    aliases = ", ".join(template.legacy_aliases) or "-"
    return (
        f"- {template.template_id} | {template.display_name} | app={template.application_id} | "
        f"format={template.format_id} | enabled={str(template.enabled).lower()} | "
        f"status={template.implementation_status} | legacy_aliases={aliases}"
    )


def _print_template_details(template: TemplateDefinition) -> None:
    print(f"Шаблон: {template.template_id}")
    print(f"  Название: {template.display_name}")
    print(f"  Описание: {template.description}")
    print(f"  Приложение: {template.application_id}")
    print(f"  Формат: {template.format_id}")
    print(f"  Версия: {template.version}")
    print(f"  Включён: {str(template.enabled).lower()}")
    print(f"  Статус реализации: {template.implementation_status}")
    print(f"  Legacy aliases: {', '.join(template.legacy_aliases) or '-'}")
    print(f"  Render preset id: {template.render_preset_id}")
    print(f"  Поддерживаемые входы: {', '.join(template.supported_input_types)}")
    print(f"  Export targets: {', '.join(template.supported_export_targets)}")
    print(f"  Требует озвучку: {str(template.requires_voice).lower()}")
    print(f"  Поддержка ввода темы: {str(template.supports_topic_input).lower()}")
    print(f"  Поддержка ввода сценария: {str(template.supports_script_input).lower()}")
    print(f"  Рекомендуется для: {', '.join(template.recommended_for)}")
    print(f"  Evidence required: {str(template.evidence_required).lower()}")
    print(f"  Workflow binding: {json.dumps(template.workflow_binding, ensure_ascii=False)}")
    print(f"  Output contract: {json.dumps(template.output_contract, ensure_ascii=False)}")
    print(
        "  Policy refs: "
        f"script={template.script_policy_id}, asset={template.asset_policy_id}, "
        f"audio={template.audio_policy_id}, duration={template.duration_policy_id}, "
        f"selection={template.selection_policy_id}, quality={template.quality_policy_id}"
    )


def _export_target_summary_line(target: ExportTargetDefinition) -> str:
    return (
        f"- {target.target_id} | {target.display_name} | format={target.format_id} | "
        f"{target.width}x{target.height} ({target.aspect_ratio}) | "
        f"enabled={str(target.enabled).lower()} | status={target.implementation_status}"
    )


def _print_export_target_details(target: ExportTargetDefinition) -> None:
    print(f"Export target: {target.target_id}")
    print(f"  Название: {target.display_name}")
    print(f"  Формат: {target.format_id}")
    print(f"  Разрешение: {target.width}x{target.height}")
    print(f"  Соотношение сторон: {target.aspect_ratio}")
    print(f"  Максимальная длительность (сек): {target.max_duration_sec}")
    print(f"  Safe zone profile: {target.safe_zone_profile}")
    print(f"  Output filename: {target.output_filename}")
    print(f"  Включён: {str(target.enabled).lower()}")
    print(f"  Статус реализации: {target.implementation_status}")
