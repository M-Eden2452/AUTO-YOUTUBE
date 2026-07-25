from __future__ import annotations

import io
import wave
from dataclasses import dataclass
from pathlib import Path


@dataclass
class PausePolicy:
    after_sentence_sec: float = 0.15
    between_scenes_sec: float = 0.4
    between_chapters_sec: float = 1.0
    min_pause_sec: float = 0.0
    max_pause_sec: float = 2.0

    def clamp(self, value: float) -> float:
        return max(self.min_pause_sec, min(self.max_pause_sec, value))


FORMAT_DEFAULTS: dict[str, PausePolicy] = {
    "vertical_short": PausePolicy(
        after_sentence_sec=0.12, between_scenes_sec=0.35, between_chapters_sec=0.6, min_pause_sec=0.05, max_pause_sec=1.0
    ),
    "longform": PausePolicy(
        after_sentence_sec=0.25, between_scenes_sec=0.5, between_chapters_sec=1.5, min_pause_sec=0.1, max_pause_sec=3.0
    ),
    "horizontal_clip": PausePolicy(
        after_sentence_sec=0.15, between_scenes_sec=0.4, between_chapters_sec=1.0, min_pause_sec=0.05, max_pause_sec=2.0
    ),
}


def pause_policy_for_format(format_id: str) -> PausePolicy:
    return FORMAT_DEFAULTS.get(format_id, PausePolicy())


def silence_wav_bytes(duration_sec: float, *, sample_rate: int = 48000, channels: int = 1, sample_width: int = 2) -> bytes:
    """Deterministic, audio-level silence - no SSML (the repo's ElevenLabs calls are raw
    REST requests, not the SDK, and the endpoint's SSML support is unverified)."""
    duration_sec = max(0.0, duration_sec)
    frame_count = int(round(duration_sec * sample_rate))
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(sample_width)
        wav.setframerate(sample_rate)
        wav.writeframes(b"\x00" * (frame_count * channels * sample_width))
    return buffer.getvalue()


def write_silence_wav(path: str | Path, duration_sec: float, *, sample_rate: int = 48000, channels: int = 1) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(silence_wav_bytes(duration_sec, sample_rate=sample_rate, channels=channels))
    return target
