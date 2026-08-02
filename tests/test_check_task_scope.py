"""Targeted tests for the read-only task-scope checker.

Every Git fixture is created under ``TemporaryDirectory``.  The checker is
expected to inspect names and status only; it must not change HEAD, the index,
or the working tree.
"""

from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from tools.qa.check_task_scope import (
    INVALID_INPUT,
    OK,
    STOP_REQUIRED,
    check_task_scope,
    normalize_scope_rules,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def _git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["GIT_CONFIG_GLOBAL"] = os.devnull
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=check,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=environment,
    )


def _write(root: Path, relative: str, text: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


class TaskScopeCheckerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.stack = TemporaryDirectory()
        self.addCleanup(self.stack.cleanup)
        self.root = Path(self.stack.name) / "repo"
        self.root.mkdir()
        _git(self.root, "init")
        _git(self.root, "config", "user.email", "scope-tests@example.invalid")
        _git(self.root, "config", "user.name", "Scope Tests")
        for relative in (
            "allowed.txt",
            "unexpected.txt",
            "old/name.txt",
            "nested/file.txt",
            "src/news/item.py",
            "src/news_backup/item.py",
        ):
            _write(self.root, relative, f"baseline for {relative}\n")
        _git(self.root, "add", "allowed.txt", "unexpected.txt", "old/name.txt")
        _git(self.root, "add", "nested/file.txt", "src/news/item.py")
        _git(self.root, "add", "src/news_backup/item.py")
        _git(self.root, "commit", "-m", "test baseline")

    def check(
        self,
        *exact: str | Path,
        directories: tuple[str | Path, ...] = (),
    ):
        return check_task_scope(
            self.root,
            allowed_paths=exact,
            allowed_directories=directories,
        )

    def test_empty_diff_is_ok(self) -> None:
        result = self.check("allowed.txt")

        self.assertEqual(result.status, OK)
        self.assertEqual(result.changes, ())

    def test_allowed_modified_file_is_ok(self) -> None:
        _write(self.root, "allowed.txt", "changed\n")

        result = self.check("allowed.txt")

        self.assertEqual(result.status, OK)
        self.assertEqual(
            [(change.source, change.kind, change.path) for change in result.changes],
            [("unstaged", "modified", "allowed.txt")],
        )

    def test_unexpected_modified_file_requires_stop(self) -> None:
        _write(self.root, "unexpected.txt", "changed\n")

        result = self.check("allowed.txt")

        self.assertEqual(result.status, STOP_REQUIRED)
        self.assertEqual(result.unexpected_paths, ("unexpected.txt",))

    def test_allowed_added_file_is_ok(self) -> None:
        _write(self.root, "added.txt", "new\n")
        _git(self.root, "add", "added.txt")

        result = self.check("added.txt")

        self.assertEqual(result.status, OK)
        self.assertEqual(result.changes[0].kind, "added")

    def test_unexpected_untracked_file_requires_stop(self) -> None:
        _write(self.root, "untracked.txt", "new\n")

        result = self.check("allowed.txt")

        self.assertEqual(result.status, STOP_REQUIRED)
        self.assertEqual(result.changes[0].kind, "untracked")
        self.assertEqual(result.unexpected_paths, ("untracked.txt",))

    def test_allowed_deletion_is_ok(self) -> None:
        (self.root / "allowed.txt").unlink()

        result = self.check("allowed.txt")

        self.assertEqual(result.status, OK)
        self.assertEqual(result.changes[0].kind, "deleted")

    def test_unexpected_deletion_requires_stop(self) -> None:
        (self.root / "unexpected.txt").unlink()

        result = self.check("allowed.txt")

        self.assertEqual(result.status, STOP_REQUIRED)
        self.assertEqual(result.unexpected_paths, ("unexpected.txt",))

    def test_allowed_rename_requires_both_paths(self) -> None:
        (self.root / "renamed").mkdir()
        _git(self.root, "mv", "old/name.txt", "renamed/name.txt")

        result = self.check("old/name.txt", "renamed/name.txt")

        self.assertEqual(result.status, OK)
        rename = result.changes[0]
        self.assertEqual((rename.kind, rename.old_path, rename.path), (
            "renamed",
            "old/name.txt",
            "renamed/name.txt",
        ))

    def test_rename_with_unexpected_old_path_requires_stop(self) -> None:
        (self.root / "renamed").mkdir()
        _git(self.root, "mv", "old/name.txt", "renamed/name.txt")

        result = self.check("renamed/name.txt")

        self.assertEqual(result.status, STOP_REQUIRED)
        self.assertEqual(result.unexpected_paths, ("old/name.txt",))

    def test_rename_with_unexpected_new_path_requires_stop(self) -> None:
        (self.root / "renamed").mkdir()
        _git(self.root, "mv", "old/name.txt", "renamed/name.txt")

        result = self.check("old/name.txt")

        self.assertEqual(result.status, STOP_REQUIRED)
        self.assertEqual(result.unexpected_paths, ("renamed/name.txt",))

    def test_multiple_unexpected_paths_are_complete_and_stably_sorted(self) -> None:
        _write(self.root, "z-last.txt", "new\n")
        _write(self.root, "unexpected.txt", "changed\n")
        (self.root / "old/name.txt").unlink()

        result = self.check("allowed.txt")

        self.assertEqual(result.status, STOP_REQUIRED)
        self.assertEqual(
            result.unexpected_paths,
            ("old/name.txt", "unexpected.txt", "z-last.txt"),
        )

    def test_staged_change_is_detected(self) -> None:
        _write(self.root, "allowed.txt", "staged\n")
        _git(self.root, "add", "allowed.txt")

        result = self.check("allowed.txt")

        self.assertEqual(result.status, OK)
        self.assertEqual(result.changes[0].source, "staged")

    def test_unstaged_change_is_detected(self) -> None:
        _write(self.root, "allowed.txt", "unstaged\n")

        result = self.check("allowed.txt")

        self.assertEqual(result.status, OK)
        self.assertEqual(result.changes[0].source, "unstaged")

    def test_staged_and_unstaged_changes_are_both_preserved(self) -> None:
        _write(self.root, "allowed.txt", "staged\n")
        _git(self.root, "add", "allowed.txt")
        _write(self.root, "allowed.txt", "staged then unstaged\n")

        result = self.check("allowed.txt")

        self.assertEqual(result.status, OK)
        self.assertEqual(
            [(change.source, change.kind) for change in result.changes],
            [("staged", "modified"), ("unstaged", "modified")],
        )

    def test_windows_separators_are_normalized(self) -> None:
        _write(self.root, "nested/file.txt", "changed\n")

        result = self.check(r"nested\file.txt")

        self.assertEqual(result.status, OK)
        self.assertEqual(result.allowed_scope, ("exact:nested/file.txt",))

    def test_explicit_directory_rule_allows_a_descendant(self) -> None:
        _write(self.root, "src/news/item.py", "changed\n")

        result = self.check(directories=("src/news",))

        self.assertEqual(result.status, OK)

    def test_directory_prefix_has_a_component_boundary(self) -> None:
        _write(self.root, "src/news_backup/item.py", "changed\n")

        result = self.check(directories=("src/news",))

        self.assertEqual(result.status, STOP_REQUIRED)
        self.assertEqual(result.unexpected_paths, ("src/news_backup/item.py",))

    def test_path_traversal_outside_root_is_invalid(self) -> None:
        result = self.check("../escape.txt")

        self.assertEqual(result.status, INVALID_INPUT)
        self.assertIn("outside repository root", result.explanation)

    def test_absolute_path_outside_repository_is_invalid(self) -> None:
        outside = self.root.parent / "outside.txt"

        result = self.check(outside)

        self.assertEqual(result.status, INVALID_INPUT)
        self.assertIn("outside repository root", result.explanation)

    def test_absolute_path_inside_repository_is_normalized(self) -> None:
        _write(self.root, "allowed.txt", "changed\n")

        result = self.check(self.root / "allowed.txt")

        self.assertEqual(result.status, OK)
        self.assertEqual(result.allowed_scope, ("exact:allowed.txt",))

    def test_dot_and_duplicate_separators_are_normalized(self) -> None:
        _write(self.root, "nested/file.txt", "changed\n")

        result = self.check("./nested//./file.txt")

        self.assertEqual(result.status, OK)
        self.assertEqual(result.allowed_scope, ("exact:nested/file.txt",))

    def test_duplicate_allowed_entries_are_deduplicated_stably(self) -> None:
        rules = normalize_scope_rules(
            self.root,
            allowed_paths=("allowed.txt", r".\allowed.txt", "allowed.txt"),
            allowed_directories=(),
        )

        self.assertEqual([rule.label for rule in rules], ["exact:allowed.txt"])

    @unittest.skipUnless(os.name == "nt", "Windows case behavior")
    def test_windows_path_matching_is_case_insensitive(self) -> None:
        _write(self.root, "allowed.txt", "changed\n")

        result = self.check("ALLOWED.TXT")

        self.assertEqual(result.status, OK)

    def test_non_git_directory_is_invalid_input(self) -> None:
        with TemporaryDirectory() as temp_dir:
            result = check_task_scope(
                Path(temp_dir),
                allowed_paths=("allowed.txt",),
            )

        self.assertEqual(result.status, INVALID_INPUT)
        self.assertIn("Git", result.explanation)

    def test_checker_does_not_change_head_index_or_worktree(self) -> None:
        _write(self.root, "allowed.txt", "staged\n")
        _git(self.root, "add", "allowed.txt")
        _write(self.root, "allowed.txt", "staged then unstaged\n")
        before = self._repository_fingerprint()

        result = self.check("allowed.txt")

        after = self._repository_fingerprint()
        self.assertEqual(result.status, OK)
        self.assertEqual(after, before)

    def test_cli_prints_machine_readable_status_and_uses_contract_exit_codes(self) -> None:
        ok = self._cli("--allow", "allowed.txt")
        _write(self.root, "unexpected.txt", "changed\n")
        stop = self._cli("--allow", "allowed.txt")
        invalid = self._cli()

        self.assertEqual(ok.returncode, 0, ok.stderr)
        self.assertTrue(ok.stdout.startswith("STATUS: OK\n"), ok.stdout)
        self.assertEqual(stop.returncode, 1, stop.stderr)
        self.assertTrue(
            stop.stdout.startswith("STATUS: STOP_REQUIRED\n"), stop.stdout
        )
        self.assertIn("unexpected.txt", stop.stdout)
        self.assertIn("request an owner decision", stop.stdout)
        self.assertEqual(invalid.returncode, 2, invalid.stderr)
        self.assertTrue(
            invalid.stdout.startswith("STATUS: INVALID_INPUT\n"), invalid.stdout
        )

    def _repository_fingerprint(self) -> tuple[str, bytes, bytes, bytes]:
        head = _git(self.root, "rev-parse", "HEAD").stdout.strip()
        status = subprocess.run(
            [
                "git",
                "status",
                "--porcelain=v1",
                "-z",
                "--untracked-files=all",
                "--renames",
            ],
            cwd=self.root,
            check=True,
            capture_output=True,
        ).stdout
        cached = subprocess.run(
            ["git", "diff", "--cached", "--binary"],
            cwd=self.root,
            check=True,
            capture_output=True,
        ).stdout
        index = (self.root / ".git" / "index").read_bytes()
        return head, status, cached, index

    def _cli(self, *extra: str) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment["GIT_CONFIG_GLOBAL"] = os.devnull
        return subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "tools.qa.check_task_scope",
                "--root",
                str(self.root),
                *extra,
            ],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=environment,
        )


if __name__ == "__main__":
    unittest.main()
