from __future__ import annotations

import unittest
from pathlib import Path

from tools.qa.check_agent_docs import REQUIRED_SKILLS, validate_repository


REPO_ROOT = Path(__file__).resolve().parents[1]

ONBOARDING_LINE_LIMITS = {
    Path("AGENTS.md"): 120,
    Path("CLAUDE.md"): 15,
    Path("docs/current/START_HERE.md"): 100,
    Path("docs/current/SYSTEM_MAP.md"): 240,
    Path("docs/current/CURRENT_STATE.md"): 280,
}

# A line count on its own is not a size limit: a journal satisfies it by losing
# its newlines instead of its content. That is not hypothetical here - before
# this guard existed CURRENT_STATE.md carried a single 49 648-character line,
# about 620 wrapped lines written as one, and START_HERE.md and SYSTEM_MAP.md
# carried 16 637 and 13 241.
#
# These documents are hand-wrapped prose: the widest line in AGENTS.md is 94
# characters. 120 leaves ordinary wrapping, long paths and link targets alone
# and still overshoots that 49 648-character line 413 times over.
ONBOARDING_MAX_LINE_LENGTH = 120

# A Markdown table row cannot be wrapped without ceasing to be a table row, so
# it gets its own ceiling rather than the prose one. It is not exempt: an
# unbounded exemption would just move the hiding place one character to the
# right. The widest legitimate row today is the Legacy/maintenance row of
# SYSTEM_MAP.md at 231 characters, so 400 lets a real table grow while still
# refusing a journal.
ONBOARDING_MAX_TABLE_ROW_LENGTH = 400

# The registry is an audit trail, not a second journal: one finding, its verdict,
# and a pointer to the commit whose body carries the account. Measured 2026-08-16
# across its 288 table rows - mean 687 characters, widest 4 043. The widest rows
# are full closure narratives that their own commit bodies already hold in full
# (ec369f8, 3475d5e and ede8c4b run 43 to 57 lines each), so the registry is
# storing a second copy at the exact place a new session has to read past.
REGISTRY_ROW_MAX_LENGTH = 1500

# The six rows that already exceeded the ceiling are named rather than rewritten
# today, and the reason is the same one the comment above gives for existing:
# summarising dense closure evidence to satisfy a number is how evidence gets
# lost. The repository already has an idiom for this shape - the ruff/mypy
# baseline in pyproject.toml - and AGENTS.md already states the rule that empties
# it: the slice that touches a baselined item drops its suppression. A name
# leaves this list when its row moves its narrative to the commit or to
# docs/audits/ and comes under the ceiling; the second assertion below refuses to
# let a name stay after that happened. New rows get 1 500 immediately, which is
# the point - the product audit of 2026-08-16 proposes eighteen of them.
REGISTRY_ROW_LENGTH_BASELINE: dict[str, int] = {
    "C43a": 1548,
    "C79": 2905,
    "C84": 1642,
    "C86": 3068,
    "C89": 4043,
    "R05": 1542,
}


def _is_table_row(line: str) -> bool:
    return line.lstrip().startswith("|")


def _registry_row_id(line: str) -> str:
    """The first cell of a registry row, without its Markdown decoration."""

    cells = line.strip().strip("|").split("|")
    return cells[0].strip().strip("`*_ ") if cells else ""


class Stage2AgentOnboardingTests(unittest.TestCase):
    def test_agent_docs_and_skills_are_consistent(self) -> None:
        # No frozen verification date: the checker derives its calendar
        # reference from the repository's own HEAD commit, so this test
        # exercises exactly what CI runs instead of a pinned constant that
        # could stay green while CI turned red.
        self.assertEqual(validate_repository(REPO_ROOT), [])

    def test_onboarding_documents_stay_short(self) -> None:
        # Every document is measured before anything is reported: failing on
        # the first one hides how much debt the others carry, which is exactly
        # how three documents grew past their limits behind one failure.
        too_long: list[str] = []
        for relative, limit in ONBOARDING_LINE_LIMITS.items():
            text = (REPO_ROOT / relative).read_text(encoding="utf-8")
            length = len(text.splitlines())
            if length > limit:
                too_long.append(f"{relative.as_posix()}: {length} lines, limit {limit}")
        self.assertEqual(
            too_long,
            [],
            "onboarding documents over their line limit:\n" + "\n".join(too_long),
        )

    def test_onboarding_documents_stay_hand_wrapped(self) -> None:
        """The line limits above cannot be met by deleting the line breaks."""

        too_wide: list[str] = []
        for relative in ONBOARDING_LINE_LIMITS:
            text = (REPO_ROOT / relative).read_text(encoding="utf-8")
            for number, line in enumerate(text.splitlines(), start=1):
                limit = (
                    ONBOARDING_MAX_TABLE_ROW_LENGTH
                    if _is_table_row(line)
                    else ONBOARDING_MAX_LINE_LENGTH
                )
                if len(line) > limit:
                    too_wide.append(
                        f"{relative.as_posix()}:{number}: "
                        f"{len(line)} characters, limit {limit}"
                    )
        self.assertEqual(
            too_wide,
            [],
            "lines that hide content by not wrapping:\n" + "\n".join(too_wide),
        )

    def test_registry_rows_stay_a_trail_and_not_a_journal(self) -> None:
        """A finding, a verdict and a pointer - not the account a commit holds."""

        relative = Path("docs/current/CLEANUP_REGISTRY.md")
        text = (REPO_ROOT / relative).read_text(encoding="utf-8")
        too_long: list[str] = []
        # Both directions are reported at once, for the reason the file limits
        # above learned: a guard that stops at its first complaint hides how many
        # rows are over, and one that never notices a row coming under keeps a
        # stale exemption alive forever.
        outgrown_baseline: list[str] = []
        for number, line in enumerate(text.splitlines(), start=1):
            if not _is_table_row(line):
                continue
            row_id = _registry_row_id(line)
            baseline = REGISTRY_ROW_LENGTH_BASELINE.get(row_id)
            limit = REGISTRY_ROW_MAX_LENGTH if baseline is None else baseline
            if len(line) > limit:
                too_long.append(
                    f"{relative.as_posix()}:{number}: {row_id or '(no id)'} "
                    f"{len(line)} characters, limit {limit}"
                )
            elif baseline is not None and len(line) <= REGISTRY_ROW_MAX_LENGTH:
                outgrown_baseline.append(row_id)
        self.assertEqual(
            too_long,
            [],
            "registry rows over their ceiling:\n" + "\n".join(too_long),
        )
        self.assertEqual(
            outgrown_baseline,
            [],
            "rows now under REGISTRY_ROW_MAX_LENGTH: drop them from "
            "REGISTRY_ROW_LENGTH_BASELINE in the same slice that shrank them: "
            + ", ".join(outgrown_baseline),
        )

    def test_required_skills_are_versioned(self) -> None:
        discovered = {
            path.parent.name
            for path in (REPO_ROOT / "skills").glob("*/SKILL.md")
        }
        self.assertEqual(discovered, set(REQUIRED_SKILLS))


if __name__ == "__main__":
    unittest.main()
