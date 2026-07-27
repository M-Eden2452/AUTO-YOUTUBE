from __future__ import annotations

from pathlib import Path
from typing import Any

from src.assets.license_policy import evaluate_asset_policy


def run_quality_check(
    *,
    script: dict[str, Any],
    research: dict[str, Any],
    assets_manifest: dict[str, Any],
    voice_manifest: dict[str, Any] | None,
    subtitles_manifest: dict[str, Any] | None,
) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    checks: list[dict[str, str]] = []

    duration = float(script.get("estimated_duration_sec") or 0)
    if 35 <= duration <= 70:
        checks.append({"check": "duration", "message": f"Duration is in range: {duration:.1f}s."})
    else:
        warnings.append({"check": "duration", "message": f"Duration needs review: {duration:.1f}s."})

    scenes = script.get("scenes", [])
    if scenes and all(scene.get("narration") for scene in scenes):
        checks.append({"check": "non_empty_scenes", "message": "All script scenes contain narration."})
    else:
        errors.append({"check": "non_empty_scenes", "message": "One or more scenes are empty."})

    unsafe_claims = [claim for claim in research.get("claims", []) if not claim.get("safe_for_script", True)]
    if unsafe_claims:
        errors.append({"check": "claims", "message": f"Unsafe claims found: {len(unsafe_claims)}."})
    else:
        checks.append({"check": "claims", "message": "No unsafe claims are marked for script use."})

    if int(assets_manifest.get("schema_version") or 0) >= 1:
        _check_schema_v1_assets(assets_manifest, errors, warnings, checks)
    else:
        _check_legacy_assets(assets_manifest, errors, warnings, checks)

    if not voice_manifest or voice_manifest.get("status") != "completed":
        warnings.append({"check": "voice", "message": "Voice stage requires draft audio or approved final voice."})
    else:
        checks.append({"check": "voice", "message": "Voice manifest is completed."})

    if subtitles_manifest and subtitles_manifest.get("srt_path") and subtitles_manifest.get("ass_path"):
        checks.append({"check": "subtitles", "message": "SRT and ASS subtitles were created."})
    else:
        warnings.append({"check": "subtitles", "message": "Subtitles are missing."})

    status = "failed" if errors else "needs_review" if warnings else "passed"
    return {"status": status, "errors": errors, "warnings": warnings, "checks": checks}


def _check_schema_v1_assets(
    assets_manifest: dict[str, Any],
    errors: list[dict[str, str]],
    warnings: list[dict[str, str]],
    checks: list[dict[str, str]],
) -> None:
    missing_assets = assets_manifest.get("missing_scenes", [])
    scenes = assets_manifest.get("scenes", [])
    selected_count = 0
    for scene in scenes:
        scene_id = str(scene.get("scene_id", ""))
        selected = scene.get("selected_asset") or {}
        if not selected:
            errors.append({"check": "asset_coverage", "message": f"Scene {scene_id} has no selected asset."})
            continue
        selected_count += 1
        if not selected.get("allowed_for_render") or selected.get("review_required"):
            errors.append({"check": "asset_rights", "message": f"Scene {scene_id} selected asset is not cleared for render."})
        policy_decision = evaluate_asset_policy(selected)
        if policy_decision.review_required or not policy_decision.allowed_for_render:
            errors.append(
                {
                    "check": "asset_policy",
                    "message": f"Scene {scene_id} selected asset is blocked by license policy: {policy_decision.reason}.",
                }
            )
        license_data = selected.get("license") if isinstance(selected.get("license"), dict) else {}
        if not license_data:
            errors.append({"check": "asset_license", "message": f"Scene {scene_id} selected asset has no license object."})
        elif license_data.get("review_required") or not license_data.get("allowed_for_render"):
            errors.append({"check": "asset_license", "message": f"Scene {scene_id} selected asset license requires review."})
        provenance = selected.get("provenance") if isinstance(selected.get("provenance"), dict) else {}
        if not provenance or not provenance.get("provider") or not provenance.get("source_page_url"):
            errors.append({"check": "asset_provenance", "message": f"Scene {scene_id} selected asset lacks provider/source provenance."})
        local_path = selected.get("path") or selected.get("local_path") or selected.get("downloaded_path")
        if not local_path or not Path(local_path).exists():
            errors.append({"check": "asset_local_file", "message": f"Scene {scene_id} selected asset local file is missing."})
        else:
            checks.append({"check": "asset_local_file", "message": f"Scene {scene_id} has a local renderable file."})
        if not selected.get("checksum_sha256"):
            errors.append({"check": "asset_checksum", "message": f"Scene {scene_id} selected asset has no SHA-256 checksum."})
        validation = selected.get("technical_validation") if isinstance(selected.get("technical_validation"), dict) else {}
        if validation.get("status") != "passed":
            errors.append({"check": "asset_validation", "message": f"Scene {scene_id} selected asset has no passing technical validation."})
        _check_selection_decision(scene_id, selected, errors, warnings, checks)
    if missing_assets:
        warnings.append({"check": "asset_coverage", "message": f"{len(missing_assets)} scene(s) still need approved assets."})
    if selected_count and not any(error["check"].startswith("asset_") for error in errors):
        checks.append({"check": "asset_rights", "message": "All selected assets have local files, license and provenance."})


def _check_selection_decision(
    scene_id: str,
    selected: dict[str, Any],
    errors: list[dict[str, str]],
    warnings: list[dict[str, str]],
    checks: list[dict[str, str]],
) -> None:
    """What the selection decision claims, and whether it is allowed to claim it.

    An asset written before stage Q2.2A-2 carries no decision. It is reported as such
    rather than assumed to be a full match - a manifest that predates the record cannot
    be made to have one retroactively.

    Note on severity: how much of a scene an asset supports is *reported* here, not
    enforced. Turning "this frame shows part of what the narration lists" into a
    blocking error would stop the render stage for most stock footage, which is a
    policy decision about the product and not something this check may make on its own.
    An internally inconsistent record is a different matter: it is a defect in the
    writer, and it fails.
    """
    from src.assets.semantic_selection.decision import has_decision, read_decision, validate_decision

    if not has_decision(selected):
        checks.append(
            {
                "check": "asset_visual_support",
                "message": f"Scene {scene_id} selected asset predates selection decisions; support is unknown.",
            }
        )
        return
    decision = read_decision(selected)
    problems = validate_decision(decision)
    if problems:
        errors.append(
            {
                "check": "asset_visual_support",
                "message": f"Scene {scene_id} selection decision contradicts itself: {', '.join(problems)}.",
            }
        )
        return
    requirements = ", ".join(decision.support_requirements) or "none"
    checks.append(
        {
            "check": "asset_visual_support",
            "message": (
                f"Scene {scene_id} support={decision.support_status} "
                f"slots={decision.slot_verdict} crop={decision.technical_status} "
                f"render_ready={'yes' if decision.render_ready else 'no'} outstanding={requirements}"
            ),
        }
    )


def _check_legacy_assets(
    assets_manifest: dict[str, Any],
    errors: list[dict[str, str]],
    warnings: list[dict[str, str]],
    checks: list[dict[str, str]],
) -> None:
    blocked_assets = []
    missing_assets = assets_manifest.get("missing_scenes", [])
    placeholder_assets = []
    real_videos = []
    for scene in assets_manifest.get("scenes", []):
        selected = scene.get("selected_asset")
        if selected and not selected.get("allowed_for_render"):
            blocked_assets.append(scene.get("scene_id", ""))
        if selected and selected.get("provider") in {"generated_layout", "debug_placeholder"}:
            placeholder_assets.append(scene.get("scene_id", ""))
        if selected and selected.get("type") == "video" and selected.get("downloaded_path"):
            real_videos.append(scene.get("scene_id", ""))
    if blocked_assets:
        errors.append({"check": "asset_rights", "message": f"Blocked assets selected in scenes: {blocked_assets}."})
    elif placeholder_assets:
        errors.append({"check": "asset_placeholders", "message": f"Placeholder/debug assets selected in scenes: {placeholder_assets}."})
    elif missing_assets:
        warnings.append({"check": "asset_coverage", "message": f"{len(missing_assets)} scene(s) still need approved assets."})
    else:
        checks.append({"check": "asset_rights", "message": "All selected assets are allowed for render."})
    if len(real_videos) >= 8:
        checks.append({"check": "real_video_count", "message": f"Real downloaded video clips: {len(real_videos)}."})
    else:
        errors.append({"check": "real_video_count", "message": f"At least 8 real downloaded videos are required; found {len(real_videos)}."})
