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

    def test_template_fallback_warns_in_draft_and_blocks_strict(self) -> None:
        from src.assets.completion import MODE_DRAFT_COMPLETE, MODE_STRICT
        from src.news.quality_check import run_quality_check

        script = self._script()
        script.update(
            {
                "script_provider": "legacy_template",
                "script_metadata": {
                    "fallback_provider": "legacy_template",
                    "fallback_reason": "insufficient_source_material",
                },
            }
        )
        common = {
            "script": script,
            "research": {"claims": []},
            "assets_manifest": {"schema_version": 0, "missing_scenes": []},
            "voice_manifest": {"status": "completed"},
            "subtitles_manifest": {"srt_path": "subtitles.srt", "ass_path": "subtitles.ass"},
        }

        draft = run_quality_check(**common, completion_mode=MODE_DRAFT_COMPLETE)
        strict = run_quality_check(**common, completion_mode=MODE_STRICT)

        self.assertIn("script_source_truth", {item["check"] for item in draft["warnings"]})
        self.assertNotIn("script_source_truth", {item["check"] for item in draft["errors"]})
        self.assertIn("script_source_truth", {item["check"] for item in strict["errors"]})

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

    def test_video_first_image_fallback_warns_in_draft_and_blocks_strict(self) -> None:
        from src.assets.completion import (
            ASSEMBLY_EXACT,
            MODE_DRAFT_COMPLETE,
            MODE_STRICT,
            SLOT_PRIMARY,
            TIER_EXACT,
            SceneVisualAssembly,
            attach_assembly,
            evaluate_usability,
        )
        from src.assets.completion.assembly import slot_from_asset
        from src.news.quality_check import run_quality_check
        from tests.test_autonomous_completion_pipeline import _asset, _png

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image = _asset(
                path=_png(root / "image.png", 1),
                scene_id="scene_001",
            )
            assembly = SceneVisualAssembly(
                scene_id="scene_001",
                scene_duration_sec=5.0,
                assembly_status=ASSEMBLY_EXACT,
                completion_mode=MODE_DRAFT_COMPLETE,
                slots=[
                    slot_from_asset(
                        image,
                        slot_id="scene_001_slot_001",
                        purpose=SLOT_PRIMARY,
                        start_offset_sec=0.0,
                        end_offset_sec=5.0,
                        quality_tier=TIER_EXACT,
                        usability=evaluate_usability(
                            image,
                            mode=MODE_DRAFT_COMPLETE,
                            quality_tier=TIER_EXACT,
                            require_local_file=True,
                        ),
                    )
                ],
            )
            scene = {"scene_id": "scene_001", "required_duration_sec": 5.0}
            attach_assembly(scene, assembly)
            manifest = {
                "schema_version": 1,
                "visual_mode": "video_first",
                "video_first_policy": {
                    "enabled": True,
                    "minimum_video_clips": 1,
                    "minimum_video_duration_ratio": 0.4,
                },
                "missing_scenes": [],
                "scenes": [scene],
            }
            common = {
                "script": self._script(),
                "research": {"claims": []},
                "assets_manifest": manifest,
                "voice_manifest": {"status": "completed"},
                "subtitles_manifest": {"srt_path": "subtitles.srt", "ass_path": "subtitles.ass"},
            }

            draft = run_quality_check(**common, completion_mode=MODE_DRAFT_COMPLETE)
            strict = run_quality_check(**common, completion_mode=MODE_STRICT)

        self.assertIn(
            "video_first_coverage",
            {warning["check"] for warning in draft["warnings"]},
        )
        self.assertNotIn(
            "video_first_coverage",
            {error["check"] for error in draft["errors"]},
        )
        self.assertIn(
            "video_first_coverage",
            {error["check"] for error in strict["errors"]},
        )


if __name__ == "__main__":
    unittest.main()
