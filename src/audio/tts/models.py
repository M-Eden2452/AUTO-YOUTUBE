from __future__ import annotations

import dataclasses
import hashlib
import json
from dataclasses import dataclass, field, replace
from typing import Any


SOURCE_GENERATED = "generated"
SOURCE_LOCAL_GENERATED = "local_generated"
SOURCE_USER_PROVIDED = "user_provided"
SOURCE_IMPORTED = "imported"


@dataclass(frozen=True)
class TTSRequest:
    job_id: str
    localization_id: str
    provider: str
    language: str
    text: str
    scene_id: str | None = None
    voice_id: str = ""
    voice_name: str = ""
    model_id: str = ""
    output_format: str = "wav"
    sample_rate: int = 48000
    settings: dict[str, Any] = field(default_factory=dict)
    audio_file: str | None = None
    scene_audio_files: list[str] = field(default_factory=list)
    output_path: str | None = None

    def with_updates(self, **changes: Any) -> "TTSRequest":
        return replace(self, **changes)


@dataclass
class TTSResult:
    provider: str
    language: str
    scene_id: str | None
    audio_path: str
    duration_sec: float
    sample_rate: int
    channels: int
    cache_hit: bool = False
    source_type: str = SOURCE_GENERATED


@dataclass
class VoicePreflightPlan:
    provider: str
    language: str
    voice_id: str
    voice_name: str
    model_id: str
    character_count: int
    estimated_cost: str = "unknown"
    remaining_credits: int | None = None
    api_key_present: bool = False
    provider_available: bool = False
    voice_available: bool = False
    model_available: bool = False
    output_path: str | None = None
    env_path: str | None = None
    api_key_length: int = 0
    api_key_last4: str = ""
    env_voice_id_present: bool = False
    http_statuses: dict[str, int] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class VoiceProfile:
    profile_id: str
    display_name: str
    provider: str
    voice_id: str
    model_id: str
    language: str
    enabled: bool = True
    settings: dict[str, Any] = field(default_factory=dict)


def compute_tts_cache_key(request: TTSRequest, *, post_processing_version: str = "") -> str:
    payload = {
        "provider": request.provider,
        "voice_id": request.voice_id,
        "model_id": request.model_id,
        "language": request.language,
        "text": request.text,
        "settings": _stable(request.settings),
        "output_format": request.output_format,
        "sample_rate": request.sample_rate,
    }
    if post_processing_version:
        payload["post_processing_version"] = post_processing_version
    return _hash_json(payload)


def compute_text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compute_settings_hash(settings: dict[str, Any]) -> str:
    return _hash_json(_stable(settings))


def _hash_json(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _stable(value: Any) -> Any:
    if dataclasses.is_dataclass(value):
        return dataclasses.asdict(value)
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value
