from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from src.assets.completion import (
    MODE_DRAFT_COMPLETE,
    SLOT_PRIMARY,
    ReuseLedger,
    SceneVisualAssembly,
    blocking_reasons,
    build_scene_assembly,
    evaluate_usability,
    unfilled_semantic_slots,
)
from src.assets.generated_infographic import (
    backdrop_spec_for_scene,
    build_generated_asset,
)
from src.assets.provider_contract import ProviderError
from src.assets.query_adapter import STATUS_OK, build_slot_queries
from src.assets.semantic_selection import rank_candidates
from src.assets.semantic_selection.decision import carry_decision
from src.assets.semantic_selection.media_policy import (
    candidate_media_kind,
    media_kind_restriction,
)

from .asset_provider_adapters import (
    STOP_REASON_BUDGET_EXHAUSTED,
    SceneRequestBudget,
)


DownloadSelected = Callable[..., tuple[dict[str, Any] | None, list[dict[str, Any]]]]
EnsureDecision = Callable[..., dict[str, Any] | None]
RankProviderResults = Callable[..., list[dict[str, Any]]]
SearchProvider = Callable[..., list[dict[str, Any]]]


def has_local_file(asset: dict[str, Any] | None) -> bool:
    if not isinstance(asset, dict):
        return False
    for key in ("path", "local_path", "downloaded_path"):
        value = asset.get(key)
        if value:
            path = Path(str(value))
            try:
                if path.is_file() and path.stat().st_size > 0:
                    return True
            except OSError:
                continue
    return False


def emergency_backdrop(
    scene: dict[str, Any],
    *,
    project_root: Path,
    project_id: str,
    ensure_decision: EnsureDecision,
) -> dict[str, Any] | None:
    """Create the final project-owned neutral-card fallback."""

    scene_id = str(scene.get("scene_id") or "")
    label = str(scene.get("on_screen_text") or "").strip()
    spec = backdrop_spec_for_scene(scene, label=label)
    try:
        asset = build_generated_asset(
            spec,
            project_root=project_root,
            project_id=project_id or project_root.name,
            scene_id=scene_id,
            variant="backdrop",
        )
    except Exception:
        return None
    asset["selected_by"] = "emergency_neutral_backdrop"
    return ensure_decision(asset, scene_id=scene_id, source_class="")


def complete_scene_assembly(
    *,
    scene: dict[str, Any],
    semantic_scene: Any,
    candidates: list[dict[str, Any]],
    strict_selection: dict[str, Any] | None,
    scene_index: int,
    duration: float,
    reuse: ReuseLedger,
    providers_by_name: dict[str, Any],
    project_root: Path | None,
    project_id: str,
    media_index: dict[str, Any],
    dry_run: bool,
    project_pool: list[dict[str, Any]],
    source_class: str,
    download_selected: DownloadSelected,
    ensure_decision: EnsureDecision,
    rank_provider_results: RankProviderResults,
    search_provider: SearchProvider,
    routing_decision: dict[str, Any] | None = None,
    provider_capabilities: dict[str, dict[str, Any]] | None = None,
    scene_provider_attempts: list[dict[str, Any]] | None = None,
    original_selected_asset_id: str = "",
    allow_emergency_backdrop: bool = True,
    request_budget: SceneRequestBudget | None = None,
) -> tuple[dict[str, Any] | None, SceneVisualAssembly, list[dict[str, Any]]]:
    """Assemble ``draft_complete`` around the canonical primary selection."""

    scene_id = str(scene.get("scene_id") or "")
    attempts: list[dict[str, Any]] = []
    pool_candidates: list[dict[str, Any]] = []
    known_ids = {str(item.get("asset_id") or "") for item in candidates}
    reusable = [
        dict(item)
        for item in project_pool
        if str(item.get("asset_id") or "") not in known_ids
    ]
    if reusable:
        pool_candidates = rank_candidates(
            semantic_scene,
            reusable,
            used_asset_ids=set(),
            required_duration_sec=duration,
            require_provider_metadata=False,
            source_class=source_class,
        )

    emergency_factory = None
    if allow_emergency_backdrop and project_root is not None and not dry_run:
        emergency_factory = lambda target: emergency_backdrop(  # noqa: E731
            target,
            project_root=project_root,
            project_id=project_id,
            ensure_decision=ensure_decision,
        )

    ordered_providers = [
        providers_by_name[name]
        for name in (
            (routing_decision or {}).get("ordered_providers")
            or list(providers_by_name)
        )
        if name in providers_by_name
    ]
    sent_queries = {
        (
            str(item.get("provider") or ""),
            str(item.get("query") or "").strip().lower(),
        )
        for item in (scene_provider_attempts or [])
    }
    targeted_search_done = False
    triggered_slots: list[str] = []

    excluded: set[str] = set()
    restriction = media_kind_restriction(scene.get("allowed_media_kinds"))
    assembly = SceneVisualAssembly(scene_id=scene_id, scene_duration_sec=duration)
    for _attempt in range(5):
        selected_id = str((strict_selection or {}).get("asset_id") or "")
        active_primary = (
            strict_selection
            if strict_selection is not None and selected_id not in excluded
            else None
        )
        pool = [
            candidate
            for candidate in (*candidates, *pool_candidates)
            if str(candidate.get("asset_id") or "") not in excluded
            and (
                not restriction
                or candidate_media_kind(candidate) == restriction
            )
        ]
        if active_primary is not None:
            pool = [
                active_primary,
                *[
                    candidate
                    for candidate in pool
                    if str(candidate.get("asset_id") or "") != selected_id
                ],
            ]
        trial = reuse.copy()
        assembly = build_scene_assembly(
            scene=scene,
            ranked_candidates=pool,
            scene_duration_sec=duration,
            mode=MODE_DRAFT_COMPLETE,
            scene_index=scene_index,
            reuse=trial,
            emergency_asset_factory=emergency_factory,
            requested_slot_count=len(
                [part for part in (scene.get("visual_parts") or []) if part]
            ),
            authoritative_primary=active_primary,
        )
        if not assembly.slots:
            reuse.adopt(trial)
            return None, assembly, attempts
        failed_asset_id = ""
        for slot in assembly.slots:
            asset = slot.selected_asset
            if dry_run or project_root is None:
                continue
            asset_id = str(asset.get("asset_id") or "")
            fallback_from_asset_id = (
                original_selected_asset_id
                if slot.purpose == SLOT_PRIMARY
                and original_selected_asset_id
                and asset_id != original_selected_asset_id
                else ""
            )
            if has_local_file(asset) and not fallback_from_asset_id:
                downloaded = asset
            else:
                download_candidate = dict(asset)
                download_candidate["rejected"] = False
                downloaded, slot_attempts = download_selected(
                    selected=download_candidate,
                    ranked_candidates=[],
                    providers_by_name=providers_by_name,
                    project_root=project_root,
                    project_id=project_id,
                    scene_id=scene_id,
                    media_index=media_index,
                    max_attempts=1,
                    fallback_from_asset_id=fallback_from_asset_id,
                )
                attempts.extend(slot_attempts)
                if downloaded:
                    carry_decision(asset, downloaded)
            if not downloaded:
                failed_asset_id = str(asset.get("asset_id") or "")
                break
            reasons = blocking_reasons(downloaded, require_local_file=True)
            usability = evaluate_usability(
                downloaded,
                mode=MODE_DRAFT_COMPLETE,
                quality_tier=slot.quality_tier,
                require_local_file=True,
            )
            if reasons or not usability.usable_in_draft:
                attempts.append(
                    {
                        "scene_id": scene_id,
                        "asset_id": str(downloaded.get("asset_id") or ""),
                        "status": "rejected_after_download",
                        "reason": ",".join(reasons or usability.block_reasons),
                    }
                )
                failed_asset_id = str(
                    downloaded.get("asset_id") or asset.get("asset_id") or ""
                )
                break
            slot.selected_asset = downloaded
            slot.provenance = dict(downloaded.get("provenance") or {})
            slot.rights = (
                dict(downloaded.get("license") or {})
                if isinstance(downloaded.get("license"), dict)
                else {}
            )
            slot.usability = usability
        if not failed_asset_id:
            if (
                not targeted_search_done
                and not dry_run
                and project_root is not None
                and ordered_providers
            ):
                targeted_search_done = True
                missing = unfilled_semantic_slots(assembly)
                if missing:
                    found, targeted_attempts = targeted_slot_search(
                        scene=scene,
                        semantic_scene=semantic_scene,
                        slot_names=missing,
                        ordered_providers=ordered_providers,
                        provider_capabilities=provider_capabilities or {},
                        project_id=project_id,
                        sent_queries=sent_queries,
                        rank_provider_results=rank_provider_results,
                        search_provider=search_provider,
                        request_budget=request_budget,
                    )
                    attempts.extend(targeted_attempts)
                    if found:
                        found = rank_candidates(
                            semantic_scene,
                            found,
                            used_asset_ids=set(),
                            required_duration_sec=duration,
                            require_provider_metadata=False,
                            source_class=source_class,
                        )
                        triggered_slots = missing
                        candidates = [*candidates, *found]
                        continue
            if triggered_slots:
                assembly.ladder_trace.append(
                    "Q2.3:targeted_slot_search:" + ",".join(triggered_slots)
                )
            reuse.adopt(trial)
            primary = assembly.primary_asset
            return (primary or strict_selection or None), assembly, attempts
        excluded.add(failed_asset_id)
        assembly.ladder_trace.append(f"download_failed:{failed_asset_id}")
    return None, assembly, attempts


def targeted_slot_search(
    *,
    scene: dict[str, Any],
    semantic_scene: Any,
    slot_names: list[str],
    ordered_providers: list[Any],
    provider_capabilities: dict[str, dict[str, Any]],
    project_id: str,
    sent_queries: set[tuple[str, str]],
    rank_provider_results: RankProviderResults,
    search_provider: SearchProvider,
    request_budget: SceneRequestBudget | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Run one bounded targeted search for still-unfilled semantic slots.

    Bounded twice over, and the two bounds answer different questions. Rule 7
    caps this to one pass per scene, which stops it becoming a retry loop.
    ``request_budget`` is the scene's shared ceiling on provider requests
    (VA-NEW-12): the general search has already spent from it, and this pass
    keeps drawing down the same count instead of opening a second allowance, so
    the ladder cannot walk past a ceiling the general search stopped at.
    """

    new_candidates: list[dict[str, Any]] = []
    attempts: list[dict[str, Any]] = []
    provider_names = [provider.name for provider in ordered_providers]
    for slot_name in slot_names:
        plan = build_slot_queries(
            scene,
            slot_name,
            providers=provider_names,
            capabilities=provider_capabilities,
        )
        for item in plan.queries:
            if item.status != STATUS_OK:
                continue
            key = (item.provider, item.query.strip().lower())
            if key in sent_queries:
                continue
            if request_budget is not None and request_budget.exhausted:
                attempts.append(
                    {
                        "scene_id": str(scene.get("scene_id") or ""),
                        "provider": item.provider,
                        "query": "",
                        "status": "skipped",
                        "reason": STOP_REASON_BUDGET_EXHAUSTED,
                        "message": (
                            "Целевой поиск по слотам не отправлен: достигнут "
                            "предел запросов к провайдерам для этой сцены "
                            f"({request_budget.limit})."
                        ),
                        "request_budget": request_budget.to_dict(),
                    }
                )
                return new_candidates, attempts
            sent_queries.add(key)
            provider = next(
                (
                    candidate
                    for candidate in ordered_providers
                    if candidate.name == item.provider
                ),
                None,
            )
            if provider is None:
                continue
            attempt = {
                "scene_id": str(scene.get("scene_id") or ""),
                "provider": provider.name,
                "query": item.query,
                "query_language": item.language,
                "query_source": item.source,
                "kind": item.kind,
                "status": "started",
            }
            media_attempts: list[dict[str, Any]] = []
            try:
                provider_results = search_provider(
                    provider,
                    item.query,
                    scene,
                    semantic_scene.to_dict(),
                    project_id=project_id,
                    limit=5,
                    media_attempts=media_attempts,
                    budget=request_budget,
                )
                new_candidates.extend(
                    rank_provider_results(
                        provider_results,
                        scene,
                        item.query,
                        fallback_level=10,
                    )
                )
                attempt.update(
                    {"status": "completed", "result_count": len(provider_results)}
                )
            except ProviderError as exc:
                error = exc.to_dict()
                error.update(
                    {"scene_id": scene.get("scene_id", ""), "query": item.query}
                )
                attempt.update({"status": "failed", "error": error})
            except Exception as exc:
                attempt.update(
                    {
                        "status": "failed",
                        "error": {
                            "code": "provider_unexpected_error",
                            "provider": provider.name,
                            "scene_id": scene.get("scene_id", ""),
                            "query": item.query,
                            "message": str(exc),
                        },
                    }
                )
            if media_attempts:
                attempt["media_attempts"] = media_attempts
            attempts.append(attempt)
    return new_candidates, attempts
