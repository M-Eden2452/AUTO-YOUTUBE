# AI-YouTube Handoff

Этот файл нужен для продолжения разработки в Claude Code без истории чатов Codex.

## Контекст проекта

- Проект: локальная система для создания русскоязычных YouTube Shorts и связанных production-пайплайнов.
- Целевая модель: `Application → Format → Template → Channel → Project → Stages → Exports`.
- Два реально работающих шаблона: `fullscreen_voiceover_v1` (самый зрелый, подтверждён сквозным
  результатом с настоящей озвучкой) и `story_card_text_only_v1` (карточка поверх локального видео).
- Рабочая папка: `G:\Projects\AI-YouTube`.
- Основная среда пользователя: Windows + Git Bash.
- Пользователь не программист: давай понятные команды, объясняй результат простым языком и явно показывай итоговые файлы.
- Предпочтительный язык общения: русский.

## Запуск Python

Всегда через интерпретатор venv, без bare `python`/`pip`/`pytest`:

```bash
cd /g/Projects/AI-YouTube
./venv/Scripts/python.exe -m src.content_creation.cli capabilities
```

На Windows-консоли с не-UTF8 кодовой страницей добавляй `PYTHONIOENCODING=utf-8` перед командой.

## Основные приложения и режимы

- `src/content_creation/cli.py` - **канонический CLI создания контента** (`create`, `resume`,
  `wizard`, `capabilities`, `project`). Запуск: `./venv/Scripts/python.exe -m src.content_creation.cli`.
  Он намеренно не подключён к `pipeline.py`.
- `pipeline.py` - CLI обслуживания и legacy: старый channel/video render, `--news-to-short`,
  `--voice-action`, `media-library`, диагностика provider/semantic/preview, read-only каталог.
- Legacy/channel pipeline - старый режим для channel profiles и video tasks
  (`quotes`, `psychology`, `survival`, `size_comparison`). Создание контента его не использует.
- `news_to_short` - staged pipeline для новостного short: input, article, research, script, visual plan, asset search, voice, subtitles, preview, quality, final render, export.
- Provider foundation - общий слой поиска/лицензий/provenance для ассетов.
- Visual preview - подготовка preview candidates и HTML review board.
- Semantic visual - анализ кандидатов, OpenAI backend и calibration/shadow decision policy.
- Voice workflow - безопасная работа с ручным WAV и voice profiles.
- Story card renderer - текущий изолированный renderer/preset для тестового short с совой.

## Архитектурная карта

Полная актуальная карта: `docs/handoff/AUTONOMOUS_ARCHITECTURE_AUDIT.md`.

- Content-creation CLI/Wizard: `src/content_creation/{cli,wizard,service,capabilities,models}.py`
- Config resolution: `src/config_resolver/` (read-only, поверх каталога/`ChannelRegistry`/
  `channel_config.json`/`AUDIO_POLICY_DEFAULTS`; карта — `docs/implementation/config_resolver/CONFIG_MAP.md`)
- Localization/voice runtime: `src/localization/` (read-only, поверх `config_resolver` +
  `voices.yaml` + `voice_manifest.json`; карта —
  `docs/implementation/localization_voice/LOCALIZATION_VOICE_MAP.md`)
- Subtitle engine: `src/subtitles/` (единственный движок субтитров; границы сцен берёт
  из `src/audio/scene_timeline.py`, язык — из `src/localization/`; адаптер пайплайна —
  `src/news/subtitles.py`; карта —
  `docs/implementation/subtitle_engine/SUBTITLE_ENGINE_MAP.md`)
- Production Catalog: `src/production_catalog/`
- Project/Channel/Evidence Foundation: `src/project_foundation/`
- Maintenance/legacy CLI: `pipeline.py`
- Provider interfaces and implementations: `src/providers/`, `src/assets/`
- License/provenance policy: `config/license_policy.json`, provider metadata in project manifests
- Visual preview: `src/assets/visual_preview.py`, config `config/visual_preview.json`
- Temporal frame analysis: `src/assets/temporal_video_analysis.py`
- Semantic service: `src/assets/semantic_visual_service.py`
- OpenAI Vision backend: `src/assets/semantic_visual_openai.py`
- Semantic calibration and decision policy: `src/assets/semantic_decision_policy.py`
- Voice CLI/workflow: `src/audio/voice_cli.py`, `src/audio/voice_workflow.py`, channel voices in `channels/nature_science_news_ru/voices.yaml`
- News-to-short pipeline: `src/news/pipeline.py`, models in `src/news/models.py`
- Story-card renderer: `src/production_plan/story_card_short_render.py`
- Story-card preset: `config/render_presets/story_card_short_v1.json`
- Existing owl test project: `projects/story_card_owl_test/`

## Перед любой новой работой

1. Сначала читай `docs/handoff/AUTONOMOUS_ARCHITECTURE_AUDIT.md` (canonical current architecture).
2. Затем `docs/handoff/AUTONOMOUS_IMPLEMENTATION_PLAN.md` и `docs/handoff/AUTONOMOUS_PROGRESS.md`.
3. `docs/handoff/START_HERE.md` / `CURRENT_STATE.md` / `NEXT_PLAN.md` — исторический контекст
   этапов 1–2B; при расхождении верен аудит.
4. Для story-card работы сначала проверь checkpoint и существующие manifests:
   - `docs/implementation/story_card_product_validation/PRODUCT_VALIDATION_CHECKPOINT.json`
   - `docs/implementation/story_card_product_validation/PRODUCT_VALIDATION_SNAPSHOT.json`
   - `projects/story_card_owl_test/render_manifest.json`
   - `projects/story_card_owl_test/story_card_layout.json`
   - `projects/story_card_owl_test/selected_asset.json`
   - `projects/story_card_owl_test/shadow_recommendation.json`
5. Используй существующие модули. Не создавай дубликаты renderer, provider, semantic, preview или voice архитектуры.
6. Не создавай третью project-систему, второй voice registry, второй provider contract и вторую
   configuration-систему. Только адаптеры поверх существующих.

## Безопасность

- Не выполняй платные вызовы без прямого разрешения пользователя.
- Не запускай OpenAI API, Vision, TTS, provider search или скачивание файлов без отдельного разрешения.
- Никогда не меняй `.env`.
- Никогда не раскрывай API keys, tokens, credentials или private provider responses.
- Не читай `.env`, `.env.*`, `secrets/**`, credential-файлы и private key-файлы.
- Не запускай `media-library migrate --apply` без отдельного подтверждения пользователя.
- Не выполняй destructive Git: `git reset`, `git clean`, удаление истории, force operations.
- Не удаляй legacy до миграции и резервной копии.
- Не запускай полный test suite после каждого локального изменения. Используй targeted tests.
- Не перезаписывай существующие validation/report artifacts без явного запроса.

## Безопасные быстрые команды

```bash
./venv/Scripts/python.exe -m src.content_creation.cli capabilities
./venv/Scripts/python.exe -m src.content_creation.cli templates list
./venv/Scripts/python.exe -m src.content_creation.cli channels list
./venv/Scripts/python.exe -B pipeline.py --help
./venv/Scripts/python.exe -B pipeline.py --news-to-short --news-action create --topic "пример темы" --dry-run --until-stage visual_plan
./venv/Scripts/python.exe -B pipeline.py --news-to-short --news-action run --job-id <job_id> --dry-run --stage asset_search
./venv/Scripts/python.exe -B pipeline.py --voice-action list --news-channel nature_science_news_ru
./venv/Scripts/python.exe -B pipeline.py --voice-action preflight --news-channel nature_science_news_ru --voice-profile <profile_id> --text "Короткий тест."
./venv/Scripts/python.exe -B pipeline.py --voice-action import-audio --job-id <job_id> --audio-file <path/to/manual.wav>
./venv/Scripts/python.exe -m src.content_creation.cli channels show --channel nature_science_news_ru --explain
./venv/Scripts/python.exe -m unittest tests.test_capability_consistency -v
./venv/Scripts/python.exe -m unittest tests.test_config_resolver tests.test_config_resolver_parity -v
./venv/Scripts/python.exe -m unittest tests.test_localization_voice_integration -v
./venv/Scripts/python.exe -m src.content_creation.cli voices explain --channel nature_science_news_ru
./venv/Scripts/python.exe -m src.content_creation.cli subtitles explain --project-id <project_id>
./venv/Scripts/python.exe -m src.content_creation.cli subtitles validate --project-id <project_id>
./venv/Scripts/python.exe -m unittest tests.test_subtitle_engine tests.test_subtitle_pipeline_integration -v
./venv/Scripts/python.exe -m unittest tests.test_story_card_short_renderer -v
./venv/Scripts/python.exe -m unittest tests.test_temporal_video_analysis -v
./venv/Scripts/python.exe -m unittest tests.test_semantic_decision_policy -v
```

## Current Story Card Direction

- Пользователь хочет один адаптивный фирменный `story_card_short_v1`, а не несколько режимов карточки.
- Адаптивный layout уже сделан: `projects/story_card_owl_test/final_test_v2.mp4` (см. `docs/implementation/story_card_adaptive_layout/ADAPTIVE_LAYOUT_REPORT.md`).
- Не запускать поиск, Vision или TTS без отдельного разрешения.
- Не перезаписывать `projects/story_card_owl_test/final_test.mp4`.

## Production Catalog

- Read-only каталог `Application → Format → Template → Export Target` в `src/production_catalog/` (models, registry, catalog, cli).
- Шаблоны: `story_card_text_only_v1` (legacy alias `story_card_short_v1`) и `fullscreen_voiceover_v1`. Оба `active`, оба используют существующие renderer/workflow — новых renderer не создавалось.
- Форматы: `vertical_short` активен; `longform` и `horizontal_clip` — `enabled=false`, потому что у них
  ещё нет ни одного шаблона. Включать формат разрешено только вместе с регистрацией рабочего шаблона
  (правило зафиксировано в `tests/test_capability_consistency.py`).
- CLI: `applications`, `formats`, `templates`, `export-targets` (list/inspect, `--json`). Пользовательская шпаргалка: `COMMANDS.md`.
- Project/Channel/EvidenceBundle реализованы в `src/project_foundation/`.

## Известные ограничения (по состоянию на аудит 2026-07-25)

- Autonomous completion (этап Q2.2B): у пайплайна два режима. `strict` — default и
  прежнее поведение: одна неотвеченная сцена останавливает ролик. `draft_complete`
  включается только явным `--completion-mode draft_complete` и собирает **черновик**
  из partial/fallback материала. Модули: `src/assets/completion/` (modes, assembly,
  ladder, replacement, report) и `src/news/draft_completion.py`. Третий режим,
  второй contract готовности и второй ladder заводить нельзя.
  Что режим **не** ослабляет ни при каких условиях: rights-blocked, unknown license,
  `must_avoid`, declared conflicting context и factually misleading материал
  fail closed в обоих режимах (`src/assets/completion/modes.py:blocking_reasons`).
  `publish_ready` в draft всегда `false`; выход — `draft_1080x1920.mp4`.
  Сцена = `visual_assembly.slots` (1–4 slots); старый scene-level `selected_asset`
  без assembly читается как один slot на всю сцену, миграции на диске нет.
  Script adaptation — максимум **один** durable pass, только по слабым сценам, под
  fact locks (`src/content/script_engine/fact_locks.py`); если покрытие не улучшилось,
  исходный script остаётся активным. Платного adapter/Vision здесь нет.
- Slot-Aware Targeted Retrieval (этап Q2.3, только в `draft_complete`): после того как
  composite assembly собран из общего per-scene пула, `unfilled_semantic_slots`
  (`src/assets/completion/ladder.py`) определяет, какие из четырёх semantic slots
  (subject/action/location/context) не закрыты **ни одним** слотом сборки (не просто
  не закрыты каждым слотом по отдельности — сосед может уже покрывать slot). Только
  для них `_targeted_slot_search` (`src/news/asset_manager.py`) отправляет **один**
  запрос на slot на provider, построенный `build_slot_queries`
  (`src/assets/query_adapter.py`) из ограниченного набора полей `visual_brief`
  (`SLOT_QUERY_FIELDS`) — без нового источника перевода. Дедупликация против уже
  отправленных query/provider пар (включая общий поиск) обязательна. Пас выполняется
  **не более одного раза за сцену**, независимо от того, сколько slots не закрыто и
  помог ли он. Результаты идут через тот же `rank_candidates`/decision pipeline и те же
  rights/technical/must_avoid/conflicting gates — targeted-результат не имеет
  отдельного авторитета. В `strict` не вызывается вообще (гейт — только внутри
  `_complete_scene_assembly`, которая сама вызывается только при `draft_complete`).
  Второй planner/pipeline не заводить.
  Попутно исправлена связанная ошибка Q2.2B: composite-сборка со свежескачиваемым
  secondary asset падала в `_ensure_selected_asset_downloaded`, потому что secondary
  почти всегда несёт `rejected=True` от strict single-winner ранжировщика — теперь
  per-slot download явно игнорирует этот флаг (ладдер уже принял независимое решение).
- Экспорт под площадки — копии master MP4; `tiktok` и `stories` не создаются.
- Визуальный поиск (после этапа Q2.1, карта —
  `docs/implementation/visual_retrieval_repair/VISUAL_RETRIEVAL_MAP.md`): порядок
  провайдеров задаёт `src/assets/scene_strategy.py` по классу сцены, запрос под
  провайдера строит `src/assets/query_adapter.py`. **Слоя перевода по-прежнему нет**:
  русский запрос в англоязычный провайдер не отправляется, сцена помечается
  `query_translation_required` и остаётся `unresolved`, пока автор не задаст
  `visual_brief` (английские `subject`/`place`/`exact_entities`/`provider_queries`).
  Бриф передаётся **одним** способом — `create --visual-brief FILE` (этап Q2.2A);
  офлайн-проверка — `script generate --visual-brief FILE`. Второй вход не заводить.
  Кандидат не выбирается автоматически без проверенного требования и пригодного кропа
  под 9:16 (`semantic_unverified`, `framing_unusable`).
  Смысловая проверка кандидата опирается на метаданные провайдера, не на кадр:
  платный Vision не подключён, локальная image-text модель не добавлена.
  Сцена без подходящего материала остаётся `unresolved` — подставлять «похожий»
  клип нельзя. Второй asset pipeline и второй планировщик создавать нельзя.
  После этапа Q2.2A-2 требования сцены разбираются по слотам
  (`src/assets/semantic_selection/decision.py`): `subject`, `action`, `location`,
  `context`, `must_include`, `conflicting_context`. Обязательность слота задаёт
  `source_class`. Частичное совпадение больше не считается полным: кандидат получает
  `support_status` (`full_support` / `partial_support` /
  `manual_confirmation_required` / `relevant_but_rights_blocked` / `unverified` /
  `unsupported`) и `support_requirements` (`needs_additional_asset`,
  `needs_multi_asset`, `needs_crop_review`, ...). Кроп получает объяснимое состояние
  (`vertical_ready` / `crop_review_required` / `low_resolution_after_crop` /
  `technical_rejected` / `aspect_ratio_mismatch`) — без Vision утверждать, что объект
  переживёт кроп, запрещено. Решение хранится **одной** записью `selection_decision`
  и переносится до манифеста, доски обзора и `project status`; второй контракт решения
  не заводить. `needs_additional_asset` только фиксирует потребность — сборки
  нескольких ассетов в одну сцену нет.
- Музыка для `fullscreen_voiceover_v1` работает: `src/audio/music_manifest.py` пишет
  `assets/music/music_manifest.json`, который читает существующий микс с ducking в
  `src/news/final_renderer.py`. Права на пользовательский трек не проверяются автоматически.
- `src/config_resolver/` подключён к пайплайну **только по части голоса и локализации**
  (этап D2/E2, через `src/localization/`): стадия `voice`, `voice_adapter`,
  content-creation service, CLI и мастер берут язык, locale, провайдера, профиль,
  `voice_id`, модель и `fallback_policy` из него. Остальное из `channel_config.json`
  (`target_duration_sec`, `min/max_duration_sec`, `resolution`, `fps`, `subtitles`,
  `music`) по-прежнему **не читается пайплайном**. Блок `languages.<id>.voice`
  читается. Стили субтитров канала (`subtitle_style.json`) подключены этапом Q3
  через `src/subtitles/style.py` — но не через `config_resolver`, а напрямую из файла
  канала; `safe_zone_bottom` намеренно не двигает ASS `MarginV`.
- Субтитры: единственный движок — `src/subtitles/`. Второй создавать нельзя.
  Границы сцен берутся только из `src/audio/scene_timeline.py`; уровень потаймингов
  слов существует в контракте, но **ни один модуль их не пишет** — выдумывать их
  запрещено (STT/alignment — отдельный этап).
- В `projects/` сосуществуют две project-системы: `job.json` (news_to_short) и `project.json`
  (story_card). Общий **read-only** слой — `src/projects/` (`ProjectRepository` для статуса,
  `build_rights_report` для прав); он не является третьей системой и ничего не пишет.
  `project list`, `project status` и `project rights-report` работают для обеих;
  `project validate` — пока только для `project.json`.
- Story-card workflow **записывает provenance** выбранного материала (Stage C3):
  `src/templates/story_card/integration.py` пишет `evidence/evidence_manifest.json` через
  `EvidenceBundle`, описывая именно тот файл, который получил renderer. Локальный файл
  пользователя сохраняется как `user_supplied` со статусом `review_required` — никогда
  `verified`. Проекты, созданные до C3, evidence не имеют, и отчёт говорит об этом прямо.
- Старые news-проекты (до 2026-07-23) содержат ассеты без `license_name` и `checksum_sha256` —
  отчёт честно помечает их `review_required`, хотя видео уже отрендерено.

