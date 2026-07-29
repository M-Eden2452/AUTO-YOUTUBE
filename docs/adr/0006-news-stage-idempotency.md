# ADR 0006: Output-validated idempotency for repeatable news stages

## Status

Accepted on 2026-07-28; extended to the `script` stage family on 2026-07-29
and to the `visual_plan` stage family on 2026-07-29 by separate bounded slices
5D. Completed for the remaining downstream families from `asset_search` through
`export` on 2026-07-29 by the stage 5 closure slice.

## Context

In the news workflow (`news_to_short`), pipeline execution relied solely on
`StageState.status == "completed"` in `job.json` to determine whether a stage could
be skipped during normal repeat runs or `resume=True`.

If a stage state was set to `"completed"` but its mandatory output file on disk was
deleted (missing) or corrupted (invalid format), the pipeline skipped re-executing
the stage, causing downstream stages to fail or operate on invalid data.

The first slices implemented stage output validation and idempotency for the
`research`, `script`, and `visual_plan` stage families. The stage 5 closure
applies the same authority to every remaining downstream family:
`asset_search`, `voice`, `subtitles`, `preview_render`, `quality_check`,
`final_render`, and `export`.

`input` and `article_ingestion` are deliberately outside this decision. `input`
is the immutable creation artifact, while re-running article ingestion may
perform network work. The master-plan 5D sequence explicitly starts at
`research` and continues from `asset_search`; it does not authorize an automatic
network retry policy.

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
- For the `asset_search` stage:
  - Mandatory output: `<project_root>/assets/assets_manifest.json`.
  - Current schema: a readable JSON object with a non-empty list of scene
    objects and a list of missing-scene objects.
  - The pre-schema dry-run shape remains accepted when it contains the legacy
    `dry_run`, `assets`, `missing_scenes`, and `warnings` fields. Existing
    projects are not migrated or forced into provider search merely because
    their valid old manifest predates scene entries.
- For the `voice` stage:
  - Mandatory output:
    `<project_root>/localizations/<job.language>/voice/voice_manifest.json`.
  - A readable manifest needs a non-empty `status`/`voice_stage_status` and a
    string `audio_path`. `provider_selection_required` remains a valid no-cost
    stage result.
  - A manifest that declares completed narration is reusable only while its
    declared audio file exists and is non-empty.
- For the `subtitles` stage:
  - Mandatory output:
    `<project_root>/localizations/<job.language>/subtitles/subtitles_manifest.json`.
  - The current cues and legacy segments shapes are both accepted. A generated
    manifest must retain every declared subtitle file.
  - A protected or `user_supplied` manifest remains complete without forcing a
    rewrite; the existing subtitle contract forbids overwriting user-authored
    files.
- For `preview_render`, the mandatory output is a non-empty
  `<project_root>/preview/preview.mp4`.
- For `quality_check`, the mandatory output is a readable
  `<project_root>/quality/quality_report.json` with a known verdict and the
  existing errors, warnings, and checks lists.
- For `final_render`, the mandatory output is a readable completed
  `<project_root>/render/final_render_manifest.json` whose declared
  `output_path` exists and is non-empty.
- For `export`, the mandatory output is the localized
  `output/project_manifest.json` with the existing export-contract fields.
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

The same recovery now applies from asset selection through export. Missing
declared narration, subtitle, preview, or final-render media invalidates only
the owning stage state; no runtime artifact is deleted or migrated. Provider
selection remains no-cost unless a separately approved execution path is
explicitly used.

No manifest shape, schema version, project lock, dispatcher, runtime project, or
user media is altered by this decision. The implementation extends the existing
`NewsProjectStore` authority instead of introducing a dependency graph, stage
framework, repository, or storage layer.

## Verification

Run:

```powershell
$env:PYTHONIOENCODING='utf-8'
.\venv\Scripts\python.exe -m unittest tests.test_news_stage_idempotency tests.test_news_to_short_models tests.test_project_repository tests.test_project_factory tests.test_project_naming_and_resume tests.test_artifact_schemas tests.test_subtitle_pipeline_integration tests.test_news_to_short_quality_check tests.test_news_to_short_delivery
.\venv\Scripts\python.exe -m tools.qa.check_agent_docs
```
