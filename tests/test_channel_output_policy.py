from __future__ import annotations

import unittest

from src.project_foundation.models import ChannelProfile, EvidenceSummary, ProjectManifest
from src.project_foundation.policies import ChannelOutputPolicy, validate


def _channel(**overrides) -> ChannelProfile:
    defaults = dict(
        channel_id="test_channel",
        supported_languages=["ru", "en"],
    )
    defaults.update(overrides)
    return ChannelProfile(**defaults)


def _project(**overrides) -> ProjectManifest:
    defaults = dict(
        project_id="proj_001",
        channel_id="test_channel",
        application_id="content_creator",
        format_id="vertical_short",
        template_id="story_card_text_only_v1",
        language="ru",
        export_targets=["youtube_shorts"],
    )
    defaults.update(overrides)
    return ProjectManifest(**defaults)


class ChannelOutputPolicyModelTests(unittest.TestCase):
    def test_roundtrip_serialization(self) -> None:
        policy = ChannelOutputPolicy(
            allowed_applications=["content_creator"],
            require_verified_evidence=True,
            minimum_resolution={"width": 1080, "height": 1920},
        )
        restored = ChannelOutputPolicy.from_dict(policy.to_dict())

        self.assertEqual(restored.allowed_applications, ["content_creator"])
        self.assertTrue(restored.require_verified_evidence)
        self.assertEqual(restored.minimum_resolution, {"width": 1080, "height": 1920})

    def test_default_values_are_permissive(self) -> None:
        policy = ChannelOutputPolicy()

        self.assertEqual(policy.allowed_applications, [])
        self.assertFalse(policy.require_verified_evidence)
        self.assertTrue(policy.allow_review_required_assets)
        self.assertFalse(policy.allow_unknown_license)


class ValidateOutputPolicyTests(unittest.TestCase):
    def test_fully_allowed_project_passes(self) -> None:
        policy = ChannelOutputPolicy(allow_unknown_license=True)
        result = validate(policy, _channel(), _project(), EvidenceSummary(total=1, verified=1))

        self.assertTrue(result.allowed)
        self.assertEqual(result.errors, [])

    def test_blocked_evidence_always_fails(self) -> None:
        policy = ChannelOutputPolicy(allow_unknown_license=True, allow_review_required_assets=True)
        result = validate(policy, _channel(), _project(), EvidenceSummary(total=1, blocked=1))

        self.assertFalse(result.allowed)
        self.assertTrue(any("blocked" in error for error in result.errors))

    def test_unknown_license_blocked_when_not_allowed(self) -> None:
        policy = ChannelOutputPolicy(allow_unknown_license=False)
        result = validate(policy, _channel(), _project(), EvidenceSummary(total=1, unknown=1))

        self.assertFalse(result.allowed)
        self.assertTrue(any("unknown license" in error for error in result.errors))

    def test_unknown_license_allowed_when_policy_permits(self) -> None:
        policy = ChannelOutputPolicy(allow_unknown_license=True)
        result = validate(policy, _channel(), _project(), EvidenceSummary(total=1, unknown=1))

        self.assertTrue(result.allowed)

    def test_review_required_blocked_when_not_allowed(self) -> None:
        policy = ChannelOutputPolicy(allow_review_required_assets=False)
        result = validate(policy, _channel(), _project(), EvidenceSummary(total=1, review_required=1))

        self.assertFalse(result.allowed)
        self.assertTrue(any("require review" in error for error in result.errors))

    def test_require_verified_evidence(self) -> None:
        policy = ChannelOutputPolicy(require_verified_evidence=True)
        result = validate(policy, _channel(), _project(), EvidenceSummary(total=2, verified=1, unknown=1))

        self.assertFalse(result.allowed)
        self.assertTrue(any("not verified" in error for error in result.errors))

    def test_application_not_in_allowlist_fails(self) -> None:
        policy = ChannelOutputPolicy(allowed_applications=["video_repurposer"], allow_unknown_license=True)
        result = validate(policy, _channel(), _project(), EvidenceSummary())

        self.assertFalse(result.allowed)
        self.assertTrue(any("application_id" in error for error in result.errors))

    def test_language_outside_channel_support_fails(self) -> None:
        policy = ChannelOutputPolicy(allow_unknown_license=True)
        project = _project(language="fr")
        result = validate(policy, _channel(supported_languages=["ru"]), project, EvidenceSummary())

        self.assertFalse(result.allowed)
        self.assertTrue(any("supported_languages" in error for error in result.errors))

    def test_export_target_not_allowed_fails(self) -> None:
        policy = ChannelOutputPolicy(allowed_export_targets=["tiktok"], allow_unknown_license=True)
        result = validate(policy, _channel(), _project(export_targets=["youtube_shorts"]), EvidenceSummary())

        self.assertFalse(result.allowed)
        self.assertTrue(any("export_targets" in error for error in result.errors))

    def test_duration_over_maximum_fails(self) -> None:
        policy = ChannelOutputPolicy(maximum_duration_seconds=60, allow_unknown_license=True)
        project = _project(metadata={"duration_seconds": 90})
        result = validate(policy, _channel(), project, EvidenceSummary())

        self.assertFalse(result.allowed)
        self.assertTrue(any("duration_seconds" in error for error in result.errors))

    def test_duration_missing_from_metadata_only_warns(self) -> None:
        policy = ChannelOutputPolicy(maximum_duration_seconds=60, allow_unknown_license=True)
        result = validate(policy, _channel(), _project(), EvidenceSummary())

        self.assertTrue(result.allowed)
        self.assertTrue(any("duration_seconds" in warning for warning in result.warnings))

    def test_minimum_resolution_violation_fails(self) -> None:
        policy = ChannelOutputPolicy(minimum_resolution={"width": 1080, "height": 1920}, allow_unknown_license=True)
        project = _project(metadata={"resolution": {"width": 640, "height": 480}})
        result = validate(policy, _channel(), project, EvidenceSummary())

        self.assertFalse(result.allowed)

    def test_require_voiceover_missing_metadata_warns_not_fails(self) -> None:
        policy = ChannelOutputPolicy(require_voiceover=True, allow_unknown_license=True)
        result = validate(policy, _channel(), _project(), EvidenceSummary())

        self.assertTrue(result.allowed)
        self.assertTrue(any("has_voiceover" in warning for warning in result.warnings))

    def test_require_voiceover_false_in_metadata_fails(self) -> None:
        policy = ChannelOutputPolicy(require_voiceover=True, allow_unknown_license=True)
        project = _project(metadata={"has_voiceover": False})
        result = validate(policy, _channel(), project, EvidenceSummary())

        self.assertFalse(result.allowed)

    def test_evaluated_rules_are_reported(self) -> None:
        policy = ChannelOutputPolicy(allow_unknown_license=True)
        result = validate(policy, _channel(), _project(), EvidenceSummary())

        self.assertIn("application", result.evaluated_rules)
        self.assertIn("evidence_blocked", result.evaluated_rules)
        self.assertIn("export_targets", result.evaluated_rules)


if __name__ == "__main__":
    unittest.main()
