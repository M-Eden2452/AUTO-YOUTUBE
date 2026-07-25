# Migration Notes — Remaining Duplicate Debt

Stage 2D deliberately did not touch two existing voice implementations. Both keep
working exactly as before; this note records why and what a future migration would
involve.

## `src/voice_engine.py` (legacy/general pipeline)

Used only by the non-News `pipeline.py` path (`--reuse-voice`/`--skip-voice`/
`--test-moss-tts`/`--test-moss-voices` flags, `build_voice_manifest` /
`apply_voice_timing_to_scene_plan` / `align_voice_manifest_to_scene_plan`, imported at
`pipeline.py:23`, called at `pipeline.py:538-542`). It already has scene-level synthesis,
MOSS-TTS-Nano fallback, and a local stub provider — features this stage had to rebuild
in `src/audio/scene_voice_generator.py` and `src/audio/pause_policy.py` rather than reuse,
because `voice_engine.py` uses a different dict+sha1 cache format and is not
`voices.yaml`-driven (it reads channel video-config directly).

**Future migration path**: once the legacy pipeline needs the same adaptive/scene-level
behavior News-to-Short now has, `voice_engine.py`'s callers could be re-pointed at
`src/audio/narration_workflow.py` through a thin adapter analogous to
`src/news/voice_adapter.py`. The MOSS-TTS fallback and local stub provider would need a
`TTSProvider` wrapper (e.g. `MossTTSProvider`, `LocalStubProvider`) registered with
`TTSProviderManager`, and the local stub would need to set `VoicePolicy.fallback_policy =
"local_stub_only_for_tests"` explicitly wherever it's used outside tests, per the
project's rule that a local stub must never be mistaken for production voice. Not
attempted now — out of scope per the Stage 2D brief (`не трогай Anime Factory, Solar
project migration, repository cleanup`-adjacent instruction: legacy pipeline migration
was excluded).

## `project_solar_vs_nuclear/…/ensure_final_voice()`

`src/production_plan/solar_vs_nuclear_render.py:105-147`. Kept exactly as-is, per
instruction, as a **reference implementation only** — it already proved the
`TTSRequest` → `ElevenLabsProvider.synthesize()` → ffmpeg-mp3-to-wav pattern works
end-to-end for a real project. Known deviations from the new canonical path (intentionally
not backported into this one-off function):

- Bypasses `TTSProviderManager`'s approval gate entirely (calls
  `ElevenLabsProvider().synthesize(request)` directly).
- Cache check is file-existence + size ≥ 1024 bytes only, not a content/settings hash.
- Duration probe (`_probe_duration`) is a regex over `ffmpeg -i` stderr, not the
  `ffprobe -show_format` JSON call (`src/assets/frame_sampling.ffprobe_media_info`) the
  new `audio_assembler.py` uses.
- Hardcodes voice id, model id, and ElevenLabs settings inline rather than sourcing them
  from a `VoicePolicy`/`VoiceProfileRegistry`.

`src/audio/voice_manifest.read_voice_manifest()` was written to tolerantly parse this
function's exact manifest shape (see `tests/test_legacy_voice_manifest_compat.py`) so
that if the Solar project's manifest is ever read by shared tooling, it won't need a
separate reader.

**Future migration path**: replace the direct `ElevenLabsProvider()` call with
`narration_workflow.generate_final()` fed by a `NarrationRequest` built from the 12-scene
`scenes.json` already in that project (per-chapter grouping would use the same
`longform` `PausePolicy` defaults already added in `src/audio/pause_policy.py`). Not
attempted now — explicitly out of scope (`Solar project migration` is in the "do not
touch now" list).
