# ADR 0009: Fullscreen Voiceover application boundary

## Status

Accepted on 2026-07-29 as the first vertical slice of rescue stage 8.

## Context

`src.content_creation.service` already delegated the
`fullscreen_voiceover_v1` template to a separate application use case, but that
use case still lived beside the compatibility CLI and Wizard modules in
`src.content_creation`. The working workflow, `job.json` model, and storage
contract are owned by `src.news`; moving that complete package in one change
would exceed the rescue-plan scope budget and risk breaking its direct
compatibility entrypoints.

The migration must establish a canonical application boundary without creating
another project model, storage layer, pipeline, provider contract, audio
service, or subtitle engine.

## Decision

- The canonical Fullscreen Voiceover application boundary is
  `src.ai_youtube.apps.content_creator.workflows.fullscreen_voiceover`.
- Its application-level orchestration lives in
  `fullscreen_voiceover/use_case.py`.
- `src.content_creation.service` imports that canonical use case.
- `src.content_creation.fullscreen_voiceover_use_case` remains a compatibility
  wrapper and re-exports the previous class, functions, signatures, and retry
  reason set.
- The boundary re-exports the existing `NewsJob`, `NewsProject`,
  `NewsProjectStore`, `NewsPipelineResult`, `create_news_to_short_job`, and
  `run_news_to_short_job` contracts. Ownership remains in `src.news`; no
  duplicate implementation or persisted schema is introduced.
- `apps.news_to_short` remains a compatibility entrypoint and resolves its
  create/run functions through the canonical application boundary.
- Root `pipeline.py` and direct `src.news` imports remain unchanged for their
  later, separately bounded rescue slices.

## Compatibility and migration

Existing imports continue to work:

```python
from src.content_creation.fullscreen_voiceover_use_case import (
    create_fullscreen_voiceover,
)
from src.news.pipeline import create_news_to_short_job, run_news_to_short_job
from src.news.project_store import NewsProjectStore
```

New application code should import:

```python
from src.ai_youtube.apps.content_creator.workflows.fullscreen_voiceover import (
    create_fullscreen_voiceover,
)
```

`job.json`, stage state, asset, voice, subtitle, render, and export contracts are
unchanged. Existing runtime projects and media are not migrated.

## Consequences

1. The active application service and `apps.news_to_short` wrapper now cross one
   explicit Fullscreen Voiceover application boundary.
2. The old use-case import path remains compatible while callers migrate.
3. `src.news` continues to own the working workflow and its persisted project
   contract until any later bounded move has independent caller evidence.
4. Story Card remains in its current boundary for the next rescue-stage slice.
5. No provider search/download, TTS, render, network, or paid action is required
   to verify this decision.

## Verification

```powershell
$env:PYTHONUTF8='1'
.\venv\Scripts\python.exe -m unittest tests.test_fullscreen_voiceover_application_boundary tests.test_content_creation_service_internals_contract tests.test_apps_structure
.\venv\Scripts\python.exe -m unittest tests.test_content_creation_service tests.test_news_to_short_pipeline tests.test_project_repository
.\venv\Scripts\python.exe -m compileall -q src/ai_youtube/apps src/content_creation/fullscreen_voiceover_use_case.py src/content_creation/service.py apps/news_to_short/main.py tests/test_fullscreen_voiceover_application_boundary.py
.\venv\Scripts\python.exe -m tools.qa.check_agent_docs
```
