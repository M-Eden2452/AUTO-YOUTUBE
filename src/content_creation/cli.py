from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from src.content_creation import capabilities
from src.content_creation.models import (
    ContentCreationError,
    ContentCreationRequest,
    ExecutionFlags,
    MusicRequestConfig,
    RenderRequestConfig,
    SubtitleRequestConfig,
    TimingRequestConfig,
    VoiceRequestConfig,
)
from src.content_creation.output_report import describe_output_file
from src.content_creation.service import create_content
from src.production_catalog.catalog import get_default_catalog
from src.production_catalog.models import CatalogValidationError


def configure_console_encoding() -> None:
    # Mirrors pipeline.py's own helper (not imported from there - this CLI must
    # stay independent of pipeline.py, like src.project_foundation.cli). Without
    # this, printing Cyrillic text crashes on a default-codepage Windows console.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def _json_flag_parser() -> argparse.ArgumentParser:
    # A shared `parents=[...]` parser so these work both before and after the
    # subcommand (argparse subparsers otherwise only accept flags defined on the
    # specific subparser they belong to).
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", dest="json_output", action="store_true", help="Print machine-readable JSON.")
    common.add_argument(
        "--debug", action="store_true", help="Show full tracebacks instead of a short error message."
    )
    common.add_argument(
        "--no-icons", action="store_true", help="Use ASCII markers instead of emoji (wizard only)."
    )
    common.add_argument(
        "--workspace",
        default=None,
        help=(
            "Runtime workspace root. Relative paths are anchored to the repository; "
            "overrides AI_YOUTUBE_WORKSPACE and path config."
        ),
    )
    common.add_argument(
        "--paths-config",
        default=None,
        help="Optional JSON path configuration; overrides AI_YOUTUBE_PATHS_CONFIG.",
    )
    return common


def build_parser() -> argparse.ArgumentParser:
    json_flag = _json_flag_parser()
    parser = argparse.ArgumentParser(
        prog="content-creation",
        description=(
            "Unified content-creation CLI: one create/wizard command over the existing "
            "Production Catalog, Project Foundation, VoiceProfileRegistry and renderers. "
            "Never runs paid TTS without --approve-paid-generation."
        ),
        parents=[json_flag],
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser(
        "capabilities",
        help="Show what formats/templates/voices/subtitles/music are usable today.",
        parents=[json_flag],
    )

    formats_p = subparsers.add_parser(
        "formats", help="List/inspect formats from the Production Catalog.", parents=[json_flag]
    )
    formats_p.add_argument("action", choices=["list", "show"], nargs="?", default="list")
    formats_p.add_argument("--format", help="format_id for 'show'.")

    templates_p = subparsers.add_parser(
        "templates", help="List/inspect templates from the Production Catalog.", parents=[json_flag]
    )
    templates_p.add_argument("action", choices=["list", "show"], nargs="?", default="list")
    templates_p.add_argument("--template", help="template_id or legacy alias for 'show'.")
    templates_p.add_argument("--format", help="Filter list by format_id.")

    channels_p = subparsers.add_parser("channels", help="List/inspect channels.", parents=[json_flag])
    channels_p.add_argument("action", choices=["list", "show"], nargs="?", default="list")
    channels_p.add_argument("--channel", help="channel_id for 'show'.")
    channels_p.add_argument(
        "--explain",
        action="store_true",
        help="For 'show': print «параметр → значение → откуда взято» via the ConfigResolver. Read-only.",
    )
    channels_p.add_argument("--template", help="With --explain: template_id whose policy layer to apply.")
    channels_p.add_argument("--format", dest="format_id", help="With --explain: format_id whose policy layer to apply.")
    channels_p.add_argument("--language", help="With --explain: language whose localization layer to apply.")
    channels_p.add_argument("--project-id", help="With --explain: project whose manifest layer to apply.")
    channels_p.add_argument(
        "--trace", action="store_true", help="With --explain: also print every layer that was considered."
    )

    voices_p = subparsers.add_parser(
        "voices", help="List voice providers/profiles, or explain a localization's voice.", parents=[json_flag]
    )
    voices_p.add_argument("action", choices=["providers", "profiles", "show", "explain"])
    voices_p.add_argument("--channel", help="channel_id for 'profiles'/'show'/'explain'.")
    voices_p.add_argument("--voice-profile", help="Profile id, alias, or display name (e.g. \"Дом\") for 'show'.")
    voices_p.add_argument("--language", help="With 'explain': localization to explain (default: every one).")
    voices_p.add_argument("--template", help="With 'explain': template_id whose policy layer to apply.")
    voices_p.add_argument("--format", dest="format_id", help="With 'explain': format_id whose policy layer to apply.")
    voices_p.add_argument("--project-id", help="With 'explain': project whose manifest and narration to inspect.")
    voices_p.add_argument("--projects-root", default=None)
    voices_p.add_argument("--voice-provider", help="With 'explain': provider as an explicit runtime override.")
    voices_p.add_argument(
        "--trace", action="store_true", help="With 'explain': also print every configuration layer considered."
    )

    subtitles_p = subparsers.add_parser(
        "subtitles",
        help="List subtitle styles, or explain/validate a project's subtitles (read-only).",
        parents=[json_flag],
    )
    subtitles_p.add_argument("action", choices=["list", "show", "explain", "validate"], nargs="?", default="list")
    subtitles_p.add_argument("--style", help="style_id for 'show'.")
    subtitles_p.add_argument("--project-id", help="Required for 'explain'/'validate'.")
    subtitles_p.add_argument("--language", help="Localization id (default: the project's own).")
    subtitles_p.add_argument("--projects-root", default=None)
    subtitles_p.add_argument(
        "--cues", action="store_true", help="With 'explain': print every cue, not just the per-scene summary."
    )

    project_p = subparsers.add_parser("project", help="Inspect existing projects.", parents=[json_flag])
    project_p.add_argument("action", choices=["list", "status", "validate", "rights-report"])
    project_p.add_argument("--project-id", help="Required for every action except 'list'.")
    project_p.add_argument("--projects-root", default=None)

    assets_p = subparsers.add_parser(
        "assets", help="Manage visual slots in an existing news project.", parents=[json_flag]
    )
    assets_p.add_argument("action", choices=["replace"])
    assets_p.add_argument("--project-id", required=True)
    assets_p.add_argument("--scene-id", required=True)
    assets_p.add_argument("--slot-id", required=True)
    assets_p.add_argument(
        "--file",
        required=True,
        help="Local media to import without modifying the original.",
    )
    assets_p.add_argument("--source-url", default="", help="Optional provenance URL.")
    assets_p.add_argument("--license-file", default="", help="Optional local rights/license proof.")
    assets_p.add_argument(
        "--confirm-user-owned",
        action="store_true",
        help="Explicitly confirm that you own or control the supplied media rights.",
    )
    assets_p.add_argument("--projects-root", default=None)

    create_p = subparsers.add_parser(
        "create", help="Create one piece of content (flag-driven, non-interactive).", parents=[json_flag]
    )
    _add_create_arguments(create_p)

    resume_p = subparsers.add_parser(
        "resume", help="Resume an existing project (shortcut for create --resume).", parents=[json_flag]
    )
    _add_create_arguments(resume_p)

    run_stage_p = subparsers.add_parser(
        "run-stage", help="Run a single news_to_short stage on an existing project.", parents=[json_flag]
    )
    run_stage_p.add_argument("--project-id", required=True)
    run_stage_p.add_argument("--stage", required=True)
    run_stage_p.add_argument("--projects-root", default=None)
    run_stage_p.add_argument("--execute-voice", action="store_true")

    script_p = subparsers.add_parser(
        "script",
        help="Script engine: list providers, generate a script offline, validate an existing one.",
        parents=[json_flag],
    )
    script_p.add_argument("action", choices=["providers", "generate", "validate"])
    script_p.add_argument(
        "--source-kind",
        default="",
        choices=["", "topic", "research", "user_script", "narration_text"],
        help="What the input is. Empty = infer from which of --topic/--text is given.",
    )
    script_p.add_argument("--provider", default="", help="Script provider id (see `script providers`).")
    script_p.add_argument("--topic", default="")
    script_p.add_argument("--text", default="", help="Article text, ready script, or ready narration.")
    script_p.add_argument("--text-file", default="", help="Same as --text, read from a UTF-8 file.")
    script_p.add_argument("--title", default="")
    script_p.add_argument("--language", default="ru")
    script_p.add_argument("--target-duration", dest="target_duration_sec", type=int, default=55)
    script_p.add_argument("--include-cta", action="store_true", help="Add a call to action (never automatic).")
    script_p.add_argument("--cta-text", default="")
    script_p.add_argument("--out", default="", help="Write a pipeline-compatible script.json here.")
    script_p.add_argument("--script-file", dest="script_json_path", default="", help="script.json for 'validate'.")
    script_p.add_argument(
        "--visual-brief",
        dest="visual_brief_path",
        default="",
        help="The same brief JSON as `create --visual-brief`. Offline: writes nothing unless --out is given.",
    )

    visual_p = subparsers.add_parser(
        "visual-plan",
        help="Visual planning: what each scene should show. Builds and checks plans offline.",
        parents=[json_flag],
    )
    visual_p.add_argument("action", choices=["planners", "build", "validate", "intents"])
    visual_p.add_argument("--planner", default="", help="Planner id (see `visual-plan planners`).")
    visual_p.add_argument(
        "--script-file", dest="script_json_path", default="", help="script.json to plan from."
    )
    visual_p.add_argument(
        "--claims-file", dest="claims_json_path", default="", help="Optional research claims.json."
    )
    visual_p.add_argument(
        "--plan-file", dest="plan_json_path", default="", help="visual_plan.json for 'validate'/'intents'."
    )
    visual_p.add_argument("--language", default="")
    visual_p.add_argument("--out", default="", help="Write a pipeline-compatible visual_plan.json here.")

    subparsers.add_parser(
        "wizard", help="Interactive terminal wizard (same request/service as 'create').", parents=[json_flag]
    )
    return parser


def _add_create_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--format", dest="format_id", help="Format id, e.g. vertical_short.")
    parser.add_argument("--template", dest="template_id", help="Template id or legacy alias.")
    parser.add_argument("--channel", dest="channel_id", help="Channel id.")
    parser.add_argument("--language", default="ru")
    parser.add_argument("--title", default="")
    parser.add_argument("--topic", default="", help="Topic/idea (fullscreen_voiceover_v1).")
    parser.add_argument(
        "--target-duration",
        dest="target_duration_sec",
        type=int,
        default=50,
        help="Target duration in seconds for fullscreen_voiceover_v1 (default: 50).",
    )
    parser.add_argument("--text", default="", help="Card headline text (story_card_text_only_v1).")
    parser.add_argument("--comment", default="", help="Card bottom-comment text (story_card_text_only_v1).")
    parser.add_argument("--source-asset", dest="source_asset_path", default="", help="Local video file (story_card_text_only_v1).")
    parser.add_argument("--source-url", default="", help="Article URL (fullscreen_voiceover_v1).")
    parser.add_argument("--script-file", dest="script_path", default="")
    parser.add_argument(
        "--visual-brief",
        dest="visual_brief_path",
        default="",
        help=(
            "JSON with an explicit per-scene visual brief, keyed by scene number or scene_id: "
            "subject / action / place / exact_entities / must_include / must_avoid / shot_type / "
            "media_types / source_class / provider_queries / infographic. Never spoken - it only "
            "steers what is shown. Optional."
        ),
    )
    parser.add_argument("--pasted-script", default="", help="Full script text pasted directly (fullscreen_voiceover_v1).")
    parser.add_argument(
        "--input-mode",
        dest="content_input_mode",
        default="",
        choices=["", "topic", "article_url", "pasted_script", "script_file"],
        help="Which of --topic/--source-url/--pasted-script/--script-file is authoritative.",
    )
    parser.add_argument("--project-id", default="")
    parser.add_argument(
        "--voice-provider", default="disabled", help="disabled | elevenlabs | audio_file (see `voices providers`)."
    )
    parser.add_argument("--voice-profile", default="", help="Profile id, alias, or display name, e.g. \"Дом\".")
    parser.add_argument(
        "--voice-mode", default="", help="scene_audio | single_narration | manual_audio | disabled."
    )
    parser.add_argument("--audio-file", default="", help="Manual WAV file for --voice-provider audio_file.")
    parser.add_argument("--subtitles", dest="subtitle_style", default="disabled", help="See `subtitles list`.")
    parser.add_argument("--music", dest="music_mode", default="disabled", help="See `capabilities`.")
    parser.add_argument("--music-path", default="")
    parser.add_argument("--timing-mode", default="")
    parser.add_argument("--quality", default="default")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--prepare-only", action="store_true", help="Stop before any paid TTS call.")
    parser.add_argument("--approve-paid-generation", action="store_true", help="Explicitly allow paid ElevenLabs synthesis.")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument(
        "--force-stage",
        action="store_true",
        help="On --resume, re-run a news_to_short stage even if already marked completed "
        "(e.g. after a visual_plan/asset_search wiring fix). Never forces a paid TTS call by itself.",
    )
    parser.add_argument(
        "--completion-mode",
        choices=["strict", "draft_complete"],
        default="",
        help="strict (default) or opt-in autonomous draft completion.",
    )
    parser.add_argument(
        "--script-adaptation",
        choices=["none", "light"],
        default="",
        help="Asset-aware adaptation; empty keeps the project/default setting.",
    )
    parser.add_argument("--projects-root", default=None)


def _resolve_cli_paths(args: argparse.Namespace):
    existing = getattr(args, "_application_paths", None)
    if existing is not None:
        return existing
    from src.config_resolver import resolve_application_paths

    paths = resolve_application_paths(
        workspace_root=getattr(args, "workspace", None),
        paths_config=getattr(args, "paths_config", None),
        projects_root=getattr(args, "projects_root", None),
    )
    args.projects_root = str(paths.projects_root)
    args.project_fallback_roots = tuple(str(path) for path in paths.project_fallback_roots)
    args.channels_root = str(paths.channels_root)
    args._application_paths = paths
    return paths


def _request_from_args(args: argparse.Namespace) -> ContentCreationRequest:
    _resolve_cli_paths(args)
    voice_profile = args.voice_profile
    if voice_profile and args.channel_id:
        try:
            voice_profile = capabilities.resolve_voice_profile(args.channel_id, args.voice_profile)
        except Exception:
            pass  # let the service layer raise a clearer error with full context
    text: dict[str, str] = {}
    if getattr(args, "text", ""):
        text["top"] = args.text
    if getattr(args, "comment", ""):
        text["comment"] = args.comment
    return ContentCreationRequest(
        project_id=args.project_id,
        title=args.title,
        source_url=args.source_url,
        script_path=args.script_path,
        pasted_script=getattr(args, "pasted_script", ""),
        content_input_mode=getattr(args, "content_input_mode", ""),
        channel_id=args.channel_id,
        format_id=args.format_id or "",
        template_id=args.template_id or "",
        language=args.language,
        text=text,
        source_asset_path=args.source_asset_path,
        topic=args.topic,
        target_duration_sec=getattr(args, "target_duration_sec", 50),
        visual_briefs=_load_visual_briefs(getattr(args, "visual_brief_path", "")),
        completion_mode=getattr(args, "completion_mode", ""),
        script_adaptation=getattr(args, "script_adaptation", ""),
        voice=VoiceRequestConfig(
            provider=args.voice_provider,
            profile=voice_profile,
            mode=args.voice_mode or ("disabled" if args.voice_provider == "disabled" else "scene_audio"),
            audio_file=args.audio_file,
            approve_paid_generation=args.approve_paid_generation,
        ),
        subtitles=SubtitleRequestConfig(style=args.subtitle_style),
        music=MusicRequestConfig(mode=args.music_mode, path=args.music_path),
        timing=TimingRequestConfig(mode=args.timing_mode),
        render=RenderRequestConfig(quality=args.quality),
        execution=ExecutionFlags(
            dry_run=args.dry_run,
            prepare_only=args.prepare_only,
            resume=args.resume,
            force_stage=getattr(args, "force_stage", False),
            stage="",
            until_stage="",
        ),
        project_overrides={
            "projects_root": args.projects_root,
            "project_fallback_roots": list(getattr(args, "project_fallback_roots", ())),
            "channels_root": getattr(args, "channels_root", ""),
        },
    )


def _print_json(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2, default=str))


def _channels_explain(args: argparse.Namespace) -> int:
    """`channels show --channel X --explain`: which settings apply to a run on this
    channel and where each one came from.

    Read-only and free: the resolver opens configuration files and the catalog, and
    reports credentials only as настроен/не настроен - it never reads a key's value.
    Nothing here is wired into the pipeline; it explains what the current readers
    already do.
    """
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
            _print_json({"status": "failed", "error": str(exc), "reason": exc.reason})
        else:
            print(f"[explain] error: {exc}")
        return 1

    if args.json_output:
        _print_json(resolved.to_dict(include_trace=bool(args.trace)))
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
    """The template/format a run on this channel would use, for the explain commands."""
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
    """Which localizations to explain: the one asked for, or every one the channel
    declares (``channel.json:supported_languages``, then the known language list)."""
    if args.language:
        return [args.language]
    channel = next((c for c in capabilities.list_channels() if c["channel_id"] == args.channel), None)
    supported = list((channel or {}).get("supported_languages") or [])
    if supported:
        return supported
    from src.localization import known_language_codes

    return list(known_language_codes())


def _voices_explain(args: argparse.Namespace) -> int:
    """`voices explain --channel X [--language ru]`: the localization/voice
    configuration that would actually be used, and where each part comes from.

    Read-only and free. It resolves configuration, looks a profile up in voices.yaml
    and inspects an existing voice_manifest.json - it never opens the network, never
    calls a TTS provider, never downloads, never renders and never writes to the
    project. A credential is reported only as настроен/не настроен; its value is not
    read into the output at any point.
    """
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
                _print_json({"status": "failed", "error": str(exc), "reason": exc.reason})
            else:
                print(f"[localization] error: {exc}")
            return 1

    issues = validate_localization_set(resolved)
    if args.json_output:
        _print_json(
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
    """Пути и данные одного проекта для subtitle-команд. Только чтение.

    Возвращает ``(project_root, localization_id, channel_id, script, voice_manifest)``.
    Работает через тот же read-only ``src.projects``, что и ``project status``,
    поэтому понимает оба хранилища в ``projects/``.
    """
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
    """Собрать cues в памяти. Ни записи, ни рендера, ни сети, ни TTS."""
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


def _subtitles_explain(args: argparse.Namespace) -> int:
    """`subtitles explain --project-id X`: какие субтитры получатся и почему.

    Строит cues в памяти, показывает источник тайминга, раскладку «сцена → cues»,
    путь будущего артефакта и решение resume. Не пишет в проект, не рендерит, не
    вызывает TTS, не ходит в сеть.
    """
    from src.subtitles import artifact_paths, explain_scene_mapping, manifest_path, plan_resume, read_manifest

    root, localization_id, result = _subtitle_result_for_project(args)
    existing = read_manifest(manifest_path(root, localization_id))
    decision = plan_resume(existing, result, project_root=root, localization_id=localization_id)
    paths = {name: str(path) for name, path in artifact_paths(root, localization_id, result.formats).items()}
    mapping = explain_scene_mapping(result)

    if args.json_output:
        _print_json(
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


def _subtitles_validate(args: argparse.Namespace) -> int:
    """`subtitles validate --project-id X`: проверить артефакт, который уже на диске.

    Читает манифест и, если его нет, сам SRT. Старый артефакт без метаданных Q3
    тоже проверяется - по времени, порядку и пересечениям. Только чтение.
    """
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
    # scene_texts не передаётся: проверка полноты покрытия имеет смысл только для
    # артефакта, созданного из этого же сценария, а у старого файла связи со
    # сценарием нет вообще - объявить его «неполным» было бы неправдой.
    result = validate_cues(
        cues,
        policy=policy,
        language=str(manifest.get("subtitle_language") or manifest.get("language") or ""),
        scene_order=scene_order if any(cue.scene_id for cue in cues) else (),
        narration_duration_sec=float(manifest.get("narration_duration_sec") or 0.0),
    )
    if args.json_output:
        _print_json(
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


def _print_rights_lines(evidence: dict[str, Any], *, prefix: str = "") -> None:
    """Four-line rights summary for a finished run - the detail lives in
    `project rights-report`, which this deliberately does not duplicate."""
    if not evidence or not evidence.get("evidence_manifest_path"):
        return
    status = str(evidence.get("rights_status") or "unknown")
    print(f"{prefix}rights_status={_RIGHTS_STATUS_LABELS.get(status, status)}")
    print(f"{prefix}evidence_path={evidence['evidence_manifest_path']}")
    print(f"{prefix}source_type={evidence.get('source_type') or '-'}")
    print(f"{prefix}review_required={'да' if evidence.get('review_required') else 'нет'}")


def _run_create(args: argparse.Namespace) -> int:
    request = _request_from_args(args)
    if getattr(args, "debug", False):
        result = create_content(request)
    else:
        try:
            result = create_content(request)
        except ContentCreationError as exc:
            if args.json_output:
                _print_json({"status": "failed", "error": str(exc), "reason": exc.reason, "retryable": exc.retryable})
            else:
                print(f"[create] error: {exc} (reason={exc.reason})")
            return 1
    if args.json_output:
        _print_json(result.to_dict())
        return 0 if result.status not in {"failed"} else 1
    print(f"[create] status={result.status}")
    print(f"[create] project_id={result.project_id}")
    print(f"[create] project_root={Path(result.project_root).resolve()}")
    for stage in result.stages:
        print(f"[create] stage {stage.get('stage')}: {stage.get('status')}")
    final_video = result.output_paths.get("final_video")
    if final_video:
        report = describe_output_file(final_video, project_root=result.project_root)
        print(f"[create] output_path={report['absolute_path']}")
        print(f"[create] output_project_relative={report['project_relative_path']}")
        print(f"[create] output_size_bytes={report['size_bytes']}")
        print(f"[create] output_duration_sec={report['duration_sec']}")
        print(f"[create] output_resolution={report['resolution']}")
        print(f"[create] output_audio_present={report['audio_present']}")
    _print_rights_lines(result.evidence, prefix="[create] ")
    for warning in result.warnings:
        print(f"[create] warning: {warning}")
    for error in result.errors:
        print(f"[create] error: {error}")
    if result.rerun_commands:
        print(f"[create] rerun: {result.rerun_commands[0]}")
    return 0 if result.status != "failed" else 1


def _run_wizard(args: argparse.Namespace) -> int:
    # The wizard now owns its own creation/retry loop (interactive network-error
    # recovery needs to happen live, not after the fact) - it returns the final
    # ContentCreationResult itself, already printed via wizard.print_result().
    from src.content_creation.wizard import run_wizard

    result = run_wizard(
        no_icons=getattr(args, "no_icons", False),
        projects_root=args.projects_root,
        project_fallback_roots=args.project_fallback_roots,
        channels_root=args.channels_root,
    )
    if result is None:
        return 0
    return 0 if result.status != "failed" else 1


def run_content_creation_cli(args: argparse.Namespace) -> int:
    _resolve_cli_paths(args)
    command = args.command
    if command == "capabilities":
        report = capabilities.build_capabilities_report()
        if args.json_output:
            _print_json(report)
        else:
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

    if command == "script":
        return _run_script_command(args)

    if command == "visual-plan":
        return _run_visual_plan_command(args)

    if command == "formats":
        catalog = get_default_catalog()
        if args.action == "show":
            if not args.format:
                raise SystemExit("formats show requires --format.")
            data = catalog.formats.get(args.format).to_dict()
        else:
            data = catalog.formats.serialize()
        _print_json(data) if args.json_output else _print_plain(data)
        return 0

    if command == "templates":
        catalog = get_default_catalog()
        try:
            if args.action == "show":
                if not args.template:
                    raise SystemExit("templates show requires --template.")
                data = catalog.templates.get(args.template).to_dict()
            elif args.format:
                data = [t.to_dict() for t in catalog.templates.filter_by_format(args.format)]
            else:
                data = catalog.templates.serialize()
        except CatalogValidationError as exc:
            raise SystemExit(str(exc)) from exc
        _print_json(data) if args.json_output else _print_plain(data)
        return 0

    if command == "channels":
        if args.action == "show":
            if not args.channel:
                raise SystemExit("channels show requires --channel.")
            if args.explain:
                return _channels_explain(args)
            data = next((c for c in capabilities.list_channels() if c["channel_id"] == args.channel), None)
            if data is None:
                raise SystemExit(f"Unknown channel_id: {args.channel!r}.")
        else:
            data = capabilities.list_channels()
        _print_json(data) if args.json_output else _print_plain(data)
        return 0

    if command == "voices":
        if args.action == "explain":
            if not args.channel:
                raise SystemExit("voices explain requires --channel.")
            return _voices_explain(args)
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
        _print_json(data) if args.json_output else _print_plain(data)
        return 0

    if command == "subtitles":
        if args.action in {"explain", "validate"}:
            if not args.project_id:
                raise SystemExit(f"subtitles {args.action} requires --project-id.")
            return _subtitles_explain(args) if args.action == "explain" else _subtitles_validate(args)
        styles = capabilities.list_subtitle_styles()
        if args.action == "show":
            if not args.style:
                raise SystemExit("subtitles show requires --style.")
            data = next((s for s in styles if s["style_id"] == args.style), None)
            if data is None:
                raise SystemExit(f"Unknown subtitle style: {args.style!r}.")
        else:
            data = styles
        _print_json(data) if args.json_output else _print_plain(data)
        return 0

    if command == "project":
        return _run_project(args)

    if command == "assets":
        return _run_assets(args)

    if command == "create" or command == "resume":
        if command == "resume":
            args.resume = True
        return _run_create(args)

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

    if command == "wizard":
        return _run_wizard(args)

    raise SystemExit(f"Unknown command: {command!r}")


def _run_assets(args: argparse.Namespace) -> int:
    """Replace one visual slot without re-running research or asset search."""
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
            _print_json(
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
        _print_json(result)
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


def _run_project(args: argparse.Namespace) -> int:
    from src.project_foundation.evidence import EvidenceBundle
    from src.project_foundation.policies import ChannelOutputPolicy, validate as validate_policy
    from src.project_foundation.projects import ProjectFactory
    from src.project_foundation.channels import ChannelRegistry
    from src.projects import PROJECT_KIND_PROJECT_MANIFEST, ProjectNotFoundError, ProjectRepository

    from src.project_foundation.models import ProjectFoundationError

    # list/status/rights-report go through the read-only src.projects layer, which
    # understands both storage systems living in projects/ (job.json and project.json).
    # validate still needs a real ProjectManifest + ChannelProfile, so it stays on
    # ProjectFactory and says so plainly for a news job.
    repository = ProjectRepository(
        args.projects_root, fallback_roots=args.project_fallback_roots
    )

    if args.action == "list":
        views = [view.to_dict() for view in repository.list(include_unknown=True)]
        if getattr(args, "json_output", False):
            _print_json(views)
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
            _print_json(view.to_dict())
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
        return _run_rights_report(args, repository)

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
        _print_json(result.to_dict()) if getattr(args, "json_output", False) else _print_plain(result.to_dict())
        return 0 if result.allowed else 1
    raise SystemExit(f"Unknown project action: {args.action!r}")


_RIGHTS_STATUS_LABELS = {
    "verified": "подтверждено",
    "review_required": "требует проверки",
    "blocked": "заблокировано",
    "unknown": "нет данных",
}


def _run_rights_report(args: argparse.Namespace, repository) -> int:
    """Show every rights-bearing material of one project, whichever system created it.

    Exit code is 0 for a report that contains only unknown/review_required items -
    those need a human, but nothing is provably wrong - and 1 when something is
    actually blocking: a forbidden asset or a scene with no material at all.
    """
    from src.project_foundation.evidence import EvidenceBundle
    from src.projects import PROJECT_KIND_PROJECT_MANIFEST, ProjectNotFoundError, build_rights_report

    try:
        view = repository.get(args.project_id)
    except ProjectNotFoundError as exc:
        print(f"[rights] {exc}")
        return 1

    report = build_rights_report(
        project_id=view.project_id, project_root=view.project_root, project_kind=view.kind
    )

    # Backward compatibility: everything the pre-Stage-C2 command printed for a
    # project.json project came from EvidenceBundle.rights_report(). It is still
    # produced and carried in the output so no previously available field is lost.
    if view.kind == PROJECT_KIND_PROJECT_MANIFEST:
        try:
            report.evidence_bundle_report = EvidenceBundle.load(view.project_root, view.project_id).rights_report()
        except Exception as exc:  # tolerant: a broken bundle must not kill the report
            report.warnings.append(f"EvidenceBundle не прочитан: {exc}")

    if getattr(args, "json_output", False):
        _print_json(report.to_dict())
        return 1 if report.has_blocking_problems else 0

    summary = report.summary
    print(f"Проект: {report.project_id}")
    print(f"Тип: {report.project_kind}")
    print(f"Папка: {Path(report.project_root).resolve()}")
    print(f"Итоговый статус: {_RIGHTS_STATUS_LABELS.get(report.overall_status, report.overall_status)}")
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
            label = _RIGHTS_STATUS_LABELS.get(item.verification_status, item.verification_status)
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


def _load_visual_briefs(path: str) -> dict[str, dict]:
    """Read the one visual brief file, or nothing. Validated before it is trusted."""
    if not str(path or "").strip():
        return {}
    from src.content_creation import input_validation

    result = input_validation.validate_visual_brief_file(path)
    if not result.valid:
        raise SystemExit(f"--visual-brief: {result.message}")
    return input_validation.load_visual_briefs(path)


def _print_plain(data: Any) -> None:
    if isinstance(data, list):
        for item in data:
            print(item)
    else:
        print(data)


def _run_script_command(args: argparse.Namespace) -> int:
    """`script` subcommand: the offline way to see and check a script.

    Runs the real pipeline path (research engine -> script engine -> script.json),
    but writes nothing except an explicit --out file. No network, no TTS, no
    downloads, no render, no paid API - by construction, not by flag.
    """
    from src.content.script_engine import from_legacy_script, list_capabilities, validate_script
    from src.news.models import INPUT_MODE_TEXT, INPUT_MODE_TOPIC, NewsJob
    from src.news.research_engine import build_research
    from src.news.script_generator import generate_for_job

    if args.action == "providers":
        data = [item.to_dict() for item in list_capabilities()]
        if args.json_output:
            _print_json(data)
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
            _print_json(payload)
        else:
            _print_validation(validation, scene_count=len(result.scenes))
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
        visual_briefs=_load_visual_briefs(getattr(args, "visual_brief_path", "")),
    )
    research = build_research(job, {"title": args.topic or args.title, "text": text or args.topic})
    outcome = generate_for_job(job, research)
    script = outcome.to_legacy_script(target_duration_sec=job.target_duration_sec)

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(script, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.json_output:
        _print_json({**outcome.to_dict(), "written_to": args.out, "script_json": script})
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
    _print_validation(outcome.validation, scene_count=len(result.scenes))
    if args.out:
        print(f"[script] script.json записан: {Path(args.out).resolve()}")
    return 0 if outcome.validation.valid else 1


def _run_visual_plan_command(args: argparse.Namespace) -> int:
    """`visual-plan` subcommand: see and check what each scene will show.

    Reads a script.json, plans from it, and writes nothing except an explicit --out
    file. No network, no downloads, no Vision, no render, no asset selection - by
    construction, not by flag. Choosing the actual file stays a later stage.
    """
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
            _print_json(data)
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
                _print_json(payload)
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
            _print_json(payload)
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
        _print_json({**planning.to_dict(), "written_to": args.out, "visual_plan_json": stored})
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


def _print_validation(validation, *, scene_count: int) -> None:
    label = {"passed": "проверка пройдена", "needs_review": "нужна проверка", "failed": "не проходит"}
    print(f"[script] {label.get(validation.status, validation.status)} (сцен: {scene_count})")
    for issue in validation.issues:
        mark = "ошибка " if issue.severity == "error" else "внимание"
        where = f" [{issue.scene_id}]" if issue.scene_id else ""
        print(f"  {mark}{where} {issue.code}: {issue.message}")


def main(argv: list[str] | None = None) -> int:
    configure_console_encoding()
    parser = build_parser()
    args = parser.parse_args(argv)
    return run_content_creation_cli(args)


if __name__ == "__main__":
    sys.exit(main())
