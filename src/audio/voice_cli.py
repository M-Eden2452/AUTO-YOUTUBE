from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from .tts.elevenlabs_provider import ElevenLabsProvider
from .tts.env import load_elevenlabs_env
from .tts.models import TTSRequest, VoiceProfile
from .voice_workflow import create_voice_approval_record, import_manual_audio
from src.news.project_store import NewsProjectStore


def _application_roots(args: Any) -> tuple[Path, Path]:
    from src.config_resolver.paths import resolve_application_paths

    paths = resolve_application_paths(
        workspace_root=getattr(args, "workspace", None),
        paths_config=getattr(args, "paths_config", None),
        projects_root=getattr(args, "projects_root", None),
    )
    channels_root = Path(getattr(args, "channels_root", "") or paths.channels_root)
    return paths.projects_root, channels_root


def load_voice_profiles(path: str | Path) -> dict[str, VoiceProfile]:
    config_path = Path(path)
    if not config_path.exists():
        return {}
    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    profiles: dict[str, VoiceProfile] = {}
    for profile_id, item in (data.get("voices") or {}).items():
        env = load_elevenlabs_env()
        # ELEVENLABS_VOICE_ID is a *fallback* for a profile that declares no voice_id
        # of its own - the same direction src/production_plan/solar_vs_nuclear_render.py
        # already reads it (`os.getenv(...) or VOICE_ID_DOM`).
        #
        # It used to be the other way round: the environment variable replaced the
        # voice_id of every elevenlabs profile in every voices.yaml. With more than one
        # profile that means every language speaks with the same voice - an English
        # profile silently got the Russian voice_id - which is exactly the thing D2 is
        # supposed to make impossible. For the one channel configured today the two
        # values are identical, so nothing changes for it.
        declared_voice_id = str(item.get("voice_id", "") or "")
        voice_id = declared_voice_id
        if not voice_id and item.get("provider") == "elevenlabs" and env.voice_id:
            voice_id = env.voice_id
        profiles[profile_id] = VoiceProfile(
            profile_id=profile_id,
            display_name=item.get("display_name", profile_id),
            provider=item.get("provider", ""),
            voice_id=voice_id,
            model_id=item.get("model_id", item.get("model", "")),
            language=item.get("language", ""),
            enabled=bool(item.get("enabled", True)),
            settings=item.get("settings") or {},
        )
    return profiles


def run_voice_cli(args: Any) -> int:
    channel = getattr(args, "news_channel", None) or "nature_science_news_ru"
    projects_root, channels_root = _application_roots(args)
    profiles_path = channels_root / channel / "voices.yaml"
    profiles = load_voice_profiles(profiles_path)
    action = getattr(args, "voice_action", None)
    provider_name = getattr(args, "provider", None) or "elevenlabs"

    if action == "list":
        payload = {
            "channel": channel,
            "profiles": [
                {
                    "profile_id": profile.profile_id,
                    "display_name": profile.display_name,
                    "provider": profile.provider,
                    "language": profile.language,
                    "voice_id": profile.voice_id,
                    "model_id": profile.model_id,
                    "enabled": profile.enabled,
                }
                for profile in profiles.values()
                if not provider_name or profile.provider == provider_name
            ],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    if action == "import-audio":
        job_id = getattr(args, "job_id", None)
        audio_file = getattr(args, "audio_file", None)
        language = getattr(args, "language", None) or "ru"
        if not job_id or not audio_file:
            raise SystemExit("--job-id and --audio-file are required for --voice-action import-audio.")
        manifest = import_manual_audio(
            project_root=projects_root / job_id,
            job_id=job_id,
            language=language,
            audio_file=audio_file,
        )
        _update_job_voice_status(
            projects_root, job_id, language, manifest["voice_stage_status"]
        )
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
        return 0

    if action in {"inspect", "preflight", "approve", "audition"}:
        profile = _resolve_profile(args, profiles)
        if not profile:
            raise SystemExit("Voice profile or voice id is required.")
        text = _load_preflight_text(args)
        request = TTSRequest(
            job_id=getattr(args, "job_id", "") or "",
            localization_id=getattr(args, "language", None) or profile.language,
            provider=profile.provider,
            language=getattr(args, "language", None) or profile.language,
            text=text,
            voice_id=profile.voice_id,
            voice_name=profile.display_name,
            model_id=profile.model_id,
            settings=profile.settings,
            output_path=_planned_output_path(args, profile),
        )
        if action == "inspect":
            print(json.dumps(_profile_public_dict(profile), ensure_ascii=False, indent=2))
            return 0
        if action == "approve":
            job_id = getattr(args, "job_id", None)
            if not job_id:
                raise SystemExit("--job-id is required for --voice-action approve.")
            approval = create_voice_approval_record(
                project_root=projects_root / job_id,
                language=request.language,
                scope=getattr(args, "approval_scope", None) or "job",
                provider=profile.provider,
                voice_id=profile.voice_id,
                voice_name=profile.display_name,
                model_id=profile.model_id,
                script_text=text,
                settings=profile.settings,
                approved_at=_now_iso(),
            )
            print(json.dumps(approval.to_dict(), ensure_ascii=False, indent=2))
            return 0
        if action == "audition":
            result = _run_audition(args, profile, request)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        plan = ElevenLabsProvider().preflight(request) if profile.provider == "elevenlabs" else None
        payload = plan.__dict__ if plan else {"provider": profile.provider, "preflight": "not_supported"}
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    raise SystemExit(f"Unsupported voice action: {action}")


def _resolve_profile(args: Any, profiles: dict[str, VoiceProfile]) -> VoiceProfile | None:
    profile_id = getattr(args, "voice_profile", None)
    if profile_id and profile_id in profiles:
        return profiles[profile_id]
    voice_id = getattr(args, "voice_id", None)
    for profile in profiles.values():
        if voice_id and profile.voice_id == voice_id:
            return profile
    return None


def _load_preflight_text(args: Any) -> str:
    if getattr(args, "text", None):
        return args.text
    job_id = getattr(args, "job_id", None)
    language = getattr(args, "language", None) or "ru"
    if job_id:
        projects_root, _channels_root = _application_roots(args)
        narration = (
            projects_root
            / job_id
            / "localizations"
            / language
            / "script"
            / "narration.txt"
        )
        if narration.exists():
            return narration.read_text(encoding="utf-8")
    return ""


def _planned_output_path(args: Any, profile: VoiceProfile) -> str | None:
    job_id = getattr(args, "job_id", None)
    if not job_id:
        return None
    language = getattr(args, "language", None) or profile.language
    projects_root, _channels_root = _application_roots(args)
    return str(
        projects_root
        / job_id
        / "localizations"
        / language
        / "voice"
        / "narration.wav"
    )


def _planned_audition_path(args: Any, profile: VoiceProfile) -> Path:
    job_id = getattr(args, "job_id", None)
    if not job_id:
        raise SystemExit("--job-id is required for --voice-action audition.")
    language = getattr(args, "language", None) or profile.language
    projects_root, _channels_root = _application_roots(args)
    return (
        projects_root
        / job_id
        / "localizations"
        / language
        / "voice"
        / "previews"
        / "dom_audition.mp3"
    )


def _run_audition(args: Any, profile: VoiceProfile, request: TTSRequest) -> dict[str, Any]:
    if profile.provider != "elevenlabs":
        raise SystemExit("Audition currently supports ElevenLabs profiles only.")
    text = request.text.strip()
    if len(text) > 300:
        raise SystemExit("Audition text must be 300 characters or less.")
    output_path = _planned_audition_path(args, profile)
    cache_hit = output_path.exists() and output_path.stat().st_size > 0
    request = request.with_updates(output_path=str(output_path), output_format="mp3_44100_128")
    provider = ElevenLabsProvider()
    plan = provider.preflight(request)
    preflight_payload = plan.__dict__
    paid_request_summary = {
        "voice_name": profile.display_name,
        "voice_id": profile.voice_id,
        "model_id": profile.model_id,
        "character_count": len(text),
        "remaining_credits": plan.remaining_credits,
        "cache_hit": cache_hit,
        "future_file": str(output_path),
    }
    if plan.errors:
        return {
            "status": "preflight_failed",
            "paid_call_performed": False,
            "paid_request_summary": paid_request_summary,
            "preflight": preflight_payload,
        }
    if cache_hit:
        duration = _duration(output_path)
        manifest = _write_audition_manifest(args, profile, request, output_path, duration, cache_hit=True)
        return {
            "status": "awaiting_voice_approval",
            "paid_call_performed": False,
            "paid_request_summary": paid_request_summary,
            "preflight": preflight_payload,
            "manifest": manifest,
        }
    result = provider.synthesize(request)
    manifest = _write_audition_manifest(args, profile, request, output_path, result.duration_sec, cache_hit=False)
    _update_job_voice_status(getattr(args, "projects_root", "projects"), request.job_id, request.language, "awaiting_voice_approval")
    return {
        "status": "awaiting_voice_approval",
        "paid_call_performed": True,
        "paid_request_summary": paid_request_summary,
        "preflight": preflight_payload,
        "audio_path": result.audio_path,
        "duration_sec": result.duration_sec,
        "manifest": manifest,
    }


def _write_audition_manifest(
    args: Any,
    profile: VoiceProfile,
    request: TTSRequest,
    output_path: Path,
    duration_sec: float,
    *,
    cache_hit: bool,
) -> dict[str, Any]:
    from src.audio.tts.models import compute_settings_hash, compute_text_hash

    manifest = {
        "status": "awaiting_voice_approval",
        "provider": "elevenlabs",
        "voice_id": profile.voice_id,
        "voice_name": profile.display_name,
        "model_id": profile.model_id,
        "language": request.language,
        "settings": profile.settings,
        "text": request.text,
        "character_count": len(request.text),
        "audio_path": str(output_path),
        "duration_sec": duration_sec,
        "cache_hit": cache_hit,
        "source_type": "generated",
        "created_at": _now_iso(),
        "script_hash": compute_text_hash(request.text),
        "settings_hash": compute_settings_hash(profile.settings),
    }
    preview_manifest = output_path.parent / "dom_audition_manifest.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    preview_manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    voice_manifest = output_path.parent.parent / "voice_manifest.json"
    if voice_manifest.exists():
        current = json.loads(voice_manifest.read_text(encoding="utf-8"))
    else:
        current = {}
    current.update(
        {
            "status": "awaiting_voice_approval",
            "voice_stage_status": "awaiting_voice_approval",
            "paid_call_performed": True,
            "audition_path": str(output_path),
            "audition_manifest_path": str(preview_manifest),
        }
    )
    voice_manifest.write_text(json.dumps(current, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def _duration(path: Path) -> float:
    try:
        from moviepy import AudioFileClip

        clip = AudioFileClip(str(path))
        duration = float(clip.duration or 0)
        clip.close()
        return duration
    except Exception:
        return 0.0


def _profile_public_dict(profile: VoiceProfile) -> dict[str, Any]:
    return {
        "profile_id": profile.profile_id,
        "display_name": profile.display_name,
        "provider": profile.provider,
        "voice_id": profile.voice_id,
        "model_id": profile.model_id,
        "language": profile.language,
        "enabled": profile.enabled,
        "settings": profile.settings,
    }


def _now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def _update_job_voice_status(projects_root: str | Path, job_id: str, language: str, status: str) -> None:
    store = NewsProjectStore(projects_root)
    job_path = store.project_root(job_id) / "job.json"
    if not job_path.exists():
        return
    job = store.load_job(job_id)
    if language in job.localizations:
        job.localizations[language].voice_status = status
    if "voice" in job.stages:
        job.stages["voice"].status = "completed" if status == "completed" else job.stages["voice"].status
    store.save_job(job)
