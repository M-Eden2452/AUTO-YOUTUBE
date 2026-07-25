from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from src.assets.frame_sampling import sha256_file as checksum_sha256

from .narration_models import NarrationRequest, NarrationScene
from .tts.models import TTSRequest
from .tts.provider_manager import TTSProviderManager
from .voice_workflow import voice_paths


TRANSIENT_EXCEPTIONS = (requests.exceptions.ConnectionError, requests.exceptions.Timeout)


def generation_output_paths(project_root: str | Path, language: str) -> dict[str, Path]:
    paths = voice_paths(project_root, language)
    root = paths["root"]
    scenes_dir = root / "scenes"
    return {
        **paths,
        "scenes_dir": scenes_dir,
        "narration_wav": root / "narration.wav",
        "narration_mp3": root / "narration.mp3",
    }


def _scene_stem(scene_index: int) -> str:
    return f"scene_{scene_index + 1:03d}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_scene_cache(scenes_dir: str | Path) -> dict[str, dict[str, Any]]:
    scenes_dir = Path(scenes_dir)
    if not scenes_dir.exists():
        return {}
    cache: dict[str, dict[str, Any]] = {}
    for meta_path in sorted(scenes_dir.glob("*.json")):
        try:
            data = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        scene_id = data.get("scene_id")
        if scene_id:
            cache[scene_id] = data
    return cache


def is_scene_cache_valid(scene_meta: dict[str, Any] | None, scene: NarrationScene) -> bool:
    if not scene_meta:
        return False
    if scene_meta.get("generation_status") != "completed":
        return False
    if scene_meta.get("generation_key") != scene.generation_key:
        return False
    output_path = scene_meta.get("output_path")
    if not output_path or not Path(output_path).is_file():
        return False
    expected_checksum = scene_meta.get("checksum_sha256")
    if not expected_checksum:
        return False
    if checksum_sha256(output_path) != expected_checksum:
        return False
    size_bytes = scene_meta.get("size_bytes")
    if size_bytes is not None and Path(output_path).stat().st_size != size_bytes:
        return False
    return True


def _provider_output_format(provider: str) -> str:
    return "mp3_44100_128" if provider == "elevenlabs" else "wav"


def _write_scene_meta(scenes_dir: Path, scene_index: int, data: dict[str, Any]) -> Path:
    scenes_dir.mkdir(parents=True, exist_ok=True)
    path = scenes_dir / f"{_scene_stem(scene_index)}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _synthesize_with_one_retry(
    manager: TTSProviderManager,
    tts_request: TTSRequest,
    *,
    approved: bool,
    max_retries_on_transient: int,
):
    attempts = 0
    while True:
        try:
            return manager.synthesize(tts_request, approved=approved)
        except TRANSIENT_EXCEPTIONS:
            attempts += 1
            if attempts > max_retries_on_transient:
                raise
            continue


def generate_scenes(
    request: NarrationRequest,
    *,
    manager: TTSProviderManager,
    approved: bool,
    max_retries_on_transient: int = 1,
) -> list[dict[str, Any]]:
    """Synthesize (or reuse cached) audio for every scene in the request.

    One synth attempt per scene, one retry only for a transient network error
    (ConnectionError/Timeout) - never for an ambiguous HTTP status. A scene that fails
    is recorded with generation_status="failed" and does not stop the other scenes from
    being generated/preserved (partial success). The paid-provider approval gate is
    checked once up front (fail-fast, no per-scene paid calls are attempted without it)
    via the same TTSProviderManager that scene requests are synthesized through.
    """
    if request.scenes:
        provider = manager.get(request.voice_profile.provider)
        if provider.paid and not approved:
            raise PermissionError(
                f"Paid TTS provider '{provider.name}' requires explicit approval for final generation."
            )

    paths = generation_output_paths(request.output_root, request.language)
    scenes_dir = paths["scenes_dir"]
    scenes_dir.mkdir(parents=True, exist_ok=True)
    cache = load_scene_cache(scenes_dir)

    results: list[dict[str, Any]] = []
    settings = {**request.voice_profile.settings}
    if request.policy.speed is not None:
        settings.setdefault("speed", request.policy.speed)

    for scene in request.scenes:
        cached = cache.get(scene.scene_id)
        if request.policy.reuse_cache and is_scene_cache_valid(cached, scene):
            reused = dict(cached)
            reused["cache_hit"] = True
            results.append(reused)
            continue

        output_path = scenes_dir / f"{_scene_stem(scene.scene_index)}.mp3"
        tts_request = TTSRequest(
            job_id=request.job_id,
            localization_id=request.localization_id,
            scene_id=scene.scene_id,
            provider=request.voice_profile.provider,
            language=request.language,
            text=scene.text,
            voice_id=request.voice_profile.voice_id,
            voice_name=request.voice_profile.display_name,
            model_id=request.voice_profile.model_id,
            settings=settings,
            output_format=_provider_output_format(request.voice_profile.provider),
            output_path=str(output_path),
        )

        base_meta = {
            "scene_id": scene.scene_id,
            "scene_index": scene.scene_index,
            "text": scene.text,
            "text_hash": scene.text_hash,
            "settings_hash": scene.settings_hash,
            "generation_key": scene.generation_key,
            "provider": request.voice_profile.provider,
            "voice_profile": request.voice_profile.profile_id,
            "provider_voice_id": request.voice_profile.voice_id,
            "model_id": request.voice_profile.model_id,
            "language": request.language,
        }
        try:
            result = _synthesize_with_one_retry(
                manager,
                tts_request,
                approved=approved,
                max_retries_on_transient=max_retries_on_transient,
            )
        except Exception as exc:  # noqa: BLE001 - per-scene failure must not abort the batch
            scene_meta = {
                **base_meta,
                "output_path": None,
                "duration_seconds": 0.0,
                "size_bytes": 0,
                "checksum_sha256": "",
                "generation_status": "failed",
                "cache_hit": False,
                "generated_at": _now_iso(),
                "error": str(exc),
            }
        else:
            audio_path = Path(result.audio_path)
            scene_meta = {
                **base_meta,
                "output_path": str(audio_path),
                "duration_seconds": result.duration_sec,
                "size_bytes": audio_path.stat().st_size,
                "checksum_sha256": checksum_sha256(audio_path),
                "generation_status": "completed",
                "cache_hit": False,
                "generated_at": _now_iso(),
                "error": None,
            }
        _write_scene_meta(scenes_dir, scene.scene_index, scene_meta)
        results.append(scene_meta)

    return results
