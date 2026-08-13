from __future__ import annotations

import atexit
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from tests.test_semantic_visual_evaluation import _controlled_live_eval_dataset_path, _write_prepared_dataset
from tests.test_semantic_visual_integration import _write_visual_review_fixture
from tests.test_visual_preview_integration import _candidate


class VisualPreviewCliWiringTests(unittest.TestCase):
    def test_cli_prepare_and_inspect_on_fake_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "project_001"
            visual_dir = project / "localizations" / "ru" / "visual"
            assets_dir = project / "assets"
            visual_dir.mkdir(parents=True)
            assets_dir.mkdir(parents=True)
            preview = assets_dir / "fixture.jpg"
            Image.new("RGB", (1080, 1920), (30, 70, 120)).save(preview)
            visual_plan = {"language": "ru", "resolution": {"width": 1080, "height": 1920}, "scenes": [{"scene_id": "scene_001", "visual_type": "image", "primary_query": "ocean science"}]}
            assets_manifest = {
                "schema_version": 1,
                "scenes": [
                    {
                        "scene_id": "scene_001",
                        "primary_query": "ocean science",
                        "visual_type": "image",
                        "semantic_scene": {"visual_priority": "environment"},
                        "queries": [{"query": "ocean science"}],
                        "provider_routing": {"ordered_providers": ["fake"]},
                        "ranked_candidates": [{**_candidate("a1"), "local_path": str(preview), "path": str(preview)}],
                        "selected_asset": {**_candidate("a1"), "local_path": str(preview), "path": str(preview)},
                    }
                ],
                "missing_scenes": [],
            }
            (visual_dir / "visual_plan.json").write_text(json.dumps(visual_plan, ensure_ascii=False), encoding="utf-8")
            (assets_dir / "assets_manifest.json").write_text(json.dumps(assets_manifest, ensure_ascii=False), encoding="utf-8")

            prepare = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    "pipeline.py",
                    "visual-preview",
                    "prepare",
                    "--projects-root",
                    str(root),
                    "--project-id",
                    "project_001",
                    "--scene-id",
                    "scene_001",
                    "--top-k",
                    "3",
                    "--offline",
                ],
                cwd=Path(__file__).resolve().parents[1],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=os_environ_without_live_flags(),
            )
            inspect = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    "pipeline.py",
                    "visual-preview",
                    "inspect",
                    "--projects-root",
                    str(root),
                    "--project-id",
                    "project_001",
                ],
                cwd=Path(__file__).resolve().parents[1],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=os_environ_without_live_flags(),
            )

            self.assertEqual(prepare.returncode, 0, prepare.stderr)
            self.assertEqual(inspect.returncode, 0, inspect.stderr)
            self.assertTrue((project / "assets" / "review" / "visual_review_manifest.json").is_file())
            self.assertTrue((project / "assets" / "review" / "visual_review_board.html").is_file())
            self.assertIn("analysed_candidates=1", inspect.stdout)


class SemanticBackendCliWiringTests(unittest.TestCase):
    def test_diagnostics_cli_is_offline_and_redacts_key(self) -> None:
        secret = "sk-test-SHOULD-NOT-PRINT"
        env = os_environ_without_live_flags()
        env["OPENAI_API_KEY"] = secret

        result = subprocess.run(
            [sys.executable, "-B", "pipeline.py", "semantic-backend", "diagnostics", "--backend", "openai"],
            cwd=Path(__file__).resolve().parents[1],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("[semantic-backend] configured=True", result.stdout)
        self.assertIn("[semantic-backend] key_configured=True", result.stdout)
        self.assertIn("[semantic-backend] live_status=not_checked", result.stdout)
        self.assertNotIn(secret, result.stdout)
        self.assertNotIn("sk-test", result.stdout)

    def test_dry_run_evaluation_cli_blocks_live_calls(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-B",
                "pipeline.py",
                "semantic-backend",
                "evaluate",
                "--backend",
                "openai",
                "--model",
                "gpt-5.6-terra",
                "--dry-run",
            ],
            cwd=Path(__file__).resolve().parents[1],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=os_environ_without_live_flags(),
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("[semantic-backend] dry_run=True", result.stdout)
        self.assertIn("[semantic-backend] projected_calls=", result.stdout)
        self.assertIn("[semantic-backend] projected_image_count=", result.stdout)
        self.assertIn("live_blocked_reasons=", result.stdout)
        self.assertIn("allow_paid_vision_required", result.stdout)

    def test_explicit_dataset_loads_requested_dataset(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dataset_path = _write_prepared_dataset(Path(tmp), scenes=1, candidates_per_scene=1, frames_per_candidate=2)

            result = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    "pipeline.py",
                    "semantic-backend",
                    "evaluate",
                    "--backend",
                    "openai",
                    "--model",
                    "gpt-5.6-terra",
                    "--dataset",
                    str(dataset_path),
                    "--dry-run",
                ],
                cwd=Path(__file__).resolve().parents[1],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=os_environ_without_live_flags(),
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"[semantic-backend] dataset_path={dataset_path}", result.stdout)
        self.assertIn("[semantic-backend] scenes=1", result.stdout)
        self.assertIn("[semantic-backend] candidates=1", result.stdout)
        self.assertIn("[semantic-backend] projected_image_count=1", result.stdout)

    def test_full_cli_gates_authorize_controlled_runtime_evaluation(self) -> None:
        env = os_environ_without_live_flags()
        env["OPENAI_API_KEY"] = "sk-test-not-printed"

        result = subprocess.run(
            [
                sys.executable,
                "-B",
                "pipeline.py",
                "semantic-backend",
                "evaluate",
                "--backend",
                "openai",
                "--model",
                "gpt-5.6-terra",
                "--dataset",
                str(_controlled_live_eval_dataset_path()),
                "--dry-run",
                "--allow-paid-vision",
                "--budget-usd",
                "0.50",
                "--max-calls",
                "6",
                "--confirm-paid-vision",
                "LIVE_VISION_APPROVED",
            ],
            cwd=Path(__file__).resolve().parents[1],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("[semantic-backend] runtime_authorized=True", result.stdout)
        self.assertIn("[semantic-backend] budget_allowed=True", result.stdout)
        self.assertIn("[semantic-backend] projected_calls=6", result.stdout)
        self.assertIn("[semantic-backend] projected_image_count=6", result.stdout)
        self.assertNotIn("sk-test", result.stdout)

    def test_mocked_evaluation_cli_for_tests(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-B",
                "pipeline.py",
                "semantic-backend",
                "evaluate",
                "--backend",
                "openai",
                "--model",
                "gpt-5.6-terra",
                "--mocked",
            ],
            cwd=Path(__file__).resolve().parents[1],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=os_environ_without_live_flags(),
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("[semantic-backend] mocked=True", result.stdout)
        self.assertIn("[semantic-backend] structured_output_validity=", result.stdout)
        self.assertIn("[semantic-backend] paid_calls_performed=False", result.stdout)


class SemanticVisualCliWiringTests(unittest.TestCase):
    def test_semantic_cli_analyse_and_inspect_on_mock_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = _write_visual_review_fixture(Path(tmp), cases=["good_match"])
            projects_root = project.parent

            analyse = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    "pipeline.py",
                    "semantic-visual",
                    "analyse",
                    "--projects-root",
                    str(projects_root),
                    "--project-id",
                    "project_001",
                    "--scene-id",
                    "scene_001",
                    "--backend",
                    "mock",
                ],
                cwd=Path(__file__).resolve().parents[1],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=os_environ_without_live_flags(),
            )
            inspect = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    "pipeline.py",
                    "semantic-visual",
                    "inspect",
                    "--projects-root",
                    str(projects_root),
                    "--project-id",
                    "project_001",
                ],
                cwd=Path(__file__).resolve().parents[1],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=os_environ_without_live_flags(),
            )

            self.assertEqual(analyse.returncode, 0, analyse.stderr)
            self.assertEqual(inspect.returncode, 0, inspect.stderr)
            self.assertIn("[semantic-visual] successful_analyses=1", analyse.stdout)
            self.assertIn("[semantic-visual] analysed_candidates=1", inspect.stdout)


_WIRING_WORKSPACE: tempfile.TemporaryDirectory | None = None


def _wiring_workspace_root() -> str:
    """Одна tmp-workspace на модуль для всех subprocess-вызовов.

    ``pipeline.py`` main() материализует ``outputs/`` и ``assets/*`` под
    workspace root (pipeline.py:96-99); без переопределения каждый subprocess
    воскрешает ретайренный repo-root ``outputs/`` (registry R02).
    """
    global _WIRING_WORKSPACE
    if _WIRING_WORKSPACE is None:
        _WIRING_WORKSPACE = tempfile.TemporaryDirectory(prefix="ai_youtube_wiring_ws_")
        atexit.register(_WIRING_WORKSPACE.cleanup)
    return _WIRING_WORKSPACE.name


def os_environ_without_live_flags() -> dict[str, str]:
    import os

    env = dict(os.environ)
    env.pop("AI_YOUTUBE_ALLOW_LIVE_TESTS", None)
    env.pop("AI_YOUTUBE_RUN_LIVE_TESTS", None)
    env["AI_YOUTUBE_WORKSPACE"] = _wiring_workspace_root()
    return env


if __name__ == "__main__":
    unittest.main()
