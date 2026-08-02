"""Targeted owner of ``tools.qa.check_agent_docs``.

Класс по ``PROJECT_EXECUTION_PLAN.md`` этому модулю **не** присвоен: current
governance классифицирует конкретный перечень существующих test-модулей
(``CLEANUP_REGISTRY.md``, «Accidental invariants»), и новый модуль в него не
входит. Ставить себе label здесь означало бы записать недоказанное решение.

Protects:
- каждая documentation-governance проверка обязана падать без своей реализации
  и не падать на корректном входе. Positive и negative случаи изолированы во
  временных каталогах, чтобы проверка не зависела от текущего состояния
  репозитория, сети, времени и пользовательских данных.

Does not prove:
- что документация содержательно верна: проверяется существование цели, форма
  метаданных и уникальность определений, а не смысл утверждений;
- что покрыты все классы идентификаторов. PLAN-ID проверяется только на
  уникальность определений и на разрешимость ``current_checkpoint``: сабы вида
  ``PLAN-12B`` определяются жирными буллитами внутри родительских разделов, и
  общая resolution-проверка дала бы ложную красную базу.
"""

from __future__ import annotations

import unittest
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

from tools.qa import check_agent_docs
from tools.qa.check_agent_docs import (
    validate_adr_references,
    validate_code_documentation,
    validate_governance_documents,
    validate_identifier_definitions,
    validate_implementation_index,
    validate_repository,
    validate_section_references,
    validate_skills,
    validate_test_classification,
)


REPO_ROOT = Path(__file__).resolve().parents[1]

PRODUCT_PLAN = Path("docs/current/PRODUCT_PLAN.md")
EXECUTION_PLAN = Path("docs/current/PROJECT_EXECUTION_PLAN.md")
CLEANUP_REGISTRY = Path("docs/current/CLEANUP_REGISTRY.md")
IMPLEMENTATION_INDEX = Path("docs/implementation/README.md")
SYSTEM_MAP = Path("docs/current/SYSTEM_MAP.md")

PRODUCT_PLAN_FRONTMATTER = """---
status: active_product_plan
product_plan_revision: 1.1
updated: 2026-08-01
working_branch: governance-reset
authority: owner_approved_product_direction
execution_source_of_truth: docs/current/PROJECT_EXECUTION_PLAN.md
---
"""

EXECUTION_PLAN_FRONTMATTER = """---
status: active
plan_revision: 2.1
created_at: 2026-07-30
updated_at: 2026-08-02
baseline_head: 84bdd8b4f64c7adaf7582bdb39b15b18163253fb
working_branch: governance-reset
current_checkpoint: PLAN-9B-4
next_exact_action: git status --short --branch
source_paths:
  - AGENTS.md
---
"""

REGISTRY_FRONTMATTER = """---
status: current
last_verified_commit: affa138
last_verified_date: 2026-08-01
source_paths:
  - AGENTS.md
---
"""

EXECUTION_PLAN_BODY = """
# Execution Plan

### PLAN-9B — input/query truth (bounded family)

#### PLAN-9B-4 — truthful source/script behavior

Body.
"""


def _write(root: Path, relative: Path, text: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _governance_root(stack: TemporaryDirectory) -> Path:
    """A minimal root where every governance document is valid."""

    root = Path(stack.name)
    _write(root, Path("AGENTS.md"), "# Agents\n")
    _write(root, PRODUCT_PLAN, PRODUCT_PLAN_FRONTMATTER + "\n# Product Plan\n")
    _write(root, EXECUTION_PLAN, EXECUTION_PLAN_FRONTMATTER + EXECUTION_PLAN_BODY)
    _write(root, CLEANUP_REGISTRY, REGISTRY_FRONTMATTER + "\n# Cleanup Registry\n")
    return root


def _review_skill_root(stack: TemporaryDirectory) -> Path:
    """A minimal root containing a valid canonical reviewer and both adapters."""

    root = Path(stack.name)
    _write(
        root,
        Path("skills/review-change/SKILL.md"),
        """---
name: review-change
description: Independently review an immutable commit or explicit diff without mutation.
---

# Review Change

## Purpose

Review one explicit change object.
Launch with `GIT_OPTIONAL_LOCKS=0`; use `git --no-optional-locks` for Git reads.
""",
    )
    _write(
        root,
        Path("skills/review-change/agents/openai.yaml"),
        """interface:
  display_name: "Review Change"
  short_description: "Review one explicit change without mutation"
  default_prompt: "Use $review-change to review an explicit immutable change."
""",
    )
    _write(
        root,
        Path(".claude/agents/review-change.md"),
        """---
name: review-change
description: Review one explicit immutable commit or diff in an independent context.
model: sonnet
color: blue
permissionMode: plan
tools: [Read, Glob, Grep, Bash]
---

Use `skills/review-change/SKILL.md` as the only review policy.
Set `GIT_OPTIONAL_LOCKS=0` and use `git --no-optional-locks` for every Git command.
Do not fix findings, stage files, or create commits.
""",
    )
    return root


class RepositoryTests(unittest.TestCase):
    def test_repository_passes_every_governance_check(self) -> None:
        self.assertEqual(
            validate_repository(REPO_ROOT, today=date(2026, 7, 29), max_age_days=120),
            [],
        )


class SkillContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.stack = TemporaryDirectory()
        self.addCleanup(self.stack.cleanup)
        self.root = _review_skill_root(self.stack)

    def test_valid_review_change_contract_produces_no_errors(self) -> None:
        self.assertEqual(
            validate_skills(self.root, required_skills=("review-change",)), []
        )

    def test_missing_claude_adapter_is_reported(self) -> None:
        (self.root / ".claude/agents/review-change.md").unlink()
        errors = validate_skills(self.root, required_skills=("review-change",))
        self.assertIn("review-change: missing .claude/agents/review-change.md", errors)

    def test_write_or_edit_capability_is_reported(self) -> None:
        adapter = self.root / ".claude/agents/review-change.md"
        adapter.write_text(
            adapter.read_text(encoding="utf-8").replace(
                "tools: [Read, Glob, Grep, Bash]",
                "tools: [Read, Glob, Grep, Bash, Write, Edit]",
            ),
            encoding="utf-8",
        )
        errors = validate_skills(self.root, required_skills=("review-change",))
        self.assertIn(
            "review-change: Claude adapter tools must be exactly "
            "Bash, Glob, Grep, Read (found Bash, Edit, Glob, Grep, Read, Write)",
            errors,
        )

    def test_missing_canonical_policy_pointer_is_reported(self) -> None:
        adapter = self.root / ".claude/agents/review-change.md"
        adapter.write_text(
            adapter.read_text(encoding="utf-8").replace(
                "Use `skills/review-change/SKILL.md` as the only review policy.",
                "Apply the review policy embedded here.",
            ),
            encoding="utf-8",
        )
        errors = validate_skills(self.root, required_skills=("review-change",))
        self.assertIn(
            "review-change: Claude adapter must point to "
            "skills/review-change/SKILL.md",
            errors,
        )

    def test_duplicated_policy_sections_are_reported(self) -> None:
        adapter = self.root / ".claude/agents/review-change.md"
        adapter.write_text(
            adapter.read_text(encoding="utf-8")
            + "\n## Review dimensions\nCopied policy.\n## Findings format\nCopied policy.\n",
            encoding="utf-8",
        )
        errors = validate_skills(self.root, required_skills=("review-change",))
        self.assertIn(
            "review-change: Claude adapter duplicates canonical policy sections: "
            "Findings format, Review dimensions",
            errors,
        )

    def test_missing_no_optional_locks_contract_is_reported(self) -> None:
        adapter = self.root / ".claude/agents/review-change.md"
        adapter.write_text(
            adapter.read_text(encoding="utf-8").replace(
                "Set `GIT_OPTIONAL_LOCKS=0` and use `git --no-optional-locks` "
                "for every Git command.\n",
                "",
            ),
            encoding="utf-8",
        )
        errors = validate_skills(self.root, required_skills=("review-change",))
        self.assertIn(
            "review-change: Claude adapter must disable optional Git locks", errors
        )

    def test_canonical_policy_must_disable_optional_locks(self) -> None:
        skill = self.root / "skills/review-change/SKILL.md"
        skill.write_text(
            skill.read_text(encoding="utf-8").replace(
                "Launch with `GIT_OPTIONAL_LOCKS=0`; use `git --no-optional-locks` "
                "for Git reads.\n",
                "Use read-only Git commands.\n",
            ),
            encoding="utf-8",
        )
        errors = validate_skills(self.root, required_skills=("review-change",))
        self.assertIn(
            "review-change: canonical skill must disable optional Git locks", errors
        )


class GovernanceDocumentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.stack = TemporaryDirectory()
        self.addCleanup(self.stack.cleanup)
        self.root = _governance_root(self.stack)

    def test_valid_governance_documents_produce_no_errors(self) -> None:
        self.assertEqual(validate_governance_documents(self.root), [])

    def test_missing_required_current_document_is_reported(self) -> None:
        (self.root / PRODUCT_PLAN).unlink()
        errors = validate_governance_documents(self.root)
        self.assertIn(f"missing current document: {PRODUCT_PLAN.as_posix()}", errors)

    def test_malformed_status_is_reported(self) -> None:
        _write(
            self.root,
            PRODUCT_PLAN,
            PRODUCT_PLAN_FRONTMATTER.replace(
                "status: active_product_plan", "status: draft"
            )
            + "\n# Product Plan\n",
        )
        errors = validate_governance_documents(self.root)
        self.assertIn(
            f"{PRODUCT_PLAN.as_posix()}: status must be active_product_plan", errors
        )

    def test_missing_frontmatter_is_reported_without_crashing(self) -> None:
        _write(self.root, CLEANUP_REGISTRY, "# Cleanup Registry\n")
        errors = validate_governance_documents(self.root)
        self.assertTrue(
            any("missing YAML frontmatter" in error for error in errors), errors
        )

    def test_invalid_baseline_head_is_reported(self) -> None:
        _write(
            self.root,
            EXECUTION_PLAN,
            EXECUTION_PLAN_FRONTMATTER.replace(
                "baseline_head: 84bdd8b4f64c7adaf7582bdb39b15b18163253fb",
                "baseline_head: not-a-commit",
            )
            + EXECUTION_PLAN_BODY,
        )
        errors = validate_governance_documents(self.root)
        self.assertIn(f"{EXECUTION_PLAN.as_posix()}: invalid baseline_head", errors)

    def test_missing_source_path_is_reported(self) -> None:
        _write(
            self.root,
            CLEANUP_REGISTRY,
            REGISTRY_FRONTMATTER.replace("  - AGENTS.md", "  - does/not/exist.md")
            + "\n# Cleanup Registry\n",
        )
        errors = validate_governance_documents(self.root)
        self.assertIn(
            f"{CLEANUP_REGISTRY.as_posix()}: missing source_path does/not/exist.md",
            errors,
        )

    def test_pointer_field_must_resolve(self) -> None:
        _write(
            self.root,
            PRODUCT_PLAN,
            PRODUCT_PLAN_FRONTMATTER.replace(
                "execution_source_of_truth: docs/current/PROJECT_EXECUTION_PLAN.md",
                "execution_source_of_truth: docs/current/GONE.md",
            )
            + "\n# Product Plan\n",
        )
        errors = validate_governance_documents(self.root)
        self.assertIn(
            f"{PRODUCT_PLAN.as_posix()}: execution_source_of_truth points at "
            "missing path docs/current/GONE.md",
            errors,
        )

    def test_empty_checkpoint_is_reported(self) -> None:
        _write(
            self.root,
            EXECUTION_PLAN,
            EXECUTION_PLAN_FRONTMATTER.replace(
                "current_checkpoint: PLAN-9B-4", 'current_checkpoint: ""'
            )
            + EXECUTION_PLAN_BODY,
        )
        errors = validate_governance_documents(self.root)
        self.assertIn(
            f"{EXECUTION_PLAN.as_posix()}: current_checkpoint must be a non-empty value",
            errors,
        )

    def test_ambiguous_checkpoint_is_reported(self) -> None:
        _write(
            self.root,
            EXECUTION_PLAN,
            EXECUTION_PLAN_FRONTMATTER.replace(
                "current_checkpoint: PLAN-9B-4",
                'current_checkpoint: "PLAN-9B-4 or PLAN-9B-2"',
            )
            + EXECUTION_PLAN_BODY,
        )
        errors = validate_governance_documents(self.root)
        self.assertTrue(
            any("is not an unambiguous plan identifier" in e for e in errors), errors
        )

    def test_checkpoint_without_step_definition_is_reported(self) -> None:
        _write(
            self.root,
            EXECUTION_PLAN,
            EXECUTION_PLAN_FRONTMATTER.replace(
                "current_checkpoint: PLAN-9B-4", "current_checkpoint: PLAN-42"
            )
            + EXECUTION_PLAN_BODY,
        )
        errors = validate_governance_documents(self.root)
        self.assertIn(
            f"{EXECUTION_PLAN.as_posix()}: current_checkpoint PLAN-42 has no step "
            "definition in this document",
            errors,
        )


class LinkTests(unittest.TestCase):
    def setUp(self) -> None:
        self.stack = TemporaryDirectory()
        self.addCleanup(self.stack.cleanup)
        self.root = Path(self.stack.name)

    def test_valid_local_link_resolves(self) -> None:
        _write(self.root, Path("docs/current/OTHER.md"), "# Other\n")
        document = _write(
            self.root, Path("docs/current/A.md"), "See [other](OTHER.md).\n"
        )
        broken = [
            target
            for target in check_agent_docs._local_links(document)
            if not target.exists()
        ]
        self.assertEqual(broken, [])

    def test_broken_local_link_is_detected(self) -> None:
        document = _write(
            self.root, Path("docs/current/A.md"), "See [gone](GONE.md).\n"
        )
        broken = [
            target
            for target in check_agent_docs._local_links(document)
            if not target.exists()
        ]
        self.assertEqual(len(broken), 1)

    def test_historical_audits_are_outside_the_strict_current_scope(self) -> None:
        _write(self.root, Path("AGENTS.md"), "# Agents\n")
        _write(
            self.root,
            Path("docs/audits/OLD_AUDIT.md"),
            "Historical [link](/docs/current/GONE.md) kept as written.\n",
        )
        _write(
            self.root,
            Path("docs/implementation/legacy_stage/REPORT.md"),
            "Historical [link](/src/gone.py) kept as written.\n",
        )
        scoped = {
            path.relative_to(self.root).as_posix()
            for path in check_agent_docs._strict_current_documents(self.root)
        }
        self.assertNotIn("docs/audits/OLD_AUDIT.md", scoped)
        self.assertNotIn("docs/implementation/legacy_stage/REPORT.md", scoped)


class SectionReferenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.stack = TemporaryDirectory()
        self.addCleanup(self.stack.cleanup)
        self.root = Path(self.stack.name)
        _write(self.root, EXECUTION_PLAN, "# Plan\n")
        _write(self.root, CLEANUP_REGISTRY, "# Registry\n")

    def _product_plan(self, body: str) -> None:
        _write(self.root, PRODUCT_PLAN, body)

    def test_existing_section_reference_passes(self) -> None:
        self._product_plan(
            "## 13. Legacy knowledge\n\n## 14. Boundary\n\n"
            "Вне scope (раздел 14).\n"
            "по порядку раздела 14\n"
            "| cell | раздел 14 |\n"
        )
        self.assertEqual(validate_section_references(self.root), [])

    def test_missing_section_reference_is_reported(self) -> None:
        self._product_plan("## 14. Boundary\n\nСмотри раздел 21.\n")
        errors = validate_section_references(self.root)
        self.assertEqual(
            errors,
            [f"{PRODUCT_PLAN.as_posix()}:3: reference to missing section 21"],
        )

    def test_nested_section_reference_resolves(self) -> None:
        self._product_plan("## 19. Motion\n\n### 19.7. Pairing\n\nСм. раздел 19.7.\n")
        self.assertEqual(validate_section_references(self.root), [])

    def test_reference_inside_a_code_fence_is_ignored(self) -> None:
        self._product_plan(
            "## 1. Purpose\n\n```text\nсм. раздел 99\n```\n\nОбычный текст.\n"
        )
        self.assertEqual(validate_section_references(self.root), [])

    def test_reference_inside_a_quote_is_ignored(self) -> None:
        self._product_plan("## 1. Purpose\n\n> цитата: см. раздел 99\n")
        self.assertEqual(validate_section_references(self.root), [])

    def test_reference_inside_inline_code_is_ignored(self) -> None:
        self._product_plan("## 1. Purpose\n\nПример: `см. раздел 99`.\n")
        self.assertEqual(validate_section_references(self.root), [])

    def test_reference_qualified_by_another_document_is_ignored(self) -> None:
        self._product_plan(
            "## 1. Purpose\n\nПолная формулировка — `OTHER_PLAN.md`, раздел 99.\n"
        )
        self.assertEqual(validate_section_references(self.root), [])

    def test_document_without_numbered_sections_is_not_checked(self) -> None:
        _write(
            self.root,
            EXECUTION_PLAN,
            "# Plan\n\n## Current checkpoint\n\nСм. раздел 4.\n",
        )
        self._product_plan("## 1. Purpose\n")
        self.assertEqual(validate_section_references(self.root), [])


class IdentifierTests(unittest.TestCase):
    def setUp(self) -> None:
        self.stack = TemporaryDirectory()
        self.addCleanup(self.stack.cleanup)
        self.root = Path(self.stack.name)
        _write(self.root, Path("AGENTS.md"), "# Agents\n")

    def test_unique_definitions_produce_no_errors(self) -> None:
        _write(
            self.root,
            EXECUTION_PLAN,
            "### PLAN-9B — family\n\n"
            "| **OD-1** | first |\n"
            "| **OD-2** | second |\n",
        )
        _write(
            self.root,
            CLEANUP_REGISTRY,
            "| C01 | first |\n| C43a | split |\n| C43b | split |\n",
        )
        self.assertEqual(validate_identifier_definitions(self.root), [])

    def test_duplicate_plan_definition_is_reported(self) -> None:
        _write(
            self.root,
            EXECUTION_PLAN,
            "### PLAN-9B — family\n\n#### PLAN-9B — family again\n",
        )
        errors = validate_identifier_definitions(self.root)
        self.assertEqual(len(errors), 1, errors)
        self.assertIn("duplicate plan step definition PLAN-9B", errors[0])

    def test_duplicate_owner_decision_is_reported(self) -> None:
        _write(
            self.root,
            EXECUTION_PLAN,
            "| **OD-1** | first |\n| **OD-1** | second |\n",
        )
        errors = validate_identifier_definitions(self.root)
        self.assertEqual(len(errors), 1, errors)
        self.assertIn("duplicate owner decision definition OD-1", errors[0])

    def test_duplicate_finding_across_documents_is_reported(self) -> None:
        _write(self.root, CLEANUP_REGISTRY, "| C50 | rights fail-open |\n")
        _write(self.root, PRODUCT_PLAN, "| C50 | copied here |\n")
        errors = validate_identifier_definitions(self.root)
        self.assertEqual(len(errors), 1, errors)
        self.assertIn("duplicate cleanup finding definition C50", errors[0])

    def test_repeated_references_are_not_duplicate_definitions(self) -> None:
        _write(
            self.root,
            EXECUTION_PLAN,
            "### PLAN-9B — family\n\n"
            "| **OD-1** | see PLAN-9B and OD-1 and C50 |\n"
            "Prerequisite: PLAN-9B. Gate: PLAN-9B. Registry C50, C50 (OD-1).\n"
            "| gate | PLAN-9B | OD-1 | C50 |\n",
        )
        _write(
            self.root,
            CLEANUP_REGISTRY,
            "| C50 | rights |\n\nСтрока закрывается по PLAN-9B (OD-1, C50).\n",
        )
        self.assertEqual(validate_identifier_definitions(self.root), [])

    def test_definition_inside_a_code_fence_is_ignored(self) -> None:
        _write(
            self.root,
            EXECUTION_PLAN,
            "### PLAN-9B — family\n\n```text\n### PLAN-9B — example\n```\n",
        )
        self.assertEqual(validate_identifier_definitions(self.root), [])

    def test_known_adr_reference_resolves(self) -> None:
        _write(self.root, Path("docs/adr/0008-canonical-provider-registry.md"), "# ADR\n")
        _write(self.root, EXECUTION_PLAN, "Единый registry (ADR 0008).\n")
        self.assertEqual(validate_adr_references(self.root), [])

    def test_unknown_adr_reference_is_reported(self) -> None:
        _write(self.root, Path("docs/adr/0008-canonical-provider-registry.md"), "# ADR\n")
        _write(self.root, EXECUTION_PLAN, "Решение принято в ADR 0099.\n")
        errors = validate_adr_references(self.root)
        self.assertEqual(
            errors,
            [f"{EXECUTION_PLAN.as_posix()}:1: reference to unknown ADR 0099"],
        )


class CodeDocumentationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.stack = TemporaryDirectory()
        self.addCleanup(self.stack.cleanup)
        self.root = Path(self.stack.name)
        for relative in (
            check_agent_docs.REQUIRED_PACKAGE_DOCSTRINGS
            + check_agent_docs.REQUIRED_MODULE_DOCSTRINGS
        ):
            _write(self.root, relative, '"""Canonical boundary.\n\nsrc/assets/README.md\n"""\n')
        _write(self.root, check_agent_docs.ASSETS_README, "# Assets\n")

    def test_documented_boundaries_produce_no_errors(self) -> None:
        self.assertEqual(validate_code_documentation(self.root), [])

    def test_missing_package_docstring_is_reported(self) -> None:
        _write(self.root, Path("src/news/__init__.py"), "VALUE = 1\n")
        errors = validate_code_documentation(self.root)
        self.assertIn("src/news/__init__.py: missing module docstring", errors)

    def test_missing_module_docstring_is_reported(self) -> None:
        _write(self.root, Path("src/news/pipeline.py"), "VALUE = 1\n")
        errors = validate_code_documentation(self.root)
        self.assertIn("src/news/pipeline.py: missing module docstring", errors)

    def test_missing_required_module_file_is_reported(self) -> None:
        (self.root / "src/news/final_renderer.py").unlink()
        errors = validate_code_documentation(self.root)
        self.assertIn("missing documented module: src/news/final_renderer.py", errors)

    def test_missing_assets_readme_is_reported(self) -> None:
        (self.root / check_agent_docs.ASSETS_README).unlink()
        errors = validate_code_documentation(self.root)
        self.assertIn("missing package README: src/assets/README.md", errors)

    def test_assets_package_docstring_must_point_at_the_readme(self) -> None:
        _write(self.root, check_agent_docs.ASSETS_PACKAGE, '"""Boundary without a pointer."""\n')
        errors = validate_code_documentation(self.root)
        self.assertIn(
            "src/assets/__init__.py: docstring must point at src/assets/README.md",
            errors,
        )

    def test_assets_package_docstring_stays_a_pointer(self) -> None:
        body = "\n".join(
            ["Canonical boundary.", "", "src/assets/README.md"]
            + [f"line {number}" for number in range(check_agent_docs.ASSETS_PACKAGE_DOCSTRING_MAX_LINES)]
        )
        _write(self.root, check_agent_docs.ASSETS_PACKAGE, f'"""{body}\n"""\n')
        errors = validate_code_documentation(self.root)
        self.assertTrue(any("not a second README" in error for error in errors), errors)

    def test_unparsable_module_is_reported_without_crashing(self) -> None:
        _write(self.root, Path("src/news/pipeline.py"), "def broken(:\n")
        errors = validate_code_documentation(self.root)
        self.assertTrue(
            any("cannot read module docstring" in error for error in errors), errors
        )


class TestClassificationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.stack = TemporaryDirectory()
        self.addCleanup(self.stack.cleanup)
        self.root = Path(self.stack.name)
        for relative, label in check_agent_docs.CLASSIFIED_TESTS:
            _write(self.root, relative, f'"""Test classification: {label}\n\nBody.\n"""\n')
        self.first = check_agent_docs.CLASSIFIED_TESTS[0][0]

    def test_classified_modules_produce_no_errors(self) -> None:
        self.assertEqual(validate_test_classification(self.root), [])

    def test_missing_classification_is_reported(self) -> None:
        _write(self.root, self.first, "import unittest\n")
        errors = validate_test_classification(self.root)
        self.assertIn(
            f"{self.first.as_posix()}: missing test classification docstring", errors
        )

    def test_docstring_without_the_classification_line_is_reported(self) -> None:
        _write(self.root, self.first, '"""Some other summary."""\n')
        errors = validate_test_classification(self.root)
        self.assertIn(
            f"{self.first.as_posix()}: docstring must start with "
            "'Test classification: <LABEL>'",
            errors,
        )

    def test_invalid_label_is_reported(self) -> None:
        _write(self.root, self.first, '"""Test classification: SMOKE\n\nBody.\n"""\n')
        errors = validate_test_classification(self.root)
        self.assertIn(
            f"{self.first.as_posix()}: invalid test classification label 'SMOKE'",
            errors,
        )

    def test_label_that_contradicts_governance_is_reported(self) -> None:
        _write(
            self.root,
            self.first,
            '"""Test classification: PRODUCT CONTRACT\n\nBody.\n"""\n',
        )
        errors = validate_test_classification(self.root)
        self.assertIn(
            f"{self.first.as_posix()}: test classification is 'PRODUCT CONTRACT', "
            "expected 'LEGACY ANCHOR'",
            errors,
        )

    def test_missing_classified_module_is_reported(self) -> None:
        (self.root / self.first).unlink()
        errors = validate_test_classification(self.root)
        self.assertIn(
            f"missing classified test module: {self.first.as_posix()}", errors
        )

    def test_every_expected_label_is_part_of_the_governance_vocabulary(self) -> None:
        for _relative, label in check_agent_docs.CLASSIFIED_TESTS:
            self.assertIn(label, check_agent_docs.TEST_CLASSIFICATION_LABELS)


class ImplementationIndexTests(unittest.TestCase):
    INDEX = (
        "# Implementation documentation\n\n"
        "## Status definitions\n\n"
        "| Статус | Значение |\n"
        "|---|---|\n"
        "| `current` | Подтверждено. |\n"
        "| `historical` | Свидетельство процесса. |\n"
        "| `superseded` | Заменено. |\n"
        "| `unknown` | Не доказано. |\n\n"
        "## Capability index\n\n"
        "| Каталог | Файлов | Статус | Назначение |\n"
        "|---|---|---|---|\n"
        "| [provider_foundation/](provider_foundation/) | 3 | `historical` | Отчёты. |\n"
    )

    def setUp(self) -> None:
        self.stack = TemporaryDirectory()
        self.addCleanup(self.stack.cleanup)
        self.root = Path(self.stack.name)
        _write(self.root, IMPLEMENTATION_INDEX, self.INDEX)
        (self.root / "docs/implementation/provider_foundation").mkdir(parents=True)
        _write(
            self.root,
            SYSTEM_MAP,
            "Индекс: [docs/implementation/README.md](../implementation/README.md).\n",
        )

    def test_valid_index_produces_no_errors(self) -> None:
        self.assertEqual(validate_implementation_index(self.root), [])

    def test_missing_index_is_reported(self) -> None:
        (self.root / IMPLEMENTATION_INDEX).unlink()
        errors = validate_implementation_index(self.root)
        self.assertEqual(
            errors, [f"missing implementation index: {IMPLEMENTATION_INDEX.as_posix()}"]
        )

    def test_index_without_a_referrer_link_is_reported(self) -> None:
        _write(self.root, SYSTEM_MAP, "Карта без ссылки на индекс.\n")
        errors = validate_implementation_index(self.root)
        self.assertIn(
            f"{SYSTEM_MAP.as_posix()}: no link to {IMPLEMENTATION_INDEX.as_posix()}",
            errors,
        )

    def test_unknown_status_is_reported(self) -> None:
        _write(
            self.root,
            IMPLEMENTATION_INDEX,
            self.INDEX.replace("| 3 | `historical` |", "| 3 | `probably_fine` |"),
        )
        errors = validate_implementation_index(self.root)
        self.assertTrue(
            any("unknown status 'probably_fine'" in error for error in errors), errors
        )

    def test_incomplete_status_vocabulary_is_reported(self) -> None:
        _write(
            self.root,
            IMPLEMENTATION_INDEX,
            self.INDEX.replace("| `superseded` | Заменено. |\n", ""),
        )
        errors = validate_implementation_index(self.root)
        self.assertTrue(
            any("status vocabulary must define exactly" in error for error in errors),
            errors,
        )

    def test_undocumented_capability_directory_is_reported(self) -> None:
        (self.root / "docs/implementation/brand_new_capability").mkdir()
        errors = validate_implementation_index(self.root)
        self.assertIn(
            f"{IMPLEMENTATION_INDEX.as_posix()}: undocumented capability directory "
            "brand_new_capability",
            errors,
        )


if __name__ == "__main__":
    unittest.main()
