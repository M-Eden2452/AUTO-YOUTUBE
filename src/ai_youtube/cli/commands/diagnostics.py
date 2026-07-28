from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from src.content_creation import capabilities
from src.content_creation.commands import authoring as _register_authoring
from src.content_creation.commands import catalog as _register_catalog
from src.content_creation.presentation import RIGHTS_STATUS_LABELS
from src.production_catalog.catalog import get_default_catalog
from src.production_catalog.models import CatalogValidationError


def register_commands(subparsers: Any, *, common: argparse.ArgumentParser) -> None:
    _register_catalog.register_commands(subparsers, common=common)
    _register_authoring.register_commands(subparsers, common=common)


def handle_diagnostics(args: argparse.Namespace, *, resolve_paths_fn: Any, print_json_fn: Any) -> int:
    command = args.command

    if command == "applications":
        cat = get_default_catalog()
        if args.action == "show":
            if not args.application:
                raise SystemExit("applications show requires --application.")
            data = cat.applications.get(args.application).to_dict()
        else:
            apps = cat.applications.list_all()
            if not args.all:
                apps = [
                    app
                    for app in apps
                    if app.enabled and app.implementation_status == "active"
                ]
            data = [app.to_dict() for app in apps]
        print_json_fn(data) if args.json_output else _print_plain(data)
        return 0

    if command == "capabilities":
        report = capabilities.build_capabilities_report()
        if args.json_output:
            print_json_fn(report)
        else:
            for app in report["applications"]:
                print(
                    f"[capabilities] application={app['application_id']} "
                    f"enabled={app['enabled']} "
                    f"status={app['implementation_status']}"
                )
            for template in report["templates"]:
                print(
                    f"[capabilities] template={template['template_id']} format={template['format_id']} "
                    f"voice_required={template['voice_required']} tested_status={template['tested_status']}"
                )
            for provider in report["voice_providers"]:
                print(f"[capabilities] voice_provider={provider['provider_id']} paid={provider['paid']} configured={provider['configured']}")
            for style in report["subtitle_styles"]:
                print(f"[capabilities] subtitle_style={style['style_id']} status={style['status']}")
            for option in report["music_options"]:
                print(f"[capabilities] music_option={option['mode_id']} status={option['status']}")
            for channel in report["channels"]:
                print(f"[capabilities] channel={channel['channel_id']} type={channel['channel_profile_type']}")
        return 0

    if command == "formats":
        cat = get_default_catalog()
        if args.action == "show":
            if not args.format:
                raise SystemExit("formats show requires --format.")
            data = cat.formats.get(args.format).to_dict()
        else:
            data = cat.formats.serialize()
        print_json_fn(data) if args.json_output else _print_plain(data)
        return 0

    if command == "templates":
        cat = get_default_catalog()
        try:
            if args.action == "show":
                if not args.template:
                    raise SystemExit("templates show requires --template.")
                data = cat.templates.get(args.template).to_dict()
            elif args.format:
                data = [t.to_dict() for t in cat.templates.filter_by_format(args.format)]
            else:
                data = cat.templates.serialize()
        except CatalogValidationError as exc:
            raise SystemExit(str(exc)) from exc
        print_json_fn(data) if args.json_output else _print_plain(data)
        return 0

    if command == "channels":
        if args.action == "show":
            if not args.channel:
                raise SystemExit("channels show requires --channel.")
            if args.explain:
                return _channels_explain(args, print_json_fn=print_json_fn)
            data = next((c for c in capabilities.list_channels() if c["channel_id"] == args.channel), None)
            if data is None:
                raise SystemExit(f"Unknown channel_id: {args.channel!r}.")
        else:
            data = capabilities.list_channels()
        print_json_fn(data) if args.json_output else _print_plain(data)
        return 0

    if command == "voices":
        if args.action == "explain":
            if not args.channel:
                raise SystemExit("voices explain requires --channel.")
            return _voices_explain(args, print_json_fn=print_json_fn)
        if args.action == "providers":
            data = capabilities.list_voice_providers()
        elif args.action == "profiles":
            if not args.channel:
                raise SystemExit("voices profiles requires --channel.")
            data = capabilities.list_voice_profiles(args.channel)
        else:
            if not args.channel or not args.voice_profile:
                raise SystemExit("voices show requires --channel and --voice-profile.")
            profile_id = capabilities.resolve_voice_profile(args.channel, args.voice_profile)
            data = next((p for p in capabilities.list_voice_profiles(args.channel) if p["profile_id"] == profile_id), None)
        print_json_fn(data) if args.json_output else _print_plain(data)
        return 0

    if command == "subtitles":
        if args.action in {"explain", "validate"}:
            if not args.project_id:
                raise SystemExit(f"subtitles {args.action} requires --project-id.")
            return _subtitles_explain(args, print_json_fn=print_json_fn) if args.action == "explain" else _subtitles_validate(args, print_json_fn=print_json_fn)
        styles = capabilities.list_subtitle_styles()
        if args.action == "show":
            if not args.style:
                raise SystemExit("subtitles show requires --style.")
            data = next((s for s in styles if s["style_id"] == args.style), None)
            if data is None:
                raise SystemExit(f"Unknown subtitle style: {args.style!r}.")
        else:
            data = styles
        print_json_fn(data) if args.json_output else _print_plain(data)
        return 0

    if command == "script":
        return _run_script_command(args, print_json_fn=print_json_fn)

    if command == "visual-plan":
        return _run_visual_plan_command(args, print_json_fn=print_json_fn)

    if command == "run-stage":
        from src.news.pipeline import run_news_to_short_job

        projects_root = args._application_paths.find_project_root(args.project_id).parent
        result = run_news_to_short_job(
            projects_root=projects_root,
            job_id=args.project_id,
            stage=args.stage,
            execute_voice=args.execute_voice,
        )
        print(f"[run-stage] status={result.status} completed_stages={result.completed_stages}")
        return 0

    raise SystemExit(f"Unknown command: {command!r}")


def _print_plain(data: Any) -> None:
    if isinstance(data, list):
        for item in data:
            print(item)
    else:
        print(data)


def _channels_explain(args: argparse.Namespace, *, print_json_fn: Any) -> int:
    from src.config_resolver import ConfigResolutionError, resolve_config

    template_id, format_id = _explain_template_and_format(args)
    try:
        resolved = resolve_config(
            channel_id=args.channel,
            template_id=template_id,
            format_id=format_id,
            language=args.language or "",
            project_id=args.project_id or "",
            channels_dir=args.channels_root,
            projects_dir=args.projects_root,
            projects_fallback_dirs=args.project_fallback_roots,
        )
    except ConfigResolutionError as exc:
        if args.json_output:
            print_json_fn({"status": "failed", "error": str(exc), "reason": exc.reason})
        else:
            print(f"[explain] error: {exc}")
        return 1

    if args.json_output:
        print_json_fn(resolved.to_dict(include_trace=bool(args.trace)))
        return 0

    print(f"[explain] channel={args.channel} template={template_id or '-'} format={format_id or '-'} language={args.language or '-'}")
    for row in resolved.explain_rows():
        note = f"  ({', '.join(row['warnings'])})" if row["warnings"] else ""
        value = row["value"] if len(row["value"]) <= 26 else row["value"][:23] + "..."
        print(f"  {row['key']:<32} {value:<26} ← {row['resolved_from']:<22} {row['origin']}{note}")
    if args.trace:
        for layer in resolved.layers:
            state = layer.note or f"{len(layer.values)} настроек"
            print(f"  [layer {layer.priority:>2}] {layer.source:<22} {state}")
    for warning in resolved.warnings:
        print(f"  [!] {warning}")
    return 0


def _explain_template_and_format(args: argparse.Namespace) -> tuple[str, str]:
    template_id = getattr(args, "template", "") or ""
    if not template_id:
        channel = next((c for c in capabilities.list_channels() if c["channel_id"] == args.channel), None)
        supported = (channel or {}).get("supported_templates") or []
        template_id = str((channel or {}).get("default_template") or "") or (supported[0] if supported else "")
    format_id = getattr(args, "format_id", "") or ""
    if not format_id and template_id:
        try:
            format_id = get_default_catalog().templates.get(template_id).format_id
        except CatalogValidationError:
            format_id = ""
    return template_id, format_id


def _explain_languages(args: argparse.Namespace) -> list[str]:
    if args.language:
        return [args.language]
    channel = next((c for c in capabilities.list_channels() if c["channel_id"] == args.channel), None)
    supported = list((channel or {}).get("supported_languages") or [])
    if supported:
        return supported
    from src.localization import known_language_codes

    return list(known_language_codes())


def _voices_explain(args: argparse.Namespace, *, print_json_fn: Any) -> int:
    from src.config_resolver import ConfigResolutionError
    from src.localization import resolve_localization, validate_localization_set

    template_id, format_id = _explain_template_and_format(args)
    project_root = None
    if args.project_id:
        project_root = args._application_paths.find_project_root(args.project_id)

    resolved = []
    for language in _explain_languages(args):
        try:
            resolved.append(
                resolve_localization(
                    channel_id=args.channel,
                    template_id=template_id,
                    format_id=format_id,
                    language=language,
                    project_id=args.project_id or "",
                    project_root=project_root,
                    projects_dir=args.projects_root,
                    projects_fallback_dirs=args.project_fallback_roots,
                    channels_dir=args.channels_root,
                    voice_provider_override=getattr(args, "voice_provider", "") or "",
                    voice_profile_override=args.voice_profile or "",
                )
            )
        except ConfigResolutionError as exc:
            if args.json_output:
                print_json_fn({"status": "failed", "error": str(exc), "reason": exc.reason})
            else:
                print(f"[localization] error: {exc}")
            return 1

    issues = validate_localization_set(resolved)
    if args.json_output:
        print_json_fn(
            {
                "channel_id": args.channel,
                "template_id": template_id,
                "format_id": format_id,
                "project_id": args.project_id or "",
                "localizations": [
                    item.to_dict(include_config=True, include_trace=bool(args.trace)) for item in resolved
                ],
                "issues": [issue.to_dict() for issue in issues],
            }
        )
        return 0

    for item in resolved:
        print(
            f"[localization] {item.localization_id} ({item.locale or '-'})  "
            f"статус={item.status} источник_озвучки={item.narration_source}"
        )
        for row in item.explain_rows():
            value = "—" if row["value"] in (None, "") else str(row["value"])
            value = value if len(value) <= 26 else value[:23] + "..."
            source = row["resolved_from"] or "-"
            note = f"  ({', '.join(row['warnings'])})" if row["warnings"] else ""
            print(f"    {row['key']:<24} {value:<26} ← {source:<22} {row['origin']}{note}")
        if item.existing_narration_path:
            reuse = "будет переиспользована" if item.reuse_existing_narration else "несовместима, не используется"
            print(f"    готовая озвучка          {item.existing_narration_path} ({reuse})")
        tts_line = "да" if item.tts_allowed else f"нет — {item.tts_blocked_reason or 'причина не указана'}"
        print(f"    TTS будет вызван         {tts_line}")
        if item.fallback_applied:
            print(f"    fallback                 {item.fallback_reason}")
        if args.trace and item.config is not None:
            for layer in item.config.layers:
                state = layer.note or f"{len(layer.values)} настроек"
                print(f"    [layer {layer.priority:>2}] {layer.source:<22} {state}")
    for issue in issues:
        print(f"  [{issue.severity}] {issue.localization_id or '-'}: {issue.message}")
    return 0 if all(not issue.is_error for issue in issues) else 1


def _subtitle_project_context(args: argparse.Namespace) -> tuple[Path, str, str, dict[str, Any], dict[str, Any] | None]:
    import json as _json

    from src.projects import ProjectNotFoundError, ProjectRepository

    try:
        view = ProjectRepository(
            args.projects_root, fallback_roots=args.project_fallback_roots
        ).get(args.project_id)
    except ProjectNotFoundError as exc:
        raise SystemExit(f"[subtitles] {exc}")
    root = Path(view.project_root)
    localization = str(getattr(args, "language", "") or view.language or "")
    if not localization:
        raise SystemExit("[subtitles] У проекта не указан язык; передайте --language.")
    script_path = root / "localizations" / localization / "script" / "script.json"
    if not script_path.is_file():
        raise SystemExit(f"[subtitles] Нет сценария: {script_path}")
    script = _json.loads(script_path.read_text(encoding="utf-8"))
    voice_path = root / "localizations" / localization / "voice" / "voice_manifest.json"
    voice = _json.loads(voice_path.read_text(encoding="utf-8")) if voice_path.is_file() else None
    return root, localization, view.channel_id, script, voice


def _subtitle_result_for_project(args: argparse.Namespace):
    import json as _json

    from src.news.subtitles import NEWS_FORMAT_ID
    from src.news.voice_adapter import resolve_localization_for_channel
    from src.subtitles import (
        SubtitlePolicy,
        SubtitleRequest,
        build_subtitle_result,
        resolve_subtitle_style,
    )

    root, localization_id, channel_id, script, voice = _subtitle_project_context(args)
    resolved = resolve_localization_for_channel(
        channel_id=channel_id,
        language=localization_id,
        project_root=root,
        project_id=args.project_id,
        projects_dir=args.projects_root,
        projects_fallback_dirs=args.project_fallback_roots,
        channels_dir=args.channels_root,
    )
    visual_path = root / "localizations" / localization_id / "visual" / "visual_plan.json"
    visual = _json.loads(visual_path.read_text(encoding="utf-8")) if visual_path.is_file() else {}
    style = resolve_subtitle_style(channel_id=channel_id, resolution=visual.get("resolution"))
    subtitle_language = str(getattr(resolved, "subtitle_language", "") or "")
    result = build_subtitle_result(
        SubtitleRequest(
            script=script,
            localization_id=localization_id,
            language=subtitle_language or str(getattr(resolved, "language", "") or localization_id),
            subtitle_language=subtitle_language,
            voice_manifest=voice,
            policy=SubtitlePolicy.from_style(style),
            style=style,
            format_id=NEWS_FORMAT_ID,
        )
    )
    return root, localization_id, result


def _subtitles_explain(args: argparse.Namespace, *, print_json_fn: Any) -> int:
    from src.subtitles import artifact_paths, explain_scene_mapping, manifest_path, plan_resume, read_manifest

    root, localization_id, result = _subtitle_result_for_project(args)
    existing = read_manifest(manifest_path(root, localization_id))
    decision = plan_resume(existing, result, project_root=root, localization_id=localization_id)
    paths = {name: str(path) for name, path in artifact_paths(root, localization_id, result.formats).items()}
    mapping = explain_scene_mapping(result)

    if args.json_output:
        print_json_fn(
            {
                "project_id": args.project_id,
                "localization_id": localization_id,
                "subtitle_language": result.language,
                "timing_source": result.timing_source,
                "scene_timeline_source": result.scene_timeline_source,
                "narration_duration_sec": round(result.narration_duration_sec, 3),
                "cue_count": len(result.cues),
                "paths": paths,
                "resume": decision.to_dict(),
                "style": result.style.to_dict(),
                "policy": result.policy.to_dict(),
                "validation": result.validation.to_dict(),
                "scenes": mapping,
            }
        )
        return 0 if result.validation.ok else 1

    print(f"[subtitles] локализация={localization_id} язык_субтитров={result.language or '-'}")
    print(f"[subtitles] источник тайминга={result.timing_source} (границы сцен: {result.scene_timeline_source})")
    print(f"[subtitles] озвучка={result.narration_duration_sec:.3f} с; cues={len(result.cues)}; сцен={result.scene_count}")
    print(f"[subtitles] стиль={result.style.source} {result.style.origin or '(значения по умолчанию)'}")
    for name, path in paths.items():
        print(f"[subtitles] {name}: {path}")
    print(f"[subtitles] resume: {'да' if decision.reuse else 'нет'} — {decision.message}")
    for row in mapping:
        print(
            f"    {row['scene_id']:<14} cues={row['cue_count']:<3} "
            f"[{row['start_sec']:7.3f} → {row['end_sec']:7.3f}] {row['timing_source']}"
        )
        if args.cues:
            for cue in row["cues"]:
                text = cue["text"].replace("\n", " ⏎ ")
                print(f"        {cue['start_sec']:7.3f}-{cue['end_sec']:7.3f}  {text}")
    for issue in result.validation.issues:
        print(f"  [{issue.severity}] {issue.code}: {issue.message}")
    return 0 if result.validation.ok else 1


def _subtitles_validate(args: argparse.Namespace, *, print_json_fn: Any) -> int:
    from src.subtitles import (
        SubtitlePolicy,
        manifest_cues,
        manifest_path,
        read_manifest,
        read_srt,
        resolve_subtitle_style,
        subtitle_dir,
        validate_cues,
    )

    root, localization_id, _channel_id, script, _voice = _subtitle_project_context(args)
    target = manifest_path(root, localization_id)
    manifest = read_manifest(target)
    cues = manifest_cues(manifest)
    source = str(target)
    if not cues:
        srt_path = subtitle_dir(root, localization_id) / "subtitles.srt"
        if not srt_path.is_file():
            print(f"[subtitles] Артефакта нет: ни {target}, ни {srt_path}.")
            return 1
        cues = read_srt(srt_path, language=str(manifest.get("language") or ""))
        source = str(srt_path)

    style = resolve_subtitle_style(channel_id=_channel_id)
    policy = SubtitlePolicy.from_style(style)
    scene_order = tuple(
        str(scene.get("scene_id") or "") for scene in (script.get("scenes") or []) if isinstance(scene, dict)
    )
    result = validate_cues(
        cues,
        policy=policy,
        language=str(manifest.get("subtitle_language") or manifest.get("language") or ""),
        scene_order=scene_order if any(cue.scene_id for cue in cues) else (),
        narration_duration_sec=float(manifest.get("narration_duration_sec") or 0.0),
    )
    if args.json_output:
        print_json_fn(
            {
                "project_id": args.project_id,
                "localization_id": localization_id,
                "artifact": source,
                "schema_version": manifest.get("schema_version") or 0,
                "cue_count": len(cues),
                "validation": result.to_dict(),
            }
        )
        return 0 if result.ok else 1
    print(f"[subtitles] артефакт={source}")
    print(f"[subtitles] схема={manifest.get('schema_version') or 'до Q3 (метаданных нет)'} cues={len(cues)}")
    print(f"[subtitles] результат={result.status}")
    for issue in result.issues:
        print(f"  [{issue.severity}] {issue.code}: {issue.message}")
    return 0 if result.ok else 1


def _run_script_command(args: argparse.Namespace, *, print_json_fn: Any) -> int:
    from src.content.script_engine import from_legacy_script, list_capabilities, validate_script
    from src.content_creation.request_builder import load_visual_briefs
    from src.news.models import INPUT_MODE_TEXT, INPUT_MODE_TOPIC, NewsJob
    from src.news.research_engine import build_research
    from src.news.script_generator import generate_for_job

    if args.action == "providers":
        data = [item.to_dict() for item in list_capabilities()]
        if args.json_output:
            print_json_fn(data)
        else:
            for item in data:
                paid = "платный" if item["requires_paid_api"] else "бесплатный"
                net = "нужна сеть" if item["requires_network"] else "офлайн"
                print(f"[script] {item['provider_id']}: {item['display_name']} ({paid}, {net}, {item['implementation_status']})")
                print(f"          {item['description']}")
        return 0

    if args.action == "validate":
        if not args.script_json_path:
            raise SystemExit("script validate requires --script-file <path to script.json>.")
        path = Path(args.script_json_path)
        if not path.is_file():
            raise SystemExit(f"Файл не найден: {path}")
        result = from_legacy_script(json.loads(path.read_text(encoding="utf-8")))
        validation = validate_script(result, expected_language=result.language)
        payload = {"script_file": str(path), "scene_count": len(result.scenes), **validation.to_dict()}
        if args.json_output:
            print_json_fn(payload)
        else:
            _print_script_validation(validation, scene_count=len(result.scenes))
        return 0 if validation.valid else 1

    text = args.text
    if args.text_file:
        text = Path(args.text_file).read_text(encoding="utf-8")
    if not text and not args.topic:
        raise SystemExit("script generate requires --topic, --text or --text-file.")

    source_kind = args.source_kind or ("research" if text else "topic")
    job = NewsJob.create(
        channel_id="",
        input_mode=INPUT_MODE_TEXT if text else INPUT_MODE_TOPIC,
        title=args.title,
        topic=args.topic,
        input_text=text,
        language=args.language,
        target_duration_sec=args.target_duration_sec,
        script_provider=args.provider,
        script_source=source_kind,
        script_include_cta=args.include_cta,
        script_cta_text=args.cta_text,
        visual_briefs=load_visual_briefs(getattr(args, "visual_brief_path", "")),
    )
    research = build_research(job, {"title": args.topic or args.title, "text": text or args.topic})
    outcome = generate_for_job(job, research)
    script = outcome.to_legacy_script(target_duration_sec=job.target_duration_sec)

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(script, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.json_output:
        print_json_fn({**outcome.to_dict(), "written_to": args.out, "script_json": script})
        return 0 if outcome.validation.valid else 1

    result = outcome.result
    print(f"[script] движок={outcome.provider_id} источник={result.source_kind} язык={result.language}")
    if outcome.used_fallback:
        print(f"[script] запрошен {outcome.requested_provider_id}, отработал {outcome.provider_id}")
    print(f"[script] сцен={len(result.scenes)} расчётная длительность={result.estimated_duration_sec:.1f} с "
          f"(цель {job.target_duration_sec} с)")
    for scene in result.scenes:
        print(f"  {scene.scene_id} [{scene.role:<11}] {scene.duration_sec:5.1f} с  {scene.narration[:70]}")
        if scene.visual_brief:
            brief = scene.visual_brief
            print(
                f"      визуал: класс={brief.get('source_class') or '-'} "
                f"предмет={brief.get('subject') or '-'} место={brief.get('place') or brief.get('location') or '-'}"
            )
            if brief.get("exact_entities"):
                print(f"      точные сущности: {', '.join(str(item) for item in brief['exact_entities'])}")
            if brief.get("must_avoid"):
                print(f"      запрещено: {', '.join(str(item) for item in brief['must_avoid'])}")
            if brief.get("infographic"):
                print(f"      инфографика: {json.dumps(brief['infographic'], ensure_ascii=False)}")
    for warning in result.warnings:
        print(f"[script] предупреждение: {warning}")
    _print_script_validation(outcome.validation, scene_count=len(result.scenes))
    if args.out:
        print(f"[script] script.json записан: {Path(args.out).resolve()}")
    return 0 if outcome.validation.valid else 1


def _run_visual_plan_command(args: argparse.Namespace, *, print_json_fn: Any) -> int:
    from src.content.script_engine import from_legacy_script
    from src.content.visual_planning import (
        VisualPlanRequest,
        build_plan,
        from_legacy_visual_plan,
        intent_to_query,
        list_capabilities,
        to_legacy_visual_plan,
        validate_visual_plan,
    )

    if args.action == "planners":
        data = [item.to_dict() for item in list_capabilities()]
        if args.json_output:
            print_json_fn(data)
        else:
            for item in data:
                paid = "платный" if item["requires_paid_api"] else "бесплатный"
                net = "нужна сеть" if item["requires_network"] else "офлайн"
                print(
                    f"[visual-plan] {item['planner_id']}: {item['display_name']} "
                    f"({paid}, {net}, язык intent={item['intent_language']}, {item['implementation_status']})"
                )
                print(f"              {item['description']}")
        return 0

    if args.action in {"validate", "intents"}:
        if not args.plan_json_path:
            raise SystemExit(f"visual-plan {args.action} requires --plan-file <path to visual_plan.json>.")
        path = Path(args.plan_json_path)
        if not path.is_file():
            raise SystemExit(f"Файл не найден: {path}")
        plan = from_legacy_visual_plan(json.loads(path.read_text(encoding="utf-8")))

        if args.action == "intents":
            payload = [
                {"scene_id": scene.scene_id, "intents": [intent.to_dict() for intent in scene.intents]}
                for scene in plan.scenes
            ]
            if args.json_output:
                print_json_fn(payload)
            else:
                for scene in plan.scenes:
                    print(f"[visual-plan] {scene.scene_id} ({scene.shot_type})")
                    for intent in scene.intents:
                        mark = " (нужен перевод)" if intent.requires_translation else ""
                        print(
                            f"    {intent.kind:<22} ур.{intent.fallback_level} "
                            f"[{intent.language}]{mark}  {intent_to_query(intent)}"
                        )
            return 0

        script = None
        if args.script_json_path and Path(args.script_json_path).is_file():
            script = from_legacy_script(json.loads(Path(args.script_json_path).read_text(encoding="utf-8")))
        validation = validate_visual_plan(plan, script=script)
        payload = {"plan_file": str(path), "scene_count": len(plan.scenes), **validation.to_dict()}
        if args.json_output:
            print_json_fn(payload)
        else:
            _print_plan_validation(validation, scene_count=len(plan.scenes))
        return 0 if validation.valid else 1

    if not args.script_json_path:
        raise SystemExit("visual-plan build requires --script-file <path to script.json>.")
    script_path = Path(args.script_json_path)
    if not script_path.is_file():
        raise SystemExit(f"Файл не найден: {script_path}")
    script_data = json.loads(script_path.read_text(encoding="utf-8"))
    result = from_legacy_script(script_data)

    research: dict[str, Any] = {}
    if args.claims_json_path:
        claims_path = Path(args.claims_json_path)
        if not claims_path.is_file():
            raise SystemExit(f"Файл не найден: {claims_path}")
        research = json.loads(claims_path.read_text(encoding="utf-8"))

    language = args.language or result.language or "ru"
    planning = build_plan(
        VisualPlanRequest(
            script=result,
            language=language,
            topic=str(research.get("topic") or result.title or ""),
            title=str(result.title or ""),
            claims=list(research.get("claims") or []),
            planner_id=args.planner,
        ),
        source_text=str(research.get("summary") or ""),
    )
    stored = to_legacy_visual_plan(planning.result, language=language, script=script_data)

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(stored, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.json_output:
        print_json_fn({**planning.to_dict(), "written_to": args.out, "visual_plan_json": stored})
        return 0 if planning.validation.valid else 1

    plan = planning.result
    print(f"[visual-plan] планировщик={planning.planner_id} тема={plan.topic_entity!r} язык={plan.language}")
    for scene in plan.scenes:
        print(f"  {scene.scene_id} [{scene.shot_type:<12}] {scene.preferred_media_kind:<15} {scene.meaning[:56]}")
        print(
            f"      предмет={scene.subject!r} действие={scene.action!r} "
            f"место={scene.place!r} эпоха={scene.period!r}"
        )
        for intent in scene.intents:
            print(f"      -> ур.{intent.fallback_level} {intent.kind:<22} {intent_to_query(intent)}")
        for warning in scene.warnings:
            print(f"      предупреждение: {warning}")
    for warning in plan.warnings:
        print(f"[visual-plan] предупреждение: {warning}")
    _print_plan_validation(planning.validation, scene_count=len(plan.scenes))
    if args.out:
        print(f"[visual-plan] visual_plan.json записан: {Path(args.out).resolve()}")
    return 0 if planning.validation.valid else 1


def _print_plan_validation(validation, *, scene_count: int) -> None:
    label = {"passed": "проверка пройдена", "needs_review": "нужна проверка", "failed": "не проходит"}
    print(f"[visual-plan] {label.get(validation.status, validation.status)} (сцен: {scene_count})")
    for issue in validation.issues:
        mark = "ошибка " if issue.severity == "error" else "внимание"
        where = f" [{issue.scene_id}]" if issue.scene_id else ""
        print(f"  {mark}{where} {issue.code}: {issue.message}")


def _print_script_validation(validation, *, scene_count: int) -> None:
    label = {"passed": "проверка пройдена", "needs_review": "нужна проверка", "failed": "не проходит"}
    print(f"[script] {label.get(validation.status, validation.status)} (сцен: {scene_count})")
    for issue in validation.issues:
        mark = "ошибка " if issue.severity == "error" else "внимание"
        where = f" [{issue.scene_id}]" if issue.scene_id else ""
        print(f"  {mark}{where} {issue.code}: {issue.message}")


__all__ = ["register_commands", "handle_diagnostics"]
