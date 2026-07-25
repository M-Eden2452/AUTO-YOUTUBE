from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .tts.models import TTSRequest, VoiceProfile, compute_settings_hash, compute_text_hash, compute_tts_cache_key
from .voice_workflow import VoiceApproval
from .voice_policy import VoicePolicy


@dataclass
class NarrationScene:
    scene_id: str
    scene_index: int
    text: str
    target_duration_sec: float | None = None
    pause_after_sec: float | None = None
    emphasis: dict[str, Any] = field(default_factory=dict)
    text_hash: str = ""
    settings_hash: str = ""
    generation_key: str = ""

    def __post_init__(self) -> None:
        if not self.text_hash:
            self.text_hash = compute_text_hash(self.text)


@dataclass
class NarrationRequest:
    project_id: str
    job_id: str
    channel_id: str
    localization_id: str
    language: str
    format_id: str
    template_id: str
    voice_profile: VoiceProfile
    policy: VoicePolicy
    scenes: list[NarrationScene] = field(default_factory=list)
    full_text: str = ""
    approval: VoiceApproval | None = None
    output_root: Path = field(default_factory=Path)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.output_root = Path(self.output_root)


def compute_generation_key(
    *,
    text: str,
    provider: str,
    voice_id: str,
    model_id: str,
    language: str,
    settings: dict[str, Any],
    output_format: str,
    speed: float | None = None,
    post_processing_version: str = "",
) -> str:
    merged_settings = dict(settings)
    if speed is not None:
        merged_settings.setdefault("speed", speed)
    request = TTSRequest(
        job_id="",
        localization_id=language,
        provider=provider,
        language=language,
        text=text,
        voice_id=voice_id,
        model_id=model_id,
        settings=merged_settings,
        output_format=output_format,
    )
    return compute_tts_cache_key(request, post_processing_version=post_processing_version)


def build_narration_request_from_scenes(
    *,
    project_id: str,
    job_id: str,
    channel_id: str,
    localization_id: str,
    language: str,
    format_id: str,
    template_id: str,
    voice_profile: VoiceProfile,
    policy: VoicePolicy,
    scenes: list[dict[str, Any]],
    full_text: str = "",
    approval: VoiceApproval | None = None,
    output_root: str | Path,
    metadata: dict[str, Any] | None = None,
) -> NarrationRequest:
    settings = {**voice_profile.settings, **(policy.provider_settings or {})}
    post_processing_version = str((policy.post_processing or {}).get("version", ""))

    narration_scenes: list[NarrationScene] = []
    for index, scene in enumerate(scenes):
        scene_id = str(scene.get("scene_id") or f"scene_{index + 1:03d}")
        text = str(scene.get("text", scene.get("narration", "")))
        generation_key = compute_generation_key(
            text=text,
            provider=voice_profile.provider,
            voice_id=voice_profile.voice_id,
            model_id=voice_profile.model_id,
            language=language,
            settings=settings,
            output_format=policy.output_format,
            speed=policy.speed,
            post_processing_version=post_processing_version,
        )
        narration_scenes.append(
            NarrationScene(
                scene_id=scene_id,
                scene_index=index,
                text=text,
                target_duration_sec=scene.get("target_duration_sec"),
                pause_after_sec=scene.get("pause_after_sec"),
                emphasis=scene.get("emphasis") or {},
                settings_hash=compute_settings_hash(settings),
                generation_key=generation_key,
            )
        )

    return NarrationRequest(
        project_id=project_id,
        job_id=job_id,
        channel_id=channel_id,
        localization_id=localization_id,
        language=language,
        format_id=format_id,
        template_id=template_id,
        voice_profile=voice_profile,
        policy=policy,
        scenes=narration_scenes,
        full_text=full_text,
        approval=approval,
        output_root=Path(output_root),
        metadata=metadata or {},
    )
