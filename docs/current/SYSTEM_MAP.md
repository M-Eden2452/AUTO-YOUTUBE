---
status: current
last_verified_commit: 0cd0e11
last_verified_date: 2026-07-28
source_paths:
  - pipeline.py
  - src/config_resolver/paths.py
  - src/content_creation
  - src/news
  - src/projects
  - src/project_foundation
  - src/assets
  - src/providers
  - src/audio
  - src/subtitles
  - anime_factory
---

# System Map

Код и Git имеют приоритет. Карта описывает существующие границы, а не разрешает
массовое перемещение.

| Область | Текущий авторитет | Роль |
|---|---|---|
| Пути и workspace | `src/config_resolver/paths.py` | единый resolver versioned resources, runtime roots и legacy fallback |
| Создание контента | `src/content_creation/` | CLI, wizard и application service |
| Fullscreen workflow | `src/news/` | staged `news_to_short`, resume и render |
| Story Card | `src/templates/story_card/`, `src/production_plan/` | workflow adapter и renderer |
| Проекты | `src/projects/`, `src/project_foundation/` | общий read API и foundation для `project.json` |
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
- `pipeline.py` и `src.content_creation.cli` пока оба публичны;
- default workspace остаётся корнем репозитория до отдельной физической миграции;
- произвольный workspace выбирается через CLI/env/path config, а versioned resources
  остаются привязаны к репозиторию;
- канонический dispatcher относится к следующему этапу rescue plan.
