# Production Catalog Foundation — Report

Этап 2A завершён: минимальный read-only каталог
`Application → Format → Template → Export Target` добавлен без создания
проектов, каналов, EvidenceBundle или creator workflow.

## Добавленные модели и contracts

- `src/production_catalog/models.py` — frozen dataclasses:
  `ApplicationDefinition`, `FormatDefinition`, `TemplateDefinition`,
  `ExportTargetDefinition`; закрытый набор `IMPLEMENTATION_STATUSES =
  {"active", "planned", "experimental"}`; `CatalogValidationError`.
  `enabled` (bool) и `implementation_status` (str) — независимые обязательные
  поля у каждой записи, без единой формулировки "или/зависит от".
- `src/production_catalog/registry.py` — `ApplicationRegistry`, `FormatCatalog`,
  `TemplateRegistry` (canonical id + legacy alias resolution, фильтры по
  application/format/enabled, защита от дублей id и alias), `ExportTargetCatalog`.
- `src/production_catalog/catalog.py` — `get_default_catalog()` (cached,
  строится только в памяти, без файлов и сети) с фактической регистрацией
  данных.
- `src/production_catalog/cli.py` — `run_production_catalog_cli(args) -> int`,
  подключён в `pipeline.py` как 4 новые команды.

## Расположение каталога

`src/production_catalog/` (models, registry, catalog, cli). Ничего не
записывается на диск и не создаёт файлов проекта.

## Зарегистрированные Applications

| application_id | display_name | enabled | implementation_status |
|---|---|---|---|
| content_creator | Создание контента | true | active |
| video_repurposer | Нарезка и переработка видео | false | planned |

## Зарегистрированные Formats

| format_id | display_name | width×height | aspect_ratio | enabled | implementation_status |
|---|---|---|---|---|---|
| vertical_short | Короткое вертикальное видео | 1080×1920 | 9:16 | true | active |
| longform | Длинное видео | 1920×1080 | 16:9 | true | experimental |
| horizontal_clip | Горизонтальная нарезка | 1920×1080 | 16:9 | false | planned |

`longform` зарегистрирован как `enabled: true` + `implementation_status:
experimental` — по аудиту проекта старый documentary/longform pipeline
частично работает end-to-end при ручной подготовке конфигурации, что не
соответствует "planned" (ничего не реализовано), но и не является полноценным
"active".

## Зарегистрированный story_card_text_only_v1

- `template_id`: `story_card_text_only_v1`
- `application_id`: `content_creator`, `format_id`: `vertical_short`
- `render_preset_id`: `story_card_short_v1` (существующий preset/renderer не
  переименован и не изменён)
- `legacy_aliases`: `["story_card_short_v1"]`
- `requires_voice`: false; `supports_topic_input` / `supports_script_input`: true
- `supported_export_targets`: youtube_shorts, instagram_reels, tiktok,
  facebook_reels, stories
- `workflow_binding` ссылается на `src.news.pipeline.run_news_to_short_cli` и
  `src.production_plan.story_card_short_render` (существующий workflow/renderer,
  новый renderer не создавался)
- `output_contract`: final_video (mp4, vertical), render_manifest (json),
  layout_manifest (json), preview_image (png), technical_validation (json)
- `evidence_required`: true (декларация; EvidenceBundle будет реализован в
  Этапе 2B)
- Policy-ссылки (`script_policy_id`, `asset_policy_id`, `audio_policy_id`,
  `duration_policy_id`, `selection_policy_id`, `quality_policy_id`): все `null` —
  сегодня это неявная логика внутри renderer/asset_manager, отдельных policy
  сущностей нет, фиктивные id не изобретались.

## Как работает legacy alias `story_card_short_v1`

`TemplateRegistry.resolve_id("story_card_short_v1")` возвращает канонический
`story_card_text_only_v1`. CLI `templates inspect --template
story_card_short_v1` печатает строку `'story_card_short_v1' — это legacy
alias. Канонический template_id: 'story_card_text_only_v1'.`, затем полную
карточку канонического шаблона. В `--json` режиме добавляются поля
`requested_id` и `resolved_from_legacy_alias`.

## Зарегистрированные Export Targets

Все 5 целей используют `format_id=vertical_short`, 1080×1920, 9:16,
`safe_zone_profile=vertical_9x16_standard`, `enabled=true`,
`implementation_status=active`. `max_duration_sec` оставлен `null` для всех —
поле объявлено опциональным, а точные лимиты платформ меняются со временем,
поэтому фиктивные числа не вносились.

| target_id | display_name | output_filename |
|---|---|---|
| youtube_shorts | YouTube Shorts | youtube_shorts.mp4 |
| instagram_reels | Instagram Reels | instagram_reels.mp4 |
| tiktok | TikTok | tiktok.mp4 |
| facebook_reels | Facebook Reels | facebook_reels.mp4 |
| stories | Stories (Instagram/Facebook) | stories.mp4 |

## Реальные CLI-команды

```bash
python -B pipeline.py applications list
python -B pipeline.py applications inspect --application content_creator
python -B pipeline.py formats list
python -B pipeline.py formats inspect --format vertical_short
python -B pipeline.py templates list
python -B pipeline.py templates list --application content_creator
python -B pipeline.py templates list --format vertical_short
python -B pipeline.py templates inspect --template story_card_text_only_v1
python -B pipeline.py templates inspect --template story_card_short_v1
python -B pipeline.py export-targets list
python -B pipeline.py export-targets inspect --target youtube_shorts
```

Любая из команд поддерживает `--json` для машиночитаемого вывода.

## Пример вывода

```text
$ python -B pipeline.py applications list
Приложения (2):
- content_creator | Создание контента | enabled=true | status=active
- video_repurposer | Нарезка и переработка видео | enabled=false | status=planned
```

```text
$ python -B pipeline.py templates inspect --template story_card_short_v1
'story_card_short_v1' — это legacy alias. Канонический template_id: 'story_card_text_only_v1'.
Шаблон: story_card_text_only_v1
  ...
  Render preset id: story_card_short_v1
```

Полный сериализованный каталог: `CATALOG_SNAPSHOT.json` в этой же папке.

## COMMANDS.md

Создан в корне проекта: `COMMANDS.md`. Короткая пользовательская шпаргалка на
русском для непрограммиста, с разделом "ЗАПЛАНИРОВАНО, НО ПОКА НЕ РАБОТАЕТ".

## Созданные docs

- `docs/implementation/production_catalog_foundation/CATALOG_PLAN.md`
- `docs/implementation/production_catalog_foundation/CATALOG_REPORT.md` (этот файл)
- `docs/implementation/production_catalog_foundation/CATALOG_SNAPSHOT.json`
- `docs/implementation/production_catalog_foundation/TEST_RESULTS.txt`

## Результаты targeted tests

- `python -m unittest tests.test_production_catalog_foundation -v` — 23 теста, OK.
- `python -m unittest tests.test_story_card_short_renderer tests.test_apps_structure -v` — 5 тестов, OK (регрессий нет).
- Полный лог: `TEST_RESULTS.txt`.

## Подтверждение отсутствия запрещённых действий

- Не выполнялись: OpenAI/провайдерные API, provider search, downloads, Vision,
  TTS, render, создание project/channel/EvidenceBundle.
- `media-library migrate --apply` не запускался.
- `.env` не читался и не менялся.

## Подтверждение неизменности контрольных файлов (SHA-256)

| Файл | До | После |
|---|---|---|
| `assets/library/metadata/media_index.json` | `61b2c5b8...30385` | `61b2c5b8...30385` (не изменился) |
| `projects/story_card_owl_test/final_test.mp4` | `46305b61...489ac96` | `46305b61...489ac96` (не изменился) |
| `projects/story_card_owl_test/final_test_v2.mp4` | `f642b11e...3fee813e0` | `f642b11e...3fee813e0` (не изменился) |

## Изменённые/созданные файлы этого этапа

Созданы:
- `src/production_catalog/__init__.py`
- `src/production_catalog/models.py`
- `src/production_catalog/registry.py`
- `src/production_catalog/catalog.py`
- `src/production_catalog/cli.py`
- `tests/test_production_catalog_foundation.py`
- `COMMANDS.md`
- `docs/implementation/production_catalog_foundation/*`

Изменены:
- `pipeline.py` (новый импорт, 4 новых command choices, новые `--application`,
  `--format`, `--template`, `--target`, `--json` аргументы, dispatch-блок)
- `CLAUDE.md`, `docs/handoff/CURRENT_STATE.md`, `docs/handoff/NEXT_PLAN.md`,
  `docs/handoff/CLI_CHEATSHEET.md`, `docs/handoff/HANDOFF_MANIFEST.json`

## Известные ограничения

- Каталог полностью read-only и in-memory: нет персистентности, нет
  project/channel/EvidenceBundle интеграции — это Этап 2B.
- `video_repurposer` зарегистрирован только как метаданные; workflow не
  реализован.
- `longform` помечен `experimental`; полноценный тестовый прогон longform
  pipeline в этом этапе не проверялся (только чтение существующего аудита).
- Policy-ссылки шаблона (`script_policy_id` и т.д.) все `null` — конкретные
  policy-сущности ещё не выделены из renderer/asset_manager.
- JSON-режим (`--json`) — новая, минимальная конвенция; в `pipeline.py` ранее
  не было единого JSON-режима для команд.

## Следующий этап

Этап 2B — Project / Channel / Evidence Foundation: `ChannelProfile`,
`ProjectManifest`, `ProjectFactory`, `EvidenceBundle`, `ChannelOutputPolicy`,
`channels list/inspect`, тестовый канал `nature_pulse`.
