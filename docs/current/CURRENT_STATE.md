---
status: current
last_verified_commit: 802a54c
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
  - src/assets/semantic_visual_evaluation.py
  - src/assets/semantic_visual_evaluation_runtime.py
  - src/assets/semantic_visual_evaluation_tooling.py
  - src/assets/frame_primitives.py
  - src/assets/frame_sampling.py
  - src/assets/perceptual_similarity.py
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
  - src/production_catalog
  - src/projects
  - schemas/job.schema.json
  - docs/adr/0004-news-job-schema-version.md
  - docs/adr/0005-news-project-lock.md
  - docs/adr/0006-news-stage-idempotency.md
  - docs/adr/0007-canonical-cli-package.md
  - tests/test_news_asset_manager_contract.py
  - tests/test_cli_internals_contract.py
  - tests/test_wizard_internals_contract.py
  - tests/test_content_creation_service_internals_contract.py
  - tests/test_semantic_visual_evaluation_internals_contract.py
  - tests/test_legacy_pipeline_internals_contract.py
  - tests/test_asset_import_boundaries.py
  - tests/test_news_stage_idempotency.py
  - docs/current/ARCHITECTURE_BOUNDARY_MAP.md
  - docs/current/CLEANUP_REGISTRY.md
  - docs/handoff/PROJECT_RESCUE_MASTER_PLAN.md
---

# Current State

Проверено 2026-07-29 по implementation HEAD `802a54c`. Код и Git имеют приоритет.

- Rescue stages 0–6, включая подэтапы 6A–6G, завершены; следующий этап — 7.
  Физическая перестройка канонической структуры начата.
  Product Evidence Gate 4.5 сохранён только как
  историческая диагностика и решением владельца снят с critical path;
  Product Repair 4.5-R закрыт без продолжения.
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
- provider consolidation этапа 7 и вертикальные переносы приложений ещё не начаты;
- compatibility wrappers, duplicate implementations, generated/runtime clutter
  и deletion candidates классифицированы, но implementation/cleanup ещё не
  выполнялись.

Создание, продолжение, TTS, render и визуальная проверка reference video больше
не являются этапами rescue plan. Архитектурные изменения выполняются малыми
slices после карты callers/tests; удаление без доказанной замены запрещено.
Сохранённые full-suite отчёты исторические; для каждого изменения запускаются
только targeted tests в радиусе зависимости.
