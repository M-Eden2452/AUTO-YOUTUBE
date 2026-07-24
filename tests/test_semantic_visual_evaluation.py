from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock


class SemanticVisualEvaluationTests(unittest.TestCase):
    def test_eval_dataset_loading(self) -> None:
        from src.assets.semantic_visual_evaluation import load_semantic_visual_eval_config

        dataset = load_semantic_visual_eval_config()

        self.assertGreaterEqual(len(dataset.cases), 12)
        categories = {case.category for case in dataset.cases}
        self.assertIn("wrong_subject", categories)
        self.assertIn("poster_only_video", categories)
        self.assertIn("strict_scene", categories)

    def test_eval_metrics(self) -> None:
        from src.assets.semantic_visual_evaluation import compute_evaluation_metrics, load_semantic_visual_eval_config, mocked_results_for_dataset

        dataset = load_semantic_visual_eval_config()
        results = mocked_results_for_dataset(dataset, backend="openai", model="gpt-5.6-terra")
        metrics = compute_evaluation_metrics(dataset, results)

        self.assertIn("subject_classification_accuracy", metrics)
        self.assertIn("must_have_recall", metrics)
        self.assertIn("structured_output_validity", metrics)
        self.assertGreaterEqual(metrics["structured_output_validity"], 0.99)

    def test_empty_action_is_ignored_by_metrics(self) -> None:
        from src.assets.semantic_visual_evaluation import EvaluationCase, EvaluationDataset, compute_evaluation_metrics
        from src.assets.semantic_visual_models import AggregateSemanticScores, SemanticVisualResult

        dataset = EvaluationDataset(
            schema_version="semantic_visual_eval.v1",
            cases=[
                EvaluationCase(
                    case_id="illustrative_no_action",
                    category="illustrative",
                    strictness="illustrative",
                    frame_count=1,
                    media_type="image",
                    expected={"subject": "match", "action": None, "environment": "match", "exact_entity": None},
                )
            ],
        )
        result = SemanticVisualResult(
            backend="openai",
            model="gpt-5.6-terra",
            backend_version="test",
            request_version="semantic_visual_request.v1",
            status="success",
            confidence=0.9,
            frames_analysed=1,
            aggregate_scores=AggregateSemanticScores(subject_match=0.9, action_match=0.1, environment_match=0.9, exact_entity_match=0.1),
        )

        metrics = compute_evaluation_metrics(dataset, {"illustrative_no_action": result})

        self.assertEqual(metrics["action_evaluation_count"], 0)
        self.assertEqual(metrics["subject_evaluation_count"], 1)

    def test_empty_exact_entity_is_ignored_by_metrics(self) -> None:
        from src.assets.semantic_visual_evaluation import EvaluationCase, EvaluationDataset, compute_evaluation_metrics
        from src.assets.semantic_visual_models import AggregateSemanticScores, SemanticVisualResult

        dataset = EvaluationDataset(
            schema_version="semantic_visual_eval.v1",
            cases=[
                EvaluationCase(
                    case_id="illustrative_no_exact",
                    category="illustrative",
                    strictness="illustrative",
                    frame_count=1,
                    media_type="image",
                    expected={"subject": "match", "action": None, "environment": "match", "exact_entity": None},
                )
            ],
        )
        result = SemanticVisualResult(
            backend="openai",
            model="gpt-5.6-terra",
            backend_version="test",
            request_version="semantic_visual_request.v1",
            status="success",
            confidence=0.9,
            frames_analysed=1,
            aggregate_scores=AggregateSemanticScores(subject_match=0.9, action_match=0.1, environment_match=0.9, exact_entity_match=0.1),
        )

        metrics = compute_evaluation_metrics(dataset, {"illustrative_no_exact": result})

        self.assertEqual(metrics["exact_entity_evaluation_count"], 0)
        self.assertEqual(metrics["environment_evaluation_count"], 1)

    def test_two_crops_of_one_image_do_not_count_as_temporal_frames(self) -> None:
        from src.assets.semantic_visual_evaluation import build_evaluation_requests, load_semantic_visual_eval_config

        with tempfile.TemporaryDirectory() as tmp:
            dataset_path = _write_prepared_dataset(Path(tmp), scenes=1, candidates_per_scene=1, frames_per_candidate=2)

            dataset = load_semantic_visual_eval_config(dataset_path, require_exists=True)
            requests = build_evaluation_requests(dataset, backend="openai", model="gpt-5.6-terra")

        self.assertEqual(len(requests), 1)
        self.assertEqual(len(requests[0].sampled_frame_references), 1)
        self.assertEqual(requests[0].candidate_metadata["media_type"], "image")
        self.assertTrue(requests[0].candidate_metadata["limited_temporal_evidence"])
        self.assertTrue(requests[0].sampled_frame_references[0].is_poster_frame)
        self.assertEqual(requests[0].maximum_frames, 1)

    def test_explicit_dataset_produces_six_calls_and_six_images(self) -> None:
        from src.assets.semantic_visual_evaluation import run_semantic_visual_evaluation

        with tempfile.TemporaryDirectory() as tmp:
            dataset_path = _write_prepared_dataset(Path(tmp), scenes=3, candidates_per_scene=2, frames_per_candidate=2)

            result = run_semantic_visual_evaluation(
                backend="openai",
                model="gpt-5.6-terra",
                dry_run=True,
                dataset_path=dataset_path,
                config={"max_calls_cli": 6, "budget_usd_cli": 0.5, "allow_paid_vision_cli": True, "confirm_paid_vision": "LIVE_VISION_APPROVED"},
            )

        self.assertEqual(result["scenes"], 3)
        self.assertEqual(result["candidates"], 6)
        self.assertEqual(result["projected_calls"], 6)
        self.assertEqual(result["projected_image_count"], 6)
        self.assertEqual(result["valid_requests"], 6)
        self.assertEqual(result["invalid_requests"], 0)

    def test_live_execution_blocks_when_dataset_limits_mismatch(self) -> None:
        from src.assets.semantic_visual_evaluation import run_semantic_visual_evaluation

        with tempfile.TemporaryDirectory() as tmp:
            dataset_path = _write_prepared_dataset(Path(tmp), scenes=3, candidates_per_scene=2, frames_per_candidate=2)

            result = run_semantic_visual_evaluation(
                backend="openai",
                model="gpt-5.6-terra",
                dry_run=False,
                mocked=False,
                dataset_path=dataset_path,
                config={"max_calls_cli": 5, "budget_usd_cli": 0.5, "allow_paid_vision_cli": True, "confirm_paid_vision": "LIVE_VISION_APPROVED"},
            )

        self.assertEqual(result["status"], "blocked")
        self.assertIn("dataset_limits_mismatch", result["live_blocked_reasons"])

    def test_config_defaults_remain_disabled_for_openai_live_eval(self) -> None:
        config = json.loads(Path("config/semantic_visual.json").read_text(encoding="utf-8"))

        self.assertFalse(config["openai"]["enabled"])
        self.assertFalse(config["openai"]["allow_paid_vision"])
        self.assertEqual(config["openai"]["maximum_budget_usd"], 0)
        self.assertEqual(config["openai"]["maximum_calls_per_project"], 0)
        self.assertFalse(config["semantic_rerank_enabled"])

    def test_missing_runtime_gate_blocks_controlled_evaluation(self) -> None:
        from src.assets.semantic_visual_evaluation import run_semantic_visual_evaluation

        base_config = {
            "allow_paid_vision_cli": True,
            "budget_usd_cli": 0.5,
            "max_calls_cli": 6,
            "confirm_paid_vision": "LIVE_VISION_APPROVED",
        }
        cases = {
            "allow_paid_vision_cli": ({**base_config, "allow_paid_vision_cli": False}, _controlled_live_eval_dataset_path(), "runtime_allow_paid_vision_required"),
            "budget_usd_cli": ({**base_config, "budget_usd_cli": 0.0}, _controlled_live_eval_dataset_path(), "runtime_budget_usd_required"),
            "max_calls_cli": ({**base_config, "max_calls_cli": 0}, _controlled_live_eval_dataset_path(), "runtime_max_calls_required"),
            "confirm_paid_vision": ({**base_config, "confirm_paid_vision": ""}, _controlled_live_eval_dataset_path(), "runtime_confirmation_required"),
            "dataset_path": (base_config, None, "runtime_dataset_required"),
            "api_key": (base_config, _controlled_live_eval_dataset_path(), "runtime_openai_key_required"),
        }

        for label, (config, dataset_path, expected_reason) in cases.items():
            env = {"OPENAI_API_KEY": "sk-test-not-printed"} if label != "api_key" else {}
            with self.subTest(label=label), mock.patch.dict("os.environ", env, clear=True):
                result = run_semantic_visual_evaluation(
                    backend="openai",
                    model="gpt-5.6-terra",
                    dry_run=True,
                    mocked=False,
                    dataset_path=dataset_path,
                    config=config,
                )

            self.assertFalse(result["runtime_authorized"])
            self.assertFalse(result["budget_allowed"])
            self.assertIn(expected_reason, result["live_blocked_reasons"])

    def test_budget_above_controlled_cap_blocks_runtime_authorization(self) -> None:
        from src.assets.semantic_visual_evaluation import run_semantic_visual_evaluation

        with mock.patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test-not-printed"}, clear=True):
            result = run_semantic_visual_evaluation(
                backend="openai",
                model="gpt-5.6-terra",
                dry_run=True,
                dataset_path=_controlled_live_eval_dataset_path(),
                config={
                    "allow_paid_vision_cli": True,
                    "budget_usd_cli": 0.51,
                    "max_calls_cli": 6,
                    "confirm_paid_vision": "LIVE_VISION_APPROVED",
                },
            )

        self.assertFalse(result["runtime_authorized"])
        self.assertFalse(result["budget_allowed"])
        self.assertIn("runtime_budget_cap_exceeded", result["live_blocked_reasons"])

    def test_max_calls_above_controlled_cap_blocks_runtime_authorization(self) -> None:
        from src.assets.semantic_visual_evaluation import run_semantic_visual_evaluation

        with mock.patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test-not-printed"}, clear=True):
            result = run_semantic_visual_evaluation(
                backend="openai",
                model="gpt-5.6-terra",
                dry_run=True,
                dataset_path=_controlled_live_eval_dataset_path(),
                config={
                    "allow_paid_vision_cli": True,
                    "budget_usd_cli": 0.5,
                    "max_calls_cli": 7,
                    "confirm_paid_vision": "LIVE_VISION_APPROVED",
                },
            )

        self.assertFalse(result["runtime_authorized"])
        self.assertFalse(result["budget_allowed"])
        self.assertIn("runtime_call_limit_exceeded", result["live_blocked_reasons"])

    def test_wrong_dataset_blocks_runtime_authorization(self) -> None:
        from src.assets.semantic_visual_evaluation import run_semantic_visual_evaluation

        with tempfile.TemporaryDirectory() as tmp:
            dataset_path = _write_prepared_dataset(Path(tmp), scenes=3, candidates_per_scene=2, frames_per_candidate=2)
            with mock.patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test-not-printed"}, clear=True):
                result = run_semantic_visual_evaluation(
                    backend="openai",
                    model="gpt-5.6-terra",
                    dry_run=True,
                    dataset_path=dataset_path,
                    config={
                        "allow_paid_vision_cli": True,
                        "budget_usd_cli": 0.5,
                        "max_calls_cli": 6,
                        "confirm_paid_vision": "LIVE_VISION_APPROVED",
                    },
                )

        self.assertFalse(result["runtime_authorized"])
        self.assertFalse(result["budget_allowed"])
        self.assertIn("runtime_dataset_not_allowlisted", result["live_blocked_reasons"])

    def test_dataset_count_mismatch_blocks_runtime_authorization(self) -> None:
        from src.assets.semantic_visual_evaluation import run_semantic_visual_evaluation

        with tempfile.TemporaryDirectory() as tmp:
            dataset_path = _write_prepared_dataset(Path(tmp), scenes=2, candidates_per_scene=2, frames_per_candidate=2)
            with mock.patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test-not-printed"}, clear=True):
                result = run_semantic_visual_evaluation(
                    backend="openai",
                    model="gpt-5.6-terra",
                    dry_run=True,
                    dataset_path=dataset_path,
                    config={
                        "allow_paid_vision_cli": True,
                        "budget_usd_cli": 0.5,
                        "max_calls_cli": 6,
                        "confirm_paid_vision": "LIVE_VISION_APPROVED",
                    },
                )

        self.assertFalse(result["runtime_authorized"])
        self.assertFalse(result["budget_allowed"])
        self.assertIn("runtime_dataset_counts_mismatch", result["live_blocked_reasons"])

    def test_dry_run_runtime_authorization_never_calls_api_backend(self) -> None:
        from src.assets.semantic_visual_evaluation import run_semantic_visual_evaluation

        with mock.patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test-not-printed"}, clear=True), mock.patch(
            "src.assets.semantic_visual_openai.OpenAISemanticVisualBackend.analyse_candidate",
            side_effect=AssertionError("dry-run must not call OpenAI backend"),
        ) as analyse_candidate:
            result = run_semantic_visual_evaluation(
                backend="openai",
                model="gpt-5.6-terra",
                dry_run=True,
                dataset_path=_controlled_live_eval_dataset_path(),
                config={
                    "allow_paid_vision_cli": True,
                    "budget_usd_cli": 0.5,
                    "max_calls_cli": 6,
                    "confirm_paid_vision": "LIVE_VISION_APPROVED",
                },
            )

        self.assertTrue(result["runtime_authorized"])
        analyse_candidate.assert_not_called()
        self.assertFalse(result["live_vision_calls_performed"])
        self.assertFalse(result["paid_calls_performed"])

    def test_controlled_live_evaluation_uses_fake_client_and_records_usage(self) -> None:
        from src.assets.semantic_visual_evaluation import run_semantic_visual_evaluation
        from tests.test_semantic_visual_openai_backend import _FakeOpenAIClient, _fake_response, _semantic_payload

        responses = [
            _fake_response(
                _semantic_payload(),
                usage={"input_tokens": 100 + index, "output_tokens": 20 + index, "input_tokens_details": {"cached_tokens": index}},
            )
            for index in range(6)
        ]
        client = _FakeOpenAIClient(responses)

        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test-not-printed"}, clear=True):
            result = run_semantic_visual_evaluation(
                backend="openai",
                model="gpt-5.6-terra",
                dry_run=False,
                mocked=False,
                dataset_path=_controlled_live_eval_dataset_path(),
                config={
                    "allow_paid_vision_cli": True,
                    "budget_usd_cli": 0.5,
                    "max_calls_cli": 6,
                    "confirm_paid_vision": "LIVE_VISION_APPROVED",
                },
                client=client,
                results_dir=Path(tmp) / "results",
            )

        self.assertEqual(result["status"], "completed")
        self.assertTrue(result["live_vision_calls_performed"])
        self.assertTrue(result["paid_calls_performed"])
        self.assertEqual(result["calls_attempted"], 6)
        self.assertEqual(result["calls_succeeded"], 6)
        self.assertEqual(result["calls_failed"], 0)
        self.assertEqual(result["images_sent"], 6)
        self.assertEqual(result["external_http_attempts"], 6)
        self.assertEqual(client.responses.call_count, 6)
        self.assertEqual(len(result["candidate_results"]), 6)
        self.assertEqual(result["total_input_tokens"], 615)
        self.assertEqual(result["total_output_tokens"], 135)

    def test_controlled_live_evaluation_caps_external_attempts_including_retries(self) -> None:
        from src.assets.semantic_visual_evaluation import run_semantic_visual_evaluation
        from tests.test_semantic_visual_openai_backend import _FakeHTTPError, _FakeOpenAIClient

        client = _FakeOpenAIClient([_FakeHTTPError(500) for _ in range(10)])

        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test-not-printed"}, clear=True):
            result = run_semantic_visual_evaluation(
                backend="openai",
                model="gpt-5.6-terra",
                dry_run=False,
                mocked=False,
                dataset_path=_controlled_live_eval_dataset_path(),
                config={
                    "allow_paid_vision_cli": True,
                    "budget_usd_cli": 0.5,
                    "max_calls_cli": 6,
                    "confirm_paid_vision": "LIVE_VISION_APPROVED",
                },
                client=client,
                results_dir=Path(tmp) / "results",
            )

        self.assertEqual(result["external_http_attempts"], 6)
        self.assertEqual(client.responses.call_count, 6)
        self.assertLessEqual(result["calls_attempted"], 6)
        self.assertIn("external_attempt_limit_reached", result["stop_reasons"])

    def test_controlled_live_evaluation_stops_after_auth_error(self) -> None:
        from src.assets.semantic_visual_evaluation import run_semantic_visual_evaluation
        from tests.test_semantic_visual_openai_backend import _FakeHTTPError, _FakeOpenAIClient, _fake_response, _semantic_payload

        client = _FakeOpenAIClient([_FakeHTTPError(401), _fake_response(_semantic_payload())])

        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test-not-printed"}, clear=True):
            result = run_semantic_visual_evaluation(
                backend="openai",
                model="gpt-5.6-terra",
                dry_run=False,
                mocked=False,
                dataset_path=_controlled_live_eval_dataset_path(),
                config={
                    "allow_paid_vision_cli": True,
                    "budget_usd_cli": 0.5,
                    "max_calls_cli": 6,
                    "confirm_paid_vision": "LIVE_VISION_APPROVED",
                },
                client=client,
                results_dir=Path(tmp) / "results",
            )

        self.assertEqual(result["calls_attempted"], 1)
        self.assertEqual(result["calls_succeeded"], 0)
        self.assertEqual(result["calls_failed"], 1)
        self.assertEqual(result["external_http_attempts"], 1)
        self.assertEqual(client.responses.call_count, 1)
        self.assertIn("authentication_error", result["stop_reasons"])

    def test_runtime_authorization_does_not_mutate_config_file(self) -> None:
        from src.assets.semantic_visual_evaluation import run_semantic_visual_evaluation

        config_path = Path("config/semantic_visual.json")
        before = config_path.read_bytes()
        with mock.patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test-not-printed"}, clear=True):
            run_semantic_visual_evaluation(
                backend="openai",
                model="gpt-5.6-terra",
                dry_run=True,
                dataset_path=_controlled_live_eval_dataset_path(),
                config={
                    "allow_paid_vision_cli": True,
                    "budget_usd_cli": 0.5,
                    "max_calls_cli": 6,
                    "confirm_paid_vision": "LIVE_VISION_APPROVED",
                },
            )
        after = config_path.read_bytes()

        self.assertEqual(after, before)

    def test_evaluation_does_not_change_selection(self) -> None:
        from src.assets.semantic_visual_evaluation import run_semantic_visual_evaluation

        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp) / "visual_review_manifest.json"
            before = {"scenes": [{"scene_id": "scene_001", "selected_candidate": {"asset_id": "asset_a"}}]}
            manifest.write_text(json.dumps(before), encoding="utf-8")

            run_semantic_visual_evaluation(backend="mock", model="mock-semantic-v1", dry_run=False, mocked=True)

            after = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual(after, before)

    def test_network_guard_remains_active(self) -> None:
        from tests.network_guard import live_tests_enabled

        self.assertFalse(live_tests_enabled())


def _controlled_live_eval_dataset_path() -> Path:
    return Path("docs/implementation/openai_live_evaluation/LIVE_EVAL_DATASET.json")


def _write_prepared_dataset(root: Path, *, scenes: int, candidates_per_scene: int, frames_per_candidate: int) -> Path:
    from PIL import Image

    frame_root = root / "frames"
    frame_root.mkdir(parents=True, exist_ok=True)
    scene_items = []
    for scene_index in range(scenes):
        candidates = []
        for candidate_index in range(candidates_per_scene):
            frames = []
            for frame_index in range(frames_per_candidate):
                path = frame_root / f"scene_{scene_index}_candidate_{candidate_index}_frame_{frame_index}.jpg"
                Image.new("RGB", (32 + frame_index, 48 + frame_index), (scene_index * 20, candidate_index * 30, frame_index * 40)).save(path)
                frames.append(
                    {
                        "frame_index": frame_index,
                        "relative_path": path.name,
                        "dataset_relative_path": str(path),
                        "width": 32 + frame_index,
                        "height": 48 + frame_index,
                        "requested_timestamp_sec": float(frame_index),
                        "actual_timestamp_sec": float(frame_index),
                        "extraction_status": "ok",
                        "is_poster_frame": frame_index == 0,
                        "sha256": f"{scene_index}{candidate_index}{frame_index}".zfill(64),
                        "perceptual_hash": f"{frame_index:016x}",
                        "technical_metrics": {"width": 32 + frame_index, "height": 48 + frame_index},
                    }
                )
            candidates.append(
                {
                    "label": chr(ord("A") + candidate_index),
                    "candidate_id": f"scene_{scene_index}_candidate_{candidate_index}",
                    "provider": "fixture",
                    "provider_asset_id": f"asset_{scene_index}_{candidate_index}",
                    "title": "Fixture still image",
                    "source_page": "https://example.test/source",
                    "preview_use": "review_only_preview_use",
                    "sampled_frames": frames,
                    "technical_analysis": {"frame_count": frames_per_candidate},
                    "ground_truth": {
                        "expected_subject_match": candidate_index == 0,
                        "expected_action_match": None if scene_index == 2 else candidate_index == 0,
                        "expected_environment_match": candidate_index == 0,
                        "expected_exact_entity_match": None if scene_index == 2 else candidate_index == 0,
                        "expected_must_have": [{"term": "fixture", "present": candidate_index == 0}],
                        "expected_negative_elements": [{"term": "wrong", "present": candidate_index != 0}],
                        "expected_classification": "suitable" if candidate_index == 0 else "unsuitable",
                        "explanation": "Fixture ground truth.",
                    },
                }
            )
        scene_items.append(
            {
                "scene_id": f"scene_{scene_index}",
                "scene_type": "illustrative" if scene_index == 2 else "balanced",
                "requirements": {
                    "scene_id": f"scene_{scene_index}",
                    "scene_text": "Fixture scene",
                    "subject": "fixture subject",
                    "action": "" if scene_index == 2 else "fixture action",
                    "environment": ["fixture environment"],
                    "location": [],
                    "exact_entity": "" if scene_index == 2 else "fixture exact",
                    "must_have": ["fixture"],
                    "negative_elements": ["wrong"],
                    "semantic_strictness": "illustrative" if scene_index == 2 else "balanced",
                },
                "candidates": candidates,
            }
        )
    dataset = {
        "schema_version": "openai_live_eval_dataset.v1",
        "project_id": "fixture",
        "constraints": {
            "scenes": scenes,
            "candidates_per_scene": candidates_per_scene,
            "maximum_frames_per_candidate": 1,
            "maximum_future_api_calls": scenes * candidates_per_scene,
            "maximum_future_images": scenes * candidates_per_scene,
            "model": "gpt-5.6-terra",
            "detail": "low",
        },
        "scenes": scene_items,
    }
    path = root / "live_eval_dataset.json"
    path.write_text(json.dumps(dataset), encoding="utf-8")
    return path


if __name__ == "__main__":
    unittest.main()
