from __future__ import annotations

import contextlib
import inspect
import io
import unittest
from types import SimpleNamespace
from unittest import mock


class CliInternalsCharacterizationTests(unittest.TestCase):
    def test_diagnostics_facade_keeps_its_callable_contract(self) -> None:
        from src.ai_youtube.cli.commands import diagnostics

        self.assertEqual(
            list(inspect.signature(diagnostics.register_commands).parameters),
            ["subparsers", "common"],
        )
        self.assertEqual(
            list(inspect.signature(diagnostics.handle_diagnostics).parameters),
            ["args", "resolve_paths_fn", "print_json_fn"],
        )
        self.assertEqual(
            diagnostics.__all__,
            ["register_commands", "handle_diagnostics"],
        )

    def test_authoring_commands_dispatch_through_existing_patch_points(self) -> None:
        from src.ai_youtube.cli.commands import diagnostics

        print_json = mock.Mock()
        for command, patch_point in (
            ("script", "_run_script_command"),
            ("visual-plan", "_run_visual_plan_command"),
        ):
            with self.subTest(command=command):
                handler = mock.Mock(return_value=17)
                with mock.patch.object(diagnostics, patch_point, handler):
                    result = diagnostics.handle_diagnostics(
                        SimpleNamespace(command=command),
                        resolve_paths_fn=mock.Mock(),
                        print_json_fn=print_json,
                    )
                self.assertEqual(result, 17)
                handler.assert_called_once_with(
                    mock.ANY,
                    print_json_fn=print_json,
                )

    def test_plain_and_validation_text_remain_stable(self) -> None:
        from src.ai_youtube.cli.commands import diagnostics

        issue = SimpleNamespace(
            severity="warning",
            scene_id="scene_002",
            code="needs_review",
            message="Проверьте сцену",
        )
        validation = SimpleNamespace(status="needs_review", issues=[issue])
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            diagnostics._print_plain([{"id": "one"}, {"id": "two"}])
            diagnostics._print_script_validation(validation, scene_count=2)
            diagnostics._print_plan_validation(validation, scene_count=2)

        self.assertEqual(
            output.getvalue().splitlines(),
            [
                "{'id': 'one'}",
                "{'id': 'two'}",
                "[script] нужна проверка (сцен: 2)",
                "  внимание [scene_002] needs_review: Проверьте сцену",
                "[visual-plan] нужна проверка (сцен: 2)",
                "  внимание [scene_002] needs_review: Проверьте сцену",
            ],
        )


if __name__ == "__main__":
    unittest.main()
