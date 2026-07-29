---
status: current
last_verified_commit: a3536a9
last_verified_date: 2026-07-29
source_paths:
  - pyproject.toml
  - ai_youtube
  - apps
  - anime_factory
  - src/ai_youtube/apps/video_repurposer/workflows/anime_clipper
  - src/ai_youtube/apps/legacy_pipeline
  - pipeline.py
  - src/production_plan/youtube_shorts.py
  - src/production_plan/solar_vs_nuclear_render.py
  - src
  - schemas
  - tests
  - tests/test_anime_clipper_application_boundary.py
  - tests/test_legacy_pipeline_application_boundary.py
  - tests/test_documentary_migration_gate.py
  - docs/adr/0011-anime-clipper-application-boundary.md
  - docs/adr/0012-legacy-pipeline-application-boundary.md
  - docs/adr/0013-documentary-migration-gate.md
  - docs/handoff/PROJECT_RESCUE_MASTER_PLAN.md
---

# Architecture Boundary Map

Проверено 2026-07-29 по gate HEAD `a3536a9`. Код и Git имеют приоритет.
Карта создана read-only инвентаризацией этапа 4.6 и актуализирована после bounded
stage 5 closure, подэтапов 6A–6G, этапа 7 и завершения этапа 8;
это не разрешение на массовое перемещение файлов.

## Снимок дерева

Команда `rg --files ai_youtube src apps anime_factory tests` показала:

- 292 production-файла в `ai_youtube/`, `src/`, `apps/`, `anime_factory/`;
- 284 production Python-файла: `ai_youtube` — 6, `apps` — 10,
  `anime_factory` — 18, `src` — 250;
- 112 модулей `tests/test_*.py`;
- крупнейшие модули: `src/news/asset_manifest_builder.py` — 1413 строк с короткими
  orchestration-методами,
  `src/assets/semantic_visual_evaluation_runtime.py` — 1000 строк и
  `src/assets/semantic_visual_evaluation_tooling.py` — 982 строки без функций
  длиннее 68 строк,
  `src/content_creation/wizard_steps.py` — 939 строк без функций длиннее
  111 строк,
  canonical
  `src/ai_youtube/apps/content_creator/workflows/fullscreen_voiceover/use_case.py`
  — 906 строк без методов длиннее 93 строк.
  Compatibility facade `src/news/asset_manager.py` — 266 строк;
  `src/content_creation/wizard.py` — 175 строк;
  `src/content_creation/service.py` — 123 строки;
  `src/content_creation/fullscreen_voiceover_use_case.py` — 29 строк;
  canonical Story Card use case — 155 строк, его compatibility wrapper —
  12 строк;
  root `pipeline.py` — 122 строки;
  `src/assets/semantic_visual_evaluation.py` — 53 строки;
  canonical diagnostics facade — 78 строк, `src/content_creation/cli.py` —
  81 строка после восстановления compatibility patch-point.

Основные области внутри `src/`:

| Область | Python-файлов | Фактическая роль |
|---|---:|---|
| `assets` | 46 | contracts, selection, download, preview, completion и split semantic tooling/runtime |
| `content` | 27 | script engine и visual planning |
| `audio` | 21 | TTS contract, voice workflow, manifests и timeline |
| `news` | 23 | fullscreen voiceover workflow, split asset orchestration и `job.json` writer |
| `content_creation` | 22 | compatibility CLI/Wizard, shared application service и два use-case wrappers |
| `ai_youtube/apps` | 12 | canonical boundaries для Fullscreen Voiceover, Story Card, Anime Clipper и legacy pipeline adapters |
| `providers` | 11 | canonical registry и adapters общего asset provider contract |
| `subtitles` | 9 | единый subtitle engine |
| `project_foundation` | 9 | `project.json`, evidence и atomic storage |
| `config_resolver` | 7 | versioned resources и runtime workspace |
| `production_catalog` | 5 | applications/formats/templates/export targets |
| `projects` | 3 | общий read-only project API и rights report |
| `legacy_pipeline` | 4 | parser, maintenance handlers и legacy channel/video orchestration за root facade |

## Entrypoints и compatibility

| Entrypoint | Статус | Dispatch |
|---|---|---|
| `ai-youtube`, `python -m ai_youtube` | канонический | `src.ai_youtube.cli.main` → domain command handlers |
| `python -m src.content_creation.cli` | compatibility | тот же parser/handlers active app с legacy patch-points |
| `pipeline.py` | legacy/maintenance compatibility | старые documentary/media/diagnostic команды и `news_to_short` |
| `python -m apps.news_to_short` | compatibility | adapter через canonical Fullscreen Voiceover boundary к `src.news.pipeline` |
| `python -m apps.youtube_pipeline` | compatibility | canonical legacy adapter → root `pipeline.py` |
| `python -m apps.anime_factory` | compatibility | canonical Anime Clipper adapter → `anime_factory.pipeline` |
| `python -m src.project_foundation.cli` | maintenance | project/channel foundation CLI |

`pyproject.toml` публикует только `ai-youtube`. Остальные entrypoints сохраняются
для совместимости и не являются альтернативными источниками product capability.

## Фактические application boundaries

```text
ai_youtube CLI
  -> src.ai_youtube.cli.main
     -> create / project / assets / diagnostics facade
        -> catalog / localization / authoring handlers
        -> terminal presentation
     -> src.content_creation.service facade
        -> src.ai_youtube.apps.content_creator.workflows.fullscreen_voiceover
           -> use_case
           -> src.news.pipeline
              -> NewsProjectStore -> job.json
              -> assets / audio / subtitles / renderer / export
        -> src.ai_youtube.apps.content_creator.workflows.story_card
           -> use_case
           -> ProjectFactory + src.templates.story_card.integration
              -> project.json + evidence + story-card renderer

compatibility
  -> src.content_creation.cli
  -> src.content_creation.fullscreen_voiceover_use_case
  -> src.content_creation.story_card_use_case
  -> apps.news_to_short
  -> apps.youtube_pipeline
     -> canonical legacy_pipeline adapter
        -> pipeline.py
           -> src.legacy_pipeline.cli / maintenance / workflow
  -> remaining apps/*

planned/disabled application
  -> video_repurposer
     -> canonical anime_clipper adapter
        -> anime_factory
```

- `content_creator` — единственное active application.
- `fullscreen_voiceover_v1` и `story_card_text_only_v1` — единственные active,
  live-tested templates.
- `video_repurposer` остаётся disabled/planned; canonical Anime Clipper adapter
  существует, но не включает product capability и сохраняет `anime_factory`
  владельцем workflow/output contracts.
- `longform` и `horizontal_clip` не имеют active template.
- legacy documentary/size-comparison модули остаются за `pipeline.py` и не
  становятся active application только из-за наличия кода.
- gate 8E подтвердил, что Solar fixed plan также не является template:
  `project_config.json`/`scenes.json` не входят в два canonical project
  contracts, а live render path не имеет application-level paid/provider gate.

## Dependency и test map

| Boundary | Production callers / dependencies | Защитные тесты | Решение |
|---|---|---|---|
| `src.ai_youtube.cli` + `src.content_creation.cli` | canonical dispatcher/domain handlers и legacy facade; вызывают service, lazy Wizard, projects и shared presentation | `test_cli_internals_contract`, `test_content_creation_cli`, `test_stage1_characterization`, `test_stage3_workspace_paths`, `test_stage4_canonical_cli`, script/visual/assets/subtitle wiring | 6B завершён: command/output contract и patch-points сохранены, handlers/presentation разделены |
| `src.content_creation.wizard` + `wizard_state`/`wizard_steps`/`wizard_presentation` | facade вызывается CLI; steps используют service, capabilities и `ProjectRepository`, state делегирует общему request builder | `test_wizard_internals_contract`, `test_content_creation_wizard`, `test_project_naming_and_resume`, localization integration | 6C завершён: `run_wizard`, compatibility imports, request-builder patch-point и lazy CLI boundary сохранены |
| `src.content_creation.service` + `service_support` | единый facade вызывается CLI и Wizard; facade валидирует request/template и маршрутизирует оба canonical workflow boundaries | `test_content_creation_service_internals_contract`, `test_content_creation_service`, CLI, Wizard paid confirmation, resume и Stage 4 tests | `create_content`, private compatibility imports, paid gate, tolerant resume и progress callback сохранены |
| `src.ai_youtube.apps.content_creator.workflows.fullscreen_voiceover` | application service и `apps.news_to_short`; canonical use case делегирует существующим `src.news` project/workflow contracts | `test_fullscreen_voiceover_application_boundary`, service internals/service, apps structure, news pipeline, project repository | slice 8A (`f8ac67e`, `06e6a25`): canonical boundary установлен; старый use-case path — wrapper, contracts не дублируются, service import остаётся lazy |
| `src.ai_youtube.apps.content_creator.workflows.story_card` | application service; canonical use case делегирует существующим project/evidence/template contracts | `test_story_card_application_boundary`, service internals/Story Card paths, project factory/repository, artifact schemas и provenance | slice 8B (`01cfc6f`): canonical boundary установлен; старый use-case path — wrapper, contracts не дублируются |
| `src.ai_youtube.apps.video_repurposer.workflows.anime_clipper` | `apps.anime_factory`; boundary лениво делегирует `anime_factory.pipeline` и переэкспортирует существующий `EpisodePaths` layout | `test_anime_clipper_application_boundary`, Stage 1 Anime Factory characterization, apps structure, Anime Factory path/cleanup/candidate/crop/transcribe tests | slice 8C (`7d0ce1e`): canonical adapter установлен; legacy package остаётся owner, catalog planned/disabled |
| `src.ai_youtube.apps.legacy_pipeline.adapter` | `apps.youtube_pipeline`; boundary лениво делегирует root facade и переэкспортирует существующий artifact/workflow surface | `test_legacy_pipeline_application_boundary`, legacy internals, Stage 1 characterization, apps structure, workspace paths, catalog и semantic facade contracts | slice 8D (`cfe6ae6`): canonical adapter установлен; root `pipeline.py` остаётся compatibility namespace owner, `src.legacy_pipeline` — behavior owner |
| documentary/fixed production plan gate | root `pipeline.py` импортирует legacy documentary engines и Solar create/render entrypoints; legacy channels вызываются только через `--channel/--video` | `test_documentary_migration_gate`, capability consistency, Stage 4 CLI, fixed-plan, legacy boundary и project repository tests | gate 8E (`a3536a9`): migration не выполнялась; application/template/project/paid-provider contracts не подтверждены |
| `src.news.pipeline` | canonical fullscreen boundary, root pipeline и direct compatibility callers; управляет stage/resume/force | `test_news_to_short_pipeline`, autonomous completion, delivery, renderer, voice | сохранить владельцем working workflow до отдельного bounded move |
| `src.news.asset_manager` + `src.news.asset_*` | facade вызывают news pipeline, quality/draft completion и replacement summary; builder использует shared `src.assets`/`src.providers` contracts | public-contract characterization, assets, provider integration, slot-aware retrieval, semantic decisions, schema/service/pipeline tests | 6A завершён: facade, builder, summaries, completion и provider adapters разделены; imports/patch-points сохранены |
| `src.assets.semantic_visual_evaluation` + `semantic_visual_evaluation_tooling`/`runtime` | 53-строчный facade импортирует root pipeline; tooling владеет offline dataset/metrics/reporting, runtime — gated execution/checkpoints | `test_semantic_visual_evaluation_internals_contract`, `test_semantic_visual_evaluation`, `test_asset_cli_wiring` | 6E завершён: public signatures/dataclass shapes/root caller сохранены; runtime и tooling разделены без второго engine |
| `src.projects.ProjectRepository` | CLI, service, Wizard, replacement и rights report | `test_project_repository`, rights report, config parity, resume | сохранить единственным read API; writer не добавлять |
| `src.news.NewsProjectStore` | news pipeline, service, voice CLI, replacement | `test_news_stage_idempotency`, news models/pipeline, service, renderer, repository tests | writer использует общий atomic primitive с 5A, schema v1 с 5B, fail-fast project lock с 5C и output validation для repeatable stages `research`–`export` с 5D |
| `src.project_foundation` | Story Card service/integration, catalog, projects/rights | project foundation/factory, Story Card integration/provenance, schemas | сохранить `project.json` owner и atomic storage |
| `src.config_resolver.paths` | CLI, apps, project stores, providers, audio/subtitles и legacy adapters | `test_stage3_workspace_paths`, config resolver/parity | сохранить единственным path/workspace resolver |
| `src.assets.provider_contract` + `src.providers` | canonical registry, asset manager, preview/download/diagnostics и provider adapters | provider contract characterization, foundation/hardening, provider integration, documentary providers | этап 7: `StockProvider` — единственный canonical contract; default factory принадлежит `src.providers.registry`, news wrapper делегирует |
| `src.audio` | service, news voice/render, localization и subtitles timing | voice/narration/timeline/policy/manifest/end-tail families | сохранить approval, manifest и timing contracts |
| `src.subtitles` | adapter `src.news.subtitles`, CLI и catalog | subtitle engine + pipeline integration | сохранить единственным subtitle engine |
| `pipeline.py` + `src.legacy_pipeline` | `apps.youtube_pipeline`; facade сохраняет legacy engine/news/diagnostic imports и передаёт module patch-points split handlers | `test_legacy_pipeline_internals_contract`, Stage 1 characterization, apps structure, workspace paths, catalog, asset CLI wiring | 6F завершён: 122-строчный facade, 27-строчный `main`, parser/maintenance/workflow разделены; public command contract и patch-points сохранены |
| `frame_sampling` + `perceptual_similarity` + `frame_primitives` | sampling и similarity зависят только от shared data/hash primitives; прежние public imports сохранены | `test_asset_import_boundaries`, visual preview foundation/integration, temporal analysis | 6G (`802a54c`) устранил оба встречных static edges |

Подэтап 6G вынес `SampledFrame`, `sha256_file` и `image_perceptual_hash` в
минимальный `frame_primitives.py`. AST-characterization запрещает прежние
встречные imports и требует общий primitive dependency. CLI ↔ Wizard cycle,
отмеченный исходным аудитом, также отсутствует: направление осталось только
CLI → Wizard через lazy import.

Этап 7 перенёс default automatic provider factory из news boundary в
`src.providers.registry`. Активный news workflow использует implementations
полного `StockProvider` contract; общий HTTP client, provider diagnostics,
download validation и license policy остаются единственными владельцами своих
политик. `stock_video_downloader` сохранён 35-строчным compatibility wrapper без
raw HTTP. D01 provider names и D02 module не являются active path и сохраняются
до отдельного retirement evidence этапа 9. Legacy documentary/fixed-plan HTTP
callers остаются в границе вертикальных переносов этапа 8.

Первый slice этапа 8 перенёс application-level Fullscreen Voiceover use case в
`src.ai_youtube.apps.content_creator.workflows.fullscreen_voiceover`.
`src.content_creation.fullscreen_voiceover_use_case` остался compatibility
wrapper, а `apps.news_to_short` теперь разрешает existing create/run contracts
через canonical boundary. `src.news` продолжает владеть `NewsJob`,
`NewsProjectStore` и working pipeline; schemas и runtime data не менялись.

Второй slice этапа 8 перенёс application-level Story Card use case в
`src.ai_youtube.apps.content_creator.workflows.story_card`.
`src.content_creation.story_card_use_case` остался compatibility wrapper.
`src.project_foundation` продолжает владеть `ProjectFactory`,
`ProjectManifest` и evidence contracts, а `src.templates.story_card` —
workflow/renderer integration; schemas и runtime data не менялись.

Третий slice этапа 8 создал
`src.ai_youtube.apps.video_repurposer.workflows.anime_clipper` как ленивый
adapter к существующим `anime_factory.pipeline` и
`anime_factory.modules.paths` contracts. `apps.anime_factory` использует новую
boundary; прямой legacy CLI, `EpisodePaths`, runtime episodes и output layout
не менялись. `video_repurposer` остаётся planned/disabled.

Четвёртый slice этапа 8 создал
`src.ai_youtube.apps.legacy_pipeline.adapter` как ленивую границу к root
`pipeline.py` и существующим `src.legacy_pipeline` contracts.
`apps.youtube_pipeline` использует новую boundary; root command signatures,
engine patch-points, parser/maintenance/workflow behavior, outputs и runtime
layout не менялись.

Gate 8E проверил documentary channels и Solar fixed plan без production/runtime
изменений. Catalog не содержит documentary application/template, `longform`
disabled без template, legacy profiles не поддерживаются `content_creator`.
Solar layout не читается `ProjectRepository`, а live render orchestration
напрямую использует TTS/HTTP dependencies без общего application approval
contract. Поэтому новый boundary не создавался, capability не включалась и
этап 8 закрыт с четырьмя фактически мигрированными slices.

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
   infrastructure contracts. `video_repurposer` имеет canonical Anime Clipper
   adapter, но остаётся planned/disabled. Documentary не имеет application
   boundary/template; будущая реализация требует отдельного подтверждённого
   product stage, а не переноса legacy/fixed-plan кода по наличию.
3. `ProjectRepository` остаётся общим read API поверх двух persisted форм;
   write convergence использует общий atomic primitive и project-lock primitive,
   а не третью schema или writer.
4. Asset providers реализуют `src.assets.provider_contract.StockProvider`, а
   default registry находится в `src.providers`; active workflow не знает HTTP
   API.
5. Audio approval/manifests, subtitle engine и path resolver — shared services,
   которые переиспользуются, а не дублируются при переносе приложений.
6. Legacy pipeline доступен через canonical adapter; `pipeline.py` и `apps/*`
   остаются compatibility zone до проверенного периода совместимости.
7. `anime_factory` доступен через canonical `video_repurposer` adapter и
   остаётся владельцем физического workflow/output layout до отдельного
   migration evidence.

Следующая очередь и доказательства удаления находятся в
[CLEANUP_REGISTRY.md](CLEANUP_REGISTRY.md).
