from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from src.content_creation.commands.projects import register_commands as _register_projects


def register_commands(subparsers: Any, *, common: argparse.ArgumentParser) -> None:
    _register_projects(subparsers, common=common)


def handle_project(args: argparse.Namespace, *, resolve_paths_fn: Any, print_json_fn: Any) -> int:
    from src.project_foundation.channels import ChannelRegistry
    from src.project_foundation.evidence import EvidenceBundle
    from src.project_foundation.models import ProjectFoundationError
    from src.project_foundation.policies import ChannelOutputPolicy, validate as validate_policy
    from src.project_foundation.projects import ProjectFactory
    from src.projects import (
        PROJECT_KIND_PROJECT_MANIFEST,
        ProjectNotFoundError,
        ProjectRepository,
        build_rights_report,
    )
    from src.content_creation.presentation import RIGHTS_STATUS_LABELS

    repository = ProjectRepository(
        args.projects_root, fallback_roots=args.project_fallback_roots
    )

    if args.action == "list":
        views = [view.to_dict() for view in repository.list(include_unknown=True)]
        if getattr(args, "json_output", False):
            print_json_fn(views)
        elif not views:
            print(f"[project] В {Path(args.projects_root).resolve()} нет проектов.")
        else:
            for view in views:
                print(
                    f"[project] {view['project_id']} | kind={view['kind']} | template={view['template_id'] or '-'} "
                    f"| channel={view['channel_id'] or '-'} | status={view['status']} "
                    f"| video={'да' if view['final_video'] else 'нет'}"
                )
        return 0

    if not args.project_id:
        print(f"[project] Действие {args.action!r} требует --project-id.")
        return 1

    if args.action == "status":
        try:
            view = repository.get(args.project_id)
        except ProjectNotFoundError as exc:
            print(f"[project] {exc}")
            return 1
        if getattr(args, "json_output", False):
            print_json_fn(view.to_dict())
        else:
            print(f"[project] project_id={view.project_id}")
            print(f"[project] kind={view.kind}")
            print(f"[project] project_root={Path(view.project_root).resolve()}")
            print(f"[project] channel={view.channel_id or '-'} template={view.template_id or '-'} language={view.language or '-'}")
            print(f"[project] status={view.status}")
            if view.quality_status:
                print(f"[project] quality={view.quality_status}")
            if view.visual_support:
                support = view.visual_support
                print(
                    f"[project] visual_support: сцен={support.get('scene_count', 0)} "
                    f"полная поддержка={support.get('full_support', 0)} "
                    f"без материала={support.get('unresolved', 0)}"
                )
                for scene_id in support.get("scenes_needing_review", []):
                    print(f"[project] visual_support: сцена {scene_id} требует проверки")
            for stage in view.stages:
                print(f"[project] stage {stage.stage}: {stage.status}" + (f" ({stage.error})" if stage.error else ""))
            if view.final_video:
                print(f"[project] final_video={Path(view.final_video).resolve()}")
            else:
                print("[project] final_video=нет готового файла")
            for name, path in view.output_paths.items():
                print(f"[project] output {name}={path}")
            for path in view.evidence_paths:
                print(f"[project] evidence={path}")
            for warning in view.warnings:
                print(f"[project] warning: {warning}")
        return 0 if view.kind != "unknown" else 1

    if args.action == "rights-report":
        try:
            view = repository.get(args.project_id)
        except ProjectNotFoundError as exc:
            print(f"[rights] {exc}")
            return 1

        report = build_rights_report(
            project_id=view.project_id, project_root=view.project_root, project_kind=view.kind
        )

        if view.kind == PROJECT_KIND_PROJECT_MANIFEST:
            try:
                report.evidence_bundle_report = EvidenceBundle.load(view.project_root, view.project_id).rights_report()
            except Exception as exc:
                report.warnings.append(f"EvidenceBundle не прочитан: {exc}")

        if getattr(args, "json_output", False):
            print_json_fn(report.to_dict())
            return 1 if report.has_blocking_problems else 0

        summary = report.summary
        print(f"Проект: {report.project_id}")
        print(f"Тип: {report.project_kind}")
        print(f"Папка: {Path(report.project_root).resolve()}")
        print(f"Итоговый статус: {RIGHTS_STATUS_LABELS.get(report.overall_status, report.overall_status)}")
        print()
        print(f"Всего материалов: {summary.total} (визуал {summary.visual_items}, музыка {summary.music_items}, прочее {summary.other_items})")
        print(f"  Подтверждено:     {summary.verified}")
        print(f"  Требует проверки: {summary.review_required}")
        print(f"  Заблокировано:    {summary.blocked}")
        print(f"  Нет данных:       {summary.unknown}")
        print(f"Сцен без материала: {summary.scenes_without_asset}")

        if report.items:
            print()
            print("Материалы:")
            for item in report.items:
                label = RIGHTS_STATUS_LABELS.get(item.verification_status, item.verification_status)
                scene = f" {item.scene_id}" if item.scene_id else ""
                print(f"  [{item.media_role}]{scene} {item.item_id} — {label}")
                if item.provider or item.author:
                    print(f"      источник: {item.provider or '-'} / {item.author or 'автор не указан'}")
                if item.source_page_url:
                    print(f"      страница: {item.source_page_url}")
                if item.license_name:
                    print(f"      лицензия: {item.license_name} ({item.commercial_use_status})")
                if item.local_path:
                    mark = "" if item.local_file_present else "  ← ФАЙЛ НЕ НАЙДЕН"
                    print(f"      файл: {item.local_path}{mark}")
                print(f"      записано в: {item.source_manifest}")
                for warning in item.warnings:
                    print(f"      ! {warning}")

        if report.missing_scenes:
            print()
            print("Сцены без материала (ролик нельзя считать готовым):")
            for scene in report.missing_scenes:
                print(f"  {scene.scene_id or '(без id)'} — {scene.reason or 'причина не записана'}")

        if report.warnings:
            print()
            for warning in report.warnings:
                print(f"! {warning}")

        print()
        print(f"Прочитанные манифесты: {', '.join(report.sources_read) or 'ни одного'}")
        print(
            "Отчёт показывает только то, что записано в проекте. Он не является юридическим "
            "подтверждением прав: статусы «требует проверки» и «нет данных» нужно закрывать вручную."
        )
        return 1 if report.has_blocking_problems else 0

    if repository.detect_kind(args.project_id) != PROJECT_KIND_PROJECT_MANIFEST:
        print(
            f"[project] Действие {args.action!r} пока поддерживается только для проектов с project.json "
            "(story_card). Для проектов news_to_short используйте 'project status' и 'project rights-report'."
        )
        return 1

    factory = ProjectFactory(base_dir=repository.project_root(args.project_id).parent)
    try:
        manifest = factory.get(args.project_id)
    except ProjectFoundationError as exc:
        print(f"[project] {exc}")
        return 1
    if args.action == "validate":
        channel = ChannelRegistry().get(manifest.channel_id)
        policy = ChannelOutputPolicy.from_dict(channel.output_policy)
        bundle = EvidenceBundle.load(manifest.project_root, manifest.project_id)
        result = validate_policy(policy, channel, manifest, bundle.summary())
        print_json_fn(result.to_dict()) if getattr(args, "json_output", False) else print(result.to_dict())
        return 0 if result.allowed else 1
    raise SystemExit(f"Unknown project action: {args.action!r}")


__all__ = ["register_commands", "handle_project"]
