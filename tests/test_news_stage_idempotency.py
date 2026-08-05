from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


DOWNSTREAM_STAGE_FAMILIES = (
    "asset_search",
    "voice",
    "subtitles",
    "preview_render",
    "quality_check",
    "final_render",
    "export",
)


class NewsDownstreamStageIdempotencyTests(unittest.TestCase):
    def test_legacy_asset_manifest_remains_a_completed_output(self) -> None:
        from src.news.project_store import NewsProjectStore

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            job, project_root = _completed_project(root, "asset_search")
            store = NewsProjectStore(root)
            store.write_json(
                project_root / "assets" / "assets_manifest.json",
                {
                    "dry_run": True,
                    "provider_order": [],
                    "assets": [],
                    "missing_scenes": [
                        {"scene_id": "scene_001", "reason": "dry_run"}
                    ],
                    "warnings": ["Legacy dry-run manifest."],
                },
            )

            self.assertTrue(store.is_stage_completed(store.load_job(job.job_id), "asset_search"))

    def test_protected_subtitles_remain_completed_without_generated_files(self) -> None:
        from src.news.project_store import NewsProjectStore

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            job, project_root = _completed_project(root, "subtitles")
            store = NewsProjectStore(root)
            store.write_json(
                project_root
                / "localizations"
                / job.language
                / "subtitles"
                / "subtitles_manifest.json",
                {
                    "status": "completed",
                    "language": job.language,
                    "source": "user_supplied",
                    "protected": True,
                    "srt_path": "user-managed-subtitles.srt",
                },
            )

            self.assertTrue(store.is_stage_completed(store.load_job(job.job_id), "subtitles"))

    def test_completed_stage_is_skipped_by_normal_repeat_and_resume(self) -> None:
        from src.news.pipeline import run_news_to_short_job

        for stage in DOWNSTREAM_STAGE_FAMILIES:
            with self.subTest(stage=stage), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                job, _project_root = _completed_project(root, stage)

                with patch(
                    "src.news.pipeline._dispatch_stage",
                    side_effect=AssertionError(f"{stage} unexpectedly re-executed"),
                ) as dispatch:
                    repeated = run_news_to_short_job(
                        projects_root=root,
                        job_id=job.job_id,
                        until_stage=stage,
                    )
                    dispatch.assert_not_called()
                self.assertNotIn(stage, repeated.completed_stages)

                with patch(
                    "src.news.pipeline._dispatch_stage",
                    side_effect=AssertionError(f"{stage} unexpectedly re-executed on resume"),
                ) as dispatch:
                    resumed = run_news_to_short_job(
                        projects_root=root,
                        job_id=job.job_id,
                        resume=True,
                        until_stage=stage,
                    )
                    dispatch.assert_not_called()
                self.assertNotIn(stage, resumed.completed_stages)

    def test_force_stage_reexecutes_completed_stage(self) -> None:
        from src.news.pipeline import run_news_to_short_job

        for stage in DOWNSTREAM_STAGE_FAMILIES:
            with self.subTest(stage=stage), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                job, project_root = _completed_project(root, stage)

                with patch(
                    "src.news.pipeline._dispatch_stage",
                    side_effect=_synthetic_dispatch,
                ) as dispatch:
                    forced = run_news_to_short_job(
                        projects_root=root,
                        job_id=job.job_id,
                        stage=stage,
                        force_stage=True,
                    )

                self.assertIn(stage, forced.completed_stages)
                self.assertEqual(dispatch.call_count, 1)
                self.assertEqual(dispatch.call_args.args[0], stage)
                self.assertTrue(_artifact_path(project_root, job.language, stage).is_file())

    def test_missing_output_reexecutes_completed_stage(self) -> None:
        from src.news.pipeline import run_news_to_short_job

        for stage in DOWNSTREAM_STAGE_FAMILIES:
            with self.subTest(stage=stage), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                job, project_root = _completed_project(root, stage)
                artifact_path = _artifact_path(project_root, job.language, stage)
                artifact_path.unlink()

                with patch(
                    "src.news.pipeline._dispatch_stage",
                    side_effect=_synthetic_dispatch,
                ) as dispatch:
                    recovered = run_news_to_short_job(
                        projects_root=root,
                        job_id=job.job_id,
                        until_stage=stage,
                    )

                self.assertIn(stage, recovered.completed_stages)
                self.assertEqual(dispatch.call_count, 1)
                self.assertTrue(artifact_path.is_file())

    def test_structurally_invalid_output_reexecutes_completed_stage(self) -> None:
        from src.news.pipeline import run_news_to_short_job

        for stage in DOWNSTREAM_STAGE_FAMILIES:
            with self.subTest(stage=stage), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                job, project_root = _completed_project(root, stage)
                artifact_path = _artifact_path(project_root, job.language, stage)
                if artifact_path.suffix == ".json":
                    artifact_path.write_text("{}\n", encoding="utf-8")
                else:
                    artifact_path.write_bytes(b"")

                with patch(
                    "src.news.pipeline._dispatch_stage",
                    side_effect=_synthetic_dispatch,
                ) as dispatch:
                    recovered = run_news_to_short_job(
                        projects_root=root,
                        job_id=job.job_id,
                        resume=True,
                        until_stage=stage,
                    )

                self.assertIn(stage, recovered.completed_stages)
                self.assertEqual(dispatch.call_count, 1)
                self.assertGreater(artifact_path.stat().st_size, 0)

    def test_corrupt_json_output_reexecutes_completed_stage(self) -> None:
        from src.news.pipeline import run_news_to_short_job

        json_stages = tuple(
            stage
            for stage in DOWNSTREAM_STAGE_FAMILIES
            if stage != "preview_render"
        )
        for stage in json_stages:
            with self.subTest(stage=stage), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                job, project_root = _completed_project(root, stage)
                artifact_path = _artifact_path(project_root, job.language, stage)
                artifact_path.write_text("{not valid json", encoding="utf-8")

                with patch(
                    "src.news.pipeline._dispatch_stage",
                    side_effect=_synthetic_dispatch,
                ) as dispatch:
                    recovered = run_news_to_short_job(
                        projects_root=root,
                        job_id=job.job_id,
                        until_stage=stage,
                    )

                self.assertIn(stage, recovered.completed_stages)
                self.assertEqual(dispatch.call_count, 1)
                self.assertIsInstance(
                    json.loads(artifact_path.read_text(encoding="utf-8")),
                    dict,
                )

    def test_missing_declared_media_reexecutes_completed_stage(self) -> None:
        from src.news.pipeline import run_news_to_short_job
        from src.news.project_store import NewsProjectStore

        for stage in ("voice", "subtitles", "final_render"):
            with self.subTest(stage=stage), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                job, project_root = _completed_project(root, stage)
                store = NewsProjectStore(root)
                manifest_path = _artifact_path(project_root, job.language, stage)
                if stage == "voice":
                    declared_path = manifest_path.parent / "narration.wav"
                    declared_path.write_bytes(b"synthetic narration fixture")
                    store.write_json(
                        manifest_path,
                        {
                            "status": "completed",
                            "voice_stage_status": "completed",
                            "language": job.language,
                            "audio_path": str(declared_path),
                        },
                    )
                elif stage == "subtitles":
                    declared_path = manifest_path.parent / "subtitles.srt"
                else:
                    declared_path = (
                        project_root
                        / "localizations"
                        / job.language
                        / "output"
                        / "master_1080x1920.mp4"
                    )
                declared_path.unlink()

                with patch(
                    "src.news.pipeline._dispatch_stage",
                    side_effect=_synthetic_dispatch,
                ) as dispatch:
                    recovered = run_news_to_short_job(
                        projects_root=root,
                        job_id=job.job_id,
                        until_stage=stage,
                    )

                self.assertIn(stage, recovered.completed_stages)
                self.assertEqual(dispatch.call_count, 1)


class FinalRenderExplicitStageDispatchTests(unittest.TestCase):
    """PLAN-STAB-2: the render/export phase always dispatches final_render as an
    explicit ``stage="final_render"`` call (see
    ``FullscreenVoiceoverUseCase._render_and_export``), never via ``until_stage``.
    The generic ``DOWNSTREAM_STAGE_FAMILIES`` tests above only exercise
    ``until_stage=`` and force paths, so they never caught that this exact call
    shape used to skip the completed-stage guard entirely.
    """

    def test_completed_final_render_skips_on_explicit_stage_dispatch(self) -> None:
        from src.news.pipeline import run_news_to_short_job
        from src.news.project_store import NewsProjectStore

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            job, project_root = _completed_project(root, "final_render")
            store = NewsProjectStore(root)
            artifact_path = _artifact_path(project_root, job.language, "final_render")
            output_path = Path(
                store.read_json(artifact_path)["output_path"]
            )
            before_manifest_bytes = artifact_path.read_bytes()
            before_output_bytes = output_path.read_bytes()
            before_mtime_ns = output_path.stat().st_mtime_ns
            before_state = store.load_job(job.job_id).stages["final_render"]

            with patch(
                "src.news.pipeline._dispatch_stage",
                side_effect=AssertionError("final_render unexpectedly re-executed"),
            ) as dispatch:
                result = run_news_to_short_job(
                    projects_root=root,
                    job_id=job.job_id,
                    stage="final_render",
                )
                dispatch.assert_not_called()

            self.assertNotIn("final_render", result.completed_stages)
            self.assertEqual(output_path.read_bytes(), before_output_bytes)
            self.assertEqual(output_path.stat().st_mtime_ns, before_mtime_ns)
            self.assertEqual(artifact_path.read_bytes(), before_manifest_bytes)

            after_state = store.load_job(job.job_id).stages["final_render"]
            self.assertEqual(after_state.status, "completed")
            self.assertEqual(after_state.finished_at, before_state.finished_at)
            self.assertEqual(after_state.attempts, before_state.attempts)

    def test_force_stage_reexecutes_completed_final_render_on_explicit_stage_dispatch(
        self,
    ) -> None:
        from src.news.pipeline import run_news_to_short_job
        from src.news.project_store import NewsProjectStore

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            job, project_root = _completed_project(root, "final_render")
            store = NewsProjectStore(root)
            artifact_path = _artifact_path(project_root, job.language, "final_render")

            with patch(
                "src.news.pipeline._dispatch_stage",
                side_effect=_synthetic_dispatch,
            ) as dispatch:
                result = run_news_to_short_job(
                    projects_root=root,
                    job_id=job.job_id,
                    stage="final_render",
                    force_stage=True,
                )

            self.assertIn("final_render", result.completed_stages)
            self.assertEqual(dispatch.call_count, 1)
            self.assertTrue(artifact_path.is_file())
            self.assertEqual(
                store.load_job(job.job_id).stages["final_render"].status,
                "completed",
            )

    def test_completed_final_render_with_missing_artifact_reexecutes_on_explicit_stage_dispatch(
        self,
    ) -> None:
        from src.news.pipeline import run_news_to_short_job
        from src.news.project_store import NewsProjectStore

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            job, project_root = _completed_project(root, "final_render")
            store = NewsProjectStore(root)
            artifact_path = _artifact_path(project_root, job.language, "final_render")
            output_path = Path(store.read_json(artifact_path)["output_path"])
            output_path.unlink()

            with patch(
                "src.news.pipeline._dispatch_stage",
                side_effect=_synthetic_dispatch,
            ) as dispatch:
                result = run_news_to_short_job(
                    projects_root=root,
                    job_id=job.job_id,
                    stage="final_render",
                )

            self.assertIn("final_render", result.completed_stages)
            self.assertEqual(dispatch.call_count, 1)
            self.assertTrue(output_path.is_file())

    def test_not_yet_completed_final_render_executes_on_explicit_stage_dispatch(
        self,
    ) -> None:
        from src.news.pipeline import run_news_to_short_job
        from src.news.project_store import NewsProjectStore

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # Completed only through quality_check: final_render has never run.
            job, project_root = _completed_project(root, "quality_check")
            store = NewsProjectStore(root)

            with patch(
                "src.news.pipeline._dispatch_stage",
                side_effect=_synthetic_dispatch,
            ) as dispatch:
                result = run_news_to_short_job(
                    projects_root=root,
                    job_id=job.job_id,
                    stage="final_render",
                )

            self.assertIn("final_render", result.completed_stages)
            self.assertEqual(dispatch.call_count, 1)
            self.assertEqual(
                store.load_job(job.job_id).stages["final_render"].status,
                "completed",
            )

    def test_forced_final_render_failure_is_not_recorded_as_completed(self) -> None:
        from src.news.pipeline import run_news_to_short_job
        from src.news.project_store import NewsProjectStore

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            job, project_root = _completed_project(root, "final_render")
            store = NewsProjectStore(root)
            artifact_path = _artifact_path(project_root, job.language, "final_render")
            output_path = Path(store.read_json(artifact_path)["output_path"])
            before_output_bytes = output_path.read_bytes()

            with patch(
                "src.news.pipeline.render_final_video",
                side_effect=RuntimeError("synthetic renderer failure"),
            ):
                with self.assertRaises(RuntimeError):
                    run_news_to_short_job(
                        projects_root=root,
                        job_id=job.job_id,
                        stage="final_render",
                        force_stage=True,
                    )

            reloaded = store.load_job(job.job_id)
            self.assertEqual(reloaded.stages["final_render"].status, "failed")
            # PLAN-STAB-1 atomic preservation: a failed forced re-render never
            # touches the previously promoted output.
            self.assertEqual(output_path.read_bytes(), before_output_bytes)


def _completed_project(projects_root: Path, target_stage: str):
    from src.news.models import NEWS_TO_SHORT_STAGES
    from src.news.pipeline import create_news_to_short_job
    from src.news.project_store import NewsProjectStore

    job = create_news_to_short_job(
        projects_root=projects_root,
        channel_id="nature_science_news_ru",
        text="Синтетический offline fixture для проверки повторных стадий.",
        script_provider="legacy_template",
        language="ru",
        now="2026-07-29T14:00:00+03:00",
    )
    store = NewsProjectStore(projects_root)
    project_root = store.project_root(job.job_id)
    target_index = NEWS_TO_SHORT_STAGES.index(target_stage)
    for stage in NEWS_TO_SHORT_STAGES[: target_index + 1]:
        _write_valid_artifact(store, project_root, job, stage)
        state = job.stages[stage]
        state.status = "completed"
        state.attempts = 1
        state.result_path = str(_artifact_path(project_root, job.language, stage))
    store.save_job(job)
    return job, project_root


def _synthetic_dispatch(
    stage_name,
    store,
    job,
    project_root,
    **_kwargs,
):
    return _write_valid_artifact(store, project_root, job, stage_name)


def _artifact_path(project_root: Path, language: str, stage: str) -> Path:
    paths = {
        "input": project_root / "input" / "input.json",
        "article_ingestion": project_root / "article" / "article.json",
        "research": project_root / "research" / "claims.json",
        "script": project_root / "localizations" / language / "script" / "script.json",
        "visual_plan": project_root / "localizations" / language / "visual" / "visual_plan.json",
        "asset_search": project_root / "assets" / "assets_manifest.json",
        "voice": project_root / "localizations" / language / "voice" / "voice_manifest.json",
        "subtitles": project_root / "localizations" / language / "subtitles" / "subtitles_manifest.json",
        "preview_render": project_root / "preview" / "preview.mp4",
        "quality_check": project_root / "quality" / "quality_report.json",
        "final_render": project_root / "render" / "final_render_manifest.json",
        "export": project_root / "localizations" / language / "output" / "project_manifest.json",
    }
    return paths[stage]


def _write_valid_artifact(store, project_root: Path, job, stage: str) -> Path:
    path = _artifact_path(project_root, job.language, stage)
    if stage == "input":
        return path
    if stage == "article_ingestion":
        store.write_json(path, {"text": "offline article fixture", "images": []})
    elif stage == "research":
        store.write_json(path, {"claims": [{"claim": "offline fact"}]})
    elif stage == "script":
        store.write_json(
            path,
            {
                "language": job.language,
                "narration_text": "Короткий текст.",
                "scenes": [{"scene_id": "scene_001", "narration": "Короткий текст."}],
            },
        )
    elif stage == "visual_plan":
        store.write_json(
            path,
            {
                "language": job.language,
                "scenes": [{"scene_id": "scene_001", "visual_query": "ocean"}],
            },
        )
    elif stage == "asset_search":
        store.write_json(
            path,
            {
                "schema_version": 1,
                "dry_run": True,
                "provider_order": [],
                "assets": [],
                "scenes": [{"scene_id": "scene_001", "selected_asset": None}],
                "missing_scenes": [{"scene_id": "scene_001", "reason": "dry_run"}],
                "visual_support": {},
                "provider_attempts": [],
                "provider_errors": [],
                "warnings": [],
            },
        )
    elif stage == "voice":
        store.write_json(
            path,
            {
                "status": "provider_selection_required",
                "voice_stage_status": "provider_selection_required",
                "language": job.language,
                "audio_path": "",
            },
        )
    elif stage == "subtitles":
        srt_path = path.parent / "subtitles.srt"
        srt_path.parent.mkdir(parents=True, exist_ok=True)
        srt_path.write_text(
            "1\n00:00:00,000 --> 00:00:01,000\nКороткий текст.\n",
            encoding="utf-8",
        )
        store.write_json(
            path,
            {
                "status": "completed",
                "language": job.language,
                "srt_path": str(srt_path),
                "ass_path": "",
                "segments": [{"start": 0.0, "end": 1.0, "text": "Короткий текст."}],
            },
        )
    elif stage == "preview_render":
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"synthetic preview fixture")
    elif stage == "quality_check":
        store.write_json(
            path,
            {"status": "passed", "errors": [], "warnings": [], "checks": []},
        )
    elif stage == "final_render":
        output_path = project_root / "localizations" / job.language / "output" / "master_1080x1920.mp4"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"synthetic final render fixture")
        store.write_json(
            path,
            {
                "status": "completed",
                "output_path": str(output_path),
                "outputs": {"master_1080x1920": str(output_path)},
            },
        )
    elif stage == "export":
        description_path = path.parent / "description.txt"
        sources_path = path.parent / "sources.json"
        description_path.parent.mkdir(parents=True, exist_ok=True)
        description_path.write_text("Описание.\n", encoding="utf-8")
        store.write_json(sources_path, {"fact_sources": [], "asset_sources": []})
        store.write_json(
            path,
            {
                "job_id": job.job_id,
                "mode": job.mode,
                "channel_id": job.channel_id,
                "language": job.language,
                "status": "passed",
                "description_path": str(description_path),
                "sources_path": str(sources_path),
                "quality_report": {"status": "passed"},
                "outputs": {},
            },
        )
    else:
        raise AssertionError(f"Unhandled synthetic stage: {stage}")
    return path


if __name__ == "__main__":
    unittest.main()
