# OpenAI Semantic Visual Backend Plan

> Created before production-code changes for the OpenAI semantic backend and evaluation harness stage.

## Baseline

- Working directory: `G:\Projects\AI-YouTube`
- Current branch: `master`
- Commit hash before implementation: `adb40fa944318646aef66102cbb1352e40b7cacc`
- Started at: `2026-07-23T12:55:55.4349862+03:00`
- Real media index SHA-256 before implementation: `61B2C5B89F353659ACD48E299DEA3CE6478F28FA968B9149E615DD2051A30385`
- Production semantic rerank default: disabled
- Paid Vision calls: forbidden for this stage
- Live Vision calls: forbidden for this stage

## Goal

Add a disabled-by-default OpenAI `SemanticVisualBackend` adapter that uses the official Python SDK Responses API behind a strict budget guard, produces the existing `SemanticVisualResult` schema, and ships a safe evaluation harness that runs only mock and mocked OpenAI responses during this stage.

## Architecture

```text
SemanticVisualRequest
-> OpenAI request builder
-> VisionBudgetGuard
-> optional mocked/live OpenAI Responses client
-> structured output adapter
-> SemanticVisualResult validation
-> existing aggregation rules
-> cache/service/evaluation harness
```

## Planned Files

- Create `src/assets/semantic_visual_openai.py` for OpenAI config, detail policy, request builder, budget guard, retry logic, usage metadata and adapter.
- Create `src/assets/semantic_visual_evaluation.py` for mock-only dataset loading, dry-run request checks, mocked evaluation and metrics.
- Create `config/semantic_visual_eval.json` for offline evaluation cases.
- Modify `config/semantic_visual.json` to add disabled OpenAI settings without changing production selection.
- Modify `src/assets/semantic_visual_service.py` to construct the OpenAI backend when explicitly requested.
- Modify `src/assets/__init__.py` to export the new modules if an export pattern already exists.
- Modify `pipeline.py` to add `semantic-backend diagnostics` and `semantic-backend evaluate`.
- Add focused tests in `tests/test_semantic_visual_openai_backend.py` and `tests/test_semantic_visual_evaluation.py`.
- Create reports in `docs/implementation/openai_semantic_backend/`.

## TDD Order

1. Write failing OpenAI backend tests for Protocol conformance, request frames, redaction, structured mapping, fallback errors, retry behavior, budget blocking and detail policy.
2. Implement the minimal OpenAI adapter, request builder, budget guard and schema adapter to pass the backend tests without network.
3. Write failing evaluation tests for dataset loading, metrics, dry-run, cache compatibility and selection immutability.
4. Implement the evaluation harness and CLI commands.
5. Run targeted tests, existing semantic tests, preview tests, provider/news tests, full discovery, import checks, config checks, CLI diagnostics, dry-run evaluation and safety scans.

## Safety Rules

- Do not execute real OpenAI API requests.
- Do not perform paid calls or reveal `OPENAI_API_KEY`.
- Do not enable semantic rerank or change production selection.
- Do not mutate `assets/library/metadata/media_index.json`.
- Do not store base64 image data in cache, reports, manifests or diagnostics.
- Do not store raw provider responses.
- Do not send license proof or full project manifests.
- Do not use `detail=auto` or `detail=original`.

## Completion Criteria

- OpenAI adapter is implemented and disabled by default.
- Responses API request construction and structured output schema are covered by mocked tests.
- Budget guard blocks live calls unless all future explicit CLI gates are present.
- Evaluation harness supports the requested case taxonomy and metrics without modifying production manifests.
- Diagnostics and dry-run commands work without network and never print secrets.
- Snapshot reports `ready_for_controlled_live_evaluation=true` with no live or paid calls performed.
