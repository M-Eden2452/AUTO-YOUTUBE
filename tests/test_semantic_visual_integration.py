from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import Any


class SemanticVisualIntegrationTests(unittest.TestCase):
    def test_review_bundle_enrichment(self) -> None:
        from src.assets.semantic_visual_service import analyse_semantic_visual_for_project

        with tempfile.TemporaryDirectory() as tmp:
            project = _write_visual_review_fixture(Path(tmp), cases=["good_match"])

            summary = analyse_semantic_visual_for_project(
                project_root=project,
                project_id="project_001",
                scene_id="scene_001",
                backend_name="mock",
                no_html=True,
            )

            manifest = _read_manifest(project)
            candidate = manifest["scenes"][0]["shortlist"][0]
            self.assertEqual(summary["successful_analyses"], 1)
            self.assertEqual(candidate["semantic_status"], "success")
            self.assertIn("semantic_analysis", candidate)
            self.assertGreater(candidate["semantic_score"], 0.85)
            self.assertFalse(candidate["semantic_review_required"])

    def test_html_semantic_section(self) -> None:
        from src.assets.semantic_visual_service import analyse_semantic_visual_for_project

        with tempfile.TemporaryDirectory() as tmp:
            project = _write_visual_review_fixture(Path(tmp), cases=["good_match"])

            summary = analyse_semantic_visual_for_project(
                project_root=project,
                project_id="project_001",
                scene_id="scene_001",
                backend_name="mock",
            )

            html = Path(summary["html_path"]).read_text(encoding="utf-8")
            self.assertIn("Semantic", html)
            self.assertIn("subject", html)
            self.assertIn("must-have", html)
            self.assertIn("evidence", html)

    def test_html_contains_no_secrets(self) -> None:
        from src.assets.semantic_visual_service import analyse_semantic_visual_for_project

        with tempfile.TemporaryDirectory() as tmp:
            project = _write_visual_review_fixture(Path(tmp), cases=["good_match"], secret="SECRET_TOKEN_VALUE")

            summary = analyse_semantic_visual_for_project(project_root=project, project_id="project_001", scene_id="scene_001", backend_name="mock")

            html = Path(summary["html_path"]).read_text(encoding="utf-8")
            self.assertNotIn("SECRET_TOKEN_VALUE", html)
            self.assertNotIn("api_key", html.lower())
            self.assertNotIn(str(project), html)

    def test_analyse_and_report_does_not_change_selection(self) -> None:
        from src.assets.semantic_visual_service import analyse_semantic_visual_for_project

        with tempfile.TemporaryDirectory() as tmp:
            project = _write_visual_review_fixture(Path(tmp), cases=["subject_mismatch", "good_match"], selected_id="asset_subject_mismatch")
            before = _read_manifest(project)["scenes"][0]["selected_candidate"]

            analyse_semantic_visual_for_project(project_root=project, project_id="project_001", scene_id="scene_001", backend_name="mock")
            after = _read_manifest(project)["scenes"][0]["selected_candidate"]

            self.assertEqual(after["asset_id"], before["asset_id"])
            self.assertEqual(after["asset_id"], "asset_subject_mismatch")

    def test_offline_mode_uses_cache_only(self) -> None:
        from src.assets.semantic_visual_mock import MockSemanticVisualBackend
        from src.assets.semantic_visual_service import analyse_semantic_visual_for_project

        with tempfile.TemporaryDirectory() as tmp:
            project = _write_visual_review_fixture(Path(tmp), cases=["good_match"])
            backend = MockSemanticVisualBackend()

            summary = analyse_semantic_visual_for_project(
                project_root=project,
                project_id="project_001",
                scene_id="scene_001",
                backend=backend,
                backend_name="mock",
                offline=True,
                refresh=True,
                no_html=True,
            )

            candidate = _read_manifest(project)["scenes"][0]["shortlist"][0]
            self.assertEqual(summary["backend_calls"], 0)
            self.assertEqual(summary["cache_misses"], 1)
            self.assertEqual(candidate["semantic_status"], "offline_cache_miss")
            self.assertEqual(backend.call_count, 0)

    def test_cache_is_used_on_second_run(self) -> None:
        from src.assets.semantic_visual_mock import MockSemanticVisualBackend
        from src.assets.semantic_visual_service import analyse_semantic_visual_for_project

        with tempfile.TemporaryDirectory() as tmp:
            project = _write_visual_review_fixture(Path(tmp), cases=["good_match"])
            first_backend = MockSemanticVisualBackend()
            second_backend = MockSemanticVisualBackend()

            first = analyse_semantic_visual_for_project(project_root=project, project_id="project_001", scene_id="scene_001", backend=first_backend, backend_name="mock", no_html=True)
            second = analyse_semantic_visual_for_project(project_root=project, project_id="project_001", scene_id="scene_001", backend=second_backend, backend_name="mock", offline=True, no_html=True)

            self.assertEqual(first["backend_calls"], 1)
            self.assertEqual(second["cache_hits"], 1)
            self.assertEqual(second["backend_calls"], 0)
            self.assertEqual(second_backend.call_count, 0)

    def test_maximum_candidates_and_frames_are_respected(self) -> None:
        from src.assets.semantic_visual_mock import MockSemanticVisualBackend
        from src.assets.semantic_visual_service import analyse_semantic_visual_for_project

        with tempfile.TemporaryDirectory() as tmp:
            project = _write_visual_review_fixture(Path(tmp), cases=["good_match", "subject_mismatch", "action_mismatch"], frame_count=5)
            backend = MockSemanticVisualBackend()

            summary = analyse_semantic_visual_for_project(
                project_root=project,
                project_id="project_001",
                scene_id="scene_001",
                backend=backend,
                backend_name="mock",
                maximum_candidates=2,
                maximum_frames=2,
                no_html=True,
            )

            self.assertEqual(summary["candidates_processed"], 2)
            self.assertEqual(backend.requests_seen[0].maximum_frames, 2)
            self.assertEqual(len(backend.requests_seen[0].sampled_frame_references), 2)

    def test_inspect_reports_semantic_summary(self) -> None:
        from src.assets.semantic_visual_service import analyse_semantic_visual_for_project, inspect_semantic_visual_project

        with tempfile.TemporaryDirectory() as tmp:
            project = _write_visual_review_fixture(Path(tmp), cases=["negative_violation", "low_confidence_negative"])

            analyse_semantic_visual_for_project(project_root=project, project_id="project_001", scene_id="scene_001", backend_name="mock", no_html=True)
            summary = inspect_semantic_visual_project(project)

            self.assertEqual(summary["scenes"], 1)
            self.assertEqual(summary["analysed_candidates"], 2)
            self.assertEqual(summary["hard_rejects"], 1)
            self.assertEqual(summary["review_required"], 1)
            self.assertEqual(summary["backend"], "mock")

    def test_full_review_bundle_creation_accepts_semantic_analysis(self) -> None:
        from src.assets.review_bundle import create_scene_review_bundle
        from src.assets.semantic_visual_mock import MockSemanticVisualBackend

        result = MockSemanticVisualBackend().analyse_candidate(_semantic_request("good_match")).to_review_dict()
        bundle = create_scene_review_bundle(
            project_id="project_001",
            scene={"scene_id": "scene_001", "primary_query": "whale ocean", "visual_type": "video"},
            semantic_scene={"subject": ["whale"], "must_include": ["whale"]},
            metadata_queries=[],
            provider_routing={},
            candidates=[_candidate("asset_good_match", "good_match")],
            analyses=[{"asset_id": "asset_good_match", "analysis_status": "passed", "semantic_analysis": result}],
            selected_candidate_id="asset_good_match",
            target_aspect_ratio="9:16",
        )

        entry = bundle.shortlist[0]
        self.assertEqual(entry["semantic_status"], "success")
        self.assertIn("semantic_analysis", entry)


def _write_visual_review_fixture(
    root: Path,
    *,
    cases: list[str],
    selected_id: str | None = None,
    frame_count: int = 3,
    secret: str = "",
) -> Path:
    project = root / "project_001"
    review = project / "assets" / "review"
    review.mkdir(parents=True)
    shortlist = [_candidate(f"asset_{case}", case, frame_count=frame_count, secret=secret) for case in cases]
    manifest = {
        "schema_version": 1,
        "project_id": "project_001",
        "scene_count": 1,
        "scenes": [
            {
                "project_id": "project_001",
                "scene_id": "scene_001",
                "scene_text": "A whale swims in the ocean.",
                "semantic_scene": {
                    "scene_id": "scene_001",
                    "subject": ["whale"],
                    "action": ["swimming"],
                    "environment": ["ocean"],
                    "must_include": ["whale", "ocean"],
                    "must_not_include": ["desert"],
                    "visual_priority": "exact_action",
                },
                "target_aspect_ratio": "9:16",
                "shortlist": shortlist,
                "selected_candidate": {"asset_id": selected_id or shortlist[0]["asset_id"]},
                "alternatives": shortlist[1:],
            }
        ],
    }
    (review / "visual_review_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return project


def _candidate(asset_id: str, case: str, *, frame_count: int = 3, secret: str = "") -> dict[str, Any]:
    return {
        "asset_id": asset_id,
        "provider": "fake",
        "provider_asset_id": asset_id,
        "media_type": "video",
        "title": "Whale swimming in ocean",
        "description": "A whale swims in blue ocean water.",
        "tags": ["whale", "ocean"],
        "semantic_fixture": case,
        "raw_metadata": {"api_key": secret} if secret else {},
        "metadata_rank": 1,
        "metadata_score": 77.0,
        "technical_score": 81.0,
        "technical_metrics": {"technical_quality_score": 81.0},
        "sampled_frames": [
            {
                "frame_index": index,
                "sha256": f"{index:064x}"[-64:],
                "perceptual_hash": f"{index:016x}"[-16:],
                "local_frame_path": fr"G:\\Projects\\AI-YouTube\\projects\\project_001\\assets\\previews\\frame_{index}.jpg",
                "width": 320,
                "height": 480,
                "extraction_status": "extracted",
            }
            for index in range(frame_count)
        ],
    }


def _read_manifest(project: Path) -> dict[str, Any]:
    return json.loads((project / "assets" / "review" / "visual_review_manifest.json").read_text(encoding="utf-8"))


def _semantic_request(case: str):
    from src.assets.semantic_visual_models import SceneVisualRequirements, SemanticVisualRequest

    return SemanticVisualRequest(
        project_id="project_001",
        scene_id="scene_001",
        backend="mock",
        requirements=SceneVisualRequirements(scene_id="scene_001", scene_text="whale ocean", subject="whale", must_have=["whale"]),
        candidate_id=f"asset_{case}",
        provider="fake",
        candidate_metadata={"semantic_fixture": case, "title": "whale ocean"},
        sampled_frame_references=[],
    )


if __name__ == "__main__":
    unittest.main()
