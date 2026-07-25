from __future__ import annotations

import wave
from pathlib import Path
from typing import Any

import requests

from .base_provider import TTSProvider
from .env import load_elevenlabs_env
from .models import SOURCE_GENERATED, TTSRequest, TTSResult, VoicePreflightPlan


ELEVENLABS_API_BASE = "https://api.elevenlabs.io/v1"


class ElevenLabsProvider(TTSProvider):
    name = "elevenlabs"
    paid = True

    def __init__(self, api_key: str | None = None, http_client: Any | None = None) -> None:
        self.env = load_elevenlabs_env()
        self.api_key = (api_key if api_key is not None else self.env.api_key).strip()
        self.http = http_client or requests

    def synthesize(self, request: TTSRequest) -> TTSResult:
        if not request.output_path:
            raise ValueError("ElevenLabs synthesis requires output_path.")
        if not self.api_key:
            raise PermissionError("ELEVENLABS_API_KEY is not configured.")
        output_path = Path(request.output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        response = self.http.post(
            f"{ELEVENLABS_API_BASE}/text-to-speech/{request.voice_id}",
            headers={"xi-api-key": self.api_key, "Content-Type": "application/json"},
            params={"output_format": request.output_format},
            json={
                "text": request.text,
                "model_id": request.model_id,
                "voice_settings": request.settings,
            },
            timeout=60,
        )
        if response.status_code >= 400:
            raise PermissionError(f"ElevenLabs synthesis failed: HTTP {response.status_code}")
        output_path.write_bytes(response.content)
        duration = _probe_audio_duration(output_path)
        return TTSResult(
            provider=self.name,
            language=request.language,
            scene_id=request.scene_id,
            audio_path=str(output_path),
            duration_sec=duration,
            sample_rate=44100,
            channels=1,
            cache_hit=False,
            source_type=SOURCE_GENERATED,
        )

    def preflight(self, request: TTSRequest) -> VoicePreflightPlan:
        plan = VoicePreflightPlan(
            provider=self.name,
            language=request.language,
            voice_id=request.voice_id,
            voice_name=request.voice_name,
            model_id=request.model_id,
            character_count=len(request.text),
            api_key_present=bool(self.api_key),
            output_path=request.output_path,
            env_path=str(self.env.env_path),
            api_key_length=len(self.api_key),
            api_key_last4=self.api_key[-4:] if len(self.api_key) >= 4 else "",
            env_voice_id_present=bool(self.env.voice_id),
        )
        if not self.api_key:
            plan.errors.append("ELEVENLABS_API_KEY is not configured.")
            return plan
        headers = {"xi-api-key": self.api_key}
        try:
            subscription = self.http.get(f"{ELEVENLABS_API_BASE}/user/subscription", headers=headers, timeout=20)
            plan.http_statuses["subscription"] = int(subscription.status_code)
            if subscription.status_code < 400:
                data = subscription.json()
                plan.provider_available = True
                if "character_limit" in data and "character_count" in data:
                    plan.remaining_credits = int(data["character_limit"]) - int(data["character_count"])
            else:
                plan.errors.append(f"ElevenLabs subscription check failed: HTTP {subscription.status_code}")

            voices = self.http.get(f"{ELEVENLABS_API_BASE}/voices", headers=headers, timeout=20)
            plan.http_statuses["voices"] = int(voices.status_code)
            if voices.status_code < 400:
                data = voices.json()
                for voice in data.get("voices", []):
                    if voice.get("voice_id") == request.voice_id:
                        plan.voice_available = True
                        plan.voice_name = voice.get("name") or request.voice_name
                        break
                if request.voice_id and not plan.voice_available:
                    plan.errors.append("Голос с указанным Voice ID недоступен. Выберите голос из доступного списка или добавьте новый Voice ID.")
            else:
                plan.errors.append(f"ElevenLabs voices check failed: HTTP {voices.status_code}")

            models = self.http.get(f"{ELEVENLABS_API_BASE}/models", headers=headers, timeout=20)
            plan.http_statuses["models"] = int(models.status_code)
            if models.status_code < 400:
                data = models.json()
                models_list = data if isinstance(data, list) else data.get("models", [])
                plan.model_available = any(model.get("model_id") == request.model_id for model in models_list)
                if request.model_id and not plan.model_available:
                    plan.errors.append(f"ElevenLabs model is not available: {request.model_id}")
            else:
                plan.errors.append(f"ElevenLabs models check failed: HTTP {models.status_code}")
        except Exception as exc:
            plan.errors.append(f"ElevenLabs preflight failed: {exc}")
        return plan

    def list_voices(self) -> list[dict[str, Any]]:
        if not self.api_key:
            return []
        response = self.http.get(f"{ELEVENLABS_API_BASE}/voices", headers={"xi-api-key": self.api_key}, timeout=20)
        response.raise_for_status()
        return response.json().get("voices", [])

    def inspect_voice(self, voice_id: str) -> dict[str, Any] | None:
        for voice in self.list_voices():
            if voice.get("voice_id") == voice_id:
                return voice
        return None


def _probe_audio_duration(path: Path) -> float:
    if path.suffix.lower() == ".wav":
        with wave.open(str(path), "rb") as wav:
            rate = wav.getframerate()
            return wav.getnframes() / float(rate) if rate else 0.0
    try:
        from moviepy import AudioFileClip

        clip = AudioFileClip(str(path))
        duration = float(clip.duration or 0)
        clip.close()
        return duration
    except Exception:
        return 0.0
