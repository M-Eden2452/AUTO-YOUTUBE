# Current State

> **Статус: исторический документ (этапы 1–2A).** Актуальное состояние —
> `docs/handoff/AUTONOMOUS_ARCHITECTURE_AUDIT.md`. Разделы «Известные ограничения» и
> «Этап 2B — следующий» устарели: Project/Channel/Evidence Foundation и единый
> content-creation CLI/Wizard реализованы, `fullscreen_voiceover_v1` подтверждён сквозным
> результатом.

Состояние зафиксировано по существующему коду и сохранённым отчётам.

## Provider foundation

- Реализации providers находятся в `src/providers/`.
- Общие asset-сервисы находятся в `src/assets/`.
- По snapshot для owl search были результаты: local_library 0, pexels 5, pixabay 5, wikimedia 0.
- Выбранный asset для owl test: `pixabay_video_18244`.

## License/provenance policy

- Policy config: `config/license_policy.json`.
- Для `pixabay_video_18244` сохранены source page, provider asset id, download URL, author, checksum, license и policy decision.
- По `selected_asset.json` render allowed: true, review required: false.
- License/provenance должны оставаться отдельными от semantic decision.

## Visual preview

- Visual preview есть как отдельный этап/сервис.
- Для owl test есть `projects/story_card_owl_test/visual_review_manifest.json`.
- Preview phase не скачивала originals; original был скачан только после ranking gates.

## Temporal frame analysis

- Модуль: `src/assets/temporal_video_analysis.py`.
- Targeted test: `tests/test_temporal_video_analysis.py`.
- Owl temporal preview анализировал позиции `[0.15, 0.5, 0.85]`.
- Controlled temporal OpenAI test завершён: 2 logical calls, 2 external HTTP attempts, 6 images, USD 0.06904.

## Semantic Vision backend

- Service: `src/assets/semantic_visual_service.py`.
- OpenAI backend: `src/assets/semantic_visual_openai.py`.
- Controlled live evaluation report: 6 attempted, 6 succeeded, 0 failed, 6 images, USD 0.11225.
- `detail=low` в live report отмечен как недостаточный для дальнейшего использования; нужен повтор отдельных случаев на `detail=high`.

## Semantic calibration

- Policy: `src/assets/semantic_decision_policy.py`.
- Targeted test: `tests/test_semantic_decision_policy.py`.
- Raw classification accuracy: 0.666667.
- Calibrated classification accuracy: 0.833333.
- Pairwise ranking accuracy: 3/3.

## Shadow ranking

- Shadow recommendation: `projects/story_card_owl_test/shadow_recommendation.json`.
- Recommended candidate: `pixabay_video_18244`.
- Runner-up: `pixabay_video_95059`.
- Score margin: 0.7066.
- Confidence: high.
- Global production selection was not changed.

## story_card_short_v1

- Preset: `config/render_presets/story_card_short_v1.json`.
- Renderer: `src/production_plan/story_card_short_render.py`.
- Test: `tests/test_story_card_short_renderer.py`.
- Current output: `projects/story_card_owl_test/final_test.mp4`.
- Render status: completed.
- Resolution: 1080x1920.
- FPS: 30.
- Duration: 14.0 sec.
- Audio status: silent visual preview; TTS performed false.

## Voice workflow

- CLI/workflow: `src/audio/voice_cli.py`, `src/audio/voice_workflow.py`.
- Supported actions from `pipeline.py`: list, inspect, preflight, import-audio, approve, audition.
- Manual WAV import is supported through `--voice-action import-audio`.
- Audition can perform paid ElevenLabs synthesis, so it needs explicit user approval before use.

## news_to_short

- Entry: `python -B pipeline.py --news-to-short`.
- Actions: create, run, resume.
- Stages in code: input, article_ingestion, research, script, visual_plan, asset_search, voice, subtitles, preview_render, quality_check, final_render, export.
- Dry-run stops before paid/heavy late stages and defaults stop stage to asset_search.

## Последние известные результаты тестов

- Targeted validation: passed, 53 tests.
- `python -m unittest tests.test_semantic_decision_policy -v`: passed.
- `python -m unittest tests.test_temporal_video_analysis -v`: passed.
- `python -m unittest tests.test_story_card_short_renderer -v`: passed.
- Full unittest discovery from saved report: passed, 276 tests, 79.042 sec. Do not rerun full suite casually.

## Production Catalog Foundation (Этап 2A)

- Готов: read-only каталог `Application → Format → Template → Export Target`.
- Расположение: `src/production_catalog/` (`models.py`, `registry.py`, `catalog.py`, `cli.py`).
- Applications: `content_creator` (enabled=true, active), `video_repurposer` (enabled=false, planned).
- Formats: `vertical_short` (active), `longform` (experimental), `horizontal_clip` (planned).
- `story_card_text_only_v1` зарегистрирован (application=content_creator, format=vertical_short, render_preset_id=story_card_short_v1).
- Legacy alias `story_card_short_v1` работает: `templates inspect --template story_card_short_v1` разрешается в канонический `story_card_text_only_v1`.
- Export targets: youtube_shorts, instagram_reels, tiktok, facebook_reels, stories (все active, format=vertical_short).
- CLI read-only работает: `python -B pipeline.py applications|formats|templates|export-targets list|inspect ...`, опционально `--json`.
- Пользовательская шпаргалка: `COMMANDS.md`.
- Targeted tests: `python -m unittest tests.test_production_catalog_foundation -v` — 23 теста, OK.
- Подробный отчёт: `docs/implementation/production_catalog_foundation/CATALOG_REPORT.md`.
- Каталог не создаёт проектов/каналов/EvidenceBundle — это Этап 2B.

## Известные ограничения

- Один тестовый Shorts с совой создан.
- Текущий `final_test.mp4` имеет фиксированный layout.
- Длительность 14 секунд.
- Центральный фрагмент начинается на 13.0 sec, длится 6.8 sec и повторяется два раза.
- Центральное видео слишком маленькое.
- Внутри карточки остаются большие пустые зоны.
- Нижний комментарий надо приблизить к нижнему краю.
- Это недостаток preset/renderer, а не semantic selection.
- Universal story-card CLI для новых тем пока отсутствует.
- Batch queue для story-card пока отсутствует.
