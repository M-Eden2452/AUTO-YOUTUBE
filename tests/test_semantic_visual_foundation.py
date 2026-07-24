from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path


class SemanticVisualFoundationTests(unittest.TestCase):
    def test_scene_visual_requirements_serialization(self) -> None:
        from src.assets.semantic_visual_models import SceneVisualRequirements

        requirements = SceneVisualRequirements(
            scene_id="scene_001",
            scene_text="A southern right whale swims near the Australian coast.",
            subject="southern right whale",
            secondary_subjects=["calf"],
            action="swimming",
            environment=["ocean", "coastal waters"],
            location=["Australia"],
            exact_entity="southern right whale",
            must_have=["whale", "ocean"],
            negative_elements=["desert", "road"],
            shot_type="wide",
            camera_view="drone",
            mood=["calm"],
            time_period="modern",
            weather="clear",
            target_aspect_ratio="9:16",
            scene_purpose="exact subject B-roll",
            acceptable_alternatives=["right whale"],
            semantic_strictness="strict",
        )

        loaded = SceneVisualRequirements.from_dict(requirements.to_dict())

        self.assertEqual(loaded.scene_id, "scene_001")
        self.assertEqual(loaded.subject, "southern right whale")
        self.assertEqual(loaded.must_have, ["whale", "ocean"])
        self.assertEqual(loaded.semantic_strictness, "strict")

    def test_adapter_from_current_semantic_scene(self) -> None:
        from src.assets.semantic_visual_models import SceneVisualRequirements

        current = {
            "scene_id": "scene_001",
            "subject": ["southern right whale"],
            "secondary_subjects": ["calf"],
            "action": ["swimming"],
            "environment": ["ocean"],
            "location": ["Australia"],
            "camera": ["drone"],
            "mood": ["calm"],
            "must_include": ["whale", "ocean"],
            "must_not_include": ["desert"],
            "visual_priority": "exact_subject",
        }

        requirements = SceneVisualRequirements.from_current_semantic_scene(
            current,
            scene={"scene_id": "scene_001", "narration": "Whale mother and calf at sea.", "target_aspect_ratio": "9:16"},
        )

        self.assertEqual(requirements.subject, "southern right whale")
        self.assertEqual(requirements.action, "swimming")
        self.assertEqual(requirements.environment, ["ocean"])
        self.assertEqual(requirements.negative_elements, ["desert"])
        self.assertEqual(requirements.camera_view, "drone")
        self.assertEqual(requirements.semantic_strictness, "strict")

    def test_semantic_request_serialization_hides_absolute_paths(self) -> None:
        from src.assets.semantic_visual_models import (
            SceneVisualRequirements,
            SemanticFrameReference,
            SemanticVisualRequest,
        )

        request = SemanticVisualRequest(
            project_id="project_001",
            scene_id="scene_001",
            backend="mock",
            requirements=SceneVisualRequirements(scene_id="scene_001", scene_text="whale ocean", subject="whale"),
            candidate_id="asset_001",
            provider="fake",
            candidate_metadata={"title": "whale ocean", "local_path": r"G:\\Projects\\AI-YouTube\\secret.jpg"},
            sampled_frame_references=[
                SemanticFrameReference(
                    frame_index=0,
                    sha256="a" * 64,
                    perceptual_hash="0" * 16,
                    relative_path="assets/previews/frame.jpg",
                    private_local_path=r"G:\\Projects\\AI-YouTube\\frame.jpg",
                )
            ],
            technical_metrics_summary={"technical_quality_score": 83.0},
            maximum_frames=5,
            backend_options={"model": "mock-v1", "api_key": "SECRET_TOKEN_VALUE"},
        )

        data = request.to_public_dict()
        raw = json.dumps(data, ensure_ascii=False)

        self.assertEqual(data["request_version"], "semantic_visual_request.v1")
        self.assertNotIn("G:\\", raw)
        self.assertNotIn("SECRET_TOKEN_VALUE", raw)
        self.assertNotIn("api_key", raw.lower())

    def test_semantic_result_validation(self) -> None:
        from src.assets.semantic_visual_models import AggregateSemanticScores, SemanticVisualResult

        result = SemanticVisualResult(
            backend="mock",
            model="mock-v1",
            backend_version="mock.1",
            request_version="semantic_visual_request.v1",
            status="success",
            confidence=0.91,
            frames_analysed=3,
            aggregate_scores=AggregateSemanticScores(subject_match=0.9, overall_semantic_match=0.88),
            semantic_score=0.88,
        )

        result.assert_valid()
        self.assertEqual(result.validation_errors(), [])

    def test_score_range_validation(self) -> None:
        from src.assets.semantic_visual_models import AggregateSemanticScores, SemanticVisualResult

        result = SemanticVisualResult(
            backend="mock",
            model="mock-v1",
            backend_version="mock.1",
            request_version="semantic_visual_request.v1",
            status="success",
            confidence=1.1,
            aggregate_scores=AggregateSemanticScores(subject_match=1.2),
            semantic_score=-0.1,
        )

        errors = result.validation_errors()

        self.assertTrue(any("confidence" in error for error in errors))
        self.assertTrue(any("aggregate_scores.subject_match" in error for error in errors))
        self.assertTrue(any("semantic_score" in error for error in errors))
        with self.assertRaises(ValueError):
            result.assert_valid()

    def test_stable_cache_key(self) -> None:
        from src.assets.semantic_visual_cache import compute_semantic_cache_key

        request = _request(case="good_match")

        first = compute_semantic_cache_key(request, semantic_config={"minimum_confidence": 0.65}, prompt_template_version="mock.template.v1")
        second = compute_semantic_cache_key(_request(case="good_match"), semantic_config={"minimum_confidence": 0.65}, prompt_template_version="mock.template.v1")
        changed = compute_semantic_cache_key(_request(case="subject_mismatch"), semantic_config={"minimum_confidence": 0.65}, prompt_template_version="mock.template.v1")

        self.assertEqual(first, second)
        self.assertNotEqual(first, changed)
        self.assertEqual(len(first), 64)

    def test_semantic_cache_hit(self) -> None:
        from src.assets.semantic_visual_cache import SemanticVisualCache, compute_semantic_cache_key
        from src.assets.semantic_visual_mock import MockSemanticVisualBackend

        with tempfile.TemporaryDirectory() as tmp:
            request = _request(case="good_match")
            key = compute_semantic_cache_key(request, semantic_config={}, prompt_template_version="mock.template.v1")
            backend = MockSemanticVisualBackend()
            result = backend.analyse_candidate(request)
            result.cache_key = key
            cache = SemanticVisualCache(Path(tmp))

            cache.write(result)
            hit = cache.read(key)

            self.assertIsNotNone(hit)
            self.assertEqual(hit.cache_key, key)
            self.assertEqual(hit.status, "success")

    def test_corrupted_cache_invalidation(self) -> None:
        from src.assets.semantic_visual_cache import SemanticVisualCache

        with tempfile.TemporaryDirectory() as tmp:
            cache = SemanticVisualCache(Path(tmp))
            folder = Path(tmp) / ("c" * 64)
            folder.mkdir(parents=True)
            (folder / "semantic_result.json").write_text("{not json", encoding="utf-8")

            self.assertIsNone(cache.read("c" * 64))

    def test_mock_good_match(self) -> None:
        from src.assets.semantic_visual_mock import MockSemanticVisualBackend

        result = MockSemanticVisualBackend().analyse_candidate(_request(case="good_match"))

        self.assertEqual(result.status, "success")
        self.assertGreater(result.aggregate_scores.subject_match, 0.85)
        self.assertGreater(result.semantic_score, 0.85)
        self.assertFalse(result.hard_reject)
        self.assertTrue(result.evidence)

    def test_subject_mismatch(self) -> None:
        from src.assets.semantic_visual_mock import MockSemanticVisualBackend

        result = MockSemanticVisualBackend().analyse_candidate(_request(case="subject_mismatch"))

        self.assertLess(result.aggregate_scores.subject_match, 0.4)
        self.assertIn("subject_mismatch", result.mismatch_reasons)
        self.assertFalse(result.hard_reject)

    def test_action_mismatch(self) -> None:
        from src.assets.semantic_visual_mock import MockSemanticVisualBackend

        result = MockSemanticVisualBackend().analyse_candidate(_request(case="action_mismatch"))

        self.assertLess(result.aggregate_scores.action_match, 0.4)
        self.assertIn("action_mismatch", result.mismatch_reasons)

    def test_negative_violation(self) -> None:
        from src.assets.semantic_visual_mock import MockSemanticVisualBackend

        result = MockSemanticVisualBackend().analyse_candidate(_request(case="negative_violation"))

        self.assertLess(result.aggregate_scores.negative_element_safety, 0.2)
        self.assertTrue(result.hard_reject)
        self.assertIn("negative_element_detected:desert", result.mismatch_reasons)

    def test_low_confidence_violation_does_not_hard_reject(self) -> None:
        from src.assets.semantic_visual_mock import MockSemanticVisualBackend

        result = MockSemanticVisualBackend().analyse_candidate(_request(case="low_confidence_negative"))

        self.assertFalse(result.hard_reject)
        self.assertIn("negative_element_low_confidence:desert", result.review_required_reasons)

    def test_single_image_limits_action_confidence(self) -> None:
        from src.assets.semantic_visual_mock import MockSemanticVisualBackend

        result = MockSemanticVisualBackend().analyse_candidate(_request(case="good_match", frame_count=1, media_type="image"))

        self.assertLessEqual(result.aggregate_scores.action_match, 0.65)
        self.assertIn("single_frame_action_limited", result.review_required_reasons)

    def test_multiple_frames_aggregate_correctly(self) -> None:
        from src.assets.semantic_visual_mock import MockSemanticVisualBackend

        result = MockSemanticVisualBackend().analyse_candidate(_request(case="good_match", frame_count=5, media_type="video"))

        self.assertEqual(result.frames_analysed, 5)
        self.assertGreater(result.aggregate_scores.action_match, 0.8)
        self.assertNotIn("single_frame_action_limited", result.review_required_reasons)

    def test_one_anomalous_frame_does_not_dominate(self) -> None:
        from src.assets.semantic_visual_mock import MockSemanticVisualBackend

        result = MockSemanticVisualBackend().analyse_candidate(_request(case="one_anomalous_frame", frame_count=5, media_type="video"))

        self.assertFalse(result.hard_reject)
        self.assertGreater(result.semantic_score, 0.7)
        self.assertIn("anomalous_frame_observed", result.review_required_reasons)

    def test_backend_timeout_fallback_result(self) -> None:
        from src.assets.semantic_visual_mock import MockSemanticVisualBackend

        result = MockSemanticVisualBackend().analyse_candidate(_request(case="timeout"))

        self.assertEqual(result.status, "timeout")
        self.assertEqual(result.error.code, "timeout")
        self.assertEqual(result.semantic_score, 0.0)

    def test_invalid_response_fallback_result(self) -> None:
        from src.assets.semantic_visual_mock import MockSemanticVisualBackend

        result = MockSemanticVisualBackend().analyse_candidate(_request(case="invalid_response"))

        self.assertEqual(result.status, "invalid_response")
        self.assertEqual(result.error.code, "invalid_response")
        self.assertTrue(result.review_required_reasons)

    def test_paid_backend_blocked_by_default(self) -> None:
        from src.assets.semantic_visual_external import ExternalSemanticVisualBackend

        backend = ExternalSemanticVisualBackend({"backend": "future_vendor", "model": "future-model", "allow_paid_vision": False, "maximum_budget_usd": 25})
        result = backend.analyse_candidate(_request(case="good_match"))

        self.assertEqual(result.status, "configuration_error")
        self.assertEqual(result.error.code, "paid_vision_disabled")

    def test_zero_budget_blocks_external_backend(self) -> None:
        from src.assets.semantic_visual_external import ExternalSemanticVisualBackend

        backend = ExternalSemanticVisualBackend({"backend": "future_vendor", "model": "future-model", "allow_paid_vision": True, "maximum_budget_usd": 0})
        result = backend.analyse_candidate(_request(case="good_match"))

        self.assertEqual(result.status, "configuration_error")
        self.assertEqual(result.error.code, "budget_required")

    def test_unicode_windows_cache_paths(self) -> None:
        from src.assets.semantic_visual_cache import SemanticVisualCache, compute_semantic_cache_key
        from src.assets.semantic_visual_mock import MockSemanticVisualBackend

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "unicode сцена"
            request = _request(case="good_match")
            key = compute_semantic_cache_key(request, semantic_config={}, prompt_template_version="mock.template.v1")
            result = MockSemanticVisualBackend().analyse_candidate(request)
            result.cache_key = key
            cache = SemanticVisualCache(root)

            cache.write(result)

            self.assertTrue((root / key / "semantic_result.json").is_file())
            self.assertEqual(cache.read(key).cache_key, key)

    def test_network_guard_remains_active(self) -> None:
        from tests.network_guard import live_tests_enabled

        self.assertFalse(live_tests_enabled())


def _request(*, case: str, frame_count: int = 3, media_type: str = "video"):
    from src.assets.semantic_visual_models import (
        SceneVisualRequirements,
        SemanticFrameReference,
        SemanticVisualRequest,
    )

    requirements = SceneVisualRequirements(
        scene_id="scene_001",
        scene_text="A whale swims in the ocean.",
        subject="whale",
        action="swimming",
        environment=["ocean"],
        must_have=["whale", "ocean"],
        negative_elements=["desert"],
        semantic_strictness="balanced",
    )
    frames = [
        SemanticFrameReference(
            frame_index=index,
            sha256=f"{index:064x}"[-64:],
            perceptual_hash=f"{index:016x}"[-16:],
            relative_path=f"assets/previews/frame_{index}.jpg",
            width=320,
            height=480,
            is_poster_frame=media_type == "video" and frame_count == 1,
        )
        for index in range(frame_count)
    ]
    return SemanticVisualRequest(
        project_id="project_001",
        scene_id="scene_001",
        backend="mock",
        requirements=requirements,
        candidate_id=f"asset_{case}",
        provider="fake",
        candidate_metadata={
            "asset_id": f"asset_{case}",
            "provider": "fake",
            "media_type": media_type,
            "title": "Whale swimming in ocean",
            "tags": ["whale", "ocean"],
            "semantic_fixture": case,
        },
        sampled_frame_references=frames,
        technical_metrics_summary={"technical_quality_score": 82.0},
        maximum_frames=frame_count,
        backend_options={"model": "mock-semantic-v1"},
    )


if __name__ == "__main__":
    unittest.main()
