---
status: current
audit_date: 2026-08-14
audit_head: bf68693773cd3b0f615d78c906133976852176a5
working_branch: governance-reset
---

# FIRST OWNER SHORT — LOCAL REPEAT, 2026-08-14

Диагностический owner-прогон на HEAD `bf68693` (пуш выполнен этим же слайсом).
Код не менялся, PLAN не двигался, M1-E не начинался.

> **CI на этом HEAD — `failure`**, run `31783376609`. В момент пуша он был
> `in_progress`, и диагностика продолжилась по контракту prompt (read-only,
> от результата CI не зависит); результат проверен после завершения прогона.
> Разбор — §10. Дефект **предшествует** этой диагностике: его внесли
> library-слайсы `d3151b0`/`ec9ca7b`, а не этот прогон. Не исправлялся.

Повтор сценария [FIRST_OWNER_SHORT_2026-08-13.md](FIRST_OWNER_SHORT_2026-08-13.md)
RUN 1 (LOCAL) на том же 5-сценном русском сценарии про полог дождевого леса,
после того как локальная медиатека была переработана
([CURATED_LIBRARY_2026-08-14.md](CURATED_LIBRARY_2026-08-14.md): 72 curated,
72 `allowed_for_render`, 0 `review_required`). Разрешения: сеть выключена
(никаких `--allow-network`), Vision выключен, paid semantic выключен,
ElevenLabs — один платный generation attempt по каналу `ru_dom`. STOCK
провайдеры не вызывались.

**Итог одной строкой:** новая библиотека сняла blocking-по-правам полностью,
но оставила red CI (§10);
(RUN 1 blocker: 0/5 сцен из-за `rights_status` — здесь 5/5 сцен нашли
`licensed`-кандидатов), но материал остаётся семантически негодным для 4 из
5 сцен. 1 сцена получила настоящий слот, ElevenLabs сгенерировал озвучку
(один платный вызов, как и разрешено), но `final_render` заблокирован
`scene_coverage`: MP4 не создан.

---

## 1. Проект и параметры

- `project_id`: `2026-08-14_sverhu-dozhdevoy-les-vyglyadit-kak-sploshnoy`
- Канал `nature_science_news_ru`, шаблон `fullscreen_voiceover_v1`, язык `ru`,
  `--completion-mode draft_complete`, вход — `--source-text-file` (тот же
  5-сценный текст) + `--input-mode script_file`, `--target-duration 25`.
  `--visual-brief` **не передавался** — сцены отбирались автоматически,
  без ручной подсказки.
- Ассеты вручную не подставлялись, `assets replace` не вызывался, запросы не
  переписывались, `_score_asset`/`candidate_ranker` не менялись,
  `curated_library.json`/`media_index.json`/rights не редактировались.

## 2. Per-scene разбор

| Сцена | narration | primary_query | local-candidates найдено | лучший rights-allowed кандидат | итог |
|---|---|---|---|---|---|
| scene_001 | «Сверху дождевой лес выглядит как сплошной зелёный потолок.» | `дождевой выглядит зелёный` | 10 (ranked), 5 (shortlist) | `pexels_34770435` (тропическая река) `final_score=27.5` | **unresolved** — ниже порога `score_below_75` |
| scene_002 | «...до лесной подстилки доходит лишь около двух процентов солнечного света.» | `буквально доходит свет` | 10 / 5 | те же два `licensed`, `final_score=27.5` | **unresolved** — `score_below_60` |
| scene_003 | «Поэтому наверху идёт главная борьба за свет...» | `свет борьба` | 10 / 5 | `pexels_37121718` (свет сквозь стволы хвойного леса, туман) `final_score=92.5` | **resolved** — единственный слот прогона |
| scene_004 | «В пологе живёт большинство животных тропического леса.» | `леса большинство` | 10 / 5 | те же два `licensed`, `final_score=27.5` | **unresolved** — `score_below_60` |
| scene_005 | «Мы замечаем реку внизу...» | `леса большая` | 10 / 5 | те же два `licensed`, `final_score=27.5` | **unresolved** — `score_below_75` |

Для каждой из 4 unresolved сцен local_library нашёл ровно один и тот же
набор из 5 кандидатов (одинаковый для всех сцен, потому что коарс-фильтр не
различает их по содержанию — см. §4): 3 legacy `review_required` + 2
`licensed` («аэросъёмка солнечных панелей», «тропическая река с порогами»).
Ни один из двух `licensed`-кандидатов не описывает полог/крону дождевого
леса — genuinely мимо темы, отклонены правильно.

## 3. scene_003 — единственный резолвнутый слот

`pexels_37121718` — «Солнце светит сквозь стволы высоких хвойных деревьев в
туманном лесу», 3840×2160, лицензия `licensed`/`allowed_for_render=true`.
`subject_match=100` (сцена: subject=`свет`, кандидат буквально несёт
«sunlight»/«солнечный свет»), `action_match=100`, `environment_match=100`,
`scene_match_score=92.5`. Реальный, осмысленный матч по теме «борьба за
свет», хотя это хвойный/туманный лес, а не тропический полог — приемлемо для
`abstract_explanation`-сцены. `framing_status: crop_review_required`
(источник 16:9, вертикальный 9:16 кроп метаданными не подтверждён —
`composition_after_crop_not_verifiable_from_metadata`). `support_status:
manual_confirmation_required`.

## 4. Найденный риск ранжирования — воспроизведён с точным примером

Прошлый аудит (RUN 1, `later debt`) фиксировал, что `_score_asset`
(`src/media_library.py:534`) даёт всем локальным кандидатам одинаковый
коарс-score, если ни один RU/EN keyword не пересёкся. Это воспроизводится
буквально: во всех 5 сценах `total_score=13.0` у всех 10 `ranked_candidates`
без исключения — коарс-фильтр не различил их по содержанию, шортлист из
top-5, ушедший в финальный semantic ranker, по сути собран content-blind.

Поверх этого нашёлся отдельный, ранее не задокументированный механизм на
семантическом слое (`src/assets/semantic_selection/candidate_ranker.py:280-301`).
Комментарий в коде (строки 284-289) объясняет намеренный дизайн: поле,
термины которого написаны на языке, которого в метаданных провайдера быть не
может («пластик» против английского title), помечается **undecidable**, а не
**unmatched** — и выбрасывается из взвешенного среднего вместе со своим
весом (`subject` весит 0.45 из 1.0).

Точный пример (scene_001, сцена «Сверху дождевой лес выглядит как сплошной
зелёный потолок», subject=`дождевой`):

| asset_id | title/keywords | rights_status | subject_match | environment_match | final_score |
|---|---|---|---|---|---|
| `6bd504a367e82a5e` | `macro insects rainforest / dark jungle night / mosquitoes forest / humid rainforest` | `review_required` (заблокирован) | `0.0` (но `дождевой` undecidable — RU термин против EN-only keywords) | `100.0` | **92.5** |
| `a02e43f7076fc30d` | `lightning storm / airplane turbulence / dark clouds / rain window` | `review_required` (заблокирован) | `0.0` (undecidable) | `100.0` | **92.5** |
| `d82237d39b9658fe` | `closing browser tabs / slow handwriting journal / rain on window / minimal desk night` | `review_required` (заблокирован) | `0.0` (undecidable) | `100.0` | **92.5** |
| `pexels_34770435` | «Широкая быстрая река с порогами, пальмы, тропическая растительность» | `licensed` | `0.0` (decidable — реально не совпало) | `100.0` | **27.5** |
| `pexels_14067718` | «Аэросъёмка солнечных панелей...» | `licensed` | `0.0` (decidable) | `100.0` | **27.5** |

Все пять кандидатов получили `environment_match=100`, но три получили
`final_score=92.5` (их subject объявлен undecidable и выброшен из среднего),
а два genuinely-decidable кандидата с честным несовпадением subject получили
только `27.5`. **«Closing browser tabs, minimal desk night» — асset, вообще
не относящийся к лесу — набрал бы наивысший балл в этой сцене, если бы не
права.** В этом прогоне неверный выбор не состоялся только потому, что все
три высокобалльных кандидата оказались `review_required`
(legacy-схема, не про содержание) — совпадение, а не гарантия: в тот момент,
когда любой подобный нерелевантный клип получит `rights_status: licensed`
(что curated-процесс делает пачками), он победит genuinely релевантный
кандидат с разницей в 65 баллов.

Это отличается от «later debt» из RUN 1 (`_score_asset` content-blind на
коарс-слое) — это отдельный, более специфичный дефект: взаимодействие
RU-сценария с EN-only метаданными на **семантическом** слое, где
`undecidable`-логика (задуманная для честного признания «неизвестно»)
на практике перекладывает вес на единственное декодируемое поле
(`environment`) и завышает итоговый балл. Не исправлялось.

## 5. Ассembly / completion

```
slot_count: 1, scenes_usable_in_draft: 1, scenes_publish_ready: 0
unresolved_scenes: [scene_001, scene_002, scene_004, scene_005]
timeline_problems: "sceneN:assembly_has_no_slots" × 4
quality_tiers: {D_partial: 1}
draft_complete: false, publish_ready: false, video_first_review_required: true
```

STOCK-провайдеры (`pexels`, `pixabay`, `wikimedia`, `internet_archive`,
`nasa_images`) были опрошены автоматически для всех 5 сцен и все 25 попыток
получили `status: skipped, reason: query_translation_required` — **ни один
сетевой запрос не отправлен** (то же честное поведение, что в RUN 2:
"Нет английского запроса для этой сцены"). Pipeline не пытался тихо уйти во
внешний stock — зафиксировано, сеть не включалась.

## 6. ElevenLabs — один платный вызов

Прогон дошёл до voice/assembly path (1 usable slot), поэтому по разрешению
владельца выполнен один generation attempt:

- `paid_call_performed`: **true**
- `provider`: `elevenlabs`, `model_id`: `eleven_multilingual_v2`
- `voice_profile`: `ru_dom` (voice_id `hDfThiytYnsDMuVgm6Qy`, "Dom") — канальный
  контракт, без изменений
- 5 сцен озвучены, `character_count=365`, суммарная длительность
  narration **23.29 с** (в целевом диапазоне 20–30 с)
- `narration.wav` создан:
  `projects/2026-08-14_.../localizations/ru/voice/narration.wav`
- Повторной генерации не запрашивалось.

Первый resume (без явного `--voice-provider`) остановился со
`status: voice_provider_required` — CLI-подсказка `rerun_commands` сама
предложила `--voice-provider disabled`, что воспроизводит уже известную
UX-находку RUN 1 («подсказка `rerun` подставляет `disabled`, хотя канал
настроен на `elevenlabs`» — не новая находка, тот же дефект). Пришлось
явно передать `--voice-provider elevenlabs --voice-profile ru_dom`.

## 7. Почему MP4 не создан

`preview_render` в top-level статусах помечен `completed`, но фактический
`preview/preview_manifest.json` говорит `status: blocked, reason:
preview_requires_completed_voice_and_no_missing_assets` (4 сцены без
ассета). `final_render`: `status: blocked, reason: scene_coverage`,
`draft_render_gate` перечисляет ровно 4 проблемы — `scene_001..005 (кроме
003) has no usable visual slot`. `output_path: ""`. Это не известный C58
(рендер вообще не запускался, блокировка — на gate до рендера, а не в
рендерере) — отдельная, самообъяснимая находка, не требующая новой записи.

`quality_check` (`status: failed`) корректно перечисляет все 4 непокрытые
сцены плюс предупреждения: отсутствующие субтитры (subtitle-этап не
достигнут), `video_first_coverage` 21% (1 видео-клип из 5 сцен).

## 8. Сравнение с первым LOCAL прогоном

| Критерий | RUN 1 (63 legacy, review_required) | LOCAL REPEAT (72 curated, licensed) |
|---|---|---|
| Сцен с `licensed`-кандидатами | 0/5 (все `review_required`) | 5/5 нашли ≥1 `licensed` кандидата |
| Слотов | 0 | 1 (`scene_003`) |
| Причина отказа для остальных | rights (`review_required`) | семантика (`score_below_60/75`) — правильный отказ |
| ElevenLabs | не достигнут | достигнут, 1 платный вызов выполнен |
| MP4 | нет | нет (`scene_coverage`) |
| STOCK fallback | не пытался | не пытался (то же честное `query_translation_required`) |

**Что исправила новая библиотека:** rights-blocker снят полностью — правила
структурно работают («заблокированы легально» → «допущены легально»), и
пайплайн впервые дошёл до voice/ElevenLabs/assembly стадии на LOCAL пути.
**Что осталось проблемой движка:** (а) коарс-фильтр локального поиска
по-прежнему content-blind (одинаковый `total_score` для всех кандидатов
сцены); (б) семантический ranker переоценивает кандидатов, чей subject
«undecidable» из-за русский/английский языкового разрыва, отдавая весь вес
единственному decidable-полю (`environment`) — конкретный, воспроизведённый
пример в §4; (в) 63 из 72 curated ассетов вообще не касаются тропического
дождевого леса (это дженерик nature-библиотека, не тематическая), поэтому
даже идеальный ranker не нашёл бы для 4 сцен ничего лучше «river/solar
panels».

## 9. Findings и owner

| Находка | Класс | Существующий owner |
|---|---|---|
| §4: `undecidable`-редистрибуция веса в `candidate_ranker.py` даёт вплоть до 92.5 балла нерелевантному кандидату при RU subject / EN metadata (конкретный пример: `d82237d39b9658fe` "closing browser tabs" против сцены про дождевой лес) | **PLAN-10C / retrieval-quality candidate** | тот же дом, что и C69/C72/C74 (config weights illusions, parked thresholds, unused quality metrics) в `docs/current/CLEANUP_REGISTRY.md` |
| Коарс `_score_asset` (`src/media_library.py:534`) даёт одинаковый score всем локальным кандидатам без keyword-пересечения — воспроизведено на новой библиотеке | **later debt** (уже записано в `FIRST_OWNER_SHORT_2026-08-13.md`, не новая находка) | тот же |
| Подсказка `rerun_commands` подставляет `--voice-provider disabled`, хотя канал сконфигурирован на `elevenlabs` | **UX inconvenience** (не новая — уже зафиксировано RUN 1) | — |
| 63/72 curated ассетов — generic nature b-roll без тематического покрытия тропического дождевого леса/полога | **expected limitation** библиотеки, не движка | владелец знал при курации (§1 CURATED_LIBRARY audit) |
| `preview_render` top-level "completed", хотя фактический `preview_manifest.json` — `blocked` | **UX inconvenience** (несогласованность статуса верхнего уровня и фактического manifest) | не классифицировался ранее, не создаю новый PLAN-ID — запись only |
| §10: `test_provenance_evidence_points_at_a_file_that_exists` зависит от gitignored файлов → 63 failures в чистом clone, CI red на `bf68693` | **BLOCKER** (red baseline: следующий слайс нельзя проверить на зелёном CI) | library-слайс `d3151b0`/`ec9ca7b`, тот же дом; новый PLAN-ID не создаётся |

## 10. CI на `bf68693` — red, разбор

`offline-tests` run `31783376609`: `Ran 2239 tests`, `FAILED (failures=63,
skipped=7)`. Все 63 — subTest одного метода:
`tests/test_curated_library.py:42`
`test_provenance_evidence_points_at_a_file_that_exists`.

Тест утверждает, что `provenance_evidence` каждой записи манифеста указывает на
существующий файл репозитория (`:45-46`). Но 63 из 72 записей ссылаются на
файлы, которых в репозитории **нет**, потому что они gitignored:

| Путь из `provenance_evidence` | Существует локально | Отслеживается Git | Правило |
|---|---|---|---|
| `assets/library/metadata/media_index.json` | да | **нет** | `.gitignore:61` |
| `projects/project_solar_vs_nuclear/03_stock/selected_sources.json` | да | **нет** | `.gitignore:47` (`/projects/`) |
| `docs/audits/CURATED_LIBRARY_2026-08-14.md` | да | да | — |

Проходят ровно те 9 записей, чей evidence — сам audit-документ, то есть девять
клипов, добавленных `ec9ca7b`. Остальные 63 зелены только на машине владельца,
где gitignored-файлы физически лежат на диске; в чистом clone CI их не видит.

Класс находки — **test hygiene**: тест зависит от неотслеживаемых runtime-файлов
и потому не воспроизводим вне рабочей машины. Это тот же класс дефекта, который
`10ae86d` уже закрывал для `test_video_asset_engine_builds_multi_clip`.

Почему локальные гейты этого не поймали: `scripts/gates.py` на этом слайсе
зелёный, а full offline suite локально проходит — оба видят присутствующие на
диске gitignored-файлы. Красным baseline становится только в CI.

**Не исправлялось** — за пределами разрешённого этой диагностике. Owner
существующий: тот же дом, что и library-слайс; новый PLAN-ID не создаётся.

## 11. Что НЕ делалось

Код не менялся. `curated_library.json`/`media_index.json`/rights не
правились. Ассеты вручную не подставлялись. `--visual-brief` не передавался.
Запросы не переписывались. Новых PLAN-ID не создано, `CLEANUP_REGISTRY.md`
не редактировался. `PLAN-9D` остался текущим checkpoint. M1-E / VA-NEW-09 не
начинался. STOCK-провайдеры не вызывались, сеть не включалась.
