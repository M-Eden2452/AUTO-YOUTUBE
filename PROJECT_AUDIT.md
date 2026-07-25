# Технический аудит проекта AI-YouTube

Дата аудита: 2026-07-22  
Рабочая папка: `G:\Projects\AI-YouTube`

## 0. Краткое вводное резюме

### 0.1. Как я понял назначение приложения

Проект предназначен для автоматизации производства YouTube-видео, в первую очередь YouTube Shorts: пользователь задает тему, URL новости или готовый текст, после чего система должна подготовить сценарий, разбить его на сцены, найти и скачать визуальные материалы, создать озвучку, субтитры, музыку, собрать финальное видео и сохранить исходники/метаданные.

В репозитории фактически существуют несколько параллельных направлений:

1. **News-to-short pipeline** - основной новый пайплайн для коротких новостных роликов.
2. **Старый YouTube/documentary pipeline** - корневой `pipeline.py` с планированием сцен, поиском ассетов, озвучкой и рендером.
3. **Production plan solar_vs_nuclear** - полуфиксированный production workflow для конкретного проекта `project_solar_vs_nuclear`.
4. **Anime Factory** - отдельный инструмент для нарезки Shorts из локального anime-видео.
5. **Legacy-скрипты** - старые прототипы, частично не подключенные к текущему пайплайну.

### 0.2. Какие части проекта изучены

Проверены:

- структура корня проекта;
- `pipeline.py`;
- `apps/*`;
- `src/news/*`;
- `src/assets/semantic_selection/*`;
- `src/providers/*`;
- `src/media_library.py`;
- `src/video_asset_engine.py`;
- `src/asset_finder.py`;
- `src/voice_engine.py`;
- `src/audio/*`;
- `src/music_engine.py`;
- `src/music_finder.py`;
- `src/video_renderer.py`;
- `src/layout_renderer.py`;
- `src/production_plan/*`;
- `anime_factory/*`;
- `legacy/*`;
- `config/video_style.json`;
- `channels/nature_science_news_ru/*`;
- `.env`, `.env.example` - только имена переменных, без раскрытия значений;
- `requirements.txt`;
- основные тесты в `tests/*`;
- текущие папки `projects/*` и `project_solar_vs_nuclear/*` на уровне структуры и манифестов.

### 0.3. Удалось ли полностью проследить pipeline от входа до готового видео

Да, удалось проследить несколько реальных последовательностей:

- news-to-short CLI: от входа `--news-to-short` до стадий проекта;
- old/documentary pipeline: от конфигурации и сцен до рендера;
- production plan: от фиксированного плана `solar_vs_nuclear` до готового видео;
- anime_factory: от локального видео до набора Shorts.

Но важно: **универсальный news-to-short pipeline сейчас не является полностью автоматическим end-to-end процессом**, потому что:

- стадия `asset_search` в `src/news/pipeline.py` ищет кандидатов, но не скачивает provider-assets;
- стадия `voice` создает безопасный манифест, но не делает платный TTS автоматически;
- `preview_render` создает preview только из уже готового финального видео;
- `final_render` требует локальные пути к ассетам и завершенную озвучку.

Готовые финальные ролики в некоторых проектах есть, но они появились через дополнительные/отдельные механизмы, например через `src/news/stock_video_downloader.py` или production-plan renderer, а не через полностью связанный новый pipeline.

### 0.4. Какие части проекта остались непонятными или не проверялись до конца

Не выполнялись:

- реальные API-запросы к Pexels, Pixabay, Unsplash, ElevenLabs;
- реальные рендеры FFmpeg/MoviePy;
- запуск тестов;
- глубокий аудит внешней папки `MOSS_TTS_Nano`;
- воспроизведение готовых видео вручную;
- проверка UI в браузере, потому что полноценного UI/сервера для основного пайплайна не найдено.

Причина: пользователь явно попросил безопасный аудит без изменения состояния, установки зависимостей, рендера, удаления или перемещения файлов.

---

## 1. Общая архитектура проекта

### 1.1. Основные папки

Фактическая структура корня:

```text
G:\Projects\AI-YouTube
  .git/
  __pycache__/
  anime_factory/
  apps/
  assets/
  channels/
  config/
  content/
  docs/
  legacy/
  manual_assets/
  MOSS_TTS_Nano/
  music/
  outputs/
  packages/
  project_solar_vs_nuclear/
  projects/
  scripts/
  src/
  subtitles/
  tests/
  venv/
  .env
  .env.example
  .gitignore
  pipeline.py
  README.md
  requirements.txt
```

Назначение основных папок:

| Папка | Назначение |
| --- | --- |
| `src/` | Основной Python-код старого пайплайна, news pipeline, аудио, провайдеры, media library, production plan |
| `apps/` | Тонкие entrypoint-обертки для разных режимов приложения |
| `channels/` | Конфигурации каналов, включая `nature_science_news_ru` |
| `config/` | Общий стиль и настройки старого pipeline |
| `content/` | Контентные JSON-файлы для старого pipeline |
| `projects/` | Сгенерированные news-to-short проекты |
| `project_solar_vs_nuclear/` | Отдельный production-проект по теме solar vs nuclear |
| `assets/` | Локальная библиотека ассетов, кеш, метаданные |
| `manual_assets/` | Ручные ассеты для старого/documentary pipeline |
| `outputs/` | Выходы старого pipeline и временные рендеры |
| `anime_factory/` | Отдельный pipeline для нарезки локального видео |
| `legacy/` | Старые прототипы и скрипты |
| `tests/` | Unit/integration-like тесты |
| `MOSS_TTS_Nano/` | Внешний локальный TTS-проект |

### 1.2. Основные entrypoints

#### Корневой CLI

Файл:

- `G:\Projects\AI-YouTube\pipeline.py`

Функция:

- `main()`

Это главный entrypoint. Он разбирает аргументы и переключает режимы:

- обычный старый pipeline;
- `--news-to-short`;
- `--voice-action`;
- `--production-plan`;
- `--render-production-plan`;
- утилиты media library;
- MOSS TTS diagnostics;
- comparison/diagnostic modes.

#### News wrapper

Файлы:

- `G:\Projects\AI-YouTube\apps\news_to_short\main.py`
- `G:\Projects\AI-YouTube\apps\news_to_short\__main__.py`

`apps/news_to_short/main.py` вызывает:

- `src.news.pipeline.run_news_to_short_cli`

#### YouTube pipeline wrapper

Файл:

- `G:\Projects\AI-YouTube\apps\youtube_pipeline\main.py`

Он импортирует корневой:

- `pipeline.main`

#### Anime Factory wrapper

Файл:

- `G:\Projects\AI-YouTube\apps\anime_factory\main.py`

Он вызывает:

- `anime_factory.pipeline.main`

### 1.3. Как запускается приложение

По коду приложение запускается как CLI. Примеры возможных режимов:

```powershell
python pipeline.py --news-to-short --topic "..." --language ru
python pipeline.py --news-to-short --url "https://..." --language ru
python pipeline.py --voice-action preflight --job-id ...
python pipeline.py --production-plan solar_vs_nuclear
python pipeline.py --render-production-plan solar_vs_nuclear
python apps/news_to_short/main.py --topic "..."
python -m apps.news_to_short --topic "..."
python apps/anime_factory/main.py --input ...
```

Полноценный локальный сервер/API в проекте не найден. UI как веб-приложение тоже не найден.

### 1.4. Основные компоненты по ответственности

| Компонент | Файлы |
| --- | --- |
| Главный CLI | `pipeline.py` |
| News project state | `src/news/models.py`, `src/news/project_store.py` |
| News article ingestion | `src/news/article_ingestor.py`, `src/news/article_parser.py` |
| News research | `src/news/research_engine.py` |
| News script | `src/news/script_generator.py` |
| News visual plan | `src/news/visual_plan.py` |
| News asset selection | `src/news/asset_manager.py`, `src/assets/semantic_selection/*` |
| News stock downloader | `src/news/stock_video_downloader.py` |
| News voice safe stage | `src/news/voice_stage.py` |
| Voice workflow/CLI | `src/audio/voice_cli.py`, `src/audio/voice_workflow.py` |
| ElevenLabs TTS | `src/audio/tts/elevenlabs_provider.py`, `src/voice_engine.py` |
| Manual WAV import | `src/audio/tts/audio_file_provider.py`, `src/audio/voice_workflow.py` |
| News subtitles | `src/news/subtitles.py` |
| News quality gate | `src/news/quality_check.py` |
| News final render | `src/news/final_renderer.py` |
| Old scene planner | `src/scene_planner.py` |
| Old asset finder | `src/asset_finder.py`, `src/video_asset_engine.py` |
| Old music | `src/music_engine.py`, `src/music_finder.py` |
| Old render | `src/video_renderer.py`, `src/layout_renderer.py` |
| Stock APIs | `src/providers/pexels_provider.py`, `src/providers/pixabay_provider.py`, `src/providers/unsplash_provider.py` |
| Local media library | `src/media_library.py` |
| Production plan | `src/production_plan/youtube_shorts.py`, `src/production_plan/solar_vs_nuclear_render.py` |
| Anime Shorts | `anime_factory/pipeline.py` and related modules |

### 1.5. Связь модулей между собой

Главная развилка находится в `pipeline.py`:

```text
pipeline.py
  if --voice-action:
    src.audio.voice_cli.run_voice_cli
  elif --production-plan:
    src.production_plan.youtube_shorts.create_solar_vs_nuclear_plan
  elif --render-production-plan:
    src.production_plan.solar_vs_nuclear_render.build_solar_vs_nuclear_video
  elif --news-to-short:
    src.news.pipeline.run_news_to_short_cli
  else:
    old documentary/youtube pipeline
```

Внутри `src/news/pipeline.py` стадии идут по списку из `src/news/models.py`:

```python
NEWS_TO_SHORT_STAGES = [
    "input",
    "article_ingestion",
    "research",
    "script",
    "visual_plan",
    "asset_search",
    "voice",
    "subtitles",
    "preview_render",
    "quality_check",
    "final_render",
    "export",
]
```

### 1.6. Что выглядит временным или тестовым

Факты из кода:

- `legacy/*` - старые прототипы, включая `legacy/download_broll.py`.
- `src/news/voice_stage.py` - безопасная заглушка для TTS: создает манифест, но не делает платный синтез.
- `src/news/preview_renderer.py` - preview строится только из уже готового final video.
- `src/news/stock_video_downloader.py` - полезный downloader, но он не подключен в `src/news/pipeline.py`.
- `src/production_plan/*` - production workflow для конкретного кейса `solar_vs_nuclear`, не универсальный движок.
- `anime_factory/*` - отдельный инструмент, не интегрированный с news/documentary pipeline.
- `project_solar_vs_nuclear/preview.html` - статический HTML-превью, а не полноценный UI.
- Старый pipeline содержит режимы и тексты, завязанные на конкретные старые сценарии, например hardcoded fallback для Jordan Peterson в `src/layout_renderer.py`.

---

## 2. Текущий процесс создания видео

В проекте есть не один, а несколько pipeline. Ниже - реальные последовательности.

### 2.1. News-to-short pipeline

Entry:

- `G:\Projects\AI-YouTube\pipeline.py`
- `G:\Projects\AI-YouTube\src\news\pipeline.py`

CLI-ветка:

```text
pipeline.py::main()
  -> if args.news_to_short
  -> src.news.pipeline.run_news_to_short_cli(args)
```

#### 2.1.1. Вход

`src/news/pipeline.py::create_news_to_short_job()` принимает:

- `--url`;
- `--urls`;
- `--topic`;
- `--text`;
- `--text-file`;
- `--assets`;
- `--language`;
- `--target-duration`;
- `--news-channel`;
- `--projects-root`.

Input mode определяется так:

```text
url/text/topic
```

Если передан `--url`, режим `url`; если `--text` или `--text-file`, режим `text`; иначе `topic`.

#### 2.1.2. Где создается проект

Файл:

- `G:\Projects\AI-YouTube\src\news\project_store.py`

Класс:

- `NewsProjectStore`

Метод:

- `create_project()`

Фактически проект создается в:

```text
projects/<job_id>/
```

`job_id` формируется в `NewsJob.create()` из slug входа и timestamp.

#### 2.1.3. Как хранится состояние проекта

Главный state:

```text
projects/<job_id>/job.json
```

Модель:

- `src/news/models.py::NewsJob`
- `src/news/models.py::StageState`
- `src/news/models.py::LocalizationState`
- `src/news/models.py::AssetRights`

Каждая стадия имеет:

- `name`;
- `status`;
- `started_at`;
- `completed_at`;
- `attempts`;
- `inputs`;
- `outputs`;
- `error`;
- `warnings`.

#### 2.1.4. Реальная структура проекта news-to-short

Создается в `NewsProjectStore.create_project()`:

```text
projects/<job_id>/
  job.json
  input/
    input.json
  article/
  research/
  assets/
  master/
    sources.json
  logs/
  localizations/
    ru/
      script/
      voice/
        previews/
      subtitles/
      visual/
      output/
    en/
      script/
      voice/
        previews/
      subtitles/
      visual/
      output/
    es/
      script/
      voice/
        previews/
      subtitles/
      visual/
      output/
```

Даже если выбран только русский язык, папки для `ru`, `en`, `es` создаются.

#### 2.1.5. Последовательность стадий

Файл:

- `G:\Projects\AI-YouTube\src\news\pipeline.py`

Функция:

- `run_news_to_short_job()`

Стадии:

1. `input`
2. `article_ingestion`
3. `research`
4. `script`
5. `visual_plan`
6. `asset_search`
7. `voice`
8. `subtitles`
9. `preview_render`
10. `quality_check`
11. `final_render`
12. `export`

Диспетчер:

- `src/news/pipeline.py::_dispatch_stage()`

#### 2.1.6. Что делает каждая стадия

| Стадия | Файл/функция | Реальное поведение |
| --- | --- | --- |
| `input` | `src/news/pipeline.py::_dispatch_stage` | Возвращает путь к `input/input.json` |
| `article_ingestion` | `src/news/article_ingestor.py::ingest_article` | Для URL скачивает HTML через `requests.get(timeout=20)`, парсит статью и картинки; для text/topic делает article object |
| `research` | `src/news/research_engine.py::build_research` | Делит текст на утверждения, классифицирует простыми эвристиками |
| `script` | `src/news/script_generator.py::build_script` | Создает детерминированный сценарий из 6 сцен |
| `visual_plan` | `src/news/visual_plan.py::build_visual_plan` | Создает visual plan с primary/alternative queries |
| `asset_search` | `src/news/asset_manager.py::build_news_asset_manifest` | Ищет и ранжирует ассеты, но в основной ветке не скачивает provider-файлы |
| `voice` | `src/news/voice_stage.py::build_safe_voice_manifest` | Создает манифест и требует ручного выбора/approval; платный TTS не вызывается |
| `subtitles` | `src/news/subtitles.py::build_subtitles` | Создает `.srt` и `.ass` из сценария |
| `preview_render` | `src/news/preview_renderer.py::render_preview` | Создает preview только если уже есть финальное видео |
| `quality_check` | `src/news/quality_check.py::run_quality_check` | Проверяет длительность, права, ассеты, voice, subtitles |
| `final_render` | `src/news/final_renderer.py::render_final_video` | Делает FFmpeg-монтаж, требует локальные `path` у ассетов |
| `export` | `src/news/exporter.py::export_localization` | Пишет description, sources, project manifest |

#### 2.1.7. Сценарий

Файл:

- `G:\Projects\AI-YouTube\src\news\script_generator.py`

Функция:

- `build_script()`

Реально сценарий создается без LLM. Это шаблонный/эвристический генератор. Он берет claims из `research/claims.json`, собирает narration и создает примерно 6 сцен.

Пример структуры сцены из кода:

```json
{
  "scene_id": "scene_001",
  "start_sec": 0.0,
  "target_duration_sec": 3.5,
  "narration": "...",
  "claim_ids": ["claim_001"],
  "visual_intent": "...",
  "on_screen_text": "...",
  "emotion": "curiosity"
}
```

#### 2.1.8. Деление на сцены

Деление находится в том же `build_script()`. Сцены не вычисляются по длительности озвучки, а создаются заранее с фиксированными целевыми длительностями:

```text
3.5, 7.0, 10.0, 13.0, 10.0, 8.0
```

#### 2.1.9. Формирование запросов

Файл:

- `G:\Projects\AI-YouTube\src\news\visual_plan.py`

Функции:

- `make_stock_query()`
- `build_visual_plan()`

Логика детерминированная:

- если текст содержит whale/кит - запросы про whales/ocean;
- если science/research - запросы про scientists/research;
- если ocean/sea - ocean wildlife;
- иначе generic nature/science.

Пример структуры visual item:

```json
{
  "scene_id": "scene_001",
  "visual_type": "video",
  "primary_query": "humpback whale ocean surface slow motion",
  "alternative_queries": [
    "whale ocean wildlife",
    "marine animal underwater"
  ],
  "negative_keywords": ["cartoon", "text overlay", "logo"],
  "preferred_asset_ids": [],
  "allow_user_asset": true,
  "allow_stock": true,
  "allow_article_asset": false,
  "fallback_type": "animated_image",
  "camera_effect": "slow_push_in",
  "transition": "cut"
}
```

#### 2.1.10. Поиск исходников

Файл:

- `G:\Projects\AI-YouTube\src\news\asset_manager.py`

Функции:

- `build_news_asset_manifest()`
- `build_assets_manifest()`
- `create_default_asset_providers()`

Источники:

- user assets;
- local media library;
- Pexels;
- Pixabay;
- Unsplash.

Критический факт: в этой ветке provider results **не скачиваются**. Они становятся кандидатами с metadata, но без локального `path`.

#### 2.1.11. Выбор материалов

Файлы:

- `G:\Projects\AI-YouTube\src\assets\semantic_selection\scene_analyzer.py`
- `G:\Projects\AI-YouTube\src\assets\semantic_selection\query_generator.py`
- `G:\Projects\AI-YouTube\src\assets\semantic_selection\candidate_ranker.py`
- `G:\Projects\AI-YouTube\src\assets\semantic_selection\continuity_checker.py`

Основная функция выбора:

- `src.assets.semantic_selection.candidate_ranker.select_best_candidate()`

Ранжирование metadata-only. Анализ превью/кадров отсутствует.

#### 2.1.12. Скачивание файлов

В основном news pipeline скачивание provider-assets не подключено.

Есть отдельный файл:

- `G:\Projects\AI-YouTube\src\news\stock_video_downloader.py`

Функция:

- `download_stock_videos_for_project()`

Она умеет скачать видео из Pexels/Pixabay в:

```text
projects/<job_id>/assets/stock_videos/
```

Но поиск по коду показывает, что `src/news/pipeline.py` не вызывает этот downloader в стандартной стадии `asset_search`.

#### 2.1.13. Озвучка

Основной news stage:

- `G:\Projects\AI-YouTube\src\news\voice_stage.py::build_safe_voice_manifest`

Он не синтезирует речь. Он пишет:

```text
localizations/<lang>/voice/voice_selection.json
localizations/<lang>/voice/voice_manifest.json
```

Платный ElevenLabs вызывается только через отдельный voice CLI:

- `G:\Projects\AI-YouTube\src\audio\voice_cli.py`
- `G:\Projects\AI-YouTube\src\audio\tts\elevenlabs_provider.py`

или через старый:

- `G:\Projects\AI-YouTube\src\voice_engine.py`

или через production-plan renderer:

- `G:\Projects\AI-YouTube\src\production_plan\solar_vs_nuclear_render.py`

#### 2.1.14. Субтитры

Файл:

- `G:\Projects\AI-YouTube\src\news\subtitles.py`

Функция:

- `build_subtitles()`

Выходы:

```text
localizations/<lang>/subtitles/subtitles.srt
localizations/<lang>/subtitles/subtitles.ass
localizations/<lang>/subtitles/subtitles_manifest.json
```

Сегменты строятся из сцен, без forced alignment по реальному аудио.

#### 2.1.15. Монтаж

Файл:

- `G:\Projects\AI-YouTube\src\news\final_renderer.py`

Функция:

- `render_final_video()`

Шаги:

1. Создает scene segments в `localizations/<lang>/output/render/segments`.
2. Масштабирует и кропает видео/изображения до 1080x1920.
3. Склеивает сегменты через FFmpeg concat.
4. Микширует voice и опционально music.
5. Прожигает `.ass` субтитры.
6. Пишет platform copies.

Выходы:

```text
localizations/<lang>/output/master_1080x1920.mp4
localizations/<lang>/output/youtube_shorts.mp4
localizations/<lang>/output/instagram_reels.mp4
localizations/<lang>/output/facebook_reels.mp4
localizations/<lang>/output/no_subtitles.mp4
localizations/<lang>/output/final_render_manifest.json
```

### 2.2. Старый YouTube/documentary pipeline

Entry:

- `G:\Projects\AI-YouTube\pipeline.py`

Последовательность:

```text
load_config()
  -> load_channel_video_config()
  -> build_quote_plan()
  -> write_youtube_metadata()
  -> build_scene_plan()
  -> build_voice_manifest()
  -> apply_voice_timing_to_scene_plan()
  -> align_voice_manifest_to_scene_plan()
  -> build_intro_plan()
  -> build_music_plan()
  -> build_asset_plan()
  -> build_render_plan()
  -> render_video()
  -> evaluate_render()
  -> export_obsidian_note()
```

Ключевые файлы:

- `src/config_loader.py`
- `src/channel_loader.py`
- `src/quote_generator.py`
- `src/scene_planner.py`
- `src/voice_engine.py`
- `src/music_engine.py`
- `src/asset_finder.py`
- `src/video_asset_engine.py`
- `src/video_renderer.py`
- `src/self_eval.py`

Особенности:

- это более связанный end-to-end pipeline, чем news-to-short;
- он умеет скачивать видео через `src/video_asset_engine.py`;
- он работает в основном для channel/video конфигов;
- структура выходов в `outputs/<channel>/<video>/`;
- часть логики выглядит исторической и специфичной для documentary/survival/Jordan Peterson.

### 2.3. Production plan `solar_vs_nuclear`

Entry:

- `pipeline.py --production-plan solar_vs_nuclear`
- `pipeline.py --render-production-plan solar_vs_nuclear`

Файлы:

- `src/production_plan/youtube_shorts.py`
- `src/production_plan/solar_vs_nuclear_render.py`

Проект:

- `G:\Projects\AI-YouTube\project_solar_vs_nuclear`

Структура:

```text
project_solar_vs_nuclear/
  01_script/
  02_voice/
  03_stock/
  04_motion/
  05_project/
    capcut/
    exports/
  06_analytics/
```

Этот workflow ближе всего к готовому production-кейсу: в текущей папке есть `render_manifest.json`, `selected_sources.json`, готовые выходы. Но он hardcoded под один сценарий.

### 2.4. Anime Factory

Файлы:

- `anime_factory/pipeline.py`
- `anime_factory/config.yaml`

Назначение:

- брать локальный episode video;
- извлекать audio;
- транскрибировать или использовать готовую transcript;
- находить эмоциональные candidates;
- делать vertical clips.

Это отдельный локальный shorts-cutter, не pipeline для stock/news automation.

---

## 3. Поиск визуальных материалов

### 3.1. Общая картина

В проекте есть несколько параллельных реализаций поиска:

| Слой | Файлы | Особенность |
| --- | --- | --- |
| Provider functions | `src/providers/pexels_provider.py`, `pixabay_provider.py`, `unsplash_provider.py` | Низкоуровневые official API wrappers |
| News provider classes | `src/news/asset_manager.py` | Классы `PexelsAssetProvider`, `PixabayAssetProvider`, `UnsplashAssetProvider` |
| News standalone downloader | `src/news/stock_video_downloader.py` | Скачивает видео, но не подключен к основной стадии |
| Old documentary engine | `src/video_asset_engine.py` | Самостоятельный поиск, скачивание, кеш, local library |
| Old image finder | `src/asset_finder.py` | Pexels/Pixabay images для не-documentary режима |
| Production plan renderer | `src/production_plan/solar_vs_nuclear_render.py` | Собственная логика поиска/скачивания Pexels/Pixabay |
| Legacy downloader | `legacy/download_broll.py` | Старый Pexels-only скрипт |

Нет единого provider abstraction для всех этих слоев.

### 3.2. Pexels

#### 3.2.1. Низкоуровневый provider

Файл:

- `G:\Projects\AI-YouTube\src\providers\pexels_provider.py`

Функции:

- `search_videos(api_key: str, query: str, per_page: int = 10)`
- `search_images(api_key: str, query: str, per_page: int = 10)`

Используется официальный API:

- `https://api.pexels.com/videos/search`
- `https://api.pexels.com/v1/search`

Параметры video search:

```python
params = {
    "query": query,
    "orientation": "landscape",
    "per_page": per_page,
}
```

Параметры image search:

```python
params = {
    "query": query,
    "orientation": "landscape",
    "per_page": per_page,
}
```

Таймаут:

- `REQUEST_TIMEOUT = 24`

Retry:

- нет.

Обработка ошибок:

- `response.raise_for_status()`;
- вызывающий код либо ловит исключения, либо падает.

#### 3.2.2. Pexels в news asset manager

Файл:

- `G:\Projects\AI-YouTube\src\news\asset_manager.py`

Класс:

- `PexelsAssetProvider`

Метод:

- `search(self, query, scene, limit=5)`

Если `scene.visual_type` image/animated_image:

- вызывает `search_images(..., per_page=limit)`.

Иначе:

- вызывает `search_videos(..., per_page=limit)`.

Запрашивается:

- по умолчанию 5 результатов на query в news manager.

Сохраняемые поля candidate:

- `id`;
- `provider`;
- `type`;
- `source_url`;
- `author`;
- `license`;
- `width`;
- `height`;
- `duration`;
- `relevance_score`.

Критический недостаток:

- в этой ветке не сохраняется `download_url`/`direct_download_url`;
- не скачивается файл;
- не создается `path`;
- финальный renderer потом не сможет использовать такой asset напрямую.

#### 3.2.3. Pexels в standalone news downloader

Файл:

- `G:\Projects\AI-YouTube\src\news\stock_video_downloader.py`

Функции:

- `_pexels_candidates()`
- `_best_pexels_file()`
- `_download_file()`
- `download_stock_videos_for_project()`

Используется официальный API через `src.providers.pexels_provider.search_videos`.

Параметры:

- `per_page=6`;
- orientation уже зашит в provider как `landscape`.

Выбор файла:

- ищет `video_files`;
- выбирает video file с достаточной шириной/высотой;
- сортирует по orientation rank и разрешению;
- vertical получает больший ранг, но API сам запрашивает landscape, что противоречит Shorts-задаче.

Фильтры:

- `width >= 1280`;
- `height >= 720`;
- direct URL обязателен;
- размер скачанного файла должен быть больше 100 KB.

Скачивание:

- `requests.get(url, stream=True, timeout=30)`;
- пишет в `assets/stock_videos`;
- при ошибке удаляет target file.

Retry:

- нет.

Fallback:

- перебирает Pexels и Pixabay candidates;
- если нет valid asset, scene попадает в `missing_assets`.

Метаданные:

- provider;
- source_id;
- source_page;
- direct_download_url;
- author;
- license;
- width/height/duration;
- orientation;
- path/downloaded_path;
- scene_id;
- search_query;
- rights_status.

#### 3.2.4. Pexels в old documentary engine

Файл:

- `G:\Projects\AI-YouTube\src\video_asset_engine.py`

Функции:

- `_search_pexels_videos()`
- `_best_pexels_file()`
- `_passes_video_filter()`
- `_select_and_cache_clips()`

Используется официальный Pexels API напрямую через `requests.get`.

Параметры:

- `orientation=landscape`;
- `per_page=10`;
- timeout `24`.

Фильтры:

- ширина >= 960;
- высота >= 540;
- width <= 2560;
- aspect ratio от 1.45 до 2.35;
- duration >= 2.5;
- предпочтение landscape HD.

Скачивание:

- скачивает выбранные clips в local media library/cache;
- проверяет файл через FFmpeg;
- создает thumbnail;
- регистрирует asset в `assets/library/metadata/media_index.json`.

Повторения:

- `avoid_duplicate_downloads()` проверяет `source_url`, `download_url`, `local_path`.

Retry:

- нет.

#### 3.2.5. Pexels в production plan

Файл:

- `G:\Projects\AI-YouTube\src\production_plan\solar_vs_nuclear_render.py`

Функции:

- `_search_candidates()`
- `_pexels_candidate()`
- `_download_video()`

Параметры:

- `per_page=8`;
- provider wrapper `search_videos()`, где orientation landscape.

Выбор:

- scoring по positive/negative keywords, quality, vertical orientation, duration;
- без анализа кадров;
- metadata-only.

Ошибки:

- исключения provider search ловятся и игнорируются через `pass`, без записи диагностики.

### 3.3. Pixabay

#### 3.3.1. Низкоуровневый provider

Файл:

- `G:\Projects\AI-YouTube\src\providers\pixabay_provider.py`

Функции:

- `search_videos(api_key: str, query: str, per_page: int = 10)`
- `search_images(api_key: str, query: str, per_page: int = 10)`
- `search_music(api_key: str, query: str, per_page: int = 10)`

Используется официальный API:

- `https://pixabay.com/api/videos/`
- `https://pixabay.com/api/`
- `https://pixabay.com/api/audio/`

Video params:

```python
{
    "key": api_key,
    "q": query,
    "video_type": "film",
    "safesearch": "true",
    "per_page": per_page,
}
```

Image params:

```python
{
    "key": api_key,
    "q": query,
    "image_type": "photo",
    "orientation": "horizontal",
    "safesearch": "true",
    "per_page": per_page,
}
```

Retry:

- нет.

Timeout:

- `REQUEST_TIMEOUT = 24`.

#### 3.3.2. Pixabay в news asset manager

Файл:

- `G:\Projects\AI-YouTube\src\news\asset_manager.py`

Класс:

- `PixabayAssetProvider`

Метод:

- `search(self, query, scene, limit=5)`

Для image:

- `search_images(..., per_page=limit)`;
- сохраняет `source_url`, `author`, `license`, width/height.

Для video:

- `search_videos(..., per_page=limit)`;
- сохраняет `source_url`, `author`, `license`, width/height/duration.

Недостаток:

- не сохраняется direct video download URL в основной news asset manager;
- не скачивается файл;
- не анализируются tags, хотя Pixabay API возвращает tags.

#### 3.3.3. Pixabay в standalone news downloader

Файл:

- `G:\Projects\AI-YouTube\src\news\stock_video_downloader.py`

Функции:

- `_pixabay_candidates()`
- `_best_pixabay_file()`

Параметры:

- `per_page=6`.

Выбор:

- берет `videos.large`, `videos.medium`, `videos.small`;
- требует direct URL;
- фильтрует width/height;
- сортирует по orientation rank и разрешению.

#### 3.3.4. Pixabay в old documentary engine

Файл:

- `G:\Projects\AI-YouTube\src\video_asset_engine.py`

Функция:

- `_search_pixabay_videos()`

Параметры:

- `video_type=film`;
- `safesearch=true`;
- `per_page=10`.

Скачивание/кеш:

- выполняется через `_select_and_cache_clips()`.

#### 3.3.5. Pixabay music

Файл:

- `G:\Projects\AI-YouTube\src\music_engine.py`

Функция:

- `build_music_plan_v2()`

Использует:

- `src.providers.pixabay_provider.search_music`

Скачивает музыку в local media library, если включен auto download и есть API key.

### 3.4. Unsplash

Файл:

- `G:\Projects\AI-YouTube\src\providers\unsplash_provider.py`

News adapter:

- `src/news/asset_manager.py::UnsplashAssetProvider`

Только images. Видео не поддерживаются.

Поля:

- source URL;
- author;
- license;
- download_location/download URL;
- width/height.

В `create_default_asset_providers()` подключается только если есть `UNSPLASH_ACCESS_KEY`.

### 3.5. Используется ли scraping, browser automation или ручной импорт

Факты:

- Pexels/Pixabay/Unsplash используют official API wrappers.
- Scraping для stock-поиска не найден.
- Browser automation для Envato не реализована.
- Ручной импорт есть частично:
  - `src/audio/voice_workflow.py::import_manual_audio` для WAV;
  - `manual_assets/<channel>/<video>/video` для старого documentary pipeline;
  - `src/production_plan/youtube_shorts.py::replace_selected_clip` для production plan;
  - user assets в news pipeline через `--assets`.

### 3.6. Анализируются ли заголовки, теги, описания, превью или видео

Факты:

- Анализируются только metadata поля, если они есть в candidate:
  - title;
  - description;
  - source_url/source_page;
  - query/search_query;
  - keywords/tags, если candidate их содержит.
- Pexels/Pixabay news adapters почти не передают tags/title/description.
- Визуальный анализ превью/кадров отсутствует.
- `src/assets/semantic_selection/vision_validator.py` явно ограничен precomputed `vision_tags`.
- Реального LLM/vision API для выбора visual не найдено.
- Анализа нескольких кадров видео не найдено.

### 3.7. Preview или оригинал

По текущему коду:

- `src/news/asset_manager.py` вообще не скачивает.
- `src/news/stock_video_downloader.py` скачивает сразу выбранный video file.
- `src/video_asset_engine.py` скачивает video file и потом делает thumbnail.
- `src/production_plan/solar_vs_nuclear_render.py` скачивает выбранный video file.
- отдельного скачивания preview перед original не найдено.

### 3.8. Повторные попытки и fallback

Retry:

- системных retry/backoff для API почти нет.
- ElevenLabs тоже без retry.
- Download functions в нескольких местах делают одну попытку.

Fallback:

- Pexels -> Pixabay fallback есть в old engine и production plan.
- News asset manager собирает candidates от нескольких providers.
- News standalone downloader перебирает candidates и providers.
- Но ошибки часто либо попадают в `provider_errors`, либо silently ignored, в зависимости от слоя.

### 3.9. Как предотвращаются повторения

Реализовано частично:

- `src/news/asset_manager.py` ведет `used_asset_ids` в рамках одного manifest.
- `src/news/stock_video_downloader.py` ведет `used_source_ids`.
- `src/video_asset_engine.py` использует `avoid_duplicate_downloads()` и `mark_asset_used_in_video()`.
- `src/media_library.py` хранит `used_in`.

Ограничения:

- нет глобальной политики "не использовать похожие кадры";
- нет perceptual hash;
- нет сравнения превью/кадров;
- нет проверки похожих материалов между соседними сценами кроме простого continuity checker по словам.

### 3.10. Ориентация и разрешение

Факты:

- Pexels wrapper запрашивает `orientation=landscape`.
- Pixabay image wrapper запрашивает `orientation=horizontal`.
- Pixabay video wrapper не задает vertical orientation.
- Для Shorts final renderer всегда делает center crop в 1080x1920.
- Semantic ranker имеет `vertical_score`, но upstream Pexels/Pixabay часто ищут landscape/horizontal.
- Old documentary engine явно ориентирован на landscape 16:9.

Проверка разрешения:

- old documentary engine проверяет width/height/aspect/duration;
- news standalone downloader проверяет minimum 1280x720;
- production plan учитывает quality score;
- news asset_manager metadata-only проверяет quality score, но файл не скачивает.

### 3.11. Сохраняются ли URL, ID и metadata

Частично.

В разных местах:

- news standalone downloader сохраняет достаточно много metadata;
- production plan сохраняет `selected_sources.json`;
- media library сохраняет source/download URL, но теряет автора и формальные license fields;
- основной news asset manager сохраняет provider/id/source_url/license/author, но не direct download/path.

Нет единой схемы provenance для всего приложения.

---

## 4. Логика соответствия сцене

### 4.1. Где находится semantic selection

Папка:

- `G:\Projects\AI-YouTube\src\assets\semantic_selection`

Файлы:

- `models.py`
- `scene_analyzer.py`
- `query_generator.py`
- `candidate_ranker.py`
- `continuity_checker.py`
- `vision_validator.py`

### 4.2. Структура SemanticScene

Файл:

- `src/assets/semantic_selection/models.py`

Класс:

- `SemanticScene`

Поля:

```python
subject: str
secondary_subjects: list[str]
action: str
environment: str
location: str
camera: str
mood: str
must_include: list[str]
should_include: list[str]
must_not_include: list[str]
visual_priority: str
fallback_level: str
```

Fallback levels:

- `exact_subject`;
- `exact_action`;
- `environment`;
- `research_context`;
- `abstract_explanation`;
- `transition`.

### 4.3. Выделяется ли главный объект

Да, частично.

Файл:

- `src/assets/semantic_selection/scene_analyzer.py`

Функция:

- `analyze_scene()`

Она эвристически ищет ключевые слова:

- whale/кит;
- ocean/sea;
- researcher/scientist;
- forest/tree;
- nuclear/solar и т.д. в production plan через дополнительные scene fields.

Ограничение: логика сильно заточена под whale/ocean и несколько общих категорий.

### 4.4. Выделяется ли действие

Да, частично.

`scene_analyzer.py` ищет слова:

- swim;
- surface;
- dive;
- sing;
- лежит;
- поет;
- etc.

Но это словарные эвристики, не полноценный parser.

### 4.5. Выделяется ли место/окружение

Да, частично:

- `environment`;
- `location`;
- `mood`.

Для ocean/whale работает лучше, чем для произвольных тем.

### 4.6. Учитывается ли тип кадра

Частично:

- поле `camera` в `SemanticScene`;
- `camera_terms` в `candidate_ranker.py`;
- `camera_effect` в `src/news/visual_plan.py`;
- old renderer поддерживает motion/crop/zoom-like эффекты.

Но реального анализа shot type по кадрам нет.

### 4.7. Must-have и negative keywords

Да, есть.

Источники:

- `src/news/visual_plan.py` добавляет `negative_keywords`;
- `src/assets/semantic_selection/scene_analyzer.py` формирует `must_include`/`must_not_include`;
- `src/assets/semantic_selection/candidate_ranker.py` отклоняет candidates по must/must_not.

Пример:

```text
must_include: ["whale", "ocean"]
must_not_include: ["desert", "mountain", "city", "road", "farm"]
```

### 4.8. Один запрос или несколько

Несколько.

В news visual plan:

- `primary_query`;
- `alternative_queries`.

В semantic query generator:

- exact subject query;
- broad action query;
- environment fallback;
- atmospheric fallback.

Файл:

- `src/assets/semantic_selection/query_generator.py`

### 4.9. Используются ли синонимы

Частично.

Есть словарные расширения в:

- `scene_analyzer.py`;
- `query_generator.py`;
- `candidate_ranker.py`.

Но полноценной synonym dictionary или multilingual semantic expansion нет.

### 4.10. Используется ли LLM для ранжирования

Нет.

В текущем active коде для news asset selection LLM не вызывается. Legacy-код содержит OpenAI-вызовы, но текущий `src/news/*` pipeline сценарий/visual/ranking делает эвристически.

### 4.11. Используется ли анализ изображения

Нет, кроме precomputed `vision_tags`.

Файл:

- `src/assets/semantic_selection/vision_validator.py`

Он не вызывает vision model. Он только использует уже существующие tags в metadata, если они есть.

### 4.12. Анализ нескольких кадров видео

Не найден.

Есть создание thumbnails в old media library:

- `src/media_library.py::create_video_thumbnail`

Но эти thumbnails не используются для semantic visual validation.

### 4.13. Проверяется ли первый кадр или весь ролик

Нет. Проверяется техническая валидность файла через FFmpeg в old engine, но не смысловое содержание.

### 4.14. Проверяются ли похожие материалы в соседних сценах

Частично.

Файл:

- `src/assets/semantic_selection/continuity_checker.py`

Он проверяет грубые semantic jumps по словам, например ocean -> desert -> ocean. Но не проверяет визуальную похожесть и не сравнивает кадры.

---

## 5. Провайдерная архитектура

### 5.1. Есть ли общий интерфейс StockProvider

Единого полноценного интерфейса вида:

```python
search()
get_preview()
download()
get_license()
```

не найдено.

Есть частичный Protocol:

Файл:

- `src/news/asset_manager.py`

Класс:

- `AssetProvider`

Он содержит только:

```python
class AssetProvider(Protocol):
    name: str

    def search(self, query: str, scene: Mapping[str, Any], limit: int = 5) -> list[dict[str, Any]]:
        ...
```

Нет:

- `get_preview()`;
- `download()`;
- `get_license()`;
- `normalize_metadata()`;
- `validate_rights()`;
- `health_check()`;
- `rate_limit_policy`;
- `retry_policy`;
- `asset_type capabilities`.

### 5.2. Как сейчас подключаются источники

Источники подключаются разными способами:

1. В `src/news/asset_manager.py` через классы-adapters.
2. В `src/video_asset_engine.py` через прямые функции поиска и скачивания.
3. В `src/production_plan/solar_vs_nuclear_render.py` через собственные candidate functions.
4. В `src/asset_finder.py` через отдельную image search логику.
5. В `src/music_engine.py` для music отдельно.

### 5.3. Насколько легко добавить новый источник

Для news asset manager добавить новый provider относительно легко только на уровне `search()`. Но этого недостаточно для полноценной интеграции, потому что:

- download не часть интерфейса;
- license не часть интерфейса;
- preview не часть интерфейса;
- capabilities не описаны;
- разные pipeline используют разные структуры candidate;
- final renderer требует local path;
- media library теряет часть provenance fields.

### 5.4. Сильная связность Pexels/Pixabay

Связность высокая:

- `src/providers/*` только API wrappers;
- `src/news/asset_manager.py` знает raw response shape Pexels/Pixabay;
- `src/news/stock_video_downloader.py` знает raw response shape Pexels/Pixabay;
- `src/video_asset_engine.py` напрямую обрабатывает Pexels/Pixabay video files;
- `src/production_plan/solar_vs_nuclear_render.py` повторяет логику выбора и скачивания;
- `src/music_engine.py` отдельно использует Pixabay music.

### 5.5. Где будут проблемы при добавлении Wikimedia/NASA/Internet Archive

Проблемные места:

- `src/news/asset_manager.py::create_default_asset_providers`;
- schema candidates в `build_assets_manifest()`;
- downloader отсутствует в provider interface;
- license/provenance schema не унифицирована;
- final renderer требует `path`, а provider classes возвращают metadata;
- local library index не хранит богатые license fields;
- разные пайплайны придется менять отдельно.

### 5.6. Какие части кода придется менять для каждого нового провайдера

Минимально:

- добавить provider wrapper в `src/providers/`;
- добавить adapter class в `src/news/asset_manager.py`;
- обновить `create_default_asset_providers()`;
- обновить downloader или создать новый;
- обновить license mapping;
- обновить tests.

Но для реального качества придется также:

- выделить общий `StockProvider`;
- унифицировать candidate schema;
- добавить download lifecycle;
- добавить manifest/provenance schema;
- подключить provider к old engine или наоборот отключить дублирующие ветки;
- обновить media library.

---

## 6. Лицензии и происхождение файлов

### 6.1. Какие поля сейчас существуют

Проверяемые поля:

| Поле | Статус |
| --- | --- |
| `provider` | есть во многих manifest/index |
| `asset_id` | есть частично |
| `source_url` | есть частично |
| `download_url` | есть в media library и old engine, но не везде |
| `direct_download_url` | есть в news downloader и production plan |
| `author` | есть в news/prod manifests, но теряется в media library |
| `license` | есть частично |
| `license_url` | практически отсутствует |
| `attribution_required` | не найдено как системное поле |
| `commercial_use_allowed` | не найдено как системное поле |
| `download_date` | есть похожее `downloaded_at`, но не везде |
| `project_id` | не системно хранится на asset level |
| `scene_id` | есть в scene assignments |
| `filename` | есть через path/local_path |
| `original_filename` | не найдено как системное поле |

### 6.2. AssetRights model

Файл:

- `src/news/models.py`

Класс:

- `AssetRights`

Поля:

```python
provider
source_id
source_url
author
license_name
usage_rights
attribution
commercial_allowed
allowed_for_render
notes
```

Это хороший зачаток, но он не стал единой схемой для всех downloaded assets.

### 6.3. База данных лицензий

Отдельная база лицензий не найдена.

Есть:

- JSON manifests в проектах;
- `assets/library/metadata/media_index.json`;
- `project_solar_vs_nuclear/03_stock/selected_sources.json`;
- `project_solar_vs_nuclear/03_stock/selected_sources.md`;
- `projects/<job_id>/assets/assets_manifest.json`;
- `projects/<job_id>/exports/sources.json` через exporter.

### 6.4. Media library index

Файл:

- `G:\Projects\AI-YouTube\src\media_library.py`

Index:

- `G:\Projects\AI-YouTube\assets\library\metadata\media_index.json`

Нормализатор:

- `_normalize_asset()`

Поля media index:

```text
id, type, provider, source_url, download_url, local_path,
thumbnail_path, original_query, keywords, mood, channel_tags,
scene_tags, width, height, duration, fps, license_note,
downloaded_at, used_in
```

Проблема:

- не хранит `author`;
- не хранит `license_name`;
- не хранит `license_url`;
- не хранит `commercial_use_allowed`;
- не хранит `attribution_required`;
- не хранит `rights_status`;
- не хранит `project_id`/`scene_id` в нормализованной форме.

### 6.5. Можно ли доказать происхождение каждого файла

Частично.

Для fresh downloads в news standalone downloader и production plan часто можно восстановить:

- provider;
- source id;
- source page;
- direct download URL;
- author;
- license name;
- local path.

Но для local media library provenance неполный. После регистрации в media index теряются поля автора и формальной лицензии. Для старых ассетов доказательная цепочка слабая.

### 6.6. Проверка коммерческого использования

Системной проверки нет.

Есть:

- `allowed_for_render`;
- `rights_status`;
- `license_note`;
- `allow_unknown_rights=false` в channel config.

Но нет единой автоматической проверки по provider license policy и нет сохраненного `license_url`.

### 6.7. Список источников для YouTube description

Частично есть:

- `src/news/exporter.py` пишет `sources.json` и `description.txt`;
- `src/production_plan/solar_vs_nuclear_render.py::write_stock_source_index()` пишет `selected_sources.md`;
- old pipeline пишет YouTube metadata через `src/youtube_metadata.py`, но не найден единый sources block с лицензиями ассетов.

### 6.8. Риск материала с неизвестной лицензией

Риск есть.

Особенно:

- article images получают license `unknown` и `reference_only`;
- media library local assets могут не иметь rights metadata;
- old documentary pipeline использует `license_note`, но не formal license schema;
- user assets считаются `user_owned`, но без документов/доказательств;
- future providers без license normalization усилят проблему.

---

## 7. Структура хранения проектов и файлов

### 7.1. News projects

Реальная структура создается `src/news/project_store.py`.

Шаблон:

```text
projects/<job_id>/
  job.json
  input/input.json
  article/article.json
  article/images.json
  research/claims.json
  master/master_visual_plan.json
  master/sources.json
  assets/assets_manifest.json
  assets/missing_assets.json
  assets/stock_videos/
  localizations/<lang>/script/script.json
  localizations/<lang>/script/narration.txt
  localizations/<lang>/visual/visual_plan.json
  localizations/<lang>/voice/voice_manifest.json
  localizations/<lang>/voice/voice_selection.json
  localizations/<lang>/voice/previews/
  localizations/<lang>/subtitles/subtitles.srt
  localizations/<lang>/subtitles/subtitles.ass
  localizations/<lang>/subtitles/subtitles_manifest.json
  localizations/<lang>/output/
```

В существующих проектах найдены разные состояния:

- некоторые имеют готовый `master_1080x1920.mp4`;
- некоторые дошли до `export`, но без финального output;
- некоторые остановлены на `asset_search` или `voice`;
- один или несколько манифестов имеют старые статусы вроде `renderer_not_connected`/`ready_for_renderer`.

### 7.2. Production project

Папка:

- `G:\Projects\AI-YouTube\project_solar_vs_nuclear`

Структура:

```text
project_solar_vs_nuclear/
  01_script/
    hook.txt
    voiceover_ru.txt
    scenes.json
  02_voice/
    voice_final.wav
    voice_manifest.json
  03_stock/
    selected_sources.json
    selected_sources.md
    stock_selection_report.json
    ...
  04_motion/
  05_project/
    capcut/
    exports/
    render_manifest.json
  06_analytics/
    render_readiness.json
```

### 7.3. Old pipeline outputs

Шаблон из `src/channel_loader.py`:

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
  visual_debug.json
  final_preview.mp4
  final_video.mp4
  render_temp/
```

### 7.4. Media library

Файл:

- `src/media_library.py`

Реальная root:

```text
assets/library/
  videos/
  images/
  music/
  thumbnails/
  metadata/
    media_index.json
```

### 7.5. Временные файлы

Найдены:

- old pipeline: `outputs/<channel>/<video>/render_temp`;
- news final render: `localizations/<lang>/output/render/segments`;
- production plan: `05_project/render`;
- anime factory: собственные intermediate dirs.

Очистка:

- `src/media_library.py::clean_temp_files()` чистит только некоторые temp-файлы в `outputs/`;
- news/prod render temp cleanup системно не найден;
- `pipeline.py --clean-temp` вызывает media library cleanup.

### 7.6. Перезапись предыдущих проектов

News:

- `job_id` содержит timestamp, риск перезаписи ниже.

Production plan:

- `create_solar_vs_nuclear_plan()` пишет в фиксированную папку `project_solar_vs_nuclear` и обновляет файлы. Риск перезаписи есть.

Old pipeline:

- output dir фиксируется как `outputs/<channel>/<video>`, plan/output files могут перезаписываться.

### 7.7. Продолжение после сбоя

News:

- есть `--resume`;
- есть `--stage`;
- есть `--force-stage`;
- состояние стадий хранится в `job.json`;
- это хорошая основа.

Old pipeline:

- скорее перегенерирует планы и выходы;
- полноценный resumable state слабее.

Production plan:

- можно повторно запускать renderer, он сохраняет/переиспользует reviewed assets.

### 7.8. Повторное использование материалов

Есть local media library:

- `src/media_library.py`;
- `assets/library/metadata/media_index.json`.

Но:

- license fields неполные;
- semantic search metadata-only;
- нет perceptual dedupe;
- нет централизованного "asset already downloaded from this provider" для всех pipeline.

---

## 8. Озвучка

### 8.1. TTS-провайдеры

Найдены:

| Провайдер | Файлы | Статус |
| --- | --- | --- |
| ElevenLabs | `src/audio/tts/elevenlabs_provider.py`, `src/voice_engine.py` | Реализован |
| Audio file/manual WAV | `src/audio/tts/audio_file_provider.py`, `src/audio/voice_workflow.py` | Реализован частично |
| Local stub/silence | `src/voice_engine.py` | Есть для old pipeline |
| MOSS TTS | `src/tts_providers/moss_tts_provider.py` | Локальный experimental provider |

### 8.2. Где хранится ElevenLabs API key

Переменная окружения:

- `ELEVENLABS_API_KEY`

Файлы использования:

- `src/audio/tts/env.py`
- `src/audio/tts/elevenlabs_provider.py`
- `src/voice_engine.py`
- `src/production_plan/solar_vs_nuclear_render.py`

`.env` содержит переменную, но значения в аудите не раскрывались.

### 8.3. Как выбирается voice_id

Источники:

- `channels/nature_science_news_ru/channel_config.json`;
- `channels/nature_science_news_ru/voices.yaml`;
- environment `ELEVENLABS_VOICE_ID`;
- fallback constants в production plan;
- CLI args `--voice-id`, `--voice-profile`.

Для news channel есть profile `ru_dom` с provider `elevenlabs`, model `eleven_multilingual_v2`.

### 8.4. Тестовый режим/короткий фрагмент

Есть через voice CLI:

- `src/audio/voice_cli.py`
- action `audition`

Логика:

- max audition text обычно 300 символов;
- output в `localizations/<lang>/voice/previews/`;
- перед paid synthesize вызывается `preflight()`;
- требуется approval record для полного paid TTS.

### 8.5. Можно ли загрузить WAV вручную

Да.

Файлы:

- `src/audio/tts/audio_file_provider.py`
- `src/audio/voice_workflow.py::import_manual_audio`
- `src/audio/voice_cli.py`

Поддерживается WAV import. Provider проверяет WAV через `wave.open`.

### 8.6. HTTP 401

Файл:

- `src/audio/tts/elevenlabs_provider.py`

При `status_code >= 400` выбрасывается:

```text
PermissionError("ElevenLabs request failed with HTTP <status>")
```

401 отдельно не обрабатывается, но попадает в общий HTTP error branch.

### 8.7. Retry

Retry для ElevenLabs не найден.

### 8.8. Промежуточные аудио

Да:

- previews в `voice/previews`;
- imported/manual audio в `voice/`;
- old voice cache в configured cache dir;
- production plan хранит `voice_final.mp3`/`voice_final.wav`.

### 8.9. Поддержка языков и голосов

Частично.

Config содержит `ru`, `en`, `es` в `channels/nature_science_news_ru/channel_config.json`, но:

- включен в основном `ru`;
- генерации переводов не найдено;
- разные voice profiles есть как структура, но полноценный multilingual workflow не завершен.

---

## 9. Локализация

### 9.1. Структура

News project store создает:

```text
localizations/
  ru/
  en/
  es/
```

В каждой:

```text
script/
voice/
  previews/
subtitles/
visual/
output/
```

### 9.2. Что реально работает

Работает частично:

- можно выбрать `--language`;
- сценарий/visual/subtitles/voice/output раскладываются в language-specific папки;
- config может описывать разные языки/голоса.

### 9.3. Ограничения

Не найдено:

- генерация перевода сценария ru -> en/es;
- отдельные language-specific visual adaptations;
- полноценная синхронизация отдельных voice/subtitle/final для нескольких языков в одном запуске;
- language-specific YouTube metadata на всех уровнях.

---

## 10. Монтаж

### 10.1. Используемые инструменты

Найдены:

- FFmpeg через subprocess;
- MoviePy;
- Pillow;
- imageio-ffmpeg;
- локальные helper modules.

CapCut:

- папка `05_project/capcut` есть в production plan;
- автоматической интеграции CapCut не найдено.

### 10.2. News final renderer

Файл:

- `src/news/final_renderer.py`

Функция:

- `render_final_video()`

Рендер:

- 1080x1920;
- fps 30;
- libx264;
- CRF 21-23;
- pixel format yuv420p.

Выбор фрагмента исходного видео:

- используется `stream_loop -1`;
- берется начало/повтор исходника;
- смыслового выбора лучшего фрагмента нет.

Crop:

- center crop через FFmpeg scale/crop;
- dynamic crop отсутствует.

Переходы:

- не реализованы как реальные transitions в news final renderer;
- visual plan содержит `transition`, но renderer делает concat.

Музыка:

- поддержана только если существует `assets/music/music_manifest.json`;
- news pipeline не имеет отдельной стадии генерации music manifest.

SFX:

- не найдено.

Синхронизация озвучки:

- final renderer берет `voice_manifest.audio_path`;
- subtitle timings строятся из script scene timing, не forced alignment.

Субтитры:

- `.ass` прожигаются FFmpeg.

Безопасные зоны:

- ASS MarginV жестко задан;
- более широкая система safe zones в news renderer ограничена.

Промежуточные рендеры:

- сохраняются в `output/render/segments`.

### 10.3. Old video renderer

Файл:

- `src/video_renderer.py`

Особенности:

- строит render plan;
- создает scene clips;
- умеет fast FFmpeg overlay для video clips;
- иначе использует MoviePy frame generation;
- добавляет музыку через `src/music_tools.py`;
- делает self evaluation.

Crop:

- FFmpeg scale/crop;
- generated motion/zoom для images/placeholders;
- dynamic semantic crop не найден.

### 10.4. Production plan renderer

Файл:

- `src/production_plan/solar_vs_nuclear_render.py`

Особенности:

- vertical 1080x1920;
- fixed 12 scene timeline;
- скачивает stock;
- renders segments;
- добавляет voice/music/subtitles;
- пишет manifest.

Это самый завершенный renderer, но он hardcoded под конкретный проект.

### 10.5. Anime Factory renderer

Файл:

- `anime_factory/pipeline.py`

Использует FFmpeg и собственные модули для:

- scene detection;
- candidate scoring;
- vertical crop modes:
  - `center`;
  - `smart_static`;
  - `dynamic`;
  - `blur`;
  - `auto`.

Это не связано с stock/news pipeline.

---

## 11. UI и управление

### 11.1. Есть ли интерфейс

Полноценный UI, локальный сервер или API не найден.

Текущий способ управления:

- CLI через `pipeline.py`;
- wrapper scripts в `apps/*`;
- ручное редактирование/добавление файлов;
- static HTML preview для production plan.

### 11.2. Production preview

Файл:

- `src/production_plan/youtube_shorts.py::render_html_preview`

Выход:

- `project_solar_vs_nuclear/preview.html`

Это статическая таблица сцен/ассетов/readiness. Она не является интерактивным UI.

### 11.3. Можно ли заменить материал сцены

Частично:

- production plan: `replace_selected_clip(project_root, scene_id, clip_path, provider, note)`;
- old pipeline: manual assets через папки;
- news pipeline: user assets через `--assets`, но полноценного UI выбора/замены нет.

### 11.4. Можно ли просмотреть preview

Частично:

- production plan static `preview.html`;
- old renderer может создавать final preview;
- news preview renderer создает preview только из готового final video.

### 11.5. Можно ли выбрать один из нескольких вариантов

Нет полноценного UI.

В коде кандидаты собираются и ranked_candidates могут сохраняться, но интерактивного выбора не найдено.

### 11.6. Можно ли вручную загрузить файл

Частично:

- voice WAV import;
- user assets для news;
- manual_assets для old pipeline;
- production plan `replace_selected_clip`.

### 11.7. Можно ли остановить и продолжить генерацию

News:

- да, через stage state и `--resume`.

Old pipeline:

- ограниченно.

Production plan:

- повторный запуск возможен, но это не полноценная task queue.

### 11.8. Ошибки понятным языком

Частично:

- news stage state записывает `error`;
- quality_check пишет errors/warnings;
- voice CLI пишет понятные статусы;
- многие provider errors в отдельных местах silently ignored.

---

## 12. Конфигурация и секреты

### 12.1. `.env`

Файл:

- `G:\Projects\AI-YouTube\.env`

Проверены только имена переменных, значения не раскрывались.

Найдены переменные:

- `OPENAI_API_KEY`;
- `PEXELS_API_KEY`;
- `PIXABAY_API_KEY`;
- `UNSPLASH_ACCESS_KEY`;
- `ELEVENLABS_API_KEY`;
- `ELEVENLABS_VOICE_ID`.

### 12.2. `.env.example`

Файл:

- `G:\Projects\AI-YouTube\.env.example`

Найдены переменные:

- `OPENAI_API_KEY`;
- `PEXELS_API_KEY`;
- `PIXABAY_API_KEY`;
- `UNSPLASH_ACCESS_KEY`;
- `ELEVENLABS_API_KEY`.

### 12.3. Config-файлы

Основные:

- `config/video_style.json`;
- `channels/nature_science_news_ru/channel_config.json`;
- `channels/nature_science_news_ru/voices.yaml`;
- `anime_factory/config.yaml`;
- `project_solar_vs_nuclear/project_config.json`.

### 12.4. FFmpeg

Используется через:

- `subprocess.run(["ffmpeg", ...])`;
- `subprocess.run(["ffprobe", ...])`;
- `imageio_ffmpeg.get_ffmpeg_exe()` в некоторых местах.

Путь к FFmpeg не централизован полностью. Часть кода рассчитывает на `ffmpeg` в PATH.

### 12.5. Настройки качества

Примеры:

- `config/video_style.json`:
  - dev/prod resolution;
  - fps;
  - duration;
  - codec settings;
  - documentary settings;
- `channels/nature_science_news_ru/channel_config.json`:
  - 1080x1920;
  - fps 30;
  - target_duration 55;
  - asset selection mode;
  - voice workflow;
- `anime_factory/config.yaml`:
  - render resolution;
  - subtitles;
  - crop modes.

### 12.6. Лимиты API и timeout

Timeout есть:

- Pexels/Pixabay/Unsplash provider wrappers: 24 сек;
- article ingestion: 20 сек;
- ElevenLabs synthesize: 60 сек;
- ElevenLabs preflight: 20 сек;
- downloads: часто 30 сек.

Retry/backoff почти нет.

### 12.7. Захардкоженные значения

Примеры:

- ElevenLabs default voice fallback в production plan;
- `solar_vs_nuclear` hardcoded project;
- old layout hardcoded text for Jordan Peterson;
- fixed durations/script templates in news script generator;
- whale/ocean specific semantic heuristics;
- fixed output resolutions in several renderers.

---

## 13. Ошибки и устойчивость

### 13.1. TODO/FIXME/заглушки

Литеральные TODO/FIXME в `src` массово не обнаружены, но есть функциональные заглушки:

- `src/news/voice_stage.py` - no paid call, requires manual workflow;
- `src/news/preview_renderer.py` - preview only from final video;
- `src/news/pipeline.py::_write_placeholder_stage()` для unknown stage;
- generated/placeholder fallback assets;
- legacy modules.

### 13.2. Критические потенциальные падения

1. **News final render без local asset path**  
   `src/news/final_renderer.py` требует `selected_asset.path`. Но `src/news/asset_manager.py` provider candidates path не создают.

2. **Voice stage not completed**  
   `src/news/quality_check.py` требует completed voice manifest. `build_safe_voice_manifest()` обычно создает status requiring selection/approval.

3. **Preview before final impossible**  
   `src/news/preview_renderer.py` блокируется, если нет final video.

4. **Provider API errors**  
   В одних местах падают через `raise_for_status`, в других silently ignored.

5. **FFmpeg path**  
   Часть вызовов рассчитывает на `ffmpeg`/`ffprobe` в PATH.

### 13.3. Отсутствие retry

Нет retry/backoff для:

- Pexels;
- Pixabay;
- Unsplash;
- ElevenLabs;
- downloads;
- article ingestion.

### 13.4. Пустые результаты

Обработка пустых результатов есть частично:

- scene попадает в `missing_assets`;
- quality check может блокировать;
- old engine может создать generated fallback.

Но:

- в news pipeline нет автоматического перехода к скачиванию;
- some provider errors can be lost;
- generated fallback запрещен по умолчанию в некоторых configs.

### 13.5. Windows пути и кириллица

Плюсы:

- используется `Path`;
- JSON пишется с `ensure_ascii=False`;
- subtitle path escaping есть в news/prod renderers;
- существующие проекты с кириллическими именами реально присутствуют.

Риски:

- FFmpeg path escaping не централизован;
- некоторые manifest paths выглядят как Windows strings;
- не найдено полного теста всего render pipeline на кириллическом project path.

### 13.6. Риск скачать неправильный материал

Высокий.

Причины:

- metadata-only ranking;
- Pexels/Pixabay adapters не передают богатые tags/description;
- нет анализа превью;
- нет анализа нескольких кадров;
- generic/fallback запросы могут увести в неверный контекст;
- production plan search silently ignores provider errors and picks by keywords only;
- old engine больше проверяет техническое качество, чем смысл.

---

## 14. Тесты

### 14.1. Наличие тестов

Папка:

- `G:\Projects\AI-YouTube\tests`

Тесты есть. Они покрывают:

- news models/project store/pipeline;
- news assets and rights;
- news final renderer на synthetic/manual assets;
- voice workflow;
- semantic asset selection;
- media library;
- documentary visual engine;
- production plan;
- anime factory;
- size comparison.

### 14.2. Тестируется ли Pexels/Pixabay

Реальные API Pexels/Pixabay не тестируются. Используются fake providers/fixtures. Это правильно для unit tests, но integration test layer отсутствует.

### 14.3. Тестируется ли поиск

Частично:

- semantic ranker;
- fake provider selection;
- local assets.

Не тестируется:

- реальные API schemas;
- rate limits;
- network failures;
- retry behavior.

### 14.4. Тестируется ли выбор визуала

Да, на уровне metadata/semantic heuristics:

- `tests/test_semantic_asset_selection.py`;
- `tests/test_news_to_short_assets.py`;
- `tests/test_documentary_visual_engine.py`.

Но не тестируется visual analysis кадров.

### 14.5. Тестируется ли лицензирование

Частично:

- blocked/reference-only assets;
- unknown rights;
- generated placeholders forbidden;
- source index в production plan.

Но нет теста полной license/provenance schema.

### 14.6. Тестируется ли рендер

Частично:

- news final renderer на тестовых картинках/WAV;
- old/documentary render plan;
- production plan readiness.

Реальный тяжелый render/API/download не запускался в аудите.

### 14.7. Есть ли тестовый проект

Да, в тестах создаются temp projects. В рабочей папке также есть реальные `projects/*` и `project_solar_vs_nuclear`.

---

## 15. Подготовка к новым источникам

### 15.1. Wikimedia Commons

Логично встроить:

- новый wrapper `src/providers/wikimedia_provider.py`;
- adapter в news asset manager;
- downloader/download method;
- license normalizer.

Нужно хранить:

- file page URL;
- original file URL;
- author/creator;
- license;
- license URL;
- attribution text;
- attribution required;
- commercial use;
- modifications allowed;
- Wikimedia page id/title;
- download date.

Риски:

- разные лицензии CC BY, CC BY-SA, public domain;
- обязательная атрибуция;
- разные размеры derivatives;
- не все материалы подходят для коммерческого YouTube.

Главная архитектурная проблема:

- нет `get_license()`/`download()` в provider interface.

### 15.2. NASA Image and Video Library

Логично встроить:

- `src/providers/nasa_provider.py`;
- provider capabilities для image/video;
- license policy adapter.

Нужно хранить:

- NASA asset id;
- title;
- description;
- center;
- photographer/creator, если есть;
- media type;
- source URL;
- direct download URL;
- NASA usage note;
- date_created;
- download date.

Риски:

- NASA media generally public, но не все third-party/personality/trademark restrictions простые;
- некоторые assets имеют разные renditions;
- videos могут требовать отдельной обработки.

### 15.3. Internet Archive

Логично встроить:

- `src/providers/internet_archive_provider.py`;
- separate metadata/license parser;
- downloader with file selection.

Нужно хранить:

- item identifier;
- file name;
- file format;
- metadata page;
- licenseurl/license;
- creator;
- collection;
- date;
- download URL;
- checksum, если доступен.

Риски:

- неоднородные лицензии;
- старые/архивные материалы могут иметь спорный статус;
- много файлов на один item;
- качество/кодеки разнообразные.

### 15.4. Envato Manual Provider

Логично встроить:

- manual provider layer, не automated downloader;
- `src/providers/envato_manual_provider.py`;
- UI/CLI flow для формирования запроса и записи ручного выбора;
- license receipt storage.

Нужно хранить:

- search query;
- Envato item URL;
- item id/name;
- author;
- license certificate/file;
- download date;
- user confirmation;
- local filename;
- project/scene assignment.

Риски:

- автоматическое скачивание может нарушать ToS;
- нужен ручной approval;
- license зависит от subscription/project registration;
- нужен UI или четкий CLI workflow.

### 15.5. Local Library Provider

Частично уже есть:

- `src/media_library.py`;
- `src/news/asset_manager.py::_rank_local_assets`;
- `src/video_asset_engine.py` local first.

Что нужно:

- сделать local library полноценным provider;
- расширить index schema;
- добавить license/provenance validation;
- добавить thumbnails/vision tags/perceptual hashes;
- добавить reuse policy.

Риски:

- текущие local assets могут быть без прав;
- media index теряет author/license fields;
- повторное использование может нарушать channel diversity.

---

## 16. Итоговая оценка компонентов

| Компонент | Текущее состояние | Что работает | Что частично | Чего нет | Критичность | Рекомендуемый следующий шаг |
| --- | --- | --- | --- | --- | --- | --- |
| Главный CLI | работает частично | Много режимов запуска | Слишком много веток в одном файле | Единой app architecture | высокая | Разделить режимы и задокументировать основной pipeline |
| News project store | готово | State, stages, resume dirs | Нет миграций schema | DB/locking | средняя | Зафиксировать schema job/project |
| Article ingestion | прототип | URL/text/topic ingestion | HTML parsing regex-based | Robust extraction/fact research | средняя | Подключить нормальный extractor/research stage |
| Research | прототип | Claims из текста | Только эвристики | Fact checking, source validation | средняя | Определить research contract |
| Script generation | прототип | Делает 6 сцен | Fixed templates | LLM/quality controls/localization | высокая | Ввести script schema + generator interface |
| Visual plan | прототип | Primary/alternative queries | Whale/ocean-heavy heuristics | LLM/query expansion | высокая | Унифицировать semantic scene model |
| News asset search | требует исправления | Сбор candidates, ranking | Provider metadata | Скачивание provider assets в main pipeline | критическая | Соединить search -> download -> manifest |
| Pexels | работает частично | Official API wrappers | Несколько разных integrations | Retry/license/full schema | высокая | Обернуть в единый provider |
| Pixabay | работает частично | Official API wrappers, music | Несколько integrations | Retry/license/full schema | высокая | Обернуть в единый provider |
| Unsplash | прототип | Image search | Только news adapter | Video/download lifecycle | средняя | Решить, нужен ли для Shorts |
| Local library | работает частично | Index, reuse, thumbnails | Weak rights metadata | Vision tags/hash/license DB | высокая | Расширить schema и rights gate |
| Semantic ranking | прототип | Must/must_not, scoring | Metadata-only | Frame/preview/LLM ranking | высокая | Добавить visual validation stage |
| License/provenance | требует исправления | Есть отдельные fields | Разные manifests | Единая доказательная цепочка | критическая | Ввести AssetProvenance schema |
| News voice stage | работает частично | Safe no-paid default | Требует manual/approval | Автоматический approved full TTS stage | высокая | Развести audition/full synth workflow |
| ElevenLabs provider | работает частично | Synthesis/preflight | Approval manager частично | Retry/401 UX/rate handling | средняя | Добавить retry и typed errors |
| Subtitles | работает частично | SRT/ASS | Timing по сценам | Forced alignment | средняя | Синхронизировать с voice duration |
| News final render | работает частично | FFmpeg vertical render | Требует local paths | Dynamic crop/transitions/SFX | высокая | Подключить asset downloader и robust render plan |
| Music | работает частично | Old pipeline/Pixabay music | News renderer только читает manifest | News music stage/SFX | средняя | Добавить music stage для news |
| UI | отсутствует | Static preview только production plan | CLI/manual workflows | Scene picker/replacement/preview | средняя | Спроектировать минимальный review UI |
| Production plan | работает частично | Конкретный проект render-ready | Hardcoded scenario | Universal workflow | средняя | Извлечь reusable parts |
| Anime Factory | работает частично | Local video Shorts cutter | Отдельный продукт | Stock/news integration | низкая | Держать отдельным модулем |
| Tests | работает частично | Много unit tests | Fake providers | Live integration/render smoke | средняя | Добавить contract tests providers |

---

## 17. Приоритеты

### 17.1. Критические проблемы

1. Main news pipeline не скачивает provider assets, хотя final renderer требует локальные paths.
2. News voice stage не создает финальную озвучку автоматически, а quality gate требует completed voice.
3. Нет единой схемы license/provenance, поэтому происхождение каждого файла нельзя надежно доказать.
4. Provider architecture раздроблена: Pexels/Pixabay логика повторяется в нескольких местах.
5. Visual matching metadata-only, без анализа превью/кадров, поэтому высок риск неправильных материалов.
6. Media library теряет важные rights/author/license fields.
7. Retry/backoff почти отсутствуют для API/download/TTS.
8. Preview stage в news pipeline зависит от уже готового финального видео.

### 17.2. Высокий приоритет

1. Ввести общий `StockProvider` contract: search, preview, download, license, normalize.
2. Ввести единую `AssetCandidate` и `AssetProvenance` schema.
3. Соединить news `asset_search` со скачиванием и сохранением local paths.
4. Перенести Pexels/Pixabay/Unsplash на один provider abstraction.
5. Расширить media library index с license/provenance fields.
6. Добавить clear errors и provider error manifest.
7. Сделать deterministic resume-safe stages для download/render.
8. Добавить integration tests с mocked HTTP schemas.

### 17.3. Средний приоритет

1. Добавить visual preview/frame analysis.
2. Добавить UI или CLI review screen для выбора ассетов.
3. Добавить music stage для news pipeline.
4. Улучшить subtitles timing с учетом реальной озвучки.
5. Добавить smart/dynamic crop для Shorts.
6. Добавить source list generator для YouTube description.
7. Сделать локализацию ru/en/es полноценной.

### 17.4. Низкий приоритет

1. Envato browser/manual flow.
2. Advanced SFX.
3. Perceptual duplicate detection.
4. Analytics feedback loop.
5. Автоматическая публикация на YouTube.

---

## 18. Что нужно передать ChatGPT для подготовки плана реализации

### 18.1. Краткая архитектурная схема

```text
CLI pipeline.py
  |-- news-to-short
  |     |-- project_store/job.json
  |     |-- article_ingestor
  |     |-- research_engine
  |     |-- script_generator
  |     |-- visual_plan
  |     |-- asset_manager
  |     |     |-- local media library
  |     |     |-- Pexels/Pixabay/Unsplash adapters
  |     |     |-- semantic_selection
  |     |-- voice_stage / voice_cli
  |     |-- subtitles
  |     |-- quality_check
  |     |-- final_renderer
  |
  |-- old documentary pipeline
  |     |-- scene_planner
  |     |-- video_asset_engine
  |     |-- voice_engine
  |     |-- music_engine
  |     |-- video_renderer
  |
  |-- production_plan solar_vs_nuclear
  |     |-- fixed project generator
  |     |-- stock downloader/renderer
  |
  |-- anime_factory
        |-- local episode to Shorts
```

### 18.2. Основные файлы

```text
pipeline.py
src/news/pipeline.py
src/news/models.py
src/news/project_store.py
src/news/article_ingestor.py
src/news/article_parser.py
src/news/research_engine.py
src/news/script_generator.py
src/news/visual_plan.py
src/news/asset_manager.py
src/news/stock_video_downloader.py
src/news/voice_stage.py
src/news/subtitles.py
src/news/quality_check.py
src/news/final_renderer.py
src/news/exporter.py
src/assets/semantic_selection/models.py
src/assets/semantic_selection/scene_analyzer.py
src/assets/semantic_selection/query_generator.py
src/assets/semantic_selection/candidate_ranker.py
src/assets/semantic_selection/continuity_checker.py
src/assets/semantic_selection/vision_validator.py
src/providers/pexels_provider.py
src/providers/pixabay_provider.py
src/providers/unsplash_provider.py
src/media_library.py
src/video_asset_engine.py
src/asset_finder.py
src/voice_engine.py
src/audio/voice_cli.py
src/audio/voice_workflow.py
src/audio/tts/elevenlabs_provider.py
src/audio/tts/audio_file_provider.py
src/music_engine.py
src/video_renderer.py
src/production_plan/youtube_shorts.py
src/production_plan/solar_vs_nuclear_render.py
anime_factory/pipeline.py
```

### 18.3. Текущая структура провайдеров

```text
src/providers/
  pexels_provider.py      - function wrappers, official API
  pixabay_provider.py     - function wrappers, official API
  unsplash_provider.py    - function wrapper, official API

src/news/asset_manager.py
  AssetProvider Protocol  - only search()
  PexelsAssetProvider
  PixabayAssetProvider
  UnsplashAssetProvider

src/video_asset_engine.py
  duplicated Pexels/Pixabay video search/download

src/news/stock_video_downloader.py
  duplicated Pexels/Pixabay download for news projects

src/production_plan/solar_vs_nuclear_render.py
  duplicated Pexels/Pixabay candidate/download logic
```

### 18.4. Текущая схема проекта и сцен

News project:

```text
job.json
input/input.json
article/article.json
research/claims.json
localizations/<lang>/script/script.json
localizations/<lang>/visual/visual_plan.json
assets/assets_manifest.json
localizations/<lang>/voice/voice_manifest.json
localizations/<lang>/subtitles/subtitles_manifest.json
localizations/<lang>/output/final_render_manifest.json
```

Scene in script:

```json
{
  "scene_id": "scene_001",
  "start_sec": 0.0,
  "target_duration_sec": 3.5,
  "narration": "...",
  "claim_ids": [],
  "visual_intent": "...",
  "on_screen_text": "...",
  "emotion": "curiosity"
}
```

Visual plan item:

```json
{
  "scene_id": "scene_001",
  "visual_type": "video",
  "primary_query": "...",
  "alternative_queries": [],
  "negative_keywords": [],
  "allow_stock": true,
  "allow_user_asset": true,
  "fallback_type": "animated_image"
}
```

### 18.5. Текущая схема хранения лицензий

Сейчас нет одной схемы. Есть разрозненные поля:

```text
provider
source_id / asset_id
source_url / source_page
direct_download_url / download_url
author
license / license_name / license_note
rights_status
allowed_for_render
downloaded_at
path / local_path / downloaded_path
```

Недостающие обязательные поля для будущего:

```text
license_url
attribution_required
commercial_use_allowed
modification_allowed
attribution_text
download_date
project_id
scene_id
original_filename
checksum
provider_terms_snapshot
```

### 18.6. Текущая логика поиска и ранжирования

```text
visual_plan -> analyze_scene -> ordered_queries
  -> provider.search(query)
  -> _rank_provider_results
  -> select_best_candidate
  -> continuity check
```

Ранжирование:

- subject match;
- action match;
- environment match;
- camera match;
- quality score;
- vertical score;
- rights check;
- duplicate penalty;
- negative keyword rejection.

Нет:

- LLM ranking;
- visual preview analysis;
- multi-frame video analysis;
- perceptual duplicate detection.

### 18.7. Главные проблемы

1. Main news asset search не скачивает файлы.
2. Provider interface содержит только `search`.
3. Final renderer требует local path, но search candidates его не имеют.
4. Voice stage intentionally safe, но не end-to-end.
5. License/provenance schema неполная.
6. Media library теряет rights metadata.
7. Semantic matching слишком эвристический и domain-specific.
8. Нет retry/backoff.
9. Нет UI review flow.
10. Несколько pipeline дублируют одну и ту же provider/download логику.

### 18.8. Рекомендуемая последовательность изменений

1. Зафиксировать целевой основной pipeline: скорее всего `src/news/*`.
2. Ввести единые dataclasses/schema:
   - `AssetCandidate`;
   - `DownloadedAsset`;
   - `AssetProvenance`;
   - `LicenseInfo`.
3. Расширить `StockProvider`:
   - `search`;
   - `get_preview`;
   - `download`;
   - `get_license`;
   - `normalize`;
   - capabilities.
4. Перевести Pexels/Pixabay/Unsplash на этот интерфейс.
5. Подключить download stage в news pipeline.
6. Обновить media library schema без потери provenance.
7. Добавить provider contract tests с mocked responses.
8. Сделать voice workflow явным:
   - draft/manual;
   - audition;
   - approval;
   - full synth.
9. Добавить preview/review stage до final render.
10. После стабилизации подключать Wikimedia, NASA, Internet Archive, Envato manual, Local Library provider.

---

## 19. Финальный вывод

Проект уже содержит много полезных заготовок: project state, сценный сценарий, semantic ranking, Pexels/Pixabay wrappers, local media library, voice workflow, FFmpeg renderers и тесты. Но сейчас это не единая стабильная система. Главный разрыв находится между поиском ассетов, скачиванием, лицензированием и финальным рендером.

Самый практичный следующий шаг - не добавлять новые источники сразу, а сначала стабилизировать provider/download/provenance architecture. Иначе Wikimedia, NASA, Internet Archive, Envato и local library будут добавлены в уже раздробленную систему и усилят технический долг.
