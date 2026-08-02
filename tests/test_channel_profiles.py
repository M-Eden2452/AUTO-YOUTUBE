"""Test classification: LEGACY ANCHOR

Protects:
- чтение legacy-каналов ``quotes`` и ``survival`` через ``config_loader`` и
  ``channel_loader``: раскладку выходных путей, поля ``video_task`` и
  построение quote/scene/metadata планов легаси-движками;
- поведение старого ``config/video_style.json`` без ``channel_id``.

Does not prove:
- что описанное является продуктовым контрактом активного продукта: эти каналы
  не поддерживаются ни одним шаблоном ``content_creator`` (gate 8E, ADR 0013);
- что содержимое каналов и ``content/`` — пользовательские данные: реестр
  относит их к fixtures легаси-стека (N04);
- что эти проверки должны пережить ретайр. Класс — LEGACY ANCHOR
  (``docs/current/CLEANUP_REGISTRY.md``, «Accidental invariants»): полезные
  проверки извлекает Knowledge Salvage Gate, после чего модуль ретайрится
  вместе со стеком по gate PLAN-L0 → PLAN-L3.
"""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.config_loader import load_config
from src.quote_generator import build_quote_plan
from src.scene_planner import build_scene_plan
from src.youtube_metadata import generate_youtube_metadata


class ChannelProfileTests(unittest.TestCase):
    def test_old_config_without_channel_keeps_root_outputs(self) -> None:
        config = load_config("config/video_style.json", dev=True)

        self.assertEqual(config["output_filename"], "outputs/final_preview.mp4")
        self.assertEqual(config["plans"]["quote_plan"], "outputs/quote_plan.json")
        self.assertNotIn("channel_id", config)

    def test_quotes_video_task_overrides_outputs_and_metadata(self) -> None:
        from src.channel_loader import load_channel_video_config
        from src.config_resolver import resolve_application_paths

        base_config = load_config("config/video_style.json", dev=True)
        config = load_channel_video_config(
            base_config,
            "quotes",
            "thoughts_too_late_001",
            obsidian_vault="D:/Notes",
        )

        output_dir = (
            resolve_application_paths().outputs_root
            / "quotes"
            / "thoughts_too_late_001"
        )
        self.assertEqual(config["channel_id"], "quotes")
        self.assertEqual(config["video_id"], "thoughts_too_late_001")
        self.assertEqual(config["output_filename"], str(output_dir / "final_preview.mp4"))
        self.assertEqual(config["prod_output_filename"], str(output_dir / "final_video.mp4"))
        self.assertEqual(config["plans"]["quote_plan"], str(output_dir / "quote_plan.json"))
        self.assertEqual(config["plans"]["scene_plan"], str(output_dir / "scene_plan.json"))
        self.assertEqual(config["plans"]["youtube_metadata"], str(output_dir / "youtube_metadata.json"))
        self.assertEqual(config["topic"], "Некоторые мысли приходят слишком поздно")
        self.assertEqual(config["visual_style"], "dark cinematic existential noir documentary")
        self.assertEqual(len(config["video_task"]["scenes"]), 15)
        self.assertEqual(
            config["obsidian"]["video_note_dir"],
            "D:/Notes/YouTube/02 Видео/Цитаты и мысли/thoughts_too_late_001",
        )

    def test_video_task_drives_quote_scene_and_metadata_plans(self) -> None:
        from src.channel_loader import load_channel_video_config

        config = load_channel_video_config(load_config("config/video_style.json", dev=True), "quotes", "thoughts_too_late_001")
        quote_plan = build_quote_plan(config)
        metadata = generate_youtube_metadata(config, quote_plan)
        scene_plan = build_scene_plan(config, quote_plan, metadata)

        self.assertEqual(quote_plan["topic"], "Некоторые мысли приходят слишком поздно")
        self.assertEqual(quote_plan["quotes"][1]["author"], "Джош Биллингс")
        self.assertEqual(metadata["chosen_title"], "Некоторые мысли приходят слишком поздно")
        self.assertEqual(metadata["title_variants"][5], "Некоторые вещи человек понимает слишком поздно")
        self.assertEqual(scene_plan["scenes"][0]["scene_type"], "intro")
        self.assertEqual(scene_plan["scenes"][0]["screen_text"], config["video_task"]["scenes"][0]["screen_text"])
        self.assertEqual(scene_plan["scenes"][14]["scene_type"], "outro")
        self.assertEqual(scene_plan["target_duration"], 143.0)

    def test_survival_video_task_builds_story_metadata_and_paths(self) -> None:
        from src.channel_loader import load_channel_video_config
        from src.config_resolver import resolve_application_paths

        config = load_channel_video_config(load_config("config/video_style.json", dev=True), "survival", "juliane_koepcke_001")
        quote_plan = build_quote_plan(config)
        metadata = generate_youtube_metadata(config, quote_plan)
        scene_plan = build_scene_plan(config, quote_plan, metadata)

        self.assertEqual(config["channel_id"], "survival")
        self.assertEqual(config["person"], "Истории выживания")
        self.assertEqual(config["video_type"], "real_survival_story")
        output_dir = (
            resolve_application_paths().outputs_root
            / "survival"
            / "juliane_koepcke_001"
        )
        self.assertEqual(Path(config["output_filename"]), output_dir / "final_preview.mp4")
        self.assertEqual(Path(config["thumbnail_path"]), output_dir / "thumbnail.png")
        self.assertEqual(config["obsidian"]["video_note_dir"], "")
        self.assertFalse(config["obsidian"]["enabled"])
        self.assertEqual(metadata["chosen_title"], "Она упала с неба и 11 дней выживала в Амазонии")
        self.assertIn("LANSA Flight 508 crash, Peru, 1971", metadata["source_notes"])
        self.assertIn("chapters", metadata)
        self.assertIn("upload_ready_fields", metadata)
        self.assertFalse(metadata["upload_ready_fields"]["made_for_kids"])
        self.assertEqual(scene_plan["scenes"][0]["subtitle_text"], config["video_task"]["scenes"][0]["subtitle_text"])
        self.assertGreaterEqual(scene_plan["target_duration"], 180.0)

    def test_thumbnail_generator_creates_png_for_video_task(self) -> None:
        from src.channel_loader import load_channel_video_config
        from src.thumbnail_generator import create_thumbnail

        config = load_channel_video_config(load_config("config/video_style.json", dev=True), "survival", "juliane_koepcke_001")
        with TemporaryDirectory() as tmp:
            target = Path(tmp) / "thumbnail.png"
            created = create_thumbnail(config, {}, target)

            self.assertEqual(created, target)
            self.assertTrue(target.exists())
            self.assertGreater(target.stat().st_size, 1000)


if __name__ == "__main__":
    unittest.main()
