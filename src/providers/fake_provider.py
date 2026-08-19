from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from src.assets.download import copy_candidate_fixture
from src.assets.models import (
    AssetCandidate,
    AssetLicense,
    AssetProvenance,
    DownloadedAsset,
    ProviderCapabilities,
    orientation_from_dimensions,
)
from src.assets.license_policy import apply_policy_to_candidate
from src.assets.provider_contract import (
    AssetPreview,
    AssetSearchRequest,
    DownloadContext,
    LicenseReviewRequired,
    ProviderHealth,
    ProviderRateLimitError,
    ProviderValidationError,
)


class FakeStockProvider:
    name = "fake"

    def __init__(
        self,
        *,
        image_fixture: str | Path | None = None,
        video_fixture: str | Path | None = None,
        mode: str = "success",
    ) -> None:
        self.image_fixture = Path(image_fixture) if image_fixture else None
        self.video_fixture = Path(video_fixture) if video_fixture else None
        self.mode = mode

    def capabilities(self) -> ProviderCapabilities:
        # Matches on nothing, so the query language is irrelevant to it.
        return ProviderCapabilities(
            provider=self.name,
            media_types=["video", "image"],
            supports_orientation_filter=True,
            query_languages=["en", "ru"],
        )

    def search(self, request: AssetSearchRequest) -> list[AssetCandidate]:
        if self.mode == "rate_limit":
            raise ProviderRateLimitError("Fake provider rate limit.", provider=self.name, query=request.query, retryable=True)
        media_type = request.media_type if request.media_type in {"image", "video"} else "video"
        fixture = self._fixture_for(media_type)
        width, height = (1080, 1920) if request.orientation_preference == "vertical" else (1920, 1080)
        # Identity follows content. The title and description below are written from
        # the query, so two queries of one scene's ladder are two different records,
        # and filing them under a single id would state that they are one asset. The
        # pool keeps one entry per ``asset_id``, so that statement is acted on: every
        # wording but one is dropped before ranking sees it, and which one survives is
        # decided by the ladder rather than by the scene. A real provider never poses
        # this question - its metadata describes the asset, not the question that found
        # it - and this fixture stands in for a real one.
        query_digest = hashlib.sha1(request.query.strip().casefold().encode("utf-8")).hexdigest()[:8]
        provider_asset_id = f"{request.scene_id or 'scene'}_{media_type}_{query_digest}"
        license_data = self._license()
        candidate = AssetCandidate(
            asset_id=f"fake_{provider_asset_id}",
            provider=self.name,
            provider_asset_id=provider_asset_id,
            media_type=media_type,
            title=f"{request.query} fake {media_type} ocean whale nature science",
            description=f"Deterministic fake {media_type} for {request.query}",
            # The query is deliberately *not* echoed into the tags: this fixture stands
            # in for a real provider, and a real provider's tags describe the asset.
            tags=["fake", "ocean", "whale", "nature", "science"],
            source_page_url=f"https://fake.local/assets/{provider_asset_id}",
            preview_url=f"https://fake.local/previews/{provider_asset_id}.jpg",
            download_url=f"file:///{fixture.as_posix()}" if fixture else f"fake://{provider_asset_id}",
            author_name="Fake Provider",
            author_url="https://fake.local/author",
            width=width,
            height=height,
            # Long enough to cover any scene this fixture is asked to fill. It used to
            # be 5s, which was shorter than most scenes - fine while nothing checked,
            # but the duration gate now (correctly) refuses a clip that cannot cover
            # its scene, and this fixture exists to stand in for one that can.
            duration_sec=30.0 if media_type == "video" else 0.0,
            orientation=orientation_from_dimensions(width, height),
            search_query=request.query,
            project_id=request.project_id,
            scene_id=request.scene_id,
            license=license_data,
            raw_metadata={"fixture_path": str(fixture or ""), "mode": self.mode},
            crop_suitability_score=100.0 if request.orientation_preference == "vertical" else 60.0,
        )
        candidate.provenance = AssetProvenance(
            provider=self.name,
            provider_asset_id=candidate.provider_asset_id,
            source_page_url=candidate.source_page_url,
            download_url=candidate.download_url,
            project_id=request.project_id,
            scene_id=request.scene_id,
            search_query=request.query,
            metadata_snapshot=candidate.raw_metadata,
        )
        apply_policy_to_candidate(candidate)
        return [candidate]

    def get_preview(self, candidate: AssetCandidate) -> AssetPreview:
        fixture = self._fixture_for(candidate.media_type)
        if fixture and fixture.exists():
            return AssetPreview(
                candidate_id=candidate.asset_id,
                local_path=str(fixture),
                width=candidate.width,
                height=candidate.height,
                media_type=candidate.media_type,
                duration_sec=candidate.duration_sec,
                rendition="fake_fixture",
                fallback_reason="fake_fixture_preview",
            )
        return AssetPreview(
            candidate_id=candidate.asset_id,
            url=candidate.preview_url,
            width=candidate.width,
            height=candidate.height,
            media_type="image",
            rendition="fake_url",
        )

    def resolve_license(self, candidate: AssetCandidate) -> AssetLicense:
        candidate.license = self._license()
        apply_policy_to_candidate(candidate)
        return candidate.license

    def download(self, candidate: AssetCandidate, destination: Path, context: DownloadContext) -> DownloadedAsset:
        self.resolve_license(candidate)
        if candidate.license.review_required or not candidate.license.allowed_for_render:
            raise LicenseReviewRequired("Fake asset requires license review.", provider=self.name, query=candidate.search_query)
        if self.mode == "invalid_file":
            destination.mkdir(parents=True, exist_ok=True)
            invalid = destination / f"{candidate.asset_id}.mp4"
            invalid.write_bytes(b"not a valid media file")
            invalid.unlink(missing_ok=True)
            raise ProviderValidationError(f"Fake invalid file was rejected: {invalid}", provider=self.name, query=candidate.search_query)
        fixture = self._fixture_for(candidate.media_type)
        if not fixture:
            raise ProviderValidationError(f"Fake provider has no {candidate.media_type} fixture.", provider=self.name, query=candidate.search_query)
        return copy_candidate_fixture(candidate, fixture, destination, context)

    def health_check(self) -> ProviderHealth:
        return ProviderHealth(provider=self.name, configured=True, status=self.mode)

    def _fixture_for(self, media_type: str) -> Path | None:
        if media_type == "image":
            return self.image_fixture
        return self.video_fixture or self.image_fixture

    def _license(self) -> AssetLicense:
        if self.mode == "unknown_license":
            return AssetLicense(
                license_name="unknown",
                rights_status="legacy_unknown",
                commercial_use_allowed=False,
                modification_allowed=False,
                attribution_required=True,
                allowed_for_render=False,
                review_required=True,
                notes="Fake provider unknown-license mode.",
            )
        return AssetLicense(
            license_name="fake_test_license",
            license_url="https://fake.local/license",
            provider_terms_url="https://fake.local/terms",
            rights_status="licensed",
            commercial_use_allowed=True,
            modification_allowed=True,
            attribution_required=False,
            attribution_text="Fake Provider test fixture",
            allowed_for_render=True,
            review_required=False,
            notes="Deterministic no-network test license.",
        )
