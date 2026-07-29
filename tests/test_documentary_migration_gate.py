from __future__ import annotations

import inspect
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
LEGACY_DOCUMENTARY_CHANNELS = {
    "psychology",
    "quotes",
    "size_comparison",
    "survival",
}


class DocumentaryMigrationGateCharacterizationTests(unittest.TestCase):
    def test_catalog_has_no_documentary_application_or_longform_template(self) -> None:
        from src.production_catalog.catalog import get_default_catalog

        catalog = get_default_catalog()
        applications = {
            definition.application_id: definition
            for definition in catalog.applications.list_all()
        }
        templates = catalog.templates.list_all()

        self.assertNotIn("documentary", applications)
        self.assertFalse(catalog.formats.get("longform").enabled)
        self.assertEqual(
            [
                template.template_id
                for template in templates
                if template.format_id == "longform"
            ],
            [],
        )
        self.assertEqual(
            {template.template_id for template in templates if template.enabled},
            {"fullscreen_voiceover_v1", "story_card_text_only_v1"},
        )

    def test_documentary_channel_profiles_remain_legacy_only(self) -> None:
        from src.content_creation.capabilities import (
            CHANNEL_TYPE_LEGACY_PIPELINE,
            list_channels,
        )

        channels = {
            channel["channel_id"]: channel
            for channel in list_channels()
            if channel["channel_id"] in LEGACY_DOCUMENTARY_CHANNELS
        }

        self.assertEqual(set(channels), LEGACY_DOCUMENTARY_CHANNELS)
        for channel in channels.values():
            self.assertEqual(
                channel["channel_profile_type"],
                CHANNEL_TYPE_LEGACY_PIPELINE,
            )
            self.assertFalse(channel["usable_for_content_creation"])
            self.assertEqual(channel["supported_templates"], [])

    def test_fixed_plan_uses_an_unrecognized_bespoke_project_contract(self) -> None:
        from src.production_plan.youtube_shorts import (
            PROJECT_FOLDER,
            create_solar_vs_nuclear_plan,
        )
        from src.projects.repository import (
            PROJECT_KIND_UNKNOWN,
            ProjectRepository,
        )

        with tempfile.TemporaryDirectory() as temporary:
            project = create_solar_vs_nuclear_plan(temporary)
            root = Path(project["root"])
            view = ProjectRepository(temporary).get(PROJECT_FOLDER)
            self.assertTrue((root / "project_config.json").is_file())
            self.assertTrue((root / "scenes.json").is_file())
            self.assertFalse((root / "job.json").exists())
            self.assertFalse((root / "project.json").exists())
            self.assertEqual(view.kind, PROJECT_KIND_UNKNOWN)
            self.assertEqual(project["readiness"]["status"], "blocked")
            self.assertIn("missing_voice_final", project["readiness"]["errors"])

    def test_root_facade_still_owns_fixed_plan_entrypoints(self) -> None:
        import pipeline
        from src.production_plan.solar_vs_nuclear_render import (
            build_solar_vs_nuclear_video,
        )
        from src.production_plan.youtube_shorts import (
            create_solar_vs_nuclear_plan,
        )

        self.assertIs(
            pipeline.create_solar_vs_nuclear_plan,
            create_solar_vs_nuclear_plan,
        )
        self.assertIs(
            pipeline.build_solar_vs_nuclear_video,
            build_solar_vs_nuclear_video,
        )
        args = pipeline.parse_args(
            [
                "--production-plan",
                "solar_vs_nuclear",
                "--production-plan-root",
                "workspace",
            ]
        )
        self.assertEqual(args.production_plan, "solar_vs_nuclear")
        self.assertEqual(args.production_plan_root, "workspace")

    def test_fixed_plan_render_has_no_application_or_paid_approval_gate(self) -> None:
        from src.production_plan.solar_vs_nuclear_render import (
            build_solar_vs_nuclear_video,
        )

        source = (
            REPO_ROOT
            / "src"
            / "production_plan"
            / "solar_vs_nuclear_render.py"
        ).read_text(encoding="utf-8")

        self.assertEqual(
            list(inspect.signature(build_solar_vs_nuclear_video).parameters),
            ["project_root"],
        )
        self.assertIn("load_dotenv(", source)
        self.assertIn("ElevenLabsProvider().synthesize(", source)
        self.assertIn("pexels_provider.search_videos(", source)
        self.assertIn("pixabay_provider.search_videos(", source)
        self.assertIn("requests.get(", source)


if __name__ == "__main__":
    unittest.main()
