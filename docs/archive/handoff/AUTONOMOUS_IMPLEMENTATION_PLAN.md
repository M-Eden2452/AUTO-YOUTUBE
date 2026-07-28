# Autonomous Implementation Plan

Основано на `docs/handoff/AUTONOMOUS_ARCHITECTURE_AUDIT.md` (2026-07-25).

Принципы: reuse before rewrite · adapter before migration · compatibility before cleanup ·
truthful capability status · one source of truth per responsibility · маленькие этапы с
targeted-тестами.

Все команды — только через `./venv/Scripts/python.exe`.

---

## Первые пять задач

### Задача 1 — Stage A: честные статусы и source of truth

- **Task class:** medium
- **Ожидаемый результат:** пользователь больше не видит опций, которые не работают; каталог
  и документация перестают противоречить коду.
- **Почему следующая:** ложные возможности вводят в заблуждение и делают любой дальнейший
  вывод о готовности недостоверным. Изменения не трогают рендер и не могут испортить данные.
- **Переиспользуемые компоненты:** `production_catalog.catalog`, `content_creation.capabilities`,
  `content_creation.cli`, `project_foundation.channels`.
- **Предполагаемые файлы:** `src/production_catalog/catalog.py`,
  `src/content_creation/capabilities.py`, `src/content_creation/wizard.py`,
  `src/content_creation/cli.py`, `CLAUDE.md`, `COMMANDS.md`,
  `docs/handoff/{START_HERE,CURRENT_STATE,NEXT_PLAN}.md`, новый
  `tests/test_capability_consistency.py`.
- **Запрещённые новые дубли:** новая capability-система, новый channel-registry, новый каталог.
- **Acceptance criteria:**
  1. `capabilities.list_channels()` помечает каждый канал полем совместимости и не выдаёт
     legacy-каналы как готовые для `content_creator`.
  2. Формат без единого `enabled`-шаблона не предлагается в wizard.
  3. `workflow_binding` story_card указывает на его настоящий workflow.
  4. `render_preset_id`, указывающий на несуществующий файл, устранён или помечен.
  5. Новый тест падает, если capability-статус разойдётся с runtime.
  6. Все существующие targeted-тесты по-прежнему проходят.

### Задача 2 — Stage B1: narration-aligned scene timing

- **Task class:** architecture (маленькая, но контрактная)
- **Ожидаемый результат:** видеоряд и субтитры совпадают с реальной озвучкой; больше нет
  ситуации «визуал 51.5 s против аудио 59.5 s».
- **Почему следующая:** самое сильное улучшение реального качества продукта при минимальном
  риске; всё нужное уже лежит в `voice_manifest.json`.
- **Переиспользуемые компоненты:** `voice_manifest` (schema v2), `pause_policy`,
  `end_tail_policy`, `news/final_renderer`, `news/subtitles`.
- **Предполагаемые файлы:** новый `src/audio/scene_timeline.py`, `src/news/pipeline.py`
  (стадия voice), `src/news/final_renderer.py`, новый
  `tests/test_scene_timeline.py`, дополнения в `tests/test_news_to_short_renderer.py`.
- **Запрещённые новые дубли:** новый audio engine, новый renderer, новая модель сценария.
- **Acceptance criteria:**
  1. После успешной стадии `voice` в `script.json` появляются `actual_duration_sec` и
     пересчитанные `start_sec` для каждой сцены.
  2. `final_renderer._create_scene_segments` использует `actual_duration_sec`, если он есть.
  3. Сумма длительностей сцен + tail совпадает с длительностью narration в пределах 0.05 s.
  4. Если озвучки нет, поведение остаётся ровно прежним (плановые длительности).
  5. Манифесты старого формата читаются без ошибок.

### Задача 3 — Stage B2: voice profile resolution и мёртвые вопросы wizard

- **Task class:** small
- **Ожидаемый результат:** выбранный голос не теряется; wizard не задаёт вопросов, которые
  ничего не меняют.
- **Переиспользуемые компоненты:** `voice_adapter.load_voice_profile_for_channel`,
  `VoiceProfileRegistry`.
- **Предполагаемые файлы:** `src/content_creation/capabilities.py`,
  `src/content_creation/wizard.py`, `src/news/pipeline.py` (проброс override в CLI),
  `tests/test_content_creation_wizard.py`, `tests/test_news_voice_adapter.py`.
- **Запрещённые новые дубли:** второй voice registry, второй resolver.
- **Acceptance criteria:**
  1. `capabilities.resolve_voice_profile` резолвит `ru_dom` для канала без своего
     `voices.yaml` тем же правилом, что и `voice_adapter`.
  2. Wizard не очищает профиль и не печатает ложное предупреждение для такого канала.
  3. Вопросы «Режим озвучки» и «Режим тайминга» удалены или подчинены template policy.
  4. `pipeline.py --news-to-short` умеет передать `--voice-profile` в стадию voice.

### Задача 4 — Stage C1: read-only project adapter

- **Task class:** architecture
- **Ожидаемый результат:** одна команда показывает статус любого проекта, независимо от того,
  какая система его создала; появляется фундамент для UI.
- **Переиспользуемые компоненты:** `NewsProjectStore`, `ProjectFactory`, `EvidenceBundle`.
- **Предполагаемые файлы:** новый `src/projects/repository.py` (+ `__init__.py`),
  `src/content_creation/cli.py`, новый `tests/test_project_repository.py`.
- **Запрещённые новые дубли:** **третья project-система**, запись в проекты, миграция папок.
- **Acceptance criteria:**
  1. `cli project status --project-id <любой>` работает и для `job.json`, и для `project.json`.
  2. Отсутствующий проект даёт понятное сообщение, а не traceback.
  3. Появляется `cli project list` с типом, каналом, шаблоном, статусом и путём к результату.
  4. Ни один файл в `projects/` не изменяется (тесты — только в tempfile).

### Задача 5 — Stage A2: архивация дублирующей документации

- **Task class:** small
- **Ожидаемый результат:** один canonical набор документов вместо десятка корневых аудитов.
- **Предполагаемые файлы:** перемещение корневых `PROJECT_AUDIT_*.md` и
  `IMPLEMENTATION_PROVIDER_FOUNDATION_*` в `docs/archive/` (перемещение, не удаление).
- **Acceptance criteria:** ни один файл не удалён; ссылки в `CLAUDE.md`/`COMMANDS.md`
  обновлены; `git status` показывает только перемещения.

---

## Один следующий этап

**Stage B1 — narration-aligned scene timing.**

Причины выбора: безопасно (ни сети, ни платных вызовов, ни записи в пользовательские проекты),
ограниченно (3–4 файла), неразрушительно (только additive-поля с fallback), напрямую полезно
пользователю (устраняет рассинхрон в готовом видео), опирается на существующий код
(`voice_manifest` v2 + `pause_policy` + `end_tail_policy`), имеет чёткие targeted-тесты.

Фактическое исполнение: Stage A выполняется первым как подготовка (документация и честные
статусы), затем сразу Stage B1.

---

## Полный roadmap

| Stage | Цель | Размер | Зависит от | Меняет | Не трогать | Acceptance | Rollback |
|---|---|---|---|---|---|---|---|
| A | Честные статусы, canonical entrypoints, актуальная документация | medium | — | catalog, capabilities, wizard, docs | рендер, project-данные | новый consistency-тест | git-diff обратим, изменения аддитивные |
| B1 | Narration-aligned scene timing | medium | A | scene_timeline, pipeline voice stage, final_renderer | voice generation, approval | сумма сцен ≈ narration | удалить вызов записи timing |
| B2 | Voice profile resolution + мёртвые вопросы wizard | small | A | capabilities, wizard, news CLI | registry, approval | профиль сохраняется | обратимо |
| B3 | Осмысленные имена проектов + resume из wizard | small | B2 | news models, wizard | существующие проекты | новый проект получает читаемый id | обратимо |
| C1 | Read-only ProjectRepository | medium | B | новый `src/projects/` + cli | обе project-системы | `project status/list` для обоих типов | удалить модуль |
| C2 | Единый rights-report над обеими формами evidence | small | C1 | repository, cli | evidence-файлы | отчёт по news-проекту | обратимо |
| D1 | Config resolver global→template→channel→project→localization | medium | C | новый resolver + читатели | channel-файлы | приоритет покрыт тестами | обратимо |
| D2 | Локализационный voice override (`languages.<lang>.voice`) | small | D1 | voice_adapter | approval | override читается | обратимо |
| E1 | Music manifest writer + wizard-опция музыки | small | D | новая стадия music, capabilities | `_mux_voice_and_music` | музыка слышна в MP4 | отключить стадию |
| E2 | Subtitle style из `channels/*/subtitle_style.json` | small | E1 | subtitles | тайминг из B1 | стиль применяется | обратимо |
| F1 | Первый настоящий longform-шаблон | architecture | C, D | catalog, service, renderer | shorts-путь | одно реальное 16:9 видео end-to-end | шаблон `enabled=False` |
| G1 | Anime Factory → `video_repurposer` через adapter | architecture | C | новый adapter, catalog | `anime_factory/` внутренности и тесты | существующие тесты зелёные | удалить adapter |
| H | Cleanup по категориям §12 аудита | small×N | всё выше | архивные перемещения | пользовательские данные | `git status` только перемещения | git |

---

## Стоп-условия

Работа останавливается с записью blocker'а в `AUTONOMOUS_PROGRESS.md`, если требуется:
платный/live API, новый секрет, удаление пользовательских данных, массовое перемещение
файлов, необратимая миграция, schema change без compatibility reader, изменение более
нескольких десятков файлов за этап, удаление/переименование основного entrypoint, новая
внешняя зависимость, выбор между двумя разными продуктовыми направлениями.
