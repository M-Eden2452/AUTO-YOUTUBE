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


def _is_table_row(line: str) -> bool:
    return line.lstrip().startswith("|")


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

    def test_required_skills_are_versioned(self) -> None:
        discovered = {
            path.parent.name
            for path in (REPO_ROOT / "skills").glob("*/SKILL.md")
        }
        self.assertEqual(discovered, set(REQUIRED_SKILLS))


if __name__ == "__main__":
    unittest.main()
