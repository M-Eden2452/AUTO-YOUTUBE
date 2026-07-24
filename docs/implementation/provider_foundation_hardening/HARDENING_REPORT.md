# Provider Foundation Hardening Report

## Scope

This stage independently re-read the previous Provider Foundation plan/report/snapshot, all project audit documents, and the actual implementation code. The work stayed inside Provider Foundation verification and hardening only. No new providers were connected, no UI was implemented, no renderer or voice refactor was performed, no legacy cleanup was performed, and no media assets or user project outputs were deleted or moved.

## Baseline

- Working directory: `G:\Projects\AI-YouTube`
- Git branch before changes: `master`
- Git commit before changes: `adb40fa944318646aef66102cbb1352e40b7cacc`
- Python: `Python 3.10.11`
- FFmpeg: available, version `8.1.1-full_build`
- FFprobe: available, version `8.1.1-full_build`
- Real media index SHA-256 before dry-run: `61B2C5B89F353659ACD48E299DEA3CE6478F28FA968B9149E615DD2051A30385`
- Real media index SHA-256 after dry-run: `61B2C5B89F353659ACD48E299DEA3CE6478F28FA968B9149E615DD2051A30385`

## Verified Claims From Previous Report

Confirmed in code:

- A shared `StockProvider` contract exists.
- Canonical asset models exist under `src/assets/models.py`.
- `schema_version` is used by the new asset contract.
- Legacy asset manifests can still be read.
- `AssetLicense` and `AssetProvenance` are present.
- Pexels, Pixabay, Fake and Local Library providers implement the provider interface.
- HTTP retry handling exists, including `Retry-After`.
- HTTP 401 and 403 are not retried.
- Downloads use `.part` files and atomic replacement.
- Partial files are cleaned after failed downloads.
- Content-Type, Content-Length, maximum file size, SHA-256, FFprobe and Pillow validation are implemented.
- Provider errors are preserved when provider candidates fail.
- The renderer can receive local media paths from the selected asset manifest.
- Quality checks distinguish schema version 1 manifests from legacy data.
- No automatic migration of the real media library index is performed.

## Gaps Found

- Provider-supplied license flags were too trusted. Pexels and Pixabay candidates could arrive as `allowed_for_render=True` without a centralized owner-reviewed policy decision.
- Unknown or incomplete rights could pass through some paths because the previous rights gate read candidate fields directly.
- `AssetCandidate.to_dict()` treated `schema_version=0` as falsy and serialized legacy candidates as schema version 1.
- Manual/user assets were previously treated as `user_owned` just because a local path existed.
- Quality check did not enforce a centralized policy decision for schema version 1 selected assets.
- Ordinary tests had no built-in socket guard, so a filled `.env` could allow accidental live calls in future tests.
- Media library migration existed only as a basic report path, not as a full analyse/dry-run/apply workflow with backups and confirmation.
- Provider diagnostics did not exist as a single no-network command.

## Fixes Implemented

- Added a config-backed centralized license policy in `src/assets/license_policy.py` and `config/license_policy.json`.
- Added provider-specific policy entries for Pexels and Pixabay with `owner_review_required: true` and `owner_approval_status: pending`.
- Made unknown providers, unknown licenses, missing source, missing remote provider asset IDs, unconfirmed manual rights and legacy local records block automatic render.
- Added `policy_decision` and `rights_declaration` fields to asset manifests.
- Updated provider contract checks to call centralized policy before render eligibility is accepted.
- Updated Pexels, Pixabay, Fake and Local Library provider paths to attach policy decisions.
- Updated news asset selection to apply policy before selection and preserve policy reasons in fallback errors.
- Updated quality check so schema version 1 selected assets are validated through centralized policy.
- Fixed schema version 0 preservation in asset serialization.
- Added a socket-level default test network guard in `tests/network_guard.py`, automatically installed by `tests/__init__.py`.
- Added media library `analyse`, `migrate --dry-run` and guarded `migrate --apply` workflows.
- Added no-network provider diagnostics with optional explicit `--live`.
- Added target architecture and cleanup inventory docs without moving or deleting project files.

## Network Isolation

Ordinary unittest runs import `tests/__init__.py`, which installs `tests.network_guard`. The guard patches socket connection creation and blocks external hosts unless an explicit live-test environment flag is set. Localhost remains allowed for future local UI/dev-server tests. Mocked HTTP tests are unaffected because they do not open real sockets.

Live integration tests require an explicit flag such as `AI_YOUTUBE_ALLOW_LIVE_TESTS=1` or `AI_YOUTUBE_RUN_LIVE_TESTS=1`. No live flag was used in this stage.

## License Policy

The policy is default-deny. The decision records:

- provider
- media type
- license name and URL
- provider terms URL
- commercial use
- modification
- attribution
- review requirement
- render allowance
- policy version
- policy reviewed date
- owner approval status
- notes and reason

Pexels and Pixabay are represented as separate provider policies, but they remain owner-review-required. This does not claim a legal guarantee. Manual/user assets require an explicit rights declaration and confirmation status. Local Library legacy records are treated as `legacy_unknown` and blocked from automatic render until reviewed.

## Media Library Migration

The real index `assets/library/metadata/media_index.json` was not modified. Analyse and dry-run were run only against generated reports/proposed output under `docs/implementation/provider_foundation_hardening`.

Dry-run result:

- Total records: 64
- Current safe records: 0
- Review records: 5
- Quarantine-recommended records: 64

The workflow supports idempotent proposed output, quarantine classification, explicit apply confirmation, backup before apply, atomic write, schema checks and rollback through the backup file. The apply path was not run.

## Provider Diagnostics

The diagnostics command is available through:

```powershell
python -B pipeline.py provider-diagnostics
```

By default it performs no network requests. It reports provider name, enabled state, key configured true/false without exposing secrets, supported media types, search/preview/download/license support, timeout, retry count, offline health status, policy status and owner approval status.

The optional `--live` mode was implemented but was not run in this stage. When used later, it must perform at most one small provider request, must not download originals, and must not expose API keys.

## Test Results

Baseline before code changes:

- `python -B -m unittest discover tests`
- Result: `Ran 107 tests in 26.754s - OK`

After hardening:

- `python -B -m unittest tests.test_asset_foundation_models tests.test_asset_foundation_providers tests.test_asset_foundation_http_download tests.test_provider_foundation_hardening tests.test_test_network_guard tests.test_media_library tests.test_news_to_short_assets tests.test_news_to_short_quality_check`
- Result: `Ran 35 tests in 0.417s - OK`

- `python -B -m unittest tests.test_news_to_short_models tests.test_news_to_short_pipeline tests.test_news_to_short_delivery tests.test_news_to_short_renderer tests.test_semantic_asset_selection`
- Result: `Ran 22 tests in 29.885s - OK`

- `python -B -m unittest discover tests`
- Result: `Ran 117 tests in 27.160s - OK`

- Import checks: passed.
- JSON validation: passed for license policy, migration analyse/report/proposed output and hardening snapshot.

The full test suite still emits an ignored MoviePy cleanup warning from legacy MoviePy object finalization, but the command exits with status 0.

## Files Created

- `config/license_policy.json`
- `docs/architecture/CLEANUP_INVENTORY.md`
- `docs/architecture/TARGET_ARCHITECTURE.md`
- `docs/implementation/provider_foundation_hardening/HARDENING_PLAN.md`
- `docs/implementation/provider_foundation_hardening/HARDENING_REPORT.md`
- `docs/implementation/provider_foundation_hardening/HARDENING_SNAPSHOT.json`
- `docs/implementation/provider_foundation_hardening/TEST_RESULTS.txt`
- `docs/implementation/provider_foundation_hardening/media_library_analyse.json`
- `docs/implementation/provider_foundation_hardening/media_library_migration_proposed.json`
- `docs/implementation/provider_foundation_hardening/media_library_migration_report.json`
- `src/assets/license_policy.py`
- `src/assets/provider_diagnostics.py`
- `tests/__init__.py`
- `tests/network_guard.py`
- `tests/test_provider_foundation_hardening.py`
- `tests/test_test_network_guard.py`

## Files Modified

- `pipeline.py`
- `src/assets/__init__.py`
- `src/assets/models.py`
- `src/assets/provider_contract.py`
- `src/media_library.py`
- `src/news/asset_manager.py`
- `src/news/quality_check.py`
- `src/providers/fake_provider.py`
- `src/providers/local_library_provider.py`
- `src/providers/pexels_provider.py`
- `src/providers/pixabay_provider.py`
- `tests/test_asset_foundation_providers.py`
- `tests/test_media_library.py`
- `tests/test_news_to_short_assets.py`
- `tests/test_news_to_short_quality_check.py`
- `tests/test_news_to_short_renderer.py`
- `tests/test_semantic_asset_selection.py`

## Remaining Issues

- Pexels and Pixabay official terms still require owner review and approval before automatic production render.
- The real local media library needs a reviewed migration pass; dry-run recommends quarantine/review for all 64 records.
- Legacy module layout remains mixed by design in this stage; only target architecture and cleanup inventory were added.
- The full suite has a non-fatal legacy MoviePy cleanup warning.
- Live provider health checks were intentionally not run.

## Readiness For New Providers

The Provider Foundation is ready for the next implementation stage to add Wikimedia Commons, NASA, Internet Archive and an Envato Manual Provider behind the same conservative policy gates. New providers should start blocked or review-required until their provider policy, terms links and owner approval status are explicitly configured.

Recommended next stage: add the new providers one by one with mocked tests first, then add separate opt-in live diagnostics only after the policy owner approves the relevant terms.
