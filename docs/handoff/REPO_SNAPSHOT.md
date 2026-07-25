# Repo Snapshot

- Date: 2026-07-23
- Project root: `G:\Projects\AI-YouTube`
- Current branch: `master`
- Python: `Python 3.10.11`
- FFmpeg: available, `ffmpeg version 8.1.1-full_build-www.gyan.dev`
- FFprobe: available, `ffprobe version 8.1.1-full_build-www.gyan.dev`

## Git status summary

The repository already had many uncommitted changes before this handoff package was created.

Modified tracked files shown by `git status --short`:

```text
M .gitignore
M pipeline.py
M requirements.txt
M src/media_library.py
M src/providers/__init__.py
M src/providers/pexels_provider.py
M src/providers/pixabay_provider.py
M tests/test_media_library.py
```

There are also many untracked provider foundation, app, config, docs, source and test files. New handoff files are under `CLAUDE.md`, `.claude/settings.json`, and `docs/handoff/`.

## Key files existence

- `pipeline.py`: exists
- `README.md`: exists
- `config/render_presets/story_card_short_v1.json`: exists
- `src/production_plan/story_card_short_render.py`: exists
- `src/providers/`: exists
- `src/assets/visual_preview.py`: exists
- `src/assets/temporal_video_analysis.py`: exists
- `src/assets/semantic_visual_service.py`: exists
- `src/assets/semantic_visual_openai.py`: exists
- `src/assets/semantic_decision_policy.py`: exists
- `src/audio/voice_cli.py`: exists
- `src/audio/voice_workflow.py`: exists
- `src/news/pipeline.py`: exists
- `projects/story_card_owl_test/final_test.mp4`: exists

## Last known test results from saved reports

- Targeted validation: passed, 53 tests.
- `tests.test_semantic_decision_policy`: passed.
- `tests.test_temporal_video_analysis`: passed.
- `tests.test_story_card_short_renderer`: passed.
- Full unittest discovery from saved report: passed, 276 tests, 79.042 sec.
- This snapshot did not rerun the full suite.

## Current test artifact

- Final MP4: `projects/story_card_owl_test/final_test.mp4`
- Render manifest: `projects/story_card_owl_test/render_manifest.json`
- Layout: `projects/story_card_owl_test/story_card_layout.json`
- Selected asset: `projects/story_card_owl_test/selected_asset.json`
- Shadow recommendation: `projects/story_card_owl_test/shadow_recommendation.json`

## media_index

- Path: `assets/library/metadata/media_index.json`
- SHA-256 from checkpoint: `61B2C5B89F353659ACD48E299DEA3CE6478F28FA968B9149E615DD2051A30385`
- Current SHA-256 checked during handoff: `61b2c5b89f353659acd48e299dea3ce6478f28fa968b9149e615dd2051a30385`

## Known unfinished work

- Adaptive `story_card_short_v1` not implemented yet.
- Universal `story-card create` CLI does not exist yet.
- Story-card batch JSON queue does not exist yet.
- UI work should wait until E2E story-card tests pass.

