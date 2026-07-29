from __future__ import annotations

import inspect
import unittest
from unittest.mock import patch


class _OfflineProvider:
    name = "offline_characterization"

    def search(self, query, scene, limit=5):
        return []


class NewsAssetManagerContractTests(unittest.TestCase):
    def test_compatibility_import_surface_and_signatures(self) -> None:
        from src.news import asset_manager

        expected_parameters = {
            "build_assets_manifest": [
                "visual_plan",
                "user_assets",
                "media_index",
                "providers",
                "dry_run",
                "channel",
                "allow_generated_fallback",
                "asset_selection",
                "project_root",
                "project_id",
                "max_download_attempts",
                "completion_mode",
                "reuse_ledger",
                "allow_infographic_fallback",
                "allow_emergency_backdrop",
                "prefer_video",
                "minimum_video_clips",
                "minimum_video_duration_ratio",
            ],
            "build_news_asset_manifest": [
                "visual_plan",
                "user_assets",
                "dry_run",
                "channel",
                "media_index_path",
                "debug_placeholders",
                "asset_selection",
                "project_root",
                "project_id",
                "completion_mode",
                "reuse_ledger",
            ],
            "create_default_asset_providers": [],
            "summarize_media_coverage": ["scene_entries", "policy"],
            "refresh_manifest_summaries": ["manifest", "mode", "reuse"],
        }
        for name, parameters in expected_parameters.items():
            value = getattr(asset_manager, name)
            self.assertTrue(callable(value), name)
            self.assertEqual(list(inspect.signature(value).parameters), parameters)

        for compatibility_name in (
            "AssetProvider",
            "PexelsAssetProvider",
            "PixabayAssetProvider",
            "UnsplashAssetProvider",
            "_ensure_selected_asset_downloaded",
            "_search_provider",
            "_select_best_candidate",
        ):
            self.assertTrue(hasattr(asset_manager, compatibility_name), compatibility_name)

    def test_build_news_manifest_keeps_module_factory_patch_point(self) -> None:
        from src.news.asset_manager import build_news_asset_manifest

        provider = _OfflineProvider()
        with patch(
            "src.news.asset_manager.create_default_asset_providers",
            return_value=[provider],
        ) as factory:
            manifest = build_news_asset_manifest(
                visual_plan={"language": "ru", "scenes": []},
                user_assets=[],
                dry_run=False,
            )

        factory.assert_called_once_with()
        self.assertEqual(
            manifest["provider_order"],
            ["user_assets", "local_library", provider.name],
        )

    def test_empty_manifest_shape_and_summary_refresh_are_stable(self) -> None:
        from src.news.asset_manager import (
            build_assets_manifest,
            refresh_manifest_summaries,
        )

        manifest = build_assets_manifest(
            visual_plan={"language": "ru", "scenes": []},
            user_assets=[],
            media_index={"version": 1, "items": []},
            providers=[],
            dry_run=True,
        )

        self.assertEqual(
            set(manifest),
            {
                "schema_version",
                "dry_run",
                "visual_mode",
                "video_first_policy",
                "media_coverage",
                "infographic_fallback",
                "asset_selection",
                "provider_order",
                "routing_decisions",
                "assets",
                "scenes",
                "missing_scenes",
                "visual_support",
                "completion",
                "continuity",
                "provider_attempts",
                "provider_errors",
                "visual_review",
                "semantic_visual",
                "warnings",
            },
        )
        refreshed = refresh_manifest_summaries(manifest)
        self.assertIs(refreshed, manifest)
        self.assertEqual(manifest["visual_support"]["scene_count"], 0)
        self.assertEqual(manifest["media_coverage"]["status"], "not_applicable")
        self.assertFalse(manifest["completion"]["draft_complete"])
        self.assertFalse(manifest["completion"]["publish_ready"])


if __name__ == "__main__":
    unittest.main()
