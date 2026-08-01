---
status: audit
audit_date: 2026-07-31
audit_head: adcbb19
working_branch: governance-reset
scope: CRITICAL-1 (provider/query reachability) и CRITICAL-2 (topic → insufficient source → silent legacy template)
method: чтение кода + Git history + контролируемые offline-пробы без сети
changes_to_repository: только этот файл
---

# Deep dive: CRITICAL-1 и CRITICAL-2 — 2026-07-31

Второй, независимый разбор двух findings из
[INDEPENDENT_REPOSITORY_REVIEW_2026-07-31.md](INDEPENDENT_REPOSITORY_REVIEW_2026-07-31.md).
Предыдущий аудит **не принимался за доказанный**: каждая его цепочка перепроверена
чтением, историей Git и исполнением.

Классы утверждений:

- **FACT** — проверено чтением файла, командой Git или исполнением offline-пробы.
- **INFERENCE** — вывод из фактов, исполнением не проверенный.
- **RECOMMENDATION** — предложение, не факт.

Ничего не выполнялось: сеть, downloads, платные API, Vision, TTS, render.
Все пробы шли под `tests/network_guard.py` (`blocked_attempts == []`, то есть
попыток выхода в сеть не было вообще), во временных каталогах вне репозитория,
с провайдерами-заглушками.

---

## 1. Executive verdict

**CRITICAL-1: ответ — D (архитектура расходится), с элементами B.**
Предыдущий аудит прав в выводе («для типичной русской темы поиск фактически не
работает»), но **не прав в трёх механизмах**, и именно эти механизмы определяют,
что чинить.

1. **FACT.** Запросы иногда **всё-таки отправляются** — и это хуже, чем ноль.
   Для темы «Почему вороны запоминают человеческие лица» весь ролик уходит в
   провайдеры **одной строкой `ice researchers`**. Причина: `GLOSSARY` матчится
   подстрокой, и `лед` находится внутри слова «иссЛЕДователи»
   ([query_adapter.py:70](../../src/assets/query_adapter.py:70) +
   [query_adapter.py:391](../../src/assets/query_adapter.py:391)). Для темы
   «Солнечная электростанция и аккумуляторное хранилище» уходит `station`
   (`станция` ⊂ «электростанция»). Для темы «канал через пустыню» слово
   `пустыня` **не** матчится, потому что в тексте «пустын**ю**» — та же наивная
   подстрока даёт одновременно ложные срабатывания и пропуски.

2. **FACT.** `legacy_broad_query` («nature science wildlife observation»)
   **никогда не доходит до remote-провайдера** на каноническом пути. Предыдущий
   аудит утверждал обратное («единственная строка, которая гарантированно
   доходит»). `build_scene_queries` рассматривает source-language запросы как
   **единый набор**: `source_is_latin` требует, чтобы **ни в одном** из них не
   было кириллицы ([query_adapter.py:158-160](../../src/assets/query_adapter.py:158)).
   Русский `primary_query` отравляет весь набор, и английская broad-строка
   выбрасывается вместе с ним. Проба это подтвердила: строка присутствует в
   `alternative_queries` каждой сцены и не отправлена ни разу.

3. **FACT.** В production **уже существует полностью рабочий provider-ready
   английский путь** — но он захардкожен под одну тему. `_apply_video_first_topic_briefs`
   ([script_generator.py:115-190](../../src/news/script_generator.py:115)) для тем со
   словами `косат`/`orca`/`killer whale` проставляет каждой сцене `visual_brief`
   с готовыми английскими `provider_queries`. Проба: та же самая машина, тот же
   вход-тема, тот же CLI — **180 поисковых вызовов, 4 осмысленных английских
   запроса** против 10 вызовов строкой `ice researchers` для ворон.

Значит дефект — **не** «нет переводчика вообще» и **не** «поиск не настойчив».
Дефект: **единственный канал, по которому английский запрос доходит до
провайдера — `visual_brief`, и заполняет его только hardcode на одну тему.**

**CRITICAL-2: предыдущий аудит подтверждён полностью, плюс два усиления.**

- **FACT.** `topic` → `article.text == сама тема` → 1 claim → `_is_thin` → шесть
  шаблонных фраз. Воспроизведено на всех трёх темах.
- **FACT (новое).** Подмена **невидима для качества**: `script_validation.status
  == "passed"`, `valid: true`, `error_count: 0`. Ни один downstream-читатель не
  смотрит на `script_warnings` и `script_metadata.fallback_reason` — repo-wide
  поиск даёт ноль production-потребителей.
- **FACT (новое).** У канонического CLI **нет режима «вот исходный текст»**:
  `--input-mode` принимает `topic | article_url | pasted_script | script_file`
  ([content.py:94-100](../../src/content_creation/commands/content.py:94)), и
  `pasted_script` трактуется как **готовый сценарий** (`user_supplied`), а не как
  материал. Единственный вход с настоящим материалом — `article_url`, то есть
  сеть. Поэтому «честный отказ» без второго шага оставит пользователя вообще без
  offline-пути.

**Общий вывод для плана.** PLAN-9B назначен зоной
`src/assets/semantic_selection/query_generator.py` — **это не тот модуль**.
Он не участвует в формировании запросов к remote-провайдерам. Реальный владелец —
`src/assets/query_adapter.py`. Это ошибка allowed zone, а не приоритета.

---

## 2. Current canonical runtime path

**FACT.** Полная цепочка канонического автоматического пути, проверена чтением и
исполнением:

```
python -m ai_youtube create --input-mode topic --topic "<RU>"
  ai_youtube/__main__.py:1 → src/ai_youtube/cli/main.py:115 main
  → src/ai_youtube/cli/commands/create.py handle_create
  → src/content_creation/service.py:95 create_content        (resolve template + validate)
  → .../fullscreen_voiceover/use_case.py:30 create_fullscreen_voiceover
      :89  _prepare_project      → src/news/pipeline.py:49  create_news_to_short_job
      :176 _run_safe_pipeline    → src/news/pipeline.py:111 run_news_to_short_job(until_stage="asset_search")
      :205 _run_voice_stage      → run_news_to_short_job(stage="voice")
      :449 _run_subtitles        → run_news_to_short_job(stage="subtitles")
      :493 _render_and_export    → run_news_to_short_job(stage="preview_render" | "quality_check"
                                                          | "final_render" | "export")
```

Внутри стадий ([pipeline.py:315-399](../../src/news/pipeline.py:315)):

| Стадия | Owner | Что делает |
|---|---|---|
| `article_ingestion` | [article_ingestor.py:53-55](../../src/news/article_ingestor.py:53) | topic-режим: `article["text"] = job.topic` |
| `research` | [research_engine.py:9-45](../../src/news/research_engine.py:9) | regex-разбиение на предложения, до 8 claims |
| `script` | [script_generator.py:104](../../src/news/script_generator.py:104) → script_engine | `deterministic_local`, при thin-input → `legacy_template` |
| `script` (post) | [script_generator.py:115-190](../../src/news/script_generator.py:115) | **hardcode:** orca-темам проставляется `visual_brief` |
| `visual_plan` | [visual_plan.py:29](../../src/news/visual_plan.py:29) → planners/deterministic | intents **в языке сценария**, `requires_translation` выставляется |
| `visual_plan` (post) | [legacy_format.py:148-210](../../src/content/visual_planning/legacy_format.py:148) | `primary_query` = термины intent (RU), в хвост `alternative_queries` дописывается `legacy_broad_query` |
| `asset_search` | [asset_manifest_builder.py:266](../../src/news/asset_manifest_builder.py:266) | `route_providers` → **`build_scene_queries`** → `_search_scene_providers` |

**FACT.** Единственная точка, где решается, что получит провайдер:
[asset_manifest_builder.py:276](../../src/news/asset_manifest_builder.py:276) →
[query_adapter.py:141 `build_scene_queries`](../../src/assets/query_adapter.py:141).
Вторая (только для draft_complete-доборки слотов):
[asset_scene_completion.py:289](../../src/news/asset_scene_completion.py:289) →
[query_adapter.py:235 `build_slot_queries`](../../src/assets/query_adapter.py:235).
**Других путей к remote-провайдеру в активном workflow нет.**

**FACT.** Провайдер, у которого нет ни одного разрешённого запроса, пропускается
с записью `status: skipped, reason: query_translation_required`
([asset_manifest_builder.py:328-346](../../src/news/asset_manifest_builder.py:328)).

**FACT.** Локальная медиатека в эту логику **не входит вообще**: кандидаты из неё
добираются напрямую через `rank_local_assets`
([asset_manifest_builder.py:295](../../src/news/asset_manifest_builder.py:295) →
[:1246-1268](../../src/news/asset_manifest_builder.py:1246)), которая режет русский
`primary_query` на токены и ищет по локальному индексу. Языковой гейт
`query_adapter` на неё не распространяется.

---

## 3. Historical implementations from Git

**FACT.** История цела: 105 commits, 2026-05-15 … 2026-07-31, две ветки
(`master fe2df5b`, `governance-reset adcbb19`). Squash/rewrite не обнаружен.

**FACT.** Поиск по всей истории (`git log --all -S` по `*.py`):

| Символ | Результат |
|---|---|
| `Translator` | **0 commits** |
| `def translate` | **0 commits** |
| `to_english` | **0 commits** |

**Вывод (FACT).** Слой перевода в application-коде **не существовал никогда**.
Восстанавливать нечего — вопрос «была ли реализация удалена» закрыт отрицательно.

### 3.1. Что действительно работало раньше — три разные вещи

**(A) Май 2026, legacy documentary pipeline — английские `visual_keywords`
пишет автор задачи, а не код.**

- **FACT.** [content/survival/juliane_koepcke_001.json](../../content/survival/juliane_koepcke_001.json),
  commit `9e4e03f` (2026-05-17): нарратив, заголовки и субтитры — русские,
  а `visual_keywords` — **английские** (`"storm clouds airplane"`,
  `"dark rainforest aerial"`, `"teen girl silhouette window"`).
- **FACT.** [scene_planner.py:59-85](../../src/scene_planner.py:59) переносит их в
  scene plan; [video_asset_engine.py:225-256 `build_query_variants`](../../src/video_asset_engine.py:225)
  строит из них **настоящую лестницу расширения**: базовый термин → `+cinematic`
  → `+documentary footage` → усечение до двух слов → `<mood> documentary` →
  channel-специфичные расширения, до 12 вариантов; затем
  [:137-148](../../src/video_asset_engine.py:137) отправляет первые 4 в Pexels и
  Pixabay, предварительно исчерпав локальную медиатеку
  ([:116-135](../../src/video_asset_engine.py:116)) с резервированием слотов под
  разнообразие.
- **INFERENCE.** Именно это владелец помнит как «поиск работал значительно
  лучше». Он и правда работал — потому что **английские ключи приходили извне**,
  а лестница расширения была лучше сегодняшней.

**(B) 25 июля 2026, baseline `13cc3f4` — news-путь всегда слал английскую строку.**

- **FACT.** `git show 13cc3f4:src/news/visual_plan.py` — `make_stock_query`
  возвращает одну из четырёх **английских** констант, и она становится
  `primary_query` **каждой** сцены. Русского в запросе не было в принципе.
- **FACT.** `git show 13cc3f4:src/news/asset_manager.py:112-133` — этот
  `primary_query` уходил провайдеру напрямую, без языкового гейта.
- **INFERENCE.** Покрытие было 100 % (что-то возвращалось всегда), релевантность —
  околонулевая (четыре строки на все видео). Субъективно это выглядит как
  «работало»: ролик собирался.

**(C) 26-28 июля 2026 — три коммита, которые дали текущее состояние.**

| Commit | Дата | Что изменилось | Эффект на поиск |
|---|---|---|---|
| `66b2e13` | 2026-07-26 | `visual_planning` foundation; `primary_query` = термины intent **на языке сценария**, английская broad-строка понижена до последнего `alternative` ([legacy_format.py:84-100](../../src/content/visual_planning/legacy_format.py:84)) | русский попал в `primary_query` |
| `fc459c7` | 2026-07-27 | введён `query_adapter`: remote-провайдеры объявлены English-only, русский запрос **блокируется** вместо отправки | покрытие 100 % → почти 0 % |
| `8d61a06` | 2026-07-28 | `_apply_video_first_topic_briefs` — hardcode `visual_brief` для orca-тем | одна тема получила рабочий путь |

**FACT.** Docstring `fc459c7` сам фиксирует мотив: Wikimedia и NASA отвечали
**0 результатов на 16 запросов каждый**, а стоки возвращали «что придумает
нечёткий поиск по иностранным словам»
([query_adapter.py:1-23](../../src/assets/query_adapter.py:1)). Решение
«не гадать» — правильное. Незакрытым осталось следствие: **никто не построил
источник английских слов**, кроме hardcode на косаток.

**RECOMMENDATION.** Ничего из истории не откатывать. Восстановлению подлежит
**одно знание** — лестница расширения из `build_query_variants` — и **одна
практика** — «английские ключи для сцены существуют как отдельное поле,
отделённое от нарратива» (это и есть сегодняшний `visual_brief`).

---

## 4. Was Codex/Claude doing work outside the application?

**Ответ: B, с частичным A.**

**FACT (B).** Английские `visual_keywords` в `content/**/*.json` — это **входные
данные, а не выход кода**. Ни один модуль репозитория их не порождает: поиск
`visual_keywords` по `src ai_youtube apps anime_factory legacy pipeline.py` даёт
только **читателей** ([scene_planner.py:63](../../src/scene_planner.py:63),
[video_asset_engine.py:226](../../src/video_asset_engine.py:226),
[media_library.py:514](../../src/media_library.py:514),
[quote_generator.py:170](../../src/quote_generator.py:170)) и одно
**переименование** ([asset_manifest_builder.py:1260](../../src/news/asset_manifest_builder.py:1260),
где `primary_query.split()` подставляется под тот же ключ). Автор файла —
человек или агент; понимание русской темы и подбор английских ключей произошли
**вне приложения**.

**FACT (частично A).** Одна capability всё же попала в код —
`_apply_video_first_topic_briefs` ([script_generator.py:115-190](../../src/news/script_generator.py:115)).
Это буквально «агент однажды подобрал английские запросы для косаток», записанное
в production `if`. Тот же формат данных (`provider_queries`, `subject`, `action`,
`place`, `must_avoid`), который агент раньше писал в задачу вручную.

**Что из agent-workflow ценно и должно переехать в приложение (KNOWLEDGE):**

1. **Структура ответа.** `subject / action / place / exact_entities /
   must_avoid / provider_queries` — набор, который агент заполнял и который уже
   есть как [`VisualBrief`](../../src/content/visual_planning/brief.py:30). Схема
   готова, заполнять её некому.
2. **Несколько запросов на сцену, от точного к общему** — `provider_queries`
   в orca-hardcode содержит ровно три уровня: точный субъект → стая → среда.
3. **`must_avoid` как часть перевода**, а не отдельная настройка: «косатка, но не
   дельфин и не горбач» — это часть смысла запроса.
4. **Тема ролика фиксируется один раз и переносится во все сцены** — все шесть
   сцен orca-ролика получили один `subject`, различаясь `action`.

**FACT.** Успешная работа агента **не** доказывает наличия capability в
приложении: сегодня без hardcode ни один из этих четырёх пунктов не выполняется
автоматически ни для одной темы.

---

## 5. Offline three-topic experiment

**Метод (FACT).** Пробы во временных каталогах вне репозитория, под
`network_guard`, провайдеры — записывающие заглушки с
`query_languages=["en"]`, `search()` возвращает пустой список, `download()`
поднимает исключение (не вызывался ни разу). Прогон стадий
`input → article_ingestion → research → script → visual_plan → asset_search`
реальным `run_news_to_short_job`. `blocked_attempts == []`.

### 5.1. Сценарий и материал

**FACT.** Одинаково для всех трёх тем:

| Показатель | Значение |
|---|---|
| `article.text == topic` | `True` |
| claims после research | **1** |
| `script_provider` | **`legacy_template`** |
| `script_warnings` | `insufficient_source_material: …использован прежний шаблонный движок` |
| `script_metadata` | `{"source_unit_count": 1, "requested_provider": "deterministic_local", "fallback_provider": "legacy_template", "fallback_reason": "insufficient_source_material"}` |
| `script_validation` | `{"status": "passed", "valid": true, "error_count": 0}` |
| `scene_count` | 6, длительности `[3.5, 7.0, 10.0, 13.0, 10.0, 8.0]` |
| `intent_language` | `ru` |
| `visual_brief` | отсутствует во всех сценах всех трёх тем |

### 5.2. Что получил бы провайдер

**FACT.** Прогон `asset_search` с записывающими заглушками:

| Тема | Реальных вызовов `search()` | Уникальные строки | Пропущено по `query_translation_required` | Пустых сцен |
|---|---|---|---|---|
| Почему вороны запоминают человеческие лица | **10** | `ice researchers` | 25 из 30 | 6 из 6 |
| Солнечная электростанция и аккумуляторное хранилище | **50** | `station`, `ice researchers station` | 5 из 30 | 6 из 6 |
| Строительство большого канала через пустыню | **10** | `ice researchers` | 25 из 30 | 6 из 6 |
| *(контроль)* Почему косатки взрывают огромных рыб | **180** | `Orcinus orca killer whale ocean`, `killer whale pod ocean`, `open ocean underwater`, `marine biologist ocean research` | **0** | 6 из 6 (заглушка ничего не возвращает) |

**FACT.** Источник каждого отправленного запроса для первых трёх тем —
`deterministic_glossary`. Ни одного `visual_brief_fields`, ни одного
`explicit_override`, ни одного `provider_supports_source_language`.

**FACT.** Разбор трёх глоссарных срабатываний (проверено исполнением):

| Вход | Совпадение | Результат | Оценка |
|---|---|---|---|
| «И**ссЛЕД**ователи связывают…» | `лед` → `ice` **и** `исследовател` → `researchers` | `ice researchers` | **ложное срабатывание**: лёд не имеет отношения ни к одной из трёх тем |
| «электро**станция**» | `станция` → `station` | `station` | **чрезмерное обобщение**: солнечная электростанция → «станция» |
| «пустын**ю**» | `пустыня` **не** ⊂ «пустыню» | ничего | **пропуск**: единственное слово темы, которое есть в глоссарии, не сработало из-за падежа |

Механизм — прямое `if russian in text` по всему тексту сцены
([query_adapter.py:391-393](../../src/assets/query_adapter.py:391)), без
нормализации, без границ слова, без учёта морфологии.

### 5.3. Проверка утверждений предыдущего аудита

| Утверждение прошлого аудита | Проверка | Итог |
|---|---|---|
| topic-режим даёт шаблонный сценарий | воспроизведено на 3/3 темах | **подтверждено** |
| перевод отсутствует, remote-провайдеры English-only | [query_adapter.py:43-56](../../src/assets/query_adapter.py:43) | **подтверждено** |
| `visual_brief` в автоматическом потоке не создаётся никем | создаётся — для orca-тем, [script_generator.py:115](../../src/news/script_generator.py:115) | **опровергнуто частично** |
| «ноль отправленных запросов» | 10 / 50 / 10 вызовов на тему | **опровергнуто** |
| `legacy_broad_query` — единственное, что доходит до провайдера | не доходит ни разу | **опровергнуто** |
| каждая сцена ищется одной строкой | верно по факту, но строка другая (`ice researchers` / `station`) | **подтверждено с исправлением** |

### 5.4. Отдельная проба: сравнение input mode

**FACT.** Тот же материал про ворон, поданный как `--text` (режим `text` на
уровне `src.news`), даёт **другой сценарий**: 7 claims, `deterministic_local`,
нарратив из предложений источника («Вороны узнают лица людей и помнят их
годами.»), никакого `insufficient_source_material`. То есть **дефект CRITICAL-2
локализован в topic-режиме**, движок сценария исправен.

**FACT.** Запросы при этом всё равно остаются мусорными: уникальные отправленные
строки — `ice` и `ice researchers`. **CRITICAL-1 не лечится наличием материала.**
Это два независимых дефекта, и порядок их починки значения не имеет.

---

## 6. Comparison of all existing entrypoints

**FACT.** Все фактически существующие входы (проверено `if __name__` / `def main`
+ `pyproject [project.scripts]`):

| # | ENTRYPOINT | REQUEST | USE CASE | PIPELINE | VISUAL PLAN | QUERY BUILDER | PROVIDER | SELECTOR | COMPLETION |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `python -m ai_youtube` ([ai_youtube/__main__.py](../../ai_youtube/__main__.py:1)) | `ContentCreationRequest` | `create_content` | `src.news.pipeline` | `visual_planning` | **`query_adapter`** | `providers/registry` | `semantic_selection` | `assets/completion` |
| 2 | `python -m src.ai_youtube` | идентично #1 | идентично | идентично | идентично | идентично | идентично | идентично | идентично |
| 3 | console-script `ai-youtube` ([pyproject.toml:26](../../pyproject.toml:26)) | идентично #1 | идентично | идентично | идентично | идентично | идентично | идентично | идентично |
| 4 | `src.content_creation.cli:main` | идентично #1 | идентично | идентично | идентично | идентично | идентично | идентично | идентично |
| 5 | `python -m apps.news_to_short` | **собственный argparse** (19 флагов) | **обходит `create_content`** | `src.news.pipeline` напрямую | как #1 | как #1 | как #1 | как #1 | как #1 |
| 6 | `python pipeline.py` | `src/legacy_pipeline/cli.py` | `run_legacy_video_pipeline` | legacy | `scene_planner` из task JSON | **`build_query_variants`** | Pexels/Pixabay напрямую | `score_survival_relevance` | `fallback_used` |
| 7 | `python pipeline.py --news-to-short` | тот же argparse | `run_news_to_short_cli` | `src.news.pipeline` | как #1 | как #1 | как #1 | как #1 | как #1 |
| 8 | `python -m apps.youtube_pipeline` | — | делегирует в `pipeline.main` | как #6 | как #6 | как #6 | как #6 | как #6 | как #6 |
| 9 | `python -m apps.anime_factory` | `anime_factory/pipeline.py:211` | Anime Clipper | source video → clips | нет | **нет поиска** | нет | `score_candidates` | нет |
| 10 | `python -m anime_factory.pipeline` | идентично #9 | идентично | идентично | — | — | — | — | — |
| 11 | `src/project_foundation/cli.py:181` | — | project/channel CRUD | — | — | — | — | — | — |
| 12 | `tools/qa/check_agent_docs.py` | — | QA документации | — | — | — | — | — | — |

**FACT.** Классификация:

- **Идентичны (#1-#4, #7):** пять способов вызвать одну и ту же функцию. #2 и #3
  разрешаются в тот же `src.ai_youtube.cli.main:main`; #4 — тонкий адаптер
  ([content_creation/cli.py:1-8](../../src/content_creation/cli.py:1) прямо это
  декларирует).
- **Wrappers без своей логики (#8, #10):** по 10 строк, делегируют.
- **Расходится (#5):** `apps/news_to_short` — единственный вход, который
  **пропускает** `create_content`, а вместе с ним — резолв template, валидацию
  музыки, paid-preflight и `visual_briefs`-merge. Из-за этого у него **есть флаг
  `--text`, которого нет у канонического CLI** (см. §9.2).
- **Отдельная реализация (#6):** legacy documentary — свой планировщик, свой
  query builder, свой отбор, свои провайдеры. Не мёртвый: рабочие данные лежат в
  [content/](../../content/), точка входа в `pyproject` (`py-modules = ["pipeline"]`).
- **Мёртвый (#9-#10 по catalog):** Anime Clipper — `enabled=False`,
  `implementation_status="planned"` ([catalog.py:44-45](../../src/production_catalog/catalog.py:44)).
- **Полностью мёртвый:** [legacy/](../../legacy/) — 8 файлов, 0 Python-callers
  (совпадает с C17 registry).

---

## 7. apps/* responsibility map

**FACT.**

| PATH | RESPONSIBILITY | CALLERS | UNIQUE LOGIC | DUPLICATED LOGIC | CANONICAL OWNER | ACTION |
|---|---|---|---|---|---|---|
| [apps/news_to_short/main.py](../../apps/news_to_short/main.py) | вход в Fullscreen Voiceover | `__main__.py`, docs | **есть:** свой argparse; `--text`/`--text-file` без аналога в каноническом CLI; прямой вызов `create/run/resume` | резолв путей, вызов pipeline | `src.ai_youtube.cli` + `content_creation.service` | **MIGRATE UNIQUE CAPABILITY** (`--text` → канонический `--input-mode source_text`), затем RETIRE |
| [apps/news_to_short/__main__.py](../../apps/news_to_short/__main__.py) | shim | — | нет | 6 строк, копия | — | RETIRE вместе с родителем |
| [apps/youtube_pipeline/main.py](../../apps/youtube_pipeline/main.py) | вход в legacy pipeline | `__main__.py` | нет | делегирование | `pipeline.py` | **RETIRE** вместе с PLAN-L4 |
| [apps/youtube_pipeline/__main__.py](../../apps/youtube_pipeline/__main__.py) | shim | — | нет | копия | — | RETIRE |
| [apps/anime_factory/main.py](../../apps/anime_factory/main.py) | вход в Anime Clipper | `__main__.py` | нет | делегирование | `anime_factory/pipeline.py` | **KEEP** до решения по C07 |
| [apps/anime_factory/__main__.py](../../apps/anime_factory/__main__.py) | shim | — | нет | копия | — | KEEP до C07 |
| [apps/__init__.py](../../apps/__init__.py) | package marker | — | нет | — | — | KEEP |
| [anime_factory/](../../anime_factory/) (корень) | реализация Anime Clipper | `apps/anime_factory`, adapter | **есть:** транскрипция, детекция сцен/лиц, динамический кроп, скоринг | своя subtitle-запись (C13), свой FFmpeg runner (C14), свои пути (C15) | `src/ai_youtube/apps/video_repurposer` | **MERGE** (C07), не в этом слайсе |

**FACT.** Ни один `apps/*` не содержит собственных TTS, render, project model
или asset pipeline. Единственная уникальная бизнес-возможность во всём `apps/` —
флаги `--text` / `--text-file` в `news_to_short`
([main.py:22-23](../../apps/news_to_short/main.py:22)).

**FACT.** Это ровно та возможность, которой не хватает CRITICAL-2: подать
исходный текст, не выдавая его за готовый сценарий. Она уже написана, уже
работает (проверено пробой §5.4) и просто не доведена до канонического CLI.

---

## 8. CRITICAL-1 verdict

**Ответ: D — архитектура расходится**, с уточнением B.

**Обоснование (FACT):**

1. Один и тот же вход (`--input-mode topic`, русская тема, тот же CLI, тот же
   pipeline) даёт **три несовместимых поведения** в зависимости от **содержания
   темы**:
   - тема со словом «косат» → 180 вызовов, 4 корректных английских запроса;
   - тема, чей текст подстрокой попадает в глоссарий → 10-50 вызовов одной
     семантически неверной строкой;
   - тема, не попавшая никуда → 0 вызовов, все провайдеры `skipped`.
2. Расхождение проходит **не по entrypoint** (#1-#5 и #7 идентичны), а по
   **наличию `visual_brief`** — то есть по единственному hardcode-`if`.
3. Одновременно верно и B: существует другая рабочая реализация лестницы запросов
   ([video_asset_engine.py:225](../../src/video_asset_engine.py:225)), но она
   принадлежит другому (legacy) pipeline и питается ключами, которые пишет автор.

**Чего в вердикте нет.** Утверждение «current path в принципе не может отправить
запрос» — неверно. Он отправляет; проблема в том, **что именно** он отправляет и
**откуда** это берётся.

**FACT — точный список того, что сломано, в порядке ущерба:**

| # | Дефект | file:line | Ущерб |
|---|---|---|---|
| 1 | нет источника английских терминов для произвольной темы | [query_adapter.py:329-367](../../src/assets/query_adapter.py:329) | основной |
| 2 | глоссарь матчится подстрокой: `лед` ⊂ «исследователи» | [query_adapter.py:391-393](../../src/assets/query_adapter.py:391) | **отправляются ложные запросы**, что хуже пустого результата |
| 3 | глоссарь не знает морфологии: «пустыню» ≠ «пустыня» | там же | пропуск единственного релевантного слова |
| 4 | source-queries оцениваются как единый набор → английский `alternative` выбрасывается вместе с русским `primary` | [query_adapter.py:158-160](../../src/assets/query_adapter.py:158) | теряется уже существующий английский запрос |
| 5 | topic-hardcode на одну тему | [script_generator.py:115-190](../../src/news/script_generator.py:115) | скрывает дефект от владельца на «своей» теме |
| 6 | `requires_translation` выставляется и никем не читается | [planners/deterministic.py:359](../../src/content/visual_planning/planners/deterministic.py:359) | сигнал есть, потребителя нет |
| 7 | `legacy_broad_query` дописывается в каждую сцену и никогда не используется | [legacy_format.py:161-164](../../src/content/visual_planning/legacy_format.py:161) | шум в persisted-плане |

**INFERENCE.** Дефект №4 — самый дешёвый в починке (перевести проверку с набора
на элемент) и даёт немедленный эффект: английская broad-строка начнёт доходить.
Это восстановит покрытие baseline `13cc3f4`, не более того. Как самостоятельное
решение недостаточно — но как страховка под фичей №1 полезна.

---

## 9. CRITICAL-2 verified implementation surface

### 9.1. Точная реализация

**FACT.** Цепочка, проверена построчно и исполнением:

```
--input-mode topic
  → resolve_content_inputs (use_case.py:615-617)   mode == "topic" → topic, без text/url
  → create_news_to_short_job (pipeline.py:76-81)   нет url и нет text → INPUT_MODE_TOPIC
  → ingest_article (article_ingestor.py:53-55)     article["text"] = job.topic
  → build_research (research_engine.py:9-45)       split_sentences(тема) → 1 claim
  → resolve_source_kind (script_generator.py:50)   topic + есть claims → SOURCE_RESEARCH
  → DeterministicScriptProvider.generate (deterministic.py:116)
      _collect_units (:176-206)                    1 unit
      _is_thin (:247-252)                          len(units) < 2 → True
      _fallback (:150-170)                         allow_legacy_fallback по умолчанию True
  → LegacyTemplateScriptProvider.generate (legacy_template.py:51-100)
      _build_scene_texts (:110-121)                6 фиксированных фраз
  → warnings += "insufficient_source_material…"    (deterministic.py:158-161)
  → metadata += fallback_provider/fallback_reason  (deterministic.py:162-169)
  → to_legacy_script (legacy_format.py:104-107)    → script_warnings / script_metadata
```

### 9.2. Все input modes

**FACT.**

| Режим CLI | `NewsJob.input_mode` | Источник материала | Провайдер сценария | Итог |
|---|---|---|---|---|
| `topic` | `topic` | **нет** (текст = тема) | `deterministic_local` → **`legacy_template`** | **шаблон, молча** |
| `article_url` | `url` | статья по сети | `deterministic_local` | честный экстрактивный сценарий |
| `pasted_script` | `text` + `script_source=user_script` | текст пользователя | `user_supplied` | текст используется **дословно как озвучка** |
| `script_file` | `text` + `script_source=user_script` | файл | `user_supplied` | то же |
| `--text` только через `apps/news_to_short` | `text`, `script_source` пуст | текст пользователя | `deterministic_local` | **честный экстрактивный сценарий из материала** |

**FACT.** Последняя строка — единственный offline-режим, дающий настоящий
сценарий из настоящего материала, и он **недоступен из канонического CLI**:
`choices` не содержат такого значения
([content.py:98](../../src/content_creation/commands/content.py:98)).

### 9.3. Видимость подмены

**FACT.**

| Канал | Содержит факт подмены? | Кто читает |
|---|---|---|
| `script["script_warnings"]` | да | **никто** (repo-wide поиск: 0 production-читателей) |
| `script["script_metadata"]["fallback_reason"]` | да, `"insufficient_source_material"` | **никто** |
| `script["script_provider"]` | да, `"legacy_template"` | **никто** |
| `script["script_validation"]` | **нет**: `status="passed"`, `valid=true` | `quality_check`, CLI |
| `quality_check` | **нет проверки происхождения сценария** ([quality_check.py:9-62](../../src/news/quality_check.py:9)) | render gate |
| completion / publish-readiness | **нет**: работает с ассетами, не с текстом | strict gate |

**FACT.** Ответ на вопрос «может ли strict-pipeline пометить такой результат
publish-ready»: по признаку сценария — **да**, ограничений нет. Сегодня он не
доходит до publish по **другой** причине — все сцены `missing` из-за CRITICAL-1.
**Как только CRITICAL-1 починят, шаблонный сценарий поедет в publish беспрепятственно.**
Это скрытая связь между двумя findings и причина не откладывать CRITICAL-2.

### 9.4. Тесты, защищающие текущее поведение

**FACT.**

| Тест | Что фиксирует | Судьба |
|---|---|---|
| [test_script_engine.py:286-292](../../tests/test_script_engine.py:286) | thin input → `legacy_template` + warning | **изменить**: ожидание становится «blocking для strict» |
| [test_script_engine.py:296-301](../../tests/test_script_engine.py:296) | `allow_legacy_fallback=False` → `ScriptProviderInputError` | **сохранить**: это уже нужное поведение, надо лишь сменить default для strict |
| [test_script_engine_pipeline.py:233-236](../../tests/test_script_engine_pipeline.py:233) | тот же fallback на уровне pipeline | изменить вместе с предыдущим |
| [test_script_engine_pipeline.py:141-157](../../tests/test_script_engine_pipeline.py:141) | **orca-hardcode** | **удалить** вместе с hardcode |
| [test_visual_planning.py:442-445](../../tests/test_visual_planning.py:442) | broad-строка присутствует в `alternative_queries` | **переписать**: проверять доставку провайдеру, а не наличие в JSON |

### 9.5. Owner direction — как выполнить минимальным изменением

**FACT — существующие механизмы, которых достаточно:**

1. `provider_options={"allow_legacy_fallback": False}` **уже реализован**
   ([deterministic.py:152-156](../../src/content/script_engine/providers/deterministic.py:152))
   и уже поднимает `ScriptProviderInputError`. Новый флаг **не нужен** — нужно
   лишь связать его с completion mode.
2. `ScriptValidationResult` — существующий owner статуса сценария
   ([validation.py:33-56](../../src/content/script_engine/validation.py:33)).
   Добавление в него одного issue-кода `template_filler_in_strict_mode` даёт
   блокирующий статус **без нового словаря состояний**.
3. `script_metadata.fallback_provider` / `fallback_reason` — **уже существующий
   metadata owner** для происхождения текста.

**RECOMMENDATION по идее `content_origin`.**
Отдельное поле **вводить не нужно**. Информация уже выражена существующим
владельцем:

| Предложенное значение | Уже выражается как |
|---|---|
| `extracted_from_source` | `script_provider == "deterministic_local"` без `fallback_reason` |
| `template_filler` | `script_provider == "legacy_template"` + `fallback_reason == "insufficient_source_material"` |
| `model_written` | `script_provider == "llm"` (провайдер зарегистрирован, `implementation_status="planned"`) |
| *(не покрыто предложением)* | `script_provider == "user_supplied"` — слова автора |

Дефект не в отсутствии поля, а в том, что **никто это поле не читает**.
Добавление `content_origin` создаст **второй** источник той же правды.
Правильное минимальное изменение: научить `validate_script` и `quality_check`
читать `provider_id` + `fallback_reason`, которые уже есть.

**RECOMMENDATION — минимальный честный контур (без LLM):**

1. `strict` → `allow_legacy_fallback = False`; `draft`/`template`/`demo` →
   `True` (существующий флаг, существующий словарь режимов
   [completion/modes.py](../../src/assets/completion/modes.py)).
2. `topic` без источника в strict → блокирующий отказ с внятной альтернативой:
   «дайте URL, вставьте текст источника, или запустите в draft/template-режиме».
3. Канонический CLI получает режим «исходный текст» — **перенос уже работающего
   `--text` из `apps/news_to_short`**, не новая функциональность.
4. LLM-research **не добавлять в этом слайсе**: он не требуется, чтобы перестать
   врать, и подпадает под network/paid approval boundaries.

---

## 10. Duplicate / dead / legacy search implementations

**FACT.** Полная классификация всей найденной search/query-логики.

### 10.1. Генераторы запросов — четыре независимых

| # | Реализация | file:line | Callers | Класс | Лучше canonical | Хуже canonical |
|---|---|---|---|---|---|---|
| 1 | `build_scene_queries` / `build_slot_queries` | [query_adapter.py:141](../../src/assets/query_adapter.py:141), [:235](../../src/assets/query_adapter.py:235) | [asset_manifest_builder.py:276](../../src/news/asset_manifest_builder.py:276), [asset_scene_completion.py:289](../../src/news/asset_scene_completion.py:289) | **CANONICAL** | — | — |
| 2 | `generate_queries` / `ordered_queries` | [semantic_selection/query_generator.py:6](../../src/assets/semantic_selection/query_generator.py:6) | [asset_manifest_builder.py:577,749,807,839](../../src/news/asset_manifest_builder.py:577), [youtube_shorts.py:263](../../src/production_plan/youtube_shorts.py:263) | **USEFUL BUT DISCONNECTED** | лестница `exact → broad → environment → atmospheric` уже сформулирована | не проходит языковой гейт; hardcode `_animal_category` → `"whale"` ([:39-42](../../src/assets/semantic_selection/query_generator.py:39)); питает только envato-метаданные и отчёты |
| 3 | `build_query_variants` | [video_asset_engine.py:225-256](../../src/video_asset_engine.py:225) | [asset_finder.py:22](../../src/asset_finder.py:22) ← `pipeline.py` | **LEGACY (knowledge valuable)** | **настоящая лестница расширения**: суффиксы, усечение, mood, channel-расширения, 12 вариантов | требует готовых английских ключей; channel-hardcode `survival`; в PLAN-L помечен к удалению |
| 4 | `legacy_broad_query` | [legacy_format.py:84-100](../../src/content/visual_planning/legacy_format.py:84) | [legacy_format.py:161](../../src/content/visual_planning/legacy_format.py:161), [visual_plan.py:78](../../src/news/visual_plan.py:78) | **DEAD (по факту доставки)** | — | четыре константы; **проба показала 0 доставок**; засоряет каждую сцену persisted-плана |

### 10.2. Источники «английских слов» — три, все ущербные

| Реализация | file:line | Класс | Комментарий |
|---|---|---|---|
| `GLOSSARY` (40 пар, подстрочный матч) | [query_adapter.py:62-79](../../src/assets/query_adapter.py:62), [:383-394](../../src/assets/query_adapter.py:383) | **SUPERSEDED (нужна замена, не расширение)** | даёт `ice` на «исследователи»; пропускает «пустыню»; предметная область — Антарктида/микропластик |
| `_apply_video_first_topic_briefs` (orca) | [script_generator.py:115-190](../../src/news/script_generator.py:115) | **KNOWLEDGE ONLY** | правильная форма ответа, неправильный носитель (`if` на одну тему) |
| `visual_keywords` в task JSON | [content/survival/juliane_koepcke_001.json](../../content/survival/juliane_koepcke_001.json) | **KNOWLEDGE ONLY** | доказывает, что перевод выполнялся вне приложения |

### 10.3. Реестры провайдеров — пять списков

**FACT.** Один и тот же набор провайдеров перечислен в пяти местах, с
расхождениями:

| Место | file:line | Состав | Расхождение |
|---|---|---|---|
| фактический конструктор | [providers/registry.py:15-37](../../src/providers/registry.py:15) | wikimedia, nasa_images, internet_archive, +pexels/pixabay при ключах | **`local_library` отсутствует** |
| языковая таблица | [query_adapter.py:43-56](../../src/assets/query_adapter.py:43) | 9 имён, включая `local_library` и `fake` | объявляет провайдера, который не создаётся |
| порядок по умолчанию | [provider_routing.py:23-30](../../src/assets/provider_routing.py:23) | 7 имён | включает `local_library`, `envato_manual` |
| приоритет по source class | [scene_strategy.py:54-65](../../src/assets/scene_strategy.py:54) | 6 имён × 9 классов | `local_library` первый во всех классах |
| диагностика | [provider_diagnostics.py:117-128](../../src/assets/provider_diagnostics.py:117) | 8 имён | включает `fake` |

**Класс: DUPLICATE.** Ни один из списков не является производным от другого.

### 10.4. Wrappers/facades без уникальной ответственности

**FACT.**

| Путь | file:line | Класс |
|---|---|---|
| `src/content_creation/fullscreen_voiceover_use_case.py` | весь файл, 29 строк re-export | **DUPLICATE** (registry C03) |
| `src/content_creation/story_card_use_case.py` | то же | **DUPLICATE** (C03) |
| `src/content_creation/cli.py` | 81 строка делегирования | **DUPLICATE** (C02) |
| `src/news/asset_manager.py:64-106 build_assets_manifest` | «Compatibility facade over the split asset-manifest builder» | **DUPLICATE** |
| `src/news/visual_plan.py:71-78 make_stock_query` | «Deprecated» | **DEAD** |
| `ai_youtube/cli/main.py`, `ai_youtube/cli/commands/content_creator.py` | 5 строк каждый | **DUPLICATE** (C01/C11) |
| `apps/*/__main__.py` (×3) | 6 строк каждый | **DUPLICATE** (C11) |

---

## 11. Local library duplicate paths

**FACT.** Три независимых пути к одной и той же локальной медиатеке:

| # | Путь | file:line | Кто вызывает | Проходит `query_adapter`? | Статус |
|---|---|---|---|---|---|
| 1 | `rank_local_assets` → `search_local_assets` | [asset_manifest_builder.py:1246-1268](../../src/news/asset_manifest_builder.py:1246) → [media_library.py:74-93](../../src/media_library.py:74) | канонический news-путь | **нет** — берёт `primary_query.split()` напрямую | **CANONICAL по факту использования** |
| 2 | `LocalLibraryStockProvider` | [providers/local_library_provider.py:21](../../src/providers/local_library_provider.py:21) | **только** [provider_diagnostics.py:125](../../src/assets/provider_diagnostics.py:125) и тесты | да (объявляет `query_languages=["en","ru"]`) | **USEFUL BUT DISCONNECTED** — не регистрируется в [registry.py:15-37](../../src/providers/registry.py:15) |
| 3 | `search_local_assets` из legacy | [video_asset_engine.py:116-135](../../src/video_asset_engine.py:116) | `pipeline.py` | нет | **LEGACY** — но содержит логику, которой нет в #1 |

**FACT.** Что есть в #3 и отсутствует в #1: резервирование слотов под
разнообразие (`min_local_diversity_per_scene`, `reserved_download_slots`,
[video_asset_engine.py:128-135](../../src/video_asset_engine.py:128)) — то есть
«не заполняй сцену тремя копиями одного локального клипа, оставь место под
новый». Это **прямо релевантно** заявленной проблеме повторяющихся визуалов.

**FACT.** Несогласованность: `query_adapter` объявляет `local_library` как
провайдера с поддержкой русского ([:53](../../src/assets/query_adapter.py:53)),
чего никогда не происходит — провайдер не создаётся, а реальный локальный поиск
идёт мимо адаптера. Это ровно тот случай, когда декларация и поведение разошлись.

**RECOMMENDATION.** PLAN-10D («регистрация локальной медиатеки») должен решать
именно это: **не добавлять четвёртый путь**, а свести #1 и #2 в один, забрав из
#3 diversity-резерв.

---

## 12. Canonical owner recommendation

### 12.1. Почему не новый сервис

**Требование §9 задания выполнено — существующие реализации проверены:**

| Кандидат | REUSE? | EXTEND? | RESTORE KNOWLEDGE? | REPLACE? |
|---|---|---|---|---|
| `query_adapter.build_scene_queries` | **да** — единственная точка контакта с провайдером, есть `ProviderQuery.source` для провенанса | **да** — нужен один новый `source`-код | — | нет |
| `VisualBrief` | **да** — схема ответа уже полная (`subject/action/place/exact_entities/must_avoid/provider_queries`) | нет | — | нет |
| `_apply_video_first_topic_briefs` | нет | нет | **да** — форма ответа и трёхуровневые `provider_queries` | **да** — заменить на общий механизм |
| `GLOSSARY` | нет — подстрочный матч **вреден** | нет | **да** — состав терминов как seed-словарь | **да** — заменить матчинг |
| `semantic_selection/query_generator` | — | — | **да** — формулировка лестницы `exact/broad/environment/atmospheric` | нет |
| `video_asset_engine.build_query_variants` | нет (чужой pipeline, умирает в PLAN-L) | нет | **да** — лестница расширения и diversity-резерв | нет |

**Вывод (INFERENCE).** Новый `TranslatorService` или `SearchEngine` **не нужен и
вреден** — он станет третьей реализацией. Нужен **один новый источник
`ProviderQuery`** внутри существующего владельца.

### 12.2. Целевая схема

```
RU-тема (intent)
  → visual_planning: SceneVisualPlan + VisualSearchIntent(requires_translation)   [СУЩЕСТВУЕТ]
  → VisualBrief как носитель провайдерского языка                                 [СУЩЕСТВУЕТ, никто не заполняет]
        ├─ уровень 1: brief автора (--visual-briefs)                              [СУЩЕСТВУЕТ]
        ├─ уровень 2: детерминированная адаптация intent → EN                     [НУЖНО: заменяет GLOSSARY]
        └─ уровень 3: model-адаптация под approval boundary                       [ОПЦИЯ, не в первом слайсе]
  → query_adapter.build_scene_queries                                             [СУЩЕСТВУЕТ]
  → ProviderQuery(source="intent_adaptation_offline" | "intent_adaptation_model") [ОДИН новый код]
  → providers → candidates → semantic_selection → completion                      [СУЩЕСТВУЕТ]
```

### 12.3. Изменения — по требуемому формату

---

**Изменение 1 — источник английских терминов для произвольной темы**

- **PROBLEM.** Для темы вне hardcode английский запрос неоткуда взять.
- **EVIDENCE.** §5.2: `ice researchers` / `station` / 25 из 30 `skipped`;
  контроль orca — 4 корректных запроса. [query_adapter.py:329-367](../../src/assets/query_adapter.py:329).
- **CURRENT OWNER.** `GLOSSARY` + `_glossary_terms` ([query_adapter.py:62-79, 383-394](../../src/assets/query_adapter.py:62)).
- **TARGET OWNER.** `src/assets/query_adapter.py` — новый уровень между
  `_explicit_provider_queries` и `_english_queries`.
- **REUSE.** `ProviderQuery.source`; `VisualBrief.provider_queries` как формат;
  состав терминов из `GLOSSARY`; лестница из `semantic_selection/query_generator`;
  трёхуровневая структура из orca-hardcode.
- **DELETE.** Подстрочный матчер `_glossary_terms`; `_apply_video_first_topic_briefs`
  вместе с [test_script_engine_pipeline.py:141](../../tests/test_script_engine_pipeline.py:141).
- **TESTS.** См. §14, T1-T5.
- **RISK.** Средний. Митигация: fail-closed сохраняется — при неуверенности
  по-прежнему `query_translation_required`, а не догадка. Это **уже** правильное
  поведение модуля, оно не меняется.
- **EXPECTED PRODUCT EFFECT.** Произвольная русская тема получает те же 3-4
  осмысленных английских запроса на сцену, что сегодня получают только косатки.

---

**Изменение 2 — прекратить ложные глоссарные срабатывания**

- **PROBLEM.** `лед` ⊂ «исследователи» → весь ролик ищется как `ice researchers`.
- **EVIDENCE.** §5.2, проверено исполнением. [query_adapter.py:391-393](../../src/assets/query_adapter.py:391).
- **CURRENT OWNER / TARGET OWNER.** Тот же модуль.
- **REUSE.** Существующий `_terms`/`_english_only`.
- **DELETE.** Ничего; заменяется матчинг (границы слова + нормализация).
- **TESTS.** T2.
- **RISK.** Низкий. Изолированная функция, два вызова.
- **EXPECTED PRODUCT EFFECT.** Прекращается отправка запросов не по теме —
  худшая из наблюдаемых форм отказа, потому что она выглядит как успех.

---

**Изменение 3 — не выбрасывать английские запросы вместе с русскими**

- **PROBLEM.** `source_is_latin` — свойство набора, а не элемента; один русский
  `primary_query` блокирует уже готовую английскую строку.
- **EVIDENCE.** §5.2, `legacy_broad_query` не доставлен ни разу.
  [query_adapter.py:158-160](../../src/assets/query_adapter.py:158).
- **CURRENT OWNER / TARGET OWNER.** Тот же модуль.
- **REUSE.** `_CYRILLIC_RE` уже есть.
- **DELETE.** После изменения 1 — сам `legacy_broad_query`
  ([legacy_format.py:84-100, 161-164](../../src/content/visual_planning/legacy_format.py:84)),
  чтобы четыре константы не заняли место настоящих запросов.
- **TESTS.** T3; переписать [test_visual_planning.py:442](../../tests/test_visual_planning.py:442).
- **RISK.** Низкий, но **порядок важен**: удалять `legacy_broad_query` **только
  после** изменения 1, иначе на переходный период покрытие упадёт до нуля.
- **EXPECTED PRODUCT EFFECT.** Уже написанные английские альтернативы доходят.

---

**Изменение 4 — честный topic-режим**

- **PROBLEM.** Тема молча превращается в шесть шаблонных фраз со статусом `passed`.
- **EVIDENCE.** §5.1, §9.1, §9.3.
- **CURRENT OWNER.** [deterministic.py:150-170](../../src/content/script_engine/providers/deterministic.py:150) + [validation.py:33](../../src/content/script_engine/validation.py:33).
- **TARGET OWNER.** Те же. Плюс связка режима: `strict` → `allow_legacy_fallback=False`.
- **REUSE.** Существующий `provider_options["allow_legacy_fallback"]`;
  существующий `ScriptValidationResult`; существующие `script_metadata`.
- **DELETE.** Ничего. **Не добавлять** `content_origin` (§9.5).
- **TESTS.** T6-T8.
- **RISK.** Низкий по коду, **заметный по UX**: без изменения 5 пользователь
  теряет offline-путь. Выполнять вместе.
- **EXPECTED PRODUCT EFFECT.** Один и тот же вход перестаёт давать одинаковые
  видео под видом успеха.

---

**Изменение 5 — перенести `--text` в канонический CLI**

- **PROBLEM.** Материал можно подать только как готовый сценарий или по сети.
- **EVIDENCE.** §9.2; [content.py:98](../../src/content_creation/commands/content.py:98) против
  [apps/news_to_short/main.py:22](../../apps/news_to_short/main.py:22); §5.4 —
  режим работает и даёт настоящий сценарий.
- **CURRENT OWNER.** `apps/news_to_short`.
- **TARGET OWNER.** `src/ai_youtube/cli/commands/` + `content_creation.request_builder`.
- **REUSE.** `INPUT_MODE_TEXT` и `resolve_source_kind` уже это поддерживают
  ([script_generator.py:50-54](../../src/news/script_generator.py:50)) — новый код
  на уровне движка **не нужен**.
- **DELETE.** После переноса — `apps/news_to_short/` целиком.
- **TESTS.** T9.
- **RISK.** Низкий.
- **EXPECTED PRODUCT EFFECT.** Честный отказ из изменения 4 получает работающую
  альтернативу, не требующую сети.

---

**Изменение 6 — один реестр провайдеров**

- **PROBLEM.** Пять расходящихся списков; `local_library` объявлен и не создаётся.
- **EVIDENCE.** §10.3, §11.
- **TARGET OWNER.** `src/providers/registry.py`.
- **REUSE.** `ProviderCapabilities.query_languages` уже перекрывает таблицу
  ([query_adapter.py:133-138](../../src/assets/query_adapter.py:133)) — то есть
  механизм «capabilities важнее таблицы» **уже есть**, таблица может стать
  fallback-ом для неизвестных имён.
- **DELETE.** `PROVIDER_QUERY_LANGUAGES` как источник правды для
  зарегистрированных провайдеров.
- **RISK.** Средний — трогает routing. **Не в одном слайсе с изменениями 1-3.**
- **EXPECTED PRODUCT EFFECT.** Косвенный; убирает класс расхождений.

### 12.4. Что создавать НЕ нужно

- **Не нужен** `TranslatorService` / `SearchEngine` / `QueryOrchestrator`.
- **Не нужен** второй словарь completion-состояний — `assets/completion/modes.py`
  остаётся владельцем.
- **Не нужно** поле `content_origin` — §9.5.
- **Не нужен** LLM в research ради «наличия AI» — §9.5, п.4.
- **Не нужен** четвёртый путь к локальной медиатеке — §11.

---

## 13. Cleanup manifest

**Ничего не удалено. Это план, а не действие.**

| Path / symbol | Current status | Callers | Valuable knowledge | Target | Action | Gate |
|---|---|---|---|---|---|---|
| `src/assets/query_adapter.py::GLOSSARY` + `_glossary_terms` [:62,:383](../../src/assets/query_adapter.py:62) | активен, даёт ложные срабатывания | `_english_queries` | состав терминов как seed | `query_adapter` | **MIGRATE THEN DELETE** | после изменения 1 |
| `src/news/script_generator.py::_apply_video_first_topic_briefs` [:115](../../src/news/script_generator.py:115) | активен, hardcode на orca | `build_script:108` | форма ответа, трёхуровневые queries, `must_avoid` | общий адаптер intent→EN | **MIGRATE THEN DELETE** | после изменения 1 |
| `tests/test_script_engine_pipeline.py:141-157` | фиксирует hardcode | — | — | — | **DELETE** | вместе с предыдущим |
| `src/content/visual_planning/legacy_format.py::legacy_broad_query` [:84](../../src/content/visual_planning/legacy_format.py:84) | **не доставляется ни разу** | `scene_to_legacy:161`, `visual_plan.py:78` | нет | — | **DELETE** | **только после** изменения 1 |
| `src/news/visual_plan.py::make_stock_query` [:71](../../src/news/visual_plan.py:71) | deprecated-обёртка | 0 production | нет | — | **DELETE** | вместе с предыдущим |
| `tests/test_visual_planning.py:442-445` | проверяет наличие broad в JSON | — | идея «покрытие не должно упасть» | тест доставки | **MIGRATE THEN DELETE** | вместе |
| `src/assets/semantic_selection/query_generator.py` [:6](../../src/assets/semantic_selection/query_generator.py:6) | питает envato + отчёты | 5 мест | лестница `exact→broad→environment→atmospheric` | `query_adapter` | **MIGRATE THEN DELETE** | после того, как лестница переедет |
| `query_generator._animal_category` [:39](../../src/assets/semantic_selection/query_generator.py:39) | hardcode `whale` | `generate_queries` | нет | — | **DELETE** | вместе с модулем |
| `src/video_asset_engine.py::build_query_variants` [:225](../../src/video_asset_engine.py:225) | legacy, живой | `asset_finder` ← `pipeline.py` | **лестница расширения** | knowledge → `query_adapter` | **MIGRATE THEN DELETE** | **PLAN-L0**, затем L3 |
| `src/video_asset_engine.py:116-135` diversity-резерв | legacy, живой | там же | **резервирование слотов под разнообразие** | knowledge → PLAN-10D | **MIGRATE THEN DELETE** | **PLAN-L0**, затем L3 |
| `content/**/*.json` `visual_keywords` | входные данные | legacy pipeline | **доказательство модели «EN-ключи отдельным полем»** | ADR/registry | **MIGRATE KNOWLEDGE** | **PLAN-L0** |
| `src/providers/local_library_provider.py` [:21](../../src/providers/local_library_provider.py:21) | не зарегистрирован | diagnostics + тесты | контракт провайдера для медиатеки | `providers/registry` | **EXTEND** (зарегистрировать) или MIGRATE THEN DELETE | **PLAN-10D** |
| `query_adapter::PROVIDER_QUERY_LANGUAGES` [:43](../../src/assets/query_adapter.py:43) | 9 имён против 5 создаваемых | `provider_query_languages` | — | `ProviderCapabilities` | **EXTEND** (fallback для неизвестных) | изменение 6 |
| `apps/news_to_short/` | свой argparse, обходит `create_content` | docs, `__main__` | **`--text` / `--text-file`** | канонический CLI | **MIGRATE THEN DELETE** | изменение 5 |
| `apps/youtube_pipeline/`, `apps/*/__main__.py` | wrappers | — | нет | — | **DELETE** | PLAN-L4 / C11 |
| `src/content_creation/{cli,fullscreen_voiceover_use_case,story_card_use_case}.py` | re-export | тесты, docs | нет | canonical | **DEFER** | C02/C03, вне этого слайса |
| `src/news/asset_manager.py::build_assets_manifest` [:64](../../src/news/asset_manager.py:64) | facade | тесты | нет | `asset_manifest_builder` | **DEFER** | вне этого слайса |
| `src/assets/query_adapter.py` (модуль) | canonical | 2 | — | — | **KEEP + EXTEND** | — |
| `src/content/visual_planning/brief.py` | canonical схема | планировщик | — | — | **KEEP** | — |
| `src/assets/completion/` | canonical readiness | — | — | — | **KEEP** | не трогать |

---

## 14. Exact tests required for implementation

**RECOMMENDATION.** Минимальный набор, который делает оба дефекта невозможными
повторно. Формат — существующий `unittest`, все офлайн.

### CRITICAL-1

- **T1 — «произвольная тема доходит до провайдера».** Три темы из §5 (вороны,
  солнечная станция, канал в пустыне) + orca как контроль. Для каждой:
  `len(unique_ok_queries) >= 2` и хотя бы один запрос содержит термин, связанный
  с темой. Файл: новый `tests/test_intent_language_adaptation.py`.
- **T2 — «глоссарь не даёт ложных срабатываний».** `"Исследователи связывают…"`
  **не** порождает `ice`. Явный regression-тест на `лед` ⊂ «исследователи».
- **T3 — «английская альтернатива не выбрасывается вместе с русской».** Сцена с
  русским `primary_query` и английским `alternative_queries[0]`: английский
  доставлен, русский — нет.
- **T4 — «морфология не теряет термин».** «пустыню», «пустыни», «пустыней» →
  `desert`.
- **T5 — «fail-closed сохранён».** Тема без единого распознаваемого термина →
  `STATUS_TRANSLATION_REQUIRED`, а **не** выдуманный перевод. Это защита от того,
  чтобы изменение 1 не превратилось в угадывание. Расширяет существующий
  [test_visual_retrieval_repair.py:232](../../tests/test_visual_retrieval_repair.py:232).

### CRITICAL-2

- **T6 — «strict не подставляет шаблон молча».** `--input-mode topic` в strict →
  блокирующий статус, `script_provider != "legacy_template"`, сообщение называет
  альтернативы. Заменяет [test_script_engine.py:286](../../tests/test_script_engine.py:286).
- **T7 — «шаблон доступен только явно».** Тот же вход в template/draft-режиме →
  `legacy_template` + `fallback_reason` в metadata + **не** `publish_ready`.
- **T8 — «происхождение сценария видно в валидации».** `script_validation`
  перестаёт быть `passed` при `fallback_provider == "legacy_template"` в strict.
- **T9 — «канонический CLI принимает исходный текст».** `--input-mode source_text`
  даёт `deterministic_local`, ≥5 сцен, ноль шаблонных литералов
  («Наблюдение выглядит простым», «самый интересный вопрос остается открытым»).

### Общие

- **T10 — характеризация до изменения.** Зафиксировать текущее поведение
  (10/50/10 вызовов, строки `ice researchers`/`station`) как characterization-тест
  **до** правки, чтобы диффы были доказуемы. Это требование
  `characterization-first` из плана.
- **T11 — «ни один тест не ходит в сеть».** Существующий `network_guard`
  применён к новым тестам.

---

## 15. Minimal execution-plan delta

**Планы не изменялись.** Ниже — что следует изменить отдельным governance-слайсом.

### 15.1. Подтверждено

| Утверждение плана | Статус |
|---|---|
| `src/assets/completion/` — не дыра, canonical owner | **подтверждено** — в пробе он корректно пометил все сцены `missing` |
| дыра выше по потоку, в генерации запросов | **подтверждено** |
| PLAN-9B «снять topic-hardcodes» | **подтверждено, hardcode найден** — но не там, где указано |
| PLAN-10D «регистрация локальной медиатеки» | **подтверждено и усилено** — §11 показывает три пути вместо одного |
| PLAN-L0 покрывает «20 движков корня `src/`» и `content/` | **подтверждено** — `video_asset_engine` и task JSON попадают в salvage |

### 15.2. Опровергнуто / требует исправления

| # | Что | Почему | Минимальная правка |
|---|---|---|---|
| 1 | **PLAN-9B allowed zone = `src/assets/semantic_selection/query_generator.py`** ([план:1348](../current/PROJECT_EXECUTION_PLAN.md:1348)) | этот модуль **не участвует** в формировании запросов к remote-провайдерам; реальный владелец — `src/assets/query_adapter.py` (§2, §10.1) | заменить зону на `src/assets/query_adapter.py` + его тесты; `query_generator.py` оставить как источник знания о лестнице |
| 2 | **PLAN-9B «снять topic-hardcodes»** без адреса | hardcode находится в `src/news/script_generator.py:115-190`, вне зоны 9B | добавить `src/news/script_generator.py` в зону 9B **или** вынести отдельным пунктом |
| 3 | **PLAN-9A перед PLAN-9B** | best-so-far persistence сохраняет лучший результат из `ice researchers` — сохранять нечего | **9B перед 9A**; persistence осмысленна после того, как появятся кандидаты |
| 4 | **CRITICAL-2 не имеет владельца в плане** | ни один PLAN-ID не покрывает topic → template | использовать **существующий** PLAN-9B как «query truth» и добавить один пункт в PLAN-11 (multi-topic evidence), **или** один новый ID `PLAN-9B0`. Новый P0 **не требуется** |
| 5 | **PLAN-9B «лестница запросов»** описана до синонимов и альтернативных названий | без источника английских слов лестница расширяет ноль | предварить лестницу пунктом «источник провайдерского языка» — это и есть §12.3 изменение 1 |

### 15.3. Отсутствующие записи cleanup registry

**FACT.** В [CLEANUP_REGISTRY.md](../current/CLEANUP_REGISTRY.md) нет ни одной
записи про: `query_adapter`, `GLOSSARY`, `legacy_broad_query`,
`_apply_video_first_topic_briefs`, дублирование генераторов запросов,
дублирование путей к локальной медиатеке, пять реестров провайдеров.
Кандидаты в новые записи — таблица §13.

### 15.4. Оценка объёма

**INFERENCE.** Ни один пункт §12.3 не требует нового top-level модуля, новой
persisted-схемы или сетевого вызова. План **не нужно увеличивать** — нужно
исправить две allowed zone, поменять местами 9A и 9B и добавить ~15 строк
registry.

---

## 16. What should be deleted after migration

**Строго после того, как замена работает и её тесты зелёные:**

1. `GLOSSARY` + `_glossary_terms` ([query_adapter.py:62-79, 383-394](../../src/assets/query_adapter.py:62)) — после изменения 1 (термины переносятся, матчер удаляется).
2. `_apply_video_first_topic_briefs` ([script_generator.py:115-190](../../src/news/script_generator.py:115)) + `tests/test_script_engine_pipeline.py:141-157` — после изменения 1.
3. `legacy_broad_query` ([legacy_format.py:84-100, 161-164](../../src/content/visual_planning/legacy_format.py:84)) и `make_stock_query` ([visual_plan.py:71-78](../../src/news/visual_plan.py:71)) — **после** 1 и 3, не раньше.
4. `src/assets/semantic_selection/query_generator.py` целиком, включая `_animal_category` — после переноса лестницы и перевода пяти callers.
5. `apps/news_to_short/` — после изменения 5.
6. `PROVIDER_QUERY_LANGUAGES` как источник правды — после изменения 6.
7. `src/video_asset_engine.py`, `src/asset_finder.py`, `src/scene_planner.py`,
   `content/**` — в рамках **PLAN-L3/L4**, но **только после PLAN-L0**, где
   явно записаны две находки: лестница расширения и diversity-резерв.

**Не удалять ни при каких условиях в рамках этой работы:**
`src/assets/completion/`, `src/subtitles/`, `src/audio/scene_timeline.py`,
`src/production_catalog/`, `src/content/visual_planning/brief.py`,
`src/content/script_engine/providers/{deterministic,user_supplied}.py`,
`src/media_library.py`, `src/news/final_renderer.py`.

---

## 17. What should explicitly NOT be rewritten

**FACT + RECOMMENDATION.** Перечисленное проверено в этом разборе и работает
правильно. Переписывание сделает продукт хуже.

1. **Принцип fail-closed в `query_adapter`.** «Нет английских доказательств →
   не отправлять запрос» ([query_adapter.py:19-22](../../src/assets/query_adapter.py:19))
   — **правильное** решение. Догадка молча подменяет предмет видео. Чинить надо
   источник слов, а не отключать защиту. Любое предложение «просто отправлять
   русский текст в Pexels» — откат к состоянию, которое уже давало 0 результатов
   на 16 запросов у Wikimedia и NASA.

2. **`DeterministicScriptProvider`.** Проба §5.4 показала: при наличии материала
   он даёт нормальный экстрактивный сценарий. Экстрактивность — **защита от
   выдумывания фактов**, а не недостаток. Заменять его LLM «ради AI» не нужно.

3. **`LegacyTemplateScriptProvider`.** Не удалять: это эталон регрессии и
   воспроизводимость старых проектов ([legacy_template.py:1-12](../../src/content/script_engine/providers/legacy_template.py:1)).
   Менять надо **не его**, а условие его молчаливого вызова.

4. **`src/assets/completion/`.** Единственный владелец publish-readiness.
   В пробе отработал корректно. Второй словарь состояний не вводить.

5. **`VisualBrief`.** Схема уже полная и уже доказана в бою (orca-путь).
   Не расширять новыми полями до тех пор, пока существующие не начнут
   заполняться автоматически.

6. **`ScriptValidationResult` / `script_metadata`.** Существующие владельцы
   статуса и происхождения сценария. Не заводить `content_origin`.

7. **`route_providers` / `scene_strategy`.** Классификация source class в пробе
   отработала осмысленно («канал через пустыню» → `exact_location`,
   «электростанция» → `research_activity`). Проблема не в маршрутизации.

8. **Anime Factory.** Вне обоих findings. Не трогать в этой работе.

---

## Appendix A — воспроизведение проб

**FACT.** Пробы созданы вне репозитория, в session scratchpad, и в репозиторий не
попали. Состав:

| Проба | Что делает | Ключевой результат |
|---|---|---|
| `probe_canonical.py` | стадии `input…visual_plan` для трёх тем + `build_scene_queries` | таблица §5.2, строки `ice researchers` / `station` |
| `probe_modes.py` | topic vs text vs orca | §5.4 и контрольные 15 запросов на сцену для orca |
| `probe_assets.py` | стадии до `asset_search` с записывающими заглушками | 10 / 50 / 10 / 180 вызовов `search()` |
| `probe_meta.py` | дамп `script_*` полей | `script_validation.status == "passed"` при `legacy_template` |

Общие свойства: `tests/network_guard.install_network_guard()` активен,
`blocked_attempts == []`, `tempfile.TemporaryDirectory`, `download()` заглушки
поднимает исключение и ни разу не вызван, платных вызовов нет.

---

## Appendix B — сводка ответов на вопросы задания

| Вопрос | Ответ |
|---|---|
| Существует ли старая реализация поиска сейчас? | **Да** — `video_asset_engine.build_query_variants`, живая, вызывается из `pipeline.py` |
| Была ли она удалена? | Нет |
| Была ли заменена? | Функционально — да, коммитами `66b2e13` → `fc459c7`; физически — нет |
| Осталась ли дублем? | Да, один из четырёх генераторов запросов (§10.1) |
| Была ли частью legacy pipeline? | Да |
| Была ли частью `apps/news_to_short`? | Нет |
| Была ли логика внутри Codex/agent workflow, а не production-кода? | **Да** — английские `visual_keywords` в `content/**` писал автор/агент (§4) |
| Использовала ли она заранее сформированный `visual_brief`? | Не `visual_brief`, а его предшественника — `visual_keywords` в task JSON. Современный аналог — orca-hardcode |
| Работал ли совершенно другой entrypoint? | Да — `python pipeline.py --channel … --video …` (§6, вход #6) |
| Была ли какая-то из реализаций «наиболее функциональной»? | По **релевантности** — legacy documentary (английские ключи + лестница). По **покрытию** — baseline `13cc3f4` (всегда что-то возвращал). По **корректности** — текущий `query_adapter` (не врёт, но и не ищет) |
