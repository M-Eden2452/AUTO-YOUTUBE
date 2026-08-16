---
status: current
last_verified_commit: 5787c61
last_verified_date: 2026-08-15
source_paths:
  - AGENTS.md
  - docs/current/PROJECT_EXECUTION_PLAN.md
  - docs/current/CURRENT_STATE.md
  - docs/current/SYSTEM_MAP.md
  - docs/current/PRODUCT_PLAN.md
  - docs/current/CLEANUP_REGISTRY.md
  - src/ai_youtube/cli
  - skills
  - tools/qa/check_agent_docs.py
  - tests/test_stage2_agent_onboarding.py
---

# Start Here

AI-YouTube — локальная offline-first платформа создания видео и переработки
длинных source videos. Production-ready сегодня только два Shorts templates.
Код и фактический Git важнее этого документа.

Это маршрутный документ. Он не пересказывает историю закрытий: у каждого
закрытого шага единственный дом — активный execution plan, у каждого findings и
retirement decision — cleanup registry.

## Порядок чтения

1. [AGENTS.md](../../AGENTS.md) — канонический контракт работы с репозиторием.
2. Git read-only командами, перечисленными там.
3. [CURRENT_STATE.md](CURRENT_STATE.md) — что существует и что ограничено сегодня.
4. [SYSTEM_MAP.md](SYSTEM_MAP.md) — только для архитектурной задачи.

## Маршрут

Текущий checkpoint — **PLAN-9D**. Авторитет — поле `current_checkpoint` во
frontmatter [PROJECT_EXECUTION_PLAN.md](PROJECT_EXECUTION_PLAN.md), а не этот
абзац; там же `next_exact_action` и evidence каждого закрытия.

**LIVE-5 выполнен 2026-08-15** (`docs/audits/LIVE_5_2026-08-15.md`, verdict
PARTIAL: 5/5 сцен получили слот, но 2/5 верны по смыслу, видео-слотов 0, MP4 без
субтитров). Набор, объявленный обязательным до него (`VA-NEW-01`…`VA-NEW-06`,
`VA-NEW-08`, `VA-NEW-09`, budget guards `VA-NEW-10`/`VA-NEW-12`), закрыт;
Review #3 над M2-A и M2-B закрыт с verdict ACCEPT WITH MINOR NOTES. Следующее
точное действие берётся из `next_exact_action` плана, а не из этого абзаца.
Любой следующий live-прогон — платное сетевое действие и требует отдельного
явного разрешения владельца; этим документом оно не выдаётся.

Вторая часть `WP0-B` (governance/docs diet) остаётся открытой — см. блок
«WP0-B (governance/docs diet) — placement» в плане.

## Кто чем владеет

- порядок работ, checkpoint, статусы шагов и evidence закрытий —
  [PROJECT_EXECUTION_PLAN.md](PROJECT_EXECUTION_PLAN.md);
- направление продукта и сохранённые идеи — [PRODUCT_PLAN.md](PRODUCT_PLAN.md).
  Идея оттуда не реализуется напрямую: сначала она становится bounded slice
  в execution plan;
- модули, границы и владельцы — [SYSTEM_MAP.md](SYSTEM_MAP.md), подробная
  проверенная карта — [ARCHITECTURE_BOUNDARY_MAP.md](ARCHITECTURE_BOUNDARY_MAP.md);
- findings, retirement decisions и exit conditions —
  [CLEANUP_REGISTRY.md](CLEANUP_REGISTRY.md);
- процедуры под конкретную задачу — `skills/<skill-name>/SKILL.md`. Для Claude
  Code root `skills/` не считается автоматически загруженным: нужный файл
  открывается вручную перед специализированной задачей.

[docs/archive](../archive/README.md) и [docs/audits](../audits/README.md) — это
evidence, а не текущий источник истины; не считай их актуальными без проверки
кода. [PROJECT_RESCUE_MASTER_PLAN.md](../handoff/PROJECT_RESCUE_MASTER_PLAN.md)
остаётся историческим контекстом и текущий порядок работ не задаёт.

## Безопасная проверка интерфейса

```powershell
.\venv\Scripts\python.exe -m ai_youtube capabilities --json
```

`python -m ai_youtube` — канонический CLI. `python -m src.content_creation.cli`,
`pipeline.py` и `apps/*` пока сохранены как compatibility entrypoints, но каждый
должен получить exit condition в cleanup registry; бессрочный wrapper не
является финальным состоянием.

Для отдельного runtime workspace используй глобальный `--workspace`, переменную
`AI_YOUTUBE_WORKSPACE` или path config. Без явной настройки legacy workspace
остаётся корнем репозитория; физическая миграция runtime не выполнялась.

Не запускай сеть, providers, Vision, TTS, скачивание, render или платные
действия без отдельного разрешения владельца.
