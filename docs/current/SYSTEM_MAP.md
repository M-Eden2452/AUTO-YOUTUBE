---
status: current
last_verified_commit: f7b3a3c
last_verified_date: 2026-07-28
source_paths:
  - ai_youtube
  - pipeline.py
  - src/config_resolver/paths.py
  - src/content_creation
  - src/news
  - src/projects
  - src/project_foundation
  - schemas/job.schema.json
  - src/assets
  - src/providers
  - src/audio
  - src/subtitles
  - anime_factory
  - docs/current/ARCHITECTURE_BOUNDARY_MAP.md
  - docs/current/CLEANUP_REGISTRY.md
---

# System Map

Код и Git имеют приоритет. Карта описывает существующие границы, а не разрешает
массовое перемещение.

| Область | Текущий авторитет | Роль |
|---|---|---|
| Пути и workspace | `src/config_resolver/paths.py` | единый resolver versioned resources, runtime roots и legacy fallback |
| Канонический CLI | `ai_youtube/`, `src/content_creation/commands/` | dispatcher активного приложения и domain parser modules |
| Создание контента | `src/content_creation/` | compatibility CLI, wizard и application service |
| Fullscreen workflow | `src/news/` | staged `news_to_short`, resume и render |
| Story Card | `src/templates/story_card/`, `src/production_plan/` | workflow adapter и renderer |
| Проекты | `src/projects/`, `src/project_foundation/` | общий read API и atomic storage primitive для project manifests |
| Ассеты | `src/assets/` | selection, preview, semantic checks, completion |
| Providers | `src/providers/` | provider adapters и общий contract |
| Голос | `src/audio/`, `src/localization/` | approval, manifests, timeline и voice resolution |
| Субтитры | `src/subtitles/` | единственный subtitle engine |
| Legacy/maintenance | `pipeline.py`, `apps/` | compatibility entrypoints |
| Video repurposing | `anime_factory/` | отдельный существующий Anime Factory workflow |

Текущая продуктовая модель:

```text
content_creator
  ├─ fullscreen_voiceover_v1
  └─ story_card_text_only_v1

video_repurposer
  └─ planned/disabled (Anime Factory ещё не перенесён под этот app boundary)
```

Ключевые переходные ограничения:

- `job.json` и `project.json` пока сосуществуют;
- `ProjectRepository` читает обе формы и legacy roots, но ничего не записывает;
- `python -m ai_youtube` — единственный канонический CLI;
- `pipeline.py`, `python -m src.content_creation.cli` и `apps/*` остаются
  compatibility entrypoints;
- default workspace остаётся корнем репозитория до отдельной физической миграции;
- произвольный workspace выбирается через CLI/env/path config, а versioned resources
  остаются привязаны к репозиторию;
- definitions CLI-команд разделены по domain-модулям; глубокое разделение крупных
  command handlers остаётся этапом 6 rescue plan.

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
автоматически. Следующий отдельный slice 5D добавляет stage idempotency.
