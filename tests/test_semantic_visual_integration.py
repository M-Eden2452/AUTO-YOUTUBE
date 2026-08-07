from __future__ import annotations

import contextlib
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


class SemanticVisualDecisionWiringTests(unittest.TestCase):
    """PLAN-9C: the Vision verdict has to arrive while the choice is still open.

    Everything here is offline. No provider, no download, no paid backend, no render:
    the candidates come from a local media index and the semantic backend is a scripted
    stand-in, which is admissible as proof of *wiring* and of nothing else.
    """

    def test_a_failed_analysis_is_not_evidence(self) -> None:
        from src.assets.semantic_visual_models import fallback_semantic_result, semantic_result_vision_tags

        result = fallback_semantic_result(
            backend="mock", status="invalid_response", error_code="invalid_response", message="broken"
        )

        self.assertEqual(semantic_result_vision_tags(result), [])

    def test_an_answer_nobody_can_stand_behind_adds_no_positive_evidence(self) -> None:
        from src.assets.semantic_visual_models import semantic_result_vision_tags

        result = _scripted_result(confidence=0.40, subject="whale", environment=["ocean"])

        self.assertEqual(semantic_result_vision_tags(result), [])

    def test_a_confirmed_observation_becomes_evidence_the_metadata_never_gave(self) -> None:
        from src.assets.semantic_visual_models import semantic_result_vision_tags

        result = _scripted_result(subject="whale", environment=["ocean"], must_have=["whale"])

        self.assertEqual(sorted(semantic_result_vision_tags(result)), ["ocean", "whale"])

    def test_a_confirmed_forbidden_element_becomes_the_term_the_scene_forbade(self) -> None:
        from src.assets.semantic_visual_models import (
            SemanticVisualRequest,
            apply_semantic_aggregation_rules,
            semantic_result_vision_tags,
        )

        request = SemanticVisualRequest(
            project_id="p", scene_id="s", backend="mock", requirements=_requirements(), candidate_id="c", provider="fake"
        )
        result = apply_semantic_aggregation_rules(
            _scripted_result(subject="whale", environment=["ocean"], forbidden="desert"), request
        )

        self.assertTrue(result.hard_reject)
        # Only the refusal travels: a candidate the backend rejected must not also carry
        # evidence that makes it look better than an honest absence of metadata.
        self.assertEqual(semantic_result_vision_tags(result), ["desert"])

    def test_the_shortlist_pass_tags_candidates_and_stays_bounded(self) -> None:
        from src.assets.semantic_visual_service import analyse_semantic_visual_for_shortlist

        backend = _ScriptedBackend({"a1": {}, "a2": {}, "a3": {}})
        shortlist = [_review_entry("a1"), _review_entry("a2"), _review_entry("a3")]

        with tempfile.TemporaryDirectory() as tmp:
            summary = analyse_semantic_visual_for_shortlist(
                project_root=Path(tmp),
                project_id="project_001",
                scene_id="scene_001",
                semantic_scene={"subject": ["whale"], "environment": ["ocean"], "must_not_include": ["desert"]},
                shortlist=shortlist,
                backend=backend,
                maximum_candidates=2,
            )

        self.assertEqual(summary["candidates_processed"], 2)
        self.assertEqual([request.candidate_id for request in backend.seen], ["a1", "a2"])
        self.assertEqual(sorted(shortlist[0]["vision_tags"]), ["ocean", "whale"])
        self.assertNotIn("vision_tags", shortlist[2])

    def test_the_shortlist_pass_makes_no_call_when_offline(self) -> None:
        from src.assets.semantic_visual_service import analyse_semantic_visual_for_shortlist

        backend = _ScriptedBackend({"a1": {}})
        shortlist = [_review_entry("a1")]

        with tempfile.TemporaryDirectory() as tmp:
            summary = analyse_semantic_visual_for_shortlist(
                project_root=Path(tmp),
                project_id="project_001",
                scene_id="scene_001",
                semantic_scene={"subject": ["whale"]},
                shortlist=shortlist,
                backend=backend,
                offline=True,
            )

        self.assertEqual(summary["backend_calls"], 0)
        self.assertEqual(backend.seen, [])
        self.assertEqual(shortlist[0]["vision_tags"], [])

    def test_the_review_pass_reuses_what_the_shortlist_pass_already_paid_for(self) -> None:
        """The two entry points must be the same request, or a candidate is paid twice."""
        from src.assets.review_bundle import create_scene_review_bundle, write_review_bundle
        from src.assets.semantic_visual_service import (
            analyse_semantic_visual_for_project,
            analyse_semantic_visual_for_shortlist,
        )

        backend = _ScriptedBackend({"a1": {}, "a2": {}})
        scene = {"scene_id": "scene_001", "narration": "A whale in the ocean.", "target_duration_sec": 4}
        semantic_scene = {"subject": ["whale"], "environment": ["ocean"], "visual_priority": "exact_subject"}
        analyses = [_preview_analysis("a1"), _preview_analysis("a2")]
        bundle = create_scene_review_bundle(
            project_id="project_001",
            scene=scene,
            semantic_scene=semantic_scene,
            metadata_queries=[],
            provider_routing={},
            candidates=[{"asset_id": "a1", "provider": "fake"}, {"asset_id": "a2", "provider": "fake"}],
            analyses=analyses,
            selected_candidate_id="a1",
            target_aspect_ratio="9:16",
        )

        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project_001"
            analyse_semantic_visual_for_shortlist(
                project_root=project,
                project_id="project_001",
                scene_id=bundle.scene_id,
                semantic_scene=bundle.semantic_scene,
                scene_text=bundle.scene_text,
                target_aspect_ratio=bundle.target_aspect_ratio,
                shortlist=bundle.shortlist,
                backend=backend,
            )
            first_calls = len(backend.seen)
            write_review_bundle(project, [bundle], write_html=False)

            summary = analyse_semantic_visual_for_project(
                project_root=project,
                project_id="project_001",
                scene_id="scene_001",
                backend=backend,
                no_html=True,
            )

        self.assertEqual(first_calls, 2)
        self.assertEqual(summary["backend_calls"], 0)
        self.assertEqual(summary["cache_hits"], 2)
        self.assertEqual(len(backend.seen), 2)

    def test_the_choice_is_untouched_while_semantic_visual_is_off(self) -> None:
        with _project() as (root, backend):
            manifest = _build(root, backend, semantic_visual={})

        self.assertEqual(manifest["scenes"][0]["selected_asset"]["asset_id"], "local_rich")
        self.assertEqual(backend.seen, [])
        self.assertFalse(manifest["asset_selection"]["semantic_visual"]["enabled"])

    def test_vision_evidence_reaches_the_decision_before_the_asset_is_chosen(self) -> None:
        with _project() as (root, backend):
            backend.script["local_rich"] = {"forbidden": "desert"}
            manifest = _build(root, backend, semantic_visual=_WIRED)

        scene = manifest["scenes"][0]
        rejected = next(item for item in scene["ranked_candidates"] if item["asset_id"] == "local_rich")
        self.assertEqual(scene["selected_asset"]["asset_id"], "local_plain")
        self.assertEqual(rejected["vision_tags"], ["desert"])
        self.assertEqual(sorted(scene["selected_asset"]["vision_tags"]), ["ocean", "whale"])
        # The refusal is spoken in the vocabulary that already existed, by the owner that
        # already owned it - no second verdict was introduced for Vision.
        self.assertIn("must_avoid_match:desert", rejected["reject_reason"])
        self.assertIn("vision_mismatch", rejected["reject_reason"])

    def test_a_vision_failure_leaves_the_deterministic_choice_in_place(self) -> None:
        with _project() as (root, backend):
            backend.script["local_rich"] = {"raises": True}
            backend.script["local_plain"] = {"raises": True}
            manifest = _build(root, backend, semantic_visual=_WIRED)
            review = _read_manifest(root / "project_001")

        scene = manifest["scenes"][0]
        self.assertEqual(scene["selected_asset"]["asset_id"], "local_rich")
        self.assertEqual(scene["selected_asset"]["vision_tags"], [])
        # The provider really was asked before the choice; it simply had nothing to say.
        self.assertEqual(review["semantic_visual"]["summary"]["backend_calls"], 0)
        self.assertEqual(len(backend.seen), 2)

    def test_only_the_bounded_shortlist_is_shown_to_the_backend(self) -> None:
        with _project(extra=True) as (root, backend):
            manifest = _build(
                root, backend, semantic_visual={**_WIRED, "maximum_candidates": 1}
            )
            review = _read_manifest(root / "project_001")

        self.assertEqual(len({request.candidate_id for request in backend.seen}), 1)
        self.assertEqual(review["semantic_visual"]["summary"]["backend_calls"], 0)
        self.assertTrue(manifest["scenes"][0]["selected_asset"])

    def test_the_scene_is_analysed_once_across_the_whole_build(self) -> None:
        with _project() as (root, backend):
            _build(root, backend, semantic_visual=_WIRED)
            review = _read_manifest(root / "project_001")

        # The review pass after selection really did run - and found both candidates
        # already in the cache, so wiring the seam costs nothing extra.
        self.assertEqual(review["semantic_visual"]["status"], "completed")
        self.assertEqual(review["semantic_visual"]["summary"]["backend_calls"], 0)
        self.assertEqual(review["semantic_visual"]["summary"]["cache_hits"], 2)
        self.assertEqual(len(backend.seen), 2)

    def test_a_user_asset_is_not_re_ranked_by_vision(self) -> None:
        from PIL import Image

        with _project() as (root, backend):
            backend.script["user_1"] = {"forbidden": "desert"}
            user_image = root / "user_whale.png"
            Image.new("RGB", (1080, 1920), (20, 80, 120)).save(user_image)
            manifest = _build(
                root,
                backend,
                semantic_visual=_WIRED,
                user_assets=[
                    {
                        "path": str(user_image),
                        "rights_declaration": {
                            "confirmation_status": "approved",
                            "license_name": "user_owned",
                            "rights_status": "user_owned",
                            "owner_approval_status": "approved",
                        },
                    }
                ],
            )

        selected = manifest["scenes"][0]["selected_asset"]
        self.assertEqual(selected["provider"], "user")
        self.assertEqual(selected["selected_by"], "user_asset_priority_manual")
        # The shortlist was still analysed; the user's own choice is simply not the
        # ranker's to revisit.
        self.assertTrue(backend.seen)

    def test_a_fixture_backend_cannot_answer_a_requirement_the_metadata_never_met(self) -> None:
        """The shipped default backend is a fixture, and a fixture must not decide.

        ``MockSemanticVisualBackend`` builds its answer out of the request it was handed,
        so it confirms every term it is asked about. Let that reach the ranker and the
        scene's own requirement is met by the act of stating it: a candidate whose
        provider metadata never mentions an iceberg is selected for an iceberg scene, and
        the project reports itself publishable on the strength of it.
        """
        from src.assets.semantic_visual_service import load_semantic_visual_config

        # What a project gets by simply switching the feature on, without naming a backend.
        self.assertEqual(load_semantic_visual_config()["backend"], "mock")
        stated = ["whale", "iceberg"]

        with _project() as (root, _):
            off = _build(root, None, semantic_visual={}, must_include=stated)
        with _project() as (root, _):
            on = _build(root, None, semantic_visual=_WIRED, must_include=stated)

        for label, manifest in (("off", off), ("on", on)):
            with self.subTest(semantic_visual=label):
                scene = manifest["scenes"][0]
                candidate = scene["ranked_candidates"][0]
                self.assertIsNone(scene["selected_asset"])
                self.assertIn("must_include_missing:iceberg", candidate["reject_reason"])
                self.assertEqual(candidate["vision_tags"], [])
                self.assertFalse(manifest["completion"]["publish_ready"])

    def test_the_manifest_stops_reporting_a_constant_for_semantic_rerank(self) -> None:
        with _project() as (root, backend):
            wired = _build(root, backend, semantic_visual=_WIRED)
        with _project() as (root, backend):
            plain = _build(root, backend, semantic_visual={})

        self.assertTrue(wired["semantic_visual"]["semantic_rerank_enabled"])
        self.assertFalse(plain["semantic_visual"]["semantic_rerank_enabled"])


# A production-capable name, so the build treats the scripted stand-in below as evidence
# rather than as the fixture backend it replaces. It still costs nothing and reaches no
# network: what is being proved is the wiring, never the visual quality.
_WIRED = {"enabled": True, "semantic_rerank_enabled": True, "backend": "scripted"}


@contextlib.contextmanager
def _project(*, extra: bool = False):
    """A project whose candidates are real local files, so previews stay offline."""
    from PIL import Image

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for asset_id in ("local_rich", "local_plain", *(("local_spare",) if extra else ())):
            Image.new("RGB", (1080, 1920), (10, 40, 90)).save(root / f"{asset_id}.png")
        yield root, _ScriptedBackend({})


def _build(
    root: Path,
    backend: "_ScriptedBackend | None",
    *,
    semantic_visual: dict[str, Any],
    user_assets: list[Any] | None = None,
    must_include: list[str] | None = None,
) -> dict[str, Any]:
    """Build one project's manifest. ``backend=None`` leaves the real factory in place,
    so the build resolves whatever backend the configuration actually names."""
    from unittest.mock import patch

    from src.news.asset_manager import build_assets_manifest

    items = [
        _library_item("local_rich", root, "Whale in the ocean", ["whale", "ocean", "aerial"]),
        _library_item("local_plain", root, "Whale", ["whale", "ocean"]),
    ]
    if (root / "local_spare.png").exists():
        items.append(_library_item("local_spare", root, "Whale close up", ["whale", "ocean"]))
    visual_plan = {
        "scenes": [
            {
                "scene_id": "scene_001",
                "visual_type": "image",
                "primary_query": "whale ocean",
                "target_duration_sec": 4,
                "semantic": {
                    "subject": ["whale"],
                    "environment": ["ocean"],
                    "must_include": must_include or ["whale"],
                    "must_not_include": ["desert"],
                    "visual_priority": "exact_subject",
                },
            }
        ]
    }
    with contextlib.ExitStack() as stack:
        if backend is not None:
            stack.enter_context(
                patch(
                    "src.assets.semantic_visual_service.create_semantic_visual_backend",
                    return_value=backend,
                )
            )
        return build_assets_manifest(
            visual_plan=visual_plan,
            user_assets=user_assets or [],
            media_index={"version": 1, "items": items},
            providers=[],
            dry_run=False,
            project_root=root / "project_001",
            project_id="project_001",
            asset_selection={"semantic_visual": semantic_visual} if semantic_visual else {},
        )


def _library_item(asset_id: str, root: Path, title: str, keywords: list[str]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "id": asset_id,
        "type": "image",
        "provider": "local",
        "provider_asset_id": asset_id,
        "local_path": str(root / f"{asset_id}.png"),
        "title": title,
        "description": title,
        "keywords": keywords,
        "tags": keywords,
        "source_url": f"file://{asset_id}",
        "width": 1080,
        "height": 1920,
        "rights_status": "licensed",
        "allowed_for_render": True,
        "review_required": False,
        "license": {
            "license_name": "user_owned",
            "rights_status": "licensed",
            "allowed_for_render": True,
            "review_required": False,
        },
        "provenance": {"provider": "local", "provider_asset_id": asset_id, "source_page_url": f"file://{asset_id}"},
    }


def _requirements(**overrides: Any):
    from src.assets.semantic_visual_models import SceneVisualRequirements

    values = {"scene_id": "scene_001", "subject": "whale", "environment": ["ocean"], "negative_elements": ["desert"]}
    values.update(overrides)
    return SceneVisualRequirements(**values)


def _scripted_result(
    *,
    confidence: float = 0.92,
    subject: str = "",
    environment: list[str] | None = None,
    must_have: list[str] | None = None,
    forbidden: str = "",
):
    from src.assets.semantic_visual_models import (
        AggregateSemanticScores,
        FrameSemanticObservation,
        SemanticVisualResult,
        TermSemanticCheckResult,
    )

    return SemanticVisualResult(
        backend="mock",
        model="scripted",
        backend_version="scripted.v1",
        request_version="semantic_visual_request.v1",
        status="success",
        confidence=confidence,
        frames_analysed=1,
        frame_observations=[
            FrameSemanticObservation(
                frame_index=0,
                subject_observations=[subject] if subject else [],
                environment_observations=list(environment or []),
                unwanted_element_observations=[forbidden] if forbidden else [],
                confidence=confidence,
            )
        ],
        aggregate_scores=AggregateSemanticScores(
            subject_match=0.93,
            action_match=0.90,
            environment_match=0.91,
            location_match=0.90,
            exact_entity_match=0.90,
            must_have_match=0.94,
            negative_element_safety=0.05 if forbidden else 0.96,
            shot_type_match=0.0,
            mood_match=0.90,
            temporal_match=0.0,
        ),
        must_have_results=[
            TermSemanticCheckResult(term=term, present=True, confidence=0.90) for term in (must_have or [])
        ],
        negative_element_results=(
            [TermSemanticCheckResult(term=forbidden, present=True, confidence=0.95, frame_indices=[0])]
            if forbidden
            else []
        ),
    )


class _ScriptedBackend:
    """A deterministic stand-in for a semantic backend. Proof of wiring, not of quality.

    It answers from a script rather than from the request, so unlike the shipped ``mock``
    fixture it can be made to disagree with what the scene asked for - which is the only
    way a test can show that the evidence really reached the choice. It identifies itself
    as ``scripted`` for that reason: the build refuses to let a fixture backend decide.
    """

    name = "scripted"

    def __init__(self, script: dict[str, dict[str, Any]]) -> None:
        self.script = script
        self.seen: list[Any] = []

    def capabilities(self):
        from src.assets.semantic_visual_backend import SemanticBackendCapabilities

        return SemanticBackendCapabilities(
            backend="scripted", model="scripted", backend_version="scripted.v1", maximum_frames=5, paid_backend=False
        )

    def health_check(self):
        from src.assets.semantic_visual_backend import SemanticBackendHealth

        return SemanticBackendHealth(backend="scripted", configured=True, status="ready")

    def analyse_candidate(self, request):
        self.seen.append(request)
        case = self.script.get(request.candidate_id, {})
        if case.get("raises"):
            raise RuntimeError("scripted backend failure")
        return _scripted_result(
            subject=request.requirements.subject,
            environment=list(request.requirements.environment),
            must_have=list(request.requirements.must_have),
            forbidden=str(case.get("forbidden") or ""),
        )


def _review_entry(asset_id: str) -> dict[str, Any]:
    return {"asset_id": asset_id, "provider": "fake", "provider_asset_id": asset_id, "sampled_frames": []}


def _preview_analysis(asset_id: str) -> dict[str, Any]:
    return {
        "asset_id": asset_id,
        "provider": "fake",
        "provider_asset_id": asset_id,
        "analysis_status": "passed",
        "sampled_frames": [
            {"frame_index": 0, "sha256": f"{asset_id:0>64}"[-64:], "perceptual_hash": "abcd", "width": 320, "height": 480}
        ],
        "technical_metrics": {"technical_quality_score": 80.0},
        "technical_quality_score": 80.0,
        "crop_scores": {},
        "duplicate_scores": [],
    }


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
