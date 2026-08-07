---
status: current
last_verified_commit: 8c60295
last_verified_date: 2026-08-07
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
  - src/ai_youtube/apps/legacy_pipeline
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
  - src/projects
  - src/project_foundation
  - schemas/job.schema.json
  - src/assets
  - src/providers
  - src/providers/registry.py
  - src/runtime_network.py
  - src/production_plan/youtube_shorts.py
  - src/production_plan/solar_vs_nuclear_render.py
  - src/audio
  - src/music_engine.py
  - src/music_finder.py
  - src/music_tools.py
  - src/subtitles
  - anime_factory
  - apps/anime_factory
  - apps/youtube_pipeline
  - docs/current/ARCHITECTURE_BOUNDARY_MAP.md
  - docs/current/CLEANUP_REGISTRY.md
  - docs/adr/0006-news-stage-idempotency.md
  - docs/adr/0008-canonical-provider-registry.md
  - docs/adr/0009-fullscreen-voiceover-application-boundary.md
  - docs/adr/0010-story-card-application-boundary.md
  - docs/adr/0011-anime-clipper-application-boundary.md
  - docs/adr/0012-legacy-pipeline-application-boundary.md
  - docs/adr/0013-documentary-migration-gate.md
  - docs/adr/0014-retire-news-provider-class-compatibility.md
  - docs/adr/0015-retire-news-stock-downloader.md
  - docs/adr/0016-two-engine-product-architecture.md
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
  - tests/test_legacy_pipeline_application_boundary.py
  - tests/test_documentary_migration_gate.py
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
| Runtime network | `src/runtime_network.py` | единственный владелец разрешения на сетевое действие: default deny, поимённые классы, проверка до первого socket/HTTP |
| Audio/music | `src/audio/`, `src/localization/`, legacy `src/music_*` | canonical voice/TTS manifests/timeline; music ownership ещё требует 9B consolidation |
| Субтитры | `src/subtitles/` | единственный subtitle engine |
| Legacy/maintenance | `src/ai_youtube/apps/legacy_pipeline/`, `pipeline.py`, `src/legacy_pipeline/`, `apps/youtube_pipeline/` | canonical lazy adapter, root compatibility namespace, parser, maintenance handlers и legacy workflow |
| Video repurposing | `src/ai_youtube/apps/video_repurposer/workflows/anime_clipper/`, `anime_factory/` | canonical lazy adapter и существующий владелец Anime Factory workflow/project-output layout |

Текущая продуктовая модель:

```text
content_creator
  ├─ fullscreen_voiceover_v1
  └─ story_card_text_only_v1

video_repurposer
  └─ planned/disabled (Anime Clipper adapter существует, product capability не включён)
```

Целевая модель ADR 0016: два application engines поверх общих services.
`content_creator` создаёт short/long; `video_repurposer` обобщает существующий
Anime Factory для Anime/stream/film/podcast source videos. Documentary — future
template/workflow `content_creator`, не третье приложение. Это target boundary:
repurposer остаётся disabled до migration и evidence.

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
- `src.ai_youtube.apps.legacy_pipeline.adapter` лениво переэкспортирует root
  command/workflow surface; `apps.youtube_pipeline` использует эту canonical
  boundary, а root `pipeline.py` остаётся владельцем compatibility namespace
  и engine patch-points.
- `src.providers.registry` владеет default automatic provider set активного
  workflow. News factory делегирует registry; D01 news-only provider names
  удалены после zero-caller audit. D02 standalone downloader также удалён после
  отдельного imports/entrypoint gate; active asset stage остаётся в
  `src.news.asset_manager`.
- `src.ai_youtube.apps.video_repurposer.workflows.anime_clipper` лениво
  переэкспортирует существующие workflow и `EpisodePaths` contracts из
  `anime_factory`; `apps.anime_factory` использует эту canonical boundary, но
  catalog остаётся planned/disabled.

`docs/implementation/` — каталог implementation evidence и истории capabilities,
а не источник текущих границ: индекс и статусы находятся в
[docs/implementation/README.md](../implementation/README.md), и ни один документ
оттуда не переопределяет эту карту, ADR или код.

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
Четвёртый slice этапа 8 (`cfe6ae6`) создал canonical legacy pipeline adapter,
перевёл `apps.youtube_pipeline` на новую boundary и сохранил root `pipeline.py`
владельцем compatibility namespace, а `src.legacy_pipeline` — владельцем
parser/maintenance/workflow behavior. Gate 8E (`a3536a9`) подтвердил отсутствие
реального documentary catalog template: `longform` остаётся disabled без
шаблона, legacy documentary channels не поддерживаются `content_creator`, а
Solar fixed plan использует отдельный `project_config.json`/`scenes.json`
contract и прямые live provider/TTS paths без application approval boundary.
Documentary migration не выполнялась, этап 8 boundary migration закрыт.
Ownership `src.news`, `src.templates.story_card`, `anime_factory`,
`pipeline.py` и `src.legacy_pipeline` при этом не считался физически
перенесённым. Этап 9A завершил D01/D02 compatibility retirement и D03 placeholder deletion.
9B-P01 зафиксировал два target engines ADR 0016 без изменения catalog status. Единого шага
«9B-C01» больше нет: read-only ownership/caller gates разделены на PLAN-1A, PLAN-1B и PLAN-1C′,
и до их закрытия move/delete package roots, wrappers, Anime project/transcription/subtitle/render
modules и legacy/shared music paths запрещены. PLAN-STAB-1 (`f0b69db`), PLAN-STAB-2 (`0eea5be`) и
PLAN-STAB-3 (`9222519`) завершены: атомарный final-output promotion, resume/explicit `stage=` skip
для завершённого `final_render` и восстанавливающий `network_guard_scope()`/credential isolation
соответственно; review-verdicts ACCEPT WITH MINOR, ACCEPT, ACCEPT WITH MINOR, все три commit pushed
(owner-provided evidence, не отдельный Git commit). PLAN-STAB-4 completed 2026-08-06, independently reviewed (verdict ACCEPT WITH MINOR): разрешение на рантайм-сеть получило единственного владельца (строка «Runtime network» выше), провайдеры не менялись и второй guard на провайдера не создавался, network approval отделён от paid approval. PLAN-STAB-5 (C50 rights-review preservation) completed 2026-08-06, independently reviewed (verdict ACCEPT). PLAN-STAB-7 и PLAN-STAB-8 (routing/reference integrity + Git-aware docs freshness) closed 2026-08-06: implementation commit `42fa741`, repair commit `8357402` закрыл все четыре finding F1-F4 независимого review без изменения контрактов; independent review verdict ACCEPT WITH MINOR, repair re-review verdict ACCEPT WITH MINOR (blocking findings: 0); CI run `31101208366` и repair run `31110155685` оба зелёные; пункт 7 blocking gate satisfied, PLAN-ID и contracts остаются раздельными. Canonical owner routing- и freshness-проверок — `tools/qa/check_agent_docs.py`, второй QA framework не создавался, а `.github/workflows/offline-tests.yml` получил `fetch-depth: 0` в существующем checkout, чтобы CI мог разрешать commit ancestry. PLAN-STAB-6 (Claude permission hardening) closed 2026-08-07: repair `b0a3547` закрыл review findings F1-F5, independent re-review verdict ACCEPT WITH MINOR (blocking findings: 0), GitHub Actions run `31147454618` зелёный (1749 tests OK, failures=0, errors=0); пункт 6 blocking gate satisfied. Versioned `.claude/settings.json` остаётся deny/ask-only без `permissions.allow`, governance-зоны и project-local settings закрыты подтверждением или deny, а contract-владелец — тот же `tools/qa/check_agent_docs.py` (`validate_claude_permissions`), второй QA framework не создавался; matcher semantics и path-обход через Bash закрытыми не считаются. PLAN-9B-2 (expansion + hardcode migration) closed 2026-08-07: implementation commit `66fd2431`, independent review verdict ACCEPT WITH MINOR (blocking findings 0), implementation CI run `31164020130` зелёный (1772 tests OK); repair commit `8c60295` закрыл review finding F1 (must_avoid punctuation bypass в query expansion), independent re-review verdict ACCEPT (findings 0), repair CI run `31172361739` зелёный. F2 (non-provider-language must_avoid без translator) — recorded non-blocking limitation, `TranslatorService` не создавался. Текущий checkpoint — **PLAN-9B-3** (query-path cleanup) по owner-approved active execution route: pending / not started, единственный оставшийся prerequisite — отдельный owner-issued implementation prompt по существующему PLAN-9B-3 contract. Bounded owner-driven stabilization review результатов PLAN-STAB-1..9 (пункт 8 blocking gate) завершён 2026-08-07 read-only, verdict CLEAR TO PROCEED TO PLAN-9B-2, blocking findings 0, предварительный архитектурный repair не требуется; stabilization gate пройден целиком. PLAN-STAB-9 (non-blocking follow-up) closed 2026-08-06: implementation completed, independently reviewed, verdict ACCEPT WITH MINOR (non-blocking wording finding, исправлен). Словарь допустимых `rights_status` получил единственного владельца `src/assets/models.py` (immutable `RIGHTS_ALLOWED_STATUSES`); независимая копия `ALLOWED_RENDER_RIGHTS` в `src/news/models.py` удалена, её import paths сохранены как compatibility re-exports того же объекта, а единственное санкционированное расширение `cleared` осталось локальным для render-gate `completion/modes.py`. Словарь задаёт написание статуса, а не право: авторитет прав по-прежнему `src/assets/license_policy.py`. PLAN-9B-2 deferred за post-audit stabilization gate. CI repair (`9f9b6f2`, `bcf6c2a`, `8ca755f`, `68acdb2`) вернул `.github/workflows/offline-tests.yml`
в зелёное состояние (GitHub Actions run `31039985187`, 1/1 checks, OK; local suite — 1589 тестов, OK);
PLAN-STAB-16 частично выполнена — green CI baseline готов, остальное pending/non-blocking. Финальная цель — один physical `src/ai_youtube` package и один owner business logic на capability; это цель плана, а не текущее состояние кода.
