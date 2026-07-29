---
status: current
last_verified_commit: 01cfc6f
last_verified_date: 2026-07-29
source_paths:
  - AGENTS.md
  - docs/handoff/PROJECT_RESCUE_MASTER_PLAN.md
  - docs/current/ARCHITECTURE_BOUNDARY_MAP.md
  - docs/current/CLEANUP_REGISTRY.md
  - ai_youtube/cli/main.py
  - src/ai_youtube/cli
  - src/config_resolver/paths.py
  - src/content_creation/cli.py
  - src/content_creation/wizard.py
  - src/content_creation/wizard_state.py
  - src/content_creation/wizard_steps.py
  - src/content_creation/wizard_presentation.py
  - src/content_creation/service.py
  - src/content_creation/service_support.py
  - src/content_creation/story_card_use_case.py
  - src/content_creation/fullscreen_voiceover_use_case.py
  - src/ai_youtube/apps/content_creator/workflows/fullscreen_voiceover
  - src/ai_youtube/apps/content_creator/workflows/story_card
  - src/assets/semantic_visual_evaluation.py
  - src/assets/semantic_visual_evaluation_runtime.py
  - src/assets/semantic_visual_evaluation_tooling.py
  - src/assets/frame_primitives.py
  - src/assets/frame_sampling.py
  - src/assets/perceptual_similarity.py
  - src/assets/provider_contract.py
  - pipeline.py
  - src/legacy_pipeline
  - src/news/asset_manager.py
  - src/news/asset_manifest_builder.py
  - src/news/asset_manifest_summaries.py
  - src/news/asset_scene_completion.py
  - src/news/asset_provider_adapters.py
  - src/news/stock_video_downloader.py
  - src/news/project_store.py
  - src/providers/registry.py
  - docs/adr/0008-canonical-provider-registry.md
  - docs/adr/0009-fullscreen-voiceover-application-boundary.md
  - docs/adr/0010-story-card-application-boundary.md
  - tests/test_news_asset_manager_contract.py
  - tests/test_cli_internals_contract.py
  - tests/test_wizard_internals_contract.py
  - tests/test_content_creation_service_internals_contract.py
  - tests/test_semantic_visual_evaluation_internals_contract.py
  - tests/test_legacy_pipeline_internals_contract.py
  - tests/test_asset_import_boundaries.py
  - tests/test_news_stage_idempotency.py
  - tests/test_fullscreen_voiceover_application_boundary.py
  - tests/test_story_card_application_boundary.py
---

# Start Here

AI-YouTube — локальная offline-first система производства Shorts. Код и Git имеют
приоритет над этим документом.

Для начала работы достаточно:

1. Прочитать [AGENTS.md](../../AGENTS.md).
2. Проверить Git указанными там read-only командами.
3. Прочитать [CURRENT_STATE.md](CURRENT_STATE.md). Открывать
   [SYSTEM_MAP.md](SYSTEM_MAP.md) только для архитектурной задачи.

Текущий rescue plan: [PROJECT_RESCUE_MASTER_PLAN.md](../handoff/PROJECT_RESCUE_MASTER_PLAN.md).
Этапы 0–7 завершены. В этапе 8 vertical slices `fullscreen_voiceover`
(`f8ac67e`, `06e6a25`) и `story_card` (`01cfc6f`) завершены: canonical
application boundaries находятся в
`src.ai_youtube.apps.content_creator.workflows`, а прежние use-case paths
сохранены wrappers. Следующий slice этапа 8 — `anime_clipper` через
`video_repurposer` adapter.
Подробная проверенная карта зависимостей находится в
[ARCHITECTURE_BOUNDARY_MAP.md](ARCHITECTURE_BOUNDARY_MAP.md), а решения по
кандидатам cleanup — в [CLEANUP_REGISTRY.md](CLEANUP_REGISTRY.md).
Исторические handoff и отчёты находятся в [docs/archive](../archive/README.md) и не
являются текущим источником истины.

Безопасная проверка интерфейса:

```powershell
.\venv\Scripts\python.exe -m ai_youtube capabilities --json
```

`python -m ai_youtube` — канонический CLI. `python -m src.content_creation.cli`,
`pipeline.py` и `apps/*` сохранены как compatibility entrypoints.

Для отдельного runtime workspace используй глобальный `--workspace`, переменную
`AI_YOUTUBE_WORKSPACE` или path config. Без явной настройки legacy workspace остаётся
корнем репозитория; физическая миграция runtime ещё не выполнялась.

Не запускай сеть, providers, Vision, TTS, скачивание или платные действия без
отдельного разрешения пользователя.
