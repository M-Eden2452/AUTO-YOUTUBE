---
status: current
last_verified_commit: 9f3ddba
last_verified_date: 2026-07-29
source_paths:
  - AGENTS.md
  - docs/current/PROJECT_EXECUTION_PLAN.md
  - docs/current/PRODUCT_PLAN.md
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

AI-YouTube — локальная offline-first платформа создания видео и переработки
длинных source videos. Сейчас production-ready только два Shorts templates;
код и Git имеют приоритет над этим документом.

Для начала работы достаточно:

1. Прочитать [AGENTS.md](../../AGENTS.md).
2. Проверить Git указанными там read-only командами.
3. Прочитать [CURRENT_STATE.md](CURRENT_STATE.md). Открывать
   [SYSTEM_MAP.md](SYSTEM_MAP.md) только для архитектурной задачи.

Текущий execution plan: [PROJECT_EXECUTION_PLAN.md](PROJECT_EXECUTION_PLAN.md).
Он задаёт порядок работ; выполняется только его `current_checkpoint` — сейчас
PLAN-9B-2, pending / не начат и заблокирован prerequisite gates PLAN-6D/6E.
Точное значение и следующее действие всегда
берутся из самого плана, а не отсюда.
[PROJECT_RESCUE_MASTER_PLAN.md](../handoff/PROJECT_RESCUE_MASTER_PLAN.md)
остаётся историческим контекстом и текущий порядок выполнения не задаёт.

Продуктовое направление: [PRODUCT_PLAN.md](PRODUCT_PLAN.md). Разделение простое:
execution plan отвечает за **порядок реализации** (checkpoint, статусы,
зависимости, gates), product plan — за **направление продукта** и сохранённые
идеи. Идея из product plan не реализуется напрямую: сначала она должна стать
bounded execution slice в execution plan.

Этапы 0–8 завершены. Этап 8 создал canonical boundaries для
`fullscreen_voiceover`, `story_card`, `anime_clipper` и legacy pipeline, но
оставшиеся old owners и wrappers ещё не retired. Documentary gate 8E закрыт
без migration. Этап 9A удалил D01 provider names, D02 standalone downloader и
D03 `packages/` placeholder. 9B-P01 зафиксировал два target engines:
`content_creator` для short/long creation и `video_repurposer` на основе
существующего Anime Factory. Repurposer пока disabled.
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
`pipeline.py` и `apps/*` пока сохранены как compatibility entrypoints, но каждый
должен получить exit condition в cleanup registry; бессрочный wrapper не
является финальным состоянием.

Для отдельного runtime workspace используй глобальный `--workspace`, переменную
`AI_YOUTUBE_WORKSPACE` или path config. Без явной настройки legacy workspace остаётся
корнем репозитория; физическая миграция runtime ещё не выполнялась.

Не запускай сеть, providers, Vision, TTS, скачивание или платные действия без
отдельного разрешения пользователя.
