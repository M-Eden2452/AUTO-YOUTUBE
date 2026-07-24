from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class ProviderFoundationHardeningTests(unittest.TestCase):
    def test_license_policy_unknown_provider_is_blocked(self) -> None:
        from src.assets.license_policy import evaluate_asset_policy
        from src.assets.models import AssetCandidate, AssetLicense

        candidate = AssetCandidate(
            asset_id="unknown_001",
            provider="unknown_provider",
            provider_asset_id="remote-1",
            media_type="video",
            source_page_url="https://example.test/asset/1",
            download_url="https://example.test/asset/1.mp4",
            license=AssetLicense(
                license_name="unknown-license",
                rights_status="licensed",
                allowed_for_render=True,
                review_required=False,
            ),
        )

        decision = evaluate_asset_policy(candidate)

        self.assertFalse(decision.allowed_for_render)
        self.assertTrue(decision.review_required)
        self.assertIn("unknown_provider", decision.reason)

    def test_license_policy_missing_source_is_blocked(self) -> None:
        from src.assets.license_policy import evaluate_asset_policy
        from src.assets.models import AssetCandidate, AssetLicense

        candidate = AssetCandidate(
            asset_id="fake_001",
            provider="fake",
            provider_asset_id="fake-1",
            media_type="image",
            source_page_url="",
            download_url="https://fake.local/asset.jpg",
            license=AssetLicense(
                license_name="fake_test_license",
                rights_status="licensed",
                allowed_for_render=True,
                review_required=False,
            ),
        )

        decision = evaluate_asset_policy(candidate)

        self.assertFalse(decision.allowed_for_render)
        self.assertTrue(decision.review_required)
        self.assertIn("missing_source", decision.reason)

    def test_stock_policy_distinguishes_internal_and_public_product_contexts(self) -> None:
        from src.assets.license_policy import evaluate_asset_policy
        from src.assets.models import AssetCandidate, AssetLicense

        candidate = AssetCandidate(
            asset_id="pexels_video_1",
            provider="pexels",
            provider_asset_id="1",
            media_type="video",
            source_page_url="https://www.pexels.com/video/1/",
            download_url="https://videos.pexels.com/video.mp4",
            author_name="Pexels Author",
            license=AssetLicense(
                license_name="pexels",
                license_url="https://www.pexels.com/license/",
                provider_terms_url="https://www.pexels.com/terms-of-service/",
                rights_status="licensed",
                allowed_for_render=True,
                review_required=False,
            ),
        )

        internal = evaluate_asset_policy(candidate, context="internal_content_production")
        public = evaluate_asset_policy(candidate, context="public_multi_user_product")

        self.assertTrue(internal.allowed_for_render)
        self.assertFalse(internal.review_required)
        self.assertFalse(public.allowed_for_render)
        self.assertTrue(public.review_required)
        self.assertEqual(public.owner_approval_status, "commercial_audit_pending")

    def test_legacy_asset_is_review_required_even_when_legacy_fields_claim_allowed(self) -> None:
        from src.assets.license_policy import evaluate_asset_policy
        from src.assets.models import AssetCandidate

        candidate = AssetCandidate.from_dict(
            {
                "asset_id": "legacy_001",
                "provider": "local",
                "type": "video",
                "provider_asset_id": "legacy-1",
                "source_url": "file:///legacy.mp4",
                "path": "G:\\Projects\\AI-YouTube\\assets\\legacy.mp4",
                "license": "user_owned",
                "rights_status": "licensed",
                "allowed_for_render": True,
            }
        )

        decision = evaluate_asset_policy(candidate)

        self.assertFalse(decision.allowed_for_render)
        self.assertTrue(decision.review_required)
        self.assertIn("legacy_schema_version_0", decision.reason)

    def test_provider_diagnostics_without_network(self) -> None:
        from src.assets.provider_diagnostics import collect_provider_diagnostics

        with patch("requests.sessions.Session.request", side_effect=AssertionError("network used")):
            diagnostics = collect_provider_diagnostics(live=False)

        names = {item["provider"] for item in diagnostics["providers"]}
        self.assertIn("pexels", names)
        self.assertIn("pixabay", names)
        self.assertIn("fake", names)
        self.assertFalse(diagnostics["live"])
        for item in diagnostics["providers"]:
            self.assertIn("key_configured", item)
            self.assertNotIn("api_key", item)

    def test_media_migration_dry_run_does_not_write_real_index_and_output_is_valid(self) -> None:
        from src.media_library import migrate_media_library

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            media = root / "Библиотека" / "кит.mp4"
            media.parent.mkdir(parents=True)
            media.write_bytes(b"not-real-video-for-migration-dry-run")
            index_path = root / "media_index.json"
            original = {
                "version": 1,
                "items": [
                    {
                        "id": "legacy_complete",
                        "type": "video",
                        "provider": "pexels",
                        "source_url": "https://pexels.example/video/1",
                        "download_url": "https://cdn.example/video/1.mp4",
                        "local_path": str(media),
                        "license_note": "Pexels license",
                    },
                    {
                        "id": "duplicate_url",
                        "type": "video",
                        "provider": "pexels",
                        "source_url": "https://pexels.example/video/1",
                        "local_path": str(media),
                    },
                ],
            }
            index_path.write_text(json.dumps(original, ensure_ascii=False, indent=2), encoding="utf-8")
            before = index_path.read_text(encoding="utf-8")
            proposed_path = root / "proposed.json"
            report_path = root / "report.json"

            result = migrate_media_library(
                index_path=index_path,
                dry_run=True,
                output_path=proposed_path,
                report_path=report_path,
            )

            after = index_path.read_text(encoding="utf-8")
            proposal = json.loads(proposed_path.read_text(encoding="utf-8"))
            report = json.loads(report_path.read_text(encoding="utf-8"))

        self.assertEqual(before, after)
        self.assertTrue(result["dry_run"])
        self.assertEqual(proposal["schema_version"], 1)
        self.assertEqual(len(proposal["items"]), 2)
        self.assertEqual(report["records_total"], 2)
        self.assertIn("unknown_rights", report["items"][0]["classifications"])
        self.assertIn("duplicate_url", report["items"][1]["classifications"])
        self.assertIn("кит.mp4", report["items"][0]["local_path"])

    def test_media_migration_apply_requires_confirmation(self) -> None:
        from src.media_library import migrate_media_library

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            index_path = root / "media_index.json"
            index_path.write_text(json.dumps({"version": 1, "items": []}), encoding="utf-8")

            with self.assertRaises(PermissionError):
                migrate_media_library(
                    index_path=index_path,
                    apply=True,
                    confirm_apply=False,
                    output_path=root / "proposed.json",
                    backup_path=root / "backup.json",
                )


if __name__ == "__main__":
    unittest.main()
