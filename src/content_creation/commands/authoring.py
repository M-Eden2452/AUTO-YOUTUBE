from __future__ import annotations

import argparse


def register_commands(
    subparsers: argparse._SubParsersAction,
    *,
    common: argparse.ArgumentParser,
) -> None:
    script = subparsers.add_parser(
        "script",
        help="Script engine: list providers, generate a script offline, validate an existing one.",
        parents=[common],
    )
    script.add_argument("action", choices=["providers", "generate", "validate"])
    script.add_argument(
        "--source-kind",
        default="",
        choices=["", "topic", "research", "user_script", "narration_text"],
        help="What the input is. Empty = infer from which of --topic/--text is given.",
    )
    script.add_argument(
        "--provider",
        default="",
        help="Script provider id (see `script providers`).",
    )
    script.add_argument("--topic", default="")
    script.add_argument(
        "--text",
        default="",
        help="Article text, ready script, or ready narration.",
    )
    script.add_argument(
        "--text-file",
        default="",
        help="Same as --text, read from a UTF-8 file.",
    )
    script.add_argument("--title", default="")
    script.add_argument("--language", default="ru")
    script.add_argument(
        "--target-duration",
        dest="target_duration_sec",
        type=int,
        default=55,
    )
    script.add_argument(
        "--include-cta",
        action="store_true",
        help="Add a call to action (never automatic).",
    )
    script.add_argument("--cta-text", default="")
    script.add_argument(
        "--out",
        default="",
        help="Write a pipeline-compatible script.json here.",
    )
    script.add_argument(
        "--script-file",
        dest="script_json_path",
        default="",
        help="script.json for 'validate'.",
    )
    script.add_argument(
        "--visual-brief",
        dest="visual_brief_path",
        default="",
        help=(
            "The same brief JSON as `create --visual-brief`. "
            "Offline: writes nothing unless --out is given."
        ),
    )

    visual_plan = subparsers.add_parser(
        "visual-plan",
        help="Visual planning: what each scene should show. Builds and checks plans offline.",
        parents=[common],
    )
    visual_plan.add_argument(
        "action",
        choices=["planners", "build", "validate", "intents"],
    )
    visual_plan.add_argument(
        "--planner",
        default="",
        help="Planner id (see `visual-plan planners`).",
    )
    visual_plan.add_argument(
        "--script-file",
        dest="script_json_path",
        default="",
        help="script.json to plan from.",
    )
    visual_plan.add_argument(
        "--claims-file",
        dest="claims_json_path",
        default="",
        help="Optional research claims.json.",
    )
    visual_plan.add_argument(
        "--plan-file",
        dest="plan_json_path",
        default="",
        help="visual_plan.json for 'validate'/'intents'.",
    )
    visual_plan.add_argument("--language", default="")
    visual_plan.add_argument(
        "--out",
        default="",
        help="Write a pipeline-compatible visual_plan.json here.",
    )
