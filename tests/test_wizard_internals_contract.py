from __future__ import annotations

import contextlib
import inspect
import io
import unittest
from unittest import mock

from src.content_creation.models import ContentCreationResult


class WizardInternalsCharacterizationTests(unittest.TestCase):
    def test_facade_keeps_existing_import_surface_and_signatures(self) -> None:
        from src.content_creation import wizard

        self.assertEqual(
            list(inspect.signature(wizard.run_wizard).parameters),
            [
                "adapter",
                "create_fn",
                "no_icons",
                "projects_root",
                "project_fallback_roots",
                "channels_root",
            ],
        )
        self.assertEqual(
            list(inspect.signature(wizard._build_request).parameters),
            ["state", "project_overrides"],
        )
        for name in (
            "CANCEL",
            "PlainAdapter",
            "PromptAdapter",
            "QuestionaryAdapter",
            "START_ACTIONS",
            "_Wizard",
            "_WizardState",
            "_default_adapter",
            "_profiles_for_language",
            "_status_icon_key",
            "choose_icon_set",
        ):
            self.assertTrue(hasattr(wizard, name), name)

    def test_wizard_creation_uses_module_request_builder_patch_point(self) -> None:
        from src.content_creation import wizard

        state = wizard._WizardState()
        request = object()
        create_fn = mock.Mock(
            return_value=ContentCreationResult(
                status="completed",
                project_id="project",
                project_root="/tmp/project",
            )
        )
        runner = wizard._Wizard(
            mock.Mock(),
            wizard.ICONS_ASCII,
            create_fn,
            project_overrides={"projects_root": "/tmp/projects"},
        )

        output = io.StringIO()
        with mock.patch.object(
            wizard,
            "_build_request",
            return_value=request,
        ) as build_request, contextlib.redirect_stdout(output):
            result = runner.run_creation(state)

        self.assertEqual(result.status, "completed")
        build_request.assert_called_once_with(
            state,
            project_overrides={"projects_root": "/tmp/projects"},
        )
        create_fn.assert_called_once_with(request)
        self.assertIn("status=completed", output.getvalue())

    def test_facade_delegates_state_steps_and_presentation(self) -> None:
        from src.content_creation import (
            wizard,
            wizard_presentation,
            wizard_state,
            wizard_steps,
        )

        self.assertIs(wizard._WizardState, wizard_state.WizardState)
        self.assertTrue(issubclass(wizard._Wizard, wizard_steps.Wizard))
        self.assertIs(wizard.PlainAdapter, wizard_presentation.PlainAdapter)
        self.assertIs(
            wizard.QuestionaryAdapter,
            wizard_presentation.QuestionaryAdapter,
        )


if __name__ == "__main__":
    unittest.main()
