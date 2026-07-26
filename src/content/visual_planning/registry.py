"""Which planners exist and which one answers a given request."""

from __future__ import annotations

from typing import Callable

from .contract import VisualPlanner, VisualPlannerCapabilities, VisualPlannerUnavailableError
from .models import VisualPlanRequest
from .planners.deterministic import DeterministicVisualPlanner

# Free, offline and reproducible - the only kind of planner that may be a default.
DEFAULT_PLANNER_ID = "deterministic_local"

PLANNER_FACTORIES: dict[str, Callable[[], VisualPlanner]] = {
    "deterministic_local": DeterministicVisualPlanner,
}


def list_planner_ids() -> list[str]:
    return list(PLANNER_FACTORIES)


def list_capabilities() -> list[VisualPlannerCapabilities]:
    return [factory().capabilities for factory in PLANNER_FACTORIES.values()]


def get_planner(planner_id: str) -> VisualPlanner:
    factory = PLANNER_FACTORIES.get(planner_id)
    if factory is None:
        known = ", ".join(sorted(PLANNER_FACTORIES))
        raise VisualPlannerUnavailableError(
            f"Неизвестный планировщик {planner_id!r}. Доступны: {known}.", planner=planner_id
        )
    return factory()


def resolve_planner_id(request: VisualPlanRequest) -> str:
    return request.planner_id or DEFAULT_PLANNER_ID


__all__ = [
    "DEFAULT_PLANNER_ID",
    "PLANNER_FACTORIES",
    "get_planner",
    "list_capabilities",
    "list_planner_ids",
    "resolve_planner_id",
]
