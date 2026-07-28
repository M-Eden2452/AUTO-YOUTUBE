---
status: current
last_verified_commit: f7b3a3c
last_verified_date: 2026-07-28
source_paths:
  - pyproject.toml
  - ai_youtube
  - apps
  - anime_factory
  - pipeline.py
  - src
  - tests
  - content
  - packages
  - docs/current/ARCHITECTURE_BOUNDARY_MAP.md
  - docs/handoff/PROJECT_RESCUE_MASTER_PLAN.md
---

# Cleanup Registry

Проверено 2026-07-28 по implementation HEAD `f7b3a3c`. Код и Git имеют приоритет.
Классификация означает целевое действие после указанного gate, а не действие
этапа 4.6. На этом этапе production code, runtime и user data не перемещались и
не удалялись.

Допустимые значения: `keep`, `split`, `merge`, `move`, `archive`, `delete`,
`do_not_touch`.

## Architecture candidates

| ID | Кандидат | Class | Фактическое evidence | Gate / целевое состояние | Этап |
|---|---|---|---|---|---|
| K01 | `ai_youtube/` + installed `ai-youtube` | `keep` | единственный script в `pyproject.toml`; dispatch только active app | сохранять public command contract | всегда |
| K02 | `src/production_catalog` + capabilities | `keep` | единственный честный registry active/planned apps и templates | не создавать второй catalog | всегда |
| K03 | `src/config_resolver` | `keep` | используется CLI, stores, providers, audio/subtitles и legacy adapters | единственный resolver, legacy read fallback сохраняется | всегда |
| K04 | `src/projects/ProjectRepository` | `keep` | читает `job.json` и `project.json`, ничего не пишет | единый read API; writers остаются у manifest owners | 5 |
| K05 | `src/assets/provider_contract.py` + `src/providers/` | `keep` | общий contract импортируют adapters, download, preview и asset manager | единственный provider contract | 7 |
| K06 | `src/audio/` | `keep` | approval, voice manifests, timeline и TTS manager защищены отдельными tests | не создавать второй voice/TTS contract | всегда |
| K07 | `src/subtitles/` | `keep` | единственный engine, news использует adapter | не создавать второй subtitle engine | всегда |
| K08 | `apps/*` wrappers | `keep` | `test_apps_structure`; внешние `python -m apps.*` entrypoints | compatibility до отдельного retirement evidence | 8–9 |
| S01 | `src/news/asset_manager.py` | `split` | 2119 строк; orchestration, search, download, ranking и completion в одном module | разделить по 6A, сохранив public functions/adapters | 6A |
| S02 | `src/content_creation/cli.py` | `split` | 1208 строк; parsing, presentation и command handlers | parser/public commands неизменны; handlers/presentation разделяются | 6B |
| S03 | `src/content_creation/wizard.py` | `split` | 1229 строк; adapters, state, steps и presentation | сохранить `run_wizard` и request builder | 6C |
| S04 | `src/content_creation/service.py` | `split` | 878 строк; два workflow и paid preflight в одном module | use cases внутри одного application service | 6D |
| S05 | `src/assets/semantic_visual_evaluation.py` | `split` | 1719 строк; offline metrics/report и controlled live execution вместе | отделить evaluation tooling от runtime backend без второго engine | 6E |
| S06 | `pipeline.py` | `split` | 703 строки и imports множества legacy/diagnostic domains | оставить тонкий dispatch facade; выносить по одному handler family | 6F |
| S07 | `frame_sampling.py` ↔ `perceptual_similarity.py` | `split` | подтверждены два static edges, один из них lazy | вынести shared data/hash primitive и убрать cycle одним slice | 6G |
| M01 | `NewsProjectStore.write_json` + `project_foundation.atomic_write_json` | `merge` | 5A (`87e272a`) подключил общий atomic primitive; 5B (`42d5b99`) добавил schema v1; 5C (`f7b3a3c`) добавил общий fail-fast project lock | stage idempotency остаётся отдельным slice 5D | 5A–5C complete |
| M02 | public project API в `src/projects` и `src/project_foundation` | `merge` | read API уже общий, writer/models ещё разделены по persisted form | единый public API поверх двух tolerant forms; без третьей system | 5 |
| V01 | `anime_factory/` | `move` | отдельный рабочий CLI/workflow; catalog app `video_repurposer` disabled | переносить целиком через adapter с old entrypoint | 8 |
| V02 | root legacy engines (`asset_finder`, `music_*`, `thumbnail_*`, `layout_renderer`, `video_renderer`) | `move` | вызываются `pipeline.py` и защищены documentary/channel tests | переносить только как legacy vertical slice с wrappers | 8 |
| A01 | historical audits/plans вне `docs/current` | `archive` | runtime imports отсутствуют; часть уже в `docs/archive` | сохранять историю, обновлять ссылки, не удалять без review | 10 |
| A02 | 9 tracked legacy файлов в `outputs/` | `archive` | пути всё ещё заданы config/root pipeline; сами outputs воспроизводимы не все | backup + manifest/reference check, затем untrack/archive | 10 |
| D01 | embedded `PexelsAssetProvider`, `PixabayAssetProvider`, `UnsplashAssetProvider` | `delete` | repo-wide Python search находит только определения; factory использует `*StockProvider` из `src/providers` | удалить отдельным diff после повторного zero-caller check | 7/9 |
| D02 | `src/news/stock_video_downloader.py` | `delete` | repo-wide search находит только собственные функции; public function уже delegates в `build_news_asset_manifest` | удалить после compatibility check; canonical replacement — news asset stage/manager | 7/9 |
| D03 | `packages/README.md` и пустая planning directory | `delete` | нет runtime imports; только historical docs references; packaging идёт из `src*` по `pyproject.toml` | удалить directory и исправить исторически-необязательные current links, если появятся | 9 |
| D04 | untracked `__pycache__/`, `*.pyc` | `delete` | 0 tracked matches; bytecode воспроизводим | удалять только filesystem-cleanup slice, не вместе с refactor | 10 |
| N01 | `.env`, `.env.*`, credentials/private keys | `do_not_touch` | конфигурация может содержать secrets; содержимое не проверялось | никогда не читать/коммитить/удалять автоматически | всегда |
| N02 | `projects/`, manifests, MP4/WAV, evidence/license proof | `do_not_touch` | 1618 файлов, 0 tracked; оба project readers используют root | только copy → verify → switch по отдельному разрешению | всегда |
| N03 | `assets/`, `manual_assets/`, `music/`, voice samples | `do_not_touch` | runtime/config callers и rights-sensitive user media | backup/checksums до любой миграции; не удалять автоматически | всегда |
| N04 | `content/`, включая `story_card_jobs.tsv` | `do_not_touch` | TSV не имеет runtime caller, но каталог содержит versioned legacy source content | отсутствие caller не доказывает право удалить user/source data | всегда |
| N05 | `project_solar_vs_nuclear/` | `do_not_touch` | 102 runtime/experiment файла, 0 tracked | сохранять до отдельного owner decision | всегда |
| N06 | `MOSS_TTS_Nano/`, `venv/` | `do_not_touch` | локальные toolchain roots, 0 tracked; MOSS вызывается legacy provider | не переносить/удалять в архитектурном slice | всегда |

## Delete evidence

Удаление возможно только отдельным bounded commit после повторной проверки.

| ID | Callers/imports | Рабочая замена | Compatibility period | Targeted verification | Persisted/media risk |
|---|---|---|---|---|---|
| D01 | внутренних callers нет; имена встречаются только в строках `class` | `PexelsStockProvider`, `PixabayStockProvider`; Unsplash не зарегистрирован как active provider, raw helper остаётся только до provider review | сохранить до provider-consolidation checkpoint; перед delete повторить repo-wide `rg` и проверить external API/export absence | `test_asset_foundation_providers`, `test_news_to_short_provider_integration`, `test_news_to_short_assets`, Stage 1 characterization | manifest schema не менять; provider ids/provenance должны остаться прежними |
| D02 | внутренних callers нет; module импортирует manager, обратного import нет | `src.news.asset_manager.build_news_asset_manifest` через normal `asset_search` stage | один отдельный compatibility checkpoint этапа 7; удалить только если entrypoint/docs/tests не появились | `test_news_to_short_assets`, `test_news_to_short_pipeline`, `test_stage1_characterization`, import smoke | не запускать download; существующие `assets_manifest.json` и downloaded media не менять |
| D03 | runtime/import callers нет; только исторические docs | `pyproject.toml` уже package-discovery из `ai_youtube*`, `src*`, `anime_factory*`, `apps*` | не требуется для runtime; отдельный docs-only cleanup commit | `tools.qa.check_agent_docs`, `test_stage2_agent_onboarding`, package discovery smoke | отсутствует |
| D04 | 0 tracked files; interpreter cache only | Python воспроизводит cache | не требуется; только после проверки абсолютного target path | `git status --short`, ближайший targeted test изменённой области | не затрагивать source, venv, projects или media |

Если новый caller, external compatibility promise или persisted dependency
обнаружены, class меняется с `delete` на `keep`/`archive` до нового evidence.

## Очередь implementation slices

Каждый пункт — отдельный characterization-first diff, targeted tests, commit и
handoff. Порядок не разрешает перепрыгивать через незавершённый rescue stage.

### Завершённый structural slice: 5A atomic NewsProjectStore

- Изменённый production-файл: `src/news/project_store.py`.
- Переиспользован contract без нового writer:
  `src/project_foundation/storage.py::atomic_write_json`.
- Characterization в `tests/test_news_to_short_models.py` подтверждает: прежний
  JSON shape/UTF-8/newline сохраняется, запись проходит через atomic replacement
  и temporary file не остаётся.
- Callers для regression review:
  `src/news/pipeline.py`, `src/content_creation/service.py`,
  `src/audio/voice_cli.py`, `src/assets/completion/replacement.py`.
- Targeted tests завершены:
  `tests.test_news_to_short_models`, `tests.test_project_repository`,
  `tests.test_news_to_short_pipeline` — 22 tests, OK.
- Lock/idempotency/schema version не добавлялись; persisted `job.json` не
  переписывались.

### Завершённый structural slice: 5B additive news schema version

- Изменённые contract-файлы: `src/news/models.py` и
  `schemas/job.schema.json`.
- `NEWS_JOB_SCHEMA_VERSION=1`; новые `NewsJob.to_dict()` payloads содержат
  обязательное integer-поле `schema_version`.
- Legacy `job.json` без версии загружается как v1 через существующий
  `NewsJob.from_dict`; отдельный reader и массовая миграция не создавались.
- Characterization:
  `tests/test_news_to_short_models.py`, `tests/test_artifact_schemas.py`.
- Ближайшие regression consumers:
  `tests/test_project_repository.py`, `tests/test_news_to_short_pipeline.py`.
- Migration note и решение публичного persisted contract:
  `docs/adr/0004-news-job-schema-version.md`.
- Project lock и stage idempotency не добавлялись; persisted/runtime manifests
  не изменялись.

### Завершённый structural slice: 5C news project lock

- Изменённые production-файлы: `src/project_foundation/storage.py` и
  `src/news/project_store.py`.
- Общий `project_lock` использует атомарное создание `.project.lock` через
  `O_CREAT | O_EXCL`; активный lock приводит к fail-fast `ProjectLockError`.
- Stale-lock policy: lock моложе или равный 300 секундам считается активным;
  более старый lock перехватывается автоматически по filesystem mtime.
  Owner token не позволяет старому writer удалить lock нового владельца.
- `NewsProjectStore.write_json` определяет корень news-проекта по `job.json` и
  держит project lock на время существующей atomic JSON write boundary.
- Characterization в `tests/test_news_to_short_models.py` подтверждает active
  lock denial, stale reclaim, прежний JSON format и отсутствие lock/tempfile
  после успешной записи.
- Targeted tests завершены:
  `tests.test_news_to_short_models`, `tests.test_project_repository`,
  `tests.test_news_to_short_pipeline`, `tests.test_project_factory` — 37 tests,
  OK.
- Manifest schemas и runtime projects не изменялись; lock не является
  stage-транзакцией и не добавляет idempotency.

### Последующая очередь

1. **Следующий slice 5D — stage idempotency:** один stage family за diff, с resume/force-stage
   characterization.
2. **6A–6G:** выполнять registry entries S01–S07 по одному подэтапу в порядке
   master plan; public imports сохранять adapters.
3. **7:** консолидировать callers на K05, затем отдельно переоценить D01/D02.
4. **8:** переносить V01/V02 только вертикальными slices с compatibility wrappers.
5. **9:** удалять только entries со статусом `delete` и актуальным evidence.
6. **10:** A01/A02/D04 и runtime dry-run; никаких user-data deletions.

## Closure rule

Registry закрывается только когда каждая строка:

- реализована отдельным проверенным commit;
- переведена в `keep`/`do_not_touch` с причиной;
- либо явно отложена с актуальным owner decision.

Исторический `docs/architecture/CLEANUP_INVENTORY.md` остаётся архивным
предшественником и не заменяет этот проверенный registry.
