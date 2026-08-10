---
status: audit
audit_date: 2026-08-10
audit_head: 7e9b34a7e9809d66831ee4100d5177c58eca1e2e
working_branch: governance-reset
scope: >
  Полный read-only аудит целостности visual assets, data lineage и hidden coupling.
method: >
  Чтение кода, документации, тестов и Git history без production-изменений и сетевых вызовов.
changes_to_repository: только этот файл
commit_created: no
---

# VISUAL ASSET INTEGRITY, DATA-LINEAGE & HIDDEN-COUPLING AUDIT

Дата аудита: 2026-08-10
Режим: READ-ONLY implementation audit; единственное разрешённое изменение — этот файл.
Проверенный commit: `7e9b34a7e9809d66831ee4100d5177c58eca1e2e` (`governance-reset`).

## 1. Executive summary

Visual-assets core имеет один production-оркестратор и один основной metadata/Vision decision owner, но фактическая decision architecture ещё не едина. После canonical media policy остаётся config-reachable `technical_rerank`, download/completion может заменить winner, continuity превращает свой вторичный вывод в `missing_scenes`, resume доверяет старому manifest без input fingerprint, а strict renderer доверяет ранее сохранённому quality verdict без повторной проверки текущих bytes/rights.

Аудит нашёл 21 новый finding: **P0=0, P1=11, P2=10, P3=0**. Самые опасные классы — не повтор прошлой сравнительной работы:

1. stale local preview cache связывает Vision/technical evidence с предыдущими bytes файла;
2. `technical_rerank` может заменить manual/media-policy winner;
3. download replacement создаёт review-запись с identity A и локальным файлом B;
4. resume не связывает asset decision с visual plan/config/provider/policy snapshot;
5. strict render имеет TOCTOU gap после quality stage.

Rights policy в проверенном пути консервативна и в целом монотонна; `draft_complete` не превращает draft в publish-ready. Главный риск — не явное снятие rights gate, а рассинхронизация identity, evidence и bytes либо обход canonical semantic/media decision до более позднего fail-closed gate.

Вердикт: ядро пригодно для дальнейшего offline hardening, но **не готово к PLAN-9D-D как достоверному quality decision и не готово к будущей Vision activation** до bounded исправлений VA-NEW-01..09, budget ledger correction и нового characterization radius. Текущий `current_checkpoint=PLAN-9D` менять этим аудитом не следует.

## 2. Baseline

| Проверка до создания отчёта | Результат |
|---|---|
| `git status --short --branch` | `## governance-reset...origin/governance-reset`; существовал пользовательский untracked `?? .codex-remote-attachments/` |
| `git log -10 --oneline` | HEAD `7e9b34a fix(metadata-evidence): require coherent local support`; далее `ae6d46c`, `709eaec`, `388b9b1`, ... |
| `git diff --stat` | пусто |
| `git rev-parse HEAD` | `7e9b34a7e9809d66831ee4100d5177c58eca1e2e` |
| `git rev-parse origin/governance-reset` | тот же commit |

Repository truth совпал с ожидаемым HEAD. `.env`, credentials, private keys и пользовательские media/project artifacts не читались и не изменялись. Сеть, provider search/download, Vision, TTS, paid API и реальный render не выполнялись.

### KNOWN BASELINE FAILURE

Известный CI run `31407704218` падает на docs-only gate: `docs/current/START_HERE.md` имеет 102 строки при hard limit 100. Это не исправлялось и не считается finding visual-assets implementation.

Прочитаны canonical docs, релевантные PLAN-секции, contracts/architecture/ADR/implementation/audit материалы и весь `docs/audits/VISUAL_ASSETS_COMPARATIVE_AUDIT_2026-08-10.md`. Предыдущий audit использован только как secondary evidence и список уже известных классов.

## 3. Production graph

Фактический current путь: `python -m ai_youtube create` → `src.content_creation.service.create_content` → `fullscreen_voiceover.use_case` → `src.news.pipeline.run_news_to_short_job` → `visual_plan` → `asset_search` → `src.news.asset_manager.build_news_asset_manifest` → `AssetManifestBuilder.build` → `assets_manifest.json` → `quality_check` → `final_renderer` → export.

| Переход / actual symbol | Owner | Input → output | Persisted? | Mutable? | Can reselect? | Can drop information? | Legacy compatibility? |
|---|---|---|---|---|---|---|---|
| script → visual plan, `src.news.visual_plan.build_visual_plan` | `src.content.visual_planning` + news adapter | script dict → visual plan dict | `localizations/<lang>/visual/visual_plan.json` | да, до stage completion | нет | да, tolerant legacy projection | да |
| scene → `VisualBrief`, `produce_brief`/`analyze_scene` | visual-planning producer; semantic scene reader | scene dict → structured brief/`SemanticScene` | внутри visual plan/manifest | да | нет | aliases normalise | да |
| brief → expansion, `expand_visual_queries` | `src.content.visual_planning.expansion` | provider-language intent → query ladder | `visual_intents`/query plan evidence | да | нет | dedup/cap | legacy seed guard |
| expansion → provider queries, `build_scene_queries` | `src.assets.query_adapter` | scene + capabilities → `SceneQueryPlan` | частично через attempts | да | нет | unsupported-language strings drop fail-closed | да |
| scene → provider order, `route_providers` | `src.assets.scene_strategy` via routing facade | scene/capabilities → routing decision | manifest | нет | да, order affects first pools | unavailable providers drop | facade |
| provider request, `AssetManifestBuilder._search_scene_providers` / `search_provider` | builder + news adapter | query × allowed media kinds → provider calls | attempts only | да | да, order/pool | partial mixed-kind results can be lost | stock/legacy adapter |
| response → normalized candidate, `candidate_to_rankable` | `src.news.asset_provider_adapters` | `AssetCandidate` → rankable dict + nested `canonical_asset` | shortlist/selected subset | да | нет | fields not in model can drop | tolerant raw adapter |
| rights normalization, `apply_policy_to_candidate` | `src.assets.license_policy` | license/provenance → policy flags | candidate/manifest | да | can exclude | unknown stays review/blocked | legacy readers fail closed |
| metadata evidence/rank, `rank_candidates` | `src.assets.semantic_selection.candidate_ranker` | semantic scene + candidates → evaluated ordering | top subset + decision | да | **canonical** | full pool drops | tolerant |
| media policy, `select_preferred_candidate` via `select_best_with_video` | `semantic_selection.media_policy` | ranked window + media restriction → winner | decision/manifest | да | **canonical media choice** | outside window cannot win | wrapper retained |
| preview/review, `_prepare_visual_review` | `visual_preview` + `review_bundle` | top-K → preview analyses/board | review JSON/HTML + cache | да | analyse-only by default | only top-K survives | no |
| optional Vision, `_apply_semantic_visual_evidence` | semantic backend as evidence; ranker remains decision owner | same top-K → `vision_tags` → rerank | cache/review/decision summary | да | authorised when enabled | exact tags can drop at remote download | no; default off |
| optional technical rerank, `select_candidate_after_review` | `review_bundle` | top-K + technical analyses → winner | review/selected | да | **hidden override** | ignores some policy fields | old opt-in path |
| download walk, `ensure_selected_asset_downloaded` | provider adapter | ordered candidates → downloaded manifest | selected asset + attempts | да | authorised replacement | non-model fields can drop | yes |
| completion/assembly, `complete_scene_with_ladder` | `src.assets.completion` + `asset_scene_completion` | primary/pool/slots → assembly | scene manifest | да | authorised bounded replacement/reuse | attempt provenance partial | tolerant single-slot reader |
| fallback/redecision, `_apply_fallbacks` | builder/completion | unresolved state → selected/missing/manual request | manifest | да | yes, policy bounded | reason can be coarsened | debug fallbacks retained off |
| continuity, `check_continuity` | continuity checker | recorded scenes → continuity/missing | manifest | нет | no winner change, but changes completion | assembly detail ignored | old heuristic |
| persistence, `_final_manifest` + pipeline/store | stage owner `asset_manager`/`pipeline` | in-memory graph → JSON | `assets/assets_manifest.json` | external files remain mutable | no | full pool/config versions absent | tolerant reader |
| resume, `run_news_to_short_job`/`validate_stage_output` | `src.news.pipeline` + `project_store` | job stage status + shallow output validation → skip/rerun | `job.json` | да | stale decision may survive | no causal snapshot | yes |
| quality, `run_quality_check` | `src.news.quality_check` | manifest/current local files → report | quality report | current bytes read | no | verdict not bound to later bytes | legacy grandfathering |
| render, `_create_scene_segments` | `src.news.final_renderer` | script + assembly + files → segments | render manifest | bytes can change pre-call | no intended selector | strict skips fresh authorization | tolerant single-slot assembly |

## 4. Ownership map

| Concern | Canonical owner | Secondary/adapter | Audit verdict |
|---|---|---|---|
| visual meaning | `src.content.visual_planning` | `src.news.visual_plan` | один producer, tolerant legacy projection |
| provider-language query | `src.assets.query_adapter` | `content.visual_planning.expansion` supplies structured seeds | ownership в целом согласовано |
| provider registry/contract | `src.providers.registry`, `src.assets.provider_contract` | `news.asset_provider_adapters` | один contract; capability claims не всегда соответствуют implementation |
| semantic evidence/decision | `semantic_selection.evidence` + `candidate_ranker` | media policy | основной owner один, но downstream override существует |
| rights | `src.assets.license_policy` | provider `resolve_license`, completion gates | единый authority, консервативен |
| preview bytes/evidence | `src.assets.visual_preview` | semantic visual cache/service | два разных cache contracts; local source identity неполна |
| completion/readiness | `src.assets.completion` | `news.asset_scene_completion` orchestrates targeted retrieval | один readiness vocabulary, ledger split |
| manifest persistence | news asset stage + `project_store`/`pipeline` | review/attribution writers | основной artifact один, causal fingerprint отсутствует |
| local reusable stock | `media_index.json` design | `media_library` matcher + `LocalLibraryStockProvider` | известный dual matcher; дополнительно current downloads не сохраняют index |
| render authorization | quality + final renderer | draft uses `evaluate_usability` | strict и draft имеют разные final-boundary strength |

## 5. Data-lineage matrix

| Field | Produced by | Transformed by | Persisted/consumed | Status |
|---|---|---|---|---|
| `subject` | planner/semantic brief | `analyze_scene`, evidence concept expansion | visual plan, semantic decision | live; source/English variants can diverge |
| `action` | planner/brief | query ladder + ranker | visual plan/decision | live; morphology/synonym coverage bounded |
| `place` | planner/brief | query adapter/evidence | visual plan/decision | live |
| `context` | authored/model brief only | expansion/ranker | visual plan | live, deliberately not inferred |
| `shot_type` | planner/brief | query modifier/media policy | visual plan | partial semantic influence |
| `visual_type` | legacy plan projection | normalized to media kind | scene/readers | legacy alias, can shadow `allowed_media_kinds` in old data |
| `source_class` | scene strategy/brief | ranking/completion | routing + decision | live |
| `allowed_media_kinds` | planner/brief | retrieval symmetry + media policy | visual plan/manifest | live; bypassable by technical/nonsemantic selector |
| `provider_queries` | author/model brief | `build_scene_queries` | attempts only | live; arbitrary tolerant input can be unbounded |
| `must_include` | author/model | evidence/ranker/decision | decision/manifest | live, hard requirement |
| `must_avoid` | author/model | expansion filter + ranker/completion | decision | live, fail-closed on known contradiction |
| `negative_terms` | adapter request | provider-specific implementation | request only | effectively dead for current providers; already known limitation |
| `source_refs` | script/planner | carried in scene/brief | visual plan | mostly provenance; no direct provider evidence |
| `rights_status` | provider/manual declaration | license policy, completion, quality | nested license/policy/selected | duplicated but authority consistent; review bundle can retain old asset value |
| `provider_confidence` | provider/adapter default | ranker/routing | shortlisted candidate | provider-asymmetric/partial |
| `media_type` | provider/model | normalization, media policy, renderer suffix fallback | candidate/asset | live; missing legacy value defaults to video in model reader |
| `duration` | provider/download validation | ranker/assembly/renderer | asset + slot | remote providers differ before download |
| aspect/orientation | dimensions/provider | technical scoring/crop/render | review/asset | unknown for NASA/IA at search time |
| candidate id | provider `asset_id` | stable wrappers/dedup | shortlist/decision | multiple identity rules |
| asset id | candidate/download/reuse | replacement/register | selected/assembly/index | may remain A in review while file is B |
| preview URL | provider | preview resolution/fallback | cache record/review | live; redirect target not re-authorized |
| download URL | provider | canonical model/download | provenance/asset | live; query params excluded from filename but URL identity weak |
| checksum | download/manual/generated | quality rehash | asset + provenance/index | strong at quality; absent from local preview cache key |
| `selected_by` | selector/manual/download carry | technical rerank/fallback/reuse | selected/decision | mutable and sometimes describes prior choice |
| `support_status` | decision owner/completion | carry/reuse | decision + root alias | duplicated; reuse can retain source-scene semantics |
| slot verdicts | completion assembly | quality/draft render recomputation | assembly | live; strict render trusts prior quality |
| review state | review bundle/manual flow | `attach_selected_asset` | review JSON/HTML | can become A/B hybrid |
| manual/user authority | user asset ranking/replacement API | technical rerank, resume, quality | selected/decision/job | replacement API good; optional rerank can override |
| Vision tags | semantic service | ranker | candidate/review/cache | remote download rebuild drops exact tags |
| technical usability | preview analysis + downloaded validation | quality/completion | review/asset/report | two meanings; preview result can refer to stale bytes |
| reuse state | reuse ledger/completion | assembly/replacement | manifest/report | source identity retained; semantic evidence not fully rebound |

Главная lineage-проблема: `selected_asset` — не immutable entity. Он меняет representation между rankable candidate, downloaded manifest, reused asset и assembly slot, а каждый переход переносит только часть identity/evidence.

## 6. Decision provenance

Для простого успешного remote asset обычно можно восстановить query, provider, selected score, rights object, final path/checksum и часть decision. Нельзя надёжно восстановить:

- полный candidate pool: сохраняются только top-10 ranked, top-5 shortlist и top-5 rejected;
- IDs всех результатов каждого provider/query: attempts содержат только `result_count`;
- точный policy/config/code/provider version, создавший решение;
- identity-связь A→B для download replacement в review artifact;
- exact Vision tags/frame evidence после remote download rebuild;
- targeted slot-search attempts в scene-level search ledger;
- причину, почему resume счёл старое решение совместимым с новыми inputs.

Поэтому ответ на `WHY THIS ASSET?` сейчас частичный. `selection_decision` существенно лучше legacy root fields, но manifest ещё не является replayable decision record.

## 7. Hidden owners

| Механизм | Default | Classification | Что реально меняет |
|---|---:|---|---|
| `candidate_ranker` + media policy | on | `CANONICAL_OWNER` | semantic winner внутри review window |
| Vision evidence rerank через тот же ranker | off | `AUTHORIZED_SECONDARY_DECISION` | меняет scores/winner тем же policy path |
| `technical_rerank` | off | `HIDDEN_OVERRIDE` | выбирает по combined technical score без canonical media/manual/must-avoid invariants |
| nonsemantic `selection_config.mode` branch | off для current channel | `LEGACY HIDDEN_OVERRIDE` | `sort(total_score); first` |
| download walk | on | `AUTHORIZED_SECONDARY_DECISION` | заменяет недоступный winner следующим candidate |
| completion/targeted slot search | draft path | `AUTHORIZED_SECONDARY_DECISION` | заполняет slots и выбирает replacements |
| safe reuse | draft path | `AUTHORIZED_SECONDARY_DECISION` | переносит asset из другой сцены |
| user/manual priority | when supplied | `CANONICAL_AUTHORITY` | должен быть защищён от automatic reselection |
| preview cache | on | `HIDDEN EVIDENCE OWNER` | stale hit меняет фактическое evidence, не winner напрямую |
| resume stage skip | on | `HIDDEN STATE OWNER` | сохраняет старый winner без rerun |
| continuity checker | on | `HIDDEN COMPLETION OVERRIDE` | добавляет resolved scene в `missing_scenes` |
| provider/media order | on | `AUTHORIZED INPUT ORDER` | влияет на pool и download fallback order |

Default metadata-only путь заметно чище старой архитектуры. Нарушения сосредоточены в opt-in path, replacement/resume и post-selection evidence boundaries, поэтому обычные happy-path tests их не показывают.

## 8. Strict vs draft

| Contract | `strict` | `draft_complete` | Verdict |
|---|---|---|---|
| default/opt-in | default | explicit request, кроме Wizard drift | contract верен не во всех entrypoints |
| semantic support | только full, без unmet requirements | partial допустим для draft | осознанное различие |
| rights/must-avoid/conflict | блокируют | также блокируют | не ослаблены |
| publish readiness | возможна после всех gates | всегда false | корректно |
| fallback/reuse | ограничен publish-ready | ladder/reuse/emergency tier для draft | смысл решения меняется, но маркируется |
| manual replacement | publish decision | draft recommendation/requirement | корректно в replacement API |
| quality | строгая publish-ready проверка | warnings + draft usability | ожидаемо |
| final render authorization | доверяет quality result, свежо не rechecks | повторно вызывает `evaluate_usability` | **strict слабее draft на final boundary** |
| output | normal final | draft-named, `publish_ready=false` | корректно |

`draft_complete` меняет не только полноту: partial semantic support и controlled reuse становятся renderable. Это отражено в persisted decision и не является скрытым publish bypass. Неожиданная инверсия — именно свежая final-boundary проверка есть у draft, но нет у strict.

## 9. Provider parity

Легенда: `Y` — реализовано на search candidate; `P` — partial/media-dependent/появляется поздно; `N` — нет.

| Provider | image/video | orientation/duration | semantic metadata | rights/provenance | pagination claim/actual | error/empty semantics | Главная asymmetry |
|---|---|---|---|---|---|---|---|
| Pexels | Y/Y | Y/Y | title/tags P, description weak | normalized provider license, URLs/author | Y/N | normalized; empty list | video request не передаёт orientation, хотя capability global Y |
| Pixabay | Y/Y | Y/Y | tags/title P | normalized license/URLs/author | Y/N | normalized; empty list | video orientation только post-select, не API filter |
| Wikimedia | Y/Y contract, practically file search | dimensions Y, duration P | title/extmetadata | strongest CC metadata | Y/N | two-call all-or-nothing | two HTTP calls/query, video parity depends Commons metadata |
| Internet Archive | Y/Y | N/N until download metadata resolution | title/description/subject P | license often review-required | Y/page=1 only | search succeeds, later file resolution can fail | candidate quality/media facts incomplete at rank time |
| NASA | Y/Y | N/N at candidate | title/description/keywords good | fixed NASA policy + provenance | N/N | per-item all-or-nothing | 1+2N requests and no dimensions/duration before ranking |
| LocalLibrary | Y/Y/music | indexed values | project-language title/tags | current schema + policy | N/local | deterministic | second matcher remains known PLAN-10D issue |
| Fake/test | Y/Y | deterministic | synthetic | deterministic allowed/unknown modes | N | explicit injectable errors | test-only; not production parity evidence |

Общий semantic contract нарушается прежде всего не license shape, а временем появления evidence: NASA/IA сравниваются с Pexels/Pixabay до того, как известны dimensions/duration/orientation. Кроме того, `supports_pagination=True` у Pexels/Pixabay/Wikimedia/IA не подкреплён cursor/page traversal.

## 10. Retrieval/request budget model

Статическая модель, без сети:

`R_scene = Σ(provider × allowed queries × allowed media kinds × provider internal calls × HTTP retry) + preview/download`.

- Canonical `build_scene_queries` объединяет explicit provider queries, до 3 brief variants, structured `visual_intents` и adapted variants; общего cap после объединения нет. При canonical producer верхняя оценка для transition/environment — около 19 unique queries/provider; tolerant external manifest может быть unbounded.
- Для обычной factual сцены `query_not_allowed_for_scene` отсекает `fallback_level>=4`, но всё ещё допускает до трёх rungs от нескольких sources.
- Builder вызывает все допустимые queries всех routed providers; early stop по достаточному candidate pool отсутствует. Mixed scene удваивает calls.
- На каждый logical search возвращается до 5 candidates; cross-query candidate dedup до network отсутствует, после network общий pool тоже не deduped до ranking/review.
- Default keyless set — Wikimedia + NASA + Internet Archive. При 4 queries и двух media kinds: `(Wiki 2 + NASA 11 + IA 1) × 4 × 2 = 112` successful HTTP requests/scene до preview/download. Это верхняя оценка при пяти NASA items.
- Если доступны все 5 remote providers и canonical 19-query mixed transition: 190 logical provider searches/scene и до 950 candidate entries до duplicate returns.
- С `max_retries=3` worst retryable attempts/query-kind: Wiki 6 + NASA 33 + IA 3 + Pexels 3 + Pixabay 3 = 48; `48 × 38 = 1824` HTTP attempts/scene до preview/download. Это analytical ceiling, не заявленный measured runtime.
- `download_stream` имеет внешний и внутренний retry loops, поэтому один preview/download способен дать `3×3=9` HTTP calls. Top-5 preview failures могут добавить до 45.
- Для S сцен линейная верхняя оценка `S × R_scene`: 6 сцен ≈ 672 default successful search requests, 15 ≈ 1680, 60 ≈ 6720 при 4-query mixed assumption. Provider-specific internal fan-out делает цену намного выше числа manifest attempts.
- Resume после завершённого `asset_search` reuse-ит manifest; mid-stage crash не имеет persisted search checkpoint и повторяет provider calls целиком.

Вывод: retrieval symmetry исправила coverage correctness, но без adaptive budget/plateau stop (PLAN-10C), корректного retry ownership и provider-internal cost telemetry request budget действительно может взорваться.

## 11. Provider failure composition

| Сценарий | Current behavior | Verdict |
|---|---|---|
| image succeeds, video fails в одном provider/query | `search_provider` накапливает result, но исключение второго kind выходит наружу; builder помечает весь query failed, накопленное теряется | bug, VA-NEW-06 |
| video succeeds, image fails | то же, зависит от order preferred kind | bug, order-dependent |
| provider A succeeds, B times out | A остаётся в pool, B имеет failed attempt | корректный isolation между providers |
| first query 429, second succeeds | HTTP client retries первый; после исчерпания builder продолжает следующий query | корректно, но budget amplified |
| preview fails | analysis получает failure; candidate может остаться, technical rerank его не выбирает | fail-soft evidence path |
| selected download fails | bounded candidate walk пытается следующий candidate | authorised replacement, provenance defect в review |
| media kind unsupported | capabilities фильтруют kind; exception при capabilities молча заменяется `{preferred}` | conservative, но diagnostics отсутствуют |
| partial metadata | provider/model defaults; ranker может считать evidence unavailable | fail-closed semantics, provider parity слабая |
| NASA item enrichment fails после нескольких успешных items | exception из `_asset_urls`/`_metadata` aborts весь `search`; ранее собранные candidates не возвращаются | provider-specific atomicity bug |

Offline injection подтвердил mixed-media loss: fake stock provider вернул video, затем выбросил `ProviderNetworkError` для image; `search_provider` выбросил ошибку вместо возврата video. Меж-provider isolation при этом сохранён builder-level `try/except`.

## 12. Identity/dedup

Фактические identity rules:

- canonical `AssetCandidate.asset_id`: provider-specific id, иногда `stable_asset_id(provider, source_url, local_path)`;
- rankable candidate сохраняет nested `canonical_asset` как download identity snapshot;
- preview cache: provider + provider_asset_id + asset_id + source string + media/rendition/request params;
- download bytes: SHA-256 + provider/source provenance;
- media library duplicate: checksum, source/download URL или local path;
- completion reuse: asset/reuse identity и scene ledger;
- review: строковый `asset_id` в bounded shortlist.

Одни bytes могут иметь разные provider renditions/URLs/IDs; один provider ID может указывать на меняющийся local path; duplicate queries возвращают один asset несколько раз. До network dedup есть только query-string dedup per provider, а candidate-level dedup перед top-K отсутствует. Это уже известная зона PLAN-10C.

Новый дефект identity: `media_library.register_asset` при duplicate делает `duplicate.update(...)` всеми непустыми полями. Поэтому более новый alias того же checksum/source может переписать historical provider/source/license/asset id старой записи. Дополнительно current news download регистрирует item только in-memory и не сохраняет index, поэтому это поведение проявляется в пределах run, а intended cross-run identity вообще не закрепляется.

## 13. Persistence/resume

Сценарий `found → selected → preview written → stop → resume` имеет два разных исхода:

1. Если `asset_search` отмечен completed и shallow validation manifest проходит, stage пропускается полностью. Старые candidate/evidence/config остаются authoritative.
2. Если процесс упал до completed state, search progress не checkpointed: provider calls, ranking и preview work повторяются; cache помогает только при совпавшем key.

`NewsProjectStore.validate_stage_output` для `asset_search` проверяет лишь non-empty list `scenes`, list `missing_scenes` и базовую shape. Он не проверяет scene parity с current visual plan, selected local files/checksums, rights/decision consistency, config/provider/policy fingerprint либо review linkage (`src/news/project_store.py:150-170`). Pipeline skips completed stage в `src/news/pipeline.py:188-223`.

Явно invalidated только изменение `completion_mode`/`script_adaptation` через `_apply_completion_overrides` (`src/news/pipeline.py:671-740`). Не invalidated:

- visual plan или manual asset bytes, изменённые вне replacement API;
- channel `asset_selection`, global preview/Vision config;
- provider enable/order/capabilities/API behavior;
- metadata matcher/media policy/code version;
- rights policy или license evidence.

Tolerant readers полезны для старых проектов, но compatibility validation не должна одновременно быть freshness proof. Сейчас old persisted decision может смешаться с new downstream files/evidence.

## 14. Stale evidence

| Transition | Что остаётся старым | Что становится новым | Impact |
|---|---|---|---|
| local file overwritten in-place | cached preview, technical/Vision analyses | source bytes/checksum/render | evidence описывает старый файл |
| ranked candidate A → downloaded B | review identity/provider/source/license A | local path/download decision B | review artifact Frankenstein A/B |
| Vision-ranked remote candidate → downloaded manifest | exact `vision_tags`/frame linkage | downloaded bytes/technical validation | decision summary без исходных observed tags |
| reused asset from scene X → scene Y | часть source decision semantic fields | scene id/path/support alias | чужое scene evidence в new scene |
| completed asset stage → resume after config change | old query/provider/policy decision | new runtime expectations | stale decision принят без justification |
| quality passed → file changed → strict render | old quality verdict | current bytes/rights | TOCTOU authorization gap |

Самый точный reproduction — local preview: создать red image, получить preview/cache hit, перезаписать тот же path blue image. `compute_preview_cache_key` не меняется; `PreviewCache.read` валидирует checksum cached preview, а не source snapshot, поэтому возвращает red preview при blue source.

## 15. Manual authority

Нормальный user asset path приоритетен: `_select_scene_asset` отдельно ranks user candidates, выбирает safe user и помечает `selected_by=user_asset_priority_manual`. `_semantic_reselection_allowed` блокирует Vision reselection manual authority. Replacement API проверяет file, checksum и rights proof, обновляет assembly/manifest и помечает preview/quality/render/export stages stale.

Нарушения end-to-end:

- opt-in `technical_rerank` не проверяет manual authority и может выбрать другой top-K candidate;
- nonsemantic legacy mode выбирает `first(total_score)` и не выражает manual contract как invariant;
- in-place изменение manual file вне replacement API не invalidates completed stage/preview;
- `inspect_user_asset` глотает technical validation exception, выставляет существующему path `quality_score=0.7`, а download walker возвращает local path без повторной валидации; ошибка обнаруживается поздно quality gate;
- resume сохраняет manual selection только потому, что весь stage пропущен, а не благодаря checked identity/fingerprint.

Вывод: replacement API можно считать надёжным; произвольный manual override через все opt-in/resume paths — пока нет.

## 16. Rights monotonicity

Проверенный invariant в authorization paths выполняется: downstream не делает `unknown/review/blocked` более разрешающим без policy evaluation или подтверждённой manual declaration.

- provider candidates проходят `apply_policy_to_candidate`;
- `ensure_selected_asset_downloaded` повторно вызывает `resolve_license` и блокирует review/not allowed;
- completion `blocking_reasons` рассматривает rights как hard block в strict и draft;
- quality проверяет root flags, nested license и policy;
- draft renderer повторно проверяет current asset;
- generated infographic получает project-owned provenance и checksum, а не внешнюю license догадку;
- legacy readers по неполным rights данным остаются review/blocked.

Не найдено доказанного `unknown → licensed`, `review → allowed` или `blocked → usable` без нового evidence. Review A/B bug способен **показать** старые rights рядом с новым file, но actual quality/render authorization читает selected manifest/assembly, а не review board. Это P1 provenance issue, не доказанный rights bypass.

## 17. Metadata semantics after 9C-3

`src.assets.semantic_selection.evidence` правильно исключает `search_query/query` из provider evidence, различает provider/query-derived tags, требует field-aware local support и не трактует cross-script absence как contradiction. HEAD `7e9b34a` дополнительно требует coherent local support вместо совпадения в длинной prose metadata.

Классы, проверенные статически:

| Class | Current behavior | Severity |
|---|---|---|
| title spam/long prose | field caps/coherence снижают влияние | low residual |
| generic/provider-generated title | обычно даёт unavailable/weak evidence; provider slug может всё же совпасть | P3 limitation |
| tags duplicated in description | evidence fields остаются раздельны, но одна provider claim может выглядеть как multi-field support | P2 calibration risk, не отдельный confirmed bug |
| singular/plural/hyphenation | normalization/stemming покрывает часть случаев | P3 bounded NLP gap |
| Russian scene vs English metadata | cross-script fail-closed/unmatched | safe, но снижает recall |
| synonyms | только declared concept expansion/glossary; произвольных синонимов нет | expected limitation |
| acronyms/named entities | literal/normalized support; short tokens намеренно осторожны | P3 |
| gerund/verb forms | limited stemming; не универсальный morphology owner | P3 |
| word inside unrelated compound | tokenization заметно лучше substring matcher | largely fixed |
| list-like description | coherent-local-support уменьшает prose contamination | low residual |

Нового P1 metadata ranking defect поверх 9C-3 не найдено. Новый self-evidence сохранился в **другом consumer** — continuity checker, см. VA-NEW-01.

## 18. Query/evidence semantic consistency

Query side использует English brief fields, exact entities, structured intents и safe glossary/Latin fallback. Ranker side использует semantic scene concepts, field-aware provider metadata и declared concept expansions. Их vocabularies пересекаются, но не тождественны:

- query ladder может выбрать declared English synonym/Latin name, которого нет в source-language semantic requirements;
- evidence matcher не переводит Russian scene; вместо guess он abstains, что безопасно, но может лишить правильный English result score;
- `must_include` проверяется буквальнее, чем мягкие subject/action/place concepts;
- provider query expansion имеет up to many rungs, а evidence decision не хранит, какой semantic concept оправдывал каждый rung;
- continuity вообще использует query/source URL как будто это observed environment, прямо отменяя 9C-3 boundary.

Semantic impedance mismatch сейчас чаще создаёт false abstention/poor recall, а не false positive. Исключение — continuity self-evidence, которое превращается в completion failure.

## 19. Multilingual path

Current contract: Russian script → source-language deterministic intent → optional authored/model English `VisualBrief`/`provider_queries` → `query_adapter` проверяет язык каждой строки → English-only remote providers получают только English → English metadata оценивается field-aware matcher.

Положительные свойства:

- `_query_language` и provider `query_languages` дают явный fail-closed;
- при отсутствии English evidence создаётся `translation_required`, Russian query не отправляется remote provider;
- LocalLibrary декларирует `en/ru` и может искать project-language records;
- names/Latin species/locations могут пройти как already-English/Latin tokens без invented translation;
- cross-script metadata не считается отрицательным доказательством.

Утечки/пробелы:

- persisted tolerant `visual_intents` и explicit provider queries могут нести mixed script, но adapter их отбрасывает — безопасно, наблюдаемость partial;
- continuity checker токенизирует только `[a-z0-9]` и потому English query становится сильнее actual Russian title/description;
- source refs/scene narration не получают general TranslatorService, поэтому recall зависит от authored/model brief или bounded glossary;
- named entity transliteration variants не имеют canonical identity link.

Новый критический multilingual bypass не найден; главный defect — English-only continuity heuristic на data path, где он не должен быть authority.

## 20. Config precedence/shadowing

| Setting | Effective precedence | Finding |
|---|---|---|
| `completion_mode` | CLI/Wizard request on create → persisted `job.completion`; explicit resume override → invalidation; empty override keeps persisted | Wizard сам ставит draft для video-first |
| `visual_mode`/prefer video | current news facade hardcodes `prefer_video=True`; scene `allowed_media_kinds` ограничивает winner | global visual_mode config фактически не owner |
| `preferred_media_kind` | scene/brief → retrieval order/media policy | live |
| `allowed_media_kinds` | scene/brief canonical; missing/empty means preferred-only compatibility | live, later rerank can bypass |
| provider enable | registry environment flags/key availability → available list | no channel-level per-provider disable in active call |
| provider priority | `scene_strategy` over available providers | channel config does not directly override order |
| `minimum_video_*` | builder/facade defaults → persisted `video_first_policy` | no demonstrated current CLI override |
| shortlist | built-in/global `config/visual_preview.json` → channel `asset_selection.visual_preview` deep merge | one effective value used by preview/review/media window |
| technical rerank | same global → channel override | default false; dangerous config-reachable selector |
| Vision | global `config/semantic_visual.json` → channel asset selection override; live OpenAI additionally needs paid/runtime gates | default off; multiple gates correctly cumulative |
| semantic brief | planner/runtime choice + persisted plan | input artifact, not channel switch |
| network/paid | explicit request approval + runtime guard; paid approval separate | correct |
| project persisted state | completed stage skip makes old manifest authoritative | silently shadows changed config |
| legacy selection mode | channel override can set nonsemantic mode | latent compatibility selector |

`merge_selection_config` gives nested channel override precedence over global preview/Vision defaults (`src/news/asset_manifest_builder.py:267-327`). Это разумно, но effective config не имеет version/fingerprint в resume validation. Известные unused score weights/`negative_terms` не переобъявляются новым finding.

## 21. Wizard/runtime drift

Canonical CLI оставляет `completion_mode` пустым, что normalizes to strict. Wizard request builder для `video_first` без отдельного вопроса записывает `completion_mode="draft_complete"` и `script_adaptation="light"` (`src/content_creation/request_builder.py:249-255`). Runtime честно persist-ит и исполняет этот request; drift находится между UI/request construction и repository contract «draft_complete — явный opt-in».

| Layer | Обещание/поведение |
|---|---|
| AGENTS / assets README / completion modes | strict default; draft explicit opt-in |
| CLI parser/request | empty → strict unless user passes flag |
| Wizard video-first | implicit draft + light adaptation |
| service/use case | передаёт request без скрытого изменения |
| runtime | persist, invalidate on explicit later change, draft output never publish-ready |

Это уже указано в prompt и не считается новым finding. Более широкого Wizard-only rights/network/paid bypass не найдено: network actions нормализуются одним builder, paid gates остаются отдельными.

## 22. Test blind-spot matrix

Targeted offline radius:

`tests.test_asset_foundation_http_download`, `test_asset_foundation_providers`, `test_provider_foundation_hardening`, `test_provider_routing`, `test_media_selection_policy`, `test_visual_preview_integration`, `test_semantic_asset_selection`, `test_semantic_slot_decisions`, `test_semantic_visual_integration`, `test_autonomous_completion_core`, `test_autonomous_completion_pipeline`, `test_news_stage_idempotency`, `test_manual_asset_replacement`, `test_news_asset_manager_contract`, `test_rights_review_preservation`.

Результат: **247 tests, 8.642s, OK**. Никакой сети/API/render.

| Combination | Coverage | Blind spot |
|---|---|---|
| strict × draft | TESTED broadly | strict QC→file mutation→render UNTESTED |
| image × video × mixed | PARTIALLY TESTED | mixed partial provider failure UNTESTED |
| metadata-only × Vision | TESTED happy paths | Vision tags through remote download rebuild UNTESTED |
| manual × auto | PARTIALLY TESTED | manual × technical rerank on UNTESTED |
| rights allowed/review/blocked | TESTED | review artifact identity after replacement UNTESTED |
| download success/failure | TESTED | A→B full evidence rebind UNTESTED |
| provider success/partial failure | PARTIALLY TESTED | per-media and NASA per-item atomicity UNTESTED |
| resume × fresh | TESTED stage idempotency | config/policy/provider/file fingerprint change UNTESTED |
| technical rerank on/off | PARTIALLY TESTED | only happy-path winner; forbidden combinations absent |
| local × remote | PARTIALLY TESTED | overwrite local source with same path UNTESTED |
| single × multiple providers | TESTED routing | internal request cost/early stop not asserted |
| continuity | TESTED | test itself uses `search_query`-derived ocean/desert labels, institutionalising self-evidence |
| media index | TESTED utility with explicit `save_media_index` | production current path save absent/unasserted |
| legacy manifest | TESTED tolerant read | semantic contamination accepted by compatibility expectations |

Количество тестов велико, но основные blind spots лежат на переходах representation/state, а не внутри отдельных pure functions.

## 23. Legacy contamination paths

| Entry | Necessary compatibility | Current semantic contamination risk |
|---|---|---|
| `src.news.asset_manager` facade | да, current pipeline caller | low; делегирует canonical builder |
| root `pipeline.py`/`src.legacy_pipeline` | временный entrypoint contract | может активировать maintenance/config paths, но не второй current news asset stage |
| `AssetCandidate.from_dict/from_legacy` | да для старых manifests | missing `media_type` defaults video; old identity/rights aliases normalize imperfectly |
| single selected asset → assembly reader | да | old asset проходит без slot semantic evidence |
| quality grandfathering old manifest | да для resume | если нет decision/assembly, применяются rights/technical gates, но не new semantic publish-readiness contract |
| legacy `selected_by`/root `support_status` | tolerant UI/reporting | может shadow nested decision в старом artifact |
| nonsemantic selection mode | compatibility config | current channel override способен активировать `sort/first` selector |
| legacy broad query guard | нужен для persisted filter | не генерирует query, contamination low |
| old `video_asset_engine`/`asset_finder` | legacy callers only | собственные download/index semantics сохраняются вне active graph |
| old tests/patch points | сохраняют API compatibility | могут pin wrapper shape и мешать removal, но не должны pin wrong semantic outcome |

Наиболее реальное проникновение legacy semantics в current product — resume старого project без `selection_decision` и config-reachable nonsemantic mode. Это известный класс salvage/retirement из прошлого audit; новый конкретный hidden selector отражён VA-NEW-21.

## 24. Shadowed better implementations

| Better implementation уже существует | Где shadowed | Consequence |
|---|---|---|
| canonical media policy проверяет `allowed_media_kinds`, bounded window и semantic rank | later `technical_rerank` | более слабый selector может отменить сильный |
| `_local_file_is_valid` связывает stat snapshot, decode и checksums | strict final renderer не вызывает его | draft final boundary сильнее strict |
| `save_media_index` и legacy video/music callers сохраняют index | current news asset downloads только `register_asset` in-memory | intended reusable stock теряется между runs |
| full downloaded manifest уже содержит B identity/provenance/license | `attach_selected_asset` копирует A entry и патчит несколько полей | review A/B hybrid |
| semantic visual cache связывает result с frame/source hashes/request version | local preview cache key не включает source snapshot | semantic layer может корректно cache-ить уже stale frames |
| replacement API invalidates downstream stages | arbitrary in-place file/config change + resume | unchecked stale artifacts |
| provider contract имеет structured errors/capabilities | `provider_capabilities` exception silently becomes preferred-only | diagnostics/feature parity исчезают |

Это не аргумент создавать новые frameworks: в большинстве случаев нужно провести уже существующий stronger primitive через ещё один active caller.

## 25. Failure-injection results

Ad-hoc probes выполнялись временными in-memory/temp-dir scripts через `venv` и не создавали repo files.

| Probe | Observed result |
|---|---|
| `technical_rerank` над manual image + rejected higher-score video | выбран rejected video, `selected_by=technical_rerank` |
| review A затем attach downloaded B | `asset_id/provider/source/license` остались A, `local_path` стал B |
| video result, затем image provider error | `search_provider` выбросил error, video потерян |
| Vision tag на fake Pexels rankable → download rebuild | до download `['observed_whale']`, после download field отсутствует |
| `download_stream`, max_retries=3, retryable failures | 9 underlying request calls |
| strict `_create_scene_segments` с false rights/wrong checksum, render primitive mocked | дошёл до render primitive; fresh authorization не сработала |
| continuity neutral titles + query ocean/desert/ocean | status failed, score 60, middle scene добавляема в missing |
| local preview red → overwrite same path blue → cache read | same key/cache hit, preview остался red |

Existing fakes/tests дополнительно покрыли timeout, 429, 403, empty list, unknown license, missing preview, download failure и old persisted project. Malformed candidate/missing media type обычно normalizes tolerant и затем fail-closed на quality; manual corrupt file даёт поздний, а не ранний diagnostic.

## 26. Observability

Если developer получил только project folder:

| Вопрос | Status | Artifact |
|---|---|---|
| что искалось? | OBSERVABLE/PARTIAL | visual plan + scene provider attempts; targeted slot attempts смешаны с download ledger |
| какие providers ответили? | OBSERVABLE | attempts/errors, но internal NASA calls не видны |
| какие candidates были? | MISSING for full pool | top ranked/shortlist/rejected only |
| почему rejected? | OBSERVABLE for persisted subset | rejection reasons/decision |
| кто победил и почему? | PARTIAL | decision + selected_by; later overrides/replacement linkage неполны |
| почему был заменён? | PARTIAL | download attempts; review identity не rebound |
| какие rights? | OBSERVABLE | selected license/policy/provenance; review может быть stale |
| какой download/checksum? | OBSERVABLE | selected + attempts |
| что одобрил человек? | PARTIAL | manual status/declaration; authority chain не versioned |
| что сделал Vision? | PARTIAL | cache/review/summary; exact tags могут drop |
| что произошло при resume? | MISSING | stage skip есть, input compatibility proof нет |
| какой request budget потрачен? | MISSING/PARTIAL | logical attempts есть, HTTP retries/internal fan-out нет |

Для будущего UI manifest недостаточно объясним: он показывает outcome, но не полную causal chain.

## 27. Scale/performance

Без benchmark и сети:

- Candidate pool растёт `O(scenes × providers × queries × media kinds × limit)`; repeated asset aliases увеличивают JSON и ranking.
- Каждый scene повторно получает provider capabilities/routing/query plan; capabilities cheap, но exception silently affects semantics.
- Ranking/review сортируют и normalise повторяющиеся candidate dicts; top-K ограничивает expensive preview, но search pool до этого не bounded global cap.
- Preview генерирует/decode-ит top-K и sample frames; cache помогает, но stale-key correctness важнее speed.
- Quality hashing/validation использует stat-keyed LRU и повторно не делает FFprobe/Pillow для unchanged snapshot — хорошая оптимизация.
- Local `media_library.search_local_assets` — линейный scan index per scene; 6/15 scenes приемлемы, 60 сцен × large index станет repeated I/O/normalization hotspot.
- Reuse/project pools и duplicate checks преимущественно linear scans; при 60 scenes и сотнях aliases появляется практический `O(S×C)`/местами `O(C²)` pressure.
- Manifest сохраняет bounded top subsets, поэтому JSON не отражает полный in-memory cost и не позволяет post-mortem оценить discarded pool.

| Workload | Static risk |
|---|---|
| Short 6 scenes | request fan-out уже доминирует CPU/JSON |
| Short 15 scenes | rate-limit/retry amplification materially likely при разрешённой сети |
| longform 60 scenes | текущая all-providers/all-queries strategy и local scans не масштабируются без PLAN-10C budget/plateau/dedup |

## 28. Security/trust boundaries

Существующие safeguards:

- filenames/target extensions sanitised; downloads идут через explicit destination и `.part` atomic promotion;
- max bytes, min bytes, optional Content-Length и decode/FFprobe validation;
- allowed content types проверяются, если header присутствует;
- checksum и provenance сохраняются;
- HTML/report text escape-ится в report paths;
- network action guard вызывается до search/preview/download;
- provider metadata не является rights authority само по себе.

Residual findings:

- `requests` follows redirects по умолчанию; `require_network` проверяет original host/action, redirect target не revalidates/allowlists. Compromised provider URL может направить preview/download на иной/internal HTTP target (VA-NEW-19, latent trust-boundary risk).
- missing Content-Type разрешён; decode validation mitigates type spoofing, но bytes всё равно принимаются до validation в bounded file.
- very long Unicode/provider metadata ограничивается не на ingestion для всех fields; ranking/reporting может получить memory/HTML size pressure, хотя escaping уменьшает injection risk.
- retryable 429/5xx responses внутри `_request` не закрываются явно до следующей попытки; full response обычно мал, но connection hygiene неполна.

Path traversal через provider filename в inspected current download target не подтверждён.

## 29. Render boundary

Renderer не имеет скрытого stock/provider fallback и не делает semantic reselection. Он читает assembly, масштабирует slot windows к реальной narration duration, проверяет file existence/timeline, определяет image/video по type/suffix, для video делает crop/loop/trim, для image — base frame и duration segment. Missing file/invalid timeline падают fail-closed.

Однако strict boundary доверяет тому, что quality stage уже проверил rights/checksum/technical/semantic readiness. В `_create_scene_segments` fresh `evaluate_usability` вызывается только при `is_draft` (`src/news/final_renderer.py:294-332`). Если после passed quality файл или manifest изменился и resume/explicit stage запускает final render, strict проверит existence/decode в rendering primitive, но не текущий checksum/rights/selection decision.

Ответ на главный render вопрос:

- renderer может использовать файл, который selection layer не одобрил **после mutation между stages**;
- internal media substitution/fallback не найден;
- current crop/aspect/duration behavior явный, но quality verdict не cryptographically bound к render inputs;
- draft path, парадоксально, повторно авторизует slot и закрывает этот gap.

## 30. Old/new functional pairs

| New/canonical owner | Old/legacy owner | Callers new/old | Features only new/old | Drift risk | Status / safe retire? |
|---|---|---|---|---|---|
| `asset_manifest_builder` | бывший monolithic `asset_manager` facade shape | pipeline → facade → builder | split decisions/assembly / patch points | low-medium | facade нужен до callers gate |
| `provider_contract` + registry | provider-specific helpers in `asset_finder`, `video_asset_engine` | current news / legacy apps | normalized rights/errors / historical cache/index flows | high outside active graph | не retire без entrypoint gate |
| `media_policy.select_preferred_candidate` | wrapper `select_best_with_video`, nonsemantic sort | current builder via wrapper / config branch | hard media restriction / total_score first | high | wrapper пока нужен; nonsemantic branch candidate for retirement |
| `query_adapter` + expansion | persisted legacy broad-query shapes | current builder / tolerant old plans | language fail-closed/provenance / broad aliases | medium | guard нужен, generator retired |
| `selection_decision` + assembly | root `selected_by/support_status`, single selected asset | current quality/render / old project resume | slot evidence / simple asset | high | reader нужен, semantic grandfathering ограничить отдельным gate |
| `LocalLibraryStockProvider` intended canonical | `media_library.search_local_assets` direct matcher | future convergence / current builder direct matcher | provider contract / current index scoring | known high | PLAN-10D, not safe yet |
| semantic Vision evidence in selection | post-selection evaluation/report tooling | builder / maintenance/eval commands | winner influence / offline evaluation | medium | обе capabilities различны; не объединять вслепую |

## 31. High-value Git-history findings

- `technical_rerank` появился до current canonical media-policy repair (blame ведёт к старым commits `fe5ba448`/`24afa971`). PLAN-9C-2/B1 обновил основной selector, но старый post-review owner не был включён в reconciliation radius.
- `attach_selected_asset` пришёл из `4d6e6bef`: intent был показать реально скачанный asset, но implementation patch-ит старую entry вместо полного rebind.
- continuity heuristic существует с `24afa971` и пережил 9C-3, потому что repair менял `semantic_selection.evidence`, а не secondary consumer.
- retrieval symmetry в `ae6d46c` правильно добавила оба media kinds, но композиция ошибок осталась all-or-nothing, создав новый observable partial-failure class.
- HEAD `7e9b34a` ограничен metadata evidence; он не мог исправить preview/download/resume/render lineage. Поэтому зелёный owning radius не является доказательством этих transitions.

История подтверждает не ошибочный product intent, а временные repair slices с недостаточным cross-boundary characterization.

## 32. Docs truth map

| Statement | Classification | Evidence |
|---|---|---|
| active asset stage — news asset manager/builder | CURRENT_AND_TRUE | runtime graph, SYSTEM_MAP/ARCH map |
| один `StockProvider` contract/registry | CURRENT_AND_TRUE | providers registry/contract |
| strict default, draft explicit opt-in | CONTRADICTS_WIZARD, true CLI/runtime default | Wizard request builder line 254 |
| candidate ranker остаётся единственным decision owner, второй selector не создан | CONTRADICTS_RUNTIME when technical rerank/nonsemantic mode enabled | builder lines 628-635, review selector |
| media restriction/manual authority не bypass-ятся | CONTRADICTS_OPT_IN_RUNTIME | technical rerank probe |
| Vision default off, paid/network gated | CURRENT_AND_TRUE | config + backend/runtime guards |
| rights authority едина | CURRENT_AND_TRUE | license policy consumers |
| LocalLibrary имеет один media index/two matchers, convergence planned | DESIGN_CURRENT but incomplete | current download index не save-ится |
| resume сохраняет completed outputs | CURRENT_AND_TRUE | pipeline |
| resume outputs соответствуют current inputs | UNKNOWN/NOT GUARANTEED | fingerprint отсутствует |
| old wrappers retained until callers gate | CURRENT_AND_TRUE | architecture docs/runtime |
| PLAN-9D current checkpoint, 9D-D blocked | CURRENT_AND_TRUE | execution plan/current state |

Docs менять этим аудитом не следует; contradictions являются evidence для owner decision.

## 33. PLAN ownership map

| Finding | Existing owner | Timing/interpretation |
|---|---|---|
| VA-NEW-01 continuity self-evidence | PLAN-9D quality evidence + correction к PLAN-9C-3 boundary | до 9D-D |
| VA-NEW-02 stale preview source | PLAN-9A persistence/provenance; PLAN-9E blocker | до Vision/activation |
| VA-NEW-03 technical selector | PLAN-9C-2 correction; PLAN-9E blocker | немедленный bounded regression fix |
| VA-NEW-04 review A/B | PLAN-9A | до UI/evidence acceptance |
| VA-NEW-05 Vision tags drop | PLAN-9A; PLAN-9E blocker | до Vision activation |
| VA-NEW-06 mixed-kind loss | PLAN-10B provider contract; regression after retrieval symmetry | до LIVE-5 provider exercise |
| VA-NEW-07 index not persisted | PLAN-10D | в planned LocalLibrary slice |
| VA-NEW-08 resume fingerprints | PLAN-9A | до reliance on resume in LIVE |
| VA-NEW-09 strict render TOCTOU | PLAN-9E activation | до LIVE render |
| VA-NEW-10 nested retries | PLAN-10B | до broad provider traffic |
| VA-NEW-11 NASA fan-out/atomicity | PLAN-10B | provider normalization slice |
| VA-NEW-12 budget cap/stop | PLAN-10C | до scale/live multi-provider |
| VA-NEW-13 capability parity | PLAN-10B | contract completion |
| VA-NEW-14 incomplete replay provenance | PLAN-9A | manifest/evidence slice |
| VA-NEW-15 reuse stale evidence | PLAN-9A | completion provenance |
| VA-NEW-16 targeted ledger drift | PLAN-10A | attempt ledger/stop reasons |
| VA-NEW-17 corrupt manual fail-late | PLAN-9A | manual persistence/diagnostics |
| VA-NEW-18 infographic invariants | **NO OWNER** | PROPOSED bounded generated-infographic semantic/layout validation slice; не новый PLAN ID |
| VA-NEW-19 redirect reauthorization | **NO OWNER** | PROPOSED bounded visual-provider redirect trust slice adjacent PLAN-10B |
| VA-NEW-20 duplicate record mutation | PLAN-10D | identity convergence |
| VA-NEW-21 nonsemantic selector | PLAN-9C-2 correction / legacy retirement gate | до activation |

Новые PLAN IDs автоматически не нужны. Два `NO OWNER` пункта достаточно оформить как proposed bounded owner-slices после owner approval.

## 34. New findings ranked P0/P1/P2/P3

| Severity | Count | IDs |
|---|---:|---|
| P0 | 0 | — |
| P1 | 11 | 01–09, 12, 14 |
| P2 | 10 | 10, 11, 13, 15–21 |
| P3 | 0 | — |

P0 не присваивался: ни один probe не доказал automatic publication с knowingly blocked rights/must-avoid. P1 означает production correctness/evidence/resume/render defect с достижимым или явно config-reachable path; P2 — material latent/provider/observability/scale defect, обычно с дополнительным условием.

## 35. Findings already known from previous audit

Не считаются новыми и не входят в числа выше:

- прежний unconditional video override/`select_best_with_video` duplicate facade — исправлен current media policy;
- completion ladder как competing primary selector — исправлен;
- image/video retrieval asymmetry — исправлена `ae6d46c`;
- metadata prose/query contamination в canonical ranker — исправлена до HEAD;
- LocalLibrary duplicate matcher owner — PLAN-10D, известен;
- shortlist/Vision composition boundary и duplicate shortlist — PLAN-10C, известны;
- отсутствие search cache и adaptive stop — общая зона PLAN-10C; новый finding здесь — quantified uncapped composition и retry/provider fan-out;
- download replacement как общий persistence concern — PLAN-9A; новый finding — конкретный A/B review rebind и Vision-tag loss;
- unused `negative_terms`, score weights и provider metadata asymmetries в общем виде;
- generated debug fallback off/default-dead;
- rights architecture, legacy salvage/retirement contours, Wizard implicit draft;
- selected candidate outside preview, legacy paths и planned LocalLibrary convergence.

## 36. Truly NEW findings from this audit

Ниже каждый major finding дан в обязательном формате.

### VA-NEW-01 — continuity использует query как evidence

- **ID:** VA-NEW-01
- **SEVERITY:** P1, confidence HIGH
- **CLASS:** CURRENT BUG / hidden completion override
- **FILES/SYMBOLS:** `src/assets/semantic_selection/continuity_checker.py:12-44`; `AssetManifestBuilder.build`, `src/news/asset_manifest_builder.py:248-263`
- **REACHABILITY:** default path, если три соседние scenes дают query/source tokens ocean→desert/mountain→ocean.
- **EXACT EVIDENCE:** `_environment_for_scene` объединяет `title`, `description`, `source_url`, `source_page`, `keywords`, **`search_query`** и English-only sets. Failed report добавляет resolved scene в top-level `missing_scenes`.
- **REPRODUCTION:** neutral titles/descriptions + search queries `ocean`, `desert`, `ocean` дали `continuity_score=60`, `status=failed`; middle scene становится missing despite selected asset.
- **PRODUCT IMPACT:** false incomplete project, лишняя manual replacement, contradiction между scene resolution и top-level completion.
- **WHY PREVIOUS AUDIT MAY HAVE MISSED IT:** 9C-3 проверял canonical metadata evidence owner; continuity — старый secondary consumer. Existing test использует те же query-derived labels.
- **EXISTING OWNER?:** PLAN-9D quality evidence / correction к 9C-3 boundary.
- **RECOMMENDED BOUNDED FIX:** строить continuity только из observed/validated asset facts либо сделать report advisory; добавить query-free/multi-slot characterization.
- **DO NOT MIX WITH:** NLP redesign, PLAN-10C dedup, renderer refactor.

### VA-NEW-02 — local preview cache не идентифицирует source snapshot

- **ID:** VA-NEW-02
- **SEVERITY:** P1, confidence HIGH
- **CLASS:** CURRENT DATA-LINEAGE BUG
- **FILES/SYMBOLS:** `compute_preview_cache_key`, `PreviewCache.read`, `_materialize_preview`; `src/assets/visual_preview.py:142-158,224-244,464-490`
- **REACHABILITY:** любой local/manual/cached provider asset, перезаписанный по тому же path без `refresh`.
- **EXACT EVIDENCE:** key содержит provider/id/source string/media/request params, но не source SHA-256/stat. Cache read rehashes cached preview only.
- **REPRODUCTION:** red PNG preview → overwrite source blue at same path → same key/cache hit → cached preview pixels remain red.
- **PRODUCT IMPACT:** technical/Vision decision описывает старые bytes, renderer — новые; quality checksum current file не обнаруживает, что evidence было о другом snapshot.
- **WHY PREVIOUS AUDIT MAY HAVE MISSED IT:** preview cache анализировался как bounded infrastructure, не как source-to-evidence identity contract.
- **EXISTING OWNER?:** PLAN-9A; blocker PLAN-9E/Vision.
- **RECOMMENDED BOUNDED FIX:** включить source checksum либо `(resolved path,size,mtime_ns)` + recorded source hash в local key и verify linkage на hit.
- **DO NOT MIX WITH:** semantic result cache rewrite; он уже имеет stronger frame/request identity.

### VA-NEW-03 — `technical_rerank` является вторым selector после media policy

- **ID:** VA-NEW-03
- **SEVERITY:** P1, confidence HIGH
- **CLASS:** LATENT CONFIG-REACHABLE HIDDEN OVERRIDE
- **FILES/SYMBOLS:** `AssetManifestBuilder._prepare_visual_review`, `src/news/asset_manifest_builder.py:599-635`; `select_candidate_after_review`, `src/assets/review_bundle.py:188-214`
- **REACHABILITY:** `asset_selection.visual_preview.technical_rerank_enabled=true`; default false.
- **EXACT EVIDENCE:** selector проверяет лишь root rights/review и `analysis_status=passed`; не проверяет `rejected`, `must_avoid`, conflict, `allowed_media_kinds`, canonical media window reason или manual authority.
- **REPRODUCTION:** manual image metadata winner + higher technical rejected video → selected video, `selected_by=technical_rerank`.
- **PRODUCT IMPACT:** human/media/semantic decision может быть заменён. Hard-rejected remote обычно позже пропустит download walker и fail closed, но manual/off-type correctness уже нарушена и provenance меняется.
- **WHY PREVIOUS AUDIT MAY HAVE MISSED IT:** B1 reconciled named media selectors, а старый opt-in review helper не был включён в owner inventory.
- **EXISTING OWNER?:** PLAN-9C-2 regression correction; PLAN-9E blocker.
- **RECOMMENDED BOUNDED FIX:** technical score должен быть evidence/score component внутри canonical selector либо post-filter обязан вызывать те же blocking/media/manual invariants.
- **DO NOT MIX WITH:** enabling Vision, changing shortlist size, broad scoring retune.

### VA-NEW-04 — review artifact смешивает candidate A с downloaded B

- **ID:** VA-NEW-04
- **SEVERITY:** P1, confidence HIGH
- **CLASS:** CURRENT PROVENANCE BUG
- **FILES/SYMBOLS:** `create_scene_review_bundle`, `attach_selected_asset`; `src/assets/review_bundle.py:88-116,449-464`
- **REACHABILITY:** selected A fails download/license/provider step, candidate B succeeds; либо selected id был вне persisted top-K.
- **EXACT EVIDENCE:** bundle сначала выбирает A или fallback shortlist[0]. Attach копирует old entry, использует `setdefault("asset_id", B)` и обновляет только decision/local path/download status; provider/source/license/title не rebound.
- **REPRODUCTION:** bundle A/old URL + attach selected B/new path → asset_id/provider/source A, path B.
- **PRODUCT IMPACT:** reviewer/owner может одобрить или атрибутировать не тот asset; post-mortem WHY reconstruction недостоверна.
- **WHY PREVIOUS AUDIT MAY HAVE MISSED IT:** общий download replacement был известен, но exact review rebind transition не инъектировался.
- **EXISTING OWNER?:** PLAN-9A.
- **RECOMMENDED BOUNDED FIX:** rebuild selected review entry from actual B, затем явно link `replaces_asset_id=A`; не patch stale dict.
- **DO NOT MIX WITH:** review UI redesign или candidate dedup.

### VA-NEW-05 — Vision tags теряются при remote download rebuild

- **ID:** VA-NEW-05
- **SEVERITY:** P1, confidence HIGH
- **CLASS:** DATA-LINEAGE / EVIDENCE LOSS
- **FILES/SYMBOLS:** `_apply_semantic_visual_evidence`, `src/news/asset_manifest_builder.py:748-790`; `ensure_selected_asset_downloaded`, `src/news/asset_provider_adapters.py:302-366`; `AssetCandidate`, `src/assets/models.py:197-315`
- **REACHABILITY:** semantic Vision enabled + remote stock candidate + successful download.
- **EXACT EVIDENCE:** tags пишутся в rankable dict; `canonical_asset` создан до Vision; model не имеет `vision_tags`; download rebuild читает nested canonical and `carry_decision` переносит только decision/support/slot.
- **REPRODUCTION:** fake Pexels rankable имел `['observed_whale']`; downloaded manifest field отсутствовал.
- **PRODUCT IMPACT:** final selected asset лишается exact observed evidence; review/decision summary нельзя связать с конкретными tags/frame facts.
- **WHY PREVIOUS AUDIT MAY HAVE MISSED IT:** Vision integration test использует local selected candidate и не проходит remote reconstruction.
- **EXISTING OWNER?:** PLAN-9A; PLAN-9E/Vision blocker.
- **RECOMMENDED BOUNDED FIX:** versioned observed-evidence record переносить identity-checked вместе с asset либо строить downloaded manifest из actual enriched candidate.
- **DO NOT MIX WITH:** paid backend activation или prompt/model changes.

### VA-NEW-06 — partial mixed-media success теряется из-за соседнего failure

- **ID:** VA-NEW-06
- **SEVERITY:** P1, confidence HIGH
- **CLASS:** CURRENT PROVIDER ERROR-COMPOSITION BUG
- **FILES/SYMBOLS:** `search_provider`, `src/news/asset_provider_adapters.py:78-131`
- **REACHABILITY:** mixed scene, provider supports image+video, первый media request succeeds, второй raises.
- **EXACT EVIDENCE:** one `results` list surrounds loop, но exception не обрабатывается per kind; builder ловит error вокруг whole query и не получает accumulated results.
- **REPRODUCTION:** video list returned, image raised `ProviderNetworkError`; function raised, video disappeared.
- **PRODUCT IMPACT:** coverage ухудшается именно после retrieval symmetry; provider×scene может стать empty despite good result.
- **WHY PREVIOUS AUDIT MAY HAVE MISSED IT:** symmetry repair tested request presence/success, не partial failure composition.
- **EXISTING OWNER?:** PLAN-10B; bounded correction before LIVE-5.
- **RECOMMENDED BOUNDED FIX:** per-kind attempt/result isolation, return successes plus structured partial errors; fail only if no usable results and policy requires it.
- **DO NOT MIX WITH:** media preference redesign или new provider contract.

### VA-NEW-07 — current downloads не сохраняются в global media index

- **ID:** VA-NEW-07
- **SEVERITY:** P1, confidence HIGH
- **CLASS:** CURRENT PERSISTENCE BUG / SHADOWED CAPABILITY
- **FILES/SYMBOLS:** `build_news_asset_manifest`, `src/news/asset_manager.py:109-147`; `ensure_selected_asset_downloaded`, `src/news/asset_provider_adapters.py:350-366`; `save_media_index`, `src/media_library.py:51-55`
- **REACHABILITY:** любой successful current news download, следующий run ожидает LocalLibrary reuse.
- **EXACT EVIDENCE:** facade loads `assets/library/metadata/media_index.json`; adapter calls `register_asset(media_index, manifest)`; production news path не вызывает `save_media_index`. `rg` нашёл save только utility/legacy video/music/tests/migration.
- **REPRODUCTION:** static callers proof; in-memory index changes, disk owner не вызывается. Repo artifact не мутировался для проверки.
- **PRODUCT IMPACT:** downloaded stock исчезает из intended global reuse после process/run, повторяются network/cost/selection.
- **WHY PREVIOUS AUDIT MAY HAVE MISSED IT:** прошлый finding считал matchers/owner count, а не write lifecycle current news path.
- **EXISTING OWNER?:** PLAN-10D.
- **RECOMMENDED BOUNDED FIX:** один atomic persistence point у canonical LocalLibrary owner после successful build; characterization restart/reload.
- **DO NOT MIX WITH:** merging both matchers или bulk reindex existing protected assets.

### VA-NEW-08 — resume не имеет input/policy/provider fingerprints

- **ID:** VA-NEW-08
- **SEVERITY:** P1, confidence HIGH
- **CLASS:** CURRENT STALE-STATE BUG
- **FILES/SYMBOLS:** `run_news_to_short_job`, `src/news/pipeline.py:188-223,671-740`; `NewsProjectStore.validate_stage_output`, `src/news/project_store.py:150-170`
- **REACHABILITY:** completed asset_search + changed visual/manual/config/provider/policy/code inputs + resume.
- **EXACT EVIDENCE:** validation проверяет JSON shape; invalidation существует только для completion mode/script adaptation.
- **REPRODUCTION:** static state model; completed scene list остаётся valid независимо от missing file/checksum/rights/config changes.
- **PRODUCT IMPACT:** stale winner/evidence/rights expectation переиспользуются молча; либо mid-stage crash повторяет expensive calls без checkpoint.
- **WHY PREVIOUS AUDIT MAY HAVE MISSED IT:** resume tests pin idempotent skip, не compatibility predicate между persisted decision и current inputs.
- **EXISTING OWNER?:** PLAN-9A.
- **RECOMMENDED BOUNDED FIX:** persist minimal asset-search input fingerprint (plan/manual snapshot, effective config, provider/policy/schema versions) в существующем manifest/job owner; invalidate from asset_search on mismatch.
- **DO NOT MIX WITH:** новый `search_session.json` owner (OD-24) или ProjectRepository writer.

### VA-NEW-09 — strict renderer имеет TOCTOU authorization gap

- **ID:** VA-NEW-09
- **SEVERITY:** P1, confidence HIGH
- **CLASS:** CURRENT RENDER-BOUNDARY BUG
- **FILES/SYMBOLS:** `_create_scene_segments`, `src/news/final_renderer.py:274-359`; `_local_file_is_valid`, `src/assets/completion/modes.py:556-633`; `run_quality_check`
- **REACHABILITY:** quality passed, затем asset bytes/manifest/rights изменились до resumed/explicit final_render.
- **EXACT EVIDENCE:** draft branch calls fresh `evaluate_usability`; strict checks assembly/path/timing then renders. Pipeline only checks saved quality status before dispatch.
- **REPRODUCTION:** valid image + false rights/wrong stored checksum reached mocked render primitive in strict.
- **PRODUCT IMPACT:** strict output может использовать bytes, не соответствующие approved checksum/evidence; draft final gate сильнее strict.
- **WHY PREVIOUS AUDIT MAY HAVE MISSED IT:** quality and renderer separately covered; cross-stage mutation не инъектировалась.
- **EXISTING OWNER?:** PLAN-9E.
- **RECOMMENDED BOUNDED FIX:** одинаковый fresh authorization snapshot для strict/draft либо quality→render fingerprint verified immediately before segment creation.
- **DO NOT MIX WITH:** FFmpeg quality/codec redesign.

### VA-NEW-10 — nested HTTP retries дают R² download attempts

- **ID:** VA-NEW-10
- **SEVERITY:** P2, confidence HIGH
- **CLASS:** CURRENT BUDGET/RETRY BUG
- **FILES/SYMBOLS:** `ProviderHttpClient.download_stream` and `_request`, `src/assets/http_client.py:68-170`
- **REACHABILITY:** retryable preview/download timeout/connection/5xx/429.
- **EXACT EVIDENCE:** outer `for max_retries` вызывает `_request`, у которого свой `for max_retries`.
- **REPRODUCTION:** `max_retries=3` → 9 session requests.
- **PRODUCT IMPACT:** rate-limit/cost/latency amplification; reported logical attempt занижает traffic.
- **WHY PREVIOUS AUDIT MAY HAVE MISSED IT:** retry tests проверяли eventual error/success, не underlying call count across nested layers.
- **EXISTING OWNER?:** PLAN-10B.
- **RECOMMENDED BOUNDED FIX:** один retry owner; streaming body failure retry отдельно и с ясным total-attempt budget.
- **DO NOT MIX WITH:** global network approval or provider-specific retry policy rewrite.

### VA-NEW-11 — NASA search имеет 1+2N fan-out и all-or-nothing enrichment

- **ID:** VA-NEW-11
- **SEVERITY:** P2, confidence HIGH
- **CLASS:** PROVIDER-SPECIFIC SCALE/ATOMICITY BUG
- **FILES/SYMBOLS:** `NasaImageLibraryStockProvider.search/_candidate_from_item`, `src/providers/nasa_images_provider.py:40-53,78-160`
- **REACHABILITY:** NASA routed, up to five results requested.
- **EXACT EVIDENCE:** one search then `_asset_urls` + `_metadata` per item; any exception aborts whole `search`. Candidate still lacks dimensions/duration.
- **REPRODUCTION:** static call graph: `1+2×5=11` successful requests/query-kind; with retry 3 — up to 33 attempts.
- **PRODUCT IMPACT:** request explosion, loss of earlier good candidates, weaker technical ranking.
- **WHY PREVIOUS AUDIT MAY HAVE MISSED IT:** provider parity noted metadata variation, but internal HTTP graph не был посчитан.
- **EXISTING OWNER?:** PLAN-10B.
- **RECOMMENDED BOUNDED FIX:** bounded per-item isolation/lazy enrichment or batch strategy; expose internal request counts/partial errors.
- **DO NOT MIX WITH:** NASA policy/license changes.

### VA-NEW-12 — combined query/request budget не имеет global cap или plateau stop

- **ID:** VA-NEW-12
- **SEVERITY:** P1, confidence HIGH
- **CLASS:** CURRENT SCALE/COST ARCHITECTURE DEFECT
- **FILES/SYMBOLS:** `build_scene_queries`, `src/assets/query_adapter.py:270-331,420-568`; `_search_scene_providers`, `src/news/asset_manifest_builder.py:378-455`
- **REACHABILITY:** default remote search; особенно mixed transition/environment и tolerant plans с большим query list.
- **EXACT EVIDENCE:** per-source caps существуют, но after-composition cap нет; every provider × every allowed query запускается до конца, независимо от enough candidates. Dedup только query-string per provider.
- **REPRODUCTION:** analytical model в разделе 10: 112 default successful HTTP requests/scene при 4-query mixed; theoretical 1824 retry attempts/scene для all-five 19-query mixed.
- **PRODUCT IMPACT:** rate limits, long runs, repeated aliases и дорогой evidence pool без proportional quality gain.
- **WHY PREVIOUS AUDIT MAY HAVE MISSED IT:** previous audit отметил absence cache/PLAN-10C, но retrieval symmetry и provider-internal fan-out не были скомпонованы в одну upper-bound модель.
- **EXISTING OWNER?:** PLAN-10C.
- **RECOMMENDED BOUNDED FIX:** global per-scene logical/HTTP budget, query/provider plateau stop, pre/post-network dedup telemetry; сохранить hard semantic restrictions.
- **DO NOT MIX WITH:** deleting providers, lowering rights/semantic thresholds.

### VA-NEW-13 — provider capabilities декларируют несуществующую parity

- **ID:** VA-NEW-13
- **SEVERITY:** P2, confidence HIGH
- **CLASS:** CONTRACT/PARITY DEFECT
- **FILES/SYMBOLS:** provider `capabilities/search` in `src/providers/{pexels,pixabay,wikimedia_commons,internet_archive,nasa_images}_provider.py`; `provider_capabilities`
- **REACHABILITY:** routing/query/media decisions для всех remote providers.
- **EXACT EVIDENCE:** Pexels/Pixabay/Wikimedia/IA claim pagination but no cursor/page traversal; orientation capability is global although video request filtering differs; NASA/IA omit search-time dimensions/duration. Capability exception silently falls back to preferred kind.
- **REPRODUCTION:** static parity matrix/call params.
- **PRODUCT IMPACT:** downstream assumes common filters/facts, но candidates сравниваются на разной evidence maturity; pagination-aware future caller будет введён в заблуждение.
- **WHY PREVIOUS AUDIT MAY HAVE MISSED IT:** provider list/metadata owners были известны, exact capability-to-wire behavior не reconciled.
- **EXISTING OWNER?:** PLAN-10B.
- **RECOMMENDED BOUNDED FIX:** truthful media-specific capability schema/diagnostics или implementation parity; не обещать pagination без token handling.
- **DO NOT MIX WITH:** new provider abstraction.

### VA-NEW-14 — persisted manifest не позволяет replay selection

- **ID:** VA-NEW-14
- **SEVERITY:** P1, confidence HIGH
- **CLASS:** CURRENT EVIDENCE/OBSERVABILITY DEFECT
- **FILES/SYMBOLS:** `_scene_entry`, `src/news/asset_manifest_builder.py:1042-1092`; provider attempts/final manifest
- **REACHABILITY:** every nontrivial selection, особенно multiple queries/replacements.
- **EXACT EVIDENCE:** only candidates[:5], ranked[:10], rejected[:5]; provider attempts have counts, not result IDs; effective code/config/policy/provider versions absent.
- **REPRODUCTION:** inspect serialized schema: discarded aliases/candidates cannot be recovered from attempts.
- **PRODUCT IMPACT:** невозможно независимо доказать why winner beat every alternative, расследовать regression или replay old decision.
- **WHY PREVIOUS AUDIT MAY HAVE MISSED IT:** prior focus был competing owners, не forensic completeness artifact.
- **EXISTING OWNER?:** PLAN-9A.
- **RECOMMENDED BOUNDED FIX:** extend existing manifest with bounded candidate identity/decision ledger, stop reasons and effective fingerprints; full raw provider payload не нужен.
- **DO NOT MIX WITH:** new database/search-session owner or storing unbounded API responses.

### VA-NEW-15 — safe reuse переносит semantic evidence source scene

- **ID:** VA-NEW-15
- **SEVERITY:** P2, confidence HIGH
- **CLASS:** CURRENT PROVENANCE BUG, draft/manual path
- **FILES/SYMBOLS:** `_build_reused_asset`, `src/assets/completion/replacement.py:737-827`
- **REACHABILITY:** owner-confirmed reuse одного project asset в другом scene/slot.
- **EXACT EVIDENCE:** `deepcopy(source_asset)` меняет identity/path/scene/support, но prior decision сохраняет остальные semantic fields/reject context; root/persisted `render_ready=True` выставляется до downstream recomputation.
- **REPRODUCTION:** static field-diff of copied source decision vs updated keys.
- **PRODUCT IMPACT:** target scene report содержит чужой semantic rationale; UI может показать confidence/reasons source scene. Actual draft gate остаётся консервативным, поэтому unsafe publish не доказан.
- **WHY PREVIOUS AUDIT MAY HAVE MISSED IT:** reuse оценивался как completion behavior, не decision rebinding.
- **EXISTING OWNER?:** PLAN-9A.
- **RECOMMENDED BOUNDED FIX:** новый target-scene decision с explicit `reused_from`, human confirmation и только transferable rights/technical evidence.
- **DO NOT MIX WITH:** disabling safe reuse или changing draft semantics.

### VA-NEW-16 — targeted slot-search ledger не является частью scene search truth

- **ID:** VA-NEW-16
- **SEVERITY:** P2, confidence HIGH
- **CLASS:** CURRENT OBSERVABILITY/PROVENANCE DEFECT
- **FILES/SYMBOLS:** `complete_scene_with_ladder/targeted_slot_search`, `src/news/asset_scene_completion.py:139-384`; builder scene entry
- **REACHABILITY:** draft composite scene с unfilled semantic slots.
- **EXACT EVIDENCE:** targeted attempts возвращаются в `ladder_attempts`, затем смешиваются с `download_attempts`/global attempts; `scene_provider_attempts` и scene query plan не дополняются. Attempt не хранит `slot_name`; candidates получают общий `fallback_level=10`.
- **REPRODUCTION:** static call/data-flow.
- **PRODUCT IMPACT:** folder не отвечает, какой slot вызвал query и почему provider был вызван после initial search; budget/stop reason неверно классифицируется.
- **WHY PREVIOUS AUDIT MAY HAVE MISSED IT:** earlier completion selector audit рассматривал winner authority, не attempt-ledger taxonomy.
- **EXISTING OWNER?:** PLAN-10A.
- **RECOMMENDED BOUNDED FIX:** один existing attempt ledger schema с phase=`targeted_slot_search`, slot id/name, query origin и candidate IDs.
- **DO NOT MIX WITH:** new completion ladder или query generator.

### VA-NEW-17 — corrupt manual asset диагностируется поздно

- **ID:** VA-NEW-17
- **SEVERITY:** P2, confidence HIGH
- **CLASS:** CURRENT FAIL-LATE DIAGNOSTICS BUG
- **FILES/SYMBOLS:** `inspect_user_asset`, `src/news/asset_manifest_builder.py:1343-1436`; `ensure_selected_asset_downloaded`, `src/news/asset_provider_adapters.py:289-299`
- **REACHABILITY:** user path exists, rights declaration cleared, bytes malformed/decoder error.
- **EXACT EVIDENCE:** validation exception swallowed; `quality_score=0.7` solely from existence; existing path returns early without revalidation. Quality later rejects missing passing validation/checksum.
- **REPRODUCTION:** static/error injection path; no protected manual artifact touched.
- **PRODUCT IMPACT:** manual authority кажется accepted, expensive stages/review могут продолжиться, затем поздний opaque failure.
- **WHY PREVIOUS AUDIT MAY HAVE MISSED IT:** manual replacement API itself validates correctly; initial user-assets ingestion — другой path.
- **EXISTING OWNER?:** PLAN-9A.
- **RECOMMENDED BOUNDED FIX:** persist explicit technical failure and block candidate early with actionable manual diagnostic; не silently assign medium quality.
- **DO NOT MIX WITH:** changing manual rights policy.

### VA-NEW-18 — generated infographic не валидирует semantic/layout invariants

- **ID:** VA-NEW-18
- **SEVERITY:** P2, confidence MEDIUM
- **CLASS:** LATENT GENERATED-ASSET CORRECTNESS GAP
- **FILES/SYMBOLS:** `InfographicSpec/spec_from_scene/render_infographic`, `src/assets/generated_infographic.py:46-140,212-341`
- **REACHABILITY:** `allow_infographic_fallback` enabled для `data_infographic` с authored spec; current news facade disables automatic fallback.
- **EXACT EVIDENCE:** integers clamp negatives, но `active_points<=total_points` не проверяется; headline/labels не имеют wrapping/bounds invariant; technical validation проверяет output PNG, не factual consistency/layout clipping.
- **REPRODUCTION:** static spec acceptance (`active_points > total_points`, arbitrarily long labels).
- **PRODUCT IMPACT:** technically valid, project-owned asset может быть internally contradictory/clipped и получить full support.
- **WHY PREVIOUS AUDIT MAY HAVE MISSED IT:** generated fallback считался off/dead; spec-enabled data path не проверялся как evidence producer.
- **EXISTING OWNER?:** NO OWNER; proposed bounded generated-infographic validation slice.
- **RECOMMENDED BOUNDED FIX:** schema invariants + deterministic layout overflow checks before generation/support decision.
- **DO NOT MIX WITH:** motion/diagram engine redesign or enabling automatic generation.

### VA-NEW-19 — redirects обходят original-host network authorization boundary

- **ID:** VA-NEW-19
- **SEVERITY:** P2, confidence MEDIUM
- **CLASS:** LATENT SECURITY/TRUST-BOUNDARY RISK
- **FILES/SYMBOLS:** `ProviderHttpClient.get_json/download_stream/_request`, `src/assets/http_client.py:49-170`; preview/download callers
- **REACHABILITY:** approved provider search/preview/download URL отвечает redirect на иной host.
- **EXACT EVIDENCE:** `require_network(action, detail=_host(original_url))` вызывается один раз; requests follows redirects by default; final target не rechecked/allowlisted.
- **REPRODUCTION:** static requests semantics; сеть не выполнялась.
- **PRODUCT IMPACT:** compromised provider metadata/endpoint теоретически может инициировать request к unexpected/internal HTTP target.
- **WHY PREVIOUS AUDIT MAY HAVE MISSED IT:** network approval owner был audited на action level, не redirect chain.
- **EXISTING OWNER?:** NO OWNER; proposed bounded slice adjacent PLAN-10B.
- **RECOMMENDED BOUNDED FIX:** disable automatic redirects and validate each hop/final scheme+host against provider policy, сохранив explicit network action.
- **DO NOT MIX WITH:** general cybersecurity audit or replacing HTTP library.

### VA-NEW-20 — duplicate registration переписывает historical identity

- **ID:** VA-NEW-20
- **SEVERITY:** P2, confidence HIGH
- **CLASS:** CURRENT IDENTITY MUTATION BUG
- **FILES/SYMBOLS:** `register_asset`, `src/media_library.py:58-71`
- **REACHABILITY:** same checksum/source/path зарегистрирован снова с другим nonempty provider/id/license metadata.
- **EXACT EVIDENCE:** duplicate найден, затем `duplicate.update` всеми nonempty normalized fields.
- **REPRODUCTION:** utility-level data flow; existing media library tests cover registration/save, но не immutable identity semantics.
- **PRODUCT IMPACT:** audit history/attribution одной physical item меняется задним числом; dedup скрывает alias вместо explicit merge record.
- **WHY PREVIOUS AUDIT MAY HAVE MISSED IT:** PLAN-10D focus был two matchers, не mutation policy одной record.
- **EXISTING OWNER?:** PLAN-10D.
- **RECOMMENDED BOUNDED FIX:** immutable canonical identity/provenance + explicit aliases/observations; mutable usage fields отдельно.
- **DO NOT MIX WITH:** bulk rewrite/reindex protected media library.

### VA-NEW-21 — nonsemantic mode сохраняет legacy `sort/first` selector

- **ID:** VA-NEW-21
- **SEVERITY:** P2, confidence HIGH
- **CLASS:** LATENT LEGACY HIDDEN OVERRIDE
- **FILES/SYMBOLS:** `_select_scene_asset`, `src/news/asset_manifest_builder.py:519-597`; `merge_selection_config`
- **REACHABILITY:** channel/runtime `asset_selection.mode` не `semantic`; current default/channel semantic.
- **EXACT EVIDENCE:** branch сортирует `state.candidates` по `total_score` и берёт first, обходя canonical semantic/media policy; `ensure_decision` лишь оформляет результат после выбора.
- **REPRODUCTION:** static config-reachable branch.
- **PRODUCT IMPACT:** legacy config может вернуть current product к weaker selector без отдельного compatibility warning.
- **WHY PREVIOUS AUDIT MAY HAVE MISSED IT:** comparative audit концентрировался на named old/new functions и default path.
- **EXISTING OWNER?:** PLAN-9C-2 correction / legacy retirement gate.
- **RECOMMENDED BOUNDED FIX:** доказать caller/config need; иначе retire after gate. Если оставить — enforce canonical blockers/media/manual authority.
- **DO NOT MIX WITH:** deleting compatibility facade или broad channel config cleanup.

## 37. False alarms investigated and rejected

1. **«Current media policy всё ещё безусловно выбирает video».** Нет: current policy соблюдает hard `allowed_media_kinds` и bounded preference; defect находится в later opt-in rerank.
2. **«draft_complete ослабляет rights/must_avoid».** Нет: эти blocks mode-independent; draft лишь разрешает partial non-contradictory support и всегда non-publish-ready.
3. **«Vision выполняет paid calls по умолчанию».** Нет: config off, backend/runtime paid/network gates cumulative; в аудите calls=0.
4. **«Unknown provider license автоматически становится licensed».** Нет: license policy сохраняет review/blocked без authoritative evidence.
5. **«Generated infographic без provider license — rights bypass».** Нет: это project-generated bytes с собственными spec fingerprint/provenance/checksum; gap — spec correctness, не external rights.
6. **«Preview cache вообще не валидирует bytes».** Валидирует cached preview checksum/decode. Bug точнее: не проверяет identity текущего source snapshot.
7. **«Отсутствующий Content-Type позволяет arbitrary bytes в render».** Download может принять пустой header, но media decode/technical validation fail-closed; redirect остаётся отдельным risk.
8. **«Renderer сам подменяет media/ищет fallback».** Нет: он использует persisted assembly и падает на missing/invalid path; suffix fallback только определяет image/video rendering primitive.
9. **«Manual replacement API не инвалидирует downstream».** Инвалидирует preview/quality/render/export и проверяет checksum/rights. Initial user-assets и arbitrary file mutation — отдельные paths.
10. **«Tolerant readers создают третью project system».** Нет: они читают старые shapes в existing project artifacts; риск — semantic grandfathering, не новый repository owner.
11. **«Provider order сам по себе competing semantic selector».** Это authorised input ordering; hidden defect возникает, когда partial failure или no-budget policy делает order outcome-dominant.
12. **«Rights review A/B artifact означает proven unsafe render».** Нет: quality/render читают selected manifest/assembly, а не review board. Это provenance/UI P1, не доказанный authorization bypass.

## 38. Recommended sequence

1. **До PLAN-9D-D:** owner принимает этот audit как blocking evidence; добавляются characterization tests для VA-NEW-01, 03, 04, 06, 08, 09 без изменения current checkpoint.
2. **Bounded correctness correction:** убрать query self-evidence из continuity/completion, провести `technical_rerank` через canonical policy, сделать mixed-kind partial results atomic, закрыть strict render fresh authorization.
3. **PLAN-9A lineage slice:** source-snapshot preview key, full A→B evidence rebind, Vision evidence carry, resume fingerprint, bounded replay ledger, reuse/manual diagnostics.
4. **До разрешённого provider LIVE-5:** один retry owner, hard per-scene budget/stop, NASA partial isolation и truthful capability matrix (PLAN-10B/10C).
5. **Planned cleanup без смешивания:** PLAN-10A attempt taxonomy; PLAN-10D media-index persistence/identity/matcher convergence.
6. **После owner decision:** два proposed bounded slices для generated infographic invariants и redirect hop authorization.
7. **Только затем:** 9D-D evidence decision → PLAN-9A/10A/10B/10C по canonical route → PLAN-9E activation. Vision не включать только потому, что PLAN-10C завершён.

## 39. What NOT to change

- Не создавать второй provider contract, selector, asset pipeline, readiness vocabulary, search database или project writer.
- Не ослаблять rights, `must_avoid`, conflict, misleading-content, strict или `publish_ready=false` draft gates.
- Не включать Vision/technical rerank/provider network до исправления lineage/budget boundaries и отдельного разрешения owner.
- Не превращать metadata gaps в общий NLP/translation redesign.
- Не объединять PLAN-9A, 10A, 10B, 10C, 10D и 9E в один mega-change.
- Не удалять compatibility wrappers/legacy readers без callers + old-project migration/retirement gate.
- Не bulk-reindex/перезаписывать `assets/`, `manual_assets/`, projects, evidence, licenses или media.
- Не менять current checkpoint/active route на основании одного audit artifact.
- Не исправлять известный `START_HERE.md` line-limit failure внутри visual-assets work.
- Не retune semantic scores до исправления identity/evidence ownership: иначе измерение качества будет недостоверным.

## 40. Final verdict

Система имеет зрелые local safeguards — единый provider/license contract, conservative rights, semantic decision schema, bounded review, technical validation, checksum, manual replacement и draft non-publish contract. Но пять cross-boundary links остаются ненадёжны: **source bytes→preview evidence, canonical decision→optional rerank, candidate A→downloaded B, inputs/config→resume, quality snapshot→strict render**.

Именно эти links объясняют, почему happy-path tests и предыдущий comparative audit могли быть зелёными, а production decision всё ещё не полностью auditable. Исправления должны быть малыми owner-slices вокруг существующих primitives, не новой архитектурой.

### Прямые ответы на 15 вопросов

1. **Есть ли один фактический visual decision architecture?** Один основной orchestration graph — да; один фактический decision owner во всех modes/transitions — нет.
2. **Где остаются hidden secondary owners?** `technical_rerank`, nonsemantic `sort/first`, download walk, completion/targeted search/reuse, continuity-to-missing, preview cache и resume skip.
3. **Можно ли доверять resume?** Только при фактически неизменных inputs/config/files; система это не доказывает, поэтому в общем случае нет.
4. **Можно ли доверять manual override end-to-end?** Replacement API — да; initial/manual + technical rerank/in-place mutation/resume chain — нет.
5. **Монотонны ли rights?** В authorization paths — да, reverse transition без evidence не найден. Reporting identity может быть stale.
6. **Может ли selected asset потерять/унаследовать чужое evidence?** Да: Vision tags drop, review A/B, safe reuse source decision, stale preview.
7. **Есть ли provider, нарушающий общий semantic contract?** NASA наиболее явно: expensive per-item enrichment и нет dimensions/duration at rank time; IA также late-resolves media facts. Pagination claims нескольких providers ложны.
8. **Взорвался ли request budget после retrieval symmetry?** Потенциально да: all-query/all-provider mixed retrieval, NASA fan-out и nested retries не имеют общего cap/plateau.
9. **Есть ли production capability хуже shadowed implementation?** Да: strict render не использует уже существующий fresh usability verifier; current news path не вызывает уже существующий `save_media_index`; optional rerank слабее media policy.
10. **Какие legacy semantics реально проникают?** Old manifest semantic grandfathering, single-asset assembly aliases, legacy root decision fields и config-reachable nonsemantic selector.
11. **Какие 3 дефекта дадут максимальный прирост quality selection?** Устранить hidden `technical_rerank`; связать preview/Vision evidence с exact source bytes; сохранить partial mixed-media successes с budgeted retrieval.
12. **Что обязательно исправить ДО LIVE-5?** VA-NEW-01, 02, 03, 04, 05, 06, 08, 09 и минимальные 10/12 budget guards; затем targeted tests.
13. **Что лучше проверить самим LIVE-5?** Реальную semantic полезность metadata/queries, provider rate-limit/latency, diversity, crop/motion fit, фактические license/attribution pages и human-visible scene continuity. Только после отдельного network/provider разрешения.
14. **Готово ли ядро к PLAN-9D-D?** Нет: current offline evidence может быть contaminated continuity/preview/override gaps; owner decision должен сначала принять bounded correction set.
15. **Готово ли оно архитектурно к Vision после PLAN-10C?** Нет. PLAN-10C решит shortlist/budget/dedup, но дополнительно нужны VA-NEW-02/04/05/08 и единый post-review decision invariant.

### TOP 15 NEW FINDINGS

| Rank | Severity | Finding | User-visible impact | Production reachable? | Existing PLAN owner | Recommended timing |
|---:|---|---|---|---|---|---|
| 1 | P1 | VA-NEW-03 hidden technical selector | manual/off-type/wrong semantic winner | config-reachable, default off | 9C-2/9E | до 9D-D/activation |
| 2 | P1 | VA-NEW-02 stale source preview | evidence о старых bytes | default local path | 9A/9E | до Vision/LIVE |
| 3 | P1 | VA-NEW-08 no resume fingerprints | молча старый winner/config | default resume | 9A | до LIVE resume |
| 4 | P1 | VA-NEW-09 strict render TOCTOU | render unapproved current snapshot | cross-stage mutation | 9E | до LIVE render |
| 5 | P1 | VA-NEW-04 review A/B hybrid | review/attribution не того asset | download replacement | 9A | до evidence/UI acceptance |
| 6 | P1 | VA-NEW-05 Vision tags drop | final asset теряет observed evidence | Vision+remote | 9A/9E | до Vision |
| 7 | P1 | VA-NEW-01 continuity self-evidence | false missing scene | default data-dependent | 9D | до 9D-D |
| 8 | P1 | VA-NEW-06 mixed partial loss | меньше/хуже candidate pool | mixed + failure | 10B | до LIVE-5 |
| 9 | P1 | VA-NEW-12 uncapped request budget | slow/rate-limited/costly run | default with network | 10C | до provider LIVE-5 |
| 10 | P1 | VA-NEW-14 non-replayable provenance | нельзя доказать why winner | default | 9A | до production observability |
| 11 | P1 | VA-NEW-07 media index not saved | повторный download, нет reuse | default successful download | 10D | planned 10D |
| 12 | P2 | VA-NEW-10 R² retries | 9 calls вместо 3 | retryable download failure | 10B | до LIVE-5 |
| 13 | P2 | VA-NEW-11 NASA 1+2N/atomicity | latency/lost good results | NASA routed | 10B | до broad NASA use |
| 14 | P2 | VA-NEW-13 capability parity lies | неравное ranking/filter behavior | default provider routing | 10B | provider contract slice |
| 15 | P2 | VA-NEW-15 reuse carries old semantics | чужое rationale в target scene | draft/manual reuse | 9A | до reuse UI |

### TOP 10 THINGS THAT LOOK WRONG BUT ARE ACTUALLY CORRECT

| Rank | Thing | Why it is correct |
|---:|---|---|
| 1 | `draft_complete` renders partial support | это explicit draft semantics; rights/must-avoid остаются hard blocks, publish-ready всегда false |
| 2 | Vision code существует при disabled config | backend/evaluation capability отделена от activation; paid/network gates не позволяют silent call |
| 3 | canonical ranker не использует `search_query` как evidence | query доказывает intent, не содержание result; это правильная 9C-3 boundary |
| 4 | unknown/review license не используется автоматически | fail-closed rights policy важнее recall |
| 5 | mixed retrieval спрашивает image и video | после symmetry это correct coverage; проблема только в budget/error composition |
| 6 | generated infographic не имеет внешней stock license | bytes project-generated, с spec fingerprint/provenance/checksum; внешний provider license не нужен |
| 7 | cached preview проверяется по собственному checksum | это правильно для cache corruption; дополнительно нужен source linkage |
| 8 | download допускает пустой Content-Type | bounded bytes затем decode/technical validate; это не само по себе render bypass |
| 9 | manual replacement помечает downstream stale | current replacement API делает нужную invalidation и rights/checksum validation |
| 10 | tolerant old-manifest reader остаётся | resume compatibility нужна; исправлять следует semantic admission gate, не удалять reader вслепую |

### Краткий отчёт владельцу

- **Baseline:** HEAD/origin `7e9b34a7e9809d66831ee4100d5177c58eca1e2e`; known docs-only line-limit failure отделён.
- **Audit artifact:** `docs/audits/VISUAL_ASSET_INTEGRITY_AUDIT_2026-08-10.md`.
- **Findings:** P0=0, P1=11, P2=10, P3=0.
- **TOP 5:** hidden technical selector; stale source preview; resume without fingerprints; strict render TOCTOU; review A/B hybrid.
- **Что реально новое:** cross-representation/source-snapshot defects, partial mixed-media failure atomicity, unsaved current media index, quantified nested/provider request fan-out, continuity self-evidence outside canonical ranker.
- **До LIVE-5:** bounded corrections 01–06, 08–10/12 и targeted transition tests; никакой сети до отдельного разрешения.
- **Можно отложить:** PLAN-10D matcher convergence/identity migration, generated infographic validation, redirect hardening, legacy retirement — при сохранении current disabled/limited reachability.
- **Нужен owner decision:** принять blocking set перед PLAN-9D-D и назначить два proposed `NO OWNER` slices; новый PLAN ID не требуется автоматически.
- **Git status после artifact:** `## governance-reset...origin/governance-reset`, `?? .codex-remote-attachments/`, `?? docs/audits/VISUAL_ASSET_INTEGRITY_AUDIT_2026-08-10.md`.
- **Final QA:** targeted radius 247 tests OK; `tools.qa.check_agent_docs` exit 0 с informational freshness notes; standalone whitespace check clean. `START_HERE.md` всё ещё 102 строки — известный CI baseline не изменён.
- **Изменения:** production code, tests, config, current PLAN metadata, protected assets и user projects не менялись. Commit/push не выполнялись.
