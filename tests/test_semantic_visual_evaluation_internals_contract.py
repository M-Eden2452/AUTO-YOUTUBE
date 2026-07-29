from __future__ import annotations

import inspect
import unittest
from dataclasses import fields


class SemanticVisualEvaluationInternalsContractTests(unittest.TestCase):
    def test_public_evaluation_surface_keeps_signatures_and_dataset_shapes(self) -> None:
        from src.assets import semantic_visual_evaluation as evaluation

        load_signature = inspect.signature(evaluation.load_semantic_visual_eval_config)
        self.assertEqual(list(load_signature.parameters), ["path", "require_exists"])
        self.assertEqual(load_signature.parameters["path"].default, evaluation.DEFAULT_EVAL_CONFIG_PATH)
        self.assertEqual(load_signature.parameters["require_exists"].kind, inspect.Parameter.KEYWORD_ONLY)
        self.assertEqual(load_signature.return_annotation, "EvaluationDataset")

        build_signature = inspect.signature(evaluation.build_evaluation_requests)
        self.assertEqual(list(build_signature.parameters), ["dataset", "backend", "model", "frame_root"])
        self.assertEqual(build_signature.parameters["frame_root"].default, evaluation.DEFAULT_EVAL_FRAME_ROOT)
        self.assertEqual(build_signature.parameters["backend"].kind, inspect.Parameter.KEYWORD_ONLY)
        self.assertEqual(build_signature.return_annotation, "list[SemanticVisualRequest]")

        mocked_signature = inspect.signature(evaluation.mocked_results_for_dataset)
        self.assertEqual(list(mocked_signature.parameters), ["dataset", "backend", "model"])
        self.assertEqual(mocked_signature.parameters["backend"].kind, inspect.Parameter.KEYWORD_ONLY)
        self.assertEqual(mocked_signature.return_annotation, "dict[str, SemanticVisualResult]")

        metrics_signature = inspect.signature(evaluation.compute_evaluation_metrics)
        self.assertEqual(list(metrics_signature.parameters), ["dataset", "results"])
        self.assertEqual(metrics_signature.return_annotation, "dict[str, float]")

        run_signature = inspect.signature(evaluation.run_semantic_visual_evaluation)
        self.assertEqual(
            list(run_signature.parameters),
            ["backend", "model", "dry_run", "mocked", "config", "dataset_path", "client", "results_dir"],
        )
        self.assertTrue(
            all(parameter.kind is inspect.Parameter.KEYWORD_ONLY for parameter in run_signature.parameters.values())
        )
        self.assertEqual(run_signature.return_annotation, "dict[str, Any]")
        self.assertEqual(
            [item.name for item in fields(evaluation.EvaluationCase)],
            [
                "case_id",
                "category",
                "strictness",
                "frame_count",
                "media_type",
                "expected",
                "scene_id",
                "candidate_id",
                "provider",
                "requirements",
                "candidate_metadata",
                "sampled_frames",
                "technical_metrics_summary",
                "limited_temporal_evidence",
                "dataset_path",
            ],
        )
        self.assertEqual(
            [item.name for item in fields(evaluation.EvaluationDataset)],
            [
                "schema_version",
                "cases",
                "models",
                "scene_count",
                "candidate_count",
                "dataset_path",
                "constraints",
                "explicit_dataset",
            ],
        )

    def test_root_pipeline_imports_the_public_evaluation_runner(self) -> None:
        import pipeline
        from src.assets.semantic_visual_evaluation import run_semantic_visual_evaluation

        self.assertIs(pipeline.run_semantic_visual_evaluation, run_semantic_visual_evaluation)

    def test_facade_separates_tooling_from_controlled_runtime(self) -> None:
        from src.assets import semantic_visual_evaluation as facade
        from src.assets import semantic_visual_evaluation_runtime as runtime
        from src.assets import semantic_visual_evaluation_tooling as tooling

        self.assertIs(facade.run_semantic_visual_evaluation, runtime.run_semantic_visual_evaluation)
        self.assertIs(facade.EvaluationDataset, tooling.EvaluationDataset)
        self.assertIs(facade.compute_evaluation_metrics, tooling.compute_evaluation_metrics)


if __name__ == "__main__":
    unittest.main()
