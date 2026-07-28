# ADR 0003: Canonical CLI and application boundaries

## Status

Accepted on 2026-07-28; implemented by `94034f2`.

## Context

The active `content_creator` application had a tested command surface under
`src.content_creation.cli`, while root `pipeline.py` and `apps/*` exposed older
entrypoints. There was no `python -m ai_youtube` dispatcher, CLI parser definitions
were concentrated in one module, and the CLI and Wizard each assembled the
application request independently. The Wizard also imported CLI presentation code,
forming the known CLI ↔ Wizard cycle.

The production catalog already records `content_creator` as active and
`video_repurposer` as planned/disabled. A new dispatcher must use that existing
registry instead of creating another application or capability contract.

## Decision

- `python -m ai_youtube` is the canonical command dispatcher. The installed
  `ai-youtube` console script resolves to the same dispatcher.
- The dispatcher registers only the active `content_creator` command surface.
- `applications list` shows only active/enabled applications by default. A planned
  application is visible through explicit inspection or `applications list --all`
  and retains its disabled/planned fields.
- Existing `python -m src.content_creation.cli`, root `pipeline.py` and `apps/*`
  entrypoints remain compatibility surfaces.
- Content command parser definitions are owned by separate catalog, project,
  content and authoring modules. Deeper extraction of the remaining large command
  handlers stays in rescue stage 6.
- CLI and Wizard translate presentation input through one request-builder boundary.
  Shared rights output lives in a presentation module, so Wizard no longer imports
  CLI code.
- New rerun and asset-replacement instructions use the canonical dispatcher.

## Consequences

New user-facing instructions have one entrypoint without hiding compatibility
commands that existing projects may rely on. Planned applications are queryable but
cannot be mistaken for ready workflows. CLI/Wizard request defaults remain identical
and are protected by compatibility tests. `src.content_creation.cli` is still large;
splitting its command implementations is a separate stage 6 change.

## Verification

Run the stage 4 characterization tests, the existing CLI/Wizard compatibility tests,
the affected service/catalog/project/asset/script/localization tests and module
entrypoint smoke checks with `.\venv\Scripts\python.exe`. On Windows test shells that
capture stdout as a legacy code page, set `PYTHONIOENCODING=utf-8`.

After documentation changes also run:

```powershell
.\venv\Scripts\python.exe -m tools.qa.check_agent_docs
```
