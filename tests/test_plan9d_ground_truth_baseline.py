"""Locks on the PLAN-9D-A offline ground-truth benchmark.

These tests guard the properties the benchmark's value rests on: the ground
truth is human and frozen, the annotator was blind, the measurement consumes
those annotations instead of producing them, and a fixture backend can never be
mistaken for evidence of visual quality.

They deliberately do not need the cached preview images. The corpus carries
every field the decision owner reads plus each frame's path and SHA256, so the
whole suite runs on a machine that has never seen ``projects/``.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from tests.plan9d_corpus_builder import annotation_template, render_pack
from tests.plan9d_ground_truth import (
    ANNOTATIONS_PATH,
    ARM_METADATA_ONLY,
    BLINDED_CANDIDATE_KEYS,
    CANDIDATE_FLAG_SPEC,
    CORPUS_CATEGORIES,
    CORPUS_PATH,
    PREFERENCE_NONE_ACCEPTABLE,
    STATUS_COMPLETE,
    STATUS_WAITING,
    BenchmarkError,
    annotations_are_complete,
    assert_admissible_evidence,
    assign_blind_ids,
    compare_arms,
    corpus_digest,
    evaluate_arm,
    load_annotations,
    load_corpus,
    run_metadata_baseline,
    validate_annotations,
    validate_corpus,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class CorpusContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.corpus = load_corpus()

    def test_frozen_corpus_validates(self) -> None:
        validate_corpus(self.corpus)

    def test_corpus_is_large_enough_to_measure_anything(self) -> None:
        scenes = self.corpus["scenes"]
        self.assertGreaterEqual(len(scenes), 12, "PLAN-9D-A requires at least 12 independent scenes")
        self.assertEqual(len(scenes), self.corpus["scene_count"])
        observations = sum(len(scene["candidates"]) for scene in scenes)
        self.assertEqual(observations, self.corpus["observation_count"])
        self.assertGreaterEqual(observations, 40)
        for scene in scenes:
            self.assertGreaterEqual(len(scene["candidates"]), 2, scene["scene_key"])

    def test_scenes_are_independent(self) -> None:
        """No scene text is reused, and no single project dominates the corpus."""

        texts = [str(scene["scene_text"]).strip().casefold() for scene in self.corpus["scenes"]]
        self.assertEqual(len(texts), len(set(texts)))
        projects = [scene["project"] for scene in self.corpus["scenes"]]
        self.assertGreaterEqual(len(set(projects)), 10)
        for project in set(projects):
            self.assertLessEqual(projects.count(project), 3, project)

    def test_category_coverage_including_the_documented_gap(self) -> None:
        covered = {c for scene in self.corpus["scenes"] for c in scene["categories"]}
        self.assertLessEqual(covered, set(CORPUS_CATEGORIES))
        for required in (
            "must_include_declared",
            "must_avoid_declared",
            "declared_conflicting_context",
            "environment_conflict_risk",
            "subject_mismatch_risk",
            "crop_framing_concern",
            "visible_text_or_logo_risk",
            "ambiguous_needs_review",
            "rights_blocked_candidate",
            "technical_dimensions_unknown",
            "no_acceptable_candidate",
        ):
            self.assertIn(required, covered, f"corpus lost coverage of {required}")
        # Recorded, not repaired: no candidate in any local project carries
        # non-real-footage wording in provider evidence, so the category cannot be
        # covered without inventing a scene. It stays in the vocabulary as a known
        # gap rather than being quietly dropped or faked.
        self.assertNotIn("non_real_footage_risk", covered)

    def test_regression_capable_scenes_exist(self) -> None:
        """Without them an A/B could never show that a change made things worse."""

        capable = [s for s in self.corpus["scenes"] if "regression_capable" in s["categories"]]
        self.assertGreaterEqual(len(capable), 5)

    def test_corpus_carries_declared_dimensions_not_preview_dimensions(self) -> None:
        """The framing gate must judge the asset, never the cached thumbnail."""

        compared = 0
        for scene in self.corpus["scenes"]:
            for entry in scene["candidates"]:
                width = int(entry["candidate"].get("width") or 0)
                height = int(entry["candidate"].get("height") or 0)
                if not width or not height:
                    self.assertIn(
                        "technical_dimensions_unknown",
                        scene["categories"],
                        f"{scene['scene_key']}: undeclared dimensions are not tagged",
                    )
                    continue
                for frame in entry["frames"]:
                    if frame.get("width") and (width, height) != (frame["width"], frame["height"]):
                        compared += 1
        self.assertGreater(compared, 0, "no candidate proves asset and preview sizes differ")

    def test_corpus_is_the_metadata_only_arm(self) -> None:
        for scene in self.corpus["scenes"]:
            for entry in scene["candidates"]:
                self.assertEqual(entry["candidate"].get("vision_tags"), [])


class ProvenanceTests(unittest.TestCase):
    def test_recorded_digest_matches_the_frozen_content(self) -> None:
        corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
        self.assertEqual(corpus["corpus_sha256"], corpus_digest(corpus))

    def test_any_edit_changes_the_digest(self) -> None:
        corpus = load_corpus()
        corpus["scenes"][0]["scene_text"] = corpus["scenes"][0]["scene_text"] + " edited"
        with self.assertRaises(BenchmarkError):
            validate_corpus(corpus)

    def test_annotations_are_bound_to_one_corpus(self) -> None:
        corpus = load_corpus()
        annotations = load_annotations()
        self.assertIs(annotations["blind"], True)
        self.assertEqual(annotations["corpus_sha256"], corpus["corpus_sha256"])
        annotations["corpus_sha256"] = "0" * 64
        complete, problems = annotations_are_complete(corpus, annotations)
        self.assertFalse(complete)
        self.assertTrue(any("corpus_sha256" in problem for problem in problems))

    def test_every_frame_is_recorded_with_a_checksum(self) -> None:
        for scene in load_corpus()["scenes"]:
            for entry in scene["candidates"]:
                self.assertTrue(entry["frames"], f"{scene['scene_key']}/{entry['blind_id']}")
                for frame in entry["frames"]:
                    self.assertRegex(str(frame["sha256"]), r"^[0-9a-f]{64}$")


class BlindingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.corpus = load_corpus()

    def test_blind_ids_are_derived_not_invented(self) -> None:
        for scene in self.corpus["scenes"]:
            expected = assign_blind_ids(
                scene["scene_key"], [entry["asset_id"] for entry in scene["candidates"]]
            )
            actual = {entry["asset_id"]: entry["blind_id"] for entry in scene["candidates"]}
            self.assertEqual(actual, expected, scene["scene_key"])

    def test_stored_order_is_blind_order(self) -> None:
        for scene in self.corpus["scenes"]:
            self.assertEqual(
                [entry["blind_id"] for entry in scene["candidates"]],
                [f"C{i}" for i in range(1, len(scene["candidates"]) + 1)],
                scene["scene_key"],
            )

    def test_blind_order_is_not_the_manifest_order(self) -> None:
        """Otherwise the blind id would be the stored ranking under a new name."""

        reshuffled = [
            scene
            for scene in self.corpus["scenes"]
            if [entry["input_order"] for entry in scene["candidates"]]
            != list(range(len(scene["candidates"])))
        ]
        self.assertGreaterEqual(len(reshuffled), len(self.corpus["scenes"]) // 2)

    def test_annotation_pack_shows_no_provider_or_ranking_evidence(self) -> None:
        """The pack may show the requirement and the pictures. Nothing else.

        A candidate value is only a leak when the pack shows it *and* the scene's
        own stated requirement does not already contain it: a stock title can
        legitimately repeat the location the author asked for, and the annotator
        has to see that requirement.
        """

        pack = render_pack(self.corpus).casefold()
        for scene in self.corpus["scenes"]:
            requirement = " ".join(
                str(value)
                for values in (scene.get("semantic_scene") or {}).values()
                for value in (values if isinstance(values, list) else [values])
            ).casefold()
            requirement += " " + str(scene["scene_text"]).casefold()
            for entry in scene["candidates"]:
                for key in BLINDED_CANDIDATE_KEYS:
                    value = entry["candidate"].get(key)
                    if not isinstance(value, str) or len(value.strip()) <= 4:
                        continue
                    text = value.strip().casefold()
                    if text in requirement:
                        continue
                    self.assertNotIn(text, pack, f"{scene['scene_key']}/{entry['blind_id']}: {key}")
            for category in scene["categories"]:
                self.assertNotIn(category, pack, scene["scene_key"])
        for token in ("input_order", "metadata_rank", "final_score", "support_status", "rejected"):
            self.assertNotIn(token, pack, token)

    def test_annotation_pack_asks_only_what_a_human_can_judge(self) -> None:
        pack = render_pack(self.corpus)
        for name in CANDIDATE_FLAG_SPEC:
            self.assertIn(name, pack)
        for forbidden in ("license", "rights", "provider_confidence", "metadata_score"):
            self.assertNotIn(forbidden, pack.casefold())


class AnnotationContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.corpus = load_corpus()
        self.annotations = load_annotations()

    def test_template_covers_every_scene_and_every_candidate(self) -> None:
        validate_annotations(self.annotations)
        expected = {scene["scene_key"] for scene in self.corpus["scenes"]}
        self.assertEqual({s["scene_key"] for s in self.annotations["scenes"]}, expected)
        by_key = {s["scene_key"]: s for s in self.annotations["scenes"]}
        for scene in self.corpus["scenes"]:
            entry = by_key[scene["scene_key"]]
            self.assertEqual(
                set(entry["candidates"]),
                {c["blind_id"] for c in scene["candidates"]},
                scene["scene_key"],
            )
            for flags in entry["candidates"].values():
                self.assertEqual(set(flags), set(CANDIDATE_FLAG_SPEC))

    def test_template_is_regenerated_identically_from_the_corpus(self) -> None:
        self.assertEqual(annotation_template(self.corpus), self.annotations)

    def test_owner_annotation_is_still_outstanding(self) -> None:
        """The first commit of PLAN-9D-A ships a benchmark that is not yet labelled."""

        self.assertEqual(self.annotations["status"], STATUS_WAITING)
        complete, problems = annotations_are_complete(self.corpus, self.annotations)
        self.assertFalse(complete)
        self.assertTrue(any("preferred_candidate" in problem for problem in problems))

    def test_out_of_vocabulary_flag_is_refused(self) -> None:
        annotations = load_annotations()
        first = annotations["scenes"][0]
        blind_id = next(iter(first["candidates"]))
        first["candidates"][blind_id]["must_avoid"] = "maybe"
        with self.assertRaises(BenchmarkError):
            validate_annotations(annotations)

    def test_preference_must_name_a_candidate_of_that_scene(self) -> None:
        annotations = _complete(self.corpus)
        annotations["scenes"][0]["preferred_candidate"] = "C99"
        complete, problems = annotations_are_complete(self.corpus, annotations)
        self.assertFalse(complete)
        self.assertTrue(any("C99" in problem for problem in problems))


class MetadataBaselineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.corpus = load_corpus()

    def test_baseline_is_deterministic(self) -> None:
        first = run_metadata_baseline(self.corpus)
        second = run_metadata_baseline(self.corpus)
        self.assertEqual(
            {k: (v.selected_blind_id, v.support_status) for k, v in first.items()},
            {k: (v.selected_blind_id, v.support_status) for k, v in second.items()},
        )

    def test_baseline_covers_every_scene_and_can_abstain(self) -> None:
        results = run_metadata_baseline(self.corpus)
        self.assertEqual(set(results), {s["scene_key"] for s in self.corpus["scenes"]})
        self.assertTrue(any(r.abstained for r in results.values()))
        self.assertTrue(any(not r.abstained for r in results.values()))
        for key, result in results.items():
            if result.selected_blind_id is not None:
                self.assertRegex(result.selected_blind_id, r"^C\d+$", key)

    def test_selection_is_not_pinned_to_one_blind_position(self) -> None:
        """Guards the defect this harness had: blind order deciding every tie."""

        chosen = {r.selected_blind_id for r in run_metadata_baseline(self.corpus).values()}
        chosen.discard(None)
        self.assertGreaterEqual(len(chosen), 3)

    def test_abstention_is_recorded_with_its_blocking_reasons(self) -> None:
        results = run_metadata_baseline(self.corpus)
        abstained = [r for r in results.values() if r.abstained]
        self.assertTrue(abstained)
        for result in abstained:
            reasons = {
                reason
                for record in result.per_candidate.values()
                for reason in record["blocking_reject_reasons"]
            }
            self.assertTrue(reasons, result.scene_key)


class MeasurementTests(unittest.TestCase):
    def setUp(self) -> None:
        self.corpus = load_corpus()
        self.selections = run_metadata_baseline(self.corpus)

    def test_measurement_waits_instead_of_inventing_a_result(self) -> None:
        report = evaluate_arm(self.corpus, load_annotations(), self.selections)
        self.assertEqual(report["status"], STATUS_WAITING)
        self.assertEqual(report["scenes"], [])
        self.assertEqual(report["aggregate"], {})
        self.assertTrue(report["blocking"])

    def test_measurement_never_writes_to_the_annotations(self) -> None:
        before = ANNOTATIONS_PATH.read_bytes()
        annotations = load_annotations()
        evaluate_arm(self.corpus, annotations, self.selections)
        evaluate_arm(self.corpus, annotations, self.selections)
        self.assertEqual(ANNOTATIONS_PATH.read_bytes(), before)
        self.assertEqual(annotations, load_annotations())

    def test_a_frozen_annotation_set_measures_without_asking_anyone(self) -> None:
        report = evaluate_arm(self.corpus, _complete(self.corpus), self.selections)
        self.assertEqual(report["status"], STATUS_COMPLETE)
        self.assertEqual(len(report["scenes"]), len(self.corpus["scenes"]))
        aggregate = report["aggregate"]
        for key in (
            "preferred_matches",
            "unacceptable_selected",
            "abstentions",
            "correct_abstentions",
            "wrong_abstentions",
            "must_avoid_escaped",
            "safe_escalations_to_review",
            "undecidable_cases",
        ):
            self.assertIn(key, aggregate)
        self.assertEqual(
            aggregate["abstentions"],
            sum(1 for r in self.selections.values() if r.abstained),
        )

    def test_abstention_is_scored_against_what_the_human_said(self) -> None:
        annotations = _complete(self.corpus, preference=PREFERENCE_NONE_ACCEPTABLE)
        report = evaluate_arm(self.corpus, annotations, self.selections)
        rows = {row["scene_key"]: row for row in report["scenes"]}
        for key, selection in self.selections.items():
            if selection.abstained:
                self.assertTrue(rows[key]["correct_abstention"], key)
                self.assertFalse(rows[key]["wrong_abstention"], key)

    def test_no_confidence_number_is_invented(self) -> None:
        report = evaluate_arm(self.corpus, _complete(self.corpus), self.selections)
        for row in report["scenes"]:
            self.assertNotIn("confidence", json.dumps(row))


class EvidenceAdmissibilityTests(unittest.TestCase):
    def test_fixture_backends_are_refused_as_quality_evidence(self) -> None:
        for source in ("mock", "scripted", "vision:mock", "VISION:Scripted", "fixture", "stub"):
            with self.assertRaises(BenchmarkError, msg=source):
                assert_admissible_evidence("candidate", source)

    def test_real_arms_are_admissible(self) -> None:
        assert_admissible_evidence("baseline", ARM_METADATA_ONLY)
        assert_admissible_evidence("candidate", "vision:openai")

    def test_a_fixture_arm_cannot_be_measured_at_all(self) -> None:
        corpus = load_corpus()
        with self.assertRaises(BenchmarkError):
            evaluate_arm(
                corpus,
                load_annotations(),
                run_metadata_baseline(corpus),
                arm_name="candidate",
                evidence_source="vision:mock",
            )


class ArmComparisonTests(unittest.TestCase):
    """The A/B step of PLAN-9D adds an arm, not a second measurement system."""

    def _arm(self, name: str, **row: object) -> dict[str, object]:
        base = {
            "scene_key": "s1",
            "selection_matches_preferred": False,
            "unacceptable_selected": False,
            "correct_abstention": False,
            "wrong_abstention": False,
            "must_avoid_escaped": False,
            "non_real_footage_selected": False,
        }
        base.update(row)
        return {"status": STATUS_COMPLETE, "arm": name, "corpus_sha256": "x", "scenes": [base]}

    def test_matching_the_human_preference_is_an_improvement(self) -> None:
        result = compare_arms(self._arm("a"), self._arm("b", selection_matches_preferred=True))
        self.assertEqual(result["aggregate"]["improvements"], 1)
        self.assertEqual(result["aggregate"]["blocking_regressions"], 0)

    def test_letting_a_must_avoid_through_is_a_blocking_regression(self) -> None:
        result = compare_arms(
            self._arm("a", selection_matches_preferred=True),
            self._arm("b", selection_matches_preferred=True, must_avoid_escaped=True),
        )
        self.assertEqual(result["aggregate"]["blocking_regressions"], 1)
        self.assertEqual(result["aggregate"]["improvements"], 0)

    def test_losing_the_preferred_answer_is_a_safe_regression(self) -> None:
        result = compare_arms(self._arm("a", selection_matches_preferred=True), self._arm("b"))
        self.assertEqual(result["aggregate"]["safe_regressions"], 1)
        self.assertEqual(result["aggregate"]["blocking_regressions"], 0)

    def test_arms_from_different_corpora_are_refused(self) -> None:
        other = self._arm("b")
        other["corpus_sha256"] = "y"
        with self.assertRaises(BenchmarkError):
            compare_arms(self._arm("a"), other)

    def test_comparison_waits_while_either_arm_is_unmeasured(self) -> None:
        corpus = load_corpus()
        waiting = evaluate_arm(corpus, load_annotations(), run_metadata_baseline(corpus))
        self.assertEqual(compare_arms(waiting, self._arm("b"))["status"], STATUS_WAITING)


class LocalPreviewTests(unittest.TestCase):
    """The pictures live in the untracked project tree, so this is opt-in."""

    def test_every_recorded_frame_exists_on_this_machine(self) -> None:
        corpus = load_corpus()
        missing = [
            frame["local_frame_path"]
            for scene in corpus["scenes"]
            for entry in scene["candidates"]
            for frame in entry["frames"]
            if not (REPO_ROOT / frame["local_frame_path"]).is_file()
        ]
        if len(missing) == sum(
            len(entry["frames"]) for scene in corpus["scenes"] for entry in scene["candidates"]
        ):
            self.skipTest("local project previews are not present on this machine")
        self.assertEqual(missing, [])


def _complete(corpus: dict, *, preference: str | None = None) -> dict:
    """A synthetic COMPLETE annotation set, for testing the harness only.

    It is never written to disk and never used as evidence about a picture: its
    only job is to prove that the harness measures a frozen annotation set
    without asking a human anything.
    """

    return {
        "schema_version": "plan9d-annotations-1",
        "corpus_version": corpus["corpus_version"],
        "corpus_sha256": corpus["corpus_sha256"],
        "blind": True,
        "annotator": "synthetic-harness-test",
        "annotated_at_utc": "2026-08-08T00:00:00Z",
        "status": STATUS_COMPLETE,
        "scenes": [
            {
                "scene_key": scene["scene_key"],
                "preferred_candidate": preference or scene["candidates"][0]["blind_id"],
                "unacceptable_candidates": [],
                "note": "",
                "candidates": {
                    entry["blind_id"]: {name: "undecidable" for name in CANDIDATE_FLAG_SPEC}
                    for entry in scene["candidates"]
                },
            }
            for scene in corpus["scenes"]
        ],
    }


if __name__ == "__main__":
    unittest.main()
