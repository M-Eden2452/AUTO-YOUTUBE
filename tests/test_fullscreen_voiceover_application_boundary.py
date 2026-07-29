from __future__ import annotations

import inspect
import subprocess
import sys
import unittest


class FullscreenVoiceoverApplicationBoundaryCharacterizationTests(
    unittest.TestCase
):
    def test_legacy_use_case_surface_and_signatures_are_stable(self) -> None:
        from src.content_creation import fullscreen_voiceover_use_case

        expected_parameters = {
            "create_fullscreen_voiceover": [
                "request",
                "template",
                "progress_callback",
            ],
            "resolve_content_inputs": ["request"],
            "resolve_script_source": ["request"],
            "resolve_localization": ["root", "job", "request"],
            "build_paid_preflight_summary": [
                "root",
                "job",
                "request",
                "localization",
            ],
            "resolve_voice_inputs": [
                "root",
                "job",
                "request",
                "localization",
            ],
            "create_paid_voice_approval": [
                "root",
                "job",
                "request",
                "localization",
            ],
            "completed_narration": ["store", "voice_manifest_path"],
            "fullscreen_rerun_command": ["request", "job_id", "approve"],
        }

        for name, parameters in expected_parameters.items():
            with self.subTest(name=name):
                function = getattr(fullscreen_voiceover_use_case, name)
                self.assertEqual(
                    list(inspect.signature(function).parameters),
                    parameters,
                )

        self.assertTrue(
            issubclass(
                fullscreen_voiceover_use_case.FullscreenVoiceoverUseCase,
                object,
            )
        )
        self.assertEqual(
            fullscreen_voiceover_use_case._RETRYABLE_ARTICLE_REASONS,
            {
                "http_429",
                "timeout",
                "connection_error",
                "request_error",
            },
        )

    def test_news_pipeline_and_project_contracts_are_stable(self) -> None:
        from src.news.models import NewsJob
        from src.news.pipeline import (
            NewsPipelineResult,
            create_news_to_short_job,
            run_news_to_short_job,
        )
        from src.news.project_store import NewsProject, NewsProjectStore

        self.assertEqual(
            list(inspect.signature(create_news_to_short_job).parameters),
            [
                "projects_root",
                "channel_id",
                "url",
                "urls",
                "title",
                "topic",
                "text",
                "text_file",
                "assets",
                "language",
                "target_duration_sec",
                "script_provider",
                "script_source",
                "script_include_cta",
                "script_cta_text",
                "visual_briefs",
                "completion_mode",
                "script_adaptation",
                "now",
            ],
        )
        self.assertEqual(
            list(inspect.signature(run_news_to_short_job).parameters),
            [
                "projects_root",
                "job_id",
                "dry_run",
                "until_stage",
                "stage",
                "resume",
                "force_stage",
                "execute_voice",
                "voice_profile_override",
                "completion_mode",
                "script_adaptation",
            ],
        )
        self.assertEqual(
            list(NewsPipelineResult.__dataclass_fields__),
            ["job_id", "status", "project_root", "completed_stages"],
        )
        self.assertEqual(
            list(NewsProject.__dataclass_fields__),
            ["root", "job"],
        )
        self.assertTrue(hasattr(NewsProjectStore, "load_job"))
        self.assertTrue(hasattr(NewsProjectStore, "save_job"))
        self.assertTrue(hasattr(NewsJob, "from_dict"))
        self.assertTrue(hasattr(NewsJob, "to_dict"))

    def test_compatibility_app_uses_existing_pipeline_contract(self) -> None:
        from apps.news_to_short import main as compatibility_app
        from src.news import pipeline

        self.assertIs(
            compatibility_app.create_news_to_short_job,
            pipeline.create_news_to_short_job,
        )
        self.assertIs(
            compatibility_app.run_news_to_short_job,
            pipeline.run_news_to_short_job,
        )

    def test_canonical_boundary_reuses_existing_contracts_and_legacy_surface(
        self,
    ) -> None:
        from src.ai_youtube.apps.content_creator.workflows import (
            fullscreen_voiceover,
        )
        from src.content_creation import fullscreen_voiceover_use_case
        from src.news.models import NewsJob
        from src.news.pipeline import (
            NewsPipelineResult,
            create_news_to_short_job,
            run_news_to_short_job,
        )
        from src.news.project_store import NewsProject, NewsProjectStore

        self.assertIs(
            fullscreen_voiceover.create_fullscreen_voiceover,
            fullscreen_voiceover_use_case.create_fullscreen_voiceover,
        )
        self.assertIs(fullscreen_voiceover.NewsJob, NewsJob)
        self.assertIs(fullscreen_voiceover.NewsProject, NewsProject)
        self.assertIs(fullscreen_voiceover.NewsProjectStore, NewsProjectStore)
        self.assertIs(
            fullscreen_voiceover.NewsPipelineResult,
            NewsPipelineResult,
        )
        self.assertIs(
            fullscreen_voiceover.create_news_to_short_job,
            create_news_to_short_job,
        )
        self.assertIs(
            fullscreen_voiceover.run_news_to_short_job,
            run_news_to_short_job,
        )

    def test_service_import_keeps_news_pipeline_lazy(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "import sys; "
                    "import src.content_creation.service; "
                    "assert 'src.news.pipeline' not in sys.modules"
                ),
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(
            completed.returncode,
            0,
            msg=completed.stderr or completed.stdout,
        )


if __name__ == "__main__":
    unittest.main()
