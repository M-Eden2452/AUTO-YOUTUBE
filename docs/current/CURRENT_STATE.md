---
status: current
last_verified_commit: 40f3557
last_verified_date: 2026-07-29
source_paths:
  - pyproject.toml
  - .github/workflows/offline-tests.yml
  - ai_youtube
  - src/ai_youtube/cli
  - src/config_resolver/paths.py
  - src/content_creation/capabilities.py
  - src/news/models.py
  - src/news/project_store.py
  - src/project_foundation/storage.py
  - src/production_catalog
  - src/projects
  - schemas/job.schema.json
  - docs/adr/0004-news-job-schema-version.md
  - docs/adr/0005-news-project-lock.md
  - docs/adr/0006-news-stage-idempotency.md
  - docs/adr/0007-canonical-cli-package.md
  - docs/current/ARCHITECTURE_BOUNDARY_MAP.md
  - docs/current/CLEANUP_REGISTRY.md
  - docs/handoff/PROJECT_RESCUE_MASTER_PLAN.md
---

# Current State

Проверено 2026-07-29 по implementation HEAD `40f3557`. Код и Git имеют приоритет.

- Rescue stages 0–4.6, slices 5A–5C и bounded 5D families
  `research`/`script`/`visual_plan` завершены; этап 5 продолжается. Физическая
  перестройка канонической структуры начата.
  Product Evidence Gate 4.5 сохранён только как
  историческая диагностика и решением владельца снят с critical path;
  Product Repair 4.5-R закрыт без продолжения.
- Этап 4.6 создал проверенные
  [dependency/boundary map](ARCHITECTURE_BOUNDARY_MAP.md) и
  [cleanup registry](CLEANUP_REGISTRY.md) без изменения production code/runtime.
- Slice 5A перевёл `NewsProjectStore.write_json` на существующий
  `project_foundation.atomic_write_json`. Slice 5B добавил `NEWS_JOB_SCHEMA_VERSION=1`.
  Slice 5C добавил общий fail-fast project lock.
  Bounded slices 5D добавили output-validated stage idempotency для семейств
  `research`, `script` и `visual_plan`: завершённое состояние признаётся только
  при наличии структурно пригодного обязательного JSON-артефакта.
  Первый structural migration slice перенёс канонический CLI-слой в `src/ai_youtube/cli/`
  с доменными модулями команд (`create`, `project`, `assets`, `diagnostics`), а `src/content_creation/cli.py`
  сохранён как тонкий compatibility wrapper.
- `python -m ai_youtube` — единственный канонический CLI;
  `src.content_creation.cli`, `pipeline.py` и `apps/*` сохранены для совместимости.
- Команды CLI зарегистрированы отдельными domain parser modules; общий request
  builder используется CLI и Wizard, cycle CLI ↔ Wizard устранён.
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
  отдельные news JSON writes; после `research`, `script` и `visual_plan`
  остальные stage families, начиная с `asset_search`, получают idempotency
  только отдельными bounded slices 5D;
- крупные command handlers и cycle frame sampling ↔ perceptual similarity — этап 6;
- provider consolidation и вертикальные переносы приложений ещё не начаты;
- compatibility wrappers, duplicate implementations, generated/runtime clutter
  и deletion candidates классифицированы, но implementation/cleanup ещё не
  выполнялись.

Создание, продолжение, TTS, render и визуальная проверка reference video больше
не являются этапами rescue plan. Архитектурные изменения выполняются малыми
slices после карты callers/tests; удаление без доказанной замены запрещено.
Сохранённые full-suite отчёты исторические; для каждого изменения запускаются
только targeted tests в радиусе зависимости.
