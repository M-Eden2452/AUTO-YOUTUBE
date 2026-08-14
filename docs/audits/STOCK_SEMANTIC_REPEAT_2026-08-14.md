---
status: current
audit_date: 2026-08-14
audit_head: b4f7225dcc9845975d25d0ed23ed1ec7ec88b73e
working_branch: governance-reset
---

# STOCK semantic repeat

This document is diagnostic evidence, not an execution plan. Current routing and
implementation truth live in `docs/current/`.

## Scope and safety

The run used the canonical `python -m ai_youtube create` path with exactly four
network actions approved: `semantic_brief`, `provider_search`, `asset_download`,
and `preview_download`. The standing semantic paid policy was enabled temporarily;
the repository default was restored byte-for-byte after the run. TTS, Vision,
render, subtitles, and quality checks were not authorized or executed.

The canonical command could not originally see repository `.env` before
`visual_plan`, so the run used `python -m dotenv run --` as a no-code workaround.
That wiring defect and the missing persisted usage summary are repaired by the
bounded correction recorded in the active execution plan.

## Result

Project:
`projects/2026-08-14_solnechnaya-panel-lovit-svet-tolko-dnem-nochyu-3`.

All five scenes received accepted provider-language semantic briefs. That proves
five successful planning-stage calls under the one-call-per-eligible-scene
contract. It does not prove the total number of calls in the run: draft
completion executed two additional replans, and the pre-repair artifacts stored
no counter for them.

Provider retrieval became live instead of stopping at `query_translation_required`: the manifest contains 125 completed search attempts, all with `query_language: en`, plus three successful download records for the selected assets. The searches returned 678 results and recorded no provider error.

The run stopped at the paid voice gate. No narration WAV, subtitles, MP4, or
quality report exists. Read-only `project status --json` confirms `visual_plan`
and `asset_search` completed, `voice` blocked, and downstream stages pending.

## Selection and rights

Three of five scenes received a slot; `scene_002` and `scene_004` remained
unresolved. All three selected assets are unique images. `video_slots=0` does not
mean retrieval found no video: video candidates existed, but the current ranking
preferred higher-scoring images.

Read-only `project rights-report --json` confirms all three selected items are
verified, licensed, have source pages, checksums, and local files. Overall rights
status remains blocked only because two scenes have no asset.

The diagnostic proves that model-assisted provider-language briefs removed the
language gate. It does not prove publish readiness: coverage is 3/5, no video was
rendered, and no quality gate ran.

## Follow-up implemented

The production backend now reads only `OPENAI_API_KEY` from repository `.env`, and only after both paid and network gates pass. A process-owned value keeps precedence; neighbouring provider and TTS secrets are not copied into the process environment. If the key is still absent, the explicitly approved path emits a visible `semantic_brief_unavailable` warning instead of silently returning to the deterministic plan.

The existing backend `usage_summary()` now has a production caller. The localized visual-plan artifact persists cumulative secret-free counters under `planning_metadata.semantic_brief_usage`, including backend, model, attempts, the per-adapter ceiling, and estimated cost. Draft-completion replans add their usage to that record; `master_visual_plan.json` remains the planning-stage snapshot. Existing readers remain tolerant and the default fail-closed configuration is unchanged.
