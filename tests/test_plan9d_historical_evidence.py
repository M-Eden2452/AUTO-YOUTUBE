"""Locks on the curated PLAN-9D historical failure evidence.

The fixture has one job: keep the proof that the pre-9B/9C retrieval defects
were real, after the gigabytes that produced them are released. So these tests
check two different kinds of thing.

*That the proof survives.* Each preserved case still carries the scene's
requirement, the query that actually reached each provider, and the pool that
came back - including the repetition across independent scenes, which is the
evidence rather than noise to be deduplicated away.

*That it can never be mistaken for a quality result.* The fixture cannot be
loaded as benchmark input, cannot be measured, cannot be handed to an annotator,
and relabelling its provenance breaks validation rather than opening the gate.

Nothing here reads a picture, a provider or a model. The fixture carries frame
paths and checksums; the bytes stay in the untracked runtime tree, and every
test in this module passes on a machine that has never seen ``projects/``.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from tests import network_guard
from tests.plan9d_corpus_builder import (
    HISTORICAL_CASES,
    RETIRED_QUERY_CLASSES,
    curate_historical_evidence,
)
from tests.plan9d_ground_truth import (
    FIXTURE_KIND_HISTORICAL_EVIDENCE,
    GENERATION_CURRENT,
    GENERATION_HISTORICAL,
    HISTORICAL_EVIDENCE_PATH,
    HISTORICAL_EVIDENCE_SCHEMA_VERSION,
    HISTORICAL_FAILURE_MODES,
    OWNER_ANNOTATION_KEYS,
    BenchmarkError,
    assert_current_benchmark_input,
    evaluate_arm,
    historical_digest,
    historical_runtime_paths,
    load_historical_evidence,
    run_metadata_baseline,
    validate_corpus,
    validate_historical_evidence,
)


REPO_ROOT = Path(__file__).resolve().parents[1]

#: The literal that was appended to every scene of a legacy visual plan and is
#: recorded as registry C36. Spelled out here rather than imported from
#: production: the compatibility guard that still recognises it has its own exit
#: condition, and this evidence has to outlive that removal.
RETIRED_BROAD_LITERAL = "nature science wildlife observation"


def _case(fixture: dict, case_id: str) -> dict:
    return next(case for case in fixture["cases"] if case["case_id"] == case_id)


def _queries(case: dict) -> list[str]:
    return [str(attempt["query"]) for attempt in case["historical_provider_attempts"]]


class ProvenanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = load_historical_evidence()

    def test_the_fixture_validates_and_says_what_it_is(self) -> None:
        validate_historical_evidence(self.fixture)
        self.assertEqual(self.fixture["schema_version"], HISTORICAL_EVIDENCE_SCHEMA_VERSION)
        self.assertEqual(self.fixture["fixture_kind"], FIXTURE_KIND_HISTORICAL_EVIDENCE)
        self.assertEqual(self.fixture["generation_class"], GENERATION_HISTORICAL)
        self.assertEqual(self.fixture["plan_step"], "PLAN-9D-A")
        self.assertIn("never be used as a benchmark", self.fixture["not_a_benchmark"])

    def test_every_case_names_where_it_came_from(self) -> None:
        for case in self.fixture["cases"]:
            self.assertTrue(case["source_project"], case["case_id"])
            self.assertTrue(case["source_scene_id"], case["case_id"])
            self.assertEqual(
                case["scene_key"], f"{case['source_project']}/{case['source_scene_id']}"
            )
            self.assertTrue(case["scene_text"].strip(), case["case_id"])
            for manifest in case["source_manifests"]:
                self.assertTrue(manifest.startswith("projects/"), manifest)

    def test_the_superseded_corpus_is_recorded_as_a_reachable_anchor(self) -> None:
        derived = self.fixture["derived_from"]
        self.assertRegex(str(derived["corpus_sha256"]), r"^[0-9a-f]{64}$")
        self.assertRegex(str(derived["corpus_commit"]), r"^[0-9a-f]{40}$")
        self.assertEqual(derived["corpus_path"], "tests/data/plan9d/corpus_v1.json")
        self.assertGreater(int(derived["corpus_scene_count"]), self.fixture["case_count"])

    def test_the_digest_covers_the_content(self) -> None:
        on_disk = json.loads(HISTORICAL_EVIDENCE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(on_disk["fixture_sha256"], historical_digest(on_disk))

    def test_any_edit_changes_the_digest(self) -> None:
        self.fixture["cases"][0]["historical_primary_query"] += " edited"
        with self.assertRaises(BenchmarkError):
            validate_historical_evidence(self.fixture)


class SeparationFromTheBenchmarkTests(unittest.TestCase):
    """It records what retrieval used to return. It measures nothing."""

    def setUp(self) -> None:
        self.fixture = load_historical_evidence()

    def test_it_is_refused_as_benchmark_input(self) -> None:
        with self.assertRaises(BenchmarkError) as raised:
            assert_current_benchmark_input(self.fixture)
        self.assertIn("PLAN-9D-B", str(raised.exception))

    def test_the_decision_owner_is_never_run_over_it(self) -> None:
        with self.assertRaises(BenchmarkError):
            run_metadata_baseline(self.fixture)
        with self.assertRaises(BenchmarkError):
            evaluate_arm(self.fixture, {}, {})

    def test_relabelling_it_as_current_breaks_validation_instead_of_opening_the_gate(self) -> None:
        relabelled = load_historical_evidence()
        relabelled["generation_class"] = GENERATION_CURRENT
        with self.assertRaises(BenchmarkError):
            assert_current_benchmark_input(relabelled)
        with self.assertRaises(BenchmarkError):
            validate_historical_evidence(relabelled)

    def test_wearing_the_benchmark_schema_does_not_make_it_a_benchmark(self) -> None:
        disguised = load_historical_evidence()
        disguised["schema_version"] = "plan9d-corpus-1"
        disguised["fixture_kind"] = "current_retrieval_benchmark"
        disguised["generation_class"] = GENERATION_CURRENT
        with self.assertRaises(BenchmarkError):
            validate_corpus(disguised)

    def test_it_carries_no_aggregate_quality_number(self) -> None:
        """Counting anything across these cases would be a metric about the old queries."""

        serialised = json.dumps(self.fixture, ensure_ascii=False)
        for token in (
            "preferred_matches",
            "unacceptable_selected",
            "correct_abstentions",
            "final_score",
            "support_status",
            "semantic_score",
            "confidence",
        ):
            self.assertNotIn(token, serialised, token)

    def test_it_carries_no_vision_result(self) -> None:
        for case in self.fixture["cases"]:
            for candidate in case["candidates"]:
                self.assertFalse(candidate.get("vision_tags"))


class NoOwnerAnnotationTests(unittest.TestCase):
    """Blind owner annotation belongs to the current corpus, and happens once."""

    def test_no_label_is_present_anywhere(self) -> None:
        serialised = json.dumps(load_historical_evidence(), ensure_ascii=False)
        for key in OWNER_ANNOTATION_KEYS:
            self.assertNotIn(key, serialised, key)

    def test_a_fabricated_label_is_refused_rather_than_absorbed(self) -> None:
        """Re-frozen on purpose: the refusal has to be the rule, not the checksum."""

        fixture = load_historical_evidence()
        fixture["cases"][0]["preferred_candidate"] = "C1"
        fixture["fixture_sha256"] = historical_digest(fixture)
        with self.assertRaises(BenchmarkError) as raised:
            validate_historical_evidence(fixture)
        self.assertIn("annotation", str(raised.exception))

    def test_a_fabricated_label_does_not_make_it_measurable_either(self) -> None:
        fixture = load_historical_evidence()
        fixture["annotator"] = "someone"
        with self.assertRaises(BenchmarkError):
            assert_current_benchmark_input(fixture)


class PreservedFailureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = load_historical_evidence()
        self.by_mode: dict[str, list[dict]] = {mode: [] for mode in HISTORICAL_FAILURE_MODES}
        for case in self.fixture["cases"]:
            for mode in case["failure_modes"]:
                self.by_mode[mode].append(case)

    def test_the_retired_broad_literal_is_preserved_verbatim(self) -> None:
        cases = self.by_mode["retired_broad_query_literal"]
        self.assertTrue(cases)
        for case in cases:
            self.assertEqual(set(_queries(case)), {RETIRED_BROAD_LITERAL})
            self.assertEqual(case["retired_query_class"], "C36")
        recorded = {entry["literal"] for entry in self.fixture["retired_query_classes"]}
        self.assertIn(RETIRED_BROAD_LITERAL, recorded)

    def test_the_subject_never_reached_the_provider(self) -> None:
        cases = self.by_mode["subject_absent_from_provider_query"]
        self.assertGreaterEqual(len(cases), 3)
        for case in cases:
            self.assertTrue(case["expected_subject_terms"], case["case_id"])
            asked = " ".join(_queries(case)).casefold()
            for term in case["expected_subject_terms"]:
                self.assertNotIn(str(term).casefold(), asked, f"{case['case_id']}: {term}")

    def test_the_named_subject_scenes_are_the_ones_kept(self) -> None:
        """PLAN-9D-C names gecko, hummingbird and penguin; the proof for each stays."""

        kept = {case["case_id"] for case in self.fixture["cases"]}
        for subject in ("gecko", "hummingbird", "penguin"):
            self.assertTrue(
                any(subject in case_id for case_id in kept), f"lost the {subject} evidence"
            )

    def test_independent_scenes_sharing_one_pool_is_kept_as_the_evidence(self) -> None:
        """The repetition is the defect. Deduplicating it would delete the finding."""

        cases = self.by_mode["shared_generic_candidate_pool"]
        self.assertGreaterEqual(len(cases), 3)
        self.assertGreaterEqual(len({case["source_project"] for case in cases}), 3)
        subjects = [tuple(case["expected_subject_terms"]) for case in cases]
        self.assertEqual(len(subjects), len(set(subjects)), "the subjects must differ")
        pools = [{c["asset_id"] for c in case["candidates"]} for case in cases]
        self.assertGreaterEqual(len(set.intersection(*pools)), 3)

    def test_a_shared_pool_is_not_counted_as_independent_observation(self) -> None:
        """Three scenes served one pool; that is one finding, not three data points."""

        cases = self.by_mode["shared_generic_candidate_pool"]
        distinct = {c["asset_id"] for case in cases for c in case["candidates"]}
        observations = sum(len(case["candidates"]) for case in cases)
        self.assertLess(len(distinct), observations)
        self.assertNotIn("observation_count", self.fixture)

    def test_a_non_provider_language_query_is_preserved(self) -> None:
        cases = self.by_mode["non_provider_language_query"]
        self.assertTrue(cases)
        for case in cases:
            cyrillic = [q for q in _queries(case) if any("а" <= ch.casefold() <= "я" for ch in q)]
            self.assertTrue(cyrillic, case["case_id"])
            answered = [
                attempt
                for attempt in case["historical_provider_attempts"]
                if attempt["result_count"] > 0
            ]
            self.assertTrue(answered, "the point is that a latin index answered anyway")

    def test_the_subject_lost_after_a_usable_primary_query_is_preserved(self) -> None:
        cases = self.by_mode["subject_lost_after_primary_query"]
        self.assertTrue(cases)
        for case in cases:
            primary = str(case["historical_primary_query"]).casefold()
            self.assertTrue(
                any(str(term).casefold() in primary for term in case["expected_subject_terms"]),
                f"{case['case_id']}: the primary query has to contain the subject",
            )
            for query in _queries(case):
                self.assertEqual(len(query.split()), 1, f"{case['case_id']}: {query!r}")

    def test_degenerate_single_token_queries_are_preserved(self) -> None:
        cases = self.by_mode["degenerate_single_token_query"]
        self.assertTrue(cases)
        for case in cases:
            self.assertTrue(
                any(len(query.split()) == 1 for query in _queries(case)), case["case_id"]
            )

    def test_the_retired_topic_hardcode_is_preserved_with_its_brief(self) -> None:
        cases = self.by_mode["retired_topic_query_hardcode"]
        self.assertTrue(cases)
        for case in cases:
            self.assertTrue(case["visual_brief_present"], case["case_id"])
            self.assertTrue(case["visual_brief_provider_queries"], case["case_id"])
            self.assertEqual(case["retired_query_class"], "C35")
        recorded = {entry["registry_id"] for entry in self.fixture["retired_query_classes"]}
        self.assertIn("C35", recorded)

    def test_a_query_labelled_with_the_wrong_language_is_preserved(self) -> None:
        """Whether a string is German is not something a test can decide.

        What it can check is the shape the defect left behind: a query that came
        from the hardcode's per-provider list rather than its default list, sent
        to that one provider and recorded as English. The string itself
        (``Die Jagdtechniken von Orcas``) is in the fixture for a human to read.
        """

        cases = self.by_mode["mislabelled_query_language"]
        self.assertTrue(cases)
        for case in cases:
            brief = case["visual_brief_provider_queries"]
            default = {str(query) for query in brief.get("default") or []}
            per_provider = {
                str(query)
                for provider, queries in brief.items()
                if provider != "default"
                for query in queries
            }
            self.assertTrue(per_provider, case["case_id"])
            overrides = [
                attempt
                for attempt in case["historical_provider_attempts"]
                if attempt["query"] in per_provider - default
                and attempt["query_language"] == "en"
            ]
            self.assertTrue(overrides, case["case_id"])

    def test_every_declared_mode_is_actually_demonstrated(self) -> None:
        for mode, cases in self.by_mode.items():
            self.assertTrue(cases, f"{mode} is in the vocabulary but nothing demonstrates it")

    def test_the_extraction_defect_is_preserved_as_the_scene_declared_it(self) -> None:
        cases = self.by_mode["garbage_subject_extraction"]
        self.assertTrue(cases)
        for case in cases:
            declared = case["historical_semantic_scene"]
            self.assertTrue(declared.get("subject") or declared.get("action"), case["case_id"])
            asked = set(_queries(case))
            self.assertFalse(
                asked & {str(v) for v in declared.get("subject") or []},
                "the query and the declared subject must be shown to differ",
            )


class CompactionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = load_historical_evidence()

    def test_nothing_was_dropped_silently(self) -> None:
        preserved = {case["scene_key"] for case in self.fixture["cases"]}
        dropped = {entry["scene_key"] for entry in self.fixture["dropped_source_scenes"]}
        self.assertFalse(preserved & dropped)
        self.assertEqual(
            len(preserved) + len(dropped), int(self.fixture["derived_from"]["corpus_scene_count"])
        )
        for entry in self.fixture["dropped_source_scenes"]:
            self.assertTrue(str(entry["reason"]).strip(), entry["scene_key"])

    def test_the_fixture_is_a_fraction_of_what_it_replaced(self) -> None:
        self.assertLess(
            self.fixture["candidate_count"],
            int(self.fixture["derived_from"]["corpus_observation_count"]),
        )
        self.assertLess(HISTORICAL_EVIDENCE_PATH.stat().st_size, 150_000)

    def test_one_representative_frame_per_candidate(self) -> None:
        frames = [
            candidate["representative_frame"]
            for case in self.fixture["cases"]
            for candidate in case["candidates"]
        ]
        self.assertEqual(len(frames), self.fixture["candidate_count"])
        for frame in frames:
            self.assertRegex(str(frame["sha256"]), r"^[0-9a-f]{64}$")
            self.assertTrue(str(frame["local_frame_path"]).startswith("projects/"))

    def test_the_residual_runtime_dependency_is_enumerable(self) -> None:
        """What PLAN-9D still needs from the runtime tree, as an exact list."""

        paths = historical_runtime_paths(self.fixture)
        self.assertTrue(all(path.startswith("projects/") for path in paths))
        self.assertEqual(
            len(paths),
            2 * self.fixture["case_count"] + self.fixture["frame_count"],
        )

    def test_the_case_table_and_the_frozen_fixture_agree(self) -> None:
        self.assertEqual(
            [case["case_id"] for case in self.fixture["cases"]],
            [spec["case_id"] for spec in HISTORICAL_CASES],
        )
        self.assertEqual(
            {entry["registry_id"] for entry in RETIRED_QUERY_CLASSES},
            {entry["registry_id"] for entry in self.fixture["retired_query_classes"]},
        )


class CurationRulesTests(unittest.TestCase):
    """The curation rules stay testable once the runtime tree is gone."""

    def _source_corpus(self) -> dict:
        scenes = []
        for index, spec in enumerate(HISTORICAL_CASES):
            scenes.append(
                {
                    "scene_key": f"{spec['project']}/{spec['scene_id']}",
                    "scene_text": f"text {index}",
                    "semantic_scene": {"subject": [], "action": []},
                    "candidates": [
                        {
                            "blind_id": "C1",
                            "asset_id": f"asset_{index}_a",
                            "input_order": 0,
                            "frames": [
                                {
                                    "local_frame_path": f"projects/p/{index}/a/frame_001.jpg",
                                    "sha256": "a" * 64,
                                    "width": 1,
                                    "height": 2,
                                    "frame_index": 1,
                                },
                                {
                                    "local_frame_path": f"projects/p/{index}/a/frame_000.jpg",
                                    "sha256": "b" * 64,
                                    "width": 1,
                                    "height": 2,
                                    "frame_index": 0,
                                },
                            ],
                            "candidate": {"asset_id": f"asset_{index}_a", "provider": "pexels"},
                        },
                        {
                            "blind_id": "C2",
                            "asset_id": f"asset_{index}_b",
                            "input_order": 1,
                            "frames": [
                                {
                                    "local_frame_path": f"projects/p/{index}/b/frame_000.jpg",
                                    "sha256": "c" * 64,
                                    "width": 1,
                                    "height": 2,
                                    "frame_index": 0,
                                }
                            ],
                            "candidate": {"asset_id": f"asset_{index}_b", "provider": "pexels"},
                        },
                    ],
                }
            )
        scenes.append(
            {
                "scene_key": "unrelated/scene_999",
                "scene_text": "dropped",
                "semantic_scene": {},
                "candidates": [
                    {
                        "blind_id": "C1",
                        "asset_id": "drop_a",
                        "input_order": 0,
                        "frames": [],
                        "candidate": {
                            "asset_id": "drop_a",
                            "provider": "pexels",
                            "search_query": RETIRED_BROAD_LITERAL,
                        },
                    },
                    {
                        "blind_id": "C2",
                        "asset_id": "drop_b",
                        "input_order": 1,
                        "frames": [],
                        "candidate": {
                            "asset_id": "drop_b",
                            "provider": "pexels",
                            "search_query": "something else entirely",
                        },
                    },
                ],
            }
        )
        return {
            "corpus_version": "synthetic",
            "corpus_sha256": "f" * 64,
            "scene_count": len(scenes),
            "observation_count": sum(len(s["candidates"]) for s in scenes),
            "scenes": scenes,
        }

    def _reader(self, project: str, scene_id: str) -> dict:
        return {
            "scene_id": scene_id,
            "primary_query": RETIRED_BROAD_LITERAL,
            "queries": [{"kind": "exact", "fallback_level": 1, "query": "q"}],
            "provider_attempts": [
                {"provider": "pexels", "query": RETIRED_BROAD_LITERAL, "result_count": 5},
                {"provider": "pexels", "query": RETIRED_BROAD_LITERAL, "result_count": 5},
            ],
            "visual_brief": None,
            "selected_asset": {"asset_id": "whatever"},
        }

    def test_curation_is_a_pure_function_of_its_input(self) -> None:
        first = curate_historical_evidence(self._source_corpus(), manifest_reader=self._reader)
        second = curate_historical_evidence(self._source_corpus(), manifest_reader=self._reader)
        for fixture in (first, second):
            fixture.pop("built_at_utc")
            fixture.pop("fixture_sha256")
        self.assertEqual(first, second)

    def test_repeated_provider_attempts_collapse_but_distinct_ones_do_not(self) -> None:
        fixture = curate_historical_evidence(self._source_corpus(), manifest_reader=self._reader)
        for case in fixture["cases"]:
            self.assertEqual(len(case["historical_provider_attempts"]), 1)

    def test_the_lowest_indexed_frame_is_the_representative_one(self) -> None:
        fixture = curate_historical_evidence(self._source_corpus(), manifest_reader=self._reader)
        frame = fixture["cases"][0]["candidates"][0]["representative_frame"]
        self.assertEqual(frame["frame_index"], 0)

    def test_a_dropped_scene_says_whether_its_evidence_was_a_duplicate(self) -> None:
        fixture = curate_historical_evidence(self._source_corpus(), manifest_reader=self._reader)
        dropped = {entry["scene_key"]: entry for entry in fixture["dropped_source_scenes"]}
        self.assertIn("unrelated/scene_999", dropped)
        entry = dropped["unrelated/scene_999"]
        self.assertIn("duplicate_evidence", entry["reason"])
        self.assertEqual(entry["duplicates_preserved_query"], [RETIRED_BROAD_LITERAL])


class OfflineTests(unittest.TestCase):
    def test_reading_the_evidence_opens_no_socket(self) -> None:
        before = len(network_guard.blocked_attempts)
        with network_guard.network_guard_scope():
            fixture = load_historical_evidence()
            historical_runtime_paths(fixture)
        self.assertEqual(len(network_guard.blocked_attempts), before)

    def test_the_generic_harness_names_no_historical_project(self) -> None:
        """The harness has to outlive the runtime data it was once built from."""

        source = (REPO_ROOT / "tests" / "plan9d_ground_truth.py").read_text(encoding="utf-8")
        for case in load_historical_evidence()["cases"]:
            self.assertNotIn(case["source_project"], source, case["case_id"])
            self.assertNotIn(case["source_scene_id"] + "/", source, case["case_id"])

    def test_the_evidence_needs_no_image_bytes(self) -> None:
        """Frames are third-party licensed provider material and stay untracked."""

        fixture = load_historical_evidence()
        validate_historical_evidence(fixture)
        tracked = [
            path
            for path in historical_runtime_paths(fixture)
            if (REPO_ROOT / "tests" / "data" / "plan9d" / Path(path).name).exists()
        ]
        self.assertEqual(tracked, [])


if __name__ == "__main__":
    unittest.main()
