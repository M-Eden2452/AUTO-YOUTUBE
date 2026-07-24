from __future__ import annotations

import unittest

from src.project_foundation.models import (
    ChannelBranding,
    ChannelProfile,
    EvidenceRecord,
    EvidenceSummary,
    ProjectFoundationError,
    ProjectManifest,
)


class ChannelProfileModelTests(unittest.TestCase):
    def test_roundtrip_serialization(self) -> None:
        profile = ChannelProfile(
            channel_id="test_channel",
            display_name="Test Channel",
            default_language="ru",
            supported_languages=["ru", "en"],
            default_application="content_creator",
            default_format="vertical_short",
            default_template="story_card_text_only_v1",
            export_targets=["youtube_shorts"],
            branding=ChannelBranding(channel_name="Test", primary_font="Inter"),
        )
        restored = ChannelProfile.from_dict(profile.to_dict())

        self.assertEqual(restored.channel_id, "test_channel")
        self.assertEqual(restored.branding.primary_font, "Inter")
        self.assertEqual(restored.supported_languages, ["ru", "en"])
        self.assertEqual(restored.to_dict(), profile.to_dict())

    def test_default_values_are_safe(self) -> None:
        profile = ChannelProfile(channel_id="minimal")

        self.assertEqual(profile.display_name, "minimal")
        self.assertEqual(profile.default_language, "ru")
        self.assertEqual(profile.supported_languages, ["ru"])
        self.assertEqual(profile.export_targets, [])
        self.assertIsInstance(profile.branding, ChannelBranding)
        self.assertEqual(profile.branding.default_music_policy, "optional")
        self.assertTrue(profile.created_at)
        self.assertEqual(profile.updated_at, profile.created_at)
        self.assertEqual(profile.schema_version, 1)

    def test_missing_channel_id_raises(self) -> None:
        with self.assertRaises(ProjectFoundationError):
            ChannelProfile(channel_id="")

    def test_branding_accepts_dict(self) -> None:
        profile = ChannelProfile(channel_id="c1", branding={"channel_name": "C1", "logo_path": "logo.png"})

        self.assertIsInstance(profile.branding, ChannelBranding)
        self.assertEqual(profile.branding.channel_name, "C1")
        self.assertEqual(profile.branding.logo_path, "logo.png")


class ProjectManifestModelTests(unittest.TestCase):
    def test_roundtrip_serialization(self) -> None:
        manifest = ProjectManifest(
            project_id="proj_001",
            title="My Project",
            channel_id="test_channel",
            application_id="content_creator",
            format_id="vertical_short",
            template_id="story_card_text_only_v1",
            language="ru",
            export_targets=["youtube_shorts"],
            status="prepared",
            metadata={"duration_seconds": 45},
        )
        restored = ProjectManifest.from_dict(manifest.to_dict())

        self.assertEqual(restored.project_id, "proj_001")
        self.assertEqual(restored.status, "prepared")
        self.assertEqual(restored.metadata["duration_seconds"], 45)
        self.assertEqual(restored.to_dict(), manifest.to_dict())

    def test_default_values(self) -> None:
        manifest = ProjectManifest(project_id="proj_002")

        self.assertEqual(manifest.title, "proj_002")
        self.assertEqual(manifest.status, "draft")
        self.assertEqual(manifest.project_root, "projects/proj_002")
        self.assertEqual(manifest.localization_root, "projects/proj_002/localizations/ru")
        self.assertEqual(manifest.evidence_root, "projects/proj_002/evidence")
        self.assertEqual(manifest.metadata, {})
        self.assertTrue(manifest.created_at)

    def test_missing_project_id_raises(self) -> None:
        with self.assertRaises(ProjectFoundationError):
            ProjectManifest(project_id="")

    def test_invalid_status_raises(self) -> None:
        with self.assertRaises(ProjectFoundationError):
            ProjectManifest(project_id="proj_003", status="not_a_real_status")

    def test_invalid_metadata_type_raises(self) -> None:
        with self.assertRaises(ProjectFoundationError):
            ProjectManifest(project_id="proj_004", metadata="not-a-dict")  # type: ignore[arg-type]


class EvidenceRecordModelTests(unittest.TestCase):
    def test_roundtrip_serialization(self) -> None:
        record = EvidenceRecord(
            evidence_id="ev_001",
            asset_id="asset_001",
            source_url="https://example.test/asset/1",
            provider="pexels",
            license_name="pexels",
            verification_status="verified",
            checksum_sha256="a" * 64,
        )
        restored = EvidenceRecord.from_dict(record.to_dict())

        self.assertEqual(restored.evidence_id, "ev_001")
        self.assertEqual(restored.verification_status, "verified")
        self.assertEqual(restored.to_dict(), record.to_dict())

    def test_default_verification_status_is_unknown(self) -> None:
        record = EvidenceRecord(evidence_id="ev_002", asset_id="asset_002")

        self.assertEqual(record.verification_status, "unknown")
        self.assertEqual(record.proof_files, [])
        self.assertFalse(record.attribution_required)

    def test_missing_evidence_id_raises(self) -> None:
        with self.assertRaises(ProjectFoundationError):
            EvidenceRecord(evidence_id="")

    def test_invalid_verification_status_raises(self) -> None:
        with self.assertRaises(ProjectFoundationError):
            EvidenceRecord(evidence_id="ev_003", verification_status="not_a_real_status")


class EvidenceSummaryModelTests(unittest.TestCase):
    def test_to_dict(self) -> None:
        summary = EvidenceSummary(total=3, verified=1, review_required=1, blocked=1, unknown=0)

        self.assertEqual(
            summary.to_dict(),
            {"total": 3, "verified": 1, "review_required": 1, "blocked": 1, "unknown": 0},
        )


if __name__ == "__main__":
    unittest.main()
