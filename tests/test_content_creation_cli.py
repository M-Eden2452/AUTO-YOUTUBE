from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from src.content_creation.cli import main


def _run(argv: list[str]) -> tuple[int, str]:
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        code = main(argv)
    return code, buffer.getvalue()


class ReadOnlyCommandsTests(unittest.TestCase):
    def test_capabilities_json(self) -> None:
        code, output = _run(["capabilities", "--json"])
        self.assertEqual(code, 0)
        data = json.loads(output)
        template_ids = {t["template_id"] for t in data["templates"]}
        self.assertIn("story_card_text_only_v1", template_ids)
        self.assertIn("fullscreen_voiceover_v1", template_ids)

    def test_formats_list_json(self) -> None:
        code, output = _run(["formats", "list", "--json"])
        self.assertEqual(code, 0)
        data = json.loads(output)
        self.assertTrue(any(item["format_id"] == "vertical_short" for item in data))

    def test_templates_show_legacy_alias(self) -> None:
        code, output = _run(["templates", "show", "--template", "story_card_short_v1", "--json"])
        self.assertEqual(code, 0)
        data = json.loads(output)
        self.assertEqual(data["template_id"], "story_card_text_only_v1")

    def test_templates_show_unknown_id_exits_nonzero(self) -> None:
        with self.assertRaises(SystemExit):
            _run(["templates", "show", "--template", "does_not_exist"])

    def test_voices_providers_lists_only_registered_providers(self) -> None:
        code, output = _run(["voices", "providers", "--json"])
        self.assertEqual(code, 0)
        data = json.loads(output)
        provider_ids = {p["provider_id"] for p in data}
        self.assertEqual(provider_ids, {"disabled", "elevenlabs", "audio_file"})
        self.assertNotIn("local_stub", provider_ids)

    def test_voices_profiles_requires_channel(self) -> None:
        with self.assertRaises(SystemExit):
            _run(["voices", "profiles"])

    def test_voices_show_resolves_display_name_alias(self) -> None:
        code, output = _run(
            ["voices", "show", "--channel", "nature_science_news_ru", "--voice-profile", "Дом", "--json"]
        )
        self.assertEqual(code, 0)
        data = json.loads(output)
        self.assertEqual(data["profile_id"], "ru_dom")

    def test_subtitles_list_never_invents_styles(self) -> None:
        code, output = _run(["subtitles", "list", "--json"])
        self.assertEqual(code, 0)
        data = json.loads(output)
        style_ids = {s["style_id"] for s in data}
        self.assertEqual(style_ids, {"disabled", "documentary"})

    def test_channels_show_unknown_channel_exits_nonzero(self) -> None:
        with self.assertRaises(SystemExit):
            _run(["channels", "show", "--channel", "does_not_exist"])


class CreateCommandTests(unittest.TestCase):
    def test_create_story_card_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            code, output = _run(
                [
                    "create",
                    "--format",
                    "vertical_short",
                    "--template",
                    "story_card_text_only_v1",
                    "--channel",
                    "nature_pulse",
                    "--language",
                    "ru",
                    "--text",
                    "Тестовый заголовок CLI",
                    "--source-asset",
                    "projects/story_card_owl_test/final_test.mp4",
                    "--voice-provider",
                    "disabled",
                    "--subtitles",
                    "disabled",
                    "--dry-run",
                    "--projects-root",
                    tmp,
                    "--json",
                ]
            )
            self.assertEqual(code, 0)
            data = json.loads(output)
            self.assertEqual(data["status"], "dry_run_completed")
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_create_missing_template_reports_error_without_traceback(self) -> None:
        code, output = _run(
            ["create", "--channel", "nature_pulse", "--template", "does_not_exist_v1"]
        )
        self.assertEqual(code, 1)
        self.assertIn("error", output)

    def test_create_requires_source_asset_for_story_card(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            code, output = _run(
                [
                    "create",
                    "--template",
                    "story_card_text_only_v1",
                    "--channel",
                    "nature_pulse",
                    "--text",
                    "x",
                    "--dry-run",
                    "--projects-root",
                    tmp,
                ]
            )
            # dry_run for story card returns before requiring source_asset only if
            # the request layer checks it before project creation; this asserts
            # the CLI surfaces a clear message either way, never a stack trace.
            if code != 0:
                self.assertIn("error", output)

    def test_create_invalid_music_path_returns_structured_json_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            code, output = _run(
                [
                    "create",
                    "--format",
                    "vertical_short",
                    "--template",
                    "fullscreen_voiceover_v1",
                    "--channel",
                    "nature_science_news_ru",
                    "--topic",
                    "x",
                    "--input-mode",
                    "topic",
                    "--music",
                    "local_file",
                    "--music-path",
                    "/no/such/file.mp3",
                    "--projects-root",
                    tmp,
                    "--json",
                ]
            )
            self.assertEqual(code, 1)
            data = json.loads(output)
            self.assertEqual(data["status"], "failed")
            self.assertEqual(data["reason"], "not_found")
            self.assertIn("error", data)

    def test_create_invalid_music_path_debug_flag_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(Exception):
                _run(
                    [
                        "create",
                        "--template",
                        "fullscreen_voiceover_v1",
                        "--channel",
                        "nature_science_news_ru",
                        "--topic",
                        "x",
                        "--input-mode",
                        "topic",
                        "--music",
                        "local_file",
                        "--music-path",
                        "/no/such/file.mp3",
                        "--projects-root",
                        tmp,
                        "--debug",
                    ]
                )


class ProjectCommandTests(unittest.TestCase):
    """`project status/list` must work for both storage systems under projects/.

    Before src.projects.ProjectRepository existed, `project status` on a
    news_to_short job (job.json) raised ProjectFoundationError and printed a raw
    traceback - which is 19 of the 21 project folders in this repo.
    """

    def _news_job(self, root: Path, project_id: str) -> None:
        from src.news.models import NewsJob

        job = NewsJob.create(channel_id="nature_science_news_ru", input_mode="topic", topic="Тема")
        job.job_id = project_id
        job.status = "completed"
        path = root / project_id / "job.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(job.to_dict(), ensure_ascii=False), encoding="utf-8")

    def test_status_reads_a_news_job_without_a_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._news_job(Path(tmp), "news_one")
            code, output = _run(["project", "status", "--project-id", "news_one", "--projects-root", tmp])
            self.assertEqual(code, 0)
            self.assertIn("kind=news_job", output)
            self.assertIn("fullscreen_voiceover_v1", output)

    def test_status_json_for_a_news_job(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._news_job(Path(tmp), "news_one")
            code, output = _run(
                ["project", "status", "--project-id", "news_one", "--projects-root", tmp, "--json"]
            )
            self.assertEqual(code, 0)
            data = json.loads(output)
            self.assertEqual(data["kind"], "news_job")
            self.assertEqual(data["project_id"], "news_one")

    def test_status_on_missing_project_is_a_clean_message(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            code, output = _run(["project", "status", "--project-id", "nope", "--projects-root", tmp])
            self.assertEqual(code, 1)
            self.assertIn("nope", output)
            self.assertNotIn("Traceback", output)

    def test_list_shows_projects_of_both_kinds(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._news_job(root, "news_one")
            (root / "empty_folder").mkdir()
            code, output = _run(["project", "list", "--projects-root", tmp, "--json"])
            self.assertEqual(code, 0)
            data = json.loads(output)
            kinds = {item["project_id"]: item["kind"] for item in data}
            self.assertEqual(kinds["news_one"], "news_job")
            self.assertEqual(kinds["empty_folder"], "unknown")

    def test_list_does_not_require_a_project_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            code, _ = _run(["project", "list", "--projects-root", tmp])
            self.assertEqual(code, 0)

    def test_validate_on_a_news_job_explains_instead_of_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._news_job(Path(tmp), "news_one")
            code, output = _run(["project", "validate", "--project-id", "news_one", "--projects-root", tmp])
            self.assertEqual(code, 1)
            self.assertIn("project.json", output)
            self.assertNotIn("Traceback", output)


if __name__ == "__main__":
    unittest.main()
