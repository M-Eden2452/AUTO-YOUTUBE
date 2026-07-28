# ADR 0007: Canonical CLI package migration to src/ai_youtube/cli

## Status

Accepted on 2026-07-28; implemented by `bb9e28a`.

## Context

Previously, the canonical CLI entry point was split across `ai_youtube/cli/commands/content_creator.py`
and `src/content_creation/cli.py`. The monolith `src/content_creation/cli.py` contained parser definitions,
subcommand dispatching, and output formatting.

To advance the target architecture outlined in the Master Plan, the canonical CLI command layer needed
to be physically moved into `src/ai_youtube/cli` with domain command modules (`create`, `project`, `assets`, `diagnostics`),
while preserving `src/content_creation/cli.py` as a compatibility wrapper for existing tests and legacy entry points.

## Decision

- `src/ai_youtube/cli/main.py` is the canonical dispatcher entry point.
- `src/ai_youtube/__main__.py` provides module execution via `python -m ai_youtube`.
- Domain command handlers are structured in:
  - `src/ai_youtube/cli/commands/create.py` (handles `create`, `resume`, `wizard`)
  - `src/ai_youtube/cli/commands/project.py` (handles `project list`, `status`, `rights-report`, `validate`)
  - `src/ai_youtube/cli/commands/assets.py` (handles `assets replace`)
  - `src/ai_youtube/cli/commands/diagnostics.py` (handles `applications`, `capabilities`, `formats`, `templates`, `channels`, `voices`, `subtitles`, `script`, `visual-plan`, `run-stage`)
- `src/content_creation/cli.py` is converted into a thin compatibility wrapper that delegates to `src.ai_youtube.cli.main` while exporting public helper functions for backward compatibility.
- Root `ai_youtube/__main__.py` delegates module execution to `src.ai_youtube.cli.main`.
- Wizard (`src/content_creation/wizard.py`) is lazily imported inside command handlers to eliminate CLI ↔ Wizard import cycles.

## Consequences

1. `python -m ai_youtube` executes the structured canonical CLI in `src/ai_youtube/cli`.
2. Legacy entry points (`python -m src.content_creation.cli`, `pipeline.py`) continue to function without breaking changes.
3. No workflow business logic, project repository, asset manager, or renderer code was duplicated or altered.

## Verification

Run:

```powershell
.\venv\Scripts\python.exe -m ai_youtube --help
.\venv\Scripts\python.exe -m src.content_creation.cli --help
.\venv\Scripts\python.exe pipeline.py --help
.\venv\Scripts\python.exe -m unittest tests.test_stage4_canonical_cli tests.test_content_creation_cli tests.test_news_to_short_pipeline tests.test_news_to_short_models tests.test_project_repository tests.test_project_factory
.\venv\Scripts\python.exe -m tools.qa.check_agent_docs
```
