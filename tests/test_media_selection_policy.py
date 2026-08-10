"""Contract of the canonical media-selection policy (PLAN-9C-2).

Protects:
- the five acceptance cases of PLAN-9C-2: a full-support image is not displaced
  by a partial-support video; PREFER_VIDEO may promote a video only among
  equally supported admissible candidates; AUTO never lets the media kind
  override the ranker's best; VIDEO_ONLY / IMAGE_ONLY are hard whitelists that
  abstain instead of silently substituting the other kind; the video preference
  cannot reach a candidate outside the declared review window;
- the LIVE-4 regressions: a strong relevant image (hummingbird, penguins) must
  not lose to a materially weaker video solely because ``media_kind == video``;
- rights safety: PREFER_VIDEO never resurrects a rights-blocked or
  review-required video;
- the wiring: ``select_best_with_video`` (builder, also the post-Vision
  reselection entry) and the facade patch-point ``_select_best_candidate``
  both delegate to the one canonical policy in
  ``src.assets.semantic_selection.media_policy``; draft completion receives
  that decision as its authoritative primary and cannot widen the media-policy
  review window or bypass the hard media-kind whitelist.

Does not prove:
- retrieval symmetry (``search_provider`` still asks for images only when the
  scene prefers an image) - that is the second PLAN-9C-2 sub-slice;
- metadata evidence quality (PLAN-9C-3), shortlist dedup / evaluated-set
  identity (PLAN-10C), download-walk redecision (PLAN-9A).
"""

from __future__ import annotations

import unittest
from unittest.mock import patch

from src.assets.semantic_selection import (
    SemanticScene,
    select_with_media_policy,
)
from src.assets.semantic_selection.decision import (
    SUPPORT_FULL,
    SUPPORT_PARTIAL,
)
from src.assets.semantic_selection.media_policy import (
    DEFAULT_REVIEW_WINDOW_SIZE,
    MEDIA_POLICY_VIDEO_PREFERENCE,
    MEDIA_POLICY_VIDEO_PREFERENCE_FALLBACK,
    candidate_media_kind,
    media_kind_restriction,
)
from src.assets.completion import ReuseLedger
from src.news.asset_scene_completion import complete_scene_assembly


def _scene(**overrides) -> SemanticScene:
    values = {
        "scene_id": "scene_003",
        "subject": ["hummingbird"],
        "action": ["hovering"],
        "environment": ["flowers"],
    }
    values.update(overrides)
    return SemanticScene(**values)


def _candidate(asset_id: str, media_type: str, title: str, **overrides) -> dict:
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
    data.update(overrides)
    return data


# Matches subject + action + environment: full support, the ranker's best.
def _full_image(asset_id: str = "img_full") -> dict:
    return _candidate(asset_id, "image", "Hummingbird hovering among flowers")


# Matches subject + environment but not the action: honest partial support.
def _partial_video(asset_id: str = "vid_partial") -> dict:
    return _candidate(asset_id, "video", "Hummingbird among colorful flowers")


# Matches subject + action (environment unmatched): same full class, lower score.
def _weaker_full_video(asset_id: str = "vid_full") -> dict:
    return _candidate(asset_id, "video", "Hummingbird hovering in slow motion")


def _complete_draft(
    candidates: list[dict],
    *,
    prefer_video: bool,
    allowed_media_kinds: list[str] | None = None,
    review_window_size: int = DEFAULT_REVIEW_WINDOW_SIZE,
) -> tuple[dict | None, dict | None, object, list[dict]]:
    """Exercise the canonical selection -> production completion boundary."""
    semantic_scene = _scene()
    selected, ranked = select_with_media_policy(
        semantic_scene,
        candidates,
        prefer_video=prefer_video,
        allowed_media_kinds=allowed_media_kinds,
        review_window_size=review_window_size,
        required_duration_sec=5.0,
    )
    completed, assembly, _attempts = complete_scene_assembly(
        scene={
            "scene_id": semantic_scene.scene_id,
            "allowed_media_kinds": list(allowed_media_kinds or []),
        },
        semantic_scene=semantic_scene,
        candidates=ranked,
        strict_selection=selected,
        scene_index=0,
        duration=5.0,
        reuse=ReuseLedger(),
        providers_by_name={},
        project_root=None,
        project_id="plan_9c_2_b1",
        media_index={"version": 1, "items": []},
        dry_run=True,
        project_pool=[],
        source_class="",
        download_selected=lambda **_kwargs: (None, []),
        ensure_decision=lambda asset, **_kwargs: asset,
        rank_provider_results=lambda *_args, **_kwargs: [],
        search_provider=lambda *_args, **_kwargs: [],
        allow_emergency_backdrop=False,
    )
    return selected, completed, assembly, ranked


class DraftCompletionMediaPolicyBoundaryTests(unittest.TestCase):
    """PLAN-9C-2-B1: completion may assemble, but not reselect media kind."""

    def test_full_image_survives_draft_completion_over_partial_video(self):
        """B1-1: the old ladder replaced this canonical image with a video."""
        selected, completed, assembly, ranked = _complete_draft(
            [_full_image(), _partial_video()],
            prefer_video=True,
        )

        by_id = {item["asset_id"]: item for item in ranked}
        self.assertEqual(by_id["img_full"]["support_status"], SUPPORT_FULL)
        self.assertEqual(by_id["vid_partial"]["support_status"], SUPPORT_PARTIAL)
        self.assertEqual(selected["asset_id"], "img_full")
        self.assertEqual(completed["asset_id"], "img_full")
        self.assertEqual(assembly.primary_asset["asset_id"], "img_full")
        self.assertNotIn("video_first:video_pool", assembly.ladder_trace)

    def test_image_whitelist_survives_draft_completion(self):
        """B1-2: a video cannot bypass the canonical hard whitelist."""
        selected, completed, assembly, _ranked = _complete_draft(
            [_full_image(), _weaker_full_video()],
            prefer_video=True,
            allowed_media_kinds=["image"],
        )

        self.assertEqual(selected["asset_id"], "img_full")
        self.assertEqual(completed["asset_id"], "img_full")
        self.assertEqual(assembly.primary_asset["media_type"], "image")

    def test_competitive_video_preference_survives_draft_completion(self):
        """B1-3: repair must not turn the bounded preference into a no-op."""
        selected, completed, assembly, _ranked = _complete_draft(
            [_full_image(), _weaker_full_video()],
            prefer_video=True,
        )

        self.assertEqual(selected["asset_id"], "vid_full")
        self.assertEqual(completed["asset_id"], "vid_full")
        self.assertEqual(assembly.primary_asset["media_type"], "video")

    def test_video_outside_review_window_is_not_resurrected_by_completion(self):
        """B1-4: completion cannot widen the evaluated media-policy boundary."""
        images = [
            _candidate(f"img_{index}", "image", "Hummingbird hovering among flowers")
            for index in range(DEFAULT_REVIEW_WINDOW_SIZE)
        ]
        selected, completed, assembly, ranked = _complete_draft(
            [*images, _weaker_full_video()],
            prefer_video=True,
        )

        video_rank = next(
            index for index, item in enumerate(ranked) if item["asset_id"] == "vid_full"
        )
        self.assertGreaterEqual(video_rank, DEFAULT_REVIEW_WINDOW_SIZE)
        self.assertEqual(selected["asset_id"], "img_0")
        self.assertEqual(completed["asset_id"], "img_0")
        self.assertEqual(assembly.primary_asset["asset_id"], "img_0")

    def test_video_only_abstention_is_not_replaced_with_an_image(self):
        """The opposite hard-whitelist direction remains fail-closed too."""
        selected, completed, assembly, _ranked = _complete_draft(
            [_full_image()],
            prefer_video=False,
            allowed_media_kinds=["video"],
        )

        self.assertIsNone(selected)
        self.assertIsNone(completed)
        self.assertFalse(assembly.slots)


class ProductionBuilderCompletionWiringTests(unittest.TestCase):
    """M3: the production builder hands completion the canonical decision."""

    def test_builder_passes_selected_candidate_as_authoritative_primary(self):
        from src.news.asset_manifest_builder import AssetManifestBuilder, SceneBuildState

        semantic_scene = _scene()
        selected, ranked = select_with_media_policy(
            semantic_scene,
            [_full_image(), _weaker_full_video()],
            prefer_video=True,
            allowed_media_kinds=["image"],
            required_duration_sec=5.0,
        )
        builder = AssetManifestBuilder(
            visual_plan={"scenes": []},
            user_assets=[],
            media_index={"version": 1, "items": []},
            providers=[],
            dry_run=True,
            channel="nature_science_news_ru",
            allow_generated_fallback=False,
            asset_selection={"visual_preview": {"enabled": False}},
            project_root=None,
            project_id="plan_9c_2_b1",
            max_download_attempts=1,
            completion_mode="draft_complete",
            reuse_ledger=None,
            allow_infographic_fallback=False,
            allow_emergency_backdrop=False,
            prefer_video=True,
            minimum_video_clips=0,
            minimum_video_duration_ratio=0.0,
        )
        state = SceneBuildState(
            scene={
                "scene_id": semantic_scene.scene_id,
                "allowed_media_kinds": ["image"],
            },
            semantic_scene=semantic_scene,
            candidates=ranked,
            scene_provider_attempts=[],
            provider_capabilities={},
            routing_decision={},
            query_plan=None,
            source_class="",
            required_duration=5.0,
            user_ranked=[],
            selected=selected,
        )

        with patch(
            "src.news.asset_manifest_builder.ensure_selected_asset_downloaded",
            return_value=(selected, []),
        ), patch(
            "src.news.asset_manifest_builder.complete_scene_assembly",
            wraps=complete_scene_assembly,
        ) as completion:
            builder._download_and_complete(state)

        kwargs = completion.call_args.kwargs
        self.assertIs(kwargs["strict_selection"], selected)
        self.assertNotIn("prefer_video", kwargs)
        self.assertEqual(state.selected["asset_id"], "img_full")
        self.assertEqual(state.assembly.primary_asset["asset_id"], "img_full")


class MediaPolicyAcceptanceCaseTests(unittest.TestCase):
    """The five PLAN-9C-2 acceptance cases, stated as behaviour."""

    def test_full_support_image_is_not_displaced_by_partial_support_video(self):
        """CASE 1: a candidate may not win solely for being a video."""
        selected, ranked = select_with_media_policy(
            _scene(),
            [_full_image(), _partial_video()],
            prefer_video=True,
            required_duration_sec=5.0,
        )
        by_id = {item["asset_id"]: item for item in ranked}
        self.assertEqual(by_id["img_full"]["support_status"], SUPPORT_FULL)
        self.assertEqual(by_id["vid_partial"]["support_status"], SUPPORT_PARTIAL)
        self.assertFalse(by_id["vid_partial"]["rejected"])
        self.assertEqual(selected["asset_id"], "img_full")

    def test_prefer_video_promotes_video_among_equally_supported_candidates(self):
        """CASE 2: among full/full candidates the bounded preference may pick video."""
        selected, ranked = select_with_media_policy(
            _scene(),
            [_full_image(), _weaker_full_video()],
            prefer_video=True,
            required_duration_sec=5.0,
        )
        by_id = {item["asset_id"]: item for item in ranked}
        self.assertEqual(by_id["img_full"]["support_status"], SUPPORT_FULL)
        self.assertEqual(by_id["vid_full"]["support_status"], SUPPORT_FULL)
        self.assertEqual(selected["asset_id"], "vid_full")

    def test_auto_keeps_the_rankers_best_regardless_of_media_kind(self):
        """CASE 3: without the preference the media kind decides nothing."""
        selected, _ranked = select_with_media_policy(
            _scene(),
            [_full_image(), _weaker_full_video()],
            prefer_video=False,
            required_duration_sec=5.0,
        )
        self.assertEqual(selected["asset_id"], "img_full")

    def test_video_only_abstains_instead_of_substituting_an_image(self):
        """CASE 4: a hard whitelist abstains; it never hides the constraint."""
        selected, ranked = select_with_media_policy(
            _scene(),
            [_full_image()],
            prefer_video=False,
            allowed_media_kinds=["video"],
            required_duration_sec=5.0,
        )
        self.assertIsNone(selected)
        self.assertFalse(ranked[0]["rejected"])

    def test_image_only_abstains_instead_of_substituting_a_video(self):
        selected, _ranked = select_with_media_policy(
            _scene(),
            [_weaker_full_video()],
            prefer_video=False,
            allowed_media_kinds=["image"],
            required_duration_sec=5.0,
        )
        self.assertIsNone(selected)

    def test_image_only_is_stronger_than_the_video_preference(self):
        """The whitelist sits above the soft preference, never below it."""
        selected, _ranked = select_with_media_policy(
            _scene(),
            [_full_image(), _weaker_full_video()],
            prefer_video=True,
            allowed_media_kinds=["image"],
            required_duration_sec=5.0,
        )
        self.assertEqual(selected["asset_id"], "img_full")

    def test_kind_whitelist_selects_the_best_admissible_candidate(self):
        """VIDEO_ONLY with an admissible video selects it - no needless abstain."""
        selected, _ranked = select_with_media_policy(
            _scene(),
            [_full_image(), _weaker_full_video()],
            prefer_video=False,
            allowed_media_kinds=["video"],
            required_duration_sec=5.0,
        )
        self.assertEqual(selected["asset_id"], "vid_full")

    def test_video_preference_cannot_reach_outside_the_review_window(self):
        """CASE 5: what nobody evaluated cannot silently become the winner."""
        images = [
            _candidate(f"img_{index}", "image", "Hummingbird hovering among flowers")
            for index in range(DEFAULT_REVIEW_WINDOW_SIZE)
        ]
        video = _weaker_full_video()
        selected, ranked = select_with_media_policy(
            _scene(),
            [*images, video],
            prefer_video=True,
            required_duration_sec=5.0,
        )
        video_rank = next(
            index
            for index, item in enumerate(ranked)
            if item["asset_id"] == "vid_full"
        )
        self.assertGreaterEqual(video_rank, DEFAULT_REVIEW_WINDOW_SIZE)
        self.assertEqual(selected["asset_id"], "img_0")

    def test_a_wider_review_window_admits_the_same_video(self):
        """The boundary is the declared window, not hostility to video."""
        images = [
            _candidate(f"img_{index}", "image", "Hummingbird hovering among flowers")
            for index in range(DEFAULT_REVIEW_WINDOW_SIZE)
        ]
        selected, _ranked = select_with_media_policy(
            _scene(),
            [*images, _weaker_full_video()],
            prefer_video=True,
            review_window_size=DEFAULT_REVIEW_WINDOW_SIZE + 1,
            required_duration_sec=5.0,
        )
        self.assertEqual(selected["asset_id"], "vid_full")


class Live4RegressionTests(unittest.TestCase):
    """The two selections LIVE-4 got wrong, restated on synthetic candidates.

    LIVE-4 scene_003 selected an Internet Archive video (65.75, outside the
    preview window) over the rank-1 hummingbird image (80.72); scene_004
    selected a zoo video (70.0) over snow images (80.0). Both persisted
    manifests live in ``projects/2026-08-09_diagnostic-ru-semantic-live-4``;
    the fixtures here reproduce the decision shape without depending on that
    mutable directory or on real provider IDs.
    """

    def test_hummingbird_image_must_not_lose_to_materially_weaker_video(self):
        selected, _ranked = select_with_media_policy(
            _scene(),
            [_full_image("hummingbird_frame"), _partial_video("archive_series_clip")],
            prefer_video=True,
            required_duration_sec=5.0,
        )
        self.assertEqual(selected["asset_id"], "hummingbird_frame")

    def test_penguin_snow_image_must_not_lose_to_zoo_video_outside_window(self):
        scene = SemanticScene(
            scene_id="scene_004",
            subject=["penguin"],
            action=["walking"],
            environment=["snow"],
        )
        snow_images = [
            _candidate(f"snow_{index}", "image", "Penguin walking in the snow")
            for index in range(DEFAULT_REVIEW_WINDOW_SIZE)
        ]
        zoo_video = _candidate("zoo_clip", "video", "Penguin walking at the zoo")
        selected, ranked = select_with_media_policy(
            scene,
            [*snow_images, zoo_video],
            prefer_video=True,
            required_duration_sec=5.0,
        )
        zoo_rank = next(
            index for index, item in enumerate(ranked) if item["asset_id"] == "zoo_clip"
        )
        self.assertGreaterEqual(zoo_rank, DEFAULT_REVIEW_WINDOW_SIZE)
        self.assertEqual(selected["asset_id"], "snow_0")


class MediaPolicySafetyTests(unittest.TestCase):
    def test_prefer_video_does_not_resurrect_a_rights_blocked_video(self):
        blocked_video = _candidate(
            "vid_blocked",
            "video",
            "Hummingbird hovering among flowers",
            rights_status="editorial_review_required",
            allowed_for_render=False,
            review_required=True,
        )
        selected, ranked = select_with_media_policy(
            _scene(),
            [_full_image(), blocked_video],
            prefer_video=True,
            required_duration_sec=5.0,
        )
        by_id = {item["asset_id"]: item for item in ranked}
        self.assertTrue(by_id["vid_blocked"]["rejected"])
        self.assertEqual(selected["asset_id"], "img_full")

    def test_policy_preserves_the_rankers_abstention(self):
        blocked_video = _candidate(
            "vid_blocked",
            "video",
            "Hummingbird hovering among flowers",
            rights_status="legacy_unknown",
            allowed_for_render=False,
            review_required=True,
        )
        selected, _ranked = select_with_media_policy(
            _scene(),
            [blocked_video],
            prefer_video=True,
            required_duration_sec=5.0,
        )
        self.assertIsNone(selected)


class MediaPolicyTraceTests(unittest.TestCase):
    def test_a_promoted_video_records_the_policy_branch(self):
        selected, _ranked = select_with_media_policy(
            _scene(),
            [_full_image(), _weaker_full_video()],
            prefer_video=True,
            required_duration_sec=5.0,
        )
        self.assertEqual(selected["selected_by"], MEDIA_POLICY_VIDEO_PREFERENCE)

    def test_a_kept_best_records_that_no_video_was_competitive(self):
        selected, _ranked = select_with_media_policy(
            _scene(),
            [_full_image(), _partial_video()],
            prefer_video=True,
            required_duration_sec=5.0,
        )
        self.assertEqual(
            selected["selected_by"], MEDIA_POLICY_VIDEO_PREFERENCE_FALLBACK
        )

    def test_auto_leaves_the_rankers_record_untouched(self):
        selected, _ranked = select_with_media_policy(
            _scene(),
            [_full_image(), _weaker_full_video()],
            prefer_video=False,
            required_duration_sec=5.0,
        )
        self.assertNotIn("selected_by", selected)


class MediaKindPrimitiveTests(unittest.TestCase):
    def test_candidate_media_kind_reads_declared_type_first(self):
        self.assertEqual(candidate_media_kind({"media_type": "video"}), "video")
        self.assertEqual(candidate_media_kind({"type": "photo"}), "image")
        self.assertEqual(
            candidate_media_kind({"path": "clip.mp4"}), "video"
        )
        self.assertEqual(candidate_media_kind({}), "unknown")

    def test_restriction_exists_only_for_a_single_routable_kind(self):
        self.assertEqual(media_kind_restriction(["video"]), "video")
        self.assertEqual(media_kind_restriction(["image"]), "image")
        self.assertEqual(media_kind_restriction(["video", "image"]), "")
        self.assertEqual(media_kind_restriction([]), "")
        self.assertEqual(media_kind_restriction(None), "")
        # Kinds the pipeline cannot route today restrict nothing, exactly like
        # the search layer's raw membership checks.
        self.assertEqual(media_kind_restriction(["animated_image"]), "")


class CanonicalWiringTests(unittest.TestCase):
    """Both production entry points are thin delegations to the one policy."""

    def test_builder_wrapper_delegates_to_the_canonical_policy(self):
        from src.news.asset_manifest_builder import select_best_with_video

        sentinel = (None, [])
        with patch(
            "src.news.asset_manifest_builder.select_with_media_policy",
            return_value=sentinel,
        ) as delegate:
            result = select_best_with_video(
                _scene(),
                [],
                prefer_video=True,
                allowed_media_kinds=["video"],
                review_window_size=7,
                required_duration_sec=5.0,
            )
        self.assertIs(result, sentinel)
        self.assertEqual(delegate.call_count, 1)
        kwargs = delegate.call_args.kwargs
        self.assertTrue(kwargs["prefer_video"])
        self.assertEqual(kwargs["allowed_media_kinds"], ["video"])
        self.assertEqual(kwargs["review_window_size"], 7)
        self.assertEqual(kwargs["required_duration_sec"], 5.0)

    def test_facade_duplicate_delegates_to_the_canonical_policy(self):
        from src.news.asset_manager import _select_best_candidate

        sentinel = (None, [])
        with patch(
            "src.news.asset_manager.select_with_media_policy",
            return_value=sentinel,
        ) as delegate:
            result = _select_best_candidate(
                _scene(),
                [],
                prefer_video=True,
                required_duration_sec=5.0,
            )
        self.assertIs(result, sentinel)
        self.assertEqual(delegate.call_count, 1)

    def test_facade_duplicate_applies_the_bounded_preference(self):
        """The old facade took the first non-rejected video at any rank."""
        from src.news.asset_manager import _select_best_candidate

        selected, _ranked = _select_best_candidate(
            _scene(),
            [_full_image(), _partial_video()],
            prefer_video=True,
            required_duration_sec=5.0,
        )
        self.assertEqual(selected["asset_id"], "img_full")


if __name__ == "__main__":
    unittest.main()
