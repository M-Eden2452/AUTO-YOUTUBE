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
        self.assertTrue(render_plan["visual_rules"]["no_scene_labels"])
        self.assertEqual(render_plan["subtitle_style"]["name"], "cinematic_documentary_v2")
        self.assertLessEqual(render_plan["music"]["volume"], 0.12)
        self.assertLessEqual(render_plan["montage"]["target_clip_seconds"][1], 6.0)

    def test_survival_overlay_is_subtitles_only(self) -> None:
        from src.layout_renderer import render_text_overlay

        config, scene_plan = self._survival_scene_plan()
        scene = scene_plan["scenes"][0]
        overlay = render_text_overlay(config, scene, 1280, 720)

        self.assertEqual(overlay.getbbox(), (0, 0, 1280, 720))
        self.assertEqual(overlay.info.get("subtitle_style"), "cinematic_documentary_v2")
        self.assertEqual(overlay.info.get("scene_labels"), "disabled")

    def test_survival_relevance_boost_prefers_rainforest_over_generic_city(self) -> None:
        from src.video_asset_engine import score_survival_relevance

        scene = {
            "visual_keywords": ["amazon jungle rain", "river survival"],
            "mood": "dark rainforest",
            "scene_type": "story",
        }

        jungle_score = score_survival_relevance(
            {
                "query": "tropical jungle rain",
                "provider": "pexels",
                "width": 1920,
                "height": 1080,
                "source_duration": 9,
            },
            scene,
            "survival",
        )
        city_score = score_survival_relevance(
            {
                "query": "business city airport terminal",
                "provider": "pexels",
                "width": 1920,
                "height": 1080,
                "source_duration": 9,
            },
            scene,
            "survival",
        )

        self.assertGreaterEqual(jungle_score - city_score, 25)

    def test_self_eval_checks_documentary_quality_rules(self) -> None:
        from src.self_eval import evaluate_documentary_quality_rules

        asset_plan = {
            "engine": "documentary_visual_engine_v2",
            "scene_assets": [
                {
                    "scene_number": 1,
                    "clips": [
                        {"type": "video", "provider": "pexels", "query": "amazon rainforest rain", "path": "a.mp4", "duration": 3.5},
                        {"type": "video", "provider": "pexels", "query": "jungle river", "path": "b.mp4", "duration": 4.0},
                        {"type": "video", "provider": "pexels", "query": "rainforest canopy", "path": "c.mp4", "duration": 3.0},
                    ],
                    "clip_count": 3,
                }
            ],
        }
        render_plan = {
            "visual_rules": {"no_scene_labels": True, "fullscreen_footage": True},
            "subtitle_style": {"name": "cinematic_documentary_v2"},
            "montage": {"target_clip_seconds": [3.0, 6.0]},
        }

        result = evaluate_documentary_quality_rules(asset_plan, render_plan)

        self.assertFalse(result["warnings"])
        self.assertIn("No scene labels configured for documentary render.", result["checks"])


if __name__ == "__main__":
    unittest.main()
