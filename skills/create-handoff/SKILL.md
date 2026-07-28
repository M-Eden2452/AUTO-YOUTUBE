---
name: create-handoff
description: Create a concise evidence-based handoff for ongoing AI-YouTube work using factual Git state, changed files, targeted test results, artifacts, external actions, blockers, and the next exact step. Use when ending a rescue stage, transferring work, or updating current project context for another agent.
---

# Create Handoff

Record facts that the next agent can verify quickly.

## Workflow

1. Read [AGENTS.md](../../AGENTS.md).
2. Capture:

   ```powershell
   git status --short --branch
   git log -5 --oneline
   git diff --stat
   ```

3. State the starting and current HEAD separately.
4. List only files and behavior actually changed.
5. Record exact targeted test commands, counts, results and interpreter. If the full
   suite was not run, say so explicitly.
6. Record created runtime artifacts and project IDs, or state that none were created.
7. Record network/API/paid actions and user approvals, including `none`.
8. Describe verified root causes, known issues, blockers and actions that must not be
   repeated.
9. Give the next exact command or bounded action.
10. For rescue work, update the stage status and `Текущий handoff` in
    [PROJECT_RESCUE_MASTER_PLAN.md](../../docs/handoff/PROJECT_RESCUE_MASTER_PLAN.md).

## Accuracy rules

- Do not copy old counts or claims without rechecking them.
- Do not call a dirty tree clean.
- Do not call a stage complete before targeted validation passes.
- Keep archived progress logs out of current-state documentation.
