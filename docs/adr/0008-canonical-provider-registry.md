# ADR 0008: Canonical provider registry boundary

## Status

Accepted and implemented on 2026-07-29.

## Context

`src.assets.provider_contract.StockProvider` and the implementations under
`src/providers/` already formed the shared provider foundation, including the
common HTTP client, download validation, diagnostics and license policy.
However, the active Fullscreen Voiceover workflow still assembled its default
provider set inside `src/news/asset_provider_adapters.py`. That module also
retained the older news-only `AssetProvider` protocol and compatibility
Pexels/Pixabay/Unsplash classes.

`src/news/stock_video_downloader.py` exposed a delegating compatibility
entrypoint, but also retained a private unreachable implementation that knew raw
Pexels/Pixabay response shapes and downloaded with `requests` directly.

## Decision

- `src.assets.provider_contract.StockProvider` remains the single canonical
  provider contract.
- `src.providers.registry.create_default_stock_providers` owns construction and
  environment enablement of the automatic provider set used by active
  workflows.
- `src.news.asset_provider_adapters.create_default_asset_providers` remains a
  compatibility wrapper and delegates to the shared registry.
- The old news-only `AssetProvider` protocol and
  `PexelsAssetProvider`/`PixabayAssetProvider`/`UnsplashAssetProvider` names are
  compatibility-only. They are not part of the default path and remain until
  the D01 compatibility-retirement checkpoint in stage 9.
- `src.news.stock_video_downloader.download_stock_videos_for_project` remains a
  compatibility wrapper over the canonical asset stage. Its unreachable
  private raw-HTTP implementation is removed; retirement of the public D02
  module remains a separate stage 9 decision.
- Timeout, retry and rate-limit translation remain owned by
  `src.assets.http_client.ProviderHttpClient`; diagnostics by
  `src.assets.provider_diagnostics`; download validation by
  `src.assets.download`; and license normalization/gating by
  `src.assets.license_policy`.
- Legacy documentary and fixed-production-plan HTTP paths are not moved in this
  decision. They remain inside the stage 8 vertical-slice boundary.

## Consequences

1. The active content-creator workflow obtains all automatic providers from
   `src.providers` and does not know provider HTTP API details.
2. Adding or changing an active provider implementation no longer requires a
   news-owned factory implementation.
3. Existing news imports, factory patch-points and the standalone downloader
   entrypoint remain compatible.
4. No provider was added, no manifest schema changed, and no runtime project or
   media file was migrated.

## Verification

Run the provider contract, HTTP/download, diagnostics, routing, news integration
and news asset tests, followed by news pipeline/CLI compatibility tests and an
import smoke for:

```text
src.assets.provider_contract
src.providers
src.providers.registry
src.news.asset_provider_adapters
src.news.asset_manager
src.news.stock_video_downloader
```
