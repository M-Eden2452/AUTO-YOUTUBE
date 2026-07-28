# AI-YouTube — инструкции для агентов

Этот файл — канонический, модельно-независимый контракт работы с репозиторием.
Код и фактический Git всегда важнее документации.

## Быстрый старт

1. Выполни `git status --short --branch`, `git log -5 --oneline` и `git diff --stat`.
2. Прочитай [docs/current/START_HERE.md](docs/current/START_HERE.md).
3. Для архитектурной работы открой
   [docs/current/SYSTEM_MAP.md](docs/current/SYSTEM_MAP.md); для статуса —
   [docs/current/CURRENT_STATE.md](docs/current/CURRENT_STATE.md).
4. Если задача продолжает rescue plan, полностью прочитай
   [docs/handoff/PROJECT_RESCUE_MASTER_PLAN.md](docs/handoff/PROJECT_RESCUE_MASTER_PLAN.md)
   и выполняй только первый незавершённый этап.

Не считай исторические отчёты в `docs/archive/` актуальными без проверки кода.

## Среда и проверки

- Рабочая среда — Windows; запускай Python через `.\venv\Scripts\python.exe`.
- Не используй bare `python`, `pip` или `pytest`: системный Python может иметь другую версию.
- Сначала добавляй characterization test, затем меняй поведение.
- Запускай только targeted tests текущего изменения. Full offline suite нужен на границе
  крупного этапа или по явному запросу.
- Не смешивай массовое форматирование, cleanup и функциональное изменение.
- После изменения документации запускай
  `.\venv\Scripts\python.exe -m tools.qa.check_agent_docs`.

## Безопасность

- Не читай и не изменяй `.env`, `.env.*`, secrets, credentials и private keys.
- Не выполняй сеть, provider search, скачивание, Vision, TTS и другие платные/API-вызовы
  без отдельного явного разрешения пользователя.
- Наличие настроенного провайдера не является разрешением на платный вызов.
- Не выполняй destructive Git, force operations и очистку чужих незакоммиченных изменений.
- Не удаляй и не перезаписывай `projects/`, media, manifests, evidence, license proof,
  voice samples и готовые MP4/WAV.
- Не запускай реальный render, если изменение проверяется синтетическим fixture.

## Архитектурные границы

- `src.content_creation.cli` — текущий CLI создания контента; `pipeline.py` обслуживает
  legacy и maintenance-команды. Единый новый dispatcher относится к этапу 4 rescue plan.
- Активное приложение — `content_creator`. Не представляй disabled/planned приложения
  как готовые.
- Активные шаблоны: `fullscreen_voiceover_v1` и `story_card_text_only_v1`.
- `src/projects/ProjectRepository` — общий read-only слой над существующими
  `job.json` и `project.json`; не создавай третью project-систему.
- Не создавай второй provider contract, asset pipeline, voice registry, subtitle engine,
  configuration resolver, readiness contract или completion ladder.
- `strict` остаётся режимом completion по умолчанию. `draft_complete` — явный opt-in,
  всегда `publish_ready=false` и не ослабляет права, `must_avoid`, conflict и
  misleading-content gates.
- Сохраняй tolerant readers, compatibility wrappers, resume/force-stage и approval gates.

## Versioned agent skills

Процедуры находятся в `skills/`:

- `create-short-video-first`
- `evaluate-render-quality`
- `resume-project`
- `replace-visual-slot`
- `architecture-change`
- `create-handoff`

Используй только skill, соответствующий задаче, и проверяй команды по текущему `--help`.

## Завершение работы

- Повтори `git status`, проверь diff и запусти targeted tests.
- Не заявляй о тестах, API-вызовах или artifacts, которых фактически не было.
- Обнови metadata в `docs/current/`, если изменились описанные границы.
- Для rescue stage обнови статус и «Текущий handoff» в master plan.
