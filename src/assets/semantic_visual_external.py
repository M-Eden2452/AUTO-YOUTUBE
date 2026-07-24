from __future__ import annotations

from typing import Any

from .semantic_visual_backend import SemanticBackendCapabilities, SemanticBackendHealth
from .semantic_visual_models import SemanticVisualRequest, SemanticVisualResult, fallback_semantic_result


class ExternalSemanticVisualBackend:
    """Disabled boundary for future paid Vision backends.

    This class intentionally performs no network calls. It exists so the rest of
    the pipeline can depend on a provider-neutral interface while paid backends
    remain gated behind explicit budget and allow flags.
    """

    name = "external"

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = dict(config or {})
        self.backend_name = str(self.config.get("backend") or "external")
        self.model = str(self.config.get("model") or "")
        self.backend_version = "external.semantic.disabled.v1"
        self.maximum_frames = int(self.config.get("maximum_frames_per_candidate") or 5)
        self.batch_limit = int(self.config.get("batch_limit") or 1)
        self.timeout_sec = float(self.config.get("timeout_sec") or 30.0)

    def capabilities(self) -> SemanticBackendCapabilities:
        return SemanticBackendCapabilities(
            backend=self.backend_name,
            model=self.model,
            backend_version=self.backend_version,
            supports_images=True,
            supports_video_frames=True,
            supports_batch=self.batch_limit > 1,
            maximum_frames=self.maximum_frames,
            batch_limit=self.batch_limit,
            paid_backend=True,
            estimated_cost_per_call_usd=float(self.config.get("estimated_cost_per_call_usd") or 0.0),
        )

    def health_check(self) -> SemanticBackendHealth:
        if not self.config.get("allow_paid_vision", False):
            return SemanticBackendHealth(backend=self.backend_name, configured=False, status="blocked", message="paid vision disabled")
        if float(self.config.get("maximum_budget_usd") or 0.0) <= 0.0:
            return SemanticBackendHealth(backend=self.backend_name, configured=False, status="blocked", message="zero budget")
        if not self.backend_name or not self.model:
            return SemanticBackendHealth(backend=self.backend_name, configured=False, status="configuration_error", message="backend/model not configured")
        return SemanticBackendHealth(backend=self.backend_name, configured=False, status="not_implemented", message="external backend adapter disabled")

    def analyse_candidate(self, request: SemanticVisualRequest) -> SemanticVisualResult:
        if not self.config.get("allow_paid_vision", False):
            return self._configuration_error(request, "paid_vision_disabled", "Paid Vision calls require allow_paid_vision=true.")
        if float(self.config.get("maximum_budget_usd") or 0.0) <= 0.0:
            return self._configuration_error(request, "budget_required", "Paid Vision calls require a positive maximum_budget_usd.")
        if not self.backend_name or self.backend_name in {"mock", "external"} or not self.model:
            return self._configuration_error(request, "backend_not_configured", "External semantic backend and model must be configured.")
        if len(request.sampled_frame_references) > self.maximum_frames:
            return self._configuration_error(request, "maximum_frames_exceeded", "Semantic request exceeds backend frame limit.")
        return self._configuration_error(request, "external_backend_not_implemented", "External semantic backend adapter is disabled in this foundation stage.")

    def _configuration_error(self, request: SemanticVisualRequest, code: str, message: str) -> SemanticVisualResult:
        return fallback_semantic_result(
            backend=self.backend_name,
            model=self.model,
            backend_version=self.backend_version,
            request_version=request.request_version,
            status="configuration_error",
            error_code=code,
            message=message,
        )
