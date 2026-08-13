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

# PROJECT AUDIT PIPELINES

## 1. Общая таблица

| Pipeline | Начинается | Заканчивается | End-to-end | Ручные шаги | Критический разрыв | Состояние |
|---|---|---|---:|---|---|---|
| News-to-short | `pipeline.py --news-to-short`, `python -m apps.news_to_short` | export/final render | Нет стабильно | voice approval/manual WAV, review | asset search не скачивает selected assets | работает частично |
| Old documentary/quote | `pipeline.py --channel --video` | `outputs/.../final_video.mp4` | Частично | подготовка configs/content | mixed schemas/licensing | legacy/prototype |
| Production plan generator | `pipeline.py --production-plan solar_vs_nuclear` | project manifests/readiness | Да как генератор | review/asset replacement | fixed project only | experiment |
| Solar render | `pipeline.py --render-production-plan project_solar_vs_nuclear` | `05_project/final_vertical.mp4` | Условно | final WAV or paid TTS | paid TTS bypasses safe approval | experiment |
| Anime Factory | `anime_factory/pipeline.py` | clips/previews/report | Частично | local episode/manual selection | separate product, copyright/licensing outside system | experiment |
| Size comparison | `pipeline.py` with size config | comparison render | Частично | CSV/content config | specialized engine | experiment |
| Voice workflow | `pipeline.py --voice-action ...` | voice manifests/audio | Частично | approve/import | not unified across all renderers | работает частично |
| Stock downloader workflows | standalone functions/scripts | local stock files/library | Частично | manual invocation | not connected to news asset stage | prototype/legacy |
| Legacy OpenAI/b-roll | `legacy/*.py` | old JSON/assets | Нет as main | manual | not connected to current pipeline | legacy |

## 2. News-to-short

### Назначение

Создать короткое news/science video из URL, текста или темы, с project manifests, сценарием, визуальным планом, ассетами, voice, subtitles, preview/final render и export.

### Entry point

- `pipeline.py::main()` branch `args.news_to_short`
- `src/news/pipeline.py::run_news_to_short_cli()`
- wrappers: `apps/news_to_short/main.py`, `apps/news_to_short/__main__.py`

### CLI

```text
python pipeline.py --news-to-short --topic "..." --language ru --target-duration 45
python pipeline.py --news-to-short --url "https://..." --until-stage asset_search
python -m apps.news_to_short --topic "..."
```

### Вход

- `--topic`, `--url`, `--text`;
- `--language`;
- `--target-duration`;
- optional `--project-id`, `--resume`, `--stage`, `--until-stage`, `--force-stage`, `--dry-run`;
- `--user-assets` exists in model/path logic but is not a full UI workflow.

### Стадии

Defined in `src/news/pipeline.py` as:

```text
input -> article_ingestion -> research -> script -> visual_plan -> asset_search -> voice -> subtitles -> preview_render -> quality_check -> final_render -> export
```

### Последовательность функций

```text
run_news_to_short_cli
  parse args
  NewsProjectStore.create_project/load_project
  run_news_to_short_job
    _dispatch_stage(input)
    ingest_article
    build_research
    build_script
    build_visual_plan
    build_asset_search_manifest
      build_news_asset_manifest
      semantic_selection.analyze_scene_semantics
      generate_search_queries
      provider.search
      rank_candidates
    build_safe_voice_manifest
    build_subtitles
    render_preview
    run_quality_check
    render_final_video
    export_localization
```

### Создаваемые файлы

```text
projects/<project_id>/job.json
projects/<project_id>/input/input.json
projects/<project_id>/article/article.json
projects/<project_id>/article/images.json
projects/<project_id>/research/claims.json
projects/<project_id>/localizations/<lang>/script/script.json
projects/<project_id>/localizations/<lang>/script/narration.txt
projects/<project_id>/master/master_visual_plan.json
projects/<project_id>/localizations/<lang>/visual/visual_plan.json
projects/<project_id>/assets/assets_manifest.json
projects/<project_id>/assets/missing_assets.json
projects/<project_id>/localizations/<lang>/voice/voice_manifest.json
projects/<project_id>/localizations/<lang>/subtitles/subtitles.srt
projects/<project_id>/localizations/<lang>/subtitles/subtitles.ass
projects/<project_id>/render/final_render_manifest.json
projects/<project_id>/export/export_manifest.json
```

### Состояние

Работает частично. Хорошо структурирован staged project store и manifests. Но end-to-end до финального видео не стабилен из-за asset download gap и voice approval/manual WAV gate.

### Ручные шаги

- manual WAV import or explicit voice approval;
- scene/asset review currently mostly through files/manifests;
- manual user assets possible but not productized.

### Платные шаги

- ElevenLabs потенциально, но `src/news/voice_stage.py` uses safe manifest and blocks unapproved paid TTS.
- Pexels/Pixabay/Unsplash search uses free/API-key calls but still external quota.

### Ошибки и retry

- API timeouts exist;
- no unified retries/backoff;
- asset errors often degrade to missing assets;
- final render raises when local files are missing.

### Resume/idempotency

`--resume`, `--stage`, `--until-stage`, `--force-stage` exist. State is JSON-based. No atomic writes, locks, migrations or complete idempotency guarantees.

### Финальный результат

Target final output: `localizations/<lang>/output/master_1080x1920.mp4` plus platform copies/export manifest. In practice blocked unless local assets and completed voice exist.

### Где цепочка разрывается

`asset_manager` produces selected metadata. `final_renderer` expects local renderable file paths. `stock_video_downloader` can download, but is not invoked by main news stage.

### Может ли пройти end-to-end

Да только при удачной ручной подготовке renderable assets and voice. Автоматически от URL/topic до готового MP4 в текущем коде не является надёжным.

### Дублирование

Дублирует provider/download logic with `src/video_asset_engine.py`, `src/asset_finder.py`, `src/news/stock_video_downloader.py`, `src/production_plan/solar_vs_nuclear_render.py`.

### Классификация

Основной будущий pipeline, но сейчас `работает частично`.

## 3. Старый documentary/quote pipeline

### Назначение

Создавать scripted documentary/quote/short video по channel/video configs.

### Entry point

- `pipeline.py::main()` default branch
- wrapper: `apps/youtube_pipeline/main.py`

### CLI

```text
python pipeline.py --channel nature_science_news_ru --video <video_id>
python pipeline.py --channel quotes --video <video_id> --skip-render
python -m apps.youtube_pipeline --channel ... --video ...
```

### Вход

- `config/video_style.json`;
- `channels/<channel>/channel_config.json`;
- `content/<channel>/<video>.json` or folder content;
- optional env API keys;
- local/manual assets.

### Стадии и функции

```text
pipeline.main
  load_config
  load_channel_video_config
  build_quote_plan
  write_youtube_metadata
  build_scene_plan
  build_voice_manifest
  align_scene_timings_with_voice
  build_intro_plan
  find_music_track / build_music_manifest
  build_asset_plan
    build_documentary_asset_plan
      search/download stock
      register_asset
  build_render_plan
  render_video
  evaluate_output
  export_obsidian_note
```

### Создаваемые файлы

- `outputs/<channel>/<video>/scene_plan.json`;
- `outputs/<channel>/<video>/voice_manifest.json`;
- `outputs/<channel>/<video>/asset_plan.json`;
- `outputs/<channel>/<video>/render_plan.json`;
- `outputs/<channel>/<video>/final_preview.mp4` or `final_video.mp4`;
- YouTube metadata and optional Obsidian notes.

### Состояние

Более цельный render path, чем news, но архитектурно старый и смешанный: old channel configs, documentary-specific asset engine, weak licenses.

### Ручные шаги

Нужно заранее подготовить channel/video content, potentially API keys and voice settings.

### Платные шаги

`src/voice_engine.py` may call ElevenLabs depending on provider/settings. Pexels/Pixabay requests/downloads possible. OpenAI not in this main branch unless legacy scripts invoked separately.

### Ошибки/retry/resume

Есть local cache/media library and some validation, but no full stage resume, atomic manifests, unified retry.

### End-to-end

Условно может пройти при корректной конфигурации и доступных assets/voice. Для коммерческого продукта не стоит расширять напрямую без выделения shared modules.

### Классификация

`legacy/prototype`, useful source of working render/download patterns.

## 4. Production plan generator

### Назначение

Создать structured production plan для fixed YouTube Shorts проекта `solar_vs_nuclear`.

### Entry point

- `pipeline.py --production-plan solar_vs_nuclear`
- `src/production_plan/youtube_shorts.py::create_solar_vs_nuclear_plan`

### Вход

Hardcoded project narrative/config in code.

### Стадии

Creates:

- folder skeleton;
- script text;
- scene specs;
- project config;
- render readiness;
- preview/report.

### Создаваемые файлы

```text
project_solar_vs_nuclear/project_config.json
project_solar_vs_nuclear/render_readiness.json
project_solar_vs_nuclear/01_script/*
project_solar_vs_nuclear/02_voice/*
project_solar_vs_nuclear/03_stock/*
project_solar_vs_nuclear/04_motion/*
project_solar_vs_nuclear/05_project/*
project_solar_vs_nuclear/06_analytics/*
```

### Состояние

Experiment. Useful as production-planning prototype, not a generic pipeline.

### End-to-end

Generator itself can complete. Full video requires render flow and assets/voice.

## 5. Solar render pipeline

### Назначение

Render fixed `project_solar_vs_nuclear` vertical video with stock, subtitles and voice.

### Entry point

- `pipeline.py --render-production-plan project_solar_vs_nuclear`
- `src/production_plan/solar_vs_nuclear_render.py::build_solar_vs_nuclear_video`

### Последовательность функций

```text
build_solar_vs_nuclear_video
  ensure_project
  load/read project config
  ensure_final_voice
  select_and_download_stock
    search_pexels/search_pixabay
    download clip
  check_render_readiness
  render_final_video
  write render_manifest
```

### Платные шаги

`ensure_final_voice()` can call ElevenLabs if final voice file is missing. This bypasses the safer `src/audio` approval flow.

### Состояние

Experiment. It has concrete outputs and manifests, but is tightly coupled to one project and hardcoded categories.

### Разрывы

- project-specific paths and semantics;
- silent provider failures;
- weak license/provenance;
- paid TTS risk.

## 6. Anime Factory

### Назначение

Отдельная система для локального анализа anime episode video: extract audio, transcribe, detect scenes, score candidates, generate previews, render selected clips/subtitles.

### Entry point

- `anime_factory/pipeline.py::main()`
- wrapper `apps/anime_factory/main.py`

### CLI

```text
python anime_factory/pipeline.py --input episode.mp4 --episode episode_01
python -m apps.anime_factory --input episode.mp4 --episode episode_01
```

### Стадии

```text
paths -> extract_audio -> transcribe/reuse transcript -> analyze_audio
-> detect_scenes -> score_candidates -> refine_boundaries
-> select candidates -> preview/report or render clips -> subtitles
```

### Создаваемые файлы

`anime_factory/projects/<episode>/...` folders for audio, transcripts, candidates, previews, renders, reports.

### Состояние

Experiment. Технически отдельный продукт. Не связан с stock provider/license architecture. Для коммерческого использования есть отдельные copyright concerns, так как источник - локальный episode media.

## 7. Size comparison pipeline

### Назначение

Создание cinematic size comparison video из CSV/content data.

### Entry point

Triggered in `pipeline.py` when loaded config has:

```text
video_type == "cinematic_size_comparison"
```

### Главные файлы

- `src/size_comparison_engine.py`
- `channels/size_comparison/channel_config.json`
- `content/size_comparison/*`

### Стадии

Load entities -> build camera plan -> generate/find assets -> render size comparison -> export optional notes.

### Состояние

Experiment/specialized.

## 8. Voice workflow

### Назначение

Управлять voice profiles, preflight, paid approval, audition, manual audio import.

### Entry point

`pipeline.py --voice-action <list|inspect|preflight|import-audio|approve|audition>`

### Главные файлы

- `src/audio/voice_cli.py`
- `src/audio/voice_workflow.py`
- `src/audio/provider_manager.py`
- `src/audio/elevenlabs_provider.py`
- `src/audio/audio_file_provider.py`
- `src/news/voice_stage.py`

### Состояние

Работает частично и является лучшей основой для будущего unified voice architecture. Не заменяет пока old and solar voice flows.

## 9. Stock downloader workflows

### News stock downloader

File: `src/news/stock_video_downloader.py`

Searches/downloads Pexels/Pixabay video into `assets/stock_videos`. Not connected to `src/news/pipeline.py`.

### Old documentary video engine

File: `src/video_asset_engine.py`

Searches/downloads Pexels/Pixabay videos, validates with FFmpeg, registers in media library.

### Old image finder

File: `src/asset_finder.py`

Downloads or generates image placeholders. Delegates to video engine for documentary video tasks.

### Solar downloader

File: `src/production_plan/solar_vs_nuclear_render.py`

Project-specific Pexels/Pixabay stock search/download.

### Legacy b-roll

File: `legacy/download_broll.py`

Old Pexels-only downloader.

## 10. Legacy pipelines

Files in `legacy/` include OpenAI scene generation, b-roll download, assembly/render helpers. These are not connected to the current root dispatcher except as standalone manual scripts.

