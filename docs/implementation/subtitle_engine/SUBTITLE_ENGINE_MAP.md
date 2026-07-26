# Субтитры: единый движок (этап Q3)

Снято по коду на этапе Q3 (после `3973f27`).
Формат: **источник текста → источник тайминга → нарезка → валидация → файл → потребитель**.

Дополняет `docs/implementation/config_resolver/CONFIG_MAP.md` (вся конфигурация) и
`docs/implementation/localization_voice/LOCALIZATION_VOICE_MAP.md` (язык и голос).
Здесь — только путь «сценарий и озвучка → субтитры».

---

## 1. Что было до Q3

Один движок, целиком в `src/news/subtitles.py` (98 строк):

```
scene["on_screen_text"] или scene["narration"]
  → куски по 5 слов
  → длительность сцены / число кусков
  → subtitles.srt + subtitles.ass (ASS-заголовок зашит в код)
  → final_renderer вжигает ass_path
```

Два подтверждённых дефекта:

1. **W2 (аудит V1).** `on_screen_text` читался раньше `narration`, а все провайдеры
   сценария заполняют его через `text_analysis.first_words` — первые пять слов
   реплики. В кадре висели только эти пять слов, всю сцену (до 14.8 с).
2. **Стиль канала мёртв.** `channels/<id>/subtitle_style.json` читал только legacy
   `src/channel_loader.py`; новый рендер субтитров его не открывал — незакрытая
   часть этапа E2.

Плюс: не было ни одной проверки (пересечения, выход за сцену, потерянный текст), не
было resume, не было ссылки на озвучку и сценарий, и разбиение не знало ни про
предложения, ни про пунктуацию.

Отдельные реализации субтитров, найденные в репозитории на момент Q3:

| Место | Что делает | Решение Q3 |
|---|---|---|
| `src/news/subtitles.py` | SRT + ASS для News-to-Short / `fullscreen_voiceover_v1` | **переведён** на `src/subtitles/` (стал адаптером) |
| `src/layout_renderer.py` | рисует `subtitle_text` на кадре через PIL (legacy channel pipeline) | не тронут: это текст на кадре, а не файл субтитров |
| `src/production_plan/solar_vs_nuclear_render.py` | свой ASS-писатель для одного зафиксированного ролика | не тронут: исторический артефакт |
| `anime_factory/` | Whisper → `subtitles_raw.srt` | не тронут: отдельное приложение, STT вне Q3 |
| Story Card (`story_card_text_only_v1`) | субтитров нет (`subtitles_allowed=false`) | не тронут |

Второго движка не появилось: в продуктовом пайплайне он ровно один.

---

## 2. Вертикальный путь после Q3

```
script.json (ScriptResult → legacy_format)
  → ResolvedLocalization (src/localization): language, subtitle_language
  → voice_manifest.json (src/audio/voice_manifest)
  → SceneTimeline (src/audio/scene_timeline, этап B1)
  → SubtitleRequest → SubtitleEngine (src/subtitles/engine)
      segmentation → timing → validation
  → SubtitleCue[] + SubtitleValidationResult
  → subtitles.srt / subtitles.ass + subtitles_manifest.json
  → final_renderer (вжигает ass_path) → master_1080x1920.mp4 → preview
  → exporter (копирует subtitles.srt / subtitles.ass)
```

Границы сцен считает **только** `src/audio/scene_timeline.py`. Своего расчёта
длительностей в `src/subtitles/` нет.

---

## 3. Модули пакета

| Модуль | Отвечает за | Не отвечает за |
|---|---|---|
| `models.py` | контракты: `SubtitleCue`, `SubtitleSegment`, `SubtitlePolicy`, `SubtitleStyle`, `SubtitleRequest`, `SubtitleResult`, `SubtitleValidationResult`, коды проблем | что-либо делать |
| `segmentation.py` | где рвётся текст | время |
| `timing.py` | откуда берётся время | текст |
| `validation.py` | что ошибка, а что предупреждение | исправление |
| `style.py` | `channels/<id>/subtitle_style.json` → `SubtitleStyle` | список существующих стилей (он один: `capabilities.list_subtitle_styles`) |
| `serialization.py` | SRT и ASS | cue-модель |
| `manifest.py` | артефакт на диске, resume | нарезка |
| `engine.py` | сборка всего перечисленного | сеть, TTS, STT, alignment, рендер |

`src/news/subtitles.py` — адаптер пайплайна: `build_subtitles(script, output_dir)`
(подпись не менялась) и `build_subtitles_for_localization(...)`.

---

## 4. Иерархия источников тайминга

Фактическая, от точного к безопасному. `timing_source` пишется в каждый cue и в
манифест — «примерно» не бывает.

| Уровень | Код | Откуда данные | Есть ли сегодня |
|---|---|---|---|
| 1. по словам | `word_timestamps` | `voice_manifest.scenes[].word_timestamps` | **нет ни одного производителя.** Читатель включается только если данные физически лежат в манифесте **и** их количество совпадает с числом слов сцены. Whisper/forced alignment — вне Q3 |
| 2. по фразам | `segment_timestamps` | `voice_manifest.scenes[].segment_timestamps` | нет производителя; читатель есть, условия те же |
| 3. по сценам | `scene_timeline` | `build_scene_timeline(voice_manifest)`, иначе `actual_duration_sec` из `script.json` (его пишет тот же B1) | **основной рабочий уровень** |
| 4. плановый | `legacy_planned` | только `target_duration_sec` | компat-откат для проектов без озвучки; помечается предупреждением `legacy_timing_source` |
| — | `unavailable` | нет сцен / нет сценария | ошибка, не тайминг |

Любая некорректность в потаймингах (пропущенное поле, не число, NaN, конец раньше
начала, нарушенный порядок, несовпавшее число слов) отбрасывает **весь** уровень
целиком и опускает движок на следующий. Частично разобранным данным доверять
нельзя: субтитры, «почти» совпадающие с голосом, хуже честного уровня сцены.

**Ручной WAV не даёт потайминги слов.** Он даёт длительность — то есть уровень 3.

Текст сцены раскладывается внутри её **речевого** отрезка (`speech_duration_sec`);
пауза между сценами остаётся без субтитра. До Q3 реплика висела и в паузе.

---

## 5. Нарезка текста

Инвариант, который проверяют и валидатор, и тесты: **последовательность слов
сохраняется полностью**. Нарезка расставляет границы и переносы строк — она не
переписывает, не сокращает, не переставляет и не выбрасывает ни одного слова.

Правила по приоритету:

1. конец предложения (`.!?…:`), с поправкой на сокращения (`т.д.`, `млн.`, `др.`);
2. конец оборота (`,;—–`);
3. лимит символов (`max_lines × max_characters_per_line`) и лимит слов;
4. защиты: не оставлять последний cue из одного короткого слова; не отрывать число
   от следующего короткого слова («12 километров»); не начинать новый cue с одного
   слова, если конец предложения пришёлся на первый же токен.

`src.news.research_engine.split_sentences` **не переиспользуется**: он отбрасывает
фрагменты короче 9 символов (`len(part.strip()) > 8`), что для субтитров означало бы
потерю текста. Границы предложений считаются в `segmentation.py` по тем же знакам.

Число строк — жёсткое ограничение (три строки внизу вертикали налезают на
защищённую зону). Ширина строки — мягкое: если текст в лимит не влезает, берётся
минимальная ширина, при которой он укладывается в `max_lines`, а перебор
отмечается предупреждением `line_too_long`.

Морфологического движка нет и не планируется.

---

## 6. Политика и стиль: что чем управляет

| | `SubtitlePolicy` | `SubtitleStyle` |
|---|---|---|
| Влияет на | **где рвётся текст** и что считать нарушением | **как выглядит** субтитр |
| Попадает в cue | да (через границы) | нет |
| Попадает в ASS | нет | да (`Style:`-строка) |
| Источник | выводится из стиля (`SubtitlePolicy.from_style`) | `channels/<id>/subtitle_style.json` |

Значения `SubtitleStyle` по умолчанию дают **байт-идентичную** строку стиля тому,
что вжигалось до Q3:

```
Style: Default,Arial,72,&H00FFFFFF,&H00000000,1,4,0,2,80,80,260,1
```

Для `nature_science_news_ru` файл канала совпадает с этими значениями, поэтому
подключение E2 картинку не меняет — это проверяется тестом.

**Осознанное ограничение:** `safe_zone_bottom` (320 в файле канала) **не**
превращается в ASS `MarginV` (260 у проверенного рендера). Q3 — про единый контракт
и правильный тайминг, а не про смену дизайна. Отступ меняется только явным ключом
`margin_v`.

Ширина строки, если канал не задал `max_characters_per_line`, оценивается как
`(play_res_x − margin_left − margin_right) / (font_size × 0.5)` = 25 символов при
1080/80/80/72. Это оценка, а не измерение шрифта; запас надёжности даёт
`max_words_per_cue`.

---

## 7. Ошибки и предупреждения

**Ошибка** — артефакт нельзя отдавать рендеру. **Предупреждение** — субтитр
читается, но не идеален.

| Ошибки | Предупреждения |
|---|---|
| `missing_script`, `no_scenes`, `no_cues`, `empty_cue_text` | `cue_too_short`, `cue_too_long` |
| `duplicate_scene_id`, `unknown_scene_id`, `cue_without_scene` | `reading_speed_too_high` |
| `cue_order_invalid`, `cue_overlap` | `line_too_long`, `too_many_lines`, `orphan_short_line` |
| `negative_time`, `non_finite_time`, `end_not_after_start` | `gap_too_large`, `duplicate_cue_text` |
| `cue_outside_scene`, `cue_outside_narration` | `legacy_timing_source`, `narration_duration_unknown` |
| `text_not_covered`, `language_mismatch` | `on_screen_text_used`, `missing_scene_plan` |
| `narration_reference_mismatch`, `duplicate_subtitle_path`, `unsupported_format` | `legacy_artifact_without_metadata` |

Длительность cue и скорость чтения — **предупреждения**, а не ошибки: cue живёт
внутри своей сцены, а длину сцены задаёт озвучка. Двигать её движок субтитров не
имеет права; единственное, что он может, — честно сказать «здесь читать быстро».

Отсутствие `scene_id` — ошибка только там, где сценарий известен. Артефакт,
созданный до Q3, сцен не хранил вообще: для него это факт происхождения
(`legacy_artifact_without_metadata`), а не поломка. Валидатор специально не настолько
строг, чтобы старые проекты перестали читаться.

---

## 8. Локализации

У каждой локализации своё:

```
localizations/<id>/subtitles/subtitles.srt
localizations/<id>/subtitles/subtitles.ass
localizations/<id>/subtitles/subtitles_manifest.json
```

Каталог выводится из `localization_id`, а не из имени файла, поэтому русский SRT
физически не может попасть в папку английской версии. Язык субтитров берётся из
`ResolvedLocalization.subtitle_language` (этап D2/E2), а не из `script.json`:
контракт локализации специально различает язык озвучки и язык субтитров.

Артефакт другой локализации при resume не переиспользуется
(`localization_changed`). Автоматического перевода нет и в Q3 не появляется.

---

## 9. Манифест и resume

`subtitles_manifest.json` расширен **аддитивно**. Ключи, которые читают
существующие модули, остались на своих местах и с тем же смыслом:

| Ключ | Кто читает |
|---|---|
| `ass_path` | `src/news/final_renderer.py` (`subtitles=` фильтр) |
| `srt_path`, `ass_path` | `src/news/quality_check.py` (проверка «субтитры созданы») |
| `segments` (`{start, end, text}`) | тесты тайминга, внешние читатели |
| `status`, `language` | общий статус стадии |

Добавлено: `schema_version=2`, `engine`, `localization_id`, `subtitle_language`,
`timing_source`, `scene_timeline_source`, `narration_path`,
`narration_duration_sec`, `narration_fingerprint`, `script_fingerprint`, `formats`,
`paths`, `cue_count`, `scene_count`, `total_duration_sec`, `validation`, `policy`,
`style`, `cues`, `warnings`, `protected`, `generated_at`.

Секретов, ключей и ответов провайдеров в манифесте нет и быть не может: движок
субтитров ни одного провайдера не видит.

Решение resume (`plan_resume`):

| Причина | Переиспользуется |
|---|---|
| `protected_artifact` — файл помечен пользователем | **да, всегда** |
| `compatible` — та же локализация, тот же `script_fingerprint`, тот же `narration_fingerprint`, файлы на месте | да |
| `no_existing_artifact` | нет |
| `legacy_artifact_without_metadata` — артефакт до Q3 | нет |
| `localization_changed` | нет |
| `script_changed` | нет |
| `narration_changed` | нет |
| `artifact_files_missing` | нет |

`script_fingerprint` считается по языку и упорядоченной паре `scene_id` +
произносимый текст: правка визуального интента или ключевых слов субтитры не меняет
и перегенерацию не вызывает. `narration_fingerprint` — путь, длительность и уровень
тайминга; аудиофайл не открывается и не хешируется (другая озвучка всегда даёт
другую длительность или другой путь). Content-addressed кеша нет — его нет и в
остальном проекте.

`--force-stage` перезаписывает всё, кроме защищённого артефакта.

---

## 10. Потребители

| Потребитель | Как получает субтитры | Состояние после Q3 |
|---|---|---|
| `src/news/pipeline.py` стадия `subtitles` | `build_subtitles_for_localization` | **переведён** |
| `src/news/final_renderer.py` | `subtitles_manifest.json → ass_path` | без изменений (ключ тот же) |
| `src/news/quality_check.py` | `srt_path` + `ass_path` | без изменений |
| `src/news/exporter.py` | копирует `subtitles.srt` / `subtitles.ass` | без изменений (имена те же) |
| `src/news/preview_renderer.py` | режет `master_1080x1920.mp4`, в который субтитры уже вжаты | без изменений: превью получает **тот же** артефакт, только уже внутри видео |
| `src/content_creation/service.py` | запускает стадию `subtitles` | без изменений |
| `src/content_creation/capabilities.py` | описание стиля `documentary` | обновлено по факту |
| CLI `subtitles explain` / `validate` | движок напрямую, только чтение | **новое** |

---

## 11. Пример

Сцена (`scene_001`, речь 6.89 с, пауза 0.35 с), реплика:

> Учёные впервые записали звук, который издаёт ледник при таянии. Оказалось, что он слышен на 12 километров.

```
scene_001#01 [ 0.00 →  1.92]  Учёные впервые / записали звук,
scene_001#02 [ 1.92 →  4.11]  который издаёт / ледник при таянии.
scene_001#03 [ 4.11 →  6.89]  Оказалось, что он слышен / на 12 километров.
```

`timing_source=scene_timeline`, три cue вместо одного, весь текст в кадре,
последний cue заканчивается ровно на конце речи, пауза 6.89 → 7.24 без субтитра.
До Q3 это была **одна** реплика «Учёные впервые записали звук,» на все 7.24 с.

---

## 12. Чего в Q3 нет

Speech-to-text, Whisper, forced alignment, скачивания моделей, настоящего TTS,
автоматического перевода, LLM, Vision, поиска ассетов, рендера, изменения музыки,
редизайна субтитров, karaoke/highlight, UI, longform, миграции исторических
проектов. Ни один модуль `src/subtitles/` не ходит в сеть и не тратит деньги.
