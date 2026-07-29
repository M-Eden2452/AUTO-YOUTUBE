from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.content_creation import input_validation
from src.content_creation.models import (
    ContentCreationError,
    ContentCreationRequest,
    ContentCreationResult,
)
from src.content_creation.service_support import (
    ProgressCallback,
    notify,
    request_path_context,
)


_RETRYABLE_ARTICLE_REASONS = {
    "http_429",
    "timeout",
    "connection_error",
    "request_error",
}


def create_fullscreen_voiceover(
    request: ContentCreationRequest,
    template,
    progress_callback: ProgressCallback | None = None,
) -> ContentCreationResult:
    return FullscreenVoiceoverUseCase(
        request,
        template,
        progress_callback,
    ).execute()


class FullscreenVoiceoverUseCase:
    """Run the existing fullscreen workflow as explicit application phases."""

    def __init__(
        self,
        request: ContentCreationRequest,
        template,
        progress_callback: ProgressCallback | None = None,
    ) -> None:
        self.request = request
        self.template = template
        self.progress_callback = progress_callback
        self.projects_root = Path()
        self.store: Any = None
        self.job: Any = None
        self.root = Path()
        self.stages: list[dict[str, Any]] = []
        self.localization: Any = None
        self.voice_manifest_path = Path()
        self.existing_voice = ""
        self.requires_paid_approval = False
        self.approve_paid = False
        self.execute_voice = False
        self.approval_warning = ""
        self.voice_manifest: dict[str, Any] = {}
        self.voice_has_audio = False

    def execute(self) -> ContentCreationResult:
        self._prepare_project()
        if self.request.execution.dry_run:
            return self._dry_run_result()

        self._run_safe_pipeline()
        self._run_voice_stage()

        voice_gate_result = self._voice_gate_result()
        if voice_gate_result is not None:
            return voice_gate_result

        draft_result = self._draft_completion_result()
        if draft_result is not None:
            return draft_result

        self._run_subtitles()
        music_warnings = self._run_music()
        return self._render_and_export(music_warnings)

    def _prepare_project(self) -> None:
        from src.news.pipeline import create_news_to_short_job
        from src.news.project_store import NewsProjectStore

        request = self.request
        if not request.channel_id:
            raise ContentCreationError(
                "channel_id is required for fullscreen_voiceover_v1."
            )
        projects_root, fallback_roots, _channels_root = request_path_context(
            request
        )
        if request.execution.resume and request.project_id:
            from src.projects import ProjectRepository

            projects_root = ProjectRepository(
                projects_root,
                fallback_roots=fallback_roots,
            ).project_root(request.project_id).parent
        self.projects_root = projects_root
        self.store = NewsProjectStore(projects_root)
        url, topic, pasted_text, text_file = resolve_content_inputs(request)

        notify(self.progress_callback, "project_create", "running")
        if request.execution.resume and request.project_id:
            self.job = self.store.load_job(request.project_id)
            self._merge_visual_briefs()
        else:
            self.job = create_news_to_short_job(
                projects_root=projects_root,
                channel_id=request.channel_id,
                url=url,
                title=request.title or None,
                topic=topic,
                text=pasted_text,
                text_file=text_file,
                language=request.language or "ru",
                target_duration_sec=int(
                    request.target_duration_sec
                    or request.project_overrides.get("target_duration_sec", 55)
                ),
                script_source=resolve_script_source(request),
                script_provider=str(
                    request.project_overrides.get("script_provider", "") or ""
                ),
                visual_briefs=dict(request.visual_briefs),
                completion_mode=request.completion_mode,
                script_adaptation=request.script_adaptation,
            )
        self.root = self.store.project_root(self.job.job_id)
        notify(self.progress_callback, "project_create", "completed")

    def _merge_visual_briefs(self) -> None:
        if not self.request.visual_briefs:
            return
        self.job.visual_briefs = {
            **self.job.visual_briefs,
            **{
                str(key): dict(value)
                for key, value in self.request.visual_briefs.items()
            },
        }
        self.store.save_job(self.job)

    def _dry_run_result(self) -> ContentCreationResult:
        from src.news.pipeline import run_news_to_short_job

        result = run_news_to_short_job(
            projects_root=self.projects_root,
            job_id=self.job.job_id,
            dry_run=True,
            completion_mode=self.request.completion_mode,
            script_adaptation=self.request.script_adaptation,
        )
        return ContentCreationResult(
            status="dry_run_completed",
            project_id=self.job.job_id,
            project_root=str(self.root),
            stages=[
                {"stage": stage, "status": "completed"}
                for stage in result.completed_stages
            ],
            rerun_commands=[
                fullscreen_rerun_command(self.request, self.job.job_id)
            ],
        )

    def _run_safe_pipeline(self) -> None:
        from src.news.article_ingestor import ArticleIngestionError
        from src.news.pipeline import run_news_to_short_job

        notify(self.progress_callback, "script_and_research", "running")
        try:
            result = run_news_to_short_job(
                projects_root=self.projects_root,
                job_id=self.job.job_id,
                until_stage="asset_search",
                resume=True,
                force_stage=bool(self.request.execution.force_stage),
                completion_mode=self.request.completion_mode,
                script_adaptation=self.request.script_adaptation,
            )
        except ArticleIngestionError as exc:
            notify(self.progress_callback, "script_and_research", "failed")
            raise ContentCreationError(
                str(exc),
                reason=exc.reason,
                retryable=exc.reason in _RETRYABLE_ARTICLE_REASONS,
            ) from exc
        self.stages.extend(
            {"stage": stage, "status": "completed"}
            for stage in result.completed_stages
        )
        self.job = self.store.load_job(self.job.job_id)
        notify(self.progress_callback, "script_and_research", "completed")

    def _run_voice_stage(self) -> None:
        from src.news.pipeline import run_news_to_short_job

        request = self.request
        self.voice_manifest_path = (
            self.root
            / "localizations"
            / self.job.language
            / "voice"
            / "voice_manifest.json"
        )
        self.localization = resolve_localization(
            root=self.root,
            job=self.job,
            request=request,
        )
        if self.localization is not None:
            self.existing_voice = self.localization.existing_narration_path
        else:
            self.existing_voice = completed_narration(
                self.store,
                self.voice_manifest_path,
            )

        self.requires_paid_approval = (
            request.voice.provider == "elevenlabs" and not self.existing_voice
        )
        self.approve_paid = (
            bool(request.voice.approve_paid_generation)
            and self.requires_paid_approval
        )
        self.execute_voice = self.approve_paid
        if self.execute_voice:
            self.approval_warning = create_paid_voice_approval(
                root=self.root,
                job=self.job,
                request=request,
                localization=self.localization,
            )

        if self.existing_voice:
            notify(
                self.progress_callback,
                "voice",
                "skipped_existing_audio",
            )
        else:
            notify(self.progress_callback, "voice", "running")
            run_news_to_short_job(
                projects_root=self.projects_root,
                job_id=self.job.job_id,
                stage="voice",
                execute_voice=self.execute_voice,
                voice_profile_override=request.voice.profile or None,
            )
            self.job = self.store.load_job(self.job.job_id)

        self._import_manual_audio()
        self._read_and_record_voice_result()

    def _import_manual_audio(self) -> None:
        request = self.request
        if request.voice.provider != "audio_file" or not request.voice.audio_file:
            return
        from src.audio.voice_workflow import import_manual_audio

        import_manual_audio(
            project_root=self.root,
            job_id=self.job.job_id,
            language=self.job.language,
            audio_file=request.voice.audio_file,
        )
        self.stages.append(
            {"stage": "manual_audio_import", "status": "completed"}
        )

    def _read_and_record_voice_result(self) -> None:
        if self.voice_manifest_path.exists():
            self.voice_manifest = self.store.read_json(
                self.voice_manifest_path
            )
        voice_audio_path = str(self.voice_manifest.get("audio_path") or "")
        self.voice_has_audio = bool(voice_audio_path) and Path(
            voice_audio_path
        ).is_file()
        if self.voice_has_audio:
            self._synchronize_voice_stage()

        if self.existing_voice:
            voice_stage_status = "skipped_existing_audio"
        else:
            voice_stage_status = (
                "completed" if self.voice_has_audio else "needs_review"
            )
        self.stages.append(
            {
                "stage": "voice",
                "status": voice_stage_status,
                "execute_voice": self.execute_voice,
                "audio_path": self.voice_manifest.get("audio_path", ""),
            }
        )
        if not self.existing_voice:
            notify(self.progress_callback, "voice", voice_stage_status)

    def _synchronize_voice_stage(self) -> None:
        self.job = self.store.load_job(self.job.job_id)
        voice_status = str(
            self.voice_manifest.get("voice_stage_status") or "completed"
        )
        localization_state = self.job.localizations.get(self.job.language)
        if localization_state is not None:
            localization_state.voice_status = voice_status
        if self.job.status == "voice_provider_required":
            self.job.status = "in_progress"
        self.store.update_stage(
            self.job,
            "voice",
            status="completed",
            result_path=str(self.voice_manifest_path),
        )

    def _voice_gate_result(self) -> ContentCreationResult | None:
        request = self.request
        if request.execution.prepare_only or (
            self.requires_paid_approval and not self.approve_paid
        ):
            notify(self.progress_callback, "paid_approval", "pending")
            preflight_summary: dict[str, Any] = {}
            if self.requires_paid_approval:
                preflight_summary = build_paid_preflight_summary(
                    root=self.root,
                    job=self.job,
                    request=request,
                    localization=self.localization,
                )
            gate_warnings = [
                "Paid ElevenLabs generation was NOT performed. Re-run with --approve-paid-generation "
                "to synthesize scene audio and continue to final_render.",
            ]
            if (
                self.localization is not None
                and self.localization.fallback_reason
            ):
                gate_warnings.append(self.localization.fallback_reason)
            return ContentCreationResult(
                status="prepared_awaiting_paid_approval",
                project_id=self.job.job_id,
                project_root=str(self.root),
                stages=self.stages,
                output_paths={
                    "voice_manifest": str(self.voice_manifest_path)
                },
                warnings=gate_warnings,
                evidence={
                    "character_count": self.voice_manifest.get(
                        "character_count",
                        0,
                    ),
                    "provider": request.voice.provider,
                    "voice_profile": request.voice.profile,
                    **preflight_summary,
                },
                rerun_commands=[
                    fullscreen_rerun_command(
                        request,
                        self.job.job_id,
                        approve=True,
                    )
                ],
            )

        if self.execute_voice and not self.voice_has_audio:
            warnings = (
                [self.approval_warning] if self.approval_warning else []
            )
            warnings.append(
                "Paid generation was approved but no audio was produced; voice_manifest is still "
                f"status={self.voice_manifest.get('status', 'unknown')!r}. Check that the channel has a "
                "configured voices.yaml voice profile."
            )
            return ContentCreationResult(
                status="needs_review",
                project_id=self.job.job_id,
                project_root=str(self.root),
                stages=self.stages,
                output_paths={
                    "voice_manifest": str(self.voice_manifest_path)
                },
                warnings=warnings,
                evidence={
                    "character_count": self.voice_manifest.get(
                        "character_count",
                        0,
                    ),
                    "provider": request.voice.provider,
                    "voice_profile": request.voice.profile,
                },
                rerun_commands=[
                    fullscreen_rerun_command(
                        request,
                        self.job.job_id,
                        approve=True,
                    )
                ],
            )
        return None

    def _draft_completion_result(self) -> ContentCreationResult | None:
        from src.assets.completion import MODE_DRAFT_COMPLETE
        from src.news.models import completion_settings

        if (
            completion_settings(self.job).get("mode") != MODE_DRAFT_COMPLETE
            or self.voice_has_audio
        ):
            return None
        from src.news.draft_completion import write_completion_report

        report_paths = write_completion_report(
            root=self.root,
            job=self.job,
        )
        self.job.status = "voice_provider_required"
        self.store.save_job(self.job)
        return ContentCreationResult(
            status="voice_provider_required",
            project_id=self.job.job_id,
            project_root=str(self.root),
            stages=self.stages,
            output_paths={
                "voice_manifest": str(self.voice_manifest_path),
                "replacement_report": report_paths.get("json_path", ""),
                "replacement_report_html": report_paths.get("html_path", ""),
            },
            warnings=[
                "Visual assembly and replacement report are saved. Configure a voice "
                "provider or import narration audio, then resume rendering."
            ],
            rerun_commands=[
                fullscreen_rerun_command(self.request, self.job.job_id)
            ],
        )

    def _run_subtitles(self) -> None:
        if self.request.subtitles.style == "disabled":
            return
        from src.news.pipeline import run_news_to_short_job

        notify(self.progress_callback, "subtitles", "running")
        run_news_to_short_job(
            projects_root=self.projects_root,
            job_id=self.job.job_id,
            stage="subtitles",
        )
        self.stages.append(
            {"stage": "subtitles", "status": "completed"}
        )
        notify(self.progress_callback, "subtitles", "completed")

    def _run_music(self) -> list[str]:
        request = self.request
        if request.music.mode != "local_file" or not request.music.path:
            return []
        from src.audio.music_manifest import (
            MusicManifestError,
            prepare_project_music,
        )

        notify(self.progress_callback, "music", "running")
        try:
            prepare_project_music(
                self.root,
                request.music.path,
                volume=request.music.volume,
            )
            self.stages.append(
                {"stage": "music", "status": "completed"}
            )
            notify(self.progress_callback, "music", "completed")
            return []
        except MusicManifestError as exc:
            self.stages.append(
                {"stage": "music", "status": "needs_review"}
            )
            notify(self.progress_callback, "music", "needs_review")
            return [f"Музыка не добавлена: {exc}"]

    def _render_and_export(
        self,
        music_warnings: list[str],
    ) -> ContentCreationResult:
        from src.news.pipeline import run_news_to_short_job

        run_news_to_short_job(
            projects_root=self.projects_root,
            job_id=self.job.job_id,
            stage="preview_render",
        )
        self.stages.append(
            {"stage": "preview_render", "status": "completed"}
        )

        quality_path = self.root / "quality" / "quality_report.json"
        notify(self.progress_callback, "render", "running")
        run_news_to_short_job(
            projects_root=self.projects_root,
            job_id=self.job.job_id,
            stage="quality_check",
        )
        quality_report = (
            self.store.read_json(quality_path)
            if quality_path.exists()
            else {}
        )
        self.stages.append(
            {
                "stage": "quality_check",
                "status": quality_report.get("status", "unknown"),
            }
        )

        run_news_to_short_job(
            projects_root=self.projects_root,
            job_id=self.job.job_id,
            stage="final_render",
        )
        final_manifest_path = (
            self.root / "render" / "final_render_manifest.json"
        )
        final_manifest = (
            self.store.read_json(final_manifest_path)
            if final_manifest_path.exists()
            else {}
        )
        render_ok = (
            bool(final_manifest.get("output_path"))
            and final_manifest.get("status") != "blocked"
        )
        render_stage_status = (
            "completed"
            if render_ok
            else (final_manifest.get("status") or "blocked")
        )
        self.stages.append(
            {"stage": "final_render", "status": render_stage_status}
        )

        final_result = run_news_to_short_job(
            projects_root=self.projects_root,
            job_id=self.job.job_id,
            stage="export",
        )
        self.stages.append(
            {
                "stage": "export",
                "status": "completed" if render_ok else "skipped",
            }
        )
        notify(self.progress_callback, "render", render_stage_status)

        output_paths = self._render_output_paths(
            render_ok=render_ok,
            final_manifest=final_manifest,
        )
        return ContentCreationResult(
            status=final_result.status,
            project_id=self.job.job_id,
            project_root=str(self.root),
            stages=self.stages,
            output_paths=output_paths,
            warnings=music_warnings,
            quality_report=quality_report,
            rerun_commands=[
                fullscreen_rerun_command(
                    self.request,
                    self.job.job_id,
                    approve=True,
                )
            ],
        )

    def _render_output_paths(
        self,
        *,
        render_ok: bool,
        final_manifest: dict[str, Any],
    ) -> dict[str, Any]:
        output_paths: dict[str, Any] = {}
        if render_ok:
            output_paths["final_video"] = final_manifest["output_path"]
            output_paths["outputs"] = final_manifest.get("outputs", {})
        replacement_root = self.root / "replacement"
        replacement_json = replacement_root / "replacement_report.json"
        replacement_html = replacement_root / "replacement_report.html"
        if replacement_json.is_file():
            output_paths["replacement_report"] = str(replacement_json)
        if replacement_html.is_file():
            output_paths["replacement_report_html"] = str(replacement_html)
        return output_paths


def resolve_content_inputs(
    request: ContentCreationRequest,
) -> tuple[str | None, str | None, str | None, str | None]:
    mode = request.content_input_mode
    url = request.source_url or None
    topic = request.topic or request.title or None
    text = request.pasted_script or None
    text_file = request.script_path or None

    if mode == "topic":
        return None, topic, None, None
    if mode == "article_url":
        result = input_validation.validate_article_url(request.source_url)
        if not result.valid:
            raise ContentCreationError(result.message, reason=result.reason)
        return url, None, None, None
    if mode == "pasted_script":
        result = input_validation.validate_pasted_script(
            request.pasted_script
        )
        if not result.valid:
            raise ContentCreationError(result.message, reason=result.reason)
        return None, None, text, None
    if mode == "script_file":
        result = input_validation.validate_script_file(request.script_path)
        if not result.valid:
            raise ContentCreationError(result.message, reason=result.reason)
        return None, None, None, text_file
    if url:
        result = input_validation.validate_article_url(request.source_url)
        if not result.valid:
            raise ContentCreationError(result.message, reason=result.reason)
    return url, topic, text, text_file


def resolve_script_source(request: ContentCreationRequest) -> str:
    from src.content.script_engine import SOURCE_USER_SCRIPT

    if request.content_input_mode in {"pasted_script", "script_file"}:
        return SOURCE_USER_SCRIPT
    return ""


def resolve_localization(
    *,
    root: Path,
    job,
    request: ContentCreationRequest,
):
    from src.news.voice_adapter import resolve_localization_for_channel

    projects_root, fallback_roots, channels_root = request_path_context(request)
    return resolve_localization_for_channel(
        channel_id=request.channel_id,
        language=job.language,
        project_root=root,
        project_id=job.job_id,
        projects_dir=projects_root,
        projects_fallback_dirs=fallback_roots,
        channels_dir=channels_root,
        voice_profile_override=request.voice.profile or None,
        manual_audio_path=request.voice.audio_file or "",
        script_path=str(
            root
            / "localizations"
            / job.language
            / "script"
            / "script.json"
        ),
    )


def build_paid_preflight_summary(
    *,
    root: Path,
    job,
    request: ContentCreationRequest,
    localization=None,
) -> dict[str, Any]:
    from src.audio.narration_workflow import prepare_final
    from src.audio.tts.audio_file_provider import AudioFileProvider
    from src.audio.tts.elevenlabs_provider import ElevenLabsProvider
    from src.audio.tts.provider_manager import TTSProviderManager
    from src.news.voice_adapter import (
        load_approval,
        script_to_narration_request,
    )

    script_path = (
        root
        / "localizations"
        / job.language
        / "script"
        / "script.json"
    )
    if not script_path.is_file():
        return {}

    resolved = resolve_voice_inputs(
        root=root,
        job=job,
        request=request,
        localization=localization,
    )
    if resolved is None:
        return {}
    policy, profile = resolved

    script_data = json.loads(script_path.read_text(encoding="utf-8"))
    approval = load_approval(root, job.language)
    narration_request = script_to_narration_request(
        script=script_data,
        project_root=root,
        job_id=job.job_id,
        channel_id=request.channel_id,
        language=job.language,
        policy=policy,
        voice_profile=profile,
        approval=approval,
    )
    manager = TTSProviderManager()
    manager.register(ElevenLabsProvider())
    manager.register(AudioFileProvider())
    try:
        summary = prepare_final(narration_request, manager=manager)
    except Exception as exc:
        return {"preflight_error": str(exc)}

    summary["target_duration_sec"] = script_data.get(
        "target_duration_sec",
        job.target_duration_sec,
    )
    summary["estimated_duration_sec"] = script_data.get(
        "estimated_duration_sec"
    )
    summary["word_count"] = len(
        (script_data.get("narration_text") or "").split()
    )
    summary["expected_credits"] = (
        summary.get("character_count", 0)
        if summary.get("model_id") == "eleven_multilingual_v2"
        else None
    )
    if localization is not None:
        summary["language"] = localization.language
        summary["locale"] = localization.locale
        summary["narration_source"] = localization.narration_source
        summary["fallback_policy"] = localization.fallback_policy
        summary["secret_configured"] = localization.secret_configured
        summary["tts_blocked_reason"] = localization.tts_blocked_reason
    return summary


def resolve_voice_inputs(
    *,
    root: Path,
    job,
    request: ContentCreationRequest,
    localization=None,
):
    from src.audio.voice_profile_registry import VoiceProfileRegistryError
    from src.news.pipeline import (
        _load_channel_voice_config,
        _load_channel_workflow_config,
    )
    from src.news.voice_adapter import (
        load_voice_profile_for_channel,
        resolve_voice_policy_for_channel,
    )

    if (
        localization is not None
        and localization.policy is not None
        and localization.voice_profile is not None
    ):
        return localization.policy, localization.voice_profile

    channel_voice_config = _load_channel_voice_config(request.channel_id)
    channel_workflow_config = _load_channel_workflow_config(
        request.channel_id
    )
    policy = resolve_voice_policy_for_channel(
        channel_voice_config,
        channel_workflow_config,
    )
    try:
        profile = load_voice_profile_for_channel(
            request.channel_id,
            channel_voice_config,
            profile_override=request.voice.profile or None,
        )
    except VoiceProfileRegistryError:
        return None
    return policy, profile


def create_paid_voice_approval(
    *,
    root: Path,
    job,
    request: ContentCreationRequest,
    localization=None,
) -> str:
    from datetime import datetime, timezone

    from src.audio.narration_workflow import _combined_settings
    from src.audio.voice_workflow import create_voice_approval_record
    from src.news.voice_adapter import script_to_narration_request

    resolved = resolve_voice_inputs(
        root=root,
        job=job,
        request=request,
        localization=localization,
    )
    if resolved is None:
        return (
            f"Could not resolve a voice profile for channel "
            f"{request.channel_id!r}."
        )
    policy, profile = resolved

    script_path = (
        root
        / "localizations"
        / job.language
        / "script"
        / "script.json"
    )
    script_data = (
        json.loads(script_path.read_text(encoding="utf-8"))
        if script_path.is_file()
        else {}
    )
    narration_request = script_to_narration_request(
        script=script_data,
        project_root=root,
        job_id=job.job_id,
        channel_id=request.channel_id,
        language=job.language,
        policy=policy,
        voice_profile=profile,
        approval=None,
    )
    settings = _combined_settings(narration_request)

    create_voice_approval_record(
        project_root=root,
        language=job.language,
        scope="job",
        provider=profile.provider,
        voice_id=profile.voice_id,
        voice_name=profile.display_name,
        model_id=profile.model_id,
        script_text=narration_request.full_text,
        settings=settings,
        approved_at=datetime.now(timezone.utc).isoformat(),
        approved_by="content_creation_wizard",
    )
    return ""


def completed_narration(store, voice_manifest_path: Path) -> str:
    if not voice_manifest_path.exists():
        return ""
    try:
        manifest = store.read_json(voice_manifest_path)
    except (OSError, ValueError):
        return ""
    audio_path = str(manifest.get("audio_path") or "")
    if not audio_path or not Path(audio_path).is_file():
        return ""
    return audio_path


def fullscreen_rerun_command(
    request: ContentCreationRequest,
    job_id: str,
    *,
    approve: bool = False,
) -> str:
    parts = [
        "./venv/Scripts/python.exe -m ai_youtube create",
        "--format vertical_short",
        "--template fullscreen_voiceover_v1",
        f"--channel {request.channel_id}",
        f"--language {request.language}",
        f"--resume --project-id {job_id}",
    ]
    if request.completion_mode:
        parts.append(f"--completion-mode {request.completion_mode}")
    if request.script_adaptation:
        parts.append(f"--script-adaptation {request.script_adaptation}")
    if request.voice.provider:
        parts.append(f"--voice-provider {request.voice.provider}")
    if request.voice.profile:
        parts.append(f'--voice-profile "{request.voice.profile}"')
    if approve:
        parts.append("--approve-paid-generation")
    return " ".join(parts)
