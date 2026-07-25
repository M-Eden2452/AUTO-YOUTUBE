from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Any

from PIL import Image

from tests.test_documentary_asset_providers import WikimediaHttpStub
from tests.test_semantic_asset_selection import _candidate as _semantic_candidate
from tests.test_visual_preview_integration import CountingPreviewProvider


class ProviderIntegrationTests(unittest.TestCase):
    def test_wikimedia_search_download_validate_manifest_chain(self) -> None:
        from src.news.asset_manager import build_assets_manifest
        from src.providers.wikimedia_commons_provider import WikimediaCommonsStockProvider

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture = root / "fixture.jpg"
            Image.new("RGB", (1080, 1920), (20, 70, 110)).save(fixture)
            provider = WikimediaCommonsStockProvider(
                http=WikimediaHttpStub(
                    search_pages=[{"pageid": 100, "title": "File:Ocean research.jpg"}],
                    imageinfo_by_title={
                        "File:Ocean research.jpg": {
                            "url": "https://upload.wikimedia.org/ocean_research.jpg",
                            "mime": "image/jpeg",
                            "width": 1080,
                            "height": 1920,
                            "extmetadata": {
                                "Artist": {"value": "Commons Author"},
                                "LicenseShortName": {"value": "CC BY 4.0"},
                                "LicenseUrl": {"value": "https://creativecommons.org/licenses/by/4.0/"},
                                "Attribution": {"value": "Commons Author, CC BY 4.0"},
                                "ImageDescription": {"value": "ocean research"},
                            },
                        }
                    },
                    download_fixture=fixture,
                )
            )
            manifest = build_assets_manifest(
                visual_plan={"scenes": [{"scene_id": "scene_001", "visual_type": "image", "primary_query": "ocean research"}]},
                user_assets=[],
                media_index={"version": 1, "items": []},
                providers=[provider],
                dry_run=False,
                project_root=root / "project",
                project_id="project_001",
            )

            selected = manifest["scenes"][0]["selected_asset"]
            self.assertEqual(selected["provider"], "wikimedia")
            self.assertTrue(Path(selected["local_path"]).is_file())
            self.assertEqual(selected["technical_validation"]["status"], "passed")
            self.assertEqual(len(selected["checksum_sha256"]), 64)
            self.assertEqual(manifest["missing_scenes"], [])

    def test_automatic_providers_fail_envato_manual_request_generated(self) -> None:
        from src.news.asset_manager import build_assets_manifest

        manifest = build_assets_manifest(
            visual_plan={"scenes": [{"scene_id": "scene_001", "visual_type": "video", "primary_query": "premium studio reconstruction"}]},
            user_assets=[],
            media_index={"version": 1, "items": []},
            providers=[],
            dry_run=False,
            project_root=Path(tempfile.mkdtemp()),
            project_id="project_001",
            asset_selection={"envato_manual_fallback_enabled": True},
        )

        manual = manifest["scenes"][0]["manual_request"]
        self.assertEqual(manual["provider"], "envato_manual")
        self.assertFalse(manual["automatic_download"])
        self.assertEqual(manifest["missing_scenes"][0]["reason"], "manual_action_required")


class ProviderFoundationNewsIntegrationTests(unittest.TestCase):
    def test_manual_asset_without_rights_confirmation_is_blocked(self) -> None:
        from src.news.asset_manager import build_assets_manifest

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture = root / "ручной_кадр.jpg"
            Image.new("RGB", (1080, 1920), (20, 40, 80)).save(fixture)
            manifest = build_assets_manifest(
                visual_plan={"scenes": [_scene()]},
                user_assets=[str(fixture)],
                media_index={"version": 1, "items": []},
                providers=[],
                dry_run=False,
                project_root=root,
                project_id="project_001",
            )

        self.assertIsNone(manifest["scenes"][0]["selected_asset"])
        self.assertEqual(manifest["missing_scenes"][0]["reason"], "license_review_required")
        self.assertEqual(manifest["assets"][0]["rights_declaration"]["confirmation_status"], "missing")

    def test_provider_policy_decision_is_included_in_manifest(self) -> None:
        from src.news.asset_manager import build_assets_manifest
        from src.providers.fake_provider import FakeStockProvider

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture = root / "fixture.jpg"
            Image.new("RGB", (1080, 1920), (10, 80, 120)).save(fixture)

            manifest = build_assets_manifest(
                visual_plan={"scenes": [_scene()]},
                user_assets=[],
                media_index={"version": 1, "items": []},
                providers=[FakeStockProvider(image_fixture=fixture)],
                dry_run=False,
                project_root=root,
                project_id="project_001",
            )

        selected = manifest["scenes"][0]["selected_asset"]
        self.assertIsNotNone(selected)
        self.assertTrue(selected["policy_decision"]["allowed_for_render"])
        self.assertEqual(selected["policy_decision"]["provider"], "fake")
        self.assertIn("policy_version", selected["policy_decision"])

    def test_quality_check_uses_centralized_policy(self) -> None:
        from src.news.quality_check import run_quality_check

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture = root / "unknown.jpg"
            Image.new("RGB", (1080, 1920), (20, 20, 20)).save(fixture)
            report = run_quality_check(
                script=_script(),
                research={"claims": [{"safe_for_script": True}]},
                assets_manifest={
                    "schema_version": 1,
                    "scenes": [
                        {
                            "scene_id": "scene_001",
                            "selected_asset": {
                                "asset_id": "unknown_001",
                                "provider": "unknown_provider",
                                "provider_asset_id": "remote-1",
                                "type": "image",
                                "media_type": "image",
                                "path": str(fixture),
                                "local_path": str(fixture),
                                "source_page_url": "https://example.test/asset/1",
                                "source_url": "https://example.test/asset/1",
                                "checksum_sha256": "a" * 64,
                                "technical_validation": {"status": "passed", "width": 1080, "height": 1920},
                                "license": {
                                    "license_name": "unknown-license",
                                    "rights_status": "licensed",
                                    "allowed_for_render": True,
                                    "review_required": False,
                                },
                                "provenance": {
                                    "provider": "unknown_provider",
                                    "provider_asset_id": "remote-1",
                                    "source_page_url": "https://example.test/asset/1",
                                },
                                "allowed_for_render": True,
                                "review_required": False,
                            },
                        }
                    ],
                    "missing_scenes": [],
                },
                voice_manifest={"status": "completed"},
                subtitles_manifest={"srt_path": "x.srt", "ass_path": "x.ass"},
            )

        self.assertEqual(report["status"], "failed")
        self.assertTrue(any(error["check"] == "asset_policy" for error in report["errors"]))


class VisualPreviewNewsIntegrationTests(unittest.TestCase):
    def test_original_is_downloaded_only_for_final_selection(self) -> None:
        from src.news.asset_manager import build_assets_manifest

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            preview = root / "preview.jpg"
            original = root / "original.jpg"
            Image.new("RGB", (320, 480), (25, 65, 110)).save(preview)
            Image.new("RGB", (1080, 1920), (25, 65, 110)).save(original)
            provider = CountingDownloadProvider(preview_path=preview, original_path=original)

            manifest = build_assets_manifest(
                visual_plan={"scenes": [{"scene_id": "scene_001", "visual_type": "image", "primary_query": "ocean science", "semantic": {"visual_priority": "environment"}}]},
                user_assets=[],
                media_index={"version": 1, "items": []},
                providers=[provider],
                dry_run=False,
                project_root=root / "project",
                project_id="project_001",
                asset_selection={"visual_preview": {"enabled": True, "shortlist_size": 2}},
            )

            self.assertEqual(provider.download_calls, 1)
            self.assertEqual(manifest["scenes"][0]["selected_asset"]["provider"], "fake")
            self.assertIn("visual_review", manifest["scenes"][0])


class CountingDownloadProvider(CountingPreviewProvider):
    def __init__(self, *, preview_path: Path, original_path: Path) -> None:
        super().__init__(preview_path=preview_path)
        self.original_path = original_path
        self.download_calls = 0

    def capabilities(self) -> Any:
        from src.assets.models import ProviderCapabilities

        return ProviderCapabilities(provider=self.name, media_types=["image"], supports_preview=True, supports_download=True)

    def search(self, request: Any) -> list[Any]:
        from src.assets.license_policy import apply_policy_to_candidate
        from src.assets.models import AssetCandidate, AssetLicense, AssetProvenance

        candidates = []
        for index in range(2):
            candidate = AssetCandidate(
                asset_id=f"fake_candidate_{index}",
                provider=self.name,
                provider_asset_id=f"candidate_{index}",
                media_type="image",
                title=f"ocean science candidate {index}",
                description="ocean science",
                tags=["ocean", "science"],
                source_page_url=f"https://fake.local/{index}",
                preview_url=f"https://fake.local/preview/{index}.jpg",
                download_url=f"file:///{self.original_path.as_posix()}",
                width=1080,
                height=1920,
                search_query=request.query,
                project_id=request.project_id,
                scene_id=request.scene_id,
                license=AssetLicense(
                    license_name="fake_test_license",
                    license_url="https://fake.local/license",
                    provider_terms_url="https://fake.local/terms",
                    rights_status="licensed",
                    commercial_use_allowed=True,
                    modification_allowed=True,
                    attribution_required=False,
                    allowed_for_render=True,
                    review_required=False,
                ),
                provenance=AssetProvenance(
                    provider=self.name,
                    provider_asset_id=f"candidate_{index}",
                    source_page_url=f"https://fake.local/{index}",
                    download_url=f"file:///{self.original_path.as_posix()}",
                    project_id=request.project_id,
                    scene_id=request.scene_id,
                    search_query=request.query,
                ),
            )
            apply_policy_to_candidate(candidate)
            candidates.append(candidate)
        return candidates

    def resolve_license(self, candidate: Any) -> Any:
        return candidate.license

    def download(self, candidate: Any, destination: Path, context: Any) -> Any:
        from src.assets.download import copy_candidate_fixture

        self.download_calls += 1
        return copy_candidate_fixture(candidate, self.original_path, destination, context)

    def health_check(self) -> Any:
        from src.assets.provider_contract import ProviderHealth

        return ProviderHealth(provider=self.name, configured=True, status="ready")


class SemanticAssetSelectionNewsIntegrationTests(unittest.TestCase):
    def test_build_assets_manifest_uses_semantic_selector(self) -> None:
        from src.news.asset_manager import AssetProvider, build_assets_manifest

        class FakeProvider(AssetProvider):
            name = "fake"

            def search(self, query: str, scene: dict, limit: int = 5) -> list[dict]:
                return [
                    _semantic_candidate("desert", "Australia desert aerial", "australia desert", 3840, 2160),
                    _semantic_candidate("whale", "right whale ocean aerial", "whale ocean aerial", 3840, 2160),
                ]

        manifest = build_assets_manifest(
            visual_plan={
                "scenes": [
                    {
                        "scene_id": "scene_001",
                        "visual_type": "video",
                        "primary_query": "southern right whale Australian coast drone",
                        "visual_priority": "exact_subject",
                    }
                ]
            },
            user_assets=[],
            media_index={"version": 1, "items": []},
            providers=[FakeProvider()],
            dry_run=False,
        )

        self.assertEqual(manifest["scenes"][0]["selected_asset"]["asset_id"], "whale")
        self.assertEqual(manifest["missing_scenes"], [])


def _scene() -> dict:
    return {
        "scene_id": "scene_001",
        "visual_type": "image",
        "primary_query": "whale ocean",
        "target_duration_sec": 3,
        "visual_keywords": ["whale", "ocean"],
    }


def _script() -> dict:
    return {
        "estimated_duration_sec": 45,
        "scenes": [
            {
                "scene_id": "scene_001",
                "narration": "A short narration.",
                "target_duration_sec": 3,
            }
        ],
    }


if __name__ == "__main__":
    unittest.main()
