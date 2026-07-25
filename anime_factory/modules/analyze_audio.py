from __future__ import annotations

from pathlib import Path

from .paths import read_json, write_json


def analyze_audio(audio_wav: Path, output_json: Path, force: bool = False) -> list[dict[str, float]]:
    if output_json.exists() and not force:
        print(f"Анализ аудио уже существует, пропускаю: {output_json}")
        return read_json(output_json)

    try:
        import numpy as np
        import soundfile as sf
    except ImportError as exc:
        raise RuntimeError(
            "Не установлены зависимости numpy/soundfile. Выполните: pip install -r anime_factory/requirements.txt"
        ) from exc

    print("Анализирую громкость аудио по окнам 1 секунда...")
    samples, sample_rate = sf.read(str(audio_wav), dtype="float32")
    if samples.ndim > 1:
        samples = samples.mean(axis=1)

    window_size = int(sample_rate)
    features: list[dict[str, float]] = []
    rms_values: list[float] = []
    for start_sample in range(0, len(samples), window_size):
        chunk = samples[start_sample : start_sample + window_size]
        if len(chunk) == 0:
            continue
        rms = float(np.sqrt(np.mean(np.square(chunk))))
        rms_values.append(rms)
        start = start_sample / sample_rate
        end = min((start_sample + len(chunk)) / sample_rate, len(samples) / sample_rate)
        features.append({"start": round(start, 2), "end": round(end, 2), "loudness": rms})

    max_rms = max(rms_values) if rms_values else 0.0
    for feature in features:
        feature["loudness"] = round(float(feature["loudness"] / max_rms), 4) if max_rms > 0 else 0.0

    write_json(output_json, features)
    print(f"Аудио-фичи сохранены: {output_json}")
    return features
