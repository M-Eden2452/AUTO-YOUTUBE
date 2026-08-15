---
status: current
last_verified_commit: 5787c61
last_verified_date: 2026-08-15
source_paths:
  - src/config_resolver
  - src/ai_youtube
  - src/content_creation
  - src/news
  - src/templates/story_card
  - src/production_plan
  - src/projects
  - src/project_foundation
  - src/assets
  - src/providers
  - src/runtime_network.py
  - src/audio
  - src/subtitles
  - src/legacy_pipeline
  - pipeline.py
  - apps
  - anime_factory
  - docs/current/ARCHITECTURE_BOUNDARY_MAP.md
  - docs/current/CLEANUP_REGISTRY.md
  - docs/implementation/README.md
---

# System Map

Код и Git имеют приоритет. Карта описывает существующие границы, а не разрешает
массовое перемещение. Она не ведёт журнал закрытий: evidence каждого шага живёт в
[PROJECT_EXECUTION_PLAN.md](PROJECT_EXECUTION_PLAN.md), завершённые structural и
vertical slices — в [CLEANUP_REGISTRY.md](CLEANUP_REGISTRY.md).

## Владельцы

| Область | Текущий авторитет | Роль |
|---|---|---|
| Пути и workspace | `src/config_resolver/paths.py` | единый resolver versioned resources, runtime roots и legacy fallback |
| Канонический CLI | `ai_youtube/`, `src/ai_youtube/cli/`, `src/content_creation/commands/` | dispatcher, domain handlers, parser modules и terminal presentation |
| Создание контента | `src/content_creation/` | compatibility CLI, wizard, shared application service и use-case wrappers |
| Fullscreen application | `src/ai_youtube/apps/content_creator/workflows/fullscreen_voiceover/` | canonical application use case и переэкспорт существующих news project/workflow contracts |
| Story Card application | `src/ai_youtube/apps/content_creator/workflows/story_card/` | canonical application use case и переэкспорт существующих project/evidence/workflow contracts |
| Fullscreen workflow | `src/news/` | staged `news_to_short`, resume и render |
| Story Card | `src/templates/story_card/`, `src/production_plan/` | workflow adapter и renderer |
| Проекты | `src/projects/`, `src/project_foundation/`, `src/news/project_store.py` | общий read API, atomic storage/lock primitives и output-validated news stage state |
| Ассеты | `src/assets/`, `src/news/asset_*.py` | shared selection/preview/completion contracts и app-specific manifest orchestration/adapters |
| Semantic evaluation | `src/assets/semantic_visual_evaluation*.py` | compatibility facade, offline dataset/metrics/report tooling и controlled live runtime |
| Providers | `src/assets/provider_contract.py`, `src/providers/` | единый `StockProvider` contract, canonical registry и provider adapters |
| Runtime network | `src/runtime_network.py` | единственный владелец разрешения на сетевое действие: default deny, поимённые классы, проверка до первого socket/HTTP |
| Audio/music | `src/audio/`, `src/localization/`, legacy `src/music_*` | canonical voice/TTS manifests/timeline; music ownership ещё требует 9B consolidation |
| Субтитры | `src/subtitles/` | единственный subtitle engine |
| Legacy/maintenance | `src/ai_youtube/apps/legacy_pipeline/`, `pipeline.py`, `src/legacy_pipeline/`, `apps/youtube_pipeline/` | canonical lazy adapter, root compatibility namespace, parser, maintenance handlers и legacy workflow |
| Video repurposing | `src/ai_youtube/apps/video_repurposer/workflows/anime_clipper/`, `anime_factory/` | canonical lazy adapter и существующий владелец Anime Factory workflow/project-output layout |

## Retrieval: четыре разных вопроса, четыре владельца

Их легко перепутать, и каждая путаница уже стоила дефекта:

- **какие запросы вообще существуют** — `build_scene_queries` / `build_slot_queries`
  в `src/assets/query_adapter.py`, питаемые expansion ladder
  `src/content/visual_planning/expansion.py`; второго query owner нет;
- **сколько разных запросов может отправить одна сцена** — `SceneRequestBudget`
  в `src/news/asset_provider_adapters.py`, один счётчик на сцену, разделяемый (а не
  копируемый) общим поиском и draft-ладдером; `search_provider` — последний
  владелец перед проводом;
- **повторить тот же HTTP-запрос** — `ProviderHttpClient`
  (`src/assets/http_client.py`), единственный владелец одного attempt budget;
- **попробовать другого кандидата** — download ladder
  (`ensure_selected_asset_downloaded`).

Пригодность кандидата решает один владелец — `rank_candidates` /
`select_best_candidate` в `src/assets/semantic_selection/candidate_ranker.py`;
права — `apply_policy_to_candidate` в `src/assets/license_policy.py`; media kind —
`select_with_media_policy` в `src/assets/semantic_selection/media_policy.py`.

## Продуктовая модель

```text
content_creator
  ├─ fullscreen_voiceover_v1
  └─ story_card_text_only_v1

video_repurposer
  └─ planned/disabled (Anime Clipper adapter существует, product capability не включён)
```

Целевая модель ADR 0016: два application engines поверх общих services.
`content_creator` создаёт short/long; `video_repurposer` обобщает существующий
Anime Factory для Anime/stream/film/podcast source videos. Documentary — future
template/workflow `content_creator`, не третье приложение. Это target boundary:
repurposer остаётся disabled до migration и evidence.

## Ключевые переходные ограничения

- `job.json` и `project.json` пока сосуществуют;
- `ProjectRepository` читает обе формы и legacy roots, но ничего не записывает;
- `python -m ai_youtube` — единственный канонический CLI;
- `pipeline.py`, `python -m src.content_creation.cli` и `apps/*` остаются
  compatibility entrypoints;
- default workspace остаётся корнем репозитория до отдельной физической миграции;
- произвольный workspace выбирается через CLI/env/path config, а versioned resources
  остаются привязаны к репозиторию;
- definitions и handlers CLI-команд разделены по domain-модулям; text/terminal
  rendering вынесен в общий presentation module, а старый CLI остаётся facade;
- `src.content_creation.wizard` остаётся compatibility facade с прежним
  `run_wizard`; working state/request translation, terminal presentation и
  интерактивные steps разделены по отдельным модулям.
- `src.content_creation.service` остаётся единой точкой входа
  `create_content`; request/template validation выполняет facade, а оба active
  workflow делегируются canonical boundaries
  `src.ai_youtube.apps.content_creator.workflows.fullscreen_voiceover` и
  `src.ai_youtube.apps.content_creator.workflows.story_card`.
  Старые `src.content_creation.fullscreen_voiceover_use_case` и
  `src.content_creation.story_card_use_case` остаются compatibility wrappers.
- `src.assets.semantic_visual_evaluation` остаётся public facade для root
  `pipeline.py`; offline dataset/metrics/reporting находятся в
  `semantic_visual_evaluation_tooling`, а gated execution —
  в `semantic_visual_evaluation_runtime`.
- root `pipeline.py` остаётся compatibility facade и сохраняет старые imports
  и patch-points; parser, maintenance handlers и legacy channel/video
  orchestration разделены в `src.legacy_pipeline`.
- `src.ai_youtube.apps.legacy_pipeline.adapter` лениво переэкспортирует root
  command/workflow surface; `apps.youtube_pipeline` использует эту canonical
  boundary, а root `pipeline.py` остаётся владельцем compatibility namespace
  и engine patch-points.
- `src.providers.registry` владеет default automatic provider set активного
  workflow. News factory делегирует registry; active asset stage остаётся в
  `src.news.asset_manager`.
- `src.ai_youtube.apps.video_repurposer.workflows.anime_clipper` лениво
  переэкспортирует существующие workflow и `EpisodePaths` contracts из
  `anime_factory`; `apps.anime_factory` использует эту canonical boundary, но
  catalog остаётся planned/disabled.

## Куда идти за подробностями

`docs/implementation/` — каталог implementation evidence и истории capabilities,
а не источник текущих границ: индекс и статусы находятся в
[docs/implementation/README.md](../implementation/README.md), и ни один документ
оттуда не переопределяет эту карту, ADR или код.

Полные callers/tests, persisted contracts и runtime roots зафиксированы в
[ARCHITECTURE_BOUNDARY_MAP.md](ARCHITECTURE_BOUNDARY_MAP.md); классификация
`keep/split/merge/move/archive/delete/do_not_touch`, delete evidence и очередь
малых slices — в [CLEANUP_REGISTRY.md](CLEANUP_REGISTRY.md).

Текущий checkpoint — **PLAN-9D**; авторитет и следующее точное действие —
во frontmatter [PROJECT_EXECUTION_PLAN.md](PROJECT_EXECUTION_PLAN.md).
