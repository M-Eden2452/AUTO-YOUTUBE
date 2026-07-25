from __future__ import annotations

import tempfile
import unittest
import wave
from pathlib import Path

import requests

from src.audio.tts.base_provider import TTSProvider
from src.audio.tts.models import SOURCE_GENERATED, TTSRequest, TTSResult, VoiceProfile
from src.audio.tts.provider_manager import TTSProviderManager
from src.audio.narration_models import build_narration_request_from_scenes
from src.audio.voice_policy import VoicePolicy


def _write_silence_wav(path: Path, seconds: float = 0.2) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(48000)
        wav.writeframes(b"\x00\x00" * int(48000 * seconds))


class FakeProvider(TTSProvider):
    name = "fake"
    paid = True

    def __init__(self, *, fail_scene_ids: dict[str, Exception] | None = None) -> None:
        self.calls = 0
        self.call_log: list[str] = []
        self.fail_scene_ids = fail_scene_ids or {}

    def synthesize(self, request: TTSRequest) -> TTSResult:
        self.calls += 1
        self.call_log.append(request.scene_id or "")
        if request.scene_id in self.fail_scene_ids:
            raise self.fail_scene_ids[request.scene_id]
        _write_silence_wav(Path(request.output_path))
        return TTSResult(
            provider=self.name, language=request.language, scene_id=request.scene_id,
            audio_path=request.output_path, duration_sec=0.2, sample_rate=48000, channels=1,
            source_type=SOURCE_GENERATED,
        )


def _build_request(output_root: Path, scene_count: int = 1, provider: str = "fake"):
    profile = VoiceProfile(profile_id="ru_dom", display_name="Dom", provider=provider, voice_id="v1", model_id="m1", language="ru")
    policy = VoicePolicy(enabled=True, output_mode="scene_audio", scene_level_generation=True, approval_required=True)
    scenes = [{"scene_id": f"scene_{i + 1:03d}", "text": f"Текст сцены {i + 1}."} for i in range(scene_count)]
    return build_narration_request_from_scenes(
        project_id="p1", job_id="j1", channel_id="c1", localization_id="ru", language="ru",
        format_id="vertical_short", template_id="fullscreen_voiceover_v1",
        voice_profile=profile, policy=policy, scenes=scenes, output_root=output_root,
    )


class SceneVoiceGeneratorTests(unittest.TestCase):
    def test_single_scene_generation(self) -> None:
        from src.audio.scene_voice_generator import generate_scenes

        with tempfile.TemporaryDirectory() as tmp:
            request = _build_request(Path(tmp), scene_count=1)
            manager = TTSProviderManager()
            fake = FakeProvider()
            manager.register(fake)
            results = generate_scenes(request, manager=manager, approved=True)
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["generation_status"], "completed")
            self.assertEqual(fake.calls, 1)

    def test_five_scene_generation(self) -> None:
        from src.audio.scene_voice_generator import generate_scenes

        with tempfile.TemporaryDirectory() as tmp:
            request = _build_request(Path(tmp), scene_count=5)
            manager = TTSProviderManager()
            fake = FakeProvider()
            manager.register(fake)
            results = generate_scenes(request, manager=manager, approved=True)
            self.assertEqual(len(results), 5)
            self.assertTrue(all(r["generation_status"] == "completed" for r in results))
            self.assertEqual(fake.calls, 5)

    def test_no_paid_call_without_approval(self) -> None:
        from src.audio.scene_voice_generator import generate_scenes

        with tempfile.TemporaryDirectory() as tmp:
            request = _build_request(Path(tmp), scene_count=3)
            manager = TTSProviderManager()
            fake = FakeProvider()
            manager.register(fake)
            with self.assertRaises(PermissionError):
                generate_scenes(request, manager=manager, approved=False)
            self.assertEqual(fake.calls, 0)

    def test_second_run_is_fully_cache_hit_no_repeated_paid_call(self) -> None:
        from src.audio.scene_voice_generator import generate_scenes

        with tempfile.TemporaryDirectory() as tmp:
            request = _build_request(Path(tmp), scene_count=3)
            manager = TTSProviderManager()
            fake = FakeProvider()
            manager.register(fake)
            generate_scenes(request, manager=manager, approved=True)
            self.assertEqual(fake.calls, 3)
            results2 = generate_scenes(request, manager=manager, approved=True)
            self.assertEqual(fake.calls, 3, "cached scenes must not be re-synthesized")
            self.assertTrue(all(r["cache_hit"] for r in results2))

    def test_partial_cache_only_regenerates_changed_scene(self) -> None:
        from src.audio.scene_voice_generator import generate_scenes

        with tempfile.TemporaryDirectory() as tmp:
            request = _build_request(Path(tmp), scene_count=3)
            manager = TTSProviderManager()
            fake = FakeProvider()
            manager.register(fake)
            generate_scenes(request, manager=manager, approved=True)
            self.assertEqual(fake.calls, 3)

            request.scenes[1].text = "Изменённый текст сцены."
            from src.audio.narration_models import compute_generation_key

            request.scenes[1].generation_key = compute_generation_key(
                text=request.scenes[1].text, provider="fake", voice_id="v1", model_id="m1", language="ru",
                settings={}, output_format="mp3_44100_128",
            )
            generate_scenes(request, manager=manager, approved=True)
            self.assertEqual(fake.calls, 4, "only the changed scene should trigger a new synth call")

    def test_corrupted_cache_file_triggers_regeneration_not_crash(self) -> None:
        from src.audio.scene_voice_generator import generate_scenes, generation_output_paths

        with tempfile.TemporaryDirectory() as tmp:
            request = _build_request(Path(tmp), scene_count=1)
            manager = TTSProviderManager()
            fake = FakeProvider()
            manager.register(fake)
            generate_scenes(request, manager=manager, approved=True)
            self.assertEqual(fake.calls, 1)

            paths = generation_output_paths(Path(tmp), "ru")
            audio_path = Path(next(iter(paths["scenes_dir"].glob("*.mp3"))))
            audio_path.write_bytes(b"not-real-audio-corrupted")

            results = generate_scenes(request, manager=manager, approved=True)
            self.assertEqual(fake.calls, 2, "corrupted audio must trigger regeneration")
            self.assertEqual(results[0]["generation_status"], "completed")

    def test_partial_failure_preserves_successful_scenes(self) -> None:
        from src.audio.scene_voice_generator import generate_scenes

        with tempfile.TemporaryDirectory() as tmp:
            request = _build_request(Path(tmp), scene_count=3)
            manager = TTSProviderManager()
            fake = FakeProvider(fail_scene_ids={"scene_002": ValueError("boom")})
            manager.register(fake)
            results = generate_scenes(request, manager=manager, approved=True)
            statuses = {r["scene_id"]: r["generation_status"] for r in results}
            self.assertEqual(statuses["scene_001"], "completed")
            self.assertEqual(statuses["scene_002"], "failed")
            self.assertEqual(statuses["scene_003"], "completed")

            # re-run: only the failed scene should be retried, successes stay cache hits
            fake.fail_scene_ids = {}
            fake.calls = 0
            results2 = generate_scenes(request, manager=manager, approved=True)
            self.assertEqual(fake.calls, 1)
            self.assertTrue(all(r["generation_status"] == "completed" for r in results2))

    def test_one_retry_on_transient_network_error_then_succeeds(self) -> None:
        from src.audio.scene_voice_generator import generate_scenes

        class FlakyProvider(FakeProvider):
            def __init__(self) -> None:
                super().__init__()
                self._raised = False

            def synthesize(self, request: TTSRequest) -> TTSResult:
                if not self._raised:
                    self._raised = True
                    self.calls += 1
                    raise requests.exceptions.ConnectionError("transient")
                return super().synthesize(request)

        with tempfile.TemporaryDirectory() as tmp:
            request = _build_request(Path(tmp), scene_count=1)
            manager = TTSProviderManager()
            flaky = FlakyProvider()
            manager.register(flaky)
            results = generate_scenes(request, manager=manager, approved=True, max_retries_on_transient=1)
            self.assertEqual(results[0]["generation_status"], "completed")
            self.assertEqual(flaky.calls, 2)

    def test_no_retry_on_ambiguous_http_style_error(self) -> None:
        from src.audio.scene_voice_generator import generate_scenes

        with tempfile.TemporaryDirectory() as tmp:
            request = _build_request(Path(tmp), scene_count=1)
            manager = TTSProviderManager()
            fake = FakeProvider(fail_scene_ids={"scene_001": PermissionError("HTTP 500")})
            manager.register(fake)
            results = generate_scenes(request, manager=manager, approved=True)
            self.assertEqual(results[0]["generation_status"], "failed")
            self.assertEqual(fake.calls, 1, "ambiguous HTTP-style failures must not be retried")


if __name__ == "__main__":
    unittest.main()
