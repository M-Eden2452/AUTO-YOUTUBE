---
status: current
last_verified_commit: 9f3ddba
last_verified_date: 2026-07-29
source_paths:
  - pyproject.toml
  - .github/workflows/offline-tests.yml
  - src/runtime_network.py
  - tests/test_runtime_network_boundary.py
  - ai_youtube
  - src/ai_youtube/cli
  - src/config_resolver/paths.py
  - src/content_creation/capabilities.py
  - src/content_creation/wizard.py
  - src/content_creation/wizard_state.py
  - src/content_creation/wizard_steps.py
  - src/content_creation/wizard_presentation.py
  - src/content_creation/service.py
  - src/content_creation/service_support.py
  - src/content_creation/story_card_use_case.py
  - src/content_creation/fullscreen_voiceover_use_case.py
  - src/ai_youtube/apps/content_creator/workflows/fullscreen_voiceover
  - src/ai_youtube/apps/content_creator/workflows/story_card
  - src/ai_youtube/apps/video_repurposer/workflows/anime_clipper
  - src/ai_youtube/apps/legacy_pipeline
  - apps/anime_factory
  - apps/youtube_pipeline
  - anime_factory
  - src/assets/semantic_visual_evaluation.py
  - src/assets/semantic_visual_evaluation_runtime.py
  - src/assets/semantic_visual_evaluation_tooling.py
  - src/assets/frame_primitives.py
  - src/assets/frame_sampling.py
  - src/assets/perceptual_similarity.py
  - src/assets/provider_contract.py
  - pipeline.py
  - src/legacy_pipeline
  - src/news/models.py
  - src/news/asset_manager.py
  - src/news/asset_manifest_builder.py
  - src/news/asset_manifest_summaries.py
  - src/news/asset_scene_completion.py
  - src/news/asset_provider_adapters.py
  - src/news/project_store.py
  - src/project_foundation/storage.py
  - src/providers/registry.py
  - src/audio
  - src/music_engine.py
  - src/music_finder.py
  - src/music_tools.py
  - src/production_plan/youtube_shorts.py
  - src/production_plan/solar_vs_nuclear_render.py
  - src/production_catalog
  - src/projects
  - schemas/job.schema.json
  - docs/adr/0004-news-job-schema-version.md
  - docs/adr/0005-news-project-lock.md
  - docs/adr/0006-news-stage-idempotency.md
  - docs/adr/0007-canonical-cli-package.md
  - docs/adr/0008-canonical-provider-registry.md
  - docs/adr/0009-fullscreen-voiceover-application-boundary.md
  - docs/adr/0010-story-card-application-boundary.md
  - docs/adr/0011-anime-clipper-application-boundary.md
  - docs/adr/0012-legacy-pipeline-application-boundary.md
  - docs/adr/0013-documentary-migration-gate.md
  - docs/adr/0014-retire-news-provider-class-compatibility.md
  - docs/adr/0015-retire-news-stock-downloader.md
  - docs/adr/0016-two-engine-product-architecture.md
  - tests/test_news_asset_manager_contract.py
  - tests/test_cli_internals_contract.py
  - tests/test_wizard_internals_contract.py
  - tests/test_content_creation_service_internals_contract.py
  - tests/test_semantic_visual_evaluation_internals_contract.py
  - tests/test_legacy_pipeline_internals_contract.py
  - tests/test_asset_import_boundaries.py
  - tests/test_news_stage_idempotency.py
  - tests/test_fullscreen_voiceover_application_boundary.py
  - tests/test_story_card_application_boundary.py
  - tests/test_anime_clipper_application_boundary.py
  - tests/test_legacy_pipeline_application_boundary.py
  - tests/test_documentary_migration_gate.py
  - docs/current/ARCHITECTURE_BOUNDARY_MAP.md
  - docs/current/CLEANUP_REGISTRY.md
  - docs/handoff/PROJECT_RESCUE_MASTER_PLAN.md
  - skills/review-change
  - .claude/agents/review-change.md
---

# Current State

Проверено 2026-07-29 от clean HEAD `9f3ddba`; факты ниже дополнительно проверены и обновлены 2026-08-05 от `68acdb2` docs-only reconciliation слайсом. Код и Git имеют приоритет.

Активный порядок задаёт [PROJECT_EXECUTION_PLAN.md](PROJECT_EXECUTION_PLAN.md); PLAN-6E завершён 2026-08-02.
Canonical policy — `skills/review-change/SKILL.md`; тонкие adapters не дублируют её. Controlled Cases A/B/C приняли safe изменения и нашли synthetic BLOCKER; после lock repair repositories byte-stable.
PLAN-9B-PRODUCER completed 2026-08-02: bounded offline producer заполняет существующий `VisualBrief` из structured/script/claim evidence, author override остаётся последним, unknown fail closed; schema/layout и query owner не менялись. Owner decision 2026-08-05 открыл «POST-AUDIT STABILIZATION PROGRAM»: PLAN-9B-2 deferred за stabilization gate. PLAN-STAB-1 completed 2026-08-05 (commit `f0b69db`) — финальный мастер пишется во временный файл рядом с целью, проверяется каноническим `ffprobe_media_info` и занимает свой путь через `os.replace`, поэтому готовый ролик переживает сбой render, validation и замены; independent review выполнен, verdict ACCEPT WITH MINOR; commit pushed. PLAN-STAB-2 completed 2026-08-05 (commit `0eea5be`) — `run_news_to_short_job` (`src/news/pipeline.py`) пропускает уже завершённый `final_render` и на explicit `stage=` пути диспетчеризации (используемом production render/export фазой на каждом resume), не только на общем `resume=True` пути; существующий `--force-stage`/`ExecutionFlags.force_stage` контракт довязан в тот же вызов и по-прежнему пересобирает final_render; missing/invalid artifact остаётся обязанностью уже действующего `NewsProjectStore.is_stage_completed` (ADR 0006); independent review выполнен, verdict ACCEPT; commit pushed. PLAN-STAB-3 completed 2026-08-05 (commit `9222519`) — `tests/network_guard.py` получил `network_guard_scope()`, восстанавливающий guard к состоянию до входа в scope вместо безусловного uninstall, устранив утечку в 9 call sites трёх owning test-модулей; `src/audio/tts/env.py::load_elevenlabs_env` больше не даёт локальному `.env` заменить test-owned fake `ELEVENLABS_API_KEY`, когда `tests/__init__.py` заранее установил test isolation lock; production override=True semantics вне test isolation не менялись; independent review выполнен, verdict ACCEPT WITH MINOR; commit pushed. Review PLAN-STAB-1/2/3 — owner-provided external review evidence; отдельного review-commit в Git это не оставляет. PLAN-STAB-4 implementation completed 2026-08-06 — новый canonical owner `src/runtime_network.py` делает runtime-сеть fail-closed по умолчанию: `ContextVar` со значением `DENY_ALL`, явное поимённое разрешение классов `provider_search`, `asset_download`, `preview_download`, `article_fetch` и `voice_preflight`, проверка `require_network` до первого socket/HTTP. Enforcement стоит в `src/assets/http_client.py` (`get_json`/`download_stream`), `src/assets/visual_preview.py`, `src/news/article_ingestor.py` и `src/audio/tts/elevenlabs_provider.py` (`preflight`/`list_voices`); пять сетевых провайдеров не менялись, потому что все ходят через общий `ProviderHttpClient`, и второй guard на провайдера не создавался. Разрешение выдаётся один раз в `create_content` из поля `network` запроса; запрос собирает общий request builder одинаково для CLI (`--allow-network`, повторяемый, без wildcard) и Wizard (явный шаг подтверждения перечисляет ровно нужные прогону классы). Наличие API-ключа, включённый по умолчанию keyless-провайдер, `--approve-paid-generation`, `--resume` и `--force-stage` разрешением не являются; `--dry-run` и `--prepare-only` остаются offline. Network approval и paid approval разделены: платный POST ElevenLabs по-прежнему принадлежит существующему hash-bound `VoiceApproval` и gates в `narration_workflow`/`TTSProviderManager`. Принятые residual risks: OpenAI Vision остаётся под собственным `VisionBudgetGuard` и config-defaults `enabled:false`/`allow_paid_vision:false`; legacy `pipeline.py --provider-diagnostics --live` и `pipeline.py --voice-action preflight/audition` становятся fail-closed без собственного approval-флага — это намеренное default-deny для путей вне канонического workflow. Independent review выполнен (commit `0947e51`), verdict **ACCEPT WITH MINOR** (GitHub Actions run `31053545804`, job `offline-tests / unittest` — success, `Ran 1623 tests in 329.132s`, `OK (skipped=6)`, failures=0, errors=0); commit pushed; blocking gate пункт 4 для PLAN-9B-2 satisfied. Два findings review — non-blocking residual evidence, не исправлены этим слайсом: `tests/test_runtime_network_boundary.py:324-329` содержит тавтологический assertion вместо полной проверки denial → readiness, а `wizard_presentation.py` показывает неполную информационную сводку сетевых действий и не использует `required_network_actions()`. PLAN-STAB-5 (C50 rights-review preservation) completed 2026-08-06, independently reviewed, verdict **ACCEPT** (findings: нет), GitHub Actions run `31084873522` — offline suite зелёный (`Ran 1646 tests in 273.522s`, `OK (skipped=6)`, failures=0, errors=0), CI headSha == HEAD == `origin/governance-reset`, worktree clean; blocking gate пункт 5 satisfied. Canonical rights owner `src/assets/license_policy.py` больше не снимает уже записанное `review_required=True`: требование ревью monotonic, учитываются все фактически присутствующие представления записи (корневой флаг, копия внутри `license`, сохранённый `policy_decision`), одного `True` достаточно, отсутствующее представление разрешением не является; блокировка получает причину `record_review_required`, обнуляет `allowed_for_render` и даёт статус `blocked`. Снимает требование только подтверждённая per-asset `rights_declaration` через существующий `_manual_declaration_is_confirmed`. Два merge owner на той же live-цепочке довязаны, чтобы флаг вообще доходил до политики: `rank_local_assets` (`src/news/asset_manifest_builder.py`) переносит `review_required` записи медиатеки в ranked item, а `with_policy_decision` (`src/news/asset_provider_adapters.py`) не теряет флаг, записанный рядом с лицензией, а не внутри неё. Owner decision 2026-08-06 принял намеренный safety trade-off: происхождение требования политика не выясняет, потому что сохранённая запись не позволяет отличить флаг оператора от прошлого ответа самой политики — комбинация «`review_required=True` + чужой `policy_decision`» реально производится `media_library._propose_media_record` и персистится `migrate_media_library` мимо `_normalize_asset`, а manifest-ассет всегда несёт `policy_decision`. Цена принята явно: policy re-evaluation, дозаполнение metadata, resume и rebuild могут установить `True`, но сами по себе ревью больше не снимают — ассет остаётся заблокированным до подтверждения владельца. Это контракт, а не открытый дефект. Новых полей, schema version, rights vocabulary, CLI и Wizard-изменений слайс не вносит; `config/license_policy.json` и `modes.blocking_reasons` не менялись; миграция манифестов не требуется. Evidence: targeted 23 OK, regression radius 204 OK, полный offline suite 1646 tests OK, docs QA 0, scope-check OK, `git diff --check` 0; сеть, provider API, download, Vision, TTS и реальный `.env` не использовались. Stabilization gate целиком не закрыт: пункт 5 satisfied, пункты 6–8 остаются открытыми. Owner decision 2026-08-06 утвердил активный execution route после PLAN-STAB-5: PLAN-STAB-9 (shared rights vocabulary owner, non-blocking follow-up для PLAN-9B-2) → PLAN-STAB-7 + PLAN-STAB-8 → PLAN-STAB-6 или явное residual-risk decision → stabilization review → PLAN-9B-2; это owner-prioritized порядок, а не переопределение blocking gate. Новый current checkpoint — **PLAN-STAB-9**. PLAN-STAB-9 (shared rights vocabulary owner) implementation completed 2026-08-06, **independent review pending**; checkpoint остаётся PLAN-STAB-9 до закрытия review, PLAN-STAB-7/PLAN-STAB-8 до этого не начинаются. Словарь допустимых `rights_status` получил единственного владельца `src/assets/models.py`: семь именованных `RIGHTS_*` и immutable `RIGHTS_ALLOWED_STATUSES` (`frozenset` из `user_owned`, `licensed`, `creative_commons`, `public_domain`). Удалена независимая копия того же списка — mutable set `ALLOWED_RENDER_RIGHTS` в `src/news/models.py` вместе с локальными объявлениями `RIGHTS_*`; значения до слайса совпадали, но гарантии этого не было, а расходиться первым мог именно news-набор, считающий `allowed_for_render` для медиатеки и результатов провайдеров. Consumers `src/news/asset_manifest_builder.py` и `src/news/asset_provider_adapters.py` переведены на прямой импорт из canonical owner; `completion/modes.py` сохраняет единственное санкционированное расширение `cleared`, теперь именованное `RIGHTS_LEGACY_CLEARED` в самом owner и намеренно не входящее в canonical набор. Обратная совместимость сохранена целиком: все семь исторических `RIGHTS_*` и `ALLOWED_RENDER_RIGHTS` по-прежнему импортируются из `src.news.models` как compatibility re-exports, причём alias — тот же объект, что canonical `frozenset`, а не равная копия; ни один существующий importer не менялся. Подтверждённый invariant: словарь задаёт только написание статуса и разрешением сам по себе не является — неизвестный, пустой и отсутствующий status fail-closed, `review_required=True` и `allowed_for_render=False` блокируют canonical status, подтверждённая `rights_declaration` не разрешает структурно неполный asset, PLAN-STAB-5 monotonic review сохранён, round-trip не меняет значение статуса, legacy manifest читается и остаётся fail-closed. Evidence: новый owning-модуль `tests/test_rights_status_vocabulary.py` (21 test OK) с divergence-тестом — identity alias и каждого re-export плюс AST-проверка исходника `src/news/models.py` на отсутствие второго set/frozenset словаря (отдельно проверено, что guard падает на всех четырёх формах возврата копии); regression radius 257 OK; docs QA 0; scope-check OK; `git diff --check` 0; сеть, provider API, download, Vision, TTS и реальный render не использовались. `config/license_policy.json`, schema version, persisted поля, CLI, Wizard, provider APIs и network boundary не менялись; миграция манифестов не требуется; словарь не расширялся. Принятые residual risks: (1) `completion/modes.py` приводит вход к lower-case, а `news`-consumers и `AssetLicense` сравнивают строку как есть — расхождение нормализации, на живых данных не проявляется, так как все производители пишут lower-case, а унификация была бы семантическим изменением gate; (2) `AssetLicense.from_dict` / `AssetCandidate.from_dict` не переносят корневой `review_required` во вложенную лицензию — вне contract этого слайса, живой render-gate читает сырой dict и корневой флаг видит; (3) `ALLOWED_RENDER_RIGHTS` остаётся compatibility alias без собственного retirement gate; (4) `RIGHTS_EDITORIAL_REVIEW_REQUIRED` и `RIGHTS_BLOCKED` импортёров не имеют и перенесены как есть. Отдельно зафиксировано характеризацией: в news-пути вердикт словаря промежуточный — `rank_provider_results` передаёт кандидата в `with_policy_decision`, и license policy перезаписывает rights-поля, включая сам `rights_status`; это то же поведение, что CLEANUP_REGISTRY записывает как C40, и словарь авторитетом рендера не является. Stabilization gate целиком не закрыт. CI repair (commits `9f9b6f2`, `bcf6c2a`, `8ca755f`, `68acdb2`, trailer `Plan-Step: PLAN-STAB-16`) вернул `.github/workflows/offline-tests.yml` в зелёное состояние: GitHub Actions run `31039985187`, job `offline-tests / unittest` — success, 1/1 checks, failures=0, errors=0; локальный полный offline suite — 1589 тестов, OK. Работа выполнена по прямому owner decision как срочный bounded end-to-end repair; исходный scope был расширен владельцем после появления новых подтверждённых CI failures — это authorized расширение, а не самовольное. Готовые видео, пользовательские проекты, downloaded assets и project outputs в Git не добавлялись; тест, ранее ссылавшийся на personal-machine fixture, теперь генерирует synthetic temporary MP4. PLAN-STAB-16 частично выполнена: первая часть (reproducible green offline CI baseline) завершена этими четырьмя commits; secret scan, dependency audit, lint baseline, type-check baseline и остальные подпункты остаются pending/non-blocking для PLAN-9B-2. Остальные PLAN-STAB-слайсы, кроме частично выполненного PLAN-STAB-16, не начинались; для PLAN-STAB-7 выполнен только factual routing repair current docs, completed он не объявлен. `.claude/skills/` отсутствует.

- Rescue stages 0–8, включая подэтапы 6A–6G, завершены. Этап 8 перенёс
  vertical slices `fullscreen_voiceover`, `story_card`, `anime_clipper` и
  legacy pipeline. Gate 8E проверил documentary/fixed-plan paths и закрыл
  кандидат без migration: реального catalog template и безопасной application
  boundary нет.
  Product Evidence Gate 4.5 сохранён только как
  историческая диагностика и решением владельца снят с critical path;
  Product Repair 4.5-R закрыт без продолжения.
- Этап 9A завершён тремя bounded deletion slices. D01 после повторного repo-wide
  zero-caller audit удалил news-only `PexelsAssetProvider`,
  `PixabayAssetProvider`, `UnsplashAssetProvider` и их re-exports.
  `AssetProvider`, news factory patch-point и canonical `StockProvider`
  implementations сохранены. D02 также завершён: standalone downloader wrapper
  удалён после отдельного AST callers/entrypoint gate; active asset stage не
  менялся. D03 удалил только `packages/README.md` и подтверждённо пустую
  planning directory после package/docs gate; package discovery не менялся.
  После owner review общий этап 9 расширен подэтапами 9B–9E: inventory,
  caller migration, ownership transfer и wrapper/package retirement.
  9B-P01 подтвердил два target engines: `content_creator` для short/long
  creation и `video_repurposer` на основе Anime Factory. Catalog status не
  менялся; repurposer остаётся disabled; production code не менялся.
- Этап 4.6 создал проверенные
  [dependency/boundary map](ARCHITECTURE_BOUNDARY_MAP.md) и
  [cleanup registry](CLEANUP_REGISTRY.md) без изменения production code/runtime.
- Slice 5A перевёл `NewsProjectStore.write_json` на существующий
  `project_foundation.atomic_write_json`. Slice 5B добавил `NEWS_JOB_SCHEMA_VERSION=1`.
  Slice 5C добавил общий fail-fast project lock.
  Bounded slices 5D добавили output-validated stage idempotency для всех
  повторяемых downstream-семейств от `research` до `export`: завершённое
  состояние признаётся только при наличии пригодного обязательного
  manifest/media output. Legacy asset/voice/subtitle shapes и protected
  пользовательские субтитры остаются tolerant.
  Первый structural migration slice перенёс канонический CLI-слой в `src/ai_youtube/cli/`
  с доменными модулями команд (`create`, `project`, `assets`, `diagnostics`), а `src/content_creation/cli.py`
  сохранён как тонкий compatibility wrapper.
- `python -m ai_youtube` — единственный канонический CLI;
  `src.content_creation.cli`, `pipeline.py` и `apps/*` сохранены для совместимости.
- Команды CLI зарегистрированы отдельными domain parser modules; общий request
  builder используется CLI и Wizard, cycle CLI ↔ Wizard устранён.
- Подэтап 6A разделил бывший 2119-строчный `src/news/asset_manager.py`:
  266-строчный compatibility facade сохраняет публичные функции, старые imports
  и patch-points; manifest builder отделён от чистых summary/coverage-расчётов,
  scene completion и provider search/download adapters. Provider contract,
  manifest schema и persisted projects не менялись.
- Подэтап 6B оставил `src/content_creation/cli.py` тонким compatibility facade
  и разделил бывший 727-строчный canonical diagnostics handler: catalog,
  localization/subtitles и authoring выполняются отдельными domain-модулями,
  а терминальное форматирование вынесено в `src/ai_youtube/cli/presentation.py`.
  Public command set, JSON/text output и старые module-level patch-points
  сохранены; потерянный migration-ом `create_content` patch-point восстановлен
  через явную dependency injection.
- Подэтап 6C уменьшил `src/content_creation/wizard.py` с 1229 до 175 строк:
  facade сохраняет `run_wizard`, prompt adapters, private compatibility imports
  и module-level request-builder patch-point. Working state и translation через
  общий `request_builder` вынесены в `wizard_state.py`, terminal presentation —
  в `wizard_presentation.py`, интерактивные шаги и execution orchestration —
  в `wizard_steps.py`. Lazy CLI → Wizard boundary и application service не
  менялись.
- Подэтап 6D уменьшил `src/content_creation/service.py` с 878 до 123 строк и
  сохранил его единой точкой входа `create_content` для CLI и Wizard. Общие
  progress/path helpers вынесены в `service_support.py`, Story Card и Fullscreen
  Voiceover — в отдельные use case-модули. Fullscreen orchestration разделён на
  явные project, safe-pipeline, voice/approval, draft и render/export фазы;
  longest method — 93 строки. Paid approval/preflight, resume/force-stage,
  tolerant existing narration и progress callback сохранены.
- Подэтап 6E уменьшил `src/assets/semantic_visual_evaluation.py` с 1719 до
  53 строк и сохранил его public facade для root `pipeline.py`. Offline
  dataset loading, synthetic frames, metrics и report artifacts вынесены в
  `semantic_visual_evaluation_tooling.py`; gated OpenAI execution, budget,
  authorization и checkpoint state — в
  `semantic_visual_evaluation_runtime.py`. Public signatures, dataclass shapes,
  dry-run/mock/fake-client paths и paid-call gates сохранены; самая длинная
  функция split-модулей — 68 строк.
- Подэтап 6F уменьшил root `pipeline.py` с 703 до 122 строк и оставил его
  compatibility facade для `apps.youtube_pipeline`, старых imports и
  module-level patch-points. Parser вынесен в `src/legacy_pipeline/cli.py`,
  maintenance/diagnostic handlers — в `maintenance.py`, legacy
  channel/video orchestration — в `workflow.py`. `main` занимает 27 строк,
  самая длинная orchestration-функция split-модулей — 77 строк; command
  contract, workspace resolution, safe paid-call gates и старый workflow
  сохранены.
- Подэтап 6G устранил подтверждённый static import-cycle
  `frame_sampling` ↔ `perceptual_similarity`: `SampledFrame`, file SHA-256 и
  perceptual image hash вынесены в минимальный `frame_primitives.py`.
  Прежние public imports из обоих модулей и `src.assets`, image sampling,
  signature generation, visual-preview и temporal-analysis поведение сохранены.
- Этап 7 закрепил `src.assets.provider_contract.StockProvider` единственным
  canonical provider contract и перенёс default automatic factory в
  `src.providers.registry`. Активный news workflow получает canonical
  implementations из `src.providers`; timeout/retry/rate-limit translation,
  diagnostics, download validation и license normalization остаются в общих
  `src.assets` components. `stock_video_downloader` сокращён до 35-строчного
  compatibility wrapper без raw HTTP, а D01 legacy provider names удалены
  bounded slice этапа 9 после zero-caller audit. Отдельный D02 checkpoint затем
  подтвердил отсутствие imports/entrypoints и удалил wrapper; active asset
  stage остаётся у `src.news.asset_manager`.
- Первый slice этапа 8 (`f8ac67e`, `06e6a25`) установил canonical Fullscreen Voiceover
  application boundary в
  `src.ai_youtube.apps.content_creator.workflows.fullscreen_voiceover`.
  Application service импортирует новый use case; прежний
  `src.content_creation.fullscreen_voiceover_use_case` и
  `apps.news_to_short` остаются compatibility wrappers. Существующие
  `NewsJob`, `NewsProjectStore` и `src.news.pipeline` переиспользуются без
  новой schema/storage/workflow system; lazy service import сохранён, runtime
  projects не мигрировались.
- Второй slice этапа 8 (`01cfc6f`) установил canonical Story Card application
  boundary в
  `src.ai_youtube.apps.content_creator.workflows.story_card`.
  Application service импортирует новый use case; прежний
  `src.content_creation.story_card_use_case` остаётся compatibility wrapper.
  Существующие `ProjectFactory`, `ProjectManifest`, `EvidenceBundle`,
  `EvidenceRecord` и `src.templates.story_card` переиспользуются без новой
  schema/storage/evidence/render system; persisted projects и user media не
  мигрировались.
- Третий slice этапа 8 (`7d0ce1e`) установил canonical Anime Clipper adapter
  boundary в
  `src.ai_youtube.apps.video_repurposer.workflows.anime_clipper`.
  `apps.anime_factory` разрешает workflow через новую границу, а существующие
  `anime_factory.pipeline`, `EpisodePaths` и `get_episode_paths` остаются
  единственными владельцами поведения и project/output layout. Catalog
  `video_repurposer` не включён и остаётся planned/disabled; runtime episodes
  не перемещались.
- Четвёртый slice этапа 8 (`cfe6ae6`) установил canonical legacy pipeline
  adapter в `src.ai_youtube.apps.legacy_pipeline.adapter`.
  `apps.youtube_pipeline` разрешает root `pipeline.main` через новую границу,
  а root facade остаётся владельцем compatibility namespace и engine
  patch-points. Существующие parser, maintenance и channel/video workflow
  contracts продолжают принадлежать `src.legacy_pipeline`; engines, outputs,
  runtime projects и media не перемещались.
- Gate 8E (`a3536a9`) подтвердил, что documentary не зарегистрирован как
  application/template, `longform` disabled и без шаблона, а legacy profiles
  `psychology`, `quotes`, `survival` и `size_comparison` недоступны
  `content_creator`. Solar fixed plan остаётся root-only experimental path:
  его `project_config.json`/`scenes.json` не распознаются `ProjectRepository`,
  а render path имеет прямые TTS/HTTP calls без application-level paid gate.
  Поэтому documentary boundary, capability и новый project contract не
  создавались; решение зафиксировано ADR 0013.
- `applications list` по умолчанию показывает только active/enabled приложения;
  planned/disabled доступны только при явном запросе и сохраняют честный статус.
- Активное приложение: `content_creator`.
- Активные live-tested шаблоны: `fullscreen_voiceover_v1` и
  `story_card_text_only_v1`.
- `video_repurposer`, `longform` и `horizontal_clip` остаются disabled/planned.
- Общий `ProjectRepository` читает старые `job.json` и `project.json`.
- Offline CI, pinned core lock, artifact schemas и characterization baseline добавлены
  этапом 1.
- `WorkspacePaths`/`ApplicationPaths` задают единый runtime workspace через
  CLI, `AI_YOUTUBE_WORKSPACE` или path config; CLI имеет наивысший приоритет.
- Default workspace и legacy fallback остаются в корне репозитория, поэтому старые
  проекты и outputs читаются без физического переноса.
- Versioned config/resources всегда разрешаются от корня репозитория, а не от cwd.
- Runtime-проекты и media физически не перемещались.

Известные переходные долги:

- две формы project manifests сохраняются tolerant readers; lock сериализует
  отдельные news JSON writes; output validation покрывает повторяемые стадии от
  `research` до `export`. `input` и потенциально сетевой `article_ingestion`
  намеренно не включены в автоматическую retry-policy ADR 0006;
- documentary gate 8E закрыт без migration; ADR 0016 определил future
  documentary как workflow/template `content_creator`, которому нужны реальный
  catalog template, canonical project/approval/provider contracts и targeted
  evidence; физические Anime
  Factory workflow/output contracts остаются у `anime_factory`, root legacy
  engine/patch-point contracts — у `pipeline.py`, а documentary и
  fixed-production-plan HTTP paths остаются внутри будущего bounded slice;
- D01 news-only provider names, D02 standalone downloader и D03 planning
  directory удалены отдельными проверенными commits; stage 10 cleanup
  candidates A01/A02/D04 ещё не начаты;
- этап 8 установил application boundaries, но не завершил ownership transfer:
  `src.news`, `src.templates.story_card`, `anime_factory`, `pipeline.py` и
  `src.legacy_pipeline` всё ещё владеют частью реализации;
- capability owner gates активного плана (PLAN-1A, PLAN-1B, PLAN-1C′), которые
  заменили монолитный inventory, должны дополнить cleanup registry точными
  production/test/docs callers и exit conditions для package roots/wrappers,
  Anime project/transcription/subtitle/render modules и legacy/shared music
  paths. До закрытия соответствующего gate перенос и удаление этих paths
  запрещены.

Создание, продолжение, TTS, render и визуальная проверка reference video больше
не являются этапами rescue plan. Архитектурные изменения выполняются малыми
slices после карты callers/tests; удаление без доказанной замены запрещено.
Сохранённые full-suite отчёты исторические; для каждого изменения запускаются
только targeted tests в радиусе зависимости.
