from __future__ import annotations

import json
import tempfile
import unittest
import wave
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import Mock, patch


def _voice_preflight_approved():
    """Grant only the voice_preflight class for a test that owns preflight.

    The legacy voice CLI has no approval flag of its own, so PLAN-STAB-4 leaves
    it fail-closed in production; tests that exercise its mechanics on fakes
    grant the class explicitly instead of weakening the boundary.
    """
    from src.runtime_network import (
        NETWORK_ACTION_VOICE_PREFLIGHT,
        approval_for_actions,
        network_approval_scope,
    )

    return network_approval_scope(
        approval_for_actions(
            [NETWORK_ACTION_VOICE_PREFLIGHT],
            granted_by="test_voice_workflow",
        )
    )


def _voice_audition_approved():
    """Grant preflight *and* synthesis for the one test that pays.

    The audition action does not stop at reading the account: it performs a real
    paid POST (its own manifest records ``paid_call_performed: True``). Before
    2026-08-17 that call had no network class at all, so granting preflight was
    enough to reach it - which is exactly the defect the class split closed. The
    two classes are named here together because this path genuinely uses both,
    and never widened in the shared helper above.
    """
    from src.runtime_network import (
        NETWORK_ACTION_VOICE_PREFLIGHT,
        NETWORK_ACTION_VOICE_SYNTHESIS,
        approval_for_actions,
        network_approval_scope,
    )

    return network_approval_scope(
        approval_for_actions(
            [NETWORK_ACTION_VOICE_PREFLIGHT, NETWORK_ACTION_VOICE_SYNTHESIS],
            granted_by="test_voice_workflow",
        )
    )


class VoiceWorkflowTests(unittest.TestCase):
    def test_tts_cache_key_changes_for_voice_model_language_text_and_settings(self) -> None:
        from src.audio.tts.models import TTSRequest, compute_tts_cache_key

        base = TTSRequest(
            job_id="job_001",
            localization_id="ru",
            scene_id="scene_001",
            provider="elevenlabs",
            language="ru",
            text="Привет",
            voice_id="voice-a",
            model_id="eleven_multilingual_v2",
            settings={"speed": 1.02},
        )
        changed_voice = base.with_updates(voice_id="voice-b")
        changed_text = base.with_updates(text="Здравствуйте")

        self.assertNotEqual(compute_tts_cache_key(base), compute_tts_cache_key(changed_voice))
        self.assertNotEqual(compute_tts_cache_key(base), compute_tts_cache_key(changed_text))

    def test_audio_file_provider_imports_user_audio_without_paid_fallback(self) -> None:
        from src.audio.tts.audio_file_provider import AudioFileProvider
        from src.audio.tts.models import SOURCE_USER_PROVIDED, TTSRequest

        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "voice.wav"
            with wave.open(str(source), "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(16000)
                wav.writeframes(b"\x00\x00" * 16000)

            request = TTSRequest(
                job_id="job_001",
                localization_id="ru",
                scene_id=None,
                provider="audio_file",
                language="ru",
                text="",
                audio_file=str(source),
                output_path=str(Path(tmp) / "normalized.wav"),
            )
            result = AudioFileProvider().synthesize(request)

            self.assertEqual(result.source_type, SOURCE_USER_PROVIDED)
            self.assertEqual(result.provider, "audio_file")
            self.assertAlmostEqual(result.duration_sec, 1.0, places=2)
            self.assertTrue(Path(result.audio_path).is_file())

    def test_approval_is_bound_to_script_and_settings_hash(self) -> None:
        from src.audio.tts.models import TTSRequest, compute_settings_hash, compute_text_hash
        from src.audio.voice_workflow import VoiceApproval, is_final_generation_approved

        request = TTSRequest(
            job_id="job_001",
            localization_id="ru",
            provider="elevenlabs",
            language="ru",
            text="Финальный сценарий",
            voice_id="hDfThiytYnsDMuVgm6Qy",
            voice_name="Dom",
            model_id="eleven_multilingual_v2",
            settings={"speed": 1.02},
        )
        approval = VoiceApproval(
            approved=True,
            scope="job",
            provider=request.provider,
            voice_id=request.voice_id,
            voice_name=request.voice_name,
            model_id=request.model_id,
            language=request.language,
            script_hash=compute_text_hash(request.text),
            settings_hash=compute_settings_hash(request.settings),
            approved_at="2026-07-18T09:30:00+03:00",
        )

        self.assertTrue(is_final_generation_approved(request, approval))
        self.assertFalse(is_final_generation_approved(request.with_updates(text="Другой сценарий"), approval))
        self.assertFalse(is_final_generation_approved(request.with_updates(settings={"speed": 0.95}), approval))

    def test_elevenlabs_preflight_never_calls_synthesis_endpoint(self) -> None:
        from src.audio.tts.elevenlabs_provider import ElevenLabsProvider
        from src.audio.tts.models import TTSRequest

        http = Mock()
        http.get.side_effect = [
            Mock(status_code=200, json=lambda: {"character_count": 1000, "character_limit": 10000}),
            Mock(status_code=200, json=lambda: {"voices": [{"voice_id": "hDfThiytYnsDMuVgm6Qy", "name": "Dom"}]}),
            Mock(status_code=200, json=lambda: {"can_use_instant_voice_cloning": True}),
        ]
        request = TTSRequest(
            job_id="job_001",
            localization_id="ru",
            provider="elevenlabs",
            language="ru",
            text="Короткая проба",
            voice_id="hDfThiytYnsDMuVgm6Qy",
            voice_name="Dom",
            model_id="eleven_multilingual_v2",
        )

        # This test owns "preflight is read-only", not the PLAN-STAB-4 gate, so
        # it grants the one class preflight belongs to. That preflight is denied
        # without the grant is covered by tests/test_runtime_network_boundary.py.
        with _voice_preflight_approved():
            plan = ElevenLabsProvider(api_key="test-key", http_client=http).preflight(request)

        self.assertTrue(plan.api_key_present)
        self.assertTrue(plan.voice_available)
        self.assertEqual(plan.character_count, len("Короткая проба"))
        called_urls = [call.args[0] for call in http.get.call_args_list]
        self.assertFalse(any("/text-to-speech/" in url for url in called_urls))
        self.assertFalse(http.post.called)

    def test_loads_saved_voice_profiles_without_secret_values(self) -> None:
        from src.audio.voice_cli import load_voice_profiles
        from src.config_resolver.paths import resolve_application_paths

        channels_root = resolve_application_paths().channels_root
        profiles = load_voice_profiles(
            str(channels_root / "nature_science_news_ru" / "voices.yaml")
        )

        self.assertIn("ru_dom", profiles)
        self.assertEqual(profiles["ru_dom"].voice_id, "hDfThiytYnsDMuVgm6Qy")
        self.assertEqual(profiles["ru_dom"].model_id, "eleven_multilingual_v2")
        self.assertNotIn("api_key", profiles["ru_dom"].settings)

    def test_import_manual_audio_marks_voice_completed_and_user_provided(self) -> None:
        from src.audio.voice_workflow import import_manual_audio

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audio = root / "manual.wav"
            with wave.open(str(audio), "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(16000)
                wav.writeframes(b"\x00\x00" * 16000)

            manifest = import_manual_audio(
                project_root=root,
                job_id="job_001",
                language="ru",
                audio_file=str(audio),
            )

            self.assertEqual(manifest["status"], "completed")
            self.assertEqual(manifest["source_type"], "user_provided")
            self.assertFalse(manifest["paid_call_performed"])
            self.assertTrue((root / "localizations" / "ru" / "voice" / "narration.wav").is_file())

    def test_create_voice_approval_record_writes_hash_bound_approval(self) -> None:
        from src.audio.voice_workflow import create_voice_approval_record

        with tempfile.TemporaryDirectory() as tmp:
            approval = create_voice_approval_record(
                project_root=Path(tmp),
                language="ru",
                scope="job",
                provider="elevenlabs",
                voice_id="hDfThiytYnsDMuVgm6Qy",
                voice_name="Dom",
                model_id="eleven_multilingual_v2",
                script_text="Финальный сценарий",
                settings={"speed": 1.02},
                approved_at="2026-07-18T10:30:00+03:00",
            )

            self.assertTrue(approval.approved)
            self.assertTrue((Path(tmp) / "localizations" / "ru" / "voice" / "approval.json").is_file())
            self.assertEqual(approval.scope, "job")

    def test_voice_cli_import_audio_uses_project_job_id(self) -> None:
        from argparse import Namespace
        from src.news.models import INPUT_MODE_TOPIC, NewsJob
        from src.news.project_store import NewsProjectStore
        from src.audio.voice_cli import run_voice_cli

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            job = NewsJob.create(
                channel_id="nature_science_news_ru",
                input_mode=INPUT_MODE_TOPIC,
                topic="Тест",
                language="ru",
                now="2026-07-18T10:30:00+03:00",
            )
            job.job_id = "job_001"
            NewsProjectStore(root).create_project(job)
            job_root = root / "job_001"
            audio = root / "manual.wav"
            with wave.open(str(audio), "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(16000)
                wav.writeframes(b"\x00\x00" * 16000)

            with redirect_stdout(StringIO()):
                code = run_voice_cli(
                    Namespace(
                        voice_action="import-audio",
                        projects_root=str(root),
                        job_id="job_001",
                        language="ru",
                        audio_file=str(audio),
                        news_channel="nature_science_news_ru",
                        provider=None,
                    )
                )

            self.assertEqual(code, 0)
            self.assertTrue((job_root / "localizations" / "ru" / "voice" / "voice_manifest.json").is_file())
            loaded = NewsProjectStore(root).load_job("job_001")
            self.assertEqual(loaded.localizations["ru"].voice_status, "completed")


    def test_audition_action_end_to_end_writes_manifest_and_respects_cache(self) -> None:
        from argparse import Namespace
        from src.audio.voice_cli import run_voice_cli

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            job_id = "job_001"
            def fake_get(url, headers=None, timeout=None):
                if url.endswith("/user/subscription"):
                    return Mock(status_code=200, json=lambda: {"character_limit": 10000, "character_count": 100})
                if url.endswith("/voices"):
                    return Mock(status_code=200, json=lambda: {"voices": [{"voice_id": "hDfThiytYnsDMuVgm6Qy", "name": "Dom"}]})
                if url.endswith("/models"):
                    return Mock(status_code=200, json=lambda: [{"model_id": "eleven_multilingual_v2"}])
                return Mock(status_code=404, json=lambda: {})

            fake_http = Mock()
            fake_http.get.side_effect = fake_get
            fake_http.post.return_value = Mock(status_code=200, content=b"RIFF....WAVEfmt ")

            # The audition path runs a preflight and then pays, so this test
            # grants both classes it exercises. The paid gate itself stays with
            # the existing VoiceApproval owner, unchanged.
            with _voice_audition_approved(), patch("src.audio.voice_cli.ElevenLabsProvider") as provider_cls:
                from src.audio.tts.elevenlabs_provider import ElevenLabsProvider as RealProvider

                provider_cls.return_value = RealProvider(api_key="test-key", http_client=fake_http)
                with redirect_stdout(StringIO()):
                    code = run_voice_cli(
                        Namespace(
                            voice_action="audition",
                            projects_root=str(root),
                            job_id=job_id,
                            language="ru",
                            text="Короткая проба голоса.",
                            voice_profile="ru_dom",
                            voice_id=None,
                            provider=None,
                            news_channel="nature_science_news_ru",
                        )
                    )
            self.assertEqual(code, 0)
            manifest_path = root / job_id / "localizations" / "ru" / "voice" / "voice_manifest.json"
            self.assertTrue(manifest_path.is_file())
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["status"], "awaiting_voice_approval")
            self.assertTrue(manifest["paid_call_performed"])
            self.assertEqual(fake_http.post.call_count, 1)

            # Re-running the same audition must hit the cached preview file, not call again.
            with _voice_audition_approved(), patch("src.audio.voice_cli.ElevenLabsProvider") as provider_cls2:
                provider_cls2.return_value = RealProvider(api_key="test-key", http_client=fake_http)
                with redirect_stdout(StringIO()):
                    run_voice_cli(
                        Namespace(
                            voice_action="audition",
                            projects_root=str(root),
                            job_id=job_id,
                            language="ru",
                            text="Короткая проба голоса.",
                            voice_profile="ru_dom",
                            voice_id=None,
                            provider=None,
                            news_channel="nature_science_news_ru",
                        )
                    )
            self.assertEqual(fake_http.post.call_count, 1, "cached audition must not trigger a second paid call")


class TTSProviderManagerTests(unittest.TestCase):
    def test_paid_provider_requires_approval(self) -> None:
        from src.audio.tts.base_provider import TTSProvider
        from src.audio.tts.models import TTSRequest, TTSResult
        from src.audio.tts.provider_manager import TTSProviderManager

        class PaidStub(TTSProvider):
            name = "paid_stub"
            paid = True

            def synthesize(self, request: TTSRequest) -> TTSResult:
                return TTSResult(
                    provider=self.name, language=request.language, scene_id=request.scene_id,
                    audio_path=request.output_path or "", duration_sec=1.0, sample_rate=48000, channels=1,
                )

        manager = TTSProviderManager()
        manager.register(PaidStub())
        request = TTSRequest(job_id="j", localization_id="ru", provider="paid_stub", language="ru", text="hi")

        with self.assertRaises(PermissionError):
            manager.synthesize(request, approved=False)

        result = manager.synthesize(request, approved=True)
        self.assertEqual(result.provider, "paid_stub")

    def test_free_provider_does_not_require_approval(self) -> None:
        from src.audio.tts.audio_file_provider import AudioFileProvider
        from src.audio.tts.models import TTSRequest
        from src.audio.tts.provider_manager import TTSProviderManager

        manager = TTSProviderManager()
        manager.register(AudioFileProvider())
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "voice.wav"
            with wave.open(str(source), "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(16000)
                wav.writeframes(b"\x00\x00" * 16000)
            request = TTSRequest(
                job_id="j", localization_id="ru", provider="audio_file", language="ru", text="",
                audio_file=str(source), output_path=str(Path(tmp) / "out.wav"),
            )
            result = manager.synthesize(request, approved=False)
            self.assertEqual(result.provider, "audio_file")

    def test_unregistered_provider_raises_key_error(self) -> None:
        from src.audio.tts.models import TTSRequest
        from src.audio.tts.provider_manager import TTSProviderManager

        manager = TTSProviderManager()
        request = TTSRequest(job_id="j", localization_id="ru", provider="nonexistent", language="ru", text="")
        with self.assertRaises(KeyError):
            manager.synthesize(request, approved=True)


if __name__ == "__main__":
    unittest.main()
