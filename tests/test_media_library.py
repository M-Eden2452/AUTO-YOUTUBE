from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


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
        item = register_asset(index, {"type": "music", "provider": "local", "local_path": "music/background.mp3"})

        mark_asset_used_in_video(index, item["id"], "survival/juliane")
        mark_asset_used_in_video(index, item["id"], "survival/juliane")

        self.assertEqual(index["items"][0]["used_in"], ["survival/juliane"])


if __name__ == "__main__":
    unittest.main()
