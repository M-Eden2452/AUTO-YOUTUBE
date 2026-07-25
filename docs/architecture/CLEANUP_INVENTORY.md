# Cleanup Inventory

This is an inventory only. Nothing should be deleted or moved in the Provider Foundation hardening stage.

## Classification Legend

- `active core`: shared code used by more than one workflow.
- `application`: app entry point or app-specific orchestration.
- `configuration`: config, presets or environment files.
- `workspace data`: project data or source content.
- `generated output`: renders, previews, reports or generated media.
- `cache/temp`: disposable runtime cache or temporary files.
- `report/documentation`: docs, audits, implementation records.
- `external dependency`: local dependency or environment folder.
- `experiment`: useful prototype, not shared core.
- `legacy`: older code kept for compatibility/reference.
- `unknown`: needs import/runtime verification.
- `candidate for future cleanup`: can be cleaned later after backup and owner approval.

## Top-Level Inventory

| Current path | Classification | Purpose | Used by code | Can move later | Can delete later | Check before delete | Recommended future place |
|---|---|---|---:|---:|---:|---|---|
| `.git/` | external dependency | Git repository metadata. | Yes | No | No | Never delete inside project cleanup. | Keep at repo root |
| `.env` | configuration | Local secrets and machine-specific config. | Yes | No | No | Do not expose values; verify secret-loading strategy. | Secure local config outside commits |
| `.env.example` | configuration | Example env variable names. | Yes | Maybe | No | Keep secret-free; update when env names change. | `config/examples/.env.example` |
| `.gitignore` | configuration | Git ignore policy. | Yes | No | No | Verify generated data patterns. | Repo root |
| `README.md` | report/documentation | Project overview. | Maybe | Maybe | No | Verify docs links and entry points. | `docs/README.md` plus short root README |
| `pipeline.py` | application | Current overloaded root CLI dispatcher. | Yes | Yes | No | All wrapper commands migrated and tested. | `apps/cli/main.py` wrapper |
| `requirements.txt` | configuration | Python dependencies. | Yes | Maybe | No | Packaging/lockfile decision. | Repo root or `config/requirements/` |
| `PROJECT_AUDIT.md` | report/documentation | Earlier broad audit. | No runtime | Maybe | No | Confirm superseded by split audit docs. | `docs/audits/` |
| `PROJECT_AUDIT_INDEX.md` | report/documentation | Audit index. | No runtime | Maybe | No | Preserve historical audit. | `docs/audits/` |
| `PROJECT_AUDIT_OVERVIEW.md` | report/documentation | Audit overview. | No runtime | Maybe | No | Preserve historical audit. | `docs/audits/` |
| `PROJECT_AUDIT_ARCHITECTURE.md` | report/documentation | Architecture audit. | No runtime | Maybe | No | Preserve historical audit. | `docs/audits/` |
| `PROJECT_AUDIT_PIPELINES.md` | report/documentation | Pipeline audit. | No runtime | Maybe | No | Preserve historical audit. | `docs/audits/` |
| `PROJECT_AUDIT_COMPONENTS.md` | report/documentation | Component audit. | No runtime | Maybe | No | Preserve historical audit. | `docs/audits/` |
| `PROJECT_AUDIT_RISKS_TESTS.md` | report/documentation | Risk/test audit. | No runtime | Maybe | No | Preserve historical audit. | `docs/audits/` |
| `PROJECT_AUDIT_ROADMAP.md` | report/documentation | Roadmap audit. | No runtime | Maybe | No | Preserve historical audit. | `docs/audits/` |
| `PROJECT_AUDIT_SNAPSHOT.json` | report/documentation | Machine-readable audit snapshot. | No runtime | Maybe | No | Validate JSON after move. | `docs/audits/` |
| `IMPLEMENTATION_PROVIDER_FOUNDATION_PLAN.md` | report/documentation | Previous implementation plan. | No runtime | Maybe | No | Preserve historical implementation record. | `docs/implementation/provider_foundation/` |
| `IMPLEMENTATION_PROVIDER_FOUNDATION_REPORT.md` | report/documentation | Previous implementation report. | No runtime | Maybe | No | Preserve historical implementation record. | `docs/implementation/provider_foundation/` |
| `IMPLEMENTATION_PROVIDER_FOUNDATION_SNAPSHOT.json` | report/documentation | Previous implementation snapshot. | No runtime | Maybe | No | Validate JSON after move. | `docs/implementation/provider_foundation/` |
| `src/` | active core | Main Python modules, current shared and app logic. | Yes | Yes | No | Import map, tests, wrappers. | Split into `src/core`, `src/pipelines`, `src/rendering`, `src/assets` |
| `apps/` | application | Thin app wrappers for news, anime and legacy pipeline. | Yes | Yes | No | Wrapper behavior and CLI tests. | Keep as top-level app entry points |
| `anime_factory/` | experiment | Separate anime clipping workflow and sample episode outputs. | Yes | Yes | No | Copyright/data ownership, CLI tests, output paths. | `apps/anime_clipper/` plus `workspace/projects/anime/` |
| `assets/` | workspace data | Media library, images, voice samples and asset metadata. | Yes | Yes | No | Backup media, hash index, migration dry-run. | `workspace/media_library/` |
| `channels/` | configuration | Channel configs, styles, voices and presets. | Yes | Yes | No | Loader paths and channel IDs. | `channels/presets/`, `channels/niches/`, `channels/voices/` |
| `config/` | configuration | Global style and policy config. | Yes | Yes | No | Typed config registry. | `config/` |
| `content/` | workspace data | Source content for old channel/video pipeline. | Yes | Yes | Maybe | Verify each channel/video is backed up and not active. | `workspace/content/` |
| `docs/` | report/documentation | Plans, architecture docs, implementation records. | No runtime | Yes | No | Link validation. | `docs/` |
| `legacy/` | legacy | Older OpenAI/b-roll/render scripts. | Maybe standalone | Yes | Maybe | Import grep, user confirmation, replacement wrappers. | `legacy/` or archived package |
| `manual_assets/` | workspace data | User-supplied media placeholders and manual assets. | Maybe | Yes | No | Rights declarations, user ownership, backup. | `workspace/media_library/manual/` |
| `MOSS_TTS_Nano/` | external dependency | Local MOSS TTS engine/weights or checkout. | Maybe | Yes | No | Voice workflow config and local environment. | Outside repo or `vendor/` ignored |
| `music/` | workspace data | Local music folder placeholder. | Maybe | Yes | Maybe | Confirm no user-owned tracks needed. | `workspace/media_library/music/` |
| `outputs/` | generated output | Old pipeline generated output and audio edits. | Maybe | Yes | Maybe | Backup user deliverables; verify not referenced by project manifests. | `workspace/reports/` and `workspace/projects/*/outputs/` |
| `packages/` | unknown | Placeholder/package planning area. | Unknown | Yes | Maybe | Check imports and docs references. | `packages/` if packaging remains |
| `projects/` | workspace data | Generated news projects. | Yes | Yes | No | Backup and project-store migration. | `workspace/projects/news_to_short/` |
| `project_solar_vs_nuclear/` | experiment | Fixed solar-vs-nuclear project data and rendered artifacts. | Yes | Yes | No | Preserve as reference project; verify render wrappers. | `workspace/projects/experiments/solar_vs_nuclear/` |
| `scripts/` | application | Utility scripts such as MOSS voice tests. | Yes | Yes | Maybe | CLI replacements and import checks. | `apps/media_tools/scripts/` |
| `subtitles/` | unknown | Top-level subtitle folder. | Unknown | Yes | Maybe | Search references and backup contents. | `workspace/temp/subtitles/` or project-local subtitles |
| `tests/` | active core | Unit/integration-style test suite. | Yes | Maybe | No | CI and package import names. | `tests/` |
| `venv/` | external dependency | Local virtual environment. | No code import | Yes | Yes | Confirm reproducible dependencies. | Outside repo, ignored |
| `__pycache__/` | cache/temp | Python bytecode cache. | No | No | Yes | Ensure no source files inside. | Ignored cache |

## Future Cleanup Candidates

Candidate cleanup areas after backups and tests:

- `__pycache__/`: remove anytime after verifying only bytecode files.
- `venv/`: remove or move outside repo after dependency install process is documented.
- `outputs/`: archive or move after verifying user deliverables are backed up.
- `subtitles/`: classify after reference search.
- Root audit/implementation files: move into `docs/` after preserving history and updating links.
- Duplicate old provider/download code: deprecate only after wrappers and tests cover old commands.

## Do Not Delete Without Owner Approval

- `.env`.
- `assets/`.
- `manual_assets/`.
- `projects/`.
- `project_solar_vs_nuclear/`.
- `outputs/`.
- `MOSS_TTS_Nano/`.
- Any binary media, rendered videos, user voice samples or generated project data.

