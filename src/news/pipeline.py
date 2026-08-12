"""Canonical boundary для стадийного выполнения workflow ``fullscreen_voiceover_v1``.

Responsibilities:
- создание проекта (``create_news_to_short_job``) и его запуск
  (``run_news_to_short_job``, ``run_news_to_short_cli``);
- порядок стадий из ``models.NEWS_TO_SHORT_STAGES``, диспетчеризация каждой
  стадии к её владельцу и запись stage state через ``NewsProjectStore``;
- resume, ``--stage``, ``--until-stage``, ``--force-stage`` и ``--dry-run``;
- итоговый статус job: ``completed``, ``needs_review``, ``draft_completed``,
  ``in_progress``, ``dry_run_completed`` либо терминальная причина completion;
- применение completion-настроек и инвалидация зависящих от них стадий.

Does not own:
- содержание стадий: research, script, visual plan, ассеты, озвучка, субтитры,
  quality check, рендер и экспорт принадлежат своим модулям;
- persisted форму и запись файлов — ``project_store.NewsProjectStore``;
- выбор шаблона и application-уровень — ``src.content_creation.service`` и
  ``src.ai_youtube.apps.content_creator.workflows.fullscreen_voiceover``
  (ADR 0009);
- общие сервисы: ``src.assets``, ``src.providers``, ``src.audio``,
  ``src.subtitles``, ``src.project_foundation``.

Inputs: ``projects_root``, ``job_id`` и флаги запуска; для create — канал,
язык, вход (topic/text/url), пользовательские ассеты, длительность, completion
mode и adaptation.

Outputs: ``NewsPipelineResult`` и артефакты стадий на диске — ``job.json`` со
stage state, ``article/``, ``research/claims.json``,
``localizations/<lang>/`` (script, visual plan, voice, subtitles, output),
``assets/assets_manifest.json``, ``quality/quality_report.json``,
``render/final_render_manifest.json``, ``export/``.

Important invariants:
- повторяемые стадии от ``research`` до ``export`` идемпотентны по проверке
  фактического output; ``input`` и потенциально сетевой ``article_ingestion``
  в эту policy намеренно не входят (ADR 0006);
- завершённая стадия пропускается при обычном повторе и при ``resume``;
  ``final_render`` также пропускается на явно запрошенной
  ``stage="final_render"`` при validated completed state; перезапустить
  завершённую стадию можно через ``force_stage``;
- стадия, чей JSON-результат содержит ``status="blocked"``, отмечается
  ``blocked``, а не ``completed``;
- ``strict`` требует ``quality_report.status == "passed"`` до финального
  рендера; ``draft_complete`` идёт через отдельный draft render gate и всегда
  оставляет ``publish_ready=false``;
- ``--execute-voice`` сам по себе платную генерацию не запускает: approval
  проверяет ``src.audio.narration_workflow``;
- ``dry_run`` останавливается на ``asset_search`` и до озвучки, рендера и
  экспорта не доходит.

See also: ``docs/current/SYSTEM_MAP.md``, ADR 0004, 0005, 0006, 0009,
``src/news/__init__.py``.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

from src.audio.scene_timeline import apply_timeline_to_script, build_scene_timeline
from src.assets.completion import MODE_DRAFT_COMPLETE, normalize_mode
from src.assets.completion.replacement import STALE_STAGES

from .article_ingestor import ArticleIngestionError, ingest_article, load_text_file
from .asset_manager import build_news_asset_manifest
from .draft_completion import (
    REASON_VOICE_REQUIRED,
    evaluate_draft_render_gate,
    reuse_ledger_from_manifest,
    run_adaptation_pass,
    write_completion_report,
)
from .exporter import export_localization
from .final_renderer import render_final_video
from .models import (
    INPUT_MODE_TEXT,
    INPUT_MODE_TOPIC,
    INPUT_MODE_URL,
    NEWS_TO_SHORT_STAGES,
    NewsJob,
    completion_settings,
)
from .preview_renderer import render_preview
from .project_store import NewsProjectStore
from .quality_check import run_quality_check
from .research_engine import build_research
from .script_generator import build_script
from .subtitles import build_subtitles_for_localization
from .visual_plan import build_visual_plan
from .voice_adapter import resolve_localization_for_channel
from .voice_stage import build_or_generate_voice_manifest


@dataclass
class NewsPipelineResult:
    job_id: str
    status: str
    project_root: Path
    completed_stages: list[str]


# A stored asset_search stays readable forever; it may only be *reused* when the
# manifest can prove which inputs produced it. Bump the version when the payload
# below changes, so older fingerprints deterministically stop matching instead of
# comparing two different questions.
ASSET_SEARCH_FINGERPRINT_VERSION = 1
ASSET_SEARCH_FINGERPRINT_KEY = "asset_search_fingerprint"


def asset_search_fingerprint(
    job: NewsJob,
    visual_plan: dict[str, Any],
    *,
    dry_run: bool,
    asset_selection: dict[str, Any],
) -> str:
    """Identify the inputs ``build_asset_search_manifest`` actually searches on.

    Exactly the arguments that decide what is retrieved and selected, and nothing
    else. ``project_root``/``project_id`` say *where* a project lives rather than
    what it asks for, and the reuse ledger is scratch state of a single run, so
    none of them belong here: a project that moved on disk must still match.
    """
    payload = {
        "version": ASSET_SEARCH_FINGERPRINT_VERSION,
        "asset_selection": asset_selection,
        "channel": job.channel_id,
        "completion_mode": normalize_mode(completion_settings(job).get("mode")),
        "dry_run": bool(dry_run),
        "user_assets": list(job.user_assets or []),
        "visual_plan": visual_plan,
    }
    encoded = json.dumps(
        payload, sort_keys=True, ensure_ascii=False, default=str
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _channel_asset_selection(channel_id: str) -> dict[str, Any]:
    selection = _load_channel_config(channel_id).get("asset_selection", {})
    return selection if isinstance(selection, dict) else {}


def _asset_search_reuse_block(
    store: NewsProjectStore,
    job: NewsJob,
    root: Path,
    *,
    dry_run: bool,
) -> str:
    """Why a completed asset_search may not be reused, or "" when it may.

    Fail closed: a missing or unusable fingerprint means compatibility is unknown,
    and unknown is not permission. Legacy manifests keep reading exactly as before
    - they are recomputed once, then carry a fingerprint like any other.
    """
    state = job.stages.get("asset_search")
    if state is None or state.status != "completed":
        return ""
    try:
        manifest = store.read_json(root / "assets" / "assets_manifest.json")
        plan = store.read_json(
            root / "localizations" / job.language / "visual" / "visual_plan.json"
        )
    except (OSError, ValueError, TypeError):
        return "asset_search_inputs_unreadable"
    if not isinstance(manifest, dict) or not isinstance(plan, dict):
        return "asset_search_inputs_unreadable"
    stored = manifest.get(ASSET_SEARCH_FINGERPRINT_KEY)
    if stored is None:
        return "asset_search_fingerprint_missing"
    if not isinstance(stored, str) or not stored.strip():
        return "asset_search_fingerprint_invalid"
    current = asset_search_fingerprint(
        job,
        plan,
        dry_run=dry_run,
        asset_selection=_channel_asset_selection(job.channel_id),
    )
    return "" if stored == current else "asset_search_inputs_changed"


def _invalidate_stale_asset_search(job: NewsJob, *, reason: str) -> None:
    """Mark the search and everything that consumes its visual assembly.

    ``STALE_STAGES`` is the existing canonical answer to "what stops being valid
    when the visual assets change", already used by visual-slot replacement.
    Voice and subtitles are built from the script and are deliberately untouched.
    Result files stay on disk as audit evidence; only the stage states go stale.
    """
    metadata = {"stale_reason": reason}
    for stage_name in ("asset_search", *STALE_STAGES):
        state = job.stages.get(stage_name)
        if state is None:
            continue
        state.status = "stale"
        state.started_at = None
        state.finished_at = None
        state.error = None
        state.settings = {**dict(state.settings or {}), **metadata}
    job.status = "in_progress"
    job.current_stage = "asset_search"


def _stamp_asset_search_fingerprint(
    store: NewsProjectStore,
    job: NewsJob,
    root: Path,
    *,
    dry_run: bool,
) -> None:
    """Bind the manifest on disk to the inputs that produced it.

    Stamped last, from the artifacts as they finally stand: the draft-complete
    adaptation pass may replace both the visual plan and the manifest after the
    first search, and it is that final pair the next resume will be compared to.
    """
    manifest_path = root / "assets" / "assets_manifest.json"
    manifest = store.read_json(manifest_path)
    plan = store.read_json(
        root / "localizations" / job.language / "visual" / "visual_plan.json"
    )
    manifest[ASSET_SEARCH_FINGERPRINT_KEY] = asset_search_fingerprint(
        job,
        plan,
        dry_run=dry_run,
        asset_selection=_channel_asset_selection(job.channel_id),
    )
    store.write_json(manifest_path, manifest)


def create_news_to_short_job(
    *,
    projects_root: str | Path | None = None,
    channel_id: str = "nature_science_news_ru",
    url: str | None = None,
    urls: list[str] | None = None,
    title: str | None = None,
    topic: str | None = None,
    text: str | None = None,
    text_file: str | None = None,
    assets: list[str] | None = None,
    language: str = "ru",
    target_duration_sec: int = 55,
    script_provider: str = "",
    script_source: str = "",
    script_include_cta: bool = False,
    script_cta_text: str = "",
    visual_briefs: dict[str, dict[str, Any]] | None = None,
    completion_mode: str = "",
    script_adaptation: str = "",
    now: str | None = None,
) -> NewsJob:
    source_urls = list(urls or [])
    if url:
        source_urls.append(url)
    input_text = text or (load_text_file(text_file) if text_file else "")
    if source_urls:
        input_mode = INPUT_MODE_URL
    elif input_text:
        input_mode = INPUT_MODE_TEXT
    else:
        input_mode = INPUT_MODE_TOPIC
    store = NewsProjectStore(projects_root)
    root = store.projects_root
    # Names are made unique against every folder already in this root - including
    # projects created by the other storage system - so a new project can never
    # collide with, or silently write into, an existing one.
    existing_ids = {entry.name for entry in root.iterdir() if entry.is_dir()} if root.is_dir() else set()
    job = NewsJob.create(
        channel_id=channel_id,
        input_mode=input_mode,
        title=title or "",
        topic=topic or input_text[:80] or (source_urls[0] if source_urls else ""),
        source_urls=source_urls,
        input_text=input_text,
        user_assets=assets or [],
        language=language,
        target_duration_sec=target_duration_sec,
        script_provider=script_provider,
        script_source=script_source,
        script_include_cta=script_include_cta,
        script_cta_text=script_cta_text,
        visual_briefs=visual_briefs,
        completion_mode=completion_mode,
        script_adaptation=script_adaptation,
        now=now,
        is_taken=existing_ids,
    )
    store.create_project(job)
    return job


def run_news_to_short_job(
    *,
    projects_root: str | Path | None = None,
    job_id: str,
    dry_run: bool = False,
    until_stage: str | None = None,
    stage: str | None = None,
    resume: bool = False,
    force_stage: bool = False,
    execute_voice: bool = False,
    voice_profile_override: str | None = None,
    completion_mode: str = "",
    script_adaptation: str = "",
) -> NewsPipelineResult:
    store = NewsProjectStore(projects_root)
    job = store.load_job(job_id)
    _apply_completion_overrides(
        store,
        job,
        completion_mode=completion_mode,
        script_adaptation=script_adaptation,
    )
    root = store.project_root(job_id)
    # Before anything reads the completed set, not while iterating it: a stored
    # asset_search that cannot prove its inputs is demoted here, so the snapshot
    # below already reflects it and no later stage can be skipped on its strength.
    # `force_stage` is the caller taking explicit control, exactly as it does for
    # every other skip decision in the loop.
    if not force_stage:
        reuse_block = _asset_search_reuse_block(store, job, root, dry_run=dry_run)
        if reuse_block:
            _invalidate_stale_asset_search(job, reason=reuse_block)
            store.save_job(job)
    stop_stage = until_stage or ("asset_search" if dry_run else None)
    stages = [stage] if stage else NEWS_TO_SHORT_STAGES
    completed = store.completed_stage_names(job)
    ran: list[str] = []
    terminal_status = ""
    for stage_name in stages:
        if stage_name not in NEWS_TO_SHORT_STAGES:
            raise ValueError(f"Unknown news_to_short stage: {stage_name}")
        # If the requested stopping point was completed by an earlier run, resume
        # stops there. Previously the generic resume `continue` won first and the
        # pipeline accidentally ran every later stage.
        if stage_name == stop_stage and stage_name in completed and not force_stage:
            break
        if resume and stage_name in completed and not force_stage:
            if (
                stage_name == "voice"
                and normalize_mode(completion_settings(job).get("mode")) == MODE_DRAFT_COMPLETE
                and not _voice_audio_exists(root, job.language, store)
            ):
                write_completion_report(root=root, job=job)
                terminal_status = REASON_VOICE_REQUIRED
                break
            continue
        # final_render is expensive (re-encodes the whole video) and is always
        # dispatched as an explicit single stage by the render/export phase, on
        # every resume - so it must honour the same completed-stage skip as the
        # rest of the pipeline instead of only skipping when no explicit `stage`
        # was requested.
        if (
            not force_stage
            and stage_name in completed
            and (not stage or stage_name == "final_render")
        ):
            if stage_name == stop_stage:
                break
            continue
        if dry_run and stage_name in {"voice", "subtitles", "preview_render", "quality_check", "final_render", "export"}:
            break
        _run_stage(
            stage_name,
            store,
            job,
            root,
            dry_run=dry_run,
            execute_voice=execute_voice,
            voice_profile_override=voice_profile_override,
            force_stage=force_stage,
        )
        ran.append(stage_name)
        if (
            stage_name == "voice"
            and normalize_mode(completion_settings(job).get("mode")) == MODE_DRAFT_COMPLETE
            and not _voice_audio_exists(root, job.language, store)
        ):
            write_completion_report(root=root, job=job)
            terminal_status = REASON_VOICE_REQUIRED
            break
        if stage_name == stop_stage:
            break
    mode = normalize_mode(completion_settings(job).get("mode"))
    if terminal_status:
        job.status = terminal_status
    elif not dry_run:
        quality_path = root / "quality" / "quality_report.json"
        final_render_path = root / "render" / "final_render_manifest.json"
        final_render = store.read_json(final_render_path) if final_render_path.exists() else {}
        final_render_completed = (
            job.stages.get("final_render") is not None
            and job.stages["final_render"].status == "completed"
        )
        has_final_output = (
            final_render_completed
            and bool(final_render.get("output_path"))
            and Path(final_render.get("output_path", "")).exists()
        )
        if has_final_output:
            if mode == MODE_DRAFT_COMPLETE:
                job.status = "draft_completed"
            else:
                quality_status = store.read_json(quality_path).get("status") if quality_path.exists() else ""
                job.status = "completed" if quality_status == "passed" else "needs_review"
        elif quality_path.exists() and (
            job.stages.get("quality_check") is None
            or job.stages["quality_check"].status != "stale"
        ):
            # A quality report on disk keeps its say over the job status - that is how
            # a blocked final render has always surfaced as needs_review. Only an
            # explicit invalidation (completion settings changed under it) makes the
            # stored verdict untrustworthy; a stage that simply has not run yet does
            # not, because the report is still the newest thing anyone measured.
            quality_status = store.read_json(quality_path).get("status")
            job.status = "needs_review" if quality_status else "in_progress"
        else:
            job.status = "in_progress"
    else:
        job.status = "dry_run_completed"
    if stop_stage and stop_stage not in ran and stop_stage in completed:
        job.status = "dry_run_completed" if dry_run else job.status
    store.save_job(job)
    return NewsPipelineResult(job_id=job.job_id, status=job.status, project_root=root, completed_stages=ran)


def run_news_to_short_cli(args: Any) -> NewsPipelineResult:
    configured_projects_root = getattr(args, "projects_root", None)
    if configured_projects_root:
        projects_root = Path(configured_projects_root)
    else:
        from src.config_resolver.paths import resolve_application_paths

        projects_root = resolve_application_paths().projects_root
    if getattr(args, "news_action", "create") == "create":
        job = create_news_to_short_job(
            projects_root=projects_root,
            channel_id=getattr(args, "news_channel", None) or "nature_science_news_ru",
            url=getattr(args, "url", None),
            urls=getattr(args, "urls", None),
            topic=getattr(args, "topic", None),
            text=getattr(args, "text", None),
            text_file=getattr(args, "text_file", None),
            assets=getattr(args, "assets", None),
            language=getattr(args, "language", "ru"),
            target_duration_sec=getattr(args, "target_duration", 55),
            completion_mode=getattr(args, "completion_mode", ""),
            script_adaptation=getattr(args, "script_adaptation", ""),
        )
    else:
        job_id = getattr(args, "job_id", None)
        if not job_id:
            raise SystemExit("--job-id is required for run/resume actions.")
        job = NewsProjectStore(projects_root).load_job(job_id)
    return run_news_to_short_job(
        projects_root=projects_root,
        job_id=job.job_id,
        dry_run=getattr(args, "dry_run", False),
        until_stage=getattr(args, "until_stage", None),
        stage=getattr(args, "stage", None),
        resume=getattr(args, "news_action", "create") == "resume" or getattr(args, "resume", False),
        force_stage=getattr(args, "force_stage", False),
        # Paid generation still requires an approval.json on disk (checked inside
        # narration_workflow.generate_final); --execute-voice alone can never trigger it.
        execute_voice=getattr(args, "execute_voice", False),
        # Was silently dropped here, so `pipeline.py --news-to-short --voice-profile X`
        # ran with the channel default instead of the profile the user asked for.
        voice_profile_override=getattr(args, "voice_profile", None) or None,
        completion_mode=getattr(args, "completion_mode", ""),
        script_adaptation=getattr(args, "script_adaptation", ""),
    )


def _run_stage(
    stage_name: str,
    store: NewsProjectStore,
    job: NewsJob,
    root: Path,
    *,
    dry_run: bool,
    execute_voice: bool = False,
    voice_profile_override: str | None = None,
    force_stage: bool = False,
) -> Path:
    store.update_stage(job, stage_name, status="running", settings={"dry_run": dry_run})
    try:
        result_path = _dispatch_stage(
            stage_name,
            store,
            job,
            root,
            dry_run=dry_run,
            execute_voice=execute_voice,
            voice_profile_override=voice_profile_override,
            force_stage=force_stage,
        )
    except Exception as exc:
        store.update_stage(job, stage_name, status="failed", error=str(exc))
        raise
    result_status = "completed"
    if result_path.suffix.lower() == ".json" and result_path.is_file():
        payload = store.read_json(result_path)
        if payload.get("status") == "blocked":
            result_status = "blocked"
        if (
            stage_name == "voice"
            and normalize_mode(completion_settings(job).get("mode")) == MODE_DRAFT_COMPLETE
            and not _voice_audio_exists(root, job.language, store)
        ):
            result_status = "blocked"
    store.update_stage(job, stage_name, status=result_status, result_path=str(result_path))
    return result_path


def _dispatch_stage(
    stage_name: str,
    store: NewsProjectStore,
    job: NewsJob,
    root: Path,
    *,
    dry_run: bool,
    execute_voice: bool = False,
    voice_profile_override: str | None = None,
    force_stage: bool = False,
) -> Path:
    if stage_name == "input":
        return root / "input" / "input.json"
    if stage_name == "article_ingestion":
        try:
            article, images = ingest_article(job)
        except ArticleIngestionError:
            raise
        except Exception as exc:
            raise ArticleIngestionError(
                f"Article could not be processed. Use text input or user assets. Details: {exc}"
            ) from exc
        store.write_json(root / "article" / "article.json", article)
        store.write_json(root / "article" / "images.json", {"images": images})
        return root / "article" / "article.json"
    if stage_name == "research":
        article = store.read_json(root / "article" / "article.json")
        research = build_research(job, article)
        store.write_json(root / "research" / "claims.json", research)
        return root / "research" / "claims.json"
    if stage_name == "script":
        research = store.read_json(root / "research" / "claims.json")
        script = build_script(job, research)
        lang_root = root / "localizations" / job.language / "script"
        store.write_json(lang_root / "script.json", script)
        (lang_root / "narration.txt").write_text(script["narration_text"] + "\n", encoding="utf-8")
        job.localizations[job.language].script_path = str(lang_root / "script.json")
        job.localizations[job.language].narration_path = str(lang_root / "narration.txt")
        store.save_job(job)
        return lang_root / "script.json"
    if stage_name == "visual_plan":
        script = store.read_json(root / "localizations" / job.language / "script" / "script.json")
        # Claims sharpen which entity the video is about; the plan is still built
        # from the script alone when an older project has no research on disk.
        claims_path = root / "research" / "claims.json"
        research = store.read_json(claims_path) if claims_path.is_file() else {}
        plan = build_visual_plan(
            script, language=job.language, user_assets=job.user_assets, research=research
        )
        master = {**plan, "language": "master", "master_language": job.language}
        store.write_json(root / "master" / "master_visual_plan.json", master)
        lang_path = root / "localizations" / job.language / "visual" / "visual_plan.json"
        store.write_json(lang_path, plan)
        job.localizations[job.language].visual_plan_path = str(lang_path)
        store.save_job(job)
        return lang_path
    if stage_name == "asset_search":
        plan = store.read_json(root / "localizations" / job.language / "visual" / "visual_plan.json")
        manifest = build_asset_search_manifest(job, plan, dry_run=dry_run, project_root=root)
        store.write_json(root / "assets" / "assets_manifest.json", manifest)
        store.write_json(root / "assets" / "missing_assets.json", {"missing_scenes": manifest["missing_scenes"]})
        if normalize_mode(completion_settings(job).get("mode")) == MODE_DRAFT_COMPLETE:
            if not dry_run:
                initial_manifest = manifest

                def _research_changed_scenes(plan_subset: dict[str, Any]) -> dict[str, Any]:
                    return build_asset_search_manifest(
                        job,
                        plan_subset,
                        dry_run=False,
                        project_root=root,
                        reuse_ledger=reuse_ledger_from_manifest(initial_manifest),
                    )

                run_adaptation_pass(
                    store=store,
                    job=job,
                    root=root,
                    research_scenes=_research_changed_scenes,
                )
            # The adaptation pass only writes a replacement when coverage improves.
            # Always report the final on-disk manifest, including the no-improvement
            # fallback case.
            write_completion_report(root=root, job=job)
        _stamp_asset_search_fingerprint(store, job, root, dry_run=dry_run)
        return root / "assets" / "assets_manifest.json"
    if stage_name == "voice":
        script_path = root / "localizations" / job.language / "script" / "script.json"
        script = store.read_json(script_path)
        # One resolution for the whole stage (D2): language, locale, provider, profile,
        # voice_id, fallback policy and narration source all come from the same
        # ConfigResolver answer instead of being recomputed per call site. Returns None
        # for a channel the resolver does not know, and the legacy readers below are
        # then used exactly as before.
        localization = resolve_localization_for_channel(
            channel_id=job.channel_id,
            language=job.language,
            project_root=root,
            project_id=job.job_id,
            projects_dir=store.projects_root,
            voice_profile_override=voice_profile_override,
            script_path=str(script_path),
        )
        manifest = build_or_generate_voice_manifest(
            project_root=root,
            language=job.language,
            script=script,
            channel_voice_config=_load_channel_voice_config(job.channel_id),
            channel_workflow_config=_load_channel_workflow_config(job.channel_id),
            channel_id=job.channel_id,
            job_id=job.job_id,
            execute=execute_voice,
            voice_profile_override=voice_profile_override,
            localization=localization,
        )
        if localization is not None and localization.locale:
            # script_locale already exists on LocalizationState and was written once at
            # create time; keeping it in step with the resolved locale costs nothing and
            # is what a later multi-language run reads back.
            job.localizations[job.language].script_locale = localization.locale
        # Write the real spoken timings back onto the script so the renderer and the
        # subtitle builder stop using the planned estimate. Both already prefer
        # actual_duration_sec; nothing wrote it before this, which is why a rendered
        # video's visual timeline could be ~8 s shorter than its own narration.
        # No-op (and script untouched) whenever narration was not generated.
        timeline = build_scene_timeline(manifest, script=script, format_id="vertical_short")
        if timeline:
            store.write_json(script_path, apply_timeline_to_script(script, timeline))
            store.write_json(
                root / "localizations" / job.language / "voice" / "scene_timeline.json", timeline.to_dict()
            )
        job.localizations[job.language].voice_status = manifest["voice_stage_status"]
        store.save_job(job)
        return root / "localizations" / job.language / "voice" / "voice_manifest.json"
    if stage_name == "subtitles":
        script_path = root / "localizations" / job.language / "script" / "script.json"
        script = store.read_json(script_path)
        voice_path = root / "localizations" / job.language / "voice" / "voice_manifest.json"
        visual_path = root / "localizations" / job.language / "visual" / "visual_plan.json"
        # Одна и та же разрешённая локализация, что у стадии voice (D2/E2): язык
        # субтитров приходит оттуда, а не из script.json.
        localization = resolve_localization_for_channel(
            channel_id=job.channel_id,
            language=job.language,
            project_root=root,
            project_id=job.job_id,
            projects_dir=store.projects_root,
            script_path=str(script_path),
        )
        artifact = build_subtitles_for_localization(
            project_root=root,
            localization_id=job.language,
            script=script,
            voice_manifest=store.read_json(voice_path) if voice_path.exists() else None,
            channel_id=job.channel_id,
            localization=localization,
            visual_plan=store.read_json(visual_path) if visual_path.exists() else None,
            resume=not force_stage,
        )
        return artifact.manifest_path
    if stage_name == "preview_render":
        script = store.read_json(root / "localizations" / job.language / "script" / "script.json")
        voice_path = root / "localizations" / job.language / "voice" / "voice_manifest.json"
        assets_path = root / "assets" / "assets_manifest.json"
        voice = store.read_json(voice_path) if voice_path.exists() else {}
        assets = store.read_json(assets_path) if assets_path.exists() else {}
        if voice.get("status") != "completed" or assets.get("missing_scenes"):
            manifest = {
                "status": "blocked",
                "reason": "preview_requires_completed_voice_and_no_missing_assets",
                "voice_status": voice.get("status", "missing"),
                "missing_scene_count": len(assets.get("missing_scenes", [])),
                "path": "",
            }
            store.write_json(root / "preview" / "preview_manifest.json", manifest)
            return root / "preview" / "preview_manifest.json"
        manifest = render_preview(root, script)
        store.write_json(root / "preview" / "preview_manifest.json", manifest)
        return root / "preview" / "preview.mp4"
    if stage_name == "quality_check":
        script = store.read_json(root / "localizations" / job.language / "script" / "script.json")
        research = store.read_json(root / "research" / "claims.json")
        assets = store.read_json(root / "assets" / "assets_manifest.json")
        voice_path = root / "localizations" / job.language / "voice" / "voice_manifest.json"
        subtitles_path = root / "localizations" / job.language / "subtitles" / "subtitles_manifest.json"
        report = run_quality_check(
            script=script,
            research=research,
            assets_manifest=assets,
            voice_manifest=store.read_json(voice_path) if voice_path.exists() else None,
            subtitles_manifest=store.read_json(subtitles_path) if subtitles_path.exists() else None,
            completion_mode=str(completion_settings(job).get("mode") or ""),
        )
        store.write_json(root / "quality" / "quality_report.json", report)
        return root / "quality" / "quality_report.json"
    if stage_name == "final_render":
        mode = normalize_mode(completion_settings(job).get("mode"))
        quality = store.read_json(root / "quality" / "quality_report.json")
        if mode != MODE_DRAFT_COMPLETE and quality.get("status") != "passed":
            manifest = {
                "status": "blocked",
                "reason": "quality_check_requires_review",
                "output_path": "",
                "completion_mode": mode,
            }
        else:
            script = store.read_json(root / "localizations" / job.language / "script" / "script.json")
            visual = store.read_json(root / "localizations" / job.language / "visual" / "visual_plan.json")
            assets = store.read_json(root / "assets" / "assets_manifest.json")
            voice = store.read_json(root / "localizations" / job.language / "voice" / "voice_manifest.json")
            if mode == MODE_DRAFT_COMPLETE:
                subtitles_path = root / "localizations" / job.language / "subtitles" / "subtitles_manifest.json"
                gate = evaluate_draft_render_gate(
                    script=script,
                    assets_manifest=assets,
                    voice_manifest=voice,
                    subtitles_manifest=store.read_json(subtitles_path) if subtitles_path.exists() else None,
                )
                if gate.get("status") != "allowed":
                    manifest = {
                        "status": "blocked",
                        "reason": gate.get("reason") or "draft_render_gate_blocked",
                        "output_path": "",
                        "completion_mode": mode,
                        "publish_ready": False,
                        "draft_render_gate": gate,
                    }
                else:
                    manifest = render_final_video(
                        project_root=root,
                        language=job.language,
                        script=script,
                        visual_plan=visual,
                        assets_manifest=assets,
                        voice_manifest=voice,
                        completion_mode=mode,
                    )
                    manifest["draft_render_gate"] = gate
                    manifest["publish_ready"] = False
            else:
                manifest = render_final_video(
                    project_root=root,
                    language=job.language,
                    script=script,
                    visual_plan=visual,
                    assets_manifest=assets,
                    voice_manifest=voice,
                    completion_mode=mode,
                )
        store.write_json(root / "render" / "final_render_manifest.json", manifest)
        if mode == MODE_DRAFT_COMPLETE:
            write_completion_report(root=root, job=job)
        return root / "render" / "final_render_manifest.json"
    if stage_name == "export":
        script = store.read_json(root / "localizations" / job.language / "script" / "script.json")
        research = store.read_json(root / "research" / "claims.json")
        assets = store.read_json(root / "assets" / "assets_manifest.json")
        quality = store.read_json(root / "quality" / "quality_report.json")
        manifest = export_localization(
            project_root=root,
            language=job.language,
            job=job.to_dict(),
            script=script,
            research=research,
            assets_manifest=assets,
            quality_report=quality,
        )
        return Path(manifest["manifest_path"])
    return _write_placeholder_stage(store, root, stage_name)


def build_asset_search_manifest(
    job: NewsJob,
    visual_plan: dict[str, Any],
    *,
    dry_run: bool,
    project_root: str | Path | None = None,
    reuse_ledger: Any | None = None,
) -> dict[str, Any]:
    manifest = build_news_asset_manifest(
        visual_plan=visual_plan,
        user_assets=job.user_assets,
        dry_run=dry_run,
        channel=job.channel_id,
        asset_selection=_channel_asset_selection(job.channel_id),
        project_root=project_root,
        project_id=job.job_id,
        completion_mode=str(completion_settings(job).get("mode") or ""),
        reuse_ledger=reuse_ledger,
    )
    return {"mode": job.mode, **manifest}


def _apply_completion_overrides(
    store: NewsProjectStore,
    job: NewsJob,
    *,
    completion_mode: str,
    script_adaptation: str,
) -> None:
    """Apply only explicit runtime overrides; an empty CLI flag preserves job.json."""
    if not completion_mode and not script_adaptation:
        return
    from .models import build_completion_state

    current = completion_settings(job)
    requested_mode = completion_mode or str(current["mode"])
    requested_adaptation = (
        script_adaptation
        if script_adaptation
        else "" if completion_mode else str(current["script_adaptation"])
    )
    updated = build_completion_state(
        mode=requested_mode,
        script_adaptation=requested_adaptation,
    )
    updated["adaptation_pass"] = int(current.get("adaptation_pass") or 0)
    settings_changed = any(
        str(updated[key]) != str(current[key])
        for key in ("mode", "script_adaptation")
    )
    if settings_changed:
        _invalidate_completion_dependent_stages(
            job,
            previous=current,
            updated=updated,
        )
    job.completion = updated
    store.save_job(job)


def _invalidate_completion_dependent_stages(
    job: NewsJob,
    *,
    previous: dict[str, Any],
    updated: dict[str, Any],
) -> None:
    """Make a stored asset result impossible to reuse under different semantics.

    Completion mode and script adaptation first take effect inside ``asset_search``.
    Every later stage may consume either its visual assembly or an adapted script, so
    all of them have to be rerun on resume.  Result paths remain as audit evidence but
    their stage states are explicitly stale.
    """
    first = NEWS_TO_SHORT_STAGES.index("asset_search")
    metadata = {
        "stale_reason": "completion_settings_changed",
        "previous_completion_mode": str(previous.get("mode") or ""),
        "completion_mode": str(updated.get("mode") or ""),
        "previous_script_adaptation": str(previous.get("script_adaptation") or ""),
        "script_adaptation": str(updated.get("script_adaptation") or ""),
    }
    for stage_name in NEWS_TO_SHORT_STAGES[first:]:
        state = job.stages.get(stage_name)
        if state is None:
            continue
        state.status = "stale"
        state.started_at = None
        state.finished_at = None
        state.error = None
        state.settings = {**dict(state.settings or {}), **metadata}
    job.status = "in_progress"
    job.current_stage = "asset_search"


def _voice_audio_exists(root: Path, language: str, store: NewsProjectStore) -> bool:
    path = root / "localizations" / language / "voice" / "voice_manifest.json"
    if not path.is_file():
        return False
    manifest = store.read_json(path)
    audio_path = str(manifest.get("audio_path") or "")
    return bool(audio_path) and Path(audio_path).is_file()


def _write_placeholder_stage(store: NewsProjectStore, root: Path, stage_name: str) -> Path:
    path = root / "logs" / f"{stage_name}.json"
    store.write_json(path, {"stage": stage_name, "status": "not_implemented_in_phase_ab"})
    return path


def _load_channel_voice_config(channel_id: str) -> dict[str, Any]:
    return _load_channel_config(channel_id).get("voice", {})


def _load_channel_workflow_config(channel_id: str) -> dict[str, Any]:
    return _load_channel_config(channel_id).get("voice_workflow", {})


def _load_channel_config(channel_id: str) -> dict[str, Any]:
    from src.config_resolver.paths import resolve_application_paths

    path = (
        resolve_application_paths().channels_root
        / channel_id
        / "channel_config.json"
    )
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data
