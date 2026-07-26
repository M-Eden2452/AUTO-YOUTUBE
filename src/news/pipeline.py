from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from src.audio.scene_timeline import apply_timeline_to_script, build_scene_timeline

from .article_ingestor import ArticleIngestionError, ingest_article, load_text_file
from .asset_manager import build_news_asset_manifest
from .exporter import export_localization
from .final_renderer import render_final_video
from .models import INPUT_MODE_TEXT, INPUT_MODE_TOPIC, INPUT_MODE_URL, NEWS_TO_SHORT_STAGES, NewsJob
from .preview_renderer import render_preview
from .project_store import NewsProjectStore
from .quality_check import run_quality_check
from .research_engine import build_research
from .script_generator import build_script
from .subtitles import build_subtitles
from .visual_plan import build_visual_plan
from .voice_stage import build_or_generate_voice_manifest


@dataclass
class NewsPipelineResult:
    job_id: str
    status: str
    project_root: Path
    completed_stages: list[str]


def create_news_to_short_job(
    *,
    projects_root: str | Path = "projects",
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
    root = Path(projects_root)
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
        now=now,
        is_taken=existing_ids,
    )
    store.create_project(job)
    return job


def run_news_to_short_job(
    *,
    projects_root: str | Path = "projects",
    job_id: str,
    dry_run: bool = False,
    until_stage: str | None = None,
    stage: str | None = None,
    resume: bool = False,
    force_stage: bool = False,
    execute_voice: bool = False,
    voice_profile_override: str | None = None,
) -> NewsPipelineResult:
    store = NewsProjectStore(projects_root)
    job = store.load_job(job_id)
    root = store.project_root(job_id)
    stop_stage = until_stage or ("asset_search" if dry_run else None)
    stages = [stage] if stage else NEWS_TO_SHORT_STAGES
    completed = store.completed_stage_names(job)
    ran: list[str] = []
    for stage_name in stages:
        if stage_name not in NEWS_TO_SHORT_STAGES:
            raise ValueError(f"Unknown news_to_short stage: {stage_name}")
        if resume and stage_name in completed and not force_stage:
            continue
        if not force_stage and stage_name in completed and not stage:
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
        )
        ran.append(stage_name)
        if stage_name == stop_stage:
            break
    if not dry_run:
        quality_path = root / "quality" / "quality_report.json"
        final_render_path = root / "render" / "final_render_manifest.json"
        if quality_path.exists():
            quality_status = store.read_json(quality_path).get("status")
            final_render = store.read_json(final_render_path) if final_render_path.exists() else {}
            has_final_output = bool(final_render.get("output_path")) and Path(final_render.get("output_path", "")).exists()
            job.status = "completed" if quality_status == "passed" and has_final_output else "needs_review"
        else:
            job.status = "completed"
    else:
        job.status = "dry_run_completed"
    if stop_stage and stop_stage not in ran and stop_stage in completed:
        job.status = "dry_run_completed" if dry_run else job.status
    store.save_job(job)
    return NewsPipelineResult(job_id=job.job_id, status=job.status, project_root=root, completed_stages=ran)


def run_news_to_short_cli(args: Any) -> NewsPipelineResult:
    projects_root = Path(getattr(args, "projects_root", "projects"))
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
) -> None:
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
        )
    except Exception as exc:
        store.update_stage(job, stage_name, status="failed", error=str(exc))
        raise
    store.update_stage(job, stage_name, status="completed", result_path=str(result_path))


def _dispatch_stage(
    stage_name: str,
    store: NewsProjectStore,
    job: NewsJob,
    root: Path,
    *,
    dry_run: bool,
    execute_voice: bool = False,
    voice_profile_override: str | None = None,
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
        plan = build_visual_plan(script, language=job.language, user_assets=job.user_assets)
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
        return root / "assets" / "assets_manifest.json"
    if stage_name == "voice":
        script_path = root / "localizations" / job.language / "script" / "script.json"
        script = store.read_json(script_path)
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
        )
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
        script = store.read_json(root / "localizations" / job.language / "script" / "script.json")
        manifest = build_subtitles(script, root / "localizations" / job.language / "subtitles")
        store.write_json(root / "localizations" / job.language / "subtitles" / "subtitles_manifest.json", manifest)
        return root / "localizations" / job.language / "subtitles" / "subtitles_manifest.json"
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
        )
        store.write_json(root / "quality" / "quality_report.json", report)
        return root / "quality" / "quality_report.json"
    if stage_name == "final_render":
        quality = store.read_json(root / "quality" / "quality_report.json")
        if quality.get("status") != "passed":
            manifest = {
                "status": "blocked",
                "reason": "quality_check_requires_review",
                "output_path": "",
            }
        else:
            script = store.read_json(root / "localizations" / job.language / "script" / "script.json")
            visual = store.read_json(root / "localizations" / job.language / "visual" / "visual_plan.json")
            assets = store.read_json(root / "assets" / "assets_manifest.json")
            voice = store.read_json(root / "localizations" / job.language / "voice" / "voice_manifest.json")
            manifest = render_final_video(
                project_root=root,
                language=job.language,
                script=script,
                visual_plan=visual,
                assets_manifest=assets,
                voice_manifest=voice,
            )
        store.write_json(root / "render" / "final_render_manifest.json", manifest)
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
) -> dict[str, Any]:
    channel_config = _load_channel_config(job.channel_id)
    manifest = build_news_asset_manifest(
        visual_plan=visual_plan,
        user_assets=job.user_assets,
        dry_run=dry_run,
        channel=job.channel_id,
        asset_selection=channel_config.get("asset_selection", {}),
        project_root=project_root,
        project_id=job.job_id,
    )
    return {"mode": job.mode, **manifest}


def _write_placeholder_stage(store: NewsProjectStore, root: Path, stage_name: str) -> Path:
    path = root / "logs" / f"{stage_name}.json"
    store.write_json(path, {"stage": stage_name, "status": "not_implemented_in_phase_ab"})
    return path


def _load_channel_voice_config(channel_id: str) -> dict[str, Any]:
    return _load_channel_config(channel_id).get("voice", {})


def _load_channel_workflow_config(channel_id: str) -> dict[str, Any]:
    return _load_channel_config(channel_id).get("voice_workflow", {})


def _load_channel_config(channel_id: str) -> dict[str, Any]:
    path = Path("channels") / channel_id / "channel_config.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data
