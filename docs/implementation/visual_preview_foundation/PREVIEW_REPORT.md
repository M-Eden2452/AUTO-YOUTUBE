# Visual Preview Foundation Report

## Baseline

- Branch: `master`
- Commit before implementation: `adb40fa944318646aef66102cbb1352e40b7cacc`
- Python: `Python 3.10.11`
- FFmpeg/FFprobe: `8.1.1-full_build-www.gyan.dev`
- Baseline full suite before production changes: `python -B -m unittest discover -s tests`
- Baseline result: `Ran 134 tests in 27.910s - OK`
- Real media index SHA-256 before implementation: `61B2C5B89F353659ACD48E299DEA3CE6478F28FA968B9149E615DD2051A30385`

## Confirmed Architecture

The implemented flow is additive and reuses the existing provider foundation:

```text
metadata candidates -> metadata shortlist -> preview resolution/cache
-> frame sampling -> technical metrics -> perceptual signatures
-> duplicate/repetition/crop heuristics -> review bundle
-> optional deterministic technical rerank -> selected-only original download
```

No parallel asset architecture was added. The implementation uses `AssetCandidate`, `AssetSearchRequest`, `StockProvider.get_preview`, provider routing output, license/provenance records and the existing news asset manifest.

## Created Modules

- `src/assets/visual_preview.py`: preview request/config/cache/service, CLI project prepare/inspect helpers.
- `src/assets/frame_sampling.py`: FFprobe media info, timestamp planning, FFmpeg frame extraction, image-as-frame support.
- `src/assets/visual_metrics.py`: brightness, contrast, blur/detail/activity/frozen/repeated-frame and crop heuristics.
- `src/assets/perceptual_similarity.py`: SHA-256 aware perceptual signatures, dHash and similarity classification.
- `src/assets/review_bundle.py`: review bundle manifest, deterministic rerank, repetition penalties and static HTML board.
- `config/visual_preview.json`: non-secret preview foundation configuration.

## Changed Files

- `pipeline.py`: added `visual-preview prepare` and `visual-preview inspect`.
- `src/assets/provider_contract.py`: extended `AssetPreview` metadata.
- `src/assets/__init__.py`: exports preview foundation APIs.
- `src/news/asset_manager.py`: integrates analyse-and-report mode before selected-only original download, with opt-in technical rerank.
- Provider `get_preview()` implementations updated for Pexels, Pixabay, Wikimedia Commons, NASA Images, Internet Archive, Local Library, Fake Provider and Envato Manual.
- Added tests: `tests/test_visual_preview_foundation.py`, `tests/test_visual_preview_integration.py`.

## Preview Resolution Flow

For each top-K metadata candidate, preview resolution tries, in order:

1. Provider preview or derivative URL.
2. Thumbnail URL.
3. Small rendition from provider raw metadata.
4. Existing local file.
5. Original fallback only when explicitly allowed and safe.

The record stores provider, provider asset id, preview URL/path, media type, expected size/type, duration when known, fallback reason, original-used flag, timestamp, SHA-256 and cache key.

## Provider-Specific Preview Rules

- Pexels: uses image thumbnails or medium/small video files from raw metadata.
- Pixabay: uses preview/webformat image URLs or safe video variants.
- Wikimedia Commons: uses thumb/preview URL and avoids large originals for shortlist analysis.
- NASA Images: uses search-result preview links, excluding metadata/captions as visual previews.
- Internet Archive: uses thumbnail/service image or small derivative, not master files.
- Local Library: analyses existing local files and creates local lightweight previews.
- Fake Provider: deterministic local/fixture previews.
- Envato Manual: remote preview automation remains disabled; imported local files can be analysed.

## Cache Design

Preview cache is project-local when a project root is available: `projects/<project_id>/assets/previews`. The reusable fallback is `assets/cache/previews`.

The cache key includes provider, provider asset id, preview URL, media type, rendition and request parameters. Downloads use `.part` files and atomic replace, validate content type and content length, enforce timeout/maximum size, calculate SHA-256, reuse valid cache entries, support refresh, and invalidate corrupted cache records.

## Frame Sampling

Video sampling uses FFprobe/FFmpeg and default positions `10%, 30%, 50%, 70%, 90%`. Timestamp planning deduplicates rounded positions and handles very short or unknown-duration previews. Images are treated as a single sampled frame. Each sampled frame records index, requested timestamp, path, dimensions, SHA-256, extraction status/error, perceptual hash and technical metrics.

## Technical Metrics

Implemented local heuristic metrics:

- Width, height, aspect ratio, orientation, duration and file size.
- Brightness mean and distribution.
- Contrast.
- Dark-frame and near-white-frame scores.
- Sharpness/blur heuristic.
- Edge/detail density.
- Dominant visual activity across sampled frames.
- Frozen, repeated and unique-frame ratios.
- Portrait, landscape and square crop heuristics.
- Technical quality score with documented/configurable weights.

Failed preview analysis is contained in candidate status/error fields and falls back to metadata ranking without assigning a false high score.

## Perceptual Signatures

Image signatures combine file SHA-256 and dHash. Video signatures aggregate hashes from multiple sampled frames, not only the first frame. Similarity compares exact checksums and frame/image hash distances, producing one of:

- `exact_duplicate`
- `near_duplicate`
- `likely_same_source_different_rendition`
- `visually_similar`
- `not_similar`
- `insufficient_data`

Thresholds are configurable in `config/visual_preview.json`.

## Duplicate And Neighbor Analysis

The review bundle computes duplicate and repetition penalties for exact asset id/source/checksum matches and near perceptual matches. Neighbor/project repetition fields include duplicate penalty, neighbor similarity penalty, project repetition count and reason. These penalties are recorded and are not hard blockers unless policy/configuration later chooses to enforce them.

## Crop Suitability

Crop suitability is estimated separately for `9:16`, `16:9` and `1:1`. The heuristic uses aspect-ratio crop loss, center information density, estimated detail retention, empty-area score and resulting crop resolution. It does not claim subject, face or object safety.

## Deterministic Reranking

Technical rerank is disabled by default. In default `analyse_and_report` mode, production selection remains metadata-driven and originals are downloaded only for the selected candidate.

When explicitly enabled via config or CLI flag, deterministic rerank combines metadata score, technical quality, crop suitability, duplicate penalty and neighbor penalty. The score breakdown and weights are written to the manifest, and candidates with blocked policy, review-required status, invalid preview/original or missing provenance cannot win automatically.

## Review Bundle And HTML Board

`visual_review_manifest.json` stores scene-level review data, candidate analyses, preview status, sampled frames, technical/similarity/crop scores, selected candidate and alternatives.

`visual_review_board.html` is a static local board with relative media paths, sampled frames, provider/source/license details, metadata/technical/duplicate/crop/combined scores and manual Envato fallback status. It does not include secrets, absolute local paths in displayed text or Envato certificate content.

Schema details are documented in `REVIEW_BUNDLE_SCHEMA.md`.

A persistent CLI smoke board was generated at `docs/implementation/visual_preview_foundation/cli_smoke_projects/preview_smoke_project/assets/review/visual_review_board.html`.

## CLI Commands

```powershell
python -B pipeline.py visual-preview prepare --project-id <project-id> --scene-id <scene-id> --top-k 5
python -B pipeline.py visual-preview prepare --project-id <project-id> --all-scenes --offline
python -B pipeline.py visual-preview inspect --project-id <project-id>
```

Options include `--refresh`, `--technical-rerank`, `--target-aspect`, `--no-html` and `--offline`.

## Mocked Test Results

- New preview/foundation tests: `Ran 26 tests in 2.474s - OK`
- New integration tests: `Ran 19 tests in 3.038s - OK`
- Combined preview tests: `Ran 45 tests in 4.892s - OK`
- Provider foundation/hardening tests: `Ran 21 tests in 0.805s - OK`
- Documentary provider tests: `Ran 16 tests in 0.493s - OK`
- News/pipeline/quality/renderer tests: `Ran 28 tests in 70.055s - OK`
- Full unittest discovery: `Ran 179 tests in 76.410s - OK`

Ordinary tests remained network-guarded.

## Live Preview Diagnostics

Limited live checks downloaded one preview/thumbnail each from Wikimedia Commons, NASA Images and Internet Archive. Pexels and Pixabay were skipped because no keys were present in the process environment. Envato automated remote preview was skipped as forbidden.

Total downloaded preview bytes: `92891`, under the `20 MB` total limit. Details are in `LIVE_PREVIEW_DIAGNOSTICS.txt`.

## Compatibility

- Existing provider contracts remain backward compatible because added preview fields are optional.
- Existing news pipeline stage structure is preserved.
- `assets_manifest.json` is not replaced; only review links are added when preview analysis runs.
- Default selection behavior remains metadata-driven until technical rerank is explicitly enabled.
- Original assets are still downloaded only after final selection.

## Safety Confirmations

- Paid API calls performed: no.
- Vision API calls performed: no.
- Automated Envato download performed: no.
- Originals for all shortlist candidates downloaded: no.
- Real `assets/library/metadata/media_index.json` SHA-256 after implementation: `61B2C5B89F353659ACD48E299DEA3CE6478F28FA968B9149E615DD2051A30385`.
- User projects and outputs were not deleted.

## Remaining Issues

- Technical heuristics are intentionally non-semantic and cannot detect objects, faces, logos, OCR text or subject-safe crops.
- Live Pexels/Pixabay preview smoke checks require keys already configured in the process environment.
- Existing full-suite MoviePy cleanup warning remains non-fatal and unchanged from baseline.

## Readiness

The stage is ready for a future semantic visual reranker: candidates now have preview manifests, sampled frames, technical metrics, perceptual signatures, duplicate analysis and deterministic score breakdowns without using paid or external Vision APIs.

Recommended next stage: add an optional semantic visual reranker interface that consumes `visual_review_manifest.json` and sampled frames, gated behind explicit configuration and policy controls.
