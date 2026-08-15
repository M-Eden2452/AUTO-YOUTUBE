from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Callable, Protocol

from src.assets.license_policy import apply_policy_to_candidate
from src.assets.models import (
    ASSET_SCHEMA_VERSION,
    RIGHTS_ALLOWED_STATUSES,
    RIGHTS_REFERENCE_ONLY,
    AssetCandidate,
)
from src.assets.provider_contract import (
    AssetSearchRequest,
    DownloadContext,
    LicenseReviewRequired,
    ProviderError,
    StockProvider,
)
from src.assets.semantic_selection.decision import carry_decision
from src.assets.semantic_selection.evidence import carry_vision_evidence
from src.media_library import register_asset
from src.providers import (
    create_default_stock_providers,
    environment_enabled as provider_environment_enabled,
)


class AssetProvider(Protocol):
    """Deprecated news-only compatibility surface.

    Active provider creation returns the canonical ``StockProvider`` contract.
    This protocol remains only until D01 and old injected test/provider callers
    complete their compatibility period.
    """

    name: str

    def search(
        self,
        query: str,
        scene: dict[str, Any],
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        ...


def create_default_asset_providers(
    *,
    load_environment: Callable[[], Any],
) -> list[StockProvider]:
    """Compatibility wrapper over the canonical provider registry."""

    return create_default_stock_providers(load_environment=load_environment)


def environment_enabled(name: str, *, default: bool) -> bool:
    """Compatibility wrapper for the former news-owned environment helper."""

    return provider_environment_enabled(name, default=default)


def provider_capabilities(
    providers_by_name: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for name, provider in providers_by_name.items():
        getter = getattr(provider, "capabilities", None)
        if not callable(getter):
            continue
        try:
            result[name] = getter().to_dict()
        except Exception:
            continue
    return result


def search_provider(
    provider: AssetProvider,
    query: str,
    scene: dict[str, Any],
    semantic_scene: dict[str, Any],
    *,
    project_id: str,
    limit: int,
    media_attempts: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Ask one provider for one query, once per allowed media kind.

    Each media kind is its own provider attempt. A real provider fails per
    endpoint, so a kind that could not be served may not discard what a
    neighbouring kind already returned, and a kind that answered is never asked
    again because of it. ``media_attempts`` is an opt-in collector that receives
    one record per kind - satisfied with its result count, or failed with the
    provider's own machine-readable error - so a half outage stays visible
    instead of hiding behind a whole-scene failure.

    When every requested kind failed there is nothing to keep, and the first
    error is raised exactly as before: a single-kind scene, and a provider that
    is down entirely, behave unchanged.
    """

    if supports_stock_contract(provider):
        preferred = scene_media_type(scene)
        try:
            supported = {
                str(item).strip().casefold()
                for item in provider.capabilities().media_types  # type: ignore[attr-defined]
            }
        except Exception:
            supported = {preferred}
        media_types = _retrieval_media_types(
            scene,
            preferred=preferred,
            supported=supported,
        )

        results: list[dict[str, Any]] = []
        failures: list[BaseException] = []
        for media_type in media_types:
            request = AssetSearchRequest(
                query=query,
                media_type=media_type,
                target_aspect_ratio="9:16",
                orientation_preference="vertical",
                min_width=720,
                min_height=(
                    1080
                    if media_type == "video"
                    else 1280
                    if media_type == "image"
                    else 0
                ),
                max_results=limit,
                scene_id=str(scene.get("scene_id") or ""),
                project_id=project_id,
                semantic_scene=semantic_scene,
                negative_terms=list(
                    semantic_scene.get("must_not_include")
                    or scene.get("negative_keywords")
                    or []
                ),
            )
            try:
                found = [
                    candidate_to_rankable(candidate)
                    for candidate in provider.search(request)  # type: ignore[arg-type]
                ]
            except Exception as exc:
                failures.append(exc)
                if media_attempts is not None:
                    media_attempts.append(
                        _media_attempt_failed(exc, provider=provider, media_type=media_type)
                    )
                continue
            results.extend(found)
            if media_attempts is not None:
                media_attempts.append(
                    {
                        "media_type": media_type,
                        "status": "completed",
                        "result_count": len(found),
                    }
                )
        if failures and len(failures) == len(media_types):
            raise failures[0]
        return results
    try:
        return provider.search(query, scene, limit=limit)
    except TypeError:
        return provider.search(query, scene)


def _media_attempt_failed(
    error: BaseException,
    *,
    provider: AssetProvider,
    media_type: str,
) -> dict[str, Any]:
    """One failed media-kind attempt, classified by code rather than message."""

    if isinstance(error, ProviderError):
        record = error.to_dict()
    else:
        record = {
            "code": "provider_unexpected_error",
            "provider": str(getattr(provider, "name", "")),
            "query": "",
            "retryable": False,
            "message": str(error),
        }
    record["media_type"] = media_type
    return {
        "media_type": media_type,
        "status": "failed",
        "result_count": 0,
        "error": record,
    }


def _retrieval_media_types(
    scene: dict[str, Any],
    *,
    preferred: str,
    supported: set[str],
) -> list[str]:
    """Kinds to request: allowed is the boundary; preferred only orders it.

    Older persisted scenes without routable ``allowed_media_kinds`` keep their
    legacy preferred-only request. Once image and/or video are stated, the
    request pool is their intersection with provider capabilities. This keeps
    IMAGE_ONLY/VIDEO_ONLY hard while giving both allowed kinds to the downstream
    canonical media-selection policy.
    """

    allowed = {
        str(item).strip().casefold()
        for item in (scene.get("allowed_media_kinds") or [])
        if str(item).strip()
    }
    routable = allowed & {"image", "video"}
    if not routable:
        return [preferred]
    other = "image" if preferred == "video" else "video"
    return [
        media_type
        for media_type in (preferred, other)
        if media_type in routable and media_type in supported
    ]


def candidate_to_rankable(candidate: AssetCandidate) -> dict[str, Any]:
    apply_policy_to_candidate(candidate)
    data = candidate.to_manifest_dict()
    data["canonical_asset"] = candidate.to_dict()
    data["keywords"] = data.get("tags", [])
    data["quality_score"] = quality_score(candidate.width, candidate.height)
    data["vertical_score"] = vertical_score(candidate.width, candidate.height)
    data["rights_score"] = (
        1.0
        if candidate.license.allowed_for_render
        and not candidate.license.review_required
        else 0.0
    )
    data["allowed_for_render"] = (
        candidate.license.allowed_for_render and not candidate.license.review_required
    )
    data["review_required"] = candidate.license.review_required
    return data


def with_policy_decision(candidate: dict[str, Any]) -> dict[str, Any]:
    stored_canonical = candidate.get("canonical_asset")
    canonical_data = dict(
        stored_canonical
        if isinstance(stored_canonical, dict) and stored_canonical
        else candidate
    )
    carry_vision_evidence(candidate, canonical_data)
    canonical = AssetCandidate.from_dict(canonical_data)
    if not canonical.provider_asset_id:
        canonical.provider_asset_id = str(
            candidate.get("provider_asset_id")
            or candidate.get("asset_id")
            or canonical.asset_id
        )
    if not canonical.source_page_url:
        canonical.source_page_url = str(
            candidate.get("source_page_url")
            or candidate.get("source_page")
            or candidate.get("source_url")
            or ""
        )
    if not canonical.local_path:
        canonical.local_path = str(
            candidate.get("local_path")
            or candidate.get("path")
            or candidate.get("downloaded_path")
            or ""
        )
    if isinstance(candidate.get("rights_declaration"), dict):
        canonical.rights_declaration = dict(candidate["rights_declaration"])
    if bool(candidate.get("review_required")) and not canonical.license.review_required:
        # A record may state the review requirement beside the licence instead of inside
        # it, and ``AssetLicense`` then derives the nested copy from allowed_for_render.
        # Normalising into a candidate must not be where the requirement disappears.
        canonical.license.review_required = True
    decision = apply_policy_to_candidate(canonical)
    updated = {**candidate, **canonical.to_manifest_dict()}
    updated["canonical_asset"] = canonical.to_dict()
    updated["policy_decision"] = decision.to_dict()
    updated["allowed_for_render"] = decision.allowed_for_render
    updated["review_required"] = decision.review_required
    updated["rights_score"] = (
        1.0 if decision.allowed_for_render and not decision.review_required else 0.0
    )
    return updated


def ensure_selected_asset_downloaded(
    *,
    selected: dict[str, Any],
    ranked_candidates: list[dict[str, Any]],
    providers_by_name: dict[str, AssetProvider],
    project_root: Path | None,
    project_id: str,
    scene_id: str,
    media_index: dict[str, Any],
    max_attempts: int,
    fallback_from_asset_id: str = "",
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    ordered: list[dict[str, Any]] = []
    seen: set[str] = set()
    for candidate in [selected, *ranked_candidates]:
        asset_id = str(candidate.get("asset_id") or "")
        rights_rejection = "rights_not_allowed" in str(
            candidate.get("reject_reason") or ""
        )
        if (
            not asset_id
            or asset_id in seen
            or (candidate.get("rejected") and not rights_rejection)
        ):
            continue
        seen.add(asset_id)
        ordered.append(candidate)
    attempts: list[dict[str, Any]] = []
    selected_asset_id = str(selected.get("asset_id") or "")
    lineage_origin_asset_id = str(fallback_from_asset_id or selected_asset_id)
    for raw_candidate in ordered[: max(1, max_attempts)]:
        candidate = with_policy_decision(raw_candidate)
        candidate_asset_id = str(candidate.get("asset_id") or "")
        if lineage_origin_asset_id and candidate_asset_id != lineage_origin_asset_id:
            candidate["replaces_asset_id"] = lineage_origin_asset_id
            canonical_data = candidate.get("canonical_asset")
            if isinstance(canonical_data, dict):
                rebound = AssetCandidate.from_dict(dict(canonical_data))
                rebound.replaces_asset_id = lineage_origin_asset_id
                candidate["canonical_asset"] = rebound.to_dict()

        if candidate.get("review_required") or not candidate.get(
            "allowed_for_render", True
        ):
            policy_decision = (
                candidate.get("policy_decision")
                if isinstance(candidate.get("policy_decision"), dict)
                else {}
            )
            attempts.append(
                {
                    "asset_id": candidate.get("asset_id", ""),
                    "provider": candidate.get("provider", ""),
                    "scene_id": scene_id,
                    "search_query": candidate.get("search_query", ""),
                    "download_status": "blocked",
                    "reason": "license_review_required",
                    "policy_decision": policy_decision,
                    "error": (
                        "Asset rights are not allowed for render: "
                        f"{policy_decision.get('reason', 'policy_blocked')}."
                    ),
                }
            )
            continue
        existing_path = (
            candidate.get("path")
            or candidate.get("local_path")
            or candidate.get("downloaded_path")
        )
        if existing_path:
            candidate["path"] = str(existing_path)
            candidate["local_path"] = str(existing_path)
            candidate["downloaded_path"] = str(existing_path)
            candidate.setdefault("download_status", "local")
            return public_candidate(candidate), attempts
        if not project_root:
            return public_candidate(candidate), attempts
        canonical_data = (
            candidate.get("canonical_asset")
            if isinstance(candidate.get("canonical_asset"), dict)
            else candidate
        )
        canonical = AssetCandidate.from_dict(canonical_data)
        canonical.project_id = canonical.project_id or project_id
        canonical.scene_id = canonical.scene_id or scene_id
        canonical.provenance.project_id = canonical.project_id
        canonical.provenance.scene_id = canonical.scene_id
        canonical.provenance.search_query = (
            canonical.provenance.search_query or canonical.search_query
        )
        provider = providers_by_name.get(canonical.provider)
        attempt = {
            "asset_id": canonical.asset_id,
            "provider": canonical.provider,
            "scene_id": scene_id,
            "search_query": canonical.search_query,
            "download_status": "started",
        }
        if not provider or not supports_stock_contract(provider):
            attempt.update(
                {
                    "download_status": "skipped",
                    "reason": "provider_has_no_download_contract",
                }
            )
            attempts.append(attempt)
            continue
        try:
            license_data = provider.resolve_license(canonical)  # type: ignore[attr-defined]
            canonical.license = license_data
            if license_data.review_required or not license_data.allowed_for_render:
                raise LicenseReviewRequired(
                    "license review required",
                    provider=canonical.provider,
                    query=canonical.search_query,
                )
            downloaded = provider.download(  # type: ignore[attr-defined]
                canonical,
                project_root / "assets" / "downloaded",
                DownloadContext(
                    project_id=project_id,
                    scene_id=scene_id,
                    search_query=canonical.search_query,
                ),
            )
            manifest = downloaded.to_manifest_dict()
            manifest.update(
                {
                    "selected_by": candidate.get("selected_by", "provider"),
                    "scene_match_score": candidate.get(
                        "scene_match_score",
                        candidate.get("final_score", 0),
                    ),
                    "final_score": candidate.get(
                        "final_score",
                        candidate.get("total_score", 0),
                    ),
                    "download_status": "downloaded",
                }
            )
            carry_decision(candidate, manifest)
            register_asset(media_index, manifest)
            attempt.update(
                {
                    "download_status": "downloaded",
                    "local_path": manifest.get("path", ""),
                    "checksum_sha256": manifest.get("checksum_sha256", ""),
                    "technical_validation": manifest.get(
                        "technical_validation",
                        {},
                    ),
                }
            )
            attempts.append(attempt)
            return public_candidate(manifest), attempts
        except LicenseReviewRequired as exc:
            attempt.update(
                {
                    "download_status": "blocked",
                    "reason": exc.code,
                    "error": str(exc),
                }
            )
            attempts.append(attempt)
        except ProviderError as exc:
            attempt.update(
                {
                    "download_status": "failed",
                    "reason": exc.code,
                    "error": str(exc),
                    "retryable": exc.retryable,
                }
            )
            attempts.append(attempt)
    return None, attempts


def supports_stock_contract(provider: Any) -> bool:
    return all(
        hasattr(provider, name)
        for name in ("capabilities", "resolve_license", "download", "health_check")
    )


def scene_media_type(scene: dict[str, Any]) -> str:
    return (
        "image"
        if scene.get("visual_type") in {"image", "animated_image"}
        else "video"
    )


def public_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in candidate.items() if not key.startswith("_")}


def rank_provider_results(
    results: list[dict[str, Any]],
    scene: dict[str, Any],
    query: str = "",
    fallback_level: int = 1,
) -> list[dict[str, Any]]:
    ranked = []
    for raw in results:
        rights_status = raw.get("rights_status") or RIGHTS_REFERENCE_ONLY
        allowed = rights_status in RIGHTS_ALLOWED_STATUSES
        width = int(raw.get("width") or 0)
        height = int(raw.get("height") or 0)
        ranked_item = {
            "schema_version": int(
                raw.get("schema_version") or ASSET_SCHEMA_VERSION
            ),
            "asset_id": raw.get("asset_id")
            or raw.get("id")
            or stable_asset_id(raw),
            "provider": raw.get("provider", ""),
            "provider_asset_id": raw.get("provider_asset_id", ""),
            "type": raw.get("type")
            or raw.get("media_type")
            or scene.get("visual_type", ""),
            "media_type": raw.get("media_type")
            or raw.get("type")
            or scene.get("visual_type", ""),
            "title": raw.get("title", ""),
            "description": raw.get("description", ""),
            "keywords": raw.get("keywords", []),
            "tags": raw.get("tags", []),
            "vision_tags": raw.get("vision_tags", []),
            "vision_tags_asset_id": raw.get("vision_tags_asset_id", ""),
            "vision_tags_source_sha256": raw.get("vision_tags_source_sha256", ""),
            "vision_tags_cache_key": raw.get("vision_tags_cache_key", ""),
            "replaces_asset_id": raw.get("replaces_asset_id", ""),
            "source_url": raw.get("source_url")
            or raw.get("source_page_url", ""),
            "source_page": raw.get("source_page")
            or raw.get("source_page_url", ""),
            "source_page_url": raw.get("source_page_url")
            or raw.get("source_page")
            or raw.get("source_url", ""),
            "preview_url": raw.get("preview_url", ""),
            "download_url": raw.get("download_url", ""),
            "author": raw.get("author") or raw.get("author_name", ""),
            "author_name": raw.get("author_name") or raw.get("author", ""),
            "license": raw.get("license", "unknown"),
            "license_name": raw.get("license_name", ""),
            "provenance": raw.get("provenance", {}),
            "canonical_asset": raw.get("canonical_asset", {}),
            "technical_validation": raw.get("technical_validation", {}),
            "checksum_sha256": raw.get("checksum_sha256", ""),
            "policy_decision": raw.get("policy_decision", {}),
            "rights_status": rights_status,
            "allowed_for_render": allowed,
            "review_required": raw.get("review_required", False),
            "width": width,
            "height": height,
            "duration": float(raw.get("duration") or raw.get("duration_sec") or 0),
            "duration_sec": float(
                raw.get("duration_sec") or raw.get("duration") or 0
            ),
            "relevance_score": float(raw.get("relevance_score", 0.5)),
            "quality_score": quality_score(width, height),
            "vertical_score": vertical_score(width, height),
            "rights_score": 1.0 if allowed else 0.0,
            "duplicate_penalty": 0,
            "watermark_penalty": float(raw.get("watermark_penalty", 0)),
            "total_score": (
                float(raw.get("relevance_score", 0.5))
                + quality_score(width, height)
                + vertical_score(width, height)
            ),
            "selected_by": "provider",
            "search_query": query
            or raw.get("search_query", scene.get("primary_query", "")),
            "fallback_level": fallback_level,
            "crop_suitability_score": raw.get(
                "crop_suitability_score",
                raw.get("vertical_score", 0),
            ),
        }
        ranked.append(with_policy_decision(ranked_item))
    return ranked


def rights_block_attempts(
    candidates: list[dict[str, Any]],
    scene_id: str,
) -> list[dict[str, Any]]:
    attempts: list[dict[str, Any]] = []
    for raw_candidate in candidates[:3]:
        candidate = with_policy_decision(raw_candidate)
        if not (
            candidate.get("review_required")
            or not candidate.get("allowed_for_render", True)
        ):
            continue
        policy_decision = (
            candidate.get("policy_decision")
            if isinstance(candidate.get("policy_decision"), dict)
            else {}
        )
        attempts.append(
            {
                "asset_id": candidate.get("asset_id", ""),
                "provider": candidate.get("provider", ""),
                "scene_id": scene_id,
                "search_query": candidate.get("search_query", ""),
                "download_status": "blocked",
                "reason": "license_review_required",
                "policy_decision": policy_decision,
                "error": (
                    "Asset rights are not allowed for render: "
                    f"{policy_decision.get('reason', 'policy_blocked')}."
                ),
            }
        )
    return attempts


def quality_score(width: int, height: int) -> float:
    pixels = width * height
    if pixels >= 1920 * 1080:
        return 10.0
    if pixels >= 1280 * 720:
        return 7.0
    if pixels:
        return 3.0
    return 1.0


def vertical_score(width: int, height: int) -> float:
    if not width or not height:
        return 0.0
    ratio = width / height
    return max(0.0, 10.0 - abs(ratio - (9 / 16)) * 10)


def stable_asset_id(asset: dict[str, Any]) -> str:
    raw = "|".join(
        str(asset.get(key, ""))
        for key in ("provider", "source_url", "local_path", "path", "id")
    )
    return "asset_" + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]
