from __future__ import annotations

import unittest


class SemanticAssetSelectionTests(unittest.TestCase):
    def test_australia_whale_scene_rejects_desert(self) -> None:
        from src.assets.semantic_selection import analyze_scene, rank_candidates

        scene = analyze_scene(
            {
                "scene_id": "scene_001",
                "primary_query": "southern right whale Australian coast drone",
                "visual_type": "video",
                "visual_priority": "exact_subject",
            }
        )
        ranked = rank_candidates(
            scene,
            [
                _candidate("desert", "Australia aerial desert road", "australia desert aerial", 3840, 2160),
                _candidate("whale", "Southern right whale mother calf ocean", "whale ocean coast drone", 3840, 2160),
            ],
        )

        self.assertEqual(ranked[0]["asset_id"], "whale")
        self.assertTrue(next(item for item in ranked if item["asset_id"] == "desert")["rejected"])
        self.assertIn("must_include", next(item for item in ranked if item["asset_id"] == "desert")["reject_reason"])

    def test_whale_scene_rejects_mountains(self) -> None:
        from src.assets.semantic_selection import analyze_scene, rank_candidates

        scene = analyze_scene({"primary_query": "whale mother calf ocean aerial", "visual_priority": "exact_subject"})
        ranked = rank_candidates(scene, [_candidate("mountains", "mountain valley aerial", "mountain canyon landscape")])

        self.assertTrue(ranked[0]["rejected"])
        self.assertGreater(ranked[0]["contradiction_penalty"], 0)

    def test_whale_scene_accepts_ocean_coastline_with_subject(self) -> None:
        from src.assets.semantic_selection import analyze_scene, rank_candidates

        scene = analyze_scene({"primary_query": "southern right whale Australian coast drone", "visual_priority": "exact_subject"})
        ranked = rank_candidates(scene, [_candidate("coast", "right whale swimming ocean coastline aerial", "whale coast ocean")])

        self.assertFalse(ranked[0]["rejected"])
        self.assertGreaterEqual(ranked[0]["scene_match_score"], 75)

    def test_exact_subject_requires_whale(self) -> None:
        from src.assets.semantic_selection import analyze_scene, rank_candidates

        scene = analyze_scene({"primary_query": "southern right whale mother calf ocean", "visual_priority": "exact_subject"})
        ranked = rank_candidates(scene, [_candidate("coast_only", "Australian coastline ocean aerial", "coastline ocean aerial")])

        self.assertTrue(ranked[0]["rejected"])
        self.assertIn("must_include", ranked[0]["reject_reason"])

    def test_transition_may_accept_coastline_without_whale(self) -> None:
        from src.assets.semantic_selection import analyze_scene, rank_candidates

        scene = analyze_scene(
            {
                "primary_query": "Australian coastline ocean aerial",
                "visual_priority": "transition",
                "visual_type": "video",
            }
        )
        ranked = rank_candidates(scene, [_candidate("coast", "Australian coastline ocean aerial", "coastline ocean aerial")])

        self.assertFalse(ranked[0]["rejected"])

    def test_negative_keyword_penalty_is_recorded(self) -> None:
        from src.assets.semantic_selection import analyze_scene, rank_candidates

        scene = analyze_scene({"primary_query": "whale ocean drone", "visual_priority": "exact_subject"})
        ranked = rank_candidates(scene, [_candidate("road", "whale road city logo", "road city")])

        self.assertIn("road", ranked[0]["negative_matches"])
        self.assertGreater(ranked[0]["contradiction_penalty"], 0)

    def test_must_include_rejection_overrides_score(self) -> None:
        from src.assets.semantic_selection import SemanticScene, rank_candidates

        scene = SemanticScene(
            scene_id="scene",
            subject=["whale"],
            environment=["ocean"],
            must_include=["whale", "ocean"],
            visual_priority="exact_subject",
        )
        ranked = rank_candidates(scene, [_candidate("high_quality_ocean", "ocean coast aerial", "ocean coast", 4096, 2160)])

        self.assertTrue(ranked[0]["rejected"])
        self.assertLess(ranked[0]["scene_match_score"], 75)

    def test_continuity_ocean_desert_ocean_rejection(self) -> None:
        from src.assets.semantic_selection import check_continuity

        report = check_continuity(
            [
                {"scene_id": "one", "selected_asset": _candidate("ocean1", "whale ocean", "ocean whale")},
                {"scene_id": "two", "selected_asset": _candidate("desert", "desert road", "desert road")},
                {"scene_id": "three", "selected_asset": _candidate("ocean2", "whale ocean", "ocean whale")},
            ]
        )

        self.assertEqual(report["status"], "failed")
        self.assertLess(report["continuity_score"], 70)

    def test_vision_mismatch_rejection_uses_existing_tags_without_api(self) -> None:
        from src.assets.semantic_selection import analyze_scene, rank_candidates

        scene = analyze_scene({"primary_query": "whale ocean aerial", "visual_priority": "exact_subject"})
        candidate = _candidate("tagged_desert", "ocean aerial", "ocean")
        candidate.update(
            {
                "checksum_sha256": "observed-bytes",
                "vision_tags": ["desert", "road"],
                "vision_tags_asset_id": candidate["asset_id"],
                "vision_tags_source_sha256": "observed-bytes",
                "vision_tags_cache_key": "semantic-cache-key",
            }
        )
        ranked = rank_candidates(scene, [candidate])

        self.assertTrue(ranked[0]["rejected"])
        self.assertIn("vision_mismatch", ranked[0]["reject_reason"])

    def test_fallback_level_enforcement(self) -> None:
        from src.assets.semantic_selection import SemanticScene, rank_candidates

        exact = SemanticScene(
            scene_id="exact",
            subject=["whale"],
            environment=["ocean"],
            must_include=["whale"],
            visual_priority="exact_subject",
            fallback_level=4,
        )
        transition = SemanticScene(
            scene_id="transition",
            environment=["ocean"],
            must_include=["ocean"],
            visual_priority="transition",
            fallback_level=4,
        )

        self.assertTrue(rank_candidates(exact, [_candidate("coast", "ocean coast", "ocean")])[0]["rejected"])
        self.assertFalse(rank_candidates(transition, [_candidate("coast", "ocean coast", "ocean")])[0]["rejected"])

    def test_unverifiable_candidate_does_not_outscore_a_checked_mismatch(self) -> None:
        """Воспроизведено на LOCAL repeat 2026-08-14, сцена «дождевой лес».

        Сцена ограничивает ``subject`` и ``action`` русскими словами; ``environment``
        и ``camera`` она не ограничивает вовсе. Против англоязычных метаданных оба
        заданных поля *undecidable* и выбрасываются из среднего вместе со своим весом
        (0.45 + 0.20), а в среднем остаются ровно те два поля, о которых сцена не
        спрашивала, — и каждое из них стоит 100 как «не применимо». Итог: ролик про
        закрывание вкладок браузера получал semantic 100 против сцены о пологе леса.

        Кандидат с двуязычными метаданными при этом проверяем: ``дождевой`` честно не
        совпадает, вес сохраняется, и он получает низкий балл. Инвертированный стимул
        и есть дефект: чем беднее метаданные, тем выше балл, потому что бедные
        метаданные нечем опровергнуть."""
        from src.assets.semantic_selection import analyze_scene, rank_candidates

        scene = analyze_scene(
            {
                "scene_id": "scene_001",
                "visual_type": "video",
                "semantic": {
                    "subject": ["дождевой"],
                    "action": ["выглядит"],
                    "environment": [],
                    "location": [],
                    "camera": [],
                    "must_include": [],
                    "visual_priority": "exact_subject",
                },
            }
        )
        unverifiable = _candidate(
            "browser_tabs",
            "Closing browser tabs at night",
            "closing browser tabs slow handwriting journal rain window minimal desk night",
        )
        checked_mismatch = _candidate(
            "tropical_river",
            "Широкая быстрая река с порогами, пальмы",
            "river rapids palms tropical река пороги пальмы тропики течение",
        )

        ranked = rank_candidates(scene, [unverifiable, checked_mismatch])
        by_id = {item["asset_id"]: item for item in ranked}

        # Ни одно заданное сценой поле не проверено, поэтому доказательства нет.
        self.assertEqual(by_id["browser_tabs"]["undecidable_fields"], ["subject", "action"])
        self.assertEqual(by_id["browser_tabs"]["semantic_match_status"], "unverified")
        self.assertEqual(
            by_id["browser_tabs"]["semantic_score"],
            0.0,
            "нечем проверить заданные поля - это отсутствие доказательства, а не совпадение",
        )
        # Непроверяемое не выбирается автоматически...
        self.assertTrue(by_id["browser_tabs"]["rejected"])
        # ...и не может обойти кандидата, которого реально сравнили со сценой.
        self.assertLessEqual(
            by_id["browser_tabs"]["final_score"], by_id["tropical_river"]["final_score"]
        )

    def test_scene_that_constrains_nothing_still_scores_its_candidates(self) -> None:
        """Обратная сторона той же правки: «сцена ничего не требует» и «сцену нечем
        проверить» — разные вещи, и вторая не должна поглотить первую."""
        from src.assets.semantic_selection import SemanticScene, rank_candidates

        unconstrained = SemanticScene(scene_id="free", visual_priority="transition")
        ranked = rank_candidates(unconstrained, [_candidate("coast", "ocean coast", "ocean")])

        self.assertEqual(ranked[0]["semantic_score"], 100.0)
        self.assertFalse(ranked[0]["rejected"])


def _candidate(asset_id: str, title: str, keywords: str, width: int = 1920, height: int = 1080) -> dict:
    return {
        "schema_version": 1,
        "asset_id": asset_id,
        "provider": "fake",
        "provider_asset_id": asset_id,
        "type": "video",
        "media_type": "video",
        "title": title,
        "description": title,
        "keywords": keywords.split(),
        "source_url": f"https://example.test/{asset_id}",
        "source_page": f"https://example.test/{asset_id}",
        "source_page_url": f"https://example.test/{asset_id}",
        "license": {
            "license_name": "fake_test_license",
            "rights_status": "licensed",
            "allowed_for_render": True,
            "review_required": False,
        },
        "provenance": {
            "provider": "fake",
            "provider_asset_id": asset_id,
            "source_page_url": f"https://example.test/{asset_id}",
        },
        "rights_status": "licensed",
        "allowed_for_render": True,
        "review_required": False,
        "width": width,
        "height": height,
        "duration": 10,
        "quality_score": 10,
        "vertical_score": 5,
    }


if __name__ == "__main__":
    unittest.main()

class M1CVisionEvidenceBindingTests(unittest.TestCase):
    def test_bare_vision_tags_have_no_content_authority(self) -> None:
        from src.assets.semantic_selection.evidence import build_evidence

        evidence = build_evidence(
            {"asset_id": "candidate_a", "vision_tags": ["desert", "road"]}
        )

        self.assertEqual(evidence.vision_tags, ())
        self.assertNotIn("desert", evidence.token_set)

    def test_partial_vision_envelopes_have_no_content_authority(self) -> None:
        from src.assets.semantic_selection.evidence import build_evidence

        complete = {
            "asset_id": "candidate_a",
            "checksum_sha256": "same-bytes",
            "vision_tags": ["desert"],
            "vision_tags_asset_id": "candidate_a",
            "vision_tags_source_sha256": "same-bytes",
            "vision_tags_cache_key": "semantic-cache-key",
        }
        for missing_field in (
            "vision_tags_asset_id",
            "vision_tags_source_sha256",
            "vision_tags_cache_key",
        ):
            with self.subTest(missing_field=missing_field):
                candidate = dict(complete)
                candidate[missing_field] = ""

                self.assertEqual(build_evidence(candidate).vision_tags, ())

    def test_vision_tags_without_current_checksum_have_no_content_authority(self) -> None:
        from src.assets.semantic_selection.evidence import build_evidence

        evidence = build_evidence(
            {
                "asset_id": "candidate_a",
                "vision_tags": ["desert"],
                "vision_tags_asset_id": "candidate_a",
                "vision_tags_source_sha256": "observed-bytes",
                "vision_tags_cache_key": "semantic-cache-key",
            }
        )

        self.assertEqual(evidence.vision_tags, ())

    def test_snapshot_specific_tags_fail_closed_for_different_representation(self) -> None:
        from src.assets.semantic_selection.evidence import build_evidence

        evidence = build_evidence(
            {
                "asset_id": "candidate_a",
                "checksum_sha256": "current-bytes",
                "vision_tags": ["desert", "road"],
                "vision_tags_asset_id": "candidate_a",
                "vision_tags_source_sha256": "preview-bytes",
                "vision_tags_cache_key": "semantic-cache-key",
            }
        )

        self.assertEqual(evidence.vision_tags, ())
        self.assertNotIn("desert", evidence.token_set)

    def test_snapshot_specific_tags_remain_evidence_for_matching_representation(self) -> None:
        from src.assets.semantic_selection.evidence import build_evidence

        evidence = build_evidence(
            {
                "asset_id": "candidate_a",
                "checksum_sha256": "same-bytes",
                "vision_tags": ["ocean", "whale"],
                "vision_tags_asset_id": "candidate_a",
                "vision_tags_source_sha256": "same-bytes",
                "vision_tags_cache_key": "semantic-cache-key",
            }
        )

        self.assertEqual(evidence.vision_tags, ("ocean", "whale"))

    def test_old_candidate_reads_but_bare_vision_tags_are_not_trusted(self) -> None:
        from src.assets.models import AssetCandidate
        from src.assets.semantic_selection.evidence import build_evidence

        loaded = AssetCandidate.from_dict(
            {
                "asset_id": "legacy_candidate",
                "provider": "local",
                "media_type": "image",
                "vision_tags": ["desert"],
            }
        )

        self.assertEqual(loaded.vision_tags, ["desert"])
        self.assertEqual(build_evidence(loaded.to_dict()).vision_tags, ())
