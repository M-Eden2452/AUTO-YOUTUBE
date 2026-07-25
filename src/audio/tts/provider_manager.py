from __future__ import annotations

from .base_provider import TTSProvider
from .models import TTSRequest, TTSResult, VoicePreflightPlan


class TTSProviderManager:
    def __init__(self) -> None:
        self._providers: dict[str, TTSProvider] = {}

    def register(self, provider: TTSProvider) -> None:
        self._providers[provider.name] = provider

    def names(self) -> list[str]:
        return sorted(self._providers)

    def get(self, name: str) -> TTSProvider:
        if name not in self._providers:
            raise KeyError(f"TTS provider is not registered: {name}")
        return self._providers[name]

    def preflight(self, request: TTSRequest) -> VoicePreflightPlan:
        return self.get(request.provider).preflight(request)

    def synthesize(self, request: TTSRequest, *, approved: bool = False) -> TTSResult:
        provider = self.get(request.provider)
        if provider.paid and not approved:
            raise PermissionError(f"Paid TTS provider '{provider.name}' requires explicit approval.")
        return provider.synthesize(request)

