from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from typing import Any

from PIL import Image


class VisualPreviewIntegrationTests(unittest.TestCase):
    def test_neighbor_scene_duplicate_penalty(self) -> None:
        from src.assets.review_bundle import compute_repetition_penalties

        candidate = {"asset_id": "asset_a", "source_page_url": "https://source/a", "checksum_sha256": "abc"}
        penalties = compute_repetition_penalties(
            candidate,
            neighbor_assets=[{"asset_id": "asset_a", "source_page_url": "https://source/a", "checksum_sha256": "abc"}],
            project_assets=[],
        )

        self.assertGreater(penalties["duplicate_penalty"], 0)
        self.assertIn("same_asset_id", penalties["reason"])

    def test_project_level_repetition_penalty(self) -> None:
        from src.assets.review_bundle import compute_repetition_penalties

        candidate = {"asset_id": "asset_a", "source_page_url": "https://source/a", "checksum_sha256": "abc"}
        penalties = compute_repetition_penalties(
            candidate,
            neighbor_assets=[],
            project_assets=[
                {"asset_id": "old_1", "source_page_url": "https://source/a"},
                {"asset_id": "old_2", "source_page_url": "https://source/a"},
            ],
        )

        self.assertEqual(penalties["project_repetition_count"], 2)
        self.assertGreater(penalties["neighbor_similarity_penalty"], 0)

    def test_review_bundle_generation(self) -> None:
        from src.assets.review_bundle import create_scene_review_bundle

        scene = {"scene_id": "scene_001", "primary_query": "ocean science", "visual_type": "image", "target_duration_sec": 4}
        analyses = [_analysis("a1", technical=80), _analysis("a2", technical=60)]

        bundle = create_scene_review_bundle(
            project_id="project_001",
            scene=scene,
            semantic_scene={"visual_priority": "environment"},
            metadata_queries=[{"query": "ocean science"}],
            provider_routing={"ordered_providers": ["fake"]},
            candidates=[_candidate("a1"), _candidate("a2")],
            analyses=analyses,
            selected_candidate_id="a1",
            target_aspect_ratio="9:16",
        )

        self.assertEqual(bundle.project_id, "project_001")
        self.assertEqual(bundle.scene_id, "scene_001")
        self.assertEqual(len(bundle.shortlist), 2)
        self.assertEqual(bundle.selected_candidate["asset_id"], "a1")

    def test_review_bundle_schema_has_required_fields(self) -> None:
        from src.assets.review_bundle import REVIEW_BUNDLE_REQUIRED_FIELDS

        for field in (
            "project_id",
            "scene_id",
            "scene_text",
            "semantic_scene",
            "target_aspect_ratio",
            "metadata_queries",
            "provider_routing",
            "shortlist",
            "selected_candidate",
            "alternatives",
            "manual_fallback_status",
        ):
            self.assertIn(field, REVIEW_BUNDLE_REQUIRED_FIELDS)

    def test_html_board_generation(self) -> None:
        from src.assets.review_bundle import create_scene_review_bundle, write_review_bundle

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            frame = root / "frame.jpg"
            Image.new("RGB", (100, 140), (30, 80, 120)).save(frame)
            bundle = create_scene_review_bundle(
                project_id="project_001",
                scene={"scene_id": "scene_001", "primary_query": "ocean", "visual_type": "image"},
                semantic_scene={},
                metadata_queries=[],
                provider_routing={},
                candidates=[_candidate("a1")],
                analyses=[_analysis("a1", frame_path=frame)],
                selected_candidate_id="a1",
                target_aspect_ratio="9:16",
            )

            result = write_review_bundle(root, [bundle])

            self.assertTrue(Path(result["json_path"]).is_file())
            self.assertTrue(Path(result["html_path"]).is_file())
            html = Path(result["html_path"]).read_text(encoding="utf-8")
            self.assertIn("scene_001", html)
            self.assertIn("fake", html)

    def test_html_uses_relative_paths(self) -> None:
        from src.assets.review_bundle import create_scene_review_bundle, write_review_bundle

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            frame = root / "assets" / "previews" / "frame.jpg"
            frame.parent.mkdir(parents=True)
            Image.new("RGB", (100, 140), (30, 80, 120)).save(frame)
            bundle = create_scene_review_bundle(
                project_id="project_001",
                scene={"scene_id": "scene_001", "primary_query": "ocean", "visual_type": "image"},
                semantic_scene={},
                metadata_queries=[],
                provider_routing={},
                candidates=[_candidate("a1")],
                analyses=[_analysis("a1", frame_path=frame)],
                selected_candidate_id="a1",
                target_aspect_ratio="9:16",
            )

            result = write_review_bundle(root, [bundle])
            html = Path(result["html_path"]).read_text(encoding="utf-8")

            self.assertIn("assets/previews/frame.jpg", html.replace("\\", "/"))
            self.assertNotIn(str(root), html)

    def test_html_contains_no_secrets(self) -> None:
        from src.assets.review_bundle import create_scene_review_bundle, write_review_bundle

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = create_scene_review_bundle(
                project_id="project_001",
                scene={"scene_id": "scene_001", "primary_query": "ocean", "visual_type": "image"},
                semantic_scene={},
                metadata_queries=[],
                provider_routing={},
                candidates=[{**_candidate("a1"), "raw_metadata": {"api_key": "SECRET_TOKEN_VALUE"}}],
                analyses=[_analysis("a1")],
                selected_candidate_id="a1",
                target_aspect_ratio="9:16",
            )

            result = write_review_bundle(root, [bundle])
            html = Path(result["html_path"]).read_text(encoding="utf-8")

            self.assertNotIn("SECRET_TOKEN_VALUE", html)
            self.assertNotIn("api_key", html.lower())

    def test_html_does_not_expose_envato_proof(self) -> None:
        from src.assets.review_bundle import create_scene_review_bundle, write_review_bundle

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = create_scene_review_bundle(
                project_id="project_001",
                scene={"scene_id": "scene_001", "primary_query": "premium footage", "visual_type": "video"},
                semantic_scene={},
                metadata_queries=[],
                provider_routing={},
                candidates=[
                    {
                        **_candidate("envato_1", provider="envato_manual"),
                        "raw_metadata": {"license_proof_reference": str(root / "metadata" / "licenses" / "certificate.txt")},
                    }
                ],
                analyses=[_analysis("envato_1")],
                selected_candidate_id="envato_1",
                target_aspect_ratio="9:16",
            )

            result = write_review_bundle(root, [bundle])
            html = Path(result["html_path"]).read_text(encoding="utf-8")

            self.assertNotIn("certificate.txt", html)
            self.assertNotIn("license_proof_reference", html)

    def test_technical_rerank_disabled_by_default(self) -> None:
        from src.assets.review_bundle import select_candidate_after_review

        candidates = [_candidate("metadata_winner"), _candidate("technical_winner")]
        analyses = [_analysis("metadata_winner", technical=20), _analysis("technical_winner", technical=95)]

        selected = select_candidate_after_review(candidates, analyses, metadata_selected_id="metadata_winner", technical_rerank=False)

        self.assertEqual(selected["asset_id"], "metadata_winner")

    def test_technical_rerank_works_when_enabled(self) -> None:
        from src.assets.review_bundle import select_candidate_after_review

        candidates = [_candidate("metadata_winner"), _candidate("technical_winner")]
        analyses = [_analysis("metadata_winner", technical=20), _analysis("technical_winner", technical=95)]

        selected = select_candidate_after_review(candidates, analyses, metadata_selected_id="metadata_winner", technical_rerank=True)

        self.assertEqual(selected["asset_id"], "technical_winner")

    def test_failed_preview_falls_back_to_metadata_ranking(self) -> None:
        from src.assets.review_bundle import select_candidate_after_review

        candidates = [_candidate("metadata_winner"), _candidate("technical_winner")]
        analyses = [
            _analysis("metadata_winner", status="failed", technical=0),
            _analysis("technical_winner", status="passed", technical=90),
        ]

        selected = select_candidate_after_review(candidates, analyses, metadata_selected_id="metadata_winner", technical_rerank=False)

        self.assertEqual(selected["asset_id"], "metadata_winner")

    def test_only_shortlisted_previews_are_fetched(self) -> None:
        from src.assets.visual_preview import VisualPreviewRequest, prepare_candidate_preview_analyses

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            preview = root / "preview.jpg"
            Image.new("RGB", (320, 480), (25, 65, 110)).save(preview)
            provider = CountingPreviewProvider(preview_path=preview)
            candidates = [_candidate(f"a{i}", preview_url=f"https://fake.local/{i}.jpg") for i in range(8)]
            request = VisualPreviewRequest(project_id="p", scene_id="s", top_k=3, project_root=str(root), offline=False)

            analyses = prepare_candidate_preview_analyses(candidates, providers_by_name={"fake": provider}, request=request)

            self.assertEqual(len(analyses), 3)
            self.assertEqual(provider.preview_calls, 3)

    def test_envato_remote_preview_is_not_fetched(self) -> None:
        from src.assets.models import AssetCandidate
        from src.assets.visual_preview import VisualPreviewRequest, prepare_candidate_preview_analyses

        candidate = AssetCandidate(
            asset_id="envato_remote",
            provider="envato_manual",
            provider_asset_id="item_1",
            media_type="video",
            preview_url="https://elements.envato.com/remote-preview.mp4",
            source_page_url="https://elements.envato.com/item_1",
        ).to_manifest_dict()

        with tempfile.TemporaryDirectory() as tmp:
            request = VisualPreviewRequest(project_id="p", scene_id="s", top_k=1, project_root=tmp, offline=False)
            analyses = prepare_candidate_preview_analyses([candidate], providers_by_name={}, request=request)

        self.assertEqual(analyses[0]["analysis_status"], "failed")
        self.assertIn("envato_remote_preview_disabled", analyses[0]["preview"]["fallback_reason"])

    def test_imported_envato_local_file_can_be_analysed(self) -> None:
        from src.assets.visual_preview import VisualPreviewRequest, prepare_candidate_preview_analyses

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            local = root / "imported.jpg"
            Image.new("RGB", (1080, 1920), (80, 100, 130)).save(local)
            candidate = {**_candidate("envato_local", provider="envato_manual"), "local_path": str(local), "path": str(local)}
            request = VisualPreviewRequest(project_id="p", scene_id="s", top_k=1, project_root=str(root), offline=True)

            analyses = prepare_candidate_preview_analyses([candidate], providers_by_name={}, request=request)

            self.assertEqual(analyses[0]["analysis_status"], "passed")
            self.assertEqual(analyses[0]["preview"]["preview_media_type"], "image")

    def test_local_preview_cache_reuses_unchanged_source_bytes(self) -> None:
        from src.assets.visual_preview import VisualPreviewRequest, prepare_candidate_preview_analyses

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "manual.png"
            _write_fixed_size_image(source, (220, 20, 20))
            candidate = {
                **_candidate("manual_asset", provider="user"),
                "local_path": str(source),
                "path": str(source),
                "checksum_sha256": "declared-provenance-is-not-source-identity",
            }
            request = VisualPreviewRequest(project_id="p", scene_id="s", top_k=1, project_root=str(root), offline=True)

            first = prepare_candidate_preview_analyses([candidate], providers_by_name={}, request=request)[0]
            second = prepare_candidate_preview_analyses([candidate], providers_by_name={}, request=request)[0]

            self.assertEqual(first["preview"]["cache_key"], second["preview"]["cache_key"])
            self.assertEqual(first["preview"]["cache_status"], "stored")
            self.assertEqual(second["preview"]["cache_status"], "hit")

    def test_local_preview_cache_tracks_current_bytes_at_same_path(self) -> None:
        from src.assets.visual_preview import VisualPreviewRequest, prepare_candidate_preview_analyses

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "manual.png"
            _write_fixed_size_image(source, (220, 20, 20))
            source_stat = source.stat()
            candidate = {
                **_candidate("manual_asset", provider="user"),
                "local_path": str(source),
                "path": str(source),
                "checksum_sha256": "unchanged-stale-provenance",
            }
            request = VisualPreviewRequest(project_id="p", scene_id="s", top_k=1, project_root=str(root), offline=True)

            first = prepare_candidate_preview_analyses([candidate], providers_by_name={}, request=request)[0]
            _write_fixed_size_image(source, (20, 20, 220))
            os.utime(source, ns=(source_stat.st_atime_ns, source_stat.st_mtime_ns))
            self.assertEqual(source.stat().st_size, source_stat.st_size)
            self.assertEqual(source.stat().st_mtime_ns, source_stat.st_mtime_ns)

            second = prepare_candidate_preview_analyses([candidate], providers_by_name={}, request=request)[0]

            self.assertNotEqual(first["preview"]["cache_key"], second["preview"]["cache_key"])
            self.assertEqual(second["preview"]["cache_status"], "stored")
            with Image.open(second["preview"]["local_path"]) as image:
                red, _green, blue = image.convert("RGB").getpixel((image.width // 2, image.height // 2))
            self.assertGreater(blue, red)

    def test_missing_local_source_does_not_use_stale_preview(self) -> None:
        from src.assets.visual_preview import VisualPreviewRequest, prepare_candidate_preview_analyses

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "manual.png"
            _write_fixed_size_image(source, (220, 20, 20))
            candidate = {**_candidate("manual_asset", provider="user"), "local_path": str(source), "path": str(source)}
            request = VisualPreviewRequest(project_id="p", scene_id="s", top_k=1, project_root=str(root), offline=True)
            first = prepare_candidate_preview_analyses([candidate], providers_by_name={}, request=request)[0]
            source.unlink()

            second = prepare_candidate_preview_analyses([candidate], providers_by_name={}, request=request)[0]

            self.assertEqual(first["analysis_status"], "passed")
            self.assertEqual(second["analysis_status"], "failed")
            self.assertFalse(second["sampled_frames"])

    def test_local_video_preview_cache_tracks_duration_transform(self) -> None:
        from src.assets.models import AssetCandidate
        from src.assets.visual_preview import VisualPreviewRequest, resolve_candidate_preview

        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "manual.mp4"
            source.write_bytes(b"stable-local-video-source")
            candidate = AssetCandidate.from_dict(
                {
                    **_candidate("manual_video", provider="user"),
                    "media_type": "video",
                    "type": "video",
                    "local_path": str(source),
                    "path": str(source),
                }
            )
            request = VisualPreviewRequest(project_id="p", scene_id="s", offline=True)

            longer = resolve_candidate_preview(
                candidate,
                provider=None,
                request=request,
                video_preview_max_duration_sec=8.0,
            )
            shorter = resolve_candidate_preview(
                candidate,
                provider=None,
                request=request,
                video_preview_max_duration_sec=4.0,
            )

            self.assertNotEqual(longer.cache_key, shorter.cache_key)

    def test_provider_specific_preview_selection(self) -> None:
        from src.assets.models import AssetCandidate
        from src.assets.visual_preview import VisualPreviewRequest, resolve_candidate_preview

        request = VisualPreviewRequest(project_id="p", scene_id="s", top_k=1)
        ia = AssetCandidate(asset_id="ia", provider="internet_archive", provider_asset_id="movie_1", media_type="video", source_page_url="https://archive.org/details/movie_1")
        pixabay = AssetCandidate(
            asset_id="pixabay",
            provider="pixabay",
            provider_asset_id="77",
            media_type="video",
            raw_metadata={"pixabay": {"videos": {"medium": {"url": "https://cdn/medium.mp4", "width": 640, "height": 360}}}},
        )

        ia_preview = resolve_candidate_preview(ia, provider=None, request=request)
        pixabay_preview = resolve_candidate_preview(pixabay, provider=None, request=request)

        self.assertEqual(ia_preview.preview_source_url, "https://archive.org/services/img/movie_1")
        self.assertEqual(pixabay_preview.preview_source_url, "https://cdn/medium.mp4")

    def test_offline_mode_uses_cache_or_local_only(self) -> None:
        from src.assets.visual_preview import VisualPreviewRequest, prepare_candidate_preview_analyses

        candidate = _candidate("remote_only", preview_url="https://fake.local/remote.jpg")
        with tempfile.TemporaryDirectory() as tmp:
            request = VisualPreviewRequest(project_id="p", scene_id="s", top_k=1, project_root=tmp, offline=True)
            analyses = prepare_candidate_preview_analyses([candidate], providers_by_name={}, request=request)

        self.assertEqual(analyses[0]["analysis_status"], "failed")
        self.assertIn("offline_no_cache", analyses[0]["preview"]["fallback_reason"])

    def test_network_guard_remains_active(self) -> None:
        from tests.network_guard import live_tests_enabled

        self.assertFalse(live_tests_enabled())


class CountingPreviewProvider:
    name = "fake"

    def __init__(self, *, preview_path: Path) -> None:
        self.preview_path = preview_path
        self.preview_calls = 0

    def get_preview(self, candidate: Any) -> Any:
        from src.assets.provider_contract import AssetPreview

        self.preview_calls += 1
        return AssetPreview(candidate_id=candidate.asset_id, local_path=str(self.preview_path), width=320, height=480)


def _candidate(asset_id: str, *, provider: str = "fake", preview_url: str = "") -> dict[str, Any]:
    return {
        "asset_id": asset_id,
        "provider": provider,
        "provider_asset_id": asset_id,
        "media_type": "image",
        "type": "image",
        "title": f"Candidate {asset_id}",
        "description": "ocean science",
        "tags": ["ocean", "science"],
        "source_page_url": f"https://fake.local/{asset_id}",
        "source_page": f"https://fake.local/{asset_id}",
        "preview_url": preview_url,
        "author_name": "Fake Author",
        "license": {"license_name": "fake_test_license", "allowed_for_render": True, "review_required": False},
        "allowed_for_render": True,
        "review_required": False,
        "final_score": 50.0,
        "total_score": 50.0,
    }


def _write_fixed_size_image(path: Path, color: tuple[int, int, int]) -> None:
    # BMP has a fixed byte size for fixed dimensions, independent of pixel values.
    # The .png suffix keeps this on the active image-preview path while Pillow reads
    # the actual encoded format. This lets the characterization defeat path+stat keys.
    Image.new("RGB", (96, 128), color).save(path, format="BMP")


def _analysis(asset_id: str, *, status: str = "passed", technical: float = 75.0, frame_path: Path | None = None) -> dict[str, Any]:
    frame = {
        "frame_index": 0,
        "local_frame_path": str(frame_path or ""),
        "width": 100,
        "height": 140,
        "sha256": "a" * 64,
        "extraction_status": "extracted" if status == "passed" else "failed",
        "perceptual_hash": "0" * 16,
    }
    return {
        "asset_id": asset_id,
        "analysis_status": status,
        "preview": {
            "candidate_id": asset_id,
            "provider": "fake",
            "provider_asset_id": asset_id,
            "preview_media_type": "image",
            "local_path": str(frame_path or ""),
            "cache_status": "hit",
        },
        "sampled_frames": [frame] if frame_path else [],
        "technical_metrics": {
            "technical_quality_score": technical,
            "score_breakdown": {"brightness": 20.0, "contrast": 20.0},
            "crop_suitability": {"9:16": {"heuristic_crop_suitability": technical}},
        },
        "perceptual_signature": {"asset_id": asset_id, "media_type": "image", "frame_hashes": ["0" * 16]},
        "duplicate_scores": [],
        "crop_scores": {"9:16": {"heuristic_crop_suitability": technical}},
        "technical_quality_score": technical,
    }


if __name__ == "__main__":
    unittest.main()

class M1CReviewIdentityIntegrationTests(unittest.TestCase):
    def test_attach_selected_asset_rebinds_identity_and_records_lineage(self) -> None:
        from src.assets.review_bundle import attach_selected_asset, create_scene_review_bundle

        candidates = [
            {
                "asset_id": "candidate_a",
                "provider": "fake",
                "provider_asset_id": "provider-a",
                "source_page_url": "https://fake.local/a",
                "license": {"rights_status": "licensed", "allowed_for_render": True},
            },
            {
                "asset_id": "candidate_b",
                "provider": "fake",
                "provider_asset_id": "provider-b",
                "source_page_url": "https://fake.local/b",
                "license": {"rights_status": "licensed", "allowed_for_render": True},
                "vision_tags": ["ocean"],
                "vision_tags_asset_id": "candidate_b",
                "vision_tags_source_sha256": "same-bytes",
                "vision_tags_cache_key": "cache-b",
            },
        ]
        bundle = create_scene_review_bundle(
            project_id="project_001",
            scene={"scene_id": "scene_001", "primary_query": "ocean"},
            semantic_scene={},
            metadata_queries=[],
            provider_routing={},
            candidates=candidates,
            analyses=[],
            selected_candidate_id="candidate_a",
            target_aspect_ratio="9:16",
        )
        attach_selected_asset(
            bundle,
            {
                **candidates[1],
                "replaces_asset_id": "candidate_a",
                "path": "assets/downloaded/b.jpg",
                "download_status": "downloaded",
                "checksum_sha256": "same-bytes",
            },
        )

        self.assertEqual(bundle.selected_candidate["asset_id"], "candidate_b")
        self.assertEqual(bundle.selected_candidate["provider_asset_id"], "provider-b")
        self.assertEqual(bundle.selected_candidate["source_page_url"], "https://fake.local/b")
        self.assertEqual(bundle.selected_candidate["replaces_asset_id"], "candidate_a")
        self.assertEqual(bundle.selected_candidate["vision_tags"], ["ocean"])
        self.assertEqual(bundle.selected_candidate["local_path"], "assets/downloaded/b.jpg")
        self.assertEqual(bundle.alternatives[0]["asset_id"], "candidate_a")

    def test_compatibility_preview_rebuild_preserves_selected_fallback_lineage(self) -> None:
        import json

        from src.assets.download import sha256_file
        from src.assets.visual_preview import prepare_visual_preview_for_project

        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project_001"
            source = project / "assets" / "downloaded" / "candidate_b.png"
            source.parent.mkdir(parents=True)
            Image.new("RGB", (1080, 1920), (20, 80, 120)).save(source)
            checksum = sha256_file(source)
            candidate_a = _candidate("candidate_a")
            ranked_b = _candidate("candidate_b")
            selected_b = {
                **ranked_b,
                "path": str(source),
                "local_path": str(source),
                "downloaded_path": str(source),
                "checksum_sha256": checksum,
                "download_status": "downloaded",
                "replaces_asset_id": "candidate_a",
            }
            manifest = {
                "schema_version": 1,
                "scenes": [
                    {
                        "scene_id": "scene_001",
                        "ranked_candidates": [candidate_a, ranked_b],
                        "selected_asset": selected_b,
                    }
                ],
            }
            (project / "assets" / "assets_manifest.json").write_text(
                json.dumps(manifest),
                encoding="utf-8",
            )

            prepare_visual_preview_for_project(
                project_root=project,
                project_id="project_001",
                all_scenes=True,
                offline=True,
                no_html=True,
            )
            review = json.loads(
                (project / "assets" / "review" / "visual_review_manifest.json").read_text(
                    encoding="utf-8"
                )
            )

        reviewed = review["scenes"][0]["selected_candidate"]
        self.assertEqual(reviewed["asset_id"], "candidate_b")
        self.assertEqual(reviewed["replaces_asset_id"], "candidate_a")
