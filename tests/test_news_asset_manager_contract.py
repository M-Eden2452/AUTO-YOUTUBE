from __future__ import annotations

import ast
import importlib.util
import inspect
import os
import unittest
from pathlib import Path
from unittest.mock import patch


class _OfflineProvider:
    name = "offline_characterization"

    def search(self, query, scene, limit=5):
        return []


class NewsAssetManagerContractTests(unittest.TestCase):
    def test_d01_legacy_provider_names_have_no_internal_callers(self) -> None:
        legacy_names = (
            "PexelsAssetProvider",
            "PixabayAssetProvider",
            "UnsplashAssetProvider",
        )
        repository_root = Path(__file__).resolve().parents[1]
        compatibility_modules = {
            repository_root / "src" / "news" / "asset_manager.py",
            repository_root / "src" / "news" / "asset_provider_adapters.py",
        }
        callers: list[str] = []

        for source_root in ("ai_youtube", "apps", "anime_factory", "src"):
            for source_path in (repository_root / source_root).rglob("*.py"):
                if source_path in compatibility_modules:
                    continue
                source = source_path.read_text(encoding="utf-8")
                if any(name in source for name in legacy_names):
                    callers.append(source_path.relative_to(repository_root).as_posix())

        self.assertEqual(callers, [])

    def test_d02_stock_downloader_has_no_internal_import_or_callers(self) -> None:
        repository_root = Path(__file__).resolve().parents[1]
        downloader_path = (
            repository_root / "src" / "news" / "stock_video_downloader.py"
        )
        offenders: list[str] = []

        for source_root in ("ai_youtube", "apps", "anime_factory", "src"):
            for source_path in (repository_root / source_root).rglob("*.py"):
                if source_path == downloader_path:
                    continue
                tree = ast.parse(
                    source_path.read_text(encoding="utf-8"),
                    filename=str(source_path),
                )
                for node in ast.walk(tree):
                    imports_downloader = (
                        isinstance(node, ast.Import)
                        and any(
                            alias.name == "src.news.stock_video_downloader"
                            for alias in node.names
                        )
                    )
                    imports_downloader_symbol = (
                        isinstance(node, ast.ImportFrom)
                        and (
                            str(node.module or "").endswith(
                                "stock_video_downloader"
                            )
                            or any(
                                alias.name
                                in {
                                    "stock_video_downloader",
                                    "download_stock_videos_for_project",
                                }
                                for alias in node.names
                            )
                        )
                    )
                    calls_downloader = (
                        isinstance(node, ast.Call)
                        and (
                            (
                                isinstance(node.func, ast.Name)
                                and node.func.id
                                == "download_stock_videos_for_project"
                            )
                            or (
                                isinstance(node.func, ast.Attribute)
                                and node.func.attr
                                == "download_stock_videos_for_project"
                            )
                        )
                    )
                    if (
                        imports_downloader
                        or imports_downloader_symbol
                        or calls_downloader
                    ):
                        offenders.append(
                            source_path.relative_to(repository_root).as_posix()
                        )
                        break

        self.assertEqual(offenders, [])

    def test_provider_consolidation_retires_legacy_names(self) -> None:
        from src.news import asset_manager
        from src.news import asset_provider_adapters
        from src.providers import create_default_stock_providers

        factory_source = inspect.getsource(
            asset_provider_adapters.create_default_asset_providers
        )
        self.assertIn("create_default_stock_providers", factory_source)
        self.assertTrue(callable(create_default_stock_providers))

        for retired_name in (
            "PexelsAssetProvider",
            "PixabayAssetProvider",
            "UnsplashAssetProvider",
        ):
            self.assertFalse(
                hasattr(asset_provider_adapters, retired_name),
                retired_name,
            )
            self.assertFalse(hasattr(asset_manager, retired_name), retired_name)

    def test_default_factory_returns_only_canonical_stock_providers(self) -> None:
        from src.news.asset_provider_adapters import create_default_asset_providers

        with patch.dict(
            os.environ,
            {
                "WIKIMEDIA_ENABLED": "true",
                "NASA_IMAGES_ENABLED": "true",
                "INTERNET_ARCHIVE_ENABLED": "true",
                "PEXELS_API_KEY": "pexels-test",
                "PIXABAY_API_KEY": "pixabay-test",
                "UNSPLASH_ACCESS_KEY": "unsplash-is-not-an-active-provider",
            },
            clear=True,
        ):
            providers = create_default_asset_providers(load_environment=lambda: None)

        self.assertEqual(
            [provider.name for provider in providers],
            [
                "wikimedia",
                "nasa_images",
                "internet_archive",
                "pexels",
                "pixabay",
            ],
        )
        for provider in providers:
            self.assertTrue(
                type(provider).__module__.startswith("src.providers."),
                type(provider).__module__,
            )
            for method_name in (
                "capabilities",
                "search",
                "get_preview",
                "resolve_license",
                "download",
                "health_check",
            ):
                self.assertTrue(
                    callable(getattr(provider, method_name, None)),
                    f"{provider.name}.{method_name}",
                )

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

    def test_d02_stock_video_downloader_module_is_retired(self) -> None:
        from src.news.asset_manager import build_news_asset_manifest

        self.assertIsNone(
            importlib.util.find_spec("src.news.stock_video_downloader")
        )
        self.assertTrue(callable(build_news_asset_manifest))


if __name__ == "__main__":
    unittest.main()
