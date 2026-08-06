"""Owning module for the versioned Claude permission contract (PLAN-STAB-6).

Класс по ``PROJECT_EXECUTION_PLAN.md`` этому модулю **не** присвоен по той же
причине, что и ``tests/test_check_agent_docs.py``: current governance
классифицирует конкретный закрытый перечень test-модулей
(``CLEANUP_REGISTRY.md``, «Accidental invariants»), и новый модуль в него не
входит.

Protects:
- ``.claude/settings.json`` остаётся deny/ask-only: ``permissions.allow`` в
  versioned контракте запрещён, а удалённые владельцем широкие гранты
  (``git add *``, ``git commit *``, ``python -c``, ``python -``) не могут
  вернуться в репозиторий;
- каждая governance-зона требует подтверждения и на ``Edit``, и на ``Write``:
  исчезновение любой из них — ошибка, называющая зону и tool;
- ``.claude/settings.local.json`` закрыт агенту на Read/Write/Edit и остаётся
  untracked и ignored;
- перечисленные секретные ``.env.*`` покрыты, а tracked ``.env.example``
  намеренно **не** покрыт: свойство PLAN-6D-1 («0 deny matches») сохранено, и
  общий blanket-pattern отвергается отдельной проверкой;
- destructive Git разделён на два непересекающихся набора, и перенос правила из
  одной корзины в другую — ошибка;
- правило с ведущим wildcard отвергается;
- checker остаётся read-only: он не меняет worktree.

Does not prove:
- что matcher действительно применяет эти правила именно так. Точная semantics
  wildcard, precedence корзин и поведение path-правил в ``ask`` в этом слайсе
  эмпирически не проверялись; проверяется текст versioned контракта;
- что Bash защищён. Правила по путям к Bash не применяются, поэтому глобальные
  Git options, shell aliases и произвольный интерпретатор остаются вне
  контракта. Именно поэтому env-покрытие проверяется только для Read/Write/Edit
  и ни одно ``Bash(...)`` env-правило контрактом не требуется;
- что effective merged user/managed/local configuration защищена. Она лежит вне
  репозитория и различается по средам; проверяется только versioned contract;
- что перечисление ``.env.*`` полно. Имя вне списка не покрыто — это принятый
  владельцем residual risk, а не пропущенная проверка.
"""

from __future__ import annotations

import json
import os
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from tools.qa import check_agent_docs
from tools.qa.check_agent_docs import validate_claude_permissions, validate_repository


REPO_ROOT = Path(__file__).resolve().parents[1]

SETTINGS = check_agent_docs.CLAUDE_SETTINGS
LOCAL_SETTINGS = check_agent_docs.CLAUDE_LOCAL_SETTINGS
LOCAL_RULE_PATH = check_agent_docs.CLAUDE_LOCAL_SETTINGS_RULE_PATH


def _env_rules(names: tuple[str, ...]) -> list[str]:
    """Same expansion the contract uses, rebuilt here instead of imported.

    Deliberately not the checker's own helper: a fixture that reuses the
    implementation cannot notice when the implementation changes shape.
    """

    return [
        f"{tool}({location}{name})"
        for name in names
        for tool in check_agent_docs.SECRET_FILE_TOOLS
        for location in ("./", "./**/")
    ]


def _valid_settings() -> dict:
    """A minimal contract that satisfies every rule the checker requires."""

    ask = ["WebFetch", "WebSearch"]
    ask.extend(check_agent_docs.DESTRUCTIVE_GIT_ASK)
    ask.extend(
        f"{tool}({protected})"
        for protected in check_agent_docs.PROTECTED_GOVERNANCE_PATHS
        for tool in check_agent_docs.PROTECTED_GOVERNANCE_TOOLS
    )
    deny = list(check_agent_docs.DESTRUCTIVE_GIT_DENY)
    deny.extend(
        f"{tool}({LOCAL_RULE_PATH})"
        for tool in check_agent_docs.LOCAL_SETTINGS_DENIED_TOOLS
    )
    deny.extend(_env_rules(check_agent_docs.SECRET_ENV_NAMES))
    return {
        "$schema": "https://json.schemastore.org/claude-code-settings.json",
        "permissions": {"defaultMode": "default", "ask": ask, "deny": deny},
    }


class PermissionContractTests(unittest.TestCase):
    """Synthetic roots only: the outcome never depends on local settings."""

    def setUp(self) -> None:
        self.stack = TemporaryDirectory()
        self.addCleanup(self.stack.cleanup)
        self.root = Path(self.stack.name)
        (self.root / SETTINGS.parent).mkdir(parents=True, exist_ok=True)
        self.settings = _valid_settings()

    def _write(self, payload: dict | None = None, *, raw: str | None = None) -> None:
        text = raw if raw is not None else json.dumps(payload or self.settings, indent=2)
        (self.root / SETTINGS).write_text(text, encoding="utf-8")

    def _errors(self) -> list[str]:
        self._write()
        return validate_claude_permissions(self.root)

    def test_valid_contract_passes(self) -> None:
        self.assertEqual(self._errors(), [])

    def test_missing_settings_file_is_an_error(self) -> None:
        errors = validate_claude_permissions(self.root)
        self.assertEqual(len(errors), 1)
        self.assertIn(SETTINGS.as_posix(), errors[0])

    def test_malformed_json_is_an_error(self) -> None:
        self._write(raw='{"permissions": {"ask": [}}')
        errors = validate_claude_permissions(self.root)
        self.assertEqual(len(errors), 1)
        self.assertIn("cannot read permission contract", errors[0])

    def test_permissions_allow_is_an_error(self) -> None:
        self.settings["permissions"]["allow"] = ["Bash(git status)"]
        self.assertTrue(
            any("permissions.allow is forbidden" in error for error in self._errors())
        )

    def test_secret_values_cannot_be_smuggled_into_the_contract(self) -> None:
        self.settings["env"] = {"ELEVENLABS_API_KEY": "value"}
        self.assertTrue(
            any("unexpected top-level keys env" in error for error in self._errors())
        )

    def test_forbidden_broad_grants_are_rejected(self) -> None:
        for grant in check_agent_docs.FORBIDDEN_BROAD_GRANTS:
            with self.subTest(grant=grant):
                settings = _valid_settings()
                settings["permissions"]["ask"].append(grant)
                self._write(settings)
                errors = validate_claude_permissions(self.root)
                self.assertTrue(
                    any(
                        "forbidden broad grant" in error and grant in error
                        for error in errors
                    ),
                    errors,
                )

    def test_forbidden_broad_grant_is_rejected_inside_allow(self) -> None:
        self.settings["permissions"]["allow"] = ["Bash(python -)"]
        errors = self._errors()
        self.assertTrue(any("permissions.allow is forbidden" in e for e in errors))
        self.assertTrue(any("forbidden broad grant" in e for e in errors))

    def test_leading_wildcard_is_rejected(self) -> None:
        self.settings["permissions"]["deny"].append(
            "Bash(*media-library migrate*--apply*)"
        )
        self.assertTrue(
            any("leading wildcard" in error for error in self._errors())
        )

    def test_rule_that_is_not_a_tool_pattern_is_rejected(self) -> None:
        self.settings["permissions"]["deny"].append("rm -rf /")
        self.assertTrue(
            any("neither a bare tool name" in error for error in self._errors())
        )

    def test_every_protected_zone_needs_edit_and_write(self) -> None:
        for protected in check_agent_docs.PROTECTED_GOVERNANCE_PATHS:
            for tool in check_agent_docs.PROTECTED_GOVERNANCE_TOOLS:
                with self.subTest(zone=protected, tool=tool):
                    settings = _valid_settings()
                    settings["permissions"]["ask"].remove(f"{tool}({protected})")
                    self._write(settings)
                    errors = validate_claude_permissions(self.root)
                    self.assertTrue(
                        any(
                            protected in error and f"covered by {tool}" in error
                            for error in errors
                        ),
                        errors,
                    )

    def test_protected_zone_may_be_covered_by_deny_instead_of_ask(self) -> None:
        zone = check_agent_docs.PROTECTED_GOVERNANCE_PATHS[0]
        self.settings["permissions"]["ask"].remove(f"Edit({zone})")
        self.settings["permissions"]["deny"].append(f"Edit({zone})")
        self.assertEqual(self._errors(), [])

    def test_local_settings_must_be_denied_for_read_write_edit(self) -> None:
        for tool in check_agent_docs.LOCAL_SETTINGS_DENIED_TOOLS:
            with self.subTest(tool=tool):
                settings = _valid_settings()
                settings["permissions"]["deny"].remove(f"{tool}({LOCAL_RULE_PATH})")
                self._write(settings)
                errors = validate_claude_permissions(self.root)
                self.assertTrue(
                    any(
                        f"{tool}({LOCAL_RULE_PATH})" in error
                        and "permissions.deny" in error
                        for error in errors
                    ),
                    errors,
                )

    def test_missing_secret_env_rule_is_an_error(self) -> None:
        rule = f"Read(./{check_agent_docs.SECRET_ENV_NAMES[1]})"
        self.settings["permissions"]["deny"].remove(rule)
        self.assertTrue(any(rule in error for error in self._errors()))

    def test_env_coverage_is_scoped_to_path_tools_only(self) -> None:
        # The contract makes no claim about Bash: a shell command reading a
        # secret file is not path-matched, and pretending otherwise would be
        # exactly the false protection this slice must not record.
        self.assertEqual(
            set(check_agent_docs.SECRET_FILE_TOOLS), {"Read", "Write", "Edit"}
        )
        required = _env_rules(check_agent_docs.SECRET_ENV_NAMES)
        self.assertFalse([rule for rule in required if rule.startswith("Bash(")])

    def test_tracked_env_example_must_not_be_denied(self) -> None:
        for rule in _env_rules(check_agent_docs.SECRET_ENV_EXEMPT_NAMES):
            with self.subTest(rule=rule):
                settings = _valid_settings()
                settings["permissions"]["deny"].append(rule)
                self._write(settings)
                errors = validate_claude_permissions(self.root)
                self.assertTrue(
                    any("secret-free template" in error for error in errors), errors
                )

    def test_blanket_env_pattern_is_rejected(self) -> None:
        for pattern in check_agent_docs.BLANKET_ENV_PATTERNS:
            with self.subTest(pattern=pattern):
                settings = _valid_settings()
                settings["permissions"]["deny"].append(f"Read({pattern})")
                self._write(settings)
                errors = validate_claude_permissions(self.root)
                self.assertTrue(
                    any("blanket env rule" in error for error in errors), errors
                )

    def test_destructive_git_deny_rules_cannot_be_downgraded(self) -> None:
        for rule in check_agent_docs.DESTRUCTIVE_GIT_DENY:
            with self.subTest(rule=rule):
                settings = _valid_settings()
                settings["permissions"]["deny"].remove(rule)
                settings["permissions"]["ask"].append(rule)
                self._write(settings)
                errors = validate_claude_permissions(self.root)
                self.assertTrue(
                    any(rule in error and "permissions.deny" in error for error in errors),
                    errors,
                )

    def test_destructive_git_ask_rules_must_stay_confirmations(self) -> None:
        for rule in check_agent_docs.DESTRUCTIVE_GIT_ASK:
            with self.subTest(rule=rule):
                settings = _valid_settings()
                settings["permissions"]["ask"].remove(rule)
                self._write(settings)
                errors = validate_claude_permissions(self.root)
                self.assertTrue(
                    any(rule in error and "permissions.ask" in error for error in errors),
                    errors,
                )

    def test_destructive_git_sets_do_not_overlap(self) -> None:
        self.assertEqual(
            set(check_agent_docs.DESTRUCTIVE_GIT_DENY)
            & set(check_agent_docs.DESTRUCTIVE_GIT_ASK),
            set(),
        )

    def test_non_string_rule_is_reported(self) -> None:
        self.settings["permissions"]["deny"].append(42)
        self.assertTrue(
            any("is not a non-empty string" in error for error in self._errors())
        )


def _git_env(home: Path) -> dict[str, str]:
    return {
        **os.environ,
        "HOME": str(home),
        "USERPROFILE": str(home),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": str(home / "absent-global-gitconfig"),
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_AUTHOR_NAME": "QA",
        "GIT_AUTHOR_EMAIL": "qa@example.invalid",
        "GIT_COMMITTER_NAME": "QA",
        "GIT_COMMITTER_EMAIL": "qa@example.invalid",
    }


class LocalSettingsStayOutsideGitTests(unittest.TestCase):
    """A synthetic local repository: no network, no global Git configuration."""

    def setUp(self) -> None:
        self.stack = TemporaryDirectory()
        self.addCleanup(self.stack.cleanup)
        base = Path(self.stack.name)
        self.home = base / "home"
        self.home.mkdir()
        self.root = base / "repo"
        self.root.mkdir()
        self.env = _git_env(self.home)
        self._git("init", "--initial-branch=main")
        (self.root / SETTINGS.parent).mkdir(parents=True, exist_ok=True)
        (self.root / SETTINGS).write_text(
            json.dumps(_valid_settings(), indent=2), encoding="utf-8"
        )
        (self.root / LOCAL_SETTINGS).write_text(
            json.dumps({"permissions": {"allow": []}}), encoding="utf-8"
        )

    def _git(self, *args: str) -> None:
        subprocess.run(
            ["git", "--no-optional-locks", *args],
            cwd=self.root,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=self.env,
        )

    def test_ignored_local_settings_pass(self) -> None:
        (self.root / ".gitignore").write_text(
            f"/{LOCAL_SETTINGS.as_posix()}\n", encoding="utf-8"
        )
        self.assertEqual(validate_claude_permissions(self.root), [])

    def test_unignored_local_settings_are_reported(self) -> None:
        errors = validate_claude_permissions(self.root)
        self.assertTrue(any("is not ignored" in error for error in errors), errors)

    def test_tracked_local_settings_are_reported(self) -> None:
        self._git("add", "--force", "--", LOCAL_SETTINGS.as_posix())
        self._git("commit", "--no-gpg-sign", "-m", "track local settings")
        errors = validate_claude_permissions(self.root)
        self.assertTrue(any("is tracked by Git" in error for error in errors), errors)


class RepositoryPermissionContractTests(unittest.TestCase):
    """The contract this repository actually ships."""

    def test_real_contract_is_valid_json_without_versioned_allow(self) -> None:
        payload = json.loads((REPO_ROOT / SETTINGS).read_text(encoding="utf-8"))
        self.assertEqual(
            set(payload), set(check_agent_docs.CLAUDE_SETTINGS_TOP_LEVEL_KEYS)
        )
        self.assertNotIn("allow", payload["permissions"])
        self.assertEqual(
            set(payload["permissions"]) - check_agent_docs.CLAUDE_PERMISSION_KEYS, set()
        )

    def test_real_repository_satisfies_the_contract(self) -> None:
        self.assertEqual(validate_claude_permissions(REPO_ROOT), [])

    def test_contract_is_part_of_governance_qa(self) -> None:
        self.assertEqual(validate_repository(REPO_ROOT), [])

    def test_validator_does_not_change_the_worktree(self) -> None:
        before = self._status()
        validate_claude_permissions(REPO_ROOT)
        self.assertEqual(self._status(), before)

    @staticmethod
    def _status() -> str:
        completed = subprocess.run(
            ["git", "--no-optional-locks", "status", "--porcelain"],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        return completed.stdout


if __name__ == "__main__":
    unittest.main()
