"""One scene, several visual slots, laid out on the scene's own timeline.

Before this, a scene had exactly one file: ``selected_asset``. That is why a scene
whose narration names both a place and an action could only ever be half answered - a
picture of the Dry Valleys does not show anyone taking a soil sample, and a close-up of
a soil sample does not show Antarctica. Neither is a full match on its own, and there
was nowhere to put both.

A ``SceneVisualAssembly`` is that place. It is deliberately small: a list of
``VisualSlot`` records that partition the scene's duration, each with the material that
fills it and the same explainable verdict every asset already carries.

Compatibility
-------------
This is additive. ``assembly_from_selected_asset`` reads any pre-Q2.2B scene entry as a
one-slot assembly, so an old ``assets_manifest.json`` needs no migration and the
renderer's single-asset path stays exactly as it was.

Timing
------
Slot offsets are relative to the start of the scene and always cover it exactly, so the
assembly can be laid onto whatever the *existing* timeline says the scene is
(``src.audio.scene_timeline``). This module owns no timeline of its own and never
decides how long a scene is.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from src.assets.semantic_selection.decision import read_decision

from .modes import (
    PRIORITY_CRITICAL,
    PRIORITY_NONE,
    PRIORITY_RANK,
    TIER_NONE,
    TIER_RANK,
    UsabilityVerdict,
)

ASSEMBLY_SCHEMA_VERSION = 1
ASSEMBLY_KEY = "visual_assembly"

# --- Slot purposes -----------------------------------------------------------
# Deliberately few. Every one of these has a consumer: the ladder chooses one when it
# fills a slot, and the replacement report prints it. Do not add a purpose without both.
SLOT_PRIMARY = "primary_visual"
SLOT_SUPPORTING = "supporting_broll"
SLOT_ESTABLISHING = "location_establishing"
SLOT_DETAIL = "detail"
SLOT_INFOGRAPHIC = "infographic"
SLOT_MAP = "map"
SLOT_OVERLAY = "scientific_overlay"
SLOT_FALLBACK = "fallback_background"

SLOT_PURPOSES = (
    SLOT_PRIMARY,
    SLOT_SUPPORTING,
    SLOT_ESTABLISHING,
    SLOT_DETAIL,
    SLOT_INFOGRAPHIC,
    SLOT_MAP,
    SLOT_OVERLAY,
    SLOT_FALLBACK,
)

# --- Assembly statuses -------------------------------------------------------
ASSEMBLY_EXACT = "exact"
ASSEMBLY_COMPOSITE = "composite"
ASSEMBLY_PARTIAL = "partial"
ASSEMBLY_FALLBACK = "fallback"
ASSEMBLY_UNRESOLVED = "unresolved"

# A vertical short is 20-70 seconds long. More than four cuts inside one narration scene
# stops reading as one thought, and fewer than ~1.2s of screen time is a flash, not a
# shot. Both bounds are product limits, not technical ones.
MAX_SLOTS_PER_SCENE = 4
MIN_SLOT_DURATION_SEC = 1.2
# Slot offsets are written rounded to milliseconds; comparisons must tolerate that.
TIMELINE_TOLERANCE_SEC = 0.005


@dataclass
class VisualSlot:
    """One stretch of one scene, and the material that fills it."""

    slot_id: str
    purpose: str = SLOT_PRIMARY
    start_offset_sec: float = 0.0
    end_offset_sec: float = 0.0
    required_subject: str = ""
    required_action: str = ""
    required_location: str = ""
    media_types: list[str] = field(default_factory=list)
    selected_asset: dict[str, Any] = field(default_factory=dict)
    fallback_asset: dict[str, Any] = field(default_factory=dict)
    support_status: str = ""
    quality_tier: str = TIER_NONE
    usability: UsabilityVerdict = field(default_factory=UsabilityVerdict)
    provenance: dict[str, Any] = field(default_factory=dict)
    rights: dict[str, Any] = field(default_factory=dict)
    crop_decision: dict[str, Any] = field(default_factory=dict)
    replacement_priority: str = PRIORITY_NONE
    reuse_of_asset: str = ""
    reuse_reason: str = ""
    ladder_level: str = ""
    notes: list[str] = field(default_factory=list)

    @property
    def duration_sec(self) -> float:
        return max(0.0, self.end_offset_sec - self.start_offset_sec)

    @property
    def asset_id(self) -> str:
        return str(self.selected_asset.get("asset_id") or "")

    @property
    def media_path(self) -> str:
        for key in ("path", "local_path", "downloaded_path"):
            value = self.selected_asset.get(key)
            if value:
                return str(value)
        return ""

    @property
    def usable_in_draft(self) -> bool:
        return bool(self.usability.usable_in_draft) and bool(self.selected_asset)

    @property
    def publish_ready(self) -> bool:
        return bool(self.usability.publish_ready) and bool(self.selected_asset)

    def to_dict(self) -> dict[str, Any]:
        return {
            "slot_id": self.slot_id,
            "purpose": self.purpose,
            "start_offset_sec": round(float(self.start_offset_sec), 3),
            "end_offset_sec": round(float(self.end_offset_sec), 3),
            "duration_sec": round(self.duration_sec, 3),
            "required_subject": self.required_subject,
            "required_action": self.required_action,
            "required_location": self.required_location,
            "media_types": list(self.media_types),
            "selected_asset": dict(self.selected_asset),
            "fallback_asset": dict(self.fallback_asset),
            "support_status": self.support_status,
            "quality_tier": self.quality_tier,
            "usability": self.usability.to_dict(),
            "provenance": dict(self.provenance),
            "rights": dict(self.rights),
            "crop_decision": dict(self.crop_decision),
            "replacement_priority": self.replacement_priority,
            "reuse_of_asset": self.reuse_of_asset,
            "reuse_reason": self.reuse_reason,
            "ladder_level": self.ladder_level,
            "notes": list(self.notes),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "VisualSlot":
        data = data if isinstance(data, dict) else {}
        return cls(
            slot_id=str(data.get("slot_id") or "slot_001"),
            purpose=str(data.get("purpose") or SLOT_PRIMARY),
            start_offset_sec=_float(data.get("start_offset_sec")),
            end_offset_sec=_float(data.get("end_offset_sec")),
            required_subject=str(data.get("required_subject") or ""),
            required_action=str(data.get("required_action") or ""),
            required_location=str(data.get("required_location") or ""),
            media_types=[str(item) for item in (data.get("media_types") or [])],
            selected_asset=dict(data.get("selected_asset") or {}),
            fallback_asset=dict(data.get("fallback_asset") or {}),
            support_status=str(data.get("support_status") or ""),
            quality_tier=str(data.get("quality_tier") or TIER_NONE),
            usability=UsabilityVerdict.from_dict(data.get("usability")),
            provenance=dict(data.get("provenance") or {}),
            rights=dict(data.get("rights") or {}),
            crop_decision=dict(data.get("crop_decision") or {}),
            replacement_priority=str(data.get("replacement_priority") or PRIORITY_NONE),
            reuse_of_asset=str(data.get("reuse_of_asset") or ""),
            reuse_reason=str(data.get("reuse_reason") or ""),
            ladder_level=str(data.get("ladder_level") or ""),
            notes=[str(item) for item in (data.get("notes") or [])],
        )


@dataclass
class SceneVisualAssembly:
    """Every slot of one scene, plus what the author still ought to look at."""

    scene_id: str
    scene_duration_sec: float = 0.0
    assembly_status: str = ASSEMBLY_UNRESOLVED
    support_status: str = ""
    completion_mode: str = ""
    slots: list[VisualSlot] = field(default_factory=list)
    replacement_recommendations: list[dict[str, Any]] = field(default_factory=list)
    ladder_trace: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    schema_version: int = ASSEMBLY_SCHEMA_VERSION

    @property
    def usable_slots(self) -> list[VisualSlot]:
        return [slot for slot in self.slots if slot.usable_in_draft]

    @property
    def usable_in_draft(self) -> bool:
        """A scene is draft-usable when its slots cover it with usable material."""
        return bool(self.slots) and not self.validate() and all(slot.usable_in_draft for slot in self.slots)

    @property
    def publish_ready(self) -> bool:
        return bool(self.slots) and not self.validate() and all(slot.publish_ready for slot in self.slots)

    @property
    def quality_tier(self) -> str:
        """The scene is only as good as its weakest slot."""
        if not self.slots:
            return TIER_NONE
        return max((slot.quality_tier for slot in self.slots), key=lambda tier: TIER_RANK.get(tier, 99))

    @property
    def replacement_priority(self) -> str:
        if not self.slots:
            return PRIORITY_CRITICAL
        return min(
            (slot.replacement_priority for slot in self.slots),
            key=lambda value: PRIORITY_RANK.get(value, 99),
        )

    @property
    def primary_asset(self) -> dict[str, Any]:
        """The scene's headline material, for readers that still expect exactly one."""
        for slot in self.slots:
            if slot.purpose == SLOT_PRIMARY and slot.selected_asset:
                return dict(slot.selected_asset)
        return dict(self.slots[0].selected_asset) if self.slots else {}

    def slot(self, slot_id: str) -> VisualSlot | None:
        return next((item for item in self.slots if item.slot_id == slot_id), None)

    def validate(self) -> list[str]:
        """Machine-readable problems with the slot timeline. Empty means it is sound."""
        problems: list[str] = []
        if not self.slots:
            problems.append("assembly_has_no_slots")
            return problems
        if len(self.slots) > MAX_SLOTS_PER_SCENE:
            problems.append(f"too_many_slots:{len(self.slots)}")
        duration_raw = _finite_float(self.scene_duration_sec)
        if duration_raw is None or duration_raw < 0:
            problems.append("scene_duration_invalid")
            duration = 0.0
        else:
            duration = round(duration_raw, 3)

        seen_slot_ids: set[str] = set()
        valid_slots: list[tuple[VisualSlot, float, float]] = []
        for slot in self.slots:
            if not slot.slot_id:
                problems.append("slot_id_missing")
            elif slot.slot_id in seen_slot_ids:
                problems.append(f"duplicate_slot_id:{slot.slot_id}")
            seen_slot_ids.add(slot.slot_id)
            if slot.purpose not in SLOT_PURPOSES:
                problems.append(f"unknown_slot_purpose:{slot.slot_id}:{slot.purpose}")
            start_value = _finite_float(slot.start_offset_sec)
            end_value = _finite_float(slot.end_offset_sec)
            if start_value is None or end_value is None:
                problems.append(f"slot_time_not_finite:{slot.slot_id}")
                continue
            valid_slots.append((slot, start_value, end_value))

        cursor = 0.0
        for slot, raw_start, raw_end in sorted(
            valid_slots, key=lambda item: (item[1], item[2], item[0].slot_id)
        ):
            start = round(raw_start, 3)
            end = round(raw_end, 3)
            if end <= start:
                problems.append(f"slot_not_forward:{slot.slot_id}")
            elif (
                len(self.slots) > 1
                and (raw_end - raw_start) < MIN_SLOT_DURATION_SEC - TIMELINE_TOLERANCE_SEC
            ):
                problems.append(
                    f"slot_too_short:{slot.slot_id}:{raw_end - raw_start:.3f}"
                )
            if start < -TIMELINE_TOLERANCE_SEC or (duration > 0 and end > duration + TIMELINE_TOLERANCE_SEC):
                problems.append(f"slot_outside_scene:{slot.slot_id}")
            if start < cursor - TIMELINE_TOLERANCE_SEC:
                problems.append(f"slot_overlap:{slot.slot_id}")
            elif start > cursor + TIMELINE_TOLERANCE_SEC:
                problems.append(f"slot_gap_before:{slot.slot_id}")
            cursor = max(cursor, end)
        if duration > 0 and abs(cursor - duration) > TIMELINE_TOLERANCE_SEC:
            problems.append(f"slots_do_not_cover_scene:{cursor:.3f}/{duration:.3f}")
        return list(dict.fromkeys(problems))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "scene_id": self.scene_id,
            "scene_duration_sec": round(float(self.scene_duration_sec), 3),
            "assembly_status": self.assembly_status,
            "support_status": self.support_status,
            "completion_mode": self.completion_mode,
            "quality_tier": self.quality_tier,
            "usable_in_draft": self.usable_in_draft,
            "publish_ready": self.publish_ready,
            "replacement_priority": self.replacement_priority,
            "slot_count": len(self.slots),
            "slots": [slot.to_dict() for slot in self.slots],
            "replacement_recommendations": [dict(item) for item in self.replacement_recommendations],
            "ladder_trace": list(self.ladder_trace),
            "warnings": list(self.warnings),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "SceneVisualAssembly":
        data = data if isinstance(data, dict) else {}
        return cls(
            scene_id=str(data.get("scene_id") or ""),
            scene_duration_sec=_float(data.get("scene_duration_sec")),
            assembly_status=str(data.get("assembly_status") or ASSEMBLY_UNRESOLVED),
            support_status=str(data.get("support_status") or ""),
            completion_mode=str(data.get("completion_mode") or ""),
            slots=[VisualSlot.from_dict(item) for item in (data.get("slots") or [])],
            replacement_recommendations=[dict(item) for item in (data.get("replacement_recommendations") or [])],
            ladder_trace=[str(item) for item in (data.get("ladder_trace") or [])],
            warnings=[str(item) for item in (data.get("warnings") or [])],
            schema_version=int(data.get("schema_version") or ASSEMBLY_SCHEMA_VERSION),
        )


def slot_windows(count: int, scene_duration_sec: float) -> list[tuple[float, float]]:
    """Split a scene into ``count`` contiguous windows that cover it exactly.

    Equal shares, with the last window absorbing the rounding, so the slots always end
    precisely where the scene does. ``count`` is clamped so a slot can never be shorter
    than a shot.
    """
    duration = max(0.0, float(scene_duration_sec or 0.0))
    usable = max(1, int(count or 1))
    if duration > 0:
        usable = min(usable, max(1, int(duration // MIN_SLOT_DURATION_SEC)))
    usable = min(usable, MAX_SLOTS_PER_SCENE)
    if duration <= 0:
        return [(0.0, 0.0) for _ in range(usable)]
    share = duration / usable
    windows: list[tuple[float, float]] = []
    cursor = 0.0
    for index in range(usable):
        end = duration if index == usable - 1 else round(cursor + share, 3)
        windows.append((round(cursor, 3), round(end, 3)))
        cursor = end
    return windows


def scaled_slot_windows(
    assembly: SceneVisualAssembly,
    target_duration_sec: float,
) -> list[tuple[VisualSlot, float, float]]:
    """Preserve stored slot boundaries while fitting the real narration duration.

    Assemblies are normally planned before TTS, so their offsets describe proportions
    of the planned scene.  The renderer receives the real duration later.  Re-splitting
    the scene into equal windows loses deliberate 25/75 or 20/30/50 cuts and can even
    silently drop slots when ``slot_windows`` clamps the requested count.  Scaling the
    stored boundaries retains the edit decision and still ends exactly on narration.
    """

    target = _finite_float(target_duration_sec)
    if target is None or target <= 0:
        raise ValueError("target_duration_must_be_positive")

    problems = assembly.validate()
    if problems:
        raise ValueError("invalid_visual_assembly:" + ",".join(problems))

    ordered = sorted(
        assembly.slots,
        key=lambda item: (item.start_offset_sec, item.end_offset_sec, item.slot_id),
    )
    source_duration = _finite_float(assembly.scene_duration_sec) or 0.0
    if source_duration <= 0:
        source_duration = max(float(slot.end_offset_sec) for slot in ordered)
    if source_duration <= 0:
        if len(ordered) == 1:
            return [(ordered[0], 0.0, round(target, 3))]
        raise ValueError("visual_assembly_has_no_source_duration")

    scale = target / source_duration
    result: list[tuple[VisualSlot, float, float]] = []
    for index, slot in enumerate(ordered):
        start = 0.0 if index == 0 else round(float(slot.start_offset_sec) * scale, 3)
        end = (
            round(target, 3)
            if index == len(ordered) - 1
            else round(float(slot.end_offset_sec) * scale, 3)
        )
        if end <= start:
            raise ValueError(f"scaled_slot_not_forward:{slot.slot_id}")
        result.append((slot, start, end))
    return result


def max_slots_for(scene_duration_sec: float) -> int:
    """How many slots this scene's own length can carry."""
    duration = max(0.0, float(scene_duration_sec or 0.0))
    if duration <= 0:
        return 1
    return max(1, min(MAX_SLOTS_PER_SCENE, int(duration // MIN_SLOT_DURATION_SEC)))


def slot_from_asset(
    asset: dict[str, Any],
    *,
    slot_id: str,
    purpose: str,
    start_offset_sec: float,
    end_offset_sec: float,
    quality_tier: str,
    usability: UsabilityVerdict,
    required_subject: str = "",
    required_action: str = "",
    required_location: str = "",
    ladder_level: str = "",
    reuse_of_asset: str = "",
    reuse_reason: str = "",
    notes: list[str] | None = None,
) -> VisualSlot:
    """Build a slot around one asset, copying the records it already carries."""
    decision = read_decision(asset)
    media_type = str(asset.get("media_type") or asset.get("type") or "")
    return VisualSlot(
        slot_id=slot_id,
        purpose=purpose,
        start_offset_sec=start_offset_sec,
        end_offset_sec=end_offset_sec,
        required_subject=required_subject,
        required_action=required_action,
        required_location=required_location,
        media_types=[media_type] if media_type else [],
        selected_asset=dict(asset),
        support_status=decision.support_status or str(asset.get("support_status") or ""),
        quality_tier=quality_tier,
        usability=usability,
        provenance=dict(asset.get("provenance") or {}),
        rights={
            "status": str(asset.get("rights_status") or decision.rights_status or ""),
            "allowed_for_render": bool(asset.get("allowed_for_render", decision.rights_allowed_for_render)),
            "review_required": bool(asset.get("review_required", decision.rights_review_required)),
            "license": asset.get("license") if isinstance(asset.get("license"), dict) else {},
            "license_name": str(asset.get("license_name") or ""),
        },
        crop_decision=dict(decision.framing or asset.get("framing_check") or {}),
        replacement_priority=usability.replacement_priority,
        reuse_of_asset=reuse_of_asset,
        reuse_reason=reuse_reason,
        ladder_level=ladder_level,
        notes=list(notes or []),
    )


def assembly_from_selected_asset(
    scene_entry: dict[str, Any],
    *,
    scene_duration_sec: float = 0.0,
    completion_mode: str = "",
) -> SceneVisualAssembly:
    """Read a pre-Q2.2B scene entry as a one-slot assembly.

    This is the whole compatibility story for old manifests: they carry exactly one
    ``selected_asset`` and no assembly, and every reader written for slots sees a
    single primary slot spanning the scene. Nothing is migrated on disk.
    """
    from .modes import evaluate_usability, TIER_EXACT, TIER_PARTIAL

    selected = scene_entry.get("selected_asset") if isinstance(scene_entry.get("selected_asset"), dict) else {}
    scene_id = str(scene_entry.get("scene_id") or "")
    duration = float(scene_duration_sec or scene_entry.get("required_duration_sec") or 0.0)
    if not selected:
        return SceneVisualAssembly(
            scene_id=scene_id,
            scene_duration_sec=duration,
            assembly_status=ASSEMBLY_UNRESOLVED,
            completion_mode=completion_mode,
            warnings=["legacy_scene_had_no_selected_asset"],
        )
    decision = read_decision(selected)
    tier = TIER_EXACT if decision.render_ready else TIER_PARTIAL
    usability = evaluate_usability(selected, mode=completion_mode or "strict", quality_tier=tier)
    slot = slot_from_asset(
        selected,
        slot_id=f"{scene_id or 'scene'}_slot_001",
        purpose=SLOT_PRIMARY,
        start_offset_sec=0.0,
        end_offset_sec=duration,
        quality_tier=tier,
        usability=usability,
        ladder_level="legacy_single_asset",
    )
    return SceneVisualAssembly(
        scene_id=scene_id,
        scene_duration_sec=duration,
        assembly_status=ASSEMBLY_EXACT if decision.render_ready else ASSEMBLY_PARTIAL,
        support_status=decision.support_status,
        completion_mode=completion_mode,
        slots=[slot],
        ladder_trace=["read_from_legacy_selected_asset"],
    )


def read_assembly(scene_entry: dict[str, Any] | None, *, scene_duration_sec: float = 0.0) -> SceneVisualAssembly:
    """The assembly of one manifest scene, whichever generation wrote it."""
    entry = scene_entry if isinstance(scene_entry, dict) else {}
    stored = entry.get(ASSEMBLY_KEY)
    # Once an assembly exists it is authoritative, including an explicit unresolved
    # assembly with no slots. Falling back to a stale compatibility ``selected_asset``
    # in that case would resurrect material the completion pass deliberately refused.
    if isinstance(stored, dict):
        assembly = SceneVisualAssembly.from_dict(stored)
        if scene_duration_sec and not assembly.scene_duration_sec:
            assembly.scene_duration_sec = float(scene_duration_sec)
        return assembly
    return assembly_from_selected_asset(entry, scene_duration_sec=scene_duration_sec)


def attach_assembly(scene_entry: dict[str, Any], assembly: SceneVisualAssembly) -> dict[str, Any]:
    """Write the assembly onto a manifest scene, keeping ``selected_asset`` in step.

    ``selected_asset`` stays the primary slot's material so that every existing reader -
    quality check, rights report, review board, the renderer's single-asset path -
    keeps working without being taught about slots.
    """
    scene_entry[ASSEMBLY_KEY] = assembly.to_dict()
    primary = assembly.primary_asset
    if primary:
        scene_entry["selected_asset"] = primary
        decision = read_decision(primary)
        if decision.support_status:
            scene_entry["support_status"] = decision.support_status
            scene_entry["support_requirements"] = list(decision.support_requirements)
    return scene_entry


def _float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _finite_float(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return parsed if math.isfinite(parsed) else None


__all__ = [
    "ASSEMBLY_COMPOSITE",
    "ASSEMBLY_EXACT",
    "ASSEMBLY_FALLBACK",
    "ASSEMBLY_KEY",
    "ASSEMBLY_PARTIAL",
    "ASSEMBLY_SCHEMA_VERSION",
    "ASSEMBLY_UNRESOLVED",
    "MAX_SLOTS_PER_SCENE",
    "MIN_SLOT_DURATION_SEC",
    "SLOT_DETAIL",
    "SLOT_ESTABLISHING",
    "SLOT_FALLBACK",
    "SLOT_INFOGRAPHIC",
    "SLOT_MAP",
    "SLOT_OVERLAY",
    "SLOT_PRIMARY",
    "SLOT_PURPOSES",
    "SLOT_SUPPORTING",
    "SceneVisualAssembly",
    "VisualSlot",
    "assembly_from_selected_asset",
    "attach_assembly",
    "max_slots_for",
    "read_assembly",
    "scaled_slot_windows",
    "slot_from_asset",
    "slot_windows",
]
