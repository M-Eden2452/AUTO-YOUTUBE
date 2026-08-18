# Аудит тестовой системы — 2026-08-17

**HEAD:** `ca66f59f4f53c03ded818d29ff3ba3231d074b41`, ветка `governance-reset`.
**Окно измерений:** 2026-08-16 23:13 — 2026-08-17 01:4x, Windows 11, Python
3.13.13 (`.\venv\Scripts\python.exe`), tracked-дерево чистое.
**Режим:** read-only. Продуктовый код, тесты, CI, `pyproject.toml`,
`scripts/gates.py`, `docs/current/**`, frozen baselines не изменялись.
Сеть, provider search, Vision, TTS и платные вызовы не выполнялись;
`network_guard` не отключался, `AI_YOUTUBE_ALLOW_LIVE_TESTS` не ставился.

---

## 1. Итог

1. Система **здорова**: 2323 теста, 932 с, exit code 0, ноль failures, errors
   и skips. Красного нет.
2. Проблема **не в количестве тестов**. 23 теста (1 %) занимают 757.9 с —
   **84.2 %** всего времени. 71 % тестов быстрее 10 мс.
3. Главный источник медленности — **реальные вызовы ffmpeg внутри
   продуктового пути**: в самом дорогом тесте 120 subprocess-вызовов
   материализации превью дают 74.2 с из 135 с.
4. Импорт и discovery всех 137 модулей стоят **2.31 с** — 0.25 % прогона.
   Ни fixture-настройка, ни старт интерпретатора медленность не объясняют.
5. Механизм выбора тестов **уже существует и его достаточно**: вариант A
   (`-m unittest tests.<module>`) даёт 0.62–1.35 с на модуль и 1.13 с на
   слайс из шести модулей. Это в 690–1500 раз быстрее полного прогона.
6. Перестраивать каталог, вводить pytest, маркеры или карту импортов
   **не нужно**; измерения не дают им окупаемости, а карта импортов здесь
   ещё и опасна (см. §4, вариант C).
7. Реально избыточного мало: ни одного `DELETE` доказать не удалось.
   Основной резерв — не удаление тестов, а **снятие лишней работы** с
   четырёх модулей: измерено −171 с из 932 с при сохранении зелёного.
8. Быстрый суточный suite измерен: **81.3 с, 2106 тестов** (минус 10 модулей).
9. Обычный feedback уже быстрый; ускорять нужно **CI и границу пакета**,
   а не targeted-цикл.
10. Первоочередной риск не в скорости: **`script_mismatch`/`is_undecidable`
    (корень `C91`) не имеет ни одного именующего его теста** при шести
    вызывающих в продакшене.

---

## 2. Baseline и метод

Команды дословно, все выполнены из корня репозитория.

Канонический полный прогон:

```bash
PYTHONUTF8=1 PYTHONIOENCODING=utf-8 AI_YOUTUBE_ALLOW_LIVE_TESTS=0 AI_YOUTUBE_RUN_LIVE_TESTS=0 ./venv/Scripts/python.exe -B -m unittest discover -s tests -p "test_*.py"
```

Результат: `Ran 2323 tests in 932.064s`, `OK`, exit code 0, обёрточный wall
934.65 с. Failures 0, errors 0, skipped 0.

Профилирование делалось тремя временными скриптами в scratchpad
(`C:\Users\Dyma\AppData\Local\Temp\claude\...\scratchpad\`), в репозиторий
ничего не писалось:

- `mod_runner.py` — наследник `unittest.TextTestResult`, пишет
  `(duration, test.id(), outcome)` по каждому тесту;
- `driver.py` — прогоняет **каждый** из 137 модулей отдельным процессом и
  замеряет process wall;
- `measure_tiers.py` — замеряет варианты запуска настоящей командной формой.

**Одна ошибка метода зафиксирована и исправлена.** Первый инструментированный
прогон запускался как `python -B <scratchpad>/timed_runner.py`, из-за чего
`sys.path[0]` указывал на scratchpad, а не на корень: 80 loader errors,
237 errors, 610 тестов вместо 2323. Эти числа отброшены и в отчёте не
используются. В `mod_runner.py` добавлен `sys.path.insert(0, os.getcwd())`;
после починки — 0 loader errors, 0 errors, 0 failures на всех 137 модулях,
сумма 2323 теста, что сходится с каноническим прогоном.

**Оговорка о среде.** Часть лёгких read-only команд (grep, чтение файлов)
выполнялась параллельно с прогонами. Абсолютные секунды поэтому имеют
погрешность единиц процентов; ранжирование модулей и доли распределения к
ней нечувствительны. Числа сравнимы между собой внутри этого отчёта и не
являются нормативом (`PROJECT_EXECUTION_PLAN.md`, «Measurement policy»).

---

## 3. Профиль времени

### 3.1 Куда уходит время на самом деле

| Слой | Стоимость | Доля прогона |
|---|---|---|
| Старт интерпретатора | 0.05 с | ~0 |
| Импорт пакета `tests` | 0.17 с | ~0 |
| **Импорт + discovery всех 137 модулей** | **2.31 с** | **0.25 %** |
| Исполнение тел тестов | ~930 с | 99.75 % |

Проверено командой, которая грузит всё и не запускает ничего:

```bash
./venv/Scripts/python.exe -B -m unittest discover -s tests -p "test_*.py" -k nomatchxyz
```

→ 2.31 с. Независимо: `loader.discover("tests","test_*.py")` без прогона —
2.29 с.

**Вывод:** гипотезы «дорогой импорт», «дорогая fixture-настройка», «дорогой
старт процесса» опровергнуты измерением. Стоимость сосредоточена в телах
примерно двадцати тестов.

### 3.2 Распределение

| Срез | Тестов | Секунд | Доля |
|---|---|---|---|
| Топ 1 % | 23 | 757.9 | **84.2 %** |
| Топ 5 % | 116 | 828.7 | 92.0 % |
| Топ 10 % | 232 | 869.0 | 96.5 % |
| Топ 25 % | 580 | 896.3 | 99.6 % |

Медианный тест — **0.0019 с**. Тестов дольше 1 с — 38, дольше 10 с — 19.
Быстрее 10 мс — **1656 тестов (71 %)**.

По модулям: медиана **0.91 с**, 72 модуля быстрее 1 с, 45 в диапазоне 1–3 с,
8 в диапазоне 3–10 с и **12 дольше 10 с**.

### 3.3 Топ-14 модулей (отдельным процессом)

| # | Модуль | wall, с | тестов | кум. |
|---|---|---|---|---|
| 1 | `test_input_query_truth_characterization` | 178.50 | 4 | 17.5 % |
| 2 | `test_content_creation_service` | 166.13 | 28 | 33.9 % |
| 3 | `test_plan9d_current_capture` | 143.28 | 57 | 47.9 % |
| 4 | `test_plan9d_ground_truth_baseline` | 124.52 | 57 | 60.2 % |
| 5 | `test_news_to_short_delivery` | 71.84 | 4 | 67.2 % |
| 6 | `test_final_renderer_end_tail` | 58.64 | 4 | 73.0 % |
| 7 | `test_news_to_short_pipeline` | 40.47 | 9 | 77.0 % |
| 8 | `test_news_to_short_renderer` | 29.87 | 2 | 79.9 % |
| 9 | `test_news_voice_adapter` | 21.18 | 5 | 82.0 % |
| 10 | `test_claude_permission_contract` | 18.72 | 47 | 83.8 % |
| 11 | `test_check_task_scope` | 11.60 | 26 | 85.0 % |
| 12 | `test_asset_cli_wiring` | 11.30 | 7 | 86.1 % |
| 13 | `test_plan9d_retrieval_gate` | 7.70 | 29 | 86.8 % |
| 14 | `test_docs_routing_and_freshness` | 7.61 | 34 | 87.6 % |

Топ-10 = 853.2 с; **оставшиеся 127 модулей = 164.5 с** суммой отдельных
процессов.

### 3.4 Топ-6 отдельных тестов

| с | Тест |
|---|---|
| 133.03 | `test_input_query_truth_characterization…test_current_provider_dispatch_and_persisted_query_plan` |
| 65.38 | `test_plan9d_current_capture.DerivedFieldTests.test_finalize_is_idempotent` |
| 64.49 | `test_plan9d_current_capture.DerivedFieldTests.test_categories_are_recomputable_from_the_stored_pool` |
| 61.41 | `test_plan9d_ground_truth_baseline…test_todays_decision_owner_is_measured_against_the_captured_one` |
| 44.38 | `test_input_query_truth_characterization…test_topic_only_thin_input_uses_declared_draft_template_fallback` |
| 38.93 | `test_news_to_short_pipeline…test_fake_provider_no_network_pipeline_reaches_final_render_with_local_paths` |

### 3.5 Разбор самого дорогого теста (cProfile)

`test_current_provider_dispatch_and_persisted_query_plan`, 134.99 с:

| Уровень | cumtime | Доля теста |
|---|---|---|
| 3 × `create_content` (полный pipeline) | 134.86 с | 99.9 % |
| `asset_manifest_builder._prepare_visual_review` (24 вызова) | 83.99 с | 62.2 % |
| `visual_preview._create_video_preview` (120 вызовов) | 74.22 с | 55.0 % |
| `subprocess.run` (126 вызовов, ffmpeg) | 74.57 с | 55.2 % |

**Это и есть ответ «куда уходит время»: 120 реальных вызовов ffmpeg,
материализующих видео-превью кандидатов, по ~0.62 с каждый.**
`visual_preview.enabled` по умолчанию `True`
(`src/assets/visual_preview.py:851`, читается в
`src/news/asset_manifest_builder.py:698-707`), поэтому любой тест, который
гоняет полный pipeline, платит за превью, даже если превью не является его
предметом.

### 3.6 Пять изменений, дающих большую часть ускорения

Измерено, а не оценено: подмена `prepare_candidate_preview_analyses`
на no-op **в памяти** (репозиторий не менялся), все тесты остались зелёными.

| Модуль | было | стало | выигрыш | статус |
|---|---|---|---|---|
| `test_input_query_truth_characterization` (1 тест) | 133.0 с | **47.1 с** | −85.9 с | OK, 0 fail |
| `test_news_to_short_delivery` | 71.8 с | **27.5 с** | −44.3 с | OK, 4 теста |
| `test_news_to_short_pipeline` | 40.5 с | **23.5 с** | −17.0 с | OK, 9 тестов |
| `test_content_creation_service` | 166.1 с | **142.4 с** | −23.7 с | OK, 28 тестов |
| **Итого измеренного резерва** | | | **≈ −171 с** | **18 % прогона** |

Пятое изменение — не тест, а вопрос к PLAN-9D: два теста
`test_plan9d_current_capture.DerivedFieldTests` стоят 129.9 с вдвоём
(идемпотентность finalize и пересчёт категорий по сохранённому пулу). Это
replay замороженного корпуса; правомерность его удешевления — решение
владельца PLAN-9D, а не вывод этого аудита.

---

## 4. Механизм выбора тестов

### 4.1 Сравнение вариантов

**A. Уже доступное без изменений — рекомендуется.**

Измерено настоящей командной формой:

| Команда | Время |
|---|---|
| `-m unittest tests.test_semantic_asset_selection` | **0.62 с** |
| `-m unittest tests.test_subtitle_engine` | **0.68 с** |
| `-m unittest tests.test_runtime_network_boundary` | **1.00 с** |
| `-m unittest tests.test_project_rights_report` | **1.33 с** |
| `-m unittest tests.test_config_resolver` | **1.35 с** |
| шесть модулей владельца semantic-selection одной командой | **1.13 с** |
| `discover … -k rights` (грузит всё) | 3.86 с |

Цена — ноль. Риск — ноль. Против 932 с это ускорение в **690–1500 раз**.
Медианный модуль 0.91 с при накладных 0.41 с на процесс: targeted-прогон
почти целиком состоит из накладных, то есть дешевле уже некуда.

`-k` по всему discover (3.86 с) полезен, когда имя теста известно, а модуль —
нет; он всё равно импортирует все 137 модулей, но это стоит 2.31 с.

**B. Тиры каталогами** (`discover -s tests/<tier>`). Цена: перенос 137 файлов
(48 852 строки) + 7 не-тестовых хелперов (`network_guard.py`,
`path_identity.py`, четыре `plan9d_*.py`, `__init__.py`) + каталог
`tests/data/`. `tests/__init__.py` ставит network guard и fake-credential до
любого импорта — при разбиении на подкаталоги это нужно воспроизвести в
каждом тире либо оставить общий пакет-родитель; ошибка здесь снимает guard
молча. CI пришлось бы менять. Выгода поверх A — нулевая: A уже даёт 0.6–1.3 с.
**Не окупается.** План отдельно фиксирует, что физический restructure
`tests/` не является prerequisite product work
(`PROJECT_EXECUTION_PLAN.md:2307+`).

**C. Карта «изменённый файл → его тесты» по графу импортов.** Построена
статически (AST, 137 модулей): медиана 3 продуктовых модуля на тест, среднее
4.2. Граф разрежен, то есть технически вариант рабочий. **Но он даёт ложный
green именно здесь:** 10 модулей не импортируют ни одного продуктового модуля
вообще, потому что запускают продукт через `subprocess` —
`test_project_foundation_cli` (`sys.executable -m src.project_foundation.cli`),
`test_stage4_canonical_cli` (`-m ai_youtube`), `test_apps_structure`,
`test_reproducibility_contract`, четыре `test_plan9d_*`, `test_asset_cli_wiring`,
`test_moss_voice_tester`, `test_test_network_guard`. У них нет рёбер к коду,
который они защищают, — селектор по графу их не выберет и покажет зелёный.
Плюс это новый чекер, требующий owner decision. **Не рекомендуется.**

**D. pytest поверх существующих `TestCase`.** Дал бы `--durations`, маркеры и
impact-выбор. Но: 2323 теста в 137 модулях, 0 конфигурации, `tests/__init__.py`
выполняет критичный side effect до импорта, 27 мест завязаны на
`inspect.signature`. Главное — окупаемости нет: A уже даёт 0.6–1.3 с, а
`--durations` заменяется тридцатью строками временного раннера (что и сделано
в этом аудите). **Отдельное решение владельца, из измерений не следует.**

**E. Гибрид.** Единственная его полезная часть — не механизм выбора, а
**второй tier для CI** (§4.3). Он не требует ни B, ни C, ни D.

### 4.2 Рекомендация

**Ничего перестраивать не нужно. Вариант A достаточен; зафиксировать его как
явную практику и добавить один быстрый tier в CI.**

Это опирается на замеры, а не на вкус: единственная величина, которая могла
бы оправдать B/C/D — стоимость выбора подмножества — измерена и равна
0.41 с накладных на модуль при импорте всего дерева за 2.31 с.

Отдельно: §7–§10 «Execution protocol» в `PROJECT_EXECUTION_PLAN.md`
**уже описывают** targeted-политику и перечисляют, когда `full` обязателен.
Отдельного нового документа-правила заводить не нужно и нельзя
(`AGENTS.md`, запрет на новый governance-механизм).

### 4.3 Что запускать после изменения

Команды даны в форме, готовой к вставке; префикс везде
`.\venv\Scripts\python.exe -B -m unittest`.

| Тип изменения | Обязательные тесты | Опционально | Нужен ли full | Почему |
|---|---|---|---|---|
| pure helper | модуль владельца | — | нет | лист без вызывающих; 0.6–1.3 с |
| semantic ranking / selection | `tests.test_semantic_asset_selection tests.test_semantic_slot_decisions tests.test_semantic_decision_policy tests.test_visual_retrieval_repair tests.test_visual_retrieval_regression tests.test_metadata_evidence_repair` (**1.13 с**) | `tests.test_plan9d_retrieval_gate` (7.7 с) | **да, на границе пакета** | меняется предмет замороженного корпуса PLAN-9D |
| query adapter | `tests.test_visual_query_expansion tests.test_slot_aware_retrieval` | `tests.test_input_query_truth_characterization` (178 с) | нет | дорогой модуль — на границу пакета |
| rights policy | `tests.test_project_rights_report tests.test_rights_review_preservation tests.test_rights_status_vocabulary` | `tests.test_evidence_bundle` | **да** | HIGH по `AGENTS.md` (права) |
| network guard | `tests.test_runtime_network_boundary tests.test_test_network_guard` | `tests.test_asset_foundation_http_download` | **да** | HIGH (сеть) |
| paid boundary | `tests.test_claude_permission_contract` (18.7 с) `tests.test_tts_env_credential_isolation` | `tests.test_content_creation_service` (166 с) | **да** | HIGH (деньги) |
| persisted schema / resume | `tests.test_project_naming_and_resume tests.test_asset_search_resume_fingerprint tests.test_news_stage_idempotency tests.test_project_repository` | `tests.test_autonomous_completion_pipeline` | **да** | HIGH (persisted schema) |
| renderer | `tests.test_final_renderer_atomic_output tests.test_scene_timeline` | `tests.test_final_renderer_end_tail` (58.6 с) `tests.test_news_to_short_renderer` (29.9 с) | на границе пакета | реальный ffmpeg — дорого, но это и есть предмет |
| subtitles | `tests.test_subtitle_engine` (0.68 с) `tests.test_subtitle_pipeline_integration` | — | нет | локальный владелец |
| CLI | `tests.test_stage4_canonical_cli tests.test_cli_internals_contract` | `tests.test_project_foundation_cli` | на границе пакета | subprocess, guard не наследуется |
| config | `tests.test_config_resolver` (1.35 с) `tests.test_channel_profiles` | — | нет | но см. §7.5 — ключ без потребителя тест не ловит |
| docs-only | `.\venv\Scripts\python.exe -m tools.qa.check_agent_docs` + `tests.test_docs_routing_and_freshness tests.test_stage2_agent_onboarding` | — | нет | §10 протокола |
| cleanup / refactor | модули всех затронутых владельцев | — | нет, если контракт не менялся | characterization-first по `AGENTS.md` |
| multi-owner change | все модули владельцев + | | **да** | §8 протокола: shared contract |

`full` = канонический прогон из §2, 932 с.

### 4.4 CI: один job или два

**Оставить один блокирующий job и добавить второй, быстрый — но не заменять
им первый.**

Причина конкретная: `.github/workflows/offline-tests.yml` объявляет
`timeout-minutes: 20`, а локальный прогон уже занимает **15.5 минуты**.
Запас — 4.5 минуты на машине, которая ставит `ffmpeg-full` и медленнее
локальной. Это не гипотеза о будущем: 19 тестов дольше 10 с растут вместе с
продуктом, и следующая пара таких тестов упрёт job в таймаут. Прежнее
измерение в плане — 1441 тест / 231.8 с; сейчас 2323 / 932 с: тестов +61 %,
времени **+302 %**.

Обязано остаться блокирующим всегда: полный suite, `scripts/gates.py` и
`tools.qa.check_agent_docs`.

**Чем опасен selective CI именно здесь.** Тремя вещами, и все три
подтверждены измерением, а не общими соображениями:

1. **Нет рёбер у subprocess-тестов.** 10 модулей не импортируют продукт (§4.1 C).
   Selective CI по diff их не выберет.
2. **Guard не наследуется дочерним процессом.** `tests/network_guard.py`
   живёт в test-пакете; на этом HEAD **7** модулей порождают Python-child
   (`test_asset_cli_wiring`, `test_check_task_scope`,
   `test_fullscreen_voiceover_application_boundary`,
   `test_production_catalog_foundation`, `test_project_foundation_cli`,
   `test_stage4_canonical_cli`, `test_story_card_project_integration`).
   Если такой модуль не выбран, отсутствует и единственная проверка,
   которая ходит этим путём.
3. **Дешёвое ≠ неважное.** 71 % тестов быстрее 10 мс; экономия от их
   пропуска — единицы секунд, а потеря защиты — полная. Ускорение CI ценой
   ложного green не рассматривается, а здесь оно ничего и не покупает.

Быстрый tier измерен: **81.3 с, 2106 тестов, 0 failures** — полный discover
минус десять модулей из §3.3. Минус пять модулей — 243.8 с, 2173 теста.

### 4.5 Политика по дорогим тестам

Правило «>10 секунд ⇒ не targeted» не используется: длительность — один
сигнал из нескольких.

- **Дорогой тест обязателен**, когда его предмет и есть дорогая операция:
  `test_final_renderer_end_tail` (58.6 с) проверяет, что аудио и музыка
  доходят до конца видео — это проверяется только реальным рендером.
- **Достаточно границы пакета** для дорогих тестов, чей предмет — сквозной
  сценарий: `test_content_creation_service` (166 с),
  `test_news_to_short_delivery` (71.8 с).
- **Только CI** — для двух тестов `plan9d_current_capture` (129.9 с вдвоём):
  это replay замороженного корпуса, локально он не меняется от слайса к слайсу.
- **Заменяется дешёвым contract-тестом**, когда дорогая работа предметом не
  является: измерено на `test_input_query_truth_characterization` — превью
  не участвуют ни в одном assert, а стоят 65 % теста (§3.6). Acceptance при
  этом остаётся отдельно, дорогим и в CI.

---

## 5. Ожидаемое было → стало

Только измеренное или прямо выведенное из измеренного.

| Сценарий | Было | Стало | Основание |
|---|---|---|---|
| Проверка одного владельца | 932 с (полный) | **0.62–1.35 с** | замер §4.1 |
| Слайс semantic-selection | 932 с | **1.13 с** | замер §4.1 |
| Быстрый суточный suite | — | **81.3 с / 2106 тестов** | замер |
| Полный suite после снятия превью там, где они не предмет | 932 с | **≈ 761 с** | −171 с измерено, §3.6 |
| Запас CI до таймаута | 4.5 мин | ≈ 7.3 мин | 20 мин − 12.7 мин |
| Импорт всего дерева | — | 2.31 с | замер |

Числа «стало» для полного suite — следствие четырёх измеренных подмен, а не
план работ: право на изменение даёт владелец, не этот отчёт.

---

## 6. Инвентарь по четырём каноническим классам

Классификация — только в четырёх классах
`PROJECT_EXECUTION_PLAN.md:2296-2307`. **Полная поимённая классификация 137
модулей в этой сессии не выполнена** (§15). Ниже — агрегат с точными
величинами там, где они проверены поимённо.

| Класс | Модулей | Основание |
|---|---|---|
| CHARACTERIZATION | **7** поимённо | `test_cli_internals_contract`, `test_content_creation_service_internals_contract`, `test_input_query_truth_characterization`, `test_legacy_pipeline_internals_contract`, `test_semantic_visual_evaluation_internals_contract`, `test_stage1_characterization`, `test_wizard_internals_contract` |
| LEGACY ANCHOR | **8** поимённо | строки раздела «Accidental invariants» |
| ARCHITECTURE INVARIANT | ≥ 2 поимённо + ~19 по признаку | `test_asset_import_boundaries`, `test_capability_consistency` названы в реестре; ещё ~19 модулей носят в имени `boundary/structure/layout/consistency/gate` |
| PRODUCT CONTRACT | остальные ~101 | остаток; поимённо не проверен |

**Выброс, который важнее агрегата.** Класс объявлен в плане, но **в самих
модулях почти не записан**: заголовок `Test classification:` есть только в
**10 файлах из 137** (7 %). Из семи characterization-модулей канонический
заголовок «Protects / Does not prove» несёт **один** —
`test_legacy_pipeline_internals_contract`.

Второй выброс: **12 модулей** (27 вхождений) замораживают сигнатуры и
исходники через `inspect.signature` / `inspect.getsource`. Четыре из них —
`*_internals_contract` — состоят из этого почти целиком, то есть по существу
являются LEGACY ANCHOR, но в реестре из них числится только
`test_legacy_pipeline_internals_contract`.

---

## 7. Находки

### 7.1 Fixture risk (приоритет)

**F1 — HIGH. Корневая причина `C91` не имеет ни одного именующего её теста,
и существующие fixtures структурно неспособны её поймать.**

Доказательство:

- `script_mismatch` (`src/assets/semantic_selection/evidence.py:189-191`) —
  это XOR по наличию кириллицы:
  `bool(CYRILLIC_RE.search(concept)) != bool(CYRILLIC_RE.search(text))`.
- `is_undecidable` (`:413-417`) спрашивает его по `self.text` — склейке полей,
  тогда как балл берёт `semantic_inflection_score` по `self.fields` (`:428-436`).
- Вызывающих в продакшене **шесть**: `decision.py:310,363,378`,
  `candidate_ranker.py:345,633` (+ реэкспорт `:641`).
- Во всём каталоге `tests/` **ноль** упоминаний `script_mismatch` и ноль
  упоминаний `is_undecidable` как предмета проверки. Совпадения по слову
  `undecidable` относятся к другому понятию — `undecidable_fields` (пофайловая
  неопределённость в выводе ранкера) и словарю PLAN-9D.
- XOR по определению даёт `False`, когда обе строки одного письма. Поэтому
  fixture, где и запрос, и метаданные латиницей, **не может** активировать
  ветку ни при каком наборе значений. Измерено: из 137 модулей **53 не
  содержат ни одного кириллического символа**, и в их числе — весь ядровой
  слой решения: `test_semantic_decision_policy`, `test_semantic_visual_integration`,
  `test_media_selection_policy`, `test_semantic_visual_evaluation`,
  `test_news_to_short_assets`, `test_manual_asset_replacement`.

Это ровно тот класс, который `C91` описывает числами 7.5 против 78.3: дефект
проявляется только на **смешанном** письме, а слой проверяется одноязычными
fixtures. Вердикт: `UNPROVEN` для существующих тестов (они не ложны, они не
про это) + новый тест в §7.7.

**F2 — MEDIUM. 53 модуля без кириллицы — это не находка сама по себе.**
Отличать «fixture намеренно минимален» от «fixture слепа к классу ошибки»
нужно по предмету: у `test_asset_foundation_http_download` язык метаданных
предметом не является, у `test_semantic_decision_policy` — является.
Поимённый разбор всех 53 не выполнен (§15).

### 7.2 Ценность и дубликаты

**Ни одного `DELETE` доказать не удалось; проверок мутацией не проводилось.**
Все кандидаты ниже — `UNPROVEN` или мягче. Это не «дубликатов нет», а
«дубликаты не доказаны в рамках бюджета этой сессии» (§15).

Единственная измеренная избыточность — **не текста, а работы**: четыре
модуля выполняют материализацию превью, не проверяя её (§3.6). Вердикт —
`REWRITE TO CONTRACT` для `test_input_query_truth_characterization`
(85.9 с при неизменных assert) и `MOVE OUT OF DEFAULT SUITE` для двух тестов
`plan9d_current_capture`.

### 7.3 Жизненный цикл characterization

| Модуль | Породивший переход | Завершён? | Вердикт |
|---|---|---|---|
| `test_input_query_truth_characterization` (178.5 с) | PLAN-9B-1 (post-fix) + PLAN-9B-4 (pre-fix) | **частично**: собственный docstring делит модуль на post-fix контракт и остаточную pre-fix характеризацию | `CONVERT TO REGRESSION` для post-fix части; удешевить по §3.6 |
| `test_legacy_pipeline_internals_contract` | 6F/8D | да, реестр: «своё назначение выполнили» | `RETIRE` вместе с носителем, gate PLAN-L3/L4 |
| `test_stage1_characterization` | этап 1 rescue | не проверено | `UNPROVEN` |
| `test_cli_internals_contract` | не назван в файле | не проверено | `UNPROVEN`; по содержанию — сигнатурный снимок |
| `test_wizard_internals_contract` | не назван в файле | не проверено | `UNPROVEN`; сигнатурный снимок |
| `test_content_creation_service_internals_contract` | не назван | не проверено | `UNPROVEN`; сигнатурный снимок |
| `test_semantic_visual_evaluation_internals_contract` | не назван | не проверено | `UNPROVEN`; 5 вхождений `inspect` |

Общая находка: **шесть из семи characterization-модулей не называют
породивший их переход**, поэтому «отработал ли тест» по ним нельзя решить
чтением — только раскопками. Это и есть причина, по которой такие модули
живут дольше своего рефакторинга.

### 7.4 Owner-карта и недотестированные границы

Построен статический граф импортов (AST, 137 модулей → 296 продуктовых).

- Медиана 3 продуктовых модуля на тест, среднее 4.2, максимум 18.
- Наибольший blast radius: `src.assets` — 50 тестов, `src.news` — 48,
  `src.content_creation` — 29, `src.audio` — 27, `src.news.models` — 19,
  `src.assets.semantic_selection` — 18.
- 91 продуктовый модуль не импортируется ни одним тестом напрямую.
  **Важная оговорка:** это не «не покрыт» — большинство достижимо
  транзитивно через `__init__` пакета (пример: `src.config_resolver.resolver`
  не импортируется по имени, но `tests/test_config_resolver.py` вызывает
  `resolve_config` из пакета в 46 тестах). Число говорит о **точности
  адресации**, а не о покрытии.

**Критичные контракты без защиты, ранжировано:**

| Приоритет | Контракт | Состояние |
|---|---|---|
| **HIGH** | `script_mismatch` / `is_undecidable` — примитив доказуемости отбора | 6 вызывающих, 0 именующих тестов (§7.1) |
| **MEDIUM** | `assets.allow_unknown_rights` как настройка канала | ключ мёртв (§7.5); сами права защищены отдельно |
| **LOW** | сигнатурные снимки как замена контракту | 12 модулей (§6) |

**Хорошая новость, которую стоит записать явно:** деньги, сеть, права,
учётные данные и resume защищены **лучше всего** и отдельными модулями —
`test_claude_permission_contract` (47 тестов), `test_project_rights_report`,
`test_rights_review_preservation`, `test_rights_status_vocabulary`,
`test_runtime_network_boundary`, `test_test_network_guard`,
`test_tts_env_credential_isolation`, `test_semantic_brief_project_budget`.
51 модуль упоминает права, 52 — платность, 54 — resume/schema.
**Недотестирован не слой безопасности, а слой смысла.**

### 7.5 Config-контракты

`C83` — не единичный случай, а класс. Измерено: в пяти
`config/channels/*/channel_config.json` **76 различных листовых ключей**, из
них **14 (18 %) не встречаются ни разу** в `src/`, `tools/`, `scripts/`:

`allow_unknown_rights`, `assets_required`, `audition_max_characters`,
`audition_model_strategy`, `avoid_exaggeration`, `content_rules`,
`default_style_profile`, `distinguish_hypotheses`, `final_render_required`,
`future_paid_providers`, `niche`, `prefer_user_assets`, `script_required`,
`use_local_library`.

Самый неприятный — `allow_unknown_rights: false`
(`config/channels/nature_science_news_ru/channel_config.json:92`): по всему
репозиторию он встречается **только** в этом файле и одном архивном отчёте.
Владелец, читающий свой канал-конфиг, видит выключатель прав, которого нет.
**Права при этом обеспечиваются независимо** — `src/projects/rights.py` и
`src/assets/license_policy.py` от ключа не зависят. То есть это дефект
**поверхности настройки**, а не открытый шлюз.

**Как ловить тестом без хрупкого grep.** Не строить config-framework.
`src/config_resolver/keys.py` уже держит `keys.SETTINGS` — список настроек, у
каждой из которых «есть файл, который её несёт, или модуль, который её
читает» (docstring `src/config_resolver/__init__.py`). Дешёвое решение —
тест **внутри существующего владельца** `tests/test_config_resolver.py`:
каждый листовой ключ, реально присутствующий в `channel_config.json`, обязан
быть либо объявлен в `keys.SETTINGS`, либо перечислен в явном списке
«декларативных, никем не читаемых». Список делает мёртвый ключ видимым
решением, а не случайностью. Declared consumer, а не схема и не grep.

Оговорка: у config resolver сейчас нет продуктовых вызывающих — его
собственный docstring говорит «At this commit nothing in the pipeline uses
the resolver». Поэтому владелец ключей — вопрос владельца, а не вывод аудита.

### 7.6 Детерминизм и изоляция

Проверено фактически, состояние **хорошее**:

| Риск | Факт |
|---|---|
| `random` | **0 файлов** |
| `sleep()` | **0 файлов** |
| часы/даты (`datetime.now`/`date.today`/`time.time()`) | **1 файл** |
| `tempfile` | 98 файлов — изоляция по умолчанию |
| мутация `os.environ` | 5 файлов, все с восстановлением через `finally`; ещё 7 используют `patch.dict` |
| захардкоженные пути | 12 вхождений |
| skip-декораторы | **1** (`test_check_task_scope.py:281`, `os.name == "nt"`) |

Порядок и изоляция: полный прогон 2323 теста — 0 failures; те же 137 модулей
**по одному в отдельном процессе** — тоже 0 failures и 0 errors, суммарно
2323 теста. То есть тестов, которые проходят поодиночке и падают в общем
прогоне (или наоборот), **не обнаружено**. Flakiness не заявляется: она не
воспроизводилась.

Платность и сеть: `tests/__init__.py:14-17` до любого импорта ставит
`TEST_CREDENTIAL_ISOLATION_ENV_VAR=1`, подменяет `ELEVENLABS_API_KEY`
фальшивым значением и включает guard, который перехватывает `connect`,
`create_connection` и `getaddrinfo`, пропуская только localhost. За оба
полных прогона ни одного платного или сетевого вызова не выполнено.

**Единственная реальная дыра — не новая:** guard не наследуется
Python-дочерними процессами. На этом HEAD таких модулей **7** (перечислены в
§4.4); всего с `subprocess` — 17, остальные 10 порождают ffmpeg/ffprobe.
Реестр (`C49`) фиксирует **12** на HEAD `adcbb19` — см. §8.

### 7.7 Новые тесты

Только один, и он следует из §7.1.

| Что | Значение |
|---|---|
| **Gap** | `script_mismatch` не проверен ни одним тестом при 6 вызывающих |
| **Какой отказ предотвращает** | Кандидат с совпадением 100 по `keywords` объявляется несопоставимым из-за одного кириллического символа в заголовке; `candidate_ranker.py:307-320` обнуляет `meaning_score`, итог `final = 0.075·quality` — измеренные 7.5 против 78.3 |
| **Почему существующие не ловят** | XOR не срабатывает на одноязычном fixture; 53 модуля без кириллицы, включая весь ядровой слой решения (§7.1) |
| **Owner** | `src/assets/semantic_selection/evidence.py` (тот же, что у `C79`/`C89`/`C90`/`C91`) |
| **Слой** | unit у примитива + один case в существующем `tests/test_semantic_asset_selection.py` |
| **Стоимость** | малая: примитив чистый, fixture — две строки смешанного письма |
| **Важно** | тест фиксирует **текущее** поведение (characterization-first по `AGENTS.md`), а не желаемое; правка `C91` — отдельный слайс с приёмкой 7.5 → ≥78 |

---

## 8. Дельта к разделу «Accidental invariants»

Раздел проверен построчно на текущем HEAD.

**Устарело:**

1. `tests/test_apps_structure.py` — записано «19 строк», фактически **39**.
2. `test_documentary_visual_engine.py` — записано «(295)», фактически **348**.
3. **`test_stage2_agent_onboarding.py:19` — оба анкера сместились, а один
   уже закрыт.** Замороженной даты `today=date(2026,7,29)` в файле **нет**;
   строка 79 прямо говорит: «No frozen verification date: the checker derives
   its calendar», и `validate_repository(REPO_ROOT)` вызывается без `today`
   (`tools/qa/check_agent_docs.py:1577-1581` — `today` стал необязательным).
   Половина строки реестра **подлежит закрытию**. Точное равенство
   `REQUIRED_SKILLS` живо, но переехало на **строку 166**.
4. **`test_stage2_agent_onboarding.py:26` описан неверно.** Реестр говорит
   «`AGENTS.md` ≤ 120 **строк**». По номеру 26 сейчас лежит
   `ONBOARDING_MAX_LINE_LENGTH = 120` — предел **длины строки в символах**,
   с развёрнутым обоснованием в комментарии (строки 19-28). Лимит на
   количество строк — другой объект, `ONBOARDING_LINE_LIMITS` на **строке 12**.
   Строка реестра сейчас указывает на не тот из двух «120».
5. **Предсказание по `REQUIRED_SKILLS` уже сбылось и было поглощено.** Реестр
   ожидал, что добавление reviewer-skill (PLAN-6E) «уронит тест».
   `review-change` уже присутствует и в `REQUIRED_SKILLS`
   (`tools/qa/check_agent_docs.py:29`), и на диске (`skills/review-change`).
   Тест не заблокировал добавление — он потребовал одной согласованной
   правки. Это аргумент за то, что строка ближе к `KEEP`, чем считалось.
6. `C49` (соседняя строка, тот же предмет): записано **12** subprocess-модулей
   на HEAD `adcbb19`, сейчас **7** порождают Python-child из 17 использующих
   `subprocess`. Реестр сам называет это измерением, а не инвариантом,
   поэтому это обновление, а не противоречие.

**Чего не хватает:**

7. **Четыре сигнатурных снимка не числятся анкерами.**
   `test_cli_internals_contract`, `test_wizard_internals_contract`,
   `test_content_creation_service_internals_contract`,
   `test_semantic_visual_evaluation_internals_contract` состоят из
   `inspect.signature`-сравнений (12 модулей, 27 вхождений всего) и по
   существу замораживают реализацию, но в разделе отсутствуют. В нём числится
   только `test_legacy_pipeline_internals_contract`.
8. **Стоимость анкера нигде не записана.** Самый дорогой модуль suite —
   characterization (`test_input_query_truth_characterization`, 178.5 с,
   17.5 % прогона). Раздел оценивает анкеры по вреду для архитектуры и не
   видит их цену в секундах.

**Что пора закрывать:**

9. Половину строки `test_stage2_agent_onboarding.py:19` — про замороженную
   дату (п. 3): работа фактически сделана.

---

## 9. Кандидаты

| Кандидат | Что защищает | Действие | Чем защита заменена | Риск | Уверенность |
|---|---|---|---|---|---|
| `test_input_query_truth_characterization` | dispatch запросов и persisted query plan | `REWRITE TO CONTRACT`: не материализовать превью — они не участвуют ни в одном assert | ничем: assert'ы те же, 0 failures | LOW | **измерено** (133.0 → 47.1 с) |
| `test_news_to_short_delivery` | доставка, субтитры, отказ от платного TTS | то же | те же assert'ы | LOW | **измерено** (71.8 → 27.5 с) |
| `test_news_to_short_pipeline` | сквозной проход без сети | то же | те же assert'ы | LOW | **измерено** (40.5 → 23.5 с) |
| `test_content_creation_service` | create/resume/платное одобрение | то же | те же assert'ы | LOW | **измерено** (166.1 → 142.4 с) |
| `test_plan9d_current_capture` (2 теста `DerivedFieldTests`) | идемпотентность finalize, пересчёт категорий | `MOVE OUT OF DEFAULT SUITE` (только CI) | замороженный корпус не меняется от слайса | MEDIUM — решает владелец PLAN-9D | средняя |
| `test_stage2_agent_onboarding.py` (дата) | момент времени | закрыть строку реестра | уже заменено производным календарём | LOW | **проверено по коду** |
| 4 модуля `*_internals_contract` | сигнатуры и import surface | `UNPROVEN` — сперва классифицировать | — | — | низкая, нужен разбор |
| любой `DELETE` | — | **нет кандидатов** | — | — | мутацией не проверялось |

---

## 10. Не трогать

- **`tests/__init__.py`** — ставит fake-credential и network guard **до**
  первого импорта. Любой перенос файлов, тиры или подкаталоги обязаны
  сохранить этот порядок; ошибка здесь снимает защиту молча и незаметно.
- **`tests/network_guard.py`**, `test_test_network_guard`,
  `test_runtime_network_boundary` — единственное, что делает «offline» фактом.
- **`test_claude_permission_contract`** (47 тестов, 18.7 с) и
  **`test_tts_env_credential_isolation`** — граница денег и учётных данных.
- **`test_project_rights_report`, `test_rights_review_preservation`,
  `test_rights_status_vocabulary`** — HIGH по `AGENTS.md`.
- **`test_asset_import_boundaries`, `test_capability_consistency`** —
  ARCHITECTURE INVARIANT, названы в реестре как не-анкеры.
- **`tests/plan9d_ground_truth.py` и разделение measurement / frozen** —
  действующий принцип; замороженный вход измеряется, историческое evidence —
  никогда. Дорогие тесты PLAN-9D можно переносить по тирам, но не смешивать
  два вида данных.
- **Дорогие render-тесты, чей предмет и есть рендер** —
  `test_final_renderer_end_tail`, `test_news_to_short_renderer`.

---

## 11. Маршрут слайсами

Новых PLAN-ID не заводится: работа ложится на существующих владельцев.

**S1 — снять с suite работу, которую он не проверяет.**
Цель: −171 с из 932 с. Scope: четыре модуля из §3.6; превью не
материализуются там, где не являются предметом. Риск по `AGENTS.md`: **LOW**
(тесты, контракт не меняется). Зависимости: нет. Приёмка: те же assert'ы,
0 failures, полный suite ≤ ~780 с. Выгода измерена.

**S2 — тест на примитив доказуемости (§7.7).**
Цель: закрыть HIGH-гэп `script_mismatch`. Scope: unit у владельца
`evidence.py` + один смешанный case. Риск: **HIGH** (отбор) — owner decision
до работы, независимый `review-change` после. Зависимости: нет.
Приёмка: characterization-first — тест фиксирует текущее поведение и краснеет
на правке `C91`, а не наоборот.

**S3 — быстрый tier в CI вторым job'ом.**
Цель: снять риск таймаута и дать быстрый сигнал. Scope:
`.github/workflows/offline-tests.yml`. Риск: **MEDIUM**. Зависимости: после
S1 (иначе tier придётся пересобирать). Приёмка: быстрый job ≈ 81 с; полный
job остаётся блокирующим и единственным авторитетом.

**S4 — дельта в реестр (§8, §14).**
Цель: привести «Accidental invariants» и `C49` в соответствие с кодом.
Scope: `docs/current/CLEANUP_REGISTRY.md`. Риск: **LOW** (docs-only).
Приёмка: `check_agent_docs`, строки ≤ 1500 символов.

**S5 — declared consumer для config-ключей (§7.5).**
Цель: сделать мёртвый ключ видимым. Scope: тест внутри
`tests/test_config_resolver.py`. Риск: **MEDIUM** (config-контракт).
Зависимости: owner decision по владельцу ключей.

Порядок: S1 → S4 → S3, параллельно S2 после owner decision; S5 последним.

---

## 12. Owner decisions

Только настоящие развилки; всё выводимое из репозитория здесь не спрашивается.

1. **Превью в тестах (S1).** Снимать материализацию превью там, где она не
   предмет, — через настройку `visual_preview.enabled=False` в конфиге теста
   или через seam? Это вопрос о том, считается ли исполнение превью частью
   «production still builds…» в характеризации PLAN-9B.
2. **Два теста `plan9d_current_capture` (129.9 с).** Остаются в дефолтном
   suite или переезжают в CI-only? Затрагивает контур измерения PLAN-9D.
3. **Владелец config-ключей (S5).** Кто отвечает за то, что ключ в
   `channel_config.json` имеет потребителя, — `config_resolver` (у которого
   сейчас нет продуктовых вызывающих) или читающий модуль?
4. **Судьба четырёх `*_internals_contract`.** Классифицировать как LEGACY
   ANCHOR со своим gate или оставить как есть?

Не спрашивается (выводится из репозитория): нужен ли pytest — нет; нужна ли
реструктуризация `tests/` — нет; нужен ли selective CI — нет.

---

## 13. Первый слайс

**S1, и внутри него — один модуль: `test_input_query_truth_characterization`.**

Почему именно он: самый дорогой модуль всего suite (178.5 с, 17.5 %), выигрыш
измерен на его самом дорогом тесте (133.0 → 47.1 с, −65 %), assert'ы не
меняются, тест остаётся зелёным, риск LOW, зависимостей нет. Один bounded
slice, один commit, targeted-проверка одной командой:

```bash
.\venv\Scripts\python.exe -B -m unittest tests.test_input_query_truth_characterization
```

Приёмка: те же assert'ы, 0 failures, модуль ≤ ~70 с, `scripts/gates.py`
зелёный.

---

## 14. Строки-кандидаты для `CLEANUP_REGISTRY.md`

Реестр этим отчётом **не правился**. Формат — шесть колонок
(`ID | Кандидат | Class | Фактическое evidence | Gate / целевое состояние | Этап`),
каждая строка ≤ 1500 символов (`REGISTRY_ROW_MAX_LENGTH`,
`tests/test_stage2_agent_onboarding.py`). ID условны.

| ID | Кандидат | Class | Фактическое evidence | Gate / целевое состояние | Этап |
|---|---|---|---|---|---|
| C9x | примитив доказуемости отбора не имеет именующего его теста | **FACT** | Аудит тестовой системы 2026-08-17 §7.1. `script_mismatch` (`src/assets/semantic_selection/evidence.py:189-191`) и `is_undecidable` (`:413-417`) имеют 6 вызывающих (`decision.py:310,363,378`, `candidate_ranker.py:345,633`) и **ноль** упоминаний в `tests/`. XOR по кириллице не срабатывает на одноязычном fixture, а 53 из 137 модулей не содержат кириллицы вообще, включая `test_semantic_decision_policy`, `test_semantic_visual_integration`, `test_media_selection_policy`. Корень `C91` структурно непокрываем существующими fixtures | Characterization-first: тест фиксирует **текущее** поведение примитива на смешанном письме и краснеет при правке `C91`. Запрещено: второй примитив доказуемости, отдельный RU-путь, изменение порогов | HIGH (отбор); владелец `src/assets/semantic_selection/evidence.py` |
| C9x | тесты платят за материализацию превью, которую не проверяют | **FACT** | Аудит 2026-08-17 §3.5-3.6. cProfile самого дорогого теста: 120 вызовов ffmpeg через `visual_preview._create_video_preview` = 74.2 с из 135 с (55 %); `_prepare_visual_review` = 84.0 с (62 %). Превью не участвуют ни в одном assert. Подмена `prepare_candidate_preview_analyses` в памяти: 133.0 → 47.1 с, 0 failures. То же на трёх модулях: delivery 71.8 → 27.5, pipeline 40.5 → 23.5, service 166.1 → 142.4. Итого −171 с из 932 с при зелёном | Снять исполнение превью там, где оно не предмет теста. Приёмка: assert'ы не меняются, 0 failures. Форма (конфиг `visual_preview.enabled` или seam) — owner decision | LOW; владельцы затронутых test-модулей |
| C9x | 14 из 76 ключей channel_config не имеют потребителя в коде | **FACT** | Аудит 2026-08-17 §7.5, обобщение `C83`. В пяти `config/channels/*/channel_config.json` 76 листовых ключей; 14 не встречаются ни разу в `src/`, `tools/`, `scripts/`. Худший — `allow_unknown_rights: false` (`nature_science_news_ru/channel_config.json:92`): по репозиторию только этот файл и один архивный отчёт. Права обеспечиваются независимо (`src/projects/rights.py`, `src/assets/license_policy.py`), то есть дефект поверхности настройки, не открытый шлюз | Declared consumer внутри существующего владельца `tests/test_config_resolver.py`: ключ обязан быть в `keys.SETTINGS` либо в явном списке декларативных. Запрещено: config-framework, второй resolver, grep-тест | MEDIUM (config-контракт); владелец ключей — owner decision |
| C9x | стоимость LEGACY ANCHOR не учитывается при их оценке | **FACT** | Аудит 2026-08-17 §6, §8. Заголовок `Test classification:` есть в 10 файлах из 137 (7 %); из 7 characterization-модулей канонический заголовок несёт 1. 12 модулей (27 вхождений) замораживают реализацию через `inspect.signature`/`getsource`, но в «Accidental invariants» числится только `test_legacy_pipeline_internals_contract`; `test_cli_internals_contract`, `test_wizard_internals_contract`, `test_content_creation_service_internals_contract`, `test_semantic_visual_evaluation_internals_contract` отсутствуют. Самый дорогой модуль suite — characterization: 178.5 с, 17.5 % прогона | Дополнить раздел четырьмя модулями и записывать цену анкера в секундах рядом с вредом. Новый реестр не заводится | LOW (docs); существующий владелец раздела |

Отдельно, **правки существующих строк** (§8), а не новые строки:
`test_apps_structure` 19 → 39; `test_documentary_visual_engine` 295 → 348;
`test_stage2_agent_onboarding.py:19` — закрыть половину про дату, перенести
анкер `REQUIRED_SKILLS` на строку 166; `:26` — указать строку 12
(`ONBOARDING_LINE_LIMITS`) вместо строки 26
(`ONBOARDING_MAX_LINE_LENGTH` — это символы, не строки); `C49` — 12 → 7.

---

## 15. Не проверено

1. **Поимённая классификация 137 модулей** по четырём классам. Проверено
   поимённо 17 (7 characterization + 8 анкеров + 2 не-анкера); остальные
   ~120 отнесены агрегатно по признакам имени и содержания (§6).
2. **Проверка мутацией не выполнялась ни разу.** Поэтому в отчёте нет ни
   одного `DELETE`, а раздел 3.2 честно вырожден: избыточность текста не
   искалась систематически.
3. **Поимённый разбор 53 модулей без кириллицы** (§7.1 F2) — какие из них
   слепы к классу ошибки, а какие минимальны намеренно.
4. **Топ-модули кроме первого не профилированы через cProfile.** Разбор
   «куда уходит время» точен для `test_input_query_truth_characterization`;
   для `test_content_creation_service` (166 с) известно только, что превью
   дают лишь 14 % — остальное не разложено.
5. **Два теста `plan9d_current_capture` (129.9 с)** — причина стоимости не
   разобрана; сказано только, что это replay замороженного корпуса.
6. **Устойчивость к порядку тестов при параллельном запуске** — параллельный
   раннер не вводился (запрещено), поэтому гонки не проверялись. Проверено
   только: полный прогон и 137 одиночных прогонов дают одинаковый результат.
7. **Числа времени зависят от среды.** Часть лёгких read-only команд шла
   параллельно с прогонами; абсолютные секунды имеют погрешность единиц
   процентов. Сравнивать их с CI-числами нечестно: CI ставит `ffmpeg-full`
   и работает на другой машине.
8. **`AI_YOUTUBE_WORKSPACE`** и прочие env-зависимости проверены только по
   наличию восстановления в `finally`, не поведением.
9. В рабочем дереве во время сессии появился незакоммиченный
   `docs/audits/SEMANTIC_BRIEF_PROMPT_AND_LANGUAGE_AUDIT_2026-08-16.md`,
   созданный **не этой сессией**. На профилирование он не влияет
   (docs-only), но дерево не было чистым по untracked всё время.

---

## Прямые ответы

**1. Проблема в количестве тестов?**
Нет. 2323 теста — не проблема: 71 % из них быстрее 10 мс, а 2300 тестов
вместе стоят 142.4 с. Проблема в 23 тестах (1 %), которые стоят 757.9 с (84 %).

**2. Что именно делает полный прогон долгим?**
Реальные вызовы ffmpeg внутри продуктового пути. В самом дорогом тесте —
120 subprocess-вызовов материализации превью, 74.2 с из 135 с. Импорт и
discovery всех 137 модулей стоят 2.31 с, то есть 0.25 % прогона.

**3. Можно ли сделать быстрый суточный suite и сколько он будет идти?**
Да, измерено: **81.3 секунды, 2106 тестов, 0 failures** — полный discover
минус десять модулей из §3.3. Он не заменяет блокирующий полный прогон.

**4. Как определять нужные тесты по изменённым файлам?**
По canonical owner и таблице §4.3, а не автоматической картой. Граф импортов
разрежен (медиана 3 модуля на тест) и технически годен, но 10 модулей
запускают продукт через `subprocess` и рёбер к нему не имеют — селектор по
графу покажет зелёный, ничего не проверив.

**5. Нужны ли маркеры и нужен ли pytest, или хватает unittest?**
Хватает unittest. Targeted-прогон уже стоит 0.62–1.35 с; маркеры и pytest
не ускорят то, что состоит почти целиком из 0.41 с накладных на процесс.
`--durations` заменяется тридцатью строками временного раннера.

**6. Когда full обязателен и когда он сейчас запускается зря?**
Обязателен по §8 «Execution protocol»: shared contract, persisted schema,
paths/package root, provider registry, compatibility retirement, закрытие
крупного этапа — плюс HIGH-классы `AGENTS.md` (деньги, сеть, права,
authority). Зря — после docs-only, после локального leaf-изменения и после
слайса одного владельца; протокол это уже разрешает (§7, §10), но локально
выбор бинарный, потому что targeted-командой пользуются реже, чем можно.

**7. Сколько тестов реально можно удалить без потери защиты?**
Доказано — **ноль**. Проверок мутацией не проводилось, покрывающих
дубликатов не найдено, поэтому ни один `DELETE` в отчёт не попал. Резерв —
не удаление тестов, а снятие лишней работы: измеренные −171 с из 932 с при
неизменных assert'ах и зелёном прогоне.

**8. Какие fixtures могут скрывать реальные дефекты?**
Одноязычные fixtures в слое отбора. `script_mismatch` — XOR по наличию
кириллицы, поэтому fixture, где всё латиницей, не может активировать ветку
ни при каком наборе значений. 53 из 137 модулей не содержат кириллицы,
включая `test_semantic_decision_policy`, `test_semantic_visual_integration`,
`test_media_selection_policy`. Это ровно механизм `C91` (7.5 против 78.3).

**9. Какие критичные области недотестированы?**
Одна, и она HIGH: примитив доказуемости отбора
(`script_mismatch`/`is_undecidable`) — 6 вызывающих, 0 именующих тестов.
Деньги, сеть, права, учётные данные и resume, наоборот, защищены лучше всего
и отдельными модулями. Недотестирован не слой безопасности, а слой смысла.

**10. Что внедрять первым?**
S1 на одном модуле `test_input_query_truth_characterization`: самый дорогой
модуль suite, выигрыш измерен (133.0 → 47.1 с), assert'ы не меняются, риск
LOW, зависимостей нет.

## Приложение 2026-08-18: параллельный прогон измерен, но не внедрён

Открытый вопрос 6 («устойчивость к порядку тестов при параллельном запуске»)
получил первое измерение. Раннер не вводился в репозиторий: скрипт жил в
scratchpad, ничего не устанавливал (ни `pytest`, ни `xdist` в venv нет) и
запускал тот же `python -m unittest`, разложив 146 модулей по шести процессам
round-robin по имени.

| прогон | стен. время | тестов | цвет |
|---|---|---|---|
| последовательный (канонический) | 992 с | 2407 | OK |
| 6 процессов | 478 с | 2407 | 6/6 воркеров OK |

Ускорение **2.08×**, ноль падений, рабочее дерево после прогона чистое
(`git status` — только заранее известный untracked `tmp/`). Балансировка при
этом плохая: воркеры разошлись 478 с против 59 с, потому что round-robin по
имени не знает про топ-модули из §3.3. Сумма процессорного времени 1324 с
против 992 с последовательных — контention и шесть стартов интерпретатора.

Потолок считается прямо из §3.3 и внедрению мешает больше, чем балансировка:
самый дорогой модуль стоит **178.5 с**, и никакое разложение по модулям ниже
этого не опустится. То есть идеальный параллельный прогон — это ~4 минуты
против 16, а не «секунды», и покупается он риском гонок, который одним зелёным
прогоном не закрывается: вопрос 6 остаётся открытым, просто теперь у него есть
одно наблюдение вместо нуля.

**Не внедряется, и это решение, а не пропуск.** Причина не только в потолке:
с 2026-08-18 ветка запушена, и полный suite идёт в CI на каждый push
(`.github/workflows/offline-tests.yml`), поэтому локальный полный прогон нужен
на границе этапа, а не постоянно. Менять инструмент, которым меряется качество
отбора, на более быстрый и менее предсказуемый ради этой частоты — плохой
обмен. Рекомендация §5 (S1 на самом дорогом модуле) остаётся первой: она
убирает работу, а не распараллеливает её.
