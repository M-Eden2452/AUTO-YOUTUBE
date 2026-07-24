# Stage 2B: Project / Channel / Evidence Foundation - Plan

## Goal

Provide a stable, self-contained foundation for channels, projects,
provenance evidence, and per-channel output rules, so that later stages
(universal CLI, batch queue, real test Shorts) can build on top of stored
`ChannelProfile` / `ProjectManifest` / `EvidenceBundle` / `ChannelOutputPolicy`
records instead of ad-hoc config files.

## Scope

In scope:

- `src/project_foundation/` package (models, channels, projects, evidence,
  policies, storage, cli).
- Filesystem-backed `ChannelRegistry` (`channels/<channel_id>/channel.json`).
- Filesystem-backed `ProjectFactory` (`projects/<project_id>/project.json`
  plus minimal subdirectories).
- `EvidenceBundle` (`projects/<project_id>/evidence/evidence_manifest.json`
  and `rights_report.json`).
- `ChannelOutputPolicy` validation (no ffprobe, no network).
- An independent CLI: `python -m src.project_foundation.cli`.
- Targeted unittest coverage.

Out of scope (explicitly not touched or integrated in this stage):

- `pipeline.py` (no wiring added).
- `src/news/`, `src/audio/` (News-to-Short / Voice pipelines).
- Story Card renderer and `projects/story_card_owl_test/`.
- `src/production_catalog/` (read for terminology only, not modified or
  imported).
- `src/production_plan/`, `project_solar_vs_nuclear/`, `anime_factory/`,
  `apps/`, `packages/`.
- `requirements.txt`, `.gitignore`, `docs/handoff/`.
- `tests/test_asset_cli_wiring.py`, `tests/test_news_to_short_provider_integration.py`.

## Design principles

- **Self-contained.** The package imports nothing from `src.news`,
  `src.audio`, `src.production_catalog`, `src.production_plan`, or
  `pipeline.py`. It only uses the Python standard library.
- **No network, no rendering, no API keys.** Every operation is pure
  filesystem I/O over JSON.
- **Filesystem, not a database.** Each channel/project is one directory with
  JSON files inside it.
- **Atomic writes.** Every JSON write goes through a temp file + `os.replace`
  so a crash mid-write cannot corrupt an existing file.
- **Safe defaults.** All optional fields have sensible defaults; empty
  allow-lists in `ChannelOutputPolicy` mean "no restriction" rather than
  "block everything".
- **No duplicated implementation.** A short audit (see
  `FOUNDATION_REPORT.md`) confirmed no existing `ChannelProfile`,
  `ChannelRegistry`, `ProjectManifest`, `ProjectFactory`, `EvidenceBundle`,
  `ChannelOutputPolicy`, or `ProjectRegistry` implementation exists anywhere
  in the repository before this stage.

## Deliverables

1. `src/project_foundation/{__init__,models,channels,projects,evidence,policies,storage,cli}.py`
2. `tests/test_project_foundation_models.py`
3. `tests/test_channel_registry.py`
4. `tests/test_project_factory.py`
5. `tests/test_evidence_bundle.py`
6. `tests/test_channel_output_policy.py`
7. `tests/test_project_foundation_cli.py`
8. This documentation set.
