---
status: historical
---

# Visual retrieval after Q2.1

> **HISTORICAL — самый полезный и поэтому самый опасный retrieval-документ.**
> Карта верна в основном, но отстала в трёх местах: (1) не знает
> `semantic_selection/media_policy.py` — единого owner решения «какой медиа-вид и
> какой кандидат»; (2) утверждение «платный Vision не подключён» устарело с
> **PLAN-9C** — `semantic_visual_service` влияет на отбор **до** скачивания;
> (3) примеры команд неканонические, канонический вход — `python -m ai_youtube`.
> Current truth: [SYSTEM_MAP.md](../../current/SYSTEM_MAP.md) и код
> `src/news/asset_manifest_builder.py`; индекс каталога —
> [README.md](../README.md).

Карта того, как сцена превращается в материал, и какие правила теперь этим управляют.
Этап Q2.1 — ремонтный: он не добавил ни второго asset pipeline, ни второго планировщика,
а починил то, что сломал реальный прогон Real Shorts E2E-A (8 сцен, 8 скачанных файлов,
0 подходящих).

## Путь сцены

```
SceneVisualPlan (+ visual_brief)
  → SceneAssetStrategy        src/assets/scene_strategy.py
  → provider-specific queries src/assets/query_adapter.py
  → provider search           src/providers/*
  → normalized candidates     src/assets/models.py (AssetCandidate)
  → semantic relevance gate   src/assets/semantic_selection/candidate_ranker.py
  → technical + duration gate тот же ranker
  → rights gate               src/assets/license_policy.py
  → selection | unresolved    src/news/asset_manager.py
```

Главное правило: **сцена без подходящего материала остаётся `unresolved`**. Ветка, которая
скачивала `candidates[0]`, когда отбор ничего не выбрал, удалена — она обесценивала любой
отказ.

## Provider routing matrix

Источник: `src/assets/scene_strategy.py::PROVIDER_PRIORITY`.
Провайдер, не зарегистрированный в текущем запуске, просто пропускается.

| source class | порядок провайдеров |
|---|---|
| `exact_location` | local_library → nasa_images → wikimedia → internet_archive → pexels → pixabay |
| `satellite_or_earth_observation` | local_library → nasa_images → wikimedia → internet_archive → pexels → pixabay |
| `scientific_equipment` | local_library → wikimedia → internet_archive → nasa_images → pexels → pixabay |
| `specific_object` | local_library → wikimedia → internet_archive → nasa_images → pexels → pixabay |
| `research_activity` | local_library → wikimedia → internet_archive → nasa_images → pexels → pixabay |
| `archive` | local_library → internet_archive → wikimedia → nasa_images → pexels → pixabay |
| `generic_broll` | local_library → **pexels → pixabay** → wikimedia → internet_archive → nasa_images |
| `data_infographic` | только local_library; сток **не опрашивается вообще** |
| `manual_required` | пусто — нужен ручной выбор |

Класс сцены берётся из `visual_brief.source_class`, если автор его указал; иначе выводится
из типа медиа и небольшого двуязычного словаря; при отсутствии признаков — `generic_broll`,
никогда не «уверенная догадка». `local_library` всегда первый там, где он есть: его права
уже урегулированы, и это свойство библиотеки, а не сцены.

Классы `exact_location`, `satellite`, `scientific_equipment`, `specific_object` помечены
`requires_provider_metadata`: кандидат без метаданных провайдера в них отклоняется.

## Правила языка запроса

Источник: `src/assets/query_adapter.py`.

- Все удалённые провайдеры объявлены **англоязычными** (`query_languages = ["en"]`).
  `local_library` и тестовая заглушка `fake` принимают `["en", "ru"]`.
- Русский запрос в англоязычный провайдер **не отправляется**. В подтверждённом прогоне
  Wikimedia и NASA получили по 16 русских запросов и вернули 0 результатов.
- Английский запрос строится по убыванию надёжности:
  1. `visual_brief.provider_queries` — по имени провайдера или по ключу `en`;
  2. английские поля брифа (`subject` / `action` / `place` / `exact_entities`);
  3. небольшой детерминированный глоссарий (только лексика кадра и устойчивые термины);
  4. латинские токены, уже присутствующие в тексте (`PET`, `McMurdo`).
- Если ничего из этого не даёт запрос — сцена помечается `query_translation_required`,
  и запрос **не отправляется**. Переводчика здесь нет и он не выдумывается: угаданный
  перевод молча подменяет предмет ролика.
- План, объявленный русским, но фактически содержащий латинские запросы, уходит
  в англоязычный провайдер как есть.
- `shot_type` — модификатор, а не запрос: «action» и «payoff» сами по себе запросом не
  становятся.

## Правила metadata score

Источник: `src/assets/semantic_selection/candidate_ranker.py`.

- Текст-доказательство собирается **только** из метаданных провайдера: `title`,
  `description`, `categories`, `depicts`, `location`, плюс `tags`, если провайдер их
  действительно вернул.
- `search_query` исключён безусловно. Поле, значение которого целиком совпадает с
  запросом, отбрасывается — но настоящий заголовок, случайно содержащий искомые слова,
  сохраняется как доказательство.
- `tags_source` на `AssetCandidate` различает `provider` и `query_derived`. Теги,
  синтезированные из запроса, доказательством не считаются.
- Отсутствие метаданных даёт `metadata_status = "unavailable"` и `metadata_score = 0`,
  а не 100. Раньше все 40 кандидатов прогона получали ровно 100.0.
- Оценки хранятся раздельно и не сливаются в одно число:
  `semantic_score`, `metadata_score` + `metadata_status`, `technical_score`,
  `rights_status`, `duration_status`, `provider_confidence`, `semantic_match_status`.
- `semantic_match_status`: `matched` только при наличии доказательств;
  `unverified` — если проверить невозможно; `mismatched` — если проверено и не совпало.
- Поле, чьи термины написаны письменностью, которой не может быть в метаданных
  (русский subject против английского заголовка), считается **неразрешимым**, а не
  несовпавшим: оно исключается из средней оценки, а его вес перераспределяется.
  Отсутствие метаданных при этом неразрешимостью **не** считается.
- Если все явные `must_include` автора выполнены на настоящих метаданных, порог
  `exact_subject` (75) не применяется: авторское требование сильнее оценки совпадения фраз.
- `must_avoid` — жёсткий отказ, а не штраф. Токенизация работает и с кириллицей
  (прежняя `[a-z0-9]+` молча выбрасывала русские термины).

## Duration suitability

Проверяется до выбора, результат сохраняется всегда:
`required_sec`, `candidate_sec`, `deficit_sec`, `tolerance_sec` (0.35 с), `adaptation`,
`status` (`sufficient` | `too_short` | `not_applicable` | `unknown` | `not_checked`).
Клип короче сцены больше не выбирается молча — в прогоне `scene_006` получила файл
6.54 с на сцену 7.92 с, и ни одна проверка не возразила. Для изображения проверка не
применяется (`not_applicable`).

## Generated infographic

`src/assets/generated_infographic.py` — статичный вертикальный SVG 1080×1920,
детерминированный, без анимации и без новых шрифтов (только generic-семейства).
Показывает заголовок, крупное число, подпись, сетку точек и двухслойный разрез.
Права: `project_generated` / `user_owned`, атрибуция не требуется, provenance
`generated_by_project`, SHA-256 считается по содержимому.

**Ограничение, зафиксированное намеренно:** значения берутся **только** из
`visual_brief.infographic`. Ничего не выводится из narration — график, построенный по
числам, которые модуль домыслил сам, был бы утверждением, которого сценарий не делал.
Без спецификации сцена честно остаётся `unresolved`.

## Visual brief

`src/content/visual_planning/brief.py`. Additive: сценарий без брифа ведёт себя как прежде.

**Вход (этап Q2.2A).** Единственный поддерживаемый способ — один JSON-файл:

```bash
./venv/Scripts/python.exe -m src.content_creation.cli create ... --visual-brief briefs.json
```

Формат: объект «сцена → бриф», ключ — номер сцены (`"1"`) или `scene_id` (`"scene_001"`).
Тот же флаг есть у офлайн-проверки `script generate --visual-brief`, которая ничего не пишет
без `--out` и печатает применённый бриф по каждой сцене.

Путь: `--visual-brief` → `ContentCreationRequest.visual_briefs` → `create_news_to_short_job`
→ `NewsJob.visual_briefs` (в `job.json`) → `build_script_request` → `ScriptRequest.visual_briefs`
→ `user_supplied` → `script.json` → `parse_brief` → visual plan → `semantic` + `source_class`
+ `provider_queries` + `infographic`. Ручное редактирование runtime-файлов не требуется.

Файл проверяется до запуска: `validate_visual_brief_file` отвечает понятным сообщением на
отсутствие файла, не-UTF-8, неверный JSON, не-объект и сцену, чей бриф не объект.

Поля: `visual_description`, `subject`, `action`, `place` (алиас `location`),
`exact_entities`, `must_include`, `must_avoid`, `shot_type`, `media_types`,
`source_class`, `provider_queries`, `fallback_visual`, `infographic`, `notes`.
Неизвестные ключи игнорируются и не отменяют известных.

- Живёт в `ScriptScene.visual_brief` → `script.json` → применяется к плану в
  `src.content.visual_planning.engine` → попадает в существующий блок `semantic`.
- Передаётся в `ScriptRequest.visual_briefs` по номеру сцены или по `scene_id`.
  Сегодня его сохраняет только `user_supplied` — единственный провайдер, который не
  меняет границы авторских сцен.
- **Никогда не озвучивается**: стадия voice читает только `narration`.
- Каждое поле заменяет только себя; бриф с subject, но без action, action не стирает.

## Жёсткие гейты выбора (этап Q2.2A)

Кандидат может быть выбран автоматически, только если проверены **требования** сцены.

1. **Semantic.** Отказ, если провайдер не сказал об ассете ничего (`metadata_status`
   `unavailable`/`query_derived_only`) **или** хотя бы один термин `must_include` написан
   письменностью, которой не может быть в его метаданных. Причина —
   `semantic_unverified:<термины>`. Именно так снимок Марса попадал в сцену про проценты:
   он выбирался, хотя его собственная запись говорила, что требование не проверено.
   Побочное непроверяемое поле (автоизвлечённый глагол, движение камеры, которое сток
   не подписывает) фиксируется в `semantic_match_status`, но выбор не блокирует — иначе
   отказ получал бы материал, все заявленные требования которого выполнены.
2. **Framing.** Кадр обрезается до `9:16`, и если оставшаяся ширина меньше
   `MIN_SHORT_EDGE_PX = 540` (то есть растяжение больше 2×), кандидат отклоняется:
   `framing_unusable:<ШxВ>`. `1280×720` даёт полосу 405 px и отклоняется; `1920×1080`
   даёт 607 px и проходит. Вердикт `framing_check` пишется всегда, даже когда не решает.

Оба гейта — отказы, а не баллы: ни релевантность, ни техническое качество их не перевешивают.

## Semantic slots и support statuses (этап Q2.2A-2)

Источники: `src/assets/semantic_selection/decision.py` (контракт),
`src/assets/semantic_selection/evidence.py` (что вообще считается доказательством).

Ретест Q2.1 дал три ложных принятия. Первое (снимок Марса под статистику) закрыл
Q2.2A изоляцией `data_infographic`. Два других прошли **честно по метаданным**:
пресс-день миссии на Марс содержал «mass spectrometer», описание раскола айсберга —
«Antarctica». Это не ошибка оценки: одно усреднённое число не может сказать, **какое
именно** требование сцены выполнено. Отсюда slot.

### Слоты

Слот — это одно требование сцены. Строятся только из того, что автор реально написал:

| слот | источник | матчинг |
|---|---|---|
| `subject` | `semantic.subject` / `visual_brief.subject` | морфологически мягкий |
| `action` | `semantic.action` / `visual_brief.action` | морфологически мягкий |
| `location` | `semantic.location` / `visual_brief.place` | морфологически мягкий |
| `context` | `semantic.context` / `visual_brief.context` | морфологически мягкий |
| `requirement:<term>` | `must_include` (включая `exact_entities`) | **буквальный** |
| `conflicting_context:<term>` | `visual_brief.conflicting_context` | морфологически мягкий |
| `must_avoid:<term>` | `must_not_include` | буквальный |

Статус слота: `matched` (≥99 % фразы), `partial` (≥50 %), `missing` (<50 %),
`undecidable` (нет метаданных либо термин написан письменностью, которой в них быть
не может), `conflicting`.

Мягкий матчинг — это допуск на словоформу, а не догадка: совпадение засчитывается,
если одно слово является префиксом другого и длина ≥5 символов. `Antarctica`/`antarctic`
совпадают, `sampling`/`samples` — нет. Авторское `must_include` проверяется **буквально**:
имя, которое обязано дойти до запроса, обязано дойти и до доказательства.

### Какие слоты обязательны

`REQUIRED_SLOT_KINDS` в `decision.py`; слот становится обязательным, только если сцена
его реально указала:

| source class | обязательные слоты |
|---|---|
| `exact_location` | location, subject, action, context |
| `satellite_or_earth_observation` | location, subject |
| `scientific_equipment` | subject |
| `specific_object` | subject |
| `research_activity` | subject, action, location |
| `archive` | subject |
| `generic_broll` | нет |
| `data_infographic` | нет (только сгенерированный ассет) |
| класс не определён | нет |

`must_include` обязателен всегда, независимо от класса.

`slot_verdict`: `conflicting` → `unverified` → `incomplete` (нет обязательного) →
`partial` (нет необязательного) → `complete`.

### Отказ против неполноты

- **Обязательный слот `missing`** (в метаданных нет ничего) + класс из
  `EXACTING_CLASSES` → отказ `required_slot_missing:<слоты>`. Это айсберг: сцена просила
  станцию и атмосферный перенос, клип совпал ровно одним словом про континент.
- **Обязательный слот `partial`** (часть фразы есть) → отказа нет, но полного совпадения
  тоже нет. `barren polar valley landscape` против заголовка `barren antarctic dry valley
  rocks` — это неточная формулировка, а не отсутствие предмета.
- **Континент вместо места**: `Antarctica` не подтверждает `McMurdo Dry Valleys`. Слот
  получает `missing` и пометку `broader_context_only`.

### Conflicting context

Противоречие должно быть **заявлено автором** и найдено в метаданных дословно. Никакой
базы знаний, никакого захардкоженного «Марса»: сцена лаборатории пишет
`conflicting_context: ["mars mission", "spacecraft", "planetary mission"]`, и тогда
NASA-описание пресс-дня даёт `conflicting` → отказ `conflicting_context:<термины>` и
`support_status = manual_confirmation_required` (человек может подтвердить).
`must_avoid` остаётся жёстким отказом навсегда — это разные вещи.

Отсутствие упоминания места **не** является противоречием: нейтральный снимок реального
масс-спектрометра проходит, даже если Антарктида в метаданных не упомянута.

### Support statuses

Один enum `support_status` на кандидата, приоритет сверху вниз:

| статус | когда |
|---|---|
| `unsupported` | `must_avoid`, semantic mismatch, жёсткий технический отказ, поиск под `data_infographic` |
| `unverified` | проверить нечем |
| `relevant_but_rights_blocked` | смысл сходится, права нет |
| `manual_confirmation_required` | conflicting context **или** полное совпадение с неразрешённым кропом |
| `partial_support` | часть указанного в кадре нет |
| `full_support` | всё подтверждено, права чистые, кроп не нужен |

Отдельно — `support_requirements` (что осталось сделать, а не альтернативный статус):
`needs_additional_asset`, `needs_multi_asset` (не хватает ≥2 разных вещей),
`needs_crop_review`, `needs_manual_confirmation`, `needs_rights_clearance`.

`render_ready = true` только при `full_support` без единого requirement.

Статус сцены (`resolution_status`): `resolved`, `resolved_needs_review`,
`unresolved_no_candidate`, `unresolved_unverified`, `unresolved_rights_blocked`,
`unresolved_generator_failed`, `manual_action_required`. Историческое поле `reason`
в `missing_scenes` сохранено как есть — его читают существующие вызовы.

## Crop decision (этап Q2.2A-2)

`decision.framing_decision`. Проверяет исходное разрешение, aspect ratio, размер
центральной области после кропа 9:16, ожидаемое итоговое разрешение (1080×1920),
`upscale_factor` и возможность pan/zoom для изображения.

| статус | смысл | решает |
|---|---|---|
| `vertical_ready` | уже в целевом соотношении (±2 %), пикселей хватает | render-ready |
| `crop_review_required` | пикселей хватает, но кадр придётся резать | **не** отказ, но и не полное совпадение |
| `low_resolution_after_crop` | кроп оставляет <540 px | отказ |
| `technical_rejected` | исходник мал сам по себе, до всякого кропа | отказ |
| `aspect_ratio_mismatch` | исходное соотношение >3.0 (панорама) | отказ |
| `unknown` | размеры неизвестны | не решает |

Vision здесь нет, поэтому утверждать, что главный объект переживёт кроп, запрещено:
любой кадр, который придётся резать, получает `crop_review_required`. `1280×720` даёт
полосу 405 px и отклоняется; `1920×1080` даёт 607 px и уходит на review; `1080×1920`
проходит как `vertical_ready`.

## Decision persistence (этап Q2.2A-2)

Одна каноническая запись `selection_decision` на ассете. Путь:

```
rank_candidates          пишет selection_decision на каждого кандидата
  → select_best_candidate  выбранный несёт её с собой
  → _ensure_selected_asset_downloaded  carry_decision() переносит её на скачанный файл
  → assets_manifest.json   scenes[].selected_asset.selection_decision
                           + scenes[].resolution_status / support_status
                           + visual_support (сводка по проекту)
  → visual_review_manifest.json  shortlist[].selection_decision, selected_candidate
  → project status         ProjectView.visual_support
```

До этого этапа `to_manifest_dict()` описывал файл, но не выбор, и всё обоснование
терялось между отбором и манифестом — доске обзора приходилось искать его обратно в
`ranked_candidates`. Теперь `attach_selected_asset` переносит вердикт на тот ассет,
который реально попал в проект.

Содержимое записи: semantic score/status, metadata score/status, technical score/status
+ полный `framing`, duration status, rights status, provider confidence, слоты
(`required/matched/missing/absent_required/conflicting/undecidable` + `details`),
`slot_verdict`, `support_status`, `support_requirements`, `render_ready`,
`selection_reasons`, `reject_reasons`. Provenance и license **не** дублируются — они
остаются в своих структурах.

Совместимость: ассет без `selection_decision` читается `read_decision()` как пустая
запись со статусом `unverified` и `render_ready = false`. Задним числом «полным
совпадением» старый манифест не становится.

`quality_check` печатает support status каждой сцены и **падает** только на
самопротиворечивой записи (`full_support` при отсутствующем обязательном слоте, при
конфликте, при непроверенном кропе). Превращать partial support в блокирующую ошибку
на этом этапе намеренно не стали: это остановило бы стадию render почти для любого
горизонтального стока, а это продуктовое решение, а не проверка.

## Классы с исчерпывающим списком провайдеров (этап Q2.2A)

`RESTRICTED_TO_PREFERRED = {data_infographic, manual_required}`. Для них
`PROVIDER_PRIORITY` — не предпочтение, а весь разрешённый набор: `build_strategy` не
дописывает «остальных доступных». Раньше дописывал, и статистика 54% уходила в Wikimedia,
NASA и Internet Archive. Пропущенные провайдеры фиксируются как
`not_permitted_for_<class>`.

Сцена `data_infographic` заканчивается ровно одним из двух: собственная инфографика
(`provider=generated`, `rights_status=user_owned`, checksum, provenance
`generated_by_project`) либо `unresolved_generator_failed`. Сгенерированный файл минует
путь скачивания — он уже локальный.

## Известные ограничения после Q2.2A-2

1. **Проверки содержимого кадра нет и на этом этапе.** Всё, что решает
   `decision.py`, решается по метаданным провайдера. Слоты закрывают случай «метаданные
   говорят правду, но не про то, что нужно сцене» (айсберг, пресс-день миссии). Случай
   «метаданные врут про сам кадр» ими не закрывается и закрыт быть не может: нужен
   анализ изображения. Платный Vision не подключён, локальная image-text модель не
   добавлена. Именно поэтому кадр, который надо резать, получает `crop_review_required`,
   а не «полностью готов».
2. **Мягкий матчинг слотов — допуск на словоформу, не морфология.** Правило «префикс
   длиной ≥5» узнаёт `Antarctica`/`antarctic` и не узнаёт `sampling`/`samples`.
   Русскоязычные слоты против англоязычных метаданных остаются `undecidable`.
3. **`context` и `conflicting_context` заполняет только автор.** Планировщик их не
   выводит: незаявленный контекст ничего не ограничивает, незаявленное противоречие
   противоречием не является. Сцена без брифа получает ровно те же гейты, что и до
   Q2.2A-2.
4. **Один ассет на сцену.** `needs_additional_asset` / `needs_multi_asset` только
   **фиксируют** потребность в добавочном материале. Сборка нескольких ассетов в одну
   сцену на этом этапе не реализована.
5. **Support status не блокирует render.** `quality_check` его печатает и падает лишь на
   самопротиворечивой записи. Решение «не рендерить сцену с partial support» —
   продуктовое и остаётся отдельной задачей.

## Известные ограничения после Q2.1

1. **Переводчика по-прежнему нет.** Русская сцена без брифа и без глоссарного попадания
   даёт `query_translation_required` — это честный отказ, а не подбор. Полноценный
   русско-английский адаптер запросов остаётся отдельной задачей.
2. **Semantic gate работает на метаданных, а не на кадре.** Это главное оставшееся
   ограничение: ретест Q2.1 дал три ложных принятия, и Q2.2A закрыл только одно из них
   (снимок Марса — через требование и через изоляцию класса). Два других прошли честно
   по метаданным: пресс-день миссии на Марс содержал слова «mass spectrometer», а описание
   раскола айсберга — «Antarctica». Отличить их может только анализ самого кадра. Платный Vision не подключён,
   локальная image-text модель не добавлена: оценка размеров зависимостей, работы на CPU
   под Windows и лицензии модели не проводилась, а добавлять тяжёлую зависимость без
   обоснования запрещено. Поэтому кадр, чьё описание врёт, пройти может.
3. **Wikimedia и NASA находят материал, но политика прав его гейтит.** В live smoke-тесте
   Wikimedia вернула точные снимки Сухих долин (`Public domain`, `CC BY-SA 4.0`), но
   `license_policy` для контекста `internal_content_production` ставит им
   `allowed_for_render = false` из-за обязательной атрибуции. Это решение политики, а не
   дефект поиска; для роликов без видимой атрибуции нужен либо пересмотр политики, либо
   выбор материала без attribution.
4. **Pixabay вернул 0 результатов** на «antarctic landscape» — это поведение самого
   провайдера, ошибок адаптера нет.
5. **`_concept_score` — совпадение токенов, не смысл.** Многословный `subject` вроде
   «barren polar valley landscape» получает частичный балл; несущей проверкой остаётся
   авторский `must_include`.
6. **Автоматическая классификация сцены слаба без брифа.** Двуязычный словарь узнаёт
   лабораторию, спутник, архив и полевую работу, но точное место без `place`/
   `exact_entities` обычно не распознаётся.

## Тесты

- `tests/test_visual_retrieval_repair.py` — 43 теста: бриф, стратегия, язык запроса,
  честный metadata score, must_include/must_avoid, длительность, инфографика.
- `tests/test_visual_retrieval_regression.py` — 14 тестов: восемь сцен провалившегося
  прогона офлайн, с настоящими заголовками неверных клипов.
- `tests/test_semantic_slot_decisions.py` — 32 теста этапа Q2.2A-2: слоты, континент
  против точного места, отсутствующие action/subject, айсберг, conflicting context,
  пресс-день миссии против нейтрального прибора, partial support у generic b-roll,
  инфографика только сгенерированная, пять состояний кропа, сохранение решения после
  выбора и после скачивания, чтение решения доской обзора, совместимость старых
  манифестов и планов, офлайн-манифест без сети и скачиваний. Офлайн-фикстура из пяти
  случаев (`Mars Media Day`, раскол айсберга, пластиковые контейнеры, горизонтальная
  Антарктида, PTR-TOF) написана вручную и не копирует пользовательские артефакты.
- Существующие `tests/test_provider_routing.py` и `tests/test_semantic_asset_selection.py`
  продолжают проходить без изменений.
