from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from src.ai_youtube.cli import presentation


COMMANDS = frozenset({"script", "visual-plan", "run-stage"})


def handle_authoring(args: argparse.Namespace, *, print_json_fn: Any) -> int:
    if args.command == "script":
        return run_script_command(args, print_json_fn=print_json_fn)
    if args.command == "visual-plan":
        return run_visual_plan_command(args, print_json_fn=print_json_fn)
    if args.command == "run-stage":
        from src.news.pipeline import run_news_to_short_job

        projects_root = args._application_paths.find_project_root(
            args.project_id
        ).parent
        result = run_news_to_short_job(
            projects_root=projects_root,
            job_id=args.project_id,
            stage=args.stage,
            execute_voice=args.execute_voice,
        )
        print(
            f"[run-stage] status={result.status} "
            f"completed_stages={result.completed_stages}"
        )
        return 0
    raise SystemExit(f"Unknown authoring command: {args.command!r}")


def run_script_command(
    args: argparse.Namespace,
    *,
    print_json_fn: Any,
) -> int:
    from src.content.script_engine import (
        ScriptProviderInputError,
        from_legacy_script,
        list_capabilities,
        validate_script,
    )
    from src.content_creation.request_builder import load_visual_briefs
    from src.news.models import INPUT_MODE_TEXT, INPUT_MODE_TOPIC, NewsJob
    from src.news.research_engine import build_research
    from src.news.script_generator import generate_for_job

    if args.action == "providers":
        data = [item.to_dict() for item in list_capabilities()]
        if args.json_output:
            print_json_fn(data)
        else:
            presentation.print_script_capabilities(data)
        return 0

    if args.action == "validate":
        if not args.script_json_path:
            raise SystemExit(
                "script validate requires --script-file <path to script.json>."
            )
        path = Path(args.script_json_path)
        if not path.is_file():
            raise SystemExit(f"Файл не найден: {path}")
        result = from_legacy_script(
            json.loads(path.read_text(encoding="utf-8"))
        )
        validation = validate_script(
            result,
            expected_language=result.language,
        )
        payload = {
            "script_file": str(path),
            "scene_count": len(result.scenes),
            **validation.to_dict(),
        }
        if args.json_output:
            print_json_fn(payload)
        else:
            presentation.print_script_validation(
                validation,
                scene_count=len(result.scenes),
            )
        return 0 if validation.valid else 1

    text = args.text
    if args.text_file:
        text = Path(args.text_file).read_text(encoding="utf-8")
    if not text and not args.topic:
        raise SystemExit(
            "script generate requires --topic, --text or --text-file."
        )

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
        visual_briefs=load_visual_briefs(
            getattr(args, "visual_brief_path", "")
        ),
    )
    research = build_research(
        job,
        {
            "title": args.topic or args.title,
            "text": text or args.topic,
        },
    )
    try:
        outcome = generate_for_job(job, research)
    except ScriptProviderInputError as exc:
        payload = {
            "status": "blocked",
            "reason": exc.code,
            "retryable": exc.retryable,
            "error": str(exc),
        }
        if args.json_output:
            print_json_fn(payload)
        else:
            print(f"Script generation blocked: {exc}")
        return 1
    script = outcome.to_legacy_script(
        target_duration_sec=job.target_duration_sec
    )

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(script, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    if args.json_output:
        print_json_fn(
            {
                **outcome.to_dict(),
                "written_to": args.out,
                "script_json": script,
            }
        )
        return 0 if outcome.validation.valid else 1

    presentation.print_script_outcome(
        outcome,
        job,
        written_to=args.out,
    )
    return 0 if outcome.validation.valid else 1


def run_visual_plan_command(
    args: argparse.Namespace,
    *,
    print_json_fn: Any,
) -> int:
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
            presentation.print_visual_planner_capabilities(data)
        return 0

    if args.action in {"validate", "intents"}:
        if not args.plan_json_path:
            raise SystemExit(
                f"visual-plan {args.action} requires "
                "--plan-file <path to visual_plan.json>."
            )
        path = Path(args.plan_json_path)
        if not path.is_file():
            raise SystemExit(f"Файл не найден: {path}")
        plan = from_legacy_visual_plan(
            json.loads(path.read_text(encoding="utf-8"))
        )

        if args.action == "intents":
            payload = [
                {
                    "scene_id": scene.scene_id,
                    "intents": [
                        intent.to_dict() for intent in scene.intents
                    ],
                }
                for scene in plan.scenes
            ]
            if args.json_output:
                print_json_fn(payload)
            else:
                presentation.print_visual_plan_intents(
                    plan,
                    intent_to_query_fn=intent_to_query,
                )
            return 0

        script = None
        if (
            args.script_json_path
            and Path(args.script_json_path).is_file()
        ):
            script = from_legacy_script(
                json.loads(
                    Path(args.script_json_path).read_text(encoding="utf-8")
                )
            )
        validation = validate_visual_plan(plan, script=script)
        payload = {
            "plan_file": str(path),
            "scene_count": len(plan.scenes),
            **validation.to_dict(),
        }
        if args.json_output:
            print_json_fn(payload)
        else:
            presentation.print_plan_validation(
                validation,
                scene_count=len(plan.scenes),
            )
        return 0 if validation.valid else 1

    if not args.script_json_path:
        raise SystemExit(
            "visual-plan build requires --script-file <path to script.json>."
        )
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
    stored = to_legacy_visual_plan(
        planning.result,
        language=language,
        script=script_data,
    )

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(stored, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    if args.json_output:
        print_json_fn(
            {
                **planning.to_dict(),
                "written_to": args.out,
                "visual_plan_json": stored,
            }
        )
        return 0 if planning.validation.valid else 1

    presentation.print_visual_plan_outcome(
        planning,
        intent_to_query_fn=intent_to_query,
        written_to=args.out,
    )
    return 0 if planning.validation.valid else 1


__all__ = [
    "COMMANDS",
    "handle_authoring",
    "run_script_command",
    "run_visual_plan_command",
]
