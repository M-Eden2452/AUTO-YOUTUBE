"""Locks on the generic PLAN-9D benchmark harness.

These tests guard the properties the benchmark's value rests on: the ground
truth is human and frozen, the annotator was blind, the measurement consumes
those annotations instead of producing them, a fixture backend can never be
mistaken for evidence of visual quality, and - added by PLAN-9D-A - historical
evidence can never be measured as if it described current retrieval.

They run on a corpus this module builds, not on a frozen one. That is the point:
after the 2026-08-08 reconciliation the only admissible benchmark input is the
capture PLAN-9D-B takes from the current production retrieval path, and it does
not exist yet. A synthetic corpus proves the *harness* behaves; it proves
nothing about visual quality and never claims to.

What moved out with the historical corpus, and where it goes
------------------------------------------------------------
The previous version of this file asserted properties of the 16-scene harvest
from ``projects/`` - corpus size, technical category coverage, the presence of
regression-capable scenes, declared-versus-preview dimensions, a frame checksum
for every observation. Those are requirements on a *benchmark* corpus, and they
stop being checkable the moment the benchmark input is the one thing that does
not exist yet. They are not dropped: they are the acceptance conditions of the
current capture (PLAN-9D-B) and of the retrieval quality gate (PLAN-9D-C), to be
asserted there against real captured data rather than re-asserted here against a
corpus this module made up.

Historical failure evidence has its own locks in
``tests/test_plan9d_historical_evidence.py``.
"""

from __future__ import annotations

import hashlib
import json
import unittest
from dataclasses import replace
from typing import Any

from tests.plan9d_corpus_builder import annotation_template, render_pack
from tests.plan9d_ground_truth import (
    ARM_METADATA_ONLY,
    BLINDED_CANDIDATE_KEYS,
    CANDIDATE_FLAG_SPEC,
    CORPUS_SCHEMA_VERSION,
    CURRENT_ANNOTATIONS_PATH,
    CURRENT_CORPUS_PATH,
    FIXTURE_KIND_CURRENT_BENCHMARK,
    FIXTURE_KIND_HISTORICAL_CORPUS,
    FIXTURE_KIND_HISTORICAL_EVIDENCE,
    GENERATION_CURRENT,
    GENERATION_HISTORICAL,
    PREFERENCE_NONE_ACCEPTABLE,
    STATUS_COMPLETE,
    STATUS_WAITING,
    BenchmarkError,
    annotation_status,
    annotations_are_complete,
    assert_admissible_evidence,
    assert_current_benchmark_input,
    assign_blind_ids,
    compare_arms,
    corpus_digest,
    evaluate_arm,
    fixture_kind_of,
    generation_class_of,
    load_annotations,
    load_current_corpus,
    run_metadata_baseline,
    validate_annotations,
    validate_corpus,
)


def _preview_key(asset_id: str) -> str:
    return hashlib.sha256(f"synthetic-preview|{asset_id}".encode("utf-8")).hexdigest()


def _candidate(asset_id: str, **overrides: Any) -> dict[str, Any]:
    record: dict[str, Any] = {
        "asset_id": asset_id,
        "provider": "pexels",
        "provider_asset_id": asset_id,
        "media_type": "video",
        "title": "gecko climbing smooth glass",
        "tags": ["gecko", "glass", "climbing"],
        "width": 1080,
        "height": 1920,
        "duration_sec": 8.0,
        "rights_status": "licensed",
        "license_name": "Pexels License",
        "allowed_for_render": True,
        "review_required": False,
        "vision_tags": [],
    }
    record.update(overrides)
    return record


def _scene(scene_key: str, candidates: list[dict[str, Any]], **overrides: Any) -> dict[str, Any]:
    """One corpus scene, stored blind and fed in manifest order.

    ``input_order`` is deliberately the reverse of the blind order, so every test
    that depends on tie-breaking is also proving that the blind identifier is not
    quietly deciding the answer.
    """

    blind = assign_blind_ids(scene_key, [c["asset_id"] for c in candidates])
    entries = [
        {
            "blind_id": blind[c["asset_id"]],
            "asset_id": c["asset_id"],
            "input_order": len(candidates) - int(blind[c["asset_id"]][1:]),
            # Shaped like the real cache: a content-addressed directory, so the
            # pack cannot leak the asset id through the picture's own URL.
            "frames": [
                {
                    "local_frame_path": (
                        f"projects/synthetic/assets/previews/{_preview_key(c['asset_id'])}/frame_000.jpg"
                    ),
                    "sha256": _preview_key(c["asset_id"]),
                    "width": 360,
                    "height": 640,
                    "frame_index": 0,
                }
            ],
            "candidate": c,
        }
        for c in candidates
    ]
    entries.sort(key=lambda entry: int(entry["blind_id"][1:]))
    scene = {
        "scene_key": scene_key,
        "project": "synthetic",
        "scene_id": scene_key.split("/")[-1],
        "scene_text": f"synthetic scene {scene_key}",
        "semantic_scene": {
            "scene_id": scene_key.split("/")[-1],
            "subject": ["gecko"],
            "action": ["climbing"],
            "environment": ["glass"],
            "visual_priority": "exact_subject",
        },
        "required_duration_sec": 5.0,
        "source_class": "generic_broll",
        "require_provider_metadata": False,
        "prefer_video": True,
        "target_aspect_ratio": "9:16",
        "categories": ["subject_mismatch_risk"],
        "candidates": entries,
    }
    scene.update(overrides)
    return scene


def _current_corpus() -> dict[str, Any]:
    """A frozen corpus shaped exactly like the one PLAN-9D-B will capture.

    Three scenes, because three properties have to be exercised: an ordinary
    selection, an abstention with a recorded blocking reason, and a tie whose
    only tie-break is the manifest order.
    """

    blocked = {
        "rights_status": "legacy_unknown",
        "allowed_for_render": False,
        "review_required": True,
    }
    corpus: dict[str, Any] = {
        "schema_version": CORPUS_SCHEMA_VERSION,
        "fixture_kind": FIXTURE_KIND_CURRENT_BENCHMARK,
        "generation_class": GENERATION_CURRENT,
        "corpus_version": "synthetic-harness-corpus",
        "built_at_utc": "2026-08-08T00:00:00+00:00",
        "plan_step": "PLAN-9D-A",
        "source": "synthetic; built by the harness locks, never committed",
        "scene_count": 3,
        "scenes": [
            _scene("synthetic/scene_selects", [_candidate("sel_a"), _candidate("sel_b")]),
            _scene(
                "synthetic/scene_abstains",
                [_candidate("blk_a", **blocked), _candidate("blk_b", **blocked)],
            ),
            _scene("synthetic/scene_ties", [_candidate("tie_a"), _candidate("tie_b")]),
        ],
        "corpus_sha256": "",
    }
    corpus["observation_count"] = sum(len(s["candidates"]) for s in corpus["scenes"])
    corpus["corpus_sha256"] = corpus_digest(corpus)
    return corpus


def _scene_block(pack: str, scene_key: str) -> str:
    """One scene's markup, so an assertion cannot match a neighbouring card.

    Blind identifiers restart at ``C1`` in every scene, so a whole-page search for
    one would find another scene's candidate and pass for the wrong reason.
    """

    for block in pack.split("<div class='scene'"):
        if f'data-key="{scene_key}"' in block:
            return block
    raise AssertionError(f"scene {scene_key} is not in the pack")


def _pack_save_button(pack: str) -> str:
    """The label the owner actually clicks, isolated from the rest of the page."""

    for block in pack.split("<button"):
        if "save()" in block:
            return block.split("</button>")[0]
    raise AssertionError("the pack has no save button")


def _historical_corpus() -> dict[str, Any]:
    corpus = _current_corpus()
    corpus["fixture_kind"] = FIXTURE_KIND_HISTORICAL_CORPUS
    corpus["generation_class"] = GENERATION_HISTORICAL
    corpus["corpus_sha256"] = ""
    corpus["corpus_sha256"] = corpus_digest(corpus)
    return corpus


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


class CurrentBenchmarkSlotTests(unittest.TestCase):
    """The benchmark slot, as PLAN-9D-B and then PLAN-9D-D filled it.

    This class used to assert that both halves were empty, which was the truth
    while those slices were unstarted. PLAN-9D-B froze a corpus and PLAN-9D-D
    produced the owner's blind labels, so what is worth locking has moved on:
    both files are there, both load through their gates, the labels are bound by
    hash to *this* corpus, and the *absence* path still names the slice that
    owns it - which is what a clean clone or a future re-capture will hit.
    """

    def test_the_current_corpus_is_frozen(self) -> None:
        self.assertTrue(CURRENT_CORPUS_PATH.exists())
        corpus = load_current_corpus()
        self.assertTrue(corpus["scenes"])

    def test_the_owner_annotation_is_frozen_and_bound_to_this_corpus(self) -> None:
        """PLAN-9D-D happened, and it happened against the corpus on disk.

        The labels are only ground truth for the pool the owner was shown, so
        the binding is the load-bearing half: ``corpus_sha256`` matching is what
        stops a later re-capture from silently inheriting an answer given about
        different pictures. ``annotations_are_complete`` is asked for its list of
        problems rather than its verdict, so a failure here names what is wrong.
        """

        self.assertTrue(CURRENT_ANNOTATIONS_PATH.exists())
        annotations = load_annotations()
        corpus = load_current_corpus()
        complete, problems = annotations_are_complete(corpus, annotations)
        self.assertEqual([], problems)
        self.assertTrue(complete)
        self.assertEqual(corpus["corpus_sha256"], annotations["corpus_sha256"])
        self.assertEqual(STATUS_COMPLETE, annotation_status())
        self.assertTrue(str(annotations.get("annotator") or "").strip())
        self.assertIs(True, annotations.get("blind"))

    def test_preview_coverage_is_counted_in_the_units_it_is_quoted_in(self) -> None:
        """Cards and frames are different units, and the prose once mixed them.

        ``render_pack`` documents what a label from it may claim, and that limit
        rests on how little of the pool - and how little of each video - the
        owner actually saw. The docstring said "54 images and 2 videos" against
        a corpus holding 43 image cards and 13 video cards built from 64 frames.
        Locking the counts here keeps the sentence answerable from data instead
        of from memory.
        """

        corpus = load_current_corpus()
        cards: dict[str, int] = {}
        frames: dict[str, int] = {}
        for scene in corpus["scenes"]:
            for entry in scene["candidates"]:
                if not entry["frames"]:
                    continue
                kind = str(entry["candidate"].get("media_type") or "")
                cards[kind] = cards.get(kind, 0) + 1
                frames[kind] = frames.get(kind, 0) + len(entry["frames"])
        self.assertEqual({"image": 43, "video": 13}, cards)
        self.assertEqual({"image": 43, "video": 21}, frames)
        self.assertEqual(56, sum(cards.values()))
        self.assertEqual(64, sum(frames.values()))

        # The load-bearing half of the limit: a video card is one still, not motion.
        video_frame_counts = sorted(
            len(entry["frames"])
            for scene in corpus["scenes"]
            for entry in scene["candidates"]
            if entry["frames"] and entry["candidate"].get("media_type") == "video"
        )
        self.assertEqual([1] * 11 + [5] * 2, video_frame_counts)

    def test_a_missing_annotation_still_reads_as_waiting_not_as_complete(self) -> None:
        """The honest answer to an absent file, kept locked after it stopped being absent."""

        missing = CURRENT_ANNOTATIONS_PATH.with_name("no_such_annotations.json")
        self.assertFalse(missing.exists())
        self.assertEqual(STATUS_WAITING, annotation_status(missing))

    def test_absence_is_reported_with_the_slice_that_owns_it(self) -> None:
        with self.assertRaises(BenchmarkError) as raised:
            load_current_corpus(CURRENT_CORPUS_PATH.with_name("no_such_corpus.json"))
        self.assertIn("PLAN-9D-B", str(raised.exception))


class ProvenanceGateTests(unittest.TestCase):
    """The single gate between historical evidence and a quality measurement."""

    def test_a_current_capture_is_accepted(self) -> None:
        assert_current_benchmark_input(_current_corpus())

    def test_historical_generation_is_refused(self) -> None:
        with self.assertRaises(BenchmarkError) as raised:
            assert_current_benchmark_input(_historical_corpus())
        self.assertIn("historical", str(raised.exception))

    def test_historical_failure_evidence_is_refused(self) -> None:
        with self.assertRaises(BenchmarkError):
            assert_current_benchmark_input(
                {
                    "schema_version": "plan9d-historical-evidence-1",
                    "fixture_kind": FIXTURE_KIND_HISTORICAL_EVIDENCE,
                    "generation_class": GENERATION_HISTORICAL,
                }
            )

    def test_an_unstamped_payload_is_read_as_historical_not_assumed_current(self) -> None:
        """The pre-9D-A corpus declared no provenance, and it was built from projects/."""

        legacy = _current_corpus()
        legacy.pop("fixture_kind")
        legacy.pop("generation_class")
        self.assertEqual(generation_class_of(legacy), GENERATION_HISTORICAL)
        self.assertEqual(fixture_kind_of(legacy), FIXTURE_KIND_HISTORICAL_CORPUS)
        with self.assertRaises(BenchmarkError):
            assert_current_benchmark_input(legacy)

    def test_relabelling_only_one_half_does_not_open_the_gate(self) -> None:
        half = _historical_corpus()
        half["generation_class"] = GENERATION_CURRENT
        with self.assertRaises(BenchmarkError):
            assert_current_benchmark_input(half)
        other = _historical_corpus()
        other["fixture_kind"] = FIXTURE_KIND_CURRENT_BENCHMARK
        with self.assertRaises(BenchmarkError):
            assert_current_benchmark_input(other)


class CorpusContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.corpus = _current_corpus()

    def test_a_current_shaped_corpus_validates(self) -> None:
        validate_corpus(self.corpus)

    def test_a_historical_corpus_never_validates_as_benchmark_input(self) -> None:
        with self.assertRaises(BenchmarkError):
            validate_corpus(_historical_corpus())

    def test_any_edit_changes_the_digest(self) -> None:
        self.corpus["scenes"][0]["scene_text"] += " edited"
        with self.assertRaises(BenchmarkError):
            validate_corpus(self.corpus)

    def test_corpus_is_the_metadata_only_arm(self) -> None:
        for scene in self.corpus["scenes"]:
            for entry in scene["candidates"]:
                self.assertEqual(entry["candidate"].get("vision_tags"), [])

    def test_input_order_is_kept_and_is_not_the_blind_order(self) -> None:
        for scene in self.corpus["scenes"]:
            orders = sorted(int(e["input_order"]) for e in scene["candidates"])
            self.assertEqual(orders, list(range(len(scene["candidates"]))))
            self.assertNotEqual(
                [e["input_order"] for e in scene["candidates"]],
                list(range(len(scene["candidates"]))),
                scene["scene_key"],
            )


class BlindingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.corpus = _current_corpus()

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

    def test_pack_offers_only_candidates_the_annotator_can_see(self) -> None:
        """A candidate with no frame is corpus data, not a question for a human.

        The capture previews a shortlist, so most candidates carry no picture at
        all - in the frozen corpus, 64 frames against 1064 candidates. Rendering
        the rest anyway asked the owner to choose BEST between blind identifiers
        with nothing to look at, and such an answer would say nothing about the
        scene. They stay in the corpus, which is the measured input, and off the
        page, which is the human question.
        """

        corpus = _current_corpus()
        scene = corpus["scenes"][0]
        hidden, *visible = scene["candidates"]
        hidden["frames"] = []
        block = _scene_block(render_pack(corpus), scene["scene_key"])
        self.assertNotIn(f"data-blind='{hidden['blind_id']}'", block)
        self.assertNotIn(f">{hidden['blind_id']}<", block)
        for entry in visible:
            self.assertIn(f"data-blind='{entry['blind_id']}'", block)

    def test_the_pack_saves_under_the_name_the_harness_reads(self) -> None:
        """A label the harness cannot find is a label that was never made.

        The pack is the only producer of the owner's ground truth and
        ``CURRENT_ANNOTATIONS_PATH`` is the only consumer, so the download name
        is a contract between the two rather than a cosmetic string. It drifted
        exactly once and cost a whole blind pass: the button offered
        ``annotations_v1.json`` while the harness read
        ``current_annotations_v1.json``, so a finished annotation sat on disk
        while ``annotation_status`` still answered
        ``WAITING_FOR_OWNER_ANNOTATION`` and nothing downstream would measure.
        """

        pack = render_pack(_current_corpus())
        self.assertIn(f"download='{CURRENT_ANNOTATIONS_PATH.name}'", pack)
        self.assertIn(CURRENT_ANNOTATIONS_PATH.name, _pack_save_button(pack))

    def test_no_pack_is_rendered_for_historical_evidence(self) -> None:
        with self.assertRaises(BenchmarkError):
            render_pack(_historical_corpus())


class AnnotationContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.corpus = _current_corpus()
        self.annotations = annotation_template(self.corpus)

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

    def test_a_fresh_template_is_unlabelled(self) -> None:
        self.assertEqual(self.annotations["status"], STATUS_WAITING)
        complete, problems = annotations_are_complete(self.corpus, self.annotations)
        self.assertFalse(complete)
        self.assertTrue(any("preferred_candidate" in problem for problem in problems))

    def test_no_template_is_offered_for_historical_evidence(self) -> None:
        with self.assertRaises(BenchmarkError):
            annotation_template(_historical_corpus())

    def test_out_of_vocabulary_flag_is_refused(self) -> None:
        first = self.annotations["scenes"][0]
        blind_id = next(iter(first["candidates"]))
        first["candidates"][blind_id]["must_avoid"] = "maybe"
        with self.assertRaises(BenchmarkError):
            validate_annotations(self.annotations)

    def test_preference_must_name_a_candidate_of_that_scene(self) -> None:
        annotations = _complete(self.corpus)
        annotations["scenes"][0]["preferred_candidate"] = "C99"
        complete, problems = annotations_are_complete(self.corpus, annotations)
        self.assertFalse(complete)
        self.assertTrue(any("C99" in problem for problem in problems))

    def test_annotations_are_bound_to_one_corpus(self) -> None:
        annotations = _complete(self.corpus)
        annotations["corpus_sha256"] = "0" * 64
        complete, problems = annotations_are_complete(self.corpus, annotations)
        self.assertFalse(complete)
        self.assertTrue(any("corpus_sha256" in problem for problem in problems))


class MetadataBaselineTests(unittest.TestCase):
    """Wiring, not quality: a synthetic pool cannot say how good a decision is."""

    def setUp(self) -> None:
        self.corpus = _current_corpus()

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

    def test_ties_are_broken_by_the_manifest_order_not_the_blind_id(self) -> None:
        """Guards the defect this harness had: blind order deciding every tie."""

        scene = next(s for s in self.corpus["scenes"] if s["scene_key"] == "synthetic/scene_ties")
        first_fed = min(scene["candidates"], key=lambda entry: int(entry["input_order"]))
        self.assertNotEqual(first_fed["blind_id"], "C1", "the tie test proves nothing this way")
        selected = run_metadata_baseline(self.corpus)["synthetic/scene_ties"]
        self.assertEqual(selected.selected_blind_id, first_fed["blind_id"])

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

    def test_the_decision_owner_is_never_run_on_historical_pools(self) -> None:
        with self.assertRaises(BenchmarkError):
            run_metadata_baseline(_historical_corpus())


class MeasurementTests(unittest.TestCase):
    def setUp(self) -> None:
        self.corpus = _current_corpus()
        self.selections = run_metadata_baseline(self.corpus)
        self.waiting = annotation_template(self.corpus)

    def test_measurement_waits_instead_of_inventing_a_result(self) -> None:
        report = evaluate_arm(self.corpus, self.waiting, self.selections)
        self.assertEqual(report["status"], STATUS_WAITING)
        self.assertEqual(report["scenes"], [])
        self.assertEqual(report["aggregate"], {})
        self.assertTrue(report["blocking"])

    def test_measurement_never_writes_to_the_annotations(self) -> None:
        before = json.dumps(self.waiting, sort_keys=True)
        evaluate_arm(self.corpus, self.waiting, self.selections)
        evaluate_arm(self.corpus, self.waiting, self.selections)
        self.assertEqual(json.dumps(self.waiting, sort_keys=True), before)

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

    def test_a_winner_the_annotator_never_saw_is_unscorable_not_a_mismatch(self) -> None:
        """Disagreement needs both parties to have seen the same thing.

        The capture previews a shortlist, so an arm may win a scene with a
        candidate that carries no frame. The owner could not choose it and did
        not, so ``preferred`` names something else - and counting that as a
        mismatch would measure preview coverage while claiming to measure the
        decision. Such a scene is scored as neither.
        """

        corpus, scene = self.corpus, self.corpus["scenes"][0]
        chosen = str(self.selections[scene["scene_key"]].selected_blind_id or "")
        self.assertTrue(chosen, "this scene has to have a winner for the case to exist")
        for entry in scene["candidates"]:
            if entry["blind_id"] == chosen:
                entry["frames"] = []
        selections = run_metadata_baseline(corpus)
        self.assertEqual(
            selections[scene["scene_key"]].selected_blind_id,
            chosen,
            "a frame is preview material; removing it must not move the decision",
        )
        annotations = _complete(corpus)
        annotations["scenes"][0]["preferred_candidate"] = next(
            e["blind_id"] for e in scene["candidates"] if e["blind_id"] != chosen
        )

        report = evaluate_arm(corpus, annotations, selections)
        row = report["scenes"][0]
        self.assertEqual(row["system_selected"], chosen)
        self.assertFalse(row["system_selected_visible"])
        self.assertTrue(row["unscorable_winner_not_visible"])
        self.assertFalse(row["selection_matches_preferred"])
        aggregate = report["aggregate"]
        self.assertEqual(aggregate["unscorable_winner_not_visible"], 1)
        self.assertEqual(aggregate["scorable_scenes"], aggregate["scenes"] - 1)

    def test_an_unscorable_scene_is_not_reported_as_a_regression(self) -> None:
        """The A/B step must not read preview coverage as a worse decision.

        Two arms over one corpus: the baseline wins the scene with the candidate
        the owner preferred, the candidate arm wins it with one that was never
        previewed. That is not evidence the second arm chose worse, so it is
        neither an improvement nor a regression.
        """

        corpus, scene = self.corpus, self.corpus["scenes"][0]
        key = scene["scene_key"]
        preferred = str(self.selections[key].selected_blind_id or "")
        self.assertTrue(preferred)
        unseen = next(e for e in scene["candidates"] if e["blind_id"] != preferred)
        unseen["frames"] = []
        annotations = _complete(corpus)
        annotations["scenes"][0]["preferred_candidate"] = preferred

        baseline = evaluate_arm(corpus, annotations, self.selections)
        moved = dict(self.selections)
        moved[key] = replace(self.selections[key], selected_blind_id=unseen["blind_id"])
        candidate_arm = evaluate_arm(corpus, annotations, moved)

        self.assertTrue(baseline["scenes"][0]["selection_matches_preferred"])
        self.assertTrue(candidate_arm["scenes"][0]["unscorable_winner_not_visible"])
        verdict = compare_arms(baseline, candidate_arm)
        self.assertNotIn(key, verdict["safe_regressions"])
        self.assertNotIn(key, verdict["blocking_regressions"])
        self.assertNotIn(key, verdict["improvements"])

    def test_no_arm_is_measured_against_historical_evidence(self) -> None:
        historical = _historical_corpus()
        with self.assertRaises(BenchmarkError):
            evaluate_arm(historical, _complete(historical), self.selections)


class FrozenBaselineMeasurementTests(unittest.TestCase):
    """PLAN-9D-E: the metadata-only arm scored against the owner's frozen labels.

    Every input is frozen - the pool by ``corpus_sha256``, the labels by the same
    hash - so this is one fixed number and not a sample of one. Writing it down
    as a test rather than as a paragraph is the point: the result becomes a
    repository fact, and the next change to the decision owner shows up here as
    a diff instead of as a claim someone has to re-derive.

    What this number is *about*. The arm runs today's ``select_best_with_video``
    over the pool captured at ``d01914d7``, so it measures the current decision
    owner, not the decision the capture recorded. Those differ, and deliberately:
    ``388b9b1`` landed after the capture and stopped a video winning by being a
    video. The comparison is locked below because it is the most useful thing
    this ground truth can say today.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.corpus = load_current_corpus()
        cls.annotations = load_annotations()
        cls.result = evaluate_arm(
            cls.corpus, cls.annotations, run_metadata_baseline(cls.corpus)
        )

    def test_the_measurement_runs_instead_of_waiting(self) -> None:
        self.assertEqual(STATUS_COMPLETE, self.result["status"])
        self.assertEqual([], self.result["blocking"])
        self.assertEqual(ARM_METADATA_ONLY, self.result["arm"])
        self.assertEqual(self.corpus["corpus_sha256"], self.result["corpus_sha256"])

    def test_the_baseline_aggregate_is_what_the_frozen_inputs_say(self) -> None:
        self.assertEqual(
            {
                "scenes": 14,
                "scorable_scenes": 14,
                "unscorable_winner_not_visible": 0,
                "preferred_matches": 4,
                "unacceptable_selected": 2,
                "abstentions": 3,
                "correct_abstentions": 0,
                "wrong_abstentions": 3,
                "must_avoid_escaped": 0,
                "non_real_footage_selected": 0,
                "safe_escalations_to_review": 10,
                "auto_safe": 1,
                "undecidable_cases": 0,
            },
            self.result["aggregate"],
        )

    def test_the_failures_are_named_because_an_average_hides_them(self) -> None:
        """Two failure classes, and which scenes they are - PLAN-9D-G needs the names.

        Choosing a candidate the owner struck out is not the same defect as
        choosing nothing where the owner found something acceptable, and the two
        will not be fixed by the same change.
        """

        def scenes_where(field: str) -> list[str]:
            return sorted(
                row["scene_key"].rsplit("/", 1)[-1]
                for row in self.result["scenes"]
                if row[field]
            )

        self.assertEqual(["scene_007", "scene_013"], scenes_where("unacceptable_selected"))
        self.assertEqual(
            ["scene_004", "scene_005", "scene_008"], scenes_where("wrong_abstention")
        )
        self.assertEqual(
            ["scene_003", "scene_009", "scene_012", "scene_014"],
            scenes_where("selection_matches_preferred"),
        )

    def test_the_flag_axes_read_zero_because_they_were_never_filled(self) -> None:
        """Absence of evidence, and it must not be read as evidence of absence.

        ``must_avoid_escaped`` and ``non_real_footage_selected`` are computed
        from the owner's per-candidate flags. The owner filled preference and
        unacceptable marks and left every flag empty, which the contract allows,
        so both counters are structurally zero for this ground truth. A later
        reader - PLAN-9D-G above all - may not turn that into "the baseline
        broke no gate".
        """

        filled = [
            value
            for scene in self.annotations["scenes"]
            for flags in (scene.get("candidates") or {}).values()
            for value in flags.values()
            if str(value or "").strip()
        ]
        self.assertEqual([], filled)
        self.assertEqual(0, self.result["aggregate"]["must_avoid_escaped"])
        self.assertEqual(0, self.result["aggregate"]["non_real_footage_selected"])

    def test_todays_decision_owner_is_measured_against_the_captured_one(self) -> None:
        """The capture's own pick is in the corpus, so the delta is free to state.

        It is the only before/after this ground truth can support without a
        second capture, and it says something specific: the video-first
        substitution PLAN-9D-C found is gone - no winner is unpreviewed any more
        - and agreement doubled, while the two scenes where the system picks
        something the owner struck out survived the change untouched.
        """

        selections = run_metadata_baseline(self.corpus)
        preferred = {
            str(scene["scene_key"]): scene for scene in self.annotations["scenes"]
        }
        captured = {"matches": 0, "unacceptable": 0, "unpreviewed": 0, "abstained": 0}
        arm = {"matches": 0, "unacceptable": 0, "unpreviewed": 0, "abstained": 0}
        for scene in self.corpus["scenes"]:
            key = str(scene["scene_key"])
            entry = preferred[key]
            visible = {c["blind_id"] for c in scene["candidates"] if c["frames"]}
            rejected = set(entry.get("unacceptable_candidates") or [])
            for tally, chosen in (
                (captured, str(scene.get("selected_blind_id") or "") or None),
                (arm, selections[key].selected_blind_id),
            ):
                if chosen is None:
                    tally["abstained"] += 1
                    continue
                tally["matches"] += chosen == entry.get("preferred_candidate")
                tally["unacceptable"] += chosen in rejected
                tally["unpreviewed"] += chosen not in visible

        self.assertEqual(
            {"matches": 2, "unacceptable": 2, "unpreviewed": 3, "abstained": 2}, captured
        )
        self.assertEqual(
            {"matches": 4, "unacceptable": 2, "unpreviewed": 0, "abstained": 3}, arm
        )


class EvidenceAdmissibilityTests(unittest.TestCase):
    def test_fixture_backends_are_refused_as_quality_evidence(self) -> None:
        for source in ("mock", "scripted", "vision:mock", "VISION:Scripted", "fixture", "stub"):
            with self.assertRaises(BenchmarkError, msg=source):
                assert_admissible_evidence("candidate", source)

    def test_real_arms_are_admissible(self) -> None:
        assert_admissible_evidence("baseline", ARM_METADATA_ONLY)
        assert_admissible_evidence("candidate", "vision:openai")

    def test_a_fixture_arm_cannot_be_measured_at_all(self) -> None:
        corpus = _current_corpus()
        with self.assertRaises(BenchmarkError):
            evaluate_arm(
                corpus,
                annotation_template(corpus),
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
            # Every row ``evaluate_arm`` produces declares whether the annotator
            # could see the winner, and ``compare_arms`` indexes it rather than
            # defaulting: a row that does not say is a programming error, not a
            # scorable scene.
            "unscorable_winner_not_visible": False,
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
        corpus = _current_corpus()
        waiting = evaluate_arm(corpus, annotation_template(corpus), run_metadata_baseline(corpus))
        self.assertEqual(compare_arms(waiting, self._arm("b"))["status"], STATUS_WAITING)


if __name__ == "__main__":
    unittest.main()
