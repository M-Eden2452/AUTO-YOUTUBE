# Apps

This folder contains compatibility entrypoint wrappers and ownership documentation.

Current strategy:

- Use `python -m ai_youtube` as the canonical CLI for the active
  `content_creator` application.
- Keep legacy working modules in place until their contracts are fully stable.
- Add `apps/<app>/main.py` wrappers so each application has a clear public entrypoint.
- Move implementation files only in a later cleanup when tests and callers are ready.

Compatibility wrappers:

- `news_to_short` - the existing fullscreen voiceover workflow.
- `youtube_pipeline` - existing main YouTube pipeline through `pipeline.py`.
- `anime_factory` - existing Anime Factory workflow through
  `anime_factory/pipeline.py`; this does not make the planned/disabled
  `video_repurposer` application ready.
