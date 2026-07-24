from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PIL import Image


class ProviderFoundationTests(unittest.TestCase):
    def test_fake_provider_search_download_and_unknown_license_modes(self) -> None:
        from src.assets.provider_contract import AssetSearchRequest, DownloadContext, LicenseReviewRequired
        from src.providers.fake_provider import FakeStockProvider

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image = root / "fixture.jpg"
            Image.new("RGB", (1080, 1920), (20, 80, 120)).save(image)
            provider = FakeStockProvider(image_fixture=image, mode="success")
            request = AssetSearchRequest(
                query="whale ocean",
                media_type="image",
                target_aspect_ratio="9:16",
                orientation_preference="vertical",
                min_width=720,
                min_height=1280,
                max_results=3,
                scene_id="scene_001",
                project_id="project_001",
            )

            candidates = provider.search(request)
            downloaded = provider.download(candidates[0], root / "downloads", DownloadContext(project_id="project_001", scene_id="scene_001"))

            self.assertEqual(provider.name, "fake")
            self.assertEqual(candidates[0].media_type, "image")
            self.assertEqual(candidates[0].orientation, "vertical")
            self.assertTrue(Path(downloaded.local_path).is_file())
            self.assertEqual(len(downloaded.checksum_sha256), 64)
            self.assertTrue(downloaded.license.allowed_for_render)
            self.assertEqual(downloaded.provenance.scene_id, "scene_001")

            blocked = FakeStockProvider(image_fixture=image, mode="unknown_license")
            blocked_candidate = blocked.search(request)[0]
            self.assertTrue(blocked.resolve_license(blocked_candidate).review_required)
            with self.assertRaises(LicenseReviewRequired):
                blocked.download(blocked_candidate, root / "blocked", DownloadContext(project_id="project_001", scene_id="scene_001"))

    def test_pexels_stock_provider_normalizes_video_and_prefers_vertical_for_shorts(self) -> None:
        from src.assets.provider_contract import AssetSearchRequest
        from src.providers.pexels_provider import PexelsStockProvider

        class StubHttp:
            def __init__(self) -> None:
                self.calls: list[dict] = []

            def get_json(self, url: str, *, headers=None, params=None, timeout=None) -> dict:
                self.calls.append({"url": url, "headers": headers, "params": params})
                return {
                    "videos": [
                        {
                            "id": 42,
                            "url": "https://www.pexels.com/video/42/",
                            "duration": 7,
                            "width": 1920,
                            "height": 1080,
                            "user": {"name": "Pexels Author", "url": "https://www.pexels.com/@author"},
                            "image": "https://images.pexels.com/video-preview.jpg",
                            "video_files": [
                                {"id": 1, "width": 1920, "height": 1080, "file_type": "video/mp4", "link": "https://cdn/landscape.mp4"},
                                {"id": 2, "width": 1080, "height": 1920, "file_type": "video/mp4", "link": "https://cdn/vertical.mp4"},
                            ],
                        }
                    ]
                }

        http = StubHttp()
        provider = PexelsStockProvider("PEXELS_KEY", http=http)
        request = AssetSearchRequest(
            query="ocean whale",
            media_type="video",
            target_aspect_ratio="9:16",
            orientation_preference="vertical",
            min_width=720,
            min_height=1280,
            max_results=5,
            scene_id="scene_001",
        )

        candidates = provider.search(request)

        self.assertEqual(http.calls[0]["params"]["orientation"], "portrait")
        self.assertEqual(candidates[0].provider, "pexels")
        self.assertEqual(candidates[0].provider_asset_id, "42")
        self.assertEqual(candidates[0].download_url, "https://cdn/vertical.mp4")
        self.assertEqual(candidates[0].preview_url, "https://images.pexels.com/video-preview.jpg")
        self.assertEqual(candidates[0].author_name, "Pexels Author")
        self.assertTrue(candidates[0].license.allowed_for_render)
        self.assertFalse(candidates[0].license.review_required)
        self.assertEqual(candidates[0].policy_decision["policy_context"], "internal_content_production")
        self.assertEqual(candidates[0].policy_decision["owner_approval_status"], "approved")

    def test_pixabay_stock_provider_normalizes_tags_author_and_vertical_video(self) -> None:
        from src.assets.provider_contract import AssetSearchRequest
        from src.providers.pixabay_provider import PixabayStockProvider

        class StubHttp:
            def __init__(self) -> None:
                self.calls: list[dict] = []

            def get_json(self, url: str, *, headers=None, params=None, timeout=None) -> dict:
                self.calls.append({"url": url, "params": params})
                return {
                    "hits": [
                        {
                            "id": 77,
                            "pageURL": "https://pixabay.com/videos/77/",
                            "tags": "whale, ocean, aerial",
                            "user": "Pixabay Author",
                            "user_id": 15,
                            "duration": 6,
                            "picture_id": "abc123",
                            "videos": {
                                "large": {"width": 1920, "height": 1080, "url": "https://cdn/large.mp4"},
                                "medium": {"width": 1080, "height": 1920, "url": "https://cdn/vertical.mp4"},
                            },
                        }
                    ]
                }

        http = StubHttp()
        provider = PixabayStockProvider("PIXABAY_KEY", http=http)
        request = AssetSearchRequest(
            query="whale ocean",
            media_type="video",
            target_aspect_ratio="9:16",
            orientation_preference="vertical",
            min_width=720,
            min_height=1280,
            max_results=5,
            scene_id="scene_001",
        )

        candidates = provider.search(request)

        self.assertEqual(http.calls[0]["params"]["q"], "whale ocean")
        self.assertEqual(candidates[0].provider, "pixabay")
        self.assertEqual(candidates[0].provider_asset_id, "77")
        self.assertEqual(candidates[0].download_url, "https://cdn/vertical.mp4")
        self.assertIn("whale", candidates[0].tags)
        self.assertEqual(candidates[0].author_name, "Pixabay Author")
        self.assertTrue(candidates[0].license.allowed_for_render)
        self.assertFalse(candidates[0].license.review_required)
        self.assertEqual(candidates[0].policy_decision["policy_context"], "internal_content_production")
        self.assertEqual(candidates[0].policy_decision["owner_approval_status"], "approved")

    def test_fake_provider_invalid_video_is_rejected_and_cleans_output(self) -> None:
        from src.assets.provider_contract import AssetSearchRequest, DownloadContext, ProviderValidationError
        from src.providers.fake_provider import FakeStockProvider

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            provider = FakeStockProvider(mode="invalid_file")
            request = AssetSearchRequest(query="whale ocean", media_type="video", scene_id="scene_001", project_id="project_001")
            candidate = provider.search(request)[0]
            destination = root / "downloads"

            with self.assertRaises(ProviderValidationError):
                provider.download(candidate, destination, DownloadContext(project_id="project_001", scene_id="scene_001"))

            self.assertEqual(list(destination.glob("*.mp4")), [])

    def test_local_library_provider_returns_only_current_render_safe_records(self) -> None:
        from src.assets.download import sha256_file
        from src.assets.provider_contract import AssetSearchRequest, DownloadContext
        from src.providers.local_library_provider import LocalLibraryStockProvider

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            safe = root / "safe.jpg"
            legacy = root / "legacy.jpg"
            Image.new("RGB", (1080, 1920), (10, 20, 30)).save(safe)
            Image.new("RGB", (1080, 1920), (40, 50, 60)).save(legacy)
            index = {
                "version": 1,
                "items": [
                    {
                        "schema_version": 1,
                        "id": "safe_local",
                        "type": "image",
                        "provider": "local",
                        "local_path": str(safe),
                        "source_url": "file://safe",
                        "keywords": ["whale", "ocean"],
                        "width": 1080,
                        "height": 1920,
                        "checksum_sha256": sha256_file(safe),
                        "rights_status": "licensed",
                        "allowed_for_render": True,
                        "review_required": False,
                        "license": {
                            "license_name": "user_owned",
                            "rights_status": "licensed",
                            "allowed_for_render": True,
                            "review_required": False,
                            "commercial_use_allowed": True,
                            "modification_allowed": True,
                        },
                        "provenance": {"provider": "local", "source_page_url": "file://safe"},
                        "technical_validation": {"status": "passed", "width": 1080, "height": 1920},
                    },
                    {
                        "id": "legacy_unknown",
                        "type": "image",
                        "provider": "local",
                        "local_path": str(legacy),
                        "keywords": ["whale", "ocean"],
                        "width": 1080,
                        "height": 1920,
                    },
                ],
            }
            provider = LocalLibraryStockProvider(index=index)
            request = AssetSearchRequest(query="whale ocean", media_type="image", scene_id="scene_001", project_id="project_001")

            candidates = provider.search(request)
            downloaded = provider.download(candidates[0], root / "unused", DownloadContext(project_id="project_001", scene_id="scene_001"))

            self.assertEqual([candidate.asset_id for candidate in candidates], ["safe_local"])
            self.assertEqual(downloaded.local_path, str(safe))
            self.assertEqual(downloaded.license.rights_status, "licensed")


if __name__ == "__main__":
    unittest.main()
