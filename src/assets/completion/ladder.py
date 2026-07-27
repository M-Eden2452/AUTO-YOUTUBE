"""The fallback ladder: how a scene gets filled when the perfect frame does not exist.

Six rungs, tried in order, each one a weaker but still honest answer:

``A`` exact           one asset that shows what the scene states
``B`` composite       two to four assets that together show it
``C`` good context    material that belongs to the subject without being the event
``D`` partial         material that shows part of the scene
``E`` generated       a figure the project drew from the scene's own specification
``F`` emergency       a reused frame, or a neutral card that claims nothing at all

The ladder never invents permission. Every rung is filtered through
``modes.blocking_reasons`` first, so material with unknown or forbidden rights, a broken
file, a ``must_avoid`` hit, a declared contradiction or evidence pointing at something
else can never appear on any rung. The bottom rung exists so that a scene is never left
empty by *silence*: when nothing may be used, the project draws a neutral card, which
states nothing and is project-owned, rather than dressing a wrong clip up as the event.

Selection order is fully deterministic and never depends on which provider answered
first - see ``tie_break_key``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import os
from pathlib import Path
from typing import Any, Callable

from src.assets.semantic_selection.candidate_ranker import SUPPORT_RANK
from src.assets.semantic_selection.decision import (
    FRAMING_VERTICAL_READY,
    SUPPORT_FULL,
    SUPPORT_MANUAL,
    SUPPORT_PARTIAL,
    SUPPORT_UNVERIFIED,
    VERDICT_PARTIAL,
    read_decision,
)

from .assembly import (
    ASSEMBLY_COMPOSITE,
    ASSEMBLY_EXACT,
    ASSEMBLY_FALLBACK,
    ASSEMBLY_PARTIAL,
    ASSEMBLY_UNRESOLVED,
    SLOT_DETAIL,
    SLOT_ESTABLISHING,
    SLOT_FALLBACK,
    SLOT_INFOGRAPHIC,
    SLOT_PRIMARY,
    SLOT_SUPPORTING,
    SceneVisualAssembly,
    max_slots_for,
    slot_from_asset,
    slot_windows,
)
from .modes import (
    MODE_DRAFT_COMPLETE,
    PRIORITY_CRITICAL,
    TIER_COMPOSITE,
    TIER_EMERGENCY,
    TIER_EXACT,
    TIER_GENERATED,
    TIER_GOOD_CONTEXT,
    TIER_PARTIAL,
    blocking_reasons,
    evaluate_usability,
    normalize_mode,
)

# --- Reuse policy ------------------------------------------------------------
# Repeating one clip is allowed - it is far better than a wrong clip - but it is a
# defect of the draft and has to be visible. Twice is the limit, and never twice in a
# row: a viewer notices an immediate repeat, and an author reading the report needs to
# know which scenes share material.
DEFAULT_MAX_USES_PER_ASSET = 2
DEFAULT_MIN_SCENE_GAP = 1
# Deducted from an asset's ordering score per previous use. Large enough that a fresh
# candidate of the same support level always wins, small enough that a reused *exact*
# match still beats a fresh partial one.
REUSE_PENALTY_PER_USE = 12.0


@dataclass
class ReuseLedger:
    """Which asset has already been used, where, and whether it may be used again."""

    max_uses: int = DEFAULT_MAX_USES_PER_ASSET
    min_scene_gap: int = DEFAULT_MIN_SCENE_GAP
    uses: dict[str, list[int]] = field(default_factory=dict)
    scenes: dict[str, list[str]] = field(default_factory=dict)

    def count(self, asset: dict[str, Any] | str) -> int:
        history = {
            int(scene_index)
            for key in _reuse_identity_keys(asset)
            for scene_index in self.uses.get(key, [])
        }
        return len(history)

    def last_scene_index(self, asset: dict[str, Any] | str) -> int | None:
        history = [
            int(scene_index)
            for key in _reuse_identity_keys(asset)
            for scene_index in self.uses.get(key, [])
        ]
        return max(history) if history else None

    def can_use(self, asset: dict[str, Any] | str, scene_index: int) -> bool:
        if not _reuse_identity_keys(asset):
            return False
        if self.count(asset) >= self.max_uses:
            return False
        last = self.last_scene_index(asset)
        # ``min_scene_gap=1`` means at least one different scene between two uses:
        # scene 0 -> scene 1 is an immediate repeat and is therefore refused.
        if last is not None and (scene_index - last) <= self.min_scene_gap:
            return False
        return True

    def record(
        self,
        asset: dict[str, Any] | str,
        scene_index: int,
        scene_id: str = "",
    ) -> None:
        keys = _reuse_identity_keys(asset)
        if not keys:
            return
        # The checksum (or path fallback) becomes the canonical serialized key. Merge
        # an old asset-id-only history when a resumed project now supplies richer
        # metadata, preserving backward compatibility without losing alias detection.
        key = keys[0]
        history = {
            int(item)
            for alias in keys
            for item in self.uses.get(alias, [])
        }
        history.add(int(scene_index))
        scene_history = list(
            dict.fromkeys(
                str(item)
                for alias in keys
                for item in self.scenes.get(alias, [])
                if str(item)
            )
        )
        if scene_id and str(scene_id) not in scene_history:
            scene_history.append(str(scene_id))
        for alias in keys[1:]:
            self.uses.pop(alias, None)
            self.scenes.pop(alias, None)
        self.uses[key] = sorted(history)
        if scene_history:
            self.scenes[key] = scene_history

    def penalty(self, asset: dict[str, Any] | str) -> float:
        return REUSE_PENALTY_PER_USE * self.count(asset)

    def copy(self) -> "ReuseLedger":
        """An independent copy, so a completion attempt can be rolled back.

        Filling a scene may have to be retried (a download fails, a file turns out to be
        unreadable). Without this, each abandoned attempt would still count as a use and
        an asset would be refused for a scene it was never actually placed in.
        """
        return ReuseLedger(
            max_uses=self.max_uses,
            min_scene_gap=self.min_scene_gap,
            uses={key: list(value) for key, value in self.uses.items()},
            scenes={key: list(value) for key, value in self.scenes.items()},
        )

    def adopt(self, other: "ReuseLedger") -> None:
        """Take over another ledger's state, after a successful attempt."""
        self.uses = {key: list(value) for key, value in other.uses.items()}
        self.scenes = {key: list(value) for key, value in other.scenes.items()}

    def repeated_assets(self) -> dict[str, list[str]]:
        return {asset_id: list(scenes) for asset_id, scenes in self.scenes.items() if len(scenes) > 1}

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_uses": self.max_uses,
            "min_scene_gap": self.min_scene_gap,
            "uses": {key: list(value) for key, value in self.uses.items()},
            "scenes": {key: list(value) for key, value in self.scenes.items()},
            "repeated_assets": self.repeated_assets(),
        }


def _reuse_identity_keys(asset: dict[str, Any] | str) -> list[str]:
    """Physical identity first, with legacy IDs retained as lookup aliases."""

    if not isinstance(asset, dict):
        value = str(asset or "").strip()
        return [value] if value else []

    keys: list[str] = []
    provenance = asset.get("provenance") if isinstance(asset.get("provenance"), dict) else {}
    checksum = str(
        asset.get("checksum_sha256") or provenance.get("checksum_sha256") or ""
    ).strip().lower()
    if (
        len(checksum) == 64
        and all(character in "0123456789abcdef" for character in checksum)
    ):
        keys.append(f"sha256:{checksum}")

    local_path = next(
        (
            str(asset.get(name) or "").strip()
            for name in ("path", "local_path", "downloaded_path")
            if str(asset.get(name) or "").strip()
        ),
        "",
    )
    if local_path:
        try:
            normalized = os.path.normcase(str(Path(local_path).resolve()))
        except (OSError, RuntimeError, ValueError):
            normalized = os.path.normcase(str(Path(local_path).absolute()))
        keys.append(f"path:{normalized}")

    asset_id = str(asset.get("asset_id") or "").strip()
    if asset_id:
        keys.append(asset_id)
    return list(dict.fromkeys(keys))


def reuse_identity(asset: dict[str, Any] | str) -> str:
    """Canonical key used by :class:`ReuseLedger` for a physical visual.

    Callers rebuilding a ledger from assemblies should pass the complete
    ``slot.selected_asset`` to this helper or directly to ``ReuseLedger.record``.
    Passing only ``asset_id`` remains supported for old manifests, but cannot detect
    two provider aliases that resolve to the same checksum.
    """

    keys = _reuse_identity_keys(asset)
    return keys[0] if keys else ""


def stable_candidate_id(candidate: dict[str, Any]) -> str:
    """An identifier that does not depend on when or in what order it was fetched."""
    values = [
        str(candidate.get(key) or "").strip()
        for key in (
            "provider_asset_id",
            "source_page_url",
            "source_url",
            "asset_id",
            "checksum_sha256",
            "local_path",
            "path",
        )
    ]
    return "|".join([str(candidate.get("provider") or "").strip(), *values])


def tie_break_key(
    candidate: dict[str, Any],
    *,
    reuse: ReuseLedger | None = None,
) -> tuple:
    """Deterministic ordering key. Lower sorts first, which means "better".

    Order, deliberately, is: semantic support, confirmed required slots, all matched
    slots, required and optional omissions, conflicts, rights confidence, technical
    suitability, vertical readiness, exact entity/location evidence, provider
    confidence, author requirements, score after the reuse penalty, reuse count, and
    finally a stable provider id.

    The last element guarantees a total order, so two runs over the same candidate set
    always choose the same asset. Provider response order is never consulted.
    """
    decision = read_decision(candidate)
    slots = decision.slots if isinstance(decision.slots, dict) else {}
    rights_confidence = 1.0 if (decision.rights_allowed_for_render and not decision.rights_review_required) else 0.0
    reuse_count = reuse.count(candidate) if reuse else 0
    score = float(candidate.get("final_score") or 0.0)
    adjusted_score = score - (reuse.penalty(candidate) if reuse else 0.0)
    details = slots.get("details") if isinstance(slots.get("details"), list) else []
    exact_entity_location = sum(
        1
        for item in details
        if isinstance(item, dict)
        and str(item.get("status") or "") == "matched"
        and (
            str(item.get("kind") or "") in {"location", "requirement"}
            or "location" in str(item.get("name") or "").lower()
            or "entity" in str(item.get("name") or "").lower()
        )
    )
    required_matches = sum(
        1
        for item in details
        if isinstance(item, dict)
        and bool(item.get("required"))
        and str(item.get("status") or "") == "matched"
    )
    return (
        -SUPPORT_RANK.get(str(decision.support_status or ""), 0),
        -required_matches,
        -len(slots.get("matched_slots") or []),
        len(slots.get("missing_required_slots") or []),
        len(slots.get("missing_slots") or []),
        len(slots.get("conflicting_slots") or []),
        -rights_confidence,
        -round(float(decision.technical_score or 0.0), 3),
        0 if decision.technical_status == FRAMING_VERTICAL_READY else 1,
        -exact_entity_location,
        -round(float(decision.provider_confidence or 0.0), 3),
        0 if "author_requirements_satisfied" in decision.selection_reasons else 1,
        -round(adjusted_score, 1),
        reuse_count,
        stable_candidate_id(candidate),
    )


def order_candidates(
    candidates: list[dict[str, Any]],
    *,
    reuse: ReuseLedger | None = None,
) -> list[dict[str, Any]]:
    """Every candidate, best first, by the deterministic key above."""
    return sorted(candidates, key=lambda candidate: tie_break_key(candidate, reuse=reuse))


def eligible_candidates(
    candidates: list[dict[str, Any]],
    *,
    require_local_file: bool = False,
) -> list[dict[str, Any]]:
    """Candidates that may be used at all - rights, file, contradictions all cleared."""
    return [
        candidate
        for candidate in candidates
        if isinstance(candidate, dict) and not blocking_reasons(candidate, require_local_file=require_local_file)
    ]


def quality_tier_for(candidate: dict[str, Any], *, reused: bool = False) -> str:
    """Which rung of the ladder this candidate answers from."""
    decision = read_decision(candidate)
    if reused:
        return TIER_EMERGENCY
    if _is_emergency_generated(candidate):
        return TIER_EMERGENCY
    if str(candidate.get("provider") or "") == "generated":
        return TIER_GENERATED
    support = str(decision.support_status or "")
    if support == SUPPORT_FULL:
        return TIER_EXACT if not decision.support_requirements else TIER_GOOD_CONTEXT
    if support == SUPPORT_PARTIAL:
        return TIER_GOOD_CONTEXT if decision.slot_verdict == VERDICT_PARTIAL else TIER_PARTIAL
    if support == SUPPORT_MANUAL:
        return TIER_PARTIAL
    if support == SUPPORT_UNVERIFIED:
        return TIER_EMERGENCY
    return TIER_PARTIAL


def _is_emergency_generated(candidate: dict[str, Any]) -> bool:
    if str(candidate.get("selected_by") or "") == "emergency_neutral_backdrop":
        return True
    raw = candidate.get("raw_metadata") if isinstance(candidate.get("raw_metadata"), dict) else {}
    provenance = candidate.get("provenance") if isinstance(candidate.get("provenance"), dict) else {}
    snapshot = (
        provenance.get("metadata_snapshot")
        if isinstance(provenance.get("metadata_snapshot"), dict)
        else {}
    )
    return str(raw.get("variant") or snapshot.get("variant") or "") == "backdrop"


def _missing_slot_names(candidate: dict[str, Any]) -> list[str]:
    slots = read_decision(candidate).slots
    slots = slots if isinstance(slots, dict) else {}
    return [str(name) for name in (slots.get("missing_slots") or [])]


def _matched_slot_names(candidate: dict[str, Any]) -> list[str]:
    slots = read_decision(candidate).slots
    slots = slots if isinstance(slots, dict) else {}
    return [str(name) for name in (slots.get("matched_slots") or [])]


def _purpose_for(candidate: dict[str, Any], *, position: int, covered: list[str]) -> str:
    """What this slot is doing in the scene, from what it was chosen to cover."""
    if _is_emergency_generated(candidate):
        return SLOT_FALLBACK
    if str(candidate.get("provider") or "") == "generated":
        return SLOT_INFOGRAPHIC
    if position == 0:
        return SLOT_PRIMARY
    joined = ",".join(covered)
    if "location" in joined:
        return SLOT_ESTABLISHING
    if "action" in joined or "subject" in joined:
        return SLOT_DETAIL
    return SLOT_SUPPORTING


def build_scene_assembly(
    *,
    scene: dict[str, Any],
    ranked_candidates: list[dict[str, Any]],
    scene_duration_sec: float,
    mode: str,
    scene_index: int = 0,
    reuse: ReuseLedger | None = None,
    require_local_file: bool = False,
    emergency_asset_factory: Callable[[dict[str, Any]], dict[str, Any] | None] | None = None,
    requested_slot_count: int = 0,
) -> SceneVisualAssembly:
    """Fill one scene by walking the ladder. Never raises; may return an unresolved scene.

    ``ranked_candidates`` must already carry their selection decisions (which is what
    ``src.assets.semantic_selection.rank_candidates`` writes). Assets already used in
    other scenes may be included in that list - they are ordered down by the reuse
    penalty and marked as reuse in the resulting slots.

    ``emergency_asset_factory`` builds the last-rung neutral card. It is a callable so
    that this module stays free of the filesystem; passing ``None`` means the scene is
    allowed to stay unresolved, which is what ``strict`` mode wants.
    """
    mode = normalize_mode(mode)
    scene_id = str(scene.get("scene_id") or "")
    duration = max(0.0, float(scene_duration_sec or 0.0))
    ledger = reuse if reuse is not None else ReuseLedger()
    assembly = SceneVisualAssembly(
        scene_id=scene_id,
        scene_duration_sec=duration,
        completion_mode=mode,
        assembly_status=ASSEMBLY_UNRESOLVED,
    )

    eligible = eligible_candidates(ranked_candidates, require_local_file=require_local_file)
    if not eligible:
        assembly.ladder_trace.append("no_eligible_candidate")
    ordered = order_candidates(eligible, reuse=ledger)

    # In strict mode nothing below the top rung may be chosen automatically: a scene
    # that has no fully supported, fully cleared candidate stays unresolved exactly as
    # it did before this stage existed.
    if mode != MODE_DRAFT_COMPLETE:
        for candidate in ordered:
            verdict = evaluate_usability(candidate, mode=mode, quality_tier=quality_tier_for(candidate))
            if verdict.automatic_render_allowed:
                return _single_slot_assembly(
                    assembly, candidate, duration, mode=mode, ladder_level="A_exact", ledger=ledger,
                    scene_index=scene_index, scene=scene,
                )
        assembly.ladder_trace.append("strict_mode_requires_full_support")
        return assembly

    slot_budget = max_slots_for(duration)
    if requested_slot_count > 0:
        slot_budget = min(slot_budget, max(1, requested_slot_count))

    # Previously used assets are deliberately absent from A-E.  Reuse is a safe last
    # resort, not a way to make a repeated exact clip look like a fresh tier-A answer.
    fresh = [
        candidate
        for candidate in ordered
        if ledger.count(candidate) == 0
        and ledger.can_use(candidate, scene_index)
    ]

    # --- rung A: one exact asset ---------------------------------------------
    exact = _first_usable_at_tier(fresh, TIER_EXACT, mode=mode)
    if exact is not None:
        assembly.ladder_trace.append("A_exact:single_asset")
        return _single_slot_assembly(
            assembly, exact, duration, mode=mode, ladder_level=TIER_EXACT, ledger=ledger,
            scene_index=scene_index, scene=scene,
        )

    # --- rung B: two to four complementary assets ---------------------------
    if ordered and slot_budget >= 2:
        composite = _composite_group(
            fresh,
            ledger=ledger,
            scene_index=scene_index,
            slot_budget=slot_budget,
            mode=mode,
        )
        if composite is not None:
            group, covered_by_position, complete = composite
            covered = [name for names in covered_by_position for name in names]
            assembly.ladder_trace.append(
                f"B_composite:{'covers_all' if complete else 'covers_part'}:{','.join(covered) or '-'}"
            )
            return _composite_assembly(
                assembly, group, duration, mode=mode, ledger=ledger,
                scene_index=scene_index, covered_by_position=covered_by_position,
                complete=complete, scene=scene,
            )

    # --- rungs C then D: weaker, but verified, fresh material ----------------
    for tier in (TIER_GOOD_CONTEXT, TIER_PARTIAL):
        candidate = _first_usable_at_tier(fresh, tier, mode=mode)
        if candidate is None:
            continue
        assembly.ladder_trace.append(f"{tier}:single_asset")
        return _single_slot_assembly(
            assembly, candidate, duration, mode=mode, ladder_level=tier, ledger=ledger,
            scene_index=scene_index, scene=scene,
        )

    # --- rung E: a deterministic project-generated figure -------------------
    generated = _first_usable_at_tier(fresh, TIER_GENERATED, mode=mode)
    if generated is not None:
        assembly.ladder_trace.append("E_generated:single_asset")
        return _single_slot_assembly(
            assembly, generated, duration, mode=mode, ladder_level=TIER_GENERATED, ledger=ledger,
            scene_index=scene_index, scene=scene,
        )

    # --- rung F: a permitted, non-adjacent reuse -----------------------------
    for candidate in ordered:
        asset_id = str(candidate.get("asset_id") or "")
        if ledger.count(candidate) <= 0:
            continue
        if not ledger.can_use(candidate, scene_index):
            assembly.ladder_trace.append(f"reuse_limit_reached:{asset_id}")
            continue
        verdict = evaluate_usability(candidate, mode=mode, quality_tier=TIER_EMERGENCY)
        if not verdict.usable_in_draft:
            continue
        assembly.ladder_trace.append("F_emergency:reuse")
        return _single_slot_assembly(
            assembly, candidate, duration, mode=mode, ladder_level=TIER_EMERGENCY, ledger=ledger,
            scene_index=scene_index, scene=scene, reused=True, forced_tier=TIER_EMERGENCY,
        )

    # --- rung F: a neutral card that states nothing --------------------------
    if emergency_asset_factory is not None:
        emergency = emergency_asset_factory(scene)
        if emergency:
            emergency_id = str(emergency.get("asset_id") or "")
            reuse_count = ledger.count(emergency)
            if not ledger.can_use(emergency, scene_index):
                assembly.ladder_trace.append(
                    f"emergency_reuse_limit_reached:{emergency_id or 'unidentified'}"
                )
            else:
                verdict = evaluate_usability(emergency, mode=mode, quality_tier=TIER_EMERGENCY)
                if verdict.usable_in_draft:
                    assembly.ladder_trace.append("F_emergency:neutral_backdrop")
                    return _single_slot_assembly(
                        assembly, emergency, duration, mode=mode, ladder_level=TIER_EMERGENCY, ledger=ledger,
                        scene_index=scene_index, scene=scene, forced_tier=TIER_EMERGENCY,
                        purpose=SLOT_FALLBACK, reused=reuse_count > 0,
                    )
                assembly.ladder_trace.append("F_emergency:factory_asset_not_usable")

    assembly.warnings.append("scene_has_no_usable_material")
    assembly.replacement_recommendations.append(
        {
            "scene_id": scene_id,
            "slot_id": "",
            "priority": PRIORITY_CRITICAL,
            "reason": "no_usable_material_found",
            "recommended_material": _recommended_material(scene),
        }
    )
    return assembly


def _first_usable_at_tier(
    ordered: list[dict[str, Any]],
    tier: str,
    *,
    mode: str,
) -> dict[str, Any] | None:
    for candidate in ordered:
        if quality_tier_for(candidate) != tier:
            continue
        if evaluate_usability(candidate, mode=mode, quality_tier=tier).usable_in_draft:
            return candidate
    return None


def _composite_group(
    ordered: list[dict[str, Any]],
    *,
    ledger: ReuseLedger,
    scene_index: int,
    slot_budget: int,
    mode: str,
) -> tuple[list[dict[str, Any]], list[list[str]], bool] | None:
    """The best deterministic group of complementary fresh assets.

    A supporting asset only earns its place by confirming something the primary is
    missing. Clips that all show the same half of the scene are not a composite. The
    greedy walk may collect up to the scene's four-slot budget and is deterministic
    because ``ordered`` already has a total stable order.
    """
    best_partial: tuple[list[dict[str, Any]], list[list[str]], bool] | None = None
    for primary in ordered:
        primary_id = str(primary.get("asset_id") or "")
        if not primary_id or ledger.count(primary) or not ledger.can_use(primary, scene_index):
            continue
        primary_tier = quality_tier_for(primary)
        if primary_tier not in {TIER_GOOD_CONTEXT, TIER_PARTIAL}:
            continue
        if not evaluate_usability(primary, mode=mode, quality_tier=primary_tier).usable_in_draft:
            continue
        missing = list(dict.fromkeys(_missing_slot_names(primary)))
        if not missing:
            continue
        remaining = set(missing)
        group = [primary]
        covered_by_position: list[list[str]] = [[]]
        for secondary in ordered:
            if len(group) >= slot_budget:
                break
            secondary_id = str(secondary.get("asset_id") or "")
            if not secondary_id or any(
                bool(
                    set(_reuse_identity_keys(item))
                    & set(_reuse_identity_keys(secondary))
                )
                for item in group
            ):
                continue
            if ledger.count(secondary) or not ledger.can_use(secondary, scene_index):
                continue
            secondary_tier = quality_tier_for(secondary)
            if secondary_tier not in {TIER_GOOD_CONTEXT, TIER_PARTIAL}:
                continue
            if not evaluate_usability(
                secondary, mode=mode, quality_tier=secondary_tier
            ).usable_in_draft:
                continue
            covered = [name for name in _matched_slot_names(secondary) if name in remaining]
            if not covered:
                continue
            group.append(secondary)
            covered_by_position.append(covered)
            remaining.difference_update(covered)
            if not remaining:
                break
        if len(group) >= 2:
            result = (group, covered_by_position, not remaining)
            if not remaining:
                return result
            if best_partial is None:
                best_partial = result
    return best_partial


def _single_slot_assembly(
    assembly: SceneVisualAssembly,
    candidate: dict[str, Any],
    duration: float,
    *,
    mode: str,
    ladder_level: str,
    ledger: ReuseLedger,
    scene_index: int,
    scene: dict[str, Any],
    reused: bool = False,
    forced_tier: str = "",
    purpose: str = "",
) -> SceneVisualAssembly:
    asset_id = str(candidate.get("asset_id") or "")
    tier = forced_tier or quality_tier_for(candidate, reused=reused)
    reuse_count = ledger.count(candidate)
    usability = evaluate_usability(candidate, mode=mode, quality_tier=tier, reuse_count=reuse_count)
    start, end = slot_windows(1, duration)[0]
    slot = slot_from_asset(
        candidate,
        slot_id=f"{assembly.scene_id or 'scene'}_slot_001",
        purpose=purpose or _purpose_for(candidate, position=0, covered=[]),
        start_offset_sec=start,
        end_offset_sec=end,
        quality_tier=tier,
        usability=usability,
        required_subject=_requirement(scene, "subject"),
        required_action=_requirement(scene, "action"),
        required_location=_requirement(scene, "location"),
        ladder_level=ladder_level,
        reuse_of_asset=asset_id if reuse_count else "",
        reuse_reason="no_other_allowed_material_for_this_scene" if reuse_count else "",
    )
    if reuse_count:
        _attach_reuse_crop(slot, asset_id=asset_id, reuse_count=reuse_count, scene_index=scene_index)
    assembly.slots = [slot]
    assembly.support_status = slot.support_status
    assembly.assembly_status = _status_for(tier)
    ledger.record(candidate, scene_index, assembly.scene_id)
    _add_recommendations(assembly)
    return assembly


def _composite_assembly(
    assembly: SceneVisualAssembly,
    candidates: list[dict[str, Any]],
    duration: float,
    *,
    mode: str,
    ledger: ReuseLedger,
    scene_index: int,
    covered_by_position: list[list[str]],
    complete: bool,
    scene: dict[str, Any],
) -> SceneVisualAssembly:
    windows = slot_windows(len(candidates), duration)
    if len(windows) != len(candidates):
        raise ValueError("composite_slot_budget_exceeds_scene_duration")
    slots = []
    for position, (candidate, window) in enumerate(zip(candidates, windows, strict=True)):
        asset_id = str(candidate.get("asset_id") or "")
        reuse_count = ledger.count(candidate)
        own_tier = quality_tier_for(candidate)
        tier = TIER_COMPOSITE if complete else own_tier
        usability = evaluate_usability(candidate, mode=mode, quality_tier=tier, reuse_count=reuse_count)
        covered = covered_by_position[position] if position < len(covered_by_position) else []
        slots.append(
            slot_from_asset(
                candidate,
                slot_id=f"{assembly.scene_id or 'scene'}_slot_{position + 1:03d}",
                purpose=_purpose_for(candidate, position=position, covered=covered),
                start_offset_sec=window[0],
                end_offset_sec=window[1],
                quality_tier=tier,
                usability=usability,
                required_subject=_requirement(scene, "subject"),
                required_action=_requirement(scene, "action"),
                required_location=_requirement(scene, "location"),
                ladder_level="B_composite",
                notes=[f"covers:{name}" for name in covered],
            )
        )
        ledger.record(candidate, scene_index, assembly.scene_id)
    assembly.slots = slots
    assembly.assembly_status = ASSEMBLY_COMPOSITE
    assembly.support_status = slots[0].support_status
    _add_recommendations(assembly)
    return assembly


def _attach_reuse_crop(
    slot: Any,
    *,
    asset_id: str,
    reuse_count: int,
    scene_index: int,
) -> None:
    """Record a stable alternate framing for a repeated asset.

    The renderer interprets the anchor and zoom as a real alternate crop, and the
    replacement report keeps the same deterministic record of how the repeated shot
    was intentionally varied.
    """

    seed = hashlib.sha256(f"{asset_id}|{reuse_count}|{scene_index}".encode("utf-8")).digest()[0]
    variants = (
        {"anchor": "left", "zoom": 1.06},
        {"anchor": "right", "zoom": 1.08},
        {"anchor": "top", "zoom": 1.05},
        {"anchor": "bottom", "zoom": 1.07},
    )
    variant_index = int(seed) % len(variants)
    slot.crop_decision = {
        **dict(slot.crop_decision),
        "reuse_transform": {
            "variant": variant_index + 1,
            **variants[variant_index],
        },
    }
    slot.notes.append(f"reuse_crop_variant:{variant_index + 1}")


def _status_for(tier: str) -> str:
    if tier == TIER_EXACT:
        return ASSEMBLY_EXACT
    if tier == TIER_GENERATED:
        return ASSEMBLY_EXACT
    if tier == TIER_EMERGENCY:
        return ASSEMBLY_FALLBACK
    return ASSEMBLY_PARTIAL


def _requirement(scene: dict[str, Any], field_name: str) -> str:
    semantic = scene.get("semantic") if isinstance(scene.get("semantic"), dict) else {}
    values = semantic.get(field_name) or []
    if isinstance(values, list) and values:
        return str(values[0])
    brief = scene.get("visual_brief") if isinstance(scene.get("visual_brief"), dict) else {}
    if field_name == "location":
        return str(brief.get("place") or brief.get("location") or "")
    return str(brief.get(field_name) or "")


def _recommended_material(scene: dict[str, Any]) -> str:
    parts = [_requirement(scene, "subject"), _requirement(scene, "action"), _requirement(scene, "location")]
    return " ".join(part for part in parts if part).strip()


def _add_recommendations(assembly: SceneVisualAssembly) -> None:
    """One recommendation per slot the author should look at. Never for a clean slot."""
    for slot in assembly.slots:
        if slot.publish_ready and not slot.reuse_of_asset:
            continue
        assembly.replacement_recommendations.append(
            {
                "scene_id": assembly.scene_id,
                "slot_id": slot.slot_id,
                "priority": slot.replacement_priority,
                "quality_tier": slot.quality_tier,
                "support_status": slot.support_status,
                "reason": ";".join(slot.usability.limitations) or "not_publish_ready",
                "recommended_material": " ".join(
                    part for part in (slot.required_subject, slot.required_action, slot.required_location) if part
                ).strip(),
                "reused": bool(slot.reuse_of_asset),
            }
        )


__all__ = [
    "DEFAULT_MAX_USES_PER_ASSET",
    "DEFAULT_MIN_SCENE_GAP",
    "REUSE_PENALTY_PER_USE",
    "ReuseLedger",
    "build_scene_assembly",
    "eligible_candidates",
    "order_candidates",
    "quality_tier_for",
    "reuse_identity",
    "stable_candidate_id",
    "tie_break_key",
]
