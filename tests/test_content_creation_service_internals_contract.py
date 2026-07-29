from __future__ import annotations

import inspect
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from src.content_creation.models import ContentCreationRequest


class ContentCreationServiceInternalsCharacterizationTests(unittest.TestCase):
    def test_service_keeps_existing_import_surface_and_signatures(self) -> None:
        from src.content_creation import service

        expected_parameters = {
            "create_content": ["request", "progress_callback"],
            "_create_story_card": ["request", "template", "progress_callback"],
            "_create_fullscreen_voiceover": [
                "request",
                "template",
                "progress_callback",
            ],
            "_create_paid_voice_approval": [
                "root",
                "job",
                "request",
                "localization",
            ],
            "_build_paid_preflight_summary": [
                "root",
                "job",
                "request",
                "localization",
            ],
            "_story_card_rerun_command": ["request"],
            "_fullscreen_rerun_command": ["request", "job_id", "approve"],
        }
        for name, parameters in expected_parameters.items():
            with self.subTest(name=name):
                function = getattr(service, name)
                self.assertEqual(
                    list(inspect.signature(function).parameters),
                    parameters,
                )

    def test_create_content_dispatches_through_module_use_case_patch_points(
        self,
    ) -> None:
        from src.content_creation import service

        request = ContentCreationRequest()
        for template_id, patch_point in (
            ("story_card_text_only_v1", "_create_story_card"),
            ("fullscreen_voiceover_v1", "_create_fullscreen_voiceover"),
        ):
            with self.subTest(template_id=template_id):
                template = SimpleNamespace(template_id=template_id)
                expected = object()
                handler = mock.Mock(return_value=expected)
                callback = mock.Mock()
                with (
                    mock.patch.object(service, "_resolve_template", return_value=template),
                    mock.patch.object(service, "_validate_music_request") as validate_music,
                    mock.patch.object(service, patch_point, handler),
                ):
                    result = service.create_content(
                        request,
                        progress_callback=callback,
                    )

                self.assertIs(result, expected)
                validate_music.assert_called_once_with(request)
                handler.assert_called_once_with(request, template, callback)

    def test_progress_callback_adapter_preserves_stage_and_status(self) -> None:
        from src.content_creation import service

        callback = mock.Mock()
        service._notify(callback, "voice", "needs_review")
        callback.assert_called_once_with("voice", "needs_review")
        service._notify(None, "voice", "completed")

    def test_paid_preflight_without_script_is_safe_and_empty(self) -> None:
        from src.content_creation import service

        with tempfile.TemporaryDirectory() as tmp:
            summary = service._build_paid_preflight_summary(
                root=Path(tmp),
                job=SimpleNamespace(language="ru"),
                request=ContentCreationRequest(channel_id="nature_pulse"),
            )

        self.assertEqual(summary, {})

    def test_facade_delegates_to_separate_workflow_use_cases(self) -> None:
        from src.content_creation import (
            fullscreen_voiceover_use_case,
            service,
            story_card_use_case,
        )

        self.assertIs(
            service._create_story_card,
            story_card_use_case.create_story_card,
        )
        self.assertIs(
            service._create_fullscreen_voiceover,
            fullscreen_voiceover_use_case.create_fullscreen_voiceover,
        )
        self.assertIs(
            service._create_paid_voice_approval,
            fullscreen_voiceover_use_case.create_paid_voice_approval,
        )


if __name__ == "__main__":
    unittest.main()
