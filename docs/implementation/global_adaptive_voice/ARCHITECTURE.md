# Global Adaptive Voice and Audio Foundation — Architecture

Stage 2D. One adaptive voice/narration foundation shared by News-to-Short today, and by
vertical_short/longform/horizontal_clip/documentary/Video Repurposer/fullscreen templates
later, without a second TTS framework, a second `ElevenLabsProvider`, or a second
`TTSRequest`/`TTSResult`.

## Starting point: three parallel voice implementations

Before this stage, the repo had:

1. `src/audio/tts/*` + `src/audio/voice_workflow.py`/`voice_cli.py` — the best-designed
   layer (typed request/result, approval-gated, hash-based cache keys), but only handled
   one whole narration per localization. Its own `TTSProviderManager` approval gate
   (`src/audio/tts/provider_manager.py`) was defined but never called by anything.
2. `src/voice_engine.py` — an older, separate system for the legacy/general pipeline, with
   scene-level synthesis, MOSS-TTS fallback, and a local stub provider, using a different
   dict+sha1 cache format. **Untouched by this stage** (see MIGRATION_NOTES.md).
3. `project_solar_vs_nuclear/…/ensure_final_voice()`
   (`src/production_plan/solar_vs_nuclear_render.py:105-147`) — reused `ElevenLabsProvider`/
   `TTSRequest` directly but bypassed the approval gate and used a fragile regex duration
   probe. **Kept as an untouched reference implementation** (see MIGRATION_NOTES.md).

The News-to-Short voice stage (`src/news/voice_stage.py`) was a pure stub that never
called any TTS provider.

## Canonical layer boundaries

| Layer | Location | Responsibility |
|---|---|---|
| Provider | `src/audio/tts/*` (existing, minimally extended) | `preflight()`/`synthesize()`/provider API/normalized `TTSResult` only |
| Voice workflow | `src/audio/voice_workflow.py` (untouched) + `src/audio/narration_workflow.py` (new) | profile selection, approval, audition, scene generation, cache, assembly, manifests, statuses, validation |
| Project adapter | `src/audio/voice_policy.py` (new) | links workflow to Channel/Project/format/template policy via plain dicts, no schema changes |
| News adapter | `src/news/voice_adapter.py` (new) + `src/news/voice_stage.py` (extended) | converts News script/scenes into the common `NarrationRequest` |
| Render adapter | none needed | `src/news/final_renderer.py` already only reads `voice_manifest["audio_path"]` |

## New modules (`src/audio/`)

- **`voice_policy.py`** — `VoicePolicy` dataclass (19 fields), `resolve_voice_policy()`
  (4-layer precedence: channel < template/format < project < localization),
  `voice_policy_from_channel_config()` (adapts the existing `voices.yaml`/
  `channel_config.json` shape), `AUDIO_POLICY_DEFAULTS` (keyed by
  `TemplateDefinition.audio_policy_id`).
- **`voice_profile_registry.py`** — `VoiceProfileRegistry` wrapping the existing
  `load_voice_profiles()`; resolves a query via exact `profile_id` → alias table
  (`"дом"`/`"dom"` → `ru_dom`) → case-insensitive `display_name`.
- **`narration_models.py`** — `NarrationScene`/`NarrationRequest`, `compute_generation_key()`
  (built on `compute_tts_cache_key`, not a duplicate hash), `build_narration_request_from_scenes()`.
- **`scene_voice_generator.py`** — per-scene synthesis + cache engine; the first real
  caller of `TTSProviderManager`. One synth attempt per scene, one retry only for
  `ConnectionError`/`Timeout`, never for an ambiguous HTTP status. A failing scene is
  recorded `generation_status="failed"` without aborting the batch.
- **`pause_policy.py`** — `PausePolicy` + per-format defaults, `silence_wav_bytes()`
  (audio-level silence, no SSML).
- **`audio_assembler.py`** — `assemble_narration()`: ffmpeg concat + pauses + resample,
  duration-validated via `src/assets/frame_sampling.ffprobe_media_info`, checksum + atomic
  `os.replace()`. `PostProcessingConfig` (loudnorm/peak-limit/etc., **disabled by default**
  — genuinely new ffmpeg-filter territory for this repo). `apply_compression()` is an
  explicit `NotImplementedError` stub, not a silent no-op.
- **`voice_manifest.py`** — `build_voice_manifest()` (schema_version=2, always sets a
  legacy-compatible `audio_path`/`status`) and `read_voice_manifest()` (tolerant reader
  that normalizes schema-less legacy manifests).
- **`narration_workflow.py`** — orchestrator: `EXTENDED_VOICE_STATES` (extends, never
  mutates, `voice_workflow.VOICE_STATES`), `prepare_final()`, `generate_final()`,
  `invalidate_scenes()`, `validate_output()` (the completed-gate).

## News-to-Short wiring

`src/news/voice_adapter.py` maps `script["scenes"]` (confirmed shape: `scene_id,
start_sec, target_duration_sec, narration, claim_ids, visual_intent, on_screen_text,
emotion`) into a `NarrationRequest`, resolves the channel's `VoicePolicy` (using
`fullscreen_voiceover_default` as the template layer, since News-to-Short's rendered
output already matches that template's contract even though News jobs don't carry a
`production_catalog` `template_id` today), and resolves the `VoiceProfile` via the
registry.

`src/news/voice_stage.py::build_or_generate_voice_manifest()` is a compatibility shim:
`build_safe_voice_manifest()` is untouched and is what still runs whenever
`execute=False` or no approval is on record — byte-identical to today's behavior. Only
when `execute=True` **and** a matching approval exists does it call
`narration_workflow.generate_final()`. `src/news/pipeline.py`'s `"voice"` stage dispatch
threads a new `execute_voice: bool = False` parameter through `run_news_to_short_job` →
`_run_stage` → `_dispatch_stage`; the default preserves all current behavior.
`src/news/final_renderer.py` was **not modified** — it already only reads
`voice_manifest["audio_path"]`.

## Production Catalog

One new `TemplateDefinition("fullscreen_voiceover_v1", requires_voice=True, ...)`
registered in `src/production_catalog/catalog.py`, reusing the existing News
`final_renderer` via `workflow_binding` — no new renderer. `story_card_text_only_v1`
stays `requires_voice=False`, unchanged.
