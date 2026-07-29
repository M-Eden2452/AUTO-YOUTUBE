# ADR 0006: Stage idempotency policy for news research, script, and visual-plan stages

## Status

Accepted on 2026-07-28; extended to the `script` stage family on 2026-07-29
and to the `visual_plan` stage family on 2026-07-29 by separate bounded slices
5D.

## Context

In the news workflow (`news_to_short`), pipeline execution relied solely on
`StageState.status == "completed"` in `job.json` to determine whether a stage could
be skipped during normal repeat runs or `resume=True`.

If a stage state was set to `"completed"` but its mandatory output file on disk was
deleted (missing) or corrupted (invalid format), the pipeline skipped re-executing
the stage, causing downstream stages to fail or operate on invalid data.

The first slice implemented stage output validation and idempotency for the
`research` stage family. The next bounded slices apply the same policy to
`script` and `visual_plan` without creating a new storage layer, universal
dependency graph, or stage orchestration framework.

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
- For the `visual_plan` stage:
  - Mandatory output:
    `<project_root>/localizations/<job.language>/visual/visual_plan.json`.
  - Validation: file exists, is valid JSON, and contains a dictionary with a
    non-empty list of scene dictionaries.
  - `master/master_visual_plan.json` is not part of the completeness check. The
    localized plan is the result path recorded by the stage and the artifact
    consumed by `asset_search`; the master copy currently has no production
    reader.
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

Deleting `visual_plan.json`, replacing it with malformed JSON, or removing its
usable scene list causes automatic recovery for the localized `visual_plan`
stage. Completed legacy plans remain readable because no planner metadata or new
schema field is required.

No manifest shape, schema version, project lock, runtime projects, or user media
are altered by this decision.

## Verification

Run:

```powershell
$env:PYTHONIOENCODING='utf-8'
.\venv\Scripts\python.exe -m unittest tests.test_news_to_short_pipeline tests.test_news_to_short_models tests.test_project_repository tests.test_project_factory tests.test_project_naming_and_resume tests.test_visual_planning_pipeline
.\venv\Scripts\python.exe -m tools.qa.check_agent_docs
```
