---
status: current
last_verified_commit: 0cd0e11
last_verified_date: 2026-07-28
source_paths:
  - pyproject.toml
  - .github/workflows/offline-tests.yml
  - src/config_resolver/paths.py
  - src/content_creation/capabilities.py
  - src/production_catalog
  - src/projects
  - docs/handoff/PROJECT_RESCUE_MASTER_PLAN.md
---

# Current State

Проверено 2026-07-28 по implementation HEAD `0cd0e11`. Код и Git имеют приоритет.

- Rescue stages 0–3 завершены; следующий этап 4 ещё не начат.
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

- CLI/Wizard и `pipeline.py` ещё не сведены к одному dispatcher — этап 4;
- две формы project manifests и неодинаковые storage primitives — этап 5;
- крупные модули и два известных import-cycle — этап 6;
- provider consolidation и вертикальные переносы приложений ещё не начаты.

Запрещено начинать этап 4, пока этап 3 не проверен и не зафиксирован. Сохранённые
full-suite отчёты исторические; для текущего изменения запускать только указанные
targeted tests.
