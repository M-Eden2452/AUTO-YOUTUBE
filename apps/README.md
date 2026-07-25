# Apps

This folder contains app-level entrypoint wrappers and ownership documentation.

Current strategy:

- Keep legacy working modules in place until their contracts are fully stable.
- Add `apps/<app>/main.py` wrappers so each application has a clear public entrypoint.
- Move implementation files only in a later cleanup when tests and callers are ready.

Apps:

- `news_to_short` - news/topic/text to vertical shorts.
- `youtube_pipeline` - existing main YouTube pipeline through `pipeline.py`.
- `anime_factory` - existing Anime Factory through `anime_factory/pipeline.py`.

