"""The eight scenes that failed, rebuilt offline as a regression fixture.

Stage Real Shorts E2E-A produced eight downloaded files and zero usable ones. This
reconstructs the same eight scenes and the same wrong candidates - stone fragments for
Antarctica, an autumn forest in Turkey for the Dry Valleys, hair-care footage for a
laboratory, a dog in a field for a statistic - and proves each of them is now refused.

The scenes are written here rather than copied out of the user's project: the fixture
must survive that project being changed or deleted, and runtime files do not belong in
tracked tests. Nothing here touches the network, a provider API, or the real project.
"""

from __future__ import annotations

import unittest

from src.assets.query_adapter import build_scene_queries
from src.assets.scene_strategy import build_strategy
from src.assets.semantic_selection import analyze_scene, select_best_candidate

PROVIDERS = ["local_library", "pexels", "pixabay", "wikimedia", "nasa_images", "internet_archive"]

# The eight scenes of the confirmed run, each with the visual brief its author would
# write. Durations are the ones the script engine actually produced.
SCENES: list[dict] = [
    {
        "scene_id": "scene_001",
        "narration": "Может ли частица пластика долететь туда, где почти нет людей?",
        "target_duration_sec": 9.33,
        "visual_brief": {
            "subject": "barren polar valley landscape",
            "place": "Antarctica",
            "exact_entities": ["Antarctica"],
            "must_include": ["antarctic"],
            "must_avoid": ["tropical forest", "green vegetation", "city", "beach resort"],
            "source_class": "exact_location",
            "shot_type": "establishing",
        },
    },
    {
        "scene_id": "scene_002",
        "narration": "В январе 2023 года они собрали образцы в Сухих долинах Мак-Мердо.",
        "target_duration_sec": 7.92,
        "visual_brief": {
            "subject": "soil sampling",
            "action": "collecting samples",
            "place": "McMurdo Dry Valleys Antarctica",
            "exact_entities": ["McMurdo Dry Valleys", "Antarctica"],
            "must_include": ["antarctic"],
            "must_avoid": ["tropical forest", "green vegetation", "autumn forest", "city"],
            "source_class": "research_activity",
        },
    },
    {
        "scene_id": "scene_003",
        "narration": "В грунте нашли микропластик и впервые нанопластик.",
        "target_duration_sec": 7.92,
        "visual_brief": {
            "subject": "laboratory microscopy",
            "place": "laboratory",
            "exact_entities": ["microscope"],
            "must_include": ["laboratory"],
            "must_avoid": ["beauty salon", "cosmetic treatment", "hair", "medical spa"],
            "source_class": "scientific_equipment",
        },
    },
    {
        "scene_id": "scene_004",
        "narration": "Наночастицы обнаружили на пятидесяти четырёх процентах участков.",
        "target_duration_sec": 8.05,
        "visual_type": "image",
        "visual_brief": {
            "source_class": "data_infographic",
            "infographic": {
                "headline_value": "54%",
                "caption": "участков верхнего слоя",
                "total_points": 13,
                "active_points": 7,
                "top_layer_label": "верхний слой",
                "top_layer_marks": 7,
                "deep_layer_label": "глубокий слой",
                "deep_layer_marks": 2,
            },
        },
    },
    {
        "scene_id": "scene_005",
        "narration": "Среди частиц были полиэтилен, ПЭТ, полистирол, ПВХ и следы износа шин.",
        "target_duration_sec": 6.04,
        "visual_brief": {
            "subject": "plastic pellets",
            "exact_entities": ["plastic"],
            "must_include": ["plastic"],
            "must_avoid": ["snow walk", "winter path"],
            "source_class": "generic_broll",
        },
    },
    {
        "scene_id": "scene_006",
        "narration": "Обнаружить настолько маленькие частицы удалось новым методом масс-спектрометрии.",
        "target_duration_sec": 7.92,
        "visual_brief": {
            "subject": "mass spectrometer",
            "action": "sample analysis",
            "place": "laboratory",
            "exact_entities": ["mass spectrometer"],
            "must_include": ["spectrometer"],
            "must_avoid": ["letter tiles", "stop motion animation", "beauty salon"],
            "source_class": "scientific_equipment",
        },
    },
    {
        "scene_id": "scene_007",
        "narration": "Пластик оставили станции или он прилетел по воздуху?",
        "target_duration_sec": 8.99,
        "visual_brief": {
            "subject": "antarctic research station",
            "place": "Antarctica",
            "exact_entities": ["Antarctic research station"],
            "must_include": ["antarctic"],
            "must_avoid": ["protest sign", "plastic curtain", "household waste"],
            "source_class": "exact_location",
        },
    },
    {
        "scene_id": "scene_008",
        "narration": "Если пластик добрался до одного из самых удалённых уголков Земли...",
        "target_duration_sec": 9.53,
        "visual_brief": {
            "subject": "antarctic landscape",
            "place": "Antarctica",
            "exact_entities": ["Antarctica"],
            "must_include": ["antarctic"],
            "must_avoid": ["protest sign", "plastic curtain", "household waste"],
            "source_class": "exact_location",
            "shot_type": "payoff",
        },
    },
]

# The candidates the real run actually chose, by their real Pexels page titles.
WRONG_CANDIDATES: dict[str, str] = {
    "scene_001": "Stone fragments on the table",
    "scene_002": "Drone view of lush autumn forest in Kayseri",
    "scene_003": "Blonde woman showcasing silky long hair",
    "scene_005": "Walking through snow covered pathway",
    "scene_006": "A stop motion animation of letter tiles",
    "scene_007": "A person packing plastic bottles",
    "scene_008": "A woman holding a sign behind a plastic curtain",
}


def _scene(scene_id: str) -> dict:
    scene = next(item for item in SCENES if item["scene_id"] == scene_id)
    brief = scene.get("visual_brief") or {}
    return {
        "scene_id": scene["scene_id"],
        "narration": scene["narration"],
        "visual_type": scene.get("visual_type", "video"),
        "target_duration_sec": scene["target_duration_sec"],
        "visual_brief": brief,
        "visual_priority": "exact_subject" if brief.get("exact_entities") else "environment",
        "semantic": {
            "subject": [brief["subject"]] if brief.get("subject") else [],
            "location": [brief["place"]] if brief.get("place") else [],
            "environment": [brief["place"]] if brief.get("place") else [],
            "must_include": list(brief.get("must_include") or []),
            "must_not_include": list(brief.get("must_avoid") or []),
            "visual_priority": "exact_subject" if brief.get("exact_entities") else "environment",
        },
    }


def _candidate(asset_id: str, title: str, *, provider: str = "pexels", duration: float = 20.0, **overrides) -> dict:
    candidate = {
        "asset_id": asset_id,
        "provider": provider,
        "provider_asset_id": asset_id,
        "media_type": "video",
        "type": "video",
        "title": title,
        "description": title,
        "tags": title.lower().split(),
        "tags_source": "provider",
        "source_page_url": f"https://example.test/{asset_id}",
        "license": {"license_name": "test", "rights_status": "licensed", "allowed_for_render": True, "review_required": False},
        "rights_status": "licensed",
        "allowed_for_render": True,
        "review_required": False,
        "width": 1080,
        "height": 1920,
        "duration_sec": duration,
        "quality_score": 8.5,
        "vertical_score": 10,
    }
    candidate.update(overrides)
    return candidate


def _select(scene_id: str, candidates: list[dict]):
    scene = _scene(scene_id)
    strategy = build_strategy(scene, available_providers=PROVIDERS)
    return select_best_candidate(
        analyze_scene(scene),
        candidates,
        required_duration_sec=float(scene["target_duration_sec"]),
        require_provider_metadata=strategy.requires_provider_metadata,
    )


class EightSceneRegressionTests(unittest.TestCase):
    def test_1_antarctic_scenes_route_to_nasa_and_wikimedia_before_stock(self) -> None:
        for scene_id in ("scene_001", "scene_007", "scene_008"):
            with self.subTest(scene=scene_id):
                order = build_strategy(_scene(scene_id), available_providers=PROVIDERS).provider_order
                self.assertLess(order.index("nasa_images"), order.index("pexels"))
                self.assertLess(order.index("wikimedia"), order.index("pexels"))

    def test_2_the_exact_mcmurdo_entity_survives_into_the_query(self) -> None:
        scene = _scene("scene_002")
        plan = build_scene_queries(scene, providers=["wikimedia", "nasa_images"], intent_language="ru")
        for provider in ("wikimedia", "nasa_images"):
            query = plan.for_provider(provider)[0].query
            self.assertIn("McMurdo Dry Valleys", query)
            self.assertNotIn("Сухих", query)
            self.assertNotIn("которую", query)

    def test_3_hair_care_footage_is_refused_for_the_laboratory_scene(self) -> None:
        selected, ranked = _select("scene_003", [_candidate("hair", WRONG_CANDIDATES["scene_003"])])
        self.assertIsNone(selected)
        self.assertIn("hair", ranked[0]["negative_matches"])

    def test_4_a_dog_in_a_field_can_never_answer_the_statistic_scene(self) -> None:
        strategy = build_strategy(_scene("scene_004"), available_providers=PROVIDERS)
        self.assertEqual(strategy.source_class, "data_infographic")
        # The stock libraries are not merely outranked here - they are not asked at all,
        # so "energetic border collie running through open field" cannot be returned.
        self.assertNotIn("pexels", strategy.provider_order)
        self.assertNotIn("pixabay", strategy.provider_order)

    def test_5_a_forest_in_turkey_is_refused_for_the_dry_valleys(self) -> None:
        selected, ranked = _select("scene_002", [_candidate("forest", WRONG_CANDIDATES["scene_002"])])
        self.assertIsNone(selected)
        self.assertTrue(ranked[0]["rejected"])

    def test_6_letter_tiles_are_refused_for_the_mass_spectrometer_scene(self) -> None:
        selected, ranked = _select("scene_006", [_candidate("tiles", WRONG_CANDIDATES["scene_006"])])
        self.assertIsNone(selected)
        self.assertTrue(ranked[0]["rejected"])

    def test_7_the_statistic_scene_gets_a_drawn_figure(self) -> None:
        import tempfile
        from pathlib import Path

        from src.assets.generated_infographic import build_generated_asset, spec_from_scene

        spec = spec_from_scene(_scene("scene_004"))
        self.assertIsNotNone(spec)
        with tempfile.TemporaryDirectory() as tmp:
            asset = build_generated_asset(spec, project_root=Path(tmp), project_id="p", scene_id="scene_004")
            self.assertTrue(Path(asset["path"]).is_file())
        self.assertEqual(asset["rights_status"], "user_owned")
        self.assertEqual(asset["provider"], "generated")

    def test_8_a_clip_shorter_than_its_scene_is_refused(self) -> None:
        good_title = "Mass spectrometer sample analysis in a research laboratory"
        selected, ranked = _select("scene_006", [_candidate("short", good_title, duration=6.54)])
        self.assertIsNone(selected)
        self.assertEqual(ranked[0]["duration_status"], "too_short")

    def test_9_generic_plastic_broll_from_pexels_is_allowed_when_it_matches(self) -> None:
        strategy = build_strategy(_scene("scene_005"), available_providers=PROVIDERS)
        self.assertEqual(strategy.source_class, "generic_broll")
        self.assertEqual(strategy.provider_order[:3], ["local_library", "pexels", "pixabay"])
        selected, _ = _select("scene_005", [_candidate("pellets", "Plastic pellets close up on a conveyor")])
        self.assertIsNotNone(selected)
        self.assertEqual(selected["asset_id"], "pellets")

    def test_every_wrong_candidate_from_the_real_run_is_now_refused(self) -> None:
        for scene_id, title in WRONG_CANDIDATES.items():
            with self.subTest(scene=scene_id, title=title):
                selected, _ = _select(scene_id, [_candidate("wrong", title)])
                self.assertIsNone(selected, f"{title!r} must not be accepted for {scene_id}")

    def test_a_correct_candidate_is_accepted_for_every_searchable_scene(self) -> None:
        good = {
            "scene_001": "Aerial view of barren antarctic dry valley rocks",
            "scene_002": "Researchers collecting soil samples in antarctic dry valleys",
            "scene_003": "Laboratory microscope examining particle samples",
            "scene_005": "Plastic pellets close up on a conveyor",
            "scene_006": "Mass spectrometer sample analysis in a research laboratory",
            "scene_007": "Antarctic research station buildings in strong wind",
            "scene_008": "Wide antarctic landscape under open sky",
        }
        for scene_id, title in good.items():
            with self.subTest(scene=scene_id):
                selected, ranked = _select(scene_id, [_candidate("right", title, provider="wikimedia")])
                self.assertIsNotNone(selected, f"{title!r} should answer {scene_id}: {ranked[0]['reject_reason']}")

    def test_no_acceptable_candidate_leaves_the_scene_unresolved(self) -> None:
        selected, ranked = _select("scene_001", [_candidate("nothing", "Unrelated office meeting")])
        self.assertIsNone(selected)
        self.assertTrue(all(item["rejected"] for item in ranked))

    def test_rights_and_provenance_survive_ranking(self) -> None:
        selected, _ = _select("scene_005", [_candidate("pellets", "Plastic pellets close up on a conveyor")])
        self.assertEqual(selected["rights_status"], "licensed")
        self.assertTrue(selected["allowed_for_render"])
        self.assertEqual(selected["source_page_url"], "https://example.test/pellets")

    def test_a_plan_without_any_brief_still_produces_a_decision(self) -> None:
        """Scenes planned before Q2.1 have no brief at all and must not crash."""
        legacy = {"scene_id": "scene_001", "visual_type": "video", "primary_query": "ocean waves aerial"}
        strategy = build_strategy(legacy, available_providers=PROVIDERS)
        self.assertIn(strategy.source_class, {"generic_broll", "exact_location"})
        self.assertTrue(strategy.provider_order)
        plan = build_scene_queries(legacy, providers=strategy.provider_order, intent_language="ru")
        self.assertTrue(plan.for_provider("pexels"))


if __name__ == "__main__":
    unittest.main()
