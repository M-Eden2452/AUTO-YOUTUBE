"""The ScriptProvider contract.

Mirrors the shape the repository already uses for asset providers
(``src.assets.provider_contract``): a Protocol plus a small error hierarchy, so
capability and cost are declared up front and a caller can refuse a paid or
networked provider *before* calling it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from .models import ScriptRequest, ScriptResult


class ScriptProviderError(RuntimeError):
    """Base error for anything a script provider can fail at."""

    code = "script_provider_error"

    def __init__(
        self,
        message: str,
        *,
        provider: str = "",
        retryable: bool = False,
        code: str = "",
    ) -> None:
        super().__init__(message)
        self.provider = provider
        self.retryable = retryable
        if code:
            self.code = code

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "provider": self.provider,
            "retryable": self.retryable,
            "message": str(self),
        }


class ScriptProviderUnavailableError(ScriptProviderError):
    """The provider exists but cannot run here (not configured, not approved, no network)."""

    code = "provider_unavailable"


class ScriptProviderInputError(ScriptProviderError):
    """The request cannot produce a script (empty source, unsupported source kind)."""

    code = "invalid_input"


class ScriptProviderResponseError(ScriptProviderError):
    """The provider answered, but the answer is not a usable script."""

    code = "invalid_response"


@dataclass
class ScriptProviderCapabilities:
    provider_id: str
    display_name: str
    description: str = ""
    supported_source_kinds: tuple[str, ...] = ()
    requires_network: bool = False
    requires_paid_api: bool = False
    deterministic: bool = True
    # Same vocabulary as src.content_creation.capabilities / production_catalog.
    implementation_status: str = "targeted_tested"

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "display_name": self.display_name,
            "description": self.description,
            "supported_source_kinds": list(self.supported_source_kinds),
            "requires_network": self.requires_network,
            "requires_paid_api": self.requires_paid_api,
            "deterministic": self.deterministic,
            "implementation_status": self.implementation_status,
        }


@runtime_checkable
class ScriptProvider(Protocol):
    """Writes a script. One implementation per way of writing one."""

    @property
    def capabilities(self) -> ScriptProviderCapabilities: ...

    def supports(self, request: ScriptRequest) -> bool:
        """True when this provider can honour the request's source kind and inputs."""
        ...

    def generate(self, request: ScriptRequest) -> ScriptResult:
        """Produce a script or raise a ScriptProviderError."""
        ...


class BaseScriptProvider:
    """Convenience base: capability plumbing, so providers only implement generate()."""

    capabilities_spec: ScriptProviderCapabilities

    @property
    def capabilities(self) -> ScriptProviderCapabilities:
        return self.capabilities_spec

    @property
    def provider_id(self) -> str:
        return self.capabilities_spec.provider_id

    def supports(self, request: ScriptRequest) -> bool:
        supported = self.capabilities_spec.supported_source_kinds
        return not supported or request.source_kind in supported

    def generate(self, request: ScriptRequest) -> ScriptResult:  # pragma: no cover - abstract
        raise NotImplementedError


__all__ = [
    "BaseScriptProvider",
    "ScriptProvider",
    "ScriptProviderCapabilities",
    "ScriptProviderError",
    "ScriptProviderInputError",
    "ScriptProviderResponseError",
    "ScriptProviderUnavailableError",
]
