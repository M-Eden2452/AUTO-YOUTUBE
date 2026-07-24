# OpenAI Semantic Vision Backend Report

## Summary

This stage adds a disabled-by-default OpenAI semantic visual backend and an offline evaluation harness. It uses the existing `SemanticVisualBackend` Protocol, `SemanticVisualRequest`, `SemanticVisualResult`, semantic cache and aggregation rules.

No live OpenAI calls were performed. No paid API calls were performed. Production selection and semantic rerank defaults were not changed.

## Implemented Backend

- Created `src/assets/semantic_visual_openai.py`.
- Added `OpenAISemanticVisualBackend` with Protocol-compatible `capabilities()`, `health_check()` and `analyse_candidate()`.
- Uses the official Python SDK entry point lazily through `from openai import OpenAI` and calls the Responses API through `client.responses.create(...)`.
- Supports multiple sampled frames from existing `SemanticFrameReference` objects.
- Converts local sampled frames to data URLs only inside request construction.
- Keeps base64 out of diagnostics, cache, manifests and reports.
- Uses strict structured output with the existing `SemanticVisualResult` schema.
- Maps OpenAI structured output to `SemanticVisualResult`, then runs existing validation and aggregation.
- Returns existing structured fallback results for refusal, incomplete, empty output, invalid schema, timeout, rate limit, auth, permission, bad request, server and unexpected errors.

## Request Builder

`OpenAIRequestBuilder` is separate from HTTP execution. It builds:

- system instruction;
- visible-data-only analysis rules;
- scene requirements and semantic strictness;
- candidate metadata after existing public sanitization;
- sampled frame markers with frame index, timestamp and poster-frame flag;
- technical context;
- strict JSON Schema for `SemanticVisualResult`.

It does not include full project manifests, API keys, absolute paths, license certificates, raw provider responses or irrelevant provenance.

## Detail Policy

The first pass is deterministic:

- maximum 3 frames by default;
- `detail=low`;
- maximum 3 candidates per scene by default;
- `analyse_and_report` only.

`detail=high` escalation is implemented as a future deterministic decision and covered by mocked tests. `detail=auto` and `detail=original` are not allowed by default.

## Budget Guard

`VisionBudgetGuard` blocks calls unless all future live gates pass:

- `allow_paid_vision=true`;
- explicit CLI allow flag;
- non-zero configured and CLI budget;
- non-zero configured and CLI call limit;
- confirmation phrase `LIVE_VISION_APPROVED`;
- allowlisted model;
- allowed detail;
- candidate/frame limits;
- projected request count and budget within project limits.

Default config blocks everything: OpenAI backend disabled, paid calls false, budget zero and call limit zero.

## Evaluation Harness

Created `src/assets/semantic_visual_evaluation.py` and `config/semantic_visual_eval.json`.

The harness supports mock backend and mocked OpenAI responses for future `gpt-5.6-terra` and `gpt-5.6-luna` comparisons. It covers 14 cases:

- correct subject/action/environment;
- wrong subject;
- wrong action;
- wrong location;
- exact entity mismatch;
- missing must-have;
- negative element present;
- generic acceptable B-roll;
- one misleading frame;
- poster-only video;
- low confidence;
- strict scene;
- balanced scene;
- illustrative scene.

Metrics include subject/action/environment accuracy, must-have precision/recall, negative precision/recall, hard-reject false-positive rate, review-required rate, structured-output validity, cache hit rate, latency, estimated cost and score stability.

## CLI

Added:

```powershell
python -B pipeline.py semantic-backend diagnostics --backend openai
python -B pipeline.py semantic-backend evaluate --backend openai --model gpt-5.6-terra --dry-run
python -B pipeline.py semantic-backend evaluate --backend openai --model gpt-5.6-terra --mocked
```

Diagnostics does not check live network status and does not print the API key. Dry-run builds requests, validates images, checks schema and budget guard, and reports projected calls/images plus live-call block reasons.

## Verification Summary

- New mocked OpenAI/evaluation tests: `Ran 35 tests in 3.126s - OK`.
- Existing semantic foundation/integration tests: `Ran 32 tests in 2.241s - OK`.
- Visual preview tests: `Ran 45 tests in 4.726s - OK`.
- Provider/news tests: `Ran 65 tests in 69.152s - OK`.
- Full unittest discovery: `Ran 246 tests in 72.969s - OK`.
- Import checks: `semantic openai imports ok`.
- Config checks: `semantic openai configs json ok`.
- Diagnostics: key shown only as configured true/false.
- Dry-run: projected calls `14`, projected image count `40`, live calls blocked.
- Media index SHA-256 after implementation: `61B2C5B89F353659ACD48E299DEA3CE6478F28FA968B9149E615DD2051A30385`.

## Safety Confirmations

- Live Vision calls performed: no.
- Paid API calls performed: no.
- `OPENAI_API_KEY` printed or stored: no.
- Base64 persisted in cache/reports/manifests: no.
- Real `media_index.json` modified: no.
- Production selection changed: no.
- Semantic rerank enabled: no.

## Remaining Issues

- Real OpenAI model behavior, pricing and availability were not validated because live calls are prohibited in this stage.
- The local interpreter used for tests did not import the OpenAI SDK; the dependency is declared in `requirements.txt`, and the adapter imports it lazily only for future gated live calls.
