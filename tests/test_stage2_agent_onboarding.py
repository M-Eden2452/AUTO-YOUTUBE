from __future__ import annotations

import unittest
from datetime import date
from pathlib import Path

from tools.qa.check_agent_docs import CURRENT_DOCS, REQUIRED_SKILLS, validate_repository


REPO_ROOT = Path(__file__).resolve().parents[1]


class Stage2AgentOnboardingTests(unittest.TestCase):
    def test_agent_docs_and_skills_are_consistent(self) -> None:
        self.assertEqual(
            validate_repository(
                REPO_ROOT,
                today=date(2026, 7, 28),
                max_age_days=120,
            ),
            [],
        )

    def test_onboarding_documents_stay_short(self) -> None:
        limits = {
            Path("AGENTS.md"): 120,
            Path("CLAUDE.md"): 15,
            **{path: 100 for path in CURRENT_DOCS},
        }
        for relative, limit in limits.items():
            lines = (REPO_ROOT / relative).read_text(encoding="utf-8").splitlines()
            self.assertLessEqual(len(lines), limit, f"{relative} exceeds {limit} lines")

    def test_required_skills_are_versioned(self) -> None:
        discovered = {
            path.parent.name
            for path in (REPO_ROOT / "skills").glob("*/SKILL.md")
        }
        self.assertEqual(discovered, set(REQUIRED_SKILLS))


if __name__ == "__main__":
    unittest.main()
