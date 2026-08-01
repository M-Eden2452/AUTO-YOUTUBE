---
status: audit
audit_date: 2026-07-31
audit_head: adcbb19
working_branch: governance-reset
author: independent read-only review
scope: whole repository (source, tests, agent infrastructure, docs, execution plan)
---

# Independent Repository Review — 2026-07-31

Read-only аудит. Ничего не изменено кроме этого файла. Commit не создавался.

Классы утверждений:

- **FACT** — проверено чтением файла или командой, воспроизводимо, с `file:line`.
- **INFERENCE** — вывод из фактов, исполнением не проверенный.
- **RECOMMENDATION** — предложение, не факт.

---

## 1. Executive verdict

**Главный вывод: план решает не ту проблему.**

`PROJECT_EXECUTION_PLAN.md` (2047 строк) строит best-so-far persistence, query
expansion ladder, pagination, adaptive budget и semantic activation — то есть
делает **поиск ассетов настойчивее**. Но фактический дефект не в настойчивости
поиска. Он в том, что для типичного русскоязычного запуска **поиск не отправляет
ни одного запроса**, а сценарий пишется **шаблоном из шести фраз**.

Три факта, каждый проверен построчно:

1. **FACT.** Единственный OpenAI-вызов во всём production-дереве —
   [semantic_visual_openai.py:438](src/assets/semantic_visual_openai.py:438).
   Это Vision-оценщик кандидатов, и он выключен
   ([config/semantic_visual.json:1-2](config/semantic_visual.json:1) —
   `enabled: false`, `backend: mock`). В research, script и visual planning
   LLM **нет вообще**. `LLMScriptProvider` — интерфейс без клиента
   ([llm.py:74](src/content/script_engine/providers/llm.py:74) —
   `implementation_status="planned"`).

2. **FACT.** Документированный основной вход `--input-mode topic`
   ([COMMANDS.md:279-285](COMMANDS.md:279)) не даёт исходного текста:
   `ingest_article` для topic-режима возвращает статью, где `text` = сама тема
   ([article_ingestor.py:55-57](src/news/article_ingestor.py:55)). Дальше
   `_is_thin` срабатывает
   ([deterministic.py:247-252](src/content/script_engine/providers/deterministic.py:247))
   и сценарий уходит в `legacy_template` — шесть заранее написанных фраз
   ([legacy_template.py:114-121](src/content/script_engine/providers/legacy_template.py:114)).

3. **FACT.** Слоя перевода нет, а все remote-провайдеры объявлены English-only
   ([query_adapter.py:43-56](src/assets/query_adapter.py:43)). Русский intent до
   провайдера не доходит; английский запрос строится либо из авторского
   `visual_brief` (который в автоматическом потоке **никто не создаёт** — он
   приходит только из пользовательского `--visual-briefs` файла), либо из
   зашитого словаря на ~40 слов про Антарктиду, лабораторию и микропластик
   ([query_adapter.py:62-79](src/assets/query_adapter.py:62)). Если ни то ни
   другое не сработало — `query_translation_required` и **запрос не
   отправляется** ([query_adapter.py:192-206](src/assets/query_adapter.py:192)).

**INFERENCE.** Для темы вида «Почему вороны запоминают человеческие лица»
(пример из самого [COMMANDS.md:281](COMMANDS.md:281)) цепочка выглядит так:
шаблонный сценарий → русский visual plan → ноль английских терминов в глоссарии
→ ноль отправленных запросов → ноль кандидатов → все сцены `missing` → `strict`
блокирует render. Единственное, что реально уходит в провайдер — одна из
**четырёх фиксированных строк** `legacy_broad_query`, которая безусловно
дописывается в `alternative_queries` каждой сцены каждого видео
([legacy_format.py:94-100, 161-164](src/content/visual_planning/legacy_format.py:94)).

Поэтому PLAN-9A…PLAN-10C построены поверх пустоты: **лестница расширения нуля
запросов даёт ноль**. Это не значит, что план плохо написан — он написан
исключительно тщательно. Это значит, что он оптимизирует ступень, которая не
является узким местом.

**Второй вывод: governance перевешивает продукт.** 2047 строк плана + 684 строки
registry + 3 уровня правил ([HARD]/[ARCH]/[HINT]) + Task contract из 10 полей +
Knowledge Salvage Gate + Reversible retirement mechanism + Owner Lookup + три
tripwire — на репозиторий с **одним активным workflow**, у которого сломан
основной вход. Критический путь до первого продуктового изменения — девять
шагов, из которых восемь не трогают продукт.

**Третий вывод: фундамент лучше, чем о нём думает план.** `src/assets/completion/`,
`src/subtitles/`, `src/audio/scene_timeline.py`, `src/production_catalog/`,
`src/content_creation/capabilities.py`, `src/news/final_renderer.py` — это
сильный, честный, хорошо задокументированный код. Его не надо переписывать.

---

## 2. Audit coverage

**FACT.** Inventory получен через `git ls-files` — **664 tracked файла**.
`git status --short --branch` на момент аудита: ветка `governance-reset`,
одна untracked запись `output/`.

| Категория | Количество | Как обработано |
|---|---|---|
| Всего tracked | 664 | inventory построен |
| Прочитано полностью, построчно | 58 | см. список ниже |
| Проверено программно (grep/AST/wc/git) | ~140 | поиск callers, hardcodes, метрик |
| Прочитано частично (head/sed, ≥40 строк) | 9 | `asset_manager.py`, `anime_factory/pipeline.py`, `anime_factory/modules/paths.py`, `requirements.lock`, 6 × `skills/*/SKILL.md` (frontmatter + workflow) |
| Пропущено осознанно | ~450 | см. таблицу пропусков |

### Прочитано полностью (построчно)

**Governance / root (9):** `AGENTS.md`, `CLAUDE.md`, `README.md`, `COMMANDS.md`,
`pyproject.toml`, `requirements.txt`, `pipeline.py`, `.claude/settings.json`,
`.gitignore` (через `git check-ignore`/`ls-files -i`).

**docs/current (5):** `START_HERE.md`, `PROJECT_EXECUTION_PLAN.md` (2047 строк,
три захода), `CLEANUP_REGISTRY.md`, `CURRENT_STATE.md`, `SYSTEM_MAP.md`.

**docs/adr (1 полностью):** `0016-two-engine-product-architecture.md`.

**Entrypoints / CLI (4):** `src/ai_youtube/cli/main.py`,
`src/content_creation/cli.py`, `apps/news_to_short/main.py`,
`src/content_creation/capabilities.py`.

**Активный workflow (7):** `src/news/pipeline.py`,
`src/news/asset_manifest_builder.py` (1413 строк),
`src/news/asset_scene_completion.py`, `src/news/final_renderer.py`,
`src/news/visual_plan.py`, `src/news/research_engine.py`,
`src/news/article_ingestor.py`.

**Application boundary (1):**
`src/ai_youtube/apps/content_creator/workflows/fullscreen_voiceover/use_case.py`
(906 строк).

**Asset / semantic (9):** `src/assets/query_adapter.py`,
`src/assets/completion/modes.py`, `src/assets/semantic_selection/models.py`,
`scene_analyzer.py`, `query_generator.py`, `vision_validator.py`,
`src/providers/registry.py`, `src/providers/local_library_provider.py`,
`config/semantic_visual.json`.

**Content engines (5):** `src/content/script_engine/providers/deterministic.py`,
`legacy_template.py`, `llm.py`, `registry.py`,
`src/content/visual_planning/planners/deterministic.py`,
`src/content/visual_planning/legacy_format.py`.

**Shared services (5):** `src/subtitles/engine.py`, `src/audio/scene_timeline.py`,
`src/audio/tts/provider_manager.py`, `src/projects/repository.py`,
`src/production_catalog/catalog.py`.

**Config (4):** `config/visual_preview.json`,
`channels/nature_science_news_ru/channel_config.json`, `config/semantic_visual.json`,
`requirements.txt`.

**Tests / QA (2):** `tests/network_guard.py`, `tests/__init__.py`,
`tools/qa/check_agent_docs.py`.

### Пропущено — и почему

| Группа | Объём | Точная причина |
|---|---|---|
| `MOSS_TTS_Nano/` | untracked, ~56k файлов | vendor tree, исключён заданием; **проверен reference-поиском** — активный `TTSProviderManager` MOSS не регистрирует |
| Runtime media (`projects/`, `assets/**` медиа, `music/`, `episodes/`) | 0 tracked медиа | disposable runtime, исключено заданием |
| `docs/implementation/**` | 96 файлов | historical implementation reports; **проверен production-зависимостью**: `openai_live_evaluation` действительно читается production-кодом (C31 подтверждён) |
| `docs/archive/**`, `docs/audits/**` (прежние) | 19 файлов | historical, явно не source of truth по `AGENTS.md:17` |
| `legacy/` | 8 файлов, 424 строки | **проверен caller-поиском**: ноль Python-callers repo-wide, подтверждает C17 |
| `src/legacy_pipeline/workflow.py`, 20 движков корня `src/` | ~4900 строк | запланированы к retirement (PLAN-L); **проверены reference-поиском** на неожиданные зависимости активного кода |
| `docs/adr/0001`–`0015` | 15 файлов | прочитаны заголовки и решения; полностью прочитан только 0016 как определяющий целевую архитектуру |
| `tests/test_*.py` (тела) | 112 модулей, 30 317 строк | прочитаны структурно: имена, `subprocess`-использование, счётчики; тела не читались построчно |
| `anime_factory/modules/*` (13 из 16) | ~1500 строк | прочитаны `paths.py` и `pipeline.py`; остальные — по именам и импортам |
| Бинарные ассеты (`.jpg`, `.png`, `.svg`, `.mp4`, `.pdf`) | ~25 tracked | исключено заданием |

### Исключения, возвращённые в scope

**FACT.** Три пропущенных пути пришлось вернуть, потому что от них зависит
активный код:

1. `docs/implementation/openai_live_evaluation/` — production-зависимость из
   `src/assets/semantic_visual_evaluation_tooling.py` (registry C31
   подтверждён).
2. `scripts/test_moss_voices.py` — импортируется на верхнем уровне
   [pipeline.py:9](pipeline.py:9), то есть является production-импортом, а не
   скриптом (C18 подтверждён).
3. `assets/library/metadata/media_index.example.json` — schema локальной
   медиатеки, читается активным news-путём через `rank_local_assets`.

### Честная граница аудита

- **Full offline suite я не запускал** — владелец отклонил запуск. Все
  утверждения о тестах в этом отчёте основаны на чтении кода и на измерении,
  записанном в плане (1441 тест, 4 failures, 3 errors на `fe2df5b`). Я это
  измерение **не подтверждал исполнением**.
- Ни один сетевой, платный, render или TTS-вызов не выполнялся.
- Grep/search нигде не выдаётся за чтение source-файла: все `file:line` в
  findings ниже относятся к файлам из списка «прочитано полностью», кроме явно
  помеченных.

---

## 3. What is already strong — НЕ трогать без причины

Это не вежливость. Перечисленное ниже — лучшая часть репозитория, и любой план,
который предлагает её «унифицировать», делает продукт хуже.

**S-1. `src/assets/completion/modes.py` — canonical readiness vocabulary.**
Разделение «можно показать в draft» / «можно выбрать автоматически» / «можно
публиковать» на независимо проверяемые факты — правильное архитектурное
решение, и docstring [modes.py:1-32](src/assets/completion/modes.py:1) честно
объясняет, какую именно ошибку оно исправляет. `_rights_are_allowed`
([modes.py:451-543](src/assets/completion/modes.py:451)) резолвит четыре
копии rights-записи консервативно, с правом вето у каждой и требованием хотя бы
одного положительного подтверждения — это fail-closed сделанный правильно.
Проверка `record["allowed_for_render"] is not True`
([modes.py:520](src/assets/completion/modes.py:520)) вместо truthy-проверки —
именно та деталь, которая отличает настоящую границу безопасности от её
имитации. **План прав, что это трогать не нужно.**

**S-2. `src/content_creation/capabilities.py` — честная витрина.**
Модуль систематически отказывается показывать то, чего нет: стили субтитров
`phrase`/`shorts_large`/`word_by_word` не перечислены, потому что не
реализованы ([capabilities.py:170-174](src/content_creation/capabilities.py:170));
MOSS и `local_stub` не предлагаются как production-голос
([capabilities.py:17-20](src/content_creation/capabilities.py:17)); legacy-каналы
показаны, но помечены `usable_for_content_creation: false`
([capabilities.py:249-257](src/content_creation/capabilities.py:249)).
Это редкая и ценная дисциплина.

**S-3. `src/audio/scene_timeline.py`.** Мост между реальной длительностью
озвучки и визуальным таймлайном. Docstring
([scene_timeline.py:1-25](src/audio/scene_timeline.py:1)) фиксирует конкретный
измеренный дефект (51.5 с визуала против 59.47 с речи) и то, как он закрыт.
`scene_render_duration` ([scene_timeline.py:267](src/audio/scene_timeline.py:267))
— единственное место, кодирующее «реальная озвучка важнее плана», что не даёт
renderer и subtitles разойтись.

**S-4. `src/news/final_renderer.py`.** Работа с FFmpeg сделана аккуратно:
экранирование апострофов в concat-файле под правила демуксера, а не шелла
([final_renderer.py:445-455](src/news/final_renderer.py:445)); объяснение,
почему `-shortest` + `-c:v copy` ненадёжны
([final_renderer.py:549-562](src/news/final_renderer.py:549)); `apad` под
sidechain, чтобы хвост не оказался тишиной
([final_renderer.py:518-528](src/news/final_renderer.py:518)). Это код человека,
который смотрел на реальный вывод.

**S-5. `src/production_catalog/`.** Единственный честный реестр
active/planned/disabled. Комментарий о том, почему `longform` выключен
([catalog.py:65-69](src/production_catalog/catalog.py:65)) — образец того, как
надо документировать флаг.

**S-6. `src/subtitles/`.** Один движок с явным списком того, чего он не делает
([engine.py:6-9](src/subtitles/engine.py:6)). Fingerprint считается по тому, что
реально влияет на субтитры ([engine.py:35-49](src/subtitles/engine.py:35)) —
правка визуального интента не вызывает перегенерацию.

**S-7. `src/projects/repository.py`.** Read-only слой над двумя формами
манифестов, с явным отказом стать третьей системой
([repository.py:17-25](src/projects/repository.py:17)).

**S-8. `tests/network_guard.py`.** Guard на уровне сокета, а не мока
библиотеки — правильный уровень перехвата.

**S-9. Плотность объяснений в комментариях.** Большинство нетривиальных решений
сопровождается объяснением «что было сломано и почему сделано так». Для проекта,
который ведут агенты, это самый ценный из активов. **Любой массовый рефакторинг,
который эти комментарии потеряет, — чистый убыток.**

---

## 4. Critical findings

### CRITICAL-1 — Асинхронный поиск не может отправить запрос для типичной русской темы

**FACT.** Цепочка проверена построчно:

- `PROVIDER_QUERY_LANGUAGES` объявляет все remote-провайдеры English-only
  ([query_adapter.py:43-56](src/assets/query_adapter.py:43)).
- `build_scene_queries` при `intent_language="ru"` и русском `primary_query`
  идёт в ветку `_explicit_provider_queries or _english_queries`
  ([query_adapter.py:189-190](src/assets/query_adapter.py:189)).
- `_english_queries` требует `visual_brief` с латинскими полями
  ([query_adapter.py:331-357](src/assets/query_adapter.py:331)); иначе падает
  на `_glossary_terms` + `_latin_terms`
  ([query_adapter.py:360-367](src/assets/query_adapter.py:360)).
- `GLOSSARY` — 40 пар, покрывающих Антарктиду, лабораторию, микропластик,
  спутники ([query_adapter.py:62-79](src/assets/query_adapter.py:62)).
- Нет совпадения → `STATUS_TRANSLATION_REQUIRED`, провайдер добавляется в
  `untranslatable_providers`, **запрос не отправляется**
  ([query_adapter.py:192-206](src/assets/query_adapter.py:192)).
- `_search_scene_providers` пропускает провайдера без разрешённых запросов
  ([asset_manifest_builder.py:328-346](src/news/asset_manifest_builder.py:328)).

**FACT.** `visual_brief` в автоматическом потоке не создаётся никем: единственный
источник — пользовательский файл через `--visual-briefs`
([request_builder.py:58](src/content_creation/request_builder.py:58) →
`load_visual_briefs`). Детерминированный планировщик его не заполняет.

**FACT.** Единственная строка, которая гарантированно доходит до английского
провайдера, — `legacy_broad_query`, безусловно дописываемая в
`alternative_queries` каждой сцены
([legacy_format.py:161-164](src/content/visual_planning/legacy_format.py:161)).
Она возвращает одну из четырёх констант
([legacy_format.py:94-100](src/content/visual_planning/legacy_format.py:94)):
`"whale mother calf aerial ocean"`, `"scientific researchers nature field
observation"`, `"ocean wildlife aerial waves"`, `"nature science wildlife
observation"`.

**INFERENCE.** Значит, для любой темы вне четырёх этих категорий каждая сцена
каждого видео ищется одной и той же строкой `"nature science wildlife
observation"`. Это и есть наблюдаемая пользователем «плохая визуальная
релевантность» — и она не лечится ни persistence, ни pagination, ни adaptive
budget.

**RECOMMENDATION.** Слой перевода intent → провайдерский язык — **первый
продуктовый слайс, до PLAN-9A**. Не «переводчик вообще»: узкая, проверяемая
задача — перевести subject / action / place / exact entities визуального плана в
английские термины, с сохранением исходных, с пометкой источника перевода и
fail-closed при неуверенности. У проекта уже есть подходящий seam
(`ProviderQuery.source`), уже объявлена зависимость `openai==2.36.0`, уже есть
approval-gate для платных вызовов, и уже есть детерминированный offline-fallback
(глоссарий) для тестов. Это переиспользование, а не новая подсистема.

Классификация относительно плана: **D — PLAN DOES NOT COVER IT.** Слово
«перевод» встречается в плане 7 раз, все — про перевод прозы документации
(OD-5) и про «перевод callers». Продуктовая capability отсутствует.

---

### CRITICAL-2 — Основной документированный вход даёт шаблонный сценарий

**FACT.** `INPUT_MODE_TOPIC` → `_article_from_text(job.topic, job.topic, ...)`,
то есть `article["text"]` равен самой теме
([article_ingestor.py:55-57](src/news/article_ingestor.py:55)).

**FACT.** `build_research` разбивает этот текст на предложения и берёт первые
восемь ([research_engine.py:12-25](src/news/research_engine.py:12)). Для темы из
одной фразы получается один claim.

**FACT.** `_is_thin` возвращает `True` при `len(units) < 2` или при доступной
длительности меньше `max(12.0, target*0.35)`
([deterministic.py:247-252](src/content/script_engine/providers/deterministic.py:247)).

**FACT.** `_fallback` передаёт управление `LegacyTemplateScriptProvider`
([deterministic.py:150-170](src/content/script_engine/providers/deterministic.py:150)),
который собирает ровно шесть фраз по фиксированному шаблону
([legacy_template.py:110-121](src/content/script_engine/providers/legacy_template.py:110)),
включая литералы «Наблюдение выглядит простым, но за ним стоит важная деталь:»
и «И пока появляются новые данные, самый интересный вопрос остается открытым».

**INFERENCE.** `--input-mode topic` — это то, что показывает мастер первым
вопросом и что документировано как основной сценарий
([COMMANDS.md:279-285](COMMANDS.md:279)). Значит, дефолтный путь продукта всегда
производит одно и то же шаблонное видео с подставленной темой.

**RECOMMENDATION.** Либо (а) topic-режим должен получать материал — через
research-провайдера, который реально что-то ищет, либо (б) topic-режим должен
честно требовать источник и отказываться, вместо тихого отката на шаблон. Тихий
откат хуже обоих вариантов: он выглядит как успех. Минимальная честная правка —
поднять `insufficient_source_material` из `warnings` в блокирующий статус для
`strict`, оставив шаблон только под явным `--allow-template-script`.

Классификация: **D — PLAN DOES NOT COVER IT.**

---

### CRITICAL-3 — «AI-YouTube» не содержит AI в контентном пути

**FACT.** Repo-wide поиск `import openai|from openai|OpenAI(` по
`src/ ai_youtube/ apps/ anime_factory/ tools/` даёт **две строки**, обе в
[semantic_visual_openai.py:438-440](src/assets/semantic_visual_openai.py:438).

**FACT.** Этот единственный вызов выключен трижды: `enabled: false`,
`backend: "mock"`, `openai.enabled: false`, `allow_paid_vision: false`,
`maximum_calls_per_project: 0`
([config/semantic_visual.json:1-34](config/semantic_visual.json:1)).

**FACT.** `research_engine.py` — regex-разбиение и словарный классификатор
([research_engine.py:48-59](src/news/research_engine.py:48)).
`script_engine/deterministic.py` — экстрактивный отбор чужих предложений по
`hook_score`/`payoff_score`. `visual_planning/deterministic.py` — извлечение
сущностей по стеммингу. Ни один не генерирует текст.

**INFERENCE.** Продукт называется системой автоматического создания
качественного видео, но ни одна из трёх творческих задач — исследование, текст,
визуальная идея — не решается моделью. Отсюда потолок качества: система умеет
собрать видео, но не умеет придумать его.

**Дополнительная ирония, FACT.** Единственная часть репозитория с настоящим ML —
Anime Factory: `faster-whisper` транскрипция, детекция лиц, детекция сцен,
динамический кроп, анализ аудиоэнергии, скоринг кандидатов
([anime_factory/pipeline.py:16-33](anime_factory/pipeline.py:16)). И она
`enabled=False`, `implementation_status="planned"`
([catalog.py:44-45](src/production_catalog/catalog.py:44)).

**RECOMMENDATION.** Определить, где именно модель обязана быть, а где
детерминированность ценнее. Моё предложение: модель обязательна на трёх точках —
(1) research/материал для topic-режима, (2) визуальный intent в английских
терминах (см. CRITICAL-1), (3) опциональная проверка кадра (уже есть, выключено).
Сценарий может остаться экстрактивным — это защищает от выдумывания фактов и
является сильной стороной, но только при наличии настоящего исходного материала.

Классификация: **D — PLAN DOES NOT COVER IT.** План рассматривает asset search
как единственную продуктовую дыру («Продуктовая рамка PLAN-9 и PLAN-10»,
[план:1267-1301](docs/current/PROJECT_EXECUTION_PLAN.md:1267)).

---

### CRITICAL-4 — Двойная оркестрация: use case вызывает pipeline семь раз

**FACT.** `FullscreenVoiceoverUseCase` вызывает `run_news_to_short_job`
**семь раз** за один запуск: `_run_safe_pipeline`
([use_case.py:182](src/ai_youtube/apps/content_creator/workflows/fullscreen_voiceover/use_case.py:182)),
`_run_voice_stage` ([use_case.py:253](src/ai_youtube/apps/content_creator/workflows/fullscreen_voiceover/use_case.py:253)),
`_run_subtitles` ([use_case.py:455](src/ai_youtube/apps/content_creator/workflows/fullscreen_voiceover/use_case.py:455)),
и четыре раза в `_render_and_export` ([use_case.py:499, 510, 527, 553](src/ai_youtube/apps/content_creator/workflows/fullscreen_voiceover/use_case.py:499)).

**FACT.** Каждый вызов заново создаёт `NewsProjectStore`, заново загружает
`job.json`, заново входит в цикл по стадиям и заново сохраняет job
([pipeline.py:125-224](src/news/pipeline.py:125)). Use case дополнительно
перечитывает job вручную ещё трижды
([use_case.py:202, 260, 311](src/ai_youtube/apps/content_creator/workflows/fullscreen_voiceover/use_case.py:202)).

**INFERENCE.** Существуют две конкурирующие модели исполнения над одним списком
стадий: цикл resume/force/stop-stage внутри `run_news_to_short_job` и
пошаговый вызов снаружи. Условная логика в цикле
([pipeline.py:139-183](src/news/pipeline.py:139) — шесть вложенных условий
пропуска стадии) существует потому, что оба режима должны сосуществовать. Это
источник трудноуловимых багов resume и причина, по которой комментарий на
[pipeline.py:142-144](src/news/pipeline.py:142) описывает уже случившуюся
регрессию («generic resume `continue` won first and the pipeline accidentally
ran every later stage»).

**RECOMMENDATION.** Один владелец исполнения стадий. Либо use case описывает
план стадий декларативно и передаёт его runner-у один раз, либо runner
становится приватным, а use case — единственным оркестратором. Второй вариант
дешевле: `run_news_to_short_job` уже умеет всё, что нужно; надо убрать
пошаговые вызовы, а не цикл.

Классификация: **D — PLAN DOES NOT COVER IT.** Registry C05 фиксирует
«определить app-specific и shared ownership», но двойная оркестрация как дефект
не названа.

---

### CRITICAL-5 — Semantic-слой существует, но по построению не влияет на отбор

**FACT.** `analyse_semantic_visual_for_project` вызывается из `_write_reviews`
([asset_manifest_builder.py:900-926](src/news/asset_manifest_builder.py:900)),
то есть **после** того, как `build()` уже прошёл по всем сценам и выбрал ассеты
([asset_manifest_builder.py:186-194](src/news/asset_manifest_builder.py:186)).

**FACT.** Сервис явно проверяет, что отбор не изменился, и предупреждает если
изменился (`_selection_fingerprint` →
`"selected_candidate_changed_unexpectedly"`,
[semantic_visual_service.py:181, 392-394](src/assets/semantic_visual_service.py:181)).
То есть неизменность отбора — это его **инвариант**, а не побочный эффект.

**FACT.** `_semantic_visual_summary` жёстко пишет
`"semantic_rerank_enabled": False` независимо от конфига
([asset_manifest_builder.py:997](src/news/asset_manifest_builder.py:997)).

**FACT.** `vision_validator.validate_candidate_vision` — заглушка из семи строк,
безусловно возвращающая `vision_validation_enabled: False`
([vision_validator.py:6-13](src/assets/semantic_selection/vision_validator.py:6)).

**INFERENCE.** ~2900 строк (`semantic_visual_*.py` — 968 + 1000 + 982 + 462 +
102 + 71 + 63 + 53) обслуживают путь, который выключен и по конструкции не
влияет на решение. Это самая большая единица неоплаченного сложностного долга в
репозитории.

**RECOMMENDATION.** План здесь **прав по направлению** (PLAN-9C — «semantic
decision wiring»), но неправ по приоритету: подключать Vision к ранжированию
кандидатов, которых ноль (CRITICAL-1), бессмысленно. Порядок должен быть:
запросы → кандидаты → потом ранжирование.

Классификация: **B — PLAN PARTIALLY COVERS IT** (wiring назван) + **F — BETTER
APPROACH EXISTS** (неверный порядок относительно CRITICAL-1).

---

## 5. Architecture findings

### HIGH-1 — Topic-hardcodes распределены по шести модулям, а не по одному

**FACT.** План утверждает, что topic-specific hardcode находится в
`query_generator.py` ([план:1855-1857](docs/current/PROJECT_EXECUTION_PLAN.md:1855)),
и делает этот файл единственной разрешённой зоной PLAN-9B
([план:1337-1338](docs/current/PROJECT_EXECUTION_PLAN.md:1337)). Фактический
поиск по `src/` (исключая legacy) находит хардкоды в шести модулях:

| Файл | Что зашито |
|---|---|
| [scene_analyzer.py:124-132](src/assets/semantic_selection/scene_analyzer.py:124) | `_infer_subject` знает только `southern right whale` / `right whale` / `whale` |
| [scene_analyzer.py:151-155](src/assets/semantic_selection/scene_analyzer.py:151) | `_infer_location` знает только Австралию |
| [scene_analyzer.py:20-21](src/assets/semantic_selection/scene_analyzer.py:20) | `MARINE_CONTEXT_NEGATIVES`, `OCEAN_TERMS` |
| [scene_analyzer.py:118-119](src/assets/semantic_selection/scene_analyzer.py:118) | `_infer_priority` ветвится по `whale`/`ocean` |
| [query_generator.py:41-42](src/assets/semantic_selection/query_generator.py:41) | `_animal_category` → `"whale"`; литерал `"nature"` на строке 16 |
| [candidate_ranker.py:228-264, 376-379](src/assets/semantic_selection/candidate_ranker.py:228) | orca/killer whale/Orcinus orca regex, alias `southern right whale` |
| [continuity_checker.py:7, 19-23, 43-44](src/assets/semantic_selection/continuity_checker.py:7) | `OCEAN` множество, правило `ocean→desert→ocean` |
| [query_adapter.py:62-79](src/assets/query_adapter.py:62) | глоссарий под Антарктиду/микропластик |
| [legacy_format.py:94-100](src/content/visual_planning/legacy_format.py:94) | четыре фиксированные строки |
| **[modes.py:295-296](src/assets/completion/modes.py:295)** | `ambiguous_whale_for_orca_scene`, `missing_orca_evidence_for_orca_scene` — **внутри canonical safety gate** |

**INFERENCE.** Последняя строка самая тревожная: доменный хардкод про косаток
живёт в `blocking_reasons`, то есть в правиле класса `[HARD]`, которое план
объявляет неприкосновенным.

**RECOMMENDATION.** Allowed zones PLAN-9B нужно расширить на весь
`src/assets/semantic_selection/` плюс `query_adapter.GLOSSARY` плюс
`legacy_format.legacy_broad_query`. И признать, что доменные правила
(«косатка — не просто кит», «океан не соседствует с пустыней») — это
**знание канала**, а не код: их место в конфиге канала или в visual brief, а не
в `if` внутри общего движка.

Классификация: **C — PLAN MISUNDERSTANDS IT.** План измерил один файл и принял
его за всю проблему; allowed zones сделали бы полное исправление нарушением
scope.

---

### HIGH-2 — Две реализации локальной медиатеки с разными правилами прав

**FACT.** Продакшн ищет по локальной библиотеке через `rank_local_assets` →
`search_local_assets`
([asset_manifest_builder.py:1246-1333](src/news/asset_manifest_builder.py:1246)).
Правило допуска: `rights_status in ALLOWED_RENDER_RIGHTS`, дефолт —
`RIGHTS_REFERENCE_ONLY` ([строка 1272](src/news/asset_manifest_builder.py:1272)).

**FACT.** Параллельно существует `LocalLibraryStockProvider` с **другим**
правилом: `schema_version >= 1` **и** `allowed_for_render` **и** не
`review_required` **и** `license` — dict **и** `provenance` — dict
([local_library_provider.py:129-136](src/providers/local_library_provider.py:129)),
плюс повторный отказ после `apply_policy_to_candidate`
([строка 80-81](src/providers/local_library_provider.py:80)).

**FACT.** `LocalLibraryStockProvider` не зарегистрирован в
`create_default_stock_providers` ([registry.py:15-37](src/providers/registry.py:15));
его единственный caller — листинг capabilities в диагностике
([provider_diagnostics.py:125](src/assets/provider_diagnostics.py:125)).

**INFERENCE.** Это ровно тот случай, который `AGENTS.md:53-54` запрещает: две
реализации одной capability, способные разойтись в поведении — и они уже
разошлись, причём в правилах прав. Более строгая реализация — та, которую никто
не вызывает.

**RECOMMENDATION.** Не «регистрировать провайдера» (как ставит вопрос PLAN-10D),
а **выбрать одного владельца доступа к локальной медиатеке** и удалить второго.
Строгие правила провайдера — правильные; правила `rank_local_assets` —
снисходительные.

Классификация: **C — PLAN MISUNDERSTANDS IT.** PLAN-10D формулирует задачу как
«включить провайдера после аудита», не заметив, что путь уже включён другой
реализацией.

---

### HIGH-3 — Три схемы каналов и две системы проектов как постоянное состояние

**FACT.** Три несовместимые формы канала сосуществуют и явно перечислены в коде
([capabilities.py:242-257](src/content_creation/capabilities.py:242)):
`channels/<id>/channel.json` (project_foundation),
`channels/<id>/channel_config.json` + `voices.yaml` (news),
legacy-профиль для `pipeline.py --channel`. Тип определяется эвристикой по форме
файла ([capabilities.py:260-272](src/content_creation/capabilities.py:260)).

**FACT.** Две системы проектов: `job.json` (12 стадий, локализации) и
`project.json` (ProjectManifest без стадий), объединённые только read-only слоем
([repository.py:5-11](src/projects/repository.py:5)). Story card проекты не
имеют стадий вовсе, и `ProjectView.stages` для них — честный пустой список
([repository.py:385-387](src/projects/repository.py:385)).

**INFERENCE.** Следствие видно в UX: `project validate` работает только для
story card ([COMMANDS.md:347-348](COMMANDS.md:347)); resume работает только для
fullscreen ([COMMANDS.md:481-483](COMMANDS.md:481)). Каждая новая возможность
приходится реализовывать дважды или объявлять частично поддержанной.

**RECOMMENDATION.** Это правильная цель для будущего слайса, но **не сейчас**.
Пока активных workflow два и один из них сломан на входе, унификация хранилища —
дорогая работа без продуктового эффекта. План правильно ставит её в PLAN-13
(`M02`, `C10`).

Классификация: **A — PLAN ALREADY COVERS IT.**

---

### HIGH-4 — Каталог обещает export targets, которых renderer не производит

**FACT.** Каталог регистрирует пять целей с уникальными именами файлов, включая
`tiktok.mp4` и `stories.mp4`
([catalog.py:261-305](src/production_catalog/catalog.py:261)).

**FACT.** `_copy_platform_outputs` копирует master только в три файла:
`youtube_shorts.mp4`, `instagram_reels.mp4`, `facebook_reels.mp4`
([final_renderer.py:475](src/news/final_renderer.py:475)). `tiktok.mp4` и
`stories.mp4` не создаются никогда.

**FACT.** Оба шаблона объявляют все пять целей в `supported_export_targets`
([catalog.py:110-116, 186-192](src/production_catalog/catalog.py:110)).

**INFERENCE.** Это единственное найденное мной нарушение принципа честности,
который в остальном выдержан образцово (см. S-2). Плюс сами «пять целей» — это
копии одного файла, а не разные кодировки под площадки.

**RECOMMENDATION.** Либо убрать `tiktok`/`stories` из
`supported_export_targets`, либо перестать копировать master пять раз и
записывать один файл с явным списком совместимых площадок. Второе честнее и
экономит место.

Классификация: **D — PLAN DOES NOT COVER IT.**

---

### MEDIUM-1 — Тройное перекодирование ухудшает качество финального видео

**FACT.** Каждый сегмент кодируется в `libx264 -preset veryfast -crf 23`
([final_renderer.py:306-308](src/news/final_renderer.py:306) и
[:344-346](src/news/final_renderer.py:344)). Затем `_duration_control_args`
перекодирует конкатенацию в `-crf 20`
([final_renderer.py:573-578](src/news/final_renderer.py:573)). Затем
`_burn_ass_subtitles` перекодирует ещё раз в `-crf 21`
([final_renderer.py:592-598](src/news/final_renderer.py:592)).

**INFERENCE.** Три поколения lossy-кодирования с `veryfast` для продукта,
который позиционируется как «качественное видео». Первое кодирование сегментов
почти целиком избыточно: сегменты существуют только для того, чтобы их сразу
склеить.

**RECOMMENDATION.** Собирать таймлайн одним `filter_complex` с `concat`-фильтром
вместо concat-демуксера по перекодированным файлам, и жечь субтитры в том же
проходе. Один проход вместо трёх: лучше картинка, быстрее рендер, меньше
временных файлов. Это заметное улучшение качества за ограниченную работу.

Классификация: **D — PLAN DOES NOT COVER IT.**

---

### MEDIUM-2 — Поиск без пагинации, с жёстким лимитом 5 и без цикла

**FACT.** `limit=5` зашит в двух местах
([asset_manifest_builder.py:391](src/news/asset_manifest_builder.py:391),
[asset_scene_completion.py:328](src/news/asset_scene_completion.py:328)),
дефолт адаптера тоже 5
([asset_provider_adapters.py:40](src/news/asset_provider_adapters.py:40)).

**FACT.** `build()` проходит по сценам один раз, без внешнего цикла и без
критерия остановки ([asset_manifest_builder.py:186-194](src/news/asset_manifest_builder.py:186)).
Единственная повторная попытка — targeted slot search, ограниченная одной фазой
на сцену через локальный флаг `targeted_search_done`
([asset_scene_completion.py:143, 232](src/news/asset_scene_completion.py:143)).

**RECOMMENDATION.** План прав (PLAN-10B, PLAN-10C). Но эффект появится только
после CRITICAL-1.

Классификация: **A — PLAN ALREADY COVERS IT**, приоритет неверен.

---

### MEDIUM-3 — Anime runtime пишет внутрь исходного пакета

**FACT.** `PROJECT_ROOT = Path(__file__).resolve().parents[1]`, и эпизоды
создаются как `PROJECT_ROOT / "episodes" / <episode>`
([anime_factory/modules/paths.py:11, 34](anime_factory/modules/paths.py:11)).
`WorkspacePaths` не используется.

Классификация: **A — PLAN ALREADY COVERS IT** (registry C15).

---

### MEDIUM-4 — `pipeline.py` импортирует `scripts/` на верхнем уровне

**FACT.** [pipeline.py:9](pipeline.py:9) —
`from scripts.test_moss_voices import main as run_moss_voice_tests`, при этом
`packages.find.include` не содержит `scripts*`, а `py-modules = ["pipeline"]`
включает модуль в дистрибутив
([pyproject.toml:36-41](pyproject.toml:36)).

Классификация: **A — PLAN ALREADY COVERS IT** (C25 → PLAN-L4).

---

## 6. Product-quality findings

**HIGH-5. `strict` по умолчанию + пустой поиск = гарантированный отказ.**
**INFERENCE** из CRITICAL-1 + `DEFAULT_COMPLETION_MODE = MODE_STRICT`
([modes.py:68](src/assets/completion/modes.py:68)): в дефолтной конфигурации
типичный запуск не может дойти до render. `draft_complete` — opt-in
([COMMANDS.md:572-579](COMMANDS.md:572)). То есть дефолтный режим продукта — тот,
который для дефолтного входа не работает. Это не аргумент ослабить `strict`
(он правильный), а аргумент, что вход должен приносить кандидатов.

**MEDIUM-5. `config/semantic_visual.json` указывает на несуществующие модели.**
**FACT.** `"primary_model": "gpt-5.6-terra"`, `"comparison_model":
"gpt-5.6-luna"` ([config/semantic_visual.json:20-21](config/semantic_visual.json:20)).
Таких моделей не существует. Поскольку backend выключен, это не ломает ничего
сегодня, но включение приведёт к ошибке на первом же вызове.

**MEDIUM-6. Один и тот же master копируется под три имени.**
**FACT.** [final_renderer.py:474-478](src/news/final_renderer.py:474) — три
`shutil.copyfile` одного файла. **INFERENCE.** Утроенный размер проекта без
пользы; настоящая адаптация под площадку (длительность, safe zone, битрейт) не
выполняется, хотя `safe_zone_profile` в каталоге объявлен
([catalog.py:240](src/production_catalog/catalog.py:240)).

**MEDIUM-7. Музыка не проверяется на права, и это записано в манифест честно.**
**FACT.** [COMMANDS.md:457-459](COMMANDS.md:457) — `unverified_user_supplied`.
Это правильное поведение, отмечаю как хорошее, а не как дефект.

**LOW-1. Локализация объявлена шире, чем реализована.** **FACT.** Канал
объявляет `en` и `es` с `enabled: false` и пустыми `voice_id`
([channel_config.json:62-81](channels/nature_science_news_ru/channel_config.json:62)),
а `localization` объявляет 10 флагов реюза
([:37-49](channels/nature_science_news_ru/channel_config.json:37)). Переводчика
нет (CRITICAL-1), значит `localize_script` не может быть выполнен.

---

## 7. Tests / QA / agent infrastructure

**FACT (измерение, не норма).** 112 test-модулей, 30 317 строк, `conftest.py`
отсутствует, guard ставится импортом пакета
([tests/__init__.py](tests/__init__.py) — 3 строки).

**HIGH-6. Network guard не действует на 12 модулей, а не на 7.**
**FACT.** `grep -l subprocess tests/*.py` даёт **12** модулей:
`test_asset_cli_wiring`, `test_final_renderer_end_tail`,
`test_fullscreen_voiceover_application_boundary`, `test_moss_tts_provider`,
`test_news_to_short_pipeline`, `test_production_catalog_foundation`,
`test_project_foundation_cli`, `test_stage4_canonical_cli`,
`test_story_card_project_integration`, `test_story_card_short_renderer`,
`test_temporal_video_analysis`, `test_visual_preview_foundation`.
План называет **7** ([план:426-428](docs/current/PROJECT_EXECUTION_PLAN.md:426)).
Guard живёт в `tests/__init__.py` и в дочерний процесс не наследуется.

**RECOMMENDATION.** Закрывать не расширением guard на «subprocess boundary»
(как в PLAN-6B), а переменной окружения, которую production-код уважает как
kill-switch сети. Guard в тестовом пакете не может защитить чужой процесс; флаг
в окружении может.

Классификация: **B — PLAN PARTIALLY COVERS IT** (число занижено, механизм
сомнителен).

**HIGH-7. `check_agent_docs.py` проверяет 3 файла из 7 и не проверяет активный план.**
**FACT.** `CURRENT_DOCS` — кортеж из трёх путей
([check_agent_docs.py:13-17](tools/qa/check_agent_docs.py:13)).
`PROJECT_EXECUTION_PLAN.md`, `CLEANUP_REGISTRY.md`,
`ARCHITECTURE_BOUNDARY_MAP.md`, `PRODUCT_EVIDENCE_GATE.md` не проверяются.
`REQUIRED_SKILLS` — точное множество из шести
([:18-25](tools/qa/check_agent_docs.py:18)), поэтому добавление reviewer-skill
уронит тест. `REQUIRED_ARCHIVED_HANDOFFS` требует вечного существования десяти
архивных файлов ([:26-37](tools/qa/check_agent_docs.py:26)).
Классификация: **A — PLAN ALREADY COVERS IT** (PLAN-6A).

**HIGH-8. Skills существуют, но не загружаются, и учат устаревшему CLI.**
**FACT.** `.claude/` содержит только `settings.json`, `settings.local.json`,
`scheduled_tasks.lock` — каталога `skills/` там нет, авто-обнаружения нет.
**FACT.** Три из шести SKILL.md учат `python -m src.content_creation.cli`, а QA
проверяет только frontmatter, ссылки и `TODO`
([check_agent_docs.py:112-142](tools/qa/check_agent_docs.py:112)).
Классификация: **A — PLAN ALREADY COVERS IT** (PLAN-6A + PLAN-7).

**MEDIUM-8. Deny-list не покрывает запись в `.env`.**
**FACT.** [.claude/settings.json](.claude/settings.json) содержит только
`Read(./.env)` и варианты; `Write`/`Edit` по `.env` не запрещены. `Bash(git clean *)`
не ловит голый `git clean`.
Классификация: **A — PLAN ALREADY COVERS IT** (PLAN-6D-1).

**MEDIUM-9. Тесты как система: имена кодируют историю, а не ответственность.**
**FACT.** `test_anime_factory_v3/v4`, `test_stage1…stage4`,
`test_*_internals_contract` (6 модулей характеризации завершённых рефакторингов).
План правильно отказывается делать реструктуризацию приоритетом
([план:416-424](docs/current/PROJECT_EXECUTION_PLAN.md:416)) — **согласен**.

**Не проверено мной.** Зелёность baseline. План фиксирует 4 failures + 3 errors
на `fe2df5b`; я это не воспроизводил.

---

## 8. Duplication and unnecessary complexity

| # | Дублирование | Evidence | Оценка |
|---|---|---|---|
| 1 | Два пути к локальной медиатеке | HIGH-2 | реальное, с расхождением в правах |
| 2 | Два package root `ai_youtube/` и `src/ai_youtube/` | `__main__.py` идентичны (план, FACT) | реальное, симптом |
| 3 | Два CLI над одним workflow: канонический `create/resume` и `apps/news_to_short/main.py` (83 строки argparse) | [apps/news_to_short/main.py:14-34](apps/news_to_short/main.py:14) | реальное |
| 4 | Двойная оркестрация стадий | CRITICAL-4 | реальное, самое вредное |
| 5 | Три схемы каналов | HIGH-3 | реальное, дорогое |
| 6 | Две системы проектов | HIGH-3 | реальное, дорогое |
| 7 | `src/news/asset_manager.py` — 266-строчный фасад, реэкспортирующий ~40 имён | [asset_manager.py:12-60](src/news/asset_manager.py:12) | фасад без exit condition |
| 8 | `src/content_creation/cli.py`, `wizard.py`, `service.py`, `*_use_case.py` — цепочка фасадов над фасадами | [cli.py:1-6](src/content_creation/cli.py:1) | накопленный переходный слой |
| 9 | ~2900 строк semantic_visual, не влияющих на решение | CRITICAL-5 | крупнейший неоплаченный долг |
| 10 | `legacy_broad_query` — четвёртая по счёту реализация «широкого запроса» | [legacy_format.py:84-100](src/content/visual_planning/legacy_format.py:84) | вредное: перекрывает новые |

**INFERENCE о природе долга.** Этапы 6A–6G дробили большие файлы на фасад +
модули и объявляли результат «complete». Фасады остались навсегда: registry
помечает S01–S07 как `выполнено`, но ни у одного нет exit condition. Дробление
без последующего удаления фасада не уменьшает сложность — оно её перемещает и
добавляет уровень косвенности. **Это системная ошибка предыдущей программы,
которую новый план наследует.**

---

## 9. What can be removed

Каждая строка — предложение, не разрешение. Ни одно удаление не выполнялось.

| Что | Почему | Риск | Проверено |
|---|---|---|---|
| `legacy/` (8 файлов, 424 строки) | ноль Python-callers repo-wide | низкий | FACT, caller-поиск |
| `legacy_broad_query` + 4 константы | активно вредит: перекрывает осмысленные запросы шумом | **отрицательный** — удаление улучшает | FACT |
| `src/assets/semantic_selection/vision_validator.py` | 7-строчная заглушка, всегда `False` | низкий | FACT |
| `apps/news_to_short/main.py` | второй CLI активного workflow | низкий после сверки флагов | FACT, OD-2 |
| `apps/youtube_pipeline/`, `apps/anime_factory/` | 8-строчные делегации | низкий | FACT |
| Дублирующие копии master (`instagram_reels.mp4`, `facebook_reels.mp4`) | побайтовые копии | низкий | FACT |
| `tiktok`/`stories` из `supported_export_targets` | файлы не производятся | низкий | FACT |
| `src/tts_providers/` + `MOSS_TTS_Nano/` | ноль callers после L3/L4 | низкий | план, OD-7 |
| Один из двух путей к медиатеке | HIGH-2 | средний | FACT |
| `src/legacy_pipeline/workflow.py` + 20 движков корня | один production-caller | средний | план, C30 |
| Промежуточное кодирование сегментов | MEDIUM-1 | средний | INFERENCE |

**Не удалять, вопреки соблазну:**
`src/assets/completion/` · `src/subtitles/` · `src/audio/scene_timeline.py` ·
`src/production_catalog/` · `capabilities.py` · `final_renderer.py` ·
`tests/network_guard.py` · плотные объясняющие комментарии.

---

## 10. What should be preserved

1. **Rights / provenance / `must_avoid` / misleading gates** — единственная
   часть, где проект строже среднего. `_rights_are_allowed` с вето каждой копии
   ([modes.py:451-543](src/assets/completion/modes.py:451)) сохранить дословно.
2. **Approval gate на платные вызовы** — трёхуровневый: инструкция в `AGENTS.md`,
   permission в `.claude/settings.json`, проверка в
   [provider_manager.py:26-30](src/audio/tts/provider_manager.py:26)
   (`PermissionError` при `paid and not approved`). План верно считает, что
   отдельный owner не нужен.
3. **Tolerant readers** — чтение старых `job.json`/манифестов без миграции.
4. **Честность каталога и capabilities** (S-2, S-5).
5. **Экстрактивность сценария** — отказ выдумывать факты. При наличии настоящего
   материала это преимущество, а не ограничение.
6. **`ProjectRepository` как read-only** — явный отказ стать третьей системой.
7. **Объясняющие комментарии.**
8. **Anime Factory как рабочая source-to-clips реализация** — единственный
   настоящий ML в репозитории. План прав, что переписывать её запрещено.

---

## 11. Missing capabilities / opportunities

| # | Чего нет | Почему важно | Severity |
|---|---|---|---|
| 1 | Слой перевода intent → язык провайдера | без него поиск не работает (CRITICAL-1) | CRITICAL |
| 2 | Research с настоящим материалом для topic-режима | без него сценарий шаблонный (CRITICAL-2) | CRITICAL |
| 3 | Обратная связь «что получилось» → «как искать дальше» | сейчас поиск однопроходный | HIGH |
| 4 | Автоматический `visual_brief` | вся английская ветка запросов зависит от того, что заполнит человек | HIGH |
| 5 | Кэш кандидатов между запусками | каждый resume ищет заново | MEDIUM |
| 6 | Настоящая адаптация под площадку | сейчас копии одного файла | MEDIUM |
| 7 | Word-level тайминги субтитров | контракт есть, писателя нет ([capabilities.py:200-202](src/content_creation/capabilities.py:200)) | LOW |
| 8 | Единый kill-switch сети для подпроцессов | HIGH-6 | MEDIUM |

---

## 12. Independent ideas

Идеи, которых нет ни в плане, ни в коде.

### IDEA-1 — Bilingual Visual Intent (решает CRITICAL-1)

- **Проблема.** Русский intent не доходит до английских провайдеров; глоссарий
  покрывает одну тему.
- **Почему важно.** Это единственный дефект, блокирующий весь продукт.
- **Решение.** Визуальный план хранит для каждого intent **пару**: исходные
  термины и английские, с обязательным полем `translation_source`
  (`author_brief` / `glossary` / `model` / `unavailable`). Модель вызывается
  один раз на видео (не на сцену) — она получает список уникальных сущностей и
  возвращает английские эквиваленты. Fail-closed: неуверенный перевод помечается
  и не попадает в `must_include`.
- **Owner.** Расширяется существующий `src/assets/query_adapter.py` — у него уже
  есть `ProviderQuery.source` и статус `query_translation_required`. Новый
  владелец не нужен.
- **Benefit.** Поиск начинает работать для произвольной темы.
- **Complexity.** Средняя. **Risk.** Низкий: слой additive, offline-путь
  сохраняется как fallback, все существующие тесты продолжают работать на
  глоссарии.
- **Priority.** **1.**

### IDEA-2 — Scene Contract вместо распределённых доменных `if`

- **Проблема.** Доменное знание («косатка ≠ кит», «океан не соседствует с
  пустыней») зашито в шести модулях, включая safety gate (HIGH-1).
- **Почему важно.** Каждая новая ниша требует правки общего движка — прямая
  причина того, что новые темы работают хуже китов.
- **Решение.** Один декларативный объект на сцену: `subject`, `disambiguates_from`
  (косатка ≠ дельфин), `requires_evidence`, `conflicts_with`. Живёт в visual plan,
  заполняется планировщиком или автором. Движки читают его и не содержат
  доменных `if` вообще.
- **Owner.** Расширяется существующий `SemanticScene`
  ([models.py:16-40](src/assets/semantic_selection/models.py:16)) — у него уже
  есть `context`, `conflicting_context`, `must_not_include`. Полей достаточно;
  не хватает **дисциплины их использовать вместо inference**.
- **Benefit.** Новая ниша = новый конфиг, не новый код.
- **Complexity.** Средняя. **Risk.** Средний (трогает ranking).
- **Priority.** 3.

### IDEA-3 — Search Session как persisted-объект

- **Проблема.** План строит best-so-far (9A), ledger (10A), pagination (10B) и
  budget (10C) четырьмя отдельными слайсами с четырьмя schema-изменениями.
- **Почему важно.** Четыре persisted-изменения = четыре tripwire, четыре
  approval, четыре tolerant reader. Это дорого и создаёт риск расхождения.
- **Решение.** Один объект `search_session.json` на проект: попытки, best-so-far
  с обоснованием, курсоры пагинации, бюджет, причина остановки. Одна схема, один
  tolerant reader, один approval.
- **Owner.** Новый persisted owner — но взамен **четырёх** запланированных.
- **Benefit.** Меньше схем, меньше согласований, resume становится тривиальным.
- **Complexity.** Средняя. **Risk.** Низкий (additive рядом с
  `assets_manifest.json`).
- **Priority.** 2 — **это прямая замена PLAN-9A + 10A + 10B + 10C.**

### IDEA-4 — Один проход FFmpeg

- **Проблема.** Три поколения кодирования (MEDIUM-1).
- **Решение.** `filter_complex` с `concat` + `subtitles` в одном вызове.
- **Owner.** `src/news/final_renderer.py`, без новых модулей.
- **Benefit.** Лучше картинка, быстрее рендер, меньше временных файлов.
- **Complexity.** Низкая-средняя. **Risk.** Средний — рендер защищён
  synthetic-тестами, нужна характеризация до изменения.
- **Priority.** 5.

### IDEA-5 — Golden-topic регрессия вместо multi-topic gate в конце

- **Проблема.** PLAN-11 ставит проверку на нескольких темах в самый конец, после
  PLAN-9E и 10C.
- **Почему важно.** Дефекты CRITICAL-1 и CRITICAL-2 были бы найдены за один день,
  если бы существовал тест «прогнать три разные темы и посмотреть, сколько
  запросов реально ушло».
- **Решение.** Offline-фикстура: три темы из разных доменов, замоканные
  провайдеры, ассерт на **число фактически сформированных запросов** и на
  различность запросов между сценами. Ноль сети, ноль денег.
- **Owner.** `tests/`, новый модуль.
- **Benefit.** Дефект класса «продукт не работает для новой темы» перестаёт быть
  невидимым.
- **Complexity.** Низкая. **Risk.** Нулевой.
- **Priority.** **2 (совместно с IDEA-1) — самая дешёвая ценность в отчёте.**

### IDEA-6 — Явное разделение «шаблон» и «сгенерировано»

- **Проблема.** `legacy_template` подставляется молча, warning теряется.
- **Решение.** Результат несёт `content_origin`: `extracted_from_source` /
  `template_filler` / `model_written`. `strict` не рендерит `template_filler`.
- **Owner.** `ScriptResult.metadata` — поле уже есть.
- **Complexity.** Низкая. **Risk.** Низкий. **Priority.** 4.

---

## 13. Review of PROJECT_EXECUTION_PLAN

### Что план делает правильно

**Честно.** Это самый дисциплинированный плановый документ, который я видел в
репозитории такого размера. Конкретно верны:

1. **Разделение [HARD]/[ARCH]/[HINT]** ([план:253-262](docs/current/PROJECT_EXECUTION_PLAN.md:253))
   — правильное различение неоспариваемого и оспариваемого.
2. **«Выполнение инструкции не является выполнением задачи»**
   ([план:284-288](docs/current/PROJECT_EXECUTION_PLAN.md:284)) — точная
   формулировка настоящего режима отказа агентов.
3. **Класс findings «unmet objective / premature stop»**
   ([план:1157-1161](docs/current/PROJECT_EXECUTION_PLAN.md:1157)) — почти
   никто этого не делает, а это ловит самый частый сбой.
4. **Measurement policy** ([план:432-441](docs/current/PROJECT_EXECUTION_PLAN.md:432))
   — «число тестов не является нормой» правильно.
5. **Отказ реструктурировать `tests/`** ([план:416-424](docs/current/PROJECT_EXECUTION_PLAN.md:416))
   — большой diff, нулевая ценность. Верно.
6. **Отказ создавать `resources/` заранее** (OD-9) и восемь кандидатов в новые
   document owners, из которых не создаётся ни один
   ([план:2015-2025](docs/current/PROJECT_EXECUTION_PLAN.md:2015)) — правильная
   сдержанность.
7. **Отказ вводить второй словарь состояний завершённости**
   ([план:1831-1835](docs/current/PROJECT_EXECUTION_PLAN.md:1831)) — верно, и
   мой анализ `modes.py` это подтверждает независимо.
8. **`strict` как default, отказ ослаблять gates** — верно.
9. **Запрет второго clip pipeline** (OD-4) — верно.
10. **Reversible retirement с `git bundle`** — обоснованно, `git remote -v` пуст.

### Findings по плану

**PLAN-E1 — E: PLAN CONTAINS UNNECESSARY WORK. Governance перевешивает продукт.**

**FACT.** До первого продуктового изменения — девять шагов
([план:512-520](docs/current/PROJECT_EXECUTION_PLAN.md:512)). Из них PLAN-1D,
PLAN-2, PLAN-3, PLAN-4, PLAN-5, PLAN-6A, PLAN-6D, PLAN-6E, PLAN-1C′ — восемь не
трогают продукт (два чинят фикстуры, один меряет baseline, один делает runner,
четыре строят governance).

**FACT.** Объём governance: план 2047 строк + registry 684 = 2731 строка
процесса на репозиторий с одним активным workflow. Раздел «Agent Autonomy Model»
внутри плана ([план:245-377](docs/current/PROJECT_EXECUTION_PLAN.md:245)) сам
себя объявляет временным и подлежащим переносу в `AGENTS.md` в PLAN-6A — то есть
план содержит копию правил, которую сам планирует удалить.

**INFERENCE.** Владелец в ревизии 2 прямо сформулировал риск: «программа не
должна превратиться в бесконечное строительство governance»
([план:188-189](docs/current/PROJECT_EXECUTION_PLAN.md:188)). Ревизия 2
сократила цепочку с «весь PLAN-1 + 6B + 6C + 7 + 8» до девяти шагов — движение
правильное, но недостаточное: восемь из девяти по-прежнему не продукт.

**RECOMMENDATION.** Оставить в блокерах PLAN-9A только PLAN-1D (маршрутизация,
1 commit) и PLAN-2/PLAN-3 (красные тесты, 2 commit). PLAN-4/5/6A/6D/6E —
параллельные. Обоснование: reviewer и scope-control — это защита от **ошибок
исполнителя**, а не предусловие правильности задачи. Задача, поставленная не
туда (что и показывают CRITICAL-1…3), reviewer-ом не спасается.

---

**PLAN-E2 — C: PLAN MISUNDERSTANDS IT. Продуктовая рамка определена неверно.**

**FACT.** Раздел «Продуктовая рамка PLAN-9 и PLAN-10»
([план:1267-1301](docs/current/PROJECT_EXECUTION_PLAN.md:1267)) утверждает:
«Не является дырой — `src/assets/completion/`… Является дырой — всё выше по
потоку», и перечисляет: генерация запросов, semantic wiring, best-so-far,
ledger, pagination, adaptive budget.

**Соглашаюсь** с первой половиной: `completion/` действительно не дыра
(независимо подтверждено чтением `modes.py`).

**Не соглашаюсь** со второй. «Выше по потоку» останавливается на генерации
запросов, но выше неё есть ещё три ступени, каждая сломана сильнее:

```
тема → [CRITICAL-2: материала нет]
     → research → [regex, не исследование]
     → script → [шаблон из 6 фраз]
     → visual plan → [русские intents]
     → query adapter → [CRITICAL-1: 0 запросов]
     → провайдеры → [план начинает здесь]
     → completion → [работает]
```

План начинает с шестой ступени.

**RECOMMENDATION.** Дополнить таблицу «где именно дыра» тремя строками выше
`query_generator`: перевод (владелец — `query_adapter`), материал для topic
(владелец — research stage), происхождение сценария (владелец — script engine).

---

**PLAN-E3 — C: allowed zones PLAN-9B делают полное исправление нарушением scope.**

**FACT.** PLAN-9B разрешает только `query_generator.py` и его тесты
([план:1337-1338](docs/current/PROJECT_EXECUTION_PLAN.md:1337)), с целью «убрать
topic-specific hardcodes». Фактически хардкоды в шести модулях (HIGH-1),
включая `modes.py` — файл, который план объявляет неприкосновенным.

**INFERENCE.** Исполнитель PLAN-9B либо нарушит scope, либо закроет шаг, не
достигнув SUCCESS CRITERIA — то есть совершит ровно тот сбой («unmet objective /
premature stop»), ради которого пересмотрена модель автономии. План создаёт
условия для сбоя, который сам же учит ловить.

**Отмечу справедливости ради:** ревизия 2 уже поймала однажды такое
противоречие в этом же шаге ([план:1910-1918](docs/current/PROJECT_EXECUTION_PLAN.md:1910))
— «лестница PLAN-9B противоречила собственным разрешённым зонам». Механизм
самопроверки работает; он просто не был применён к hardcode-части.

---

**PLAN-E4 — F: BETTER APPROACH EXISTS. Четыре persisted-слайса вместо одного.**

PLAN-9A (best-so-far), PLAN-10A (ledger), PLAN-10B (pagination cursors),
PLAN-10C (budget) — четыре изменения persisted-состояния, каждое со своим
tripwire, tolerant reader и `full`-прогоном. Все четыре описывают состояние
одного поиска. См. IDEA-3.

---

**PLAN-E5 — C: PLAN-10D неверно ставит вопрос о локальной медиатеке.**

См. HIGH-2. Вопрос не «включить ли провайдера», а «какая из двух живых
реализаций каноническая».

---

**PLAN-E6 — B: PLAN-6B занижает subprocess-риск.**

См. HIGH-6: 12 модулей, не 7; и guard в тестовом пакете не может защитить
подпроцесс.

---

**PLAN-E7 — E: Knowledge Salvage Gate избыточен для части families.**

**FACT.** KSG обязателен для всех knowledge-bearing families
([план:677-724](docs/current/PROJECT_EXECUTION_PLAN.md:677)), включая
`legacy/` — 8 файлов, 424 строки, ноль callers.

**INFERENCE.** Формальная salvage-классификация восьми MVP-скриптов, у которых
уже есть полная история в Git, а retirement обратим через annotated tag +
bundle, — это процедура ради процедуры. Git **уже является** salvage-механизмом.

**RECOMMENDATION.** KSG применять там, где знание рискует потеряться: доменные
правила, prompts, edge cases (`size_comparison_engine` — да, обоснованно; OD-10
верен). Для `legacy/` достаточно tag + bundle + строка в `Retired`.

---

**PLAN-E8 — A, отмечаю согласие.** OD-1…OD-10, `Preserved runtime corpus`,
измерения C17–C33 — проверил выборочно (C17 caller-поиском, C19/C20/C21 через
`git ls-files -i -c` и `git status`, C18 через `pipeline.py:9`, C25 через
`pyproject.toml`, C31 через grep). **Все проверенные подтвердились.** Фактическая
база плана надёжна; расходится приоритизация, а не факты.

---

## 14. Proposed minimal PLAN delta

Минимальное изменение, а не переписывание. План остаётся, меняется порядок и
добавляются три шага.

### D1 — Сократить критический путь до трёх шагов

```
было:  1D → 2 → 3 → 4 → 5 → 6A → 6D → 6E → 1C′ → 9A
стало: 1D → 2 → 3 → ► P0 ◄
       параллельно: 4, 5, 6A, 6B, 6C, 6D, 6E, 7, 8, L*
```

Обоснование: PLAN-4/5/6* — защита от ошибок исполнителя; они не делают задачу
правильной. PLAN-2/3 остаются (красные тесты). PLAN-1D остаётся (1 commit,
иначе агент уходит в исторический master plan).

### D2 — Новый шаг **PLAN-P0 — Query Reachability Gate** (read-only, 0 USD)

- **цель:** измерить, сколько запросов **фактически** уходит в провайдеров для
  трёх тем из разных доменов.
- **зоны:** новый `tests/test_query_reachability.py`, отчёт в этом файле.
- **метод:** offline-фикстуры, замоканные провайдеры, счётчик
  `SceneQueryPlan.queries` со `status == STATUS_OK` и счётчик
  `untranslatable_providers`.
- **измеримый результат:** известно точное число отправленных запросов на тему;
  известно, сколько сцен ищут одной и той же строкой.
- **verification:** targeted, без сети.
- **почему первым:** это дешевле любого другого шага и определяет, верны ли
  CRITICAL-1 и весь остальной приоритет. Если я неправ — это выяснится за день.

### D3 — Новый шаг **PLAN-P1 — Bilingual Visual Intent** (см. IDEA-1)

- **зависимости:** PLAN-P0.
- **зоны:** `src/assets/query_adapter.py`, `src/content/visual_planning/`,
  targeted tests.
- **ограничение:** additive; глоссарий сохраняется как offline-fallback; модель —
  только через существующий approval gate; fail-closed при неуверенности.
- **exit condition:** метрика PLAN-P0 показывает ненулевой и различный набор
  запросов для всех трёх тем.

### D4 — Новый шаг **PLAN-P2 — честный topic-режим** (см. CRITICAL-2)

- Либо research с материалом, либо явный отказ вместо тихого шаблона.
- Минимум: `insufficient_source_material` становится блокирующим для `strict`.

### D5 — Слить PLAN-9A + 10A + 10B + 10C в один `search_session.json`

См. IDEA-3. Один persisted owner, один approval, один tolerant reader.

### D6 — Расширить allowed zones PLAN-9B

На весь `src/assets/semantic_selection/`, `query_adapter.GLOSSARY`,
`legacy_format.legacy_broad_query`. Отдельно разрешить снять два orca-литерала
из `modes.py:295-296` как исключение из неприкосновенности гейта.

### D7 — Переформулировать PLAN-10D

Не «включить ли `LocalLibraryStockProvider`», а «выбрать канонического владельца
доступа к медиатеке и удалить второго» (HIGH-2).

### D8 — Поправить факты в плане

- subprocess-модулей **12**, не 7 ([план:426-428](docs/current/PROJECT_EXECUTION_PLAN.md:426));
- дополнить таблицу «где дыра» тремя ступенями выше query generation (PLAN-E2).

### Чего делать НЕ надо

- не создавать третий плановый документ;
- не реструктурировать `tests/`;
- не переписывать `completion/`, `subtitles/`, `scene_timeline`, каталог;
- не создавать `resources/` заранее;
- не вводить второй словарь состояний;
- не откладывать продукт до идеального репозитория.

---

## 15. Top 10 recommendations by ROI

| # | Действие | Стоимость | Эффект | Ссылка |
|---|---|---|---|---|
| 1 | **Query Reachability Gate** — измерить число реально отправленных запросов на трёх темах | очень низкая | подтверждает или опровергает главный вывод отчёта за один день | D2 |
| 2 | **Bilingual Visual Intent** — перевод intent → язык провайдера | средняя | поиск начинает работать для произвольной темы | IDEA-1 |
| 3 | **Убрать `legacy_broad_query` из `alternative_queries`** | очень низкая | прекращается засорение каждой сцены строкой «nature science wildlife observation» | CRITICAL-1 |
| 4 | **Честный topic-режим** — не подставлять шаблон молча | низкая | пользователь перестаёт получать одинаковые видео | CRITICAL-2 |
| 5 | **Сократить критический путь до 1D → 2 → 3 → P0** | нулевая (правка плана) | продукт начинается на 6 шагов раньше | D1 |
| 6 | **Слить 9A+10A+10B+10C в `search_session.json`** | нулевая сейчас, экономит потом | 1 схема и 1 approval вместо 4 | IDEA-3 |
| 7 | **Убрать двойную оркестрацию стадий** | средняя | исчезает класс багов resume | CRITICAL-4 |
| 8 | **Выбрать одного владельца локальной медиатеки** | низкая | устраняется расхождение в правилах прав | HIGH-2 |
| 9 | **Один проход FFmpeg вместо трёх** | средняя | заметно лучше картинка, быстрее рендер | IDEA-4 |
| 10 | **Расширить allowed zones PLAN-9B на все 6 модулей** | нулевая (правка плана) | исполнитель сможет завершить задачу, не нарушая scope | D6 |

---

## 16. What I would do next if this were my project

**День 1 — проверить главный вывод.**
Написать `tests/test_query_reachability.py`: три темы («вороны и лица»,
«солнечная электростанция», «строительство канала» — как раз три reference
domains из PLAN-11), замоканные провайдеры, счётчик реально сформированных
запросов. Ноль сети, ноль денег. Если запросов ноль — весь остальной план
подождёт. Если я неправ — я узнаю об этом дешевле всех.

**Дни 2–4 — починить вход.**
Перевод intent → английский (IDEA-1) и удаление `legacy_broad_query` из
альтернатив. Ничего больше. Замерить тем же тестом из дня 1.

**День 5 — честный topic.**
`insufficient_source_material` перестаёт быть warning для `strict`.
Пользователь узнаёт, что материала нет, вместо шести шаблонных фраз.

**Дни 6–8 — одно живое видео на новой теме.**
Тема, для которой в репозитории нет ни одного хардкода. Пройти путь до конца,
посмотреть результат глазами. Записать, что именно плохо. **Это заменяет
PLAN-11 как evidence gate и даёт его на две недели раньше.**

**Дальше — то, что скажет это видео.** Не то, что записано в плане сегодня.

Параллельно, не блокируя: PLAN-L (ретайр legacy — согласен полностью),
PLAN-6A/6D/6E (governance), PLAN-7 (документация).

**И последнее.** План ошибается в приоритете, но не в фактах и не в ценностях.
Его правила про rights, approval gates, tolerant readers, честный каталог и
запрет второго владельца — правильные, и их надо сохранить целиком. Проблема не
в том, что план слишком строг. Проблема в том, что он строг к правильному
исполнению **не той задачи**. Самое ценное, что можно сделать с этим планом, —
не ослабить его, а **направить на настоящее узкое место**.

---

## Проверки после создания отчёта

```
git diff --check          → выполнено, вывод пуст
git status --short --branch
## governance-reset
?? docs/audits/INDEPENDENT_REPOSITORY_REVIEW_2026-07-31.md
?? output/
```

Изменён только этот файл. Commit не создавался. `current_checkpoint` не
запускался. Canonical docs не изменялись.
