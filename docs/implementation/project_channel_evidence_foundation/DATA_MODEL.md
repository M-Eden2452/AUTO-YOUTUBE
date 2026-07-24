# Stage 2B: Data Model Reference

All models live in `src/project_foundation/models.py` and are plain
`dataclasses` with `to_dict()` / `from_dict()` for deterministic JSON
serialization (`schema_version = 1` everywhere in this stage).

## ChannelProfile

Stored at `channels/<channel_id>/channel.json`.

| Field | Type | Default |
|---|---|---|
| `channel_id` | `str` (required, non-empty) | - |
| `display_name` | `str` | `channel_id` |
| `description` | `str` | `""` |
| `default_language` | `str` | `"ru"` |
| `supported_languages` | `list[str]` | `[default_language]` |
| `default_application` | `str` | `""` |
| `default_format` | `str` | `""` |
| `default_template` | `str` | `""` |
| `export_targets` | `list[str]` | `[]` |
| `branding` | `ChannelBranding` | see below |
| `output_policy` | `dict` (raw `ChannelOutputPolicy.to_dict()`) | `{}` |
| `created_at` / `updated_at` | ISO-8601 UTC `str` | now |
| `schema_version` | `int` | `1` |

`default_application` / `default_format` / `default_template` are plain
string ids (e.g. `"content_creator"`, `"vertical_short"`,
`"story_card_text_only_v1"`) matching the vocabulary used by
`src/production_catalog`, but this package does not import or depend on
that catalog.

### ChannelBranding

| Field | Default |
|---|---|
| `channel_name` | `""` |
| `logo_path` | `""` |
| `primary_font` | `""` |
| `secondary_font` | `""` |
| `default_music_policy` | `"optional"` |
| `default_voice_id` | `""` |
| `visual_style_notes` | `""` |

## ProjectManifest

Stored at `projects/<project_id>/project.json`.

| Field | Type | Default |
|---|---|---|
| `project_id` | `str` (required, non-empty) | - |
| `title` | `str` | `project_id` |
| `channel_id` | `str` | `""` |
| `application_id` / `format_id` / `template_id` | `str` | `""` |
| `language` | `str` | `"ru"` |
| `export_targets` | `list[str]` | `[]` |
| `status` | `str`, one of `PROJECT_STATUSES` | `"draft"` |
| `source_type` | `str` | `"manual"` |
| `source_reference` | `str` | `""` |
| `project_root` | project-relative `str` | `projects/<project_id>` |
| `localization_root` | project-relative `str` | `<project_root>/localizations/<language>` |
| `evidence_root` | project-relative `str` | `<project_root>/evidence` |
| `created_at` / `updated_at` | ISO-8601 UTC `str` | now |
| `schema_version` | `int` | `1` |
| `metadata` | `dict` | `{}` |

`PROJECT_STATUSES`: `draft`, `prepared`, `assets_ready`, `audio_ready`,
`render_ready`, `rendered`, `qc_passed`, `exported`, `archived`, `failed`.
Any other value raises `ProjectFoundationError`.

`metadata` is where optional, not-yet-modelled signals live (e.g.
`duration_seconds`, `resolution`, `has_voiceover`, `has_music`,
`has_subtitles`, `manual_qc_passed`) that `ChannelOutputPolicy` validation
reads opportunistically without requiring ffprobe.

## EvidenceRecord / EvidenceBundle

`EvidenceBundle` is an in-memory, ordered collection of `EvidenceRecord`
keyed by `evidence_id`, persisted at
`projects/<project_id>/evidence/evidence_manifest.json`. A companion
`rights_report.json` in the same directory is a derived, regenerable
summary.

| Field | Type | Default |
|---|---|---|
| `evidence_id` | `str` (required, non-empty) | - |
| `asset_id` | `str` | `""` |
| `source_url` / `license_url` | `str` | `""` |
| `provider` / `author` / `license_name` | `str` | `""` |
| `commercial_use_status` | `str` (free-form) | `"unknown"` |
| `attribution_required` | `bool` | `False` |
| `attribution_text` | `str` | `""` |
| `acquired_at` | `str` | `""` |
| `checksum_sha256` | `str` | `""` |
| `local_path` / `original_filename` | `str` | `""` |
| `proof_files` | `list[str]` | `[]` |
| `notes` | `str` | `""` |
| `verification_status` | `str`, one of `VERIFICATION_STATUSES` | `"unknown"` |
| `schema_version` | `int` | `1` |

`VERIFICATION_STATUSES`: `verified`, `review_required`, `blocked`,
`unknown`.

`EvidenceBundle.add()` refuses to silently overwrite an existing
`evidence_id` unless `overwrite=True` is passed explicitly, and
`EvidenceBundle.load()` + `.save()` round-trip every previously stored
record, so updating a bundle never silently drops earlier evidence.

`EvidenceBundle.validate()` flags (non-exhaustive):

- verified records missing `source_url`, `license_name`, or
  `checksum_sha256`;
- `checksum_sha256` present but not 64 hex characters;
- `attribution_required=True` with empty `attribution_text`;
- duplicate `evidence_id` values (defensive check for hand-edited files).

`EvidenceBundle.summary()` returns an `EvidenceSummary` (`total`,
`verified`, `review_required`, `blocked`, `unknown`), the input consumed by
`ChannelOutputPolicy` validation.

## ChannelOutputPolicy

Not a separate file - stored inline as `ChannelProfile.output_policy`
(a plain dict) and parsed on demand via `ChannelOutputPolicy.from_dict()`.

| Field | Default | Meaning |
|---|---|---|
| `allowed_applications` / `allowed_formats` / `allowed_templates` / `allowed_export_targets` / `allowed_languages` | `[]` | empty = no restriction |
| `require_verified_evidence` | `False` | every evidence record must be `verified` |
| `allow_review_required_assets` | `True` | |
| `allow_unknown_license` | `False` | |
| `minimum_resolution` / `preferred_resolution` | `None` | `{"width": int, "height": int}` |
| `maximum_duration_seconds` | `None` | |
| `require_voiceover` / `require_music` / `require_subtitles` / `require_manual_qc` | `False` | read from `ProjectManifest.metadata` |
| `notes` | `""` | |

`validate(policy, channel, project, evidence_summary) -> ValidationResult`
(`allowed: bool`, `errors: list[str]`, `warnings: list[str]`,
`evaluated_rules: list[str]`). Blocked evidence always fails validation
regardless of policy flags. Resolution/duration/voiceover/music/subtitles
checks only run when the corresponding key exists in
`ProjectManifest.metadata`; if it is missing, a warning is recorded instead
of a hard failure (no ffprobe is invoked at this stage).
