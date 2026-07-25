# VoicePolicy

`src/audio/voice_policy.py`. A dataclass with 19 fields governing how voice/narration is
generated for a given project/format/template/localization.

## Fields

`enabled, required, provider, voice_profile, language, model_id, output_mode,
timing_mode, approval_required, audition_required, scene_level_generation, reuse_cache,
pause_policy, post_processing, fallback_policy, failure_policy, output_format,
target_sample_rate, target_channels, loudness_target, peak_limit, speed,
provider_settings, notes`.

## Enums

- `output_mode`: `single_narration | scene_audio | manual_audio | disabled`
- `timing_mode`: `narration_driven | visual_driven | fixed_duration | adaptive`
- `fallback_policy`: `none | manual_audio | local_tts | local_stub_only_for_tests`

Invalid values raise `VoicePolicyError` at construction time.

## Resolution (4-layer precedence)

`resolve_voice_policy(channel_defaults, template_defaults, project_overrides,
localization_overrides)` merges four plain dicts of field overrides in order — each
later layer's non-`None` values win over the earlier ones; unset (`None`) entries never
reset a field a previous layer already set. This never touches the dataclass internals
of `ChannelProfile`/`ProjectManifest`/`TemplateDefinition` — all four layers are read via
plain `dict.get()`, so existing `ChannelProfile`/`ProjectManifest` JSON on disk is
untouched and remains backward compatible.

- **Channel layer**: `voice_policy_from_channel_config(channel_voice_config,
  channel_workflow_config)` adapts the existing `channels/<id>/channel_config.json`
  `"voice"`/`"voice_workflow"` keys (and `voices.yaml`) — no changes to that file's shape.
  `voice_workflow.never_auto_fallback_to_paid: true` → `fallback_policy: "none"`.
- **Template layer**: `AUDIO_POLICY_DEFAULTS[template.audio_policy_id]`, a small in-code
  lookup table in `voice_policy.py` (kept out of `src/production_catalog` so that package
  never has to import `src/audio` — the catalog only stores the string id).
  `fullscreen_voiceover_default` → `enabled/required=True, output_mode=scene_audio,
  timing_mode=narration_driven, scene_level_generation=True`. `story_card_no_voice` →
  `enabled=False, output_mode=disabled`.
- **Project layer**: reserved for `ProjectManifest.metadata["voice_policy_overrides"]`
  (same free-form-dict convention `ChannelOutputPolicy.validate()` already uses for
  `has_voiceover`/`resolution`/etc.) — not populated by News (which has no
  `ProjectManifest`), but ready for Project Foundation-backed formats.
- **Localization layer**: reserved for per-language overrides (e.g. a future
  `voice_selection.json` override); News doesn't populate this layer yet.

## Per-format policy (current)

| Format/template | output_mode | timing_mode | scene_level_generation | approval_required |
|---|---|---|---|---|
| `story_card_text_only_v1` | `disabled` | `visual_driven` | `False` | n/a |
| `fullscreen_voiceover_v1` (News-to-Short) | `scene_audio` | `narration_driven` | `True` | `True` |
| `longform` (not wired yet) | intended `scene_audio` with chapter grouping | `adaptive` | `True` | `True` |
| `horizontal_clip` (not wired yet) | intended `manual_audio`/`scene_audio` | `visual_driven` or `fixed_duration` | configurable | configurable |

## Safety invariant

`fallback_policy` never permits an automatic ElevenLabs → fake-silence fallback in
production. `local_stub_only_for_tests` is a real enum value precisely so the intent is
explicit and greppable — nothing in this stage sets it outside test fixtures.
