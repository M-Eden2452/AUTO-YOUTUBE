from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.project_foundation.evidence import EvidenceBundle
from src.project_foundation.models import EvidenceRecord, ProjectFoundationError


def _verified_record(evidence_id: str = "ev_001", asset_id: str = "asset_001") -> EvidenceRecord:
    return EvidenceRecord(
        evidence_id=evidence_id,
        asset_id=asset_id,
        source_url="https://example.test/asset/1",
        provider="pexels",
        license_name="pexels",
        verification_status="verified",
        checksum_sha256="a" * 64,
    )


class EvidenceBundleTests(unittest.TestCase):
    def test_add_get_list(self) -> None:
        bundle = EvidenceBundle(project_id="proj_001")
        bundle.add(_verified_record())

        self.assertEqual(len(bundle), 1)
        self.assertEqual(bundle.get("ev_001").asset_id, "asset_001")
        self.assertEqual(bundle.get_by_asset_id("asset_001")[0].evidence_id, "ev_001")
        self.assertEqual([record.evidence_id for record in bundle.list()], ["ev_001"])

    def test_duplicate_evidence_id_rejected_without_overwrite(self) -> None:
        bundle = EvidenceBundle(project_id="proj_001")
        bundle.add(_verified_record())

        with self.assertRaises(ProjectFoundationError):
            bundle.add(_verified_record())

    def test_overwrite_flag_allows_replace(self) -> None:
        bundle = EvidenceBundle(project_id="proj_001")
        bundle.add(_verified_record())
        replaced = EvidenceRecord(evidence_id="ev_001", asset_id="asset_002", verification_status="blocked")

        bundle.add(replaced, overwrite=True)

        self.assertEqual(bundle.get("ev_001").asset_id, "asset_002")
        self.assertEqual(len(bundle), 1)

    def test_get_missing_raises(self) -> None:
        bundle = EvidenceBundle(project_id="proj_001")

        with self.assertRaises(ProjectFoundationError):
            bundle.get("does_not_exist")

    def test_validate_flags_incomplete_verified_record(self) -> None:
        bundle = EvidenceBundle(project_id="proj_001")
        bundle.add(EvidenceRecord(evidence_id="ev_bad", verification_status="verified"))

        errors = bundle.validate()

        self.assertTrue(any("source_url" in error for error in errors))
        self.assertTrue(any("license_name" in error for error in errors))
        self.assertTrue(any("checksum_sha256" in error for error in errors))

    def test_validate_flags_missing_attribution_text(self) -> None:
        bundle = EvidenceBundle(project_id="proj_001")
        bundle.add(EvidenceRecord(evidence_id="ev_attr", attribution_required=True, attribution_text=""))

        errors = bundle.validate()

        self.assertTrue(any("attribution_text" in error for error in errors))

    def test_summary_counts_by_verification_status(self) -> None:
        bundle = EvidenceBundle(project_id="proj_001")
        bundle.add(EvidenceRecord(evidence_id="ev1", verification_status="verified"))
        bundle.add(EvidenceRecord(evidence_id="ev2", verification_status="review_required"))
        bundle.add(EvidenceRecord(evidence_id="ev3", verification_status="blocked"))
        bundle.add(EvidenceRecord(evidence_id="ev4", verification_status="unknown"))

        summary = bundle.summary()

        self.assertEqual(summary.total, 4)
        self.assertEqual(summary.verified, 1)
        self.assertEqual(summary.review_required, 1)
        self.assertEqual(summary.blocked, 1)
        self.assertEqual(summary.unknown, 1)

    def test_save_and_load_roundtrip_preserves_records(self) -> None:
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "proj_001"
            bundle = EvidenceBundle(project_id="proj_001")
            bundle.add(_verified_record("ev1", "asset1"))
            bundle.add(EvidenceRecord(evidence_id="ev2", asset_id="asset2", verification_status="unknown"))

            bundle.save(project_root)
            reloaded = EvidenceBundle.load(project_root, "proj_001")

            self.assertEqual(len(reloaded), 2)
            self.assertEqual({r.evidence_id for r in reloaded.list()}, {"ev1", "ev2"})
            self.assertTrue((project_root / "evidence" / "evidence_manifest.json").is_file())

    def test_updating_bundle_does_not_lose_previously_saved_records(self) -> None:
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "proj_001"
            bundle = EvidenceBundle(project_id="proj_001")
            bundle.add(_verified_record("ev1", "asset1"))
            bundle.save(project_root)

            reloaded = EvidenceBundle.load(project_root, "proj_001")
            reloaded.add(EvidenceRecord(evidence_id="ev2", asset_id="asset2"))
            reloaded.save(project_root)

            final = EvidenceBundle.load(project_root, "proj_001")
            self.assertEqual({r.evidence_id for r in final.list()}, {"ev1", "ev2"})

    def test_load_missing_manifest_returns_empty_bundle(self) -> None:
        with TemporaryDirectory() as tmp:
            bundle = EvidenceBundle.load(Path(tmp) / "no_such_project", "proj_missing")

            self.assertEqual(len(bundle), 0)
            self.assertEqual(bundle.project_id, "proj_missing")

    def test_corrupted_manifest_raises_clear_error(self) -> None:
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "proj_001"
            evidence_dir = project_root / "evidence"
            evidence_dir.mkdir(parents=True)
            (evidence_dir / "evidence_manifest.json").write_text("{not valid json", encoding="utf-8")

            with self.assertRaises(ProjectFoundationError):
                EvidenceBundle.load(project_root, "proj_001")

    def test_rights_report_groups_by_provider_and_license(self) -> None:
        bundle = EvidenceBundle(project_id="proj_001")
        bundle.add(_verified_record("ev1", "asset1"))
        bundle.add(EvidenceRecord(evidence_id="ev2", asset_id="asset2", provider="pexels", license_name="pexels", verification_status="review_required"))
        bundle.add(EvidenceRecord(evidence_id="ev3", asset_id="asset3", provider="wikimedia", license_name="cc-by", verification_status="blocked"))

        report = bundle.rights_report()

        self.assertEqual(report["by_provider"]["pexels"], 2)
        self.assertEqual(report["by_provider"]["wikimedia"], 1)
        self.assertEqual(report["summary"]["blocked"], 1)
        self.assertEqual(len(report["needs_attention"]), 2)

    def test_save_rights_report_writes_file(self) -> None:
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "proj_001"
            bundle = EvidenceBundle(project_id="proj_001")
            bundle.add(_verified_record())

            bundle.save_rights_report(project_root)

            self.assertTrue((project_root / "evidence" / "rights_report.json").is_file())


if __name__ == "__main__":
    unittest.main()
