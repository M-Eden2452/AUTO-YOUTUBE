from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from src.providers.fake_provider import FakeStockProvider


class _CapturingStockProvider:
    name = "capture"

    def __init__(self, *, media_types: list[str] | None = None) -> None:
        self.media_types = list(media_types or ["video", "image"])
        self.requests = []

    def capabilities(self):
        from src.assets.models import ProviderCapabilities

        return ProviderCapabilities(
            provider=self.name,
            media_types=self.media_types,
            query_languages=["en", "ru"],
        )

    def search(self, request):
        self.requests.append(request)
        return []

    @staticmethod
    def resolve_license(candidate):
        return candidate

    @staticmethod
    def download(candidate, destination, context):
        return candidate

    @staticmethod
    def health_check():
        return None


class _HalfOutageStockProvider(FakeStockProvider):
    """Answers one media type and is down for the neighbouring one.

    A real provider fails per endpoint, not per scene: the image search can
    answer while the video search times out. This fixture reproduces exactly
    that shape so ``search_provider`` can be asked what it does with a mixed
    request when only half of it comes back.
    """

    def __init__(self, *, failing_media_type: str, **kwargs: object) -> None:
        super().__init__(**kwargs)  # type: ignore[arg-type]
        self.failing_media_type = failing_media_type
        self.requested_media_types: list[str] = []

    def search(self, request):  # type: ignore[override]
        from src.assets.provider_contract import ProviderNetworkError

        self.requested_media_types.append(request.media_type)
        if request.media_type == self.failing_media_type:
            raise ProviderNetworkError(
                f"{self.name} {request.media_type} endpoint is unavailable.",
                provider=self.name,
                query=request.query,
                retryable=True,
            )
        return super().search(request)


class NewsToShortAssetTests(unittest.TestCase):
    def _search_media_types(
        self,
        *,
        visual_type: str | None,
        allowed_media_kinds: list[str] | None,
        supported_media_types: list[str] | None = None,
    ) -> list[str]:
        from src.news.asset_manager import _search_provider

        provider = _CapturingStockProvider(media_types=supported_media_types)
        scene = {"scene_id": "scene_001"}
        if visual_type is not None:
            scene["visual_type"] = visual_type
        if allowed_media_kinds is not None:
            scene["allowed_media_kinds"] = allowed_media_kinds
        _search_provider(
            provider,
            "orca ocean",
            scene,
            {"must_not_include": []},
            project_id="retrieval_symmetry",
            limit=5,
        )
        return [request.media_type for request in provider.requests]

    def test_mixed_media_retrieval_requests_both_kinds_when_image_is_preferred(self) -> None:
        """PLAN-9C-2 R1: image preference may order, but may not filter."""
        self.assertEqual(
            self._search_media_types(
                visual_type="image",
                allowed_media_kinds=["image", "video"],
            ),
            ["image", "video"],
        )

    def test_mixed_media_retrieval_keeps_both_kinds_when_video_is_preferred(self) -> None:
        """PLAN-9C-2 R2: protect the existing mixed-video retrieval path."""
        self.assertEqual(
            self._search_media_types(
                visual_type="video",
                allowed_media_kinds=["image", "video"],
            ),
            ["video", "image"],
        )

    def test_image_only_retrieval_never_requests_video(self) -> None:
        """PLAN-9C-2 R3: allowed kinds are the hard retrieval boundary."""
        self.assertEqual(
            self._search_media_types(
                visual_type="video",
                allowed_media_kinds=["image"],
            ),
            ["image"],
        )

    def test_video_only_retrieval_never_requests_image(self) -> None:
        """PLAN-9C-2 R4: allowed kinds override an opposing image hint."""
        self.assertEqual(
            self._search_media_types(
                visual_type="image",
                allowed_media_kinds=["video"],
            ),
            ["video"],
        )

    def test_preference_changes_request_order_not_the_allowed_kind_set(self) -> None:
        """PLAN-9C-2 R5: both preferences expose the same candidate kinds."""
        image_first = self._search_media_types(
            visual_type="image",
            allowed_media_kinds=["image", "video"],
        )
        video_first = self._search_media_types(
            visual_type="video",
            allowed_media_kinds=["image", "video"],
        )

        self.assertEqual(set(image_first), {"image", "video"})
        self.assertEqual(set(video_first), {"image", "video"})
        self.assertEqual(image_first, ["image", "video"])
        self.assertEqual(video_first, ["video", "image"])

    def test_retrieval_respects_provider_media_capabilities(self) -> None:
        self.assertEqual(
            self._search_media_types(
                visual_type="video",
                allowed_media_kinds=["image", "video"],
                supported_media_types=["image"],
            ),
            ["image"],
        )

    def test_missing_or_empty_allowed_kinds_keep_legacy_preferred_only_behavior(self) -> None:
        for allowed in (None, []):
            with self.subTest(allowed=allowed):
                self.assertEqual(
                    self._search_media_types(
                        visual_type="image",
                        allowed_media_kinds=allowed,
                    ),
                    ["image"],
                )

    def test_manifest_builder_passes_mixed_scene_kinds_to_provider_retrieval(self) -> None:
        """Production path: scene constraints reach the real retrieval owner."""
        from src.news.asset_manager import build_assets_manifest

        provider = _CapturingStockProvider()
        manifest = build_assets_manifest(
            visual_plan={
                "language": "en",
                "scenes": [
                    {
                        "scene_id": "scene_001",
                        "visual_type": "image",
                        "allowed_media_kinds": ["image", "video"],
                        "primary_query": "orca ocean",
                    }
                ],
            },
            user_assets=[],
            media_index={"version": 1, "items": []},
            providers=[provider],
            dry_run=False,
            project_id="retrieval_symmetry_integration",
            allow_infographic_fallback=False,
            allow_emergency_backdrop=False,
        )

        self.assertEqual(
            [request.media_type for request in provider.requests],
            ["image", "video"],
        )
        self.assertTrue(
            all(request.scene_id == "scene_001" for request in provider.requests)
        )
        self.assertEqual(manifest["provider_attempts"][0]["result_count"], 0)

    def test_stock_video_search_keeps_full_hd_landscape_sources_for_vertical_crop(self) -> None:
        from src.assets.models import ProviderCapabilities
        from src.news.asset_manager import _search_provider

        captured = []

        class Provider:
            name = "capture"

            @staticmethod
            def capabilities() -> ProviderCapabilities:
                return ProviderCapabilities(provider="capture", media_types=["video"])

            @staticmethod
            def search(request):
                captured.append(request)
                return []

            @staticmethod
            def resolve_license(candidate):
                return candidate

            @staticmethod
            def download(candidate, destination, context):
                return candidate

            @staticmethod
            def health_check():
                return None

        _search_provider(
            Provider(),
            "orca",
            {
                "scene_id": "scene_001",
                "visual_type": "video",
                "allowed_media_kinds": ["video"],
            },
            {"must_not_include": []},
            project_id="landscape_crop",
            limit=5,
        )

        self.assertEqual(captured[0].min_width, 720)
        self.assertEqual(captured[0].min_height, 1080)

    def test_default_provider_factory_loads_existing_dotenv_configuration(self) -> None:
        from src.news.asset_manager import create_default_asset_providers

        with patch("src.news.asset_manager.load_dotenv") as load_dotenv, patch.dict(
            os.environ,
            {"PEXELS_API_KEY": "pexels-test", "PIXABAY_API_KEY": "pixabay-test"},
            clear=True,
        ):
            providers = create_default_asset_providers()

        load_dotenv.assert_called_once_with()
        self.assertIn("pexels", {provider.name for provider in providers})
        self.assertIn("pixabay", {provider.name for provider in providers})

    def test_animated_stock_video_is_rejected_as_non_real_footage(self) -> None:
        from src.assets.semantic_selection import analyze_scene, rank_candidates

        ranked = rank_candidates(
            analyze_scene(
                {
                    "scene_id": "scene_001",
                    "visual_type": "video",
                    "primary_query": "orca killer whale ocean",
                    "visual_brief": {
                        "subject": "orca killer whale",
                        "must_include": ["orca"],
                        "source_class": "generic_broll",
                    },
                }
            ),
            [
                {
                    "asset_id": "animated_orca",
                    "provider": "internet_archive",
                    "media_type": "video",
                    "type": "video",
                    "title": "Disney Little Einsteins animated orca cartoon",
                    "description": "A cartoon orca in an animated children's show.",
                    "width": 1920,
                    "height": 1080,
                    "duration": 90.0,
                    "allowed_for_render": True,
                }
            ],
            required_duration_sec=10.0,
        )

        self.assertTrue(ranked[0]["rejected"])
        self.assertIn("non_real_video_footage:", ranked[0]["reject_reason"])

    def test_exact_orca_metadata_outweighs_broader_dolphin_taxonomy_category(self) -> None:
        from src.assets.semantic_selection import SemanticScene, rank_candidates

        scene = SemanticScene(
            scene_id="scene_001",
            subject=["orca killer whale"],
            must_not_include=["dolphin"],
            visual_priority="exact_subject",
        )
        candidate = {
            "asset_id": "commons_orca",
            "provider": "wikimedia",
            "media_type": "video",
            "title": "Killer whales swimming in the wild.webm",
            "description": "Killer whales (Orcinus orca) swimming in the wild.",
            "tags": ["People with dolphins", "Orcinus orca in New Zealand"],
            "tags_source": "provider",
            "width": 1920,
            "height": 1080,
            "duration_sec": 30.0,
            "allowed_for_render": True,
        }

        ranked = rank_candidates(scene, [candidate], required_duration_sec=10.0)

        self.assertNotIn("dolphin", ranked[0]["negative_matches"])
        self.assertNotIn("must_avoid_match:dolphin", ranked[0]["reject_reason"])

    def test_explicit_dolphin_description_stays_blocked_for_orca_scene(self) -> None:
        from src.assets.semantic_selection import SemanticScene, rank_candidates

        scene = SemanticScene(
            scene_id="scene_001",
            subject=["orca killer whale"],
            must_not_include=["dolphin"],
            visual_priority="exact_subject",
        )
        candidate = {
            "asset_id": "actual_dolphin",
            "provider": "wikimedia",
            "media_type": "video",
            "title": "Dolphin swimming beside a boat",
            "description": "A bottlenose dolphin in the open ocean.",
            "tags": ["dolphins"],
            "tags_source": "provider",
            "width": 1920,
            "height": 1080,
            "duration_sec": 30.0,
            "allowed_for_render": True,
        }

        ranked = rank_candidates(scene, [candidate], required_duration_sec=10.0)

        self.assertIn("dolphin", ranked[0]["negative_matches"])
        self.assertIn("must_avoid_match:dolphin", ranked[0]["reject_reason"])

    def test_generic_whale_video_is_not_treated_as_verified_orca(self) -> None:
        from src.assets.semantic_selection import SemanticScene, rank_candidates

        scene = SemanticScene(
            scene_id="scene_001",
            subject=["orca killer whale"],
            visual_priority="exact_subject",
        )
        candidate = {
            "asset_id": "ambiguous_whale",
            "provider": "pexels",
            "media_type": "video",
            "title": "Aerial footage of whales in the ocean",
            "description": "Whales swimming near a boat.",
            "tags": ["whale", "ocean"],
            "tags_source": "provider",
            "width": 3840,
            "height": 2160,
            "duration_sec": 30.0,
            "allowed_for_render": True,
        }

        ranked = rank_candidates(scene, [candidate], required_duration_sec=10.0)

        self.assertTrue(ranked[0]["rejected"])
        self.assertIn("ambiguous_whale_for_orca_scene", ranked[0]["reject_reason"])

    def test_unrelated_video_is_not_selected_for_exact_orca_scene(self) -> None:
        from src.assets.semantic_selection import SemanticScene, rank_candidates

        scene = SemanticScene(
            scene_id="scene_001",
            subject=["orca killer whale"],
            visual_priority="exact_subject",
        )
        candidate = {
            "asset_id": "boats_on_lake",
            "provider": "pexels",
            "media_type": "video",
            "title": "scenic view of boats on tranquil lake",
            "description": "scenic view of boats on tranquil lake",
            "tags": ["scenic", "view", "boats", "tranquil", "lake"],
            "tags_source": "provider",
            "width": 2160,
            "height": 3840,
            "duration_sec": 45.0,
            "allowed_for_render": True,
        }

        ranked = rank_candidates(scene, [candidate], required_duration_sec=7.0)

        self.assertTrue(ranked[0]["rejected"])
        self.assertIn("missing_orca_evidence_for_orca_scene", ranked[0]["reject_reason"])

    def test_strict_selector_prefers_video_only_among_competitive_candidates(self) -> None:
        """Retargeted from the retired first-video-at-any-rank pin (PLAN-9C-2).

        The facade used to duplicate the unconditional override; it now
        delegates to the canonical media policy, so the preference may promote
        a video only inside the best candidate's own support class.
        """
        from src.assets.semantic_selection import SemanticScene
        from src.news.asset_manager import _select_best_candidate

        scene = SemanticScene(
            scene_id="scene_001",
            subject=["hummingbird"],
            action=["hovering"],
            environment=["flowers"],
        )

        def candidate(asset_id: str, media_type: str, title: str) -> dict:
            data = {
                "asset_id": asset_id,
                "provider": "pexels",
                "media_type": media_type,
                "title": title,
                "description": title,
                "tags": [],
                "tags_source": "provider",
                "width": 1080,
                "height": 1920,
                "rights_status": "licensed",
                "license_name": "Pexels License",
                "allowed_for_render": True,
                "review_required": False,
            }
            if media_type == "video":
                data["duration_sec"] = 12.0
            return data

        full_image = candidate(
            "image", "image", "Hummingbird hovering among flowers"
        )
        full_video = candidate(
            "video", "video", "Hummingbird hovering in slow motion"
        )
        partial_video = candidate(
            "partial_video", "video", "Hummingbird among colorful flowers"
        )

        promoted, _ranked = _select_best_candidate(
            scene,
            [full_image, full_video],
            prefer_video=True,
            required_duration_sec=5.0,
        )
        kept, _ranked = _select_best_candidate(
            scene,
            [full_image, partial_video],
            prefer_video=True,
            required_duration_sec=5.0,
        )

        self.assertEqual(promoted["asset_id"], "video")
        self.assertEqual(kept["asset_id"], "image")

    def test_standard_news_manifest_never_creates_emergency_infographic(self) -> None:
        from src.news.asset_manager import build_news_asset_manifest

        plan = {
            "language": "ru",
            "scenes": [
                {
                    "scene_id": "scene_001",
                    "visual_type": "video",
                    "allowed_media_kinds": ["video", "image"],
                    "target_duration_sec": 4.0,
                    "primary_query": "orca",
                }
            ],
        }
        with tempfile.TemporaryDirectory() as tmp, patch(
            "src.news.asset_manager.create_default_asset_providers", return_value=[]
        ):
            manifest = build_news_asset_manifest(
                visual_plan=plan,
                user_assets=[],
                dry_run=False,
                project_root=tmp,
                project_id="video_first",
                completion_mode="draft_complete",
                # Without this the manifest is built against the machine's real
                # assets/library index. The test passed only while every local record
                # was rights-blocked; once the curated library became renderable, a
                # solar-farm clip won the query "orca" - a real answer from real data,
                # and nothing this test is about.
                media_index_path=Path(tmp) / "empty_media_index.json",
            )

        self.assertEqual(manifest["visual_mode"], "video_first")
        self.assertFalse(manifest["infographic_fallback"])
        self.assertTrue(manifest["video_first_policy"]["enabled"])
        self.assertEqual(manifest["media_coverage"]["video_clips"], 0)
        self.assertTrue(manifest["media_coverage"]["review_required"])
        self.assertIsNone(manifest["scenes"][0]["selected_asset"])
        self.assertEqual(manifest["scenes"][0]["visual_assembly"]["slots"], [])

    def test_user_assets_are_selected_first_with_user_owned_rights(self) -> None:
        from src.news.asset_manager import build_assets_manifest

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            user_image = root / "whale.jpg"
            Image.new("RGB", (1080, 1920), (20, 80, 120)).save(user_image)
            visual_plan = {
                "scenes": [
                    {
                        "scene_id": "scene_001",
                        "visual_type": "image",
                        "primary_query": "whale mother calf aerial ocean",
                    }
                ]
            }

            manifest = build_assets_manifest(
                visual_plan=visual_plan,
                user_assets=[
                    {
                        "path": str(user_image),
                        "rights_declaration": {
                            "confirmation_status": "approved",
                            "license_name": "user_owned",
                            "rights_status": "user_owned",
                            "owner_approval_status": "approved",
                        },
                    }
                ],
                media_index={"version": 1, "items": []},
                dry_run=False,
            )

            selected = manifest["scenes"][0]["selected_asset"]
            self.assertEqual(selected["provider"], "user")
            self.assertTrue(selected["allowed_for_render"])
            self.assertEqual(selected["rights_declaration"]["confirmation_status"], "approved")
            self.assertTrue(selected["policy_decision"]["allowed_for_render"])
            self.assertEqual(manifest["missing_scenes"], [])

    def test_confirmed_user_asset_cannot_bypass_must_avoid_in_draft(self) -> None:
        from src.assets.completion import MODE_DRAFT_COMPLETE, read_assembly
        from src.news.asset_manager import build_assets_manifest

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            user_image = root / "penguin.jpg"
            Image.new("RGB", (1080, 1920), (20, 80, 120)).save(user_image)
            manifest = build_assets_manifest(
                visual_plan={
                    "scenes": [
                        {
                            "scene_id": "scene_001",
                            "visual_type": "image",
                            "target_duration_sec": 4.0,
                            "primary_query": "Antarctic research sample",
                            "visual_brief": {
                                "subject": "research sample",
                                "must_avoid": ["penguin"],
                            },
                        }
                    ]
                },
                user_assets=[
                    {
                        "path": str(user_image),
                        "rights_declaration": {
                            "confirmation_status": "approved",
                            "license_name": "user_owned",
                            "rights_status": "user_owned",
                            "owner_approval_status": "approved",
                        },
                    }
                ],
                media_index={"version": 1, "items": []},
                providers=[],
                dry_run=False,
                project_root=root,
                project_id="must_avoid_fixture",
                completion_mode=MODE_DRAFT_COMPLETE,
            )

            scene = manifest["scenes"][0]
            assembly = read_assembly(scene, scene_duration_sec=4.0)

        self.assertTrue(assembly.usable_in_draft)
        self.assertTrue(assembly.slots)
        self.assertTrue(all(slot.selected_asset["provider"] != "user" for slot in assembly.slots))
        rejected = next(
            item for item in scene["ranked_candidates"] if item["provider"] == "user"
        )
        self.assertIn("must_avoid_match:penguin", rejected["reject_reason"])

    def test_visual_support_summary_uses_the_weakest_secondary_slot(self) -> None:
        from src.assets.completion import (
            ASSEMBLY_COMPOSITE,
            MODE_DRAFT_COMPLETE,
            SLOT_PRIMARY,
            SLOT_SUPPORTING,
            TIER_EXACT,
            TIER_PARTIAL,
            SceneVisualAssembly,
            attach_assembly,
            evaluate_usability,
        )
        from src.assets.completion.assembly import slot_from_asset
        from src.assets.semantic_selection.decision import SUPPORT_PARTIAL
        from src.news.asset_manager import refresh_manifest_summaries
        from tests.test_autonomous_completion_pipeline import _asset, _png

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            exact = _asset(
                path=_png(root / "exact.png", 1),
                scene_id="scene_001",
            )
            partial = _asset(
                path=_png(root / "partial.png", 2),
                scene_id="scene_001",
                support=SUPPORT_PARTIAL,
                missing=["instrument_action"],
            )
            assembly = SceneVisualAssembly(
                scene_id="scene_001",
                scene_duration_sec=4.0,
                assembly_status=ASSEMBLY_COMPOSITE,
                completion_mode=MODE_DRAFT_COMPLETE,
                slots=[
                    slot_from_asset(
                        exact,
                        slot_id="scene_001_slot_001",
                        purpose=SLOT_PRIMARY,
                        start_offset_sec=0.0,
                        end_offset_sec=2.0,
                        quality_tier=TIER_EXACT,
                        usability=evaluate_usability(
                            exact,
                            mode=MODE_DRAFT_COMPLETE,
                            quality_tier=TIER_EXACT,
                            require_local_file=True,
                        ),
                    ),
                    slot_from_asset(
                        partial,
                        slot_id="scene_001_slot_002",
                        purpose=SLOT_SUPPORTING,
                        start_offset_sec=2.0,
                        end_offset_sec=4.0,
                        quality_tier=TIER_PARTIAL,
                        usability=evaluate_usability(
                            partial,
                            mode=MODE_DRAFT_COMPLETE,
                            quality_tier=TIER_PARTIAL,
                            require_local_file=True,
                        ),
                    ),
                ],
            )
            scene = {"scene_id": "scene_001", "required_duration_sec": 4.0}
            attach_assembly(scene, assembly)
            manifest = {
                "scenes": [scene],
                "missing_scenes": [],
                "completion": {"mode": MODE_DRAFT_COMPLETE},
            }
            refresh_manifest_summaries(manifest, mode=MODE_DRAFT_COMPLETE)

        summary = manifest["visual_support"]
        self.assertEqual(summary["full_support"], 0)
        self.assertEqual(summary["by_support_status"][SUPPORT_PARTIAL], 1)
        self.assertEqual(summary["scenes_needing_review"], ["scene_001"])

    def test_image_only_video_first_manifest_is_draft_review_not_publish_ready(self) -> None:
        from src.assets.completion import (
            ASSEMBLY_EXACT,
            MODE_DRAFT_COMPLETE,
            SLOT_PRIMARY,
            TIER_EXACT,
            SceneVisualAssembly,
            attach_assembly,
            evaluate_usability,
        )
        from src.assets.completion.assembly import slot_from_asset
        from src.news.asset_manager import refresh_manifest_summaries
        from tests.test_autonomous_completion_pipeline import _asset, _png

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image = _asset(
                path=_png(root / "image.png", 1),
                scene_id="scene_001",
            )
            assembly = SceneVisualAssembly(
                scene_id="scene_001",
                scene_duration_sec=5.0,
                assembly_status=ASSEMBLY_EXACT,
                completion_mode=MODE_DRAFT_COMPLETE,
                slots=[
                    slot_from_asset(
                        image,
                        slot_id="scene_001_slot_001",
                        purpose=SLOT_PRIMARY,
                        start_offset_sec=0.0,
                        end_offset_sec=5.0,
                        quality_tier=TIER_EXACT,
                        usability=evaluate_usability(
                            image,
                            mode=MODE_DRAFT_COMPLETE,
                            quality_tier=TIER_EXACT,
                            require_local_file=True,
                        ),
                        reuse_of_asset=image["asset_id"],
                        reuse_reason="test_reuse",
                    )
                ],
            )
            scene = {"scene_id": "scene_001", "required_duration_sec": 5.0}
            attach_assembly(scene, assembly)
            manifest = {
                "visual_mode": "video_first",
                "scenes": [scene],
                "missing_scenes": [],
                "completion": {"mode": MODE_DRAFT_COMPLETE},
            }

            refresh_manifest_summaries(manifest, mode=MODE_DRAFT_COMPLETE)

        coverage = manifest["media_coverage"]
        self.assertEqual(coverage["status"], "image_only_draft_fallback")
        self.assertEqual(coverage["video_clips"], 0)
        self.assertEqual(coverage["image_slots"], 1)
        self.assertEqual(coverage["reused_slots"], 1)
        self.assertEqual(coverage["video_duration_ratio"], 0.0)
        self.assertTrue(coverage["review_required"])
        self.assertEqual(manifest["completion"]["scenes_publish_ready"], 1)
        self.assertFalse(manifest["completion"]["publish_ready"])
        self.assertTrue(manifest["completion"]["video_first_review_required"])

    def test_video_coverage_threshold_is_configurable_and_duration_based(self) -> None:
        from src.assets.completion import SceneVisualAssembly, VisualSlot, attach_assembly
        from src.news.asset_manager import summarize_media_coverage

        assembly = SceneVisualAssembly(
            scene_id="scene_001",
            scene_duration_sec=5.0,
            slots=[
                VisualSlot(
                    slot_id="video_slot",
                    start_offset_sec=0.0,
                    end_offset_sec=2.0,
                    selected_asset={"asset_id": "video_1", "media_type": "video"},
                ),
                VisualSlot(
                    slot_id="image_slot",
                    start_offset_sec=2.0,
                    end_offset_sec=5.0,
                    selected_asset={"asset_id": "image_1", "media_type": "image"},
                ),
            ],
        )
        scene = {"scene_id": "scene_001", "required_duration_sec": 5.0}
        attach_assembly(scene, assembly)

        meets = summarize_media_coverage(
            [scene],
            policy={
                "enabled": True,
                "minimum_video_clips": 1,
                "minimum_video_duration_ratio": 0.4,
            },
        )
        misses = summarize_media_coverage(
            [scene],
            policy={
                "enabled": True,
                "minimum_video_clips": 1,
                "minimum_video_duration_ratio": 0.5,
            },
        )

        self.assertEqual(meets["video_duration_ratio"], 0.4)
        self.assertTrue(meets["meets_video_first_threshold"])
        self.assertFalse(misses["meets_video_first_threshold"])
        self.assertTrue(misses["review_required"])

    def test_video_coverage_allows_small_timeline_rounding_miss(self) -> None:
        from src.assets.completion import SceneVisualAssembly, VisualSlot, attach_assembly
        from src.news.asset_manager import summarize_media_coverage

        assembly = SceneVisualAssembly(
            scene_id="scene_001",
            scene_duration_sec=37.05,
            slots=[
                VisualSlot(
                    slot_id="video_slot",
                    start_offset_sec=0.0,
                    end_offset_sec=14.63,
                    selected_asset={"asset_id": "video_1", "media_type": "video"},
                ),
                VisualSlot(
                    slot_id="image_slot",
                    start_offset_sec=14.63,
                    end_offset_sec=37.05,
                    selected_asset={"asset_id": "image_1", "media_type": "image"},
                ),
            ],
        )
        scene = {"scene_id": "scene_001", "required_duration_sec": 37.05}
        attach_assembly(scene, assembly)

        coverage = summarize_media_coverage(
            [scene],
            policy={
                "enabled": True,
                "minimum_video_clips": 1,
                "minimum_video_duration_ratio": 0.4,
            },
        )

        self.assertEqual(coverage["video_duration_ratio"], 0.3949)
        self.assertTrue(coverage["meets_video_first_threshold"])
        self.assertFalse(coverage["review_required"])

    def test_unresolved_scene_duration_remains_in_video_coverage_denominator(self) -> None:
        from src.assets.completion import SceneVisualAssembly, VisualSlot, attach_assembly
        from src.news.asset_manager import summarize_media_coverage

        selected = {"scene_id": "scene_001", "required_duration_sec": 5.0}
        attach_assembly(
            selected,
            SceneVisualAssembly(
                scene_id="scene_001",
                scene_duration_sec=5.0,
                slots=[
                    VisualSlot(
                        slot_id="video_slot",
                        start_offset_sec=0.0,
                        end_offset_sec=5.0,
                        selected_asset={"asset_id": "video_1", "media_type": "video"},
                    )
                ],
            ),
        )
        unresolved = {"scene_id": "scene_002", "required_duration_sec": 5.0}
        attach_assembly(
            unresolved,
            SceneVisualAssembly(
                scene_id="scene_002",
                scene_duration_sec=5.0,
                slots=[],
            ),
        )

        coverage = summarize_media_coverage(
            [selected, unresolved],
            policy={
                "enabled": True,
                "minimum_video_clips": 1,
                "minimum_video_duration_ratio": 0.4,
            },
        )

        self.assertEqual(coverage["visual_duration_sec"], 10.0)
        self.assertEqual(coverage["video_duration_sec"], 5.0)
        self.assertEqual(coverage["video_duration_ratio"], 0.5)

    def test_reference_only_assets_are_not_selected_for_render(self) -> None:
        from src.news.asset_manager import build_assets_manifest

        with tempfile.TemporaryDirectory() as tmp:
            local_path = Path(tmp) / "reference.mp4"
            local_path.write_bytes(b"fake video")
            media_index = {
                "version": 1,
                "items": [
                    {
                        "id": "local_reference",
                        "type": "video",
                        "provider": "local",
                        "local_path": str(local_path),
                        "keywords": ["whale", "ocean"],
                        "width": 1920,
                        "height": 1080,
                        "duration": 8,
                        "rights_status": "reference_only",
                    }
                ],
            }
            visual_plan = {"scenes": [{"scene_id": "scene_001", "visual_type": "video", "primary_query": "whale ocean"}]}

            manifest = build_assets_manifest(
                visual_plan=visual_plan,
                user_assets=[],
                media_index=media_index,
                dry_run=False,
            )

            self.assertIsNone(manifest["scenes"][0]["selected_asset"])
            self.assertEqual(manifest["missing_scenes"][0]["scene_id"], "scene_001")

    def test_local_library_asset_can_be_selected_when_rights_allow_render(self) -> None:
        from src.news.asset_manager import build_assets_manifest

        with tempfile.TemporaryDirectory() as tmp:
            local_path = Path(tmp) / "ocean.mp4"
            local_path.write_bytes(b"fake video")
            media_index = {
                "version": 1,
                "items": [
                    {
                        "schema_version": 1,
                        "id": "local_ocean",
                        "type": "video",
                        "provider": "local",
                        "provider_asset_id": "local_ocean",
                        "local_path": str(local_path),
                        "keywords": ["whale", "ocean", "mother", "calf"],
                        "source_url": "file://local_ocean",
                        "width": 1920,
                        "height": 1080,
                        "duration": 8,
                        "rights_status": "licensed",
                        "allowed_for_render": True,
                        "review_required": False,
                        "license": {
                            "license_name": "user_owned",
                            "rights_status": "licensed",
                            "allowed_for_render": True,
                            "review_required": False,
                        },
                        "provenance": {
                            "provider": "local",
                            "provider_asset_id": "local_ocean",
                            "source_page_url": "file://local_ocean",
                        },
                    }
                ],
            }
            visual_plan = {"scenes": [{"scene_id": "scene_001", "visual_type": "video", "primary_query": "whale mother calf ocean"}]}

            manifest = build_assets_manifest(
                visual_plan=visual_plan,
                user_assets=[],
                media_index=media_index,
                dry_run=False,
            )

            self.assertEqual(manifest["scenes"][0]["selected_asset"]["asset_id"], "local_ocean")
            self.assertEqual(manifest["missing_scenes"], [])

    def test_provider_errors_are_recorded_without_stopping_manifest(self) -> None:
        from src.news.asset_manager import AssetProvider, build_assets_manifest

        class BrokenProvider(AssetProvider):
            name = "broken"

            def search(self, query: str, scene: dict, limit: int = 5) -> list[dict]:
                raise RuntimeError("provider unavailable")

        visual_plan = {"scenes": [{"scene_id": "scene_001", "visual_type": "video", "primary_query": "forest science"}]}

        manifest = build_assets_manifest(
            visual_plan=visual_plan,
            user_assets=[],
            media_index={"version": 1, "items": []},
            providers=[BrokenProvider()],
            dry_run=False,
        )

        self.assertEqual(manifest["provider_errors"][0]["provider"], "broken")
        self.assertEqual(manifest["missing_scenes"][0]["scene_id"], "scene_001")

    def test_generated_placeholder_is_forbidden_unless_debug_placeholders_enabled(self) -> None:
        from src.news.asset_manager import build_assets_manifest

        visual_plan = {"scenes": [{"scene_id": "scene_001", "visual_type": "video", "primary_query": "whale aerial"}]}

        normal = build_assets_manifest(
            visual_plan=visual_plan,
            user_assets=[],
            media_index={"version": 1, "items": []},
            dry_run=False,
        )
        debug = build_assets_manifest(
            visual_plan=visual_plan,
            user_assets=[],
            media_index={"version": 1, "items": []},
            dry_run=False,
            allow_generated_fallback=True,
        )

        self.assertIsNone(normal["scenes"][0]["selected_asset"])
        self.assertEqual(normal["missing_scenes"][0]["reason"], "no_allowed_asset_found")
        self.assertEqual(debug["scenes"][0]["selected_asset"]["selected_by"], "generated_fallback")

    def test_fake_provider_selected_asset_is_downloaded_with_license_and_provenance(self) -> None:
        from PIL import Image

        from src.news.asset_manager import build_assets_manifest
        from src.providers.fake_provider import FakeStockProvider

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture = root / "fixture.jpg"
            Image.new("RGB", (1080, 1920), (25, 90, 130)).save(fixture)
            visual_plan = {
                "scenes": [
                    {
                        "scene_id": "scene_001",
                        "visual_type": "image",
                        "primary_query": "whale ocean vertical",
                        "semantic": {
                            "environment": ["ocean"],
                            "must_include": ["ocean"],
                            "visual_priority": "environment",
                        },
                    }
                ]
            }

            manifest = build_assets_manifest(
                visual_plan=visual_plan,
                user_assets=[],
                media_index={"version": 1, "items": []},
                providers=[FakeStockProvider(image_fixture=fixture)],
                dry_run=False,
                project_root=root / "project",
                project_id="project_001",
            )

            selected = manifest["scenes"][0]["selected_asset"]
            self.assertEqual(manifest["schema_version"], 1)
            self.assertEqual(selected["provider"], "fake")
            self.assertTrue(Path(selected["path"]).is_file())
            self.assertEqual(selected["download_status"], "downloaded")
            self.assertEqual(len(selected["checksum_sha256"]), 64)
            self.assertEqual(selected["license"]["rights_status"], "licensed")
            self.assertEqual(selected["provenance"]["scene_id"], "scene_001")
            self.assertEqual(selected["technical_validation"]["status"], "passed")
            self.assertEqual(manifest["missing_scenes"], [])

    def test_unknown_provider_rights_are_blocked_and_recorded_as_missing(self) -> None:
        from PIL import Image

        from src.news.asset_manager import build_assets_manifest
        from src.providers.fake_provider import FakeStockProvider

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture = root / "fixture.jpg"
            Image.new("RGB", (1080, 1920), (25, 90, 130)).save(fixture)
            visual_plan = {
                "scenes": [
                    {
                        "scene_id": "scene_001",
                        "visual_type": "image",
                        "primary_query": "ocean vertical",
                        "semantic": {
                            "environment": ["ocean"],
                            "must_include": ["ocean"],
                            "visual_priority": "environment",
                        },
                    }
                ]
            }

            manifest = build_assets_manifest(
                visual_plan=visual_plan,
                user_assets=[],
                media_index={"version": 1, "items": []},
                providers=[FakeStockProvider(image_fixture=fixture, mode="unknown_license")],
                dry_run=False,
                project_root=root / "project",
                project_id="project_001",
            )

            self.assertIsNone(manifest["scenes"][0]["selected_asset"])
            self.assertEqual(manifest["missing_scenes"][0]["scene_id"], "scene_001")
            self.assertEqual(manifest["missing_scenes"][0]["reason"], "license_review_required")
            self.assertTrue(any(attempt.get("download_status") == "blocked" for attempt in manifest["provider_attempts"]))


class PartialMixedMediaRetrievalTests(unittest.TestCase):
    """VA-NEW-06 / M2-A: one failing media type may not erase the other's results.

    ``search_provider`` asks one provider once per allowed media kind. Since
    retrieval symmetry (``ae6d46c``) a mixed scene sends two requests, and a
    single failing one used to abort the whole call, discarding candidates that
    had already come back. Isolation is per provider attempt: the surviving kind
    keeps its results, the failing kind stays visible as a failed attempt, and a
    call where nothing survived still raises rather than reporting empty success.
    """

    @staticmethod
    def _mixed_scene(*, visual_type: str = "video") -> dict[str, object]:
        return {
            "scene_id": "scene_001",
            "visual_type": visual_type,
            "allowed_media_kinds": ["image", "video"],
            "primary_query": "orca ocean",
        }

    def _search(
        self,
        provider: object,
        *,
        scene: dict[str, object] | None = None,
        media_attempts: list[dict[str, object]] | None = None,
    ) -> list[dict[str, object]]:
        from src.news.asset_manager import _search_provider

        # The ledger collector is opt-in, so a caller that does not want the
        # per-media-type record keeps calling exactly as it always has.
        extra = {} if media_attempts is None else {"media_attempts": media_attempts}
        return _search_provider(
            provider,
            "orca ocean",
            scene if scene is not None else self._mixed_scene(),
            {"must_not_include": []},
            project_id="va_new_06",
            limit=5,
            **extra,
        )

    def test_a_satisfied_media_type_survives_a_failing_preferred_neighbour(self) -> None:
        provider = _HalfOutageStockProvider(failing_media_type="video")

        results = self._search(provider)

        self.assertEqual(provider.requested_media_types, ["video", "image"])
        self.assertEqual([str(item["media_type"]) for item in results], ["image"])

    def test_a_satisfied_media_type_survives_a_failing_secondary_neighbour(self) -> None:
        provider = _HalfOutageStockProvider(failing_media_type="video")

        results = self._search(provider, scene=self._mixed_scene(visual_type="image"))

        self.assertEqual(provider.requested_media_types, ["image", "video"])
        self.assertEqual([str(item["media_type"]) for item in results], ["image"])

    def test_a_failed_media_type_stays_visible_as_its_own_attempt(self) -> None:
        provider = _HalfOutageStockProvider(failing_media_type="video")
        media_attempts: list[dict[str, object]] = []

        self._search(provider, media_attempts=media_attempts)

        self.assertEqual(
            [(item["media_type"], item["status"]) for item in media_attempts],
            [("video", "failed"), ("image", "completed")],
        )
        error = media_attempts[0]["error"]
        assert isinstance(error, dict)
        self.assertEqual(error["code"], "network_error")
        self.assertTrue(error["retryable"])
        self.assertEqual(media_attempts[0]["result_count"], 0)
        self.assertEqual(media_attempts[1]["result_count"], 1)

    def test_a_satisfied_media_type_is_never_re_requested_because_a_neighbour_failed(
        self,
    ) -> None:
        provider = _HalfOutageStockProvider(failing_media_type="video")

        self._search(provider)

        self.assertEqual(provider.requested_media_types.count("image"), 1)
        self.assertEqual(provider.requested_media_types.count("video"), 1)

    def test_every_media_type_failing_still_raises_instead_of_reporting_empty_success(
        self,
    ) -> None:
        from src.assets.provider_contract import ProviderRateLimitError

        provider = FakeStockProvider(mode="rate_limit")
        media_attempts: list[dict[str, object]] = []

        with self.assertRaises(ProviderRateLimitError):
            self._search(provider, media_attempts=media_attempts)

        self.assertEqual(
            [(item["media_type"], item["status"]) for item in media_attempts],
            [("video", "failed"), ("image", "failed")],
        )

    def test_a_single_media_type_scene_keeps_its_failure_raising_unchanged(self) -> None:
        from src.assets.provider_contract import ProviderNetworkError

        provider = _HalfOutageStockProvider(failing_media_type="video")

        with self.assertRaises(ProviderNetworkError):
            self._search(
                provider,
                scene={
                    "scene_id": "scene_001",
                    "visual_type": "video",
                    "allowed_media_kinds": ["video"],
                    "primary_query": "orca ocean",
                },
            )

    def test_manifest_builder_keeps_partial_results_and_still_reports_the_failure(
        self,
    ) -> None:
        """Production path: the builder is where a lost half used to disappear."""
        from src.news.asset_manager import build_assets_manifest

        provider = _HalfOutageStockProvider(failing_media_type="video")
        manifest = build_assets_manifest(
            visual_plan={
                "language": "en",
                "scenes": [self._mixed_scene()],
            },
            user_assets=[],
            media_index={"version": 1, "items": []},
            providers=[provider],
            dry_run=False,
            project_id="va_new_06_integration",
            allow_infographic_fallback=False,
            allow_emergency_backdrop=False,
        )

        scene_entry = manifest["scenes"][0]
        self.assertEqual(
            [str(item["media_type"]) for item in scene_entry["candidates"]],
            ["image"],
        )

        attempt = scene_entry["provider_attempts"][0]
        self.assertEqual(attempt["status"], "completed")
        self.assertEqual(attempt["result_count"], 1)
        self.assertEqual(
            [(item["media_type"], item["status"]) for item in attempt["media_attempts"]],
            [("video", "failed"), ("image", "completed")],
        )

        # The half that failed is still an honest provider error, not a silent gap.
        self.assertEqual(
            [error["code"] for error in manifest["provider_errors"]],
            ["network_error"],
        )
        self.assertEqual(manifest["provider_errors"][0]["media_type"], "video")


class _CountingStockProvider(FakeStockProvider):
    """Records every request it is actually sent and answers with nothing.

    A provider that finds nothing is the honest shape for a fan-out measurement:
    the search runs to the end of the plan, so what the counter holds afterwards
    is the whole cost of the scene rather than the cost up to a lucky hit.
    """

    def __init__(self, name: str) -> None:
        super().__init__(mode="success")
        self.name = name
        self.requests: list[tuple[str, str]] = []

    def search(self, request):  # type: ignore[override]
        self.requests.append((request.query, request.media_type))
        return []


def _rich_mixed_scene(scene_id: str = "scene_001") -> dict[str, object]:
    """One scene whose plan legitimately expands into many provider queries."""

    return {
        "scene_id": scene_id,
        "visual_type": "video",
        "allowed_media_kinds": ["image", "video"],
        "primary_query": "orca ocean hunting",
        "visual_brief": {
            "subject": "orca",
            "action": "hunting",
            "place": "open ocean",
            "must_include": ["orca"],
        },
        "provider_queries": {
            "pexels": ["orca ocean", "killer whale pod", "orca hunting seal"],
            "pixabay": ["orca ocean", "killer whale pod", "orca hunting seal"],
        },
        "search_queries": ["orca ocean surface", "whale pod aerial"],
    }


class SceneRequestBudgetTests(unittest.TestCase):
    """VA-NEW-12 / M2-B: one scene has a hard ceiling on provider requests.

    Per-source caps existed, but nothing capped the composition: every routed
    provider ran every allowed query to the end regardless of what had already
    come back. Measured on the real production path at ``36f23cc``, the scene
    below sent **36** provider search requests through three providers, and the
    largest real per-scene fan-out on disk is 30 query attempts through five
    providers - which at current retrieval symmetry costs up to 60 requests.

    The unit is one ``provider.search`` call - one query against one media kind -
    because that is what a provider rate-limits and bills. A query attempt is
    deliberately not the unit: since ``ae6d46c`` a mixed scene sends one request
    per allowed media kind, so counting attempts undercounts the real cost by
    exactly that multiplier.
    """

    @staticmethod
    def _build(
        providers: list[_CountingStockProvider],
        *,
        budget: object = None,
        scenes: list[dict[str, object]] | None = None,
        completion_mode: str = "",
    ) -> dict[str, object]:
        from src.news.asset_manager import build_assets_manifest

        selection = {} if budget is None else {"max_provider_requests_per_scene": budget}
        return build_assets_manifest(
            visual_plan={
                "language": "en",
                "intent_language": "en",
                "scenes": scenes if scenes is not None else [_rich_mixed_scene()],
            },
            user_assets=[],
            media_index={"version": 1, "items": []},
            providers=list(providers),
            dry_run=False,
            asset_selection=selection or None,
            project_id="va_new_12",
            completion_mode=completion_mode,
            allow_infographic_fallback=False,
            allow_emergency_backdrop=False,
        )

    @staticmethod
    def _sent(providers: list[_CountingStockProvider]) -> int:
        return sum(len(provider.requests) for provider in providers)

    def _providers(self) -> list[_CountingStockProvider]:
        return [
            _CountingStockProvider(name)
            for name in ("pexels", "pixabay", "wikimedia_commons")
        ]

    def test_a_scene_never_sends_more_provider_requests_than_its_budget(self) -> None:
        providers = self._providers()

        self._build(providers, budget=10)

        self.assertLessEqual(self._sent(providers), 10)

    def test_the_budget_is_an_exact_ceiling_and_not_an_approximation(self) -> None:
        """Off-by-one: a budget of N allows N requests, never N+1."""

        for limit in (1, 2, 3, 7, 12):
            with self.subTest(limit=limit):
                providers = self._providers()

                self._build(providers, budget=limit)

                self.assertEqual(self._sent(providers), limit)

    def test_an_odd_budget_cuts_inside_a_query_because_requests_are_the_unit(
        self,
    ) -> None:
        """A mixed query costs two requests, so an odd budget stops mid-query."""

        providers = self._providers()

        self._build(providers, budget=5)

        sent = [request for provider in providers for request in provider.requests]
        self.assertEqual(len(sent), 5)
        # Two whole mixed queries (video+image) plus the first half of a third.
        self.assertEqual(
            [media_type for _query, media_type in sent],
            ["video", "image", "video", "image", "video"],
        )

    def test_an_exhausted_budget_never_reaches_the_provider_at_all(self) -> None:
        """Not "call and discard": the request is never sent."""

        providers = self._providers()

        manifest = self._build(providers, budget=0)

        self.assertEqual(self._sent(providers), 0)
        self.assertEqual(len(manifest["scenes"]), 1)

    def test_a_failing_request_spends_its_unit_and_never_refills_the_budget(
        self,
    ) -> None:
        from src.assets.provider_contract import ProviderNetworkError

        class _AlwaysFailing(_CountingStockProvider):
            def search(self, request):  # type: ignore[override]
                self.requests.append((request.query, request.media_type))
                raise ProviderNetworkError(
                    "down",
                    provider=self.name,
                    query=request.query,
                    retryable=True,
                )

        providers = [_AlwaysFailing(name) for name in ("pexels", "pixabay")]

        self._build(providers, budget=6)  # type: ignore[arg-type]

        self.assertEqual(self._sent(providers), 6)

    @staticmethod
    def _half_outage(name: str) -> _HalfOutageStockProvider:
        """A provider whose video endpoint is down and image endpoint answers."""

        provider = _HalfOutageStockProvider(failing_media_type="video")
        provider.name = name
        return provider

    def test_a_failing_media_kind_costs_the_requests_it_actually_sent(self) -> None:
        """M2-A made the second kind reachable; the budget counts both halves."""

        provider = self._half_outage("pexels")

        self._build([provider], budget=4)  # type: ignore[list-item]

        # Four requests, i.e. two query attempts of two kinds each - not four
        # query attempts. The kind that fails is charged exactly like the kind
        # that answers.
        self.assertEqual(
            provider.requested_media_types,
            ["video", "image", "video", "image"],
        )

    def test_partial_media_success_survives_the_budget_running_out(self) -> None:
        """M2-A is not undone: what already answered is kept and stays visible."""

        provider = self._half_outage("pexels")

        manifest = self._build([provider], budget=3)  # type: ignore[list-item]

        self.assertEqual(provider.requested_media_types, ["video", "image", "video"])
        scene_entry = manifest["scenes"][0]
        # The image half that answered before the stop is still in the pool.
        self.assertEqual(
            {str(item["media_type"]) for item in scene_entry["candidates"]},
            {"image"},
        )
        # The video half that was cut is unresolved, not silently successful.
        last = scene_entry["provider_attempts"][-2]
        self.assertEqual(
            [
                (item["media_type"], item["status"])
                for item in last.get("media_attempts", [])
            ],
            [("video", "failed"), ("image", "skipped")],
        )

    def test_the_budget_stop_is_its_own_reason_and_not_a_provider_error(self) -> None:
        providers = self._providers()

        manifest = self._build(providers, budget=4)

        stops = [
            attempt
            for attempt in manifest["scenes"][0]["provider_attempts"]
            if attempt.get("reason") == "request_budget_exhausted"
        ]
        self.assertEqual(len(stops), 1)
        self.assertEqual(stops[0]["status"], "skipped")
        self.assertEqual(stops[0]["request_budget"], {"limit": 4, "spent": 4})
        self.assertGreater(stops[0]["queries_not_sent"], 0)
        # Stopping on budget is not a provider failing.
        self.assertEqual(manifest["provider_errors"], [])

    def test_an_untranslatable_provider_survives_a_budget_stop(self) -> None:
        """A plan-level fact is not a request and is never spent away."""

        from src.assets.models import ProviderCapabilities

        class _UnsearchableLanguageProvider(_CountingStockProvider):
            """Nothing in the plan is in a language it can be searched in."""

            def capabilities(self):  # type: ignore[override]
                return ProviderCapabilities(
                    provider=self.name,
                    media_types=["video", "image"],
                    query_languages=["ja"],
                )

        providers = [
            _CountingStockProvider("pexels"),
            _UnsearchableLanguageProvider("wikimedia_commons"),
        ]

        manifest = self._build(providers, budget=2)  # type: ignore[arg-type]

        reasons = [
            attempt.get("reason")
            for attempt in manifest["scenes"][0]["provider_attempts"]
        ]
        self.assertIn("query_translation_required", reasons)
        self.assertIn("request_budget_exhausted", reasons)

    def test_each_scene_gets_its_own_budget(self) -> None:
        providers = self._providers()

        self._build(
            providers,
            budget=4,
            scenes=[_rich_mixed_scene("scene_001"), _rich_mixed_scene("scene_002")],
        )

        self.assertEqual(self._sent(providers), 8)

    def test_a_stopped_scene_does_not_starve_the_next_one(self) -> None:
        providers = self._providers()

        manifest = self._build(
            providers,
            budget=4,
            scenes=[_rich_mixed_scene("scene_001"), _rich_mixed_scene("scene_002")],
        )

        second = manifest["scenes"][1]
        sent = [
            attempt
            for attempt in second["provider_attempts"]
            if attempt.get("status") in {"completed", "failed"}
        ]
        self.assertEqual(len(sent), 2)

    def test_an_invalid_budget_falls_back_to_the_bounded_default(self) -> None:
        """Never unlimited: a broken value is replaced, not interpreted."""

        from src.news.asset_provider_adapters import (
            DEFAULT_MAX_PROVIDER_REQUESTS_PER_SCENE as DEFAULT,
        )

        for raw in (-1, "many", None, [], 1.5):
            with self.subTest(raw=raw):
                providers = self._providers()

                self._build(providers, budget=raw)

                self.assertLessEqual(self._sent(providers), DEFAULT)
                self.assertGreater(self._sent(providers), 0)

    def test_a_scene_that_configures_nothing_is_still_bounded(self) -> None:
        """The guard is the default, not something a channel has to opt into."""

        from src.news.asset_provider_adapters import (
            DEFAULT_MAX_PROVIDER_REQUESTS_PER_SCENE as DEFAULT,
        )

        names = (
            "pexels",
            "pixabay",
            "wikimedia_commons",
            "internet_archive",
            "nasa_images",
        )
        providers = [_CountingStockProvider(name) for name in names]
        scene = _rich_mixed_scene()
        scene["provider_queries"] = {
            name: [f"orca variant {index:02d}" for index in range(12)] for name in names
        }

        self._build(providers, budget=None, scenes=[scene])

        self.assertEqual(self._sent(providers), DEFAULT)


class ShortlistIdentityTests(unittest.TestCase):
    """One record, one place on the shortlist.

    Every query of the ladder is searched separately, and a provider that answers two
    of them with the same asset used to put that asset on the shortlist twice. Measured
    on the LIVE-5 manifest: 6 distinct records in a top ten, one of them holding four
    places, so the depth a person sees on the review board is half of what it claims.
    """

    def _manifest(self, root: Path) -> dict:
        from src.news.asset_manager import build_assets_manifest

        fixture = root / "fixture.jpg"
        Image.new("RGB", (1080, 1920), (30, 60, 90)).save(fixture)
        provider = FakeStockProvider(image_fixture=fixture)
        scene = {
            "scene_id": "scene_001",
            "visual_type": "image",
            "primary_query": "solar panels on a roof",
            "alternative_queries": [
                "solar panels roof",
                "solar panels",
                "roof panels daylight",
                "solar array",
            ],
            "target_duration_sec": 4.0,
        }
        return build_assets_manifest(
            visual_plan={"scenes": [scene]},
            user_assets=[],
            media_index={"version": 1, "items": []},
            providers=[provider],
            dry_run=False,
            project_root=root / "project",
            project_id="shortlist_identity",
        )

    def test_one_record_takes_one_place_on_the_shortlist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest = self._manifest(Path(tmp))

        shortlist = manifest["scenes"][0]["ranked_candidates"]
        asset_ids = [item["asset_id"] for item in shortlist]

        self.assertTrue(asset_ids)
        self.assertEqual(len(asset_ids), len(set(asset_ids)))

    def test_the_surviving_copy_names_the_most_direct_query(self) -> None:
        """Which duplicate survives is not "the first one sent".

        A provider's planned queries do not arrive in order of directness - on the
        stored solar plan one provider's levels arrive as 1, 2, 3, 4, 1, 3 - so the
        first copy of an asset can be the one a level-4 fallback found while a level-1
        query returned the same asset later. Position still comes from the first
        occurrence, because pool order is the ranker's tie-break; the provenance the
        manifest reports comes from the most direct query that actually returned it.
        """
        from types import SimpleNamespace

        from src.news.asset_manifest_builder import AssetManifestBuilder

        state = SimpleNamespace(
            candidates=[
                {"asset_id": "roof", "fallback_level": 4, "search_query": "daylight"},
                {"asset_id": "farm", "fallback_level": 1, "search_query": "solar farm"},
                {"asset_id": "roof", "fallback_level": 1, "search_query": "solar panels"},
            ]
        )
        # The step reads nothing off ``self``, so the builder need not be constructed
        # with a project, providers and an index just to exercise one rule.
        AssetManifestBuilder._deduplicate_candidates(None, state)

        self.assertEqual([item["asset_id"] for item in state.candidates], ["roof", "farm"])
        self.assertEqual(state.candidates[0]["fallback_level"], 1)
        self.assertEqual(state.candidates[0]["search_query"], "solar panels")

    def test_the_review_board_shows_each_record_once(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest = self._manifest(Path(tmp))

        scene = manifest["scenes"][0]
        for field in ("candidates", "rejected_candidates"):
            ids = [item["asset_id"] for item in scene[field]]
            self.assertEqual(len(ids), len(set(ids)), field)


if __name__ == "__main__":
    unittest.main()
