from __future__ import annotations

from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.assets.completion import ReuseLedger, SceneVisualAssembly
from src.assets.semantic_selection import select_best_candidate
from src.media_library import load_media_index

from .asset_manifest_builder import (
    build_assets_manifest as _build_assets_manifest,
    ensure_decision as _ensure_decision,
    generated_fallback_asset as _generated_fallback_asset,
    inspect_user_asset as _inspect_user_asset,
    media_type as _media_type,
    merge_selection_config as _merge_selection_config,
    missing_reason as _missing_reason,
    query_not_allowed_for_scene as _query_not_allowed_for_scene,
    rank_local_assets as _rank_local_assets,
    rank_user_assets as _rank_user_assets,
    warnings as _warnings,
)
from .asset_manifest_summaries import (
    DEFAULT_MIN_VIDEO_CLIPS,
    DEFAULT_MIN_VIDEO_DURATION_RATIO,
    IMAGE_EXTENSIONS,
    VIDEO_EXTENSIONS,
    apply_video_first_readiness as _apply_video_first_readiness,
    completion_summary as _completion_summary,
    refresh_manifest_summaries,
    slot_media_type as _slot_media_type,
    summarize_media_coverage,
    video_first_policy as _video_first_policy,
    visual_support_summary as _visual_support_summary,
)
from .asset_provider_adapters import (
    AssetProvider,
    candidate_to_rankable as _candidate_to_rankable,
    create_default_asset_providers as _create_default_asset_providers,
    ensure_selected_asset_downloaded as _ensure_selected_asset_downloaded,
    environment_enabled as _env_enabled,
    provider_capabilities as _provider_capabilities,
    public_candidate as _public_candidate,
    quality_score as _quality_score,
    rank_provider_results as _rank_provider_results,
    rights_block_attempts as _rights_block_attempts,
    scene_media_type as _scene_media_type,
    search_provider as _search_provider,
    stable_asset_id as _stable_asset_id,
    supports_stock_contract as _supports_stock_contract,
    vertical_score as _vertical_score,
    with_policy_decision as _with_policy_decision,
)
from .asset_scene_completion import (
    complete_scene_assembly,
    emergency_backdrop,
    has_local_file as _has_local_file,
    targeted_slot_search,
)


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
    completion_mode: str = "",
    reuse_ledger: ReuseLedger | None = None,
    allow_infographic_fallback: bool = True,
    allow_emergency_backdrop: bool = True,
    prefer_video: bool = False,
    minimum_video_clips: int = DEFAULT_MIN_VIDEO_CLIPS,
    minimum_video_duration_ratio: float = DEFAULT_MIN_VIDEO_DURATION_RATIO,
) -> dict[str, Any]:
    """Compatibility facade over the split asset-manifest builder."""

    return _build_assets_manifest(
        visual_plan=visual_plan,
        user_assets=user_assets,
        media_index=media_index,
        providers=providers,
        dry_run=dry_run,
        channel=channel,
        allow_generated_fallback=allow_generated_fallback,
        asset_selection=asset_selection,
        project_root=project_root,
        project_id=project_id,
        max_download_attempts=max_download_attempts,
        completion_mode=completion_mode,
        reuse_ledger=reuse_ledger,
        allow_infographic_fallback=allow_infographic_fallback,
        allow_emergency_backdrop=allow_emergency_backdrop,
        prefer_video=prefer_video,
        minimum_video_clips=minimum_video_clips,
        minimum_video_duration_ratio=minimum_video_duration_ratio,
    )


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
    completion_mode: str = "",
    reuse_ledger: ReuseLedger | None = None,
) -> dict[str, Any]:
    media_index = (
        {"version": 1, "items": []}
        if dry_run
        else load_media_index(
            media_index_path or "assets/library/metadata/media_index.json"
        )
    )
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
        completion_mode=completion_mode,
        reuse_ledger=reuse_ledger,
        allow_infographic_fallback=False,
        allow_emergency_backdrop=False,
        prefer_video=True,
    )


def _select_best_candidate(
    semantic_scene: Any,
    candidates: list[dict[str, Any]],
    *,
    prefer_video: bool,
    **selection_kwargs: Any,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    selected, ranked = select_best_candidate(
        semantic_scene,
        candidates,
        **selection_kwargs,
    )
    if not prefer_video:
        return selected, ranked
    preferred = next(
        (
            candidate
            for candidate in ranked
            if _slot_media_type(candidate) == "video"
            and not candidate.get("rejected", False)
        ),
        None,
    )
    return (preferred or selected), ranked


def create_default_asset_providers() -> list[AssetProvider]:
    return _create_default_asset_providers(load_environment=load_dotenv)


def _emergency_backdrop(
    scene: dict[str, Any],
    *,
    project_root: Path,
    project_id: str,
) -> dict[str, Any] | None:
    return emergency_backdrop(
        scene,
        project_root=project_root,
        project_id=project_id,
        ensure_decision=_ensure_decision,
    )


def _complete_scene_assembly(
    *,
    scene: dict[str, Any],
    semantic_scene: Any,
    candidates: list[dict[str, Any]],
    strict_selection: dict[str, Any] | None,
    scene_index: int,
    duration: float,
    reuse: ReuseLedger,
    providers_by_name: dict[str, AssetProvider],
    project_root: Path | None,
    project_id: str,
    media_index: dict[str, Any],
    dry_run: bool,
    project_pool: list[dict[str, Any]],
    source_class: str,
    routing_decision: dict[str, Any] | None = None,
    provider_capabilities: dict[str, dict[str, Any]] | None = None,
    scene_provider_attempts: list[dict[str, Any]] | None = None,
    allow_emergency_backdrop: bool = True,
    prefer_video: bool = False,
) -> tuple[dict[str, Any] | None, SceneVisualAssembly, list[dict[str, Any]]]:
    return complete_scene_assembly(
        scene=scene,
        semantic_scene=semantic_scene,
        candidates=candidates,
        strict_selection=strict_selection,
        scene_index=scene_index,
        duration=duration,
        reuse=reuse,
        providers_by_name=providers_by_name,
        project_root=project_root,
        project_id=project_id,
        media_index=media_index,
        dry_run=dry_run,
        project_pool=project_pool,
        source_class=source_class,
        download_selected=_ensure_selected_asset_downloaded,
        ensure_decision=_ensure_decision,
        rank_provider_results=_rank_provider_results,
        search_provider=_search_provider,
        routing_decision=routing_decision,
        provider_capabilities=provider_capabilities,
        scene_provider_attempts=scene_provider_attempts,
        allow_emergency_backdrop=allow_emergency_backdrop,
        prefer_video=prefer_video,
    )


def _targeted_slot_search(
    *,
    scene: dict[str, Any],
    semantic_scene: Any,
    slot_names: list[str],
    ordered_providers: list[AssetProvider],
    provider_capabilities: dict[str, dict[str, Any]],
    project_id: str,
    sent_queries: set[tuple[str, str]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    return targeted_slot_search(
        scene=scene,
        semantic_scene=semantic_scene,
        slot_names=slot_names,
        ordered_providers=ordered_providers,
        provider_capabilities=provider_capabilities,
        project_id=project_id,
        sent_queries=sent_queries,
        rank_provider_results=_rank_provider_results,
        search_provider=_search_provider,
    )
