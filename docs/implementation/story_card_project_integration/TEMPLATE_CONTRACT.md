# Story Card Template Contract (Stage 2C)

## Canonical identity

- Canonical `template_id`: `story_card_text_only_v1`
- Legacy alias (still accepted): `story_card_short_v1`
- Supported `format_id`: `vertical_short` (1080x1920, 30fps — from the
  existing preset, see `config/render_presets/story_card_short_v1.json`)
- Supported `application_id` (informational, not enforced by this layer):
  `content_creator`

`canonicalize_story_card_template_id(template_id)` in
`src/templates/story_card/integration.py` resolves either string to the
canonical id and raises `StoryCardIntegrationError` for anything else.

## Entry point

```python
from src.templates.story_card import prepare_story_card_render

result = prepare_story_card_render(
    project,                      # ProjectManifest
    channel=channel,              # ChannelProfile | None
    source_asset_path=path,       # local image/video path, must exist
    text={"top": "...", "comment": "..."},  # at least one non-empty key required
    render_preset_path=preset_path,  # defaults to the existing story_card preset
    dry_run=True,                 # True: no files written, no render
    allow_overwrite=False,        # False: never clobbers an existing output
    render=False,                 # True: actually invoke the local renderer
)
```

## Validation performed (all local, no network)

1. `project.template_id` canonicalizes to `story_card_text_only_v1`
   (canonical id or `story_card_short_v1` alias) — else
   `StoryCardIntegrationError`.
2. `project.format_id == "vertical_short"` — else
   `StoryCardIntegrationError`.
3. If `channel` is given:
   - `project.language` must be in `channel.supported_languages` — else error.
   - `channel.output_policy.allowed_templates`, if non-empty, is checked
     alias-aware (both canonical id and legacy alias are accepted) — else
     error.
   - `channel.output_policy.allowed_formats`, if non-empty, must include
     `vertical_short` — else error.
   - `channel.output_policy.allowed_export_targets` mismatches are recorded
     as warnings (not hard errors), consistent with the soft-warning style
     used by `src.project_foundation.policies.validate`.
   - A project `template_id` that differs from `channel.default_template`
     is a warning (explicit override), not an error.
4. `source_asset_path` must exist as a local file — else error.
5. `text` must contain a non-empty `top` or `comment` string — else error.

## Render statuses returned

| Status | Meaning |
|---|---|
| `dry_run` | Nothing written; paths/dimensions are a preview of what would happen. |
| `prepared` | Render request JSON written under the project; renderer not invoked (`render=False`). |
| `rendered` | Local renderer ran and produced the final MP4 and preview PNG. |
| `skipped_existing_output` | Output already exists and `allow_overwrite=False`; nothing was touched. |
| `failed` | Renderer ran but its own manifest reported a non-`completed` status. |

## Output paths (project-relative)

- `render_request_path`: `<project.project_root>/outputs/story_card_render_request.json`
- `output_path`: `<project.project_root>/outputs/story_card_short.mp4`
- `frame_preview_path` (in `metadata`): `<project.project_root>/outputs/story_card_preview.png`

`outputs/` already exists once a project is created via `ProjectFactory`
(`PROJECT_SUBDIRS` in `src/project_foundation/projects.py`).

## Result fields

`StoryCardIntegrationResult.to_dict()` returns: `project_id`, `template_id`
(as given, possibly the legacy alias), `canonical_template_id`,
`render_status`, `render_request_path`, `output_path`, `width`, `height`,
`fps`, `duration_seconds`, `source_asset`, `localization` (`{language, text}`),
`warnings`, `metadata` (`preset_name`, `preset_path`, `frame_preview_path`,
`channel_id`, and — only when `render=True` — `render_manifest`, the raw
manifest returned by `render_story_card_short`).
