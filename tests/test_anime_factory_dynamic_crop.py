import unittest

from anime_factory.modules.dynamic_crop import build_crop_path


class AnimeFactoryDynamicCropTests(unittest.TestCase):
    def test_build_crop_path_smooths_and_clamps_crop_x(self):
        detections = [
            {"time": 0.0, "faces": [{"x": 1700, "y": 100, "w": 160, "h": 160, "confidence": 0.9}]},
            {"time": 0.5, "faces": [{"x": 0, "y": 100, "w": 160, "h": 160, "confidence": 0.9}]},
        ]

        result = build_crop_path(
            detections=detections,
            video_width=1920,
            video_height=1080,
            clip_duration=1.0,
            config={"smoothing": 0.85, "max_shift_px": 60, "min_face_detections_ratio": 0.25},
        )

        crop_path = result["crop_path"]
        crop_w = int(1080 * 9 / 16)
        self.assertEqual(crop_path[0]["crop_w"], crop_w)
        self.assertTrue(all(0 <= item["crop_x"] <= 1920 - crop_w for item in crop_path))
        self.assertLessEqual(abs(crop_path[1]["crop_x"] - crop_path[0]["crop_x"]), 60)
        self.assertEqual(result["quality"]["mode"], "dynamic")

    def test_build_crop_path_falls_back_to_center_without_faces(self):
        detections = [
            {"time": 0.0, "faces": []},
            {"time": 0.5, "faces": []},
            {"time": 1.0, "faces": []},
            {"time": 1.5, "faces": []},
        ]

        result = build_crop_path(
            detections=detections,
            video_width=1920,
            video_height=1080,
            clip_duration=2.0,
            config={"smoothing": 0.85, "max_shift_px": 60, "min_face_detections_ratio": 0.25},
        )

        expected_center = int(round((1920 - int(1080 * 9 / 16)) / 2))
        self.assertEqual(result["quality"]["mode"], "center")
        self.assertIn("лица почти не найдены", result["quality"]["warnings"][0])
        self.assertTrue(all(item["crop_x"] == expected_center for item in result["crop_path"]))
        self.assertTrue(all(item["mode"] == "center" for item in result["crop_path"]))


if __name__ == "__main__":
    unittest.main()
