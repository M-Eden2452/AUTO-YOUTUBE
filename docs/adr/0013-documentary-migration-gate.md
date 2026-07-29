# ADR 0013: Close the documentary migration gate without a vertical slice

Date: 2026-07-29

Status: accepted

## Context

Stage 8E was conditional: create a documentary application boundary only after
confirming a real working template. The read-only audit found no such template:

- the production catalog has no `documentary` application or template;
- `longform` is planned/disabled and has no registered template;
- `psychology`, `quotes`, `survival`, and `size_comparison` are legacy
  `pipeline.py --channel/--video` profiles and are deliberately unavailable to
  `content_creator`;
- the Solar vs Nuclear fixed production plan writes a bespoke
  `project_config.json`/`scenes.json` layout outside the two project contracts
  read by `ProjectRepository`;
- its render entrypoint directly loads `.env`, can invoke ElevenLabs, searches
  Pexels/Pixabay, downloads over HTTP, and has no application-level paid-action
  approval parameter.

Component and fixture tests cover parts of the legacy documentary engine and the
fixed plan, but they do not establish a catalog template, canonical application
service, compatible persisted project contract, or safely gated end-to-end
workflow.

## Decision

Do not create a documentary application boundary, register a documentary
template, enable `longform`, or copy the fixed-plan workflow into
`src.ai_youtube.apps`.

Close stage 8E as evaluated but not eligible for migration. Leave the legacy
documentary channels, fixed-plan entrypoints, project layout, and root
`pipeline.py` compatibility surface unchanged. Stage 8 is complete with the
four verified vertical slices already migrated.

A future documentary implementation is a new bounded product/application stage.
Before it can be registered or migrated it must demonstrate:

1. a real catalog template and application service;
2. reuse of an existing recognized project/storage contract;
3. the canonical provider contract and paid-action approval gates;
4. an explicit output/evidence contract and targeted workflow tests.

## Consequences

- No production code, schema, runtime project, media, or capability status
  changes in 8E.
- `tests/test_documentary_migration_gate.py` protects the current stop-gate and
  prevents legacy code presence from being mistaken for an active template.
- The Solar fixed plan remains a compatibility/experimental path behind the root
  facade; it is not represented as publish-ready.
- The next rescue work is stage 9, beginning with a fresh callers and
  compatibility audit of cleanup candidate D01.
