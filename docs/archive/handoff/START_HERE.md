# Start Here

> **Статус: исторический документ (этапы 1–2B).** Актуальная карта архитектуры и статусов —
> `docs/handoff/AUTONOMOUS_ARCHITECTURE_AUDIT.md`. При любом расхождении верен аудит.
> В частности, разделы «Что ещё не соединено» ниже устарели: универсальный CLI
> (`src/content_creation/cli.py` + wizard) реализован, а story-card layout уже адаптивный.

Это handoff-пакет для продолжения AI-YouTube в Claude Code.

## Что это за проект

AI-YouTube - локальный production-проект для создания русскоязычных YouTube Shorts. Сейчас основной фокус - автоматизированные Shorts на базе одного фирменного `story_card_short_v1`, где текст, выбранное видео, лицензия/provenance, voice workflow и финальный MP4 должны соединяться одной пользовательской командой.

## Что уже реально работает

- Главный CLI `pipeline.py`.
- Staged `news_to_short` pipeline: create/run/resume и стадии до final/export.
- Provider foundation с несколькими providers и license/provenance policy.
- Visual preview кандидатов.
- Temporal frame analysis.
- Semantic Vision backend и calibration policy.
- Shadow ranking для выбора лучшего кандидата без немедленной смены production selection.
- Изолированный renderer `story_card_short_v1` для теста с совой.
- Voice workflow для preflight, import manual WAV, approve/audition.

## Что было проверено live

- OpenAI Semantic Vision controlled live evaluation: 6/6 успешных вызовов, 6 изображений, cost USD 0.11225.
- Controlled OpenAI temporal test для owl candidates: 2 logical calls, 6 images, cost USD 0.06904.
- Story-card render: `projects/story_card_owl_test/final_test.mp4`, 1080x1920, 30 fps, 14.0 sec.

## Что ещё не соединено общей пользовательской командой

- Нет универсального CLI `python -B pipeline.py story-card create ...`.
- Нет batch-команды с JSON queue.
- Story-card renderer/preset пока фиксированный, не адаптивный.
- Существующие provider, preview, temporal, semantic, shadow, license, voice и render части надо соединить, а не строить новую параллельную архитектуру.

## Читать первым

1. `CLAUDE.md`
2. `docs/handoff/CURRENT_STATE.md`
3. `docs/handoff/NEXT_PLAN.md`
4. `docs/handoff/CLI_CHEATSHEET.md`

## Источники истины

- `docs/implementation/story_card_product_validation/PRODUCT_VALIDATION_CHECKPOINT.json`
- `docs/implementation/story_card_product_validation/PRODUCT_VALIDATION_SNAPSHOT.json`
- `docs/implementation/story_card_product_validation/STORY_CARD_REPORT.md`
- `docs/implementation/story_card_product_validation/TEMPORAL_TEST_REPORT.md`
- `docs/implementation/story_card_product_validation/SHADOW_RANKING_REPORT.md`
- `docs/implementation/story_card_product_validation/CALIBRATION_REPORT.md`
- `docs/implementation/openai_live_evaluation/results/LIVE_EVAL_REPORT.md`
- `projects/story_card_owl_test/render_manifest.json`
- `projects/story_card_owl_test/story_card_layout.json`
- `projects/story_card_owl_test/selected_asset.json`
- `projects/story_card_owl_test/shadow_recommendation.json`

## Не перезаписывать

- `projects/story_card_owl_test/final_test.mp4`
- `projects/story_card_owl_test/render_manifest.json`
- `projects/story_card_owl_test/story_card_layout.json`
- `projects/story_card_owl_test/selected_asset.json`
- `projects/story_card_owl_test/shadow_recommendation.json`
- Отчёты в `docs/implementation/story_card_product_validation/`
- Live eval результаты в `docs/implementation/openai_live_evaluation/results/`
- `.env`
- `assets/library/metadata/media_index.json`

## Готовый тест с совой

- Проект: `projects/story_card_owl_test/`
- Финальный текущий MP4: `projects/story_card_owl_test/final_test.mp4`
- Renderer: `src/production_plan/story_card_short_render.py`
- Preset: `config/render_presets/story_card_short_v1.json`
