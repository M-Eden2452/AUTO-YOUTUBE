# Stage 2C — Story Card Template Integration: Report

## Chosen implementation

- Renderer: `src/production_plan/story_card_short_render.py` (unchanged) —
  the only Story Card renderer in the repo; no legacy/duplicate renderer
  exists, so nothing needed to be chosen between.
- Preset: `config/render_presets/story_card_short_v1.json` (unchanged).
- Canonical naming: `story_card_text_only_v1` with legacy alias
  `story_card_short_v1`, matching what is already registered in
  `src/production_catalog/catalog.py` (Stage 2A) and already used as the
  default in the Stage 2B fixtures/tests.

## Legacy aliases found

- `story_card_short_v1` → `story_card_text_only_v1` (already established in
  Stage 2A's `TemplateRegistry`; reimplemented here as two local constants
  in `src/templates/story_card/integration.py` instead of importing
  `src.production_catalog`, per the Stage 2C scope boundary that keeps
  Production Catalog unconnected on this stage).

## Reused vs. created

**Reused (no changes):**
- `src/production_plan/story_card_short_render.py`
- `config/render_presets/story_card_short_v1.json`
- `src/project_foundation/*` (models, storage, channels, projects, policies, evidence)

**Created:**
- `src/templates/__init__.py`
- `src/templates/story_card/__init__.py`
- `src/templates/story_card/integration.py`
- `tests/test_story_card_project_integration.py`
- `docs/implementation/story_card_project_integration/INTEGRATION_PLAN.md`
- `docs/implementation/story_card_project_integration/TEMPLATE_CONTRACT.md`
- `docs/implementation/story_card_project_integration/INTEGRATION_REPORT.md` (this file)

## Test results

`./venv/Scripts/python.exe -m unittest tests.test_story_card_project_integration -v`
→ **16 passed** (canonical id, legacy alias, unknown template id, dry-run,
render request creation + project-relative paths, overwrite protection,
smoke local render, invalid format, invalid template, missing localization
text, missing source asset, channel policy disallow, channel policy
alias-aware allow, no pipeline import, no writes to real channels/projects).

`./venv/Scripts/python.exe -m unittest tests.test_story_card_short_renderer -v`
→ **4 passed**, unchanged (existing Story Card renderer tests, still green).

`./venv/Scripts/python.exe -m unittest tests.test_project_foundation_models tests.test_project_foundation_cli -v`
→ **23 passed**, unchanged (Stage 2B regression, no Stage 2B model changes were made).

## Smoke checks

- `import src.templates.story_card` succeeds; `'pipeline' not in sys.modules`
  confirmed in a subprocess (see `test_does_not_import_pipeline`).
- Story Card smoke render (`test_smoke_local_render_produces_vertical_mp4`)
  runs entirely in a `TemporaryDirectory`, with `socket.socket` patched to
  raise if called, and still renders a valid MP4 — no network path is
  exercised by `prepare_story_card_render`.
- `test_does_not_write_to_real_channels_or_projects` snapshots the real
  `channels/` and `projects/` directories before/after and asserts they are
  untouched.

## Confirmed

- No network calls, no downloads, no TTS/ElevenLabs, no OpenAI API calls
  anywhere in `src/templates/story_card/`.
- `pipeline.py` was not opened or modified during this stage (it was already
  showing as modified in `git status` before this stage started, from prior
  work — see below).
- `src/news/`, `src/audio/`, `src/production_catalog/` were not touched.
- No secrets read or written; `.env` not touched.
- No new file is larger than 1 MB (new files range from ~60 bytes to ~17 KB).
- Real `channels/` and `projects/` directories are unmodified (verified by
  a dedicated test, matching the same pattern as
  `tests/test_project_foundation_cli.py`).

## Known limitations

- The channel/policy compatibility check duplicates a small, alias-aware
  subset of `src.project_foundation.policies.validate()` (template/format/
  language/export_targets) rather than calling it directly, because that
  function compares `template_id` by exact string and also requires an
  `EvidenceSummary` argument that isn't relevant to render preparation. This
  is an intentional, documented trade-off, not an oversight.
- `render=True` performs a real local MoviePy/ffmpeg encode (CPU-bound,
  no network) — callers should keep using small presets/durations for
  automated tests, as done here and in the existing renderer test.
- This stage does not add a CLI subcommand; `prepare_story_card_render` is a
  Python entry point only, consistent with the stage boundary (no
  `pipeline.py` changes).

## Git status

```
 M .gitignore
 M pipeline.py
 M requirements.txt
?? .claude/
?? CLAUDE.md
?? COMMANDS.md
?? PROJECT_AUDIT*.md / .json
?? anime_factory/
?? apps/
?? channels/nature_science_news_ru/
?? config/render_presets/
?? content/story_card_jobs.tsv
?? docs/... (multiple pre-existing untracked doc trees)
?? docs/implementation/story_card_project_integration/   <- new (this stage)
?? outputs/audio_edits/
?? packages/
?? project_solar_vs_nuclear/
?? src/audio/
?? src/news/
?? src/production_catalog/
?? src/production_plan/
?? src/templates/                                        <- new (this stage)
?? tests/test_*.py (many pre-existing untracked test files)
?? tests/test_story_card_project_integration.py           <- new (this stage)
```

Everything except the three lines marked "new (this stage)" (plus the
untouched pre-existing modifications to `.gitignore`/`pipeline.py`/
`requirements.txt`) predates this session's work.

## Ready for commit?

Yes, Stage 2C is ready for its own commit.

**Recommended commit scope (this stage's work only):**
```
src/templates/
tests/test_story_card_project_integration.py
docs/implementation/story_card_project_integration/
```

**Suggested commit message:**
```
integrate story card template with project foundation
```

No `git add`, `git commit`, or any other git write operation was performed —
per instructions, this stage stops after the report.
