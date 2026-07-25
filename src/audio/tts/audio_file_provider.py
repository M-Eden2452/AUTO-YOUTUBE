from __future__ import annotations

import shutil
import wave
from pathlib import Path

from .base_provider import TTSProvider
from .models import SOURCE_USER_PROVIDED, TTSRequest, TTSResult


class AudioFileProvider(TTSProvider):
    name = "audio_file"
    paid = False

    def synthesize(self, request: TTSRequest) -> TTSResult:
        if not request.audio_file:
            raise ValueError(
                "Черновой источник озвучки не настроен. Добавьте тестовый аудиофайл, подключите локальный TTS или выберите платную пробу ElevenLabs."
            )
        source = Path(request.audio_file)
        if not source.exists():
            raise FileNotFoundError(str(source))
        if source.suffix.lower() != ".wav":
            raise ValueError("audio_file provider currently accepts WAV files in this phase.")
        output = Path(request.output_path) if request.output_path else source
        if output != source:
            output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, output)
        duration_sec, sample_rate, channels = inspect_wav(output)
        return TTSResult(
            provider=self.name,
            language=request.language,
            scene_id=request.scene_id,
            audio_path=str(output),
            duration_sec=duration_sec,
            sample_rate=sample_rate,
            channels=channels,
            cache_hit=False,
            source_type=SOURCE_USER_PROVIDED,
        )


def inspect_wav(path: str | Path) -> tuple[float, int, int]:
    with wave.open(str(path), "rb") as wav:
        frames = wav.getnframes()
        sample_rate = wav.getframerate()
        channels = wav.getnchannels()
    duration = frames / float(sample_rate) if sample_rate else 0.0
    return duration, sample_rate, channels

