# ADR 0015: Retire the standalone news stock downloader

## Status

Accepted and implemented on 2026-07-29 as stage 9 bounded slice D02.

## Context

Stage 7 removed the unreachable raw-HTTP implementation from
`src.news.stock_video_downloader` and left one delegating compatibility
function, `download_stock_videos_for_project`. It read a persisted visual plan,
called `src.news.asset_manager.build_news_asset_manifest` and wrote the same
asset manifest plus a missing-assets summary.

The stage 9 D02 audit found no imports or calls from production code, no
`src.news` package export, no CLI/console-script registration and no documented
current command. The only executable caller was the characterization that kept
the temporary wrapper alive. Historical docstrings named the module as a
consumer of the visual-plan format but did not import or execute it.

## Decision

- Delete `src/news/stock_video_downloader.py` and retire
  `download_stock_videos_for_project`.
- Keep `src.news.asset_manager.build_news_asset_manifest` as the existing
  canonical asset-stage entrypoint used by the active news workflow.
- Update the two historical production docstrings so they no longer claim the
  retired module remains a visual-plan consumer.
- Do not add a replacement CLI, wrapper or downloader.
- Do not read, rewrite or migrate persisted asset manifests or downloaded
  media.
- Keep the unrelated D03 planning directory as a separate deletion checkpoint.

## Consequences

1. Importing `src.news.stock_video_downloader` now fails.
2. The active `asset_search` stage and its provider/download contracts are
   unchanged.
3. Existing `assets_manifest.json`, `missing_assets.json` and downloaded media
   remain readable and untouched.
4. The repository has no standalone news path that can bypass normal workflow
   orchestration to start provider download.

## Verification

Pre-change AST characterization confirmed zero production imports or calls.
Targeted verification covers the news asset-manager contract, asset behavior,
news pipeline and stage-1 compatibility. Network/provider search, download,
TTS, Vision and render are not required.
