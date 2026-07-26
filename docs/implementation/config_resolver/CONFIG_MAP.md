# Карта конфигурации проекта AI-YouTube

Снята по коду на коммите `66b2e13` (Q2) перед реализацией этапа D1.
Формат каждой строки: **настройка → возможные источники → текущий приоритет → потребители**.

Всё, что здесь написано, проверено поиском по репозиторию. Строка
«не читается никем» означает, что поиск по `src/` и `pipeline.py` не нашёл ни одного
чтения — а не что настройка «наверное, где-то используется».

---

## 1. Где вообще лежит конфигурация

| Носитель | Что в нём | Кто читает |
|---|---|---|
| `channels/<id>/channel_config.json` | язык, длительности, разрешение, fps, `voice`, `voice_workflow`, `localization`, `languages`, `content`, `assets`, `asset_selection`, `approval`, `subtitles`, `music` | `src/news/pipeline.py` (`_load_channel_config`: только `voice`, `voice_workflow`, `asset_selection`), `src/channel_loader.py` (legacy: `channel_name`, `video_format`, `default_language`, `obsidian_folder`), `src/content_creation/capabilities.py` (только `mode` и наличие блока `voice` — для классификации канала в `_classify_channel_config`) |
| `channels/<id>/channel.json` | `ChannelProfile`: `default_language`, `supported_languages`, `default_*`, `export_targets`, `branding`, `output_policy` | `src/project_foundation/channels.py` → `src/content_creation/{capabilities,service}.py` |
| `channels/<id>/voices.yaml` | голосовые профили | `src/audio/voice_profile_registry.py` через `src/news/voice_adapter.py` |
| `channels/<id>/style.json`, `subtitle_style.json` | стиль legacy-пайплайна | только `src/channel_loader.py`; `src/news/subtitles.py` их не открывает |
| `src/production_catalog/catalog.py` | Application / Format / Template + `*_policy_id` | `src/content_creation/*`, `src/production_catalog/cli.py` |
| `src/audio/voice_policy.py` `AUDIO_POLICY_DEFAULTS` | политика звука по `template.audio_policy_id` | `src/news/voice_adapter.py`, `src/content_creation/capabilities.py` |
| `config/video_style.json` + `src/config_loader.py` | legacy render config (dev/prod/preview) | `pipeline.py` legacy-режим |
| `config/render_presets/story_card_short_v1.json` | разрешение, fps, layout карточки | `src/production_plan/story_card_short_render.py`, `src/templates/story_card/integration.py` |
| `config/{semantic_visual,visual_preview,license_policy}.json` | semantic/preview/лицензии | соответствующие модули `src/assets/` |
| `projects/<id>/job.json` | `NewsJob`: язык, длительность, разрешение, aspect_ratio, стадии | `src/news/pipeline.py`, `src/projects/repository.py` |
| `projects/<id>/project.json` | `ProjectManifest`: язык, format/template, export targets | `src/project_foundation/projects.py`, `src/projects/repository.py` |
| Переменные окружения | **только** ключи провайдеров и тюнинг эндпоинтов | см. раздел 4 |
| Флаги CLI / ответы мастера | `ContentCreationRequest` | `src/content_creation/{cli,wizard,service}.py` |

---

## 2. Настройки, у которых больше одного источника

| Настройка | Возможные источники | Приоритет **до** D1 (что делает код) | Потребители |
|---|---|---|---|
| `language` | CLI `--language`; `job.json`/`project.json`; `channel_config.json:language`; `channel.json:default_language`; захардкоженное `"ru"` | **Две разные цепочки.** Story card: `request.language or channel.default_language` (`service.py:134`). News: `request.language or "ru"` (`service.py:464`) — `channel_config.json:language` не читается вообще | `NewsJob.language`, `ProjectManifest.language`, пути `localizations/<lang>/` |
| `target_duration_sec` | CLI `--target-duration`; `project_overrides`; `channel_config.json:target_duration_sec`; захардкоженное `55` | `request.target_duration_sec or project_overrides["target_duration_sec"] or 55` (`service.py:465`). Канальное значение **не читается** | `NewsJob`, `src/content/script_engine` |
| `resolution.width/height` | `FormatDefinition` каталога; `channel_config.json:resolution`; `NewsJob.resolution` (по умолчанию 1080×1920); render preset | Берётся `NewsJob.resolution` / preset. Канальное значение **не читается**; формат каталога тоже не подставляется | `src/news/final_renderer.py`, `src/production_plan/story_card_short_render.py` |
| `fps` | `channel_config.json:fps`; render preset; литерал `fps=30` в ffmpeg-фильтре | Story card — из preset; news — литерал `30` в `final_renderer.py:157,184` и `preview_renderer.py:33`. Канальное значение **не читается** | ffmpeg |
| `voice.provider / voice_profile / model_id / settings` | CLI `--voice-profile`; `channel_config.json:voice`; `channel_config.json:languages.<lang>.voice`; `AUDIO_POLICY_DEFAULTS` | `resolve_voice_policy(channel < template < project < localization)` — **шаблон перекрывает канал**; profile отдельно через `load_voice_profile_for_channel(profile_override → channel voice_profile → "ru_dom")`. Блок `languages.*` **не читается** | `src/news/voice_adapter.py`, `src/audio/narration_workflow.py` |
| `voice.approval_required / audition_required / fallback_policy` | `channel_config.json:voice_workflow`; `AUDIO_POLICY_DEFAULTS` | Шаблон перекрывает канал. Практический эффект: `never_auto_fallback_to_paid: true` у `nature_science_news_ru` **проигрывает** шаблонному `fallback_policy: manual_audio` | `src/audio/voice_workflow.py`, `src/news/voice_stage.py` |
| `subtitles` | CLI `--subtitles`; `channel_config.json:subtitles.enabled`; `channels/*/subtitle_style.json`; возможности шаблона | Только CLI + возможности шаблона. Канальные `subtitles.enabled` и `subtitle_style.json` **не читаются** новым пайплайном | `src/news/subtitles.py` |
| `music` | CLI `--music`; `channel_config.json:music`; `assets/music/music_manifest.json` | Только CLI → manifest → `final_renderer`. Канальный блок **не читается** | `src/audio/music_manifest.py`, `src/news/final_renderer.py` |

---

## 3. Настройки, которые записаны в конфиге, но не читаются никем

Проверено поиском по `src/` и `pipeline.py`:

- `channel_config.json`: `target_duration_sec`, `min_duration_sec`, `max_duration_sec`,
  `resolution`, `fps`, `language`, `subtitles`, `music`, `localization`, `languages`,
  `content`, `assets`, `approval`.
- `channels/*/subtitle_style.json` — только legacy `channel_loader`.
- Слово `languages` не встречается ни в `src/news/`, ни в `src/audio/` — подключение
  этого блока и есть содержание этапа D2.

Резолвер разрешает часть из них и честно помечает предупреждением
`no_consumer_yet`: `fps`, `min_duration_sec`, `max_duration_sec`. Остальные не входят в
его набор ключей, потому что у них нет ни одного потребителя и ни одного значения
по умолчанию в коде — придумывать их D1 не должен.

---

## 4. Переменные окружения

В этом проекте окружение используется **только** для провайдеров. Ни одна
продуктовая настройка (голос, длительность, стиль) через окружение не задаётся.

| Переменная | Секрет | Где читается |
|---|---|---|
| `ELEVENLABS_API_KEY` | да | `src/audio/tts/env.py`, `src/voice_engine.py` |
| `OPENAI_API_KEY` | да | `src/assets/semantic_visual_openai.py`, `semantic_visual_evaluation.py` |
| `PEXELS_API_KEY` | да | `src/news/{asset_manager,stock_video_downloader}.py`, `src/asset_finder.py`, `src/video_asset_engine.py`, `src/assets/provider_diagnostics.py` |
| `PIXABAY_API_KEY` | да | там же + `src/music_engine.py`, `src/music_finder.py` |
| `UNSPLASH_ACCESS_KEY` | да | упоминается в `provider_diagnostics.py` |
| `ELEVENLABS_VOICE_ID` | нет | `src/audio/tts/env.py`, `src/production_plan/solar_vs_nuclear_render.py` |
| `WIKIMEDIA_*`, `NASA_IMAGES_*`, `INTERNET_ARCHIVE_*` (`API_BASE`, `USER_AGENT`, `REQUEST_TIMEOUT`, `MAX_RESULTS`) | нет | соответствующие провайдеры в `src/providers/` |

**Что делает резолвер.** Он знает четыре ключа-секрета
(`ELEVENLABS_API_KEY`, `OPENAI_API_KEY`, `PEXELS_API_KEY`, `PIXABAY_API_KEY`) и хранит
о них ровно один бит — «настроен / не настроен». Значение не читается, не
возвращается, не попадает в trace, отчёт, лог или манифест; в JSON-выводе стоит `***`.
Тюнинг эндпоинтов провайдеров резолвер не трогает: это внутреннее дело
`src/providers/`, у него уже есть свой отчёт (`provider_diagnostics`), и дублировать
его D1 не должен.

---

## 5. Приоритет, который реализован в D1

```
global_default → format_policy → channel_profile → channel_config
    → template_policy → project_override → localization_override
    → runtime_override            (+ environment: только секреты)
```

Два отличия от эскиза в `PRODUCT_VISION_AND_ROADMAP.md` («Бриф 5») и причины:

1. **`template_policy` выше канальных слоёв, а не ниже.** Так делает код сегодня
   (`resolve_voice_policy` сливает `channel_defaults`, затем `template_defaults`).
   Поставить канал выше — значит поменять поведение озвучки
   `nature_science_news_ru`, а D1 менять поведение не имеет права. Конфликт не
   скрыт: если шаблон действительно перекрыл канальное значение, у настройки
   появляется предупреждение `template_policy_overrode_channel`.
2. **Над локализацией есть слой `runtime_override`.** Явный флаг CLI сегодня бьёт
   любой файл (`request.target_duration_sec or ... or 55`,
   `load_voice_profile_for_channel(profile_override=...)`), и это место за ним
   сохранено.

Пустая строка и пустой словарь считаются «не задано» — так же, как это читает любая
цепочка `a or b or default` в существующем коде. Именно это не даёт
`languages.en.voice.voice_id: ""` стереть голос канала.
