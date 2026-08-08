"""Locks on the PLAN-9D-C offline retrieval quality gate.

The gate answers one question - can the current retrieval path reach the subject
a scene declares - and it has to answer it from the frozen corpus alone, before
any human looks at a picture. Three properties make that answer worth anything,
and each is locked here.

*The gate never becomes a live run.* PLAN-9D-B was the one bounded slice allowed
to touch a provider. Everything after it reads the frozen file, so the whole gate
is exercised under the repository's socket guard.

*The measurement is not measuring itself.* A candidate counts as carrying the
subject only if the *provider* said so. The query we sent is excluded from the
matched text, because including it would make every candidate match its own query
and the resulting number would be a restatement of the query plan.

*The expectations are anchored outside the gate.* The counts asserted below are
the ones the PLAN-9D-B closure recorded independently from the corpus file - 14
scenes, 1064 observations, 56 previewed candidates, 64 frames, 745 licensed and
319 review_required - plus the two query defects PLAN-9B repaired, which must
stay repaired. Nothing here compares the gate to a stored copy of its own output.

What is deliberately absent: any assertion about how a picture looks. The visual
read of the 56 previewed candidates belongs to the PLAN-9D-C record in the
execution plan, and the blind human annotation belongs to PLAN-9D-D.
"""

from __future__ import annotations

import unittest

from tests import network_guard
from tests.plan9d_ground_truth import load_current_corpus
from tests.plan9d_retrieval_gate import (
    MANDATORY_CASE_IDS,
    RetrievalGateError,
    candidate_metadata_text,
    declared_subject_terms,
    evaluate_query_integrity,
    evaluate_selection,
    evaluate_shortlist,
    run_retrieval_gate,
    subject_tokens,
)

# Independently recorded by the PLAN-9D-B closure from the corpus file itself.
EXPECTED_SCENES = 14
EXPECTED_OBSERVATIONS = 1064
EXPECTED_PREVIEWED = 56
EXPECTED_FRAMES = 64
EXPECTED_LICENSED = 745
EXPECTED_REVIEW_REQUIRED = 319
EXPECTED_CORPUS_SHA256 = (
    "da8e50a968afc72fcc427ffeb9b0e58fe264119f9d191d17849ce2265fa89b35"
)


class RetrievalGateOfflineTests(unittest.TestCase):
    def test_gate_runs_with_no_socket_available(self) -> None:
        with network_guard.network_guard_scope():
            report = run_retrieval_gate()
        self.assertEqual(report["corpus_sha256"], EXPECTED_CORPUS_SHA256)

    def test_gate_is_deterministic(self) -> None:
        self.assertEqual(run_retrieval_gate(), run_retrieval_gate())

    def test_gate_refuses_a_corpus_without_scenes(self) -> None:
        corpus = load_current_corpus()
        corpus["scenes"] = []
        with self.assertRaises(RetrievalGateError):
            run_retrieval_gate(corpus)


class CorpusCoverageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.report = run_retrieval_gate()

    def test_corpus_size_matches_the_recorded_capture(self) -> None:
        totals = self.report["totals"]
        self.assertEqual(totals["scenes"], EXPECTED_SCENES)
        self.assertEqual(totals["observations"], EXPECTED_OBSERVATIONS)
        self.assertEqual(totals["previewed"], EXPECTED_PREVIEWED)
        self.assertEqual(totals["frames"], EXPECTED_FRAMES)

    def test_rights_split_matches_the_recorded_capture(self) -> None:
        totals = self.report["totals"]
        self.assertEqual(totals["licensed"], EXPECTED_LICENSED)
        self.assertEqual(totals["review_required"], EXPECTED_REVIEW_REQUIRED)
        self.assertEqual(
            totals["licensed"] + totals["review_required"], EXPECTED_OBSERVATIONS
        )

    def test_mandatory_evaluation_set_is_present(self) -> None:
        self.assertEqual(self.report["missing_mandatory_cases"], [])
        cases = {entry["verdict"]["case_id"] for entry in self.report["scenes"]}
        for case_id in MANDATORY_CASE_IDS:
            self.assertIn(case_id, cases)

    def test_every_scene_has_a_pool_and_something_previewed(self) -> None:
        for entry in self.report["scenes"]:
            with self.subTest(scene=entry["verdict"]["scene_id"]):
                self.assertGreater(entry["raw_retrieval"]["pool_size"], 0)
                self.assertGreater(entry["preview_shortlist"]["previewed"], 0)


class QueryIntegrityTests(unittest.TestCase):
    """The PLAN-9B repairs have to still hold in what was actually sent."""

    def setUp(self) -> None:
        self.report = run_retrieval_gate()

    def test_no_non_provider_language_query_reached_a_provider(self) -> None:
        for entry in self.report["scenes"]:
            with self.subTest(scene=entry["verdict"]["scene_id"]):
                self.assertEqual(
                    entry["query_integrity"]["non_provider_script_queries"], []
                )

    def test_no_retired_broad_literal_reached_a_provider(self) -> None:
        for entry in self.report["scenes"]:
            with self.subTest(scene=entry["verdict"]["scene_id"]):
                self.assertEqual(entry["query_integrity"]["retired_broad_literals"], [])

    def test_every_scene_asked_a_provider_about_its_own_subject(self) -> None:
        for entry in self.report["scenes"]:
            with self.subTest(scene=entry["verdict"]["scene_id"]):
                self.assertGreaterEqual(
                    entry["query_integrity"]["subjectful_attempts"], 1
                )
                self.assertTrue(entry["query_integrity"]["declared_subject_terms"])

    def test_declared_subject_terms_drop_non_provider_language_noise(self) -> None:
        """``secondary_subjects`` also collects narration words; they are not terms."""

        scene = {
            "semantic_scene": {
                "subject": ["gecko"],
                "must_include": [],
                "secondary_subjects": ["Геккон", "гладком", "day gecko"],
            }
        }
        self.assertEqual(declared_subject_terms(scene), ["gecko", "day gecko"])

    def test_the_flat_compatibility_mirror_is_reported_not_hidden(self) -> None:
        """It is not what providers were asked, but it is persisted, so it is named."""

        self.assertEqual(
            self.report["totals"]["scenes_with_non_provider_script_in_legacy_mirror"],
            EXPECTED_SCENES,
        )

    def test_subject_free_rungs_are_counted(self) -> None:
        totals = self.report["totals"]
        self.assertGreater(totals["subject_free_provider_attempts"], 0)
        self.assertGreater(totals["results_from_subject_free_queries"], 0)


class SubjectMatchingTests(unittest.TestCase):
    """The measurement must not be able to confirm itself."""

    def test_the_query_we_sent_is_not_part_of_the_matched_text(self) -> None:
        candidate = {
            "candidate": {
                "title": "Blue ceramic mug on a table",
                "description": "",
                "tags": [],
                "keywords": [],
                "search_query": "pangolin walking",
            },
            "search_query": "pangolin walking",
        }
        text = candidate_metadata_text(candidate)
        self.assertNotIn("pangolin", text)
        self.assertIn("ceramic mug", text)

    def test_token_matching_is_looser_than_phrase_matching(self) -> None:
        terms = ["solar power plant"]
        self.assertEqual(subject_tokens(terms), ["solar", "power", "plant"])
        report = run_retrieval_gate()
        totals = report["totals"]
        self.assertGreater(totals["subject_token_hits"], totals["subject_phrase_hits"])

    def test_every_scene_pool_reaches_its_subject_at_least_once(self) -> None:
        for entry in run_retrieval_gate()["scenes"]:
            with self.subTest(scene=entry["verdict"]["scene_id"]):
                self.assertGreaterEqual(entry["raw_retrieval"]["subject_phrase_hits"], 1)


class ShortlistAndSelectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.report = run_retrieval_gate()

    def test_repeated_observations_consume_preview_slots(self) -> None:
        """A repeat inside ``candidates[:5]`` costs a slot nobody can look at."""

        self.assertEqual(self.report["totals"]["preview_slots_lost_to_repeats"], 14)
        losing = [
            entry["verdict"]["scene_id"]
            for entry in self.report["scenes"]
            if entry["preview_shortlist"]["preview_slots_lost_to_repeats"]
        ]
        self.assertEqual(len(losing), 9)

    def test_previewed_candidates_are_the_top_of_the_pool(self) -> None:
        for entry in self.report["scenes"]:
            shortlist = entry["preview_shortlist"]
            with self.subTest(scene=entry["verdict"]["scene_id"]):
                self.assertEqual(
                    shortlist["previewed_ranks"],
                    list(range(shortlist["previewed"])),
                )

    def test_no_rights_blocked_candidate_reached_the_shortlist(self) -> None:
        for entry in self.report["scenes"]:
            with self.subTest(scene=entry["verdict"]["scene_id"]):
                self.assertEqual(
                    entry["preview_shortlist"]["previewed_not_allowed_for_render"], []
                )

    def test_selection_is_not_bound_to_the_preview_window(self) -> None:
        totals = self.report["totals"]
        self.assertEqual(totals["scenes_with_selection"], 12)
        self.assertEqual(totals["selections_outside_preview_window"], 3)
        self.assertEqual(totals["selections_never_previewed"], 3)

    def test_the_video_preference_drives_most_selections(self) -> None:
        """``select_best_with_video`` takes the first non-rejected video at any rank."""

        self.assertEqual(self.report["totals"]["selections_that_are_the_first_video"], 7)

    def test_no_selected_candidate_matches_a_declared_must_avoid_phrase(self) -> None:
        for entry in self.report["scenes"]:
            with self.subTest(scene=entry["verdict"]["scene_id"]):
                self.assertFalse(entry["selection"]["selected_must_avoid_hit"])

    def test_a_scene_without_a_selection_is_reported_not_guessed(self) -> None:
        empty = [
            entry["verdict"]["scene_id"]
            for entry in self.report["scenes"]
            if not entry["selection"]["has_selection"]
        ]
        self.assertEqual(len(empty), 2)
        for entry in self.report["scenes"]:
            if not entry["selection"]["has_selection"]:
                self.assertIsNone(entry["selection"]["selected_rank"])
                self.assertFalse(entry["selection"]["selected_previewed"])


class GateVerdictTests(unittest.TestCase):
    def test_the_gate_states_a_verdict_for_every_scene(self) -> None:
        report = run_retrieval_gate()
        self.assertEqual(len(report["scenes"]), EXPECTED_SCENES)
        for entry in report["scenes"]:
            self.assertIn("passed", entry["verdict"])

    def test_the_current_corpus_passes_the_retrieval_gate(self) -> None:
        report = run_retrieval_gate()
        self.assertEqual(report["failed_scenes"], [])
        self.assertTrue(report["passed"])

    def test_the_gate_fails_when_a_subject_never_reaches_a_provider(self) -> None:
        """A negative control: the gate has to be able to say no."""

        corpus = load_current_corpus()
        scene = corpus["scenes"][0]
        scene["provider_attempts"] = [
            {
                "provider": "pexels",
                "query": "nature science wildlife observation",
                "query_language": "en",
                "query_source": "legacy",
                "status": "completed",
                "result_count": 10,
            }
        ]
        report = run_retrieval_gate(corpus)
        self.assertFalse(report["passed"])
        failures = report["failed_scenes"][0]["failures"]
        self.assertIn("no_executed_query_carried_the_subject", failures)
        self.assertIn("retired_broad_literal_reached_a_provider", failures)


class ScenePrimitiveTests(unittest.TestCase):
    """The per-scene helpers stay usable on their own, without the whole report."""

    def setUp(self) -> None:
        self.scene = load_current_corpus()["scenes"][0]

    def test_query_integrity_names_the_scene_it_measured(self) -> None:
        record = evaluate_query_integrity(self.scene)
        self.assertEqual(record["scene_id"], self.scene["scene_id"])
        self.assertEqual(record["case_id"], self.scene["case_id"])

    def test_shortlist_window_never_exceeds_the_production_size(self) -> None:
        record = evaluate_shortlist(self.scene)
        self.assertLessEqual(record["window_size"], record["shortlist_size"])
        self.assertLessEqual(record["previewed"], record["window_size"])

    def test_selection_record_survives_an_unselected_scene(self) -> None:
        scene = dict(self.scene)
        scene["selected_asset_id"] = ""
        record = evaluate_selection(scene)
        self.assertFalse(record["has_selection"])
        self.assertIsNone(record["selected_rank"])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
