"""Stage B3: readable project names, a real title, and resuming an unfinished project.

Three problems this covers, all visible in `projects/` today:

- ``wizard_установил_questionary_единственная_подходящая_библиотека__20260724T210156``
  - a folder named after the first 80 characters of a pasted script;
- ``project-61958823`` - a Russian title stripped to nothing by an ASCII-only slugifier;
- half-finished projects that the wizard offered no way to pick back up, and whose
  finished narration was destroyed by re-running the voice stage.

No network, no TTS, no paid API: every project here is built under tempfile.
"""

from __future__ import annotations

import json
import unittest
import wave
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from src.content_creation.models import ContentCreationRequest, ExecutionFlags, VoiceRequestConfig
from src.content_creation.wizard import START_ACTIONS, run_wizard
from src.news.models import NewsJob
from src.news.pipeline import create_news_to_short_job
from src.project_foundation.naming import (
    build_project_id,
    slugify_title,
    suggest_title,
    transliterate,
)
from src.projects import ProjectRepository

from tests.test_content_creation_wizard import FakeCreateFn, ScriptedAdapter


class TransliterationAndSlugTests(unittest.TestCase):
    def test_russian_title_becomes_readable_latin(self) -> None:
        self.assertEqual(
            slugify_title("Почему вороны запоминают человеческие лица"),
            "pochemu-vorony-zapominayut-chelovecheskie-lica",
        )

    def test_every_cyrillic_letter_has_a_mapping(self) -> None:
        alphabet = "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"
        result = transliterate(alphabet)
        self.assertTrue(result.isascii(), f"unmapped characters remain: {result!r}")

    def test_uppercase_cyrillic_is_handled(self) -> None:
        self.assertEqual(slugify_title("ЖЁЛТЫЙ ЩЕНОК"), "zheltyy-schenok")

    def test_windows_forbidden_characters_never_survive(self) -> None:
        slug = slugify_title('Как? Зачем: "это" <всё> | и \\ ещё / *')
        self.assertTrue(all(char not in slug for char in '<>:"/\\|?*'))
        self.assertFalse(slug.endswith(("." , " ")))

    def test_reserved_windows_name_is_made_usable(self) -> None:
        self.assertNotIn(slugify_title("con"), {"con", "CON"})
        self.assertNotIn(slugify_title("LPT1"), {"lpt1", "LPT1"})

    def test_length_is_capped_on_a_word_boundary(self) -> None:
        long_title = "почему киты используют сложные звуки чтобы общаться на огромных расстояниях в океане"
        slug = slugify_title(long_title)
        untruncated = slugify_title(long_title, max_length=1000)

        self.assertLessEqual(len(slug), 48)
        self.assertFalse(slug.endswith("-"))
        # Every surviving word must be a whole word of the full slug, in order -
        # "pochemu-kity-ispolzuyut-slozh" would be worse than one word fewer.
        words = slug.split("-")
        self.assertEqual(words, untruncated.split("-")[: len(words)])
        self.assertLess(len(words), len(untruncated.split("-")))

    def test_titleless_input_falls_back_instead_of_producing_an_empty_name(self) -> None:
        self.assertEqual(slugify_title("!!! ??? ***"), "project")
        self.assertEqual(slugify_title(""), "project")


class ProjectIdTests(unittest.TestCase):
    def test_id_starts_with_the_date_then_the_title(self) -> None:
        project_id = build_project_id("Почему вороны запоминают лица", created_at="2026-07-25T21:03:04+03:00")
        self.assertEqual(project_id, "2026-07-25_pochemu-vorony-zapominayut-lica")

    def test_compact_stamp_is_also_understood(self) -> None:
        # The news pipeline's own historical stamp format.
        self.assertTrue(build_project_id("Тест", created_at="20260724T214350").startswith("2026-07-24_"))

    def test_id_is_deterministic_without_a_collision_check(self) -> None:
        first = build_project_id("Одно и то же", created_at="2026-07-25")
        second = build_project_id("Одно и то же", created_at="2026-07-25")
        self.assertEqual(first, second)

    def test_collisions_get_a_readable_counter_not_a_random_suffix(self) -> None:
        taken = {"2026-07-25_tema", "2026-07-25_tema-2"}
        self.assertEqual(build_project_id("Тема", created_at="2026-07-25", is_taken=taken), "2026-07-25_tema-3")

    def test_a_predicate_works_as_well_as_a_container(self) -> None:
        self.assertEqual(
            build_project_id("Тема", created_at="2026-07-25", is_taken=lambda name: name == "2026-07-25_tema"),
            "2026-07-25_tema-2",
        )

    def test_id_stays_short_enough_for_windows_paths(self) -> None:
        project_id = build_project_id("а" * 300, created_at="2026-07-25")
        self.assertLessEqual(len(project_id), 64)


class SuggestTitleTests(unittest.TestCase):
    def test_first_sentence_of_a_pasted_script_is_suggested(self) -> None:
        script = "Вороны запоминают лица. Потом они рассказывают об этом другим воронам. И так далее."
        self.assertEqual(suggest_title(script), "Вороны запоминают лица.")

    def test_first_non_empty_candidate_wins(self) -> None:
        self.assertEqual(suggest_title("", "   ", "Тема ролика"), "Тема ролика")

    def test_long_single_sentence_is_trimmed(self) -> None:
        suggestion = suggest_title("слово " * 40)
        self.assertLessEqual(len(suggestion), 60)

    def test_nothing_usable_gives_a_placeholder_not_an_empty_string(self) -> None:
        self.assertEqual(suggest_title("", None), "Без названия")


class NewsJobNamingTests(unittest.TestCase):
    def test_pasted_script_no_longer_names_the_folder(self) -> None:
        script = (
            "Wizard установил questionary, единственная подходящая библиотека для "
            "интерактивного выбора в терминале, и это заняло довольно много времени."
        )
        job = NewsJob.create(
            channel_id="c", input_mode="text", input_text=script, now="2026-07-24T21:01:56+00:00"
        )
        self.assertTrue(job.job_id.startswith("2026-07-24_"))
        self.assertLessEqual(len(job.job_id), 64)
        self.assertNotIn("установил", job.job_id)

    def test_explicit_title_wins_over_topic(self) -> None:
        job = NewsJob.create(
            channel_id="c",
            input_mode="topic",
            title="Вороны и лица",
            topic="какая-то длинная тема которая не должна попасть в имя папки",
            now="2026-07-25T10:00:00+00:00",
        )
        self.assertEqual(job.job_id, "2026-07-25_vorony-i-lica")
        self.assertEqual(job.title, "Вороны и лица")

    def test_title_falls_back_to_topic_when_not_given(self) -> None:
        job = NewsJob.create(channel_id="c", input_mode="topic", topic="Почему киты поют")
        self.assertEqual(job.title, "Почему киты поют")

    def test_a_job_json_written_before_title_existed_still_loads(self) -> None:
        job = NewsJob.create(channel_id="c", input_mode="topic", topic="Тема")
        data = job.to_dict()
        del data["title"]
        restored = NewsJob.from_dict(data)
        self.assertEqual(restored.title, "")
        self.assertEqual(restored.job_id, job.job_id)

    def test_two_jobs_created_the_same_day_do_not_share_a_folder(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = create_news_to_short_job(projects_root=root, title="Одна тема", now="2026-07-25T10:00:00+00:00")
            second = create_news_to_short_job(projects_root=root, title="Одна тема", now="2026-07-25T10:05:00+00:00")
            self.assertNotEqual(first.job_id, second.job_id)
            self.assertTrue(second.job_id.endswith("-2"))
            self.assertTrue((root / first.job_id).is_dir())
            self.assertTrue((root / second.job_id).is_dir())


class ProjectViewResumeFieldsTests(unittest.TestCase):
    def test_last_completed_stage_and_finished_flag(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            job = create_news_to_short_job(projects_root=root, title="Черновик", now="2026-07-25T10:00:00+00:00")
            job_path = root / job.job_id / "job.json"
            data = json.loads(job_path.read_text(encoding="utf-8"))
            for stage in ("input", "article_ingestion", "research", "script"):
                data["stages"][stage]["status"] = "completed"
            job_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

            view = ProjectRepository(root).get(job.job_id)
            self.assertEqual(view.last_completed_stage, "script")
            self.assertFalse(view.is_finished)
            self.assertEqual(view.title, "Черновик")

    def test_nothing_completed_reports_empty_rather_than_guessing(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            job = create_news_to_short_job(projects_root=root, title="Пустой")
            self.assertEqual(ProjectRepository(root).get(job.job_id).last_completed_stage, "")

    def test_old_job_without_title_falls_back_to_topic(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            job = create_news_to_short_job(projects_root=root, topic="Старая тема")
            job_path = root / job.job_id / "job.json"
            data = json.loads(job_path.read_text(encoding="utf-8"))
            del data["title"]
            job_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

            self.assertEqual(ProjectRepository(root).get(job.job_id).title, "Старая тема")


class WizardTitleTests(unittest.TestCase):
    def test_suggested_title_is_accepted_with_one_keypress(self) -> None:
        adapter = ScriptedAdapter(
            [
                "new",
                "vertical_short",
                "fullscreen_voiceover_v1",
                "nature_science_news_ru",
                "ru",
                "topic",
                "Почему вороны запоминают лица",
                "60",
                "disabled",
                "disabled",
                "disabled",
                True,
                "run",
            ]
        )
        create_fn = FakeCreateFn([])
        run_wizard(adapter=adapter, create_fn=create_fn)
        self.assertEqual(create_fn.requests[0].title, "Почему вороны запоминают лица")

    def test_a_typed_title_replaces_the_suggestion(self) -> None:
        adapter = ScriptedAdapter(
            [
                "new",
                "vertical_short",
                "fullscreen_voiceover_v1",
                "nature_science_news_ru",
                "ru",
                "topic",
                "Очень длинная и неудобная тема для имени папки",
                "Вороны и лица",  # the title question
                "60",
                "disabled",
                "disabled",
                "disabled",
                True,
                "run",
            ],
            auto_title=False,
        )
        create_fn = FakeCreateFn([])
        run_wizard(adapter=adapter, create_fn=create_fn)
        self.assertEqual(create_fn.requests[0].title, "Вороны и лица")


class WizardResumeTests(unittest.TestCase):
    def _unfinished_project(self, root: Path, *, title: str, completed: tuple[str, ...]) -> str:
        job = create_news_to_short_job(projects_root=root, title=title, now="2026-07-25T10:00:00+00:00")
        job_path = root / job.job_id / "job.json"
        data = json.loads(job_path.read_text(encoding="utf-8"))
        for stage in completed:
            data["stages"][stage]["status"] = "completed"
        job_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return job.job_id

    def test_start_menu_offers_continuing(self) -> None:
        self.assertIn("resume", [value for value, _ in START_ACTIONS])

    def test_resume_reuses_the_same_project_id_and_skips_the_questionnaire(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            project_id = self._unfinished_project(root, title="Недоделанный ролик", completed=("input", "script"))

            adapter = ScriptedAdapter(["resume", project_id])
            create_fn = FakeCreateFn([])
            run_wizard(adapter=adapter, create_fn=create_fn, projects_root=str(root))

            request = create_fn.requests[0]
            self.assertEqual(request.project_id, project_id)
            self.assertTrue(request.execution.resume)
            self.assertEqual(request.template_id, "fullscreen_voiceover_v1")
            self.assertEqual(request.title, "Недоделанный ролик")
            # No format/channel/topic questions were asked again.
            messages = [message for message, _ in adapter.select_calls]
            self.assertFalse(any("Формат" in message for message in messages))
            self.assertFalse(any("Источник сценария" in message for message in messages))

    def test_the_list_shows_where_each_project_stopped(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            project_id = self._unfinished_project(
                root, title="Ролик про ворон", completed=("input", "article_ingestion", "research", "script")
            )

            adapter = ScriptedAdapter(["resume", project_id])
            run_wizard(adapter=adapter, create_fn=FakeCreateFn([]), projects_root=str(root))

            resume_choices = next(
                choices for message, choices in adapter.select_calls if "продолжить" in message.lower()
            )
            label = dict(resume_choices)[project_id]
            self.assertIn("Ролик про ворон", label)
            self.assertIn("сценарий", label)

    def test_finished_projects_are_not_offered(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            unfinished = self._unfinished_project(root, title="Незавершённый", completed=("input",))
            finished = self._unfinished_project(root, title="Готовый", completed=("input",))
            output = root / finished / "localizations" / "ru" / "output" / "master.mp4"
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(b"video")
            (root / finished / "render").mkdir(parents=True, exist_ok=True)
            (root / finished / "render" / "final_render_manifest.json").write_text(
                json.dumps({"status": "completed", "output_path": str(output)}), encoding="utf-8"
            )

            adapter = ScriptedAdapter(["resume", unfinished])
            run_wizard(adapter=adapter, create_fn=FakeCreateFn([]), projects_root=str(root))

            resume_choices = next(
                choices for message, choices in adapter.select_calls if "продолжить" in message.lower()
            )
            offered = [value for value, _ in resume_choices]
            self.assertIn(unfinished, offered)
            self.assertNotIn(finished, offered)

    def test_nothing_to_resume_falls_back_to_creating_a_new_project(self) -> None:
        with TemporaryDirectory() as tmp:
            adapter = ScriptedAdapter(
                [
                    "resume",  # asked to continue...
                    # ...but there is nothing, so the normal new-project flow starts
                    "vertical_short",
                    "fullscreen_voiceover_v1",
                    "nature_science_news_ru",
                    "ru",
                    "topic",
                    "Тема",
                    "60",
                    "disabled",
                    "disabled",
                    "disabled",
                    True,
                    "run",
                ]
            )
            create_fn = FakeCreateFn([])
            result = run_wizard(adapter=adapter, create_fn=create_fn, projects_root=str(Path(tmp) / "empty"))
            self.assertIsNotNone(result)
            self.assertEqual(create_fn.requests[0].project_id, "")


class ResumeDoesNotRegenerateVoiceTests(unittest.TestCase):
    """The narration a user already paid for must survive a resume.

    Beyond wasting credits, re-running the voice stage with execute_voice=False
    rewrites voice_manifest.json as the unconfigured stub
    (src.news.voice_stage.build_safe_voice_manifest), which erased the record of
    narration still sitting on disk.
    """

    def _project_with_narration(self, root: Path) -> tuple[str, Path]:
        job = create_news_to_short_job(
            projects_root=root, channel_id="nature_science_news_ru", title="С озвучкой", language="ru"
        )
        voice_dir = root / job.job_id / "localizations" / "ru" / "voice"
        voice_dir.mkdir(parents=True, exist_ok=True)
        narration = voice_dir / "narration.wav"
        with wave.open(str(narration), "wb") as handle:
            handle.setnchannels(1)
            handle.setsampwidth(2)
            handle.setframerate(8000)
            handle.writeframes(b"\x00\x00" * 8000)
        manifest_path = voice_dir / "voice_manifest.json"
        manifest_path.write_text(
            json.dumps(
                {
                    "status": "completed",
                    "voice_stage_status": "completed",
                    "audio_path": str(narration),
                    "narration": {"duration_sec": 1.0, "pause_total_sec": 0.0},
                    "scenes": [{"scene_id": "scene_001", "scene_index": 0, "duration_seconds": 1.0}],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return job.job_id, manifest_path

    def _resume(self, root: Path, project_id: str):
        from src.content_creation.service import create_content

        request = ContentCreationRequest(
            project_id=project_id,
            channel_id="nature_science_news_ru",
            template_id="fullscreen_voiceover_v1",
            language="ru",
            voice=VoiceRequestConfig(provider="elevenlabs", approve_paid_generation=False),
            execution=ExecutionFlags(resume=True),
            project_overrides={"projects_root": str(root)},
        )

        calls: list[dict] = []

        class _Result:
            status = "completed"
            completed_stages: list[str] = []

        def _record(**kwargs):
            calls.append(kwargs)
            return _Result()

        with patch("src.news.pipeline.run_news_to_short_job", side_effect=_record):
            result = create_content(request)
        return result, calls

    def test_voice_stage_is_not_run_again_and_the_manifest_survives(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            project_id, manifest_path = self._project_with_narration(root)
            before = manifest_path.read_text(encoding="utf-8")

            result, calls = self._resume(root, project_id)

            self.assertNotIn("voice", [call.get("stage") for call in calls])
            self.assertEqual(manifest_path.read_text(encoding="utf-8"), before)
            voice_stage = next(stage for stage in result.stages if stage["stage"] == "voice")
            self.assertEqual(voice_stage["status"], "skipped_existing_audio")

    def test_no_paid_approval_is_requested_for_narration_that_already_exists(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            project_id, _ = self._project_with_narration(root)

            result, _ = self._resume(root, project_id)

            self.assertNotEqual(result.status, "prepared_awaiting_paid_approval")

    def test_a_manifest_pointing_at_a_deleted_file_is_not_treated_as_finished(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            project_id, manifest_path = self._project_with_narration(root)
            Path(json.loads(manifest_path.read_text(encoding="utf-8"))["audio_path"]).unlink()

            result, calls = self._resume(root, project_id)

            self.assertIn("voice", [call.get("stage") for call in calls])
            self.assertEqual(result.status, "prepared_awaiting_paid_approval")


if __name__ == "__main__":
    unittest.main()
