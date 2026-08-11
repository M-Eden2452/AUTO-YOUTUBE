from __future__ import annotations

import unittest


class AssetFoundationModelTests(unittest.TestCase):
    def test_asset_candidate_roundtrip_preserves_license_provenance_and_unicode(self) -> None:
        from src.assets.models import AssetCandidate, AssetLicense, AssetProvenance

        license_data = AssetLicense(
            license_name="pexels",
            license_url="https://www.pexels.com/license/",
            provider_terms_url="https://www.pexels.com/terms-of-service/",
            rights_status="licensed",
            commercial_use_allowed=True,
            modification_allowed=True,
            attribution_required=False,
            attribution_text="Video by Тестовый автор on Pexels",
            allowed_for_render=True,
            review_required=False,
            notes="normalized provider license",
            checked_at="2026-07-22T19:00:00+00:00",
        )
        provenance = AssetProvenance(
            provider="pexels",
            provider_asset_id="видео_001",
            source_page_url="https://www.pexels.com/video/1/",
            download_url="https://videos.pexels.com/video.mp4",
            original_filename="ocean.mp4",
            downloaded_at="2026-07-22T19:01:00+00:00",
            checksum_sha256="a" * 64,
            project_id="проект_001",
            scene_id="scene_001",
            search_query="кит океан",
            metadata_snapshot={"raw": {"id": 1, "name": "Кит"}},
        )
        candidate = AssetCandidate(
            asset_id="pexels_video_1",
            provider="pexels",
            provider_asset_id="1",
            media_type="video",
            title="Кит в океане",
            description="ocean whale aerial",
            tags=["whale", "ocean"],
            source_page_url="https://www.pexels.com/video/1/",
            preview_url="https://images.pexels.com/preview.jpg",
            download_url="https://videos.pexels.com/video.mp4",
            author_name="Тестовый автор",
            author_url="https://www.pexels.com/@author",
            width=1080,
            height=1920,
            duration_sec=4.5,
            orientation="vertical",
            search_query="кит океан",
            local_path="G:\\Projects\\AI-YouTube\\tmp\\кит.mp4",
            original_filename="ocean.mp4",
            downloaded_at="2026-07-22T19:01:00+00:00",
            checksum_sha256="a" * 64,
            project_id="проект_001",
            scene_id="scene_001",
            license=license_data,
            provenance=provenance,
            raw_metadata={"provider_payload": {"id": 1}},
        )

        data = candidate.to_dict()
        loaded = AssetCandidate.from_dict(data)
        manifest = loaded.to_manifest_dict()

        self.assertEqual(data["schema_version"], 1)
        self.assertEqual(loaded.title, "Кит в океане")
        self.assertEqual(loaded.license.rights_status, "licensed")
        self.assertEqual(loaded.provenance.project_id, "проект_001")
        self.assertEqual(manifest["type"], "video")
        self.assertEqual(manifest["path"], "G:\\Projects\\AI-YouTube\\tmp\\кит.mp4")
        self.assertEqual(manifest["downloaded_path"], manifest["path"])
        self.assertEqual(manifest["source_page"], "https://www.pexels.com/video/1/")
        self.assertTrue(manifest["allowed_for_render"])
        self.assertFalse(manifest["review_required"])

    def test_legacy_manifest_without_schema_version_is_read_as_legacy_zero(self) -> None:
        from src.assets.models import AssetCandidate

        legacy = {
            "asset_id": "old_pixabay_1",
            "provider": "pixabay",
            "type": "video",
            "title": "legacy ocean",
            "source_url": "https://pixabay.com/videos/1/",
            "source_page": "https://pixabay.com/videos/1/",
            "download_url": "https://cdn.pixabay.com/video.mp4",
            "author": "Legacy Author",
            "license": "pixabay",
            "rights_status": "licensed",
            "allowed_for_render": True,
            "path": "G:\\Projects\\AI-YouTube\\assets\\legacy.mp4",
            "downloaded_path": "G:\\Projects\\AI-YouTube\\assets\\legacy.mp4",
            "width": 1920,
            "height": 1080,
            "duration": 8,
        }

        candidate = AssetCandidate.from_dict(legacy)
        manifest = candidate.to_manifest_dict()

        self.assertEqual(candidate.schema_version, 0)
        self.assertEqual(candidate.media_type, "video")
        self.assertEqual(candidate.source_page_url, "https://pixabay.com/videos/1/")
        self.assertEqual(candidate.author_name, "Legacy Author")
        self.assertEqual(candidate.license.license_name, "pixabay")
        self.assertEqual(candidate.license.rights_status, "licensed")
        self.assertEqual(manifest["path"], legacy["path"])
        self.assertEqual(manifest["license"]["rights_status"], "licensed")


if __name__ == "__main__":
    unittest.main()


class M1CAssetLineageModelTests(unittest.TestCase):
    def test_optional_lineage_and_vision_evidence_roundtrip(self) -> None:
        from src.assets.models import AssetCandidate

        candidate = AssetCandidate(
            asset_id="candidate_b",
            provider="fake",
            replaces_asset_id="candidate_a",
            vision_tags=["ocean", "whale"],
            vision_tags_asset_id="candidate_b",
            vision_tags_source_sha256="abc123",
            vision_tags_cache_key="semantic-cache-key",
        )
        loaded = AssetCandidate.from_dict(candidate.to_dict())

        self.assertEqual(loaded.replaces_asset_id, "candidate_a")
        self.assertEqual(loaded.vision_tags, ["ocean", "whale"])
        self.assertEqual(loaded.vision_tags_asset_id, "candidate_b")
        self.assertEqual(loaded.vision_tags_source_sha256, "abc123")
        self.assertEqual(loaded.vision_tags_cache_key, "semantic-cache-key")

    def test_legacy_candidate_without_optional_lineage_fields_still_reads(self) -> None:
        from src.assets.models import AssetCandidate

        loaded = AssetCandidate.from_dict(
            {"asset_id": "legacy", "provider": "local", "media_type": "image"}
        )

        self.assertEqual(loaded.replaces_asset_id, "")
        self.assertEqual(loaded.vision_tags, [])
        self.assertEqual(loaded.vision_tags_asset_id, "")
        self.assertEqual(loaded.vision_tags_source_sha256, "")
        self.assertEqual(loaded.vision_tags_cache_key, "")
