from __future__ import annotations

from typing import Any

from src.assets.completion import ReuseLedger, normalize_mode, read_assembly
from src.assets.semantic_selection.candidate_ranker import SUPPORT_RANK
from src.assets.semantic_selection.decision import SUPPORT_FULL, read_decision

# The media-kind vocabulary moved to the selection policy so that coverage
# summaries and the selection decision can never classify one asset differently.
# These names stay importable here for their existing callers.
from src.assets.semantic_selection.media_policy import (
    IMAGE_EXTENSIONS,
    VIDEO_EXTENSIONS,
    candidate_media_kind as slot_media_type,
)

DEFAULT_MIN_VIDEO_CLIPS = 1
DEFAULT_MIN_VIDEO_DURATION_RATIO = 0.4


def visual_support_summary(
    scene_entries: list[dict[str, Any]], missing_scenes: list[dict[str, Any]]
) -> dict[str, Any]:
    """Summarize how many scenes have honest visual support."""

    by_status: dict[str, int] = {}
    requirements: dict[str, int] = {}
    scenes_needing_review: list[str] = []
    for entry in scene_entries:
        assembly = read_assembly(
            entry,
            scene_duration_sec=float(entry.get("required_duration_sec") or 0.0),
        )
        decisions = [
            read_decision(slot.selected_asset)
            for slot in assembly.slots
            if slot.selected_asset
        ]
        statuses = [decision.support_status or "unresolved" for decision in decisions]
        status = (
            min(statuses, key=lambda value: SUPPORT_RANK.get(value, 0))
            if statuses
            else "unresolved"
        )
        by_status[status] = by_status.get(status, 0) + 1
        for decision in decisions:
            for requirement in decision.support_requirements:
                requirements[requirement] = requirements.get(requirement, 0) + 1
        if status != SUPPORT_FULL or not assembly.publish_ready:
            scenes_needing_review.append(str(entry.get("scene_id") or ""))
    return {
        "scene_count": len(scene_entries),
        "full_support": by_status.get(SUPPORT_FULL, 0),
        "resolved": sum(
            1
            for entry in scene_entries
            if read_assembly(
                entry,
                scene_duration_sec=float(entry.get("required_duration_sec") or 0.0),
            ).publish_ready
        ),
        "unresolved": len(missing_scenes),
        "by_support_status": by_status,
        "requirements": requirements,
        "scenes_needing_review": scenes_needing_review,
    }


def video_first_policy(
    *,
    enabled: bool,
    minimum_video_clips: int = DEFAULT_MIN_VIDEO_CLIPS,
    minimum_video_duration_ratio: float = DEFAULT_MIN_VIDEO_DURATION_RATIO,
) -> dict[str, Any]:
    return {
        "enabled": bool(enabled),
        "minimum_video_clips": max(1, int(minimum_video_clips)),
        "minimum_video_duration_ratio": max(
            0.0, min(1.0, float(minimum_video_duration_ratio))
        ),
        "threshold_mode": "all",
        "image_fallback_allowed_in_draft": True,
        "image_fallback_publish_ready": False,
    }


def summarize_media_coverage(
    scene_entries: list[dict[str, Any]],
    *,
    policy: dict[str, Any],
) -> dict[str, Any]:
    """Count selected visual media and enforce the manifest-level video threshold."""

    video_slots = 0
    image_slots = 0
    unknown_slots = 0
    reused_slots = 0
    video_duration = 0.0
    visual_duration = 0.0
    video_asset_ids: set[str] = set()
    image_asset_ids: set[str] = set()
    for entry in scene_entries:
        assembly = read_assembly(
            entry,
            scene_duration_sec=float(entry.get("required_duration_sec") or 0.0),
        )
        visual_duration += max(0.0, float(assembly.scene_duration_sec))
        for slot in assembly.slots:
            asset = slot.selected_asset if isinstance(slot.selected_asset, dict) else {}
            if not asset:
                continue
            duration = max(0.0, float(slot.duration_sec))
            if slot.reuse_of_asset:
                reused_slots += 1
            asset_id = str(asset.get("asset_id") or slot.asset_id or "")
            media_type = slot_media_type(asset)
            if media_type == "video":
                video_slots += 1
                video_duration += duration
                if asset_id:
                    video_asset_ids.add(asset_id)
            elif media_type == "image":
                image_slots += 1
                if asset_id:
                    image_asset_ids.add(asset_id)
            else:
                unknown_slots += 1

    ratio = video_duration / visual_duration if visual_duration > 0.0 else 0.0
    enabled = bool(policy.get("enabled", False))
    minimum_clips = max(1, int(policy.get("minimum_video_clips") or DEFAULT_MIN_VIDEO_CLIPS))
    minimum_ratio = max(
        0.0,
        min(
            1.0,
            float(
                policy.get("minimum_video_duration_ratio")
                if policy.get("minimum_video_duration_ratio") is not None
                else DEFAULT_MIN_VIDEO_DURATION_RATIO
            ),
        ),
    )
    threshold_tolerance = 0.01
    meets_policy = (
        not enabled
        or (
            len(video_asset_ids) >= minimum_clips
            and ratio + threshold_tolerance >= minimum_ratio
        )
    )
    image_only = enabled and image_slots > 0 and video_slots == 0
    review_required = enabled and not meets_policy
    if not enabled:
        status = "not_applicable"
    elif meets_policy:
        status = "meets_policy"
    elif image_only:
        status = "image_only_draft_fallback"
    elif video_slots:
        status = "insufficient_video_coverage"
    else:
        status = "no_selected_video"
    return {
        "status": status,
        "selected_slots": video_slots + image_slots + unknown_slots,
        "video_slots": video_slots,
        "video_clips": len(video_asset_ids),
        "image_slots": image_slots,
        "image_assets": len(image_asset_ids),
        "unknown_slots": unknown_slots,
        "reused_slots": reused_slots,
        "visual_duration_sec": round(visual_duration, 3),
        "video_duration_sec": round(video_duration, 3),
        "video_duration_ratio": round(ratio, 4),
        "image_fallback_used": image_slots > 0,
        "image_only_fallback": image_only,
        "meets_video_first_threshold": meets_policy,
        "review_required": review_required,
        "publish_ready": not review_required,
    }


def apply_video_first_readiness(
    completion: dict[str, Any],
    media_coverage: dict[str, Any],
) -> None:
    review_required = bool(media_coverage.get("review_required", False))
    completion["video_first_review_required"] = review_required
    if review_required:
        completion["publish_ready"] = False


def completion_summary(
    scene_entries: list[dict[str, Any]], *, mode: str, reuse: ReuseLedger
) -> dict[str, Any]:
    """Summarize draft and publish readiness per scene and slot."""

    tiers: dict[str, int] = {}
    statuses: dict[str, int] = {}
    draft_usable: list[str] = []
    publish_ready: list[str] = []
    unresolved: list[str] = []
    slot_count = 0
    timeline_problems: list[str] = []
    for entry in scene_entries:
        assembly = read_assembly(
            entry,
            scene_duration_sec=float(entry.get("required_duration_sec") or 0.0),
        )
        statuses[assembly.assembly_status] = statuses.get(assembly.assembly_status, 0) + 1
        slot_count += len(assembly.slots)
        for slot in assembly.slots:
            tiers[slot.quality_tier] = tiers.get(slot.quality_tier, 0) + 1
        scene_id = str(entry.get("scene_id") or "")
        (draft_usable if assembly.usable_in_draft else unresolved).append(scene_id)
        if assembly.publish_ready:
            publish_ready.append(scene_id)
        timeline_problems.extend(f"{scene_id}:{problem}" for problem in assembly.validate())
    return {
        "mode": mode,
        "scene_count": len(scene_entries),
        "slot_count": slot_count,
        "scenes_usable_in_draft": len(draft_usable),
        "scenes_publish_ready": len(publish_ready),
        "unresolved_scenes": unresolved,
        "quality_tiers": tiers,
        "assembly_statuses": statuses,
        "timeline_problems": timeline_problems,
        "reuse": reuse.to_dict(),
        "draft_complete": bool(scene_entries) and not unresolved and not timeline_problems,
        "publish_ready": bool(scene_entries) and len(publish_ready) == len(scene_entries),
    }


def refresh_manifest_summaries(
    manifest: dict[str, Any],
    *,
    mode: str = "",
    reuse: ReuseLedger | None = None,
) -> dict[str, Any]:
    """Recompute the canonical scene, slot, and coverage summaries in place."""

    scenes = [
        entry for entry in (manifest.get("scenes") or []) if isinstance(entry, dict)
    ]
    missing = [
        entry for entry in (manifest.get("missing_scenes") or []) if isinstance(entry, dict)
    ]
    stored_completion = (
        manifest.get("completion")
        if isinstance(manifest.get("completion"), dict)
        else {}
    )
    ledger = reuse or _reuse_from_summary(stored_completion.get("reuse"))
    resolved_mode = normalize_mode(mode or str(stored_completion.get("mode") or ""))
    manifest["visual_support"] = visual_support_summary(scenes, missing)
    stored_policy = (
        manifest.get("video_first_policy")
        if isinstance(manifest.get("video_first_policy"), dict)
        else {}
    )
    policy = video_first_policy(
        enabled=bool(
            stored_policy.get(
                "enabled",
                str(manifest.get("visual_mode") or "") == "video_first",
            )
        ),
        minimum_video_clips=int(
            stored_policy.get("minimum_video_clips") or DEFAULT_MIN_VIDEO_CLIPS
        ),
        minimum_video_duration_ratio=float(
            stored_policy.get("minimum_video_duration_ratio")
            if stored_policy.get("minimum_video_duration_ratio") is not None
            else DEFAULT_MIN_VIDEO_DURATION_RATIO
        ),
    )
    manifest["video_first_policy"] = policy
    media_coverage = summarize_media_coverage(scenes, policy=policy)
    manifest["media_coverage"] = media_coverage
    completion = completion_summary(
        scenes,
        mode=resolved_mode,
        reuse=ledger,
    )
    apply_video_first_readiness(completion, media_coverage)
    manifest["completion"] = completion
    return manifest


def _reuse_from_summary(value: Any) -> ReuseLedger:
    stored = value if isinstance(value, dict) else {}
    ledger = ReuseLedger(
        max_uses=int(stored.get("max_uses") or ReuseLedger.max_uses),
        min_scene_gap=int(stored.get("min_scene_gap") or ReuseLedger.min_scene_gap),
    )
    ledger.uses = {
        str(asset_id): [int(index) for index in (indexes or [])]
        for asset_id, indexes in (stored.get("uses") or {}).items()
    }
    ledger.scenes = {
        str(asset_id): [str(scene_id) for scene_id in (scene_ids or [])]
        for asset_id, scene_ids in (stored.get("scenes") or {}).items()
    }
    return ledger
