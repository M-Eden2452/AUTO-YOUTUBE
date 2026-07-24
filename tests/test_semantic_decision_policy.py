from __future__ import annotations

import unittest


class SemanticDecisionPolicyTests(unittest.TestCase):
    def test_live_dataset_calibration_restores_suitable_material_with_limitations(self) -> None:
        from src.assets.semantic_decision_policy import evaluate_live_dataset_calibration

        evaluation = evaluate_live_dataset_calibration(
            results_path="docs/implementation/openai_live_evaluation/results/LIVE_EVAL_RESULTS.json",
            dataset_path="docs/implementation/openai_live_evaluation/LIVE_EVAL_DATASET.json",
        )

        decisions = {item["candidate_id"]: item for item in evaluation["calibrated_results"]}
        self.assertEqual(evaluation["raw_accuracy"], 0.666667)
        self.assertEqual(evaluation["calibrated_accuracy"], 0.833333)
        self.assertEqual(decisions["scene01_A_saturn_v_launch"]["calibrated_decision"], "suitable_with_limitations")
        self.assertEqual(decisions["scene03_A_misty_forest_canopy"]["calibrated_decision"], "suitable_with_limitations")
        self.assertIn("limited_temporal_evidence", decisions["scene01_A_saturn_v_launch"]["evidence_limitations"])
        self.assertIn("camera_view_mismatch_non_blocking", decisions["scene03_A_misty_forest_canopy"]["calibration_reasons"])
        self.assertEqual(decisions["scene02_B_bear_standing_river"]["calibrated_decision"], "unsuitable")
        self.assertIn("required_element_missing", decisions["scene02_B_bear_standing_river"]["calibration_reasons"])

    def test_explicit_wrong_entity_and_negative_element_remain_unsuitable(self) -> None:
        from src.assets.semantic_decision_policy import evaluate_live_dataset_calibration

        evaluation = evaluate_live_dataset_calibration(
            results_path="docs/implementation/openai_live_evaluation/results/LIVE_EVAL_RESULTS.json",
            dataset_path="docs/implementation/openai_live_evaluation/LIVE_EVAL_DATASET.json",
        )

        decisions = {item["candidate_id"]: item for item in evaluation["calibrated_results"]}
        shuttle = decisions["scene01_B_space_shuttle_launch"]
        desert = decisions["scene03_B_desert_dunes"]

        self.assertEqual(shuttle["calibrated_decision"], "unsuitable")
        self.assertIn("exact_entity_or_subject_mismatch", shuttle["calibration_reasons"])
        self.assertEqual(desert["calibrated_decision"], "unsuitable")
        self.assertIn("confirmed_negative_element", desert["calibration_reasons"])

    def test_pairwise_ranking_accuracy_is_three_of_three(self) -> None:
        from src.assets.semantic_decision_policy import evaluate_live_dataset_calibration

        evaluation = evaluate_live_dataset_calibration(
            results_path="docs/implementation/openai_live_evaluation/results/LIVE_EVAL_RESULTS.json",
            dataset_path="docs/implementation/openai_live_evaluation/LIVE_EVAL_DATASET.json",
        )

        pairwise = {item["scene_id"]: item for item in evaluation["pairwise_rankings"]}
        self.assertEqual(evaluation["pairwise_ranking_accuracy"], 1.0)
        self.assertEqual(pairwise["scene_01_strict_saturn_v"]["winner_candidate_id"], "scene01_A_saturn_v_launch")
        self.assertEqual(pairwise["scene_02_balanced_bear_salmon"]["winner_candidate_id"], "scene02_A_bear_catching_salmon")
        self.assertEqual(pairwise["scene_03_illustrative_forest_broll"]["winner_candidate_id"], "scene03_A_misty_forest_canopy")
        self.assertEqual(evaluation["pairwise_correct"], 3)
        self.assertEqual(evaluation["pairwise_total"], 3)

    def test_license_is_not_mixed_into_semantic_decision(self) -> None:
        from src.assets.semantic_decision_policy import calibrate_semantic_result

        raw = {
            "candidate_id": "licensed_review_case",
            "scene_id": "scene_license",
            "returned_classification": "review",
            "expected_classification": "suitable",
            "subject_match": True,
            "action_match": True,
            "environment_match": True,
            "exact_entity_match": True,
            "must_have_results": [{"term": "owl", "present": True, "confidence": 0.98}],
            "negative_element_results": [{"term": "watermark", "present": False, "confidence": 0.98}],
            "review_required_reasons": ["license_review_required"],
            "mismatch_reasons": [],
            "semantic_score": 0.82,
            "confidence": 0.9,
        }

        decision = calibrate_semantic_result(raw)

        self.assertEqual(decision["calibrated_decision"], "suitable")
        self.assertIn("license_review_separate", decision["evidence_limitations"])
        self.assertNotIn("license_review_required", decision["calibration_reasons"])

    def test_low_confidence_missing_must_have_is_limitation_not_review(self) -> None:
        from src.assets.semantic_decision_policy import calibrate_semantic_result

        raw = {
            "candidate_id": "owl_turn_low_resolution_concern",
            "scene_id": "owl_scene",
            "returned_classification": "review",
            "subject_match": True,
            "action_match": True,
            "environment_match": True,
            "must_have_results": [
                {"term": "owl clearly visible", "present": True, "confidence": 0.99},
                {"term": "head-turn movement", "present": True, "confidence": 0.84},
                {"term": "sufficient resolution for central 9:16 card", "present": False, "confidence": 0.68},
            ],
            "negative_element_results": [{"term": "owl remains completely static", "present": False, "confidence": 0.98}],
            "review_required_reasons": ["Review vertical reframing because crop may limit composition."],
            "mismatch_reasons": ["must_have_missing:sufficient resolution for central 9:16 card"],
            "semantic_score": 0.9566,
            "confidence": 0.92,
            "hard_reject": False,
        }

        decision = calibrate_semantic_result(raw)

        self.assertEqual(decision["calibrated_decision"], "suitable_with_limitations")
        self.assertGreaterEqual(decision["calibrated_score"], 0.95)
        self.assertIn("low_confidence_required_element_missing", decision["evidence_limitations"])


if __name__ == "__main__":
    unittest.main()
