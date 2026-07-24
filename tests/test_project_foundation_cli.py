from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

REPO_ROOT = Path(__file__).resolve().parents[1]


def _run_cli(args: list[str], *, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-B", "-m", "src.project_foundation.cli", *args],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


class ProjectFoundationCliTests(unittest.TestCase):
    def test_channels_list_empty(self) -> None:
        with TemporaryDirectory() as tmp:
            channels_root = Path(tmp) / "channels"
            result = _run_cli(["--channels-root", str(channels_root), "channels", "list"], cwd=Path(tmp))

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout), [])

    def test_channels_create_and_show(self) -> None:
        with TemporaryDirectory() as tmp:
            channels_root = Path(tmp) / "channels"
            config_path = Path(tmp) / "channel_config.json"
            config_path.write_text(
                json.dumps({"channel_id": "cli_channel", "display_name": "CLI Channel", "default_language": "ru"}),
                encoding="utf-8",
            )

            create_result = _run_cli(
                ["--channels-root", str(channels_root), "channels", "create", "--config", str(config_path)],
                cwd=Path(tmp),
            )
            show_result = _run_cli(
                ["--channels-root", str(channels_root), "channels", "show", "cli_channel"],
                cwd=Path(tmp),
            )

            self.assertEqual(create_result.returncode, 0, create_result.stderr)
            self.assertEqual(show_result.returncode, 0, show_result.stderr)
            payload = json.loads(show_result.stdout)
            self.assertEqual(payload["channel_id"], "cli_channel")
            self.assertEqual(payload["display_name"], "CLI Channel")
            self.assertTrue((channels_root / "cli_channel" / "channel.json").is_file())

    def test_channels_show_missing_returns_nonzero(self) -> None:
        with TemporaryDirectory() as tmp:
            channels_root = Path(tmp) / "channels"
            result = _run_cli(["--channels-root", str(channels_root), "channels", "show", "missing"], cwd=Path(tmp))

            self.assertNotEqual(result.returncode, 0)
            payload = json.loads(result.stderr)
            self.assertIn("error", payload)

    def test_channels_validate_reports_errors_for_bad_config(self) -> None:
        with TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "bad_channel.json"
            config_path.write_text(json.dumps({"channel_id": ""}), encoding="utf-8")

            result = _run_cli(["channels", "validate", "--config", str(config_path)], cwd=Path(tmp))

            self.assertNotEqual(result.returncode, 0)
            payload = json.loads(result.stdout)
            self.assertFalse(payload["valid"])
            self.assertTrue(payload["errors"])

    def test_channels_validate_passes_for_good_config(self) -> None:
        with TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "good_channel.json"
            config_path.write_text(json.dumps({"channel_id": "ok_channel"}), encoding="utf-8")

            result = _run_cli(["channels", "validate", "--config", str(config_path)], cwd=Path(tmp))

            self.assertEqual(result.returncode, 0, result.stdout)
            payload = json.loads(result.stdout)
            self.assertTrue(payload["valid"])

    def test_projects_create_dry_run_and_real_then_list_and_show(self) -> None:
        with TemporaryDirectory() as tmp:
            channels_root = Path(tmp) / "channels"
            projects_root = Path(tmp) / "projects"
            channel_config = Path(tmp) / "channel_config.json"
            channel_config.write_text(
                json.dumps(
                    {
                        "channel_id": "cli_channel",
                        "default_language": "ru",
                        "supported_languages": ["ru"],
                        "default_application": "content_creator",
                        "default_format": "vertical_short",
                        "default_template": "story_card_text_only_v1",
                        "export_targets": ["youtube_shorts"],
                    }
                ),
                encoding="utf-8",
            )
            _run_cli(
                ["--channels-root", str(channels_root), "channels", "create", "--config", str(channel_config)],
                cwd=Path(tmp),
            )

            project_config = Path(tmp) / "project_config.json"
            project_config.write_text(
                json.dumps({"channel_id": "cli_channel", "title": "CLI Project", "project_id": "cli_project"}),
                encoding="utf-8",
            )

            dry_run_result = _run_cli(
                [
                    "--channels-root", str(channels_root),
                    "--projects-root", str(projects_root),
                    "projects", "create", "--config", str(project_config), "--dry-run",
                ],
                cwd=Path(tmp),
            )
            self.assertEqual(dry_run_result.returncode, 0, dry_run_result.stderr)
            self.assertTrue(json.loads(dry_run_result.stdout)["dry_run"])
            self.assertFalse(projects_root.exists())

            create_result = _run_cli(
                [
                    "--channels-root", str(channels_root),
                    "--projects-root", str(projects_root),
                    "projects", "create", "--config", str(project_config),
                ],
                cwd=Path(tmp),
            )
            self.assertEqual(create_result.returncode, 0, create_result.stderr)
            self.assertTrue((projects_root / "cli_project" / "project.json").is_file())

            list_result = _run_cli(["--projects-root", str(projects_root), "projects", "list"], cwd=Path(tmp))
            show_result = _run_cli(
                ["--projects-root", str(projects_root), "projects", "show", "cli_project"], cwd=Path(tmp)
            )

            self.assertEqual(list_result.returncode, 0, list_result.stderr)
            self.assertEqual([item["project_id"] for item in json.loads(list_result.stdout)], ["cli_project"])
            self.assertEqual(json.loads(show_result.stdout)["title"], "CLI Project")

    def test_projects_validate_and_evidence_commands(self) -> None:
        with TemporaryDirectory() as tmp:
            channels_root = Path(tmp) / "channels"
            projects_root = Path(tmp) / "projects"
            channel_config = Path(tmp) / "channel_config.json"
            channel_config.write_text(
                json.dumps(
                    {
                        "channel_id": "policy_channel",
                        "default_application": "content_creator",
                        "default_format": "vertical_short",
                        "default_template": "story_card_text_only_v1",
                        "export_targets": ["youtube_shorts"],
                        "output_policy": {"allow_unknown_license": True},
                    }
                ),
                encoding="utf-8",
            )
            _run_cli(
                ["--channels-root", str(channels_root), "channels", "create", "--config", str(channel_config)],
                cwd=Path(tmp),
            )

            project_config = Path(tmp) / "project_config.json"
            project_config.write_text(
                json.dumps({"channel_id": "policy_channel", "title": "Policy Project", "project_id": "policy_project"}),
                encoding="utf-8",
            )
            _run_cli(
                [
                    "--channels-root", str(channels_root),
                    "--projects-root", str(projects_root),
                    "projects", "create", "--config", str(project_config),
                ],
                cwd=Path(tmp),
            )

            evidence_result = _run_cli(
                ["--projects-root", str(projects_root), "projects", "evidence-list", "policy_project"], cwd=Path(tmp)
            )
            rights_result = _run_cli(
                ["--projects-root", str(projects_root), "projects", "rights-report", "policy_project"], cwd=Path(tmp)
            )
            validate_result = _run_cli(
                [
                    "--channels-root", str(channels_root),
                    "--projects-root", str(projects_root),
                    "projects", "validate", "policy_project",
                ],
                cwd=Path(tmp),
            )

            self.assertEqual(evidence_result.returncode, 0, evidence_result.stderr)
            self.assertEqual(json.loads(evidence_result.stdout), [])
            self.assertEqual(rights_result.returncode, 0, rights_result.stderr)
            self.assertTrue((projects_root / "policy_project" / "evidence" / "rights_report.json").is_file())
            self.assertEqual(validate_result.returncode, 0, validate_result.stderr)
            self.assertTrue(json.loads(validate_result.stdout)["allowed"])

    def test_cli_does_not_import_pipeline(self) -> None:
        result = subprocess.run(
            [sys.executable, "-B", "-c", "import sys; import src.project_foundation.cli; assert 'pipeline' not in sys.modules"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_does_not_write_to_real_channels_or_projects(self) -> None:
        real_channels = set(Path("channels").iterdir()) if Path("channels").is_dir() else set()
        real_projects = set(Path("projects").iterdir()) if Path("projects").is_dir() else set()

        with TemporaryDirectory() as tmp:
            _run_cli(["--channels-root", str(Path(tmp) / "channels"), "channels", "list"], cwd=Path(tmp))

        self.assertEqual(set(Path("channels").iterdir()) if Path("channels").is_dir() else set(), real_channels)
        self.assertEqual(set(Path("projects").iterdir()) if Path("projects").is_dir() else set(), real_projects)


if __name__ == "__main__":
    unittest.main()
