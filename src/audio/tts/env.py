from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from src.utils import PROJECT_ROOT


@dataclass(frozen=True)
class ElevenLabsEnv:
    env_path: Path
    api_key: str
    voice_id: str

    @property
    def api_key_present(self) -> bool:
        return bool(self.api_key)

    @property
    def api_key_length(self) -> int:
        return len(self.api_key)

    @property
    def api_key_last4(self) -> str:
        return self.api_key[-4:] if len(self.api_key) >= 4 else ""

    @property
    def voice_id_present(self) -> bool:
        return bool(self.voice_id)


def load_elevenlabs_env() -> ElevenLabsEnv:
    env_path = PROJECT_ROOT / ".env"
    load_dotenv(env_path, override=True)
    api_key = (os.getenv("ELEVENLABS_API_KEY") or "").strip()
    voice_id = (os.getenv("ELEVENLABS_VOICE_ID") or "").strip()
    os.environ["ELEVENLABS_API_KEY"] = api_key
    if voice_id:
        os.environ["ELEVENLABS_VOICE_ID"] = voice_id
    return ElevenLabsEnv(env_path=env_path, api_key=api_key, voice_id=voice_id)
