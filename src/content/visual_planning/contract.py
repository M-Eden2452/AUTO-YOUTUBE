"""The VisualPlanner contract.

Same shape as the script engine's provider contract
(``src.content.script_engine.contract``) and the asset provider contract
(``src.assets.provider_contract``): a Protocol plus a small error hierarchy, with
capability and cost declared up front so a caller can refuse a paid or networked
planner before calling it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from .models import VisualPlanRequest, VisualPlanResult


class VisualPlannerError(RuntimeError):
    """Base error for anything a visual planner can fail at."""

    code = "visual_planner_error"

    def __init__(self, message: str, *, planner: str = "", retryable: bool = False) -> None:
        super().__init__(message)
        self.planner = planner
        self.retryable = retryable

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "planner": self.planner,
            "retryable": self.retryable,
            "message": str(self),
        }


class VisualPlannerUnavailableError(VisualPlannerError):
    """The planner exists but cannot run here (not configured, not approved)."""

    code = "planner_unavailable"


class VisualPlannerInputError(VisualPlannerError):
    """The request cannot produce a plan (no script, no scenes)."""

    code = "invalid_input"


@dataclass
class VisualPlannerCapabilities:
    planner_id: str
    display_name: str
    description: str = ""
    requires_network: bool = False
    requires_paid_api: bool = False
    deterministic: bool = True
    # Language the intents come out in. "source" = whatever the script is written in.
    intent_language: str = "source"
    # Same vocabulary as src.content_creation.capabilities / production_catalog.
    implementation_status: str = "targeted_tested"

    def to_dict(self) -> dict[str, Any]:
        return {
            "planner_id": self.planner_id,
            "display_name": self.display_name,
            "description": self.description,
            "requires_network": self.requires_network,
            "requires_paid_api": self.requires_paid_api,
            "deterministic": self.deterministic,
            "intent_language": self.intent_language,
            "implementation_status": self.implementation_status,
        }


@runtime_checkable
class VisualPlanner(Protocol):
    """Decides what to show. One implementation per way of deciding."""

    @property
    def capabilities(self) -> VisualPlannerCapabilities: ...

    def supports(self, request: VisualPlanRequest) -> bool:
        """True when this planner can work with the request's material."""
        ...

    def plan(self, request: VisualPlanRequest) -> VisualPlanResult:
        """Produce a plan or raise a VisualPlannerError."""
        ...


class BaseVisualPlanner:
    """Convenience base: capability plumbing, so planners only implement plan()."""

    capabilities_spec: VisualPlannerCapabilities

    @property
    def capabilities(self) -> VisualPlannerCapabilities:
        return self.capabilities_spec

    @property
    def planner_id(self) -> str:
        return self.capabilities_spec.planner_id

    def supports(self, request: VisualPlanRequest) -> bool:
        """Whether this planner handles this *kind* of material - not whether the
        material is usable. An empty script is an input problem, and ``plan()`` says
        so precisely; answering False here would report it as "planner unavailable",
        which is the wrong thing to go and fix."""
        return True

    def plan(self, request: VisualPlanRequest) -> VisualPlanResult:  # pragma: no cover - abstract
        raise NotImplementedError


__all__ = [
    "BaseVisualPlanner",
    "VisualPlanner",
    "VisualPlannerCapabilities",
    "VisualPlannerError",
    "VisualPlannerInputError",
    "VisualPlannerUnavailableError",
]
