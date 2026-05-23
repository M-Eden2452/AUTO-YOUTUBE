from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

from src.utils import project_path


DEFAULT_MOSS_TTS_TEST_TEXT = "\u0422\u044b \u043d\u0435 \u043b\u0435\u043d\u0438\u0432\u044b\u0439. \u0422\u044b \u043f\u0435\u0440\u0435\u0433\u0440\u0443\u0436\u0435\u043d. \u0418\u043d\u043e\u0433\u0434\u0430 \u043c\u043e\u0437\u0433\u0443 \u043d\u0443\u0436\u043d\u0430 \u043d\u0435 \u043c\u043e\u0442\u0438\u0432\u0430\u0446\u0438\u044f, \u0430 \u0442\u0438\u0448\u0438\u043d\u0430."
DEFAULT_MOSS_TTS_OUTPUT = Path("outputs/tts_tests/moss_tts_test.wav")


class MossTtsProviderError(RuntimeError):
    """Raised when the local MOSS-TTS-Nano provider cannot synthesize audio."""


def synthesize_text(text: str, output_path: str | Path, config: dict[str, Any] | None = None) -> Path:
    tts_config = _tts_config(config or {})
    moss_path = project_path(tts_config.get("moss_tts_path", "MOSS_TTS_Nano"))
    python_exe = _moss_python_exe(moss_path)
    target = project_path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    _validate_moss_repo(moss_path, python_exe)
    command = _build_command(python_exe, text, target, tts_config)

    timeout = int(tts_config.get("timeout_seconds", 900))
    try:
        result = subprocess.run(
            command,
            cwd=moss_path,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise MossTtsProviderError(f"MOSS-TTS-Nano timed out after {timeout}s while writing {target}.") from exc
    except OSError as exc:
        raise MossTtsProviderError(f"Failed to start MOSS-TTS-Nano from {moss_path}: {exc}") from exc

    if result.returncode != 0:
        details = (result.stderr or result.stdout or "").strip()
        raise MossTtsProviderError(f"MOSS-TTS-Nano failed with exit code {result.returncode}: {details}")
    if not target.exists() or target.stat().st_size <= 0:
        details = (result.stderr or result.stdout or "").strip()
        raise MossTtsProviderError(f"MOSS-TTS-Nano did not create a non-empty audio file at {target}. {details}")
    return target


def run_test_synthesis(config: dict[str, Any] | None = None) -> Path:
    tts_config = _tts_config(config or {})
    output_path = tts_config.get("test_output_path", DEFAULT_MOSS_TTS_OUTPUT)
    return synthesize_text(DEFAULT_MOSS_TTS_TEST_TEXT, output_path, tts_config)


def _tts_config(config: dict[str, Any]) -> dict[str, Any]:
    nested = config.get("tts")
    return dict(nested if isinstance(nested, dict) else config)


def _moss_python_exe(moss_path: Path) -> Path:
    if _is_windows():
        return moss_path / ".venv" / "Scripts" / "python.exe"
    return moss_path / ".venv" / "bin" / "python"


def _is_windows() -> bool:
    return os.name == "nt"


def _validate_moss_repo(moss_path: Path, python_exe: Path) -> None:
    if not moss_path.exists():
        raise MossTtsProviderError(f"MOSS-TTS-Nano path does not exist: {moss_path}")
    if not (moss_path / "infer.py").exists():
        raise MossTtsProviderError(f"MOSS-TTS-Nano infer.py was not found under: {moss_path}")
    if not (moss_path / "requirements.txt").exists():
        raise MossTtsProviderError(f"MOSS-TTS-Nano requirements.txt was not found under: {moss_path}")
    nested_repo = moss_path / "MOSS_TTS_Nano"
    if (nested_repo / "infer.py").exists() and (nested_repo / "requirements.txt").exists():
        raise MossTtsProviderError(
            f"MOSS-TTS-Nano appears nested at {nested_repo}. Move the inner repository contents up to {moss_path}."
        )
    if not python_exe.exists():
        raise MossTtsProviderError(f"MOSS-TTS-Nano venv Python was not found: {python_exe}")


def _build_command(python_exe: Path, text: str, target: Path, config: dict[str, Any]) -> list[str]:
    backend = str(config.get("backend", "onnx"))
    command = [
        str(python_exe),
        "-m",
        "moss_tts_nano",
        "generate",
        "--backend",
        backend,
        "--text",
        text,
        "--output-audio-path",
        str(target),
        "--max-new-frames",
        str(int(config.get("max_new_frames", 120))),
    ]
    if backend == "onnx":
        command.extend(
            [
                "--execution-provider",
                str(config.get("execution_provider", "cpu")),
                "--voice",
                str(config.get("voice", "Junhao")),
            ]
        )
    else:
        command.extend(["--device", str(config.get("device", "auto"))])

    if config.get("voice_clone_enabled") and config.get("prompt_audio_path"):
        command.extend(["--mode", "voice_clone", "--prompt-audio-path", str(project_path(config["prompt_audio_path"]))])
    return command
