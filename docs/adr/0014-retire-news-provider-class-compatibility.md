# ADR 0014: Retire news-only provider class compatibility

## Status

Accepted and implemented on 2026-07-29 as stage 9 bounded slice D01.

## Context

Stage 7 established `src.assets.provider_contract.StockProvider` as the single
provider contract and moved the active automatic provider factory to
`src.providers.registry`. It intentionally retained the older
`PexelsAssetProvider`, `PixabayAssetProvider` and `UnsplashAssetProvider`
classes in `src.news.asset_provider_adapters`, with re-exports from
`src.news.asset_manager`, until the stage 9 compatibility-retirement
checkpoint.

The stage 9 audit found no production imports, callers or package exports for
those three names. The only remaining references were their definitions, the
compatibility re-export and the characterization that recorded that temporary
surface. The repository publishes only the canonical `ai-youtube` command, and
stages 7 and 8 completed without a caller appearing.

## Decision

- Remove the three news-only provider classes and their `asset_manager`
  re-exports.
- Keep the news `AssetProvider` protocol because injected offline/test
  providers still use its legacy `search(query, scene, limit)` shape.
- Keep `create_default_asset_providers` as the news factory patch-point; it
  continues to delegate to `src.providers.registry`.
- Keep `PexelsStockProvider` and `PixabayStockProvider` as the canonical active
  implementations. Unsplash remains outside the automatic provider set.
- Do not change manifest schemas, provider identifiers, provenance, license
  policy or downloaded media.
- Keep retirement of `src.news.stock_video_downloader` as the separate D02
  checkpoint, subsequently completed by ADR 0015.

## Consequences

1. Importing the three retired names from either news module now fails instead
   of exposing duplicate search-only provider implementations.
2. Active provider construction and workflow behavior are unchanged.
3. The news adapter no longer imports raw provider API modules solely for the
   retired classes.
4. Runtime projects, manifests and user media require no migration.

## Verification

The D01 characterization first confirmed zero internal callers. Targeted
verification covers the news asset-manager contract, provider foundation,
provider integration and news asset behavior. Network/provider search,
download, TTS, Vision and render are not required.
