"""Offline integration coverage for autonomous draft completion.

Everything in this module lives under ``TemporaryDirectory``. Asset search, rendering
and the voice stage are replaced at their orchestration boundaries; no provider,
network, TTS, LLM, Vision or image-generation call is possible.
"""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from PIL import Image

from src.assets.completion import (
    ASSEMBLY_COMPOSITE,
    ASSEMBLY_EXACT,
    ASSEMBLY_FALLBACK,
    ASSEMBLY_PARTIAL,
    BLOCK_FACTUALLY_MISLEADING,
    BLOCK_MUST_AVOID,
    BLOCK_RIGHTS,
    MODE_DRAFT_COMPLETE,
    MODE_STRICT,
    PRIORITY_CRITICAL,
    SLOT_FALLBACK,
    SLOT_PRIMARY,
    TIER_EMERGENCY,
    TIER_EXACT,
    TIER_PARTIAL,
    SceneVisualAssembly,
    attach_assembly,
    blocking_reasons,
    build_replacement_report,
    evaluate_usability,
    read_assembly,
)
from src.assets.completion.assembly import slot_from_asset
from src.assets.semantic_selection.decision import (
    DECISION_KEY,
    FRAMING_VERTICAL_READY,
    SUPPORT_FULL,
    SUPPORT_PARTIAL,
    VERDICT_COMPLETE,
    VERDICT_PARTIAL,
    SelectionDecision,
)
from src.content.script_engine.adaptation import (
    ADAPT_LIGHT,
    ADAPT_NONE,
    SceneAdaptationProposal,
)
from src.content_creation.cli import _request_from_args, build_parser
from src.news.draft_completion import (
    _replan,
    evaluate_draft_render_gate,
    run_adaptation_pass,
    script_paths,
)
from src.news.models import (
    INPUT_MODE_TEXT,
    MODE_NEWS_TO_SHORT,
    NewsJob,
    completion_settings,
)
from src.news.pipeline import (
    _dispatch_stage,
    build_asset_search_manifest,
    run_news_to_short_job,
)
from src.news.project_store import NewsProjectStore
from src.news.quality_check import run_quality_check


def _job(
    *,
    title: str,
    completion_mode: str = "",
    now: str = "2026-07-27T10:00:00+00:00",
) -> NewsJob:
    return NewsJob.create(
        channel_id="offline_fixture",
        input_mode=INPUT_MODE_TEXT,
        title=title,
        topic="Nanoplastic transport",
        input_text="Offline fixture input.",
        completion_mode=completion_mode,
        now=now,
    )


def _png(path: Path, index: int) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    color = ((index * 31) % 255, (index * 67) % 255, (index * 97) % 255)
    Image.new("RGB", (108, 192), color).save(path, format="PNG")
    return path


def _asset(
    *,
    path: Path,
    scene_id: str,
    support: str = SUPPORT_FULL,
    missing: list[str] | None = None,
) -> dict:
    missing = list(missing or [])
    asset_id = f"generated_{scene_id}_{path.stem}"
    checksum = hashlib.sha256(path.read_bytes()).hexdigest()
    decision = SelectionDecision(
        scene_id=scene_id,
        asset_id=asset_id,
        provider="generated",
        provider_confidence=1.0,
        semantic_score=100.0 if support == SUPPORT_FULL else 70.0,
        semantic_status="matched",
        metadata_score=100.0,
        metadata_status="matched",
        technical_score=100.0,
        technical_status=FRAMING_VERTICAL_READY,
        framing={"status": FRAMING_VERTICAL_READY, "crop": "center"},
        rights_status="user_owned",
        rights_allowed_for_render=True,
        rights_review_required=False,
        slots={
            "matched_slots": ["subject"],
            "missing_slots": missing,
            "missing_required_slots": missing,
            "conflicting_slots": [],
            "undecidable_slots": [],
            "details": [],
        },
        slot_verdict=VERDICT_COMPLETE if support == SUPPORT_FULL else VERDICT_PARTIAL,
        support_status=support,
        support_requirements=[],
        selection_reasons=["offline_fixture_evidence"],
        reject_reasons=[],
    )
    source_url = f"project://offline-fixture/{asset_id}"
    license_data = {
        "license_name": "project_generated",
        "rights_status": "user_owned",
        "commercial_use_allowed": True,
        "modification_allowed": True,
        "attribution_required": False,
        "allowed_for_render": True,
        "review_required": False,
    }
    provenance = {
        "provider": "generated",
        "provider_asset_id": asset_id,
        "source_page_url": source_url,
        "original_filename": path.name,
        "checksum_sha256": checksum,
        "project_id": "offline_fixture",
        "scene_id": scene_id,
    }
    return {
        "schema_version": 1,
        "asset_id": asset_id,
        "provider": "generated",
        "provider_asset_id": asset_id,
        "type": "image",
        "media_type": "image",
        "title": f"Neutral nanoplastic context {scene_id}",
        "description": "Deterministic project-owned test image.",
        "path": str(path),
        "local_path": str(path),
        "source_page_url": source_url,
        "source_url": source_url,
        "width": 108,
        "height": 192,
        "orientation": "vertical",
        "checksum_sha256": checksum,
        "rights_status": "user_owned",
        "allowed_for_render": True,
        "review_required": False,
        "license": license_data,
        "provenance": provenance,
        "technical_validation": {
            "status": "passed",
            "media_type": "image",
            "width": 108,
            "height": 192,
            "format": "png",
        },
        DECISION_KEY: decision.to_dict(),
    }


def _scene_entry(
    *,
    root: Path,
    scene_id: str,
    index: int,
    narration: str,
    duration: float = 5.0,
    tier: str = TIER_EXACT,
    support: str = SUPPORT_FULL,
) -> dict:
    path = _png(root / "fixture_assets" / f"{scene_id}_{index}.png", index)
    missing = ["exact_sampling_action"] if support == SUPPORT_PARTIAL else []
    asset = _asset(path=path, scene_id=scene_id, support=support, missing=missing)
    verdict = evaluate_usability(
        asset,
        mode=MODE_DRAFT_COMPLETE,
        quality_tier=tier,
        require_local_file=True,
    )
    purpose = SLOT_FALLBACK if tier == TIER_EMERGENCY else SLOT_PRIMARY
    slot = slot_from_asset(
        asset,
        slot_id=f"{scene_id}_slot_001",
        purpose=purpose,
        start_offset_sec=0.0,
        end_offset_sec=duration,
        quality_tier=tier,
        usability=verdict,
        required_subject="nanoplastic particles",
        required_action="sampling and measurement",
        required_location="Antarctic snow",
        ladder_level=tier,
    )
    if tier == TIER_EMERGENCY:
        status = ASSEMBLY_FALLBACK
    elif support == SUPPORT_PARTIAL:
        status = ASSEMBLY_PARTIAL
    else:
        status = ASSEMBLY_EXACT
    assembly = SceneVisualAssembly(
        scene_id=scene_id,
        scene_duration_sec=duration,
        assembly_status=status,
        support_status=support,
        completion_mode=MODE_DRAFT_COMPLETE,
        slots=[slot],
        ladder_trace=[f"offline:{tier}"],
    )
    entry = {
        "scene_id": scene_id,
        "narration": narration,
        "required_duration_sec": duration,
        "visual_type": "image",
        "resolution_status": "resolved" if assembly.publish_ready else "resolved_needs_review",
        "visual_brief": {
            "subject": "nanoplastic particles",
            "action": "sampling and measurement",
            "place": "Antarctic snow",
            "must_avoid": ["unrelated wildlife presented as a sample"],
            "provider_queries": {
                "manual": [f"nanoplastic Antarctic sampling scene {index}"],
            },
        },
        "query_plan": {
            "queries": [
                {
                    "language": "en",
                    "query": f"nanoplastic Antarctic sampling scene {index}",
                }
            ]
        },
        "ranked_candidates": [asset],
    }
    return attach_assembly(entry, assembly)


_NANOPLASTIC_NARRATION = [
    "Нанопластик обнаруживают даже в удалённых снежных районах.",
    "Исследователи отбирают пробы, не смешивая разные слои снега.",
    "Размер частиц измеряют лабораторными методами.",
    "Воздушные потоки могут переносить частицы на большие расстояния.",
    "Каждая проба получает отдельную маркировку и контроль качества.",
    "Кадр показывает контекст отбора, но не точное действие прибора.",
    "Результаты сопоставляют с направлением ветра и местом отбора.",
    "Нейтральная карточка сохраняет факт, пока точный материал не найден.",
]


def _nanoplastic_fixture(root: Path) -> tuple[dict, dict, dict]:
    scenes: list[dict] = []
    entries: list[dict] = []
    plan_scenes: list[dict] = []
    for index, narration in enumerate(_NANOPLASTIC_NARRATION, start=1):
        scene_id = f"scene_{index:03d}"
        tier = TIER_PARTIAL if index == 6 else TIER_EMERGENCY if index == 8 else TIER_EXACT
        support = SUPPORT_PARTIAL if index in {6, 8} else SUPPORT_FULL
        scenes.append(
            {
                "scene_id": scene_id,
                "narration": narration,
                "target_duration_sec": 5.0,
                "actual_duration_sec": 5.0,
                "start_sec": float((index - 1) * 5),
            }
        )
        entry = _scene_entry(
            root=root,
            scene_id=scene_id,
            index=index,
            narration=narration,
            tier=tier,
            support=support,
        )
        entries.append(entry)
        plan_scenes.append(
            {
                "scene_id": scene_id,
                "visual_brief": dict(entry["visual_brief"]),
                "required_duration_sec": 5.0,
            }
        )
    script = {
        "language": "ru",
        "estimated_duration_sec": 40.0,
        "narration_text": "\n".join(_NANOPLASTIC_NARRATION),
        "scenes": scenes,
    }
    manifest = {
        "schema_version": 1,
        "mode": MODE_NEWS_TO_SHORT,
        "scenes": entries,
        "missing_scenes": [],
        "completion": {
            "mode": MODE_DRAFT_COMPLETE,
            "reuse": {"uses": {}, "scenes": {}, "repeated_assets": {}},
        },
    }
    visual_plan = {
        "language": "ru",
        "resolution": {"width": 1080, "height": 1920},
        "scenes": plan_scenes,
    }
    return script, manifest, visual_plan


def _write_render_inputs(
    *,
    store: NewsProjectStore,
    job: NewsJob,
    root: Path,
    script: dict,
    manifest: dict,
    visual_plan: dict,
    audio_path: Path,
    quality_status: str,
) -> None:
    store.write_json(root / "localizations" / job.language / "script" / "script.json", script)
    store.write_json(
        root / "localizations" / job.language / "visual" / "visual_plan.json",
        visual_plan,
    )
    store.write_json(root / "assets" / "assets_manifest.json", manifest)
    store.write_json(
        root / "localizations" / job.language / "voice" / "voice_manifest.json",
        {"status": "completed", "audio_path": str(audio_path)},
    )
    store.write_json(root / "quality" / "quality_report.json", {"status": quality_status})


def _write_completed_resume_outputs(
    *,
    store: NewsProjectStore,
    job: NewsJob,
    root: Path,
) -> None:
    scene = {"scene_id": "scene_001"}
    store.write_json(root / "research" / "claims.json", {"claims": []})
    store.write_json(
        root / "localizations" / job.language / "script" / "script.json",
        {
            "narration_text": "Offline completion fixture narration.",
            "scenes": [scene],
        },
    )
    visual_plan = {"scenes": [scene]}
    store.write_json(
        root / "localizations" / job.language / "visual" / "visual_plan.json",
        visual_plan,
    )
    # A resumable fixture, so the manifest carries the input fingerprint production
    # stamps on it. Without one it would be a legacy artifact and resume would refuse
    # to reuse it, which is a different contract than the one these tests assert.
    from src.news.pipeline import (
        ASSET_SEARCH_FINGERPRINT_KEY,
        _channel_asset_selection,
        asset_search_fingerprint,
    )

    store.write_json(
        root / "assets" / "assets_manifest.json",
        {
            "schema_version": 1,
            "scenes": [scene],
            "missing_scenes": [],
            ASSET_SEARCH_FINGERPRINT_KEY: asset_search_fingerprint(
                job,
                visual_plan,
                dry_run=False,
                asset_selection=_channel_asset_selection(job.channel_id),
            ),
        },
    )


class _VisualOnlyAdapter:
    adapter_id = "offline_visual_only"
    paid = False

    def __init__(self) -> None:
        self.calls = 0

    def adapt(self, request) -> SceneAdaptationProposal:
        self.calls += 1
        return SceneAdaptationProposal(
            scene_id=request.scene_id,
            narration=request.narration,
            visual_parts=[
                "Нанопластик в снежной пробе",
                "Лабораторное измерение частиц",
            ],
            revised_brief={"media_types": ["image"]},
            rules_applied=["split_into_visual_parts"],
            reasons=["offline no-improvement fixture"],
        )


class CompletionModeWiringTests(unittest.TestCase):
    def test_cli_job_round_trip_and_old_job_keep_strict_as_the_default(self) -> None:
        parser = build_parser()
        draft_request = _request_from_args(
            parser.parse_args(["create", "--completion-mode", MODE_DRAFT_COMPLETE])
        )
        default_request = _request_from_args(parser.parse_args(["create"]))

        self.assertEqual(draft_request.completion_mode, MODE_DRAFT_COMPLETE)
        self.assertEqual(default_request.completion_mode, "")

        draft_job = _job(title="Explicit draft", completion_mode=draft_request.completion_mode)
        restored = NewsJob.from_dict(draft_job.to_dict())
        self.assertEqual(completion_settings(restored)["mode"], MODE_DRAFT_COMPLETE)
        self.assertEqual(completion_settings(restored)["script_adaptation"], ADAPT_LIGHT)

        strict_job = _job(title="Implicit strict")
        self.assertEqual(completion_settings(strict_job)["mode"], MODE_STRICT)
        self.assertEqual(completion_settings(strict_job)["script_adaptation"], ADAPT_NONE)

        legacy = NewsJob.from_dict(
            {
                "job_id": "legacy_job",
                "mode": MODE_NEWS_TO_SHORT,
                "channel_id": "legacy_channel",
                "input_mode": INPUT_MODE_TEXT,
            }
        )
        self.assertEqual(completion_settings(legacy)["mode"], MODE_STRICT)
        self.assertEqual(completion_settings(legacy)["script_adaptation"], ADAPT_NONE)

    def test_build_asset_search_manifest_passes_the_resolved_completion_mode(self) -> None:
        visual_plan = {"scenes": []}
        with (
            patch("src.news.pipeline._load_channel_config", return_value={}),
            patch(
                "src.news.pipeline.build_news_asset_manifest",
                return_value={"schema_version": 1, "scenes": [], "missing_scenes": []},
            ) as build,
        ):
            for requested, expected in (
                ("", MODE_STRICT),
                (MODE_DRAFT_COMPLETE, MODE_DRAFT_COMPLETE),
            ):
                with self.subTest(requested=requested):
                    job = _job(title=f"Mode {expected}", completion_mode=requested)
                    manifest = build_asset_search_manifest(
                        job,
                        visual_plan,
                        dry_run=True,
                        project_root=Path("unused_offline_root"),
                    )
                    self.assertEqual(manifest["mode"], MODE_NEWS_TO_SHORT)
                    self.assertEqual(
                        build.call_args.kwargs["completion_mode"],
                        expected,
                    )

    def test_resume_restarts_asset_search_when_completion_semantics_change(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            projects = Path(tmp) / "projects"
            store = NewsProjectStore(projects)
            for index, (initial_mode, override) in enumerate(
                (
                    (MODE_STRICT, {"completion_mode": MODE_DRAFT_COMPLETE}),
                    (MODE_DRAFT_COMPLETE, {"script_adaptation": ADAPT_NONE}),
                ),
                start=1,
            ):
                with self.subTest(initial_mode=initial_mode, override=override):
                    job = _job(
                        title=f"Completion override {index}",
                        completion_mode=initial_mode,
                        now=f"2026-07-27T11:0{index}:00+00:00",
                    )
                    project = store.create_project(job).root
                    _write_completed_resume_outputs(
                        store=store,
                        job=job,
                        root=project,
                    )
                    for state in job.stages.values():
                        state.status = "completed"
                        state.finished_at = "2026-07-27T11:30:00+00:00"
                    store.save_job(job)
                    old_output = project / "render" / "old-final.mp4"
                    old_output.parent.mkdir(parents=True, exist_ok=True)
                    old_output.write_bytes(b"stale output")
                    store.write_json(
                        project / "quality" / "quality_report.json",
                        {"status": "passed"},
                    )
                    store.write_json(
                        project / "render" / "final_render_manifest.json",
                        {"status": "completed", "output_path": str(old_output)},
                    )

                    with patch("src.news.pipeline._run_stage") as run_stage:
                        result = run_news_to_short_job(
                            projects_root=projects,
                            job_id=job.job_id,
                            until_stage="asset_search",
                            resume=True,
                            **override,
                        )

                    stored = store.load_job(job.job_id)
                    self.assertEqual(result.completed_stages, ["asset_search"])
                    self.assertEqual(result.status, "in_progress")
                    self.assertEqual(run_stage.call_count, 1)
                    self.assertEqual(
                        run_stage.call_args.args[0],
                        "asset_search",
                    )
                    for stage_name in (
                        "asset_search",
                        "voice",
                        "subtitles",
                        "preview_render",
                        "quality_check",
                        "final_render",
                        "export",
                    ):
                        self.assertEqual(stored.stages[stage_name].status, "stale")
                        self.assertEqual(
                            stored.stages[stage_name].settings["stale_reason"],
                            "completion_settings_changed",
                        )

    def test_resume_keeps_completed_asset_search_when_override_is_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            projects = Path(tmp) / "projects"
            store = NewsProjectStore(projects)
            job = _job(
                title="Unchanged completion setting",
                completion_mode=MODE_DRAFT_COMPLETE,
                now="2026-07-27T11:10:00+00:00",
            )
            project = store.create_project(job).root
            _write_completed_resume_outputs(
                store=store,
                job=job,
                root=project,
            )
            for state in job.stages.values():
                state.status = "completed"
            store.save_job(job)

            with patch("src.news.pipeline._run_stage") as run_stage:
                result = run_news_to_short_job(
                    projects_root=projects,
                    job_id=job.job_id,
                    until_stage="asset_search",
                    resume=True,
                    completion_mode=MODE_DRAFT_COMPLETE,
                )

            self.assertEqual(result.completed_stages, [])
            run_stage.assert_not_called()

    def test_only_an_invalidated_quality_report_loses_its_say_over_job_status(self) -> None:
        """A stage that never ran is not the same as one deliberately invalidated.

        Both leave ``quality_check`` in a non-completed state, but only ``stale`` means
        the stored verdict was measured under different semantics. Requiring
        ``completed`` here once silently downgraded a blocked final render from
        ``needs_review`` to ``in_progress``, hiding the review signal.
        """
        for stage_status, report_status, expected in (
            ("pending", "needs_review", "needs_review"),
            ("stale", "passed", "in_progress"),
        ):
            with self.subTest(quality_stage=stage_status):
                with tempfile.TemporaryDirectory() as tmp:
                    projects = Path(tmp) / "projects"
                    store = NewsProjectStore(projects)
                    job = _job(
                        title=f"Quality authority {stage_status}",
                        now="2026-07-27T12:00:00+00:00",
                    )
                    store.create_project(job)
                    job.stages["quality_check"].status = stage_status
                    store.save_job(job)
                    store.write_json(
                        projects / job.job_id / "quality" / "quality_report.json",
                        {"status": report_status},
                    )

                    with patch("src.news.pipeline._run_stage"):
                        result = run_news_to_short_job(
                            projects_root=projects,
                            job_id=job.job_id,
                            stage="final_render",
                        )

                    self.assertEqual(result.status, expected)


class QualityAndRenderGateTests(unittest.TestCase):
    def test_partial_support_is_draft_reviewable_but_fails_the_strict_publish_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            narration = "Нанопластик обнаружили в снежной пробе."
            script = {
                "estimated_duration_sec": 40.0,
                "scenes": [{"scene_id": "scene_001", "narration": narration}],
            }
            exact = {
                "schema_version": 1,
                "scenes": [
                    _scene_entry(
                        root=root,
                        scene_id="scene_001",
                        index=1,
                        narration=narration,
                    )
                ],
                "missing_scenes": [],
            }
            partial = {
                "schema_version": 1,
                "scenes": [
                    _scene_entry(
                        root=root,
                        scene_id="scene_001",
                        index=2,
                        narration=narration,
                        tier=TIER_PARTIAL,
                        support=SUPPORT_PARTIAL,
                    )
                ],
                "missing_scenes": [],
            }
            common = {
                "script": script,
                "research": {"claims": [{"safe_for_script": True}]},
                "voice_manifest": {"status": "completed"},
                "subtitles_manifest": {"srt_path": "offline.srt", "ass_path": "offline.ass"},
            }

            exact_strict = run_quality_check(
                assets_manifest=exact,
                completion_mode=MODE_STRICT,
                **common,
            )
            partial_strict = run_quality_check(
                assets_manifest=partial,
                completion_mode=MODE_STRICT,
                **common,
            )
            partial_draft = run_quality_check(
                assets_manifest=partial,
                completion_mode=MODE_DRAFT_COMPLETE,
                **common,
            )

        self.assertEqual(exact_strict["status"], "passed")
        self.assertEqual(partial_strict["status"], "failed")
        self.assertIn("asset_publish_readiness", {item["check"] for item in partial_strict["errors"]})
        self.assertEqual(partial_draft["status"], "needs_review")
        self.assertEqual(partial_draft["errors"], [])
        self.assertIn("asset_publish_readiness", {item["check"] for item in partial_draft["warnings"]})

    def test_pipeline_final_render_uses_separate_strict_and_draft_gates_without_ffmpeg(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            projects = Path(tmp) / "projects"
            store = NewsProjectStore(projects)
            strict_job = _job(title="Strict render", now="2026-07-27T11:00:00+00:00")
            draft_job = _job(
                title="Draft render",
                completion_mode=MODE_DRAFT_COMPLETE,
                now="2026-07-27T12:00:00+00:00",
            )
            strict_root = store.create_project(strict_job).root
            draft_root = store.create_project(draft_job).root
            script, manifest, visual_plan = _nanoplastic_fixture(Path(tmp) / "shared")
            audio = Path(tmp) / "narration.wav"
            audio.write_bytes(b"offline narration")
            for job, root in ((strict_job, strict_root), (draft_job, draft_root)):
                _write_render_inputs(
                    store=store,
                    job=job,
                    root=root,
                    script=script,
                    manifest=manifest,
                    visual_plan=visual_plan,
                    audio_path=audio,
                    quality_status="failed",
                )

            rendered = {
                "status": "completed",
                "render_status": "draft_completed",
                "output_path": str(Path(tmp) / "mocked_draft.mp4"),
            }
            with (
                patch("src.news.pipeline.render_final_video", return_value=dict(rendered)) as render,
                patch("src.news.pipeline.write_completion_report", return_value={}) as report,
            ):
                strict_path = _dispatch_stage(
                    "final_render",
                    store,
                    strict_job,
                    strict_root,
                    dry_run=False,
                )
                strict_manifest = store.read_json(strict_path)
                self.assertEqual(render.call_count, 0)

                draft_path = _dispatch_stage(
                    "final_render",
                    store,
                    draft_job,
                    draft_root,
                    dry_run=False,
                )
                draft_manifest = store.read_json(draft_path)

        self.assertEqual(strict_manifest["status"], "blocked")
        self.assertEqual(strict_manifest["reason"], "quality_check_requires_review")
        self.assertEqual(render.call_count, 1)
        self.assertEqual(
            render.call_args.kwargs["completion_mode"],
            MODE_DRAFT_COMPLETE,
        )
        self.assertEqual(draft_manifest["draft_render_gate"]["status"], "allowed")
        self.assertFalse(draft_manifest["publish_ready"])
        report.assert_called_once()


class PipelineTerminalStateTests(unittest.TestCase):
    def test_missing_voice_returns_actionable_status_and_keeps_all_replacement_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            projects = Path(tmp) / "projects"
            store = NewsProjectStore(projects)
            job = _job(
                title="Voice required",
                completion_mode=MODE_DRAFT_COMPLETE,
                now="2026-07-27T13:00:00+00:00",
            )
            root = store.create_project(job).root
            script, manifest, _ = _nanoplastic_fixture(root)
            store.write_json(
                root / "localizations" / job.language / "script" / "script.json",
                script,
            )
            store.write_json(root / "assets" / "assets_manifest.json", manifest)

            voice_manifest_path = (
                root
                / "localizations"
                / job.language
                / "voice"
                / "voice_manifest.json"
            )
            with patch(
                "src.news.pipeline._run_stage",
                return_value=voice_manifest_path,
            ) as voice_stage:
                result = run_news_to_short_job(
                    projects_root=projects,
                    job_id=job.job_id,
                    stage="voice",
                    execute_voice=False,
                )

            replacement_root = root / "replacement"
            expected = [
                replacement_root / "replacement_report.json",
                replacement_root / "replacement_report.html",
                replacement_root / "replacement_queue.json",
                replacement_root / "timeline_replacement_map.csv",
            ]
            report = json.loads(expected[0].read_text(encoding="utf-8"))
            reports_exist = all(path.is_file() for path in expected)
            stored_status = store.load_job(job.job_id).status

        voice_stage.assert_called_once()
        self.assertEqual(result.status, "voice_provider_required")
        self.assertEqual(stored_status, "voice_provider_required")
        self.assertTrue(reports_exist)
        self.assertEqual(report["summary"]["scenes_usable_in_draft"], 8)
        self.assertGreater(report["summary"]["weak_fragment_count"], 0)


class AdaptationRollbackTests(unittest.TestCase):
    def test_two_adaptation_replans_accumulate_usage_without_reusing_proposed_scenes(
        self,
    ) -> None:
        job = _job(title="Cumulative semantic usage", completion_mode=MODE_DRAFT_COMPLETE)
        script = {
            "title": "Cumulative semantic usage",
            "language": "ru",
            "scenes": [
                {
                    "scene_id": "scene_001",
                    "index": 1,
                    "narration": "Original narration.",
                    "target_duration_sec": 5.0,
                }
            ],
        }
        original_plan = {
            "planning_metadata": {
                "semantic_brief_usage": {
                    "backend": "openai",
                    "model": "fixture-model",
                    "calls": 1,
                    "maximum_calls_per_project": 8,
                    "estimated_cost_usd": 0.01,
                }
            },
            "scenes": [{"scene_id": "scene_001", "marker": "original"}],
        }
        fresh_plans = [
            {
                "planning_metadata": {
                    "semantic_brief_usage": {
                        "backend": "openai",
                        "model": "fixture-model",
                        "calls": 2,
                        "maximum_calls_per_project": 8,
                        "estimated_cost_usd": 0.02,
                    }
                },
                "scenes": [{"scene_id": "scene_001", "marker": "proposed"}],
            },
            {
                "planning_metadata": {
                    "semantic_brief_usage": {
                        "backend": "openai",
                        "model": "fixture-model",
                        "calls": 3,
                        "maximum_calls_per_project": 8,
                        "estimated_cost_usd": 0.03,
                    }
                },
                "scenes": [{"scene_id": "scene_001", "marker": "accepted"}],
            },
        ]
        with patch("src.news.visual_plan.build_visual_plan", side_effect=fresh_plans):
            proposed = _replan(
                script, job=job, research={}, visual_plan=original_plan
            )
            accepted = _replan(
                script,
                job=job,
                research={},
                visual_plan=original_plan,
                usage_plan=proposed,
            )

        usage = accepted["planning_metadata"]["semantic_brief_usage"]
        self.assertEqual(usage["calls"], 6)
        self.assertEqual(usage["estimated_cost_usd"], 0.06)
        self.assertEqual(accepted["scenes"][0]["marker"], "original")

    def test_no_change_adaptation_persists_cumulative_semantic_usage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            projects = Path(tmp) / "projects"
            store = NewsProjectStore(projects)
            job = _job(
                title="Cumulative usage persisted",
                completion_mode=MODE_DRAFT_COMPLETE,
            )
            root = store.create_project(job).root
            narration = "Nanoplastic was measured in Antarctic snow."
            script = {
                "title": job.title,
                "language": job.language,
                "scenes": [
                    {
                        "scene_id": "scene_001",
                        "index": 1,
                        "narration": narration,
                        "target_duration_sec": 5.0,
                    }
                ],
            }
            entry = _scene_entry(
                root=root,
                scene_id="scene_001",
                index=1,
                narration=narration,
                tier=TIER_PARTIAL,
                support=SUPPORT_PARTIAL,
            )
            manifest = {
                "schema_version": 1,
                "scenes": [entry],
                "missing_scenes": [],
                "completion": {"mode": MODE_DRAFT_COMPLETE, "reuse": {}},
            }
            original_plan = {
                "planning_metadata": {
                    "semantic_brief_usage": {
                        "backend": "openai",
                        "model": "fixture-model",
                        "calls": 1,
                        "maximum_calls_per_project": 8,
                        "estimated_cost_usd": 0.01,
                    }
                },
                "scenes": [
                    {
                        "scene_id": "scene_001",
                        "marker": "original",
                        "visual_brief": dict(entry["visual_brief"]),
                    }
                ],
            }
            fresh_plans = [
                {
                    "planning_metadata": {
                        "semantic_brief_usage": {
                            "backend": "openai",
                            "model": "fixture-model",
                            "calls": 2,
                            "maximum_calls_per_project": 8,
                            "estimated_cost_usd": 0.02,
                        }
                    },
                    "scenes": [{"scene_id": "scene_001", "marker": "proposed"}],
                },
                {
                    "planning_metadata": {
                        "semantic_brief_usage": {
                            "backend": "openai",
                            "model": "fixture-model",
                            "calls": 3,
                            "maximum_calls_per_project": 8,
                            "estimated_cost_usd": 0.03,
                        }
                    },
                    "scenes": [{"scene_id": "scene_001", "marker": "accepted"}],
                },
            ]
            paths = script_paths(root, job.language)
            visual_plan_path = (
                root / "localizations" / job.language / "visual" / "visual_plan.json"
            )
            store.write_json(paths["script"], script)
            store.write_json(visual_plan_path, original_plan)
            store.write_json(root / "assets" / "assets_manifest.json", manifest)
            store.write_json(root / "research" / "claims.json", {"claims": []})

            with patch(
                "src.news.visual_plan.build_visual_plan", side_effect=fresh_plans
            ):
                result = run_adaptation_pass(
                    store=store,
                    job=job,
                    root=root,
                    adapter=_VisualOnlyAdapter(),
                    research_scenes=None,
                )
            persisted = store.read_json(visual_plan_path)

        self.assertEqual(result["status"], "no_change")
        usage = persisted["planning_metadata"]["semantic_brief_usage"]
        self.assertEqual(usage["calls"], 6)
        self.assertEqual(usage["estimated_cost_usd"], 0.06)
        self.assertEqual(persisted["scenes"][0]["marker"], "original")

    def test_one_pass_is_spent_but_unhelpful_adaptation_rolls_back(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            projects = Path(tmp) / "projects"
            store = NewsProjectStore(projects)
            job = _job(
                title="Adaptation rollback",
                completion_mode=MODE_DRAFT_COMPLETE,
                now="2026-07-27T14:00:00+00:00",
            )
            root = store.create_project(job).root
            narration = "Нанопластик обнаружили в 54% исследованных проб."
            script = {
                "estimated_duration_sec": 40.0,
                "narration_text": narration,
                "scenes": [
                    {
                        "scene_id": "scene_001",
                        "narration": narration,
                        "target_duration_sec": 5.0,
                    }
                ],
            }
            entry = _scene_entry(
                root=root,
                scene_id="scene_001",
                index=1,
                narration=narration,
                tier=TIER_PARTIAL,
                support=SUPPORT_PARTIAL,
            )
            manifest = {
                "schema_version": 1,
                "scenes": [entry],
                "missing_scenes": [],
                "completion": {"mode": MODE_DRAFT_COMPLETE, "reuse": {}},
            }
            visual_plan = {
                "resolution": {"width": 1080, "height": 1920},
                "scenes": [
                    {
                        "scene_id": "scene_001",
                        "visual_brief": dict(entry["visual_brief"]),
                    }
                ],
            }
            paths = script_paths(root, job.language)
            store.write_json(paths["script"], script)
            store.write_json(
                root / "localizations" / job.language / "visual" / "visual_plan.json",
                visual_plan,
            )
            store.write_json(root / "assets" / "assets_manifest.json", manifest)
            store.write_json(root / "research" / "claims.json", {"claims": []})
            adapter = _VisualOnlyAdapter()
            research = Mock(return_value=manifest)

            with patch(
                "src.news.draft_completion._replan",
                return_value=visual_plan,
            ):
                first = run_adaptation_pass(
                    store=store,
                    job=job,
                    root=root,
                    adapter=adapter,
                    research_scenes=research,
                )

            second = run_adaptation_pass(
                store=store,
                job=job,
                root=root,
                adapter=adapter,
                research_scenes=research,
            )
            current_script = store.read_json(paths["script"])
            adapted_script = store.read_json(paths["adapted"])
            adaptation_report = store.read_json(paths["adaptation_report"])
            original_exists = paths["original"].is_file()

        self.assertEqual(first["status"], "no_change")
        self.assertEqual(first["changed_scene_ids"], [])
        self.assertEqual(second["reason"], "adaptation_pass_limit_reached")
        self.assertEqual(adapter.calls, 1)
        research.assert_called_once()
        self.assertEqual(completion_settings(job)["adaptation_pass"], 1)
        self.assertEqual(current_script, script)
        self.assertEqual(adapted_script["scenes"][0]["narration"], narration)
        self.assertNotIn("visual_parts", adapted_script["scenes"][0])
        self.assertTrue(original_exists)
        outcome = adaptation_report["scenes"][0]
        self.assertFalse(outcome["accepted"])
        self.assertEqual(outcome["rejection_reason"], "visual_coverage_not_improved")


class ReplacementReportTests(unittest.TestCase):
    def test_report_uses_scaled_scene_timecodes_and_keeps_the_script_diff(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scene_id = "scene_001"
            exact_asset = _asset(
                path=_png(root / "exact.png", 1),
                scene_id=scene_id,
                support=SUPPORT_FULL,
            )
            partial_asset = _asset(
                path=_png(root / "partial.png", 2),
                scene_id=scene_id,
                support=SUPPORT_PARTIAL,
                missing=["instrument_action"],
            )
            exact_verdict = evaluate_usability(
                exact_asset,
                mode=MODE_DRAFT_COMPLETE,
                quality_tier=TIER_EXACT,
                require_local_file=True,
            )
            partial_verdict = evaluate_usability(
                partial_asset,
                mode=MODE_DRAFT_COMPLETE,
                quality_tier=TIER_PARTIAL,
                require_local_file=True,
            )
            slots = [
                slot_from_asset(
                    exact_asset,
                    slot_id="slot_context",
                    purpose=SLOT_PRIMARY,
                    start_offset_sec=0.0,
                    end_offset_sec=2.0,
                    quality_tier=TIER_EXACT,
                    usability=exact_verdict,
                ),
                slot_from_asset(
                    partial_asset,
                    slot_id="slot_instrument",
                    purpose=SLOT_PRIMARY,
                    start_offset_sec=2.0,
                    end_offset_sec=4.0,
                    quality_tier=TIER_PARTIAL,
                    usability=partial_verdict,
                    required_action="instrument measurement",
                ),
            ]
            assembly = SceneVisualAssembly(
                scene_id=scene_id,
                scene_duration_sec=4.0,
                assembly_status=ASSEMBLY_COMPOSITE,
                support_status=SUPPORT_PARTIAL,
                completion_mode=MODE_DRAFT_COMPLETE,
                slots=slots,
            )
            entry = attach_assembly(
                {
                    "scene_id": scene_id,
                    "required_duration_sec": 4.0,
                    "visual_type": "image",
                    "visual_brief": {
                        "subject": "nanoplastic particles",
                        "action": "instrument measurement",
                        "provider_queries": {
                            "manual": ["nanoplastic laboratory instrument close up"],
                        },
                    },
                },
                assembly,
            )
            script = {
                "scenes": [
                    {
                        "scene_id": scene_id,
                        "narration": "Адаптированный текст о частицах.",
                        "start_sec": 10.0,
                        "target_duration_sec": 4.0,
                        "actual_duration_sec": 8.0,
                    }
                ]
            }
            adaptation = {
                "mode": ADAPT_LIGHT,
                "scenes": [
                    {
                        "scene_id": scene_id,
                        "original_narration": "Исходный текст о частицах.",
                        "adapted_narration": "Адаптированный текст о частицах.",
                        "reasons": ["less action-specific"],
                        "changed": True,
                    }
                ],
            }
            report = build_replacement_report(
                project_id="offline_report",
                script=script,
                assets_manifest={"scenes": [entry], "missing_scenes": []},
                completion_mode=MODE_DRAFT_COMPLETE,
                adaptation_report=adaptation,
            )

        self.assertEqual(len(report["fragments"]), 1)
        fragment = report["fragments"][0]
        self.assertEqual(fragment["slot_id"], "slot_instrument")
        self.assertEqual(fragment["start_timecode"], "00:14.0")
        self.assertEqual(fragment["end_timecode"], "00:18.0")
        self.assertIn("nanoplastic laboratory instrument close up", fragment["search_queries"])
        self.assertIn("--slot-id slot_instrument", fragment["replace_command"])
        self.assertEqual(
            report["summary"]["script_diff"],
            [
                {
                    "scene_id": scene_id,
                    "original": "Исходный текст о частицах.",
                    "adapted": "Адаптированный текст о частицах.",
                    "reasons": ["less action-specific"],
                }
            ],
        )

    def test_blocked_fragment_exposes_exact_readiness_reasons(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            narration = "Нанопластик обнаружили в снежной пробе."
            entry = _scene_entry(
                root=root,
                scene_id="scene_001",
                index=1,
                narration=narration,
            )
            asset = entry["visual_assembly"]["slots"][0]["selected_asset"]
            asset["rights_status"] = "blocked"
            asset["allowed_for_render"] = False
            asset["review_required"] = True
            asset["license"].update(
                {
                    "rights_status": "blocked",
                    "allowed_for_render": False,
                    "review_required": True,
                }
            )
            asset[DECISION_KEY]["rights"].update(
                {
                    "status": "blocked",
                    "allowed_for_render": False,
                    "review_required": True,
                }
            )
            report = build_replacement_report(
                project_id="blocked_reason_report",
                script={
                    "scenes": [
                        {
                            "scene_id": "scene_001",
                            "narration": narration,
                            "actual_duration_sec": 5.0,
                        }
                    ]
                },
                assets_manifest={"scenes": [entry], "missing_scenes": []},
                completion_mode=MODE_DRAFT_COMPLETE,
            )

        fragment = report["fragments"][0]
        self.assertEqual(fragment["block_reasons"], [BLOCK_RIGHTS])
        self.assertEqual(fragment["why_weak"], BLOCK_RIGHTS)
        self.assertIn("scene_001", report["summary"]["unresolved_scenes"])

    def test_narration_scene_absent_from_manifest_is_a_critical_timed_fragment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = _scene_entry(
                root=root,
                scene_id="scene_001",
                index=1,
                narration="Первая сцена.",
            )
            report = build_replacement_report(
                project_id="missing_scene_report",
                script={
                    "scenes": [
                        {
                            "scene_id": "scene_001",
                            "narration": "Первая сцена.",
                            "start_sec": 0.0,
                            "actual_duration_sec": 5.0,
                        },
                        {
                            "scene_id": "scene_002",
                            "narration": "Вторая narration scene отсутствует в manifest.",
                            "start_sec": 7.0,
                            "actual_duration_sec": 3.0,
                            "visual_brief": {
                                "subject": "nanoplastic sample",
                                "provider_queries": {
                                    "manual": ["nanoplastic snow sample"],
                                },
                            },
                        },
                    ]
                },
                assets_manifest={"scenes": [first], "missing_scenes": []},
                completion_mode=MODE_DRAFT_COMPLETE,
            )

        self.assertEqual(report["summary"]["scene_count"], 2)
        self.assertIn("scene_002", report["summary"]["unresolved_scenes"])
        missing = next(
            fragment
            for fragment in report["fragments"]
            if fragment["scene_id"] == "scene_002"
        )
        self.assertEqual(missing["replacement_priority"], PRIORITY_CRITICAL)
        self.assertEqual(missing["why_weak"], "no_asset_manifest_entry")
        self.assertEqual(missing["start_timecode"], "00:07.0")
        self.assertEqual(missing["end_timecode"], "00:10.0")
        self.assertEqual(
            {
                "scene_id",
                "slot_id",
                "start_timecode",
                "end_timecode",
                "narration",
                "used_file",
                "provider",
                "source_url",
                "license",
                "support_status",
                "quality_tier",
                "block_reasons",
                "why_weak",
                "what_is_missing",
                "replacement_priority",
                "recommended_material",
                "search_queries",
                "english_search_queries",
                "replace_command",
                "manual_replacement_instructions",
            }
            - missing.keys(),
            set(),
        )

    def test_english_queries_filter_cyrillic_without_translation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            narration = "Нанопластик нашли в снегу Антарктиды."
            entry = _scene_entry(
                root=root,
                scene_id="scene_001",
                index=1,
                narration=narration,
                tier=TIER_PARTIAL,
                support=SUPPORT_PARTIAL,
            )
            entry["visual_brief"] = {
                "subject": "нанопластик",
                "action": "отбор проб",
                "place": "Антарктида",
                "provider_queries": {
                    "manual": [
                        "нанопластик снег Антарктида",
                        "nanoplastic Antarctic snow",
                    ]
                },
            }
            entry["query_plan"] = {
                "queries": [
                    {"language": "ru", "query": "лабораторная проба частиц"},
                    {"language": "en", "query": "laboratory particle sample"},
                    {"language": "en", "query": "снег Антарктиды"},
                ]
            }
            report = build_replacement_report(
                project_id="english_query_report",
                script={
                    "scenes": [
                        {
                            "scene_id": "scene_001",
                            "narration": narration,
                            "actual_duration_sec": 5.0,
                        }
                    ]
                },
                assets_manifest={"scenes": [entry], "missing_scenes": []},
                completion_mode=MODE_DRAFT_COMPLETE,
            )

        fragment = report["fragments"][0]
        self.assertIn("нанопластик снег Антарктида", fragment["search_queries"])
        self.assertIn("лабораторная проба частиц", fragment["search_queries"])
        self.assertIn("нанопластик отбор проб Антарктида", fragment["search_queries"])
        self.assertEqual(
            fragment["english_search_queries"],
            [
                "nanoplastic Antarctic snow",
                "laboratory particle sample",
            ],
        )
        self.assertTrue(all(query.isascii() for query in fragment["english_search_queries"]))


class NanoplasticOfflineRegressionTests(unittest.TestCase):
    def test_all_eight_scenes_are_safe_and_draft_usable_and_weak_scenes_are_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            script, manifest, _ = _nanoplastic_fixture(root)
            audio = root / "narration.wav"
            audio.write_bytes(b"offline narration")

            assemblies = [
                read_assembly(
                    entry,
                    scene_duration_sec=float(entry["required_duration_sec"]),
                )
                for entry in manifest["scenes"]
            ]
            all_slots = [slot for assembly in assemblies for slot in assembly.slots]
            all_blocks = {
                reason
                for slot in all_slots
                for reason in blocking_reasons(
                    slot.selected_asset,
                    require_local_file=True,
                )
            }
            report = build_replacement_report(
                project_id="nanoplastic_offline_8",
                script=script,
                assets_manifest=manifest,
                completion_mode=MODE_DRAFT_COMPLETE,
            )
            gate = evaluate_draft_render_gate(
                script=script,
                assets_manifest=manifest,
                voice_manifest={"status": "completed", "audio_path": str(audio)},
            )

        self.assertEqual(sum(assembly.usable_in_draft for assembly in assemblies), 8)
        self.assertEqual(all_blocks, set())
        self.assertNotIn(BLOCK_RIGHTS, all_blocks)
        self.assertNotIn(BLOCK_FACTUALLY_MISLEADING, all_blocks)
        self.assertNotIn(BLOCK_MUST_AVOID, all_blocks)
        self.assertTrue(all(not slot.usability.rights_blocked for slot in all_slots))
        self.assertTrue(all(not slot.usability.factually_misleading for slot in all_slots))
        self.assertTrue(all(not slot.usability.must_avoid_blocked for slot in all_slots))
        self.assertEqual(gate["status"], "allowed")
        self.assertEqual(report["summary"]["scenes_usable_in_draft"], 8)
        self.assertEqual(report["summary"]["unresolved_scenes"], [])
        weak_scene_ids = {item["scene_id"] for item in report["fragments"]}
        self.assertEqual(weak_scene_ids, {"scene_006", "scene_008"})
        self.assertGreater(report["summary"]["weak_fragment_count"], 0)


if __name__ == "__main__":
    unittest.main()
