---
status: audit
audit_date: 2026-07-31
audit_head: adcbb19
working_branch: governance-reset
scope: targeted verification оставшихся архитектурных findings (CRITICAL-4, CRITICAL-5, LocalLibrary, provider registry, export targets, FFmpeg, risk boundaries)
method: чтение кода + существующие tests + контролируемые offline-пробы без сети
changes_to_repository: только этот файл
commit_created: no
---

# Secondary Architecture Findings Deep Dive

Третий, независимый разбор. Проверяются findings, оставшиеся после
[CRITICAL_INPUT_SEARCH_DEEP_DIVE](CRITICAL_INPUT_SEARCH_DEEP_DIVE_2026-07-31.md)
и [INDEPENDENT_REPOSITORY_REVIEW](INDEPENDENT_REPOSITORY_REVIEW_2026-07-31.md),
против гипотез
[PROJECT_EXECUTION_PLAN_REVISION_2_1_PROPOSAL](PROJECT_EXECUTION_PLAN_REVISION_2_1_PROPOSAL_2026-07-31.md).

Proposal 2.1 рассматривался как **гипотеза**, а не как evidence.

Классы утверждений: **FACT** — проверено чтением, командой или исполнением
offline-пробы. **INFERENCE** — вывод из фактов, исполнением не проверенный.
**RECOMMENDATION** — предложение.

Шкала вердиктов: **A** полностью подтверждён · **B** факт верен, механизм иной ·
**C** подтверждён частично / scope уже · **D** опровергнут · **E** evidence
недостаточно.

---

## 1. Executive verdict

| Finding | Previous claim | Verdict | Фактический механизм | Severity сейчас | Влияние на Proposal 2.1 |
|---|---|---|---|---|---|
| **A. Double orchestration** (CRITICAL-4) | «Use case вызывает pipeline 7 раз → два конкурирующих orchestration owner» | **B** | Один runner, используемый в **двух режимах**. Batch (`until_stage=`) соблюдает ADR 0006; explicit (`stage=`) **отключает output-validated idempotency**. Слои разделены **по ADR 0009**, а не случайно | MEDIUM (был HIGH) | §12 и C43 переформулировать; owner уточнить |
| **B. Semantic/Vision** (CRITICAL-5) | «Semantic-слой по построению не влияет на отбор; неизменность отбора — инвариант сервиса» | **C** | **Два разных слоя.** Metadata-semantic = canonical decision maker (rank/reject/block). Vision-service = observational, пишет в *review*-манифест. Ingestion seam `vision_tags` **живой**: проба сменила выбранный asset | MEDIUM | §7.3 исправить: 9C — wiring, не снятие архитектурного запрета |
| **C. LocalLibrary** | «Три пути, правила прав уже разошлись; строгая реализация — та, которую никто не вызывает» | **C** | **Один индекс, один rights-authority** (`apply_policy_to_candidate`). Два matcher'а, три policy-обёртки. Проба: 8/10 совпало, ровно **2** расхождения | MEDIUM | §10 и C40 сузить; главный аргумент опровергнут |
| **D. Provider registry** | «Пять расходящихся реестров, ни один не производный» | **D** | Разные **факты**, а не дубли. `PROVIDER_PRIORITY` фильтруется по availability, capabilities перекрывают таблицу — проверено пробой. Runtime-расхождений в каноническом пути нет | LOW | C41 переписать; PLAN-10B как owner **снять** |
| **E. Export targets** | «Каталог обещает 5, renderer делает 3» | **A** (факт), **B** (механизм) | Подтверждено. Уточнение: «3» заявлено в **трёх** production-владельцах; каталог — единственный outlier. `supported_export_targets`/`safe_zone_profile` — ноль production-читателей | LOW-MEDIUM (правдивость) | owner уточнить: PLAN-11 = gate, не implementation |
| **F. FFmpeg** | «Три поколения lossy: сегменты crf 23 → конкатенация crf 20 → субтитры crf 21» | **C** | Три поколения — да, но **условно**. Конкатенация — `-c:v copy`, **не** encode. crf 20 принадлежит duration-control mux и имеет документированную причину | MEDIUM | §14.2 и C45 уточнить; «single-pass тривиален» — неверно |
| **G. Risk boundaries** | «9B-1 = один файл, без gates; 9B-5 = PLAN-5 + approval» | **C** | 9B-1 подтверждён полностью (E-2 **закрыт**). У 9B-5 **пропущены** 6D/6E и reversible retirement | — | §5.5 дополнить (единственный содержательный пробел) |
| **PLAN-5 как blocker** | «Обязателен до 9B-5 и 9B-3» | **D** | Targeted, full и все три smoke-команды работают **сегодня** — проверено исполнением | — | §5.4 исправить: PARALLEL для всех 9B |
| **PLAN-6A blocker** | «Обязателен до 6D → значит до 9B-2» | **C** | 6A→6D — **декларативная** зависимость, не техническая | — | пометить как ordering convention |
| **PLAN-6D/6E blockers** | «Обязательны до 9B-2» | **A** с расширением | Верно, но та же boundary раньше пересекается **9B-5** | — | §5.5 дополнить |
| **PLAN-1C′ → 6E** | «Снять зависимость» | **C** | Снятие безопасно, но по **другой** причине: 6E остаётся upstream 9A транзитивно через 9B-2 | — | CHANGE, не просто REMOVE |

**Главный вывод.** Ни один из семи findings не отменяется, но **четыре из семи
опираются на неверный или упрощённый механизм**, и в трёх случаях это меняет
назначенного owner. Критический путь Proposal 2.1 **не меняется**; меняются
gates у одного слайса (9B-5) и формулировки шести registry-строк.

---

## 2. Method and safety

**FACT.** Ничего не выполнялось: сеть, downloads, платные API, Vision, TTS,
render, provider search. Все пробы шли под `tests/network_guard.py`;
`blocked_attempts == []` во всех прогонах, то есть попыток выхода в сеть не было.

**FACT.** Пробы созданы в session scratchpad **вне репозитория** и в Git не
попали. Состав:

| Проба | Что делает | Ключевой результат |
|---|---|---|
| `probe_orchestration.py` | `run_news_to_short_job` в batch- и single-stage-режиме на 7 downstream families | batch → 0 dispatch, `stage=` → 1 dispatch, `stage=`+`resume` → 0 |
| `probe_semantic.py` | 3 synthetic кандидата, synthetic vision-результат | selection сменился `A_best` → `B_ok` |
| `probe_local_rights.py` | 10 synthetic media_index записей через оба live-пути | 8/10 совпало, 2 расхождения |
| `probe_registry.py` | фактический конструктор + три таблицы + routing | `local_library` не попадает в `ordered_providers` |

**FACT.** Дополнительно исполнены read-only проверки: `python -m ai_youtube
--help`, `capabilities --json`, `applications list` (все exit 0) и targeted
`python -m unittest tests.test_visual_retrieval_repair
tests.test_semantic_asset_selection` (53 теста, 0.116 s, OK).

**Честная граница.** Full offline suite не запускался (E-11 остаётся открытым за
PLAN-4). Реальный render не выполнялся: цепочка FFmpeg установлена чтением
командных билдеров и существующих characterization-тестов, а не исполнением.
CRITICAL-1/CRITICAL-2 повторно не проверялись — приняты доказанными.

---

## 3. Double orchestration

### 3.1. Фактический control-flow

**FACT.** Полный канонический путь (проверено чтением):

```
python -m ai_youtube create …
  → content_creation.service.create_content
  → FullscreenVoiceoverUseCase.execute()                       use_case.py:69
      _prepare_project        → create_news_to_short_job        :89   (не runner)
      [dry_run? → run_news_to_short_job(dry_run=True) и ВЫХОД]  :156
      _run_safe_pipeline      → run(until_stage="asset_search",
                                     resume=True, force_stage=…) :182
      _run_voice_stage        → run(stage="voice", …)            :253  ← только если нет existing_voice
      [voice gate / draft gate → возможен ранний выход]
      _run_subtitles          → run(stage="subtitles")           :455  ← только если style != "disabled"
      _run_music              → prepare_project_music            :474  ← стадии в runner НЕ существует
      _render_and_export      → run(stage="preview_render")      :499
                              → run(stage="quality_check")       :510
                              → run(stage="final_render")        :527
                              → run(stage="export")              :553
```

**FACT — уточнение количества.** «Семь вызовов» — верхняя граница, а не норма.
`dry_run` взаимоисключающ с остальными (ранний `return`, use_case.py:71-73).
Вызов voice пропускается при существующей озвучке, subtitles — при
`--subtitles disabled`. Фактический диапазон — **4–7** вызовов.

### 3.2. Механизм, который предыдущие аудиты не назвали

**FACT.** Решающая строка — [pipeline.py:157](../../src/news/pipeline.py:157):

```python
if not force_stage and stage_name in completed and not stage:
```

`and not stage` означает: когда запрошена **явная** стадия, проверка
«completed + валидный output → пропустить» **не применяется вообще**.

**FACT (проба `probe_orchestration.py`).** На семи downstream-семействах, каждое
из которых предварительно доведено до валидного `completed`:

| Режим вызова | dispatch-вызовов |
|---|---|
| `until_stage=X` (batch) | **0** для всех семи |
| `stage=X` (explicit) | **1** для всех семи |
| `stage=X, resume=True` | **0** для voice и final_render |

**INFERENCE.** ADR 0006 «Output-validated idempotency» формулирует политику
безусловно («`status == completed` + валидный output + нет `force_stage` →
пропустить»), но фактически она действует **только в batch-режиме**. Канонический
use case исполняет 6 из 12 стадий в explicit-режиме, то есть **вне** контракта
ADR 0006.

**FACT.** Существующий тест
[test_news_stage_idempotency.py:68](../../tests/test_news_stage_idempotency.py:68)
проверяет пропуск только через `until_stage=`. Контракт для `stage=` не покрыт
ни одним тестом.

**FACT.** Третья строка пробы показывает, что runner **уже умеет** нужное
поведение: `stage=X` вместе с `resume=True` пропускает завершённую стадию. Use
case просто не передаёт `resume` в хвостовых вызовах.

### 3.3. Два owner'а или намеренное расслоение?

**Ответ: 3 — архитектура смешанная, и это зафиксировано ADR.**

**FACT.** [ADR 0009](../adr/0009-fullscreen-voiceover-application-boundary.md:26):
«Its **application-level orchestration** lives in `fullscreen_voiceover/use_case.py`»
и «The boundary re-exports … `run_news_to_short_job` contracts. **Ownership
remains in `src.news`**». То есть расслоение — принятое решение, а не
случайность.

Фактические ответственности:

| Слой | Владеет | Не владеет |
|---|---|---|
| `run_news_to_short_job` | список и порядок `NEWS_TO_SHORT_STAGES`; исполнение стадии; output-validation; `job.status`; persistence; completion overrides | application-политикой |
| `FullscreenVoiceoverUseCase` | paid approval gate, manual audio import, **music** (стадии в runner нет), draft completion gate, `--subtitles disabled`, сборка `ContentCreationResult`, rerun commands, progress notify; **и порядком хвостовых 6 стадий** | исполнением стадии, валидацией output, статусом job |

**INFERENCE.** Дублируется **ровно один факт**: порядок стадий 7–12 закодирован
и в `NEWS_TO_SHORT_STAGES`, и в порядке вызова методов use case. Всё остальное
разделено корректно.

### 3.4. Что реально может произойти, а что нет

| Риск | Вердикт | Evidence |
|---|---|---|
| повторный **платный TTS** | **НЕТ** | три независимых guard'а: `existing_voice` в use_case.py:245; `localization.reuse_existing_narration` внутри стадии ([voice_stage.py:164](../../src/news/voice_stage.py:164)); approval-hash → `PermissionError` ([narration_workflow.py:106](../../src/audio/narration_workflow.py:106)). Плюс 3 существующих теста в `test_project_naming_and_resume.py:416-447` |
| повторный **paid operation** любого рода | **НЕТ** | единственный платный путь — voice; Vision выключен и вызывается вне runner |
| повторный **локальный render** | **ДА** | `preview_render` и `final_render` всегда переисполняются в explicit-режиме. Стоимость — только время ffmpeg. Это **уже** записано в плане (PLAN-3, «у 7 проектов могут повториться только локальные preview/final render») |
| **неправильный resume** | **ЧАСТИЧНО** | голова цепочки соблюдает resume, хвост — нет. Наблюдаемо как «resume завершённого проекта перерендеривает» |
| **неправильный force** | **ЧАСТИЧНО** | `force_stage` передаётся только в `_run_safe_pipeline`; для хвоста флаг инертен (стадии и так исполняются) |
| **пропуск stage** | **НЕТ дефекта** | `subtitles` при `disabled` и `music` вне `NEWS_TO_SHORT_STAGES` — намеренная application-политика |
| **повторная stage execution** | **ДА** | см. §3.2; это и есть точный дефект |

### 3.5. Verdict

**B — finding подтверждён, механизм иной.**

- **FACT:** несколько вызовов существуют; их 4–7, не всегда 7.
- **FACT:** реальный дефект — не «два owner'а», а **отключение контракта ADR
  0006 в explicit-режиме**, не покрытое ни одним тестом.
- **INFERENCE:** формулировка «два конкурирующих orchestration owner» вводит
  исполнителя в заблуждение: она предлагает убрать пошаговые вызовы, тогда как
  между стадиями действительно нужны application-шаги (paid gate, manual audio,
  music, draft gate), которых runner не знает и знать не должен.
- **Severity: MEDIUM**, не HIGH. Контрактный дефект, не потеря данных и не деньги.
- **Нужен ли target «один orchestration owner»?** В такой формулировке — **нет**.
  Правильный target: **один контракт идемпотентности, действующий во всех
  режимах вызова**.
- **PLAN-13B как owner:** подходит для крупной конвергенции «один владелец
  порядка стадий», но **не** для дешёвого точного исправления. Самая дешёвая
  проверяемая правка — передавать `resume=True` в хвостовых вызовах (или
  декларировать план стадий один раз) — живёт внутри контракта ADR 0006,
  владельцы которого `src/news/pipeline.py` и `NewsProjectStore`.
- **RECOMMENDATION:** C43 разделить на две строки — точный дефект контракта
  (owner: ADR 0006 / `src/news/pipeline.py`, отдельный bounded slice) и
  архитектурную конвергенцию (owner: PLAN-13B). Предусловие «подтвердить
  `resume`/`force`/`stop-stage` callers» сохранить: [E-9 остаётся открытым].

---

## 4. Semantic/Vision decision path

### 4.1. Полный decision path

**FACT.** [asset_manifest_builder.py:185-202](../../src/news/asset_manifest_builder.py:185):

```
build()  per scene:
  _prepare_scene        analyze_scene → SemanticScene; route_providers; build_scene_queries
                        candidates = user_assets + rank_local_assets
  _search_scene_providers                                   +provider candidates
  _add_generated_infographic
  _select_scene_asset   selection_config["mode"] == "semantic"  (DEFAULT, :209)
                        → select_best_with_video → select_best_candidate → rank_candidates
  _prepare_visual_review  technical_rerank_enabled? → МОЖЕТ СМЕНИТЬ state.selected  (:564-571)
  _download_and_complete / _apply_fallbacks / _record_scene
после цикла:
  _write_reviews        semantic_visual.enabled? → analyse_semantic_visual_for_project  (:905)
  _final_manifest       _semantic_visual_summary()  → жёстко "semantic_rerank_enabled": False  (:997)
```

### 4.2. Два разных слоя, которые прошлые аудиты смешали

**FACT — слой 1, metadata-semantic (`src/assets/semantic_selection/`).**
Это **и есть** движок отбора. `selection_config["mode"] = "semantic"` —
значение по умолчанию ([:209](../../src/news/asset_manifest_builder.py:209)).
`rank_candidates` вычисляет `semantic_score` и `semantic_match_status`, пишет
`reject_reasons` и формирует `SelectionDecision`.

**FACT — слой 1 влияет на blocking.** В `src/assets/completion/modes.py`:
- `:307` — `if decision.semantic_status == "mismatched": reasons.append(BLOCK_FACTUALLY_MISLEADING)`;
- `:290` — `reason == "vision_mismatch"` → `BLOCK_MUST_AVOID`;
- `:309` — `support_status == SUPPORT_UNSUPPORTED` → `BLOCK_FACTUALLY_MISLEADING`.

**FACT — слой 2, `semantic_visual` (платный Vision).** Вызывается из
`_write_reviews()` **после** всего цикла отбора и работает с
`assets/review/visual_review_manifest.json`, а не с `assets/assets_manifest.json`
([semantic_visual_service.py:172-183](../../src/assets/semantic_visual_service.py:172)).
`semantic_rank` / `semantic_score` / `hard_reject` попадают **только** в
review-манифест.

**FACT.** `_selection_fingerprint`
([:392](../../src/assets/semantic_visual_service.py:392)) сравнивает
`selected_candidate` review-манифеста до и после и в случае расхождения
дописывает **строку-предупреждение**. Ничто в функции `selected_candidate` не
меняет, поэтому предупреждение не может сработать. Это **защитная
самопроверка**, а не структурный инвариант, запрещающий переранжирование.

**FACT.** `_semantic_visual_summary` ([:991-998](../../src/news/asset_manifest_builder.py:991))
жёстко пишет `"semantic_rerank_enabled": False`, хотя реальное значение конфига
уже разобрано в `selection_config` ([:251-256](../../src/news/asset_manifest_builder.py:251)).
Repo-wide поиск: **ноль** читателей этого поля из манифеста. То есть это дефект
**отчётности**, а не решения.

### 4.3. Ingestion seam живой — доказано исполнением

**FACT.** `vision_tags` — первоклассный вход слоя 1:
[evidence.py:195-200](../../src/assets/semantic_selection/evidence.py:195) кладёт
их в `token_set` и делает `has_evidence` истинным;
[candidate_ranker.py:380](../../src/assets/semantic_selection/candidate_ranker.py:380)
превращает пересечение с `must_not_include` в `vision_mismatch`.

**FACT (проба `probe_semantic.py`).** Три synthetic кандидата, сцена
`solar power plant desert`, `must_not_include = [cartoon, animation]`:

| Сценарий | selected | сменился? |
|---|---|---|
| без semantic/vision-результата | `A_best` | — |
| vision говорит, что лучший кандидат — мультипликация | **`B_ok`** | **ДА** (`A_best` отклонён: `non_real_video_footage:cartoon`) |
| vision подтверждает слабейшего кандидата | `A_best` | нет |

**FACT.** Продюсера у `vision_tags` в каноническом пути нет: единственные
источники — запись локальной медиатеки
([:1296](../../src/news/asset_manifest_builder.py:1296)) и сырой ответ провайдера
([asset_provider_adapters.py:412](../../src/news/asset_provider_adapters.py:412)).
Vision-сервис их не пишет.

**FACT.** `vision_validator.validate_candidate_vision` — 7-строчная заглушка с
**нулём callers** в production (экспортируется только из `__init__.py`).

**FACT — второй живой hook переотбора.** `visual_preview.technical_rerank_enabled`
может сменить `state.selected` **после** первичного отбора
([:564-571](../../src/news/asset_manifest_builder.py:564)). Значение по умолчанию
в `config/visual_preview.json` — `false`.

### 4.4. Verdict

**C — подтверждён частично; scope и механизм существенно иные.**

Ответы на поставленные вопросы:

1. **Semantic полностью observational?** — **НЕТ.** Metadata-semantic слой
   является каноническим владельцем решения.
2. **Влияет только косвенно?** — неприменимо.
3. **Может влиять на blocking, но не на ranking?** — влияет **и на то, и на
   другое** (modes.py:290/307/309 + rank_candidates).
4. **Может реально сменить selected asset?** — **ДА**, доказано пробой.

Наблюдательным относительно `assets_manifest.json` является **только платный
Vision-сервис**, и то потому, что у него нет продюсера в нужный момент, а не
потому, что архитектура это запрещает.

**Порядок `provider-ready queries → candidates → semantic → rank/select` —
подтверждён корректным.** PLAN-9C — **правильный existing owner**.

**RECOMMENDATION.** Formulation в Proposal §7.3 — «9C — не «включить флаг», а
снять архитектурное ограничение» — **неверна и должна быть исправлена**.
Архитектурного запрета не существует; `_selection_fingerprint` — самопроверка,
а не вето. 9C — это **producer→consumer wiring**: заставить Vision-результат
попадать в кандидатов (через существующие `vision_tags` / поля
`SelectionDecision`) **до** отбора, вместо записи в review-манифест **после**.
Отдельной строкой зафиксировать дефект отчётности `_semantic_visual_summary:997`.

---

## 5. LocalLibrary responsibility map

### 5.1. Не принимать «три пути = три дубля»

**FACT — один индекс.** Все потребители читают
`<library_root>/metadata/media_index.json`:
`asset_manager.py:126`, `local_library_provider.py:25`, `video_asset_engine.py:59`,
`music_engine.py:34`.

**FACT — два matcher'а, не три.** Путь #3 (`video_asset_engine.py:117`)
**вызывает ту же самую функцию** `media_library.search_local_assets`, что и путь
#1. Это не третья реализация поиска, а второй потребитель первой.

| | PATH 1 `rank_local_assets` | PATH 2 `LocalLibraryStockProvider` | PATH 3 legacy documentary |
|---|---|---|---|
| ENTRYPOINT | `asset_manifest_builder.py:1246` | `local_library_provider.py:41` | `video_asset_engine.py:116` |
| CALLERS | `_prepare_scene:295` (канонический путь) | `provider_diagnostics.py:125` + тесты | `pipeline.py` (legacy) |
| MATCHER | `media_library.search_local_assets` (score+reasons) | собственный token-intersection | **тот же** `media_library.search_local_assets` |
| INPUT | scene dict; `primary_query.split()` | `AssetSearchRequest` | scene dict; `visual_keywords` |
| INDEX | тот же `media_index.json` | тот же | тот же |
| ПРОХОДИТ `query_adapter`? | нет | да (если бы был зарегистрирован) | нет |
| RIGHTS | `with_policy_decision` → `apply_policy_to_candidate` | `_is_current_safe_record` → `apply_policy_to_candidate` | **нет rights-гейта на локальном пути** |
| PROVENANCE | пробрасывается в кандидата | требуется как dict до политики | не проверяется |
| DEDUP | `used_asset_ids` skip; `duplicate_penalty` — **мёртвый код** (`continue` на :1275 срабатывает раньше) | нет | `mark_asset_used_in_video` в индексе |
| RANKING | relevance + quality + vertical, затем общий `rank_candidates` | сортировка по (портретность, площадь) — **релевантности нет** | score + survival-специфичный реранк |
| DIVERSITY | нет | нет | **`min_local_diversity_per_scene` / `reserved_download_slots`** (:128-135) |
| DOWNLOAD | локальный файл уже на диске | contract `download()` с checksum/validation | кэш + докачка |
| FAILURE | пустой список | `ProviderNoResultsError` | fallback на generated motion |
| OUTPUT | dict, совместимый со слоем решений | `AssetCandidate` | clip dict legacy-формата |

### 5.2. Соседние capability, которые НЕЛЬЗЯ вливать в конвергенцию

**FACT.** В `_prepare_scene` кандидаты собираются из трёх независимых источников
([:293-301](../../src/news/asset_manifest_builder.py:293)):

- `rank_user_assets` ← `inspect_user_asset` — **пользовательские файлы этого
  проекта** (`--assets`);
- `rank_local_assets` — **глобальная локальная стоковая библиотека**;
- `self.project_pool` ([:774-776](../../src/news/asset_manifest_builder.py:774)) —
  **уже скачанные в проект ассеты**, переиспользуемые между сценами.

**INFERENCE.** Это три **разные легитимные ответственности**. Конвергенция
локальной медиатеки не должна их поглощать; Proposal §10 этой границы не
проводит.

### 5.3. Verdict по вопросу A/B/C

**C — смешанная ситуация**, разрешаемая так:

- **ОДНА capability** — глобальная локальная стоковая библиотека: один индекс,
  один rights-authority, два matcher'а, три policy-обёртки. Здесь конвергенция
  обоснована.
- **ДВЕ соседние legitimate capability** — user/manual assets и project pool.
  Их трогать нельзя.
- **PATH 3** принадлежит legacy documentary pipeline и умирает в PLAN-L3; из
  него нужно спасти **diversity-резерв** (§5.4 ниже), а не саму реализацию.

**Четвёртый путь не создавать** — подтверждаю.

---

## 6. LocalLibrary rights/provenance comparison

### 6.1. Rights-authority общий

**FACT.** Оба живых пути завершаются одним и тем же каноническим решением
`apply_policy_to_candidate`
([license_policy.py:211](../../src/assets/license_policy.py:211)), которое
управляется `config/license_policy.json`:

- PATH 1: `with_policy_decision(item)`
  ([asset_provider_adapters.py:154](../../src/news/asset_provider_adapters.py:154))
  → `updated["allowed_for_render"] = decision.allowed_for_render`;
- PATH 2: прямой вызов + отказ при `review_required or not allowed_for_render`.

**FACT — критическое следствие.** Вычисление
`rights_status = asset.get("rights_status") or RIGHTS_REFERENCE_ONLY;
allowed = rights_status in ALLOWED_RENDER_RIGHTS`
([:1272-1273](../../src/news/asset_manifest_builder.py:1272)) **перезаписывается**
политикой к моменту выхода из функции. Эти две строки — фактически мёртвый код.

### 6.2. Построчное сравнение и проба

**FACT (проба `probe_local_rights.py`, 10 synthetic записей, реальные временные
файлы).** PATH 1 считался разрешающим, если запись пережила `rank_local_assets`
**и** `modes.blocking_reasons` вернул пусто. PATH 2 — если пережила `search`.

| Случай | PATH 1 | PATH 2 | Расхождение |
|---|---|---|---|
| A полностью совместимая запись | allow | allow | — |
| B `schema_version = 0` | block | block | — |
| C **`provenance` отсутствует** | **allow** | **block** | **#1 разрешает, #2 запрещает** |
| D `license` без `license_name` | block | block | — |
| E `rights_status = reference_only` | allow | allow | — |
| F `rights_status` отсутствует | allow | allow | — |
| G `allowed_for_render` = строка `"false"` | allow | allow | — |
| H **`review_required = True`** | **allow** | **block** | **#1 разрешает, #2 запрещает** |
| I `license_name` вне policy-таблицы | block | block | — |
| J `source_url`/`source_page` отсутствуют | block | block | — |

**Ответ на прямой вопрос задания:**

- **Есть ли случай, когда #1 разрешит, а #2 запретит?** — **ДА, ровно два:**
  отсутствующий `provenance` и явный `review_required: True`.
- **И наоборот?** — **НЕТ.** Ни одного случая, где #2 разрешает, а #1 блокирует.

### 6.3. Что из Proposal §10 опровергнуто

**FACT — опровергнуто.** Утверждение «#1 допускает `rights_status in
ALLOWED_RENDER_RIGHTS` с дефолтом `RIGHTS_REFERENCE_ONLY`» как источник
послабления — **неверно**. Случаи E и F расхождения не дают: политика
перезаписывает интерим-значение.

**FACT — опровергнуто.** «Более строгая реализация — та, которую никто не
вызывает» — упрощение. Дополнительная строгость #2 сводится к **двум** условиям
пре-фильтра. При этом на финальном гейте **#1 строже** #2 сразу по трём осям:
`_rights_are_allowed` требует непустое и не-`unknown` `license_name`
([modes.py:466](../../src/assets/completion/modes.py:466)), проверяет
`allowed_for_render is True` по идентичности, а не по truthiness
([:520](../../src/assets/completion/modes.py:520)), и валидирует `rights_status`
против белого списка — ничего из этого `_is_current_safe_record` не делает.

### 6.4. Новый дефект, найденный этой проверкой

**FACT.** Случай H: запись, **явно помеченная `review_required: True`**,
проходит PATH 1, потому что policy-правило `user_owned` для `local_library`
устанавливает `review_required: false` и перезаписывает исходный флаг.

**INFERENCE.** Это **fail-open** на явном флаге ревью — узкий, но настоящий
rights-дефект, и он не описан ни в одном из предыдущих аудитов. Severity: MEDIUM
(касается только локальной медиатеки, где записи создаёт сам проект).

**RECOMMENDATION.** Зафиксировать отдельной registry-строкой. Класс `[HARD]`
(rights). Правка — тривиальная: не позволять policy-правилу снимать явный
`review_required` записи; owner — `apply_policy_to_candidate` либо
`with_policy_decision`. Не смешивать с конвергенцией путей.

### 6.5. Legacy diversity reserve

**FACT.** [video_asset_engine.py:128-135](../../src/video_asset_engine.py:128):

```python
min_diversity = int(library_config.get("min_local_diversity_per_scene", target_count))
local_diversity_gap = max(0, min_diversity - len({m["asset"].get("local_path","") for m in local_matches}))
reserved_download_slots = min(local_diversity_gap, max_new_downloads_per_scene, target_count - 1)
local_take = max(0, target_count - reserved_download_slots)
```

Смысл: «не заполняй сцену несколькими копиями одного локального клипа — оставь
слоты под новый материал». Уникальность считается по `local_path`.

**FACT — современного эквивалента нет.** В PATH 1 есть только пропуск по
`used_asset_ids` ([:1275-1276](../../src/news/asset_manifest_builder.py:1275)) и
`duplicate_penalty`, который до применения не доживает (`continue` срабатывает
раньше). Резервирования слотов под разнообразие нет ни в
`completion/ladder.py`, ни в селекторе.

**RECOMMENDATION.** Salvage подтверждён (класс `MIGRATE KNOWLEDGE`, потребитель
PLAN-10D). Формулировка Proposal §6 верна. Отметить дополнительно, что
`duplicate_penalty` в `rank_local_assets` — мёртвый код и подлежит удалению
вместе с этой работой.

---

## 7. Provider registry/capability ownership

### 7.1. Проба

**FACT (`probe_registry.py`, без API-ключей в окружении):**

```
фактически сконструировано:  ['wikimedia', 'nasa_images', 'internet_archive']

PROVIDER_QUERY_LANGUAGES  объявляет 9  не сконструированы: pexels, pixabay, unsplash,
                                                            envato_manual, local_library, fake
DEFAULT_PROVIDER_ORDER    объявляет 7  не сконструированы: local_library, pexels, pixabay, envato_manual
PROVIDER_PRIORITY (union) объявляет 6  не сконструированы: local_library, pexels, pixabay

язык:  wikimedia/nasa_images/internet_archive → table=('en',) capabilities=['en'] effective=('en',)

routing(scene, provider_names=constructed):
  source_class      = exact_location
  ordered_providers = ['nasa_images', 'wikimedia', 'internet_archive']
  'local_library' in ordered_providers -> False
  PROVIDER_PRIORITY[exact_location]     = ['local_library','nasa_images','wikimedia',
                                           'internet_archive','pexels','pixabay']

routing(scene) без provider_names:
  ordered_providers = ['local_library','nasa_images','wikimedia','internet_archive',
                       'pexels','pixabay','envato_manual']
```

**INFERENCE.** Таблица перечисляет имена, которых в прогоне нет, и **корректно
их отфильтровывает**. Runtime-расхождения в каноническом пути **не возникает**.

### 7.2. Матрица фактов

| FACT | OWNER | DUPLICATED? | SHOULD DERIVE FROM REGISTRY? | SHOULD REMAIN SEPARATE? |
|---|---|---|---|---|
| какие провайдеры существуют в этом прогоне | `providers/registry.create_default_stock_providers` + env | **нет** | это и **есть** registry | — |
| capabilities: media types, download/preview/license support | `provider.capabilities()` каждого провайдера | **нет** | уже оттуда | — |
| query languages зарегистрированного провайдера | `capabilities().query_languages` | **нет** — проверено: capabilities перекрывают таблицу ([query_adapter.py:133-138](../../src/assets/query_adapter.py:133)) | уже оттуда | — |
| query language **неизвестного** имени | `query_adapter.PROVIDER_QUERY_LANGUAGES` | **нет** — задокументированный fallback | нет | **да**, оставить fallback |
| приоритет провайдеров по source class | `scene_strategy.PROVIDER_PRIORITY` | **нет** — другой факт: policy-предпочтение, пересекаемое с availability | **нет** | **да** |
| порядок, когда caller не назвал провайдеров | `provider_routing.DEFAULT_PROVIDER_ORDER` | вестигиальный: канонический путь его не использует | — | удалить либо согласовать |
| инвентарь **конструируемых** провайдеров, включая `fake` и manual | `provider_diagnostics._provider_specs` | **нет** — другой факт: что можно построить, а не что построено | нет | **да** |
| enabled state | env-переменные + `environment_enabled` | нет | — | — |
| cost / availability | не моделируются нигде | — | — | — |

**FACT — намеренность зафиксирована в коде.**
[scene_strategy.py:48-53](../../src/assets/scene_strategy.py:48): «A name that is
not registered in this run is skipped, so an order may list providers that do not
exist here — that is what makes the table readable rather than conditional».
[provider_routing.py:20-21](../../src/assets/provider_routing.py:20): «Order used
when a caller names no providers at all… the per-scene order comes from the
strategy, not from here».

### 7.3. Почему `local_library` есть в декларациях и нет в registry

**FACT.** Это **не** ошибка реестра и **не** intentional disconnected capability
в чистом виде. Это следствие Finding C: локальная медиатека **действительно
ищется**, но **мимо provider-контракта** — через `rank_local_assets`. Поэтому
таблицы, описывающие «провайдер local_library», описывают путь, который в
provider-механике не участвует.

**INFERENCE.** Это **одно** расхождение декларации и поведения, принадлежащее
LocalLibrary-конвергенции, а не проблема «пяти реестров».

**FACT — побочно.** `unsplash` объявлен в `PROVIDER_QUERY_LANGUAGES:49`,
`scene_strategy._GENERIC_STOCK:250` и `candidate_ranker:136`, но
`src/providers/unsplash_provider.py` предоставляет функцию, а не `StockProvider`,
и нигде не конструируется. Полностью осиротевшее имя.

### 7.4. Verdict

**D — опровергнут** в части «пять расходящихся source of truth». Остаётся
**LOW**-severity остаток: вестигиальный `DEFAULT_PROVIDER_ORDER`, осиротевший
`unsplash` и декларация `local_library`.

**Является ли PLAN-10B правильным owner конвергенции?** — **НЕТ.** Конвергировать
нечего: механизм «capabilities важнее таблицы» уже существует и работает.
Загружать PLAN-10B (pagination и provider contract) чужой работой смысла нет.
[E-5 закрыт отрицательно.]

**RECOMMENDATION.** C41 переписать: не «convergence к providers/registry», а
(a) декларация `local_library` устраняется вместе с LocalLibrary-конвергенцией
→ **PLAN-10D**; (b) `DEFAULT_PROVIDER_ORDER` и `unsplash` — мелкая уборка внутри
любого слайса, который и так трогает routing; отдельного ID не требуется.
PLAN-13C как альтернативный owner **не нужен**.

---

## 8. Export-target truthfulness

### 8.1. Фактическая цепочка

**FACT.** [catalog.py:229-305](../../src/production_catalog/catalog.py:229)
регистрирует **пять** целей — `youtube_shorts`, `instagram_reels`, `tiktok`,
`facebook_reels`, `stories`. У всех пяти `enabled=True`,
`implementation_status="active"`, различный `output_filename`, одинаковый
`safe_zone_profile="vertical_9x16_standard"`.

**FACT.** Оба шаблона объявляют все пять в `supported_export_targets`
([:110](../../src/production_catalog/catalog.py:110), [:186](../../src/production_catalog/catalog.py:186)).

**FACT.** [final_renderer.py:474-478](../../src/news/final_renderer.py:474)
создаёт ровно три файла: `youtube_shorts.mp4`, `instagram_reels.mp4`,
`facebook_reels.mp4`. `tiktok.mp4` и `stories.mp4` не создаются никогда.

**FACT — уточнение, которого не было в предыдущих аудитах.** «Три» — не каприз
renderer'а, а согласованный контракт **трёх** production-владельцев:

| Владелец | Значение |
|---|---|
| `final_renderer._copy_platform_outputs:475` | 3 имени |
| `exporter._render_outputs:66-73` (defaults) | `master`, `youtube_shorts`, `instagram_reels`, `facebook_reels`, `no_subtitles` |
| `NewsJob.platforms` default ([models.py:174](../../src/news/models.py:174)) | `["youtube_shorts","instagram_reels","facebook_reels"]` |

Каталог с пятью целями — **единственный outlier**.

**FACT — потребителей нет.** `supported_export_targets` читается только
`production_catalog/cli.py:208` (печать) и сериализуется в
`capabilities.py:410`. `safe_zone_profile` читается только `cli.py:239` (печать).
**Ни то, ни другое не влияет на render.**

**FACT — другого export-слоя нет.** Repo-wide поиск по именам платформенных
файлов даёт только `final_renderer.py`, `exporter.py`, `models.py`,
`production_catalog/catalog.py` и тесты. Первый audit ничего не пропустил.

**FACT.** Master действительно копируется побайтово (`shutil.copyfile`) — никакой
адаптации под площадку (длительность, битрейт, safe zone) не выполняется.

### 8.2. Verdict

**A по факту, B по механизму.** Расхождение подтверждено; но «продукт обещает
пять» — это утверждение **одного файла без потребителей**, а не сквозная
продуктовая декларация.

**Минимальное направление — truthful catalog.** Обоснование не «так дешевле», а
evidence: три production-владельца **уже** согласованно заявляют три цели;
привести пятого к ним — это привести outlier к большинству. Создание двух
дополнительных байт-в-байт копий ухудшило бы MEDIUM-6 (утроение размера
проекта), не добавив продуктовой ценности. Настоящая platform export capability
(разные битрейты/длительности/safe zone) — отдельная будущая продуктовая работа,
и `safe_zone_profile` уже стоит как для неё заготовленное поле.

**Owner.** Отнесение fix к **PLAN-11 неверно**: PLAN-11 — product evidence gate,
у него `required verification: product gate` и `rollback: —`, и он **не имеет
allowed zones для source**. Правильно разделить:

- **PLAN-11 остаётся evidence gate**, который такую ложь обязан ловить (общее
  требование «нет ложного `publish_ready`» расширяется на «каталог не обещает
  несуществующий output»);
- **implementation owner** — bounded slice, меняющий `production_catalog`
  (одна правка `supported_export_targets` + снятие двух `ExportTargetDefinition`
  либо перевод их в `implementation_status="planned"`, что честнее и сохраняет
  roadmap). Нового PLAN-ID не требуется.

---

## 9. FFmpeg encode chain

### 9.1. Полная цепочка

**FACT.** [final_renderer.py:56-133](../../src/news/final_renderer.py:56):

| # | Шаг | Вход → выход | Кодек | CRF/preset | Фильтры | Причина | Обязателен? |
|---|---|---|---|---|---|---|---|
| 1 | `_render_video_segment` :279 | исходный клип → сегмент | **libx264** | veryfast / **23** | `scale`/`crop` из `crop_decision` | нарезка слота на таймлайн сцены, приведение к canvas | **lossy #1** |
| 1' | `_render_image_segment` :314 | still → сегмент | **libx264** | veryfast / **23** | `scale`,`zoompan`,`setsar`,`format` | pan/zoom по стиллу | **lossy #1** |
| 2 | concat :69-84 | сегменты → `silent_master.mp4` | **`-c:v copy`** | — | — | склейка | **НЕ encode** |
| 3a | `_mux_voice_only` :486 / `_mux_voice_and_music` :499 | + голос (+музыка) | **libx264** через `_duration_control_args` | veryfast / **20** | `tpad` или `null` | **точная длительность**: `-shortest`+`copy` режет по keyframe и промахивается | **lossy #2**, есть audio |
| 3b | нет audio :121 | → `no_subtitles.mp4` | **`-c:v copy`** | — | — | — | **НЕ encode** |
| 4a | `_burn_ass_subtitles` :582 | + ASS | **libx264**, `-c:a copy` | veryfast / **21** | `subtitles=…` | прожиг субтитров | **lossy #3**, есть `ass_path` |
| 4b | нет ASS :132 | `shutil.copyfile` | — | — | — | — | **НЕ encode** |
| 5 | `_copy_platform_outputs` :458 | master → 3 имени | `shutil.copyfile` | — | — | — | **НЕ encode** |

### 9.2. Ответ на точный вопрос

**Действительно ли один final video в normal canonical path проходит через ТРИ
lossy H.264 generations?**

**ДА — но условно.** Три поколения при **audio present AND ASS subtitles
present**. Это состояние по умолчанию для `fullscreen_voiceover_v1` (стадия
subtitles исполняется, если не передан `--subtitles disabled`).

- нет озвучки → шаг 3 становится `-c:v copy` → **две** генерации;
- нет ASS → шаг 4 становится `shutil.copyfile` → **две** генерации;
- нет обоих → **одна** генерация.

Стадии **не** взаимоисключающие: 3 и 4 при штатном сценарии выполняются обе.

### 9.3. Что предыдущие аудиты описали неточно

**FACT — исправление.** И первый audit (MEDIUM-1), и Proposal §14.2 утверждают
«затем **конкатенация** перекодируется в `-crf 20`». Конкатенация выполняется с
`-c:v copy` и **бесплатна** ([:80-81](../../src/news/final_renderer.py:80)).
Перекодирование в crf 20 принадлежит **audio-mux с duration control** и имеет
документированную причину
([:553-561](../../src/news/final_renderer.py:553)): комбинация `-shortest` +
`-c:v copy` уже приводила к измеренному дефекту (~2.75 s лишнего хвоста на первом
живом рендере).

### 9.4. FACT / INFERENCE / RECOMMENDATION

- **FACT:** три lossy-поколения в штатном пути; таблица §9.1 — по одному шагу.
- **INFERENCE:** это ухудшает качество и скорость. Величину **никто не измерял**
  — ни один аудит не рендерил. Заявлять «заметно лучше картинка» как факт нельзя.
- **RECOMMENDATION:** «single-pass как тривиальная замена» — **неверно**.
  Шаг 3 нельзя просто убрать: он держит точную длительность и `tpad`-расширение
  под narration_plus_tail. Шаг 1 нельзя просто убрать: у каждого сегмента свои
  crop/zoompan-фильтры, поэтому нужен полноценный `concat`-filtergraph с
  per-input цепочками.

  **Самое дешёвое улучшение, подтверждённое evidence: слить шаги 3 и 4 в один
  encode.** Оба уже перекодируют всё видео целиком; `subtitles` + `tpad` + `-t`
  + `-c:a aac` композируются в одну команду. Результат: 3 → 2 поколения, один
  владелец, семантика таймлайна не меняется. Полный single-pass — отдельная,
  существенно более крупная работа.

- **FACT — база для characterization уже есть.**
  [test_final_renderer_end_tail.py:82-101](../../tests/test_final_renderer_end_tail.py:82)
  патчит `_run_ffmpeg` и проверяет форму аргументов mux. Требование
  «characterization сначала» выполнимо без реального рендера.

### 9.5. Owner

**PLAN-8 не является implementation owner.** PLAN-8 — это `PRODUCT_PLAN.md`,
docs-only слайс (`разрешённые зоны: docs/current/PRODUCT_PLAN.md`,
`required verification: docs QA`). Он может и должен **хранить roadmap-запись**,
но исполнить правку renderer'а не может.

**RECOMMENDATION.** C45 записать так: **roadmap-владелец — PLAN-8; implementation
owner — будущий bounded renderer slice, создаваемый в момент планирования, после
PLAN-11.** Явно указать, что нового PLAN-ID сейчас не создаётся и что цель
первого шага — слияние шагов 3+4, а не «один проход».

---

## 10. Critical-path risk boundary analysis

### 10.1. Risk matrix по фактическим footprint'ам

| Slice | Files / owners | Public CLI? | Persisted bytes? | Shared contract? | Destructive? | Network/paid? | Required test level | Required governance gate |
|---|---|---|---|---|---|---|---|---|
| **9B-0** | новый test-модуль | нет | нет | нет | нет | нет | targeted + `network_guard` | — |
| **9B-1** | `query_adapter.py` + 3 test-модуля; **2** production-импортёра | нет | значения в свободном поле, **0 читателей** | нет | нет | нет | targeted | — (достаточно 1D/2/3/4) |
| **9B-5** | `commands/content.py`, `request_builder`, `cli/commands/*`, `use_case.resolve_content_inputs`; **+ retire `apps/news_to_short`** (2 test-caller'а, свой README) | **ДА** (`--input-mode choices`) | нет | нет | **ДА** | нет | targeted + smoke + `full` | **owner approval + 6D + 6E + reversible retirement** |
| **9B-4** | `providers/deterministic.py`, `validation.py`, `quality_check.py` + 3 test-модуля | наблюдаемое поведение `strict` | нет | `script_validation` | нет | нет | targeted + `full` | owner approval |
| **9B-2** | `query_adapter`, `script_generator`, `legacy_format`, `semantic_selection/*` | нет | **ДА** (содержимое visual plan) | да | **ДА** (orca-hardcode) | нет | targeted + `full` | **6D + 6E + reversible retirement** |
| **9B-3** | GLOSSARY-матчер, `legacy_broad_query`, `make_stock_query`, `query_generator` (**5** callers) | нет | да | да | **ДА** | нет | targeted + `full` | **6E + reversible retirement** |

### 10.2. 9B-1 — предложение проверено полностью

**FACT — blast radius.** Production-импортёров `query_adapter` ровно два:
`asset_manifest_builder.py:29,276` и `asset_scene_completion.py:20,289`.
Test-модулей три: `test_slot_aware_retrieval`, `test_visual_retrieval_regression`,
`test_visual_retrieval_repair`. Заявление «затрагивает только `query_adapter.py`»
подтверждается.

**FACT — E-2 ЗАКРЫТ.** Проверено по всем пяти подвопросам:

1. **Попадает ли `ProviderQuery.source` в persisted asset manifest?** — **ДА.**
   `query_plan.to_dict()` пишется в `assets_manifest.json` дважды: в
   `_scene_entry` ([:845](../../src/news/asset_manifest_builder.py:845)) и в
   запись missing-сцены ([:814](../../src/news/asset_manifest_builder.py:814)).
2. **Является ли это schema/public/persisted change?** — **НЕТ.**
   `schemas/assets.schema.json` типизирует `scenes` как
   `{"type":"array","items":{"type":"object"}}` при `additionalProperties: true`.
   Ни одного `enum` в схеме нет.
3. **Меняется ли serialization?** — **НЕТ.** Новое значение существующего
   строкового поля существующей структуры.
4. **Является ли `ProviderQuery.source` enum/validated vocabulary?** — **НЕТ.**
   Обычная `str` в dataclass ([query_adapter.py:95](../../src/assets/query_adapter.py:95)),
   без валидации.
5. **Нужны ли tolerant readers?** — **НЕТ.** Repo-wide поиск: **ноль** читателей
   констант `SOURCE_EXPLICIT` / `SOURCE_BRIEF_FIELDS` / `SOURCE_GLOSSARY` /
   `SOURCE_LATIN_TOKENS` / `SOURCE_SAME_LANGUAGE` вне самого `query_adapter.py`.
   Поле — write-only телеметрия.

**FACT.** 9B-1 не трогает `VisualBrief` и `schemas/` вообще. PLAN-1C′ до него
не требуется.

**INFERENCE.** Persisted-bytes tripwire (**schema, поле манифеста, layout файлов,
имя каталога проекта**) **не срабатывает**: новое *значение* в существующем
свободном непрочитываемом поле не является ни новым полем, ни схемой, ни
layout'ом. Остаточная оговорка честно: байты `assets_manifest.json` при этом
меняются, поэтому характеризационный тест 9B-0 обязан зафиксировать текущее
содержимое `query_plan` до правки.

### 10.3. Единственный содержательный пробел Proposal 2.1

**FACT.** `apps/news_to_short` имеет реальных callers за пределами собственного
пакета: `tests/test_apps_structure.py:10` и
`tests/test_fullscreen_voiceover_application_boundary.py:133`, плюс собственный
`README.md` и упоминания в docs.

**FACT.** `--input-mode` реализован как argparse `choices=["", "topic",
"article_url", "pasted_script", "script_file"]`
([content.py:94-100](../../src/content_creation/commands/content.py:94)).
Добавление значения меняет `--help` и поведение валидации документированного
флага.

**INFERENCE — противоречие внутри Proposal.** §5.5 назначает 9B-5 только
«+ PLAN-5 (`smoke`) + owner approval». Но 9B-5 измеримо пересекает ещё две
boundary из той же таблицы: «несколько owners в одном diff» (→ 6D) и
«destructive retirement реализации с callers» (→ 6E + reversible retirement).
При этом порядок §7.1 (`9B-0 → 9B-1 → **9B-5** → 9B-4 → 9B-2 → 9B-3`) ставит
9B-5 **раньше** 9B-2, для которого 6D/6E объявлены обязательными. Слайс с более
широкой risk boundary оказался раньше слайса с более узкой и без её gates.

**RECOMMENDATION — два варианта, рекомендуется первый:**

1. **Разделить 9B-5** на `9B-5a` (additive: новый input mode в каноническом CLI;
   public CLI + owner approval; ретайра нет) и `9B-5b` (retire
   `apps/news_to_short` после миграции callers; требует 6D + 6E + reversible
   retirement). Порядок сохраняется, критический путь не удлиняется, gates
   становятся честными.
2. Оставить 9B-5 цельным и добавить ему 6D + 6E + reversible retirement — но
   тогда 6A→6D→6E возвращаются в критический путь раньше, чем предполагает §5.2.

---

## 11. PLAN-5 gate verdict

**FACT — проверено исполнением, а не чтением:**

- targeted: `python -B -m unittest tests.test_visual_retrieval_repair
  tests.test_semantic_asset_selection` → **53 теста, 0.116 s, OK**;
- full: `python -B -m unittest discover -s tests -p "test_*.py"` — ровно эта
  команда стоит в `.github/workflows/offline-tests.yml` и записана как измеримый
  результат PLAN-4;
- smoke: `python -m ai_youtube --help` → exit 0; `capabilities --json` → exit 0;
  `applications list` → exit 0.

**FACT.** `tools/qa/` сегодня содержит **только** `check_agent_docs.py`. Runner'а
нет. `AGENTS.md` задаёт правило («targeted tests текущего изменения; full на
границе»), но не команду.

**INFERENCE.** Всё, что перечислено в `required verification` слайсов 9B-3
(`targeted + full`) и 9B-5 (`targeted + smoke + full`), **выполнимо сегодня** без
PLAN-5. PLAN-5 добавляет режим `fast`, единую командную модель и
воспроизводимость формулировки — это удобство и гигиена, а не защита.

**Verdict по под-слайсам:**

| Slice | PLAN-5 |
|---|---|
| 9B-0 | **PARALLEL** |
| 9B-1 | **PARALLEL** |
| 9B-5 | **PARALLEL** (Proposal говорит BLOCKER — исправить) |
| 9B-4 | **PARALLEL** |
| 9B-2 | **PARALLEL** |
| 9B-3 | **PARALLEL** (Proposal говорит BLOCKER — исправить) |

**Достаточен ли зелёный PLAN-4 как baseline protection?** — **ДА.** PLAN-4 даёт
воспроизводимый зелёный `full` на зафиксированном HEAD; сравнение «до/после»
targeted-прогоном возможно немедленно. PLAN-5 нужен для *единообразия* будущих
прогонов, а не для доказуемости конкретного diff'а.

**RECOMMENDATION.** В §5.4 заменить «**Обязателен до PLAN-9B-5** … и до
PLAN-9B-3» на «PARALLEL для всех под-слайсов 9B; `smoke`/`full` до PLAN-5
исполняются существующими командами, перечисленными в PLAN-4 и CI».

---

## 12. PLAN-6A/6D/6E gate verdict

Для каждого — какой **реальный** risk предотвращается и на каком **первом**
слайсе он появляется.

### PLAN-6A — governance R1–R12 в `AGENTS.md`

- **Реальный risk:** агент, буквально исполняющий `AGENTS.md`, действует по
  устаревшим правилам.
- **Где закрывается на самом деле:** **PLAN-1D-routing**. После 1D агент
  попадает в активный план, где Agent Autonomy Model уже записана целиком
  (раздел «Agent Autonomy Model», строки 245–377).
- **Первый 9B-слайс, где 6A даёт маржинальную защиту:** **ни один.** Собственные
  добавления 6A (проверка команд в `skills/*/SKILL.md`, расширение
  `CURRENT_DOCS`, cap `AGENTS.md`) обслуживают PLAN-7 и PLAN-12, не 9B.
- **Отдельная FACT-находка:** зависимость **6A → 6D декларативная, не
  техническая**. 6D-1 пишет `.claude/settings.json`, 6D-2 создаёт
  `tools/qa/check_task_scope.py`, 6D-3 правит `CLAUDE.md` — ни одному из них не
  требуется, чтобы R1–R12 уже лежали в `AGENTS.md`.
- **Verdict: PARALLEL** для всех 9B. Если 6D понадобится раньше 6A, порядок
  можно поменять без потери защиты — но это owner decision, здесь только
  фиксируется, что технического препятствия нет.

### PLAN-6D — scope control (`check_task_scope`)

- **Реальный risk:** diff молча выходит за allowed zones слайса.
- **Первое появление risk'а:** слайс, чей diff затрагивает **больше одного
  owner**. По матрице §10.1 это **9B-5** (в текущей редакции Proposal), иначе —
  **9B-2**. Для 9B-0 (один новый файл) и 9B-1 (один модуль + его тесты)
  allowlist тривиален и проверяется глазами.
- **Verdict: BLOCKER, начиная с первого multi-owner слайса.** Proposal называет
  9B-2 — **верно только если 9B-5 сделан additive-only** (§10.3, вариант 1).

### PLAN-6E — independent reviewer

- **Реальный risk:** удаление реализации, у которой есть callers, «под
  ответственность reviewer» — при отсутствующем reviewer. Плюс класс findings
  «unmet objective / premature stop».
- **Первое появление risk'а:** первый **destructive retirement реализации с
  callers**. Это **9B-5** (ретайр `apps/news_to_short`, 2 test-caller'а) либо
  **9B-2** (orca-hardcode + его тест), смотря по редакции.
- **Дополнительно обязателен до:** 9A (persisted bytes) и 9C (semantic decision
  path) — оба входят в список «когда reviewer обязателен» PLAN-6E.
- **Verdict: BLOCKER, начиная с первого destructive слайса.**

**Общий принцип, подтверждённый проверкой.** Ни 6D, ни 6E не становятся
обязательными «потому что полезны»: у обоих есть конкретная пересекаемая
boundary, и она пересекается позже 9B-1. Но и объявлять их необязательными
«потому что fix маленький» нельзя: 9B-5 и 9B-2 — не маленькие fix'ы, у них
multi-owner diff и удаление кода с callers.

---

## 13. PLAN-1C′ dependency verdict

**FACT — что такое 1C′ на самом деле.** Разрешённые зоны — «только
`docs/current/CLEANUP_REGISTRY.md`»; запрещено «production-код, tests, схемы,
config, любые move/delete/untrack». Required verification —
`tools.qa.check_agent_docs` + `git diff --check`.

- **Read-only ли он?** — **Нет, строго говоря.** Он **пишет** в
  `CLEANUP_REGISTRY.md`. Но он не меняет ни кода, ни схем, ни persisted
  артефактов, ни наблюдаемой поверхности.
- **Является ли это governance/canonical mutation?** — **ДА.**
  `CLEANUP_REGISTRY.md` — источник истины №6 в precedence активного плана.
- **Нужен ли reviewer по действующим правилам?** — **НЕТ.** Список PLAN-6E
  («persisted state, manifests, resume, providers, asset selection,
  semantic/Vision, rights/provenance, paid/TTS, rendering, package boundaries,
  shared contracts, compatibility retirement, runtime migration») описывает, что
  изменение **трогает в коде**. 1C′ не трогает ничего из перечисленного: он
  составляет инвентарь **про** эти области. Оговорка «для простой Markdown-правки
  не требуется» применима.
- **Влияет ли снятие зависимости на safety guarantees?** — **НЕТ**, и это
  ключевая проверка, которой Proposal не сделал. По предлагаемому порядку
  `9B-0 → 9B-1 → 9B-5 → 9B-4 → 9B-2 → 9B-3` и по предлагаемой цепочке
  `PLAN-9A ← PLAN-9B-2 + PLAN-1C′`, слайс **9B-2 сам требует 6E**. Значит 6E
  остаётся **транзитивно upstream** от 9A даже после снятия ребра `1C′ → 6E`.
  Гарантия сохраняется полностью.

**Verdict: CHANGE DEPENDENCY.**

Не просто REMOVE, потому что при простом удалении единственная запись о том, что
6E обязателен перед 9A, исчезает из явного вида и остаётся только транзитивной —
а транзитивные гарантии ломаются при следующем reorder.

**RECOMMENDATION:**

1. Снять `PLAN-1C′ зависимости: PLAN-6E`.
2. **Одновременно** записать явно: `PLAN-9A` и `PLAN-9C` требуют `PLAN-6E`
   (persisted bytes и semantic decision path — обе позиции уже есть в
   risk-boundary таблице §5.5, но 6E там указан только для 9B-2/9B-3).

План при этом не меняется этим аудитом — это рекомендация к правке.

---

## 14. Proposal 2.1 corrections

| # | PROPOSAL CLAIM | VERDICT | KEEP AS WRITTEN | CORRECT | REMOVE | NEEDS OWNER DECISION |
|---|---|---|---|---|---|---|
| 1 | §5.2 критический путь: `1D→2→3→4 → 9B-0 → 9B-1`, остальное параллельно | подтверждён | ✔ | | | |
| 2 | §5.3 перестановка `9A→9B` меняет ровно одно ребро | подтверждён | ✔ | | | |
| 3 | §5.4 PLAN-5 «обязателен до 9B-5 и 9B-3» | **опровергнут** | | **✔** PARALLEL для всех 9B | | |
| 4 | §5.4 PLAN-6A обязателен до 6D → до 9B-2 | частично | | ✔ пометить 6A→6D как ordering convention | | |
| 5 | §5.4 PLAN-6D обязателен до 9B-2 | подтверждён | ✔ | (+ 9B-5, если ретайр в нём) | | |
| 6 | §5.4 PLAN-6E обязателен до 9B-2 | подтверждён | ✔ | (+ 9B-5, если ретайр в нём) | | |
| 7 | §5.4 снять `1C′ → 6E` | подтверждён с уточнением | | **✔** CHANGE: снять + явно записать `9A`/`9C` требуют 6E | | ✔ |
| 8 | §5.5 risk-таблица: 9B-5 = PLAN-5 + owner approval | **неполон** | | **✔** добавить 6D + 6E + reversible retirement, **или** разделить 9B-5 | | ✔ |
| 9 | §7.1 9B-1 затрагивает только `query_adapter.py` | подтверждён | ✔ | | | |
| 10 | §7.1 порядок `9B-0→9B-1→9B-5→9B-4→9B-2→9B-3` | подтверждён при разделении 9B-5 | ✔ | | | ✔ |
| 11 | §7.3 «9C — не «включить флаг», а снять архитектурное ограничение» | **опровергнут** | | **✔** архитектурного запрета нет; 9C — producer→consumer wiring | | |
| 12 | §7.3 «`_selection_fingerprint` делает неизменность отбора инвариантом сервиса» | **опровергнут** | | **✔** защитная самопроверка, сработать не может | | |
| 13 | §10 «правила прав #1 и #2 уже разошлись» | частично | | **✔** сузить: rights-authority общий, расхождений ровно 2 | | |
| 14 | §10 «#1 допускает `RIGHTS_REFERENCE_ONLY`» | **опровергнут** | | | **✔** удалить (значение перезаписывается политикой) | |
| 15 | §10 «более строгая реализация — та, которую никто не вызывает» | **опровергнут** | | **✔** #1 строже на трёх осях финального гейта | | |
| 16 | §10 «три пути к локальной медиатеке» | частично | | **✔** один индекс, два matcher'а, три policy-обёртки; #1 и #3 делят функцию | | |
| 17 | §10 salvage diversity-резерва; четвёртый путь запрещён | подтверждён | ✔ | | | |
| 18 | §11 «пять расходящихся реестров, ни один не производный» | **опровергнут** | | **✔** разные факты; capabilities перекрывают таблицу | | |
| 19 | §11 owner конвергенции = PLAN-10B (fallback 13C) | **опровергнут** | | | **✔** снять; остаток → PLAN-10D | ✔ |
| 20 | §12 double orchestration = HIGH, owner PLAN-13B | частично | | **✔** MEDIUM; разделить контрактный дефект (ADR 0006) и конвергенцию (13B) | | ✔ |
| 21 | §12 предусловие «подтвердить resume/force/stop-stage callers» | подтверждён | ✔ | | | |
| 22 | §14.1 export truthfulness, owner PLAN-11 | факт да, owner нет | | **✔** PLAN-11 = evidence gate; implementation — bounded catalog slice | | ✔ |
| 23 | §14.2 «сегменты crf 23 → конкатенация crf 20 → субтитры crf 21» | **механизм неверен** | | **✔** конкатенация — `-c:v copy`; crf 20 = duration control | | |
| 24 | §14.2 owner PLAN-8 | частично | | **✔** PLAN-8 = roadmap; implementation owner — будущий renderer slice | | ✔ |
| 25 | §14.4 «`final_renderer.py` не трогать до отдельного слайса» | подтверждён | ✔ | | | |
| 26 | §15 HIGH-3 покрыт PLAN-1B/PLAN-13, новый этап не нужен | подтверждён | ✔ | | | |
| 27 | §16 Anime Factory — источник Video Repurposer, не ретайрить | подтверждён | ✔ | | | |
| 28 | §18 C34–C39, C42, C46–C49 | подтверждены | ✔ | | | |
| 29 | §18 C40 (LocalLibrary) | частично | | **✔** переформулировать по §5–6 | | |
| 30 | §18 C41 (пять реестров → PLAN-10B) | **опровергнут** | | **✔** переписать; owner PLAN-10D | | ✔ |
| 31 | §18 C43 (double orchestration → 13B) | частично | | **✔** разделить на две строки | | ✔ |
| 32 | §18 C44 (export → PLAN-11) | частично | | **✔** gate vs implementation | | ✔ |
| 33 | §18 C45 (FFmpeg → PLAN-8 roadmap) | частично | | **✔** roadmap vs implementation owner | | ✔ |
| 34 | §21 E-2 открыт | **закрыт** | | | **✔** удалить из открытых | |
| 35 | §21 E-5 открыт (PLAN-10B правильный owner?) | **закрыт отрицательно** | | | **✔** удалить из открытых | |
| 36 | §21 E-7 открыт (rights-семантика трёх путей) | **закрыт** | | | **✔** удалить: §6.2 даёт таблицу | |
| 37 | §19 «сильные foundations не переписывать» | подтверждён | ✔ | | | |
| 38 | §23 порядок действий | подтверждён | ✔ | | | |

**Новая строка, которой в Proposal нет:** fail-open на `review_required: True` в
локальной медиатеке (§6.4) — предлагаемый ID **C50**, класс `[HARD]` (rights),
owner — `apply_policy_to_candidate` / `with_policy_decision`, gate — отдельный
bounded slice, **не** смешивать с PLAN-10D.

---

## 15. Findings safe to canonicalize now

Доказаны фактом **и** механизмом; могут войти в canonical revision 2.1 без
дополнительной проверки:

1. **Критический путь `1D → 2 → 3 → 4 → 9B-0 → 9B-1`** и перестановка 9B↔9A.
2. **9B-1 — слайс без governance-gate.** E-2 закрыт: `ProviderQuery.source` не
   является schema-level изменением, tolerant reader не нужен,
   persisted-bytes tripwire не срабатывает (§10.2).
3. **PLAN-5 — PARALLEL для всех под-слайсов 9B** (проверено исполнением).
4. **PLAN-6D и PLAN-6E — BLOCKER первого multi-owner / первого destructive
   слайса**, с явным указанием, что это 9B-5 либо 9B-2 в зависимости от
   редакции.
5. **Снятие `1C′ → 6E` с одновременной явной записью `9A`/`9C` требуют 6E.**
6. **Порядок semantic/Vision** `provider-ready query → candidates → semantic →
   rank/select`; PLAN-9C — правильный owner.
7. **9C — producer→consumer wiring, а не снятие архитектурного запрета.**
8. **LocalLibrary: один индекс, один rights-authority, ровно два расхождения**
   (`provenance`, `review_required`), ноль расхождений в обратную сторону.
9. **Diversity-резерв — уникальное знание, подлежащее salvage** (PLAN-L0 →
   PLAN-10D); `duplicate_penalty` в `rank_local_assets` — мёртвый код.
10. **Provider registry: convergence не требуется**; остаток — декларация
    `local_library` (→ PLAN-10D), вестигиальный `DEFAULT_PROVIDER_ORDER`,
    осиротевший `unsplash`.
11. **Export targets: каталог — единственный outlier против трёх согласованных
    production-владельцев**; направление — truthful catalog.
12. **FFmpeg: три поколения при audio+ASS; конкатенация не кодирует; crf 20 —
    duration control с документированной причиной.**
13. **Double orchestration: расслоение зафиксировано ADR 0009; настоящий дефект
    — отключение ADR 0006 в explicit-режиме; повторных платных операций нет.**
14. **HIGH-3 и Anime Factory: owners существуют, prerequisite'ом не являются,
    риска случайного ретайра нет.**

---

## 16. Findings that must remain provisional

| # | Что | Почему не закрыто | Кто закрывает |
|---|---|---|---|
| P-1 | Величина ущерба от трёх lossy-поколений | Ни один аудит не рендерил. «Заметно хуже качество/медленнее» — INFERENCE, не измерение | будущий renderer slice: characterization + одно измерение |
| P-2 | Осуществимость слияния шагов 3+4 FFmpeg | Композиция `subtitles` + `tpad` + `-t` + `-c:a aac` выглядит корректной, но не исполнялась | тот же слайс |
| P-3 | Полный inventory topic-hardcodes (E-6) | repo-wide повторный поиск заданием запрещён; остаётся **PROVISIONAL** | PLAN-9B-2 |
| P-4 | Зелёность baseline (E-11) | full suite не запускался ни одним из трёх аудитов | PLAN-4 |
| P-5 | Public behavior `resume`/`force`/`stop-stage` при снятии double orchestration (E-9) | callers построчно не перечислены; §3.4 даёт только риск-профиль | PLAN-13B |
| P-6 | Совместимость CRITICAL-2 fix со старыми persisted проектами (E-12) | не проверялась | PLAN-9B-4 |
| P-7 | Возможность миграции всех пяти callers `semantic_selection/query_generator` (E-3) | семантика callers построчно не читалась | PLAN-9B-3 |
| P-8 | Метод provider-language adaptation (E-4) | OD-16 запрещает фиксировать заранее | PLAN-9B-1 |
| P-9 | Механизм subprocess network kill-switch и его owner (E-8) | вне scope этого аудита | владелец / PLAN-6B / PLAN-5 |
| P-10 | Нужно ли `local_library` вообще регистрировать как провайдера | зависит от исхода LocalLibrary-конвергенции; аудит установил только, что декларация и поведение разошлись | PLAN-10D |
| P-11 | Хостинг CRITICAL-2 (E-13) | продуктовое решение владельца | владелец |

---

## 17. Exact minimal patch to Proposal 2.1

Ревизия 2.2 **не нужна**. Требуется точечный патч proposal 2.1 из **девяти**
правок. Ни одна не меняет критический путь §5.2.

| # | Раздел Proposal | Правка | Класс |
|---|---|---|---|
| **P1** | §5.4, строка PLAN-5 | «Обязателен до PLAN-9B-5 … и до 9B-3» → «**PARALLEL для всех под-слайсов 9B**; `smoke`/`full` до PLAN-5 исполняются существующими командами PLAN-4 и CI» | исправление факта |
| **P2** | §5.5, строка 9B-5 · §8.3 | Добавить 6D + 6E + reversible retirement, **либо** (рекомендуется) разделить на `9B-5a` (additive input mode; public CLI + owner approval) и `9B-5b` (retire `apps/news_to_short`; 6D + 6E + reversible retirement) | закрытие пробела |
| **P3** | §5.4, строка PLAN-1C′ | «зависимость снять» → «зависимость снять **и одновременно явно записать, что PLAN-9A и PLAN-9C требуют PLAN-6E**» | усиление |
| **P4** | §7.3 | Удалить «9C — не «включить флаг», а снять архитектурное ограничение» и «неизменность отбора — инвариант сервиса». Заменить на: metadata-semantic слой **уже** владеет решением; `vision_tags` — живой ingestion seam (проба сменила выбранный asset); Vision-сервис пишет в review-манифест; `_selection_fingerprint` — самопроверка. **9C = producer→consumer wiring.** Добавить дефект отчётности `_semantic_visual_summary:997` | исправление механизма |
| **P5** | §10 · C40 | Удалить аргумент про `RIGHTS_REFERENCE_ONLY` и «строгая реализация никем не вызывается». Заменить на: один индекс, один `apply_policy_to_candidate`, **два** расхождения (`provenance`, `review_required`), ноль обратных; #1 и #3 делят `media_library.search_local_assets`. Добавить границу: user assets и project pool **не** входят в конвергенцию | сужение scope |
| **P6** | §11 · C41 | Заменить «пять расходящихся реестров → convergence → PLAN-10B» на: разные факты, не дубли; capabilities перекрывают таблицу (проверено); `PROVIDER_PRIORITY` фильтруется по availability. Остаток: декларация `local_library` → **PLAN-10D**; `DEFAULT_PROVIDER_ORDER` и `unsplash` — попутная уборка. **PLAN-10B и PLAN-13C как owners снять** | опровержение |
| **P7** | §12 · C43 | Severity HIGH → **MEDIUM**. Механизм: не «два owner'а», а отключение ADR 0006 в explicit-режиме (`pipeline.py:157`, `and not stage`), не покрытое тестами; расслоение зафиксировано ADR 0009. Разделить C43: точный контрактный дефект (owner — ADR 0006 / `src/news/pipeline.py`) и конвергенция «один владелец порядка стадий» (owner — PLAN-13B). Добавить FACT: повторных платных операций нет (три guard'а + 3 теста) | исправление механизма |
| **P8** | §14.1 · §14.2 · C44 · C45 | 14.1: PLAN-11 — **evidence gate**, implementation — bounded catalog slice; добавить FACT о трёх согласованных production-владельцах. 14.2: конкатенация — `-c:v copy`, **не** encode; crf 20 = duration control с документированной причиной; «single-pass тривиален» — снять; первый шаг = слияние шагов 3+4. PLAN-8 — roadmap-владелец, implementation owner — будущий renderer slice | исправление механизма + owner |
| **P9** | §18 · §21 | Добавить **C50** (fail-open на `review_required: True` в локальной медиатеке, класс `[HARD]`). Из §21 удалить **E-2**, **E-5**, **E-7** как закрытые; для E-2 записать результат: не schema-level, tolerant reader не нужен | добавление + закрытие |

---

## 18. Recommended next exact action

**Порядок не меняется относительно Proposal §23.** Меняется только содержание
шага 2.

1. **Владелец принимает решения**, к четырём вопросам §22.2 Proposal
   добавляются три из этого аудита:
   - **D-1.** 9B-5 разделяется на `9B-5a` / `9B-5b` (рекомендация: **да**) —
     или остаётся цельным и получает 6D + 6E.
   - **D-2.** C41 переписывается, PLAN-10B как owner provider-registry
     convergence снимается (рекомендация: **да**).
   - **D-3.** C43 разделяется на контрактный дефект и конвергенцию; severity
     HIGH → MEDIUM (рекомендация: **да**).

2. **Один docs-only slice «revision 2.1»**, allowed zones — ровно два файла:
   `docs/current/PROJECT_EXECUTION_PLAN.md` и
   `docs/current/CLEANUP_REGISTRY.md`. Содержание — таблица §20 Proposal
   **с применённым патчем §17 этого аудита**. Полного rewrite не выполнять.
   Required verification: `tools.qa.check_agent_docs`, `git diff --check`.
   Один commit, trailer `Plan-Step: PLAN-REV-2.1`.

3. **PLAN-1D-routing** — текущий `current_checkpoint`, не начат.

4. **PLAN-2 → PLAN-3 → PLAN-4.**

5. **PLAN-9B-0** (characterization; обязан зафиксировать текущее содержимое
   `query_plan` в persisted-манифесте — см. §10.2) и **PLAN-9B-1**.

Параллельно после зелёного PLAN-4: PLAN-5, PLAN-6A/6D/6E, PLAN-6B/6C, PLAN-7,
PLAN-8, PLAN-L\*, PLAN-1C′.

**Дополнительные deep-dive после этого аудита не требуются.** Все семь findings
имеют установленный факт и установленный механизм. Открытые вопросы §16 —
implementation-time проверки внутри своих слайсов, а не отдельные аудиты.

---

## 19. Обязательная сводная таблица

| Finding | Verdict | Fact established? | Mechanism established? | Correct owner established? | Safe to put into canonical revision 2.1? |
|---|---|---|---|---|---|
| **CRITICAL-4 double orchestration** | **B** | **да** — 4–7 вызовов, explicit-режим переисполняет всегда (проба) | **да** — `pipeline.py:157 and not stage`; ADR 0006 не действует; ADR 0009 фиксирует расслоение | **частично** — контрактный дефект → ADR 0006/`src/news/pipeline.py`; конвергенция → PLAN-13B | **да, с патчем P7** (severity MEDIUM, две registry-строки) |
| **CRITICAL-5 semantic/Vision** | **C** | **да** — проба сменила выбранный asset через `vision_tags` | **да** — два слоя; слой 1 решает, слой 2 пишет в review-манифест; fingerprint — самопроверка | **да** — PLAN-9C | **да, с патчем P4** |
| **LocalLibrary** | **C** | **да** — 10 synthetic случаев, 2 расхождения, 0 обратных | **да** — один индекс, один `apply_policy_to_candidate`, два matcher'а, #1 и #3 делят функцию | **да** — PLAN-10D (одна capability) + отдельно user assets / project pool | **да, с патчем P5** |
| **Provider registry duplication** | **D** | **да** — проба: `local_library` не попадает в `ordered_providers`, capabilities перекрывают таблицу | **да** — разные факты, фильтрация по availability задокументирована в коде | **да** — остаток к PLAN-10D; PLAN-10B/13C снять | **да, с патчем P6** |
| **Export targets** | **A** факт / **B** механизм | **да** — 5 объявлено, 3 создаётся, 0 читателей `supported_export_targets` | **да** — три production-владельца согласованно заявляют 3; каталог — outlier | **да** — PLAN-11 = gate; implementation = bounded catalog slice | **да, с патчем P8** |
| **FFmpeg encoding** | **C** | **да** — три поколения при audio+ASS; таблица по шагам | **да** — concat = `copy`; crf 20 = duration control | **частично** — PLAN-8 = roadmap; implementation owner создаётся позже | **да, с патчем P8**; величина ущерба остаётся INFERENCE (P-1) |
| **PLAN-5 boundary** | **D** (как blocker) | **да** — targeted/full/smoke исполнены сегодня | **да** — runner отсутствует, но все нужные команды существуют | **да** — PARALLEL для всех 9B | **да, патч P1** |
| **PLAN-6A boundary** | **C** | **да** — Autonomy Model действует из плана; 1D закрывает routing | **да** — 6A→6D зависимость декларативная | **да** — PARALLEL для 9B | **да, патч P4-адъяцентная пометка** |
| **PLAN-6D boundary** | **A** (с расширением) | **да** — multi-owner diff у 9B-2 и 9B-5 | **да** — allowlist vs `git diff --name-only` | **да** — BLOCKER первого multi-owner слайса | **да, патч P2** |
| **PLAN-6E boundary** | **A** (с расширением) | **да** — `apps/news_to_short` имеет 2 test-caller'а | **да** — destructive retirement с callers | **да** — BLOCKER первого destructive слайса; плюс 9A и 9C | **да, патчи P2 + P3** |
| **PLAN-1C′ dependency** | **C** | **да** — docs-only, пишет canonical registry | **да** — 6E остаётся upstream 9A транзитивно через 9B-2 | **да** — CHANGE, не REMOVE | **да, патч P3** |

---

## Проверки после создания отчёта

```
git status --short --branch     → до и после: только 4 untracked записи, без изменений tracked
git diff --check                → выполнено, вывод пуст, exit 0
git diff --stat                 → пусто (ни один tracked файл не изменён)
```

Изменён/создан только `docs/audits/SECONDARY_ARCHITECTURE_FINDINGS_DEEP_DIVE_2026-07-31.md`.
Production-код, tests, configs, schemas, canonical plan, `CLEANUP_REGISTRY.md`,
`AGENTS.md`, `START_HERE.md`, `CLAUDE.md` и proposal 2.1 **не изменялись**.
Уже существовавшие untracked файлы (включая `output/` и предыдущие
audit/proposal) не тронуты. Пробы созданы вне репозитория. PLAN-1D не начинался.
Cleanup не выполнялся. Legacy не удалялся. Сеть, downloads, платные API, Vision,
TTS и render не использовались. Commit не создавался.
