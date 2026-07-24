from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageFilter


class VisualPreviewFoundationTests(unittest.TestCase):
    def test_preview_request_serialization(self) -> None:
        from src.assets.visual_preview import VisualPreviewRequest

        request = VisualPreviewRequest(
            project_id="project_001",
            scene_id="scene_001",
            top_k=5,
            target_aspect_ratio="9:16",
            refresh=True,
            offline=True,
            technical_rerank=True,
        )

        loaded = VisualPreviewRequest.from_dict(request.to_dict())

        self.assertEqual(loaded.project_id, "project_001")
        self.assertEqual(loaded.scene_id, "scene_001")
        self.assertEqual(loaded.top_k, 5)
        self.assertTrue(loaded.refresh)
        self.assertTrue(loaded.offline)
        self.assertTrue(loaded.technical_rerank)

    def test_preview_cache_key_stability(self) -> None:
        from src.assets.models import AssetCandidate
        from src.assets.visual_preview import VisualPreviewRequest, compute_preview_cache_key

        candidate = AssetCandidate(asset_id="a1", provider="pexels", provider_asset_id="42", media_type="image", preview_url="https://cdn/preview.jpg")
        request = VisualPreviewRequest(project_id="p", scene_id="s", target_aspect_ratio="9:16", top_k=5)

        first = compute_preview_cache_key(candidate, request, preview_source_url=candidate.preview_url, rendition="medium")
        second = compute_preview_cache_key(AssetCandidate.from_dict(candidate.to_dict()), request, preview_source_url=candidate.preview_url, rendition="medium")
        changed = compute_preview_cache_key(candidate, request, preview_source_url=candidate.preview_url + "?v=2", rendition="medium")

        self.assertEqual(first, second)
        self.assertNotEqual(first, changed)
        self.assertEqual(len(first), 64)

    def test_preview_cache_hit(self) -> None:
        from src.assets.visual_preview import PreviewCache

        with tempfile.TemporaryDirectory() as tmp:
            cache = PreviewCache(Path(tmp), max_preview_size_bytes=1024 * 1024)
            key = "a" * 64
            image_bytes = _image_bytes((48, 64), (10, 20, 30))

            stored = cache.store_bytes(key, image_bytes, media_type="image", extension=".jpg", source_url="https://example.test/a.jpg")
            hit = cache.read(key, media_type="image")

            self.assertEqual(hit.cache_status, "hit")
            self.assertEqual(hit.local_path, stored.local_path)
            self.assertEqual(hit.sha256, stored.sha256)

    def test_corrupted_preview_cache_invalidation(self) -> None:
        from src.assets.visual_preview import PreviewCache

        with tempfile.TemporaryDirectory() as tmp:
            cache = PreviewCache(Path(tmp), max_preview_size_bytes=1024 * 1024)
            key = "b" * 64
            record = cache.store_bytes(key, _image_bytes((48, 64), (10, 20, 30)), media_type="image", extension=".jpg", source_url="")
            Path(record.local_path).write_bytes(b"corrupt")

            self.assertIsNone(cache.read(key, media_type="image"))

    def test_image_preview_generation(self) -> None:
        from src.assets.visual_preview import create_local_preview

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "large.jpg"
            Image.new("RGB", (1200, 800), (30, 80, 120)).save(source)

            record = create_local_preview(source, root / "cache", media_type="image", cache_key="c" * 64, max_dimension=320)

            with Image.open(record.local_path) as image:
                self.assertLessEqual(max(image.size), 320)
            self.assertEqual(record.preview_media_type, "image")
            self.assertEqual(record.cache_status, "stored")

    def test_video_preview_generation(self) -> None:
        from src.assets.visual_preview import create_local_preview

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.mp4"
            if not _write_tiny_video(source, duration=1.2, color="0x224466"):
                self.skipTest("FFmpeg unavailable")

            record = create_local_preview(source, root / "cache", media_type="video", cache_key="d" * 64, max_duration_sec=0.6, max_dimension=360)

            self.assertTrue(Path(record.local_path).is_file())
            self.assertEqual(record.preview_media_type, "video")
            self.assertGreater(record.duration_sec, 0)
            self.assertLessEqual(record.duration_sec, 0.8)

    def test_frame_timestamps_for_normal_video(self) -> None:
        from src.assets.frame_sampling import planned_sample_timestamps

        timestamps = planned_sample_timestamps(duration_sec=10.0, sample_count=5, positions=[0.1, 0.3, 0.5, 0.7, 0.9])

        self.assertEqual(timestamps, [1.0, 3.0, 5.0, 7.0, 9.0])

    def test_frame_timestamps_for_very_short_video(self) -> None:
        from src.assets.frame_sampling import planned_sample_timestamps

        timestamps = planned_sample_timestamps(duration_sec=0.4, sample_count=5, positions=[0.1, 0.3, 0.5, 0.7, 0.9])

        self.assertGreaterEqual(len(timestamps), 1)
        self.assertTrue(all(0 <= item <= 0.4 for item in timestamps))

    def test_no_duplicate_timestamps(self) -> None:
        from src.assets.frame_sampling import planned_sample_timestamps

        timestamps = planned_sample_timestamps(duration_sec=0.1, sample_count=5, positions=[0.1, 0.3, 0.5, 0.7, 0.9])

        self.assertEqual(len(timestamps), len(set(timestamps)))

    def test_frame_extraction_through_ffmpeg(self) -> None:
        from src.assets.frame_sampling import sample_frames

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.mp4"
            if not _write_tiny_video(source, duration=1.0, color="0x224466"):
                self.skipTest("FFmpeg unavailable")

            frames = sample_frames(source, media_type="video", output_dir=root / "frames", sample_count=3, positions=[0.2, 0.5, 0.8])

            self.assertGreaterEqual(len(frames), 1)
            self.assertTrue(all(frame.extraction_status == "extracted" for frame in frames))
            self.assertTrue(all(Path(frame.local_frame_path).is_file() for frame in frames))

    def test_image_treated_as_one_frame(self) -> None:
        from src.assets.frame_sampling import sample_frames

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "image.jpg"
            Image.new("RGB", (320, 480), (40, 70, 110)).save(source)

            frames = sample_frames(source, media_type="image", output_dir=root / "frames", sample_count=5)

            self.assertEqual(len(frames), 1)
            self.assertEqual(frames[0].requested_timestamp_sec, 0.0)
            self.assertEqual(frames[0].width, 320)

    def test_dark_frame_metric(self) -> None:
        from src.assets.visual_metrics import analyze_frame_metrics

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "dark.jpg"
            Image.new("RGB", (100, 100), (0, 0, 0)).save(path)

            metrics = analyze_frame_metrics(path)

            self.assertGreater(metrics.dark_frame_score, 0.95)
            self.assertLess(metrics.brightness_mean, 5)

    def test_white_frame_metric(self) -> None:
        from src.assets.visual_metrics import analyze_frame_metrics

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "white.jpg"
            Image.new("RGB", (100, 100), (255, 255, 255)).save(path)

            metrics = analyze_frame_metrics(path)

            self.assertGreater(metrics.near_white_frame_score, 0.95)
            self.assertGreater(metrics.brightness_mean, 250)

    def test_contrast_metric(self) -> None:
        from src.assets.visual_metrics import analyze_frame_metrics

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "contrast.jpg"
            _striped_image(path, size=(120, 120), stripe=4)

            metrics = analyze_frame_metrics(path)

            self.assertGreater(metrics.contrast, 80)

    def test_sharpness_heuristic(self) -> None:
        from src.assets.visual_metrics import analyze_frame_metrics

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sharp = root / "sharp.jpg"
            blurry = root / "blurry.jpg"
            _striped_image(sharp, size=(160, 160), stripe=2)
            Image.open(sharp).filter(ImageFilter.GaussianBlur(5)).save(blurry)

            sharp_metrics = analyze_frame_metrics(sharp)
            blurry_metrics = analyze_frame_metrics(blurry)

            self.assertGreater(sharp_metrics.sharpness_heuristic, blurry_metrics.sharpness_heuristic)

    def test_frozen_frame_detection(self) -> None:
        from src.assets.frame_sampling import SampledFrame
        from src.assets.visual_metrics import analyze_video_frame_set

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = []
            for index in range(3):
                path = root / f"same_{index}.jpg"
                Image.new("RGB", (80, 80), (20, 50, 80)).save(path)
                paths.append(path)
            frames = [SampledFrame(frame_index=i, local_frame_path=str(path), extraction_status="extracted") for i, path in enumerate(paths)]

            metrics = analyze_video_frame_set(frames)

            self.assertGreater(metrics.frozen_frame_ratio, 0.9)

    def test_repeated_frame_detection(self) -> None:
        from src.assets.frame_sampling import SampledFrame
        from src.assets.visual_metrics import analyze_video_frame_set

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            colors = [(20, 50, 80), (20, 50, 80), (200, 40, 30)]
            frames = []
            for index, color in enumerate(colors):
                path = root / f"frame_{index}.jpg"
                Image.new("RGB", (80, 80), color).save(path)
                frames.append(SampledFrame(frame_index=index, local_frame_path=str(path), extraction_status="extracted"))

            metrics = analyze_video_frame_set(frames)

            self.assertGreater(metrics.repeated_frame_ratio, 0.25)
            self.assertLess(metrics.unique_frame_ratio, 1.0)

    def test_perceptual_image_hash_stability(self) -> None:
        from src.assets.perceptual_similarity import image_perceptual_hash

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "hash.jpg"
            _striped_image(path, size=(128, 128), stripe=4)

            self.assertEqual(image_perceptual_hash(path), image_perceptual_hash(path))
            self.assertEqual(len(image_perceptual_hash(path)), 16)

    def test_exact_duplicate_detection(self) -> None:
        from src.assets.perceptual_similarity import compare_signatures, signature_from_image

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "first.jpg"
            second = root / "second.jpg"
            Image.new("RGB", (128, 128), (80, 90, 100)).save(first)
            second.write_bytes(first.read_bytes())

            result = compare_signatures(signature_from_image("a", first), signature_from_image("b", second))

            self.assertEqual(result.classification, "exact_duplicate")
            self.assertEqual(result.aggregate_similarity, 1.0)

    def test_near_duplicate_detection(self) -> None:
        from src.assets.perceptual_similarity import compare_signatures, signature_from_image

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "first.jpg"
            second = root / "second.jpg"
            _striped_image(first, size=(128, 128), stripe=8)
            _striped_image(second, size=(128, 128), stripe=8, offset=1)

            result = compare_signatures(signature_from_image("a", first), signature_from_image("b", second), near_threshold=10)

            self.assertIn(result.classification, {"near_duplicate", "likely_same_source_different_rendition", "visually_similar"})
            self.assertGreater(result.aggregate_similarity, 0.7)

    def test_video_signature_uses_multiple_frames(self) -> None:
        from src.assets.frame_sampling import SampledFrame
        from src.assets.perceptual_similarity import signature_from_frames

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            frames = []
            for index, color in enumerate([(20, 30, 40), (80, 90, 100), (150, 160, 170)]):
                path = root / f"frame_{index}.jpg"
                Image.new("RGB", (96, 96), color).save(path)
                frames.append(SampledFrame(frame_index=index, local_frame_path=str(path), extraction_status="extracted"))

            signature = signature_from_frames("video_asset", frames)

            self.assertEqual(signature.media_type, "video")
            self.assertEqual(len(signature.frame_hashes), 3)

    def test_9_16_crop_suitability(self) -> None:
        from src.assets.visual_metrics import estimate_crop_suitability

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "portrait.jpg"
            _center_detail_image(path, size=(1080, 1920))

            result = estimate_crop_suitability(path, "9:16")

            self.assertGreater(result["heuristic_crop_suitability"], 85)
            self.assertIn("estimated_detail_retention", result)

    def test_16_9_crop_suitability(self) -> None:
        from src.assets.visual_metrics import estimate_crop_suitability

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "landscape.jpg"
            _center_detail_image(path, size=(1920, 1080))

            result = estimate_crop_suitability(path, "16:9")

            self.assertGreater(result["heuristic_crop_suitability"], 85)

    def test_square_crop_suitability(self) -> None:
        from src.assets.visual_metrics import estimate_crop_suitability

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "square.jpg"
            _center_detail_image(path, size=(1000, 1000))

            result = estimate_crop_suitability(path, "1:1")

            self.assertGreater(result["heuristic_crop_suitability"], 85)

    def test_windows_unicode_paths(self) -> None:
        from src.assets.visual_preview import create_local_preview

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "unicode сцена"
            root.mkdir()
            source = root / "кадр.jpg"
            Image.new("RGB", (320, 480), (25, 55, 95)).save(source)

            record = create_local_preview(source, root / "cache", media_type="image", cache_key="e" * 64)

            self.assertTrue(Path(record.local_path).is_file())
            self.assertIn("unicode", str(Path(record.local_path).parent))

    def test_technical_score_breakdown(self) -> None:
        from src.assets.frame_sampling import sample_frames
        from src.assets.visual_metrics import analyze_visual_technical_quality

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "image.jpg"
            _center_detail_image(source, size=(1080, 1920))
            frames = sample_frames(source, media_type="image", output_dir=root / "frames")

            analysis = analyze_visual_technical_quality(source, media_type="image", sampled_frames=frames, target_aspect_ratios=["9:16", "16:9", "1:1"])

            self.assertEqual(analysis.analysis_status, "passed")
            self.assertGreater(analysis.technical_quality_score, 0)
            self.assertIn("brightness", analysis.score_breakdown)
            self.assertIn("9:16", analysis.crop_suitability)


def _image_bytes(size: tuple[int, int], color: tuple[int, int, int]) -> bytes:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "image.jpg"
        Image.new("RGB", size, color).save(path)
        return path.read_bytes()


def _write_tiny_video(path: Path, *, duration: float = 1.0, color: str = "0x224466") -> bool:
    command = [
        imageio_ffmpeg.get_ffmpeg_exe(),
        "-y",
        "-v",
        "error",
        "-f",
        "lavfi",
        "-i",
        f"color=c={color}:s=320x480:d={duration}:r=12",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        str(path),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    return result.returncode == 0 and path.exists()


def _striped_image(path: Path, *, size: tuple[int, int], stripe: int, offset: int = 0) -> None:
    image = Image.new("RGB", size, (0, 0, 0))
    pixels = image.load()
    for y in range(size[1]):
        for x in range(size[0]):
            value = 255 if ((x + offset) // stripe) % 2 == 0 else 0
            pixels[x, y] = (value, value, value)
    image.save(path)


def _center_detail_image(path: Path, *, size: tuple[int, int]) -> None:
    image = Image.new("RGB", size, (30, 35, 40))
    pixels = image.load()
    left = size[0] // 4
    right = size[0] * 3 // 4
    top = size[1] // 4
    bottom = size[1] * 3 // 4
    for y in range(top, bottom):
        for x in range(left, right):
            value = 220 if ((x + y) // 12) % 2 == 0 else 80
            pixels[x, y] = (value, value, 60)
    image.save(path)


if __name__ == "__main__":
    unittest.main()
