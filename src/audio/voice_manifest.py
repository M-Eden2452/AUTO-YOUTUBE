from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .audio_assembler import AssemblyResult
from .narration_models import NarrationRequest
from .voice_workflow import VoiceApproval


SCHEMA_VERSION = 2


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_cache_summary(scenes_meta: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(scenes_meta)
    hits = sum(1 for scene in scenes_meta if scene.get("cache_hit"))
    return {"total_scenes": total, "cache_hits": hits, "cache_misses": total - hits}


def _default_generation_summary(scenes_meta: list[dict[str, Any]]) -> dict[str, Any]:
    completed = sum(1 for scene in scenes_meta if scene.get("generation_status") == "completed")
    failed = sum(1 for scene in scenes_meta if scene.get("generation_status") == "failed")
    return {"completed": completed, "failed": failed, "total": len(scenes_meta)}


def build_voice_manifest(
    request: NarrationRequest,
    *,
    status: str,
    scenes_meta: list[dict[str, Any]] | None = None,
    assembly: AssemblyResult | None = None,
    approval: VoiceApproval | None = None,
    preflight: dict[str, Any] | None = None,
    cache_summary: dict[str, Any] | None = None,
    generation_summary: dict[str, Any] | None = None,
    post_processing: dict[str, Any] | None = None,
    errors: list[str] | None = None,
    warnings: list[str] | None = None,
    voice_stage_status: str | None = None,
) -> dict[str, Any]:
    """Build the unified voice_manifest.json payload (schema_version=2).

    Always sets a legacy-compatible top-level ``audio_path``/``status`` so
    ``src/news/final_renderer.py`` (which only reads ``voice_manifest["audio_path"]``)
    and ``src/news/quality_check.py`` (which only reads ``voice_manifest["status"]``)
    keep working without any change to either file.
    """
    scenes_meta = scenes_meta or []
    character_count = sum(len(scene.text) for scene in request.scenes) or len(request.full_text)
    narration = assembly.to_dict() if assembly else {}
    audio_path = narration.get("output_path", "")
    now = _now_iso()
    return {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "voice_stage_status": voice_stage_status or status,
        "project_id": request.project_id,
        "job_id": request.job_id,
        "channel_id": request.channel_id,
        "localization": request.localization_id,
        "language": request.language,
        "format_id": request.format_id,
        "template_id": request.template_id,
        "provider": request.voice_profile.provider,
        "voice_profile": request.voice_profile.profile_id,
        "voice_id": request.voice_profile.voice_id,
        "voice_name": request.voice_profile.display_name,
        "model_id": request.voice_profile.model_id,
        "output_mode": request.policy.output_mode,
        "timing_mode": request.policy.timing_mode,
        "approval": approval.to_dict() if approval else None,
        "preflight": preflight or {},
        "character_count": character_count,
        "scenes": scenes_meta,
        "narration": narration,
        "cache_summary": cache_summary or _default_cache_summary(scenes_meta),
        "generation_summary": generation_summary or _default_generation_summary(scenes_meta),
        "post_processing": post_processing or {},
        "errors": errors or [],
        "warnings": warnings or [],
        "created_at": now,
        "updated_at": now,
        # legacy-compatible fields consumed by final_renderer.py / quality_check.py:
        "audio_path": audio_path,
        "source_type": "user_provided" if request.voice_profile.provider == "audio_file" else "generated",
        "paid_provider": "elevenlabs",
        "paid_call_performed": any(
            scene.get("generation_status") == "completed" and not scene.get("cache_hit") for scene in scenes_meta
        ),
    }


def read_voice_manifest(path: str | Path) -> dict[str, Any]:
    """Tolerant manifest reader: normalizes legacy (schema-version-less) manifests -
    both the current news/voice_stage.py stub shape and Solar's 02_voice/voice_manifest.json
    shape - into the same accessor shape as build_voice_manifest(), without raising."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if "schema_version" not in data:
        data = _normalize_legacy_manifest(data)
    return data


def _normalize_legacy_manifest(data: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(data)
    normalized.setdefault("schema_version", 1)
    normalized.setdefault("status", data.get("status") or data.get("voice_stage_status") or "unconfigured")
    normalized.setdefault("voice_stage_status", normalized["status"])
    normalized.setdefault("scenes", [])
    normalized.setdefault("narration", {"output_path": data.get("audio_path", "")})
    normalized.setdefault("cache_summary", {})
    normalized.setdefault("generation_summary", {})
    normalized.setdefault("post_processing", {})
    normalized.setdefault("errors", [])
    normalized.setdefault("warnings", [])
    normalized.setdefault("audio_path", data.get("audio_path", ""))
    return normalized
