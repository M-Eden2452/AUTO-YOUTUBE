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
        self.assertGreaterEqual(len(first_scene["clips"]), 1)
        self.assertLessEqual(len(first_scene["clips"]), 4)
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
        self.assertLessEqual(render_plan["fps"], 24)
        self.assertTrue(render_plan["visual_rules"]["no_scene_labels"])
        self.assertEqual(render_plan["subtitle_style"]["name"], "cinematic_documentary_v2")
        self.assertLessEqual(render_plan["music"]["volume"], 0.12)
        self.assertEqual(render_plan["montage"]["target_clip_seconds"], [4.0, 30.0])

    def test_cinematic_preview_profile_prefers_quality_over_speed(self) -> None:
        from src.config_loader import load_config
        from src.channel_loader import load_channel_video_config
        from src.video_renderer import build_render_plan, validation_tolerance_for_duration

        config = load_channel_video_config(load_config("config/video_style.json", cinematic_preview=True), "survival", "juliane_koepcke_001")
        scene_plan = {"scenes": [{"scene_number": 1, "duration": 12, "scene_type": "story"}]}
        asset_plan = {"engine": "documentary_visual_engine_v2", "scene_assets": [{"scene_number": 1, "clips": []}], "music": {"path": "", "volume": 0.11}}

        render_plan = build_render_plan(config, scene_plan, asset_plan, asset_plan["music"])

        self.assertTrue(config["cinematic_preview"])
        self.assertEqual(render_plan["fps"], 24)
        self.assertIn(render_plan["preset"], {"medium", "slow"})
        self.assertLessEqual(render_plan["encoding"]["crf"], 20)
        self.assertEqual(render_plan["render_profile"], "cinematic_preview")
        self.assertGreaterEqual(validation_tolerance_for_duration(660), 4.0)

    def test_adaptive_pacing_uses_scene_mood_and_voice_duration(self) -> None:
        from src.video_asset_engine import adaptive_shot_duration, target_clip_count_for_scene

        calm = {"duration": 18, "mood": "calm jungle atmosphere", "scene_type": "story", "voice_duration": 13}
        storm = {"duration": 16, "mood": "shock storm tension", "scene_type": "story", "voice_duration": 10}
        reflection = {"duration": 20, "mood": "emotional reflection", "scene_type": "reflection", "voice_duration": 14}

        self.assertGreaterEqual(adaptive_shot_duration(calm), 8)
        self.assertLessEqual(adaptive_shot_duration(storm), 8)
        self.assertGreaterEqual(adaptive_shot_duration(reflection), 10)
        self.assertLess(target_clip_count_for_scene(calm), target_clip_count_for_scene(storm))

    def test_voice_engine_builds_scene_manifest_and_reuses_cache(self) -> None:
        from src.voice_engine import build_voice_manifest

        scene_plan = {
            "scenes": [
                {"scene_number": 1, "scene_id": "intro", "subtitle_text": "Тихий дождь над джунглями.", "duration": 8},
                {"scene_number": 2, "scene_id": "storm", "subtitle_text": "Гроза стала сильнее.", "duration": 7},
            ]
        }
        with TemporaryDirectory() as tmp:
            config = {
                "channel_id": "survival",
                "video_id": "voice_test",
                "output_dir": tmp,
                "plans": {"voice_manifest": str(Path(tmp) / "voice_manifest.json")},
                "voice": {"enabled": True, "provider": "local_stub", "cache_dir": str(Path(tmp) / "voice_cache")},
            }
            first = build_voice_manifest(config, scene_plan, reuse_voice=True, skip_voice=False)
            second = build_voice_manifest(config, scene_plan, reuse_voice=True, skip_voice=False)

            self.assertEqual(first["engine"], "voice_engine_v1")
            self.assertEqual(len(first["scenes"]), 2)
            self.assertTrue(all(Path(item["path"]).exists() for item in first["scenes"]))
            self.assertTrue(all(item["cache_status"] == "reused" for item in second["scenes"]))
            self.assertGreater(first["total_voice_duration"], 0)

    def test_voice_engine_falls_back_to_moss_when_elevenlabs_fails(self) -> None:
        from unittest.mock import patch

        from src.voice_engine import build_voice_manifest

        scene_plan = {
            "scenes": [
                {"scene_number": 1, "scene_id": "intro", "subtitle_text": "Тестовая русская фраза.", "duration": 8},
            ]
        }
        with TemporaryDirectory() as tmp:
            config = {
                "channel_id": "psychology",
                "video_id": "voice_test",
                "output_dir": tmp,
                "plans": {"voice_manifest": str(Path(tmp) / "voice_manifest.json")},
                "voice": {
                    "enabled": True,
                    "provider": "elevenlabs",
                    "voice_id": "voice",
                    "cache_dir": str(Path(tmp) / "voice_cache"),
                    "fallback_provider": "moss_tts_nano",
                    "moss_tts_path": "G:/Projects/AI-YouTube/MOSS_TTS_Nano",
                },
            }

            def fake_moss(text, output_path, moss_config):
                target = Path(output_path)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(b"RIFFfake-wave")
                return target

            with patch.dict("os.environ", {"ELEVENLABS_API_KEY": "test-key"}), patch(
                "src.voice_engine._generate_elevenlabs_voice",
                side_effect=RuntimeError("eleven down"),
            ), patch("src.voice_engine._generate_moss_voice", side_effect=fake_moss):
                manifest = build_voice_manifest(config, scene_plan, reuse_voice=False, skip_voice=False)

            self.assertEqual(manifest["scenes"][0]["provider"], "moss_tts_nano")
            self.assertTrue(Path(manifest["scenes"][0]["path"]).exists())
            self.assertTrue(any("ElevenLabs voice request failed" in item for item in manifest["warnings"]))
            self.assertTrue(any("MOSS-TTS-Nano fallback used" in item for item in manifest["warnings"]))

    def test_manual_video_assets_are_used_before_library_and_api(self) -> None:
        from src.video_asset_engine import build_documentary_asset_plan

        scene_plan = {
            "scenes": [
                {
                    "scene_number": 1,
                    "scene_id": "intro",
                    "scene_type": "intro",
                    "duration": 12,
                    "visual_keywords": ["rain apartment window"],
                    "mood": "night rain",
                }
            ]
        }
        with TemporaryDirectory() as tmp:
            manual_root = Path(tmp) / "manual_assets" / "psychology" / "overloaded_mind_001"
            video_path = manual_root / "video" / "rain_window.mp4"
            video_path.parent.mkdir(parents=True)
            video_path.write_bytes(b"manual-video-placeholder")
            config = {
                "channel_id": "psychology",
                "video_id": "overloaded_mind_001",
                "output_filename": str(Path(tmp) / "final_preview.mp4"),
                "asset_library": {"root": str(Path(tmp) / "library"), "download_if_not_enough": False},
                "manual_assets": {"root": str(manual_root)},
                "documentary_asset_search": {"enabled": False},
                "plans": {"visual_debug": str(Path(tmp) / "visual_debug.json")},
            }

            asset_plan = build_documentary_asset_plan(config, scene_plan, refresh=False)

        first = asset_plan["scene_assets"][0]
        self.assertEqual(first["provider"], "manual_asset")
        self.assertEqual(first["asset_source"], "manual_assets")
        self.assertEqual(first["clips"][0]["path"], str(video_path))

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
            "montage": {"target_clip_seconds": [4.0, 30.0], "average_shot_seconds": 9.0},
            "fps": 24,
            "voice": {"enabled": True},
            "music": {"ducking": True},
        }

        result = evaluate_documentary_quality_rules(asset_plan, render_plan)

        self.assertFalse(result["warnings"])
        self.assertIn("No scene labels configured for documentary render.", result["checks"])


if __name__ == "__main__":
    unittest.main()
