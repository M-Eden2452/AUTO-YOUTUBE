---
status: current
last_verified_commit: 5787c61
last_verified_date: 2026-08-15
source_paths:
  - docs/current/PROJECT_EXECUTION_PLAN.md
  - docs/current/CLEANUP_REGISTRY.md
  - src/production_catalog
  - src/content_creation/capabilities.py
  - src/ai_youtube/apps
  - src/news
  - src/assets
  - src/projects
  - src/runtime_network.py
  - config/semantic_brief.json
  - config/semantic_visual.json
  - schemas/job.schema.json
  - tests
---

# Current State

Что существует сегодня и чем это ограничено. Код и фактический Git важнее этого
документа. История закрытий здесь не пересказывается: evidence каждого шага
живёт в [PROJECT_EXECUTION_PLAN.md](PROJECT_EXECUTION_PLAN.md), завершённые
structural/vertical slices и retirement decisions — в
[CLEANUP_REGISTRY.md](CLEANUP_REGISTRY.md), карта модулей — в
[SYSTEM_MAP.md](SYSTEM_MAP.md) и
[ARCHITECTURE_BOUNDARY_MAP.md](ARCHITECTURE_BOUNDARY_MAP.md).

## Что работает

- Активное приложение — одно: `content_creator`.
- Активные live-tested шаблоны: `fullscreen_voiceover_v1` и
  `story_card_text_only_v1`.
- `video_repurposer`, `longform` и `horizontal_clip` остаются planned/disabled.
  Anime Clipper adapter существует, но product capability не включена.
- `applications list` по умолчанию показывает только active/enabled приложения;
  planned/disabled доступны лишь по явному запросу и сохраняют честный статус.
- Канонический CLI — `python -m ai_youtube`. `src.content_creation.cli`,
  `pipeline.py` и `apps/*` — compatibility entrypoints.

## Что уже получилось, и что это ещё не значит

Первый черновой `draft_1080x1920.mp4` этой программы существует и повторно
воспроизводится offline на принятом HEAD. В последнем прогоне 5 из 5 сцен
получили usable visual slot, но **0 из 5** — `publish_ready`, `quality_report`
остался `needs_review`, все слоты draft-only. Это диагностическое evidence, а не
приёмка: publish-ready результата у платформы пока нет.

## Активные ограничения

- Две формы project manifests (`job.json` и `project.json`) сосуществуют;
  `ProjectRepository` читает обе и legacy roots, но ничего не записывает.
- Default workspace остаётся корнем репозитория; runtime-проекты и media
  физически не переносились. Versioned config/resources всегда разрешаются от
  корня репозитория, а не от cwd.
- Этап 8 установил application boundaries, но ownership transfer не завершён:
  `src.news`, `src.templates.story_card`, `anime_factory`, `pipeline.py` и
  `src.legacy_pipeline` всё ещё владеют частью поведения.
- `strict` — режим completion по умолчанию; `draft_complete` — явный opt-in,
  всегда `publish_ready=false`, и права, `must_avoid`, conflict и
  misleading-content gates им не ослабляются.
- Runtime-сеть fail-closed по умолчанию: единственный владелец разрешения —
  `src/runtime_network.py` с закрытым словарём классов, разрешение выдаётся
  поимённо на один прогон. Наличие ключа разрешением не является.
- Смысловой бриф (`config/semantic_brief.json`) и Vision
  (`config/semantic_visual.json`) в репозитории **выключены**. Включение требует
  двух раздельных разрешений — сетевого и платного; одно другого не заменяет.
- Output-validated stage idempotency покрывает повторяемые стадии от `research`
  до `export`; `input` и потенциально сетевой `article_ingestion` намеренно вне
  автоматической retry-policy (ADR 0006).
- Tolerant readers, resume/force-stage и approval gates сохраняются; legacy
  asset/voice/subtitle shapes и пользовательские субтитры остаются protected.

Открытые findings с владельцами (`C47`, `C63`, `C65`, `C75`–`C82` и остальные)
перечислены в [CLEANUP_REGISTRY.md](CLEANUP_REGISTRY.md) со своим gate; здесь они
не дублируются.

## Маршрут

Текущий checkpoint — **PLAN-9D**; авторитетное значение и следующее точное
действие — во frontmatter [PROJECT_EXECUTION_PLAN.md](PROJECT_EXECUTION_PLAN.md).
Следующее точное действие — **LIVE-5**; это платное сетевое действие и требует
отдельного явного разрешения владельца.

## Процесс

- Архитектурные изменения выполняются малыми slices после карты callers/tests;
  удаление без доказанной замены и migrated callers запрещено.
- Сначала characterization test, затем изменение поведения.
- Для каждого изменения запускаются targeted tests в радиусе владельца; полный
  offline suite — на границе крупного этапа или по явному запросу. Сохранённые
  full-suite отчёты историчны.
