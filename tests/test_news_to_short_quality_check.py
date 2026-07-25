from __future__ import annotations

import tempfile
import unittest
from pathlib import Path


class NewsToShortQualityCheckFoundationTests(unittest.TestCase):
    def _script(self) -> dict:
        return {
            "estimated_duration_sec": 45,
            "scenes": [
                {"scene_id": "scene_001", "narration": "one", "target_duration_sec": 5},
                {"scene_id": "scene_002", "narration": "two", "target_duration_sec": 5},
            ],
        }

    def test_quality_check_rejects_missing_local_file_for_new_manifest(self) -> None:
        from src.news.quality_check import run_quality_check

        report = run_quality_check(
            script=self._script(),
            research={"claims": []},
            assets_manifest={
                "schema_version": 1,
                "missing_scenes": [],
                "scenes": [
                    {
                        "scene_id": "scene_001",
                        "selected_asset": {
                            "asset_id": "asset_1",
                            "type": "video",
                            "path": "G:\\Projects\\AI-YouTube\\missing.mp4",
                            "allowed_for_render": True,
                            "review_required": False,
                            "checksum_sha256": "c" * 64,
                            "technical_validation": {"status": "passed"},
                            "license": {"rights_status": "licensed", "allowed_for_render": True, "review_required": False},
                            "provenance": {"provider": "fake", "source_page_url": "https://example.test/1"},
                        },
                    }
                ],
            },
            voice_manifest={"status": "completed"},
            subtitles_manifest={"srt_path": "subtitles.srt", "ass_path": "subtitles.ass"},
        )

        self.assertEqual(report["status"], "failed")
        self.assertIn("asset_local_file", {error["check"] for error in report["errors"]})

    def test_quality_check_passes_new_manifest_with_valid_local_files_rights_and_provenance(self) -> None:
        from src.news.quality_check import run_quality_check

        with tempfile.TemporaryDirectory() as tmp:
            first = Path(tmp) / "one.mp4"
            second = Path(tmp) / "two.jpg"
            first.write_bytes(b"local-video-placeholder")
            second.write_bytes(b"local-image-placeholder")
            scenes = []
            for scene_id, path, media_type in (("scene_001", first, "video"), ("scene_002", second, "image")):
                scenes.append(
                    {
                        "scene_id": scene_id,
                        "selected_asset": {
                            "asset_id": scene_id,
                            "schema_version": 1,
                            "provider": "fake",
                            "provider_asset_id": scene_id,
                            "type": media_type,
                            "media_type": media_type,
                            "path": str(path),
                            "downloaded_path": str(path),
                            "source_page_url": f"https://fake.local/assets/{scene_id}",
                            "allowed_for_render": True,
                            "review_required": False,
                            "checksum_sha256": "d" * 64,
                            "technical_validation": {"status": "passed"},
                            "license": {
                                "rights_status": "licensed",
                                "allowed_for_render": True,
                                "review_required": False,
                                "license_name": "fake_test_license",
                                "license_url": "https://fake.local/license",
                            },
                            "provenance": {
                                "provider": "fake",
                                "provider_asset_id": scene_id,
                                "source_page_url": f"https://fake.local/assets/{scene_id}",
                                "checksum_sha256": "d" * 64,
                            },
                        },
                    }
                )

            report = run_quality_check(
                script=self._script(),
                research={"claims": []},
                assets_manifest={"schema_version": 1, "missing_scenes": [], "scenes": scenes},
                voice_manifest={"status": "completed"},
                subtitles_manifest={"srt_path": "subtitles.srt", "ass_path": "subtitles.ass"},
            )

        self.assertEqual(report["status"], "passed")
        self.assertIn("asset_local_file", {check["check"] for check in report["checks"]})


if __name__ == "__main__":
    unittest.main()
