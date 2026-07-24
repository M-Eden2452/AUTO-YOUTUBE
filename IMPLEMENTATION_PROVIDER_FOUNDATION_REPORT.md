# Provider Foundation Implementation Report

## 1. Summary

Implemented the first architecture stabilization step for the future `src/news` pipeline. The new path now supports:

```text
scene -> semantic queries -> provider search -> normalized candidates -> rights gate
-> candidate selection -> selected asset download -> technical validation
-> SHA-256 -> license/provenance manifest -> local path -> final renderer
```

No Wikimedia, NASA, Internet Archive, Envato, Storyblocks, vision API, LLM ranking, UI, solar refactor or anime integration was implemented.

Important note on API safety: no paid ElevenLabs/OpenAI calls were performed. During one intermediate full-suite run before test isolation was tightened, existing tests could see provider environment variables and may have attempted live free stock-provider calls. After that, affected tests were patched to force fake/empty providers, and the final targeted/full test runs were no-network for Pexels/Pixabay.

## 2. Baseline

- Project root: `G:\Projects\AI-YouTube`
- Git branch: `master`
- Commit before implementation: `adb40fa944318646aef66102cbb1352e40b7cacc`
- Python: `Python 3.10.11`
- FFmpeg: available
- FFprobe: available
- Baseline targeted tests before production code changes: `27 tests OK`
- Initial worktree was already dirty and contained many untracked project areas.

## 3. What Was Implemented

### Canonical asset models

Created `src/assets/models.py` with:

- `AssetCandidate`
- `DownloadedAsset`
- `AssetLicense`
- `AssetProvenance`
- `ProviderCapabilities`

The models read legacy dicts without `schema_version` as version 0 and write new manifests with `schema_version: 1`. Manifest serialization keeps compatibility aliases:

- `media_type` and `type`
- `local_path`, `path`, `downloaded_path`
- `source_page_url`, `source_page`, `source_url`
- top-level `rights_status`, `allowed_for_render`, `review_required`

### Provider contract

Created `src/assets/provider_contract.py` with:

- `StockProvider`
- `AssetSearchRequest`
- `DownloadContext`
- `AssetPreview`
- `ProviderHealth`
- typed errors for configuration, auth, rate limit, timeout, network, invalid response, no results, download failure, validation failure and license review.

### HTTP and download foundation

Created:

- `src/assets/http_client.py`
- `src/assets/download.py`

Implemented:

- requests Session support;
- explicit User-Agent;
- configurable timeout;
- bounded retries;
- exponential backoff;
- `Retry-After` for HTTP 429;
- no retry for 401/403;
- streaming downloads to `.part`;
- cleanup on error;
- content type and content length checks;
- maximum/minimum file size checks;
- atomic replace after success;
- SHA-256;
- Pillow image validation;
- FFprobe video validation.

### Pexels and Pixabay

Modified:

- `src/providers/pexels_provider.py`
- `src/providers/pixabay_provider.py`

Added:

- `PexelsStockProvider`
- `PixabayStockProvider`

Old compatibility functions remain:

- `search_videos()`
- `search_images()`
- `search_music()` for Pixabay

The new providers normalize:

- provider asset id;
- media type;
- source page URL;
- preview URL;
- direct download URL;
- author;
- width/height/duration;
- orientation;
- tags where available;
- license;
- provenance;
- crop suitability score.

For Shorts, the new Pexels provider requests `portrait`; Pixabay video candidates are locally ranked for vertical orientation because its video endpoint does not provide the same simple orientation filter.

### Fake provider

Created `src/providers/fake_provider.py`.

`FakeStockProvider`:

- uses no network;
- returns deterministic image/video candidates;
- copies local fixtures on download;
- writes license/provenance;
- computes checksum through the common download helpers;
- supports success, unknown-license, rate-limit and invalid-file modes.

### Local Library provider/source

Created `src/providers/local_library_provider.py`.

`LocalLibraryStockProvider`:

- reads a supplied index or the existing media index;
- returns only current schema-safe records;
- blocks legacy records without schema/version/license/provenance;
- validates existing local files without copying them;
- computes checksum when absent for the selected local asset only.

The existing local library search inside `src/news/asset_manager.py` remains for backward compatibility.

### News asset_search integration

Modified `src/news/asset_manager.py`.

The existing stage list is unchanged. Inside `asset_search`, the new flow now:

1. analyzes scene semantics;
2. builds ordered semantic queries;
3. searches user assets;
4. searches local library;
5. searches Pexels/Pixabay through the new `StockProvider` contract;
6. normalizes candidates;
7. records provider attempts and errors;
8. ranks candidates through existing semantic ranker;
9. enforces rights gate;
10. downloads only the selected candidate;
11. falls back to the next ranked candidate on license/download/validation failure;
12. validates the downloaded file;
13. computes SHA-256;
14. writes license/provenance/technical validation/local path into selected asset;
15. records missing scenes without false completed status.

### Renderer compatibility

Modified `src/news/final_renderer.py`.

Renderer now accepts:

- `path`
- `local_path`
- `downloaded_path`

It still fails if no actual local file exists.

### Quality gate

Modified `src/news/quality_check.py`.

For new `schema_version >= 1` manifests, quality check now validates:

- selected asset exists;
- local file exists;
- checksum exists;
- technical validation has `status: passed`;
- license object exists;
- provenance object exists;
- `allowed_for_render` is true;
- `review_required` is false.

Legacy manifests without `schema_version` still use the older checks.

### Media library

Modified `src/media_library.py`.

Added:

- checksum-based duplicate lookup;
- `build_media_library_migration_report()`;
- extended normalization for new records.

The real `assets/library/metadata/media_index.json` was not migrated or rewritten. Verification showed:

```text
version: 1
total: 64
schema_version_records: 0
current_license_records: 0
```

### Stock downloader compatibility

Modified `src/news/stock_video_downloader.py`.

`download_stock_videos_for_project()` now delegates to `build_news_asset_manifest()` and therefore uses the new provider/download foundation. The old implementation remains as `_legacy_download_stock_videos_for_project()` for compatibility/reference.

## 4. Files Created

- `IMPLEMENTATION_PROVIDER_FOUNDATION_PLAN.md`
- `IMPLEMENTATION_PROVIDER_FOUNDATION_REPORT.md`
- `IMPLEMENTATION_PROVIDER_FOUNDATION_SNAPSHOT.json`
- `src/assets/models.py`
- `src/assets/provider_contract.py`
- `src/assets/http_client.py`
- `src/assets/download.py`
- `src/providers/fake_provider.py`
- `src/providers/local_library_provider.py`
- `tests/test_asset_foundation_models.py`
- `tests/test_asset_foundation_providers.py`
- `tests/test_asset_foundation_http_download.py`
- `tests/test_news_to_short_quality_check.py`

## 5. Files Modified

- `src/assets/__init__.py`
- `src/providers/__init__.py`
- `src/providers/pexels_provider.py`
- `src/providers/pixabay_provider.py`
- `src/news/asset_manager.py`
- `src/news/pipeline.py`
- `src/news/final_renderer.py`
- `src/news/quality_check.py`
- `src/news/stock_video_downloader.py`
- `src/media_library.py`
- `tests/test_media_library.py`
- `tests/test_news_to_short_assets.py`
- `tests/test_news_to_short_pipeline.py`
- `tests/test_news_to_short_delivery.py`
- `tests/test_news_to_short_renderer.py`

Pre-existing modified tracked files not changed intentionally by this implementation:

- `.gitignore`
- root `pipeline.py`
- `requirements.txt`

## 6. Compatibility Wrappers Kept

- `src/providers/pexels_provider.py::search_videos`
- `src/providers/pexels_provider.py::search_images`
- `src/providers/pixabay_provider.py::search_videos`
- `src/providers/pixabay_provider.py::search_images`
- `src/providers/pixabay_provider.py::search_music`
- `src/news/asset_manager.py::PexelsAssetProvider`
- `src/news/asset_manager.py::PixabayAssetProvider`
- `src/news/asset_manager.py::UnsplashAssetProvider`
- `src/news/stock_video_downloader.py::_legacy_download_stock_videos_for_project`

## 7. Duplicates Still Remaining

Remaining by design for compatibility:

- old documentary providers/downloaders in `src/video_asset_engine.py` and `src/asset_finder.py`;
- project-specific stock logic in `src/production_plan/solar_vs_nuclear_render.py`;
- legacy b-roll downloader in `legacy/download_broll.py`;
- old voice paths outside `src/audio`;
- separate renderers for news, documentary, solar and anime.

## 8. New Schemas

Short asset manifest shape:

```json
{
  "schema_version": 1,
  "asset_id": "fake_scene_001_video_001",
  "provider": "fake",
  "provider_asset_id": "scene_001_video_001",
  "media_type": "video",
  "type": "video",
  "source_page_url": "https://fake.local/assets/...",
  "download_url": "file:///...",
  "local_path": "...",
  "path": "...",
  "downloaded_path": "...",
  "checksum_sha256": "...",
  "license": {
    "license_name": "fake_test_license",
    "rights_status": "licensed",
    "allowed_for_render": true,
    "review_required": false
  },
  "provenance": {
    "provider": "fake",
    "provider_asset_id": "...",
    "source_page_url": "...",
    "download_url": "...",
    "project_id": "...",
    "scene_id": "..."
  },
  "technical_validation": {
    "status": "passed"
  }
}
```

## 9. Error Handling and Retry

New provider/download code uses typed errors. API requests retry only retryable cases:

- timeout;
- connection errors;
- HTTP 429;
- HTTP 5xx.

No retry for:

- 400;
- 401;
- 403;
- invalid payload;
- license review required.

Errors are written into `provider_errors`, `provider_attempts`, scene `provider_attempts`, scene `download_attempts` and `missing_scenes`.

## 10. Tests Added

Added tests for:

- asset schema serialization/deserialization;
- legacy manifest compatibility;
- Pexels mocked normalization;
- Pixabay mocked normalization;
- vertical preference for Shorts;
- retry on timeout/429/5xx;
- no retry on 401;
- `.part` cleanup;
- SHA-256 generation;
- invalid file rejection;
- unknown rights blocking;
- attribution/provider metadata preservation;
- media library migration dry-run;
- duplicate checksum detection;
- fake provider search/download;
- Local Library provider;
- news asset_search integration;
- quality check rejection for missing local files;
- no-network fake-provider pipeline to final render;
- Unicode/Windows-like path roundtrip.

## 11. Test Results

Baseline before implementation:

```text
python -B -m unittest tests.test_news_to_short_models tests.test_news_to_short_pipeline tests.test_news_to_short_assets tests.test_semantic_asset_selection tests.test_media_library tests.test_news_to_short_renderer
Ran 27 tests in 14.350s
OK
```

Red tests before implementation:

```text
Ran 26 tests
FAILED (failures=2, errors=13)
```

Targeted after implementation:

```text
python -B -m unittest tests.test_asset_foundation_models tests.test_asset_foundation_providers tests.test_asset_foundation_http_download tests.test_news_to_short_models tests.test_news_to_short_pipeline tests.test_news_to_short_assets tests.test_news_to_short_quality_check tests.test_semantic_asset_selection tests.test_media_library tests.test_news_to_short_renderer tests.test_news_to_short_delivery
Ran 47 tests in 25.634s
OK
```

Full local unittest discovery:

```text
python -B -m unittest discover tests
Ran 107 tests in 27.319s
OK
```

Note: the full suite still prints an existing MoviePy cleanup warning from `FFMPEG_AudioReader.__del__`, but the process exits 0 and all tests pass.

## 12. Baseline Failures

No targeted baseline failures were observed before implementation.

During full discovery, a test-order issue exposed that `.env` loading could make existing tests see real provider keys. This may have caused an intermediate live stock-provider attempt before the tests were isolated. It was fixed by patching those tests to force `create_default_asset_providers=[]` when they are meant to be no-network. Final verification runs were isolated.

## 13. Not Touched Intentionally

- `PROJECT_AUDIT_*`
- existing `PROJECT_AUDIT.md`
- `.env`
- `assets/library/metadata/media_index.json`
- `anime_factory`
- `src/production_plan` behavior
- `legacy`
- old documentary pipeline architecture
- UI/API/publishing
- paid TTS/LLM behavior

## 14. Readiness For New Providers

The foundation is now ready for planning Wikimedia, NASA, Internet Archive, Local Library expansion and Envato Manual Provider, because the required extension points now exist:

- provider-neutral `AssetSearchRequest`;
- normalized `AssetCandidate`;
- `AssetLicense`;
- `AssetProvenance`;
- provider errors;
- download/validation/checksum helpers;
- rights gate;
- fake provider tests.

`ready_for_new_providers` is still not fully true for production rollout because remaining work is needed:

- license policy decisions per provider;
- migration strategy for the real media library;
- UI/manual review;
- broader e2e fixtures;
- cleanup of old duplicate providers.

## 15. Recommended Next Stage

Run a focused migration/design stage for the real media library and provider policy:

1. define legal license mappings for Pexels/Pixabay/Local assets;
2. add a non-destructive media library migration command;
3. quarantine legacy unknown assets by default;
4. add a provider diagnostics CLI;
5. only then implement Wikimedia/NASA/Internet Archive/Envato.
