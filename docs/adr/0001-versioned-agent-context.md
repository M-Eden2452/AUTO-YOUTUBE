# ADR 0001: Versioned agent context is canonical

## Status

Accepted on 2026-07-28; implemented by `b7350b3`.

## Context

Agent context was spread across a model-specific `CLAUDE.md`, long handoff logs and
stale current-state pages. The proposed external `G:\AI-YouTube-System` does not yet
exist and would be unversioned if created as the only source.

## Decision

- Keep canonical instructions in root `AGENTS.md`.
- Keep short current knowledge in `docs/current/`.
- Keep reusable model-independent skills in `skills/`.
- Keep `CLAUDE.md` as a thin adapter only.
- Move superseded handoff material to `docs/archive/handoff/`.
- Treat any future external agent-system directory as a generated or synchronized
  consumer of these versioned sources until a separate sync contract is approved.

## Consequences

Agents can start from version-controlled files, historical claims are visibly
separated, and no second mutable source of truth is introduced.

## Verification

Run:

```powershell
.\venv\Scripts\python.exe -m tools.qa.check_agent_docs
```
