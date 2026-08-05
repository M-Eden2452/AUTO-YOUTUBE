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
  - skills/review-change
  - .claude/agents/review-change.md
  - tools/qa/check_agent_docs.py
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
Он задаёт порядок работ; PLAN-6E завершён 2026-08-02: canonical read-only policy
находится в `skills/review-change/`, тонкие Claude/Codex adapters ссылаются на неё,
а controlled acceptance проверила безопасный и нарушающий synthetic diff. Локальный checker
`python -m tools.qa.check_task_scope` принимает task-specific `--allow` /
`--allow-dir` и возвращает `OK/0`, `STOP_REQUIRED/1` или `INVALID_INPUT/2`.
Для Claude Code root `skills/` не считается автоматически загруженным:
перед специализированной задачей нужно вручную открыть релевантный
`skills/<skill-name>/SKILL.md`. PLAN-6E, PLAN-L0 и PLAN-9B-PRODUCER завершены.
Owner decision 2026-08-05 добавил «POST-AUDIT STABILIZATION PROGRAM».
PLAN-STAB-1 завершён 2026-08-05: мастер переживает сбой повторного render
через проверенный временный файл. PLAN-STAB-2 завершён 2026-08-05: resume и
explicit `stage=` dispatch пропускают уже завершённый `final_render`;
`--force-stage` по-прежнему пересобирает его. Текущий checkpoint —
PLAN-STAB-3 pending / not started (offline test guard), blocked до
отдельного owner-issued implementation prompt. PLAN-9B-2 остаётся pending /
not started и deferred за stabilization gate. Точное значение и следующее
действие — в самом плане.
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
