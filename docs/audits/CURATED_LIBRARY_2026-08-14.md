# CURATED LOCAL LIBRARY — owner slice, 2026-08-14

Слайс по решению владельца от 2026-08-14: собрать нормальную `assets/library`
из того, что уже лежит на диске, вместо очередной уборки каталогов. Вход —
`AI-YouTube_attic\2026-08-13` (карантин **R05**), `projects/project_solar_vs_nuclear/03_stock`
и сама `assets/library`. Сеть, Vision, платный semantic и TTS не выполнялись:
слайс полностью offline.

Versioned результат — `assets/library/metadata/curated_library.json` (**72 записи**:
63 отобраны offline, ещё 9 добавлены после отдельно разрешённой владельцем
сетевой проверки источников, см. 3.1). Проверка и перенос в runtime-индекс —
`python -m tools.library.curated_index`.

---

## 1. Что было на входе

| Корпус | Файлов | Байт | Провенанс |
|---|---:|---:|---|
| `assets/library/videos` | 63 | 2 806 161 300 | `media_index.json`: source/download URL есть у всех 63 |
| attic `assets/cache/videos` | 95 | 8 978 764 090 | только `provider` + `provider_asset_id` в имени файла |
| attic `assets/broll` | 34 | 1 557 749 971 | нет вообще (`scene_01..35.mp4` одного прогона) |
| solar `03_stock` | 15 | 962 064 926 | `selected_sources.json`: 12 из 15 с полной записью |

**Дублей больше, чем уникального материала.** 207 файлов дают **82 уникальных
provider id**. Кэш из карантина почти целиком дублирует медиатеку: из 50 его id
только **8** отсутствовали в `assets/library`, остальные 42 — те же ролики в
другом рендишене. 47 групп байт-идентичных копий подтверждены sha256.

## 2. Что реально в кадре

Все 85 уникальных кандидатов (кроме `broll` без провенанса) просмотрены
контактными листами по три кадра (15/50/85 % длительности). Подтверждён и
расширен дефект, записанный в `FIRST_OWNER_SHORT_2026-08-13.md`: **метаданные
описывали поисковый запрос, а не кадр.** Восемь записей описывали не тот сюжет:

| Файл обещал | В кадре | ID |
|---|---|---|
| `psychology_diagram_02_laziness_overload_distinction` | мотоцикл везёт гору мешков по улице | `pexels:34971525` |
| `psychology_diagram_03_overload_reduction_path` | конвейер мусоросортировки с воздуха | `pexels:29702561` |
| `psychology_many_browser_tabs_dark_calendar` | рука открывает жестяную банку | `pexels:4061832` |
| `psychology_lonely_urban_person_sitting_edge_bed` | пустая ночная улица сверху | `pexels:30353676` |
| `psychology_quiet_notebook_rain_person_writing` | снегопад на еловых ветках | `pexels:1299684` |
| `survival_storm_clouds_airplane_dark_rainforest` | перрон и терминал аэропорта | `pexels:36936635` |
| `survival_empty_wooden_hut_river_silence_dark_camp` | красная изба в заснеженном лесу | `pexels:28963349` |
| `psychology_person_alone_desk_night_hands_keyboard` | гитарист на фоне подсвеченного моста | `pixabay:46637` |

Курируемые записи содержат `content_ru` — одно предложение о том, что видно в
кадре, — и ключевые слова на английском и русском отдельно от исходного запроса,
который сохранён как `search_query`.

## 3. Что отобрано и по какому правилу

**63 записи.** Правила отбора:

1. **Без провенанса — не в библиотеку.** 9 кандидатов сначала остались вне
   манифеста: 7 файлов карантина (`pexels:18922150`, `11381482`, `17312957`,
   `6805846`, `19769452`, `pixabay:197564`, `37088`) и 2 файла solar-проекта
   (`pixabay:212433` — вертикальный питон 2160×4096, `pexels:36167827`),
   которых нет в `selected_sources.json`. Ни в одном каталоге репозитория для
   них не была записана страница источника; выводить URL из id — это выдумать
   провенанс, а не восстановить его. Владелец разрешил проверить их у
   провайдера, и после подтверждения все 9 добавлены — см. 3.1.
   Исключение, не потребовавшее сети, — `pixabay:178732`: его политика прав
   записана целиком в `projects/plan9d_current_capture_v1/capture_raw.json`.
2. **Побеждает та копия, которая реально есть в наибольшем разрешении.**
   24 клипа медиатеки существовали в карантине в 4K при HD в библиотеке. Для
   вертикального кадра 1080×1920 это не косметика: кроп 9:16 из 1920×1080 даёт
   608 px по ширине и требует апскейла, из 3840×2160 — 1215 px и даёт запас.
3. **Рендишен не наследует чужой URL.** У копий из кэша собственный
   download URL никогда не записывался, поэтому у них `download_url: ""` и
   `rendition_note`, а не URL от HD-версии того же ролика. Инвариант закреплён
   тестом.
4. **13 кандидатов отброшены по качеству кадра** (тёмные ветки без сюжета,
   ровное серое небо, 1280×720, дубли сюжета) — список причин в `drop` рабочей
   таблицы слайса; отброшенные файлы остаются в `assets/library` с записью
   `curation_status: legacy_unreviewed`.
5. `pexels:5155195` (ребёнок за стеклом) исключён отдельно как чувствительный
   материал, а не по качеству.

Итог по ведущей теме записи (с учётом 3.1): тропический лес — 13, энергетика —
11, люди — 10, вода — 8, дикая природа — 5, лес — 5, город — 5, погода — 3,
авиация — 3, природа — 2, ландшафт — 2, по одной: зима, промышленность,
абстракция, ночное небо, горы. Вертикальных (9:16) — 4, с разрешением 2560 px и
выше — 40.

## 3.1. Сетевая проверка источников (решение владельца 2026-08-14)

Правило 1 выше отсекло 9 клипов не по качеству, а по отсутствию записи об
источнике. Владелец отдельно разрешил сетевую проверку — **только чтение
страниц провайдера, без скачивания, без API-ключей и без платных вызовов.**
Проверено 9 id, все существуют, и все названия совпали с тем, что я до этого
описал по кадрам:

| ID | Канонический URL провайдера | Название на странице | Автор |
|---|---|---|---|
| `pexels:18922150` | `/video/b-roll-25-18922150/` | Peaceful stream flowing through a lush tropical jungle in Thailand | Tony Flanagan |
| `pexels:11381482` | `/video/footstep-into-mud-11381482/` | Close-up of hiking boots stepping through muddy water on a grassy trail | Ammad Rasool |
| `pexels:17312957` | `/video/naturaleza-insectos-...-17312957/` | Detailed monochrome view of a grasshopper resting on a leaf | CESAR A RAMIREZ VALLEJO TRAPHITHO |
| `pexels:6805846` | `/video/sun-shining-bright-through-the-trees-6805846/` | Sun Shining Bright Through the Trees | Joshua Woroniecki |
| `pexels:19769452` | `/video/pucallpa-laguna-yarinacocha-19769452/` | Serene canoe journey on Ucayali River with sunset reflections | Jose Galarza |
| `pexels:36167827` | `/video/electrician-working-on-industrial-battery-bank-36167827/` | Electrician Working on Industrial Battery Bank | Mumtaz Niazi |
| `pixabay:197564` | `https://pixabay.com/videos/id-197564/` | Bridge, Wooden Bridge, Historic Monuments | Kanenori |
| `pixabay:37088` | `https://pixabay.com/videos/id-37088/` | Waterfall, Water, River | Ronin_Studio_Munich |
| `pixabay:212433` | `https://pixabay.com/videos/id-212433/` | Snake, Reptile, Scales | не указан на странице |

Метод, который сделал это возможным: у Pixabay форма `videos/id-<id>/` уже была
подтверждена записью в репозитории; у Pexels URL без slug (`/video/<id>/`)
отдаёт 403, но `/video/video-<id>/` резолвится и возвращает канонический адрес.
Проверено на контрольном id `11774048`, чей настоящий slug известен из
`selected_sources.json`, — вернулся именно он. То есть URL не выдуман, а получен
от провайдера.

У этих девяти `download_url` остаётся пустым: подтверждена страница источника,
а не тот рендишен, который лежит на диске. `provenance_evidence` указывает на
этот документ — таблица выше и есть запись проверки.

Материал того стоил: вертикальный питон 2160×4096 (единственная вертикальная
дикая природа в медиатеке), два водопада 4K, мост Кинтай на рассвете и
единственный кадр с человеком у энергетического оборудования.

## 4. Перемещения файлов

Ничего не удалено. Счётчики сверены после каждой операции.

| Операция | Файлов |
|---|---:|
| переименовано в `assets/library/videos` под правдивое имя | 26 |
| перенесено из карантина в библиотеку (4K, водопад, + 7 после проверки 3.1) | 32 |
| скопировано из solar-проекта (проект не тронут) | 14 |
| вытеснено из библиотеки в `AI-YouTube_attic\2026-08-14_displaced_by_curation` | 24 |

`assets/library/videos` — 85 файлов, 6.8 GB (было 63 файла, 2.7 GB).
Карантин — 148 файлов, 6.6 GB (было 156 файлов, 10.5 GB), из них 124 в папке
`2026-08-13` и 24 вытесненные HD-копии.
`projects/project_solar_vs_nuclear/03_stock` — 18 файлов, без изменений.

## 5. Единственный оставшийся блокер: `local_library` не имеет правила для лицензий провайдеров

`BLOCKER-L2` из диагностики закрыт наполовину. Записи теперь несут права:
`schema_version: 1`, `license`, `provenance`, `rights_status: licensed`,
`allowed_for_render: true` — и проходят `_is_current_safe_record`.

Но `config/license_policy.json` даёт провайдеру `local_library` правила только
для `user_owned` и `fake_test_license`. Лицензии `pexels` и `pixabay` в его
таблице нет, поэтому все 63 записи получают `license_not_in_policy`:

```
python -m tools.library.curated_index verify
curated items: 63
structural/technical problems: 0
policy allowed: 0  blocked/review: 63
  license_not_in_policy: 63
```

**Асимметрия зафиксирована фактом, а не мнением:** тот же файл, та же лицензия,
тот же контекст `internal_content_production` — через провайдера `pexels`
получает `allowed_for_render: true`, а из локальной медиатеки блокируется. Гейт
здесь не защищает права: он реагирует на то, кто отдал файл, а не на то, чем он
лицензирован. Записать эти файлы как `user_owned` было бы ложью — владелец не
автор стока.

**Решение владельца 2026-08-14: зеркалить правила провайдеров.** Провайдер
`local_library` получил те же два контекста, что у `pexels` и `pixabay`:
`internal_content_production` — лицензии `pexels`/`pixabay` разрешены при
`requires_schema_version: 1`; `public_multi_user_product` — заблокированы до
будущего коммерческого аудита. Правила `user_owned` и `fake_test_license` и
механизм `schema_v1_required` не менялись. Изменён только
`config/license_policy.json`; код прав не трогался.

```
python -m tools.library.curated_index verify
curated items: 63
structural/technical problems: 0
policy allowed: 63  blocked/review: 0
```

Оба контекста закреплены тестами `tests/test_curated_library.py`: внутренний —
`allowed` с причиной `policy_rule_allowed`, публичный — не `allowed`.

## 5.1. Библиотека стала живой — и это сразу вскрыло слепой ранжировщик

Первый же побочный эффект: тест
`test_standard_news_manifest_never_creates_emergency_infographic` перестал
проходить, потому что строил манифест против **реальной** медиатеки машины
(`media_index_path` не передавался). Пока каждая локальная запись блокировалась
по правам, тест проходил случайно. Теперь на запрос `orca` локальная медиатека
уверенно отдала клип **солнечной электростанции**.

Это ровно тот `later debt`, что записан в `FIRST_OWNER_SHORT_2026-08-13`:
`_score_asset` (`src/media_library.py`) начисляет очки за `type` + `aspect_16_9`
+ `duration` и пропускает кандидата с нулём совпадений по ключевым словам. Пока
права блокировали всё, дефект был не виден. Тест починен по образцу `f69b81c` /
`10ae86d` — теперь он получает собственный пустой индекс. Сам ранжировщик в этом
слайсе не менялся: это отдельная работа, и теперь у неё есть воспроизводимый
пример.

## 6. Что этот слайс не делал

Код отбора, ранжирования и провайдеров не менялся. Единственная правка src —
`_normalize_asset` сохраняет `title`/`description`: их уже читает
`LocalLibraryStockProvider.search`, а писать их индекс не умел. В
`license_policy.json` добавлены только правила `local_library` для лицензий
`pexels`/`pixabay`; ни одно существующее правило не ослаблено, `default_deny`,
монотонность `review_required` и `requires_schema_version` не тронуты.
Дубликаты в карантине не удалялись. Локальный ранжировщик (`_score_asset`)
остаётся записанным долгом — см. 5.1. Вход локальных файлов в
`fullscreen_voiceover_v1` (`BLOCKER-L1`) не строился: это отдельный contract, и
он по-прежнему открыт. LOCAL-повтор в этом слайсе не выполнялся.
