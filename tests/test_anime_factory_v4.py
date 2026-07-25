import unittest

from anime_factory.modules.dynamic_crop import build_smart_static_crop_path
from anime_factory.modules.preview import build_comparison_labels


class AnimeFactoryV4Tests(unittest.TestCase):
    def test_smart_static_crop_centers_weighted_faces(self):
        detections = [
            {"time": 0.0, "faces": [{"x": 1200, "y": 120, "w": 180, "h": 180, "confidence": 0.9}]},
            {"time": 0.5, "faces": [{"x": 1220, "y": 130, "w": 200, "h": 200, "confidence": 0.9}]},
        ]

        result = build_smart_static_crop_path(detections, video_width=1920, video_height=1080, clip_duration=2.0)

        center_crop_x = int((1920 - int(1080 * 9 / 16)) / 2)
        self.assertGreater(result["crop_path"][0]["crop_x"], center_crop_x)
        self.assertEqual(result["quality"]["mode"], "smart_static")
        self.assertEqual(result["crop_path"][0]["mode"], "smart_static")

    def test_comparison_labels_include_requested_modes(self):
        labels = build_comparison_labels(["center", "smart_static", "dynamic", "blur"])

        self.assertEqual(labels, "center | smart_static | dynamic | blur")


if __name__ == "__main__":
    unittest.main()
