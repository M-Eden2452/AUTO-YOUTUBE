# Команды AI-YouTube

Короткая шпаргалка на человеческом языке. Все команды безопасны: они ничего
не скачивают, не платят и не создают новых видео — только показывают, что
уже есть в системе.

Две точки входа:

- `./venv/Scripts/python.exe -m src.content_creation.cli` — **создание контента** (create,
  resume, wizard, capabilities);
- `./venv/Scripts/python.exe -B pipeline.py` — обслуживание, диагностика и старый
  channel/video pipeline.

## 1. Перейти в проект

```bash
cd /g/Projects/AI-YouTube
```

## 2. Запуск Python

Всегда через интерпретатор venv (без `source venv/Scripts/activate` тоже работает):

```bash
./venv/Scripts/python.exe --version
```

Если консоль ругается на русские буквы, добавьте перед командой `PYTHONIOENCODING=utf-8`.

## 3. Посмотреть Applications (приложения)

Приложение — это "режим работы" системы. Сейчас есть "Создание контента"
(работает) и "Нарезка и переработка видео" (запланировано, ещё не работает).

```bash
./venv/Scripts/python.exe -B pipeline.py applications list
```

Подробнее про одно приложение:

```bash
./venv/Scripts/python.exe -B pipeline.py applications inspect --application content_creator
```

## 4. Посмотреть Formats (форматы видео)

Формат — это разрешение и пропорции ролика (например, вертикальный short).

```bash
./venv/Scripts/python.exe -B pipeline.py formats list
```

Подробнее про один формат:

```bash
./venv/Scripts/python.exe -B pipeline.py formats inspect --format vertical_short
```

## 5. Посмотреть Templates (шаблоны/фирменные стили)

Шаблон — это готовый фирменный стиль ролика, например "Карточка с текстом".

```bash
./venv/Scripts/python.exe -B pipeline.py templates list
```

Только шаблоны для одного приложения или формата:

```bash
./venv/Scripts/python.exe -B pipeline.py templates list --application content_creator
./venv/Scripts/python.exe -B pipeline.py templates list --format vertical_short
```

## 6. Посмотреть Export Targets (площадки экспорта)

Куда можно опубликовать готовый ролик (YouTube Shorts, Instagram Reels и т.д.).

```bash
./venv/Scripts/python.exe -B pipeline.py export-targets list
```

Подробнее про одну площадку:

```bash
./venv/Scripts/python.exe -B pipeline.py export-targets inspect --target youtube_shorts
```

## 7. Посмотреть первый рабочий шаблон

Это тот самый шаблон, который уже использовался для видео с совой.

```bash
./venv/Scripts/python.exe -B pipeline.py templates inspect --template story_card_text_only_v1
```

Старое имя того же шаблона (работает так же, как имя выше):

```bash
./venv/Scripts/python.exe -B pipeline.py templates inspect --template story_card_short_v1
```

Добавьте `--json` к любой из команд выше, чтобы получить машиночитаемый ответ.

## 8. Существующие безопасные команды (уже реально работают)

```bash
./venv/Scripts/python.exe -B pipeline.py --help
./venv/Scripts/python.exe -B pipeline.py --news-to-short --news-action create --topic "пример темы" --dry-run --until-stage visual_plan
./venv/Scripts/python.exe -B pipeline.py --news-to-short --news-action run --job-id <job_id> --dry-run --stage asset_search
./venv/Scripts/python.exe -B pipeline.py --voice-action list --news-channel nature_science_news_ru
./venv/Scripts/python.exe -B pipeline.py --voice-action preflight --news-channel nature_science_news_ru --voice-profile <profile_id> --text "Короткий тест."
./venv/Scripts/python.exe -B pipeline.py --voice-action import-audio --job-id <job_id> --audio-file <path/to/manual.wav>
./venv/Scripts/python.exe -m unittest tests.test_story_card_short_renderer -v
./venv/Scripts/python.exe -m unittest tests.test_temporal_video_analysis -v
./venv/Scripts/python.exe -m unittest tests.test_semantic_decision_policy -v
./venv/Scripts/python.exe -m unittest tests.test_production_catalog_foundation -v
```

## 9. Готовое видео с совой (адаптивная версия)

```text
projects/story_card_owl_test/final_test_v2.mp4
```

## 10. Единый CLI создания контента (Stage 2E)

Новый канонический слой для создания контента: `src/content_creation/` (модели
`ContentCreationRequest`/`ContentCreationResult`, `service.py`, `cli.py`,
интерактивный `wizard.py`). Он не дублирует provider/voice/renderer/каталог —
только соединяет их. `pipeline.py` не менялся и остаётся отдельным legacy CLI.

Запуск: `./venv/Scripts/python.exe -m src.content_creation.cli <команда>`.

### 10.1. Environment check

```bash
./venv/Scripts/python.exe --version
```
Ожидается Python 3.13.13. Ничего не создаёт, не использует сеть.

### 10.2. Capabilities (что реально доступно сейчас)

```bash
./venv/Scripts/python.exe -m src.content_creation.cli capabilities --json
```
Показывает: шаблоны с их tested_status (`live_tested`/`mock_tested`/
`architecture_supported`), voice providers, subtitle styles, music options,
каналы. Read-only, без сети и оплаты, безопасно для повторного запуска.

### 10.3. Channels / Formats / Templates

```bash
./venv/Scripts/python.exe -m src.content_creation.cli channels list
./venv/Scripts/python.exe -m src.content_creation.cli formats list
./venv/Scripts/python.exe -m src.content_creation.cli templates list
./venv/Scripts/python.exe -m src.content_creation.cli templates show --template story_card_short_v1
```
Read-only, файлов не создают.

### 10.4. Voice providers / profiles

```bash
./venv/Scripts/python.exe -m src.content_creation.cli voices providers
./venv/Scripts/python.exe -m src.content_creation.cli voices profiles --channel nature_science_news_ru
./venv/Scripts/python.exe -m src.content_creation.cli voices show --channel nature_science_news_ru --voice-profile "Дом"
```
Реально зарегистрированы только `disabled`, `elevenlabs` (платный), `audio_file`
(ручной WAV). `local_stub`/MOSS-TTS никогда не показываются как production-опция.
Read-only, без сети (ElevenLabs здесь только проверяет наличие ключа в `.env`,
не звонит в API).

### 10.4.1. Какой голос будет у локализации и почему (этап D2/E2)

```bash
./venv/Scripts/python.exe -m src.content_creation.cli voices explain --channel nature_science_news_ru
```

Показывает для каждой языковой версии: язык, locale, язык субтитров, провайдера,
профиль голоса, `voice_id`, модель, политику fallback, источник озвучки, наличие
ключа («настроен / не настроен») и — если TTS не будет вызван — почему.

Отдельный язык, конкретный проект, полный разбор по слоям, JSON:

```bash
./venv/Scripts/python.exe -m src.content_creation.cli voices explain --channel nature_science_news_ru --language en
```

```bash
./venv/Scripts/python.exe -m src.content_creation.cli voices explain --channel nature_science_news_ru --language ru --project-id <project_id>
```

```bash
./venv/Scripts/python.exe -m src.content_creation.cli voices explain --channel nature_science_news_ru --trace --json
```

- если у языка нет подходящего голоса, команда говорит об этом прямо и возвращает
  код 1 — вместо того чтобы молча озвучить английский текст русским голосом;
- если готовая озвучка уже лежит в проекте, видно, что она будет переиспользована
  и повторная генерация не нужна;
- значение ключа API не выводится ни в каком виде;
- команда ничего не запускает и ничего не меняет: ни сети, ни TTS, ни рендера,
  ни записи в проект.

### 10.5. Subtitle styles

```bash
./venv/Scripts/python.exe -m src.content_creation.cli subtitles list
```
Реально существуют только `disabled` и `documentary` (арифметическая нарезка
без привязки к реальному таймингу озвучки, `src/news/subtitles.py`). Стили
`phrase`/`shorts_large`/`word_by_word` не реализованы и намеренно не
показываются.

### 10.6. Story Card create (dry-run, безопасно)

```bash
./venv/Scripts/python.exe -m src.content_creation.cli create \
  --format vertical_short --template story_card_text_only_v1 \
  --channel nature_pulse --language ru \
  --text "Кошка слышит звуки, которые человеческое ухо не замечает." \
  --source-asset projects/story_card_owl_test/final_test.mp4 \
  --voice-provider disabled --subtitles disabled \
  --dry-run --projects-root /tmp/cc_test
```
Ничего не создаёт на диске (только план). Уберите `--dry-run` и
`--projects-root /tmp/cc_test`, чтобы реально создать проект в `projects/` и
отрендерить карточку (без сети, без оплаты - source-asset обязателен, поиска
ассетов в этом workflow пока нет).

### 10.7. Fullscreen Voiceover create + paid approval gate

```bash
./venv/Scripts/python.exe -m src.content_creation.cli create \
  --format vertical_short --template fullscreen_voiceover_v1 \
  --channel nature_science_news_ru --language ru \
  --topic "Почему вороны запоминают человеческие лица" \
  --voice-provider elevenlabs --voice-profile ru_dom \
  --subtitles documentary --music disabled
```
Без `--approve-paid-generation` команда доходит только до конца стадии
`voice` (без платного вызова) и останавливается со статусом
`prepared_awaiting_paid_approval`, печатая точную команду для продолжения.
Платный вызов ElevenLabs выполняется только с явным флагом:

```bash
./venv/Scripts/python.exe -m src.content_creation.cli create ... \
  --resume --project-id <project_id> --approve-paid-generation
```

Источник сценария выбирается явно через `--input-mode` (`topic` | `article_url`
| `pasted_script` | `script_file`), с соответствующим полем
(`--topic`/`--source-url`/`--pasted-script`/`--script-file`). Ссылки на
страницы поиска (Google/Bing/Yandex/DuckDuckGo) отклоняются до сети:

```bash
./venv/Scripts/python.exe -m src.content_creation.cli create \
  --format vertical_short --template fullscreen_voiceover_v1 \
  --channel nature_science_news_ru --language ru \
  --input-mode article_url --source-url "https://example.com/real-article" \
  --voice-provider disabled --subtitles documentary
```

### 10.8. Manual WAV (без сети и без оплаты)

```bash
./venv/Scripts/python.exe -m src.content_creation.cli create \
  --format vertical_short --template fullscreen_voiceover_v1 \
  --channel nature_science_news_ru --language ru --topic "..." \
  --voice-provider audio_file --audio-file path/to/manual.wav
```
Ручной WAV никогда не требует `--approve-paid-generation` (это не платный
провайдер).

### 10.9. Список проектов / Resume / Status / Validate

Показать все проекты (обеих внутренних систем хранения) одной командой:

```bash
./venv/Scripts/python.exe -m src.content_creation.cli project list
```

Подробности по одному проекту — стадии, качество, путь к готовому MP4, файлы лицензий:

```bash
./venv/Scripts/python.exe -m src.content_creation.cli project status --project-id <id>
./venv/Scripts/python.exe -m src.content_creation.cli project status --project-id <id> --json
```

Продолжить проект и подтвердить платную озвучку:

```bash
./venv/Scripts/python.exe -m src.content_creation.cli resume --project-id <id> --approve-paid-generation
```

Проверка политики канала:

```bash
./venv/Scripts/python.exe -m src.content_creation.cli project validate --project-id <id>
```

`project list` и `project status` работают для любого проекта. `project validate` пока
доступна только для проектов `story_card_text_only_v1` (у них есть `project.json`).

### 10.9.1. Отчёт о правах на материалы

Показывает все материалы, которые проект реально использует, — откуда взяты, по какой
лицензии, и что нельзя подтвердить:

```bash
./venv/Scripts/python.exe -m src.content_creation.cli project rights-report --project-id <id>
./venv/Scripts/python.exe -m src.content_creation.cli project rights-report --project-id <id> --json
```

Работает для проектов обоих типов. Читает `assets/assets_manifest.json` (выбранные
визуальные материалы), `assets/missing_assets.json` (сцены без материала),
`assets/music/music_manifest.json` (музыка), `assets/sources.json` (резервный источник)
и `evidence/evidence_manifest.json`. Один и тот же материал не показывается дважды.

Четыре статуса:

| Статус | Что означает |
|---|---|
| `подтверждено` | есть лицензия, ссылка на источник и контрольная сумма, рендер разрешён |
| `требует проверки` | часть данных есть, но подтвердить право нельзя без человека |
| `нет данных` | о материале не записано ничего |
| `заблокировано` | материал прямо запрещён политикой лицензий |

Коды возврата: `0` — блокирующих проблем нет (даже если есть «требует проверки» или
«нет данных»); `1` — есть заблокированный материал **или** сцена без материала вообще.

Отчёт только читает файлы проекта и ничего в них не меняет. Он **не является юридическим
подтверждением прав**: статусы «требует проверки» и «нет данных» нужно закрывать вручную.

### 10.10. Output path (Phase 13)

После успешного `create` CLI печатает точный абсолютный путь, путь
относительно проекта, размер файла, длительность, разрешение и наличие
аудиодорожки - путь никогда не приходится угадывать.

### 10.11. Interactive Terminal Wizard

```bash
./venv/Scripts/python.exe -m src.content_creation.cli wizard
```
Интерактивный мастер (стрелки + Enter через `questionary`). Списки формата/
шаблона/канала/языка/голоса/субтитров/музыки берутся из тех же registries, что
и у `create` - второго списка в коде нет. В неинтерактивном терминале (нет TTY)
автоматически падает на обычные нумерованные вопросы через `input()`.

**Wizard navigation (Stage 2E.1).** После заполнения настроек мастер
показывает итоговую сводку и меню: `Запустить`, `Изменить формат/шаблон/
канал/язык/источник сценария/озвучку/субтитры/музыку`, `Начать
заново`, `Отмена`. Режим озвучки и режим тайминга не спрашиваются - они
определяются политикой шаблона. Изменение формата сбрасывает несовместимый шаблон;
изменение шаблона пересчитывает доступные voice/subtitles/music options и
очищает значения, которые больше не применимы (например disabled voice
очищает voice_profile). Никакой проект не создаётся до финального
подтверждения запуска.

**Language selection.** Язык выбирается из списка (`Русский`/`English`/
`Español` -> `ru`/`en`/`es`), список берётся из единого
`src.content_creation.languages` каталога (используется и CLI, и мастером).
При выборе языка мастер предупреждает (не блокирует), если у канала нет
voice profile для этого языка или канал не поддерживает язык вообще.

**Источник сценария** (только для `fullscreen_voiceover_v1` - Story Card его
не спрашивает вовсе, только текст карточки + локальный ассет):
- `topic` - тема, сценарий строится автоматически;
- `article_url` - прямая ссылка на статью, проверяется до сетевого вызова;
- `pasted_script` - готовый текст сценария целиком;
- `script_file` - путь к `.txt`/`.md` файлу, проверяется существование,
  расширение и кодировка (UTF-8) до какого-либо сетевого вызова.

**Article URL validation.** Ссылки на страницы поиска отклоняются ДО сети:
`google.*/search`, `bing.com/search`, `yandex.*/search`, `duckduckgo.com`.
Проверяются также схема (`http`/`https`), наличие домена и длина ссылки.
При отклонении мастер предлагает: ввести другую ссылку, использовать только
тему, вставить готовый текст, или отменить.

**Network error handling.** HTTP 429/403, timeout, connection error, пустая
или невалидная статья (редирект на логин/капчу) никогда не показывают
Python traceback в мастере: печатается короткое сообщение и предлагается
`Повторить попытку` / `Использовать только тему` / `Изменить источник
сценария` / `Отмена`, введённые настройки не теряются. В неинтерактивном
`create` та же ошибка возвращает ненулевой exit code и (`--json`)
machine-readable `{"status":"failed","error":...,"reason":...,"retryable":...}`.
Полный traceback показывается только с явным `--debug`.

**Local music file.** `--music local_file --music-path <файл>` (и в мастере,
и в `create`) обязательно требует существующий файл с поддерживаемым расширением
(`.mp3/.wav/.m4a/.aac/.flac/.ogg`); `disabled` всегда очищает путь. Если
шаблон не поддерживает музыку вообще (`story_card_text_only_v1` - renderer
пишет `audio=False`), вопрос о музыке не показывается вовсе.

Для `fullscreen_voiceover_v1` музыка теперь действительно подмешивается: трек
зацикливается на всю длительность ролика и автоматически приглушается под речь
(sidechain ducking), громкость по умолчанию `0.10`. Система записывает
`assets/music/music_manifest.json` с путём, размером, SHA-256 и пометкой о правах.

```bash
./venv/Scripts/python.exe -m src.content_creation.cli create \
  --format vertical_short --template fullscreen_voiceover_v1 \
  --channel nature_science_news_ru --language ru \
  --input-mode topic --topic "Почему киты поют" \
  --voice-provider elevenlabs --voice-profile "Дом" \
  --subtitles documentary \
  --music local_file --music-path music/my_track.mp3 \
  --prepare-only
```

Права на музыкальный файл **не проверяются автоматически** - в манифесте они
помечены как `unverified_user_supplied`. Используйте только свою или
лицензированную музыку.

**`--no-icons`** переключает мастер на ASCII-маркеры (`[*] [>] [OK] [!] [X]`)
вместо эмодзи - полезно при проблемной кодировке терминала:
```bash
./venv/Scripts/python.exe -m src.content_creation.cli wizard --no-icons
```

**`--debug`** отключает перехват классифицированных ошибок (429/403/URL/
файл) и показывает полный traceback - для разработки, не для обычного
использования:
```bash
./venv/Scripts/python.exe -m src.content_creation.cli create ... --debug
```

**Отмена без создания проекта:** на любом шаге, включая финальное
подтверждение сводки, выбор "Отмена" не создаёт и не изменяет ничего на
диске.

**Первый вопрос мастера - "Что делаем?"**: создать новый ролик или продолжить
незавершённый. В списке продолжения показано название ролика и стадия, на
которой он остановился. Продолжение работает с тем же `project_id`, не
переспрашивает формат/канал/тему и **не генерирует озвучку заново**, если она
уже готова. Пока поддерживается только `fullscreen_voiceover_v1`: у story card
нет стадий, и его нужно создавать заново.

**Название ролика** спрашивается отдельно и предлагается автоматически (по теме
или первому предложению сценария) - достаточно нажать Enter. Именно из него
строится имя папки проекта:

```text
Название: Почему вороны запоминают человеческие лица
Папка:    projects/2026-07-25_pochemu-vorony-zapominayut-chelovecheskie-lica
```

Кириллица транслитерируется, длина ограничена, запрещённые для Windows символы
и имена не попадают в путь, а при совпадении названий добавляется `-2`, `-3`.
Существующие проекты со старыми именами не переименовываются и открываются
как раньше.

### 10.12. Troubleshooting

- `template_id ... is not compatible with format_id ...` - формат и шаблон не
  совпадают в каталоге; смотрите `templates list`.
- `source_asset_path is required` - для Story Card поиск ассетов не подключён,
  нужен локальный файл.
- `Could not resolve voice profile for: ...` - опечатка в `--voice-profile`;
  смотрите `voices profiles --channel ...`.
- `Это ссылка на страницу поиска, а не на статью.` - вставлена ссылка на
  выдачу поиска (Google/Bing/Yandex/DuckDuckGo), а не на саму статью.
- `Article request failed with HTTP 429/403.` - сайт ограничил доступ;
  повторите позже, используйте тему или вставьте текст сценария вручную.
- `Для local_file нужен путь к аудиофайлу.` / `Файл не найден` - проверьте
  `--music-path` и расширение файла.
- Ошибки валидации печатаются одной строкой без traceback; необработанный
  traceback - признак настоящего бага, а не ожидаемой ошибки ввода. Полный
  traceback можно получить намеренно через `--debug`.

### 10.13. Сценарий: движки и проверка (этап Q1)

Всё офлайн, бесплатно, ничего не пишется без `--out`.

```bash
./venv/Scripts/python.exe -m src.content_creation.cli script providers
```

```bash
./venv/Scripts/python.exe -m src.content_creation.cli script generate --text "Текст статьи..." --out out/script.json
```

```bash
./venv/Scripts/python.exe -m src.content_creation.cli script validate --script-file out/script.json
```

- `--provider legacy_template` вернёт прежний шаблонный сценарий из шести фраз;
- `--source-kind user_script` означает, что вы передали **готовый** сценарий, и
  ни одно слово в нём не будет переписано;
- призыв к действию добавляется только с `--include-cta`.

### 10.14. Визуальный план: что показывать в каждой сцене (этап Q2)

Строит план по готовому `script.json`. Ничего не скачивает, не выбирает
финальный файл, не запускает Vision и не рендерит.

```bash
./venv/Scripts/python.exe -m src.content_creation.cli visual-plan planners
```

```bash
./venv/Scripts/python.exe -m src.content_creation.cli visual-plan build --script-file out/script.json --claims-file out/claims.json --out out/visual_plan.json
```

```bash
./venv/Scripts/python.exe -m src.content_creation.cli visual-plan intents --plan-file out/visual_plan.json
```

```bash
./venv/Scripts/python.exe -m src.content_creation.cli visual-plan validate --plan-file out/visual_plan.json --script-file out/script.json
```

- `build` показывает для каждой сцены предмет, действие, место, эпоху, тип кадра
  и цепочку запросов от точного к общему;
- `intents` печатает только запросы — удобно, чтобы глазами проверить, что сцены
  ищут разное;
- `--claims-file` необязателен, но с ним точнее определяется главная тема видео;
- запросы выводятся на языке сценария и помечаются `(нужен перевод)`: слоя
  перевода в проекте нет, и подставлять приблизительный английский вместо
  названного в тексте животного или страны система не будет.

### 10.15. Откуда берётся каждая настройка (этап D1)

Показывает для канала таблицу «параметр → значение → откуда взято». Только чтение:
ни сети, ни оплаты, ни записи файлов.

```bash
./venv/Scripts/python.exe -m src.content_creation.cli channels show --channel nature_science_news_ru --explain
```

С разбором по слоям и в JSON:

```bash
./venv/Scripts/python.exe -m src.content_creation.cli channels show --channel nature_science_news_ru --explain --trace
```

```bash
./venv/Scripts/python.exe -m src.content_creation.cli channels show --channel nature_science_news_ru --explain --json
```

Можно уточнить, для какого именно запуска считать: `--template`, `--format`,
`--language`, `--project-id`.

- стрелка `←` показывает победивший слой, а следом — файл, из которого значение взято;
- `template_policy_overrode_channel` означает, что политика шаблона перекрыла
  настройку канала (сейчас так работает `voice.fallback_policy`);
- `no_consumer_yet` означает, что настройка в файле есть, но её пока никто не читает;
- ключи API показываются только как «настроен / не настроен» — их значения система
  не читает и никуда не выводит;
- команда ничего не меняет в пайплайне: она объясняет то, что уже происходит.

## 11. ЗАПЛАНИРОВАНО, НО ПОКА НЕ РАБОТАЕТ

Эти команды пока не существуют. Не пытайтесь их запускать - они будут
добавлены на следующих этапах.

```bash
./venv/Scripts/python.exe -B pipeline.py creator create ...
./venv/Scripts/python.exe -B pipeline.py channels list
./aiyt
./venv/Scripts/python.exe -B pipeline.py story-card batch --queue <queue.json>
./venv/Scripts/python.exe -B pipeline.py repurpose create ...
./venv/Scripts/python.exe -m src.content_creation.cli create --format longform ...
./venv/Scripts/python.exe -m src.content_creation.cli create --format horizontal_clip ...
```

`longform`/`horizontal_clip` пока не имеют ни одного зарегистрированного
шаблона в Production Catalog, поэтому оба формата помечены `enabled=false` и не
предлагаются в wizard. Формат включается только вместе с появлением рабочего
шаблона. Video Repurposer (`video_repurposer`) зарегистрирован в
каталоге, но отключён. Полноценный web/desktop UI не разрабатывается - вместо
него есть Interactive Terminal Wizard (10.11).
