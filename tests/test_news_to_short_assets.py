from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image


class NewsToShortAssetTests(unittest.TestCase):
    def test_standard_news_manifest_never_creates_emergency_infographic(self) -> None:
        from src.news.asset_manager import build_news_asset_manifest

        plan = {
            "language": "ru",
            "scenes": [
                {
                    "scene_id": "scene_001",
                    "visual_type": "video",
                    "allowed_media_kinds": ["video", "image"],
                    "target_duration_sec": 4.0,
                    "primary_query": "orca",
                }
            ],
        }
        with tempfile.TemporaryDirectory() as tmp, patch(
            "src.news.asset_manager.create_default_asset_providers", return_value=[]
        ):
            manifest = build_news_asset_manifest(
                visual_plan=plan,
                user_assets=[],
                dry_run=False,
                project_root=tmp,
                project_id="video_first",
                completion_mode="draft_complete",
            )

        self.assertEqual(manifest["visual_mode"], "video_first")
        self.assertFalse(manifest["infographic_fallback"])
        self.assertIsNone(manifest["scenes"][0]["selected_asset"])
        self.assertEqual(manifest["scenes"][0]["visual_assembly"]["slots"], [])

    def test_user_assets_are_selected_first_with_user_owned_rights(self) -> None:
        from src.news.asset_manager import build_assets_manifest

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            user_image = root / "whale.jpg"
            Image.new("RGB", (1080, 1920), (20, 80, 120)).save(user_image)
            visual_plan = {
                "scenes": [
                    {
                        "scene_id": "scene_001",
                        "visual_type": "image",
                        "primary_query": "whale mother calf aerial ocean",
                    }
                ]
            }

            manifest = build_assets_manifest(
                visual_plan=visual_plan,
                user_assets=[
                    {
                        "path": str(user_image),
                        "rights_declaration": {
                            "confirmation_status": "approved",
                            "license_name": "user_owned",
                            "rights_status": "user_owned",
                            "owner_approval_status": "approved",
                        },
                    }
                ],
                media_index={"version": 1, "items": []},
                dry_run=False,
            )

            selected = manifest["scenes"][0]["selected_asset"]
            self.assertEqual(selected["provider"], "user")
            self.assertTrue(selected["allowed_for_render"])
            self.assertEqual(selected["rights_declaration"]["confirmation_status"], "approved")
            self.assertTrue(selected["policy_decision"]["allowed_for_render"])
            self.assertEqual(manifest["missing_scenes"], [])

    def test_confirmed_user_asset_cannot_bypass_must_avoid_in_draft(self) -> None:
        from src.assets.completion import MODE_DRAFT_COMPLETE, read_assembly
        from src.news.asset_manager import build_assets_manifest

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            user_image = root / "penguin.jpg"
            Image.new("RGB", (1080, 1920), (20, 80, 120)).save(user_image)
            manifest = build_assets_manifest(
                visual_plan={
                    "scenes": [
                        {
                            "scene_id": "scene_001",
                            "visual_type": "image",
                            "target_duration_sec": 4.0,
                            "primary_query": "Antarctic research sample",
                            "visual_brief": {
                                "subject": "research sample",
                                "must_avoid": ["penguin"],
                            },
                        }
                    ]
                },
                user_assets=[
                    {
                        "path": str(user_image),
                        "rights_declaration": {
                            "confirmation_status": "approved",
                            "license_name": "user_owned",
                            "rights_status": "user_owned",
                            "owner_approval_status": "approved",
                        },
                    }
                ],
                media_index={"version": 1, "items": []},
                providers=[],
                dry_run=False,
                project_root=root,
                project_id="must_avoid_fixture",
                completion_mode=MODE_DRAFT_COMPLETE,
            )

            scene = manifest["scenes"][0]
            assembly = read_assembly(scene, scene_duration_sec=4.0)

        self.assertTrue(assembly.usable_in_draft)
        self.assertTrue(assembly.slots)
        self.assertTrue(all(slot.selected_asset["provider"] != "user" for slot in assembly.slots))
        rejected = next(
            item for item in scene["ranked_candidates"] if item["provider"] == "user"
        )
        self.assertIn("must_avoid_match:penguin", rejected["reject_reason"])

    def test_visual_support_summary_uses_the_weakest_secondary_slot(self) -> None:
        from src.assets.completion import (
            ASSEMBLY_COMPOSITE,
            MODE_DRAFT_COMPLETE,
            SLOT_PRIMARY,
            SLOT_SUPPORTING,
            TIER_EXACT,
            TIER_PARTIAL,
            SceneVisualAssembly,
            attach_assembly,
            evaluate_usability,
        )
        from src.assets.completion.assembly import slot_from_asset
        from src.assets.semantic_selection.decision import SUPPORT_PARTIAL
        from src.news.asset_manager import refresh_manifest_summaries
        from tests.test_autonomous_completion_pipeline import _asset, _png

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            exact = _asset(
                path=_png(root / "exact.png", 1),
                scene_id="scene_001",
            )
            partial = _asset(
                path=_png(root / "partial.png", 2),
                scene_id="scene_001",
                support=SUPPORT_PARTIAL,
                missing=["instrument_action"],
            )
            assembly = SceneVisualAssembly(
                scene_id="scene_001",
                scene_duration_sec=4.0,
                assembly_status=ASSEMBLY_COMPOSITE,
                completion_mode=MODE_DRAFT_COMPLETE,
                slots=[
                    slot_from_asset(
                        exact,
                        slot_id="scene_001_slot_001",
                        purpose=SLOT_PRIMARY,
                        start_offset_sec=0.0,
                        end_offset_sec=2.0,
                        quality_tier=TIER_EXACT,
                        usability=evaluate_usability(
                            exact,
                            mode=MODE_DRAFT_COMPLETE,
                            quality_tier=TIER_EXACT,
                            require_local_file=True,
                        ),
                    ),
                    slot_from_asset(
                        partial,
                        slot_id="scene_001_slot_002",
                        purpose=SLOT_SUPPORTING,
                        start_offset_sec=2.0,
                        end_offset_sec=4.0,
                        quality_tier=TIER_PARTIAL,
                        usability=evaluate_usability(
                            partial,
                            mode=MODE_DRAFT_COMPLETE,
                            quality_tier=TIER_PARTIAL,
                            require_local_file=True,
                        ),
                    ),
                ],
            )
            scene = {"scene_id": "scene_001", "required_duration_sec": 4.0}
            attach_assembly(scene, assembly)
            manifest = {
                "scenes": [scene],
                "missing_scenes": [],
                "completion": {"mode": MODE_DRAFT_COMPLETE},
            }
            refresh_manifest_summaries(manifest, mode=MODE_DRAFT_COMPLETE)

        summary = manifest["visual_support"]
        self.assertEqual(summary["full_support"], 0)
        self.assertEqual(summary["by_support_status"][SUPPORT_PARTIAL], 1)
        self.assertEqual(summary["scenes_needing_review"], ["scene_001"])

    def test_reference_only_assets_are_not_selected_for_render(self) -> None:
        from src.news.asset_manager import build_assets_manifest

        with tempfile.TemporaryDirectory() as tmp:
            local_path = Path(tmp) / "reference.mp4"
            local_path.write_bytes(b"fake video")
            media_index = {
                "version": 1,
                "items": [
                    {
                        "id": "local_reference",
                        "type": "video",
                        "provider": "local",
                        "local_path": str(local_path),
                        "keywords": ["whale", "ocean"],
                        "width": 1920,
                        "height": 1080,
                        "duration": 8,
                        "rights_status": "reference_only",
                    }
                ],
            }
            visual_plan = {"scenes": [{"scene_id": "scene_001", "visual_type": "video", "primary_query": "whale ocean"}]}

            manifest = build_assets_manifest(
                visual_plan=visual_plan,
                user_assets=[],
                media_index=media_index,
                dry_run=False,
            )

            self.assertIsNone(manifest["scenes"][0]["selected_asset"])
            self.assertEqual(manifest["missing_scenes"][0]["scene_id"], "scene_001")

    def test_local_library_asset_can_be_selected_when_rights_allow_render(self) -> None:
        from src.news.asset_manager import build_assets_manifest

        with tempfile.TemporaryDirectory() as tmp:
            local_path = Path(tmp) / "ocean.mp4"
            local_path.write_bytes(b"fake video")
            media_index = {
                "version": 1,
                "items": [
                    {
                        "schema_version": 1,
                        "id": "local_ocean",
                        "type": "video",
                        "provider": "local",
                        "provider_asset_id": "local_ocean",
                        "local_path": str(local_path),
                        "keywords": ["whale", "ocean", "mother", "calf"],
                        "source_url": "file://local_ocean",
                        "width": 1920,
                        "height": 1080,
                        "duration": 8,
                        "rights_status": "licensed",
                        "allowed_for_render": True,
                        "review_required": False,
                        "license": {
                            "license_name": "user_owned",
                            "rights_status": "licensed",
                            "allowed_for_render": True,
                            "review_required": False,
                        },
                        "provenance": {
                            "provider": "local",
                            "provider_asset_id": "local_ocean",
                            "source_page_url": "file://local_ocean",
                        },
                    }
                ],
            }
            visual_plan = {"scenes": [{"scene_id": "scene_001", "visual_type": "video", "primary_query": "whale mother calf ocean"}]}

            manifest = build_assets_manifest(
                visual_plan=visual_plan,
                user_assets=[],
                media_index=media_index,
                dry_run=False,
            )

            self.assertEqual(manifest["scenes"][0]["selected_asset"]["asset_id"], "local_ocean")
            self.assertEqual(manifest["missing_scenes"], [])

    def test_provider_errors_are_recorded_without_stopping_manifest(self) -> None:
        from src.news.asset_manager import AssetProvider, build_assets_manifest

        class BrokenProvider(AssetProvider):
            name = "broken"

            def search(self, query: str, scene: dict, limit: int = 5) -> list[dict]:
                raise RuntimeError("provider unavailable")

        visual_plan = {"scenes": [{"scene_id": "scene_001", "visual_type": "video", "primary_query": "forest science"}]}

        manifest = build_assets_manifest(
            visual_plan=visual_plan,
            user_assets=[],
            media_index={"version": 1, "items": []},
            providers=[BrokenProvider()],
            dry_run=False,
        )

        self.assertEqual(manifest["provider_errors"][0]["provider"], "broken")
        self.assertEqual(manifest["missing_scenes"][0]["scene_id"], "scene_001")

    def test_generated_placeholder_is_forbidden_unless_debug_placeholders_enabled(self) -> None:
        from src.news.asset_manager import build_assets_manifest

        visual_plan = {"scenes": [{"scene_id": "scene_001", "visual_type": "video", "primary_query": "whale aerial"}]}

        normal = build_assets_manifest(
            visual_plan=visual_plan,
            user_assets=[],
            media_index={"version": 1, "items": []},
            dry_run=False,
        )
        debug = build_assets_manifest(
            visual_plan=visual_plan,
            user_assets=[],
            media_index={"version": 1, "items": []},
            dry_run=False,
            allow_generated_fallback=True,
        )

        self.assertIsNone(normal["scenes"][0]["selected_asset"])
        self.assertEqual(normal["missing_scenes"][0]["reason"], "no_allowed_asset_found")
        self.assertEqual(debug["scenes"][0]["selected_asset"]["selected_by"], "generated_fallback")

    def test_fake_provider_selected_asset_is_downloaded_with_license_and_provenance(self) -> None:
        from PIL import Image

        from src.news.asset_manager import build_assets_manifest
        from src.providers.fake_provider import FakeStockProvider

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture = root / "fixture.jpg"
            Image.new("RGB", (1080, 1920), (25, 90, 130)).save(fixture)
            visual_plan = {
                "scenes": [
                    {
                        "scene_id": "scene_001",
                        "visual_type": "image",
                        "primary_query": "whale ocean vertical",
                        "semantic": {
                            "environment": ["ocean"],
                            "must_include": ["ocean"],
                            "visual_priority": "environment",
                        },
                    }
                ]
            }

            manifest = build_assets_manifest(
                visual_plan=visual_plan,
                user_assets=[],
                media_index={"version": 1, "items": []},
                providers=[FakeStockProvider(image_fixture=fixture)],
                dry_run=False,
                project_root=root / "project",
                project_id="project_001",
            )

            selected = manifest["scenes"][0]["selected_asset"]
            self.assertEqual(manifest["schema_version"], 1)
            self.assertEqual(selected["provider"], "fake")
            self.assertTrue(Path(selected["path"]).is_file())
            self.assertEqual(selected["download_status"], "downloaded")
            self.assertEqual(len(selected["checksum_sha256"]), 64)
            self.assertEqual(selected["license"]["rights_status"], "licensed")
            self.assertEqual(selected["provenance"]["scene_id"], "scene_001")
            self.assertEqual(selected["technical_validation"]["status"], "passed")
            self.assertEqual(manifest["missing_scenes"], [])

    def test_unknown_provider_rights_are_blocked_and_recorded_as_missing(self) -> None:
        from PIL import Image

        from src.news.asset_manager import build_assets_manifest
        from src.providers.fake_provider import FakeStockProvider

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture = root / "fixture.jpg"
            Image.new("RGB", (1080, 1920), (25, 90, 130)).save(fixture)
            visual_plan = {
                "scenes": [
                    {
                        "scene_id": "scene_001",
                        "visual_type": "image",
                        "primary_query": "ocean vertical",
                        "semantic": {
                            "environment": ["ocean"],
                            "must_include": ["ocean"],
                            "visual_priority": "environment",
                        },
                    }
                ]
            }

            manifest = build_assets_manifest(
                visual_plan=visual_plan,
                user_assets=[],
                media_index={"version": 1, "items": []},
                providers=[FakeStockProvider(image_fixture=fixture, mode="unknown_license")],
                dry_run=False,
                project_root=root / "project",
                project_id="project_001",
            )

            self.assertIsNone(manifest["scenes"][0]["selected_asset"])
            self.assertEqual(manifest["missing_scenes"][0]["scene_id"], "scene_001")
            self.assertEqual(manifest["missing_scenes"][0]["reason"], "license_review_required")
            self.assertTrue(any(attempt.get("download_status") == "blocked" for attempt in manifest["provider_attempts"]))


if __name__ == "__main__":
    unittest.main()
