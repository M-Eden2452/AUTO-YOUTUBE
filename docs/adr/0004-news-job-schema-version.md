# ADR 0004: Versioned news job manifests

## Status

Accepted on 2026-07-28; implemented by `42d5b99`.

## Context

`NewsProjectStore` owns the persisted `job.json` form used by the
`fullscreen_voiceover_v1` workflow. The manifest had a characterization schema,
but no top-level version, while `project.json` and the other persisted artifact
contracts were already versioned.

Existing projects must remain readable through `NewsJob.from_dict`, and this
change must not introduce a second reader, rewrite runtime projects, or combine
schema work with project locking or stage idempotency.

## Decision

- `NEWS_JOB_SCHEMA_VERSION` is the single current version constant and is `1`.
- Every new `NewsJob.to_dict()` payload includes integer `schema_version`.
- `schemas/job.schema.json` requires `schema_version` with a minimum value of `1`.
- A legacy `job.json` without `schema_version` is interpreted as version `1`.
- Unknown fields continue to be ignored by the tolerant `NewsJob.from_dict`
  reader, and an explicitly stored version is preserved.

## Consequences

New news manifests are explicitly versioned without changing the storage owner or
the common atomic write primitive. Existing files are not migrated in bulk and
are not modified by this decision. When a legacy project is later saved through
its normal workflow, the rewritten manifest gains `schema_version: 1`.

Any future incompatible manifest change requires a new version decision and
characterization of both the old and new forms. Project locking and stage
idempotency remain separate rescue slices.

## Verification

Run:

```powershell
.\venv\Scripts\python.exe -m unittest tests.test_news_to_short_models tests.test_artifact_schemas
.\venv\Scripts\python.exe -m unittest tests.test_project_repository tests.test_news_to_short_pipeline
.\venv\Scripts\python.exe -m tools.qa.check_agent_docs
```
