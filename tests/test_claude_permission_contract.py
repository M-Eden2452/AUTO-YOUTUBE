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
  untracked и ignored **правилом tracked ``.gitignore``**: per-machine
  ``.git/info/exclude`` и global excludesFile доказательством не считаются;
- каждый tracked файл под ``.claude/`` требует подтверждения на ``Edit`` и
  ``Write``; список берётся из ``git ls-files``, поэтому новый tracked
  governance-файл не может появиться незамеченным;
- перечисленные секретные ``.env.*`` покрыты и в deny, и в tracked
  ``.gitignore``, а tracked ``.env.example`` намеренно **не** покрыт: свойство
  PLAN-6D-1 («0 deny matches») сохранено, и отвергается **любое** deny-правило,
  которое по модели checker'а может до него дотянуться, а не только два
  перечисленных blanket-написания;
- минимальный обязательный контракт зафиксирован литерально и **независимо**
  от констант validator, поэтому одновременное сужение settings и константы
  ловится;
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
from unittest import mock

from tools.qa import check_agent_docs
from tools.qa.check_agent_docs import validate_claude_permissions, validate_repository


REPO_ROOT = Path(__file__).resolve().parents[1]

SETTINGS = check_agent_docs.CLAUDE_SETTINGS
LOCAL_SETTINGS = check_agent_docs.CLAUDE_LOCAL_SETTINGS
LOCAL_RULE_PATH = check_agent_docs.CLAUDE_LOCAL_SETTINGS_RULE_PATH

# Literal, and deliberately not `check_agent_docs.SECRET_ENV_NAMES`: this is the
# minimum the repository must exclude, so it has to be stated independently of
# the value the checker happens to hold today.
GITIGNORE_SENSITIVE_ENV = (
    ".env",
    ".env.local",
    ".env.development",
    ".env.development.local",
    ".env.production",
    ".env.production.local",
    ".env.staging",
    ".env.staging.local",
    ".env.test",
    ".env.test.local",
    ".env.bak",
    ".env.backup",
    ".env.old",
    ".env.save",
)


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

    def test_any_deny_rule_reaching_env_example_is_rejected(self) -> None:
        """Written as literal spellings, not as a list the checker also owns.

        The first two slipped past the previous two-pattern blacklist: the
        rejection has to follow from what a rule can *match*, not from whether
        somebody remembered to enumerate its spelling.
        """

        for rule in (
            "Read(./.env*)",
            "Read(./**/.env*)",
            "Write(./.env.example)",
            "Edit(./**/.env.example)",
            "Read(./.env.*)",
            "Edit(./**/.env.*)",
            "Read(./**/.env.exampl?)",
        ):
            with self.subTest(rule=rule):
                settings = _valid_settings()
                settings["permissions"]["deny"].append(rule)
                self._write(settings)
                errors = validate_claude_permissions(self.root)
                self.assertTrue(
                    any("secret-free template" in error for error in errors), errors
                )

    def test_exact_sensitive_env_rules_are_not_false_positives(self) -> None:
        """The exempt-template check must not fire on the real deny rules.

        `Read(./.env)`, `Read(./**/.env)` and every `.env.<name>` rule live in
        the valid fixture; a model that flagged them would force the contract
        to drop the coverage it exists to provide.
        """

        deny = self.settings["permissions"]["deny"]
        self.assertIn("Read(./.env)", deny)
        self.assertIn("Read(./**/.env)", deny)
        self.assertIn("Edit(./**/.env.production.local)", deny)
        self.assertEqual(self._errors(), [])

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


class _SyntheticRepositoryTestCase(unittest.TestCase):
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
        self._write_settings(_valid_settings())
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

    def _write_settings(self, payload: dict) -> None:
        (self.root / SETTINGS).write_text(
            json.dumps(payload, indent=2), encoding="utf-8"
        )

    def _write_gitignore(
        self,
        *,
        local_settings: bool = True,
        env_names: tuple[str, ...] = GITIGNORE_SENSITIVE_ENV,
        track: bool = True,
    ) -> None:
        lines = list(env_names)
        if local_settings:
            lines.append(f"/{LOCAL_SETTINGS.as_posix()}")
        (self.root / ".gitignore").write_text(
            "\n".join(lines) + "\n", encoding="utf-8"
        )
        if track:
            self._git("add", "--", ".gitignore")
            self._git("commit", "--no-gpg-sign", "-m", "ignore rules")


class TrackedIgnoreRulesTests(_SyntheticRepositoryTestCase):
    """Only the repository's own tracked .gitignore proves an exclusion.

    A per-machine ignore file makes one checkout look protected while CI and
    every other clone stay exposed, so `git check-ignore` alone is not an
    answer: the *source* of the exclusion is what the contract requires.
    """

    def test_tracked_gitignore_rules_pass(self) -> None:
        self._write_gitignore()
        self.assertEqual(validate_claude_permissions(self.root), [])

    def test_untracked_gitignore_is_reported(self) -> None:
        self._write_gitignore(track=False)
        errors = validate_claude_permissions(self.root)
        self.assertTrue(
            any("missing tracked .gitignore" in error for error in errors), errors
        )

    def test_local_settings_without_a_tracked_rule_are_reported(self) -> None:
        self._write_gitignore(local_settings=False)
        errors = validate_claude_permissions(self.root)
        self.assertTrue(
            any(
                LOCAL_SETTINGS.as_posix() in error
                and "not excluded by the tracked .gitignore" in error
                for error in errors
            ),
            errors,
        )

    def test_git_info_exclude_is_not_accepted(self) -> None:
        """The exact hole the previous `check-ignore --quiet` call left open."""

        self._write_gitignore(local_settings=False)
        exclude = self.root / ".git" / "info" / "exclude"
        exclude.parent.mkdir(parents=True, exist_ok=True)
        exclude.write_text(f"/{LOCAL_SETTINGS.as_posix()}\n", encoding="utf-8")
        errors = validate_claude_permissions(self.root)
        self.assertTrue(
            any(
                "excluded only by" in error and "info/exclude" in error
                for error in errors
            ),
            errors,
        )

    def test_global_excludes_file_is_not_accepted(self) -> None:
        self._write_gitignore(local_settings=False)
        excludes = self.home / "global-ignore"
        excludes.write_text(f"/{LOCAL_SETTINGS.as_posix()}\n", encoding="utf-8")
        config = self.home / "global-gitconfig"
        config.write_text(
            f"[core]\n\texcludesFile = {excludes.as_posix()}\n", encoding="utf-8"
        )
        with mock.patch.dict(os.environ, {"GIT_CONFIG_GLOBAL": str(config)}):
            errors = validate_claude_permissions(self.root)
        self.assertTrue(
            any(
                LOCAL_SETTINGS.as_posix() in error
                and "not excluded by the tracked .gitignore" in error
                for error in errors
            ),
            errors,
        )

    def test_missing_sensitive_env_rule_is_reported(self) -> None:
        kept = tuple(
            name for name in GITIGNORE_SENSITIVE_ENV if name != ".env.production"
        )
        self._write_gitignore(env_names=kept)
        errors = validate_claude_permissions(self.root)
        self.assertTrue(
            any(
                error.startswith(".env.production is not excluded")
                for error in errors
            ),
            errors,
        )

    def test_ignoring_the_tracked_template_is_reported(self) -> None:
        self._write_gitignore(env_names=(*GITIGNORE_SENSITIVE_ENV, ".env.example"))
        errors = validate_claude_permissions(self.root)
        self.assertTrue(
            any(error.startswith(".env.example is ignored by") for error in errors),
            errors,
        )

    def test_negated_template_rule_is_not_read_as_an_exclusion(self) -> None:
        """`!.env.example` means the opposite of a match, not an exclusion."""

        self._write_gitignore(env_names=(*GITIGNORE_SENSITIVE_ENV, "!.env.example"))
        errors = validate_claude_permissions(self.root)
        self.assertEqual(errors, [])

    def test_tracked_local_settings_are_reported(self) -> None:
        self._write_gitignore()
        self._git("add", "--force", "--", LOCAL_SETTINGS.as_posix())
        self._git("commit", "--no-gpg-sign", "-m", "track local settings")
        errors = validate_claude_permissions(self.root)
        self.assertTrue(any("is tracked by Git" in error for error in errors), errors)


class TrackedClaudeGovernanceTests(_SyntheticRepositoryTestCase):
    """Tracked files under .claude/ need Edit and Write confirmation.

    The tracked set comes from `git ls-files`, so this fails for a governance
    file nobody remembered to add to the contract - which is precisely how the
    reviewer adapter went unguarded.
    """

    AGENT_FILE = ".claude/agents/review-change.md"

    def _track_agent_file(self) -> None:
        path = self.root / self.AGENT_FILE
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("adapter\n", encoding="utf-8")
        self._git("add", "--", self.AGENT_FILE)
        self._git("commit", "--no-gpg-sign", "-m", "track adapter")

    def test_tracked_agent_file_without_confirmation_is_reported(self) -> None:
        self._write_gitignore()
        self._track_agent_file()
        errors = validate_claude_permissions(self.root)
        for tool in ("Edit", "Write"):
            with self.subTest(tool=tool):
                self.assertTrue(
                    any(
                        self.AGENT_FILE in error and f"not covered by {tool}" in error
                        for error in errors
                    ),
                    errors,
                )

    def test_tracked_agent_file_with_confirmation_passes(self) -> None:
        settings = _valid_settings()
        settings["permissions"]["ask"].extend(
            ["Edit(./.claude/agents/**)", "Write(./.claude/agents/**)"]
        )
        self._write_settings(settings)
        self._write_gitignore()
        self._track_agent_file()
        self.assertEqual(validate_claude_permissions(self.root), [])

    def test_new_tracked_claude_file_is_detected(self) -> None:
        settings = _valid_settings()
        settings["permissions"]["ask"].extend(
            ["Edit(./.claude/agents/**)", "Write(./.claude/agents/**)"]
        )
        self._write_settings(settings)
        self._write_gitignore()
        self._track_agent_file()
        (self.root / ".claude/hooks.json").write_text("{}", encoding="utf-8")
        self._git("add", "--", ".claude/hooks.json")
        self._git("commit", "--no-gpg-sign", "-m", "track hooks")
        errors = validate_claude_permissions(self.root)
        self.assertTrue(
            any(".claude/hooks.json" in error for error in errors), errors
        )

    def test_gitignored_local_settings_is_not_tracked_governance(self) -> None:
        """The exact deny owns it, so it must not also demand an ask rule."""

        settings = _valid_settings()
        settings["permissions"]["ask"].extend(
            ["Edit(./.claude/agents/**)", "Write(./.claude/agents/**)"]
        )
        self._write_settings(settings)
        self._write_gitignore()
        self._track_agent_file()
        errors = validate_claude_permissions(self.root)
        self.assertFalse(
            [error for error in errors if LOCAL_SETTINGS.as_posix() in error], errors
        )


class MinimumContractPinnedIndependentlyTests(unittest.TestCase):
    """The minimum contract, stated literally and read from the real files.

    Nothing here may come from ``PROTECTED_GOVERNANCE_PATHS``,
    ``SECRET_ENV_NAMES``, ``DESTRUCTIVE_GIT_DENY``, ``DESTRUCTIVE_GIT_ASK`` or
    ``FORBIDDEN_BROAD_GRANTS``. Every other test in this module derives its
    expectations from those constants, so deleting a zone from the constant
    *and* from ``settings.json`` in one edit stayed green: the fixture simply
    stopped mentioning it. These tests are the second, independent statement
    that makes such a simultaneous narrowing fail.

    It is the *minimum*, not a byte-for-byte copy of ``settings.json``: rules
    may be added freely, and only removing one of these breaks the build.
    """

    REQUIRED_CONFIRMED_PATHS = (
        "./AGENTS.md",
        "./CLAUDE.md",
        "./skills/**",
        "./tools/qa/**",
        "./.github/workflows/**",
        "./docs/current/PROJECT_EXECUTION_PLAN.md",
        "./docs/archive/**",
        "./docs/handoff/**",
        "./.claude/settings.json",
        "./.claude/agents/**",
    )
    REQUIRED_DENY = (
        "Read(./.claude/settings.local.json)",
        "Write(./.claude/settings.local.json)",
        "Edit(./.claude/settings.local.json)",
        "Bash(git reset --hard)",
        "Bash(git reset --hard *)",
        "Bash(git reset * --hard)",
        "Bash(git reset * --hard *)",
        "Bash(git clean)",
        "Bash(git clean *)",
        "Bash(git push --force*)",
        "Bash(git push * --force*)",
        "Bash(git push -f)",
        "Bash(git push -f *)",
        "Bash(git push * -f)",
        "Bash(git push * -f *)",
        "Bash(git filter-branch)",
        "Bash(git filter-branch *)",
        "Bash(git reflog delete *)",
        "Bash(git reflog expire *)",
        "Bash(git update-ref -d *)",
        "Bash(git update-ref --no-deref -d *)",
        "Bash(git gc --prune*)",
        "Bash(git gc * --prune*)",
    )
    REQUIRED_ASK = (
        "Bash(git checkout --)",
        "Bash(git checkout -- *)",
        "Bash(git checkout * -- *)",
        "Bash(git restore)",
        "Bash(git restore *)",
        "Bash(git rm)",
        "Bash(git rm *)",
        "Bash(git branch -D)",
        "Bash(git branch -D *)",
        "Bash(git worktree remove)",
        "Bash(git worktree remove *)",
    )
    FORBIDDEN_ANYWHERE = (
        "Bash(*)",
        "Bash(git add *)",
        "Bash(git commit *)",
        "Bash(python -c ' *)",
        "Bash(python -)",
        "Bash(./venv/Scripts/python.exe -c ' *)",
        "Bash(./venv/Scripts/python.exe -B -c ' *)",
        "Bash(G:/Projects/AI-YouTube/venv/Scripts/python.exe -B -c ' *)",
    )
    SENSITIVE_ENV_NAMES = GITIGNORE_SENSITIVE_ENV
    EXEMPT_ENV_NAME = ".env.example"

    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = json.loads(
            (REPO_ROOT / ".claude/settings.json").read_text(encoding="utf-8")
        )
        cls.permissions = cls.payload["permissions"]
        cls.ask = list(cls.permissions.get("ask", []))
        cls.deny = list(cls.permissions.get("deny", []))
        cls.confirmed = set(cls.ask) | set(cls.deny)

    def test_versioned_contract_has_no_allow_bucket(self) -> None:
        self.assertNotIn("allow", self.permissions)

    def test_every_required_zone_is_confirmed_for_edit_and_write(self) -> None:
        for path in self.REQUIRED_CONFIRMED_PATHS:
            for tool in ("Edit", "Write"):
                with self.subTest(path=path, tool=tool):
                    self.assertIn(f"{tool}({path})", self.confirmed)

    def test_every_tracked_claude_file_is_a_confirmed_governance_path(self) -> None:
        completed = subprocess.run(
            ["git", "--no-optional-locks", "ls-files", "--", ".claude/"],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        tracked = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
        self.assertIn(".claude/agents/review-change.md", tracked)
        self.assertIn(".claude/settings.json", tracked)
        for path in tracked:
            with self.subTest(path=path):
                self.assertTrue(
                    path == ".claude/settings.json"
                    or path.startswith(".claude/agents/"),
                    f"{path} is tracked under .claude/ but no literal rule here "
                    "covers it; add the rule to settings.json and name it above",
                )

    def test_every_sensitive_env_name_is_denied_for_path_tools(self) -> None:
        for env_name in self.SENSITIVE_ENV_NAMES:
            for tool in ("Read", "Write", "Edit"):
                for location in ("./", "./**/"):
                    rule = f"{tool}({location}{env_name})"
                    with self.subTest(rule=rule):
                        self.assertIn(rule, self.deny)

    def test_no_deny_rule_names_the_tracked_template(self) -> None:
        self.assertFalse(
            [rule for rule in self.deny if self.EXEMPT_ENV_NAME in rule]
        )

    def test_required_destructive_git_deny_rules_are_present(self) -> None:
        for rule in self.REQUIRED_DENY:
            with self.subTest(rule=rule):
                self.assertIn(rule, self.deny)

    def test_required_destructive_git_ask_rules_are_present(self) -> None:
        for rule in self.REQUIRED_ASK:
            with self.subTest(rule=rule):
                self.assertIn(rule, self.ask)

    def test_forbidden_broad_grants_are_absent_from_every_bucket(self) -> None:
        every_rule = [
            rule
            for values in self.permissions.values()
            if isinstance(values, list)
            for rule in values
        ]
        for grant in self.FORBIDDEN_ANYWHERE:
            with self.subTest(grant=grant):
                self.assertNotIn(grant, every_rule)

    def test_tracked_gitignore_lists_every_sensitive_env_name(self) -> None:
        lines = [
            line.strip()
            for line in (REPO_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        ]
        for env_name in self.SENSITIVE_ENV_NAMES:
            with self.subTest(env_name=env_name):
                self.assertIn(env_name, lines)
        self.assertNotIn(self.EXEMPT_ENV_NAME, lines)
        self.assertIn(f"/{LOCAL_SETTINGS.as_posix()}", lines)

    def test_tracked_template_stays_tracked_and_unignored(self) -> None:
        tracked = subprocess.run(
            [
                "git",
                "--no-optional-locks",
                "ls-files",
                "--error-unmatch",
                "--",
                self.EXEMPT_ENV_NAME,
            ],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        self.assertEqual(tracked.returncode, 0, tracked.stderr)
        ignored = subprocess.run(
            [
                "git",
                "--no-optional-locks",
                "-c",
                "core.excludesFile=",
                "check-ignore",
                "--quiet",
                "--no-index",
                "--",
                self.EXEMPT_ENV_NAME,
            ],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        self.assertNotEqual(ignored.returncode, 0, "the template must not be ignored")


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
