---
status: proposal
proposal_date: 2026-07-31
proposal_head: adcbb19
working_branch: governance-reset
target_document: docs/current/PROJECT_EXECUTION_PLAN.md
target_revision: 2.1
scope: плановая корректировка на основе уже собранного evidence
changes_to_repository: только этот файл
canonical_documents_changed: none
commit_created: no
---

# Proposed Revision 2.1

Предложение по точечной корректировке действующего
[PROJECT_EXECUTION_PLAN.md](../current/PROJECT_EXECUTION_PLAN.md) (revision 2).
Документ **ничего не меняет**: canonical plan, `CLEANUP_REGISTRY.md`, `AGENTS.md`
и `START_HERE.md` остаются как есть. Production-код не менялся, новых
исследований и аудитов не запускалось, PLAN-1D не начинался, commit не
создавался.

Классы утверждений сохранены из источников: **FACT** — проверено чтением,
командой или offline-пробой; **INFERENCE** — вывод из фактов; **OWNER** —
решение владельца, зафиксированное в задании на эту ревизию;
**PROPOSAL** — предложение автора этой ревизии, не факт и не решение.

---

## 1. Executive decision

**PROPOSAL.** Revision 2.1 — это **перестановка и переадресация**, а не
переписывание. Плановый объём изменений: две ошибочные allowed zones, один
обмен порядком (9B ↔ 9A), одна риск-ориентированная модель критического пути,
шесть findings, получающих существующего owner, и около двадцати строк в
`CLEANUP_REGISTRY.md`. Ни один существующий PLAN-ID не удаляется.

Три утверждения, на которых стоит вся ревизия:

1. **Продуктовое узкое место переопределено, но не увеличено.** Дефект не в
   настойчивости поиска и не в отсутствии «AI». Дефект в том, что **единственный
   канал доставки provider-ready английского запроса — `visual_brief`, и
   заполняет его только hardcode на одну тему** (deep-dive §1, §8). Следствие:
   произвольная тема получает либо ложный запрос (`ice researchers`), либо
   чрезмерное обобщение (`station`), либо `query_translation_required`.

2. **Новый диагностический этап не создаётся.** Предложенный первым аудитом
   PLAN-P0 (Content & Query Reachability Gate) **считается выполненным по
   смыслу**: deep-dive уже измерил offline, без сети и денег, фактическое число
   `search()`-вызовов, уникальность строк, источник каждого запроса, canonical
   path, альтернативные entrypoints и Git history. Повторять это отдельным
   этапом — оплатить одно и то же evidence дважды. Тесты, предложенные
   deep-dive (T1–T11), становятся regression/product-тестами внутри своих
   implementation slices.

3. **Ревизия не выдаёт новых разрешений.** Ни одно предложение ниже не является
   approval на реализацию. Перенос `--text` в канонический CLI, любое
   persisted-изменение, любое destructive retirement и любая model/network
   операция требуют owner approval **в момент implementation** (§22).

Что ревизия **не** делает: не создаёт `TranslatorService`, `SearchEngine`,
`QueryOrchestrator`, `search_session.json`, `content_origin`, четвёртый путь к
локальной медиатеке, второй словарь completion-состояний, новый AI-подсистемный
слой и третий плановый документ.

---

## 2. Evidence hierarchy

**PROPOSAL.** Для revision 2.1 действует следующий порядок доказательности —
он **дополняет**, а не заменяет `Source-of-truth precedence` действующего плана.

```
1. Git и фактический код                                     (без изменений)
2. Реальные tests, artifacts и воспроизводимые offline-пробы
3. CRITICAL_INPUT_SEARCH_DEEP_DIVE_2026-07-31.md             ← более позднее evidence
4. INDEPENDENT_REPOSITORY_REVIEW_2026-07-31.md               ← более раннее evidence
5. Owner decisions задания на revision 2.1
6. Собственные рекомендации этой ревизии                     (PROPOSAL)
```

**Правило разрешения конфликта.** Deep-dive выполнил контролируемые
offline-пробы (`network_guard` активен, `blocked_attempts == []`, провайдеры —
записывающие заглушки, временные каталоги вне репозитория). Первый audit
основан на чтении кода. Там, где механизмы расходятся, **побеждает deep-dive**.

### 2.1. Что deep-dive подтвердил в первом аудите

| Утверждение первого аудита | Итог |
|---|---|
| topic-режим даёт шаблонный сценарий из шести фраз | **подтверждено** на 3/3 темах |
| слоя перевода нет, remote-провайдеры объявлены English-only | **подтверждено** |
| каждая сцена ищется фактически одной строкой | **подтверждено с исправлением строки** |
| `src/assets/completion/` — не дыра, canonical owner | **подтверждено** (в пробе корректно пометил все сцены `missing`) |
| дыра выше по потоку | **подтверждено** |
| PLAN-10D недооценивает проблему локальной медиатеки | **подтверждено и усилено** (три пути, не два) |
| PLAN-6B занижает subprocess-риск | **подтверждено** (12 модулей, не 7) |

### 2.2. Что deep-dive опроверг — эти механизмы больше не используются

| Механизм первого аудита | Фактический механизм (deep-dive) |
|---|---|
| «ноль отправленных запросов» | 10 / 50 / 10 вызовов `search()` на тему; **отправляются ложные запросы**, что хуже нуля |
| «`legacy_broad_query` — единственное, что гарантированно доходит» | **не доходит ни разу**: `source_is_latin` — свойство всего набора, русский `primary_query` выбрасывает английский alternative вместе с собой |
| «`visual_brief` в автоматическом потоке не создаётся никем» | создаётся — для orca-тем, `_apply_video_first_topic_briefs`; **provider-ready путь уже работает**, но захардкожен |
| «нужен слой перевода как отдельная capability/подсистема» | нужен **один новый источник `ProviderQuery`** внутри существующего владельца `query_adapter` |
| «topic-hardcode сосредоточен в `query_generator.py`» | `query_generator.py` **не участвует** в формировании remote-запросов; canonical boundary — `src/assets/query_adapter.py` |

### 2.3. Historical evidence, принятое как факт

- **FACT.** `Translator` / `def translate` / `to_english` — **0 commits** за всю
  историю. Полноценного translate-слоя в application не существовало никогда;
  восстанавливать нечего.
- **FACT.** Английские `visual_keywords` в `content/**/*.json` — **входные
  данные**, а не выход кода. Их писал человек или агент вне приложения.
- **FACT.** Legacy `build_query_variants` содержал настоящую лестницу расширения
  (суффиксы, усечение, mood, channel-расширения, до 12 вариантов) и
  diversity-резерв локальных слотов.
- **FACT.** `_apply_video_first_topic_briefs` доказывает, что
  `VisualBrief`/`provider_queries` **уже являются рабочим transport contract**:
  контроль-тема дала 180 вызовов и 4 осмысленных английских запроса.

---

## 3. Owner decisions incorporated

**OWNER.** Решения задания на revision 2.1. Нумерация продолжает OD-1…OD-10
действующего плана.

| # | Решение |
|---|---|
| **OD-11** | PLAN-P0 (Content & Query Reachability Gate) **не создаётся**. Evidence получено deep-dive; повторный диагностический этап запрещён. Предложенные тесты становятся regression/product-тестами внутри implementation slices |
| **OD-12** | CRITICAL-1 — текущий главный product defect, но в **исправленной** формулировке deep-dive: проблема не «ноль запросов», а «ложные/чрезмерно общие/пропущенные запросы и единственный канал доставки — hardcode» |
| **OD-13** | **Не создавать** `TranslatorService`, `SearchEngine`, `QueryOrchestrator` и второй query pipeline. Canonical owner переиспользует `VisualBrief`, `SceneVisualPlan`/`VisualSearchIntent`, `query_adapter.build_scene_queries`, `ProviderQuery`, provider contracts |
| **OD-14** | `src/assets/query_adapter.py` — фактическая canonical boundary, через которую remote-запросы доходят до провайдеров. Allowed zone PLAN-9B исправляется на неё |
| **OD-15** | PLAN-9B выполняется **до** PLAN-9A. Best-so-far бессмысленно оптимизировать до появления provider-ready кандидатов |
| **OD-16** | Метод provider-language adaptation **не фиксируется заранее**. Допустимы deterministic normalization/lexicon, prepared `VisualBrief`, model-assisted adaptation или комбинация. Выбор — по semantic correctness, fail-closed, testability, cost, network/paid boundary и reuse существующих owners. Модель допускается только если реально лучше закрывает gap |
| **OD-17** | CRITICAL-2 исправляется сейчас, **без AI research**. Текущий product scope: prepared content → scenes/visual intent → asset search/selection → rights/provenance → voice → timeline → subtitles → music/SFX → editing/render → export. Idea generation, web/AI research, AI script writing, autonomous creative direction — **DEFER**, без PLAN, package, interface и placeholder |
| **OD-18** | Для factual strict workflow `topic` = **intent, не source material**. Silent fallback `topic → insufficient material → generic template → factual production success` запрещён. `LegacyTemplateScriptProvider` **не удаляется** — допустим только в явно выбранном `template`/`demo`/`test`/`draft` режиме. `content_origin` **не создаётся**: используются существующие `script_provider`, `fallback_reason`, `script_metadata`, `ScriptValidationResult` |
| **OD-19** | Уникальная capability `apps/news_to_short --text/--text-file` **мигрирует** в канонический `python -m ai_youtube` + content_creation request path; после переноса capability и callers `apps/news_to_short` ретайрится по OD-2. Это не новая script-engine функциональность |
| **OD-20** | CRITICAL-3 («в content path почти нет AI») **не является** current critical defect. Отдельный этап не создаётся. Future-proofing rule: downstream production pipeline не должен предполагать, что script создан внутри AI-YouTube; prepared external content остаётся first-class input |
| **OD-21** | CRITICAL-4 (double orchestration) сохраняется как HIGH architecture debt, но **не** prerequisite CRITICAL-1/2. Получает существующего owner (PLAN-13), решение не проектируется сейчас |
| **OD-22** | Порядок semantic/Vision: provider-ready query → candidates → semantic/Vision → rank/select. PLAN-9C сохраняется, новый semantic stack не создаётся |
| **OD-23** | Anime Factory — **не** disposable legacy. Это source implementation будущего `video_repurposer`. `enabled=False`/`planned` не означает ненужности. Порядок: стабилизировать Content Creator → UI Content Creator → отдельный deep audit Anime Factory → классификация каждой capability → построить Video Repurposer → его UI. Runtime внутри source repo остаётся дефектом и чинится через PLAN-14 |
| **OD-24** | `search_session.json` как отдельный persisted owner **не утверждается**. Сначала проверить существующих owners (`job.json`, asset manifest, project state, completion/resume state). Если существующего owner можно расширить — новый файл запрещён |
| **OD-25** | Multi-topic regression начинается **раньше** PLAN-11 и применяется после каждого существенного product slice. PLAN-11 остаётся финальным product evidence gate, но не первой проверкой на разных темах |
| **OD-26** | Governance не должен задерживать дешёвое product-исправление без реальной причины, **но** safety/reviewer/persisted/paid protections обязаны быть готовы до своей risk boundary. Каждый оставшийся blocker обязан иметь однострочное обоснование |

---

## 4. Corrected product bottleneck

**PROPOSAL.** Раздел «Продуктовая рамка PLAN-9 и PLAN-10» действующего плана
верен в первой половине («`completion/` — не дыра») и **неполон** во второй: он
начинает перечисление дыр с генерации запросов, тогда как выше находятся ещё две
ступени.

Исправленная карта (замена таблицы плана, строки 1282–1292):

```
prepared content / topic
  → [CRITICAL-2] source material: topic не является материалом; thin input
                 молча уходит в LegacyTemplateScriptProvider, а
                 script_validation остаётся "passed"
  → research     (regex + словарный классификатор; в текущем scope — не дефект)
  → script       (DeterministicScriptProvider исправен при наличии материала)
  → visual plan  (intents на языке сценария; requires_translation выставляется
                  и никем не читается)
  → [CRITICAL-1] provider language: единственный канал доставки английского
                 запроса — visual_brief; заполняет его только topic-hardcode.
                 GLOSSARY матчится подстрокой → ложные срабатывания и пропуски.
                 source_is_latin — свойство набора → английский alternative
                 выбрасывается вместе с русским primary
  → providers    (нет pagination, лимит 5 — PLAN-10B/10C, эффект только после
                  CRITICAL-1)
  → semantic     (существует, по построению не влияет — PLAN-9C)
  → completion   (работает; canonical owner; не трогать)
```

Исправленная таблица владения дырами:

| Что | Owner-слайс | Изменение относительно revision 2 |
|---|---|---|
| честность источника сценария (`topic` → template) | **PLAN-9B-4** | **новое**: revision 2 не имела owner |
| канонический вход «исходный текст» | **PLAN-9B-5** | **новое**: revision 2 не имела owner |
| источник provider-language запросов | **PLAN-9B-1** | было: «генерация запросов и semantic expansion → PLAN-9B» без адреса |
| лестница расширения и снятие topic-hardcodes | **PLAN-9B-2** | зона исправлена |
| retirement устаревших query-путей | **PLAN-9B-3** | **новое** |
| best-so-far persistence через `resume` | PLAN-9A | без изменений, кроме порядка |
| semantic/Vision wiring | PLAN-9C | без изменений |
| ledger попыток и stop reasons | PLAN-10A | без изменений |
| pagination и provider exhaustion | PLAN-10B | + provider registry convergence |
| adaptive budget, plateau, эскалация | PLAN-10C | без изменений |
| локальная медиатека | PLAN-10D | переформулирован (§10) |

**FACT — точный список сломанного, в порядке ущерба** (deep-dive §8):

| # | Дефект | file:line | Ущерб |
|---|---|---|---|
| 1 | нет источника английских терминов для произвольной темы | [query_adapter.py:329-367](../../src/assets/query_adapter.py:329) | основной |
| 2 | глоссарь матчится подстрокой (`лед` ⊂ «исследователи») | [query_adapter.py:391-393](../../src/assets/query_adapter.py:391) | отправляются ложные запросы — хуже пустого результата |
| 3 | глоссарь не знает морфологии («пустыню» ≠ «пустыня») | там же | пропуск единственного релевантного слова |
| 4 | `source_is_latin` — свойство набора, не элемента | [query_adapter.py:158-160](../../src/assets/query_adapter.py:158) | теряется уже существующий английский запрос |
| 5 | topic-hardcode на одну тему | [script_generator.py:115-190](../../src/news/script_generator.py:115) | скрывает дефект на «своей» теме |
| 6 | `requires_translation` выставляется и не читается | [planners/deterministic.py:359](../../src/content/visual_planning/planners/deterministic.py:359) | сигнал есть, потребителя нет |
| 7 | `legacy_broad_query` дописывается в каждую сцену и не доставляется | [legacy_format.py:161-164](../../src/content/visual_planning/legacy_format.py:161) | шум в persisted-плане |

**FACT — скрытая связь двух findings** (deep-dive §9.3). Сегодня шаблонный
сценарий не доезжает до publish только потому, что все сцены `missing` из-за
CRITICAL-1. **Как только CRITICAL-1 починят, шаблонный сценарий поедет в publish
беспрепятственно.** Поэтому CRITICAL-2 не откладывается за CRITICAL-1, а идёт
внутри той же цепочки.

---

## 5. New critical path

### 5.1. Старый путь (revision 2)

```
PLAN-1D-routing
  → PLAN-2 → PLAN-3 → PLAN-4 → PLAN-5
  → PLAN-6A → PLAN-6D → PLAN-6E
  → PLAN-1C′
  → ► PLAN-9A ◄            (первый product-слайс: best-so-far persistence)
затем: PLAN-9B → 9C → 9D → 9E; PLAN-10A → 10B → 10C → (10D) → PLAN-11
```

Девять шагов до первого product-изменения, и это изменение — persistence
результата, которого пока не существует.

### 5.2. Предлагаемый путь (revision 2.1)

```
PLAN-1D-routing → PLAN-2 → PLAN-3 → PLAN-4
  → ► PLAN-9B-0 (characterization) → PLAN-9B-1 (provider-language foundation) ◄

параллельно, стартует после зелёного PLAN-4:
  PLAN-5 · PLAN-6A → PLAN-6D → PLAN-6E · PLAN-6B · PLAN-6C · PLAN-7 · PLAN-8
  PLAN-L0 → L1 → L2 → L3 → L4 · инкрементальный перевод прозы

далее по risk boundary (§5.4):
  PLAN-9B-5 (source_text CLI)  ← требует PLAN-5 + owner approval
  PLAN-9B-4 (honest script)    ← идёт вместе с 9B-5
  PLAN-9B-2 (expansion + hardcode removal) ← требует 6A/6D/6E
  PLAN-9B-3 (query-path cleanup)           ← требует зелёной замены
  → PLAN-1C′
  → PLAN-9A → PLAN-9C
  → PLAN-10A → PLAN-10B → PLAN-10C → PLAN-10D
  → PLAN-9D → PLAN-9E → PLAN-11
```

**PLAN-P0 не вставляется.** Evidence уже получено (OD-11).

### 5.3. Почему PLAN-9B теперь раньше PLAN-9A

**FACT.** Deep-dive §5.2: canonical path сегодня отправляет 10/50/10 вызовов
уникальными строками `ice researchers` / `station`, и во всех трёх темах
6 из 6 сцен остаются пустыми. **INFERENCE.** Best-so-far persistence сохраняет
лучший результат из этого множества, то есть сохранять нечего; persisted-схема,
tolerant reader, `full`-прогон и уже выданный owner approval будут потрачены на
контракт, чьё наполнение ещё не существует. Persistence осмысленна ровно с того
момента, когда появляются provider-ready кандидаты.

**Проверка зависимостей — перестановка минимальна и непротиворечива.**

| Слайс | Зависимость revision 2 | Зависимость revision 2.1 | Конфликт? |
|---|---|---|---|
| PLAN-9B | PLAN-9A | критический путь §5.2 | нет |
| PLAN-9A | prerequisite chain → 9A | PLAN-9B-2 + PLAN-1C′ | нет |
| PLAN-9C | PLAN-9A + C01-SEM | без изменений | нет |
| PLAN-10A | PLAN-9A | без изменений | нет |
| PLAN-10B | PLAN-10A | без изменений | нет |
| PLAN-10C | PLAN-9B + PLAN-10B | без изменений — **обе выполнены раньше** | нет |
| PLAN-10D | PLAN-10C + аудит | без изменений, аудит переформулирован (§10) | нет |
| PLAN-9D | PLAN-9B + PLAN-9C | без изменений | нет |
| PLAN-9E | PLAN-9D + PLAN-10C | без изменений | нет |
| PLAN-11 | PLAN-9E + PLAN-10C | без изменений; regression начинается раньше (OD-25) | нет |

Меняется **ровно одно ребро графа**: `9A → 9B` становится `9B → 9A`. Все
остальные зависимости сохраняются и остаются выполнимыми.

### 5.4. Какие blockers остаются и почему — по одной строке на blocker

**Принцип (OD-26).** Blocker остаётся только если он защищает **конкретную**
risk boundary, которую пересекает конкретный слайс. «Стоял в плане» — не
причина.

**Остаются перед первым production fix (PLAN-9B-0/9B-1):**

| Blocker | Одна строка: почему до первого production fix |
|---|---|
| **PLAN-1D-routing** | Без него новый агент, буквально исполнив `AGENTS.md`, уходит в historical master plan и начинает не ту работу. |
| **PLAN-2** | Красный `test_voice_profile_resolution` делает невозможным различить «сломал я» и «было сломано» в радиусе изменения. |
| **PLAN-3** | То же для `test_autonomous_completion_pipeline` — модуля, который потом меняет PLAN-9A. |
| **PLAN-4** | Без зелёного воспроизводимого baseline любой targeted-прогон после query-изменения недоказуем. |

**Переходят в parallel lane, с указанием собственной risk boundary:**

| Слайс | Почему больше не блокирует 9B-0/9B-1 | Где становится обязательным |
|---|---|---|
| **PLAN-5** | Targeted-прогон работает существующим `unittest discover`; режимы — удобство, а не защита. | **Обязателен до PLAN-9B-5** (меняется public CLI surface → required verification включает `smoke`) и до PLAN-9B-3 (retirement → `full`). |
| **PLAN-6A** | Agent Autonomy Model **уже действует** из текста плана; 6A только переносит её в `AGENTS.md`. | Обязателен до PLAN-6D (существующая зависимость) → значит до PLAN-9B-2. |
| **PLAN-6D** | `check_task_scope` защищает от выхода за allowlist; 9B-0/9B-1 — один owner, один модуль, allowlist тривиален. | **Обязателен до PLAN-9B-2**: первый слайс, чей diff затрагивает больше одного owner (`query_adapter` + `script_generator` + `visual_planning`). |
| **PLAN-6E** | Reviewer защищает от ошибок исполнителя, а не делает задачу правильной. | **Обязателен до PLAN-9B-2**: decision-rights модель разрешает удалять реализацию с callers «под ответственность reviewer» — значит reviewer должен существовать до первого такого удаления. |
| **PLAN-1C′** | 9B-0/9B-1 не трогают semantic/completion/asset-manifest ownership. | **Обязателен до PLAN-9A** (persisted asset manifest) и до **PLAN-9C** (semantic decision path). Для 9B-3 достаточно узкого capability gate по правилу 11 Execution protocol. |
| **PLAN-6B, 6C, 7, 8, PLAN-L\*** | Уже параллельны в revision 2; ревизия 2.1 это не меняет. | по своим собственным gates. |

**Предлагаемое снятие одной зависимости.** PLAN-1C′ сейчас зависит от PLAN-6E.
**PROPOSAL:** зависимость снять. 1C′ — docs-only capability gate, пишущий в
`CLEANUP_REGISTRY.md`; read-only ownership inventory не требует существования
reviewer-skill. Это освобождает 1C′ от цепочки 6A→6D→6E и позволяет закрыть его
параллельно. Reviewer при этом остаётся обязательным там, где действительно
нужен — перед первым destructive/multi-owner production-слайсом.

### 5.5. Safety gates перед persisted/network/paid/destructive работой

**PROPOSAL — risk-boundary таблица.** Она заменяет одну линейную цепочку
блокеров и делает явным, что именно защищает каждый gate.

| Пересекаемая boundary | Обязательные gates | Первый слайс, который её пересекает |
|---|---|---|
| локальное поведение, targeted tests, ноль persisted/public/paid/destructive | 1D, 2, 3, 4 | **PLAN-9B-0, PLAN-9B-1** |
| shared contract / требуется `full` | + PLAN-5 | PLAN-9B-2 |
| несколько owners в одном diff | + PLAN-6D (`check_task_scope`) | PLAN-9B-2 |
| destructive retirement реализации с callers | + PLAN-6E (reviewer) + reversible retirement (annotated tag + `git bundle` + строка `Retired`) | PLAN-9B-2 (orca-hardcode), PLAN-9B-3 |
| public CLI/input mode | + PLAN-5 (`smoke`) + **owner approval** | PLAN-9B-5 |
| persisted bytes / schema / layout | + tolerant reader + **owner approval** (approval PLAN-9A **не переносится**) | PLAN-9A |
| semantic/Vision decision path | + PLAN-1C′ | PLAN-9C |
| network / model / paid операция | + **owner approval на конкретное действие** + PLAN-6E | уровень 3 provider-language adaptation (§6), PLAN-9E |
| runtime/user data move | + `Preserved runtime corpus` + проверенный абсолютный путь + owner approval | PLAN-14D/14E |

**Что осознанно НЕ оптимизировано.** Путь не сокращался ради меньшего числа
этапов. PLAN-4 сохранён, хотя он «всего лишь измерение»; PLAN-6E сохранён как
blocker первого destructive слайса, хотя это добавляет три шага. Минимизированы
только blockers без конкретной защищаемой boundary.

---

## 6. Parallel / non-blocking path

**PROPOSAL.** Параллельная дорожка расширяется относительно revision 2. Ни один
из этих слайсов не блокирует PLAN-9B-0/9B-1.

```
PLAN-5                          test runner modes         → gate для 9B-3/9B-5
PLAN-6A → PLAN-6D → PLAN-6E     governance/scope/reviewer → gate для 9B-2
PLAN-6B                         minimalism baseline + subprocess measurement (§14)
PLAN-6C                         dependency/toolchain ownership
PLAN-7                          canonical CLI в документации
PLAN-8                          PRODUCT_PLAN.md
PLAN-L0 → L1 → L2 → L3 → L4     retirement legacy content stack
PLAN-1A / PLAN-1B               capability gates для PLAN-13
инкрементальный перевод прозы   OD-5
```

**Изменение в PLAN-L0.** В обязательный salvage-список добавляются две находки,
которые deep-dive назвал прямо (§13, §16):

1. **лестница расширения** `build_query_variants`
   ([video_asset_engine.py:225-256](../../src/video_asset_engine.py:225)) —
   класс `MIGRATE KNOWLEDGE`, целевой потребитель — PLAN-9B-2;
2. **diversity-резерв локальных слотов**
   ([video_asset_engine.py:116-135](../../src/video_asset_engine.py:116)) —
   класс `MIGRATE KNOWLEDGE`, целевой потребитель — PLAN-10D;
3. **практика «английские ключи существуют отдельным полем, отделённым от
   нарратива»** (`visual_keywords` в `content/**/*.json`) — класс
   `MIGRATE KNOWLEDGE`, целевой носитель — ADR/registry.

**PROPOSAL по PLAN-L0 scope.** Первый audit предлагал (PLAN-E7) освободить
`legacy/` от KSG как процедуру ради процедуры. **Не принимать это в revision
2.1**: решение о scope KSG — owner decision (OD-1), и revision 2.1 не имеет
evidence, что 8 файлов `legacy/` не содержат уникального знания. Оставить как
есть; при желании владельца — отдельное решение.

---

## 7. PLAN-9 reordered structure

### 7.1. PLAN-9B — переопределение по фактическому owner

**Было (revision 2):**
- название: «query expansion и снятие topic-hardcodes»;
- allowed zone: `src/assets/semantic_selection/query_generator.py` и его тесты;
- статус: blocked (PLAN-9A).

**Предлагается (revision 2.1):**
- название: **«input/query truth: provider-language adaptation, expansion,
  снятие topic-hardcodes и честный источник сценария»**;
- allowed zones — по под-слайсу, не общие на весь этап;
- статус: **первый product-этап программы**, не блокирован PLAN-9A.

**FACT — основание смены зоны** (deep-dive §2, §10.1).
`src/assets/semantic_selection/query_generator.py` **не участвует** в
формировании запросов к remote-провайдерам: его пять callers питают
envato-метаданные и отчёты. Единственные точки контакта с провайдером —
[query_adapter.py:141 `build_scene_queries`](../../src/assets/query_adapter.py:141)
и [query_adapter.py:235 `build_slot_queries`](../../src/assets/query_adapter.py:235).
**Других путей к remote-провайдеру в активном workflow нет.**

**Идентификаторы под-слайсов — не порядок выполнения.** Прецедент уже
установлен PLAN-12 («Буквы под-slices — идентификаторы, а не порядок
выполнения»). Порядок задаётся явно ниже.

**Порядок выполнения:** `9B-0 → 9B-1 → 9B-5 → 9B-4 → 9B-2 → 9B-3`.

---

#### PLAN-9B-0 — characterization текущего поведения

- **цель:** зафиксировать фактическое поведение до правки, чтобы диффы были
  доказуемы (требование characterization-first действующего плана).
- **зоны:** новый offline test-модуль + этот план (evidence).
- **фиксируется:** число фактических `search()`-вызовов на тему; уникальные
  отправленные строки (`ice researchers`, `station`); `source` каждого запроса
  (`deterministic_glossary`); число провайдеров, пропущенных по
  `query_translation_required`; `script_provider == "legacy_template"` при
  `script_validation.status == "passed"`.
- **evidence-база:** deep-dive §5.1, §5.2 (таблицы уже содержат ожидаемые
  значения; тест их воспроизводит, а не переизмеряет заново).
- **соответствует тестам deep-dive:** T10, T11.
- **risk boundary:** нет. Ноль production-изменений, ноль сети, ноль денег.
- **required verification:** targeted + `network_guard`.

#### PLAN-9B-1 — provider-language / query adaptation foundation

- **цель:** произвольный visual intent порождает **несколько provider-ready
  queries** без topic-specific hardcode.
- **зоны:** `src/assets/query_adapter.py` + его тесты. Точка расширения —
  уровень между `_explicit_provider_queries` и `_english_queries`.
- **требования (OWNER):**
  - reuse `VisualBrief` как формат ответа (`subject` / `action` / `place` /
    `exact_entities` / `must_avoid` / `provider_queries`) — схема уже полная и
    уже доказана orca-путём; новыми полями не расширять;
  - reuse `ProviderQuery.source` — один новый `source`-код, не новый транспорт;
  - **сохранить fail-closed**: при неуверенности по-прежнему
    `STATUS_TRANSLATION_REQUIRED`, а не догадка. Это уже правильное поведение
    модуля и оно не меняется;
  - **не отправлять догадки как factual query**;
  - **не использовать substring `GLOSSARY` как canonical translation
    mechanism** — состав терминов сохраняется как seed, механизм матчинга
    заменяется (границы слова + нормализация);
  - **не создавать новый service** без доказанной необходимости (OD-13).
- **входит сюда же:** дефект №2 (ложные срабатывания) и №3 (морфология) —
  они принадлежат тому же модулю и той же функции.
- **соответствует тестам deep-dive:** T1, T2, T4, T5.
- **risk boundary:** локальное поведение одного owner. Persisted-эффект
  подлежит проверке (§21, E-2).
- **required verification:** targeted `query_adapter` tests; `full` — только
  если проверка покажет изменение shared contract.

#### PLAN-9B-5 — канонический вход «исходный текст» (CRITICAL-2, часть 1)

Описан в §8. Выполняется **до или вместе с** 9B-4.

#### PLAN-9B-4 — честный источник сценария (CRITICAL-2, часть 2)

Описан в §8.

#### PLAN-9B-2 — query expansion + domain-hardcode removal

- **цель:** контролируемая лестница расширения + снятие topic-specific
  hardcodes из shared engine.
- **зоны:** `src/assets/query_adapter.py`, `src/news/script_generator.py`,
  `src/content/visual_planning/legacy_format.py`,
  `src/assets/semantic_selection/*` и их тесты.
- **salvage useful knowledge из трёх источников, без восстановления старого
  pipeline:**
  - legacy `build_query_variants` — лестница расширения (через PLAN-L0);
  - `semantic_selection/query_generator` — формулировка
    `exact → broad → environment → atmospheric`;
  - orca `provider_queries` — трёхуровневая структура «точный субъект → группа →
    среда» и `must_avoid` как часть смысла запроса.
- **входит сюда же дефект №4** (`source_is_latin` как свойство набора →
  проверка переносится на элемент). Deep-dive: самый дешёвый в починке, даёт
  немедленный эффект, но как самостоятельное решение недостаточен.
- **удаление topic-specific hardcodes** выполняется **после** переноса полезной
  capability, не раньше.
- **Topic-hardcode inventory считается PROVISIONAL.** Первый audit насчитал
  шесть модулей; deep-dive нашёл главный носитель в седьмом
  (`src/news/script_generator.py`). **Число файлов не фиксируется как
  invariant** — это измерение, а не контракт. Отдельно отмечается, что hardcode
  найден и внутри `modes.py:295-296` (`ambiguous_whale_for_orca_scene`,
  `missing_orca_evidence_for_orca_scene`), то есть внутри `[HARD]` safety gate;
  снятие этих двух литералов требует отдельного обоснования и **не** является
  разрешением менять сам gate.
- **соответствует тестам deep-dive:** T3.
- **risk boundary:** несколько owners + destructive → требует 5, 6A, 6D, 6E.
- **required verification:** targeted + `full` (меняется persisted содержимое
  visual plan).

#### PLAN-9B-3 — query-path cleanup

- **выполняется только ПОСЛЕ зелёной replacement implementation.**
- **кандидаты на retirement** (ни один не удаляется до переноса уникального
  knowledge и всех callers):
  - harmful substring `GLOSSARY` matching (`_glossary_terms`);
  - `_apply_video_first_topic_briefs` + `tests/test_script_engine_pipeline.py:141-157`;
  - dead `legacy_broad_query` — **только после** 9B-1 и дефекта №4, иначе на
    переходный период покрытие падает до нуля;
  - deprecated `make_stock_query` ([visual_plan.py:71-78](../../src/news/visual_plan.py:71));
  - `src/assets/semantic_selection/query_generator.py` — **после миграции ВСЕХ
    пяти callers** (`asset_manifest_builder.py:577,749,807,839`,
    `youtube_shorts.py:263`).
- **правило (OWNER):** replacement working → callers migrated → targeted tests
  green → **затем** delete. Не удалять source до переноса уникального
  knowledge/callers.
- **risk boundary:** destructive retirement → reversible retirement mechanism
  обязателен.
- **required verification:** targeted + `full`.

### 7.2. PLAN-9A — без изменения состава, с изменением места

- **состав, ограничения, additive schema, tolerant reader, уже выданный owner
  approval — сохраняются дословно.**
- меняется **только** prerequisite chain: `PLAN-9B-2 + PLAN-1C′` вместо
  `…6E → 1C′`.
- **PROPOSAL:** добавить в раздел одну строку — при проектировании состава
  учесть, что 9A/10A/10B/10C логически описывают **одно** состояние поиска
  (§9). Это не разрешение создавать `search_session.json` (OD-24).

### 7.3. PLAN-9C — сохраняется, порядок подтверждён

- Порядок `provider-ready query → candidates → semantic/Vision → rank/select`
  подтверждён (OD-22).
- Цель без изменений: существующий semantic result должен реально влиять на
  decision path **после** того, как 9B обеспечит нормальных кандидатов.
- Новый semantic stack не создаётся. Запрет на mock как доказательство
  визуального качества сохраняется.
- **FACT для будущего исполнителя** (deep-dive §5.2, первый audit CRITICAL-5):
  `_semantic_visual_summary` жёстко пишет `"semantic_rerank_enabled": False`
  независимо от конфига; `_selection_fingerprint` делает неизменность отбора
  **инвариантом** сервиса. То есть 9C — не «включить флаг», а снять
  архитектурное ограничение.

### 7.4. PLAN-9D / PLAN-9E — без изменений

Зависимости и содержание сохраняются. 9D по-прежнему запрещает новые платные
вызовы; 9E по-прежнему требует owner approval и opt-in policy.

---

## 8. CRITICAL-2 / source_text integration

**OWNER (OD-17, OD-18, OD-19).** CRITICAL-2 — product defect, исправляется
сейчас, без AI research.

### 8.1. Что именно исправляется

**FACT** (deep-dive §9.1, §9.3, воспроизведено на 3/3 темах):

```
topic → article["text"] == сама тема → 1 claim → _is_thin → LegacyTemplateScriptProvider
      → 6 фиксированных фраз
      → script_validation.status == "passed", valid == true, error_count == 0
      → downstream не читает script_warnings / script_metadata.fallback_reason
        (repo-wide поиск: 0 production-читателей)
```

### 8.2. PLAN-9B-4 — честный источник сценария

- **цель:** silent fallback `topic → insufficient material → generic template →
  factual production success` перестаёт существовать.
- **owner direction (OD-18):** для factual strict workflow `topic` = intent, не
  source material. Если usable source material отсутствует — либо предоставлен
  внешний prepared source, либо workflow честно блокируется как
  `insufficient_source_material`.
- **существующие механизмы, которых достаточно** (deep-dive §9.5) — новых
  сущностей не создаётся:
  1. `provider_options={"allow_legacy_fallback": False}` **уже реализован** и
     уже поднимает `ScriptProviderInputError`
     ([deterministic.py:152-156](../../src/content/script_engine/providers/deterministic.py:152));
     нужно связать его с completion mode, а не заводить новый флаг;
  2. `ScriptValidationResult` — существующий owner статуса сценария; один
     issue-код даёт блокирующий статус **без второго словаря состояний**;
  3. `script_metadata.fallback_provider` / `fallback_reason` — существующий
     metadata owner происхождения текста.
- **`content_origin` не создаётся (OD-18).** Информация уже выражена: 
  `extracted_from_source` ≡ `script_provider == "deterministic_local"` без
  `fallback_reason`; `template_filler` ≡ `legacy_template` +
  `fallback_reason == "insufficient_source_material"`; `model_written` ≡
  `script_provider == "llm"`; плюс не покрытый предложением
  `user_supplied` — слова автора. Дефект не в отсутствии поля, а в том, что
  **никто существующее поле не читает**. Минимальное изменение: научить
  `validate_script` и `quality_check` читать `provider_id` + `fallback_reason`.
- **`LegacyTemplateScriptProvider` не удаляется.** Он остаётся эталоном
  регрессии и воспроизводимости старых проектов; допустим в явно выбранном
  `template` / `demo` / `test` / `draft` режиме. Меняется **условие его
  молчаливого вызова**, а не он сам.
- **соответствует тестам deep-dive:** T6, T7, T8.
- **тесты, которые придётся изменить** (deep-dive §9.4):
  `tests/test_script_engine.py:286-292` (ожидание становится «blocking для
  strict»); `tests/test_script_engine_pipeline.py:233-236`;
  `tests/test_script_engine.py:296-301` — **сохранить**, там уже нужное
  поведение.
- **risk boundary:** поведение strict-режима наблюдаемо пользователем.
  Выполняется **вместе с 9B-5**, иначе пользователь теряет offline-путь.

### 8.3. PLAN-9B-5 — миграция уникальной capability `--text`

**FACT** (deep-dive §7, §9.2, §5.4). Единственная уникальная бизнес-возможность
во всём `apps/` — флаги `--text` / `--text-file`
([apps/news_to_short/main.py:22-23](../../apps/news_to_short/main.py:22)). Тот
же материал, поданный через `--text`, даёт **7 claims, `deterministic_local`,
нарратив из предложений источника** и никакого `insufficient_source_material`.
Канонический CLI такой возможности не имеет: `--input-mode` принимает только
`topic | article_url | pasted_script | script_file`
([content.py:94-100](../../src/content_creation/commands/content.py:94)), причём
`pasted_script` трактуется как **готовый сценарий** (`user_supplied`), а не как
материал. Единственный вход с настоящим материалом — `article_url`, то есть сеть.

- **действие:** MIGRATE UNIQUE CAPABILITY из `apps/news_to_short` в канонический
  `python -m ai_youtube` + content_creation request path.
- **имя режима:** кандидат `source_text`. **Не закреплять без проверки
  фактического CLI contract** — имя определяется по текущим naming conventions
  при implementation.
- **reuse:** `INPUT_MODE_TEXT` и `resolve_source_kind` **уже поддерживают** этот
  режим ([script_generator.py:50-54](../../src/news/script_generator.py:50)) —
  нового кода на уровне движка не требуется. Это **не** новая script-engine
  функциональность.
- **после переноса capability и callers:** `apps/news_to_short` → RETIRE/DELETE
  в соответствии с OD-2 и registry K08.
- **соответствует тестам deep-dive:** T9.
- **risk boundary: PUBLIC CLI SURFACE — owner tripwire.** Ревизия рекомендует
  перенос, но **не является разрешением реализовать его** (§22).
- **required verification:** targeted + `smoke` + `full`.

### 8.4. Что в CRITICAL-2 осознанно НЕ делается

- LLM-research не добавляется (OD-17, OD-20). Он не требуется, чтобы система
  перестала врать, и подпадает под network/paid boundary.
- `DeterministicScriptProvider` не заменяется. Проба показала: при наличии
  материала он даёт нормальный экстрактивный сценарий; экстрактивность — защита
  от выдумывания фактов.
- `research_engine` не переписывается в этой ревизии.

---

## 9. PLAN-10 changes

**Ни один ID не удаляется.** 10A / 10B / 10C / 10D после 9B/9A по-прежнему
нужны.

| Слайс | Изменение в revision 2.1 |
|---|---|
| **PLAN-10A** | без изменений по составу; добавляется примечание §9.1 |
| **PLAN-10B** | + **provider registry convergence** (§11) как отдельный под-slice, не смешиваемый с CRITICAL-1 |
| **PLAN-10C** | без изменений; порядок эскалации остаётся здесь |
| **PLAN-10D** | переформулирован (§10) |

### 9.1. Логическая когезия search-session state

**PROPOSAL + OD-24.** 9A (best-so-far), 10A (attempts/stop reasons),
10B (pagination cursor) и 10C (budget/plateau) описывают **одно** логическое
состояние одного поиска. Ревизия 2.1 фиксирует это как **проектное требование**,
а не как новый файл:

- **не создавать и не утверждать** `search_session.json` как отдельного
  persisted owner;
- **не утверждать заранее четыре независимые persisted schemas**;
- до выбора physical representation **сначала проверить существующих owners**:
  `job.json`, asset manifest, project state, completion/resume state;
- **если существующего owner можно расширить — новый файл запрещён**;
- implementation может оставаться разбитой на bounded commits: когезия
  относится к схеме и владению, а не к размеру коммита.

Цель — одна persisted truth, а не новый competing manifest.

---

## 10. LocalLibrary convergence

**Было (revision 2, PLAN-10D):** «регистрация локальной медиатеки» —
`LocalLibraryStockProvider` участвует в автоматическом поиске, если аудит
доказал ценность и безопасность.

**Проблема формулировки.** Первый audit нашёл два пути; **deep-dive нашёл три**
(§11):

| # | Путь | file:line | Проходит `query_adapter`? | Статус |
|---|---|---|---|---|
| 1 | `rank_local_assets` → `search_local_assets` | [asset_manifest_builder.py:1246-1268](../../src/news/asset_manifest_builder.py:1246) | **нет** — берёт `primary_query.split()` напрямую | **CANONICAL по факту использования** |
| 2 | `LocalLibraryStockProvider` | [local_library_provider.py:21](../../src/providers/local_library_provider.py:21) | да (`query_languages=["en","ru"]`) | **USEFUL BUT DISCONNECTED** — не создаётся в registry |
| 3 | legacy `search_local_assets` | [video_asset_engine.py:116-135](../../src/video_asset_engine.py:116) | нет | **LEGACY**, но содержит логику, которой нет в #1 |

**FACT.** #3 содержит **diversity-резерв** (`min_local_diversity_per_scene`,
`reserved_download_slots`) — «не заполняй сцену тремя копиями одного локального
клипа, оставь место под новый». Это прямо релевантно заявленной проблеме
повторяющихся визуалов.

**FACT.** Правила прав у #1 и #2 **уже разошлись**: #1 допускает
`rights_status in ALLOWED_RENDER_RIGHTS` с дефолтом `RIGHTS_REFERENCE_ONLY`;
#2 требует `schema_version >= 1` **и** `allowed_for_render` **и** не
`review_required` **и** `license`/`provenance` как dict, плюс повторный отказ
после `apply_policy_to_candidate`. Более строгая реализация — та, которую никто
не вызывает.

**Предлагаемая формулировка PLAN-10D:**

1. **Сначала установить** для каждого из трёх путей: responsibility, callers,
   rights semantics, provenance semantics, dedup, query-language behavior,
   diversity behavior. Ни один путь **не объявляется неправильным заранее**
   только потому, что он второй или третий.
2. **Затем** — ОДИН canonical owner local-library capability.
3. **Salvage useful knowledge:** stricter rights/provenance policy (#2),
   diversity reserve (#3, через PLAN-L0), полезное ranking behavior (#1).
4. **Затем** удалить superseded paths по общему правилу retirement.
5. **Запрещено создать четвёртую реализацию.**

**Отдельный FACT-дефект для той же зоны.** `query_adapter` объявляет
`local_library` провайдером с поддержкой русского
([query_adapter.py:53](../../src/assets/query_adapter.py:53)), чего никогда не
происходит: провайдер не создаётся, а реальный локальный поиск идёт мимо
адаптера. Декларация и поведение разошлись — закрывается вместе с §11.

---

## 11. Provider registry convergence

**FACT** (deep-dive §10.3). Один и тот же набор провайдеров перечислен в **пяти**
местах, ни один список не производный от другого:

| Место | file:line | Расхождение |
|---|---|---|
| фактический конструктор | [providers/registry.py:15-37](../../src/providers/registry.py:15) | `local_library` отсутствует |
| языковая таблица | [query_adapter.py:43-56](../../src/assets/query_adapter.py:43) | 9 имён, объявляет провайдера, который не создаётся |
| порядок по умолчанию | [provider_routing.py:23-30](../../src/assets/provider_routing.py:23) | 7 имён, включая `envato_manual` |
| приоритет по source class | [scene_strategy.py:54-65](../../src/assets/scene_strategy.py:54) | `local_library` первый во всех 9 классах |
| диагностика | [provider_diagnostics.py:117-128](../../src/assets/provider_diagnostics.py:117) | 8 имён, включая `fake` |

**Предлагаемый owner:** **PLAN-10B** (существующий владелец provider contract;
уже требует `full` и уже перечисляет adapters по одному под-slice).
Альтернативный owner, если 10B будет признан слишком узким — **PLAN-13C**
(wrapper/package retirement и ownership). Finding **не остаётся orphan** в любом
случае.

**Target direction:** provider capabilities происходят из одного canonical
registry / provider contracts настолько, насколько возможно.
`ProviderCapabilities.query_languages` **уже перекрывает** таблицу
([query_adapter.py:133-138](../../src/assets/query_adapter.py:133)) — механизм
«capabilities важнее таблицы» существует; `PROVIDER_QUERY_LANGUAGES` может стать
fallback для неизвестных имён, а не источником правды.

**Ограничение (deep-dive §12.3, изменение 6):** **не выполнять в одном слайсе с
CRITICAL-1 query changes** — это расширяет risk/shared boundary. Отдельный
bounded slice после 9B.

---

## 12. Double orchestration ownership

**Finding сохранён.** **FACT** (первый audit CRITICAL-4, подтверждено deep-dive
§2): `FullscreenVoiceoverUseCase` вызывает `run_news_to_short_job` несколько раз
за один запуск (`_run_safe_pipeline`, `_run_voice_stage`, `_run_subtitles` и
четыре раза в `_render_and_export`). Каждый вызов заново создаёт
`NewsProjectStore`, заново загружает `job.json` и заново входит в цикл по
стадиям.

**Оценка для текущего roadmap:**

- это **не** prerequisite CRITICAL-1/2;
- не блокирует query/input fixes;
- severity: **HIGH architecture debt**, не первый product blocker.

**Назначенный owner: PLAN-13** — «ownership migration, retirement и
root-structure classification», под-slice **PLAN-13B (ownership transfer)**.
Обоснование: responsibility действительно совпадает — это вопрос «кто владелец
порядка pipeline stages», то есть application/ownership convergence, а не
поиск/ввод. Registry C05 («определить app-specific и shared ownership»)
дополняется явной строкой про двойную оркестрацию.

**Target direction:** один owner порядка pipeline stages.

**Решение сейчас не проектируется.** При implementation сначала подтвердить
фактических `resume` / `force-stage` / `stop-stage` callers и публичное
поведение; условная логика внутри цикла существует потому, что оба режима
обязаны сосуществовать, и её снятие меняет наблюдаемое поведение resume.

---

## 13. Semantic / Vision ordering

**Подтверждено (OD-22).** Порядок:

```
provider-ready query → candidates → semantic/Vision → rank/select
```

Не наоборот. Подключать Vision к ранжированию кандидатов, которых ноль,
бессмысленно.

- **PLAN-9C сохраняется** без изменения цели и зон.
- **Новый semantic stack не создаётся.**
- PLAN-9C по-прежнему обязан заставить **существующий** semantic result реально
  влиять на decision path — после того как PLAN-9B обеспечит кандидатов.
- PLAN-1C′ остаётся обязательным перед PLAN-9C (capability owner gate
  asset/semantic).
- `vision_validator` (7-строчная заглушка, безусловно возвращающая
  `vision_validation_enabled: False`) остаётся зафиксирован как дефект wiring,
  а не как отдельный слайс.

---

## 14. Renderer / export quality findings

Три finding'а, ни один из которых не блокирует CRITICAL-1/2 и ни один из
которых не остаётся orphan.

### 14.1. Export-target truthfulness

**FACT.** Каталог регистрирует пять целей, включая `tiktok.mp4` и `stories.mp4`
([catalog.py:261-305](../../src/production_catalog/catalog.py:261)), оба шаблона
объявляют все пять в `supported_export_targets`, а `_copy_platform_outputs`
создаёт только три файла ([final_renderer.py:475](../../src/news/final_renderer.py:475)).
`tiktok.mp4` и `stories.mp4` не создаются никогда.

- **Предпочтительное направление (OWNER):** сначала **truthful
  capability/catalog fix**, а не создание дополнительных одинаковых копий видео
  ради соответствия старому каталогу.
- **Назначенный owner:** **PLAN-11** как предусловие M1 evidence — каталог,
  обещающий несуществующий output, делает product evidence недостоверным.
  Сам fix — правка `supported_export_targets`, отдельного ID не требует.
- **Registry:** новая строка (§18).

### 14.2. FFmpeg single-pass

**FACT.** Каждый сегмент кодируется `libx264 -preset veryfast -crf 23`, затем
конкатенация перекодируется в `-crf 20`, затем прожиг ASS-субтитров — ещё раз в
`-crf 21`. Три поколения lossy-кодирования.

- **Target direction:** по возможности один final encode / filter graph вместо
  нескольких поколений re-encode.
- **Обязательные условия:** characterization **сначала**; **не менять renderer
  одновременно с search/input**.
- **Назначенный owner:** **PLAN-8** — roadmap продуктового качества фиксирует
  это как отдельный будущий product-quality slice после PLAN-11. Новый PLAN-ID
  сейчас не создаётся.
- **Registry:** новая строка (§18).

### 14.3. Побочные наблюдения, зафиксированные без owner-слайса

- **FACT.** Один и тот же master копируется под три имени
  ([final_renderer.py:474-478](../../src/news/final_renderer.py:474)); настоящая
  адаптация под площадку не выполняется, хотя `safe_zone_profile` в каталоге
  объявлен. Идёт вместе с 14.1.
- **FACT.** `config/semantic_visual.json` называет несуществующие модели
  (`gpt-5.6-terra`, `gpt-5.6-luna`). Сегодня ничего не ломает (backend выключен),
  но включение даст ошибку на первом вызове. Закрывается в радиусе PLAN-9E.

### 14.4. Что в renderer НЕ трогать

`final_renderer.py` остаётся до отдельного renderer-слайса: экранирование
апострофов под правила concat-демуксера, объяснение ненадёжности
`-shortest` + `-c:v copy`, `apad` под sidechain — это код, написанный по
реальному выводу, и он сохраняется дословно.

---

## 15. Channel / project convergence

**HIGH-3 первого аудита — новый этап НЕ создаётся.**

**FACT.** Три несовместимые формы канала (`channel.json`;
`channel_config.json` + `voices.yaml`; legacy-профиль `pipeline.py --channel`),
тип определяется эвристикой по форме файла. Две системы проектов (`job.json` со
стадиями и `project.json` без), объединённые только read-only слоем.
Следствие в UX: `project validate` работает только для story card, `resume` —
только для fullscreen.

**Уже покрыто:** **PLAN-1B** (capability gate application/shared ownership,
C05–C08, C12–C16) и **PLAN-13** (M02, C10, PLAN-13E root-structure
classification).

**Цель поздней архитектурной конвергенции:**

- разобраться в нескольких channel formats;
- разобраться в нескольких project/state formats;
- мигрировать callers;
- **сохранить tolerant readers**;
- удалить transitional duplicates **после** migration.

**НЕ является prerequisite** текущих search/input fixes. Пока активных workflow
два и вход одного из них нечестен, унификация хранилища — дорогая работа без
продуктового эффекта.

---

## 16. Anime Factory → Video Repurposer roadmap

**OWNER (OD-23).** Anime Factory **не** является disposable legacy application.
`enabled=False` / `implementation_status="planned"` в каталоге **не** означает,
что продукт не нужен — capability выключена, а не отвергнута (locked decision 5
действующего плана уже это фиксирует).

**Это source implementation будущего второго продукта — VIDEO REPURPOSER.**
Второй clip pipeline с нуля запрещён (locked decision 4, ADR 0016).

**Порядок roadmap:**

```
1. стабилизировать Content Creator engine
2. сделать нормальный UI Content Creator
3. отдельный deep audit существующего Anime Factory
4. классифицировать каждую capability: KEEP · MIGRATE · REWRITE · SHARE · DELETE
5. построить Video Repurposer из существующего Anime Factory + shared core
6. затем его UI
```

**Существующие полезные capabilities — не переписывать заранее:** Whisper-
транскрипция, scene detection, face detection, dynamic crop, candidate scoring.
Это единственный настоящий ML в репозитории.

**Разделение двух вопросов — обязательное:**

| Предмет | Классификация | Owner |
|---|---|---|
| Anime Factory **capability** | **PRESERVE FOR FUTURE PRODUCTIZATION** | post-UI roadmap (PLAN-8 записывает, PLAN-13 не мигрирует раньше времени) |
| Anime **runtime внутри source repo** (`input/`, `episodes/`, `artifacts/`, `output/media`) | **FIX LATER VIA WORKSPACE** — defect | **PLAN-14** (Runtime Workspace), registry C15 |

**FACT.** `PROJECT_ROOT = Path(__file__).resolve().parents[1]`, эпизоды
создаются как `PROJECT_ROOT / "episodes" / <episode>`, `WorkspacePaths` не
используется. Это дефект расположения runtime, а не дефект capability.

**Deep audit Anime Factory в revision 2.1 не запускается и не планируется как
ближайший шаг** — он идёт после UI Content Creator.

---

## 17. Future AI / advanced editing — deferred

**OWNER (OD-17, OD-20).** В критический execution plan сейчас **не добавляется**.

Future roadmap (владелец — `PRODUCT_PLAN.md`, PLAN-8) может содержать короткую
owner note: после стабильного production engine возможно добавить AI research,
idea generation, script generation, autonomous creative direction, advanced
editing/motion/plugins.

**Сейчас:**

```
NO IMPLEMENTATION
NO PLACEHOLDER PACKAGES
NO SPECULATIVE INTERFACES
NO NEW BLOCKERS
```

**Единственное архитектурное требование — future-proofing rule.** Downstream
production pipeline не должен предполагать, что script обязательно создан внутри
AI-YouTube. Prepared external content (человек, ChatGPT, Claude, другой AI,
внешний сервис, ручной ввод) остаётся нормальным first-class input. Если
будущий AI authoring появится:

```
AI research / script layer → тот же ContentInput / prepared content contract
                           → существующий downstream video production engine
```

Speculative abstractions под это сейчас не создаются. Отмечу отдельно:
`LLMScriptProvider` уже зарегистрирован как `implementation_status="planned"` —
это существующая точка подключения, и её достаточно; второй placeholder не нужен.

**CRITICAL-3 первого аудита («в content path почти нет AI») не считается current
critical defect** и отдельного этапа не получает.

---

## 18. Cleanup additions

**PROPOSAL.** Строки для `CLEANUP_REGISTRY.md`. **Ни одна не даёт права на
действие.** Для каждой действует общее правило:

```
replacement working → callers migrated → targeted tests green → then delete old
```

**FACT** (deep-dive §15.3): в текущем registry **нет ни одной** записи про
`query_adapter`, `GLOSSARY`, `legacy_broad_query`,
`_apply_video_first_topic_briefs`, дублирование генераторов запросов,
дублирование путей к локальной медиатеке и пять реестров провайдеров.

| Предлагаемый ID | Предмет | Класс | Action | Gate |
|---|---|---|---|---|
| C34 | `query_adapter::GLOSSARY` + `_glossary_terms` — substring matcher | FACT | **MIGRATE THEN DELETE** (термины как seed, матчер заменить) | PLAN-9B-1 → 9B-3 |
| C35 | `script_generator::_apply_video_first_topic_briefs` (orca-hardcode) + `tests/test_script_engine_pipeline.py:141-157` | FACT | **MIGRATE THEN DELETE** (форма ответа, трёхуровневые queries, `must_avoid`) | PLAN-9B-2 → 9B-3 |
| C36 | `legacy_format::legacy_broad_query` — **0 доставок**, шум в persisted-плане | FACT | **DELETE** | **только после** 9B-1 и дефекта №4 |
| C37 | `visual_plan::make_stock_query` — deprecated, 0 production-callers | FACT | **DELETE** | вместе с C36 |
| C38 | `semantic_selection/query_generator.py` + `_animal_category` — 5 callers, питает envato/отчёты | FACT | **MIGRATE THEN DELETE** (лестница `exact→broad→environment→atmospheric`) | PLAN-9B-3, после миграции **всех** callers |
| C39 | четыре независимых генератора запросов | FACT | convergence к `query_adapter` | PLAN-9B |
| C40 | три пути к локальной медиатеке, разошедшиеся правила прав | FACT | **ONE CANONICAL OWNER**; четвёртый путь запрещён | **PLAN-10D** |
| C41 | пять расходящихся списков провайдеров; `local_library` объявлен и не создаётся | FACT | convergence к `providers/registry` + `ProviderCapabilities` | **PLAN-10B** (fallback: 13C) |
| C42 | `apps/news_to_short` — уникальные `--text`/`--text-file`, обходит `create_content` | FACT | **MIGRATE UNIQUE CAPABILITY THEN RETIRE** (OD-2, OD-19, K08) | **PLAN-9B-5** |
| C43 | double orchestration: несколько вызовов `run_news_to_short_job` из одного use case | FACT | один owner порядка stages | **PLAN-13B** (дополняет C05) |
| C44 | `tiktok`/`stories` в `supported_export_targets` не производятся renderer | FACT | truthful catalog fix | **PLAN-11** (предусловие M1) |
| C45 | три поколения lossy-encode в final render | FACT + INFERENCE | characterization → single-pass filter graph | **PLAN-8 roadmap**, после PLAN-11 |
| C46 | legacy `build_query_variants` — лестница расширения | FACT | **MIGRATE KNOWLEDGE** → PLAN-9B-2 | **PLAN-L0** |
| C47 | legacy diversity-резерв локальных слотов | FACT | **MIGRATE KNOWLEDGE** → PLAN-10D | **PLAN-L0** |
| C48 | `visual_keywords` в `content/**` — практика «EN-ключи отдельным полем» | FACT | **MIGRATE KNOWLEDGE** (ADR/registry) | **PLAN-L0** |
| C49 | subprocess network-guard measurement: 12 модулей, не 7 | FACT | measurement, **не** invariant | **PLAN-6B** (§14 задания) |

**Отдельно сохранить из legacy как historical product knowledge (OWNER):**
query expansion ladder · local-library diversity reserve · практика внешних
английских visual keywords. **Старый pipeline ради этих идей не сохраняется.**

---

## 19. Existing PLAN sections unchanged

**PROPOSAL.** Revision 2.1 **не трогает** следующее. Перечислено явно, чтобы
исполнитель канонической правки не расширил diff.

**Разделы плана без изменений:** Шаблон задания для нового чата ·
Source-of-truth precedence · Locked owner decisions 1–13 · Owner decisions
ревизии 2 (OD-1…OD-10) · Safety boundaries и `Preserved runtime corpus` ·
Agent Autonomy Model целиком · Reversible retirement mechanism ·
Test classification · Measurement policy (кроме одной цифры, §20) ·
Execution protocol 1–12 · Completion and archive policy.

**PLAN-ID без изменений содержания:** PLAN-0 · PLAN-1 / 1A / 1B / 1D ·
PLAN-2 · PLAN-3 · PLAN-4 · PLAN-5 · PLAN-6A · PLAN-6C · PLAN-6D · PLAN-6E ·
PLAN-7 · PLAN-L0 (кроме трёх добавленных salvage-находок) · L1 · L2 · L3 · L4 ·
PLAN-9D · PLAN-9E · PLAN-10A · PLAN-10C · PLAN-12\* · PLAN-14\* (кроме явной
записи про Anime runtime) · PLAN-15.

**Сильные foundations, которые ревизия явно сохраняет и запрещает переписывать
ради «унификации»:**

- `src/assets/completion/` — canonical readiness vocabulary, лестница A–F,
  `blocking_reasons`, `_rights_are_allowed` с вето каждой копии;
- rights / provenance / `must_avoid` / misleading gates — **сохранить дословно**;
- `VisualBrief` — схема уже полная и доказана orca-путём; **новыми полями не
  расширять**, пока существующие не начнут заполняться автоматически;
- `ScriptValidationResult` и существующий `script_metadata`;
- `DeterministicScriptProvider` — экстрактивность как защита от выдумывания;
- `LegacyTemplateScriptProvider` как explicit legacy/template provider;
- `src/subtitles/` — один engine с явным списком того, чего он не делает;
- `src/audio/scene_timeline.py` — «реальная озвучка важнее плана»;
- `src/production_catalog/` — единственный честный registry;
- `src/projects/ProjectRepository` — read-only поверх двух форм, явный отказ
  стать третьей системой;
- поведение final renderer до отдельного renderer-слайса;
- `tests/network_guard.py` — guard на уровне сокета;
- принцип **fail-closed** в `query_adapter`: «нет английских доказательств → не
  отправлять запрос». Чинить надо источник слов, а не отключать защиту. Любое
  предложение «просто отправлять русский текст в Pexels» — откат к состоянию,
  которое уже давало 0 результатов на 16 запросов у Wikimedia и NASA;
- `route_providers` / `scene_strategy` — классификация source class в пробе
  отработала осмысленно; проблема не в маршрутизации;
- плотные объясняющие комментарии — самый ценный актив проекта, ведомого
  агентами.

---

## 20. Exact canonical delta required

**Как читать.** Каждая строка — точечная правка `PROJECT_EXECUTION_PLAN.md`
(или `CLEANUP_REGISTRY.md`). Полный rewrite плана **не требуется и запрещён**.
`OWNER APPROVAL` в этой таблице означает «нужно ли одобрение владельца для
внесения правки в план», а не для последующей реализации (последнее — §22).

### 20.1. Critical path

| CURRENT SECTION | PROPOSED CHANGE | WHY | EVIDENCE | RISK | OWNER APPROVAL? |
|---|---|---|---|---|---|
| «Критический путь (ревизия 2)», строки ~512–535 | Заменить единую цепочку на: блокеры `1D → 2 → 3 → 4` + risk-boundary таблица §5.5; первым product-слайсом становится `PLAN-9B-0/9B-1` | Governance не должен задерживать дешёвое product-исправление без конкретной защищаемой boundary | OD-26; deep-dive §5.2 | средний: неверная оценка boundary допустит незащищённое изменение — митигируется таблицей §5.5 | **да** |
| там же | Блок «Параллельно» дополнить: PLAN-5, PLAN-6A/6D/6E переходят в параллель с явным указанием их gate | Каждый blocker обязан иметь однострочное обоснование | §5.4 | низкий | **да** |
| «Current checkpoint» → «Заблокировано» | Переписать: PLAN-9A блокируется `PLAN-9B-2 + PLAN-1C′`; PLAN-9B-1 блокируется `1D → 2 → 3 → 4` | Следствие перестановки | §5.3 | низкий | да |
| PLAN-1C′ → «зависимости: PLAN-6E» | Снять зависимость от 6E | Docs-only ownership inventory не требует существования reviewer | §5.4 | низкий | **да** |
| frontmatter: `plan_revision: 2` | → `2.1`; `updated_at`; `owner_decisions_date` | Версионирование | — | нулевой | нет |

### 20.2. PLAN-9A

| CURRENT SECTION | PROPOSED CHANGE | WHY | EVIDENCE | RISK | OWNER APPROVAL? |
|---|---|---|---|---|---|
| PLAN-9A → «prerequisite chain» | Заменить на `PLAN-9B-2 + PLAN-1C′` | Persistence осмысленна только после появления кандидатов | deep-dive §5.2 (6/6 сцен пусты во всех темах) | низкий | **да** |
| PLAN-9A → «status: blocked» | Сохранить `blocked`, сменить блокер | — | — | нулевой | нет |
| PLAN-9A → состав/ограничения/approval | **не менять** | Уже выданный approval покрывает именно этот состав | план, «Уже выданные owner approvals» | — | нет |
| PLAN-9A | Добавить одну строку: состав проектировать с учётом логической когезии 9A/10A/10B/10C; `search_session.json` **не** утверждается | OD-24 | первый audit IDEA-3 (переформулировано) | низкий | да |

### 20.3. PLAN-9B

| CURRENT SECTION | PROPOSED CHANGE | WHY | EVIDENCE | RISK | OWNER APPROVAL? |
|---|---|---|---|---|---|
| PLAN-9B → «разрешённые зоны: `semantic_selection/query_generator.py`» | **Заменить** на `src/assets/query_adapter.py` (+ per-slice зоны §7.1) | Модуль не участвует в формировании remote-запросов | deep-dive §2, §10.1 | **низкий, но правка обязательна**: без неё исполнитель либо нарушит scope, либо закроет шаг, не достигнув SUCCESS CRITERIA | **да** |
| PLAN-9B → название и цель | Расширить до «input/query truth» | CRITICAL-2 не имел owner ни в одном ID | deep-dive §15.2 #4 | средний: этап становится крупнее — митигируется шестью bounded под-слайсами | **да** |
| PLAN-9B | Добавить под-слайсы 9B-0…9B-5 с раздельными зонами и явным порядком выполнения | Разные ownership/risk boundaries в одном ID | прецедент PLAN-6D, PLAN-12, PLAN-13 | низкий | **да** |
| PLAN-9B → «лестница запросов» | Предварить пунктом «источник провайдерского языка» | Без источника английских слов лестница расширяет ноль | deep-dive §15.2 #5 | низкий | да |
| PLAN-9B → «граница слайса» | Сохранить: routing/эскалация остаются у 10B/10C/10D | Уже верно в revision 2 | план, строки 1344–1351 | нулевой | нет |
| PLAN-9B | Добавить: topic-hardcode inventory — **PROVISIONAL**, число файлов не invariant | Первый audit нашёл 6 модулей, deep-dive — главный носитель в седьмом | §7.1 | низкий | да |
| PLAN-9B | Добавить: hardcode внутри `modes.py:295-296` снимается только с отдельным обоснованием; сам gate неприкосновенен | Литералы живут в `[HARD]` safety gate | первый audit HIGH-1 | **средний** | **да** |

### 20.4. PLAN-9C

| CURRENT SECTION | PROPOSED CHANGE | WHY | EVIDENCE | RISK | OWNER APPROVAL? |
|---|---|---|---|---|---|
| PLAN-9C → «status: blocked (PLAN-9A и закрытый C01-SEM)» | Сохранить; явно записать порядок `query → candidates → semantic → rank` | OD-22 | deep-dive §5.2; первый audit CRITICAL-5 | низкий | да |
| PLAN-9C | Добавить FACT: `semantic_rerank_enabled: False` пишется жёстко; неизменность отбора — инвариант сервиса | Исполнитель должен знать, что это не «включить флаг» | первый audit CRITICAL-5 | низкий | нет |

### 20.5. CRITICAL-2 — input/source behavior

| CURRENT SECTION | PROPOSED CHANGE | WHY | EVIDENCE | RISK | OWNER APPROVAL? |
|---|---|---|---|---|---|
| «Продуктовая рамка PLAN-9 и PLAN-10», таблица дыр | Добавить две строки выше генерации запросов: честность источника сценария (9B-4), канонический вход «исходный текст» (9B-5) | Ни один ID не покрывал CRITICAL-2 | deep-dive §9 | низкий | **да** |
| новый PLAN-9B-4 | strict → `allow_legacy_fallback=False`; issue-код в `ScriptValidationResult`; `quality_check` читает `provider_id`+`fallback_reason` | Silent fallback выглядит как успех; после починки CRITICAL-1 шаблон поедет в publish | deep-dive §9.1, §9.3, §9.5 | средний: меняется наблюдаемое поведение strict — митигируется парой с 9B-5 | **да** |
| новый PLAN-9B-4 | Явно: `content_origin` **не** создаётся; `LegacyTemplateScriptProvider` **не** удаляется | OD-18; второй источник той же правды запрещён | deep-dive §9.5 | низкий | да |
| новый PLAN-9B-5 | MIGRATE `--text`/`--text-file` → канонический CLI (кандидат `source_text`), затем retire `apps/news_to_short` | Единственная уникальная capability в `apps/`; движок уже поддерживает | deep-dive §7, §9.2, §5.4 | средний: **public CLI surface** | **да** — и отдельно при implementation (§22) |
| PLAN-9B-5 | Имя режима **не закреплять** до проверки CLI contract | naming conventions не проверялись | OD-19 | низкий | да |

### 20.6. PLAN-10D

| CURRENT SECTION | PROPOSED CHANGE | WHY | EVIDENCE | RISK | OWNER APPROVAL? |
|---|---|---|---|---|---|
| PLAN-10D → «цель: `LocalLibraryStockProvider` участвует в поиске…» | Переформулировать: сначала установить responsibility/callers/rights/provenance/dedup/query-language/diversity **трёх** путей, затем ОДИН canonical owner | Путь уже включён другой реализацией; правила прав разошлись | deep-dive §11; первый audit HIGH-2 | средний: rights semantics — `[HARD]` boundary | **да** |
| PLAN-10D | Добавить: salvage diversity-резерва из legacy; **четвёртая реализация запрещена** | Прямо релевантно повторяющимся визуалам | deep-dive §11 | низкий | да |
| PLAN-10D | Добавить FACT: `query_adapter` объявляет `local_library` с поддержкой RU, чего не происходит | Декларация разошлась с поведением | deep-dive §11 | низкий | нет |

### 20.7. PLAN-6B — subprocess safety measurement

| CURRENT SECTION | PROPOSED CHANGE | WHY | EVIDENCE | RISK | OWNER APPROVAL? |
|---|---|---|---|---|---|
| «Известный риск», строка ~427: «**7** test-модулей» | Исправить на **12**, с пометкой «measurement, не invariant» | `grep -l subprocess tests/*.py` → 12 модулей | первый audit HIGH-6 | низкий | да |
| PLAN-6B | Добавить: guard в test-пакете **не** наследуется subprocess; оценить environment kill-switch как альтернативу «расширению guard на subprocess boundary» | Guard в тестовом пакете не может защитить чужой процесс | первый audit HIGH-6 | низкий | да |
| PLAN-6B | Записать ограничение: 6B остаётся **report-only** owner. Если выбранный механизм требует, чтобы production-код уважал env kill-switch — это production-изменение вне зон 6B и его owner — PLAN-5 (владелец runner/`smoke`) отдельным слайсом | 6B по плану ничего не мутирует | план, PLAN-6B/14F | **средний** — требует решения владельца | **да** |

### 20.8. PLAN-13 — orchestration / channel / project

| CURRENT SECTION | PROPOSED CHANGE | WHY | EVIDENCE | RISK | OWNER APPROVAL? |
|---|---|---|---|---|---|
| PLAN-13B | Добавить double orchestration как явный scope-пункт; target direction «один owner порядка pipeline stages»; решение не проектируется сейчас | Finding не должен остаться orphan | первый audit CRITICAL-4; deep-dive §2 | низкий (запись), высокий (реализация) | да |
| PLAN-13B | Добавить обязательное предусловие: подтвердить `resume`/`force`/`stop-stage` callers и public behavior до изменения | Условная логика существует ради сосуществования двух режимов | первый audit CRITICAL-4 | низкий | нет |
| PLAN-1B / PLAN-13 | Явно записать: HIGH-3 (channel schemas + project systems) покрыт здесь; **новый этап не создаётся**; не prerequisite search/input fixes | Уже покрыто; дорогая работа без продуктового эффекта сейчас | первый audit HIGH-3 | низкий | да |
| registry C05 | Дополнить строкой C43 | — | — | низкий | нет |

### 20.9. PLAN-14 — Anime runtime workspace

| CURRENT SECTION | PROPOSED CHANGE | WHY | EVIDENCE | RISK | OWNER APPROVAL? |
|---|---|---|---|---|---|
| PLAN-14 / registry C15 | Явно разделить: Anime **capability** = PRESERVE FOR FUTURE PRODUCTIZATION; Anime **runtime внутри source repo** = FIX LATER VIA WORKSPACE | Два разных предмета, смешение приводит к ретайру нужного продукта | OD-23; первый audit MEDIUM-3 | низкий | **да** |
| PLAN-14 | Записать, что `enabled=False`/`planned` **не** является доказательством ненужности | Locked decision 5 усиливается | OD-23 | нулевой | да |

### 20.10. Post-UI Video Repurposer roadmap

| CURRENT SECTION | PROPOSED CHANGE | WHY | EVIDENCE | RISK | OWNER APPROVAL? |
|---|---|---|---|---|---|
| PLAN-8 (`PRODUCT_PLAN.md`) | Записать шестишаговый roadmap §16 как post-rescue roadmap; deep audit Anime Factory — **после** UI Content Creator | Владелец зафиксировал порядок | OD-23 | низкий | **да** |
| PLAN-8 | Записать future AI/advanced editing note §17 с явным `NO IMPLEMENTATION / NO PLACEHOLDER / NO SPECULATIVE INTERFACES` | OD-17, OD-20 | — | низкий | **да** |
| PLAN-8 | Записать future-proofing rule: prepared external content — first-class input | OD-20 | — | низкий | да |

### 20.11. Cleanup registry additions

| CURRENT SECTION | PROPOSED CHANGE | WHY | EVIDENCE | RISK | OWNER APPROVAL? |
|---|---|---|---|---|---|
| `CLEANUP_REGISTRY.md`, новая таблица «Ревизия 2.1 findings» | Добавить C34–C49 (§18) | Ни одной записи про query/провайдеров/медиатеку сегодня нет | deep-dive §13, §15.3 | низкий — строка не даёт права на действие | **да** |
| `Knowledge salvage log` → обязательные families | Добавить три находки: expansion ladder, diversity reserve, EN-keywords practice | Прямо названы deep-dive | deep-dive §13, §16 | низкий | да |
| registry K08 / OD-2 | Уточнить: `news_to_short` ретайрится **после** PLAN-9B-5 | Порядок «capability → callers → retire» | OD-19 | низкий | да |
| registry | **Никаких изменений в `Retired`** — ничего не ретайрено | — | — | нулевой | нет |

---

## 21. Findings that still require evidence

**PROPOSAL.** Ниже — то, что revision 2.1 **не доказала** и что должно быть
проверено в момент implementation, а не принято на веру.

| # | Открытый вопрос | Почему не закрыт сейчас | Кто закрывает |
|---|---|---|---|
| E-1 | Точное имя канонического input mode (`source_text` или иное) | CLI naming conventions построчно не сверялись; закреплять имя без проверки contract запрещено | PLAN-9B-5 |
| E-2 | Является ли новый `ProviderQuery.source` **schema-level** изменением asset manifest или добавлением значения | Не проверено, попадает ли `source` в persisted manifest как enum с валидацией | PLAN-9B-1 (если schema-level → tripwire, §22) |
| E-3 | Возможна ли миграция всех пяти callers `semantic_selection/query_generator` | Callers перечислены, но их семантика (envato-метаданные, отчёты) построчно не читалась | PLAN-9B-3 |
| E-4 | Каким должен быть метод provider-language adaptation | OD-16 запрещает фиксировать заранее; критерии заданы, выбор не сделан | PLAN-9B-1 |
| E-5 | Верно ли, что PLAN-10B — правильный owner provider-registry convergence | Оценено по совпадению responsibility, не по фактическому объёму слайса | владелец / PLAN-10B |
| E-6 | Полный inventory topic-hardcodes | **PROVISIONAL**: первый audit — 6 модулей, deep-dive нашёл главный в седьмом; repo-wide повторный поиск не запускался (запрещён заданием) | PLAN-9B-2 |
| E-7 | Rights/provenance semantics трёх путей к локальной медиатеке | Правила прочитаны, фактическое поведение на реальном индексе не проверялось | PLAN-10D |
| E-8 | Механизм subprocess network kill-switch и его owner | Выбор между расширением guard и env-переменной не сделан; второй вариант выходит за report-only зоны 6B | владелец / PLAN-6B / PLAN-5 |
| E-9 | Public behavior `resume`/`force`/`stop-stage` при снятии double orchestration | Callers не перечислены построчно | PLAN-13B |
| E-10 | Число 12 subprocess-модулей | Это **measurement** от `adcbb19`, не invariant; при изменении tests изменится | PLAN-6B |
| E-11 | Зелёность baseline | Ни первый audit, ни deep-dive, ни эта ревизия не запускали full suite | PLAN-4 |
| E-12 | Совместимость CRITICAL-2 fix с существующими persisted проектами | Tolerant-reader поведение при `script_provider == "legacy_template"` в старых проектах не проверялось | PLAN-9B-4 |
| E-13 | Хостинг CRITICAL-2: под-слайсы PLAN-9B **или** отдельный новый ID | Задание требует минимизировать новые ID; архитектурно это отдельная ownership boundary | **владелец**, §22 |

---

## 22. Owner approvals / tripwires

**Этот proposal не выдаёт никаких новых разрешений.** Утверждение revision 2.1
владельцем является разрешением **изменить план**, а не разрешением реализовать
описанное.

### 22.1. Изменения, требующие owner approval при implementation

| Boundary | Конкретный слайс | Что именно срабатывает |
|---|---|---|
| **public CLI / input mode** | **PLAN-9B-5** | Перенос `--text`/`--text-file` в канонический CLI **меняет public CLI surface**. Ревизия рекомендует перенос, но **это не автоматическое разрешение реализации** |
| **наблюдаемое поведение strict** | PLAN-9B-4 | strict перестаёт принимать `topic` без материала — меняется exit-поведение продукта для существующего документированного входа |
| **persisted bytes / schema / layout** | PLAN-9A; PLAN-9B-1 при исходе E-2; PLAN-10A/10B/10C | approval PLAN-9A покрывает **ровно** состав, описанный в PLAN-9A, и **не переносится** на 9B…9E, PLAN-10\* и PLAN-L |
| **destructive retirement** | PLAN-9B-2 (orca-hardcode), PLAN-9B-3 (GLOSSARY matcher, `legacy_broad_query`, `make_stock_query`, `query_generator`), PLAN-9B-5 (`apps/news_to_short`) | обязательны: зелёная замена, миграция callers, annotated tag, внешний `git bundle`, строка в `Retired` |
| **paid / network / model** | уровень 3 provider-language adaptation (§6/OD-16), PLAN-9E | approval **на каждое конкретное действие**; ноль платных вызовов без него |
| **runtime / user data moves** | PLAN-14D/14E, Anime runtime | `Preserved runtime corpus`, проверенный абсолютный путь, отдельный approval |
| **`[HARD]` safety gate** | снятие orca-литералов из `modes.py:295-296` | требует отдельного обоснования; сам gate неприкосновенен |

### 22.2. Решения, которые владелец должен принять до канонической правки

1. **E-13.** CRITICAL-2 остаётся под-слайсами PLAN-9B (рекомендация: **да**,
   минимизирует новые ID, прецедент bounded под-слайсов существует) — или
   получает один новый ID.
2. **§5.4.** Снятие зависимости PLAN-1C′ от PLAN-6E.
3. **§20.7.** Owner для subprocess kill-switch, если механизм окажется
   production-side.
4. **§14.** Согласие на назначение export-truthfulness → PLAN-11 и FFmpeg
   single-pass → PLAN-8 roadmap, без новых ID.

### 22.3. Что остаётся неизменным

Tripwire не отменяется и не ослабляется. Approval — это факт, а не исключение из
правила. Ни одно предложение выше не ослабляет `[HARD]`: secrets, платные и
сетевые вызовы, destructive Git, удаление реальных user data, rights/`must_avoid`/
misleading/conflict gates, публикация, изменение persisted contract без tolerant
reader, второй одновременно живущий canonical owner.

---

## 23. Recommended next exact action

**PROPOSAL — строгий порядок.**

1. **Владелец читает этот proposal и принимает четыре решения §22.2.**
   До этого канонический план не трогается.

2. **Один docs-only slice «revision 2.1»**, allowed zones — ровно два файла:
   `docs/current/PROJECT_EXECUTION_PLAN.md` и
   `docs/current/CLEANUP_REGISTRY.md`. Содержание — таблица §20, ничего сверх
   неё. Полного rewrite плана не выполнять.
   Required verification: `tools.qa.check_agent_docs`, `git diff --check`.
   Один commit, trailer `Plan-Step: PLAN-REV-2.1`.

3. **Затем — PLAN-1D-routing** (текущий `current_checkpoint`, не начат).

4. **Затем — PLAN-2 → PLAN-3 → PLAN-4.**

5. **Затем — PLAN-9B-0** (characterization, ноль production-изменений) и
   **PLAN-9B-1** (provider-language foundation).

Параллельно после зелёного PLAN-4 — PLAN-5, PLAN-6A/6D/6E, PLAN-6B/6C,
PLAN-7, PLAN-8, PLAN-L\*.

**Чего делать НЕ надо:** не создавать третий плановый документ · не создавать
PLAN-P0 · не начинать implementation до канонической правки · не переписывать
`completion/`, `subtitles/`, `scene_timeline`, каталог, renderer ·
не реструктурировать `tests/` · не создавать `resources/` заранее ·
не вводить второй словарь состояний · не создавать `search_session.json` ·
не создавать `content_origin` · не создавать AI research/authoring слой ·
не откладывать продукт до идеального репозитория.

---

## Проверки после создания файла

```
git diff --check          → выполнено
git status --short --branch
```

Изменён только этот файл. Canonical plan, `CLEANUP_REGISTRY.md`, `AGENTS.md` и
`START_HERE.md` не изменялись. Production-код не выполнялся. PLAN-1D не
начинался. Commit не создавался.
