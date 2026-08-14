from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


def _russian_energy_library(root: Path) -> dict[str, object]:
    """A controlled library labelled the way this project labels its own records.

    Four clips each carry the vocabulary of one scene, plus one unrelated clip that is
    by far the longest - the shape that decided every shortlist while the query was
    being thrown away.
    """
    from src.media_library import register_asset

    records = [
        ("solar", ["солнечная", "панель", "фотоэлектрические", "ячейки"], 12.0),
        ("battery", ["аккумуляторы", "накопитель", "энергия", "хранение"], 12.0),
        ("factory", ["завод", "конвейер", "сборка", "панелей"], 12.0),
        ("wind", ["ветряк", "турбина", "закат"], 12.0),
        ("long_unrelated", ["jungle", "canopy", "river"], 90.0),
    ]
    index: dict[str, object] = {"version": 1, "items": []}
    for asset_id, keywords, duration in records:
        path = root / f"{asset_id}.mp4"
        path.write_bytes(b"dummy")
        register_asset(
            index,
            {
                "id": asset_id,
                "type": "video",
                "provider": "fake",
                "provider_asset_id": asset_id,
                "local_path": str(path),
                "source_url": f"https://fake.local/video/{asset_id}",
                "keywords": keywords,
                "width": 1920,
                "height": 1080,
                "duration": duration,
                "schema_version": 1,
                "rights_status": "licensed",
                "allowed_for_render": True,
                "review_required": False,
                "license": {
                    "license_name": "fake_test_license",
                    "rights_status": "licensed",
                    "allowed_for_render": True,
                    "review_required": False,
                },
                "provenance": {"provider": "fake", "provider_asset_id": asset_id},
            },
        )
    return index


class MediaLibraryTests(unittest.TestCase):
    def test_generate_semantic_filename_is_safe_and_descriptive(self) -> None:
        from src.media_library import generate_semantic_filename

        filename = generate_semantic_filename(
            media_type="video",
            provider="Pexels",
            channel="Survival Stories",
            keywords=["Amazon jungle", "rain/storm", "Plane crash"],
            mood=["Dark", "tense"],
            width=1920,
            height=1080,
            short_id="ABC 123",
        )

        self.assertEqual(filename, "pexels_video_survival_stories_amazon_jungle_rain_storm_plane_crash_dark_tense_1920x1080_abc_123.mp4")
        self.assertLessEqual(len(filename), 140)

    def test_register_asset_load_save_and_duplicate_detection(self) -> None:
        from src.media_library import avoid_duplicate_downloads, load_media_index, register_asset, save_media_index

        with TemporaryDirectory() as tmp:
            index_path = Path(tmp) / "metadata" / "media_index.json"
            index = load_media_index(index_path)
            self.assertEqual(index, {"version": 1, "items": []})

            item = register_asset(
                index,
                {
                    "type": "video",
                    "provider": "pexels",
                    "source_url": "https://example.com/video/1",
                    "local_path": str(Path(tmp) / "videos" / "clip.mp4"),
                    "keywords": ["jungle", "rain"],
                    "mood": ["dark"],
                    "channel_tags": ["survival"],
                    "width": 1920,
                    "height": 1080,
                    "duration": 8,
                },
            )
            save_media_index(index, index_path)
            reloaded = load_media_index(index_path)

            self.assertEqual(len(reloaded["items"]), 1)
            self.assertEqual(reloaded["items"][0]["id"], item["id"])
            self.assertIsNotNone(avoid_duplicate_downloads(reloaded, source_url="https://example.com/video/1"))
            self.assertIsNotNone(avoid_duplicate_downloads(reloaded, local_path=str(Path(tmp) / "videos" / "clip.mp4")))

    def test_search_local_assets_scores_scene_relevance(self) -> None:
        from src.media_library import register_asset, search_local_assets

        with TemporaryDirectory() as tmp:
            video_path = Path(tmp) / "jungle.mp4"
            image_path = Path(tmp) / "city.jpg"
            video_path.write_bytes(b"dummy")
            image_path.write_bytes(b"dummy")
            index = {"version": 1, "items": []}
            register_asset(
                index,
                {
                    "type": "video",
                    "provider": "local",
                    "local_path": str(video_path),
                    "keywords": ["amazon", "jungle", "rain"],
                    "mood": ["dark"],
                    "channel_tags": ["survival"],
                    "scene_tags": ["crash"],
                    "width": 1920,
                    "height": 1080,
                    "duration": 10,
                },
            )
            register_asset(
                index,
                {
                    "type": "image",
                    "provider": "local",
                    "local_path": str(image_path),
                    "keywords": ["city"],
                    "mood": ["bright"],
                    "channel_tags": ["quotes"],
                    "width": 800,
                    "height": 800,
                    "duration": 0,
                },
            )

            matches = search_local_assets(
                index,
                {
                    "visual_keywords": ["amazon", "river"],
                    "mood": "dark",
                    "scene_type": "crash",
                    "duration": 6,
                },
                media_type="video",
                channel="survival",
                min_score=4,
            )

        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["asset"]["local_path"], str(video_path))
        self.assertGreaterEqual(matches[0]["score"], 10)

    def test_mark_asset_used_in_video_is_idempotent(self) -> None:
        from src.media_library import mark_asset_used_in_video, register_asset

        index = {"version": 1, "items": []}
        item = register_asset(index, {"type": "music", "provider": "local", "local_path": "assets/music/background.mp3"})

        mark_asset_used_in_video(index, item["id"], "survival/juliane")
        mark_asset_used_in_video(index, item["id"], "survival/juliane")

        self.assertEqual(index["items"][0]["used_in"], ["survival/juliane"])

    def test_migration_dry_run_marks_legacy_records_for_review_without_mutating_index(self) -> None:
        from src.media_library import build_media_library_migration_report

        index = {
            "version": 1,
            "items": [
                {
                    "id": "legacy_1",
                    "type": "video",
                    "provider": "pexels",
                    "local_path": "assets/library/videos/legacy.mp4",
                    "source_url": "https://www.pexels.com/video/1/",
                    "license_note": "Pexels license",
                }
            ],
        }
        before = {"version": index["version"], "items": [dict(index["items"][0])]}

        report = build_media_library_migration_report(index)

        self.assertEqual(index, before)
        self.assertEqual(report["schema_version"], 1)
        self.assertEqual(report["total_items"], 1)
        self.assertEqual(report["items"][0]["migration_status"], "legacy_unknown")
        self.assertTrue(report["items"][0]["review_required"])
        self.assertFalse(report["items"][0]["commercial_use_allowed"])

    def test_duplicate_detection_can_use_checksum_for_new_records(self) -> None:
        from src.media_library import avoid_duplicate_downloads, register_asset

        index = {"version": 1, "items": []}
        register_asset(
            index,
            {
                "type": "video",
                "provider": "fake",
                "local_path": "assets/library/videos/clip.mp4",
                "checksum_sha256": "b" * 64,
                "rights_status": "licensed",
            },
        )

        duplicate = avoid_duplicate_downloads(index, source_url="", local_path="", download_url="", checksum_sha256="b" * 64)

        self.assertIsNotNone(duplicate)
        self.assertEqual(duplicate["checksum_sha256"], "b" * 64)

    def test_local_search_reads_the_language_the_scripts_are_written_in(self) -> None:
        """A Russian query must reach the comparison instead of vanishing at tokenization.

        With an ASCII-only split every Cyrillic letter is a separator, so the query
        contributes no tokens, every horizontal video ties on type+aspect+duration and
        the shortlist degenerates into "the longest clips in the index" - identical for
        every scene of the project.
        """
        from src.media_library import tokenize as _tokens

        self.assertEqual(_tokens(["солнечная панель"]), ["солнечная", "панель"])
        self.assertEqual(_tokens(["панель ловит Солнечная"]), ["панель", "ловит", "солнечная"])
        self.assertEqual(_tokens(["solar panel"]), ["solar", "panel"])

    def test_russian_queries_of_different_meaning_get_different_shortlists(self) -> None:
        from src.media_library import search_local_assets

        with TemporaryDirectory() as tmp:
            index = _russian_energy_library(Path(tmp))
            expected = {
                "солнечная панель": "solar",
                "аккумуляторы энергия": "battery",
                "завод сборка панелей": "factory",
                "ветряк закат": "wind",
            }

            tops = {}
            for query, wanted in expected.items():
                matches = search_local_assets(
                    index,
                    {
                        "visual_keywords": query.split(),
                        "scene_type": "video",
                        "duration": 6,
                    },
                    media_type="video",
                    channel="",
                    min_score=1,
                    limit=10,
                )
                top = matches[0]["asset"]["id"]
                tops[query] = top

                self.assertEqual(top, wanted, f"{query!r} ranked {top!r} first")
                self.assertGreater(
                    matches[0]["score"],
                    3,
                    f"{query!r} scored no keyword hit at all",
                )
                # The longest clip in the index is unrelated to every one of these
                # scenes and must not lead on type/aspect/duration alone.
                self.assertNotEqual(top, "long_unrelated")

            self.assertEqual(len(set(tops.values())), len(expected))

    def test_production_local_ranking_follows_the_scene_not_the_duration(self) -> None:
        """The same defect through the path the manifest builder actually runs."""
        from src.news.asset_manifest_builder import rank_local_assets

        with TemporaryDirectory() as tmp:
            index = _russian_energy_library(Path(tmp))
            scenes = {
                "аккумуляторы держат энергия": "battery",
                "завод сборка панелей": "factory",
            }

            for query, wanted in scenes.items():
                ranked = rank_local_assets(
                    index,
                    {
                        "primary_query": query,
                        "visual_type": "video",
                        "target_duration_sec": 6,
                    },
                    "",
                    set(),
                )

                self.assertEqual(ranked[0]["asset_id"], wanted, f"{query!r}")

    def test_both_local_library_matchers_read_the_same_words(self) -> None:
        """One answer to "what are the words in this text" across the local library.

        The provider tokenized on whitespace and the coarse matcher on ASCII runs, so
        the two disagreed on punctuation *and* on whether Cyrillic exists at all.
        """
        from src.media_library import tokenize as coarse_tokens
        from src.providers.local_library_provider import _tokens as provider_tokens

        text = "Солнечная панель, photovoltaic-cells: завод."

        self.assertEqual(provider_tokens(text), set(coarse_tokens([text])))
        self.assertEqual(
            provider_tokens(text),
            {"солнечная", "панель", "photovoltaic", "cells", "завод"},
        )

    def test_registered_record_keeps_what_the_frame_shows(self) -> None:
        """``LocalLibraryStockProvider`` searches title/description, so the writer must keep them."""
        from src.media_library import register_asset
        from src.providers.local_library_provider import LocalLibraryStockProvider
        from src.assets.provider_contract import AssetSearchRequest

        with TemporaryDirectory() as tmp:
            video_path = Path(tmp) / "clip.mp4"
            video_path.write_bytes(b"dummy")
            index = {"version": 1, "items": []}
            register_asset(
                index,
                {
                    "type": "video",
                    "provider": "fake",
                    "provider_asset_id": "1",
                    "local_path": str(video_path),
                    "source_url": "https://fake.local/video/1",
                    "description": "airport terminal under a storm sky",
                    "title": "airport terminal under a storm sky",
                    "original_query": "storm clouds rainforest",
                    "keywords": ["airport", "terminal"],
                    "schema_version": 1,
                    "rights_status": "licensed",
                    "allowed_for_render": True,
                    "review_required": False,
                    "license": {
                        "license_name": "fake_test_license",
                        "license_url": "https://fake.local/license",
                        "rights_status": "licensed",
                        "allowed_for_render": True,
                        "review_required": False,
                    },
                    "provenance": {"provider": "fake", "provider_asset_id": "1"},
                },
            )

            self.assertEqual(index["items"][0]["description"], "airport terminal under a storm sky")

            provider = LocalLibraryStockProvider(index=index)
            found = provider.search(AssetSearchRequest(query="terminal", media_type="video"))

        self.assertEqual([candidate.provider_asset_id for candidate in found], ["1"])


if __name__ == "__main__":
    unittest.main()
