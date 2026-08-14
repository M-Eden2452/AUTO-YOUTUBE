---
status: current
audit_date: 2026-08-14
audit_head: a8549ff995c64ace5a5e3a32521df104a2e06ba3
working_branch: governance-reset
---

# FIRST OWNER SHORT — LOCAL, Solar repeat AFTER CYRILLIC FIX, 2026-08-14

A/B product proof: the exact same script, channel, template and command from
[FIRST_OWNER_SHORT_LOCAL_SOLAR_2026-08-14.md](FIRST_OWNER_SHORT_LOCAL_SOLAR_2026-08-14.md)
(HEAD `fbf223a`), re-run on HEAD `a8549ff` — a **bounded Cyrillic-tokenization
correction** inside the scope of `C40`, not a completed PLAN-10D. No script
change, no manual asset assignment, no query rewrite, no `--visual-brief`, no
`assets replace`, no library edit.

**Границы `a8549ff`.** Коммит дал обоим локальным matcher'ам один Unicode-aware
токенизатор. Он **не** свёл их в один canonical matcher/provider — это остаётся
открытым scope **PLAN-10D** (`### PLAN-10D`, статус `blocked`), как и
diversity reserve `C47`, который в scope того же PLAN-10D входит. Ни одного
PLAN-ID этот коммит не закрывает; название файла и заголовок исправлены задним
числом ровно потому, что прежняя формулировка «AFTER PLAN-10D» читалась как
обратное.

**Итог одной строкой:** 5/5 сцен получили usable visual slot (было 0/5).
ElevenLabs вызван один раз, `draft_1080x1920.mp4` создан (23.93s, 1080×1920,
audio present). Визуальная проверка кадров подтверждает: 2 сцены GOOD, 1
ACCEPTABLE, 2 BAD. Ни одна из двух BAD не является регрессией этого
токенизаторного исправления: у них два разных и уже существовавших механизма —
русская морфология (сцена 2) и draft-режимный reuse-фолбэк поверх неё
(сцена 3), см. §6.

**Три разных долга, которые нельзя смешивать:**

| Долг | Что это | Где записан |
|---|---|---|
| tokenizer | локальный поиск не читал кириллицу | исправлен `a8549ff` |
| morphology | extraction стеммит русский, matching — только префикс | `C79` (заведён этим слайсом) |
| diversity reserve | сцена не должна заполняться копией уже использованного клипа | `C47` → **PLAN-10D**, post-v1 |

---

## 1. Что перепроверено перед прогоном

| Утверждение prompt | Проверка | Результат |
|---|---|---|
| branch `governance-reset`, HEAD `a8549ff`, tree clean, origin sync | `git status --short --branch`, `git rev-parse HEAD` vs `origin/governance-reset` | подтверждено |
| exact-HEAD CI run `31795940186` success | `gh run view 31795940186 --json` → `conclusion: success`, `headSha a8549ff…` | подтверждено |
| full offline suite 2245 OK | commit `a8549ff` trailer: "Targeted 337 OK, full offline suite 2245 OK, gates OK"; CI green on exact HEAD | подтверждено по commit + CI; локальный повторный full-suite run стартован (`unittest discover`, PID жив, ещё не завершён на момент записи этого отчёта — см. §9) |
| tokenizer fix действительно изменил `_tokens`/`tokenize` | `git show a8549ff -- src/media_library.py` | подтверждено: `WORD_RE = re.compile(r"[^\W_]+", re.UNICODE)`, `_tokens` переименован в `tokenize`, оба локальных matcher'а (`media_library.py`, `providers/local_library_provider.py`) используют один токенизатор. Общий токенизатор — не общий matcher: convergence остаётся за PLAN-10D |
| curated library не менялась | `curated_library.json`: 72 items, все `rights_status=licensed`; последний commit файла `ec9ca7b` (до `a8549ff`) | подтверждено — библиотека не тронута этим прогоном |

## 2. Тот же сценарий, тот же канал, та же команда

Идентично §2–3 предыдущего отчёта: тема `energy/solar`, 5 сцен RU, канал
`nature_science_news_ru`, шаблон `fullscreen_voiceover_v1`, `--completion-mode
draft_complete`, `--voice-provider elevenlabs --voice-profile ru_dom
--prepare-only --json`. Сценарий не переписывался после просмотра результатов.

`project_id`: `2026-08-14_solnechnaya-panel-lovit-svet-tolko-dnem-nochyu-2`.
Сеть выключена для provider search (`--allow-network` не передавался), Vision
выключен, paid semantic выключен. `estimated_duration_sec = 22.08`,
`character_count = 329` — идентично прошлому прогону (сценарий байт-в-байт тот же).

## 3. BEFORE vs AFTER — shortlist

| | BEFORE (`fbf223a`) | AFTER (`a8549ff`) |
|---|---|---|
| Кириллические токены запроса | 0 у всех 5 сцен | реальные (`панель`, `ряды`, `штампуют`, `аккумуляторы`, `выигрывает`, …) |
| Уникальных шортлистов из 5 | 1 (все сцены получили один и тот же топ-10) | **5 из 5** |
| `total_score` у top-1 кандидата | 13.0 у всех 10 кандидатов во всех 5 сценах | варьируется по сцене: 72.5 (matched) для 4 сцен, наследуемый reuse для 1-й |
| `slot_count` / `scenes_usable_in_draft` | 0 / 0 | **5 / 5** |
| `selected_asset` | `null` во всех 5 сценах | конкретный `asset_id` в каждой из 5 сцен |
| ElevenLabs | не вызывался (paid-gate заблокирован покрытием) | вызван 1 раз (разрешено prompt) |
| MP4 | не создан | `draft_1080x1920.mp4`, 23.93s |

## 4. Per-scene результат (AFTER)

| Сцена | primary_query | semantic subject (`semantic_scene.subject`) | выбранный asset | final | semantic_match_status | rights | tier |
|---|---|---|---|---|---|---|---|
| 001 | `панель ловит Солнечная` | `панель` | `pexels_9788590` (крупный план ячеек) | 72.5 | `matched` | `licensed` | C_good_context |
| 002 | `панель уходят Ряды` | `панель` | `pexels_32386564` (конвейер сборки) | 72.5 | `matched` | `licensed` | D_partial |
| 003 | `панель штампуют быстрее` | `панель` | `pexels_9788590` (переиспользован со сцены 1) | 7.5* | `unverified`* | `licensed` | **F_emergency** |
| 004 | `аккумуляторы держат вечера` | `аккумуляторы` | `pexels_36167827` (стойка аккумуляторов) | 72.5 | `matched` | `licensed` | C_good_context |
| 005 | `Солнечная выигрывает полдень` | `Солнечная` | `pexels_27009031` (аэросъёмка рядов) | 72.5 | `matched` | `licensed` | C_good_context |

\* Скор/статус собственного (пустого) ранжированного пула сцены 3 — реальный
выбор пришёл не из этого пула, а из reuse-фолбэка (см. §6).

Различие шортлистов подтверждено напрямую: `ranked_candidates` top-5 всех пяти
сцен различны (`5 distinct shortlists / 5 scenes`), запрос впервые участвует в
отборе.

## 5. Что реально в кадре (кадры извлечены из исходников библиотеки И из
финального MP4, не только из метаданных)

| Сцена | Asset | Что на кадре (source) | Что на кадре (в готовом MP4, вертикальный кроп) | Вердикт |
|---|---|---|---|---|
| 1 | `pexels_9788590` | крупный план фотоэлемента, синее небо, горы на фоне | тот же кадр, вертикальный кроп сохраняет текстуру ячеек и небо | **GOOD** |
| 2 | `pexels_32386564` | сборочная линия завода: панель на роликовом конвейере, манипулятор | тот же индустриальный конвейер — **не** ряды панелей и не горизонт | **BAD** (по смыслу; кадр технически качественный) |
| 3 | `pexels_9788590` (повтор) | тот же крупный план ячеек, что и сцена 1 | идентичный кадр сцене 1 — нет ни завода, ни конвейера, ни штамповки | **BAD** (по смыслу и по дублированию кадра) |
| 4 | `pexels_36167827` | техник у промышленной стойки аккумуляторов, надпись "NEW BATTERY" видна | вертикальный кроп сохраняет технику и надпись | **GOOD** |
| 5 | `pexels_27009031` | аэросъёмка длинных рядов панелей, дневной свет (не закатный) | тот же кадр, композиция рядов читается в 9:16 | **ACCEPTABLE** — тематически верно (солнечная электростанция), но свет дневной, не закатный, узкое требование "закат" не выполнено |

## 6. Root cause сцены 2/3 — доказан, и это НЕ регрессия токенизатора

`semantic_scene.subject` обеих сцен (002 и 003) — одинаковый: `["панель"]`.

**Как он выбирается на самом деле** (перепроверено по коду 2026-08-14, прежняя
формулировка «extractor берёт самую короткую форму слова» была неточной):
`src/content/visual_planning/entities.py` группирует слова по стему, и уже
**внутри одной stem-группы** оставляет кратчайшую surface-форму как ближайшую к
словарной (`:214`). Субъект затем берётся не по длине, а по salience:
`+3.0` за попадание в topic (и `kind = ENTITY_KIND_TOPIC`), `+1.5` за title,
`+1.0` за claim, сортировка `(-salience, stem)` (`:221-236`). Тема проекта —
`energy/solar`, поэтому topic-сущность `панель` выигрывает у `ряды` в сцене 2 и
у не выделенных отдельной сущностью «заводов» в сцене 3.

**Настоящий долг — рассогласование двух слоёв, а не «слабый стеммер».**
Extraction имеет реальный русский стеммер со списком окончаний
(`entities.py:94`, `stem()`), а evidence-матчинг — только префиксное отношение
от пяти символов (`src/assets/semantic_selection/evidence.py:181`,
`stem_match`). Одна половина системы склонения понимает, вторая нет.

**Owner этой находки:** до этого слайса его не было. Прежняя редакция отчёта
приписывала дефект `C40`/PLAN-10C — **обе ссылки неверны**: `C40` принадлежит
**PLAN-10D** (глобальная локальная стоковая библиотека), а `PLAN-10C` — это
adaptive budget и plateau policy, к морфологии отношения не имеющая. Находка
заведена отдельной строкой реестра **`C79`**; PLAN-ID ей этим слайсом не
назначается.

Механизм по фактическому `ladder_trace`:

- Сцена 2 первой получает `pexels_32386564` (единственный кандидат с точным
  литеральным совпадением `панель` в keywords и высоким keyword-скором) —
  `canonical_primary:authoritative`.
- Сцена 3 ищет тот же `pexels_32386564` (у него тоже `панель` в keywords), но
  получает `ladder_trace: ["reuse_limit_reached:pexels_32386564",
  "F_emergency:reuse"]` — `min_scene_gap=1` в `src/assets/completion/ladder.py:119`
  запрещает повторное использование ассета в соседней сцене (индексы 1 и 2,
  gap=1 ≤ min_scene_gap=1). Сцена 3 падает в emergency-reuse и получает клип
  сцены 1 вместо конвейера.

То есть: правильный конвейерный клип для сцены "заводы штампуют панели" в
библиотеке есть, ranking его нашёл бы, но (а) морфологическое рассогласование
(`C79`) отдало его "не той" сцене первым, а (б) adjacency-политика reuse честно
запретила его повторное использование соседней сценой.

**Третий множитель — режим прогона.** Вся лестница ниже верхней ступени
достижима только в `draft_complete`: в `strict` функция возвращается раньше
(`src/assets/completion/ladder.py:479-492`, `strict_mode_requires_full_support`),
и сцена 3 осталась бы **нерешённой**, а не получила бы копию сцены 1. Команда
прогона задавала `--completion-mode draft_complete`, и приложение честно
пометило все пять слотов draft-only. То есть дубликат кадра — не поломка
лестницы, а буквальное значение draft-режима при отсутствии diversity reserve
(`C47` → **PLAN-10D**, post-v1).

Механизмы (б) и (в) работают по спецификации; дефект — только в (а), и он не
новый. Ни один из трёх не является следствием `a8549ff`.

Отдельная деталь для будущего owner: `max_uses=2` и `min_scene_gap=1` не
настраиваются ни одним конфиг-ключом — значения зашиты в
`src/assets/completion/ladder.py:78-79` и переопределяются только при чтении
манифеста прошлого прогона.

## 7. Control point (перед ElevenLabs)

```
slot_count: 5                 scenes_usable_in_draft: 5     unresolved_scenes: []
quality_tiers: {C_good_context: 3, D_partial: 1, F_emergency: 1}
assembly_statuses: {partial: 4, fallback: 1}
media_coverage.status: meets_policy   video_duration_ratio: 1.0
provider_attempts: 28 — 25 STOCK (5 сцен × 5 провайдеров), все status=skipped
  reason=query_translation_required (0 сетевых запросов); 3 local_library
  reason=license_review_required (legacy-записи, заблокированы правами)
draft_complete: true (mode)   publish_ready: false          video_first_review_required: false
```

Все 5 сцен формально получили пригодный (usable_in_draft=true) слот — контракт
prompt («если все 5 необходимых сцен получили пригодные visual slots») выполнен
по собственным метрикам приложения. Сеть не вызывалась ни разу для provider
search; локальные загрузки заблокированы правами там, где положено (3 legacy
записи), а не смыслом. Согласно правилу разрешён ровно один ElevenLabs
generation attempt.

## 8. ElevenLabs / voice / render

Один вызов через `--resume --approve-paid-generation` (single attempt, без
повторной генерации):

```
narration.wav создан:  localizations/ru/voice/narration.wav
final_render:           completed
export:                 completed
quality_check:          needs_review (asset_publish_readiness × 5 — draft-only,
                         требует замены до публикации; subtitles missing —
                         --subtitles не передавался в команде prompt, как и в
                         прошлом прогоне; это свойство команды, не регрессия)
```

`draft_1080x1920.mp4`: 23.93s, 1080×1920, H.264 + AAC mono audio 48kHz.
Путь: `projects/2026-08-14_solnechnaya-panel-lovit-svet-tolko-dnem-nochyu-2/
localizations/ru/output/draft_1080x1920.mp4`.

Второй файл `draft_no_subtitles.mp4` создан тем же прогоном (без сабов, что
ожидаемо — subtitles stage остался `pending`, т.к. `--subtitles` не передавался
ни в этом, ни в прошлом прогоне; это не отличие AFTER от BEFORE).

## 9. Локальный full offline suite — перепроверен

`PYTHONIOENCODING=utf-8 ./venv/Scripts/python.exe -B -m unittest discover -s
tests -p "test_*.py"` → `Ran 2245 tests in 712.317s` → `OK` (exit code 0).
Совпадает с заявленным в prompt "full offline suite: 2245 OK" и с commit
trailer `a8549ff` независимо от зелёного CI run (`31795940186`) — три
источника согласны. Единственный шум в выводе — два `AttributeError` в
`FFMPEG_AudioReader.__del__` (moviepy, деструктор при сборке мусора после
успешного теста), не влияет на исход (`OK`, 0 failures, 0 errors).

## 10. Findings

Находки самого прогона:

| Находка | Класс | Owner |
|---|---|---|
| Токенизаторное исправление (`a8549ff`) снимает BLOCKER §5.1 прошлого отчёта: RU-запрос впервые участвует в отборе, 5 из 5 шортлистов различны, 5 из 5 сцен получили usable slot (было 0 из 5) | подтверждение, не находка | **ни один PLAN-ID не закрыт**; `C40` и PLAN-10D остаются открытыми (matcher/provider convergence, `C47`) |
| Сцены 2 и 3 получают семантически неверные ассеты (конвейер вместо рядов; переиспользованный close-up вместо конвейера/штамповки) из-за одинакового извлечённого subject `панель` для обеих сцен | дефект, воспроизведён на живом прогоне; **владельца не имел** | новая строка реестра **`C79`** (заведена этим слайсом) |
| Сцена 3 получает копию кадра сцены 1: `min_scene_gap=1` (`ladder.py:119`) корректно запретила соседний повтор нужного клипа, а `draft_complete` разрешил F_emergency reuse. Резерва под новый материал в системе нет | следствие отсутствия diversity reserve, **не** дефект лестницы | **`C47`** → **PLAN-10D** (post-v1) |
| Subtitles stage остаётся `pending` — команда prompt не передаёт `--subtitles`, идентично прошлому прогону | UX-заметка, не находка этого прогона | нет нового owner |

Находки послепрогонного чтения кода (получены разбором, не измерением
прогона; фиксируются здесь как evidence их происхождения):

| Находка | Класс | Owner |
|---|---|---|
| Ни один пиксель не осматривается на пути отбора: `technical_score` (`candidate_ranker.py:231`) — это корзина по числу пикселей плюс расстояние aspect ratio до 9:16, обе из метаданных. Реальные метрики кадра считаются на каждом preview (`visual_metrics.py`), но `asset_manifest_builder.py:641-648` намеренно присваивает `after_id = before_id`, и они доходят только до review-доски | подтверждение уже записанных строк на живом коде | **`C69`** + **`C74`** (существующие) |
| Платный Vision — единственный канонический semantic/Vision backend, который идёт мимо default-deny `runtime_network`: `semantic_visual_openai.py:440` создаёт клиент напрямую, класса под Vision в `NETWORK_ACTIONS` нет, сторож только paid (`VisionBudgetGuard`, `:170`). Сейчас не стреляет — Vision выключен четырьмя независимыми гейтами; legacy-обходы отдельно записаны в `C65` | латентное расхождение с маршрутом, не эксплуатируемая дыра | новая строка реестра **`C80`**; смежно `C65` |
| Понятие хука существует только для текста (`hook_score`, `src/content/script_engine/text_analysis.py:132`); визуального эквивалента — удержания первых секунд кадром — нет ни в коде, ни в плане | post-v1 product discovery, не требование v1 | новая строка реестра **`C81`**; implementation owner пока не назначен |

## 11. Что НЕ делалось

Production-код не менялся. Библиотека, `curated_library.json`,
`media_index.json`, rights, пороги, веса, ranking, tokenizer и morphology не
трогались этим прогоном (все изменения токенизатора — в проверяемом коммите
`a8549ff`, до начала диагностики). Ассеты вручную не подставлялись,
`--visual-brief` не передавался, `assets replace` не вызывался, запросы после
результатов не переписывались, сценарий после результатов не переписывался.
Сеть (кроме одного разрешённого ElevenLabs вызова), Vision и paid semantic не
включались. ElevenLabs вызван ровно один раз, повторной генерации не было.
Новых PLAN-ID не создано. M1-E / VA-NEW-09 не начинался.

**Post-run docs slice (2026-08-14, тот же день, отдельный слайс, без кода).**
Этот отчёт был переименован и исправлен после независимой перепроверки его
собственных утверждений: снято название «AFTER PLAN-10D», исправлено описание
subject-эвристики, исправлена ошибочная атрибуция морфологического дефекта к
`C40`/PLAN-10C, добавлен третий множитель сцены 3 (draft-режим). Тем же слайсом
выводы перенесены в [CLEANUP_REGISTRY.md](../current/CLEANUP_REGISTRY.md)
строками `C79`–`C81` и в
[PROJECT_EXECUTION_PLAN.md](../current/PROJECT_EXECUTION_PLAN.md) —
как того требует правило «отчёт не даёт права на действие». Production-код,
сеть и платные API этим слайсом не затрагивались; PLAN-ID не создавались и
статусы PLAN-10C / PLAN-10D / PLAN-9E не менялись.

**Owner-decision addendum (2026-08-14).** `C79` — pre-v1 bounded correction
после STOCK diagnostic и до M4/PLAN-11; `C81` — post-v1 product discovery.
Повтор кадра блокирует publish-ready конкретного ролика без ручной
замены/approval, но не platform v1 и не переносит PLAN-10D. STOCK repeat не
разрешается этим docs-слайсом: отдельный execution prompt обязан назвать
network/paid scopes. `maximum_budget_usd` не hard dollar cap; hard runtime
