"""Стадия ``subtitles`` News-to-Short и CLI-команды поверх единого движка (Q3).

Тесты идут через настоящий пайплайн, но озвучка подменяется готовым schema-v2
манифестом: ни TTS, ни сеть, ни FFmpeg, ни платные вызовы не участвуют
(``build_or_generate_voice_manifest`` пропатчен, ``tests.network_guard`` установлен
на весь пакет).
"""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.content_creation.cli import main

NARRATIONS = [
    "Учёные впервые записали звук, который издаёт ледник при таянии, и он оказался неожиданно низким.",
    "Оказалось, что этот гул слышен на 12 километров вокруг, даже сквозь толщу воды.",
    "Это меняет представление о том, как быстро уходит лёд.",
]


def _run_cli(argv: list[str]) -> tuple[int, str]:
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        code = main(argv)
    return code, buffer.getvalue()


def _voice_manifest(scene_ids: list[str], durations: list[float], pause: float = 0.35) -> dict:
    gaps = max(0, len(durations) - 1)
    return {
        "schema_version": 2,
        "status": "completed",
        "voice_stage_status": "completed",
        "format_id": "vertical_short",
        "audio_path": "narration.wav",
        "scenes": [
            {
                "scene_id": scene_id,
                "scene_index": index,
                "duration_seconds": duration,
                "generation_status": "completed",
            }
            for index, (scene_id, duration) in enumerate(zip(scene_ids, durations, strict=True))
        ],
        "narration": {
            "output_path": "narration.wav",
            "duration_sec": sum(durations) + pause * gaps,
            "pause_total_sec": pause * gaps,
        },
    }


class SubtitleStageTests(unittest.TestCase):
    def _project_with_voice(self, root: Path):
        """Проект, доведённый до завершённой стадии voice, с реальными таймингами."""
        from src.news.pipeline import create_news_to_short_job, run_news_to_short_job

        job = create_news_to_short_job(
            projects_root=root,
            channel_id="nature_science_news_ru",
            text=" ".join(NARRATIONS),
            language="ru",
            now="2026-07-26T10:00:00+03:00",
        )
        run_news_to_short_job(projects_root=root, job_id=job.job_id, until_stage="script", dry_run=True)
        script_path = root / job.job_id / "localizations" / "ru" / "script" / "script.json"
        script = json.loads(script_path.read_text(encoding="utf-8"))
        # Свой текст сцен, чтобы тест не зависел от того, как провайдер сценария
        # порезал новость; scene_id и структура остаются те, что создал пайплайн.
        for index, scene in enumerate(script["scenes"]):
            scene["narration"] = NARRATIONS[index % len(NARRATIONS)]
        script_path.write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")

        scene_ids = [scene["scene_id"] for scene in script["scenes"]]
        # Длительность пропорциональна длине реплики - как у настоящей озвучки, иначе
        # предупреждение «читать слишком быстро» появлялось бы из-за самого теста.
        durations = [round(len(scene["narration"]) / 14.9, 2) for scene in script["scenes"]]
        manifest = _voice_manifest(scene_ids, durations)
        with patch("src.news.pipeline.build_or_generate_voice_manifest", return_value=manifest):
            run_news_to_short_job(projects_root=root, job_id=job.job_id, stage="voice")
        # Настоящая стадия voice пишет манифест сама (внутри
        # build_or_generate_voice_manifest); патч этого не делает, поэтому файл
        # кладётся здесь - иначе стадия субтитров не увидела бы озвучку.
        voice_path = root / job.job_id / "localizations" / "ru" / "voice" / "voice_manifest.json"
        voice_path.parent.mkdir(parents=True, exist_ok=True)
        voice_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        return job, root / job.job_id, manifest

    def _subtitles_manifest(self, project_root: Path) -> dict:
        path = project_root / "localizations" / "ru" / "subtitles" / "subtitles_manifest.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def test_stage_writes_a_localization_aware_artifact_with_real_timing(self) -> None:
        from src.news.pipeline import run_news_to_short_job

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            job, project_root, voice = self._project_with_voice(root)
            run_news_to_short_job(projects_root=root, job_id=job.job_id, stage="subtitles")

            manifest = self._subtitles_manifest(project_root)
            self.assertEqual(manifest["schema_version"], 2)
            self.assertEqual(manifest["localization_id"], "ru")
            self.assertEqual(manifest["subtitle_language"], "ru")
            self.assertEqual(manifest["timing_source"], "scene_timeline")
            self.assertEqual(manifest["scene_timeline_source"], "voice_manifest")
            self.assertAlmostEqual(
                manifest["narration_duration_sec"], voice["narration"]["duration_sec"], places=2
            )
            self.assertAlmostEqual(
                manifest["segments"][-1]["end"], voice["narration"]["duration_sec"], delta=0.05
            )
            # ключи, которые читают final_renderer / quality_check / exporter
            self.assertTrue(Path(manifest["srt_path"]).is_file())
            self.assertTrue(Path(manifest["ass_path"]).is_file())
            # Предупреждения (скорость чтения, длинный cue) допустимы; ошибок быть не должно.
            self.assertEqual(manifest["validation"]["error_count"], 0, manifest["validation"])

    def test_subtitles_carry_the_whole_narration_not_the_first_five_words(self) -> None:
        """Дефект W2 аудита V1 закрыт: в кадре весь текст сцены."""
        from src.news.pipeline import run_news_to_short_job

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            job, project_root, _ = self._project_with_voice(root)
            run_news_to_short_job(projects_root=root, job_id=job.job_id, stage="subtitles")
            script = json.loads(
                (project_root / "localizations" / "ru" / "script" / "script.json").read_text(encoding="utf-8")
            )
            manifest = self._subtitles_manifest(project_root)
            by_scene: dict[str, list[str]] = {}
            for cue in manifest["cues"]:
                by_scene.setdefault(cue["scene_id"], []).extend(cue["text"].split())
            for scene in script["scenes"]:
                self.assertEqual(by_scene[scene["scene_id"]], scene["narration"].split())

    def test_rerunning_the_stage_reuses_a_compatible_artifact(self) -> None:
        from src.news.pipeline import run_news_to_short_job

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            job, project_root, _ = self._project_with_voice(root)
            run_news_to_short_job(projects_root=root, job_id=job.job_id, stage="subtitles")
            first = self._subtitles_manifest(project_root)
            run_news_to_short_job(projects_root=root, job_id=job.job_id, stage="subtitles")
            second = self._subtitles_manifest(project_root)
        self.assertEqual(first["generated_at"], second["generated_at"])

    def test_force_stage_regenerates_and_edited_script_changes_the_result(self) -> None:
        from src.news.pipeline import run_news_to_short_job

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            job, project_root, _ = self._project_with_voice(root)
            run_news_to_short_job(projects_root=root, job_id=job.job_id, stage="subtitles")
            before = self._subtitles_manifest(project_root)

            script_path = project_root / "localizations" / "ru" / "script" / "script.json"
            script = json.loads(script_path.read_text(encoding="utf-8"))
            script["scenes"][0]["narration"] = "Совсем другая первая мысль про лёд и воду."
            script_path.write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")

            run_news_to_short_job(projects_root=root, job_id=job.job_id, stage="subtitles")
            after = self._subtitles_manifest(project_root)
        self.assertNotEqual(before["script_fingerprint"], after["script_fingerprint"])
        self.assertIn("Совсем другая", " ".join(cue["text"] for cue in after["cues"]))

    def test_a_protected_artifact_survives_the_stage(self) -> None:
        from src.news.pipeline import run_news_to_short_job

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            job, project_root, _ = self._project_with_voice(root)
            run_news_to_short_job(projects_root=root, job_id=job.job_id, stage="subtitles")
            manifest_path = project_root / "localizations" / "ru" / "subtitles" / "subtitles_manifest.json"
            protected = json.loads(manifest_path.read_text(encoding="utf-8"))
            protected["protected"] = True
            protected["script_fingerprint"] = "user-edited"
            manifest_path.write_text(json.dumps(protected, ensure_ascii=False, indent=2), encoding="utf-8")
            srt_path = Path(protected["srt_path"])
            srt_path.write_text("1\n00:00:00,000 --> 00:00:02,000\nМой собственный субтитр\n", encoding="utf-8")

            run_news_to_short_job(
                projects_root=root, job_id=job.job_id, stage="subtitles", force_stage=True
            )
            self.assertIn("Мой собственный субтитр", srt_path.read_text(encoding="utf-8"))
            self.assertEqual(
                json.loads(manifest_path.read_text(encoding="utf-8"))["script_fingerprint"], "user-edited"
            )

    def test_quality_check_and_renderer_still_read_the_manifest(self) -> None:
        from src.news.final_renderer import _load_subtitles_manifest
        from src.news.pipeline import run_news_to_short_job
        from src.news.quality_check import run_quality_check

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            job, project_root, _ = self._project_with_voice(root)
            run_news_to_short_job(projects_root=root, job_id=job.job_id, stage="subtitles")
            manifest = self._subtitles_manifest(project_root)
            report = run_quality_check(
                script={"scenes": [{"narration": "x"}], "estimated_duration_sec": 50},
                research={},
                assets_manifest={},
                voice_manifest={"status": "completed"},
                subtitles_manifest=manifest,
            )
            self.assertTrue(
                any(check["check"] == "subtitles" for check in report["checks"]),
                report,
            )
            loaded = _load_subtitles_manifest(project_root, "ru")
            self.assertEqual(loaded["ass_path"], manifest["ass_path"])
            self.assertTrue(Path(loaded["ass_path"]).is_file())

    def test_cli_explain_and_validate_are_read_only(self) -> None:
        from src.news.pipeline import run_news_to_short_job

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            job, project_root, voice = self._project_with_voice(root)

            # explain работает ещё до того, как артефакт создан
            code, output = _run_cli(
                ["subtitles", "explain", "--project-id", job.job_id, "--projects-root", str(root), "--json"]
            )
            self.assertEqual(code, 0, output)
            data = json.loads(output)
            self.assertEqual(data["timing_source"], "scene_timeline")
            self.assertEqual(data["localization_id"], "ru")
            self.assertEqual(data["subtitle_language"], "ru")
            self.assertFalse(data["resume"]["reuse"])
            self.assertEqual(data["resume"]["reason"], "no_existing_artifact")
            self.assertEqual(len(data["scenes"]), len(voice["scenes"]))
            self.assertFalse(Path(data["paths"]["srt"]).exists(), "explain не должен ничего писать")

            run_news_to_short_job(projects_root=root, job_id=job.job_id, stage="subtitles")
            before = sorted(str(path) for path in project_root.rglob("*"))

            code, output = _run_cli(
                ["subtitles", "explain", "--project-id", job.job_id, "--projects-root", str(root), "--json"]
            )
            self.assertEqual(code, 0, output)
            self.assertTrue(json.loads(output)["resume"]["reuse"])

            code, output = _run_cli(
                ["subtitles", "validate", "--project-id", job.job_id, "--projects-root", str(root), "--json"]
            )
            self.assertEqual(code, 0, output)
            validated = json.loads(output)
            self.assertEqual(validated["schema_version"], 2)
            self.assertGreater(validated["cue_count"], 0)
            self.assertEqual(validated["validation"]["error_count"], 0, validated["validation"])

            self.assertEqual(before, sorted(str(path) for path in project_root.rglob("*")))

    def test_cli_explain_prints_scene_to_cue_mapping_in_text_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            job, _project_root, _ = self._project_with_voice(root)
            code, output = _run_cli(
                ["subtitles", "explain", "--project-id", job.job_id, "--projects-root", str(root), "--cues"]
            )
        self.assertEqual(code, 0, output)
        self.assertIn("источник тайминга=scene_timeline", output)
        self.assertIn("scene_001", output)
        self.assertIn("resume:", output)

    def test_cli_validate_reads_a_pre_q3_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            job, project_root, _ = self._project_with_voice(root)
            subtitles_dir = project_root / "localizations" / "ru" / "subtitles"
            subtitles_dir.mkdir(parents=True, exist_ok=True)
            (subtitles_dir / "subtitles_manifest.json").write_text(
                json.dumps(
                    {
                        "status": "completed",
                        "language": "ru",
                        "srt_path": str(subtitles_dir / "subtitles.srt"),
                        "ass_path": str(subtitles_dir / "subtitles.ass"),
                        "segments": [
                            {"start": 0.0, "end": 2.5, "text": "Учёные впервые записали звук,"},
                            {"start": 2.5, "end": 5.0, "text": "который издаёт ледник при таянии."},
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            code, output = _run_cli(
                ["subtitles", "validate", "--project-id", job.job_id, "--projects-root", str(root), "--json"]
            )
        self.assertEqual(code, 0, output)
        data = json.loads(output)
        self.assertEqual(data["schema_version"], 0)
        self.assertEqual(data["cue_count"], 2)
        self.assertIn("legacy_artifact_without_metadata", [i["code"] for i in data["validation"]["issues"]])


if __name__ == "__main__":
    unittest.main()
