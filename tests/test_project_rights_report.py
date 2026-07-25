"""Unified, read-only rights report over a project's existing manifests.

Every case runs against tempfile-backed project folders: no network, no downloads,
no paid API, and nothing is written into the real projects/ tree.
"""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from src.content_creation.cli import main
from src.projects import (
    PROJECT_KIND_NEWS_JOB,
    PROJECT_KIND_PROJECT_MANIFEST,
    MEDIA_ROLE_MUSIC,
    MEDIA_ROLE_VISUAL,
    build_rights_report,
)


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _selected_asset(
    scene_id: str,
    *,
    asset_id: str | None = None,
    provider: str = "pexels",
    provider_asset_id: str = "111",
    license_name: str = "pexels",
    source_page: str = "https://www.pexels.com/video/example-111/",
    checksum: str = "a" * 64,
    allowed: bool = True,
    review: bool = False,
    local_path: str = "",
) -> dict:
    return {
        "asset_id": asset_id or f"{provider}_video_{provider_asset_id}",
        "scene_id": scene_id,
        "provider": provider,
        "provider_asset_id": provider_asset_id,
        "source_page_url": source_page,
        "download_url": "https://videos.example.com/file.mp4",
        "author": "Автор Тестовый",
        "media_type": "video",
        "license_name": license_name,
        "license": {
            "license_name": license_name,
            "license_url": "https://www.pexels.com/license/",
            "commercial_use_allowed": True,
            "attribution_required": False,
            "attribution_text": "",
        },
        "checksum_sha256": checksum,
        "local_path": local_path,
        "allowed_for_render": allowed,
        "review_required": review,
    }


def _news_project(root: Path, project_id: str, scenes: list[dict], *, missing: list[dict] | None = None) -> Path:
    project_root = root / project_id
    _write(project_root / "job.json", {"job_id": project_id, "channel_id": "c", "language": "ru", "stages": {}})
    _write(
        project_root / "assets" / "assets_manifest.json",
        {"schema_version": 1, "scenes": scenes, "missing_scenes": missing or []},
    )
    _write(project_root / "assets" / "missing_assets.json", {"missing_scenes": missing or []})
    return project_root


class NewsAssetsTests(unittest.TestCase):
    def test_selected_assets_become_rights_items(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project_root = _news_project(
                root,
                "news_one",
                [
                    {
                        "scene_id": "scene_001",
                        "selected_asset": _selected_asset(
                            "scene_001", provider_asset_id="111", source_page="https://www.pexels.com/video/one-111/"
                        ),
                    },
                    {
                        "scene_id": "scene_002",
                        "selected_asset": _selected_asset(
                            "scene_002",
                            provider_asset_id="222",
                            checksum="b" * 64,
                            source_page="https://www.pexels.com/video/two-222/",
                        ),
                    },
                ],
            )
            report = build_rights_report(
                project_id="news_one", project_root=project_root, project_kind=PROJECT_KIND_NEWS_JOB
            )

            self.assertEqual(report.summary.total, 2)
            self.assertEqual(report.summary.visual_items, 2)
            self.assertEqual(report.summary.verified, 2)
            self.assertEqual(report.overall_status, "verified")
            self.assertFalse(report.has_blocking_problems)
            self.assertEqual([item.scene_id for item in report.items], ["scene_001", "scene_002"])

    def test_unselected_candidates_are_not_counted_as_used(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scene = {
                "scene_id": "scene_001",
                "selected_asset": _selected_asset("scene_001"),
                "candidates": [_selected_asset("scene_001", provider_asset_id="999")],
                "rejected_candidates": [_selected_asset("scene_001", provider_asset_id="888")],
            }
            project_root = _news_project(root, "news_one", [scene])
            report = build_rights_report(project_id="news_one", project_root=project_root)

            self.assertEqual(report.summary.total, 1)

    def test_scene_without_a_selected_asset_is_skipped_not_invented(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = _news_project(
                Path(tmp), "news_one", [{"scene_id": "scene_001", "selected_asset": {}}]
            )
            report = build_rights_report(project_id="news_one", project_root=project_root)
            self.assertEqual(report.summary.total, 0)


class MissingScenesTests(unittest.TestCase):
    def test_scenes_without_material_are_reported_and_block(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = _news_project(
                Path(tmp),
                "news_one",
                [{"scene_id": "scene_001", "selected_asset": _selected_asset("scene_001")}],
                missing=[{"scene_id": "scene_002", "reason": "no_candidate_passed_policy", "primary_query": "ocean"}],
            )
            report = build_rights_report(project_id="news_one", project_root=project_root)

            self.assertEqual(report.summary.scenes_without_asset, 1)
            self.assertEqual(report.missing_scenes[0].scene_id, "scene_002")
            self.assertEqual(report.missing_scenes[0].reason, "no_candidate_passed_policy")
            self.assertEqual(report.overall_status, "blocked")
            self.assertTrue(report.has_blocking_problems)

    def test_missing_scenes_are_never_hidden_by_verified_assets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = _news_project(
                Path(tmp),
                "news_one",
                [{"scene_id": "scene_001", "selected_asset": _selected_asset("scene_001")}],
                missing=[{"scene_id": "scene_002", "reason": "dry_run_does_not_download_assets"}],
            )
            report = build_rights_report(project_id="news_one", project_root=project_root)
            self.assertEqual(report.summary.verified, 1)
            self.assertTrue(report.has_blocking_problems)


class ItemStatusTests(unittest.TestCase):
    def _single_item(self, tmp: str, asset: dict):
        project_root = _news_project(Path(tmp), "news_one", [{"scene_id": "scene_001", "selected_asset": asset}])
        return build_rights_report(project_id="news_one", project_root=project_root).items[0]

    def test_blocked_asset(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            item = self._single_item(tmp, _selected_asset("scene_001", allowed=False))
            self.assertEqual(item.verification_status, "blocked")

    def test_review_required_asset(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            item = self._single_item(tmp, _selected_asset("scene_001", review=True))
            self.assertEqual(item.verification_status, "review_required")

    def test_missing_license_is_not_verified(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            asset = _selected_asset("scene_001", license_name="")
            asset["license"] = {}
            item = self._single_item(tmp, asset)
            self.assertEqual(item.verification_status, "review_required")
            self.assertTrue(any("лицензии" in w for w in item.warnings))

    def test_missing_source_url_is_not_verified(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            item = self._single_item(tmp, _selected_asset("scene_001", source_page=""))
            self.assertEqual(item.verification_status, "review_required")
            self.assertTrue(any("источник" in w for w in item.warnings))

    def test_missing_checksum_is_not_verified(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            item = self._single_item(tmp, _selected_asset("scene_001", checksum=""))
            self.assertEqual(item.verification_status, "review_required")

    def test_asset_with_no_rights_data_at_all_is_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bare = {"asset_id": "x", "scene_id": "scene_001"}
            item = self._single_item(tmp, bare)
            self.assertEqual(item.verification_status, "unknown")

    def test_declared_local_file_that_is_absent_is_flagged_separately(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            item = self._single_item(tmp, _selected_asset("scene_001", local_path=str(Path(tmp) / "gone.mp4")))
            self.assertFalse(item.local_file_present)
            self.assertTrue(any("не найден" in w for w in item.warnings))
            # A missing file does not by itself change the rights verdict.
            self.assertEqual(item.verification_status, "verified")

    def test_summary_counts_missing_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            asset = _selected_asset("scene_001", license_name="", source_page="", checksum="")
            asset["license"] = {}
            project_root = _news_project(Path(tmp), "news_one", [{"scene_id": "scene_001", "selected_asset": asset}])
            summary = build_rights_report(project_id="news_one", project_root=project_root).summary
            self.assertEqual(summary.items_missing_license, 1)
            self.assertEqual(summary.items_missing_source, 1)
            self.assertEqual(summary.items_missing_checksum, 1)


class MusicRightsTests(unittest.TestCase):
    def _project_with_music(self, root: Path) -> Path:
        project_root = _news_project(
            root, "news_one", [{"scene_id": "scene_001", "selected_asset": _selected_asset("scene_001")}]
        )
        track = root / "bed.mp3"
        track.write_bytes(b"fake-audio")
        from src.audio.music_manifest import prepare_project_music

        prepare_project_music(project_root, track)
        return project_root

    def test_user_supplied_music_is_never_verified(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = self._project_with_music(Path(tmp))
            report = build_rights_report(project_id="news_one", project_root=project_root)
            music = [item for item in report.items if item.media_role == MEDIA_ROLE_MUSIC]

            self.assertEqual(len(music), 1)
            self.assertIn(music[0].verification_status, {"review_required", "unknown"})
            self.assertNotEqual(music[0].verification_status, "verified")
            self.assertEqual(music[0].commercial_use_status, "unknown")
            self.assertEqual(report.summary.music_items, 1)

    def test_music_does_not_make_the_whole_project_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = build_rights_report(project_id="news_one", project_root=self._project_with_music(Path(tmp)))
            self.assertEqual(report.overall_status, "review_required")
            self.assertFalse(report.has_blocking_problems)

    def test_licence_is_never_guessed_from_the_file_extension(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = build_rights_report(project_id="news_one", project_root=self._project_with_music(Path(tmp)))
            music = next(item for item in report.items if item.media_role == MEDIA_ROLE_MUSIC)
            self.assertEqual(music.license_name, "unverified_user_supplied")


class DeduplicationTests(unittest.TestCase):
    def test_same_asset_in_assets_manifest_and_sources_json_appears_once(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project_root = _news_project(
                root, "news_one", [{"scene_id": "scene_001", "selected_asset": _selected_asset("scene_001")}]
            )
            _write(
                project_root / "assets" / "sources.json",
                {
                    "schema_version": 1,
                    "assets": [
                        {
                            "provider": "pexels",
                            "provider_asset_id": "111",
                            "source_page": "https://www.pexels.com/video/example-111/",
                            "author": "Автор Тестовый",
                            "license_name": "pexels",
                        }
                    ],
                },
            )
            report = build_rights_report(project_id="news_one", project_root=project_root)

            self.assertEqual(report.summary.total, 1)
            self.assertEqual(report.items[0].source_manifest, "assets/assets_manifest.json")

    def test_material_only_in_sources_json_is_still_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project_root = _news_project(
                root, "news_one", [{"scene_id": "scene_001", "selected_asset": _selected_asset("scene_001")}]
            )
            _write(
                project_root / "assets" / "sources.json",
                {
                    "assets": [
                        {
                            "provider": "wikimedia",
                            "provider_asset_id": "777",
                            "source_page": "https://commons.wikimedia.org/wiki/File:Other.jpg",
                            "license_name": "cc-by-sa",
                        }
                    ]
                },
            )
            report = build_rights_report(project_id="news_one", project_root=project_root)
            self.assertEqual(report.summary.total, 2)

    def test_different_materials_sharing_a_filename_are_not_merged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = _selected_asset(
                "scene_001", provider_asset_id="111", checksum="a" * 64, local_path="a/scene.mp4",
                source_page="https://www.pexels.com/video/one-111/",
            )
            second = _selected_asset(
                "scene_002", provider_asset_id="222", checksum="b" * 64, local_path="b/scene.mp4",
                source_page="https://www.pexels.com/video/two-222/",
            )
            project_root = _news_project(
                root,
                "news_one",
                [
                    {"scene_id": "scene_001", "selected_asset": first},
                    {"scene_id": "scene_002", "selected_asset": second},
                ],
            )
            self.assertEqual(build_rights_report(project_id="news_one", project_root=project_root).summary.total, 2)

    def test_a_shared_source_page_does_not_merge_provably_different_materials(self) -> None:
        """A weak key must never override a strong one: same landing page, different
        checksums and different provider asset ids means two materials."""
        with tempfile.TemporaryDirectory() as tmp:
            shared = "https://www.pexels.com/video/collection-page/"
            project_root = _news_project(
                Path(tmp),
                "news_one",
                [
                    {
                        "scene_id": "scene_001",
                        "selected_asset": _selected_asset(
                            "scene_001", provider_asset_id="111", checksum="a" * 64, source_page=shared
                        ),
                    },
                    {
                        "scene_id": "scene_002",
                        "selected_asset": _selected_asset(
                            "scene_002", provider_asset_id="222", checksum="b" * 64, source_page=shared
                        ),
                    },
                ],
            )
            self.assertEqual(build_rights_report(project_id="news_one", project_root=project_root).summary.total, 2)

    def test_the_same_material_reused_in_two_scenes_is_reported_once(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            asset = _selected_asset("scene_001", provider_asset_id="111", checksum="a" * 64)
            project_root = _news_project(
                Path(tmp),
                "news_one",
                [
                    {"scene_id": "scene_001", "selected_asset": dict(asset)},
                    {"scene_id": "scene_002", "selected_asset": dict(asset, scene_id="scene_002")},
                ],
            )
            report = build_rights_report(project_id="news_one", project_root=project_root)
            self.assertEqual(report.summary.total, 1)
            self.assertIn("scene_002", report.items[0].scene_id)


class EvidenceBundleCompatibilityTests(unittest.TestCase):
    def test_project_manifest_without_evidence_says_so_instead_of_pretending(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "card_one"
            _write(project_root / "project.json", {"project_id": "card_one", "template_id": "story_card_text_only_v1"})
            report = build_rights_report(
                project_id="card_one", project_root=project_root, project_kind=PROJECT_KIND_PROJECT_MANIFEST
            )

            self.assertEqual(report.summary.total, 0)
            self.assertEqual(report.overall_status, "unknown")
            self.assertTrue(any("evidence_manifest.json" in w for w in report.warnings))
            self.assertTrue(any("подтвердить нельзя" in w for w in report.warnings))

    def test_evidence_records_are_read_when_they_do_exist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "card_one"
            _write(project_root / "project.json", {"project_id": "card_one"})
            _write(
                project_root / "evidence" / "evidence_manifest.json",
                {
                    "project_id": "card_one",
                    "records": [
                        {
                            "evidence_id": "ev_001",
                            "asset_id": "owl_clip",
                            "provider": "pixabay",
                            "source_url": "https://pixabay.com/videos/id-18244/",
                            "license_name": "pixabay",
                            "checksum_sha256": "c" * 64,
                            "verification_status": "verified",
                        }
                    ],
                },
            )
            report = build_rights_report(
                project_id="card_one", project_root=project_root, project_kind=PROJECT_KIND_PROJECT_MANIFEST
            )

            self.assertEqual(report.summary.total, 1)
            self.assertEqual(report.items[0].verification_status, "verified")
            self.assertEqual(report.items[0].source_manifest, "evidence/evidence_manifest.json")


class ToleranceTests(unittest.TestCase):
    def test_corrupt_assets_manifest_warns_instead_of_raising(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "news_one"
            _write(project_root / "job.json", {"job_id": "news_one"})
            path = project_root / "assets" / "assets_manifest.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("{ not json", encoding="utf-8")

            report = build_rights_report(project_id="news_one", project_root=project_root)
            self.assertEqual(report.summary.total, 0)
            self.assertTrue(any("повреждён" in w for w in report.warnings))

    def test_project_without_any_manifest_does_not_raise(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "empty"
            project_root.mkdir()
            report = build_rights_report(project_id="empty", project_root=project_root)
            self.assertEqual(report.overall_status, "unknown")
            self.assertEqual(report.sources_read, [])

    def test_report_serializes_to_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = _news_project(
                Path(tmp), "news_one", [{"scene_id": "scene_001", "selected_asset": _selected_asset("scene_001")}]
            )
            payload = build_rights_report(project_id="news_one", project_root=project_root).to_dict()
            json.dumps(payload, ensure_ascii=False)
            self.assertIn("overall_status", payload)
            self.assertIn("summary", payload)


class ReadOnlyTests(unittest.TestCase):
    def test_building_a_report_changes_no_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project_root = _news_project(
                root,
                "news_one",
                [{"scene_id": "scene_001", "selected_asset": _selected_asset("scene_001")}],
                missing=[{"scene_id": "scene_002", "reason": "no_candidate"}],
            )
            track = root / "bed.mp3"
            track.write_bytes(b"fake-audio")
            from src.audio.music_manifest import prepare_project_music

            prepare_project_music(project_root, track)

            def snapshot() -> dict[str, tuple[int, int]]:
                return {
                    path.relative_to(project_root).as_posix(): (path.stat().st_size, path.stat().st_mtime_ns)
                    for path in sorted(project_root.rglob("*"))
                    if path.is_file()
                }

            before = snapshot()
            build_rights_report(project_id="news_one", project_root=project_root)
            build_rights_report(project_id="news_one", project_root=project_root)
            self.assertEqual(before, snapshot())


class RightsReportCliTests(unittest.TestCase):
    def _run(self, argv: list[str]) -> tuple[int, str]:
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = main(argv)
        return code, buffer.getvalue()

    def test_text_output_for_a_news_project_exits_zero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _news_project(
                Path(tmp), "news_one", [{"scene_id": "scene_001", "selected_asset": _selected_asset("scene_001")}]
            )
            code, output = self._run(
                ["project", "rights-report", "--project-id", "news_one", "--projects-root", tmp]
            )
            self.assertEqual(code, 0)
            self.assertIn("Проект: news_one", output)
            self.assertIn("Всего материалов: 1", output)
            self.assertIn("pexels", output)
            self.assertIn("не является юридическим", output)

    def test_blocked_material_exits_one(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _news_project(
                Path(tmp),
                "news_one",
                [{"scene_id": "scene_001", "selected_asset": _selected_asset("scene_001", allowed=False)}],
            )
            code, output = self._run(
                ["project", "rights-report", "--project-id", "news_one", "--projects-root", tmp]
            )
            self.assertEqual(code, 1)
            self.assertIn("Заблокировано:    1", output)

    def test_scene_without_material_exits_one(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _news_project(
                Path(tmp),
                "news_one",
                [{"scene_id": "scene_001", "selected_asset": _selected_asset("scene_001")}],
                missing=[{"scene_id": "scene_002", "reason": "no_candidate_passed_policy"}],
            )
            code, output = self._run(
                ["project", "rights-report", "--project-id", "news_one", "--projects-root", tmp]
            )
            self.assertEqual(code, 1)
            self.assertIn("Сцены без материала", output)

    def test_review_required_only_still_exits_zero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _news_project(
                Path(tmp),
                "news_one",
                [{"scene_id": "scene_001", "selected_asset": _selected_asset("scene_001", review=True)}],
            )
            code, _ = self._run(["project", "rights-report", "--project-id", "news_one", "--projects-root", tmp])
            self.assertEqual(code, 0)

    def test_json_output_carries_status_and_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _news_project(
                Path(tmp), "news_one", [{"scene_id": "scene_001", "selected_asset": _selected_asset("scene_001")}]
            )
            code, output = self._run(
                ["project", "rights-report", "--project-id", "news_one", "--projects-root", tmp, "--json"]
            )
            data = json.loads(output)
            self.assertEqual(code, 0)
            self.assertEqual(data["overall_status"], "verified")
            self.assertFalse(data["has_blocking_problems"])
            self.assertEqual(data["summary"]["total"], 1)
            self.assertEqual(data["items"][0]["media_role"], MEDIA_ROLE_VISUAL)

    def test_story_card_project_keeps_the_previous_evidence_bundle_output(self) -> None:
        """Backward compatibility: nothing that the old command exposed is lost."""
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "card_one"
            _write(
                project_root / "project.json",
                {
                    "project_id": "card_one",
                    "title": "Карточка",
                    "channel_id": "nature_pulse",
                    "application_id": "content_creator",
                    "format_id": "vertical_short",
                    "template_id": "story_card_text_only_v1",
                },
            )
            code, output = self._run(
                ["project", "rights-report", "--project-id", "card_one", "--projects-root", tmp, "--json"]
            )
            data = json.loads(output)
            self.assertEqual(code, 0)
            self.assertEqual(data["project_kind"], PROJECT_KIND_PROJECT_MANIFEST)
            legacy = data["evidence_bundle_report"]
            for key in ("project_id", "summary", "by_provider", "by_license", "needs_attention"):
                self.assertIn(key, legacy)

    def test_missing_project_reports_cleanly_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            code, output = self._run(["project", "rights-report", "--project-id", "nope", "--projects-root", tmp])
            self.assertEqual(code, 1)
            self.assertNotIn("Traceback", output)
            self.assertIn("nope", output)

    def test_cli_run_writes_nothing_into_the_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = _news_project(
                Path(tmp), "news_one", [{"scene_id": "scene_001", "selected_asset": _selected_asset("scene_001")}]
            )
            before = sorted(path.relative_to(project_root).as_posix() for path in project_root.rglob("*"))
            self._run(["project", "rights-report", "--project-id", "news_one", "--projects-root", tmp])
            after = sorted(path.relative_to(project_root).as_posix() for path in project_root.rglob("*"))
            self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
