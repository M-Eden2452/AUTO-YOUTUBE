"""Which providers exist and which one answers a given request."""

from __future__ import annotations

from typing import Callable

from .contract import ScriptProvider, ScriptProviderCapabilities, ScriptProviderUnavailableError
from .models import SOURCE_NARRATION_TEXT, SOURCE_USER_SCRIPT, ScriptRequest
from .providers.deterministic import DeterministicScriptProvider
from .providers.legacy_template import LegacyTemplateScriptProvider
from .providers.llm import LLMScriptProvider
from .providers.user_supplied import UserSuppliedScriptProvider

# Free, offline and reproducible - the only kind of provider that may be a default.
DEFAULT_PROVIDER_ID = "deterministic_local"

PROVIDER_FACTORIES: dict[str, Callable[[], ScriptProvider]] = {
    "deterministic_local": DeterministicScriptProvider,
    "user_supplied": UserSuppliedScriptProvider,
    "legacy_template": LegacyTemplateScriptProvider,
    "llm": LLMScriptProvider,
}

# A finished script or a finished narration is answered by the provider that keeps
# the user's words, unless the caller names another one explicitly.
SOURCE_KIND_DEFAULTS: dict[str, str] = {
    SOURCE_USER_SCRIPT: "user_supplied",
    SOURCE_NARRATION_TEXT: "user_supplied",
}


def list_provider_ids() -> list[str]:
    return list(PROVIDER_FACTORIES)


def list_capabilities() -> list[ScriptProviderCapabilities]:
    return [factory().capabilities for factory in PROVIDER_FACTORIES.values()]


def get_provider(provider_id: str) -> ScriptProvider:
    factory = PROVIDER_FACTORIES.get(provider_id)
    if factory is None:
        known = ", ".join(sorted(PROVIDER_FACTORIES))
        raise ScriptProviderUnavailableError(
            f"Неизвестный движок сценария {provider_id!r}. Доступны: {known}.", provider=provider_id
        )
    return factory()


def resolve_provider_id(request: ScriptRequest) -> str:
    """The provider that should answer ``request``.

    Priority: what the request explicitly asks for, then what its source kind
    implies, then the default.
    """
    if request.provider_id:
        return request.provider_id
    return SOURCE_KIND_DEFAULTS.get(request.source_kind, DEFAULT_PROVIDER_ID)


__all__ = [
    "DEFAULT_PROVIDER_ID",
    "PROVIDER_FACTORIES",
    "SOURCE_KIND_DEFAULTS",
    "get_provider",
    "list_capabilities",
    "list_provider_ids",
    "resolve_provider_id",
]
