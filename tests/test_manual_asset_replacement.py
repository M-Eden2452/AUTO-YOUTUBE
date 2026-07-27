from __future__ import annotations

import json
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from src.assets.completion.assembly import (
    ASSEMBLY_COMPOSITE,
    SLOT_PRIMARY,
    SLOT_SUPPORTING,
    SceneVisualAssembly,
    attach_assembly,
    read_assembly,
    slot_from_asset,
)
from src.assets.completion.modes import MODE_STRICT, TIER_EXACT, evaluate_usability
from src.assets.completion.replacement import (
    VisualSlotReplacementError,
    replace_visual_slot,
)
from src.assets.download import sha256_file, validate_local_asset
from src.assets.semantic_selection.decision import (
    DECISION_KEY,
    FRAMING_VERTICAL_READY,
    SUPPORT_FULL,
    VERDICT_COMPLETE,
    SelectionDecision,
)
from src.news.models import INPUT_MODE_TOPIC, NewsJob
from src.news.project_store import NewsProjectStore


def _write_png(path: Path, color: tuple[int, int, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (540, 960), color).save(path, format="PNG")


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _existing_asset(path: Path, asset_id: str) -> dict:
    checksum = sha256_file(path)
    decision = SelectionDecision(
        scene_id="scene_001",
        asset_id=asset_id,
        provider="fake",
        provider_confidence=1.0,
        semantic_score=1.0,
        semantic_status="matched",
        metadata_score=1.0,
        metadata_status="matched",
        technical_score=1.0,
        technical_status=FRAMING_VERTICAL_READY,
        framing={
            "status": FRAMING_VERTICAL_READY,
            "source_width": 540,
            "source_height": 960,
            "render_ready": True,
        },
        rights_status="public_domain",
        rights_allowed_for_render=True,
        rights_review_required=False,
        slots={
            "matched_slots": ["subject"],
            "missing_slots": [],
            "missing_required_slots": [],
            "conflicting_slots": [],
            "undecidable_slots": [],
        },
        slot_verdict=VERDICT_COMPLETE,
        support_status=SUPPORT_FULL,
        support_requirements=[],
        selection_reasons=["offline_fixture"],
    )
    return {
        "schema_version": 1,
        "asset_id": asset_id,
        "provider": "fake",
        "provider_asset_id": asset_id,
        "media_type": "image",
        "type": "image",
        "title": asset_id,
        "source_page_url": f"https://fake.local/{asset_id}",
        "source_url": f"https://fake.local/{asset_id}",
        "path": str(path),
        "local_path": str(path),
        "downloaded_path": str(path),
        "original_filename": path.name,
        "checksum_sha256": checksum,
        "width": 540,
        "height": 960,
        "orientation": "vertical",
        "license": {
            "license_name": "fake_test_license",
            "rights_status": "public_domain",
            "allowed_for_render": True,
            "review_required": False,
        },
        "license_name": "fake_test_license",
        "rights_status": "public_domain",
        "allowed_for_render": True,
        "review_required": False,
        "provenance": {
            "provider": "fake",
            "provider_asset_id": asset_id,
            "source_page_url": f"https://fake.local/{asset_id}",
            "original_filename": path.name,
            "checksum_sha256": checksum,
            "project_id": "manual_replace_project",
            "scene_id": "scene_001",
        },
        "technical_validation": {
            "status": "passed",
            "media_type": "image",
            "width": 540,
            "height": 960,
            "orientation": "vertical",
        },
        DECISION_KEY: decision.to_dict(),
        "support_status": SUPPORT_FULL,
    }


class ManualAssetReplacementTests(unittest.TestCase):
    def _project(self, workspace: Path) -> tuple[Path, Path, NewsJob]:
        projects_root = workspace / "projects"
        job = NewsJob.create(
            channel_id="test_channel",
            input_mode=INPUT_MODE_TOPIC,
            title="Manual replacement",
            topic="Offline fixture",
            language="ru",
            completion_mode=MODE_STRICT,
            now="2026-07-27T12:00:00+00:00",
        )
        job.job_id = "manual_replace_project"
        for stage_name, state in job.stages.items():
            state.status = "completed"
            state.finished_at = "2026-07-27T12:01:00+00:00"
            state.result_path = f"old/{stage_name}.json"
        job.status = "completed"
        store = NewsProjectStore(projects_root)
        project = store.create_project(job).root

        primary_path = project / "assets" / "original_primary.png"
        supporting_path = project / "assets" / "original_supporting.png"
        _write_png(primary_path, (25, 60, 120))
        _write_png(supporting_path, (80, 125, 30))
        primary = _existing_asset(primary_path, "old_primary")
        supporting = _existing_asset(supporting_path, "old_supporting")
        assembly = SceneVisualAssembly(
            scene_id="scene_001",
            scene_duration_sec=4.0,
            assembly_status=ASSEMBLY_COMPOSITE,
            support_status=SUPPORT_FULL,
            completion_mode=MODE_STRICT,
            slots=[
                slot_from_asset(
                    primary,
                    slot_id="scene_001_slot_001",
                    purpose=SLOT_PRIMARY,
                    start_offset_sec=0.0,
                    end_offset_sec=2.0,
                    quality_tier=TIER_EXACT,
                    usability=evaluate_usability(
                        primary,
                        mode=MODE_STRICT,
                        quality_tier=TIER_EXACT,
                        require_local_file=True,
                    ),
                    required_subject="research station",
                    ladder_level="exact",
                ),
                slot_from_asset(
                    supporting,
                    slot_id="scene_001_slot_002",
                    purpose=SLOT_SUPPORTING,
                    start_offset_sec=2.0,
                    end_offset_sec=4.0,
                    quality_tier=TIER_EXACT,
                    usability=evaluate_usability(
                        supporting,
                        mode=MODE_STRICT,
                        quality_tier=TIER_EXACT,
                        require_local_file=True,
                    ),
                    required_action="scientist taking a sample",
                    ladder_level="exact",
                ),
            ],
        )
        scene = {
            "scene_id": "scene_001",
            "required_duration_sec": 4.0,
            "narration": "Scientists take a sample.",
            "visual_brief": {
                "subject": "scientist",
                "action": "taking a sample",
                "provider_queries": {"fake": ["scientist taking sample"]},
            },
            "resolution_status": "resolved",
        }
        attach_assembly(scene, assembly)
        store.write_json(
            project / "assets" / "assets_manifest.json",
            {
                "schema_version": 1,
                "project_id": job.job_id,
                "scenes": [scene],
                "missing_scenes": [],
                "visual_support": {"scene_count": 1, "full_support": 1},
                "completion": {
                    "mode": MODE_STRICT,
                    "scene_count": 1,
                    "slot_count": 2,
                    "scenes_usable_in_draft": 1,
                    "scenes_publish_ready": 1,
                    "unresolved_scenes": [],
                    "quality_tiers": {TIER_EXACT: 2},
                    "assembly_statuses": {ASSEMBLY_COMPOSITE: 1},
                    "timeline_problems": [],
                    "reuse": {"uses": {}, "scenes": {}, "repeated_assets": {}},
                    "draft_complete": True,
                    "publish_ready": True,
                },
            },
        )
        store.write_json(
            project / "localizations" / "ru" / "script" / "script.json",
            {
                "language": "ru",
                "estimated_duration_sec": 40.0,
                "scenes": [
                    {
                        "scene_id": "scene_001",
                        "narration": "Scientists take a sample.",
                        "target_duration_sec": 4.0,
                    }
                ],
            },
        )
        store.write_json(
            project / "research" / "claims.json",
            {"claims": [{"claim_id": "claim_001", "text": "A preserved fact."}]},
        )
        store.write_json(
            project / "assets" / "search_trace.json",
            {"queries": ["offline fixture"], "provider_calls": 0},
        )
        store.write_json(
            project / "quality" / "quality_report.json",
            {"status": "passed", "errors": [], "warnings": [], "marker": "preserve"},
        )
        output_path = project / "localizations" / "ru" / "output" / "final.mp4"
        output_path.write_bytes(b"offline-old-render")
        store.write_json(
            project / "render" / "final_render_manifest.json",
            {
                "status": "completed",
                "output_path": str(output_path),
                "publish_ready": True,
                "marker": "preserve",
            },
        )
        return projects_root, project, job

    def test_replaces_only_selected_slot_and_preserves_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            projects_root, project, job = self._project(workspace)
            source = workspace / "incoming" / "replacement.png"
            proof = workspace / "incoming" / "ownership.txt"
            _write_png(source, (190, 45, 35))
            proof.write_text("Owner confirms this media is user-owned.\n", encoding="utf-8")
            source_before = source.read_bytes()
            proof_before = proof.read_bytes()

            manifest_before = _read(project / "assets" / "assets_manifest.json")
            scene_before = manifest_before["scenes"][0]
            assembly_before = read_assembly(scene_before)
            primary_before = assembly_before.slots[0].to_dict()
            target_before = assembly_before.slots[1].to_dict()
            selected_before = dict(scene_before["selected_asset"])
            untouched_paths = [
                project / "research" / "claims.json",
                project / "localizations" / "ru" / "script" / "script.json",
                project / "assets" / "search_trace.json",
            ]
            untouched_bytes = {path: path.read_bytes() for path in untouched_paths}

            result = replace_visual_slot(
                projects_root=projects_root,
                project_id=job.job_id,
                scene_id="scene_001",
                slot_id="scene_001_slot_002",
                source_file=source,
                source_url="https://example.test/user-source",
                license_file=proof,
                confirm_user_owned=True,
            )

            self.assertEqual(result["status"], "replaced")
            self.assertEqual(source.read_bytes(), source_before)
            self.assertEqual(proof.read_bytes(), proof_before)
            imported = Path(result["asset_path"])
            imported_proof = Path(result["license_proof_path"])
            self.assertTrue(imported.is_file())
            self.assertTrue(imported_proof.is_file())
            self.assertNotEqual(imported.resolve(), source.resolve())
            self.assertEqual(sha256_file(imported), sha256_file(source))
            self.assertEqual(sha256_file(imported_proof), sha256_file(proof))
            self.assertEqual(validate_local_asset(imported, "image")["status"], "passed")
            self.assertEqual(
                imported.parent,
                project / "assets" / "replacements" / "scene_001" / "scene_001_slot_002",
            )

            manifest = _read(project / "assets" / "assets_manifest.json")
            scene = manifest["scenes"][0]
            assembly = read_assembly(scene)
            self.assertEqual(assembly.slots[0].to_dict(), primary_before)
            replacement_slot = assembly.slots[1]
            self.assertNotEqual(replacement_slot.selected_asset, target_before["selected_asset"])
            for key in (
                "slot_id",
                "purpose",
                "start_offset_sec",
                "end_offset_sec",
                "required_subject",
                "required_action",
                "required_location",
            ):
                self.assertEqual(replacement_slot.to_dict()[key], target_before[key])
            self.assertEqual(scene["selected_asset"], selected_before)
            self.assertEqual(replacement_slot.quality_tier, TIER_EXACT)
            self.assertEqual(replacement_slot.support_status, SUPPORT_FULL)
            self.assertTrue(replacement_slot.usability.publish_ready)
            asset = replacement_slot.selected_asset
            self.assertEqual(asset["provider"], "user")
            self.assertEqual(asset["rights_status"], "user_owned")
            self.assertTrue(asset["allowed_for_render"])
            self.assertFalse(asset["review_required"])
            self.assertEqual(asset["checksum_sha256"], sha256_file(source))
            self.assertEqual(asset["provenance"]["original_filename"], source.name)
            self.assertEqual(asset["provenance"]["scene_id"], "scene_001")
            self.assertEqual(
                asset["provenance"]["metadata_snapshot"]["declared_source_url"],
                "https://example.test/user-source",
            )
            declaration = asset["rights_declaration"]
            self.assertTrue(declaration["rights_confirmed"])
            self.assertEqual(declaration["owner_approval_status"], "owner_approved")
            self.assertEqual(
                declaration["license_proof"]["checksum_sha256"],
                sha256_file(proof),
            )
            self.assertEqual(asset[DECISION_KEY]["support_status"], SUPPORT_FULL)
            self.assertEqual(asset[DECISION_KEY]["slot_verdict"], VERDICT_COMPLETE)
            self.assertEqual(manifest["completion"]["scenes_publish_ready"], 1)
            self.assertTrue(manifest["completion"]["publish_ready"])

            history = _read(Path(result["history_path"]))
            self.assertEqual(len(history["entries"]), 1)
            entry = history["entries"][0]
            self.assertEqual(entry["previous_asset_id"], "old_supporting")
            self.assertEqual(entry["replacement_asset_id"], asset["asset_id"])
            self.assertEqual(entry["previous_slot"], target_before)
            self.assertEqual(entry["license_proof"]["checksum_sha256"], sha256_file(proof))

            loaded_job = NewsProjectStore(projects_root).load_job(job.job_id)
            self.assertEqual(loaded_job.status, "render_stale")
            for stage_name in ("preview_render", "quality_check", "final_render", "export"):
                state = loaded_job.stages[stage_name]
                self.assertEqual(state.status, "stale")
                self.assertIsNone(state.finished_at)
                self.assertEqual(state.settings["stale_scene_id"], "scene_001")
                self.assertEqual(state.settings["stale_slot_id"], "scene_001_slot_002")
                self.assertEqual(state.result_path, f"old/{stage_name}.json")
            quality = _read(project / "quality" / "quality_report.json")
            self.assertEqual(quality["status"], "stale")
            self.assertEqual(quality["previous_status"], "passed")
            self.assertEqual(quality["marker"], "preserve")
            render = _read(project / "render" / "final_render_manifest.json")
            self.assertEqual(render["status"], "stale")
            self.assertEqual(render["previous_status"], "completed")
            self.assertEqual(render["output_path"], "")
            self.assertTrue(Path(render["stale_output_path"]).is_file())
            self.assertFalse(render["publish_ready"])
            self.assertEqual(render["marker"], "preserve")

            for path, previous in untouched_bytes.items():
                self.assertEqual(path.read_bytes(), previous)
            self.assertEqual(
                set(result["report_paths"]),
                {"json_path", "html_path", "queue_path", "csv_path"},
            )
            for report_path in result["report_paths"].values():
                self.assertTrue(Path(report_path).is_file())

    def test_primary_replacement_synchronizes_legacy_selected_asset(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            projects_root, project, job = self._project(workspace)
            source = workspace / "incoming" / "new-primary.png"
            _write_png(source, (30, 170, 180))
            before = _read(project / "assets" / "assets_manifest.json")
            supporting_before = read_assembly(before["scenes"][0]).slots[1].to_dict()

            result = replace_visual_slot(
                projects_root=projects_root,
                project_id=job.job_id,
                scene_id="scene_001",
                slot_id="scene_001_slot_001",
                source_file=source,
                confirm_user_owned=True,
            )

            scene = _read(project / "assets" / "assets_manifest.json")["scenes"][0]
            assembly = read_assembly(scene)
            self.assertEqual(assembly.slots[1].to_dict(), supporting_before)
            self.assertEqual(scene["selected_asset"]["asset_id"], result["asset_id"])
            self.assertEqual(
                scene[DECISION_KEY]["asset_id"],
                result["asset_id"],
            )
            self.assertEqual(
                scene["selected_asset"]["source_page_url"],
                f"manual://user-owned/{result['checksum_sha256']}",
            )

    def test_replacement_can_rerun_quality_and_render_without_research_or_search(self) -> None:
        from src.news.pipeline import run_news_to_short_job

        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            projects_root, project, job = self._project(workspace)
            source = workspace / "incoming" / "rerender.png"
            _write_png(source, (125, 40, 190))
            claims_path = project / "research" / "claims.json"
            trace_path = project / "assets" / "search_trace.json"
            preserved = {
                claims_path: claims_path.read_bytes(),
                trace_path: trace_path.read_bytes(),
            }

            replacement = replace_visual_slot(
                projects_root=projects_root,
                project_id=job.job_id,
                scene_id="scene_001",
                slot_id="scene_001_slot_002",
                source_file=source,
                confirm_user_owned=True,
            )
            voice = project / "localizations" / "ru" / "voice" / "narration.wav"
            voice.parent.mkdir(parents=True, exist_ok=True)
            voice.write_bytes(b"offline narration")
            subtitles = project / "localizations" / "ru" / "subtitles"
            subtitles.mkdir(parents=True, exist_ok=True)
            srt = subtitles / "subtitles.srt"
            ass = subtitles / "subtitles.ass"
            srt.write_text("1\n00:00:00,000 --> 00:00:04,000\nOffline\n", encoding="utf-8")
            ass.write_text("[Script Info]\n", encoding="utf-8")
            store = NewsProjectStore(projects_root)
            store.write_json(
                project / "localizations" / "ru" / "voice" / "voice_manifest.json",
                {"status": "completed", "audio_path": str(voice)},
            )
            store.write_json(
                subtitles / "subtitles_manifest.json",
                {"status": "completed", "srt_path": str(srt), "ass_path": str(ass)},
            )
            store.write_json(
                project / "localizations" / "ru" / "visual" / "visual_plan.json",
                {
                    "resolution": {"width": 1080, "height": 1920},
                    "scenes": [{"scene_id": "scene_001"}],
                },
            )

            quality_result = run_news_to_short_job(
                projects_root=projects_root,
                job_id=job.job_id,
                stage="quality_check",
            )
            quality = _read(project / "quality" / "quality_report.json")

            output = project / "localizations" / "ru" / "output" / "final.mp4"

            def offline_render(**kwargs: object) -> dict:
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(b"offline rerender")
                manifest = kwargs["assets_manifest"]
                assembly = read_assembly(manifest["scenes"][0])
                self.assertEqual(
                    assembly.slot("scene_001_slot_002").selected_asset["asset_id"],
                    replacement["asset_id"],
                )
                return {
                    "status": "completed",
                    "render_status": "completed",
                    "output_path": str(output),
                }

            with patch(
                "src.news.pipeline.render_final_video",
                side_effect=offline_render,
            ) as render:
                render_result = run_news_to_short_job(
                    projects_root=projects_root,
                    job_id=job.job_id,
                    stage="final_render",
                )

            loaded = store.load_job(job.job_id)
            output_exists = output.is_file()
            preserved_after = {path: path.read_bytes() for path in preserved}

        self.assertEqual(quality_result.completed_stages, ["quality_check"])
        self.assertEqual(quality["status"], "passed")
        self.assertEqual(render_result.status, "completed")
        self.assertEqual(render.call_count, 1)
        self.assertEqual(loaded.stages["final_render"].status, "completed")
        self.assertTrue(output_exists)
        for path, before in preserved.items():
            self.assertEqual(preserved_after[path], before)

    def test_legacy_single_asset_scene_is_upgraded_without_migration_step(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            projects_root, project, job = self._project(workspace)
            manifest_path = project / "assets" / "assets_manifest.json"
            manifest = _read(manifest_path)
            legacy_scene = manifest["scenes"][0]
            legacy_scene.pop("visual_assembly")
            manifest["completion"] = {}
            NewsProjectStore(projects_root).write_json(manifest_path, manifest)
            job_path = project / "job.json"
            stored_job = _read(job_path)
            stored_job.pop("completion", None)
            NewsProjectStore(projects_root).write_json(job_path, stored_job)
            source = workspace / "incoming" / "legacy-replacement.png"
            _write_png(source, (210, 145, 20))

            result = replace_visual_slot(
                projects_root=projects_root,
                project_id=job.job_id,
                scene_id="scene_001",
                slot_id="scene_001_slot_001",
                source_file=source,
                confirm_user_owned=True,
            )

            scene = _read(manifest_path)["scenes"][0]
            assembly = read_assembly(scene)
            self.assertEqual(len(assembly.slots), 1)
            self.assertEqual(assembly.slots[0].selected_asset["asset_id"], result["asset_id"])
            self.assertEqual(scene["selected_asset"]["asset_id"], result["asset_id"])
            self.assertTrue(assembly.publish_ready)
            self.assertEqual(
                NewsProjectStore(projects_root).load_job(job.job_id).completion,
                {},
            )

    def test_rights_confirmation_is_required_before_copy_or_project_write(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            projects_root, project, job = self._project(workspace)
            source = workspace / "incoming" / "unconfirmed.png"
            proof = workspace / "incoming" / "unconfirmed-license.txt"
            _write_png(source, (90, 120, 30))
            proof.write_text("An opaque file is not a parsed rights verdict.\n", encoding="utf-8")
            watched = [
                project / "job.json",
                project / "assets" / "assets_manifest.json",
                project / "quality" / "quality_report.json",
                project / "render" / "final_render_manifest.json",
            ]
            before = {path: path.read_bytes() for path in watched}

            with self.assertRaises(VisualSlotReplacementError) as caught:
                replace_visual_slot(
                    projects_root=projects_root,
                    project_id=job.job_id,
                    scene_id="scene_001",
                    slot_id="scene_001_slot_002",
                    source_file=source,
                    source_url="https://example.test/unconfirmed-source",
                    license_file=proof,
                )

            self.assertEqual(caught.exception.code, "rights_confirmation_required")
            for path, previous in before.items():
                self.assertEqual(path.read_bytes(), previous)
            self.assertFalse((project / "assets" / "replacements").exists())

    def test_corrupt_media_fails_without_mutating_project(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            projects_root, project, job = self._project(workspace)
            corrupt = workspace / "incoming" / "corrupt.png"
            corrupt.parent.mkdir(parents=True, exist_ok=True)
            corrupt.write_bytes(b"this is not a png")
            watched = [
                project / "job.json",
                project / "assets" / "assets_manifest.json",
                project / "quality" / "quality_report.json",
                project / "render" / "final_render_manifest.json",
            ]
            before = {path: path.read_bytes() for path in watched}

            with self.assertRaises(VisualSlotReplacementError) as caught:
                replace_visual_slot(
                    projects_root=projects_root,
                    project_id=job.job_id,
                    scene_id="scene_001",
                    slot_id="scene_001_slot_002",
                    source_file=corrupt,
                    confirm_user_owned=True,
                )

            self.assertEqual(caught.exception.code, "invalid_media")
            for path, previous in before.items():
                self.assertEqual(path.read_bytes(), previous)
            self.assertFalse(
                (project / "assets" / "replacements" / "replacement_history.json").exists()
            )
            self.assertEqual(corrupt.read_bytes(), b"this is not a png")

    def test_canonical_cli_rejects_unconfirmed_ownership(self) -> None:
        from src.content_creation.cli import main

        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            projects_root, project, job = self._project(workspace)
            source = workspace / "incoming" / "cli-unconfirmed.png"
            _write_png(source, (20, 90, 180))
            before = (project / "assets" / "assets_manifest.json").read_bytes()
            output = io.StringIO()

            with redirect_stdout(output):
                exit_code = main(
                    [
                        "assets",
                        "replace",
                        "--projects-root",
                        str(projects_root),
                        "--project-id",
                        job.job_id,
                        "--scene-id",
                        "scene_001",
                        "--slot-id",
                        "scene_001_slot_002",
                        "--file",
                        str(source),
                        "--json",
                    ]
                )

            payload = json.loads(output.getvalue())
            self.assertEqual(exit_code, 1)
            self.assertEqual(payload["code"], "rights_confirmation_required")
            self.assertEqual(
                (project / "assets" / "assets_manifest.json").read_bytes(),
                before,
            )
            self.assertFalse((project / "assets" / "replacements").exists())

    def test_canonical_cli_replaces_one_slot(self) -> None:
        from src.content_creation.cli import main

        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            projects_root, project, job = self._project(workspace)
            source = workspace / "incoming" / "cli-replacement.png"
            _write_png(source, (70, 90, 210))
            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = main(
                    [
                        "assets",
                        "replace",
                        "--projects-root",
                        str(projects_root),
                        "--project-id",
                        job.job_id,
                        "--scene-id",
                        "scene_001",
                        "--slot-id",
                        "scene_001_slot_002",
                        "--file",
                        str(source),
                        "--confirm-user-owned",
                        "--json",
                    ]
                )
            self.assertEqual(exit_code, 0)
            result = json.loads(output.getvalue())
            self.assertEqual(result["status"], "replaced")
            self.assertTrue(Path(result["asset_path"]).is_file())
            assembly = read_assembly(
                _read(project / "assets" / "assets_manifest.json")["scenes"][0]
            )
            self.assertEqual(
                assembly.slot("scene_001_slot_002").selected_asset["asset_id"],
                result["asset_id"],
            )


if __name__ == "__main__":
    unittest.main()
