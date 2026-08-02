"""Test classification: LEGACY ANCHOR

Protects:
- снимок slice 8D: стабильность root command/workflow surface, форму
  ``LegacyPipelineArtifacts``, переиспользование существующих engine
  patch-points вместо новых, делегацию ``apps.youtube_pipeline`` в root facade
  и то, что canonical adapter ``src.ai_youtube.apps.legacy_pipeline`` лениво
  переэкспортирует существующие функции, а не дублирует их.

Does not prove:
- что legacy pipeline остаётся поддерживаемым приложением: adapter создавался
  ради переноса границы, а не ради продления жизни стека;
- что ``apps.youtube_pipeline`` обещан пользователю — он назначен к удалению в
  PLAN-L4;
- что модуль должен пережить носителя. Класс — LEGACY ANCHOR
  (``docs/current/CLEANUP_REGISTRY.md``, «Accidental invariants»):
  characterization этапа 8D своё назначение выполнила, поэтому модуль
  ретайрится вместе с носителем по gate PLAN-L3 / PLAN-L4.
"""

from __future__ import annotations

import inspect
import unittest
from dataclasses import fields
from unittest import mock


class LegacyPipelineApplicationBoundaryCharacterizationTests(unittest.TestCase):
    def test_root_command_and_workflow_surface_is_stable(self) -> None:
        import pipeline
        from src.legacy_pipeline.cli import parse_args
        from src.legacy_pipeline.maintenance import run_maintenance_command
        from src.legacy_pipeline.workflow import run_legacy_video_pipeline

        self.assertIs(pipeline.parse_args, parse_args)
        self.assertIs(pipeline.run_maintenance_command, run_maintenance_command)
        self.assertIs(
            pipeline.run_legacy_video_pipeline,
            run_legacy_video_pipeline,
        )
        self.assertEqual(list(inspect.signature(pipeline.main).parameters), [])
        self.assertEqual(
            list(inspect.signature(pipeline.limit_scene_plan).parameters),
            ["scene_plan", "max_scenes"],
        )

    def test_legacy_artifact_contract_is_stable(self) -> None:
        from src.legacy_pipeline.workflow import LegacyPipelineArtifacts

        self.assertEqual(
            [field.name for field in fields(LegacyPipelineArtifacts)],
            [
                "plans",
                "quote_plan",
                "metadata",
                "scene_plan",
                "music_plan",
                "asset_plan",
                "render_plan",
            ],
        )

    def test_root_engine_patch_points_reuse_existing_owners(self) -> None:
        import pipeline
        from src.asset_finder import build_asset_plan
        from src.thumbnail_generator import create_thumbnail
        from src.video_renderer import (
            build_render_plan,
            render_video,
        )

        self.assertIs(pipeline.build_asset_plan, build_asset_plan)
        self.assertIs(pipeline.create_thumbnail, create_thumbnail)
        self.assertIs(pipeline.build_render_plan, build_render_plan)
        self.assertIs(pipeline.render_video, render_video)

    def test_compatibility_app_delegates_to_root_facade(self) -> None:
        from apps.youtube_pipeline import main as compatibility_app

        with mock.patch("pipeline.main", return_value=17) as root_main:
            result = compatibility_app.main()

        root_main.assert_called_once_with()
        self.assertEqual(result, 0)

    def test_canonical_adapter_reuses_existing_facade_and_workflow(self) -> None:
        import pipeline
        from src.ai_youtube.apps.legacy_pipeline import adapter
        from src.legacy_pipeline.workflow import LegacyPipelineArtifacts

        self.assertIs(adapter.main, pipeline.main)
        self.assertIs(adapter.parse_args, pipeline.parse_args)
        self.assertIs(
            adapter.run_maintenance_command,
            pipeline.run_maintenance_command,
        )
        self.assertIs(
            adapter.run_legacy_video_pipeline,
            pipeline.run_legacy_video_pipeline,
        )
        self.assertIs(adapter.limit_scene_plan, pipeline.limit_scene_plan)
        self.assertIs(
            adapter.LegacyPipelineArtifacts,
            LegacyPipelineArtifacts,
        )


if __name__ == "__main__":
    unittest.main()
