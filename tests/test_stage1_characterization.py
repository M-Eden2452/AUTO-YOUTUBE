from __future__ import annotations

import argparse
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


class LegacyPipelineCliContractTests(unittest.TestCase):
    def test_public_maintenance_command_and_safe_defaults(self) -> None:
        import pipeline

        with mock.patch.object(
            sys,
            "argv",
            ["pipeline.py", "applications", "list", "--json"],
        ):
            args = pipeline.parse_args()

        self.assertEqual(args.command, "applications")
        self.assertEqual(args.subcommand, "list")
        self.assertTrue(args.json_output)
        self.assertFalse(args.live)
        self.assertFalse(args.allow_paid_vision)
        self.assertEqual(args.budget_usd, 0.0)
        self.assertEqual(args.max_calls, 0)
        self.assertEqual(args.confirm_paid_vision, "")

    def test_catalog_command_keeps_dispatching_through_legacy_entrypoint(self) -> None:
        import pipeline

        with (
            mock.patch.object(sys, "argv", ["pipeline.py", "formats", "list", "--json"]),
            mock.patch.object(pipeline, "ensure_dir"),
            mock.patch.object(pipeline, "ensure_media_library"),
            mock.patch.object(pipeline, "run_production_catalog_cli", return_value=0) as dispatch,
            self.assertRaises(SystemExit) as caught,
        ):
            pipeline.main()

        self.assertEqual(caught.exception.code, 0)
        dispatched = dispatch.call_args.args[0]
        self.assertEqual(dispatched.command, "formats")
        self.assertEqual(dispatched.subcommand, "list")
        self.assertTrue(dispatched.json_output)


class ContentCreationCliContractTests(unittest.TestCase):
    def _commands(self) -> set[str]:
        from src.content_creation.cli import build_parser

        parser = build_parser()
        action = next(
            item for item in parser._actions if isinstance(item, argparse._SubParsersAction)
        )
        return set(action.choices)

    def test_current_public_commands_remain_available(self) -> None:
        self.assertGreaterEqual(
            self._commands(),
            {
                "capabilities",
                "formats",
                "templates",
                "channels",
                "voices",
                "subtitles",
                "project",
                "assets",
                "create",
                "resume",
                "run-stage",
                "wizard",
            },
        )

    def test_resume_command_sets_resume_without_paid_approval(self) -> None:
        from src.content_creation.cli import main
        from src.content_creation.models import ContentCreationResult

        with tempfile.TemporaryDirectory() as tmp:
            result = ContentCreationResult(
                status="completed",
                project_id="existing",
                project_root=str(Path(tmp) / "existing"),
            )
            with mock.patch("src.content_creation.cli.create_content", return_value=result) as create:
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    code = main(
                        [
                            "resume",
                            "--project-id",
                            "existing",
                            "--projects-root",
                            tmp,
                            "--json",
                        ]
                    )

        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output.getvalue())["project_id"], "existing")
        request = create.call_args.args[0]
        self.assertTrue(request.execution.resume)
        self.assertFalse(request.voice.approve_paid_generation)

    def test_paid_generation_flag_is_explicitly_forwarded(self) -> None:
        from src.content_creation.cli import main
        from src.content_creation.models import ContentCreationResult

        result = ContentCreationResult(
            status="dry_run_completed",
            project_id="new",
            project_root="unused",
        )
        with mock.patch("src.content_creation.cli.create_content", return_value=result) as create:
            with contextlib.redirect_stdout(io.StringIO()):
                code = main(
                    [
                        "create",
                        "--project-id",
                        "new",
                        "--approve-paid-generation",
                        "--dry-run",
                        "--json",
                    ]
                )

        self.assertEqual(code, 0)
        self.assertTrue(create.call_args.args[0].voice.approve_paid_generation)


class AnimeFactoryCliContractTests(unittest.TestCase):
    def test_parser_defaults_are_stable(self) -> None:
        from anime_factory import pipeline as anime_pipeline

        with mock.patch.object(sys, "argv", ["pipeline.py", "--episode", "episode_001"]):
            args = anime_pipeline.parse_args()

        self.assertEqual(args.episode, "episode_001")
        self.assertEqual(args.max_clips, 10)
        self.assertEqual(args.candidate_count, 30)
        self.assertEqual(args.min_duration, 20)
        self.assertEqual(args.max_duration, 45)
        self.assertEqual(args.crop_mode, "auto")
        self.assertFalse(args.preview_only)
        self.assertFalse(args.force)

    def test_missing_input_is_a_clean_nonzero_failure(self) -> None:
        from anime_factory import pipeline as anime_pipeline

        error = io.StringIO()
        with (
            mock.patch.object(sys, "argv", ["pipeline.py", "--episode", "episode_001"]),
            contextlib.redirect_stderr(error),
        ):
            code = anime_pipeline.main()

        self.assertEqual(code, 1)
        self.assertIn("--input", error.getvalue())
        self.assertNotIn("Traceback", error.getvalue())


if __name__ == "__main__":
    unittest.main()
