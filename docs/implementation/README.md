# Implementation documentation

## Purpose

Этот каталог — **implementation evidence и история развития capabilities**: чем
обосновывался этап, что и когда было сделано, какие проверки выполнялись.

Он **не является**:

- текущим планом работ — это
  [PROJECT_EXECUTION_PLAN.md](../current/PROJECT_EXECUTION_PLAN.md);
- канонической картой архитектуры — это
  [SYSTEM_MAP.md](../current/SYSTEM_MAP.md) и [ADR](../adr/README.md);
- источником истины о текущем поведении кода.

При любом конфликте приоритет: фактический код и Git → [AGENTS.md](../../AGENTS.md)
→ документы `docs/current/` → ADR → материалы этого каталога.

Этот индекс только маршрутизирует к существующим документам и объясняет их
статус. Новых архитектурных решений он не принимает и ни один документ не
делает current.

## How to use this directory

1. Сначала прочитай `docs/current/` и ADR. Начинать отсюда нельзя.
2. Заходи сюда с конкретным вопросом «почему это устроено так» или «что
   проверялось на этом этапе», а не за инструкцией.
3. Любое утверждение отсюда проверяй по текущему коду и тестам до того, как на
   него опереться. Дата и commit внутри документа — момент его написания,
   а не подтверждение на текущем HEAD.
4. Ничего в этом каталоге не перемещай, не переименовывай и не удаляй: часть
   файлов — активные fixtures production и тестов (см. Known limitations).

## Status definitions

| Статус | Значение |
|---|---|
| `current` | Подтверждено текущим кодом, документами или тестами. |
| `historical` | Полезное свидетельство процесса или прежней реализации. **Не текущая инструкция.** |
| `superseded` | Заменено другим документом или решением; замена указана явно. |
| `unknown` | Достоверный статус пока не доказан. Документ читается как инструкция, но против текущего HEAD не проверялся. |

Сводка: `current` — 14 файлов, `historical` — 67, `superseded` — 0,
`unknown` — 15. Всего 96 tracked-файлов в 17 каталогах.

Пофайловая классификация всего каталога **не выполнена** и принадлежит
**PLAN-12B** (registry C27/C28). Статусы ниже — маршрутизация, а не эта
классификация.

## Capability index

### Configuration and paths

| Документ | Статус | Назначение |
|---|---|---|
| [config_resolver/CONFIG_MAP.md](config_resolver/CONFIG_MAP.md) | `unknown` | Карта «настройка → источники → приоритет → потребители», снятая по коду на коммите `66b2e13`. |

Canonical current owner: `src/config_resolver/`. Документ старше текущего HEAD
и как справочник по конфигурации не подтверждён.

### Assets, providers, search

| Каталог | Файлов | Статус | Назначение |
|---|---|---|---|
| [provider_foundation/](provider_foundation/) | 3 | `historical` | Plan/report/snapshot первого provider foundation: поиск, кандидаты, права, download, манифесты. |
| [provider_foundation_hardening/](provider_foundation_hardening/) | 7 | `historical` | Верификация и hardening того же foundation плюс выводы media-library migration tooling. |
| [documentary_asset_providers/](documentary_asset_providers/) | 6 | `historical` (5) · `unknown` (1) | Добавление Wikimedia Commons, NASA, Internet Archive и Envato Manual. `unknown` — [LICENSE_POLICY_DECISIONS.md](documentary_asset_providers/LICENSE_POLICY_DECISIONS.md), читается как действующая политика, но против HEAD не проверялась. |

Canonical current owner: `src/assets/provider_contract.py` и `src/providers/`
(единый `StockProvider` contract и canonical registry, ADR 0008). Списки
провайдеров и правил внутри отчётов — состояние на момент этапа.

### Visual retrieval

| Документ | Статус | Назначение |
|---|---|---|
| [visual_retrieval_repair/VISUAL_RETRIEVAL_MAP.md](visual_retrieval_repair/VISUAL_RETRIEVAL_MAP.md) | `unknown` | Карта пути «сцена → стратегия → provider-запросы → поиск» после ремонтного этапа Q2.1. |

Canonical current owner: `src/assets/scene_strategy.py` и
`src/assets/query_adapter.py`. Семья **PLAN-9B** активно меняет именно эту
область, поэтому карта устаревает раньше остальных.

### Semantic evaluation and Vision

| Каталог | Файлов | Статус | Назначение |
|---|---|---|---|
| [semantic_visual_foundation/](semantic_visual_foundation/) | 6 | `historical` (5) · `unknown` (1) | Foundation семантического reranking. `unknown` — [SEMANTIC_RESULT_SCHEMA.md](semantic_visual_foundation/SEMANTIC_RESULT_SCHEMA.md), описывает additive-поля `visual_review_manifest.json`. |
| [openai_semantic_backend/](openai_semantic_backend/) | 8 | `historical` (7) · `unknown` (1) | Disabled-by-default OpenAI backend и offline harness; readiness-проверки на 2026-07-23. `unknown` — [EVALUATION_DATASET_SCHEMA.md](openai_semantic_backend/EVALUATION_DATASET_SCHEMA.md). |
| [openai_live_evaluation/](openai_live_evaluation/) | 24 | **`current` (14)** · `historical` (10) | Единственный выполненный контролируемый платный live-прогон и его подготовленный датасет. |

Canonical current owner решения об отборе: `src/assets/semantic_selection/**` и
`src/assets/completion/`. Продуктовые границы Vision — раздел 8
[PRODUCT_PLAN.md](../current/PRODUCT_PLAN.md); wiring и активация —
PLAN-9C/9D/9E.

**`current` в `openai_live_evaluation` — это fixtures, а не инструкция.**
Активно читаются production и тестами:
[LIVE_EVAL_DATASET.json](openai_live_evaluation/LIVE_EVAL_DATASET.json),
`prepared_dataset/frames/**` (12 кадров) и
[results/LIVE_EVAL_RESULTS.json](openai_live_evaluation/results/LIVE_EVAL_RESULTS.json)
— из `src/assets/semantic_visual_evaluation_tooling.py`,
`tests/test_semantic_decision_policy.py` и
`tests/test_semantic_visual_evaluation.py`. Зависимость production от `docs/`
зафиксирована как дефект **C31** в
[CLEANUP_REGISTRY.md](../current/CLEANUP_REGISTRY.md); target owner решает
PLAN-13 по OD-8/OD-9. **Файлы не переносить и не untrack-ить.** Остальные
10 файлов — evidence платного прогона: отчёт, usage, checkpoints, sanitized
payloads, контактные листы.

### Preview and review bundles

| Каталог | Файлов | Статус | Назначение |
|---|---|---|---|
| [visual_preview_foundation/](visual_preview_foundation/) | 13 | `historical` (12) · `unknown` (1) | Foundation превью, сэмплирования кадров и перцептивного сходства; включает вывод CLI smoke-прогона. `unknown` — [REVIEW_BUNDLE_SCHEMA.md](visual_preview_foundation/REVIEW_BUNDLE_SCHEMA.md), описывает `assets/review/visual_review_manifest.json`. |

Canonical current owner: `src/assets/` (frame primitives, sampling, perceptual
similarity) и `src/news/asset_*.py`. `cli_smoke_projects/` — зафиксированный
вывод одного прогона, не рабочий проект.

### Audio, voice, localization

| Каталог | Файлов | Статус | Назначение |
|---|---|---|---|
| [global_adaptive_voice/](global_adaptive_voice/) | 5 | `unknown` (4) · `historical` (1) | Единый adaptive voice/narration foundation этапа 2D. `historical` — только [IMPLEMENTATION_REPORT.md](global_adaptive_voice/IMPLEMENTATION_REPORT.md). |
| [localization_voice/LOCALIZATION_VOICE_MAP.md](localization_voice/LOCALIZATION_VOICE_MAP.md) | 1 | `unknown` | Карта «настройка → ConfigResolver key → потребитель → runtime-результат» этапа D2/E2. |

Canonical current owner: `src/audio/` и `src/localization/`. Music ownership по
[SYSTEM_MAP.md](../current/SYSTEM_MAP.md) ещё требует консолидации 9B, поэтому
описания музыкального пути особенно ненадёжны.

[global_adaptive_voice/MIGRATION_NOTES.md](global_adaptive_voice/MIGRATION_NOTES.md)
— единственный документ каталога, на который ссылается production-комментарий
(`src/content_creation/capabilities.py:20`). Это ссылка на объяснение
оставшегося дублирования, а не подтверждение актуальности.

### Subtitles

| Документ | Статус | Назначение |
|---|---|---|
| [subtitle_engine/SUBTITLE_ENGINE_MAP.md](subtitle_engine/SUBTITLE_ENGINE_MAP.md) | `unknown` | Карта «источник текста → тайминг → нарезка → валидация → файл» этапа Q3. |

Canonical current owner: `src/subtitles/` — единственный subtitle engine.
Второй движок создавать запрещено ([AGENTS.md](../../AGENTS.md)).

### Projects, channels, evidence

| Каталог | Файлов | Статус | Назначение |
|---|---|---|---|
| [project_channel_evidence_foundation/](project_channel_evidence_foundation/) | 4 | `historical` (2) · `unknown` (2) | Foundation этапа 2B: channels, projects, evidence, per-channel output rules. `unknown` — [CLI_REFERENCE.md](project_channel_evidence_foundation/CLI_REFERENCE.md) и [DATA_MODEL.md](project_channel_evidence_foundation/DATA_MODEL.md). |

Canonical current owner: `src/project_foundation/` и `src/projects/`
(общий read API поверх `job.json` и `project.json`).

**Предупреждение.** `CLI_REFERENCE.md` учит `python -m src.project_foundation.cli`.
Канонический CLI — `python -m ai_youtube` (ADR 0007). Модуль
`src/project_foundation/cli.py` существует, но его роль относительно
канонического CLI этим документом не подтверждена — отсюда `unknown`, а не
`superseded`.

### Production catalog and templates

| Каталог | Файлов | Статус | Назначение |
|---|---|---|---|
| [production_catalog_foundation/](production_catalog_foundation/) | 4 | `historical` | Этап 2A: read-only каталог `Application → Format → Template → Export Target`. |

Canonical current owner: `src/production_catalog/`. Каталог экспорта, по
разделу 5 [PRODUCT_PLAN.md](../current/PRODUCT_PLAN.md), объявляет больше целей,
чем реально производится, — состав целей из отчёта этапа фактом не является.

### Story Card

| Каталог | Файлов | Статус | Назначение |
|---|---|---|---|
| [story_card_project_integration/](story_card_project_integration/) | 3 | `historical` (2) · `unknown` (1) | Этап 2C: подключение рендерера Story Card к project/channel foundation. `unknown` — [TEMPLATE_CONTRACT.md](story_card_project_integration/TEMPLATE_CONTRACT.md) (canonical `template_id` и legacy alias). |
| [story_card_adaptive_layout/](story_card_adaptive_layout/) | 1 | `historical` | Отчёт о переходе фирменного шаблона к адаптивной вёрстке (v1 → v2). |
| [story_card_product_validation/](story_card_product_validation/) | 8 | `historical` | Изолированный продуктовый прогон: калибровка, shadow ranking, temporal-тест, render-отчёт. |

Canonical current owner: `src/templates/story_card/`,
`src/production_plan/` и canonical application boundary
`src/ai_youtube/apps/content_creator/workflows/story_card/` (ADR 0010).

**Предупреждение.** Раздел 19.8 [PRODUCT_PLAN.md](../current/PRODUCT_PLAN.md)
фиксирует, что текущая реализация на MoviePy — временная, а Story Card
становится обязательным parity-case сравнительного PoC. Отчёты этого семейства
описывают именно ту реализацию, которая помечена как подлежащая замене.

## Known limitations

- Часть документов описывает **промежуточные стадии**: план писался до
  изменения кода, отчёт — сразу после, и оба фиксируют момент, а не итог.
- Большинство файлов **не проверено против current HEAD**. 15 документов
  читаются как инструкция, но подтверждения не имеют — они помечены `unknown`
  именно поэтому, а не потому, что они неверны.
- Этот индекс **не делает historical документы current** и не выдаёт разрешений
  на действия.
- Пофайловая классификация, перемещение данных из `docs/implementation` в
  versioned fixture owner и архивирование принадлежат **PLAN-12B/12C**
  (registry **C27**, **C28**). До них archive/move/delete любого файла этих
  семейств не выполняются.
- Каталог содержит **активные fixtures** (registry **C31**): удаление или
  перемещение файлов `openai_live_evaluation` ломает production-код и тесты.
- Одна входящая ссылка из production указывает на несуществующий документ:
  `src/content_creation/capabilities.py:355` ссылается на
  `docs/implementation/unified_content_cli/IMPLEMENTATION_REPORT.md`, которого
  в репозитории нет и никогда не было в Git-истории. Исправление принадлежит
  владельцу соответствующего кода, не этому индексу.
- В каталоге нет документов по UI/Wizard, финальному рендеру и legacy
  migration. Группы под них здесь не заведены, потому что материалов,
  подтверждающих такие группы, не существует.

## Related current documents

- [START_HERE.md](../current/START_HERE.md) — точка входа для агента.
- [SYSTEM_MAP.md](../current/SYSTEM_MAP.md) — текущие границы и владельцы.
- [PRODUCT_PLAN.md](../current/PRODUCT_PLAN.md) — продуктовое направление.
- [PROJECT_EXECUTION_PLAN.md](../current/PROJECT_EXECUTION_PLAN.md) — порядок
  работ и current checkpoint.
- [CLEANUP_REGISTRY.md](../current/CLEANUP_REGISTRY.md) — классификация
  кандидатов cleanup, включая C27, C28 и C31.
- [ADR index](../adr/README.md) — решения, меняющие контракты и границы.
- [docs/audits](../audits/) — независимые аудиты; происхождение решений
  ревизии 2.1 объясняет
  [CANONICAL_REVISION_2_1_INDEPENDENT_VERIFICATION_2026-08-01.md](../audits/CANONICAL_REVISION_2_1_INDEPENDENT_VERIFICATION_2026-08-01.md).
