"""Test classification: LEGACY ANCHOR

Protects:
- снимок разделения 6F: root ``pipeline.py`` остаётся compatibility facade,
  чьи ``parse_args``, ``run_maintenance_command`` и workflow-функции — те же
  объекты, что и в ``src.legacy_pipeline``, и чей ``--skip-render`` прогон
  продолжает проходить через прежние module-level patch-points без render,
  TTS и сети.

Does not prove:
- что root ``pipeline.py`` является поддерживаемым пользовательским входом:
  канонический CLI — ``python -m ai_youtube`` (ADR 0007), а root facade
  назначен к удалению последним в PLAN-L4;
- что legacy workflow даёт корректный продуктовый результат: проверяется
  тождество функций и порядок делегации, а не качество ролика;
- что модуль должен пережить носителя. Класс — LEGACY ANCHOR
  (``docs/current/CLEANUP_REGISTRY.md``, «Accidental invariants»):
  characterization своё назначение выполнила — рефакторинг 6F завершён, —
  поэтому модуль ретайрится вместе с носителем по gate PLAN-L3 / PLAN-L4.
"""

from __future__ import annotations

import contextlib
import io
import inspect
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


class LegacyPipelineInternalsContractTests(unittest.TestCase):
    def test_root_module_is_a_compatibility_facade(self) -> None:
        import pipeline
        from src.legacy_pipeline.cli import parse_args
        from src.legacy_pipeline.maintenance import run_maintenance_command
        from src.legacy_pipeline.workflow import run_legacy_video_pipeline

        self.assertIs(pipeline.parse_args, parse_args)
        self.assertIs(pipeline.run_maintenance_command, run_maintenance_command)
        self.assertIs(pipeline.run_legacy_video_pipeline, run_legacy_video_pipeline)
        self.assertEqual(list(inspect.signature(pipeline.main).parameters), [])
        self.assertEqual(
            list(inspect.signature(pipeline.limit_scene_plan).parameters),
            ["scene_plan", "max_scenes"],
        )

    def test_skip_render_keeps_legacy_orchestration_and_root_patch_points(self) -> None:
        import pipeline

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            application_paths = SimpleNamespace(
                config_root=root / "config",
                outputs_root=root / "outputs",
                projects_root=root / "projects",
                repository_root=root,
                workspace=SimpleNamespace(media_library=root / "media_library"),
            )
            config = {
                "dev_mode": False,
                "plans": {
                    "quote_plan": "quote_plan.json",
                    "scene_plan": "scene_plan.json",
                    "asset_plan": "asset_plan.json",
                    "render_plan": "render_plan.json",
                },
                "obsidian": {"enabled": False},
            }
            quote_plan = {"quotes": []}
            metadata = {"chosen_title": "Characterized"}
            scene_plan = {"scenes": [], "target_duration": 0}
            voice_manifest = {"segments": []}
            intro_plan = {"enabled": False}
            music_plan = {"status": "disabled"}
            asset_plan = {"scenes": []}
            render_plan = {"output_path": str(root / "output.mp4")}

            with (
                mock.patch.object(
                    sys,
                    "argv",
                    ["pipeline.py", "--skip-render", "--no-obsidian"],
                ),
                mock.patch(
                    "src.config_resolver.resolve_application_paths",
                    return_value=application_paths,
                ),
                mock.patch.object(pipeline, "configure_console_encoding"),
                mock.patch.object(pipeline, "ensure_dir"),
                mock.patch.object(pipeline, "ensure_media_library"),
                mock.patch.object(pipeline, "load_config", return_value=config) as load_config,
                mock.patch.object(
                    pipeline,
                    "build_quote_plan",
                    return_value=quote_plan,
                ) as build_quote_plan,
                mock.patch.object(
                    pipeline,
                    "write_youtube_metadata",
                    return_value=metadata,
                ) as write_youtube_metadata,
                mock.patch.object(
                    pipeline,
                    "build_scene_plan",
                    return_value=scene_plan,
                ) as build_scene_plan,
                mock.patch.object(
                    pipeline,
                    "build_voice_manifest",
                    return_value=voice_manifest,
                ) as build_voice_manifest,
                mock.patch.object(
                    pipeline,
                    "apply_voice_timing_to_scene_plan",
                    return_value=scene_plan,
                ) as apply_voice_timing,
                mock.patch.object(
                    pipeline,
                    "align_voice_manifest_to_scene_plan",
                    return_value=voice_manifest,
                ) as align_voice_manifest,
                mock.patch.object(
                    pipeline,
                    "build_intro_plan",
                    return_value=intro_plan,
                ) as build_intro_plan,
                mock.patch.object(
                    pipeline,
                    "build_music_plan",
                    return_value=music_plan,
                ) as build_music_plan,
                mock.patch.object(
                    pipeline,
                    "build_asset_plan",
                    return_value=asset_plan,
                ) as build_asset_plan,
                mock.patch.object(
                    pipeline,
                    "build_render_plan",
                    return_value=render_plan,
                ) as build_render_plan,
                mock.patch.object(pipeline, "write_json") as write_json,
                mock.patch.object(pipeline, "render_video") as render_video,
                mock.patch.object(pipeline, "evaluate_render") as evaluate_render,
                contextlib.redirect_stdout(io.StringIO()) as output,
            ):
                pipeline.main()

        load_config.assert_called_once()
        build_quote_plan.assert_called_once_with(config)
        write_youtube_metadata.assert_called_once_with(
            config,
            quote_plan,
            output_path="outputs/youtube_metadata.json",
        )
        build_scene_plan.assert_called_once_with(config, quote_plan, metadata)
        build_voice_manifest.assert_called_once_with(
            config,
            scene_plan,
            reuse_voice=True,
            skip_voice=False,
        )
        apply_voice_timing.assert_called_once_with(
            scene_plan,
            voice_manifest,
            cinematic_preview=False,
        )
        align_voice_manifest.assert_called_once_with(voice_manifest, scene_plan)
        build_intro_plan.assert_called_once_with(config, metadata)
        build_music_plan.assert_called_once_with(config, scene_plan)
        build_asset_plan.assert_called_once_with(config, scene_plan, refresh=False)
        build_render_plan.assert_called_once_with(
            config,
            scene_plan,
            asset_plan,
            music_plan,
        )
        self.assertEqual(write_json.call_count, 7)
        render_video.assert_not_called()
        evaluate_render.assert_not_called()
        self.assertIn("[render] Skipped via --skip-render", output.getvalue())
        self.assertIn("chosen title: Characterized", output.getvalue())


if __name__ == "__main__":
    unittest.main()
