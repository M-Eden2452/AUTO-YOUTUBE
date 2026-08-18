"""WP0-A machine quality gates.

Единая команда локальных гейтов перед коммитом: ruff, mypy, docs-checker,
git whitespace-проверки и фиксированный набор repo-state guard-тестов. Полный
test suite сюда по-прежнему намеренно не входит — он остаётся в CI;
targeted-тесты текущего слайса запускаются отдельно, как и раньше
(AGENTS.md, «Среда и проверки»).
"""

from __future__ import annotations

import os
import subprocess
import sys

# Repo-state guards, and only they. The suite stays out for the reason the
# docstring gives, but the older rule - "gates run no tests at all" - cost this
# branch two red commits on 2026-08-18 (C100, C102): the row-ceiling guard is a
# 1.4-second test that no slice's targeted set had any reason to touch, so it
# survived every gate and every targeted run until a 16-minute full suite
# finally said it out loud.
#
# What belongs here: a test that reads the repository itself - its documents,
# its registry, its layout, its import boundaries - and answers in about a
# second. What deliberately does not: anything exercising behaviour (that is
# the slice's own targeted run), and ``test_claude_permission_contract``, which
# does ask a repo-state question but costs 20 s alone - twice this whole list.
# A gate people wait for is a gate people bypass.
REPO_STATE_GUARDS: tuple[str, ...] = (
    "tests.test_stage2_agent_onboarding",
    "tests.test_docs_routing_and_freshness",
    "tests.test_capability_consistency",
    "tests.test_asset_import_boundaries",
    "tests.test_apps_structure",
)

GATES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("ruff", (sys.executable, "-m", "ruff", "check", ".")),
    ("mypy", (sys.executable, "-m", "mypy")),
    ("agent-docs", (sys.executable, "-B", "-m", "tools.qa.check_agent_docs")),
    ("repo-state-guards", (sys.executable, "-B", "-m", "unittest", *REPO_STATE_GUARDS)),
    ("git-diff-check", ("git", "diff", "--check")),
    ("git-diff-cached-check", ("git", "diff", "--cached", "--check")),
)

# Failures of these guards quote registry rows and document lines, which are
# Cyrillic. A console left on cp1252 turns that report into an encoding error
# and the real complaint disappears.
ENV = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}


def main() -> int:
    for name, command in GATES:
        result = subprocess.run(command, env=ENV)
        if result.returncode != 0:
            print(f"GATES FAIL {name}")
            return result.returncode or 1
    print("GATES OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
