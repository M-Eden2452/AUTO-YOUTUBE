"""Canonical boundary платной генерации озвучки: gate, сборка, манифест, валидация.

Единственный путь, по которому проект выполняет платную генерацию речи.
``prepare_final`` только смотрит, ``generate_final`` действует и без валидного
approval отказывает.

Responsibilities:
- ``prepare_final`` — preflight провайдера, осмотр кэша сцен и проверка
  approval без единого платного вызова;
- ``approval_covers_request`` — approval выдаётся один раз на весь текст
  озвучки и проверяется по существующему hash-контракту;
- ``generate_final`` — по-сценная генерация, сборка narration с паузами формата
  и запись ``voice_manifest.json``;
- ``invalidate_scenes`` — точечная инвалидация только перечисленных сцен;
- ``validate_output`` — completed-gate озвучки на диске;
- ``EXTENDED_VOICE_STATES`` — расширение существующего набора состояний
  ``voice_workflow.VOICE_STATES``, а не его замена.

Does not own:
- контракт TTS-провайдера и их реестр — ``src.audio.tts``;
- policy озвучки и профили голоса — ``voice_policy``,
  ``voice_profile_registry``;
- форму манифеста — ``voice_manifest``; сборку звука — ``audio_assembler``;
  паузы — ``pause_policy``;
- фактические длительности сцен — ``scene_timeline``;
- порядок стадий и статус проекта — ``src.news.pipeline``;
- субтитры и рендер.

Inputs: ``NarrationRequest`` (текст, сцены, профиль голоса, язык, policy,
approval, ``output_root``) и ``TTSProviderManager``.

Outputs: ``localizations/<lang>/voice/voice_manifest.json``, по-сценные
аудиофайлы с sidecar-кэшем и собранный ``narration.wav``; функции возвращают
сам манифест либо ``NarrationValidationResult``.

Important invariants:
- при ``approval_required`` генерация без валидного approval поднимает
  ``PermissionError``; approval привязан к текущему тексту, настройкам, голосу,
  модели и языку;
- ``prepare_final`` платных вызовов не делает;
- выключенная озвучка даёт манифест со статусом ``skipped``, а не пустой
  результат;
- narration собирается только когда все сцены завершены; частичный сбой
  оставляет ``partially_completed`` и сохраняет уже сгенерированные сцены;
- ``validate_output`` считает озвучку завершённой только при полном наборе
  сцен, существующих файлах, ненулевой длительности и совпадении checksum;
- ``invalidate_scenes`` удаляет только sidecar перечисленных сцен и остальные
  не трогает.

See also: ``src/audio/__init__.py``, ``src/news/voice_stage.py``,
``docs/current/SYSTEM_MAP.md``.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any

from src.assets.frame_sampling import sha256_file as checksum_sha256

from .audio_assembler import PostProcessingConfig, assemble_narration
from .narration_models import NarrationRequest
from .pause_policy import pause_policy_for_format
from .scene_voice_generator import generate_scenes, generation_output_paths, is_scene_cache_valid, load_scene_cache
from .tts.models import TTSRequest
from .tts.provider_manager import TTSProviderManager
from .voice_manifest import build_voice_manifest, read_voice_manifest
from .voice_policy import OUTPUT_MODE_DISABLED
from .voice_workflow import VOICE_STATES, is_final_generation_approved


# Extends, never mutates, the original 12-state VOICE_STATES from voice_workflow.py.
EXTENDED_VOICE_STATES = [*VOICE_STATES, "partially_completed", "blocked", "manual_audio_ready", "skipped"]


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _combined_settings(request: NarrationRequest) -> dict[str, Any]:
    settings = {**request.voice_profile.settings}
    if request.policy.speed is not None:
        settings.setdefault("speed", request.policy.speed)
    return settings


def _whole_script_request(request: NarrationRequest) -> TTSRequest:
    return TTSRequest(
        job_id=request.job_id,
        localization_id=request.localization_id,
        provider=request.voice_profile.provider,
        language=request.language,
        text=request.full_text,
        voice_id=request.voice_profile.voice_id,
        model_id=request.voice_profile.model_id,
        settings=_combined_settings(request),
    )


def approval_covers_request(request: NarrationRequest) -> bool:
    """Approval is granted once, against the whole narration text (matching today's
    audition/approve UX), not per scene - so validity is checked against a single
    synthetic whole-script TTSRequest, reusing the existing hash-bound approval check
    unchanged."""
    if not request.approval:
        return False
    return is_final_generation_approved(_whole_script_request(request), request.approval)


def _post_processing_config(request: NarrationRequest) -> PostProcessingConfig:
    allowed = {f.name for f in dataclasses.fields(PostProcessingConfig)}
    data = {key: value for key, value in (request.policy.post_processing or {}).items() if key in allowed}
    data.setdefault("sample_rate", request.policy.target_sample_rate)
    data.setdefault("channels", request.policy.target_channels)
    return PostProcessingConfig(**data)


def prepare_final(request: NarrationRequest, *, manager: TTSProviderManager) -> dict[str, Any]:
    """No paid call is performed here - only preflight (confirmed read-only for
    ElevenLabs), cache inspection, and approval-hash validation."""
    provider = manager.get(request.voice_profile.provider)
    preflight = provider.preflight(_whole_script_request(request))
    paths = generation_output_paths(request.output_root, request.language)
    cache = load_scene_cache(paths["scenes_dir"])
    cache_ready = sum(1 for scene in request.scenes if is_scene_cache_valid(cache.get(scene.scene_id), scene))
    approval_valid = approval_covers_request(request)
    character_count = sum(len(scene.text) for scene in request.scenes) or len(request.full_text)
    return {
        "provider": request.voice_profile.provider,
        "voice_profile": request.voice_profile.profile_id,
        "voice_name": request.voice_profile.display_name,
        "model_id": request.voice_profile.model_id,
        "character_count": character_count,
        "scene_count": len(request.scenes),
        "cache_ready_scenes": cache_ready,
        "cache_missing_scenes": len(request.scenes) - cache_ready,
        "approval_valid": approval_valid,
        "preflight": dataclasses.asdict(preflight),
        "ready_for_final_generation": approval_valid and not preflight.errors,
    }


def generate_final(request: NarrationRequest, *, manager: TTSProviderManager) -> dict[str, Any]:
    """The gated entrypoint: refuses via PermissionError unless the approval is valid
    for the current script/settings/voice/model/language, then chains scene generation
    -> narration assembly -> manifest write. Narration is only assembled (status
    "completed") once every scene succeeded; a partial failure leaves status
    "partially_completed" with successfully generated scenes preserved in cache."""
    paths = generation_output_paths(request.output_root, request.language)

    if request.policy.output_mode == OUTPUT_MODE_DISABLED or not request.policy.enabled:
        manifest = build_voice_manifest(request, status="skipped", scenes_meta=[], assembly=None, approval=request.approval)
        _write_json(paths["manifest"], manifest)
        return manifest

    if request.policy.approval_required and not approval_covers_request(request):
        raise PermissionError(
            "Final voice generation requires a valid approval matching the current "
            "script text, settings, voice, model, and language."
        )

    scenes_meta = generate_scenes(request, manager=manager, approved=True)
    all_completed = bool(scenes_meta) and all(scene["generation_status"] == "completed" for scene in scenes_meta)

    assembly = None
    status = "partially_completed" if scenes_meta else "failed"
    if all_completed:
        pause_policy = pause_policy_for_format(request.format_id)
        ordered_scenes = sorted(request.scenes, key=lambda scene: scene.scene_index)
        ordered_meta = sorted(scenes_meta, key=lambda scene: scene["scene_index"])
        scene_files = [Path(scene["output_path"]) for scene in ordered_meta]
        pauses = [
            pause_policy.clamp(
                scene.pause_after_sec if scene.pause_after_sec is not None else pause_policy.between_scenes_sec
            )
            for scene in ordered_scenes[:-1]
        ]
        assembly = assemble_narration(
            scene_files,
            pauses,
            target_sample_rate=request.policy.target_sample_rate,
            target_channels=request.policy.target_channels,
            output_path=paths["narration_wav"],
            post_processing=_post_processing_config(request),
        )
        status = "completed"

    manifest = build_voice_manifest(
        request,
        status=status,
        scenes_meta=scenes_meta,
        assembly=assembly,
        approval=request.approval,
        post_processing=_post_processing_config(request).to_dict(),
    )
    _write_json(paths["manifest"], manifest)
    return manifest


def invalidate_scenes(project_root: str | Path, language: str, changed_scene_ids: list[str]) -> None:
    """Marks only the listed scenes stale (deletes their cache sidecar so the next
    generate_final() call regenerates just those scenes) - never touches the rest."""
    paths = generation_output_paths(project_root, language)
    scenes_dir = paths["scenes_dir"]
    if not scenes_dir.exists():
        return
    changed = set(changed_scene_ids)
    for meta_path in scenes_dir.glob("*.json"):
        try:
            data = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if data.get("scene_id") in changed:
            meta_path.unlink(missing_ok=True)


@dataclasses.dataclass
class NarrationValidationResult:
    valid: bool
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"valid": self.valid, "reason": self.reason}


def validate_output(
    project_root: str | Path, language: str, *, expected_scene_count: int | None = None
) -> NarrationValidationResult:
    """The completed-gate: all required scenes present + duration>0 + checksum match +
    narration assembled. Reads the manifest via the tolerant read_voice_manifest()."""
    paths = generation_output_paths(project_root, language)
    if not paths["manifest"].is_file():
        return NarrationValidationResult(False, "manifest_missing")
    manifest = read_voice_manifest(paths["manifest"])
    scenes = manifest.get("scenes") or []
    if expected_scene_count is not None and len(scenes) != expected_scene_count:
        return NarrationValidationResult(False, "scene_count_mismatch")
    for scene in scenes:
        if scene.get("generation_status") != "completed":
            return NarrationValidationResult(False, f"scene_not_completed:{scene.get('scene_id')}")
        output_path = scene.get("output_path")
        if not output_path or not Path(output_path).is_file():
            return NarrationValidationResult(False, f"scene_file_missing:{scene.get('scene_id')}")
    narration = manifest.get("narration") or {}
    narration_path = narration.get("output_path")
    if not narration_path or not Path(narration_path).is_file():
        return NarrationValidationResult(False, "narration_missing")
    if float(narration.get("duration_sec") or 0) <= 0:
        return NarrationValidationResult(False, "narration_zero_duration")
    if narration.get("checksum_sha256") and checksum_sha256(narration_path) != narration["checksum_sha256"]:
        return NarrationValidationResult(False, "narration_checksum_mismatch")
    return NarrationValidationResult(True, "")
