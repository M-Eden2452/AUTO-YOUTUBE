from __future__ import annotations

import inspect
import unittest


class StoryCardApplicationBoundaryCharacterizationTests(unittest.TestCase):
    def test_legacy_use_case_surface_and_signatures_are_stable(self) -> None:
        from src.content_creation import story_card_use_case

        expected_parameters = {
            "create_story_card": [
                "request",
                "template",
                "progress_callback",
            ],
            "story_card_rerun_command": ["request"],
        }

        for name, parameters in expected_parameters.items():
            with self.subTest(name=name):
                function = getattr(story_card_use_case, name)
                self.assertEqual(
                    list(inspect.signature(function).parameters),
                    parameters,
                )

    def test_project_contract_is_stable(self) -> None:
        from src.project_foundation.models import ProjectManifest
        from src.project_foundation.projects import (
            ProjectCreationResult,
            ProjectFactory,
        )

        self.assertEqual(
            list(inspect.signature(ProjectFactory.create).parameters),
            [
                "self",
                "channel",
                "title",
                "project_id",
                "application_id",
                "format_id",
                "template_id",
                "language",
                "export_targets",
                "source_type",
                "source_reference",
                "metadata",
                "dry_run",
            ],
        )
        self.assertEqual(
            list(ProjectCreationResult.__dataclass_fields__),
            ["manifest", "created_paths", "dry_run"],
        )
        self.assertEqual(
            list(ProjectManifest.__dataclass_fields__),
            [
                "project_id",
                "title",
                "channel_id",
                "application_id",
                "format_id",
                "template_id",
                "language",
                "export_targets",
                "status",
                "source_type",
                "source_reference",
                "project_root",
                "localization_root",
                "evidence_root",
                "created_at",
                "updated_at",
                "schema_version",
                "metadata",
            ],
        )

    def test_story_card_workflow_and_evidence_contracts_are_stable(self) -> None:
        from src.project_foundation.evidence import EvidenceBundle
        from src.project_foundation.models import (
            EVIDENCE_RECORD_SCHEMA_VERSION,
            EvidenceRecord,
        )
        from src.templates import story_card

        self.assertEqual(
            list(inspect.signature(story_card.prepare_story_card_render).parameters),
            [
                "project",
                "channel",
                "source_asset_path",
                "source_asset",
                "text",
                "render_preset_path",
                "output_filename",
                "preview_filename",
                "render_request_filename",
                "dry_run",
                "allow_overwrite",
                "render",
            ],
        )
        self.assertEqual(
            list(story_card.StoryCardIntegrationResult.__dataclass_fields__),
            [
                "project_id",
                "template_id",
                "canonical_template_id",
                "render_status",
                "render_request_path",
                "output_path",
                "width",
                "height",
                "fps",
                "duration_seconds",
                "source_asset",
                "localization",
                "warnings",
                "metadata",
            ],
        )

        record = EvidenceRecord(evidence_id="visual_source_asset")
        bundle = EvidenceBundle(project_id="story-card-characterization")
        bundle.add(record)
        payload = bundle.to_manifest_dict()

        self.assertEqual(
            set(payload),
            {"project_id", "schema_version", "updated_at", "records"},
        )
        self.assertEqual(
            payload["records"][0]["schema_version"],
            EVIDENCE_RECORD_SCHEMA_VERSION,
        )

    def test_canonical_boundary_reuses_existing_contracts_and_legacy_surface(
        self,
    ) -> None:
        from src.ai_youtube.apps.content_creator.workflows import story_card
        from src.content_creation import story_card_use_case
        from src.project_foundation.evidence import EvidenceBundle
        from src.project_foundation.models import EvidenceRecord, ProjectManifest
        from src.project_foundation.projects import (
            ProjectCreationResult,
            ProjectFactory,
        )
        from src.templates.story_card import (
            StoryCardIntegrationError,
            StoryCardIntegrationResult,
            prepare_story_card_render,
        )

        self.assertIs(
            story_card.create_story_card,
            story_card_use_case.create_story_card,
        )
        self.assertIs(story_card.ProjectFactory, ProjectFactory)
        self.assertIs(story_card.ProjectCreationResult, ProjectCreationResult)
        self.assertIs(story_card.ProjectManifest, ProjectManifest)
        self.assertIs(story_card.EvidenceBundle, EvidenceBundle)
        self.assertIs(story_card.EvidenceRecord, EvidenceRecord)
        self.assertIs(
            story_card.StoryCardIntegrationError,
            StoryCardIntegrationError,
        )
        self.assertIs(
            story_card.StoryCardIntegrationResult,
            StoryCardIntegrationResult,
        )
        self.assertIs(
            story_card.prepare_story_card_render,
            prepare_story_card_render,
        )


if __name__ == "__main__":
    unittest.main()
