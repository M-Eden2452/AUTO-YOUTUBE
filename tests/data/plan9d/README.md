# PLAN-9D — данные offline-оценки

Evaluation-only. Ничего здесь не является production-контрактом, не включается в
runtime и не меняет поведение кода. Owner каталога — `tests/plan9d_ground_truth.py`
(контракты данных и измерение) и `tests/plan9d_corpus_builder.py` (сборка, курирование
и рендер пакета разметки). Локи — `tests/test_plan9d_ground_truth_baseline.py`
(generic harness) и `tests/test_plan9d_historical_evidence.py` (historical fixture).

**PLAN-9D НЕ закрыт.** PLAN-9D-A готовит основание, PLAN-9D-B снимает вход для
измерения; ни один из них ничего об улучшении decision path не утверждает.

## Два разных вида данных, и почему их нельзя смешивать

Owner direction 2026-08-08 переформулировал, на чём измеряется decision quality:
candidate pool говорит что-то о качестве **решения** только если сам pool
представляет текущее retrieval-поведение. Ни один runtime project на диске не
создан текущим query stack — самый новый файл в `projects/` датирован 2026-07-28,
тогда как PLAN-9B-1 (`141beae`) от 2026-08-01, а PLAN-9B-2/9B-3/9C — от 2026-08-07/08.

| `generation_class` | что это | кто создаёт | можно измерять |
|---|---|---|---|
| `historical_pre_query_fixes` | доказательство, что дефект retrieval был реальным | PLAN-9D-A | **нет** |
| `current_head_capture` | benchmark input, снятый с текущего production-пути | PLAN-9D-B | да |

Разделение — не соглашение об именах, а данные и гейт.
`assert_current_benchmark_input` — единственная точка, через которую что-либо
попадает в измерение; она отказывает historical-данным и **любому payload без
провенанса** (замороженный корпус до PLAN-9D-A провенанса не объявлял вовсе,
а собран был из `projects/`, поэтому «не объявлено» читается как historical).

## Файлы

| Файл | Что это |
|---|---|
| `historical_failure_evidence_v1.json` | Замороженное historical failure evidence: 7 кейсов, 31 кандидат, по одному representative frame на кандидата |
| `current_corpus_v1.json` | Замороженный current capture (PLAN-9D-B): 14 сцен, 1064 наблюдения, 1052 уникальных ассета, 64 кадра |
| `current_annotations_v1.json` | Слепая разметка владельца (PLAN-9D-D, 2026-08-12): 14 сцен, 14 `preferred_candidate`, 7 отметок `unacceptable`, привязана к `corpus_sha256` замороженного корпуса |
| `current_corpus_v2.json` | Двуязычный корпус (PLAN-9D-H, 2026-08-17): 11 сцен, 78 карточек, 55 с картинками. Собран офлайн из сохранённых кандидатов двух прогонов |
| `current_annotations_v2.json` | **Ещё не существует.** Слепая разметка владельца по v2; без неё `measure` на v2 отвечает `WAITING_FOR_OWNER_ANNOTATION`, и PLAN-9D-H не закрыт |

Изображения в репозиторий **не копируются**: это чужой лицензированный
provider-материал, а `projects/` намеренно untracked. Fixture несёт путь, размеры и
SHA256 кадра, и все тесты работают на машине, которая `projects/` никогда не видела.

## Current capture (PLAN-9D-B)

`current_corpus_v1.json` снят одним bounded прогоном текущего production-пути с
`capture_head_sha = d01914d77822057569a491216cfecf21b08f5d0c`. Owner выдал ровно два
сетевых класса — `provider_search` и `preview_download`; `asset_download` не
запрашивался и не использовался, потому что кадры берутся из ограниченного
preview-кэша (`config/visual_preview.json`, 5 МБ на превью).

Прогонялись production-владельцы в production-порядке, без единой собственной
строки запроса:

```
evaluation script (narration + author visual_brief)
  → src/news/visual_plan.build_visual_plan → content/visual_planning (brief, expansion ladder)
  → AssetManifestBuilder._prepare_scene    → analyze_scene, route_providers, build_scene_queries
  → _search_scene_providers                → providers/*, rank_provider_results, license_policy
  → _select_scene_asset                    → candidate_ranker (единственный владелец решения)
  → _prepare_visual_review                 → visual_preview + frame_sampling
```

`_download_and_complete` и всё, что после него, **не запускается** — это записано в
самом корпусе (`stages_not_run`).

Evaluation-константы корпуса заявлены, а не спрятаны: пустые `user_assets`, пустой
media index (локальная медиатека — другой источник и наполнена ровно теми
историческими проектами, которые PLAN-9D-A вывел из benchmark), пустые
`used_asset_ids`, `vision_tags` пусты (semantic backend остался в shipped default
`enabled:false`).

Владелец инструмента — `tests/plan9d_current_capture.py`. Две команды:

```
.\venv\Scripts\python.exe -B -m tests.plan9d_current_capture preflight --out %TEMP%\plan9d_preflight.json
.\venv\Scripts\python.exe -B -m tests.plan9d_current_capture finalize --corpus tests\data\plan9d\current_corpus_v1.json
```

`preflight` полностью offline: он строит планы и прогоняет tripwires (нет visual
brief, пустой semantic subject, потерянный в запросе субъект, вернувшийся
ретайренный broad-литерал, нарушение языкового контракта провайдера). При любом
срабатывании ни один provider-запрос не отправляется, и обойти tripwire
запросом, написанным руками, запрещено — иначе измеряется не система.

`capture` требует явного освобождения тестового socket guard
(`AI_YOUTUBE_ALLOW_LIVE_TESTS=1`) и сам отказывается работать под ним: прогон под
guard записал бы несуществующую аварию провайдеров. Повторный capture ради
лучшего результата запрещён; `finalize` пересчитывает только производные поля
(технические категории, статистику дублей) и идемпотентен.

### Что в корпусе есть и чего в нём нет

Есть: требование сцены, `visual_brief`, `visual_intents`, `semantic_scene`, план
запросов с провенансом каждой строки, фактические provider attempts, полный пул
кандидатов с правами и заявленными провайдером размерами, превью и кадры с SHA256
и perceptual hash, выбранный текущим владельцем решения кандидат.

Нет: owner-разметки (это PLAN-9D-D), Vision evidence (PLAN-9D-F), любых
агрегатов качества. **PLAN-9D-B ничего не утверждает о том, хороший retrieval или
плохой** — это вопрос PLAN-9D-C.

### Кадры и review

Кадры лежат в `projects/plan9d_current_capture_v1/` — отдельном evaluation-only
runtime namespace, который целиком под `/projects/` в `.gitignore` и не смешивается
ни с пользовательскими, ни с историческими проектами. Превью снимались только для
production-shortlist (5 кандидатов на сцену), поэтому визуально проверяемы 56
кандидатов из 1064; остальные представлены метаданными, ровно как их видит
владелец решения. Эти 56 карточек — **43 image и 13 video** кандидата, а 64
кадра распределены как 43 image + 21 video. Единицы разные и смешивать их
нельзя: 11 из 13 video-кандидатов несут один сэмплированный кадр, поэтому
метка на video-карточке — суждение об одном кадре, а не о движении. Clean clone получает корпус целиком, но без пикселей — это
честное ограничение, а не недосмотр: чужой лицензированный материал в Git не
копируется.

Пакет просмотра для PLAN-9D-C собирается локально и корпус не меняет:

```
.\venv\Scripts\python.exe -B -m tests.plan9d_corpus_builder review --corpus tests\data\plan9d\current_corpus_v1.json --out %TEMP%\plan9d_c_review.html
```

Он показывает требование сцены и кадры под обезличенными `C1..Cn` и намеренно не
показывает провайдера, заголовок, лицензию, оценки, выбор ranker и Vision. Полей
для заполнения в нём нет: разметка — отдельный шаг и отдельный пакет (`pack`).

### Что было раньше на этом месте

`corpus_v1.json` (16 сцен, 75 наблюдений, 107 кадров, 451 КБ) и его пустой шаблон
`annotations_v1.json` удалены в PLAN-9D-A. Точные байты остаются в Git:

```
git show 04fe035e6ac07dbbe4a80257c3ed9d971976457e:tests/data/plan9d/corpus_v1.json
```

Файл не переименован и не оставлен «на всякий случай» намеренно: он имел форму
benchmark-корпуса, и любой его возврат в дерево вернул бы ровно ту двусмысленность,
ради устранения которой шаг существует. Восстановленный из Git файл провенанса не
объявляет, поэтому benchmark-гейт его тоже отклонит.

## Корпус v2 — двуязычный (PLAN-9D-H)

Зачем он есть. v1 **не видит языка**: 14 английских субъектов из 14, пустой
`media_index`, 2 кириллические записи кандидатов из 1064. Поэтому языковая или
доказательная правка, принятая по v1, прошла бы при любом содержании правки
(`K12` языкового аудита 2026-08-16). v1 при этом **не заменяется и не
перегенерируется**: он остаётся замороженным со своим числом 4/14.

Материал — сохранённые кандидаты двух прогонов, которые сделал текущий стек
(решение владельца 2026-08-17):

| `run_id` | проект | HEAD прогона | что это было |
|---|---|---|---|
| `live_5` | `2026-08-15_solnechnaya-…-2` | `68c46cdd` | платный live-прогон, 5 сцен, verdict PARTIAL |
| `local_after_fix` | `2026-08-14_solnechnaya-…-3` | `a8549ff9` | локальная диагностика после правки токенизации |

Сборка полностью офлайн: оба проекта уже хранят по 10 записей на сцену
(5 `candidates` + 5 `rejected_candidates`). **Повторный прогон — платное сетевое
действие и в этот шаг не входит.**

```
.\venv\Scripts\python.exe -B -m tests.plan9d_corpus_builder build-v2
```

### Два класса корпуса

Поле `corpus_class` в схеме `plan9d-corpus-1`, объявляется у корпуса и может быть
переопределено у сцены. Отсутствие поля читается как `blind_annotation` — именно
этим v1 и является, поэтому он валидируется байт в байт как раньше.

| Класс | Что это | Что из него можно цитировать |
|---|---|---|
| `blind_annotation` («слепая разметка») | пул, который выдал настоящий прогон; ground truth — слепое предпочтение владельца | поведение системы в поле |
| `incident_analysis` («разбор инцидента») | те же настоящие кандидаты, требование написано рукой | поведение механизма, **не** поле |

Сцена класса `incident_analysis` обязана нести `incident_note` — что именно она
воспроизводит и что в ней написано рукой; без него она неотличима от снятой.
`measure` печатает класс у каждой сцены и считает `incident_scenes` отдельно от
итогов.

### Что в нём есть

| Величина | Значение |
|---|---|
| Сцены | 11 = 10 снятых + 1 инцидентная |
| Карточки | 78 = 73 (10 сцен, дедупликация по `asset_id`) + 5 инцидентных |
| Карточек с картинками | 55 (6 из снятых кадров, 20 из кэша превью, 29 из файлов локальной библиотеки) |
| Карточек без картинок | 23 — прогон их не предпросматривал |
| Записей с кириллицей в метаданных | 30 (в v1 — 2) |
| Сцен с русским субъектом и русским запретом | 1 (инцидентная) |

Записей в манифестах 100, а уникальных `asset_id` — 73: повторы есть и внутри
`candidates`, и между двумя списками. По сценам уникальных 10·7·7·9·7 в LIVE-5 и
7·5·7·5·9 в LOCAL.

Провайдер читается **только** из `selection_decision.provider`. Префикс
`asset_id` провайдером не является: `pexels_32386564` — запись
`local_library`, и внешнее ревью построило на префиксе целую рекомендацию.

### Чего он не может

- Это **хвост сохранённой десятки, а не пул**: в LIVE-5 было 234 попытки к
  провайдерам и 1303 результата, а в манифесте осталось 100 записей. Вопрос
  «правильный кандидат был на сороковом месте» этим корпусом не проверяется, и
  офлайн-материала глубже нет — только новый платный прогон.
- Пиксели есть там, где их оставил прогон. 23 карточки без картинки остаются в
  измеряемом пуле (ранжировщик их видел) и не попадают на доску; доска пишет
  их число прямо на странице.
- Видео показано кадрами: метка на такой карточке — суждение о кадрах, а не о
  движении.
- Запретов ни один прогон не объявлял (`must_not_include` пуст во всех 10
  сценах), поэтому случай с запретом — инцидентная сцена.

### Доска слепой разметки

Та же доска, что у v1 — `render_pack`; второй не создаётся. Для v2 обязателен
каталог слепых медиа: файл локальной библиотеки называется
`pexels_video_solar_panel_assembly_line_factory_conveyor_…mp4`, и ссылка на него
положила бы ответ в `src` той самой карточки, которую владелец судит. Имена в
каталоге собираются только из blind id; для клипов кадры снимает `ffmpeg`
локально.

```
.\venv\Scripts\python.exe -B -m tests.plan9d_corpus_builder pack ^
  --corpus tests\data\plan9d\current_corpus_v2.json ^
  --out %TEMP%\plan9d_h\plan9d_h_pack.html ^
  --media-dir %TEMP%\plan9d_h\media
```

Кнопка сохраняет `current_annotations_v2.json` — имя берётся из самого корпуса
(`annotations_filename`), а не пишется вторым написанием.

### Изменившиеся победители — поимённо

```
.\venv\Scripts\python.exe -B -m tests.plan9d_ground_truth measure --json --out %TEMP%\before.json
.\venv\Scripts\python.exe -B -m tests.plan9d_ground_truth measure --baseline %TEMP%\before.json
```

Приёмка «ноль изменившихся победителей» перестала быть сверкой двух таблиц
глазами: `--baseline` печатает `сцена: был X → стал Y` и отказывается сравнивать
измерения разных корпусов.

## Historical failure evidence

Курируется, а не сэмплируется. Несколько сцен демонстрируют один и тот же дефект —
пять независимых проектов обслужил один и тот же ретайренный broad-литерал — и
сохранение всех превратило бы fixture в архив runtime, а не в доказательство.
Сохранены три из них, потому что **повтор здесь и есть находка**, плюс по одному
кейсу на каждый оставшийся отдельный дефект.

| case_id | failure modes | что доказывает |
|---|---|---|
| `gecko_subject_free_broad_query` | `subject_absent_from_provider_query`, `retired_broad_query_literal`, `shared_generic_candidate_pool` | visual brief отсутствовал; всем провайдерам ушёл литерал `nature science wildlife observation` (registry C36) |
| `hummingbird_subject_free_broad_query` | те же | другой проект, другой субъект, тот же литерал и тот же pool |
| `penguin_subject_free_broad_query` | те же | третий независимый проект; пересечение pools — 4 asset id |
| `cyrillic_query_to_latin_provider` | `non_provider_language_query` | русский запрос ушёл в англоязычные индексы как есть (CRITICAL-1 до PLAN-9B-1) |
| `subject_lost_between_primary_query_and_provider` | `degenerate_single_token_query`, `subject_lost_after_primary_query`, `subject_absent_from_provider_query` | `primary_query` содержал субъект, а провайдеров спросили одним словом `close` |
| `glossary_substitute_for_extracted_stopwords` | `garbage_subject_extraction`, `degenerate_single_token_query` | subject/action извлеклись как русские служебные слова, глоссарий заменил их одним английским токеном |
| `orca_topic_query_hardcode` | `retired_topic_query_hardcode`, `degenerate_single_token_query`, `mislabelled_query_language` | `visual_brief.provider_queries` дословно от ретайренного one-topic hardcode (registry C35), включая немецкий wikimedia-запрос, помеченный как `en` |

Каждая сцена исходного корпуса либо сохранена, либо перечислена в
`dropped_source_scenes` с причиной. Тихого усечения нет: 7 сохранённых + 9
отброшенных = 16 сцен `corpus_v1.json`.

Что fixture **не** содержит: `vision_tags`, score, `support_status`, любые
aggregate-числа и любую owner-разметку. Их отсутствие залочено тестами — иначе
рядом с historical данными легко появился бы «результат качества».

### Политика кадров

Хранится **один** representative frame на кандидата (путь + SHA256 + размеры),
а не 1–5, как в старом корпусе: 107 путей сжаты до 31. Причина именно в
доказательности, а не в экономии. Для сохранённых кейсов провайдерские `tags`
часто оказываются эхом самого запроса (`tags_source` пуст) — то есть у metadata-гейта
не было ничего своего, и единственная content-проверка «в pool нет заявленного
субъекта» делается глазами. Но сам заявленный дефект — «субъект не дошёл до
провайдера» — доказывается из `historical_provider_attempts` и без единого пикселя;
кадр остаётся provenance-якорем, а не носителем доказательства.

## Остаточная зависимость от `projects/`

`historical_runtime_paths()` возвращает точный список. Сейчас это 45 путей:
14 манифестов (по два на кейс) и 31 кадр — суммарно порядка 1 МБ. Всё остальное
под `projects/` (около 7.3 ГБ) PLAN-9D больше не нужно.

Оговорка «Safety boundaries» в `PROJECT_EXECUTION_PLAN.md` защищает кадры
замороженного корпуса, пока PLAN-9D открыт, и снимается на шаге (4) cleanup
sequencing. PLAN-9D-A ничего не удаляет из `projects/` — это отдельный
owner-authorized slice.

## Порядок работы

1. **PLAN-9D-A (сделано).** Historical evidence курировано и заморожено.
2. **PLAN-9D-B (сделано).** Bounded capture текущего retrieval снят и заморожен
   в `current_corpus_v1.json` своим `corpus_sha256`. PLAN-9D в целом **не закрыт**.
3. **PLAN-9D-C (сделано).** Retrieval quality gate на замороженном current
   corpus — владелец `tests/plan9d_retrieval_gate.py`, лок
   `tests/test_plan9d_retrieval_gate.py`, отчёт печатается командой
   `.\venv\Scripts\python.exe -B -m tests.plan9d_retrieval_gate`. Gate прошёл:
   субъект сцены доходит до провайдера и возвращается в pool во всех 14 сценах.
   Про качество *решения* он говорит обратное — подробности и две owner
   decision перед разметкой в секции PLAN-9D-C
   `docs/current/PROJECT_EXECUTION_PLAN.md`. Корпус этим шагом не менялся.
4. **PLAN-9D-D (сделано 2026-08-12).** Слепая разметка владельцем — **один
   раз**, по current corpus:

   ```
   .\venv\Scripts\python.exe -B -m tests.plan9d_corpus_builder pack --corpus tests\data\plan9d\current_corpus_v1.json --out %TEMP%\plan9d_pack.html
   ```

   Пакет одноразовый, пишется вне репозитория. Кнопка сохраняет
   `current_annotations_v1.json` — имя берётся из `CURRENT_ANNOTATIONS_PATH`, а
   не пишется вторым написанием: они однажды разъехались, и законченный слепой
   проход пролежал непрочитанным рядом с harness, который продолжал отвечать
   `WAITING_FOR_OWNER_ANNOTATION`. Пересборка корпуса после разметки запрещена:
   изменится `corpus_sha256`, и harness откажется считать разметку валидной.
5. **PLAN-9D-E → PLAN-9D-G.** Metadata-only baseline, real Vision evidence, offline A/B.
6. **PLAN-9D-H (в работе, 2026-08-17).** Двуязычный корпус v2 и доска слепой
   разметки собраны; разметка владельца ещё не сделана, поэтому шаг **не
   закрыт**. Раздел «Корпус v2» выше.

Пока разметки нет, `evaluate_arm` возвращает `WAITING_FOR_OWNER_ANNOTATION` и не
измеряет ничего. Разметка от имени владельца не заполняется и после заморозки не
редактируется.

## Что видит и чего не видит аннотатор

Видит: текст сцены, заявленные subject / action / environment / location,
`must_include`, `must_not_include`, заявленный контекст и противоречие, целевой
кадр и длительность, а также сами изображения кандидатов.

Не видит: провайдера, заголовок, описание, теги, лицензию, любые score,
`metadata_rank`, результат ranker, результат Vision, выбранный системой кандидат,
категории корпуса и исходный порядок кандидатов. Идентификаторы обезличены:
`C1..Cn` назначаются по `sha256(salt ‖ scene_key ‖ asset_id)` — детерминированно и
без связи с ранжированием.

Аннотатор **не** оценивает права, лицензионную политику, качество метаданных,
надёжность провайдера, технические размеры и внутренние score. Это решает система.

## Как считается baseline

`run_metadata_baseline` вызывает production-путь как есть:
`select_best_with_video` → `select_best_candidate`. Второго selector нет, своего
score нет, confidence не выдумывается. Кандидаты подаются без `vision_tags` —
это metadata-only ветка. Первым делом вызывается тот же provenance-гейт: на
historical pool решающий владелец не запускается вообще.

Заявленные evaluation-константы:

- `used_asset_ids` пуст: каждая сцена оценивается независимо;
- кандидаты **хранятся** в blind-порядке, но **подаются** в порядке манифеста,
  потому что ранжирование — стабильная сортировка и порядок входа разрешает
  ничьи. Подача в blind-порядке однажды сделала так, что хэш решал каждую ничью;
  это исправлено и залочено тестом;
- framing-гейт судит **заявленные provider-размеры** из записи кандидата, а не
  разрешение локального превью. Кандидаты без объявленных размеров дают
  `framing_unknown` (не hard reject). Production-гейт не отключался.

## Требования к current corpus — где они проверяются

Прежняя версия локов проверяла на historical корпусе размер, покрытие технических
категорий, наличие `regression_capable` сцен, расхождение заявленных и превью-размеров
и checksum каждого кадра. Это требования к **benchmark**-корпусу, и проверять их на
синтетике бессмысленно, поэтому они были перенесены в условия приёмки PLAN-9D-B и
PLAN-9D-C. На снятых данных они проверены — `tests/test_plan9d_current_capture.py`,
класс `DerivedFieldTests`:

- размер: 14 сцен, 1064 наблюдения, ни одна сцена не исключена по нехватке кандидатов;
- покрытие: встретились **все 13** технических категорий словаря, включая
  `regression_capable` (12 сцен) — без них A/B мог бы выглядеть только нейтрально
  или лучше;
- checksum: SHA256 есть у каждого из 64 кадров;
- расхождение заявленных и превью-размеров записано как измеренная величина.
  Факт, а не оценка: сравнимы всего 2 пары из 1064 — превью снимается только для
  production-shortlist, а его запись редко несёт собственные размеры. Framing-гейт
  как и прежде читает **заявленные** размеры кандидата.

Пробел прошлого корпуса закрылся сам: категория `non_real_footage_risk`, которой
не было ни в одной из 88 пригодных исторических сцен, в current capture встретилась
в 11 сценах из 14. Синтезировать такую сцену по-прежнему запрещено — она пришла из
реальных provider-метаданных.

## Готовность к будущим режимам Review и Auto

Оба будущих режима могут опираться на **один** decision owner. Разница — в
approval/escalation policy поверх уже существующих выходов, а не в ранжировании.
Здесь ничего из этого не реализовано.

Уже существующие сигналы, пригодные для такой политики: выбранный кандидат либо
его отсутствие; `blocking_reject_reasons` и `advisory_reject_reasons`;
`support_status` и `support_requirements`; `slot_verdict`; `rights_status`,
`allowed_for_render`, `review_required`; `semantic_match_status`,
`semantic_evidence`, `undecidable_fields`, `must_include_unverifiable`,
`metadata_status`; `framing_status`, `duration_status`; на уровне проекта —
`resolution_status`, `missing_scenes`, `completion`, `publish_ready`.

Чего не хватает — зафиксировано как **отсутствующий контракт, не добавлено**:

1. **Abstain и fallback неразличимы одним полем.** Когда decision owner
   возвращает `None`, оркестрация подставляет сгенерированный backdrop, и «нет
   приемлемого кандидата» отличается от «закрыто fallback'ом» только по
   `selected_by`. Явного scene-level поля нет.
2. **Нет поля disposition.** `support_status` описывает достаточность evidence, а
   не принятое решение; «принято автоматически» и «отправлено на review» нигде не
   записываются.
3. **Нет продуктового порога auto-safe.** Чтение `full_support` как «можно
   принимать автоматически» — соглашение этого benchmark (`AUTO_SAFE_SUPPORT`), а
   не объявленный контракт.
4. **Нет записи действия ревьюера** (принял / заменил / оставил нерешённым),
   с которой будущий benchmark мог бы сравнивать autonomous-режим.

Ни один режим не имеет права обходить rights blockers, `must_avoid`, заявленные
конфликты, misleading-content гейты, технические hard reject и явные ограничения
пользователя. Benchmark считает нарушение любого из них **blocking regression**.

## Что запрещено этому каталогу

Historical evidence не измеряется и не размечается. Mock, scripted и любой
fixture-backend не могут служить доказательством визуального качества —
`assert_admissible_evidence` отказывает такому arm'у до любого измерения.
Разметка от имени владельца не заполняется.
