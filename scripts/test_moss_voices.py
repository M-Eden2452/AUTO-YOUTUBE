from __future__ import annotations

import sys
import time
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config_loader import load_config
from src.tts_providers.moss_tts_provider import MossTtsProviderError, synthesize_text
from src.utils import ensure_dir


MAIN_SAMPLE_DIR = PROJECT_ROOT / "assets" / "voice_samples"
MOSS_SAMPLE_DIR = PROJECT_ROOT / "MOSS_TTS_Nano" / "assets" / "voice_samples"
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "tts_tests" / "moss"
REPORT_PATH = OUTPUT_DIR / "moss_voice_report.md"

SAMPLE_README = """# MOSS voice samples

Place short clean reference voice samples here for MOSS-TTS-Nano voice cloning tests.

Requirements:
- 5-20 seconds
- wav or mp3
- one speaker
- no music
- no background noise
- no heavy reverb

Suggested names:
- moss_test_01.wav
- moss_test_02.wav
- moss_test_03.wav

You can also place samples in:

```text
G:/Projects/AI-YouTube/MOSS_TTS_Nano/assets/voice_samples/
```
"""

TEST_TEXTS = {
    "ru_short": "\u0422\u044b \u043d\u0435 \u043b\u0435\u043d\u0438\u0432\u044b\u0439. \u0422\u044b \u043f\u0435\u0440\u0435\u0433\u0440\u0443\u0436\u0435\u043d. \u0418\u043d\u043e\u0433\u0434\u0430 \u043c\u043e\u0437\u0433\u0443 \u043d\u0443\u0436\u043d\u0430 \u043d\u0435 \u043c\u043e\u0442\u0438\u0432\u0430\u0446\u0438\u044f, \u0430 \u0442\u0438\u0448\u0438\u043d\u0430.",
    "ru_narration": "\u0421\u043e\u0432\u0440\u0435\u043c\u0435\u043d\u043d\u044b\u0439 \u0447\u0435\u043b\u043e\u0432\u0435\u043a \u0443\u0441\u0442\u0430\u0435\u0442 \u043d\u0435 \u0442\u043e\u043b\u044c\u043a\u043e \u043e\u0442 \u0440\u0430\u0431\u043e\u0442\u044b. \u041e\u043d \u0443\u0441\u0442\u0430\u0435\u0442 \u043e\u0442 \u043f\u043e\u0441\u0442\u043e\u044f\u043d\u043d\u043e\u0433\u043e \u0448\u0443\u043c\u0430, \u0443\u0432\u0435\u0434\u043e\u043c\u043b\u0435\u043d\u0438\u0439 \u0438 \u0431\u0435\u0441\u043a\u043e\u043d\u0435\u0447\u043d\u043e\u0433\u043e \u043f\u043e\u0442\u043e\u043a\u0430 \u0438\u043d\u0444\u043e\u0440\u043c\u0430\u0446\u0438\u0438.",
    "en_short": "This is a local voice test for the NightPuzzle and AI-YouTube automation project.",
}


@dataclass(frozen=True)
class VoiceSample:
    sample_id: str
    path: Path


@dataclass(frozen=True)
class GenerationResult:
    sample: VoiceSample
    test_id: str
    text: str
    output_path: Path
    duration_seconds: float
    file_size_bytes: int
    backend: str
    speed: str
    error: str


def main() -> int:
    ensure_sample_dir()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    config = moss_config()
    samples = discover_voice_samples([MAIN_SAMPLE_DIR, MOSS_SAMPLE_DIR])
    if not samples:
        report = build_report(samples, [], config, no_samples=True)
        REPORT_PATH.write_text(report, encoding="utf-8")
        print(f"[moss-voices] No samples found. Instructions written to {MAIN_SAMPLE_DIR / 'README.md'}")
        print(f"[moss-voices] Report written to {REPORT_PATH}")
        return 0

    results: list[GenerationResult] = []
    for sample in samples:
        for test_id, text in TEST_TEXTS.items():
            output_path = OUTPUT_DIR / f"{sample.sample_id}_{test_id}.wav"
            results.append(generate_one(sample, test_id, text, output_path, config))
            REPORT_PATH.write_text(build_report(samples, results, config), encoding="utf-8")

    REPORT_PATH.write_text(build_report(samples, results, config), encoding="utf-8")
    failures = [result for result in results if result.error]
    print(f"[moss-voices] Samples: {len(samples)} | tests: {len(results)} | failures: {len(failures)}")
    print(f"[moss-voices] Output dir: {OUTPUT_DIR}")
    print(f"[moss-voices] Report: {REPORT_PATH}")
    return 1 if len(failures) == len(results) else 0


def ensure_sample_dir() -> None:
    MAIN_SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    readme = MAIN_SAMPLE_DIR / "README.md"
    if not readme.exists():
        readme.write_text(SAMPLE_README, encoding="utf-8")


def moss_config() -> dict[str, Any]:
    base = load_config("config/video_style.json")
    tts = dict(base.get("tts", {}))
    tts.update(
        {
            "backend": "onnx",
            "execution_provider": "cpu",
            "voice_clone_enabled": True,
            "max_new_frames": 95,
            "timeout_seconds": 900,
        }
    )
    return tts


def discover_voice_samples(sample_roots: list[Path]) -> list[VoiceSample]:
    supported = {".wav", ".mp3", ".m4a", ".aac", ".flac"}
    samples: list[VoiceSample] = []
    seen: set[Path] = set()
    for root in sample_roots:
        if not root.exists():
            continue
        for path in sorted(root.iterdir()):
            if not path.is_file() or path.suffix.lower() not in supported:
                continue
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            samples.append(VoiceSample(sample_id=f"moss_test_{len(samples) + 1:02d}", path=path))
    return samples


def generate_one(
    sample: VoiceSample,
    test_id: str,
    text: str,
    output_path: Path,
    config: dict[str, Any],
) -> GenerationResult:
    start = time.perf_counter()
    error = ""
    try:
        synthesize_text(
            text,
            output_path,
            {
                **config,
                "prompt_audio_path": str(sample.path),
                "voice_clone_enabled": True,
            },
        )
    except MossTtsProviderError as exc:
        error = str(exc)
    except Exception as exc:
        error = f"Unexpected error: {exc}"
    elapsed = time.perf_counter() - start
    size = output_path.stat().st_size if output_path.exists() else 0
    audio_duration = wav_duration(output_path) if output_path.exists() else 0.0
    speed = speed_text(elapsed, audio_duration)
    return GenerationResult(
        sample=sample,
        test_id=test_id,
        text=text,
        output_path=output_path,
        duration_seconds=elapsed,
        file_size_bytes=size,
        backend=str(config.get("backend", "onnx")),
        speed=speed,
        error=error,
    )


def build_report(
    samples: list[VoiceSample],
    results: list[GenerationResult],
    backend_info: dict[str, Any],
    no_samples: bool = False,
) -> str:
    lines = [
        "# MOSS-TTS-Nano Voice Test Report",
        "",
        f"- generated_at: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"- backend: {backend_info.get('backend', 'onnx')}",
        f"- execution_provider: {backend_info.get('execution_provider', 'cpu')}",
        f"- moss_python: {moss_python_path(backend_info)}",
        f"- sample_roots: `{MAIN_SAMPLE_DIR}`, `{MOSS_SAMPLE_DIR}`",
        "",
    ]
    if no_samples:
        lines.extend(
            [
                "## No voice samples found",
                "",
                "Add short clean voice samples before running the tester.",
                "",
                "- Required length: 5-20 seconds",
                "- Format: wav or mp3",
                "- One speaker",
                "- No music",
                "- No background noise",
                "",
            ]
        )
        return "\n".join(lines)

    lines.extend(["## Samples", ""])
    for sample in samples:
        lines.append(f"- {sample.sample_id}: `{sample.path}`")
    lines.extend(["", "## Results", ""])
    for result in results:
        output_name = f"{result.sample.sample_id}_{result.test_id}.wav"
        lines.extend(
            [
                f"### {output_name}",
                "",
                f"- sample: {result.sample.sample_id}",
                f"- sample_path: `{result.sample.path}`",
                f"- text_id: {result.test_id}",
                f"- text: {result.text}",
                f"- output_wav: `{result.output_path}`",
                f"- generation_time_seconds: {result.duration_seconds:.2f}",
                f"- file_size_bytes: {result.file_size_bytes}",
                f"- error: {result.error or 'none'}",
                f"- backend: {result.backend}",
                f"- speed: {result.speed}",
                "",
                "Manual quality check:",
                "",
                "- naturalness:",
                "- similarity:",
                "- russian_quality:",
                "- noise:",
                "- speed:",
                "- usable_for_youtube: yes/no",
                "- notes:",
                "",
            ]
        )
    return "\n".join(lines)


def moss_python_path(config: dict[str, Any]) -> str:
    moss_path = Path(config.get("moss_tts_path", PROJECT_ROOT / "MOSS_TTS_Nano"))
    return str(moss_path / ".venv" / "Scripts" / "python.exe")


def wav_duration(path: Path) -> float:
    if path.suffix.lower() != ".wav":
        return 0.0
    try:
        with wave.open(str(path), "rb") as handle:
            frames = handle.getnframes()
            rate = handle.getframerate()
            return frames / float(rate) if rate else 0.0
    except wave.Error:
        return 0.0


def speed_text(elapsed: float, audio_duration: float) -> str:
    if elapsed <= 0 or audio_duration <= 0:
        return "unknown"
    return f"{audio_duration / elapsed:.2f}x realtime"


if __name__ == "__main__":
    raise SystemExit(main())
