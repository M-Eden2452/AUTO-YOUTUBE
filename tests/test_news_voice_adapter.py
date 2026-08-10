from __future__ import annotations

import json
import tempfile
import unittest
import wave
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock, patch

from tests.network_guard import network_guard_scope


def _fixture_script() -> dict:
    scenes = []
    for i in range(1, 6):
        scenes.append(
            {
                "scene_id": f"scene_{i:03d}",
                "start_sec": (i - 1) * 6.0,
                "target_duration_sec": 6.0,
                "narration": f"Факт номер {i} про ворон и человеческие лица.",
                "claim_ids": [f"claim_{i}"],
                "visual_intent": "crow closeup",
                "on_screen_text": "",
                "emotion": "curious",
            }
        )
    return {
        "narration_text": " ".join(s["narration"] for s in scenes),
        "scenes": scenes,
    }


def _fixture_channel_config() -> dict:
    return {
        "voice": {
            "provider": "elevenlabs",
            "voice_profile": "ru_dom",
            "voice_id": "hDfThiytYnsDMuVgm6Qy",
            "model": "eleven_multilingual_v2",
            "output_format": "mp3_44100_128",
            "settings": {"stability": 0.6, "similarity_boost": 0.75, "style": 0.05, "use_speaker_boost": True, "speed": 1.02},
        },
        "voice_workflow": {
            "draft_provider": "audio_file",
            "paid_provider": "elevenlabs",
            "paid_tts_requires_approval": True,
            "audition_requires_approval": True,
            "full_generation_requires_approval": True,
            "audition_max_characters": 300,
            "never_auto_fallback_to_paid": True,
        },
    }


def _wav_bytes(seconds: float = 0.4) -> bytes:
    buffer = BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(48000)
        wav.writeframes(b"\x00\x00" * int(48000 * seconds))
    return buffer.getvalue()


class NewsVoiceAdapterTests(unittest.TestCase):
    def test_script_to_narration_request_maps_five_scenes(self) -> None:
        from src.news.voice_adapter import load_voice_profile_for_channel, resolve_voice_policy_for_channel, script_to_narration_request

        script = _fixture_script()
        channel_config = _fixture_channel_config()
        policy = resolve_voice_policy_for_channel(channel_config["voice"], channel_config["voice_workflow"])
        profile = load_voice_profile_for_channel("nature_science_news_ru", channel_config["voice"])
        request = script_to_narration_request(
            script=script, project_root="/tmp/unused", job_id="job_001", channel_id="nature_science_news_ru",
            language="ru", policy=policy, voice_profile=profile, approval=None,
        )
        self.assertEqual(len(request.scenes), 5)
        self.assertEqual(profile.profile_id, "ru_dom")
        self.assertTrue(policy.scene_level_generation)
        self.assertEqual(policy.output_mode, "scene_audio")

    def test_execute_false_matches_safe_stub_output(self) -> None:
        from src.news.voice_stage import build_or_generate_voice_manifest, build_safe_voice_manifest

        script = _fixture_script()
        channel_config = _fixture_channel_config()
        with tempfile.TemporaryDirectory() as tmp1, tempfile.TemporaryDirectory() as tmp2:
            baseline = build_safe_voice_manifest(
                project_root=tmp1, language="ru", script=script, channel_voice_config=channel_config["voice"]
            )
            adapted = build_or_generate_voice_manifest(
                project_root=tmp2, language="ru", script=script, channel_voice_config=channel_config["voice"],
                channel_workflow_config=channel_config["voice_workflow"], channel_id="nature_science_news_ru",
                job_id="job_001", execute=False,
            )
            self.assertEqual(baseline, adapted)

    def test_execute_true_without_approval_falls_back_to_stub_no_network(self) -> None:
        from src.news.voice_stage import build_or_generate_voice_manifest

        with network_guard_scope():
            script = _fixture_script()
            channel_config = _fixture_channel_config()
            with tempfile.TemporaryDirectory() as tmp:
                manifest = build_or_generate_voice_manifest(
                    project_root=tmp, language="ru", script=script, channel_voice_config=channel_config["voice"],
                    channel_workflow_config=channel_config["voice_workflow"], channel_id="nature_science_news_ru",
                    job_id="job_001", execute=True,
                )
                self.assertEqual(manifest["status"], "provider_selection_required")

    def test_execute_true_with_approval_generates_completed_manifest_via_fake_http(self) -> None:
        from src.audio.voice_workflow import create_voice_approval_record
        from src.news.voice_stage import build_or_generate_voice_manifest

        script = _fixture_script()
        channel_config = _fixture_channel_config()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_voice_approval_record(
                project_root=root, language="ru", scope="job", provider="elevenlabs",
                voice_id=channel_config["voice"]["voice_id"], voice_name="Dom", model_id=channel_config["voice"]["model"],
                script_text=script["narration_text"], settings=channel_config["voice"]["settings"],
                approved_at="2026-07-24T00:00:00+00:00",
            )

            fake_http = Mock()
            fake_http.post.return_value = Mock(status_code=200, content=_wav_bytes(0.4))
            with patch("src.audio.tts.elevenlabs_provider.requests", fake_http):
                manifest = build_or_generate_voice_manifest(
                    project_root=root, language="ru", script=script, channel_voice_config=channel_config["voice"],
                    channel_workflow_config=channel_config["voice_workflow"], channel_id="nature_science_news_ru",
                    job_id="job_001", execute=True,
                )

            self.assertEqual(manifest["status"], "completed")
            self.assertEqual(fake_http.post.call_count, 5)
            self.assertTrue(Path(manifest["audio_path"]).is_file())
            self.assertGreater(manifest["narration"]["duration_sec"], 0)

    def test_full_pipeline_with_generated_voice_reaches_final_render(self) -> None:
        from PIL import Image

        from src.audio.voice_workflow import create_voice_approval_record
        from src.news.pipeline import create_news_to_short_job, run_news_to_short_job
        from src.news.project_store import NewsProjectStore

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            images = []
            for index in range(12):
                image = root / f"crow_{index:03d}.jpg"
                Image.new("RGB", (1080, 1920), (10 + index, 40, 30)).save(image)
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
            job = create_news_to_short_job(
                projects_root=root, channel_id="nature_science_news_ru",
                topic="Почему вороны запоминают человеческие лица?",
                script_provider="legacy_template",
                assets=images,
                language="ru",
                now="2026-07-24T00:00:00+03:00",
            )
            with patch("src.news.asset_manager.create_default_asset_providers", return_value=[]):
                run_news_to_short_job(projects_root=root, job_id=job.job_id, until_stage="voice")

            project = root / job.job_id
            narration_text = (project / "localizations" / "ru" / "script" / "narration.txt").read_text(encoding="utf-8").strip()
            channel_config = _fixture_channel_config()
            create_voice_approval_record(
                project_root=project, language="ru", scope="job", provider="elevenlabs",
                voice_id=channel_config["voice"]["voice_id"], voice_name="Dom", model_id=channel_config["voice"]["model"],
                script_text=narration_text, settings=channel_config["voice"]["settings"],
                approved_at="2026-07-24T00:00:00+00:00",
            )

            fake_http = Mock()
            fake_http.post.return_value = Mock(status_code=200, content=_wav_bytes(0.3))
            with patch("src.audio.tts.elevenlabs_provider.requests", fake_http):
                run_news_to_short_job(projects_root=root, job_id=job.job_id, stage="voice", execute_voice=True)

            voice_manifest = json.loads((project / "localizations" / "ru" / "voice" / "voice_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(voice_manifest["status"], "completed")
            self.assertTrue(Path(voice_manifest["audio_path"]).is_file())

            run_news_to_short_job(projects_root=root, job_id=job.job_id, stage="subtitles")
            store = NewsProjectStore(root)
            store.write_json(project / "quality" / "quality_report.json", {"status": "passed", "errors": [], "warnings": [], "checks": []})
            result = run_news_to_short_job(projects_root=root, job_id=job.job_id, stage="final_render")
            final_manifest = json.loads((project / "render" / "final_render_manifest.json").read_text(encoding="utf-8"))

            self.assertEqual(final_manifest["status"], "completed")
            self.assertEqual(final_manifest["audio_path"], voice_manifest["audio_path"])
            self.assertTrue(Path(final_manifest["output_path"]).is_file())
            self.assertEqual(result.status, "completed")


if __name__ == "__main__":
    unittest.main()
