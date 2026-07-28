---
status: current
last_verified_commit: b7350b3
last_verified_date: 2026-07-28
source_paths:
  - AGENTS.md
  - docs/handoff/PROJECT_RESCUE_MASTER_PLAN.md
  - src/content_creation/cli.py
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
Исторические handoff и отчёты находятся в [docs/archive](../archive/README.md) и не
являются текущим источником истины.

Безопасная проверка интерфейса:

```powershell
.\venv\Scripts\python.exe -m src.content_creation.cli capabilities --json
```

Не запускай сеть, providers, Vision, TTS, скачивание или платные действия без
отдельного разрешения пользователя.
