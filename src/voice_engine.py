from __future__ import annotations

import hashlib
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import imageio_ffmpeg
import requests
from dotenv import load_dotenv
from moviepy import AudioFileClip

from .utils import project_path, write_json


REQUEST_TIMEOUT = 60
ELEVENLABS_TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"


def build_voice_manifest(
    config: dict[str, Any],
    scene_plan: dict[str, Any],
    reuse_voice: bool = True,
    skip_voice: bool = False,
) -> dict[str, Any]:
    voice_config = _voice_config(config)
    output_path = project_path(config.get("plans", {}).get("voice_manifest", Path(config.get("output_dir", "outputs")) / "voice_manifest.json"))
    cache_dir = project_path(voice_config.get("cache_dir", Path(config.get("output_dir", "outputs")) / "voice"))
    cache_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "engine": "voice_engine_v1",
        "enabled": bool(voice_config.get("enabled", True)) and not skip_voice,
        "provider": voice_config.get("provider", "elevenlabs"),
        "voice_id": voice_config.get("voice_id", ""),
        "style": voice_config.get("style", "calm grounded survival documentary"),
        "cache_dir": str(cache_dir),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "scenes": [],
        "total_voice_duration": 0.0,
        "warnings": [],
    }
    if skip_voice or not manifest["enabled"]:
        manifest["status"] = "skipped"
        write_json(output_path, manifest)
        return manifest

    load_dotenv()
    api_key = os.getenv("ELEVENLABS_API_KEY", "")
    provider = str(voice_config.get("provider", "elevenlabs"))
    cursor = 0.0
    for scene in scene_plan.get("scenes", []):
        text = _scene_voice_text(scene)
        scene_number = int(scene.get("scene_number", len(manifest["scenes"]) + 1))
        cache_key = _cache_key(text, voice_config)
        target = cache_dir / f"scene_{scene_number:03d}_{cache_key[:10]}.mp3"
        cache_status = "reused" if reuse_voice and target.exists() and target.stat().st_size > 0 else "generated"
        if cache_status != "reused":
            if provider == "local_stub" or not api_key:
                _create_stub_voice_mp3(target, _estimate_voice_duration(text))
                if provider != "local_stub" and not api_key:
                    manifest["warnings"].append("ELEVENLABS_API_KEY unavailable; local placeholder voice was generated.")
            else:
                try:
                    _generate_elevenlabs_voice(api_key, voice_config, text, target)
                except requests.RequestException as exc:
                    _create_stub_voice_mp3(target, _estimate_voice_duration(text))
                    manifest["warnings"].append(f"ElevenLabs voice request failed for scene {scene_number}: {exc.__class__.__name__}.")
        duration = _audio_duration(target) or _estimate_voice_duration(text)
        item = {
            "scene_number": scene_number,
            "scene_id": scene.get("scene_id", ""),
            "text_hash": cache_key,
            "path": str(target),
            "text": text,
            "duration": round(duration, 3),
            "start": round(cursor, 3),
            "cache_status": cache_status,
        }
        manifest["scenes"].append(item)
        cursor += max(float(scene.get("duration", 0)), duration + float(voice_config.get("post_scene_pause", 0.8)))

    manifest["total_voice_duration"] = round(sum(float(item["duration"]) for item in manifest["scenes"]), 3)
    manifest["status"] = "ready" if manifest["scenes"] else "empty"
    write_json(output_path, manifest)
    return manifest


def apply_voice_timing_to_scene_plan(scene_plan: dict[str, Any], voice_manifest: dict[str, Any], cinematic_preview: bool = False) -> dict[str, Any]:
    if not voice_manifest.get("enabled") or not voice_manifest.get("scenes"):
        return scene_plan
    by_number = {int(item["scene_number"]): item for item in voice_manifest.get("scenes", [])}
    scenes: list[dict[str, Any]] = []
    for scene in scene_plan.get("scenes", []):
        item = by_number.get(int(scene.get("scene_number", 0)))
        updated = {**scene}
        if item:
            voice_duration = float(item.get("duration", 0))
            updated["voice_duration"] = voice_duration
            updated["duration"] = round(max(float(scene.get("duration", 0)), voice_duration + (1.0 if cinematic_preview else 0.5)), 3)
        scenes.append(updated)
    updated_plan = {**scene_plan, "scenes": scenes}
    updated_plan["target_duration"] = round(sum(float(scene.get("duration", 0)) for scene in scenes), 3)
    return updated_plan


def align_voice_manifest_to_scene_plan(voice_manifest: dict[str, Any], scene_plan: dict[str, Any]) -> dict[str, Any]:
    if not voice_manifest.get("scenes"):
        return voice_manifest
    starts: dict[int, float] = {}
    cursor = 0.0
    for scene in scene_plan.get("scenes", []):
        starts[int(scene.get("scene_number", 0))] = cursor
        cursor += float(scene.get("duration", 0))
    updated = {**voice_manifest, "scenes": []}
    for item in voice_manifest.get("scenes", []):
        scene_number = int(item.get("scene_number", 0))
        updated["scenes"].append({**item, "start": round(starts.get(scene_number, item.get("start", 0)), 3)})
    return updated


def _voice_config(config: dict[str, Any]) -> dict[str, Any]:
    defaults = {
        "enabled": True,
        "provider": "elevenlabs",
        "voice_id": "EXAVITQu4vr4xnSDxMaL",
        "model_id": "eleven_multilingual_v2",
        "stability": 0.58,
        "similarity_boost": 0.72,
        "style": "calm grounded cinematic survival documentary",
        "speaker_boost": True,
        "post_scene_pause": 0.8,
    }
    return {**defaults, **config.get("voice", {})}


def _generate_elevenlabs_voice(api_key: str, voice_config: dict[str, Any], text: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    response = requests.post(
        ELEVENLABS_TTS_URL.format(voice_id=voice_config.get("voice_id")),
        headers={"xi-api-key": api_key, "Accept": "audio/mpeg", "Content-Type": "application/json"},
        json={
            "text": text,
            "model_id": voice_config.get("model_id", "eleven_multilingual_v2"),
            "voice_settings": {
                "stability": float(voice_config.get("stability", 0.58)),
                "similarity_boost": float(voice_config.get("similarity_boost", 0.72)),
                "use_speaker_boost": bool(voice_config.get("speaker_boost", True)),
            },
        },
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    target.write_bytes(response.content)


def _create_stub_voice_mp3(target: Path, duration: float) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    command = [
        imageio_ffmpeg.get_ffmpeg_exe(),
        "-y",
        "-f",
        "lavfi",
        "-i",
        "anullsrc=channel_layout=stereo:sample_rate=44100",
        "-t",
        f"{max(duration, 0.5):.3f}",
        "-q:a",
        "9",
        "-acodec",
        "libmp3lame",
        str(target),
    ]
    subprocess.run(command, capture_output=True, text=True, check=True)


def _audio_duration(path: Path) -> float:
    clip = None
    try:
        clip = AudioFileClip(str(path))
        return float(clip.duration or 0)
    except Exception:
        return 0.0
    finally:
        if clip:
            clip.close()


def _scene_voice_text(scene: dict[str, Any]) -> str:
    return str(scene.get("subtitle_text") or scene.get("screen_text") or "").strip()


def _estimate_voice_duration(text: str) -> float:
    word_count = len([part for part in text.split() if part.strip()])
    return max(2.0, word_count / 2.25 + 0.6)


def _cache_key(text: str, voice_config: dict[str, Any]) -> str:
    payload = "|".join(
        [
            text,
            str(voice_config.get("provider", "")),
            str(voice_config.get("voice_id", "")),
            str(voice_config.get("model_id", "")),
            str(voice_config.get("stability", "")),
            str(voice_config.get("similarity_boost", "")),
        ]
    )
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()
