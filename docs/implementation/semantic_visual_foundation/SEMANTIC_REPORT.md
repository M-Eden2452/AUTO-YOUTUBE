# Semantic Visual Reranking Foundation Report

## Baseline

- Branch: `master`
- Commit before implementation: `adb40fa944318646aef66102cbb1352e40b7cacc`
- Started at: `2026-07-23T12:23:39.1139242+03:00`
- Completed at: `2026-07-23T12:41:27.7689638+03:00`
- Real media index SHA-256 before and after: `61B2C5B89F353659ACD48E299DEA3CE6478F28FA968B9149E615DD2051A30385`

## Implemented Architecture

The semantic foundation is additive and consumes the existing visual review bundle:

```text
visual_review_manifest sampled frames
-> SceneVisualRequirements adapter
-> SemanticVisualRequest
-> SemanticVisualBackend Protocol
-> deterministic mock or disabled external boundary
-> SemanticVisualResult validation
-> aggregation rules
-> semantic cache
-> review bundle and HTML enrichment
```

The default mode is `analyse_and_report`. `semantic_rerank_enabled` is false by default and no production selection logic uses semantic scores.

## Created Components

- `src/assets/semantic_visual_models.py`: requirements, request, frame reference, frame observation, aggregate scores, term checks, evidence, structured result, validation and aggregation rules.
- `src/assets/semantic_visual_backend.py`: provider-neutral backend Protocol, capabilities and health models.
- `src/assets/semantic_visual_cache.py`: stable SHA-256 cache key and atomic JSON result cache.
- `src/assets/semantic_visual_mock.py`: deterministic offline mock backend with good/mismatch/negative/low-confidence/timeout/invalid fixtures.
- `src/assets/semantic_visual_external.py`: disabled future external backend adapter with paid/budget/config gates and no live calls.
- `src/assets/semantic_visual_service.py`: manifest-driven semantic analysis service, cache orchestration, enrichment and inspect summary.
- `config/semantic_visual.json`: disabled-by-default semantic configuration.

## Review Integration

`src/assets/review_bundle.py` now supports optional candidate-level `semantic_analysis`, `semantic_rank`, `semantic_score`, `semantic_status` and `semantic_review_required` fields. Existing metadata, technical, crop and duplicate fields are preserved.

The static HTML board renders a semantic block only when semantic analysis exists. It shows confidence, semantic score, subject/action/environment scores, must-have terms, negative findings, mismatch reasons and evidence summaries. It does not render raw provider responses, secrets or absolute local paths.

## Aggregation Rules

Aggregation is implemented in `apply_semantic_aggregation_rules()`:

- Uses multiple frame observations when available; a single frame marks temporal evidence as limited for video.
- Caps action match at `0.65` when only one frame is available for an action scene.
- Must-have failures with low confidence become review-required, not automatic proof.
- High-confidence negative findings become hard rejects only when confidence reaches the configured hard-reject threshold and the evidence is consistent across frames.
- Low-confidence or single anomalous negative observations become review-required instead of destroying an otherwise good candidate.
- Failed, timeout or invalid analysis returns a structured fallback result with `semantic_score=0.0`; production ranking can continue from technical/metadata scores.

## Cache

The default project cache is:

```text
projects/<project_id>/assets/semantic_cache/
```

The fallback root is:

```text
assets/cache/semantic_visual/
```

Cache keys include backend, model, backend version, request schema version, normalized scene requirements, candidate id, provider, frame SHA-256/perceptual hashes, semantic configuration and prompt/template version. Writes use `.part` plus atomic replace. Reads invalidate missing, corrupted, mismatched or out-of-range structured results. Cache records store result JSON and frame references/hashes only; no secrets or base64 images are stored.

## CLI

Added:

```powershell
python -B pipeline.py semantic-visual analyse --project-id <project-id> --scene-id <scene-id> --backend mock
python -B pipeline.py semantic-visual inspect --project-id <project-id>
```

Options: `--all-scenes`, `--refresh`, `--offline`, `--maximum-candidates`, `--maximum-frames`, `--no-html`.

The CLI does not permit paid Vision calls. Non-mock backends are routed to the disabled external boundary and return configuration errors unless future explicit gates are implemented.

## Test Evidence

- Red TDD check: `Ran 32 tests`, expected `FAILED (failures=1, errors=30)` before implementation.
- Semantic targeted tests: `Ran 32 tests in 2.196s - OK`.
- Preview tests: `Ran 45 tests in 4.271s - OK`.
- Provider/news/quality tests: `Ran 65 tests in 69.551s - OK`.
- Full unittest discovery: `Ran 211 tests in 74.693s - OK`.
- Import checks: `semantic imports ok`.
- Config validation: `semantic config json ok`.
- CLI smoke: `successful_analyses=1`, `paid_calls_performed=False`.
- HTML scan: no secrets, no temp root and no Windows absolute paths.

## Safety Confirmations

- Live Vision calls performed: no.
- Paid API calls performed: no.
- OpenAI/Gemini/Claude live calls performed: no.
- Automated Envato download performed: no.
- Scraping performed: no.
- Real `assets/library/metadata/media_index.json` modified: no.
- Production selection changed: no.

## Remaining Issues

- The mock backend is fixture-driven and intentionally non-semantic.
- The external backend is a disabled boundary for part two; it performs no live requests.
- Semantic rerank exists only as a configuration concept and is not wired into production selection.

## Readiness

The foundation is ready for controlled semantic backend evaluation in the next stage.
