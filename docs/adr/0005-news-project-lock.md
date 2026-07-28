# ADR 0005: Fail-fast project lock for news writes

## Status

Accepted on 2026-07-28; implemented by `f7b3a3c`.

## Context

`NewsProjectStore.write_json` is the existing JSON writer boundary for the
`fullscreen_voiceover_v1` project tree. Slice 5A made each write atomic, but two
writers could still enter that boundary concurrently. The repository had no
shared project-lock primitive, and adding a workflow-specific second storage
layer would violate the project-foundation boundary.

This slice must not rewrite persisted projects, change manifest schemas, add
stage idempotency, or turn a single JSON write into a whole-stage transaction.

## Decision

- `src.project_foundation.storage.project_lock` is the shared project-lock
  primitive.
- Acquisition atomically creates `.project.lock` with
  `O_CREAT | O_EXCL`. Contention is fail-fast and raises `ProjectLockError`;
  writers do not wait indefinitely.
- The transient lock metadata contains an owner token, process ID and creation
  time. Release removes the lock only when the owner token still matches.
- A lock whose filesystem mtime is at most 300 seconds old is active. A lock
  older than 300 seconds is stale and may be reclaimed automatically.
- A fresh malformed lock is still treated as active. Age, not parseability or
  process inspection, is the stale-lock authority.
- `NewsProjectStore.write_json` resolves the news project root from `job.json`
  and holds the project lock around the existing `atomic_write_json` call.
  The direct parent remains the fallback for the pre-existing standalone static
  call shape when no news manifest ancestor exists.

## Consequences

All JSON writes through `NewsProjectStore` use the same `.project.lock` at the
news-project root once `job.json` exists. New project creation locks the initial
`job.json` at its parent and subsequent nested writes resolve that same root.
Successful writes leave neither the lock nor atomic tempfile behind.

The five-minute threshold is deliberately much longer than a single local JSON
write. A crashed writer can therefore recover without manual deletion, while a
fresh lock is never silently stolen. This is a writer-boundary lock only:
multi-file stage transactions, resume semantics and repeated-stage idempotency
remain slice 5D.

No manifest shape, tolerant reader, runtime project or user media is changed by
this decision.

## Verification

Run:

```powershell
.\venv\Scripts\python.exe -m unittest tests.test_news_to_short_models tests.test_project_repository tests.test_news_to_short_pipeline tests.test_project_factory
.\venv\Scripts\python.exe -m tools.qa.check_agent_docs
```
