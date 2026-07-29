---
status: current
last_verified_commit: b9f8212
last_verified_date: 2026-07-29
source_paths:
  - ai_youtube
  - src/ai_youtube/cli
  - pipeline.py
  - src/config_resolver/paths.py
  - src/content_creation
  - src/content_creation/wizard.py
  - src/content_creation/wizard_state.py
  - src/content_creation/wizard_steps.py
  - src/content_creation/wizard_presentation.py
  - src/news
  - src/news/asset_manager.py
  - src/news/asset_manifest_builder.py
  - src/news/asset_manifest_summaries.py
  - src/news/asset_scene_completion.py
  - src/news/asset_provider_adapters.py
  - src/projects
  - src/project_foundation
  - schemas/job.schema.json
  - src/assets
  - src/providers
  - src/audio
  - src/subtitles
  - anime_factory
  - docs/current/ARCHITECTURE_BOUNDARY_MAP.md
  - docs/current/CLEANUP_REGISTRY.md
  - docs/adr/0006-news-stage-idempotency.md
  - tests/test_news_asset_manager_contract.py
  - tests/test_cli_internals_contract.py
  - tests/test_wizard_internals_contract.py
  - tests/test_news_stage_idempotency.py
---

# System Map

Код и Git имеют приоритет. Карта описывает существующие границы, а не разрешает
массовое перемещение.

| Область | Текущий авторитет | Роль |
|---|---|---|
| Пути и workspace | `src/config_resolver/paths.py` | единый resolver versioned resources, runtime roots и legacy fallback |
| Канонический CLI | `ai_youtube/`, `src/ai_youtube/cli/`, `src/content_creation/commands/` | dispatcher, domain handlers, parser modules и terminal presentation |
| Создание контента | `src/content_creation/` | compatibility CLI, wizard и application service |
| Fullscreen workflow | `src/news/` | staged `news_to_short`, resume и render |
| Story Card | `src/templates/story_card/`, `src/production_plan/` | workflow adapter и renderer |
| Проекты | `src/projects/`, `src/project_foundation/`, `src/news/project_store.py` | общий read API, atomic storage/lock primitives и output-validated news stage state |
| Ассеты | `src/assets/`, `src/news/asset_*.py` | shared selection/preview/completion contracts и app-specific manifest orchestration/adapters |
| Providers | `src/providers/` | provider adapters и общий contract |
| Голос | `src/audio/`, `src/localization/` | approval, manifests, timeline и voice resolution |
| Субтитры | `src/subtitles/` | единственный subtitle engine |
| Legacy/maintenance | `pipeline.py`, `apps/` | compatibility entrypoints |
| Video repurposing | `anime_factory/` | отдельный существующий Anime Factory workflow |

Текущая продуктовая модель:

```text
content_creator
  ├─ fullscreen_voiceover_v1
  └─ story_card_text_only_v1

video_repurposer
  └─ planned/disabled (Anime Factory ещё не перенесён под этот app boundary)
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
builder или lazy CLI → Wizard boundary. Следующий отдельный подэтап — 6D.
