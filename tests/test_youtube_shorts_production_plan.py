from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path


class YoutubeShortsProductionPlanTests(unittest.TestCase):
    def test_solar_vs_nuclear_plan_creates_required_folders_and_files(self) -> None:
        from src.production_plan.youtube_shorts import create_solar_vs_nuclear_plan

        with tempfile.TemporaryDirectory() as tmp:
            project = create_solar_vs_nuclear_plan(Path(tmp))

            self.assertEqual(project["config"]["project_id"], "solar_vs_nuclear")
            for rel in [
                "01_script/script_ru.txt",
                "01_script/voiceover_ru.txt",
                "01_script/fact_sources.txt",
                "02_voice",
                "03_stock/nuclear",
                "03_stock/solar",
                "03_stock/weather",
                "03_stock/city_scale",
                "03_stock/battery_storage",
                "04_motion/counter_panels",
                "04_motion/capacity_factor",
                "04_motion/annual_energy",
                "04_motion/land_area",
                "05_project/capcut",
                "05_project/exports",
                "06_analytics/metrics_24h.json",
                "06_analytics/metrics_7d.json",
                "06_analytics/retention_screenshots",
                "project_config.json",
                "scenes.json",
                "preview.html",
                "render_readiness.json",
            ]:
                self.assertTrue((project["root"] / rel).exists(), rel)

    def test_scene_json_contains_machine_readable_asset_fields(self) -> None:
        from src.production_plan.youtube_shorts import create_solar_vs_nuclear_plan

        with tempfile.TemporaryDirectory() as tmp:
            project = create_solar_vs_nuclear_plan(Path(tmp))
            scenes = json.loads((project["root"] / "scenes.json").read_text(encoding="utf-8"))["scenes"]

            self.assertEqual(len(scenes), 12)
            first = scenes[0]
            self.assertEqual(first["asset_type"], ["stock", "composite", "motion"])
            self.assertEqual(first["status"], "pending")
            self.assertIn("nuclear power plant", first["positive_keywords"])
            self.assertIn("Chernobyl", first["negative_keywords"])
            self.assertIn("single solar panel close up", first["search_queries"])
            self.assertIn("subject", first["semantic_scene"])
            # PLAN-9B-3: the plan carries the canonical ladder in the same
            # ``{kind, fallback_level, query}`` items the asset manifest stores. It used
            # to be a dict keyed by the four fixed rungs of the retired generator - one
            # of which appended the literal word "nature" to whatever the scene said.
            for item in first["semantic_queries"]:
                self.assertEqual(set(item), {"kind", "fallback_level", "query"})
                self.assertTrue(item["query"].strip())
            levels = [item["fallback_level"] for item in first["semantic_queries"]]
            self.assertEqual(levels, sorted(levels))

    def test_the_retired_semantic_query_generator_is_gone_from_the_root_import_chain(self) -> None:
        """``pipeline.py`` imports this module, which imported the retired generator.

        The root entrypoint therefore has to keep importing cleanly after the deletion,
        and the retired module must not come back through any other path.
        """
        import importlib

        import pipeline

        self.assertTrue(hasattr(pipeline, "main"))
        with self.assertRaises(ModuleNotFoundError):
            importlib.import_module("src.assets.semantic_selection.query_generator")

        import src.assets.semantic_selection as semantic_selection

        self.assertNotIn("generate_queries", semantic_selection.__all__)
        self.assertNotIn("ordered_queries", semantic_selection.__all__)

    def test_manual_clip_replacement_updates_scene_status(self) -> None:
        from src.production_plan.youtube_shorts import create_solar_vs_nuclear_plan, replace_selected_clip

        with tempfile.TemporaryDirectory() as tmp:
            project = create_solar_vs_nuclear_plan(Path(tmp))
            clip = project["root"] / "03_stock" / "solar" / "clip.mp4"
            clip.write_bytes(b"fake")

            replace_selected_clip(project["root"], "scene_003", clip, provider="manual", note="approved")
            scenes = json.loads((project["root"] / "scenes.json").read_text(encoding="utf-8"))["scenes"]
            scene = next(item for item in scenes if item["scene_id"] == "scene_003")

            self.assertEqual(scene["status"], "selected")
            self.assertEqual(scene["selected_asset"]["path"], str(clip))
            self.assertEqual(scene["selected_asset"]["replacement_note"], "approved")

    def test_render_readiness_blocks_without_final_voice(self) -> None:
        from src.production_plan.youtube_shorts import check_render_readiness, create_solar_vs_nuclear_plan

        with tempfile.TemporaryDirectory() as tmp:
            project = create_solar_vs_nuclear_plan(Path(tmp))
            readiness = check_render_readiness(project["root"])

            self.assertEqual(readiness["status"], "blocked")
            self.assertIn("missing_voice_final", readiness["errors"])

    def test_render_readiness_reports_missing_materials(self) -> None:
        from src.production_plan.youtube_shorts import check_render_readiness, create_solar_vs_nuclear_plan

        with tempfile.TemporaryDirectory() as tmp:
            project = create_solar_vs_nuclear_plan(Path(tmp))
            voice = project["root"] / "02_voice" / "voice_final.wav"
            voice.write_bytes(b"fake")
            readiness = check_render_readiness(project["root"])

            self.assertEqual(readiness["status"], "blocked")
            self.assertIn("missing_scene_materials", readiness["errors"])
            self.assertEqual(len(readiness["missing_scenes"]), 12)

    def test_render_policy_allows_only_single_subtitle_text_layer(self) -> None:
        from src.production_plan.youtube_shorts import create_solar_vs_nuclear_plan

        with tempfile.TemporaryDirectory() as tmp:
            project = create_solar_vs_nuclear_plan(Path(tmp))
            policy = project["config"]["render_policy"]

            self.assertEqual(policy["allowed_text_layers"], ["ass_subtitles"])
            self.assertEqual(policy["subtitle_layers"], 1)
            self.assertFalse(policy["allow_overlay_text"])
            self.assertFalse(policy["allow_generated_motion_placeholders"])

    def test_render_readiness_blocks_generated_motion_assets(self) -> None:
        from src.production_plan.youtube_shorts import check_render_readiness, create_solar_vs_nuclear_plan

        with tempfile.TemporaryDirectory() as tmp:
            project = create_solar_vs_nuclear_plan(Path(tmp))
            voice = project["root"] / "02_voice" / "voice_final.wav"
            voice.write_bytes(b"fake")
            data = json.loads((project["root"] / "scenes.json").read_text(encoding="utf-8"))
            for scene in data["scenes"]:
                scene["selected_asset"] = {
                    "path": str(project["root"] / "03_stock" / "solar" / f"{scene['scene_id']}.mp4"),
                    "provider": "manual",
                    "type": "video",
                    "visual_review_status": "approved",
                }
            data["scenes"][3]["selected_asset"] = {
                "path": str(project["root"] / "04_motion" / "counter_panels" / "scene_004_background.png"),
                "provider": "motion_design",
                "type": "motion",
            }
            (project["root"] / "scenes.json").write_text(json.dumps(data), encoding="utf-8")

            readiness = check_render_readiness(project["root"])

            self.assertEqual(readiness["status"], "blocked")
            self.assertIn("generated_visual_assets_not_allowed", readiness["errors"])

    def test_known_bad_snake_asset_is_rejected_for_solar_panel_scene(self) -> None:
        from src.production_plan.solar_vs_nuclear_render import _candidate
        from src.production_plan.youtube_shorts import create_solar_vs_nuclear_plan

        with tempfile.TemporaryDirectory() as tmp:
            project = create_solar_vs_nuclear_plan(Path(tmp))
            scenes = json.loads((project["root"] / "scenes.json").read_text(encoding="utf-8"))["scenes"]
            scene = next(item for item in scenes if item["scene_id"] == "scene_002")

            candidate = _candidate(
                provider="pixabay",
                source_id="212433",
                source_page="https://pixabay.com/videos/snake-forest-wildlife-212433/",
                download_url="https://example.invalid/snake.mp4",
                author="",
                license_name="pixabay",
                width=1920,
                height=1080,
                duration=8,
                query="utility scale solar module",
                scene=scene,
            )

            self.assertTrue(candidate["rejected"])
            self.assertIn("known_bad_visual_asset", candidate["reject_reason"])

    def test_stock_source_index_contains_provider_links_and_local_paths(self) -> None:
        from src.production_plan.solar_vs_nuclear_render import write_stock_source_index
        from src.production_plan.youtube_shorts import create_solar_vs_nuclear_plan

        with tempfile.TemporaryDirectory() as tmp:
            project = create_solar_vs_nuclear_plan(Path(tmp))
            scenes = json.loads((project["root"] / "scenes.json").read_text(encoding="utf-8"))["scenes"]
            scenes[0]["selected_asset"] = {
                "asset_id": "pexels_123",
                "provider": "pexels",
                "author": "Author Name",
                "license": "pexels",
                "rights_status": "licensed",
                "allowed_for_render": True,
                "source_page": "https://www.pexels.com/video/example/",
                "search_query": "solar panel close up",
                "width": 3840,
                "height": 2160,
                "duration": 12,
                "path": str(project["root"] / "03_stock" / "solar" / "scene_001_pexels_123.mp4"),
            }

            index = write_stock_source_index(project["root"], scenes)

            md = Path(index["markdown_path"]).read_text(encoding="utf-8")
            self.assertIn("pexels", md)
            self.assertIn("https://www.pexels.com/video/example/", md)
            self.assertIn("scene_001_pexels_123.mp4", md)
            self.assertTrue(Path(index["json_path"]).is_file())


if __name__ == "__main__":
    unittest.main()
