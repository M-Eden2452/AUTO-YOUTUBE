# Stage 2C — Story Card Template Integration: Plan

## Goal

Connect the existing, working Story Card renderer to the Stage 2B
Project/Channel Foundation (`ChannelProfile` / `ProjectManifest` /
`ProjectFactory`) without rewriting the renderer and without wiring in
News, Audio, Production Catalog, or the general `pipeline.py`.

## Path implemented

```
ChannelProfile
  -> ProjectFactory.create(...)
  -> ProjectManifest
  -> prepare_story_card_render(project, channel=..., source_asset_path=..., text=...)
  -> render request (JSON, project-relative)
  -> optional local render via src.production_plan.story_card_short_render
  -> StoryCardIntegrationResult (structured metadata)
```

## What was reused (no duplicates created)

- Renderer: `src/production_plan/story_card_short_render.py`
  (`load_story_card_preset`, `render_story_card_short`) — unchanged.
- Preset: `config/render_presets/story_card_short_v1.json` — unchanged.
- Foundation: `src/project_foundation/` (`ChannelProfile`, `ProjectManifest`,
  `ProjectFactory`, `ChannelRegistry`, `ChannelOutputPolicy`) — unchanged.
- Canonical/legacy naming pattern: mirrors
  `src/production_catalog/catalog.py` (`template_id="story_card_text_only_v1"`,
  `legacy_aliases=("story_card_short_v1",)`), reimplemented as two local
  constants instead of importing `src.production_catalog`, because Stage 2C
  explicitly keeps Production Catalog unconnected on this stage.

## What was created

- `src/templates/story_card/` — a small integration package:
  - `integration.py` — `prepare_story_card_render(...)`,
    `canonicalize_story_card_template_id(...)`, `StoryCardIntegrationResult`,
    `StoryCardIntegrationError`, render-status constants.
  - `__init__.py` — public exports.
- `tests/test_story_card_project_integration.py` — integration tests.
- This `docs/implementation/story_card_project_integration/` folder.

## Explicit non-goals for this stage

Not connected: `src/news/`, `src/audio/` (TTS/ElevenLabs), any downloads,
`src/production_catalog/`, `pipeline.py`, YouTube upload, publishing, UI,
Solar vs Nuclear, Anime Factory.
