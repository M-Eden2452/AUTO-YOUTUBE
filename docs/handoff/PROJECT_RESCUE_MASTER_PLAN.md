# AI-YouTube — Master Plan восстановления и передачи между AI-агентами

Статус: **выполняется; этапы 0–4.6 и bounded slice 5A завершены; этап 4.5
сохранён как историческая диагностика и снят с critical path; этап 5 —
Project и storage foundation — выполняется, следующий slice 5B**
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

> **Это гипотеза границ, а не обязательное дерево для массового переноса.**
> Названия слоёв (`core`, `services`, `infrastructure`) и точное расположение
> модулей подтверждаются только после карты зависимостей, фиксации публичных
> контрактов и первого вертикального переноса. Нельзя перемещать файл лишь ради
> соответствия этому дереву.

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
3. После каждого этапа — targeted tests в радиусе изменённой зависимости.
4. Full offline suite не является обязательным локальным шагом: запускать его в CI после коммита либо локально только при изменении общих contracts, storage, paths, providers или compatibility-слоя.
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

### Value gate для инфраструктуры

Инфраструктурную работу выполнять только если она хотя бы в одном из случаев:

- снижает риск потери данных, лишних платных вызовов или поломки продукта;
- разблокирует текущий workflow `create` / `resume` / `render`;
- уменьшает повторяющуюся работу агента и риск потери контекста;
- предотвращает уже известную регрессию.

В противном случае задача попадает в backlog. Product/video evidence не является
обязательным checkpoint для архитектурных, compatibility, cleanup и
data-safety этапов.

### Бюджет проверок

- Документация, skills и metadata: только релевантная проверка документации.
- Локальный parser, wrapper или команда: compatibility-тесты этой команды.
- Один workflow-модуль: его тесты и ближайшая интеграционная проверка.
- Contracts, storage, paths, providers и compatibility: затронутое семейство
  тестов; полный suite — CI checkpoint после отдельного коммита.
- Пользовательский workflow: небольшой synthetic smoke важнее полного suite,
  если он проверяет реальную цепочку риска.

Не запускать тест шире радиуса зависимости без явно записанной причины.

### Бюджет области и handoff

Обычный подэтап затрагивает не более 8 production-файлов **или** ровно один
публичный контракт / workflow boundary. Если требуется превысить этот предел
либо принять более одного независимого архитектурного решения, остановиться,
разделить работу и сделать handoff. У каждого подэтапа — отдельные проверка,
commit и handoff; исключение допускается только с записанным обоснованием.

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

Статус: [x] завершён 2026-07-28

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

Уточнение границы: этап 4 отвечает за внешний dispatcher, регистрацию команд,
capability и compatibility wrappers. Дальнейшее внутреннее разделение CLI,
Wizard и service, уменьшение крупных функций и перенос presentation-логики
выполняются только в подэтапах 6B–6D. Этап 4 не переоткрывается, если не меняется
публичный command contract.

---

### Этап 4.5. Product Evidence Gate

Статус: [x] закрыт 2026-07-28 как исторический диагностический snapshot;
решением владельца от 2026-07-28 снят с critical path.

Сохранённый отчёт:
[docs/current/PRODUCT_EVIDENCE_GATE.md](../current/PRODUCT_EVIDENCE_GATE.md).

Решение владельца:

- не повторять `create`, `resume`, TTS, provider search/download, render,
  contact-sheet или visual quality gate в рамках rescue plan;
- незавершённый Product Repair 4.5-R закрыть без продолжения;
- результат `FAIL` сохранить только как исторический факт о конкретном
  reference project, а не как блокер архитектуры;
- перейти к структуре, зависимостям, границам модулей, консолидации,
  доказанному удалению лишнего и cleanup.

---

### Этап 4.6. Архитектурная инвентаризация и карта cleanup

Статус: [x] завершён 2026-07-28

Это был read-only этап относительно production code и runtime data: сначала
доказательства и карта, затем отдельные изменения.

Задачи:

1. Зафиксировать фактическое дерево production-модулей, entrypoints и
   compatibility wrappers.
2. Построить карту imports/callers/tests для крупных модулей и публичных
   contracts.
3. Отдельно отметить persisted schemas, runtime roots и пользовательские данные,
   которые нельзя потерять при переносе или удалении.
4. Классифицировать каждый архитектурный кандидат:
   `keep`, `split`, `merge`, `move`, `archive`, `delete` или `do_not_touch`.
5. Для каждого `delete`-кандидата записать:
   - callers/imports;
   - рабочую замену;
   - compatibility period;
   - targeted tests;
   - риск для persisted projects/media.
6. Подтвердить целевые границы приложений, services и infrastructure по
   фактическим зависимостям, а не по желаемому дереву каталогов.
7. Сформировать очередь малых implementation slices; не перемещать и не удалять
   production code на этом этапе.

Критерий готовности:

- в `docs/current/` есть актуальная dependency/boundary map;
- существует проверяемый cleanup registry с доказательствами для удаления;
- для первого structural slice указаны точные файлы, callers и targeted tests;
- массовое перемещение и преждевременное удаление не выполнялись.

Результаты:

- [ARCHITECTURE_BOUNDARY_MAP.md](../current/ARCHITECTURE_BOUNDARY_MAP.md);
- [CLEANUP_REGISTRY.md](../current/CLEANUP_REGISTRY.md);
- первый structural slice — 5A: characterization-first перевод
  `NewsProjectStore.write_json` на существующий
  `project_foundation.atomic_write_json`.

---

### Этап 5. Project и storage foundation

Статус: [ ] выполняется; slice 5A завершён 2026-07-28, следующий slice 5B

Задачи:

1. Использовать существующий `ProjectRepository`.
2. Не создавать третью project-систему.
3. Определить единый `ProjectView`.
4. Добавить schema version для news manifests.
5. Перевести NewsProjectStore на общий atomic storage. **Выполнено в slice 5A,
   implementation commit `87e272a`.**
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

Каждый подэтап ниже независим: отдельные targeted tests, commit и handoff.
Не объединять их в одну сессию без записанного исключения из бюджета области.

#### 6A. Asset manager

`src/news/asset_manager.py`: отделить orchestration от provider search,
selection, download и completion.

#### 6B. Внутренности CLI

Разделить внутренности `src/content_creation/cli.py` и presentation-слой.
Внешний dispatcher и compatibility не менять без необходимости: это граница
этапа 4.

#### 6C. Wizard

Разделить `src/content_creation/wizard.py` на state, шаги и presentation.

#### 6D. Application service

Выделить в `src/content_creation/service.py` отдельные use cases и сделать
оркестрацию явной.

#### 6E. Semantic evaluation

Разделить в `src/assets/semantic_visual_evaluation.py` runtime и evaluation
tooling.

#### 6F. Legacy pipeline

Оставить `pipeline.py` тонким фасадом dispatch и compatibility без дублирования
бизнес-логики.

#### 6G. Оставшиеся import cycles

Устранить cycle frame sampling ↔ perceptual similarity и другие обнаруженные
циклы отдельными малыми изменениями.

Критерий готовности:

- нет orchestration-функций на сотни строк;
- нет статических import-cycle;
- поведение каждого подэтапа подтверждено его targeted tests;
- нет статических import-cycle после 6G.

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

### Этап 9. Retire compatibility и удалить доказанное лишнее

Статус: [ ] не начат

Задачи:

1. Брать кандидатов только из cleanup registry этапа 4.6.
2. Удалять по одному bounded slice после проверки imports, callers и
   compatibility entrypoints.
3. Сначала удалять доказанные code duplicates, неиспользуемые adapters,
   placeholders и dead wrappers.
4. Старый provider/downloader удалять только после перевода callers на
   существующий `src/providers` contract и targeted tests.
5. Compatibility wrapper удалять только после зафиксированного периода
   совместимости и отсутствия callers.
6. Сомнительный или исторически ценный код архивировать, а не удалять.
7. Каждый deletion slice оформлять отдельными diff, targeted tests, commit и
   handoff.
8. Не удалять `projects/`, manifests, media, evidence, license proof, voice
   samples, готовые MP4/WAV и пользовательские исходники.

Критерий готовности:

- каждый удалённый code path имеет доказанную замену или доказанное отсутствие
  callers;
- compatibility и persisted-project contracts продолжают проходить targeted
  tests;
- в commit нет runtime или пользовательских данных;
- rollback каждого slice ограничен одним commit.

---

### Этап 10. Repository/runtime cleanup и разделение рабочих зон

Статус: [ ] не начат

Задачи:

1. Удалить только воспроизводимые кэши и временные файлы.
2. Заархивировать устаревшие audits, handoffs и generated reports.
3. Перестать отслеживать подтверждённые generated outputs и обновить
   `.gitignore`.
4. Провести dry-run inventory runtime-каталогов, тяжёлых artifacts и toolchain.
5. Для внешнего workspace использовать только `copy → verify → switch`;
   массовое перемещение и удаление источника запрещены.
6. Проверить counts, manifests и checksums до и после копирования.
7. Сохранить dual-read старых roots и направлять новые записи во внешний
   workspace только отдельным bounded изменением.
8. Старые runtime-данные оставить до отдельного подтверждения владельца.
9. Не смешивать filesystem cleanup с архитектурным refactor или contract change.

Критерий готовности:

- корень содержит только код, конфигурацию и versioned документы;
- generated/runtime данные не загрязняют Git;
- старые проекты продолжают читаться;
- внешний workspace проверен без удаления исходных данных;
- каждый cleanup diff воспроизводим и не затрагивает пользовательские media.

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
- крупные orchestration-модули разделены по подтверждённым границам;
- cleanup registry закрыт либо содержит явно отложенные `do_not_touch` записи;
- отсутствуют доказанные dead imports, duplicate implementations и
  неподтверждённые compatibility wrappers;
- платные вызовы требуют явного approval;
- новый агент получает актуальный контекст из нескольких коротких файлов;
- persisted projects, manifests и пользовательские media сохранены;
- финальная проверка архитектуры не требует создания, рендера или визуальной
  оценки нового видео.

---

## 13. Что делать первым

Первое действие при возобновлении плана:

> Начать только slice 5B: characterization-first добавить additive schema
> version news manifest в `src/news/models.py` и `schemas/job.schema.json`,
> сохранив tolerant read старых `job.json`; не объединять с project lock,
> idempotency или migration.

Не начинать с:

- перемещения папок;
- удаления code path без callers/replacement evidence;
- удаления проектов;
- создания нового репозитория с переписанным кодом;
- массового форматирования;
- добавления новых providers;
- создания или рендера reference video;
- UI;
- RAG или vector database;
- swarm/subagents;
- физической миграции runtime.

---

## 14. Текущий handoff

Этот раздел обновляется после каждого выполненного этапа.

```text
Последнее обновление: 2026-07-28
Завершённый bounded slice: 5A atomic NewsProjectStore
Текущий этап: 5 Project и storage foundation — выполняется
Следующий bounded slice: 5B additive news schema version
Исходный HEAD slice 5A: 736f0c6
Implementation commit slice 5A: 87e272a
Ветка: master
Git до slice 5A: чистый
Исходный HEAD аудита: 8d61a06
Проверенный code baseline HEAD: 8485a21
Коммит этапа 1: c8eb8f6
Коммит этапа 2 и agent context: b7350b3
Коммит handoff этапа 2: 8ed340d
Исходный HEAD этапа 3: 8ed340d
Implementation HEAD этапа 3: 0cd0e11
Коммит handoff этапа 3: ac9c313
Исходный HEAD этапа 4: ac9c313
Implementation HEAD этапа 4: 94034f2
Коммит handoff этапа 4: 65cef10
Evidence-коммит этапа 4.5: fb374fd
Коммит локального аудита 4.5-R: 05cc8ed
Коммит этапа 4.6: 736f0c6
Выполнено:
- полностью прочитаны master plan, START_HERE, CURRENT_STATE, SYSTEM_MAP и architecture-change skill
- проверены NewsProjectStore, общий atomic_write_json, фактические callers и targeted test family
- сначала добавлен characterization JSON shape/UTF-8/trailing newline, os.replace и отсутствия temporary file
- подтверждено ожидаемое падение characterization до production change: os.replace called 0 times
- NewsProjectStore.write_json переведён на существующий src.project_foundation.storage.atomic_write_json
- сохранены public static method, JSON shape, UTF-8, trailing newline и существующие callers
Изменения production code: только src/news/project_store.py
Characterization: tests/test_news_to_short_models.py
Удаления и перемещения: не выполнялись
Targeted checks:
- .\venv\Scripts\python.exe -m unittest tests.test_news_to_short_models: OK, 4 tests
- .\venv\Scripts\python.exe -m unittest tests.test_project_repository tests.test_news_to_short_pipeline: OK, 18 tests
- .\venv\Scripts\python.exe -m tools.qa.check_agent_docs: OK
Full offline suite: не запускался; bounded writer change проверен указанным в registry targeted family
Runtime project IDs/artifacts: не создавались и не изменялись
Сеть/API/TTS/Vision/render/платные действия: не выполнялись
Найденные root causes:
- отдельный NewsProjectStore writer обходил существующий atomic storage primitive
- формат обоих writers уже совпадал; требовалась только безопасная делегация без schema change
Новые known issues: отсутствуют
Следующий точный этап: 5B additive news schema version, один bounded characterization-first diff
Следующая точная команда: Get-Content -Raw -Encoding UTF8 src/news/models.py
После чтения: проверить schemas/job.schema.json и tests/test_artifact_schemas.py, сначала защитить tolerant read старого job.json
Главный запрет: не объединять 5B с project lock, idempotency, migration или cleanup; не изменять persisted projects/runtime data
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
