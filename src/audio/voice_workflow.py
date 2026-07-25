from __future__ import annotations

import dataclasses
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .tts.audio_file_provider import AudioFileProvider
from .tts.models import TTSRequest, compute_settings_hash, compute_text_hash


VOICE_STATES = [
    "unconfigured",
    "draft_ready",
    "provider_selection_required",
    "audition_confirmation_required",
    "audition_generating",
    "awaiting_voice_approval",
    "voice_approved",
    "voice_rejected",
    "final_confirmation_required",
    "final_generating",
    "completed",
    "failed",
]


@dataclass
class VoiceApproval:
    approved: bool
    scope: str
    provider: str
    voice_id: str
    voice_name: str
    model_id: str
    language: str
    script_hash: str
    settings_hash: str
    approved_at: str
    approved_by: str = "user"

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


def is_final_generation_approved(request: TTSRequest, approval: VoiceApproval | None) -> bool:
    if not approval or not approval.approved:
        return False
    return all(
        [
            approval.provider == request.provider,
            approval.voice_id == request.voice_id,
            approval.model_id == request.model_id,
            approval.language == request.language,
            approval.script_hash == compute_text_hash(request.text),
            approval.settings_hash == compute_settings_hash(request.settings),
            approval.scope in {"once", "job", "channel_voice_default"},
        ]
    )


def build_audition_text(script_text: str, max_characters: int = 300) -> str:
    cleaned = " ".join(script_text.split())
    if len(cleaned) <= max_characters:
        return cleaned
    fragment = cleaned[:max_characters].rsplit(" ", 1)[0].strip()
    return fragment or cleaned[:max_characters]


def voice_paths(project_root: str | Path, language: str) -> dict[str, Path]:
    root = Path(project_root) / "localizations" / language / "voice"
    return {
        "root": root,
        "selection": root / "voice_selection.json",
        "approval": root / "approval.json",
        "manifest": root / "voice_manifest.json",
        "previews": root / "previews",
    }


def import_manual_audio(
    *,
    project_root: str | Path,
    job_id: str,
    language: str,
    audio_file: str,
    scene_id: str | None = None,
) -> dict[str, Any]:
    paths = voice_paths(project_root, language)
    paths["root"].mkdir(parents=True, exist_ok=True)
    output_name = f"{scene_id}.wav" if scene_id else "narration.wav"
    output_path = paths["root"] / output_name
    request = TTSRequest(
        job_id=job_id,
        localization_id=language,
        scene_id=scene_id,
        provider="audio_file",
        language=language,
        text="",
        audio_file=audio_file,
        output_path=str(output_path),
    )
    result = AudioFileProvider().synthesize(request)
    manifest = {
        "status": "completed",
        "voice_stage_status": "completed",
        "provider": "audio_file",
        "language": language,
        "audio_path": result.audio_path,
        "duration_sec": result.duration_sec,
        "sample_rate": result.sample_rate,
        "channels": result.channels,
        "cache_hit": result.cache_hit,
        "source_type": result.source_type,
        "paid_provider": "elevenlabs",
        "paid_tts_requires_approval": True,
        "paid_call_performed": False,
    }
    selection = {
        "provider": "audio_file",
        "language": language,
        "audio_file": str(Path(audio_file)),
        "source_type": result.source_type,
        "status": "user_provided",
    }
    _write_json(paths["selection"], selection)
    _write_json(paths["manifest"], manifest)
    return manifest


def create_voice_approval_record(
    *,
    project_root: str | Path,
    language: str,
    scope: str,
    provider: str,
    voice_id: str,
    voice_name: str,
    model_id: str,
    script_text: str,
    settings: dict[str, Any],
    approved_at: str,
    approved_by: str = "user",
) -> VoiceApproval:
    if scope == "global_auto_approval":
        raise ValueError("global_auto_approval is not implemented.")
    approval = VoiceApproval(
        approved=True,
        scope=scope,
        provider=provider,
        voice_id=voice_id,
        voice_name=voice_name,
        model_id=model_id,
        language=language,
        script_hash=compute_text_hash(script_text),
        settings_hash=compute_settings_hash(settings),
        approved_at=approved_at,
        approved_by=approved_by,
    )
    paths = voice_paths(project_root, language)
    paths["root"].mkdir(parents=True, exist_ok=True)
    _write_json(paths["approval"], approval.to_dict())
    return approval


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
