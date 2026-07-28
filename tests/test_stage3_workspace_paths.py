from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path


class ExistingProjectsRootContractTests(unittest.TestCase):
    def test_explicit_projects_root_remains_authoritative(self) -> None:
        from src.content_creation.cli import build_parser, run_content_creation_cli

        with tempfile.TemporaryDirectory() as temporary:
            projects_root = Path(temporary) / "isolated-projects"
            project_root = projects_root / "known-project"
            project_root.mkdir(parents=True)
            (project_root / "job.json").write_text(
                json.dumps(
                    {
                        "job_id": "known-project",
                        "title": "Characterized",
                        "channel_id": "nature_science_news_ru",
                        "template_id": "fullscreen_voiceover_v1",
                        "language": "ru",
                        "status": "created",
                    }
                ),
                encoding="utf-8",
            )

            args = build_parser().parse_args(
                ["project", "list", "--projects-root", str(projects_root), "--json"]
            )
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = run_content_creation_cli(args)

        self.assertEqual(code, 0)
        projects = json.loads(output.getvalue())
        self.assertEqual([project["project_id"] for project in projects], ["known-project"])

    def test_legacy_pipeline_parser_keeps_workspace_override(self) -> None:
        import pipeline

        args = pipeline.parse_args(
            ["--workspace", "runtime-fixture", "--paths-config", "paths.json"]
        )

        self.assertEqual(args.workspace, "runtime-fixture")
        self.assertEqual(args.paths_config, "paths.json")


class ApplicationPathResolutionTests(unittest.TestCase):
    def test_precedence_is_cli_then_environment_then_config_then_legacy_default(self) -> None:
        from src.config_resolver import ENV_WORKSPACE_ROOT, resolve_application_paths

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repository = root / "repository"
            repository.mkdir()
            config_file = root / "paths.json"
            config_file.write_text(
                json.dumps({"workspace_root": "configured"}),
                encoding="utf-8",
            )

            configured = resolve_application_paths(
                paths_config=config_file,
                environment={},
                repository_root=repository,
            )
            environment = resolve_application_paths(
                paths_config=config_file,
                environment={ENV_WORKSPACE_ROOT: str(root / "environment")},
                repository_root=repository,
            )
            cli = resolve_application_paths(
                workspace_root=root / "cli",
                paths_config=config_file,
                environment={ENV_WORKSPACE_ROOT: str(root / "environment")},
                repository_root=repository,
            )
            legacy = resolve_application_paths(
                environment={},
                repository_root=repository,
            )

        self.assertEqual(configured.workspace.root, root / "configured")
        self.assertEqual(environment.workspace.root, root / "environment")
        self.assertEqual(cli.workspace.root, root / "cli")
        self.assertEqual(legacy.workspace.root, repository)

    def test_config_can_name_workspace_subdirectories(self) -> None:
        from src.config_resolver import resolve_application_paths

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repository = root / "repository"
            repository.mkdir()
            config_file = root / "paths.json"
            config_file.write_text(
                json.dumps(
                    {
                        "workspace_root": "runtime",
                        "projects_dir": "jobs",
                        "outputs_dir": "deliveries",
                    }
                ),
                encoding="utf-8",
            )

            paths = resolve_application_paths(
                paths_config=config_file,
                environment={},
                repository_root=repository,
            )

        self.assertEqual(paths.projects_root, root / "runtime" / "jobs")
        self.assertEqual(paths.outputs_root, root / "runtime" / "deliveries")

    def test_existing_output_falls_back_to_repository_outputs(self) -> None:
        from src.config_resolver import resolve_application_paths

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repository = root / "repository"
            legacy_output = repository / "outputs" / "old" / "final.mp4"
            legacy_output.parent.mkdir(parents=True)
            legacy_output.write_bytes(b"legacy")
            paths = resolve_application_paths(
                workspace_root=root / "workspace",
                environment={},
                repository_root=repository,
            )

            found = paths.find_output(Path("old") / "final.mp4")

        self.assertEqual(found, legacy_output)

    def test_default_application_resources_do_not_depend_on_cwd(self) -> None:
        from src.assets.license_policy import load_license_policy
        from src.content_creation.capabilities import list_channels
        from src.production_plan.story_card_short_render import load_story_card_preset

        with tempfile.TemporaryDirectory() as temporary:
            previous = Path.cwd()
            os.chdir(temporary)
            try:
                channels = list_channels()
                policy = load_license_policy()
                preset = load_story_card_preset()
            finally:
                os.chdir(previous)

        self.assertTrue(channels)
        self.assertNotEqual(policy["policy_version"], "missing-policy")
        self.assertEqual(preset["name"], "story_card_short_v1")


class LegacyProjectFallbackTests(unittest.TestCase):
    @staticmethod
    def _write_job(root: Path, project_id: str, title: str) -> None:
        project_root = root / project_id
        project_root.mkdir(parents=True)
        (project_root / "job.json").write_text(
            json.dumps(
                {
                    "job_id": project_id,
                    "title": title,
                    "channel_id": "nature_science_news_ru",
                    "language": "ru",
                    "status": "created",
                }
            ),
            encoding="utf-8",
        )

    def test_repository_reads_primary_and_legacy_roots_with_primary_precedence(self) -> None:
        from src.projects import ProjectRepository

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            primary = root / "workspace" / "projects"
            legacy = root / "repository" / "projects"
            self._write_job(primary, "duplicate", "Primary")
            self._write_job(legacy, "duplicate", "Legacy")
            self._write_job(legacy, "legacy-only", "Legacy only")

            repository = ProjectRepository(primary, fallback_roots=[legacy])
            project_ids = repository.list_ids()
            duplicate = repository.get("duplicate")
            legacy_only = repository.get("legacy-only")

        self.assertEqual(project_ids, ["duplicate", "legacy-only"])
        self.assertEqual(duplicate.title, "Primary")
        self.assertEqual(legacy_only.title, "Legacy only")
        self.assertEqual(Path(legacy_only.project_root), legacy / "legacy-only")

    def test_content_cli_accepts_workspace_without_changing_explicit_root_contract(self) -> None:
        from src.content_creation.cli import build_parser, run_content_creation_cli

        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary) / "workspace"
            self._write_job(workspace / "projects", "workspace-project", "Workspace")
            args = build_parser().parse_args(
                ["project", "status", "--project-id", "workspace-project", "--workspace", str(workspace), "--json"]
            )
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = run_content_creation_cli(args)

        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output.getvalue())["project_id"], "workspace-project")
        self.assertEqual(args.projects_root, str(workspace / "projects"))
        self.assertTrue(args.project_fallback_roots)

    def test_new_news_project_is_written_only_to_selected_workspace(self) -> None:
        from src.config_resolver import resolve_application_paths
        from src.news.pipeline import create_news_to_short_job

        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary) / "workspace"
            paths = resolve_application_paths(
                workspace_root=workspace,
                environment={},
            )
            job = create_news_to_short_job(
                projects_root=paths.projects_root,
                topic="Workspace fixture",
                title="Workspace fixture",
                now="2026-07-28T12:00:00+00:00",
            )

            manifest = paths.projects_root / job.job_id / "job.json"
            manifest_exists = manifest.is_file()
            manifest_projects_root = manifest.parent.parent

        self.assertTrue(manifest_exists)
        self.assertEqual(manifest_projects_root, workspace / "projects")


if __name__ == "__main__":
    unittest.main()
