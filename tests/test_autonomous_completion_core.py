from __future__ import annotations

import hashlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from src.assets.generated_infographic import InfographicSpec, build_generated_asset
from src.assets.completion.assembly import (
    ASSEMBLY_KEY,
    ASSEMBLY_PARTIAL,
    SLOT_PRIMARY,
    SceneVisualAssembly,
    VisualSlot,
    assembly_from_selected_asset,
    read_assembly,
    scaled_slot_windows,
)
from src.assets.completion.ladder import (
    ReuseLedger,
    build_scene_assembly,
    order_candidates,
    reuse_identity,
)
from src.assets.completion.modes import (
    BLOCK_FACTUALLY_MISLEADING,
    BLOCK_MUST_AVOID,
    BLOCK_RIGHTS,
    BLOCK_TECHNICAL,
    MODE_DRAFT_COMPLETE,
    MODE_STRICT,
    PRIORITY_HIGH,
    TIER_COMPOSITE,
    TIER_EMERGENCY,
    TIER_EXACT,
    TIER_PARTIAL,
    UsabilityVerdict,
    blocking_reasons,
    evaluate_usability,
)
from src.assets.semantic_selection.decision import (
    DECISION_KEY,
    FRAMING_VERTICAL_READY,
    SUPPORT_FULL,
    SUPPORT_PARTIAL,
    SUPPORT_UNVERIFIED,
    VERDICT_COMPLETE,
    VERDICT_CONFLICTING,
    VERDICT_INCOMPLETE,
    VERDICT_PARTIAL,
    SelectionDecision,
)


def _candidate(
    asset_id: str,
    *,
    support: str = SUPPORT_FULL,
    slot_verdict: str = VERDICT_COMPLETE,
    provider: str = "fake",
    path: str = "",
    matched: list[str] | None = None,
    missing: list[str] | None = None,
    details: list[dict] | None = None,
    reject_reasons: list[str] | None = None,
    final_score: float = 80.0,
    variant: str = "",
    media_type: str = "image",
) -> dict:
    decision = SelectionDecision(
        scene_id="scene",
        asset_id=asset_id,
        provider=provider,
        provider_confidence=0.8,
        semantic_score=80.0,
        semantic_status="matched",
        technical_score=90.0,
        technical_status=FRAMING_VERTICAL_READY,
        rights_status="licensed",
        rights_allowed_for_render=True,
        rights_review_required=False,
        slots={
            "matched_slots": list(matched or []),
            "missing_slots": list(missing or []),
            "missing_required_slots": list(missing or []),
            "conflicting_slots": [],
            "details": list(details or []),
        },
        slot_verdict=slot_verdict,
        support_status=support,
        reject_reasons=list(reject_reasons or []),
    )
    candidate = {
        "asset_id": asset_id,
        "provider": provider,
        "provider_asset_id": asset_id,
        "type": media_type,
        "media_type": media_type,
        "path": path,
        "local_path": path,
        "rights_status": "licensed",
        "allowed_for_render": True,
        "review_required": False,
        "license": {
            "license_name": "test",
            "rights_status": "licensed",
            "allowed_for_render": True,
            "review_required": False,
        },
        "technical_validation": {
            "status": "passed",
            "media_type": media_type,
            "width": 1080,
            "height": 1920,
        },
        "final_score": final_score,
        DECISION_KEY: decision.to_dict(),
    }
    if variant:
        candidate["raw_metadata"] = {"variant": variant}
    return candidate


class CompletionModeSafetyTests(unittest.TestCase):
    def test_strict_stays_full_support_only(self) -> None:
        exact = evaluate_usability(
            _candidate("exact"), mode=MODE_STRICT, quality_tier=TIER_EXACT
        )
        partial = evaluate_usability(
            _candidate(
                "partial",
                support=SUPPORT_PARTIAL,
                slot_verdict=VERDICT_PARTIAL,
            ),
            mode=MODE_STRICT,
            quality_tier=TIER_PARTIAL,
        )

        self.assertTrue(exact.usable_in_draft)
        self.assertTrue(exact.publish_ready)
        self.assertFalse(partial.usable_in_draft)
        self.assertFalse(partial.automatic_render_allowed)

    def test_partial_is_automatic_draft_only(self) -> None:
        verdict = evaluate_usability(
            _candidate(
                "partial",
                support=SUPPORT_PARTIAL,
                slot_verdict=VERDICT_PARTIAL,
            ),
            mode=MODE_DRAFT_COMPLETE,
            quality_tier=TIER_PARTIAL,
        )

        self.assertTrue(verdict.usable_in_draft)
        self.assertTrue(verdict.automatic_render_allowed)
        self.assertFalse(verdict.publish_ready)
        self.assertTrue(verdict.manual_replacement_recommended)

    def test_missing_orca_evidence_is_factually_blocked(self) -> None:
        verdict = evaluate_usability(
            _candidate(
                "boats_on_lake",
                support=SUPPORT_PARTIAL,
                slot_verdict=VERDICT_PARTIAL,
                reject_reasons=["missing_orca_evidence_for_orca_scene"],
                media_type="video",
            ),
            mode=MODE_DRAFT_COMPLETE,
            quality_tier=TIER_PARTIAL,
        )

        self.assertTrue(verdict.blocked)
        self.assertFalse(verdict.usable_in_draft)
        self.assertIn(BLOCK_FACTUALLY_MISLEADING, verdict.block_reasons)

    def test_unverified_provider_footage_is_not_auto_used(self) -> None:
        verdict = evaluate_usability(
            _candidate(
                "unknown",
                support=SUPPORT_UNVERIFIED,
                slot_verdict="unverified",
            ),
            mode=MODE_DRAFT_COMPLETE,
            quality_tier=TIER_EMERGENCY,
        )

        self.assertFalse(verdict.usable_in_draft)
        self.assertFalse(verdict.automatic_render_allowed)
        self.assertTrue(verdict.manual_replacement_required)

    def test_safe_emergency_stand_in_has_high_replacement_priority(self) -> None:
        verdict = evaluate_usability(
            _candidate(
                "neutral_backdrop",
                provider="generated",
                support=SUPPORT_PARTIAL,
                slot_verdict=VERDICT_PARTIAL,
                variant="backdrop",
            ),
            mode=MODE_DRAFT_COMPLETE,
            quality_tier=TIER_EMERGENCY,
        )

        self.assertTrue(verdict.usable_in_draft)
        self.assertFalse(verdict.publish_ready)
        self.assertTrue(verdict.manual_replacement_required)
        self.assertEqual(verdict.replacement_priority, PRIORITY_HIGH)

    def test_any_conflicting_rights_record_blocks_with_explicit_flag(self) -> None:
        candidate = _candidate("blocked")
        decision = SelectionDecision.from_dict(candidate[DECISION_KEY])
        decision.rights_status = "blocked"
        decision.rights_allowed_for_render = False
        decision.rights_review_required = True
        candidate[DECISION_KEY] = decision.to_dict()

        verdict = evaluate_usability(
            candidate, mode=MODE_DRAFT_COMPLETE, quality_tier=TIER_PARTIAL
        )

        self.assertIn(BLOCK_RIGHTS, verdict.block_reasons)
        self.assertTrue(verdict.blocked)
        self.assertTrue(verdict.rights_blocked)
        self.assertFalse(verdict.usable_in_draft)

    def test_nested_license_veto_cannot_be_overridden_by_root_flag(self) -> None:
        candidate = _candidate("nested_block")
        candidate["license"]["allowed_for_render"] = False
        candidate["license"]["review_required"] = True
        candidate["license"]["rights_status"] = "review_required"

        self.assertIn(BLOCK_RIGHTS, blocking_reasons(candidate))

    def test_unknown_license_is_blocked_even_with_a_permissive_root_flag(self) -> None:
        candidate = _candidate("unknown_license")
        candidate["license"]["license_name"] = "unknown"
        candidate["license_name"] = "unknown"

        verdict = evaluate_usability(
            candidate,
            mode=MODE_DRAFT_COMPLETE,
            quality_tier=TIER_PARTIAL,
        )

        self.assertTrue(verdict.rights_blocked)
        self.assertFalse(verdict.usable_in_draft)

    def test_string_boolean_cannot_turn_a_rights_veto_into_permission(self) -> None:
        candidate = _candidate("string_false")
        candidate["license"]["allowed_for_render"] = "false"

        self.assertIn(BLOCK_RIGHTS, blocking_reasons(candidate))

    def test_render_gate_requires_passing_technical_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "exists.bin"
            source.write_bytes(b"not validated")
            candidate = _candidate("not_validated", path=str(source))
            candidate["technical_validation"] = {}

            reasons = blocking_reasons(candidate, require_local_file=True)

        self.assertIn(BLOCK_TECHNICAL, reasons)

    def test_render_gate_rejects_stale_checksum_and_corrupt_passed_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            valid = root / "valid.png"
            Image.new("RGB", (32, 32), "green").save(valid)
            stale = _candidate("stale_checksum", path=str(valid))
            stale["checksum_sha256"] = "0" * 64
            self.assertIn(
                BLOCK_TECHNICAL,
                blocking_reasons(stale, require_local_file=True),
            )

            corrupt = root / "corrupt.png"
            corrupt.write_bytes(b"not a decodable PNG")
            corrupt_candidate = _candidate("corrupt", path=str(corrupt))
            corrupt_candidate["checksum_sha256"] = hashlib.sha256(
                corrupt.read_bytes()
            ).hexdigest()
            self.assertIn(
                BLOCK_TECHNICAL,
                blocking_reasons(corrupt_candidate, require_local_file=True),
            )

    def test_final_render_gate_refuses_an_asset_with_no_recorded_checksum(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "unrecorded.png"
            Image.new("RGB", (32, 32), "green").save(source)
            candidate = _candidate("unrecorded", path=str(source))

            # Earlier gates still read manifests written before a checksum was
            # persisted, so a missing expectation is not a block there.
            self.assertNotIn(
                BLOCK_TECHNICAL,
                blocking_reasons(candidate, require_local_file=True),
            )
            # The final boundary has nothing left to compare the bytes against.
            self.assertIn(
                BLOCK_TECHNICAL,
                blocking_reasons(
                    candidate,
                    require_local_file=True,
                    fresh_local_file_validation=True,
                ),
            )

    def test_unchanged_local_file_decode_validation_is_cached(self) -> None:
        from src.assets.download import validate_local_asset

        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "cached.png"
            Image.new("RGB", (32, 32), "green").save(source)
            checksum = hashlib.sha256(source.read_bytes()).hexdigest()
            candidate = _candidate("cached", path=str(source))
            candidate["checksum_sha256"] = checksum
            candidate["provenance"] = {"checksum_sha256": checksum}

            with patch(
                "src.assets.download.validate_local_asset",
                wraps=validate_local_asset,
            ) as validate:
                first = blocking_reasons(candidate, require_local_file=True)
                second = blocking_reasons(candidate, require_local_file=True)

        self.assertNotIn(BLOCK_TECHNICAL, first)
        self.assertNotIn(BLOCK_TECHNICAL, second)
        self.assertEqual(validate.call_count, 1)

    def test_must_avoid_and_conflict_have_explicit_block_flags(self) -> None:
        must_avoid = _candidate("avoid", reject_reasons=["must_avoid_match:penguin"])
        conflict = _candidate("conflict", slot_verdict=VERDICT_CONFLICTING)

        avoid_verdict = evaluate_usability(
            must_avoid, mode=MODE_DRAFT_COMPLETE, quality_tier=TIER_PARTIAL
        )
        conflict_verdict = evaluate_usability(
            conflict, mode=MODE_DRAFT_COMPLETE, quality_tier=TIER_PARTIAL
        )

        self.assertIn(BLOCK_MUST_AVOID, avoid_verdict.block_reasons)
        self.assertTrue(avoid_verdict.must_avoid_blocked)
        self.assertIn(BLOCK_FACTUALLY_MISLEADING, conflict_verdict.block_reasons)
        self.assertTrue(conflict_verdict.factually_misleading)

    def test_non_real_and_ambiguous_species_video_are_blocked_in_draft(self) -> None:
        for reason in (
            "non_real_video_footage:animated",
            "ambiguous_whale_for_orca_scene",
        ):
            with self.subTest(reason=reason):
                candidate = _candidate(
                    reason,
                    reject_reasons=[reason],
                    media_type="video",
                    support=SUPPORT_PARTIAL,
                    slot_verdict=VERDICT_PARTIAL,
                )

                verdict = evaluate_usability(
                    candidate,
                    mode=MODE_DRAFT_COMPLETE,
                    quality_tier=TIER_PARTIAL,
                )

                self.assertIn(BLOCK_FACTUALLY_MISLEADING, verdict.block_reasons)
                self.assertTrue(verdict.factually_misleading)

    def test_nonempty_conflicting_slots_block_even_when_stale_verdict_is_partial(self) -> None:
        candidate = _candidate(
            "stale_conflict",
            support=SUPPORT_PARTIAL,
            slot_verdict=VERDICT_PARTIAL,
        )
        candidate[DECISION_KEY]["slots"]["conflicting_slots"] = [
            "conflicting_context:Mars"
        ]

        verdict = evaluate_usability(
            candidate,
            mode=MODE_DRAFT_COMPLETE,
            quality_tier=TIER_PARTIAL,
        )

        self.assertIn(BLOCK_FACTUALLY_MISLEADING, verdict.block_reasons)
        self.assertTrue(verdict.factually_misleading)
        self.assertFalse(verdict.usable_in_draft)


class VisualAssemblyTests(unittest.TestCase):
    def _slot(self, slot_id: str, start: float, end: float, asset_id: str) -> VisualSlot:
        verdict = UsabilityVerdict(
            usable_in_draft=True,
            automatic_render_allowed=True,
            publish_ready=False,
            manual_replacement_recommended=True,
            quality_tier=TIER_PARTIAL,
            support_status=SUPPORT_PARTIAL,
        )
        return VisualSlot(
            slot_id=slot_id,
            purpose=SLOT_PRIMARY,
            start_offset_sec=start,
            end_offset_sec=end,
            selected_asset=_candidate(
                asset_id,
                support=SUPPORT_PARTIAL,
                slot_verdict=VERDICT_PARTIAL,
            ),
            support_status=SUPPORT_PARTIAL,
            quality_tier=TIER_PARTIAL,
            usability=verdict,
        )

    def test_multislot_round_trip_and_nonuniform_scaling(self) -> None:
        assembly = SceneVisualAssembly(
            scene_id="scene_001",
            scene_duration_sec=4.0,
            assembly_status=ASSEMBLY_PARTIAL,
            completion_mode=MODE_DRAFT_COMPLETE,
            slots=[
                self._slot("slot_a", 0.0, 1.2, "a"),
                self._slot("slot_b", 1.2, 4.0, "b"),
            ],
        )

        restored = SceneVisualAssembly.from_dict(assembly.to_dict())
        windows = scaled_slot_windows(restored, 8.0)

        self.assertEqual(restored.to_dict(), assembly.to_dict())
        self.assertEqual([(start, end) for _, start, end in windows], [(0.0, 2.4), (2.4, 8.0)])
        self.assertTrue(restored.usable_in_draft)

    def test_validation_rejects_multislot_fragment_below_minimum_duration(self) -> None:
        assembly = SceneVisualAssembly(
            scene_id="s",
            scene_duration_sec=3.0,
            slots=[
                self._slot("too_short", 0.0, 0.8, "a"),
                self._slot("remainder", 0.8, 3.0, "b"),
            ],
        )

        self.assertIn("slot_too_short:too_short:0.800", assembly.validate())

    def test_validation_rejects_duplicate_ids_gap_overlap_and_nonfinite_time(self) -> None:
        duplicate = SceneVisualAssembly(
            scene_id="s",
            scene_duration_sec=4.0,
            slots=[
                self._slot("same", 0.0, 1.0, "a"),
                self._slot("same", 2.0, 4.0, "b"),
                self._slot("nan", float("nan"), 3.0, "c"),
            ],
        )

        problems = duplicate.validate()

        self.assertIn("duplicate_slot_id:same", problems)
        self.assertIn("slot_gap_before:same", problems)
        self.assertIn("slot_time_not_finite:nan", problems)
        self.assertFalse(duplicate.usable_in_draft)

    def test_legacy_selected_asset_is_one_full_scene_slot(self) -> None:
        selected = _candidate("legacy")
        assembly = assembly_from_selected_asset(
            {"scene_id": "scene_legacy", "selected_asset": selected},
            scene_duration_sec=5.0,
            completion_mode=MODE_STRICT,
        )

        self.assertEqual(len(assembly.slots), 1)
        self.assertEqual(assembly.slots[0].start_offset_sec, 0.0)
        self.assertEqual(assembly.slots[0].end_offset_sec, 5.0)
        self.assertEqual(assembly.primary_asset["asset_id"], "legacy")

    def test_authoritative_primary_is_not_reselected_by_completion(self) -> None:
        image = _candidate("exact_image", final_score=100.0)
        video = _candidate(
            "partial_video",
            support=SUPPORT_PARTIAL,
            slot_verdict=VERDICT_PARTIAL,
            final_score=60.0,
            media_type="video",
        )

        assembly = build_scene_assembly(
            scene={"scene_id": "scene_001"},
            ranked_candidates=[image, video],
            scene_duration_sec=5.0,
            mode=MODE_DRAFT_COMPLETE,
            authoritative_primary=image,
        )

        self.assertEqual(assembly.primary_asset["asset_id"], "exact_image")
        self.assertEqual(assembly.primary_asset["media_type"], "image")
        self.assertIn("canonical_primary:authoritative", assembly.ladder_trace)
        self.assertNotIn("video_first:video_pool", assembly.ladder_trace)

    def test_strict_and_draft_preserve_the_same_authoritative_media_decision(self) -> None:
        image = _candidate("exact_image", final_score=80.0)
        video = _candidate(
            "competitive_video",
            final_score=70.0,
            media_type="video",
        )

        strict = build_scene_assembly(
            scene={"scene_id": "scene_strict"},
            ranked_candidates=[image, video],
            scene_duration_sec=5.0,
            mode=MODE_STRICT,
            authoritative_primary=video,
        )
        draft = build_scene_assembly(
            scene={"scene_id": "scene_draft"},
            ranked_candidates=[image, video],
            scene_duration_sec=5.0,
            mode=MODE_DRAFT_COMPLETE,
            authoritative_primary=video,
        )

        self.assertEqual(strict.primary_asset["asset_id"], "competitive_video")
        self.assertEqual(draft.primary_asset["asset_id"], "competitive_video")
        self.assertEqual(strict.primary_asset["media_type"], "video")
        self.assertEqual(draft.primary_asset["media_type"], "video")

    def test_explicit_unresolved_assembly_does_not_resurrect_legacy_asset(self) -> None:
        unresolved = SceneVisualAssembly(
            scene_id="scene_unresolved",
            scene_duration_sec=5.0,
            slots=[],
        )
        entry = {
            "scene_id": "scene_unresolved",
            "selected_asset": _candidate("stale"),
            ASSEMBLY_KEY: unresolved.to_dict(),
        }

        restored = read_assembly(entry, scene_duration_sec=5.0)

        self.assertEqual(restored.scene_id, "scene_unresolved")
        self.assertEqual(restored.slots, [])
        self.assertFalse(restored.usable_in_draft)


class FallbackAndReuseTests(unittest.TestCase):
    def test_composite_can_fill_up_to_four_complementary_slots(self) -> None:
        candidates = [
            _candidate(
                "a",
                support=SUPPORT_PARTIAL,
                slot_verdict=VERDICT_INCOMPLETE,
                matched=["subject"],
                missing=["action", "location", "context"],
            ),
            _candidate(
                "b",
                support=SUPPORT_PARTIAL,
                slot_verdict=VERDICT_INCOMPLETE,
                matched=["action"],
                missing=["subject", "location", "context"],
            ),
            _candidate(
                "c",
                support=SUPPORT_PARTIAL,
                slot_verdict=VERDICT_INCOMPLETE,
                matched=["location"],
                missing=["subject", "action", "context"],
            ),
            _candidate(
                "d",
                support=SUPPORT_PARTIAL,
                slot_verdict=VERDICT_INCOMPLETE,
                matched=["context"],
                missing=["subject", "action", "location"],
            ),
        ]

        assembly = build_scene_assembly(
            scene={"scene_id": "scene_composite"},
            ranked_candidates=candidates,
            scene_duration_sec=8.0,
            mode=MODE_DRAFT_COMPLETE,
            requested_slot_count=4,
        )

        self.assertEqual(len(assembly.slots), 4)
        self.assertEqual(assembly.quality_tier, TIER_COMPOSITE)
        self.assertEqual(assembly.validate(), [])

    def test_partial_precedes_generated_and_tier_order_is_a_to_f(self) -> None:
        partial = _candidate(
            "partial",
            support=SUPPORT_PARTIAL,
            slot_verdict=VERDICT_INCOMPLETE,
            missing=["subject"],
        )
        generated = _candidate(
            "generated",
            provider="generated",
            support=SUPPORT_FULL,
            variant="infographic",
        )

        assembly = build_scene_assembly(
            scene={"scene_id": "scene_001"},
            ranked_candidates=[generated, partial],
            scene_duration_sec=4.0,
            mode=MODE_DRAFT_COMPLETE,
        )

        self.assertEqual(assembly.primary_asset["asset_id"], "partial")
        self.assertEqual(assembly.quality_tier, TIER_PARTIAL)

    def test_tie_break_is_provider_order_independent_and_prefers_exact_location(self) -> None:
        exact_location = _candidate(
            "z_location",
            matched=["place"],
            details=[
                {
                    "name": "location",
                    "kind": "location",
                    "required": True,
                    "status": "matched",
                }
            ],
        )
        context_only = _candidate(
            "a_context",
            matched=["place"],
            details=[
                {
                    "name": "context",
                    "kind": "context",
                    "required": True,
                    "status": "matched",
                }
            ],
        )

        first = order_candidates([context_only, exact_location])[0]["asset_id"]
        second = order_candidates([exact_location, context_only])[0]["asset_id"]

        self.assertEqual(first, "z_location")
        self.assertEqual(second, "z_location")

    def test_reuse_obeys_gap_and_max_and_records_alternate_crop(self) -> None:
        candidate = _candidate("repeat")
        ledger = ReuseLedger(max_uses=2, min_scene_gap=1)
        ledger.record("repeat", 0, "scene_000")

        immediate = build_scene_assembly(
            scene={"scene_id": "scene_001"},
            ranked_candidates=[candidate],
            scene_duration_sec=4.0,
            mode=MODE_DRAFT_COMPLETE,
            scene_index=1,
            reuse=ledger,
        )
        self.assertFalse(immediate.slots)

        reused = build_scene_assembly(
            scene={"scene_id": "scene_002"},
            ranked_candidates=[candidate],
            scene_duration_sec=4.0,
            mode=MODE_DRAFT_COMPLETE,
            scene_index=2,
            reuse=ledger,
        )
        self.assertEqual(reused.quality_tier, TIER_EMERGENCY)
        self.assertEqual(reused.slots[0].reuse_of_asset, "repeat")
        self.assertIn("reuse_transform", reused.slots[0].crop_decision)
        self.assertEqual(ledger.count("repeat"), 2)

        over_limit = build_scene_assembly(
            scene={"scene_id": "scene_004"},
            ranked_candidates=[candidate],
            scene_duration_sec=4.0,
            mode=MODE_DRAFT_COMPLETE,
            scene_index=4,
            reuse=ledger,
        )
        self.assertFalse(over_limit.slots)

    def test_reuse_penalty_prefers_fresh_equal_candidate(self) -> None:
        reused = _candidate("a_reused")
        fresh = _candidate("z_fresh")
        ledger = ReuseLedger()
        ledger.record("a_reused", 0, "scene_000")

        ordered = order_candidates([reused, fresh], reuse=ledger)

        self.assertEqual(ordered[0]["asset_id"], "z_fresh")

    def test_reuse_identity_prefers_checksum_over_alias_asset_ids(self) -> None:
        checksum = "a" * 64
        first = _candidate("provider_alias_a")
        second = _candidate("provider_alias_b")
        first["checksum_sha256"] = checksum
        second["checksum_sha256"] = checksum
        ledger = ReuseLedger(max_uses=2, min_scene_gap=1)
        ledger.record(first, 0, "scene_000")

        self.assertEqual(reuse_identity(first), f"sha256:{checksum}")
        self.assertEqual(reuse_identity(second), reuse_identity(first))
        self.assertEqual(ledger.count(second), 1)
        self.assertFalse(ledger.can_use(second, 1))

        reused = build_scene_assembly(
            scene={"scene_id": "scene_002"},
            ranked_candidates=[second],
            scene_duration_sec=4.0,
            mode=MODE_DRAFT_COMPLETE,
            scene_index=2,
            reuse=ledger,
        )
        self.assertEqual(reused.quality_tier, TIER_EMERGENCY)
        self.assertEqual(reused.slots[0].reuse_of_asset, "provider_alias_b")
        self.assertEqual(ledger.count(first), 2)
        self.assertFalse(ledger.can_use(second, 4))

    def test_emergency_factory_obeys_reuse_policy_but_unique_backdrops_remain_usable(self) -> None:
        repeated = _candidate(
            "repeated_backdrop",
            provider="generated",
            support=SUPPORT_PARTIAL,
            slot_verdict=VERDICT_PARTIAL,
            variant="backdrop",
        )
        repeated["checksum_sha256"] = "b" * 64
        ledger = ReuseLedger(max_uses=2, min_scene_gap=1)

        first = build_scene_assembly(
            scene={"scene_id": "scene_000"},
            ranked_candidates=[],
            scene_duration_sec=4.0,
            mode=MODE_DRAFT_COMPLETE,
            scene_index=0,
            reuse=ledger,
            emergency_asset_factory=lambda _scene: repeated,
        )
        adjacent = build_scene_assembly(
            scene={"scene_id": "scene_001"},
            ranked_candidates=[],
            scene_duration_sec=4.0,
            mode=MODE_DRAFT_COMPLETE,
            scene_index=1,
            reuse=ledger,
            emergency_asset_factory=lambda _scene: repeated,
        )
        second = build_scene_assembly(
            scene={"scene_id": "scene_002"},
            ranked_candidates=[],
            scene_duration_sec=4.0,
            mode=MODE_DRAFT_COMPLETE,
            scene_index=2,
            reuse=ledger,
            emergency_asset_factory=lambda _scene: repeated,
        )
        over_limit = build_scene_assembly(
            scene={"scene_id": "scene_004"},
            ranked_candidates=[],
            scene_duration_sec=4.0,
            mode=MODE_DRAFT_COMPLETE,
            scene_index=4,
            reuse=ledger,
            emergency_asset_factory=lambda _scene: repeated,
        )

        self.assertTrue(first.slots)
        self.assertFalse(adjacent.slots)
        self.assertIn(
            "emergency_reuse_limit_reached:repeated_backdrop",
            adjacent.ladder_trace,
        )
        self.assertEqual(second.slots[0].reuse_of_asset, "repeated_backdrop")
        self.assertTrue(second.slots[0].reuse_reason)
        self.assertFalse(over_limit.slots)

        unique_ledger = ReuseLedger(max_uses=2, min_scene_gap=1)
        for index, checksum in enumerate(("c" * 64, "d" * 64)):
            unique = _candidate(
                f"unique_backdrop_{index}",
                provider="generated",
                support=SUPPORT_PARTIAL,
                slot_verdict=VERDICT_PARTIAL,
                variant="backdrop",
            )
            unique["checksum_sha256"] = checksum
            assembly = build_scene_assembly(
                scene={"scene_id": f"scene_unique_{index}"},
                ranked_candidates=[],
                scene_duration_sec=4.0,
                mode=MODE_DRAFT_COMPLETE,
                scene_index=index,
                reuse=unique_ledger,
                emergency_asset_factory=lambda _scene, asset=unique: asset,
            )
            self.assertTrue(assembly.slots)


class GeneratedInfographicTests(unittest.TestCase):
    def test_png_is_real_vertical_deterministic_and_project_owned(self) -> None:
        spec = InfographicSpec(
            title="Confirmed sample",
            headline_value="54%",
            caption="topsoil sites",
            total_points=10,
            active_points=5,
            points_label="confirmed observations",
            scene_id="scene_004",
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = build_generated_asset(
                spec,
                project_root=root / "first",
                project_id="offline-project",
                scene_id="scene_004",
            )
            second = build_generated_asset(
                spec,
                project_root=root / "second",
                project_id="offline-project",
                scene_id="scene_004",
            )
            first_bytes = Path(first["path"]).read_bytes()
            revised = build_generated_asset(
                InfographicSpec(
                    title="Confirmed sample",
                    headline_value="55%",
                    caption="topsoil sites",
                    scene_id="scene_004",
                ),
                project_root=root / "first",
                project_id="offline-project",
                scene_id="scene_004",
            )

            first_path = Path(first["path"])
            second_path = Path(second["path"])
            revised_path = Path(revised["path"])
            self.assertEqual(first_path.suffix, ".png")
            self.assertEqual(first_path.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")
            self.assertEqual(first_path.read_bytes(), second_path.read_bytes())
            self.assertEqual(first["checksum_sha256"], second["checksum_sha256"])
            self.assertNotEqual(first_path, revised_path)
            self.assertNotEqual(first["asset_id"], revised["asset_id"])
            self.assertEqual(first_path.read_bytes(), first_bytes)
            with Image.open(first_path) as rendered:
                self.assertEqual(rendered.format, "PNG")
                self.assertEqual(rendered.size, (1080, 1920))
                self.assertEqual(rendered.mode, "RGB")

            self.assertEqual(first["technical_validation"]["status"], "passed")
            self.assertEqual(first["technical_validation"]["codec"], "png")
            self.assertEqual(first["license"]["rights_status"], "user_owned")
            self.assertTrue(first["license"]["allowed_for_render"])
            source_url = first["source_page_url"]
            self.assertTrue(source_url.startswith("project-generated://offline-project/"))
            self.assertEqual(first["provenance"]["source_page_url"], source_url)
            self.assertTrue(first["raw_metadata"]["generated_by_project"])
            self.assertTrue(Path(first["svg_path"]).is_file())

    def test_png_font_lookup_has_a_builtin_fallback(self) -> None:
        from src.assets import generated_infographic

        real_truetype = generated_infographic.ImageFont.truetype

        def reject_named_fonts(font: object, *args: object, **kwargs: object) -> object:
            if isinstance(font, (str, Path)):
                raise OSError("no system fonts")
            return real_truetype(font, *args, **kwargs)

        with patch.object(
            generated_infographic.ImageFont,
            "truetype",
            side_effect=reject_named_fonts,
        ):
            image = generated_infographic.render_png(
                InfographicSpec(title="Offline", scene_id="scene_001")
            )
        self.assertEqual(image.size, (1080, 1920))
        self.assertEqual(image.mode, "RGB")


class MultiSlotRendererTests(unittest.TestCase):
    def test_strict_renderer_reauthorizes_current_asset_snapshot(self) -> None:
        from src.news.final_renderer import _create_scene_segments

        for mutation, expected_block in (
            ("bytes_replaced", BLOCK_TECHNICAL),
            ("checksums_removed", BLOCK_TECHNICAL),
            ("rights_revoked", BLOCK_RIGHTS),
        ):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                segments_dir = root / "segments"
                segments_dir.mkdir()
                source = root / "safe.bmp"
                Image.new("RGB", (32, 32), "green").save(source)
                asset = _candidate("safe", path=str(source))
                digest = hashlib.sha256(source.read_bytes()).hexdigest()
                asset["checksum_sha256"] = digest
                asset["provenance"] = {"checksum_sha256": digest}
                slot = VisualSlot(
                    slot_id="slot_001",
                    purpose=SLOT_PRIMARY,
                    start_offset_sec=0.0,
                    end_offset_sec=2.0,
                    selected_asset=asset,
                    support_status=SUPPORT_FULL,
                    quality_tier=TIER_EXACT,
                    usability=UsabilityVerdict(
                        usable_in_draft=True,
                        automatic_render_allowed=True,
                        publish_ready=True,
                        quality_tier=TIER_EXACT,
                        support_status=SUPPORT_FULL,
                    ),
                )
                assembly = SceneVisualAssembly(
                    scene_id="scene_001",
                    scene_duration_sec=2.0,
                    slots=[slot],
                )
                manifest = {
                    "scenes": [
                        {
                            "scene_id": "scene_001",
                            "selected_asset": asset,
                            ASSEMBLY_KEY: assembly.to_dict(),
                        }
                    ]
                }
                stored = manifest["scenes"][0][ASSEMBLY_KEY]["slots"][0]["selected_asset"]
                first_readiness = evaluate_usability(
                    stored,
                    mode=MODE_STRICT,
                    quality_tier=TIER_EXACT,
                    require_local_file=True,
                )
                self.assertTrue(first_readiness.publish_ready)
                source_stat = source.stat()

                if mutation == "rights_revoked":
                    stored["allowed_for_render"] = False
                else:
                    replacement = root / "replacement.bmp"
                    Image.new("RGB", (32, 32), "red").save(replacement)
                    self.assertEqual(replacement.stat().st_size, source_stat.st_size)
                    source.write_bytes(replacement.read_bytes())
                    os.utime(
                        source,
                        ns=(source_stat.st_atime_ns, source_stat.st_mtime_ns),
                    )
                if mutation == "checksums_removed":
                    # Dropping the recorded expectation must not become the way to
                    # authorize whatever bytes now occupy the approved path.
                    stored.pop("checksum_sha256", None)
                    stored["provenance"].pop("checksum_sha256", None)

                with (
                    patch("src.news.final_renderer._render_image_segment") as render,
                    self.assertRaisesRegex(RuntimeError, expected_block),
                ):
                    _create_scene_segments(
                        segments_dir=segments_dir,
                        width=1080,
                        height=1920,
                        script={
                            "scenes": [
                                {"scene_id": "scene_001", "target_duration_sec": 2.0}
                            ]
                        },
                        assets_manifest=manifest,
                        completion_mode=MODE_STRICT,
                    )
                render.assert_not_called()

    def test_draft_renderer_recomputes_readiness_instead_of_trusting_stored_verdict(self) -> None:
        from src.news.final_renderer import _create_scene_segments

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            segments_dir = root / "segments"
            segments_dir.mkdir()
            source = root / "safe.png"
            Image.new("RGB", (32, 32), "green").save(source)
            asset = _candidate("safe", path=str(source))
            asset["checksum_sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
            stale_verdict = UsabilityVerdict(
                usable_in_draft=False,
                automatic_render_allowed=False,
                quality_tier=TIER_EXACT,
                support_status=SUPPORT_FULL,
            )
            slot = VisualSlot(
                slot_id="slot_001",
                purpose=SLOT_PRIMARY,
                start_offset_sec=0.0,
                end_offset_sec=2.0,
                selected_asset=asset,
                support_status=SUPPORT_FULL,
                quality_tier=TIER_EXACT,
                usability=stale_verdict,
            )
            assembly = SceneVisualAssembly(
                scene_id="scene_001",
                scene_duration_sec=2.0,
                slots=[slot],
            )
            manifest = {
                "scenes": [
                    {
                        "scene_id": "scene_001",
                        "selected_asset": asset,
                        ASSEMBLY_KEY: assembly.to_dict(),
                    }
                ]
            }
            script = {"scenes": [{"scene_id": "scene_001", "target_duration_sec": 2.0}]}

            with patch("src.news.final_renderer._render_image_segment"):
                segments = _create_scene_segments(
                    segments_dir=segments_dir,
                    width=1080,
                    height=1920,
                    script=script,
                    assets_manifest=manifest,
                    completion_mode=MODE_DRAFT_COMPLETE,
                )

            self.assertEqual(len(segments), 1)

            # The inverse stale record is also refused: stored true cannot override a
            # rights veto added to the actual selected asset.
            stored = manifest["scenes"][0][ASSEMBLY_KEY]["slots"][0]
            stored["usability"]["usable_in_draft"] = True
            stored["usability"]["automatic_render_allowed"] = True
            stored["selected_asset"]["allowed_for_render"] = False
            with self.assertRaisesRegex(RuntimeError, BLOCK_RIGHTS):
                _create_scene_segments(
                    segments_dir=segments_dir,
                    width=1080,
                    height=1920,
                    script=script,
                    assets_manifest=manifest,
                    completion_mode=MODE_DRAFT_COMPLETE,
                )

    def test_reuse_transform_changes_real_image_pixels_and_video_crop_mapping(self) -> None:
        from src.news.final_renderer import _base_frame, _video_filter

        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "split.png"
            image = Image.new("RGB", (200, 100), "red")
            image.paste(Image.new("RGB", (100, 100), "blue"), (100, 0))
            image.save(source)
            left_decision = {"reuse_transform": {"anchor": "left", "zoom": 1.08}}
            right_decision = {"reuse_transform": {"anchor": "right", "zoom": 1.08}}

            left = _base_frame(str(source), 50, 100, crop_decision=left_decision)
            right = _base_frame(str(source), 50, 100, crop_decision=right_decision)

        self.assertEqual(left.size, (50, 100))
        self.assertEqual(right.size, (50, 100))
        self.assertNotEqual(left.tobytes(), right.tobytes())
        self.assertIn("crop=1080:1920:0:(ih-oh)/2", _video_filter(1080, 1920, crop_decision=left_decision))
        self.assertIn(
            "crop=1080:1920:iw-ow:(ih-oh)/2",
            _video_filter(1080, 1920, crop_decision=right_decision),
        )

    def test_renderer_uses_every_stored_boundary_scaled_to_actual_duration(self) -> None:
        from src.news.final_renderer import _create_scene_segments

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            segments_dir = root / "segments"
            segments_dir.mkdir()
            first = root / "first.png"
            second = root / "second.png"
            Image.new("RGB", (32, 32), "red").save(first)
            Image.new("RGB", (32, 32), "blue").save(second)

            verdict = UsabilityVerdict(
                usable_in_draft=True,
                automatic_render_allowed=True,
                quality_tier=TIER_PARTIAL,
                support_status=SUPPORT_PARTIAL,
            )
            slots = []
            for slot_id, start, end, asset_id, path in (
                ("slot_a", 0.0, 1.2, "a", first),
                ("slot_b", 1.2, 4.0, "b", second),
            ):
                asset = _candidate(
                    asset_id,
                    support=SUPPORT_PARTIAL,
                    slot_verdict=VERDICT_PARTIAL,
                    path=str(path),
                )
                asset["checksum_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
                slots.append(
                    VisualSlot(
                        slot_id=slot_id,
                        purpose=SLOT_PRIMARY,
                        start_offset_sec=start,
                        end_offset_sec=end,
                        selected_asset=asset,
                        support_status=SUPPORT_PARTIAL,
                        quality_tier=TIER_PARTIAL,
                        usability=verdict,
                    )
                )
            assembly = SceneVisualAssembly(
                scene_id="scene_001",
                scene_duration_sec=4.0,
                assembly_status=ASSEMBLY_PARTIAL,
                completion_mode=MODE_DRAFT_COMPLETE,
                slots=slots,
            )
            manifest = {
                "scenes": [
                    {
                        "scene_id": "scene_001",
                        "selected_asset": slots[0].selected_asset,
                        ASSEMBLY_KEY: assembly.to_dict(),
                    }
                ]
            }
            script = {
                "scenes": [
                    {
                        "scene_id": "scene_001",
                        "target_duration_sec": 4.0,
                        "actual_duration_sec": 8.0,
                    }
                ]
            }

            with patch("src.news.final_renderer._render_image_segment"):
                segments = _create_scene_segments(
                    segments_dir=segments_dir,
                    width=1080,
                    height=1920,
                    script=script,
                    assets_manifest=manifest,
                    completion_mode=MODE_DRAFT_COMPLETE,
                )

        self.assertEqual(len(segments), 2)
        self.assertEqual([item["duration"] for item in segments], [2.4, 5.6])
        self.assertEqual(
            [(item["start_offset_sec"], item["end_offset_sec"]) for item in segments],
            [(0.0, 2.4), (2.4, 8.0)],
        )

    def test_renderer_refuses_zero_duration_before_invoking_ffmpeg(self) -> None:
        from src.news.final_renderer import _create_scene_segments

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            segments_dir = root / "segments"
            segments_dir.mkdir()
            source = root / "safe.png"
            Image.new("RGB", (32, 32), "green").save(source)
            asset = _candidate("safe", path=str(source))
            asset["checksum_sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
            slot = VisualSlot(
                slot_id="slot_001",
                purpose=SLOT_PRIMARY,
                start_offset_sec=0.0,
                end_offset_sec=2.0,
                selected_asset=asset,
                support_status=SUPPORT_FULL,
                quality_tier=TIER_EXACT,
                usability=UsabilityVerdict(),
            )
            assembly = SceneVisualAssembly(
                scene_id="scene_001",
                scene_duration_sec=2.0,
                slots=[slot],
            )
            manifest = {
                "scenes": [
                    {
                        "scene_id": "scene_001",
                        ASSEMBLY_KEY: assembly.to_dict(),
                    }
                ]
            }
            script = {
                "scenes": [
                    {"scene_id": "scene_001", "target_duration_sec": 2.0}
                ]
            }

            with (
                patch(
                    "src.assets.completion.assembly.scaled_slot_windows",
                    return_value=[(slot, 0.0, 0.0004)],
                ),
                patch("src.news.final_renderer._render_image_segment") as render,
            ):
                with self.assertRaisesRegex(RuntimeError, "non-positive render duration"):
                    _create_scene_segments(
                        segments_dir=segments_dir,
                        width=1080,
                        height=1920,
                        script=script,
                        assets_manifest=manifest,
                    )
                render.assert_not_called()

    def test_concat_file_escapes_apostrophe_for_ffmpeg_demuxer(self) -> None:
        from src.news.final_renderer import _write_concat_file

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            quoted_dir = root / "O'Brien"
            quoted_dir.mkdir()
            segment = quoted_dir / "segment.mp4"
            segment.write_bytes(b"segment")
            concat = root / "frames.txt"

            _write_concat_file(concat, [{"path": segment, "duration": 1.0}])

            normalized = str(segment.resolve()).replace("\\", "/")
            expected = f"file '{normalized.replace(chr(39), chr(39) + chr(92) + chr(39) + chr(39))}'\n"
            self.assertEqual(concat.read_text(encoding="utf-8"), expected)

    def test_optional_draft_mode_uses_draft_filenames_and_status(self) -> None:
        from src.news.final_renderer import render_final_video

        def fake_ffmpeg(args: list[str]) -> None:
            target = Path(args[-1])
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"fake mp4")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake_segment = root / "segment.mp4"
            fake_segment.write_bytes(b"segment")
            with (
                patch(
                    "src.news.final_renderer._create_scene_segments",
                    return_value=[
                        {
                            "path": fake_segment,
                            "duration": 2.0,
                            "scene_id": "scene_001",
                            "slot_id": "slot_001",
                            "quality_tier": TIER_PARTIAL,
                        }
                    ],
                ),
                patch("src.news.final_renderer._run_ffmpeg", side_effect=fake_ffmpeg),
                # This module checks draft naming, not video validity; the promotion
                # probe would reject the fake bytes above. Preservation semantics are
                # owned by tests/test_final_renderer_atomic_output.py.
                patch(
                    "src.news.final_renderer.ffprobe_media_info",
                    return_value={"status": "passed", "duration_sec": 2.0},
                ),
            ):
                manifest = render_final_video(
                    project_root=root,
                    language="en",
                    script={
                        "estimated_duration_sec": 2.0,
                        "scenes": [{"scene_id": "scene_001", "target_duration_sec": 2.0}],
                    },
                    visual_plan={"resolution": {"width": 1080, "height": 1920}},
                    assets_manifest={"scenes": []},
                    voice_manifest={},
                    completion_mode=MODE_DRAFT_COMPLETE,
                )

            output_dir = root / "localizations" / "en" / "output"
            self.assertEqual(manifest["status"], "completed")
            self.assertEqual(manifest["render_status"], "draft_completed")
            self.assertEqual(Path(manifest["output_path"]).name, "draft_1080x1920.mp4")
            self.assertTrue((output_dir / "draft_no_subtitles.mp4").is_file())
            self.assertFalse((output_dir / "youtube_shorts.mp4").exists())


if __name__ == "__main__":
    unittest.main()
