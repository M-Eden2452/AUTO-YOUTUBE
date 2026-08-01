---
status: active
plan_revision: 2.1
created_at: 2026-07-30
updated_at: 2026-08-01
baseline_head: fe2df5b
working_branch: governance-reset
owner_decisions_date: 2026-07-31
current_checkpoint: PLAN-1D-routing
next_exact_action: git status --short --branch
source_paths:
  - AGENTS.md
  - pyproject.toml
  - requirements.txt
  - requirements.lock
  - .gitignore
  - docs/current/CURRENT_STATE.md
  - docs/current/START_HERE.md
  - docs/current/SYSTEM_MAP.md
  - docs/current/ARCHITECTURE_BOUNDARY_MAP.md
  - docs/current/CLEANUP_REGISTRY.md
  - docs/handoff/PROJECT_RESCUE_MASTER_PLAN.md
  - src/production_catalog
  - src/config_resolver
  - src/assets
  - src/news
  - src/providers
  - src/audio
  - src/subtitles
  - anime_factory
  - apps
  - tests
  - tools/qa
---

# AI-YouTube Project Execution Plan

Временный orchestration-документ на период согласованной программы работ.
Он задаёт **порядок выполнения** и ничего больше. Он не заменяет `AGENTS.md`,
`CURRENT_STATE.md`, `PRODUCT_PLAN.md` и `CLEANUP_REGISTRY.md` и не является
архитектурной или продуктовой спецификацией.

После полного завершения программы этот файл удаляется из `docs/current/`
и сохраняется одним архивным snapshot — см. «Completion and archive policy».

## Current checkpoint

- **Текущий шаг:** PLAN-1D-routing, не начат.
- **Выполнено:** PLAN-0 — создан этот план; ветка `governance-reset`.
  STEP 0 — архитектурная ревизия перенесена в этот файл и в
  `CLEANUP_REGISTRY.md`. **PLAN-REV-2.1** — ревизия 2.1 канонизирована
  docs-only слайсом; production-код, tests, схемы и public CLI не менялись.
- **Зелёные проверки:** `tools.qa.check_agent_docs`.
- **Почему checkpoint сместился с PLAN-1A.** Это **не** признак выполненной
  работы. Ревизия 2 разделила монолитный PLAN-1 на три capability gates
  (1A, 1B, 1C′) и выделила routing-фикс 1D как первый самостоятельный шаг.
  Ни один под-slice PLAN-1 не выполнен. `baseline_head` остаётся `fe2df5b`:
  нового baseline run не было. **Ревизия 2.1 checkpoint не сдвинула:**
  следующий шаг по-прежнему PLAN-1D-routing.
- **Заблокировано (модель ревизии 2.1 — risk-based, не линейная цепочка):**
  - **PLAN-9B-0 и PLAN-9B-1** — первый product-этап программы — блокируются
    только `PLAN-1D-routing → PLAN-2 → PLAN-3 → PLAN-4`;
  - **PLAN-6D** — blocker **первого multi-owner implementation slice**
    (PLAN-9B-2);
  - **PLAN-6E** — blocker **первого destructive retirement / high-risk
    shared-contract slice** (PLAN-9B-2, PLAN-9B-3, PLAN-9B-5b), плюс
    **обязателен для PLAN-9A** (persisted-bytes boundary) и **для PLAN-9C**
    (semantic decision boundary);
  - **PLAN-9A** — блокируется `PLAN-9B-2` + `PLAN-1C′`, дополнительно требует
    `PLAN-6E`;
  - **PLAN-9C** — блокируется `PLAN-1C′` + `PLAN-6E`;
  - **PLAN-5, PLAN-6A, PLAN-6B, PLAN-6C, PLAN-7, PLAN-8, PLAN-1A, PLAN-1B,
    PLAN-1C′, PLAN-12\*, PLAN-13\*, PLAN-14\* и PLAN-L** — параллельны и
    **не блокируют первый product fix**;
  - PLAN-11 M2 — до подтверждения бюджета.
- **Следующая точная команда:** `git status --short --branch`
- **После проверки Git выполнить:** PLAN-1D-routing.
- **Что нельзя повторять:**
  - закрывать шаг без зелёной обязательной проверки;
  - записывать число тестов, длительность прогона или accuracy как норму;
  - менять production-код без закрытого capability gate изменяемой области;
  - создавать третий плановый документ;
  - архивировать `PROJECT_RESCUE_MASTER_PLAN.md` или
    `ARCHITECTURE_BOUNDARY_MAP.md` до PLAN-12;
  - снимать с Git `docs/implementation` целым семейством;
  - заявлять о защите, которая существует только в документах;
  - выполнять destructive retirement knowledge-bearing family до Knowledge
    Salvage Gate (PLAN-L0);
  - требовать KSG для disposable runtime/media: их цепочка — PLAN-14D → 14E;
  - считать «нет caller» доказательством отсутствия ценности;
  - **создавать PLAN-P0 / «Content & Query Reachability Gate»**: evidence уже
    получено двумя deep-dive, повторный диагностический этап запрещён (OD-11);
  - **возвращать опровергнутые механизмы** — см. «Ревизия 2.1: опровергнутые
    формулировки».

## Шаблон задания для нового чата

Историю предыдущих чатов пересказывать не нужно. Достаточно отправить:

```text
Работай в G:\Projects\AI-YouTube.
Сначала выполни git status --short --branch, git log -5 --oneline и
git diff --stat. Прочитай AGENTS.md и полностью
docs/current/PROJECT_EXECUTION_PLAN.md. Исторический
docs/handoff/PROJECT_RESCUE_MASTER_PLAN.md читай как context согласно AGENTS.md,
но не обновляй как current plan.

Продолжи только current_checkpoint активного execution plan и выполни один
bounded sub-slice. Перед изменением проверь фактические callers, tests,
contracts и существующих owners; не создавай дублирующую реализацию.
Запусти только required/targeted проверки этого slice; full offline suite —
только когда его требует план или меняется shared boundary.

Не выполняй сеть, provider download/search, Vision, TTS, платные вызовы,
реальный render, удаление/перенос runtime или user data без моего отдельного
разрешения. После зелёных проверок обнови checkpoint/evidence в активном плане,
покажи diff summary и закоммить slice отдельным commit с
Plan-Step: <ID>. В конце сообщи результат, проверки, commit и следующий
точный checkpoint.
```

Если задача только на review, в последнем абзаце следует заменить
«выполни/закоммить slice» на «ничего не меняй и дай вывод».

## Source-of-truth precedence

1. Git и фактический код.
2. Реальные tests и artifacts.
3. **Этот файл — порядок выполнения текущей программы.**
4. `CURRENT_STATE.md` — фактическое состояние продукта.
5. `PRODUCT_PLAN.md` — продуктовая цель и evidence (создаётся в PLAN-8).
6. `CLEANUP_REGISTRY.md` — переходные пути, owners и exit conditions.
7. `docs/adr/` — зафиксированные долговечные решения.
8. Historical plans и audits — только как context.

**Отношение к `docs/handoff/PROJECT_RESCUE_MASTER_PLAN.md`.** Master plan
остаётся **историческим исходным документом** и источником данных для PLAN-1.
Его разделы «Что делать первым» и «Текущий handoff» отражают состояние на
2026-07-29 и **не являются** текущим порядком работ: порядок задаёт этот файл.
Master plan не обновляется как current plan и не архивируется до PLAN-12C.
Противоречие между двумя документами разрешается в пользу этого файла
только по вопросу порядка выполнения; по фактам архитектуры приоритет у кода.

Если код или tests противоречат этому плану, агент обязан остановиться,
проверить evidence и обновить план после решения владельца.

**Временная маршрутизация агентов.** После ревизии 2 документы больше **не**
указывают один и тот же следующий шаг: этот файл указывает PLAN-1D-routing, а
`AGENTS.md` и `START_HERE.md` по-прежнему направляют задачу в master plan, то
есть в 9B-C01. Поэтому PLAN-1D выполняется первым: он добавляет в `AGENTS.md`
и `START_HERE.md` короткую ссылку на активный execution plan. До этой ссылки
checkpoint нельзя переводить на PLAN-2: иначе новый агент, буквально выполнив
текущий `AGENTS.md`, снова начнёт C01.

## Locked owner decisions

Подтверждено владельцем на 2026-07-30:

1. Ближайший продуктовый приоритет — визуальная релевантность и завершённость
   Shorts.
2. Проект должен представлять несколько понятных инструментов поверх общего
   переиспользуемого ядра.
3. `content_creator` — основной инструмент создания новых видео; longform и
   documentary развиваются как workflows/templates внутри него, а не как третья
   платформа.
4. `video_repurposer` — подтверждённая долгосрочная часть продукта: нарезка
   стримов, подкастов, мультфильмов, фильмов и локальных длинных видео.
   Развивается из существующего Anime Factory. **Второй clip pipeline с нуля
   запрещён.**
5. Отсутствие `video_repurposer`-проектов сейчас не доказывает отсутствие
   потребности: capability выключена. Приоритетом он при этом не является и
   остаётся disabled до migration и product evidence.
6. Runtime Workspace остаётся целевой архитектурой: код и пользовательские
   данные должны быть физически разделены. Физическая runtime migration сейчас
   отложена; `WorkspacePaths`, tolerant legacy reads и цель
   `copy → verify → switch` сохраняются.
7. Внешний `AI-YouTube-System` допустим только как необязательный
   пользовательский mirror и не является source of truth.
8. Обязательное дерево `core/services/infrastructure` отменено. Структура
   остаётся настолько плоской, насколько позволяет продукт; новый уровень
   каталогов создаётся только при доказанной границе, нескольких реальных
   callers и измеримой пользе.
9. Для каждой capability не должно быть двух реализаций, способных разойтись в
   поведении. Физическое расположение кода само по себе дефектом не является;
   переносить рабочие файлы ради соответствия дереву запрещено.
10. Канонический пользовательский путь — `python -m ai_youtube`. Старые
    entrypoints (`python -m src.content_creation.cli`, `python pipeline.py`,
    `python -m apps.*`) не являются постоянным пользовательским контрактом.
    **Изменено ревизией 2:** формулировка «сначала PLAN-1» отменена. Каждый
    entrypoint удаляется после **своего** capability gate; для legacy-семейства
    это PLAN-L1, а не глобальный inventory.
11. Владелец подтвердил отсутствие личных `.bat`/`.cmd`/`.ps1`, ярлыков,
    Windows Tasks и IDE Run Configurations, которые нужно сохранять ради старых
    команд. Поиск по компьютеру вне репозитория запрещён.
12. R1–R12 становятся новой governance model (внедрение — PLAN-6). Отдельный
    ADR про переход на новые правила не создаётся.
13. Платные и сетевые операции требуют отдельного разрешения на конкретное
    действие. Для M1: 0 USD и ноль новых платных Vision-вызовов. Бюджет M2 —
    `TBD`, подтверждается отдельно перед первым реальным платным запуском.

## Owner decisions ревизии 2 (2026-07-31)

Ревизия 2 пересмотрела план под явную позицию владельца: существующая
зависимость, существующий owner и существующая архитектура **не являются
доказательством правильности**; тестовое runtime-медиа ценности не имеет;
правила ограничивают исполнение, но не мышление; программа не должна
превратиться в бесконечное строительство governance.

| # | Решение |
|---|---|
| **OD-1** | `channels/{psychology,quotes,survival,size_comparison}` и `content/` не сохраняются как активные workflows. Ретайр вместе с legacy допускается **только после Knowledge Salvage Gate** |
| **OD-2** | `apps/news_to_short` как отдельный CLI не сохраняется. Если его флаги полностью покрыты каноническим CLI — удалить; уникальную возможность сначала перенести в `content_creator`, затем удалить |
| **OD-3** | `assets/voice_samples` — disposable test/runtime media, в source repo не хранится. Если конкретный активный voice profile действительно требует sample — перенести минимально необходимый во внешний Workspace с provenance, иначе удалить |
| **OD-4** | Бюджет M2 остаётся `TBD` и ничего не блокирует |
| **OD-5** | Вся поддерживаемая human/agent-проза со временем становится преимущественно русской, **включая body существующих ADR**. Инкрементально, без одного mass-diff; не блокирует product work |
| **OD-6** | Locked decisions 8 и 9 больше не запрещают пересмотр `config`/`channels`/`assets`/`resources`. Пересмотр — только после классификации, не ради эстетики |
| **OD-7** | **MOSS-TTS не нужен продукту.** Не реинтегрировать как активный TTS provider. KSG → caller audit → удалить `MOSS_TTS_Nano/` и `src/tts_providers/`. Не сохранять 56k файлов «на всякий случай»; vendor repo в `Workspace/models` не переносить |
| **OD-8** | Live-eval — evaluation resource. **`docs/` — неправильный target owner.** Fixture/evidence сохраняется, caller позже переводится на утверждённого owner. `resources/evaluation/` — **только candidate path**; физический target `DEFER` до PLAN-13 |
| **OD-9** | Top-level `resources/` — `DEFER` до PLAN-13, заранее **не создавать**. Сначала классифицировать `channels` · `schemas` · reusable templates · evaluation resources · versioned assets/config, затем решить, уменьшает ли `resources/` число owners |
| **OD-10** | `size_comparison_engine`: L0 сохраняет reusable algorithm, domain knowledge, visual logic, edge cases и полезные тесты. **Capability внутри L3 не мигрируется.** Если формат понадобится — отдельный будущий product slice на новом canonical core |

## Owner decisions ревизии 2.1 (2026-07-31)

Ревизия 2.1 — **перестановка и переадресация**, а не переписывание. Ни один
существующий PLAN-ID не удалён. Источники: `docs/audits/`
`CRITICAL_INPUT_SEARCH_DEEP_DIVE_2026-07-31.md`,
`PROJECT_EXECUTION_PLAN_REVISION_2_1_PROPOSAL_2026-07-31.md` и
`SECONDARY_ARCHITECTURE_FINDINGS_DEEP_DIVE_2026-07-31.md`. **При конфликте
Secondary Deep Dive исправляет Proposal 2.1**; исправленные формулировки
записаны ниже и в разделе «Ревизия 2.1: опровергнутые формулировки».

| # | Решение |
|---|---|
| **OD-11** | **PLAN-P0 (Content & Query Reachability Gate) не создаётся.** Evidence уже получено двумя deep-dive offline, без сети и денег. Тесты T1–T11 из `CRITICAL_INPUT_SEARCH_DEEP_DIVE` становятся regression/product-тестами **внутри соответствующих PLAN-9B слайсов**, а не отдельным диагностическим этапом |
| **OD-12** | CRITICAL-1 — текущий главный product defect в **исправленной** формулировке: не «ноль запросов», а «ложные / чрезмерно общие / пропущенные запросы, и единственный канал доставки provider-ready английского запроса — hardcode на одну тему» |
| **OD-13** | **Не создавать** `TranslatorService`, `SearchEngine`, `QueryOrchestrator` и второй query pipeline. Переиспользуются `VisualBrief`, `SceneVisualPlan`/`VisualSearchIntent`, `build_scene_queries`/`build_slot_queries`, `ProviderQuery`, provider contracts |
| **OD-14** | `src/assets/query_adapter.py` — фактическая canonical boundary, через которую remote-запросы доходят до провайдеров. Allowed zone PLAN-9B исправлена на неё |
| **OD-15** | **PLAN-9B выполняется до PLAN-9A.** Best-so-far persistence бессмысленна до появления provider-ready кандидатов. PLAN-9A не удаляется и состав не меняет |
| **OD-16** | Метод provider-language adaptation **не фиксируется заранее**: deterministic normalization/lexicon, prepared `VisualBrief`, model-assisted adaptation или комбинация. Выбор — по semantic correctness, fail-closed, testability, cost, network/paid boundary и reuse существующих owners. **Model/network вариант требует отдельного owner approval** |
| **OD-17** | CRITICAL-2 исправляется сейчас, **без AI research**. Idea generation, web/AI research, AI script writing, autonomous creative direction — **DEFER**: без PLAN, package, interface и placeholder |
| **OD-18** | Для factual strict workflow `topic` = **intent, не source material**. Silent fallback `topic → insufficient material → generic template → factual production success` запрещён. `LegacyTemplateScriptProvider` **не удаляется**: допустим только в явно выбранном `template`/`demo`/`test`/`draft`. `content_origin` **не создаётся** |
| **OD-19** | Capability `apps/news_to_short --text/--text-file` **мигрирует** в канонический `python -m ai_youtube` + content_creation request path. **Разделено (D-1):** миграция — PLAN-9B-5a (additive), retirement — PLAN-9B-5b. **Исправлено 2026-08-01:** это не единственная возможность wrapper'а — перед retirement обязателен полный **capability parity check** (см. PLAN-9B-5b), минимум `--text`/`--text-file` **и** `--assets` |
| **OD-20** | CRITICAL-3 («в content path мало AI») **не является** current defect и отдельного этапа не получает. Future-proofing rule: downstream pipeline не должен предполагать, что script создан внутри AI-YouTube; prepared external content — first-class input |
| **OD-21** | CRITICAL-4 (double orchestration) сохраняется как architecture debt, **не** prerequisite CRITICAL-1/2. **Исправлено Secondary Deep Dive:** severity **MEDIUM**, не HIGH; finding разделяется на contract defect и возможную позднюю конвергенцию (D-3) |
| **OD-22** | Порядок semantic/Vision: provider-ready query → candidates → semantic/Vision → rank/select. PLAN-9C сохраняется, новый semantic stack не создаётся |
| **OD-23** | Anime Factory — **не** disposable legacy: это source implementation будущего `video_repurposer`. Порядок: Content Creator stable → UI Content Creator → deep audit Anime Factory → KEEP/MIGRATE/REWRITE/SHARE/DELETE → Video Repurposer → его UI. Runtime внутри source repo остаётся дефектом, owner — PLAN-14 |
| **OD-24** | `search_session.json` как отдельный persisted owner **не утверждается**. Сначала проверить `job.json`, asset manifest, project state, completion/resume state. Если существующего owner можно расширить — новый persisted файл запрещён |
| **OD-25** | **Multi-topic regression начинается раньше PLAN-11** и выполняется после каждого существенного product slice, где это релевантно: минимум по одной репрезентативной теме из разных классов (animals/wildlife · energy/technology · geography/infrastructure). PLAN-11 остаётся финальным product evidence gate, но **не первой** multi-topic проверкой |
| **OD-26** | Governance не задерживает дешёвое product-исправление без конкретной защищаемой boundary, **но** safety/reviewer/persisted/paid protections обязаны быть готовы **до своей risk boundary**. Каждый оставшийся blocker имеет однострочное обоснование |
| **D-1** | **ДА** — 9B-5 разделяется на **9B-5a** (additive source-text canonical input; public CLI surface + owner approval; не destructive) и **9B-5b** (retirement `apps/news_to_short`; требует PLAN-6D + PLAN-6E + reversible retirement) |
| **D-2** | **ДА** — PLAN-10B **не является** owner provider-registry convergence; сама гипотеза «пять расходящихся реестров надо свести» **опровергнута**. PLAN-10B возвращается к своей реальной ответственности: pagination / provider exhaustion / provider contract behavior |
| **D-3** | **ДА** — double orchestration finding разделяется на точный idempotency contract defect (owner: ADR 0006 / `src/news/pipeline.py`) и возможную позднюю orchestration convergence (owner: PLAN-13B, только если после исправления contract остаётся архитектурная необходимость). Severity **MEDIUM** |
| **E-13** | CRITICAL-2 остаётся **bounded sub-slices существующего PLAN-9B**. Новый top-level PLAN-ID не создаётся |
| **1C′/6E** | Прямая зависимость `PLAN-1C′ → PLAN-6E` **снята**. Одновременно **явно установлено**: `PLAN-9A` требует `PLAN-6E` (persisted-state boundary), `PLAN-9C` требует `PLAN-6E` (semantic decision boundary). Транзитивная зависимость через PLAN-9B-2 доказательством не считается |
| **export** | PLAN-11 — **evidence gate**, обязанный ловить ложные product capabilities. Implementation owner — будущий bounded `production_catalog` slice. Нового PLAN-ID не создаётся |
| **ffmpeg** | PLAN-8 — **roadmap owner** product-quality item. Implementation owner — будущий bounded renderer slice с characterization первым. Нового PLAN-ID не создаётся |
| **subprocess** | Архитектурное решение по subprocess network kill-switch **сейчас не принимается**: механизм и owner остаются implementation-time evidence/owner decision. **PLAN-6B остаётся report/measurement owner в своей текущей границе** |

### Ревизия 2.1: опровергнутые формулировки

Эти утверждения **опровергнуты** контролируемыми offline-пробами Secondary Deep
Dive. Возвращать их в план, registry, задания и commit-сообщения запрещено.

| Опровергнутая формулировка | Что верно на самом деле |
|---|---|
| «semantic-слой по построению не может влиять на selection»; «`_selection_fingerprint` делает неизменность отбора инвариантом сервиса» | metadata-semantic слой **уже** ranks / rejects / blocks и **может сменить выбранный asset** — доказано synthetic-пробой. `_selection_fingerprint` — защитная самопроверка, а не вето. Дефект — в том, что платный Vision пишет результат **поздно** в review-манифест и не подаёт evidence в decision layer до отбора |
| «два конкурирующих orchestration owner»; «ровно 7 pipeline calls»; «есть риск повторного платного TTS» | ADR 0009 **намеренно** разделяет application orchestration и news pipeline ownership. Вызовов **4–7** в зависимости от режима. Реальный дефект — explicit `stage=` path отключает output-validated idempotency ADR 0006 условием `and not stage` (`src/news/pipeline.py`). Batch-режим idempotency соблюдает. Повторного платного TTS аудит **не обнаружил**: несколько независимых guard'ов плюс существующие тесты |
| «три независимых LocalLibrary implementation»; «#1 допускает `RIGHTS_REFERENCE_ONLY`, поэтому мягче»; «более строгая реализация — та, которую никто не вызывает» | Один `media_index`, один rights-authority `apply_policy_to_candidate`, **два** matcher'а, несколько consumers/wrappers; legacy path #3 использует **ту же** `media_library.search_local_assets`, что и #1. Доказанных расхождений live-путей ровно **два**: missing `provenance` и `review_required=True`. Обратных расхождений — ноль. Аргумент про `RIGHTS_REFERENCE_ONLY` опровергнут: значение перезаписывается политикой |
| «пять расходящихся provider registries, всё свести к `providers/registry`»; «owner конвергенции — PLAN-10B» | Это **разные legitimate facts**, а не дубли: actual constructed providers · provider capabilities · fallback language info · source-class priority · diagnostics inventory · availability. `ProviderCapabilities.query_languages` **уже** имеет приоритет над fallback-таблицей. Остаточный cleanup: declaration mismatch `local_library` → PLAN-10D; вестигиальный `DEFAULT_PROVIDER_ORDER` и осиротевший `unsplash` → opportunistic cleanup. Отдельный PLAN-ID не создаётся |
| «сегменты crf 23 → **конкатенация** crf 20 → субтитры crf 21»; «single-pass — простой fix» | Нормальный путь: segment encode CRF 23 → concat **`-c:v copy`** (не перекодирует) → audio + exact-duration encode CRF 20 → ASS subtitle encode CRF 21 → copies. Три lossy generations возникают **при audio + ASS subtitles**. CRF 20 имеет документированную причину (exact-duration/tpad behavior). Полный single-pass filtergraph — отдельное более крупное исследование |
| «PLAN-5 обязателен до PLAN-9B-5 и PLAN-9B-3» | Targeted, full и все три smoke-команды исполнимы **сегодня** существующими командами. PLAN-5 улучшает uniform runner UX/reproducibility, но техническим blocker product fixes не является |
| «`legacy_broad_query` — единственное, что гарантированно доходит до провайдера» | Не доходит ни разу: `source_is_latin` — свойство всего набора, поэтому русский `primary_query` выбрасывает английский alternative вместе с собой |
| «topic-hardcode сосредоточен в `semantic_selection/query_generator.py`» | Этот модуль **не участвует** в формировании remote-запросов. Canonical boundary — `src/assets/query_adapter.py`; главный носитель hardcode — `src/news/script_generator.py` |
| «канонический CLI не имеет source-text входа»; «`--text`/`--text-file` — единственная уникальная capability `apps/news_to_short`» (**опровергнуто 2026-08-01**) | `create --pasted-script` / `--script-file` при default/legacy unspecified `content_input_mode` уже проводят подготовленный текст в тот же downstream, поэтому PLAN-9B-5a делает вход **явным**, а не создаёт движок. Вторая возможность wrapper'а — `--assets` → `NewsJob.user_assets`, у которой канонического аналога нет; она не может быть молча потеряна при retirement |

### Открытые вопросы ревизии 2.1 (закрываются в момент implementation)

**Закрыты и в списке unresolved больше не значатся:**

- **E-2 — ЗАКРЫТ.** `ProviderQuery.source` — существующее свободное строковое
  telemetry-поле; это **не** schema-level change, tolerant reader не нужен,
  persisted-bytes tripwire не срабатывает. Байты `assets_manifest.json` при этом
  меняются, поэтому characterization PLAN-9B-0 обязан зафиксировать текущее
  содержимое `query_plan` до правки.
- **E-5 — ЗАКРЫТ ОТРИЦАТЕЛЬНО.** PLAN-10B не является owner provider-registry
  convergence, потому что сама registry-convergence гипотеза опровергнута.
- **E-7 — ЗАКРЫТ.** Rights/provenance comparison трёх local-library путей
  выполнен Secondary Deep Dive: ровно два доказанных расхождения.

**Остаются открытыми, каждый — внутри своего слайса, не отдельным аудитом:**

| Вопрос | Кто закрывает |
|---|---|
| полный inventory topic-hardcodes (**PROVISIONAL**, число файлов не invariant) | PLAN-9B-2 |
| миграция всех callers `semantic_selection/query_generator` | PLAN-9B-3 |
| backward compatibility CRITICAL-2 fix со старыми persisted проектами | PLAN-9B-4 |
| метод provider-language adaptation (OD-16) | PLAN-9B-1 |
| механизм и owner subprocess network kill-switch | владелец / PLAN-6B / PLAN-5 |
| public behavior `resume`/`force`/`stop-stage` до крупной orchestration convergence | PLAN-13B |
| реальный ущерб от нескольких FFmpeg-кодирований (никто не рендерил) | будущий renderer slice |
| осуществимость слияния audio/duration encode + subtitle burn в один encode | тот же слайс |
| регистрировать ли `local_library` как `StockProvider` после PLAN-10D | PLAN-10D |
| зелёность baseline | PLAN-4 |

### Сильные foundations — сохраняются

Ревизия 2.1 **не** превращает работающие foundations в кандидатов на rewrite.
Второй competing owner для этих ответственностей не создаётся:

`src/assets/completion/` как canonical completion/readiness owner ·
rights / provenance / `must_avoid` / misleading / conflict gates ·
`VisualBrief` как существующий transport contract ·
`ScriptValidationResult` + `script_metadata` · `DeterministicScriptProvider` ·
`LegacyTemplateScriptProvider` для explicit `legacy`/`template`/`demo`/`test`/
`draft` · subtitles foundation · `src/audio/scene_timeline.py` ·
production catalog foundation · tolerant project readers · final renderer до
отдельного renderer-слайса · `tests/network_guard.py` ·
`route_providers` / `scene_strategy`, пока evidence не докажет их дефект.

**Hard constraints не ослабляются ревизией 2.1:** factual truth · rights ·
provenance · `must_avoid` · misleading/conflict · paid approval остаются
`[HARD]` и heuristics не становятся.

### Никакой новой архитектуры из аудита

Audit evidence обязано **уменьшать** архитектуру, а не порождать абстракции.
Не создавать: `TranslatorService` · `SearchEngine` · `QueryOrchestrator` ·
`search_session.json` · `content_origin` · новый semantic stack · четвёртый
LocalLibrary path · второй completion-state vocabulary · placeholder-пакеты и
speculative interfaces под future AI.

## Safety boundaries

Действуют правила R1–R3 из `AGENTS.md`; здесь они не дублируются.
Дополнительно на период этой программы:

- сеть, provider search, download, Vision, TTS, render и платные API не
  выполняются без отдельного разрешения на конкретное действие;
- synthetic render в tempfile разрешён и обязателен для renderer contract
  tests; реальный render пользовательского проекта — только по необходимости и
  с разрешением;
- в `master` не сливать и ничего не публиковать без отдельного разрешения;
- destructive retirement **knowledge-bearing family** (source, workflow, config,
  prompts, templates, tests, уникальное docs/evidence) выполняется только после
  Knowledge Salvage Gate (PLAN-L0) и с обратимым retirement-механизмом;
- удаление **disposable runtime/media/cache** идёт цепочкой PLAN-14D → PLAN-14E
  и KSG не требует; его gate — классификация, `Preserved runtime corpus`,
  проверенный абсолютный путь и owner approval на конкретное действие.

**Изменено ревизией 2.** Безусловная неприкосновенность `projects/`, `assets/`,
`manual_assets/`, `music/`, `outputs/` снята: владелец объявил тестовое
runtime-медиа disposable. Вместо неё действует точный список сохраняемого.

**Preserved runtime corpus — сохраняется обязательно:**

- отобранный **минимальный representative** набор JSON/SRT/ASS манифестов
  проектов (состав определяет PLAN-14D, см. registry C32);
- `assets/library/metadata/media_index.json` — provenance и rights локальной
  медиатеки;
- versioned SVG в `manual_assets/**`;
- versioned config `config/` (кроме умирающего `video_style.json`) и активные
  `channels/nature_science_news_ru`, `channels/nature_pulse`;
- live-eval dataset/results/frames как evaluation resource (переезжает по OD-8).

**Disposable — удаляется на runtime reset:** медиа во всех перечисленных
каталогах (`*.mp4`, `*.mov`, `*.wav`, `*.mp3`, `*.png`, `*.jpg`, `*.jpeg`),
кэши, `project_solar_vs_nuclear/`, `assets/voice_samples` (OD-3),
`MOSS_TTS_Nano/` (OD-7).

Ни одно удаление не выполняется вне своего bounded slice и без явного
подтверждения абсолютного пути.

## Agent Autonomy Model

Действует на период этой программы. Канонический владелец правил после PLAN-6A —
`AGENTS.md`; здесь модель зафиксирована, чтобы она действовала **до** 6A, и
после 6A этот раздел сворачивается до ссылки. Отдельный документ не создаётся.

### Классы правил

```
[HARD]   нарушать нельзя. Если правило можно enforce технически —
         оно обязано быть enforced, а не только записано.
[ARCH]   архитектурная граница. Пересматривается через evidence,
         ADR и independent review. Оспаривать — можно и нужно.
[HINT]   рекомендуемый способ. Если он не достигает SUCCESS CRITERIA,
         агент обязан искать другой и назвать причину смены.

Правило без класса читается как [HINT].
```

**[HARD].** Secrets · платные и сетевые вызовы без разрешения на конкретное
действие · destructive Git · удаление реальных user data · rights, `must_avoid`,
misleading и conflict gates · публикация · изменение persisted contract без
tolerant reader и migration · второй одновременно живущий canonical owner ·
**доказать canonical owner, callers, persisted contracts, дубли и тесты
изменяемой capability до её изменения**.

**[ARCH].** Канонический CLI `python -m ai_youtube` · два engine (ADR 0016) ·
один owner на capability · направление зависимостей · граница workspace
(ADR 0002) · владение persisted schema · `strict` как default completion mode ·
tolerant readers · размещение пакетов и структура корня.

**[HINT].** Приоритет провайдеров · число и виды запросов · пороги
`minimum_confidence`/`hard_reject_confidence` · `analyse_and_report` и
`semantic_rerank_enabled: false` · предпочтительный тип визуала · порядок
внутренних действий · «только targeted tests» · рекомендуемый размер модуля ·
лимит длины `AGENTS.md`.

### Goal > prescribed method

```
Выполнение инструкции не является выполнением задачи.
Если CURRENT APPROACH не достигает SUCCESS CRITERIA, задача не закрыта.
Агент переходит к поиску альтернативы внутри [HARD] и своих decision rights,
а не сообщает об успехе на основании соблюдённой процедуры.
```

Плохой quality score сам по себе **не** является причиной остановки. Допустимые
причины остановки перечислены в PLAN-10A.

### Decision rights — три tripwire

Owner approval требуется, когда изменение затрагивает:

1. **persisted bytes** — schema, поле манифеста, layout файлов, имя каталога
   проекта (дополнительно обязателен tolerant reader);
2. **внешне наблюдаемую поверхность** — имя команды CLI, флаг, exit code, ключ
   JSON-вывода, имя console script;
3. **деньги, сеть или публикацию** — на каждое конкретное действие.

Всё остальное — решение агента под ответственность reviewer, **включая удаление
реализации, у которой есть callers**, если callers переведены в том же изменении
и ни один tripwire не сработал. Существующая зависимость не является
доказательством, что её нужно сохранять.

**Уже выданные owner approvals.** Tripwire не отменяется и не ослабляется;
approval — это факт, а не исключение из правила. Утверждение владельцем ревизии
2 этого плана является explicit owner approval на persisted-change **ровно в том
объёме, который уже описан в PLAN-9A**: additive schema, tolerant reader,
чтение старых manifests без миграции, best-so-far/persistence contract в
перечисленном там составе. Повторно спрашивать владельца о самом PLAN-9A не
нужно.

Любое расширение за эти границы — non-additive изменение, новый layout файлов,
переименование каталога проекта, второй manifest, схема вне названного состава
или persisted-изменение в другом слайсе — снова требует owner approval. Approval
на PLAN-9A не переносится на PLAN-9B…PLAN-15 и на PLAN-L. **Уточнено ревизией
2.1:** approval PLAN-9A относится **ровно** к составу PLAN-9A и не переносится
на `PLAN-9B*`, `PLAN-9C`, `PLAN-9D`, `PLAN-9E`, `PLAN-10*` и любые новые
persisted / public / network / destructive изменения.

### Challenge / Recovery Protocol

Новые имена состояний завершённости **не вводятся**: словарь уже принадлежит
`src/assets/completion/modes.py` (`usable_in_draft`, `automatic_render_allowed`,
`publish_ready`, `manual_replacement_recommended`, `manual_replacement_required`,
`blocked` + `block_reasons`, tiers `A_exact…F_emergency`). Причины остановки
принадлежат PLAN-10A. Второй словарь создал бы второго canonical owner.

Когда предписанный подход не даёт результата:

1. назвать **root cause**, а не симптом;
2. **не ослаблять [HARD]**;
3. найти **минимум одну жизнеспособную альтернативу**. Сравнение нескольких
   альтернатив обязательно **только** для неоднозначного, архитектурного,
   дорогого или высокорискового решения; в обычном случае одной работающей
   альтернативы достаточно;
4. внутри decision rights — применить и записать причину;
5. вне decision rights — остановиться, показать альтернативу и рекомендацию.

### Owner Lookup — semantic trigger

Проверка существующего владельца обязательна, когда создаётся:

- новая **shared / cross-cutting responsibility**;
- новый **public owner** — то, на что будут ссылаться извне модуля;
- новый **persisted owner** — то, что пишет или владеет форматом на диске.

Имена классов `Service|Registry|Manager|Provider|Store|Engine` — только
эвристика для reviewer, не сам триггер. Для private-функций не применяется.

Процедура — один проход: grep по существительному-ответственности в
`SYSTEM_MAP.md`, `schemas/` и `src/**` → `reuse` / `extend` / `replace`. При
создании нового owner — одно предложение в commit body о том, почему
существующий нельзя расширить. Enforce выполняет reviewer, отдельный QA-модуль
не создаётся: проверка требует суждения.

### Task contract

Формат задания каждого достаточно крупного слайса:

```
OBJECTIVE          что должно измениться для пользователя
SUCCESS CRITERIA   какой конечный результат считается хорошим
HARD CONSTRAINTS   что нельзя нарушать
ALLOWED ZONES      какие файлы/каталоги разрешено менять
CURRENT APPROACH   рекомендуемый способ
ALTERNATIVES       агент вправе искать самостоятельно
STOP CONDITIONS    когда действительно нужно остановиться
VERIFICATION       чем доказан результат
ROLLBACK           как откатить
EXIT CONDITION     когда пункт можно снять с учёта
```

`ALLOWED ZONES` держится отдельно от `HARD CONSTRAINTS`: первое — scope одного
слайса, второе — вечное правило. В прежней редакции оба записывались одинаково
под заголовком «запрещено», и агент не мог отличить оспариваемое от
неоспариваемого.

## Reversible retirement mechanism

Постоянный каталог `trash/` не создаётся: он стал бы вторым source tree.
Механизм обратимого ретайра:

1. **annotated tag** `retired/<family>-<YYYY-MM-DD>` на последний commit, где
   код ещё существовал;
2. **commit body** ретайр-коммита содержит `Retired:`, `Reason:`,
   `Replaced-by:`, `Recovered-from:` (тег), `Salvaged:` (ссылка на решение
   PLAN-L0), `Exit:`;
3. **таблица `Retired`** в `CLEANUP_REGISTRY.md`;
4. **внешняя копия обязательна.** [FACT] `git remote -v` пуст, поэтому локальные
   теги не защищены от потери диска: перед каждым ретайром выполняется
   `git bundle create` тега во внешний workspace.

Archive branch не используется: ветки дрейфуют и требуют обслуживания.

## Test classification

Перед любым удалением или переписыванием test-модуль получает класс:

```
PRODUCT CONTRACT        защищает поведение, обещанное пользователю
ARCHITECTURE INVARIANT  защищает границу, которую мы намеренно держим
CHARACTERIZATION        зафиксировал поведение на время конкретного refactor
LEGACY ANCHOR           замораживает старую реализацию или accidental structure
```

**LEGACY ANCHOR не препятствует сознательному ретайру старой архитектуры** и
удаляется либо переписывается вместе с ней. Зелёный или красный тест сам по себе
контрактом не является: сначала отвечаем, защищает ли он нужное product/public
behavior или замораживает accidental legacy implementation.

Подтверждённые кандидаты в LEGACY ANCHOR записаны в `CLEANUP_REGISTRY.md`,
раздел «Accidental invariants».

**Физический restructure каталога `tests/` не является prerequisite product
work и в критический путь не входит.** [FACT] сейчас 112 плоских модулей,
30 403 строки, `conftest.py` отсутствует, network guard ставится из
`tests/__init__.py`. Плоская структура с осмысленными именами работает;
реструктуризация дала бы большой diff и нулевую product-ценность. Вопрос
пересматривается **после** PLAN-L, когда модулей останется около 106.
Именование вида `test_anime_factory_v3/v4` и `test_stage1…stage4` кодирует
историю rescue, а не ответственность — кандидаты на переименование, но не
приоритет.

**Известный риск, не закрытый классификацией.** [FACT] test-модули запускают CLI
через `subprocess`, где `tests/network_guard.py` **не действует** — guard живёт
внутри test-пакета и дочерним процессом не наследуется. Это касается не только
режима `smoke` из PLAN-5, но и `full`. **Измерение, не invariant:** на audit HEAD
`adcbb19` таких модулей **12** (было записано 7); при изменении tests число
изменится, нормой оно не является (registry C49).

**Механизм закрытия ревизией 2.1 заранее не выбран.** Расширение guard на
subprocess boundary и environment kill-switch — обе альтернативы остаются
открытыми; выбор и owner — implementation-time evidence/owner decision. **PLAN-6B
остаётся report/measurement owner в своей текущей границе** и ничего не мутирует;
если выбранный механизм потребует, чтобы production-код уважал kill-switch, это
production-изменение вне зон 6B и оно получает своего owner отдельным слайсом.

## Measurement policy

Число тестов, длительность прогона и accuracy моделей — **изменчивые
наблюдения**. Они записываются только как измерение с датой и проверяемым
состоянием Git и никогда не становятся нормой в правилах, тестах или
документах. Критерий успеха проверки — «команда завершилась с exit code 0 без
неожиданных failures/errors», а не совпадение с записанным числом.

Точные **контрактные** значения разрешены и иногда обязательны: `schema_version`,
budget cap, timeout, количество обязательных artifacts, лимиты провайдеров.

Измерения на HEAD `fe2df5b`, 2026-07-30, дерево чистое:

- полный offline suite: 1441 теста, около 245 секунд, 4 failures и 3 errors;
- `tests.test_voice_profile_resolution`: 8 тестов, 1 failure и 3 errors;
- `tests.test_autonomous_completion_pipeline`: 14 тестов, 3 failures;
- кандидат `fast`-режима без десяти render-тяжёлых модулей: около 1350 тестов,
  около 34 секунд;
- канонический CLI: `--help`, `capabilities --json`, `applications list` —
  примерно по одной секунде каждая;
- сохранённая калибровка live-eval: 3 сцены, 6 кандидатов, 12 кадров;
  индикативное измерение, **не** production evidence.

## Execution protocol

1. Разрешённые зоны каждого шага неявно включают этот файл только для
   обновления checkpoint, статуса, фактических проверок и новых evidence.
2. Один bounded slice — один commit. Commit message содержит trailer
   `Plan-Step: <ID>`; Git log является авторитетом для hash.
3. Собственный hash невозможно записать внутри того же commit без
   самоссылочного amend-цикла. Поэтому поле `commit` может заполняться
   последующим plan-only уточнением, но его отсутствие не делает проверенный
   slice незавершённым.
4. Verification-only checkpoint может иметь plan-only commit с измерением и
   указанием **проверенного исходного HEAD**. Последующий docs-only commit не
   выдаётся за проверенный production HEAD.
5. Если один шаг требует нескольких независимых изменений или затрагивает
   больше одной ownership/behavior boundary, он делится на под-slices до
   реализации. Заголовок-этап закрывается только после всех его под-slices.
6. После каждого commit повторяются `git status --short --branch`,
   `git diff --check` и проверки, указанные для slice. Сеть и платные действия
   не считаются проверкой без отдельного owner approval.
7. Targeted tests выполняются после каждого behavior/code slice. Full offline
   suite не запускается автоматически после локального leaf-изменения.
8. Full offline suite обязателен на границе shared contract, persisted schema,
   paths/package root, provider registry, compatibility retirement и при
   закрытии крупного этапа, который объединяет несколько product slices.
9. Если этап состоит из contract-foundation и нескольких adapters, `full`
   выполняется после contract slice и один раз при закрытии семейства; каждый
   adapter между ними проверяется targeted tests.
10. Docs-only и report-only slices не требуют `full`, если не меняют test
    discovery, runner или production contract. Для них обязательны собственные
    QA/tests и `git diff --check`.
11. **Capability owner gate — обязателен, глобальный inventory — нет.** Перед
    изменением конкретной capability доказываются: canonical owner, фактические
    callers, persisted contracts, duplicate implementations, релевантные tests и
    границы legacy/replacement. Это правило класса `[HARD]`. Оно **заменяет**
    прежнее требование закрыть весь PLAN-1 до любого production-изменения:
    доказывается область, которую меняешь, а не весь репозиторий.
12. **Detail policy.** Подробно описывается только `active` шаг и ближайшие
    один-два следующих. `completed` сворачивается до статуса, commit,
    измеримого результата и фактических проверок. `blocked` держится в виде ID,
    зависимостей, allowed/prohibited zones, gates, verification и rollback.
    Развёрнутые описания PLAN-9…PLAN-15 сворачиваются в момент PLAN-8, когда
    у продуктовых подробностей появится собственный владелец
    `PRODUCT_PLAN.md`, а не раньше: до этого свёртка потеряла бы
    owner-approved решения. Этот файл не превращается во второй Master Plan.

## Execution table

Формат каждого шага одинаков. `commit` заполняется только фактическим hash
после выполнения; заранее hash не придумывается — источником является Git.

### Критический путь (ревизия 2.1)

Принцип владельца: **minimum strong foundation → product slice → feedback →
следующий foundation только если он реально нужен.** Не governance-first и не
product-at-any-cost. Product-слайс не ждёт идеального репозитория, но перед
изменением каждой capability агент обязан доказать её настоящего owner.

**До первого product fix — ровно четыре шага плюс два product-слайса:**

```
PLAN-1D-routing
  → PLAN-2 → PLAN-3 → PLAN-4
  → ► PLAN-9B-0 (characterization) → PLAN-9B-1 (provider-language foundation) ◄
```

Почему остаётся каждый из четырёх — по одной строке:

| Blocker | Почему до первого production fix |
|---|---|
| **PLAN-1D-routing** | Без него новый агент, буквально исполнив `AGENTS.md`, уходит в historical master plan и начинает не ту работу. |
| **PLAN-2** | Красный `test_voice_profile_resolution` не даёт различить «сломал я» и «было сломано» в радиусе изменения. |
| **PLAN-3** | То же для `test_autonomous_completion_pipeline` — модуля, который потом меняет PLAN-9A. |
| **PLAN-4** | Без зелёного воспроизводимого baseline targeted-прогон после query-изменения недоказуем. |

**Параллельно, не блокирует первый product fix** (стартует после зелёного
PLAN-4; PLAN-1C′ — сразу):

```
PLAN-5                        · uniform test runner (UX/reproducibility)
PLAN-6A → PLAN-6D → PLAN-6E   · governance / scope control / independent reviewer
PLAN-6B · PLAN-6C · PLAN-7 · PLAN-8 · инкрементальный перевод прозы (OD-5)
PLAN-L0 → L1 → L2 → L3 → L4   · retire legacy content stack
PLAN-1A · PLAN-1B · PLAN-1C′  · capability owner gates
```

**Дальше — по risk boundary, а не по линейной цепочке:**

Граф ниже нормализован по фактическим зависимостям detailed sections; он не
является одной линейной цепочкой и новых рёбер не вводит.

```
семейство 9B (основная последовательность):
  PLAN-9B-0 → PLAN-9B-1 → PLAN-9B-5a → PLAN-9B-4 → PLAN-9B-2

  PLAN-9B-3   — отдельный cleanup/destructive path после PLAN-9B-2
  PLAN-9B-5b  — отдельный destructive retirement path после миграции
                capability/callers и своих gates
  Ни PLAN-9B-3, ни PLAN-9B-5b prerequisite PLAN-9A не являются.

две сходящиеся ветки:
  PLAN-9B-2 + PLAN-1C′ + PLAN-6E → PLAN-9A → PLAN-10A → PLAN-10B → PLAN-10C
  PLAN-1C′ + PLAN-6E             → PLAN-9C → PLAN-9D

PLAN-9E   требует PLAN-9D + PLAN-10C + owner approval
PLAN-10D  после PLAN-10C
PLAN-11   после PLAN-9E + PLAN-10C
затем PLAN-12* → PLAN-13* → PLAN-14* → PLAN-15
```

### Risk-based governance model (ревизия 2.1)

Blocker остаётся только если он защищает **конкретную** risk boundary, которую
пересекает **конкретный** слайс. «Стоял в плане» причиной не является (OD-26).

| Слайс | Роль в ревизии 2.1 | Обоснование одной строкой |
|---|---|---|
| **PLAN-5** | **PARALLEL для всех под-слайсов PLAN-9B** | targeted / full / smoke исполнимы **сегодня** существующими командами (PLAN-4 и CI); PLAN-5 улучшает uniform runner UX и воспроизводимость формулировки, но техническим blocker product fixes не является |
| **PLAN-6A** | **PARALLEL относительно PLAN-9B** | Agent Autonomy Model уже действует из текста этого плана; зависимость **6A → 6D — ordering convention, а не техническая необходимость** |
| **PLAN-6D** | **BLOCKER первого multi-owner implementation slice** | `check_task_scope` защищает от выхода diff за allowed zones; у 9B-0/9B-1 allowlist тривиален, первый multi-owner diff — PLAN-9B-2 |
| **PLAN-6E** | **BLOCKER первого destructive retirement / high-risk shared-contract slice** | reviewer обязан существовать до первого удаления реализации, у которой есть callers (PLAN-9B-2, 9B-3, 9B-5b) |
| **PLAN-1C′** | **прямая зависимость от PLAN-6E снята** | docs-only ownership inventory, пишущий в `CLEANUP_REGISTRY.md`, не требует существования reviewer-skill |
| **PLAN-9A** | **явно требует PLAN-6E** плюс PLAN-9B-2 и PLAN-1C′ | persisted-state boundary |
| **PLAN-9C** | **явно требует PLAN-6E** плюс PLAN-1C′ | semantic decision boundary |

**Почему 9A/9C требуют 6E явно, а не транзитивно.** Через PLAN-9B-2 зависимость
существует и без записи, но транзитивные гарантии ломаются при следующем
reorder. Это **не** ослабление safety, а перенос gate на фактическую risk
boundary.

### Risk-boundary таблица safety gates

Заменяет одну линейную цепочку блокеров и делает явным, что защищает каждый gate.

| Пересекаемая boundary | Обязательные gates | Первый слайс, который её пересекает |
|---|---|---|
| локальное поведение, targeted tests, ноль persisted/public/paid/destructive | 1D, 2, 3, 4 | **PLAN-9B-0, PLAN-9B-1** |
| public CLI / input mode | + **owner approval** (`smoke` исполним существующей командой) | **PLAN-9B-5a** |
| наблюдаемое поведение `strict` | + **owner approval** | PLAN-9B-4 |
| несколько owners в одном diff | + **PLAN-6D** (`check_task_scope`) | PLAN-9B-2 |
| destructive retirement реализации с callers | + **PLAN-6E** + reversible retirement (annotated tag + `git bundle` + строка `Retired`) | PLAN-9B-2, PLAN-9B-3, PLAN-9B-5b |
| persisted bytes / schema / layout | + tolerant reader + **owner approval** (approval PLAN-9A **не переносится**) + PLAN-6E | PLAN-9A |
| semantic / Vision decision path | + **PLAN-1C′** + **PLAN-6E** | PLAN-9C |
| network / model / paid операция | + **owner approval на конкретное действие** + PLAN-6E | model-assisted вариант PLAN-9B-1 (OD-16), PLAN-9E |
| runtime / user data move | + `Preserved runtime corpus` + проверенный абсолютный путь + owner approval | PLAN-14D/14E |

**Что осознанно не оптимизировано.** Путь не сокращался ради меньшего числа
этапов: PLAN-4 сохранён, хотя он «всего лишь измерение»; PLAN-6E сохранён как
blocker первого destructive слайса. Минимизированы только blockers без
конкретной защищаемой boundary.

**Что изменилось относительно ревизии 2.** Первым product-слайсом становится
`PLAN-9B-0/9B-1`, а не `PLAN-9A`: best-so-far persistence бессмысленна, пока
система не получает provider-ready кандидатов (OD-15). В основной **product
order** перевёрнуто одно ключевое ребро: `9A → 9B` становится `9B → 9A`.
Governance dependencies и gates при этом **отдельно перераспределены по
risk-based model**: прямая `1C′ → 6E` снята, `9A → 6E` и `9C → 6E` записаны
явно, `PLAN-5` и `PLAN-6A` стали parallel относительно 9B, 6D/6E переведены на
свои risk boundaries, а PLAN-9B декомпозирован. `PLAN-5`, `PLAN-6A`, `PLAN-6D`,
`PLAN-6E` и `PLAN-1C′` **не удалены**.

PLAN-9B-1 становится первым слайсом, меняющим production-код в продуктовой
ветке; PLAN-L2/L3/L4 меняют production-код независимо, в ретайр-ветке работ, и
на поведение активного `content_creator` не влияют.

Независимые под-slices могут меняться местами только когда их зависимости,
allowed zones и owner approvals не пересекаются; изменение порядка
фиксируется здесь до работы, а не задним числом.

### PLAN-0 — versioned execution plan

- **status:** completed · **completed:** 2026-07-30 ·
  **commit:** `4027269`
- **цель:** один отслеживаемый план для Claude, Codex и других агентов.
- **зависимости:** —
- **разрешённые зоны:** `docs/current/PROJECT_EXECUTION_PLAN.md`,
  одна короткая ссылка в `docs/current/CURRENT_STATE.md`.
- **запрещено:** всё прочее, включая правку master plan.
- **измеримый результат:** план существует, checkpoint виден, ссылка добавлена.
- **required verification:** `tools.qa.check_agent_docs`, `git diff --check`.
- **фактические проверки:** обе команды повторно завершились с exit code 0 на
  clean HEAD `4027269`.
- **rollback:** один commit.

### PLAN-1 — capability owner gates (бывший монолитный 9B-C01)

- **status:** split. Ревизия 2 разделила PLAN-1 на четыре независимых слайса.
  **Глобальный inventory перестал быть предусловием любого
  production-изменения**; вместо него действует правило 11 Execution protocol:
  доказывается owner той capability, которую меняешь.
- **зависимости:** PLAN-0. **Не зависит** от зелёного full suite.
- **разрешённые зоны:** 1A, 1B, 1C′ — только `docs/current/CLEANUP_REGISTRY.md`;
  1D дополнительно допускает короткую routing-правку в `AGENTS.md`,
  `docs/current/START_HERE.md` и `docs/current/CURRENT_STATE.md`.
- **запрещено:** production-код, tests, схемы, config, любые move/delete/untrack,
  создание новых документов, правка master plan, изменение поведения.
- **общие требования к любому caller gate.** Проверяются module entrypoints через
  `python -m`, console scripts в `pyproject.toml`, `*.bat`, `*.cmd`, `*.ps1`,
  `.vscode`, `.idea`, task/config files, tests, docs, относительные, динамические
  и строковые вызовы. Статический import-граф **не** является доказательством
  отсутствия внешнего caller. Поиск вне репозитория запрещён. Вывод о
  дублировании бизнес-логики только по совпадению basename запрещён.

#### PLAN-1D-routing — маршрутизация агентов

- **status:** pending. **Текущий шаг.**
- **зависимости:** STEP 0 (перенос ревизии 2 в этот файл и в registry) выполнен.
  **Порядок обязателен:** 1D направляет будущих агентов в этот документ, поэтому
  документ должен сначала содержать утверждённую архитектуру.
- **цель:** шаг 4 `AGENTS.md` и «Текущий rescue plan» в `START_HERE.md`
  перестают направлять задачу в `PROJECT_RESCUE_MASTER_PLAN.md` как в current
  plan; добавляется ссылка на активный execution plan.
- **расширено 2026-08-01 — stale checkpoint в `CURRENT_STATE.md`.** [FACT]
  `docs/current/CURRENT_STATE.md` ссылается на активный execution plan и при
  этом называет текущим checkpoint `9B-C01`, которого после ревизии 2 больше
  нет. Это тот же routing-дефект в третьем current-документе, поэтому он
  чинится здесь же. **Exit condition расширен:** после PLAN-1D все current
  routing docs указывают на `PROJECT_EXECUTION_PLAN.md` как на current
  execution ordering source и **не называют `9B-C01` текущим checkpoint**. В
  `CURRENT_STATE.md` меняется **только** routing/checkpoint statement;
  unrelated docs cleanup там не выполняется.
- **evidence:** [FACT] у активного плана **одна** входящая ссылка во всём
  репозитории — из `CURRENT_STATE.md`; `AGENTS.md`, `START_HERE.md`, `CLAUDE.md`
  и `README.md` его не упоминают.
- **дополнительно записываются в registry** два уже проверенных findings:
  `docs/current/PRODUCT_EVIDENCE_GATE.md` со `status: historical_reference` как
  кандидат PLAN-12A (перемещение выполняет 12A, не 1D); и факт, что `skills/` не
  загружаются Claude Code автоматически, поскольку каталог не является
  `.claude/skills/`.
- **измеримый результат:** новый агент, буквально исполнив `AGENTS.md`,
  попадает в этот план, а не в historical master plan.
- **required verification:** `tools.qa.check_agent_docs`, `git diff --check`.
- **rollback:** один commit.

#### PLAN-1C′ — capability owner gate: asset/semantic

- **status:** pending. **BLOCKS PLAN-9A и PLAN-9C.** Первый product-слайс
  (PLAN-9B-0/9B-1) **не** блокирует.
- **зависимости:** — . **Изменено ревизией 2.1:** прямая зависимость от PLAN-6E
  **снята** — это docs-only ownership inventory, пишущий в
  `CLEANUP_REGISTRY.md`, и существование reviewer-skill ему не требуется.
  **Одновременно явно зафиксировано:** `PLAN-9A` требует `PLAN-6E`
  (persisted-state boundary) и `PLAN-9C` требует `PLAN-6E` (semantic decision
  boundary). Полагаться на транзитивную зависимость через PLAN-9B-2 запрещено.
- **остаётся обязательным capability-owner gate перед PLAN-9A и PLAN-9C.**
- **scope:** C01-SEM плюс владельцы persisted asset-manifest, релевантные tests и
  проверка дублей в радиусе PLAN-9A: `src/assets/semantic_selection/*`,
  `src/assets/semantic_visual*`, `src/assets/completion/*`,
  `src/news/asset_manifest_builder.py`, `src/news/asset_scene_completion.py`,
  `src/news/project_store.py`, `schemas/`.
- **C01-SEM.** Ownership для `semantic_selection`, `semantic_visual`, visual
  planner и asset completion: кто принимает решение о пригодности кандидата, где
  заканчивается shared service и начинается workflow policy, какова роль
  заглушки `vision_validator` и подключённого, но не влияющего на отбор
  `semantic_visual_service`.
- **дополнительно:** зафиксировать как дефект production-зависимость на
  `docs/implementation/openai_live_evaluation` (registry C31). **Файлы не
  переносить** — target owner решает PLAN-13 по OD-8/OD-9.
- **вынесено из scope ревизией 2:** пофайловая классификация
  `docs/implementation` (96 файлов) переходит в **PLAN-12B** — она не нужна
  PLAN-9A.
- **измеримый результат:** C01-SEM закрыт; для каждого затронутого модуля
  известны canonical owner, callers, persisted contract, дубли и тесты.
- **required verification:** `tools.qa.check_agent_docs`, `git diff --check`.
- **rollback:** один commit.

#### PLAN-1A — capability gate: entrypoints и package roots

- **status:** pending. **Не блокирует первый product fix и PLAN-9A.**
  Обслуживает PLAN-L и PLAN-13.
- **scope:** C01–C04, C08–C11; `pyproject.toml`, console scripts, module
  entrypoints, `apps/*`, root `ai_youtube/`, `src.content_creation.cli`.
- **примечание:** caller gate для `pipeline.py`, `legacy/` и legacy-семейства
  выполняет **PLAN-L1**, а не 1A. Foundation audit установил [FACT], что
  `legacy/` (8 файлов) не имеет ни одного Python-caller и упоминается только в
  `README.md` и historical docs (registry C17); это **не** закрывает C17.
- **required verification:** `tools.qa.check_agent_docs`, `git diff --check`.

#### PLAN-1B — capability gate: application/shared ownership

- **status:** pending. **Не блокирует первый product fix и PLAN-9A.**
  Обслуживает PLAN-13, включая покрытие HIGH-3 (channel/project formats).
- **scope:** C05–C08 и C12–C16; Fullscreen, Story Card, Anime
  project/transcription/subtitles/FFmpeg/render, music, project/workspace и
  границы shared-сервисов.
- **required verification:** `tools.qa.check_agent_docs`, `git diff --check`.

### PLAN-L — retirement legacy content stack

- **status:** pending · **зависимости:** зелёный PLAN-4 ·
  **параллелен PLAN-6A/6D/6E и PLAN-9A; prerequisite для PLAN-9A не является.**
- **цель:** убрать крупнейший disposable блок репозитория до того, как он
  продолжит удерживать docs, packaging, tests и minimalism.
- **evidence [FACT], 2026-07-31:** legacy content-стек — `pipeline.py` →
  `src/legacy_pipeline/workflow.py` → 20 модулей корня `src/` (~4903 строки) —
  имеет **ровно одного** production-caller (`pipeline.py`) и **6** test-модулей
  из 112. `legacy/` (8 файлов, 424 строки) не имеет ни одного Python-caller.
  Исключения, которые остаются: `src/media_library.py` (используется активным
  news-путём) и `src/utils.py` (используется `src/audio/tts/env.py` и
  `src/tts_providers/moss_tts_provider.py`).
- **evidence [FACT]:** `src/legacy_pipeline/maintenance.py` (~500 строк) — **не**
  legacy-генерация контента, а единственный CLI-доступ к visual-preview,
  semantic-backend, semantic-evaluation, semantic-visual, media-library и
  envato-manual. Канонический CLI этих команд не имеет. [INFERENCE] PLAN-9D без
  них не запускается — поэтому L2 обязателен до L3.
- **impact:** −~5700 строк, −6 тестов, −6 top-level путей; закрываются C17, C18,
  C19, C24, C25, C29; PLAN-7, PLAN-13D, PLAN-14B и часть PLAN-14F становятся
  тривиальными.
- **rollback:** один commit на под-slice плюс annotated tag по механизму
  reversible retirement.

#### PLAN-L0 — Knowledge Salvage Gate

- **status:** pending · **обязателен до L3** · **зоны:** только
  `docs/current/CLEANUP_REGISTRY.md`.
- **правило (OD-1):** отсутствие caller — **не** критерий отсутствия ценности.
  Ретайр legacy допускается только после salvage.
- **scope gate — что проходит через L0.** KSG применяется к
  **knowledge-bearing retirement families**: source code, workflow, config,
  prompts, templates, tests и те docs/evidence, которые содержат уникальное
  инженерное или продуктовое знание.
- **что через L0 НЕ проходит.** Disposable runtime/media/cache — старые `.mp4`,
  `.wav`, `.png`, кэши, generated outputs, runtime-каталоги проектов — идёт
  другой цепочкой: **PLAN-14D** (классификация, отбор representative corpus,
  сверка с `Preserved runtime corpus`) → **PLAN-14E** (cleanup). Спрашивать
  «какое product knowledge содержится в старом mp4» не нужно и запрещено как
  формальность: это превратило бы runtime reset в бесконечный gate.
  **Knowledge Salvage и Runtime Reset не смешиваются.**
- **граница между цепочками.** Решает не каталог, а носитель знания: JSON/SRT/ASS
  манифесты — это persisted **форма**, их ценность проверяется отбором
  representative corpus в 14D, а не salvage-классификацией L0. Если внутри
  runtime-каталога найден source/prompt/template/config — он уходит в L0.
- **что искать в каждом удаляемом family:** reusable algorithm · domain и
  product knowledge · prompts, templates, visual rules · rights и licensing
  knowledge · fallback и recovery logic · edge cases · reusable schema
  knowledge · полезные characterization и product tests.
- **классификация каждой находки:**

  ```
  MIGRATE CAPABILITY        пометить как отдельный будущий product slice.
                            НЕ выполняется внутри PLAN-L (OD-10).
  MIGRATE KNOWLEDGE         перенести знание: ADR, docstring, comment, fixture
  KEEP MINIMAL REGRESSION   оставить минимальный representative fixture
  ARCHIVE ONLY              только retirement tag, в active tree не возвращать
  DELETE                    ничего ценного
  ```

- **граница L0/L3 (OD-10).** L0 сохраняет **знание**, а не переносит capability.
  **L3 остаётся cleanup/retirement-этапом и не превращается в
  product-development.** Если salvage признаёт capability ценной — это отдельный
  будущий product slice на новом canonical core из salvage evidence, а не
  миграция старой реализации внутрь L3.
- **семейства в scope:** `channels/{psychology,quotes,survival,size_comparison}`
  и `content/` (OD-1) · 20 движков корня `src/` · `legacy/` ·
  `src/legacy_pipeline/workflow.py` · `config/video_style.json` ·
  `MOSS_TTS_Nano/` и `src/tts_providers/` (OD-7) · 6 legacy test-модулей.
- **обязательные salvage-находки ревизии 2.1** (сохранить **до** retirement;
  старый pipeline ради них **не** сохраняется):
  1. **legacy `build_query_variants` expansion ladder** — `MIGRATE KNOWLEDGE`,
     потребитель **PLAN-9B-2** (registry C46);
  2. **local-library diversity reserve** (`min_local_diversity_per_scene` /
     `reserved_download_slots`) — `MIGRATE KNOWLEDGE`, потребитель **PLAN-10D**
     (registry C47);
  3. **практика «provider-ready английские visual keywords существуют
     отдельным полем, отделённым от нарратива»** — `MIGRATE KNOWLEDGE`,
     носитель ADR/registry (registry C48).
- **измеримый результат:** для каждого family записан класс каждой находки и,
  где применимо, что именно потенциально стоит восстановить позже.
- **required verification:** `tools.qa.check_agent_docs`, `git diff --check`.

#### PLAN-L1 — caller gate и retirement manifest

- **status:** pending · **зависимости:** PLAN-L0 · **зоны:** только registry.
- **цель:** полный caller gate по legacy-семейству по общим требованиям PLAN-1.
  Закрывает C17.
- **дополнительно:** зафиксировать retirement-теги, которые будут созданы в
  L3/L4, и подтвердить наличие внешнего `git bundle` перед первым удалением.
- **required verification:** `tools.qa.check_agent_docs`, `git diff --check`.

#### PLAN-L2 — вынести diagnostics из legacy

- **status:** pending · **зависимости:** PLAN-L1 · **обязателен до L3.**
- **цель:** команды `src/legacy_pipeline/maintenance.py` (visual-preview,
  semantic-backend, semantic-evaluation, semantic-visual, media-library,
  envato-manual) переезжают на канонический CLI `diagnostics` либо в `tools/`.
- **запрещено:** менять поведение команд в этом слайсе; смешивать перенос
  diagnostics с удалением движков.
- **required verification:** targeted + `smoke` + `full` — меняется CLI surface.

#### PLAN-L3 — retire движков

- **status:** pending · **зависимости:** PLAN-L0 и PLAN-L2.
- **удаляется:** `src/legacy_pipeline/workflow.py`; 20 модулей корня `src/`
  **кроме** `media_library.py` и `utils.py`; `src/tts_providers/` (OD-7);
  `channels/{psychology,quotes,survival,size_comparison}` и `content/` (OD-1);
  `config/video_style.json`; 6 legacy test-модулей.
- **запрещено:** мигрировать capability внутрь этого слайса (OD-10).
- **required verification:** `full`.

#### PLAN-L4 — retire entrypoint

- **status:** pending · **зависимости:** PLAN-L3.
- **удаляется:** `pipeline.py`, `src/legacy_pipeline/cli.py`,
  `apps/youtube_pipeline/`, `legacy/`, `scripts/`, `MOSS_TTS_Nano/` (OD-7).
- **исправляется:** `py-modules = ["pipeline"]` снимается вместе с импортом
  `scripts.test_moss_voices` (C18, C25); `outputs/*.json` и
  `outputs/asset_library_report.md` снимаются с Git (C19, C29).
- **измеримый результат:** канонический CLI — единственный пользовательский вход;
  wheel собирается и импортируется из произвольного temporary checkout.
- **required verification:** `full` + сборка wheel + `import` в temporary venv
  вне checkout. Установка требует отдельного разрешения.

### PLAN-2 — baseline repair: voice-profile fixtures

- **status:** pending · **completed:** — · **commit:** —
- **цель:** убрать устаревшую изоляцию через `os.chdir` и использовать явный
  `channels_dir` либо существующий path seam.
- **зависимости:** PLAN-1D-routing. **Изменено ревизией 2:** зависимость от
  полного PLAN-1 снята — слайс трогает один test-модуль и никакого capability
  ownership не меняет.
- **разрешённые зоны:** `tests/test_voice_profile_resolution.py`.
- **запрещено:** production-код, прочие тесты.
- **диагноз:** изоляция через `os.chdir` перестала действовать после того, как
  versioned resources стали резолвиться от корня репозитория, а не от `cwd`;
  реестр читает настоящий `channels/` и возвращает чужой профиль. Production
  корректен.
- **измеримый результат:** модуль завершается без failures и errors; сохранены
  паритет UI и runtime, резолв по display_name, borrowed profile с
  `source_channel_id`, `include_global=False`, понятное сообщение об ошибке.
- **required verification:** только targeted-модуль. Режим `fast` ещё не
  существует до PLAN-5 и поэтому не может быть prerequisite.
- **rollback:** один commit.

### PLAN-3 — baseline repair: completion-wiring fixtures

- **status:** pending · **completed:** — · **commit:** —
- **цель:** создавать обязательные stage outputs согласно output-validated
  idempotency ADR 0006.
- **зависимости:** PLAN-2. **Изменено ревизией 2:** зависимость от полного
  PLAN-1 снята. Слайс трогает один test-модуль, но это **тот самый модуль**,
  который меняет PLAN-9A, поэтому он остаётся прямым prerequisite 9A.
- **разрешённые зоны:** `tests/test_autonomous_completion_pipeline.py`.
- **запрещено:** production-код.
- **диагноз:** три теста помечают стадии `completed`, не создавая обязательных
  outputs, и ожидают поведение до этапа 5D.
- **окончательный resume-факт:** стадия с отсутствующим или непригодным output
  может быть перезапущена; по 28 проверенным проектам платные и сетевые стадии
  не перезапускаются; у 7 проектов могут повториться только локальные
  preview/final render. Старое предположение о повторных платных
  `research`/`script` в current-документы не переносится.
- **измеримый результат:** модуль завершается без failures и errors;
  ожидаемое production-поведение не изменено.
- **required verification:** только targeted-модуль. Совместный полный
  baseline выполняется отдельным PLAN-4.
- **rollback:** один commit.

### PLAN-4 — зелёный baseline

- **status:** pending · **completed:** — · **commit:** —
- **цель:** воспроизводимый зелёный offline baseline.
- **зависимости:** PLAN-2, PLAN-3.
- **разрешённые зоны:** production/tests не меняются; этот plan обновляется
  измерением, проверенным исходным HEAD и новым checkpoint.
- **измеримый результат:** `python -B -m unittest discover -s tests -p "test_*.py"`
  завершается с exit code 0 без неожиданных failures и errors; фактические число
  тестов и время записаны в Measurement policy как измерение с датой и
  проверенным исходным HEAD.
- **required verification:** full offline suite.
- **rollback:** один plan-only checkpoint commit.

### PLAN-5 — единый test runner

- **status:** pending · **completed:** — · **commit:** —
- **цель:** один runner вместо трёх разных правил о тестах.
- **зависимости:** PLAN-4. **PARALLEL для всех под-слайсов PLAN-9B** (ревизия
  2.1). [FACT] targeted (`python -B -m unittest <модули>`), full
  (`python -B -m unittest discover -s tests -p "test_*.py"`) и три smoke-команды
  (`python -m ai_youtube --help`, `capabilities --json`, `applications list`)
  исполнимы **сегодня**. PLAN-5 улучшает uniform runner UX и воспроизводимость
  формулировки; техническим blocker product fixes он не является и в required
  verification слайсов 9B подменяется существующими командами.
- **разрешённые зоны:** `tools/qa/run_tests.py`,
  `.github/workflows/offline-tests.yml` и targeted runner tests.
- **запрещено:** production-код, изменение существующих product-test
  contracts, замена `unittest` как движка, правка network guard. Новые тесты
  самого runner разрешены.
- **режимы:**
  - `smoke` — несколько секунд: import канонического пакета,
    `python -m ai_youtube --help`, `capabilities --json`, `applications list`,
    один безопасный synthetic dry-run при наличии. Только allowlist проверенных
    read-only CLI paths. Учитывать, что tests network guard **не действует**
    автоматически на прямой subprocess CLI;
  - `fast` — suite без render-тяжёлых модулей, ориентир 30–40 секунд;
  - `targeted` — радиус изменённой зависимости;
  - `full` — весь offline suite, включая synthetic renderer contracts.
- **измеримый результат:** четыре режима работают и печатают фактический бюджет;
  вшитых ожидаемых чисел тестов в коде runner нет; каждое исключение из `fast`
  выводится с причиной, а `full` динамически обнаруживает все `test_*.py`;
  offline workflow вызывает тот же `full`, а не поддерживает вторую команду.
  Smoke содержит только доказанно read-only subprocess paths; test-package
  network guard не считается защитой subprocess CLI.
- **required verification:** `smoke` + `fast` + `full`.
- **rollback:** один commit.

### PLAN-6 — governance, ранний minimalism baseline и toolchain audit

- **status:** pending · **completed:** — · **commit:** —
- **цель:** до product/refactor работ закрепить единые правила, измерить
  фактическое загрязнение репозитория и определить владельцев зависимостей.
- **зависимости:** PLAN-5.
- **запрещено:** production-код, удаление/перенос файлов и runtime data,
  создание ADR про governance, обновление lock или скачивание зависимостей.
- **разделение ревизией 2.** Только **6A, 6D и 6E** блокируют PLAN-9A.
  **6B и 6C — параллельные**, глобальными prerequisites product-работ не
  являются.
- **переоценка ревизией 2.1 (risk-based).**
  **6A — PARALLEL** относительно PLAN-9B: Agent Autonomy Model уже действует из
  текста этого плана, а routing чинит PLAN-1D; собственные добавления 6A
  (проверка команд в `skills/*/SKILL.md`, расширение `CURRENT_DOCS`, cap
  `AGENTS.md`) обслуживают PLAN-7 и PLAN-12, не 9B. Зависимость **6A → 6D —
  ordering convention, а не техническая необходимость**.
  **6D — blocker первого multi-owner implementation slice** (PLAN-9B-2).
  **6E — blocker первого destructive retirement / high-risk shared-contract
  slice** (PLAN-9B-2, 9B-3, 9B-5b), плюс **обязателен для PLAN-9A и PLAN-9C**.
- **bounded sub-slices:**
  - **PLAN-6A — governance R1–R12, Agent Autonomy Model и docs QA:**
    - **PARALLEL относительно PLAN-9B** (ревизия 2.1);
    - разрешённые зоны: `AGENTS.md`, `tools/qa/check_agent_docs.py`, связанные
      onboarding и reproducibility tests;
    - R1–R12 в согласованной редакции с категориями A/B/C/D;
    - **переносит в `AGENTS.md` Agent Autonomy Model этого плана:** классы
      `[HARD]/[ARCH]/[HINT]`, «выполнение инструкции не является выполнением
      задачи», Decision rights (три tripwire), Challenge/Recovery Protocol,
      semantic Owner Lookup, Task contract. После переноса соответствующий
      раздел этого плана сворачивается до ссылки: один canonical owner на
      правило;
    - **исправляет три формулировки, ошибочно оформленные как HARD:**
      (a) «сначала добавляй characterization test» → `[HINT]` с условием
      «когда меняешь наблюдаемое поведение, у которого есть caller»;
      (b) «не создавай второй provider contract / voice registry / subtitle
      engine / config resolver / completion ladder» → `[ARCH]`: запрещён
      **второй одновременно живущий** canonical owner, **замена** owner через
      evidence + ADR + review разрешена;
      (c) «сохраняй tolerant readers, resume/force-stage и approval gates» →
      разделить: approval gates `[HARD]`, tolerant readers `[ARCH]`;
    - **cap 120 строк `AGENTS.md`** (`tests/test_stage2_agent_onboarding.py:26`)
      переклассифицируется в measurement/warning. Число не является
      архитектурным решением; `AGENTS.md` остаётся коротким по responsibility.
      Если Engineering Conventions окажутся отдельной responsibility, отдельный
      owner допускается **после доказательства необходимости** и не
      запрещается числом строк. `docs/architecture/ENGINEERING_CONVENTIONS.md`
      заранее не создаётся;
    - **минимальный gap-набор conventions**, у которого сегодня нет владельца и
      который закрывается здесь как `[ARCH]`: правило размещения пакета
      (`src/foo.py` против `src/foo/`); процедура deprecation; политика fixtures
      (versioned / synthetic / временный каталог); именование и категории тестов;
      условие появления нового top-level каталога. Уже покрытое (naming, errors,
      logging, config, persistence, schemas, typing, imports, dependency
      direction, public/private API) повторно не документируется — владельцы
      существуют в коде, ADR и `SYSTEM_MAP`;
    - QA не требует вечного существования конкретных архивных handoff;
    - exact-count проверка skills заменяется минимальным обязательным набором
      критичных skills плюс автоматической проверкой всех найденных;
    - broken link, missing source path и invalid commit — error;
    - возраст документа и превышение рекомендуемого размера — warning;
    - onboarding-лимит `START_HERE.md` может остаться жёстким;
    - `README.md` и `COMMANDS.md` обязаны упоминать канонический CLI;
    - `CURRENT_DOCS` перестаёт быть вшитым кортежем из трёх путей: проверяются
      все файлы `docs/current/` со `status: current` плюс активный execution
      plan. Сейчас QA покрывает три файла из семи, и активный план не
      проверяется вовсе;
    - файл в `docs/current/` со `status`, отличным от `current` или `active`,
      становится error: это делает findings PLAN-1D самопроверяемыми;
    - `max_age_days` перестаёт быть вшитой в код нормой — приходит аргументом,
      дефолт остаётся warning, а не error;
    - снимается требование «`docs/handoff` содержит ровно один файл»: оно
      конфликтует с PLAN-12C, который этот каталог архивирует;
    - **добавляется проверка команд внутри `skills/*/SKILL.md`**: команды,
      которым skill обучает агента, обязаны соответствовать каноническому
      CLI. Foundation audit [FACT]: три из шести skills
      (`create-short-video-first`, `resume-project`, `replace-visual-slot`)
      учат `python -m src.content_creation.cli`, а текущий QA проверяет только
      frontmatter, локальные ссылки и `TODO`. PLAN-7 чинит эти три файла
      однократно; без проверки ничто не мешает им разойтись снова;
  - **PLAN-6B — ранний report-only minimalism baseline:**
    - зависимость: PLAN-6A. **Параллельный: product-работу не блокирует;**
    - **subprocess network-guard measurement (ревизия 2.1, registry C49):**
      guard из test-пакета дочерним процессом **не наследуется**. На audit HEAD
      `adcbb19` subprocess-модулей **12** (ранее записано 7) — это
      **measurement, не invariant**. Архитектурное решение по kill-switch
      сейчас **не принимается**: расширение guard на subprocess boundary и
      environment kill-switch остаются открытыми альтернативами,
      механизм/owner — implementation-time evidence/owner decision. **6B
      остаётся report/measurement owner в своей текущей границе и ничего не
      мутирует**; production-side механизм получает своего owner отдельным
      слайсом;
    - **сохранить как candidates для architecture fitness enforcement**
      (внедрение — здесь и в существующих test-владельцах, второй QA framework
      не создаётся): unknown top-level directories · runtime writes внутрь
      source repo · tracked generated media · absolute machine paths ·
      более одного canonical public CLI · запрещённые application → application
      зависимости · владение persisted manifests и schema · consistency
      provider registry · network boundary · paid calls через approval
      gateway · stale commands и невалидный agent routing.
      Владельцы: детекторы репозитория — `check_repository_minimalism.py`;
      инварианты кода — существующие `tests/test_asset_import_boundaries.py`,
      `tests/test_capability_consistency.py`, `tests/test_artifact_schemas.py`,
      `tests/network_guard.py`; переписываемый `tests/test_apps_structure.py`
      становится тестом «нет второго canonical public CLI»;
    - разрешённые зоны: `tools/qa/check_repository_minimalism.py`, его
      targeted tests, `docs/current/CLEANUP_REGISTRY.md`;
    - отчёт покрывает tracked cache/generated outputs, top-level paths вне
      draft allowlist, exact duplicates, wrappers без registry, retired
      imports, hardcoded machine paths, empty directories и orphan-кандидатов;
    - **три детектора добавляются по проверенным findings Foundation audit:**
      (a) tracked ∩ ignored — `git ls-files -i -c --exclude-standard`; сейчас
      9 файлов: 8 × `outputs/*.json` и `assets/broll/.gitkeep`, где директорное
      правило обесценивает последующее отрицание (registry C19, C21);
      (b) top-level untracked вне allowlist; сейчас `output/` и `tmp/`, не
      покрытые ни одним правилом `.gitignore` (registry C20);
      (c) hardcoded drive-paths **в versioned config**, а не только в коде;
      сейчас `config/video_style.json` и `channels/psychology/style.json`
      (registry C24). Детектор tracked generated outputs обязан находить и
      `outputs/asset_library_report.md`, который под `.gitignore` не подпадает,
      но порождается `src/media_library.py` (registry C29);
    - detector ничего не удаляет; orphan/duplicate остаются review evidence;
  - **PLAN-6C — dependency/toolchain ownership audit:**
    - зависимость: PLAN-6B. **Параллельный: product-работу не блокирует.**
      Ревизия 2 сняла с 6C роль предусловия PLAN-6E: skills discovery
      verification для Codex невыполнима (Codex не установлен) и больше не
      блокирует reviewer — см. PLAN-6E;
    - **installed-package defect C25 и `scripts/` (C18) закрывает PLAN-L4**, а
      не 6C: их носители удаляются вместе с legacy-стеком. За 6C остаётся
      distribution boundary `tools/` (C26) и dependency ownership;
    - read-only по `pyproject.toml`, `requirements.txt`, `requirements.lock`,
      CI/task/config files, Anime/ML optional dependencies, `venv/`,
      MOSS/Whisper/model weights и agent-specific adapters;
    - обновляется только `docs/current/CLEANUP_REGISTRY.md`;
    - фиксируются direct/resolved/optional/toolchain owners, callers,
      воспроизводимость, replacement и exit conditions до package
      consolidation;
    - **обязательная проверка installed-package defect (registry C25).**
      [FACT] `py-modules = ["pipeline"]` включает `pipeline.py` в дистрибутив,
      `packages.find.include` не содержит `scripts*`, а `pipeline.py:9`
      импортирует `scripts.test_moss_voices`. [INFERENCE] non-editable
      установка ломает `import pipeline`; `pip install .` не выполнялся, и CI
      это не ловит, потому что использует `--editable`. Проверяется сборкой
      wheel и импортом в temporary venv вне checkout; требует отдельного
      разрешения на установку. Это прямой блокер критерия PLAN-15
      «installed package из произвольного temporary checkout»;
    - **обязательное решение по intended distribution boundary `tools/`
      (registry C26).** [FACT] `tools*` не входит в `packages.find.include`;
      все известные callers находятся внутри checkout. Отсутствие в wheel
      **не является дефектом по умолчанию**. Если решение — «только checkout»,
      правка идёт в формулировку `AGENTS.md`, а не в `pyproject.toml`.
      Добавлять `tools*` в wheel только ради того, чтобы repository QA
      работал из установленного пакета, запрещено;
    - **обязательная skills discovery verification (совместно с PLAN-6E).**
      Различать четыре разных состояния: наличие файлов, manual loading,
      auto-discovery, actual invocation. [FACT] Claude Code не обнаруживает
      корневой `skills/` автоматически: `.claude/` содержит только
      `settings.json`, `settings.local.json` и `scheduled_tasks.lock`.
      **[ПРЕДП]** утверждение «Codex обнаруживает эти skills через
      `skills/*/agents/openai.yaml`» не проверено: Codex в среде не установлен,
      discovery-check не выполнялся, tracked codex-конфигов в репозитории нет.
      Наличие `agents/openai.yaml` не является доказательством discovery.
      Проверка: получить фактический список project skills установленного
      Codex; выполнить явный вызов одного repo skill; определить обнаруженный
      path; проверить фактическую роль `agents/openai.yaml`; сравнить корневой
      `skills/` со стандартным discovery path. **До получения результата
      второй набор skills не создаётся.**
  - **PLAN-6D — scope control foundation:** см. отдельный раздел ниже;
  - **PLAN-6E — independent reviewer foundation:** см. отдельный раздел ниже.
- **измеримый результат:** docs QA зелёный при новых правилах; `AGENTS.md`
  в районе ста строк; первый minimalism report сохранён как baseline;
  dependency/toolchain решения известны до PLAN-13C и PLAN-14B; scope-контроль
  и независимый reviewer существуют технически, а не только в тексте правил.
- **required verification:** PLAN-6A — docs QA + `full`; PLAN-6B — targeted
  tests detector + docs QA; PLAN-6C — docs QA; PLAN-6D — targeted tests
  `check_task_scope` + docs QA; PLAN-6E — docs QA; `git diff --check` всегда.
- **rollback:** один commit на под-slice.

### PLAN-6D — scope control foundation

- **status:** pending · **completed:** — · **commit:** —
- **цель:** перевести защиту от выхода за scope и от порчи пользовательских
  данных с уровня «агент помнит правило» на уровень технического ограничения.
- **роль в ревизии 2.1:** **BLOCKER первого multi-owner implementation slice**
  — по фактическим footprint'ам это PLAN-9B-2 (`query_adapter` +
  `script_generator` + `visual_planning` + `semantic_selection`). Для PLAN-9B-0
  (один новый test-модуль) и PLAN-9B-1 (один модуль и его тесты) allowlist
  тривиален и проверяется глазами.
- **зависимости:** PLAN-6A — **ordering convention, не техническая
  необходимость** (ревизия 2.1): 6D-1 пишет `.claude/settings.json`, 6D-2
  создаёт `tools/qa/check_task_scope.py`, 6D-3 правит `CLAUDE.md`, и ни одному
  из них не требуется, чтобы R1–R12 уже лежали в `AGENTS.md`. **Исправлено
  ревизией 2:** прежняя зависимость от
  PLAN-6C возвращала параллельные 6B и 6C в критический путь через 6D и
  противоречила разделению «блокируют только 6A, 6D и 6E». Содержательной
  зависимости от dependency/toolchain аудита у 6D нет; единственное касание 6C —
  Codex-часть skills discovery, которая в `CLAUDE.md` не записывается (6D-3).
- **разрешённые зоны:** `.claude/settings.json`, `CLAUDE.md`,
  `tools/qa/check_task_scope.py` и его targeted tests.
- **запрещено:** production-код, создание hooks, создание `.claude/skills/`,
  дублирование содержимого `skills/` в adapter-файлах, блокировка versioned
  resources, fixtures, `.gitkeep` и документации.
- **evidence, на котором построен slice** (проверено 2026-07-30 от clean HEAD
  `2379444`): механизма сравнения allowlist задачи с фактическим Git diff в
  репозитории нет; единственный QA-модуль — `tools/qa/check_agent_docs.py`;
  hooks, `.claude/agents/`, `.claude/skills/` и git-hooks отсутствуют.
- **bounded под-slices:**
  - **6D-1 — permissions: четыре раздельных класса действий.** Классы не
    смешиваются. **Исправлено ревизией 2:** прежняя редакция ставила permanent
    hard deny на `projects/**`, `music/**`, `assets/library/**`,
    `assets/cache/**`, `anime_factory/episodes/**`. Владелец объявил это
    тестовое runtime-медиа disposable, а PLAN-14E обязан его удалить — правило
    пришлось бы обходить ради собственного утверждённого шага. Permission,
    которое придётся обходить, защитой не является.
    - *Hard deny — вечное:* secrets — существующие `.env`/credentials/pem/key
      плюс `Write` и `Edit` по `.env` (сейчас закрыт только `Read`);
      destructive Git — `reset --hard`, `clean` по непроверенным путям, force
      operations, включая починку голого `git clean`, который текущий шаблон
      `Bash(git clean *)` не ловит; удаление реальных user data, **не**
      классифицированных владельцем как disposable.
    - *Scope / explicit cleanup authorization:* legacy и test runtime/media,
      уже объявленные disposable, — `projects/**`, `music/**`,
      `assets/library/**`, `assets/cache/**`, `anime_factory/episodes/**`.
      Вне своего bounded cleanup slice эти пути остаются закрытыми; удаление
      разрешено **только** внутри PLAN-14C/14D/14E (или PLAN-L для legacy
      носителей), только по проверенному абсолютному пути и только после
      сверки с `Preserved runtime corpus` в `CLEANUP_REGISTRY.md`.
      Классификация «disposable» **не** является разрешением удалить: она лишь
      снимает вечность запрета.
    - *Смешанные каталоги:* `outputs/**` и `manual_assets/**` **не**
      блокируются целиком — под ними лежат tracked versioned-файлы. Для них
      используются точные подпути или типы runtime-файлов. `channels/**` и
      `content/**` не блокируются вовсе.
    - *Ask / explicit owner approval:* `git push`, создание remote,
      `git stash`, `git commit --amend`, сеть, provider search/download и
      paid API. Бессрочный hard deny для них не применяется, если permission
      system поддерживает ask-policy. Поддержка ключа `ask` проверяется внутри
      этого под-slice до записи правил; если ключ недоступен, эти действия
      остаются instruction-level требованием и в hard deny **не** переводятся.
    - *Записанная граница:* Claude permissions не защищают от произвольного
      Python-кода, запущенного через Bash. Выдавать deny-list за полную защиту
      запрещено.
    - *Limitation и fallback для scope-класса:* `.claude/settings.json` не
      знает, какой plan-step выполняется, поэтому «deny везде, кроме
      утверждённого cleanup slice» декларативно не выражается. Проверяется
      внутри под-slice: если доступен `ask`, disposable-пути получают `ask`, а
      не `deny`; если `ask` недоступен — они остаются в `deny`, и cleanup slice
      снимает правило **своим** commit, а не обходит его. Постоянный `deny`,
      который исполнитель PLAN-14E обязан обойти, не записывается: это ложная
      защита. Фактическую границу удержания держат `check_task_scope` (6D-2),
      `Preserved runtime corpus` и требование абсолютного пути.
    - *Почему не hook:* `.claude/settings.json` уже является владельцем этого
      ограничения и покрывает требуемое декларативно. Hook стал бы вторым
      владельцем одного правила.
  - **6D-2 — `tools/qa/check_task_scope.py`.** Allowlist передаётся конкретной
    задачей; сравнивается с фактическим `git diff --name-only` с учётом add,
    rename и delete; неожиданный файл даёт понятный `STOP_REQUIRED`; модуль
    ничего не исправляет автоматически; постоянного глобального списка файлов
    всех задач он не хранит; активный execution plan считается разрешённым
    только когда его изменение входит в протокол шага. Tests обязаны покрывать
    случаи allowed, unexpected, rename, delete и empty diff.
    *Owner:* пакет `tools/qa` уже является владельцем QA. Модуль
    `check_agent_docs.py` расширить нельзя: у него другой вход (статические
    инварианты репозитория против allowlist конкретной задачи) и другой
    lifecycle. Прецедент sibling-модуля уже утверждён в PLAN-6B
    (`check_repository_minimalism.py`), поэтому второго source of truth не
    возникает. *Exit condition:* модуль удаляется, если scope-контроль станет
    частью harness.
  - **6D-3 — `CLAUDE.md`.** Одно предложение о том, что `skills/` не
    загружаются автоматически и релевантный `SKILL.md` нужно открыть перед
    задачей. Содержимое skills не дублируется. `.claude/skills/` не создаётся:
    это был бы второй набор skills и нарушение ADR 0001.
    **Границы утверждения:** формулировка про отсутствие auto-discovery
    доказана для Claude Code [FACT]. Утверждение о поведении Codex в
    `CLAUDE.md` не записывается до skills discovery verification PLAN-6C/6E:
    оно пока имеет статус **[ПРЕДП]**.
- **измеримый результат:** deny/ask отражают проверенные пути и не блокируют ни
  один tracked versioned-файл; `check_task_scope` возвращает `STOP_REQUIRED` на
  неожиданный файл и молчит на разрешённый; `CLAUDE.md` объясняет загрузку
  skills; ни одного нового hook, agent или документа не создано.
- **required verification:** targeted tests `check_task_scope`, docs QA,
  `git diff --check`.
- **rollback:** один commit на под-slice.

### PLAN-6E — independent reviewer foundation

- **status:** pending · **completed:** — · **commit:** —
- **цель:** один независимый read-only reviewer до первого destructive и
  high-risk production-slice.
- **роль в ревизии 2.1:** **BLOCKER первого destructive retirement / high-risk
  shared-contract slice** — PLAN-9B-2 (orca-hardcode с собственным тестом),
  PLAN-9B-3 (query-path cleanup), PLAN-9B-5b (retirement `apps/news_to_short`,
  у которого есть test-callers). **Дополнительно обязателен для PLAN-9A**
  (persisted bytes) **и PLAN-9C** (semantic decision path) — обе позиции уже
  входят в список «когда reviewer обязателен» ниже. Для PLAN-9B-0/9B-1
  необязателен: они не пересекают ни одну из этих boundary.
- **зависимости:** PLAN-6D. **Не является** blocker первого product fix.
- **разрешённые зоны:** `skills/review-change/`, `.claude/agents/`,
  `tools/qa/check_agent_docs.py` в части регистрации нового skill.
- **запрещено:** production-код, раздельные review policies для Claude и
  Codex, orchestrator, постоянная команда агентов, reviewer, исправляющий
  собственный finding.
- **обязательный порядок:** сначала доказать overlap с существующими skills.
  Новый owner создаётся только если ни один существующий skill не может быть
  безопасно доработан. `skills/architecture-change` для этого не подходит: он
  принадлежит implementer, и расширение сделало бы implementer собственным
  reviewer.
- **предусловие — разделено ревизией 2 (снят deadlock).** Прежняя формулировка
  блокировала 6E на skills discovery verification для Codex внутри PLAN-6C.
  [FACT] Codex в среде не установлен, discovery-check выполнить невозможно, а
  6E обязателен до PLAN-9A — план не мог продвинуться. Теперь:
  - **Claude-часть выполнима и обязательна сейчас.** [FACT] `skills/` не
    является `.claude/skills/`, auto-discovery нет: создаётся canonical
    `skills/review-change/SKILL.md` и тонкий adapter
    `.claude/agents/review-change.md`, поведение подтверждается controlled
    read-only acceptance ниже;
  - **Codex-adapter остаётся `[ПРЕДП]`** до фактической проверки discovery и
    6E не блокирует. Второй набор skills не создаётся ни при каком результате.
- **canonical policy — одна, model-independent:**
  - `skills/review-change/SKILL.md` — единственный источник review rules;
  - `skills/review-change/agents/openai.yaml` — тонкий adapter для Codex по уже
    существующему в репозитории шаблону;
  - `.claude/agents/review-change.md` — тонкий adapter для Claude, который
    ссылается на canonical skill и не дублирует правила.
- **поведение reviewer:** работает read-only; проверяет конкретный immutable
  commit или явно заданный diff; не редактирует файлы; не исправляет findings;
  не создаёт commit; не обновляет этот план; не меняет checkpoint; выдаёт
  findings по severity с `file:line`, evidence, impact и smallest safe
  correction; отдельно перечисляет executed checks, skipped checks и residual
  risks; проверяет task scope, duplicate owner, compatibility, persisted state,
  paid/network behavior и фактическую эффективность тестов; после repair
  выполняет повторный review.
- **разделение ролей (уточнено ревизией 2).** Implementer **активно ищет лучший
  способ** решить задачу, свободен внутри allowed scope, вправе оспорить план и
  предложить альтернативу. Reviewer работает **консервативно**: ищет нарушения,
  duplicate owner, contract break, architecture drift, unsafe data handling,
  rights violations, unverified success, regression. Implementer и reviewer не
  являются одним контекстом; repair выполняет implementer после подтверждения
  findings владельцем.
- **обязательный класс findings «unmet objective / premature stop».** Reviewer
  проверяет не только нарушения, но и обратное: не остановился ли implementer на
  соблюдении процедуры, не достигнув SUCCESS CRITERIA и не попытавшись найти
  альтернативу. Без этого класса reviewer не ловит именно тот сбой, ради
  которого пересмотрена модель автономии.
- **техническое подтверждение read-only, определяется до реализации:**
  отсутствие Write/Edit в наборе инструментов adapter; безопасный набор
  read-only Git/search команд; сравнение `git status` и `git diff` до и после
  review. Review считается неуспешным, если working tree изменён reviewer-ом.
- **когда reviewer обязателен:** persisted state, manifests, resume, providers,
  asset selection, semantic/Vision, rights/provenance, paid/TTS, rendering,
  package boundaries, shared contracts, compatibility retirement, runtime
  migration. Для простой Markdown-правки не требуется.
- **измеримый результат:** существует ровно одна canonical review policy и не
  более двух тонких adapters; read-only подтверждается технически, а не
  обещанием; reviewer не может закрыть собственный finding.
- **controlled read-only acceptance (обязательна).** `docs QA` и
  `git diff --check` доказывают только целостность документов: `--check` ищет
  whitespace-ошибки и конфликтные маркеры и не сравнивает состояние дерева.
  Поэтому поведение reviewer проверяется отдельной контролируемой процедурой,
  результат которой записывается как evidence слайса:
  1. зафиксировать `git status --short --branch` и `git diff --stat` до review;
  2. запустить reviewer на конкретном immutable commit;
  3. повторно снять `git status` и `git diff` и доказать отсутствие изменений;
  4. прогнать один заведомо безопасный diff — ожидается отсутствие findings
     или только информационные;
  5. прогнать один synthetic diff с известным нарушением — ожидается, что
     нарушение найдено с `file:line`, evidence, impact и smallest safe
     correction;
  6. подтвердить, что reviewer нарушение **не исправил**, файлов не изменил и
     commit не создал.
  Review считается неуспешным, если working tree изменён reviewer-ом.
  Synthetic diff создаётся во временном каталоге вне репозитория и в Git не
  попадает. Отдельная автоматизация и новый QA-модуль для этого не создаются:
  процедура выполняется один раз при закрытии слайса.
- **required verification:** controlled read-only acceptance (шаги 1–6),
  docs QA, `git diff --check`.
- **rollback:** один commit.

### PLAN-7 — канонический пользовательский CLI в документации

- **status:** pending · **completed:** — · **commit:** —
- **цель:** документация перестаёт обучать устаревшему entrypoint.
- **зависимости:** PLAN-6A. **Параллельный: product-работу не блокирует**
  (изменено ревизией 2).
- **взаимодействие с PLAN-L.** L4 удаляет `pipeline.py`, поэтому 24 упоминания
  `pipeline.py` в `COMMANDS.md` исчезают как факт, а не переписываются. Если L4
  выполнен раньше PLAN-7 — сверять по фактическому `--help`, а не по этому
  списку.
- **язык (OD-5).** `README.md` и `COMMANDS.md` сокращаются с 1086 до ~300 строк;
  русская редакция получается **побочно при переписывании**, отдельным
  переводом это не оформляется и mass-diff не создаёт. Правило: не переводить
  filenames, directory names, identifiers, CLI/API, JSON/YAML keys, точные
  команды, имена библиотек, литералы, блоки кода, third-party licenses и
  historical artifacts. Каталоги `docs/archive/`, `docs/audits/` и
  `docs/implementation/` в scope перевода не входят как historical.
- **разрешённые зоны:** `README.md`, `COMMANDS.md`,
  `skills/create-short-video-first/SKILL.md`, `skills/resume-project/SKILL.md`,
  `skills/replace-visual-slot/SKILL.md`,
  `docs/contracts/STAGE1_PUBLIC_CONTRACTS.md`.
- **запрещено:** production-код, **удаление старых entrypoints**.
- **требования:** `COMMANDS.md` — 100–150 строк, основные команды и ссылка на
  `--help`; `README.md` — около 150 строк, фактический продукт,
  active/planned/disabled и быстрый старт. Команды сверять с фактическим
  `--help`, а не по памяти.
- **измеренный масштаб расхождения** (Foundation audit, [FACT] от `4ca3655`):
  `README.md` — 405 строк, упоминаний `ai_youtube` **0**, учит bare `python`
  и `pip` вопреки `AGENTS.md`; `COMMANDS.md` — 681 строка, упоминаний
  `ai_youtube` **0** против 49 × `src.content_creation.cli` и 24 ×
  `pipeline.py`; три `SKILL.md` учат `src.content_creation.cli`;
  `docs/contracts/STAGE1_PUBLIC_CONTRACTS.md` называет
  `src.content_creation.cli` «current CLI» и канонический CLI не упоминает.
  Это измерение, а не норма.
- **`docs/contracts/` — порядок:** файл добавлен в зоны потому, что обучает
  устаревшему entrypoint и до сих пор не входил ни в один slice (registry
  C22). Его **target responsibility** решает PLAN-12E по содержимому; PLAN-7
  правит только утверждения о каноническом CLI и не перемещает файл.
- **измеримый результат:** ни один из этих файлов не обучает устаревшему пути.
- **required verification:** docs QA + `smoke`.
- **rollback:** один commit.

### PLAN-8 — PRODUCT_PLAN.md

- **status:** pending · **completed:** — · **commit:** —
- **цель:** отделить продуктовую цель и evidence от архитектурного порядка.
- **зависимости:** PLAN-7. **Параллельный: product-работу не блокирует**
  (изменено ревизией 2 — прежде PLAN-8 стоял в prerequisite-цепочке 9A).
- **разрешённые зоны:** `docs/current/PRODUCT_PLAN.md`.
- **запрещено:** создание `ARCHITECTURE_DEBT.md` до того, как PLAN-1 докажет
  фактический пробел относительно `CLEANUP_REGISTRY.md`.
- **измеримый результат:** продуктовый приоритет, измеренная база и критерии
  M1/M2/M3 зафиксированы; отдельно записан post-rescue roadmap:
  `video_repurposer` через migration Anime Factory и будущий
  longform/documentary workflow `content_creator`, с entry/enable evidence и
  без создания новых engine stacks. Ориентир до 250 строк.
- **обязательные roadmap-записи ревизии 2.1** (PLAN-8 — **roadmap owner**, не
  implementation owner ни одной из них):
  - **post-rescue roadmap `video_repurposer` (OD-23):** Content Creator stable →
    UI Content Creator → отдельный deep audit Anime Factory → классификация
    каждой capability `KEEP · MIGRATE · REWRITE · SHARE · DELETE` → Video
    Repurposer из существующего Anime Factory + shared core → его UI. Второй
    clip pipeline с нуля запрещён; deep audit Anime Factory ближайшим шагом
    **не** является;
  - **future AI / advanced editing note (OD-17, OD-20):** `NO IMPLEMENTATION ·
    NO PLACEHOLDER PACKAGES · NO SPECULATIVE INTERFACES · NO NEW BLOCKERS`.
    Future AI layer подключается **сверху** к существующему production
    pipeline: `AI research / script layer → тот же prepared content contract →
    существующий downstream video production engine`. `LLMScriptProvider` уже
    зарегистрирован как `planned` — этой точки подключения достаточно;
  - **future-proofing rule:** downstream production pipeline не должен
    предполагать, что script создан внутри AI-YouTube. Prepared external
    content (человек, внешний AI, ручной ввод) — **first-class input**;
  - **product-quality item «несколько lossy generations в final render»**
    (registry C45). Фактический нормальный путь: segment encode CRF 23 →
    concat **`-c:v copy`** → audio + exact-duration encode CRF 20 → ASS
    subtitle encode CRF 21 → copies. Concat **не перекодирует**; CRF 20
    принадлежит duration-control mux и имеет документированную причину
    (`-shortest` + `-c:v copy` промахивается по длительности). Три lossy
    generations возникают при **audio + ASS subtitles**. «Single-pass как
    простой fix» — неверно. Первый разумный кандидат будущего renderer-слайса:
    объединить audio/duration encode и subtitle burn в один encode, **если
    characterization докажет эквивалентность**; полный filtergraph single-pass —
    отдельное более крупное исследование. **PLAN-8 хранит запись; implementation
    owner — будущий bounded renderer slice с characterization первым. Нового
    PLAN-ID сейчас не создаётся.**
- **решение по отдельному `EVALUATION_STRATEGY`:** принимается **после** того,
  как `PRODUCT_PLAN.md` написан, и **по качественным критериям**, а не по
  объёму файла: отдельная responsibility; отдельные readers; отдельный
  lifecycle; смешение контрактов; routing ambiguity; maintenance coupling.
  Количество строк — measurement и warning signal, оно может подтверждать
  проблему, но само по себе новый файл не создаёт. Числовой порог объёма как
  условие extraction не задаётся.
- **обязательное завершение:** после commit `PRODUCT_PLAN.md` продуктовые
  подробности PLAN-9–PLAN-11 (лестницы, M1/M2/M3, reference domains и quality
  evidence) переносятся туда. В этом execution plan остаются только ID,
  зависимости, allowed/prohibited zones, gates, verification и rollback.
  До появления проверенного `PRODUCT_PLAN.md` текущие подробности не удалять.
- **required verification:** docs QA.
- **rollback:** один commit.

### Продуктовая рамка PLAN-9 и PLAN-10: где именно дыра в asset-search

Зафиксировано ревизией 2, чтобы будущий агент не начал строить то, что уже
построено.

**Не является дырой.** `src/assets/completion/` уже владеет лестницей выбора
`A_exact → B_composite → C_good_context → D_partial → E_generated → F_emergency`
с жёстким фильтром `modes.blocking_reasons` (неизвестные или запрещённые права,
битый файл, `must_avoid`, заявленное противоречие, evidence на другой предмет) и
детерминированным `tie_break_key`, не зависящим от того, какой provider ответил
первым. Rung E — сгенерированная по спецификации сцены диаграмма, rung F —
project-owned нейтральная карточка, которая ничего не утверждает. Это canonical
owner completion-состояний; он сохраняется, пока дальнейшее evidence не докажет
дефект boundary. Второй словарь состояний не вводится.

**Является дырой — всё выше по потоку** (карта исправлена ревизией 2.1: над
генерацией запросов находятся ещё две ступени):

```
prepared content / topic
  → [CRITICAL-2] source material: topic не является материалом; thin input
                 молча уходит в LegacyTemplateScriptProvider, а
                 script_validation остаётся "passed"
  → research     (в текущем scope дефектом не является)
  → script       (DeterministicScriptProvider исправен при наличии материала)
  → visual plan  (intents на языке сценария; translation_required выставляется
                  и никем не читается)
  → [CRITICAL-1] provider language: единственный канал доставки английского
                 запроса — visual_brief, а заполняет его только topic-hardcode.
                 GLOSSARY матчится подстрокой → ложные срабатывания и
                 морфологические пропуски. source_is_latin — свойство набора,
                 поэтому английский alternative выбрасывается вместе с русским
  → providers    (нет pagination — PLAN-10B/10C; эффект только после CRITICAL-1)
  → semantic     (metadata-слой РЕШАЕТ; платный Vision подаёт evidence поздно —
                  PLAN-9C)
  → completion   (работает; canonical owner; не трогать)
```

| Что | Owner-слайс |
|---|---|
| честность источника сценария (`topic` → template) | **PLAN-9B-4** |
| канонический вход «исходный текст» | **PLAN-9B-5a** |
| источник provider-language запросов | **PLAN-9B-1** |
| лестница расширения и снятие topic-hardcodes | **PLAN-9B-2** |
| retirement устаревших query-путей | **PLAN-9B-3** |
| semantic/Vision producer → existing consumer wiring | PLAN-9C |
| best-so-far persistence через `resume` | PLAN-9A |
| ledger попыток и причины остановки | PLAN-10A |
| pagination и provider exhaustion | PLAN-10B |
| adaptive budget, plateau, порядок эскалации | PLAN-10C |
| global local stock library convergence | PLAN-10D |
| альтернативная правдивая визуальная стратегия | PLAN-9B + PLAN-10C |

**Скрытая связь двух findings.** Сегодня шаблонный сценарий не доезжает до
publish только потому, что все сцены `missing` из-за CRITICAL-1. Как только
CRITICAL-1 починят, шаблонный сценарий поедет в publish беспрепятственно.
Поэтому CRITICAL-2 **не откладывается** за CRITICAL-1, а идёт внутри той же
цепочки PLAN-9B.

**Hard constraints отбора** (класс `[HARD]`, не предмет торга ни при каком
качестве): factual truth · rights и provenance · `must_avoid` ·
misleading/conflict · paid approval.

**Heuristics отбора** (класс `[HINT]`, агент вправе изменить с обоснованием,
пока не доказано обратное): приоритет провайдеров · число и виды запросов ·
пороги `minimum_confidence` и `hard_reject_confidence` · предпочтительный тип
визуала для сцены · размер shortlist.

### PLAN-9A — best-so-far foundation и tolerant persistence/resume

- **status:** blocked · **commit:** —
- **prerequisite chain (единственная действующая, ревизия 2.1):**
  `PLAN-9B-2` + `PLAN-1C′` + **`PLAN-6E`**. Прежняя цепочка
  `…PLAN-5 → PLAN-6A → PLAN-6D → PLAN-6E → PLAN-1C′` отменена ревизией 2.1:
  PLAN-5 и PLAN-6A параллельны, PLAN-6D входит транзитивно как предусловие
  PLAN-9B-2, а PLAN-6E записан **явно** из-за persisted-state boundary, а не
  транзитивно. Отдельный owner approval на сам слайс не требуется, потому что он
  **уже выдан**: persisted-bytes tripwire срабатывает, и утверждение ревизии 2
  покрывает его ровно в описанном здесь объёме — см. «Decision rights → Уже
  выданные owner approvals». Tripwire этим не отменён: любое
  persisted-изменение сверх состава и ограничений ниже требует нового approval.
- **изменено ревизией 2.1 — только место, не состав.** PLAN-9A выполняется
  **после** PLAN-9B: best-so-far persistence бессмысленна до того, как система
  получает нормальные provider-ready candidates (OD-15). Состав, ограничения,
  additive schema, tolerant reader, уже выданный owner approval и success
  criteria сохраняются дословно. Первым product-слайсом программы становится
  PLAN-9B-0/9B-1.
- **цель:** до расширения поиска гарантировать, что лучший найденный материал
  не теряется между итерациями и при `resume`.
- **состав:** top candidates по сцене, best-so-far с обоснованием, semantic
  score, rights status, Vision/evaluation result, manual approvals, выбранный
  fallback. Расширяет существующие `rejected_candidates`/`rejected_reasons`;
  второй manifest или project system не создаётся.
- **логическая когезия search-session state (OD-24).** PLAN-9A, PLAN-10A,
  PLAN-10B и PLAN-10C логически описывают **одно** состояние одного поиска.
  Это проектное требование, а **не** новый файл: `search_session.json` как
  отдельный persisted owner **не создаётся и не утверждается**; четыре
  независимые persisted schemas заранее не утверждаются. До выбора physical
  representation обязательно проверить существующих owners — `job.json`, asset
  manifest, project state, completion/resume state. **Если существующего owner
  можно расширить, новый persisted файл запрещён.** Разбиение implementation на
  bounded commits когезии не нарушает: она относится к схеме и владению.
- **ограничения:** additive schema/tolerant reader; старые manifests и resume
  читаются без миграции; characterization-first.
- **измеримый результат:** после остановки, ошибки или resume сохранённый
  best-so-far не ухудшается и остаётся объяснимым.
- **required verification:** targeted persisted-contract tests + `full`.
- **rollback:** один commit.

### PLAN-9B — input/query truth (bounded family)

- **status:** pending. **Первый product-этап программы** (ревизия 2.1);
  PLAN-9A его больше не блокирует.
- **цель семейства:** **input/query truth — provider-language adaptation,
  query expansion, truthful source input и cleanup старых query paths.**
- **зависимости семейства:** `PLAN-1D-routing → PLAN-2 → PLAN-3 → PLAN-4`.
  Дальнейшие gates — **по risk boundary каждого под-слайса**, см. таблицу
  «Risk-boundary таблица safety gates».
- **новый top-level PLAN-ID не создаётся (E-13):** CRITICAL-2 размещается
  bounded под-слайсами внутри PLAN-9B.
- **порядок выполнения** (идентификаторы под-слайсов — **не** порядок; прецедент
  PLAN-6D/PLAN-12/PLAN-13):

  ```
  PLAN-9B-0 → PLAN-9B-1 → PLAN-9B-5a → PLAN-9B-4 → PLAN-9B-2 → PLAN-9B-3
  PLAN-9B-5b — после успешной миграции capability и готовности его
               destructive gates
  ```

- **фактический owner remote-запросов (OD-14).** [FACT]
  `src/assets/semantic_selection/query_generator.py` **не участвует** в
  формировании запросов к remote-провайдерам: его callers питают
  envato-метаданные и отчёты. Единственные точки контакта с провайдером —
  `build_scene_queries` и `build_slot_queries` в `src/assets/query_adapter.py`;
  других путей к remote-провайдеру в активном workflow нет. Прежняя allowed
  zone ревизии 2 была ошибочной и заменена.
- **граница семейства сохраняется:** лестница заканчивается на генерации
  запросов. Переход к локальной медиатеке, к другому provider и к разрешённому
  fallback — routing/completion policy; владельцы — PLAN-10C (порядок
  эскалации), PLAN-10B (provider contract), PLAN-10D (global local library).
- **regression по разным доменам (OD-25):** после каждого существенного
  под-слайса, где это релевантно, проверять репрезентативные темы минимум из
  разных классов (animals/wildlife · energy/technology · geography/
  infrastructure). PLAN-11 остаётся финальным product evidence gate, но не
  первой multi-topic проверкой.
- **тесты T1–T11** из `docs/audits/CRITICAL_INPUT_SEARCH_DEEP_DIVE_2026-07-31.md`
  распределены как regression/product tests по под-слайсам ниже. Отдельный
  диагностический этап под них **не создаётся** (OD-11).
- **rollback:** один commit на под-slice.

#### PLAN-9B-0 — characterization текущего поведения

- **status:** pending. **Первый шаг семейства.**
- **зависимости:** PLAN-4.
- **цель:** зафиксировать фактическое поведение **до** правки, чтобы диффы были
  доказуемы. **Ноль production-изменений**, ноль сети, ноль денег.
- **разрешённые зоны:** новый offline test-модуль и evidence в этом плане.
- **фиксируется:** фактическое число provider `search()`-вызовов на тему ·
  source каждого запроса · уникальные отправленные строки, включая ложные
  `ice researchers` и чрезмерно общий `station` · число провайдеров,
  пропущенных по `translation_required` · `legacy_template` при
  `script_validation == passed` · **persisted содержимое `query_plan` до
  изменения** (байты `assets_manifest.json` меняются даже при
  не-schema-level правке).
- **тесты deep-dive:** T10, T11.
- **risk boundary:** нет.
- **required verification:** targeted + активный `network_guard`.

#### PLAN-9B-1 — provider-language / query foundation

- **status:** pending · **зависимости:** PLAN-9B-0.
- **фактический owner:** `src/assets/query_adapter.py`.
- **цель:** произвольный visual intent порождает **несколько provider-ready
  queries** без topic-specific hardcode.
- **разрешённые зоны:** `src/assets/query_adapter.py` и его тесты.
- **reuse (OD-13) — новых сущностей не создаётся:** `VisualBrief` ·
  `SceneVisualPlan` / `VisualSearchIntent` · `ProviderQuery` ·
  `build_scene_queries` / `build_slot_queries` · provider contracts.
  **Не создавать** `TranslatorService`, `SearchEngine`, `QueryOrchestrator` и
  второй query pipeline.
- **сохранить fail-closed.** При неуверенности по-прежнему
  `translation_required`, а не догадка. Догадки как factual query не
  отправляются. «Просто отправлять русский текст провайдеру» — откат к уже
  измеренному нулевому результату и запрещён.
- **исправляется в scope этого слайса:** harmful substring glossary matching
  (состав терминов сохраняется как seed, механизм матчинга заменяется —
  границы слова + нормализация) · морфологические пропуски ·
  provider-language source gap.
- **метод adaptation заранее не фиксируется (OD-16):** deterministic
  normalization/lexicon, prepared brief, model-assisted adaptation или
  комбинация — по evidence. **Model/network вариант требует отдельного owner
  approval на конкретное действие.**
- **`ProviderQuery.source` — E-2 закрыт.** Это существующее свободное строковое
  telemetry-поле: **не** schema-level change, tolerant reader не требуется,
  persisted-bytes tripwire не срабатывает. Characterization 9B-0 обязан
  зафиксировать `query_plan` до правки.
- **тесты deep-dive:** T1, T2, T3, T4, T5. **Исправлено 2026-08-01:** T3
  («английская alternative не выбрасывается вместе с русским primary») проверяет
  исправление `source_is_latin`, который вычисляется на уровне всего набора в
  `src/assets/query_adapter.py` — то есть в owner и allowed zone этого слайса.
- **risk boundary:** локальное поведение одного owner; ноль public/paid/
  destructive. Достаточно 1D/2/3/4.
- **required verification:** targeted `query_adapter` tests; `full` — только
  если проверка покажет изменение shared contract.

#### PLAN-9B-5a — additive source-text canonical input (CRITICAL-2, часть 1)

- **status:** pending · **зависимости:** PLAN-9B-1.
- **исправлено 2026-08-01 — source text уже частично существует.** [FACT]
  канонический `python -m ai_youtube create` через `--pasted-script` /
  `--script-file` при текущем default/legacy unspecified `content_input_mode`
  уже проводит подготовленный исходный текст в тот же downstream
  (`text` / `text_file` → deterministic/extractive script path). Формулировки
  «канонический CLI не имеет source-text входа» и «`--text`/`--text-file` —
  единственная уникальная capability» **опровергнуты** и не возвращаются.
- **цель (переопределена):** сделать source-material input **явным first-class
  canonical contract**: выбрать owner-approved public naming; убрать
  зависимость от implicit/legacy unspecified mode; валидировать intent;
  документировать; покрыть smoke/test public behavior; сохранить prepared
  external content как first-class input. Слайс **не** создаёт новый script
  engine и **не** создаёт capability с нуля.
- **additive: `apps/news_to_short` в этом слайсе не удаляется.**
- **имя input mode окончательно не фиксируется**, пока implementation не
  проверит текущий CLI naming contract. Реализация точного нового или
  изменённого имени input mode всё ещё требует owner approval в момент
  implementation (PUBLIC CLI SURFACE tripwire).
- **risk boundary:** **PUBLIC CLI SURFACE → отдельный owner approval в момент
  implementation.** Слайс **не** destructive; 6D/6E им не требуются.
- **тесты deep-dive:** T9.
- **required verification:** targeted + smoke (существующими командами) +
  `full`.

#### PLAN-9B-4 — truthful source/script behavior (CRITICAL-2, часть 2)

- **status:** pending · **зависимости:** PLAN-9B-5a (выполняется вместе или
  сразу после — иначе пользователь теряет offline-путь подачи материала).
- **цель:** для factual strict workflow `topic` = **intent, не usable source
  material**. Запрещённая цепочка `topic → insufficient source →
  LegacyTemplate → validation passed → production success` перестаёт
  существовать. При недостаточном материале — truthful blocking state
  `insufficient_source_material`.
- **reuse — новых сущностей не создаётся:** `allow_legacy_fallback` ·
  `ScriptValidationResult` · `script_provider` · `fallback_reason` ·
  `script_metadata`. **`content_origin` не создаётся** (OD-18): информация уже
  выражена существующими полями, дефект в том, что их **никто не читает**.
- **`LegacyTemplateScriptProvider` не удаляется.** Он остаётся эталоном
  регрессии и воспроизводимости старых проектов; разрешён только явным режимам
  `template` / `demo` / `test` / `draft`. Меняется условие его **молчаливого**
  вызова, а не он сам.
- **AI research не добавляется** (OD-17).
- **тесты deep-dive:** T6, T7, T8.
- **открытый вопрос:** backward compatibility со старыми persisted проектами,
  где `script_provider == "legacy_template"` — проверяется в этом слайсе.
- **risk boundary:** наблюдаемое поведение `strict` → **owner approval**.
- **required verification:** targeted + `full`.

#### PLAN-9B-2 — expansion + hardcode migration

- **status:** pending · **зависимости:** PLAN-9B-4, **PLAN-6D**, **PLAN-6E**.
- **цель:** контролируемая лестница расширения плюс снятие topic-specific
  hardcodes из shared engine.
- **лестница запросов:** точный субъект → субъект и действие → субъект,
  действие и локация → синонимы → альтернативные названия сущности → более
  широкий, но не меняющий смысл контекст → другой допустимый визуальный план
  той же идеи. **Предваряется источником provider-языка (9B-1):** без него
  лестница расширяет ноль.
- **salvage knowledge, без восстановления старого pipeline:** legacy
  `build_query_variants` expansion ladder (через PLAN-L0) · semantic query
  ladder `exact → broad → environment → atmospheric` · orca `provider_queries`
  (трёхуровневая структура «точный субъект → группа → среда») · `must_avoid`
  как часть смысла запроса.
- **topic-hardcode inventory — PROVISIONAL.** Число файлов **не фиксируется как
  invariant**: это измерение, а не контракт.
- **порядок обязателен:** replacement working → callers migrated → targeted и
  `full` зелёные → reviewer/gates → **затем** retirement. Удаление любого
  hardcode до переноса полезной capability запрещено.
- **`[HARD]` gate неприкосновенен:** снятие topic-литералов, живущих внутри
  safety gate `modes.blocking_reasons`, требует отдельного обоснования и **не**
  является разрешением менять сам gate.
- **тесты deep-dive:** — (T3 перенесён в PLAN-9B-1 вместе с исправлением
  `source_is_latin`, registry C36; тест не потерян и нового тестового этапа не
  создаётся).
- **risk boundary:** multi-owner diff + persisted содержимое visual plan +
  destructive → **PLAN-6D + PLAN-6E + reversible retirement**.
- **required verification:** targeted + `full`.

#### PLAN-9B-3 — query-path cleanup

- **status:** pending · **зависимости:** PLAN-9B-2, **PLAN-6E**.
- **выполняется только ПОСЛЕ работающей замены.**
- **кандидаты на retirement** (ни один не удаляется раньше переноса уникального
  knowledge и всех callers): obsolete GLOSSARY matcher · orca topic hardcode ·
  `legacy_broad_query` · deprecated `make_stock_query` · superseded semantic
  `query_generator` — **только после миграции всех callers**.
- **risk boundary:** destructive retirement → **PLAN-6E + reversible retirement
  mechanism** (annotated tag + внешний `git bundle` + строка `Retired`).
- **required verification:** targeted + `full`.

#### PLAN-9B-5b — retirement `apps/news_to_short`

- **status:** pending · **зависимости:** PLAN-9B-5a **и** миграция всех
  callers; **PLAN-6D**, **PLAN-6E**.
- **порядок обязателен: capability сначала мигрируется, wrapper удаляется
  только потом** (OD-2, OD-19, registry K08, C42).
- **capability parity check — обязателен перед retirement (2026-08-01).**
  Список уникальных возможностей wrapper'а в прежней редакции был неполон,
  поэтому перед удалением проводится полный parity inventory
  `apps/news_to_short`. Минимум уже известных возможностей:
  **A.** named source-text input (`--text` / `--text-file`) → canonical
  first-class source-material contract (PLAN-9B-5a);
  **B.** user supplied assets at project creation (`--assets` →
  `NewsJob.user_assets`) → либо мигрировать в canonical Content Creator create
  path, либо получить **явное owner decision** о намеренном retirement этой
  capability. [FACT] у канонического `create` доказанного эквивалентного
  create-time входа нет; второй носитель `pipeline.py --news-to-short --assets`
  умирает в PLAN-L4. **Молчаливо потерять `--assets` запрещено.**
  Точный public CLI для user-assets сейчас не проектируется: это
  implementation decision и public-surface tripwire.
- **разрешается только после:** parity inventory wrapper'а; миграции всех
  сохраняемых capabilities; миграции callers; PLAN-6D; PLAN-6E; reversible
  retirement; targeted + smoke + `full`.
- **risk boundary:** destructive retirement реализации, у которой есть callers
  (test-callers и собственный README) → **PLAN-6D + PLAN-6E + reversible
  retirement**.
- **required verification:** targeted + smoke + `full`.

### PLAN-9C — semantic decision wiring

- **status:** blocked (**PLAN-1C′** и закрытый C01-SEM; **PLAN-6E** —
  semantic decision boundary; фактическое наполнение даёт PLAN-9B) ·
  **commit:** —
- **порядок подтверждён (OD-22):**
  `provider-ready query → candidates → semantic/Vision → rank/select`.
  Подключать Vision к ранжированию кандидатов, которых ноль, бессмысленно.
- **исправлено ревизией 2.1 — механизм.** Формулировки «semantic не может
  влиять на selection» и «selection fingerprint запрещает rerank»
  **опровергнуты**. [FACT] metadata-semantic слой уже **ranks**, **rejects**,
  **blocks** и **может изменить выбранный asset** — доказано synthetic-пробой
  через живой ingestion seam. `_selection_fingerprint` — защитная
  самопроверка, а не вето.
- **фактическая проблема:** платный Vision-сервис пишет результат **поздно** — в
  review-манифест после цикла отбора — и **не подаёт evidence в decision layer
  до selection**.
- **цель:** **producer → existing semantic consumer wiring.** Target:
  `provider-ready candidates → Vision/semantic evidence → существующее semantic
  ranking → selection`. **Новый semantic stack не создаётся.**
- **отдельно зафиксированный дефект отчётности:** `_semantic_visual_summary`
  жёстко пишет `semantic_rerank_enabled=False` независимо от фактического
  конфига. Это дефект **отчётности**, а не решения; читателей этого поля из
  манифеста нет.
- **разрешённые зоны:** production asset selection path.
- **запрещено:** создавать второй visual planner, Vision stack или asset
  pipeline; изменять default-поведение в этом slice; **использовать mock
  semantic backend как влияющий на production selection** — mock допустим
  только в wiring-тестах и не является доказательством визуального качества.
- **измеримый результат:** wiring доказан тестами; default-конфигурация
  поведения не меняет.
- **required verification:** targeted selection/wiring tests + `full`, так как
  меняется shared production decision path.
- **rollback:** один commit.

### PLAN-9D — offline visual-quality evidence

- **status:** blocked (PLAN-9B, PLAN-9C) · **commit:** —
- **цель:** доказать улучшение decision path на уже имеющихся данных.
- **источники:** существующий live-eval dataset, уже сохранённые кадры,
  сохранённые результаты предыдущего Vision-прогона, вручную размеченные
  fixtures.
- **запрещено:** новые платные вызовы.
- **измеримый результат:** улучшение решения на известных данных
  зафиксировано; mock как доказательство не используется.
- **required verification:** targeted evaluation tests + offline product
  fixture gate; повторный `full` не нужен без изменения shared contract.
- **rollback:** один commit.

### PLAN-9E — controlled semantic activation

- **status:** blocked (PLAN-9D, PLAN-10C + owner approval) · **commit:** —
- **цель:** включить доказанный semantic decision path только для явно
  выбранного template/project policy.
- **implementation-time verification моделей (2026-08-01).** До первого
  разрешённого live/paid semantic/Vision вызова configured semantic/Vision
  model identifiers обязаны быть сверены с **фактическим provider/backend
  contract** и актуально поддерживаемыми model IDs: проверить configured model
  IDs; сверить их с provider contract; **fail closed** при unknown/unsupported
  model; не выполнять paid call при invalid или непроверенной model config.
  Точная network/provider validation требует owner approval на конкретное
  действие. До такой проверки **нельзя утверждать**, что конкретный model ID
  валиден или невалиден; это implementation-time verification, а не новый
  architecture finding и не новый PLAN-ID.
- **запрещено:** глобально включать paid backend, менять default всех старых
  проектов, использовать mock, ослаблять rights/`must_avoid`/misleading gates.
- **измеримый результат:** opt-in policy имеет безопасный fallback при
  отсутствии результата/бюджета/backend; старые проекты и default config
  сохраняют прежнее поведение; выбор и причина записываются в manifest.
- **required verification:** targeted policy/integration tests + `smoke` +
  `full` как общий activation gate.
- **rollback:** один commit.

### PLAN-10A — query/provider attempt ledger и stop reasons

- **status:** blocked (PLAN-9A) · **commit:** —
- **цель:** каждая попытка и остановка сохранена; best-so-far можно объяснить
  и продолжить после `resume`.
- **допустимые stop reasons:** исчерпаны разрешённые query variants; исчерпаны
  providers и pagination; достигнут budget; несколько итераций не улучшили
  best-so-far; следующий шаг требует отдельного платного разрешения; достигнут
  strict threshold. Бесконечный поиск запрещён.
- **required verification:** targeted persisted-contract tests + `full`.
- **rollback:** один commit.

### PLAN-10B — pagination и provider contract

- **status:** blocked (PLAN-10A) · **commit:** —
- **цель:** поиск не ограничен первой страницей результатов и фиксированным
  лимитом на пару provider × query.
- **граница:** сначала additive pagination/cursor contract и
  characterization старых adapters; затем каждый active provider переводится
  отдельным под-slice. Провайдер без pagination сохраняет bounded single-page
  adapter и честно сообщает exhaustion.
- **PLAN-10B не является owner provider-registry convergence (D-2).** Гипотеза
  «пять расходящихся реестров надо свести к `providers/registry`»
  **опровергнута**: это разные legitimate facts (actual constructed providers ·
  provider capabilities · fallback language info · source-class priority ·
  diagnostics inventory · availability), а `ProviderCapabilities.query_languages`
  **уже** имеет приоритет над fallback-таблицей. Остаточный cleanup:
  `local_library` declaration mismatch → **PLAN-10D**; вестигиальный
  `DEFAULT_PROVIDER_ORDER` и осиротевшее имя `unsplash` → opportunistic cleanup
  внутри слайса, который и так трогает routing. Отдельный PLAN-ID не создаётся.
  Ответственность PLAN-10B — **pagination / provider exhaustion / provider
  contract behavior**, и загружать её чужой работой запрещено.
- **required verification:** contract-foundation — targeted + `full`; каждый
  provider adapter — targeted; один итоговый `full` при закрытии family.
- **rollback:** один commit на contract и один на provider-family.

### PLAN-10C — adaptive budget и plateau policy

- **status:** blocked (PLAN-9B, PLAN-10B) · **commit:** —
- **цель:** политика `quick` / `standard` / `deep` вместо одного фиксированного
  лимита. Бюджет учитывает важность и длительность сцены, сложность субъекта,
  число новых уникальных кандидатов, улучшение best-so-far, число providers,
  стоимость вызовов, strict или draft mode.
- **владеет порядком эскалации** за пределами query variants: исчерпаны
  разрешённые запросы → локальная медиатека → другой provider → разрешённый
  fallback. Эти ступени сняты с PLAN-9B, потому что относятся к
  routing/completion policy, а не к генерации запросов. Включение локальной
  медиатеки остаётся за PLAN-10D и его аудитом, provider contract — за
  PLAN-10B; PLAN-10C определяет только момент перехода и его причину.
- **измеримый результат:** поиск продолжается, пока улучшает best-so-far;
  plateau останавливает; одна сложная сцена не останавливает остальные, не
  удаляет найденные assets, не сбрасывает проект и не блокирует reviewable draft.
- **запрещено:** случайный нерелевантный asset ради `completed`, misleading
  visual, `must_avoid` conflict, нарушение rights, ложный `publish_ready`.
- **required verification:** targeted policy tests после каждого slice;
  `full` один раз при закрытии adaptive-search family.
- **rollback:** один commit.

### PLAN-10D — convergence глобальной локальной стоковой библиотеки

- **status:** blocked (PLAN-10C + аудит) · **commit:** —
- **переформулирован ревизией 2.1.** Прежняя цель «регистрация
  `LocalLibraryStockProvider` в автоматическом поиске» была слишком узкой, а
  формулировка «три независимых LocalLibrary implementation» — **неверной**.
- **[FACT], установленные Secondary Deep Dive:** один `media_index` · один
  rights-authority `apply_policy_to_candidate` · **два** matcher'а · несколько
  consumers/wrappers; legacy path #3 использует **ту же**
  `media_library.search_local_assets`, что и path #1. Аргумент про
  `RIGHTS_REFERENCE_ONLY` **опровергнут**: интерим-значение перезаписывается
  политикой.
- **[FACT] ровно два доказанных расхождения live local-library путей:**
  1. missing `provenance`;
  2. `review_required=True`.
  Обратных расхождений — **ноль**.
- **scope — только GLOBAL LOCAL STOCK LIBRARY.** Соседние legitimate
  capabilities **не объединяются и в конвергенцию не входят**:
  - user/manual project assets (`--assets`);
  - project pool уже скачанных в проект ассетов;
  - глобальная локальная стоковая библиотека — **это и есть scope PLAN-10D**.
- **цель:**
  1. определить canonical matcher / provider boundary;
  2. harmonize provenance и review semantics;
  3. salvage **diversity reserve** из legacy (`min_local_diversity_per_scene` /
     `reserved_download_slots`, через PLAN-L0) — прямо релевантен проблеме
     повторяющихся визуалов; современного эквивалента нет;
  4. удалить superseded wrappers/path после переноса knowledge и callers;
  5. **не создать четвёртый путь.**
- **сопутствующие записи:** `query_adapter` объявляет `local_library`
  провайдером с поддержкой русского, чего не происходит, — declaration mismatch
  закрывается здесь (а не в PLAN-10B). `duplicate_penalty` в
  `rank_local_assets` — фактически **мёртвый код** (`used_asset_ids` вызывает
  `continue` раньше применения penalty); убирается вместе с этим bounded
  слайсом и отдельным PLAN не становится.
- **не смешивать с C50.** Fail-open на явном `review_required=True` — отдельный
  rights correctness defect и отдельный bounded fix, не часть architectural
  convergence.
- **deadline C50 (2026-08-01).** Новый top-level PLAN-ID не создаётся; C50
  остаётся отдельным bounded rights-fix слайсом и может быть выполнен
  независимо после зелёного PLAN-4, когда его bounded scope и tests
  подтверждены. Но как `[HARD]` rights correctness он **обязан быть CLOSED**:
  (1) до расширения / convergence / повторного включения Global Local Library
  в PLAN-10D; (2) до финального product evidence PLAN-11 / M1; (3) до любого
  live/publish-ready workflow, реально способного использовать Global Local
  Library asset с policy normalization. PLAN-9E искусственным owner C50 не
  делается — semantic activation и rights correctness разные
  responsibilities; если PLAN-9E фактически использует LocalLibrary
  publish-ready path, общий `[HARD]` rights gate применяется и без добавления
  формальной dependency.
- **открытый вопрос:** нужно ли вообще регистрировать `local_library` как
  `StockProvider` — решается по исходу конвергенции.
- **измеримый результат:** одна canonical local-library capability без
  расхождений в rights/provenance; diversity reserve сохранён; четвёртый путь
  не создан; при отрицательном решении о регистрации registry не усложняется.
- **required verification:** при изменении shared provider registry —
  targeted + `full`; для решения `defer/reject` — docs QA.
- **rollback:** один commit.

### PLAN-11 — multi-topic product evidence

- **status:** blocked (PLAN-9E, PLAN-10C) · **commit:** —
- **scope:** текущий automatic asset-search path относится прежде всего к
  `fullscreen_voiceover_v1`. `story_card_text_only_v1` сейчас требует
  явный local `source_asset`; PLAN-11 не выдаёт улучшение одного workflow за
  доказательство качества всех templates.
- **примечание о зависимости:** PLAN-10D не является обязательным условием
  M1, если аудит не доказал ценность/безопасность локальной библиотеки.
  Evidence запускается после каждого product slice на сохранённых fixtures;
  итоговый multi-topic gate не является первой проверкой результата.
- **early multi-topic regression (OD-25).** Первая проверка на разных доменах
  **не ждёт PLAN-11**: после каждого существенного product slice, где это
  релевантно, проверяются репрезентативные темы минимум из разных классов —
  animals/wildlife · energy/technology · geography/infrastructure. PLAN-11
  остаётся финальным product evidence gate, но **не первой** multi-topic
  проверкой.
- **PLAN-11 как EVIDENCE GATE ложных product capabilities.** Требование «нет
  ложного `publish_ready`» расширяется до «каталог не обещает несуществующий
  output». [FACT] catalog объявляет **5** active export targets, тогда как три
  production-owner согласованно работают с **3**; `supported_export_targets` и
  `safe_zone_profile` в render decision **не участвуют** (ноль production-
  читателей), то есть каталог — единственный outlier.
  **Цель — truthful catalog.** Создавать бессмысленные byte-identical
  TikTok/Stories outputs только ради соответствия каталогу **запрещено**.
  **PLAN-11 не является implementation owner:** у него `required verification:
  product gate`, `rollback: —` и нет allowed zones для source. Implementation —
  будущий небольшой bounded `production_catalog` slice, который либо убирает
  несуществующие targets из `active`, либо переводит их в `planned`, в
  зависимости от фактического intended product contract на момент
  implementation. Нового PLAN-ID не создаётся.
- **три reference domains:**
  1. животные и строгий контекст среды: кит или косатка в открытом океане;
     бассейн, шоу и трибуны исключены;
  2. энергетика и технологии: солнечная электростанция, аккумуляторное
     хранилище, энергосеть;
  3. география и инфраструктура: строительство крупного канала через пустыню;
     точные карты, satellite imagery и infographic допустимы, если правдивее
     случайного видео.
- **gate не использует единый глобальный процент видео.** Соотношение
  video / still / infographic определяет template policy.
- **общие требования:** все обязательные сцены имеют безопасный usable visual;
  ноль `must_avoid`; ноль misleading conflicts; ноль нарушений
  rights/provenance; нет новых topic-specific hardcodes; best-so-far и
  rejection evidence сохранены; `resume` не ухудшает результат.
- **M1:** 0 USD, ноль новых платных Vision-вызовов.
  По умолчанию M1 использует сохранённые/local fixtures; новый provider search,
  download или иной сетевой вызов требует отдельного разрешения даже при
  нулевой стоимости.
- **M2:** бюджет платных вызовов — **TBD, owner approval before M2**. Числовые
  лимиты не согласованы и здесь не фиксируются.
- **M3:** `strict` выставляет `publish_ready=true` только после реальной
  визуальной проверки. Бюджет не утверждается до анализа M2.
- **required verification:** product gate. **rollback:** —

### PLAN-12 — классификация и архивирование документации

- **status:** blocked (PLAN-1B) · **commit:** —
- **изменено ревизией 2.** Прежний блокер «PLAN-1» больше не существует: PLAN-1
  разделён на capability gates. **Вся family PLAN-12 не блокирует первый
  product slice** — она выполняется параллельно или после PLAN-9A. Внутренняя
  последовательная цепочка `12E → 12A → 12B → 12C` сохраняется без изменений.
- **добавлено в PLAN-12B (перенесено из PLAN-1C):** пофайловая классификация
  `docs/implementation` (96 файлов), `docs/audits` (9), `docs/architecture` (5),
  `docs/apps` (3) — registry C27, C28. PLAN-9A её не требует.
- **порядок внутри этапа:** `12E → 12A → 12B → 12C`.
  **Буквы под-slices — идентификаторы, а не порядок выполнения.** Цепочка
  последовательная: каждый под-slice зависит от **непосредственно
  предыдущего** звена, а не от 12E напрямую. Пропуск звена запрещён.
  Существующие ID не переименовываются.
- **цель:** current navigation ведёт только к актуальным документам.
- **bounded sub-slices** (перечислены в порядке выполнения):
  - **PLAN-12E — document ownership model.** *Выполняется первым внутри
    PLAN-12.* **Зависимости: PLAN-1B.**
    Решение владельца от 2026-07-31: принято **направление B** —
    `current` (волатильное состояние и активные планы) / `architecture`
    (долговечные границы) / `product` (цель, quality, evaluation) /
    `runbooks` (операционные пути запуска) / `adr` / `archive` /
    `implementation`.
    **Направление — это ownership *direction*, а не разрешение перемещать
    конкретные файлы.** Все размещения ниже — candidate, не назначение:
    - `docs/apps/*` — candidate source для `docs/runbooks/`; exact per-file
      migration только после PLAN-12B evidence; каталог не архивируется;
    - `docs/architecture/visual_rendering_policy.md` — candidate source для
      `docs/product/QUALITY_BAR.md`; move/extract только после подтверждения
      PLAN-12B, что competing quality owner не существует (registry C23);
    - `docs/contracts/*` — target responsibility решается **по содержимому
      каждого файла**, не автоматически по каталогу (registry C22);
    - `SYSTEM_MAP.md` — target `docs/architecture/` принят концептуально;
      физический move выполняется только вместе с обновлением всех callers
      в соответствующем bounded slice.
    Категории `architecture/`, `apps/` и `contracts/` не удаляются ради
    меньшего числа каталогов. Число каталогов и число Markdown-файлов
    метриками качества не являются. Критерии — один canonical owner на
    responsibility, понятный lifecycle, отделение current от historical,
    отделение runtime data от source, сохранность product knowledge,
    тематичность документов и создание нового owner только при доказанной
    необходимости.
    *Измерение Foundation audit, не gate:* `docs/current/` — 2639 строк, из
    них 1616 (61%) приходится на два волатильных плановых документа.
    Разрешённые зоны: только `docs/current/CLEANUP_REGISTRY.md` и этот файл.
    Никаких move в этом под-slice.
  - **PLAN-12A — current docs. Зависимости: PLAN-12E.** Перенести уникальные
    подтверждённые данные `ARCHITECTURE_BOUNDARY_MAP.md` в `SYSTEM_MAP.md`,
    затем удалить current-копию; убрать дубли CURRENT_STATE/START_HERE.
    `docs/current/PRODUCT_EVIDENCE_GATE.md` **обязан переехать**, а не просто
    сменить `status`: [FACT] пять его `source_paths` указывают внутрь
    gitignored `projects/`, поэтому его evidence неверсионируемо и файл не
    может остаться в `docs/current/`.
    После слияния `SYSTEM_MAP` ← `ARCHITECTURE_BOUNDARY_MAP` **измерить
    результат как measurement**. Решение о `RUNTIME_FLOWS` принимается по
    качественным критериям, а не по числу строк — см. отдельный пункт
    «`RUNTIME_FLOWS` — CONDITIONAL NEW OWNER CANDIDATE» ниже.
  - **PLAN-12B — данные внутри docs. Зависимости: PLAN-12A.** Перенести
    production/evaluation fixtures из `docs/implementation` в versioned
    fixture/data owner и обновить callers; paid evidence сохранять без
    переписывания истории.
  - **PLAN-12C — archive. Зависимости: PLAN-12B.** `PROJECT_RESCUE_MASTER_PLAN.md`
    и подтверждённо исторические plans/audits/reports переместить в
    `docs/archive`, обновив navigation и links.
    **Не начинается, пока не закрыты 12E, 12A и 12B:** archive/move без
    утверждённой модели владения и без выполненных предшествующих шагов
    запрещён.
    Персональные ограничения состава:
    - `docs/architecture/visual_rendering_policy.md` — **временно защищён от
      archive и delete** до подтверждения PLAN-12B, что competing quality
      owner не существует (registry C23);
    - `docs/architecture/localization_and_voice_architecture.md` — **не
      объявляется заранее ни `keep`, ни archive-кандидатом**: DEFER вместе с
      остальными `docs/architecture/*` до полного per-file evidence
      (registry C28);
    - состав `docs/implementation`, `docs/audits`, `docs/architecture` и
      `docs/apps` — **DEFER до PLAN-12B** (registry C27).
- **`RUNTIME_FLOWS` — CONDITIONAL NEW OWNER CANDIDATE.** Не «justified».
  Создаётся только при выполнении всех пяти условий: пофайловая классификация
  `docs/*` завершена (PLAN-12B, ревизия 2 — прежде PLAN-1C);
  фактические runtime-flow sources прочитаны полностью (`docs/apps/*`,
  `COMMANDS.md` §10, `skills/resume-project`, `skills/create-short-video-first`,
  ADR 0006); PLAN-12A выполнил merge; итоговый `SYSTEM_MAP` измерен как
  measurement; **качественно** доказано, что runtime execution / stage /
  resume / failure information не помещается туда без смешения
  ответственности. Если после merge `SYSTEM_MAP` остаётся тематичным и его
  ответственности не смешиваются — новый owner не создаётся, независимо от
  числа строк.
- **действия по классам:** keep, move, archive, backup_then_untrack, delete,
  defer. Целое семейство одним действием не архивируется и не удаляется.
- **запрещено:** untrack двенадцати reference jpg до переноса dataset;
  переписывать historical snapshot как current; оставлять битые ссылки;
  начинать 12C раньше закрытия 12E/12A/12B; трактовать буквенную нумерацию
  под-slices как порядок выполнения.
- **required verification:** PLAN-12E — docs QA; PLAN-12A/12C — docs QA;
  PLAN-12B — targeted production callers + `full`; `git diff --check` всегда.
- **rollback:** один commit на семейство.

### PLAN-13 — ownership migration, retirement и root-structure classification

- **status:** blocked (PLAN-1B) · **commit:** —
- **изменено ревизией 2.** Блокеры PLAN-6C и PLAN-12 сняты как механические:
  прямой зависимостью является только capability gate PLAN-1B. **PLAN-9A не
  блокирует.** Значительная часть прежнего scope PLAN-13D переехала в PLAN-L.
- **цель:** один owner бизнес-логики, один установленный package root и один
  канонический CLI без потери compatibility/persisted contracts.
- **root-structure classification (OD-6, OD-9) — новый обязательный под-slice
  PLAN-13E, выполняется до любого move.** Старое допущение «существующий path —
  аргумент сохранить path» отменено; locked decisions 8 и 9 больше не запрещают
  пересмотр. Но переносить ради эстетики запрещено: **сначала классификация пяти
  групп, потом решение.**

  | Группа | Что известно | Действие |
  |---|---|---|
  | `channels/` | после L3 остаются `nature_science_news_ru` (активный) и `nature_pulse` | классифицировать вместе с template policy |
  | `schemas/` | 8 versioned contracts, читаются `test_artifact_schemas` | классифицировать |
  | reusable templates | `config/render_presets/`, `channels/*/templates/`, versioned SVG | классифицировать |
  | evaluation resources | live-eval dataset/results/frames — registry C31 | классифицировать; `docs/` подтверждён неправильным owner (OD-8) |
  | versioned assets/config | [FACT] после L3 все 5 оставшихся файлов `config/` активны, 8–21 caller каждый | **оставить на месте**, отдельной причины двигать нет |

  **Top-level `resources/` заранее не создаётся (OD-9).** Решение принимается по
  результату классификации и только если `resources/` реально уменьшает число
  owners и делает структуру понятнее. `resources/evaluation/` — candidate path,
  не назначение.
- **PLAN-13E также назначает physical target для C31** и переводит caller
  `src/assets/semantic_visual_evaluation_tooling.py:26,38,695` плюс
  `tests/test_semantic_decision_policy.py`, освобождая `docs/` от production
  dependency. Синтетический генератор
  `tests/test_semantic_visual_evaluation.py:458 _write_prepared_dataset` уже
  существует и повторно не создаётся.
- **applications против developer tools.** Это разные responsibilities:
  `apps/*` и `anime_factory/` — applications; `tools/` — developer tooling, QA,
  диагностика и maintenance. `anime_factory` остаётся **migration source**
  будущего `video_repurposer` (ADR 0016), а не постоянной параллельной
  архитектурой приложения; его runtime (`episodes/`, `input/`, `config.yaml`)
  живёт внутри source tree и переезжает во внешний workspace.
  `apps/news_to_short` вторым CLI не остаётся (OD-2, registry K08).
- **bounded sub-slices:**
  - **PLAN-13A — caller migration:** одно семейство production callers, затем
    current docs/examples, затем tests;
  - **PLAN-13B — ownership transfer:** переносить implementation, не
    копировать; Fullscreen, Story Card, Anime, projects, assets/providers,
    audio/music, subtitles и rendering — разные commits.
    **Orchestration finding (D-3, ревизия 2.1) — разделён на две
    ответственности; формулировка «два конкурирующих orchestration owner»
    опровергнута.** ADR 0009 **намеренно** разделяет application orchestration
    и news pipeline ownership.
    - **A. Точный idempotency contract defect.** [FACT] explicit `stage=` path
      отключает output-validated idempotency ADR 0006 через условие
      `and not stage`; batch-режим (`until_stage=`) idempotency **соблюдает**,
      explicit-режим повторно исполняет завершённые локальные стадии. Контракт
      для `stage=` не покрыт ни одним тестом. Owner — **ADR 0006 /
      `src/news/pipeline.py`**, отдельный будущий bounded slice.
      **Severity: MEDIUM.** [FACT] повторного платного TTS аудит **не
      обнаружил**: существуют несколько независимых guard'ов и существующие
      тесты; повторяются только локальные preview/final render.
      Вызовов — **4–7** в зависимости от режима, не «ровно 7».
    - **B. Возможная поздняя orchestration convergence.** Owner — PLAN-13B,
      **только если** после исправления contract остаётся архитектурная
      необходимость. «Один orchestration owner» **не** является уже принятым
      решением; правильный target — один контракт идемпотентности, действующий
      во всех режимах вызова.
    - **обязательное предусловие любой из двух работ:** подтвердить фактических
      `resume` / `force-stage` / `stop-stage` callers и публичное поведение до
      изменения — условная логика существует ради сосуществования двух режимов;
- **HIGH-3 (channel/project formats) — новый этап не создаётся.** Несколько
  форм канала и две системы проектов покрыты существующими **PLAN-1B** и
  **PLAN-13** (M02, C10, PLAN-13E). Позже: inventory channel formats → inventory
  project/state formats → tolerant readers → migrate callers → delete
  transitional duplicates. **Prerequisite текущих search/input fixes это не
  является;**
  - **PLAN-13C — wrapper/package retirement:** один wrapper/package family
    после zero-production-caller gate и dependency/toolchain audit PLAN-6C;
    root `ai_youtube/` и `src/ai_youtube/` свести к одному installable
    src-layout package;
  - **PLAN-13D — legacy pipeline: перенесён в PLAN-L ревизией 2.** Весь его
    прежний scope — сохранение maintenance-команд (теперь PLAN-L2), удаление
    `pipeline.py` (PLAN-L4), снятие production-импорта `scripts.test_moss_voices`
    (PLAN-L4, registry C18) — выполняется в параллельном этапе PLAN-L, потому
    что ждать здесь было незачем: у legacy-стека ровно один production-caller.
    Здесь под-slice сохранён как якорь ссылок и собственного содержания не имеет.
  - **PLAN-13E — root-structure classification:** см. выше в этом разделе.
- **предусловие удаления любого старого entrypoint:** переведены или удалены
  tests, актуальные docs, console scripts, module entrypoints и подтверждённые
  внешние callers в том же изменении. Красные tests или лгущая документация
  после retirement недопустимы.
- **измеримый результат:** один physical package root и один канонический CLI.
- **запрещено:** смешивать caller migration, ownership transfer, runtime
  migration и cleanup в одном diff.
- **required verification:** targeted contract + ближайший integration smoke;
  `full` на package/shared-contract boundaries.
- **rollback:** один commit на семейство.

### PLAN-14 — repository/runtime minimalism и переносимость

- **status:** blocked (PLAN-6B, PLAN-6C, PLAN-12, PLAN-13) · **commit:** —
- **цель:** кодовый репозиторий содержит только source/config/tests/versioned
  docs, а runtime/toolchain/user data имеют явных владельцев вне code root.
- **Anime Factory: два разных предмета, смешивать запрещено (OD-23,
  ревизия 2.1).**

  | Предмет | Классификация | Owner |
  |---|---|---|
  | Anime Factory **capability** | **PRESERVE FOR FUTURE PRODUCTIZATION** — source implementation будущего `video_repurposer`, **не** disposable legacy | post-UI roadmap; запись — PLAN-8, преждевременной миграции в PLAN-13 нет |
  | Anime **runtime внутри source repo** (`input/`, `episodes/`, `artifacts/`, `outputs/media`) | **FIX LATER VIA WORKSPACE** — дефект расположения runtime | **PLAN-14**, registry C15 |

  `enabled=False` / `implementation_status="planned"` **не является
  доказательством ненужности**: capability выключена, а не отвергнута (усиление
  locked decision 5). Productize Anime сейчас не нужно; deep audit Anime
  Factory идёт **после** UI Content Creator.
- **bounded sub-slices:**
  - **PLAN-14A — финальный minimalism QA:** повторно запустить и при
    необходимости усилить созданный в PLAN-6B
    `tools/qa/check_repository_minimalism.py`; сравнить результат с ранним
    baseline и закрыть только подтверждённые нарушения. Orphan/duplicate —
    review evidence, не автоматическое разрешение удалить;
  - **PLAN-14B — dependency/toolchain convergence:** реализовать решения
    аудита PLAN-6C: `pyproject.toml` — владелец direct dependencies,
    `requirements.lock` — проверенный lock; `requirements.txt` оставить,
    генерировать или удалить только по зафиксированному caller/docs gate.
    Anime/ML optional dependencies, `venv/`, MOSS/Whisper/model weights и
    agent-specific adapters имеют раздельных owners. Обновление lock/download
    требует отдельного network approval.
    За 14B остаётся distribution boundary `tools/` (registry C26).
    **Изменено ревизией 2:** installed-package defect C25,
    `scripts/test_moss_voices.py` C18 и hardcoded `G:/` C24 закрываются в
    PLAN-L, потому что их носители (`pipeline.py`, `scripts/`,
    `config/video_style.json`, `channels/psychology/`) там удаляются. Здесь они
    не дублируются; 14B только проверяет, что после L4 в выжившем versioned
    config не осталось hardcoded drive;
  - **PLAN-14C — generated/cache/empty directories:** удалять только
    воспроизводимые cache/temp и подтверждённо пустые runtime directories по
    проверенному абсолютному пути; пустой `__init__.py` не мусор;
  - **PLAN-14D — runtime inventory и отбор representative corpus.**
    **Переписан ревизией 2 (OWNER: тестовое медиа disposable).** Inventory
    counts, manifests, project/media/model/toolchain roots и target workspace —
    как раньше, ничего не копируя и не удаляя. **Добавлено:** классификация и
    дедупликация 749 legacy JSON-манифестов (registry C32) по `schema_version`,
    manifest shape, completion state, resume state, legacy edge case и
    malformed/partial; отбор **минимального representative corpus**,
    достаточного tolerant-reader tests. Полный набор — во внешний retirement
    bundle как historical evidence. **749 файлов не становятся permanent
    architecture anchor.** Checksum-верификация применяется только к
    отобранному корпусу;
  - **PLAN-14E — workspace migration.** **Переписан ревизией 2.** Прежний
    `copy → verify counts/manifests/checksums → switch` для всего дерева
    заменён на: сохранить отобранный corpus, `media_index.json`, versioned SVG
    и, если нужно, минимальный voice sample с provenance (OD-3) → создать
    внешний workspace → переключить default → удалить disposable медиа.
    Выполняется только по отдельному owner approval; dual-read legacy roots
    сохраняется.
    **`MOSS_TTS_Nano/` не переносится (OD-7):** это цельный вендоренный
    сторонний репозиторий, а Runtime Workspace не является хранилищем исходного
    кода. Он ретайрится в PLAN-L4 вместе с `src/tts_providers/` после Knowledge
    Salvage Gate;
  - **PLAN-14F — root allowlist и правила `.gitignore`:** по одному top-level
    family за commit; tracked source, runtime/user data и generated output
    классифицируются раздельно.
    **Разрешённые зоны включают `.gitignore`** — это единственный slice,
    которому оно разрешено. Причина: `.gitignore` описывает именно root
    allowlist, а C20 и C21 — правила о top-level путях. **PLAN-6B остаётся
    detector/report-only owner и `.gitignore` не правит**; молчаливое
    превращение report-слайса в mutation-слайс запрещено. Нового PLAN ради двух
    правил не создаётся.
    Здесь исполняются exit conditions:
    (a) **C21** — директорное правило `assets/broll/` заменяется на
    `assets/broll/*`, после чего `git ls-files -i -c --exclude-standard` не
    содержит `.gitkeep`;
    (b) **C20** — `output/` и `tmp/` получают правила `.gitignore`. Удаление
    самих untracked артефактов в commit не входит и выполняется отдельно
    (PLAN-14C для воспроизводимого cache/temp), потому что untracked-файлы
    Git-состояние не меняют.
    **Изменено ревизией 2:** 8 × `outputs/*.json` (C19) и
    `outputs/asset_library_report.md` (C29) снимаются с Git в **PLAN-L4**
    вместе с их producer `pipeline.py --asset-report`, поэтому здесь остаётся
    только `assets/broll/.gitkeep` (C21) и остаток root allowlist. Обратить
    внимание: `src/media_library.py` при этом **сохраняется** — он используется
    активным news-путём;
- **измеримый результат:** report-only QA зелёный по утверждённому allowlist;
  runtime default не зависит от repo root/drive; сохранён именно
  `Preserved runtime corpus`, а не всё дерево runtime.
- **required verification:** targeted paths/contracts; `full` после path/
  package/toolchain changes; без реального render и сети.
- **rollback:** один commit на под-slice; data copy не совмещается с source
  retirement.

### PLAN-15 — final rescue acceptance

- **status:** blocked (PLAN-11–PLAN-14) · **commit:** —
- **цель:** доказать чистоту, понятность и переносимость, а не только закрыть
  строки плана.
- **обязательные проверки:**
  - clean Git и отсутствие незаписанного handoff;
  - docs QA, repository minimalism QA, smoke, fast и full offline;
  - canonical CLI и installed package из произвольного temporary checkout/path
    без hardcoded username/drive; сеть не требуется;
  - один owner на capability, один package root/CLI, закрытые wrappers и
    отсутствие доказанных duplicate implementations;
  - старые persisted projects/manifests читаются tolerant readers;
  - runtime/user media counts/checksums не ухудшились;
  - product gate M1 и честный active/planned/disabled catalog.
- **измеримый результат:** `CURRENT_STATE.md` описывает фактический финальный
  продукт; `CLEANUP_REGISTRY.md` не содержит бессрочных переходных состояний
  без owner evidence; post-rescue roadmap для `video_repurposer` и
  longform/documentary находится в `PRODUCT_PLAN.md`, а не в placeholder-коде.
- **required verification:** все перечисленные offline checks.
- **rollback:** финальный docs/checkpoint commit; проблемный implementation
  откатывается по его собственному bounded commit.

## Результат после каждого этапа

Это краткая карта состояния, а не второй набор критериев готовности. Полные
gates и проверки остаются в соответствующих разделах выше.

| После этапа | Что фактически получаем |
|---|---|
| PLAN-0 | Один активный versioned execution plan на отдельной локальной ветке. |
| PLAN-1D-routing | Новый агент попадает в этот план, а не в historical master plan. |
| PLAN-1C′ | Закрыт C01-SEM: у asset/semantic capability известны owner, callers, persisted contracts, дубли и тесты. Снят один из двух gates PLAN-9A и PLAN-9C. |
| PLAN-1A / PLAN-1B | Capability gates для PLAN-L и PLAN-13; product-работу не блокируют. |
| PLAN-L | Legacy content stack ретайрен после Knowledge Salvage Gate: −~5700 строк, −6 тестов, −6 top-level путей; закрыты C17, C18, C19, C24, C25, C29; знание сохранено, retirement обратим. |
| PLAN-2 | Исправленные voice-profile fixtures без изменения рабочего production resolver. |
| PLAN-3 | Исправленные completion/resume fixtures, соответствующие output-validated idempotency. |
| PLAN-4 | Зелёный и воспроизводимый полный offline baseline на зафиксированном source HEAD. |
| PLAN-5 | Один test runner с режимами `smoke`, `fast`, `targeted`, `full`; локальные проверки и offline CI используют одну командную модель. **Параллелен PLAN-9B.** |
| PLAN-9B-0 / 9B-1 | **Первый product-этап:** зафиксировано фактическое поведение до правки; произвольная тема получает несколько provider-ready queries без topic-hardcode, fail-closed сохранён. |
| PLAN-6A / 6D / 6E | Короткие единые правила с классами `[HARD]/[ARCH]/[HINT]`, приоритет цели над предписанным методом, технический scope-контроль и один независимый read-only reviewer, ловящий в том числе «unmet objective / premature stop». 6A параллелен; 6D — gate первого multi-owner слайса; 6E — gate первого destructive слайса, плюс PLAN-9A и PLAN-9C. |
| PLAN-6B / 6C | Ранний отчёт о мусоре и дублях с зафиксированными кандидатами fitness-проверок; проверенная карта dependency/toolchain ownership. Параллельны product-работе. |
| PLAN-7 | README, COMMANDS и рабочие skills обучают только каноническому `python -m ai_youtube`; старые entrypoints пока лишь совместимы. |
| PLAN-8 | Отдельный `PRODUCT_PLAN.md` с приоритетами, evidence gates и roadmap двух engines; execution plan становится короче. |
| PLAN-9 | Честный источник сценария и канонический вход «исходный текст»; универсальные provider-ready queries без topic-hardcode; сохранение best-so-far, переносимое через resume; semantic evidence доходит до существующего decision layer и включается только opt-in. |
| PLAN-10 | Ограниченный и объяснимый search loop с ledger, stop reasons, pagination и adaptive budget; глобальная локальная библиотека сведена к одной capability с одной rights/provenance семантикой и сохранённым diversity reserve. |
| PLAN-11 | Проверенное offline M1 evidence на нескольких темах без новых платных Vision-вызовов и без ложных claims по Story Card; каталог не обещает несуществующий output. |
| PLAN-12 | Утверждённая модель владения документами (12E) фиксируется **до** любых archive/move; затем current docs содержат только актуальные знания, fixtures получают правильного владельца, а historical материалы находятся в archive. Порядок внутри этапа — последовательная цепочка `12E → 12A → 12B → 12C`. |
| PLAN-13 | Один владелец бизнес-логики на capability, один physical package root, один канонический CLI; классификация пяти групп root structure выполнена, решение о `resources/` принято по evidence, `docs/` свободен от production dependency. |
| PLAN-14 | Минимальный root allowlist, согласованные dependency/toolchain files и переносимый runtime workspace; сохранён отобранный representative corpus и versioned resources, disposable медиа удалено. |
| PLAN-15 | Финально доказанный чистый, понятный, переносимый offline-проект с честным catalog и закрытым cleanup registry. |

## Decisions and discoveries

Только новые факты, меняющие порядок или scope. Не журнал команд.

### Ревизия 2.1 плана, 2026-07-31

Источники: `CRITICAL_INPUT_SEARCH_DEEP_DIVE_2026-07-31.md` (контролируемые
offline-пробы под активным `network_guard`, ноль сети и денег),
`PROJECT_EXECUTION_PLAN_REVISION_2_1_PROPOSAL_2026-07-31.md` и
`SECONDARY_ARCHITECTURE_FINDINGS_DEEP_DIVE_2026-07-31.md`. При конфликте
Secondary Deep Dive исправляет Proposal 2.1.

- **[FACT]** единственный канал доставки provider-ready английского запроса —
  `visual_brief`, и заполняет его только topic-hardcode на одну тему. Следствие:
  произвольная тема получает ложный запрос, чрезмерное обобщение либо
  `translation_required`. Это CRITICAL-1 в исправленной формулировке: проблема
  **не** «ноль запросов» — отправляются **ложные** запросы, что хуже нуля.
- **[FACT]** `src/assets/semantic_selection/query_generator.py` **не участвует**
  в формировании remote-запросов; canonical boundary — `src/assets/
  query_adapter.py` (`build_scene_queries` / `build_slot_queries`). Allowed
  zone PLAN-9B ревизии 2 была ошибочной.
- **[FACT]** `Translator` / `def translate` / `to_english` — **0 commits** за всю
  историю: полноценного translate-слоя не существовало никогда, восстанавливать
  нечего. Английские `visual_keywords` в legacy `content/**` — **входные
  данные**, а не выход кода.
- **[FACT]** `topic → article["text"] == сама тема → thin input →
  LegacyTemplateScriptProvider → шесть фиксированных фраз →
  `script_validation == passed`; downstream не читает `script_warnings` /
  `fallback_reason`. Это CRITICAL-2. Как только CRITICAL-1 починят, шаблонный
  сценарий поедет в publish беспрепятственно, поэтому CRITICAL-2 идёт внутри
  той же цепочки PLAN-9B.
- **[FACT, исправлено 2026-08-01]** у `apps/news_to_short` **две** возможности
  вне явного контракта канонического `create`: (1) `--text` / `--text-file` —
  **именованный** source-text вход; функционально тот же downstream уже
  достижим как `create --pasted-script/--script-file` при default/legacy
  unspecified `content_input_mode`, поэтому PLAN-9B-5a даёт имя, валидацию и
  документацию, а не новый движок; (2) `--assets` — пользовательские ассеты при
  создании проекта (`NewsJob.user_assets`), **доказанного аналога в
  каноническом `create` нет**. Прежняя формулировка «единственная уникальная
  бизнес-возможность — `--text`/`--text-file`» **опровергнута**. PLAN-9B-5b не
  выполняется, пока не пройден capability parity check.
- **[FACT]** `ProviderQuery.source` попадает в persisted manifest, но схема
  типизирует сцены как свободные объекты без `enum`, поле не валидируется и
  **не имеет ни одного читателя**. E-2 закрыт: не schema-level change, tolerant
  reader не нужен. Байты манифеста при этом меняются → characterization 9B-0
  обязан зафиксировать `query_plan` до правки.
- **[FACT]** targeted, full и три smoke-команды исполнимы **сегодня** без
  PLAN-5 (проверено исполнением). PLAN-5 переведён в parallel для всех
  под-слайсов PLAN-9B.
- **[FACT]** зависимость `PLAN-6A → PLAN-6D` — **декларативная**: 6D-1/6D-2/6D-3
  не требуют, чтобы R1–R12 уже лежали в `AGENTS.md`.
- **[FACT]** synthetic-проба сменила выбранный asset через живой semantic
  ingestion seam. Формулировки «semantic не может влиять на selection» и
  «fingerprint запрещает rerank» **опровергнуты**: `_selection_fingerprint` —
  самопроверка. Проблема — платный Vision пишет результат поздно в review-
  манифест. Отдельно: `_semantic_visual_summary` жёстко пишет
  `semantic_rerank_enabled=False` — дефект отчётности.
- **[FACT]** double orchestration: ADR 0009 намеренно разделяет application и
  news pipeline ownership; вызовов 4–7 в зависимости от режима; реальный дефект
  — `and not stage` в `src/news/pipeline.py`, отключающий output-validated
  idempotency ADR 0006 в explicit-режиме, не покрытый ни одним тестом.
  Повторного платного TTS **нет** (несколько guard'ов + тесты). Severity
  снижена HIGH → MEDIUM.
- **[FACT]** LocalLibrary: один `media_index`, один rights-authority
  `apply_policy_to_candidate`, два matcher'а; legacy path использует ту же
  `search_local_assets`, что и канонический. Ровно два расхождения
  (`provenance`, `review_required`), ноль обратных. Формулировка «три
  независимых implementation» и аргумент про `RIGHTS_REFERENCE_ONLY`
  опровергнуты. **Новый дефект:** явный `review_required=True` может пройти
  канонический путь, потому что policy позднее сбрасывает исходный флаг —
  registry C50, класс `[HARD]`. Дополнительно: `duplicate_penalty` в
  `rank_local_assets` — мёртвый код.
- **[FACT]** provider registry: `local_library` не попадает в
  `ordered_providers`, таблицы корректно фильтруются по availability,
  `ProviderCapabilities.query_languages` перекрывает таблицу. Гипотеза «пять
  расходящихся реестров» **опровергнута**; PLAN-10B как owner конвергенции
  снят (E-5 закрыт отрицательно).
- **[FACT]** export: каталог объявляет 5 active targets, три production-owner
  согласованно работают с 3; `supported_export_targets` и `safe_zone_profile`
  имеют ноль production-читателей и в render decision не участвуют. Каталог —
  единственный outlier.
- **[FACT]** FFmpeg: concat выполняется с `-c:v copy` и **не перекодирует**;
  CRF 20 принадлежит duration-control mux и имеет документированную причину.
  Три lossy generations — при audio + ASS subtitles. Величина ущерба **никем не
  измерялась** — ни один аудит не рендерил.
- **[FACT]** subprocess-модулей, запускающих CLI мимо `network_guard`, на audit
  HEAD `adcbb19` — **12**, а не 7. Это measurement, не invariant.
- **[owner decision]** OD-11…OD-26, D-1, D-2, D-3 и E-13 приняты; см. «Owner
  decisions ревизии 2.1».
- **[owner decision]** PLAN-P0 не создаётся: evidence уже получено, тесты
  T1–T11 распределены по PLAN-9B слайсам.
- **[FACT]** `baseline_head` остаётся `fe2df5b`: ни один из трёх аудитов и ни
  ревизия 2.1 полный offline suite не запускали. Подменять `baseline_head`
  текущим HEAD запрещено до нового full baseline run в PLAN-4.

### Ревизия 2 плана, 2026-07-31

- **[FACT]** legacy content stack — `pipeline.py` → `src/legacy_pipeline/workflow.py`
  → 20 модулей корня `src/` (~4903 строки) — имеет **ровно одного**
  production-caller и 6 test-модулей из 112. `legacy/` (424 строки) не имеет ни
  одного Python-caller. Исключения, которые остаются: `src/media_library.py`
  (активный news-путь) и `src/utils.py` (`src/audio/tts/env.py`,
  `src/tts_providers/moss_tts_provider.py`). Это основание для раннего PLAN-L.
- **[FACT]** `src/legacy_pipeline/maintenance.py` — не legacy-генерация, а
  единственный CLI-доступ к visual-preview, semantic-backend,
  semantic-evaluation, semantic-visual, media-library и envato-manual;
  канонический CLI этих команд не имеет. Поэтому L2 обязателен до L3.
- **[FACT]** `channels/{psychology,quotes,survival,size_comparison}` и
  `content/survival/juliane_koepcke_001.json` читаются
  `tests/test_channel_profiles.py` и `tests/test_documentary_visual_engine.py` —
  это fixtures legacy-стека, а не user data. Registry N04 изменён.
- **[FACT]** `MOSS_TTS_Nano/` — цельный вендоренный сторонний репозиторий
  (собственные `pyproject.toml`, `venv/`, `tests/`, `finetuning/`, 45 `.exe`);
  активный `src/audio/tts/provider_manager.py` MOSS не регистрирует.
  **[INFERENCE]** после L3/L4 у него и у `src/tts_providers/` ноль callers.
  Делить на weights и vendor code нечего — OD-7 ретайрит целиком.
- **[FACT]** production-зависимость на `docs/implementation/openai_live_evaluation`
  — три строки `semantic_visual_evaluation_tooling.py:26,38,695` плюс
  `tests/test_semantic_decision_policy.py`. Синтетический генератор
  `_write_prepared_dataset` уже существует. Дефект зафиксирован как C31.
- **[FACT]** после L3 все пять оставшихся файлов `config/` активны, 8–21 caller
  каждый. Повода переносить каталог нет; открыты только `channels/`, `schemas/`
  и reusable templates.
- **[FACT]** `apps/news_to_short/main.py` — 83 строки собственного argparse,
  дублирующего флаги канонического `create`/`resume`; два других wrapper —
  8-строчные делегации. Registry K08 уточнён.
- **[FACT]** PLAN-6E был заблокирован невыполнимым предусловием: Codex не
  установлен, discovery-check выполнить нельзя, а 6E обязателен до PLAN-9A.
  Deadlock снят разделением Claude-части и Codex-части.
- **[FACT]** `src/assets/completion/` уже владеет лестницей выбора A–F,
  `blocking_reasons` и словарём состояний завершённости. Второй словарь
  (`PASS/DEGRADED/…`) не вводится: это создало бы второго canonical owner.
  Продуктовая дыра находится **выше по потоку** — см. «Продуктовая рамка
  PLAN-9 и PLAN-10».
- **[owner decision]** OD-1…OD-10 приняты; см. раздел «Owner decisions
  ревизии 2».
- **[owner decision]** порядок первых действий изменён: STEP 0 (перенос ревизии
  в этот файл и в registry) выполняется **до** PLAN-1D-routing, потому что 1D
  направляет будущих агентов именно сюда.
- **[FACT]** `baseline_head` остаётся `fe2df5b`: нового full baseline run не
  выполнялось. Смещение `current_checkpoint` с PLAN-1A на PLAN-1D-routing —
  следствие reorder, а не выполненной работы.

- **2026-07-30** targeted re-search ограничен одной фазой **на сцену**, а не на
  проект: `targeted_search_done` — локальная переменная
  `complete_scene_assembly` в `src/news/asset_scene_completion.py`, вызываемой
  из per-scene цикла `src/news/asset_manifest_builder.py`.
- **2026-07-30** `config/semantic_visual.json` содержит `enabled: false`,
  `backend: mock`, `semantic_rerank_enabled: false`; режим по умолчанию
  `analyse_and_report`. **Исправлено ревизией 2.1:** прежний вывод «semantic-слой
  существует, но не влияет на отбор» относился к **платному Vision-сервису** и в
  общем виде **опровергнут** — metadata-semantic слой является каноническим
  владельцем решения и может сменить выбранный asset. См. PLAN-9C.
- **2026-07-30** `src/assets/semantic_selection/vision_validator.py` —
  заглушка, безусловно возвращающая `vision_validation_enabled: False`;
  production-callers отсутствуют.
- **2026-07-30** `src/assets/semantic_selection/query_generator.py` содержит
  topic-specific hardcode под один субъект и литерал `"nature"` в atmospheric
  fallback. **Уточнено ревизией 2.1:** этот модуль **не участвует** в
  формировании remote-запросов; главный носитель topic-hardcode —
  `src/news/script_generator.py`, canonical boundary —
  `src/assets/query_adapter.py`.
- **2026-07-30** provider-поиск выполняется без pagination с жёстким лимитом
  результатов на пару provider × query.
- **2026-07-30** `LocalLibraryStockProvider` существует, но не зарегистрирован
  в `create_default_stock_providers`.
- **2026-07-30** production читает данные из
  `docs/implementation/openai_live_evaluation/` через
  `src/assets/semantic_visual_evaluation_tooling.py`; это семейство содержит
  active fixtures и не подлежит массовому untrack.
- **2026-07-30** в репозитории не найдено `.bat`, `.cmd`, `.ps1` и IDE
  launch-конфигураций; владелец подтвердил отсутствие личных внешних команд,
  но старые entrypoints до PLAN-1 и PLAN-13 не удаляются.
- **2026-07-30** нет настроенного remote; действующего CI и доказательств его
  запусков нет; workflow для этого клона выполниться не мог. Локальный запуск
  `full` является основной проверкой.
- **2026-07-30** PLAN-0 уже зафиксирован commit `4027269`; post-commit docs QA
  и `git diff --check` завершились с exit code 0, дерево чистое.
- **2026-07-30** текущий `AGENTS.md` всё ещё направляет rescue-задачу в master
  plan. Пока оба документа указывают C01, конфликт не меняет действие; перед
  переходом на PLAN-2 routing обязан быть исправлен PLAN-1D.
- **2026-07-30** `fast` runner отсутствует; поэтому он удалён из prerequisites
  PLAN-2/PLAN-3 и впервые появляется/проверяется в PLAN-5.
- **2026-07-30** `pyproject.toml` и `requirements.txt` повторяют direct runtime
  dependencies, а `requirements.lock` хранит resolved environment. Это
  кандидат ownership/convergence PLAN-14B, не основание удалять файл сейчас.
- **2026-07-30** `story_card_text_only_v1` требует переданный local
  `source_asset`; automatic asset search в этот workflow не подключён.
  Визуальные PLAN-9–PLAN-11 не считаются доказательством Story Card без
  отдельного workflow evidence.
- **2026-07-30** product sequence изменён: tolerant best-so-far persistence
  предшествует query expansion, pagination и semantic activation, чтобы новые
  попытки не могли терять уже найденный результат.
- **2026-07-30** minimalism QA выполняется дважды: ранний report-only baseline
  после test runner/governance и финальный gate после ownership/docs cleanup.
  Dependency/toolchain audit также перенесён до package consolidation.
- **2026-07-30** verification budget уточнён: targeted tests после каждого
  code slice; `full` — на shared boundaries и при закрытии крупных families,
  а не после каждого локального product leaf.
- **2026-07-30** governance-аудит от clean HEAD `2379444`: независимого
  reviewer в репозитории нет ни в какой форме — отсутствуют `.claude/agents/`,
  `.claude/skills/`, `.claude/commands/`, hooks, Codex-конфиг, git-hooks
  (в `.git/hooks` только samples), `.vscode`, `.idea`, `*.bat`, `*.cmd`, `*.ps1`.
- **2026-07-30** механизма scope-контроля нет: ничто не сравнивает allowlist
  задачи с фактическим `git diff --name-only`. Технически enforced сейчас ровно
  три вещи: `tools/qa/check_agent_docs.py`, deny-list `.claude/settings.json`
  и `tests/network_guard.py`. Остальные правила зависят от памяти модели.
- **2026-07-30** `skills/` не является `.claude/skills/`, поэтому Claude Code
  не загружает эти skills автоматически; они доступны только при ручном чтении
  файла. Codex-адаптер существует как `skills/*/agents/openai.yaml`.
- **2026-07-30** `docs/current/PRODUCT_EVIDENCE_GATE.md` имеет
  `status: historical_reference` внутри `docs/current/` — единственный такой
  файл. `tools.qa.check_agent_docs` проверяет три файла из семи в
  `docs/current/` и не проверяет активный execution plan.
- **2026-07-30** лестница PLAN-9B противоречила собственным разрешённым зонам:
  `src/assets/semantic_selection/query_generator.py` — 55 строк, возвращает
  только строки запросов, а ступени «локальная медиатека», «другой provider» и
  «разрешённый fallback» живут в `src/providers/registry.py`,
  `src/providers/local_library_provider.py` и
  `src/news/asset_scene_completion.py`. Реализовать их внутри слайса было
  невозможно без выхода за scope, и они пересекались с PLAN-10D. Три ступени
  перенесены к PLAN-10C как порядок эскалации; PLAN-9B оставлен только за
  генерацией запросов. **Уточнено ревизией 2.1:** граница «лестница
  заканчивается на генерации запросов» сохраняется, но сама allowed zone была
  ошибочной — canonical owner remote-запросов `src/assets/query_adapter.py`,
  а не `semantic_selection/query_generator.py`.
- **2026-07-30** `git diff --check` проверяет whitespace-ошибки и конфликтные
  маркеры и не сравнивает состояние дерева, поэтому не может доказать
  read-only поведение reviewer. PLAN-6E получил отдельную controlled read-only
  acceptance вместо недоказуемого требования.
- **2026-07-30** карта tracked-файлов под кандидатами protected paths:
  `projects/` — 0; `music/` — 1 `.gitkeep`; `assets/library`+`assets/cache` — 1
  example; `anime_factory/episodes/` — 1 `.gitkeep`; `outputs/` — 9 плановых
  JSON и отчёт; `manual_assets/` — 7, включая 3 versioned SVG; `channels/` — 19
  versioned; `content/` — 13 versioned. Поэтому `outputs/**` и
  `manual_assets/**` нельзя блокировать целиком, а `channels/**` и `content/**`
  нельзя блокировать вовсе. 79 из 112 тестовых модулей используют
  `TemporaryDirectory`/`mkdtemp` вне репозитория, поэтому repo-relative
  deny-list synthetic tempfile не задевает.

### Repository Foundation audit, 2026-07-31

Read-only bounded аудит каркаса (root, `docs`, agent infrastructure,
developer tooling, QA, dev config) от clean HEAD `4ca3655`. Каждая запись
имеет класс: **FACT** — проверено командой; **INFERENCE** — вывод, исполнением
не проверенный; **[ПРЕДП]** — не проверено вовсе; **DEFER** — evidence
недостаточно.

- **2026-07-31 [FACT]** аудит выполнен от `audit_head` `4ca3655`.
  `baseline_head` остаётся `fe2df5b`: полный offline suite на `4ca3655` не
  запускался, промежуточные commits docs-only. Происхождение измерения не
  переписывается без повторного full run.
- **2026-07-31 [FACT]** покрытие аудита: 183 tracked файла в scope, 61
  прочитан построчно, 108 проверены программно, 14 metadata-only, 1 исключён
  по security. **`docs/implementation` (96 файлов) построчно не читался**,
  `docs/audits` (9) и `docs/architecture` (5) прочитаны заголовками. Поэтому
  archive/move/delete внутри этих семейств — DEFER до PLAN-12B.
- **2026-07-31 [FACT]** `git ls-files -i -c --exclude-standard`: 9 tracked
  файлов совпадают с `.gitignore` — 8 × `outputs/*.json` и
  `assets/broll/.gitkeep`. Директорное правило `assets/broll/` обесценивает
  последующее `!assets/broll/.gitkeep`.
- **2026-07-31 [FACT]** `output/` и `tmp/` не покрыты `.gitignore`.
  `output/` содержит один файл — `output/pdf/PROJECT_EXECUTION_PLAN_mobile.pdf`,
  280 820 байт; `tmp/pdfs/` пуст. **[INFERENCE]** это generated artifact:
  имя и размер соответствуют рендеру активного плана, содержимое PDF не
  парсилось. Владелец подтвердил удаление; оно выполняется отдельно от
  commit, поскольку файлы untracked.
- **2026-07-31 [FACT]** `pipeline.py:9` импортирует `scripts.test_moss_voices`;
  `packages.find.include` не содержит `scripts*` при `py-modules=["pipeline"]`.
  **[INFERENCE]** non-editable install ломает `import pipeline` — `pip install .`
  не выполнялся, CI использует `--editable` и дефект не ловит.
  **Отдельный вопрос [DEFER]:** отсутствие `tools*` в wheel дефектом по
  умолчанию не является — сначала PLAN-6C определяет intended distribution
  boundary. Предварительно `tools/` остаётся вне wheel.
- **2026-07-31 [FACT]** `legacy/` (8 файлов) не имеет ни одного Python-caller
  repo-wide; ссылки только в `README.md` и historical docs. **[DEFER]**
  архивирование требует caller gate PLAN-L1: статический граф не доказывает
  отсутствия внешнего или строкового caller.
- **2026-07-31 [FACT]** link-checker по всем 100 tracked `.md`: 0 битых
  локальных ссылок. Hash-скан по всем 664 tracked: единственный содержательный
  exact-дубликат — `ai_youtube/__main__.py` == `src/ai_youtube/__main__.py`,
  то есть симптом двух package roots (C01/C11), а не удаляемый дубль.
  Остальные совпадения — 15 пустых `.gitkeep` и 3 корректных
  `apps/*/__main__.py` boilerplate.
- **2026-07-31 [FACT]** активный execution plan имеет **одну** входящую ссылку
  во всём репозитории — `CURRENT_STATE.md`. `AGENTS.md`, `START_HERE.md`,
  `CLAUDE.md` и `README.md` его не упоминают. Routing чинит PLAN-1D.
  `docs/architecture/visual_rendering_policy.md` — единственный документ,
  задающий визуальный quality bar, — имеет **ноль** входящих ссылок.
- **2026-07-31 [FACT]** `README.md` (405 строк) и `COMMANDS.md` (681 строка)
  не упоминают `ai_youtube` ни разу; `COMMANDS.md` содержит 49 упоминаний
  `src.content_creation.cli` и 24 × `pipeline.py`; `README.md` учит bare
  `python`/`pip` вопреки `AGENTS.md`. `docs/contracts/STAGE1_PUBLIC_CONTRACTS.md`
  называет `src.content_creation.cli` «current CLI» и до сих пор не входил ни
  в один slice — добавлен в зоны PLAN-7.
- **2026-07-31 [FACT]** Claude Code не обнаруживает корневой `skills/`
  автоматически: `.claude/` содержит только `settings.json`,
  `settings.local.json` и `scheduled_tasks.lock`. **[ПРЕДП]** утверждение
  «Codex обнаруживает эти skills через `skills/*/agents/openai.yaml`» **не
  проверено**: Codex в среде не установлен, discovery-check не выполнялся,
  tracked codex-конфигов нет. Наличие файла не является доказательством
  discovery. Различать четыре состояния: наличие файлов, manual loading,
  auto-discovery, actual invocation.
- **2026-07-31 [FACT]** три из шести `SKILL.md` учат
  `python -m src.content_creation.cli`, а `tools/qa/check_agent_docs.py`
  проверяет только frontmatter, локальные ссылки и `TODO` — команды внутри
  skills не проверяются. PLAN-7 чинит файлы, PLAN-6A добавляет проверку.
- **2026-07-31 [FACT]** `docs/current/PRODUCT_EVIDENCE_GATE.md` указывает в
  `source_paths` пять путей внутри gitignored `projects/`. Смена `status` его
  не чинит: файл обязан переехать (PLAN-12A).
- **2026-07-31 [FACT]** `docs/current/` — 2639 строк, из них 1616 (61%)
  приходится на два волатильных плановых документа. **[INFERENCE]** слияние
  `SYSTEM_MAP` + `ARCHITECTURE_BOUNDARY_MAP` + `docs/apps/` + `docs/contracts/`
  дало бы 793 строки до вычета перекрытий. Это **measurement**, а не gate:
  решения о создании отдельного owner принимаются по responsibility, readers,
  lifecycle, смешению контрактов, routing ambiguity и maintenance coupling.
  Число строк может подтверждать проблему, но само по себе новый файл не
  создаёт.
- **2026-07-31 [owner decision]** принято **направление B** модели владения
  документами; зафиксировано как PLAN-12E. Направление — ownership direction,
  не разрешение перемещать файлы. Обязательная последовательная цепочка
  внутри этапа: `12E → 12A → 12B → 12C`, каждое звено зависит от предыдущего.
- **2026-07-31 [FACT]** из восьми кандидатов на новых document owners
  (`RUNTIME_FLOWS`, `QUALITY_BAR`, `EVALUATION_STRATEGY`, `TESTING`,
  `RECOVERY_AND_RESUME`, `STATE_AND_SCHEMAS`, `SECURITY_AND_APPROVALS`,
  `RUNTIME_WORKSPACE`) сейчас не создаётся ни один:
  1 CONDITIONAL NEW OWNER CANDIDATE (`RUNTIME_FLOWS`, пять evidence gates),
  1 EXTRACT CANDIDATE (`QUALITY_BAR`), 2 EXTEND EXISTING OWNER
  (`TESTING` → `tools/qa/run_tests.py`, `STATE_AND_SCHEMAS` → `schemas/` и
  существующий индекс), 2 DEFER (`EVALUATION_STRATEGY`, `RECOVERY_AND_RESUME`),
  2 NOT NEEDED (`SECURITY_AND_APPROVALS` — уже имеет корректное трёхуровневое
  владение instruction + permission + test; `RUNTIME_WORKSPACE` — ADR 0002 +
  PLAN-14 + `CURRENT_STATE`). Ни один не запрещён заранее.

## Completion and archive policy

Пока PLAN-15 не закрыт, файл имеет `status: active`.

После полного выполнения программы:

1. Выполнить финальную проверку: `smoke`, `fast`, full offline, docs QA,
   canonical CLI smoke, `git diff --check`, проверку неизменности
   пользовательских данных и утверждённые product evidence gates.
2. Обновить `CURRENT_STATE.md`, `PRODUCT_PLAN.md` и `CLEANUP_REGISTRY.md`
   только если их фактическое состояние изменилось.
3. Сделать финальную версию этого файла со `status: completed`.
4. Переместить её в
   `docs/archive/handoff/PROJECT_EXECUTION_PLAN_<start-date>_<finish-date>.md`.
5. Удалить активный путь `docs/current/PROJECT_EXECUTION_PLAN.md`.
6. Удалить ссылки на активный план из `AGENTS.md`, `START_HERE.md`,
   `CURRENT_STATE.md` и других current-документов.

Новый активный план поверх завершённого не создаётся. Следующая крупная
программа при необходимости получает собственный `PROJECT_EXECUTION_PLAN.md`.
