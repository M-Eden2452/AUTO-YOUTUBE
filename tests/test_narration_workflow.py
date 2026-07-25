from __future__ import annotations

import tempfile
import unittest
import wave
from pathlib import Path

from src.audio.tts.base_provider import TTSProvider
from src.audio.tts.models import SOURCE_GENERATED, TTSRequest, TTSResult, VoiceProfile, compute_settings_hash, compute_text_hash
from src.audio.tts.provider_manager import TTSProviderManager
from src.audio.narration_models import build_narration_request_from_scenes
from src.audio.voice_policy import VoicePolicy
from src.audio.voice_workflow import VoiceApproval


def _write_wav(path: Path, seconds: float = 0.5) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(48000)
        wav.writeframes(b"\x00\x00" * int(48000 * seconds))


class FakePaidProvider(TTSProvider):
    name = "fake_paid"
    paid = True

    def __init__(self, *, fail_scene_ids: set[str] | None = None) -> None:
        self.calls = 0
        self.fail_scene_ids = fail_scene_ids or set()

    def synthesize(self, request: TTSRequest) -> TTSResult:
        self.calls += 1
        if request.scene_id in self.fail_scene_ids:
            raise ValueError(f"synthesis failed for {request.scene_id}")
        out = Path(request.output_path)
        _write_wav(out, 0.5)
        return TTSResult(
            provider=self.name, language=request.language, scene_id=request.scene_id, audio_path=str(out),
            duration_sec=0.5, sample_rate=48000, channels=1, source_type=SOURCE_GENERATED,
        )


def _build(output_root: Path, *, scene_count: int = 2, approved_scope: str = "job") -> tuple:
    profile = VoiceProfile(profile_id="ru_dom", display_name="Dom", provider="fake_paid", voice_id="v1", model_id="m1", language="ru")
    policy = VoicePolicy(
        enabled=True, required=True, output_mode="scene_audio", scene_level_generation=True,
        approval_required=True, target_sample_rate=48000, target_channels=1,
    )
    scenes = [{"scene_id": f"scene_{i + 1:03d}", "text": f"Сцена номер {i + 1}."} for i in range(scene_count)]
    full_text = " ".join(s["text"] for s in scenes)
    request = build_narration_request_from_scenes(
        project_id="p1", job_id="j1", channel_id="c1", localization_id="ru", language="ru",
        format_id="vertical_short", template_id="fullscreen_voiceover_v1",
        voice_profile=profile, policy=policy, scenes=scenes, full_text=full_text, output_root=output_root,
    )
    settings = dict(profile.settings)
    approval = VoiceApproval(
        approved=True, scope=approved_scope, provider=profile.provider, voice_id=profile.voice_id,
        voice_name=profile.display_name, model_id=profile.model_id, language=request.language,
        script_hash=compute_text_hash(full_text), settings_hash=compute_settings_hash(settings),
        approved_at="2026-07-24T00:00:00+00:00",
    )
    request.approval = approval
    return request, profile, policy


class NarrationWorkflowTests(unittest.TestCase):
    def test_generate_final_completes_and_assembles_narration(self) -> None:
        from src.audio.narration_workflow import generate_final

        with tempfile.TemporaryDirectory() as tmp:
            request, _, _ = _build(Path(tmp) / "project")
            manager = TTSProviderManager()
            fake = FakePaidProvider()
            manager.register(fake)
            manifest = generate_final(request, manager=manager)
            self.assertEqual(manifest["status"], "completed")
            self.assertGreater(manifest["narration"]["duration_sec"], 0)
            self.assertTrue(Path(manifest["audio_path"]).is_file())

    def test_generate_final_refuses_without_valid_approval(self) -> None:
        from src.audio.narration_workflow import generate_final

        with tempfile.TemporaryDirectory() as tmp:
            request, _, _ = _build(Path(tmp) / "project")
            request.approval = None
            manager = TTSProviderManager()
            fake = FakePaidProvider()
            manager.register(fake)
            with self.assertRaises(PermissionError):
                generate_final(request, manager=manager)
            self.assertEqual(fake.calls, 0)

    def test_approval_invalidated_by_text_change(self) -> None:
        from src.audio.narration_workflow import generate_final

        with tempfile.TemporaryDirectory() as tmp:
            request, _, _ = _build(Path(tmp) / "project")
            request.scenes[0].text = "Совсем другой текст."
            request.full_text = "Совсем другой текст. Сцена номер 2."
            manager = TTSProviderManager()
            fake = FakePaidProvider()
            manager.register(fake)
            with self.assertRaises(PermissionError):
                generate_final(request, manager=manager)

    def test_partial_failure_yields_partially_completed_no_narration(self) -> None:
        from src.audio.narration_workflow import generate_final

        with tempfile.TemporaryDirectory() as tmp:
            request, _, _ = _build(Path(tmp) / "project", scene_count=3)
            manager = TTSProviderManager()
            fake = FakePaidProvider(fail_scene_ids={"scene_002"})
            manager.register(fake)
            manifest = generate_final(request, manager=manager)
            self.assertEqual(manifest["status"], "partially_completed")
            self.assertEqual(manifest["narration"], {})
            self.assertEqual(manifest["audio_path"], "")

    def test_validate_output_completed_gate(self) -> None:
        from src.audio.narration_workflow import generate_final, validate_output

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            request, _, _ = _build(root, scene_count=2)
            manager = TTSProviderManager()
            fake = FakePaidProvider()
            manager.register(fake)
            generate_final(request, manager=manager)
            result = validate_output(root, "ru", expected_scene_count=2)
            self.assertTrue(result.valid, result.reason)

    def test_validate_output_fails_when_manifest_missing(self) -> None:
        from src.audio.narration_workflow import validate_output

        with tempfile.TemporaryDirectory() as tmp:
            result = validate_output(Path(tmp) / "project", "ru")
            self.assertFalse(result.valid)
            self.assertEqual(result.reason, "manifest_missing")

    def test_invalidate_scenes_only_marks_listed_scenes_stale(self) -> None:
        from src.audio.narration_workflow import generate_final, invalidate_scenes
        from src.audio.scene_voice_generator import generation_output_paths, load_scene_cache

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            request, _, _ = _build(root, scene_count=3)
            manager = TTSProviderManager()
            fake = FakePaidProvider()
            manager.register(fake)
            generate_final(request, manager=manager)

            invalidate_scenes(root, "ru", ["scene_002"])
            paths = generation_output_paths(root, "ru")
            cache = load_scene_cache(paths["scenes_dir"])
            self.assertNotIn("scene_002", cache)
            self.assertIn("scene_001", cache)
            self.assertIn("scene_003", cache)

    def test_disabled_policy_yields_skipped_status_without_calling_provider(self) -> None:
        from src.audio.narration_workflow import generate_final

        with tempfile.TemporaryDirectory() as tmp:
            request, _, _ = _build(Path(tmp) / "project")
            request.policy.enabled = False
            manager = TTSProviderManager()
            fake = FakePaidProvider()
            manager.register(fake)
            manifest = generate_final(request, manager=manager)
            self.assertEqual(manifest["status"], "skipped")
            self.assertEqual(fake.calls, 0)

    def test_prepare_final_no_paid_call_and_reports_readiness(self) -> None:
        from src.audio.narration_workflow import prepare_final

        with tempfile.TemporaryDirectory() as tmp:
            request, _, _ = _build(Path(tmp) / "project")
            manager = TTSProviderManager()
            fake = FakePaidProvider()
            manager.register(fake)
            summary = prepare_final(request, manager=manager)
            self.assertEqual(fake.calls, 0)
            self.assertTrue(summary["approval_valid"])
            self.assertEqual(summary["scene_count"], 2)

    def test_extended_voice_states_supersets_original_without_mutation(self) -> None:
        from src.audio.narration_workflow import EXTENDED_VOICE_STATES
        from src.audio.voice_workflow import VOICE_STATES

        self.assertEqual(VOICE_STATES, [
            "unconfigured", "draft_ready", "provider_selection_required", "audition_confirmation_required",
            "audition_generating", "awaiting_voice_approval", "voice_approved", "voice_rejected",
            "final_confirmation_required", "final_generating", "completed", "failed",
        ])
        for extra in ("partially_completed", "blocked", "manual_audio_ready", "skipped"):
            self.assertIn(extra, EXTENDED_VOICE_STATES)
        self.assertEqual(EXTENDED_VOICE_STATES[: len(VOICE_STATES)], VOICE_STATES)


if __name__ == "__main__":
    unittest.main()
