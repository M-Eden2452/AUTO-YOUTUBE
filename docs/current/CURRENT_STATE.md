---
status: current
last_verified_commit: b7350b3
last_verified_date: 2026-07-28
source_paths:
  - pyproject.toml
  - .github/workflows/offline-tests.yml
  - src/content_creation/capabilities.py
  - src/production_catalog
  - src/projects
  - docs/handoff/PROJECT_RESCUE_MASTER_PLAN.md
---

# Current State

Проверено 2026-07-28 по implementation HEAD `b7350b3`. Код и Git имеют приоритет.

- Rescue stages 0–2 завершены; следующий этап 3 ещё не начат.
- Активное приложение: `content_creator`.
- Активные live-tested шаблоны: `fullscreen_voiceover_v1` и
  `story_card_text_only_v1`.
- `video_repurposer`, `longform` и `horizontal_clip` остаются disabled/planned.
- Общий `ProjectRepository` читает старые `job.json` и `project.json`.
- Offline CI, pinned core lock, artifact schemas и characterization baseline добавлены
  этапом 1.
- Runtime-проекты и media пока остаются внутри репозитория; физическая миграция не
  выполнялась.

Известные переходные долги:

- production-код ещё зависит от `Path.cwd()` и локальных путей — этап 3;
- CLI/Wizard и `pipeline.py` ещё не сведены к одному dispatcher — этап 4;
- две формы project manifests и неодинаковые storage primitives — этап 5;
- крупные модули и два известных import-cycle — этап 6;
- provider consolidation и вертикальные переносы приложений ещё не начаты.

Запрещено начинать этап 3, пока этап 2 не проверен и не зафиксирован. Сохранённые
full-suite отчёты исторические; для текущего изменения запускать только указанные
targeted tests.
