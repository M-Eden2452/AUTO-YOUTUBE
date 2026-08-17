---
name: architecture-change
description: Make a bounded architecture change in AI-YouTube while preserving characterization contracts, compatibility wrappers, persisted projects, and the current rescue-stage boundary. Use for refactors, module moves, new boundaries, storage or path changes, provider consolidation, or public contract decisions.
---

# Architecture Change

Keep the change inside one verified rescue stage or one smaller vertical slice.

## Workflow

1. Read [AGENTS.md](../../AGENTS.md),
   [SYSTEM_MAP.md](../../docs/current/SYSTEM_MAP.md) and the active rescue stage.
2. Record Git status, HEAD and existing uncommitted work.
3. Locate callers, tests, persisted schemas and compatibility entrypoints.
4. Add or identify a characterization test before changing behavior.
5. Reuse the existing repository, resolver, provider contract, engine and application
   service. Create an adapter when compatibility is required.
6. Implement one bounded change. Do not combine cleanup, mass moves or unrelated module
   splits.
7. Preserve tolerant readers and old entrypoints until their compatibility period ends.
8. Run targeted contract/regression tests and inspect the diff.
9. Add an ADR under `docs/adr/` when the decision changes a public contract or system
   boundary, and also when it introduces a new module-owner, a new persisted field, a
   new config-gate, or a new class of network action — these are boundary decisions
   even when the surrounding diff looks additive.
10. Refresh `docs/current/` metadata and the rescue handoff when their claims changed.

## Stop conditions

Stop and prepare a separate plan if the change requires:

- a second source of truth or duplicated subsystem;
- physical runtime migration;
- deletion of user data or legacy code without a tested replacement;
- paid/network actions;
- changes spanning more than the current rescue stage.
