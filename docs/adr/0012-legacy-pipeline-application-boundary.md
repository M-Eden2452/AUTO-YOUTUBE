# ADR 0012: Legacy pipeline application boundary

## Status

Accepted on 2026-07-29 as the fourth vertical slice of rescue stage 8.

## Context

The historical command surface is still owned by root `pipeline.py`. That
module is a compatibility facade whose namespace intentionally exposes engine
functions for external imports and monkeypatch-based integrations. Parsing,
maintenance dispatch, and channel/video orchestration already live in
`src.legacy_pipeline`.

The compatibility entrypoint `python -m apps.youtube_pipeline` called the root
facade directly. Physically moving the facade or the legacy engine modules
would break those patch points and would mix this application-boundary slice
with documentary migration, runtime migration, or compatibility retirement.

## Decision

- The canonical adapter boundary is
  `src.ai_youtube.apps.legacy_pipeline.adapter`.
- It lazily re-exports the existing root `main`, `parse_args`,
  `run_maintenance_command`, `run_legacy_video_pipeline`, and
  `limit_scene_plan` objects.
- It re-exports the existing `LegacyPipelineArtifacts` dataclass from
  `src.legacy_pipeline.workflow`; no new project, manifest, or artifact
  contract is introduced.
- `apps.youtube_pipeline` remains the compatibility entrypoint and now resolves
  root `main` through the canonical adapter.
- Root `pipeline.py` remains the compatibility namespace owner so its
  historical engine patch points continue to control the split handlers.
- `src.legacy_pipeline` remains the sole owner of parser, maintenance, and
  legacy channel/video workflow behavior.

## Compatibility and migration

Existing imports and commands continue to work:

```python
import pipeline
from src.legacy_pipeline.workflow import run_legacy_video_pipeline
```

```powershell
.\venv\Scripts\python.exe pipeline.py --help
.\venv\Scripts\python.exe -m apps.youtube_pipeline --help
```

New application-boundary code may import:

```python
from src.ai_youtube.apps.legacy_pipeline.adapter import main
```

The root facade, legacy engines, output locations, configuration, projects,
and media are not moved or rewritten.

## Consequences

1. The legacy pipeline has one explicit canonical application adapter without
   a duplicate dispatcher, workflow, engine, or persisted contract.
2. Root imports, command behavior, module patch points, and the old app wrapper
   remain compatible.
3. Documentary and fixed-production-plan code remain behind the compatibility
   facade until their own separately approved vertical slice.
4. Runtime migration, compatibility retirement, provider calls, TTS, and
   rendering are outside this decision.

## Verification

```powershell
$env:PYTHONUTF8='1'
.\venv\Scripts\python.exe -m unittest tests.test_legacy_pipeline_application_boundary tests.test_legacy_pipeline_internals_contract tests.test_stage1_characterization.LegacyPipelineCliContractTests tests.test_apps_structure
.\venv\Scripts\python.exe -m unittest tests.test_stage3_workspace_paths tests.test_production_catalog_foundation.ProductionCatalogCliTests tests.test_semantic_visual_evaluation_internals_contract
.\venv\Scripts\python.exe -m compileall -q src/ai_youtube/apps/legacy_pipeline apps/youtube_pipeline pipeline.py src/legacy_pipeline tests/test_legacy_pipeline_application_boundary.py
.\venv\Scripts\python.exe -m tools.qa.check_agent_docs
```
