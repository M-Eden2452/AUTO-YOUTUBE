"""Owning module for current-routing integrity and Git-aware docs freshness.

Класс по ``PROJECT_EXECUTION_PLAN.md`` этому модулю **не** присвоен по той же
причине, что и ``tests/test_check_agent_docs.py``: current governance
классифицирует конкретный закрытый перечень test-модулей
(``CLEANUP_REGISTRY.md``, «Accidental invariants»), и новый модуль в него не
входит.

Protects (PLAN-STAB-7, current-routing и reference integrity):
- ровно один authoritative current checkpoint; три routing mirror-документа не
  могут молча разойтись с ``current_checkpoint`` активного execution plan;
- конкурирующее актуальное утверждение распознаётся по узким маркерам
  «текущий/current checkpoint» и «текущий/current шаг|step», а историческая
  фраза («предыдущий checkpoint — … закрыт») текущим утверждением не считается;
- ``next_exact_action`` не может ссылаться на несуществующий PLAN-ID и обязан
  называть текущий checkpoint;
- completed шаг не может быть объявлен текущим checkpoint, причём статус
  читается по той же prose-модели, что и остальные парсеры: heading или
  status-строка внутри fenced block либо цитаты разделом документа не является.

Protects (PLAN-STAB-8, Git-aware documentation freshness):
- ``last_verified_commit`` и ``baseline_head`` проверяются по фактическому Git,
  а не только по hex-форме: несуществующий commit и commit вне истории HEAD —
  ошибки с разными сообщениями;
- расхождение объявленных ``source_paths`` после baseline сообщается как
  advisory и не делает дерево красным (массовая правка ``last_verified_*``
  запрещена контрактом PLAN-STAB-8);
- отсутствие Git и shallow clone обрабатываются fail-closed.

Does not prove:
- что содержание документов верно по существу: проверяется разрешимость
  routing-полей и соответствие метаданных Git, а не смысл утверждений;
- что каждая PLAN-ID-ссылка в плане разрешается. Общая resolution-проверка дала
  бы ложную красную базу: сабы вида ``PLAN-12B`` определяются жирными буллитами
  внутри родительских разделов. Проверяются только routing-поля.
"""

from __future__ import annotations

import os
import subprocess
import unittest
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

from tools.qa import check_agent_docs
from tools.qa.check_agent_docs import (
    validate_freshness,
    validate_repository,
    validate_routing,
)


REPO_ROOT = Path(__file__).resolve().parents[1]

EXECUTION_PLAN = Path("docs/current/PROJECT_EXECUTION_PLAN.md")
START_HERE = Path("docs/current/START_HERE.md")
CURRENT_STATE = Path("docs/current/CURRENT_STATE.md")
SYSTEM_MAP = Path("docs/current/SYSTEM_MAP.md")


def _write(root: Path, relative: Path, text: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


# --- synthetic Git fixtures ------------------------------------------------
#
# Every synthetic repository is fully local: `git init` and `git commit` never
# touch the network, and system/global Git configuration is disabled so a
# developer machine cannot change the outcome.


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


def _git(root: Path, *args: str, env: dict[str, str]) -> str:
    completed = subprocess.run(
        ["git", "--no-optional-locks", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    return completed.stdout.strip()


class _SyntheticRepository:
    """A local Git repository built commit by commit inside a temp directory."""

    def __init__(self, root: Path, home: Path) -> None:
        self.root = root
        self.env = _git_env(home)
        _git(root, "init", "--initial-branch=main", env=self.env)

    def commit(self, message: str, *, stamp: str = "2026-08-06T12:00:00+00:00") -> str:
        env = {**self.env, "GIT_AUTHOR_DATE": stamp, "GIT_COMMITTER_DATE": stamp}
        _git(self.root, "add", "--all", env=env)
        _git(self.root, "commit", "--no-gpg-sign", "-m", message, env=env)
        return _git(self.root, "rev-parse", "HEAD", env=self.env)

    def run(self, *args: str) -> str:
        return _git(self.root, *args, env=self.env)


REGISTRY_TEMPLATE = """---
status: current
last_verified_commit: {commit}
last_verified_date: 2026-08-01
source_paths:
  - src/tracked.py
---

# Cleanup Registry
"""


class FreshnessTests(unittest.TestCase):
    """PLAN-STAB-8: freshness is decided by Git, not by a decorative hex string."""

    def setUp(self) -> None:
        self.stack = TemporaryDirectory()
        self.addCleanup(self.stack.cleanup)
        home = Path(self.stack.name) / "home"
        home.mkdir()
        self.root = Path(self.stack.name) / "repo"
        self.root.mkdir()
        self.repo = _SyntheticRepository(self.root, home)
        _write(self.root, Path("src/tracked.py"), "VALUE = 1\n")
        _write(self.root, check_agent_docs.CLEANUP_REGISTRY_DOC, REGISTRY_TEMPLATE.format(commit="0" * 40))
        self.baseline = self.repo.commit("baseline")

    def _registry(self, commit: str) -> None:
        _write(
            self.root,
            check_agent_docs.CLEANUP_REGISTRY_DOC,
            REGISTRY_TEMPLATE.format(commit=commit),
        )

    def _name(self) -> str:
        return check_agent_docs.CLEANUP_REGISTRY_DOC.as_posix()

    def test_ancestor_commit_produces_no_errors(self) -> None:
        self._registry(self.baseline[:7])
        _write(self.root, Path("docs/unrelated.md"), "text\n")
        self.repo.commit("later work")
        self.assertEqual(validate_freshness(self.root), [])

    def test_commit_that_does_not_exist_is_reported(self) -> None:
        self._registry("0123456789abcdef0123456789abcdef01234567")
        self.repo.commit("record an unknown commit")
        errors = validate_freshness(self.root)
        self.assertEqual(len(errors), 1, errors)
        self.assertIn(f"{self._name()}: last_verified_commit", errors[0])
        self.assertIn("is not a commit in this repository", errors[0])

    def test_malformed_commit_is_reported_separately_from_a_missing_one(self) -> None:
        self._registry("not-a-commit")
        self.repo.commit("record a malformed commit")
        errors = validate_freshness(self.root)
        self.assertEqual(len(errors), 1, errors)
        self.assertIn("is not a Git commit id", errors[0])
        self.assertNotIn("is not a commit in this repository", errors[0])

    def test_commit_outside_head_history_is_reported(self) -> None:
        self.repo.run("checkout", "-b", "side")
        _write(self.root, Path("src/tracked.py"), "VALUE = 2\n")
        side = self.repo.commit("side work")
        self.repo.run("checkout", "main")
        self._registry(side)
        self.repo.commit("record a non-ancestor commit")
        errors = validate_freshness(self.root)
        self.assertEqual(len(errors), 1, errors)
        self.assertIn("is not an ancestor of HEAD", errors[0])

    def test_source_path_drift_is_an_advisory_not_an_error(self) -> None:
        self._registry(self.baseline)
        _write(self.root, Path("src/tracked.py"), "VALUE = 2\n")
        self.repo.commit("change a declared source path")
        advisories: list[str] = []
        self.assertEqual(validate_freshness(self.root, advisories=advisories), [])
        self.assertEqual(len(advisories), 1, advisories)
        self.assertIn(self._name(), advisories[0])
        self.assertIn("source_paths", advisories[0])
        self.assertIn("src/tracked.py", advisories[0])

    def test_unchanged_source_paths_produce_no_advisory(self) -> None:
        self._registry(self.baseline)
        _write(self.root, Path("docs/unrelated.md"), "text\n")
        self.repo.commit("change nothing declared")
        advisories: list[str] = []
        self.assertEqual(validate_freshness(self.root, advisories=advisories), [])
        self.assertEqual(advisories, [])

    def test_missing_git_repository_fails_closed(self) -> None:
        outside = Path(self.stack.name) / "export"
        outside.mkdir()
        _write(outside, check_agent_docs.CLEANUP_REGISTRY_DOC, REGISTRY_TEMPLATE.format(commit=self.baseline))
        errors = validate_freshness(outside)
        self.assertEqual(len(errors), 1, errors)
        self.assertIn("not a readable Git repository", errors[0])

    def test_shallow_clone_fails_closed(self) -> None:
        self._registry(self.baseline)
        self.repo.commit("second commit so a depth-1 clone truncates history")
        clone = Path(self.stack.name) / "shallow"
        _git(
            Path(self.stack.name),
            "clone",
            "--depth=1",
            "--branch=main",
            self.root.as_uri(),
            str(clone),
            env=self.repo.env,
        )
        errors = validate_freshness(clone)
        self.assertTrue(errors, "a shallow clone must not silently pass")
        self.assertTrue(
            any("shallow" in error for error in errors),
            errors,
        )

    def test_error_message_names_the_document_and_the_field(self) -> None:
        self._registry("0123456789abcdef0123456789abcdef01234567")
        self.repo.commit("record an unknown commit")
        errors = validate_freshness(self.root)
        self.assertTrue(errors[0].startswith(f"{self._name()}: last_verified_commit"), errors)


# --- routing ---------------------------------------------------------------

PLAN_TEMPLATE = """---
status: active
plan_revision: 2.1
created_at: 2026-07-30
updated_at: 2026-08-06
baseline_head: 84bdd8b4f64c7adaf7582bdb39b15b18163253fb
working_branch: governance-reset
current_checkpoint: {checkpoint}
next_exact_action: {action}
source_paths:
  - AGENTS.md
---

# Execution Plan

## Current checkpoint

- **Текущий шаг:** **PLAN-STAB-7**.

#### PLAN-STAB-7 — current-routing и reference integrity
{prelude}
- **status:** {status_seven}
- **цель:** routing не расходится.

#### PLAN-STAB-8 — Git-aware documentation freshness

- **status:** {status_eight}
- **цель:** freshness проверяется по Git.

#### PLAN-STAB-9 — shared rights vocabulary owner

- **status:** completed 2026-08-06 (commit `ed4604d`) · **зависимости:** —.
- **цель:** один владелец словаря.
"""

MIRROR_TEMPLATE = """---
status: current
last_verified_commit: 9f3ddba
last_verified_date: 2026-07-29
source_paths:
  - AGENTS.md
---

# Mirror

Текущий checkpoint — **{checkpoint}**: подробности в плане.
"""

DEFAULT_ACTION = (
    "coordinated bounded implementation covering PLAN-STAB-7 and PLAN-STAB-8"
)

# Разметка, показанная как пример, а не как структура самого документа: heading
# и status-строка внутри fenced block и внутри цитаты.
FENCED_HEADING_PRELUDE = """
```markdown
#### PLAN-STAB-99 — heading, показанный как пример разметки

- **status:** completed 2026-01-01
```
"""

FENCED_STATUS_PRELUDE = """
```markdown
- **status:** completed 2026-01-01
```
"""

QUOTED_HEADING_PRELUDE = """
> Цитата из архивного плана:
>
> #### PLAN-STAB-99 — heading внутри цитаты
>
> - **status:** completed 2026-01-01
"""

PENDING_STATUS_SEVEN = "pending / not started. Completed слайс не объявляется."


class RoutingTests(unittest.TestCase):
    """PLAN-STAB-7: one authoritative checkpoint, mirrors that cannot drift."""

    def setUp(self) -> None:
        self.stack = TemporaryDirectory()
        self.addCleanup(self.stack.cleanup)
        self.root = Path(self.stack.name)
        _write(self.root, Path("AGENTS.md"), "# Agents\n")
        self._plan()
        for mirror in (START_HERE, CURRENT_STATE, SYSTEM_MAP):
            self._mirror(mirror, "PLAN-STAB-7")

    def _plan(
        self,
        *,
        checkpoint: str = "PLAN-STAB-7",
        action: str = DEFAULT_ACTION,
        status_seven: str = PENDING_STATUS_SEVEN,
        status_eight: str = "pending / not started",
        prelude: str = "",
    ) -> None:
        _write(
            self.root,
            EXECUTION_PLAN,
            PLAN_TEMPLATE.format(
                checkpoint=checkpoint,
                action=action,
                status_seven=status_seven,
                status_eight=status_eight,
                prelude=prelude,
            ),
        )

    def _mirror(self, relative: Path, checkpoint: str, *, extra: str = "") -> None:
        text = MIRROR_TEMPLATE.format(checkpoint=checkpoint)
        if extra:
            text = f"{text}\n{extra}\n"
        _write(self.root, relative, text)

    def test_consistent_routing_produces_no_errors(self) -> None:
        self.assertEqual(validate_routing(self.root), [])

    def test_coordinated_route_keeps_two_separate_plan_ids(self) -> None:
        self.assertEqual(validate_routing(self.root), [])
        plan = (self.root / EXECUTION_PLAN).read_text(encoding="utf-8")
        defined = {
            identifier
            for kind, identifier in check_agent_docs._identifier_definitions(plan)
            if kind == "plan step"
        }
        self.assertIn("PLAN-STAB-7", defined)
        self.assertIn("PLAN-STAB-8", defined)
        self.assertNotIn("PLAN-STAB-7+8", defined)

    def test_checkpoint_without_a_step_definition_is_reported(self) -> None:
        self._plan(checkpoint="PLAN-STAB-42", action="finish PLAN-STAB-42")
        errors = validate_routing(self.root)
        self.assertTrue(
            any("PLAN-STAB-42" in error for error in errors), errors
        )

    def test_start_here_naming_another_checkpoint_is_reported(self) -> None:
        self._mirror(START_HERE, "PLAN-STAB-9")
        errors = validate_routing(self.root)
        self.assertEqual(len(errors), 1, errors)
        self.assertIn(START_HERE.as_posix(), errors[0])
        self.assertIn("PLAN-STAB-9", errors[0])
        self.assertIn("PLAN-STAB-7", errors[0])

    def test_current_state_naming_a_closed_checkpoint_is_reported(self) -> None:
        self._mirror(CURRENT_STATE, "PLAN-STAB-9")
        errors = validate_routing(self.root)
        self.assertTrue(
            any(CURRENT_STATE.as_posix() in error for error in errors), errors
        )

    def test_system_map_naming_a_closed_checkpoint_is_reported(self) -> None:
        self._mirror(SYSTEM_MAP, "PLAN-STAB-9")
        errors = validate_routing(self.root)
        self.assertTrue(
            any(SYSTEM_MAP.as_posix() in error for error in errors), errors
        )

    def test_mirror_without_any_checkpoint_statement_is_reported(self) -> None:
        _write(
            self.root,
            SYSTEM_MAP,
            MIRROR_TEMPLATE.format(checkpoint="PLAN-STAB-7").replace(
                "Текущий checkpoint — **PLAN-STAB-7**: подробности в плане.",
                "Карта без routing-указателя.",
            ),
        )
        errors = validate_routing(self.root)
        self.assertTrue(
            any("no current-checkpoint statement" in error for error in errors), errors
        )

    # --- narrow current markers -------------------------------------------
    #
    # Расхождение читается новым агентом как «два текущих задания», поэтому
    # конкурирующее утверждение обязано находиться независимо от того, каким
    # существительным оно записано. И ровно поэтому же историческая фраза
    # текущим утверждением быть не должна.

    def test_competing_current_step_statement_is_reported(self) -> None:
        self._mirror(START_HERE, "PLAN-STAB-7", extra="Текущий шаг — PLAN-STAB-6.")
        errors = validate_routing(self.root)
        self.assertEqual(len(errors), 1, errors)
        self.assertIn(START_HERE.as_posix(), errors[0])
        self.assertIn("PLAN-STAB-6", errors[0])
        self.assertIn("PLAN-STAB-7", errors[0])

    def test_competing_english_current_step_statement_is_reported(self) -> None:
        self._mirror(CURRENT_STATE, "PLAN-STAB-7", extra="Current step — PLAN-STAB-6.")
        errors = validate_routing(self.root)
        self.assertEqual(len(errors), 1, errors)
        self.assertIn(CURRENT_STATE.as_posix(), errors[0])
        self.assertIn("PLAN-STAB-6", errors[0])
        self.assertIn("PLAN-STAB-7", errors[0])

    def test_previous_checkpoint_sentence_is_not_a_current_statement(self) -> None:
        self._mirror(
            SYSTEM_MAP,
            "PLAN-STAB-7",
            extra="Предыдущий checkpoint — PLAN-STAB-9 закрыт.",
        )
        self.assertEqual(validate_routing(self.root), [])

    def test_a_historical_statement_alone_is_still_a_missing_current_statement(
        self,
    ) -> None:
        _write(
            self.root,
            SYSTEM_MAP,
            MIRROR_TEMPLATE.format(checkpoint="PLAN-STAB-7").replace(
                "Текущий checkpoint — **PLAN-STAB-7**: подробности в плане.",
                "Предыдущий checkpoint — PLAN-STAB-9 закрыт.",
            ),
        )
        errors = validate_routing(self.root)
        self.assertTrue(
            any("no current-checkpoint statement" in error for error in errors), errors
        )

    def test_two_agreeing_current_statements_are_not_a_conflict(self) -> None:
        self._mirror(START_HERE, "PLAN-STAB-7", extra="Текущий шаг — PLAN-STAB-7.")
        self.assertEqual(validate_routing(self.root), [])

    # --- status parsing ----------------------------------------------------
    #
    # Разметка, показанная как пример, разделом документа не является: иначе
    # пример обрывает поиск и настоящий статус настоящего шага не находится.

    def test_a_heading_inside_a_fenced_block_does_not_end_the_status_search(
        self,
    ) -> None:
        self._plan(prelude=FENCED_HEADING_PRELUDE)
        plan = (self.root / EXECUTION_PLAN).read_text(encoding="utf-8")
        self.assertEqual(
            check_agent_docs._step_status(plan, "PLAN-STAB-7"), PENDING_STATUS_SEVEN
        )
        self.assertEqual(validate_routing(self.root), [])

    def test_a_status_line_inside_a_fenced_block_is_not_the_step_status(self) -> None:
        self._plan(prelude=FENCED_STATUS_PRELUDE)
        plan = (self.root / EXECUTION_PLAN).read_text(encoding="utf-8")
        self.assertEqual(
            check_agent_docs._step_status(plan, "PLAN-STAB-7"), PENDING_STATUS_SEVEN
        )
        self.assertEqual(validate_routing(self.root), [])

    def test_a_quoted_example_heading_does_not_end_the_status_search(self) -> None:
        self._plan(prelude=QUOTED_HEADING_PRELUDE)
        plan = (self.root / EXECUTION_PLAN).read_text(encoding="utf-8")
        self.assertEqual(
            check_agent_docs._step_status(plan, "PLAN-STAB-7"), PENDING_STATUS_SEVEN
        )
        self.assertEqual(validate_routing(self.root), [])

    def test_a_real_next_heading_still_ends_the_status_search(self) -> None:
        self._plan(status_eight="completed 2026-01-01 (commit `abc1234`)")
        path = self.root / EXECUTION_PLAN
        plan = "".join(
            f"{line}\n"
            for line in path.read_text(encoding="utf-8").splitlines()
            if line != f"- **status:** {PENDING_STATUS_SEVEN}"
        )
        path.write_text(plan, encoding="utf-8")
        self.assertIsNone(check_agent_docs._step_status(plan, "PLAN-STAB-7"))
        errors = validate_routing(self.root)
        self.assertTrue(
            any("has no status line" in error for error in errors), errors
        )

    def test_next_exact_action_pointing_at_an_unknown_step_is_reported(self) -> None:
        self._plan(action="finish PLAN-STAB-7 and then PLAN-STAB-99")
        errors = validate_routing(self.root)
        self.assertTrue(
            any("PLAN-STAB-99" in error for error in errors), errors
        )

    def test_next_exact_action_that_forgets_the_checkpoint_is_reported(self) -> None:
        self._plan(action="review PLAN-STAB-9 and move on")
        errors = validate_routing(self.root)
        self.assertTrue(
            any("does not name current_checkpoint" in error for error in errors), errors
        )

    def test_next_exact_action_that_grew_into_a_journal_is_reported(self) -> None:
        """The field is a pointer. Length is the only thing that says so.

        Its two neighbours above check that the action names a defined step and
        the current checkpoint - both of which a 143-line closure journal
        satisfies perfectly, which is how the real field reached 10 832
        characters without a single complaint.
        """
        self._plan(
            action=(
                "finish PLAN-STAB-7. " + "Closed earlier and recorded here. " * 20
            )
        )
        errors = validate_routing(self.root)
        self.assertTrue(
            any("is a pointer, not a journal" in error for error in errors), errors
        )

    def test_an_action_at_the_limit_is_still_accepted(self) -> None:
        """The guard refuses a journal, not a sentence that happens to be long."""
        action = "finish PLAN-STAB-7. " + "x" * (
            check_agent_docs.NEXT_EXACT_ACTION_MAX_CHARS - len("finish PLAN-STAB-7. ")
        )
        self.assertEqual(len(action), check_agent_docs.NEXT_EXACT_ACTION_MAX_CHARS)
        self._plan(action=action)
        self.assertEqual(validate_routing(self.root), [])

    def test_completed_step_cannot_be_the_current_checkpoint(self) -> None:
        self._plan(
            checkpoint="PLAN-STAB-9",
            action="review PLAN-STAB-9",
        )
        for mirror in (START_HERE, CURRENT_STATE, SYSTEM_MAP):
            self._mirror(mirror, "PLAN-STAB-9")
        errors = validate_routing(self.root)
        self.assertTrue(
            any("is completed and cannot be the current checkpoint" in e for e in errors),
            errors,
        )

    def test_pending_status_that_merely_mentions_completed_is_accepted(self) -> None:
        self._plan(
            status_seven=(
                "pending / not started. Factual routing repair выполнен ранее; "
                "completed слайс не объявляется."
            )
        )
        self.assertEqual(validate_routing(self.root), [])


class RepositoryRoutingAndFreshnessTests(unittest.TestCase):
    """The real repository satisfies both contracts without a frozen constant."""

    def test_repository_routing_is_consistent(self) -> None:
        self.assertEqual(validate_routing(REPO_ROOT), [])

    def test_repository_freshness_is_git_verified(self) -> None:
        self.assertEqual(validate_freshness(REPO_ROOT), [])

    def test_repository_passes_without_a_frozen_verification_date(self) -> None:
        self.assertEqual(validate_repository(REPO_ROOT), [])

    def test_calendar_age_reference_comes_from_the_head_commit(self) -> None:
        head_date = check_agent_docs._head_commit_date(REPO_ROOT)
        self.assertIsInstance(head_date, date)
        self.assertEqual(check_agent_docs._reference_date(REPO_ROOT), head_date)

    def test_validation_does_not_touch_the_working_tree(self) -> None:
        before = subprocess.run(
            ["git", "--no-optional-locks", "status", "--porcelain"],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        ).stdout
        validate_repository(REPO_ROOT)
        after = subprocess.run(
            ["git", "--no-optional-locks", "status", "--porcelain"],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        ).stdout
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
