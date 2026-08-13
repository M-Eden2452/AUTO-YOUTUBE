---
status: historical
audit_date: 2026-07-22
---

> **HISTORICAL (2026-07-22) — не текущая инструкция и не карта текущей
> архитектуры.** Эта серия описывает репозиторий **до** governance-reset:
> `pipeline.py` как основной вход, `asset_finder` / `video_asset_engine` как
> действующая asset-система, модули, часть которых уже удалена или ретайрена.
> Канонический CLI сегодня — `python -m ai_youtube`. Current truth:
> [SYSTEM_MAP.md](../current/SYSTEM_MAP.md) и
> [CLEANUP_REGISTRY.md](../current/CLEANUP_REGISTRY.md); индекс каталога —
> [README.md](README.md). Команды и пути отсюда не исполнять.

# PROJECT AUDIT OVERVIEW

## 1. Реальное назначение приложения

Фактически проект является набором Python CLI-pipeline для автоматизации создания вертикальных и частично documentary-style видео: сценарий, сцены, visual plan, stock assets, voice, subtitles, render и export. Внутри репозитория сосуществуют несколько поколений и направлений:

- новый `news-to-short` pipeline в `src/news`;
- старый documentary/quote/channel pipeline в корневом `pipeline.py` и модулях `src/*.py`;
- project-specific `solar_vs_nuclear`;
- отдельный `anime_factory`;
- специализированный size comparison pipeline;
- legacy scripts;
- wrappers в `apps/`.

## 2. Задуманное назначение

Задуманный продукт шире текущей реализации: пользователь передаёт тему, ссылку, текст, сценарий или локальные материалы, система исследует тему, строит сценарий, разбивает на сцены, ищет и скачивает визуалы, проверяет лицензии, создаёт озвучку, субтитры, музыку/SFX, монтирует видео и экспортирует варианты для YouTube Shorts, Reels, TikTok и длинных роликов.

## 3. Разница между задуманным и реальным

| Возможность | Заявлена | Реально реализована | Подключена к pipeline | Требует ручного шага | Состояние |
|---|---:|---:|---:|---:|---|
| URL -> short project | Да | Да | Да | Нет/иногда review | работает частично |
| Topic/text -> script | Да | Да, heuristic/template | Да | Нет | прототип |
| LLM research/fact checking | Да в идее/docs | Только legacy OpenAI scripts | Нет в main news | Да/нет | отсутствует в main |
| Scene split | Да | Да | Да | Нет | работает частично |
| Visual plan | Да | Да | Да | Нет | прототип |
| Semantic visual matching | Да | Да, metadata heuristics | Да | Нет | прототип |
| Pexels search | Да | Да | Частично | Нет | работает частично |
| Pexels download | Да | Да в отдельных модулях | Не в main news | Да | работает частично |
| Pixabay search | Да | Да | Частично | Нет | работает частично |
| Pixabay download | Да | Да в отдельных модулях | Не в main news | Да | работает частично |
| Unsplash | Да/есть ключ | Image metadata search | Частично | Да | прототип |
| Wikimedia/NASA/Internet Archive | Будущее | Нет | Нет | Да | отсутствует |
| Envato manual | Будущее/docs | Нет | Нет | Да | отсутствует |
| Local library reuse | Да | Да, basic index/search | Частично | Нет | работает частично |
| License proof | Да | Частично | Частично | Да | требует исправления |
| ElevenLabs voice | Да | Да | Да в разных flows | Approval/manual required in news | работает частично |
| Manual WAV | Да | Да | Да | Да | готово/частично |
| MOSS local TTS | Да | Experimental provider | Не main | Да | эксперимент |
| Subtitles | Да | SRT/ASS | Да | Нет | работает частично |
| Music | Да | Old music engine/Pixabay | Не в news stage | Да | прототип |
| SFX | Да | Не найдено как стадия | Нет | Да | отсутствует |
| Final render | Да | FFmpeg/MoviePy | Да | Зависит от assets/voice | работает частично |
| UI | Будущее | Static HTML reports/previews | Нет | Да | отсутствует |
| HTTP API | Будущее | Не найден | Нет | Да | отсутствует |
| Publishing/upload | Будущее | Metadata/export files only | Нет | Да | отсутствует |

## 4. Самостоятельные направления проекта

### News-to-short

Главная новая архитектурная попытка. Находится в `src/news`, запускается через `pipeline.py --news-to-short` или `apps/news_to_short`. Имеет staged project store, localizations, manifests, safe voice workflow, final renderer. Главный разрыв: stock candidates не превращаются в скачанные локальные файлы внутри main pipeline.

### Старый documentary/quote pipeline

Находится вокруг `pipeline.py`, `src/config_loader.py`, `src/channel_loader.py`, `src/scene_planner.py`, `src/asset_finder.py`, `src/video_asset_engine.py`, `src/video_renderer.py`, `src/voice_engine.py`. Он ближе к end-to-end render, но смешивает старые и новые подходы, имеет слабое licensing/provenance и много project/channel assumptions.

### Production plan / solar_vs_nuclear

`src/production_plan/youtube_shorts.py` создаёт фиксированный проект `project_solar_vs_nuclear`. `src/production_plan/solar_vs_nuclear_render.py` рендерит его. Это не универсальная система, а отдельный product experiment.

### Anime Factory

Отдельная CLI-система в `anime_factory/`: анализ локального episode video, transcribe, scene detection, candidate selection, previews, render clips, subtitles. Не связана со stock providers и news pipeline.

### Size comparison

Специализированный pipeline для cinematic size comparison в `src/size_comparison_engine.py`, с каналом `channels/size_comparison` и content files.

### Legacy

`legacy/` содержит старые OpenAI/scene/download/render scripts. Часть идей пересекается с текущими pipeline, но они не являются основным entrypoint.

## 5. Точки входа и CLI

| Entry point | Назначение | Пример команды | Состояние |
|---|---|---|---|
| `pipeline.py` | общий CLI-dispatcher | `python pipeline.py --news-to-short --topic "..."`
| `apps/news_to_short/main.py` | app wrapper для news | `python -m apps.news_to_short ...` | работает частично |
| `apps/youtube_pipeline/main.py` | wrapper старого pipeline | `python -m apps.youtube_pipeline ...` | legacy wrapper |
| `apps/anime_factory/main.py` | wrapper anime | `python -m apps.anime_factory ...` | experiment |
| `anime_factory/pipeline.py` | прямой anime CLI | `python anime_factory/pipeline.py --input episode.mp4 --episode e01` | experiment |
| `legacy/main.py` | старый OpenAI scene script | `python legacy/main.py` | legacy |
| `legacy/download_broll.py` | старый Pexels downloader | `python legacy/download_broll.py` | legacy |

Основные группы аргументов `pipeline.py`:

- global config: `--config`, `--channel`, `--video`, `--dev`, `--prod`, `--prod-preview`, `--cinematic-preview`;
- old pipeline utilities: `--skip-render`, `--find-music`, `--refresh-assets`, `--index-assets`, `--clean-temp`, `--asset-report`;
- news: `--news-to-short`, `--topic`, `--url`, `--text`, `--language`, `--target-duration`, `--project-id`, `--stage`, `--until-stage`, `--resume`, `--force-stage`, `--dry-run`;
- voice: `--voice-action`, `--voice-project`, `--voice-language`, `--voice-provider`, `--voice-file`, `--voice-approve`, `--voice-sample-text`;
- production plan: `--production-plan`, `--render-production-plan`.

## 6. Верхнеуровневые папки

| Путь | Тип | Назначение | Состояние |
|---|---|---|---|
| `.git` | repo metadata | Git internals | не читалась глубоко |
| `src` | исходный код | основная библиотека pipeline | active + mixed legacy |
| `src/news` | исходный код | новый news-to-short | active/prototype |
| `src/assets` | исходный код | semantic asset selection | prototype |
| `src/providers` | исходный код | API provider wrappers | prototype |
| `src/audio` | исходный код | safe voice workflow | active/prototype |
| `src/production_plan` | исходный код | solar_vs_nuclear plan/render | experiment |
| `apps` | wrappers | app entry wrappers | active/prototype |
| `anime_factory` | отдельное app | anime clip workflow | experiment |
| `channels` | конфигурация | channel configs/voices | active |
| `config` | конфигурация | global video style | active |
| `content` | данные | сценарии/channel content | active |
| `projects` | данные проектов | news-to-short outputs/manifests | generated data |
| `project_solar_vs_nuclear` | данные проекта | fixed project manifests/assets/render | experiment data |
| `assets` | media/data/cache | media library, generated/downloaded assets | mixed data/cache |
| `manual_assets` | data | manually supplied assets | active/manual |
| `music` | data | local music | active/prototype |
| `outputs` | generated output | old pipeline outputs/audio edits | generated |
| `subtitles` | data/output | empty top-level folder | unused |
| `legacy` | legacy code | старые scripts | legacy |
| `docs` | документация | app/architecture docs | useful but partial |
| `tests` | tests | static unittest files | not run |
| `scripts` | utilities | MOSS tests/scripts | support |
| `MOSS_TTS_Nano` | external/local model | local TTS repo/env | external heavy |
| `venv` | environment | virtual environment | excluded |
| `packages` | package marker | app packaging/docs placeholder | prototype |

## 7. Внешние сервисы

| Сервис | Где используется | Назначение | Статус |
|---|---|---|---|
| ElevenLabs | `src/audio/elevenlabs_provider.py`, `src/voice_engine.py`, `src/production_plan/solar_vs_nuclear_render.py` | TTS | active, paid-risk |
| OpenAI | `legacy/*.py`, dependency/config key | legacy LLM scene generation | legacy/not main |
| Pexels | `src/providers/pexels_provider.py`, `src/news/*`, `src/video_asset_engine.py`, `legacy/download_broll.py` | video/image stock | active/duplicated |
| Pixabay | `src/providers/pixabay_provider.py`, `src/news/*`, `src/video_asset_engine.py`, `src/music_engine.py` | video/image/music stock | active/duplicated |
| Unsplash | `src/providers/unsplash_provider.py`, `src/news/asset_manager.py` | image stock | prototype |
| Wikimedia Commons | docs/future only | future source | absent |
| NASA Image and Video Library | docs/future only | future source | absent |
| Internet Archive | docs/future only | future source | absent |
| Envato Elements | docs/future/manual idea | future manual source | absent |

## 8. Типы входных и выходных данных

Входы:

- URL, text, topic для news;
- channel/video config для old pipeline;
- local user assets;
- manual WAV;
- local episode video для anime;
- CSV/content configs для size comparison;
- API keys через env.

Выходы:

- `job.json`, `input.json`, `article.json`, `claims.json`;
- `script.json`, `narration.txt`;
- `master_visual_plan.json`;
- `assets_manifest.json`, `missing_assets.json`;
- voice manifests/audio files;
- `.srt`, `.ass`, subtitle manifests;
- render manifests and `.mp4`;
- export manifests, YouTube metadata JSON;
- static preview/report HTML in some flows;
- media library index.

## 9. Конфигурации

| Файл/папка | Назначение | Наблюдение |
|---|---|---|
| `.env` | реальные секреты | значения не читались/не раскрывались |
| `.env.example` | список переменных | содержит names for OpenAI, ElevenLabs, Pexels, Pixabay, Unsplash |
| `requirements.txt` | Python deps | MoviePy, FFmpeg wrapper, OpenAI, requests, PyYAML, ElevenLabs |
| `config/video_style.json` | global old pipeline style | production/dev presets |
| `channels/*/channel_config.json` | channel configs | несколько продуктовых направлений |
| `channels/nature_science_news_ru/voices.yaml` | voice profiles | language/voice config |
| `anime_factory/config.yaml` | anime defaults | отдельный config |
| `project_solar_vs_nuclear/project_config.json` | fixed project config | project-specific |

Env variable names found:

- `ELEVENLABS_API_KEY`
- `ELEVENLABS_VOICE_ID`
- `OPENAI_API_KEY`
- `PEXELS_API_KEY`
- `PIXABAY_API_KEY`
- `UNSPLASH_ACCESS_KEY`

## 10. Форматы проектов

### News projects

Фактическая структура:

```text
projects/<project_id>/
  job.json
  input/input.json
  article/article.json
  article/images.json
  research/claims.json
  master/sources.json
  master/master_visual_plan.json
  assets/assets_manifest.json
  assets/missing_assets.json
  localizations/<language>/
    script/script.json
    script/narration.txt
    visual/visual_plan.json
    voice/voice_manifest.json
    subtitles/subtitles.srt
    subtitles/subtitles.ass
    output/
```

### Old outputs

```text
outputs/<channel>/<video>/
  scene_plan.json
  youtube_metadata.json
  asset_plan.json
  render_plan.json
  final_preview.mp4 / final_video.mp4
```

### Solar project

```text
project_solar_vs_nuclear/
  project_config.json
  render_readiness.json
  01_script/
  02_voice/
  03_stock/
  04_motion/
  05_project/
  06_analytics/
```

### Anime Factory

```text
anime_factory/
  projects/<episode_id>/
    audio/
    transcripts/
    scenes/
    candidates/
    previews/
    renders/
    reports/
```

## 11. Языки и видеоформаты

Языки:

- `ru`, `en`, `es` заложены в `NewsProjectStore` localizations;
- фактическая генерация в основном работает по выбранному language, но translation/adaptation flow не найден;
- voice profiles существуют минимум для `nature_science_news_ru`;
- old pipeline channel configs русскоязычные и нишевые.

Видеоформаты:

- news final renderer: 1080x1920 vertical, 30 fps, MP4/H.264/AAC;
- old renderer: configurable, часто vertical Shorts;
- size comparison: cinematic-size-comparison-specific;
- anime: clip renders with crop modes;
- explicit platform variants для YouTube Shorts/Reels/TikTok частично копируются/exported, но platform-specific encoding/upload отсутствует.

## 12. Production, prototype, experiment, legacy

| Подсистема | Назначение | Главные файлы | Реально используется | Состояние |
|---|---|---|---:|---|
| News project store | staged project data | `src/news/project_store.py` | Да | работает частично |
| News pipeline | URL/text/topic to staged output | `src/news/pipeline.py` | Да | работает частично |
| News asset manager | candidate selection | `src/news/asset_manager.py` | Да | прототип |
| Semantic selection | better visual relevance | `src/assets/semantic_selection/*` | Да | прототип |
| Safe voice workflow | approval/manual voice | `src/audio/*`, `src/news/voice_stage.py` | Да | работает частично |
| News final render | vertical final render | `src/news/final_renderer.py` | Да | работает частично |
| Old pipeline | documentary/quotes | `pipeline.py`, `src/video_renderer.py` | Да | legacy/prototype |
| Media library | asset index/cache | `src/media_library.py` | Да | работает частично |
| Production plan | solar project | `src/production_plan/*` | Да | experiment |
| Anime Factory | local video clip automation | `anime_factory/*` | Да | experiment |
| Legacy OpenAI scripts | scene/script generation | `legacy/*` | Нет в main | legacy |
| UI/API | product management | не найдено | Нет | отсутствует |
| Publishing | upload to platforms | не найдено | Нет | отсутствует |

## 13. Текущий уровень готовности

Для личного использования владельцем проект полезен как набор CLI-инструментов и прототипов. Для закрытой беты нужен один стабильный end-to-end pipeline, unified assets/licenses, fake providers, безопасный paid-call gate и UI/review layer. Для коммерческого продукта текущая готовность низкая из-за лицензий, секретов, отсутствия user isolation, CI/CD, observability, packaging и устойчивого UX.

