from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any, Protocol

from PIL import Image

from src.assets.generated_infographic import build_generated_asset, spec_from_scene
from src.assets.provider_routing import route_providers
from src.assets.query_adapter import STATUS_TRANSLATION_REQUIRED, build_scene_queries
from src.assets.scene_strategy import CLASS_DATA_INFOGRAPHIC
from src.assets.semantic_selection import analyze_scene, check_continuity, ordered_queries, rank_candidates, select_best_candidate
from src.assets.download import sha256_file, validate_local_asset
from src.assets.license_policy import apply_policy_to_candidate
from src.assets.models import ASSET_SCHEMA_VERSION, AssetCandidate, AssetLicense, AssetProvenance
from src.assets.provider_contract import AssetSearchRequest, DownloadContext, LicenseReviewRequired, ProviderError
from src.assets.review_bundle import create_scene_review_bundle, select_candidate_after_review, write_review_bundle
from src.assets.semantic_visual_service import analyse_semantic_visual_for_project, load_semantic_visual_config
from src.assets.visual_preview import VisualPreviewRequest, load_visual_preview_config, prepare_candidate_preview_analyses
from src.media_library import load_media_index, register_asset, search_local_assets
from src.providers import InternetArchiveStockProvider, NasaImageLibraryStockProvider, PexelsStockProvider, PixabayStockProvider, WikimediaCommonsStockProvider
from src.providers.envato_manual_provider import EnvatoManualProvider
from src.providers import pexels_provider, pixabay_provider, unsplash_provider
from .models import ALLOWED_RENDER_RIGHTS, RIGHTS_REFERENCE_ONLY, RIGHTS_USER_OWNED


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v"}


class AssetProvider(Protocol):
    name: str

    def search(self, query: str, scene: dict[str, Any], limit: int = 5) -> list[dict[str, Any]]:
        ...


def build_assets_manifest(
    *,
    visual_plan: dict[str, Any],
    user_assets: list[str],
    media_index: dict[str, Any],
    providers: list[AssetProvider] | None = None,
    dry_run: bool = False,
    channel: str = "nature_science_news_ru",
    allow_generated_fallback: bool = False,
    asset_selection: dict[str, Any] | None = None,
    project_root: str | Path | None = None,
    project_id: str = "",
    max_download_attempts: int = 3,
) -> dict[str, Any]:
    visual_preview_config = load_visual_preview_config()
    semantic_visual_config = load_semantic_visual_config()
    selection_config = {
        "mode": "semantic",
        "legacy_fallback_enabled": False,
        "vision_validation_enabled": False,
        "visual_preview": {
            "enabled": bool(visual_preview_config.get("enabled", True)),
            "mode": str(visual_preview_config.get("mode") or "analyse_and_report"),
            "shortlist_size": int(visual_preview_config.get("shortlist_size") or 5),
            "technical_rerank_enabled": bool(visual_preview_config.get("technical_rerank_enabled", False)),
            "target_aspect_ratio": "9:16",
            "offline": False,
            "no_html": False,
        },
        "semantic_visual": {
            "enabled": bool(semantic_visual_config.get("enabled", False)),
            "mode": str(semantic_visual_config.get("mode") or "analyse_and_report"),
            "backend": str(semantic_visual_config.get("backend") or "mock"),
            "maximum_candidates": int(semantic_visual_config.get("maximum_candidates") or 5),
            "maximum_frames_per_candidate": int(semantic_visual_config.get("maximum_frames_per_candidate") or 5),
            "semantic_rerank_enabled": bool(semantic_visual_config.get("semantic_rerank_enabled", False)),
            "allow_paid_vision": bool(semantic_visual_config.get("allow_paid_vision", False)),
            "offline": False,
            "no_html": False,
        },
    }
    if asset_selection:
        selection_config = _merge_selection_config(selection_config, asset_selection)
    user_candidates = [_inspect_user_asset(path, index) for index, path in enumerate(user_assets, start=1)]
    provider_errors: list[dict[str, Any]] = []
    provider_attempts: list[dict[str, Any]] = []
    routing_decisions: list[dict[str, Any]] = []
    scene_entries: list[dict[str, Any]] = []
    missing_scenes: list[dict[str, Any]] = []
    used_asset_ids: set[str] = set()
    providers_by_name = {provider.name: provider for provider in providers or []}
    project_root_path = Path(project_root) if project_root else None
    review_bundles = []
    review_output: dict[str, str] = {}

    for scene in visual_plan.get("scenes", []):
        semantic_scene = analyze_scene(scene)
        candidates: list[dict[str, Any]] = []
        scene_provider_attempts: list[dict[str, Any]] = []
        manual_request: dict[str, Any] | None = None
        provider_capabilities = _provider_capabilities(providers_by_name)
        routing_decision = route_providers(
            scene,
            provider_names=list(providers_by_name.keys()),
            provider_enabled={name: True for name in providers_by_name},
            capabilities=provider_capabilities,
        )
        routing_decisions.append(routing_decision)
        # One query plan per scene, built per provider: a provider that cannot be
        # searched in the plan's language gets an English query or no request at all.
        query_plan = build_scene_queries(
            scene,
            providers=list(routing_decision["ordered_providers"]),
            intent_language=str(visual_plan.get("intent_language") or visual_plan.get("language") or "ru"),
            capabilities=provider_capabilities,
        )
        source_class = str(routing_decision.get("source_class") or "")
        required_duration = float(scene.get("target_duration_sec") or 0)
        preferred = set(scene.get("preferred_asset_ids") or [])
        user_ranked = _rank_user_assets(user_candidates, scene, preferred, used_asset_ids)
        candidates.extend(user_ranked)
        candidates.extend(_rank_local_assets(media_index, scene, channel, used_asset_ids))
        if not dry_run:
            ordered_provider_names = routing_decision["ordered_providers"] or list(providers_by_name)
            ordered_providers = [providers_by_name[name] for name in ordered_provider_names if name in providers_by_name]
            for provider in ordered_providers:
                planned = query_plan.for_provider(provider.name)
                if not planned:
                    # Either nothing could be written in a language this provider
                    # indexes, or the scene needs no search at all. Either way a
                    # request is not sent: a query in the wrong language returns
                    # noise that then has to be rejected downstream.
                    blocked = [
                        item for item in query_plan.queries
                        if item.provider == provider.name and item.status == STATUS_TRANSLATION_REQUIRED
                    ]
                    for item in blocked:
                        skipped_attempt = {
                            "scene_id": scene.get("scene_id", ""),
                            "provider": provider.name,
                            "query": "",
                            "status": "skipped",
                            "reason": STATUS_TRANSLATION_REQUIRED,
                            "message": item.notes,
                        }
                        scene_provider_attempts.append(skipped_attempt)
                        provider_attempts.append(skipped_attempt)
                    continue
                allowed_queries = [
                    {"kind": item.kind, "fallback_level": item.fallback_level, "query": item.query, "language": item.language, "query_source": item.source}
                    for item in planned
                ]
                allowed_queries = [
                    query for query in allowed_queries if not _query_not_allowed_for_scene(semantic_scene, query)
                ]
                for query in allowed_queries:
                    attempt = {
                        "scene_id": scene.get("scene_id", ""),
                        "provider": provider.name,
                        "query": str(query["query"]),
                        "query_language": str(query.get("language") or ""),
                        "query_source": str(query.get("query_source") or ""),
                        "status": "started",
                    }
                    try:
                        provider_results = _search_provider(
                            provider,
                            str(query["query"]),
                            scene,
                            semantic_scene.to_dict(),
                            project_id=project_id,
                            limit=5,
                        )
                        candidates.extend(_rank_provider_results(provider_results, scene, str(query["query"]), int(query["fallback_level"])))
                        attempt.update({"status": "completed", "result_count": len(provider_results)})
                    except ProviderError as exc:
                        error = exc.to_dict()
                        error.update({"scene_id": scene.get("scene_id", ""), "query": str(query["query"])})
                        provider_errors.append(error)
                        attempt.update({"status": "failed", "error": error})
                    except Exception as exc:
                        error = {
                            "code": "provider_unexpected_error",
                            "provider": provider.name,
                            "scene_id": scene.get("scene_id", ""),
                            "query": str(query["query"]),
                            "message": str(exc),
                        }
                        provider_errors.append(error)
                        attempt.update({"status": "failed", "error": error})
                    scene_provider_attempts.append(attempt)
                    provider_attempts.append(attempt)
        generated_asset: dict[str, Any] | None = None
        if source_class == CLASS_DATA_INFOGRAPHIC and project_root_path and not dry_run:
            # There is no footage of a statistic. Draw it from the scene's own numbers
            # instead of accepting whatever a stock search returns for the words.
            spec = spec_from_scene(scene)
            if spec is not None:
                generated_asset = build_generated_asset(
                    spec,
                    project_root=project_root_path,
                    project_id=project_id or project_root_path.name,
                    scene_id=str(scene.get("scene_id") or ""),
                )
                candidates.insert(0, generated_asset)
        if user_ranked:
            selected = sorted(user_ranked, key=lambda item: item.get("total_score", 0), reverse=True)[0]
            candidates.sort(key=lambda item: item.get("total_score", 0), reverse=True)
        elif generated_asset is not None:
            selected = generated_asset
        elif selection_config["mode"] == "semantic":
            selected, ranked_candidates = select_best_candidate(
                semantic_scene,
                candidates,
                used_asset_ids=used_asset_ids,
                required_duration_sec=required_duration,
                require_provider_metadata=bool(routing_decision.get("requires_provider_metadata")),
            )
            candidates = ranked_candidates
        else:
            candidates.sort(key=lambda item: item.get("total_score", 0), reverse=True)
            selected = candidates[0] if candidates else None
        visual_review_entry: dict[str, Any] = {}
        preview_settings = selection_config.get("visual_preview", {}) if isinstance(selection_config.get("visual_preview"), dict) else {}
        if project_root_path and candidates and bool(preview_settings.get("enabled", True)):
            top_k = int(preview_settings.get("shortlist_size") or visual_preview_config.get("shortlist_size") or 5)
            request = VisualPreviewRequest(
                project_id=project_id,
                scene_id=str(scene.get("scene_id") or ""),
                top_k=top_k,
                target_aspect_ratio=str(preview_settings.get("target_aspect_ratio") or "9:16"),
                project_root=str(project_root_path),
                refresh=bool(preview_settings.get("refresh", False)),
                offline=bool(preview_settings.get("offline", False)),
                technical_rerank=bool(preview_settings.get("technical_rerank_enabled", False)),
                no_html=bool(preview_settings.get("no_html", False)),
                sample_count=int(visual_preview_config.get("frame_sample_count") or 5),
                sample_positions=[float(item) for item in visual_preview_config.get("frame_sample_positions", [0.1, 0.3, 0.5, 0.7, 0.9])],
                target_aspect_ratios=[str(item) for item in visual_preview_config.get("target_aspect_ratios", ["9:16", "16:9", "1:1"])],
            )
            analyses = prepare_candidate_preview_analyses(
                candidates,
                providers_by_name=providers_by_name,
                request=request,
                config=visual_preview_config,
            )
            metadata_selected_id = str((selected or {}).get("asset_id") or (candidates[0].get("asset_id") if candidates else ""))
            if bool(preview_settings.get("technical_rerank_enabled", False)):
                selected = select_candidate_after_review(
                    candidates[:top_k],
                    analyses,
                    metadata_selected_id=metadata_selected_id,
                    technical_rerank=True,
                    target_aspect_ratio=request.target_aspect_ratio,
                )
            selected_id = str((selected or {}).get("asset_id") or metadata_selected_id)
            bundle = create_scene_review_bundle(
                project_id=project_id,
                scene=scene,
                semantic_scene=semantic_scene.to_dict(),
                metadata_queries=ordered_queries(semantic_scene),
                provider_routing=routing_decision,
                candidates=candidates[:top_k],
                analyses=analyses,
                selected_candidate_id=selected_id,
                target_aspect_ratio=request.target_aspect_ratio,
                manual_request=manual_request,
                technical_rerank_enabled=bool(preview_settings.get("technical_rerank_enabled", False)),
            )
            review_bundles.append(bundle)
            visual_review_entry = {
                "status": "prepared",
                "analysis_mode": "technical_rerank" if bool(preview_settings.get("technical_rerank_enabled", False)) else "analyse_and_report",
                "analysed_candidates": len(analyses),
                "selected_candidate_before_rerank": metadata_selected_id,
                "selected_candidate_after_rerank": selected_id,
                "manifest_path": str(project_root_path / "assets" / "review" / "visual_review_manifest.json"),
                "html_path": "" if bool(preview_settings.get("no_html", False)) else str(project_root_path / "assets" / "review" / "visual_review_board.html"),
            }
        download_attempts: list[dict[str, Any]] = []
        if generated_asset is not None and selected is generated_asset:
            # Already a real local file with its own checksum and provenance; there is
            # nothing to fetch, and sending it through the download path only fails
            # because no provider owns it.
            download_attempts = []
        elif selected:
            selected, download_attempts = _ensure_selected_asset_downloaded(
                selected=selected,
                ranked_candidates=candidates,
                providers_by_name=providers_by_name,
                project_root=project_root_path,
                project_id=project_id,
                scene_id=str(scene.get("scene_id") or ""),
                media_index=media_index,
                max_attempts=max_download_attempts,
            )
        # There used to be a branch here that downloaded ``candidates[0]`` when nothing
        # passed selection. It made every rejection meaningless: a candidate refused for
        # missing the scene's subject was fetched and rendered anyway. A scene with no
        # acceptable candidate is now left unresolved, which is the whole point of
        # having a gate. The rights verdict is still reported - it is known from the
        # licence policy before any request, so it never needed a download to discover.
        elif candidates:
            download_attempts = _rights_block_attempts(candidates, str(scene.get("scene_id") or ""))
        if download_attempts:
            provider_attempts.extend(download_attempts)
        if (
            not selected
            and allow_generated_fallback
            and not dry_run
            and (allow_generated_fallback or bool(selection_config.get("legacy_fallback_enabled", False)))
        ):
            selected = _generated_fallback_asset(scene)
        if (
            not selected
            and not dry_run
            and project_root_path
            and bool(selection_config.get("envato_manual_fallback_enabled", False))
        ):
            manual_request = EnvatoManualProvider(projects_root=project_root_path.parent).prepare_request(
                project_id=project_id or project_root_path.name,
                scene_id=str(scene.get("scene_id") or ""),
                scene=scene,
                queries=[str(item["query"]) for item in ordered_queries(semantic_scene)[:3] if item.get("query")],
                limit=int(selection_config.get("envato_manual_query_limit") or 6),
                open_browser=False,
            )
        if selected:
            used_asset_ids.add(selected["asset_id"])
        else:
            missing_scenes.append(
                {
                    "scene_id": scene.get("scene_id"),
                    "primary_query": scene.get("primary_query", ""),
                    "semantic_queries": ordered_queries(semantic_scene),
                    "semantic_scene": semantic_scene.to_dict(),
                    "provider_attempts": scene_provider_attempts,
                    "download_attempts": download_attempts,
                    "manual_request": manual_request or {},
                    "source_class": source_class,
                    "asset_strategy": routing_decision.get("strategy", {}),
                    "query_plan": query_plan.to_dict(),
                    "untranslatable_providers": list(query_plan.untranslatable_providers),
                    "rejected_reasons": sorted(
                        {str(item.get("reject_reason") or "") for item in candidates if item.get("rejected")} - {""}
                    ),
                    "reason": (
                        "manual_action_required"
                        if manual_request
                        else "unresolved_generator_failed"
                        if source_class == CLASS_DATA_INFOGRAPHIC
                        else _missing_reason(dry_run, candidates, download_attempts)
                    ),
                }
            )
        scene_entries.append(
            {
                "scene_id": scene.get("scene_id"),
                "primary_query": scene.get("primary_query", ""),
                "queries": ordered_queries(semantic_scene),
                "visual_type": scene.get("visual_type", ""),
                "semantic_scene": semantic_scene.to_dict(),
                "provider_routing": routing_decision,
                "asset_strategy": routing_decision.get("strategy", {}),
                "source_class": source_class,
                "query_plan": query_plan.to_dict(),
                "required_duration_sec": required_duration,
                "selected_asset": selected,
                "manual_request": manual_request or {},
                "visual_review": visual_review_entry,
                "provider_attempts": scene_provider_attempts,
                "download_attempts": download_attempts,
                "ranked_candidates": [_public_candidate(candidate) for candidate in candidates[:10]],
                "candidates": [_public_candidate(candidate) for candidate in candidates[:5]],
                "rejected_candidates": [_public_candidate(candidate) for candidate in candidates if candidate.get("rejected")][:5],
            }
        )
    continuity = check_continuity(scene_entries)
    if continuity["status"] == "failed":
        for issue in continuity["issues"]:
            missing_scenes.append({"scene_id": issue["scene_id"], "reason": issue["reason"]})
    if project_root_path and review_bundles:
        preview_settings = selection_config.get("visual_preview", {}) if isinstance(selection_config.get("visual_preview"), dict) else {}
        review_output = write_review_bundle(project_root_path, review_bundles, write_html=not bool(preview_settings.get("no_html", False)))
        semantic_settings = selection_config.get("semantic_visual", {}) if isinstance(selection_config.get("semantic_visual"), dict) else {}
        if bool(semantic_settings.get("enabled", False)):
            analyse_semantic_visual_for_project(
                project_root=project_root_path,
                project_id=project_id,
                all_scenes=True,
                backend_name=str(semantic_settings.get("backend") or "mock"),
                offline=bool(semantic_settings.get("offline", False)),
                maximum_candidates=int(semantic_settings.get("maximum_candidates") or semantic_visual_config.get("maximum_candidates") or 5),
                maximum_frames=int(semantic_settings.get("maximum_frames_per_candidate") or semantic_visual_config.get("maximum_frames_per_candidate") or 5),
                no_html=bool(semantic_settings.get("no_html", False)),
                config=semantic_visual_config,
            )

    return {
        "schema_version": ASSET_SCHEMA_VERSION,
        "dry_run": dry_run,
        "asset_selection": selection_config,
        "provider_order": ["user_assets", "local_library", *[provider.name for provider in providers or []]],
        "routing_decisions": routing_decisions,
        "assets": user_candidates,
        "scenes": scene_entries,
        "missing_scenes": missing_scenes,
        "continuity": continuity,
        "provider_attempts": provider_attempts,
        "provider_errors": provider_errors,
        "visual_review": {
            "enabled": bool((selection_config.get("visual_preview") or {}).get("enabled", False)) if isinstance(selection_config.get("visual_preview"), dict) else False,
            "mode": str((selection_config.get("visual_preview") or {}).get("mode", "analyse_and_report")) if isinstance(selection_config.get("visual_preview"), dict) else "analyse_and_report",
            "manifest_path": review_output.get("json_path", ""),
            "html_path": review_output.get("html_path", ""),
        },
        "semantic_visual": {
            "enabled": bool((selection_config.get("semantic_visual") or {}).get("enabled", False)) if isinstance(selection_config.get("semantic_visual"), dict) else False,
            "mode": str((selection_config.get("semantic_visual") or {}).get("mode", "analyse_and_report")) if isinstance(selection_config.get("semantic_visual"), dict) else "analyse_and_report",
            "semantic_rerank_enabled": False,
        },
        "warnings": _warnings(dry_run, provider_errors, missing_scenes),
    }


def build_news_asset_manifest(
    *,
    visual_plan: dict[str, Any],
    user_assets: list[str],
    dry_run: bool,
    channel: str = "nature_science_news_ru",
    media_index_path: str | Path | None = None,
    debug_placeholders: bool = False,
    asset_selection: dict[str, Any] | None = None,
    project_root: str | Path | None = None,
    project_id: str = "",
) -> dict[str, Any]:
    media_index = {"version": 1, "items": []} if dry_run else load_media_index(media_index_path or "assets/library/metadata/media_index.json")
    providers = [] if dry_run else create_default_asset_providers()
    return build_assets_manifest(
        visual_plan=visual_plan,
        user_assets=user_assets,
        media_index=media_index,
        providers=providers,
        dry_run=dry_run,
        channel=channel,
        allow_generated_fallback=debug_placeholders and not dry_run,
        asset_selection=asset_selection,
        project_root=project_root,
        project_id=project_id,
    )


def create_default_asset_providers() -> list[AssetProvider]:
    providers: list[AssetProvider] = []
    if _env_enabled("WIKIMEDIA_ENABLED", default=True):
        providers.append(WikimediaCommonsStockProvider())
    if _env_enabled("NASA_IMAGES_ENABLED", default=True):
        providers.append(NasaImageLibraryStockProvider())
    if _env_enabled("INTERNET_ARCHIVE_ENABLED", default=True):
        providers.append(InternetArchiveStockProvider())
    if os.getenv("PEXELS_API_KEY"):
        providers.append(PexelsStockProvider(os.getenv("PEXELS_API_KEY", "")))
    if os.getenv("PIXABAY_API_KEY"):
        providers.append(PixabayStockProvider(os.getenv("PIXABAY_API_KEY", "")))
    return providers


def _merge_selection_config(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            nested = dict(merged[key])
            nested.update(value)
            merged[key] = nested
        else:
            merged[key] = value
    return merged


def _env_enabled(name: str, *, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return str(value).strip().lower() not in {"0", "false", "no", "off", "disabled"}


class PexelsAssetProvider:
    name = "pexels"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    def search(self, query: str, scene: dict[str, Any], limit: int = 5) -> list[dict[str, Any]]:
        if scene.get("visual_type") in {"image", "animated_image"}:
            photos = pexels_provider.search_images(self.api_key, query, per_page=limit)
            return [
                {
                    "asset_id": f"pexels_photo_{photo.get('id')}",
                    "provider": self.name,
                    "type": "image",
                    "source_url": photo.get("url", ""),
                    "source_page": photo.get("url", ""),
                    "author": photo.get("photographer", ""),
                    "license": "pexels",
                    "rights_status": "licensed",
                    "width": photo.get("width", 0),
                    "height": photo.get("height", 0),
                    "duration": 0,
                    "relevance_score": 6,
                }
                for photo in photos
            ]
        videos = pexels_provider.search_videos(self.api_key, query, per_page=limit)
        return [
            {
                "asset_id": f"pexels_video_{video.get('id')}",
                "provider": self.name,
                "type": "video",
                "source_url": video.get("url", ""),
                "source_page": video.get("url", ""),
                "author": video.get("user", {}).get("name", ""),
                "license": "pexels",
                "rights_status": "licensed",
                "width": video.get("width", 0),
                "height": video.get("height", 0),
                "duration": video.get("duration", 0),
                "relevance_score": 6,
            }
            for video in videos
        ]


class PixabayAssetProvider:
    name = "pixabay"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    def search(self, query: str, scene: dict[str, Any], limit: int = 5) -> list[dict[str, Any]]:
        if scene.get("visual_type") in {"image", "animated_image"}:
            hits = pixabay_provider.search_images(self.api_key, query, per_page=limit)
            return [
                {
                    "asset_id": f"pixabay_image_{hit.get('id')}",
                    "provider": self.name,
                    "type": "image",
                    "source_url": hit.get("pageURL", ""),
                    "source_page": hit.get("pageURL", ""),
                    "author": hit.get("user", ""),
                    "license": "pixabay",
                    "rights_status": "licensed",
                    "width": hit.get("imageWidth", 0),
                    "height": hit.get("imageHeight", 0),
                    "duration": 0,
                    "relevance_score": 5,
                }
                for hit in hits
            ]
        hits = pixabay_provider.search_videos(self.api_key, query, per_page=limit)
        return [
            {
                "asset_id": f"pixabay_video_{hit.get('id')}",
                "provider": self.name,
                "type": "video",
                "source_url": hit.get("pageURL", ""),
                "source_page": hit.get("pageURL", ""),
                "author": hit.get("user", ""),
                "license": "pixabay",
                "rights_status": "licensed",
                "width": hit.get("videos", {}).get("large", {}).get("width", 0),
                "height": hit.get("videos", {}).get("large", {}).get("height", 0),
                "duration": hit.get("duration", 0),
                "relevance_score": 5,
            }
            for hit in hits
        ]


class UnsplashAssetProvider:
    name = "unsplash"

    def __init__(self, access_key: str) -> None:
        self.access_key = access_key

    def search(self, query: str, scene: dict[str, Any], limit: int = 5) -> list[dict[str, Any]]:
        if scene.get("visual_type") not in {"image", "animated_image"}:
            return []
        hits = unsplash_provider.search_images(self.access_key, query, per_page=limit)
        return [
            {
                "asset_id": f"unsplash_image_{hit.get('id')}",
                "provider": self.name,
                "type": "image",
                "source_url": hit.get("links", {}).get("html", ""),
                "source_page": hit.get("links", {}).get("html", ""),
                "author": hit.get("user", {}).get("name", ""),
                "license": "unsplash",
                "rights_status": "licensed",
                "width": hit.get("width", 0),
                "height": hit.get("height", 0),
                "duration": 0,
                "relevance_score": 5,
            }
            for hit in hits
        ]


def _inspect_user_asset(path: Any, index: int) -> dict[str, Any]:
    raw = path if isinstance(path, dict) else {"path": str(path)}
    source = Path(str(raw.get("path") or raw.get("local_path") or ""))
    media_type = _media_type(source)
    asset_id = str(raw.get("asset_id") or f"user_asset_{index:03d}")
    rights_declaration = dict(raw.get("rights_declaration") or {})
    if not rights_declaration:
        rights_declaration = {
            "confirmation_status": "missing",
            "rights_status": "unconfirmed",
            "notes": "Manual asset rights were not confirmed by the owner.",
        }
    provider_asset_id = str(raw.get("provider_asset_id") or asset_id)
    source_url = str(raw.get("source_page_url") or raw.get("source_url") or f"manual://{provider_asset_id}")
    width = int(raw.get("width") or 0)
    height = int(raw.get("height") or 0)
    technical_validation: dict[str, Any] = {}
    checksum = ""
    if source.exists():
        try:
            technical_validation = validate_local_asset(source, media_type)
            width = int(technical_validation.get("width") or width)
            height = int(technical_validation.get("height") or height)
            checksum = sha256_file(source)
        except Exception:
            if media_type == "image":
                try:
                    with Image.open(source) as image:
                        width, height = image.size
                except Exception:
                    width = height = 0
    candidate = AssetCandidate(
        asset_id=asset_id,
        provider="user",
        provider_asset_id=provider_asset_id,
        media_type=media_type,
        title=str(raw.get("title") or source.stem),
        description=str(raw.get("description") or ""),
        tags=[source.stem],
        source_page_url=source_url,
        preview_url=str(raw.get("preview_url") or ""),
        download_url=str(raw.get("download_url") or source_url),
        author_name=str(raw.get("author") or raw.get("author_name") or "user"),
        width=width,
        height=height,
        duration_sec=float(raw.get("duration") or raw.get("duration_sec") or 0),
        local_path=str(source),
        original_filename=source.name,
        checksum_sha256=checksum,
        license=AssetLicense(
            license_name=str(rights_declaration.get("license_name") or raw.get("license") or "user_owned"),
            rights_status=str(rights_declaration.get("rights_status") or RIGHTS_USER_OWNED),
            allowed_for_render=False,
            review_required=True,
            notes=str(rights_declaration.get("notes") or ""),
        ),
        provenance=AssetProvenance(
            provider="user",
            provider_asset_id=provider_asset_id,
            source_page_url=source_url,
            download_url=str(raw.get("download_url") or source_url),
            original_filename=source.name,
            checksum_sha256=checksum,
            metadata_snapshot={"rights_declaration": rights_declaration},
        ),
        technical_validation=technical_validation,
        rights_declaration=rights_declaration,
    )
    apply_policy_to_candidate(candidate)
    data = candidate.to_manifest_dict()
    data.update(
        {
            "author": candidate.author_name,
            "vertical_score": _vertical_score(width, height),
            "quality_score": 0.7 if source.exists() else 0.2,
            "rights_score": 1.0 if candidate.license.allowed_for_render and not candidate.license.review_required else 0.0,
        }
    )
    return data


def _rank_user_assets(
    assets: list[dict[str, Any]],
    scene: dict[str, Any],
    preferred: set[str],
    used_asset_ids: set[str],
) -> list[dict[str, Any]]:
    ranked = []
    for asset in assets:
        score = 100.0
        if asset["asset_id"] in preferred:
            score += 20
        if asset["asset_id"] in used_asset_ids:
            score -= 30
        ranked.append({**asset, "total_score": score, "selected_by": "user_asset_priority"})
    return ranked


def _rank_local_assets(
    media_index: dict[str, Any],
    scene: dict[str, Any],
    channel: str,
    used_asset_ids: set[str],
) -> list[dict[str, Any]]:
    media_type = "image" if scene.get("visual_type") in {"image", "animated_image"} else "video"
    matches = search_local_assets(
        media_index,
        {
            "visual_keywords": scene.get("primary_query", "").split(),
            "scene_type": scene.get("visual_type", ""),
            "duration": scene.get("target_duration_sec", 0),
        },
        media_type=media_type,
        channel=channel,
        min_score=1,
        limit=10,
    )
    ranked = []
    for match in matches:
        asset = match["asset"]
        rights_status = asset.get("rights_status") or RIGHTS_REFERENCE_ONLY
        allowed = rights_status in ALLOWED_RENDER_RIGHTS
        asset_id = asset.get("id") or _stable_asset_id(asset)
        if asset_id in used_asset_ids:
            continue
        duplicate_penalty = 25 if asset_id in used_asset_ids else 0
        width = int(asset.get("width") or 0)
        height = int(asset.get("height") or 0)
        ranked_item = {
            "schema_version": int(asset.get("schema_version") or 0),
            "asset_id": asset_id,
            "provider_asset_id": asset.get("provider_asset_id") or asset_id,
            "path": asset.get("local_path", ""),
            "local_path": asset.get("local_path", ""),
            "provider": "local_library",
            "type": asset.get("type", media_type),
            "media_type": asset.get("type", media_type),
            "title": asset.get("title", ""),
            "description": asset.get("description", asset.get("caption", "")),
            "keywords": asset.get("keywords", []),
            "tags": asset.get("tags", []),
            "vision_tags": asset.get("vision_tags", []),
            "source_url": asset.get("source_url", ""),
            "source_page": asset.get("source_page", asset.get("source_url", "")),
            "source_page_url": asset.get("source_page_url") or asset.get("source_page") or asset.get("source_url", ""),
            "author": asset.get("author", ""),
            "license": asset.get("license", asset.get("license_note", "")),
            "provenance": asset.get("provenance", {}),
            "checksum_sha256": asset.get("checksum_sha256", ""),
            "technical_validation": asset.get("technical_validation", {}),
            "rights_status": rights_status,
            "allowed_for_render": allowed,
            "width": width,
            "height": height,
            "duration": float(asset.get("duration") or 0),
            "duration_sec": float(asset.get("duration_sec") or asset.get("duration") or 0),
            "relevance_score": float(match.get("score", 0)),
            "quality_score": _quality_score(width, height),
            "vertical_score": _vertical_score(width, height),
            "rights_score": 1.0 if allowed else 0.0,
            "duplicate_penalty": duplicate_penalty,
            "watermark_penalty": 0,
            "total_score": float(match.get("score", 0)) + _quality_score(width, height) + _vertical_score(width, height) - duplicate_penalty,
            "selected_by": "local_library",
        }
        ranked_item = _with_policy_decision(ranked_item)
        ranked.append(ranked_item)
    return ranked


def _provider_capabilities(providers_by_name: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Capabilities as the router and the query adapter need them.

    A provider that does not implement ``capabilities()`` (the older, simpler search
    protocol) contributes nothing rather than a guess, so routing falls back to the
    table in ``src.assets.query_adapter``.
    """
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


def _search_provider(
    provider: AssetProvider,
    query: str,
    scene: dict[str, Any],
    semantic_scene: dict[str, Any],
    *,
    project_id: str,
    limit: int,
) -> list[dict[str, Any]]:
    media_type = _scene_media_type(scene)
    if _supports_stock_contract(provider):
        request = AssetSearchRequest(
            query=query,
            media_type=media_type,
            target_aspect_ratio="9:16",
            orientation_preference="vertical",
            min_width=720,
            min_height=1280 if media_type in {"image", "video"} else 0,
            max_results=limit,
            scene_id=str(scene.get("scene_id") or ""),
            project_id=project_id,
            semantic_scene=semantic_scene,
            negative_terms=list(semantic_scene.get("must_not_include") or scene.get("negative_keywords") or []),
        )
        return [_candidate_to_rankable(candidate) for candidate in provider.search(request)]  # type: ignore[arg-type]
    try:
        return provider.search(query, scene, limit=limit)
    except TypeError:
        return provider.search(query, scene)


def _candidate_to_rankable(candidate: AssetCandidate) -> dict[str, Any]:
    apply_policy_to_candidate(candidate)
    data = candidate.to_manifest_dict()
    data["canonical_asset"] = candidate.to_dict()
    data["keywords"] = data.get("tags", [])
    data["quality_score"] = _quality_score(candidate.width, candidate.height)
    data["vertical_score"] = _vertical_score(candidate.width, candidate.height)
    data["rights_score"] = 1.0 if candidate.license.allowed_for_render and not candidate.license.review_required else 0.0
    data["allowed_for_render"] = candidate.license.allowed_for_render and not candidate.license.review_required
    data["review_required"] = candidate.license.review_required
    return data


def _with_policy_decision(candidate: dict[str, Any]) -> dict[str, Any]:
    stored_canonical = candidate.get("canonical_asset")
    canonical_data = stored_canonical if isinstance(stored_canonical, dict) and stored_canonical else candidate
    canonical = AssetCandidate.from_dict(canonical_data)
    if not canonical.provider_asset_id:
        canonical.provider_asset_id = str(candidate.get("provider_asset_id") or candidate.get("asset_id") or canonical.asset_id)
    if not canonical.source_page_url:
        canonical.source_page_url = str(candidate.get("source_page_url") or candidate.get("source_page") or candidate.get("source_url") or "")
    if not canonical.local_path:
        canonical.local_path = str(candidate.get("local_path") or candidate.get("path") or candidate.get("downloaded_path") or "")
    if isinstance(candidate.get("rights_declaration"), dict):
        canonical.rights_declaration = dict(candidate["rights_declaration"])
    decision = apply_policy_to_candidate(canonical)
    updated = {**candidate, **canonical.to_manifest_dict()}
    updated["canonical_asset"] = canonical.to_dict()
    updated["policy_decision"] = decision.to_dict()
    updated["allowed_for_render"] = decision.allowed_for_render
    updated["review_required"] = decision.review_required
    updated["rights_score"] = 1.0 if decision.allowed_for_render and not decision.review_required else 0.0
    return updated


def _ensure_selected_asset_downloaded(
    *,
    selected: dict[str, Any],
    ranked_candidates: list[dict[str, Any]],
    providers_by_name: dict[str, AssetProvider],
    project_root: Path | None,
    project_id: str,
    scene_id: str,
    media_index: dict[str, Any],
    max_attempts: int,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    ordered: list[dict[str, Any]] = []
    seen: set[str] = set()
    for candidate in [selected, *ranked_candidates]:
        asset_id = str(candidate.get("asset_id") or "")
        rights_rejection = "rights_not_allowed" in str(candidate.get("reject_reason") or "")
        if not asset_id or asset_id in seen or (candidate.get("rejected") and not rights_rejection):
            continue
        seen.add(asset_id)
        ordered.append(candidate)
    attempts: list[dict[str, Any]] = []
    for raw_candidate in ordered[: max(1, max_attempts)]:
        candidate = _with_policy_decision(raw_candidate)
        if candidate.get("review_required") or not candidate.get("allowed_for_render", True):
            policy_decision = candidate.get("policy_decision") if isinstance(candidate.get("policy_decision"), dict) else {}
            attempts.append(
                {
                    "asset_id": candidate.get("asset_id", ""),
                    "provider": candidate.get("provider", ""),
                    "scene_id": scene_id,
                    "search_query": candidate.get("search_query", ""),
                    "download_status": "blocked",
                    "reason": "license_review_required",
                    "policy_decision": policy_decision,
                    "error": f"Asset rights are not allowed for render: {policy_decision.get('reason', 'policy_blocked')}.",
                }
            )
            continue
        existing_path = candidate.get("path") or candidate.get("local_path") or candidate.get("downloaded_path")
        if existing_path:
            candidate["path"] = str(existing_path)
            candidate["local_path"] = str(existing_path)
            candidate["downloaded_path"] = str(existing_path)
            candidate.setdefault("download_status", "local")
            return _public_candidate(candidate), attempts
        if not project_root:
            return _public_candidate(candidate), attempts
        canonical_data = candidate.get("canonical_asset") if isinstance(candidate.get("canonical_asset"), dict) else candidate
        canonical = AssetCandidate.from_dict(canonical_data)
        canonical.project_id = canonical.project_id or project_id
        canonical.scene_id = canonical.scene_id or scene_id
        canonical.provenance.project_id = canonical.project_id
        canonical.provenance.scene_id = canonical.scene_id
        canonical.provenance.search_query = canonical.provenance.search_query or canonical.search_query
        provider = providers_by_name.get(canonical.provider)
        attempt = {
            "asset_id": canonical.asset_id,
            "provider": canonical.provider,
            "scene_id": scene_id,
            "search_query": canonical.search_query,
            "download_status": "started",
        }
        if not provider or not _supports_stock_contract(provider):
            attempt.update({"download_status": "skipped", "reason": "provider_has_no_download_contract"})
            attempts.append(attempt)
            continue
        try:
            license_data = provider.resolve_license(canonical)  # type: ignore[attr-defined]
            canonical.license = license_data
            if license_data.review_required or not license_data.allowed_for_render:
                raise LicenseReviewRequired("license review required", provider=canonical.provider, query=canonical.search_query)
            downloaded = provider.download(  # type: ignore[attr-defined]
                canonical,
                project_root / "assets" / "downloaded",
                DownloadContext(project_id=project_id, scene_id=scene_id, search_query=canonical.search_query),
            )
            manifest = downloaded.to_manifest_dict()
            manifest.update(
                {
                    "selected_by": candidate.get("selected_by", "provider"),
                    "scene_match_score": candidate.get("scene_match_score", candidate.get("final_score", 0)),
                    "final_score": candidate.get("final_score", candidate.get("total_score", 0)),
                    "download_status": "downloaded",
                }
            )
            register_asset(media_index, manifest)
            attempt.update(
                {
                    "download_status": "downloaded",
                    "local_path": manifest.get("path", ""),
                    "checksum_sha256": manifest.get("checksum_sha256", ""),
                    "technical_validation": manifest.get("technical_validation", {}),
                }
            )
            attempts.append(attempt)
            return _public_candidate(manifest), attempts
        except LicenseReviewRequired as exc:
            attempt.update({"download_status": "blocked", "reason": exc.code, "error": str(exc)})
            attempts.append(attempt)
            continue
        except ProviderError as exc:
            attempt.update({"download_status": "failed", "reason": exc.code, "error": str(exc), "retryable": exc.retryable})
            attempts.append(attempt)
            continue
    return None, attempts


def _supports_stock_contract(provider: Any) -> bool:
    return all(hasattr(provider, name) for name in ("capabilities", "resolve_license", "download", "health_check"))


def _scene_media_type(scene: dict[str, Any]) -> str:
    return "image" if scene.get("visual_type") in {"image", "animated_image"} else "video"


def _public_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    public = {key: value for key, value in candidate.items() if not key.startswith("_")}
    return public


def _rank_provider_results(results: list[dict[str, Any]], scene: dict[str, Any], query: str = "", fallback_level: int = 1) -> list[dict[str, Any]]:
    ranked = []
    for raw in results:
        rights_status = raw.get("rights_status") or RIGHTS_REFERENCE_ONLY
        allowed = rights_status in ALLOWED_RENDER_RIGHTS
        width = int(raw.get("width") or 0)
        height = int(raw.get("height") or 0)
        ranked_item = {
            "schema_version": int(raw.get("schema_version") or ASSET_SCHEMA_VERSION),
            "asset_id": raw.get("asset_id") or raw.get("id") or _stable_asset_id(raw),
            "provider": raw.get("provider", ""),
            "provider_asset_id": raw.get("provider_asset_id", ""),
            "type": raw.get("type") or raw.get("media_type") or scene.get("visual_type", ""),
            "media_type": raw.get("media_type") or raw.get("type") or scene.get("visual_type", ""),
            "title": raw.get("title", ""),
            "description": raw.get("description", ""),
            "keywords": raw.get("keywords", []),
            "tags": raw.get("tags", []),
            "vision_tags": raw.get("vision_tags", []),
            "source_url": raw.get("source_url") or raw.get("source_page_url", ""),
            "source_page": raw.get("source_page") or raw.get("source_page_url", ""),
            "source_page_url": raw.get("source_page_url") or raw.get("source_page") or raw.get("source_url", ""),
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
            "duration_sec": float(raw.get("duration_sec") or raw.get("duration") or 0),
            "relevance_score": float(raw.get("relevance_score", 0.5)),
            "quality_score": _quality_score(width, height),
            "vertical_score": _vertical_score(width, height),
            "rights_score": 1.0 if allowed else 0.0,
            "duplicate_penalty": 0,
            "watermark_penalty": float(raw.get("watermark_penalty", 0)),
            "total_score": float(raw.get("relevance_score", 0.5)) + _quality_score(width, height) + _vertical_score(width, height),
            "selected_by": "provider",
            "search_query": query or raw.get("search_query", scene.get("primary_query", "")),
            "fallback_level": fallback_level,
            "crop_suitability_score": raw.get("crop_suitability_score", raw.get("vertical_score", 0)),
        }
        ranked.append(_with_policy_decision(ranked_item))
    return ranked


def _query_not_allowed_for_scene(semantic_scene: Any, query: dict[str, str | int]) -> bool:
    level = int(query.get("fallback_level") or 1)
    if semantic_scene.visual_priority in {"transition", "environment"}:
        return False
    return level >= 4


def _rights_block_attempts(candidates: list[dict[str, Any]], scene_id: str) -> list[dict[str, Any]]:
    """Record, without downloading, that a candidate's rights blocked it.

    Same shape ``_ensure_selected_asset_downloaded`` writes, so the manifest reads the
    same whether the block was found while selecting or while fetching.
    """
    attempts: list[dict[str, Any]] = []
    for raw_candidate in candidates[:3]:
        candidate = _with_policy_decision(raw_candidate)
        if not (candidate.get("review_required") or not candidate.get("allowed_for_render", True)):
            continue
        policy_decision = candidate.get("policy_decision") if isinstance(candidate.get("policy_decision"), dict) else {}
        attempts.append(
            {
                "asset_id": candidate.get("asset_id", ""),
                "provider": candidate.get("provider", ""),
                "scene_id": scene_id,
                "search_query": candidate.get("search_query", ""),
                "download_status": "blocked",
                "reason": "license_review_required",
                "policy_decision": policy_decision,
                "error": f"Asset rights are not allowed for render: {policy_decision.get('reason', 'policy_blocked')}.",
            }
        )
    return attempts


def _missing_reason(dry_run: bool, candidates: list[dict[str, Any]], download_attempts: list[dict[str, Any]] | None = None) -> str:
    if dry_run:
        return "dry_run_does_not_download_assets"
    for attempt in download_attempts or []:
        if attempt.get("download_status") == "blocked" and attempt.get("reason"):
            return str(attempt["reason"])
    if download_attempts:
        return "download_or_validation_failed"
    if not candidates:
        return "no_allowed_asset_found"
    return "no_semantic_asset_above_threshold"


def _media_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in IMAGE_EXTENSIONS:
        return "image"
    if suffix in VIDEO_EXTENSIONS:
        return "video"
    return "unknown"


def _quality_score(width: int, height: int) -> float:
    pixels = width * height
    if pixels >= 1920 * 1080:
        return 10.0
    if pixels >= 1280 * 720:
        return 7.0
    if pixels:
        return 3.0
    return 1.0


def _vertical_score(width: int, height: int) -> float:
    if not width or not height:
        return 0.0
    ratio = width / height
    return max(0.0, 10.0 - abs(ratio - (9 / 16)) * 10)


def _stable_asset_id(asset: dict[str, Any]) -> str:
    raw = "|".join(str(asset.get(key, "")) for key in ("provider", "source_url", "local_path", "path", "id"))
    return "asset_" + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def _warnings(dry_run: bool, provider_errors: list[dict[str, str]], missing_scenes: list[dict[str, Any]]) -> list[str]:
    warnings: list[str] = []
    if dry_run:
        warnings.append("Dry run skipped downloads and paid providers.")
    if provider_errors:
        warnings.append(f"{len(provider_errors)} provider error(s) were recorded.")
    if missing_scenes:
        warnings.append(f"{len(missing_scenes)} scene(s) still need allowed assets.")
    return warnings


def _generated_fallback_asset(scene: dict[str, Any]) -> dict[str, Any]:
    return {
        "asset_id": f"generated_{scene.get('scene_id', 'scene')}",
        "path": "",
        "provider": "generated_layout",
        "type": scene.get("fallback_type") or "text_card",
        "source_url": "",
        "source_page": "",
        "author": "AI-YouTube",
        "license": "project_generated",
        "rights_status": "licensed",
        "allowed_for_render": True,
        "width": 1080,
        "height": 1920,
        "duration": float(scene.get("target_duration_sec") or 0),
        "relevance_score": 2.0,
        "quality_score": 5.0,
        "vertical_score": 10.0,
        "rights_score": 1.0,
        "duplicate_penalty": 0,
        "watermark_penalty": 0,
        "total_score": 8.0,
        "selected_by": "generated_fallback",
    }
