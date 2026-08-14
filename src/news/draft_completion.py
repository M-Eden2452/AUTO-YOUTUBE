"""Autonomous draft completion for the news_to_short pipeline (stage Q2.2B).

This is the orchestration layer, not a second pipeline. It calls the existing stages -
the script engine, the visual planner, ``build_news_asset_manifest``, the renderer - and
adds exactly three things they did not have:

1. **one** asset-aware adaptation pass, run only over the scenes that could not be
   answered, verified against the script's own fact locks;
2. a **draft render gate**, separate from the strict publish gate, that asks whether the
   video can be assembled rather than whether it is finished;
3. the **replacement report**, written after the render, so the author sees every weak
   fragment with its timecode.

Nothing here searches, renders, speaks or pays on its own; it decides what to call and
in what order, and it records why.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.assets.completion import (
    MODE_DRAFT_COMPLETE,
    ReuseLedger,
    blocking_reasons,
    evaluate_usability,
    normalize_mode,
    read_assembly,
)
from src.assets.completion.modes import TIER_RANK
from src.assets.completion.report import build_replacement_report, write_replacement_report
from src.content.script_engine.adaptation import (
    ADAPT_NONE,
    MAX_ADAPTATION_PASSES,
    SceneAdaptationRequest,
    ScriptAdaptationReport,
    adapt_scenes,
    apply_adaptation_to_script,
    get_adapter,
    normalize_adaptation_mode,
)
from src.content.script_engine.fact_locks import extract_fact_locks

from .models import NewsJob, completion_settings

# Gate check ids, so a caller can react to a specific failure rather than a message.
CHECK_SCENE_COVERAGE = "scene_coverage"
CHECK_AUDIO = "narration_audio"
CHECK_TIMELINE = "slot_timeline"
CHECK_RIGHTS = "asset_rights"
CHECK_FILES = "asset_files"
CHECK_CONTENT = "asset_content"
CHECK_SUBTITLES = "subtitles"

REASON_VOICE_REQUIRED = "voice_provider_required"


def script_paths(root: Path, language: str) -> dict[str, Path]:
    base = root / "localizations" / language / "script"
    return {
        "script": base / "script.json",
        "original": base / "script_original.json",
        "adapted": base / "script_adapted.json",
        "adaptation_report": base / "script_adaptation_report.json",
        "fact_locks": base / "script_fact_locks.json",
    }


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------- #
# Adaptation pass
# --------------------------------------------------------------------------- #


def collect_adaptation_requests(
    *,
    script: dict[str, Any],
    visual_plan: dict[str, Any],
    assets_manifest: dict[str, Any],
    fact_locks: Any,
) -> list[SceneAdaptationRequest]:
    """One request per scene the retrieval stage could not answer well.

    A scene that is already publish-ready is never adapted: rewriting what worked is how
    an adaptation loop turns into a regression.
    """
    plan_scenes = {
        str(entry.get("scene_id") or ""): entry
        for entry in (visual_plan.get("scenes") or [])
        if isinstance(entry, dict)
    }
    script_scenes = {
        str(entry.get("scene_id") or ""): entry
        for entry in (script.get("scenes") or [])
        if isinstance(entry, dict)
    }
    requests: list[SceneAdaptationRequest] = []
    for entry in assets_manifest.get("scenes") or []:
        if not isinstance(entry, dict):
            continue
        scene_id = str(entry.get("scene_id") or "")
        duration = float(entry.get("required_duration_sec") or 0.0)
        assembly = read_assembly(entry, scene_duration_sec=duration)
        if assembly.publish_ready:
            continue
        plan_scene = plan_scenes.get(scene_id, {})
        script_scene = script_scenes.get(scene_id, {})
        brief = plan_scene.get("visual_brief") if isinstance(plan_scene.get("visual_brief"), dict) else {}
        missing: list[str] = []
        for slot in assembly.slots:
            missing.extend(slot.usability.limitations)
        rejected = [
            str(candidate.get("reject_reason") or "")
            for candidate in (entry.get("ranked_candidates") or [])
            if isinstance(candidate, dict) and candidate.get("reject_reason")
        ]
        requests.append(
            SceneAdaptationRequest(
                scene_id=scene_id,
                narration=str(script_scene.get("narration") or entry.get("narration") or ""),
                reason=str(entry.get("resolution_status") or "not_publish_ready"),
                missing_slots=list(dict.fromkeys(missing)),
                rejected_reasons=rejected[:8],
                unmatched_requirements=_unmatched_requirements(entry),
                visual_brief=dict(brief),
                source_class=str(entry.get("source_class") or ""),
                scene_duration_sec=duration,
                locks=fact_locks.for_scene(scene_id),
            )
        )
    return requests


def _unmatched_requirements(entry: dict[str, Any]) -> list[str]:
    """Author-stated terms no candidate could be shown to contain."""
    terms: list[str] = []
    for candidate in entry.get("ranked_candidates") or []:
        if not isinstance(candidate, dict):
            continue
        for reason in str(candidate.get("reject_reason") or "").split(";"):
            for prefix in ("must_include_missing:", "must_include_unverifiable:"):
                if reason.startswith(prefix):
                    terms.extend(part for part in reason[len(prefix):].split(",") if part)
        terms.extend(str(item) for item in (candidate.get("must_include_unverifiable") or []))
    return list(dict.fromkeys(terms))


def run_adaptation_pass(
    *,
    store: Any,
    job: NewsJob,
    root: Path,
    adapter: Any | None = None,
    allow_paid: bool = False,
    research_scenes: Any | None = None,
) -> dict[str, Any]:
    """Adapt the problem scenes once, re-search only those, keep whichever is better.

    ``research_scenes(plan_subset)`` performs the re-search. It is injected so this
    function stays testable offline and so the caller decides whether a provider may be
    contacted at all; passing ``None`` runs the adaptation and the re-planning but leaves
    the existing search results in place.
    """
    settings = completion_settings(job)
    mode = normalize_mode(settings.get("mode"))
    adaptation_mode = normalize_adaptation_mode(settings.get("script_adaptation"))
    paths = script_paths(root, job.language)
    if mode != MODE_DRAFT_COMPLETE or adaptation_mode == ADAPT_NONE:
        return {"status": "skipped", "reason": "adaptation_not_requested", "mode": mode}
    if int(settings.get("adaptation_pass") or 0) >= MAX_ADAPTATION_PASSES:
        return {"status": "skipped", "reason": "adaptation_pass_limit_reached", "mode": mode}

    script = _read_json(paths["script"])
    if not script.get("scenes"):
        return {"status": "skipped", "reason": "no_script_on_disk", "mode": mode}
    assets_manifest = _read_json(root / "assets" / "assets_manifest.json")
    visual_plan = _read_json(root / "localizations" / job.language / "visual" / "visual_plan.json")
    research = _read_json(root / "research" / "claims.json")

    fact_locks = extract_fact_locks(script, research=research)
    _write_json(paths["fact_locks"], fact_locks.to_dict())

    requests = collect_adaptation_requests(
        script=script, visual_plan=visual_plan, assets_manifest=assets_manifest, fact_locks=fact_locks
    )
    report = adapt_scenes(
        requests=requests,
        fact_locks=fact_locks,
        adapter=adapter or get_adapter(),
        mode=adaptation_mode,
        pass_index=int(settings.get("adaptation_pass") or 0),
        allow_paid=allow_paid,
    )
    if not paths["original"].exists():
        # Written once before considering a proposal. A failed/no-improvement pass is
        # therefore as auditable as an accepted rewrite.
        _write_json(paths["original"], script)
    proposed = apply_adaptation_to_script(script, report)
    proposed_plan = _replan(proposed, job=job, research=research, visual_plan=visual_plan)
    merged = assets_manifest
    improved: set[str] = set()
    research_error = ""
    if report.changed_scene_ids and research_scenes is not None:
        changed = set(report.changed_scene_ids)
        subset = {
            **proposed_plan,
            "scenes": [
                entry
                for entry in (proposed_plan.get("scenes") or [])
                if str(entry.get("scene_id") or "") in changed
            ],
        }
        if subset["scenes"]:
            try:
                fresh = research_scenes(subset)
                merged = merge_scene_results(assets_manifest, fresh)
                improved = set(merged.get("adaptation_replaced_scenes") or [])
            except Exception as exc:
                # A provider failure is not allowed to corrupt the script or consume
                # the fallback assets. The attempted pass is recorded and ends here.
                research_error = str(exc)
                report.warnings.append(f"asset_research_failed:{exc}")

    # Only scenes whose visual coverage really improved may keep an adaptation. All
    # other proposals are converted into explicit, serialized rejections.
    for outcome in report.scenes:
        if outcome.changed and outcome.scene_id not in improved:
            outcome.accepted = False
            outcome.rejection_reason = (
                "asset_research_failed" if research_error else "visual_coverage_not_improved"
            )

    accepted = apply_adaptation_to_script(script, report)
    accepted_plan = _replan(
        accepted,
        job=job,
        research=research,
        visual_plan=visual_plan,
        usage_plan=proposed_plan,
    )
    _write_json(paths["adapted"], accepted)
    visual_plan_path = (
        root / "localizations" / job.language / "visual" / "visual_plan.json"
    )
    if improved:
        _write_json(paths["script"], accepted)
        _write_json(visual_plan_path, accepted_plan)
        _write_json(root / "assets" / "assets_manifest.json", merged)
        _write_json(
            root / "assets" / "missing_assets.json",
            {"missing_scenes": merged.get("missing_scenes", [])},
        )
    else:
        previous_usage = (
            (visual_plan.get("planning_metadata") or {}).get(
                "semantic_brief_usage"
            )
            or {}
        )
        cumulative_usage = (
            (accepted_plan.get("planning_metadata") or {}).get(
                "semantic_brief_usage"
            )
            or {}
        )
        if cumulative_usage and cumulative_usage != previous_usage:
            retained_plan = dict(visual_plan)
            retained_metadata = dict(retained_plan.get("planning_metadata") or {})
            retained_metadata["semantic_brief_usage"] = dict(cumulative_usage)
            retained_plan["planning_metadata"] = retained_metadata
            _write_json(visual_plan_path, retained_plan)

    _write_json(paths["adaptation_report"], report.to_dict())
    # The pass is spent after a complete attempt, whether it helped or fell back.
    # That makes the single-pass rule durable across resume without losing the
    # original script on a provider error.
    job.completion = {
        **settings,
        "adaptation_pass": int(settings.get("adaptation_pass") or 0) + 1,
    }
    store.save_job(job)
    status = "adapted" if improved else "no_change"
    return {
        "status": status,
        "mode": mode,
        "adaptation": report.to_dict(),
        "changed_scene_ids": sorted(improved),
        "requested_scenes": [item.scene_id for item in requests],
        "researched": research_scenes is not None,
        "research_error": research_error,
        "script_paths": {key: str(value) for key, value in paths.items()},
    }


def _usage_calls(usage: dict[str, Any]) -> int:
    try:
        return int(usage.get("calls") or 0)
    except (TypeError, ValueError):
        return 0


def _usage_cost(usage: dict[str, Any]) -> float:
    try:
        return float(usage.get("estimated_cost_usd") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _accumulate_semantic_brief_usage(
    plan: dict[str, Any], previous_plan: dict[str, Any]
) -> dict[str, Any]:
    """Carry prior spend forward while keeping each adapter's call cap unchanged."""
    metadata = dict(plan.get("planning_metadata") or {})
    current = dict(metadata.get("semantic_brief_usage") or {})
    previous = dict(
        (previous_plan.get("planning_metadata") or {}).get(
            "semantic_brief_usage"
        )
        or {}
    )
    if not current and not previous:
        return plan
    usage = dict(current or previous)
    if current and previous:
        usage["calls"] = _usage_calls(previous) + _usage_calls(current)
        usage["estimated_cost_usd"] = round(
            _usage_cost(previous) + _usage_cost(current), 6
        )
    metadata["semantic_brief_usage"] = usage
    return {**plan, "planning_metadata": metadata}


def _replan(
    adapted_script: dict[str, Any],
    *,
    job: NewsJob,
    research: dict[str, Any],
    visual_plan: dict[str, Any],
    usage_plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Rebuild a plan while preserving scenes and cumulative semantic spend.

    The localized visual plan is the cumulative project record; the master plan keeps
    the planning-stage snapshot. The call cap remains per adapter instance.
    """
    from .visual_plan import build_visual_plan

    plan = build_visual_plan(
        adapted_script, language=job.language, user_assets=job.user_assets, research=research
    )
    plan = _accumulate_semantic_brief_usage(
        plan, usage_plan if usage_plan is not None else visual_plan
    )
    # Anything the stored plan carried that the planner does not produce (an author's
    # hand-written brief on an untouched scene) is preserved rather than regenerated.
    previous = {
        str(entry.get("scene_id") or ""): entry
        for entry in (visual_plan.get("scenes") or [])
        if isinstance(entry, dict)
    }
    scenes = []
    script_by_id = {
        str(scene.get("scene_id") or ""): scene
        for scene in (adapted_script.get("scenes") or [])
        if isinstance(scene, dict)
    }
    adapted_ids = {
        str(scene.get("scene_id") or "")
        for scene in (adapted_script.get("scenes") or [])
        if isinstance(scene, dict)
        and (
            scene.get("visual_brief_adapted")
            or scene.get("visual_parts")
            or scene.get("adaptation_rules")
        )
    }
    for entry in plan.get("scenes") or []:
        scene_id = str(entry.get("scene_id") or "")
        if scene_id in previous and scene_id not in adapted_ids:
            scenes.append(previous[scene_id])
        else:
            updated = dict(entry)
            script_scene = script_by_id.get(scene_id, {})
            if script_scene.get("visual_parts"):
                updated["visual_parts"] = list(script_scene["visual_parts"])
            scenes.append(updated)
    return {**plan, "scenes": scenes}


def merge_scene_results(existing: dict[str, Any], fresh: dict[str, Any]) -> dict[str, Any]:
    """Merge a re-search of a few scenes into the full manifest, keeping the better one.

    "Better" is decided by what the author would prefer to look at: publish-ready first,
    then draft-usable, then the quality tier. When the adapted search did not improve the
    scene, the original result is kept - which is what makes an unhelpful adaptation
    harmless rather than destructive.
    """
    merged = dict(existing)
    by_id = {
        str(entry.get("scene_id") or ""): entry
        for entry in (existing.get("scenes") or [])
        if isinstance(entry, dict)
    }
    replaced: list[str] = []
    for entry in fresh.get("scenes") or []:
        if not isinstance(entry, dict):
            continue
        scene_id = str(entry.get("scene_id") or "")
        previous = by_id.get(scene_id)
        if previous is None:
            by_id[scene_id] = entry
            replaced.append(scene_id)
            continue
        if _assembly_rank(entry) < _assembly_rank(previous):
            by_id[scene_id] = entry
            replaced.append(scene_id)
    existing_order = [
        str(item.get("scene_id") or "")
        for item in (existing.get("scenes") or [])
        if isinstance(item, dict)
    ]
    merged["scenes"] = [by_id[key] for key in existing_order if key in by_id]
    present = set(existing_order)
    for scene_id, entry in by_id.items():
        if scene_id not in present:
            merged["scenes"].append(entry)
            present.add(scene_id)
    usable = {
        str(entry.get("scene_id") or "")
        for entry in merged["scenes"]
        if read_assembly(entry, scene_duration_sec=float(entry.get("required_duration_sec") or 0.0)).usable_in_draft
    }
    missing_by_id = {
        str(item.get("scene_id") or ""): item
        for item in (existing.get("missing_scenes") or [])
        if isinstance(item, dict)
    }
    fresh_scene_ids = {
        str(item.get("scene_id") or "")
        for item in (fresh.get("scenes") or [])
        if isinstance(item, dict)
    }
    for scene_id in fresh_scene_ids:
        missing_by_id.pop(scene_id, None)
    for item in fresh.get("missing_scenes") or []:
        if isinstance(item, dict):
            missing_by_id[str(item.get("scene_id") or "")] = item
    merged["missing_scenes"] = [
        item for scene_id, item in missing_by_id.items() if scene_id not in usable
    ]
    merged["adaptation_replaced_scenes"] = replaced
    merged["provider_attempts"] = [
        *(existing.get("provider_attempts") or []),
        *(fresh.get("provider_attempts") or []),
    ]
    merged["provider_errors"] = [
        *(existing.get("provider_errors") or []),
        *(fresh.get("provider_errors") or []),
    ]
    merged["routing_decisions"] = _merge_scene_records(
        existing.get("routing_decisions") or [],
        fresh.get("routing_decisions") or [],
    )
    # These are derived from scenes and must be rebuilt after a partial re-search.
    from .asset_manager import refresh_manifest_summaries

    ledger_source = fresh if isinstance(fresh.get("completion"), dict) else existing
    ledger = reuse_ledger_from_manifest(ledger_source)
    existing_completion = (
        existing.get("completion") if isinstance(existing.get("completion"), dict) else {}
    )
    summary_mode = str(existing_completion.get("mode") or MODE_DRAFT_COMPLETE)
    refresh_manifest_summaries(merged, mode=summary_mode, reuse=ledger)
    return merged


def _merge_scene_records(existing: list[Any], fresh: list[Any]) -> list[Any]:
    """Replace scene-keyed derived records while preserving stable order."""
    by_id = {
        str(item.get("scene_id") or ""): item
        for item in existing
        if isinstance(item, dict)
    }
    order = list(by_id)
    for item in fresh:
        if not isinstance(item, dict):
            continue
        scene_id = str(item.get("scene_id") or "")
        if scene_id not in by_id:
            order.append(scene_id)
        by_id[scene_id] = item
    return [by_id[scene_id] for scene_id in order]


def _assembly_rank(entry: dict[str, Any]) -> tuple[int, int, int, int, int, int]:
    from src.assets.semantic_selection.decision import read_decision

    assembly = read_assembly(entry, scene_duration_sec=float(entry.get("required_duration_sec") or 0.0))
    matched = 0
    missing = 0
    conflicting = 0
    for slot in assembly.slots:
        slots = read_decision(slot.selected_asset).slots
        if not isinstance(slots, dict):
            continue
        matched += len(slots.get("matched_slots") or [])
        missing += len(slots.get("missing_required_slots") or slots.get("missing_slots") or [])
        conflicting += len(slots.get("conflicting_slots") or [])
    return (
        0 if assembly.publish_ready else 1,
        0 if assembly.usable_in_draft else 1,
        TIER_RANK.get(assembly.quality_tier, 99),
        conflicting,
        missing,
        -matched,
    )


# --------------------------------------------------------------------------- #
# Draft render gate
# --------------------------------------------------------------------------- #


def evaluate_draft_render_gate(
    *,
    script: dict[str, Any],
    assets_manifest: dict[str, Any],
    voice_manifest: dict[str, Any] | None = None,
    subtitles_manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """May a draft be assembled? Deliberately not "is this video finished".

    Requires: every narration scene filled with usable material, narration audio on
    disk, a sound slot timeline, cleared rights and a valid file for every fragment
    actually used, and nothing that would make a false claim. Does *not* require full
    support, publish-readiness, or an empty replacement list - those are the publish
    gate, which stays exactly as strict as it was.
    """
    checks: list[dict[str, str]] = []
    problems: list[dict[str, str]] = []

    entries = {
        str(entry.get("scene_id") or ""): entry
        for entry in (assets_manifest.get("scenes") or [])
        if isinstance(entry, dict)
    }
    script_scenes = [scene for scene in (script.get("scenes") or []) if isinstance(scene, dict)]
    if not script_scenes:
        problems.append({"check": CHECK_SCENE_COVERAGE, "message": "Script has no scenes."})

    for index, scene in enumerate(script_scenes, start=1):
        scene_id = str(scene.get("scene_id") or f"scene_{index:03d}")
        entry = entries.get(scene_id)
        if entry is None:
            problems.append({"check": CHECK_SCENE_COVERAGE, "message": f"Scene {scene_id} has no asset entry."})
            continue
        duration = float(entry.get("required_duration_sec") or 0.0)
        assembly = read_assembly(entry, scene_duration_sec=duration)
        if not assembly.slots:
            problems.append(
                {"check": CHECK_SCENE_COVERAGE, "message": f"Scene {scene_id} has no usable visual slot."}
            )
            continue
        for problem in assembly.validate():
            problems.append({"check": CHECK_TIMELINE, "message": f"Scene {scene_id}: {problem}."})
        for slot in assembly.slots:
            asset = slot.selected_asset
            reasons = blocking_reasons(asset, require_local_file=True)
            readiness = evaluate_usability(
                asset,
                mode=MODE_DRAFT_COMPLETE,
                quality_tier=slot.quality_tier,
                require_local_file=True,
            )
            if not readiness.usable_in_draft and not reasons:
                reasons = ["not_usable_in_draft"]
            for reason in reasons:
                check = {
                    "rights_blocked": CHECK_RIGHTS,
                    "technical_blocked": CHECK_FILES,
                    "no_usable_media_file": CHECK_FILES,
                }.get(reason, CHECK_CONTENT)
                problems.append(
                    {"check": check, "message": f"Scene {scene_id} slot {slot.slot_id}: {reason}."}
                )
            path = slot.media_path
            if path and not Path(path).exists():
                problems.append(
                    {"check": CHECK_FILES, "message": f"Scene {scene_id} slot {slot.slot_id} file is missing."}
                )
    if not problems:
        checks.append({"check": CHECK_SCENE_COVERAGE, "message": "Every scene has usable material with cleared rights."})

    audio_path = str((voice_manifest or {}).get("audio_path") or "")
    if not audio_path or not Path(audio_path).exists():
        problems.append({"check": CHECK_AUDIO, "message": "Narration audio does not exist yet."})
    else:
        checks.append({"check": CHECK_AUDIO, "message": "Narration audio is on disk."})

    if subtitles_manifest and subtitles_manifest.get("ass_path"):
        checks.append({"check": CHECK_SUBTITLES, "message": "Subtitles are prepared."})

    blocked_by_audio = any(item["check"] == CHECK_AUDIO for item in problems)
    status = "allowed" if not problems else "blocked"
    reason = ""
    if blocked_by_audio and len(problems) == 1:
        reason = REASON_VOICE_REQUIRED
    elif problems:
        reason = problems[0]["check"]
    return {"status": status, "reason": reason, "problems": problems, "checks": checks}


# --------------------------------------------------------------------------- #
# Replacement report
# --------------------------------------------------------------------------- #


def write_completion_report(*, root: Path, job: NewsJob) -> dict[str, str]:
    """Build and write the weak-fragment report from what is already on disk."""
    settings = completion_settings(job)
    script = _read_json(root / "localizations" / job.language / "script" / "script.json")
    assets_manifest = _read_json(root / "assets" / "assets_manifest.json")
    render_manifest = _read_json(root / "render" / "final_render_manifest.json")
    adaptation = _read_json(script_paths(root, job.language)["adaptation_report"])
    completion = assets_manifest.get("completion") if isinstance(assets_manifest.get("completion"), dict) else {}
    report = build_replacement_report(
        project_id=job.job_id,
        script=script,
        assets_manifest=assets_manifest,
        completion_mode=str(settings.get("mode") or ""),
        render_manifest=render_manifest,
        adaptation_report=adaptation,
        reuse=completion.get("reuse") if isinstance(completion.get("reuse"), dict) else {},
    )
    return write_replacement_report(root, report)


def reuse_ledger_from_manifest(assets_manifest: dict[str, Any]) -> ReuseLedger:
    """Rebuild the reuse ledger a manifest recorded, for a re-search of a few scenes."""
    completion = assets_manifest.get("completion") if isinstance(assets_manifest.get("completion"), dict) else {}
    stored = completion.get("reuse") if isinstance(completion.get("reuse"), dict) else {}
    ledger = ReuseLedger(
        max_uses=int(stored.get("max_uses") or ReuseLedger.max_uses),
        min_scene_gap=int(stored.get("min_scene_gap") or ReuseLedger.min_scene_gap),
    )
    for asset_id, uses in (stored.get("uses") or {}).items():
        ledger.uses[str(asset_id)] = [int(item) for item in uses or []]
    for asset_id, scenes in (stored.get("scenes") or {}).items():
        ledger.scenes[str(asset_id)] = [str(item) for item in scenes or []]
    return ledger


__all__ = [
    "CHECK_AUDIO",
    "CHECK_CONTENT",
    "CHECK_FILES",
    "CHECK_RIGHTS",
    "CHECK_SCENE_COVERAGE",
    "CHECK_SUBTITLES",
    "CHECK_TIMELINE",
    "REASON_VOICE_REQUIRED",
    "ScriptAdaptationReport",
    "collect_adaptation_requests",
    "evaluate_draft_render_gate",
    "merge_scene_results",
    "reuse_ledger_from_manifest",
    "run_adaptation_pass",
    "script_paths",
    "write_completion_report",
]
