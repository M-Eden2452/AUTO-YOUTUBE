"""Test classification: LEGACY ANCHOR

Protects:
- реализацию ``src.size_comparison_engine``: чтение данных с сохранением
  disclaimer-пометок о мифических объектах, адаптивные стадии камеры вместо
  одного линейного масштаба, удаление белого и плоского цветного фона
  силуэта, приоритет abyss-фона над референсными изображениями и допуск
  warning-ов о fallback, когда рендер прошёл валидацию.

Does not prove:
- что формат сравнения размеров существует в активном продукте: движок входит
  в legacy content stack (C30, C33) и не имеет шаблона ``content_creator``;
- что capability исчезает вместе с движком: сам формат помечен как отдельный
  будущий product slice на новом canonical core (OD-10), и внутри PLAN-L он
  **не** мигрируется;
- что модуль защищает нужное поведение от изменения. Класс — LEGACY ANCHOR
  (``docs/current/CLEANUP_REGISTRY.md``, «Accidental invariants»): алгоритм,
  visual logic, edge cases и полезные проверки сохраняет Knowledge Salvage
  Gate, после чего движок и его тест удаляются; gate — PLAN-L0 → PLAN-L3.
"""

from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from src.size_comparison_engine import (
    build_size_asset_plan,
    build_camera_plan,
    evaluate_size_comparison,
    load_size_data,
    prepare_silhouette_asset,
)


class SizeComparisonEngineTests(unittest.TestCase):
    def test_load_size_data_preserves_mythical_disclaimer_notes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_path = Path(temp_dir) / "data.csv"
            with data_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=["name", "size_meters", "category", "source_note", "visual_priority"],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "name": "Leviathan",
                        "size_meters": "300",
                        "category": "mythical",
                        "source_note": "Fictional mythological interpretation",
                        "visual_priority": "7",
                    }
                )

            objects = load_size_data(data_path)

        self.assertEqual(objects[0].name, "Leviathan")
        self.assertEqual(objects[0].size_meters, 300)
        self.assertIn("interpretation", objects[0].source_note.lower())

    def test_camera_plan_uses_adaptive_stages_instead_of_one_linear_scale(self) -> None:
        objects = [
            ("Human", 1.8, "reference", 1),
            ("Great White Shark", 6, "real animal", 2),
            ("Megalodon", 18, "prehistoric", 5),
            ("Kraken", 100, "mythical", 6),
            ("Leviathan", 300, "mythical", 7),
            ("Jormungandr", 1000, "mythical", 8),
        ]
        plan = build_camera_plan(
            [
                {"name": name, "size_meters": size, "category": category, "source_note": "", "visual_priority": priority}
                for name, size, category, priority in objects
            ],
            resolution=(1280, 720),
            duration_seconds=210,
        )

        self.assertGreaterEqual(len(plan["stages"]), 3)
        self.assertNotEqual(plan["stages"][0]["meters_per_pixel"], plan["stages"][-1]["meters_per_pixel"])
        self.assertTrue(any(stage.get("reference_overlay") for stage in plan["stages"]))
        for stage in plan["stages"]:
            smallest_visible = min(item["visible_pixels"] for item in stage["objects"])
            self.assertGreaterEqual(smallest_visible, 42)

    def test_prepare_silhouette_asset_removes_white_background(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "shark.png"
            target = Path(temp_dir) / "processed" / "shark.png"
            image = Image.new("RGBA", (120, 60), (255, 255, 255, 255))
            draw = ImageDraw.Draw(image)
            draw.rectangle((20, 20, 100, 42), fill=(12, 20, 24, 255))
            image.save(source)

            result = prepare_silhouette_asset(source, target)
            processed = Image.open(result["processed_path"]).convert("RGBA")

        self.assertEqual(processed.getpixel((0, 0))[3], 0)
        self.assertGreater(processed.getpixel((60, 30))[3], 200)
        self.assertEqual(result["background"], "white_removed")

    def test_prepare_silhouette_asset_removes_flat_colored_background(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "kraken.png"
            target = Path(temp_dir) / "processed" / "kraken.png"
            image = Image.new("RGBA", (120, 60), (40, 92, 104, 255))
            draw = ImageDraw.Draw(image)
            draw.ellipse((28, 8, 92, 50), fill=(238, 244, 246, 255))
            image.save(source)

            result = prepare_silhouette_asset(source, target)
            processed = Image.open(result["processed_path"]).convert("RGBA")

        self.assertEqual(processed.getpixel((0, 0))[3], 0)
        self.assertGreater(processed.getpixel((60, 30))[3], 200)
        self.assertEqual(result["background"], "flat_color_removed")

    def test_asset_plan_prefers_abyss_background_over_reference_images(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            backgrounds = root / "backgrounds"
            images = root / "images"
            backgrounds.mkdir()
            images.mkdir()
            Image.new("RGB", (12, 12), "white").save(backgrounds / "aircraft carrier side view.png")
            Image.new("RGB", (12, 12), "navy").save(backgrounds / "underwater abyss backdrop.png")

            plan = build_size_asset_plan([], root, Path(temp_dir) / "out")

        self.assertIn("underwater abyss", plan["background"]["path"].lower())

    def test_self_eval_allows_asset_fallback_warnings_when_render_validates(self) -> None:
        result = evaluate_size_comparison(
            Path("preview.mp4"),
            {"warnings": ["No manual image matched Leviathan; generated silhouette placeholder will be used."]},
            {"stages": [{"reference_overlay": True}]},
            {"duration": 216, "fps": 24, "resolution": [1280, 720]},
            {"validation": {"ok": True, "errors": []}},
        )

        self.assertTrue(result["ok"])
        self.assertEqual(len(result["warnings"]), 1)


if __name__ == "__main__":
    unittest.main()
