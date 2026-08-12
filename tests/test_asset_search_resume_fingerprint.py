"""Resume must not reuse an asset_search whose inputs it cannot vouch for.

READABLE != REUSABLE. A stored ``assets_manifest.json`` stays readable for
backward compatibility, but resume may only skip ``asset_search`` when the
manifest can prove it was produced from the inputs the current run would use.

Every project here comes out of the real pipeline: ``dry_run=True`` stops at
``asset_search`` and builds it with no providers and an empty media index, so
the whole module is offline and contacts nothing.
"""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


CHANNEL = "nature_science_news_ru"
TEXT = "Gepard razgonyaetsya do sta kilometrov v chas za tri sekundy."
RENDER_STAGES = ("preview_render", "quality_check", "final_render", "export")


class AssetSearchResumeFingerprintTests(unittest.TestCase):
    def test_changed_visual_plan_is_not_silently_reused(self) -> None:
        """The owner attaches footage, re-plans, resumes - and the search must rerun."""
        from src.news.pipeline import run_news_to_short_job

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            job, project_root, store = _dry_run_project(root)
            plan_path = _plan_path(project_root, job.language)
            manifest_path = project_root / "assets" / "assets_manifest.json"
            plan_before = _read(plan_path)
            manifest_before = _read(manifest_path)

            owner_clip = root / "owner_clip.mp4"
            owner_clip.write_bytes(b"offline fixture")
            attached = store.load_job(job.job_id)
            attached.user_assets = [str(owner_clip)]
            store.save_job(attached)
            run_news_to_short_job(
                projects_root=root,
                job_id=job.job_id,
                stage="visual_plan",
                force_stage=True,
                dry_run=True,
            )
            self.assertNotEqual(
                _read(plan_path),
                plan_before,
                "fixture is vacuous: the visual plan did not actually change",
            )

            result = run_news_to_short_job(
                projects_root=root,
                job_id=job.job_id,
                resume=True,
                until_stage="asset_search",
                dry_run=True,
            )

            self.assertIn("asset_search", result.completed_stages)
            self.assertNotEqual(_read(manifest_path), manifest_before)

    def test_changed_selection_policy_is_not_silently_reused(self) -> None:
        """The channel's asset_selection policy is a real input to the search."""
        from src.news.pipeline import _load_channel_config, run_news_to_short_job

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            job, _project_root, _store = _dry_run_project(root)

            changed = {
                **_load_channel_config(CHANNEL),
                "asset_selection": {
                    "mode": "legacy",
                    "legacy_fallback_enabled": True,
                    "vision_validation_enabled": False,
                },
            }
            with patch("src.news.pipeline._load_channel_config", return_value=changed):
                result = run_news_to_short_job(
                    projects_root=root,
                    job_id=job.job_id,
                    resume=True,
                    until_stage="asset_search",
                    dry_run=True,
                )

            self.assertIn("asset_search", result.completed_stages)

    def test_unchanged_inputs_still_reuse_the_completed_search(self) -> None:
        """The guard has to stay quiet when nothing semantic moved."""
        from src.news.pipeline import run_news_to_short_job

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            job, project_root, _store = _dry_run_project(root)
            manifest_before = _read(project_root / "assets" / "assets_manifest.json")

            result = run_news_to_short_job(
                projects_root=root,
                job_id=job.job_id,
                resume=True,
                until_stage="asset_search",
                dry_run=True,
            )

            self.assertNotIn("asset_search", result.completed_stages)
            self.assertEqual(
                _read(project_root / "assets" / "assets_manifest.json"),
                manifest_before,
            )

    def test_legacy_manifest_stays_readable_but_is_not_reused(self) -> None:
        """A manifest from before the fingerprint reads fine; it just cannot be trusted."""
        from src.news.pipeline import run_news_to_short_job
        from src.news.project_store import NewsProjectStore

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            job, project_root, store = _dry_run_project(root)
            manifest_path = project_root / "assets" / "assets_manifest.json"
            legacy = _read(manifest_path)
            legacy.pop("asset_search_fingerprint", None)
            store.write_json(manifest_path, legacy)

            reader = NewsProjectStore(root)
            self.assertTrue(
                reader.is_stage_completed(reader.load_job(job.job_id), "asset_search"),
                "a legacy manifest must remain readable and structurally complete",
            )

            result = run_news_to_short_job(
                projects_root=root,
                job_id=job.job_id,
                resume=True,
                until_stage="asset_search",
                dry_run=True,
            )

            self.assertIn("asset_search", result.completed_stages)

    def test_unreadable_fingerprint_is_treated_as_unknown(self) -> None:
        from src.news.pipeline import run_news_to_short_job

        for broken in ({"nested": "object"}, "", 17):
            with self.subTest(broken=broken), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                job, project_root, store = _dry_run_project(root)
                manifest_path = project_root / "assets" / "assets_manifest.json"
                manifest = _read(manifest_path)
                manifest["asset_search_fingerprint"] = broken
                store.write_json(manifest_path, manifest)

                result = run_news_to_short_job(
                    projects_root=root,
                    job_id=job.job_id,
                    resume=True,
                    until_stage="asset_search",
                    dry_run=True,
                )

                self.assertIn("asset_search", result.completed_stages)

    def test_recompute_invalidates_the_render_stages_that_consume_it(self) -> None:
        """A rerun search cannot leave an old preview, verdict, master or export standing."""
        from src.news.pipeline import run_news_to_short_job

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            job, project_root, store = _dry_run_project(root)
            _complete_downstream_stages(store, project_root, job.job_id)
            manifest_path = project_root / "assets" / "assets_manifest.json"
            manifest = _read(manifest_path)
            manifest["asset_search_fingerprint"] = "0" * 64
            store.write_json(manifest_path, manifest)

            run_news_to_short_job(
                projects_root=root,
                job_id=job.job_id,
                resume=True,
                until_stage="asset_search",
                dry_run=True,
            )

            after = store.load_job(job.job_id)
            for stage in RENDER_STAGES:
                self.assertEqual(
                    after.stages[stage].status,
                    "stale",
                    f"{stage} consumes the visual assembly and must not stay completed",
                )
            for stage in ("voice", "subtitles"):
                self.assertEqual(
                    after.stages[stage].status,
                    "completed",
                    f"{stage} is built from the script, not from the assets",
                )

    def test_dry_run_result_is_not_compatible_with_a_real_run(self) -> None:
        """A dry run searches no provider at all; its manifest cannot serve a real run."""
        from src.news.pipeline import asset_search_fingerprint

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            job, project_root, store = _dry_run_project(root)
            plan = _read(_plan_path(project_root, job.language))
            loaded = store.load_job(job.job_id)

            self.assertNotEqual(
                asset_search_fingerprint(loaded, plan, dry_run=True, asset_selection={}),
                asset_search_fingerprint(loaded, plan, dry_run=False, asset_selection={}),
            )

    def test_fingerprint_is_deterministic_and_order_independent(self) -> None:
        from src.news.pipeline import asset_search_fingerprint

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            job, project_root, store = _dry_run_project(root)
            plan = _read(_plan_path(project_root, job.language))
            loaded = store.load_job(job.job_id)
            selection = {"mode": "semantic", "legacy_fallback_enabled": False}
            reordered = {"legacy_fallback_enabled": False, "mode": "semantic"}

            first = asset_search_fingerprint(
                loaded, plan, dry_run=True, asset_selection=selection
            )
            second = asset_search_fingerprint(
                loaded, plan, dry_run=True, asset_selection=reordered
            )

            self.assertEqual(first, second)
            self.assertEqual(len(first), 64)


def _dry_run_project(projects_root: Path):
    """A project carried to a completed asset_search by the real pipeline."""
    from src.news.pipeline import create_news_to_short_job, run_news_to_short_job
    from src.news.project_store import NewsProjectStore

    job = create_news_to_short_job(
        projects_root=projects_root,
        channel_id=CHANNEL,
        text=TEXT,
        script_provider="legacy_template",
        language="ru",
        now="2026-08-12T10:00:00+03:00",
    )
    run_news_to_short_job(projects_root=projects_root, job_id=job.job_id, dry_run=True)
    store = NewsProjectStore(projects_root)
    return job, store.project_root(job.job_id), store


def _complete_downstream_stages(store, project_root: Path, job_id: str) -> None:
    """Valid artifacts for the stages a real render would have produced."""
    job = store.load_job(job_id)
    language = job.language
    voice_dir = project_root / "localizations" / language / "voice"
    audio_path = voice_dir / "narration.wav"
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    audio_path.write_bytes(b"offline voice fixture")
    store.write_json(
        voice_dir / "voice_manifest.json",
        {
            "status": "completed",
            "voice_stage_status": "completed",
            "language": language,
            "audio_path": str(audio_path),
        },
    )

    subtitles_dir = project_root / "localizations" / language / "subtitles"
    srt_path = subtitles_dir / "subtitles.srt"
    srt_path.parent.mkdir(parents=True, exist_ok=True)
    srt_path.write_text(
        "1\n00:00:00,000 --> 00:00:01,000\nTekst.\n", encoding="utf-8"
    )
    store.write_json(
        subtitles_dir / "subtitles_manifest.json",
        {
            "status": "completed",
            "language": language,
            "srt_path": str(srt_path),
            "segments": [{"start": 0.0, "end": 1.0, "text": "Tekst."}],
        },
    )

    preview_path = project_root / "preview" / "preview.mp4"
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    preview_path.write_bytes(b"offline preview fixture")
    store.write_json(
        project_root / "quality" / "quality_report.json",
        {"status": "passed", "errors": [], "warnings": [], "checks": []},
    )

    output_dir = project_root / "localizations" / language / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    master_path = output_dir / "master_1080x1920.mp4"
    master_path.write_bytes(b"offline master fixture")
    store.write_json(
        project_root / "render" / "final_render_manifest.json",
        {
            "status": "completed",
            "output_path": str(master_path),
            "outputs": {"master_1080x1920": str(master_path)},
        },
    )
    description_path = output_dir / "description.txt"
    description_path.write_text("Opisanie.\n", encoding="utf-8")
    sources_path = output_dir / "sources.json"
    store.write_json(sources_path, {"fact_sources": [], "asset_sources": []})
    store.write_json(
        output_dir / "project_manifest.json",
        {
            "job_id": job.job_id,
            "mode": job.mode,
            "channel_id": job.channel_id,
            "language": language,
            "status": "passed",
            "description_path": str(description_path),
            "sources_path": str(sources_path),
            "quality_report": {"status": "passed"},
            "outputs": {},
        },
    )

    for stage in ("voice", "subtitles", *RENDER_STAGES):
        state = job.stages[stage]
        state.status = "completed"
        state.attempts = 1
    store.save_job(job)


def _plan_path(project_root: Path, language: str) -> Path:
    return project_root / "localizations" / language / "visual" / "visual_plan.json"


def _read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
