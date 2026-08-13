---
status: historical
document_date: 2026-07-28
---

# AI-YouTube — Master Plan восстановления и передачи между AI-агентами

> **HISTORICAL CONTEXT — маршрут не задаёт.** Этот план описывает rescue-этапы
> 0–9 и объявляет checkpoint `9B-C01`, который отменён. Текущий checkpoint и
> следующее действие живут **только** во frontmatter
> [PROJECT_EXECUTION_PLAN.md](../current/PROJECT_EXECUTION_PLAN.md); то же правило
> записано в [AGENTS.md](../../AGENTS.md). Файл не архивируется до **PLAN-12C**
> и сохраняется как исторический контекст.

Статус: **выполняется; этапы 0–8, включая подэтапы 6A–6G, завершены; этап 4.5
сохранён как историческая диагностика и снят с critical path; этап 8 создал
canonical application boundaries, но не завершил передачу владения всей
реализацией; этап 9A завершён bounded slices D01–D03; после owner review цель
усилена до фактической консолидации; 9B-P01 зафиксировал два целевых application
engines на основе уже существующего кода; первый незавершённый checkpoint —
9B-C01 compatibility и canonical-ownership inventory**
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

### 2.1. Жёсткая конечная цель

План должен завершиться не только безопасной миграцией, но и контролируемой
архитектурной консолидацией:

> Для каждой поддерживаемой возможности существует одна каноническая
> production-реализация и один владелец бизнес-логики; переходные пути либо
> удалены, либо обоснованы как постоянный публичный adapter без собственной
> реализации.

Проект считается минимальным и переносимым, когда:

1. Нет одновременно старой и новой реализации одной capability.
2. Один capability может иметь несколько infrastructure adapters, но только
   одного владельца business logic.
3. Compatibility wrapper имеет запись в cleanup registry, реальных callers,
   каноническую замену и проверяемое условие удаления; бессрочный статус
   `wrapper` запрещён.
4. Test-only caller не является достаточной причиной сохранять старый public
   path после одобренного breaking change.
5. Один физический package root предоставляет установленный import
   `ai_youtube`; launcher не дублирует package implementation.
6. Planned/disabled capability не остаётся бесконечным placeholder в
   installable production tree: она получает owner decision `keep`,
   `archive` или `delete`.
7. Runtime, проекты, exports, MP4/WAV, provider cache, temp и скачанные
   материалы находятся вне Git и вне code root по умолчанию.
8. В корне остаётся только утверждённый allowlist кода, конфигурации, тестов,
   схем, tools, skills и актуальной документации.
9. Каждый production-файл имеет подтверждённого caller, является явным
   entrypoint/contract либо записан как обоснованный permanent adapter.
10. Пустые каталоги, planning placeholders, orphan modules, exact duplicates и
    generated outputs отсутствуют либо внесены в узкий документированный
    allowlist.
11. Репозиторий самодостаточен для нового AI-агента: `AGENTS.md`,
    `docs/current/` и versioned `skills/` не зависят от конкретной модели,
    внешнего диска или приватной knowledge-системы.
12. Чистый checkout работает из произвольного пути на поддерживаемой среде;
    production-код не содержит username, drive letter или обязательного
    `Path.cwd()`.

Минимализм здесь означает минимальное число владельцев, entrypoints и
источников истины, а не искусственное объединение разных domain-модулей в один
большой файл.

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

- `src/content_creation/` как существующий application service и временный
  compatibility CLI;
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
- compatibility wrappers до их callers/replacement/retirement gate;
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
Shared platform
  → projects / catalog / paths / rights
  → assets / providers
  → audio / TTS / music
  → subtitles
  → rendering / FFmpeg / export

Application engine
  content_creator
    → создаёт новые короткие и длинные видео
    → current: fullscreen_voiceover, story_card
    → future: longform/documentary workflows через templates

  video_repurposer
    → делает нарезки из существующих длинных видео
    → source types: streams, animation, films, podcasts, local/source video
    → current implementation source: Anime Factory
    → target workflow family: source_to_clips

  legacy_pipeline
    → только временная compatibility/maintenance boundary
```

Это два application engines, а не две копии платформы. Они обязаны использовать
одни и те же project, workspace, catalog, rights, asset/provider, audio/music,
subtitle, rendering и export contracts.

Фактический и целевой product surface:

| Capability | Текущее состояние | Финальное правило |
|---|---|---|
| `content_creator` | active только для двух short templates | один engine для short/long creation; новые форматы добавляются templates/workflows поверх shared services |
| `fullscreen_voiceover_v1` | active | сохранить как template/workflow текущего engine |
| `story_card_text_only_v1` | active | сохранить как template/workflow, без второй платформы |
| `video_repurposer` | catalog entry planned/disabled; рабочая основа находится в `anime_factory` | обязательный второй engine; обобщить существующую реализацию, не писать новый clip pipeline |
| Anime/stream/film/podcast clipping | реально существует только anime MVP для local MP4 | различия задавать template policies/strategies; отдельный полный engine на каждый source type запрещён |
| `legacy_pipeline` | compatibility + maintenance | сохранить только доказанно нужные maintenance/migration команды на ограниченный период; остальное retire |
| documentary/longform | format planned, реального template нет | будущий workflow/template внутри `content_creator`, а не третье приложение |
| Solar/старые documentary profiles | experimental или legacy-only | не переносить как новую платформу; reusable части определять audit-ом, остальное archive |

`video_repurposer` остаётся disabled в текущем catalog до завершения migration,
project/workspace integration и targeted evidence. Целевой статус не разрешает
представлять его пользователю как уже готовый.

### 6.1. Engine, tool, workflow и template

- **Engine/Application** владеет use cases и выбирает workflow.
- **Workflow** задаёт последовательность stages, но использует shared services.
- **Template** является versioned конфигурацией format, duration, selection,
  asset, audio, subtitle, render и quality policies; template не копирует engine.
- **Tool/CLI command** принимает задачу пользователя и выбирает application +
  template; внутри него нет второй orchestration implementation.
- **Channel/Profile** задаёт defaults/policies и может выбирать templates, но не
  является отдельным engine.
- **Project** — runtime instance с `application_id`, `workflow/template_id`,
  source, stages, artifacts и exports.

Связи не являются строгим деревом `template → channel`. Правильная модель:

```text
CLI tool
  → Application engine
    → Workflow
      → shared services

Template ──declares──> format + policies + workflow binding
Channel ──selects──> defaults + allowed templates
Project ──references──> application + workflow/template + optional channel
Project → stages → artifacts → exports
```

Новый Anime, podcast, stream или film template регистрируется только вместе с
реальным workflow binding и tests. Пустые каталоги «на будущее» не создаются.

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
  requirements.txt
  requirements.lock
  .env.example

  src/
    ai_youtube/
      cli/
        main.py
        commands/
          create.py
          repurpose.py
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
            # longform добавляется только вместе с реальной реализацией

        video_repurposer/
          service.py
          workflows/
            source_to_clips/     # ownership target существующего Anime Factory

      services/
        assets/
        audio/                   # voice, TTS orchestration и music manifest
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
  schemas/
  skills/
  scripts/

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
```

`pipeline.py`, top-level `apps/`, `anime_factory/`, root `ai_youtube/` shim и
старые owner packages являются переходными кандидатами, а не частью финального
allowlist. Каждый удаляется только собственным bounded slice после
callers/replacement gate. Это целевая структура, а не разрешение на массовое
перемещение.

---

## 8. Три логические и физически разделяемые зоны

### 8.1. Репозиторий с кодом

```text
<REPOSITORY_ROOT>
```

Содержит:

- код;
- тесты;
- схемы;
- конфигурации по умолчанию;
- ADR;
- versioned техническую документацию;
- только временно одобренные compatibility wrappers.

Фактический путь владельца `G:\Projects\AI-YouTube` является локальным
размещением, а не production contract.

### 8.2. Runtime workspace

```text
<AI_YOUTUBE_WORKSPACE>
```

Целевая структура:

```text
<AI_YOUTUBE_WORKSPACE>\
  projects\
    content_creator\
    video_repurposer\
  exports\
    content_creator\
    video_repurposer\
  artifacts\
    content_creator\
    video_repurposer\
  media_library\
    user\
    providers\
    music\
    voices\
  provider_cache\
  model_cache\
  temp\
  runtime_reports\
  user_config\
    channels\
    templates\
```

Workspace выбирается через CLI, environment или path config. Ни один drive
letter не является обязательным; `G:\AI-YouTube-Workspace` допустим только как
локальный пример. Существующие `projects/`, `outputs/`, `assets/library/`,
`manual_assets/`, `music/` и Anime `episodes/` переводятся через существующий
`WorkspacePaths` и tolerant readers; MOSS/Whisper и другие runtime model weights
относятся к `model_cache`. Второй path resolver запрещён.

### 8.3. Versioned знания и skills для AI-агентов

Канонический agent context хранится внутри репозитория:

```text
<REPOSITORY_ROOT>\
  AGENTS.md
  docs\
    current\
      START_HERE.md
      SYSTEM_MAP.md
      CURRENT_STATE.md
      ARCHITECTURE_BOUNDARY_MAP.md
      CLEANUP_REGISTRY.md
    adr\
    archive\
  skills\
    ...\
```

Внешний `AI-YouTube-System` может быть личным mirror или дополнительной
knowledge-базой, но не содержит уникальных обязательных инструкций и не
является source of truth. Клонирование репозитория должно быть достаточным для
работы Codex, Claude и другого агента, способного читать `AGENTS.md` и Markdown.

Желаемая третья физическая зона допустима в переносимом виде:

```text
<AI_YOUTUBE_SYSTEM>\
  knowledge\
  policies\
  skills\
  handoffs\
  templates\
  mirrors\project_current_docs\
```

Она хранит пользовательские/global agent resources и generated mirrors.
Project-specific architecture, ADR, current docs и versioned skills остаются в
Git. `<AI_YOUTUBE_SYSTEM>` не требуется для запуска приложения или offline
tests.

Каждая current knowledge-страница должна содержать:

- `status`;
- `last_verified_commit`;
- `last_verified_date`;
- `source_paths`;
- правило «код и Git имеют приоритет».

---

## 9. План будущих переименований

| Текущий путь | Целевой путь | Условие переноса |
|---|---|---|
| root `ai_youtube/` + `src/ai_youtube/` | один physical `src/ai_youtube/`, устанавливаемый как `ai_youtube` | После package/import/console-script characterization; implementation не копировать |
| `src/content_creation/` | `src/ai_youtube/apps/content_creator/` | После выделения public service API |
| `src/news/` | `.../workflows/fullscreen_voiceover/` | После characterization tests |
| `src/templates/story_card/` | `.../workflows/story_card/` | После workflow contract tests |
| `src/project_foundation/` + `src/projects/` | `src/ai_youtube/core/projects/` | После общего public API |
| `src/assets/` | `services/assets/` + app-specific completion | После отделения generic от workflow-specific |
| `src/providers/` | `infrastructure/providers/` | После удаления старых provider adapters |
| `src/audio/` | `services/audio/` | С сохранением approval/manifests |
| `src/subtitles/` | `services/subtitles/` | После сохранения старых imports |
| `anime_factory/` | `apps/video_repurposer/workflows/source_to_clips/` + template policies | Product scope подтверждён 9B-P01; обобщать существующий workflow, не создавать второй clip engine |
| Anime `EpisodePaths`/JSON/output layout | общий project/workspace owner с tolerant legacy episode reader | После schema/callers inventory; без массовой migration |
| Anime subtitles/FFmpeg/render helpers | существующие shared subtitles/rendering/FFmpeg owners + app-specific crop/selection | Переносить только подтверждённо generic части; domain crop/scoring остаются workflow policy |
| `src/music_engine.py`, `src/music_finder.py`, `src/music_tools.py`, `src/audio/music_manifest.py` | один shared audio/music service | После callers/rights/network audit; сохранить manifest, approval и license evidence |
| legacy documentary/Solar code | archive или reusable shared parts | Future documentary создаётся template внутри `content_creator`, legacy live-call path не переносится целиком |
| top-level `apps/*` | canonical CLI/app packages либо delete | После перевода production/docs/tests callers и завершения compatibility gate |
| `pipeline.py` + `src/legacy_pipeline/` | только подтверждённые maintenance services; затем delete/archive | Root entrypoint удалять последним |
| старые `src/*.py` | соответствующий canonical owner либо archive/delete | После import map и tests; постоянный свалочный `legacy/` не создавать |
| `docs/handoff/*` | `docs/current` или `docs/archive` | После создания короткого current state |
| runtime-папки | внешний Workspace | Copy → verify → switch |
| `MOSS_TTS_Nano`, Whisper/model weights | Workspace `model_cache/` | Только copy → verify → switch; не удалять source автоматически |
| `venv` | воспроизводимая toolchain вне чистого code root | После проверки lock/install; не переносить как source code |

### 9.1. Правило единственного владельца

Для каждого capability cleanup registry обязан показывать текущего и целевого
владельца:

| Capability | Целевой canonical owner |
|---|---|
| installed package и CLI | `src/ai_youtube/cli` как import `ai_youtube.cli` |
| создание short/long | `src/ai_youtube/apps/content_creator` |
| нарезка source video | `src/ai_youtube/apps/video_repurposer`; существующий Anime Factory является migration source |
| applications/workflows | `src/ai_youtube/apps/<application>/workflows/<workflow>`; template не владеет копией engine |
| catalog/formats/templates/export targets | существующий `ProductionCatalog`/registries, перенесённые без второго catalog |
| project read/storage primitives | один API в `src/ai_youtube/core/projects`, перенесённый из существующих owners без третьей системы |
| provider contract/registry | один contract и adapters под `src/ai_youtube/infrastructure/providers` |
| source analysis/candidate selection/reframing | существующие Anime modules, обобщённые внутри `video_repurposer`; shared boundary только при доказанном втором caller |
| assets/providers | shared service; stock/local/user/generated methods выбираются template asset policy |
| voice/TTS/music | один shared audio service; legacy music search/mix paths консолидируются, rights manifest сохраняется |
| subtitles | существующий `src/subtitles` engine; Anime relative-cue logic становится adapter/policy, не вторым engine |
| rendering/FFmpeg/export | shared execution/contracts; workflow хранит layout, crop и montage orchestration |
| configuration и paths | единственный resolver, без локальных параллельных loaders |

Точный physical move выполняется только после проверки фактических imports,
persisted contracts и public entrypoints. Таблица фиксирует направление
консолидации, но не разрешает копировать реализацию или создавать новую
абстракцию до удаления старой.

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

Статус: [x] завершён 2026-07-29; implementation commit `e3c90c3`

Задачи:

1. Использовать существующий `ProjectRepository`.
2. Не создавать третью project-систему.
3. Определить единый `ProjectView`.
4. Добавить schema version для news manifests. **Выполнено в slice 5B,
   implementation commit `42d5b99`.**
5. Перевести NewsProjectStore на общий atomic storage. **Выполнено в slice 5A,
   implementation commit `87e272a`.**
6. Добавить project lock. **Выполнено в slice 5C, implementation commit
   `f7b3a3c`.**
7. Добавить idempotency для повторных стадий. **Все repeatable downstream
   families от `research` до `export` покрыты output validation. `input` и
   потенциально сетевой `article_ingestion` намеренно исключены из
   автоматической retry-policy ADR 0006.**
8. Сохранить чтение старых `job.json` и `project.json`.
9. Не выполнять массовую миграцию.

Критерий готовности:

- один read API;
- один storage primitive;
- старые проекты читаются;
- новые записи атомарны.

Результат:

- `ProjectRepository`/`ProjectView` остаются единственным read-only API над
  `job.json` и `project.json`;
- `NewsProjectStore` пишет через общий `atomic_write_json` под общим project
  lock, не создавая новый storage/repository contract;
- news schema v1 остаётся additive, старые manifests читаются tolerant;
- normal repeat, `resume`, `force-stage`, отсутствующие, структурно непригодные
  и повреждённые outputs покрыты characterization для `research`–`export`;
- legacy asset/voice/subtitle shapes и protected user subtitles сохранены;
- массовая миграция, runtime/user-media changes, provider search, TTS и render
  не выполнялись.

---

### Этап 6. Разделение крупных модулей

Статус: [x] завершён 2026-07-29; 6A–6G завершены

Каждый подэтап ниже независим: отдельные targeted tests, commit и handoff.
Не объединять их в одну сессию без записанного исключения из бюджета области.

#### 6A. Asset manager

`src/news/asset_manager.py`: отделить orchestration от provider search,
selection, download и completion.

Статус: [x] завершён 2026-07-29; implementation commits `cba1cf7`,
`20750ab`, `59b39d3`, `fe5ba44`; characterization commit `0515e02`.

Результат:

- `asset_manager.py` уменьшен с 2119 до 266 строк и оставлен compatibility
  facade с прежними публичными сигнатурами/imports/patch-points;
- manifest summaries/coverage, scene completion/assembly, provider
  search/download adapters и manifest builder разделены по отдельным модулям;
- `build_assets_manifest()` стал коротким orchestration facade, а сценовый
  проход разделён на небольшие методы;
- существующий `src.assets.provider_contract`, manifest schemas,
  `NewsProjectStore.validate_stage_output()` и persisted projects не менялись;
- targeted verification: 181 tests OK, compile/import smoke OK; full offline
  suite, сеть, provider download, TTS, Vision и render не запускались.

#### 6B. Внутренности CLI

Разделить внутренности `src/content_creation/cli.py` и presentation-слой.
Внешний dispatcher и compatibility не менять без необходимости: это граница
этапа 4.

Статус: [x] завершён 2026-07-29; implementation commit `1f9495c`.

Результат:

- `src/content_creation/cli.py` подтверждён как тонкий compatibility facade,
  поэтому split выполнен в фактическом 727-строчном
  `src/ai_youtube/cli/commands/diagnostics.py`;
- catalog, localization/subtitles и authoring handlers вынесены в отдельные
  domain-модули, а diagnostics оставлен 78-строчным facade;
- terminal formatting вынесен в `src/ai_youtube/cli/presentation.py`;
- public command set, JSON/text output, workspace resolution и старые
  module-level patch-points сохранены; потерянный migration-ом
  `src.content_creation.cli.create_content` patch-point восстановлен через
  dependency injection;
- targeted verification: 79 tests OK, compile/import и safe capabilities smoke
  OK; full offline suite, сеть, provider download, TTS, Vision и render не
  запускались.

#### 6C. Wizard

Разделить `src/content_creation/wizard.py` на state, шаги и presentation.

Статус: [x] завершён 2026-07-29; implementation commit `b9f8212`.

Результат:

- `src/content_creation/wizard.py` уменьшен с 1229 до 175 строк и оставлен
  compatibility facade с прежним `run_wizard`, prompt adapters и private
  imports;
- working state и перевод через существующий общий request builder вынесены в
  `wizard_state.py`, terminal adapters/summaries/results — в
  `wizard_presentation.py`, шаги/resume/edit/execution orchestration — в
  `wizard_steps.py`;
- module-level `_build_request` patch-point и lazy CLI → Wizard boundary
  сохранены; application service, schemas и persisted projects не менялись;
- максимальный Wizard method — 111 строк, orchestration-функций на сотни строк
  после split нет;
- targeted verification: 124 tests OK, compile/import checks OK; full offline
  suite, сеть, provider download, TTS, Vision и render не запускались.

#### 6D. Application service

Выделить в `src/content_creation/service.py` отдельные use cases и сделать
оркестрацию явной.

Статус: [x] завершён 2026-07-29; implementation commit `8e087c7`.

Результат:

- `src/content_creation/service.py` уменьшен с 878 до 123 строк и сохранён как
  единый application service facade с прежним `create_content`;
- два active workflow вынесены в `story_card_use_case.py` и
  `fullscreen_voiceover_use_case.py`, общие progress/path helpers — в
  `service_support.py`;
- бывшая 344-строчная fullscreen orchestration разделена на явные project,
  safe-pipeline, voice/paid-gate, draft и render/export фазы; longest method —
  93 строки;
- сохранены private compatibility imports, module dispatch patch-points, paid
  preflight/approval, existing-narration protection, resume/force-stage,
  tolerant project behavior и progress callback;
- targeted verification: 97 tests OK, compile/import checks OK; full offline
  suite, сеть, provider download, TTS, Vision и render не запускались.

#### 6E. Semantic evaluation

Разделить в `src/assets/semantic_visual_evaluation.py` runtime и evaluation
tooling.

Статус: [x] завершён 2026-07-29; implementation commit `8c89a67`.

Результат:

- `src/assets/semantic_visual_evaluation.py` уменьшен с 1719 до 53 строк и
  сохранён как public facade для root `pipeline.py`;
- offline dataset loading, synthetic frames, metrics и report/comparison
  artifacts вынесены в `semantic_visual_evaluation_tooling.py`, controlled
  OpenAI execution, authorization/budget limits и checkpoints —
  в `semantic_visual_evaluation_runtime.py`;
- public signatures, dataset dataclass shapes, dry-run/mock/fake-client paths,
  root-pipeline import и paid-call gates сохранены;
- 59 из 63 прежних top-level definitions перенесены AST-идентично; longest
  function после split — 68 строк;
- targeted verification: 30 tests OK, compile/import и diff checks OK; full
  offline suite, сеть, provider calls, Vision, TTS и render не запускались.

#### 6F. Legacy pipeline

Оставить `pipeline.py` тонким фасадом dispatch и compatibility без дублирования
бизнес-логики.

Статус: [x] завершён 2026-07-29; implementation commit `0d2cd67`.

Результат:

- root `pipeline.py` уменьшен с 703 до 122 строк и оставлен compatibility
  facade для `apps.youtube_pipeline`, старых imports и module patch-points;
- public parser вынесен без изменения аргументов/defaults в
  `src/legacy_pipeline/cli.py`, maintenance/diagnostic handlers — в
  `maintenance.py`, legacy channel/video workflow — в `workflow.py`;
- `main` уменьшен с 512 до 27 строк и выполняет только workspace/path
  initialization и делегацию; самая длинная orchestration-функция
  split-модулей — 77 строк;
- compatibility namespace передаёт root patch-points фактическим handlers без
  дублирования business logic; command/output contract, safe paid-call gates и
  synthetic `--skip-render` workflow сохранены;
- targeted verification: 54 tests OK, compile/import и diff checks OK; full
  offline suite, сеть, provider calls/download, Vision, TTS и render не
  запускались.

#### 6G. Оставшиеся import cycles

Устранить cycle frame sampling ↔ perceptual similarity и другие обнаруженные
циклы отдельными малыми изменениями.

Статус: [x] завершён 2026-07-29; implementation commit `802a54c`.

Результат:

- characterization-first зафиксировал прежние public imports
  `SampledFrame`, `sha256_file`, `image_perceptual_hash`, package export
  `src.assets.SampledFrame` и image sampling/signature behavior;
- `SampledFrame`, file SHA-256 и perceptual image hash вынесены в минимальный
  `src/assets/frame_primitives.py`;
- `frame_sampling.py` и `perceptual_similarity.py` больше не импортируют друг
  друга и зависят только от shared primitive; старые public import paths
  сохранены;
- targeted verification: 48 tests OK для import-boundary, visual-preview
  foundation/integration и temporal analysis; compile/diff checks OK; full
  offline suite, сеть, provider calls/download, Vision, TTS и render не
  запускались.

Критерий готовности:

- нет orchestration-функций на сотни строк;
- нет статических import-cycle;
- поведение каждого подэтапа подтверждено его targeted tests;
- нет статических import-cycle после 6G.

---

### Этап 7. Консолидация providers

Статус: [x] завершён 2026-07-29; implementation commit `fb93a05`

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

Результат:

- `src.assets.provider_contract.StockProvider` подтверждён единственным
  canonical provider contract; второй provider contract не создавался;
- default automatic provider set и environment-enabled policy перенесены в
  `src.providers.registry`, а news factory сохранён compatibility wrapper;
- активный Fullscreen Voiceover asset path получает только canonical
  implementations из `src.providers`;
- timeout/retry/rate-limit translation, diagnostics, download validation и
  license normalization остаются у существующих общих `src.assets`
  components;
- standalone `stock_video_downloader` сокращён до 35-строчного compatibility
  wrapper без raw HTTP; недостижимая private legacy реализация удалена;
- D01 legacy provider names и D02 public wrapper сохранены до отдельного
  retirement этапа 9, поскольку characterization подтверждает compatibility
  surface; преждевременного удаления entrypoints не выполнялось;
- legacy documentary/fixed-production-plan HTTP paths оставлены в границе
  вертикальных переносов этапа 8, без смешивания с provider stage;
- targeted verification: 55 provider/asset tests и 23 pipeline/CLI tests OK,
  compile/import smoke и docs QA OK; сеть, provider search/download и full
  offline suite не запускались.

---

### Этап 8. Миграция приложений вертикальными срезами

Статус: [x] завершён 2026-07-29; vertical slices `fullscreen_voiceover`,
`story_card`, `anime_clipper` и legacy pipeline перенесены, documentary gate
8E закрыт без migration; последние implementation/gate commits `06e6a25`,
`01cfc6f`, `7d0ce1e`, `cfe6ae6`, `a3536a9`

Точное значение статуса: этап 8 создал canonical application boundaries и
перевёл на них непосредственных application callers. Он не утверждает, что
`src.news`, `src.templates.story_card`, `anime_factory`, `pipeline.py` и
`src.legacy_pipeline` уже перестали владеть реализацией. Передача оставшегося
ownership, превращение старых путей в wrappers и их удаление относятся к
этапам 9B–9E.

Порядок:

1. [x] `fullscreen_voiceover`;
2. [x] `story_card`;
3. [x] `anime_clipper` через `video_repurposer` adapter;
4. [x] legacy pipeline;
5. [x] documentary — gate проверен; реального рабочего шаблона нет, migration
   не выполнялась.

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

Результат первого vertical slice:

- canonical application boundary создан в
  `src.ai_youtube.apps.content_creator.workflows.fullscreen_voiceover`;
- application-level use case физически перенесён в новый boundary без
  изменения orchestration behavior;
- существующие `NewsJob`, `NewsProject`, `NewsProjectStore`,
  `NewsPipelineResult` и create/run workflow functions переэкспортируются из
  `src.news`, который остаётся их единственным владельцем; второй project
  contract, writer или pipeline не создавался;
- `src.content_creation.service` использует canonical use case;
  `src.content_creation.fullscreen_voiceover_use_case` и
  `apps.news_to_short` остаются совместимыми wrappers;
- migration note зафиксирован ADR 0009; schemas, manifests, runtime projects и
  user media не менялись;
- targeted verification: pre-change characterization 3 tests OK; boundary,
  service internals и apps 11 tests OK; service/news pipeline/project
  repository 49 tests OK; compile/import/diff/docs QA OK;
- full offline suite, сеть, provider search/download, TTS, Vision, render и
  платные действия не запускались.

Результат второго vertical slice:

- canonical application boundary создан в
  `src.ai_youtube.apps.content_creator.workflows.story_card`;
- application-level use case физически перенесён в новый boundary без
  изменения orchestration behavior;
- существующие `ProjectFactory`, `ProjectCreationResult`, `ProjectManifest`,
  `EvidenceBundle`, `EvidenceRecord` и Story Card integration contracts
  переэкспортируются из их прежних owner modules; второй project writer,
  schema, evidence bundle или renderer не создавался;
- `src.content_creation.service` использует canonical use case;
  `src.content_creation.story_card_use_case` остаётся compatibility wrapper;
- migration note зафиксирован ADR 0010; schemas, manifests, runtime projects и
  user media не менялись;
- targeted verification: pre-change characterization 3 tests OK; boundary и
  service internals 9 tests OK; Story Card service/project/evidence/schema
  radius 75 tests OK; compile/import/content-comparison/diff/docs QA OK;
- full offline suite, сеть, provider search/download, TTS, Vision, render и
  платные действия не запускались.

Результат третьего vertical slice:

- canonical lazy adapter boundary создан в
  `src.ai_youtube.apps.video_repurposer.workflows.anime_clipper`;
- существующие `parse_args`, `run_pipeline`, `main`, `EpisodePaths`,
  `PROJECT_ROOT` и `get_episode_paths` переэкспортируются из `anime_factory`,
  который остаётся единственным владельцем workflow и project/output layout;
- `apps.anime_factory` использует canonical boundary, а прямой
  `anime_factory.pipeline` CLI и прежние imports остаются совместимыми;
- catalog `video_repurposer` намеренно остаётся planned/disabled и не
  представляется готовым приложением;
- migration note зафиксирован ADR 0011; runtime episodes, schemas, manifests и
  user media не менялись;
- targeted verification: pre-change characterization 4 tests OK;
  boundary/CLI/catalog/apps 9 tests OK; Anime Factory path/cleanup/candidate/
  crop/transcript/selection radius 13 tests OK; compile/import/diff/docs QA OK;
- full offline suite, FFmpeg, render, transcription model, сеть и платные
  действия не запускались.

Результат четвёртого vertical slice:

- canonical lazy adapter boundary создан в
  `src.ai_youtube.apps.legacy_pipeline.adapter`;
- существующие root `main`, `parse_args`, `run_maintenance_command`,
  `run_legacy_video_pipeline`, `limit_scene_plan` и
  `LegacyPipelineArtifacts` переэкспортируются без создания второго
  dispatcher, workflow, engine или project/artifact contract;
- `apps.youtube_pipeline` использует canonical boundary, а root `pipeline.py`
  остаётся владельцем compatibility namespace и engine patch-points;
- `src.legacy_pipeline` остаётся единственным владельцем parser, maintenance и
  legacy channel/video workflow behavior;
- migration note зафиксирован ADR 0012; outputs, schemas, manifests, runtime
  projects и user media не менялись;
- targeted verification: pre-change characterization 4 tests OK;
  boundary/internals/Stage 1/apps 10 tests OK; workspace/catalog/semantic
  radius 23 tests OK; compile/import/diff/docs QA OK;
- full offline suite, сеть, provider calls/download, TTS, Vision, render и
  платные действия не запускались.

Результат documentary gate 8E:

- production catalog не содержит `documentary` application/template;
  `longform` остаётся planned/disabled и без зарегистрированного шаблона;
- legacy profiles `psychology`, `quotes`, `survival` и `size_comparison`
  доступны только через root `pipeline.py --channel/--video` и намеренно не
  поддерживаются `content_creator`;
- Solar fixed production plan пишет отдельные `project_config.json` и
  `scenes.json`, которые не являются `job.json`/`project.json` и определяются
  `ProjectRepository` как unknown;
- Solar render path напрямую загружает `.env`, вызывает ElevenLabs,
  Pexels/Pixabay и HTTP download без application-level paid/provider gate;
- characterization зафиксировал catalog/channel/project/root-owner/live-call
  stop-gates; ADR 0013 запрещает создавать ложный documentary boundary или
  включать capability по наличию legacy кода;
- production code, schemas, runtime projects, user media и capability registry
  не менялись; сеть, provider calls/download, TTS, Vision и render не
  запускались;
- targeted verification: 56 tests OK для documentary gate, catalog/capability,
  Stage 4 CLI, fixed plan, legacy boundary и `ProjectRepository`; docs QA и
  diff checks OK;
- этап 8 закрыт с четырьмя фактически перенесёнными vertical slices.

---

### Этап 9. Canonical ownership, retirement и доказанное удаление

Статус: [ ] выполняется; 9A завершён 2026-07-29 отдельными D01–D03 commits;
9B-P01 product boundary завершён; 9B-C01 и этапы 9C–9E не начаты

#### 9A. Удаление доказанного dead code

Статус: [x] завершён 2026-07-29

Задачи 9A:

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

Результат D01:

- pre-change characterization и повторный repo-wide audit подтвердили
  отсутствие production callers/package exports для
  `PexelsAssetProvider`, `PixabayAssetProvider`, `UnsplashAssetProvider`;
- временные classes, raw provider-module imports и `asset_manager` re-exports
  удалены после compatibility period stages 7–8;
- news `AssetProvider`, factory patch-point и canonical
  `PexelsStockProvider`/`PixabayStockProvider` сохранены;
- schemas, manifests, provider ids/provenance, runtime projects и media не
  менялись;
- targeted verification: 41 provider/news asset test, import/compile smoke и
  docs QA OK; сеть/provider search/download/TTS/Vision/render не запускались;
- решение public compatibility boundary зафиксировано ADR 0014.

Результат D02:

- pre-change AST characterization и повторный repo-wide audit подтвердили
  отсутствие production imports/calls, package export, CLI/console script и
  current command для `src.news.stock_video_downloader`;
- единственный executable caller был временным characterization test;
- standalone wrapper удалён, два production docstring больше не называют его
  visual-plan consumer;
- canonical `src.news.asset_manager.build_news_asset_manifest` и active
  `asset_search` stage сохранены; новый wrapper/CLI не создавался;
- schemas, manifests, downloaded media, runtime projects и user data не
  менялись;
- targeted verification: 46 news asset/pipeline/compatibility tests,
  import/compile smoke и docs QA OK; сеть/provider search/download/TTS/Vision/
  render не запускались;
- решение public compatibility boundary зафиксировано ADR 0015.

Результат D03:

- read-only inventory подтвердил, что `packages/` содержал только один tracked
  planning README; hidden/untracked files, runtime/current callers и package
  discovery dependency отсутствовали;
- pre-delete characterization зафиксировал package discovery только из
  `ai_youtube*`, `src*`, `anime_factory*`, `apps*`;
- `packages/README.md` и пустая physical directory удалены; historical
  plans/audits сохранены как snapshots;
- устаревшие Stage 2 date/length assertions актуализированы без снятия
  onboarding size gate: `START_HERE` остаётся не длиннее 100 строк;
- targeted verification: 8 onboarding/reproducibility tests, package-discovery
  smoke и docs QA OK;
- production code/config, schemas, runtime projects и user data не менялись;
  сеть/provider/TTS/Vision/render не запускались.

Подэтап 9A закрыт: каждый delete path D01–D03 имеет актуальное zero-caller/
replacement evidence, отдельный commit и ограниченный rollback. Закрытие 9A не
означает завершение ownership transfer или retirement всех wrappers.

#### 9B. Product surface, compatibility и ownership inventory

Статус: [ ] выполняется; P01 product/application boundary decision завершён,
следующий checkpoint C01 — read-only caller/ownership inventory

Это первый незавершённый этап. Он read-only относительно production code,
runtime и пользовательских данных.

Задачи:

1. Подтвердить обязательный product surface:
   - `content_creator` сохраняется как engine для short/long creation;
   - `video_repurposer` сохраняется как второй engine, а Anime Factory является
     существующим migration source;
   - documentary/longform развивается как workflow/template
     `content_creator`, а не третье приложение;
   - для каждой legacy/maintenance команды определить `keep temporarily`,
     `replace`, `archive` или `delete`;
   - planned target не считать уже активным tool.
2. Расширить существующий `docs/current/CLEANUP_REGISTRY.md`, не создавать
   второй compatibility registry.
3. Для каждого старого path и wrapper записать:
   - current owner и target canonical owner;
   - production, tests, docs и external/console callers;
   - persisted/runtime dependency;
   - public compatibility promise;
   - replacement;
   - итоговый class;
   - точное exit condition.
4. Обязательно проверить семейства:
   - root `ai_youtube/` и `src/ai_youtube/`;
   - `src.content_creation.cli` и use-case wrappers;
   - `apps/*`;
   - `src.news` и Fullscreen canonical boundary;
   - `src.templates.story_card` и Story Card boundary;
   - `anime_factory` и Anime Clipper adapter;
   - Anime `EpisodePaths`, transcription, subtitles, FFmpeg/crop/render helpers;
   - `src.audio.music_manifest` и legacy music engine/finder/tools;
   - `pipeline.py`, `src.legacy_pipeline` и legacy adapter;
   - semantic evaluation facade, project layers и другие re-export paths.
5. Построить exact-duplicate hash report для tracked production files,
   запретить вывод о duplicate business logic только по совпадению basename.
6. Выбрать первый bounded 9C slice; ничего не переносить и не удалять.

Критерий готовности:

- каждый compatibility path и old owner имеет строку registry;
- у каждой поддерживаемой capability указан один target owner;
- test-only caller явно отделён от внешнего/public caller;
- зафиксирован owner decision для disabled/planned tools;
- выбран один переход с минимальным dependency radius и targeted tests.

Результат P01:

- owner подтвердил два целевых application engines:
  `content_creator` и `video_repurposer`;
- фактический audit подтвердил, что новые engines создавать не нужно:
  `ProductionCatalog`, `ProjectRepository`, `WorkspacePaths`, providers/assets,
  audio/TTS/music, subtitles/renderers и Anime Factory уже существуют;
- `video_repurposer` остаётся disabled до migration/evidence, но больше не
  является кандидатом на archive;
- future documentary/longform закреплён за `content_creator`;
- domain source types Anime/stream/film/podcast должны различаться templates и
  policies, а не полными копиями pipeline;
- решение target boundary зафиксировано ADR 0016; production/runtime behavior
  не менялось.

#### 9C. Перевод callers на canonical imports и entrypoints

Статус: [ ] не начат

Задачи:

1. Переводить одно семейство callers за bounded slice: production, затем
   current docs/examples, затем tests.
2. Не сохранять старый path только потому, что characterization test импортирует
   его; после одобренного retirement тест переносится или удаляется вместе с
   contract.
3. Сохранять wrapper до zero-production-caller gate и завершения явно
   записанного compatibility period.
4. Не менять persisted schemas, project formats, paid gates или runtime layout
   в import-migration slice.
5. Каждый public breaking decision фиксировать ADR и migration note.

Критерий готовности:

- normal production flow использует только canonical imports;
- старые paths не владеют orchestration и не используются внутренним кодом;
- оставшиеся callers и exit condition актуальны в cleanup registry.

#### 9D. Передача владения реализацией canonical packages

Статус: [ ] не начат

Задачи:

1. Переносить реализацию, а не копировать её: после каждого slice business logic
   существует только у одного owner.
2. Старый path после переноса может быть только тонким re-export/delegation
   wrapper без собственной policy, storage, HTTP, render или orchestration.
3. Выполнять по одному workflow/subsystem boundary:
   Fullscreen, Story Card, Anime Clipper, legacy maintenance, project,
   assets/providers, audio, subtitles и rendering не объединять в один diff.
4. Сохранять tolerant readers, manifests, resume/force-stage, approval gates и
   пользовательские paths.
5. Не создавать временный второй engine, repository, resolver или contract.

Критерий готовности:

- canonical package содержит настоящую реализацию;
- старый package либо тонкий wrapper, либо уже удалён;
- source comparison/callers audit не показывает две production-реализации;
- targeted contract и ближайший integration smoke проходят.

#### 9E. Удаление старых implementations, wrappers и duplicate package roots

Статус: [ ] не начат

Задачи:

1. Удалять один wrapper/package family за commit после 9C/9D, zero-caller gate
   и проверки console/import entrypoints.
2. Свести root `ai_youtube/` и `src/ai_youtube/` к одному physical package root,
   установленному как `ai_youtube`.
3. Удалить ненужные `apps/*`, old use-case paths и exact duplicate entry stubs
   вместе с их parent compatibility surface, а не создавать helper ради
   нескольких строк boilerplate.
4. `pipeline.py` удалять последним, после переноса подтверждённых maintenance
   команд и отдельного решения по legacy profiles.
5. Исторически ценный код архивировать вне active/installable package tree;
   runtime и user data не удалять.

Критерий готовности этапа 9:

- одна production-реализация и один owner на capability;
- один installed/public package root и один canonical CLI;
- registry не содержит бессрочного `wrapper` или `keep always` без public
  evidence и owner decision;
- старые internal imports и test-only compatibility удалены;
- disabled/planned code имеет финальный `keep`, `archive` или `delete`;
- каждый retirement имеет отдельный commit, targeted tests и rollback.

---

### Этап 10. Repository/runtime cleanup и разделение рабочих зон

Статус: [ ] не начат

Каждый подэтап выполняется отдельным audit/diff/commit. Compatibility inventory,
caller migration и duplicate package ownership относятся к этапу 9 и не
смешиваются с этапом 10.

#### 10A. Historical docs inventory и archive

- перечислить historical audits/plans вне `docs/current`;
- проверить current links и archive destination;
- перемещать только отдельным commit после read-only inventory;
- не переписывать historical snapshots ради актуальности.

#### 10B. Generated outputs и Git tracking

- классифицировать tracked outputs/reports как source, evidence или generated;
- сохранять невоспроизводимые evidence и user artifacts;
- untrack только подтверждённо generated content после backup/reference gate;
- обновить `.gitignore` тем же bounded slice.

#### 10C. Cache, temp, empty directories и placeholders

- удалять только воспроизводимые `__pycache__`, `*.pyc`, temp и пустые runtime
  directories после проверки абсолютного target;
- отдельно классифицировать пустые source/evidence directories и нулевые
  package markers;
- пустой `__init__.py` не считать мусором автоматически.

#### 10D. Runtime/toolchain dry-run inventory

- посчитать проекты, artifacts, media, manifests, checksums и toolchain roots;
- ничего не копировать, не перемещать и не удалять;
- определить target workspace из config, а не hardcoded drive.

#### 10E. Runtime workspace copy, verify и switch

- использовать только `copy → verify counts/manifests/checksums → switch`;
- сохранить dual-read legacy roots;
- направить новые записи во внешний workspace отдельным contract slice;
- старые данные оставить до отдельного подтверждения владельца.

#### 10F. Root directory minimization

- утвердить root allowlist из раздела 7;
- versioned source/config, user data и generated/runtime классифицировать
  раздельно;
- не удалять `projects`, media, evidence, license proof или source content;
- каждый top-level retirement выполнять отдельным commit.

#### 10G. Report-only repository minimalism QA

Добавить `tools/qa/check_repository_minimalism.py`, который ничего не удаляет и
формирует проверяемый отчёт о:

- tracked cache/temp/generated outputs;
- runtime roots внутри Git;
- пустых каталогах и planning placeholders;
- top-level paths вне allowlist;
- exact duplicate production files с узким allowlist;
- wrappers без строки cleanup registry;
- запрещённых old imports после их retirement;
- hardcoded machine paths и broken current-doc links.

Orphan-module и caller результаты являются кандидатами для ручного review, а не
автоматическим доказательством безопасного удаления.

Критерий готовности:

- корень соответствует утверждённому allowlist;
- generated/runtime данные не загрязняют Git;
- старые проекты продолжают читаться;
- внешний workspace проверен без удаления исходных данных;
- default runtime не зависит от repo root или фиксированного drive;
- minimalism QA выполняется в report-only режиме и имеет документированный
  allowlist;
- каждый cleanup diff воспроизводим и не затрагивает пользовательские media.

---

### Этап 11. Финальная инженерная проверка

Статус: [ ] не начат

Проект считается восстановленным, когда:

- существует один установленный package/import root `ai_youtube`, физически
  принадлежащий `src/ai_youtube`;
- существует один канонический CLI; noncanonical entrypoints удалены либо имеют
  ADR, реального внешнего caller и статус permanent adapter без business logic;
- `content_creator` и `video_repurposer` являются двумя canonical application
  engines; documentary/longform и source-specific variants не создают третьи
  engine stacks;
- catalog регистрирует только templates с реальным workflow binding/tests и
  честным active/planned status;
- каждая поддерживаемая capability имеет одного canonical owner;
- существует один ProjectRepository;
- существует один storage primitive и явно разделённые tolerant manifest owners,
  а не параллельные storage systems;
- существует один path/config resolver;
- существует один provider contract;
- существует по одному asset, voice/TTS, subtitle и rendering engine contract;
- оба application engines используют эти shared contracts, а app-specific
  scoring/crop/layout остаётся bounded workflow policy;
- runtime по умолчанию находится вне Git и code root;
- новые projects/exports/artifacts разделены по application, а user/provider/
  music/voice media разрешаются через один workspace resolver;
- нет production hardcode конкретного компьютера;
- CI выполняет offline suite;
- нет import-cycle;
- крупные orchestration-модули разделены по подтверждённым границам;
- cleanup registry закрыт: остаются только реализованные решения,
  обоснованные permanent owners и `do_not_touch` user-data записи;
- отсутствуют доказанные dead imports, duplicate implementations, test-only
  compatibility и wrappers без exit condition;
- нет active package placeholders для planned/disabled tools;
- root соответствует allowlist, нет бесхозных empty directories и generated
  artifacts;
- report-only minimalism QA и полный offline suite проходят;
- платные вызовы требуют явного approval;
- новый агент любой модели получает актуальный self-contained контекст из
  `AGENTS.md` и нескольких коротких current docs;
- clone не зависит от `G:\...`, конкретного username или внешней обязательной
  knowledge-базы;
- persisted projects, manifests и пользовательские media сохранены;
- финальная проверка архитектуры не требует создания, рендера или визуальной
  оценки нового видео.

---

## 13. Что делать первым

Первое действие при возобновлении плана:

> Продолжить 9B-C01 read-only inventory: перечислить public entrypoints,
> package roots, wrappers, current implementation owners и
> production/test/docs callers. Отдельно картировать existing Anime
> project/path/transcription/subtitle/render modules и legacy/shared music
> paths. Обновить только существующий `CLEANUP_REGISTRY.md`; ничего не
> переносить и не удалять.

Не начинать с:

- перемещения папок;
- удаления code path без callers/replacement evidence;
- удаления проектов;
- создания нового репозитория с переписанным кодом;
- массового форматирования;
- добавления новых providers;
- архивирования или удаления disabled tool без owner decision;
- создания второго compatibility registry;
- физической миграции runtime или удаления user data;
- создания или рендера reference video;
- UI;
- RAG или vector database;
- swarm/subagents;
- физической миграции runtime.

---

## 14. Текущий handoff

Этот раздел обновляется после каждого выполненного этапа.

```text
Последнее обновление: 2026-07-29
Завершённый bounded slice: 9B-P01 two-engine product/application boundary
Текущий этап: 9B выполняется; product surface подтверждён, caller/ownership inventory не завершён
Следующий этап: 9B-C01 read-only compatibility/caller/ownership inventory
Исходный HEAD P01: 9f3ddba
Commit D01: 1683b24
Commit D02: dcd6a3c
Commit D03/закрытие 9A: 75a2715
Commit пересмотра cleanup plan: 9f3ddba
Commit P01: текущий commit
Ветка: master
Git до работы: clean, HEAD 9f3ddba
Выполнено:
- owner product goal сопоставлен с ProductionCatalog, content_creator, Anime Factory, WorkspacePaths, ProjectRepository и shared services
- подтверждены два target engines: content_creator для short/long creation и video_repurposer для source-to-clips
- video_repurposer закреплён как migration existing Anime Factory, а не новый pipeline; catalog остаётся disabled до evidence
- documentary/longform закреплён как future workflow/template content_creator, а не третье приложение
- Anime/stream/film/podcast различаются templates/policies/strategies поверх одного workflow
- workspace target дополнен app-scoped projects/exports/artifacts и shared media library для user/providers/music/voices
- external AI-YouTube-System разрешён как optional physical agent zone, но не source of truth
- cleanup registry расширен кандидатами music, Anime subtitles/render/paths/transcription
Изменения production code: отсутствуют
Characterization tests: не добавлялись; изменение только план/metadata
Targeted test maintenance: не требовалась
ADR: docs/adr/0016-two-engine-product-architecture.md
Schemas/Manifests: не изменялись
Runtime projects/user media: не затрагивались
Сеть/API/TTS/Vision/provider search/download/платные действия: не выполнялись
Targeted checks:
- .\venv\Scripts\python.exe -m tools.qa.check_agent_docs: OK
- .\venv\Scripts\python.exe -m unittest tests.test_stage2_agent_onboarding: OK, 3 tests
Full offline suite: не требуется; production/runtime contracts не менялись
Найденные root causes:
- оба желаемых engines уже частично существуют; новый implementation создал бы дублирование
- Anime Factory содержит полный MVP source-to-clips, но использует собственные paths, subtitle formatter и FFmpeg/render helpers
- modern music manifest/rights path сосуществует с legacy music search/download/mix modules
- строгая цепочка Application→Workflow→Format→Template→Channel была неверна: channel и template независимо выбираются project policy
Новый known issue:
- точные callers/ownership для registry C01–C16 ещё не собраны
- video_repurposer project schema/workspace integration и enable evidence отсутствуют
- stage 10 A01/A02/D04 и runtime inventory ещё не начаты и теперь следуют после этапа 9
Что нельзя повторять:
- не создавать новый clip engine вместо переноса Anime Factory
- не создавать отдельные engines для Anime/stream/film/podcast или documentary
- не переносить Anime generic-looking helper в shared service без доказанного второго caller
- не смешивать C01 inventory с move, enable capability или runtime migration
Следующая точная read-only команда: git status --short --branch
После проверки Git выполнить: C01 inventory package roots/wrappers, Anime modules, music paths и production/test/docs callers
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
