---
status: historical
document_date: 2026-07-18
---

# AI-YouTube: карта проекта, приложения и план разделения

> **HISTORICAL (2026-07-18) — не актуальная карта проекта.** Документ называет
> себя «актуальной картой» и описывает `pipeline.py` как основной вход, а
> `asset_finder` / `video_asset_engine` — как действующую asset-систему. Оба
> утверждения устарели: канонический CLI — `python -m ai_youtube`, канонический
> retrieval — `src/assets/**` + `src/providers/**`. Current truth:
> [SYSTEM_MAP.md](current/SYSTEM_MAP.md) и [AGENTS.md](../AGENTS.md);
> классификация и архивация этого файла принадлежат **PLAN-12**.

Дата обзора: 2026-07-18.

Этот документ объясняет проект как набор рабочих направлений. Его цель - помочь быстро понять, что лежит в каждой папке, зачем нужны файлы, как запускаются части системы, что уже работает, а что стоит доделать перед будущим пользовательским интерфейсом.

## 1. Общая картина

Сейчас `AI-YouTube` - это уже не одно маленькое приложение, а локальный набор инструментов для видеопроизводства:

1. **Main YouTube Pipeline** - основной генератор роликов по структуре `channels/`, `content/`, `src/`, `pipeline.py`.
2. **Anime Factory** - отдельный pipeline в `anime_factory/` для поиска удачных фрагментов в локальном anime/mp4 и рендера YouTube Shorts.
3. **Media/Audio Utilities** - пока не отдельное приложение, но уже часто используемый рабочий слой вокруг `ffmpeg`, `outputs/audio_edits/` и ручных аудио/видео операций.
4. **MOSS voice testing** - локальные тесты TTS/voice clone через `MOSS_TTS_Nano`, `assets/voice_samples/`, `scripts/test_moss_voices.py`.
5. **Legacy MVP** - старые скрипты в `legacy/`, которые показывают историю проекта, но уже не должны быть основной точкой развития.

Главная архитектурная мысль: в будущем лучше разделить проект не по случайным папкам, а по приложениям и общим библиотекам.

Рекомендуемая модель:

```text
apps/
  youtube_pipeline/
  anime_factory/
  media_tools/
  ui/
packages/
  core/
  media/
  providers/
  storage/
```

Пока физически структура другая, но логически проект уже движется именно туда.

## 2. Корень проекта

`pipeline.py` - главная точка входа основного YouTube pipeline. Загружает конфиг, подмешивает channel/video task, строит планы, генерирует голос, музыку, ассеты, рендерит видео, пишет метаданные и Obsidian-заметку. Также содержит сервисные режимы: индекс ассетов, очистка temp, отчет по библиотеке, тесты MOSS.

`README.md` - текущая вводная документация. Описывает запуск основного pipeline, multi-channel подход, MOSS-TTS и структуру проекта. Часть текста в старых файлах выглядит битой кодировкой в консоли, но смысл README все еще полезен.

`requirements.txt` - зависимости основного pipeline: MoviePy, NumPy, Pillow, imageio-ffmpeg, python-dotenv, OpenAI SDK, requests, PyYAML.

`.env.example` - безопасный пример переменных окружения: `OPENAI_API_KEY`, `PEXELS_API_KEY`, `PIXABAY_API_KEY`, `UNSPLASH_ACCESS_KEY`, `ELEVENLABS_API_KEY`.

`.env` - локальные секреты. Не читать вслух, не коммитить, не вставлять в документы.

`.gitignore` - правила исключения. Уже правильно исключает `.env`, `venv/`, `MOSS_TTS_Nano/`, большие медиа, outputs, кеши ассетов, аудио, видео и временные файлы.

`venv/` - локальное окружение Python для основного проекта. Это не код приложения.

`MOSS_TTS_Nano/` - локально скачанный внешний проект MOSS-TTS-Nano. Используется как зависимость для тестового/локального TTS, но не является частью репозитория.

`__pycache__/` - кеш Python. Не важен для архитектуры.

`subtitles/` - сейчас папка-заготовка. В основном pipeline почти не используется; в Anime Factory субтитры живут внутри `anime_factory/episodes/...`.

## 3. Основное приложение: Main YouTube Pipeline

### Назначение

Основной pipeline делает длинные или короткие cinematic/documentary видео по заранее подготовленным данным:

```text
config + channel profile + content task
-> quote_plan
-> youtube_metadata
-> scene_plan
-> voice_manifest
-> music_plan
-> asset_plan
-> render_plan
-> final mp4 + thumbnail + self_eval + Obsidian note
```

### Запуски

Быстрый старый dev-режим:

```powershell
python pipeline.py --dev
```

Новый multi-channel режим:

```powershell
python pipeline.py --channel quotes --video thoughts_too_late_001 --dev
python pipeline.py --channel psychology --video overloaded_mind_001 --dev
python pipeline.py --channel survival --video juliane_koepcke_001 --dev
```

Production:

```powershell
python pipeline.py --channel quotes --video thoughts_too_late_001 --prod
```

Только планы без рендера:

```powershell
python pipeline.py --channel quotes --video thoughts_too_late_001 --skip-render
```

Сервисные режимы:

```powershell
python pipeline.py --index-assets
python pipeline.py --asset-report
python pipeline.py --clean-temp
python pipeline.py --test-moss-tts
python pipeline.py --test-moss-voices
```

### Текущий этап

Состояние: рабочий локальный pipeline-прототип с несколькими каналами. Он уже умеет читать video tasks, строить планы, искать/кешировать ассеты, рендерить видео и делать self-eval. При этом код еще смешивает несколько эпох: старый quotes-MVP, documentary-video pipeline, size comparison engine и voice/TTS.

Что доделать:

- отделить CLI от бизнес-логики, чтобы будущий UI мог запускать pipeline как сервис;
- сделать единую модель `Project`, `Channel`, `VideoTask`, `RenderJob`;
- вынести работу с медиа в отдельный пакет;
- привести кодировку старых русских документов/строк к нормальному UTF-8;
- добавить постоянный job history: статус, логи, путь к результатам, ошибки;
- определить, какие outputs являются временными, а какие являются архивом результата.

## 4. `src/`: ядро основного pipeline

`src/__init__.py` - маркер Python-пакета. Нужен, чтобы `src.*` импортировался как пакет.

`src/utils.py` - общие функции: путь от корня проекта, создание папок, чтение/запись JSON.

`src/config_loader.py` - загружает `config/video_style.json` и переключает режимы `dev`, `prod`, `prod-preview`, `cinematic-preview`. Меняет resolution, fps, output filename, font size и длительность сцен.

`src/channel_loader.py` - соединяет базовый конфиг, `channels/<channel>/channel_config.json`, `channels/<channel>/style.json` и конкретный content task. Также задает per-video output paths и Obsidian paths.

`src/quote_generator.py` - строит `quote_plan`. В старом режиме использует зашитые Peterson-идеи. В новом video task режиме берет сцены из `content/` и превращает их в список quote/items.

`src/youtube_metadata.py` - генерирует YouTube metadata: заголовки, описание, теги, chapters, pinned comment, hooks, thumbnail prompt. Пишет `youtube_metadata.json`.

`src/scene_planner.py` - строит `scene_plan`. В старом режиме создает intro/thought/final сцены из quote plan. В новом режиме берет готовые сцены из video task и нормализует поля для рендера.

`src/intro_generator.py` - строит небольшой intro plan для render plan. Сейчас это легкий планировщик, не полноценный генератор заставок.

`src/voice_engine.py` - создает `voice_manifest`. Поддерживает ElevenLabs, локальный stub и fallback на MOSS-TTS-Nano. Кеширует голос по hash текста и настроек. Потом подгоняет длительность сцен под длительность озвучки.

`src/tts_providers/__init__.py` - маркер подпакета TTS-провайдеров.

`src/tts_providers/moss_tts_provider.py` - адаптер к локальному MOSS-TTS-Nano. Проверяет репозиторий, выбирает Python из MOSS venv, запускает синтез через subprocess.

`src/music_finder.py` - старый фасад для music plan. Для video task переключается на `music_engine.build_music_plan_v2`, иначе ищет локальный fallback `music/background.mp3`.

`src/music_engine.py` - новый music planner. Ищет музыку в локальной media library, может скачивать через Pixabay API, регистрирует треки в `media_index.json`, задает volume и ducking под голос.

`src/music_tools.py` - фактическое добавление музыки к видео через MoviePy. Умеет loop music, уменьшать громкость под голос, накладывать voice clips и экспортировать финальный mp4.

`src/asset_finder.py` - старый фасад выбора ассетов. Для video task переключается на `video_asset_engine.build_documentary_asset_plan`. В старом режиме ищет картинки через Pexels/Pixabay или создает placeholder.

`src/video_asset_engine.py` - новый documentary visual engine. Ищет локальные видео в media library, ранжирует по ключевым словам, при нехватке качает видео с Pexels/Pixabay, делает thumbnails, регистрирует ассеты, подбирает несколько клипов на сцену и fallback generated motion.

`src/media_library.py` - библиотека медиа. Создает структуру `assets/library`, ведет `media_index.json`, ищет локальные ассеты по keywords/mood/channel, предотвращает дубликаты, генерирует semantic filenames, делает отчет.

`src/image_tools.py` - утилиты Pillow: подгонка изображения под размер, загрузка шрифтов, создание placeholder-изображений.

`src/layout_renderer.py` - отрисовка кадров и текстовых оверлеев. Используется `video_renderer.py` для документального кадра и классического quote-card стиля.

`src/video_renderer.py` - строит `render_plan` и рендерит видео. Рендерит сцены во временные mp4, склеивает их через ffmpeg, валидирует длительность/размер, добавляет музыку и голос.

`src/thumbnail_generator.py` - создает thumbnail для video task. Использует `thumbnail_engine` для documentary thumbnail или fallback logic.

`src/thumbnail_engine.py` - documentary thumbnail engine. Берет кадр/картинку, делает цветокоррекцию, фон, текст, fallback background.

`src/size_comparison_engine.py` - отдельный engine для cinematic size comparison роликов. Читает CSV с объектами и размерами, строит camera plan, готовит силуэты, рендерит size comparison видео, self-eval и Obsidian note.

`src/self_eval.py` - проверка результата. Проверяет существование mp4, длительность, resolution, количество сцен, риски overflow текста, ассеты, музыку, metadata, Obsidian note и documentary quality rules.

`src/obsidian_exporter.py` - экспортирует Markdown-заметку в Obsidian vault или fallback в outputs. Смысл: человек читает status, планы, ссылки на видео и ассеты.

`src/providers/__init__.py` - объединяет функции провайдеров Pexels, Pixabay, Unsplash.

`src/providers/pexels_provider.py` - тонкий клиент поиска видео через Pexels API.

`src/providers/pixabay_provider.py` - тонкий клиент поиска видео, изображений и музыки через Pixabay API.

`src/providers/unsplash_provider.py` - тонкий клиент поиска изображений через Unsplash API.

## 5. `config/`

`config/video_style.json` - базовый конфиг основного pipeline. Хранит тип видео, тему, язык, стиль, resolution/fps, длительности, шрифты, цвета, музыку, пути к output plans, настройки OpenAI, Pexels/Pixabay, TTS, asset library, fallback behavior и Obsidian.

Текущее состояние: это исторически главный конфиг, но он стал слишком широким. В будущем его лучше разделить:

```text
config/base.yaml
config/render_profiles.yaml
config/providers.yaml
config/apps/youtube_pipeline.yaml
```

## 6. `channels/`

`channels/quotes/channel_config.json` - профиль канала цитат/мыслей: id, название, язык, формат, Obsidian folder.

`channels/quotes/style.json` - визуальный и звуковой стиль канала quotes.

`channels/psychology/channel_config.json` - профиль канала psychology.

`channels/psychology/style.json` - стиль psychology: документальный вайб, субтитры, музыка, голос, ассеты.

`channels/survival/channel_config.json` - профиль канала survival.

`channels/survival/style.json` - стиль survival. В коде есть отдельная логика ранжирования survival-видео по rainforest/jungle/river и штраф за city/business/office.

`channels/size_comparison/channel_config.json` - профиль канала size comparison.

`channels/size_comparison/style.json` - стиль size comparison.

Смысл папки: отделить творческую/брендовую настройку канала от общего кода. Это правильное направление.

## 7. `content/`

`content/quotes/thoughts_too_late_001.json` - готовый video task для канала quotes. Содержит chosen title, thumbnail text, description, disclaimer, список сцен, screen text, authors, mood, visual keywords.

`content/psychology/overloaded_mind_001/script.txt` - текстовый сценарий psychology-ролика.

`content/psychology/overloaded_mind_001/research_notes.md` - исследовательские заметки.

`content/psychology/overloaded_mind_001/visual_plan.md` - план визуального ряда.

`content/psychology/overloaded_mind_001/music_direction.txt` - направление для музыки.

`content/psychology/overloaded_mind_001/scene_notes.json` - machine-readable video task для psychology. Именно этот файл читает `channel_loader.py`, если нет `content/<channel>/<video>.json`.

`content/psychology/overloaded_mind_001/diagram_01_placeholder.txt`, `diagram_02_placeholder.txt`, `diagram_03_placeholder.txt` - текстовые placeholders для будущих диаграмм.

`content/survival/juliane_koepcke_001.json` - готовый video task для survival-ролика.

`content/size_comparison/sea_monsters_001/data.csv` - таблица объектов и размеров для size comparison.

`content/size_comparison/sea_monsters_001/scene_notes.json` - описание size comparison задачи.

Смысл папки: здесь должен жить креатив конкретного ролика. Код не должен придумывать заново то, что уже задано в content task.

## 8. `manual_assets/`

`manual_assets/psychology/overloaded_mind_001/images/.gitkeep` - место для ручных картинок.

`manual_assets/psychology/overloaded_mind_001/video/.gitkeep` - место для ручных видеофрагментов. `video_asset_engine.py` умеет брать видео отсюда и матчить по номеру сцены/id/keywords.

`manual_assets/psychology/overloaded_mind_001/audio/.gitkeep` - место для ручного аудио.

`manual_assets/psychology/overloaded_mind_001/references/.gitkeep` - место для референсов.

`manual_assets/psychology/overloaded_mind_001/diagrams/diagram_01_information_noise.svg` - диаграмма information noise.

`manual_assets/psychology/overloaded_mind_001/diagrams/diagram_02_dopamine_loop.svg` - диаграмма dopamine loop.

`manual_assets/psychology/overloaded_mind_001/diagrams/diagram_03_attention_fragmentation.svg` - диаграмма attention fragmentation.

Смысл папки: ручные ассеты для конкретного video task. Это хорошо отделяет авторский материал от скачанного кеша.

## 9. `assets/`

`assets/images/.gitkeep` - держит пустую папку картинок в Git.

`assets/voice_samples/README.md` - инструкция для voice reference samples: короткие чистые аудио 5-20 секунд, один голос, без шума.

`assets/library/metadata/media_index.example.json` - пример индекса media library. Настоящий `media_index.json` игнорируется Git.

Скрытые/игнорируемые по `.gitignore` подпапки:

- `assets/library/videos/` - кеш скачанных или локально зарегистрированных видео.
- `assets/library/images/` - кеш изображений.
- `assets/library/music/` - кеш музыки.
- `assets/library/thumbnails/` - thumbnails для видео ассетов.
- `assets/cache/` - вспомогательный кеш.

Смысл папки: хранение ассетов, но не кода. Большие медиа не должны попадать в Git.

## 10. `music/`

`music/.gitkeep` - держит папку в Git.

Ожидаемые локальные файлы вроде `music/background.mp3` не коммитятся. Основной pipeline использует эту папку как fallback для музыки.

## 11. `outputs/`

`outputs/asset_library_report.md` - отчет по media library.

`outputs/audio_edits/` - текущая рабочая папка для ручных аудио-операций, которые мы делали через ffmpeg. Это не часть основного pipeline, но уже полезный будущий кандидат на `media_tools`.

`outputs/audio_edits/home_voice_60min/` - артефакты нарезки голоса из фильма: analysis wav, whisper segments, master wav, flac/opus финалы, manifests.

Обычные outputs основного pipeline по новому режиму должны жить так:

```text
outputs/<channel>/<video>/
  quote_plan.json
  scene_plan.json
  asset_plan.json
  render_plan.json
  music_plan.json
  voice_manifest.json
  youtube_metadata.json
  self_eval.json
  render_stage.json
  final_preview.mp4
  final_video.mp4
  thumbnail.png
```

Смысл папки: runtime state и результаты. По-хорошему большую часть outputs надо считать временными или build artifacts.

## 12. Anime Factory

### Назначение

`anime_factory/` - отдельное приложение для YouTube Shorts из локального anime/mp4. Оно:

1. копирует source video в папку эпизода;
2. извлекает audio wav;
3. транскрибирует речь через faster-whisper;
4. анализирует громкость;
5. опционально ищет scene cuts;
6. ищет кандидаты 20-45 секунд;
7. делает preview и HTML report;
8. позволяет вручную выбрать candidates;
9. рендерит вертикальные shorts 1080x1920 с субтитрами и crop режимами.

### Запуск

Preview workflow:

```powershell
python anime_factory/pipeline.py --input anime_factory/input/source.mp4 --episode episode_001 --candidate-count 30 --preview-only --force
```

Финальный render selected:

```powershell
python anime_factory/pipeline.py --input anime_factory/input/source.mp4 --episode episode_001 --render-selected anime_factory/episodes/episode_001/selected.json --crop-mode auto
```

### Текущий этап

Состояние: сильный MVP, ближе к самостоятельному приложению, чем к модулю основного pipeline. Есть CLI, config, тесты, report.html, preview workflow, выбранные candidates, несколько crop modes.

Что доделать:

- сделать нормальный UI для просмотра candidates и выбора `selected.json`;
- добавить job/status database вместо ручных файлов;
- улучшить face detection для аниме или подключить модель, специально обученную на anime faces;
- добавить детектор copyright/risk notes и workflow ручной проверки;
- добавить экспорт metadata для Shorts;
- добавить пакетную обработку нескольких эпизодов;
- отделить `episodes/` artifacts от исходного кода, чтобы репозиторий не засорялся.

## 13. `anime_factory/` по файлам

`anime_factory/__init__.py` - настройка пакета. Добавляет корень проекта в `sys.path`, чтобы imports работали при запуске скрипта.

`anime_factory/README.md` - инструкция по запуску Anime Factory, crop modes, preview workflow, selected.json и флагам.

`anime_factory/requirements.txt` - зависимости Anime Factory: faster-whisper, numpy, soundfile, pyyaml, opencv-python.

`anime_factory/config.yaml` - настройки emotional words, scoring candidates, subtitles, render resolution/bitrate, dynamic crop.

`anime_factory/pipeline.py` - CLI-orchestrator Anime Factory. Управляет extract audio, transcribe, analyze audio, detect scenes, score candidates, preview, render selected и report.

`anime_factory/modules/__init__.py` - маркер подпакета modules.

`anime_factory/modules/paths.py` - dataclass `EpisodePaths`, пути episode, создание папок, очистка output/previews/crops, чтение/запись JSON, загрузка YAML config.

`anime_factory/modules/ffmpeg_utils.py` - проверка ffmpeg/ffprobe, запуск ffmpeg команд, probe video size, экранирование путей для ffmpeg filters.

`anime_factory/modules/extract_audio.py` - копирует source video в episode и извлекает audio wav.

`anime_factory/modules/transcribe.py` - faster-whisper transcription, сохраняет `transcript.json` и `subtitles_raw.srt`.

`anime_factory/modules/analyze_audio.py` - считает аудио-фичи по окнам: громкость/энергия для scoring candidates.

`anime_factory/modules/detect_scenes.py` - ищет резкие смены сцен и пишет `scene_cuts.json`.

`anime_factory/modules/score_candidates.py` - главный scoring engine. Строит окна по transcript, оценивает hook, payoff, emotional words, audio energy, speech density, duration fit, context warning, silence penalty.

`anime_factory/modules/refine_boundaries.py` - уточняет границы candidates по репликам, тишине и scene cuts.

`anime_factory/modules/selection.py` - читает `selected.json` и пишет `selected.example.json`.

`anime_factory/modules/subtitles.py` - создает SRT/ASS субтитры для short, режет строки под 2 строки и max chars.

`anime_factory/modules/detect_faces.py` - sample-based face detection для crop. Есть anime backend heuristics и fallback пустых detections.

`anime_factory/modules/dynamic_crop.py` - строит dynamic crop path по лицам, smart static crop, center crop, blur fallback, рендерит dynamic video через OpenCV и mux audio/subtitles через ffmpeg.

`anime_factory/modules/render_clips.py` - рендерит финальные shorts. Выбирает crop mode: center, blur, smart_static, dynamic, auto. Пишет crop/faces metadata.

`anime_factory/modules/preview.py` - рендерит previews для candidates и crop comparisons.

`anime_factory/modules/report.py` - генерирует `report.html` с candidates, reasons, warnings и ссылками на видео.

`anime_factory/episodes/episode_001/selected.example.json` - пример ручного выбора candidates.

`anime_factory/episodes/episode_001/report.html` - HTML-отчет по текущему episode.

`anime_factory/episodes/episode_001/artifacts/transcript.json` - транскрипт.

`anime_factory/episodes/episode_001/artifacts/subtitles_raw.srt` - сырые субтитры.

`anime_factory/episodes/episode_001/artifacts/audio_features.json` - аудио-фичи.

`anime_factory/episodes/episode_001/artifacts/candidates.json` - найденные candidates.

`anime_factory/episodes/episode_001/previews/*.srt`, `*.ass` - субтитры для preview shorts.

`anime_factory/episodes/episode_001/previews/*.mp4` - вероятно есть локально, но игнорируются Git.

## 14. `scripts/`

`scripts/test_moss_voices.py` - CLI для тестирования MOSS voices. Ищет voice samples в `assets/voice_samples/` и MOSS folder, генерирует несколько тестовых фраз, пишет wav и report в `outputs/tts_tests/moss/`.

Состояние: полезный dev-инструмент, но не часть production pipeline. В будущем можно вынести в `apps/voice_lab/` или `tools/voice_test/`.

## 15. `legacy/`

`legacy/main.py` - старый генератор YouTube package через OpenAI.

`legacy/scene_planner.py` - старый текстовый scene planner.

`legacy/scene_plan_json.py` - старый генератор JSON scene plan.

`legacy/download_broll.py` - старый загрузчик b-roll из Pexels.

`legacy/render_from_scene_plan.py` - старый rough render по scene plan.

`legacy/assemble_broll_video.py` - старая сборка b-roll видео.

`legacy/assemble_broll_with_text.py` - старая сборка b-roll с текстом.

`legacy/add_music.py` - старое добавление музыки.

Состояние: архив истории. Не развивать, кроме случаев, когда нужно достать идею или мигрировать функцию в новый код.

## 16. `docs/`

`docs/project_explanation.md` - старый большой обзор проекта. Полезен исторически, но часть информации устарела и не учитывает Anime Factory.

`docs/cleanup_report.md` - старый отчет по чистке. Полезен как список кандидатов на удаление/архивирование.

`docs/project_map_and_app_split_plan.md` - этот документ. Актуальная карта проекта на 2026-07-18.

## 17. `tests/`

`tests/test_channel_profiles.py` - проверяет загрузку channel profiles и генерацию quote/scene/metadata по каналам.

`tests/test_documentary_visual_engine.py` - проверяет documentary visual engine и качество подбора ассетов.

`tests/test_media_library.py` - проверяет регистрацию, поиск, dedupe и индекс media library.

`tests/test_size_comparison_engine.py` - проверяет size comparison data/camera/render helpers.

`tests/test_moss_tts_provider.py` - проверяет MOSS provider behavior.

`tests/test_moss_voice_tester.py` - проверяет voice sample tester.

`tests/test_anime_factory_paths.py` - проверяет пути и JSON helpers Anime Factory.

`tests/test_anime_factory_cleanup.py` - проверяет безопасную очистку output/previews/crops.

`tests/test_anime_factory_transcribe.py` - проверяет transcription helpers/SRT behavior.

`tests/test_anime_factory_candidates.py` - проверяет scoring candidates.

`tests/test_anime_factory_dynamic_crop.py` - проверяет dynamic crop path.

`tests/test_anime_factory_v3.py` - проверяет поведение новых crop/render функций версии v3.

`tests/test_anime_factory_v4.py` - проверяет smart static crop/report/preview behavior версии v4.

Состояние: тесты уже покрывают важные куски архитектуры, особенно Anime Factory. Для будущего UI надо добавить интеграционные тесты job lifecycle.

## 18. Как приложения связаны

Связи сейчас такие:

```text
pipeline.py
  -> src/*
  -> scripts/test_moss_voices.py
  -> MOSS_TTS_Nano через subprocess
  -> assets/library
  -> channels/content/manual_assets
  -> outputs

anime_factory/pipeline.py
  -> anime_factory/modules/*
  -> faster-whisper
  -> ffmpeg/opencv
  -> anime_factory/episodes/*
```

Общее между приложениями:

- ffmpeg;
- работа с аудио/видео;
- JSON/YAML artifacts;
- локальные outputs;
- будущая потребность в UI и job status.

Разное:

- основной pipeline создает видео по сценарному плану;
- Anime Factory режет готовое видео на shorts;
- audio edits сейчас ручные и не оформлены как приложение.

## 19. Рекомендованное разделение

Первый безопасный шаг без большой ломки:

```text
apps/
  youtube_pipeline/      # CLI wrapper вокруг текущего pipeline.py
  anime_factory/         # перенос текущей anime_factory
  media_tools/           # аудио/видео утилиты ffmpeg
packages/
  ai_youtube_core/       # config, paths, json, job status
  media_engine/          # ffmpeg utils, audio, render helpers
  provider_clients/      # pexels, pixabay, unsplash, elevenlabs
data/
  channels/
  content/
  manual_assets/
runtime/
  outputs/
  cache/
```

Второй шаг:

- `pipeline.py` становится тонким CLI;
- вся логика переезжает в классы/функции сервисов;
- UI вызывает сервисы, а не shell-команды напрямую;
- все job outputs получают единый формат `job.json`.

Третий шаг:

- сделать единый desktop/web UI;
- на первом экране выбрать приложение: YouTube Pipeline, Anime Factory, Media Tools, Voice Lab;
- внутри каждого приложения показать inputs, настройки, queue, progress, logs, artifacts.

## 20. Что доделать перед UI

Общее:

- единый `Job` формат: id, app, status, input, config, started_at, finished_at, artifacts, errors;
- единая папка runtime outputs;
- нормальные machine-readable логи;
- единая политика временных файлов;
- исправить старую кодировку русских строк в документах/конфигах, если она реально повреждена в файлах, а не только в консоли;
- запретить приложению читать/показывать `.env`;
- добавить команду `doctor`, которая проверяет ffmpeg, python deps, keys, writable folders.

Main YouTube Pipeline:

- отделить старый quotes fallback от нового video task режима;
- сделать schema validation для content tasks;
- сделать preview report до рендера;
- улучшить asset review: какие клипы выбраны, почему, license/source;
- добавить ручную замену ассетов до финального рендера;
- улучшить voice workflow и понятный выбор ElevenLabs/MOSS/stub.

Anime Factory:

- UI для просмотра `report.html` внутри приложения;
- кнопки select/reject candidate;
- рендер выбранных candidates без ручного JSON;
- пакетная обработка episodes;
- более надежный anime face detector;
- проверка, что subtitle text не вылезает за экран;
- auto title/description/hashtags для Shorts.

Media Tools:

- оформить наши ручные аудио операции в CLI: compress, trim silence, extract voice segments, split, convert;
- presets: `under10mb_voice`, `voice_only_60min`, `best_quality_flac`, `compatible_mp3`;
- сохранять manifest с командами ffmpeg и параметрами качества.

Voice Lab:

- список voice samples;
- запуск MOSS/ElevenLabs тестов;
- сравнение качества;
- сохранение выбранного голоса в channel/video config.

## 21. Практический вывод

На сегодня проект лучше понимать так:

- `src/` + root `pipeline.py` - основное приложение для генерации YouTube-видео.
- `anime_factory/` - отдельное приложение для Shorts из готового видео.
- `outputs/audio_edits/` - зарождающееся приложение media tools.
- `scripts/test_moss_voices.py` + `MOSS_TTS_Nano/` - отдельная лаборатория голосов.
- `legacy/` - архив старого MVP.

Самая правильная следующая архитектурная задача: не сразу делать UI, а сначала ввести слой `apps + packages + runtime jobs`. Тогда UI станет тонкой оболочкой над уже понятными приложениями, а не еще одним большим файлом поверх хаоса.
