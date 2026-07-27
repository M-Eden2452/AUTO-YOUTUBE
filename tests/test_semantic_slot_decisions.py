"""Stage Q2.2A-2: a scene has several requirements, and all of them are judged.

The Q2.1 retest produced three false accepts. The first - a photograph of Mars for a
statistic - was closed by stage Q2.2A through the ``data_infographic`` isolation. The
other two passed honestly on metadata and are the reason this file exists:

- a NASA press-day photograph whose description contains "mass spectrometer" answered
  an ordinary laboratory scene, because one matching term out of a long and otherwise
  unrelated description was enough;
- a clip of the B-15A iceberg breaking off answered a scene about a research station
  and airborne transport, because both the scene and the clip say "Antarctica".

Neither is a scoring bug: a single averaged number cannot say *which* requirement was
met. Every test below pins one requirement of the slot decision, the support status it
produces, or the record's survival from ranking to the manifest and the review board.

Nothing here touches the network, a provider API, a download, TTS or a render. The
regression fixture is written out by hand rather than copied from the user's projects,
so it survives those projects being changed or deleted.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.assets.review_bundle import create_scene_review_bundle, write_review_bundle
from src.assets.semantic_selection import analyze_scene, rank_candidates, select_best_candidate
from src.assets.semantic_selection.decision import (
    DECISION_KEY,
    FRAMING_CROP_REVIEW,
    FRAMING_LOW_RESOLUTION,
    FRAMING_REJECTED,
    FRAMING_VERTICAL_READY,
    NEEDS_ADDITIONAL_ASSET,
    NEEDS_CROP_REVIEW,
    SUPPORT_FULL,
    SUPPORT_MANUAL,
    SUPPORT_PARTIAL,
    SUPPORT_UNSUPPORTED,
    SelectionDecision,
    read_decision,
    validate_decision,
)
from src.assets.scene_strategy import build_strategy
from src.content.visual_planning.brief import apply_brief, parse_brief
from src.news.asset_manager import _ensure_selected_asset_downloaded, build_assets_manifest
from src.news.visual_plan import build_visual_plan

PROVIDERS = ["local_library", "pexels", "pixabay", "wikimedia", "nasa_images", "internet_archive"]


# --- The offline regression fixture ------------------------------------------
# Five scenes, each with the brief its author would write, and the candidate the real
# run either accepted wrongly or would accept rightly. Titles and descriptions are the
# kind of text the named providers really return.
FIXTURE_SCENES: dict[str, dict] = {
    "mass_spectrometry": {
        "scene_id": "scene_006",
        "narration": "Обнаружить настолько маленькие частицы удалось новым методом масс-спектрометрии.",
        "target_duration_sec": 7.92,
        "visual_brief": {
            "subject": "mass spectrometer",
            "action": "sample analysis",
            "place": "laboratory",
            "exact_entities": ["mass spectrometer"],
            "must_include": ["spectrometer"],
            "must_avoid": ["letter tiles", "beauty salon"],
            # The scene wants an ordinary analytical laboratory. Material that is
            # explicitly a planetary mission is not that, and the author says so here
            # instead of the pipeline inventing a rule about Mars.
            "conflicting_context": ["mars mission", "spacecraft", "planetary mission"],
            "source_class": "scientific_equipment",
        },
    },
    "antarctic_station": {
        "scene_id": "scene_007",
        "narration": "Пластик оставили станции или он прилетел по воздуху?",
        "target_duration_sec": 8.99,
        "visual_brief": {
            "subject": "antarctic research station",
            "place": "Antarctica",
            "context": ["wind", "atmospheric transport"],
            "exact_entities": ["Antarctica"],
            "must_include": ["antarctic"],
            "must_avoid": ["protest sign", "household waste"],
            "source_class": "exact_location",
        },
    },
    "plastic_types": {
        "scene_id": "scene_005",
        "narration": "Среди частиц были полиэтилен, ПЭТ, полистирол, ПВХ и следы износа шин.",
        "target_duration_sec": 6.04,
        "visual_brief": {
            "subject": "plastic",
            "context": ["tyre wear particles", "polystyrene granules"],
            "must_include": ["plastic"],
            "source_class": "generic_broll",
        },
    },
    "dry_valleys": {
        "scene_id": "scene_002",
        "narration": "В январе 2023 года они собрали образцы в Сухих долинах Мак-Мердо.",
        "target_duration_sec": 7.92,
        "visual_brief": {
            "subject": "dry valley floor",
            "place": "McMurdo Dry Valleys, Antarctica",
            "exact_entities": ["McMurdo Dry Valleys"],
            "must_include": ["McMurdo Dry Valleys"],
            "source_class": "exact_location",
        },
    },
    "soil_sampling": {
        "scene_id": "scene_002b",
        "narration": "Исследователи собирают почву в Сухих долинах.",
        "target_duration_sec": 7.0,
        "visual_brief": {
            "subject": "soil sample",
            "action": "collecting samples",
            "place": "Antarctica",
            "must_include": ["soil"],
            "source_class": "research_activity",
        },
    },
}

FIXTURE_CANDIDATES: dict[str, dict] = {
    # The NASA press day. Every word of it is true, and none of it is a laboratory.
    "mars_media_day": {
        "asset_id": "nasa_sam_media_day",
        "provider": "nasa_images",
        "title": "Sample Analysis at Mars Media Day",
        "description": (
            "Members of the news media view the Sample Analysis at Mars instrument suite, which "
            "includes a quadrupole mass spectrometer, before it is installed on the Mars Science "
            "Laboratory rover for the planetary mission."
        ),
        "tags": ["mars", "sam", "instrument", "media"],
    },
    # The neutral instrument photograph the scene actually wants.
    "ptr_tof": {
        "asset_id": "wikimedia_ptr_tof",
        "provider": "wikimedia",
        "title": "PTR-TOF mass spectrometer during sample analysis in an analytical laboratory",
        "description": "A proton transfer reaction time-of-flight mass spectrometer used for sample analysis in a laboratory.",
        "tags": ["mass spectrometer", "laboratory", "analysis"],
    },
    # The Internet Archive clip. It shares exactly one word with the scene.
    "iceberg": {
        "asset_id": "ia_b15a_iceberg",
        "provider": "internet_archive",
        "media_type": "video",
        "type": "video",
        "title": "B-15A Iceberg Breaks Off from the Ross Ice Shelf, Antarctica",
        "description": "Satellite imagery shows the B-15A iceberg breaking apart near the Ross Ice Shelf in Antarctica.",
        "tags": ["iceberg", "antarctica", "ross ice shelf"],
        "duration_sec": 30.0,
    },
    "station_in_wind": {
        "asset_id": "wikimedia_station",
        "provider": "wikimedia",
        "media_type": "video",
        "type": "video",
        "title": "Antarctic research station buildings in strong wind",
        "description": (
            "Buildings of an antarctic research station in Antarctica during a wind storm, "
            "with atmospheric transport of snow across the site."
        ),
        "tags": ["antarctic", "research station", "wind"],
        "duration_sec": 30.0,
    },
    # Real plastic, and only part of what the narration lists.
    "plastic_containers": {
        "asset_id": "pexels_plastic_containers",
        "provider": "pexels",
        "media_type": "video",
        "type": "video",
        "title": "Stacked plastic containers on a sorting line",
        "description": "Clear plastic containers moving along a recycling sorting line.",
        "tags": ["plastic", "containers", "recycling"],
        "duration_sec": 20.0,
    },
    # Relevant, correct, and horizontal: the crop question this stage refuses to guess.
    "antarctica_horizontal": {
        "asset_id": "nasa_dry_valleys_wide",
        "provider": "nasa_images",
        "title": "McMurdo Dry Valleys seen from the air, Antarctica",
        "description": "Wide aerial photograph of the bare dry valley floor of the McMurdo Dry Valleys in Antarctica.",
        "tags": ["mcmurdo dry valleys", "antarctica"],
        "width": 4096,
        "height": 2304,
    },
    # The whole continent, and nothing of the valley the scene names.
    "antarctica_only": {
        "asset_id": "wikimedia_antarctica",
        "provider": "wikimedia",
        "title": "Coast of Antarctica",
        "description": "The coast of Antarctica seen from a research vessel.",
        "tags": ["antarctica", "coast"],
    },
    "lab_dish_no_place": {
        "asset_id": "wikimedia_lab_dish",
        "provider": "wikimedia",
        "media_type": "video",
        "type": "video",
        "title": "Soil sample in a laboratory dish",
        "description": "A soil sample in a petri dish on a laboratory bench.",
        "tags": ["soil", "laboratory"],
        "duration_sec": 20.0,
    },
}


def _unique(values: list[str]) -> list[str]:
    """Same de-duplication ``apply_brief`` performs when it merges the two lists."""
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        key = str(value).strip().casefold()
        if key and key not in seen:
            seen.add(key)
            ordered.append(str(value).strip())
    return ordered


def _scene(name: str) -> dict:
    """One fixture scene in the shape the visual plan stores."""
    source = FIXTURE_SCENES[name]
    brief = source["visual_brief"]
    return {
        "scene_id": source["scene_id"],
        "narration": source["narration"],
        "visual_type": source.get("visual_type", "video"),
        "target_duration_sec": source["target_duration_sec"],
        "visual_brief": brief,
        "semantic": {
            "subject": [brief["subject"]] if brief.get("subject") else [],
            "action": [brief["action"]] if brief.get("action") else [],
            "location": [brief["place"]] if brief.get("place") else [],
            "environment": [brief["place"]] if brief.get("place") else [],
            "context": list(brief.get("context") or []),
            "conflicting_context": list(brief.get("conflicting_context") or []),
            "must_include": _unique(list(brief.get("exact_entities") or []) + list(brief.get("must_include") or [])),
            "must_not_include": list(brief.get("must_avoid") or []),
            "source_class": brief.get("source_class", ""),
            "visual_priority": "exact_subject",
        },
    }


def _candidate(name: str, **overrides) -> dict:
    """One fixture candidate, normalised the way a provider adapter delivers it."""
    source = FIXTURE_CANDIDATES[name]
    candidate = {
        "provider_asset_id": source["asset_id"],
        "media_type": "image",
        "type": "image",
        "tags_source": "provider",
        "source_page_url": f"https://example.test/{source['asset_id']}",
        "license": {"license_name": "test", "rights_status": "licensed", "allowed_for_render": True, "review_required": False},
        "rights_status": "licensed",
        "allowed_for_render": True,
        "review_required": False,
        "width": 1080,
        "height": 1920,
        "duration_sec": 0.0,
    }
    candidate.update(source)
    candidate.update(overrides)
    return candidate


def _select(scene_name: str, candidates: list[dict]):
    scene = _scene(scene_name)
    strategy = build_strategy(scene, available_providers=PROVIDERS)
    return select_best_candidate(
        analyze_scene(scene),
        candidates,
        required_duration_sec=float(scene["target_duration_sec"]),
        require_provider_metadata=strategy.requires_provider_metadata,
        source_class=strategy.source_class,
    )


def _rank_one(scene_name: str, candidate: dict) -> dict:
    scene = _scene(scene_name)
    strategy = build_strategy(scene, available_providers=PROVIDERS)
    return rank_candidates(
        analyze_scene(scene),
        [candidate],
        required_duration_sec=float(scene["target_duration_sec"]),
        require_provider_metadata=strategy.requires_provider_metadata,
        source_class=strategy.source_class,
    )[0]


class SemanticSlotTests(unittest.TestCase):
    """1-5: the scene states several requirements, and each is answered separately."""

    def test_1_every_stated_requirement_becomes_a_slot(self) -> None:
        ranked = _rank_one("antarctic_station", _candidate("station_in_wind"))
        slots = ranked[DECISION_KEY]["slots"]
        self.assertIn("subject", slots["required_slots"])
        self.assertIn("location", slots["required_slots"])
        self.assertIn("context", slots["required_slots"])
        self.assertIn("requirement:antarctic", slots["required_slots"])
        self.assertEqual(slots["conflicting_slots"], [])
        names = {slot["name"] for slot in slots["details"]}
        self.assertEqual(names, set(slots["required_slots"]))

    def test_2_a_continent_does_not_confirm_a_named_valley(self) -> None:
        selected, ranked = _select("dry_valleys", [_candidate("antarctica_only")])
        self.assertIsNone(selected, "Antarctica alone cannot answer the McMurdo Dry Valleys")
        slots = ranked[0][DECISION_KEY]["slots"]
        self.assertIn("location", slots["missing_slots"])
        location = next(slot for slot in slots["details"] if slot["name"] == "location")
        # The continent *is* in the evidence; the valley is not, and that is the whole
        # difference between a match and a broader shot of the same part of the world.
        self.assertEqual(location["note"], "broader_context_only")
        self.assertGreater(location["score"], 0.0)

    def test_3_a_missing_action_keeps_the_match_from_being_full(self) -> None:
        # Research activity: the scene is people doing something, not a place.
        ranked = _rank_one("soil_sampling", _candidate("lab_dish_no_place"))
        slots = ranked[DECISION_KEY]["slots"]
        self.assertIn("action", slots["missing_required_slots"])
        self.assertNotEqual(ranked["support_status"], SUPPORT_FULL)

    def test_4_a_missing_subject_keeps_the_match_from_being_full(self) -> None:
        ranked = _rank_one("antarctic_station", _candidate("iceberg"))
        slots = ranked[DECISION_KEY]["slots"]
        self.assertIn("subject", slots["absent_required_slots"])
        self.assertNotEqual(ranked["support_status"], SUPPORT_FULL)

    def test_5_the_iceberg_is_missing_the_station_and_the_transport(self) -> None:
        selected, ranked = _select("antarctic_station", [_candidate("iceberg")])
        self.assertIsNone(selected, "one shared word about a continent is not a research station")
        decision = ranked[0][DECISION_KEY]
        self.assertIn("subject", decision["slots"]["missing_slots"])
        self.assertIn("context", decision["slots"]["missing_slots"])
        # The place did match - which is exactly why nothing else caught this.
        self.assertIn("location", decision["slots"]["matched_slots"])
        self.assertIn("required_slot_missing", ranked[0]["reject_reason"])

    def test_5b_the_right_station_footage_is_accepted(self) -> None:
        selected, _ = _select("antarctic_station", [_candidate("station_in_wind")])
        self.assertIsNotNone(selected)
        self.assertEqual(selected["asset_id"], "wikimedia_station")


class ConflictingContextTests(unittest.TestCase):
    """6-8: a contradiction has to be stated by the author before it counts."""

    def test_6_a_declared_conflicting_context_found_in_metadata_is_a_conflict(self) -> None:
        ranked = _rank_one("mass_spectrometry", _candidate("mars_media_day"))
        slots = ranked[DECISION_KEY]["slots"]
        self.assertTrue(slots["conflicting_slots"])
        self.assertEqual(ranked[DECISION_KEY]["slot_verdict"], "conflicting")
        self.assertIn("conflicting_context", ranked["reject_reason"])

    def test_7_a_mars_press_day_never_fully_answers_a_laboratory_scene(self) -> None:
        selected, ranked = _select("mass_spectrometry", [_candidate("mars_media_day")])
        self.assertIsNone(selected)
        decision = ranked[0][DECISION_KEY]
        # The instrument term really is in the description, so the requirement passes -
        # and that used to be the whole test.
        self.assertIn("requirement:spectrometer", decision["slots"]["matched_slots"])
        self.assertNotEqual(decision["support_status"], SUPPORT_FULL)
        self.assertEqual(decision["support_status"], SUPPORT_MANUAL)

    def test_8_a_neutral_real_instrument_is_supported(self) -> None:
        selected, ranked = _select("mass_spectrometry", [_candidate("ptr_tof")])
        self.assertIsNotNone(selected, ranked[0]["reject_reason"])
        decision = selected[DECISION_KEY]
        self.assertEqual(decision["slots"]["conflicting_slots"], [])
        self.assertEqual(decision["support_status"], SUPPORT_FULL)
        self.assertTrue(decision["render_ready"])

    def test_8b_a_missing_mention_of_the_place_is_not_a_conflict(self) -> None:
        """Metadata that simply does not mention Antarctica says nothing against the
        instrument. Absence of evidence is not evidence of contradiction."""
        ranked = _rank_one("mass_spectrometry", _candidate("ptr_tof"))
        self.assertEqual(ranked[DECISION_KEY]["slots"]["conflicting_slots"], [])
        self.assertFalse(ranked["rejected"], ranked["reject_reason"])


class SupportStatusTests(unittest.TestCase):
    """9-11: how much of the scene the frame really carries."""

    def test_9_generic_broll_may_be_partial_without_being_refused(self) -> None:
        selected, ranked = _select("plastic_types", [_candidate("plastic_containers")])
        self.assertIsNotNone(selected, ranked[0]["reject_reason"])
        self.assertEqual(selected[DECISION_KEY]["support_status"], SUPPORT_PARTIAL)

    def test_10_plastic_containers_owe_the_rest_of_the_list(self) -> None:
        selected, _ = _select("plastic_types", [_candidate("plastic_containers")])
        decision = selected[DECISION_KEY]
        self.assertEqual(decision["support_status"], SUPPORT_PARTIAL)
        self.assertIn(NEEDS_ADDITIONAL_ASSET, decision["support_requirements"])
        self.assertIn("context", decision["slots"]["missing_slots"])
        self.assertFalse(decision["render_ready"])

    def test_11_a_data_infographic_is_only_ever_the_generated_asset(self) -> None:
        scene = {
            "scene_id": "scene_004",
            "visual_type": "image",
            "visual_brief": {"source_class": "data_infographic"},
            "semantic": {"source_class": "data_infographic", "visual_priority": "abstract_explanation"},
        }
        strategy = build_strategy(scene, available_providers=PROVIDERS)
        self.assertEqual(strategy.provider_order, ["local_library"])
        ranked = rank_candidates(
            analyze_scene(scene), [_candidate("antarctica_only")], source_class=strategy.source_class
        )[0]
        self.assertEqual(ranked["support_status"], SUPPORT_UNSUPPORTED)


class CropDecisionTests(unittest.TestCase):
    """12-14: the crop verdict says what it knows and refuses what it does not."""

    def test_12_a_horizontal_relevant_image_needs_its_crop_reviewed(self) -> None:
        selected, ranked = _select("dry_valleys", [_candidate("antarctica_horizontal")])
        self.assertIsNotNone(selected, ranked[0]["reject_reason"])
        decision = selected[DECISION_KEY]
        # The words all match. What no metadata can say is whether the valley survives
        # being cut down to the middle 9:16 strip.
        self.assertEqual(decision["slot_verdict"], "complete")
        self.assertEqual(decision["technical"]["status"], FRAMING_CROP_REVIEW)
        self.assertIn(NEEDS_CROP_REVIEW, decision["support_requirements"])
        self.assertEqual(decision["support_status"], SUPPORT_MANUAL)
        self.assertFalse(decision["render_ready"], "a frame nobody has looked at is not render-ready")

    def test_13_a_vertical_asset_of_the_right_size_is_ready(self) -> None:
        ranked = _rank_one("mass_spectrometry", _candidate("ptr_tof", width=1080, height=1920))
        framing = ranked[DECISION_KEY]["technical"]["framing"]
        self.assertEqual(framing["status"], FRAMING_VERTICAL_READY)
        self.assertEqual(framing["effective_width"], 1080)
        self.assertEqual(framing["upscale_factor"], 1.0)
        self.assertTrue(framing["render_ready"])

    def test_14_a_crop_that_leaves_too_few_pixels_is_refused(self) -> None:
        ranked = _rank_one("mass_spectrometry", _candidate("ptr_tof", width=1280, height=720))
        self.assertTrue(ranked["rejected"])
        self.assertEqual(ranked["framing_status"], FRAMING_LOW_RESOLUTION)
        self.assertEqual(ranked[DECISION_KEY]["technical"]["framing"]["effective_width"], 405)
        self.assertEqual(ranked["support_status"], SUPPORT_UNSUPPORTED)

    def test_14b_a_source_too_small_before_any_crop_is_named_as_such(self) -> None:
        ranked = _rank_one("mass_spectrometry", _candidate("ptr_tof", width=360, height=640))
        self.assertEqual(ranked["framing_status"], FRAMING_REJECTED)
        self.assertEqual(ranked[DECISION_KEY]["technical"]["framing"]["reason"], "source_resolution_too_low")

    def test_14c_an_extreme_panorama_is_an_aspect_mismatch(self) -> None:
        ranked = _rank_one("mass_spectrometry", _candidate("ptr_tof", width=6000, height=1200))
        self.assertEqual(ranked["framing_status"], "aspect_ratio_mismatch")
        self.assertTrue(ranked["rejected"])

    def test_14d_every_candidate_carries_a_crop_verdict(self) -> None:
        framing = _rank_one("plastic_types", _candidate("plastic_containers"))[DECISION_KEY]["technical"]["framing"]
        self.assertEqual(framing["target_aspect_ratio"], "9:16")
        self.assertEqual(framing["expected_output_width"], 1080)
        self.assertEqual(framing["expected_output_height"], 1920)
        self.assertIn("pan_zoom_possible", framing)


class DecisionPersistenceTests(unittest.TestCase):
    """15-17: the record survives selection, download and the review board."""

    def test_15_the_selected_candidate_carries_its_decision(self) -> None:
        selected, _ = _select("mass_spectrometry", [_candidate("ptr_tof")])
        self.assertTrue(selected[DECISION_KEY])
        decision = read_decision(selected)
        self.assertEqual(decision.asset_id, "wikimedia_ptr_tof")
        self.assertEqual(decision.source_class, "scientific_equipment")
        self.assertEqual(validate_decision(decision), [])

    def test_16_the_decision_survives_the_download_step(self) -> None:
        # A candidate whose rights the policy clears, already present on disk: the exact
        # path where ``to_manifest_dict`` used to rebuild the asset and drop the record.
        cleared = _candidate(
            "ptr_tof",
            provider="pexels",
            schema_version=1,
            local_path="C:/tmp/a.jpg",
            download_url="https://example.test/a.jpg",
            license={
                "license_name": "pexels",
                "license_url": "https://www.pexels.com/license/",
                "provider_terms_url": "https://www.pexels.com/terms-of-service/",
                "rights_status": "licensed",
                "allowed_for_render": True,
                "review_required": False,
            },
        )
        selected, ranked = _select("mass_spectrometry", [cleared])
        downloaded, attempts = _ensure_selected_asset_downloaded(
            selected=selected,
            ranked_candidates=ranked,
            providers_by_name={},
            project_root=None,
            project_id="p",
            scene_id="scene_006",
            media_index={"version": 1, "items": []},
            max_attempts=1,
        )
        self.assertEqual(attempts, [], "no provider is called for a file that is already local")
        self.assertTrue(downloaded[DECISION_KEY], "the decision must not be lost while resolving the file")
        self.assertEqual(read_decision(downloaded).support_status, SUPPORT_FULL)

    def test_17_the_review_board_reads_the_decision_off_the_selected_asset(self) -> None:
        selected, ranked = _select("dry_valleys", [_candidate("antarctica_horizontal")])
        bundle = create_scene_review_bundle(
            project_id="p",
            scene=_scene("dry_valleys"),
            semantic_scene=analyze_scene(_scene("dry_valleys")).to_dict(),
            metadata_queries=[],
            provider_routing={},
            candidates=ranked,
            analyses=[],
            selected_candidate_id=selected["asset_id"],
            target_aspect_ratio="9:16",
        )
        entry = bundle.selected_candidate
        self.assertEqual(entry["support_status"], SUPPORT_MANUAL)
        self.assertEqual(entry["technical_status"], FRAMING_CROP_REVIEW)
        self.assertFalse(entry["render_ready"])
        self.assertTrue(entry[DECISION_KEY], "the board must not have to look the decision back up")


class CompatibilityTests(unittest.TestCase):
    """18-19: nothing written before this stage may fail to load."""

    def test_18_an_asset_without_a_decision_reads_as_unknown_not_as_full(self) -> None:
        legacy = {"asset_id": "old", "provider": "pexels", "path": "old.mp4"}
        decision = read_decision(legacy)
        self.assertEqual(decision.support_status, "unverified")
        self.assertFalse(decision.render_ready)
        self.assertEqual(SelectionDecision.from_dict(None).slot_verdict, "unverified")
        self.assertEqual(SelectionDecision.from_dict({}).support_status, "unverified")

    def test_18b_a_stored_decision_round_trips(self) -> None:
        selected, _ = _select("mass_spectrometry", [_candidate("ptr_tof")])
        stored = json.loads(json.dumps(selected[DECISION_KEY], ensure_ascii=False))
        restored = SelectionDecision.from_dict(stored)
        self.assertEqual(restored.to_dict(), selected[DECISION_KEY])

    def test_19_a_visual_plan_written_before_this_stage_still_ranks(self) -> None:
        legacy_scene = {
            "scene_id": "scene_001",
            "visual_type": "video",
            "primary_query": "ocean waves aerial",
            "semantic": {"subject": ["ocean"], "must_include": ["ocean"], "visual_priority": "environment"},
        }
        scene = analyze_scene(legacy_scene)
        self.assertEqual(scene.context, [])
        self.assertEqual(scene.conflicting_context, [])
        self.assertEqual(scene.source_class, "")
        ranked = rank_candidates(
            scene,
            [_candidate("plastic_containers", title="Ocean waves seen from the air", description="Ocean waves")],
        )[0]
        self.assertTrue(ranked[DECISION_KEY])
        self.assertEqual(validate_decision(read_decision(ranked)), [])

    def test_19b_a_brief_without_the_new_fields_is_unchanged(self) -> None:
        brief = parse_brief({"subject": "mass spectrometer", "source_class": "scientific_equipment"})
        self.assertEqual(brief.context, [])
        self.assertEqual(brief.conflicting_context, [])
        self.assertNotIn("context", brief.to_dict())
        with_fields = parse_brief({"context": ["wind"], "conflicting_context": ["mars mission"]})
        self.assertEqual(with_fields.context, ["wind"])
        self.assertEqual(parse_brief(with_fields.to_dict()).conflicting_context, ["mars mission"])


class ValidationTests(unittest.TestCase):
    """Section 9: a decision has to be checkable on its own."""

    def test_full_support_is_impossible_with_a_missing_required_slot(self) -> None:
        decision = SelectionDecision(
            support_status=SUPPORT_FULL,
            slot_verdict="complete",
            slots={"missing_required_slots": ["subject"], "conflicting_slots": []},
        )
        self.assertIn("full_support_with_missing_required_slot", validate_decision(decision))

    def test_full_support_is_impossible_with_a_conflicting_slot(self) -> None:
        decision = SelectionDecision(
            support_status=SUPPORT_FULL,
            slot_verdict="complete",
            slots={"missing_required_slots": [], "conflicting_slots": ["conflicting_context:mars mission"]},
        )
        self.assertIn("full_support_with_conflicting_slot", validate_decision(decision))

    def test_full_support_is_impossible_with_an_unreviewed_crop(self) -> None:
        decision = SelectionDecision(
            support_status=SUPPORT_FULL, slot_verdict="complete", technical_status=FRAMING_CROP_REVIEW
        )
        self.assertIn("full_support_with_unreviewed_crop", validate_decision(decision))

    def test_a_strict_class_is_never_full_on_an_unverified_requirement(self) -> None:
        scene = _scene("dry_valleys")
        scene["semantic"]["must_include"] = ["Сухие долины"]
        ranked = rank_candidates(
            analyze_scene(scene), [_candidate("antarctica_horizontal")], source_class="exact_location"
        )[0]
        self.assertTrue(ranked["rejected"])
        self.assertIn("semantic_unverified", ranked["reject_reason"])
        self.assertNotEqual(ranked["support_status"], SUPPORT_FULL)

    def test_partial_support_is_never_render_ready(self) -> None:
        selected, _ = _select("plastic_types", [_candidate("plastic_containers")])
        decision = read_decision(selected)
        self.assertEqual(decision.support_status, SUPPORT_PARTIAL)
        self.assertFalse(decision.render_ready)
        self.assertEqual(validate_decision(decision), [])


class OfflineManifestTests(unittest.TestCase):
    """20: the whole path, with no provider, no network, no download and no render."""

    def test_20_the_manifest_records_the_decision_without_touching_anything(self) -> None:
        plan = {
            "language": "ru",
            "scenes": [
                {
                    **_scene("plastic_types"),
                    "primary_query": "plastic",
                    "preferred_asset_ids": [],
                }
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            manifest = build_assets_manifest(
                visual_plan=plan,
                user_assets=[],
                media_index={"version": 1, "items": []},
                providers=[],
                dry_run=True,
                project_root=root,
                project_id="project",
            )
            self.assertEqual(manifest["provider_attempts"], [])
            self.assertEqual(manifest["provider_errors"], [])
            summary = manifest["visual_support"]
            self.assertEqual(summary["scene_count"], 1)
            self.assertEqual(summary["unresolved"], 1)
            self.assertEqual(manifest["missing_scenes"][0]["resolution_status"], "unresolved_no_candidate")
            # Nothing was fetched, so nothing was written outside the manifest itself.
            self.assertFalse((root / "assets" / "downloaded").exists())


class ExtractedRequirementTests(unittest.TestCase):
    """A requirement only the planner invented must not refuse every candidate.

    The Q2.2A-2 retest left three scenes permanently empty over `долинах`, `грунте` and
    `пластик` - words extracted from Russian narration and promoted to hard
    requirements. Every remote provider is English-only, so such a term is never sent
    and can never come back in an answer: the requirement is unverifiable by
    construction, and an unverifiable requirement refuses everything.
    """

    def test_a_russian_stem_is_not_promoted_to_a_hard_requirement(self) -> None:
        plan = build_visual_plan(
            {
                "language": "ru",
                "scenes": [
                    {
                        "scene_id": "scene_001",
                        "narration": "В январе они собрали образцы в Сухих долинах Мак-Мердо.",
                        "target_duration_sec": 7.9,
                    }
                ],
            },
            language="ru",
        )
        must_include = plan["scenes"][0]["semantic"]["must_include"]
        self.assertEqual([term for term in must_include if not term.isascii()], [], must_include)

    def test_a_latin_name_is_still_required(self) -> None:
        """The gate is not switched off: a name a provider can actually return stays."""
        plan = build_visual_plan(
            {
                "language": "ru",
                "scenes": [
                    {
                        "scene_id": "scene_001",
                        "narration": "Прибор PTR-TOF работает в лаборатории.",
                        "target_duration_sec": 7.0,
                    }
                ],
            },
            language="ru",
        )
        planned = plan["scenes"][0]["semantic"]["must_include"]
        self.assertTrue(all(term.isascii() for term in planned), planned)

    def test_an_explicitly_empty_requirement_is_not_guessed_back(self) -> None:
        """The asset layer used to re-derive must_include from the scene's own subject.

        ``explicit.get(key) or fallback`` cannot tell "nothing was said" from "there is
        nothing", so the stem the planner had just stopped promoting came straight back.
        """
        scene = {
            "scene_id": "scene_002",
            "narration": "Учёные собрали образцы в Сухих долинах.",
            "semantic": {"subject": ["долинах"], "must_include": [], "visual_priority": "exact_subject"},
        }
        self.assertEqual(analyze_scene(scene).must_include, [])

    def test_a_scene_without_a_plan_still_gets_the_old_inference(self) -> None:
        """Hand-written fixtures and pre-planner projects keep their behaviour."""
        scene = {"scene_id": "scene_x", "primary_query": "whale in the ocean", "narration": "whale"}
        self.assertIn("whale", analyze_scene(scene).must_include)

    def test_a_brief_that_names_the_subject_replaces_the_extracted_requirement(self) -> None:
        """An author who described the shot has answered - including with silence."""
        from src.content.visual_planning.models import SceneVisualPlan

        plan = SceneVisualPlan(scene_id="scene_002", index=2, subject="долинах", must_include=["долинах"])
        apply_brief(plan, parse_brief({"subject": "Antarctic field researchers"}))
        self.assertEqual(plan.must_include, [])


class SoftScoreThresholdTests(unittest.TestCase):
    """The averaged score may no longer overrule the slot verdict.

    The retest dropped three clips whose only objection was ``score_below_60`` while
    their own slot record read "requirement matched, context missing" - a description of
    what is still owed, not a refusal.
    """

    # The scene as its author really wrote it: a long subject phrase listing several
    # materials, of which the clip shows one. The phrase overlap is what drags the
    # average under the threshold; the author's own requirement is met exactly.
    SCENE = {
        "scene_id": "scene_005",
        "narration": "Среди частиц были полиэтилен, ПЭТ, полистирол, ПВХ и следы износа шин.",
        "visual_type": "video",
        "target_duration_sec": 6.04,
        "semantic": {
            "subject": ["common plastic products and tire wear"],
            "action": ["showing plastic materials and rubber abrasion"],
            "location": [],
            "environment": [],
            "context": ["several different material examples"],
            "conflicting_context": [],
            "must_include": ["plastic"],
            "must_not_include": [],
            "source_class": "generic_broll",
            "visual_priority": "environment",
        },
    }

    def _thin_plastic_clip(self) -> dict:
        return _candidate(
            "plastic_containers",
            asset_id="pexels_bottles",
            provider_asset_id="pexels_bottles",
            title="close up shot of plastic bottles",
            description="",
            tags=["plastic"],
            media_type="video",
            type="video",
            width=2160,
            height=4096,
            duration_sec=20.0,
        )

    def _rank(self, candidate: dict) -> dict:
        return rank_candidates(
            analyze_scene(self.SCENE),
            [candidate],
            required_duration_sec=float(self.SCENE["target_duration_sec"]),
            source_class="generic_broll",
        )[0]

    def _pick(self, candidates: list[dict]):
        return select_best_candidate(
            analyze_scene(self.SCENE),
            candidates,
            required_duration_sec=float(self.SCENE["target_duration_sec"]),
            source_class="generic_broll",
        )

    def test_a_low_score_alone_no_longer_refuses_a_partly_supported_clip(self) -> None:
        ranked = self._rank(self._thin_plastic_clip())
        self.assertEqual(ranked[DECISION_KEY]["support_status"], SUPPORT_PARTIAL)
        self.assertTrue(
            [reason for reason in ranked["advisory_reject_reasons"] if reason.startswith("score_below_")],
            ranked["reject_reason"],
        )
        self.assertFalse(ranked["rejected"], ranked["reject_reason"])

    def test_the_objection_is_still_recorded(self) -> None:
        """Softened is not hidden: the reviewer still sees the score was low."""
        ranked = self._rank(self._thin_plastic_clip())
        self.assertIn("score_below_", ranked["reject_reason"])
        self.assertIn("score_below_", ";".join(ranked[DECISION_KEY]["reject_reasons"]))

    def test_a_partly_supported_clip_is_never_render_ready(self) -> None:
        selected, ranked = self._pick([self._thin_plastic_clip()])
        self.assertIsNotNone(selected, ranked[0]["reject_reason"])
        decision = selected[DECISION_KEY]
        self.assertEqual(decision["support_status"], SUPPORT_PARTIAL)
        self.assertFalse(decision["render_ready"])
        self.assertIn(NEEDS_ADDITIONAL_ASSET, decision["support_requirements"])
        self.assertEqual(validate_decision(read_decision(selected)), [])

    def test_an_unverifiable_candidate_is_not_rescued_by_the_same_rule(self) -> None:
        """Only a judged, partly supported candidate survives a soft objection."""
        blank = _candidate(
            "plastic_containers",
            asset_id="pexels_blank",
            provider_asset_id="pexels_blank",
            title="",
            description="",
            tags=[],
            tags_source="query_derived",
        )
        ranked = self._rank(blank)
        self.assertTrue(ranked["rejected"], ranked["reject_reason"])
        self.assertEqual(ranked["advisory_reject_reasons"], [])

    def test_a_missing_required_slot_is_still_a_refusal(self) -> None:
        """The iceberg protection is untouched: this is not a general loosening."""
        selected, ranked = _select("antarctic_station", [_candidate("iceberg")])
        self.assertIsNone(selected)
        self.assertIn("required_slot_missing", ranked[0]["reject_reason"])
        self.assertIn(
            "required_slot_missing",
            ";".join(ranked[0]["blocking_reject_reasons"]),
        )

    def test_a_fully_supported_candidate_outranks_a_partial_one(self) -> None:
        """Selection must not hand a scene to a partial match that merely scores well."""
        ranked = rank_candidates(
            analyze_scene(self.SCENE),
            [self._thin_plastic_clip(), _candidate("plastic_containers")],
            required_duration_sec=float(self.SCENE["target_duration_sec"]),
            source_class="generic_broll",
        )
        usable = [item[DECISION_KEY]["support_status"] for item in ranked if not item["rejected"]]
        self.assertEqual(usable, sorted(usable, key=lambda value: value != SUPPORT_FULL))


class ReviewBoardRenderingTests(unittest.TestCase):
    """The person opening the board must see the verdict, not three scores."""

    def _board(self) -> str:
        scene = _scene("plastic_types")
        ranked = _rank_one("plastic_types", _candidate("plastic_containers"))
        bundle = create_scene_review_bundle(
            project_id="project",
            scene=scene,
            semantic_scene=analyze_scene(scene).to_dict(),
            metadata_queries=[],
            provider_routing={},
            candidates=[ranked],
            analyses=[],
            selected_candidate_id=str(ranked.get("asset_id") or ""),
            target_aspect_ratio="9:16",
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            (root / "assets" / "review").mkdir(parents=True, exist_ok=True)
            paths = write_review_bundle(root, [bundle], write_html=True)
            return Path(paths["html_path"]).read_text(encoding="utf-8")

    def test_the_board_shows_the_support_status_and_the_crop_decision(self) -> None:
        board = self._board()
        self.assertIn(SUPPORT_PARTIAL, board)
        self.assertIn("кроп:", board)
        self.assertIn("render-ready:", board)

    def test_the_board_names_the_requirements_that_went_unanswered(self) -> None:
        board = self._board()
        self.assertIn("не подтверждено", board)


if __name__ == "__main__":
    unittest.main()
