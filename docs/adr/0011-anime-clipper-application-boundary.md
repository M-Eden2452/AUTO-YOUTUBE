# ADR 0011: Anime Clipper application boundary

## Status

Accepted on 2026-07-29 as the third vertical slice of rescue stage 8.

## Context

The working local-video clipping workflow, CLI parser, episode layout, and
output paths are owned by `anime_factory`. The compatibility entrypoint
`python -m apps.anime_factory` delegates directly to that package, while the
production catalog honestly keeps `video_repurposer` planned and disabled.

Physically moving the Anime Factory modules or introducing another episode
manifest, output writer, renderer, or CLI would exceed this bounded slice and
risk existing direct imports and runtime folders.

## Decision

- The canonical adapter boundary is
  `src.ai_youtube.apps.video_repurposer.workflows.anime_clipper`.
- It lazily re-exports the existing `parse_args`, `run_pipeline`, and `main`
  workflow functions from `anime_factory.pipeline`.
- It also re-exports the existing `EpisodePaths`, `PROJECT_ROOT`, and
  `get_episode_paths` project/output contracts from
  `anime_factory.modules.paths`.
- `apps.anime_factory` remains the compatibility entrypoint and now resolves
  the workflow through the canonical adapter.
- `anime_factory` remains the sole owner of workflow behavior, episode
  directories, intermediate artifacts, reports, previews, and rendered output.
- `video_repurposer` remains planned and disabled; this migration boundary does
  not advertise the application as ready.

## Compatibility and migration

Existing imports continue to work:

```python
from anime_factory.pipeline import main, parse_args, run_pipeline
from anime_factory.modules.paths import EpisodePaths, get_episode_paths
```

New application-boundary code may import:

```python
from src.ai_youtube.apps.video_repurposer.workflows.anime_clipper import (
    EpisodePaths,
    get_episode_paths,
    run_pipeline,
)
```

The direct `python anime_factory/pipeline.py` command and
`python -m apps.anime_factory` compatibility command remain available. Existing
`anime_factory/episodes` runtime data is not moved or rewritten.

## Consequences

1. Anime Clipper has one explicit application adapter without a duplicate
   workflow or project/output contract.
2. Direct legacy imports and the old app wrapper remain compatible.
3. Catalog status remains honest until a separately approved product slice
   supplies a supported service/template contract.
4. Runtime migration, network access, transcription, FFmpeg execution, preview
   generation, and rendering are outside this decision.

## Verification

```powershell
$env:PYTHONUTF8='1'
.\venv\Scripts\python.exe -m unittest tests.test_anime_clipper_application_boundary tests.test_stage1_characterization.AnimeFactoryCliContractTests tests.test_apps_structure tests.test_production_catalog_foundation.ProductionCatalogModelTests.test_video_repurposer_registered_planned_and_disabled
.\venv\Scripts\python.exe -m unittest tests.test_anime_factory_paths tests.test_anime_factory_cleanup tests.test_anime_factory_candidates tests.test_anime_factory_dynamic_crop tests.test_anime_factory_transcribe tests.test_anime_factory_v3 tests.test_anime_factory_v4
.\venv\Scripts\python.exe -m compileall -q src/ai_youtube/apps/video_repurposer apps/anime_factory anime_factory tests/test_anime_clipper_application_boundary.py
.\venv\Scripts\python.exe -m tools.qa.check_agent_docs
```
