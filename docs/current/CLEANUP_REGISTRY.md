---
status: current
last_verified_commit: 72221e1
last_verified_date: 2026-08-07
source_paths:
  - pyproject.toml
  - ai_youtube
  - apps
  - anime_factory
  - src/ai_youtube/apps/video_repurposer/workflows/anime_clipper
  - src/ai_youtube/apps/legacy_pipeline
  - pipeline.py
  - src/production_plan/youtube_shorts.py
  - src/production_plan/solar_vs_nuclear_render.py
  - src
  - tests
  - tests/test_anime_clipper_application_boundary.py
  - tests/test_legacy_pipeline_application_boundary.py
  - tests/test_documentary_migration_gate.py
  - docs/adr/0011-anime-clipper-application-boundary.md
  - docs/adr/0012-legacy-pipeline-application-boundary.md
  - docs/adr/0013-documentary-migration-gate.md
  - docs/adr/0014-retire-news-provider-class-compatibility.md
  - docs/adr/0015-retire-news-stock-downloader.md
  - docs/adr/0016-two-engine-product-architecture.md
  - tests/data/legacy_content
  - docs/current/ARCHITECTURE_BOUNDARY_MAP.md
  - docs/handoff/PROJECT_RESCUE_MASTER_PLAN.md
---

# Cleanup Registry

`last_verified_commit` / `last_verified_date` означают **последний общий
consistency review** этого файла: 2026-08-01 от clean HEAD `affa138`. Они **не**
означают, что все строки заново переизмерены сегодня. Provenance секций
сохраняется отдельно:

- baseline-секции (K01–K08, S01–S07, M01–M02, V00–V04, A01–A02, D01–D04,
  N01–N06, C01–C16) — проверены 2026-07-29 от clean HEAD `9f3ddba` и от своих
  исторических HEAD, указанных внутри строк;
- **C17–C29** — Repository Foundation audit, 2026-07-31 от `4ca3655`;
- **C30–C33** — evidence ревизии 2, 2026-07-31;
- **C34–C50** — evidence ревизии 2.1 (deep-dive), 2026-07-31 от `adcbb19`;
- **C51–C52** — findings PLAN-1D-routing, 2026-08-01 от clean HEAD `b396a50`;
- **C53–C62** — findings motion rendering, 2026-08-01 от clean HEAD `35325b4`;
- **C63** — plan↔code reconciliation finding, 2026-08-08 от clean HEAD
  `7a8142f`; read-only, дефект не исправлялся;
- **C75–C78** — подтверждённые дефекты retrieval-эксперимента EXP-001,
  перенесены 2026-08-13 из журнала `docs/audits/STOCK_RETRIEVAL_EXPERIMENTS.md`
  слайсом AUD-DELTA-CLOSE; структурная часть каждой строки перепроверена по
  коду в момент переноса, эмпирическая часть остаётся за журналом; дефекты не
  исправлялись;
- **C64–C74** — retrieval/material engine audit, 2026-08-13 от clean HEAD
  `f3b607a`; read-only, дефекты не исправлялись; часть предложенных внешним
  отчётом строк отклонена перепроверкой — см. errata в
  [RETRIEVAL_ENGINE_AUDIT_2026-08-13.md](../audits/RETRIEVAL_ENGINE_AUDIT_2026-08-13.md);
- **C01-SEM ownership inventory** — PLAN-1C′, 2026-08-07 от clean HEAD
  `b0e99a7`; read-only, без перемещения файлов и без изменения поведения;
- **Knowledge salvage log** — заполнен PLAN-L0, 2026-08-02 от clean HEAD
  `2b46afb`; read-only, без retirement и без миграции capability.

Код и Git имеют приоритет.
Классификация означает целевое действие после указанного gate, а не действие
этапа 4.6. Подэтапы 6A–6G и provider consolidation этапа 7 выполнены bounded
изменениями; Fullscreen Voiceover, Story Card, Anime Clipper и legacy pipeline
slices этапа 8 завершили canonical boundaries, documentary gate 8E закрыт без
migration. Они не завершили ownership transfer старых package owners. Runtime и
user data не перемещались и не удалялись. Этап 9A завершил D01–D03 отдельными
bounded commits. 9B-P01 подтвердил два target engines; caller/ownership
inventory C01–C16 ещё не выполнен.

Допустимые значения: `keep`, `split`, `merge`, `move`, `replace`, `archive`,
`delete`, `do_not_touch`, `obsolete-with-legacy`. `compatibility wrapper` —
переходное состояние, а не финальный class.

**Ревизия 2 execution plan, 2026-07-31.** Владелец зафиксировал: существующая
зависимость, существующий owner и существующая архитектура не являются
доказательством правильности; тестовое runtime-медиа disposable. Поэтому часть
строк сменила class с `do_not_touch` на `split`, `delete` или
`obsolete-with-legacy`, а gates перенаправлены на новый параллельный этап
`PLAN-L` и на capability-scoped gates. Owner decisions OD-1…OD-10 и правило
«отсутствие caller не доказывает отсутствия ценности» находятся в
`PROJECT_EXECUTION_PLAN.md`; здесь они не дублируются.

**Ревизия 2.1 execution plan, 2026-07-31.** Добавлены findings C34–C50 по
input/query truth, LocalLibrary, provider declarations, export catalog, FFmpeg,
legacy knowledge salvage и rights fail-open. Часть формулировок предыдущих
аудитов **опровергнута** контролируемыми offline-пробами и здесь записана в
исправленном виде: не «три независимых LocalLibrary implementation», не «пять
расходящихся provider registries», не «два конкурирующих orchestration owner»,
не «конкатенация перекодируется в CRF 20». Owner decisions OD-11…OD-26, D-1,
D-2, D-3 и E-13 находятся в `PROJECT_EXECUTION_PLAN.md`; здесь не дублируются.
Ни одна строка ревизии 2.1 не даёт права на действие и ничего ещё не ретайрено.

**Motion rendering findings, 2026-08-01.** Добавлены findings C53–C62 по
composition/renderer: временная реализация Story Card, MoviePy и его duration
probes, рисующая часть `generated_infographic`, защитная запись о stock FFmpeg
path, недостижимый `preview_render`, разрозненные FPS/canvas, отсутствие
per-scene fingerprint и visual regression, разрозненные design tokens. Каждый
пункт перепроверен по коду. Owner decisions мотивации находятся в
`PROJECT_EXECUTION_PLAN.md` и `PRODUCT_PLAN.md`; здесь не дублируются. Ни одна
строка права на действие не даёт; правило парности замещения и retirement —
**PD-11**.

Ни одна строка не даёт права на действие сама по себе. Для knowledge-bearing
families (source, workflow, config, prompts, templates, tests, уникальное
docs/evidence) обязателен Knowledge Salvage Gate (`PLAN-L0`) перед destructive
retirement и обратимый retirement-механизм (annotated tag + `git bundle` +
строка в `Retired`). Для disposable runtime/media/cache действует другая
цепочка — `PLAN-14D` → `PLAN-14E` со сверкой по `Preserved runtime corpus`;
KSG к ним не применяется.

## Architecture candidates

| ID | Кандидат | Class | Фактическое evidence | Gate / целевое состояние | Этап |
|---|---|---|---|---|---|
| K01 | root `ai_youtube/` + `src/ai_youtube/` + installed `ai-youtube` | `merge` | console script указывает на root shim; package discovery включает `ai_youtube*` и `src*`; оба `__main__.py` exact-identical | сохранить public command contract, но оставить один physical `src/ai_youtube` package, устанавливаемый как `ai_youtube` | 9B–9E |
| K02 | `src/production_catalog` + capabilities | `keep` | единственный честный registry active/planned apps и templates | не создавать второй catalog | всегда |
| K03 | `src/config_resolver` | `keep` | используется CLI, stores, providers, audio/subtitles и legacy adapters | единственный resolver, legacy read fallback сохраняется | всегда |
| K04 | `src/projects/ProjectRepository` | `keep` | читает `job.json` и `project.json`, ничего не пишет | единый read API; writers остаются у manifest owners | 5 |
| K05 | `src/assets/provider_contract.py` + `src/providers/` | `keep` | этап 7 (`fb93a05`) закрепил `StockProvider` canonical contract и перенёс default factory в `src.providers.registry`; adapters/download/preview/diagnostics используют общую foundation | единственный provider contract и registry | 7 complete |
| K06 | `src/audio/` | `keep` | approval, voice manifests, timeline и TTS manager защищены отдельными tests | не создавать второй voice/TTS contract | всегда |
| K07 | `src/subtitles/` | `keep` | единственный engine, news использует adapter | не создавать второй subtitle engine | всегда |
| K08 | `apps/*` wrappers | `delete` | **уточнено ревизией 2.** [FACT] `apps/anime_factory/main.py` и `apps/youtube_pipeline/main.py` — 8-строчные делегации; `apps/news_to_short/main.py` — **83 строки собственного argparse**, дублирующего флаги канонического `create`/`resume`, то есть второй CLI активного workflow. **Исправлено 2026-08-01:** возможностей вне явного контракта канонического `create` **две** — именованный source-text вход (`--text` / `--text-file`, функционально уже достижимый как `create --pasted-script/--script-file` при default/legacy unspecified `content_input_mode`) и пользовательские ассеты при создании проекта (`--assets` → `NewsJob.user_assets`), у которого доказанного канонического аналога нет. Формулировка «единственная уникальная бизнес-возможность» опровергнута. У пакета есть test-callers и собственный `README.md` | `youtube_pipeline` удаляется в **PLAN-L4**. `news_to_short` (**OD-2, OD-19, D-1**): source-material вход становится явным canonical contract в **PLAN-9B-5a** (additive, без удаления), retirement — **только в PLAN-9B-5b** после **capability parity check** всего wrapper'а, миграции сохраняемых capabilities и всех callers, с PLAN-6D + PLAN-6E + reversible retirement. `--assets` мигрирует либо получает явное owner decision о намеренном retirement; молчаливая потеря запрещена. `anime_factory` — вместе с миграцией `video_repurposer`; **capability не disposable (OD-23)** | L4 / **9B-5a → 9B-5b** / PLAN-13 |
| S01 | `src/news/asset_manager.py` + `src/news/asset_*.py` | `split` | 6A (`cba1cf7`, `20750ab`, `59b39d3`, `fe5ba44`) оставил 266-строчный facade и отделил builder, summaries, completion и provider adapters | выполнено; public functions, imports и patch-points защищены characterization | 6A complete |
| S02 | CLI internals после canonical migration | `split` | 6B (`1f9495c`) оставил 81-строчный compatibility facade, разделил catalog/localization/authoring handlers и terminal presentation; diagnostics стал 78-строчным facade | выполнено; public command/output contract и старые patch-points защищены characterization | 6B complete |
| S03 | `src/content_creation/wizard.py` + `wizard_state`/`wizard_steps`/`wizard_presentation` | `split` | 6C (`b9f8212`) уменьшил facade с 1229 до 175 строк и разделил state/request translation, steps/execution и terminal presentation | выполнено; `run_wizard`, private compatibility imports, module request-builder patch-point и lazy CLI boundary защищены characterization | 6C complete |
| S04 | `src/content_creation/service.py` + use case modules | `split` | 6D (`8e087c7`) уменьшил facade с 878 до 123 строк, разделил Story Card/Fullscreen Voiceover use cases и явные fullscreen phases | выполнено; единый `create_content`, private imports, paid gate, tolerant resume и progress callback защищены characterization | 6D complete |
| S05 | `src/assets/semantic_visual_evaluation.py` + tooling/runtime modules | `split` | 6E (`8c89a67`) оставил 53-строчный facade и отделил offline dataset/metrics/reporting от controlled live execution/checkpoints | выполнено; public signatures, dataclass shapes, root-pipeline import и paid-call gates защищены characterization | 6E complete |
| S06 | `pipeline.py` + `src/legacy_pipeline` | `split` | 6F (`0d2cd67`) уменьшил root facade с 703 до 122 строк и разделил parser, maintenance handlers и legacy workflow | выполнено; старые imports, module patch-points, command/output contract и workspace resolution защищены characterization | 6F complete |
| S07 | `frame_sampling.py` + `perceptual_similarity.py` + `frame_primitives.py` | `split` | 6G (`802a54c`) вынес shared frame data/file hash/image hash primitives и устранил оба встречных static edges | выполнено; прежние public imports и visual-preview/temporal behavior защищены characterization | 6G complete |
| M01 | `NewsProjectStore.write_json` + `project_foundation.atomic_write_json` | `merge` | 5A (`87e272a`) подключил общий atomic primitive; 5B (`42d5b99`) добавил schema v1; 5C (`f7b3a3c`) добавил общий fail-fast project lock; 5D (`e3c90c3`) завершил output-validated idempotency | общий storage primitive и lock используются manifest owner; repeatable stages `research`–`export` проверяют обязательные outputs | 5 complete |
| M02 | public project API в `src/projects` и `src/project_foundation` | `merge` | read API уже общий, writer/models ещё разделены по persisted form | единый public API поверх двух tolerant forms; без третьей system; physical ownership — отдельный 9D slice | 9D |
| V00 | `src/content_creation/fullscreen_voiceover_use_case.py` | `delete` | slice 8A (`f8ac67e`, `06e6a25`) перенёс application use case в `src.ai_youtube.apps.content_creator.workflows.fullscreen_voiceover`; old path — 29-строчный wrapper | 9B callers, 9C canonical imports, 9E delete; `src.news` workflow ownership проверяется отдельно | 9B–9E |
| V03 | `src/content_creation/story_card_use_case.py` | `delete` | slice 8B (`01cfc6f`) перенёс application use case в `src.ai_youtube.apps.content_creator.workflows.story_card`; old path — 12-строчный wrapper | 9B callers, 9C canonical imports, 9E delete; template/project/evidence ownership проверяется отдельно | 9B–9E |
| V01 | `anime_factory/` | `move` | slice 8C (`7d0ce1e`) создал canonical lazy adapter; `anime_factory` всё ещё владеет CLI, `EpisodePaths`, workflow/output layout; catalog disabled/planned | owner P01 сохранил `video_repurposer` как второй target engine; 9B картирует modules, 9D обобщает/переносит без копирования, 9E retires old package | 9B–9E |
| V02 | root legacy engines + `pipeline.py` + `src/legacy_pipeline` | `replace` | slice 8D (`cfe6ae6`) создал canonical lazy adapter; root facade остаётся namespace/patch-point owner, `src.legacy_pipeline` — behavior owner | 9B классифицирует команды; 9D сохраняет только нужные maintenance services; 9E удаляет root entrypoint последним | 9B–9E |
| V04 | documentary channels + Solar fixed production plan | `archive` | gate 8E (`a3536a9`) подтвердил отсутствие template, disabled `longform`, legacy-only profiles, bespoke project contract и прямые live calls | ADR 0016: future documentary — workflow/template `content_creator`; legacy path не переносить целиком, reusable parts только после audit; runtime/user data не удалять | 9B–9E |
| A01 | historical audits/plans вне `docs/current` | `archive` | runtime imports отсутствуют; часть уже в `docs/archive` | сохранять историю, обновлять ссылки, не удалять без review | 10 |
| A02 | 9 tracked legacy файлов в `outputs/` | `archive` | пути всё ещё заданы config/root pipeline; сами outputs воспроизводимы не все | backup + manifest/reference check, затем untrack/archive. **Retired 2026-08-13 owner decision**: backup = annotated tag + bundle `legacy-content-outputs-2026-08-13`, reference check выполнен (тесты используют только строки путей и tmp, реальные файлы не читает никто); см. **R02** | ~~10~~ **closed → R02** |
| D01 | compatibility `PexelsAssetProvider`, `PixabayAssetProvider`, `UnsplashAssetProvider` в `src/news/asset_provider_adapters.py` | `delete` | stage 9 zero-caller audit подтвердил только definitions/re-export/test references; active factory использует canonical `StockProvider` implementations | завершено: classes, raw provider imports и `asset_manager` re-exports удалены; `AssetProvider`/factory patch-point сохранены | 9 D01 complete |
| D02 | `src/news/stock_video_downloader.py` | `delete` | stage 9 AST/repo audit подтвердил отсутствие production imports/calls, package export, CLI и current command; test был единственным executable caller | завершено: wrapper удалён, два исторических production docstring исправлены; canonical asset stage сохранён | 9 D02 complete |
| D03 | `packages/README.md` и пустая planning directory | `delete` | повторный audit подтвердил один tracked planning README, отсутствие runtime/current callers и package discovery только из `ai_youtube*`, `src*`, `anime_factory*`, `apps*` | завершено: README и пустая physical directory удалены; historical snapshots не переписаны | 9 D03 complete |
| D04 | untracked `__pycache__/`, `*.pyc` | `delete` | 0 tracked matches; bytecode воспроизводим | удалять только filesystem-cleanup slice, не вместе с refactor | 10 |
| N01 | `.env`, `.env.*`, credentials/private keys | `do_not_touch` | конфигурация может содержать secrets; содержимое не проверялось | никогда не читать/коммитить/удалять автоматически | всегда |
| N02 | `projects/` — 1618 файлов | `split` | **изменено ревизией 2 (OWNER).** 749 JSON + ~700 медиа, 0 tracked; оба project readers используют root | медиа — disposable, удаляется на runtime reset; JSON/SRT/ASS проходят classify/dedupe и дают **минимальный representative corpus** (C32); полный набор — во внешний retirement bundle | 14D |
| N03 | `assets/`, `manual_assets/`, `music/` | `split` | **изменено ревизией 2 (OWNER).** 287 + 18 + 3 файла; смешанные runtime media и versioned resources | **keep:** `assets/library/metadata/media_index.json` (provenance/rights), versioned SVG в `manual_assets/**`. **delete:** всё медиа, кэши. `assets/voice_samples` — **disposable (OD-3)**; минимально необходимый sample активного voice profile переносится во внешний Workspace с provenance, иначе удаляется | 14D/14E |
| N04 | `content/`, включая `story_card_jobs.tsv` | `obsolete-with-legacy` | **изменено ревизией 2.** [FACT] это fixtures legacy-стека, а не user data: `content/survival/juliane_koepcke_001.json` и `channels/survival` читаются `tests/test_documentary_visual_engine.py` и `tests/test_channel_profiles.py`; `story_card_jobs.tsv` не имеет runtime caller | ретайр вместе с legacy-стеком **после Knowledge Salvage Gate** (OD-1): visual rules, промпты и продуктовые декларации форматов сохраняются как knowledge. **Retired 2026-08-13 owner decision раньше L3** (KSG соблюдён): 11 файлов без читателей — R03; fixture-пара survival/quotes перенесена в `tests/data/legacy_content/` и подставляется через `application_paths` — R04; оба LEGACY ANCHOR теста сохранены и остаются носителями KEEP MINIMAL REGRESSION знания до PLAN-L3; publish-metadata возможность записана **R02-KN** | ~~PLAN-L0 → L3~~ **closed → R03/R04** |
| N05 | `project_solar_vs_nuclear/` | `delete` | **изменено ревизией 2 (OWNER).** 102 runtime/experiment файла, 0 tracked | удаляется на runtime reset; уникальных инженерных доказательств не содержит | 14C/14D |
| N06 | `MOSS_TTS_Nano/` (56 463 файла), `src/tts_providers/` | `delete` | **изменено ревизией 2 (OD-7).** [FACT] это цельный вендоренный сторонний репозиторий: собственные `pyproject.toml`, `requirements.txt`, `venv/`, `tests/`, `finetuning/`, `.egg-info`, `app.py`, `infer.py`, 45 `.exe`, `generated_audio/`, логи. [FACT] активный `src/audio/tts/provider_manager.py` MOSS **не регистрирует**; единственный мост `src/tts_providers/moss_tts_provider.py` импортируют только `src/voice_engine.py` (L3), `pipeline.py` и `scripts/test_moss_voices.py` (L4) и один тест. [INFERENCE] после L3/L4 — ноль callers | KSG сохраняет provider-specific knowledge, инструкции запуска, edge cases и вывод «почему пробовали и что вышло» в один ADR, затем оба пути удаляются. **Не реинтегрировать в scope этой программы. Vendor repo в `Workspace/models` не переносить** — Runtime Workspace не хранилище исходного кода. `venv/` воспроизводится вне clean root | **PLAN-L0 → L4** |

## 9B compatibility и ownership inventory

Это единственный compatibility registry проекта; отдельный
`COMPATIBILITY_REGISTRY.md` не создаётся. Для каждой строки 9B обязан добавить
production/test/docs/external callers, current owner, target owner, persisted
dependency, public promise, replacement и exit condition. Test-only caller сам
по себе не переводит строку в permanent `keep`.

| ID | Старый/переходный surface | Известное текущее состояние | Требуемое решение |
|---|---|---|---|
| C01 | root `ai_youtube/` против `src/ai_youtube/` | public launcher и implementation разделены; два exact-identical `__main__.py` | один physical src-layout package, import/console compatibility characterization |
| C02 | `src.content_creation.cli` | compatibility CLI с сохранёнными patch-points; canonical dispatcher уже существует | caller inventory → canonical imports → delete или обоснованный permanent adapter |
| C03 | Fullscreen/Story Card old use-case paths | thin wrappers, canonical application use cases уже существуют | перевести callers и удалить wrappers отдельными slices |
| C04 | `apps.news_to_short`, `apps.anime_factory`, `apps.youtube_pipeline` | compatibility packages и документированные module entrypoints | owner/external promise decision; убрать бессрочный `keep always` |
| C05 | `src.news` против Fullscreen canonical boundary | application use case перенесён, staged workflow/project/assets всё ещё принадлежат `src.news`. **Ревизия 2.1:** расслоение application/news ownership зафиксировано **ADR 0009 намеренно**; «два конкурирующих orchestration owner» — опровергнуто | определить app-specific и shared ownership, затем переносить без копирования. Точный idempotency contract defect вынесен в **C43a**, возможная поздняя convergence — **C43b** |
| C06 | `src.templates.story_card`/`src.production_plan` против Story Card boundary | project/evidence/render contracts остаются у прежних owners | определить shared contracts и workflow owner; не создавать второй renderer |
| C07 | `anime_factory` против Anime Clipper adapter | adapter новый, implementation/output layout старые, capability disabled | P01: finish migration в единый `video_repurposer`; C01 должен разложить modules по app-specific/shared ownership |
| C08 | `pipeline.py`/`src.legacy_pipeline` против legacy adapter | root namespace, patch-points и behavior разделены между переходными paths | классифицировать каждую command family; root wrapper удалить последним |
| C09 | `src.assets.semantic_visual_evaluation` | public facade нужен root pipeline | пересмотреть после C08; не удалять раньше единственного caller |
| C10 | `src.projects` + `src.project_foundation` + manifest writers | один read API и storage primitives, но physical owners разделены persisted forms | единый public owner поверх tolerant formats, без массовой manifest migration |
| C11 | exact-identical production entry stubs | две package `__main__` копии и три `apps/*/__main__.py` копии | удалять вместе с parent surface; не добавлять shared boilerplate abstraction |
| C12 | `src.audio.music_manifest` против `src.music_engine`/`music_finder`/`music_tools` | modern manifest/rights path и legacy search/download/mix paths сосуществуют; final renderers используют разные части | выбрать один shared music owner, сохранить license manifest/ducking, raw network перевести на provider/approval contracts или retire |
| C13 | `anime_factory.modules.subtitles` против `src.subtitles` | Anime пишет candidate-relative SRT/ASS своим formatter; общий subtitle engine уже имеет timing/style/serialization/manifests | сохранить только app-specific relative-cue adapter, использовать общий engine/serialization вместо второго subtitle stack |
| C14 | Anime FFmpeg/crop/render helpers против news/root renderers | несколько FFmpeg runners и render orchestrations; crop/scoring действительно domain-specific | один shared FFmpeg execution boundary и render contracts; crop/layout orchestration остаётся у workflow, не создавать один giant renderer |
| C15 | Anime `EpisodePaths`/JSON layout против `WorkspacePaths`/`ProjectRepository` | Anime runtime живёт под package root и не распознаётся общим repository | app-scoped project path через существующий resolver, tolerant legacy episode reader; не создавать third project system |
| C16 | Anime transcription/audio/scene analysis/candidate scoring | единственная рабочая source-to-clips реализация уже существует в Anime modules | переносить/обобщать существующие modules внутри `video_repurposer`; shared service только при доказанном втором caller |

## Repository Foundation audit findings (C17–C29)

Read-only bounded audit каркаса репозитория, выполнен 2026-07-31 от clean
HEAD `4ca3655` (`audit_head`). Production-код, tests и структура не менялись.

Каждая строка имеет класс доказанности:
**FACT** — проверено командой, воспроизводимо;
**INFERENCE** — вывод из фактов, исполнением не проверен;
**DEFER** — evidence недостаточно, решение отложено к названному gate.

Это findings каркаса, а не 9B compatibility surfaces: они не заменяют и не
дублируют C01–C16.

| ID | Path / предмет | Current owner | Класс | Evidence | Exit condition | Gate |
|---|---|---|---|---|---|---|
| C17 | `legacy/` (8 файлов, 424 строки) | никто | **FACT** + **DEFER** | repo-wide поиск не нашёл ни одного Python-caller; ссылки только из `README.md` и historical docs | статический граф не доказывает отсутствия внешнего/строкового caller — нужен caller gate; salvage знания; затем delete с retirement tag | **PLAN-L0 → L1 → L4** |
| C18 | `scripts/test_moss_voices.py` | `pipeline.py:9` | **FACT** | единственный production-импорт из `scripts/`; sys.path-инъекция; hardcoded `G:/`; имя `test_*.py` вне `tests/` | **OD-7 закрыл вариант «→ `tools/`»:** MOSS ретайрится, `src/tts_providers/` удаляется, значит helper удаляется вместе с ними. Class → `delete`; импорт снимается в L4 вместе с `pipeline.py` | **PLAN-L0 → L4** |
| C19 | `outputs/*.json` (**8 файлов**) | Git index ∩ ignore | **FACT** | `git ls-files -i -c --exclude-standard` перечисляет `asset_plan`, `music_plan`, `quote_plan`, `render_plan`, `render_stage`, `scene_plan`, `self_eval`, `youtube_metadata` — tracked при совпадении с `outputs/**/*.json` | класс решён: generated output legacy-стека. Producer умирает вместе с `pipeline.py`, поэтому untrack планировался в L4. **Retired 2026-08-13 owner decision раньше L4** — canonical path в `outputs/` не пишет (export идёт в `projects/<id>/localizations/*/output`), producer при запуске создаёт каталог заново; см. **R02** | ~~PLAN-L4~~ **closed → R02** |
| C20 | `output/`, `tmp/` | никто | **FACT** | `git check-ignore` → NOT IGNORED для обоих; `output/` = 1 файл (`output/pdf/PROJECT_EXECUTION_PLAN_mobile.pdf`, 280 820 байт, 2026-07-30); `tmp/pdfs/` пуст | правила `.gitignore` для `output/` и `tmp/` добавлены **в PLAN-14F** (единственный slice с `.gitignore` в allowed zones); untracked-артефакты удалены — это commit не требует, воспроизводимый cache/temp закрывает 14C. PLAN-6B — только detector | PLAN-6B (detect) → **14F** (`.gitignore`) → 14C (untracked cleanup) |
| C21 | `assets/broll/.gitkeep` | Git index ∩ ignore | **FACT** | директорное правило `assets/broll/` обесценивает последующее `!assets/broll/.gitkeep`; файл tracked и ignored одновременно | правило заменено на `assets/broll/*` **в PLAN-14F** (единственный slice с `.gitignore` в allowed zones); `git ls-files -i -c` не содержит `.gitkeep`. PLAN-6B — только detector | PLAN-6B (detect) → **14F** (fix) |
| C22 | `docs/contracts/STAGE1_PUBLIC_CONTRACTS.md` | orphan | **FACT** + **DEFER** | 0 входящих ссылок; называет `src.content_creation.cli` «current CLI»; канонический `python -m ai_youtube` не упоминает | target responsibility определяется PLAN-12E **по содержимому файла**, не автоматически по каталогу; затем update или archive | PLAN-12E → 7/12C |
| C23 | `docs/architecture/visual_rendering_policy.md` | orphan; **временно защищён от archive/delete** | **FACT** + **INFERENCE** | FACT: 0 входящих ссылок. INFERENCE: единственный владелец визуального quality bar — `docs/implementation` построчно не читался | PLAN-12E выбрал target path (кандидат — `docs/product/QUALITY_BAR.md`); PLAN-12B подтвердил отсутствие competing quality owner. **Ревизия 2 перенесла подтверждение из PLAN-1C в PLAN-12B** вместе с пофайловой классификацией `docs/*` (C27). **До этого archive/delete запрещены** | **PLAN-12E → 12B** |
| C24 | hardcoded `G:/` в versioned config | `config/`, `channels/` | **FACT** | `config/video_style.json` — `moss_tts_path`, `vault_path`; `channels/psychology/style.json` — `moss_tts_path` | **оба носителя умирают в L3:** `config/video_style.json` и `channels/psychology/` ретайрятся вместе с legacy-стеком, поэтому отдельного исправления не требуется. Если после L3 hardcoded drive обнаружится в выжившем versioned config — резолвить через существующий resolver или env | **PLAN-L3**, остаток → PLAN-14B |
| C25 | `pyproject`: `pipeline` в дистрибутиве без `scripts` | packaging | **FACT** + **INFERENCE** | FACT: `py-modules = ["pipeline"]`, `packages.find.include` без `scripts*`, `pipeline.py:9` импортирует `scripts.test_moss_voices`. INFERENCE: non-editable install ломает `import pipeline` — `pip install .` не выполнялся | дефект исчезает вместе с носителем: L4 удаляет `pipeline.py` и `scripts/` и снимает `py-modules`. Проверка: wheel собран и импортируется в temporary venv вне checkout | **PLAN-L4** |
| C26 | intended distribution boundary `tools/` | не определён | **DEFER** | `tools*` не входит в `packages.find.include`; все известные callers (`AGENTS.md`, `tests/test_stage2_agent_onboarding.py`, ADR, активный план) находятся внутри checkout | зафиксировать: `tools/` в wheel или только checkout. Предварительно — только checkout, тогда правка идёт в формулировку `AGENTS.md`, а не в `pyproject.toml`. **Добавлять `tools*` в wheel только ради работы repository QA из установленного пакета запрещено** | PLAN-6C |
| C27 | `docs/implementation` (96), `docs/audits` (9), `docs/architecture` (5), `docs/apps` (3) | смешанный | **DEFER** | проверены типы, заголовки, frontmatter, reference-граф и hash; построчно **не читались** | пофайловая классификация выполнена; до этого archive/move/delete любого файла этих семейств не выполняются. **Ревизия 2 перенесла классификацию из PLAN-1C в PLAN-12B:** PLAN-9A её не требует | **PLAN-12B** |
| C28 | `docs/architecture/localization_and_voice_architecture.md` | не классифицирован | **DEFER** | заранее не объявляется ни `keep`, ни archive-кандидатом | per-file evidence по всему `docs/architecture/*` получено | **PLAN-12B** |
| C29 | `outputs/asset_library_report.md` | tracked generated output | **FACT** | **не** входит в index ∩ ignore и не подпадает ни под одно правило `.gitignore` — в отличие от C19. Порождается production-кодом: `src/media_library.py:218` `create_asset_report(output_path="outputs/asset_library_report.md")`, вызывается из `src/legacy_pipeline/maintenance.py:459` по флагу `--asset-report` (`src/legacy_pipeline/cli.py:47`) | producer `--asset-report` умирает вместе с legacy CLI; untrack планировался в L4. `src/media_library.py` **сохраняется** — он используется активным news-путём. **Retired 2026-08-13 owner decision раньше L4**: файл удалён, producer невредим и при `--asset-report` пересоздаст отчёт; см. **R02** | ~~PLAN-L4~~ **closed → R02** |

Строки C17–C29 не дают права на действие сами по себе: каждая закрывается
своим gate по общему `Closure rule` ниже.

## Ревизия 2 findings (C30–C33)

Зафиксировано 2026-07-31 архитектурной ревизией execution plan. Классы
доказанности те же: **FACT** / **INFERENCE** / **DEFER**.

| ID | Path / предмет | Current owner | Класс | Evidence | Action / target | Exit condition | Gate |
|---|---|---|---|---|---|---|---|
| C30 | legacy content stack: `pipeline.py`, `src/legacy_pipeline/{cli,workflow}.py`, 20 модулей корня `src/` (~4903 строки), `src/tts_providers/`, `channels/{psychology,quotes,survival,size_comparison}`, `content/`, `config/video_style.json`, `apps/youtube_pipeline/`, `legacy/`, `scripts/` | `pipeline.py` | **FACT** | единственный production-caller — `pipeline.py`; 6 test-модулей из 112. Исключения, которые **остаются**: `src/media_library.py` (активный news-путь) и `src/utils.py` (`src/audio/tts/env.py`, `src/tts_providers/moss_tts_provider.py`) | `delete` после salvage. Diagnostics из `maintenance.py` — **не** часть стека, переезжают в L2 | ноль production-callers; канонический CLI — единственный вход; retirement tag создан и выгружен bundle | **PLAN-L0 → L1 → L2 → L3 → L4** |
| C31 | production-зависимость на `docs/implementation/openai_live_evaluation` | `src/assets/semantic_visual_evaluation_tooling.py` | **FACT** | три production-строки: `:26` дефолтный dataset, `:38` дефолтный results dir, `:695` переписывание относительных путей. Плюс `tests/test_semantic_decision_policy.py` (3 места). Синтетический генератор уже существует: `tests/test_semantic_visual_evaluation.py:458 _write_prepared_dataset` | `move`. **Зафиксировано (OD-8): `docs/` — неправильный target owner**, fixture/evidence сохраняется. **Physical target — DEFER**; `resources/evaluation/` только candidate, потому что top-level `resources/` не утверждён (OD-9) | target owner утверждён classification-ом, caller переведён, `docs/` свободен от production dependency | **PLAN-13** (запись дефекта — PLAN-1C′, без перемещения файлов) |
| C32 | legacy manifest corpus, 749 JSON в `projects/` | runtime | **FACT** + **DEFER** | 749 JSON плюс ~700 медиафайлов; единственный реальный корпус legacy-манифестов | `split`: classify/dedupe по `schema_version`, manifest shape, completion state, resume state, legacy edge case, malformed/partial → в active resources только **минимальный representative corpus** для tolerant-reader tests. Полный набор — во внешний retirement bundle как historical evidence. **Не делать 749 файлов permanent architecture anchor** | representative corpus отобран и версионирован; полный набор выгружен наружу; tolerant-reader tests зелёные | **PLAN-14D** |
| C33 | `src/size_comparison_engine.py` (720 строк) | `pipeline.py` | **FACT** + **DEFER** | входит в C30; собственный test-модуль `tests/test_size_comparison_engine.py` | `delete` после KSG (**OD-10**): сохраняются алгоритм, visual logic, edge cases, полезные проверки и запись «что стоит восстановить». **Capability внутри PLAN-L не мигрируется.** Формат при необходимости реализуется отдельным будущим product slice на новом canonical core | salvage записан в `Knowledge salvage log`; движок и его тест удалены | **PLAN-L0 → L3** |

## Ревизия 2.1 findings (C34–C50)

Зафиксировано 2026-07-31 по evidence
`docs/audits/CRITICAL_INPUT_SEARCH_DEEP_DIVE_2026-07-31.md` и
`docs/audits/SECONDARY_ARCHITECTURE_FINDINGS_DEEP_DIVE_2026-07-31.md`
(контролируемые offline-пробы, сеть/платные API/render не использовались).
Классы доказанности: **FACT** / **INFERENCE** / **DEFER**.

**Общее правило для каждой строки ниже:**

```
replacement working → callers migrated → targeted/full green → reviewer/gates
                    → затем retirement
```

Ни одна строка не даёт права на действие. Ни одна из них ещё не исполнена.

| ID | Предмет | Класс | Evidence / исправленная формулировка | Action | Gate |
|---|---|---|---|---|---|
| C34 | `query_adapter` GLOSSARY substring matcher | **FACT** | матчинг подстрокой даёт ложные срабатывания (термин «лёд» внутри несвязанного слова) и не знает морфологии — пропускает единственное релевантное слово | **MIGRATE THEN DELETE**: состав терминов сохраняется как seed, harmful матчер заменяется (границы слова + нормализация) | **PLAN-9B-1 → PLAN-9B-3** |
| C35 | topic-hardcode `provider_queries` под одну тему (orca) в `src/news/script_generator.py` + его тест | **FACT** | доказывает, что `VisualBrief`/`provider_queries` — **уже рабочий transport contract**; но заполняется только для одной темы и скрывает дефект на «своей» теме | **MIGRATE CAPABILITY THEN DELETE**: перенести форму ответа, трёхуровневую структуру запросов и `must_avoid` как часть смысла, затем удалить hardcode | **PLAN-9B-2 → PLAN-9B-3** |
| C36 | `legacy_broad_query` в legacy visual-plan format | **FACT** | дописывается в каждую сцену и **не доходит до провайдера ни разу**: `source_is_latin` — свойство всего набора, поэтому русский `primary_query` выбрасывает английский alternative вместе с собой. Шум в persisted-плане | **DELETE — только после** работающей замены (9B-1 и исправления проверки `source_is_latin` на уровне элемента), иначе покрытие на переходный период падает до нуля | **PLAN-9B-3** |
| C37 | deprecated `make_stock_query` в `src/news/visual_plan.py` | **FACT** | deprecated, production-callers отсутствуют | **DELETE** после gate, вместе с C36 | **PLAN-9B-3** |
| C38 | `src/assets/semantic_selection/query_generator.py` + `_animal_category` | **FACT** | **не участвует** в формировании remote-запросов; его callers питают envato-метаданные и отчёты. Содержит полезную лестницу `exact → broad → environment → atmospheric` | **MIGRATE KNOWLEDGE/CALLERS THEN RETIRE** — только после миграции **всех** callers | **PLAN-9B-3** (открытый вопрос: семантика callers построчно не читалась) |
| C39 | несколько поколений query generation в репозитории | **FACT** | сосуществуют legacy-, semantic- и adapter-поколения; canonical boundary remote-запросов — `src/assets/query_adapter.py` | **CONVERGENCE к фактическому query boundary**; второй query pipeline, `TranslatorService`, `SearchEngine` и `QueryOrchestrator` **не создаются** | **PLAN-9B** |
| C40 | глобальная локальная стоковая библиотека | **FACT** | **Исправлено ревизией 2.1.** **Не** «три независимых implementation»: один `media_index`, **один** rights-authority `apply_policy_to_candidate`, **два** matcher'а, несколько consumers/wrappers; legacy path использует **ту же** `media_library.search_local_assets`, что и канонический. Доказанных расхождений live-путей ровно **два**: missing `provenance` и `review_required=True`; обратных — **ноль**. Аргумент про `RIGHTS_REFERENCE_ONLY` **опровергнут** (значение перезаписывается политикой). Дополнительно: `duplicate_penalty` в `rank_local_assets` — **мёртвый код** (`used_asset_ids` вызывает `continue` раньше применения penalty) | **ONE CANONICAL OWNER глобальной локальной стоковой библиотеки:** canonical matcher/provider boundary · harmonize provenance/review semantics · salvage diversity reserve (C47) · удалить superseded wrappers/path · **четвёртый путь запрещён**. **User/manual project assets и project pool — отдельные legitimate capabilities и в конвергенцию не входят.** `duplicate_penalty` убирается вместе с этим слайсом | **PLAN-10D** |
| C41 | provider declarations vs фактический registry | **FACT** | **Исправлено ревизией 2.1.** Гипотеза «пять расходящихся реестров, всё свести к `providers/registry`» **опровергнута**: это разные legitimate facts (actual constructed providers · capabilities · fallback language info · source-class priority · diagnostics inventory · availability), таблицы корректно фильтруются по availability, `ProviderCapabilities.query_languages` **уже** имеет приоритет над fallback-таблицей | Остаточный cleanup, **не** конвергенция: (a) `local_library` declaration mismatch (объявлен провайдером с поддержкой RU, но не создаётся, а реальный локальный поиск идёт мимо адаптера) → **PLAN-10D**; (b) вестигиальный `DEFAULT_PROVIDER_ORDER` → opportunistic cleanup; (c) осиротевшее имя `unsplash` → opportunistic cleanup. **PLAN-10B owner-ом не является (D-2); отдельный PLAN-ID не создаётся** | **PLAN-10D** + opportunistic |
| C42 | `apps/news_to_short` — `--text` / `--text-file` **и** `--assets` | **FACT** | **Исправлено 2026-08-01.** Две возможности вне явного контракта канонического `create`: (A) именованный source-text вход `--text`/`--text-file` — тот же downstream уже достижим через `create --pasted-script/--script-file` при default/legacy unspecified `content_input_mode`, поэтому 9B-5a даёт **имя, валидацию и документацию**, а не новый script engine; (B) `--assets` → `NewsJob.user_assets` — **доказанного эквивалентного create-time входа у канонического `create` нет** (второй носитель `pipeline.py --news-to-short --assets` умирает в PLAN-L4). Прежнее «единственная уникальная бизнес-возможность» опровергнуто. У пакета есть test-callers и собственный `README.md` | (A) **MAKE CANONICAL CONTRACT EXPLICIT (9B-5a)**; (B) **MIGRATE OR EXPLICIT OWNER RETIREMENT DECISION** — молчаливая потеря `--assets` запрещена; **RETIRE wrapper (9B-5b)** только после полного **capability parity check** и миграции сохраняемых capabilities и всех callers (OD-2, OD-19, D-1, K08). Точный public CLI для user-assets — implementation decision и public-surface tripwire | **PLAN-9B-5a → PLAN-9B-5b** |
| C43a | idempotency contract defect: explicit `stage=` path отключает output-validated idempotency ADR 0006 — **частично закрыт, residual остаётся** | **FACT** | **Обновлено 2026-08-08 docs-only reconciliation (HEAD `7a8142f`).** PLAN-STAB-2 (`0eea5be`) сузил дефект: условие в `src/news/pipeline.py:219` теперь `not force_stage and ... and (not stage or stage_name == "final_render")`, то есть explicit `stage=` соблюдает контракт **только** для `final_render`. Residual: для всех остальных стадий explicit-режим по-прежнему переисполняет завершённые локальные стадии. Прежняя редакция строки ниже описывает состояние **до** PLAN-STAB-2 и как current fact больше не читается. Исходная запись: условие `and not stage` в `src/news/pipeline.py` означало, что при явно запрошенной стадии проверка «completed + валидный output → пропустить» не применяется. Batch-режим (`until_stage=`) контракт **соблюдает**; explicit-режим повторно исполняет завершённые локальные стадии. Контракт для `stage=` не покрыт ни одним тестом. **Повторных платных операций нет** (несколько независимых guard'ов + существующие тесты); повторяются только локальные preview/final render. Вызовов **4–7** в зависимости от режима, не «ровно 7». **Severity: MEDIUM** | точный contract fix: один контракт идемпотентности, действующий во всех режимах вызова. Owner — **ADR 0006 / `src/news/pipeline.py`**, отдельный будущий bounded slice. Предусловие: подтвердить фактических `resume`/`force-stage`/`stop-stage` callers и public behavior | future bounded pipeline-contract slice |
| C43b | возможная поздняя orchestration convergence | **INFERENCE** | расслоение application orchestration / news pipeline ownership зафиксировано **ADR 0009 намеренно**; «два конкурирующих owner» **опровергнуто**. Дублируется ровно один факт — порядок хвостовых стадий | «один владелец порядка стадий» — **не** принятое решение. Выполняется **только если** после C43a остаётся архитектурная необходимость | **PLAN-13B** |
| C44 | export catalog mismatch | **FACT** | catalog объявляет **5** active export targets; три production-owner согласованно работают с **3**. `supported_export_targets` и `safe_zone_profile` имеют **ноль** production-читателей и в render decision не участвуют — каталог единственный outlier. Master копируется побайтово, адаптации под площадку нет | **truthful catalog**: убрать несуществующие targets из `active` **либо** перевести в `planned` — по фактическому intended product contract в момент implementation. **Создавать byte-identical копии ради соответствия каталогу запрещено.** **PLAN-11 = evidence gate**, обязанный ловить ложные product capabilities; **implementation owner — будущий bounded `production_catalog` slice**. Нового PLAN-ID нет | **PLAN-11** (gate) + future catalog slice |
| C45 | несколько lossy generations в final render | **FACT** + **INFERENCE** | **Исправлено ревизией 2.1.** Нормальный путь: segment encode CRF 23 → concat **`-c:v copy`** (не перекодирует) → audio + exact-duration encode CRF 20 → ASS subtitle encode CRF 21 → copies. Три lossy generations возникают **при audio + ASS subtitles**; без озвучки или без ASS — две, без обоих — одна. CRF 20 имеет документированную причину (`-shortest` + `-c:v copy` промахивается по длительности). **INFERENCE:** величина ущерба **никем не измерялась** — ни один аудит не рендерил | **PLAN-8 = roadmap owner** product-quality item. **Implementation owner — будущий bounded renderer slice, characterization первым.** Первый разумный кандидат: объединить audio/duration encode и subtitle burn в один encode, если characterization докажет эквивалентность. Полный filtergraph single-pass — отдельное более крупное исследование. «Single-pass как простой fix» — **неверно** | **PLAN-8** (roadmap) + future renderer slice |
| C46 | legacy query expansion ladder (`build_query_variants`) | **FACT** | настоящая лестница расширения: суффиксы, усечение, mood, channel-расширения | **MIGRATE KNOWLEDGE** → потребитель **PLAN-9B-2**. Старый pipeline ради этого не сохраняется | **PLAN-L0** |
| C47 | legacy local diversity reserve | **FACT** | `min_local_diversity_per_scene` / `reserved_download_slots`: «не заполняй сцену копиями одного локального клипа, оставь слоты под новый материал». Современного эквивалента **нет** — прямо релевантно проблеме повторяющихся визуалов | **MIGRATE KNOWLEDGE** → потребитель **PLAN-10D** | **PLAN-L0** |
| C48 | историческая практика внешних EN visual keywords | **FACT** | `visual_keywords` в legacy `content/**/*.json` — **входные данные**, а не выход кода: provider-ready английские ключи существовали отдельным полем, отделённым от нарратива | **MIGRATE KNOWLEDGE** (ADR/registry). Реализацию не восстанавливать | **PLAN-L0** |
| C49 | subprocess network-guard measurement | **FACT** | `tests/network_guard.py` живёт внутри test-пакета и дочерним процессом **не наследуется**. На audit HEAD `adcbb19` subprocess-модулей **12** (ранее записано 7). Это **measurement, не invariant** | зафиксировать как измерение; архитектурное решение по kill-switch **сейчас не принимается** — механизм и owner остаются implementation-time решением. **PLAN-6B остаётся report/measurement owner в своей текущей границе** | **PLAN-6B** (measure) + позднее решение owner |
| C50 | **rights fail-open:** явный `review_required=True` local-library record проходит канонический путь | **FACT** + **INFERENCE** | policy-правило для локальной библиотеки устанавливает `review_required: false` и **перезаписывает исходный флаг записи**, поэтому явно помеченная на ревью запись проходит. Обратного случая нет. Дефект не описан ни в одном предыдущем аудите | **[HARD] rights correctness.** Отдельный bounded fix с собственной verification: policy **не может silently снять** explicit `review_required` без доказанного разрешённого контракта. Owner — `apply_policy_to_candidate` / `with_policy_decision`. **Не смешивать с PLAN-10D architectural convergence** | отдельный bounded rights slice; исполним независимо после зелёного PLAN-4. **Deadline (2026-08-01): обязан быть CLOSED до расширения/convergence/повторного включения Global Local Library в PLAN-10D, до финального product evidence PLAN-11 / M1 и до любого live/publish-ready workflow, реально использующего Global Local Library asset с policy normalization** |

Строки C34–C50 закрываются каждая своим gate по общему `Closure rule` ниже.

**Исполнено на 2026-08-07 (обновлено closure-слайсом PLAN-9B-3).** Прежняя
редакция этой строки утверждала, что ничего из перечисленного не удалено; это
перестало соответствовать факту и исправлено здесь.

- **C34** — исполнена через **PLAN-9B-1**, commit `141beae`. Harmful GLOSSARY
  **substring** matcher (строка `if russian in text and english not in
  matched:`) физически удалён и заменён матчингом по границам токенов с
  ограниченной морфологией (`_word_tokens` / `_contains_lexicon_phrase` /
  `_lexicon_token_matches` / `_GLOSSARY_STEMS` / `_GLOSSARY_STEM_ENDINGS`).
  Словарь `GLOSSARY` сохранён намеренно — этого требует сам action строки
  («состав терминов сохраняется как seed»). Substring-матчинга против
  `GLOSSARY` на HEAD не осталось, поэтому у второй половины gate
  (`→ PLAN-9B-3`) объекта удаления не было; строка исполнена, а не пропущена.
- **C35, C36, C37, C38** — исполнены через **PLAN-9B-3**, commit `72221e1`,
  строка **R01** таблицы `Retired` ниже.
- Остальные строки C34–C50 не удалены и закрываются каждая своим gate.

**Non-blocking observation F3 (independent review PLAN-9B-3, 2026-08-07;
pre-existing, вне diff `72221e1`).** Относится к истории C36/R01. При
отсутствии брифа `_english_queries` в `src/assets/query_adapter.py` собирает
запрос из glossary- и latin-токенов текста сцены, поэтому ретайренный legacy
broad literal, всё ещё присутствующий в persisted-плане, записанном до слайса,
теоретически может вернуться этим путём. Единственная действующая защита —
exclusion-список `_LEGACY_BROAD_QUERIES` (см. ниже). Наблюдение записано как
non-blocking follow-up; нового PLAN-ID и нового finding-ID под него не
создавалось, repair в closure-слайсе не выполнялся.

**Compatibility guard `_LEGACY_BROAD_QUERIES` — KEEP с exit condition.**
Exclusion-список из четырёх строк в `src/assets/query_adapter.py`
**retirement candidate'ом PLAN-9B-3 не является и никогда не являлся**: он
создан commit `141beae` в **PLAN-9B-1**, то есть позже составления списка
кандидатов (ревизия 2.1, 2026-07-31); он не производит запросы, а только
отфильтровывает четыре ретайренных литерала при tolerant flat read
(`_source_language_queries`) планов, записанных до слайса. Current owner —
`src/assets/query_adapter.py`; replacement — canonical PLAN-9B-2 ladder
`src/content/visual_planning/expansion.py`, пишущая новые планы без этих
литералов. **Exit condition:** guard снимается, когда pre-slice persisted
планы перестают читаться; до этого снятие вернуло бы legacy broad literal в
живой запрос (см. F3 выше). Бессрочным `keep` строка не является.

## PLAN-1D findings (C51–C52)

Зафиксировано 2026-08-01 слайсом `PLAN-1D-routing` от clean HEAD `b396a50`.
Проверено чтением файлов и листингом каталогов; production-код, tests, схемы и
runtime не затрагивались. Классы доказанности те же: **FACT** / **INFERENCE** /
**DEFER**. Ни одна строка не даёт права на перемещение, создание или удаление
чего-либо: PLAN-1D только записал findings.

| ID | Предмет | Класс | Evidence | Action / target | Gate |
|---|---|---|---|---|---|
| C51 | `docs/current/PRODUCT_EVIDENCE_GATE.md` внутри `docs/current/` | **FACT** | frontmatter файла — `status: historical_reference` (`last_verified_commit` `05cc8ed`, `last_verified_date` 2026-07-28); это единственный такой файл в `docs/current/`. `tools/qa/check_agent_docs.py` требует `status: current` только от `START_HERE.md`, `SYSTEM_MAP.md` и `CURRENT_STATE.md`, поэтому расхождение не ловится автоматически. Его `source_paths` указывают на пять путей внутри gitignored `projects/`, поэтому смена `status` дефект не чинит | **не считать active current document**; `move` из `docs/current/`. **Физическое перемещение выполняет PLAN-12A, а не PLAN-1D** — в этом слайсе файл не перемещался и не изменялся | **PLAN-12A** |
| C52 | корневой `skills/` и Claude Code project-skill discovery | **FACT** + **INFERENCE** | **FACT:** каталог со skills — корневой `skills/` (6 skills); `.claude/` в репозитории содержит только `settings.json`, `settings.local.json` и `scheduled_tasks.lock` — каталога `.claude/skills/` нет. Claude Code автоматически корневой `skills/` как project skills не загружает; наличие `SKILL.md` само по себе auto-discovery не доказывает. **INFERENCE / `[ПРЕДП]`:** discovery Codex через `skills/*/agents/openai.yaml` **не проверен** и фактом не записывается. Различать четыре состояния: наличие файлов · manual loading · auto-discovery · actual invocation | решение о размещении и способе discovery принадлежит **PLAN-6C / PLAN-6D / PLAN-6E** согласно execution plan. **Второй набор skills сейчас не создаётся**, файлы не перемещаются и не дублируются | **PLAN-6C / PLAN-6D / PLAN-6E** |

## Motion rendering findings (C53–C62)

Зафиксировано 2026-08-01 слайсом `MOTION-ROADMAP-1` от clean HEAD `35325b4`.
Источник — read-only rendering / motion-design / AI-directed video аудит;
каждый пункт **перепроверен по фактическому коду** перед записью. Сеть,
providers, Vision, TTS, render и установка зависимостей не выполнялись.
Классы доказанности прежние: **FACT** / **INFERENCE** / **DEFER**.

**Ни одна строка не даёт права на действие.** Destructive cleanup по этим
находкам сейчас **не разрешён**: каждая закрывается своим gate по общему
`Closure rule` ниже, а замещение подчиняется **PD-11** (`PRODUCT_PLAN.md`).

| ID | Предмет | Класс | Evidence | Action / disposition | Gate |
|---|---|---|---|---|---|
| C53 | Story Card renderer на MoviePy | **FACT** | `src/production_plan/story_card_short_render.py` (528 строк) — второй способ композиции в активном продукте: `moviepy.VideoClip` + покадровая Pillow-вёрстка с ручным измерением метрик шрифта. Единственный активный production-caller MoviePy, помимо duration probes (C54). Шаблон `story_card_text_only_v1` объявляет его в `workflow_binding.renderer` (`src/production_catalog/catalog.py`) | **MIGRATE_CAPABILITY_THEN_DELETE.** Замена — выбранный production web motion backend. Шаблон **сохраняется**, удаляется только реализация. Обязателен parity: functional · adaptive text · vertical layout · visual parity или улучшение · стабильный Windows render | **MOTION-CS2** (parity case) → **MOTION-CS4**; PoC + parity + caller migration + targeted/full |
| C54 | MoviePy duration probes | **FACT** | `src/audio/tts/elevenlabs_provider.py::_probe_audio_duration` и `src/audio/voice_cli.py::_duration` импортируют `AudioFileClip` только чтобы получить длительность не-WAV файла, в `try/except` с возвратом `0.0`. Существующий владелец того же факта — `src/assets/frame_sampling.py::ffprobe_media_info` (ключ `duration_sec`), которым пользуется остальной код | **REPLACE_WITH_EXISTING_OWNER_THEN_DELETE.** Замена — существующий ffprobe helper; новый owner не создаётся | caller search + targeted audio tests |
| C55 | зависимость `moviepy` | **FACT** | `requirements.txt` и `pyproject.toml` объявляют `moviepy==2.2.1`. Активные callers: C53, C54. Остальные (`src/music_tools.py`, `src/self_eval.py`, `src/video_renderer.py`) — legacy-семейство, уже назначенное к удалению в **PLAN-L3** | **REMOVE_AFTER_LAST_CALLER.** Снятие с зависимостей допустимо **только** после закрытия C53, C54 и PLAN-L3. **Не объявлять удалённой заранее** | dependency/caller search + `full` |
| C56 | рисующая часть `generated_infographic` | **FACT** | `src/assets/generated_infographic.py`: `CANVAS_WIDTH`/`CANVAS_HEIGHT` — константы модуля, и `build_generated_asset` **выбрасывает исключение** при ином размере, поэтому горизонтальный формат физически недостижим; палитра зашита в код; вёрстка — ручная арифметика курсора; `_load_font` при отсутствии кандидатов молча падает в `ImageFont.load_default()`, из-за чего детерминизм машинно-зависим (docstring признаёт «on the same machine») | **MIGRATE_DRAWING_CAPABILITY.** Замена — web motion backend + ECharts. **PRESERVE (не удалять):** правило «нет evidence → нет фактической диаграммы» (`spec_from_scene` возвращает `None` без авторских значений) · fingerprint спеки · создание project-owned актива `build_generated_asset` с license/provenance/checksum · technical validation · минимальная offline аварийная карточка | **MOTION-CS4**; после миграции прежний owner теряет право рисовать production-инфографику |
| C57 | stock fullscreen FFmpeg path | **FACT** | `src/news/final_renderer.py` — canonical владелец финального рендера активного `fullscreen_voiceover_v1`; единственный caller — стадия `final_render` в `src/news/pipeline.py`. Покрыт end-to-end тестом с реальным offline-рендером (`tests/test_news_to_short_renderer.py`) | **KEEP_AND_IMPROVE.** Это canonical stock composition path и canonical final assembler. **Не должен попасть под широкий renderer cleanup** и не замещается motion-бэкендом. Доработка — предмет **MOTION-CS1**, а не замена | — (защитная запись) |
| C58 | недостижимый `preview_render` | **FACT** | `NEWS_TO_SHORT_STAGES` (`src/news/models.py`) ставит `preview_render` **раньше** `final_render`, но `src/news/preview_renderer.py` требует `master_1080x1920.mp4`, который пишет только `final_render` (`src/news/final_renderer.py`). В `draft_complete` итоговый файл называется `draft_1080x1920.mp4`, поэтому preview не резолвится **никогда**. На первом проходе стадия всегда возвращает `blocked` | **FIX (не удаление).** Порядок стадий и имя файла — предмет **MOTION-CS1**. Блокирует scene preview, Vision review композиции и bounded repair сильнее, чем отсутствие motion-бэкенда | **MOTION-CS1** |
| C59 | FPS/canvas зашиты в нескольких местах | **FACT** | `30` зашит в ffmpeg-фильтрах `src/news/final_renderer.py` (`fps=30` в `_video_filter`, `_render_image_segment`); `config/render_presets/story_card_short_v1.json` объявляет свои `fps`/`resolution`; `channels/*/channel_config.json` объявляет `fps`, **который никто не читает** — это прямо задокументировано в `src/config_resolver/keys.py` | **CONVERGE TO ONE CONTRACT.** Единый источник canvas/FPS/pixel-format/duration — предусловие любого второго backend, потому что это половина контракта сегмента | **MOTION-CS1** |
| C60 | отсутствие per-scene render fingerprint/cache | **FACT** | `src/news/final_renderer.py::_create_scene_segments` всегда пишет `render/segments/{scene_id}{suffix}.mp4` с флагом `-y`; ключа кэша нет. Resume — только stage-level (`src/news/project_store.py::is_stage_completed` → `validate_stage_output`). Перерендер одной сцены сегодня невозможен. Готовый образец content-addressed ключа уже есть в репозитории: `src/assets/semantic_visual_cache.py::compute_semantic_cache_key` | **ADD FINGERPRINT/CACHE.** Обязательно. **Место persistence не утверждено** — см. `OWNER_DECISION_REQUIRED` в MOTION-CS1: сначала проверяются существующий render manifest, project state и tolerant readers; `assets_manifest` **не выбирается автоматически**; любое изменение persisted schema — owner tripwire | **MOTION-CS1** + owner decision |
| C61 | отсутствие visual regression рендерера | **FACT** | В `tests/` нет golden-frame / perceptual-baseline теста рендерера: совпадения `perceptual_hash` встречаются только в semantic/preview/temporal-модулях. Инструменты для регрессии уже в репозитории и новых зависимостей не требуют (`sha256_file`, perceptual hash, попиксельная разница в `src/assets/temporal_video_analysis.py`) | **ADD BEFORE ANY RENDERER CHANGE.** Предусловие безопасного изменения рендерера, включая характеризацию C45 | **MOTION-CS1** (characterization первым) |
| C62 | design tokens размазаны по шести источникам | **FACT** | `channels/*/subtitle_style.json` (шрифт, safe zones, margins) · `channels/*/style.json` (только свободные строки, не токены) · `channels/*/channel_config.json` (resolution/fps) · `config/render_presets/story_card_short_v1.json` (цвета, шрифты, layout, radii, encoding — **и литеральный текст конкретного ролика**) · зашитая палитра в `src/assets/generated_infographic.py` · зашитые CRF/preset/fps в `src/news/final_renderer.py`. Canonical owner темы отсутствует | **ONE TOKEN OWNER.** Точное место (`channels` либо `config/design_tokens`) — `OWNER_DECISION_REQUIRED`. Отдельно: развести токены и контент конкретного ролика в существующем render preset. **Design system на каждый backend запрещена** | **MOTION-CS3** + owner decision |

Строки C53–C62 закрываются каждая своим gate по общему `Closure rule` ниже.
Ничего из перечисленного пока не удалено.

## Plan↔code reconciliation finding (C63)

Зафиксировано 2026-08-08 docs-only reconciliation от clean HEAD `7a8142f`.
Источник — перепроверка подтверждённых выводов read-only architecture audits по
фактическому коду. Production-код, tests, схемы, config и runtime **не
изменялись**; дефект **не исправлялся**.

| ID | Предмет | Класс | Evidence | Action / disposition | Gate |
|---|---|---|---|---|---|
| C63 | author `--visual-brief` не достигает сцен на topic/article paths | **FACT** | `ContentCreationRequest.visual_briefs` доходит до `NewsJob.visual_briefs` и до `ScriptRequest.visual_briefs` (`src/news/script_generator.py:89`), но единственный consumer `request.brief_for(...)` — `src/content/script_engine/providers/user_supplied.py:112`. Author overlay визуального плана (`_apply_scene_briefs`, `src/content/visual_planning/engine.py:77`) читает только `script.scenes[].visual_brief`. Для `topic` / статьи выбирается `deterministic_local` (`DEFAULT_PROVIDER_ID`, `src/content/script_engine/registry.py:15`) либо другой не-user provider, который брифы не переносит, поэтому явный авторский бриф на этих путях молча теряется. Заявление плана «explicit author brief всегда выигрывает» (PLAN-9B-PRODUCER) верно только для user-supplied script/narration | **MISSING OWNER CANDIDATE.** Живого PLAN-ID у этого residual нет: family PLAN-9B и PLAN-9B-PRODUCER закрыты, а естественный дом — существующее visual-planning / script-provider ownership. Второй brief owner, второй planner и новый storage создавать запрещено. Новый PLAN-ID этой записью **не** создаётся | owner decision о владельце; до него — только запись |

## Retrieval engine audit findings (C64–C74)

Зафиксировано 2026-08-13 docs-only слайсом от clean HEAD `f3b607a`. Источник —
read-only аудит retrieval/material engine
([RETRIEVAL_ENGINE_AUDIT_2026-08-13.md](../audits/RETRIEVAL_ENGINE_AUDIT_2026-08-13.md)),
но **каждая строка перепроверена по фактическому коду** перед записью: внешний
отчёт — гипотеза, репозиторий — истина. Production-код, tests, схемы, config и
runtime **не изменялись**; сеть, providers, Vision, TTS и render не выполнялись.
Классы доказанности прежние: **FACT** / **INFERENCE** / **DEFER**.

**Ни одна строка не даёт права на действие**; каждая закрывается своим gate по
общему `Closure rule` ниже. Нумерация здесь сквозная по реестру и с номерами
внешнего отчёта не совпадает:

| В отчёте | Здесь | Почему |
|---|---|---|
| `C64`–`C70` | C64–C70 | без изменений |
| `C72` | C71 | номер сдвинут, потому что предыдущий кандидат отклонён |
| `C75` | C72 | то же |
| `C71` (tracked `outputs/*.json`) | — | **не новая находка**: уже записана строками **C19**, **C29** и **A02** |
| `C73` (висячий corpus path) | — | **опровергнуто**: `tests/plan9d_corpus_builder.py:104-110` документирует намеренную замену корпуса в PLAN-9D-A, якорь — коммит `SUPERSEDED_CORPUS_COMMIT` |
| `C74` (классификация тестов) | — | **не противоречие**: метка модуля и класс отдельных проверок — разные оси; примирение уже записано строкой `tests/test_size_comparison_engine.py` в Knowledge salvage log |
| разделы future-useful | C73–C74 | записаны как inventory будущей ценности, без прав на действие |

| ID | Предмет | Класс | Evidence | Action / disposition | Gate |
|---|---|---|---|---|---|
| C64 | третий retrieval-путь: fixed-plan `solar_vs_nuclear_render` | **FACT** | `src/production_plan/solar_vs_nuclear_render.py` держит собственный поиск и скачивание: `select_and_download_stock:152` (вызов `:63`), собственный `_download_file`, прямые вызовы module-level `search_videos` из `pexels_provider`/`pixabay_provider`. Достижим из legacy CLI: `pipeline.py:44` импортирует `build_solar_vs_nuclear_video`, вызов — `src/legacy_pipeline/maintenance.py:403`. Реестр знал этот файл как часть Solar production plan (**V04**, **N05**), но **не как отдельный retrieval-путь** | `obsolete-with-legacy`. Ретайр вместе с legacy-семейством (**C08**, **C30**); до ретайра действует **C65**. Второй retrieval owner не создаётся: canonical путь — `src/assets/**` + `src/providers/registry` | **PLAN-L0 → L3 → L4** |
| C65 | обход default-deny сети в legacy-стеках | **FACT** | `src/runtime_network.py` объявляет default-deny по классам, но legacy-путь ходит в сеть голым `requests` мимо `require_network`: `src/asset_finder.py:109,134,151` · `src/video_asset_engine.py:408,445,595` · `src/music_engine.py:161,227` · `src/production_plan/solar_vs_nuclear_render.py:543` · module-level функции провайдеров `src/providers/pexels_provider.py:191,204`, `pixabay_provider.py:186,198,217`, `unsplash_provider.py:14`. Смежно и тем же способом: `src/voice_engine.py:200` (платный TTS). Формулировка внешнего отчёта «6 call-sites» **занижена** | `правка`, не удаление. **OWNER DECISION 2026-08-13:** временный «legacy network gate» **не разрешён** — обёртка call-sites в `require_network` не пишется. Вопрос отложен до окончания Review #2 и переформулирован: сначала выясняется, можно ли ретайрить legacy retrieval stacks целиком, потому что улучшать код, который сразу после этого исчезает, смысла не имеет. Находка остаётся **открытой**; PLAN-ID и номер VA-NEW не создаются | Review #2 → решение «retire или gate» → **PLAN-L3** |
| C66 | `src/providers/unsplash_provider.py` + legacy-экспорты `src/providers/__init__.py` | **FACT** | файл — не `StockProvider`, а голая функция с `requests.get:14`; production-callers и owning test отсутствуют, единственная ссылка — реэкспорт из `__init__`. Осиротевшее **имя** `unsplash` в таблицах данных и вестигиальный `DEFAULT_PROVIDER_ORDER` уже записаны **C41** (пункты (c) и (b)) и здесь не дублируются | `delete` через retirement package «retrieval-orphans»: KSG (сохранять нечего — провайдер никогда не подключался), затем annotated tag + `git bundle` + строка `Retired` | **PLAN-L0** → retirement |
| C67 | заглушка `vision_validator` и ключ канала `vision_validation_enabled` | **FACT** | заглушка и её ноль callers уже описаны секцией **C01-SEM**; новое — судьба ключа: `channels/nature_science_news_ru/channel_config.json:102` его объявляет, а `src/news/asset_manifest_builder.py:290` и `src/production_plan/youtube_shorts.py:211` пишут его константой `False`; фактический гейт Vision — `semantic_visual.enabled` вместе с `semantic_rerank_enabled` | `delete` заглушки вместе с ключом одним слайсом. **OWNER DECISION REQUIRED**: удаление ключа меняет versioned config канала. Vision через `vision_validator` не воскрешать — canonical owner `semantic_visual_service` | **PLAN-9E** |
| C68 | мёртвый пост-review селектор | **FACT** | `src/assets/review_bundle.py:199` `select_candidate_after_review` с захардкоженными весами `:274`; production его не вызывает — `src/news/asset_manifest_builder.py:648` жёстко ставит `after_id = before_id`. Единственные callers — `tests/test_visual_preview_integration.py:188,198,208`. После PLAN-9C выбранного кандидата меняет только Vision-переотбор | `delete` одним слайсом (код + его тесты + мёртвые config-веса из **C69**) **после** того, как **PLAN-9E** зафиксирует, нужен ли пост-review переотбор вообще. Второй селектор не восстанавливать | **PLAN-9E** → retirement |
| C69 | ложные пульты управления в retrieval-конфигах | **FACT** | `config/visual_preview.json` читается (`src/assets/visual_preview.py:30`), но ключи `technical_score_weights` (строка 21), `rerank_weights` (30) и `refresh_policy` (18) не читает ни одна строка кода — фактические веса захардкожены. `config/semantic_visual.json` держит два независимых лимита кандидатов (`maximum_candidates` = 5, строка 6, против `openai.maximum_candidates_per_scene` = 3, строка 29) и два бюджета (строки 13 и 32). Retrieval-блоки `config/video_style.json` читаются только по `enabled` (носитель умирает в L3 — **C24**, **C30**) | `правка`: свести к одному источнику либо удалить ключ вместе с иллюзией настраиваемости. Ложная ручка опаснее её отсутствия: следующий агент будет крутить её вместо кода | **PLAN-9E / PLAN-10C** (semantic_visual, visual_preview) · **PLAN-L3** (video_style) |
| C70 | `schemas/*.json` не являются enforcement и отстают от кода | **FACT** | единственный читатель схем — `tests/test_artifact_schemas.py:11` (`SCHEMA_ROOT`); production ими ничего не валидирует. `schemas/assets.schema.json` не знает реально пишущихся ключей — `asset_search_fingerprint` в файле отсутствует — и спасается `additionalProperties: true`. `schemas/evidence.schema.json` отстаёт от `EVIDENCE_RECORD_SCHEMA_VERSION = 2` (`src/project_foundation/models.py:65`) | **OWNER DECISION REQUIRED**: либо догнать поля и сделать схемы enforcement, либо честно пометить их характеризационными. Третий контракт формы манифеста не создавать | owner decision → **PLAN-13** |
| C71 | production-правило прав для тестового провайдера `fake` | **FACT** | `config/license_policy.json:35-44` объявляет полноценное правило прав для провайдера `fake` (`fake_test_license`, `https://fake.local/...`) внутри боевой политики — единственного источника rights (`src/assets/license_policy.py`, fail-closed) | `правка`: вынести в тестовый конфиг **или** явно записать, почему тестовый двойник имеет права в production policy. Fail-closed и `review_required` не ослаблять | owner decision → rights owner |
| C72 | припаркованный слой `semantic_decision_policy` | **FACT** + **DEFER** | `src/assets/semantic_decision_policy.py` калибрует пороги suitable/review/unsuitable поверх сырого Vision-результата; ноль production-callers (факт уже записан **C01-SEM**), owning test есть (`tests/test_semantic_decision_policy.py`). Действующие пороги живут в `config/semantic_visual.json` и `candidate_ranker` | **OWNER DECISION REQUIRED**, ровно две опции: (a) explicit item к **PLAN-9E** / **PLAN-10C** как калибровка порогов, (b) retire по KSG. Молчаливое удаление запрещено; второй слой порогов рядом с существующим не создавать | **PLAN-9E / PLAN-10C** |
| C73 | `src/assets/temporal_video_analysis.py` — готовый детектор «живого» отрезка клипа | **FACT** | ноль production-callers, owning test есть (`tests/test_temporal_video_analysis.py`); модуль уже считает hash-дистанции между кадрами, per-position crop и contact-sheet. Для longform не хватает ровно одного звена — источникового временного диапазона: в модели кандидата нет `clip_start`/`clip_end`, а `src/news/final_renderer.py` рендерит сегмент всегда от t=0 источника | `keep` как future-useful. Longform переиспользует **этот** модуль как основу выбора отрезка; **второй segment engine не создаётся** — рабочий образец `-ss`/`-t` уже есть в `anime_factory` (**C07**, do-not-touch) | **M5** (owner packaging label; PLAN-ID этой строкой не создаётся) |
| C74 | пиксельные метрики качества считаются и никуда не идут | **FACT** | `src/assets/visual_metrics.py:139,158` (`estimate_crop_suitability`) и покадровый `_score_frame` вычисляются на каждом preview, но их потребители — только тесты (`tests/test_visual_preview_foundation.py:301-330`); ни один вход отбора их не читает, а конфиг-веса к ним мертвы (**C69**) | `keep` как future-useful. Quality-aware retrieval начинать с **переиспользования существующих producers**; новый quality engine не писать без доказанного gap. Пороги и веса этой строкой не назначаются | **PLAN-10C** (в связке с предложением RD-C) |

## EXP-001 retrieval findings (C75–C78)

Перенесено 2026-08-13 слайсом AUD-DELTA-CLOSE из
[STOCK_RETRIEVAL_EXPERIMENTS.md](../audits/STOCK_RETRIEVAL_EXPERIMENTS.md).
Причина переноса: журнал экспериментов — evidence, и по правилу
[docs/audits/README.md](../audits/README.md) права на действие он не даёт;
до этой записи четыре подтверждённых дефекта жили только там и могли
потеряться. Дефекты **не исправлялись**; сеть, providers, Vision, TTS и render
этим слайсом не выполнялись.

Разделение доказательности здесь важно и записано явно:

- **структура** (что именно делает код) перепроверена по репозиторию в момент
  переноса — это класс **FACT**;
- **эмпирика** (что именно вернули провайдеры на живом прогоне 2026-08-12) взята
  из журнала и офлайн не воспроизводима — она остаётся ссылкой на EXP-001, а не
  утверждением реестра.

Общий owner всех четырёх строк — существующий **PLAN-10B** (pagination /
provider exhaustion / provider contract behavior). Новый PLAN-ID не создаётся,
номер VA-NEW не выдаётся, `RD-B` остаётся предложением и owner decision не
является. Порядок работ не меняется: строки ждут своего шага.

| ID | Предмет | Класс | Evidence | Action / disposition | Gate |
|---|---|---|---|---|---|
| C75 | Wikimedia-адаптер выбрасывает Commons-видео по mime | **FACT** | `src/providers/wikimedia_commons_provider.py:124` выводит `media_type` только из префиксов `video/` и `image/`, всё остальное даёт пустую строку, и `:125-126` возвращает `None`. Commons отдаёт `.ogv` как `application/ogg`, поэтому файл отбрасывается как неизвестный тип ещё до ранжирования, прав и превью. Эмпирика — EXP-001 (`Root cause`, п. 2) | `правка` внутри существующего provider contract: набор принимаемых mime расширяется до фактически отдаваемых Commons контейнеров. Второй адаптер и второй media-type resolver не создаются; `provider_contract.StockProvider` остаётся единственным контрактом | **PLAN-10B** |
| C76 | глубина поиска Wikimedia: media-type фильтр применяется после выдачи | **FACT** | `:60` отправляет `srsearch` сырым запросом, без `filetype:video`; `:52` считает `limit = min(max(1, request.max_results), self.max_results)`, а production передаёт `max_results=5` (`src/news/asset_manifest_builder.py:470`), поэтому `srlimit=5`. Фильтр по типу стоит **после** — `:86` (`candidate.media_type != request.media_type`), и `:94` режет ещё раз. На Commons, где подавляющее большинство файлов — изображения, из пяти дофильтровых попаданий видео может не остаться ни одного. `self.max_results` по умолчанию 8 (`:35`) и в production не достигается | `правка`: либо запрос сужается до медиатипа на стороне API, либо глубина берётся до фильтра, а не после. Принадлежит контракту exhaustion/pagination, которым владеет PLAN-10B; отдельный «wikimedia-only» путь поиска не создаётся | **PLAN-10B** |
| C77 | форма запроса Internet Archive теряет фразу | **FACT** | `src/providers/internet_archive_provider.py:61` строит `q = f"({request.query}) AND mediatype:{mediatype}"`. Скобки группируют, но не связывают слова: многословный запрос распадается на отдельные термины, и выдача уходит от предмета. Эмпирика — EXP-001: `(cheetah running) AND mediatype:movies` вернул Lamborghini и GTA III; тот же материал находился по точному названию. Сам адаптер исправен — дефект в форме запроса | `правка` формы запроса внутри существующего адаптера. Второй query owner не создаётся: строки по-прежнему приходят из `src/assets/query_adapter.py` (**C39**), провайдер отвечает только за синтаксис своего API | **PLAN-10B** |
| C78 | одна строка запроса уходит провайдерам с разной терпимостью к длине | **FACT** (структура) + **INFERENCE** (масштаб) | `build_scene_queries` (`src/assets/query_adapter.py:270`) — единственная граница запросов, и `search_provider` (`src/news/asset_provider_adapters.py:79`) отдаёт одну и ту же строку каждому провайдеру. Это факт. Вывод EXP-001 — что MediaWiki full-text не терпит лишних слов (длинный шаблон дал 0, короткий `cheetah running` дал релевантное видео), тогда как Pixabay/Pexels терпят — эмпирический и офлайн не проверяется | `правка` в существующих владельцах, не новый слой: провайдер-специфичная **форма** запроса принадлежит provider contract (**PLAN-10B**), а генерация терминов остаётся за expansion ladder. Запрещено: второй словарь синонимов, второй query owner, per-provider копия query-пути. `RD-B` этой строкой не начинается и owner decision не получает | **PLAN-10B** (в координации с границей запросов **C39**) |

## C01-SEM — ownership inventory asset/semantic (PLAN-1C′)

Зафиксировано 2026-08-07 слайсом `PLAN-1C′` от clean HEAD `b0e99a7`, ветка
`governance-reset`. Источник — фактический код, import-граф, реальные callers,
persisted-артефакты проектов, `schemas/` и tests. Production-код, tests, схемы,
config, manifests и runtime **не изменялись**; ни один файл не перемещался; сеть,
providers, Vision, TTS и render не выполнялись. Классы доказанности прежние:
**FACT** / **INFERENCE** / **DEFER**.

**Эта секция закрывает C01-SEM.** Она отвечает ровно на три вопроса контракта —
кто принимает решение о пригодности кандидата, где заканчивается shared service и
начинается workflow policy, и какова роль заглушки `vision_validator` и
подключённого, но не влияющего на отбор `semantic_visual_service`. Она **не даёт
права на действие**: ни одна строка ниже не разрешает переносить файлы, менять
поведение, создавать owner или удалять реализацию.

### Владельцы

Ownership выведено из фактических responsibilities, callers, возвращаемых
значений, мутации состояния, persisted-контрактов и tests; совпадение basename
доказательством не считается.

| Capability / module | Canonical owner | Production callers | Decision authority | Persisted contract | Owning tests | Duplication / overlap |
|---|---|---|---|---|---|---|
| разбор сцены в проверяемые требования | `src/assets/semantic_selection/scene_analyzer.py` (`analyze_scene`) | `news/asset_manifest_builder.py:316`, `production_plan/youtube_shorts.py:254` | **evidence / requirements**, решения не принимает | читает блок `semantic` визуального плана; сам ничего не пишет | `test_semantic_asset_selection.py`, `test_visual_planning_pipeline.py`, `test_semantic_slot_decisions.py` | нет; блок `semantic` производит `src/content/visual_planning` |
| что метаданные провайдера доказывают | `src/assets/semantic_selection/evidence.py` | только `candidate_ranker` и `decision` того же подпакета | **evidence producer** | нет | `test_visual_retrieval_repair.py`, `test_semantic_asset_selection.py` | выделен из `candidate_ranker` намеренно, чтобы score и slot читали одни правила |
| оценка и отклонение кандидата | `src/assets/semantic_selection/candidate_ranker.py` (`rank_candidates`) | `asset_manifest_builder.py:507`, `asset_scene_completion.py:110,248` | **ranking + reject** | пишет в кандидата `selection_decision`, `support_status`, `slot_verdict` | `test_semantic_asset_selection.py`, `test_visual_retrieval_wiring.py`, `test_visual_retrieval_repair.py`, `test_news_to_short_assets.py` | второго ranker нет |
| окончательный выбор кандидата сцены | `candidate_ranker.select_best_candidate` | через `asset_manifest_builder.select_best_with_video:1097` | **decision owner** отбора | выбранный ассет попадает в `scenes[].selected_asset` | `test_semantic_slot_decisions.py`, `test_visual_retrieval_regression.py` | `news/asset_manager._select_best_candidate:150` — построчно та же video-preference обёртка; **не вызывается production-путём**, сохранена как patch-point, закреплена `test_news_asset_manager_contract.py:226` |
| словарь verdict/support и persisted решение | `src/assets/semantic_selection/decision.py` (`DECISION_KEY = "selection_decision"`) | `completion/*`, `news/asset_manifest_builder.py`, `asset_provider_adapters.py`, `draft_completion.py`, `quality_check.py`, `review_bundle.py`, `asset_manifest_summaries.py` | **contract owner** словаря | `selection_decision` внутри `assets_manifest.json`, `DECISION_SCHEMA_VERSION = 1` | `test_semantic_slot_decisions.py`, `test_autonomous_completion_core.py`, `test_slot_aware_retrieval.py` | второго словаря verdict нет |
| межсценовая связность | `src/assets/semantic_selection/continuity_checker.py` | `asset_manifest_builder.py:262` | **advisory report**: ни отбора, ни `missing_scenes` (VA-NEW-01); среду читает через canonical `evidence.build_evidence`, а не через query/provenance | блок `continuity` манифеста | `test_continuity_evidence_lineage.py`, `test_semantic_asset_selection.py:95` | нет |
| `vision_validator` | `src/assets/semantic_selection/vision_validator.py` (13 строк) | **ноль** — экспортируется из `__init__`, но не вызывается ни production-кодом, ни tests | никакой | нет | **нет owning test** | заглушка; фактическое потребление `vision_tags` живёт в `evidence.py:195` и `candidate_ranker.py:380` |
| Vision evidence по кандидату | `src/assets/semantic_visual_service.py` | `asset_manifest_builder._write_reviews:959`, `pipeline.py` (legacy CLI) | **evidence producer**, окончательного выбора не делает | пишет `assets/review/visual_review_manifest.json`: `semantic_analysis`, `semantic_score`, `semantic_rank`, `semantic_review_required`, блок `semantic_visual` | `test_semantic_visual_integration.py` | второго Vision stack нет |
| протокол и реализации backend | `semantic_visual_backend.py` + `semantic_visual_mock/openai/external.py` | только `semantic_visual_service.create_semantic_visual_backend` | нет | нет | `test_semantic_visual_foundation.py`, `test_semantic_visual_openai_backend.py` | нет |
| кэш Vision-результатов | `src/assets/semantic_visual_cache.py` | `semantic_visual_service` | нет | content-addressed кэш под корнем проекта | `test_semantic_visual_foundation.py` | нет |
| калибровка Vision-вердикта | `src/assets/semantic_decision_policy.py` | **ноль production-callers** | policy, сегодня ни к чему не подключена | нет | `test_semantic_decision_policy.py` | не дубль: это отдельный, ещё не подключённый слой поверх сырого результата |
| offline-оценка Vision | `semantic_visual_evaluation_runtime.py` + `_tooling.py`, фасад `semantic_visual_evaluation.py` | `pipeline.py:15` → `src/legacy_pipeline/maintenance.py:140`; канонический CLI этих команд не имеет | нет | dataset/results под `docs/implementation/openai_live_evaluation` (**C31**) | `test_semantic_visual_evaluation.py`, `test_semantic_visual_evaluation_internals_contract.py` | фасад — уже записанная строка **C09** |
| что значит «готово» и что блокирует материал | `src/assets/completion/modes.py` | `asset_manifest_builder`, `asset_scene_completion`, `news/final_renderer`, `news/quality_check`, `news/models`, `news/pipeline`, `news/script_generator` | **completion policy owner** (`blocking_reasons`, `evaluate_usability`) | `COMPLETION_SCHEMA_VERSION = 1`, блок `completion` манифеста | `test_autonomous_completion_core.py`, `test_news_to_short_quality_check.py`, `test_rights_status_vocabulary.py` | второй ladder/словарь причин не создаётся |
| лестница fallback и детерминированный порядок | `src/assets/completion/ladder.py` | `asset_scene_completion.complete_scene_assembly` | **decision owner ступени**, фильтрует каждую ступень через `modes.blocking_reasons` | `ReuseLedger` внутри прогона | `test_autonomous_completion_core.py` | нет |
| сцена как несколько слотов | `src/assets/completion/assembly.py` | `asset_manifest_builder`, `final_renderer`, `attribution_export`, `projects/rights`, `asset_manifest_summaries` | нет | `visual_assembly` внутри `scenes[]`; `assembly_from_selected_asset` читает досхемные записи без миграции | `test_autonomous_completion_core.py`, `test_slot_aware_retrieval.py` | нет |
| ручная замена слота | `src/assets/completion/replacement.py` | `src/ai_youtube/cli/commands/assets.py:12` | пользовательское решение | **перезаписывает** `assets_manifest.json`, `missing_assets.json`, историю замен, `quality`/`render` manifests и `job.json` | `test_manual_asset_replacement.py` | нет |
| отчёт о слабых фрагментах | `src/assets/completion/report.py` | `news/draft_completion.py:33` | нет, только отчёт | `replacement_report.json/html`, `replacement_queue.json`, `timeline_replacement_map.csv` | `test_autonomous_completion_pipeline.py` | нет |
| оркестрация стадии `asset_search` | `src/news/asset_manifest_builder.py` | `news/asset_manager.build_news_asset_manifest` ← `news/pipeline.py:66` | **orchestration owner**: собирает чужие решения, своего критерия пригодности не имеет | возвращает dict манифеста; `ASSET_SCHEMA_VERSION` | `test_news_to_short_assets.py`, `test_slot_aware_retrieval.py`, `test_visual_retrieval_wiring.py`, `test_rights_review_preservation.py`, `test_artifact_schemas.py` | `src/news/asset_manager.py` — compatibility facade поверх него (**C09-семейство**, closure — свой gate) |
| заполнение сцены в `draft_complete` | `src/news/asset_scene_completion.py` | `asset_manifest_builder.py:735` (и через facade) | workflow policy поверх shared ladder | скачанные файлы проекта, attempts | `test_slot_aware_retrieval.py` | нет |
| состояние проекта и валидность стадии | `src/news/project_store.py` (`NewsProjectStore`) | `news/pipeline.py`, `draft_completion`, `replacement`, CLI | **persistence owner**: атомарная запись, project lock, `is_stage_completed`/`validate_stage_output` | `job.json`, форма проверки `asset_search` — `scenes` + `missing_scenes`, tolerant к досхемным манифестам | `test_news_stage_idempotency.py`, `test_news_to_short_pipeline.py`, `test_project_repository.py` | формой манифеста не владеет |
| декларация формы манифеста | `schemas/assets.schema.json` | — | нет | `additionalProperties: true`; `semantic_visual` и `visual_review` объявлены объектами без внутренней формы | `test_artifact_schemas.py` | второй schema owner отсутствует |

### Кто принимает решение о пригодности кандидата

**FACT.** Решение принимается **одним** владельцем и только на метаданных
провайдера: `rank_candidates` выставляет `rejected`/`reject_reason` и
`selection_decision`, а `select_best_candidate` возвращает первого неотклонённого
кандидата. Оркестратор `asset_manifest_builder` добавляет к этому только
предпочтение видео (`select_best_with_video`) и приоритет пользовательского
ассета; собственного критерия пригодности у него нет. Второй момент, способный
изменить уже выбранного кандидата, — `select_candidate_after_review` в
`_prepare_visual_review:613`, и он выполняется **только** при
`technical_rerank_enabled`, по умолчанию `false`, и работает на технических
признаках, а не на смысле.

**Обновлено 2026-08-13 (после PLAN-9C).** Абзац выше описывает состояние на
`b0e99a7`; его второе утверждение больше не верно. `select_candidate_after_review`
production-путём **не вызывается вовсе** — `asset_manifest_builder.py:648` жёстко
ставит `after_id = before_id` (строка **C68**). Уже выбранного кандидата сегодня
может изменить только Vision-переотбор внутри `_prepare_visual_review`, и только
когда Vision включён обоими гейтами.

Три владельца различаются и не сливаются:
**evidence producers** — `scene_analyzer`, `evidence`, `visual_preview`,
`semantic_visual_service`; **decision owner** — `candidate_ranker`
(+ `completion/ladder` для ступени fallback и `completion/modes` для допуска);
**orchestration owner** — `asset_manifest_builder`; **persistence owner** —
`news/project_store` вместе с `news/pipeline`.

### Где заканчивается shared service и начинается workflow policy

**FACT.** Граница проходит по `src/assets/*` против `src/news/*`.
`semantic_selection`, `semantic_visual*` и `completion` не знают ни о стадиях, ни
о `job.json`, ни о провайдерском порядке: они получают сцену и кандидатов и
возвращают значения. Workflow-политика — какой режим завершённости, какой порядок
провайдеров, сколько попыток скачивания, когда включается `draft_complete`,
что попадает в `missing_scenes` — принадлежит `src/news`. Единственные
пересечения границы в обратную сторону — отложенный импорт
`completion/replacement.py:250` (`src.news.asset_manager.refresh_manifest_summaries`) и
чтение `assets_manifest.json` из `src/assets/completion/replacement.py` и
`src/assets/visual_preview.py`. Это **INFERENCE**-уровня дефект слоистости, а не
второй owner; действие по нему здесь не назначается.

### Роль `vision_validator` и `semantic_visual_service`

**FACT.** `vision_validator.validate_candidate_vision` — заглушка: возвращает
`vision_validation_enabled: False` и переданные теги, не имеет ни одного caller и
ни одного owning test. Флаг `vision_validation_enabled` в `selection_config`
(`asset_manifest_builder.py:260`, `production_plan/youtube_shorts.py:211`) тоже
никем не читается.

**FACT.** `semantic_visual_service` подключён, но на отбор не влияет:
`analyse_semantic_visual_for_project` вызывается из `_write_reviews:959`, то есть
**после** цикла по всем сценам, после отбора, скачивания и fallback, и пишет
результат только в review-манифест. `_selection_fingerprint:446` — защитная
самопроверка: расхождение фиксируется как `selection_warning`, а не как право
изменить выбор. Отдельно подтверждён уже записанный дефект отчётности:
`_semantic_visual_summary:1050` пишет `semantic_rerank_enabled: False` жёстко,
хотя реальное значение приходит из `config/semantic_visual.json` через
`_selection_config:300`; читателей этого поля манифеста в коде нет.

**Обновлено 2026-08-13 (после PLAN-9C).** Утверждение «подключён, но на отбор не
влияет» больше не верно: `_apply_semantic_visual_evidence`
(`asset_manifest_builder.py:692`, вызов из `:635`) применяет Vision-evidence
**внутри цикла сцены — до скачивания и до финального выбора**, а не только в
review-манифест; `_write_reviews` переехал на `:1126`. Факт про заглушку
`vision_validator` и мёртвый ключ `vision_validation_enabled` не изменился, их
судьба записана строкой **C67**.

### Persisted contracts

- `projects/<id>/assets/assets_manifest.json` — `ASSET_SCHEMA_VERSION`, объявлен
  `schemas/assets.schema.json`. **Три писателя:** `news/pipeline.py:437`
  (каноническая стадия, через атомарный `NewsProjectStore.write_json`),
  `news/draft_completion.py:256` (merged-манифест после адаптации сценария),
  `assets/completion/replacement.py:294` (ручная замена слота).
- `projects/<id>/assets/review/visual_review_manifest.json` — владелец формы
  `src/assets/review_bundle.py`; Vision-evidence дописывает
  `semantic_visual_service`.
- `projects/<id>/assets/missing_assets.json`, `job.json` и stage-state —
  `news/project_store.py` и `news/pipeline.py`.
- `selection_decision` и `visual_assembly` — additive-поля внутри `scenes[]`;
  tolerant reader (`assembly_from_selected_asset`) читает досхемные записи без
  миграции.

### Duplicate / overlap — вердикт

| Предмет | Класс | Вердикт |
|---|---|---|
| `news/asset_manager._select_best_candidate` против `asset_manifest_builder.select_best_with_video` | **FACT** | одна и та же реализация в двух местах; production-путь использует вторую, первая — compatibility patch-point, закреплённый тестом. Живого второго owner нет |
| `news/asset_manager` целиком | **FACT** | compatibility facade: `build_news_asset_manifest` делегирует в builder; собственного поведения не добавляет |
| `semantic_score` в `candidate_ranker` против `semantic_score` в `semantic_visual_models` | **FACT** | совпадение имени при разном смысле (метаданные против Vision). Не дубль реализации; риск ошибочного чтения при wiring PLAN-9C |
| `semantic_decision_policy` против `semantic_visual_service` | **FACT** | не дубль: policy калибрует сырой результат и сегодня не подключена ни к одному production-пути |
| `vision_validator` против `evidence.build_evidence` | **FACT** | фактическое потребление `vision_tags` живёт в `evidence`/`candidate_ranker`; `vision_validator` — неиспользуемая заглушка |

### PLAN-9C relevance — где Vision evidence должно войти

**INFERENCE**, ограниченный уже существующим кодом; PLAN-1C′ здесь ничего не
включает и не проектирует. Два уже существующих seam:

1. **Bounded shortlist перед скачиванием.** `_prepare_visual_review:581` уже
   строит `state.candidates[:top_k]`, уже получает evidence
   (`prepare_candidate_preview_analyses`) и уже умеет переизбирать кандидата
   через `select_candidate_after_review` **до** `_download_and_complete`. Это
   единственная точка внутри цикла сцены, где evidence уже способно изменить
   выбор.
2. **Приём evidence существующим decision owner.** `evidence.py:195` уже читает
   `candidate["vision_tags"]`, добавляет их в token set и в `metadata_status`, а
   `candidate_ranker.py:380` уже отклоняет кандидата по `vision_mismatch`.
   Контракт закреплён тестом
   `test_semantic_asset_selection.py::test_vision_mismatch_rejection_uses_existing_tags_without_api`
   и платных вызовов не делает.

Из этого следует только одно: подключение Vision в PLAN-9C — это перенос уже
существующего producer'а на уже существующий seam, а не новый selector, новый
semantic stack, новый manifest и не второй словарь «требуется проверка
человеком».

**Обновлено 2026-08-13.** Так и вышло, но seam 1 реализован **не** через
`select_candidate_after_review` (он мёртв, **C68**), а через
`_apply_semantic_visual_evidence` в той же точке цикла — до
`_download_and_complete`.

### C31 — повторная проверка, без действия

**FACT, перепроверено 2026-08-07 от `b0e99a7`.** Production-зависимость на
`docs/implementation/openai_live_evaluation` существует и не устранена:
`src/assets/semantic_visual_evaluation_tooling.py:26` (дефолтный dataset),
`:38` (дефолтный results dir), `:695` (переписывание относительных путей), плюс
три вызова в `tests/test_semantic_decision_policy.py` (строки 11–12, 29–30,
46–47) и `tests/test_semantic_visual_evaluation.py:455`. Каталог содержит
dataset, checkpoint, sanitized payloads, contact sheet и `results/`.

Строка **C31** остаётся в разделе «Ревизия 2 findings» без изменения класса,
action и exit condition. Physical target и перемещение остаются **PLAN-13** по
OD-8/OD-9. В этом слайсе ничего не переносилось, imports не менялись, target
owner не выбирался, пофайловая классификация `docs/implementation` (C27,
**PLAN-12B**) не выполнялась.

### Что этот gate не закрывает

C01–C16, C09 и C27 остаются открытыми и закрываются своими gates. Наблюдение о
слоистости (`src/assets` читает и импортирует `src/news`) записано как evidence и
права на исправление не даёт. Отсутствие owning test у `vision_validator` и
неподключённость `semantic_decision_policy` записаны как факты; ни одна строка
кода этим слайсом не изменялась.

## Delete evidence

Удаление возможно только отдельным bounded commit после повторной проверки.

| ID | Callers/imports | Рабочая замена | Compatibility period | Targeted verification | Persisted/media risk |
|---|---|---|---|---|---|
| D01 | повторный tracked/repo-wide audit: production callers и package exports отсутствуют; stages 7–8 прошли без нового caller | `src.providers.registry` создаёт `PexelsStockProvider`/`PixabayStockProvider`; Unsplash не active | выполнен отдельный stage 9 checkpoint после полного stage 8 compatibility period | 41 test: `test_news_asset_manager_contract`, `test_asset_foundation_providers`, `test_news_to_short_provider_integration`, `test_news_to_short_assets`; import/compile smoke | schemas, provider ids, provenance, runtime projects и media не изменены |
| D02 | повторный AST/tracked audit: production imports/calls, `src.news` export, CLI/console script и current command отсутствуют | `src.news.asset_manager.build_news_asset_manifest` через normal `asset_search` stage | выполнен отдельный stage 9 checkpoint после stage 7–8 compatibility period | 46 test: `test_news_asset_manager_contract`, `test_news_to_short_assets`, `test_news_to_short_pipeline`, `test_stage1_characterization`; import/compile smoke | download не запускался; существующие `assets_manifest.json`, missing-assets summaries и media не изменены |
| D03 | runtime/import/current callers нет; repo references находятся только в historical plans/audits и current cleanup handoff | `pyproject.toml` package discovery использует `ai_youtube*`, `src*`, `anime_factory*`, `apps*` | runtime compatibility period не требуется; выполнен отдельный docs/package checkpoint | pre-delete characterization; 8 onboarding/reproducibility tests; docs QA и package-discovery smoke | production/runtime/persisted/media risk отсутствует |
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
- D01 legacy names были сохранены для compatibility period stages 7–8 и
  удалены отдельным zero-caller slice этапа 9; D02 public wrapper затем удалён
  собственным imports/entrypoint checkpoint.
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

### Завершённый gate: 8E Documentary

- Catalog/application audit подтвердил отсутствие `documentary` application и
  template; `longform` остаётся planned/disabled без template.
- `psychology`, `quotes`, `survival` и `size_comparison` подтверждены как
  legacy `pipeline.py --channel/--video` profiles без поддерживаемого
  `content_creator` template.
- Solar fixed plan остаётся bespoke root-only workflow:
  `project_config.json`/`scenes.json` не читаются как `job.json` или
  `project.json`, а render entrypoint имеет прямые TTS/HTTP dependencies без
  application-level approval gate.
- Characterization `tests/test_documentary_migration_gate.py` фиксирует catalog,
  channel, project-contract, root-owner и paid/provider stop-gates.
- Migration, capability registration, production/schema/runtime changes,
  network/provider/TTS/render и user-media operations не выполнялись.
- Decision: ADR 0013. Этап 8 закрыт с четырьмя перенесёнными slices; documentary
  требует отдельного будущего product/application stage.

### Завершённый deletion slice: 9 D01 news-only provider classes

- Pre-change characterization подтвердил отсутствие любых production callers
  вне двух временных compatibility modules.
- Повторный tracked repo-wide audit нашёл только definitions, re-export,
  characterization и исторические/current документы; `pyproject.toml`
  публикует только canonical CLI, stages 7–8 прошли без нового caller.
- Из `src.news.asset_provider_adapters` удалены
  `PexelsAssetProvider`, `PixabayAssetProvider`, `UnsplashAssetProvider` и
  ненужные raw provider-module imports; их `asset_manager` re-exports также
  удалены.
- News `AssetProvider` protocol, `create_default_asset_providers` patch-point,
  canonical registry и `PexelsStockProvider`/`PixabayStockProvider` сохранены.
- Targeted verification: 41 test OK для asset-manager contract, provider
  foundation, provider integration и news assets; import/compile smoke OK.
- Решение публичного compatibility contract: ADR 0014. Schemas, manifests,
  provider ids/provenance, runtime projects и user media не менялись; сеть,
  provider search/download, TTS, Vision и render не запускались.

### Завершённый deletion slice: 9 D02 standalone stock downloader

- Pre-change AST characterization подтвердил отсутствие production imports и
  calls за пределами самого wrapper.
- Повторный tracked/repo audit подтвердил отсутствие `src.news` package export,
  CLI/console-script registration и current command; единственным executable
  caller был временный characterization test.
- `src/news/stock_video_downloader.py` удалён; два production docstring больше
  не называют его сохранённым visual-plan consumer.
- Existing `src.news.asset_manager.build_news_asset_manifest` и normal
  `asset_search` stage остаются canonical asset path; новый wrapper/CLI не
  создавался.
- Targeted verification: 46 tests OK для asset-manager contract, news assets,
  news pipeline и Stage 1 compatibility; import/compile smoke OK.
- Решение public compatibility boundary: ADR 0015. Schemas, manifests,
  downloaded media, runtime projects и user data не менялись; сеть/provider
  search/download, TTS, Vision и render не запускались.

### Завершённый deletion slice: 9 D03 packages placeholder

- Read-only inventory подтвердил, что `packages/` содержал только один tracked
  planning `README.md`; hidden/untracked файлов и runtime/package callers не
  было.
- Pre-delete characterization зафиксировал точный `pyproject.toml` discovery
  set: `ai_youtube*`, `src*`, `anime_factory*`, `apps*`; `packages*` в него не
  входил.
- `packages/README.md` и оставшаяся пустая physical directory удалены.
  Исторические plans/audits сохранены как snapshots и не переписывались.
- Targeted verification: 8 onboarding/reproducibility tests, package-discovery
  smoke и docs QA OK. Устаревшие Stage 2 date/length assertions актуализированы:
  `START_HERE` остаётся не длиннее 100 строк, reference docs имеют отдельные
  ограниченные caps.
- Production code, package configuration, schemas, runtime projects и user
  data не менялись; сеть/provider/TTS/Vision/render не запускались.

### Последующая очередь

1. **9A:** D01–D03 завершены отдельными проверенными commits.
2. **9B-P01:** два target engines и место documentary подтверждены ADR 0016.
3. **9B-C01:** выполнить read-only compatibility/ownership inventory и
   заполнить C01–C16 фактическими callers/decisions. **Ревизия 2 разделила этот
   монолитный checkpoint на capability gates `PLAN-1A` / `PLAN-1B` / `PLAN-1C′`
   (+ routing `PLAN-1D`); единого шага «9B-C01» больше нет.**
4. **9C:** переводить callers на canonical imports по одному family.
5. **9D:** передавать ownership реализации по одному workflow/subsystem.
6. **9E:** удалять old wrappers/package roots после zero-caller gate.
7. **10:** только после этапа 9 начать раздельные docs/generated/cache/runtime/
   root-minimization slices; никаких user-data deletions.
8. **C17–C29:** findings Repository Foundation audit распределены по
   существующим владельцам активного execution plan. Отдельный cleanup plan для
   них не создаётся.
9. **Ревизия 2 (2026-07-31)** перенаправила часть gates на новый параллельный
   этап `PLAN-L` и на capability-scoped gates. Актуальные gates смотреть в
   таблицах выше, а не в этом списке.
10. **Ревизия 2.1 (2026-07-31)** добавила findings C34–C50 и перевела
    governance на risk-based модель: первым product-этапом становится семейство
    `PLAN-9B` (`9B-0 → 9B-1 → 9B-5a → 9B-4 → 9B-2`; `9B-3` и `9B-5b` —
    отдельные destructive paths). **Уточнено 2026-08-01:** `PLAN-9A` требует
    только `9B-2` + `1C′` + `6E` и `9B-3`/`9B-5b` не ждёт. `PLAN-5` и
    `PLAN-6A` — параллельные;
    `PLAN-6D` — gate первого multi-owner слайса; `PLAN-6E` — gate первого
    destructive слайса и обязателен для `PLAN-9A` и `PLAN-9C`. Порядок и
    обоснования — в `PROJECT_EXECUTION_PLAN.md`.

## Retired

Обратимый ретайр по механизму `PROJECT_EXECUTION_PLAN.md` →
«Reversible retirement mechanism»: annotated tag на последний commit, где код
существовал, + `git bundle` во внешний workspace, + строка здесь. Постоянный
каталог `trash/` не создаётся.

**Внешний workspace для bundle (owner decision, PLAN-9B-3, 2026-08-07):**
`G:\Projects\AI-YouTube_retirement_bundles\`, вне worktree и вне репозитория;
имя файла совпадает с именем тега без префикса `retired/`. До PLAN-9B-3 механизм
ни разу не исполнялся (`git tag -l` был пуст) и путь нигде не был зафиксирован.

| ID | Что ретайрено | Tag | Commit | Причина | Замена | Salvaged | Дата снятия с учёта |
|---|---|---|---|---|---|---|---|
| R01 | `legacy_broad_query` (`src/content/visual_planning/legacy_format.py`) · `make_stock_query` (`src/news/visual_plan.py`) · `_apply_video_first_topic_briefs` (`src/news/script_generator.py`) · `src/assets/semantic_selection/query_generator.py` (`generate_queries` / `ordered_queries`) | `retired/query-paths-2026-08-07` (bundle `query-paths-2026-08-07.bundle`) | `1bbfcad` — последний commit, где код существовал | superseded query-generation paths: четыре фиксированные английские строки на любое видео, topic-специфичный auto-brief одного животного и генератор, собиравший запрос из слов сцены без проверки, на каком он языке | `src/content/visual_planning/expansion.py` (PLAN-9B-2 ladder) + `legacy_format.semantic_scene_queries` как shape adapter для `SemanticScene` | PLAN-9B-2 (C46, C48 — knowledge перенесён в `expansion.py`); собственного уникального knowledge сверх этого у ретайренного кода нет | 2026-08-07 |
| R02 | `outputs/` целиком: 9 tracked generated артефактов legacy-стека (C19: 8 JSON-планов · C29: `asset_library_report.md` · вместе A02) + untracked legacy-рендеры каналов psychology/quotes/size_comparison/survival, `final_video.mp4`, `render_temp/`, smoke-WAV (~263 файла, ~1.8 GB). Личные аудио владельца `outputs/audio_edits/` (19 файлов, 2.2 GB) **не ретайрены** — перемещены владельцем в `G:\Projects\audio_edits\` до удаления | `retired/legacy-content-outputs-2026-08-13` (bundle `legacy-content-outputs-2026-08-13.bundle`) | `92520ee` — последний commit, где файлы существовали | generated output одного прогона на видео; canonical path в `outputs/` не пишет (`exporter.export_localization` → `projects/<id>/localizations/*/output`), вход и выход перепутаны только у legacy | per-project artifacts канонического store `projects/` | уникального knowledge нет: планы/self-eval/render-stage перенесены в canonical в лучшем виде (см. R02-KN в Knowledge salvage log — единственная не перенесённая возможность `title_variants`/`youtube_metadata` записана отдельно); producer-код не тронут и при запуске пересоздаёт каталог | 2026-08-13 (owner decision, раньше PLAN-L4) |
| R03 | `content/` без fixture-пары: `psychology/overloaded_mind_001/**` (8 файлов: brief, script, visual_plan, research, music_direction, diagram-плейсхолдеры) · `size_comparison/sea_monsters_001/**` (2) · `story_card_jobs.tsv` (очередь legacy story-card wizard) | `retired/legacy-content-outputs-2026-08-13` (bundle `legacy-content-outputs-2026-08-13.bundle`; anchor `92520ee`, файлы byte-идентичны состоянию anchor) | `30d5db8` — последний commit, где файлы существовали | рукописные брифы-задания legacy-стека 2 (N04); ни один тест и ни один runtime-caller их не читает (проверено: оба legacy-теста загружают только survival/quotes пару) | canonical задание живёт в `job.json` проекта, собирается из CLI-флагов | publish-metadata возможность (`title_variants`) уже записана строкой **R02-KN**; visual rules/prompts этих брифов не содержат уникального знания сверх уже записанного в salvage log C46–C48/OD-1 | 2026-08-13 (owner decision, N04 частично — fixture-пара ретайрится R04) |
| R04 | каталог `content/` целиком (последняя пара: `survival/juliane_koepcke_001.json`, `quotes/thoughts_too_late_001.json`) | `retired/legacy-content-outputs-2026-08-13` (bundle `legacy-content-outputs-2026-08-13.bundle`; anchor `92520ee`) | `cb5782b` — последний commit, где пара лежала в `content/`; сами файлы **не удалены**, а перенесены `git mv` в `tests/data/legacy_content/` (история сохранена) | root-каталог legacy-заданий больше не существует; canonical задание живёт в `job.json`, runtime-читателей у `content/` не осталось | fixtures читаются теми же двумя LEGACY ANCHOR тестами через `load_channel_video_config(..., application_paths=...)` с `content_root=tests/data/legacy_content` — src не менялся, использован существующий параметр инъекции | KEEP MINIMAL REGRESSION знание живёт в самих сохранённых тестах (16 проверок зелёные без `content/`); R02-KN записан отдельно | 2026-08-13 (owner decision, завершение N04) |

Строка добавляется **в том же commit**, что и удаление. Ретайр без tag, без
bundle и без строки здесь считается незавершённым.

## Knowledge salvage log

Заполняется PLAN-L0 до destructive retirement **knowledge-bearing family**:
source, workflow, config, prompts, templates, tests и docs/evidence с уникальным
инженерным или product knowledge. Disposable runtime/media/cache сюда не
попадают — их владелец `PLAN-14D` → `PLAN-14E` и `Preserved runtime corpus`.
Правило: **отсутствие caller не является критерием отсутствия ценности.**

Классы находок: `MIGRATE CAPABILITY` (пометить как отдельный будущий product
slice, внутри PLAN-L **не выполняется**) · `MIGRATE KNOWLEDGE` · `KEEP MINIMAL
REGRESSION` · `ARCHIVE ONLY` · `DELETE`.

**Заполнено PLAN-L0, 2026-08-02, clean HEAD `2b46afb`.** Read-only bounded
audit: чтение source, config, prompts, content JSON и тестов, `git ls-files` /
`git check-ignore` для фактов трекинга, import/caller graph. Сеть, providers,
model API, TTS, Vision, render и удаление файлов не выполнялись; production-код,
tests, configs и runtime не менялись. Ни одна строка ниже не даёт права на
действие и ничего ещё не ретайрено. Класс `MIGRATE CAPABILITY` **не** планирует
работу сам по себе: он фиксирует, что возможность существует и требует
отдельного будущего owner-issued product slice.

| Family | Находка | Класс | Куда перенесено | Что стоит восстановить позже |
|---|---|---|---|---|
| `outputs/youtube_metadata.json` + `title_variants` в legacy briefs (`content/*/…json`) — запись **R02-KN**, добавлена 2026-08-13 при раннем ретайре R02 | **FACT.** Legacy-стек генерировал publish-метаданные: `title_variants` (4–5 вариантов названия в brief и в `youtube_metadata.json`), description и структуру для загрузки. Canonical path аналога **не имеет**: `exporter.export_localization` пишет только `description.txt` + sources/attribution; ни выбора названия, ни вариантов, ни tags | `MIGRATE CAPABILITY` | никуда не перенесено — возможность отсутствует в canonical | Генерация publish-метаданных (варианты названия · description · tags) как будущий bounded product slice поверх существующего `export`; естественная точка — рядом с truthful-catalog слайсом PLAN-11 (implementation там же объявлен отдельным будущим slice). Нового PLAN-ID эта строка не создаёт |
| `src/video_asset_engine.py::build_query_variants` (:225-256) | **C46, FACT.** Лестница из готовых английских ключей: для каждого термина `visual_keywords` (или `image_query`, иначе литерал `cinematic documentary`) — сам термин, затем термин + первые два суффикса из `["cinematic", "documentary footage", "slow motion", "dark atmosphere"]`, затем усечение до первых двух слов при длине > 2 слов; после всех терминов — `"<mood> documentary"`; затем channel-расширение (для `survival` — 10 topic-литералов); финал — case-insensitive дедупликация с нормализацией пробелов и обрезка до 12 вариантов. Потребитель берёт `queries[:4]` | `MIGRATE KNOWLEDGE` | этот registry → **PLAN-9B-2** | Порядок «точное → квалифицированное суффиксом → усечённое → mood → контекст», ограничение общего числа вариантов и отдельный меньший лимит на фактически исполняемые запросы, дедупликацию по нормализованной форме. **Не переносить:** требование готовых английских ключей на входе, channel-hardcode `survival` и любые topic-литералы — их запрещает fail-closed граница PLAN-9B-PRODUCER |
| `src/video_asset_engine.py` (:128-135, :150, :163) + `config/video_style.json:123` | **C47, FACT.** `min_diversity = asset_library.min_local_diversity_per_scene` (код default 4, `video_style.json` 7, `content/psychology/**/scene_notes.json` 4); `local_diversity_gap = max(0, min_diversity − число уникальных local_path среди локальных матчей)`; `reserved_download_slots = min(gap, max_new_downloads_per_scene, target_count − 1)`; `local_take = target_count − reserved`. Догрузка запускается, если не хватает клипов **или** gap > 0; при gap > 0 кандидат-дубликат уже существующего локального ассета пропускается | `MIGRATE KNOWLEDGE` | этот registry → **PLAN-10D** | Правило: сцена не заполняется копиями одного локального клипа — часть слотов резервируется под новый материал, резерв ограничен сверху бюджетом загрузок и всегда оставляет минимум один локальный слот (`target_count − 1`); при нехватке нового материала сцена деградирует к локальным и затем к fallback, а не остаётся пустой. **Привязано к legacy:** имена ключей в `asset_library`, счёт уникальности по `local_path` |
| `content/**/*.json` → `scenes[].visual_keywords` | **C48, FACT.** Provider-ready английские ключи существуют **входным отдельным полем**, а не результатом перевода в query-слое: `content/survival/juliane_koepcke_001.json` и `content/psychology/overloaded_mind_001/scene_notes.json` дают русские `screen_text`/`subtitle_text` и одновременно английские `visual_keywords` (`["rain apartment window", "blue glow", "tired eyes", …]`). Код только читает поле (`video_asset_engine:226`, `scene_planner`, `quote_generator`) | `MIGRATE KNOWLEDGE` | этот registry → **PLAN-9B-PRODUCER**, затем **PLAN-9B-2** | Разделение visual intent и нарратива в отдельные поля одного scene-контракта; провайдер получает visual-поле, а не текст сцены; explicit author-ключи выигрывают у автоматических. **Реализацию восстанавливать не нужно:** современный носитель — существующий `VisualBrief`/`SceneVisualPlan`, второй planner не создаётся |
| `src/self_eval.py::evaluate_render` | **FACT.** Единственный анализ **готового файла**, а не метаданных: файл существует и непустой → длительность из `VideoFileClip` против суммы `scene.duration` с допуском 20 с (prod) / 0.5 с (dev) → размер кадра против `config.resolution` → число сцен (3–5 для prod-preview, 22–32 для production) → риск переполнения текста при `len(screen_text) > 135` → fallback/placeholder-сцены → музыка подключена → metadata содержит `chosen_title` | `MIGRATE KNOWLEDGE` | этот registry → расширение существующего quality owner; **MOTION-CS1** (technical QA сегмента) | Проверять сам rendered-артефакт, а не план: длительность против суммы плановых длительностей с явным допуском, фактическое разрешение против запрошенного, читаемость по длине экранного текста, различие «ошибка» и «предупреждение». **Новый Quality Engine не создаётся.** Пороги 135 / 20 с / 22–32 — legacy-калибровка одного формата, не контракт |
| `src/self_eval.py::evaluate_documentary_quality_rules` + `_evaluate_documentary_assets` | **FACT.** Отдельный слой montage-правил: сцена без клипов, сцена только из placeholder, сцена с одним повторяющимся визуальным источником, доля уникальных источников против `max(число сцен, число клипов // 5)`, средняя длина плана ≥ 4 с, `fps ≥ 24`, включённый voice, включённый music ducking, наличие статичных image-клипов | `MIGRATE KNOWLEDGE` | этот registry → **MOTION-CS1**; смежно **PLAN-10D** (повторяющиеся визуалы) | Детекторы «placeholder-only сцена», «одна и та же картинка на всю сцену» и «низкое разнообразие источников» — прямые метрики проблемы повторяющихся визуалов; требование ducking при озвучке; пол средней длины плана. **Не переносить:** channel-специфичные списки терминов (`survival`/`psychology`) и их пороги 0.55 / 0.45 |
| `src/thumbnail_generator.py` + `src/thumbnail_engine.py` | **FACT.** Готовая генерация обложки 1280×720 из уже отобранных ассетов: кадр из видео-клипа или изображение сцены → `fit_cover` → снижение насыщенности/яркости, рост контраста, лёгкое размытие → затемняющие слои (общий, левый ~62 %, нижний ~74 %) → заголовок с обводкой, метка канала, разделительная линия, футер, рамка. У нового продукта возможности нет | `MIGRATE CAPABILITY` | этот registry → отдельный будущий product slice на новом canonical core | User outcome: пользователь получает готовую обложку из материалов ролика без ручного редактора. Ценные правила: фон берётся из фактически выбранных ассетов, а не из отдельного поиска; затемнение под текст обязательное; заголовок переносится максимум на 3 строки. **Код не переносить.** Точный размер, палитра и стиль — предмет будущего slice |
| `src/youtube_metadata.py` | **FACT.** Генерация публикационного пакета: варианты заголовка и выбранный, описание, теги, ключевые слова, `thumbnail_text`/`thumbnail_idea`/`thumbnail_prompt`, главы из накопленных `scene.duration` в `MM:SS`, `pinned_comment`, `shorts_hooks`. `generate_with_ai_later()` намеренно `NotImplementedError`. У нового продукта возможности нет | `MIGRATE CAPABILITY` | этот registry → отдельный будущий product slice на новом canonical core | User outcome: из готового проекта собирается пакет для загрузки. Входы: план сцен, quote-план и task-декларация; выход: несколько вариантов заголовка при одном выбранном, главы, вычисленные из фактических длительностей, а не заявленных |
| `src/youtube_metadata.py::_generate_video_task_metadata` → `upload_ready_fields` | **FACT.** Safeguards публикации: `visibility_default: "private"`, `made_for_kids: false`, обязательные `disclaimer` и `source_notes` (из task или из `source_note` каждого quote-элемента), `category_suggestion`, явный `language` | `MIGRATE KNOWLEDGE` | этот registry → тот же будущий metadata product slice | Готовый к загрузке пакет по умолчанию **не публичный**; disclaimer и источники входят в сам пакет, а не только во внутренние манифесты; `made_for_kids` задаётся явно. Это правила публикации, а не форматирование |
| `src/size_comparison_engine.py` + `content/size_comparison/sea_monsters_001/data.csv` | **C33/OD-10, FACT.** Целостный формат сравнения размеров: CSV `name,size_meters,category,source_note,visual_priority` → сортировка по размеру → камера-план → покадровый рендер сцены океана с силуэтами, подписями и reference-оверлеем → добавление амбиенса → валидация файла → Obsidian-заметка. У нового продукта формата нет | `MIGRATE CAPABILITY` | этот registry → отдельный будущий product slice на новом canonical core | User outcome: последовательное сравнение объектов очень разного масштаба, остающееся читаемым. Входной контракт — табличные данные с категорией и источником на каждый объект. **Capability внутри PLAN-L0/L3 не мигрируется** (OD-10) |
| `src/size_comparison_engine.py::build_camera_plan` / `_group_scale_stages` | **FACT.** Reusable алгоритм: объекты режутся на стадии по порогам ≤20 / 20–140 / 140–400 / >400 м (пустые стадии выбрасываются); внутри стадии крупнейший объект занимает 54 % ширины кадра при <120 м и 86 % при ≥120 м; если при этом мельчайший объект оказался бы тоньше 42 px, масштаб пересчитывается от него; `camera_motion` = `slow_pan_reveal` при крупнейшем ≥100 м, иначе `slow_push_in`; `reference_overlay` включается при ≥100 м | `MIGRATE KNOWLEDGE` | этот registry → тот же будущий product slice | Адаптивные стадии вместо одного линейного масштаба; жёсткий пол видимости мелкого объекта, который **побеждает** желаемый размер крупного; постоянный reference-объект в кадре на больших стадиях; тип движения камеры выводится из масштаба стадии. **Не переносить:** пороги под один набор морских объектов и ручную Pillow-вёрстку |
| `src/size_comparison_engine.py::prepare_silhouette_asset` | **FACT.** Подготовка силуэта без ручного редактора: если альфа непрозрачна, берётся статистика краевых пикселей; при `edge_mean.min() > 228` — удаление белого фона по порогу расстояния 52, при `edge_std < 28` — удаление плоского цветного фона по порогу 55; затем размытие маски 0.45 и заливка единым тоном. Результат сообщает, какой фон был удалён | `MIGRATE KNOWLEDGE` | этот registry → тот же будущий product slice | Эвристику «решай по краям изображения, есть ли удаляемый однородный фон» и то, что результат обязан сообщать применённый режим (`transparent` / `white_removed` / `flat_color_removed` / `opaque`), а не молча менять пиксели |
| `tests/test_size_comparison_engine.py` | **FACT.** Полезные проверяемые случаи: `source_note` мифического объекта сохраняет пометку интерпретации; план даёт ≥3 стадии с **разными** `meters_per_pixel`, хотя бы одним `reference_overlay` и минимальной видимостью ≥42 px в каждой стадии; удаление белого и плоского цветного фона даёт прозрачный угол и непрозрачный центр; фон-подбор предпочитает `underwater abyss` reference-изображениям; self-eval остаётся `ok` при warning'ах ассетов, если рендер провалидировался | `KEEP MINIMAL REGRESSION` | этот registry → тот же будущий product slice | Минимальный fixture: небольшой набор объектов разных порядков + проверка «стадий больше одной, масштабы различаются, мельчайший объект остаётся видимым, пометка вымышленности не теряется». Весь legacy-стек ради этого не сохраняется |
| `content/size_comparison/sea_monsters_001/data.csv` + `channels/size_comparison/channel_config.json` | **FACT.** `category` разделяет `reference` / `real animal` / `prehistoric` / `mythical`; `source_note` каждой мифической строки явно называет её вымышленной интерпретацией; `content_rules` канала требуют помечать мифические измерения как вымышленные; `_label` дописывает `/ estimated interpretation` к категории с `myth`, а `_draw_title_band` выводит дисклеймер в кадре | `MIGRATE KNOWLEDGE` | этот registry → существующие misleading/`must_avoid` gates + будущий product slice | Правило: измерение вымышленного объекта нельзя показывать наравне с измеренным — класс достоверности задаётся в данных, повторяется в подписи кадра и в metadata. Это rights/misleading knowledge, а не оформление |
| `src/layout_renderer.py` | **FACT.** Оверлеи и титры: размеры шрифтов от ширины кадра (`width*0.052` титул, `width*0.04` финал), ширина переноса зависит от ширины (31 против 27 символов на `_draw_thought`, 72/58 на подписи), `break_long_words=False`; три раскладки по `scene_type` (`intro` / `thought` / `final`); огибающая прозрачности `fade_in` 18 % / `fade_out` 14 % с полом 0.25; читаемость — скруглённая подложка с ограниченной альфой, градиент от 58 % высоты и двойная отрисовка текста со смещением 1 px; кинематографические полосы 4.5 % высоты | `MIGRATE KNOWLEDGE` | этот registry → будущий longform/horizontal; смежно **MOTION-CS3** | Пропорциональные кадру типографика и перенос вместо абсолютных пикселей; запрет разрыва длинных слов; читаемость обеспечивается подложкой **или** градиентом, а не увеличением шрифта; отдельные раскладки на роль сцены; плавные вход/выход с ненулевым полом. **Не переносить:** ручную Pillow-вёрстку и зашитые hex-цвета |
| `src/layout_renderer.py::_content_label` + `src/quote_generator.py` + `src/scene_planner.py::_hard_rules` | **FACT.** Трёхуровневая таксономия достоверности текста: `quote` / `idea` / `narration_card`, у каждого элемента собственный `source_note`, у плана — общий `disclaimer`; экранная метка отражает уровень (`БЛИЗКАЯ ЦИТАТА` / `ПЕРЕСКАЗ ИДЕИ` / `МЫСЛЬ ДЛЯ ЭКРАНА`); `_hard_rules` фиксируют это как обязательное правило плана | `MIGRATE KNOWLEDGE` | этот registry → существующие rights / misleading / `must_avoid` gates | Пересказ нельзя показывать как дословную цитату: уровень достоверности хранится в самом элементе, попадает на экран и в metadata одновременно. Прямо релевантно factual-strict политике (OD-18) |
| `src/scene_planner.py::_hard_rules` | **FACT.** Пять зафиксированных правил: рендер не падает при отсутствии необязательных ассетов; кириллица рендерится через явный путь к Windows-шрифту; dev-preview остаётся коротким; production строится по структурным планам, а не по сырому видео как источнику логики; пересказ помечается как `idea`/`narration_card` | `MIGRATE KNOWLEDGE` | этот registry → **MOTION-CS1** (шрифты и деградация рендера) | Правила «недостающий необязательный ассет не валит рендер» и «нелатинский текст требует явно выбранного шрифта с проверяемым fallback» — это те же дефекты, что даёт `ImageFont.load_default()` в C56 |
| `src/music_engine.py::build_music_plan_v2` + `src/music_finder.py` | **FACT.** Подбор музыки по настроению: локальная библиотека (`search_local_assets` по `music`, ключи = queries, `mood`, общая длительность) → Pixabay audio при наличии ключа и `auto_download` → локальный fallback-файл → честный `music_not_found` с warning. Ранжирование кандидата: `min(duration, 360) + downloads/1000`. Громкость `min(music_search.volume, documentary_music_volume)`; `fade_in` 2.0 с, `fade_out` = `min(4.0, max(2.0, длительность*0.04))`; `loop_used` выставляется, если трек короче ролика. Queries приходят из style/task; при их отсутствии — три общих; для `survival` — 6 hardcoded | `MIGRATE KNOWLEDGE` | этот registry → существующий music owner (**C12**) / будущая Music Studio | Порядок «локальное → провайдер → локальный fallback → честный отказ»; потолок громкости, задаваемый форматом, а не запросом; вычисляемые fade и явный признак зацикливания; отказ фиксируется в плане, а не заменяется тишиной молча. **Не переносить:** channel-hardcode queries и scraping-политику. **Сеть в PLAN-L0 не выполнялась** |
| `src/music_tools.py::add_background_music` + `content/psychology/**/music_direction.txt` | **FACT.** Ducking: при наличии озвучки громкость музыки умножается на 0.42; музыка зацикливается до длительности видео и подрезается точно; голосовые дорожки накладываются по `start`/`volume` из voice-манифеста. Текстовая директива формата требует voice-first микс, ducking при озвучке и явно запрещает motivational drums, trailer risers, bright corporate piano и high-energy ритм | `MIGRATE KNOWLEDGE` | этот registry → существующий music/audio owner | Правило voice-first: музыка приглушается детерминированным коэффициентом при наличии голоса, а не «на слух»; недостающая длительность закрывается зацикливанием, а не растяжением; негативная директива стиля хранится вместе с форматом. Коэффициент 0.42 — legacy-калибровка, не контракт |
| `src/voice_engine.py::build_voice_manifest` | **FACT.** Лестница деградации озвучки: кэш по `cache_key` от текста и voice-конфига → ElevenLabs → MOSS (только если `fallback_provider == "moss_tts_nano"` или `moss_tts_enabled`) → локальный stub; каждое понижение уровня добавляет warning с номером сцены и не прерывает сборку. Таймлайн: `cursor += max(scene.duration, длительность_озвучки + post_scene_pause)`. Отсутствие `ELEVENLABS_API_KEY` даёт stub, а не платный вызов | `MIGRATE KNOWLEDGE` | этот registry → существующий audio/TTS owner (**K06**) | Кэш-ключ от текста и параметров голоса (правка одной сцены не переозвучивает остальные); каждое понижение уровня провайдера видимо в манифесте; отсутствие ключа никогда не превращается в платный вызов; длительность сцены не может быть короче фактической озвучки плюс пауза |
| `src/video_renderer.py` | **FACT.** Пошаговый рендер с восстановлением: `render_stage.json` пишется на каждом шаге (`render_silent_started/done`, `validate_silent_*`, `add_music_*`, `failed` с именем стадии); `RenderStageError` несёт стадию и сообщение; `validate_video_file` проверяет существование, ненулевой размер, читаемость, валидный размер кадра и длительность против ожидаемой; `validation_tolerance_for_duration` = `max(2.0, min(8.0, duration*0.008))`; `_can_fast_render_scene` выбирает быстрый ffmpeg-путь, когда все клипы сцены — существующие видеофайлы; при провале музыки silent-видео остаётся результатом | `MIGRATE KNOWLEDGE` | этот registry → **MOTION-CS1** | Именованные стадии в персистентном логе (перезапуск знает, где остановился); допуск длительности, пропорциональный длительности, а не константа; валидация после каждой стадии, а не только в конце; частичный результат сохраняется вместо потери всего рендера. Смежно с C58/C60 |
| `src/video_asset_engine.py` (:404-501, :727-732) | **FACT.** Приёмка кандидата провайдера: `_passes_video_filter` требует ширину 960–2560, высоту ≥540, соотношение 1.45–2.35 и длительность ≥2.5 с; `_score_candidate` = близость к 16:9 (штраф 80 за единицу отклонения) + `min(duration,18)*8` + `min(width,1920)/24`; предпочитаются файлы ≤1920 при наличии; каждый отказ пишется в `rejected` с причиной; `_license_note` даёт разный текст для Pexels, Pixabay и локального ассета и во всех случаях требует проверки лицензии до публикации | `MIGRATE KNOWLEDGE` | этот registry → **PLAN-10B** (provider contract) / **PLAN-10D** | Явные минимумы разрешения и длительности до скачивания; предпочтение 1920 вместо максимального доступного; **отказ с причиной сохраняется** и доступен диагностике; лицензионная пометка присваивается в момент приёмки кандидата, а не при рендере. Числовые пороги — legacy-калибровка |
| `src/video_asset_engine.py::_valid_video_file` + `adaptive_shot_duration` | **FACT.** Скачанный файл проверяется реальным декодированием: ffmpeg `-t 2 -f null -` и проверка кода возврата (плюс отсечка размера <1024 байт). Длительность плана выводится из смысла сцены: 6.0 с для mood со `shock/storm/tension/disaster/danger`, 7.5 с для `rescue/discovery/hope`, 13.0 с для `reflection`/`closing`, иначе 11.0 с; +2.0 с при озвучке ≥12 с; результат зажат в 4–30 с; число планов = `ceil(duration / shot_duration)`, максимум 5 | `MIGRATE KNOWLEDGE` | этот registry → **MOTION-CS1** (technical QA и pacing) | Проверять скачанный медиафайл декодированием, а не только размером; длительность плана выводить из настроения сцены и фактической озвучки, с жёсткими границами; число планов вычислять из длительности сцены, а не задавать константой |
| `content/psychology/overloaded_mind_001/scene_notes.json` → `visual_rules` + `visual_plan.md` | **FACT.** Декларативные правила монтажа рядом с контентом: `shot_duration` = минимум 5 с, среднее 8–15 с, эмоциональные сцены 15–25 с, максимум 25 с; `avoid` = motivational editing, sigma aesthetics, TikTok pacing, 2–3-секундные склейки, огромные чёрные плашки субтитров, случайный сток; `visual_plan.md` дополняет: приоритет источников `manual_assets → assets/library → Pexels → Pixabay → Unsplash → Archive.org → generated fallback` и правило «склейки следуют паузам нарратива, а не социальному биту» | `MIGRATE KNOWLEDGE` | этот registry → **MOTION-CS1** (pacing) и будущий longform | Формат владеет собственным диапазоном длительности плана и явным negative-списком; приоритет источников визуала — упорядоченная лестница с generated fallback **последним**; ритм монтажа привязан к нарративу. Это продуктовые правила, живущие данными, а не кодом |
| `content/psychology/overloaded_mind_001/research_notes.md` | **FACT.** Редакционно-безопасностная директива темы: материал объявлен редакционной рефлексией, а не клиническим диагнозом; явно запрещено утверждать, что любая прокрастинация есть перегрузка; требуется дисклеймер «не медицинский совет» в metadata и в экспортируемой заметке | `MIGRATE KNOWLEDGE` | этот registry → существующие misleading/`must_avoid` gates | Правило: чувствительная тема несёт собственную редакционную границу и обязательный дисклеймер, зафиксированные вместе с контентом и доезжающие до публикационных полей. Это safety knowledge, а не заметка автора |
| `content/psychology/overloaded_mind_001/{scene_notes.json → infographics, diagram_0*_placeholder.txt}` | **FACT.** Инфографика объявлена данными: список `{id, title, asset_path}` указывает на versioned SVG в `manual_assets/**`, а текстовые placeholder-файлы описывают содержание каждой диаграммы словами (timeline 1995→2010→2026, петля «усталость → контент → облегчение → истощение», фрагментация внимания) | `MIGRATE KNOWLEDGE` | этот registry → **MOTION-CS4** | Диаграмма объявляется контентом (id, заголовок, ссылка на актив), а её смысл записан отдельно от реализации; versioned SVG остаётся источником, а не generated-выходом. Согласуется с контрактом `build_generated_asset` |
| `src/channel_loader.py::load_channel_video_config` | **FACT.** Трёхуровневое разрешение конфигурации: базовый config < `channels/<ch>/style.json` < `content/**` video task, с ключевым слиянием для `subtitle_style`, `voice`, `music_search`, `asset_library`, `manual_assets`. Перед слиянием проверяется, что `video_task.channel` и `video_task.video_id` совпадают с запрошенными, иначе `ValueError`. `_content_task_path` толерантно принимает две формы: `content/<ch>/<vid>.json` и `content/<ch>/<vid>/scene_notes.json` | `MIGRATE KNOWLEDGE` | этот registry → существующий `src/config_resolver` (**K03**) | Порядок приоритета «продукт < канал < конкретный ролик» с поключевым, а не поблочным слиянием; отказ при несовпадении заявленной и запрошенной идентичности задания; толерантный reader двух исторических форм без миграции файлов. **Второй resolver не создаётся** |
| `channels/{psychology,quotes,survival,size_comparison}/style.json` | **FACT.** Стиль канала — данные, а не код: `visual_style`, `image_style`, `intro_style`, `text_style`, `music_mood`, разрешённые `transitions`/`animations`, палитра и **`avoid`** — negative-список (meme style, motivational cringe, flashy TikTok transitions, fake drama, huge black subtitle rectangles, scene labels, presentation UI). `subtitle_style` содержит настоящие токены: `font_size`, `wrap_chars`, `spacing`, `padding_x/y`, `radius`, `background_alpha`, `y_ratio` | `MIGRATE KNOWLEDGE` | этот registry → **MOTION-CS3** (один token owner) + будущая channel style policy | Что именно является токеном формата (размер, перенос, отступы, радиус, альфа подложки, вертикальная позиция) и что канал объявляет **запрещённое**, а не только желаемое. Прямо питает решение по владельцу design tokens (**C62**) |
| `channels/*/prompts/`, `channels/*/templates/` | **FACT.** В `channels/psychology`, `channels/quotes` и `channels/survival` обе директории содержат только `.gitkeep`; в `channels/size_comparison` обе директории отсутствуют. Salvage knowledge в этих путях нет — вывод сделан по фактическому дереву и содержимому | `DELETE` | — | Восстанавливать нечего: пустые placeholder-директории и отсутствующие пути |
| `content/story_card_jobs.tsv` | **FACT.** Файл прочитан целиком: заголовок `job_id/slug/topic` и пять строк с историческими темами Story Card; runtime-caller отсутствует. Ни алгоритма, ни правила, ни схемы, переиспользуемой новым продуктом, в нём нет | `DELETE` | — | Восстанавливать нечего. Темы прошлых роликов не являются инженерным или продуктовым знанием |
| `config/video_style.json` → `fallback_behavior` | **FACT.** Декларативная политика деградации: `missing_image` → создать placeholder, `missing_music` → рендерить без звука, `missing_font` → стандартный шрифт Pillow, `openai_disabled` → использовать редакционный план. Рядом — `api_models`, `intro_generation`, `openai_image_generation`, все выключены | `MIGRATE KNOWLEDGE` | этот registry → существующий completion/fallback owner (`src/assets/completion/`) | Реакция на каждый класс отсутствующего ресурса объявляется данными и читается человеком до запуска. **Отдельная оговорка:** `missing_font` → `load_default()` — тот же машинно-зависимый дефект, что C56; при переносе правило должно стать «явный проверяемый fallback-шрифт», а не «молча любой». `moss_tts_path` и `vault_path` с зашитым `G:/` (**C24**) — дефект, не знание |
| `src/config_loader.py` | **FACT.** Лестница профилей одного формата: `dev` (сцена ≤10 с, fps ≤24, короткий preview), `prod` (перенос `prod_*` значений), `prod_preview` (1280×720, шрифт ≤44, ровно 5 сцен), `cinematic_preview` (1280×720, fps 24, crf 17, preset slow, не dev). `_rebase_runtime_outputs` рекурсивно переписывает относительные пути, начинающиеся с `outputs`, под переданный корень | `MIGRATE KNOWLEDGE` | этот registry → **MOTION-CS1** (preview/draft policy) | Идея дешёвого preview-профиля: понижаются разрешение, fps и **число сцен**, а не только качество кодирования; production-значения хранятся отдельными `prod_*` ключами. **Не переносить:** rebase путей — его заменяет существующий `WorkspacePaths` |
| `src/obsidian_exporter.py` + `export_size_comparison_obsidian_note` | **FACT.** Экспорт человекочитаемой заметки проекта во внешний vault с копированием видео и обложки, ссылками на планы и структурой «статус → превью → состав → визуальные заметки → self-eval checks → warnings → следующие шаги»; при отсутствии vault пишет в `outputs/`. Является ли внешний knowledge-base экспорт продуктовой возможностью — **owner decision не принят**, поэтому класс `MIGRATE CAPABILITY` здесь не присваивается | `ARCHIVE ONLY` | — | Активное восстановление не требуется: интеграция с конкретным личным vault — не продуктовый контракт, retirement tag и history достаточны. Переиспользуемая часть — структура отчёта — вынесена отдельной строкой ниже |
| `src/obsidian_exporter.py` (структура заметки) | **FACT.** Отчёт по проекту всегда содержал четыре раздела, полезные вне Obsidian: что фактически получилось, какие проверки прошли, какие предупреждения остались, что делать дальше; плюс fallback-запись в `outputs/`, когда внешняя цель недоступна | `MIGRATE KNOWLEDGE` | этот registry → существующий completion/review reporting | Человекочитаемая сводка проекта — «результат / пройденные проверки / оставшиеся предупреждения / следующие шаги» — и правило «недоступная внешняя цель не отменяет отчёт, он пишется локально» |
| `src/asset_finder.py`, `src/image_tools.py` | **FACT.** Legacy image-путь: поиск портрета по токенам имени в `assets/images`, покадровое скачивание одной картинки на сцену из Pexels/Pixabay, кэш по имени `scene_NN_*`, генерируемый placeholder с градиентом и подписью «временный визуальный ассет». Полностью перекрыт каноническим asset-stage и provider registry; правило «лучше видимый placeholder, чем упавший рендер» уже сохранено строкой `fallback_behavior` | `ARCHIVE ONLY` | — | Активного восстановления не требуется: retirement tag и history достаточны. Единственная переиспользуемая идея — подписанный placeholder, который **видно** как временный, — уже записана выше |
| `src/intro_generator.py` | **FACT.** Прочитан целиком (23 строки): возвращает статический словарь с русским заголовком и подзаголовком одного legacy-канала, длительностью 12 с и полем `generation`, где провайдер называется `openai_image_later`, а `enabled` всегда `False`. Алгоритма, правила или контракта нет | `DELETE` | — | Восстанавливать нечего. Идея «зарезервированное выключенное поле под будущую генерацию» — антипаттерн speculative interface, запрещённый действующим планом |
| `legacy/scene_planner.py`, `legacy/scene_plan_json.py` | **FACT.** Два прототипных промпта разбиения сценария на монтажные сцены. Запрошенная схема ответа: `scene_number`, `estimated_start`/`estimated_end`, `narration_text`, `emotion`, **`broll_keywords` на английском**, `screen_text`, `editing_note`; второй вариант дополнительно требует «только валидный JSON без пояснений» и общий `style` | `MIGRATE KNOWLEDGE` | этот registry → **PLAN-9B-PRODUCER** | Исторический прецедент C48 в форме промпта: английские visual-ключи запрашивались **отдельным полем** рядом с русским нарративом, вместе с эмоцией и монтажной заметкой на сцену; ответ требовался строго машиночитаемым. Прямая иллюстрация того, какое evidence producer обязан заполнять. **Скрипты не восстанавливать; сетевой/модельный вызов требует отдельного owner approval** |
| `legacy/main.py` | **FACT.** Промпт полного публикационного пакета: 10 вариантов названия, описание, главы с таймкодами, visual plan по сценам, short hook и 15 тегов — одним запросом из готового сценария | `MIGRATE KNOWLEDGE` | этот registry → тот же будущий metadata product slice | Состав публикационного пакета, ожидаемый пользователем, и то, что он выводится из финального сценария. Совпадает с полями `src/youtube_metadata.py` — два независимых источника одного продуктового ожидания |
| `legacy/{download_broll,assemble_broll_video,assemble_broll_with_text,add_music,render_from_scene_plan}.py` | **FACT.** Пять прототипов: первый Pexels-результат на сцену, подрезка каждого клипа до 5 с, ресайз 1920×1080, конкатенация MoviePy, статичный текст поверх, музыка фиксированной громкостью 0.18, черновой рендер трёх сцен из JSON. Каждый шаг перекрыт каноническим `src/news/final_renderer.py`, asset-stage и music owner; уникальных правил не содержат | `ARCHIVE ONLY` | — | Активного восстановления не требуется: retirement tag и history достаточны. Единственные не перекрытые идеи — фиксированная длина плана и первый попавшийся результат провайдера — уже опровергнуты `adaptive_shot_duration` и лестницей приёмки кандидатов |
| `src/tts_providers/moss_tts_provider.py` | **FACT.** Интеграция локального провайдера отдельным процессом: запуск из **собственного** `.venv` вендорного репозитория (`Scripts/python.exe` на Windows), команда `-m moss_tts_nano generate --backend … --text … --output-audio-path … --max-new-frames …`, для `onnx` добавляются `--execution-provider` и `--voice`, иначе `--device`; режим `voice_clone` включается только при заданном `prompt_audio_path`; таймаут по умолчанию 900 с; перед запуском проверяются наличие каталога, `infer.py`, `requirements.txt`, вложенного дубликата репозитория и venv-интерпретатора; успехом считается **непустой** выходной файл, а не нулевой код возврата | `MIGRATE KNOWLEDGE` | этот registry → существующий TTS provider owner (**K06**) | Как безопасно интегрировать локальную ML-модель: чужой процесс со своим интерпретатором и зависимостями, обязательный таймаут, диагностируемые предусловия с внятным сообщением на каждое, проверка фактического артефакта, а не кода возврата. Применимо к любому будущему локальному провайдеру. **MOSS как провайдер не реинтегрируется (OD-7)** |
| `MOSS_TTS_Nano/START_HERE.md` (untracked) | **FACT.** `MOSS_TTS_Nano/` исключён `.gitignore:2` и содержит **0 tracked-файлов**, поэтому retirement tag и Git history эту директорию восстановить **не могут** — записанное здесь знание единственное сохраняемое. Из project-authored инструкции: запуск локального web-UI, автоподхват русских пресетов из `assets/voice_samples` без правки кода, требования к reference-сэмплу (короткий чистый wav, один говорящий), имена результатов с датой/временем/сэмплом, и что отказ `WeTextProcessing`/`tn`/`pynini` на Windows **не фатален** — генерация продолжается на сыром тексте с явным сообщением | `MIGRATE KNOWLEDGE` | этот registry (единственный носитель) | Требования к reference-сэмплу для клонирования голоса; принцип «новый голос добавляется файлом, а не правкой кода»; опциональная нормализация текста деградирует явно и не валит синтез. **Vendor repo в Workspace не переносить (OD-7)** |
| `MOSS_TTS_Nano/` (вендорный репозиторий) | **FACT/INFERENCE.** FACT: 56k+ файлов, собственные `pyproject.toml`, `requirements.txt`, `venv/`, `tests/`, `finetuning/`, `.egg-info`, `app.py`, `infer.py`, `generated_audio/`, логи; 0 tracked-файлов; upstream — публичный сторонний проект. INFERENCE: project-unique знание исчерпывается двумя строками выше. Продуктовое решение: MOSS не нужен (**OD-7**) — 0.1B локальная CPU-модель проверялась как бесплатный fallback к платному ElevenLabs и в качестве активного провайдера не выбрана | `DELETE` | — | Восстанавливать нечего: upstream получается заново, `venv/` воспроизводится, project-unique знание уже записано. **Не сохранять 56k файлов «на всякий случай»** |
| `scripts/test_moss_voices.py` | **FACT.** Ручной voice-evaluation harness: обходит два корня сэмплов с дедупликацией по resolved-пути, гоняет три фиксированных текста (короткий русский, русский нарратив, короткий английский), измеряет `audio_duration / elapsed` как «×realtime», пишет инкрементальный markdown-отчёт и оставляет **пустые поля для человека**: naturalness, similarity, russian_quality, noise, speed, `usable_for_youtube: yes/no`. При отсутствии сэмплов отчёт объясняет требования к ним вместо падения | `MIGRATE KNOWLEDGE` | этот registry → будущая voice/TTS evaluation работа | Форма сравнения голосов: фиксированный набор текстов на всех языках продукта, машинная метрика скорости плюс структурированное человеческое суждение, инкрементальная запись отчёта (долгий прогон не теряется), пустой прогон объясняет, чего не хватает. `sys.path`-инъекция, зашитый `G:/` и имя `test_*` вне `tests/` (**C18**) — дефекты, не знание |
| `tests/test_documentary_visual_engine.py` (11 проверок) | **FACT.** Классификация проверок: **PRODUCT CONTRACT** — ручные ассеты используются раньше библиотеки и API; survival-оверлей остаётся subtitles-only; self-eval применяет montage-правила. **ARCHITECTURE INVARIANT** — voice-манифест переиспользует кэш вместо повторного синтеза; MOSS-fallback срабатывает при отказе ElevenLabs. **CHARACTERIZATION** — adaptive pacing по mood и длительности озвучки; multi-clip план сцены с debug-выходом. **LEGACY ANCHOR** — форма legacy render-плана, cinematic-preview профиль, survival-релевантность, music-план `voice_over_ready` | `KEEP MINIMAL REGRESSION` | этот registry → **PLAN-10D** (приоритет ручных ассетов и дедупликация) и **K06** (лестница fallback озвучки) | Минимально сохранить два поведения: (1) явно предоставленный пользователем ассет побеждает найденный автоматически; (2) отказ платного TTS понижает уровень до следующего провайдера, помечает сцену в манифесте и не прерывает сборку. Legacy-движки и legacy-каналы ради этого не сохраняются |
| `tests/test_channel_profiles.py` (5 проверок) | **FACT.** **PRODUCT CONTRACT** — video task переопределяет пути вывода и metadata; конфиг без канала сохраняет корневые `outputs`. **CHARACTERIZATION** — task управляет quote/scene/metadata планами; survival-задание строит story-metadata и пути. **LEGACY ANCHOR** — генерация PNG-обложки конкретного legacy-задания | `MIGRATE KNOWLEDGE` | этот registry → существующий `config_resolver` / project-path owner | Полезный проверяемый случай: разрешение конфигурации без канала **не должно** ломаться и продолжает писать в корневой каталог вывода — это правило обратной совместимости, а не снимок legacy. Отдельный fixture не требуется: канонический путь уже проверен собственными тестами |
| `tests/test_size_comparison_engine.py` (6 проверок) | **FACT.** Классифицирован выше отдельной строкой `KEEP MINIMAL REGRESSION`. Модульная метка в `tools/qa/check_agent_docs.py` — `LEGACY ANCHOR`, и это верно для модуля целиком: он импортирует ретайримый движок | `KEEP MINIMAL REGRESSION` | этот registry → будущий size-comparison product slice | См. строку `tests/test_size_comparison_engine.py` выше. Модуль ретайрится вместе с движком; переживает только описанный минимальный случай |
| `tests/test_moss_tts_provider.py` (4 проверки) | **FACT.** **ARCHITECTURE INVARIANT** — синтез идёт через отдельный venv-интерпретатор вендорного репозитория, а не через интерпретатор продукта; `prompt_audio_path` включает режим `voice_clone`. **PRODUCT CONTRACT** — отказ CLI превращается в понятную ошибку, а не в traceback. **LEGACY ANCHOR** — дословный дефолтный русский тестовый текст | `MIGRATE KNOWLEDGE` | этот registry → **K06** (provider boundary) | Проверяемое правило для любого будущего локального провайдера: чужой процесс запускается своим интерпретатором, а его отказ доходит до пользователя классифицированной ошибкой. Сам модуль ретайрится вместе с `src/tts_providers/` |
| `tests/test_moss_voice_tester.py` (3 проверки) | **FACT.** **CHARACTERIZATION** — обнаружение сэмплов из нескольких корней. **PRODUCT CONTRACT** — пустой прогон объясняет, как добавить сэмплы; отчёт содержит поля ручной оценки. Полезное поведение уже записано строкой `scripts/test_moss_voices.py` | `ARCHIVE ONLY` | — | Активного восстановления не требуется: знание сохранено выше, модуль ретайрится вместе со своим носителем в PLAN-L4 |
| `tests/test_legacy_pipeline_internals_contract.py`, `tests/test_legacy_pipeline_application_boundary.py` (7 проверок) | **FACT.** Обе — **CHARACTERIZATION** этапов 6F/8D: фиксировали, что root-модуль остался фасадом, что patch-points переиспользуют существующих owners, что `LegacyPipelineArtifacts` не изменился и что compatibility-app делегирует в фасад. Рефакторинг, который они охраняли, завершён; новых продуктовых правил в них нет | `ARCHIVE ONLY` | — | Активного восстановления не требуется: своё назначение выполнили, retirement tag и history достаточны. Ретайрятся вместе с носителем (**PLAN-L3/L4**) |
| `src/legacy_pipeline/workflow.py` | **FACT.** Оркестрация как последовательность плана: quote → metadata → scene → (prod-preview обрезка сцен) → voice → применение тайминга озвучки к плану сцен → обратное выравнивание манифеста → intro → music → assets → render plan; все артефакты пишутся **до** рендера; `--skip-render` всё равно пишет `self_eval` со своим объяснением; `RenderStageError` перехватывается и превращается в `self_eval` с именем стадии и причиной, а не в traceback | `MIGRATE KNOWLEDGE` | этот registry → **MOTION-CS1**; смежно **C43a** | Двусторонняя синхронизация: длительности озвучки применяются к плану сцен, затем манифест выравнивается обратно по плану; все планы персистятся до дорогого шага; пропуск и отказ рендера оба оставляют машиночитаемый результат с причиной, а не пустоту |
| `src/production_plan/story_card_short_render.py::build_story_card_layout` | **C53, FACT.** Адаптивная вёрстка без фиксированных координат: `_measure_wrapped_block` считает **реальную** высоту блока, повторяя вертикальный шаг отрисовки, поэтому измерение не может обрезать текст; `_line_height` = высота bbox `"Ag"` конкретного шрифта; `_wrap_line` — жадный перенос по `draw.textlength` против доступной ширины, слово длиннее строки **не разрывается** (`or not current`) и выходит за max_width; центральное видео получает весь остаток по вертикали при ограничениях `min_video_aspect` 1.18 и `min_video_height` 40; шрифт выбирается лестницей `DejaVuSans → arial → load_default`; контраст — вторая отрисовка со смещением 2 px | `MIGRATE KNOWLEDGE` | этот registry → parity case **MOTION-CS2** → **MOTION-CS4** | Вертикальная геометрия выводится из фактически отрисованного текста, а не из констант; измеряющий и рисующий код обязаны иметь одинаковый шаг строки; длинное неразрывное слово — известный незакрытый edge case, новый backend обязан решить его явно; медиа забирает остаток пространства при защищённых минимальных пропорции и высоте |
| `tests/test_story_card_short_renderer.py` | **C53, FACT.** Parity-контракт уже существует и его не нужно изобретать: `test_layout_keeps_card_inside_safe_zones` (карточка внутри safe zones, видео положительного размера и ниже верхнего текста) и `test_adaptive_layout_fills_card_and_protects_video` (площадь видео больше прежнего фиксированного 836×560, `content_occupancy_ratio ≥ 0.88`, соотношение ≥1.15, `bottom_gap ≤ 60`, зазор верхний текст → видео ≤40, строгий порядок видео < бренд < комментарий) | `KEEP MINIMAL REGRESSION` | этот registry → **MOTION-CS2** parity, затем **MOTION-CS4** | Именно эти два теста — минимальный parity-fixture замены renderer'а: safe zones соблюдены, порядок блоков не нарушен, медиа не схлопнулось и не выдавило текст. **Шаблон `story_card_text_only_v1` не удаляется (OD-M-8)** |
| `src/assets/generated_infographic.py::build_generated_asset` | **C56, FACT.** Спека → project-owned актив: `InfographicSpec.fingerprint()` = sha256 по generator id и всем значимым полям; fingerprint входит в **имя файла** (`<scene>_<variant>_<fp12>`), поэтому пересчитанная версия не перезаписывает байты, на которые ссылается активный манифест; пишутся SVG (запись отрисованного) и PNG (то, что умеет ffmpeg); technical validation требует формат PNG и точный размер 1080×1920, иначе `ValueError`; считается sha256 файла и попадает и в `checksum_sha256`, и в provenance; лицензия — `project_generated` / `user_owned`, коммерческое использование и модификация разрешены, атрибуция не требуется, `review_required=False` | `MIGRATE KNOWLEDGE` | этот registry → **MOTION-CS4** | Полный контракт: fingerprint спеки → стабильное уникальное имя → две формы (запись и рендер) → техническая валидация до регистрации → checksum → license и provenance проекта. **Новый author встраивается в этот контракт, а не рядом с ним;** второй asset-путь не создаётся. Рисующая часть (константы канвы, зашитая палитра, `load_default()`) — заменяемая, а не сохраняемая |
| `src/assets/generated_infographic.py::spec_from_scene` | **C56, FACT.** Возвращает `None`, когда `scene.visual_brief.infographic` отсутствует или пуст; docstring фиксирует причину: диаграмма, построенная на числах, которые модуль вывел сам, была бы утверждением, которого сценарий не делал. Ни одно значение не угадывается из нарратива | `MIGRATE KNOWLEDGE` | этот registry → **MOTION-CS4** и будущая data-evidence policy | Правило «нет evidence → нет фактической диаграммы»: отсутствие авторских значений даёт честное `None`, а не правдоподобную картинку. Это тот же fail-closed принцип, что и у producer'а; ослабление ради заполненности кадра запрещено |
| `moviepy==2.2.1` — фактические callers | **C54/C55, FACT (уточнено 2026-08-02).** Активные callers, переживающие PLAN-L: `src/production_plan/story_card_short_render.py:10` (`VideoClip`, `VideoFileClip` — единственное реальное использование композиции) и два duration-probe в `try/except` с возвратом `0.0` — `src/audio/tts/elevenlabs_provider.py:138`, `src/audio/voice_cli.py:327`. Legacy-callers, умирающие в PLAN-L3, — **шесть**, а не три: `self_eval`, `music_tools`, `video_renderer`, `size_comparison_engine`, `thumbnail_engine`, `voice_engine`. Существующий владелец того же факта для probe — `src/assets/frame_sampling.py::ffprobe_media_info` (`duration_sec`) | `MIGRATE KNOWLEDGE` | этот registry → **MOTION-CS4** (dependency gate), **C54** (замена probe) | Снятие зависимости требует закрытия ровно трёх активных callers, из которых два — не композиция, а длительность файла и заменяются существующим ffprobe-владельцем без нового owner. **Зависимость не объявлять удалённой заранее.** Утверждения о производительности MoviePy без измерений запрещены |

**Что этот gate сознательно не делал.** Capability не мигрировалась, retirement
не выполнялся, tag и bundle не создавались, ни один файл не удалён и не
перемещён; production-код, tests, configs, schemas, manifests и runtime не
изменялись. Disposable runtime/media/cache в таблицу не включались — их владелец
`PLAN-14D` → `PLAN-14E`.

Обязательные к проверке families: `channels/{psychology,quotes,survival,size_comparison}`
и `content/` (OD-1) · 20 движков корня `src/` · `legacy/` ·
`src/legacy_pipeline/workflow.py` · `config/video_style.json` ·
`MOSS_TTS_Nano/` + `src/tts_providers/` (OD-7) · `src/size_comparison_engine.py`
(OD-10) · legacy test-модули.

**Проверено PLAN-L0, 2026-08-02.** Все перечисленные families аудированы.
Уточнения фактов, полученные при аудите (измерения, не нормативы):

- 20 движков корня `src/` — это ровно `src/*.py` **кроме** `__init__.py`,
  `media_library.py` и `utils.py`; суммарно **4903** строки, что совпадает с
  evidence PLAN-L. Исключения подтверждены заново: `media_library.py` имеет
  четыре активных non-legacy production-caller
  (`news/asset_manager`, `news/asset_manifest_builder`,
  `news/asset_provider_adapters`, `providers/local_library_provider`),
  `utils.py` — активный caller `src/audio/tts/env.py`.
- test-модулей legacy-стека фактически **семь**, а не шесть: пять модулей,
  которые `tools/qa/check_agent_docs.py` уже помечает `LEGACY ANCHOR`
  (`test_channel_profiles`, `test_documentary_visual_engine`,
  `test_size_comparison_engine`, `test_legacy_pipeline_internals_contract`,
  `test_legacy_pipeline_application_boundary`), плюс `test_moss_tts_provider`
  (умирает с `src/tts_providers/`, PLAN-L3) и `test_moss_voice_tester`
  (умирает со `scripts/`, PLAN-L4). Прежнее «6» — измерение более раннего
  аудита, а не инвариант.
- `MOSS_TTS_Nano/` исключён `.gitignore` и содержит **0 tracked-файлов**,
  поэтому обратимый retirement-механизм к нему неприменим: annotated tag и
  bundle из него ничего не восстановят. Project-authored знание из него
  сохранено строками таблицы выше — это единственный носитель.
- legacy-callers `moviepy` — шесть модулей, а не три, как записано в **C55**.
  Строка C55 остаётся в силе по существу (снятие зависимости только после
  последнего caller); уточняется только состав.

**Обязательные находки ревизии 2.1** — PLAN-L0 сохраняет их **до** retirement;
старый pipeline ради них **не** сохраняется:

| Находка | Класс | Целевой потребитель | Registry |
|---|---|---|---|
| legacy query expansion ladder `build_query_variants` (суффиксы, усечение, mood, channel-расширения) | `MIGRATE KNOWLEDGE` | **PLAN-9B-2** | C46 |
| local-library diversity reserve (`min_local_diversity_per_scene` / `reserved_download_slots`) | `MIGRATE KNOWLEDGE` | **PLAN-10D** | C47 |
| практика «provider-ready английские visual keywords существуют отдельным полем, отделённым от нарратива» | `MIGRATE KNOWLEDGE` | ADR / registry | C48 |

**Обязательные находки motion rendering (2026-08-01)** — сохраняются **до**
замещения соответствующего owner по **PD-11**; старая реализация ради них не
сохраняется:

| Находка | Класс | Целевой потребитель | Registry |
|---|---|---|---|
| поведение Story Card: адаптивный текст, вёрстка по реальным метрикам шрифта, работа с длинными строками, вертикальный layout | `MIGRATE KNOWLEDGE` + `KEEP MINIMAL REGRESSION` | parity case **MOTION-CS2** → **MOTION-CS4** | C53 |
| контракт «спека → project-owned asset с license/provenance/checksum/technical validation» и fingerprint спеки (`build_generated_asset`) | `MIGRATE KNOWLEDGE` | **MOTION-CS4** — новый author встраивается **в** этот контракт, а не рядом | C56 |
| правило «нет evidence → нет фактической диаграммы» (`spec_from_scene` возвращает `None` без авторских значений) | `MIGRATE KNOWLEDGE` | **MOTION-CS4** и будущая data-evidence policy | C56 |
| callers и фактическая необходимость `moviepy` | `MIGRATE KNOWLEDGE` | **MOTION-CS4** (dependency gate) | C54, C55 |
| анализ качества готового файла (`src/self_eval.py`): длительность, разрешение, число сцен, переполнение текста | `MIGRATE KNOWLEDGE` | будущее расширение существующего quality owner; **MOTION-CS1** (technical QA сегмента) | C45-смежное |

Что искать в каждом: reusable algorithm · domain и product knowledge · prompts,
templates, visual rules · rights и licensing knowledge · fallback и recovery
logic · edge cases · reusable schema knowledge · полезные characterization и
product tests.

## Preserved runtime corpus

Канонический список того, что переживает runtime reset. Всё, что не перечислено
здесь и классифицировано как runtime/generated/media, — disposable (OWNER,
2026-07-31). Операционные детали — `PROJECT_EXECUTION_PLAN.md` →
«Safety boundaries».

**Исполнено 2026-08-08 — owner-authorized runtime media cleanup `projects/`
(bounded slice от HEAD `8bf2271`, отдельный от PLAN-14D и его не закрывающий).**
Удалены 792 untracked runtime-файла (~7.04 GiB) в 31 старой project directory:
downloaded/stock media, preview-кэши и кадры вне evidence-списка, review HTML,
rendered/localization outputs и прочие generated media. Tracked файлы не
менялись. Сохранено 950 файлов (~153 MiB): полный корпус JSON/SRT/ASS
манифестов всех проектов — superset будущего representative corpus, отбор и
внешний bundle остаются за C32/PLAN-14D и этим слайсом **не** выполнены; все
45 runtime-путей `historical_runtime_paths()` PLAN-9D (14 манифестов + 31
кадр; защищены PLAN-9D-A до шага (4) cleanup sequencing);
`projects/plan9d_current_capture_v1/` целиком (124 файла, visual evidence
PLAN-9D-C); SHA-якорённые артефакты `PRODUCT_EVIDENCE_GATE.md`
(`contact_sheet_6frames.png`, `draft_1080x1920.mp4` проекта
`2026-07-28_pochemu-kosatki-vzryvayut-ogromnyh-ryb-2`); example source assets
`COMMANDS.md` (`story_card_owl_test/final_test.mp4`, `final_test_v2.mp4`);
`ATTRIBUTION.md` каждого проекта (rights/attribution evidence). Счётчики
N02/C32 (1618 файлов, 749 JSON, ~700 медиа) — исторические измерения своих
provenance-дат и здесь намеренно не переписаны. Verification: все preserved
paths сверены по существованию, targeted PLAN-9D + content-creation +
project tests — 286 OK.

| Предмет | Почему сохраняется | Owner решения |
|---|---|---|
| минимальный representative набор JSON/SRT/ASS манифестов проектов | единственная база проверки tolerant readers и resume на реальных legacy-формах; состав отбирается, а не сохраняется целиком | C32, PLAN-14D |
| `assets/library/metadata/media_index.json` | provenance и rights локальной медиатеки; нужен аудиту PLAN-10D | N03 |
| versioned SVG в `manual_assets/**` | versioned resource, не runtime media | N03 |
| `config/` кроме `video_style.json`; `channels/nature_science_news_ru`, `channels/nature_pulse` | активная versioned-конфигурация: 8–21 caller на файл | N04, T.9 |
| live-eval dataset / results / frames | active evaluation resource, читается production-кодом; нужен PLAN-9D | C31 |
| минимально необходимый voice sample активного профиля, если он реально требуется | переносится во внешний Workspace **с provenance**, иначе удаляется | OD-3 |

## Accidental invariants

Тесты и проверки, которые замораживают случайную структуру или момент времени, а
не product/public behavior. Класс — **LEGACY ANCHOR** по test classification
`PROJECT_EXECUTION_PLAN.md`. LEGACY ANCHOR **не препятствует сознательному
ретайру старой архитектуры** и переписывается либо удаляется вместе с ней.

| Предмет | Что именно заморожено | Почему это anchor, а не контракт | Действие | Gate |
|---|---|---|---|---|
| `tests/test_apps_structure.py` (19 строк) | существование файлов `pipeline.py` и `anime_factory/pipeline.py`; импортируемость `apps.*.main` | это снимок временных compatibility wrappers, а не обещание пользователю | переписать в fitness-тест «нет второго canonical public CLI», затем retire исходный | **PLAN-9B-5b или PLAN-L4 — что наступит раньше.** Общее правило: test/caller классифицируется и мигрирует/ретайрится вместе с тем parent surface, который фактически удаляется первым. Модуль импортирует `apps.news_to_short.main` (ретайр — **PLAN-9B-5b**) и `apps.youtube_pipeline.main` (ретайр — **PLAN-L4**); там же `tests/test_fullscreen_voiceover_application_boundary.py`. Все реальные test-callers wrapper'а обязаны быть migrated/updated **до** его retirement |
| `tests/test_reproducibility_contract.py:24-27` | буквальное равенство `packages.find.include == ["ai_youtube*","src*","anime_factory*","apps*"]` | упадёт в момент исправления C25 и удаления `apps/`; фиксирует implementation detail с авторитетом контракта | переписать в инвариант: «нет package root вне объявленного набора», «wheel импортирует канонический CLI» | **PLAN-L4** |
| `tests/test_stage2_agent_onboarding.py:19` | `today=date(2026,7,29)` и точное равенство множества `REQUIRED_SKILLS` | замораживает момент времени; добавление reviewer-skill (PLAN-6E) уронит тест | заменить на минимальный обязательный набор skills + автопроверку всех найденных; дату передавать аргументом | **PLAN-6A** |
| `tests/test_stage2_agent_onboarding.py:26` | `AGENTS.md ≤ 120` строк | число не является архитектурным решением; `AGENTS.md` должен быть коротким **по responsibility** | переклассифицировать в measurement/warning | **PLAN-6A** |
| `tests/test_documentary_visual_engine.py` (295), `tests/test_channel_profiles.py`, `tests/test_size_comparison_engine.py` | реализация legacy-движков и чтение legacy-каналов | замораживают ретайримую архитектуру | KSG извлекает полезные проверки, затем retire | **PLAN-L0 → L3** |
| `tests/test_legacy_pipeline_internals_contract.py`, `tests/test_legacy_pipeline_application_boundary.py` | CHARACTERIZATION этапов 6F/8D | своё назначение выполнили: рефакторинг, который они охраняли, завершён | retire вместе с носителем | **PLAN-L3 / L4** |

Не-anchor для контраста, менять нельзя без отдельного решения:
`tests/test_asset_import_boundaries.py` и `tests/test_capability_consistency.py`
— **ARCHITECTURE INVARIANT**; проверки `modes.blocking_reasons` (rights,
`must_avoid`, misleading, битый файл) — **PRODUCT CONTRACT**.

## Closure rule

Registry закрывается только когда каждая строка:

- реализована отдельным проверенным commit;
- переведена в permanent `keep`/`do_not_touch` с owner/public evidence;
- либо явно отложена с актуальным owner decision.

Статус `wrapper`, test-only caller или planned capability без exit condition не
закрывает registry.

Исторический `docs/architecture/CLEANUP_INVENTORY.md` остаётся архивным
предшественником и не заменяет этот проверенный registry.
