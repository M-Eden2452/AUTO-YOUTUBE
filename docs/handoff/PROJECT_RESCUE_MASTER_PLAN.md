# AI-YouTube — Master Plan восстановления и передачи между AI-агентами

Статус: **выполняется; этапы 0–3 завершены**
Дата аудита и создания плана: **2026-07-28**
Репозиторий: `G:\Projects\AI-YouTube`
HEAD на момент аудита: `8d61a06`
Авторитет: фактический код и Git всегда важнее этого документа.

---

## 1. Как использовать этот документ в новом чате

Перед продолжением работы передай агенту этот файл и следующую инструкцию:

```text
Прочитай docs/handoff/PROJECT_RESCUE_MASTER_PLAN.md полностью.
Ничего не меняй, пока не проверишь фактический Git и текущий код.
Продолжай только с первого незавершённого этапа плана.
Выполняй один этап за раз, после него запускай указанные targeted tests.
Не начинай следующий этап, пока текущий не проверен.
После завершения этапа обнови статус и handoff в этом документе.
```

Обязательный порядок для нового агента:

1. Выполнить только read-only проверки:
   - `git status --short --branch`;
   - `git log -5 --oneline`;
   - `git diff --stat`.
2. Проверить, не изменился ли HEAD и не появилась ли незавершённая работа.
3. Прочитать только документы и код, относящиеся к текущему этапу.
4. Не считать старые оценки и списки файлов актуальными без проверки.
5. Не выполнять рефакторинг, перенос или удаление нескольких этапов одновременно.
6. После работы заполнить раздел «Текущий handoff».

---

## 2. Главный вывод аудита

Проект **не следует переписывать с нуля**.

Рекомендуемая стратегия:

> Создать чистый целевой каркас и переносить в него существующие рабочие возможности
> вертикальными срезами, сохраняя manifests, тесты, пользовательские проекты и
> обратную совместимость.

Почему полный rewrite не рекомендуется:

- существует реальный staged Shorts pipeline;
- есть resume и состояния стадий;
- реализовано безопасное подтверждение платного TTS;
- есть лицензии, provenance и checksums;
- работает asset selection, fallback и ручная замена визуальных слотов;
- реализованы voice, subtitles, timeline и FFmpeg render;
- существует общий read-only `ProjectRepository`;
- последний сохранённый отчёт утверждает прохождение 1306 тестов;
- существуют реальные E2E-проекты и MP4;
- в коде накоплено много неочевидных правил безопасности и совместимости.

Итоговая инженерная оценка на момент аудита: **5/10**.
Потенциал безопасного восстановления: **8/10**.

---

## 3. Факты на момент аудита

Эти данные являются снимком 2026-07-28 и должны перепроверяться в новом чате.

- 535 tracked-файлов.
- 332 Python-файла.
- Около 84 973 строк Python.
- Около 54 439 строк production-кода.
- Около 26 951 строк тестов.
- 95 тестовых модулей.
- Все 332 Python-файла статически разбирались без SyntaxError.
- Последний сохранённый full-suite результат: 1306 тестов, OK.
- Во время аудита тесты и рендеры не запускались.
- На момент аудита рабочее дерево было грязным:
  - 20 изменённых файлов;
  - примерно 1166 добавленных и 234 удалённых строк;
  - новый `.claude/settings.local.json`.

Крупные зоны риска:

- `src/news/asset_manager.py` — более 2100 строк;
- `src/assets/semantic_visual_evaluation.py` — более 1700 строк;
- `src/content_creation/cli.py` — более 1400 строк;
- `src/content_creation/wizard.py` — более 1200 строк;
- `src/content_creation/service.py` — около 840 строк;
- `pipeline.py` содержит перегруженный dispatch и legacy orchestration.

Найденные статические import-cycle:

- `src.content_creation.cli` ↔ `src.content_creation.wizard`;
- `src.assets.frame_sampling` ↔ `src.assets.perceptual_similarity`.

Отсутствовали:

- `pyproject.toml`;
- CI;
- formatter/linter/type-check configuration;
- dependency lock;
- единое структурированное логирование;
- единая project lock/idempotency policy;
- единая атомарная запись project JSON;
- модельно-независимый `AGENTS.md`;
- внешний `G:\AI-YouTube-System`;
- внешний `G:\AI-YouTube-Workspace`.

---

## 4. Что уже ценно и должно быть сохранено

Не переписывать без необходимости:

- `src/content_creation/` как существующий application service и canonical CLI;
- `src/news/` как основной рабочий `fullscreen_voiceover` workflow;
- `src/projects/ProjectRepository`;
- `src/project_foundation/`;
- `src/assets/provider_contract.py`;
- `src/providers/`;
- license/provenance/evidence contracts;
- `src/audio/` и платный approval gate;
- `src/subtitles/`;
- scene timeline и end-tail policy;
- resume/force-stage;
- manual asset replacement;
- network guard в тестах;
- старые manifests и tolerant readers;
- compatibility wrappers;
- реальные проекты, рендеры, voice samples и доказательства лицензий.

---

## 5. Главные архитектурные проблемы

### 5.1. Несколько поколений продукта

Одновременно существуют:

- canonical content creation CLI;
- root `pipeline.py`;
- legacy channel/video pipeline;
- staged `news_to_short`;
- Story Card workflow;
- Anime Factory;
- Solar/size-comparison эксперименты;
- wrappers в `apps/`;
- legacy scripts.

### 5.2. Несколько источников истины

- `job.json` и `project.json`;
- несколько способов описать channel;
- `pipeline.py` и `src.content_creation.cli`;
- современные providers и старые provider-классы;
- актуальные и исторические handoff-документы в одной навигации.

### 5.3. Крупные модули

CLI, Wizard, asset manager и application service одновременно:

- парсят ввод;
- выбирают workflow;
- читают конфигурацию;
- управляют стадиями;
- выполняют бизнес-логику;
- печатают пользовательский результат;
- обрабатывают ошибки.

### 5.4. Код, runtime и внешние зависимости смешаны

Внутри репозитория находятся:

- `projects/`;
- `outputs/`;
- `assets/`;
- `manual_assets/`;
- `music/`;
- `project_solar_vs_nuclear/`;
- `MOSS_TTS_Nano/`;
- `venv/`;
- evaluation frames и runtime reports.

### 5.5. Контекст для агентов быстро устаревает

- root `README.md` описывает старую архитектуру;
- `CLAUDE.md` привязан к одной модели;
- canonical audit содержит исторические дефекты;
- `AUTONOMOUS_PROGRESS.md` слишком велик для быстрого onboarding;
- отсутствует короткий нейтральный current-state документ.

---

## 6. Целевая продуктовая модель

```text
Application
  content_creator
    → fullscreen_voiceover
    → story_card

  video_repurposer
    → anime_clipper

  documentary
    → будущие longform workflows

  legacy_pipeline
    → только обратная совместимость
```

Story Card рассматривается как workflow/template внутри `content_creator`, а не как
отдельная инфраструктурная платформа.

Базовая модель:

```text
Application
  → Workflow
    → Format
      → Template
        → Channel
          → Project
            → Stages
              → Artifacts
                → Exports
```

---

## 7. Целевая структура репозитория

```text
AI-YouTube/
  README.md
  AGENTS.md
  CLAUDE.md                 # короткий adapter к AGENTS.md
  pyproject.toml
  .env.example

  src/
    ai_youtube/
      cli/
        main.py
        commands/
          create.py
          project.py
          assets.py
          diagnostics.py

      core/
        catalog/
        projects/
        stages/
        config/
        localization/
        rights/
        errors.py

      apps/
        content_creator/
          service.py
          workflows/
            fullscreen_voiceover/
            story_card/

        video_repurposer/
          service.py
          workflows/
            anime_clipper/

        documentary/
          README.md

        legacy_pipeline/
          adapter.py

      services/
        assets/
        audio/
        subtitles/
        rendering/
        export/

      infrastructure/
        providers/
        ffmpeg/
        filesystem/
        http/
        tts/

  config/
    system/
    policies/
    templates/
    providers/

  channels/

  tests/
    unit/
    contracts/
    integration/
    e2e/
    fixtures/

  docs/
    current/
      architecture/
      applications/
      workflows/
      operations/
    adr/
    archive/

  tools/
    qa/
    migrations/
    diagnostics/

  legacy/

  pipeline.py               # временный compatibility wrapper
  apps/                     # временные compatibility wrappers
```

Это целевая структура, а не разрешение на массовое перемещение.

---

## 8. Три независимых слоя

### 8.1. Репозиторий с кодом

```text
G:\Projects\AI-YouTube
```

Содержит:

- код;
- тесты;
- схемы;
- конфигурации по умолчанию;
- ADR;
- versioned техническую документацию;
- compatibility wrappers.

### 8.2. Runtime workspace

```text
G:\AI-YouTube-Workspace
```

Целевая структура:

```text
G:\AI-YouTube-Workspace\
  projects\
    content_creator\
    video_repurposer\
    documentary\
  exports\
  artifacts\
  media_library\
    user\
    providers\
  provider_cache\
  temp\
  runtime_reports\
  user_config\
```

### 8.3. Система знаний и skills

```text
G:\AI-YouTube-System
```

Целевая структура:

```text
G:\AI-YouTube-System\
  README.md
  START_HERE.md
  SYSTEM_MAP.md
  CURRENT_STATE.md

  knowledge\
    architecture\
    applications\
    workflows\
    contracts\
    operations\
    decisions\
    known_issues\

  policies\
    safety.md
    git.md
    paid_actions.md
    user_data.md

  skills\
    create_short_video_first\
    evaluate_render_quality\
    resume_project\
    replace_visual_slot\
    architecture_change\
    create_handoff\

  handoffs\
    CURRENT.md
    archive\

  templates\
  scripts\
```

Каждая knowledge-страница должна содержать:

- `status`;
- `last_verified_commit`;
- `last_verified_date`;
- `source_paths`;
- правило «код и Git имеют приоритет».

---

## 9. План будущих переименований

| Текущий путь | Целевой путь | Условие переноса |
|---|---|---|
| `src/content_creation/` | `src/ai_youtube/apps/content_creator/` | После выделения public service API |
| `src/news/` | `.../workflows/fullscreen_voiceover/` | После characterization tests |
| `src/templates/story_card/` | `.../workflows/story_card/` | После workflow contract tests |
| `src/project_foundation/` + `src/projects/` | `src/ai_youtube/core/projects/` | После общего public API |
| `src/assets/` | `services/assets/` + app-specific completion | После отделения generic от workflow-specific |
| `src/providers/` | `infrastructure/providers/` | После удаления старых provider adapters |
| `src/audio/` | `services/audio/` | С сохранением approval/manifests |
| `src/subtitles/` | `services/subtitles/` | После сохранения старых imports |
| `anime_factory/` | `apps/video_repurposer/workflows/anime_clipper/` | Только через adapter |
| `pipeline.py` | compatibility wrapper | Удалять последним |
| старые `src/*.py` | `legacy/` или соответствующий service | После import map и tests |
| `docs/handoff/*` | `docs/current` или `docs/archive` | После создания короткого current state |
| runtime-папки | внешний Workspace | Copy → verify → switch |
| `venv`, `MOSS_TTS_Nano` | внешняя toolchain/vendor зона | После воспроизводимой установки |

---

## 10. Политика удаления

### 10.1. Потенциально безопасно после baseline

- `__pycache__/`;
- `*.pyc`;
- локальные `.claude/settings.local.json`;
- локальные scheduled-task lock-файлы;
- подтверждённо пустые runtime-каталоги.

### 10.2. Удалять только после проверки callers

- встроенные `PexelsAssetProvider`, `PixabayAssetProvider`,
  `UnsplashAssetProvider` в `src/news/asset_manager.py`;
- `src/news/stock_video_downloader.py`;
- `packages/`, если это только placeholder;
- `content/story_card_jobs.tsv`, если нет потребителя;
- старые thumbnail/music/layout реализации;
- duplicate adapters и compatibility imports.

### 10.3. Архивировать или переносить, не удалять сразу

- `legacy/`;
- старые audits и handoffs;
- `project_solar_vs_nuclear/`;
- tracked JSON из `outputs/`;
- крупные evaluation frames;
- debug-проект с именем `wizard_установил_questionary...`;
- повторные тестовые runtime-проекты.

### 10.4. Никогда не удалять автоматически

- `.env`;
- `projects/`;
- `assets/`;
- `manual_assets/`;
- `music/`;
- voice samples;
- `MOSS_TTS_Nano/`;
- MP4/WAV и пользовательские исходники;
- evidence и license proof;
- любой незакоммиченный код.

Пустой `__init__.py` не является мусором автоматически.

---

## 11. Общие правила выполнения плана

1. Один этап — один ограниченный набор изменений.
2. Сначала characterization test, затем изменение.
3. После каждого этапа — targeted tests.
4. Full offline suite — на границах крупных этапов.
5. Не выполнять сеть, provider search, Vision, TTS или платные API без отдельного
   разрешения пользователя.
6. Не запускать реальный render, если этап проверяется синтетическими fixtures.
7. Не изменять `.env`.
8. Не использовать destructive Git.
9. Не удалять runtime и пользовательские данные.
10. Не выполнять массовое форматирование вместе с рефакторингом.
11. Не создавать второй contract, resolver, repository или provider layer.
12. Любая schema change обязана иметь tolerant reader и migration note.
13. Старый entrypoint удаляется только после compatibility period.
14. При обнаружении незапланированного большого изменения остановиться и подготовить
    отдельный план.

---

## 12. Этапы восстановления

### Этап 0. Защитить текущее состояние

Статус: [x] завершён 2026-07-28

Задачи:

1. Проверить фактический `git status`.
2. Не начинать cleanup при грязном рабочем дереве.
3. Закончить, проверить и отдельно зафиксировать текущую работу либо безопасно
   отложить её по решению пользователя.
4. Получить чистый baseline.
5. Сохранить список последних рабочих проектов и manifests.
6. Зафиксировать HEAD и результаты тестов.

Критерий готовности:

- рабочее дерево чистое;
- незавершённая работа не потеряна;
- baseline воспроизводим.

---

### Этап 1. Characterization и воспроизводимость

Статус: [x] завершён 2026-07-28

Задачи:

1. Зафиксировать публичные CLI и их ожидаемые результаты.
2. Добавить characterization tests для:
   - `pipeline.py`;
   - `src.content_creation.cli`;
   - Anime Factory;
   - project status/list/resume;
   - paid-call denial.
3. Зафиксировать схемы:
   - `job.json`;
   - `project.json`;
   - stage state;
   - assets;
   - voice;
   - evidence;
   - render/export.
4. Добавить `pyproject.toml`.
5. Добавить dependency lock.
6. Добавить offline CI.
7. Зафиксировать `.gitattributes` и line endings.
8. Не выполнять массовое форматирование.

Критерий готовности:

- чистая установка воспроизводима;
- offline suite выполняется в CI;
- текущие CLI contracts защищены.

---

### Этап 2. Source of truth и onboarding агентов

Статус: [x] завершён 2026-07-28

Задачи:

1. Создать короткий модельно-независимый `AGENTS.md`.
2. Превратить `CLAUDE.md` в тонкий adapter.
3. Создать:
   - `START_HERE.md`;
   - `SYSTEM_MAP.md`;
   - короткий `CURRENT_STATE.md`.
4. Разделить `docs/current`, `docs/adr`, `docs/archive`.
5. Создать первые skills:
   - `create_short_video_first`;
   - `evaluate_render_quality`;
   - `resume_project`;
   - `replace_visual_slot`;
   - `architecture_change`;
   - `create_handoff`.
6. Добавить проверку ссылок и stale metadata.
7. Не копировать огромный progress-log в current state.

Критерий готовности:

- новый агент начинает работу после чтения не более трёх коротких документов;
- актуальные и исторические знания физически разделены.

---

### Этап 3. Единая система путей

Статус: [x] завершён 2026-07-28

Задачи:

1. Создать `WorkspacePaths`/`ApplicationPaths`.
2. Убрать production-зависимость от `Path.cwd()`.
3. Убрать hardcoded `G:\...`.
4. Поддержать workspace через config/env/CLI.
5. Сохранить fallback на старые `projects/` и `outputs/`.
6. Проверять пути на tempfile.
7. Ничего физически не переносить.

Критерий готовности:

- код работает с произвольным workspace;
- старые проекты продолжают читаться.

---

### Этап 4. Канонический CLI и app boundaries

Статус: [ ] не начат

Задачи:

1. Создать один dispatcher: `python -m ai_youtube`.
2. Разнести CLI-команды по отдельным модулям.
3. Оставить `pipeline.py` и `apps/*` wrappers.
4. Убрать бизнес-логику из CLI и Wizard.
5. Сделать capability registry честным.
6. Не показывать disabled приложения как готовые.
7. Устранить import-cycle CLI ↔ Wizard.

Критерий готовности:

- один канонический CLI;
- старые команды проходят compatibility tests.

---

### Этап 5. Project и storage foundation

Статус: [ ] не начат

Задачи:

1. Использовать существующий `ProjectRepository`.
2. Не создавать третью project-систему.
3. Определить единый `ProjectView`.
4. Добавить schema version для news manifests.
5. Перевести NewsProjectStore на общий atomic storage.
6. Добавить project lock.
7. Добавить idempotency для повторных стадий.
8. Сохранить чтение старых `job.json` и `project.json`.
9. Не выполнять массовую миграцию.

Критерий готовности:

- один read API;
- один storage primitive;
- старые проекты читаются;
- новые записи атомарны.

---

### Этап 6. Разделение крупных модулей

Статус: [ ] не начат

Выполнять строго по одному модулю:

1. `src/news/asset_manager.py`:
   - orchestration;
   - provider search;
   - selection;
   - download;
   - completion.
2. `src/content_creation/cli.py`:
   - command modules;
   - presentation отдельно.
3. `src/content_creation/wizard.py`:
   - state;
   - steps;
   - presentation.
4. `src/content_creation/service.py`:
   - отдельные use cases.
5. `src/assets/semantic_visual_evaluation.py`:
   - runtime;
   - evaluation tooling.
6. `pipeline.py`:
   - только dispatch и compatibility.
7. Устранить cycle frame sampling ↔ perceptual similarity.

Критерий готовности:

- нет orchestration-функций на сотни строк;
- нет статических import-cycle;
- поведение подтверждено тестами.

---

### Этап 7. Консолидация providers

Статус: [ ] не начат

Задачи:

1. Зафиксировать один provider contract.
2. Перевести callers на `src/providers`.
3. Удалить встроенные provider-классы только после тестов.
4. Удалить старый downloader только после import/runtime проверки.
5. Централизовать:
   - timeout;
   - retry;
   - rate limit;
   - diagnostics;
   - download validation;
   - license normalization.
6. Не добавлять новых providers в ходе консолидации.

Критерий готовности:

- provider добавляется одним adapter-модулем;
- renderer и workflow не знают детали HTTP API.

---

### Этап 8. Миграция приложений вертикальными срезами

Статус: [ ] не начат

Порядок:

1. `fullscreen_voiceover`;
2. `story_card`;
3. `anime_clipper` через `video_repurposer` adapter;
4. legacy pipeline;
5. documentary — только после реального рабочего шаблона.

Каждый перенос включает:

- application service;
- project contract;
- workflow;
- targeted tests;
- compatibility wrapper;
- migration note.

Критерий готовности:

- рабочий workflow переносится целиком;
- старый entrypoint остаётся совместимым.

---

### Этап 9. Внешний runtime workspace

Статус: [ ] не начат

Задачи:

1. Выполнить dry-run inventory.
2. Создать backup.
3. Копировать, а не перемещать.
4. Проверить counts, manifests и checksums.
5. Включить dual-read и single-write в новый workspace.
6. Проверить resume старого проекта.
7. Проверить создание нового проекта.
8. Старые данные оставить до отдельного подтверждения владельца.

Критерий готовности:

- новые runtime-данные создаются вне Git;
- старые проекты продолжают читаться;
- rollback не требует восстановления удалённых данных.

---

### Этап 10. Cleanup

Статус: [ ] не начат

Задачи:

1. Удалить кэши.
2. Заархивировать исторические документы.
3. Убрать подтверждённые placeholders.
4. Удалить доказанные code duplicates.
5. Перестать отслеживать generated outputs.
6. Перенести тяжёлые evaluation artifacts.
7. Проверить `.gitignore`.
8. Не удалять пользовательские проекты и медиа.

Критерий готовности:

- корень содержит только код, конфигурацию и versioned документы;
- runtime находится во внешнем workspace;
- каждый удалённый code path имеет доказанную замену.

---

### Этап 11. Финальная инженерная проверка

Статус: [ ] не начат

Проект считается восстановленным, когда:

- существует один канонический CLI;
- старые команды работают через wrappers;
- существует один ProjectRepository;
- существует один storage layer;
- существует один path/config resolver;
- существует один provider contract;
- runtime по умолчанию находится вне Git;
- нет production hardcode конкретного компьютера;
- CI выполняет offline suite;
- нет import-cycle;
- платные вызовы требуют явного approval;
- новый агент получает актуальный контекст из нескольких коротких файлов;
- Short можно создать, продолжить и проверить без огромного prompt;
- MP4 проверяется технически и визуально.

---

## 13. Что делать первым

Первое действие при возобновлении плана:

> Проверить текущее рабочее дерево и получить безопасный чистый baseline.

Не начинать с:

- перемещения папок;
- удаления проектов;
- создания нового репозитория с переписанным кодом;
- массового форматирования;
- добавления новых providers;
- UI;
- RAG или vector database;
- swarm/subagents;
- физической миграции runtime.

---

## 14. Текущий handoff

Этот раздел обновляется после каждого выполненного этапа.

```text
Последнее обновление: 2026-07-28
Текущий этап: Этап 3 — завершён; следующий этап 4 ещё не начат
Исходный HEAD аудита: 8d61a06
Проверенный code baseline HEAD: 8485a21
Коммит этапа 1: c8eb8f6
Коммит этапа 2 и agent context: b7350b3
Коммит handoff этапа 2: 8ed340d
Исходный HEAD этапа 3: 8ed340d
Implementation HEAD этапа 3: 0cd0e11
Текущий HEAD перед handoff-only коммитом: 0cd0e11
Рабочее дерево: подготовлены ADR 0002, current metadata и handoff этапа 3
Выполнено:
- master plan полностью прочитан; фактические Git/HEAD/status/diff проверены до изменений
- до изменения поведения добавлен characterization test: явный --projects-root остаётся изолированным и авторитетным
- в существующий src.config_resolver добавлены WorkspacePaths/ApplicationPaths и единая модель runtime/static путей
- workspace поддержан через CLI, AI_YOUTUBE_WORKSPACE и JSON path config с приоритетом CLI > env > config > legacy default
- versioned config/resources привязаны к корню репозитория; production-зависимость от cwd и машинный hardcoded G:\ удалены
- ProjectRepository читает primary workspace с fallback на legacy projects; outputs имеют совместимый legacy fallback
- явный --projects-root сохранён как изолированный compatibility contract
- default workspace намеренно остаётся корнем репозитория до этапа 9; физический перенос runtime не выполнялся
- content CLI, wizard/service, news workflow, root pipeline и project foundation используют общий resolver
- создан ADR 0002 о workspace paths и storage compatibility
Targeted checks этапа 3:
- pre-change: .\venv\Scripts\python.exe -B -m unittest tests.test_stage3_workspace_paths — 1 test, OK, 0.790 s
- основной affected-набор — 366 tests, OK, 78.469 s
- wizard/assets/subtitles/story-card integration — 70 tests, OK, 20.908 s
- capabilities smoke из cwd вне репозитория — OK
Full offline suite: не запускался по указанию пользователя; для этапа 3 не требовался
Runtime-проекты и пользовательские media не изменялись и не удалялись
Runtime project IDs/artifacts: создавались только внутри TemporaryDirectory тестов и автоматически удалены; постоянные artifacts не создавались
Не выполнено: этапы 4–11, cleanup, физическая миграция runtime, реальные provider/API/TTS вызовы
Новый known issue: не обнаружен
Платные действия: не выполнялись
Сеть/API: не выполнялись
Следующее действие после фиксации handoff: git status --short --branch; затем начинать только этап 4 — «Канонический CLI и app boundaries»
Главный запрет: не начинать этап 5, пока этап 4 не завершён и не проверен
```

---

## 15. Шаблон handoff для следующего чата

```text
Задача:

Исходный HEAD:
Текущий HEAD:

Git status:

Этап master plan:

Что было проверено:

Что было изменено:

Какие файлы затронуты:

Targeted tests:

Full offline suite:

Runtime project IDs:

Созданные artifacts:

Сеть/API:

Платные действия:

Найденные root causes:

Новые known issues:

Что нельзя повторять:

Блокеры:

Следующая точная команда:
```
