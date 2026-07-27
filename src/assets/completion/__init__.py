"""Autonomous draft completion (stage Q2.2B).

Turns "no exact material -> the video cannot be rendered" into "no exact material ->
use a safe fallback, render the draft, and tell the author exactly what is weak".

Four parts, each usable on its own:

``modes``     what "ready" means - draft, automatic, publish - and what blocks material
``assembly``  a scene as several timed visual slots, backwards compatible with one asset
``ladder``    the six-rung fallback ladder, deterministic tie-breaking, reuse control
``report``    the weak-fragment and replacement report

None of these talk to a provider, the network, or a paid service.
"""

from __future__ import annotations

from .assembly import (
    ASSEMBLY_COMPOSITE,
    ASSEMBLY_EXACT,
    ASSEMBLY_FALLBACK,
    ASSEMBLY_KEY,
    ASSEMBLY_PARTIAL,
    ASSEMBLY_UNRESOLVED,
    MAX_SLOTS_PER_SCENE,
    SLOT_DETAIL,
    SLOT_ESTABLISHING,
    SLOT_FALLBACK,
    SLOT_INFOGRAPHIC,
    SLOT_PRIMARY,
    SLOT_SUPPORTING,
    SceneVisualAssembly,
    VisualSlot,
    assembly_from_selected_asset,
    attach_assembly,
    read_assembly,
    slot_windows,
)
from .ladder import (
    ReuseLedger,
    build_scene_assembly,
    order_candidates,
    quality_tier_for,
    reuse_identity,
    tie_break_key,
)
from .modes import (
    BLOCK_FACTUALLY_MISLEADING,
    BLOCK_MISSING_FILE,
    BLOCK_MUST_AVOID,
    BLOCK_RIGHTS,
    BLOCK_TECHNICAL,
    COMPLETION_MODES,
    DEFAULT_COMPLETION_MODE,
    MODE_DRAFT_COMPLETE,
    MODE_STRICT,
    PRIORITY_CRITICAL,
    PRIORITY_HIGH,
    PRIORITY_LOW,
    PRIORITY_MEDIUM,
    PRIORITY_NONE,
    QUALITY_TIERS,
    TIER_COMPOSITE,
    TIER_EMERGENCY,
    TIER_EXACT,
    TIER_GENERATED,
    TIER_GOOD_CONTEXT,
    TIER_PARTIAL,
    UsabilityVerdict,
    blocking_reasons,
    evaluate_usability,
    normalize_mode,
)
from .report import build_replacement_report, write_replacement_report
from .replacement import VisualSlotReplacementError, replace_visual_slot

__all__ = [
    "ASSEMBLY_COMPOSITE",
    "ASSEMBLY_EXACT",
    "ASSEMBLY_FALLBACK",
    "ASSEMBLY_KEY",
    "ASSEMBLY_PARTIAL",
    "ASSEMBLY_UNRESOLVED",
    "BLOCK_FACTUALLY_MISLEADING",
    "BLOCK_MISSING_FILE",
    "BLOCK_MUST_AVOID",
    "BLOCK_RIGHTS",
    "BLOCK_TECHNICAL",
    "COMPLETION_MODES",
    "DEFAULT_COMPLETION_MODE",
    "MAX_SLOTS_PER_SCENE",
    "MODE_DRAFT_COMPLETE",
    "MODE_STRICT",
    "PRIORITY_CRITICAL",
    "PRIORITY_HIGH",
    "PRIORITY_LOW",
    "PRIORITY_MEDIUM",
    "PRIORITY_NONE",
    "QUALITY_TIERS",
    "SLOT_DETAIL",
    "SLOT_ESTABLISHING",
    "SLOT_FALLBACK",
    "SLOT_INFOGRAPHIC",
    "SLOT_PRIMARY",
    "SLOT_SUPPORTING",
    "TIER_COMPOSITE",
    "TIER_EMERGENCY",
    "TIER_EXACT",
    "TIER_GENERATED",
    "TIER_GOOD_CONTEXT",
    "TIER_PARTIAL",
    "ReuseLedger",
    "SceneVisualAssembly",
    "UsabilityVerdict",
    "VisualSlot",
    "VisualSlotReplacementError",
    "assembly_from_selected_asset",
    "attach_assembly",
    "blocking_reasons",
    "build_replacement_report",
    "build_scene_assembly",
    "evaluate_usability",
    "normalize_mode",
    "order_candidates",
    "quality_tier_for",
    "read_assembly",
    "replace_visual_slot",
    "reuse_identity",
    "slot_windows",
    "tie_break_key",
    "write_replacement_report",
]
