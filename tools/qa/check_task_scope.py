"""Compare a task-local path allowlist with the current Git working tree.

The checker is deliberately read-only.  It inspects porcelain status with
optional Git locks disabled, never reads changed file contents, and never
stages, fixes, or commits anything.
"""

from __future__ import annotations

import argparse
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Iterable, Sequence


REPO_ROOT = Path(__file__).resolve().parents[2]

OK = "OK"
STOP_REQUIRED = "STOP_REQUIRED"
INVALID_INPUT = "INVALID_INPUT"

EXIT_OK = 0
EXIT_STOP_REQUIRED = 1
EXIT_INVALID_INPUT = 2


class InvalidInputError(ValueError):
    """The requested repository or scope cannot be checked safely."""


class GitStatusError(RuntimeError):
    """Git could not provide a trustworthy working-tree status."""


@dataclass(frozen=True)
class ScopeRule:
    """One normalized exact-path or component-bounded directory rule."""

    kind: str
    path: str
    key: str

    @property
    def label(self) -> str:
        return f"{self.kind}:{self.path}"

    def matches(self, candidate: str) -> bool:
        candidate_key = _path_key(candidate)
        if self.kind == "exact":
            return candidate_key == self.key
        return candidate_key == self.key or candidate_key.startswith(self.key + "/")


@dataclass(frozen=True)
class Change:
    """One staged, unstaged, or untracked Git status fact."""

    source: str
    kind: str
    path: str
    old_path: str | None = None

    @property
    def affected_paths(self) -> tuple[str, ...]:
        if self.kind == "renamed" and self.old_path is not None:
            return self.old_path, self.path
        return (self.path,)


@dataclass(frozen=True)
class ScopeViolation:
    """A change with one or more paths outside the supplied task scope."""

    change: Change
    unexpected_paths: tuple[str, ...]


@dataclass(frozen=True)
class ScopeResult:
    """Stable result returned by the importable API and rendered by the CLI."""

    status: str
    explanation: str
    repository_root: str = ""
    allowed_scope: tuple[str, ...] = ()
    changes: tuple[Change, ...] = ()
    violations: tuple[ScopeViolation, ...] = ()

    @property
    def unexpected_paths(self) -> tuple[str, ...]:
        paths = {
            path
            for violation in self.violations
            for path in violation.unexpected_paths
        }
        return tuple(sorted(paths, key=_path_key))


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise InvalidInputError(message)


def _path_key(path: str) -> str:
    normalized = path.replace("\\", "/")
    return normalized.casefold() if os.name == "nt" else normalized


def _normalize_relative_parts(raw: str) -> str:
    parts: list[str] = []
    for part in raw.replace("\\", "/").split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            if not parts:
                raise InvalidInputError("allowed path escapes outside repository root")
            parts.pop()
            continue
        parts.append(part)
    if not parts:
        raise InvalidInputError("repository root itself is not a bounded allowed path")
    return PurePosixPath(*parts).as_posix()


def _is_absolute_or_driven(raw: str) -> bool:
    windows = PureWindowsPath(raw)
    return PurePosixPath(raw.replace("\\", "/")).is_absolute() or bool(
        windows.drive
    )


def _relative_to_root(root: Path, raw: str | os.PathLike[str]) -> str:
    text = os.fspath(raw).strip()
    if not text:
        raise InvalidInputError("allowed path must not be empty")

    if not _is_absolute_or_driven(text):
        return _normalize_relative_parts(text)

    windows = PureWindowsPath(text)
    if windows.drive and not windows.is_absolute():
        raise InvalidInputError("drive-relative allowed paths are ambiguous")

    candidate = Path(text).resolve(strict=False)
    root = root.resolve(strict=False)
    try:
        common = Path(os.path.commonpath((root, candidate)))
    except (OSError, ValueError) as exc:
        raise InvalidInputError("allowed path is outside repository root") from exc
    if _path_key(str(common)) != _path_key(str(root)):
        raise InvalidInputError("allowed path is outside repository root")
    relative = os.path.relpath(candidate, root)
    return _normalize_relative_parts(relative)


def normalize_scope_rules(
    repository_root: Path,
    *,
    allowed_paths: Iterable[str | os.PathLike[str]],
    allowed_directories: Iterable[str | os.PathLike[str]],
) -> tuple[ScopeRule, ...]:
    """Normalize, validate, deduplicate, and sort caller-supplied scope rules."""

    root = repository_root.resolve(strict=False)
    unique: dict[tuple[str, str], ScopeRule] = {}
    for kind, entries in (
        ("exact", allowed_paths),
        ("directory", allowed_directories),
    ):
        for raw in entries:
            path = _relative_to_root(root, raw)
            key = _path_key(path)
            unique[(kind, key)] = ScopeRule(kind=kind, path=path, key=key)
    return tuple(
        sorted(unique.values(), key=lambda rule: (rule.key, rule.kind, rule.path))
    )


def _decode_git_path(raw: bytes) -> str:
    return raw.decode("utf-8", errors="surrogateescape").replace("\\", "/")


def _change_kind(status: str) -> str:
    if status == "A" or status == "C":
        return "added"
    if status == "D":
        return "deleted"
    if status == "R":
        return "renamed"
    return "modified"


def parse_porcelain_status(payload: bytes) -> tuple[Change, ...]:
    """Parse ``git status --porcelain=v1 -z`` without path quoting loss."""

    fields = payload.split(b"\0")
    if fields and fields[-1] == b"":
        fields.pop()

    changes: list[Change] = []
    index = 0
    while index < len(fields):
        entry = fields[index]
        index += 1
        if len(entry) < 4 or entry[2:3] != b" ":
            raise GitStatusError("Git returned malformed porcelain status")

        x_status = chr(entry[0])
        y_status = chr(entry[1])
        path = _decode_git_path(entry[3:])
        old_path: str | None = None
        if x_status in "RC" or y_status in "RC":
            if index >= len(fields):
                raise GitStatusError("Git returned a rename without its old path")
            old_path = _decode_git_path(fields[index])
            index += 1

        if x_status == "?" and y_status == "?":
            changes.append(Change(source="untracked", kind="untracked", path=path))
            continue
        if x_status == "!" and y_status == "!":
            continue

        for source, status in (("staged", x_status), ("unstaged", y_status)):
            if status == " ":
                continue
            kind = _change_kind(status)
            changes.append(
                Change(
                    source=source,
                    kind=kind,
                    path=path,
                    old_path=old_path if kind == "renamed" else None,
                )
            )

    source_order = {"staged": 0, "unstaged": 1, "untracked": 2}
    return tuple(
        sorted(
            changes,
            key=lambda change: (
                _path_key(change.old_path or change.path),
                _path_key(change.path),
                source_order[change.source],
                change.kind,
            ),
        )
    )


def resolve_repository_root(candidate: Path) -> Path:
    """Validate that *candidate* is the top level of a readable Git worktree."""

    try:
        root = candidate.resolve(strict=True)
    except OSError as exc:
        raise InvalidInputError(f"repository root is not accessible: {candidate}") from exc
    if not root.is_dir():
        raise InvalidInputError(f"repository root is not a directory: {root}")

    completed = subprocess.run(
        ["git", "--no-optional-locks", "rev-parse", "--show-toplevel"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "unknown error"
        raise GitStatusError(f"Git repository root resolution failed: {detail}")
    discovered = Path(completed.stdout.strip()).resolve(strict=False)
    if _path_key(str(discovered)) != _path_key(str(root)):
        raise InvalidInputError(
            f"--root must be the Git repository root: discovered {discovered}"
        )
    return discovered


def collect_changes(repository_root: Path) -> tuple[Change, ...]:
    """Return current staged, unstaged, renamed, deleted, and untracked facts."""

    completed = subprocess.run(
        [
            "git",
            "--no-optional-locks",
            "status",
            "--porcelain=v1",
            "-z",
            "--untracked-files=all",
            "--renames",
        ],
        cwd=repository_root,
        check=False,
        capture_output=True,
    )
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise GitStatusError(f"Git status failed: {detail or 'unknown error'}")
    return parse_porcelain_status(completed.stdout)


def evaluate_changes(
    changes: Sequence[Change], rules: Sequence[ScopeRule]
) -> tuple[ScopeViolation, ...]:
    """Pure scope comparison over already collected change facts."""

    violations: list[ScopeViolation] = []
    for change in changes:
        unexpected = tuple(
            path
            for path in change.affected_paths
            if not any(rule.matches(path) for rule in rules)
        )
        if unexpected:
            violations.append(
                ScopeViolation(
                    change=change,
                    unexpected_paths=tuple(sorted(unexpected, key=_path_key)),
                )
            )
    return tuple(
        sorted(
            violations,
            key=lambda violation: (
                _path_key(violation.unexpected_paths[0]),
                violation.change.source,
                violation.change.kind,
            ),
        )
    )


def check_task_scope(
    repository_root: Path,
    *,
    allowed_paths: Iterable[str | os.PathLike[str]] = (),
    allowed_directories: Iterable[str | os.PathLike[str]] = (),
) -> ScopeResult:
    """Inspect one task working tree and return a non-mutating scope decision."""

    exact = tuple(allowed_paths)
    directories = tuple(allowed_directories)
    if not exact and not directories:
        return ScopeResult(
            status=INVALID_INPUT,
            explanation="at least one --allow or --allow-dir entry is required",
        )

    try:
        root = resolve_repository_root(Path(repository_root))
        rules = normalize_scope_rules(
            root,
            allowed_paths=exact,
            allowed_directories=directories,
        )
        changes = collect_changes(root)
    except (InvalidInputError, GitStatusError, OSError) as exc:
        return ScopeResult(status=INVALID_INPUT, explanation=str(exc))

    allowed_scope = tuple(rule.label for rule in rules)
    violations = evaluate_changes(changes, rules)
    if violations:
        return ScopeResult(
            status=STOP_REQUIRED,
            explanation=(
                "unexpected changed paths are outside the task allowlist; "
                "stop and request an owner decision before changing the diff"
            ),
            repository_root=str(root),
            allowed_scope=allowed_scope,
            changes=changes,
            violations=violations,
        )
    return ScopeResult(
        status=OK,
        explanation="all changed paths are within the task allowlist",
        repository_root=str(root),
        allowed_scope=allowed_scope,
        changes=changes,
    )


def _format_change(change: Change) -> str:
    if change.kind == "renamed":
        return f"{change.kind} ({change.source}): {change.old_path} -> {change.path}"
    return f"{change.kind} ({change.source}): {change.path}"


def render_result(result: ScopeResult) -> str:
    """Render stable text whose first line is a machine-readable status."""

    lines = [f"STATUS: {result.status}"]
    if result.repository_root:
        lines.append(f"REPOSITORY_ROOT: {result.repository_root}")
    if result.allowed_scope:
        lines.append("ALLOWED_SCOPE:")
        lines.extend(f"- {entry}" for entry in result.allowed_scope)
    if result.changes:
        lines.append("OBSERVED_CHANGES:")
        lines.extend(f"- {_format_change(change)}" for change in result.changes)
    else:
        lines.append("OBSERVED_CHANGES: none")
    if result.violations:
        lines.append("UNEXPECTED_CHANGES:")
        for violation in result.violations:
            outside = ", ".join(violation.unexpected_paths)
            lines.append(f"- {_format_change(violation.change)}; outside scope: {outside}")
    lines.append(f"DECISION: {result.explanation}")
    return "\n".join(lines)


def _build_parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(
        description="Check the current Git working tree against a task-local path scope."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=REPO_ROOT,
        help="Git repository root (defaults to this checkout).",
    )
    parser.add_argument(
        "--allow",
        dest="allowed_paths",
        action="append",
        default=[],
        metavar="PATH",
        help="Allow one exact repository path; repeat for additional paths.",
    )
    parser.add_argument(
        "--allow-dir",
        dest="allowed_directories",
        action="append",
        default=[],
        metavar="DIR",
        help="Allow one directory and descendants using component boundaries.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = _build_parser().parse_args(argv)
    except InvalidInputError as exc:
        result = ScopeResult(status=INVALID_INPUT, explanation=str(exc))
    else:
        result = check_task_scope(
            args.root,
            allowed_paths=args.allowed_paths,
            allowed_directories=args.allowed_directories,
        )
    print(render_result(result))
    return {
        OK: EXIT_OK,
        STOP_REQUIRED: EXIT_STOP_REQUIRED,
        INVALID_INPUT: EXIT_INVALID_INPUT,
    }[result.status]


if __name__ == "__main__":
    raise SystemExit(main())
