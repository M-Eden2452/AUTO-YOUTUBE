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

# PROJECT AUDIT COMPONENTS

## 1. Summary table

| Компонент | Состояние | Работает | Частично | Отсутствует | Критичность | Следующий шаг |
|---|---|---|---|---|---|---|
| Input | работает частично | URL/text/topic/channel configs/local video | unified validation | product UI | High | typed input schema |
| Article ingestion | работает частично | requests + simple HTML parse | robust extraction/source tracking | paywall/JS parsing | Medium | extractor abstraction |
| Research | прототип | heuristic claims | classification only | fact checking | High | source-backed claims schema |
| Fact checking | отсутствует | none in main | legacy source hints | verification engine | High | define verification stage |
| Script generation | прототип | deterministic script/scenes | limited templates | LLM adaptation | High | stable script schema/tests |
| Scene planning | работает частично | scenes/timing | schemas differ | audio-based scene sync | High | one Scene model |
| Visual planning | прототип | visual descriptions | whale/nature bias | universal planning | High | generic visual schema |
| Semantic selection | прототип | metadata ranking | precomputed tags only | vision/frame analysis | High | preview-based validation |
| Query generation | прототип | multiple semantic queries | limited synonyms | LLM query expansion | Medium | provider-neutral query object |
| Pexels | работает частично | official API search/download in places | no unified flow | license snapshot | High | provider contract |
| Pixabay | работает частично | official API search/download/music in places | no unified flow | license snapshot | High | provider contract |
| Unsplash | прототип | official image search | weak integration | video/download/render | Medium | decide role |
| Manual assets | работает частично | user assets allowed | no UI | rights declaration UX | High | manual provider |
| Local library | работает частично | index/search/dedupe | weak metadata | rights status/checksum | High | migrate schema |
| Asset download | работает частично | multiple implementations | news gap | unified retries | Critical | one downloader service |
| License tracking | требует исправления | some provider/source fields | inconsistent | proof-grade provenance | Critical | AssetLicense schema |
| Voice | работает частично | safe workflow exists | multiple flows | unified voice engine | High | consolidate around `src/audio` |
| ElevenLabs | работает частично | preflight/synthesize | no retry; uneven approval | global cost policy | High | paid-call gate |
| Manual WAV | работает частично | import/inspect | UX incomplete | waveform review | Medium | formal manual audio stage |
| MOSS | эксперимент | local provider wrapper | external env required | main integration | Low | keep isolated |
| Subtitles | работает частично | SRT/ASS | heuristic timings | word alignment | Medium | align with audio |
| Music | прототип | old Pixabay/local music | not news stage | license/mix policy | Medium | news music stage |
| SFX | отсутствует | none found | none | SFX generation/library | Low | defer |
| Rendering | работает частично | FFmpeg/MoviePy outputs | several renderers | unified render service | High | renderer contract |
| FFmpeg | работает частично | encoding/validation | escaping varies | centralized diagnostics | High | shared FFmpeg helper |
| MoviePy | работает частично | old render/mix helpers | version-risk | unified usage | Medium | isolate usage |
| Localization | прототип | ru/en/es folders | single-lang actual flow | translation/adaptation | Medium | localization model |
| Export | работает частично | MP4/manifests/copies | no upload | publishing APIs | Medium | export manifest schema |
| Metadata | работает частично | YouTube metadata JSON | sources incomplete | attribution list | High | provenance-driven metadata |
| UI | отсутствует | static previews only | none | app/web UI | High | after pipeline stable |
| CLI | работает частично | many commands | overloaded dispatcher | discoverability | Medium | split commands |
| HTTP API | отсутствует | none | none | server/API | Low now | defer |
| Publishing | отсутствует | metadata only | none | YouTube/TikTok/Reels upload | Low now | defer |
| Analytics | прототип/отсутствует | solar analytics folder | no runtime analytics | product analytics | Low | defer |
| Project storage | работает частично | staged JSON | no version/atomic writes | migrations | Critical | schemas/versioning |
| Configuration | работает частично | env/json/yaml | scattered constants | typed config | High | config registry |
| Logging | прототип | prints/log files in places | inconsistent | observability | Medium | structured logs |
| Cleanup | работает частично | media cleanup utility | not universal | lifecycle policy | Medium | temp/cache policy |
| Resume | работает частично | news stage resume | no idempotency locks | robust recovery | High | resumable stages |
| Error handling | требует исправления | some timeouts/quality gates | broad exceptions | retry taxonomy | Critical | error policy |

## 2. Input

Главные файлы: `pipeline.py`, `src/news/models.py`, `src/news/pipeline.py`, `src/channel_loader.py`, `anime_factory/pipeline.py`.

Входы существуют для:

- news: topic/url/text;
- old: channel/video config;
- voice: project/language/provider/manual audio file;
- production plan: hardcoded project name;
- anime: local input video;
- size comparison: config/content CSV.

Риск: нет единого input schema and validation layer. Пользовательский продукт пока должен знать CLI and file layout.

## 3. Article ingestion

Главные файлы:

- `src/news/article_ingestor.py`
- `src/news/article_parser.py`

`ingest_article()` uses URL/text/topic and writes article data. URL path uses `requests.get(..., timeout=20)` and simple parsing. Article image extraction marks images as reference-only/unknown rights.

Ограничения: нет JS rendering, no source credibility scoring, no robust metadata extraction, no fact verification.

## 4. Research and fact checking

Главные файлы:

- `src/news/research_engine.py`
- legacy LLM: `legacy/main.py`, `legacy/scene_planner.py`, `legacy/scene_plan_json.py`

Main news research is deterministic/heuristic. OpenAI LLM calls exist only in legacy scripts through `client.responses.create`, not in main news pipeline.

Fact checking as отдельная подтверждённая стадия отсутствует.

## 5. Script generation and scenes

Главные файлы:

- `src/news/script_generator.py`
- `src/news/models.py`
- `src/scene_planner.py`
- `src/quote_generator.py`

News script generator creates deterministic Shorts structure, narration and scenes. Old pipeline creates scene plans from channel/video configs and quote/documentary data.

Проблема: scenes in news, old pipeline, production plan and anime have different schemas.

## 6. Visual planning and semantic selection

Главные файлы:

- `src/news/visual_plan.py`
- `src/assets/semantic_selection/models.py`
- `src/assets/semantic_selection/scene_analyzer.py`
- `src/assets/semantic_selection/query_generator.py`
- `src/assets/semantic_selection/candidate_ranker.py`
- `src/assets/semantic_selection/vision_validator.py`

Факты:

- subject/action/environment/location/camera/mood/must_include/must_not_include exist;
- multiple queries are generated;
- ranking uses metadata/title/tags/quality/orientation/duplicates/rights;
- `vision_validator.py` only consumes precomputed tags and does not call paid vision API;
- no frame sampling or preview analysis is called.

Риск: heuristics are heavily nature/whale/ocean/research oriented and can select semantically wrong visuals for other topics.

## 7. Providers

### Pexels

Files:

- `src/providers/pexels_provider.py`
- `src/news/asset_manager.py`
- `src/news/stock_video_downloader.py`
- `src/video_asset_engine.py`
- `legacy/download_broll.py`
- `src/production_plan/solar_vs_nuclear_render.py`

Uses official API. Search supports query, per_page/limit, orientation in some wrappers, type video/image. Downloads are implemented in several places. Retry/backoff absent. Metadata and license fields differ by implementation.

### Pixabay

Files:

- `src/providers/pixabay_provider.py`
- `src/news/asset_manager.py`
- `src/news/stock_video_downloader.py`
- `src/video_asset_engine.py`
- `src/music_engine.py`
- `src/production_plan/solar_vs_nuclear_render.py`

Uses official API for video/image/music. Supports safesearch, video_type, orientation in wrapper. Download paths and metadata differ. No unified license capture.

### Unsplash

Files:

- `src/providers/unsplash_provider.py`
- `src/news/asset_manager.py`

Official API image search. No strong download/render integration found.

### Manual assets

Manual/user assets appear in news models and asset manager as user-owned renderable assets. There is no UI or formal rights declaration workflow.

### Local library

File: `src/media_library.py`; index: `assets/library/metadata/media_index.json`.

Stats observed:

- records: 64;
- providers: local 5, pexels 50, pixabay 9;
- types: video 63, music 1;
- without source URL: 1;
- without download URL: 1;
- without author: 64;
- without rights_status: 64;
- without local_path: 0;
- missing local files: 0.

## 8. Asset download

Main implementations:

- `src/news/stock_video_downloader.py`;
- `src/video_asset_engine.py`;
- `src/asset_finder.py`;
- `src/production_plan/solar_vs_nuclear_render.py`;
- `legacy/download_broll.py`;
- `src/music_engine.py`.

Validation:

- old video engine uses FFmpeg/thumbnail validation;
- news standalone downloader checks file existence/size but is not pipeline-connected;
- no checksum, no partial resume, no central duplicate policy.

Critical gap: news search manifest can select an asset that renderer cannot use because no local file path exists.

## 9. License tracking

Fields appear inconsistently:

- provider;
- source_url;
- download_url;
- license/license_note;
- rights_status in some news/article paths;
- allowed_for_render in some paths;
- attribution in some paths.

Missing as required normalized fields:

- author in media library;
- license_url;
- attribution_required;
- commercial_use_allowed;
- modification_allowed;
- download_date as legal event;
- checksum;
- source page snapshot/license snapshot;
- project_id/scene_id binding for each downloaded asset.

Conclusion: not commercial-safe.

## 10. Voice, ElevenLabs, manual WAV, MOSS

Files:

- `src/audio/base_provider.py`
- `src/audio/elevenlabs_provider.py`
- `src/audio/provider_manager.py`
- `src/audio/voice_workflow.py`
- `src/audio/audio_file_provider.py`
- `src/audio/voice_cli.py`
- `src/news/voice_stage.py`
- `src/voice_engine.py`
- `src/tts_providers/moss_tts_provider.py`
- `src/production_plan/solar_vs_nuclear_render.py`

What works:

- provider abstraction exists for safe workflow;
- ElevenLabs preflight and synthesize exist;
- manual WAV import exists;
- MOSS provider wrapper exists as experimental local subprocess.

Risks:

- no retry/backoff;
- 401/429 not modeled as separate actionable error types everywhere;
- old/solar paths bypass safe approval;
- voice_id/model config scattered.

## 11. Subtitles

Files:

- `src/news/subtitles.py`
- `anime_factory/modules/subtitles.py`
- `src/production_plan/solar_vs_nuclear_render.py`

News creates SRT and ASS from scene timings and word chunks. No forced alignment with audio waveform. Unicode/ASS escaping is partly handled but not a centralized subtitle engine.

## 12. Music and SFX

Files:

- `src/music_engine.py`
- `src/music_tools.py`
- `src/news/final_renderer.py`

Music exists mainly in old pipeline and Pixabay music engine. News final renderer can use a music manifest if present, but no news music stage was found. SFX stage/provider not found.

## 13. Rendering

Files:

- `src/news/final_renderer.py`
- `src/news/preview_renderer.py`
- `src/video_renderer.py`
- `src/production_plan/solar_vs_nuclear_render.py`
- `anime_factory/modules/render_clips.py`

FFmpeg is the main reliable render tool. MoviePy is used in old helper paths. News final output is vertical 1080x1920. Cropping is mostly center crop/scale. Anime has dynamic/smart/static/blur crop modes.

Missing:

- unified render model;
- smart crop for stock/news;
- transition system;
- interrupted render resume;
- corrupted output detection beyond basic probes.

## 14. UI, CLI, API

No real UI/web server/HTTP API/desktop app found. There are app wrappers and static HTML previews/reports, but no screen for replacing scene material, previewing candidates, choosing alternatives, manual upload, cancellation, progress or user-friendly errors.

CLI is powerful but overloaded in `pipeline.py`.

## 15. Export and publishing

Export exists as MP4/manifests and metadata files. Upload to YouTube/TikTok/Reels not found. Sources/attribution list for YouTube description is not reliably generated from complete provenance.

## 16. Configuration and secrets

Secret variable names are used; values were not exposed:

- `ELEVENLABS_API_KEY`
- `ELEVENLABS_VOICE_ID`
- `OPENAI_API_KEY`
- `PEXELS_API_KEY`
- `PIXABAY_API_KEY`
- `UNSPLASH_ACCESS_KEY`

No hardcoded secret values were intentionally included in this audit. Config is spread across JSON/YAML/env/CLI/hardcoded constants.

## 17. Logging, cleanup, resume, errors

Logging is mostly prints and manifests. Cleanup exists in media library utilities and some temporary render paths, but not as global lifecycle. Resume exists mainly in news by stage, but without locks/atomic writes/idempotency proof.

