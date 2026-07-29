---
status: current
last_verified_commit: 7d0ce1e
last_verified_date: 2026-07-29
source_paths:
  - ai_youtube
  - src/ai_youtube/cli
  - pipeline.py
  - src/legacy_pipeline
  - src/config_resolver/paths.py
  - src/content_creation
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
  - src/ai_youtube/apps/video_repurposer/workflows/anime_clipper
  - src/assets/semantic_visual_evaluation.py
  - src/assets/semantic_visual_evaluation_runtime.py
  - src/assets/semantic_visual_evaluation_tooling.py
  - src/assets/frame_primitives.py
  - src/assets/frame_sampling.py
  - src/assets/perceptual_similarity.py
  - src/assets/provider_contract.py
  - src/news
  - src/news/asset_manager.py
  - src/news/asset_manifest_builder.py
  - src/news/asset_manifest_summaries.py
  - src/news/asset_scene_completion.py
  - src/news/asset_provider_adapters.py
  - src/news/stock_video_downloader.py
  - src/projects
  - src/project_foundation
  - schemas/job.schema.json
  - src/assets
  - src/providers
  - src/providers/registry.py
  - src/audio
  - src/subtitles
  - anime_factory
  - apps/anime_factory
  - docs/current/ARCHITECTURE_BOUNDARY_MAP.md
  - docs/current/CLEANUP_REGISTRY.md
  - docs/adr/0006-news-stage-idempotency.md
  - docs/adr/0008-canonical-provider-registry.md
  - docs/adr/0009-fullscreen-voiceover-application-boundary.md
  - docs/adr/0010-story-card-application-boundary.md
  - docs/adr/0011-anime-clipper-application-boundary.md
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
  - tests/test_anime_clipper_application_boundary.py
---

# System Map

Код и Git имеют приоритет. Карта описывает существующие границы, а не разрешает
массовое перемещение.

| Область | Текущий авторитет | Роль |
|---|---|---|
| Пути и workspace | `src/config_resolver/paths.py` | единый resolver versioned resources, runtime roots и legacy fallback |
| Канонический CLI | `ai_youtube/`, `src/ai_youtube/cli/`, `src/content_creation/commands/` | dispatcher, domain handlers, parser modules и terminal presentation |
| Создание контента | `src/content_creation/` | compatibility CLI, wizard, shared application service и use-case wrappers |
| Fullscreen application | `src/ai_youtube/apps/content_creator/workflows/fullscreen_voiceover/` | canonical application use case и переэкспорт существующих news project/workflow contracts |
| Story Card application | `src/ai_youtube/apps/content_creator/workflows/story_card/` | canonical application use case и переэкспорт существующих project/evidence/workflow contracts |
| Fullscreen workflow | `src/news/` | staged `news_to_short`, resume и render |
| Story Card | `src/templates/story_card/`, `src/production_plan/` | workflow adapter и renderer |
| Проекты | `src/projects/`, `src/project_foundation/`, `src/news/project_store.py` | общий read API, atomic storage/lock primitives и output-validated news stage state |
| Ассеты | `src/assets/`, `src/news/asset_*.py` | shared selection/preview/completion contracts и app-specific manifest orchestration/adapters |
| Semantic evaluation | `src/assets/semantic_visual_evaluation*.py` | compatibility facade, offline dataset/metrics/report tooling и controlled live runtime |
| Providers | `src/assets/provider_contract.py`, `src/providers/` | единый `StockProvider` contract, canonical registry и provider adapters |
| Голос | `src/audio/`, `src/localization/` | approval, manifests, timeline и voice resolution |
| Субтитры | `src/subtitles/` | единственный subtitle engine |
| Legacy/maintenance | `pipeline.py`, `src/legacy_pipeline/`, `apps/` | root compatibility facade, parser, maintenance handlers и legacy workflow |
| Video repurposing | `src/ai_youtube/apps/video_repurposer/workflows/anime_clipper/`, `anime_factory/` | canonical lazy adapter и существующий владелец Anime Factory workflow/project-output layout |

Текущая продуктовая модель:

```text
content_creator
  ├─ fullscreen_voiceover_v1
  └─ story_card_text_only_v1

video_repurposer
  └─ planned/disabled (Anime Clipper adapter существует, product capability не включён)
```

Ключевые переходные ограничения:

- `job.json` и `project.json` пока сосуществуют;
- `ProjectRepository` читает обе формы и legacy roots, но ничего не записывает;
- `python -m ai_youtube` — единственный канонический CLI;
- `pipeline.py`, `python -m src.content_creation.cli` и `apps/*` остаются
  compatibility entrypoints;
- default workspace остаётся корнем репозитория до отдельной физической миграции;
- произвольный workspace выбирается через CLI/env/path config, а versioned resources
  остаются привязаны к репозиторию;
- definitions и handlers CLI-команд разделены по domain-модулям; text/terminal
  rendering вынесен в общий presentation module, а старый CLI остаётся facade;
- `src.content_creation.wizard` остаётся compatibility facade с прежним
  `run_wizard`; working state/request translation, terminal presentation и
  интерактивные steps разделены по отдельным модулям.
- `src.content_creation.service` остаётся единой точкой входа
  `create_content`; request/template validation выполняет facade, а оба active
  workflow делегируются canonical boundaries
  `src.ai_youtube.apps.content_creator.workflows.fullscreen_voiceover` и
  `src.ai_youtube.apps.content_creator.workflows.story_card`.
  Старые `src.content_creation.fullscreen_voiceover_use_case` и
  `src.content_creation.story_card_use_case` остаются compatibility wrappers.
- `src.assets.semantic_visual_evaluation` остаётся public facade для root
  `pipeline.py`; offline dataset/metrics/reporting находятся в
  `semantic_visual_evaluation_tooling`, а gated execution —
  в `semantic_visual_evaluation_runtime`.
- root `pipeline.py` остаётся compatibility facade и сохраняет старые imports
  и patch-points; parser, maintenance handlers и legacy channel/video
  orchestration разделены в `src.legacy_pipeline`.
- `src.providers.registry` владеет default automatic provider set активного
  workflow. News factory делегирует registry; старые news-only provider names
  и `stock_video_downloader` остаются compatibility surface до этапа 9.
- `src.ai_youtube.apps.video_repurposer.workflows.anime_clipper` лениво
  переэкспортирует существующие workflow и `EpisodePaths` contracts из
  `anime_factory`; `apps.anime_factory` использует эту canonical boundary, но
  catalog остаётся planned/disabled.

Этап 4.6 завершил read-only инвентаризацию. Полные callers/tests, persisted
contracts и runtime roots зафиксированы в
[ARCHITECTURE_BOUNDARY_MAP.md](ARCHITECTURE_BOUNDARY_MAP.md); классификация
`keep/split/merge/move/archive/delete/do_not_touch`, delete evidence и очередь
малых slices — в [CLEANUP_REGISTRY.md](CLEANUP_REGISTRY.md). Slice 5A перевёл
`NewsProjectStore` на существующий atomic write primitive без создания нового
storage layer. Slice 5B добавил additive news schema version v1: новые записи
версионированы, а старые `job.json` без поля читаются как v1 без массовой
миграции. Slice 5C добавил общий fail-fast project-lock primitive и применил его
к `NewsProjectStore.write_json`; stale lock старше пяти минут перехватывается
автоматически. Этап 5 завершён: bounded slices 5D добавили output-validated
stage idempotency для всех повторяемых downstream-семейств от `research` до
`export`, сохранив legacy asset/voice/subtitle manifests и protected user
subtitles. `input` и потенциально сетевой `article_ingestion` не включены в
автоматическую retry-policy по ADR 0006. Подэтап 6A разделил
`src/news/asset_manager.py` на compatibility facade, manifest builder, чистые
summary/coverage-расчёты, scene completion и provider search/download adapters.
Существующий `src.assets.provider_contract` и старые import/patch points сохранены.
Подэтап 6B разделил canonical CLI internals на catalog,
localization/subtitles и authoring handlers, оставил 78-строчный diagnostics
facade и вынес terminal formatting в `src/ai_youtube/cli/presentation.py`.
Подэтап 6C оставил `src/content_creation/wizard.py` 175-строчным compatibility
facade и вынес state/request translation, terminal presentation/adapters и
steps/execution orchestration в отдельные модули без изменения общего request
builder или lazy CLI → Wizard boundary. Подэтап 6D оставил
`src/content_creation/service.py` 123-строчным facade и отделил use cases Story
Card и Fullscreen Voiceover; paid gate, tolerant resume и progress callback
сохранены. Подэтап 6E оставил semantic evaluation 53-строчным facade и отделил
offline tooling от controlled live runtime без нового engine или изменения
root-pipeline import. Подэтап 6F оставил root `pipeline.py` 122-строчным
compatibility facade и отделил parser, maintenance handlers и legacy
channel/video workflow без изменения public command contract или patch-points.
Подэтап 6G вынес `SampledFrame`, file SHA-256 и perceptual image hash в
`src.assets.frame_primitives`; прежние импорты из `frame_sampling`,
`perceptual_similarity` и `src.assets` сохранены, а встречные static edges
между sampling и similarity устранены. Этап 7 перенёс default provider factory
в `src.providers.registry`, закрепил `StockProvider` единственным canonical
contract и удалил недостижимый raw-HTTP дубль из standalone downloader,
сохранив его публичный wrapper. Первый slice этапа 8 (`f8ac67e`, `06e6a25`) перенёс
application-level Fullscreen Voiceover use case в canonical app boundary,
оставил прежний import path wrapper и переиспользовал без дублирования
`NewsJob`, `NewsProjectStore` и `src.news.pipeline`; service import сохраняет
прежнюю lazy pipeline boundary. Второй slice этапа 8 (`01cfc6f`) перенёс
application-level Story Card use case в соседний canonical boundary, сохранил
старый import path wrapper и переиспользовал без дублирования `ProjectFactory`,
`ProjectManifest`, `EvidenceBundle` и `src.templates.story_card`. Третий slice
этапа 8 (`7d0ce1e`) создал canonical Anime Clipper adapter, сохранил
`anime_factory` владельцем workflow и output layout и перевёл
`apps.anime_factory` на новую boundary без включения `video_repurposer`.
Следующий slice этапа 8 — legacy pipeline.
