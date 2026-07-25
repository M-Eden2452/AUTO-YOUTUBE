# Provider Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development for behavior changes. This plan is stored in the project root because the owner explicitly requested `IMPLEMENTATION_PROVIDER_FOUNDATION_PLAN.md`.

**Goal:** stabilize the future `src/news` pipeline by adding one provider foundation for search, normalized candidates, rights validation, selected-asset download, technical validation, license/provenance manifests and renderer-ready local paths.

**Architecture:** add canonical asset/license/provenance dataclasses and a provider-neutral contract under `src/assets`; adapt Pexels/Pixabay to the contract while preserving old function imports; integrate the new path into `src/news/asset_manager.py` without adding a breaking top-level pipeline stage. Existing projects and manifests without `schema_version` remain readable as legacy version 0.

**Tech Stack:** Python 3.10, dataclasses, standard library, `requests`, Pillow, FFmpeg/FFprobe via subprocess where available.

---

## Baseline Snapshot

- Project root: `G:\Projects\AI-YouTube`
- Git branch: `master`
- Git commit before implementation: `adb40fa944318646aef66102cbb1352e40b7cacc`
- Python: `Python 3.10.11`
- FFmpeg: available as `C:\Users\Dyma\scoop\shims\ffmpeg.exe`
- FFprobe: available as `C:\Users\Dyma\scoop\shims\ffprobe.exe`
- Existing worktree before implementation already contained modified/untracked files, including `.gitignore`, `pipeline.py`, `requirements.txt`, audit files, `src/news`, `src/assets`, `src/audio`, `src/production_plan`, tests and project data.
- Live API calls planned: none in tests.
- Paid API calls planned: none.
- Real `assets/library/metadata/media_index.json` migration planned: no.

## Audit Files Reviewed

- `PROJECT_AUDIT_INDEX.md`
- `PROJECT_AUDIT_OVERVIEW.md`
- `PROJECT_AUDIT_ARCHITECTURE.md`
- `PROJECT_AUDIT_PIPELINES.md`
- `PROJECT_AUDIT_COMPONENTS.md`
- `PROJECT_AUDIT_RISKS_TESTS.md`
- `PROJECT_AUDIT_ROADMAP.md`
- `PROJECT_AUDIT_SNAPSHOT.json`
- `PROJECT_AUDIT.md`

The audit was used as orientation only. Current code was rechecked before planning.

## Current Asset Models Found

- `src/news/models.py::AssetRights`: minimal rights status object with `allowed_for_render`.
- `src/news/asset_manager.py`: manifest dictionaries with `asset_id`, `provider`, `type`, `source_url`, `source_page`, `author`, `license`, `rights_status`, `allowed_for_render`, `path`, `downloaded_path`.
- `src/media_library.py`: legacy media index records with `id`, `type`, `provider`, `source_url`, `download_url`, `local_path`, `thumbnail_path`, `keywords`, `mood`, `width`, `height`, `duration`, `fps`, `license_note`, `downloaded_at`, `used_in`.
- `src/assets/semantic_selection/models.py::SemanticScene`: semantic scene schema used for query generation/ranking.
- `project_solar_vs_nuclear/03_stock/selected_sources.json`: project-only selected source records.
- `src/production_plan/youtube_shorts.py` and `src/production_plan/solar_vs_nuclear_render.py`: project-specific selected asset dictionaries.

## Current Provider Implementations Found

- `src/providers/pexels_provider.py`: old official API wrapper functions `search_videos()` and `search_images()`, both landscape-biased.
- `src/providers/pixabay_provider.py`: old official API wrapper functions `search_videos()`, `search_images()`, `search_music()`.
- `src/providers/unsplash_provider.py`: old image-only wrapper. It will not be extended in this stage.
- `src/news/asset_manager.py::PexelsAssetProvider`, `PixabayAssetProvider`, `UnsplashAssetProvider`: news-specific `search()` only providers.
- `src/news/stock_video_downloader.py`: separate news downloader not called by main news pipeline.
- `src/video_asset_engine.py` and `src/asset_finder.py`: old documentary search/download paths.
- `src/production_plan/solar_vs_nuclear_render.py`: fixed project stock search/download.
- `legacy/download_broll.py`: legacy Pexels downloader.

## Current `asset_search` Path

```text
src/news/pipeline.py::_dispatch_stage("asset_search")
  -> build_asset_search_manifest(job, plan, dry_run)
  -> src/news/asset_manager.py::build_news_asset_manifest()
  -> build_assets_manifest()
  -> analyze_scene()
  -> ordered_queries()
  -> provider.search(query, scene)
  -> _rank_provider_results()
  -> select_best_candidate()
  -> write assets/assets_manifest.json and missing_assets.json
```

Current gap: selected provider candidates are metadata-only and usually do not have a renderer-ready `path`.

## Current Final Renderer Path

```text
src/news/pipeline.py::_dispatch_stage("final_render")
  -> quality_report must be passed
  -> src/news/final_renderer.py::render_final_video()
  -> _create_scene_segments()
  -> selected_asset["path"]
  -> FFmpeg render segment
```

Current gap: renderer requires local files, but the main `asset_search` stage does not guarantee them.

## Compatible Architecture To Implement

### New neutral modules

- Create `src/assets/models.py`
  - `AssetLicense`
  - `AssetProvenance`
  - `AssetCandidate`
  - `DownloadedAsset`
  - `ProviderCapabilities`
  - legacy compatibility readers and manifest serializers.

- Create `src/assets/provider_contract.py`
  - `StockProvider` protocol.
  - `AssetSearchRequest`, `DownloadContext`, `AssetPreview`, `ProviderHealth`.
  - typed provider errors.
  - rights gate helpers.

- Create `src/assets/http_client.py`
  - `ProviderHttpClient`.
  - retry and request helpers.
  - streaming atomic download to `.part`.

- Create `src/assets/download.py`
  - `download_candidate_asset()`.
  - SHA-256 generation.
  - image/video technical validation.
  - local filename generation.

- Create `src/providers/fake_provider.py`
  - deterministic no-network `FakeStockProvider`.
  - success, rate-limit, invalid-file and unknown-license modes.

### Existing modules to modify

- Modify `src/providers/pexels_provider.py`
  - add `PexelsStockProvider`.
  - keep `search_videos()` and `search_images()` compatibility functions.
  - avoid landscape-only search for the new contract.

- Modify `src/providers/pixabay_provider.py`
  - add `PixabayStockProvider`.
  - keep `search_videos()`, `search_images()`, `search_music()`.
  - normalize tags, preview, author and direct download URLs.

- Modify `src/providers/__init__.py`
  - export new provider classes and keep old aliases.

- Modify `src/news/asset_manager.py`
  - support both old `AssetProvider.search(query, scene)` and new `StockProvider.search(AssetSearchRequest)`.
  - inside `asset_search`, after ranking, run rights gate and download only selected candidates.
  - fallback to next ranked candidate on download/validation/license failure.
  - write provider attempts, provider errors, ranked candidates, selected asset, download status, checksum, technical validation, license, provenance.
  - register new downloaded assets in media library only when downloaded and safe.
  - keep direct calls from old tests working.

- Modify `src/news/pipeline.py`
  - pass project root/job context to asset search.
  - keep stage list unchanged.

- Modify `src/news/final_renderer.py`
  - accept `path`, `local_path` or `downloaded_path`.
  - still reject missing local files.

- Modify `src/news/quality_check.py`
  - validate local file existence, checksum/technical validation, license/provenance presence, `allowed_for_render=true`, `review_required=false`.
  - keep legacy manifests readable but stricter for new `schema_version`.

- Modify `src/media_library.py`
  - extend normalized schema for new records.
  - add compatibility reader for legacy records.
  - add dry-run migration report.
  - add checksum duplicate support.
  - do not auto-migrate real `media_index.json`.

- Modify `src/assets/__init__.py`
  - export canonical models and helpers.

### Tests to add/modify

- Add `tests/test_asset_foundation_models.py`.
- Add `tests/test_asset_foundation_providers.py`.
- Add `tests/test_asset_foundation_http_download.py`.
- Add/extend `tests/test_news_to_short_assets.py`.
- Add/extend `tests/test_media_library.py`.
- Add/extend `tests/test_news_to_short_pipeline.py` for fake provider no-network asset roundtrip.
- Add/extend `tests/test_news_to_short_renderer.py` only where renderer local-path compatibility matters.

## Risks

- Existing tests use old fake provider objects that implement only `search(query, scene)`. The implementation must preserve that path.
- Existing manifests use `type`, `path`, `source_page`; canonical models use `media_type`, `local_path`, `source_page_url`. Adapters must keep both.
- Current quality check hard-codes a minimum count of downloaded real videos. This may need adjustment so it validates the selected assets instead of a fixed count that can block valid image-based or short-scene projects.
- Real media library contains legacy records without strong rights metadata. New news pipeline must not treat those as safe automatically.
- Pexels/Pixabay live calls must not happen during tests; all provider tests must mock HTTP/session responses.
- `src/production_plan` and `anime_factory` must not be refactored in this stage.

## Test Plan

### Baseline before production code changes

Run with bytecode disabled:

```text
python -B -m unittest tests.test_news_to_short_models tests.test_news_to_short_pipeline tests.test_news_to_short_assets tests.test_semantic_asset_selection tests.test_media_library tests.test_news_to_short_renderer
```

Record failures as baseline.

### TDD red tests

Run individual tests after adding them and before implementation:

```text
python -B -m unittest tests.test_asset_foundation_models
python -B -m unittest tests.test_asset_foundation_providers
python -B -m unittest tests.test_asset_foundation_http_download
python -B -m unittest tests.test_news_to_short_assets
python -B -m unittest tests.test_media_library
python -B -m unittest tests.test_news_to_short_pipeline
```

Expected before implementation: new imports/functions fail.

### After implementation

Run targeted tests:

```text
python -B -m unittest tests.test_asset_foundation_models tests.test_asset_foundation_providers tests.test_asset_foundation_http_download tests.test_news_to_short_models tests.test_news_to_short_pipeline tests.test_news_to_short_assets tests.test_semantic_asset_selection tests.test_media_library tests.test_news_to_short_renderer
```

Then run full local unittest discovery without live API:

```text
python -B -m unittest discover tests
```

### Import checks

```text
python -B -c "import pipeline; import apps.news_to_short.main; import src.news.pipeline; import src.news.asset_manager; import src.providers.pexels_provider; import src.providers.pixabay_provider; import src.assets.models; import src.assets.provider_contract"
```

### JSON validation

Validate `IMPLEMENTATION_PROVIDER_FOUNDATION_SNAPSHOT.json` after creation with `ConvertFrom-Json`.

## Completion Criteria

- Unified provider contract exists.
- Canonical asset/license/provenance models exist.
- Pexels/Pixabay implement the contract while old functions remain.
- FakeStockProvider exists and has deterministic no-network behavior.
- News `asset_search` can search, select, download, validate, checksum, save provenance/license and pass local path to renderer.
- Quality check rejects unknown/review-required rights and missing local files.
- Legacy manifests remain readable.
- Media library migration dry-run exists and does not modify the real index automatically.
- Targeted tests pass or baseline unrelated failures are documented.
- No live or paid API calls are performed.

