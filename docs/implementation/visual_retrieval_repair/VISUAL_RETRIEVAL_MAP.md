# Visual retrieval after Q2.1

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

Поля: `visual_description`, `subject`, `action`, `place` (алиас `location`),
`exact_entities`, `must_include`, `must_avoid`, `shot_type`, `media_types`,
`source_class`, `provider_queries`, `fallback_visual`, `infographic`, `notes`.

- Живёт в `ScriptScene.visual_brief` → `script.json` → применяется к плану в
  `src.content.visual_planning.engine` → попадает в существующий блок `semantic`.
- Передаётся в `ScriptRequest.visual_briefs` по номеру сцены или по `scene_id`.
  Сегодня его сохраняет только `user_supplied` — единственный провайдер, который не
  меняет границы авторских сцен.
- **Никогда не озвучивается**: стадия voice читает только `narration`.
- Каждое поле заменяет только себя; бриф с subject, но без action, action не стирает.

## Известные ограничения после Q2.1

1. **Переводчика по-прежнему нет.** Русская сцена без брифа и без глоссарного попадания
   даёт `query_translation_required` — это честный отказ, а не подбор. Полноценный
   русско-английский адаптер запросов остаётся отдельной задачей.
2. **Semantic gate работает на метаданных, а не на кадре.** Платный Vision не подключён,
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
- Существующие `tests/test_provider_routing.py` и `tests/test_semantic_asset_selection.py`
  продолжают проходить без изменений.
