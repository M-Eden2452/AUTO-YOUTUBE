---
status: audit
audit_date: 2026-08-13
audit_head: f3b607a24d942d368af4f65ea830d4c685a278f3
working_branch: governance-reset
---

> **HISTORICAL EVIDENCE — не source of truth.** Снимок retrieval/material engine
> на HEAD `f3b607a`. При расхождении верны фактический код, Git, `AGENTS.md`,
> `docs/current/` и активный execution plan. Индекс каталога — [README.md](README.md).

## Errata переноса в репозиторий (2026-08-13)

Владелец принял отчёт как historical evidence; строка «Статус отчёта: внешний,
неутверждённый» ниже описывает состояние **до** принятия. Тело отчёта сохранено
дословно и не переписывалось. Перед записью находок в canonical docs они
перепроверены по коду; ниже — то, что **не** подтвердилось и в
`docs/current/CLEANUP_REGISTRY.md` не переносилось:

- **§13, C71** (tracked `outputs/*.json`) — не новая находка: уже записана
  строками **C19**, **C29** и **A02**.
- **§13, C73** (висячий `SUPERSEDED_CORPUS_PATH`) — не дефект:
  `tests/plan9d_corpus_builder.py:104-110` документирует намеренную замену
  корпуса слайсом PLAN-9D-A, а якорь — коммит `SUPERSEDED_CORPUS_COMMIT`
  (`git show <commit>:<path>` воспроизводит байты).
- **§13, C74** (конфликт классификаций тестов) — не противоречие: метка модуля
  (`tools/qa/check_agent_docs.py`) и класс отдельных проверок — разные оси;
  образец примирения уже есть в реестре для `test_size_comparison_engine.py`.
- **§6.3, `assets replace`** — команда **зарегистрирована** в каноническом CLI:
  `src/content_creation/commands/projects.py:20` через
  `src/ai_youtube/cli/commands/project.py:11`; `python -m ai_youtube --help`
  показывает `assets`. Пустой `register_commands` в
  `src/ai_youtube/cli/commands/assets.py:7` — мёртвый код, команду он не отключает.
- **§13, C65** — обход `require_network` шире, чем «6 call-sites»; фактический
  инвентарь записан в строке **C65** реестра.

Разошедшиеся номера строк: `_write_reviews` — фактически
`src/news/asset_manifest_builder.py:1126`; загрузка стека 3 — фактически
`src/production_plan/solar_vs_nuclear_render.py:543`.

Маппинг предложенных ID в фактические — раздел «Retrieval engine audit findings
(C64–C72)» в `docs/current/CLEANUP_REGISTRY.md`.

---

# RETRIEVAL / MATERIAL ENGINE — FULL REPOSITORY AUDIT

- **Дата:** 2026-08-13
- **HEAD:** `f3b607a24d942d368af4f65ea830d4c685a278f3` (branch `governance-reset`, origin в той же точке)
- **Метод:** read-only; 7 параллельных read-only субагентов + перекрёстная верификация несущих утверждений; статический анализ, выборочный git history. Python не запускался, сеть не использовалась, репозиторий не изменялся.
- **Статус отчёта:** внешний, неутверждённый. Не является source of truth, пока владелец не примет; после approve — отдельный docs-commit в `docs/audits/` по конвенции репозитория.
- **Companion-файл:** `RETRIEVAL_ENGINE_AUDIT_2026-08-13.classification.json` — машинно-читаемая классификация (path → класс A–G → якорь → evidence → действие).
- **Незакрытая оговорка метода:** достижимость проверена статически (импорты/wiring/строковые ссылки/dynamic import `importlib` в `apps/legacy_pipeline/adapter.py` / compatibility-dict `pipeline.py:98`); «недостижимо из canonical CLI» означает отсутствие статической цепочки от `src/ai_youtube/cli/main.py`, а не невозможность запуска legacy-entrypoint'ов напрямую.

Классификация: **A** active canonical · **B** active compatibility (нужен, есть/нужен exit condition) · **C** future useful (не live, доказанная будущая ценность) · **D** duplicate/superseded (canonical replacement существует) · **E** dead/cleanup candidate · **F** historical evidence · **G** uncertain. `CS` = confusion score 0–10 (способность запутать следующего агента).

---

## 1. EXECUTIVE VERDICT

1. **Ядро retrieval-движка чище, чем ожидалось.** Canonical-путь имеет по одному владельцу на каждую ответственность: один query boundary (`query_adapter`), один routing owner (`scene_strategy` + фасад `provider_routing`), один состав провайдеров (`providers/registry`), один rights owner (`license_policy`, fail-closed), один decision owner (`media_policy` → `candidate_ranker`), один download-путь через `require_network`. Покрытие плотное: 53 из 134 тестовых модулей (~1015 тестов) — retrieval.
2. **Но в репозитории живут ТРИ retrieval-стека, а не один.** Стек 2 (legacy documentary: `asset_finder` → `video_asset_engine`) и стек 3 (fixed-plan: `production_plan/solar_vs_nuclear_render.select_and_download_stock`) — legacy-only, оба ходят в Pexels/Pixabay **голым `requests.get` в обход `require_network`** и достижимы с дефолтной команды `python pipeline.py`. Это главный операционный риск аудита (см. §6.1): default-deny сети, заявленный `runtime_network.py:35-41`, на legacy-путях не действует.
3. **Главный источник путаницы агентов — не код, а документы.** Корневые `README.md` и `COMMANDS.md` (оба CS 9) описывают систему до-июньского образца и ни разу не упоминают канонический CLI; `docs/project_map_and_app_split_plan.md` называет себя «актуальной картой»; восемь `PROJECT_AUDIT_*.md` лежат без status-frontmatter. При этом `docs/current/SYSTEM_MAP.md` точен (5/5 проверенных утверждений).
4. **CLEANUP_REGISTRY в основном верен, но устарел в трёх местах после PLAN-9C** (semantic-сервис уже влияет на отбор; `select_candidate_after_review` больше не вызывается вовсе; line-refs сместились) и имеет три пробела (стек 3 не заведён как retrieval-путь; сетевой обход стеков 2/3 не записан; `unsplash_provider.py` как файл).
5. **Конфиги содержат «ложные пульты управления»:** `technical_score_weights`/`rerank_weights`/`refresh_policy` в `visual_preview.json` не читает ни одна строка кода; retrieval-блоки `video_style.json` мертвы кроме `enabled`; в `semantic_visual.json` двойной cap и двойной бюджет (top-level vs `openai.*`). Обе схемы `schemas/*.json` — не enforcement и отстают от кода.
6. Итоговые счётчики классификации (164 позиции в JSON): **A = 63 · B = 38 · C = 4 · D = 13 · E = 7 · F = 39 · G = 0.** Удалять почти нечего — и это нормальный итог: основная чистка это (а) баннеры/индексация docs, (б) retirement legacy-стеков по уже существующим механизмам, (в) дельта реестра.
7. Архитектурный вердикт по шкале задания: **B — «в основном централизован, есть несколько legacy seams»** для canonical-ядра; **C — «заметно раздвоен (фактически растроен)»** для репозитория в целом за счёт legacy-стеков, у которых уже есть дома в реестре (C08/C12/C17) и plan (PLAN-L).

---

## 2. REPO STATE (baseline)

- `git status`: worktree чист, кроме одного pre-existing untracked файла `docs/audits/AI_DEVELOPMENT_SYSTEM_AUDIT_2026-08-12.md` (создан другой сессией до аудита; не трогался).
- `git log -3`: `f3b607a` (M1-D resume fingerprint) · `0f424f9` (EXP-001 evidence) · `79c604d` (RD-A corrections).
- Retirement-теги: `retired/query-paths-2026-08-07` (единственный), bundle в `G:\Projects\AI-YouTube_retirement_bundles\query-paths-2026-08-07.bundle`.
- Контекст плана: checkpoint **PLAN-9D** (под-слайсы A–E закрыты, F/G — optional paid-Vision track, PLAN-9D маршрут больше не блокирует); **следующее действие — M1-E / VA-NEW-09** (strict render TOCTOU, PLAN-9E); Review #2 (M1-D+M1-E) не выполнен.
- Продуктовый контекст качества отбора (PLAN-9D-E, 2026-08-12): metadata-only решение совпадает с owner-разметкой **4/14**; 2 выбора вычеркнутого владельцем; 3 ложных abstention; `auto_safe` 1/14.

**ПОДТВЕРЖДЕНИЕ: NO CHANGES / NO COMMIT / NO PUSH.** Единственные записанные файлы — этот отчёт и его JSON, оба вне репозитория.

---

## 3. CURRENT PRODUCTION FLOW (canonical, проверено по коду)

```
python -m ai_youtube
  ai_youtube/__main__.py → src/ai_youtube/cli/main.py:114 main()
    ↓ create|resume            src/ai_youtube/cli/commands/create.py:14
    ↓ service + NETWORK SCOPE  src/content_creation/service.py:146 create_content
    │                          network_approval_scope(...)  service.py:166-171
    ↓ use case                 apps/content_creator/workflows/fullscreen_voiceover/use_case.py:69
    ↓ stage loop + resume      src/news/pipeline.py:297 run_news_to_short_job
    │                          M1-D reuse-гейт: _asset_search_reuse_block :147, fingerprint :113
    ↓ visual_plan              src/news/visual_plan.py:33 → content/visual_planning/engine.py:62
    │                          planner: DeterministicVisualPlanner (единственный)
    │                          briefs: brief.py:220 produce_brief (+semantic_brief adapter, выключен config)
    │                          строки: expansion.py:196 expand_queries → legacy_format.py:214 (shape adapter)
    ↓ asset_search             src/news/pipeline.py:791 build_asset_search_manifest
    │                          → asset_manager.py:109 (compatibility-фасад)
    │                          → AssetManifestBuilder.build  asset_manifest_builder.py:264
    │   per scene:
    │     analyze_scene :346 → route_providers :348 (scene_strategy.PROVIDER_PRIORITY)
    │     build_scene_queries :355 (query_adapter.py:270; translation_required ⇒ не отправляется)
    │     rank_user_assets :366 / rank_local_assets :373 (media_library.search_local_assets)
    │     _search_scene_providers :394 → search_provider (asset_provider_adapters.py:79)
    │        → providers/registry.py:56 (wikimedia+nasa+IA всегда; pexels/pixabay при ключе)
    │        → http_client.get_json :49 [require_network(provider_search) :58]
    │     rights: license_policy.apply_policy_to_candidate :275 (до download, fail-closed)
    │     selection: select_best_with_video :1288 → media_policy.select_with_media_policy :114
    │        → candidate_ranker.rank_candidates :140 / select_best_candidate :182
    │     preview/review: visual_preview.py:343 (preview key v2 :224) → review_bundle.py:55
    │        (after_id = before_id :648 — post-review селектора в production НЕТ)
    │     semantic evidence (выключен config): _apply_semantic_visual_evidence :692 — ДО download
    │     download: ensure_selected_asset_downloaded (adapters :238) → download.py:22
    │        → http_client.download_stream :68 [require_network(asset_download) :79]
    │     ladder (только draft_complete): asset_scene_completion.py:77 → assets/completion/**
    ↓ манифест                 asset_manifest_builder._final_manifest :1190 → assets_manifest.json
    │                          + asset_search_fingerprint (pipeline.py:226-232)
    ↓ потребители              preview_render :683 · quality_check :702 · final_render :728 · export :776
```

Production-дефолт: отбор **чисто метаданный** (Vision/semantic-brief/technical-rerank/user-assets выключены двойными гейтами или не подключены к canonical CLI).

---

## 4. CANONICAL OWNERS

| Ответственность | Owner | Entry symbol | Evidence |
|---|---|---|---|
| CLI | `src/ai_youtube/cli/main.py` | `main` | `ai_youtube/__main__.py:1-4` |
| Создание + network scope | `src/content_creation/service.py` | `create_content:146` | `create.py:27-29`; scope `:166-171` |
| Стадии/resume/fingerprint | `src/news/pipeline.py` | `run_news_to_short_job:297` | M1-D блок `:147,:113,:604` |
| Вход asset_search | `src/news/pipeline.py` | `build_asset_search_manifest:791` | `pipeline.py:578,586` |
| Оркестратор сцены | `src/news/asset_manifest_builder.py` | `AssetManifestBuilder.build:264` | ← `asset_manager.py:87` (фасад) |
| Visual plan | `content/visual_planning/engine.py` | `build_plan:62` | ← `news/visual_plan.py:33` |
| Query boundary (C39) | `src/assets/query_adapter.py` | `build_scene_queries:270` | `asset_manifest_builder.py:355` |
| Slot-queries (ladder) | `src/assets/query_adapter.py` | `build_slot_queries:348` | `asset_scene_completion.py:323` |
| Состав провайдеров | `src/providers/registry.py` | `create_default_stock_providers:56` | ← `asset_provider_adapters.py:55` |
| Порядок/source_class | `src/assets/scene_strategy.py` | `build_strategy` (+фасад `provider_routing.py:33`) | `asset_manifest_builder.py:348` |
| Вызов search + glue | `src/news/asset_provider_adapters.py` | `search_provider:79` | `asset_manifest_builder.py:464` |
| Rights | `src/assets/license_policy.py` (+`models.py:38`) | `apply_policy_to_candidate:275` | adapters `:171,:226` |
| Decision (media-вид + выбор) | `semantic_selection/media_policy.py` | `select_with_media_policy:114` | обёртка `:1288`, вызовы `:574,:590,:807` |
| Ranking | `semantic_selection/candidate_ranker.py` | `rank_candidates:140` / `select_best_candidate:182` | `media_policy.py:130` |
| Evidence/vision_tags | `semantic_selection/evidence.py` | `bind_vision_tags:322` | ranker `:222`; builder `:791` |
| Preview + identity v2 | `src/assets/visual_preview.py` | `compute_preview_cache_key:224` | builder `:629` |
| Review bundle | `src/assets/review_bundle.py` | `create_scene_review_bundle:55` | builder `:649,:1134` |
| Vision boundary | `src/assets/semantic_visual_service.py` | `analyse_semantic_visual_for_shortlist:251` | builder `:747` (до отбора) |
| Download | `adapters:238` → `src/assets/download.py:22` → `http_client.py:68` | — | retry: сеть ×3 в http_client; кандидаты ×3 в adapters |
| Network approval | `src/runtime_network.py` | `NETWORK_ACTIONS` (6 классов) | enforcement: http_client `:58,:79`, visual_preview `:539`, semantic_brief `:231` |
| Completion ladder | `src/assets/completion/**` | `build_scene_assembly` | `asset_scene_completion.py:180` |
| Локальная библиотека | `src/media_library.py` | `search_local_assets` | builder `:1516` (живой; НЕ legacy) |

---

## 5. ТРИ RETRIEVAL-СТЕКА (центральная структурная находка)

| Стек | Вход | Ядро | Сетевой гейт | Статус |
|---|---|---|---|---|
| 1. Canonical | `python -m ai_youtube` | `src/assets/**` + `src/providers/registry` + `asset_manifest_builder` + `media_library` | `require_network` всюду | active |
| 2. Legacy documentary | `python pipeline.py` (default-ветка `:104`), `apps/youtube_pipeline` | `asset_finder.py` → `video_asset_engine.py` (+`music_engine`) | **НЕТ** — голый `requests.get` (`asset_finder.py:109,134`; `video_asset_engine.py:408,445,595`) | legacy-only |
| 3. Fixed-plan (solar) | `pipeline.py` / `maintenance.py:403` | `production_plan/solar_vs_nuclear_render.py`: свой `select_and_download_stock:152`, свой `_download_file:175`, прямые `pexels_provider.search_videos:350` / `pixabay:372` (module-level legacy-функции, тоже raw `requests`) | **НЕТ** | legacy-only |

Мосты legacy→canonical всего три: `media_library.py`, `utils.py`, `src/providers/*`. Канальный гейт формально закрывает legacy-каналы от canonical CLI (`capabilities.py:244,256`, `test_documentary_migration_gate.py:42-62`).

### 5.1 Дубли/затенённые реализации (old vs new)

| Old | New (canonical) | Caller old | Вердикт |
|---|---|---|---|
| `asset_finder.py` поиск+download | adapters+registry+download | `pipeline.py:10` | D, ретайр по C08/PLAN-L; до ретайра — сетевой гейт (§6.1) |
| `video_asset_engine.py` (749 LOC, свой `build_query_variants:225`, свой ranker `score_survival_relevance`) | expansion.py + candidate_ranker | `asset_finder.py:13` | D; знание уже спасено (C46/C48 → expansion.py) |
| `solar_vs_nuclear_render.select_and_download_stock` | builder+adapters | `pipeline.py:44`, `maintenance.py:403` | D; **в реестре не заведён — новый кандидат** |
| module-level `search_videos/search_images/search_music` в `pexels/pixabay_provider.py:188-214` (raw requests) | методы классов через `ProviderHttpClient` | только стек 3 | D; ретайрить вместе со стеком 3 |
| 6 legacy-экспортов `providers/__init__.py:50-57` | — | 0 callers | E |
| `unsplash_provider.py` (голая функция, не StockProvider) | — | 0 callers; имя в 5 таблицах данных | E; якорь: PLAN-10B «осиротевшее имя» |
| `review_bundle.select_candidate_after_review:199` (второй селектор, веса захардкожены `:274`) | Vision-переотбор `:806-819` | только тесты; production жёстко `after_id = before_id` `:645-648` | D (superseded); ретайр = код+тесты+мёртвые config-ключи одним слайсом |
| `semantic_decision_policy.py` (калибровка порогов) | пороги живут в `semantic_visual.json`+ranker | 0 production callers; свой тест | C/E — owner decision (§10) |
| `vision_validator.py` (13-строчная заглушка) | реальный Vision-путь через `semantic_visual_service`+`vision_tags` | 0 callers, 0 owning tests, не менялся с foundation-коммита | E; вместе с мёртвым ключом канала `vision_validation_enabled` |
| Протокол `AssetProvider` (`asset_provider_adapters.py:30`, deprecated) | `provider_contract.StockProvider:166` | никто не реализует; fallback-ветка `:134-136` недостижима | E (внутри живого файла — opportunistic) |
| `asset_manager.py` 4 обёртки (`_select_best_candidate:150` и др.) | builder импортирует напрямую | только патч-точки тестов | B (facade; exit: перенос патч-точек) |
| `provider_routing.DEFAULT_PROVIDER_ORDER:22` | явные `provider_names` всегда передаются | мёртвая ветка | E; уже записан планом как vestigial (PLAN-10B opportunistic) |
| `config_resolver.resolve_config` | фактические читатели конфигов | 0 production-вызовов; parity-тест D1; self-claim о потребителе ложен (`resolver.py:25-26`) | B (shadow по контракту D1; не удалять без решения по D1) |

---

## 6. ГЛАВНЫЕ РИСКОВЫЕ НАХОДКИ

### 6.1 Обход default-deny сети в legacy-стеках (приоритет №1)
`runtime_network.py:35-41` заявляет default-deny для всей сети, но стеки 2/3 ходят в Pexels/Pixabay без `require_network`: поиск и стриминговое скачивание `asset_finder.py:109,134,151`, `video_asset_engine.py:408,445,595`, `solar_vs_nuclear_render.py:350,372` + `_download_file:175`. Достижимо: `python pipeline.py` (дефолтная ветка `main()` `:104` → `workflow.py:182 build_asset_plan`), при наличии ключей в env и `video_style.json.pexels_search.enabled: true` (текущий default). Предложение: bounded correction «legacy network gate» (обернуть ~6 call-sites в `require_network`) ДО физического ретайра стеков; кандидат на новый VA-NEW номер; owner decision обязателен.

### 6.2 Vision-egress без сетевого класса (записать, не чинить)
`semantic_visual_openai.py` не импортирует `runtime_network`; гейты — только платёжные (`VisionBudgetGuard`). Разделение «оплата ≠ сеть» задокументировано в `runtime_network.py:18-21` как намеренное. Фиксация факта для будущего PLAN-9E/9D-F.

### 6.3 Канонический CLI: две «пустые» точки
- `assets replace` — заглушка: `cli/commands/assets.py:7-8` `register_commands = pass`; обработчик есть, сабкоманда не регистрируется. Замена слота доступна только через compatibility CLI. Документация (`AGENTS.md`, `COMMANDS.md`, skill `replace-visual-slot`) обещает команду. Якорь: M3 («user assets в create», C63-семейство).
- `run-stage` (`authoring.py:19-30`) вызывает `run_news_to_short_job` вне `network_approval_scope` — fail-closed, но с невнятной диагностикой (смежно с follow-up PLAN-10A «denial ≠ provider error», `asset_manifest_builder.py:476`).

---

## 7. CONFIG / JSON FINDINGS

| Файл | Класс/CS | Вердикт |
|---|---|---|
| `config/license_policy.json` | A/2 | Единственный источник rights, fail-closed. Находка: production-правило для провайдера `fake` (`:35-44`) — тестовый двойник в боевой политике |
| `config/semantic_brief.json` | A/1 | Полностью живой, выключен by design, каждое поле блокирует отдельно |
| `config/semantic_visual.json` | B/6 | Двойной cap кандидатов/кадров (top-level 5/5 vs `openai.*` 3/3 — сервис строит по одному, backend валидирует по другому → `maximum_candidates_per_scene_exceeded`); двойной бюджет; `mode` report-only; `request/result_version` перекрыты константами |
| `config/visual_preview.json` | B/8 | **Мёртвые ключи**: `technical_score_weights` (7), `rerank_weights` (5), `refresh_policy`, часть `similarity_thresholds` — 0 читателей; реальные веса захардкожены (`visual_metrics.py:274-280`, `review_bundle.py:274`). Ложное впечатление настраиваемости |
| `config/video_style.json` (retrieval-блоки) | B/9 | Читается только `enabled`; `orientation:"landscape"` (противоречит продуктовому 9:16), `per_page`, `max_downloads`, `queries` — мертвы, захардкожены в `asset_finder.py:107,126` |
| `config/semantic_visual_eval.json` | B/3 | Живой датасет eval-инструментария (вне production-пути) |
| `schemas/assets.schema.json` | F/7 | Не enforcement (читает только `tests/test_artifact_schemas.py`); не знает 5 реально пишущихся ключей, вкл. `asset_search_fingerprint`; спасает лишь `additionalProperties:true` |
| `schemas/evidence.schema.json` | F/7 | Отстаёт от `EVIDENCE_RECORD_SCHEMA_VERSION=2` на 15 полей |
| `config/system/paths.json` | — | Файла нет; `DEFAULT_PATHS_CONFIG` всегда падает в дефолты (легитимный optional override) |
| `outputs/*.json` (9 tracked) | E/6 | Сгенерированные артефакты legacy-прогонов закоммичены (вход/выход перепутаны); цепочка PLAN-14 disposable |
| `docs/implementation/openai_live_evaluation/LIVE_EVAL_DATASET.json` | B/8 | **Production-код читает файл из docs/** (`evaluation_tooling.py:25-27`) — известный C31, физический перенос = PLAN-13. НЕ трогать |
| `assets/library/metadata/media_index.json` | A/3 | Живой локальный индекс (untracked; в git только `.example`) |
| Резолверы | B/5 | `config_loader.py` — canonical для legacy `video_style`; `config_resolver.resolve_config` — shadow с 0 production-вызовов; retrieval-ключи в резолвер не заведены; `keys.py` min/max duration и fps — `no_consumer_yet` |
| `channels/**` | A/3 | `asset_selection` только у `nature_science_news_ru` и дублирует дефолт байт-в-байт; ключ `vision_validation_enabled` — **без потребителя** (реальный гейт: `semantic_visual.enabled && semantic_rerank_enabled`, builder `:723-729`); два формата (`channel_config.json` vs `channel.json` у nature_pulse) — известный STAB-кандидат |
| `pyproject.toml` | — | mypy `ignore_errors` накрывает ~19 модулей `src/assets` + 9 `src/news` (почти весь retrieval); ratchet-правило действует |

Прочее: путь к `license_policy.json` резолвится двумя способами (canonical `repository_path` vs `_REPOSITORY_ROOT` в `completion/replacement.py:79,654`, игнорирующий `AI_YOUTUBE_PATHS_CONFIG`).

---

## 8. DOC / MD FINDINGS

Точные (CURRENT CANONICAL): `SYSTEM_MAP.md` (CS 1; лишь frontmatter отстаёт), `docs/implementation/README.md` (лучший guard-документ), `docs/archive/README.md`.

**Топ-опасные для агентов:**

| Документ | CS | Проблема |
|---|---|---|
| `COMMANDS.md` (корень) | 9 | 681 строка команд; 0 упоминаний `python -m ai_youtube`; 49× compatibility CLI + 24× `pipeline.py`; всё ещё исполняется → staleness невидим |
| `README.md` (корень) | 9 | Описывает quote-pipeline мая-2026; ни retrieval, ни providers, ни news_to_short |
| `docs/project_map_and_app_split_plan.md` | 8 | Сам себя называет «Актуальная карта» (`:450`); `asset_finder`/`video_asset_engine` как действующая asset-система |
| `docs/handoff/PROJECT_RESCUE_MASTER_PLAN.md` | 8 | Без historical-баннера, маршрутизируется из `AGENTS.md`; заявляет checkpoint `9B-C01`, отменённый SYSTEM_MAP `:225`. По плану не архивируется до PLAN-12C — нужен именно баннер |
| `docs/contracts/STAGE1_PUBLIC_CONTRACTS.md` | 8 | C22: единственный файл в `contracts/`, называет compatibility CLI «current» |
| `docs/audits/PROJECT_AUDIT_*.md` (8 шт.) | 7 | Без status-frontmatter; `asset_finder`/`make_stock_query`/`query_generator` показаны живыми; в `PROJECT_AUDIT_ARCHITECTURE.md:436` — ссылка на несуществующий `stock_video_downloader.py` |
| `docs/apps/news_to_short.md` | 7 | Все команды — retired-tier entrypoints; исполняются → staleness невидим |
| `docs/implementation/visual_retrieval_repair/VISUAL_RETRIEVAL_MAP.md` | 7 | Самый полезный retrieval-документ (85% точен) — и потому самый опасный: не знает `media_policy`, утверждает «платный Vision не подключён» (устарело с PLAN-9C), учит неканоническому CLI |
| `docs/apps/youtube_pipeline.md` | 6 | `asset_finder` как «рабочий режим» |
| `docs/implementation/config_resolver/CONFIG_MAP.md` | 6 | Перечисляет удалённый `stock_video_downloader.py` как читателя ключа |
| `docs/archive/handoff/CLI_CHEATSHEET.md` | 6 | «Команды основаны на **текущем** pipeline.py» внутри архива |
| `docs/cleanup_report.md` | 4 | Снапшот «что используется», superseded реестром |

Структурные: `docs/audits/` не имеет README/индекса; `ARCHITECTURE_BOUNDARY_MAP.md` противоречит сам себе про `stock_video_downloader` (`:183` «сохранён» vs `:185` «удалён») и отстаёт по числам; три archive-баннера указывают на до-переносный путь `docs/handoff/…` (битые ссылки). Doc-дубли D1–D6: шесть пар документов рассказывают о retrieval разные истории (полный список в отчёте субагента, ключевые — в §8 выше).

---

## 9. TEST FINDINGS

- Инвентарь: 53 retrieval-модуля/~1015 тестов; классификация [gov] уже встроена в `tools/qa/check_agent_docs.py:402-411`.
- **`tests/test_asset_cli_wiring.py` (CS 9)** — вся поверхность 9 subprocess-вызовов = ретайримый `pipeline.py`; canonical CLI этих команд не имеет; участник C49 (network guard не наследуется subprocess). Не классифицирован в gov-списке.
- **Противоречие классификаций:** gov-метки называют `test_legacy_pipeline_application_boundary/internals_contract` LEGACY ANCHOR, реестр (`:1033`) — CHARACTERIZATION с вердиктом ARCHIVE ONLY. Разрешить одной строкой в cleanup-слайсе.
- **Висячий frozen-путь:** `tests/data/plan9d/corpus_v1.json` не существует, но путь заморожен константой `plan9d_corpus_builder.py:110` и assert'ом `test_plan9d_historical_evidence.py:97` — тест зелёный на несуществующий файл.
- `test_apps_structure.py:34` замораживает существование `pipeline.py` (`Path("pipeline.py").is_file()`) — прямой якорь против PLAN-L4.
- Ноль тестов: `unsplash_provider`, `music_finder`, legacy `build_query_variants` (знание уже спасено C46).
- Fixture-файлов вне plan9d нет (все инлайновые); `conftest.py` отсутствует; legacy-fixtures живут в `content/survival/*.json` (N04).
- Пробелы (не чинились): smoke `python -m ai_youtube create` (G1), E2E LLM→TTS→MP4 (G2), idempotency `stage=` (C43a), C49 (12 subprocess-модулей).
- plan9d harness: `plan9d_ground_truth.py` (A), `plan9d_retrieval_gate.py` (A/B), `plan9d_corpus_builder.py`/`plan9d_current_capture.py` (B, ручные инструменты PLAN-9D-F/G). Не трогать.

---

## 10. FUTURE-USEFUL ORPHANS (класс C) — с привязкой к PLAN

| Файл/знание | Что делает | Почему не live | PLAN-якорь (существующий) | Рекомендация |
|---|---|---|---|---|
| `src/providers/local_library_provider.py` | Полный StockProvider локальной библиотеки | Не конструируется в registry (задумано); объявлен первым в каждом `PROVIDER_PRIORITY`, всегда отфильтровывается | **PLAN-10D** (там же открытый вопрос о регистрации) | Держать как есть до PLAN-10D |
| `src/assets/temporal_video_analysis.py` | Внутриклиповая изменчивость: hash-дистанции, per-position crop, contact-sheet | 0 production callers; owning test есть | **M5 / longform** | Добавить explicit item в M5: «reuse temporal_video_analysis как основу segment-выбора» |
| `src/assets/semantic_decision_policy.py` | Калибровка порогов suitable/review/unsuitable + pairwise ranking | 0 production callers; owning test есть | PLAN-9E / PLAN-10C (калибровка порогов) | **Owner decision**: либо explicit item к PLAN-9E/10C, либо ретайр. Не удалять молча |
| `tests/path_identity.py` | Windows 8.3/case нормализация путей | 2 потребителя из 60+ path-тестов | — | Оставить; асимметрию отметить |
| Знание `min_local_diversity_per_scene` / `reserved_download_slots` | Diversity reserve из legacy | — | **PLAN-10D п.3** (уже записано) | Ничего не делать — уже в плане |
| Незадействованные выходы `visual_metrics`/`perceptual_similarity` (B7/B8) | Пиксельные метрики качества и crop-suitability считаются на каждом preview и никуда не идут | Потребителя в отборе нет | **RD-C / PLAN-10C** | Explicit item: «подключить существующие pixel-метрики к decision/threshold работе, не писать новые» |
| `EnvatoManualProvider` + флаг `envato_manual_fallback_enabled` | Ручной премиум-путь | Выключен, в канале не включён | **ENVATO-CS1** | Уже есть кандидат-слайс |

## 11. QUALITY-AWARE RETRIEVAL — что уже существует

**Живое:** размеры кандидата (`models.py:214`), min-размеры двумя слоями (provider-фильтр `provider_contract.py:62` 720/1280→1080; ranking-гейт `MIN_SHORT_EDGE_PX=540` + `framing_decision`), orientation (в API и на кандидате), **crop viability + effективное разрешение после кропа + upscale factor** (`decision.py:666-745`, hard reject), quality/vertical score по метаданным (ranker `:623-643`, adapters `:557-568`; вес 0.075 в final_score), дубликаты (perceptual hash cross-candidate + in-clip frozen/repeat), duration-гейт (`_duration_check`, tolerance 0.35s, hint slow_down_or_loop), multi-slot (`completion/assembly.py`, `MAX_SLOTS_PER_SCENE`).

**Producer есть — consumer нет (главный разрыв):** пиксельные `estimate_crop_suitability` и `_score_frame` (brightness/contrast/sharpness/detail/activity) считаются на каждом preview (`visual_preview.py:380,402`) и не влияют ни на один выбор; конфиг-веса к ним мертвы (§7).

**Отсутствует полностью:** bitrate видео (ffprobe его не извлекает), fps источника как retrieval-сигнал, aesthetic score. Полуготовых старых реализаций этого нет — писать придётся с нуля (дом: RD-C/PLAN-10C после baseline).

## 12. LONG-FORM / SEGMENT — что уже существует

Есть живое: покадровый seek `-ss` (`frame_sampling.py:67`), caps `-t` (preview `:687`, render `:394`), slot-окна на таймлайне сцены (`start/end_offset_sec` + `scaled_slot_windows` → renderer `:312-333`), выбор rendition у провайдеров (nasa `_select_rendition`, pexels `_best_video_file`, pixabay renditions), ffprobe-инфо (`frame_sampling.py:88`). Припарковано: `temporal_video_analysis.py` (готовый детектор «какой отрезок клипа живой»). **Отсутствует ровно одно звено: источниковый временной диапазон** — в модели кандидата нет `clip_start/clip_end`, а `final_renderer._render_video_segment:375-406` всегда рендерит с t=0 источника (`-stream_loop`), никогда `-ss` по source. Рабочий образец сегментного извлечения существует только в `anime_factory` (protected C07; факт, не классификация). EXP-001 подтвердил ценность: LONG_FORM-стратегия дала единственный FULL-материал, Vision умеет находить сегмент. Дом: **M5**, с explicit item «source clip range в candidate model + `-ss` в render path».

---

## 13. ДЕЛЬТА К CLEANUP_REGISTRY

**Подтверждено без изменений:** C17 (`legacy/` — 0 callers, как записано), C22, C36–C38 (retired, guard-тесты на месте), C07/C08/C12 рамки, C31 (LIVE_EVAL_DATASET читается из docs), C40 (три consumer'а `media_index`), C41 (local_library mismatch), C46/C48 (знание в expansion.py), C49, C50 (fail-open на review_required — не трогался), C63.

**Устарело (нужна правка строк):**
1. C01-SEM: «`semantic_visual_service` вызывается после отбора и на выбор не влияет» — **неверно с PLAN-9C** (`_apply_semantic_visual_evidence:692` до выбора, переспрашивает селектор `:806-819`).
2. C01-SEM: «единственный, кто может изменить выбранного — `select_candidate_after_review` при `technical_rerank_enabled`» — **функция больше не вызывается вовсе** (`after_id = before_id :645-648`); реальный изменитель — Vision-переотбор.
3. Line-refs C01-SEM сместились (`:260`→`:290`, `_write_reviews:959`→`:1145`).

**Новые кандидаты в реестр (предлагаемые строки):**
| ID (предл.) | Что | Класс | Действие |
|---|---|---|---|
| C64 | Стек 3: `solar_vs_nuclear_render.select_and_download_stock` + module-level `search_*` в providers | D | retire вместе с C08-семейством; до того — network gate |
| C65 | Сетевой обход стеков 2/3 (6 call-sites без `require_network`) | правка | bounded correction «legacy network gate» (VA-NEW-кандидат) |
| C66 | `src/providers/unsplash_provider.py` + 6 legacy-экспортов `__init__` | E | retirement package «retrieval-orphans» |
| C67 | `vision_validator.py` (заглушка) + мёртвый ключ `vision_validation_enabled` | E | retire (owner decision из-за channel-ключа) |
| C68 | `select_candidate_after_review` + `compute_repetition_penalties` + мёртвые config-веса | D | retire одним слайсом (код+тесты+ключи) |
| C69 | Мёртвые config-ключи `visual_preview.json`/`video_style.json`/двойные caps `semantic_visual.json` | правка | config hygiene slice |
| C70 | `schemas/*.json` не-enforcement и отстают | F | решение: догнать поля или пометить характеризационными |
| C71 | `outputs/*.json` tracked-артефакты | E | PLAN-14 disposable chain |
| C72 | Правило `fake` в `license_policy.json` | правка | вынести в test-конфиг |
| C73 | Висячий `SUPERSEDED_CORPUS_PATH` (plan9d corpus_v1) | правка | одна строка + тест |
| C74 | Противоречие классификаций тестов gov vs registry | правка | синхронизировать |
| C75 | `semantic_decision_policy.py` парковка | C/E | owner decision (PLAN-9E/10C или retire) |

---

## 14. CLEANUP / QUARANTINE CANDIDATES (для следующего слайса; сейчас НИЧЕГО не перемещено)

```
RETIREMENT PACKAGES (механизм: annotated tag + git bundle → AI-YouTube_retirement_bundles + строка Retired)
├── PKG-1 «retrieval-orphans» (низкий риск, маленький blast radius)
│   ├── src/providers/unsplash_provider.py            (E, 0 callers, 0 tests; имя в таблицах — PLAN-10B)
│   ├── providers/__init__.py: 6 legacy-экспортов     (E, 0 callers)
│   ├── vision_validator.py + ключ vision_validation_enabled  (E; owner decision)
│   └── review_bundle.select_candidate_after_review + тесты + мёртвые веса конфига (D)
├── PKG-2 «legacy-stack retirement» (большой; ПОСЛЕ M1-E+Review #2; по PLAN-L gates)
│   ├── стек 2: asset_finder.py, video_asset_engine.py, scene_planner.py, quote_generator.py,
│   │   self_eval.py, size_comparison_engine.py, intro_generator.py, obsidian_exporter.py,
│   │   music_finder.py, music_engine.py                (D/E, якоря C08/C12)
│   ├── стек 3: solar_vs_nuclear_render retrieval-часть + module-level search_* (D, новый C64)
│   ├── их тесты: test_documentary_visual_engine, test_asset_cli_wiring, test_apps_structure:34
│   │   (по test-classification плана; противоречие C74 разрешить)
│   └── ПРЕДУСЛОВИЕ: network gate (C65) или одновременный ретайр
├── PKG-3 «config hygiene» (мелкий)
│   ├── visual_preview.json: technical_score_weights, rerank_weights, refresh_policy
│   ├── video_style.json: мёртвые retrieval-ключи (orientation/per_page/max_downloads/queries)
│   ├── semantic_visual.json: двойной cap/бюджет — свести к одному источнику
│   ├── license_policy.json: правило fake → в тестовый конфиг
│   └── plan9d SUPERSEDED_CORPUS_PATH: одна строка
└── PKG-4 «docs guard» (docs-only, можно немедленно)
    ├── status-frontmatter/баннер: README.md*, COMMANDS.md*, project_map_and_app_split_plan.md,
    │   PROJECT_RESCUE_MASTER_PLAN.md (баннер, не архив — PLAN-12C), PROJECT_AUDIT_*.md (8),
    │   news_to_short.md, youtube_pipeline.md, VISUAL_RETRIEVAL_MAP.md, CLI_CHEATSHEET.md,
    │   STAGE1_PUBLIC_CONTRACTS.md (C22 → PLAN-12E)
    ├── README-индекс в docs/audits/
    ├── фикс самопротиворечия ARCHITECTURE_BOUNDARY_MAP :183/:185 + битых archive-ссылок
    └── дельта CLEANUP_REGISTRY (§13: правки C01-SEM + новые строки)
    * README/COMMANDS: минимум — баннер + ссылка на canonical CLI; переписывание — отдельное решение
```

## 15. DO NOT TOUCH (выглядят старыми/лишними — реально нужны)

`src/media_library.py` (5 живых canonical-callers) · `src/utils.py` (корневой path-якорь canonical-кода) · трио `semantic_visual_evaluation*` (живой CLI-инструментарий с e2e-тестом) · `semantic_visual_external.py` (fail-closed граница) · `semantic_visual_mock.py` (default backend без права переотбора) · `fake_provider.py` (тестовая инфраструктура) · frozen `tests/data/plan9d/*` · plan9d harness (4 файла) · `LIVE_EVAL_DATASET.json` в docs (production читает; перенос = PLAN-13) · `content/survival/*.json` (fixtures N04) · `anime_factory/**` (C07, migration source; единственный образец `-ss/-t` сегментов) · `_LEGACY_BROAD_QUERIES` guard в query_adapter (persisted-compatibility) · legacy_pipeline compatibility surface до PLAN-L gates · `media_index.json` (runtime) · `docs/audits/*` как evidence (не удалять, индексировать).

## 16. PLAN GAP ANALYSIS

**Уже отражено в плане (не дублировать):** pagination/exhaustion (PLAN-10B), retry R² и partial mixed-media (M2-A), budget+эскалация (PLAN-10C, VA-NEW-12), local library (PLAN-10D: mismatch, duplicate_penalty, diversity reserve, C50-gate), attempt ledger + denial≠error (PLAN-10A), Vision activation/режимы (PLAN-9E), Vision benchmark (9D-F/G), user assets + replace-slot в canonical CLI (M3/C63), Envato (CS1–3), longform (M5), RD-B/RD-C (proposal, EXP-001 даёт готовые входы: короткий query для Commons, mime `.ogv`, `filetype:video`, глубина, кавычки IA).

**Потеряно/не имеет строки (добавить):** §13 «новые кандидаты» C64–C75; плюс явные items: M5 ← «source clip range + temporal_video_analysis reuse»; RD-C/10C ← «подключить существующие pixel-метрики»; PLAN-9E/10C ← решение по `semantic_decision_policy.py`.

**Где план мог бы породить дубль (предупреждение):** RD-B — только улучшение существующей expansion ladder (уже записано); provider-registry convergence — гипотеза опровергнута D-2, пять реестров легитимны (девятый инвентарь в `provider_diagnostics._provider_specs` — кандидат на сведение при касании routing); Vision — только через `semantic_visual_service`, не воскрешать `vision_validator`.

## 17. RECOMMENDED PACKAGES (порядок)

1. **AUD-DELTA (docs-only, можно сразу):** PKG-4 + дельта реестра §13. Не мешает M1-E/Review #2.
2. **M1-E / VA-NEW-09 + Review #2** — по плану, вне этого аудита.
3. **CL-NET (bounded correction, после Review #2, owner decision):** network gate для стеков 2/3 (C65) — либо совместить с PKG-2, если ретайр будет быстрым.
4. **CL-RETIRE-1:** PKG-1 «retrieval-orphans» + PKG-3 config hygiene (маленькие diff'ы, отдельные commits).
5. **CL-RETIRE-2:** PKG-2 legacy-стеки по PLAN-L gates (KSG уже частично пройден: C46/C48 спасены; остатки — по Knowledge Salvage checklist).
6. **Дальше по плану:** M2-A (PLAN-10B, включая EXP-001 фиксы Wikimedia/IA как часть provider contract) → PLAN-10C (+pixel-метрики item) → PLAN-10D → M3 → M5.

## 18. EXACT NEXT ACTION

Передать этот отчёт на gap-review (Gemini) и adversarial-проверку таблицы D/E; после approve владельца — выполнить **AUD-DELTA** (docs-only слайс: баннеры + индекс docs/audits + правки реестра §13) отдельным commit, не трогая checkpoint; M1-E остаётся следующим действием плана и этим аудитом не меняется.

## 19. REPO STATE ПОСЛЕ АУДИТА

HEAD `f3b607a` = origin/governance-reset; worktree — без изменений (тот же один pre-existing untracked файл); **NO CHANGES · NO COMMIT · NO PUSH**. Выход аудита — два файла в `G:\Projects\AI-YouTube_Architecture_Audit\`.
