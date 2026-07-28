# ADR 0006: Stage idempotency policy for news research stage

## Status

Accepted on 2026-07-28; implemented by slice 5D.

## Context

In the news workflow (`news_to_short`), pipeline execution relied solely on
`StageState.status == "completed"` in `job.json` to determine whether a stage could
be skipped during normal repeat runs or `resume=True`.

If a stage state was set to `"completed"` but its mandatory output file on disk was
deleted (missing) or corrupted (invalid format), the pipeline skipped re-executing
the stage, causing downstream stages to fail or operate on invalid data.

This slice implements stage output validation and idempotency for the `research`
stage family without creating a new storage layer, universal dependency graph, or
stage orchestration framework.

## Decision

- `NewsProjectStore.is_stage_completed(job, stage)` is the authority for stage
  completeness.
- A stage is completed if and only if `job.stages[stage].status == "completed"` AND
  its mandatory output file exists and passes validation via
  `NewsProjectStore.validate_stage_output(job, stage)`.
- For the `research` stage:
  - Mandatory output: `<project_root>/research/claims.json`.
  - Validation: file exists, is valid JSON, and contains a dictionary with a list of
    `claims`.
- Re-execution policy:
  - `status == "completed"` + mandatory output valid + no `force_stage` -> skip stage.
  - `status == "completed"` + mandatory output missing or invalid -> re-execute stage.
  - `force_stage=True` -> re-execute stage regardless of completed state.
  - `status` in `{"running", "failed", "pending", "stale"}` -> re-execute stage.

## Consequences

Deleting or corrupting `claims.json` in a completed project causes the pipeline to
automatically re-run the `research` stage on resume or repeat run, restoring valid
claims without requiring manual job reset or `force_stage`.

No manifest shape, schema version, project lock, runtime projects, or user media
are altered by this decision.

## Verification

Run:

```powershell
.\venv\Scripts\python.exe -m unittest tests.test_news_to_short_pipeline tests.test_news_to_short_models tests.test_project_repository tests.test_project_factory
.\venv\Scripts\python.exe -m tools.qa.check_agent_docs
```
