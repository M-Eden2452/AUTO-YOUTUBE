# ADR 0006: Stage idempotency policy for news research and script stages

## Status

Accepted on 2026-07-28; extended to the `script` stage family on 2026-07-29
by a second bounded slice 5D.

## Context

In the news workflow (`news_to_short`), pipeline execution relied solely on
`StageState.status == "completed"` in `job.json` to determine whether a stage could
be skipped during normal repeat runs or `resume=True`.

If a stage state was set to `"completed"` but its mandatory output file on disk was
deleted (missing) or corrupted (invalid format), the pipeline skipped re-executing
the stage, causing downstream stages to fail or operate on invalid data.

The first slice implemented stage output validation and idempotency for the
`research` stage family. The second bounded slice applies the same policy to
`script` without creating a new storage layer, universal dependency graph, or
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
- For the `script` stage:
  - Mandatory output:
    `<project_root>/localizations/<job.language>/script/script.json`.
  - Validation: file exists, is valid JSON, and contains a dictionary with
    non-empty `narration_text` plus a non-empty list of scene dictionaries.
  - `narration.txt` is not part of the completeness check. `script.json` is the
    canonical result consumed by downstream stages, while later workflow steps
    may legally adapt or annotate it.
- Re-execution policy:
  - `status == "completed"` + mandatory output valid + no `force_stage` -> skip stage.
  - `status == "completed"` + mandatory output missing or invalid -> re-execute stage.
  - `force_stage=True` -> re-execute stage regardless of completed state.
  - `status` in `{"running", "failed", "pending", "stale"}` -> re-execute stage.

## Consequences

Deleting or corrupting `claims.json` in a completed project causes the pipeline to
automatically re-run the `research` stage on resume or repeat run, restoring valid
claims without requiring manual job reset or `force_stage`.

Deleting `script.json`, replacing it with invalid JSON, or removing its mandatory
usable content causes the same automatic recovery for the localized `script`
stage. Completed legacy scripts remain readable because no new schema field is
required.

No manifest shape, schema version, project lock, runtime projects, or user media
are altered by this decision.

## Verification

Run:

```powershell
$env:PYTHONIOENCODING='utf-8'
.\venv\Scripts\python.exe -m unittest tests.test_news_to_short_pipeline tests.test_news_to_short_models tests.test_project_repository tests.test_project_factory tests.test_project_naming_and_resume
.\venv\Scripts\python.exe -m tools.qa.check_agent_docs
```
