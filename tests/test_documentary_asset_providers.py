from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image


class DocumentaryAssetProviderTests(unittest.TestCase):
    def test_wikimedia_search_normalizes_image_extmetadata_and_cc_by_policy(self) -> None:
        from src.assets.provider_contract import AssetSearchRequest
        from src.providers.wikimedia_commons_provider import WikimediaCommonsStockProvider

        http = WikimediaHttpStub(
            search_pages=[
                {"pageid": 10, "title": "File:Blue whale map.jpg"},
            ],
            imageinfo_by_title={
                "File:Blue whale map.jpg": {
                    "url": "https://upload.wikimedia.org/blue_whale_map.jpg",
                    "thumburl": "https://upload.wikimedia.org/thumb/blue_whale_map.jpg",
                    "mime": "image/jpeg",
                    "width": 2400,
                    "height": 1600,
                    "timestamp": "2024-01-01T00:00:00Z",
                    "extmetadata": {
                        "Artist": {"value": "<span>Marine Researcher</span>"},
                        "Credit": {"value": "Research archive"},
                        "LicenseShortName": {"value": "CC BY 4.0"},
                        "LicenseUrl": {"value": "https://creativecommons.org/licenses/by/4.0/"},
                        "UsageTerms": {"value": "Creative Commons Attribution 4.0"},
                        "Attribution": {"value": "Marine Researcher, CC BY 4.0"},
                        "ImageDescription": {"value": "<p>Blue whale migration map</p>"},
                        "Categories": {"value": "Blue whales|Maps"},
                    },
                }
            },
        )
        provider = WikimediaCommonsStockProvider(http=http)

        candidates = provider.search(AssetSearchRequest(query="blue whale map", media_type="image", scene_id="scene_001", project_id="p1"))

        self.assertEqual(len(candidates), 1)
        candidate = candidates[0]
        self.assertEqual(candidate.provider, "wikimedia")
        self.assertEqual(candidate.provider_asset_id, "10")
        self.assertEqual(candidate.source_page_url, "https://commons.wikimedia.org/wiki/File:Blue_whale_map.jpg")
        self.assertEqual(candidate.download_url, "https://upload.wikimedia.org/blue_whale_map.jpg")
        self.assertEqual(candidate.preview_url, "https://upload.wikimedia.org/thumb/blue_whale_map.jpg")
        self.assertEqual(candidate.author_name, "Marine Researcher")
        self.assertIn("Maps", candidate.tags)
        self.assertEqual(candidate.license.license_name, "CC BY 4.0")
        self.assertTrue(candidate.license.allowed_for_render)
        self.assertFalse(candidate.license.review_required)
        self.assertIn("Marine Researcher", candidate.license.attribution_text)
        self.assertEqual(candidate.policy_decision["modification_notice_required"], True)

    def test_wikimedia_video_cc_by_sa_review_and_unknown_license_blocked(self) -> None:
        from src.assets.provider_contract import AssetSearchRequest
        from src.providers.wikimedia_commons_provider import WikimediaCommonsStockProvider

        http = WikimediaHttpStub(
            search_pages=[
                {"pageid": 11, "title": "File:Archive clip.webm"},
                {"pageid": 12, "title": "File:Mystery image.jpg"},
            ],
            imageinfo_by_title={
                "File:Archive clip.webm": {
                    "url": "https://upload.wikimedia.org/archive_clip.webm",
                    "thumburl": "https://upload.wikimedia.org/thumb/archive_clip.jpg",
                    "mime": "video/webm",
                    "width": 1280,
                    "height": 720,
                    "duration": 15.0,
                    "extmetadata": {
                        "Artist": {"value": "Archive Author"},
                        "LicenseShortName": {"value": "CC BY-SA 4.0"},
                        "LicenseUrl": {"value": "https://creativecommons.org/licenses/by-sa/4.0/"},
                        "Attribution": {"value": "Archive Author, CC BY-SA 4.0"},
                    },
                },
                "File:Mystery image.jpg": {
                    "url": "https://upload.wikimedia.org/mystery.jpg",
                    "mime": "image/jpeg",
                    "width": 1280,
                    "height": 720,
                    "extmetadata": {
                        "LicenseShortName": {"value": "unknown"},
                    },
                },
            },
        )
        provider = WikimediaCommonsStockProvider(http=http)

        video_candidates = provider.search(AssetSearchRequest(query="archive clip", media_type="video", min_width=1, min_height=1))
        image_candidates = provider.search(AssetSearchRequest(query="mystery image", media_type="image", min_width=1, min_height=1))

        self.assertEqual(video_candidates[0].media_type, "video")
        self.assertTrue(video_candidates[0].license.review_required)
        self.assertIn("share_alike", video_candidates[0].policy_decision["reason"])
        self.assertFalse(image_candidates[0].license.allowed_for_render)
        self.assertTrue(image_candidates[0].license.review_required)
        self.assertIn("unknown_license", image_candidates[0].policy_decision["reason"])

    def test_wikimedia_download_uses_common_helper_for_selected_candidate_only(self) -> None:
        from src.assets.provider_contract import AssetSearchRequest, DownloadContext
        from src.providers.wikimedia_commons_provider import WikimediaCommonsStockProvider

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture = root / "fixture.jpg"
            Image.new("RGB", (1200, 900), (10, 30, 60)).save(fixture)
            http = WikimediaHttpStub(
                search_pages=[{"pageid": 10, "title": "File:Blue whale.jpg"}],
                imageinfo_by_title={
                    "File:Blue whale.jpg": {
                        "url": "https://upload.wikimedia.org/blue_whale.jpg",
                        "mime": "image/jpeg",
                        "width": 1200,
                        "height": 900,
                        "extmetadata": {
                            "Artist": {"value": "Commons Author"},
                            "LicenseShortName": {"value": "CC BY 4.0"},
                            "LicenseUrl": {"value": "https://creativecommons.org/licenses/by/4.0/"},
                            "Attribution": {"value": "Commons Author, CC BY 4.0"},
                        },
                    }
                },
                download_fixture=fixture,
            )
            provider = WikimediaCommonsStockProvider(http=http)
            candidate = provider.search(AssetSearchRequest(query="blue whale", media_type="image", min_width=1, min_height=1))[0]

            downloaded = provider.download(candidate, root / "downloads", DownloadContext(project_id="p1", scene_id="scene_001"))

            self.assertTrue(Path(downloaded.local_path).is_file())
            self.assertEqual(len(downloaded.checksum_sha256), 64)
            self.assertEqual(http.downloads, ["https://upload.wikimedia.org/blue_whale.jpg"])

    def test_nasa_search_normalizes_assets_and_policy_reviews_third_party_notice(self) -> None:
        from src.assets.provider_contract import AssetSearchRequest
        from src.providers.nasa_images_provider import NasaImageLibraryStockProvider

        http = NasaHttpStub(
            search_items=[
                nasa_search_item("NASA-1", title="Earth hurricane from space", keywords=["earth", "storm"], center="GSFC"),
                nasa_search_item(
                    "NASA-2",
                    title="Courtesy image",
                    keywords=["astronaut"],
                    description="Courtesy of a third party photographer.",
                ),
            ],
            assets={
                "NASA-1": ["https://images-assets.nasa.gov/image/NASA-1/NASA-1~orig.jpg", "https://images-assets.nasa.gov/image/NASA-1/metadata.json"],
                "NASA-2": ["https://images-assets.nasa.gov/image/NASA-2/NASA-2~orig.jpg"],
            },
            metadata={
                "NASA-1": {"AVAIL:Title": "Earth hurricane from space"},
                "NASA-2": {"AVAIL:Description": "Copyright third party notice."},
            },
        )
        provider = NasaImageLibraryStockProvider(http=http)

        candidates = provider.search(AssetSearchRequest(query="earth storm", media_type="image", scene_id="scene_001", project_id="p1"))

        self.assertEqual(candidates[0].provider, "nasa_images")
        self.assertEqual(candidates[0].provider_asset_id, "NASA-1")
        self.assertEqual(candidates[0].download_url, "https://images-assets.nasa.gov/image/NASA-1/NASA-1~orig.jpg")
        self.assertEqual(candidates[0].source_page_url, "https://images.nasa.gov/details/NASA-1")
        self.assertEqual(candidates[0].raw_metadata["center"], "GSFC")
        self.assertTrue(candidates[0].license.allowed_for_render)
        self.assertIn("NASA", candidates[0].license.attribution_text)
        self.assertTrue(candidates[1].license.review_required)
        self.assertIn("third_party_notice", candidates[1].policy_decision["reason"])

    def test_nasa_video_rendition_selection_ignores_json_metadata(self) -> None:
        from src.assets.provider_contract import AssetSearchRequest
        from src.providers.nasa_images_provider import NasaImageLibraryStockProvider

        http = NasaHttpStub(
            search_items=[nasa_search_item("NASA-VID", title="Aviation research", media_type="video", keywords=["aviation"])],
            assets={
                "NASA-VID": [
                    "https://images-assets.nasa.gov/video/NASA-VID/metadata.json",
                    "https://images-assets.nasa.gov/video/NASA-VID/NASA-VID~small.mp4",
                    "https://images-assets.nasa.gov/video/NASA-VID/NASA-VID~orig.mov",
                    "https://images-assets.nasa.gov/video/NASA-VID/NASA-VID.en.vtt",
                ]
            },
            metadata={"NASA-VID": {}},
        )
        provider = NasaImageLibraryStockProvider(http=http)

        candidates = provider.search(AssetSearchRequest(query="aviation research", media_type="video", min_width=1, min_height=1))

        self.assertEqual(candidates[0].download_url, "https://images-assets.nasa.gov/video/NASA-VID/NASA-VID~small.mp4")
        self.assertEqual(candidates[0].raw_metadata["captions_url"], "https://images-assets.nasa.gov/video/NASA-VID/NASA-VID.en.vtt")
        self.assertNotIn("metadata.json", candidates[0].download_url)

    def test_internet_archive_search_and_file_selection_policy(self) -> None:
        from src.assets.provider_contract import AssetSearchRequest
        from src.providers.internet_archive_provider import InternetArchiveStockProvider

        http = InternetArchiveHttpStub(
            docs=[
                {
                    "identifier": "prelinger_safe",
                    "title": "Old educational film",
                    "creator": "Archive Creator",
                    "mediatype": "movies",
                    "licenseurl": "https://creativecommons.org/publicdomain/zero/1.0/",
                    "collection": ["prelinger"],
                    "subject": ["education", "history"],
                },
                {
                    "identifier": "restricted_item",
                    "title": "Restricted item",
                    "mediatype": "movies",
                    "licenseurl": "",
                    "rights": "All Rights Reserved",
                    "collection": ["unknown"],
                },
            ],
            metadata={
                "prelinger_safe": {
                    "metadata": {"identifier": "prelinger_safe"},
                    "files": [
                        {"name": "prelinger_meta.xml", "format": "Metadata"},
                        {"name": "prelinger_archive.torrent", "format": "Archive BitTorrent"},
                        {"name": "master.mpeg", "format": "MPEG2", "size": "9000000000"},
                        {"name": "derivative.mp4", "format": "h.264", "size": "12000000", "md5": "abc"},
                    ],
                }
            },
        )
        provider = InternetArchiveStockProvider(http=http)

        candidates = provider.search(AssetSearchRequest(query="old educational film", media_type="video", min_width=1, min_height=1))
        safe = candidates[0]
        selected_file = provider.resolve_candidate_file(safe)

        self.assertEqual(safe.provider, "internet_archive")
        self.assertEqual(safe.provider_asset_id, "prelinger_safe")
        self.assertTrue(safe.license.allowed_for_render)
        self.assertEqual(selected_file["name"], "derivative.mp4")
        self.assertEqual(safe.download_url, "https://archive.org/download/prelinger_safe/derivative.mp4")
        self.assertFalse(candidates[1].license.allowed_for_render)
        self.assertIn("all_rights_reserved", candidates[1].policy_decision["reason"])

    def test_envato_manual_prepare_generates_manifest_without_browser_or_download(self) -> None:
        from src.providers.envato_manual_provider import EnvatoManualProvider

        with tempfile.TemporaryDirectory() as tmp:
            provider = EnvatoManualProvider(projects_root=tmp)
            with patch("webbrowser.open", side_effect=AssertionError("browser opened")):
                manifest = provider.prepare_request(
                    project_id="project_001",
                    scene_id="scene_001",
                    scene={"visual_description": "Cinematic aerial shot of renewable energy infrastructure"},
                    queries=["renewable energy infrastructure aerial"],
                    limit=4,
                    open_browser=False,
                )

        self.assertEqual(manifest["provider"], "envato_manual")
        self.assertEqual(len(manifest["search_queries"]), 4)
        self.assertEqual(len(manifest["search_urls"]), 4)
        self.assertFalse(manifest["automatic_download"])
        self.assertIn("source_url", manifest["required_metadata_checklist"])

    def test_envato_manual_import_requires_source_proof_and_confirmation(self) -> None:
        from src.providers.envato_manual_provider import EnvatoManualProvider

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            media = root / "downloaded.jpg"
            proof = root / "certificate.txt"
            Image.new("RGB", (1080, 1920), (90, 40, 20)).save(media)
            proof.write_text("registration proof", encoding="utf-8")
            provider = EnvatoManualProvider(projects_root=root)

            blocked = provider.import_asset(
                project_id="project_001",
                scene_id="scene_001",
                file=media,
                source_url="",
                item_id="item-1",
                author="Envato Author",
                license_proof=proof,
                confirm_project_registration=False,
            )
            imported = provider.import_asset(
                project_id="project_001",
                scene_id="scene_001",
                file=media,
                source_url="https://elements.envato.com/item-1",
                item_id="item-1",
                author="Envato Author",
                license_proof=proof,
                confirm_project_registration=True,
            )

            self.assertTrue(blocked.license.review_required)
            self.assertFalse(blocked.license.allowed_for_render)
            self.assertTrue(imported.license.allowed_for_render)
            self.assertFalse(imported.license.review_required)
            self.assertTrue(Path(imported.local_path).is_file())
            self.assertEqual(imported.provenance.provider, "envato_manual")
            self.assertNotIn("registration proof", json.dumps(imported.to_manifest_dict()))
            self.assertTrue(Path(imported.raw_metadata["license_proof_reference"]).is_file())


class WikimediaHttpStub:
    def __init__(self, *, search_pages: list[dict], imageinfo_by_title: dict[str, dict], download_fixture: Path | None = None) -> None:
        self.search_pages = search_pages
        self.imageinfo_by_title = imageinfo_by_title
        self.download_fixture = download_fixture
        self.downloads: list[str] = []

    def get_json(self, url: str, *, headers=None, params=None, timeout=None) -> dict:
        params = params or {}
        if params.get("list") == "search":
            return {"query": {"search": self.search_pages}}
        if params.get("prop") == "imageinfo":
            titles = str(params.get("titles") or "").split("|")
            pages = {}
            for index, title in enumerate(titles, start=1):
                page = next((item for item in self.search_pages if item["title"] == title), {"pageid": index, "title": title})
                pages[str(page["pageid"])] = {"pageid": page["pageid"], "title": title, "imageinfo": [self.imageinfo_by_title[title]]}
            return {"query": {"pages": pages}}
        return {}

    def download_stream(self, url: str, target: str | Path, **kwargs) -> dict:
        if not self.download_fixture:
            raise AssertionError("download fixture missing")
        from src.assets.download import sha256_file

        target = Path(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(self.download_fixture.read_bytes())
        self.downloads.append(url)
        return {"path": str(target), "bytes": target.stat().st_size, "checksum_sha256": sha256_file(target), "content_type": "image/jpeg"}


class NasaHttpStub:
    def __init__(self, *, search_items: list[dict], assets: dict[str, list[str]], metadata: dict[str, dict]) -> None:
        self.search_items = search_items
        self.assets = assets
        self.metadata = metadata

    def get_json(self, url: str, *, headers=None, params=None, timeout=None) -> dict:
        if url.endswith("/search"):
            return {"collection": {"items": self.search_items}}
        if "/asset/" in url:
            nasa_id = url.rsplit("/", 1)[-1]
            return {"collection": {"items": [{"href": href} for href in self.assets.get(nasa_id, [])]}}
        if "/metadata/" in url:
            nasa_id = url.rsplit("/", 1)[-1]
            return self.metadata.get(nasa_id, {})
        return {}


class InternetArchiveHttpStub:
    def __init__(self, *, docs: list[dict], metadata: dict[str, dict]) -> None:
        self.docs = docs
        self.metadata = metadata

    def get_json(self, url: str, *, headers=None, params=None, timeout=None) -> dict:
        if "advancedsearch" in url:
            return {"response": {"docs": self.docs}}
        identifier = url.rstrip("/").rsplit("/", 1)[-1]
        return self.metadata.get(identifier, {"metadata": {}, "files": []})


def nasa_search_item(nasa_id: str, *, title: str, media_type: str = "image", keywords: list[str] | None = None, center: str = "NASA", description: str = "") -> dict:
    return {
        "href": f"https://images-assets.nasa.gov/{media_type}/{nasa_id}/collection.json",
        "links": [{"href": f"https://images-assets.nasa.gov/{media_type}/{nasa_id}/{nasa_id}~thumb.jpg", "rel": "preview"}],
        "data": [
            {
                "nasa_id": nasa_id,
                "title": title,
                "description": description or title,
                "keywords": keywords or [],
                "media_type": media_type,
                "date_created": "2024-01-01T00:00:00Z",
                "center": center,
                "photographer": "NASA",
                "location": "Earth orbit",
            }
        ],
    }


if __name__ == "__main__":
    unittest.main()
