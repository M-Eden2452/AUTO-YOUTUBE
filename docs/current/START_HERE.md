---
status: current
last_verified_commit: dcd6a3c
last_verified_date: 2026-07-29
source_paths:
  - AGENTS.md
  - docs/handoff/PROJECT_RESCUE_MASTER_PLAN.md
  - docs/current/ARCHITECTURE_BOUNDARY_MAP.md
  - docs/current/CLEANUP_REGISTRY.md
  - ai_youtube
  - src/ai_youtube/cli
  - src/ai_youtube/apps
  - src/config_resolver
  - src/content_creation
  - src/assets
  - pipeline.py
  - src/legacy_pipeline
  - src/news
  - src/providers
  - src/production_catalog
  - src/production_plan
  - docs/adr
  - tests
---

# Start Here

AI-YouTube — локальная offline-first система производства Shorts. Код и Git имеют
приоритет над этим документом.

Для начала работы достаточно:

1. Прочитать [AGENTS.md](../../AGENTS.md).
2. Проверить Git указанными там read-only командами.
3. Прочитать [CURRENT_STATE.md](CURRENT_STATE.md). Открывать
   [SYSTEM_MAP.md](SYSTEM_MAP.md) только для архитектурной задачи.

Текущий rescue plan: [PROJECT_RESCUE_MASTER_PLAN.md](../handoff/PROJECT_RESCUE_MASTER_PLAN.md).
Этапы 0–8 завершены. В этапе 8 vertical slices `fullscreen_voiceover`
(`f8ac67e`, `06e6a25`), `story_card` (`01cfc6f`), `anime_clipper`
(`7d0ce1e`) и legacy pipeline (`cfe6ae6`) завершены. Canonical boundaries
находятся в `src.ai_youtube.apps`; прежние use-case/entrypoint paths сохранены
wrappers, а `video_repurposer` остаётся planned/disabled. Documentary candidate
был проверен gate 8E (`a3536a9`) и не мигрирован: реального
catalog template, canonical project contract и безопасного application-level
paid/provider gate нет. Этап 9 завершён: bounded slice D01 удалил три
news-only provider class names после zero-caller audit, сохранив canonical
registry и news factory patch-point. D02 затем удалил standalone
`src.news.stock_video_downloader` после отдельного zero-caller/entrypoint
audit, а D03 — пустую planning directory `packages/` после package/docs gate.
Следующий rescue stage — 10; начинать его следует с отдельного read-only
inventory, без runtime/user-data deletion.
Подробная проверенная карта зависимостей находится в
[ARCHITECTURE_BOUNDARY_MAP.md](ARCHITECTURE_BOUNDARY_MAP.md), а решения по
кандидатам cleanup — в [CLEANUP_REGISTRY.md](CLEANUP_REGISTRY.md).
Исторические handoff и отчёты находятся в [docs/archive](../archive/README.md) и не
являются текущим источником истины.

Безопасная проверка интерфейса:

```powershell
.\venv\Scripts\python.exe -m ai_youtube capabilities --json
```

`python -m ai_youtube` — канонический CLI. `python -m src.content_creation.cli`,
`pipeline.py` и `apps/*` сохранены как compatibility entrypoints.

Для отдельного runtime workspace используй глобальный `--workspace`, переменную
`AI_YOUTUBE_WORKSPACE` или path config. Без явной настройки legacy workspace остаётся
корнем репозитория; физическая миграция runtime ещё не выполнялась.

Не запускай сеть, providers, Vision, TTS, скачивание или платные действия без
отдельного разрешения пользователя.
