"""Stage C3: the Story Card workflow records what it actually rendered.

Before this, story_card_text_only_v1 could produce a finished MP4 while
`project rights-report` showed zero materials - the workflow never wrote the
provenance of the file it used. These tests cover the whole chain: the adapter
that describes a material, the integration that stores it in the project's
existing EvidenceBundle, and the unified rights report that reads it back.

No network, no downloads, no Vision, no TTS, no paid API: provider assets are
mock objects and every file is created under tempfile.
"""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image

from src.assets.evidence_adapter import AssetEvidenceError, build_asset_evidence_record
from src.assets.models import AssetCandidate, AssetLicense, AssetProvenance, DownloadedAsset
from src.project_foundation.channels import ChannelRegistry
from src.project_foundation.evidence import EvidenceBundle
from src.project_foundation.models import (
    EVIDENCE_RECORD_SCHEMA_VERSION,
    VERIFICATION_REVIEW_REQUIRED,
    VERIFICATION_UNKNOWN,
    VERIFICATION_VERIFIED,
    ChannelProfile,
    EvidenceRecord,
)
from src.project_foundation.projects import ProjectFactory
from src.projects import build_rights_report
from src.projects.repository import PROJECT_KIND_PROJECT_MANIFEST
from src.templates.story_card import (
    RENDER_STATUS_DRY_RUN,
    RENDER_STATUS_PREPARED,
    StoryCardIntegrationError,
    prepare_story_card_render,
)
from src.templates.story_card.integration import STORY_CARD_VISUAL_EVIDENCE_ID

from tests.test_story_card_project_integration import _write_tiny_preset


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _make_image(path: Path, colour: tuple[int, int, int] = (10, 20, 30)) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (16, 16), colour).save(path, format="PNG")
    return path


def _mock_provider_asset(local_path: Path) -> DownloadedAsset:
    """A fully described provider asset - built in memory, nothing is downloaded."""
    candidate = AssetCandidate(
        asset_id="pexels_12345",
        provider="pexels",
        provider_asset_id="12345",
        media_type="image",
        title="Snowy forest",
        source_page_url="https://www.pexels.com/photo/12345/",
        download_url="https://images.pexels.com/photos/12345/file.jpg",
        author_name="Jane Photographer",
        author_url="https://www.pexels.com/@jane",
        original_filename="file.jpg",
        license=AssetLicense(
            license_name="Pexels License",
            license_url="https://www.pexels.com/license/",
            rights_status="cleared",
            commercial_use_allowed=True,
            modification_allowed=True,
            attribution_required=False,
            attribution_text="Photo by Jane Photographer on Pexels",
            allowed_for_render=True,
            review_required=False,
        ),
        provenance=AssetProvenance(
            provider="pexels",
            provider_asset_id="12345",
            source_page_url="https://www.pexels.com/photo/12345/",
            download_url="https://images.pexels.com/photos/12345/file.jpg",
            original_filename="file.jpg",
            downloaded_at="2026-07-25T10:00:00Z",
            search_query="snowy forest",
            metadata_snapshot={"width": 1920, "height": 1080},
        ),
    )
    return DownloadedAsset.from_candidate(
        candidate,
        local_path=str(local_path),
        checksum_sha256=_sha256(local_path),
        downloaded_at="2026-07-25T10:00:00Z",
        technical_validation={"status": "passed", "media_type": "image", "width": 16, "height": 16},
    )


class AssetEvidenceAdapterTests(unittest.TestCase):
    def test_local_file_is_recorded_as_user_supplied_and_never_verified(self) -> None:
        with TemporaryDirectory() as tmp:
            asset = _make_image(Path(tmp) / "my_clip.png")
            record = build_asset_evidence_record(evidence_id="visual", local_path=asset)

            self.assertEqual(record.provider, "user_supplied")
            self.assertEqual(record.source_type, "user_supplied")
            self.assertEqual(record.media_role, "visual")
            self.assertEqual(record.commercial_use_status, "unknown")
            self.assertEqual(record.verification_status, VERIFICATION_REVIEW_REQUIRED)
            self.assertNotEqual(record.verification_status, VERIFICATION_VERIFIED)
            self.assertFalse(record.allowed_for_render)
            self.assertTrue(record.review_required)
            # Nothing is invented for a file we know nothing about.
            self.assertEqual(record.license_name, "")
            self.assertEqual(record.source_url, "")
            self.assertEqual(record.author, "")

    def test_checksum_is_computed_from_the_real_file(self) -> None:
        with TemporaryDirectory() as tmp:
            asset = _make_image(Path(tmp) / "clip.png")
            record = build_asset_evidence_record(evidence_id="visual", local_path=asset)
            self.assertEqual(record.checksum_sha256, _sha256(asset))
            self.assertEqual(len(record.checksum_sha256), 64)

    def test_provider_asset_keeps_licence_and_provenance(self) -> None:
        with TemporaryDirectory() as tmp:
            asset_path = _make_image(Path(tmp) / "file.jpg")
            record = build_asset_evidence_record(
                evidence_id="visual", local_path=asset_path, asset=_mock_provider_asset(asset_path)
            )

            self.assertEqual(record.provider, "pexels")
            self.assertEqual(record.provider_asset_id, "12345")
            self.assertEqual(record.asset_id, "pexels_12345")
            self.assertEqual(record.source_url, "https://www.pexels.com/photo/12345/")
            self.assertEqual(record.download_url, "https://images.pexels.com/photos/12345/file.jpg")
            self.assertEqual(record.author, "Jane Photographer")
            self.assertEqual(record.author_url, "https://www.pexels.com/@jane")
            self.assertEqual(record.license_name, "Pexels License")
            self.assertEqual(record.commercial_use_status, "allowed")
            self.assertEqual(record.source_type, "provider")
            self.assertTrue(record.allowed_for_render)
            self.assertFalse(record.review_required)
            self.assertEqual(record.verification_status, VERIFICATION_VERIFIED)
            # The raw provider blocks survive untouched.
            self.assertEqual(record.provenance["search_query"], "snowy forest")
            self.assertEqual(record.provenance["metadata_snapshot"], {"width": 1920, "height": 1080})
            self.assertEqual(record.technical_validation["status"], "passed")

    def test_provider_asset_dict_form_is_accepted_without_loss(self) -> None:
        with TemporaryDirectory() as tmp:
            asset_path = _make_image(Path(tmp) / "file.jpg")
            asset = _mock_provider_asset(asset_path)
            from_object = build_asset_evidence_record(evidence_id="v", local_path=asset_path, asset=asset)
            from_dict = build_asset_evidence_record(
                evidence_id="v", local_path=asset_path, asset=asset.to_dict()
            )
            self.assertEqual(from_object.to_dict(), from_dict.to_dict())

    def test_provider_asset_without_a_licence_is_not_verified(self) -> None:
        with TemporaryDirectory() as tmp:
            asset_path = _make_image(Path(tmp) / "file.jpg")
            asset = _mock_provider_asset(asset_path).to_dict()
            asset["license"]["license_name"] = ""
            record = build_asset_evidence_record(evidence_id="v", local_path=asset_path, asset=asset)
            self.assertNotEqual(record.verification_status, VERIFICATION_VERIFIED)

    def test_swapped_file_wins_over_the_checksum_recorded_for_the_candidate(self) -> None:
        with TemporaryDirectory() as tmp:
            original = _make_image(Path(tmp) / "original.jpg", colour=(1, 2, 3))
            asset = _mock_provider_asset(original)
            replacement = _make_image(Path(tmp) / "replacement.jpg", colour=(200, 100, 50))

            record = build_asset_evidence_record(evidence_id="v", local_path=replacement, asset=asset)

            self.assertEqual(record.checksum_sha256, _sha256(replacement))
            self.assertNotEqual(record.checksum_sha256, _sha256(original))
            self.assertEqual(Path(record.local_path), replacement.resolve())
            self.assertIn("does not match", record.notes)

    def test_missing_file_gives_a_clear_error(self) -> None:
        with TemporaryDirectory() as tmp:
            missing = Path(tmp) / "not_here.mp4"
            with self.assertRaises(AssetEvidenceError) as ctx:
                build_asset_evidence_record(evidence_id="v", local_path=missing)
            self.assertIn("not_here.mp4", str(ctx.exception))

    def test_unsupported_asset_type_is_rejected(self) -> None:
        with TemporaryDirectory() as tmp:
            asset_path = _make_image(Path(tmp) / "file.jpg")
            with self.assertRaises(AssetEvidenceError):
                build_asset_evidence_record(evidence_id="v", local_path=asset_path, asset=object())


class EvidenceRecordSchemaTests(unittest.TestCase):
    def test_v1_record_still_loads_and_keeps_its_derived_flags(self) -> None:
        v1 = {
            "evidence_id": "legacy",
            "provider": "wikimedia",
            "source_url": "https://commons.wikimedia.org/x",
            "license_name": "CC BY 4.0",
            "checksum_sha256": "a" * 64,
            "verification_status": VERIFICATION_VERIFIED,
            "schema_version": 1,
        }
        record = EvidenceRecord.from_dict(v1)
        self.assertEqual(record.schema_version, 1)
        self.assertEqual(record.media_role, "other")
        self.assertTrue(record.allowed_for_render)
        self.assertFalse(record.review_required)

    def test_new_records_declare_the_new_schema_version(self) -> None:
        self.assertEqual(EvidenceRecord(evidence_id="x").schema_version, EVIDENCE_RECORD_SCHEMA_VERSION)

    def test_round_trip_preserves_every_new_field(self) -> None:
        record = EvidenceRecord(
            evidence_id="x",
            media_role="visual",
            media_type="video",
            source_type="provider",
            provider_asset_id="42",
            download_url="https://example.test/a.mp4",
            author_url="https://example.test/author",
            allowed_for_render=True,
            review_required=False,
            provenance={"search_query": "q"},
            technical_validation={"status": "passed"},
        )
        self.assertEqual(EvidenceRecord.from_dict(record.to_dict()).to_dict(), record.to_dict())


class StoryCardWritesEvidenceTests(unittest.TestCase):
    def _project(self, tmp: Path):
        registry = ChannelRegistry(base_dir=tmp / "channels")
        channel = ChannelProfile(
            channel_id="provenance_test_channel",
            default_language="ru",
            supported_languages=["ru"],
            default_application="content_creator",
            default_format="vertical_short",
            default_template="story_card_text_only_v1",
            export_targets=["youtube_shorts"],
        )
        registry.create(channel)
        manifest = ProjectFactory(base_dir=tmp / "projects").create(
            channel, title="Provenance Project"
        ).manifest
        return channel, manifest

    def _prepare(self, tmp: Path, channel, manifest, source: Path, **kwargs):
        return prepare_story_card_render(
            manifest,
            channel=channel,
            source_asset_path=source,
            text={"top": "Верхний текст"},
            render_preset_path=_write_tiny_preset(tmp),
            dry_run=False,
            render=False,
            **kwargs,
        )

    def test_local_file_run_writes_one_evidence_record(self) -> None:
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            channel, manifest = self._project(tmp_path)
            source = _make_image(tmp_path / "source.png")

            result = self._prepare(tmp_path, channel, manifest, source)
            self.assertEqual(result.render_status, RENDER_STATUS_PREPARED)

            bundle = EvidenceBundle.load(manifest.project_root, manifest.project_id)
            self.assertEqual(len(bundle), 1)
            record = bundle.get(STORY_CARD_VISUAL_EVIDENCE_ID)
            self.assertEqual(record.media_role, "visual")
            self.assertEqual(record.source_type, "user_supplied")
            self.assertEqual(record.checksum_sha256, _sha256(source))
            self.assertNotEqual(record.verification_status, VERIFICATION_VERIFIED)

    def test_evidence_points_at_the_file_handed_to_the_renderer(self) -> None:
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            channel, manifest = self._project(tmp_path)
            source = _make_image(tmp_path / "source.png")

            result = self._prepare(tmp_path, channel, manifest, source)

            record = EvidenceBundle.load(manifest.project_root, manifest.project_id).get(
                STORY_CARD_VISUAL_EVIDENCE_ID
            )
            self.assertEqual(Path(record.local_path), Path(result.source_asset).resolve())
            render_request = json.loads(Path(result.render_request_path).read_text(encoding="utf-8"))
            self.assertEqual(Path(render_request["source_asset"]).resolve(), Path(record.local_path))
            # The render input and its rights record are explicitly tied together.
            self.assertEqual(render_request["evidence_id"], record.evidence_id)
            self.assertEqual(render_request["source_asset_checksum_sha256"], record.checksum_sha256)

    def test_a_different_file_on_a_second_run_replaces_the_record(self) -> None:
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            channel, manifest = self._project(tmp_path)
            first = _make_image(tmp_path / "first.png", colour=(1, 2, 3))
            second = _make_image(tmp_path / "second.png", colour=(200, 150, 100))

            self._prepare(tmp_path, channel, manifest, first)
            self._prepare(tmp_path, channel, manifest, second)

            bundle = EvidenceBundle.load(manifest.project_root, manifest.project_id)
            self.assertEqual(len(bundle), 1, "one visual means one record, not a growing pile")
            record = bundle.get(STORY_CARD_VISUAL_EVIDENCE_ID)
            self.assertEqual(record.checksum_sha256, _sha256(second))
            self.assertNotEqual(record.checksum_sha256, _sha256(first))

    def test_provider_asset_provenance_survives_the_workflow(self) -> None:
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            channel, manifest = self._project(tmp_path)
            source = _make_image(tmp_path / "file.jpg")

            self._prepare(tmp_path, channel, manifest, source, source_asset=_mock_provider_asset(source))

            record = EvidenceBundle.load(manifest.project_root, manifest.project_id).get(
                STORY_CARD_VISUAL_EVIDENCE_ID
            )
            self.assertEqual(record.provider, "pexels")
            self.assertEqual(record.provider_asset_id, "12345")
            self.assertEqual(record.license_name, "Pexels License")
            self.assertEqual(record.source_url, "https://www.pexels.com/photo/12345/")
            self.assertEqual(record.provenance["search_query"], "snowy forest")
            self.assertEqual(record.verification_status, VERIFICATION_VERIFIED)

    def test_dry_run_writes_nothing_at_all(self) -> None:
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            channel, manifest = self._project(tmp_path)
            source = _make_image(tmp_path / "source.png")

            result = prepare_story_card_render(
                manifest,
                channel=channel,
                source_asset_path=source,
                text={"top": "Верхний текст"},
                render_preset_path=_write_tiny_preset(tmp_path),
                dry_run=True,
            )

            self.assertEqual(result.render_status, RENDER_STATUS_DRY_RUN)
            self.assertFalse(EvidenceBundle.manifest_path(manifest.project_root).exists())

    def test_missing_source_asset_is_reported_clearly(self) -> None:
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            channel, manifest = self._project(tmp_path)
            with self.assertRaises(StoryCardIntegrationError) as ctx:
                self._prepare(tmp_path, channel, manifest, tmp_path / "nope.png")
            self.assertIn("nope.png", str(ctx.exception))
            self.assertFalse(EvidenceBundle.manifest_path(manifest.project_root).exists())

    def test_the_users_own_file_is_never_touched(self) -> None:
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            channel, manifest = self._project(tmp_path)
            source = _make_image(tmp_path / "precious.png")
            before = (source.read_bytes(), source.stat().st_size, source.stat().st_mtime_ns)

            self._prepare(tmp_path, channel, manifest, source)

            after = (source.read_bytes(), source.stat().st_size, source.stat().st_mtime_ns)
            self.assertEqual(before, after)

    def test_result_carries_a_short_rights_summary(self) -> None:
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            channel, manifest = self._project(tmp_path)
            source = _make_image(tmp_path / "source.png")

            result = self._prepare(tmp_path, channel, manifest, source)

            evidence = result.metadata["evidence"]
            self.assertEqual(evidence["source_type"], "user_supplied")
            self.assertEqual(evidence["rights_status"], VERIFICATION_REVIEW_REQUIRED)
            self.assertTrue(evidence["review_required"])
            self.assertTrue(Path(evidence["evidence_manifest_path"]).is_file())
            self.assertTrue(any("права" in w.lower() for w in result.warnings))


class UnifiedRightsReportSeesStoryCardTests(unittest.TestCase):
    def _report_for(self, tmp: Path, *, asset=None):
        registry = ChannelRegistry(base_dir=tmp / "channels")
        channel = ChannelProfile(
            channel_id="rights_report_channel",
            default_language="ru",
            supported_languages=["ru"],
            default_application="content_creator",
            default_format="vertical_short",
            default_template="story_card_text_only_v1",
            export_targets=["youtube_shorts"],
        )
        registry.create(channel)
        manifest = ProjectFactory(base_dir=tmp / "projects").create(channel, title="Report Project").manifest
        source = _make_image(tmp / "source.png")
        prepare_story_card_render(
            manifest,
            channel=channel,
            source_asset_path=source,
            source_asset=asset(source) if asset else None,
            text={"top": "Верхний текст"},
            render_preset_path=_write_tiny_preset(tmp),
            dry_run=False,
            render=False,
        )
        report = build_rights_report(
            project_id=manifest.project_id,
            project_root=manifest.project_root,
            project_kind=PROJECT_KIND_PROJECT_MANIFEST,
        )
        return report, source

    def test_report_is_no_longer_empty_for_a_new_story_card_project(self) -> None:
        with TemporaryDirectory() as tmp:
            report, source = self._report_for(Path(tmp))

            self.assertEqual(report.summary.total, 1)
            self.assertEqual(report.summary.visual_items, 1)
            self.assertEqual(report.summary.other_items, 0)
            item = report.items[0]
            self.assertEqual(item.media_role, "visual")
            self.assertEqual(item.provider, "user_supplied")
            self.assertEqual(item.checksum_sha256, _sha256(source))
            self.assertTrue(item.local_file_present)
            self.assertIn("evidence/evidence_manifest.json", report.sources_read)
            self.assertFalse(
                any("не записывает provenance" in warning for warning in report.warnings),
                "the old 'story card records nothing' warning must not fire for a project that does",
            )

    def test_user_supplied_material_is_never_reported_as_verified(self) -> None:
        with TemporaryDirectory() as tmp:
            report, _ = self._report_for(Path(tmp))

            self.assertEqual(report.summary.verified, 0)
            self.assertEqual(report.overall_status, VERIFICATION_REVIEW_REQUIRED)
            self.assertTrue(report.items[0].review_required)
            self.assertFalse(report.items[0].allowed_for_render)
            self.assertTrue(any("пользователем" in w for w in report.items[0].warnings))
            # Informational, not blocking: nothing is provably wrong.
            self.assertFalse(report.has_blocking_problems)

    def test_a_fully_described_provider_asset_can_reach_verified(self) -> None:
        with TemporaryDirectory() as tmp:
            report, _ = self._report_for(Path(tmp), asset=_mock_provider_asset)

            self.assertEqual(report.summary.verified, 1)
            self.assertEqual(report.overall_status, VERIFICATION_VERIFIED)
            item = report.items[0]
            self.assertEqual(item.provider, "pexels")
            self.assertEqual(item.provider_asset_id, "12345")
            self.assertEqual(item.license_name, "Pexels License")
            self.assertEqual(item.download_url, "https://images.pexels.com/photos/12345/file.jpg")

    def test_an_old_story_card_project_without_evidence_still_reads(self) -> None:
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            registry = ChannelRegistry(base_dir=tmp_path / "channels")
            channel = ChannelProfile(
                channel_id="legacy_channel",
                default_language="ru",
                supported_languages=["ru"],
                default_application="content_creator",
                default_format="vertical_short",
                default_template="story_card_text_only_v1",
                export_targets=["youtube_shorts"],
            )
            registry.create(channel)
            manifest = ProjectFactory(base_dir=tmp_path / "projects").create(
                channel, title="Legacy Project"
            ).manifest

            report = build_rights_report(
                project_id=manifest.project_id,
                project_root=manifest.project_root,
                project_kind=PROJECT_KIND_PROJECT_MANIFEST,
            )

            self.assertEqual(report.summary.total, 0)
            self.assertEqual(report.overall_status, VERIFICATION_UNKNOWN)
            self.assertTrue(any("evidence_manifest.json" in w for w in report.warnings))

    def test_a_v1_evidence_record_is_still_read_the_old_way(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            (root / "evidence").mkdir(parents=True)
            (root / "evidence" / "evidence_manifest.json").write_text(
                json.dumps(
                    {
                        "project_id": "p1",
                        "schema_version": 1,
                        "records": [
                            {
                                "evidence_id": "legacy_record",
                                "provider": "wikimedia",
                                "source_url": "https://commons.wikimedia.org/x",
                                "license_name": "CC BY 4.0",
                                "checksum_sha256": "b" * 64,
                                "verification_status": "verified",
                                "schema_version": 1,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            report = build_rights_report(
                project_id="p1", project_root=root, project_kind=PROJECT_KIND_PROJECT_MANIFEST
            )

            self.assertEqual(report.summary.total, 1)
            item = report.items[0]
            self.assertEqual(item.media_role, "other")
            self.assertEqual(item.verification_status, VERIFICATION_VERIFIED)
            self.assertTrue(item.allowed_for_render)


if __name__ == "__main__":
    unittest.main()
