"""WP0-A machine quality gates.

Единая команда локальных гейтов перед коммитом: ruff, mypy, docs-checker и
git whitespace-проверки. Полный test suite сюда намеренно не входит — он
остаётся в CI; targeted-тесты текущего слайса запускаются отдельно, как и
раньше (AGENTS.md, «Среда и проверки»).
"""

from __future__ import annotations

import subprocess
import sys

GATES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("ruff", (sys.executable, "-m", "ruff", "check", ".")),
    ("mypy", (sys.executable, "-m", "mypy")),
    ("agent-docs", (sys.executable, "-B", "-m", "tools.qa.check_agent_docs")),
    ("git-diff-check", ("git", "diff", "--check")),
    ("git-diff-cached-check", ("git", "diff", "--cached", "--check")),
)


def main() -> int:
    for name, command in GATES:
        result = subprocess.run(command)
        if result.returncode != 0:
            print(f"GATES FAIL {name}")
            return result.returncode or 1
    print("GATES OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
