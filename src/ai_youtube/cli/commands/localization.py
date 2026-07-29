from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from src.ai_youtube.cli import presentation
from src.content_creation import capabilities
from src.production_catalog.catalog import get_default_catalog
from src.production_catalog.models import CatalogValidationError


COMMANDS = frozenset({"channels", "voices", "subtitles"})


def handle_localization(args: argparse.Namespace, *, print_json_fn: Any) -> int:
    command = args.command

    if command == "channels":
        if args.action == "show":
            if not args.channel:
                raise SystemExit("channels show requires --channel.")
            if args.explain:
                return channels_explain(args, print_json_fn=print_json_fn)
            data = next(
                (
                    channel
                    for channel in capabilities.list_channels()
                    if channel["channel_id"] == args.channel
                ),
                None,
            )
            if data is None:
                raise SystemExit(f"Unknown channel_id: {args.channel!r}.")
        else:
            data = capabilities.list_channels()
        print_json_fn(data) if args.json_output else presentation.print_plain(data)
        return 0

    if command == "voices":
        if args.action == "explain":
            if not args.channel:
                raise SystemExit("voices explain requires --channel.")
            return voices_explain(args, print_json_fn=print_json_fn)
        if args.action == "providers":
            data = capabilities.list_voice_providers()
        elif args.action == "profiles":
            if not args.channel:
                raise SystemExit("voices profiles requires --channel.")
            data = capabilities.list_voice_profiles(args.channel)
        else:
            if not args.channel or not args.voice_profile:
                raise SystemExit(
                    "voices show requires --channel and --voice-profile."
                )
            profile_id = capabilities.resolve_voice_profile(
                args.channel,
                args.voice_profile,
            )
            data = next(
                (
                    profile
                    for profile in capabilities.list_voice_profiles(args.channel)
                    if profile["profile_id"] == profile_id
                ),
                None,
            )
        print_json_fn(data) if args.json_output else presentation.print_plain(data)
        return 0

    if command == "subtitles":
        if args.action in {"explain", "validate"}:
            if not args.project_id:
                raise SystemExit(
                    f"subtitles {args.action} requires --project-id."
                )
            if args.action == "explain":
                return subtitles_explain(args, print_json_fn=print_json_fn)
            return subtitles_validate(args, print_json_fn=print_json_fn)
        styles = capabilities.list_subtitle_styles()
        if args.action == "show":
            if not args.style:
                raise SystemExit("subtitles show requires --style.")
            data = next(
                (style for style in styles if style["style_id"] == args.style),
                None,
            )
            if data is None:
                raise SystemExit(f"Unknown subtitle style: {args.style!r}.")
        else:
            data = styles
        print_json_fn(data) if args.json_output else presentation.print_plain(data)
        return 0

    raise SystemExit(f"Unknown localization command: {command!r}")


def channels_explain(args: argparse.Namespace, *, print_json_fn: Any) -> int:
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
            print_json_fn(
                {
                    "status": "failed",
                    "error": str(exc),
                    "reason": exc.reason,
                }
            )
        else:
            print(f"[explain] error: {exc}")
        return 1

    if args.json_output:
        print_json_fn(resolved.to_dict(include_trace=bool(args.trace)))
        return 0

    presentation.print_config_explanation(
        args,
        resolved,
        template_id=template_id,
        format_id=format_id,
    )
    return 0


def _explain_template_and_format(args: argparse.Namespace) -> tuple[str, str]:
    template_id = getattr(args, "template", "") or ""
    if not template_id:
        channel = next(
            (
                item
                for item in capabilities.list_channels()
                if item["channel_id"] == args.channel
            ),
            None,
        )
        supported = (channel or {}).get("supported_templates") or []
        template_id = str((channel or {}).get("default_template") or "") or (
            supported[0] if supported else ""
        )
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
    channel = next(
        (
            item
            for item in capabilities.list_channels()
            if item["channel_id"] == args.channel
        ),
        None,
    )
    supported = list((channel or {}).get("supported_languages") or [])
    if supported:
        return supported
    from src.localization import known_language_codes

    return list(known_language_codes())


def voices_explain(args: argparse.Namespace, *, print_json_fn: Any) -> int:
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
                    voice_provider_override=(
                        getattr(args, "voice_provider", "") or ""
                    ),
                    voice_profile_override=args.voice_profile or "",
                )
            )
        except ConfigResolutionError as exc:
            if args.json_output:
                print_json_fn(
                    {
                        "status": "failed",
                        "error": str(exc),
                        "reason": exc.reason,
                    }
                )
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
                    item.to_dict(
                        include_config=True,
                        include_trace=bool(args.trace),
                    )
                    for item in resolved
                ],
                "issues": [issue.to_dict() for issue in issues],
            }
        )
        return 0

    presentation.print_localizations(args, resolved, issues)
    return 0 if all(not issue.is_error for issue in issues) else 1


def _subtitle_project_context(
    args: argparse.Namespace,
) -> tuple[Path, str, str, dict[str, Any], dict[str, Any] | None]:
    import json

    from src.projects import ProjectNotFoundError, ProjectRepository

    try:
        view = ProjectRepository(
            args.projects_root,
            fallback_roots=args.project_fallback_roots,
        ).get(args.project_id)
    except ProjectNotFoundError as exc:
        raise SystemExit(f"[subtitles] {exc}")
    root = Path(view.project_root)
    localization = str(
        getattr(args, "language", "") or view.language or ""
    )
    if not localization:
        raise SystemExit(
            "[subtitles] У проекта не указан язык; передайте --language."
        )
    script_path = (
        root
        / "localizations"
        / localization
        / "script"
        / "script.json"
    )
    if not script_path.is_file():
        raise SystemExit(f"[subtitles] Нет сценария: {script_path}")
    script = json.loads(script_path.read_text(encoding="utf-8"))
    voice_path = (
        root
        / "localizations"
        / localization
        / "voice"
        / "voice_manifest.json"
    )
    voice = (
        json.loads(voice_path.read_text(encoding="utf-8"))
        if voice_path.is_file()
        else None
    )
    return root, localization, view.channel_id, script, voice


def _subtitle_result_for_project(args: argparse.Namespace):
    import json

    from src.news.subtitles import NEWS_FORMAT_ID
    from src.news.voice_adapter import resolve_localization_for_channel
    from src.subtitles import (
        SubtitlePolicy,
        SubtitleRequest,
        build_subtitle_result,
        resolve_subtitle_style,
    )

    root, localization_id, channel_id, script, voice = (
        _subtitle_project_context(args)
    )
    resolved = resolve_localization_for_channel(
        channel_id=channel_id,
        language=localization_id,
        project_root=root,
        project_id=args.project_id,
        projects_dir=args.projects_root,
        projects_fallback_dirs=args.project_fallback_roots,
        channels_dir=args.channels_root,
    )
    visual_path = (
        root
        / "localizations"
        / localization_id
        / "visual"
        / "visual_plan.json"
    )
    visual = (
        json.loads(visual_path.read_text(encoding="utf-8"))
        if visual_path.is_file()
        else {}
    )
    style = resolve_subtitle_style(
        channel_id=channel_id,
        resolution=visual.get("resolution"),
    )
    subtitle_language = str(
        getattr(resolved, "subtitle_language", "") or ""
    )
    result = build_subtitle_result(
        SubtitleRequest(
            script=script,
            localization_id=localization_id,
            language=(
                subtitle_language
                or str(
                    getattr(resolved, "language", "")
                    or localization_id
                )
            ),
            subtitle_language=subtitle_language,
            voice_manifest=voice,
            policy=SubtitlePolicy.from_style(style),
            style=style,
            format_id=NEWS_FORMAT_ID,
        )
    )
    return root, localization_id, result


def subtitles_explain(
    args: argparse.Namespace,
    *,
    print_json_fn: Any,
) -> int:
    from src.subtitles import (
        artifact_paths,
        explain_scene_mapping,
        manifest_path,
        plan_resume,
        read_manifest,
    )

    root, localization_id, result = _subtitle_result_for_project(args)
    existing = read_manifest(manifest_path(root, localization_id))
    decision = plan_resume(
        existing,
        result,
        project_root=root,
        localization_id=localization_id,
    )
    paths = {
        name: str(path)
        for name, path in artifact_paths(
            root,
            localization_id,
            result.formats,
        ).items()
    }
    mapping = explain_scene_mapping(result)

    if args.json_output:
        print_json_fn(
            {
                "project_id": args.project_id,
                "localization_id": localization_id,
                "subtitle_language": result.language,
                "timing_source": result.timing_source,
                "scene_timeline_source": result.scene_timeline_source,
                "narration_duration_sec": round(
                    result.narration_duration_sec,
                    3,
                ),
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

    presentation.print_subtitle_explanation(
        args,
        localization_id=localization_id,
        result=result,
        decision=decision,
        paths=paths,
        mapping=mapping,
    )
    return 0 if result.validation.ok else 1


def subtitles_validate(
    args: argparse.Namespace,
    *,
    print_json_fn: Any,
) -> int:
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

    root, localization_id, channel_id, script, _voice = (
        _subtitle_project_context(args)
    )
    target = manifest_path(root, localization_id)
    manifest = read_manifest(target)
    cues = manifest_cues(manifest)
    source = str(target)
    if not cues:
        srt_path = subtitle_dir(root, localization_id) / "subtitles.srt"
        if not srt_path.is_file():
            print(
                f"[subtitles] Артефакта нет: ни {target}, ни {srt_path}."
            )
            return 1
        cues = read_srt(
            srt_path,
            language=str(manifest.get("language") or ""),
        )
        source = str(srt_path)

    style = resolve_subtitle_style(channel_id=channel_id)
    policy = SubtitlePolicy.from_style(style)
    scene_order = tuple(
        str(scene.get("scene_id") or "")
        for scene in (script.get("scenes") or [])
        if isinstance(scene, dict)
    )
    result = validate_cues(
        cues,
        policy=policy,
        language=str(
            manifest.get("subtitle_language")
            or manifest.get("language")
            or ""
        ),
        scene_order=scene_order if any(cue.scene_id for cue in cues) else (),
        narration_duration_sec=float(
            manifest.get("narration_duration_sec") or 0.0
        ),
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

    presentation.print_subtitle_validation(
        source=source,
        manifest=manifest,
        cues=cues,
        result=result,
    )
    return 0 if result.ok else 1


__all__ = [
    "COMMANDS",
    "channels_explain",
    "handle_localization",
    "subtitles_explain",
    "subtitles_validate",
    "voices_explain",
]
