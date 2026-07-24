from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw


class TemporalVideoAnalysisTests(unittest.TestCase):
    def test_motion_video_extracts_independent_temporal_frames(self) -> None:
        from src.assets.temporal_video_analysis import analyze_temporal_candidate

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            video = _make_video(root, moving=True)

            analysis = analyze_temporal_candidate(
                candidate_id="moving_owl_fixture",
                preview_path=video,
                output_dir=root / "frames",
                positions=[0.15, 0.5, 0.85],
            )

        self.assertEqual(analysis["frame_count"], 3)
        self.assertEqual([round(item["requested_position"], 2) for item in analysis["frames"]], [0.15, 0.5, 0.85])
        self.assertTrue(analysis["temporal_independence"])
        self.assertTrue(analysis["visible_motion_evidence"])
        self.assertEqual(len(set(item["sha256"] for item in analysis["frames"])), 3)
        self.assertTrue(analysis["contact_sheet_image"].endswith("contact_sheet.jpg"))

    def test_static_video_does_not_count_as_temporal_motion(self) -> None:
        from src.assets.temporal_video_analysis import analyze_temporal_candidate

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            video = _make_video(root, moving=False)

            analysis = analyze_temporal_candidate(
                candidate_id="static_owl_fixture",
                preview_path=video,
                output_dir=root / "frames",
                positions=[0.15, 0.5, 0.85],
            )

        self.assertEqual(analysis["frame_count"], 3)
        self.assertFalse(analysis["temporal_independence"])
        self.assertFalse(analysis["visible_motion_evidence"])
        self.assertLessEqual(analysis["mean_perceptual_hash_distance"], 2)


def _make_video(root: Path, *, moving: bool) -> Path:
    frames_dir = root / ("moving_frames" if moving else "static_frames")
    frames_dir.mkdir(parents=True)
    for index in range(12):
        image = Image.new("RGB", (320, 240), (28, 34, 42))
        draw = ImageDraw.Draw(image)
        x = 40 + (index * 16 if moving else 0)
        draw.ellipse((x, 78, x + 72, 150), fill=(194, 160, 88))
        draw.rectangle((x + 24, 102, x + 62, 132), fill=(30, 28, 22))
        image.save(frames_dir / f"frame_{index:03d}.png")
    output = root / ("moving.mp4" if moving else "static.mp4")
    command = [
        imageio_ffmpeg.get_ffmpeg_exe(),
        "-y",
        "-v",
        "error",
        "-framerate",
        "4",
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
