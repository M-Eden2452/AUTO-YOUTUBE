---
status: current
last_verified_commit: fe5ba44
last_verified_date: 2026-07-29
source_paths:
  - pyproject.toml
  - ai_youtube
  - apps
  - anime_factory
  - pipeline.py
  - src
  - schemas
  - tests
  - docs/handoff/PROJECT_RESCUE_MASTER_PLAN.md
---

# Architecture Boundary Map

Проверено 2026-07-29 по implementation HEAD `fe5ba44`. Код и Git имеют приоритет.
Карта создана read-only инвентаризацией этапа 4.6 и актуализирована после bounded
stage 5 closure и подэтапа 6A; это не разрешение на массовое перемещение файлов.

## Снимок дерева

Команда `rg --files ai_youtube src apps anime_factory tests` показала:

- 262 production-файла в `ai_youtube/`, `src/`, `apps/`, `anime_factory/`;
- 254 production Python-файла: `ai_youtube` — 6, `apps` — 10,
  `anime_factory` — 18, `src` — 220;
- 101 модуль `tests/test_*.py`;
- крупнейшие модули: `src/assets/semantic_visual_evaluation.py` — 1719 строк,
  `src/news/asset_manifest_builder.py` — 1413 строк с короткими
  orchestration-методами,
  `src/content_creation/wizard.py` — 1229,
  `src/content_creation/service.py` — 878, `pipeline.py` — 703.
  Compatibility facade `src/news/asset_manager.py` — 266 строк;
  `src/content_creation/cli.py` — 75 строк после structural migration.

Основные области внутри `src/`:

| Область | Python-файлов | Фактическая роль |
|---|---:|---|
| `assets` | 43 | contracts, selection, download, preview, completion и semantic tooling |
| `content` | 27 | script engine и visual planning |
| `audio` | 21 | TTS contract, voice workflow, manifests и timeline |
| `news` | 23 | fullscreen voiceover workflow, split asset orchestration и `job.json` writer |
| `content_creation` | 16 | CLI/Wizard/application service |
| `providers` | 10 | adapters общего asset provider contract |
| `subtitles` | 9 | единый subtitle engine |
| `project_foundation` | 9 | `project.json`, evidence и atomic storage |
| `config_resolver` | 7 | versioned resources и runtime workspace |
| `production_catalog` | 5 | applications/formats/templates/export targets |
| `projects` | 3 | общий read-only project API и rights report |

## Entrypoints и compatibility

| Entrypoint | Статус | Dispatch |
|---|---|---|
| `ai-youtube`, `python -m ai_youtube` | канонический | `ai_youtube.cli.main` → `src.content_creation.cli` |
| `python -m src.content_creation.cli` | compatibility | тот же parser/service active app |
| `pipeline.py` | legacy/maintenance compatibility | старые documentary/media/diagnostic команды и `news_to_short` |
| `python -m apps.news_to_short` | compatibility | прямой adapter к `src.news.pipeline` |
| `python -m apps.youtube_pipeline` | compatibility | тонкий вызов root `pipeline.py` |
| `python -m apps.anime_factory` | compatibility | adapter к `anime_factory.pipeline` |
| `python -m src.project_foundation.cli` | maintenance | project/channel foundation CLI |

`pyproject.toml` публикует только `ai-youtube`. Остальные entrypoints сохраняются
для совместимости и не являются альтернативными источниками product capability.

## Фактические application boundaries

```text
ai_youtube CLI
  -> src.content_creation.cli
     -> src.content_creation.service
        -> fullscreen_voiceover_v1
           -> src.news.pipeline
              -> NewsProjectStore -> job.json
              -> assets / audio / subtitles / renderer / export
        -> story_card_text_only_v1
           -> ProjectFactory + src.templates.story_card.integration
              -> project.json + evidence + story-card renderer

compatibility
  -> pipeline.py
  -> apps/*

planned adapter
  -> video_repurposer -> anime_factory
```

- `content_creator` — единственное active application.
- `fullscreen_voiceover_v1` и `story_card_text_only_v1` — единственные active,
  live-tested templates.
- `video_repurposer` остаётся disabled/planned; `anime_factory` ещё не перенесён
  под эту границу.
- `longform` и `horizontal_clip` не имеют active template.
- legacy documentary/size-comparison модули остаются за `pipeline.py` и не
  становятся active application только из-за наличия кода.

## Dependency и test map

| Boundary | Production callers / dependencies | Защитные тесты | Решение |
|---|---|---|---|
| `src.content_creation.cli` | canonical wrapper; вызывает service, lazy Wizard, projects и domain command modules | `test_content_creation_cli`, `test_stage1_characterization`, `test_stage3_workspace_paths`, `test_stage4_canonical_cli`, script/visual/assets/subtitle wiring | сохранить внешний contract, внутренности разделять в 6B |
| `src.content_creation.wizard` | вызывается CLI; использует service, capabilities и `ProjectRepository` | `test_content_creation_wizard`, `test_project_naming_and_resume`, localization integration | разделять state/steps/presentation в 6C |
| `src.content_creation.service` | вызывается CLI и Wizard; маршрутизирует оба active workflow | `test_content_creation_service`, Wizard/resume и Stage 4 tests | разделять use cases в 6D, не создавать второй service |
| `src.news.pipeline` | service, `apps.news_to_short`, root pipeline; управляет stage/resume/force | `test_news_to_short_pipeline`, autonomous completion, delivery, renderer, voice | сохранить fullscreen workflow boundary |
| `src.news.asset_manager` + `src.news.asset_*` | facade вызывают news pipeline, quality/draft completion и replacement summary; builder использует shared `src.assets`/`src.providers` contracts | public-contract characterization, assets, provider integration, slot-aware retrieval, semantic decisions, schema/service/pipeline tests | 6A завершён: facade, builder, summaries, completion и provider adapters разделены; imports/patch-points сохранены |
| `src.assets.semantic_visual_evaluation` | root pipeline и один выделенный test module | `test_semantic_visual_evaluation` | отделить offline evaluation/reporting от controlled live runtime в 6E |
| `src.projects.ProjectRepository` | CLI, service, Wizard, replacement и rights report | `test_project_repository`, rights report, config parity, resume | сохранить единственным read API; writer не добавлять |
| `src.news.NewsProjectStore` | news pipeline, service, voice CLI, replacement | `test_news_stage_idempotency`, news models/pipeline, service, renderer, repository tests | writer использует общий atomic primitive с 5A, schema v1 с 5B, fail-fast project lock с 5C и output validation для repeatable stages `research`–`export` с 5D |
| `src.project_foundation` | Story Card service/integration, catalog, projects/rights | project foundation/factory, Story Card integration/provenance, schemas | сохранить `project.json` owner и atomic storage |
| `src.config_resolver.paths` | CLI, apps, project stores, providers, audio/subtitles и legacy adapters | `test_stage3_workspace_paths`, config resolver/parity | сохранить единственным path/workspace resolver |
| `src.assets.provider_contract` + `src.providers` | asset manager, preview/download/diagnostics и provider adapters | provider foundation/hardening, provider integration, documentary providers | сохранить единым asset provider contract |
| `src.audio` | service, news voice/render, localization и subtitles timing | voice/narration/timeline/policy/manifest/end-tail families | сохранить approval, manifest и timing contracts |
| `src.subtitles` | adapter `src.news.subtitles`, CLI и catalog | subtitle engine + pipeline integration | сохранить единственным subtitle engine |
| `pipeline.py` | `apps.youtube_pipeline`; импортирует legacy engines, news workflow и diagnostics | Stage 1 characterization, apps structure, workspace paths, catalog | оставить facade; handlers выносить малыми slices в 6F |
| `frame_sampling` ↔ `perceptual_similarity` | top-level edge similarity → sampling и local edge sampling → similarity | visual preview foundation/integration, temporal analysis | разорвать static cycle отдельным slice 6G |

Локальный import в `frame_sampling.py:159` на
`perceptual_similarity.image_perceptual_hash` и top-level import в
`perceptual_similarity.py:10` на `SampledFrame, sha256_file` образуют
подтверждённый двунаправленный static edge. CLI ↔ Wizard cycle, отмеченный
исходным аудитом, в текущем коде уже отсутствует: направление осталось только
CLI → Wizard через lazy import.

## Persisted contracts

| Contract | Writer / reader | Версия и tolerance | Обязательная защита |
|---|---|---|---|
| `job.json` + stage state | atomic `NewsProjectStore`; `ProjectRepository` reader | `schema_version=1`; старые manifests без поля и отсутствующие optional-поля принимает `NewsJob.from_dict` | не переименовывать и не мигрировать массово; будущую версию добавлять только с tolerant reader |
| `project.json` | `ProjectFactory`; `ProjectRepository` reader | `ProjectManifest.schema_version=1` | сохранить atomic write и tolerant read |
| `assets/assets_manifest.json` | asset manager/completion | asset schema v1 и legacy normalization | сохранять provenance, license, checksum и replacement history |
| `voice_manifest.json` | `src.audio.voice_manifest` | schema v2 читает legacy v1 | не ослаблять paid approval и old-manifest compatibility |
| `subtitles_manifest.json` | `src.subtitles.manifest` | schema v2 с проверкой старых manifests | сохранить timing source и old project reads |
| evidence manifests/records | `src.project_foundation.evidence` | project schema v1, evidence record v2 | не терять rights/evidence paths |
| render/export manifests | workflow renderers/exporter | schemas в `schemas/render.schema.json`, `export.schema.json` | менять только с tolerant reader и targeted schema tests |

Каталог `schemas/` содержит восемь characterization schemas:
`job`, `project`, `stage-state`, `assets`, `voice`, `evidence`, `render`,
`export`; их проверяет `tests/test_artifact_schemas.py`.

## Runtime roots и пользовательские данные

Read-only snapshot файлов на 2026-07-28:

| Root | Tracked / всего файлов | Политика |
|---|---:|---|
| `projects/` | 0 / 1618 | `do_not_touch`; manifests/media/runtime projects |
| `outputs/` | 9 / 282 | сначала archive/verify; tracked legacy outputs всё ещё читаются legacy pipeline |
| `assets/` | 4 / 287 | `do_not_touch`; library, metadata, voice samples |
| `manual_assets/` | 7 / 18 | `do_not_touch`; пользовательские и rights-sensitive assets |
| `music/` | 1 / 3 | `do_not_touch` до проверки прав и backup |
| `content/` | 13 / 13 | versioned legacy source content; не считать мусором |
| `project_solar_vs_nuclear/` | 0 / 102 | эксперимент/runtime evidence; не удалять автоматически |
| `MOSS_TTS_Nano/` | 0 / 56463 | локальная toolchain; не читать/переносить/удалять автоматически |
| `venv/` | 0 / 12736 | локальная воспроизводимая среда, cleanup только отдельным этапом |
| `__pycache__/` | 0 / 2 | воспроизводимый cache, кандидат только этапа 10 |

`WorkspacePaths` знает `projects`, `outputs`, `exports`, `artifacts`,
`media_library`, `manual_assets`, `music`, `provider_cache`, `temp`,
`runtime_reports`, `user_config`. При отсутствии явного CLI/env/config workspace
корень репозитория остаётся legacy default; физическая миграция не выполнялась.

## Подтверждённые целевые границы

1. Сохранять нынешние import paths до отдельного vertical slice; желаемое дерево
   `core/services/infrastructure` не является самоцелью.
2. `content_creator` владеет двумя active workflows, но не их shared
   infrastructure contracts.
3. `ProjectRepository` остаётся общим read API поверх двух persisted форм;
   write convergence использует общий atomic primitive и project-lock primitive,
   а не третью schema или writer.
4. Asset providers реализуют `src.assets.provider_contract`; workflow не должен
   знать HTTP API после этапа 7.
5. Audio approval/manifests, subtitle engine и path resolver — shared services,
   которые переиспользуются, а не дублируются при переносе приложений.
6. `pipeline.py` и `apps/*` остаются compatibility zone до проверенного периода
   совместимости.
7. `anime_factory` переносится только целым workflow через
   `video_repurposer` adapter.

Следующая очередь и доказательства удаления находятся в
[CLEANUP_REGISTRY.md](CLEANUP_REGISTRY.md).
