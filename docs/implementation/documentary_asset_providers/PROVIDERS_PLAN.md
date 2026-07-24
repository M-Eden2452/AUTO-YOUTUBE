# New Documentary Asset Providers Plan

> Created before production-code changes for the Wikimedia Commons, NASA Image and Video Library, Internet Archive, and Envato Manual Provider stage.

## Baseline

- Working directory: `G:\Projects\AI-YouTube`
- Current branch: `master`
- Commit hash before implementation: `adb40fa944318646aef66102cbb1352e40b7cacc`
- Started at: `2026-07-23T01:00:00+03:00`
- Python: `Python 3.10.11`
- FFmpeg: available, `8.1.1-full_build-www.gyan.dev`
- FFprobe: available, `8.1.1-full_build-www.gyan.dev`
- Real media index SHA-256 before implementation: `61B2C5B89F353659ACD48E299DEA3CE6478F28FA968B9149E615DD2051A30385`
- Baseline full suite command: `python -B -m unittest discover tests`
- Baseline result: `Ran 117 tests in 27.034s - OK`
- Baseline note: existing non-fatal MoviePy `FFMPEG_AudioReader.__del__` warning is still emitted.
- Ordinary tests network mode: blocked by `tests.network_guard`; no live flag used for baseline.

## Git Status Before Implementation

```text
 M .gitignore
 M pipeline.py
 M requirements.txt
 M src/media_library.py
 M src/providers/__init__.py
 M src/providers/pexels_provider.py
 M src/providers/pixabay_provider.py
 M tests/test_media_library.py
?? IMPLEMENTATION_PROVIDER_FOUNDATION_PLAN.md
?? IMPLEMENTATION_PROVIDER_FOUNDATION_REPORT.md
?? IMPLEMENTATION_PROVIDER_FOUNDATION_SNAPSHOT.json
?? PROJECT_AUDIT.md
?? PROJECT_AUDIT_ARCHITECTURE.md
?? PROJECT_AUDIT_COMPONENTS.md
?? PROJECT_AUDIT_INDEX.md
?? PROJECT_AUDIT_OVERVIEW.md
?? PROJECT_AUDIT_PIPELINES.md
?? PROJECT_AUDIT_RISKS_TESTS.md
?? PROJECT_AUDIT_ROADMAP.md
?? PROJECT_AUDIT_SNAPSHOT.json
?? anime_factory/
?? apps/
?? channels/nature_science_news_ru/
?? config/license_policy.json
?? docs/apps/
?? docs/architecture/
?? docs/implementation/
?? docs/project_map_and_app_split_plan.md
?? docs/superpowers/
?? outputs/audio_edits/
?? packages/
?? project_solar_vs_nuclear/
?? src/assets/
?? src/audio/
?? src/news/
?? src/production_plan/
?? src/providers/fake_provider.py
?? src/providers/local_library_provider.py
?? tests/__init__.py
?? tests/network_guard.py
?? tests/test_anime_factory_candidates.py
?? tests/test_anime_factory_cleanup.py
?? tests/test_anime_factory_dynamic_crop.py
?? tests/test_anime_factory_paths.py
?? tests/test_anime_factory_transcribe.py
?? tests/test_anime_factory_v3.py
?? tests/test_anime_factory_v4.py
?? tests/test_apps_structure.py
?? tests/test_asset_foundation_http_download.py
?? tests/test_asset_foundation_models.py
?? tests/test_asset_foundation_providers.py
?? tests/test_news_to_short_assets.py
?? tests/test_news_to_short_delivery.py
?? tests/test_news_to_short_models.py
?? tests/test_news_to_short_pipeline.py
?? tests/test_news_to_short_quality_check.py
?? tests/test_news_to_short_renderer.py
?? tests/test_provider_foundation_hardening.py
?? tests/test_semantic_asset_selection.py
?? tests/test_test_network_guard.py
?? tests/test_voice_workflow.py
?? tests/test_youtube_shorts_production_plan.py
```

## Git Diff Stat Before Implementation

```text
 .gitignore                        |   1 +
 pipeline.py                       | 107 +++++++++++++++-
 requirements.txt                  |   1 +
 src/media_library.py              | 251 ++++++++++++++++++++++++++++++++++++-
 src/providers/__init__.py         |   8 ++
 src/providers/pexels_provider.py  | 240 +++++++++++++++++++++++++++++++++++-
 src/providers/pixabay_provider.py | 252 +++++++++++++++++++++++++++++++++++++-
 tests/test_media_library.py       |  47 +++++++
 8 files changed, 896 insertions(+), 11 deletions(-)
```

## Current Provider Contracts

- `src/assets/models.py`
  - `AssetLicense`, `AssetProvenance`, `ProviderCapabilities`, `AssetCandidate`, `DownloadedAsset`
  - supports `schema_version`, local-path aliases, raw metadata, `policy_decision`, rights declaration, technical validation, SHA-256.
- `src/assets/provider_contract.py`
  - `StockProvider` protocol with `capabilities`, `search`, `get_preview`, `resolve_license`, `download`, `health_check`.
  - `AssetSearchRequest` and `DownloadContext`.
  - typed provider errors: configuration, authentication, rate limit, timeout, network, invalid response, no results, download, validation, license review.
- `src/assets/http_client.py`
  - `ProviderHttpClient` with retry, explicit user agent, timeout, JSON requests, streaming `.part` downloads and content size/type checks.
- `src/assets/download.py`
  - selected-candidate download only, `.part`, validation via Pillow/FFprobe, SHA-256, `DownloadedAsset` creation.
- `src/assets/license_policy.py`
  - config-backed default-deny centralized policy. Current Pexels/Pixabay are pending owner review.
- `src/assets/provider_diagnostics.py`
  - no-network diagnostics currently covering fake, local_library, Pexels, Pixabay and legacy Unsplash.
- `src/news/asset_manager.py`
  - semantic queries, provider search, metadata ranking, centralized policy, selected download, fallback, manifest/provenance/license.

## Files Planned To Create

- `src/assets/provider_routing.py`
- `src/assets/attribution_export.py`
- `src/providers/wikimedia_commons_provider.py`
- `src/providers/nasa_images_provider.py`
- `src/providers/internet_archive_provider.py`
- `src/providers/envato_manual_provider.py`
- `tests/test_documentary_asset_providers.py`
- `tests/test_provider_routing.py`
- `tests/test_attribution_export.py`
- `docs/implementation/documentary_asset_providers/PROVIDERS_REPORT.md`
- `docs/implementation/documentary_asset_providers/PROVIDERS_SNAPSHOT.json`
- `docs/implementation/documentary_asset_providers/TEST_RESULTS.txt`
- `docs/implementation/documentary_asset_providers/LIVE_DIAGNOSTICS.txt`
- `docs/implementation/documentary_asset_providers/LICENSE_POLICY_DECISIONS.md`

## Files Planned To Modify

- `config/license_policy.json`
- `pipeline.py`
- `src/assets/__init__.py`
- `src/assets/license_policy.py`
- `src/assets/provider_diagnostics.py`
- `src/news/asset_manager.py`
- `src/news/pipeline.py`
- `src/news/quality_check.py`
- `src/news/final_renderer.py`
- `src/media_library.py`
- `src/providers/__init__.py`
- `src/providers/pexels_provider.py`
- `src/providers/pixabay_provider.py`
- existing provider/news tests as needed for compatibility.

## New Provider Classes

- `WikimediaCommonsStockProvider`
  - official MediaWiki Action API at `https://commons.wikimedia.org/w/api.php`
  - no API key
  - image/video File namespace search, `imageinfo` and `extmetadata`, selected download only.
- `NasaImageLibraryStockProvider`
  - `https://images-api.nasa.gov`
  - no API key
  - `/search`, `/asset/{nasa_id}`, `/metadata/{nasa_id}`, captions metadata when available.
- `InternetArchiveStockProvider`
  - Advanced Search API plus `/metadata/{identifier}` and selected file download URL
  - no API key for public search/read.
- `EnvatoManualProvider`
  - not automatic
  - prepares English queries/search URLs/manifests and imports a user-downloaded local file only with source/proof/project registration confirmation.

## Policy Decisions

- Keep default-deny for unknown providers and unknown rights.
- Add policy contexts:
  - `internal_content_production`
  - `public_multi_user_product`
- For `internal_content_production`, allow Pexels/Pixabay only when required metadata is present, technical validation passes, prohibited-use flags are absent, and the asset is used inside the edited video instead of redistributed as standalone stock.
- For `public_multi_user_product`, keep Pexels/Pixabay blocked or review-required until a later commercial audit.
- Wikimedia auto-allow only recognized Public Domain, CC0, CC BY 2.0/2.5/3.0/4.0 with source page, license URL, attribution where required, commercial use and modifications allowed.
- Wikimedia review-required: CC BY-SA, GFDL, Free Art License, multiple licenses, unknown CC versions, missing URL, conflicting metadata, unclear author/public-domain rationale, non-copyright restriction warnings, personality/trademark/coat-of-arms warnings.
- NASA auto-allow only editorial/informational internal use with NASA as source, no endorsement implication, no third-party copyright/clearance warning, source page and `nasa_id` preserved.
- Internet Archive auto-allow only explicit CC0, sufficiently documented Public Domain, CC BY 3.0/4.0 with author, or trusted collection configured in policy. Missing/unknown/all-rights-reserved/NC/ND/restricted/borrow-only blocked.
- Envato imported assets require source URL, item id, author, license proof reference and explicit project registration confirmation. Certificates are stored locally under project metadata/licenses and are not exposed in public source exports.
- No legal guarantee will be claimed.

## Provider Routing Design

- Add `src/assets/provider_routing.py` as a configurable, non-LLM rule layer.
- Inputs: semantic scene fields, raw scene fields, media type, provider capabilities, enabled state and policy eligibility.
- Output per scene: ordered providers, reasons, skipped providers and fallback order.
- Local Library is checked first only for policy-safe schema v1 assets.
- Pexels/Pixabay handle generic B-roll.
- Wikimedia handles named/specific/historical/maps/diagrams/scientific objects.
- NASA handles space, Earth observation, climate, atmosphere, ocean data, glaciers, storms, aviation/NASA technology.
- Internet Archive handles historical film, archival footage, old educational films and public-domain records.
- Envato is manual fallback only and never an automatic first choice.

## Attribution Export Design

- Add reusable source export helper that creates:
  - `sources.json`
  - `ATTRIBUTION.md`
  - `youtube_sources.txt`
- Save provider, source page, author, license, attribution text, modification notice, selected filename, project id and scene id.
- Include Wikimedia credits when required.
- Include NASA as source with no endorsement wording.
- Build Internet Archive credit from actual license metadata.
- Keep Pexels/Pixabay credits in metadata.
- Do not publish Envato certificate contents or local absolute paths in `youtube_sources.txt`.

## Test Plan

Before production-code changes:

- Run full baseline: `python -B -m unittest discover tests`.
- Write failing mocked tests for providers/routing/export/policy/Envato CLI.

After implementation:

- `python -B -m unittest tests.test_documentary_asset_providers`
- `python -B -m unittest tests.test_provider_routing tests.test_attribution_export`
- `python -B -m unittest tests.test_asset_foundation_models tests.test_asset_foundation_providers tests.test_asset_foundation_http_download tests.test_provider_foundation_hardening`
- `python -B -m unittest tests.test_news_to_short_assets tests.test_news_to_short_pipeline tests.test_news_to_short_quality_check tests.test_news_to_short_renderer tests.test_news_to_short_delivery`
- `python -B -m unittest discover tests`
- Import check for pipeline, news, providers and assets modules.
- JSON validation for policy and snapshots.
- No-network provider diagnostics, including each new `--provider` filter.
- Limited live diagnostics only after mocked tests pass.
- Re-check real media index SHA-256.

## Risks

- Existing `asset_manager` combines provider order and search loops; routing must be added without changing the news stage structure.
- Current semantic analyzer is whale/news-oriented; routing needs robust keyword fallback from raw scene text.
- Strict policy may cause many real provider results to be blocked until metadata is complete.
- NASA and Internet Archive file metadata can return JSON/metadata/service files; selection must avoid downloading non-media files.
- Wikimedia extmetadata can contain HTML snippets; normalization must strip tags for public fields and retain raw snapshot.
- Envato must never download automatically or log credentials.
- Full suite must remain network-blocked even if `.env` has API keys.
- `assets/library/metadata/media_index.json` must remain unchanged.

## Completion Criteria

- Four new provider classes implemented behind existing `StockProvider` foundation.
- Centralized policy covers Pexels/Pixabay contexts, Wikimedia, NASA, Internet Archive and Envato manual.
- Unknown rights block automatic render.
- Provider routing decision is saved in asset manifests.
- Only the selected automatic candidate is downloaded.
- Envato prepares/imports only; no automated Envato download.
- Attribution export files are generated without secrets, certificates or absolute paths in public export.
- Mocked tests and full unittest discovery pass with network guard.
- Limited live diagnostics are recorded separately.
- Real media index SHA-256 is unchanged.
- Paid API calls are not performed.
