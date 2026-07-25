from __future__ import annotations

import io
import subprocess
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from tests.network_guard import install_network_guard, uninstall_network_guard


class ProductionCatalogModelTests(unittest.TestCase):
    def test_content_creator_registered_active_and_enabled(self) -> None:
        from src.production_catalog.catalog import get_default_catalog

        catalog = get_default_catalog()
        application = catalog.applications.get("content_creator")

        self.assertTrue(application.enabled)
        self.assertEqual(application.implementation_status, "active")
        self.assertIn("vertical_short", application.supported_format_ids)

    def test_video_repurposer_registered_planned_and_disabled(self) -> None:
        from src.production_catalog.catalog import get_default_catalog

        catalog = get_default_catalog()
        application = catalog.applications.get("video_repurposer")

        self.assertFalse(application.enabled)
        self.assertEqual(application.implementation_status, "planned")

    def test_vertical_short_format_registered(self) -> None:
        from src.production_catalog.catalog import get_default_catalog

        catalog = get_default_catalog()
        format_definition = catalog.formats.get("vertical_short")

        self.assertEqual(format_definition.width, 1080)
        self.assertEqual(format_definition.height, 1920)
        self.assertTrue(format_definition.enabled)
        self.assertEqual(format_definition.implementation_status, "active")

    def test_template_returned_by_canonical_id(self) -> None:
        from src.production_catalog.catalog import get_default_catalog

        catalog = get_default_catalog()
        template = catalog.templates.get("story_card_text_only_v1")

        self.assertEqual(template.application_id, "content_creator")
        self.assertEqual(template.format_id, "vertical_short")
        self.assertEqual(template.render_preset_id, "story_card_short_v1")

    def test_legacy_alias_resolves_to_canonical_id(self) -> None:
        from src.production_catalog.catalog import get_default_catalog

        catalog = get_default_catalog()

        self.assertEqual(catalog.templates.resolve_id("story_card_short_v1"), "story_card_text_only_v1")
        template = catalog.templates.get("story_card_short_v1")
        self.assertEqual(template.template_id, "story_card_text_only_v1")

    def test_templates_filter_by_application_and_format(self) -> None:
        from src.production_catalog.catalog import get_default_catalog

        catalog = get_default_catalog()

        by_application = catalog.templates.filter_by_application("content_creator")
        by_format = catalog.templates.filter_by_format("vertical_short")
        by_missing_application = catalog.templates.filter_by_application("video_repurposer")

        self.assertEqual(
            {t.template_id for t in by_application}, {"story_card_text_only_v1", "fullscreen_voiceover_v1"}
        )
        self.assertEqual(
            {t.template_id for t in by_format}, {"story_card_text_only_v1", "fullscreen_voiceover_v1"}
        )
        self.assertEqual(by_missing_application, [])

    def test_fullscreen_voiceover_template_requires_voice(self) -> None:
        from src.production_catalog.catalog import get_default_catalog

        catalog = get_default_catalog()
        template = catalog.templates.get("fullscreen_voiceover_v1")

        self.assertTrue(template.requires_voice)
        self.assertEqual(template.application_id, "content_creator")
        self.assertEqual(template.format_id, "vertical_short")
        self.assertEqual(template.audio_policy_id, "fullscreen_voiceover_default")

    def test_story_card_template_still_voice_disabled(self) -> None:
        from src.production_catalog.catalog import get_default_catalog

        catalog = get_default_catalog()
        template = catalog.templates.get("story_card_text_only_v1")

        self.assertFalse(template.requires_voice)

    def test_duplicate_template_id_rejected(self) -> None:
        from src.production_catalog.catalog import _build_templates
        from src.production_catalog.models import CatalogValidationError, TemplateDefinition

        registry = _build_templates()
        duplicate = TemplateDefinition(
            template_id="story_card_text_only_v1",
            application_id="content_creator",
            format_id="vertical_short",
            display_name="Дубликат",
            description="",
            version=1,
            enabled=True,
            implementation_status="active",
            supported_input_types=("topic",),
            supported_export_targets=(),
            requires_voice=False,
            supports_topic_input=True,
            supports_script_input=False,
            recommended_for=(),
            render_preset_id="story_card_short_v1",
        )

        with self.assertRaises(CatalogValidationError):
            registry.register(duplicate)

    def test_duplicate_alias_rejected(self) -> None:
        from src.production_catalog.registry import TemplateRegistry
        from src.production_catalog.models import CatalogValidationError, TemplateDefinition

        registry = TemplateRegistry()
        registry.register(
            TemplateDefinition(
                template_id="template_a",
                application_id="content_creator",
                format_id="vertical_short",
                display_name="A",
                description="",
                version=1,
                enabled=True,
                implementation_status="active",
                supported_input_types=("topic",),
                supported_export_targets=(),
                requires_voice=False,
                supports_topic_input=True,
                supports_script_input=False,
                recommended_for=(),
                render_preset_id="preset_a",
                legacy_aliases=("shared_alias",),
            )
        )
        conflicting = TemplateDefinition(
            template_id="template_b",
            application_id="content_creator",
            format_id="vertical_short",
            display_name="B",
            description="",
            version=1,
            enabled=True,
            implementation_status="active",
            supported_input_types=("topic",),
            supported_export_targets=(),
            requires_voice=False,
            supports_topic_input=True,
            supports_script_input=False,
            recommended_for=(),
            render_preset_id="preset_b",
            legacy_aliases=("shared_alias",),
        )

        with self.assertRaises(CatalogValidationError):
            registry.register(conflicting)

    def test_unknown_template_returns_clear_error(self) -> None:
        from src.production_catalog.catalog import get_default_catalog
        from src.production_catalog.models import CatalogValidationError

        catalog = get_default_catalog()

        with self.assertRaises(CatalogValidationError):
            catalog.templates.get("does_not_exist")

    def test_unknown_format_returns_clear_error(self) -> None:
        from src.production_catalog.catalog import get_default_catalog
        from src.production_catalog.models import CatalogValidationError

        catalog = get_default_catalog()

        with self.assertRaises(CatalogValidationError):
            catalog.formats.get("does_not_exist")

    def test_export_target_catalog_validation(self) -> None:
        from src.production_catalog.catalog import get_default_catalog
        from src.production_catalog.models import CatalogValidationError

        catalog = get_default_catalog()
        target = catalog.export_targets.get("youtube_shorts")

        self.assertEqual(target.format_id, "vertical_short")
        catalog.export_targets.validate("tiktok")
        with self.assertRaises(CatalogValidationError):
            catalog.export_targets.get("unknown_target")

    def test_invalid_implementation_status_rejected(self) -> None:
        from src.production_catalog.models import ApplicationDefinition, CatalogValidationError

        with self.assertRaises(CatalogValidationError):
            ApplicationDefinition(
                application_id="broken_app",
                display_name="Broken",
                description="",
                supported_input_types=("topic",),
                supported_format_ids=("vertical_short",),
                enabled=True,
                implementation_status="implemented",
            )


class ProductionCatalogCliTests(unittest.TestCase):
    def _run_cli(self, argv: list[str]) -> tuple[int, str]:
        import pipeline

        buffer = io.StringIO()
        old_argv = sys.argv
        sys.argv = ["pipeline.py", *argv]
        try:
            with redirect_stdout(buffer):
                try:
                    pipeline.main()
                    exit_code = 0
                except SystemExit as exc:
                    exit_code = exc.code if isinstance(exc.code, int) else (1 if exc.code else 0)
        finally:
            sys.argv = old_argv
        return exit_code, buffer.getvalue()

    def test_applications_list_cli(self) -> None:
        exit_code, output = self._run_cli(["applications", "list"])
        self.assertEqual(exit_code, 0)
        self.assertIn("content_creator", output)
        self.assertIn("video_repurposer", output)

    def test_applications_inspect_cli(self) -> None:
        exit_code, output = self._run_cli(["applications", "inspect", "--application", "content_creator"])
        self.assertEqual(exit_code, 0)
        self.assertIn("Создание контента", output)

    def test_formats_list_cli(self) -> None:
        exit_code, output = self._run_cli(["formats", "list"])
        self.assertEqual(exit_code, 0)
        self.assertIn("vertical_short", output)

    def test_templates_list_cli(self) -> None:
        exit_code, output = self._run_cli(["templates", "list"])
        self.assertEqual(exit_code, 0)
        self.assertIn("story_card_text_only_v1", output)

    def test_templates_inspect_canonical_id_cli(self) -> None:
        exit_code, output = self._run_cli(["templates", "inspect", "--template", "story_card_text_only_v1"])
        self.assertEqual(exit_code, 0)
        self.assertIn("Render preset id: story_card_short_v1", output)

    def test_templates_inspect_legacy_alias_cli(self) -> None:
        exit_code, output = self._run_cli(["templates", "inspect", "--template", "story_card_short_v1"])
        self.assertEqual(exit_code, 0)
        self.assertIn("legacy alias", output)
        self.assertIn("story_card_text_only_v1", output)

    def test_export_targets_list_cli(self) -> None:
        exit_code, output = self._run_cli(["export-targets", "list"])
        self.assertEqual(exit_code, 0)
        self.assertIn("youtube_shorts", output)

    def test_unknown_template_cli_exits_nonzero(self) -> None:
        exit_code, _ = self._run_cli(["templates", "inspect", "--template", "does_not_exist"])
        self.assertNotEqual(exit_code, 0)

    def test_read_only_cli_does_not_call_network(self) -> None:
        install_network_guard()
        try:
            exit_code, _ = self._run_cli(["templates", "list"])
        finally:
            uninstall_network_guard()
        self.assertEqual(exit_code, 0)

    def test_no_project_or_render_files_created_by_catalog_commands(self) -> None:
        projects_root = Path("projects")
        before = set(projects_root.iterdir()) if projects_root.is_dir() else set()

        self._run_cli(["applications", "list"])
        self._run_cli(["formats", "list"])
        self._run_cli(["templates", "list"])
        self._run_cli(["export-targets", "list"])

        after = set(projects_root.iterdir()) if projects_root.is_dir() else set()
        self.assertEqual(before, after)

    def test_cli_via_subprocess_smoke(self) -> None:
        result = subprocess.run(
            [sys.executable, "-B", "pipeline.py", "templates", "inspect", "--template", "story_card_short_v1"],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("story_card_text_only_v1", result.stdout)


if __name__ == "__main__":
    unittest.main()
