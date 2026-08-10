---
status: audit
audit_date: 2026-08-10
audit_head: 19d2c9489fce6d6b20fe5225229675e5414dbbeb
working_branch: governance-reset
scope: >
  Полный сравнительный read-only аудит старого и нового функционала VISUAL ASSET
  PIPELINE (поиск, оценка, выбор, скачивание, использование изображений/видео);
  проектирование единой IMAGE/VIDEO/MIXED media-selection policy вместо жёсткого
  prefer_video; сверка документации и планов; salvage/retire карта.
method: >
  Чтение кода на HEAD, read-only Git history, offline-пробы функциями самого
  репозитория на артефактах LIVE-3/LIVE-4 (без сети и записи), три параллельных
  read-only sweep'а (legacy-движки, provider-слой, тесты) и полная сверка
  docs/current, docs/architecture, docs/contracts, docs/apps, docs/adr,
  docs/audits, docs/implementation, docs/handoff. Дополнительно выполнена
  сверка с независимым внешним аудитом (Codex, 2026-08-10) и слияние лучших
  выводов обоих; расхождения указаны в §55.
changes_to_repository: только этот файл
commit_created: no
---

# СРАВНИТЕЛЬНЫЙ АУДИТ VISUAL ASSET PIPELINE: СТАРОЕ vs НОВОЕ, ЕДИНАЯ MEDIA POLICY

Все утверждения ниже проверены на HEAD `19d2c94` чтением кода, Git history,
offline-пробами на артефактах реальных прогонов LIVE-3/LIVE-4 и сверкой
документации. Ничего не изменялось, кроме создания этого файла (разрешение
владельца). Сеть, провайдеры, модели, Vision, TTS и render не вызывались.

---

## ЧАСТЬ I. ИНВЕНТАРЬ И СРАВНЕНИЕ

### 1. Baseline

- Ветка `governance-reset`, HEAD `19d2c9489fce6d6b20fe5225229675e5414dbbeb`,
  origin == HEAD, worktree чист (до создания этого файла).
- Прочитаны: AGENTS.md, START_HERE, CURRENT_STATE, SYSTEM_MAP,
  ARCHITECTURE_BOUNDARY_MAP, PROJECT_EXECUTION_PLAN, CLEANUP_REGISTRY,
  PRODUCT_PLAN (включая §19 motion), docs/architecture/* (все 5),
  docs/contracts/STAGE1_PUBLIC_CONTRACTS.md, docs/apps/*, apps/README.md,
  docs/adr (16 ADR), релевантные docs/audits (5 крупных) и
  docs/implementation (9 каталогов), docs/handoff/PROJECT_RESCUE_MASTER_PLAN.md.
- Опора на evidence реальных прогонов: `projects/2026-08-09_diagnostic-ru-semantic-live-3`,
  `projects/2026-08-09_diagnostic-ru-semantic-live-4`, замороженный корпус
  PLAN-9D-C (14 сцен, 1064 наблюдения).

### 2. Все найденные asset-контуры

Найдено **пять** контуров поиска/выбора/скачивания стоков (плюс ручные скрипты):

| # | Контур | Вход | Статус |
|---|---|---|---|
| K | **Канонический**: `asset_manifest_builder` + `semantic_selection` + `query_adapter` + `StockProvider`-реестр + `license_policy` + `download.py` | `python -m ai_youtube create` | ACTIVE_PRODUCTION |
| A | **Legacy video engine**: `src/asset_finder.py` + `src/video_asset_engine.py` + `src/media_library.py` (documentary_visual_engine_v2) | только `python pipeline.py` (`compatibility["build_asset_plan"]` → `src/legacy_pipeline/workflow.py:182`) | LEGACY_REACHABLE |
| B | **Solar/Shorts эксперимент**: `src/production_plan/solar_vs_nuclear_render.py` + `youtube_shorts.py` | только `python pipeline.py --production-plan` | LEGACY_REACHABLE, topic-bound |
| C | **Root `legacy/`** (8 скриптов: download_broll, assemble_*, scene_planner...) | ничем не импортируется | LEGACY_UNREACHABLE |
| D | **Локальная библиотека, второй нормализатор**: `LocalLibraryStockProvider` (полный контракт, никем не конструируется) vs inline `rank_local_assets` (wired) | K использует inline | DUPLICATE_OWNER |

Прямых HTTP-вызовов стоковых API вне канонического контракта ровно три живых
места — `asset_finder.py:109/134`, `video_asset_engine.py:408/445`,
`legacy/download_broll.py:25` — все недостижимы из `create`.

### 3. Карта канонического контура (K)

```
python -m ai_youtube create
→ src/content_creation/service.py (create_content; network-approval scope)
→ apps/content_creator/.../fullscreen_voiceover/use_case.py
→ src/news/pipeline.py run_news_to_short_job
   ├─ visual_plan: src/news/visual_plan.py → src/content/visual_planning/engine.build_plan
   │    планнер deterministic_local + (опц.) semantic brief (gpt-4.1, два gate, OFF)
   │    → expansion.expand_queries (лестница) → visual_plan.json
   └─ asset_search: asset_manager.build_news_asset_manifest  [prefer_video=True, :146]
        → AssetManifestBuilder.build, по сцене:
          _prepare_scene: analyze_scene → route_providers (scene_strategy)
                          → query_adapter.build_scene_queries → user/local кандидаты
          _search_scene_providers: провайдеры × ступени, limit 5, всё в один пул
          _select_scene_asset: select_best_with_video:1239
                               → candidate_ranker.select_best_candidate → rank_candidates
          _prepare_visual_review: shortlist top-5 → превью → (Vision rerank OFF,
                               technical rerank OFF)
          _download_and_complete: ensure_selected_asset_downloaded (walk ≤3)
          _apply_fallbacks → _record_scene
        → _write_reviews (Vision-отчёт OFF) → манифест → project_store
→ voice/subtitles/preview → final_renderer (fail-closed, подмен нет) → export
```

Владельцы: запросы — `query_adapter` (питается `expansion`); классификация —
`scene_strategy`; провайдеры — `StockProvider` + `providers/registry`; evidence —
`semantic_selection/evidence.py`; ранжирование — `candidate_ranker`; права —
`license_policy.apply_policy_to_candidate` (один авторитет, вызывается отовсюду);
скачивание — `assets/download.py` через `ensure_selected_asset_downloaded`;
оркестрация — `asset_manifest_builder`; persistence — `project_store`+`pipeline`;
рендер — `final_renderer` (RuntimeError вместо подмены).

### 4. Карта Legacy A (`asset_finder` + `video_asset_engine`)

```
config (channel style.json / video_style.json)
→ scene_planner (visual_keywords, mood, scene_type, duration, voice_duration)
→ build_asset_plan (asset_finder:20; video_task → video engine)
→ build_query_variants (:225): base terms + 2 суффикса из
   ["cinematic","documentary footage"] + 2-словная обрезка + "{mood} documentary"
   + (channel=="survival" → 10 hardcoded jungle-запросов); cap 12, ищутся первые 4
→ Pexels videos (landscape, per_page=10) + Pixabay (film, per_page=10)
   файл: landscape, 960≤w≤2560, aspect 1.45–2.35, dur≥2.5s; причины отказов пишутся
→ scoring (:695): aspect(≤100) + min(dur,18)*8 (доминирует) + resolution(≤80)
   + survival-словари (только survival)
→ local library first (media_library.search_local_assets, порог min_local_score=4)
→ diversity floor: min_local_diversity_per_scene + reserved_download_slots —
   принудительно скачивает свежее, когда локальный пул однообразен (:128-135)
→ multi-clip: adaptive_shot_duration (mood/voice: 6.0/7.5/11.0/13.0s, +2s)
   → target_clip_count (1..5) → _fit_clip_durations (рескейл к длине сцены)
→ download: 1 попытка, без retry; затем ffmpeg-декод первых 2s (:574-590)
→ кэш скачанного (semantic filename + media_index.json, кросс-проектный),
   дедуп по checksum→url→path; usage-запись пишется, но не читается
→ fallback: 4 запроса × 2 провайдера → local → generated_motion (conf 0.32);
   НИКОГДА не абстейнится и не блокирует рендер
→ ЧЕГО НЕТ: прав (license_note-строка; в media_index всё уходит как
   unknown_rights → quarantine_recommended), вертикали (landscape-only),
   semantic evidence, abstain, retry, checksum при скачивании, Vision, review
```

### 5. Карты остальных контуров

**Legacy B (solar/Shorts)** — единственный legacy с abstain и attribution:
рукописные англ. запросы на сцену + `DEFAULT_NEGATIVES`; поиск через
канонические provider-модули, но с дефолтной landscape-ориентацией при цели 9:16
(`pexels_provider.py:188` не переопределён — дефект); скоринг
`18*positives − 35*negatives + quality(≤10 на 1080p) + vertical(12/4) + (dur≥3 ? +10 : −20)`;
блок-лист известных плохих ассетов + off-topic словарь по теме; один клип на
сцену; `used_ids` в прогоне; loop-to-fill при рендере; download чистит
недокачанный файл; права **утверждаются, не проверяются**
(`rights_status:"licensed"` каждому, :446-448); abstain → `needs_assets` +
`check_render_readiness` блокирует рендер; human-review carry-forward
(`_can_keep_reviewed_asset`), отчёт top-8 кандидатов и `selected_sources.md`.
ЧЕГО НЕТ: semantic evidence, расширения запросов, provider-тиров, Vision.

**Legacy C (`legacy/`)** — прото-скрипты: Pexels per_page=1, `videos[0]`, fixed
5s cut, hardcoded пути/шрифты; ноль прав; ценна одна идея — «narration по-русски,
b-roll keywords по-английски» (`scene_planner.py:23`) — прародитель
intent-language split, давно канонизированного.

**D (локальная библиотека)** — сравнение в §23 ниже.

### 6. Capability comparison matrix

Легенда: ✔ есть; ~ частично; ✘ нет. **Жирным** — лучший.

| Capability | K (canonical) | A (video engine) | B (solar) | C (legacy/) | Лучший / почему |
|---|---|---|---|---|---|
| Semantic scene understanding | **✔** brief+entities+slots | ✘ keywords | ~ hybrid (analyze_scene подключён) | ✘ | **K** — единственный с evidence-контрактом |
| Query generation | **✔** лестница ролей, языковой gate | ~ суффиксы+обрезка | ~ рукописные | ✘ 1 keyword | **K**; у A любопытна обрезка как ступень — канон осознанно отказался (subject-free ступени) |
| Query expansion | **✔** intent-ступени | ~ 12 вариантов, ищутся 4 | ✘ | ✘ | **K** |
| Provider abstraction | **✔** StockProvider+реестр | ✘ прямые requests | ~ модули без контракта | ✘ | **K** (ADR 0008) |
| Pexels / Pixabay | **✔** классы, vertical params | ~ landscape hardcode | ~ landscape дефект | ~ | **K** — orientation/min-size из запроса |
| Wikimedia / IA / NASA | **✔** | ✘ | ✘ | ✘ | **K** |
| Local library | ✔ inline (+неподключённый provider-класс) | ✔ тот же индекс | ✘ | ✘ | K, но см. §23 — контрактный класс строже |
| Image support | ✔ | ✘ (image_cache мёртв) | ✘ | ~ | **K** |
| Video support | ✔ | ✔ | ✔ | ~ | K (validation), A (pacing) — см. salvage |
| Mixed media / per-scene kinds | **✔** allowed_media_kinds, visual_type | ✘ | ✘ | ✘ | **K** |
| Rights | **✔** один авторитет, fail-closed | ✘ (unknown_rights) | ✘ (asserted) | ✘ | **K** — безальтернативно |
| Provenance/checksum | **✔** sha256, provenance, атрибуция | ~ имена файлов | ~ selected_sources.md | ✘ | **K** |
| Metadata normalization | **✔** (с дрейфом METADATA_FIELDS) | ~ | ~ | ✘ | **K** |
| Semantic matching | **✔** (с дефектом bag-of-words) | ✘ | ~ substring +18/−35 | ✘ | **K**; у B идея жёсткого negative-веса уже есть в must_avoid |
| Technical scoring | ✔ quality+vertical+framing gate | ✔ aspect/res/dur | ~ | ✘ | **K** (framing-gate 540px), A даёт duration-fit идею |
| Orientation/aspect | **✔** 9:16 путь, crop-check | ✘ landscape | ✘ дефект | ✘ | **K** |
| Duration | ✔ `_duration_check` к длине сцены | ~ min(dur,18)*8 без сцены | ~ ≥3s | ✘ 5s cut | **K** — единственный сравнивает с требуемой длительностью |
| Video usability | **✔** evaluate_usability (ladder) | ~ ffmpeg-декод 2s | ✘ | ✘ | **K**; декод-проба A уже есть в validate_local_asset |
| Multi-clip per scene | **✔** slots+validated windows | ✔ первый в репо | ✘ | ✘ | **K** (валидация окон); у A — mood/voice-пейсинг, которого у K нет |
| Caching | ~ downloads+Vision-кэш, поисковые ответы НЕ кэшируются | ✔ downloads+thumbnails+media_index, поиск не кэшируется | ~ download-level | ✘ | ничья; кэш поисковых ответов — незанятая ниша обоих |
| Download | **✔** retry×3, backoff, checksum, validation | ✘ 1 попытка | ~ чистит partial | ✘ | **K** |
| Fallback | **✔** ступени+abstain (strict) | ✘ никогда не абстейнится | ✔ abstain+render gate | ✘ | **K**; abstain-паттерн B уже канонизирован |
| Manual override | **✔** user assets, replace-slot, review carry | ~ manual_assets conf 0.98 | ✔ reviewed carry | ✘ | **K** |
| Review/debug trail | ✔ review bundle+decision records | ✔ visual_debug.json (rejected+reasons) | ✔ top-8 report | ✘ | **K** (полнее), паритет по «отклонённые с причинами» стоит удерживать |
| Vision | **✔** подключён (OFF) | ✘ | ✘ | ✘ | **K** |
| Render integration | **✔** fail-closed, сегменты, loop-to-fill | ~ concat | ~ loop | ~ | **K** |
| Diversity floor (свежесть пула) | ✘ | **✔** reserved_download_slots | ✘ | ✘ | **A** — реальный GAP канона (уже назначен в PLAN-10D) |
| Mood/voice pacing слотов | ✘ (только длительность) | **✔** adaptive_shot_duration | ✘ | ✘ | **A** — реальный GAP канона |
| Popularity signals | ✘ | ✘ (Pixabay отдаёт — отброшено) | ✘ | ✘ | никто; возможность, не регресс |

### 7. Что canonical делает лучше всех

Права (единственный fail-closed контур; legacy пишет unknown_rights или
утверждает права без проверки), provider-контракт и реестр, вертикаль 9:16 на
уровне API-параметров и framing-gate, semantic evidence + slot-вердикты +
SOFT_REJECT-семантика, скачивание (retry/checksum/validation), abstain и
честные `missing_scenes`, tolerant persistence, ручная замена слота, Vision-обвязка,
мультиязычный запросный контур. **Канон — единственный контур, который вообще
имеет право попасть в продукт**: без прав и вертикали ни один legacy не пригоден.

### 8. Что legacy делает лучше

1. **Mood/voice-aware пейсинг слотов** (`video_asset_engine.adaptive_shot_duration:669-692`,
   `target_clip_count_for_scene`) — темп нарезки от настроения сцены и длины
   озвучки. Канон режет только от длительности (`max_slots_for`). **GAP.**
2. **Diversity floor** (`min_local_diversity_per_scene`, `reserved_download_slots`,
   `skip_existing_duplicates`, :128-135,163,527-528) — принудительная закачка
   свежего материала при однообразном локальном пуле. У канона есть ReuseLedger
   (потолки reuse), но нет «пола свежести». **GAP** (salvage уже прописан в PLAN-10D).
3. **Отчёт отклонённых кандидатов с причинами на сцену** (visual_debug.json;
   у B — top-8 report). Канон пишет decision records и review bundle — паритет
   почти полный; удерживать при изменениях селектора.
4. Идея **loop-to-fill** (B) и **декод-проба** (A) — уже канонизированы.
5. **Никто** (ни канон, ни legacy) не кэширует поисковые ответы и не использует
   popularity-сигналы (Pixabay их отдаёт) — две незанятые возможности.

### 9. Capabilities worth salvaging (главная таблица)

| Legacy item | Полезная способность | Есть ли у канона | Лучший | Salvage? | Target owner | Legacy удалить после? |
|---|---|---|---|---|---|---|
| `adaptive_shot_duration` + `target_clip_count_for_scene` (A) | пейсинг слотов от mood/voice | нет (только длительность) | legacy | **PORT** (reimplement по мотивам: вход — существующие shot_type/длина озвучки, не mood-словарь A) | `completion/assembly.max_slots_for` + ladder | да (в составе retire A) |
| diversity floor / reserved_download_slots (A) | свежесть пула, борьба с повторами | ReuseLedger ≠ то же | legacy | **PORT** — уже назначено: PLAN-10D «diversity-reserve salvage» | `completion` reuse-слой + builder | да |
| rejected-trail (A visual_debug, B top-8) | отладка отбора | почти паритет | ничья | KEEP PARITY (контракт при R-2a: причины отказа сохраняются) | decision records | да |
| ffmpeg-декод пробника (A `_valid_video_file`) | валидация видео | есть (`validate_local_asset`) | canonical | NO (уже есть) | — | да |
| abstain + render gate (B) | честный отказ | есть (strict/missing) | canonical | NO | — | да |
| attribution export (B `selected_sources.md`) | атрибуция | есть (`attribution_export`) | canonical | NO | — | да |
| human-review carry-forward (B) | сохранение одобренного | есть (replace-slot + review) | canonical | NO | — | да |
| «RU narration / EN keywords» (C scene_planner) | языковой split | давно канонизировано | canonical | NO | — | да |
| Поисковый кэш (нет ни у кого) | меньше повторных API-вызовов | нет | — | NEW IDEA (не salvage) — кандидат в PLAN-10B/10C контур | provider layer / http cache | — |
| Popularity-сигналы (нет ни у кого) | слабый prior качества | нет | — | NEW IDEA, только как tie-break внутри support-класса, не как score | ranker tie-break | — |

### 10. Что НЕ надо salvage

- Весь скоринг A/B (substring-веса, `min(dur,18)*8`, survival-словари) —
  канонический evidence/slot-слой строго сильнее; перенос сломал бы контракт.
- Query-обрезка «a b c → a b» (A) — канон осознанно отказался от subject-free
  ступеней (retired C35/C36; PLAN-9D-C: subject-free ступени дали 301 результат
  и ноль полезных решений — чистая стоимость).
- Legacy rights «asserted licensed» (B :446-448) — противоречит [HARD]-классу.
- generated_motion-заглушки (A) как замена abstain — канон правильно абстейнится.
- Landscape-only параметры (A, B).

### 11. Duplicate implementations

- `asset_manager._select_best_candidate` ≡ `select_best_with_video` — построчный
  дубль, production не вызывает, закреплён тестами (patch-point).
- Три video-first реализации (см. §20).
- `LocalLibraryStockProvider` vs `rank_local_assets` (см. §23).
- Полный parallel-контур A (queries+scoring+selection+download) и B —
  legacy-only.
- Preview-URL знание провайдеров продублировано в `visual_preview.py:520-559`
  вне provider-классов (живой out-of-contract фрагмент).

### 12. Duplicate policies

- **Video-preference** существует как три несогласованных политики (builder
  wrapper, facade-дубль, ladder) при нуле продуктовых документов о ней (§20).
- **Reuse/повторы**: ReuseLedger (completion) vs duplicate_penalty (review
  bundle) vs used_asset_ids (builder) — три слоя одного намерения; не сливать
  бездумно: у каждого своя зона (прогон/превью/пул), но контракт стоит описать.
- **«Что считается пригодным»**: rejected (ranker) vs blocking_reasons
  (modes) vs automatic_render_allowed (usability) — иерархия корректна, но
  select_best_with_video читает только первый уровень (rejected) — источник
  дефекта.

### 13. Best query architecture — каноническая

`expansion` (роли из brief) → `semantic_scene_queries` (форма) →
`query_adapter` (provider-facing, языковой gate, дедуп, бюджет). Подтверждено
LIVE-4: полная лестница ролей без truncation. Единственный не-K генератор,
достигающий провайдера — Envato manual request (та же лестница). Оставить как
есть; ничего из legacy не переносить.

### 14. Best provider architecture — каноническая

`StockProvider` + `providers/registry` + `ProviderHttpClient` (retry/backoff/
rate-limit) + per-provider normalizers + `provider_diagnostics` (legacy CLI).
Дефекты для фиксации (не salvage): `AssetSearchRequest.negative_terms`
заполняется, но нигде не потребляется (висячий провод); `evidence.METADATA_FIELDS`
дрейф (`categories/depicts/location` никто не эмитит); Pixabay-титулы
синтетические; IA описание — каталожная проза (см. R-2b).

### 15. Best normalization architecture

Каноническая двухслойная (`candidate_to_rankable` → `rank_provider_results` →
`with_policy_decision`), с оговорками из §14. Потерянных при миграции
способностей не обнаружено: всё, что умели legacy-нормализаторы (размеры,
duration, url), канон умеет строже; наоборот — legacy теряли права и provenance.

### 16. Best rights architecture — каноническая, безальтернативно

Один авторитет `license_policy.apply_policy_to_candidate` + fail-closed
неизвестное + monotonic review (PLAN-STAB-5) + словарь статусов в
`assets/models.py`. Legacy: A пишет unknown_rights (его ассеты в media_index —
quarantine_recommended, `media_library.py:382-398`), B утверждает права без
проверки. Любая консолидация обязана сохранить канон как единственного владельца.

### 17. Best ranking architecture — каноническая, с двумя ремонтами

`rank_candidates`: evidence → field-matches (веса 0.45/0.20/0.15/0.05) →
penalties → support/slot-вердикты → `_ranking_key (rejected, SUPPORT_RANK,
final)`. Сильные стороны: undecidable-поля, SOFT_REJECT, must_avoid как
дисквалификация. Ремонты (не заимствования из legacy): R-2b — evidence
contamination (длинная каталожная проза IA + bag-of-words `concept_score`:
2 разрозненных слова из 2726-символьного текста = subject_match 100 — доказано
на lava и «Life On Earth»); гигиена полей (provider_confidence считается, но в
score не входит — его читает только ladder `tie_break_key`; location_match /
metadata_score / relevance_score / total_score — рассчитано-и-проигнорировано);
orca/whale/«southern right whale» хардкоды — вынести в данные (P2).

### 18. Best selection architecture

**Каноническая база + ladder-контракт как политика.** Сегодняшняя цепочка
production: `select_best_candidate` → `select_best_with_video` (подмена «первое
не-отклонённое видео на любом ранге») → download-walk. Лучшая существующая
реализация выбора — связка `order_candidates(tie_break_key)` +
`evaluate_usability` из `completion/ladder.py`: детерминированный
мультикритериальный порядок (support → required slots → conflicts → rights →
technical → **provider_confidence** → author reqs → score−reuse → stable id) и
usability-gate. Именно её строгая ветка (`ladder.py:450-474`) — готовый
bounded-video-first: «видео только среди SUPPORT_FULL+rights-cleared, иначе
честный общий порядок, trace фиксирует ветку». **Эта ветка сейчас мертва в
production** (единственный caller передаёт draft_complete жёстко,
`asset_scene_completion.py:158-166`).

### 19. Best video/image architecture

Смотри Часть II (§21-27): единая политика на базе ladder-контракта, режимы через
существующие поля, сцена сообщает потребность существующими `visual_type` /
`allowed_media_kinds` / `shot_type` / `source_class`, проект — существующей
`video_first_policy` (coverage) как tie-break, Vision — та же политика до и после.

### 20. Анализ всех video-first реализаций

| Контракт | builder `select_best_with_video:1239` (production) | facade `_select_best_candidate:150` (дубль) | ladder strict `:450-474` (мертво) | ladder draft `:488-503` (draft_complete) |
|---|---|---|---|---|
| Semantic eligibility | только `not rejected` (советующий score_below проходит) | тот же | **SUPPORT_FULL + без requirements** (automatic_render_allowed) | usable_in_draft (support ∈ draftable) |
| Support class | игнорирует | игнорирует | **уважает** | уважает |
| Technical usability | игнорирует | игнорирует | **gate** | gate |
| Score | игнорирует | игнорирует | внутри tie_break (после support) | внутри tie_break |
| Rank/shortlist | **любой ранг**, вне окна превью | тот же | порядок tie_break | порядок tie_break |
| Duration | игнорирует (уже в rejected при too_short) | тот же | через usability | через usability |
| Rights | только через rejected | тот же | **rights_confidence в ключе + gate** | gate |
| Image fallback | «или выбор ранкера» (без trace) | тот же | **честный: пул целиком + trace `video_first:image_fallback`** | тот же + trace |
| Abstention | наследует ранкера | тот же | **сохраняет** (strict_mode_requires_full_support) | сохраняет |

Дополнительные строки той же политики (сверка с Codex-аудитом): **provider
adapter** — retrieval асимметричен (`search_provider:98`: preferred=video ищет
video+image; preferred=image ищет ТОЛЬКО image — видео даже не запрашивается);
**video coverage** (`minimum_video_clips` / ~40% duration) — полезный
quality-target, но не per-scene selector; **compatibility facade** — всегда
передаёт `prefer_video=True` (скрытая template-policy). Оговорка к ladder:
строгая ветка — support-gated (SUPPORT_FULL), т.е. семантически корректная
основа; внутри FULL-класса видео всё же побеждает FULL-изображение независимо
от tie_break — это ровно «bounded preference», а не дефект.

История: жёсткий prefer_video введён `8485a21` (2026-07-28, «harden video-first
draft delivery») — **в тот же день**, когда владелец снял Product Evidence Gate
(historical-эталон показал 39% видео / 61% статики и был признан не-блокером,
`PROJECT_RESCUE_MASTER_PLAN.md:838-856`, `PRODUCT_EVIDENCE_GATE.md:18-33`).
Семантический ранкер тогда был неделю от роду; support/slot-слой появился позже
— обёртка не пересматривалась. **Ни одного продуктового мандата на «любое видео
любой ценой» не существует**: полный grep PRODUCT_PLAN, всех ADR, contracts,
architecture-доков не находит prefer_video/video-first как требование; execution
plan классифицирует «предпочтительный тип визуала» как **[HINT]**
(`PROJECT_EXECUTION_PLAN.md:3842`), а `visual_rendering_policy.md:11` («Reject
off-topic visual results…») прямо противоречит текущему поведению. Намерение
владельца (динамичный ролик, не слайдшоу) — правильное; имплементация («первое
видео на любом ранге») — грубая и уже стоила: 7/12 подмен в 9D-C (гекко ранг 14,
титр-кадр вместо панголина, conspiracy-ролик вместо Saturn V), 2/5 в LIVE-4
(колибри: видео 65.75 вместо кадра 80.72; пингвины: zoo-видео 70.0 вместо
snow-кадров 80.0).

**Ответ §10: да** — неактивная строгая ветка ladder уже содержит правильную
основу единой политики; писать четвёртую реализацию не нужно.

---

## ЧАСТЬ II. ЕДИНАЯ MEDIA POLICY (проект, не имплементация)

### 21. Рекомендуемая unified media policy

Один контракт, один владелец, четыре режима. Семантика:

```
ВХОД: ranked (уже с decision records), режим сцены/проекта/пользователя,
      allowed_media_kinds сцены, review-окно (top-K), coverage-статус проекта.

GATE-ПОРЯДОК (проверен против фактической архитектуры):
 1. author/user hard constraints  (user asset priority; must_include/avoid — уже в ранкере)
 2. allowed media kinds           (существующее поле; сегодня фильтрует только поиск —
                                   политика обязана применять и на отборе)
 3. rights                        (уже в rejected/blocking — не трогается)
 4. semantic eligibility          (support-класс лучшего кандидата = «конкурентный класс»)
 5. scene media need              (visual_type/shot_type/source_class — см. §24)
 6. ranking/evidence              (существующий порядок ранкера)
 7. technical usability           (evaluate_usability — существующий)
 8. media preference СРЕДИ конкурентных
                                  (видео предпочесть ТОЛЬКО внутри того же
                                   support-класса, что лучший кандидат, И внутри
                                   review-окна top-K; вне класса/окна — никогда)
 9. project composition target    (coverage-дефицит решает НИЧЬИ, не классы)
10. abstain                       (missing_scenes — существующий)
```

Ключевое отличие от сегодняшнего: **никаких магических score-gap чисел** — грань
задаётся уже существующей градацией `SUPPORT_RANK` («тот же support-класс») и
существующим `shortlist_size` («в пределах review-окна»). Это ровно контракт
строгой ветки ladder, обобщённый с SUPPORT_FULL до «класс лучшего кандидата».

Определение «конкурентного видео» (слито с Codex-формулировкой): видео
конкурентно изображению, только когда оно (1) прошло те же hard-gates,
(2) в том же support/slot-completeness классе, (3) не хуже по rights/review
состоянию, (4) технически пригодно. Следствия: full-match image побеждает
partial-match video; среди full/full режим PREFER_VIDEO выбирает видео; AUTO
берёт лучший семантический результат независимо от типа; VIDEO_ONLY/IMAGE_ONLY
— жёсткий whitelist с abstain. Плюс требование **симметричного retrieval**:
поиск запрашивает все разрешённые `allowed_media_kinds` в обоих направлениях
(сегодня image-режим не запрашивает видео вовсе — устранить в R-2a).

Полный лексикографический порядок (расширен уровнями lock и composition
intent): 1) user/author hard constraint и persisted lock → 2) допустимый
composition intent → 3) allowed_media_kinds → 4) rights → 5) semantic
admissibility/slot support → 6) scene-specific motion/static need → 7)
evidence/ranking → 8) technical quality/duration → 9) мягкое media-предпочтение
среди конкурентных → 10) project coverage среди безопасных альтернатив → 11)
abstain/manual review. Media kind не имеет права обходить уровни 1-8.

### 22. Рекомендуемые user-facing режимы

«Тип исходников» (проект/шаблон, override на сцену):

- **Auto / Best match** — media-тип только как ничья внутри конкурентного класса.
- **Prefer video** — bounded-предпочтение §21 (п.8).
- **Video only** — `allowed_media_kinds=["video"]`; нет пригодного видео → abstain
  (`missing_scenes`), никакой скрытой картинки.
- **Images only** — зеркально.

Advanced (спрятать): target video coverage (существующие
`minimum_video_clips`/`minimum_video_duration_ratio`), scene overrides (уже есть:
`--visual-brief` с `media_types`). Никаких score-gap/thresholds пользователю.

**DEFAULT (слитая рекомендация)**: для движка `content_creator` в целом —
`AUTO_BEST_MATCH`; для шаблона `fullscreen_voiceover_v1` — профильный
`PREFER_VIDEO` (bounded, §21). `VIDEO_ONLY`/`IMAGE_ONLY` — только явным
выбором автора/шаблона/пользователя. Старое «video-first потому что владелец
когда-то просил» основанием не является (мандата нет — §20).

Выразимость без новой схемы — **подтверждена полями на HEAD**:
`VisualBrief.media_types` → `scene.allowed_media_kinds` (пишется планом, читается
`search_provider:90`); режим проекта — значение в существующем
`channel_config.asset_selection` (merge уже есть) + флаг create/wizard;
enforcement на отборе — внутри политики (сегодня отсутствует — это и есть R-2a).

### 23. Local library: лучший owner и migration plan

Сравнение: `LocalLibraryStockProvider` (не подключён) — schema-gate (v1+,
allowed_for_render, не review, license+provenance) fail-closed, проверка
существования файла, полный StockProvider-контракт (preview/license/download c
checksum+validation); inline `rank_local_assets` (подключён) — channel-scoped
поиск через `search_local_assets` со скорингом, но: ключевые слова = сырой
`primary_query.split()` (включая русские хвосты), нет schema-gate, нет проверки
файла на этапе кандидата, legacy `total_score`. **Лучший owner — контрактный
класс.** План миграции (дом уже назначен — PLAN-10D): (1) перенести в класс
channel-scope и интеграцию скоринга (или признать бинарный матч достаточным —
semantic-ранкер всё равно решает по evidence); (2) включить класс в реестр;
(3) перевести builder на общий провайдерский путь (кандидаты локалки пойдут через
те же `rank_provider_results`); (4) `rank_local_assets` → MIGRATE_CALLERS →
RETIRE_AFTER_MIGRATION. Ничего не удалять до (3).

### 24. Scene-level media logic — правильный owner уже существует

Ни одного нового поля не требуется:

- `visual_type` (video/image/animated_image/diagram) — запрошенный вид; уже
  управляет типом поиска и fallback_type.
- `allowed_media_kinds` — жёсткое множество; сегодня читается поиском, политика
  добавит enforcement на отборе.
- `shot_type == "action"` — **готовый сигнал motion-sensitive сцены**: его уже
  ставит semantic brief (колибри/пингвины/орки в LIVE-4 — все "action").
  Общее правило (без хардкода животных): при shot_type=action и наличии видео в
  конкурентном классе — видео строго предпочтительно; при отсутствии —
  изображение допустимо с пометкой партиальности (уже есть: act=25 у орок ⇒
  partial_support/needs_review). Существующий Vision-контракт уже знает
  `limited_temporal_evidence=true` для стилла
  (`docs/implementation/openai_live_evaluation/LIVE_EVAL_PREPARATION.md:50`) —
  готовый крючок для будущего Vision-веса.
- `source_class ∈ {archive, specific_object, satellite, data_infographic}` —
  **статичные/архивные сцены**: video-бонус не применяется; для
  data_infographic уже сегодня рисуется собственная графика.

Концептуальная 4-классовая модель потребности сцены (формулировка из
Codex-аудита, носители — перечисленные выше существующие поля):
**Motion-required** (действие/процесс нельзя честно передать статикой →
нет пригодного видео = abstain/review, не подмена смысла случайным клипом);
**Motion-preferred** (видео полезно, сильный кадр допустим);
**Static/evidence-first** (архивное фото/документ/портрет/карта/схема —
статика НЕ является downgrade); **Neutral** (тип не входит в смысл).

### 25. Project-level video coverage

Существующие `minimum_video_clips` / `minimum_video_duration_ratio` /
`video_first_policy` (asset_manifest_summaries) — правильный дом: сейчас это
**отчётность** (coverage → review_required warning). Целевое использование: (а)
оставить отчётность; (б) политика читает coverage-дефицит ТОЛЬКО как решатель
ничьих внутри конкурентного класса (п.9 §21). Фиксированный процент не
предлагается — существующие дефолты (1 клип, ratio 0.4) остаются до evidence
и НЕ распространяются автоматически на longform/другие шаблоны. Это отвечает и
плану: «video / still / infographic определяет template policy»
(`PROJECT_EXECUTION_PLAN.md:5816`). Эскалация при дефиците coverage (слито):
1) сначала neutral-сцены; 2) замена только при наличии конкурентного видео;
3) иначе зафиксировать unmet target / review; 4) никогда не выбирать
семантически слабый клип ради процента.

### 26. Vision interaction

Один контракт: политика — **одна функция, вызываемая дважды** (metadata-pass и
после enrich vision_tags), а media-preference живёт ВНУТРИ неё (п.8), а не
поверх. Тогда Vision-подтверждённый кандидат не может быть смыт нижестоящим
сканом видео (сегодня builder:776 повторяет `select_best_with_video` ПОСЛЕ
Vision — подтверждено кодом; тесты эту комбинацию не покрывают вовсе).
Существующий `_semantic_reselection_allowed` сохраняется (user-выбор не
переизбирается). Дополнительный контракт (слито): **замороженный eligible
decision set** — каждый кандидат, способный выиграть после media-policy,
обязан входить в evaluated/preview set; кандидат, вошедший после rerank,
либо дополнительно оценивается в пределах бюджета, либо не может быть выбран.
Сегодня выбор вне превью-окна доказан (LIVE-4, 9D-C 3/12) — это correctness
defect, а не только UX-долг.

### 27. Download fallback

Сохранить walk (`ensure_selected_asset_downloaded`), но контрактом политики:
**повторно запускать тот же selector на оставшемся пуле** (а не сырой обход
списка), соблюдать VIDEO_ONLY/IMAGE_ONLY, не выбирать unseen/unreviewed
кандидата без нужного evidence, и **фиксировать замену** в `selection_decision`
(original → failure → replacement → reason, включая смену media kind). Дом
фиксации уже запланирован — **PLAN-9A best-so-far persistence**. Переход
image→слабое video при провале лучшего image разрешён только если видео в том
же конкурентном классе; при невозможности безопасной замены — review/abstain.

### 28. Target architecture diagram (адаптировано к фактическому репозиторию)

```
VisualBrief (deterministic + optional semantic model)      [есть]
→ expansion ladder → query_adapter                          [есть]
→ providers/registry (StockProvider) → normalized candidates[есть]
→ license_policy (fail-closed)                              [есть]
→ evidence.build_evidence  ← R-2b ремонт                    [есть, ремонт]
→ rank_candidates (+ decision records)                      [есть]
→ UnifiedSelectionPolicy  ← R-2a: ladder-контракт сюда      [ЗАМЕНЯЕТ select_best_with_video]
   ├─ user media mode (allowed_media_kinds + template profile)
   ├─ scene media need (visual_type/shot_type/source_class)
   ├─ semantic eligibility (support-класс лучшего)
   ├─ technical usability (evaluate_usability)
   └─ project composition (coverage tie-break)
→ Shortlist top-K (дедуп по asset — PLAN-10C F2)            [есть, ремонт]
→ Vision evidence (OFF→PLAN-9E) → ТА ЖЕ политика            [есть]
→ Download (walk, bounded + evidence — PLAN-9A)             [есть, ремонт]
→ Manifest → final_renderer (fail-closed)                   [есть]
```

Motion-совместимость: политика формулируется над «кандидатами разрешённых
видов» — будущий composition-кандидат (chart/map/motion) входит как ещё один
вид, не ломая контракт.

### 29. Canonical owners после консолидации

| Решение | Owner |
|---|---|
| Within-type ranking (stock) | `candidate_ranker` (без изменений полномочий) |
| **Media/selection policy (единая)** | один модуль в `src/assets/semantic_selection` (decision-слой), переиспользующий `evaluate_usability`+`SUPPORT_RANK`+`tie_break_key`; builder, ladder и post-Vision зовут ЕГО |
| Media mode defaults | template/channel profile (`asset_selection` в channel_config + production catalog) |
| Scene media need | существующие поля плана (см. §24) |
| Coverage | `asset_manifest_summaries` (отчёт) + вход политики |
| Rights | `license_policy` (не меняется) |
| Download replacement evidence | `selection_decision` (PLAN-9A) |

### 30. PORT_CAPABILITY_TO_CANONICAL

1. Ladder strict video-контракт → UnifiedSelectionPolicy (R-2a) — порт внутри
   канона, не из legacy.
2. Diversity floor (A) → reuse/completion-слой (уже назначено PLAN-10D).
3. Mood/voice-пейсинг (A) → `max_slots_for`/assembly (новый маленький кандидат-
   слайс, после R-2; вход — существующие shot_type/длина озвучки, не
   mood-словарь A).
4. Rejected-trail parity (A/B) → закрепить контрактом в R-2a тестах;
   более явная download-budget telemetry (A) → canonical attempt ledger
   (PLAN-10A).
5. Composition-intents из fixed-планов B (map/annotation/composite/motion как
   знание о типах сцен) → visual planning, DESIGN_ONLY (§44).
6. Early plateau / bounded retrieval (A `target_count*3`, `queries[:4]`) →
   PLAN-10A/10B/10C бюджеты.
7. (Не salvage, новые идеи, отдельно и позже): поисковый кэш; popularity
   tie-break; semantic filenames/thumbnails → shared cache (опционально, P2).

### 31. RETIRE_AFTER_MIGRATION

| Item | Prerequisite |
|---|---|
| `select_best_with_video` (builder) + facade-дубль `_select_best_candidate` + их тесты-пины | R-2a: политика на месте, тесты перенацелены |
| `rank_local_assets` + второй нормализатор локалки | PLAN-10D шаги §23 |
| Контур A целиком (`asset_finder`, `video_asset_engine`) + его ветка в `legacy_pipeline/workflow` | порт §30 п.2-3 выполнен; legacy CLI объявлен ретиром отдельным gate |
| Контур B (`solar_vs_nuclear_render`, `youtube_shorts` fixed plan) | решение по documentary (ADR 0013): либо архив как исторический эксперимент, либо перенос сценария в catalog-template; кода-зависимостей нет |
| `apps/news_to_short` вход | уже помечен планом (PLAN-9B-5b) |
| Ladder draft video-ветка как ОТДЕЛЬНАЯ политика | R-2a унифицирует — ladder зовёт общую политику |

### 32. SAFE_REMOVAL_CANDIDATE (перепроверено независимо)

Подтверждены все прежние кандидаты: `semantic_selection/vision_validator.py` +
экспорт + мёртвый ключ `vision_validation_enabled` (0 callers, 0 tests);
корневой `legacy/` (0 импортов repo-wide — перепроверено grep'ом);
`providers/unsplash_provider.py` + функц. re-exports `search_pexels_*/pixabay_*`
(0 callers; словарные упоминания имени "unsplash" в query_adapter/scene_strategy/
ranker — безвредные записи, не зависимости); пустой `register_commands` в
`cli/commands/assets.py` (**уточнение**: мёртв только он — `handle_assets` в том
же файле ЖИВОЙ, файл не удалять); мёртвые config-блоки `rerank_weights` и
`technical_score_weights` в visual_preview.json (0 читателей); мёртвая ветка
`legacy_fallback_enabled` (логическая форма `A and (A or B)`);
`build_visual_plan_result` как публичный экспорт (только self-caller); дрейф
`METADATA_FIELDS` (`categories/depicts/location`) — удалить или начать эмитить
(решается в R-2b); `AssetSearchRequest.negative_terms` — висячий провод
(потребителя нет): либо подключить к провайдерам, либо убрать поле.

### 33. KEEP_SEPARATE

`anime_factory`/`video_repurposer` (другое приложение, ADR 0011/0016);
`story_card` (свой контур evidence/рендера; MoviePy — временный, гейт MOTION-CS2
parity, НЕ удалён); `legacy_pipeline` + root `pipeline.py` (compatibility
namespace до отдельного retirement-gate); Envato manual provider (ручной
источник, сохранён намеренно); `semantic_visual*` стек (будущее PLAN-9E);
`semantic_brief` стек (активируемая capability).

### 34. UNKNOWN (не удалять)

`semantic_decision_policy.py`, `temporal_video_analysis.py` — припаркованные
неподключённые слои с owning-тестами (судьба — отдельное owner decision);
`production_plan/youtube_shorts.py` — судьба за documentary-решениями;
`docs/implementation/openai_live_evaluation` данные — C31 (production-зависимость,
двигать нельзя); `LICENSE_POLICY_DECISIONS.md` — помечен в индексе unknown
(«читается как действующая политика, но против HEAD не проверялась») — требует
отдельной сверки, т.к. права — [HARD]-класс.

### 35. Что удалять НЕЛЬЗЯ

Tolerant-readers persisted-данных (`NewsJob.from_dict`,
`from_legacy_visual_plan` + flat-ветка, `_LEGACY_BROAD_QUERIES` guard,
`assembly_from_selected_asset`/`read_assembly`, `modes` legacy-rights,
`models.from_legacy`, `quality_check._check_legacy_assets`, rights re-exports);
`asset_manager` facade до перенаправления layering-инверсии
(completion/replacement, quality_check, draft_completion импортируют summaries
через него) и тестов; user-данные `projects/`, media_index, license proof;
rights/provenance история; manual replace-slot workflow; Vision/semantic-brief
стеки; всё из §34.

### 36. Migration order

1. R-2a (политика; внутри — retire facade-дубля, перенацеливание тестов).
2. R-2b (evidence) — параллельно возможен, файлы не пересекаются.
3. R-2c (download evidence) — вместе с PLAN-9A или сразу после.
4. LIVE-5.
5. PLAN-10C (shortlist дедуп/бюджет — уже в плане), PLAN-10D (локалка +
   diversity floor) — после своих блокеров по плану.
6. Порты §30 п.3 (пейсинг) — отдельный маленький слайс.
7. Retire §31 в порядке готовности prerequisites.
8. Safe removals §32 — отдельными cleanup-слайсами.

### 37. Cleanup order (P0-P3)

- **P0 correctness**: R-2a, R-2b (+R-2c evidence-trail).
- **P1 consolidation**: единый policy-owner (внутри R-2a), facade-дубль,
  layering-инверсия, три-в-одну video-first, stale-строки реестра/доков
  (supersede-пометки старых architecture-доков — отдельный docs-слайс).
- **P2 migration**: локалка (PLAN-10D), diversity floor, пейсинг, retire A/B
  после портов.
- **P3 deletion**: §32 + хвосты после P2. Deletion до migration запрещён.

---

## ЧАСТЬ III. RECONCILIATION ДОКУМЕНТАЦИИ И ПЛАНА

### 38. Итоги сверки документации

- `docs/apps/news_to_short.md` — самый точный документ контура; один GAP:
  ladder описан как решатель, video-first подмена не упомянута
  (CONTRADICTS_RUNTIME by omission). Команды указывают на legacy CLI
  (CURRENT_BUT_STALE_DETAILS).
- `docs/architecture/visual_rendering_policy.md` — самый противоречивый:
  `:11` «Reject off-topic visual results…» — **CONTRADICTS_RUNTIME** (главное
  формальное основание P0); `:8-9` запрет карточек — HISTORICAL_SUPERSEDED
  (ladder E/F теперь committed capability); `:10` визуальная проверка —
  IDEA_NOT_IMPLEMENTED (Vision OFF).
- `TARGET_ARCHITECTURE.md` — migration-гипотеза; provider/rights/UI-принципы
  CURRENT_AND_CONFIRMED, folder-план IDEA_NOT_IMPLEMENTED, wrappers-раздел
  HISTORICAL_SUPERSEDED (ADR 0014/0015); «3-5 альтернатив рядом с выбранным»
  сегодня невыполнимо (выбор бывает вне превью-окна) — аргумент в R-2a.
- `news_to_short_phase_ab_plan.md` — приоритет источников актуален; Unsplash
  stale; **о media-типе не говорит ничего** — video-first вне заявленной модели.
- `STAGE1_PUBLIC_CONTRACTS.md` — актуален, кроме «current CLI»; **у решения
  отбора нет contract-страницы вообще** (GAP).
- `CLEANUP_INVENTORY.md` — HISTORICAL_SUPERSEDED целиком (реестр — преемник).
- ADR: ни один из 16 не касается media-типа — video-first не пересекал
  ADR-границ, потому и не был замечен.
- Аудиты: video-first **не рассматривал ни один** (в SECONDARY он — узел на
  диаграмме; порядок проверен, обёртка — нет). Первое измерение — PLAN-9D-C
  2026-08-09. Два audit-первоисточника (motion 2026-08-01 и premium
  2026-08-07) в docs/audits **отсутствуют** — §19 PRODUCT_PLAN опирается на
  нечитаемый источник (docs-долг).
- `PRODUCT_EVIDENCE_GATE.md` — historical_reference; единственное измерение
  video-coverage (39%/61%), снятое как гейт 2026-07-28 — в тот же день появился
  hardcode prefer_video.
- Реестр: строка C40 (duplicate_penalty в rank_local_assets) — устарела
  (на HEAD поле живо только в review_bundle); строчные номера C01-SEM устарели
  (select_best_with_video:1097→1239 и др.) — содержательно верны.
- SECONDARY-находка `pipeline.py:157 and not stage` — локация невалидна на
  HEAD (файл 122 строки, grep пуст); фикс или перенос — UNKNOWN, владелец
  PLAN-13B не закрывал.

### 39. Главные противоречия «док ↔ runtime» (ранжировано)

1. [HARD]-класс «misleading/conflict» побеждается [HINT]-классом «предпочтение
   видео»: `visual_rendering_policy.md:11` vs `select_best_with_video`
   (7/12 в 9D-C, 2/5 в LIVE-4).
2. «Единственный владелец решения об отборе — select_best_candidate»
   (план `:5121`, `:5085-5087`; master plan §2.1) — фактически неверно как
   написано: обёртка переопределяет; плюс живой второй hook technical_rerank.
3. `prefer_video=True` — политика без документа: ни PRODUCT_PLAN, ни ADR, ни
   contracts; только [HINT]-строка без владельца-шага.
4. Ladder-вариант video-first нигде не задокументирован; две разные политики
   под одним именем — паттерн «второй владелец», запрещённый PRODUCT_PLAN §17.
5. UI-обещание «3-5 альтернатив» невыполнимо при выборе вне превью-окна.

### 40. Plan reconciliation — PROPOSED PLAN CHANGES (документы не редактировались)

| # | CURRENT PLAN | ПОЧЕМУ МОЖЕТ БЫТЬ НЕВЕРЕН | EVIDENCE | PROPOSED CHANGE | BENEFIT | RISK | КОГДА |
|---|---|---|---|---|---|---|---|
| 1 | Пересмотр `select_best_with_video` «остаётся за своими шагами» (9D-C `:5476`), но ни один шаг им не владеет | ownership gap: PLAN-10C — shortlist/бюджет, PLAN-9C закрыт, PLAN-9A — persistence; media-подмена — ничья (аналог C63) | план `:5437-5476`; LIVE-4 | Завести owner-issued слайс **R-2a = UnifiedSelectionPolicy foundation** (не «repair обёртки»), с явной записью в execution plan | закрывает P0 и «второго владельца» одним шагом | малый: контракт из существующих словарей | **DO NOW** |
| 2 | R-2a как локальный фикс текущего video-first | фикс bool-обёртки оставит три политики и не даст дом режимам VIDEO_ONLY/IMAGE_ONLY | §20-22 | R-2a — первый bounded-слайс единой media policy (режимы — существующими полями; enforcement allowed_media_kinds на отборе) | не переделывать selection при motion/format-профилях | чуть шире scope; всё равно один модуль | **DO NOW** (в рамках R-2a) |
| 3 | MOTION-CS1…CS4 unscheduled, вне критического пути | верно и должно остаться; но малый foundation-кусок нужен раньше | PRODUCT_PLAN §19.12 («PLAN-9B — вторая половина формата»), §19.4 | Из Motion-семьи СЕЙЧАС — только: (а) media/selection policy как composition-совместимый seam (п.2); (б) DESIGN_ONLY маппинг `composition_type` на существующие поля (source_class/visual_type/fallback_type уже несут diagram/infographic) | стыковка будущих авторов кадра без переделки отбора | нулевой код-риск: дизайн-запись | (а) DO NOW, (б) DESIGN_ONLY |
| 4 | Remotion/HyperFrames — OD-P-6 не решён | решать сейчас не нужно | PRODUCT_PLAN `:766-780` | Не запускать MOTION-CS2 до закрытия stock-качества (R-2a/b → LIVE-5) и OD-решений | фокус на correctness | none | LATER |
| 5 | PLAN-9A «best-so-far» не начат | download-walk сегодня молча заменяет решение | adapters:204-367 | R-2c (evidence замены) исполнить как часть/предпосылку PLAN-9A | честный трейл решений | малый | R-2c с PLAN-9A |
| 6 | PLAN-10D несёт salvage diversity-floor | подтверждаю приоритет: единственный настоящий legacy-GAP вместе с пейсингом | §8-9 | добавить в 10D-контур упоминание mood/voice-пейсинга как отдельного кандидата (или новый маленький слайс) | закрывает «повторы/статичность» жалобы | средний (новая логика слотов) | LATER (после R-2) |
| 7 | `visual_rendering_policy.md` без статуса противоречит committed-поведению | документ читается как действующий | §38-39 | docs-слайс: supersede-пометки старым architecture-докам; contract-страница решения отбора | убирает ложные ориентиры | нулевой | LATER (docs) |
| 8 | LIVE-5 не определён формально | нужен gate после ремонтов | Часть II | LIVE-5 = тот же diagnostic после R-2a+R-2b (+9D-D разблокировка после) | измеримость эффекта | нулевой | после R-2a/b |
| 9 | PLAN-9B-PRODUCER-M-LIVE `next:` до сих пор называет «прогон live-3» | LIVE-3 и LIVE-4 уже состоялись (HEAD `19d2c94` сам описывает live-3) | план `:4786`; projects/…live-3, …live-4 | обновить next-указатель шага на фактическое состояние (в своём reviewed docs-слайсе) | однозначный routing | нулевой | LATER (docs) |

### 41. Ответы на вопросы plan reconciliation

1. **Нужно ли до R-2a определить общий media-selection contract?** Да — §21-27
   и есть этот контракт; R-2a реализует его первый bounded-кусок.
2. **R-2a: repair или foundation?** Foundation единой политики (change #2).
3. **MOTION-CS1…CS4 позже?** Все четыре — позже (unscheduled, как в плане);
   из них ничего не тянуть вперёд, кроме п.3 таблицы.
4. **Малая foundation-часть Motion сейчас?** Да: policy-seam (код, R-2a) +
   маппинг composition_type на существующие поля (design-only запись).
5. **Менять ли план, не реализуя Remotion/HyperFrames?** Да — изменения #1,#2,
   #5 не требуют ни одной motion-библиотеки.

### 42. One visual decision architecture и within/cross-type selection

Целевая модель «SCENE MEANING → VISUAL INTENT → candidate composition types →
specialized authors → evidence → one decision contract → normalized artifact →
FFmpeg» **совместима с фактическими контрактами** и уже наполовину существует:
intent = VisualBrief/visual_intents; composition types сегодня = {stock, user
asset, generated infographic/backdrop} с полями source_class/visual_type/
fallback_type; decision contract = decision records + (после R-2a) единая
политика; normalized artifact = segment contract final_renderer; FFmpeg —
сборщик (PRODUCT_PLAN §19.3). Stock остаётся ОДНИМ из авторов, не центром.
**Within-type** selection (ranking стоков) — `candidate_ranker`, расширять его
до cross-type нельзя (его semantics — asset-кандидаты). **Cross-type** решение
(«сток vs chart vs map vs motion») — будущий отдельный уровень: сегодняшний его
зачаток — `scene_strategy.classify_scene` (уже отправляет data_infographic мимо
стока) + AI Director из PRODUCT_PLAN §19.4 (пока не существует). Правильный
владелец cross-type в будущем — слой стратегии сцены (scene_strategy/визуальный
интент), НЕ ранкер; сравнение — не одним числом, а «пригоден/не пригоден по
классам + poster-review», как задумано в §19.4.

### 43. AUTO + human control

Один pipeline, три режима поверх существующих механизмов: AUTO (текущий),
REVIEW/ASSISTED (review bundle + board уже пишутся; UI позже), MANUAL OVERRIDE
(есть: user assets приоритет; `assets replace` слот; author visual_brief).
User decision сохраняется уже сегодня: `selected_by=user_asset_priority_manual`
защищён от переизбора (`_semantic_reselection_allowed`), замена слота
перезаписывает манифесты и помечает stale downstream-стадии (replacement.py).
Чего не хватает (в контракт R-2a/9A, не в UI): явный `locked_by_user` в
selection_decision, снятие lock тем же CLI, единые правила инвалидции (сегодня
replacement уже помечает render-стадии stale — распространить на смену режима).

### 44. Media kind policy vs composition intent

Развели: **MEDIA KIND** (AUTO/PREFER_VIDEO/VIDEO_ONLY/IMAGE_ONLY) — §21-22,
существующие поля. **COMPOSITION INTENT** (stock/user_asset/chart/map/diagram/
text_motion/infographic/hybrid) — концепт §19 PRODUCT_PLAN; сегодняшние носители:
`source_class` (data_infographic уже маршрутизирует в генератор),
`visual_type=diagram`, `fallback_type`, `provider=generated`. Новая схема не
нужна для нынешнего шага; расширение словаря source_class/visual_type — решение
уровня MOTION-CS4, не сейчас (DESIGN_ONLY-заметка в change #3).

### 45. Template/format policy

Да, defaults — на шаблоне/канале: существующие носители — production catalog
(templates), `channels/<id>/channel_config.json:asset_selection` (merge уже
работает). Примеры-концепты: fullscreen_voiceover → prefer_video (bounded);
story_card → собственный ассет/изображение; будущий documentary → mixed+archive
классы. Отдельные pipelines не создаются (PD-9, ADR 0016).

### 46. Automatic escalation

Целевое поведение уже наполовину есть: `classify_scene` отправляет
data_infographic сразу в генератор (не тратя stock-бюджет) — этот паттерн и есть
«очевидно нужен chart → мимо стока». Для остального: stock → evidence →
«strong enough» = существующий support-класс (FULL/PARTIAL достаточно; ниже —
эскалация); бесконечная эскалация исключена детерминированной лестницей типов
(stock → generated → abstain сегодня; + будущие типы между ними); rights/cost —
существующие gates; честный abstain — missing_scenes. Решатель «strong enough»
после R-2a — единая политика; отдельный «эскалатор» не строится.

### 47. Factual motion safety

Питающий evidence-владелец уже существует и уже применяет правило: генератор
инфографики — «нет evidence → нет фактической диаграммы»
(`generated_infographic` + PRODUCT_PLAN §19.9 сохраняет правило при замене на
ECharts). Числа/факты — из `research/claims.json` и слотов сцены; AI Director
(будущий) по §19.4 «не выдумывает данные», варианты — только из одобренных
шаблонов с валидированными параметрами. Декоративный motion без фактов —
допустим; фактический chart без evidence — нет. Новых владельцев не требуется.

### 48. Human UX model (рекомендация продукта)

PROJECT LEVEL: Automation (Auto / Review each scene), Template/Style,
«Тип исходников» (Auto / Prefer video / Video only / Images only), Vision
(off/assist — после PLAN-9E), Cost mode (free-only / allow-paid — существующие
gates). SCENE LEVEL (позже, в review-борде): Auto / Stock / Мой файл / График /
Карта / Схема / Motion — как composition intent; для Stock — те же 4 media-режима.
Скрыть всегда: провайдерские внутренности, score-gap, support-классы, имена
backend'ов (Remotion/HyperFrames), thresholds. Auto обязан работать без единого
выбора человека (сегодняшний create).

### 49. Motion timing decision

- **FOUNDATION_REQUIRED_NOW**: единая selection/media policy (R-2a) как
  composition-совместимый seam; evidence-трейл замен (R-2c/9A); сохранение
  segment-контракта final_renderer (ничего не ломать).
- **DESIGN_ONLY_NOW**: маппинг composition_type ↔ существующие поля; контракт
  poster/review для будущих авторов (review bundle уже носитель); human-lock
  semantics (§43).
- **IMPLEMENT_LATER**: MOTION-CS1 (preview/fingerprint), CS2 PoC
  (Remotion/HyperFrames — OD-P-6), CS3 tokens, CS4 SceneComposer; ECharts;
  MapLibre; Lottie; OTIO-экспорт.
- **DO_NOT_BUILD**: всё из PRODUCT_PLAN §19.10 «не добавлять сейчас» (Motion
  Canvas, Vega-Lite/D3/deck.gl, Rive, PySceneDetect/OpenCV в Content Creator,
  Shotstack/Creatomate, обязательный облачный рендер, кодоген в user-рантайме);
  Manim/Three.js — только по доказанной потребности внутри выбранного backend.

### 50. Final target product flow

```
SCRIPT → SCENES → VISUAL UNDERSTANDING (brief: есть; Vision: OFF→9E)
→ VISUAL STRATEGY (scene_strategy: есть; расширение на composition — CS4)
→ candidate types (stock: есть; user: есть; generated infographic: есть;
                   chart/map/motion: LATER)
→ generation/search (query ladder + providers: есть; ремонт evidence: R-2b)
→ evidence/rights/quality (есть)
→ auto or human decision (ЕДИНАЯ ПОЛИТИКА: R-2a; human lock: есть+9A)
→ selected composition → download/render кадра (есть; замены с evidence: R-2c)
→ normalized segment (есть) → FFmpeg assembly (есть; CS1 — later)
```

---

## ЧАСТЬ IV. ВЕРДИКТ И ОТВЕТЫ ВЛАДЕЛЬЦУ

### 51. FINAL VERDICT (синтез двух независимых аудитов)

Оба независимых аудита сошлись по существу: **каноническая архитектура —
правильная и единственная возможная основа** (по способностям — вердикт «A»),
**при обязательной существенной консолидации selection-слоя** (по объёму работ
— формулировка «B» Codex-аудита): единая media-policy вместо трёх video-first,
evidence-set identity (shortlist/Vision), download redecision, схождение
local-library. Ни одна legacy-подсистема не лучше в целом — у A/B нет прав,
вертикали, semantic evidence, abstain (A), retry; их полезное исчерпывается §9.
Legacy-контуры после портов §30 готовятся к retirement (§31); пользовательские
данные и tolerant-readers неприкосновенны (§35). Заменять канон legacy-движком
не нужно; сохранять второй pipeline — тоже.

### 52. Точная декомпозиция R-2 (слитая версия двух аудитов)

Важная оговорка (из Codex-сверки): идентификаторов `R-2`/`LIVE-5` в планах
репозитория НЕТ — это рабочие ярлыки owner-промптов; первым действием их нужно
завести как реальные owner-issued слайсы (change #1 таблицы §40).

- **R-2a — Unified Media Policy foundation** (owner: decision-слой
  semantic_selection; builder/ladder/post-Vision — вызовы одной функции).
  Контракт §21-22; реализация — переиспользование `evaluate_usability` +
  `SUPPORT_RANK` + `tie_break_key` (**лучшая существующая логика, четвёртая
  реализация не пишется**). Внутри: retire facade-дубля, enforcement
  `allowed_media_kinds` на отборе, **симметричный image/video retrieval**,
  режимы AUTO/PREFER_VIDEO/VIDEO_ONLY/IMAGE_ONLY. Красные-сначала
  characterization-тесты (5 слитых случаев): (1) full-match image побеждает
  partial-match video; (2) при full/full PREFER_VIDEO выбирает видео; (3) AUTO
  берёт лучший результат независимо от типа; (4) VIDEO_ONLY/IMAGE_ONLY
  абстейнятся при отсутствии допустимого типа; (5) после preview/Vision нельзя
  выбрать кандидата вне evaluated decision set. Acceptance: LIVE-4
  scene_003/004, 9D-C 7/12. R-2a не раздувать до rewrite.
- **R-2b — metadata evidence repair** (owners: evidence.py + IA-normalizer;
  найден только этим аудитом): ограничение/взвешивание длинной каталожной
  прозы, фразовость/близость для многословных концептов, судьба
  provider_confidence, синхронизация METADATA_FIELDS, negative_terms-провод.
  Acceptance: lava и «Life On Earth» перестают получать subject=100.
- **R-2c — evidence-set / shortlist identity** (выделен Codex-аудитом;
  пересекается с уже записанным PLAN-10C F2): дедуп shortlist по asset
  identity до top_k, замороженный eligible set, превью для каждого возможного
  победителя. Исполнять в связке с PLAN-10C, тест из R-2a п.5 — общий.
- **R-2d — download redecision + provenance** (owner: adapters +
  selection_decision; дом — PLAN-9A): повторный запуск той же политики на
  остатке пула, границы same-class/window, фиксация original→failure→
  replacement→reason (+смена media kind).
- **R-2e — local-library convergence** (= PLAN-10D): один matcher boundary
  (рекомендация — контрактный `LocalLibraryStockProvider`, §23), canonical
  rights/evidence, diversity reserve, Unicode/vertical scoring.
- **R-2f — legacy capability port & retirement** (= §30-31): multi-clip/
  пейсинг, cache/telemetry, затем caller/parity gates и вывод контуров A/B.
- Отдельные дома (не R-2): пейсинг-слайс (после R-2), docs-supersede —
  docs-слайс.

### 53. LIVE-5 и Vision readiness

**LIVE-5 — после R-2a + R-2b** (тот же diagnostic-вход, сравнение с LIVE-4
baseline). Vision A/B готов, когда: выбор следует ранжированию в границах
объявленной политики (R-2a); subject-evidence не зарабатывается на невизуальном
тексте (R-2b); превью-окно дедуплицировано и выбранный кандидат в нём
(PLAN-10C); контракт «после Vision политика та же» закреплён тестом (R-2a).
Затем PLAN-9D-D…G и PLAN-9E по плану.

### 54. Ответы владельцу простыми словами

1. **Сначала закончить стоки?** Да. R-2a → R-2b → LIVE-5. Motion не трогать.
2. **Менять ли foundation ради motion уже сейчас?** Только одним способом:
   политика отбора формулируется над «видами кандидатов» (R-2a) — этого
   достаточно, чтобы потом вставить chart/map/motion без переделки.
3. **Начинать MOTION-CS1?** Нет. Unscheduled, вне критического пути — так и
   оставить.
4. **Запускать MOTION-CS2 (Remotion/HyperFrames)?** Нет. OD-P-6 не решён, и до
   чистого stock-качества PoC не имеет смысла.
5. **Как выглядит Auto?** Как сегодня, но выбор честный: семантика → права →
   пригодность → видео предпочитается только среди равных по support и внутри
   превью-окна; нет достойного — картинка; нет ничего — сцена честно пустая.
6. **Как выглядит ручной режим?** Те же артефакты: review-board по shortlist,
   «мой файл» приоритетом, замена слота командой; выбор человека блокирует
   автоподмену и снимается явно.
7. **Как взаимодействуют image/video/motion/chart/map?** Сцена заявляет
   потребность существующими полями; stock — один из авторов; фактические
   chart/map — только из доказанных данных; решение между типами — стратегия
   сцены, не ранкер стоков.
8. **Минимальный следующий implementation slice?** **R-2a** (§52) — один модуль
   политики, переиспользующий ladder-логику, с красными-сначала тестами.
9. **Какие планы переписать/уточнить?** Таблица §40: завести R-2a-слайс в
   execution plan (change #1-2), R-2c связать с PLAN-9A (#5), пейсинг в/рядом с
   PLAN-10D (#6), docs-supersede и contract-страница отбора (#7), LIVE-5 gate
   (#8). Документы в этом аудите не редактировались.
10. **Что готовить к retirement/removal?** RETIRE_AFTER_MIGRATION — §31 (обёртки
    выбора, rank_local_assets, контуры A и B, apps/news_to_short);
    SAFE_REMOVAL — §32 (vision_validator, legacy/, unsplash, мёртвые ключи и
    ветки); НЕ трогать — §34-35.

### 55. Сверка с независимым аудитом (Codex, 2026-08-10)

Два аудита выполнены независимо и сошлись по всем главным пунктам —
перекрёстная валидация: canonical как основа; `select_best_with_video` как
главный дефект (первое не-отклонённое видео любого ранга; 9D-C 7/12, ранги
14/6/5, выборы вне превью-окна); `prefer_video=True` как скрытая policy;
salvage-список (diversity reserve, пейсинг, multi-clip, trail); режимы
AUTO/PREFER/ONLY без числовых score-gap; «конкурентный класс» как грань;
Vision = evidence provider, не второй selector; download-walk без policy;
lock/unlock с инвалидацией; LocalLibrary — один owner; retire A/B после портов;
default AUTO для движка + PREFER_VIDEO как профиль Shorts-шаблона.

**Codex добавил (влито)**: асимметрия retrieval (image-режим не запрашивает
видео — `search_provider:98`); «замороженный eligible decision set» как
отдельный correctness-слайс (R-2c); 4-классовая модель потребности сцены (§24);
4-шаговая эскалация coverage (§25); лексикографический порядок с lock и
composition-intent уровнями (§21); 5 acceptance-тестов R-2a; явная фиксация,
что `R-2`/`LIVE-5` — не plan-ID; наблюдение, что EXECUTION_PLAN до сих пор
называет следующим действием LIVE-3 (устарело относительно HEAD).

**Этот аудит добавил (отсутствует у Codex)**: дефект metadata-contamination —
bag-of-words `concept_score` по неограниченной каталожной прозе IA
(subject=100 у lava и «Life On Earth», доказано offline-пробами) — без него
R-2 неполон; доказательство, что `prefer_video` не имеет ни одного продуктового
мандата (полный грep PRODUCT_PLAN/ADR/contracts) и появился в день снятия
Product Evidence Gate (`8485a21`, 2026-07-28); что строгая support-gated ветка
ladder — готовая основа политики и **мертва в production** (единственный caller
жёстко передаёт draft_complete); тестовый долг (контракт «ранг-1 vs видео» не
защищён ни одним тестом; Vision+prefer_video не тестируются вместе); мёртвые
config-блоки и ветки; provider-metadata карта (METADATA_FIELDS-дрейф,
negative_terms-провод); PRODUCT_PLAN §19 motion-извлечение и план-изменения §40.

**Поправки к Codex-деталям**: пути `src/assets/candidate_ranker.py` и
`visual_planning/model.py` неточны (фактически
`src/assets/semantic_selection/candidate_ranker.py`, `models.py`);
характеристика ladder «семантически слишком грубо» не учитывает, что строгая
ветка support-gated (это и есть рекомендуемый обоими контракт); вывод «decode
validation портировать» требует проверки паритета — канонический
`validate_local_asset/_validate_video` уже строже по content-type/bytes/sha256
(если реального декод-пробника нет — добавить именно его, не весь путь).

---

*Конец отчёта. Аудит строго read-only: изменён только этот файл; commit/push не
выполнялись; сеть, провайдеры, модели, Vision, TTS, render не вызывались.*
