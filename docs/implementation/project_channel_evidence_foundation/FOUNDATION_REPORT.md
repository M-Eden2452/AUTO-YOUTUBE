# Stage 2B: Project / Channel / Evidence Foundation - Report

## Pre-implementation audit

Read `CLAUDE.md`, `COMMANDS.md`, `src/production_catalog/models.py` (for
terminology only), and searched the whole repository for existing
`ChannelProfile`, `ChannelRegistry`, `ProjectManifest`, `ProjectFactory`,
`EvidenceBundle`, `ChannelOutputPolicy`, `ProjectRegistry` classes.

Result: no such classes exist anywhere. The only textual match was a test
class named `ChannelProfileTests` in `tests/test_channel_profiles.py`
(committed in `eebb01c`/`9e4e03f`), which tests the unrelated legacy
quote/survival channel-config pipeline (`src.channel_loader`,
`src.config_loader`). It was left untouched - no conflict, no dependency,
no duplication.

`channels/nature_science_news_ru/channel_config.json` and the other
`channels/<id>/channel_config.json` files are also a different, unrelated
legacy JSON format (News-to-Short specific: voice provider, resolution,
localization settings). The new `ChannelRegistry` reads/writes
`channels/<id>/channel.json` (a different filename), so there is no
collision with the existing legacy directory layout, and none of those
directories were modified.

## Architecture

```
src/project_foundation/
  __init__.py    - public exports
  models.py      - ChannelProfile, ChannelBranding, ProjectManifest,
                   EvidenceRecord, EvidenceSummary, status/verification
                   constants, ProjectFoundationError
  storage.py     - atomic_write_json / read_json / read_json_if_exists
  channels.py    - ChannelRegistry (create/get/list/update/exists)
  projects.py    - ProjectFactory (create/get/list/save) + project_id
                   generation
  evidence.py    - EvidenceBundle (add/get/list/validate/summary/
                   rights_report/save/load)
  policies.py    - ChannelOutputPolicy, ValidationResult, validate()
  cli.py         - argparse CLI, independent of pipeline.py
```

The package has zero imports from `src.news`, `src.audio`,
`src.production_catalog`, `src.production_plan`, or `pipeline.py` - only
the Python standard library.

## Files created

- `src/project_foundation/__init__.py`
- `src/project_foundation/models.py`
- `src/project_foundation/storage.py`
- `src/project_foundation/channels.py`
- `src/project_foundation/projects.py`
- `src/project_foundation/evidence.py`
- `src/project_foundation/policies.py`
- `src/project_foundation/cli.py`
- `tests/test_project_foundation_models.py`
- `tests/test_channel_registry.py`
- `tests/test_project_factory.py`
- `tests/test_evidence_bundle.py`
- `tests/test_channel_output_policy.py`
- `tests/test_project_foundation_cli.py`
- `docs/implementation/project_channel_evidence_foundation/{FOUNDATION_PLAN,DATA_MODEL,CLI_REFERENCE,FOUNDATION_REPORT}.md`

No existing file was modified.

## Test results

```
./venv/Scripts/python.exe -m unittest \
  tests.test_project_foundation_models \
  tests.test_channel_registry \
  tests.test_project_factory \
  tests.test_evidence_bundle \
  tests.test_channel_output_policy \
  tests.test_project_foundation_cli \
  -v
```

Result: **72 tests, all passing** (Python 3.13.13, `./venv/Scripts/python.exe`).

Coverage highlights: model round-trip serialization, default values,
invalid `status`/`verification_status`, duplicate channel_id, corrupted
JSON (channel + evidence manifest), atomic writes leaving no stray temp
files, project creation, dry-run writing nothing, no-overwrite protection,
channel-default inheritance vs. explicit overrides, evidence validation
rules, rights report grouping, blocked/unknown/review-required policy
outcomes, CLI list/show/create/validate/evidence-list/rights-report over
subprocess, CLI-does-not-import-`pipeline`, and explicit assertions that
no test writes into the real `channels/` or `projects/` directories.

## Smoke checks

```
./venv/Scripts/python.exe -c "from src.project_foundation import ChannelProfile, ProjectManifest, EvidenceBundle, ChannelOutputPolicy; print('imports OK')"
```
-> `imports OK`

CLI smoke (temp directory only): `channels create`, `channels list`,
`projects create --dry-run`, and an intentional `channels show
<missing>` all behaved as expected, the last one exiting with code `1`
and a JSON `{"error": ...}` on stderr.

## Safety verification

- No network/API calls, no downloads, no Vision/TTS calls, no rendering at
  any point in this stage.
- `pipeline.py`: not modified by this stage (its pre-existing uncommitted
  diff predates this session and was left untouched).
- Old WIP groups (`src/news/`, `src/audio/`, `src/production_catalog/`,
  `src/production_plan/`, `project_solar_vs_nuclear/`, `anime_factory/`,
  `apps/`, `packages/`, `requirements.txt`, `.gitignore`,
  `docs/handoff/`, `tests/test_asset_cli_wiring.py`,
  `tests/test_news_to_short_provider_integration.py`): not modified.
- Secret scan over all new files (patterns: API keys, `Authorization:`,
  `Bearer`, `sk-`, base64 data URLs, etc.): no matches.
- No new file exceeds 1 MB (largest is `models.py` at ~15 KB).
- No real channel or project was created under the repository's actual
  `channels/` or `projects/` directories; every test and CLI smoke check
  ran against a `tempfile.TemporaryDirectory()`.

## Known limitations

- `ChannelOutputPolicy` resolution/duration/voiceover/music/subtitles
  checks only look at `ProjectManifest.metadata`; there is no ffprobe or
  media inspection in this stage (by design, per Stage 2B scope).
- `ProjectFactory`/`ChannelRegistry` are filesystem-only (no database, no
  indexing beyond directory scans) - acceptable at current project scale.
- The CLI has no `channels update` subcommand yet (only `ChannelRegistry.update()`
  exists at the Python API level); it was not explicitly requested for
  Stage 2B's CLI surface.
- `EvidenceBundle` does not fetch or copy proof files - it only stores
  references, exactly as scoped for this stage.
- No integration with `src/production_catalog`, `src/news`, `src/audio`,
  or `pipeline.py` yet - that is future wiring, intentionally deferred.

## Ready for commit

Stage 2B is self-contained, fully tested (72/72), and does not touch any
excluded file or directory. It is ready for a separate commit.

Suggested commit message:

```
add project, channel, evidence, and output policy foundation
```
