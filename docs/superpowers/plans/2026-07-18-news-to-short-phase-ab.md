# News To Short Phase A+B Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the first safe `news_to_short` phase inside the existing AI-YouTube application without moving existing app files.

**Architecture:** Keep the current `pipeline.py`, YouTube pipeline, Anime Factory, and provider modules intact. Add a bounded `src/news/` subsystem for job/project/stage artifacts and a reusable `src/audio/tts/` subsystem for future voice providers and approval-controlled paid TTS.

**Tech Stack:** Python stdlib dataclasses, JSON/YAML files, existing `requests` and `PyYAML`, unittest tests, existing virtualenv.

---

### Task 1: News Job Models

**Files:**
- Create: `src/news/models.py`
- Create: `tests/test_news_to_short_models.py`

- [ ] Write tests for job defaults, stage metadata, localization folders, rights statuses, and stage ordering.
- [ ] Run `venv\Scripts\python.exe -m unittest tests.test_news_to_short_models` and verify tests fail because `src.news.models` is missing.
- [ ] Implement dataclasses and validation helpers in `src/news/models.py`.
- [ ] Re-run the model tests and keep them green.

### Task 2: Project Store

**Files:**
- Create: `src/news/project_store.py`
- Extend: `tests/test_news_to_short_models.py`

- [ ] Write tests for creating `projects/<job_id>/`, master folders, and `localizations/ru|en|es`.
- [ ] Run the targeted tests and verify failure.
- [ ] Implement project directory creation, JSON read/write, stage updates, and resume loading.
- [ ] Re-run the targeted tests.

### Task 3: A+B Pipeline Stages

**Files:**
- Create: `src/news/article_parser.py`
- Create: `src/news/article_ingestor.py`
- Create: `src/news/research_engine.py`
- Create: `src/news/script_generator.py`
- Create: `src/news/visual_plan.py`
- Create: `src/news/pipeline.py`
- Create: `tests/test_news_to_short_pipeline.py`

- [ ] Write tests for URL/topic/text input, article JSON, research claims, script JSON, `narration.txt`, master visual plan, localized visual plan, and dry-run no-paid behavior.
- [ ] Run the pipeline tests and verify failure.
- [ ] Implement minimal deterministic stage processors that save every intermediate artifact to disk.
- [ ] Re-run the pipeline tests.

### Task 4: Safe Voice Architecture

**Files:**
- Create: `src/audio/__init__.py`
- Create: `src/audio/tts/__init__.py`
- Create: `src/audio/tts/models.py`
- Create: `src/audio/tts/base_provider.py`
- Create: `src/audio/tts/provider_manager.py`
- Create: `src/audio/tts/audio_file_provider.py`
- Create: `src/audio/tts/elevenlabs_provider.py`
- Create: `src/audio/voice_workflow.py`
- Create: `tests/test_voice_workflow.py`

- [ ] Write tests for cache key composition, audio_file status, approval invalidation by script/settings hash, voice states, and ElevenLabs preflight not calling synthesis.
- [ ] Run the voice tests and verify failure.
- [ ] Implement provider contracts, audio_file validation, safe ElevenLabs catalog/preflight helpers, and approval JSON helpers.
- [ ] Re-run the voice tests.

### Task 5: Channel Profile And CLI Hook

**Files:**
- Create: `channels/nature_science_news_ru/channel_config.json`
- Create: `channels/nature_science_news_ru/style.json`
- Create: `channels/nature_science_news_ru/subtitle_style.json`
- Create: `channels/nature_science_news_ru/voices.yaml`
- Modify: `pipeline.py`
- Extend: `tests/test_news_to_short_pipeline.py`

- [ ] Write tests or CLI smoke checks for `--news-to-short --topic ... --dry-run` and resume.
- [ ] Run the checks and verify failure before the CLI hook exists.
- [ ] Add a guarded CLI branch that does not affect existing arguments unless `--news-to-short` is present.
- [ ] Re-run targeted tests and CLI dry-run smoke test.

### Task 6: Documentation

**Files:**
- Create: `docs/apps/youtube_pipeline.md`
- Create: `docs/apps/anime_factory.md`
- Create: `docs/apps/news_to_short.md`
- Create: `docs/architecture/news_to_short_phase_ab_plan.md`
- Create: `docs/architecture/localization_and_voice_architecture.md`

- [ ] Document current apps, what each can do, available settings, future useful functionality, and current completion stage.
- [ ] Document the hybrid architecture boundaries and why physical moves into `apps/`/`packages/` are deferred.
- [ ] Document future Storyblocks/Envato provider slots without adding integrations or keys.

### Task 7: Verification

**Files:**
- No new files.

- [ ] Run `venv\Scripts\python.exe -m unittest tests.test_news_to_short_models tests.test_news_to_short_pipeline tests.test_voice_workflow`.
- [ ] Run existing stable tests used as baseline.
- [ ] Run `venv\Scripts\python.exe -m compileall pipeline.py src anime_factory`.
- [ ] Run a dry-run command and confirm artifacts are created under `projects/<job_id>/`.
