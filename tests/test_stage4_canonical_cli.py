from __future__ import annotations

import ast
import contextlib
import io
import json
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported


def _constructed_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }


class CanonicalDispatcherCharacterizationTests(unittest.TestCase):
    def test_python_module_dispatcher_matches_legacy_capabilities_contract(self) -> None:
        from src.content_creation.cli import main as legacy_main

        legacy_stdout = io.StringIO()
        with contextlib.redirect_stdout(legacy_stdout):
            self.assertEqual(legacy_main(["capabilities", "--json"]), 0)

        completed = subprocess.run(
            [sys.executable, "-B", "-m", "ai_youtube", "capabilities", "--json"],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout), json.loads(legacy_stdout.getvalue()))

    def test_canonical_help_only_advertises_active_content_creator_commands(self) -> None:
        completed = subprocess.run(
            [sys.executable, "-B", "-m", "ai_youtube", "--help"],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("python -m ai_youtube", completed.stdout)
        self.assertIn("create", completed.stdout)
        self.assertIn("project", completed.stdout)
        self.assertNotIn("video_repurposer", completed.stdout)
        self.assertNotIn("documentary", completed.stdout)

    def test_capability_registry_never_marks_disabled_apps_ready(self) -> None:
        from src.content_creation.capabilities import build_capabilities_report

        applications = {
            item["application_id"]: item
            for item in build_capabilities_report()["applications"]
        }

        self.assertTrue(applications["content_creator"]["enabled"])
        self.assertEqual(
            applications["content_creator"]["implementation_status"],
            "active",
        )
        self.assertFalse(applications["video_repurposer"]["enabled"])
        self.assertEqual(
            applications["video_repurposer"]["implementation_status"],
            "planned",
        )

    def test_default_app_listing_contains_only_ready_applications(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "ai_youtube",
                "applications",
                "list",
                "--json",
            ],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        applications = json.loads(completed.stdout)
        self.assertEqual(
            [item["application_id"] for item in applications],
            ["content_creator"],
        )

    def test_planned_application_is_visible_only_when_explicitly_requested(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "ai_youtube",
                "applications",
                "show",
                "--application",
                "video_repurposer",
                "--json",
            ],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        application = json.loads(completed.stdout)
        self.assertFalse(application["enabled"])
        self.assertEqual(application["implementation_status"], "planned")

    def test_new_rerun_instructions_use_the_canonical_dispatcher(self) -> None:
        from src.assets.completion.report import _replace_command
        from src.content_creation.models import ContentCreationRequest
        from src.content_creation.service import (
            _fullscreen_rerun_command,
            _story_card_rerun_command,
        )

        request = ContentCreationRequest(
            channel_id="nature_science_news_ru",
            language="ru",
        )
        for command in (
            _story_card_rerun_command(request),
            _fullscreen_rerun_command(request, "job_001"),
            _replace_command("job_001", "scene_001", "slot_001"),
        ):
            self.assertIn("-m ai_youtube", command)
            self.assertNotIn("-m src.content_creation.cli", command)


class CliBoundaryCharacterizationTests(unittest.TestCase):
    def test_command_parser_definitions_are_split_by_domain(self) -> None:
        from src.content_creation.commands import (
            authoring,
            catalog,
            content,
            projects,
        )

        self.assertTrue(callable(authoring.register_commands))
        self.assertTrue(callable(catalog.register_commands))
        self.assertTrue(callable(content.register_commands))
        self.assertTrue(callable(projects.register_commands))

    def test_wizard_does_not_import_cli_presentation(self) -> None:
        imports = _imported_modules(REPO_ROOT / "src/content_creation/wizard.py")
        self.assertNotIn("src.content_creation.cli", imports)

    def test_cli_and_wizard_delegate_request_construction(self) -> None:
        for relative_path in (
            "src/content_creation/cli.py",
            "src/content_creation/wizard.py",
        ):
            constructed = _constructed_names(REPO_ROOT / relative_path)
            self.assertNotIn(
                "ContentCreationRequest",
                constructed,
                f"{relative_path} still owns application request construction.",
            )


if __name__ == "__main__":
    unittest.main()
