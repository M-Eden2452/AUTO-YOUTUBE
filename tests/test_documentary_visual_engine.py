from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.channel_loader import load_channel_video_config
from src.config_loader import load_config
from src.quote_generator import build_quote_plan
from src.scene_planner import build_scene_plan
from src.youtube_metadata import generate_youtube_metadata


class DocumentaryVisualEngineTests(unittest.TestCase):
    def _survival_scene_plan(self) -> tuple[dict, dict]:
        config = load_channel_video_config(load_config("config/video_style.json", dev=True), "survival", "juliane_koepcke_001")
        quote_plan = build_quote_plan(config)
        metadata = generate_youtube_metadata(config, quote_plan)
        scene_plan = build_scene_plan(config, quote_plan, metadata)
        return config, scene_plan

    def test_video_asset_engine_builds_multi_clip_scene_plan_and_debug(self) -> None:
        from src.video_asset_engine import build_documentary_asset_plan

        config, scene_plan = self._survival_scene_plan()
        with TemporaryDirectory() as tmp:
            config["asset_cache_dir"] = str(Path(tmp) / "videos")
            config["image_cache_dir"] = str(Path(tmp) / "images")
            config["plans"]["visual_debug"] = str(Path(tmp) / "visual_debug.json")
            config["documentary_asset_search"] = {"enabled": False}
            asset_plan = build_documentary_asset_plan(config, scene_plan, refresh=False)

        first_scene = asset_plan["scene_assets"][0]
        self.assertEqual(asset_plan["engine"], "documentary_visual_engine_v2")
        self.assertGreaterEqual(len(first_scene["queries"]), 3)
        self.assertGreaterEqual(len(first_scene["clips"]), 3)
        self.assertAlmostEqual(sum(float(clip["duration"]) for clip in first_scene["clips"]), float(scene_plan["scenes"][0]["duration"]), delta=0.2)
        self.assertIn("visual_debug_path", asset_plan)
        self.assertIn("rejected_clips", asset_plan["visual_debug"][0])

    def test_music_engine_returns_voice_over_ready_plan(self) -> None:
        from src.music_engine import build_music_plan_v2

        config, scene_plan = self._survival_scene_plan()
        with TemporaryDirectory() as tmp:
            config["music_cache_dir"] = str(Path(tmp) / "music")
            music_plan = build_music_plan_v2(config, scene_plan)

        self.assertEqual(music_plan["engine"], "music_engine_v2")
        self.assertLessEqual(float(music_plan["volume"]), 0.16)
        self.assertIn("fade_in", music_plan["fade_points"])
        self.assertIn("queries", music_plan)
        self.assertGreaterEqual(len(music_plan["queries"]), 4)

    def test_render_plan_marks_documentary_montage_strategy(self) -> None:
        from src.video_renderer import build_render_plan

        config, scene_plan = self._survival_scene_plan()
        asset_plan = {
            "engine": "documentary_visual_engine_v2",
            "scene_assets": [
                {
                    "scene_number": scene["scene_number"],
                    "clips": [{"type": "generated_motion", "path": "", "duration": scene["duration"]}],
                }
                for scene in scene_plan["scenes"]
            ],
            "music": {"path": "", "status": "music_not_found", "volume": 0.12},
        }
        render_plan = build_render_plan(config, scene_plan, asset_plan, asset_plan["music"])

        self.assertEqual(render_plan["render_strategy"], "documentary_scene_montage")
        self.assertTrue(render_plan["subtitle_safe_area"])
        self.assertLessEqual(render_plan["fps"], 10)
        self.assertEqual(render_plan["preset"], "ultrafast")


if __name__ == "__main__":
    unittest.main()
