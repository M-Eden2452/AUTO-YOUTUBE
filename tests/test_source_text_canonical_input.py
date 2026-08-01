from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from src.ai_youtube.apps.content_creator.workflows.fullscreen_voiceover.use_case import (
    resolve_content_inputs,
    resolve_script_source,
)
from src.ai_youtube.cli.main import build_parser, main, run_content_creation_cli
from src.content_creation.models import ContentCreationRequest, ContentCreationResult


class _CreateRecorder:
    def __init__(self) -> None:
        self.requests: list[ContentCreationRequest] = []

    def __call__(self, request: ContentCreationRequest) -> ContentCreationResult:
        self.requests.append(request)
        return ContentCreationResult(
            status="dry_run_completed",
            project_id="recorded",
            project_root=request.project_overrides["projects_root"],
        )


class SourceTextCanonicalInputTests(unittest.TestCase):
    def _capture_request(self, extra_args: list[str]) -> ContentCreationRequest:
        recorder = _CreateRecorder()
        with tempfile.TemporaryDirectory() as tmp:
            args = build_parser().parse_args(
                [
                    "create",
                    "--template",
                    "fullscreen_voiceover_v1",
                    "--channel",
                    "nature_science_news_ru",
                    "--projects-root",
                    tmp,
                    *extra_args,
                ]
            )
            self.assertEqual(
                run_content_creation_cli(args, create_content_fn=recorder),
                0,
            )
        self.assertEqual(len(recorder.requests), 1)
        return recorder.requests[0]

    def _run_rejected(self, extra_args: list[str]) -> dict:
        recorder = _CreateRecorder()
        output = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(output):
            args = build_parser().parse_args(
                [
                    "create",
                    "--template",
                    "fullscreen_voiceover_v1",
                    "--channel",
                    "nature_science_news_ru",
                    "--projects-root",
                    tmp,
                    "--json",
                    *extra_args,
                ]
            )
            code = run_content_creation_cli(args, create_content_fn=recorder)
        self.assertEqual(code, 1)
        self.assertEqual(recorder.requests, [])
        return json.loads(output.getvalue())

    def test_source_text_parses_into_existing_field_with_explicit_mode(self) -> None:
        request = self._capture_request(["--source-text", "Prepared material"])
        self.assertEqual(request.pasted_script, "Prepared material")
        self.assertEqual(request.content_input_mode, "pasted_script")

    def test_source_text_file_parses_into_existing_field_with_explicit_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.txt"
            source.write_text("Prepared file material", encoding="utf-8")
            request = self._capture_request(["--source-text-file", str(source)])
        self.assertEqual(request.script_path, str(source))
        self.assertEqual(request.content_input_mode, "script_file")

    def test_pasted_script_remains_an_alias_with_explicit_mode(self) -> None:
        request = self._capture_request(["--pasted-script", "Legacy alias"])
        self.assertEqual(request.pasted_script, "Legacy alias")
        self.assertEqual(request.content_input_mode, "pasted_script")

    def test_script_file_remains_an_alias_with_explicit_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "legacy.txt"
            source.write_text("Legacy file alias", encoding="utf-8")
            request = self._capture_request(["--script-file", str(source)])
        self.assertEqual(request.script_path, str(source))
        self.assertEqual(request.content_input_mode, "script_file")

    def test_story_card_text_keeps_its_existing_destination(self) -> None:
        recorder = _CreateRecorder()
        with tempfile.TemporaryDirectory() as tmp:
            args = build_parser().parse_args(
                [
                    "create",
                    "--template",
                    "story_card_text_only_v1",
                    "--channel",
                    "nature_pulse",
                    "--projects-root",
                    tmp,
                    "--text",
                    "Card headline",
                ]
            )
            self.assertEqual(
                run_content_creation_cli(args, create_content_fn=recorder),
                0,
            )
        request = recorder.requests[0]
        self.assertEqual(request.text, {"top": "Card headline"})
        self.assertEqual(request.pasted_script, "")
        self.assertEqual(request.content_input_mode, "")

    def test_inline_and_file_inputs_are_rejected_before_pipeline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.txt"
            source.write_text("File material", encoding="utf-8")
            error = self._run_rejected(
                [
                    "--source-text",
                    "Inline material",
                    "--source-text-file",
                    str(source),
                ]
            )
        self.assertEqual(error["reason"], "invalid_content")
        self.assertIn("one authoritative", error["error"].lower())

    def test_source_text_conflicts_with_topic_mode(self) -> None:
        error = self._run_rejected(
            ["--source-text", "Prepared material", "--input-mode", "topic"]
        )
        self.assertEqual(error["reason"], "invalid_content")
        self.assertIn("input-mode", error["error"])

    def test_source_text_file_conflicts_with_topic_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.txt"
            source.write_text("Prepared file material", encoding="utf-8")
            error = self._run_rejected(
                ["--source-text-file", str(source), "--input-mode", "topic"]
            )
        self.assertEqual(error["reason"], "invalid_content")
        self.assertIn("input-mode", error["error"])

    def test_explicit_compatible_mode_is_preserved(self) -> None:
        request = self._capture_request(
            [
                "--source-text",
                "Prepared material",
                "--input-mode",
                "pasted_script",
            ]
        )
        self.assertEqual(request.content_input_mode, "pasted_script")

    def test_source_text_conflicts_with_source_url(self) -> None:
        error = self._run_rejected(
            [
                "--source-text",
                "Prepared material",
                "--source-url",
                "https://example.com/article",
            ]
        )
        self.assertEqual(error["reason"], "invalid_content")

    def test_empty_source_text_is_rejected(self) -> None:
        error = self._run_rejected(["--source-text", "   "])
        self.assertEqual(error["reason"], "empty")

    def test_missing_source_text_file_is_rejected(self) -> None:
        error = self._run_rejected(
            ["--source-text-file", "definitely-missing-source.txt"]
        )
        self.assertEqual(error["reason"], "not_found")

    def test_legacy_programmatic_unspecified_mode_is_unchanged(self) -> None:
        request = ContentCreationRequest(pasted_script="Legacy programmatic input")
        self.assertEqual(request.content_input_mode, "")
        self.assertEqual(
            resolve_content_inputs(request),
            (None, None, "Legacy programmatic input", None),
        )
        self.assertEqual(resolve_script_source(request), "")

    def test_canonical_input_reaches_existing_news_job_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = main(
                    [
                        "create",
                        "--template",
                        "fullscreen_voiceover_v1",
                        "--channel",
                        "nature_science_news_ru",
                        "--source-text",
                        "Prepared downstream material",
                        "--dry-run",
                        "--projects-root",
                        tmp,
                        "--json",
                    ]
                )
            self.assertEqual(code, 0, output.getvalue())
            jobs = list(Path(tmp).glob("*/job.json"))
            self.assertEqual(len(jobs), 1)
            job = json.loads(jobs[0].read_text(encoding="utf-8"))
        self.assertEqual(job["input_mode"], "text")
        self.assertEqual(job["input_text"], "Prepared downstream material")
        self.assertEqual(job["script_source"], "user_script")

    def test_create_help_shows_canonical_flags_and_compatibility_aliases(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output), self.assertRaises(SystemExit) as ctx:
            build_parser().parse_args(["create", "--help"])
        self.assertEqual(ctx.exception.code, 0)
        help_text = output.getvalue()
        for flag in (
            "--source-text",
            "--source-text-file",
            "--pasted-script",
            "--script-file",
            "--text",
        ):
            self.assertIn(flag, help_text)


if __name__ == "__main__":
    unittest.main()
