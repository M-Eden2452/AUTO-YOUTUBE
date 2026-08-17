"""What is weak in the finished draft, with timecodes and a way to fix each item.

A draft that quietly contains four stand-in shots is worse than no draft at all. This
module is the other half of autonomous completion: for every fragment that is not
publish-ready it writes down where it is in the video, what is actually on screen, what
is missing, how urgent it is, and exactly what to search for and where.

Four artefacts, deliberately in four shapes:

``replacement_report.json``      the full record, for tools
``replacement_report.html``      the same thing to read, offline, no external assets
``replacement_queue.json``       just the work, ordered by priority
``timeline_replacement_map.csv`` timecode -> scene/slot, for scrubbing the video

Nothing here re-runs a search, contacts a provider, or costs anything. It reports what
the assembly stage already decided.
"""

from __future__ import annotations

import csv
import html
import json
from pathlib import Path
from typing import Any

from src.assets.completion.assembly import SceneVisualAssembly, read_assembly
from src.assets.query_adapter import STATUS_OK
from src.assets.completion.modes import (
    BLOCK_MISSING_FILE,
    PRIORITY_CRITICAL,
    PRIORITY_NONE,
    PRIORITY_RANK,
    QUALITY_TIERS,
    TIER_NONE,
    evaluate_usability,
    normalize_mode,
)

REPLACEMENT_REPORT_SCHEMA_VERSION = 1

# Where a replacement can realistically come from, provider-neutral on purpose: the
# first two are manual handoffs the project does not automate (and does not claim to),
# the rest are the search providers already implemented.
RECOMMENDED_SOURCES_VIDEO = ["envato_manual", "pexels", "pixabay", "internet_archive", "wikimedia", "manual_upload"]
RECOMMENDED_SOURCES_IMAGE = ["wikimedia", "nasa_images", "pexels", "pixabay", "internet_archive", "manual_upload"]

# What each limitation code means in one sentence, for the human-readable report.
_LIMITATION_TEXT = {
    "crop_not_verified": "не проверено, переживает ли объект кроп под 9:16",
    "needs_manual_confirmation": "требуется решение автора",
    "needs_rights_clearance": "права требуют отдельной проверки",
}


def timecode(seconds: float) -> str:
    """``MM:SS.s`` - the form a person types into a player."""
    value = max(0.0, float(seconds or 0.0))
    minutes = int(value // 60)
    remainder = value - minutes * 60
    return f"{minutes:02d}:{remainder:04.1f}"


def scene_start_times(script: dict[str, Any]) -> dict[str, tuple[float, float]]:
    """``scene_id -> (start_sec, duration_sec)`` from the script's own timing.

    Real narration timing wins over the plan, exactly as the renderer and the subtitle
    builder already do - this module must not invent a second timeline.
    """
    from src.audio.scene_timeline import scene_render_duration

    result: dict[str, tuple[float, float]] = {}
    cursor = 0.0
    for index, scene in enumerate(script.get("scenes") or [], start=1):
        if not isinstance(scene, dict):
            continue
        scene_id = str(scene.get("scene_id") or f"scene_{index:03d}")
        duration = scene_render_duration(scene)
        start = scene.get("start_sec")
        start_sec = float(start) if start not in (None, "") else cursor
        result[scene_id] = (start_sec, duration)
        cursor = start_sec + duration
    return result


def search_queries_for(scene_entry: dict[str, Any]) -> list[str]:
    """Available provider/search phrases for replacing this scene's material.

    Taken from what the project already has - the author's brief and the query plan the
    retrieval stage built. This general field intentionally preserves original-language
    phrases. Use :func:`english_search_queries_for` for the stricter English/ASCII view.
    """
    queries: list[str] = []
    brief = scene_entry.get("visual_brief") if isinstance(scene_entry.get("visual_brief"), dict) else {}
    provider_queries = brief.get("provider_queries") if isinstance(brief.get("provider_queries"), dict) else {}
    for values in provider_queries.values():
        queries.extend(_query_strings(values))
    plan = scene_entry.get("query_plan") if isinstance(scene_entry.get("query_plan"), dict) else {}
    for item in plan.get("queries") or []:
        # Only what the plan meant to send. A query the language gate refused is
        # now recorded in the plan (``query_language_unsupported``), and offering
        # it back here as a usable phrase would resurrect the one string the gate
        # exists to stop. Absent status reads as sendable, which is what every
        # plan written before that record looked like.
        if not isinstance(item, dict) or not item.get("query"):
            continue
        status = str(item.get("status") or STATUS_OK)
        if status in {STATUS_OK, ""}:
            queries.append(str(item["query"]))
    composed = " ".join(
        part
        for part in (
            str(brief.get("subject") or ""),
            str(brief.get("action") or ""),
            str(brief.get("place") or brief.get("location") or ""),
        )
        if part
    ).strip()
    if composed:
        queries.append(composed)
    return list(dict.fromkeys(query.strip() for query in queries if query.strip()))


def english_search_queries_for(scene_entry: dict[str, Any]) -> list[str]:
    """Only existing queries that are defensibly usable as English/ASCII.

    This is deliberately a filter, not a translator. Cyrillic (including a query
    incorrectly tagged ``language=en``) is omitted rather than guessed, and no provider,
    model or network boundary is called.
    """
    return [
        query
        for query in search_queries_for(scene_entry)
        if _is_defensibly_ascii_query(query)
    ]


def _query_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, set):
        value = sorted(value, key=lambda item: str(item))
    if isinstance(value, (list, tuple)):
        return [
            str(item)
            for item in value
            if isinstance(item, (str, int, float)) and str(item).strip()
        ]
    return []


def _is_defensibly_ascii_query(value: str) -> bool:
    text = str(value or "").strip()
    return bool(text and text.isascii() and any(character.isalpha() for character in text))


def build_replacement_report(
    *,
    project_id: str,
    script: dict[str, Any],
    assets_manifest: dict[str, Any],
    completion_mode: str = "",
    render_manifest: dict[str, Any] | None = None,
    adaptation_report: dict[str, Any] | None = None,
    reuse: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """The whole report as data. Pure - no filesystem, no clock, no network."""
    timings = scene_start_times(script)
    fragments: list[dict[str, Any]] = []
    tier_counts: dict[str, int] = {tier: 0 for tier in QUALITY_TIERS}
    status_counts: dict[str, int] = {}
    publish_ready_scenes = 0
    draft_usable_scenes = 0
    publish_ready_scene_ids: list[str] = []
    draft_only_scene_ids: list[str] = []
    unresolved_scenes: list[str] = []
    resolved_mode = normalize_mode(completion_mode)
    manifest_entries = (
        list(assets_manifest.get("scenes") or [])
        if isinstance(assets_manifest.get("scenes") or [], list)
        else []
    )
    manifest_scene_ids = {
        str(entry.get("scene_id") or "")
        for entry in manifest_entries
        if isinstance(entry, dict) and entry.get("scene_id")
    }

    for entry in manifest_entries:
        if not isinstance(entry, dict):
            continue
        scene_id = str(entry.get("scene_id") or "")
        start_sec, duration = timings.get(scene_id, (0.0, float(entry.get("required_duration_sec") or 0.0)))
        assembly = read_assembly(entry, scene_duration_sec=duration)
        status_counts[assembly.assembly_status] = status_counts.get(assembly.assembly_status, 0) + 1
        readiness_by_slot = {
            slot.slot_id: evaluate_usability(
                slot.selected_asset,
                mode=resolved_mode,
                quality_tier=slot.quality_tier,
                require_local_file=True,
                reuse_count=1 if slot.reuse_of_asset else 0,
            )
            for slot in assembly.slots
        }
        timeline_valid = not assembly.validate()
        scene_publish_ready = bool(assembly.slots) and timeline_valid and all(
            readiness.publish_ready for readiness in readiness_by_slot.values()
        )
        scene_draft_usable = bool(assembly.slots) and timeline_valid and all(
            readiness.usable_in_draft for readiness in readiness_by_slot.values()
        )
        if scene_publish_ready:
            publish_ready_scenes += 1
            publish_ready_scene_ids.append(scene_id)
        if scene_draft_usable:
            draft_usable_scenes += 1
            if not scene_publish_ready:
                draft_only_scene_ids.append(scene_id)
        else:
            unresolved_scenes.append(scene_id)
        narration = _narration_for(script, scene_id)
        for slot in assembly.slots:
            tier_counts[slot.quality_tier] = tier_counts.get(slot.quality_tier, 0) + 1
            readiness = readiness_by_slot[slot.slot_id]
            if readiness.publish_ready and not slot.reuse_of_asset:
                continue
            fragments.append(
                _fragment(
                    project_id=project_id,
                    entry=entry,
                    assembly=assembly,
                    slot=slot,
                    scene_start_sec=start_sec,
                    actual_scene_duration_sec=duration,
                    narration=narration,
                    readiness=readiness,
                )
            )
        if not assembly.slots:
            fragments.append(
                _missing_fragment(
                    project_id=project_id,
                    scene_id=scene_id,
                    start_sec=start_sec,
                    duration_sec=duration,
                    narration=narration,
                    scene_entry=entry,
                    weakness="no_usable_material_found",
                )
            )

    missing_narration_scene_count = 0
    missing_narration_scene_ids: set[str] = set()
    for index, scene in enumerate(script.get("scenes") or [], start=1):
        if not isinstance(scene, dict):
            continue
        narration = str(scene.get("narration") or scene.get("narration_text") or "").strip()
        if not narration:
            continue
        scene_id = str(scene.get("scene_id") or f"scene_{index:03d}")
        if scene_id in manifest_scene_ids or scene_id in missing_narration_scene_ids:
            continue
        missing_narration_scene_ids.add(scene_id)
        missing_narration_scene_count += 1
        start_sec, duration = timings.get(
            scene_id,
            (0.0, float(scene.get("actual_duration_sec") or scene.get("target_duration_sec") or 0.0)),
        )
        if scene_id not in unresolved_scenes:
            unresolved_scenes.append(scene_id)
        status_counts["unresolved"] = status_counts.get("unresolved", 0) + 1
        fragments.append(
            _missing_fragment(
                project_id=project_id,
                scene_id=scene_id,
                start_sec=start_sec,
                duration_sec=duration,
                narration=narration,
                scene_entry=scene,
                weakness="no_asset_manifest_entry",
            )
        )

    fragments.sort(key=lambda item: (PRIORITY_RANK.get(item["replacement_priority"], 99), item["start_sec"]))
    scene_count = len(manifest_entries) + missing_narration_scene_count
    reuse_data = dict(reuse or {})
    script_diff = [
        {
            "scene_id": str(item.get("scene_id") or ""),
            "original": str(item.get("original_narration") or ""),
            "adapted": str(item.get("adapted_narration") or ""),
            "reasons": list(item.get("reasons") or []),
        }
        for item in ((adaptation_report or {}).get("scenes") or [])
        if isinstance(item, dict) and item.get("changed")
    ]
    return {
        "schema_version": REPLACEMENT_REPORT_SCHEMA_VERSION,
        "project_id": project_id,
        "completion_mode": completion_mode,
        "summary": {
            "scene_count": scene_count,
            "scenes_usable_in_draft": draft_usable_scenes,
            "scenes_publish_ready": publish_ready_scenes,
            "publish_ready_scene_ids": publish_ready_scene_ids,
            "draft_only_scene_ids": draft_only_scene_ids,
            "scenes_needing_improvement": scene_count - publish_ready_scenes,
            "unresolved_scenes": unresolved_scenes,
            "weak_fragment_count": len(fragments),
            "quality_tiers": dict(tier_counts),
            "assembly_statuses": status_counts,
            "exact_scenes": status_counts.get("exact", 0),
            "composite_scenes": status_counts.get("composite", 0),
            "partial_scenes": status_counts.get("partial", 0),
            "emergency_fragments": tier_counts.get("F_emergency", 0),
            "reused_assets": reuse_data.get("repeated_assets", {}),
            "adapted_scenes": [
                str(item.get("scene_id") or "")
                for item in ((adaptation_report or {}).get("scenes") or [])
                if item.get("changed")
            ],
            "script_diff": script_diff,
        },
        "fragments": fragments,
        "script_adaptation": dict(adaptation_report or {}),
        "reuse": reuse_data,
        "render": {
            "status": str((render_manifest or {}).get("status") or ""),
            "output_path": str((render_manifest or {}).get("output_path") or ""),
            "publish_ready": bool(scene_count) and publish_ready_scenes == scene_count,
        },
    }


def _missing_fragment(
    *,
    project_id: str,
    scene_id: str,
    start_sec: float,
    duration_sec: float,
    narration: str,
    scene_entry: dict[str, Any],
    weakness: str,
) -> dict[str, Any]:
    """A complete critical work item for a narration scene with no visual slot."""
    queries = search_queries_for(scene_entry)
    replace_command = _replace_command(project_id, scene_id, "")
    return {
        "scene_id": scene_id,
        "slot_id": "",
        "purpose": "",
        "start_timecode": timecode(start_sec),
        "end_timecode": timecode(start_sec + duration_sec),
        "start_sec": round(start_sec, 3),
        "end_sec": round(start_sec + duration_sec, 3),
        "narration": narration,
        "used_file": "",
        "provider": "",
        "source_url": "",
        "license": "",
        "rights": {},
        "provenance": {},
        "checksum_sha256": "",
        "support_status": "",
        "quality_tier": TIER_NONE,
        "block_reasons": [BLOCK_MISSING_FILE],
        "why_weak": weakness,
        "what_it_shows": "",
        "what_is_missing": "everything the narration scene states",
        "replacement_priority": PRIORITY_CRITICAL,
        "recommended_material": _recommended_material_for(scene_entry),
        "search_queries": queries,
        "english_search_queries": english_search_queries_for(scene_entry),
        "recommended_sources": _sources_for(scene_entry),
        "local_path": "",
        "crop_decision": {},
        "replace_command": replace_command,
        "manual_replacement_instructions": (
            "Import a rights-cleared local image/video for this narration scene with "
            f"`{replace_command}`, then re-run quality_check and final_render."
        ),
        "reused": False,
        "reuse_reason": "",
        "limitations": [weakness],
    }


def _fragment(
    *,
    project_id: str,
    entry: dict[str, Any],
    assembly: SceneVisualAssembly,
    slot: Any,
    scene_start_sec: float,
    actual_scene_duration_sec: float,
    narration: str,
    readiness: Any,
) -> dict[str, Any]:
    asset = slot.selected_asset
    planned_duration = float(assembly.scene_duration_sec or actual_scene_duration_sec or 0.0)
    scale = (
        float(actual_scene_duration_sec) / planned_duration
        if planned_duration > 0 and actual_scene_duration_sec > 0
        else 1.0
    )
    start = scene_start_sec + float(slot.start_offset_sec or 0.0) * scale
    end = scene_start_sec + float(slot.end_offset_sec or 0.0) * scale
    limitations = list(readiness.limitations)
    provenance = asset.get("provenance") if isinstance(asset.get("provenance"), dict) else {}
    rights = asset.get("license") if isinstance(asset.get("license"), dict) else {}
    provider = str(asset.get("provider") or provenance.get("provider") or "")
    source_url = str(
        asset.get("source_page_url")
        or asset.get("source_url")
        or provenance.get("source_page_url")
        or ""
    )
    license_name = str(
        rights.get("license_name")
        or asset.get("license_name")
        or asset.get("rights_status")
        or ""
    )
    replace_command = _replace_command(project_id, assembly.scene_id, slot.slot_id)
    queries = search_queries_for(entry)
    block_reasons = list(readiness.block_reasons)
    return {
        "scene_id": assembly.scene_id,
        "slot_id": slot.slot_id,
        "purpose": slot.purpose,
        "start_timecode": timecode(start),
        "end_timecode": timecode(end),
        "start_sec": round(start, 3),
        "end_sec": round(end, 3),
        "narration": narration,
        "used_file": slot.media_path,
        "provider": provider,
        "source_url": source_url,
        "license": license_name,
        "rights": rights,
        "provenance": provenance,
        "checksum_sha256": str(asset.get("checksum_sha256") or provenance.get("checksum_sha256") or ""),
        "support_status": readiness.support_status or slot.support_status,
        "quality_tier": slot.quality_tier,
        "block_reasons": block_reasons,
        "why_weak": _why_weak(slot, readiness),
        "what_it_shows": str(asset.get("title") or asset.get("description") or ""),
        "what_is_missing": ", ".join(limitations) or "-",
        "replacement_priority": readiness.replacement_priority,
        "recommended_material": " ".join(
            part for part in (slot.required_subject, slot.required_action, slot.required_location) if part
        ).strip(),
        "search_queries": queries,
        "english_search_queries": english_search_queries_for(entry),
        "recommended_sources": _sources_for(entry),
        "local_path": slot.media_path,
        "crop_decision": dict(slot.crop_decision or {}),
        "replace_command": replace_command,
        "manual_replacement_instructions": (
            "Choose a rights-cleared file that shows the recommended material, run "
            f"`{replace_command}`, then re-run quality_check and final_render. "
            "Research, script generation and asset search are not repeated."
        ),
        "reused": bool(slot.reuse_of_asset),
        "reuse_reason": slot.reuse_reason,
        "limitations": limitations,
    }


def _why_weak(slot: Any, readiness: Any | None = None) -> str:
    block_reasons = list(readiness.block_reasons) if readiness is not None else []
    if block_reasons:
        return ";".join(block_reasons)
    if slot.reuse_of_asset:
        return "reused_material"
    if slot.quality_tier == "F_emergency":
        return "emergency_fallback_not_the_stated_subject"
    limitations = list(
        readiness.limitations
        if readiness is not None
        else slot.usability.limitations
    )
    if limitations:
        return ";".join(limitations)
    return "not_publish_ready"


def _recommended_material_for(entry: dict[str, Any]) -> str:
    brief = entry.get("visual_brief") if isinstance(entry.get("visual_brief"), dict) else {}
    return " ".join(
        value
        for value in (
            str(brief.get("subject") or ""),
            str(brief.get("action") or ""),
            str(brief.get("place") or brief.get("location") or ""),
        )
        if value
    ).strip()


def _sources_for(entry: dict[str, Any]) -> list[str]:
    media_type = str(entry.get("visual_type") or "")
    return list(RECOMMENDED_SOURCES_IMAGE if media_type in {"image", "animated_image", "diagram"} else RECOMMENDED_SOURCES_VIDEO)


def _replace_command(project_id: str, scene_id: str, slot_id: str) -> str:
    return (
        "./venv/Scripts/python.exe -m ai_youtube assets replace "
        f"--project-id {project_id or '<project_id>'} --scene-id {scene_id} "
        f"--slot-id {slot_id or '<slot_id>'} --file <path> --confirm-user-owned"
    )


def _narration_for(script: dict[str, Any], scene_id: str) -> str:
    for scene in script.get("scenes") or []:
        if isinstance(scene, dict) and str(scene.get("scene_id") or "") == scene_id:
            return str(scene.get("narration") or scene.get("narration_text") or "")
    return ""


def write_replacement_report(project_root: str | Path, report: dict[str, Any]) -> dict[str, str]:
    """Write all four artefacts. Returns the paths, keyed by artefact."""
    root = Path(project_root) / "replacement"
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "replacement_report.json"
    html_path = root / "replacement_report.html"
    queue_path = root / "replacement_queue.json"
    csv_path = root / "timeline_replacement_map.csv"

    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    queue_path.write_text(
        json.dumps(
            {
                "project_id": report.get("project_id", ""),
                "generated_from": str(json_path),
                "items": [
                    {
                        key: fragment[key]
                        for key in (
                            "scene_id", "slot_id", "start_timecode", "end_timecode",
                            "replacement_priority", "block_reasons", "why_weak",
                            "recommended_material", "search_queries",
                            "english_search_queries", "recommended_sources", "replace_command",
                            "manual_replacement_instructions",
                        )
                        if key in fragment
                    }
                    for fragment in report.get("fragments") or []
                    if fragment.get("replacement_priority") != PRIORITY_NONE
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["start_timecode", "end_timecode", "scene_id", "slot_id", "quality_tier",
             "support_status", "replacement_priority", "used_file"]
        )
        for fragment in report.get("fragments") or []:
            writer.writerow(
                [
                    fragment.get("start_timecode", ""), fragment.get("end_timecode", ""),
                    fragment.get("scene_id", ""), fragment.get("slot_id", ""),
                    fragment.get("quality_tier", ""), fragment.get("support_status", ""),
                    fragment.get("replacement_priority", ""), fragment.get("used_file", ""),
                ]
            )
    html_path.write_text(render_report_html(report), encoding="utf-8")
    return {
        "json_path": str(json_path),
        "html_path": str(html_path),
        "queue_path": str(queue_path),
        "csv_path": str(csv_path),
    }


def render_report_html(report: dict[str, Any]) -> str:
    """Self-contained HTML. No external stylesheet, script, font or image."""
    summary = report.get("summary") or {}
    rows: list[str] = []
    for fragment in report.get("fragments") or []:
        queries = "<br>".join(html.escape(query) for query in (fragment.get("search_queries") or [])[:4])
        limitation = html.escape(str(fragment.get("what_is_missing") or "-"))
        for code, text in _LIMITATION_TEXT.items():
            limitation = limitation.replace(code, text)
        rows.append(
            "<tr class='p-{priority}'>"
            "<td class='mono'>{start}–{end}</td>"
            "<td>{scene}<br><span class='muted mono'>{slot}</span></td>"
            "<td>{narration}</td>"
            "<td>{shows}<br><span class='muted'>{provider} · {license}</span>"
            "<br><span class='mono muted'>{source}</span>"
            "<br><span class='mono muted'>{file}</span></td>"
            "<td>{missing}</td>"
            "<td><span class='tier'>{tier}</span><br><span class='muted'>{support}</span></td>"
            "<td class='prio'>{priority}</td>"
            "<td>{recommended}<br><span class='mono muted'>{queries}</span>"
            "<br><span class='mono muted'>{replace}</span></td>"
            "</tr>".format(
                priority=html.escape(str(fragment.get("replacement_priority") or "")),
                start=html.escape(str(fragment.get("start_timecode") or "")),
                end=html.escape(str(fragment.get("end_timecode") or "")),
                scene=html.escape(str(fragment.get("scene_id") or "")),
                slot=html.escape(str(fragment.get("slot_id") or "")),
                narration=html.escape(str(fragment.get("narration") or "")),
                shows=html.escape(str(fragment.get("what_it_shows") or "")),
                provider=html.escape(str(fragment.get("provider") or "")),
                license=html.escape(str(fragment.get("license") or "")),
                source=html.escape(str(fragment.get("source_url") or "")),
                file=html.escape(str(fragment.get("used_file") or "")),
                missing=limitation,
                tier=html.escape(str(fragment.get("quality_tier") or "")),
                support=html.escape(str(fragment.get("support_status") or "")),
                recommended=html.escape(str(fragment.get("recommended_material") or "")),
                queries=queries,
                replace=html.escape(str(fragment.get("replace_command") or "")),
            )
        )
    tiers = " · ".join(f"{key}: {value}" for key, value in (summary.get("quality_tiers") or {}).items())
    diffs = "".join(
        "<li><span class='mono'>{scene}</span>: <del>{original}</del> → <ins>{adapted}</ins></li>".format(
            scene=html.escape(str(item.get("scene_id") or "")),
            original=html.escape(str(item.get("original") or "")),
            adapted=html.escape(str(item.get("adapted") or "")),
        )
        for item in (summary.get("script_diff") or [])
        if isinstance(item, dict)
    )
    return _HTML_TEMPLATE.format(
        project_id=html.escape(str(report.get("project_id") or "")),
        mode=html.escape(str(report.get("completion_mode") or "")),
        scene_count=summary.get("scene_count", 0),
        draft=summary.get("scenes_usable_in_draft", 0),
        publish=summary.get("scenes_publish_ready", 0),
        improve=summary.get("scenes_needing_improvement", 0),
        weak=summary.get("weak_fragment_count", 0),
        tiers=html.escape(tiers) or "-",
        adapted=html.escape(", ".join(summary.get("adapted_scenes") or [])) or "-",
        reused=html.escape(", ".join((summary.get("reused_assets") or {}).keys())) or "-",
        script_diff=diffs or "<li>Адаптация текста не применялась.</li>",
        rows="\n".join(rows) or "<tr><td colspan='8'>Слабых фрагментов нет.</td></tr>",
        output=html.escape(str((report.get("render") or {}).get("output_path") or "")),
    )


_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ru"><head><meta charset="utf-8">
<title>Замена материалов — {project_id}</title>
<style>
 body{{font-family:system-ui,Segoe UI,Arial,sans-serif;margin:24px;background:#0f1720;color:#e8eef3}}
 h1{{font-size:20px;margin:0 0 4px}} .muted{{color:#8fa3b0}} .mono{{font-family:Consolas,monospace;font-size:12px}}
 table{{border-collapse:collapse;width:100%;margin-top:16px}}
 th,td{{border-bottom:1px solid #24323d;padding:8px;text-align:left;vertical-align:top;font-size:13px}}
 th{{color:#8fa3b0;font-weight:600;font-size:12px;text-transform:uppercase}}
 .tier{{font-family:Consolas,monospace;background:#1b2a35;padding:2px 6px;border-radius:4px}}
 .prio{{font-weight:700}}
 tr.p-critical .prio{{color:#ff6b6b}} tr.p-high .prio{{color:#ffa94d}}
 tr.p-medium .prio{{color:#ffd43b}} tr.p-low .prio{{color:#8fa3b0}}
 .cards{{display:flex;gap:12px;flex-wrap:wrap;margin-top:12px}}
 .card{{background:#16222c;border-radius:8px;padding:10px 14px;min-width:120px}}
 .card b{{display:block;font-size:22px}}
</style></head><body>
<h1>Замена материалов — {project_id}</h1>
<div class="muted">режим завершения: {mode} · черновик: {output}</div>
<div class="cards">
 <div class="card"><b>{scene_count}</b><span class="muted">сцен</span></div>
 <div class="card"><b>{draft}</b><span class="muted">годны в черновик</span></div>
 <div class="card"><b>{publish}</b><span class="muted">готовы к публикации</span></div>
 <div class="card"><b>{improve}</b><span class="muted">требуют улучшения</span></div>
 <div class="card"><b>{weak}</b><span class="muted">слабых фрагментов</span></div>
</div>
<p class="muted">уровни качества: {tiers}<br>адаптированные сцены: {adapted}<br>повторно использованные материалы: {reused}</p>
<details><summary>Изменения текста</summary><ul>{script_diff}</ul></details>
<table><thead><tr>
<th>таймкод</th><th>сцена / слот</th><th>закадровый текст</th><th>что использовано</th>
<th>чего не хватает</th><th>уровень</th><th>приоритет</th><th>чем заменить</th>
</tr></thead><tbody>
{rows}
</tbody></table>
</body></html>
"""


__all__ = [
    "RECOMMENDED_SOURCES_IMAGE",
    "RECOMMENDED_SOURCES_VIDEO",
    "REPLACEMENT_REPORT_SCHEMA_VERSION",
    "build_replacement_report",
    "english_search_queries_for",
    "render_report_html",
    "scene_start_times",
    "search_queries_for",
    "timecode",
    "write_replacement_report",
]
