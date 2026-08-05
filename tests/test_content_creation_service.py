from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import imageio_ffmpeg
from PIL import Image

from src.content_creation.models import (
    ContentCreationError,
    ContentCreationRequest,
    ExecutionFlags,
    MusicRequestConfig,
    VoiceRequestConfig,
)
from src.content_creation.service import create_content


def _make_synthetic_source_video(root: Path) -> Path:
    """A tiny, deterministic, valid MP4 built on the fly - no repository fixture needed."""
    frames_dir = root / "synthetic_frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    for index in range(6):
        Image.new("RGB", (320, 180), (40 + index * 10, 60, 90)).save(frames_dir / f"frame_{index:03d}.png")
    output = root / "synthetic_source.mp4"
    command = [
        imageio_ffmpeg.get_ffmpeg_exe(),
        "-y",
        "-v",
        "error",
        "-framerate",
        "6",
        "-i",
        str(frames_dir / "frame_%03d.png"),
        "-pix_fmt",
        "yuv420p",
        "-c:v",
        "libx264",
        str(output),
    ]
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise RuntimeError(result.stderr)
    return output


class MusicValidationServiceTests(unittest.TestCase):
    def test_local_file_without_path_rejected_before_any_project_creation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            request = ContentCreationRequest(
                channel_id="nature_pulse",
                template_id="story_card_text_only_v1",
                text={"top": "x"},
                source_asset_path="projects/story_card_owl_test/final_test.mp4",
                music=MusicRequestConfig(mode="local_file", path=""),
                project_overrides={"projects_root": tmp},
            )
            with self.assertRaises(ContentCreationError) as ctx:
                create_content(request)
            self.assertEqual(ctx.exception.reason, "empty")
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_local_file_missing_on_disk_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            request = ContentCreationRequest(
                channel_id="nature_pulse",
                template_id="story_card_text_only_v1",
                text={"top": "x"},
                source_asset_path="projects/story_card_owl_test/final_test.mp4",
                music=MusicRequestConfig(mode="local_file", path="/no/such/track.mp3"),
                project_overrides={"projects_root": tmp},
            )
            with self.assertRaises(ContentCreationError) as ctx:
                create_content(request)
            self.assertEqual(ctx.exception.reason, "not_found")


class TemplateResolutionTests(unittest.TestCase):
    def test_unknown_template_id_raises_clear_error(self) -> None:
        request = ContentCreationRequest(channel_id="nature_pulse", template_id="does_not_exist_v1")
        with self.assertRaises(ContentCreationError):
            create_content(request)

    def test_missing_template_and_channel_default_raises(self) -> None:
        request = ContentCreationRequest()
        with self.assertRaises(ContentCreationError):
            create_content(request)

    def test_incompatible_format_and_template_raises(self) -> None:
        request = ContentCreationRequest(
            channel_id="nature_pulse",
            template_id="story_card_text_only_v1",
            format_id="longform",
        )
        with self.assertRaises(ContentCreationError):
            create_content(request)


class StoryCardCreateTests(unittest.TestCase):
    def test_dry_run_creates_no_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            request = ContentCreationRequest(
                channel_id="nature_pulse",
                template_id="story_card_text_only_v1",
                language="ru",
                text={"top": "Тестовый заголовок"},
                source_asset_path="projects/story_card_owl_test/final_test.mp4",
                execution=ExecutionFlags(dry_run=True),
                project_overrides={"projects_root": tmp},
            )
            result = create_content(request)
            self.assertEqual(result.status, "dry_run_completed")
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_missing_source_asset_raises_before_touching_disk(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            request = ContentCreationRequest(
                channel_id="nature_pulse",
                template_id="story_card_text_only_v1",
                text={"top": "x"},
                project_overrides={"projects_root": tmp},
            )
            with self.assertRaises(ContentCreationError):
                create_content(request)

    def test_prepare_only_renders_nothing_but_writes_render_request(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = _make_synthetic_source_video(Path(tmp))
            request = ContentCreationRequest(
                channel_id="nature_pulse",
                template_id="story_card_text_only_v1",
                language="ru",
                text={"top": "Тестовый заголовок"},
                source_asset_path=str(source),
                execution=ExecutionFlags(prepare_only=True),
                project_overrides={"projects_root": tmp},
            )
            result = create_content(request)
            self.assertEqual(result.status, "prepared_awaiting_render")
            self.assertNotIn("final_video", result.output_paths)
            self.assertTrue(Path(result.output_paths["render_request"]).is_file())


class FullscreenVoiceoverCreateTests(unittest.TestCase):
    def _fake_assets(self, root: Path) -> list[dict]:
        images = []
        for index in range(12):
            image = root / f"forest_{index:03d}.jpg"
            Image.new("RGB", (1080, 1920), (22 + index, 70, 55)).save(image)
            images.append(
                {
                    "path": str(image),
                    "rights_declaration": {
                        "confirmation_status": "approved",
                        "owner_approval_status": "approved",
                        "license_name": "user_owned",
                        "rights_status": "user_owned",
                    },
                }
            )
        return images

    def test_dry_run_stops_before_voice_stage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            request = ContentCreationRequest(
                channel_id="nature_science_news_ru",
                template_id="fullscreen_voiceover_v1",
                language="ru",
                topic="Почему кошки мурчат",
                completion_mode="draft_complete",
                voice=VoiceRequestConfig(provider="disabled"),
                execution=ExecutionFlags(dry_run=True),
                project_overrides={"projects_root": tmp},
            )
            result = create_content(request)
            self.assertEqual(result.status, "dry_run_completed")
            self.assertNotIn("voice", [s["stage"] for s in result.stages])

    def test_article_url_search_engine_rejected_before_any_project_creation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            request = ContentCreationRequest(
                channel_id="nature_science_news_ru",
                template_id="fullscreen_voiceover_v1",
                language="ru",
                content_input_mode="article_url",
                source_url="https://www.google.com/search?q=crows+remember+faces",
                project_overrides={"projects_root": tmp},
            )
            with self.assertRaises(ContentCreationError) as ctx:
                create_content(request)
            self.assertEqual(ctx.exception.reason, "search_engine_url")
            # No project directory should have been created for a rejected URL.
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_strict_topic_without_source_material_returns_clean_blocking_reason(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            request = ContentCreationRequest(
                channel_id="nature_science_news_ru",
                template_id="fullscreen_voiceover_v1",
                language="ru",
                content_input_mode="topic",
                topic="Почему вороны запоминают человеческие лица",
                execution=ExecutionFlags(prepare_only=True),
                project_overrides={"projects_root": tmp},
            )

            with self.assertRaises(ContentCreationError) as caught:
                create_content(request)

            self.assertEqual(caught.exception.reason, "insufficient_source_material")
            message = str(caught.exception).lower()
            for alternative in ("article", "source text", "draft", "template"):
                self.assertIn(alternative, message)

    def test_strict_topic_dry_run_returns_the_same_clean_blocking_reason(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            request = ContentCreationRequest(
                channel_id="nature_science_news_ru",
                template_id="fullscreen_voiceover_v1",
                language="ru",
                content_input_mode="topic",
                topic="Почему вороны запоминают человеческие лица",
                execution=ExecutionFlags(dry_run=True),
                project_overrides={"projects_root": tmp},
            )

            with self.assertRaises(ContentCreationError) as caught:
                create_content(request)

            self.assertEqual(caught.exception.reason, "insufficient_source_material")

    def test_progress_callback_is_invoked_for_story_card(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            request = ContentCreationRequest(
                channel_id="nature_pulse",
                template_id="story_card_text_only_v1",
                text={"top": "x"},
                source_asset_path="projects/story_card_owl_test/final_test.mp4",
                execution=ExecutionFlags(dry_run=True),
                project_overrides={"projects_root": tmp},
            )
            events: list[tuple[str, str]] = []
            create_content(request, progress_callback=lambda stage, status: events.append((stage, status)))
            self.assertIn(("project_create", "running"), events)
            self.assertIn(("project_create", "completed"), events)

    def test_default_run_stops_before_paid_generation_without_explicit_approval(self) -> None:
        from src.news.pipeline import create_news_to_short_job as real_create

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            request = ContentCreationRequest(
                channel_id="nature_science_news_ru",
                template_id="fullscreen_voiceover_v1",
                language="ru",
                topic="Почему листья меняют цвет осенью",
                completion_mode="draft_complete",
                voice=VoiceRequestConfig(provider="elevenlabs", profile="ru_dom"),
                project_overrides={"projects_root": tmp},
            )

            def _create_with_assets(**kwargs):
                kwargs["assets"] = self._fake_assets(root)
                return real_create(**kwargs)

            with patch("src.news.asset_manager.create_default_asset_providers", return_value=[]), patch(
                "src.news.pipeline.create_news_to_short_job", side_effect=_create_with_assets
            ):
                result = create_content(request)

            self.assertEqual(result.status, "prepared_awaiting_paid_approval")
            self.assertIn("Paid ElevenLabs generation was NOT performed", result.warnings[0])
            self.assertFalse(Path(result.project_root, "render", "final_render_manifest.json").exists())

    def test_paid_approval_writes_matching_approval_record(self) -> None:
        # This is the exact bug found via manual test: confirming paid generation
        # in the wizard still left voice_manifest at
        # status=provider_selection_required/audio_path="" because no approval.json
        # was ever written, so build_or_generate_voice_manifest(execute=True) fell
        # back to the safe stub. _create_paid_voice_approval must write a record
        # that src.audio.voice_workflow.is_final_generation_approved actually accepts.
        from src.audio.voice_workflow import voice_paths
        from src.content_creation.service import _create_paid_voice_approval

        with tempfile.TemporaryDirectory() as tmp:
            projects_root = Path(tmp)
            with patch("src.news.asset_manager.create_default_asset_providers", return_value=[]):
                from src.news.pipeline import create_news_to_short_job, run_news_to_short_job

                job = create_news_to_short_job(
                    projects_root=projects_root,
                    channel_id="nature_science_news_ru",
                    topic="Почему у зебр полосы",
                    language="ru",
                    completion_mode="draft_complete",
                )
                run_news_to_short_job(projects_root=projects_root, job_id=job.job_id, until_stage="script")

            project_root = projects_root / job.job_id
            request = ContentCreationRequest(
                channel_id="nature_science_news_ru",
                template_id="fullscreen_voiceover_v1",
                language="ru",
                voice=VoiceRequestConfig(provider="elevenlabs", profile="ru_dom", approve_paid_generation=True),
            )
            warning = _create_paid_voice_approval(root=project_root, job=job, request=request)
            self.assertEqual(warning, "")

            approval_path = voice_paths(project_root, "ru")["approval"]
            self.assertTrue(approval_path.is_file())
            approval = json.loads(approval_path.read_text(encoding="utf-8"))
            self.assertTrue(approval["approved"])
            self.assertEqual(approval["provider"], "elevenlabs")
            self.assertEqual(approval["voice_id"], "hDfThiytYnsDMuVgm6Qy")
            self.assertEqual(approval["model_id"], "eleven_multilingual_v2")

    def test_visual_brief_can_be_attached_on_resume_not_only_at_creation(self) -> None:
        """A real E2E run needed a visual_brief for scenes whose script.json already
        existed (untranslated Russian narration left the general per-scene query
        empty for every provider). Before this fix, --visual-brief was only ever
        merged into the job at creation - request.visual_briefs was silently ignored
        on resume. The merge is additive: a brief attached on an earlier resume must
        not be erased by a later resume that only supplies a different scene's brief."""
        from src.news.pipeline import create_news_to_short_job

        with tempfile.TemporaryDirectory() as tmp:
            projects_root = Path(tmp)
            with patch("src.news.asset_manager.create_default_asset_providers", return_value=[]):
                job = create_news_to_short_job(
                    projects_root=projects_root,
                    channel_id="nature_science_news_ru",
                    topic="Почему косатки взрывают рыбу",
                    language="ru",
                )
            from src.news.project_store import NewsProjectStore

            store = NewsProjectStore(projects_root)
            job.visual_briefs = {"scene_001": {"subject": "orca"}}
            store.save_job(job)

            request = ContentCreationRequest(
                project_id=job.job_id,
                channel_id="nature_science_news_ru",
                template_id="fullscreen_voiceover_v1",
                language="ru",
                visual_briefs={"scene_002": {"subject": "ocean sunfish"}},
                execution=ExecutionFlags(resume=True),
                project_overrides={"projects_root": str(projects_root)},
            )
            with patch("src.news.asset_manager.create_default_asset_providers", return_value=[]), patch(
                "src.news.pipeline.run_news_to_short_job"
            ):
                try:
                    create_content(request)
                except Exception:
                    pass  # only the persisted job state matters for this test

            reloaded = store.load_job(job.job_id)
            self.assertEqual(reloaded.visual_briefs["scene_001"], {"subject": "orca"})
            self.assertEqual(reloaded.visual_briefs["scene_002"], {"subject": "ocean sunfish"})

    def test_force_stage_flows_from_request_to_the_asset_search_resume_call(self) -> None:
        """A real E2E run needed to re-run visual_plan/asset_search after a wiring fix
        for a project whose stages were already marked completed. The canonical
        service had no way to do that - only pipeline.py's legacy --force-stage did.
        This is the wiring test for the fix: ExecutionFlags.force_stage must reach
        run_news_to_short_job's own force_stage, without touching the voice call
        (never forces a paid TTS re-run by itself)."""
        from src.news.pipeline import create_news_to_short_job

        with tempfile.TemporaryDirectory() as tmp:
            projects_root = Path(tmp)
            with patch("src.news.asset_manager.create_default_asset_providers", return_value=[]):
                job = create_news_to_short_job(
                    projects_root=projects_root,
                    channel_id="nature_science_news_ru",
                    topic="Почему у зебр полосы",
                    language="ru",
                )
            request = ContentCreationRequest(
                project_id=job.job_id,
                channel_id="nature_science_news_ru",
                template_id="fullscreen_voiceover_v1",
                language="ru",
                execution=ExecutionFlags(resume=True, force_stage=True),
                project_overrides={"projects_root": str(projects_root)},
            )
            with patch("src.news.asset_manager.create_default_asset_providers", return_value=[]), patch(
                "src.news.pipeline.run_news_to_short_job"
            ) as mocked:
                mocked.return_value.completed_stages = []
                mocked.return_value.status = "in_progress"
                try:
                    create_content(request)
                except Exception:
                    pass  # only the call arguments matter for this test

            asset_search_call = next(
                call for call in mocked.call_args_list if call.kwargs.get("until_stage") == "asset_search"
            )
            self.assertTrue(asset_search_call.kwargs.get("force_stage"))

    def test_force_stage_flows_from_request_to_the_final_render_resume_call(self) -> None:
        """PLAN-STAB-2 wiring test: the render/export phase's explicit
        ``stage="final_render"`` call must also receive ``ExecutionFlags.force_stage``,
        the same existing contract already wired to the asset_search resume call above,
        otherwise --force-stage would have no way to force a completed final_render to
        re-run."""
        from src.news.pipeline import create_news_to_short_job

        with tempfile.TemporaryDirectory() as tmp:
            projects_root = Path(tmp)
            with patch("src.news.asset_manager.create_default_asset_providers", return_value=[]):
                job = create_news_to_short_job(
                    projects_root=projects_root,
                    channel_id="nature_science_news_ru",
                    topic="Почему у зебр полосы",
                    language="ru",
                )
            request = ContentCreationRequest(
                project_id=job.job_id,
                channel_id="nature_science_news_ru",
                template_id="fullscreen_voiceover_v1",
                language="ru",
                execution=ExecutionFlags(resume=True, force_stage=True),
                project_overrides={"projects_root": str(projects_root)},
            )
            with patch("src.news.asset_manager.create_default_asset_providers", return_value=[]), patch(
                "src.news.pipeline.run_news_to_short_job"
            ) as mocked:
                mocked.return_value.completed_stages = []
                mocked.return_value.status = "in_progress"
                try:
                    create_content(request)
                except Exception:
                    pass  # only the call arguments matter for this test

            final_render_call = next(
                call for call in mocked.call_args_list if call.kwargs.get("stage") == "final_render"
            )
            self.assertTrue(final_render_call.kwargs.get("force_stage"))

    def test_explicit_profile_resolves_globally_for_channel_without_voices_yaml(self) -> None:
        # This is the exact bug report: nature_pulse has no voices.yaml of its own, but
        # the user explicitly passed --voice-profile ru_dom (registered in
        # nature_science_news_ru's voices.yaml). An explicit profile must resolve
        # globally and take priority over the channel's own (nonexistent) default.
        from src.audio.voice_workflow import voice_paths
        from src.content_creation.service import _create_paid_voice_approval

        with tempfile.TemporaryDirectory() as tmp:
            projects_root = Path(tmp)
            with patch("src.news.asset_manager.create_default_asset_providers", return_value=[]):
                from src.news.pipeline import create_news_to_short_job, run_news_to_short_job

                job = create_news_to_short_job(
                    projects_root=projects_root,
                    channel_id="nature_pulse",
                    topic="x",
                    language="ru",
                    completion_mode="draft_complete",
                )
                run_news_to_short_job(projects_root=projects_root, job_id=job.job_id, until_stage="script")

            project_root = projects_root / job.job_id
            request = ContentCreationRequest(
                channel_id="nature_pulse",
                template_id="fullscreen_voiceover_v1",
                language="ru",
                voice=VoiceRequestConfig(provider="elevenlabs", profile="ru_dom", approve_paid_generation=True),
            )
            warning = _create_paid_voice_approval(root=project_root, job=job, request=request)
            self.assertEqual(warning, "")
            approval_path = voice_paths(project_root, "ru")["approval"]
            self.assertTrue(approval_path.is_file())
            approval = json.loads(approval_path.read_text(encoding="utf-8"))
            self.assertEqual(approval["provider"], "elevenlabs")
            self.assertEqual(approval["voice_id"], "hDfThiytYnsDMuVgm6Qy")
            self.assertEqual(approval["model_id"], "eleven_multilingual_v2")

    def test_unresolvable_profile_on_channel_without_voices_yaml_warns_not_crash(self) -> None:
        from src.content_creation.service import _create_paid_voice_approval

        with tempfile.TemporaryDirectory() as tmp:
            projects_root = Path(tmp)
            with patch("src.news.asset_manager.create_default_asset_providers", return_value=[]):
                from src.news.pipeline import create_news_to_short_job, run_news_to_short_job

                job = create_news_to_short_job(
                    projects_root=projects_root,
                    channel_id="nature_pulse",
                    topic="x",
                    language="ru",
                    completion_mode="draft_complete",
                )
                run_news_to_short_job(projects_root=projects_root, job_id=job.job_id, until_stage="script")

            project_root = projects_root / job.job_id
            request = ContentCreationRequest(
                channel_id="nature_pulse",
                template_id="fullscreen_voiceover_v1",
                language="ru",
                voice=VoiceRequestConfig(provider="elevenlabs", profile="does_not_exist_anywhere", approve_paid_generation=True),
            )
            warning = _create_paid_voice_approval(root=project_root, job=job, request=request)
            self.assertNotEqual(warning, "")
            self.assertIn("Could not resolve", warning)

    def test_preflight_summary_shown_before_paid_approval_for_channel_without_voices_yaml(self) -> None:
        # Item 3 of the bug report: before any paid call, show display_name/model/
        # character_count/scene_count/cache state via the existing (unmodified)
        # narration_workflow.prepare_final - and approval.json must NOT exist yet
        # (only created after --approve-paid-generation).
        from src.audio.tts.base_provider import TTSProvider
        from src.audio.tts.elevenlabs_provider import ElevenLabsProvider
        from src.audio.voice_workflow import voice_paths
        from src.news.pipeline import create_news_to_short_job as real_create

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            def _create_with_assets(**kwargs):
                kwargs["assets"] = self._fake_assets(root)
                return real_create(**kwargs)

            request = ContentCreationRequest(
                channel_id="nature_pulse",
                template_id="fullscreen_voiceover_v1",
                language="ru",
                topic="Почему у зебр полосы",
                completion_mode="draft_complete",
                voice=VoiceRequestConfig(provider="elevenlabs", profile="ru_dom"),
                project_overrides={"projects_root": tmp},
            )
            with patch("src.news.asset_manager.create_default_asset_providers", return_value=[]), patch(
                "src.news.pipeline.create_news_to_short_job", side_effect=_create_with_assets
            ), patch.object(ElevenLabsProvider, "preflight", TTSProvider.preflight):
                result = create_content(request)

            self.assertEqual(result.status, "prepared_awaiting_paid_approval")
            self.assertEqual(result.evidence.get("voice_name"), "Dom")
            self.assertEqual(result.evidence.get("model_id"), "eleven_multilingual_v2")
            self.assertIn("character_count", result.evidence)
            self.assertIn("scene_count", result.evidence)
            self.assertIn("cache_ready_scenes", result.evidence)
            self.assertIn("preflight", result.evidence)
            # No approval.json until the user explicitly approves the paid call.
            approval_path = voice_paths(Path(result.project_root), "ru")["approval"]
            self.assertFalse(approval_path.is_file())

    def test_resume_with_explicit_profile_override_for_nature_pulse_project(self) -> None:
        # Reproduces the exact reported scenario: an existing fullscreen_voiceover_v1
        # project under channel "nature_pulse" (no voices.yaml), resumed with explicit
        # --voice-provider elevenlabs --voice-profile ru_dom. Must not recreate the
        # project, must not change channel_id, and must not re-run asset_search.
        from src.news.pipeline import create_news_to_short_job as real_create

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            def _create_with_assets(**kwargs):
                kwargs["assets"] = self._fake_assets(root)
                return real_create(**kwargs)

            with patch("src.news.asset_manager.create_default_asset_providers", return_value=[]), patch(
                "src.news.pipeline.create_news_to_short_job", side_effect=_create_with_assets
            ):
                first_request = ContentCreationRequest(
                    channel_id="nature_pulse",
                    template_id="fullscreen_voiceover_v1",
                    language="ru",
                    topic="В видео используются архивные материалы",
                    completion_mode="draft_complete",
                    voice=VoiceRequestConfig(provider="disabled"),
                    project_overrides={"projects_root": tmp},
                )
                first_result = create_content(first_request)
                project_id = first_result.project_id
                original_channel_id = json.loads(
                    (Path(tmp) / project_id / "job.json").read_text(encoding="utf-8")
                )["channel_id"]
                self.assertEqual(original_channel_id, "nature_pulse")

                resume_request = ContentCreationRequest(
                    project_id=project_id,
                    channel_id="nature_pulse",
                    template_id="fullscreen_voiceover_v1",
                    language="ru",
                    voice=VoiceRequestConfig(provider="elevenlabs", profile="ru_dom"),
                    execution=ExecutionFlags(resume=True),
                    project_overrides={"projects_root": tmp},
                )
                with patch(
                    "src.news.pipeline.create_news_to_short_job",
                    side_effect=AssertionError("must not recreate/re-download on resume"),
                ):
                    resume_result = create_content(resume_request)

            self.assertEqual(resume_result.project_id, project_id)
            self.assertEqual(resume_result.status, "prepared_awaiting_paid_approval")
            resumed_channel_id = json.loads(
                (Path(tmp) / project_id / "job.json").read_text(encoding="utf-8")
            )["channel_id"]
            self.assertEqual(resumed_channel_id, "nature_pulse")
            # The explicit profile must have been used for the (not-yet-approved) evidence.
            self.assertEqual(resume_result.evidence.get("voice_profile"), "ru_dom")

    def test_paid_approval_actually_produces_audio_end_to_end(self) -> None:
        # Full path, network-free: confirms execute_voice=True driven by
        # approve_paid_generation actually reaches a real (faked) synthesis call
        # and the resulting voice_manifest has a real audio_path - not just that
        # the boolean flag was computed correctly in isolation.
        import wave

        from src.audio.tts.models import SOURCE_GENERATED, TTSResult
        from src.news.pipeline import create_news_to_short_job as real_create

        def fake_synthesize(self, request):
            path = Path(request.output_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            with wave.open(str(path), "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(48000)
                wav_file.writeframes(b"\x00\x00" * 48000)
            return TTSResult(
                provider="elevenlabs",
                language=request.language,
                scene_id=request.scene_id,
                audio_path=str(path),
                duration_sec=1.0,
                sample_rate=48000,
                channels=1,
                source_type=SOURCE_GENERATED,
            )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            def _create_with_assets(**kwargs):
                kwargs["assets"] = self._fake_assets(root)
                return real_create(**kwargs)

            request = ContentCreationRequest(
                channel_id="nature_science_news_ru",
                template_id="fullscreen_voiceover_v1",
                language="ru",
                topic="Почему у зебр полосы",
                completion_mode="draft_complete",
                voice=VoiceRequestConfig(provider="elevenlabs", profile="ru_dom", approve_paid_generation=True),
                project_overrides={"projects_root": tmp},
            )
            with patch("src.news.asset_manager.create_default_asset_providers", return_value=[]), patch(
                "src.news.pipeline.create_news_to_short_job", side_effect=_create_with_assets
            ), patch("src.audio.tts.elevenlabs_provider.ElevenLabsProvider.synthesize", new=fake_synthesize):
                result = create_content(request)

            self.assertNotEqual(result.status, "prepared_awaiting_paid_approval")
            voice_manifest_path = Path(
                result.project_root, "localizations", "ru", "voice", "voice_manifest.json"
            )
            manifest = json.loads(voice_manifest_path.read_text(encoding="utf-8"))
            self.assertTrue(manifest.get("audio_path"))
            self.assertTrue(manifest.get("paid_call_performed"))

    def test_resume_preserves_project_id_and_does_not_recreate_job(self) -> None:
        from src.news.pipeline import create_news_to_short_job as real_create

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            def _create_with_assets(**kwargs):
                kwargs["assets"] = self._fake_assets(root)
                return real_create(**kwargs)

            with patch("src.news.asset_manager.create_default_asset_providers", return_value=[]), patch(
                "src.news.pipeline.create_news_to_short_job", side_effect=_create_with_assets
            ):
                first_request = ContentCreationRequest(
                    channel_id="nature_science_news_ru",
                    template_id="fullscreen_voiceover_v1",
                    language="ru",
                    topic="Почему совы бесшумно летают",
                    voice=VoiceRequestConfig(provider="elevenlabs", profile="ru_dom"),
                    project_overrides={
                        "projects_root": tmp,
                        "script_provider": "legacy_template",
                    },
                )
                first_result = create_content(first_request)
                self.assertEqual(first_result.status, "prepared_awaiting_paid_approval")
                project_id = first_result.project_id

                resume_request = ContentCreationRequest(
                    project_id=project_id,
                    channel_id="nature_science_news_ru",
                    template_id="fullscreen_voiceover_v1",
                    language="ru",
                    completion_mode="draft_complete",
                    voice=VoiceRequestConfig(provider="elevenlabs", profile="ru_dom"),
                    execution=ExecutionFlags(resume=True),
                    project_overrides={"projects_root": tmp},
                )
                with patch(
                    "src.news.pipeline.create_news_to_short_job", side_effect=AssertionError("must not recreate job on resume")
                ):
                    resume_result = create_content(resume_request)

            self.assertEqual(resume_result.project_id, project_id)
            self.assertEqual(resume_result.status, "prepared_awaiting_paid_approval")
            self.assertIn("asset_search", [stage["stage"] for stage in resume_result.stages])
            stored = json.loads(
                Path(tmp, project_id, "job.json").read_text(encoding="utf-8")
            )
            self.assertEqual(stored["completion"]["mode"], "draft_complete")

    def test_voice_disabled_runs_through_quality_check(self) -> None:
        from src.content_creation.models import SubtitleRequestConfig
        from src.news.pipeline import create_news_to_short_job as real_create

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            def _create_with_assets(**kwargs):
                kwargs["assets"] = self._fake_assets(root)
                return real_create(**kwargs)

            request = ContentCreationRequest(
                channel_id="nature_science_news_ru",
                template_id="fullscreen_voiceover_v1",
                language="ru",
                topic="Почему совы бесшумно летают",
                voice=VoiceRequestConfig(provider="disabled"),
                subtitles=SubtitleRequestConfig(style="disabled"),
                project_overrides={
                    "projects_root": tmp,
                    "script_provider": "legacy_template",
                },
            )
            with patch("src.news.asset_manager.create_default_asset_providers", return_value=[]), patch(
                "src.news.pipeline.create_news_to_short_job", side_effect=_create_with_assets
            ):
                result = create_content(request)

            # Voice disabled -> no ElevenLabs call is ever attempted (no network,
            # no cost); the quality gate has the final say on whether final_render
            # runs, rather than this workflow silently producing a video the
            # quality check would have blocked.
            self.assertIn(result.status, {"needs_review", "completed"})
            self.assertIn("quality_check", [s["stage"] for s in result.stages])

    def test_manual_wav_requires_no_paid_approval(self) -> None:
        import wave

        from src.news.pipeline import create_news_to_short_job as real_create

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audio_path = root / "manual.wav"
            with wave.open(str(audio_path), "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(48000)
                wav_file.writeframes(b"\x00\x00" * 48000 * 2)

            def _create_with_assets(**kwargs):
                kwargs["assets"] = self._fake_assets(root)
                return real_create(**kwargs)

            request = ContentCreationRequest(
                channel_id="nature_science_news_ru",
                template_id="fullscreen_voiceover_v1",
                language="ru",
                topic="Почему у зебр полосы",
                completion_mode="draft_complete",
                voice=VoiceRequestConfig(provider="audio_file", audio_file=str(audio_path)),
                project_overrides={"projects_root": tmp},
            )
            with patch("src.news.asset_manager.create_default_asset_providers", return_value=[]), patch(
                "src.news.pipeline.create_news_to_short_job", side_effect=_create_with_assets
            ):
                result = create_content(request)

            # Manual WAV is not paid - it must never land in the paid-approval gate,
            # even though --approve-paid-generation was never passed.
            self.assertNotEqual(result.status, "prepared_awaiting_paid_approval")
            self.assertIn("manual_audio_import", [s["stage"] for s in result.stages])
            voice_manifest_path = Path(result.project_root, "localizations", "ru", "voice", "voice_manifest.json")
            manifest = json.loads(voice_manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["provider"], "audio_file")
            self.assertAlmostEqual(manifest["duration_sec"], 2.0, places=2)
            from src.news.project_store import NewsProjectStore

            stored = NewsProjectStore(tmp).load_job(result.project_id)
            self.assertEqual(stored.stages["voice"].status, "completed")
            self.assertIsNotNone(stored.stages["voice"].finished_at)
            self.assertEqual(stored.localizations["ru"].voice_status, "completed")


class MusicWiringTests(unittest.TestCase):
    """A requested local track must actually reach the renderer.

    src/news/final_renderer.py has always been able to loop, sidechain-duck and mix
    a music bed, gated on assets/music/music_manifest.json - which nothing wrote, so
    the option was dead. The service now writes it before the render.
    """

    def _wav(self, path: Path, seconds: float = 0.3) -> Path:
        import wave

        path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(path), "wb") as handle:
            handle.setnchannels(1)
            handle.setsampwidth(2)
            handle.setframerate(8000)
            handle.writeframes(b"\x00\x00" * int(8000 * seconds))
        return path

    def test_manifest_is_written_where_the_renderer_reads_it(self) -> None:
        from src.audio.music_manifest import prepare_project_music, read_music_manifest
        from src.news.final_renderer import _load_music_manifest

        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "project"
            track = self._wav(Path(tmp) / "bed.wav")
            prepare_project_music(project_root, track, volume=0.18)

            # The renderer's own loader must see exactly what the writer produced.
            self.assertEqual(_load_music_manifest(project_root), read_music_manifest(project_root))
            self.assertAlmostEqual(_load_music_manifest(project_root)["volume"], 0.18)

    def test_music_request_with_a_missing_file_is_rejected_before_any_work(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            request = ContentCreationRequest(
                channel_id="nature_science_news_ru",
                template_id="fullscreen_voiceover_v1",
                language="ru",
                topic="Тема",
                music=MusicRequestConfig(mode="local_file", path="/no/such/track.mp3"),
                project_overrides={"projects_root": tmp},
            )
            with self.assertRaises(ContentCreationError):
                create_content(request)
            self.assertEqual(list(Path(tmp).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
