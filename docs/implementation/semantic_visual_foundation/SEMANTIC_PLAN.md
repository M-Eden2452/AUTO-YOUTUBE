# Semantic Visual Reranking Foundation Plan

> Created before production-code changes for the semantic visual foundation stage.

## Goal

Add a provider-neutral semantic analysis layer that consumes existing sampled frames from the visual review bundle, stores strict structured semantic observations, caches deterministic results, enriches the review bundle and HTML board, and leaves production asset selection unchanged by default.

## Baseline

- Working directory: `G:\Projects\AI-YouTube`
- Current branch: `master`
- Commit hash before implementation: `adb40fa944318646aef66102cbb1352e40b7cacc`
- Started at: `2026-07-23T12:23:39.1139242+03:00`
- Real media index SHA-256 before implementation: `61B2C5B89F353659ACD48E299DEA3CE6478F28FA968B9149E615DD2051A30385`
- Production semantic rerank default: disabled
- Paid Vision calls: forbidden
- Live Vision calls: forbidden

## Target Flow

```text
scene requirements
-> sampled frames from visual review bundle
-> semantic analysis request
-> semantic backend
-> structured frame observations
-> candidate semantic aggregate
-> mismatch and negative-term checks
-> semantic cache
-> semantic review result
-> review bundle enrichment
-> optional future semantic rerank
```

## Planned Files

- Create `config/semantic_visual.json` for disabled-by-default semantic settings.
- Create `src/assets/semantic_visual_models.py` for dataclass models, validation and current-schema adapter.
- Create `src/assets/semantic_visual_backend.py` for provider-neutral Protocol and backend health/capability types.
- Create `src/assets/semantic_visual_cache.py` for stable SHA-256 cache keys, atomic JSON writes and invalidation.
- Create `src/assets/semantic_visual_mock.py` for deterministic offline fixture-driven backend behavior.
- Create `src/assets/semantic_visual_external.py` for disabled paid-backend boundary with explicit budget gates.
- Create `src/assets/semantic_visual_service.py` for bundle-driven semantic analysis and enrichment.
- Modify `src/assets/review_bundle.py` to accept optional semantic analysis fields and render a safe HTML section.
- Modify `src/assets/__init__.py` to export semantic foundation APIs.
- Modify `src/news/asset_manager.py` to pass semantic config into review integration without changing selection.
- Modify `pipeline.py` to add `semantic-visual analyse` and `semantic-visual inspect`.
- Add focused unittest coverage in `tests/test_semantic_visual_foundation.py` and `tests/test_semantic_visual_integration.py`.

## TDD Order

1. Write failing tests for model serialization, adapter mapping, request/result validation and score ranges.
2. Implement the minimal semantic dataclasses and validation helpers.
3. Write failing tests for cache key stability, cache hit, corruption and Unicode paths.
4. Implement semantic cache.
5. Write failing tests for mock backend behaviors and aggregation rules.
6. Implement backend Protocol, mock backend, external disabled skeleton and aggregation.
7. Write failing tests for review bundle enrichment, HTML safety, CLI analyse/inspect, offline cache-only mode and selection stability.
8. Implement service, review bundle hooks and pipeline CLI.
9. Run targeted, preview, provider/news/quality, full discovery, import, config, CLI, HTML and media-index checks.

## Safety Rules

- Do not read or report `.env`.
- Do not mutate `assets/library/metadata/media_index.json`.
- Do not perform network, paid Vision, OpenAI/Gemini/Claude, Envato download or scraping calls.
- Do not enable semantic rerank by default.
- Do not switch branches, commit, reset, clean or destructively checkout.
- Do not add heavy ML dependencies.

## Completion Criteria

- Models, backend contract, cache, mock backend, aggregation rules, service, review integration, HTML section, CLI and reports are implemented.
- All requested tests pass using mock fixtures only.
- `analyse_and_report` leaves selected candidates unchanged.
- External backend is blocked by default and with zero budget.
- `SEMANTIC_SNAPSHOT.json` marks `ready_for_semantic_backend_evaluation=true`.
