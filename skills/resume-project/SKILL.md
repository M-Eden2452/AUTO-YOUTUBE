---
name: resume-project
description: Inspect and safely resume an existing AI-YouTube project through the current ProjectRepository and content-creation CLI while preserving completed stages and explicit paid-action approval. Use for requests to continue, recover, retry, or finish an existing project or job ID.
---

# Resume Project

Resume from persisted state; do not reconstruct or rewrite the project.

## Workflow

1. Read [AGENTS.md](../../AGENTS.md) and check Git.
2. Inspect the project without mutation:

   ```powershell
   .\venv\Scripts\python.exe -m src.content_creation.cli project status --project-id <id> --json
   ```

3. Verify the manifest path, project kind, last completed stage, blockers, stale
   downstream stages and existing outputs.
4. Inspect the stage-specific manifest named by the blocker. Do not trust only the
   top-level `status`.
5. Resume through the canonical CLI:

   ```powershell
   .\venv\Scripts\python.exe -m src.content_creation.cli resume --project-id <id> --json
   ```

6. Add `--dry-run` or `--prepare-only` when an offline diagnosis is sufficient.
7. Use `--force-stage` only for a named stage with a verified reason. It never grants
   permission for paid TTS or another external call.
8. If the next action is paid or networked, stop before it and request explicit approval.
9. Re-run `project status --json` and verify the new manifest/output paths.

## Guardrails

- Do not edit `job.json`, `project.json` or stage status by hand.
- Do not rerun completed research, asset search or render without a concrete need.
- Do not add `--approve-paid-generation` unless the user approved that exact generation.
- Preserve tolerant reading of old projects.
