---
status: current
last_verified_commit: fb374fd
last_verified_date: 2026-07-28
source_paths:
  - pyproject.toml
  - .github/workflows/offline-tests.yml
  - ai_youtube
  - src/config_resolver/paths.py
  - src/content_creation/capabilities.py
  - src/production_catalog
  - src/projects
  - docs/current/PRODUCT_EVIDENCE_GATE.md
  - docs/handoff/PROJECT_RESCUE_MASTER_PLAN.md
---

# Current State

Проверено 2026-07-28 по HEAD `fb374fd`. Код и Git имеют приоритет.

- Rescue stages 0–4 завершены; этап 4.5 Product Evidence Gate завершён с
  **Fail**. Следующий ограниченный этап — 4.5-R Product Repair; этапы 4.6 и 5
  ещё не начаты.
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

- проверенный reference Short технически исправен, но имеет только 39% video
  duration, 3/3 partial-support draft-only scenes и `publish_ready=false`;
  подробности в [PRODUCT_EVIDENCE_GATE.md](PRODUCT_EVIDENCE_GATE.md);
- две формы project manifests и неодинаковые storage primitives — этап 5;
- крупные command handlers и cycle frame sampling ↔ perceptual similarity — этап 6;
- provider consolidation и вертикальные переносы приложений ещё не начаты.

До ограниченного Product Repair нельзя начинать этапы 4.6, 5 или последующие.
Сохранённые full-suite отчёты исторические; для текущего изменения запускать
только указанные targeted tests.
