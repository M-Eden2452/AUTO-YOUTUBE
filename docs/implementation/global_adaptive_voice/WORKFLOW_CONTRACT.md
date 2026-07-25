# Narration Workflow Contract

## Lifecycle

`src/audio/voice_workflow.VOICE_STATES` (unchanged, 12 values):

```
unconfigured -> draft_ready -> provider_selection_required -> audition_confirmation_required
-> audition_generating -> awaiting_voice_approval -> voice_approved | voice_rejected
-> final_confirmation_required -> final_generating -> completed | failed
```

`src/audio/narration_workflow.EXTENDED_VOICE_STATES` extends this list (does not mutate
or reorder it) with four scene-level-generation statuses actually produced by
`generate_final()`: `partially_completed`, `blocked`, `manual_audio_ready`, `skipped`.

`generate_final()` returns:
- `"skipped"` — policy `output_mode == "disabled"` or `enabled == False`; no provider call.
- `"partially_completed"` — one or more scenes failed; narration is **not** assembled;
  successfully generated scenes are preserved in the scene cache.
- `"completed"` — every scene succeeded; narration was assembled, checksummed, and
  atomically written.

## Approval binding

Approval (`VoiceApproval`, unchanged) is granted once against the **whole narration
text** (matching today's audition/approve UX — `create_voice_approval_record()` already
hashes the full script text passed to it), not per scene.
`narration_workflow.approval_covers_request()` builds one synthetic whole-script
`TTSRequest` from `NarrationRequest.full_text` + voice/model/language/settings and
reuses the existing `is_final_generation_approved()` unchanged. Any change to text,
voice, model, settings, or language invalidates it — verified in
`tests/test_narration_workflow.py::test_approval_invalidated_by_text_change`.

`generate_final()` raises `PermissionError` (no scenes touched, zero provider calls) when
`policy.approval_required` is true and the approval doesn't cover the request.
`scene_voice_generator.generate_scenes()` independently double-checks via
`TTSProviderManager.synthesize(..., approved=...)` before any paid scene call — this is
the first real caller of that previously-unused gate.

## Actions

| Action | Function | Paid call? |
|---|---|---|
| list/inspect profiles | `voice_profile_registry.VoiceProfileRegistry` | no |
| preflight | `narration_workflow.prepare_final()` (calls `provider.preflight()`) | no (ElevenLabs preflight is read-only, verified) |
| prepare final | `narration_workflow.prepare_final()` | no |
| generate final | `narration_workflow.generate_final()` | yes, gated on approval |
| import manual audio | `voice_workflow.import_manual_audio()` (unchanged) | no |
| invalidate scene(s) | `narration_workflow.invalidate_scenes()` | no |
| validate output | `narration_workflow.validate_output()` | no |

Audition (`voice_cli.py::_run_audition`, unchanged) keeps its existing 300-character cap.
`generate_final()` has no such cap — full scene/chapter text is used.

## Scene-level generation and caching

Layout: `projects/<project_id>/localizations/<language>/voice/scenes/scene_NNN.{mp3,json}`,
assembled `.../voice/narration.wav`. Each scene's sidecar JSON matches the schema in
`ARCHITECTURE.md`/spec item 7 exactly (`scene_id, scene_index, text, text_hash,
settings_hash, generation_key, provider, voice_profile, provider_voice_id, model_id,
language, output_path, duration_seconds, size_bytes, checksum_sha256,
generation_status, cache_hit, generated_at, error`).

`generation_key` (via `compute_generation_key()`, wrapping `compute_tts_cache_key`) folds
in normalized text, provider, voice id, model, language, settings, output format, speed,
and `post_processing_version` — changing any of these invalidates only that scene's cache
entry. `is_scene_cache_valid()` re-verifies the on-disk checksum before trusting a cache
hit, so a corrupted file is silently regenerated rather than trusted.

## Completed gate

`validate_output()` requires, in order: manifest exists → (optional) scene count matches
→ every scene `generation_status == "completed"` and its file exists → narration file
exists → narration `duration_sec > 0` → narration checksum matches the manifest. Any
failure returns `NarrationValidationResult(valid=False, reason=...)` rather than raising.
