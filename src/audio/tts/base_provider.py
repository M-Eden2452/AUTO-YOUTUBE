from __future__ import annotations

from abc import ABC, abstractmethod

from .models import TTSRequest, TTSResult, VoicePreflightPlan


class TTSProvider(ABC):
    name: str
    paid: bool = False

    @abstractmethod
    def synthesize(self, request: TTSRequest) -> TTSResult:
        raise NotImplementedError

    def preflight(self, request: TTSRequest) -> VoicePreflightPlan:
        return VoicePreflightPlan(
            provider=self.name,
            language=request.language,
            voice_id=request.voice_id,
            voice_name=request.voice_name,
            model_id=request.model_id,
            character_count=len(request.text),
            provider_available=True,
            voice_available=not request.voice_id,
            model_available=not request.model_id,
            output_path=request.output_path,
        )

