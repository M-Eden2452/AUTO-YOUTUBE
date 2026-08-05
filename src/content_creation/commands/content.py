from __future__ import annotations

import argparse

from src.runtime_network import NETWORK_ACTIONS, NETWORK_ACTION_DESCRIPTIONS


def register_commands(
    subparsers: argparse._SubParsersAction,
    *,
    common: argparse.ArgumentParser,
) -> None:
    create = subparsers.add_parser(
        "create",
        help="Create one piece of content (flag-driven, non-interactive).",
        parents=[common],
    )
    add_create_arguments(create)

    resume = subparsers.add_parser(
        "resume",
        help="Resume an existing project (shortcut for create --resume).",
        parents=[common],
    )
    add_create_arguments(resume)

    run_stage = subparsers.add_parser(
        "run-stage",
        help="Run a single news_to_short stage on an existing project.",
        parents=[common],
    )
    run_stage.add_argument("--project-id", required=True)
    run_stage.add_argument("--stage", required=True)
    run_stage.add_argument("--projects-root", default=None)
    run_stage.add_argument("--execute-voice", action="store_true")

    subparsers.add_parser(
        "wizard",
        help="Interactive terminal wizard (same request/service as 'create').",
        parents=[common],
    )


def add_create_arguments(parser: argparse.ArgumentParser) -> None:
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
    parser.add_argument(
        "--text",
        default="",
        help="Card headline text (story_card_text_only_v1).",
    )
    parser.add_argument(
        "--comment",
        default="",
        help="Card bottom-comment text (story_card_text_only_v1).",
    )
    parser.add_argument(
        "--source-asset",
        dest="source_asset_path",
        default="",
        help="Local video file (story_card_text_only_v1).",
    )
    parser.add_argument(
        "--source-url",
        default="",
        help="Article URL (fullscreen_voiceover_v1).",
    )
    parser.add_argument(
        "--source-text-file",
        "--script-file",
        dest="script_path",
        default=None,
        help=(
            "UTF-8 .txt/.md source material for fullscreen_voiceover_v1 "
            "(--script-file is a compatibility alias)."
        ),
    )
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
    parser.add_argument(
        "--source-text",
        "--pasted-script",
        dest="pasted_script",
        default=None,
        help=(
            "Prepared source material pasted directly for fullscreen_voiceover_v1 "
            "(--pasted-script is a compatibility alias)."
        ),
    )
    parser.add_argument(
        "--input-mode",
        dest="content_input_mode",
        default="",
        choices=["", "topic", "article_url", "pasted_script", "script_file"],
        help=(
            "Which of --topic/--source-url/--source-text/--source-text-file is "
            "authoritative. Compatibility aliases: --pasted-script/--script-file."
        ),
    )
    parser.add_argument("--project-id", default="")
    parser.add_argument(
        "--voice-provider",
        default="disabled",
        help="disabled | elevenlabs | audio_file (see `voices providers`).",
    )
    parser.add_argument(
        "--voice-profile",
        default="",
        help='Profile id, alias, or display name, e.g. "Дом".',
    )
    parser.add_argument(
        "--voice-mode",
        default="",
        help="scene_audio | single_narration | manual_audio | disabled.",
    )
    parser.add_argument(
        "--audio-file",
        default="",
        help="Manual WAV file for --voice-provider audio_file.",
    )
    parser.add_argument(
        "--subtitles",
        dest="subtitle_style",
        default="disabled",
        help="See `subtitles list`.",
    )
    parser.add_argument(
        "--music",
        dest="music_mode",
        default="disabled",
        help="See `capabilities`.",
    )
    parser.add_argument("--music-path", default="")
    parser.add_argument("--timing-mode", default="")
    parser.add_argument("--quality", default="default")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--prepare-only", action="store_true", help="Stop before any paid TTS call.")
    parser.add_argument(
        "--approve-paid-generation",
        action="store_true",
        help="Explicitly allow paid ElevenLabs synthesis.",
    )
    parser.add_argument(
        "--allow-network",
        dest="allow_network",
        action="append",
        default=None,
        choices=list(NETWORK_ACTIONS),
        metavar="ACTION",
        help=(
            "Explicitly approve ONE class of runtime network access; repeat the flag "
            "per class. Nothing is approved by default - a configured API key, a "
            "default-on provider and --approve-paid-generation are not approvals. "
            + " ".join(
                f"{action}: {NETWORK_ACTION_DESCRIPTIONS[action]}"
                for action in NETWORK_ACTIONS
            )
        ),
    )
    parser.add_argument("--resume", action="store_true")
    parser.add_argument(
        "--force-stage",
        action="store_true",
        help=(
            "On --resume, re-run a news_to_short stage even if already marked completed "
            "(e.g. after a visual_plan/asset_search wiring fix). Never forces a paid TTS call by itself."
        ),
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
