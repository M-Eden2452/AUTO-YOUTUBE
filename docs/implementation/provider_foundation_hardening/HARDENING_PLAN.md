# Provider Foundation Hardening Plan

> Created before implementation for the Provider Foundation verification and hardening stage.

**Goal:** independently verify the implemented Provider Foundation, block accidental network access in ordinary tests, centralize conservative license decisions, add safe media-library migration workflows and provider diagnostics, and document the target architecture without moving or deleting project data.

**Architecture:** keep the existing provider contract and news pipeline shape, then add small shared services around it: a test-only network guard, a config-backed license policy under `src/assets`, a non-destructive media-library migration/diagnostics layer, and CLI entry points in the existing root dispatcher. No new external providers, UI, vision analysis, render refactor, voice refactor, mass file moves, or media-index mutation are in scope.

**Tech Stack:** Python 3.10, `unittest`, standard library JSON/socket/path helpers, existing `requests`, Pillow and FFmpeg/FFprobe validation.

---

## Baseline To Record

- Git branch, commit, `git status --short`, `git diff --stat`.
- Python version.
- FFmpeg and FFprobe availability.
- Real `assets/library/metadata/media_index.json` SHA-256 before and after.
- Baseline unittest discovery under a temporary no-network guard.

## Verification Scope

- Re-read the previous implementation/audit reports and compare claims with code.
- Verify `src/assets` models, `StockProvider`, HTTP retries, `Retry-After`, no retry for 401/403, `.part` download, atomic replace, partial cleanup, content type and length checks, maximum size checks, SHA-256, FFprobe/Pillow validation.
- Verify the news flow: scene, semantic queries, provider search, candidate normalization, ranking, rights gate, download, validation, checksum, license, provenance, local path, quality check and renderer.
- Verify legacy compatibility and confirm the real media index is not automatically migrated.

## Implementation Tasks

### Task 1: Test Network Guard

**Files:**
- Create: `tests/network_guard.py`
- Modify: tests that need to explicitly allow mocked HTTP only if necessary.
- Test: `tests/test_test_network_guard.py`

Steps:
- Add a socket-level guard that blocks external hosts by default during unittest runs.
- Allow localhost only for future local UI/dev-server tests.
- Provide an explicit env flag for live integration tests.
- Keep mocked HTTP tests unaffected because they do not use real sockets.
- Add a test that attempts an external socket connection and confirms it is blocked.

### Task 2: Central License Policy

**Files:**
- Create: `config/license_policy.json`
- Create: `src/assets/license_policy.py`
- Modify: `src/assets/models.py`
- Modify: `src/assets/provider_contract.py`
- Modify: provider modules and news asset manager where decisions are made.
- Modify: `src/news/quality_check.py`
- Tests: asset/provider/news quality tests.

Steps:
- Load a human-readable policy config with provider/media/license/source rules.
- Default unknown or incomplete rights to blocked/review-required.
- Require source URL and provider asset id for remote providers.
- Support manual/user declarations and owner approval status.
- Mark Pexels/Pixabay as owner-review-required, with policy links but no legal guarantee.
- Store a structured policy decision in selected asset manifests.
- Make quality check validate through the centralized policy decision for schema version 1.

### Task 3: Media Library Migration Workflow

**Files:**
- Modify: `src/media_library.py`
- Modify: `pipeline.py`
- Tests: `tests/test_media_library.py`

Steps:
- Add `media-library analyse`.
- Add `media-library migrate --dry-run`.
- Add `media-library migrate --apply`, but make apply require explicit confirmation, backup path, output path and a clean dry-run.
- Ensure dry-run creates a proposed output/report without writing the real index.
- Classify records as current safe, legacy complete/incomplete, missing file, unknown rights, missing source, duplicate URL/checksum, manual review and quarantine recommended.

### Task 4: Provider Diagnostics

**Files:**
- Create: `src/assets/provider_diagnostics.py`
- Modify: `pipeline.py`
- Tests: provider diagnostics tests.

Steps:
- Add a no-network diagnostics command by default.
- Report provider status, key configured true/false without secrets, capabilities, timeout, retries, health, policy status and owner approval status.
- Support `--live` as an explicit option only; do not run it in this task.

### Task 5: Architecture Documentation

**Files:**
- Create: `docs/architecture/TARGET_ARCHITECTURE.md`
- Create: `docs/architecture/CLEANUP_INVENTORY.md`

Steps:
- Document the target separation of applications, shared core, pipelines, providers, license/provenance, audio/TTS, rendering, media tools, browser automation, UI, channel presets, workspace data, cache/temp, tests, docs and legacy.
- Include the future local browser UI boundary and needed backend contracts.
- Inventory top-level folders/files without deleting or moving anything.

### Task 6: Final Verification And Reports

**Files:**
- Create: `docs/implementation/provider_foundation_hardening/HARDENING_REPORT.md`
- Create: `docs/implementation/provider_foundation_hardening/HARDENING_SNAPSHOT.json`
- Create: `docs/implementation/provider_foundation_hardening/TEST_RESULTS.txt`

Steps:
- Run targeted provider foundation, news pipeline, media library, quality check and renderer tests.
- Run full local unittest discovery with network guard and filled-env safety.
- Run import checks.
- Validate JSON files.
- Run migration analyse and dry-run only.
- Re-check media index SHA-256.
- Record files created/modified and remaining issues.

## Explicit Non-Goals

- No Wikimedia Commons, NASA, Internet Archive, Envato, Storyblocks or new paid services.
- No UI implementation.
- No vision analysis or frame sampling.
- No voice/render refactor.
- No mass project restructure.
- No legacy deletion.
- No cleanup of user projects, outputs, caches or binary media.
- No `.env` changes or secret disclosure.
- No automatic commit, branch switch, real media-index migration or live provider health check.

