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
    completion_mode: str = "",
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
        _check_schema_v1_assets(
            assets_manifest,
            errors,
            warnings,
            checks,
            completion_mode=completion_mode,
        )
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
    *,
    completion_mode: str = "",
) -> None:
    from src.assets.completion import (
        MODE_DRAFT_COMPLETE,
        assembly_from_selected_asset,
        evaluate_usability,
        normalize_mode,
        read_assembly,
    )
    from src.assets.semantic_selection.decision import has_decision

    mode = normalize_mode(completion_mode)
    missing_assets = assets_manifest.get("missing_scenes", [])
    scenes = assets_manifest.get("scenes", [])
    selected_count = 0
    for scene in scenes:
        scene_id = str(scene.get("scene_id", ""))
        explicit_assembly = isinstance(scene.get("visual_assembly"), dict)
        duration = float(scene.get("required_duration_sec") or 0.0)
        assembly = (
            read_assembly(scene, scene_duration_sec=duration)
            if isinstance(scene.get("visual_assembly"), dict)
            else assembly_from_selected_asset(
                scene,
                scene_duration_sec=duration,
                completion_mode=mode,
            )
        )
        # A pre-Q2.2B selected_asset had no slot timeline at all. Its zero duration
        # cannot become a new validation failure merely because the compatibility
        # reader exposes it as a single slot.
        timeline_problems = assembly.validate() if explicit_assembly else []
        for problem in timeline_problems:
            errors.append(
                {
                    "check": "asset_slot_timeline",
                    "message": f"Scene {scene_id} visual slot timeline is invalid: {problem}.",
                }
            )
        if not assembly.slots:
            errors.append({"check": "asset_coverage", "message": f"Scene {scene_id} has no selected asset."})
            continue
        for slot in assembly.slots:
            selected = slot.selected_asset or {}
            label = f"Scene {scene_id} slot {slot.slot_id}"
            if not selected:
                errors.append({"check": "asset_coverage", "message": f"{label} has no selected asset."})
                continue
            selected_count += 1
            if not selected.get("allowed_for_render") or selected.get("review_required"):
                errors.append({"check": "asset_rights", "message": f"{label} is not cleared for render."})
            policy_decision = evaluate_asset_policy(selected)
            if policy_decision.review_required or not policy_decision.allowed_for_render:
                errors.append(
                    {
                        "check": "asset_policy",
                        "message": f"{label} is blocked by license policy: {policy_decision.reason}.",
                    }
                )
            license_data = selected.get("license") if isinstance(selected.get("license"), dict) else {}
            if not license_data:
                errors.append({"check": "asset_license", "message": f"{label} has no license object."})
            elif license_data.get("review_required") or not license_data.get("allowed_for_render"):
                errors.append({"check": "asset_license", "message": f"{label} license requires review."})
            provenance = selected.get("provenance") if isinstance(selected.get("provenance"), dict) else {}
            if not provenance or not provenance.get("provider") or not provenance.get("source_page_url"):
                errors.append({"check": "asset_provenance", "message": f"{label} lacks provider/source provenance."})
            local_path = selected.get("path") or selected.get("local_path") or selected.get("downloaded_path")
            if not local_path or not Path(local_path).is_file():
                errors.append({"check": "asset_local_file", "message": f"{label} local file is missing."})
            else:
                checks.append({"check": "asset_local_file", "message": f"{label} has a local renderable file."})
            if not selected.get("checksum_sha256"):
                errors.append({"check": "asset_checksum", "message": f"{label} has no SHA-256 checksum."})
            validation = (
                selected.get("technical_validation")
                if isinstance(selected.get("technical_validation"), dict)
                else {}
            )
            if validation.get("status") != "passed":
                errors.append({"check": "asset_validation", "message": f"{label} has no passing technical validation."})
            _check_selection_decision(f"{scene_id}/{slot.slot_id}", selected, errors, warnings, checks)

            # Old manifests had no semantic decision and are grandfathered: their
            # historical strict behaviour remains the rights/technical gate above.
            # Once a decision or assembly exists, strict means publish-ready.
            semantic_contract_present = explicit_assembly or has_decision(selected)
            readiness = evaluate_usability(
                selected,
                mode=mode,
                quality_tier=slot.quality_tier,
                require_local_file=True,
            )
            if mode == MODE_DRAFT_COMPLETE:
                if not readiness.usable_in_draft:
                    errors.append(
                        {"check": "asset_draft_readiness", "message": f"{label} is not usable in a draft."}
                    )
                elif not readiness.publish_ready:
                    warnings.append(
                        {
                            "check": "asset_publish_readiness",
                            "message": f"{label} is draft-only and requires replacement before publication.",
                        }
                    )
            elif semantic_contract_present and not readiness.publish_ready:
                errors.append(
                    {
                        "check": "asset_publish_readiness",
                        "message": f"{label} is not publish-ready in strict mode.",
                    }
                )
    if missing_assets:
        warnings.append({"check": "asset_coverage", "message": f"{len(missing_assets)} scene(s) still need approved assets."})
    if selected_count and not any(error["check"].startswith("asset_") for error in errors):
        checks.append({"check": "asset_rights", "message": "All selected assets have local files, license and provenance."})
    _check_video_first_coverage(
        assets_manifest,
        mode=mode,
        errors=errors,
        warnings=warnings,
        checks=checks,
    )


def _check_video_first_coverage(
    assets_manifest: dict[str, Any],
    *,
    mode: str,
    errors: list[dict[str, str]],
    warnings: list[dict[str, str]],
    checks: list[dict[str, str]],
) -> None:
    from src.assets.completion import MODE_DRAFT_COMPLETE
    from src.news.asset_manager import (
        DEFAULT_MIN_VIDEO_CLIPS,
        DEFAULT_MIN_VIDEO_DURATION_RATIO,
        summarize_media_coverage,
    )

    stored_policy = (
        assets_manifest.get("video_first_policy")
        if isinstance(assets_manifest.get("video_first_policy"), dict)
        else {}
    )
    enabled = bool(
        stored_policy.get(
            "enabled",
            str(assets_manifest.get("visual_mode") or "") == "video_first",
        )
    )
    if not enabled:
        return
    policy = {
        "enabled": True,
        "minimum_video_clips": int(
            stored_policy.get("minimum_video_clips") or DEFAULT_MIN_VIDEO_CLIPS
        ),
        "minimum_video_duration_ratio": float(
            stored_policy.get("minimum_video_duration_ratio")
            if stored_policy.get("minimum_video_duration_ratio") is not None
            else DEFAULT_MIN_VIDEO_DURATION_RATIO
        ),
    }
    scenes = [
        scene
        for scene in (assets_manifest.get("scenes") or [])
        if isinstance(scene, dict)
    ]
    coverage = summarize_media_coverage(scenes, policy=policy)
    message = (
        "Video-first coverage "
        f"has {coverage['video_clips']} video clip(s), "
        f"{coverage['image_slots']} image slot(s), "
        f"{coverage['reused_slots']} reused slot(s), and "
        f"{coverage['video_duration_ratio']:.0%} video duration."
    )
    if coverage["review_required"]:
        message += " The image fallback is review-only and not publish-ready."
        target = warnings if mode == MODE_DRAFT_COMPLETE else errors
        target.append({"check": "video_first_coverage", "message": message})
    else:
        checks.append({"check": "video_first_coverage", "message": message})


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
