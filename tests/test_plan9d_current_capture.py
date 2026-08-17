"""Locks on the PLAN-9D-B current-HEAD retrieval capture.

The capture is the one part of PLAN-9D allowed to touch a provider, and it runs
once. Everything after it - the retrieval gate, the owner's blind pass, the
metadata baseline, the A/B - reads the frozen file instead. So these tests check
the two things that make that safe.

*That the frozen corpus can answer where it came from.* Which HEAD produced the
pools, when, into which workspace, under which network approval, from which
queries. A corpus that cannot answer those is exactly what PLAN-9D-A found the
retired ``corpus_v1.json`` to be, and the reconciliation exists to stop a second
one appearing.

*That measuring it never becomes a live run.* No test here opens a socket, and
the module proves it rather than promising it: the capture entry point is
exercised under the repository's own socket guard and has to refuse.

Historical evidence and the current capture are kept apart by data, not by
naming, and both directions are locked: the historical fixture cannot pass the
benchmark gate, and a current capture cannot be assembled out of historical
manifests by relabelling anything.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from tests import network_guard
from tests.plan9d_corpus_builder import render_pack, render_review_pack
from tests.plan9d_current_capture import (
    CAPTURE_NETWORK_ACTIONS,
    CAPTURE_PROJECT_ID,
    CAPTURE_WORKSPACE,
    EVALUATION_SCENES,
    CaptureError,
    assert_socket_guard_released,
    capture_corpus,
    capture_statistics,
    check_tripwires,
    finalize,
    scene_categories,
    _unique_pool,
)
from tests.plan9d_ground_truth import (
    CURRENT_ANNOTATIONS_PATH,
    CURRENT_CORPUS_PATH,
    FIXTURE_KIND_CURRENT_BENCHMARK,
    GENERATION_CURRENT,
    LEGACY_BROAD_QUERY_LITERALS,
    STATUS_COMPLETE,
    STATUS_WAITING,
    BenchmarkError,
    annotation_status,
    assert_current_benchmark_input,
    corpus_digest,
    load_annotations,
    load_current_corpus,
    load_historical_evidence,
    secret_like_findings,
    validate_corpus,
    validate_current_capture,
)


REPO_ROOT = Path(__file__).resolve().parents[1]

#: The four simple subject cases PLAN-9D-C names by hand. Kept here so a future
#: edit to the evaluation set cannot quietly drop one of them.
REQUIRED_SIMPLE_SUBJECTS = ("gecko", "hummingbird", "penguin", "orca")

#: Derived fields of the frozen capture that the current decision path no longer
#: produces, scene by scene, with the categories it dropped and added.
#:
#: The corpus stores two kinds of thing: network facts written once (pools,
#: queries, frames) and arithmetic over them (categories, statistics). The second
#: kind is a function of the *code*, so a repair to selection moves it - and the
#: obvious answer, re-running ``finalize`` and committing the result, is the one
#: that cannot be taken: ``corpus_sha256`` would change, and the owner's blind
#: annotations record the hash they were made against
#: (``current_annotations_v1.json``, checked in ``validate_annotations``). A
#: recomputed corpus therefore orphans the only labelled ground truth in this
#: repository, which is a far worse loss than a named drift.
#:
#: Owner decision 2026-08-17, at the closure of package D: name the drift, leave
#: the corpus and the labels untouched. Registry row ``C95`` carries the debt and
#: its exit condition; the honest fix is to take code-derived fields out of the
#: hash so labels bind to captured facts, and that belongs to the instrument
#: (package C), not here.
#:
#: This is a pin, not an allowance. The tests below require the drift to be
#: *exactly* this - a further selection change reddens them again, and a drift
#: that disappears reddens them too, so the entry is dropped by whoever removed
#: it rather than left as scenery.
KNOWN_DERIVED_DRIFT: dict[str, dict[str, tuple[str, ...]]] = {
    # C91 (per-field decidability): the pool stopped being ambiguous because the
    # terms that could not be compared against a glued record can be compared
    # against its fields. No winner changed anywhere in the corpus - measured
    # with ``measure --baseline``: changed_winners 0.
    "plan9d_current_capture_v1/scene_010": {
        "dropped": ("ambiguous_needs_review",),
        "added": (),
    },
}


def _corpus() -> dict:
    return load_current_corpus()


class CorpusPresenceTests(unittest.TestCase):
    """The capture happened, and the file it produced is the one being read."""

    def test_frozen_corpus_is_committed(self) -> None:
        self.assertTrue(
            CURRENT_CORPUS_PATH.is_file(),
            "PLAN-9D-B freezes tests/data/plan9d/current_corpus_v1.json; without it every "
            "later sub-slice has nothing to measure",
        )

    def test_corpus_loads_through_the_generic_validator(self) -> None:
        corpus = _corpus()
        self.assertEqual(corpus["fixture_kind"], FIXTURE_KIND_CURRENT_BENCHMARK)
        self.assertEqual(corpus["generation_class"], GENERATION_CURRENT)


class ProvenanceTests(unittest.TestCase):
    """1, 2: the corpus declares that it is current, and which HEAD produced it."""

    def test_provenance_is_explicit(self) -> None:
        corpus = _corpus()
        validate_current_capture(corpus)
        self.assertEqual(corpus["plan_step"], "PLAN-9D-B")
        self.assertTrue(corpus["capture_timestamp_utc"].endswith("+00:00"))
        self.assertEqual(corpus["capture_workspace"], CAPTURE_WORKSPACE)

    def test_capture_head_sha_is_a_full_commit(self) -> None:
        head = str(_corpus()["capture_head_sha"])
        self.assertEqual(len(head), 40, head)
        self.assertTrue(all(char in "0123456789abcdef" for char in head), head)

    def test_missing_head_sha_is_refused(self) -> None:
        corpus = dict(_corpus())
        corpus["capture_head_sha"] = ""
        with self.assertRaises(BenchmarkError):
            validate_current_capture(corpus)

    def test_short_head_sha_is_refused(self) -> None:
        corpus = dict(_corpus())
        corpus["capture_head_sha"] = "d01914d"
        with self.assertRaises(BenchmarkError):
            validate_current_capture(corpus)

    def test_network_approval_is_recorded_and_excludes_asset_download(self) -> None:
        network = _corpus()["network"]
        self.assertEqual(sorted(network["approved_actions"]), sorted(CAPTURE_NETWORK_ACTIONS))
        self.assertNotIn("asset_download", network["approved_actions"])
        self.assertFalse(network["asset_download_used"])

    def test_a_capture_claiming_an_asset_download_is_refused(self) -> None:
        corpus = json.loads(json.dumps(_corpus()))
        corpus["network"]["asset_download_used"] = True
        with self.assertRaises(BenchmarkError):
            validate_current_capture(corpus)


class HistoricalIsolationTests(unittest.TestCase):
    """3, 4, 7: neither direction of the historical/current boundary is passable."""

    def test_historical_evidence_cannot_pass_the_benchmark_gate(self) -> None:
        fixture = load_historical_evidence()
        with self.assertRaises(BenchmarkError):
            assert_current_benchmark_input(fixture, context="test")
        with self.assertRaises(BenchmarkError):
            validate_current_capture(fixture)

    def test_relabelling_historical_evidence_does_not_make_it_a_capture(self) -> None:
        fixture = json.loads(json.dumps(load_historical_evidence()))
        fixture["fixture_kind"] = FIXTURE_KIND_CURRENT_BENCHMARK
        fixture["generation_class"] = GENERATION_CURRENT
        # The provenance stamp is now a lie, and the shape is still historical:
        # no capture_head_sha, no workspace, no network record, no scenes.
        with self.assertRaises(BenchmarkError):
            validate_current_capture(fixture)

    def test_current_corpus_contains_no_historical_source_project(self) -> None:
        corpus = _corpus()
        historical_projects = {
            str(case["source_project"]) for case in load_historical_evidence()["cases"]
        }
        blob = json.dumps(corpus, ensure_ascii=False)
        for project in historical_projects:
            self.assertNotIn(project, blob, f"historical project {project!r} leaked into the capture")
        for scene in corpus["scenes"]:
            self.assertEqual(scene["project"], CAPTURE_PROJECT_ID)

    def test_no_historical_query_seeded_the_capture(self) -> None:
        corpus = _corpus()
        historical_queries = {
            " ".join(str(attempt["query"]).casefold().split())
            for case in load_historical_evidence()["cases"]
            for attempt in case["historical_provider_attempts"]
            if str(attempt["query"]).strip()
        }
        captured = {
            " ".join(str(attempt["query"]).casefold().split())
            for scene in corpus["scenes"]
            for attempt in scene["provider_attempts"]
            if str(attempt.get("query") or "").strip()
        }
        self.assertEqual(sorted(captured & historical_queries), [])

    def test_no_retired_broad_literal_reached_a_provider(self) -> None:
        for scene in _corpus()["scenes"]:
            for attempt in scene["provider_attempts"]:
                query = " ".join(str(attempt.get("query") or "").casefold().split())
                self.assertNotIn(query, LEGACY_BROAD_QUERY_LITERALS, scene["scene_key"])

    def test_a_capture_carrying_a_retired_literal_is_refused(self) -> None:
        corpus = json.loads(json.dumps(_corpus()))
        corpus["scenes"][0]["query_plan"]["queries"].append(
            {"provider": "pexels", "query": "nature science wildlife observation", "status": "ok"}
        )
        with self.assertRaises(BenchmarkError):
            validate_current_capture(corpus)


class FrozenDigestTests(unittest.TestCase):
    """5: the corpus is frozen, and the freeze is checkable rather than asserted."""

    def test_recorded_digest_matches_the_content(self) -> None:
        corpus = _corpus()
        self.assertEqual(corpus["corpus_sha256"], corpus_digest(corpus))

    def test_digest_is_stable_across_reloads(self) -> None:
        self.assertEqual(corpus_digest(_corpus()), corpus_digest(_corpus()))

    def test_any_edit_breaks_the_digest(self) -> None:
        corpus = json.loads(json.dumps(_corpus()))
        corpus["scenes"][0]["scene_text"] += " "
        with self.assertRaises(BenchmarkError):
            validate_corpus(corpus)


class OfflineTests(unittest.TestCase):
    """6: measuring the corpus is a pure function of a file on disk."""

    def test_capture_refuses_to_run_under_the_socket_guard(self) -> None:
        with network_guard.network_guard_scope():
            with self.assertRaises(CaptureError):
                assert_socket_guard_released()
            with self.assertRaises(CaptureError):
                capture_corpus(granted_by="test")

    def test_reading_the_corpus_opens_no_socket(self) -> None:
        with network_guard.network_guard_scope():
            corpus = _corpus()
            validate_current_capture(corpus)
            capture_statistics(corpus["scenes"])
            render_review_pack(corpus)

    def test_the_corpus_carries_no_vision_evidence(self) -> None:
        for scene in _corpus()["scenes"]:
            for candidate in scene["candidates"]:
                self.assertFalse(candidate["candidate"].get("vision_tags"))


class WorkspaceTests(unittest.TestCase):
    """8: every frame the corpus points at belongs to this capture."""

    def test_frames_live_in_the_capture_workspace(self) -> None:
        frames = 0
        for scene in _corpus()["scenes"]:
            for candidate in scene["candidates"]:
                for frame in candidate["frames"]:
                    frames += 1
                    self.assertTrue(
                        str(frame["local_frame_path"]).startswith(f"{CAPTURE_WORKSPACE}/"),
                        frame["local_frame_path"],
                    )
                    self.assertTrue(frame["sha256"])
        self.assertGreater(frames, 0, "a capture with no frame evidence cannot be reviewed")

    def test_a_frame_outside_the_workspace_is_refused(self) -> None:
        corpus = json.loads(json.dumps(_corpus()))
        for scene in corpus["scenes"]:
            for candidate in scene["candidates"]:
                if candidate["frames"]:
                    candidate["frames"][0]["local_frame_path"] = (
                        "projects/2026-07-28_pochemu-kosatki/assets/previews/f.jpg"
                    )
                    break
            else:
                continue
            break
        with self.assertRaises(BenchmarkError):
            validate_current_capture(corpus)

    def test_the_workspace_is_not_tracked_by_git(self) -> None:
        gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        self.assertIn("/projects/", gitignore)
        self.assertTrue(CAPTURE_WORKSPACE.startswith("projects/"))


class SecretTests(unittest.TestCase):
    """9: a credential cannot reach the frozen file, and the check has teeth."""

    def test_no_secret_like_value_is_persisted(self) -> None:
        self.assertEqual(secret_like_findings(_corpus()), [])

    def test_a_credential_shaped_url_is_detected(self) -> None:
        findings = secret_like_findings({"preview": {"url": "https://example.test/v?key=abc123"}})
        self.assertEqual(len(findings), 1)
        self.assertNotIn("abc123", findings[0])

    def test_a_credential_named_field_is_detected(self) -> None:
        self.assertTrue(secret_like_findings({"api_key": "x"}))

    def test_an_authorization_header_value_is_detected(self) -> None:
        self.assertTrue(secret_like_findings({"h": "Authorization: Bearer abcdefghijklmnop"}))

    def test_provider_prose_is_not_a_finding(self) -> None:
        """A catalogue entry may say "authorization" and mean the word.

        The first capture attempt aborted on exactly this: a provider description
        and the approval note both mentioned a marker word, and a scan that stops
        a run over prose is a scan that gets switched off.
        """

        self.assertEqual(
            secret_like_findings(
                {
                    "description": "Congressional authorization for the launch, 1969",
                    "granted_by": "owner (PLAN-9D-B bounded capture approval)",
                    "title": "The secret life of pangolins",
                }
            ),
            [],
        )


class AnnotationTests(unittest.TestCase):
    """10: PLAN-9D-B prepares for the owner's pass and never performs it.

    The owner's pass has since happened (PLAN-9D-D, 2026-08-12), so the absence
    of the file can no longer stand in for "the capture did not write it". The
    claim itself is unchanged and still locked, only its evidence had to move:
    the label is a separate artifact, signed by a named human and bound by hash
    to the frozen corpus, and the capture payload carries no owner vocabulary at
    all - which is what would actually be violated if PLAN-9D-B ever answered
    the human question for itself.
    """

    def test_the_annotation_is_a_separate_owner_artifact(self) -> None:
        annotations = load_annotations()
        self.assertTrue(str(annotations.get("annotator") or "").strip())
        self.assertIs(True, annotations.get("blind"))
        self.assertEqual(_corpus()["corpus_sha256"], annotations["corpus_sha256"])

    def test_annotation_status_follows_the_owner_file_not_the_capture(self) -> None:
        """Only the owner's file moves this needle, and its absence is honest."""

        self.assertEqual(STATUS_COMPLETE, annotation_status())
        self.assertEqual(
            STATUS_WAITING,
            annotation_status(CURRENT_ANNOTATIONS_PATH.with_name("no_such_annotations.json")),
        )

    def test_the_capture_carries_no_owner_label(self) -> None:
        blob = json.dumps(_corpus(), ensure_ascii=False)
        for key in ("preferred_candidate", "unacceptable_candidates", "annotator"):
            self.assertNotIn(f'"{key}"', blob)

    def test_the_annotation_template_is_available_but_empty(self) -> None:
        from tests.plan9d_corpus_builder import annotation_template

        template = annotation_template(_corpus())
        self.assertEqual(template["status"], STATUS_WAITING)
        self.assertEqual(template["annotator"], "")
        self.assertTrue(all(not scene["preferred_candidate"] for scene in template["scenes"]))


class DuplicationTests(unittest.TestCase):
    """11, 12: repetition is measured; the builder invents no cross-scene sharing."""

    def test_within_scene_repeats_are_counted_not_rewritten(self) -> None:
        pool, repeats = _unique_pool(
            [
                {"asset_id": "a", "search_query": "one"},
                {"asset_id": "b", "search_query": "one"},
                {"asset_id": "a", "search_query": "two"},
            ]
        )
        self.assertEqual([item["asset_id"] for item in pool], ["a", "b"])
        self.assertEqual(repeats["a"]["count"], 2)
        self.assertEqual(repeats["a"]["queries"], ["one", "two"])

    def test_recorded_repeat_counts_match_the_statistics(self) -> None:
        corpus = _corpus()
        recomputed = capture_statistics(corpus["scenes"])
        self.assertEqual(
            recomputed["unique_asset_count"], corpus["capture_statistics"]["unique_asset_count"]
        )
        self.assertEqual(
            recomputed["cross_scene_intersections"],
            corpus["capture_statistics"]["cross_scene_intersections"],
        )

    def test_each_scene_stores_one_record_per_asset(self) -> None:
        for scene in _corpus()["scenes"]:
            ids = [str(item["asset_id"]) for item in scene["candidates"]]
            self.assertEqual(len(ids), len(set(ids)), scene["scene_key"])

    def test_cross_scene_sharing_is_reported_exactly(self) -> None:
        """A shared asset is evidence about retrieval, so it is stated, not hidden.

        The property under test is that the builder does not *create* sharing: an
        intersection exists only where two scenes genuinely both received the same
        asset id from a provider.
        """

        corpus = _corpus()
        by_scene = {
            scene["scene_key"]: {str(item["asset_id"]) for item in scene["candidates"]}
            for scene in corpus["scenes"]
        }
        for entry in corpus["capture_statistics"]["cross_scene_intersections"]:
            left, right = entry["scenes"]
            self.assertEqual(sorted(by_scene[left] & by_scene[right]), entry["shared_asset_ids"])
        reported = {
            tuple(entry["scenes"]) for entry in corpus["capture_statistics"]["cross_scene_intersections"]
        }
        keys = sorted(by_scene)
        for index, left in enumerate(keys):
            for right in keys[index + 1 :]:
                if by_scene[left] & by_scene[right]:
                    self.assertIn((left, right), reported)


class EvaluationSetTests(unittest.TestCase):
    """The set stays the one PLAN-9D-C was promised, and the tripwires still bite."""

    def test_the_four_required_simple_subjects_are_present(self) -> None:
        declared = " ".join(
            str(scene.visual_brief.get("subject") or "").casefold() for scene in EVALUATION_SCENES
        )
        for subject in REQUIRED_SIMPLE_SUBJECTS:
            self.assertIn(subject, declared)

    def test_the_set_is_bounded_and_not_only_wildlife(self) -> None:
        self.assertGreaterEqual(len(EVALUATION_SCENES), 12)
        self.assertLessEqual(len(EVALUATION_SCENES), 16)
        non_wildlife = [
            scene for scene in EVALUATION_SCENES if "non_wildlife_subject" in scene.coverage
        ]
        self.assertGreaterEqual(len(non_wildlife), 1)

    def test_no_scene_hands_the_planner_a_ready_made_query(self) -> None:
        for scene in EVALUATION_SCENES:
            self.assertNotIn("provider_queries", scene.visual_brief, scene.case_id)
            self.assertNotIn("source_class", scene.visual_brief, scene.case_id)

    def test_a_lost_subject_trips_the_wire(self) -> None:
        entry = {
            "scene_id": "scene_001",
            "declared_brief": {"subject": "gecko"},
            "visual_brief": {"subject": "gecko"},
            "semantic_scene": {"subject": ["gecko"]},
            "executable_queries": [
                {"provider": "pexels", "query": "smooth glass surface", "language": "en"}
            ],
        }
        tripwires = {item["tripwire"] for item in check_tripwires([entry])}
        self.assertIn("subject_absent_from_provider_query", tripwires)

    def test_a_retired_literal_trips_the_wire(self) -> None:
        entry = {
            "scene_id": "scene_001",
            "declared_brief": {"subject": "gecko"},
            "visual_brief": {"subject": "gecko"},
            "semantic_scene": {"subject": ["gecko"]},
            "executable_queries": [
                {"provider": "pexels", "query": "gecko", "language": "en"},
                {"provider": "pexels", "query": "nature science wildlife observation", "language": "en"},
            ],
        }
        tripwires = {item["tripwire"] for item in check_tripwires([entry])}
        self.assertIn("retired_broad_query_literal", tripwires)

    def test_a_missing_brief_trips_the_wire(self) -> None:
        entry = {
            "scene_id": "scene_001",
            "declared_brief": {"subject": "gecko"},
            "visual_brief": {},
            "semantic_scene": {"subject": []},
            "executable_queries": [],
        }
        tripwires = {item["tripwire"] for item in check_tripwires([entry])}
        self.assertEqual(
            tripwires,
            {"scene_without_visual_brief", "empty_semantic_subject", "no_provider_ready_query"},
        )


class LineageTests(unittest.TestCase):
    """Every captured scene can be traced from requirement to candidate."""

    def test_each_scene_records_the_whole_chain(self) -> None:
        for scene in _corpus()["scenes"]:
            self.assertTrue(scene["scene_text"], scene["scene_key"])
            self.assertTrue(scene["visual_brief"], scene["scene_key"])
            self.assertTrue(scene["semantic_scene"]["subject"], scene["scene_key"])
            self.assertTrue(scene["query_plan"]["queries"], scene["scene_key"])
            self.assertTrue(scene["routing"]["ordered_providers"], scene["scene_key"])
            self.assertTrue(scene["provider_attempts"], scene["scene_key"])
            self.assertGreaterEqual(len(scene["candidates"]), 2, scene["scene_key"])

    def test_every_candidate_names_its_provider_and_query(self) -> None:
        for scene in _corpus()["scenes"]:
            attempted = {str(item["provider"]) for item in scene["provider_attempts"]}
            for candidate in scene["candidates"]:
                self.assertTrue(candidate["provider"], candidate["asset_id"])
                self.assertIn(candidate["provider"], attempted | {"local_library"})
                self.assertTrue(candidate["search_query"], candidate["asset_id"])

    def test_rights_are_recorded_for_every_candidate(self) -> None:
        for scene in _corpus()["scenes"]:
            for candidate in scene["candidates"]:
                rights = candidate["rights"]
                self.assertTrue(rights["rights_status"], candidate["asset_id"])
                self.assertIn("allowed_for_render", rights)
                self.assertIn("review_required", rights)

    def test_the_four_simple_subject_scenes_reached_a_provider(self) -> None:
        corpus = _corpus()
        cases = {scene["case_id"]: scene for scene in corpus["scenes"]}
        for subject in REQUIRED_SIMPLE_SUBJECTS:
            case = next((key for key in cases if subject in key), "")
            self.assertTrue(case, f"no captured scene for {subject}")
            attempts = cases[case]["provider_attempts"]
            self.assertTrue(any(item["status"] == "completed" for item in attempts), case)


class DerivedFieldTests(unittest.TestCase):
    """The corpus's arithmetic is recomputable from the corpus, and it was.

    PLAN-9D-A moved the benchmark-corpus acceptance conditions - size, technical
    category coverage, ``regression_capable`` scenes, declared-versus-preview
    dimensions and a checksum per frame - onto PLAN-9D-B and PLAN-9D-C, to be
    checked on really captured data instead of on synthetic. This is that check.
    """

    def test_finalize_is_idempotent(self) -> None:
        """Running it twice says the same thing as running it once.

        This is idempotence of the function, and it holds whatever the decision
        path currently answers. Until 2026-08-17 the same name asserted something
        else - that the *stored file* equals its own recomputation - which is a
        claim about the file being up to date with the code, not about
        ``finalize``. The two were separated when a repair moved a derived field
        and took the second claim down with it; the second is now its own test
        below, with the drift named.
        """
        once = finalize(_corpus())
        twice = finalize(once)
        self.assertEqual(twice["corpus_sha256"], once["corpus_sha256"])

    def test_the_stored_corpus_still_matches_the_code_apart_from_named_drift(self) -> None:
        """The file is what today's code derives - or differs exactly as recorded.

        With an empty ``KNOWN_DERIVED_DRIFT`` this is the original assertion, hash
        against hash. With entries in it the hash cannot match by construction, so
        the check moves to the categories themselves and requires the difference to
        be neither wider nor narrower than the pin.
        """
        corpus = _corpus()
        if not KNOWN_DERIVED_DRIFT:
            self.assertEqual(finalize(corpus)["corpus_sha256"], corpus["corpus_sha256"])
            return

        measured: dict[str, dict[str, tuple[str, ...]]] = {}
        for scene in corpus["scenes"]:
            stored, now = list(scene["categories"]), scene_categories(scene)
            if stored == now:
                continue
            measured[scene["scene_key"]] = {
                "dropped": tuple(item for item in stored if item not in now),
                "added": tuple(item for item in now if item not in stored),
            }
        self.assertEqual(
            KNOWN_DERIVED_DRIFT,
            measured,
            "the frozen corpus drifted from the code by something other than the pin: "
            "record it in KNOWN_DERIVED_DRIFT with the repair that caused it, or - if a "
            "pinned entry is gone - drop it in the slice that removed it",
        )

    def test_categories_are_recomputable_from_the_stored_pool(self) -> None:
        for scene in _corpus()["scenes"]:
            if scene["scene_key"] in KNOWN_DERIVED_DRIFT:
                continue
            self.assertEqual(scene["categories"], scene_categories(scene), scene["scene_key"])

    def test_the_corpus_covers_more_than_one_technical_category(self) -> None:
        counts = _corpus()["capture_statistics"]["technical_categories"]
        self.assertGreater(len(counts), 1, counts)

    def test_regression_capable_scenes_exist(self) -> None:
        """Without them an A/B can only ever look neutral or better."""

        counts = _corpus()["capture_statistics"]["technical_categories"]
        self.assertGreaterEqual(counts.get("regression_capable", 0), 1, counts)

    def test_declared_versus_preview_dimensions_are_recorded(self) -> None:
        divergence = _corpus()["capture_statistics"]["declared_vs_preview_dimension_divergence"]
        self.assertEqual(
            sorted(divergence), ["differs", "not_comparable", "same"]
        )
        self.assertEqual(
            sum(divergence.values()),
            sum(len(scene["candidates"]) for scene in _corpus()["scenes"]),
        )

    def test_every_frame_carries_a_checksum(self) -> None:
        for scene in _corpus()["scenes"]:
            for candidate in scene["candidates"]:
                for frame in candidate["frames"]:
                    self.assertEqual(len(frame["sha256"]), 64, frame["local_frame_path"])


class ReviewPackTests(unittest.TestCase):
    """The PLAN-9D-C pack is review material, and cannot become an annotation pass."""

    def test_the_pack_hides_the_answer(self) -> None:
        corpus = _corpus()
        html = render_review_pack(corpus)
        lowered = html.casefold()
        # Nothing may say which candidate the ranker chose, and nothing may name a
        # provider, a title or a licence: those are what a reviewer would read
        # instead of the picture.
        self.assertNotIn("selected", lowered)
        # The page's own disclaimer names Vision to say it is absent, so the check
        # is for the evidence field, not for the word.
        self.assertNotIn("vision_tags", lowered)
        self.assertNotIn("semantic_match", lowered)
        for scene in corpus["scenes"][:3]:
            for candidate in scene["candidates"]:
                self.assertNotIn(str(candidate["asset_id"]), html)
                if candidate["provider"]:
                    self.assertNotIn(candidate["provider"], lowered)
                title = str(candidate["candidate"].get("title") or "").strip()
                if len(title) > 12:
                    self.assertNotIn(title, html)

    def test_the_pack_collects_nothing(self) -> None:
        html = render_review_pack(_corpus())
        for control in ("<select", "<textarea", "<input", "<button", "annotations_v1.json"):
            self.assertNotIn(control, html)

    def test_the_pack_shows_the_requirement_and_the_frames(self) -> None:
        corpus = _corpus()
        html = render_review_pack(corpus)
        first = corpus["scenes"][0]
        self.assertIn(first["scene_text"][:40], html)
        self.assertIn("data-blind='C1'", html)
        self.assertIn("<img", html)

    def test_the_pack_refuses_historical_evidence(self) -> None:
        with self.assertRaises(BenchmarkError):
            render_review_pack(load_historical_evidence())

    def test_the_annotation_pack_is_a_different_page(self) -> None:
        """``pack`` still exists for PLAN-9D-D and still asks for a label."""

        html = render_pack(_corpus())
        self.assertIn("data-best", html)
        self.assertNotIn("data-best", render_review_pack(_corpus()))


if __name__ == "__main__":  # pragma: no cover - convenience
    unittest.main()
