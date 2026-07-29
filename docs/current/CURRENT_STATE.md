---
status: current
last_verified_commit: 9f3ddba
last_verified_date: 2026-07-29
source_paths:
  - pyproject.toml
  - .github/workflows/offline-tests.yml
  - ai_youtube
  - src/ai_youtube/cli
  - src/config_resolver/paths.py
  - src/content_creation/capabilities.py
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
  - apps/anime_factory
  - apps/youtube_pipeline
  - anime_factory
  - src/assets/semantic_visual_evaluation.py
  - src/assets/semantic_visual_evaluation_runtime.py
  - src/assets/semantic_visual_evaluation_tooling.py
  - src/assets/frame_primitives.py
  - src/assets/frame_sampling.py
  - src/assets/perceptual_similarity.py
  - src/assets/provider_contract.py
  - pipeline.py
  - src/legacy_pipeline
  - src/news/models.py
  - src/news/asset_manager.py
  - src/news/asset_manifest_builder.py
  - src/news/asset_manifest_summaries.py
  - src/news/asset_scene_completion.py
  - src/news/asset_provider_adapters.py
  - src/news/project_store.py
  - src/project_foundation/storage.py
  - src/providers/registry.py
  - src/audio
  - src/music_engine.py
  - src/music_finder.py
  - src/music_tools.py
  - src/production_plan/youtube_shorts.py
  - src/production_plan/solar_vs_nuclear_render.py
  - src/production_catalog
  - src/projects
  - schemas/job.schema.json
  - docs/adr/0004-news-job-schema-version.md
  - docs/adr/0005-news-project-lock.md
  - docs/adr/0006-news-stage-idempotency.md
  - docs/adr/0007-canonical-cli-package.md
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
  - docs/current/ARCHITECTURE_BOUNDARY_MAP.md
  - docs/current/CLEANUP_REGISTRY.md
  - docs/handoff/PROJECT_RESCUE_MASTER_PLAN.md
---

# Current State

Проверено 2026-07-29 от clean HEAD `9f3ddba`. Код и Git имеют
приоритет.

- Rescue stages 0–8, включая подэтапы 6A–6G, завершены. Этап 8 перенёс
  vertical slices `fullscreen_voiceover`, `story_card`, `anime_clipper` и
  legacy pipeline. Gate 8E проверил documentary/fixed-plan paths и закрыл
  кандидат без migration: реального catalog template и безопасной application
  boundary нет.
  Product Evidence Gate 4.5 сохранён только как
  историческая диагностика и решением владельца снят с critical path;
  Product Repair 4.5-R закрыт без продолжения.
- Этап 9A завершён тремя bounded deletion slices. D01 после повторного repo-wide
  zero-caller audit удалил news-only `PexelsAssetProvider`,
  `PixabayAssetProvider`, `UnsplashAssetProvider` и их re-exports.
  `AssetProvider`, news factory patch-point и canonical `StockProvider`
  implementations сохранены. D02 также завершён: standalone downloader wrapper
  удалён после отдельного AST callers/entrypoint gate; active asset stage не
  менялся. D03 удалил только `packages/README.md` и подтверждённо пустую
  planning directory после package/docs gate; package discovery не менялся.
  После owner review общий этап 9 расширен подэтапами 9B–9E: inventory,
  caller migration, ownership transfer и wrapper/package retirement.
  9B-P01 подтвердил два target engines: `content_creator` для short/long
  creation и `video_repurposer` на основе Anime Factory. Catalog status не
  менялся; repurposer остаётся disabled. Следующий checkpoint — read-only
  9B-C01; production code не менялся.
- Этап 4.6 создал проверенные
  [dependency/boundary map](ARCHITECTURE_BOUNDARY_MAP.md) и
  [cleanup registry](CLEANUP_REGISTRY.md) без изменения production code/runtime.
- Slice 5A перевёл `NewsProjectStore.write_json` на существующий
  `project_foundation.atomic_write_json`. Slice 5B добавил `NEWS_JOB_SCHEMA_VERSION=1`.
  Slice 5C добавил общий fail-fast project lock.
  Bounded slices 5D добавили output-validated stage idempotency для всех
  повторяемых downstream-семейств от `research` до `export`: завершённое
  состояние признаётся только при наличии пригодного обязательного
  manifest/media output. Legacy asset/voice/subtitle shapes и protected
  пользовательские субтитры остаются tolerant.
  Первый structural migration slice перенёс канонический CLI-слой в `src/ai_youtube/cli/`
  с доменными модулями команд (`create`, `project`, `assets`, `diagnostics`), а `src/content_creation/cli.py`
  сохранён как тонкий compatibility wrapper.
- `python -m ai_youtube` — единственный канонический CLI;
  `src.content_creation.cli`, `pipeline.py` и `apps/*` сохранены для совместимости.
- Команды CLI зарегистрированы отдельными domain parser modules; общий request
  builder используется CLI и Wizard, cycle CLI ↔ Wizard устранён.
- Подэтап 6A разделил бывший 2119-строчный `src/news/asset_manager.py`:
  266-строчный compatibility facade сохраняет публичные функции, старые imports
  и patch-points; manifest builder отделён от чистых summary/coverage-расчётов,
  scene completion и provider search/download adapters. Provider contract,
  manifest schema и persisted projects не менялись.
- Подэтап 6B оставил `src/content_creation/cli.py` тонким compatibility facade
  и разделил бывший 727-строчный canonical diagnostics handler: catalog,
  localization/subtitles и authoring выполняются отдельными domain-модулями,
  а терминальное форматирование вынесено в `src/ai_youtube/cli/presentation.py`.
  Public command set, JSON/text output и старые module-level patch-points
  сохранены; потерянный migration-ом `create_content` patch-point восстановлен
  через явную dependency injection.
- Подэтап 6C уменьшил `src/content_creation/wizard.py` с 1229 до 175 строк:
  facade сохраняет `run_wizard`, prompt adapters, private compatibility imports
  и module-level request-builder patch-point. Working state и translation через
  общий `request_builder` вынесены в `wizard_state.py`, terminal presentation —
  в `wizard_presentation.py`, интерактивные шаги и execution orchestration —
  в `wizard_steps.py`. Lazy CLI → Wizard boundary и application service не
  менялись.
- Подэтап 6D уменьшил `src/content_creation/service.py` с 878 до 123 строк и
  сохранил его единой точкой входа `create_content` для CLI и Wizard. Общие
  progress/path helpers вынесены в `service_support.py`, Story Card и Fullscreen
  Voiceover — в отдельные use case-модули. Fullscreen orchestration разделён на
  явные project, safe-pipeline, voice/approval, draft и render/export фазы;
  longest method — 93 строки. Paid approval/preflight, resume/force-stage,
  tolerant existing narration и progress callback сохранены.
- Подэтап 6E уменьшил `src/assets/semantic_visual_evaluation.py` с 1719 до
  53 строк и сохранил его public facade для root `pipeline.py`. Offline
  dataset loading, synthetic frames, metrics и report artifacts вынесены в
  `semantic_visual_evaluation_tooling.py`; gated OpenAI execution, budget,
  authorization и checkpoint state — в
  `semantic_visual_evaluation_runtime.py`. Public signatures, dataclass shapes,
  dry-run/mock/fake-client paths и paid-call gates сохранены; самая длинная
  функция split-модулей — 68 строк.
- Подэтап 6F уменьшил root `pipeline.py` с 703 до 122 строк и оставил его
  compatibility facade для `apps.youtube_pipeline`, старых imports и
  module-level patch-points. Parser вынесен в `src/legacy_pipeline/cli.py`,
  maintenance/diagnostic handlers — в `maintenance.py`, legacy
  channel/video orchestration — в `workflow.py`. `main` занимает 27 строк,
  самая длинная orchestration-функция split-модулей — 77 строк; command
  contract, workspace resolution, safe paid-call gates и старый workflow
  сохранены.
- Подэтап 6G устранил подтверждённый static import-cycle
  `frame_sampling` ↔ `perceptual_similarity`: `SampledFrame`, file SHA-256 и
  perceptual image hash вынесены в минимальный `frame_primitives.py`.
  Прежние public imports из обоих модулей и `src.assets`, image sampling,
  signature generation, visual-preview и temporal-analysis поведение сохранены.
- Этап 7 закрепил `src.assets.provider_contract.StockProvider` единственным
  canonical provider contract и перенёс default automatic factory в
  `src.providers.registry`. Активный news workflow получает canonical
  implementations из `src.providers`; timeout/retry/rate-limit translation,
  diagnostics, download validation и license normalization остаются в общих
  `src.assets` components. `stock_video_downloader` сокращён до 35-строчного
  compatibility wrapper без raw HTTP, а D01 legacy provider names удалены
  bounded slice этапа 9 после zero-caller audit. Отдельный D02 checkpoint затем
  подтвердил отсутствие imports/entrypoints и удалил wrapper; active asset
  stage остаётся у `src.news.asset_manager`.
- Первый slice этапа 8 (`f8ac67e`, `06e6a25`) установил canonical Fullscreen Voiceover
  application boundary в
  `src.ai_youtube.apps.content_creator.workflows.fullscreen_voiceover`.
  Application service импортирует новый use case; прежний
  `src.content_creation.fullscreen_voiceover_use_case` и
  `apps.news_to_short` остаются compatibility wrappers. Существующие
  `NewsJob`, `NewsProjectStore` и `src.news.pipeline` переиспользуются без
  новой schema/storage/workflow system; lazy service import сохранён, runtime
  projects не мигрировались.
- Второй slice этапа 8 (`01cfc6f`) установил canonical Story Card application
  boundary в
  `src.ai_youtube.apps.content_creator.workflows.story_card`.
  Application service импортирует новый use case; прежний
  `src.content_creation.story_card_use_case` остаётся compatibility wrapper.
  Существующие `ProjectFactory`, `ProjectManifest`, `EvidenceBundle`,
  `EvidenceRecord` и `src.templates.story_card` переиспользуются без новой
  schema/storage/evidence/render system; persisted projects и user media не
  мигрировались.
- Третий slice этапа 8 (`7d0ce1e`) установил canonical Anime Clipper adapter
  boundary в
  `src.ai_youtube.apps.video_repurposer.workflows.anime_clipper`.
  `apps.anime_factory` разрешает workflow через новую границу, а существующие
  `anime_factory.pipeline`, `EpisodePaths` и `get_episode_paths` остаются
  единственными владельцами поведения и project/output layout. Catalog
  `video_repurposer` не включён и остаётся planned/disabled; runtime episodes
  не перемещались.
- Четвёртый slice этапа 8 (`cfe6ae6`) установил canonical legacy pipeline
  adapter в `src.ai_youtube.apps.legacy_pipeline.adapter`.
  `apps.youtube_pipeline` разрешает root `pipeline.main` через новую границу,
  а root facade остаётся владельцем compatibility namespace и engine
  patch-points. Существующие parser, maintenance и channel/video workflow
  contracts продолжают принадлежать `src.legacy_pipeline`; engines, outputs,
  runtime projects и media не перемещались.
- Gate 8E (`a3536a9`) подтвердил, что documentary не зарегистрирован как
  application/template, `longform` disabled и без шаблона, а legacy profiles
  `psychology`, `quotes`, `survival` и `size_comparison` недоступны
  `content_creator`. Solar fixed plan остаётся root-only experimental path:
  его `project_config.json`/`scenes.json` не распознаются `ProjectRepository`,
  а render path имеет прямые TTS/HTTP calls без application-level paid gate.
  Поэтому documentary boundary, capability и новый project contract не
  создавались; решение зафиксировано ADR 0013.
- `applications list` по умолчанию показывает только active/enabled приложения;
  planned/disabled доступны только при явном запросе и сохраняют честный статус.
- Активное приложение: `content_creator`.
- Активные live-tested шаблоны: `fullscreen_voiceover_v1` и
  `story_card_text_only_v1`.
- `video_repurposer`, `longform` и `horizontal_clip` остаются disabled/planned.
- Общий `ProjectRepository` читает старые `job.json` и `project.json`.
- Offline CI, pinned core lock, artifact schemas и characterization baseline добавлены
  этапом 1.
- `WorkspacePaths`/`ApplicationPaths` задают единый runtime workspace через
  CLI, `AI_YOUTUBE_WORKSPACE` или path config; CLI имеет наивысший приоритет.
- Default workspace и legacy fallback остаются в корне репозитория, поэтому старые
  проекты и outputs читаются без физического переноса.
- Versioned config/resources всегда разрешаются от корня репозитория, а не от cwd.
- Runtime-проекты и media физически не перемещались.

Известные переходные долги:

- две формы project manifests сохраняются tolerant readers; lock сериализует
  отдельные news JSON writes; output validation покрывает повторяемые стадии от
  `research` до `export`. `input` и потенциально сетевой `article_ingestion`
  намеренно не включены в автоматическую retry-policy ADR 0006;
- documentary gate 8E закрыт без migration; ADR 0016 определил future
  documentary как workflow/template `content_creator`, которому нужны реальный
  catalog template, canonical project/approval/provider contracts и targeted
  evidence; физические Anime
  Factory workflow/output contracts остаются у `anime_factory`, root legacy
  engine/patch-point contracts — у `pipeline.py`, а documentary и
  fixed-production-plan HTTP paths остаются внутри будущего bounded slice;
- D01 news-only provider names, D02 standalone downloader и D03 planning
  directory удалены отдельными проверенными commits; stage 10 cleanup
  candidates A01/A02/D04 ещё не начаты;
- этап 8 установил application boundaries, но не завершил ownership transfer:
  `src.news`, `src.templates.story_card`, `anime_factory`, `pipeline.py` и
  `src.legacy_pipeline` всё ещё владеют частью реализации;
- 9B-C01 должен дополнить cleanup registry точными production/test/docs callers
  и exit conditions для package roots/wrappers, Anime project/transcription/
  subtitle/render modules и legacy/shared music paths. До завершения C01
  перенос и удаление этих paths запрещены.

Создание, продолжение, TTS, render и визуальная проверка reference video больше
не являются этапами rescue plan. Архитектурные изменения выполняются малыми
slices после карты callers/tests; удаление без доказанной замены запрещено.
Сохранённые full-suite отчёты исторические; для каждого изменения запускаются
только targeted tests в радиусе зависимости.
