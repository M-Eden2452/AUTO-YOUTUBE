---
status: current
last_verified_commit: affa138
last_verified_date: 2026-08-01
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
  - content
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
- **C34–C50** — evidence ревизии 2.1 (deep-dive), 2026-07-31 от `adcbb19`.

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
| A02 | 9 tracked legacy файлов в `outputs/` | `archive` | пути всё ещё заданы config/root pipeline; сами outputs воспроизводимы не все | backup + manifest/reference check, затем untrack/archive | 10 |
| D01 | compatibility `PexelsAssetProvider`, `PixabayAssetProvider`, `UnsplashAssetProvider` в `src/news/asset_provider_adapters.py` | `delete` | stage 9 zero-caller audit подтвердил только definitions/re-export/test references; active factory использует canonical `StockProvider` implementations | завершено: classes, raw provider imports и `asset_manager` re-exports удалены; `AssetProvider`/factory patch-point сохранены | 9 D01 complete |
| D02 | `src/news/stock_video_downloader.py` | `delete` | stage 9 AST/repo audit подтвердил отсутствие production imports/calls, package export, CLI и current command; test был единственным executable caller | завершено: wrapper удалён, два исторических production docstring исправлены; canonical asset stage сохранён | 9 D02 complete |
| D03 | `packages/README.md` и пустая planning directory | `delete` | повторный audit подтвердил один tracked planning README, отсутствие runtime/current callers и package discovery только из `ai_youtube*`, `src*`, `anime_factory*`, `apps*` | завершено: README и пустая physical directory удалены; historical snapshots не переписаны | 9 D03 complete |
| D04 | untracked `__pycache__/`, `*.pyc` | `delete` | 0 tracked matches; bytecode воспроизводим | удалять только filesystem-cleanup slice, не вместе с refactor | 10 |
| N01 | `.env`, `.env.*`, credentials/private keys | `do_not_touch` | конфигурация может содержать secrets; содержимое не проверялось | никогда не читать/коммитить/удалять автоматически | всегда |
| N02 | `projects/` — 1618 файлов | `split` | **изменено ревизией 2 (OWNER).** 749 JSON + ~700 медиа, 0 tracked; оба project readers используют root | медиа — disposable, удаляется на runtime reset; JSON/SRT/ASS проходят classify/dedupe и дают **минимальный representative corpus** (C32); полный набор — во внешний retirement bundle | 14D |
| N03 | `assets/`, `manual_assets/`, `music/` | `split` | **изменено ревизией 2 (OWNER).** 287 + 18 + 3 файла; смешанные runtime media и versioned resources | **keep:** `assets/library/metadata/media_index.json` (provenance/rights), versioned SVG в `manual_assets/**`. **delete:** всё медиа, кэши. `assets/voice_samples` — **disposable (OD-3)**; минимально необходимый sample активного voice profile переносится во внешний Workspace с provenance, иначе удаляется | 14D/14E |
| N04 | `content/`, включая `story_card_jobs.tsv` | `obsolete-with-legacy` | **изменено ревизией 2.** [FACT] это fixtures legacy-стека, а не user data: `content/survival/juliane_koepcke_001.json` и `channels/survival` читаются `tests/test_documentary_visual_engine.py` и `tests/test_channel_profiles.py`; `story_card_jobs.tsv` не имеет runtime caller | ретайр вместе с legacy-стеком **после Knowledge Salvage Gate** (OD-1): visual rules, промпты и продуктовые декларации форматов сохраняются как knowledge | **PLAN-L0 → L3** |
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
| C19 | `outputs/*.json` (**8 файлов**) | Git index ∩ ignore | **FACT** | `git ls-files -i -c --exclude-standard` перечисляет `asset_plan`, `music_plan`, `quote_plan`, `render_plan`, `render_stage`, `scene_plan`, `self_eval`, `youtube_metadata` — tracked при совпадении с `outputs/**/*.json` | класс решён: generated output legacy-стека. Producer умирает вместе с `pipeline.py`, поэтому untrack выполняется в L4, а не отдельным minimalism-слайсом | **PLAN-L4** |
| C20 | `output/`, `tmp/` | никто | **FACT** | `git check-ignore` → NOT IGNORED для обоих; `output/` = 1 файл (`output/pdf/PROJECT_EXECUTION_PLAN_mobile.pdf`, 280 820 байт, 2026-07-30); `tmp/pdfs/` пуст | правила `.gitignore` для `output/` и `tmp/` добавлены **в PLAN-14F** (единственный slice с `.gitignore` в allowed zones); untracked-артефакты удалены — это commit не требует, воспроизводимый cache/temp закрывает 14C. PLAN-6B — только detector | PLAN-6B (detect) → **14F** (`.gitignore`) → 14C (untracked cleanup) |
| C21 | `assets/broll/.gitkeep` | Git index ∩ ignore | **FACT** | директорное правило `assets/broll/` обесценивает последующее `!assets/broll/.gitkeep`; файл tracked и ignored одновременно | правило заменено на `assets/broll/*` **в PLAN-14F** (единственный slice с `.gitignore` в allowed zones); `git ls-files -i -c` не содержит `.gitkeep`. PLAN-6B — только detector | PLAN-6B (detect) → **14F** (fix) |
| C22 | `docs/contracts/STAGE1_PUBLIC_CONTRACTS.md` | orphan | **FACT** + **DEFER** | 0 входящих ссылок; называет `src.content_creation.cli` «current CLI»; канонический `python -m ai_youtube` не упоминает | target responsibility определяется PLAN-12E **по содержимому файла**, не автоматически по каталогу; затем update или archive | PLAN-12E → 7/12C |
| C23 | `docs/architecture/visual_rendering_policy.md` | orphan; **временно защищён от archive/delete** | **FACT** + **INFERENCE** | FACT: 0 входящих ссылок. INFERENCE: единственный владелец визуального quality bar — `docs/implementation` построчно не читался | PLAN-12E выбрал target path (кандидат — `docs/product/QUALITY_BAR.md`); PLAN-12B подтвердил отсутствие competing quality owner. **Ревизия 2 перенесла подтверждение из PLAN-1C в PLAN-12B** вместе с пофайловой классификацией `docs/*` (C27). **До этого archive/delete запрещены** | **PLAN-12E → 12B** |
| C24 | hardcoded `G:/` в versioned config | `config/`, `channels/` | **FACT** | `config/video_style.json` — `moss_tts_path`, `vault_path`; `channels/psychology/style.json` — `moss_tts_path` | **оба носителя умирают в L3:** `config/video_style.json` и `channels/psychology/` ретайрятся вместе с legacy-стеком, поэтому отдельного исправления не требуется. Если после L3 hardcoded drive обнаружится в выжившем versioned config — резолвить через существующий resolver или env | **PLAN-L3**, остаток → PLAN-14B |
| C25 | `pyproject`: `pipeline` в дистрибутиве без `scripts` | packaging | **FACT** + **INFERENCE** | FACT: `py-modules = ["pipeline"]`, `packages.find.include` без `scripts*`, `pipeline.py:9` импортирует `scripts.test_moss_voices`. INFERENCE: non-editable install ломает `import pipeline` — `pip install .` не выполнялся | дефект исчезает вместе с носителем: L4 удаляет `pipeline.py` и `scripts/` и снимает `py-modules`. Проверка: wheel собран и импортируется в temporary venv вне checkout | **PLAN-L4** |
| C26 | intended distribution boundary `tools/` | не определён | **DEFER** | `tools*` не входит в `packages.find.include`; все известные callers (`AGENTS.md`, `tests/test_stage2_agent_onboarding.py`, ADR, активный план) находятся внутри checkout | зафиксировать: `tools/` в wheel или только checkout. Предварительно — только checkout, тогда правка идёт в формулировку `AGENTS.md`, а не в `pyproject.toml`. **Добавлять `tools*` в wheel только ради работы repository QA из установленного пакета запрещено** | PLAN-6C |
| C27 | `docs/implementation` (96), `docs/audits` (9), `docs/architecture` (5), `docs/apps` (3) | смешанный | **DEFER** | проверены типы, заголовки, frontmatter, reference-граф и hash; построчно **не читались** | пофайловая классификация выполнена; до этого archive/move/delete любого файла этих семейств не выполняются. **Ревизия 2 перенесла классификацию из PLAN-1C в PLAN-12B:** PLAN-9A её не требует | **PLAN-12B** |
| C28 | `docs/architecture/localization_and_voice_architecture.md` | не классифицирован | **DEFER** | заранее не объявляется ни `keep`, ни archive-кандидатом | per-file evidence по всему `docs/architecture/*` получено | **PLAN-12B** |
| C29 | `outputs/asset_library_report.md` | tracked generated output | **FACT** | **не** входит в index ∩ ignore и не подпадает ни под одно правило `.gitignore` — в отличие от C19. Порождается production-кодом: `src/media_library.py:218` `create_asset_report(output_path="outputs/asset_library_report.md")`, вызывается из `src/legacy_pipeline/maintenance.py:459` по флагу `--asset-report` (`src/legacy_pipeline/cli.py:47`) | producer `--asset-report` умирает вместе с legacy CLI; untrack выполняется в L4. `src/media_library.py` при этом **сохраняется** — он используется активным news-путём | **PLAN-L4** |

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
| C43a | idempotency contract defect: explicit `stage=` path отключает output-validated idempotency ADR 0006 | **FACT** | условие `and not stage` в `src/news/pipeline.py` означает, что при явно запрошенной стадии проверка «completed + валидный output → пропустить» не применяется. Batch-режим (`until_stage=`) контракт **соблюдает**; explicit-режим повторно исполняет завершённые локальные стадии. Контракт для `stage=` не покрыт ни одним тестом. **Повторных платных операций нет** (несколько независимых guard'ов + существующие тесты); повторяются только локальные preview/final render. Вызовов **4–7** в зависимости от режима, не «ровно 7». **Severity: MEDIUM** | точный contract fix: один контракт идемпотентности, действующий во всех режимах вызова. Owner — **ADR 0006 / `src/news/pipeline.py`**, отдельный будущий bounded slice. Предусловие: подтвердить фактических `resume`/`force-stage`/`stop-stage` callers и public behavior | future bounded pipeline-contract slice |
| C43b | возможная поздняя orchestration convergence | **INFERENCE** | расслоение application orchestration / news pipeline ownership зафиксировано **ADR 0009 намеренно**; «два конкурирующих owner» **опровергнуто**. Дублируется ровно один факт — порядок хвостовых стадий | «один владелец порядка стадий» — **не** принятое решение. Выполняется **только если** после C43a остаётся архитектурная необходимость | **PLAN-13B** |
| C44 | export catalog mismatch | **FACT** | catalog объявляет **5** active export targets; три production-owner согласованно работают с **3**. `supported_export_targets` и `safe_zone_profile` имеют **ноль** production-читателей и в render decision не участвуют — каталог единственный outlier. Master копируется побайтово, адаптации под площадку нет | **truthful catalog**: убрать несуществующие targets из `active` **либо** перевести в `planned` — по фактическому intended product contract в момент implementation. **Создавать byte-identical копии ради соответствия каталогу запрещено.** **PLAN-11 = evidence gate**, обязанный ловить ложные product capabilities; **implementation owner — будущий bounded `production_catalog` slice**. Нового PLAN-ID нет | **PLAN-11** (gate) + future catalog slice |
| C45 | несколько lossy generations в final render | **FACT** + **INFERENCE** | **Исправлено ревизией 2.1.** Нормальный путь: segment encode CRF 23 → concat **`-c:v copy`** (не перекодирует) → audio + exact-duration encode CRF 20 → ASS subtitle encode CRF 21 → copies. Три lossy generations возникают **при audio + ASS subtitles**; без озвучки или без ASS — две, без обоих — одна. CRF 20 имеет документированную причину (`-shortest` + `-c:v copy` промахивается по длительности). **INFERENCE:** величина ущерба **никем не измерялась** — ни один аудит не рендерил | **PLAN-8 = roadmap owner** product-quality item. **Implementation owner — будущий bounded renderer slice, characterization первым.** Первый разумный кандидат: объединить audio/duration encode и subtitle burn в один encode, если characterization докажет эквивалентность. Полный filtergraph single-pass — отдельное более крупное исследование. «Single-pass как простой fix» — **неверно** | **PLAN-8** (roadmap) + future renderer slice |
| C46 | legacy query expansion ladder (`build_query_variants`) | **FACT** | настоящая лестница расширения: суффиксы, усечение, mood, channel-расширения | **MIGRATE KNOWLEDGE** → потребитель **PLAN-9B-2**. Старый pipeline ради этого не сохраняется | **PLAN-L0** |
| C47 | legacy local diversity reserve | **FACT** | `min_local_diversity_per_scene` / `reserved_download_slots`: «не заполняй сцену копиями одного локального клипа, оставь слоты под новый материал». Современного эквивалента **нет** — прямо релевантно проблеме повторяющихся визуалов | **MIGRATE KNOWLEDGE** → потребитель **PLAN-10D** | **PLAN-L0** |
| C48 | историческая практика внешних EN visual keywords | **FACT** | `visual_keywords` в legacy `content/**/*.json` — **входные данные**, а не выход кода: provider-ready английские ключи существовали отдельным полем, отделённым от нарратива | **MIGRATE KNOWLEDGE** (ADR/registry). Реализацию не восстанавливать | **PLAN-L0** |
| C49 | subprocess network-guard measurement | **FACT** | `tests/network_guard.py` живёт внутри test-пакета и дочерним процессом **не наследуется**. На audit HEAD `adcbb19` subprocess-модулей **12** (ранее записано 7). Это **measurement, не invariant** | зафиксировать как измерение; архитектурное решение по kill-switch **сейчас не принимается** — механизм и owner остаются implementation-time решением. **PLAN-6B остаётся report/measurement owner в своей текущей границе** | **PLAN-6B** (measure) + позднее решение owner |
| C50 | **rights fail-open:** явный `review_required=True` local-library record проходит канонический путь | **FACT** + **INFERENCE** | policy-правило для локальной библиотеки устанавливает `review_required: false` и **перезаписывает исходный флаг записи**, поэтому явно помеченная на ревью запись проходит. Обратного случая нет. Дефект не описан ни в одном предыдущем аудите | **[HARD] rights correctness.** Отдельный bounded fix с собственной verification: policy **не может silently снять** explicit `review_required` без доказанного разрешённого контракта. Owner — `apply_policy_to_candidate` / `with_policy_decision`. **Не смешивать с PLAN-10D architectural convergence** | отдельный bounded rights slice; исполним независимо после зелёного PLAN-4. **Deadline (2026-08-01): обязан быть CLOSED до расширения/convergence/повторного включения Global Local Library в PLAN-10D, до финального product evidence PLAN-11 / M1 и до любого live/publish-ready workflow, реально использующего Global Local Library asset с policy normalization** |

Строки C34–C50 закрываются каждая своим gate по общему `Closure rule` ниже.
Ничего из перечисленного пока не удалено — таблица `Retired` остаётся пустой.

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

| ID | Что ретайрено | Tag | Commit | Причина | Замена | Salvaged | Дата снятия с учёта |
|---|---|---|---|---|---|---|---|
| — | пока ничего не ретайрено | — | — | — | — | — | — |

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

| Family | Находка | Класс | Куда перенесено | Что стоит восстановить позже |
|---|---|---|---|---|
| — | PLAN-L0 не выполнен | — | — | — |

Обязательные к проверке families: `channels/{psychology,quotes,survival,size_comparison}`
и `content/` (OD-1) · 20 движков корня `src/` · `legacy/` ·
`src/legacy_pipeline/workflow.py` · `config/video_style.json` ·
`MOSS_TTS_Nano/` + `src/tts_providers/` (OD-7) · `src/size_comparison_engine.py`
(OD-10) · 6 legacy test-модулей.

**Обязательные находки ревизии 2.1** — PLAN-L0 сохраняет их **до** retirement;
старый pipeline ради них **не** сохраняется:

| Находка | Класс | Целевой потребитель | Registry |
|---|---|---|---|
| legacy query expansion ladder `build_query_variants` (суффиксы, усечение, mood, channel-расширения) | `MIGRATE KNOWLEDGE` | **PLAN-9B-2** | C46 |
| local-library diversity reserve (`min_local_diversity_per_scene` / `reserved_download_slots`) | `MIGRATE KNOWLEDGE` | **PLAN-10D** | C47 |
| практика «provider-ready английские visual keywords существуют отдельным полем, отделённым от нарратива» | `MIGRATE KNOWLEDGE` | ADR / registry | C48 |

Что искать в каждом: reusable algorithm · domain и product knowledge · prompts,
templates, visual rules · rights и licensing knowledge · fallback и recovery
logic · edge cases · reusable schema knowledge · полезные characterization и
product tests.

## Preserved runtime corpus

Канонический список того, что переживает runtime reset. Всё, что не перечислено
здесь и классифицировано как runtime/generated/media, — disposable (OWNER,
2026-07-31). Операционные детали — `PROJECT_EXECUTION_PLAN.md` →
«Safety boundaries».

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
