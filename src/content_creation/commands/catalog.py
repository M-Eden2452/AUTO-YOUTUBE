from __future__ import annotations

import argparse


def register_commands(
    subparsers: argparse._SubParsersAction,
    *,
    common: argparse.ArgumentParser,
) -> None:
    applications = subparsers.add_parser(
        "applications",
        help="List ready applications or inspect any registered application.",
        parents=[common],
    )
    applications.add_argument(
        "action",
        choices=["list", "show"],
        nargs="?",
        default="list",
    )
    applications.add_argument(
        "--application",
        help="application_id for 'show'.",
    )
    applications.add_argument(
        "--all",
        action="store_true",
        help="Include planned/disabled applications in 'list'.",
    )

    subparsers.add_parser(
        "capabilities",
        help="Show what formats/templates/voices/subtitles/music are usable today.",
        parents=[common],
    )

    formats = subparsers.add_parser(
        "formats",
        help="List/inspect formats from the Production Catalog.",
        parents=[common],
    )
    formats.add_argument("action", choices=["list", "show"], nargs="?", default="list")
    formats.add_argument("--format", help="format_id for 'show'.")

    templates = subparsers.add_parser(
        "templates",
        help="List/inspect templates from the Production Catalog.",
        parents=[common],
    )
    templates.add_argument("action", choices=["list", "show"], nargs="?", default="list")
    templates.add_argument("--template", help="template_id or legacy alias for 'show'.")
    templates.add_argument("--format", help="Filter list by format_id.")

    channels = subparsers.add_parser(
        "channels",
        help="List/inspect channels.",
        parents=[common],
    )
    channels.add_argument("action", choices=["list", "show"], nargs="?", default="list")
    channels.add_argument("--channel", help="channel_id for 'show'.")
    channels.add_argument(
        "--explain",
        action="store_true",
        help="For 'show': print «параметр → значение → откуда взято» via the ConfigResolver. Read-only.",
    )
    channels.add_argument(
        "--template",
        help="With --explain: template_id whose policy layer to apply.",
    )
    channels.add_argument(
        "--format",
        dest="format_id",
        help="With --explain: format_id whose policy layer to apply.",
    )
    channels.add_argument(
        "--language",
        help="With --explain: language whose localization layer to apply.",
    )
    channels.add_argument(
        "--project-id",
        help="With --explain: project whose manifest layer to apply.",
    )
    channels.add_argument(
        "--trace",
        action="store_true",
        help="With --explain: also print every layer that was considered.",
    )

    voices = subparsers.add_parser(
        "voices",
        help="List voice providers/profiles, or explain a localization's voice.",
        parents=[common],
    )
    voices.add_argument("action", choices=["providers", "profiles", "show", "explain"])
    voices.add_argument("--channel", help="channel_id for 'profiles'/'show'/'explain'.")
    voices.add_argument(
        "--voice-profile",
        help='Profile id, alias, or display name (e.g. "Дом") for \'show\'.',
    )
    voices.add_argument(
        "--language",
        help="With 'explain': localization to explain (default: every one).",
    )
    voices.add_argument(
        "--template",
        help="With 'explain': template_id whose policy layer to apply.",
    )
    voices.add_argument(
        "--format",
        dest="format_id",
        help="With 'explain': format_id whose policy layer to apply.",
    )
    voices.add_argument(
        "--project-id",
        help="With 'explain': project whose manifest and narration to inspect.",
    )
    voices.add_argument("--projects-root", default=None)
    voices.add_argument(
        "--voice-provider",
        help="With 'explain': provider as an explicit runtime override.",
    )
    voices.add_argument(
        "--trace",
        action="store_true",
        help="With 'explain': also print every configuration layer considered.",
    )

    subtitles = subparsers.add_parser(
        "subtitles",
        help="List subtitle styles, or explain/validate a project's subtitles (read-only).",
        parents=[common],
    )
    subtitles.add_argument(
        "action",
        choices=["list", "show", "explain", "validate"],
        nargs="?",
        default="list",
    )
    subtitles.add_argument("--style", help="style_id for 'show'.")
    subtitles.add_argument("--project-id", help="Required for 'explain'/'validate'.")
    subtitles.add_argument(
        "--language",
        help="Localization id (default: the project's own).",
    )
    subtitles.add_argument("--projects-root", default=None)
    subtitles.add_argument(
        "--cues",
        action="store_true",
        help="With 'explain': print every cue, not just the per-scene summary.",
    )
