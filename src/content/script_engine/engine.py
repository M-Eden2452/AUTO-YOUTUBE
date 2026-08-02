"""One entry point: request in, validated script out."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from .contract import ScriptProvider, ScriptProviderError, ScriptProviderUnavailableError
from .legacy_format import to_legacy_script
from .models import ScriptRequest, ScriptResult, ScriptValidationResult
from .registry import get_provider, resolve_provider_id
from .validation import validate_script


@dataclass
class ScriptGeneration:
    """A script together with the verdict on it and how it was produced."""

    result: ScriptResult
    validation: ScriptValidationResult
    provider_id: str
    requested_provider_id: str = ""

    @property
    def used_fallback(self) -> bool:
        return bool(self.requested_provider_id) and self.requested_provider_id != self.provider_id

    def to_legacy_script(self, *, target_duration_sec: float | int | None = None) -> dict[str, Any]:
        return to_legacy_script(self.result, target_duration_sec=target_duration_sec)

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "requested_provider_id": self.requested_provider_id,
            "used_fallback": self.used_fallback,
            "script": self.result.to_dict(),
            "validation": self.validation.to_dict(),
        }


def generate_script(
    request: ScriptRequest,
    *,
    provider: ScriptProvider | None = None,
    fallback_provider_id: str = "",
) -> ScriptGeneration:
    """Run the provider the request resolves to and validate what comes back.

    Validation never raises: an invalid script is returned *with* its problems, so
    the caller (CLI, wizard, pipeline) decides whether to stop. Provider failures
    do raise - a provider that cannot produce a script has nothing to report on.

    ``fallback_provider_id`` is opt-in and empty by default: silently substituting
    a different writer would hide a real failure. It exists for the one case that
    needs it - a remote provider failing for reasons the user cannot fix (no model
    wired, not approved, unusable answer) must not strand a pipeline run mid-way.
    The substitution is never silent: it is recorded in ``used_fallback``, in the
    script's ``warnings`` and in its ``metadata``.
    """
    if provider is not None:
        # An injected provider *is* the requested one: taking the id from the
        # request instead would misreport which engine ran and could make the
        # fallback look identical to the provider that just failed.
        engine = provider
        requested_id = getattr(provider.capabilities, "provider_id", "") or resolve_provider_id(request)
    else:
        requested_id = resolve_provider_id(request)
        engine = get_provider(requested_id)
    try:
        if not engine.supports(request):
            raise ScriptProviderUnavailableError(
                f"Движок {requested_id!r} не поддерживает источник {request.source_kind!r}.",
                provider=requested_id,
            )
        result = engine.generate(request)
    except ScriptProviderError as error:
        if not fallback_provider_id or fallback_provider_id == requested_id:
            raise
        result = _generate_with_fallback(request, fallback_provider_id, error)

    validation = validate_script(
        result,
        constraints=request.constraints,
        expected_language=request.language,
        allow_legacy_fallback=bool(
            request.provider_options.get("allow_legacy_fallback", False)
        ),
    )
    return ScriptGeneration(
        result=result,
        validation=validation,
        provider_id=result.provider_id or requested_id,
        requested_provider_id=requested_id,
    )


def _generate_with_fallback(
    request: ScriptRequest, fallback_provider_id: str, error: ScriptProviderError
) -> ScriptResult:
    """Second attempt with a local provider, carrying the reason for it."""
    fallback_request = replace(request, provider_id=fallback_provider_id)
    result = get_provider(fallback_provider_id).generate(fallback_request)
    result.warnings.append(
        f"provider_fallback: движок {error.provider or 'запрошенный'!r} не отработал "
        f"({error.code}), сценарий написан движком {fallback_provider_id!r}"
    )
    result.metadata.update(
        {
            "requested_provider": error.provider or request.provider_id,
            "fallback_provider": fallback_provider_id,
            "fallback_reason": error.code,
            "fallback_message": str(error),
        }
    )
    return result


__all__ = ["ScriptGeneration", "ScriptProviderError", "generate_script"]
