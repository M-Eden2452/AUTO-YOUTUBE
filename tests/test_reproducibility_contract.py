from __future__ import annotations

import re
import tomllib
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _requirement_name(value: str) -> str:
    return re.split(r"[<>=!~;\s\[]", value, maxsplit=1)[0].lower().replace("_", "-")


class ReproducibilityContractTests(unittest.TestCase):
    def test_d03_package_discovery_uses_only_runtime_package_roots(self) -> None:
        pyproject = tomllib.loads(
            (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        )
        discovery = pyproject["tool"]["setuptools"]["packages"]["find"]

        self.assertEqual(discovery["where"], ["."])
        self.assertEqual(
            discovery["include"],
            ["ai_youtube*", "src*", "anime_factory*", "apps*"],
        )
        self.assertNotIn("packages*", discovery["include"])
        self.assertFalse((REPO_ROOT / "packages").exists())

    def test_pyproject_and_direct_requirements_match(self) -> None:
        pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        declared = set(pyproject["project"]["dependencies"])
        requirements = {
            line.strip()
            for line in (REPO_ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }

        self.assertEqual(declared, requirements)
        self.assertEqual(pyproject["project"]["requires-python"], ">=3.11")

    def test_lock_is_fully_pinned_and_covers_direct_dependencies(self) -> None:
        lines = [
            line.strip()
            for line in (REPO_ROOT / "requirements.lock").read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        self.assertTrue(lines)
        self.assertTrue(all("==" in line for line in lines))

        locked_names = {_requirement_name(line) for line in lines}
        direct_names = {
            _requirement_name(line)
            for line in (REPO_ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }
        self.assertGreaterEqual(locked_names, direct_names)
        self.assertEqual(len(locked_names), len(lines))

    def test_offline_ci_runs_the_guarded_unittest_suite(self) -> None:
        workflow = (REPO_ROOT / ".github" / "workflows" / "offline-tests.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn('AI_YOUTUBE_ALLOW_LIVE_TESTS: "0"', workflow)
        self.assertIn('AI_YOUTUBE_RUN_LIVE_TESTS: "0"', workflow)
        self.assertIn("python -m pip install --requirement requirements.lock", workflow)
        self.assertIn(
            "python -m pip install --no-deps --no-build-isolation --editable .",
            workflow,
        )
        self.assertIn('python -B -m unittest discover -s tests -p "test_*.py"', workflow)

    def test_line_endings_and_binary_artifacts_are_declared(self) -> None:
        attributes = (REPO_ROOT / ".gitattributes").read_text(encoding="utf-8")
        self.assertIn("*.py text eol=lf", attributes)
        self.assertIn("*.json text eol=lf", attributes)
        self.assertIn("*.mp4 binary", attributes)
        self.assertIn("*.wav binary", attributes)


if __name__ == "__main__":
    unittest.main()
