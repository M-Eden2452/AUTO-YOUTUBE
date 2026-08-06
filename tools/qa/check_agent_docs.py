from __future__ import annotations

import argparse
import ast
import re
import subprocess
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
CURRENT_DOCS = (
    Path("docs/current/START_HERE.md"),
    Path("docs/current/SYSTEM_MAP.md"),
    Path("docs/current/CURRENT_STATE.md"),
)
REQUIRED_SKILLS = (
    "create-short-video-first",
    "evaluate-render-quality",
    "resume-project",
    "replace-visual-slot",
    "architecture-change",
    "create-handoff",
    "review-change",
)
REVIEW_CHANGE_SKILL = "review-change"
REVIEW_CHANGE_CLAUDE_ADAPTER = Path(".claude/agents/review-change.md")
REVIEW_CHANGE_CLAUDE_FIELDS = {
    "name",
    "description",
    "model",
    "color",
    "permissionMode",
    "tools",
}
REVIEW_CHANGE_CLAUDE_TOOLS = {"Bash", "Glob", "Grep", "Read"}
REVIEW_CHANGE_POLICY_HEADINGS = {
    "Review dimensions",
    "Findings format",
    "Repair cycle",
}
REQUIRED_ARCHIVED_HANDOFFS = (
    "AUTONOMOUS_ARCHITECTURE_AUDIT.md",
    "AUTONOMOUS_IMPLEMENTATION_PLAN.md",
    "AUTONOMOUS_PROGRESS.md",
    "CLI_CHEATSHEET.md",
    "CURRENT_STATE.md",
    "HANDOFF_MANIFEST.json",
    "NEXT_PLAN.md",
    "PRODUCT_VISION_AND_ROADMAP.md",
    "REPO_SNAPSHOT.md",
    "START_HERE.md",
)
LOCAL_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
COMMIT_RE = re.compile(r"^[0-9a-f]{7,40}$")

# --- current vs historical -------------------------------------------------
#
# Strict validation applies only to routing/current authority. Historical
# evidence (docs/audits/** and historical files inside docs/implementation/**)
# keeps its original wording on purpose: one audit already contains 141
# repository-root-style links, mass rewriting of evidence is forbidden, and
# PLAN-12B/PLAN-12C own the final classification and archive. An index is
# required to link to historical files correctly; the historical files
# themselves are not required to satisfy this policy.
STRICT_CURRENT_DOCS = (
    Path("AGENTS.md"),
    Path("CLAUDE.md"),
    Path("docs/implementation/README.md"),
    Path("docs/adr/README.md"),
    Path("src/assets/README.md"),
)
STRICT_CURRENT_GLOBS = ("docs/current/*.md",)


@dataclass(frozen=True)
class GovernanceDocument:
    """Frontmatter contract of a main current governance document."""

    relative: Path
    status: str
    required_scalars: tuple[str, ...] = ()
    required_dates: tuple[str, ...] = ()
    required_paths: tuple[str, ...] = ()
    commit_fields: tuple[str, ...] = ()
    requires_source_paths: bool = False
    checkpoint_field: str = ""


# Freshness of these three is governed by their own revision process, not by a
# rolling window: adding a time window here would make the QA tool depend on
# the current date and turn a green tree red without any change to the repo.
GOVERNANCE_DOCS = (
    GovernanceDocument(
        relative=Path("docs/current/PRODUCT_PLAN.md"),
        status="active_product_plan",
        required_scalars=("product_plan_revision", "working_branch", "authority"),
        required_dates=("updated",),
        required_paths=("execution_source_of_truth",),
    ),
    GovernanceDocument(
        relative=Path("docs/current/PROJECT_EXECUTION_PLAN.md"),
        status="active",
        required_scalars=("plan_revision", "working_branch", "next_exact_action"),
        required_dates=("created_at", "updated_at"),
        commit_fields=("baseline_head",),
        requires_source_paths=True,
        checkpoint_field="current_checkpoint",
    ),
    GovernanceDocument(
        relative=Path("docs/current/CLEANUP_REGISTRY.md"),
        status="current",
        required_dates=("last_verified_date",),
        commit_fields=("last_verified_commit",),
        requires_source_paths=True,
    ),
)

# Section references are only self-references in a document that numbers its
# own sections. A document without numbered sections can only be pointing at
# another document, so its numeric references are not checked here.
SECTION_REFERENCE_DOCS = (
    Path("docs/current/PRODUCT_PLAN.md"),
    Path("docs/current/PROJECT_EXECUTION_PLAN.md"),
    Path("docs/current/CLEANUP_REGISTRY.md"),
)
SECTION_HEADING_RE = re.compile(r"^#{2,6}\s+(\d+(?:\.\d+)*)\.\s+\S")
SECTION_REFERENCE_RE = re.compile(
    r"(?:раздел\w*\s+|section\s+|§\s*)(\d+(?:\.\d+)*)", re.IGNORECASE
)
DOCUMENT_NAME_RE = re.compile(r"[A-Za-z0-9_.\-/]+\.md")
INLINE_CODE_RE = re.compile(r"`[^`]*`")
FENCE_RE = re.compile(r"^\s*(?:```|~~~)")

# Canonical definitions are distinguished from references by syntactic
# position, never by the identifier alone: identifiers legitimately repeat in
# references, prerequisites, gates and historical mentions.
#   PLAN/MOTION  -> section heading with an em-dash title
#   OD/PD        -> first table cell, bold
#   C<number>    -> first table cell, plain
PLAN_DEFINITION_RE = re.compile(
    r"^#{2,6}\s+((?:PLAN|MOTION)-[A-Za-z0-9′]+(?:-[A-Za-z0-9′]+)*)\s+—\s"
)
DECISION_DEFINITION_RE = re.compile(
    r"^\|\s*\*\*((?:OD|PD)-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)\*\*\s*\|"
)
FINDING_DEFINITION_RE = re.compile(r"^\|\s*(C\d+[a-z]?)\s*\|")
IDENTIFIER_DEFINITION_RULES = (
    ("plan step", PLAN_DEFINITION_RE),
    ("owner decision", DECISION_DEFINITION_RE),
    ("cleanup finding", FINDING_DEFINITION_RE),
)
CHECKPOINT_RE = re.compile(r"^(?:PLAN|MOTION)-[A-Za-z0-9′]+(?:-[A-Za-z0-9′]+)*$")
ADR_REFERENCE_RE = re.compile(r"\bADR[  ]?(\d{4})\b")

# --- current routing (PLAN-STAB-7) -----------------------------------------
#
# The execution plan's `current_checkpoint` is the single authority. The three
# onboarding documents mirror it in prose, so drift between them is exactly
# what a new agent reads as "three competing current tasks".
#
# Reference integrity is deliberately scoped to the routing fields. A blanket
# "every PLAN-ID mentioned anywhere must have a heading" rule would report ~33
# false positives: sub-steps such as PLAN-12B are defined as bold bullets
# inside their parent section, and `PLAN-ID` itself is an ordinary prose word.
EXECUTION_PLAN_DOC = Path("docs/current/PROJECT_EXECUTION_PLAN.md")
CLEANUP_REGISTRY_DOC = Path("docs/current/CLEANUP_REGISTRY.md")
ROUTING_MIRRORS = (
    Path("docs/current/START_HERE.md"),
    Path("docs/current/CURRENT_STATE.md"),
    Path("docs/current/SYSTEM_MAP.md"),
)
# A current statement is recognised by a narrow current marker, never by the
# bare presence of a PLAN-ID next to the word: the same paragraph legitimately
# records closed steps ("предыдущий checkpoint — PLAN-STAB-9 закрыт"), and
# reading those as current statements would report a conflict that does not
# exist. So a qualifier that is not `текущий`/`current` makes the sentence
# historical. `checkpoint` with no qualifier at all keeps its meaning, because
# the noun itself is the routing subject; a bare `шаг`/`step` is an ordinary
# word and is not read as routing at all.
CHECKPOINT_STATEMENT_RE = re.compile(
    r"(?:(?P<marker>[^\W\d_]+)\s+)?"
    r"\b(?P<subject>checkpoint|шаг|step)\b\s*[—–-]\s*\*{0,2}"
    r"(?P<identifier>(?:PLAN|MOTION)-[A-Za-z0-9′]+(?:-[A-Za-z0-9′]+)*)",
    re.IGNORECASE,
)
CURRENT_ROUTING_MARKERS = frozenset({"текущий", "current"})
PLAN_REFERENCE_RE = re.compile(r"(?:PLAN|MOTION)-[A-Za-z0-9′]+(?:-[A-Za-z0-9′]+)*")
# `PLAN-ID` reads like an identifier but is prose; it never defines a step.
PLAN_PROSE_WORDS = frozenset({"PLAN-ID", "PLAN-IDs"})
BULLET_PLAN_DEFINITION_RE = re.compile(
    r"^\s*-\s+\*\*((?:PLAN|MOTION)-[A-Za-z0-9′]+(?:-[A-Za-z0-9′]+)*)\*\*\s+—\s"
)
STEP_STATUS_RE = re.compile(r"^-\s+\*\*status:\*\*\s*(.+)$")
ANY_HEADING_RE = re.compile(r"^#{1,6}\s")
# The verdict is the head of the status value, not any word inside it: a
# pending step may legitimately say "completed слайс не объявляется".
COMPLETED_STATUS_PREFIX = "completed"

# --- Git-aware freshness (PLAN-STAB-8) -------------------------------------
#
# Every commit a current document points at is verified against real Git: it
# must exist and be reachable from HEAD. Recording the commit a document was
# verified against is self-referential by nature — a document cannot contain
# the hash of the commit that writes it — so the contract is "ancestor of
# HEAD" (N−1 semantics), never "equal to HEAD".
FRESHNESS_FIELDS = (
    (Path("docs/current/START_HERE.md"), "last_verified_commit"),
    (Path("docs/current/SYSTEM_MAP.md"), "last_verified_commit"),
    (Path("docs/current/CURRENT_STATE.md"), "last_verified_commit"),
    (CLEANUP_REGISTRY_DOC, "last_verified_commit"),
    (EXECUTION_PLAN_DOC, "baseline_head"),
)
# Drift of declared source_paths after the baseline is reported, never failed.
# Making it an error would demand a repository-wide rewrite of last_verified_*
# on every code commit — exactly the mass edit PLAN-STAB-8 forbids.
SOURCE_DRIFT_SAMPLE = 5

# Protects the DOC-CS1 result: these boundaries must stay documented in code.
REQUIRED_PACKAGE_DOCSTRINGS = (
    Path("src/assets/__init__.py"),
    Path("src/news/__init__.py"),
    Path("src/audio/__init__.py"),
    Path("src/providers/__init__.py"),
    Path("src/production_catalog/__init__.py"),
    Path("src/content_creation/__init__.py"),
    Path("src/assets/semantic_selection/__init__.py"),
    Path("src/projects/__init__.py"),
)
REQUIRED_MODULE_DOCSTRINGS = (
    Path("src/news/final_renderer.py"),
    Path("src/news/pipeline.py"),
    Path("src/production_catalog/catalog.py"),
    Path("src/assets/license_policy.py"),
    Path("src/assets/provider_contract.py"),
    Path("src/audio/narration_workflow.py"),
    Path("src/content_creation/service.py"),
)
ASSETS_README = Path("src/assets/README.md")
ASSETS_PACKAGE = Path("src/assets/__init__.py")
# Regression guard only, not a definition of architectural correctness: the
# assets package docstring is a pointer to src/assets/README.md, and this cap
# exists so it cannot silently grow back into a second full-size README.
ASSETS_PACKAGE_DOCSTRING_MAX_LINES = 40

TEST_CLASSIFICATION_LABELS = (
    "PRODUCT CONTRACT",
    "ARCHITECTURE INVARIANT",
    "CHARACTERIZATION",
    "LEGACY ANCHOR",
)
TEST_CLASSIFICATION_PREFIX = "Test classification:"
# Only the exact set current governance already classifies, never all of
# tests/**. LEGACY ANCHOR rows come from CLEANUP_REGISTRY.md section
# "Accidental invariants"; the two ARCHITECTURE INVARIANT modules come from the
# explicit non-anchor contrast in the same section. Modules where governance
# classifies individual assertions rather than the whole module are absent on
# purpose: a single module-level label would be false there.
CLASSIFIED_TESTS = (
    (Path("tests/test_apps_structure.py"), "LEGACY ANCHOR"),
    (Path("tests/test_channel_profiles.py"), "LEGACY ANCHOR"),
    (Path("tests/test_documentary_visual_engine.py"), "LEGACY ANCHOR"),
    (Path("tests/test_size_comparison_engine.py"), "LEGACY ANCHOR"),
    (Path("tests/test_legacy_pipeline_internals_contract.py"), "LEGACY ANCHOR"),
    (Path("tests/test_legacy_pipeline_application_boundary.py"), "LEGACY ANCHOR"),
    (Path("tests/test_asset_import_boundaries.py"), "ARCHITECTURE INVARIANT"),
    (Path("tests/test_capability_consistency.py"), "ARCHITECTURE INVARIANT"),
)

# Protects the DOC-CS2 result.
IMPLEMENTATION_ROOT = Path("docs/implementation")
IMPLEMENTATION_INDEX = Path("docs/implementation/README.md")
IMPLEMENTATION_INDEX_REFERRER = Path("docs/current/SYSTEM_MAP.md")
IMPLEMENTATION_STATUSES = ("current", "historical", "superseded", "unknown")
STATUS_COLUMN_HEADER = "Статус"
STATUS_DEFINITION_RE = re.compile(r"^\|\s*`([a-z]+)`\s*\|")
TABLE_SEPARATOR_RE = re.compile(r"^\|[\s:|-]+\|?$")
BACKTICK_TOKEN_RE = re.compile(r"`([^`]+)`")


def _frontmatter(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError("missing YAML frontmatter")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise ValueError("unterminated YAML frontmatter")
    payload = yaml.safe_load(text[4:end]) or {}
    if not isinstance(payload, dict):
        raise ValueError("frontmatter must be an object")
    return payload


def _local_links(path: Path) -> Iterable[Path]:
    for match in LOCAL_LINK_RE.finditer(path.read_text(encoding="utf-8")):
        raw = match.group(1).strip()
        if not raw or raw.startswith(("#", "http://", "https://", "mailto:")):
            continue
        target = raw.split("#", 1)[0].replace("%20", " ")
        if target:
            yield (path.parent / target).resolve()


def _prose_lines(text: str) -> list[tuple[int, str]]:
    """Numbered lines outside fenced code blocks and outside block quotes."""

    lines: list[tuple[int, str]] = []
    inside_fence = False
    for number, line in enumerate(text.splitlines(), start=1):
        if FENCE_RE.match(line):
            inside_fence = not inside_fence
            continue
        if inside_fence or line.lstrip().startswith(">"):
            continue
        lines.append((number, line))
    return lines


def _strict_current_documents(root: Path) -> list[Path]:
    documents = [root / relative for relative in STRICT_CURRENT_DOCS]
    for pattern in STRICT_CURRENT_GLOBS:
        documents.extend(sorted(root.glob(pattern)))
    seen: set[Path] = set()
    unique: list[Path] = []
    for document in documents:
        if document not in seen:
            seen.add(document)
            unique.append(document)
    return unique


def _label(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def _module_docstring(path: Path) -> str | None:
    """Top-level docstring of a Python module, or None when it has none."""

    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return ast.get_docstring(tree)


def _identifier_definitions(text: str) -> dict[tuple[str, str], list[int]]:
    found: dict[tuple[str, str], list[int]] = {}
    for number, line in _prose_lines(text):
        for kind, pattern in IDENTIFIER_DEFINITION_RULES:
            match = pattern.match(line)
            if match:
                found.setdefault((kind, match.group(1)), []).append(number)
    return found


def validate_governance_documents(root: Path) -> list[str]:
    """Metadata contract of PRODUCT_PLAN, PROJECT_EXECUTION_PLAN and registry."""

    errors: list[str] = []
    for document in GOVERNANCE_DOCS:
        name = document.relative.as_posix()
        path = root / document.relative
        if not path.is_file():
            errors.append(f"missing current document: {name}")
            continue
        try:
            metadata = _frontmatter(path)
        except (OSError, ValueError, yaml.YAMLError) as exc:
            errors.append(f"{name}: {exc}")
            continue

        if metadata.get("status") != document.status:
            errors.append(f"{name}: status must be {document.status}")
        for field in document.required_scalars:
            value = metadata.get(field)
            if value is None or not str(value).strip():
                errors.append(f"{name}: {field} must be a non-empty value")
        for field in document.required_dates:
            try:
                date.fromisoformat(str(metadata.get(field, "")))
            except ValueError:
                errors.append(f"{name}: invalid {field}")
        for field in document.commit_fields:
            if not COMMIT_RE.fullmatch(str(metadata.get(field, ""))):
                errors.append(f"{name}: invalid {field}")
        for field in document.required_paths:
            target = str(metadata.get(field, "")).strip()
            if not target:
                errors.append(f"{name}: {field} must be a non-empty value")
            elif not (root / target).exists():
                errors.append(f"{name}: {field} points at missing path {target}")
        if document.requires_source_paths:
            sources = metadata.get("source_paths")
            if not isinstance(sources, list) or not sources:
                errors.append(f"{name}: source_paths must be a non-empty list")
            else:
                for source in sources:
                    if not (root / str(source)).exists():
                        errors.append(f"{name}: missing source_path {source}")
        if document.checkpoint_field:
            errors.extend(_validate_checkpoint(path, name, document, metadata))
    return errors


def _validate_checkpoint(
    path: Path, name: str, document: GovernanceDocument, metadata: dict[str, Any]
) -> list[str]:
    field = document.checkpoint_field
    value = metadata.get(field)
    if isinstance(value, (list, dict)):
        return [f"{name}: {field} must be a single value"]
    checkpoint = str(value or "").strip()
    if not checkpoint:
        return [f"{name}: {field} must be a non-empty value"]
    if not CHECKPOINT_RE.fullmatch(checkpoint):
        return [f"{name}: {field} {checkpoint!r} is not an unambiguous plan identifier"]
    defined = {
        identifier
        for kind, identifier in _identifier_definitions(path.read_text(encoding="utf-8"))
        if kind == "plan step"
    }
    if checkpoint not in defined:
        return [f"{name}: {field} {checkpoint} has no step definition in this document"]
    return []


# --- read-only Git access --------------------------------------------------
#
# Same shape as tools/qa/check_task_scope.py: optional locks disabled, never
# checked for success implicitly, never mutating, never networked.


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            ["git", "--no-optional-locks", *args],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError:
        return None


def _git_succeeds(root: Path, *args: str) -> bool:
    completed = _git(root, *args)
    return completed is not None and completed.returncode == 0


def _repository_root(root: Path) -> Path | None:
    """The Git top level of *root*, or None when *root* is not one itself."""

    completed = _git(root, "rev-parse", "--show-toplevel")
    if completed is None or completed.returncode != 0:
        return None
    discovered = completed.stdout.strip()
    if not discovered:
        return None
    try:
        return Path(discovered).resolve()
    except OSError:
        return None


def _repository_is_shallow(root: Path) -> bool:
    completed = _git(root, "rev-parse", "--is-shallow-repository")
    if completed is None or completed.returncode != 0:
        return False
    return completed.stdout.strip().lower() == "true"


def _commit_exists(root: Path, commit: str) -> bool:
    return _git_succeeds(root, "cat-file", "-e", f"{commit}^{{commit}}")


def _is_ancestor_of_head(root: Path, commit: str) -> bool:
    return _git_succeeds(root, "merge-base", "--is-ancestor", commit, "HEAD")


def _changed_since(root: Path, commit: str, sources: Iterable[str]) -> list[str]:
    paths = [str(source) for source in sources if str(source).strip()]
    if not paths:
        return []
    completed = _git(root, "diff", "--name-only", commit, "HEAD", "--", *paths)
    if completed is None or completed.returncode != 0:
        return []
    return [line.strip() for line in completed.stdout.splitlines() if line.strip()]


def _head_commit_date(root: Path) -> date | None:
    completed = _git(root, "log", "-1", "--format=%cI")
    if completed is None or completed.returncode != 0:
        return None
    stamp = completed.stdout.strip()
    try:
        return date.fromisoformat(stamp[:10])
    except ValueError:
        return None


def _reference_date(root: Path) -> date:
    """Calendar reference for document age: the repository, not the wall clock.

    A wall-clock reference turns a green tree red without any change to the
    repository, which is why the previous contract had to be frozen inside the
    tests to stay green. The HEAD commit date is deterministic locally and in
    CI, needs no network, and moves only when the repository itself moves.
    """

    return _head_commit_date(root) or date.today()


def validate_freshness(
    root: Path, *, advisories: list[str] | None = None
) -> list[str]:
    """Commit metadata of current documents is verified against real Git.

    Fail-closed: without a readable, complete Git history the contract cannot
    be checked at all, and a checker that silently skips it would restore the
    decorative-hex-string behaviour PLAN-STAB-8 exists to remove.
    """

    errors: list[str] = []
    if _repository_root(root) != root.resolve():
        return [
            "cannot verify Git-aware documentation freshness: "
            f"{root} is not a readable Git repository; run the checker inside "
            "the repository checkout"
        ]
    if _repository_is_shallow(root):
        return [
            "cannot verify Git-aware documentation freshness: repository is a "
            "shallow clone and cannot resolve commit ancestry; use "
            "fetch-depth: 0 in CI or `git fetch --unshallow` locally"
        ]

    for relative, field in FRESHNESS_FIELDS:
        name = relative.as_posix()
        path = root / relative
        if not path.is_file():
            continue
        try:
            metadata = _frontmatter(path)
        except (OSError, ValueError, yaml.YAMLError):
            # Shape and readability are owned by the metadata contract above.
            continue
        commit = str(metadata.get(field, "")).strip()
        if not COMMIT_RE.fullmatch(commit):
            errors.append(
                f"{name}: {field} {commit!r} is not a Git commit id; record the "
                "commit the document was actually verified against"
            )
            continue
        if not _commit_exists(root, commit):
            errors.append(
                f"{name}: {field} {commit} is not a commit in this repository; "
                "record a commit that exists on this branch"
            )
            continue
        if not _is_ancestor_of_head(root, commit):
            errors.append(
                f"{name}: {field} {commit} is not an ancestor of HEAD; record a "
                "commit reachable from the current branch"
            )
            continue
        if advisories is None:
            continue
        sources = metadata.get("source_paths")
        if not isinstance(sources, list) or not sources:
            continue
        changed = _changed_since(root, commit, sources)
        if not changed:
            continue
        # Printed to a Windows console that is not guaranteed to be UTF-8, so
        # the advisory stays ASCII.
        shown = ", ".join(changed[:SOURCE_DRIFT_SAMPLE])
        if len(changed) > SOURCE_DRIFT_SAMPLE:
            shown += f", ... ({len(changed)} files total)"
        advisories.append(
            f"{name}: source_paths changed since {field} {commit}: {shown}; "
            "re-verify the content, then update the metadata in its own "
            "reviewed slice"
        )
    return errors


def _plan_step_headings(text: str) -> set[str]:
    return {
        identifier
        for kind, identifier in _identifier_definitions(text)
        if kind == "plan step"
    }


def _plan_step_bullets(text: str) -> set[str]:
    return {
        match.group(1)
        for _, line in _prose_lines(text)
        if (match := BULLET_PLAN_DEFINITION_RE.match(line))
    }


def _step_status(text: str, identifier: str) -> str | None:
    """First status verdict declared under the heading that defines *identifier*.

    Read from prose only, exactly like every other definition parser here: a
    heading or a status line shown as an example inside a fenced block or a
    block quote is not part of the document's own structure, and letting it end
    the section would hide the real status of a real step.
    """

    inside = False
    for _, line in _prose_lines(text):
        match = PLAN_DEFINITION_RE.match(line)
        if match:
            inside = match.group(1) == identifier
            continue
        if not inside:
            continue
        if ANY_HEADING_RE.match(line):
            return None
        status = STEP_STATUS_RE.match(line)
        if status:
            return status.group(1).strip().lstrip("*").strip()
    return None


def _current_checkpoint_statements(text: str) -> list[tuple[int, str]]:
    """Current-routing statements of a mirror as (line number, plan identifier)."""

    statements: list[tuple[int, str]] = []
    for number, line in _prose_lines(text):
        for match in CHECKPOINT_STATEMENT_RE.finditer(line):
            marker = (match.group("marker") or "").lower()
            if marker:
                if marker not in CURRENT_ROUTING_MARKERS:
                    continue
            elif match.group("subject").lower() != "checkpoint":
                continue
            statements.append((number, match.group("identifier")))
    return statements


def _referenced_plan_steps(value: str) -> set[str]:
    return set(PLAN_REFERENCE_RE.findall(value)) - PLAN_PROSE_WORDS


def validate_routing(root: Path) -> list[str]:
    """One authoritative current checkpoint that the mirrors cannot contradict."""

    name = EXECUTION_PLAN_DOC.as_posix()
    plan = root / EXECUTION_PLAN_DOC
    if not plan.is_file():
        return [f"missing current document: {name}"]
    try:
        metadata = _frontmatter(plan)
    except (OSError, ValueError, yaml.YAMLError):
        # Reported by the metadata contract; routing cannot be judged here.
        return []
    checkpoint = str(metadata.get("current_checkpoint") or "").strip()
    if not CHECKPOINT_RE.fullmatch(checkpoint):
        return []

    text = plan.read_text(encoding="utf-8")
    headings = _plan_step_headings(text)
    if checkpoint not in headings:
        return [
            f"{name}: current_checkpoint {checkpoint} has no heading definition "
            "in this document; a bullet-only step cannot be the current checkpoint"
        ]

    errors: list[str] = []
    status = _step_status(text, checkpoint)
    if status is None:
        errors.append(f"{name}: current_checkpoint {checkpoint} has no status line")
    elif status.lower().startswith(COMPLETED_STATUS_PREFIX):
        errors.append(
            f"{name}: current_checkpoint {checkpoint} is completed and cannot be "
            "the current checkpoint; move the checkpoint to the next open step"
        )

    action = str(metadata.get("next_exact_action") or "")
    defined = headings | _plan_step_bullets(text)
    for identifier in sorted(_referenced_plan_steps(action) - defined):
        errors.append(
            f"{name}: next_exact_action references undefined plan step {identifier}"
        )
    if checkpoint not in _referenced_plan_steps(action):
        errors.append(
            f"{name}: next_exact_action does not name current_checkpoint "
            f"{checkpoint}; the stated next action is stale"
        )

    for relative in ROUTING_MIRRORS:
        mirror_name = relative.as_posix()
        mirror = root / relative
        if not mirror.is_file():
            errors.append(f"missing current document: {mirror_name}")
            continue
        found = _current_checkpoint_statements(mirror.read_text(encoding="utf-8"))
        if not found:
            errors.append(
                f"{mirror_name}: no current-checkpoint statement; this routing "
                f"mirror must name current_checkpoint {checkpoint}"
            )
            continue
        for number, identifier in found:
            if identifier != checkpoint:
                errors.append(
                    f"{mirror_name}:{number}: routing mirror names checkpoint "
                    f"{identifier}, execution plan current_checkpoint is {checkpoint}"
                )
    return errors


def validate_section_references(root: Path) -> list[str]:
    """Numeric self-references resolve to a section this document defines."""

    errors: list[str] = []
    for relative in SECTION_REFERENCE_DOCS:
        name = relative.as_posix()
        path = root / relative
        if not path.is_file():
            errors.append(f"missing current document: {name}")
            continue
        lines = _prose_lines(path.read_text(encoding="utf-8"))
        sections = {
            match.group(1)
            for _, line in lines
            if (match := SECTION_HEADING_RE.match(line))
        }
        if not sections:
            # No numbered sections: a numeric reference here can only point at
            # another document, so it is not this document's to resolve.
            continue
        for number, line in lines:
            others = {
                found
                for found in DOCUMENT_NAME_RE.findall(line)
                if Path(found).name != relative.name
            }
            if others:
                continue
            for match in SECTION_REFERENCE_RE.finditer(INLINE_CODE_RE.sub(" ", line)):
                target = match.group(1)
                if target not in sections:
                    errors.append(
                        f"{name}:{number}: reference to missing section {target}"
                    )
    return errors


def validate_identifier_definitions(root: Path) -> list[str]:
    """Canonical identifiers are defined exactly once across current docs."""

    definitions: dict[tuple[str, str], list[str]] = {}
    for document in _strict_current_documents(root):
        if not document.is_file():
            continue
        label = _label(root, document)
        for key, numbers in _identifier_definitions(
            document.read_text(encoding="utf-8")
        ).items():
            definitions.setdefault(key, []).extend(
                f"{label}:{number}" for number in numbers
            )
    errors: list[str] = []
    for (kind, identifier), places in sorted(definitions.items()):
        if len(places) > 1:
            errors.append(
                f"duplicate {kind} definition {identifier}: {', '.join(places)}"
            )
    return errors


def validate_adr_references(root: Path) -> list[str]:
    """Every ADR referenced by a current document exists in docs/adr."""

    adr_root = root / "docs" / "adr"
    known = {
        path.name[:4]
        for path in adr_root.glob("*.md")
        if path.name[:4].isdigit()
    }
    errors: list[str] = []
    for document in _strict_current_documents(root):
        if not document.is_file():
            continue
        label = _label(root, document)
        for number, line in _prose_lines(document.read_text(encoding="utf-8")):
            for match in ADR_REFERENCE_RE.finditer(line):
                if match.group(1) not in known:
                    errors.append(
                        f"{label}:{number}: reference to unknown ADR {match.group(1)}"
                    )
    return errors


def validate_code_documentation(root: Path) -> list[str]:
    """Package and module boundaries documented by DOC-CS1 stay documented."""

    errors: list[str] = []
    for relative in REQUIRED_PACKAGE_DOCSTRINGS + REQUIRED_MODULE_DOCSTRINGS:
        name = relative.as_posix()
        path = root / relative
        if not path.is_file():
            errors.append(f"missing documented module: {name}")
            continue
        try:
            docstring = _module_docstring(path)
        except (OSError, SyntaxError, ValueError) as exc:
            errors.append(f"{name}: cannot read module docstring ({exc})")
            continue
        if not docstring or not docstring.strip():
            errors.append(f"{name}: missing module docstring")

    readme = root / ASSETS_README
    if not readme.is_file():
        errors.append(f"missing package README: {ASSETS_README.as_posix()}")

    package = root / ASSETS_PACKAGE
    if package.is_file():
        try:
            docstring = _module_docstring(package)
        except (OSError, SyntaxError, ValueError):
            docstring = None
        if docstring and docstring.strip():
            name = ASSETS_PACKAGE.as_posix()
            if ASSETS_README.as_posix() not in docstring:
                errors.append(
                    f"{name}: docstring must point at {ASSETS_README.as_posix()}"
                )
            length = len(docstring.splitlines())
            if length > ASSETS_PACKAGE_DOCSTRING_MAX_LINES:
                errors.append(
                    f"{name}: docstring is {length} lines; it is a pointer to "
                    f"{ASSETS_README.as_posix()}, not a second README "
                    f"(regression guard: {ASSETS_PACKAGE_DOCSTRING_MAX_LINES})"
                )
    return errors


def validate_test_classification(root: Path) -> list[str]:
    """Governance-classified test modules declare their class in code."""

    errors: list[str] = []
    for relative, expected in CLASSIFIED_TESTS:
        name = relative.as_posix()
        if expected not in TEST_CLASSIFICATION_LABELS:
            errors.append(f"{name}: unknown test classification label {expected!r}")
            continue
        path = root / relative
        if not path.is_file():
            errors.append(f"missing classified test module: {name}")
            continue
        try:
            docstring = _module_docstring(path)
        except (OSError, SyntaxError, ValueError) as exc:
            errors.append(f"{name}: cannot read module docstring ({exc})")
            continue
        if not docstring or not docstring.strip():
            errors.append(f"{name}: missing test classification docstring")
            continue
        first = next(
            (line.strip() for line in docstring.splitlines() if line.strip()), ""
        )
        if not first.startswith(TEST_CLASSIFICATION_PREFIX):
            errors.append(
                f"{name}: docstring must start with "
                f"'{TEST_CLASSIFICATION_PREFIX} <LABEL>'"
            )
            continue
        declared = first[len(TEST_CLASSIFICATION_PREFIX) :].strip()
        if declared not in TEST_CLASSIFICATION_LABELS:
            errors.append(f"{name}: invalid test classification label {declared!r}")
        elif declared != expected:
            errors.append(
                f"{name}: test classification is {declared!r}, expected {expected!r}"
            )
    return errors


def _status_column_tokens(lines: list[str]) -> dict[str, list[int]]:
    tokens: dict[str, list[int]] = {}
    column: int | None = None
    for number, line in enumerate(lines, start=1):
        if not line.startswith("|"):
            column = None
            continue
        if TABLE_SEPARATOR_RE.match(line.rstrip()):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if STATUS_COLUMN_HEADER in cells:
            column = cells.index(STATUS_COLUMN_HEADER)
            continue
        if column is None or column >= len(cells):
            continue
        for token in BACKTICK_TOKEN_RE.findall(cells[column]):
            tokens.setdefault(token, []).append(number)
    return tokens


def validate_implementation_index(root: Path) -> list[str]:
    """Implementation evidence stays indexed, routed to and honestly labelled."""

    errors: list[str] = []
    name = IMPLEMENTATION_INDEX.as_posix()
    index = root / IMPLEMENTATION_INDEX
    if not index.is_file():
        errors.append(f"missing implementation index: {name}")
        return errors

    referrer = root / IMPLEMENTATION_INDEX_REFERRER
    if not referrer.is_file():
        errors.append(f"missing current document: {IMPLEMENTATION_INDEX_REFERRER.as_posix()}")
    elif index.resolve() not in set(_local_links(referrer)):
        errors.append(
            f"{IMPLEMENTATION_INDEX_REFERRER.as_posix()}: no link to {name}"
        )

    text = index.read_text(encoding="utf-8")
    lines = text.splitlines()
    declared = [
        match.group(1)
        for line in lines
        if (match := STATUS_DEFINITION_RE.match(line))
    ]
    if sorted(declared) != sorted(IMPLEMENTATION_STATUSES):
        errors.append(
            f"{name}: status vocabulary must define exactly "
            f"{', '.join(IMPLEMENTATION_STATUSES)}"
        )
    for token, numbers in sorted(_status_column_tokens(lines).items()):
        if token not in IMPLEMENTATION_STATUSES:
            places = ", ".join(f"{name}:{number}" for number in numbers)
            errors.append(f"{name}: unknown status {token!r} at {places}")

    indexed = set()
    for match in LOCAL_LINK_RE.finditer(text):
        raw = match.group(1).strip()
        if not raw or raw.startswith(("#", "http://", "https://", "mailto:")):
            continue
        head = raw.split("#", 1)[0].split("/", 1)[0]
        if head:
            indexed.add(head)
    implementation_root = root / IMPLEMENTATION_ROOT
    if implementation_root.is_dir():
        for entry in sorted(implementation_root.iterdir()):
            if entry.is_dir() and entry.name not in indexed:
                errors.append(f"{name}: undocumented capability directory {entry.name}")
    return errors


def validate_skills(
    root: Path = REPO_ROOT,
    *,
    required_skills: Iterable[str] = REQUIRED_SKILLS,
) -> list[str]:
    """Validate canonical repository skills and their thin platform adapters."""

    errors: list[str] = []
    for skill_name in required_skills:
        skill_root = root / "skills" / skill_name
        skill_file = skill_root / "SKILL.md"
        openai_file = skill_root / "agents" / "openai.yaml"
        if not skill_file.is_file():
            errors.append(f"missing skill: {skill_name}")
            continue
        try:
            metadata = _frontmatter(skill_file)
        except (OSError, ValueError, yaml.YAMLError) as exc:
            errors.append(f"{skill_name}: {exc}")
            continue
        if set(metadata) != {"name", "description"}:
            errors.append(
                f"{skill_name}: SKILL.md frontmatter must contain only name/description"
            )
        if metadata.get("name") != skill_name:
            errors.append(f"{skill_name}: frontmatter name mismatch")
        content = skill_file.read_text(encoding="utf-8")
        if "TODO" in content:
            errors.append(f"{skill_name}: unresolved TODO")

        if not openai_file.is_file():
            errors.append(f"{skill_name}: missing agents/openai.yaml")
        else:
            try:
                openai_metadata = (
                    yaml.safe_load(openai_file.read_text(encoding="utf-8")) or {}
                )
                prompt = openai_metadata["interface"]["default_prompt"]
            except (KeyError, TypeError, yaml.YAMLError) as exc:
                errors.append(f"{skill_name}: invalid agents/openai.yaml ({exc})")
            else:
                if f"${skill_name}" not in prompt:
                    errors.append(
                        f"{skill_name}: default_prompt must mention ${skill_name}"
                    )

        if skill_name != REVIEW_CHANGE_SKILL:
            continue

        if "GIT_OPTIONAL_LOCKS=0" not in content or "git --no-optional-locks" not in content:
            errors.append(
                f"{skill_name}: canonical skill must disable optional Git locks"
            )

        claude_file = root / REVIEW_CHANGE_CLAUDE_ADAPTER
        if not claude_file.is_file():
            errors.append(
                f"{skill_name}: missing {REVIEW_CHANGE_CLAUDE_ADAPTER.as_posix()}"
            )
            continue
        try:
            claude_metadata = _frontmatter(claude_file)
        except (OSError, ValueError, yaml.YAMLError) as exc:
            errors.append(f"{skill_name}: invalid Claude adapter ({exc})")
            continue
        if set(claude_metadata) != REVIEW_CHANGE_CLAUDE_FIELDS:
            errors.append(
                f"{skill_name}: Claude adapter frontmatter must contain exactly "
                + ", ".join(sorted(REVIEW_CHANGE_CLAUDE_FIELDS))
            )
        if claude_metadata.get("name") != skill_name:
            errors.append(f"{skill_name}: Claude adapter name mismatch")
        if claude_metadata.get("model") != "sonnet":
            errors.append(f"{skill_name}: Claude adapter model must be sonnet")
        if claude_metadata.get("permissionMode") != "plan":
            errors.append(f"{skill_name}: Claude adapter permissionMode must be plan")
        raw_tools = claude_metadata.get("tools")
        tools = set(raw_tools) if isinstance(raw_tools, list) else set()
        if tools != REVIEW_CHANGE_CLAUDE_TOOLS:
            expected = ", ".join(sorted(REVIEW_CHANGE_CLAUDE_TOOLS))
            found = ", ".join(sorted(str(tool) for tool in tools)) or "none"
            errors.append(
                f"{skill_name}: Claude adapter tools must be exactly {expected} "
                f"(found {found})"
            )

        claude_content = claude_file.read_text(encoding="utf-8")
        if "skills/review-change/SKILL.md" not in claude_content:
            errors.append(
                f"{skill_name}: Claude adapter must point to "
                "skills/review-change/SKILL.md"
            )
        if (
            "GIT_OPTIONAL_LOCKS=0" not in claude_content
            or "git --no-optional-locks" not in claude_content
        ):
            errors.append(
                f"{skill_name}: Claude adapter must disable optional Git locks"
            )
        duplicated = sorted(
            heading
            for heading in REVIEW_CHANGE_POLICY_HEADINGS
            if f"## {heading}" in claude_content
        )
        if duplicated:
            errors.append(
                f"{skill_name}: Claude adapter duplicates canonical policy sections: "
                + ", ".join(duplicated)
            )
    return errors


def validate_repository(
    root: Path = REPO_ROOT,
    *,
    today: date | None = None,
    max_age_days: int = 120,
    advisories: list[str] | None = None,
) -> list[str]:
    errors: list[str] = []
    today = today or _reference_date(root)

    linked_docs = [root / "AGENTS.md", root / "CLAUDE.md"]
    for relative in CURRENT_DOCS:
        path = root / relative
        linked_docs.append(path)
        if not path.is_file():
            errors.append(f"missing current document: {relative.as_posix()}")
            continue
        try:
            metadata = _frontmatter(path)
        except (OSError, ValueError, yaml.YAMLError) as exc:
            errors.append(f"{relative.as_posix()}: {exc}")
            continue
        if metadata.get("status") != "current":
            errors.append(f"{relative.as_posix()}: status must be current")
        commit = str(metadata.get("last_verified_commit", ""))
        if not COMMIT_RE.fullmatch(commit):
            errors.append(f"{relative.as_posix()}: invalid last_verified_commit")
        try:
            verified = date.fromisoformat(str(metadata.get("last_verified_date", "")))
        except ValueError:
            errors.append(f"{relative.as_posix()}: invalid last_verified_date")
        else:
            age = (today - verified).days
            if age < 0:
                errors.append(f"{relative.as_posix()}: verification date is in the future")
            elif age > max_age_days:
                errors.append(
                    f"{relative.as_posix()}: metadata is stale ({age} days; max {max_age_days})"
                )
        sources = metadata.get("source_paths")
        if not isinstance(sources, list) or not sources:
            errors.append(f"{relative.as_posix()}: source_paths must be a non-empty list")
        else:
            for source in sources:
                source_path = root / str(source)
                if not source_path.exists():
                    errors.append(f"{relative.as_posix()}: missing source_path {source}")

    errors.extend(validate_governance_documents(root))

    linked_docs.extend(root / "skills" / name / "SKILL.md" for name in REQUIRED_SKILLS)
    errors.extend(validate_skills(root))

    handoff_root = root / "docs" / "handoff"
    if handoff_root.is_dir():
        unexpected = sorted(
            path.name
            for path in handoff_root.iterdir()
            if path.is_file() and path.name != "PROJECT_RESCUE_MASTER_PLAN.md"
        )
        if unexpected:
            errors.append(f"historical files remain in docs/handoff: {', '.join(unexpected)}")
    archive_root = root / "docs" / "archive" / "handoff"
    for filename in REQUIRED_ARCHIVED_HANDOFFS:
        if not (archive_root / filename).is_file():
            errors.append(f"missing archived handoff: {filename}")

    for document in linked_docs + _strict_current_documents(root):
        if not document.is_file():
            continue
        for target in _local_links(document):
            if not target.exists():
                label = _label(root, document)
                errors.append(f"{label}: broken local link to {target}")

    errors.extend(validate_routing(root))
    errors.extend(validate_freshness(root, advisories=advisories))
    errors.extend(validate_section_references(root))
    errors.extend(validate_identifier_definitions(root))
    errors.extend(validate_adr_references(root))
    errors.extend(validate_code_documentation(root))
    errors.extend(validate_test_classification(root))
    errors.extend(validate_implementation_index(root))

    seen: set[str] = set()
    unique_errors: list[str] = []
    for error in errors:
        if error not in seen:
            seen.add(error)
            unique_errors.append(error)
    return unique_errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate current agent docs and skills.")
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    parser.add_argument("--max-age-days", type=int, default=120)
    args = parser.parse_args(argv)

    advisories: list[str] = []
    errors = validate_repository(
        args.root.resolve(),
        max_age_days=args.max_age_days,
        advisories=advisories,
    )
    for advisory in advisories:
        print(f"NOTE: {advisory}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("Agent documentation and skills are current and internally consistent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
