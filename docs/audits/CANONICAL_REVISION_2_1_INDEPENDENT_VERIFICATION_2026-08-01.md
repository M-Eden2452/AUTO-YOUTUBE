---
status: audit
audit_date: 2026-08-01
audit_head: affa138
working_branch: governance-reset
scope: independent read-only verification of canonical revision 2.1
method: полное чтение двух canonical файлов, четырёх audit-документов и пяти ADR + проверка утверждений по коду, Git и одной offline-пробе вне репозитория
changes_to_repository: только этот файл (untracked, git add не выполнялся)
commit_created: no
---

# Canonical Revision 2.1 — Independent Read-Only Verification

Дата: 2026-08-01 · Ветка: `governance-reset` · HEAD: `affa1389e76ea655436fd44a520d27f24e3d3205` (`affa138`)
Режим: read-only · Объект: `docs/current/PROJECT_EXECUTION_PLAN.md` + `docs/current/CLEANUP_REGISTRY.md`

---

## 1. Executive verdict

**B. Revision 2.1 sound, minor corrections recommended.**

Ревизия 2.1 внутренне непротиворечива по существу и faithful к evidence: восемь
из восьми заявленных инвариантов зависимостей выполняются, 35 из 35 пунктов
no-loss-проверки присутствуют (33 корректно, 2 с оговоркой), а восемь из девяти
ключевых claims §13 подтверждены фактическим кодом дословно, включая самые
рискованные (`source_is_latin` как свойство набора, `and not stage`, `-c:v copy`
в concat, fail-open `review_required`, мёртвый `duplicate_penalty`).

Найдено **девять** дефектов, ни один из которых не является архитектурным:
одно фактическое противоречие зависимостей в сводном графе (`PLAN-9E` поставлен
перед `PLAN-10C`, хотя сам требует `PLAN-10C`), одно опровергнутое кодом
`[FACT]` про уникальность `--text`/`--text-file` (плюс пропущенная вторая
уникальная возможность `--assets`), два случая неоднозначной графики/формулировки
(гипотезы H1 и H2), одна незапланированная `[HARD]` rights-строка (C50), один
stale current-документ (`CURRENT_STATE.md` указывает на несуществующий checkpoint
9B-C01) и три LOW-дефекта.

Все девять правятся ~25 строками docs-only текста в двух файлах и одном
current-документе. Ни одна не требует ревизии 2.2, нового PLAN-ID или нового
deep-dive. Безопасность не ослаблена.

---

## 2. Scope: что реально прочитано

**Прочитано полностью, построчно:**

| Слой | Файлы |
|---|---|
| Canonical (объект аудита) | `docs/current/PROJECT_EXECUTION_PLAN.md` (2750), `docs/current/CLEANUP_REGISTRY.md` (751) |
| Evidence | `CRITICAL_INPUT_SEARCH_DEEP_DIVE_2026-07-31.md` (1000), `SECONDARY_ARCHITECTURE_FINDINGS_DEEP_DIVE_2026-07-31.md` (1135) |
| Evidence (структурно + §§4–12, 14, 20–23) | `PROJECT_EXECUTION_PLAN_REVISION_2_1_PROPOSAL_2026-07-31.md` (1264), `INDEPENDENT_REPOSITORY_REVIEW_2026-07-31.md` (1247) |
| Governance | `AGENTS.md` (82), `CLAUDE.md` (7), `docs/current/START_HERE.md` (71), `tools/qa/check_agent_docs.py` (189) |
| ADR | 0002, 0006, 0008, 0009, 0016 |

**Прочитано целенаправленно по коду** (для доказательства конкретного
утверждения, не построчно целиком): `src/assets/query_adapter.py`,
`src/news/pipeline.py`, `src/news/asset_manifest_builder.py`,
`src/news/final_renderer.py`, `src/media_library.py`,
`src/assets/license_policy.py`, `src/assets/provider_routing.py`,
`src/providers/registry.py`, `src/production_catalog/catalog.py`,
`src/assets/semantic_visual_service.py`, `apps/news_to_short/main.py`,
`src/ai_youtube/cli/main.py`, `src/ai_youtube/cli/commands/*`,
`src/content_creation/commands/content.py`,
`src/content_creation/request_builder.py`, `src/content_creation/models.py`,
`src/ai_youtube/apps/content_creator/workflows/fullscreen_voiceover/use_case.py`,
`tests/test_news_stage_idempotency.py`, `tests/test_apps_structure.py`,
`.claude/settings.json`, `config/license_policy.json`, `config/semantic_visual.json`.

**Исключено по указанию владельца** (§1 задания): `channels/`, `content/`,
`MOSS_TTS_Nano/`, `music/`, `output/`, `outputs/`, `project_solar_vs_nuclear/`,
`projects/`, `.env*`, `venv/`, `__pycache__/`, `anime_factory/episodes/`,
`anime_factory/input/`, `assets/library/`, `assets/cache/`,
`assets/voice_samples/`. Имена и метаданные этих путей использованы (`ls`,
`git ls-files -i -c`, `git check-ignore`, счётчики) — содержимое не читалось.

**Прочитан один versioned tracked файл внутри исключённой зоны:**
`config/video_style.json` — **нет**, не открывался. Открывались только
`config/license_policy.json` и `config/semantic_visual.json`, которые в
исключённые пути не входят и нужны были для проверки claims I и MEDIUM-5.

**Осталось непроверенным и почему:**

| Что | Почему |
|---|---|
| Зелёность baseline (1441 тест / 245 с / 4F+3E на `fe2df5b`) | §0 задания запрещает полный прогон suite; проверены только счётные величины |
| `docs/implementation` (96 файлов), `docs/audits` (прочие 9), `docs/architecture` (5) | вне scope; DEFER до PLAN-12B по C27 |
| Фактический render / FFmpeg-исполнение | цепочка установлена чтением командных билдеров; render запрещён |
| Codex skills discovery | Codex не установлен; остаётся `[ПРЕДП]` как и в плане |
| Семантика пяти callers `semantic_selection/query_generator` | построчно не читалась; остаётся PROVISIONAL (P-7) |
| Полный inventory topic-hardcodes | остаётся PROVISIONAL по плану (P-3) |

**Одна offline-проба** выполнена в session scratchpad вне репозитория
(`probe_input.py`): импорт `resolve_content_inputs`/`resolve_script_source`,
ноль сети, ноль записи в репозиторий, ноль платных вызовов. Результат — §8.B.

---

## 3. Reviewer hypothesis verdicts

| Hypothesis | Verdict | Evidence (path:line) | Correction needed? |
|---|---|---|---|
| **H1** — графика 680–686 создаёт зависимость `PLAN-9B-5b → PLAN-9A` | **AMBIGUOUS AND SHOULD FIX** | `docs/current/PROJECT_EXECUTION_PLAN.md:681-686` против `:69-70`, `:700`, `:1620-1621`; `docs/current/CLEANUP_REGISTRY.md:645-646` | **ДА** — точечная замена блока (AUDIT-R21-01/03) |
| **H2** — «меняется ровно одно ребро графа» ложно | **PARTIALLY CONFIRMED / SHOULD FIX (minor)** | `:732-733` против `:254`, `:699`, `:804` | **ДА** — 2 строки (AUDIT-R21-07) |

### H1 — разбор

**Что фактически написано** (`PROJECT_EXECUTION_PLAN.md:680-686`):

```
PLAN-9B-5a → PLAN-9B-4 → PLAN-9B-2 → PLAN-9B-3   (порядок внутри семейства 9B)
PLAN-9B-5b   после успешной миграции capability и готовности destructive gates
  → PLAN-9A → PLAN-9C → PLAN-9D → PLAN-9E
  → PLAN-10A → PLAN-10B → PLAN-10C → PLAN-10D → PLAN-11
  → PLAN-12* → PLAN-13* → PLAN-14* → PLAN-15
```

1. **Создаёт ли графика утверждение `PLAN-9B-5b → PLAN-9A`?** Формально — да,
   при естественном чтении. Строка `→ PLAN-9A` идёт непосредственно после строки
   `PLAN-9B-5b`, начинается со стрелки-продолжения и имеет отступ продолжения.
   Три следующие строки используют ту же конструкцию, то есть весь блок читается
   как **одна** цепочка, чей последний названный предшественник — `PLAN-9B-5b`.
   Это **семантическое**, не текстуальное утверждение: слов «PLAN-9A требует
   PLAN-9B-5b» в документе нет нигде.

2. **Опровергается ли это полным контекстом?** Да, тремя независимыми местами,
   и одно из них помечено как единственно действующее:
   - `:69-70` «Заблокировано» → «PLAN-9A — блокируется `PLAN-9B-2` + `PLAN-1C′`,
     дополнительно требует `PLAN-6E`»;
   - `:700` Risk-based governance model → «PLAN-9A **явно требует PLAN-6E** плюс
     PLAN-9B-2 и PLAN-1C′»;
   - `:1620-1621` собственный раздел PLAN-9A → «**prerequisite chain
     (единственная действующая, ревизия 2.1):** `PLAN-9B-2` + `PLAN-1C′` +
     **`PLAN-6E`**».
   Плюс `:1673-1676` явно отделяет 9B-5b от последовательности внутри семейства.
   Слово «единственная действующая» разрешает конфликт в пользу 9B-2.

3. **Есть ли ещё места, объявляющие 9B-3 или 9B-5b prerequisite 9A?** В
   `PROJECT_EXECUTION_PLAN.md` — **нет**. В `CLEANUP_REGISTRY.md:645-646` —
   **да, косвенно**: «первым product-этапом становится семейство `PLAN-9B`
   (`9B-0 → 9B-1 → 9B-5a → 9B-4 → 9B-2 → 9B-3`, затем `9B-5b`), `PLAN-9A`
   выполняется **после него**». Местоимение «него» указывает на **семейство**,
   то есть на всё 9B включая 9B-3 и 9B-5b. Это второе место с той же
   неоднозначностью. «Risk-boundary таблица» (`:712-722`) и «Результат после
   каждого этапа» (`:2380-2402`) зависимость 9B-5b → 9A **не** утверждают.

4. **Совместимость с owner decision D-1.** D-1 (`:250`) разделяет 9B-5 именно
   потому, что additive-часть не destructive, а destructive-часть требует
   6D+6E+reversible retirement. Ставить `PLAN-9A` (persisted-bytes boundary,
   approval уже выдан) в очередь **за** destructive retirement wrapper'а
   противоречит духу D-1: разделение делалось, чтобы **не** тащить destructive
   gates в критический путь.

5. **Есть ли product/safety причина?** Нет. Risk boundaries не пересекаются:
   `PLAN-9A` пересекает «persisted bytes / schema / layout» (`:719`),
   `PLAN-9B-5b` — «destructive retirement реализации с callers» (`:718`). Общих
   файлов нет: 9A работает в `src/news/project_store.py` /
   `asset_manifest_builder.py` радиусе, 9B-5b удаляет `apps/news_to_short/`.
   Единственная содержательная зависимость 9A от 9B — наличие provider-ready
   кандидатов, которое обеспечивают 9B-1 и 9B-2, а не retirement wrapper'а.

6. **Вердикт.** Реального dependency defect в тексте нет — есть **ambiguity
   графики**, которая при буквальном исполнении добавляет `PLAN-9A` ложный
   destructive-blocker и удлиняет критический путь на два слайса. Это подпадает
   под критерий §16.2 («допускает неоднозначное исполнение будущим агентом»),
   поэтому правка оправдана. Правка минимальна — переоформление блока (§13.1).

### H2 — разбор

**Что фактически написано** (`:729-734`): «Первым product-слайсом становится
`PLAN-9B-0/9B-1`, а не `PLAN-9A` … Меняется **ровно одно ребро графа**:
`9A → 9B` становится `9B → 9A`; все остальные зависимости сохраняются. `PLAN-5`,
`PLAN-6A`, `PLAN-6D`, `PLAN-6E` и `PLAN-1C′` **не удалены** — они переходят в
risk-based / parallel model выше.»

**Классификация семи перечисленных изменений:**

| # | Изменение | Класс | Где записано |
|---|---|---|---|
| 1 | `9A → 9B` становится `9B → 9A` | **ребро графа** (перевёрнуто) | `:238`, `:729-732`, `:1630` |
| 2 | PLAN-5 больше не blocker PLAN-9B | **ребро графа (удалено)**: revision 2 ставила 5 в цепочку до 9A | `:695`, `:1040`, `:271` |
| 3 | PLAN-6A параллелен | **ordering convention** (6A→6D сохраняется как convention) | `:696`, `:1082-1086` |
| 4 | 6D / 6E стали risk-based gates | **gate** (переадресация, не удаление) | `:697-698`, `:1087-1089` |
| 5 | прямая `1C′ → 6E` снята | **ребро графа (удалено)** | `:254`, `:699`, `:804-809` |
| 6 | `9A → 6E` установлена явно | **explicit restatement транзитивной зависимости** (через 9B-2 она существует и без записи — `:703-706`) | `:254`, `:700`, `:1620` |
| 7 | `9C → 6E` установлена явно | **новая зависимость** (транзитивного пути 9C→6E не было: 9C зависел от 9A и C01-SEM) | `:254`, `:701`, `:1844` |
| 8 | 9B разбит на sub-slices | **декомпозиция узла** с собственными gates | `:1673-1676`, `:1699-1840` |

Итого относительно ревизии 2: одно ребро перевёрнуто, **минимум два удалены**
(2 и 5), **одно добавлено** (7), одно переформулировано явно (6), один узел
декомпозирован. «Ровно одно ребро» верно **только** для основной
product-order chain (`9A ↔ 9B`), что и подтвердил Secondary Deep Dive §14 строка 2.

2. **Есть ли в документе оговорка?** Частично. Раздел «Почему 9A/9C требуют 6E
   явно, а не транзитивно» (`:703-706`) объясняет пункты 6–7, но **не** снимает
   претензию: он говорит о **добавлении** явных рёбер, а не о **снятых**. Вторая
   половина того же абзаца (`:733-734`) перечисляет пять слайсов, перешедших в
   risk-based/parallel model — это косвенная оговорка, но она не отменяет прямое
   утверждение «все остальные зависимости сохраняются».

3. **Ложна ли фраза буквально?** Да — фрагмент «все остальные зависимости
   сохраняются» прямо противоречит трём местам того же документа, где записано
   «прямая зависимость `PLAN-1C′ → PLAN-6E` **снята**» (`:254`, `:699`, `:804`).
   Это внутридокументное противоречие, а не только стилистика.

4. **Может ли агент сделать неверный вывод?** Да, ровно один — что `1C′` всё ещё
   ждёт `6E`. Последствие: `PLAN-1C′` (docs-only, единственный оставшийся gate
   `PLAN-9A`/`PLAN-9C`) искусственно откладывается за reviewer foundation.
   Ущерб ограничен, потому что раздел PLAN-1C′ (`:804-809`) утверждает обратное
   явно и с обоснованием.

5. **Вердикт.** PARTIALLY CONFIRMED. Претензия «ровно одно ребро» как таковая —
   разрешима контекстом; претензия «все остальные зависимости сохраняются» —
   фактически ложна. Правка из двух строк оправдана по §16.3. Предложенная
   reviewer'ом формулировка приемлема, но неточна («governance gates отдельно
   перераспределены» скрывает, что одно ребро **удалено**, а одно **добавлено**).
   Точнее — §13.2.

---

## 4. Actual dependency graph

Нормализовано из пяти мест записи: «Current checkpoint → Заблокировано»
(`:60-75`), «Критический путь» (`:652-686`), «Risk-based governance model»
(`:693-706`), «Risk-boundary таблица» (`:712-722`), собственный раздел каждого
PLAN-ID, «Результат после каждого этапа» (`:2380-2402`),
`CLEANUP_REGISTRY.md` «Последующая очередь» (`:624-649`).

| Узел | Explicit prerequisites | Risk gates | Parallel | Owner approvals | Противоречия между местами записи |
|---|---|---|---|---|---|
| PLAN-1D-routing | STEP 0 (выполнен) | — | — | — | нет |
| PLAN-1A | — | — | параллелен всему | — | нет |
| PLAN-1B | — | — | параллелен всему | — | нет |
| PLAN-1C′ | — (`6E` снят) | — | параллелен 9B | — | **см. AUDIT-R21-07**: `:733` «все остальные зависимости сохраняются» ↔ `:254/699/804` |
| PLAN-2 | PLAN-1D | — | — | — | нет |
| PLAN-3 | PLAN-2 | — | — | — | нет |
| PLAN-4 | PLAN-2, PLAN-3 | — | — | — | нет |
| PLAN-5 | PLAN-4 | — | PARALLEL всем 9B | — | нет |
| PLAN-6A | PLAN-5 (`:1073`, ordering) | — | PARALLEL 9B | — | нет; 6A→6D помечена как convention (`:696`, `:1258`) |
| PLAN-6B | PLAN-6A | — | параллелен | — | нет |
| PLAN-6C | PLAN-6B | — | параллелен | — | нет |
| PLAN-6D | PLAN-6A (convention) | BLOCKER первого multi-owner slice | — | — | нет |
| PLAN-6E | PLAN-6D | BLOCKER первого destructive slice | — | — | нет |
| PLAN-7 | PLAN-6A | — | параллелен | — | нет |
| PLAN-8 | PLAN-7 | — | параллелен | — | нет |
| PLAN-L0 | зелёный PLAN-4 | KSG | параллелен 9A/6* | — | нет |
| PLAN-L1 | PLAN-L0 | — | — | — | нет |
| PLAN-L2 | PLAN-L1; обязателен до L3 | CLI surface → `full` | — | — | нет |
| PLAN-L3 | PLAN-L0, PLAN-L2 | destructive + KSG + reversible | — | — | нет |
| PLAN-L4 | PLAN-L3 | destructive + reversible | — | установка пакета — отдельно | нет |
| PLAN-9B-0 | PLAN-4 | нет | — | — | нет |
| PLAN-9B-1 | PLAN-9B-0 | нет | — | model-вариант OD-16 → approval | нет |
| PLAN-9B-5a | PLAN-9B-1 | public CLI surface | — | **owner approval** | нет |
| PLAN-9B-4 | PLAN-9B-5a | наблюдаемое `strict` | — | **owner approval** | нет |
| PLAN-9B-2 | PLAN-9B-4, **6D**, **6E** | multi-owner + persisted visual plan + destructive | — | — | нет |
| PLAN-9B-3 | PLAN-9B-2, **6E** | destructive + reversible | — | — | нет |
| PLAN-9B-5b | PLAN-9B-5a + миграция callers, **6D**, **6E** | destructive + reversible | — | — | нет |
| PLAN-9A | **PLAN-9B-2 + PLAN-1C′ + PLAN-6E** | persisted bytes + tolerant reader | — | approval **уже выдан** (ровно состав 9A) | **AUDIT-R21-03**: `:681-686` и registry `:645-646` подразумевают всё 9B / 9B-5b |
| PLAN-9C | PLAN-1C′ + PLAN-6E (+ наполнение от 9B) | semantic decision path | — | — | нет |
| PLAN-9D | PLAN-9B, PLAN-9C | ноль платных вызовов | — | — | нет |
| PLAN-9E | **PLAN-9D, PLAN-10C** + owner approval | paid/network activation | — | **owner approval** | **AUDIT-R21-01**: `:683-684` ставит 9E перед 10A/10B/10C |
| PLAN-10A | PLAN-9A | persisted contract | — | — | нет |
| PLAN-10B | PLAN-10A | — | — | — | нет |
| PLAN-10C | PLAN-9B, PLAN-10B | — | — | — | нет |
| PLAN-10D | PLAN-10C + аудит | shared provider registry → `full` | — | — | нет |
| PLAN-11 | PLAN-9E, PLAN-10C | product gate; 10D **не** обязателен для M1 | — | M2 бюджет — approval | нет |
| PLAN-12E | PLAN-1B | docs QA | вся 12 параллельна первому product slice | — | нет |
| PLAN-12A | PLAN-12E | docs QA | — | — | нет |
| PLAN-12B | PLAN-12A | targeted + `full` | — | — | нет |
| PLAN-12C | PLAN-12B | docs QA | — | — | нет |
| PLAN-13A/13B/13C/13E | PLAN-1B (семейство) | package/shared contract → `full` | — | — | нет |
| PLAN-13D | — (перенесён в PLAN-L, якорь ссылок) | — | — | — | нет |
| PLAN-14A…14F | PLAN-6B, PLAN-6C, PLAN-12, PLAN-13 | runtime/user data → corpus + абсолютный путь + approval | — | **owner approval** на 14E | нет |
| PLAN-15 | PLAN-11…PLAN-14 | все offline checks | — | — | нет |

**Циклов нет.** Проверено обходом: единственная потенциальная петля
`9B → 10C → 9E → 11` и `9A → 10A → 10B → 10C` не замыкается ни на 9B-*, ни на
9A. `PLAN-9D` зависит от `9B` и `9C`, `9C` — от `1C′`/`6E`, обе точки входа
достижимы из `PLAN-4`.

**Скрытых blockers не найдено**, с одной оговоркой: `PLAN-L2` выносит
diagnostics-команды, которыми пользуется `PLAN-9D`. План формулирует это как
«[INFERENCE] PLAN-9D без них не запускается — поэтому L2 обязателен **до L3**»
(`:869-870`), то есть зависимость направлена корректно (L2 до L3), а не «L2 до
9D». Сегодня команды существуют в legacy `maintenance.py`, поэтому 9D исполним
и без L2. **Это не дефект.**

### Проверка восьми инвариантов §10 задания

| # | Инвариант | Результат | Evidence |
|---|---|---|---|
| 1 | `1C′` не зависит напрямую от `6E` | **ВЫПОЛНЕН** | `:804-806` «прямая зависимость от PLAN-6E **снята**» |
| 2 | `9A` явно требует `1C′` + `6E` + актуальный 9B prerequisite | **ВЫПОЛНЕН** | `:1620-1621`, дублируется `:69-70`, `:700` |
| 3 | `9C` явно требует `1C′` + `6E` | **ВЫПОЛНЕН** | `:1844-1845`, `:71`, `:701` |
| 4 | `6D` не блокирует `9B-0` / `9B-1` | **ВЫПОЛНЕН** | `:697`, `:1253-1257` («allowlist тривиален») |
| 5 | `6E` не блокирует `9B-0` / `9B-1` | **ВЫПОЛНЕН** | `:1364-1365` «Для PLAN-9B-0/9B-1 необязателен» |
| 6 | `5` не технический blocker ни одного 9B sub-slice | **ВЫПОЛНЕН** | `:695`, `:1040-1046`, `:271`; проверено Secondary §11 исполнением |
| 7 | `12*` не блокирует первый product slice | **ВЫПОЛНЕН** | `:2068-2071` «Вся family PLAN-12 не блокирует первый product slice» |
| 8 | `L` параллелен, не prerequisite `9A` | **ВЫПОЛНЕН** | `:855-856` «параллелен … prerequisite для PLAN-9A не является» |

### Структурная исполнимость

| Проверка | Результат |
|---|---|
| `current_checkpoint: PLAN-1D-routing` единственный и совпадает с разделом | **ДА** — frontmatter `:9` == «Current checkpoint» `:48` == PLAN-1D-routing `:780` |
| `next_exact_action` == «Следующая точная команда» | **ДА** — `git status --short --branch` (`:10` == `:76`) |
| `baseline_head: fe2df5b` не подменён commit'ом канонизации | **ДА** — `:6`; `git show --stat` подтверждает: `4ca3655`, `adcbb19`, `affa138` меняют только `docs/current/*.md` |
| статусы completed/pending/blocked/split не противоречат зависимостям | **ДА по существу**, INFO-замечание ниже |
| нет stage, недостижимого из-за circular gate | **ДА** |
| нет stage, формально разрешённого до обязательного safety gate | **ДА** — каждая boundary в `:712-722` имеет названный первый пересекающий слайс, и все пять проверены (§10 отчёта) |
| нет двух canonical owners одной ответственности | **ДА** — ревизия 2.1 owners только сужает (10B→10D, PLAN-11→gate, PLAN-8→roadmap) |
| `source_paths` во frontmatter обоих файлов существуют | **ДА** — все 23 пути плана и 24 пути registry разрешаются |

**INFO (не finding).** `PLAN-9A` имеет `status: blocked`, `PLAN-9B` —
`status: pending`, при том что оба в момент `affa138` неисполнимы (их
предшественники `pending`). Соглашение о статусах в документе не задано, а
«Detail policy» (`:629-636`) описывает `blocked` как уровень детализации, а не
как состояние конечного автомата. Исполнение это не меняет.

---

## 5. Внутренняя непротиворечивость

| ID | Место (файл:строка) | Тип дефекта | Severity | Доказательство |
|---|---|---|---|---|
| AUDIT-R21-01 | `PROJECT_EXECUTION_PLAN.md:683-684` | DEPENDENCY CONTRADICTION | MEDIUM | Граф ставит `9E` до `10A/10B/10C`; `:1893` объявляет `PLAN-9E` заблокированным `PLAN-10C` |
| AUDIT-R21-03 | `PROJECT_EXECUTION_PLAN.md:681-686`; `CLEANUP_REGISTRY.md:645-646` | AMBIGUOUS WORDING | MEDIUM | Графика подразумевает `9B-5b → 9A`; `:1620` объявляет prerequisite «единственной действующей» цепочкой `9B-2 + 1C′ + 6E` |
| AUDIT-R21-07 | `PROJECT_EXECUTION_PLAN.md:732-733` | FACTUAL CONTRADICTION (внутридокументная) | LOW | «все остальные зависимости сохраняются» ↔ «прямая зависимость `1C′ → 6E` снята» (`:254`, `:699`, `:804`) |
| AUDIT-R21-11 | `PROJECT_EXECUTION_PLAN.md:1814` | OWNER/GATE MISMATCH | LOW | T3 («английская альтернатива не выбрасывается») назначен 9B-2, но исправляемый им `source_is_latin` принадлежит 9B-1 (`CLEANUP_REGISTRY.md:206` C36) |

Прочие проверенные места противоречий **не** содержат: «Заблокировано»
(`:60-75`), «Risk-based governance model» (`:693-706`), «Risk-boundary таблица»
(`:712-722`), «Результат после каждого этапа» (`:2380-2402`) согласованы между
собой и с разделами отдельных PLAN-ID.

---

## 6. Canonicalization no-loss check

| # | Finding | Источник | Вердикт | Где в canonical (или почему нет) |
|---|---|---|---|---|
| 1 | запрет PLAN-P0 (OD-11) | Proposal §5.2 | PRESENT CORRECTLY | план `:91-92`, `:234`, `:2486-2487` |
| 2 | T1–T11 распределены по 9B слайсам | CRITICAL §14 | PRESENT BUT AMBIGUOUS | все 11 распределены (9B-0=T10,T11 `:1713`; 9B-1=T1,T2,T4,T5 `:1745`; 9B-5a=T9 `:1763`; 9B-4=T6,T7,T8 `:1785`; 9B-2=T3 `:1814`) — сумма 11/11, но T3 не в том слайсе (AUDIT-R21-11) |
| 3 | OD-25 early multi-topic regression | Proposal §5, OD-25 | PRESENT CORRECTLY | `:248`, `:1689-1693`, `:2021-2026` |
| 4 | PLAN-9B before PLAN-9A (OD-15) | Secondary §15.1 | PRESENT CORRECTLY | `:238`, `:1630-1635`, `:729-732` |
| 5 | exact query owner = `src/assets/query_adapter.py` (OD-14) | CRITICAL §2, §10.1 | PRESENT CORRECTLY | `:237`, `:1678-1684`, `:1720`, `:1723`, `:2421-2424` |
| 6 | CRITICAL-2 внутри PLAN-9B, без нового top-level stage (E-13) | Proposal §22.2 | PRESENT CORRECTLY | `:253`, `:1667-1668` |
| 7 | 9B-5a / 9B-5b split (D-1) | Secondary §10.3 | PRESENT CORRECTLY | `:250`, `:1751-1765`, `:1831-1840`; registry K08, C42 |
| 8 | AI authoring = DEFER (OD-17), без placeholder-пакетов | Proposal §17 | PRESENT CORRECTLY | `:240`, `:326-329`, `:1512-1517`, `:1784` |
| 9 | PLAN-9C = producer → existing consumer wiring | Secondary §4.4 | PRESENT CORRECTLY | `:1859-1861`, `:245` |
| 10 | `_selection_fingerprint` НЕ архитектурный запрет | Secondary §4.2 | PRESENT CORRECTLY | `:266`, `:1850-1855`, `:2448-2451` |
| 11 | `_semantic_visual_summary` — дефект отчётности | Secondary §4.2 | PRESENT CORRECTLY | `:1862-1865`, `:2452-2453` |
| 12 | double orchestration severity = MEDIUM | Secondary §3.5 | PRESENT CORRECTLY | `:244`, `:2219`, `:2458-2459`; registry C43a |
| 13 | ADR 0009 intentional split | Secondary §3.3 | PRESENT CORRECTLY | `:267`, `:2210-2212`, `:2454-2455`; registry C05, C43b |
| 14 | ADR 0006 explicit-stage idempotency defect (C43a) | Secondary §3.2 | PRESENT CORRECTLY | `:2213-2218`; registry C43a; подтверждено кодом `src/news/pipeline.py:157` |
| 15 | paid TTS re-execution НЕ заявлен как текущий риск | Secondary §3.4 | PRESENT CORRECTLY | `:267`, `:2219-2221`, `:1011-1015`, `:2458-2459` |
| 16 | LocalLibrary: один index / один rights authority / ДВА matcher'а | Secondary §5.1 | PRESENT CORRECTLY | `:268`, `:1969-1974`, `:2460-2463`; registry C40 |
| 17 | user assets и project pool НЕ входят в convergence | Secondary §5.2 | PRESENT CORRECTLY | `:1979-1983`; registry C40 |
| 18 | diversity reserve salvage (C47) | Secondary §6.5 | PRESENT CORRECTLY | `:926-928`, `:1987-1989`; registry C47 + `Knowledge salvage log` |
| 19 | dead `duplicate_penalty` | Secondary §6.5 | PRESENT CORRECTLY | `:1994-1997`; registry C40; scope корректно ограничен `rank_local_assets` (проверено: `review_bundle.py`, `candidate_ranker.py` живые) |
| 20 | provider-registry convergence hypothesis removed (D-2, E-5) | Secondary §7.4 | PRESENT CORRECTLY | `:251`, `:269`, `:284-285`, `:1926-1936`, `:2469-2473`; registry C41 |
| 21 | PLAN-10B возвращена pagination/exhaustion responsibility | Secondary §7.4 | PRESENT CORRECTLY | `:1917-1925`, `:1935-1936` |
| 22 | truthful export catalog (C44) | Secondary §8.2 | PRESENT CORRECTLY | `:2027-2040`, `:2474-2477`; registry C44 |
| 23 | PLAN-11 = evidence gate, не implementation owner | Secondary §8.2 | PRESENT CORRECTLY | `:255`, `:2035-2040` |
| 24 | FFmpeg concat = `-c:v copy`, не перекодирование (C45) | Secondary §9.3 | PRESENT CORRECTLY | `:270`, `:1521-1533`, `:2478-2481`; registry C45 |
| 25 | PLAN-8 = roadmap owner, не renderer implementation owner | Secondary §9.5 | PRESENT CORRECTLY | `:256`, `:1504-1505`, `:1531-1533` |
| 26 | C50 `[HARD]` rights fail-open | Secondary §6.4 | PRESENT BUT AMBIGUOUS | registry C50 присутствует полностью; план упоминает `:1998-2000`, `:2465-2467` — но **позиции в порядке выполнения нет** (AUDIT-R21-04) |
| 27 | «Сильные foundations — сохраняются» (список не сокращён) | CRITICAL §17, Secondary §15 | PRESENT CORRECTLY | `:304-321`; покрыты все 8 пунктов CRITICAL §17 и 12 из 14 Secondary §15 |
| 28 | `search_session.json` запрещён без evidence (OD-24) | Proposal §9.1 | PRESENT CORRECTLY | `:247`, `:327`, `:1642-1650` |
| 29 | no TranslatorService / SearchEngine / QueryOrchestrator (OD-13) | CRITICAL §12.4 | PRESENT CORRECTLY | `:236`, `:326`, `:1727-1728` |
| 30 | Anime Factory preserved as future Video Repurposer source (OD-23) | Proposal §16 | PRESENT CORRECTLY | `:246`, `:1506-1511`, `:2264-2275`; registry K08 |
| 31 | PLAN-L0 salvage: C46 / C47 / C48 | CRITICAL §13, Secondary §6.5 | PRESENT CORRECTLY | `:922-931`; registry C46, C47, C48 + `Knowledge salvage log` |
| 32 | E-2 / E-5 / E-7 закрыты и убраны из unresolved | Secondary §14 (34–36) | PRESENT CORRECTLY | `:277-287`; таблица открытых `:291-302` их не содержит |
| 33 | remaining provisional findings оставлены implementation-time | Secondary §16 (P-1…P-11) | PRESENT CORRECTLY | `:289-302` — все 11 присутствуют (P-1 `:299`, P-2 `:300`, P-3 `:293`, P-4 `:302`, P-5 `:298`, P-6 `:295`, P-7 `:294`, P-8 `:296`, P-9 `:297`, P-10 `:301`, P-11 закрыт через E-13); E-1 → `:1759-1760` |
| 34 | OD-1…OD-10 ревизии 2 не отменены и не искажены | план `:209-220` | PRESENT CORRECTLY | таблица OD-1…OD-10 идентична редакции `adcbb19` (сверено `git show adcbb19`); 2.1 только добавляет OD-11…OD-26 |
| 35 | «Ревизия 2.1: опровергнутые формулировки» — все 8 строк | Secondary §14 | PRESENT BUT AMBIGUOUS | `:264-273`, все 8 строк соответствуют доказанному; **но** заголовок (`:261-262`) приписывает **все** восемь Secondary Deep Dive, тогда как строки 7 (`legacy_broad_query`) и 8 (topic-hardcode в `query_generator`) доказаны CRITICAL Deep Dive §5.2/§10.1. Атрибуция, не содержание |

### Дополнительно: доказанные findings, отсутствующие в обоих canonical файлах

Пройдено по `INDEPENDENT_REPOSITORY_REVIEW` §§4–8 и `PROPOSAL` §§20–21.

| Finding | Класс в источнике | Присутствует? | Оценка |
|---|---|---|---|
| MEDIUM-5 — `config/semantic_visual.json` объявляет несуществующие модели `gpt-5.6-terra` / `gpt-5.6-luna` | **FACT** (Review §6) | **MISSING** — ноль упоминаний в обоих файлах, явного отказа нет | **AUDIT-R21-06**, LOW |
| LOW-1 — локализация канала объявлена шире, чем реализована (`en`/`es` с пустыми `voice_id`) | FACT (Review §6) | MISSING | следствие CRITICAL-1; не влияет на порядок; **не** finding аудита |
| Дублирование №7/№8 — фасады `asset_manager.py` (266 строк), `content_creation/*` без exit condition; S01–S07 закрыты без exit condition | INFERENCE (Review §8) | PRESENT BUT AMBIGUOUS — частично покрыто registry C02/C03 и `Closure rule` (`:738-747`), но системное наблюдение «дробление без удаления фасада» не записано | не поднимаю: класс INFERENCE, следствия для порядка нет |
| HIGH-1 — topic-hardcode внутри `[HARD]` gate `modes.py:295-296` | FACT (Review §5) | PRESENT CORRECTLY | план `:1811-1813` |
| HIGH-5 — `strict` по умолчанию + пустой поиск = гарантированный отказ | INFERENCE (Review §6) | PRESENT CORRECTLY | план `:1602-1606` («все сцены `missing` из-за CRITICAL-1») |
| MEDIUM-6 — master копируется побайтово под три имени | FACT (Review §6) | PRESENT CORRECTLY | registry C44 «Master копируется побайтово, адаптации под площадку нет» |
| MEDIUM-8 — deny-list не покрывает `Write`/`Edit` по `.env`; `Bash(git clean *)` не ловит голый `git clean` | FACT (Review §7) | PRESENT CORRECTLY | план `:1284-1289` (6D-1); подтверждено чтением `.claude/settings.json` |
| Proposal §20.7 — owner production-side kill-switch = PLAN-5 | RECOMMENDATION | PRESENT, изменено осознанно | план `:257`, `:565-568`, `:297` — owner оставлен открытым; это owner decision, а не потеря |

---

## 7. PROJECT_EXECUTION_PLAN ↔ CLEANUP_REGISTRY consistency

Сопоставлены все строки C34–C50, а также K08, C05, C17–C33, N01–N06.
**ID уникальны** (проверено); `D01`–`D04` встречаются дважды по конструкции —
в «Architecture candidates» и в «Delete evidence», это разные таблицы одной
строки, не дубликаты.
**Таблица `Retired` пуста** (`CLEANUP_REGISTRY.md:660`);
**`Knowledge salvage log` пуст** (`:679`). Ничего ошибочно не перенесено в
`Retired`. Ни одна строка C34–C50 не объявлена выполненной.

Классы доказанности C34–C50 сверены с evidence: ни один не сильнее источника.
C43b — `INFERENCE` (корректно: конвергенция не доказана). C45 —
`FACT` + `INFERENCE` с явным разделением («величина ущерба **никем не
измерялась**») — корректно. C50 — `FACT` + `INFERENCE` — корректно (fail-open
доказан кодом, severity — вывод). C32/C17/C22/C23/C26/C27/C28 сохраняют `DEFER`.

**Реальные mismatches:**

| # | Строка | Mismatch | Severity |
|---|---|---|---|
| 1 | `CLEANUP_REGISTRY.md:645-646` («Последующая очередь» п.10) | «`PLAN-9A` выполняется **после него** [семейства `PLAN-9B`]» ↔ план `:1620` «prerequisite chain (единственная действующая): `PLAN-9B-2` + `PLAN-1C′` + `PLAN-6E`». Registry требует больше, чем план | MEDIUM (AUDIT-R21-03) |
| 2 | `CLEANUP_REGISTRY.md:86` (K08) и `:212` (C42) | «единственная уникальная бизнес-возможность — `--text` / `--text-file`» — опровергнуто кодом в обе стороны (§8.B) | MEDIUM (AUDIT-R21-02) |
| 3 | `CLEANUP_REGISTRY.md:221` (C50) | Gate = «отдельный future bounded rights slice» — единственная `[HARD]`-строка без позиции в порядке выполнения; план тоже её не размещает | MEDIUM (AUDIT-R21-04) |
| 4 | `CLEANUP_REGISTRY.md:726` («Accidental invariants») | Gate `tests/test_apps_structure.py` = **PLAN-L4**, но тест импортирует `apps.news_to_short.main`, который ретайрит **PLAN-9B-5b**; порядок 9B-5b ↔ L4 не зафиксирован | LOW (AUDIT-R21-08) |
| 5 | `CLEANUP_REGISTRY.md:1-4` (frontmatter) и `:33` | `last_verified_commit: 9f3ddba` / `2026-07-29` и «Проверено 2026-07-29 от clean HEAD `9f3ddba`» — при том что строки C30–C50 добавлены `adcbb19`/`affa138` по evidence от `4ca3655`/`adcbb19` | LOW (AUDIT-R21-09) |
| 6 | `CLEANUP_REGISTRY.md:86` (K08) | «`apps/news_to_short/main.py` — **83 строки** собственного argparse»; фактически файл 86 строк | INFO (measurement drift) |

**Совпадают корректно** (проверено построчно): C34 · C35 · C36 · C37 · C38 ·
C39 · C40 · C41 · C43a · C43b · C44 · C45 · C46 · C47 · C48 · C49 — gates,
owners и формулировки идентичны исправленному evidence и разделам плана.
C05 корректно дополнен ADR 0009 и ссылками на C43a/C43b. C17–C33 ревизией 2.1
не тронуты и не должны были быть. N01–N06 не тронуты ревизией 2.1 (изменения
N02/N03/N04/N05/N06 принадлежат ревизии 2). C19/C20/C21 подтверждены фактически:
`git ls-files -i -c --exclude-standard` → ровно 9 файлов (8 × `outputs/*.json` +
`assets/broll/.gitkeep`); `git check-ignore output tmp` → NOT IGNORED для обоих;
`output/` содержит один файл `output/pdf/PROJECT_EXECUTION_PLAN_mobile.pdf`.

### Stale frontmatter: решение

`tools/qa/check_agent_docs.py:13-17` проверяет `CURRENT_DOCS` — ровно три файла
(`START_HERE.md`, `SYSTEM_MAP.md`, `CURRENT_STATE.md`). `CLEANUP_REGISTRY.md` и
активный план **не проверяются вообще**, поэтому их frontmatter не может
уронить QA. Для трёх проверяемых файлов валидируются: `status == "current"`,
формат `last_verified_commit` (регулярка `^[0-9a-f]{7,40}$`, **существование
commit'а в Git не проверяется**), `last_verified_date` (возраст ≤ 120 дней;
сейчас 3 дня) и существование каждого `source_path`. Запуск на `affa138`:
exit 0, «Agent documentation and skills are current and internally consistent».

**Вердикт:** `last_verified` ≠ `last_modified`, и для `START_HERE.md` /
`CURRENT_STATE.md` (не изменялись с `4027269`/`9f3ddba`) значение **корректно**.
Для `CLEANUP_REGISTRY.md` — **stale metadata**: содержательные строки C30–C50
проверены на `4ca3655`/`adcbb19`, а шапка утверждает `9f3ddba`/2026-07-29.
Это LOW-дефект governance, не пойманный технически, потому что registry вне
`CURRENT_DOCS`. PLAN-6A уже планирует расширить `CURRENT_DOCS` на все файлы
`docs/current/` со `status: current` плюс активный план (`:1133-1136`), что
закроет и это.

---

## 8. Code/evidence cross-check

Проверены все девять. Ниже — вердикт и доказательство для каждого.

### A. QUERY PATH — **CONFIRMED**

- `src/assets/query_adapter.py:43-56` — `PROVIDER_QUERY_LANGUAGES`, в том числе
  `"local_library": ("en", "ru")` на `:53`. Совпадает с планом.
- `:62` `GLOSSARY` (40 пар); `:141` `build_scene_queries`; `:235`
  `build_slot_queries` — координаты плана верны.
- **`source_is_latin` — свойство ВСЕГО набора: подтверждено дословно.**
  `:156-159`: `source_is_latin = bool(source_queries) and not any(_CYRILLIC_RE.search(str(item["query"])) for item in source_queries)`.
  Один русский элемент обнуляет флаг для всего набора, и английский alternative
  выбрасывается вместе с русским primary. **CONFIRMED.**
- **`semantic_selection/query_generator.py` не участвует в remote-запросах:
  CONFIRMED.** Единственные production-callers `build_scene_queries` /
  `build_slot_queries` — `src/news/asset_manifest_builder.py:31,276` и
  `src/news/asset_scene_completion.py:20,289`. `generate_queries` /
  `ordered_queries` идут в `asset_manifest_builder.py:577,749,807,839`
  (метаданные и отчёты) и `src/production_plan/youtube_shorts.py:263`. Ни один
  не доходит до провайдера.
- **Подстрочный матчинг: CONFIRMED.** `:391-393` — `for russian, english in GLOSSARY.items(): if russian in text`. Ни границ слова, ни нормализации.
- **Главный носитель topic-hardcode — `src/news/script_generator.py`:**
  подтверждено косвенно (координаты `:115-190` соответствуют
  `_apply_video_first_topic_briefs`, единственному заполнителю `visual_brief`).
  Полный inventory остаётся PROVISIONAL по плану — **UNVERIFIED by design.**

### B. 9B — **CORRECTED (существенно)**

- `apps/news_to_short/main.py:23-24` действительно объявляет `--text` и
  `--text-file`; `:51-52` передаёт их в `create_news_to_short_job(text=…, text_file=…)`.
  **Это подтверждено.**
- **Опровергнуто:** утверждение плана `:2437` «Канонический CLI такого входа
  **не имеет**» (и registry K08/C42) неверно. Канонический
  `python -m ai_youtube create` имеет `--pasted-script` и `--script-file`,
  которые `src/content_creation/request_builder.py:47-48` кладёт в
  `ContentCreationRequest.pasted_script` / `.script_path`, а
  `.../fullscreen_voiceover/use_case.py:607-639 resolve_content_inputs`
  при `content_input_mode == ""` (**значение по умолчанию**,
  `src/content_creation/models.py:123` — комментарий прямо называет его
  «legacy/unspecified») возвращает их как `text` / `text_file` и передаёт в тот
  же `create_news_to_short_job` (`use_case.py:117-124`) с
  `script_source = resolve_script_source(request) == ""` (`:641-646`).
  **Offline-проба вне репозитория:**

  ```
  mode repr: ''
  resolve_content_inputs -> (None, None, '<исходный текст>', None)
  resolve_script_source -> ''
  ```

  То есть `python -m ai_youtube create --pasted-script "<материал>"` **без**
  `--input-mode` даёт ровно `INPUT_MODE_TEXT` + `deterministic_local` —
  поведение, которое deep-dive §5.4 измерил как «честный экстрактивный
  сценарий». Deep-dive §9.2 проверял только явные значения `--input-mode` и
  пропустил дефолтную ветку.
- **Вторая, пропущенная всеми аудитами уникальная возможность.** Фактический
  список флагов канонического `create` (получен исполнением `build_parser()`):
  `--text` присутствует, но принадлежит story card («Card headline text»);
  **флага `--assets` в каноническом `create` нет**. При этом
  `apps/news_to_short/main.py:26,53` передаёт `assets=` в
  `create_news_to_short_job`, где `src/news/pipeline.py:94` кладёт их в
  `NewsJob.user_assets`, потребляемые `pipeline.py:362,596`. Второй носитель —
  `pipeline.py --news-to-short --assets` (`src/news/pipeline.py:244`), который
  умирает в PLAN-L4. **После PLAN-9B-5b + PLAN-L4 ни один CLI не сможет подать
  пользовательские ассеты при создании проекта.**
- **Test-callers у пакета есть: CONFIRMED.** `tests/test_apps_structure.py:10`
  (`importlib.import_module("apps.news_to_short.main")`) и
  `tests/test_fullscreen_voiceover_application_boundary.py:133`
  (`from apps.news_to_short import main as compatibility_app`).

### C. SEMANTIC — **CONFIRMED**

- `_selection_fingerprint` — `src/assets/semantic_visual_service.py:88`
  (снимок до), `:180` (сравнение после), `:392` (определение). Функция только
  сравнивает и дописывает предупреждение; вето отсутствует. **Защитная
  самопроверка, а не архитектурный запрет — CONFIRMED.**
- Vision-сервис пишет результат после цикла отбора: подтверждено вызовом из
  `_write_reviews()` в `src/news/asset_manifest_builder.py` (после per-scene
  цикла) в review-манифест.
- **«жёстко пишет `semantic_rerank_enabled=False` независимо от конфига» —
  CONFIRMED дословно.** `src/news/asset_manifest_builder.py:991-998`:

  ```python
  def _semantic_visual_summary(self) -> dict[str, Any]:
      settings = self.selection_config.get("semantic_visual")
      values = settings if isinstance(settings, dict) else {}
      return {
          "enabled": bool(values.get("enabled", False)),
          "mode": str(values.get("mode", "analyse_and_report")),
          "semantic_rerank_enabled": False,
      }
  ```

  `enabled` и `mode` читаются из конфига, `semantic_rerank_enabled` — литерал.
- Способность metadata-semantic слоя rank/reject/block принята как доказанная
  Secondary §4.3 synthetic-пробой; повторная проба не выполнялась —
  **UNVERIFIED by delegation**, evidence не опровергнуто ничем прочитанным.

### D. ORCHESTRATION — **CONFIRMED**

- `src/news/pipeline.py:157`:
  `if not force_stage and stage_name in completed and not stage:` — **дословно
  как в плане.** При явно запрошенной стадии output-validated пропуск не
  применяется.
- Batch-режим соблюдает контракт: `:145` и `:147` (`stop_stage`, `resume`)
  срабатывают раньше и без `and not stage`.
- **Контракт `stage=` не покрыт тестом: CONFIRMED.**
  `tests/test_news_stage_idempotency.py` использует `until_stage=` в шести
  тестах (`:83,96,142,170,199,250`); единственное `stage=` — `:116` вместе с
  `force_stage=True`, то есть проверка **пере**исполнения, а не пропуска.
- ADR 0006 формулирует политику безусловно: «`status == "completed"` +
  mandatory output valid + no `force_stage` -> skip stage», без исключения для
  explicit-режима. Отклонение кода от ADR подтверждено.
- ADR 0009 фиксирует расслоение намеренно: «Its **application-level
  orchestration** lives in `fullscreen_voiceover/use_case.py`» и «Ownership
  remains in `src.news`». **CONFIRMED.**
- «4–7 вызовов, не ровно 7» и «повторного платного TTS нет» приняты по Secondary
  §3.1/§3.4 (проба + три независимых guard'а); повторно не измерялись —
  **UNVERIFIED by delegation**.

### E. LOCALLIBRARY — **CONFIRMED**

- Один `media_index`: все потребители читают
  `<library_root>/metadata/media_index.json` (принято по Secondary §5.1;
  подтверждено сигнатурой `search_local_assets(index, …)`,
  `src/media_library.py:74`).
- Один rights-authority: `src/assets/license_policy.py:211
  apply_policy_to_candidate`; PATH 1 достигает его через
  `src/news/asset_provider_adapters.py:154 with_policy_decision`.
- Два matcher'а: `media_library.search_local_assets:74-93` (общий для PATH 1 и
  PATH 3) и собственный token-intersection в `LocalLibraryStockProvider`.
- `src/assets/license_policy.py:35` — `review_required: bool = True` в
  `LicensePolicyDecision`. **CONFIRMED.**
- `rank_local_assets` — `src/news/asset_manifest_builder.py:1246`. **CONFIRMED.**
- **`duplicate_penalty` — мёртвый код: CONFIRMED дословно.**

  ```
  1275:        if asset_id in used_asset_ids:
  1276:            continue
  1277:        duplicate_penalty = 25 if asset_id in used_asset_ids else 0
  ```

  `continue` на `:1276` срабатывает раньше, поэтому на `:1277` условие всегда
  ложно и penalty всегда 0 (используется на `:1322`, `:1328`).
- **Проверено, что «мёртвый код» не распространён ошибочно.** Живые и не
  затронутые вхождения: `src/assets/review_bundle.py:224,231,237,249,262,263`
  (накапливается по similarity, покрыт
  `tests/test_visual_preview_integration.py:12`) и
  `src/assets/semantic_selection/candidate_ranker.py:278,316,505` (без
  предшествующего `continue`). Registry C40 говорит именно про
  `rank_local_assets` — **формулировка точна.**

### F. REGISTRY — **CONFIRMED**

- **`ProviderCapabilities.query_languages` имеет приоритет: CONFIRMED
  дословно.** `src/assets/query_adapter.py:133-138`:
  `"""Languages a provider can be searched in. Capabilities win over the table."""`
  → `declared = (capabilities or {}).get("query_languages"); if declared: return …`,
  и только затем `PROVIDER_QUERY_LANGUAGES.get(provider, ("en",))`.
- **Разные таблицы хранят разные ответственности: CONFIRMED.**
  `src/assets/provider_routing.py:20-21` документирует это в коде: «Order used
  when a caller names no providers at all… the per-scene order comes from the
  strategy, not from here».
- **`local_library` не попадает в `ordered_providers`: CONFIRMED механизмом.**
  `src/news/asset_manifest_builder.py:266-273` вызывает `route_providers` с
  `provider_names=list(self.providers_by_name.keys())` — то есть **фактически
  сконструированными** провайдерами. `LocalLibraryStockProvider` не создаётся
  `src/providers/registry.create_default_stock_providers`, поэтому имя в
  `ordered_providers` не появляется, хотя присутствует в
  `DEFAULT_PROVIDER_ORDER` (`provider_routing.py:22-30`) и в
  `PROVIDER_QUERY_LANGUAGES` (`:53`). Реальный локальный поиск идёт мимо —
  `asset_manifest_builder.py:296-301 rank_local_assets`.
- **Осиротевший `unsplash`: CONFIRMED.** Имя объявлено в
  `query_adapter.py:49`, `scene_strategy.py:250`, `candidate_ranker.py:136`;
  `src/providers/unsplash_provider.py` предоставляет функцию `search_images`, а
  не `StockProvider`, и нигде не конструируется.
- `DEFAULT_PROVIDER_ORDER` вестигиален: используется только как дефолт при
  `provider_names=None`, чего канонический путь не делает. **CONFIRMED.**

### G. EXPORT — **CONFIRMED, с одним уточнением формулировки**

- `src/production_catalog/catalog.py:229-305 _build_export_targets` регистрирует
  **пять** targets: `youtube_shorts` (`:233`), `instagram_reels` (`:248`),
  `tiktok` (`:263`), `facebook_reels` (`:278`), `stories` (`:293`) — у всех
  `enabled=True`, `implementation_status="active"`, `safe_zone_profile="vertical_9x16_standard"`
  на `:240/255/270/285/300`. **Координаты плана точны.**
- Production создаёт **три**: `src/news/final_renderer.py:475` —
  `for name in ("youtube_shorts.mp4", "instagram_reels.mp4", "facebook_reels.mp4")`,
  и все три — `shutil.copyfile(master, target)` (побайтовые копии).
- **Уточнение.** Утверждение «`supported_export_targets` и `safe_zone_profile`
  имеют **ноль** production-читателей» (план `:2030-2032`, registry C44) точно
  для render decision, но не буквально: `src/production_catalog/cli.py:208`
  печатает `supported_export_targets`, `:239` печатает `safe_zone_profile`, и
  оба сериализуются в capabilities-вывод. Это **display readers**, не
  decision readers. Содержательный claim («в render decision не участвуют»,
  «каталог — единственный outlier») **CONFIRMED**; абсолютное «ноль
  production-читателей» — неточность, не влияющая на решение. Не поднимаю
  отдельным finding: план в той же фразе сам ограничивает claim render decision.

### H. FFMPEG — **CONFIRMED дословно**

| Шаг | Код | Кодек / CRF |
|---|---|---|
| segment encode (video) | `final_renderer.py:303-308` | libx264 veryfast **23** |
| segment encode (image) | `:341-346` | libx264 veryfast **23** |
| **concat** | `:69-84` | **`-c:v copy`** — не перекодирует |
| audio + exact-duration mux | `:573-578` (`_duration_control_args`) | libx264 veryfast **20** |
| нет audio | `:121` | **`-c:v copy`** |
| ASS subtitle burn | `:593-600` (`_burn_ass_subtitles`) | libx264 veryfast **21**, `-c:a copy` |
| нет ASS | `:132` | `shutil.copyfile` |
| platform outputs | `:458-483` | `shutil.copyfile` × 3 |

- **CRF 20 принадлежит duration-control / audio mux: CONFIRMED**, вместе с
  документированной причиной — `:553-561` объясняет, что `-shortest` + `-c:v copy`
  режет по keyframe и уже дало «~2.75s tail on the first live fullscreen-voiceover
  render».
- **«Три lossy generations при audio + ASS; без озвучки или без ASS — две; без
  обоих — одна» — CONFIRMED арифметически** по таблице выше: 23 → (copy) → 20 →
  21 = 3; 23 → (copy) → (copy) → 21 = 2; 23 → (copy) → 20 → (copyfile) = 2;
  23 → (copy) → (copy) → (copyfile) = 1.

### I. C50 — **CONFIRMED**

- **Механизм fail-open подтверждён построчно.**
  `src/assets/license_policy.py:169`:
  `review_required = bool(rule.get("review_required", True)) if rule else bool(default.get("review_required", True))`
  — значение берётся **исключительно** из policy-правила; исходный
  `review_required` записи медиатеки в вычислении не участвует.
- `apply_policy_to_candidate` (`:211-221`) затем выполняет
  `candidate.license = decision.to_license(candidate.license)`, где
  `to_license` (`:47-…`) подставляет `review_required=self.review_required`,
  то есть **перезаписывает** исходный флаг записи.
- `config/license_policy.json:383-395` — провайдер `local_library`, правило
  `license_name: "user_owned"` → `"allowed_for_render": true`,
  `"review_required": false`. Дополнительно `license_policy.py:164-165`:
  при `provider == "local_library"` и `owner_approval_status == "schema_v1_required"`
  и `schema_version >= ASSET_SCHEMA_VERSION` → `owner_review_required = False`,
  поэтому reason `owner_review_required` не добавляется и `blocked` остаётся
  ложным.
- Итог: запись, явно помеченная `review_required: true`, выходит из
  канонического пути с `review_required=False` и `allowed_for_render=True`.
  **Обратного случая нет** — политика не может ужесточить запись, помеченную
  как разрешённую, иначе как через `reason_parts` (что не связано с исходным
  флагом). **CONFIRMED.**

---

## 9. Четыре проверки §15

### 15.1 — «одна входящая ссылка» — **ПОДТВЕРЖДЕНО с уточнением**

```
$ grep -rn "PROJECT_EXECUTION_PLAN" --include=*.md .   (без docs/audits/ и самого плана)
docs/current/CLEANUP_REGISTRY.md:55,64,159,649,653,705,721
docs/current/CURRENT_STATE.md:91
```

- **Markdown-ссылка ровно одна** — `CURRENT_STATE.md:91`
  `[PROJECT_EXECUTION_PLAN.md](PROJECT_EXECUTION_PLAN.md)`.
- Остальные семь — **текстовые упоминания в backticks** в
  `CLEANUP_REGISTRY.md`, добавленные позже самим commit'ами `adcbb19`/`affa138`
  (на `4ca3655`, где делалось измерение, их было **0** — проверено
  `git show 4ca3655:docs/current/CLEANUP_REGISTRY.md | grep -c`).
- `AGENTS.md`, `START_HERE.md`, `CLAUDE.md`, `README.md` его **не упоминают** —
  подтверждено чтением всех четырёх целиком.

**Вывод:** утверждение плана остаётся верным по существу (одна навигационная
ссылка; четыре названных файла молчат), и обоснование PLAN-1D как первого шага
не подорвано. Формулировка «во всём репозитории» стала на семь текстовых
упоминаний менее точной — INFO, не finding.

### 15.2 — routing в master plan — **ПОДТВЕРЖДЕНО полностью**

- `AGENTS.md:13-15`, шаг 4 «Быстрый старт»: «Если задача продолжает rescue plan,
  полностью прочитай `docs/handoff/PROJECT_RESCUE_MASTER_PLAN.md` и выполняй
  только первый незавершённый этап.» Ссылки на активный план нет.
- `AGENTS.md:82`: «Для rescue stage обнови статус и «Текущий handoff» в master plan.»
- `START_HERE.md:39`: «Текущий rescue plan: `PROJECT_RESCUE_MASTER_PLAN.md`.»
- `START_HERE.md:46-48`: «Следующий checkpoint — read-only **9B-C01** inventory
  package roots, wrappers, implementation owners, Anime/shared modules и callers.»

Агент, буквально исполнивший `AGENTS.md`, действительно уходит в master plan и
начинает 9B-C01 — шаг, который `CLEANUP_REGISTRY.md:630-631` объявляет
несуществующим. **Единственное обоснование PLAN-1D подтверждено.**

**Дополнительно обнаружено:** третий current-документ,
`CURRENT_STATE.md:90-92`, ведёт на активный план **и одновременно** утверждает
«текущий checkpoint — **9B-C01**». Он не входит в allowed zones PLAN-1D
(`:766-768`) — см. AUDIT-R21-05.

### 15.3 — счётные величины — **ПОДТВЕРЖДЕНО, с уточнением базы**

| Величина | План | Факт на `affa138` | Итог |
|---|---|---|---|
| test-модулей `test_*.py` | 112 | **112** | совпало |
| строк | 30 403 | **30 403** (`cat tests/*.py`) / **30 317** (`cat tests/test_*.py`) | совпало для `tests/*.py` |
| `conftest.py` | отсутствует | отсутствует | совпало |
| network guard из `tests/__init__.py` | да | `tests/` содержит `__init__.py`, `network_guard.py` и 112 `test_*.py` | совпало |
| «после PLAN-L останется около 106» | 106 | не проверялось (6 legacy test-модулей ещё существуют) | не опровергнуто |
| subprocess-модулей | 12 на `adcbb19` | **12 на `affa138`** (`grep -l subprocess tests/test_*.py`) | совпало; **это измерение, не норма** |

**Уточнение.** Плановое «112 плоских модулей, 30 403 строки» смешивает две
базы: 112 — это `test_*.py`, 30 403 — это все `tests/*.py`. Источник
(`INDEPENDENT_REPOSITORY_REVIEW` §7) писал «112 модулей, 30 317 строк», то есть
одну базу. Расхождение — measurement drift/смешение баз, не дефект.
Полный suite **не запускался** (запрещено §0), поэтому 1441/245 с/4F+3E не
проверялись.

### 15.4 — документация и skills — **ПОДТВЕРЖДЕНО дословно**

```
README.md   = 405 строк,  "ai_youtube" = 0
COMMANDS.md = 681 строка, "ai_youtube" = 0
COMMANDS.md: src.content_creation.cli = 49,  pipeline.py = 24
skills/ = 6 каталогов; SKILL.md с "src.content_creation.cli" = 3:
  create-short-video-first, replace-visual-slot, resume-project
```

Все четыре числа плана (`:1474-1481`, `:2686-2691`, `:1145-1148`) совпадают с
фактом до единицы.

`REQUIRED_SKILLS` в `tools/qa/check_agent_docs.py:18-25` — точное множество из
шести имён, совпадающее с составом `skills/`: `create-short-video-first`,
`evaluate-render-quality`, `resume-project`, `replace-visual-slot`,
`architecture-change`, `create-handoff`. Расхождений нет; наблюдение плана о
том, что добавление reviewer-skill (PLAN-6E) уронит exact-count проверку
(`:1127-1128`, registry `:728`), **подтверждено чтением кода**.

---

## 10. Governance / safety verdict

**SAFETY PRESERVED.**

| Проверка | Результат | Evidence |
|---|---|---|
| Три owner tripwires сохранены | ДА | `:423-434` — persisted bytes · внешне наблюдаемая поверхность · деньги/сеть/публикация; формулировка не ослаблена относительно ревизии 2 |
| Approval на PLAN-9A НЕ распространился | ДА, **усилено** | `:447-450`: «approval PLAN-9A относится **ровно** к составу PLAN-9A и не переносится на `PLAN-9B*`, `PLAN-9C`, `PLAN-9D`, `PLAN-9E`, `PLAN-10*`». Ревизия 2 перечисляла границы менее явно |
| persisted / public / network / paid / destructive требуют своих gates | ДА | `:712-722`, продублировано в каждом слайсе 9B-* и в `:1761-1762`, `:1788`, `:1815-1816`, `:1827-1828`, `:1837-1839` |
| rights · provenance · `must_avoid` · misleading/conflict остались `[HARD]` | ДА | `:319-321`, `:391-396`, `:1608-1610`; C50 явно помечен `[HARD]` |
| reversible retirement сохранён | ДА | `:510-525`; `[FACT] git remote -v` **пуст — проверено фактически** (вывод пустой), значит требование внешнего `git bundle` обосновано |
| Knowledge Salvage Gate и Runtime Reset не смешаны | ДА | `:887-897` — явный запрет спрашивать «какое knowledge в старом mp4»; registry `:665-675` дублирует границу |
| 6D / 6E перестали быть глобальными blockers, но обязательны перед своими boundaries | ДА | см. таблицу ниже |
| Технически enforced ровно три вещи | ДА | `.claude/` содержит **только** `settings.json`, `settings.local.json`, `scheduled_tasks.lock` (нет `agents/`, `skills/`, `commands/`, hooks); `tools/` содержит **только** `tools/qa/check_agent_docs.py` (+ `__init__.py`); `tests/network_guard.py` существует. `.github/workflows/offline-tests.yml` существует, но `git remote -v` пуст → CI выполниться не мог, что план и фиксирует (`:2570-2572`) |
| C49 — subprocess measurement | ДА | `tests/network_guard.py` живёт в test-пакете; `grep -l subprocess tests/test_*.py` → **12** на `affa138` (те же 12 модулей, что перечислил Review §7). Приведено как **измерение**, не норма |

### Соответствие boundary → первый пересекающий слайс

Для каждой строки «Risk-boundary таблицы» (`:712-722`) проверено, что названный
слайс действительно её пересекает:

| Boundary | Названный слайс | Пересекает? | Проверка |
|---|---|---|---|
| локальное поведение, ноль persisted/public/paid/destructive | 9B-0, 9B-1 | **ДА** | 9B-0 — новый test-модуль; 9B-1 — `query_adapter.py` + тесты, 2 production-импортёра, `ProviderQuery.source` — write-only поле |
| public CLI / input mode | 9B-5a | **ДА** | добавление input mode меняет `--input-mode choices` и `--help` (`src/content_creation/commands/content.py:90-100`) |
| наблюдаемое поведение `strict` | 9B-4 | **ДА** | `allow_legacy_fallback` + `ScriptValidationResult` меняют exit-поведение документированного входа |
| несколько owners в одном diff | 9B-2 | **ДА** | зоны: `query_adapter` + `script_generator` + `legacy_format` + `semantic_selection/*` |
| destructive retirement с callers | 9B-2, 9B-3, 9B-5b | **ДА** | 9B-2 удаляет orca-hardcode + его тест; 9B-3 — GLOSSARY-матчер, `legacy_broad_query`, `make_stock_query`, `query_generator` (5 callers); 9B-5b — `apps/news_to_short` (2 test-caller'а, проверено) |
| persisted bytes / schema / layout | 9A | **ДА** | additive schema в `assets_manifest.json` |
| semantic / Vision decision path | 9C | **ДА** | production asset selection path |
| network / model / paid | model-вариант 9B-1 (OD-16), 9E | **ДА** | OD-16 явно требует отдельного approval; 9E включает paid backend |
| runtime / user data move | 14D / 14E | **ДА** | физическое перемещение runtime |

**Ослаблений не найдено.** Единственное место, где governance формально
**не дотягивает**, — отсутствие позиции у `[HARD]`-строки C50 в порядке
выполнения (AUDIT-R21-04). Это не ослабление существующего gate, а
незаполненный слот: правило остаётся `[HARD]`, но момент его исполнения не
назначен.

---

## 11. Findings

---

**ID: AUDIT-R21-01**
**Severity: MEDIUM** · **Class: DEPENDENCY CONTRADICTION**

- **FACT.** `docs/current/PROJECT_EXECUTION_PLAN.md:683-684` объявляет цепочку
  `→ PLAN-9A → PLAN-9C → PLAN-9D → PLAN-9E` / `→ PLAN-10A → PLAN-10B →
  PLAN-10C → PLAN-10D → PLAN-11`, то есть **PLAN-9E раньше PLAN-10C**.
  `docs/current/PROJECT_EXECUTION_PLAN.md:1893` объявляет
  «**PLAN-9E** — status: blocked (**PLAN-9D, PLAN-10C** + owner approval)».
- **EVIDENCE.** Обе строки в одном файле. Источник ошибки установлен:
  в ревизии 2 (`git show adcbb19:docs/current/PROJECT_EXECUTION_PLAN.md`, блок
  «После PLAN-9A») эти два ряда были **двумя независимыми строками без
  ведущей стрелки** — `PLAN-9B → 9C → 9D → 9E` и `PLAN-10A → … → PLAN-11`.
  Канонизация 2.1 добавила каждой строке ведущий `→`, превратив две
  независимые цепочки в одну и создав ложное ordering-утверждение. Proposal
  §5.2 давал корректный порядок: `… → PLAN-10A → 10B → 10C → 10D → PLAN-9D →
  PLAN-9E → PLAN-11`.
- **IMPACT.** Агент, читающий только сводный граф, попытается выполнить
  PLAN-9E — controlled semantic activation с платным backend и owner approval —
  до PLAN-10C. Слайс окажется неисполним (или будет исполнен без adaptive
  budget/plateau policy), а при попытке «разблокировать» его исполнитель может
  ослабить prerequisite в разделе PLAN-9E. Это единственный узел графа, где
  сводка требует **невозможного**, а не просто более строгого порядка.
- **VERDICT: CORRECTION REQUIRED.**
- **SMALLEST SAFE CORRECTION:** см. §13.1 (общий патч с AUDIT-R21-03).

---

**ID: AUDIT-R21-02**
**Severity: MEDIUM** · **Class: FACTUAL CONTRADICTION**

- **FACT (a).** План `:2435-2437`: «[FACT] единственная уникальная бизнес-
  возможность во всём `apps/` — флаги `--text` / `--text-file`; тот же материал
  через них даёт нормальный экстрактивный сценарий. **Канонический CLI такого
  входа не имеет.**» То же в `CLEANUP_REGISTRY.md:86` (K08) и `:212` (C42), и
  в OD-19 (`:242`).
- **EVIDENCE (a).** Канонический `python -m ai_youtube create` имеет
  `--pasted-script` и `--script-file`
  (`src/content_creation/commands/content.py:74,86-90`).
  `src/content_creation/request_builder.py:47-48` кладёт их в
  `ContentCreationRequest.script_path` / `.pasted_script`.
  `src/content_creation/models.py:123` задаёт
  `content_input_mode: str = ""  # "" (legacy/unspecified) | topic | …`.
  `.../fullscreen_voiceover/use_case.py:607-639 resolve_content_inputs` при
  пустом mode доходит до `return url, topic, text, text_file` (`:639`), а
  `resolve_script_source` (`:641-646`) возвращает `""`. Далее
  `use_case.py:117-124` вызывает `create_news_to_short_job(text=pasted_text,
  text_file=text_file, script_source="")` — **те же параметры**, что и
  `apps/news_to_short/main.py:51-52`. Контролируемая offline-проба вне
  репозитория (ноль сети, ноль записи в репозиторий) вернула
  `resolve_content_inputs -> (None, None, '<текст>', None)` и
  `resolve_script_source -> ''`.
  Deep-dive §9.2 разбирал только явные значения `--input-mode` и дефолтную
  ветку не проверял; §5.4 проверял режим на уровне `src.news`, а не CLI.
- **FACT (b).** Одновременно у `apps/news_to_short` есть **вторая** уникальная
  возможность, не названная ни одним аудитом: флаг `--assets`
  (`apps/news_to_short/main.py:26`, передаётся `:53`), заполняющий
  `NewsJob.user_assets` (`src/news/pipeline.py:94`), потребляемый
  `src/news/pipeline.py:362,596`. Фактический список флагов канонического
  `create` (получен исполнением `build_parser()`) содержит `--source-asset`
  (story card) и **не содержит** `--assets`. Второй носитель —
  `pipeline.py --news-to-short --assets` (`src/news/pipeline.py:244`) — умирает
  в PLAN-L4.
- **IMPACT.** Два разнонаправленных последствия.
  (a) Scope PLAN-9B-5a завышен: слайс описан как «мигрировать **уникальную**
  capability», хотя фактически требуется дать **имя, валидацию и документацию**
  уже работающему входу. Owner approval на public CLI surface всё равно нужен
  (меняется `--input-mode choices` и `--help`), поэтому gate не ослабляется —
  но исполнитель, обнаружив, что «capability уже есть», может закрыть слайс
  без переименования и оставить CRITICAL-2 fix (9B-4) без честной альтернативы.
  (b) Гораздо серьёзнее: после PLAN-9B-5b + PLAN-L4 **ни один CLI не сможет
  подать пользовательские ассеты при создании проекта**. Исполнитель 9B-5b,
  доверившись формулировке «единственная уникальная возможность — `--text`»,
  мигрирует только текстовый вход и ретайрит wrapper, потеряв `--assets`.
  Обязательный порядок «capability сначала мигрируется, wrapper удаляется
  потом» (`:1835-1836`) от этого не защищает, потому что список capability в
  плане неполон.
- **VERDICT: CORRECTION REQUIRED.**
- **SMALLEST SAFE CORRECTION:** см. §13.3.

---

**ID: AUDIT-R21-03**
**Severity: MEDIUM** · **Class: AMBIGUOUS WORDING** (гипотеза H1)

- **FACT.** `docs/current/PROJECT_EXECUTION_PLAN.md:681-686` — блок, в котором
  строка `PLAN-9B-5b …` непосредственно предшествует строке-продолжению
  `  → PLAN-9A → …`. `docs/current/CLEANUP_REGISTRY.md:645-646` — «…
  (`9B-0 → 9B-1 → 9B-5a → 9B-4 → 9B-2 → 9B-3`, затем `9B-5b`), `PLAN-9A`
  выполняется **после него**».
- **EVIDENCE.** Опровергается тремя местами плана: `:69-70`, `:700`,
  `:1620-1621` («prerequisite chain (**единственная действующая**, ревизия
  2.1): `PLAN-9B-2` + `PLAN-1C′` + `PLAN-6E`»), а также `:1673-1676`, где
  9B-5b явно вынесен из последовательности семейства. Risk boundaries 9A
  (persisted bytes, `:719`) и 9B-5b (destructive retirement, `:718`) не
  пересекаются; общих файлов у слайсов нет.
- **IMPACT.** Буквальное исполнение сводного графа добавляет `PLAN-9A` два
  ложных blocker'а — `PLAN-9B-3` и `PLAN-9B-5b` — и, через них, полный набор
  destructive gates (6D + 6E + reversible retirement + внешний `git bundle`).
  Это прямо противоречит owner decision D-1, ради которого 9B-5 и разделялся,
  и удлиняет путь до persisted-слайса, чей approval уже выдан.
- **VERDICT: CORRECTION REQUIRED.**
- **SMALLEST SAFE CORRECTION:** см. §13.1 (план) и §13.4 (registry).

---

**ID: AUDIT-R21-04**
**Severity: MEDIUM** · **Class: OWNER/GATE MISMATCH**

- **FACT.** `CLEANUP_REGISTRY.md:221` — C50, класс `FACT` + `INFERENCE`,
  помечен «**[HARD]** rights correctness», gate — «отдельный future bounded
  rights slice». В `PROJECT_EXECUTION_PLAN.md` C50 упоминается дважды:
  `:1998-2000` (PLAN-10D — «не смешивать с C50») и `:2465-2467` (Decisions).
  **Ни одна из этих записей не задаёт, до какого этапа fix обязан состояться.**
- **EVIDENCE.** Дефект подтверждён кодом (§8.I): явный `review_required=True`
  проходит канонический путь. При этом `PLAN-11` (`:2051-2054`) требует «ноль
  нарушений rights/provenance» как product gate, а `PLAN-9E` включает paid
  semantic activation — оба выполняются позже неопределённого «future slice».
  Для сравнения: другие «future bounded slice» строки (C43a, C44, C45)
  относятся к MEDIUM contract/quality findings, а не к `[HARD]` rights.
- **IMPACT.** `[HARD]` rights fail-open остаётся без назначенного момента
  исполнения. Формально ничто не мешает дойти до PLAN-11 / M1 evidence с
  действующим fail-open; PLAN-11 поймает его только если в fixtures окажется
  запись с явным `review_required=True`, что не гарантировано. Правило класса
  `[HARD]`, у которого нет позиции в порядке, исполняется по памяти — ровно то,
  что план объявляет недопустимым (`:381-383`: «Если правило можно enforce
  технически — оно обязано быть enforced, а не только записано»).
- **VERDICT: CORRECTION REQUIRED.**
- **SMALLEST SAFE CORRECTION:** см. §13.5.

---

**ID: AUDIT-R21-05**
**Severity: MEDIUM** · **Class: STALE EVIDENCE**

- **FACT.** `docs/current/CURRENT_STATE.md:90-92` (`status: current`):
  «Активный порядок работ задаёт `PROJECT_EXECUTION_PLAN.md`; **текущий
  checkpoint — 9B-C01**.» Это единственная markdown-ссылка на активный план во
  всём репозитории (§9.1).
- **EVIDENCE.** `PROJECT_EXECUTION_PLAN.md:9` — `current_checkpoint:
  PLAN-1D-routing`; `:48` — «Текущий шаг: PLAN-1D-routing, не начат».
  `CLEANUP_REGISTRY.md:630-631` — «Ревизия 2 разделила этот монолитный
  checkpoint на capability gates `PLAN-1A` / `PLAN-1B` / `PLAN-1C′`
  (+ routing `PLAN-1D`); **единого шага «9B-C01» больше нет**».
  Allowed zones PLAN-1D (`:766-768`) — `AGENTS.md` и
  `docs/current/START_HERE.md`; `CURRENT_STATE.md` в них не входит.
- **IMPACT.** PLAN-1D объявляет измеримым результатом «новый агент, буквально
  исполнив `AGENTS.md`, попадает в этот план» (`:795-796`). После PLAN-1D
  агент попадёт в план **через** `CURRENT_STATE.md` — и прочитает там, что
  текущий checkpoint 9B-C01, то есть ровно тот шаг, ради ухода от которого
  PLAN-1D и выполняется. Источник истины №4 противоречит источнику истины №3 по
  вопросу, который принадлежит №3. Precedence (`:125-134`) конфликт разрешает,
  но только для агента, который прочёл раздел precedence.
- **VERDICT: CORRECTION REQUIRED.**
- **SMALLEST SAFE CORRECTION:** см. §13.6.

---

**ID: AUDIT-R21-06**
**Severity: LOW** · **Class: MISSING FINDING**

- **FACT.** `INDEPENDENT_REPOSITORY_REVIEW_2026-07-31.md` §6, MEDIUM-5, класс
  **FACT**: «`config/semantic_visual.json` указывает на несуществующие модели:
  `"primary_model": "gpt-5.6-terra"`, `"comparison_model": "gpt-5.6-luna"`».
  Проверено на `affa138`: `config/semantic_visual.json:20-21` содержит именно
  эти значения.
- **EVIDENCE.** `grep -c "gpt-5.6"` по обоим canonical файлам → **0** и **0**.
  Явного отказа («не считаем дефектом, потому что …») в плане тоже нет. Ни
  одна из строк C34–C50 и ни один OD его не покрывает.
- **IMPACT.** PLAN-9E («включить доказанный semantic decision path … opt-in
  policy», `:1891-1903`) и PLAN-9D зависят от Vision backend. Первое же
  включение с текущим конфигом упрётся в неизвестное имя модели. Ущерб
  ограничен (backend выключен, дефект проявится сразу и на первом вызове), но
  это **доказанный FACT, молча исчезнувший при канонизации**, что план сам
  называет дефектом канонизации.
- **VERDICT: CORRECTION REQUIRED.**
- **SMALLEST SAFE CORRECTION:** см. §13.7.

---

**ID: AUDIT-R21-07**
**Severity: LOW** · **Class: FACTUAL CONTRADICTION** (гипотеза H2)

- **FACT.** `PROJECT_EXECUTION_PLAN.md:732-733`: «Меняется **ровно одно ребро
  графа**: `9A → 9B` становится `9B → 9A`; **все остальные зависимости
  сохраняются**.»
- **EVIDENCE.** Тот же документ трижды утверждает обратное:
  `:254` («Прямая зависимость `PLAN-1C′ → PLAN-6E` **снята**»), `:699`
  («прямая зависимость от PLAN-6E снята»), `:804-806` (то же в разделе
  PLAN-1C′). Дополнительно `:701` устанавливает **новое** ребро `9C → 6E`, для
  которого транзитивного пути не существовало. Классификация всех восьми
  изменений — §3, таблица H2.
- **IMPACT.** Единственный правдоподобный неверный вывод — что `PLAN-1C′` всё
  ещё ждёт `PLAN-6E`. Следствие: docs-only слайс, снимающий один из двух gates
  `PLAN-9A`/`PLAN-9C`, откладывается за reviewer foundation без причины. Ущерб
  ограничен, потому что раздел PLAN-1C′ явно и с обоснованием утверждает
  обратное.
- **VERDICT: CORRECTION REQUIRED** (минимальная, по критерию §16.3 —
  утверждение противоречит собственному документу).
- **SMALLEST SAFE CORRECTION:** см. §13.2.

---

**ID: AUDIT-R21-08**
**Severity: LOW** · **Class: OWNER/GATE MISMATCH**

- **FACT.** `CLEANUP_REGISTRY.md:726` («Accidental invariants») назначает
  `tests/test_apps_structure.py` gate **PLAN-L4**. Тест
  (`tests/test_apps_structure.py:10`) импортирует `apps.news_to_short.main`
  наряду с `apps.youtube_pipeline.main` и `apps.anime_factory.main`. Пакет
  `apps/news_to_short` ретайрит **PLAN-9B-5b** (`:1831-1840`). Аналогично
  `tests/test_fullscreen_voiceover_application_boundary.py:133`
  (`from apps.news_to_short import main as compatibility_app`).
- **EVIDENCE.** Порядок 9B-5b ↔ L4 нигде не зафиксирован: PLAN-L параллелен
  (`:855-856`), 9B-5b зависит только от 9B-5a + 6D + 6E.
- **IMPACT.** Если 9B-5b выполняется раньше L4, два test-модуля краснеют, а
  строка registry указывает на неверный gate. `required verification` слайса
  (`targeted + smoke + full`, `:1840`) это поймает — то есть ущерб
  ограничивается потерянным временем и риском «починить тест», а не «перевести
  caller».
- **VERDICT: CORRECTION REQUIRED** (одна ячейка таблицы).
- **SMALLEST SAFE CORRECTION:** см. §13.8.

---

**ID: AUDIT-R21-09**
**Severity: LOW** · **Class: STALE EVIDENCE**

- **FACT.** `CLEANUP_REGISTRY.md:3-4` — `last_verified_commit: 9f3ddba`,
  `last_verified_date: 2026-07-29`; `:33` — «Проверено 2026-07-29 от clean HEAD
  `9f3ddba`». Файл при этом содержит строки C30–C50, добавленные commit'ами
  `adcbb19` (2026-07-31) и `affa138` (2026-08-01) по evidence от `4ca3655` и
  `adcbb19`.
- **EVIDENCE.** `git log --oneline -- docs/current/CLEANUP_REGISTRY.md` →
  `affa138`, `adcbb19`, `fe2df5b`, `9f3ddba`, `75a2715`.
  `tools/qa/check_agent_docs.py:13-17` не включает registry в `CURRENT_DOCS`,
  поэтому QA этого не ловит (запуск на `affa138`: exit 0).
- **IMPACT.** Читатель, доверившийся шапке, отнесёт C34–C50 к состоянию
  `9f3ddba` — commit'у, на котором ни один из трёх аудитов не выполнялся.
  Внутри файла секции C17–C29 и C34–C50 честно называют свои audit HEAD, так
  что противоречие разрешимо, но шапка вводит в заблуждение. Это **не**
  «`last_verified` ≠ `last_modified`»: содержательные строки действительно
  проверялись на других commit'ах.
- **VERDICT: CORRECTION REQUIRED** (две строки frontmatter + одна строка тела),
  **либо ALREADY RESOLVED**, если владелец считает достаточным, что PLAN-6A
  (`:1133-1136`) расширит `CURRENT_DOCS` и сделает проверку автоматической.
- **SMALLEST SAFE CORRECTION:** см. §13.9.

---

**ID: AUDIT-R21-10**
**Severity: LOW** · **Class: OWNER/GATE MISMATCH**

- **FACT.** `PROJECT_EXECUTION_PLAN.md:1814` назначает тест **T3** слайсу
  PLAN-9B-2. T3 (`CRITICAL_INPUT_SEARCH_DEEP_DIVE` §14) — «английская
  альтернатива не выбрасывается вместе с русской».
- **EVIDENCE.** Исправление, которое проверяет T3, — перевод `source_is_latin`
  с уровня набора на уровень элемента (`src/assets/query_adapter.py:156-159`).
  `CLEANUP_REGISTRY.md:206` (C36) относит это исправление к **PLAN-9B-1**:
  «DELETE — только после работающей замены (**9B-1** и исправления проверки
  `source_is_latin` на уровне элемента)». Allowed zone 9B-1 —
  `src/assets/query_adapter.py` (`:1723`); allowed zones 9B-2 — четыре других
  owner'а плюс `query_adapter`.
- **IMPACT.** Тест приезжает на слайс позже исправления. Исполнитель 9B-1
  внесёт изменение без regression-теста, а исполнитель 9B-2 обнаружит, что
  «его» тест проверяет чужой diff. Риск потери — низкий (T3 всё равно
  распределён и не потерян), риск неверной атрибуции — реальный.
- **VERDICT: CORRECTION REQUIRED** (перенос одного идентификатора).
- **SMALLEST SAFE CORRECTION:** см. §13.10.

---

**Findings уровня INFO (correction не предлагается):**

- `PROJECT_EXECUTION_PLAN.md:549-551` «112 плоских модулей, 30 403 строки»
  смешивает две базы (112 = `test_*.py`; 30 403 = все `tests/*.py`; для
  `test_*.py` — 30 317). Источник (Review §7) писал 30 317. Measurement drift.
- `CLEANUP_REGISTRY.md:86` (K08) «83 строки собственного argparse» —
  `apps/news_to_short/main.py` содержит 86 строк. Measurement drift.
- `PROJECT_EXECUTION_PLAN.md:261-262` приписывает все восемь строк таблицы
  «опровергнутых формулировок» Secondary Deep Dive; строки 7–8 доказаны
  CRITICAL Deep Dive (§5.2, §10.1). Атрибуция, не содержание.
- `PROJECT_EXECUTION_PLAN.md:2030-2032` / C44 «ноль production-читателей»
  `supported_export_targets` / `safe_zone_profile` — точнее «ноль читателей в
  render decision»: `src/production_catalog/cli.py:208,239` их печатает.
  План в той же фразе сам ограничивает claim render decision.
- `PLAN-9A` имеет `status: blocked`, `PLAN-9B` — `pending` при одинаковой
  фактической неисполнимости. Соглашение о статусах не задано; исполнения не
  меняет.

---

## 12. Что НЕ подтвердилось (false alarms)

Чтобы эти замечания не всплывали в следующем цикле:

1. **«План где-то текстом объявляет 9B-5b или 9B-3 prerequisite PLAN-9A».**
   **REFUTED.** Такой формулировки нет ни в одном из пяти мест записи
   зависимостей. Проблема **только** в ASCII-графике и в одном местоимении
   registry. Все три содержательные записи (`:69-70`, `:700`, `:1620-1621`)
   говорят `9B-2 + 1C′ + 6E`, и одна из них помечена «единственная действующая».

2. **«PLAN-9A ждёт retirement `apps/news_to_short` по product/safety причине».**
   **REFUTED.** Risk boundaries не пересекаются: 9A — persisted bytes, 9B-5b —
   destructive retirement wrapper'а; общих файлов нет; содержательная
   зависимость 9A от 9B закрывается 9B-1/9B-2.

3. **«Фраза "ровно одно ребро" делает план неисполнимым».** **REFUTED.**
   Утверждение неточно, но каждое затронутое ребро записано корректно в своём
   разделе, и таблица «Risk-based governance model» (`:693-706`) даёт полную
   картину. Ущерб ограничен одним возможным неверным выводом про `1C′ → 6E`.

4. **«PLAN-5 всё ещё блокирует какой-то 9B слайс».** **REFUTED.** `:695`,
   `:1040-1046`, `:271`, `:2443-2445` последовательно объявляют его PARALLEL;
   Secondary §11 доказал исполнимость targeted/full/smoke сегодня.

5. **«PLAN-6D / PLAN-6E превратились в глобальные blockers или, наоборот, стали
   необязательными».** **REFUTED в обе стороны.** Оба остаются обязательными
   перед своими boundaries (9B-2 / 9B-3 / 9B-5b, плюс 9A и 9C для 6E) и не
   блокируют 9B-0/9B-1 (`:697-698`, `:1253-1257`, `:1359-1365`).

6. **«Прямая зависимость `1C′ → 6E` осталась».** **REFUTED.** Снята в трёх
   местах (`:254`, `:699`, `:804-806`). Единственный след — неточная фраза
   `:733` (AUDIT-R21-07).

7. **«PLAN-12*, PLAN-L или PLAN-13 блокируют первый product slice».**
   **REFUTED.** `:2068-2071`, `:855-856`, `:2166-2169`.

8. **«В графе есть цикл».** **REFUTED.** Обход всех перечисленных узлов циклов
   не обнаружил.

9. **«`baseline_head` подменён commit'ом канонизации».** **REFUTED.**
   `:6` — `fe2df5b`; `git show --stat` подтверждает, что `4ca3655`, `adcbb19` и
   `affa138` меняли только `docs/current/*.md`. Запрет подмены записан дважды
   (`:2488-2490`, `:2536-2538`).

10. **«Утверждение о "ровно одной входящей ссылке" стало неверным и подрывает
    PLAN-1D».** **REFUTED.** Markdown-ссылка по-прежнему одна; семь новых
    упоминаний в registry — текстовые и добавлены после измерения. Обоснование
    PLAN-1D (`AGENTS.md` / `START_HERE.md` ведут в master plan) подтверждено
    независимо (§9.2).

11. **«`duplicate_penalty` объявлен мёртвым везде».** **REFUTED.** Registry C40
    говорит именно про `rank_local_assets`; `review_bundle.py` и
    `candidate_ranker.py` — живые и не затронуты. Формулировка точна.

12. **«`_selection_fingerprint` — архитектурный запрет на rerank» или
    «semantic не может влиять на отбор».** **REFUTED** (уже опровергнуто
    Secondary; canonical plan записал исправление корректно, `:266`,
    `:1850-1855`).

13. **«Размер документа (2750 строк) — дефект».** Не рассматривался как дефект
    по §10 задания; restructure не предлагается.

14. **«Три из четырёх evidence-документов не в Git — это дефект governance».**
    **ЧАСТИЧНО REFUTED.** Все четыре untracked (`git status`), включая
    `INDEPENDENT_REPOSITORY_REVIEW`. Canonical plan ссылается на них в
    `:225-228`, `:2410-2414`, registry `:187-190`. Формально это ссылка на
    неверсионированное evidence. Но: (a) `.gitignore` их не покрывает —
    проверено `git check-ignore`, они просто не добавлены; (b) сами документы
    объявляют `changes_to_repository: только этот файл` и `commit_created: no`,
    то есть их untracked-состояние **осознанно**; (c) плановые findings из них
    перенесены в canonical файлы с собственным evidence и path:line, поэтому
    canonical plan исполним и без evidence-файлов. Оцениваю как **осознанное
    состояние с остаточным риском потери**, а не как finding. Рекомендация без
    статуса finding: при следующем docs-slice добавить четыре файла в Git одним
    commit'ом — они read-only и ничего не ломают.

---

## 13. Minimal correction proposal

Все правки docs-only. Ни одна не меняет критический путь, owner'ов или gates —
они приводят текст в соответствие с уже принятыми решениями.

### 13.1. `docs/current/PROJECT_EXECUTION_PLAN.md`, раздел «Критический путь (ревизия 2.1)», строки 680–686

**WHY WRONG.** Ведущие стрелки превращают четыре независимых утверждения в одну
цепочку: (а) `PLAN-9B-5b` становится последним предшественником `PLAN-9A`
(AUDIT-R21-03, гипотеза H1); (б) `PLAN-9E` оказывается перед `PLAN-10C`, хотя
`:1893` объявляет `PLAN-10C` его блокером (AUDIT-R21-01).

**БЫЛО:**

```
PLAN-9B-5a → PLAN-9B-4 → PLAN-9B-2 → PLAN-9B-3   (порядок внутри семейства 9B)
PLAN-9B-5b   после успешной миграции capability и готовности destructive gates
  → PLAN-9A → PLAN-9C → PLAN-9D → PLAN-9E
  → PLAN-10A → PLAN-10B → PLAN-10C → PLAN-10D → PLAN-11
  → PLAN-12* → PLAN-13* → PLAN-14* → PLAN-15
```

**СТАЛО:**

```
9B: PLAN-9B-5a → PLAN-9B-4 → PLAN-9B-2 → PLAN-9B-3
    PLAN-9B-5b — отдельный destructive path после миграции capability и
                 готовности его gates; PLAN-9A он НЕ блокирует
9A: PLAN-9B-2 + PLAN-1C′ + PLAN-6E → PLAN-9A → PLAN-10A → PLAN-10B → PLAN-10C
9C: PLAN-1C′ + PLAN-6E → PLAN-9C → PLAN-9D → PLAN-9E   (9E также требует 10C)
    PLAN-10D после PLAN-10C · PLAN-11 после PLAN-9E и PLAN-10C
    затем PLAN-12* → PLAN-13* → PLAN-14* → PLAN-15
```

(6 строк вместо 5; ни одной новой зависимости — только те, что уже записаны в
`:69-71`, `:700-701`, `:1620-1621`, `:1844-1845`, `:1893`, `:1907`, `:1919`,
`:1943`, `:1965`, `:2012`.)

### 13.2. `docs/current/PROJECT_EXECUTION_PLAN.md`, раздел «Что изменилось относительно ревизии 2», строки 732–733

**WHY WRONG.** «Все остальные зависимости сохраняются» противоречит `:254`,
`:699` и `:804` — прямая зависимость `1C′ → 6E` снята, а `9C → 6E` добавлена
(AUDIT-R21-07, гипотеза H2).

**БЫЛО:**

```
Меняется **ровно одно ребро графа**: `9A → 9B` становится `9B → 9A`; все
остальные зависимости сохраняются.
```

**СТАЛО:**

```
В основной product-order chain меняется **одно ребро**: `9A → 9B` становится
`9B → 9A`. Governance-зависимости отдельно перераспределены по risk boundaries:
`PLAN-1C′ → PLAN-6E` **снята**, `PLAN-9A → PLAN-6E` и `PLAN-9C → PLAN-6E`
записаны **явно**, `PLAN-5` и `PLAN-6A` больше не блокируют PLAN-9B. Остальные
зависимости сохраняются.
```

### 13.3. `docs/current/PROJECT_EXECUTION_PLAN.md`, раздел «Ревизия 2.1 плана, 2026-07-31», строки 2435–2437

**WHY WRONG.** Опровергнуто кодом и offline-пробой в обе стороны
(AUDIT-R21-02): канонический CLI достигает того же входа через
`--pasted-script` / `--script-file` при дефолтном `--input-mode ""`, а
уникальная возможность `--assets` в списке отсутствует.

**БЫЛО:**

```
- **[FACT]** единственная уникальная бизнес-возможность во всём `apps/` — флаги
  `--text` / `--text-file`; тот же материал через них даёт нормальный
  экстрактивный сценарий. Канонический CLI такого входа не имеет.
```

**СТАЛО:**

```
- **[FACT, исправлено 2026-08-01]** у `apps/news_to_short` две возможности вне
  канонического `create`: (1) `--text` / `--text-file` — **именованный**
  source-text вход; функционально он уже достижим как
  `create --pasted-script/--script-file` при дефолтном `--input-mode ""`
  (`models.py:123` «legacy/unspecified», `use_case.py:639`, `:641-646`), то
  есть 9B-5a даёт имя, валидацию и документацию, а не новый движок;
  (2) `--assets` — пользовательские ассеты при создании проекта
  (`main.py:26` → `pipeline.py:94` `NewsJob.user_assets`), **аналога в
  каноническом `create` нет**. PLAN-9B-5b не выполняется, пока обе не
  мигрированы.
```

Плюс одна строка в `docs/current/CLEANUP_REGISTRY.md`, C42 (`:212`), колонка
`Evidence`: заменить «единственная уникальная бизнес-возможность во всём
`apps/`» на «две возможности вне канонического `create`: именованный
source-text вход (`--text`/`--text-file`) и пользовательские ассеты
(`--assets`)». То же уточнение — в K08 (`:86`).

### 13.4. `docs/current/CLEANUP_REGISTRY.md`, «Последующая очередь», п.10, строки 645–646

**WHY WRONG.** «`PLAN-9A` выполняется после него [семейства]» требует больше,
чем план (AUDIT-R21-03).

**БЫЛО:** `…, затем `9B-5b`), `PLAN-9A` выполняется после него.`

**СТАЛО:** `…, затем `9B-5b`); `PLAN-9A` требует только `9B-2` + `1C′` + `6E` и `9B-3`/`9B-5b` не ждёт.`

### 13.5. `docs/current/CLEANUP_REGISTRY.md`, C50, строка 221, колонка `Gate`

**WHY WRONG.** Единственная `[HARD]`-строка без позиции в порядке выполнения
(AUDIT-R21-04).

**БЫЛО:** `отдельный future bounded rights slice`

**СТАЛО:** `отдельный bounded rights slice; как [HARD] rights correctness обязан быть закрыт до PLAN-9E и до product evidence PLAN-11/M1`

(Плюс те же семь слов в `PROJECT_EXECUTION_PLAN.md:1998-2000`, где C50 уже
упоминается.)

### 13.6. `docs/current/PROJECT_EXECUTION_PLAN.md`, PLAN-1D-routing, строки 766–768 и 784–786

**WHY WRONG.** `CURRENT_STATE.md` — единственная навигационная ссылка на план —
называет текущим checkpoint'ом ретайренный 9B-C01 (AUDIT-R21-05), и PLAN-1D его
не правит.

**БЫЛО (`:766-768`):** `1D дополнительно допускает короткую routing-правку в `AGENTS.md` и `docs/current/START_HERE.md`.`

**СТАЛО:** `1D дополнительно допускает короткую routing-правку в `AGENTS.md`, `docs/current/START_HERE.md` и одну строку `docs/current/CURRENT_STATE.md:91`, которая до сих пор называет текущим checkpoint'ом ретайренный 9B-C01.`

### 13.7. `docs/current/CLEANUP_REGISTRY.md`, новая строка в таблице «Ревизия 2.1 findings»

**WHY WRONG.** Доказанный FACT Independent Review §6 (MEDIUM-5) исчез при
канонизации без явного отказа (AUDIT-R21-06).

**ДОБАВИТЬ:**

```
| C51 | `config/semantic_visual.json` объявляет несуществующие модели | **FACT** | `:20-21` — `"primary_model": "gpt-5.6-terra"`, `"comparison_model": "gpt-5.6-luna"`; таких моделей нет. Backend выключен, поэтому сегодня ничего не ломает | сверить имена моделей с фактическим provider contract **до** первого платного вызова | **PLAN-9E** |
```

Если владелец считает это не дефектом — записать отказ одной строкой; молчание
недопустимо по правилу самого плана.

### 13.8. `docs/current/CLEANUP_REGISTRY.md`, «Accidental invariants», строка 726, колонка `Gate`

**БЫЛО:** `**PLAN-L4**`

**СТАЛО:** `**PLAN-9B-5b или PLAN-L4** — что наступит раньше: тест импортирует `apps.news_to_short.main`, который ретайрит 9B-5b (там же — `tests/test_fullscreen_voiceover_application_boundary.py:133`)`

### 13.9. `docs/current/CLEANUP_REGISTRY.md`, frontmatter строки 3–4 и тело строка 33

**БЫЛО:** `last_verified_commit: 9f3ddba` / `last_verified_date: 2026-07-29`; «Проверено 2026-07-29 от clean HEAD `9f3ddba`.»

**СТАЛО:** `last_verified_commit: affa138` / `last_verified_date: 2026-07-31`; «Строки K01–N06 проверены 2026-07-29 от `9f3ddba`; C17–C29 — 2026-07-31 от `4ca3655`; C30–C50 — 2026-07-31 от `adcbb19`.»

### 13.10. `docs/current/PROJECT_EXECUTION_PLAN.md`, строки 1745 и 1814

**БЫЛО:** 9B-1 — `**тесты deep-dive:** T1, T2, T4, T5.` · 9B-2 — `**тесты deep-dive:** T3.`

**СТАЛО:** 9B-1 — `**тесты deep-dive:** T1, T2, T3, T4, T5.` · 9B-2 — `**тесты deep-dive:** — (T3 переехал в 9B-1 вместе с исправлением `source_is_latin`, registry C36).`

---

**Суммарный объём предложенных правок:** ~27 строк в трёх файлах
(`PROJECT_EXECUTION_PLAN.md` — 5 мест, `CLEANUP_REGISTRY.md` — 5 мест,
`CURRENT_STATE.md` — 1 строка, правится внутри PLAN-1D). Ревизия 2.2 не нужна;
это plan-only уточнение внутри существующей ревизии 2.1.

---

## 14. Out-of-scope observations

По одной строке, без углубления:

- `src/ai_youtube/cli/commands/assets.py:7 register_commands` — тело `pass`;
  подкоманда `assets` фактически регистрируется в `diagnostics`, функция мёртвая.
- `.github/workflows/offline-tests.yml` существует, но `git remote -v` пуст —
  workflow не мог выполниться ни разу (план это фиксирует, `:2570-2572`).
- `src/news/asset_manifest_builder.py:1272-1273` — вычисление
  `rights_status`/`allowed` перезаписывается политикой позже; фактически
  мёртвые строки (Secondary §6.1 отметил, canonical не записал).
- `src/production_catalog/models.py:102,164` — `supported_export_targets` и
  `safe_zone_profile` сериализуются в capabilities-вывод, то есть попадают в
  публичный JSON, хотя render их не читает.
- `src/providers/unsplash_provider.py` предоставляет функцию, а не
  `StockProvider`, при трёх упоминаниях имени `unsplash` в других модулях.
- `tests/` содержит шесть модулей `*_internals_contract.py` — characterization
  завершённых рефакторингов 6A–6F без exit condition; registry помечает только
  два из них (`test_legacy_pipeline_internals_contract`).

---

## 15. Can PLAN-1D start now?

**YES.**

PLAN-1D не зависит ни от одного из десяти findings. Его собственное обоснование
проверено фактически и подтверждено (§9.2): `AGENTS.md:13-15` и
`START_HERE.md:39,46-48` действительно уводят агента в master plan и в
несуществующий checkpoint 9B-C01. Его allowed zones, required verification
(`tools.qa.check_agent_docs` — зелёный на `affa138`) и rollback корректны.

**Рекомендация:** включить правку `docs/current/CURRENT_STATE.md:91`
(AUDIT-R21-05, §13.6) **в тот же слайс PLAN-1D** — это один и тот же
routing-дефект в третьем current-документе, и разносить его по двум коммитам
означало бы оставить единственную навигационную ссылку указывающей на
ретайренный checkpoint. Остальные девять правок — отдельный plan-only слайс,
который PLAN-1D не блокирует и может быть выполнен до, после или вместе с ним.

Правки AUDIT-R21-01 и AUDIT-R21-03 обязаны быть внесены **до** PLAN-9B-2, а
AUDIT-R21-02 — **до** PLAN-9B-5a. До этих точек их отсутствие ни на что не
влияет.

---

## 16. Additional deep-dive needed?

**NO.**

Ни один HIGH/CRITICAL факт не остался недоказанным. Все девять claims §13
проверены против кода, восемь подтверждены дословно, один исправлен и
исправление доказано контролируемой offline-пробой. Оставшиеся открытые вопросы
(P-1…P-11, E-1) — implementation-time проверки внутри своих слайсов, как и
записано планом; ни один не требует отдельного аудита.

Единственное, что стоило бы измерить отдельно — зелёность baseline
(1441/245 с/4F+3E) — уже принадлежит **PLAN-4** и не является аудитом.

---

## 17. Confidence & limitations

**Где доказательства сильные.** Все девять claims §13 подтверждены прямым
чтением кода с точными строками; четыре проверки §15 — исполнением команд; H1,
H2, AUDIT-R21-01 и AUDIT-R21-03 — сопоставлением строк внутри одного файла и с
`git show` предыдущей редакции. AUDIT-R21-02 усилен исполняемой offline-пробой.

**Где доказательства слабее.**

| Утверждение | Почему слабее | Что изменится, если оно неверно |
|---|---|---|
| «Metadata-semantic слой может сменить выбранный asset» | принято по Secondary §4.3 (synthetic-проба), повторно не воспроизводилось | п. 10 no-loss-таблицы сменится с PRESENT CORRECTLY на CONTRADICTED; PLAN-9C вернётся к формулировке «снять ограничение» |
| «4–7 вызовов pipeline, повторного платного TTS нет» | принято по Secondary §3.1/§3.4 | п. 12 и 15 no-loss-таблицы; severity C43a могла бы вернуться к HIGH |
| «Один `media_index` у всех потребителей» | подтверждено сигнатурами, не полным обходом всех callers | п. 16 no-loss-таблицы; scope PLAN-10D мог бы расшириться |
| «`--assets` не достижим никаким другим способом в каноническом CLI» | проверено полным списком флагов `create` и отсутствием `assets=` в `use_case.py:117-136`; не исключён обходной путь через `--visual-brief` или post-hoc `assets replace` | AUDIT-R21-02(b) снизится с MEDIUM до LOW; часть (a) останется |
| «T3 логически принадлежит 9B-1» | вывод из C36 и allowed zones, а не из явного текста deep-dive | AUDIT-R21-10 станет FALSE ALARM |
| Отсутствие MEDIUM-5 в canonical — потеря, а не осознанный отказ | отказ мог быть принят устно владельцем и не записан | AUDIT-R21-06 станет ALREADY RESOLVED |

**Где возможна ошибка аудитора.**

1. Чтение ASCII-графики — вопрос типографской конвенции. Если в этом
   репозитории ведущий `→` на новой строке означает «новая независимая цепочка»,
   то AUDIT-R21-01 и AUDIT-R21-03 понижаются до INFO. Против этой трактовки —
   тот факт, что ревизия 2 писала независимые цепочки **без** ведущей стрелки
   (`git show adcbb19`), то есть конвенция в самом файле противоположная.
2. Полный inventory topic-hardcodes не проверялся (запрещён), поэтому
   утверждение «главный носитель — `script_generator.py`» принято, а не
   доказано.
3. `docs/implementation` (96 файлов) не читался, поэтому «MEDIUM-5 отсутствует
   в canonical» проверено только по двум canonical файлам — в `docs/` он мог
   быть записан где-то ещё, что не сделало бы его частью canonical plan.
4. Полный suite не запускался, поэтому ни одно утверждение этого отчёта не
   опирается на прогон тестов; все test-факты получены чтением исходников.

**Что явно не проверялось и почему** — таблица в §2.

---

## 18. Repository state

**Before (снято до начала аудита):**

```
$ git status --short --branch
## governance-reset
?? docs/audits/CRITICAL_INPUT_SEARCH_DEEP_DIVE_2026-07-31.md
?? docs/audits/INDEPENDENT_REPOSITORY_REVIEW_2026-07-31.md
?? docs/audits/PROJECT_EXECUTION_PLAN_REVISION_2_1_PROPOSAL_2026-07-31.md
?? docs/audits/SECONDARY_ARCHITECTURE_FINDINGS_DEEP_DIVE_2026-07-31.md
?? output/

$ git diff --check      → пусто, exit 0
$ git diff --stat       → пусто
$ git rev-parse HEAD    → affa1389e76ea655436fd44a520d27f24e3d3205
```

**After (снято перед публикацией отчёта):**

```
$ git status --short --branch
## governance-reset
?? docs/audits/CANONICAL_REVISION_2_1_INDEPENDENT_VERIFICATION_2026-08-01.md
?? docs/audits/CRITICAL_INPUT_SEARCH_DEEP_DIVE_2026-07-31.md
?? docs/audits/INDEPENDENT_REPOSITORY_REVIEW_2026-07-31.md
?? docs/audits/PROJECT_EXECUTION_PLAN_REVISION_2_1_PROPOSAL_2026-07-31.md
?? docs/audits/SECONDARY_ARCHITECTURE_FINDINGS_DEEP_DIVE_2026-07-31.md
?? output/

$ git diff --check      → пусто, exit 0
$ git diff --stat       → пусто
```

- **tracked changes:** НЕТ. Tracked-состояние дерева идентично состоянию до
  аудита.
- **untracked changes:** ровно один новый файл — этот отчёт. `git add` не
  выполнялся.
- **commit created:** NO. Tag, stash, reset, clean, checkout, branch — не
  выполнялись.
- **Прочее:** production-код, tests, схемы, configs, `AGENTS.md`, `CLAUDE.md`,
  `START_HERE.md`, `CLEANUP_REGISTRY.md`, `PROJECT_EXECUTION_PLAN.md` и три
  предыдущих audit-документа **не изменялись**. Сеть, provider search/download,
  Vision, TTS, render и платные вызовы **не выполнялись**. Полный offline suite
  **не запускался**. Единственный исполненный Python-код: `tools.qa.check_agent_docs`
  (read-only, exit 0), `build_parser()` (read-only), и одна проба
  `probe_input.py` в session scratchpad **вне репозитория**. Cleanup не
  выполнялся, PLAN-1D не начинался.
