from __future__ import annotations

import inspect
import unittest
from unittest import mock


class AnimeClipperApplicationBoundaryCharacterizationTests(unittest.TestCase):
    def test_legacy_workflow_surface_and_signatures_are_stable(self) -> None:
        from anime_factory import pipeline

        self.assertEqual(list(inspect.signature(pipeline.parse_args).parameters), [])
        self.assertEqual(
            list(inspect.signature(pipeline.run_pipeline).parameters),
            ["args"],
        )
        self.assertEqual(list(inspect.signature(pipeline.main).parameters), [])

    def test_episode_project_and_output_contract_is_stable(self) -> None:
        from anime_factory.modules.paths import (
            PROJECT_ROOT,
            EpisodePaths,
            get_episode_paths,
        )

        self.assertEqual(
            list(EpisodePaths.__dataclass_fields__),
            [
                "root",
                "source_video",
                "artifacts_dir",
                "output_dir",
                "previews_dir",
                "audio_wav",
                "transcript_json",
                "subtitles_raw_srt",
                "audio_features_json",
                "candidates_json",
                "scene_cuts_json",
                "crops_dir",
                "selected_example_json",
                "report_html",
            ],
        )

        paths = get_episode_paths("season/episode_001")

        self.assertEqual(
            paths.root,
            PROJECT_ROOT / "episodes" / "season_episode_001",
        )
        self.assertEqual(paths.source_video, paths.root / "source.mp4")
        self.assertEqual(paths.output_dir, paths.root / "output")
        self.assertEqual(paths.previews_dir, paths.root / "previews")
        self.assertEqual(paths.artifacts_dir, paths.root / "artifacts")
        self.assertEqual(
            paths.candidates_json,
            paths.artifacts_dir / "candidates.json",
        )
        self.assertEqual(paths.report_html, paths.root / "report.html")

    def test_compatibility_app_delegates_to_legacy_main(self) -> None:
        from apps.anime_factory import main as compatibility_app

        with mock.patch(
            "anime_factory.pipeline.main",
            return_value=17,
        ) as legacy_main:
            result = compatibility_app.main()

        legacy_main.assert_called_once_with()
        self.assertEqual(result, 0)

    def test_catalog_keeps_video_repurposer_planned_and_disabled(self) -> None:
        from src.production_catalog.catalog import get_default_catalog

        application = get_default_catalog().applications.get(
            "video_repurposer"
        )

        self.assertFalse(application.enabled)
        self.assertEqual(application.implementation_status, "planned")

    def test_canonical_boundary_reuses_existing_workflow_and_paths(self) -> None:
        from anime_factory import pipeline
        from anime_factory.modules.paths import (
            PROJECT_ROOT,
            EpisodePaths,
            get_episode_paths,
        )
        from src.ai_youtube.apps.video_repurposer.workflows import (
            anime_clipper,
        )

        self.assertIs(anime_clipper.PROJECT_ROOT, PROJECT_ROOT)
        self.assertIs(anime_clipper.EpisodePaths, EpisodePaths)
        self.assertIs(anime_clipper.get_episode_paths, get_episode_paths)
        self.assertIs(anime_clipper.parse_args, pipeline.parse_args)
        self.assertIs(anime_clipper.run_pipeline, pipeline.run_pipeline)
        self.assertIs(anime_clipper.main, pipeline.main)


if __name__ == "__main__":
    unittest.main()
