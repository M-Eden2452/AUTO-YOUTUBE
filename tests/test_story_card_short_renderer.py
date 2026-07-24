from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw


class StoryCardShortRendererTests(unittest.TestCase):
    def test_story_card_preset_contract(self) -> None:
        preset = json.loads(Path("config/render_presets/story_card_short_v1.json").read_text(encoding="utf-8"))

        self.assertEqual(preset["schema_version"], "story_card_short_preset.v1")
        self.assertEqual(preset["name"], "story_card_short_v1")
        self.assertEqual(preset["resolution"], [1080, 1920])
        self.assertEqual(preset["fps"], 30)
        self.assertGreaterEqual(preset["duration_sec"], 7)
        self.assertLessEqual(preset["duration_sec"], 9)
        self.assertEqual(preset["fragment"]["repeat_count"], 1)
        self.assertIn("не поворачивает", preset["text"]["top_highlights"]["negative"])
        self.assertEqual(preset["text"]["top_highlights"]["number"], "270°")
        self.assertEqual(preset["brand"]["name"], "Пульс природы")
        self.assertEqual(preset["brand"]["username"], "@nature_pulse_test")

    def test_layout_keeps_card_inside_safe_zones(self) -> None:
        from src.production_plan.story_card_short_render import build_story_card_layout, load_story_card_preset

        preset = load_story_card_preset()
        layout = build_story_card_layout(preset)
        safe = layout["safe_zone"]
        card = layout["card"]
        video = layout["central_video"]

        self.assertGreaterEqual(card["x"], safe["left"])
        self.assertGreaterEqual(card["y"], safe["top"])
        self.assertLessEqual(card["x"] + card["width"], preset["resolution"][0] - safe["right"])
        self.assertLessEqual(card["y"] + card["height"], preset["resolution"][1] - safe["bottom"])
        self.assertGreater(video["width"], 0)
        self.assertGreater(video["height"], 0)
        self.assertGreater(video["y"], layout["top_text"]["y"])

    def test_adaptive_layout_fills_card_and_protects_video(self) -> None:
        from src.production_plan.story_card_short_render import build_story_card_layout, load_story_card_preset

        preset = load_story_card_preset()
        layout = build_story_card_layout(preset)
        card = layout["card"]

        # Central video is significantly larger than the old fixed 836x560 v1 box.
        self.assertGreater(layout["video_width"] * layout["video_height"], 836 * 560)
        # The card useful area is well filled by content.
        self.assertGreaterEqual(layout["content_occupancy_ratio"], 0.88)
        # Landscape, head-safe aspect ratio: no aggressive vertical crop of the owl head.
        self.assertGreaterEqual(layout["video_width"] / layout["video_height"], 1.15)
        # The comment is close to the bottom edge (no large empty zone below it).
        self.assertLessEqual(layout["bottom_gap"], 60)
        # The gap between the top text and the video is small.
        top_text_bottom = layout["top_text"]["y"] + layout["top_text_height"]
        self.assertLessEqual(layout["video_y"] - top_text_bottom, 40)
        # Stacking order is correct and nothing overlaps.
        self.assertLess(layout["video_y"] + layout["video_height"], layout["brand_y"])
        self.assertLess(layout["brand_y"], layout["comment_y"])
        self.assertLessEqual(layout["comment_y"], card["y"] + card["height"])

    def test_smoke_render_creates_vertical_mp4_and_preview(self) -> None:
        from src.assets.frame_sampling import ffprobe_media_info
        from src.production_plan.story_card_short_render import render_story_card_short

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = _make_source_video(root)
            output = root / "story_card.mp4"
            preview = root / "preview.png"
            preset = {
                "schema_version": "story_card_short_preset.v1",
                "name": "story_card_short_test",
                "resolution": [270, 480],
                "fps": 12,
                "duration_sec": 1.2,
                "fragment": {"start_sec": 0.0, "duration_sec": 1.0, "repeat_count": 1, "first_zoom": 1.05, "second_zoom": 1.12},
                "safe_margins": {"left": 18, "right": 18, "top": 18, "bottom": 18},
                "card": {"x": 22, "y": 28, "width": 226, "height": 420, "radius": 10, "background_color": "#111a24", "shadow_alpha": 120},
                "background": {"blur_radius": 8, "darken_alpha": 150, "zoom_start": 1.05, "zoom_end": 1.08},
                "central_video": {"x": 36, "y": 178, "width": 198, "height": 124, "corner_radius": 6},
                "text": {
                    "font": "DejaVuSans.ttf",
                    "top_font_size": 16,
                    "comment_font_size": 13,
                    "brand_font_size": 14,
                    "username_font_size": 10,
                    "line_spacing": 4,
                    "top": "Сова не поворачивает голову на 360°.\nНо она может развернуть её примерно на 270°.",
                    "comment": "Миф звучит эффектнее. Но анатомия совы интереснее.",
                    "top_highlights": {"negative": "не поворачивает", "number": "270°", "mechanism": "", "context": ""},
                    "colors": {"primary": "#ffffff", "negative": "#ff5252", "number": "#ffe66d", "mechanism": "#72e084", "context": "#7ecbff", "muted": "#b7c2cf"},
                },
                "brand": {"name": "Пульс природы", "username": "@nature_pulse_test", "icon_size": 32},
                "encoding": {"codec": "libx264", "crf": 28, "preset": "ultrafast", "pix_fmt": "yuv420p"},
            }

            manifest = render_story_card_short(source_video=source, output_path=output, frame_preview_path=preview, preset=preset)
            info = ffprobe_media_info(output)

            self.assertEqual(manifest["status"], "completed")
            self.assertTrue(output.exists())
            self.assertTrue(preview.exists())
            self.assertEqual(info["width"], 270)
            self.assertEqual(info["height"], 480)
            self.assertAlmostEqual(info["duration_sec"], 1.2, delta=0.3)


def _make_source_video(root: Path) -> Path:
    frames_dir = root / "frames"
    frames_dir.mkdir()
    for index in range(18):
        image = Image.new("RGB", (320, 180), (38, 62, 48))
        draw = ImageDraw.Draw(image)
        x = 120 + min(index, 10) * 4
        draw.ellipse((x, 56, x + 66, 126), fill=(220, 220, 205))
        draw.ellipse((x + 18, 78, x + 30, 90), fill=(255, 190, 60))
        draw.polygon([(x + 38, 92), (x + 52, 86), (x + 48, 102)], fill=(35, 28, 22))
        image.save(frames_dir / f"frame_{index:03d}.png")
    output = root / "source.mp4"
    command = [
        imageio_ffmpeg.get_ffmpeg_exe(),
        "-y",
        "-v",
        "error",
        "-framerate",
        "12",
        "-i",
        str(frames_dir / "frame_%03d.png"),
        "-pix_fmt",
        "yuv420p",
        "-c:v",
        "libx264",
        str(output),
    ]
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise RuntimeError(result.stderr)
    return output


if __name__ == "__main__":
    unittest.main()
