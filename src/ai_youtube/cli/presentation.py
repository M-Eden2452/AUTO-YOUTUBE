from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def print_plain(data: Any) -> None:
    if isinstance(data, list):
        for item in data:
            print(item)
    else:
        print(data)


def print_capabilities(report: dict[str, Any]) -> None:
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
        print(
            f"[capabilities] voice_provider={provider['provider_id']} "
            f"paid={provider['paid']} configured={provider['configured']}"
        )
    for style in report["subtitle_styles"]:
        print(
            f"[capabilities] subtitle_style={style['style_id']} "
            f"status={style['status']}"
        )
    for option in report["music_options"]:
        print(
            f"[capabilities] music_option={option['mode_id']} "
            f"status={option['status']}"
        )
    for channel in report["channels"]:
        print(
            f"[capabilities] channel={channel['channel_id']} "
            f"type={channel['channel_profile_type']}"
        )


def print_config_explanation(
    args: Any,
    resolved: Any,
    *,
    template_id: str,
    format_id: str,
) -> None:
    print(
        f"[explain] channel={args.channel} template={template_id or '-'} "
        f"format={format_id or '-'} language={args.language or '-'}"
    )
    for row in resolved.explain_rows():
        note = f"  ({', '.join(row['warnings'])})" if row["warnings"] else ""
        value = row["value"] if len(row["value"]) <= 26 else row["value"][:23] + "..."
        print(
            f"  {row['key']:<32} {value:<26} ← "
            f"{row['resolved_from']:<22} {row['origin']}{note}"
        )
    if args.trace:
        for layer in resolved.layers:
            state = layer.note or f"{len(layer.values)} настроек"
            print(f"  [layer {layer.priority:>2}] {layer.source:<22} {state}")
    for warning in resolved.warnings:
        print(f"  [!] {warning}")


def print_localizations(args: Any, resolved: list[Any], issues: list[Any]) -> None:
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
            print(
                f"    {row['key']:<24} {value:<26} ← "
                f"{source:<22} {row['origin']}{note}"
            )
        if item.existing_narration_path:
            reuse = (
                "будет переиспользована"
                if item.reuse_existing_narration
                else "несовместима, не используется"
            )
            print(f"    готовая озвучка          {item.existing_narration_path} ({reuse})")
        tts_line = (
            "да"
            if item.tts_allowed
            else f"нет — {item.tts_blocked_reason or 'причина не указана'}"
        )
        print(f"    TTS будет вызван         {tts_line}")
        if item.fallback_applied:
            print(f"    fallback                 {item.fallback_reason}")
        if args.trace and item.config is not None:
            for layer in item.config.layers:
                state = layer.note or f"{len(layer.values)} настроек"
                print(f"    [layer {layer.priority:>2}] {layer.source:<22} {state}")
    for issue in issues:
        print(f"  [{issue.severity}] {issue.localization_id or '-'}: {issue.message}")


def print_subtitle_explanation(
    args: Any,
    *,
    localization_id: str,
    result: Any,
    decision: Any,
    paths: dict[str, str],
    mapping: list[dict[str, Any]],
) -> None:
    print(
        f"[subtitles] локализация={localization_id} "
        f"язык_субтитров={result.language or '-'}"
    )
    print(
        f"[subtitles] источник тайминга={result.timing_source} "
        f"(границы сцен: {result.scene_timeline_source})"
    )
    print(
        f"[subtitles] озвучка={result.narration_duration_sec:.3f} с; "
        f"cues={len(result.cues)}; сцен={result.scene_count}"
    )
    print(
        f"[subtitles] стиль={result.style.source} "
        f"{result.style.origin or '(значения по умолчанию)'}"
    )
    for name, path in paths.items():
        print(f"[subtitles] {name}: {path}")
    print(
        f"[subtitles] resume: {'да' if decision.reuse else 'нет'} — "
        f"{decision.message}"
    )
    for row in mapping:
        print(
            f"    {row['scene_id']:<14} cues={row['cue_count']:<3} "
            f"[{row['start_sec']:7.3f} → {row['end_sec']:7.3f}] "
            f"{row['timing_source']}"
        )
        if args.cues:
            for cue in row["cues"]:
                text = cue["text"].replace("\n", " ⏎ ")
                print(
                    f"        {cue['start_sec']:7.3f}-{cue['end_sec']:7.3f}  "
                    f"{text}"
                )
    for issue in result.validation.issues:
        print(f"  [{issue.severity}] {issue.code}: {issue.message}")


def print_subtitle_validation(
    *,
    source: str,
    manifest: dict[str, Any],
    cues: list[Any],
    result: Any,
) -> None:
    print(f"[subtitles] артефакт={source}")
    print(
        f"[subtitles] схема="
        f"{manifest.get('schema_version') or 'до Q3 (метаданных нет)'} "
        f"cues={len(cues)}"
    )
    print(f"[subtitles] результат={result.status}")
    for issue in result.issues:
        print(f"  [{issue.severity}] {issue.code}: {issue.message}")


def print_script_capabilities(data: list[dict[str, Any]]) -> None:
    for item in data:
        paid = "платный" if item["requires_paid_api"] else "бесплатный"
        net = "нужна сеть" if item["requires_network"] else "офлайн"
        print(
            f"[script] {item['provider_id']}: {item['display_name']} "
            f"({paid}, {net}, {item['implementation_status']})"
        )
        print(f"          {item['description']}")


def print_script_outcome(outcome: Any, job: Any, *, written_to: str = "") -> None:
    result = outcome.result
    print(
        f"[script] движок={outcome.provider_id} "
        f"источник={result.source_kind} язык={result.language}"
    )
    if outcome.used_fallback:
        print(
            f"[script] запрошен {outcome.requested_provider_id}, "
            f"отработал {outcome.provider_id}"
        )
    print(
        f"[script] сцен={len(result.scenes)} "
        f"расчётная длительность={result.estimated_duration_sec:.1f} с "
        f"(цель {job.target_duration_sec} с)"
    )
    for scene in result.scenes:
        print(
            f"  {scene.scene_id} [{scene.role:<11}] {scene.duration_sec:5.1f} с  "
            f"{scene.narration[:70]}"
        )
        if scene.visual_brief:
            brief = scene.visual_brief
            print(
                f"      визуал: класс={brief.get('source_class') or '-'} "
                f"предмет={brief.get('subject') or '-'} "
                f"место={brief.get('place') or brief.get('location') or '-'}"
            )
            if brief.get("exact_entities"):
                print(
                    "      точные сущности: "
                    + ", ".join(str(item) for item in brief["exact_entities"])
                )
            if brief.get("must_avoid"):
                print(
                    "      запрещено: "
                    + ", ".join(str(item) for item in brief["must_avoid"])
                )
            if brief.get("infographic"):
                print(
                    "      инфографика: "
                    + json.dumps(brief["infographic"], ensure_ascii=False)
                )
    for warning in result.warnings:
        print(f"[script] предупреждение: {warning}")
    print_script_validation(outcome.validation, scene_count=len(result.scenes))
    if written_to:
        print(f"[script] script.json записан: {Path(written_to).resolve()}")


def print_visual_planner_capabilities(data: list[dict[str, Any]]) -> None:
    for item in data:
        paid = "платный" if item["requires_paid_api"] else "бесплатный"
        net = "нужна сеть" if item["requires_network"] else "офлайн"
        print(
            f"[visual-plan] {item['planner_id']}: {item['display_name']} "
            f"({paid}, {net}, язык intent={item['intent_language']}, "
            f"{item['implementation_status']})"
        )
        print(f"              {item['description']}")


def print_visual_plan_intents(plan: Any, *, intent_to_query_fn: Any) -> None:
    for scene in plan.scenes:
        print(f"[visual-plan] {scene.scene_id} ({scene.shot_type})")
        for intent in scene.intents:
            mark = " (нужен перевод)" if intent.requires_translation else ""
            print(
                f"    {intent.kind:<22} ур.{intent.fallback_level} "
                f"[{intent.language}]{mark}  {intent_to_query_fn(intent)}"
            )


def print_visual_plan_outcome(
    planning: Any,
    *,
    intent_to_query_fn: Any,
    written_to: str = "",
) -> None:
    plan = planning.result
    print(
        f"[visual-plan] планировщик={planning.planner_id} "
        f"тема={plan.topic_entity!r} язык={plan.language}"
    )
    for scene in plan.scenes:
        print(
            f"  {scene.scene_id} [{scene.shot_type:<12}] "
            f"{scene.preferred_media_kind:<15} {scene.meaning[:56]}"
        )
        print(
            f"      предмет={scene.subject!r} действие={scene.action!r} "
            f"место={scene.place!r} эпоха={scene.period!r}"
        )
        for intent in scene.intents:
            print(
                f"      -> ур.{intent.fallback_level} {intent.kind:<22} "
                f"{intent_to_query_fn(intent)}"
            )
        for warning in scene.warnings:
            print(f"      предупреждение: {warning}")
    for warning in plan.warnings:
        print(f"[visual-plan] предупреждение: {warning}")
    print_plan_validation(planning.validation, scene_count=len(plan.scenes))
    if written_to:
        print(f"[visual-plan] visual_plan.json записан: {Path(written_to).resolve()}")


def print_plan_validation(validation: Any, *, scene_count: int) -> None:
    label = {
        "passed": "проверка пройдена",
        "needs_review": "нужна проверка",
        "failed": "не проходит",
    }
    print(
        f"[visual-plan] {label.get(validation.status, validation.status)} "
        f"(сцен: {scene_count})"
    )
    for issue in validation.issues:
        mark = "ошибка " if issue.severity == "error" else "внимание"
        where = f" [{issue.scene_id}]" if issue.scene_id else ""
        print(f"  {mark}{where} {issue.code}: {issue.message}")


def print_script_validation(validation: Any, *, scene_count: int) -> None:
    label = {
        "passed": "проверка пройдена",
        "needs_review": "нужна проверка",
        "failed": "не проходит",
    }
    print(
        f"[script] {label.get(validation.status, validation.status)} "
        f"(сцен: {scene_count})"
    )
    for issue in validation.issues:
        mark = "ошибка " if issue.severity == "error" else "внимание"
        where = f" [{issue.scene_id}]" if issue.scene_id else ""
        print(f"  {mark}{where} {issue.code}: {issue.message}")


__all__ = [
    "print_capabilities",
    "print_config_explanation",
    "print_localizations",
    "print_plain",
    "print_plan_validation",
    "print_script_capabilities",
    "print_script_outcome",
    "print_script_validation",
    "print_subtitle_explanation",
    "print_subtitle_validation",
    "print_visual_plan_intents",
    "print_visual_plan_outcome",
    "print_visual_planner_capabilities",
]
