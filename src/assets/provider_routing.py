"""Which providers a scene is asked, in what order.

This used to score every provider against one blob of scene text with English keyword
sets (``NASA_TERMS``, ``HISTORICAL_TERMS``, ...). On a Russian script none of them
matched, so every provider scored the same 10 and the order collapsed to registration
order plus a "+10 if video" bonus - identical for all eight scenes of the confirmed
run, regardless of what those scenes were about.

The decision now belongs to ``src.assets.scene_strategy``: the scene is classified into
a source class once, and the class carries the provider order. This module stays as the
entry point every existing caller already uses, and keeps returning the same keys.
"""

from __future__ import annotations

from typing import Any

from .scene_strategy import PROVIDER_PRIORITY, build_strategy

# Order used when a caller names no providers at all. Kept for callers that relied on
# it; the per-scene order comes from the strategy, not from here.
DEFAULT_PROVIDER_ORDER = [
    "local_library",
    "pexels",
    "pixabay",
    "wikimedia",
    "nasa_images",
    "internet_archive",
    "envato_manual",
]


def route_providers(
    scene: dict[str, Any],
    *,
    provider_names: list[str] | None = None,
    provider_enabled: dict[str, bool] | None = None,
    policy_eligible: dict[str, bool] | None = None,
    capabilities: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Route one scene. Returns the decision *and* the strategy it came from."""
    names = list(provider_names or DEFAULT_PROVIDER_ORDER)
    strategy = build_strategy(
        scene,
        available_providers=names,
        provider_enabled=provider_enabled,
        policy_eligible=policy_eligible,
        capabilities=capabilities,
    )
    ordered = list(strategy.provider_order)
    # ``fallback_order`` has always meant "everything, manual last". It is kept
    # separate from ``ordered_providers`` because a manual provider is not something
    # the pipeline may call on its own.
    manual = [name for name in ordered if name in _MANUAL_PROVIDERS]
    automatic = [name for name in ordered if name not in _MANUAL_PROVIDERS]
    return {
        "scene_id": strategy.scene_id,
        "media_type": strategy.media_type,
        "ordered_providers": automatic + manual,
        "reasons": {name: list(values) for name, values in strategy.reasons.items()},
        "skipped_providers": dict(strategy.skipped_providers),
        "fallback_order": automatic + manual,
        "source_class": strategy.source_class,
        "classification_reason": strategy.classification_reason,
        "classified_from": strategy.classified_from,
        "requires_provider_metadata": strategy.requires_provider_metadata,
        "allows_generic_stock": strategy.allows_generic_stock,
        "strategy": strategy.to_dict(),
    }


def provider_priority_matrix() -> dict[str, list[str]]:
    """The routing table, for documentation and diagnostics."""
    return {source_class: list(order) for source_class, order in PROVIDER_PRIORITY.items()}


_MANUAL_PROVIDERS = frozenset({"envato_manual"})

__all__ = ["DEFAULT_PROVIDER_ORDER", "provider_priority_matrix", "route_providers"]
