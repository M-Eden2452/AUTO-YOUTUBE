import tempfile
import unittest
from pathlib import Path

from anime_factory.modules.paths import EpisodePaths, clean_force_outputs, clean_output_only


def _paths(root: Path) -> EpisodePaths:
    artifacts = root / "artifacts"
    return EpisodePaths(
        root=root,
        source_video=root / "source.mp4",
        artifacts_dir=artifacts,
        output_dir=root / "output",
        previews_dir=root / "previews",
        audio_wav=artifacts / "audio.wav",
        transcript_json=artifacts / "transcript.json",
        subtitles_raw_srt=artifacts / "subtitles_raw.srt",
        audio_features_json=artifacts / "audio_features.json",
        candidates_json=artifacts / "candidates.json",
        scene_cuts_json=artifacts / "scene_cuts.json",
        crops_dir=artifacts / "crops",
        selected_example_json=root / "selected.example.json",
        report_html=root / "report.html",
    )


class AnimeFactoryCleanupTests(unittest.TestCase):
    def test_force_cleanup_removes_only_render_outputs_crops_and_report(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = _paths(Path(temp_dir) / "episode")
            paths.output_dir.mkdir(parents=True)
            paths.previews_dir.mkdir(parents=True)
            paths.crops_dir.mkdir(parents=True)
            paths.artifacts_dir.mkdir(parents=True, exist_ok=True)
            paths.source_video.write_text("source", encoding="utf-8")
            paths.audio_wav.write_text("audio", encoding="utf-8")
            paths.transcript_json.write_text("[]", encoding="utf-8")
            paths.candidates_json.write_text("[]", encoding="utf-8")
            paths.report_html.write_text("report", encoding="utf-8")
            (paths.output_dir / "short_001.mp4").write_text("video", encoding="utf-8")
            (paths.previews_dir / "preview.jpg").write_text("preview", encoding="utf-8")
            (paths.crops_dir / "short_001_crop_path.json").write_text("[]", encoding="utf-8")

            clean_force_outputs(paths)

            self.assertTrue(paths.source_video.exists())
            self.assertTrue(paths.audio_wav.exists())
            self.assertTrue(paths.transcript_json.exists())
            self.assertTrue(paths.candidates_json.exists())
            self.assertFalse(paths.report_html.exists())
            self.assertEqual(list(paths.output_dir.iterdir()), [])
            self.assertEqual(list(paths.previews_dir.iterdir()), [])
            self.assertEqual(list(paths.crops_dir.iterdir()), [])

    def test_clean_output_only_keeps_artifacts_and_report(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = _paths(Path(temp_dir) / "episode")
            paths.output_dir.mkdir(parents=True)
            paths.artifacts_dir.mkdir(parents=True)
            paths.report_html.write_text("report", encoding="utf-8")
            paths.transcript_json.write_text("[]", encoding="utf-8")
            (paths.output_dir / "short_001.mp4").write_text("video", encoding="utf-8")

            clean_output_only(paths)

            self.assertEqual(list(paths.output_dir.iterdir()), [])
            self.assertTrue(paths.transcript_json.exists())
            self.assertTrue(paths.report_html.exists())


if __name__ == "__main__":
    unittest.main()
