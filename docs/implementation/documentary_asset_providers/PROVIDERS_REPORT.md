# New Documentary Asset Providers Report

## Summary

Implemented four new documentary asset sources behind the existing Provider Foundation:

- `WikimediaCommonsStockProvider`
- `NasaImageLibraryStockProvider`
- `InternetArchiveStockProvider`
- `EnvatoManualProvider`

The automatic provider chain remains:

```text
scene -> semantic queries -> provider routing -> provider search -> normalized candidates
-> metadata ranking -> centralized license policy -> selected candidate
-> selected-only download/import -> technical validation -> SHA-256
-> provenance/license/local path -> quality check -> renderer
```

No UI, vision API, frame sampling, LLM visual reranking, browser scraping, automated Envato download, paid API call, media-index migration apply, renderer refactor, audio refactor or legacy deletion was implemented.

## Baseline

- Working directory: `G:\Projects\AI-YouTube`
- Branch: `master`
- Commit before implementation: `adb40fa944318646aef66102cbb1352e40b7cacc`
- Python: `Python 3.10.11`
- FFmpeg/FFprobe: available, `8.1.1-full_build-www.gyan.dev`
- Baseline full suite before production-code changes: `Ran 117 tests - OK`
- Real media index SHA-256 before and after: `61B2C5B89F353659ACD48E299DEA3CE6478F28FA968B9149E615DD2051A30385`

## Actual Architecture

The stage extends the existing foundation instead of adding a parallel architecture:

- `AssetCandidate`, `DownloadedAsset`, `AssetLicense`, `AssetProvenance`, `AssetSearchRequest`, `ProviderCapabilities`, `StockProvider`, `ProviderHttpClient`, `download_candidate_asset()` and centralized license policy are reused.
- New providers normalize search results into `AssetCandidate`.
- Downloads go through the common `.part`/validation/SHA-256 helper.
- Policy decisions are applied before automatic render selection and again during quality check.
- `src/news/asset_manager.py` keeps the existing `asset_search` stage but now records per-scene routing decisions.
- `src/news/exporter.py` now also generates project-level attribution/source files.

## Created Providers

### Wikimedia Commons

File: `src/providers/wikimedia_commons_provider.py`

- Uses MediaWiki Action API at `https://commons.wikimedia.org/w/api.php`.
- Searches File namespace only.
- Supports image and video candidates.
- Reads `imageinfo` and `extmetadata`.
- Normalizes page id, title, source page URL, original URL, thumbnail URL, mime, dimensions, duration, author/artist, credit, license short name, license URL, usage terms, attribution, categories, description, timestamp and raw metadata.
- Download is selected-candidate only and uses the common helper.

### NASA Image and Video Library

File: `src/providers/nasa_images_provider.py`

- Uses `https://images-api.nasa.gov`.
- Supports `/search`, `/asset/{nasa_id}` and `/metadata/{nasa_id}`.
- Supports images and videos.
- Selects one suitable rendition and ignores JSON metadata/caption files as media.
- Stores NASA id, title, description, keywords, media type, date, center, creator, location, preview URL, source page, original URL, metadata URL, captions URL and available renditions.

### Internet Archive

File: `src/providers/internet_archive_provider.py`

- Uses Advanced Search API and selected item `/metadata/{identifier}`.
- Normalizes identifier, title, description, creator, collection, mediatype, date/year, subject, license URL, rights, public date and downloads.
- Resolves selected media file only after candidate selection.
- Excludes metadata, thumbnails, torrents, XML, SQLite, JSON and service files.
- Prefers MP4/H.264 derivatives and avoids huge masters when a usable derivative exists.

### Envato Manual

File: `src/providers/envato_manual_provider.py`

- Not an automatic stock provider.
- Generates 3-8 English search queries and public Envato search URLs.
- Saves manual request manifests.
- Opens a browser only when explicitly requested.
- Imports a user-downloaded local file only when source URL, item id, author, license proof and project registration confirmation are supplied.
- Stores proof by local reference under project metadata/licenses.
- Never logs credentials and never downloads from Envato automatically.

## Provider Capabilities

- Wikimedia: search, preview, download, license metadata, image/video.
- NASA Images: search, preview, download, license metadata, image/video.
- Internet Archive: search, preview, download, license metadata, image/video.
- Envato Manual: manual import and license metadata only; no automatic search candidate and no automatic download.
- Pexels/Pixabay remain StockProvider-compatible.
- Local Library remains schema-v1 safe-only.

## Provider Routing

File: `src/assets/provider_routing.py`

Routing is non-LLM and configurable by inputs:

- subject/action/environment/location text
- exact entity/history context
- media type
- provider capabilities
- enabled status
- policy eligibility

Recorded output:

- ordered provider list
- reason per provider
- skipped provider reasons
- fallback order

Examples covered by tests:

- NASA scene prefers NASA after local library.
- Historical/archive scene prefers Wikimedia and Internet Archive over generic stock.
- Generic nature scene prefers Local Library, Pexels and Pixabay.
- Rare exact/scientific object prefers Wikimedia.
- Envato is manual fallback only.
- Disabled and policy-blocked providers are skipped.

## Policy Decisions

File: `config/license_policy.json`

Policy now distinguishes:

- `internal_content_production`
- `public_multi_user_product`

Pexels/Pixabay:

- Internal production is allowed only with preserved source page, provider asset id, download URL, terms/license metadata and no detected prohibited use or standalone stock redistribution.
- Public multi-user product remains review-required/blocked pending commercial audit.
- UI attribution requirements are preserved in policy metadata.

Wikimedia:

- Auto-allowed: Public Domain, CC0, CC BY 2.0/2.5/3.0/4.0 when required metadata is clear.
- Review-required: CC BY-SA, GFDL, Free Art License, multiple licenses, unknown CC versions, missing URL, conflicting metadata, unclear author/rationale, non-copyright restrictions.
- Unknown rights blocked.

NASA:

- Auto-allowed only for documentary/editorial/educational/informational context with NASA as source, no endorsement implication and no third-party/clearance warning.
- People, astronauts/employees, logos/emblems, promotional/merchandising, unclear ownership and metadata conflicts are review-required.
- The implementation does not treat all NASA library content as automatically Public Domain.

Internet Archive:

- Auto-allowed only for explicit CC0, sufficiently documented Public Domain, CC BY 3.0/4.0 with author, or trusted configured collections.
- Missing license, All Rights Reserved, NC/ND, restricted/borrow-only, copyright warnings and unknown status are blocked.

Envato:

- Allowed only after manual import with proof and project registration confirmation.
- Missing source/proof/confirmation is review-required and will fail quality check.

Full details are in `LICENSE_POLICY_DECISIONS.md`.

## Search Logic

- Wikimedia: Action API `list=search` with `srnamespace=6`, followed by `prop=imageinfo` for result titles.
- NASA: `/search` with media type, then one selected item asset/metadata expansion during provider normalization.
- Internet Archive: Advanced Search with conservative fields, item metadata only for selected file resolution.
- Envato: generated public search URLs only; no automatic search candidates.

## File Selection Logic

- Wikimedia: original URL from `imageinfo.url`; thumbnail from `thumburl`.
- NASA: image/video rendition chosen from `/asset/{nasa_id}`; JSON metadata and captions are excluded from media selection, captions URL is preserved.
- Internet Archive: service files excluded; MP4/H.264 derivatives preferred over huge masters.
- Envato: user-selected local file only.

## Download Logic

- Automatic providers download only the selected candidate.
- Download helper uses `.part`, content checks, validation, atomic replace, SHA-256 and provenance.
- Envato does not download from Envato; import copies a local user-downloaded file and validates it.

## Attribution Export

File: `src/assets/attribution_export.py`

Generated per project:

- `assets/sources.json`
- `assets/ATTRIBUTION.md`
- `assets/youtube_sources.txt`

Rules:

- Wikimedia required credits are retained.
- NASA is credited as source with no endorsement wording.
- Internet Archive credit is based on actual license metadata.
- Pexels/Pixabay credit metadata is retained.
- Envato certificate/proof content and local absolute paths are not published in `youtube_sources.txt`.

## Diagnostics

File: `src/assets/provider_diagnostics.py`

Offline diagnostics now include:

- Wikimedia
- NASA Images
- Internet Archive
- Envato Manual
- Pexels
- Pixabay
- Local Library
- Fake

Fields include enabled/configured/API-key/user-agent booleans, search/preview/download/manual import/license support, policy status, owner approval, live status and routing priority.

Filters:

- `python -B pipeline.py provider-diagnostics --provider wikimedia`
- `python -B pipeline.py provider-diagnostics --provider nasa`
- `python -B pipeline.py provider-diagnostics --provider internet_archive`
- `python -B pipeline.py provider-diagnostics --provider envato_manual`

Live mode is explicit and search-only for public APIs.

## Envato Manual Workflow

Prepare:

```powershell
python -B pipeline.py envato-manual prepare --project-id <id> --scene-id <id>
```

Options:

- `--open-browser`
- `--query`
- `--limit`

Import:

```powershell
python -B pipeline.py envato-manual import --project-id <id> --scene-id <id> --file <local-file> --source-url <envato-item-url> --item-id <item-id> --author <author> --license-proof <proof-file> --confirm-project-registration
```

Without source URL, item id, author, proof and registration confirmation, imported material remains review-required and does not pass quality check.

## Mocked Test Results

- New provider/routing/attribution tests: `Ran 16 tests - OK`
- Provider foundation/news/quality/renderer targeted tests: `Ran 54 tests - OK`
- Policy regression targeted tests: `Ran 31 tests - OK`
- Full mocked discovery after live diagnostics: `Ran 134 tests - OK`

Ordinary tests remain network-blocked by `tests.network_guard`.

## Live Diagnostic Results

- Wikimedia: HTTP 200, one File namespace search request, 1 result, no media download.
- NASA Images: HTTP 200, one search request, 1 result, no asset rendition download.
- Internet Archive: HTTP 200, one advanced search request, 1 result, no item file download.
- Envato Manual: public search URL generated only, no HTTP media request, no login and no download.

See `LIVE_DIAGNOSTICS.txt`.

## Compatibility

- Existing provider foundation tests remain green.
- Existing Pexels/Pixabay provider classes still support old search helper functions.
- `asset_search` stage structure is preserved.
- Renderer still receives `path`/`local_path`/`downloaded_path`.
- Quality check continues to enforce schema-v1 license/provenance/local-file/SHA/validation requirements.
- Real media index was not modified.

## Files Created

- `docs/implementation/documentary_asset_providers/PROVIDERS_PLAN.md`
- `docs/implementation/documentary_asset_providers/PROVIDERS_REPORT.md`
- `docs/implementation/documentary_asset_providers/PROVIDERS_SNAPSHOT.json`
- `docs/implementation/documentary_asset_providers/TEST_RESULTS.txt`
- `docs/implementation/documentary_asset_providers/LIVE_DIAGNOSTICS.txt`
- `docs/implementation/documentary_asset_providers/LICENSE_POLICY_DECISIONS.md`
- `src/assets/provider_routing.py`
- `src/assets/attribution_export.py`
- `src/providers/wikimedia_commons_provider.py`
- `src/providers/nasa_images_provider.py`
- `src/providers/internet_archive_provider.py`
- `src/providers/envato_manual_provider.py`
- `tests/test_documentary_asset_providers.py`
- `tests/test_provider_routing.py`
- `tests/test_attribution_export.py`

## Files Modified

- `config/license_policy.json`
- `pipeline.py`
- `src/assets/__init__.py`
- `src/assets/download.py`
- `src/assets/license_policy.py`
- `src/assets/provider_diagnostics.py`
- `src/news/asset_manager.py`
- `src/news/exporter.py`
- `src/providers/__init__.py`
- `tests/test_asset_foundation_providers.py`
- `tests/test_provider_foundation_hardening.py`

## Remaining Issues

- No UI/manual review screen exists yet.
- Real local media library still needs reviewed migration; this stage does not run apply.
- NASA policy remains conservative and may over-review people/logos/courtesy metadata.
- Internet Archive rights remain conservative because IA does not guarantee copyright status.
- Envato import is CLI/manual only.
- Full suite still emits a non-fatal legacy MoviePy cleanup warning.

## Readiness For Visual Reranking

Ready for a future visual reranking stage at the metadata/manifest boundary:

- candidates are normalized
- raw provider metadata snapshots are preserved
- routing reasons are recorded
- license decisions are centralized
- renderer receives local validated paths only

Recommended next stage: add visual preview/reranking service boundaries with fixture-only tests first, then manual review UX. Do not add vision API calls until policy and review gates are visible to the user.
