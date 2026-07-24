# Visual Preview Foundation Plan

> Created before production-code changes for the visual preview, frame sampling and similarity foundation stage.

## Goal

Add a reversible, provider-neutral preview analysis layer between metadata ranking and selected-only original download:

```text
scene -> semantic queries -> provider routing -> metadata candidates -> metadata shortlist
-> preview resolution -> preview download/cache -> frame sampling
-> technical visual metrics -> perceptual signatures -> duplicate/similarity checks
-> crop suitability -> review bundle -> optional deterministic technical rerank
-> selected candidate -> original download -> license/provenance -> quality check -> renderer
```

This stage intentionally does not implement semantic Vision AI, paid Vision APIs, CLIP, object detection, OCR, face detection, NSFW detection, a full UI, renderer rewrite, audio refactor, Envato automation, scraping or media-library apply migration.

## Baseline

- Working directory: `G:\Projects\AI-YouTube`
- Current branch: `master`
- Commit hash before implementation: `adb40fa944318646aef66102cbb1352e40b7cacc`
- Started at: `2026-07-23T00:00:00+03:00`
- Python: `Python 3.10.11`
- FFmpeg: `ffmpeg version 8.1.1-full_build-www.gyan.dev`
- FFprobe: `ffprobe version 8.1.1-full_build-www.gyan.dev`
- Real media index SHA-256 before implementation: `61B2C5B89F353659ACD48E299DEA3CE6478F28FA968B9149E615DD2051A30385`
- Baseline full suite command before production-code changes: `python -B -m unittest discover -s tests`
- Baseline result: `Ran 134 tests in 27.910s - OK`
- Baseline note: existing non-fatal MoviePy `FFMPEG_AudioReader.__del__` ignored exception was emitted, matching earlier stage notes.
- Ordinary unittest network mode: blocked by `tests.network_guard`.

## Git Status Before Production Code Changes

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
?? src/providers/envato_manual_provider.py
?? src/providers/fake_provider.py
?? src/providers/internet_archive_provider.py
?? src/providers/local_library_provider.py
?? src/providers/nasa_images_provider.py
?? src/providers/wikimedia_commons_provider.py
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
?? tests/test_attribution_export.py
?? tests/test_documentary_asset_providers.py
?? tests/test_news_to_short_assets.py
?? tests/test_news_to_short_delivery.py
?? tests/test_news_to_short_models.py
?? tests/test_news_to_short_pipeline.py
?? tests/test_news_to_short_quality_check.py
?? tests/test_news_to_short_renderer.py
?? tests/test_provider_foundation_hardening.py
?? tests/test_provider_routing.py
?? tests/test_semantic_asset_selection.py
?? tests/test_test_network_guard.py
?? tests/test_voice_workflow.py
?? tests/test_youtube_shorts_production_plan.py
```

## Git Diff Stat Before Production Code Changes

```text
 .gitignore                        |   1 +
 pipeline.py                       | 171 +++++++++++++++++++++++++-
 requirements.txt                  |   1 +
 src/media_library.py              | 251 ++++++++++++++++++++++++++++++++++++-
 src/providers/__init__.py         |  16 +++
 src/providers/pexels_provider.py  | 240 +++++++++++++++++++++++++++++++++++-
 src/providers/pixabay_provider.py | 252 +++++++++++++++++++++++++++++++++++++-
 tests/test_media_library.py       |  47 +++++++
 8 files changed, 968 insertions(+), 11 deletions(-)
```

## Prior Implementation Docs Reviewed

- `IMPLEMENTATION_PROVIDER_FOUNDATION_PLAN.md`
- `IMPLEMENTATION_PROVIDER_FOUNDATION_REPORT.md`
- `IMPLEMENTATION_PROVIDER_FOUNDATION_SNAPSHOT.json`
- `docs/implementation/provider_foundation_hardening/HARDENING_PLAN.md`
- `docs/implementation/provider_foundation_hardening/HARDENING_REPORT.md`
- `docs/implementation/provider_foundation_hardening/HARDENING_SNAPSHOT.json`
- `docs/implementation/provider_foundation_hardening/TEST_RESULTS.txt`
- `docs/implementation/documentary_asset_providers/PROVIDERS_PLAN.md`
- `docs/implementation/documentary_asset_providers/PROVIDERS_REPORT.md`
- `docs/implementation/documentary_asset_providers/PROVIDERS_SNAPSHOT.json`
- `docs/implementation/documentary_asset_providers/TEST_RESULTS.txt`
- `docs/implementation/documentary_asset_providers/LIVE_DIAGNOSTICS.txt`
- `docs/implementation/documentary_asset_providers/LICENSE_POLICY_DECISIONS.md`
- `docs/architecture/TARGET_ARCHITECTURE.md`
- `docs/architecture/CLEANUP_INVENTORY.md`

The reports were used only as orientation. The implementation is based on the actual code in `src/assets`, `src/providers`, `src/news`, `src/media_library.py`, `pipeline.py` and tests.

## Current Candidate Flow In Code

Current `src/news/asset_manager.py::build_assets_manifest()`:

1. Builds a selection config with default `mode=semantic`.
2. Converts user assets through `_inspect_user_asset()`.
3. For each scene, calls `analyze_scene(scene)`.
4. Calls `route_providers()` with available providers.
5. Adds user-ranked candidates and legacy local-library ranked candidates.
6. For each routed provider and semantic query, calls `_search_provider()`.
7. Converts `StockProvider` results through `_candidate_to_rankable()`.
8. Applies `_rank_provider_results()` and centralized policy.
9. Selects by existing semantic metadata rank through `select_best_candidate()`.
10. Calls `_ensure_selected_asset_downloaded()` for selected and fallback ranked candidates.
11. Downloads only the selected eligible candidate through provider `download()`.
12. Writes selected asset, ranked candidates, provider attempts/errors, missing scenes and continuity.

The preview foundation will hook in after step 9 has produced ranked metadata candidates and before step 10 downloads originals. In default `analyse_and_report` mode it must not change the selected candidate. In explicit `technical_rerank` mode it can reorder eligible shortlisted candidates deterministically before selected-only original download.

## Current Provider `get_preview()` Implementations

- `PexelsStockProvider.get_preview()` returns `AssetPreview(candidate_id, url=candidate.preview_url, width, height)`. Video preview is currently the provider image poster. Image preview is `src.medium` or `src.small`.
- `PixabayStockProvider.get_preview()` returns `AssetPreview(candidate_id, url=candidate.preview_url, width, height)`. Video preview is currently a Vimeo poster URL derived from `picture_id`; image preview is `previewURL` or `webformatURL`.
- `WikimediaCommonsStockProvider.get_preview()` returns `AssetPreview(candidate_id, url=candidate.preview_url, width, height)`, where search uses `thumburl`.
- `NasaImageLibraryStockProvider.get_preview()` returns `AssetPreview(candidate_id, url=candidate.preview_url, width, height)`, where search uses item `links.rel=preview`. NASA search currently resolves `download_url` from `/asset/{nasa_id}`, but preview analysis must prefer the search preview and avoid downloading original/high quality renditions.
- `InternetArchiveStockProvider.get_preview()` returns `AssetPreview(candidate_id, url=candidate.preview_url, width, height)`. Current search does not reliably set preview URL, so preview service must synthesize IA thumbnails from identifier before touching metadata/master files.
- `LocalLibraryStockProvider.get_preview()` returns `AssetPreview(local_path=candidate.preview_url or candidate.local_path, width, height)`. Preview service should generate a smaller local preview/cache from the existing local file, not copy the original unnecessarily.
- `FakeStockProvider.get_preview()` returns URL `https://fake.local/previews/...jpg`; tests need deterministic local fixture handling because ordinary tests must not use network.
- `EnvatoManualProvider.get_preview()` returns empty `AssetPreview` and `supports_preview=False`. Remote Envato preview must not be automated. Imported local Envato files can later be analyzed as local files.

## Current `AssetCandidate` Schema

`src/assets/models.py::AssetCandidate` fields currently include:

- identity: `asset_id`, `provider`, `provider_asset_id`, `schema_version`
- media metadata: `media_type`, `title`, `description`, `tags`, `width`, `height`, `duration_sec`, `orientation`
- source: `source_page_url`, `preview_url`, `download_url`, `author_name`, `author_url`
- local state: `local_path`, `original_filename`, `downloaded_at`, `checksum_sha256`
- context: `project_id`, `scene_id`, `search_query`
- policy: `license`, `provenance`, `policy_decision`, `rights_declaration`
- analysis-ish existing fields: `raw_metadata`, `technical_validation`, `crop_suitability_score`

Preview analysis should not bloat `AssetCandidate` with every sampled-frame field. Store rich preview results in a scene review manifest and add only a compact reference from `assets_manifest.json`.

## New Modules Planned

- `src/assets/visual_preview.py`
  - config loading, `VisualPreviewRequest`, `CandidatePreview`, `PreviewCacheRecord`, preview resolution, preview cache, safe download/generation, scene analysis orchestration, manifest inspection helpers.
- `src/assets/frame_sampling.py`
  - FFprobe metadata, timestamp planning, FFmpeg extraction, image-as-one-frame handling and `SampledFrame`.
- `src/assets/visual_metrics.py`
  - `TechnicalVisualMetrics`, brightness/contrast/sharpness/detail/activity/frozen/repeated/crop heuristics and quality scoring.
- `src/assets/perceptual_similarity.py`
  - `PerceptualSignature`, dHash/average hash helpers, exact duplicate, near duplicate, video multi-frame signatures and `SimilarityResult`.
- `src/assets/review_bundle.py`
  - `SceneReviewBundle`, shortlist/ranking records, deterministic technical rerank, neighbor/project repetition penalties, JSON manifest and static HTML board generation.

## Files Planned To Modify

- `config/visual_preview.json` will be created.
- `src/assets/__init__.py` will export preview foundation APIs.
- `src/assets/provider_contract.py` may extend `AssetPreview` without breaking existing providers.
- `src/providers/pexels_provider.py` and `src/providers/pixabay_provider.py` will expose safer preview rendition metadata while keeping original download URLs for selected-only download.
- `src/providers/wikimedia_commons_provider.py`, `src/providers/nasa_images_provider.py`, `src/providers/internet_archive_provider.py`, `src/providers/local_library_provider.py`, `src/providers/fake_provider.py`, `src/providers/envato_manual_provider.py` will keep `get_preview()` unified and provider-specific rules conservative.
- `src/news/asset_manager.py` will call preview analysis after metadata ranking and before original download, guarded by config/explicit flags.
- `src/news/pipeline.py` may pass asset selection/preview config through existing stage structure if needed.
- `pipeline.py` will add `visual-preview prepare` and `visual-preview inspect`.
- New tests will be added under `tests/`.

## Preview Cache Location Decision

Use project-local preview cache for pipeline/CLI runs:

```text
projects/<project_id>/assets/previews/
projects/<project_id>/assets/review/
```

Reason: `NewsProjectStore` already owns `projects/<project_id>/assets`, review artifacts are project-specific, and this avoids moving global project structure before the target `workspace/cache/` migration. For standalone service tests or callers without `project_root`, use fallback:

```text
assets/cache/previews/
```

No existing media-library files are moved. Real `assets/library/metadata/media_index.json` is not modified.

## Preview Resolution Design

Resolution order per candidate:

1. Provider `get_preview(candidate)` URL/local path.
2. Candidate `preview_url` or thumbnail-like metadata.
3. Provider-specific small derivative:
   - Pexels: image `small/medium`, video poster or smaller video file when metadata exposes one.
   - Pixabay: image `previewURL/webformatURL`, video poster or smallest usable preview variant.
   - Wikimedia: `thumburl` for images; small derivative/thumbnail for videos when available.
   - NASA: `links.rel=preview`; exclude captions/JSON/metadata.
   - Internet Archive: thumbnail URL from `https://archive.org/services/img/<identifier>` or small derivative if already known.
   - Local Library/user/imported Envato: existing local file, then generated reduced local preview.
   - Fake: local fixture first when available, deterministic fake URL otherwise only in live-disabled diagnostics.
4. Existing local file if present.
5. Original/download URL only when no other preview exists, `allow_original_fallback` is true, media is safely bounded by config and offline mode is false.

Resolution record must include provider, provider asset id, preview source URL/local source, media type, expected content type, expected size if known, resolution/duration if known, fallback reason, original-used flag, timestamp and cache key.

## Preview Cache Design

Cache key will be SHA-256 over a stable JSON payload containing provider, provider asset id, asset id, preview URL/local source, media type, rendition name, target aspect ratio, sample count and version.

Requirements:

- Windows-safe filenames with extension from content/source.
- Unicode-safe paths through `pathlib`.
- `.part` writes and atomic replace.
- max preview size from config, default 5 MB.
- timeout from config/request.
- Content-Type and Content-Length validation for remote previews.
- SHA-256 stored in `PreviewCacheRecord`.
- cache hit reuse.
- refresh option.
- corrupted-cache invalidation by missing file, empty file, checksum mismatch or failed Pillow/FFprobe validation.
- no duplicate download inside one run by sharing cache key records.
- offline mode uses cached/local previews only and records `offline_no_cache` when missing.

## Frame Sampling Design

- Images are one sampled frame using the local preview/image path.
- Videos use FFprobe duration when possible.
- Default positions: `[0.10, 0.30, 0.50, 0.70, 0.90]`.
- For unknown duration, use bounded fallback timestamps starting at 0.
- For very short videos, clamp positions and de-duplicate rounded timestamps.
- Avoid exact 0 when possible to skip black first frames.
- Save frames under the preview cache record folder or `assets/review/frames`.
- Each `SampledFrame` stores index, requested timestamp, actual timestamp when known, path, width, height, SHA-256, extraction status/error, perceptual hash and technical metrics.
- Failed extraction records an error and does not fail the whole pipeline.

## Technical Metrics Design

Local only, no external Vision API:

- width, height, aspect ratio, orientation, duration, file size
- brightness mean and distribution
- contrast
- dark-frame score
- near-white-frame score
- simple sharpness/blur heuristic using grayscale local differences
- edge/detail density heuristic
- dominant visual activity across frames
- frozen-frame ratio
- repeated-frame ratio
- unique-frame ratio
- portrait, landscape and square heuristic crop suitability
- technical quality score with documented weights

Metrics are heuristic and will be stored as such. They do not claim object, face, subject or artistic quality detection.

## Similarity Design

- Exact duplicate: SHA-256 match.
- Perceptual image hash: local dHash implemented with Pillow, optionally NumPy if available.
- Video signature: list of sampled frame perceptual hashes; compare aggregate/frame distances across multiple frames.
- Classifications: `exact_duplicate`, `near_duplicate`, `likely_same_source_different_rendition`, `visually_similar`, `not_similar`, `insufficient_data`.
- Store compared asset ids, hash distance, frame-level distances, aggregate similarity, threshold, classification and reason.

## Neighbor And Project Repetition Design

The review layer will compare the current scene shortlist against:

- previous selected/prepared scenes in the current run
- next known scene when already prepared in an existing manifest
- last 3-5 scenes
- all current project selected assets found in existing review/asset manifests

Penalties are configurable and non-blocking by default:

- same asset id
- same source URL
- same checksum
- near perceptual signature
- repeated preview cache key
- repeated technical composition proxy such as very similar aspect/detail/activity profiles

The manifest records `duplicate_penalty`, `neighbor_similarity_penalty`, `project_repetition_count`, reasons and future `overridden_by_user=false`.

## Crop Suitability Design

Targets: `9:16`, `16:9`, `1:1`.

For each target:

- aspect mismatch
- estimated crop retention
- central detail density
- estimated detail loss
- empty-area heuristic
- stability across sampled frames
- estimated post-crop resolution
- score and explanation

Use names such as `heuristic_crop_suitability`, `estimated_detail_retention` and `center_information_density`. Do not use `subject-safe crop`.

## Review Bundle And HTML Design

For each scene:

- JSON manifest under `projects/<project_id>/assets/review/visual_review_manifest.json`.
- Static HTML board under `projects/<project_id>/assets/review/visual_review_board.html`.
- The project `assets_manifest.json` may include a compact pointer to the review bundle but the existing schema is not broken.
- HTML uses relative local paths for previews/frames.
- HTML includes no secrets, no absolute paths in displayed text, no Envato proof/certificate content, no external JS requests and no project-mutating buttons.
- Envato manual fallback is displayed as manual action only before import.

## CLI Design

Add dispatcher command:

```powershell
python -B pipeline.py visual-preview prepare --project-id <project-id> --scene-id <scene-id> --top-k 5
python -B pipeline.py visual-preview prepare --project-id <project-id> --all-scenes --offline --no-html
python -B pipeline.py visual-preview inspect --project-id <project-id>
```

Options:

- `--all-scenes`
- `--refresh`
- `--technical-rerank`
- `--target-aspect 9:16`
- `--no-html`
- `--offline`
- `--top-k`

`prepare` reads existing project visual/assets manifests when present and can produce review artifacts for one scene or all scenes. It must not call paid/Vision APIs. Offline mode must rely on cached/local/fake inputs.

`inspect` reports scene count, analyzed candidates, preview cache hits/misses, failed previews, exact/near duplicates, review-required candidates, selected candidates, missing scenes and HTML board path.

## Test Plan

Red tests before production implementation:

- `python -B -m unittest tests.test_visual_preview_foundation`
- `python -B -m unittest tests.test_visual_preview_integration`

Targeted tests after implementation:

- `python -B -m unittest tests.test_visual_preview_foundation tests.test_visual_preview_integration`
- `python -B -m unittest tests.test_asset_foundation_models tests.test_asset_foundation_providers tests.test_asset_foundation_http_download tests.test_provider_foundation_hardening tests.test_test_network_guard`
- `python -B -m unittest tests.test_documentary_asset_providers tests.test_provider_routing tests.test_attribution_export`
- `python -B -m unittest tests.test_news_to_short_assets tests.test_news_to_short_pipeline tests.test_news_to_short_quality_check tests.test_news_to_short_renderer tests.test_news_to_short_delivery`
- `python -B -m unittest tests.test_documentary_visual_engine tests.test_youtube_shorts_production_plan`
- `python -B -m unittest discover -s tests`

Smoke checks:

- import check for new modules and touched modules
- JSON validation for `config/visual_preview.json` and `PREVIEW_SNAPSHOT.json`
- config validation via loader
- CLI prepare/inspect on a disposable Fake Provider project
- generated HTML secret/path scan
- limited live preview diagnostics after mocked tests
- final `media_index.json` SHA-256 check

New mocked tests should cover the 45 requested behaviors: serialization, cache key stability/hit/corruption, image/video preview generation, frame timestamp edge cases, FFmpeg extraction, image-as-frame, dark/white/contrast/sharpness/activity/frozen/repeated metrics, perceptual hash stability, exact/near duplicate detection, multi-frame video signatures, crop suitability, neighbor/project repetition, review bundle, HTML relative/no-secret/no-Envato-proof, score breakdown, rerank default/off/on, fallback on failed preview, shortlist-only preview fetch, selected-only original download, Envato remote no-fetch, imported Envato local analysis, provider-specific preview selection, Windows/Unicode paths, offline mode, network guard and existing suite compatibility.

## Risks

- The current asset manager downloads selected candidates immediately after metadata selection. Integration must insert preview analysis before that call without accidentally downloading originals for the whole shortlist.
- Current provider `get_preview()` is minimal. The preview service must enrich missing fields without forcing all providers to change at once.
- Pexels/Pixabay video APIs may expose posters rather than playable preview video. The foundation should analyze poster frames when only poster previews exist and record that limitation.
- NASA search currently fetches asset renditions during search. This is metadata/API work, not media download, but preview analysis must still prefer `links.rel=preview` and avoid original media downloads.
- Internet Archive thumbnail may be an image even for video candidates. That is acceptable as a preview fallback, but it must be recorded as poster/image analysis.
- FFmpeg may fail on tiny/corrupt fixtures. Failures must be recorded as analysis errors with low scores, not crash the whole pipeline.
- Strict license policy may block candidates even if technical scores are high.
- Full suite must remain network-blocked. Live diagnostics must set live flags explicitly and stay within size/time/provider limits.
- `.env` must not be read into reports and secrets must not appear in HTML/logs.
- The dirty worktree contains prior-stage untracked files. This stage must not revert or clean them.

## Completion Criteria

- Shared preview service and cache are implemented.
- Automatic providers support safe preview resolution.
- Envato remote preview remains non-automated.
- Frame sampling supports image and video.
- Technical visual metrics and heuristic crop suitability are implemented.
- Perceptual signatures, exact duplicate and near duplicate analysis work.
- Neighbor/project repetition penalties work.
- Review bundle JSON and static HTML board are generated.
- Technical rerank is off by default and works only when explicitly enabled.
- Original download is selected-only after preview analysis.
- Failed preview falls back to metadata ranking.
- Mocked tests and full discovery pass with network guard.
- Limited live preview diagnostics are recorded.
- Real media index SHA-256 is unchanged.
- No paid API calls, Vision API calls or automated Envato downloads occur.
- Snapshot marks readiness for a future semantic visual reranker.
