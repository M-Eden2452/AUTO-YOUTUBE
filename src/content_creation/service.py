from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from src.content_creation import input_validation
from src.content_creation.models import ContentCreationError, ContentCreationRequest, ContentCreationResult
from src.production_catalog.catalog import get_default_catalog
from src.production_catalog.models import CatalogValidationError
from src.project_foundation.channels import ChannelRegistry
from src.project_foundation.models import ProjectFoundationError
from src.project_foundation.projects import ProjectFactory
from src.templates.story_card.integration import (
    STORY_CARD_CANONICAL_TEMPLATE_ID,
    StoryCardIntegrationError,
    prepare_story_card_render,
)

FULLSCREEN_VOICEOVER_TEMPLATE_ID = "fullscreen_voiceover_v1"

ProgressCallback = Callable[[str, str], None]

# Reasons from src.news.article_ingestor.ArticleIngestionError that are transient/
# network-side (worth offering "retry") vs. content/input-side (retrying the exact
# same input would fail again the same way).
_RETRYABLE_ARTICLE_REASONS = {"http_429", "timeout", "connection_error", "request_error"}


def _notify(callback: ProgressCallback | None, stage: str, status: str) -> None:
    if callback is not None:
        callback(stage, status)

# The two templates this application layer actually knows how to create today.
# Anything else in the catalog is architecture-supported only (see
# src.content_creation.capabilities.TEMPLATE_TESTED_STATUS) and raises a clear
# ContentCreationError rather than silently doing nothing.
_SUPPORTED_TEMPLATE_IDS = {STORY_CARD_CANONICAL_TEMPLATE_ID, FULLSCREEN_VOICEOVER_TEMPLATE_ID}


def _resolve_template(request: ContentCreationRequest):
    catalog = get_default_catalog()
    template_query = request.template_id
    if not template_query and request.channel_id:
        try:
            channel = ChannelRegistry().get(request.channel_id)
            template_query = channel.default_template
        except ProjectFoundationError:
            template_query = ""
    if not template_query:
        raise ContentCreationError("template_id is required (explicitly, or via the channel's default_template).")
    try:
        template = catalog.templates.get(template_query)
    except CatalogValidationError as exc:
        raise ContentCreationError(str(exc)) from exc
    if request.format_id and request.format_id != template.format_id:
        raise ContentCreationError(
            f"format_id {request.format_id!r} is not compatible with template "
            f"{template.template_id!r} (expects {template.format_id!r})."
        )
    return template


def _validate_music_request(request: ContentCreationRequest) -> None:
    if request.music.mode == "disabled":
        return
    if request.music.mode == "local_file":
        result = input_validation.validate_music_path(request.music.path)
        if not result.valid:
            raise ContentCreationError(result.message, reason=result.reason)
        return
    raise ContentCreationError(f"Unknown music mode: {request.music.mode!r}.", reason="invalid_music_mode")


def create_content(
    request: ContentCreationRequest, *, progress_callback: ProgressCallback | None = None
) -> ContentCreationResult:
    """Coordinate existing foundation components to create one piece of content.

    Routes by the resolved template_id to whichever real, tested implementation
    backs it - this deliberately does not invent a third project-storage system:
    story_card_text_only_v1 uses src.project_foundation (ProjectFactory/ChannelProfile)
    + src.templates.story_card.integration, exactly as validated by
    tests/test_story_card_project_integration.py; fullscreen_voiceover_v1 uses
    src.news.pipeline (NewsJob/NewsProjectStore), exactly as validated by the live
    crow-video run and tests/test_news_voice_adapter.py.

    progress_callback(stage, status), if given, is invoked as each stage starts/
    completes (status in {"running", "completed"}) - purely a UI hook for the
    terminal wizard's live progress display; the returned ContentCreationResult
    always carries the same `stages` list regardless of whether one is passed.
    """
    template = _resolve_template(request)
    _validate_music_request(request)
    canonical_template_id = template.template_id

    if canonical_template_id == STORY_CARD_CANONICAL_TEMPLATE_ID:
        return _create_story_card(request, template, progress_callback)
    if canonical_template_id == FULLSCREEN_VOICEOVER_TEMPLATE_ID:
        return _create_fullscreen_voiceover(request, template, progress_callback)
    raise ContentCreationError(
        f"template {canonical_template_id!r} is registered in the production catalog "
        f"(implementation_status={template.implementation_status!r}) but has no create "
        f"workflow implemented yet - it is architecture-supported only."
    )


def _create_story_card(
    request: ContentCreationRequest, template, progress_callback: ProgressCallback | None = None
) -> ContentCreationResult:
    if not request.channel_id:
        raise ContentCreationError("channel_id is required for story_card_text_only_v1.")
    if not request.source_asset_path:
        raise ContentCreationError(
            "source_asset_path is required for story_card_text_only_v1 (asset search is not "
            "wired into this workflow yet - pass a local video file with --source-asset)."
        )
    channel = ChannelRegistry().get(request.channel_id)
    factory = ProjectFactory(base_dir=request.project_overrides.get("projects_root", "projects"))
    dry_run = bool(request.execution.dry_run)

    _notify(progress_callback, "project_create", "running")
    if request.execution.resume and request.project_id:
        manifest = factory.get(request.project_id)
        created_paths: list[str] = []
    else:
        creation = factory.create(
            channel,
            title=request.title or request.topic or "story_card",
            project_id=request.project_id or None,
            application_id=template.application_id,
            format_id=template.format_id,
            template_id=template.template_id,
            language=request.language or channel.default_language,
            dry_run=dry_run,
        )
        manifest = creation.manifest
        created_paths = creation.created_paths
    _notify(progress_callback, "project_create", "completed")

    if dry_run:
        return ContentCreationResult(
            status="dry_run_completed",
            project_id=manifest.project_id,
            project_root=manifest.project_root,
            stages=[{"stage": "project_create", "status": "dry_run"}],
            output_paths={},
            rerun_commands=[_story_card_rerun_command(request)],
        )

    _notify(progress_callback, "render", "running")
    try:
        render_result = prepare_story_card_render(
            manifest,
            channel=channel,
            source_asset_path=request.source_asset_path,
            text=request.text,
            dry_run=False,
            render=not request.execution.prepare_only,
            allow_overwrite=bool(request.project_overrides.get("allow_overwrite", False)),
        )
    except StoryCardIntegrationError as exc:
        _notify(progress_callback, "render", "failed")
        return ContentCreationResult(
            status="failed",
            project_id=manifest.project_id,
            project_root=manifest.project_root,
            errors=[str(exc)],
            rerun_commands=[_story_card_rerun_command(request)],
        )
    _notify(progress_callback, "render", "completed")

    status = {
        "dry_run": "dry_run_completed",
        "prepared": "prepared_awaiting_render",
        "rendered": "completed",
        "skipped_existing_output": "skipped_existing_output",
        "failed": "failed",
    }.get(render_result.render_status, render_result.render_status)

    output_paths: dict[str, Any] = {}
    if render_result.render_status == "rendered":
        output_paths["final_video"] = render_result.output_path
    output_paths["render_request"] = render_result.render_request_path

    # A short, honest rights line in the normal output; the full licence detail stays
    # in `project rights-report` rather than bloating every successful run.
    evidence = dict(render_result.metadata.get("evidence") or {})
    if evidence.get("evidence_manifest_path"):
        output_paths["evidence_manifest"] = evidence["evidence_manifest_path"]

    return ContentCreationResult(
        status=status,
        project_id=manifest.project_id,
        project_root=manifest.project_root,
        stages=[{"stage": "story_card_render", "status": render_result.render_status}],
        output_paths=output_paths,
        warnings=list(render_result.warnings),
        errors=[] if render_result.render_status != "failed" else ["story_card render failed; see metadata.render_manifest."],
        evidence=evidence,
        quality_report={},
        rerun_commands=[_story_card_rerun_command(request)],
    )


def _story_card_rerun_command(request: ContentCreationRequest) -> str:
    parts = [
        "./venv/Scripts/python.exe -m src.content_creation.cli create",
        "--format vertical_short",
        "--template story_card_text_only_v1",
        f"--channel {request.channel_id}",
        f"--language {request.language}",
    ]
    if request.text.get("top"):
        parts.append(f'--text "{request.text["top"]}"')
    if request.source_asset_path:
        parts.append(f"--source-asset {request.source_asset_path}")
    parts.append("--voice-provider disabled --subtitles disabled")
    return " ".join(parts)


def _resolve_content_inputs(request: ContentCreationRequest) -> tuple[str | None, str | None, str | None, str | None]:
    """Return (url, topic, pasted_text, text_file) for create_news_to_short_job,
    honoring content_input_mode when set so exactly one source is ever active -
    e.g. a stray --topic left over from a previous wizard step never leaks into
    an article_url run. Falls back to the old "whichever flag is non-empty"
    behavior when content_input_mode is unset, for CLI backward compatibility.
    """
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
        result = input_validation.validate_pasted_script(request.pasted_script)
        if not result.valid:
            raise ContentCreationError(result.message, reason=result.reason)
        return None, None, text, None
    if mode == "script_file":
        result = input_validation.validate_script_file(request.script_path)
        if not result.valid:
            raise ContentCreationError(result.message, reason=result.reason)
        return None, None, None, text_file
    # Legacy/unspecified mode: still reject an obvious search-engine URL before
    # any network call if one was passed directly via --source-url.
    if url:
        result = input_validation.validate_article_url(request.source_url)
        if not result.valid:
            raise ContentCreationError(result.message, reason=result.reason)
    return url, topic, text, text_file


def _resolve_script_source(request: ContentCreationRequest) -> str:
    """Map the UI's content_input_mode onto a script-engine source kind.

    Only pasted_script/script_file are finished scripts. topic and article_url go
    through research as before, so their behaviour is unchanged.
    """
    from src.content.script_engine import SOURCE_USER_SCRIPT

    if request.content_input_mode in {"pasted_script", "script_file"}:
        return SOURCE_USER_SCRIPT
    return ""


def _resolve_localization(*, root: Path, job, request: ContentCreationRequest):
    """The one resolved localization this whole workflow uses.

    Before D2 the policy and the voice profile were resolved separately in three
    places (the voice stage, the preflight summary, the approval writer), so a
    channel-language voice could in principle disagree between them. They now all
    read this. Returns None only when the channel is unknown to the resolver, in
    which case each call site keeps its own legacy readers.

    ``request.voice.provider`` is deliberately NOT passed as a runtime override:
    ``VoiceRequestConfig.provider`` defaults to "disabled", and treating that default
    as an explicit choice would silently switch off narration on a template that
    requires it. The paid-approval gate below still keys on it, exactly as before.
    """
    from src.news.voice_adapter import resolve_localization_for_channel

    projects_root = Path(request.project_overrides.get("projects_root", "projects"))
    return resolve_localization_for_channel(
        channel_id=request.channel_id,
        language=job.language,
        project_root=root,
        project_id=job.job_id,
        projects_dir=projects_root,
        voice_profile_override=request.voice.profile or None,
        manual_audio_path=request.voice.audio_file or "",
        script_path=str(root / "localizations" / job.language / "script" / "script.json"),
    )


def _build_paid_preflight_summary(
    *, root: Path, job, request: ContentCreationRequest, localization=None
) -> dict[str, Any]:
    """Read-only, no-cost summary shown before the paid gate: takes the profile and the
    policy from the resolved localization (src.localization), then reuses the existing,
    unmodified src.audio.narration_workflow.prepare_final for display_name/model_id/
    character_count/scene_count/cache state and a provider preflight (confirmed
    read-only for ElevenLabsProvider elsewhere in this codebase - never calls the
    synthesis endpoint). Also adds target_duration_sec/estimated_duration_sec/word_count
    read straight off script.json, and expected_credits (eleven_multilingual_v2 only:
    1 character = 1 credit per ElevenLabs pricing; None for any other model since the
    rate is unknown).

    Returns {} if it can't be built yet (script not written, no resolvable profile) -
    this is purely informational and must never block or crash the approval-gate result.
    """
    from src.audio.narration_workflow import prepare_final
    from src.audio.tts.audio_file_provider import AudioFileProvider
    from src.audio.tts.elevenlabs_provider import ElevenLabsProvider
    from src.audio.tts.provider_manager import TTSProviderManager
    from src.news.voice_adapter import load_approval, script_to_narration_request

    script_path = root / "localizations" / job.language / "script" / "script.json"
    if not script_path.is_file():
        return {}

    resolved = _resolve_voice_inputs(root=root, job=job, request=request, localization=localization)
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

    summary["target_duration_sec"] = script_data.get("target_duration_sec", job.target_duration_sec)
    summary["estimated_duration_sec"] = script_data.get("estimated_duration_sec")
    summary["word_count"] = len((script_data.get("narration_text") or "").split())
    summary["expected_credits"] = (
        summary.get("character_count", 0) if summary.get("model_id") == "eleven_multilingual_v2" else None
    )
    if localization is not None:
        # Why the paid call is or is not possible, in the same summary the CLI prints -
        # secret presence is a bool, never the key itself.
        summary["language"] = localization.language
        summary["locale"] = localization.locale
        summary["narration_source"] = localization.narration_source
        summary["fallback_policy"] = localization.fallback_policy
        summary["secret_configured"] = localization.secret_configured
        summary["tts_blocked_reason"] = localization.tts_blocked_reason
    return summary


def _resolve_voice_inputs(*, root: Path, job, request: ContentCreationRequest, localization=None):
    """``(policy, voice_profile)`` for this run, or None if no profile resolves.

    Prefers the resolved localization; falls back to the pre-D2 readers for a channel
    the resolver does not know, so a channel that worked before keeps working.
    """
    from src.audio.voice_profile_registry import VoiceProfileRegistryError
    from src.news.pipeline import _load_channel_voice_config, _load_channel_workflow_config
    from src.news.voice_adapter import load_voice_profile_for_channel, resolve_voice_policy_for_channel

    if localization is not None and localization.policy is not None and localization.voice_profile is not None:
        return localization.policy, localization.voice_profile

    channel_voice_config = _load_channel_voice_config(request.channel_id)
    channel_workflow_config = _load_channel_workflow_config(request.channel_id)
    policy = resolve_voice_policy_for_channel(channel_voice_config, channel_workflow_config)
    try:
        profile = load_voice_profile_for_channel(
            request.channel_id, channel_voice_config, profile_override=request.voice.profile or None
        )
    except VoiceProfileRegistryError:
        return None
    return policy, profile


def _create_paid_voice_approval(*, root: Path, job, request: ContentCreationRequest, localization=None) -> str:
    """Write the approval.json that src.audio.voice_workflow/narration_workflow actually
    gate on (is_final_generation_approved / approval_covers_request).

    Without this, build_or_generate_voice_manifest(execute=True) in src/news/voice_stage.py
    calls load_approval() first; if no approval.json exists on disk it silently falls back
    to the unconfigured stub manifest (status=provider_selection_required, audio_path="")
    even when the caller passed execute_voice=True - this was the actual point where the
    wizard's confirmed "Yes" to paid generation got lost. This function never touches
    ElevenLabsProvider or narration_workflow.py themselves; it only writes the approval
    record via the existing, unmodified src.audio.voice_workflow.create_voice_approval_record.

    Returns "" on success, or a short warning message if no voice profile could be
    resolved at all - neither this channel's own voices.yaml nor (when an explicit
    request.voice.profile was given) any other channel's voices.yaml has it. In that
    case execute_voice is left to fall back to the existing safe/stub behavior, unchanged.

    An explicit request.voice.profile (e.g. --voice-profile ru_dom from the CLI/wizard)
    always takes priority over the channel's own configured default, and is resolved
    globally (see src.news.voice_adapter.load_voice_profile_for_channel) - a channel
    with no voices.yaml of its own (e.g. nature_pulse) can still use it. Since D2 the
    profile and the policy come from the same resolved localization the voice stage
    uses, so the approval can no longer be written against a different voice than the
    one that will actually be generated.
    """
    from datetime import datetime, timezone

    from src.audio.narration_workflow import _combined_settings
    from src.audio.voice_workflow import create_voice_approval_record
    from src.news.voice_adapter import script_to_narration_request

    resolved = _resolve_voice_inputs(root=root, job=job, request=request, localization=localization)
    if resolved is None:
        return f"Could not resolve a voice profile for channel {request.channel_id!r}."
    policy, profile = resolved

    script_path = root / "localizations" / job.language / "script" / "script.json"
    script_data = json.loads(script_path.read_text(encoding="utf-8")) if script_path.is_file() else {}

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


def _completed_narration(store, voice_manifest_path: Path) -> str:
    """Path of narration this project already has, or "" if there is none.

    Deliberately strict: the manifest must claim an audio file *and* that file must
    exist on disk. A manifest pointing at a deleted wav is not finished narration,
    and treating it as such would skip the only step that could recreate it.
    """
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


def _create_fullscreen_voiceover(
    request: ContentCreationRequest, template, progress_callback: ProgressCallback | None = None
) -> ContentCreationResult:
    from src.news.article_ingestor import ArticleIngestionError
    from src.news.pipeline import create_news_to_short_job, run_news_to_short_job
    from src.news.project_store import NewsProjectStore

    if not request.channel_id:
        raise ContentCreationError("channel_id is required for fullscreen_voiceover_v1.")
    projects_root = Path(request.project_overrides.get("projects_root", "projects"))
    store = NewsProjectStore(projects_root)
    dry_run = bool(request.execution.dry_run)
    url, topic, pasted_text, text_file = _resolve_content_inputs(request)

    _notify(progress_callback, "project_create", "running")
    if request.execution.resume and request.project_id:
        job = store.load_job(request.project_id)
    else:
        job = create_news_to_short_job(
            projects_root=projects_root,
            channel_id=request.channel_id,
            url=url,
            title=request.title or None,
            topic=topic,
            text=pasted_text,
            text_file=text_file,
            language=request.language or "ru",
            target_duration_sec=int(
                request.target_duration_sec or request.project_overrides.get("target_duration_sec", 55)
            ),
            # This is the only layer that knows whether pasted text is an article
            # to write *about* or a script to speak. Before the script engine the
            # distinction was lost, and a finished script was shredded into
            # sentences and re-wrapped in the template generator's own phrases.
            script_source=_resolve_script_source(request),
            script_provider=str(request.project_overrides.get("script_provider", "") or ""),
            # Reaches user_supplied before script.json is written, which is the only
            # point where a brief can be attached to the author's own scenes.
            visual_briefs=dict(request.visual_briefs),
            completion_mode=request.completion_mode,
            script_adaptation=request.script_adaptation,
        )
    root = store.project_root(job.job_id)
    _notify(progress_callback, "project_create", "completed")
    stages: list[dict[str, Any]] = []

    if dry_run:
        result = run_news_to_short_job(
            projects_root=projects_root,
            job_id=job.job_id,
            dry_run=True,
            completion_mode=request.completion_mode,
            script_adaptation=request.script_adaptation,
        )
        return ContentCreationResult(
            status="dry_run_completed",
            project_id=job.job_id,
            project_root=str(root),
            stages=[{"stage": stage, "status": "completed"} for stage in result.completed_stages],
            rerun_commands=[_fullscreen_rerun_command(request, job.job_id)],
        )

    # Always safe to run up through asset_search: no paid TTS call happens before
    # the voice stage, matching src.audio.voice_workflow's approval-gated design.
    _notify(progress_callback, "script_and_research", "running")
    try:
        result = run_news_to_short_job(
            projects_root=projects_root,
            job_id=job.job_id,
            until_stage="asset_search",
            resume=True,
            completion_mode=request.completion_mode,
            script_adaptation=request.script_adaptation,
        )
    except ArticleIngestionError as exc:
        _notify(progress_callback, "script_and_research", "failed")
        raise ContentCreationError(
            str(exc), reason=exc.reason, retryable=exc.reason in _RETRYABLE_ARTICLE_REASONS
        ) from exc
    stages.extend({"stage": stage, "status": "completed"} for stage in result.completed_stages)
    # The pipeline owns job-stage mutation. Reload before this service changes any
    # terminal or voice state, otherwise a stale in-memory job can overwrite the
    # stages that the resumed pipeline just completed.
    job = store.load_job(job.job_id)
    _notify(progress_callback, "script_and_research", "completed")

    # Only elevenlabs is a paid provider (src.audio.tts.elevenlabs_provider.ElevenLabsProvider.paid
    # is the only True among the registered providers) - manual WAV import never needs
    # --approve-paid-generation, matching src.audio.voice_workflow.import_manual_audio's own
    # no-approval design.
    voice_manifest_path = root / "localizations" / job.language / "voice" / "voice_manifest.json"
    # One resolution for the rest of this workflow (D2). It also answers "is there
    # already narration on disk", by manifest and not by a bare file check, so the
    # existing-narration protection and the paid gate agree with the voice stage.
    localization = _resolve_localization(root=root, job=job, request=request)
    if localization is not None:
        existing_voice = localization.existing_narration_path
    else:
        existing_voice = _completed_narration(store, voice_manifest_path)

    requires_paid_approval = request.voice.provider == "elevenlabs" and not existing_voice
    approve_paid = bool(request.voice.approve_paid_generation) and requires_paid_approval
    execute_voice = approve_paid
    approval_warning = ""
    if execute_voice:
        # This is the fix for the wizard bug where confirming paid generation still
        # left voice_manifest at status=provider_selection_required/audio_path="":
        # build_or_generate_voice_manifest(execute=True) requires an approval.json on
        # disk (checked via src.audio.voice_workflow.is_final_generation_approved) and
        # we never wrote one, so it silently fell back to the unconfigured stub.
        approval_warning = _create_paid_voice_approval(
            root=root, job=job, request=request, localization=localization
        )

    if existing_voice:
        # Resuming a project whose narration is already generated. Running the voice
        # stage again would not just waste credits - with execute_voice=False it
        # rewrites voice_manifest.json as the unconfigured stub
        # (src.news.voice_stage.build_safe_voice_manifest), destroying the record of
        # narration that is sitting on disk. So it is not run at all.
        _notify(progress_callback, "voice", "skipped_existing_audio")
    else:
        _notify(progress_callback, "voice", "running")
        run_news_to_short_job(
            projects_root=projects_root,
            job_id=job.job_id,
            stage="voice",
            execute_voice=execute_voice,
            voice_profile_override=request.voice.profile or None,
        )
        job = store.load_job(job.job_id)

    if request.voice.provider == "audio_file" and request.voice.audio_file:
        from src.audio.voice_workflow import import_manual_audio

        import_manual_audio(
            project_root=root, job_id=job.job_id, language=job.language, audio_file=request.voice.audio_file
        )
        stages.append({"stage": "manual_audio_import", "status": "completed"})

    voice_manifest = store.read_json(voice_manifest_path) if voice_manifest_path.exists() else {}
    # Only report the voice stage as done if a real audio file actually exists now -
    # never show a checkmark for the safe/unconfigured stub manifest.
    voice_audio_path = str(voice_manifest.get("audio_path") or "")
    voice_has_audio = bool(voice_audio_path) and Path(voice_audio_path).is_file()
    if voice_has_audio:
        # A manual import happens after the safe voice preflight. In draft mode that
        # preflight is deliberately recorded as blocked, so synchronize the durable
        # job state now that a real narration file exists.
        job = store.load_job(job.job_id)
        voice_status = str(voice_manifest.get("voice_stage_status") or "completed")
        localization_state = job.localizations.get(job.language)
        if localization_state is not None:
            localization_state.voice_status = voice_status
        if job.status == "voice_provider_required":
            job.status = "in_progress"
        store.update_stage(
            job,
            "voice",
            status="completed",
            result_path=str(voice_manifest_path),
        )
    if existing_voice:
        voice_stage_status = "skipped_existing_audio"
    else:
        voice_stage_status = "completed" if voice_has_audio else "needs_review"
    stages.append(
        {"stage": "voice", "status": voice_stage_status, "execute_voice": execute_voice, "audio_path": voice_manifest.get("audio_path", "")}
    )
    if not existing_voice:
        _notify(progress_callback, "voice", voice_stage_status)

    if request.execution.prepare_only or (requires_paid_approval and not approve_paid):
        _notify(progress_callback, "paid_approval", "pending")
        preflight_summary: dict[str, Any] = {}
        if requires_paid_approval:
            # Free, read-only summary shown before the paid gate: resolved
            # display_name/model/character count/scene count/cache state, plus a
            # provider preflight - see _build_paid_preflight_summary docstring.
            preflight_summary = _build_paid_preflight_summary(
                root=root, job=job, request=request, localization=localization
            )
        gate_warnings = [
            "Paid ElevenLabs generation was NOT performed. Re-run with --approve-paid-generation "
            "to synthesize scene audio and continue to final_render.",
        ]
        if localization is not None and localization.fallback_reason:
            # Never let a missing key look like a silent no-op: say why, and what to do.
            gate_warnings.append(localization.fallback_reason)
        return ContentCreationResult(
            status="prepared_awaiting_paid_approval",
            project_id=job.job_id,
            project_root=str(root),
            stages=stages,
            output_paths={"voice_manifest": str(voice_manifest_path)},
            warnings=gate_warnings,
            evidence={
                "character_count": voice_manifest.get("character_count", 0),
                "provider": request.voice.provider,
                "voice_profile": request.voice.profile,
                **preflight_summary,
            },
            rerun_commands=[_fullscreen_rerun_command(request, job.job_id, approve=True)],
        )

    if execute_voice and not voice_has_audio:
        # Paid generation was approved and attempted but no audio came out (e.g. no
        # voices.yaml for this channel, or the underlying approval still didn't match) -
        # surface this clearly instead of silently continuing to a render that quality_check
        # will block anyway.
        warnings = [approval_warning] if approval_warning else []
        warnings.append(
            "Paid generation was approved but no audio was produced; voice_manifest is still "
            f"status={voice_manifest.get('status', 'unknown')!r}. Check that the channel has a "
            "configured voices.yaml voice profile."
        )
        return ContentCreationResult(
            status="needs_review",
            project_id=job.job_id,
            project_root=str(root),
            stages=stages,
            output_paths={"voice_manifest": str(voice_manifest_path)},
            warnings=warnings,
            evidence={
                "character_count": voice_manifest.get("character_count", 0),
                "provider": request.voice.provider,
                "voice_profile": request.voice.profile,
            },
            rerun_commands=[_fullscreen_rerun_command(request, job.job_id, approve=True)],
        )

    from src.assets.completion import MODE_DRAFT_COMPLETE
    from src.news.models import completion_settings

    if completion_settings(job).get("mode") == MODE_DRAFT_COMPLETE and not voice_has_audio:
        from src.news.draft_completion import write_completion_report

        report_paths = write_completion_report(root=root, job=job)
        job.status = "voice_provider_required"
        store.save_job(job)
        return ContentCreationResult(
            status="voice_provider_required",
            project_id=job.job_id,
            project_root=str(root),
            stages=stages,
            output_paths={
                "voice_manifest": str(voice_manifest_path),
                "replacement_report": report_paths.get("json_path", ""),
                "replacement_report_html": report_paths.get("html_path", ""),
            },
            warnings=[
                "Visual assembly and replacement report are saved. Configure a voice "
                "provider or import narration audio, then resume rendering."
            ],
            rerun_commands=[_fullscreen_rerun_command(request, job.job_id)],
        )

    if request.subtitles.style != "disabled":
        _notify(progress_callback, "subtitles", "running")
        run_news_to_short_job(projects_root=projects_root, job_id=job.job_id, stage="subtitles")
        stages.append({"stage": "subtitles", "status": "completed"})
        _notify(progress_callback, "subtitles", "completed")

    # src/news/final_renderer.py has always been able to loop, duck and mix a music
    # bed - it just needed assets/music/music_manifest.json, which nothing wrote.
    # Written here (not as a new pipeline stage) so job.json's stage schema is
    # unchanged and existing projects keep resuming.
    music_warnings: list[str] = []
    if request.music.mode == "local_file" and request.music.path:
        from src.audio.music_manifest import MusicManifestError, prepare_project_music

        _notify(progress_callback, "music", "running")
        try:
            prepare_project_music(root, request.music.path, volume=request.music.volume)
            stages.append({"stage": "music", "status": "completed"})
            _notify(progress_callback, "music", "completed")
        except MusicManifestError as exc:
            # Never fail the whole render over a background track: report it and
            # continue with voice only, rather than losing the paid narration.
            music_warnings.append(f"Музыка не добавлена: {exc}")
            stages.append({"stage": "music", "status": "needs_review"})
            _notify(progress_callback, "music", "needs_review")

    run_news_to_short_job(projects_root=projects_root, job_id=job.job_id, stage="preview_render")
    stages.append({"stage": "preview_render", "status": "completed"})

    quality_report: dict[str, Any] = {}
    quality_path = root / "quality" / "quality_report.json"
    _notify(progress_callback, "render", "running")
    run_news_to_short_job(projects_root=projects_root, job_id=job.job_id, stage="quality_check")
    if quality_path.exists():
        quality_report = store.read_json(quality_path)
    stages.append({"stage": "quality_check", "status": quality_report.get("status", "unknown")})

    run_news_to_short_job(projects_root=projects_root, job_id=job.job_id, stage="final_render")
    final_manifest_path = root / "render" / "final_render_manifest.json"
    final_manifest = store.read_json(final_manifest_path) if final_manifest_path.exists() else {}
    render_ok = bool(final_manifest.get("output_path")) and final_manifest.get("status") != "blocked"
    render_stage_status = "completed" if render_ok else (final_manifest.get("status") or "blocked")
    stages.append({"stage": "final_render", "status": render_stage_status})

    final_result = run_news_to_short_job(projects_root=projects_root, job_id=job.job_id, stage="export")
    stages.append({"stage": "export", "status": "completed" if render_ok else "skipped"})
    _notify(progress_callback, "render", render_stage_status)

    output_paths = {}
    if render_ok:
        output_paths["final_video"] = final_manifest["output_path"]
        output_paths["outputs"] = final_manifest.get("outputs", {})
    replacement_root = root / "replacement"
    replacement_json = replacement_root / "replacement_report.json"
    replacement_html = replacement_root / "replacement_report.html"
    if replacement_json.is_file():
        output_paths["replacement_report"] = str(replacement_json)
    if replacement_html.is_file():
        output_paths["replacement_report_html"] = str(replacement_html)

    return ContentCreationResult(
        status=final_result.status,
        project_id=job.job_id,
        project_root=str(root),
        stages=stages,
        output_paths=output_paths,
        warnings=music_warnings,
        quality_report=quality_report,
        rerun_commands=[_fullscreen_rerun_command(request, job.job_id, approve=True)],
    )


def _fullscreen_rerun_command(request: ContentCreationRequest, job_id: str, *, approve: bool = False) -> str:
    parts = [
        "./venv/Scripts/python.exe -m src.content_creation.cli create",
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
