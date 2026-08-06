"""An asset a person marked for rights review cannot be cleared by automation.

PLAN-STAB-5 / C50. The licence policy used to compute ``review_required`` purely from
its own rule table and then overwrite the record's flag with the answer, so a
local-library record marked for review left the canonical path allowed and renderable.
These tests pin the invariant in both directions: automation may tighten a rights
restriction, never loosen a recorded one, and the only thing that clears it is a
confirmed per-asset ``rights_declaration``.

The preservation is monotonic and does not ask where the requirement came from - owner
decision 2026-08-06, after evidence that a stored record cannot tell an operator's flag
apart from this policy's earlier answer. The accepted cost is that repairing metadata no
longer releases an asset on its own; that is pinned here as a contract, not a defect.

Offline: synthetic records only, no provider, no network, no real asset.
"""

from __future__ import annotations

import json
import unittest


SOURCE = "https://example.invalid/library/flagged"


def _local_library_record(**overrides) -> dict:
    """A current-schema local-library record the rule table would otherwise allow."""

    record = {
        "schema_version": 1,
        "id": "local_flagged",
        "asset_id": "local_flagged",
        "provider": "local_library",
        "provider_asset_id": "local_flagged",
        "type": "video",
        "media_type": "video",
        "local_path": "assets/library/videos/flagged.mp4",
        "source_url": SOURCE,
        "source_page_url": SOURCE,
        "rights_status": "user_owned",
        "allowed_for_render": True,
        "review_required": True,
        "license": {
            "license_name": "user_owned",
            "rights_status": "user_owned",
            "allowed_for_render": True,
            "review_required": True,
        },
        "provenance": {"provider": "local_library", "source_page_url": SOURCE},
        "width": 1080,
        "height": 1920,
    }
    record.update(overrides)
    return record


class ExplicitReviewRequirementTests(unittest.TestCase):
    """The record's own review requirement outranks anything the policy derives."""

    def test_the_policy_cannot_clear_a_requirement_the_record_states(self) -> None:
        """Matrix 1: explicit True beats a rule that says no review is needed."""
        from src.assets.license_policy import (
            RECORD_REVIEW_REQUIRED_REASON,
            evaluate_asset_policy,
        )

        decision = evaluate_asset_policy(_local_library_record())

        self.assertTrue(decision.review_required)
        self.assertFalse(decision.allowed_for_render)
        self.assertEqual(decision.status, "blocked")
        self.assertIn(RECORD_REVIEW_REQUIRED_REASON, decision.reason)

    def test_a_silent_nested_licence_does_not_clear_it(self) -> None:
        """Matrix 2: incomplete metadata is not permission - the stricter copy wins."""
        from src.assets.license_policy import (
            RECORD_REVIEW_REQUIRED_REASON,
            evaluate_asset_policy,
        )

        record = _local_library_record(
            license={
                "license_name": "user_owned",
                "rights_status": "user_owned",
                "allowed_for_render": True,
            }
        )

        decision = evaluate_asset_policy(record)

        self.assertTrue(decision.review_required)
        self.assertIn(RECORD_REVIEW_REQUIRED_REASON, decision.reason)

    def test_a_rule_that_says_nothing_about_review_does_not_clear_it(self) -> None:
        """Matrix 2: a derived value that is simply absent is not a decision to allow."""
        from src.assets.license_policy import (
            RECORD_REVIEW_REQUIRED_REASON,
            evaluate_asset_policy,
        )

        policy = {
            "policy_version": "test-policy",
            "policy_reviewed_date": "2026-08-06",
            "default_decision": {},
            "providers": {
                "local_library": {
                    "enabled": True,
                    "owner_review_required": False,
                    "owner_approval_status": "approved",
                    "rules": [
                        {
                            "media_type": "*",
                            "license_name": "user_owned",
                            "allowed_for_render": True,
                        }
                    ],
                }
            },
        }

        decision = evaluate_asset_policy(_local_library_record(), policy=policy)

        self.assertTrue(decision.review_required)
        self.assertFalse(decision.allowed_for_render)
        self.assertIn(RECORD_REVIEW_REQUIRED_REASON, decision.reason)

    def test_re_evaluating_the_candidate_keeps_the_requirement(self) -> None:
        """Matrix 3: running the policy again is not a way to launder the flag."""
        from src.assets.license_policy import (
            RECORD_REVIEW_REQUIRED_REASON,
            apply_policy_to_candidate,
        )
        from src.assets.models import AssetCandidate

        candidate = AssetCandidate.from_dict(_local_library_record())
        apply_policy_to_candidate(candidate)
        second = apply_policy_to_candidate(candidate)

        self.assertTrue(second.review_required)
        self.assertFalse(second.allowed_for_render)
        self.assertTrue(candidate.license.review_required)
        self.assertFalse(candidate.license.allowed_for_render)
        self.assertIn(RECORD_REVIEW_REQUIRED_REASON, second.reason)

    def test_repeated_application_is_idempotent(self) -> None:
        """Matrix 5: the third answer is the first answer."""
        from src.assets.license_policy import apply_policy_to_candidate
        from src.assets.models import AssetCandidate

        candidate = AssetCandidate.from_dict(_local_library_record())
        decisions = [apply_policy_to_candidate(candidate).to_dict() for _ in range(3)]

        self.assertEqual(decisions[0], decisions[1])
        self.assertEqual(decisions[1], decisions[2])

    def test_the_policy_can_still_add_a_requirement_the_record_denies(self) -> None:
        """Matrix 4: automation may tighten. Only loosening is forbidden."""
        from src.assets.license_policy import evaluate_asset_policy

        record = _local_library_record(
            review_required=False,
            license={
                "license_name": "user_owned",
                "rights_status": "user_owned",
                "allowed_for_render": True,
                "review_required": False,
            },
            source_url="",
            source_page_url="",
            provenance={"provider": "local_library"},
        )

        decision = evaluate_asset_policy(record)

        self.assertTrue(decision.review_required)
        self.assertFalse(decision.allowed_for_render)
        self.assertIn("missing_source", decision.reason)

    def test_the_reason_and_the_evidence_survive(self) -> None:
        """Matrix 8: why review is needed, and what it was based on, stay readable."""
        from src.assets.license_policy import (
            RECORD_REVIEW_REQUIRED_REASON,
            apply_policy_to_candidate,
        )
        from src.assets.models import AssetCandidate

        record = _local_library_record(
            schema_version=0,
            rights_declaration={"confirmation_status": "missing", "notes": "waiting for the owner"},
        )
        candidate = AssetCandidate.from_dict(record)
        decision = apply_policy_to_candidate(candidate)

        reasons = decision.reason.split("|")
        self.assertIn(RECORD_REVIEW_REQUIRED_REASON, reasons)
        self.assertIn("legacy_schema_version_0", reasons)
        self.assertEqual(candidate.policy_decision["reason"], decision.reason)
        self.assertEqual(candidate.rights_declaration["notes"], "waiting for the owner")
        self.assertEqual(candidate.provenance.source_page_url, SOURCE)

    def test_a_manifest_round_trip_keeps_the_requirement(self) -> None:
        """Matrix 6: serialise, deserialise, re-evaluate - still blocked."""
        from src.assets.license_policy import (
            RECORD_REVIEW_REQUIRED_REASON,
            apply_policy_to_candidate,
        )
        from src.assets.models import AssetCandidate

        candidate = AssetCandidate.from_dict(_local_library_record())
        apply_policy_to_candidate(candidate)

        stored = json.loads(json.dumps(candidate.to_manifest_dict()))
        self.assertTrue(stored["review_required"])
        self.assertTrue(stored["license"]["review_required"])

        restored = AssetCandidate.from_dict(stored)
        self.assertTrue(restored.license.review_required)

        decision = apply_policy_to_candidate(restored)
        self.assertTrue(decision.review_required)
        self.assertIn(RECORD_REVIEW_REQUIRED_REASON, decision.reason)

    def test_a_rebuild_from_the_stored_manifest_keeps_the_requirement(self) -> None:
        """Matrix 7: resume reads the stored asset and must reach the same verdict."""
        from src.assets.license_policy import evaluate_asset_policy
        from src.assets.models import AssetCandidate

        candidate = AssetCandidate.from_dict(_local_library_record())
        stored = candidate.to_manifest_dict()

        first = evaluate_asset_policy(stored)
        resumed = evaluate_asset_policy(AssetCandidate.from_dict(stored).to_manifest_dict())

        self.assertTrue(first.review_required)
        self.assertEqual(first.status, resumed.status)
        self.assertEqual(first.reason, resumed.reason)
        self.assertEqual(first.review_required, resumed.review_required)

    def test_the_render_gate_refuses_the_flagged_asset(self) -> None:
        """Matrix 9: the requirement reaches the point where render is refused."""
        from src.assets.models import AssetCandidate
        from src.assets.provider_contract import (
            LicenseReviewRequired,
            ensure_license_allows_render,
        )

        candidate = AssetCandidate.from_dict(_local_library_record())

        with self.assertRaises(LicenseReviewRequired) as raised:
            ensure_license_allows_render(candidate)

        self.assertIn("record_review_required", str(raised.exception))

    def test_absent_data_is_not_approval(self) -> None:
        """Matrix 10: a record that says nothing has not been cleared."""
        from src.assets.license_policy import evaluate_asset_policy

        decision = evaluate_asset_policy(
            {
                "schema_version": 1,
                "asset_id": "silent",
                "provider": "local_library",
                "type": "video",
                "license": {"license_name": "user_owned"},
            }
        )

        self.assertTrue(decision.review_required)
        self.assertFalse(decision.allowed_for_render)
        self.assertIn("missing_source", decision.reason)
        self.assertIn("missing_provider_asset_id", decision.reason)

    def test_a_legacy_record_without_the_field_is_read_and_stays_fail_closed(self) -> None:
        """Matrix 11: old manifests keep loading; absence never becomes permission."""
        from src.assets.license_policy import (
            RECORD_REVIEW_REQUIRED_REASON,
            evaluate_asset_policy,
        )

        legacy = {
            "id": "legacy_1",
            "provider": "local_library",
            "provider_asset_id": "legacy-1",
            "type": "video",
            "source_url": SOURCE,
            "path": "assets/library/videos/legacy.mp4",
            "license": "user_owned",
            "rights_status": "user_owned",
        }

        decision = evaluate_asset_policy(legacy)

        self.assertTrue(decision.review_required)
        self.assertFalse(decision.allowed_for_render)
        self.assertIn("legacy_schema_version_0", decision.reason)
        # Blocked by the existing schema rule, not by a requirement invented for it.
        self.assertNotIn(RECORD_REVIEW_REQUIRED_REASON, decision.reason)

    def test_one_flagged_asset_does_not_flag_its_neighbours(self) -> None:
        """Matrix 12: the requirement belongs to a record, not to the batch."""
        from src.assets.license_policy import (
            RECORD_REVIEW_REQUIRED_REASON,
            apply_policy_to_candidate,
        )
        from src.assets.models import AssetCandidate

        flagged = AssetCandidate.from_dict(_local_library_record())
        clean = AssetCandidate.from_dict(
            _local_library_record(
                id="local_clean",
                asset_id="local_clean",
                provider_asset_id="local_clean",
                review_required=False,
                license={
                    "license_name": "user_owned",
                    "rights_status": "user_owned",
                    "allowed_for_render": True,
                    "review_required": False,
                },
            )
        )

        flagged_decision = apply_policy_to_candidate(flagged)
        clean_decision = apply_policy_to_candidate(clean)

        self.assertTrue(flagged_decision.review_required)
        self.assertFalse(clean_decision.review_required)
        self.assertTrue(clean_decision.allowed_for_render)
        self.assertEqual(clean_decision.reason, "policy_rule_allowed")
        self.assertNotIn(RECORD_REVIEW_REQUIRED_REASON, clean_decision.reason)


class MonotonicMergeTests(unittest.TestCase):
    """One recorded ``True`` is enough, wherever the record happens to keep it.

    A stored record cannot say whether a review requirement came from an operator or
    from an earlier run of this policy, so the merge does not try to guess: it takes the
    stricter value from every representation the record actually carries.
    """

    def test_a_stale_allowing_decision_does_not_override_the_record(self) -> None:
        """The operator flagged an asset the policy had already allowed."""
        from src.assets.license_policy import (
            RECORD_REVIEW_REQUIRED_REASON,
            evaluate_asset_policy,
        )

        record = _local_library_record(
            policy_decision={
                "status": "allowed",
                "reason": "policy_rule_allowed",
                "allowed_for_render": True,
                "review_required": False,
            }
        )

        decision = evaluate_asset_policy(record)

        self.assertTrue(decision.review_required)
        self.assertFalse(decision.allowed_for_render)
        self.assertIn(RECORD_REVIEW_REQUIRED_REASON, decision.reason)

    def test_a_stale_blocking_decision_keeps_the_requirement(self) -> None:
        """A stored decision that asked for review is itself a recorded requirement."""
        from src.assets.license_policy import (
            RECORD_REVIEW_REQUIRED_REASON,
            evaluate_asset_policy,
        )

        record = _local_library_record(
            review_required=False,
            license={
                "license_name": "user_owned",
                "rights_status": "user_owned",
                "allowed_for_render": True,
                "review_required": False,
            },
            policy_decision={
                "status": "blocked",
                "reason": "missing_source",
                "allowed_for_render": False,
                "review_required": True,
            },
        )

        decision = evaluate_asset_policy(record)

        self.assertTrue(decision.review_required)
        self.assertFalse(decision.allowed_for_render)
        self.assertIn(RECORD_REVIEW_REQUIRED_REASON, decision.reason)

    def test_the_root_flag_alone_is_enough(self) -> None:
        from src.assets.license_policy import evaluate_asset_policy

        record = _local_library_record(
            license={
                "license_name": "user_owned",
                "rights_status": "user_owned",
                "allowed_for_render": True,
                "review_required": False,
            }
        )

        self.assertTrue(evaluate_asset_policy(record).review_required)

    def test_the_nested_flag_alone_is_enough(self) -> None:
        from src.assets.license_policy import evaluate_asset_policy

        record = _local_library_record(review_required=False)

        self.assertTrue(evaluate_asset_policy(record).review_required)

    def test_a_derived_block_converges_and_stays_converged(self) -> None:
        """f(f(x)) == f(x): the second answer is also the third and the fourth."""
        from src.assets.license_policy import apply_policy_to_candidate
        from src.assets.models import AssetCandidate

        record = _local_library_record(
            review_required=False,
            license={
                "license_name": "user_owned",
                "rights_status": "user_owned",
                "allowed_for_render": True,
                "review_required": False,
            },
            source_url="",
            source_page_url="",
            provenance={"provider": "local_library"},
        )
        candidate = AssetCandidate.from_dict(record)

        decisions = [apply_policy_to_candidate(candidate).to_dict() for _ in range(4)]

        self.assertTrue(all(item["review_required"] for item in decisions))
        self.assertEqual(decisions[1], decisions[2])
        self.assertEqual(decisions[2], decisions[3])


class ExplicitHumanDecisionStillDecidesTests(unittest.TestCase):
    """The invariant hardens automation. It must not take the operator's own decision."""

    def test_a_confirmed_owner_declaration_still_clears_the_requirement(self) -> None:
        """The manual-asset path marks the candidate for review and relies on this."""
        from src.assets.license_policy import evaluate_asset_policy

        record = _local_library_record(
            provider="user",
            provider_asset_id="user_asset_001",
            id="user_asset_001",
            asset_id="user_asset_001",
            rights_declaration={
                "confirmed": True,
                "owner_approval_status": "approved",
                "notes": "Owner confirmed the rights for this file.",
            },
        )

        decision = evaluate_asset_policy(record)

        self.assertFalse(decision.review_required)
        self.assertTrue(decision.allowed_for_render)
        self.assertEqual(decision.reason, "policy_rule_allowed")

    def test_an_unconfirmed_declaration_does_not_clear_it(self) -> None:
        from src.assets.license_policy import evaluate_asset_policy

        record = _local_library_record(
            provider="user",
            provider_asset_id="user_asset_002",
            id="user_asset_002",
            asset_id="user_asset_002",
            rights_declaration={"confirmation_status": "missing"},
        )

        decision = evaluate_asset_policy(record)

        self.assertTrue(decision.review_required)
        self.assertFalse(decision.allowed_for_render)
        self.assertIn("manual_rights_not_confirmed", decision.reason)

    def test_supplying_the_missing_metadata_does_not_clear_the_review(self) -> None:
        """The accepted cost of the fail-closed rule, pinned so it cannot drift back.

        Owner decision 2026-08-06: repairing the metadata that caused a block no longer
        releases the asset by itself. Distinguishing an operator's own flag from this
        policy's earlier answer is not something a stored record supports, and guessing
        at it is what let a flagged asset through. The operator confirms, or it stays.
        """
        from src.assets.license_policy import (
            RECORD_REVIEW_REQUIRED_REASON,
            apply_policy_to_candidate,
        )
        from src.assets.models import AssetCandidate

        record = _local_library_record(
            review_required=False,
            license={
                "license_name": "user_owned",
                "rights_status": "user_owned",
                "allowed_for_render": True,
                "review_required": False,
            },
        )
        record.pop("provider_asset_id")
        candidate = AssetCandidate.from_dict(record)

        blocked = apply_policy_to_candidate(candidate)
        self.assertTrue(blocked.review_required)
        self.assertIn("missing_provider_asset_id", blocked.reason)
        self.assertNotIn(RECORD_REVIEW_REQUIRED_REASON, blocked.reason)

        candidate.provider_asset_id = "local_flagged"
        repaired = apply_policy_to_candidate(candidate)

        self.assertTrue(repaired.review_required)
        self.assertFalse(repaired.allowed_for_render)
        self.assertNotIn("missing_provider_asset_id", repaired.reason)
        self.assertIn(RECORD_REVIEW_REQUIRED_REASON, repaired.reason)

        # ...and the operator's confirmation is the way out.
        candidate.rights_declaration = {"confirmed": True, "owner_approval_status": "approved"}
        confirmed = apply_policy_to_candidate(candidate)

        self.assertFalse(confirmed.review_required)
        self.assertTrue(confirmed.allowed_for_render)


class RecordReviewFlagSurvivesNormalisationTests(unittest.TestCase):
    """The flag must still be there when the record reaches the policy."""

    def test_ranking_a_local_library_record_carries_its_review_flag(self) -> None:
        import tempfile
        from pathlib import Path

        from src.media_library import register_asset
        from src.news.asset_manifest_builder import rank_local_assets

        with tempfile.TemporaryDirectory() as tmp:
            media = Path(tmp) / "flagged.mp4"
            media.write_bytes(b"synthetic")
            index: dict = {"version": 1, "items": []}
            register_asset(
                index,
                {
                    "schema_version": 1,
                    "id": "local_flagged",
                    "type": "video",
                    "provider": "local_library",
                    "provider_asset_id": "local_flagged",
                    "local_path": str(media),
                    "source_url": SOURCE,
                    "source_page_url": SOURCE,
                    "keywords": ["ocean"],
                    "tags": ["ocean"],
                    "rights_status": "user_owned",
                    "allowed_for_render": True,
                    "review_required": True,
                    # The nested licence says nothing about review; the record does.
                    "license": {"license_name": "user_owned"},
                    "provenance": {"provider": "local_library", "source_page_url": SOURCE},
                    "width": 1080,
                    "height": 1920,
                    "duration": 5.0,
                },
            )

            ranked = rank_local_assets(
                index,
                {"primary_query": "ocean", "visual_type": "video", "target_duration_sec": 5.0},
                "",
                set(),
            )

        self.assertEqual(len(ranked), 1)
        self.assertTrue(ranked[0]["review_required"])
        self.assertFalse(ranked[0]["allowed_for_render"])
        self.assertEqual(ranked[0]["rights_score"], 0.0)
        self.assertIn("record_review_required", ranked[0]["policy_decision"]["reason"])

    def test_policy_decision_merge_keeps_a_flag_stored_beside_the_licence(self) -> None:
        from src.news.asset_provider_adapters import with_policy_decision

        item = dict(_local_library_record())
        item["license"] = {"license_name": "user_owned", "allowed_for_render": True}

        updated = with_policy_decision(item)

        self.assertTrue(updated["review_required"])
        self.assertFalse(updated["allowed_for_render"])
        self.assertEqual(updated["rights_score"], 0.0)
        self.assertIn("record_review_required", updated["policy_decision"]["reason"])


if __name__ == "__main__":
    unittest.main()
