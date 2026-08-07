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
Owner decision 2026-08-05 добавил «POST-AUDIT STABILIZATION PROGRAM». PLAN-STAB-1 (`f0b69db`), PLAN-STAB-2
(`0eea5be`) и PLAN-STAB-3 (`9222519`) завершены 2026-08-05 и independently reviewed — verdicts ACCEPT WITH
MINOR, ACCEPT, ACCEPT WITH MINOR (owner-provided external review evidence, не отдельный Git commit).
PLAN-STAB-4 (`0947e51`, runtime-сеть fail-closed, `src/runtime_network.py`) completed 2026-08-06,
independently reviewed, verdict ACCEPT WITH MINOR (два findings non-blocking, не исправлены); gate
пункт 4 satisfied. PLAN-STAB-5 (C50 rights-review preservation) completed 2026-08-06, independently reviewed, verdict ACCEPT (findings: нет), GitHub Actions run `31084873522` зелёный (1646 tests OK); пункт 5 gate satisfied; rights review стал monotonic и снимается только подтверждённой per-asset `rights_declaration` (owner decision 2026-08-06 — намеренный safety contract, детали в [CURRENT_STATE.md](CURRENT_STATE.md)). Owner decision 2026-08-06 утвердил активный execution route после PLAN-STAB-5: PLAN-STAB-9 (non-blocking follow-up) → PLAN-STAB-7 + PLAN-STAB-8 → PLAN-STAB-6 или residual-risk decision → stabilization review → PLAN-9B-2. PLAN-STAB-9 (shared rights vocabulary owner) implementation completed 2026-08-06, independently reviewed 2026-08-06, verdict **ACCEPT WITH MINOR** (non-blocking wording finding, исправлен): единственным владельцем словаря допустимых `rights_status` стал `src/assets/models.py` (immutable `RIGHTS_ALLOWED_STATUSES`), независимая копия `ALLOWED_RENDER_RIGHTS` в `src/news/models.py` удалена, а её import paths сохранены как compatibility re-exports того же объекта; неизвестный и отсутствующий status остаются fail-closed, права словарём не выдаются. PLAN-STAB-9 closed и остаётся non-blocking follow-up. PLAN-STAB-7 и PLAN-STAB-8 closed 2026-08-06: implementation commit `42fa741`, repair commit `8357402` закрыл все четыре finding F1-F4 независимого review без изменения контрактов; independent review verdict ACCEPT WITH MINOR, repair re-review verdict ACCEPT WITH MINOR (blocking findings: 0); GitHub Actions run `31101208366` и repair run `31110155685` оба зелёные; пункт 7 gate satisfied, PLAN-STAB-8 остаётся non-blocking. `tools/qa/check_agent_docs.py` остаётся единственным владельцем обоих контрактов и теперь проверяет current-routing integrity (один authoritative checkpoint, три mirror-документа, `next_exact_action`, completed шаг не может быть текущим) и Git-aware docs freshness (каждый `last_verified_commit`/`baseline_head` — настоящий commit и ancestor HEAD; drift `source_paths` — advisory `NOTE`; отсутствие Git и shallow clone fail-closed; возраст считается от даты HEAD commit, а не от системных часов). PLAN-STAB-6 (Claude permission hardening) closed 2026-08-07: implementation `3cedff10`, repair `b0a3547` закрыл review findings F1-F5, independent re-review verdict ACCEPT WITH MINOR (blocking findings: 0), GitHub Actions run `31147454618` (headSha `49385dd`) зелёный (1749 tests OK, failures=0, errors=0); пункт 6 blocking gate satisfied. Bounded owner-driven stabilization review результатов PLAN-STAB-1..9 (пункт 8 blocking gate, без собственного PLAN-ID) завершён 2026-08-07 read-only — ничего не редактировал, не commit и не push; final verdict **CLEAR TO PROCEED TO PLAN-9B-2**, blocking findings 0, все четыре свойства (user-output preservation, offline/paid fail-closed behavior, rights safety, однозначный current routing) подтверждены, предварительный архитектурный repair перед PLAN-9B-2 не требуется; targeted evidence — `tools.qa.check_agent_docs` exit 0, permission/routing/governance tests 140 OK, rights/network cross-contract tests 78 OK, closure CI run `31149780652` (headSha `2186b20`) зелёный (1749 tests OK, failures=0, errors=0); пункт 8 blocking gate satisfied и stabilization gate пройден целиком. Checkpoint — **PLAN-9B-2** (expansion + hardcode migration): implementation не начата; единственный оставшийся prerequisite — отдельный owner-issued implementation prompt, то есть шаг ready for owner-issued implementation. Следующее точное действие — отдельный owner-issued implementation slice PLAN-9B-2 строго по существующему PLAN-9B-2 contract. Детали — в [CURRENT_STATE.md](CURRENT_STATE.md).
PLAN-9B-2 остаётся deferred за stabilization gate. CI repair (`9f9b6f2`, `bcf6c2a`, `8ca755f`, `68acdb2`)
вернул `.github/workflows/offline-tests.yml` в зелёное состояние (GitHub Actions run `31039985187`,
1/1 checks, failures=0, errors=0; локальный full suite — 1589 тестов, OK); PLAN-STAB-16 частично
выполнена — green CI baseline готов, secret scan/dependency audit/lint/type-check остаются pending.
Точное значение и следующее действие — в самом плане. [PROJECT_RESCUE_MASTER_PLAN.md](../handoff/PROJECT_RESCUE_MASTER_PLAN.md) остаётся историческим контекстом и текущий порядок выполнения не задаёт.

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
