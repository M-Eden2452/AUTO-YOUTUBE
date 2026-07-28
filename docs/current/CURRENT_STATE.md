---
status: current
last_verified_commit: 87e272a
last_verified_date: 2026-07-28
source_paths:
  - pyproject.toml
  - .github/workflows/offline-tests.yml
  - ai_youtube
  - src/config_resolver/paths.py
  - src/content_creation/capabilities.py
  - src/production_catalog
  - src/projects
  - docs/current/ARCHITECTURE_BOUNDARY_MAP.md
  - docs/current/CLEANUP_REGISTRY.md
  - docs/handoff/PROJECT_RESCUE_MASTER_PLAN.md
---

# Current State

Проверено 2026-07-28 по implementation HEAD `87e272a`. Код и Git имеют приоритет.

- Rescue stages 0–4.6 и bounded slice 5A завершены. Этап 5 выполняется.
  Product Evidence Gate 4.5 сохранён только как
  историческая диагностика и решением владельца снят с critical path;
  Product Repair 4.5-R закрыт без продолжения.
- Этап 4.6 создал проверенные
  [dependency/boundary map](ARCHITECTURE_BOUNDARY_MAP.md) и
  [cleanup registry](CLEANUP_REGISTRY.md) без изменения production code/runtime.
- Slice 5A перевёл `NewsProjectStore.write_json` на существующий
  `project_foundation.atomic_write_json`, сохранив JSON shape, UTF-8 и trailing
  newline. Следующий bounded slice 5B добавляет additive schema version news
  manifest с tolerant read старых `job.json`.
- `python -m ai_youtube` — канонический CLI активного `content_creator`;
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

- две формы project manifests сохраняются tolerant readers; явная schema version
  news manifest, project lock и stage idempotency остаются отдельными slices
  этапа 5;
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
