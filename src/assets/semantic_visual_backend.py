from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .semantic_visual_models import SemanticVisualRequest, SemanticVisualResult


@dataclass
class SemanticBackendCapabilities:
    backend: str
    model: str = ""
    backend_version: str = ""
    supports_images: bool = True
    supports_video_frames: bool = True
    supports_batch: bool = False
    maximum_frames: int = 5
    batch_limit: int = 1
    paid_backend: bool = False
    estimated_cost_per_call_usd: float = 0.0

    def to_dict(self) -> dict[str, object]:
        return {
            "backend": self.backend,
            "model": self.model,
            "backend_version": self.backend_version,
            "supports_images": self.supports_images,
            "supports_video_frames": self.supports_video_frames,
            "supports_batch": self.supports_batch,
            "maximum_frames": self.maximum_frames,
            "batch_limit": self.batch_limit,
            "paid_backend": self.paid_backend,
            "estimated_cost_per_call_usd": self.estimated_cost_per_call_usd,
        }


@dataclass
class SemanticBackendHealth:
    backend: str
    configured: bool
    status: str = "unknown"
    message: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "backend": self.backend,
            "configured": self.configured,
            "status": self.status,
            "message": self.message,
        }


class SemanticVisualBackend(Protocol):
    name: str

    def capabilities(self) -> SemanticBackendCapabilities:
        ...

    def analyse_candidate(self, request: SemanticVisualRequest) -> SemanticVisualResult:
        ...

    def health_check(self) -> SemanticBackendHealth:
        ...
