from __future__ import annotations

import unittest


class ProviderRoutingTests(unittest.TestCase):
    def test_nasa_scene_prefers_nasa(self) -> None:
        from src.assets.provider_routing import route_providers

        decision = route_providers(
            {
                "scene_id": "scene_001",
                "visual_type": "image",
                "primary_query": "NASA satellite observes hurricane over Earth atmosphere",
            },
            provider_names=["local_library", "pexels", "pixabay", "wikimedia", "nasa_images", "internet_archive", "envato_manual"],
        )

        self.assertEqual(decision["ordered_providers"][0], "local_library")
        self.assertEqual(decision["ordered_providers"][1], "nasa_images")
        self.assertIn("space_or_earth_observation", decision["reasons"]["nasa_images"])

    def test_historical_scene_prefers_wikimedia_and_archive(self) -> None:
        from src.assets.provider_routing import route_providers

        decision = route_providers(
            {
                "scene_id": "scene_002",
                "visual_type": "video",
                "primary_query": "historical archival footage old educational film 1930",
            },
            provider_names=["pexels", "wikimedia", "internet_archive", "nasa_images"],
        )

        self.assertLess(decision["ordered_providers"].index("internet_archive"), decision["ordered_providers"].index("pexels"))
        self.assertLess(decision["ordered_providers"].index("wikimedia"), decision["ordered_providers"].index("pexels"))
        self.assertIn("historical_or_archival", decision["reasons"]["internet_archive"])

    def test_generic_nature_prefers_local_then_stock(self) -> None:
        from src.assets.provider_routing import route_providers

        decision = route_providers(
            {"scene_id": "scene_003", "visual_type": "video", "primary_query": "cinematic nature animals forest river"},
            provider_names=["local_library", "wikimedia", "pexels", "pixabay", "internet_archive", "envato_manual"],
        )

        self.assertEqual(decision["ordered_providers"][:3], ["local_library", "pexels", "pixabay"])
        self.assertEqual(decision["fallback_order"][-1], "envato_manual")
        self.assertIn("manual_fallback_only", decision["reasons"]["envato_manual"])

    def test_rare_exact_object_prefers_wikimedia(self) -> None:
        from src.assets.provider_routing import route_providers

        decision = route_providers(
            {
                "scene_id": "scene_004",
                "visual_type": "image",
                "primary_query": "specific rare scientific equipment diagram named location observatory",
            },
            provider_names=["pexels", "pixabay", "wikimedia", "internet_archive"],
        )

        self.assertEqual(decision["ordered_providers"][0], "wikimedia")
        self.assertIn("specific_or_rare_subject", decision["reasons"]["wikimedia"])

    def test_disabled_and_policy_blocked_providers_are_skipped(self) -> None:
        from src.assets.provider_routing import route_providers

        decision = route_providers(
            {"scene_id": "scene_005", "visual_type": "image", "primary_query": "earth observation"},
            provider_names=["nasa_images", "wikimedia", "pexels"],
            provider_enabled={"nasa_images": False, "pexels": True, "wikimedia": True},
            policy_eligible={"pexels": False, "wikimedia": True},
        )

        self.assertNotIn("nasa_images", decision["ordered_providers"])
        self.assertNotIn("pexels", decision["ordered_providers"])
        self.assertEqual(decision["skipped_providers"]["nasa_images"], "disabled")
        self.assertEqual(decision["skipped_providers"]["pexels"], "policy_blocked")


if __name__ == "__main__":
    unittest.main()
