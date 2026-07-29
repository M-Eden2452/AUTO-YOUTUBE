---
status: current
last_verified_commit: cfe6ae6
last_verified_date: 2026-07-29
source_paths:
  - pyproject.toml
  - ai_youtube
  - apps
  - anime_factory
  - src/ai_youtube/apps/video_repurposer/workflows/anime_clipper
  - src/ai_youtube/apps/legacy_pipeline
  - pipeline.py
  - src
  - tests
  - tests/test_anime_clipper_application_boundary.py
  - tests/test_legacy_pipeline_application_boundary.py
  - docs/adr/0011-anime-clipper-application-boundary.md
  - docs/adr/0012-legacy-pipeline-application-boundary.md
  - content
  - packages
  - docs/current/ARCHITECTURE_BOUNDARY_MAP.md
  - docs/handoff/PROJECT_RESCUE_MASTER_PLAN.md
---

# Cleanup Registry

Проверено 2026-07-29 по implementation HEAD `cfe6ae6`. Код и Git имеют приоритет.
Классификация означает целевое действие после указанного gate, а не действие
этапа 4.6. Подэтапы 6A–6G и provider consolidation этапа 7 выполнены bounded
изменениями; Fullscreen Voiceover, Story Card, Anime Clipper и legacy pipeline
slices этапа 8 также завершены. Runtime и user data не перемещались и не
удалялись.

Допустимые значения: `keep`, `split`, `merge`, `move`, `archive`, `delete`,
`do_not_touch`.

## Architecture candidates

| ID | Кандидат | Class | Фактическое evidence | Gate / целевое состояние | Этап |
|---|---|---|---|---|---|
| K01 | `ai_youtube/` + installed `ai-youtube` | `keep` | единственный script в `pyproject.toml`; dispatch только active app | сохранять public command contract | всегда |
| K02 | `src/production_catalog` + capabilities | `keep` | единственный честный registry active/planned apps и templates | не создавать второй catalog | всегда |
| K03 | `src/config_resolver` | `keep` | используется CLI, stores, providers, audio/subtitles и legacy adapters | единственный resolver, legacy read fallback сохраняется | всегда |
| K04 | `src/projects/ProjectRepository` | `keep` | читает `job.json` и `project.json`, ничего не пишет | единый read API; writers остаются у manifest owners | 5 |
| K05 | `src/assets/provider_contract.py` + `src/providers/` | `keep` | этап 7 (`fb93a05`) закрепил `StockProvider` canonical contract и перенёс default factory в `src.providers.registry`; adapters/download/preview/diagnostics используют общую foundation | единственный provider contract и registry | 7 complete |
| K06 | `src/audio/` | `keep` | approval, voice manifests, timeline и TTS manager защищены отдельными tests | не создавать второй voice/TTS contract | всегда |
| K07 | `src/subtitles/` | `keep` | единственный engine, news использует adapter | не создавать второй subtitle engine | всегда |
| K08 | `apps/*` wrappers | `keep` | `test_apps_structure`; внешние `python -m apps.*` entrypoints | compatibility до отдельного retirement evidence | 8–9 |
| S01 | `src/news/asset_manager.py` + `src/news/asset_*.py` | `split` | 6A (`cba1cf7`, `20750ab`, `59b39d3`, `fe5ba44`) оставил 266-строчный facade и отделил builder, summaries, completion и provider adapters | выполнено; public functions, imports и patch-points защищены characterization | 6A complete |
| S02 | CLI internals после canonical migration | `split` | 6B (`1f9495c`) оставил 81-строчный compatibility facade, разделил catalog/localization/authoring handlers и terminal presentation; diagnostics стал 78-строчным facade | выполнено; public command/output contract и старые patch-points защищены characterization | 6B complete |
| S03 | `src/content_creation/wizard.py` + `wizard_state`/`wizard_steps`/`wizard_presentation` | `split` | 6C (`b9f8212`) уменьшил facade с 1229 до 175 строк и разделил state/request translation, steps/execution и terminal presentation | выполнено; `run_wizard`, private compatibility imports, module request-builder patch-point и lazy CLI boundary защищены characterization | 6C complete |
| S04 | `src/content_creation/service.py` + use case modules | `split` | 6D (`8e087c7`) уменьшил facade с 878 до 123 строк, разделил Story Card/Fullscreen Voiceover use cases и явные fullscreen phases | выполнено; единый `create_content`, private imports, paid gate, tolerant resume и progress callback защищены characterization | 6D complete |
| S05 | `src/assets/semantic_visual_evaluation.py` + tooling/runtime modules | `split` | 6E (`8c89a67`) оставил 53-строчный facade и отделил offline dataset/metrics/reporting от controlled live execution/checkpoints | выполнено; public signatures, dataclass shapes, root-pipeline import и paid-call gates защищены characterization | 6E complete |
| S06 | `pipeline.py` + `src/legacy_pipeline` | `split` | 6F (`0d2cd67`) уменьшил root facade с 703 до 122 строк и разделил parser, maintenance handlers и legacy workflow | выполнено; старые imports, module patch-points, command/output contract и workspace resolution защищены characterization | 6F complete |
| S07 | `frame_sampling.py` + `perceptual_similarity.py` + `frame_primitives.py` | `split` | 6G (`802a54c`) вынес shared frame data/file hash/image hash primitives и устранил оба встречных static edges | выполнено; прежние public imports и visual-preview/temporal behavior защищены characterization | 6G complete |
| M01 | `NewsProjectStore.write_json` + `project_foundation.atomic_write_json` | `merge` | 5A (`87e272a`) подключил общий atomic primitive; 5B (`42d5b99`) добавил schema v1; 5C (`f7b3a3c`) добавил общий fail-fast project lock; 5D (`e3c90c3`) завершил output-validated idempotency | общий storage primitive и lock используются manifest owner; repeatable stages `research`–`export` проверяют обязательные outputs | 5 complete |
| M02 | public project API в `src/projects` и `src/project_foundation` | `merge` | read API уже общий, writer/models ещё разделены по persisted form | единый public API поверх двух tolerant forms; без третьей system | 5 |
| V00 | `src/content_creation/fullscreen_voiceover_use_case.py` | `move` | slice 8A (`f8ac67e`, `06e6a25`) перенёс implementation в `src.ai_youtube.apps.content_creator.workflows.fullscreen_voiceover`; service и `apps.news_to_short` используют canonical boundary | выполнено; старый import path — 29-строчный wrapper, `src.news` contracts не дублированы, service import остаётся lazy | 8A complete |
| V03 | `src/content_creation/story_card_use_case.py` | `move` | slice 8B (`01cfc6f`) перенёс implementation в `src.ai_youtube.apps.content_creator.workflows.story_card`; service использует canonical boundary | выполнено; старый import path — 12-строчный wrapper, project/evidence/template contracts не дублированы | 8B complete |
| V01 | `anime_factory/` | `move` | slice 8C (`7d0ce1e`) создал canonical lazy adapter в `src.ai_youtube.apps.video_repurposer.workflows.anime_clipper`; `apps.anime_factory` использует boundary, catalog остаётся disabled/planned | выполнено без физического move: legacy CLI, `EpisodePaths`, workflow/output layout и runtime остаются у `anime_factory` | 8C complete |
| V02 | root legacy engines (`asset_finder`, `music_*`, `thumbnail_*`, `layout_renderer`, `video_renderer`) | `move` | slice 8D (`cfe6ae6`) создал canonical lazy adapter в `src.ai_youtube.apps.legacy_pipeline`; `apps.youtube_pipeline` использует boundary, а characterization фиксирует root engine identities и patch-points | выполнено без физического move: root facade остаётся compatibility namespace owner, `src.legacy_pipeline` — behavior owner, engines/runtime не перемещены | 8D complete |
| A01 | historical audits/plans вне `docs/current` | `archive` | runtime imports отсутствуют; часть уже в `docs/archive` | сохранять историю, обновлять ссылки, не удалять без review | 10 |
| A02 | 9 tracked legacy файлов в `outputs/` | `archive` | пути всё ещё заданы config/root pipeline; сами outputs воспроизводимы не все | backup + manifest/reference check, затем untrack/archive | 10 |
| D01 | compatibility `PexelsAssetProvider`, `PixabayAssetProvider`, `UnsplashAssetProvider` в `src/news/asset_provider_adapters.py` | `delete` | этап 7 подтвердил отсутствие active/internal callers, но contract test всё ещё фиксирует re-export; default factory использует только `StockProvider` implementations из registry | сохранить до отдельного stage 9 retirement checkpoint | 9 |
| D02 | `src/news/stock_video_downloader.py` | `delete` | этап 7 удалил недостижимый raw-HTTP дубль и оставил 35-строчный public wrapper; characterization фиксирует delegation и два manifest outputs | удалить wrapper только после отдельного external/entrypoint check этапа 9 | 9 |
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
| D01 | active/internal callers нет; `asset_manager` re-export и contract test подтверждают продолжающийся compatibility promise | `src.providers.registry` создаёт `PexelsStockProvider`/`PixabayStockProvider`; Unsplash не active | этап 7 завершён без premature deletion; перед stage 9 delete повторить repo-wide `rg` и проверить внешний import period | `test_news_asset_manager_contract`, `test_asset_foundation_providers`, `test_news_to_short_provider_integration`, `test_news_to_short_assets` | manifest schema не менять; provider ids/provenance должны остаться прежними |
| D02 | внутренних callers нет; stage 7 оставил только public delegating function, которую теперь фиксирует characterization | `src.news.asset_manager.build_news_asset_manifest` через normal `asset_search` stage | отдельный stage 9 retirement checkpoint; удалить только после external/entrypoint recheck | `test_news_asset_manager_contract`, `test_news_to_short_assets`, `test_news_to_short_pipeline`, `test_stage1_characterization`, import smoke | не запускать download; существующие `assets_manifest.json` и downloaded media не менять |
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

### Завершённые bounded slices: 5D stage idempotency

- `research` (`56dd2eb`) проверяет обязательный `research/claims.json`: файл
  должен быть читаемым JSON-объектом со списком `claims`.
- `script` (`3abbfac`) проверяет локализованный `script/script.json`: файл
  должен быть читаемым JSON-объектом с непустыми `narration_text` и списком
  сцен-объектов.
- `visual_plan` (`40f3557`) проверяет локализованный
  `visual/visual_plan.json`: файл должен быть читаемым JSON-объектом с непустым
  списком сцен-объектов.
- Stage 5 closure (`e3c90c3`) добавил те же guarantees для `asset_search`,
  `voice`, `subtitles`, `preview_render`, `quality_check`, `final_render` и
  `export`. Обязательные declared audio/subtitle/render media также проверяются.
- Closure объединён в один commit по явному запросу владельца завершить весь
  этап 5 до этапа 6: изменение осталось в одной completeness boundary
  `NewsProjectStore`, одном production-файле и одной characterization matrix,
  без независимых schema/storage/dispatcher решений.
- Все повторяемые семейства от `research` до `export` защищены characterization
  для normal repeat, `resume`, `force-stage`, отсутствующего, структурно
  непригодного и повреждённого output.
- Pre-schema asset manifest, legacy voice/subtitle shapes и protected
  пользовательские субтитры остаются tolerant. `input` и потенциально сетевой
  `article_ingestion` не входят в автоматическую retry-policy ADR 0006.
- Manifest schema, lock policy, runtime projects и user media не менялись.

### Завершённый structural slice: 6A Asset manager

- Characterization commit `0515e02` зафиксировал пять публичных сигнатур,
  compatibility imports, пустой manifest shape и module-level factory patch-point.
- Чистые manifest summaries и video coverage вынесены в
  `src/news/asset_manifest_summaries.py` (`cba1cf7`).
- Scene completion/assembly и bounded targeted slot search вынесены в
  `src/news/asset_scene_completion.py` (`20750ab`).
- Existing provider search/download translation вынесена в
  `src/news/asset_provider_adapters.py` (`59b39d3`) без изменения
  `src.assets.provider_contract`.
- `src/news/asset_manager.py` оставлен 266-строчным compatibility facade;
  manifest orchestration разделён на короткие методы
  `src/news/asset_manifest_builder.py` (`fe5ba44`).
- Старые public/private imports и patch-points `load_dotenv`,
  `create_default_asset_providers`, `select_best_candidate` сохранены.
- Targeted verification: 181 tests OK, compile/import smoke OK. Full offline suite
  не запускался; сеть, provider download, TTS, Vision и render не выполнялись.
- Manifest schema, persisted projects, runtime/user media и
  `NewsProjectStore.validate_stage_output()` не менялись.

### Завершённый structural slice: 6B Внутренности CLI

- `tests/test_cli_internals_contract.py` зафиксировал signatures diagnostics
  facade, authoring patch-points и text validation output.
- `src/ai_youtube/cli/commands/diagnostics.py` уменьшен с 727 до 78 строк и
  оставлен compatibility facade.
- Catalog, localization/subtitles и script/visual-plan/run-stage handlers
  вынесены в отдельные domain-модули; terminal formatting вынесен в
  `src/ai_youtube/cli/presentation.py` (`1f9495c`).
- Public command set, JSON/text output, workspace resolution и legacy
  `create_content` patch-point сохранены.
- Targeted verification: 79 tests OK, compile/import smoke и safe capabilities
  smoke OK. Full offline suite, сеть, provider download, TTS, Vision и render
  не запускались.
- Schemas, persisted projects, runtime/user media и application service не
  менялись.

### Завершённый structural slice: 6C Wizard

- `tests/test_wizard_internals_contract.py` зафиксировал signatures и import
  surface Wizard facade, module-level `_build_request` patch-point и фактическую
  делегацию в split-модули.
- `src/content_creation/wizard.py` уменьшен с 1229 до 175 строк и оставлен
  compatibility facade с прежним `run_wizard`, prompt adapters и private
  imports.
- Working state и перевод через существующий общий request builder вынесены в
  `wizard_state.py`; terminal adapters/summaries/results — в
  `wizard_presentation.py`; шаги, resume/edit и execution orchestration — в
  `wizard_steps.py` (`b9f8212`).
- В split Wizard нет orchestration-функций длиннее 111 строк; application
  service, schema, persisted projects и lazy CLI → Wizard boundary не менялись.
- Targeted verification: 124 tests OK, compile/import checks OK. Full offline
  suite, сеть, provider download, TTS, Vision и render не запускались.

### Завершённый structural slice: 6D Application service

- `tests/test_content_creation_service_internals_contract.py` зафиксировал
  signatures/import surface service facade, dispatch patch-points, progress
  callback, безопасный no-script paid preflight и делегацию в use case-модули.
- `src/content_creation/service.py` уменьшен с 878 до 123 строк и оставлен
  единой точкой входа `create_content` для canonical CLI, compatibility CLI и
  Wizard.
- Story Card вынесен в `story_card_use_case.py`, Fullscreen Voiceover — в
  `fullscreen_voiceover_use_case.py`, общие progress/path helpers — в
  `service_support.py` (`8e087c7`).
- Бывшая 344-строчная fullscreen orchestration разделена на project setup,
  safe pipeline, voice/paid gate, draft completion, subtitles/music и
  render/export; longest method — 93 строки.
- Paid approval/preflight, existing-narration protection, resume/force-stage,
  two persisted project forms и progress callback сохранены.
- Targeted verification: 97 tests OK, compile/import checks OK. Full offline
  suite, сеть, provider download, TTS, Vision и render не запускались.

### Завершённый structural slice: 6E Semantic evaluation

- `tests/test_semantic_visual_evaluation_internals_contract.py` зафиксировал
  public signatures, dataset dataclass shapes, root `pipeline.py` caller и
  делегацию facade в split-модули.
- `src/assets/semantic_visual_evaluation.py` уменьшен с 1719 до 53 строк и
  оставлен public compatibility facade.
- Offline dataset loading, synthetic fixtures, metrics и report/comparison
  artifacts вынесены в `semantic_visual_evaluation_tooling.py`; controlled
  OpenAI runtime, authorization/budget limits, attempt caps и execution
  checkpoints — в `semantic_visual_evaluation_runtime.py` (`8c89a67`).
- 59 из 63 прежних top-level definitions перенесены AST-идентично; изменённые
  orchestration-функции разделены на helpers, longest function — 68 строк.
- Targeted verification: 30 tests OK, compile/import checks и diff check OK.
  Full offline suite, сеть, provider calls, Vision, TTS и render не запускались.

### Завершённый structural slice: 6F Legacy pipeline

- `tests/test_legacy_pipeline_internals_contract.py` зафиксировал сигнатуры и
  делегацию root facade, старые module-level patch-points и synthetic
  `--skip-render` orchestration без render/TTS/network.
- Root `pipeline.py` уменьшен с 703 до 122 строк; `main` — с 512 до 27 строк.
  Старые imports сохранены как compatibility surface для monkeypatch/callers.
- Неизменённый public parser вынесен в `src/legacy_pipeline/cli.py`;
  maintenance/diagnostic commands — в `maintenance.py`; legacy channel/video
  planning, render и evaluation orchestration — в `workflow.py` (`0d2cd67`).
- Split использует переданный namespace root facade, поэтому существующие
  patch-points продолжают управлять фактическими handlers без дублирования
  business logic. Самая длинная orchestration-функция — 77 строк.
- Targeted verification: 54 tests OK, compile/import checks и diff check OK.
  Full offline suite, сеть, provider calls/download, Vision, TTS и render не
  запускались.

### Завершённый structural slice: 6G Import cycles

- `tests/test_asset_import_boundaries.py` characterization-first зафиксировал
  прежние imports `SampledFrame`, `sha256_file` и `image_perceptual_hash`,
  package export `src.assets.SampledFrame` и image sampling/signature behavior.
- `SampledFrame`, file SHA-256 и perceptual image hash вынесены в минимальный
  `src/assets/frame_primitives.py` (`802a54c`).
- `frame_sampling.py` и `perceptual_similarity.py` теперь зависят только от
  shared primitive и больше не импортируют друг друга; старые public import
  paths сохранены re-export-ами.
- Targeted verification: 48 tests OK для import-boundary, visual-preview
  foundation/integration и temporal analysis; compile и diff checks OK.
  Full offline suite, сеть, provider calls/download, Vision, TTS и render не
  запускались.

### Завершённый structural slice: 7 Provider consolidation

- `src.assets.provider_contract.StockProvider` подтверждён единственным
  canonical contract; новый contract/provider layer не создавался.
- Default automatic provider factory и environment-enabled policy перенесены из
  news boundary в `src.providers.registry` (`fb93a05`).
- `src.news.asset_provider_adapters.create_default_asset_providers` сохранил
  прежний patch-point и делегирует registry; default set состоит только из
  полных `StockProvider` implementations.
- Общие `ProviderHttpClient`, provider diagnostics, download validation и
  license policy подтверждены как владельцы timeout/retry/rate-limit,
  diagnostics, technical download validation и license normalization.
- `src.news.stock_video_downloader` сокращён до 35-строчного compatibility
  wrapper; недостижимые private raw search/download helpers удалены.
- D01 legacy names и D02 public wrapper сохранены из-за подтверждённого
  compatibility surface и переоценены для отдельного retirement этапа 9.
- Targeted verification: 55 provider/asset tests и 23 pipeline/CLI tests OK,
  compile/import smoke и docs QA OK. Full offline suite, сеть, provider
  search/download, TTS, Vision и render не запускались.

### Завершённый vertical slice: 8A Fullscreen Voiceover boundary

- Characterization-first зафиксировал старый use-case import surface,
  signatures `create_news_to_short_job`/`run_news_to_short_job`,
  `NewsJob`/`NewsProjectStore` contract и `apps.news_to_short` delegation.
- Canonical application boundary создан в
  `src.ai_youtube.apps.content_creator.workflows.fullscreen_voiceover`
  (`f8ac67e`, `06e6a25`); 906-строчный use case перенесён без поведенческих
  изменений, package re-exports разрешаются лениво.
- `src.content_creation.service` использует canonical use case, а прежний
  `src.content_creation.fullscreen_voiceover_use_case` оставлен 29-строчным
  compatibility wrapper с теми же function objects и signatures.
- Boundary и `apps.news_to_short` переиспользуют существующие `NewsJob`,
  `NewsProject`, `NewsProjectStore`, `NewsPipelineResult` и create/run functions
  из `src.news`; второй project contract, writer или pipeline не создавался.
- Targeted verification: pre-change characterization 3 tests OK; boundary,
  service internals и apps 11 tests OK; service/news pipeline/project repository
  49 tests OK; compile/import/diff и docs QA OK. Full offline suite, сеть,
  provider search/download, TTS, Vision и render не запускались.
- Migration decision: ADR 0009. Persisted schemas, runtime projects и user media
  не менялись.

### Завершённый vertical slice: 8B Story Card boundary

- Characterization-first зафиксировал старый use-case import surface,
  `ProjectFactory`/`ProjectManifest`, Story Card integration result/signature и
  evidence manifest/record contracts.
- Canonical application boundary создан в
  `src.ai_youtube.apps.content_creator.workflows.story_card` (`01cfc6f`);
  реализация use case перенесена без поведенческих изменений.
- `src.content_creation.service` использует canonical use case, а прежний
  `src.content_creation.story_card_use_case` оставлен 12-строчным compatibility
  wrapper с теми же function objects и signatures.
- Boundary переиспользует существующие `ProjectFactory`,
  `ProjectCreationResult`, `ProjectManifest`, `EvidenceBundle`,
  `EvidenceRecord` и `src.templates.story_card` contracts; второй writer,
  schema, evidence bundle или renderer не создавался.
- Targeted verification: pre-change characterization 3 tests OK; boundary и
  service internals 9 tests OK; Story Card service/project/evidence/schema
  radius 75 tests OK; compile/import/content-comparison/diff checks OK. Full
  offline suite, сеть, provider search/download, TTS, Vision и render не
  запускались.
- Migration decision: ADR 0010. Persisted schemas, runtime projects и user media
  не менялись.

### Завершённый vertical slice: 8C Anime Clipper boundary

- Characterization-first зафиксировал signatures legacy `parse_args`,
  `run_pipeline` и `main`, `EpisodePaths` dataclass/output layout,
  `apps.anime_factory` delegation и planned/disabled catalog status.
- Canonical lazy adapter создан в
  `src.ai_youtube.apps.video_repurposer.workflows.anime_clipper` (`7d0ce1e`).
- Adapter переэкспортирует существующие workflow functions, `EpisodePaths`,
  `PROJECT_ROOT` и `get_episode_paths`; новой project schema, writer, renderer
  или output layout не создавалось.
- `apps.anime_factory` использует canonical boundary, а прямой
  `anime_factory.pipeline` CLI и module imports остаются совместимыми.
- Targeted verification: pre-change characterization 4 tests OK;
  boundary/CLI/catalog/apps 9 tests OK; Anime Factory path, cleanup, candidate,
  crop, transcript и selection radius 13 tests OK; compile/import/diff checks
  OK. Full offline suite, FFmpeg, render, transcription model, сеть и платные
  действия не запускались.
- Migration decision: ADR 0011. Runtime episodes и user media не менялись;
  `video_repurposer` остаётся planned/disabled.

### Завершённый vertical slice: 8D Legacy pipeline boundary

- Characterization-first зафиксировал root command/workflow signatures,
  `LegacyPipelineArtifacts` shape, engine function identities и
  `apps.youtube_pipeline` delegation.
- Canonical lazy adapter создан в
  `src.ai_youtube.apps.legacy_pipeline.adapter` (`cfe6ae6`).
- Adapter переэкспортирует существующие root `main`, parser, maintenance,
  channel/video workflow и `limit_scene_plan` contracts; нового dispatcher,
  project/artifact contract или engine не создавалось.
- `apps.youtube_pipeline` использует canonical boundary, а root `pipeline.py`
  и прямые `src.legacy_pipeline` imports остаются совместимыми.
- Targeted verification: pre-change characterization 4 tests OK;
  boundary/internals/Stage 1/apps 10 tests OK; workspace/catalog/semantic
  radius 23 tests OK; compile/import/diff checks OK. Full offline suite, сеть,
  provider calls/download, TTS, Vision и render не запускались.
- Migration decision: ADR 0012. Outputs, persisted projects, runtime layout и
  user media не менялись.

### Последующая очередь

1. **8:** documentary рассматривать только после read-only подтверждения
   реального рабочего шаблона; не включать planned capability по наличию
   legacy кода.
2. **9:** повторно проверить и удалять только D01/D02/D03 с актуальным
   zero-caller и compatibility evidence.
3. **10:** A01/A02/D04 и runtime dry-run; никаких user-data deletions.

## Closure rule

Registry закрывается только когда каждая строка:

- реализована отдельным проверенным commit;
- переведена в `keep`/`do_not_touch` с причиной;
- либо явно отложена с актуальным owner decision.

Исторический `docs/architecture/CLEANUP_INVENTORY.md` остаётся архивным
предшественником и не заменяет этот проверенный registry.
