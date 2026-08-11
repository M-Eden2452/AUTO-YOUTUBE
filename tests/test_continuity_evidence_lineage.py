"""Evidence lineage and authority of the continuity report (VA-NEW-01).

Protects one invariant: **what we asked a provider for is not evidence of what
the asset it returned actually shows.** A search query, a provider query, a
source URL, a source page and a file path are provenance -- they say where the
material came from and why we looked, never what is depicted.

Protects:

- continuity reads only canonical observed evidence, through the single owner
  ``src.assets.semantic_selection.evidence``: ``search_query``/``query``,
  ``source_url``, ``source_page`` and ``download_url`` can no longer establish an
  environment, while provider-authored ``title``/``description``/``tags`` still
  can;
- validated Vision tags stay continuity evidence through that same canonical
  path, so a future Vision activation needs no second route;
- continuity holds no ``missing_scenes`` authority. The scene loop
  (``_record_scene``) is the only owner of scene resolution, and a scene it
  resolved is not pushed back into ``missing_scenes`` by a cross-scene
  heuristic -- not even when that heuristic fires on legitimate metadata;
- manual/user authority and the strict/draft completion contract survive both
  changes, and genuinely unresolved scenes still reach ``missing_scenes``.

Does not prove:

- the quality of the ocean/desert/mountain inference itself, which is unchanged
  by this slice and remains a bounded English keyword heuristic;
- multi-slot assembly continuity: continuity read one ``selected_asset`` before
  this slice and still does, which this module characterizes rather than fixes;
- metadata evidence scoring (PLAN-9C-3) or media selection (PLAN-9C-2), which
  keep their own owning modules.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.assets.completion import MODE_DRAFT_COMPLETE
from src.assets.semantic_selection import check_continuity


def _asset(asset_id: str, **overrides) -> dict:
    """A candidate whose observed metadata deliberately names no environment."""
    data = {
        "schema_version": 1,
        "asset_id": asset_id,
        "provider": "pexels",
        "provider_asset_id": asset_id,
        "media_type": "video",
        "title": "Researchers at work",
        "description": "Two researchers checking equipment.",
        "tags": ["researcher", "equipment"],
        "tags_source": "provider",
        "search_query": "",
        "source_url": "https://example.test/a.mp4",
        "source_page": "https://example.test/a",
        "width": 1080,
        "height": 1920,
    }
    data.update(overrides)
    return data


def _entries(middle: dict) -> list[dict]:
    """Ocean, the asset under test, ocean -- the transition continuity judges."""
    ocean = {"title": "A whale in the open ocean", "description": "Whale surfacing.", "tags": ["whale", "ocean"]}
    return [
        {"scene_id": "scene_001", "selected_asset": _asset("ocean_a", **ocean)},
        {"scene_id": "scene_002", "selected_asset": middle},
        {"scene_id": "scene_003", "selected_asset": _asset("ocean_b", **ocean)},
    ]


class ContinuityEvidenceLineageTests(unittest.TestCase):
    """What continuity may read as proof of visual content."""

    def test_search_query_alone_cannot_establish_environment(self) -> None:
        # The retrieval intent said "desert"; the asset says nothing of the kind.
        report = check_continuity(
            _entries(_asset("neutral", search_query="desert canyon aerial"))
        )

        self.assertEqual(report["environments"], ["ocean", "unknown", "ocean"])
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["issues"], [])

    def test_provider_query_alias_alone_cannot_establish_environment(self) -> None:
        report = check_continuity(_entries(_asset("neutral", query="desert road")))

        self.assertEqual(report["environments"][1], "unknown")

    def test_provenance_and_location_alone_cannot_establish_environment(self) -> None:
        # Where a file lives is not what it depicts: a "desert" folder, a stock
        # page slug and a download path are all location data.
        for field in ("source_url", "source_page", "download_url", "local_path"):
            with self.subTest(field=field):
                report = check_continuity(
                    _entries(
                        _asset("neutral", **{field: "https://example.test/desert/clip-42.mp4"})
                    )
                )

                self.assertEqual(report["environments"][1], "unknown")
                self.assertEqual(report["status"], "passed")

    def test_provider_authored_metadata_still_establishes_environment(self) -> None:
        # The legitimate capability is preserved: a provider that really described
        # a desert is still believed, and the transition is still reported.
        report = check_continuity(
            _entries(
                _asset(
                    "described",
                    title="Sand dunes in the desert",
                    description="Wind moving over desert sand.",
                    tags=["desert", "dunes"],
                )
            )
        )

        self.assertEqual(report["environments"], ["ocean", "desert", "ocean"])
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["issues"][0]["scene_id"], "scene_002")

    def test_provider_tags_alone_still_establish_environment(self) -> None:
        report = check_continuity(_entries(_asset("tagged", tags=["desert", "canyon"])))

        self.assertEqual(report["environments"][1], "desert")

    def test_query_derived_tags_are_not_observed_evidence(self) -> None:
        # A provider that admits it synthesised its labels from our query is
        # quoting us back, not describing the asset.
        report = check_continuity(
            _entries(_asset("synth", tags=["desert"], tags_source="query_derived"))
        )

        self.assertEqual(report["environments"][1], "unknown")

    def test_metadata_field_that_is_the_query_repeated_back_is_not_evidence(self) -> None:
        report = check_continuity(
            _entries(_asset("echo", title="desert", search_query="desert"))
        )

        self.assertEqual(report["environments"][1], "unknown")

    def test_validated_vision_tags_remain_continuity_evidence(self) -> None:
        # Offline: no Vision call is made here. This fixes the future contract --
        # validated Vision evidence reaches continuity through the canonical
        # evidence owner and needs no second route.
        report = check_continuity(_entries(_asset("seen", vision_tags=["desert", "sand"])))

        self.assertEqual(report["environments"][1], "desert")


def _library_item(asset_id: str, words: list[str], local_path: Path, source_url: str) -> dict:
    return {
        "schema_version": 1,
        "id": asset_id,
        "type": "video",
        "provider": "local",
        "provider_asset_id": asset_id,
        "local_path": str(local_path),
        "title": " ".join(words),
        "description": " ".join(words),
        "keywords": list(words),
        "source_url": source_url,
        "width": 1080,
        "height": 1920,
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
            "provider_asset_id": asset_id,
            "source_page_url": source_url,
        },
    }


class ContinuityMissingSceneAuthorityTests(unittest.TestCase):
    """Continuity reports; the scene loop decides what is missing."""

    def _build(
        self,
        specs: list[tuple[str, str, list[str], str]],
        *,
        completion_mode: str = "",
        user_assets: list | None = None,
    ) -> dict:
        from src.news.asset_manager import build_assets_manifest

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            items = []
            scenes = []
            for scene_id, query, words, source_url in specs:
                path = root / f"{scene_id}.mp4"
                path.write_bytes(b"fake video")
                items.append(_library_item(f"{scene_id}_asset", words, path, source_url))
                scenes.append(
                    {"scene_id": scene_id, "visual_type": "video", "primary_query": query}
                )
            return build_assets_manifest(
                visual_plan={"scenes": scenes},
                user_assets=user_assets or [],
                media_index={"version": 1, "items": items},
                dry_run=False,
                completion_mode=completion_mode,
            )

    # Three resolved scenes whose middle asset is described honestly as a desert.
    _LEGITIMATE = [
        ("scene_001", "ocean whale", ["whale", "ocean"], "file://library/a.mp4"),
        ("scene_002", "desert scientists", ["scientists", "desert"], "file://library/b.mp4"),
        ("scene_003", "ocean whale", ["whale", "ocean"], "file://library/c.mp4"),
    ]

    # Same three scenes, but the middle asset only *lives* in a "desert" folder.
    _SELF_EVIDENCE = [
        ("scene_001", "ocean whale", ["whale", "ocean"], "file://library/a.mp4"),
        (
            "scene_002",
            "laboratory scientists",
            ["scientists", "laboratory"],
            "file://library/desert/b.mp4",
        ),
        ("scene_003", "ocean whale", ["whale", "ocean"], "file://library/c.mp4"),
    ]

    def _assert_all_resolved(self, manifest: dict) -> None:
        for scene in manifest["scenes"]:
            self.assertEqual(scene["resolution_status"], "resolved", scene["scene_id"])
            self.assertIsNotNone(scene["selected_asset"], scene["scene_id"])

    def test_provenance_self_evidence_does_not_reach_the_continuity_report(self) -> None:
        manifest = self._build(self._SELF_EVIDENCE)

        self._assert_all_resolved(manifest)
        self.assertEqual(manifest["continuity"]["environments"][1], "unknown")
        self.assertEqual(manifest["continuity"]["status"], "passed")
        self.assertEqual(manifest["missing_scenes"], [])
        self.assertEqual(manifest["visual_support"]["unresolved"], 0)

    def test_resolved_scene_survives_a_legitimate_continuity_failure(self) -> None:
        # The advisory capability is intact -- and it is advisory. The report still
        # says the transition is illogical; the resolved scene stays resolved.
        manifest = self._build(self._LEGITIMATE)

        self._assert_all_resolved(manifest)
        self.assertEqual(manifest["continuity"]["status"], "failed")
        self.assertEqual(
            manifest["continuity"]["issues"][0]["scene_id"], "scene_002"
        )
        self.assertEqual(manifest["missing_scenes"], [])
        self.assertEqual(manifest["visual_support"]["unresolved"], 0)

    def test_continuity_failure_adds_no_missing_scene_warning(self) -> None:
        manifest = self._build(self._LEGITIMATE)

        self.assertNotIn(
            "1 scene(s) still need allowed assets.", manifest["warnings"]
        )

    def test_continuity_never_changes_the_selected_asset(self) -> None:
        # VA-NEW-03 guard: continuity reports, it does not select.
        manifest = self._build(self._LEGITIMATE)

        self.assertEqual(
            [scene["selected_asset"]["asset_id"] for scene in manifest["scenes"]],
            ["scene_001_asset", "scene_002_asset", "scene_003_asset"],
        )
        self.assertEqual(
            [scene["selected_asset"]["media_type"] for scene in manifest["scenes"]],
            ["video", "video", "video"],
        )

    def test_genuinely_unresolved_scenes_still_reach_missing_scenes(self) -> None:
        # The fix removes continuity's authority, not the scene loop's. Material
        # that may not be rendered still leaves the scene honestly empty.
        from src.news.asset_manager import build_assets_manifest

        # Nothing in the library and no providers configured: offline by
        # construction, and every scene is honestly empty.
        manifest = build_assets_manifest(
            visual_plan={
                "scenes": [
                    {
                        "scene_id": f"scene_00{index}",
                        "visual_type": "video",
                        "primary_query": "ocean whale",
                    }
                    for index in range(1, 4)
                ]
            },
            user_assets=[],
            media_index={"version": 1, "items": []},
            dry_run=False,
        )

        for scene in manifest["scenes"]:
            self.assertIsNone(scene["selected_asset"], scene["scene_id"])
        self.assertEqual(
            [item["scene_id"] for item in manifest["missing_scenes"]],
            ["scene_001", "scene_002", "scene_003"],
        )

    def test_strict_completion_is_not_weakened(self) -> None:
        manifest = self._build(self._LEGITIMATE, completion_mode="strict")

        self._assert_all_resolved(manifest)
        self.assertEqual(manifest["missing_scenes"], [])
        self.assertEqual(manifest["completion"]["mode"], "strict")
        self.assertFalse(manifest["completion"]["draft_complete"])

    def test_draft_completion_records_only_scene_loop_reasons(self) -> None:
        # Draft completion has its own, stricter notion of an unusable scene and
        # keeps it: what must not appear is a continuity reason, because that
        # authority no longer exists. Draft is not promoted either way.
        manifest = self._build(self._LEGITIMATE, completion_mode=MODE_DRAFT_COMPLETE)

        reasons = {item["reason"] for item in manifest["missing_scenes"]}
        self.assertNotIn("illogical_ocean_desert_ocean_transition", reasons)
        self.assertFalse(any(reason.startswith("illogical_") for reason in reasons))
        self.assertFalse(manifest["completion"]["publish_ready"])

    def test_manual_authority_survives_continuity_self_evidence(self) -> None:
        from PIL import Image
        from src.news.asset_manager import build_assets_manifest

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # The owner's own file, stored in a folder named after the search.
            manual_dir = root / "desert"
            manual_dir.mkdir()
            manual_image = manual_dir / "scientists.jpg"
            Image.new("RGB", (1080, 1920), (30, 30, 30)).save(manual_image)

            manifest = build_assets_manifest(
                visual_plan={
                    "scenes": [
                        {
                            "scene_id": "scene_001",
                            "visual_type": "image",
                            "primary_query": "laboratory scientists",
                        }
                    ]
                },
                user_assets=[
                    {
                        "path": str(manual_image),
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
            self.assertEqual(manifest["missing_scenes"], [])


if __name__ == "__main__":
    unittest.main()
