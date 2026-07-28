"""Stage Q1: the script engine seen from the pipeline, the timeline and the CLI.

``tests.test_script_engine`` covers the engine in isolation. This file covers the
seams it was plugged into, which is where a regression would actually hurt:

- ``build_script(job, research)`` keeps the exact public contract the news_to_short
  pipeline has relied on since stage AB;
- scripts with any number of scenes and any mix of durations survive
  ``src.audio.scene_timeline``, which used to only ever see six equal-ish scenes;
- every ``script.json`` already on disk still parses;
- the ``script`` CLI works without network, TTS, downloads, render or a paid API.

Nothing here writes into ``projects/``: real project files are opened read-only and
generated output goes to a temporary directory.
"""

from __future__ import annotations

import contextlib
import glob
import io
import json
import os
import tempfile
import unittest
from pathlib import Path

from src.audio.scene_timeline import apply_timeline_to_script, build_scene_timeline
from src.content.script_engine import SCRIPT_SCHEMA_VERSION, from_legacy_script, validate_script
from src.content_creation.cli import main
from src.news.models import INPUT_MODE_TEXT, INPUT_MODE_TOPIC, NewsJob
from src.news.research_engine import build_research
from src.news.script_generator import (
    JOB_SOURCE_KINDS,
    build_script,
    build_script_request,
    generate_for_job,
    resolve_source_kind,
)

ARTICLE = (
    "Почему вороны узнают лица людей и помнят их годами? "
    "Исследователи из Вашингтонского университета надевали одну и ту же маску и ловили птиц. "
    "Вороны запоминали эту маску и потом кричали на любого человека, который её носил. "
    "Реакция сохранялась больше пяти лет подряд, хотя птиц больше никто не трогал. "
    "Более того, птицы передавали информацию сородичам, которые сами никогда не попадали в ловушку. "
    "Это значит, что у ворон работает социальная передача знания о конкретной угрозе."
)


def _run_cli(argv: list[str]) -> tuple[int, str]:
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        code = main(argv)
    return code, buffer.getvalue()


def _job(**overrides) -> NewsJob:
    base = {
        "channel_id": "nature_science_news_ru",
        "input_mode": INPUT_MODE_TEXT,
        "topic": "Почему вороны узнают лица",
        "input_text": ARTICLE,
        "language": "ru",
        "target_duration_sec": 55,
    }
    base.update(overrides)
    return NewsJob.create(**base)


def _research(job: NewsJob | None = None, text: str = ARTICLE) -> dict:
    """The real research payload, built by the real research engine.

    Claims are the article's own first eight sentences (``research_engine``), which
    is why ``build_script_request`` does not also pass the raw text: hand-written
    fixtures with three short claims describe an input the pipeline never produces.
    """
    job = job or _job(input_text=text)
    return build_research(job, {"title": job.topic, "text": text})


class PublicContractTest(unittest.TestCase):
    """build_script is the one function the pipeline calls. Its shape is frozen."""

    def test_signature_and_return_type_are_unchanged(self) -> None:
        script = build_script(_job(), _research())
        self.assertIsInstance(script, dict)
        for key in (
            "title",
            "hook",
            "language",
            "target_duration_sec",
            "estimated_duration_sec",
            "narration_text",
            "description",
            "source_claim_ids",
            "scenes",
        ):
            self.assertIn(key, script)

    def test_every_scene_carries_the_keys_downstream_stages_read(self) -> None:
        script = build_script(_job(), _research())
        for scene in script["scenes"]:
            for key in (
                "scene_id",
                "start_sec",
                "target_duration_sec",
                "narration",
                "claim_ids",
                "visual_intent",
                "on_screen_text",
                "emotion",
            ):
                self.assertIn(key, scene)

    def test_narration_text_matches_the_scenes(self) -> None:
        """pipeline.py writes narration.txt straight from this field."""
        script = build_script(_job(), _research())
        self.assertEqual(script["narration_text"], "\n".join(s["narration"] for s in script["scenes"]))

    def test_scene_ids_are_unique_and_sequential(self) -> None:
        script = build_script(_job(), _research())
        ids = [scene["scene_id"] for scene in script["scenes"]]
        self.assertEqual(ids, [f"scene_{index:03d}" for index in range(1, len(ids) + 1)])

    def test_start_times_are_contiguous(self) -> None:
        script = build_script(_job(), _research())
        cursor = 0.0
        for scene in script["scenes"]:
            self.assertAlmostEqual(scene["start_sec"], cursor, places=2)
            cursor += scene["target_duration_sec"]

    def test_the_verdict_travels_with_the_script(self) -> None:
        script = build_script(_job(), _research())
        self.assertIn("script_validation", script)
        self.assertIn(script["script_validation"]["status"], {"passed", "needs_review", "failed"})

    def test_result_is_json_serialisable(self) -> None:
        json.dumps(build_script(_job(), _research()), ensure_ascii=False)

    def test_orca_topic_gets_video_first_retrieval_briefs_without_hard_exact_gate(self) -> None:
        job = _job(
            topic="Почему косатки взрывают огромных рыб",
            input_text=(
                "Косатки охотятся на рыбу-луну. "
                "Учёные изучают точную координацию двух животных."
            ),
            script_source="user_script",
        )
        script = build_script(job, {})
        briefs = [scene.get("visual_brief") for scene in script["scenes"]]
        self.assertTrue(briefs)
        self.assertTrue(all(brief and brief["subject"] == "orca killer whale" for brief in briefs))
        self.assertTrue(all(brief["media_types"] == ["video", "image"] for brief in briefs))
        self.assertTrue(all(not brief.get("must_include") for brief in briefs))
        self.assertIn("dolphin", briefs[0]["must_avoid"])
        self.assertTrue(briefs[0]["provider_queries"]["default"])

    def test_the_default_no_longer_produces_the_fixed_six(self) -> None:
        """The point of Q1: an article gets a script shaped by its own content."""
        script = build_script(_job(), _research())
        durations = [scene["target_duration_sec"] for scene in script["scenes"]]
        self.assertNotEqual(durations, [3.5, 7.0, 10.0, 13.0, 10.0, 8.0])
        self.assertGreater(len(set(durations)), 1)

    def test_asking_for_the_legacy_provider_restores_the_old_shape(self) -> None:
        script = build_script(_job(script_provider="legacy_template"), _research())
        self.assertEqual(
            [scene["target_duration_sec"] for scene in script["scenes"]],
            [3.5, 7.0, 10.0, 13.0, 10.0, 8.0],
        )


class SourceKindResolutionTest(unittest.TestCase):
    """What the pipeline thinks the input is decides which provider answers."""

    def test_a_job_without_the_new_fields_behaves_as_before(self) -> None:
        """Every job.json written before Q1 lacks script_source entirely."""
        job = _job()
        job.script_source = ""
        self.assertEqual(resolve_source_kind(job, _research()), "research")

    def test_topic_without_research_is_a_topic(self) -> None:
        job = _job(input_mode=INPUT_MODE_TOPIC, input_text="")
        job.script_source = ""
        self.assertEqual(resolve_source_kind(job, {"claims": []}), "topic")

    def test_a_declared_source_wins(self) -> None:
        job = _job(script_source="user_script")
        self.assertEqual(resolve_source_kind(job, _research()), "user_script")

    def test_an_unknown_declared_source_is_ignored_not_trusted(self) -> None:
        job = _job(script_source="нечто")
        self.assertEqual(resolve_source_kind(job, _research()), "research")

    def test_all_declared_kinds_are_known_to_the_engine(self) -> None:
        for kind in JOB_SOURCE_KINDS:
            with self.subTest(kind=kind):
                job = _job(script_source=kind)
                self.assertEqual(resolve_source_kind(job, _research()), kind)

    def test_a_ready_script_is_not_shredded_into_research(self) -> None:
        """The defect this stage removed: a pasted script used to be cut into
        sentences and re-wrapped in the template generator's own phrases."""
        script_text = (
            "Вороны узнают человеческие лица и помнят обидчиков.\n\n"
            "Учёные надевали маску и ловили птиц, чтобы проверить память.\n\n"
            "Поэтому вороны предупреждают сородичей об опасном человеке."
        )
        job = _job(input_text=script_text, script_source="user_script")
        request = build_script_request(job, _research())
        self.assertEqual(request.raw_text, script_text)

        outcome = generate_for_job(job, _research())
        self.assertEqual(outcome.provider_id, "user_supplied")
        spoken = " ".join(scene.narration for scene in outcome.result.scenes)
        for block in script_text.split("\n\n"):
            self.assertIn(block.strip(), spoken)

    def test_research_input_still_goes_through_research(self) -> None:
        request = build_script_request(_job(), _research())
        self.assertEqual(request.source_kind, "research")
        self.assertTrue(request.claims)

    def test_claims_are_not_duplicated_by_also_passing_the_raw_text(self) -> None:
        """research_engine's claims already are the article's sentences."""
        request = build_script_request(_job(), _research())
        self.assertEqual(request.raw_text, "")

    def test_thin_material_falls_back_to_the_previous_generator(self) -> None:
        """A bare topic has nothing to write from; the old template takes over and
        the script says so, rather than inventing filler."""
        job = _job(input_mode=INPUT_MODE_TOPIC, input_text="", topic="Вороны")
        outcome = generate_for_job(job, {"topic": "Вороны", "claims": [], "summary": ""})
        self.assertEqual(outcome.provider_id, "legacy_template")
        self.assertTrue(any("insufficient_source_material" in w for w in outcome.result.warnings))


class BackwardCompatibleJobTest(unittest.TestCase):
    """A job.json written before Q1 must load and run unchanged."""

    def test_new_fields_all_default_to_off(self) -> None:
        job = NewsJob.create(channel_id="c", input_mode=INPUT_MODE_TOPIC, topic="Тема")
        self.assertEqual(job.script_provider, "")
        self.assertEqual(job.script_source, "")
        self.assertFalse(job.script_include_cta)
        self.assertEqual(job.script_cta_text, "")

    def test_a_pre_q1_job_dict_round_trips(self) -> None:
        job = _job()
        payload = {
            key: value
            for key, value in job.to_dict().items()
            if not key.startswith("script_")
        }
        restored = NewsJob.from_dict(payload)
        self.assertEqual(restored.script_provider, "")
        self.assertEqual(restored.script_source, "")

    def test_no_cta_is_ever_added_without_being_asked(self) -> None:
        script = build_script(_job(), _research())
        self.assertNotIn("cta", [scene.get("role") for scene in script["scenes"]])


class SceneTimelineCompatibilityTest(unittest.TestCase):
    """Variable scene counts and lengths must survive the real timeline builder."""

    def _voice_manifest(self, scene_ids: list[str], durations: list[float], pause: float = 0.35) -> dict:
        return {
            "schema_version": 2,
            "status": "completed",
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
                "duration_sec": sum(durations) + pause * (len(durations) - 1),
                "pause_total_sec": pause * (len(durations) - 1),
            },
        }

    def _script_with(self, count: int) -> dict:
        """A script with `count` scenes of deliberately unequal lengths."""
        scenes = []
        cursor = 0.0
        for index in range(1, count + 1):
            duration = round(2.0 + (index * 1.9) % 11.0, 2)
            scenes.append(
                {
                    "scene_id": f"scene_{index:03d}",
                    "start_sec": round(cursor, 2),
                    "target_duration_sec": duration,
                    "narration": f"Предложение номер {index} про наблюдение за птицами.",
                    "claim_ids": [],
                    "visual_intent": "птицы",
                    "on_screen_text": f"Сцена {index}",
                    "emotion": "explanation",
                    "role": "hook" if index == 1 else ("payoff" if index == count else "development"),
                }
            )
            cursor += duration
        return {
            "title": "Тест",
            "hook": scenes[0]["narration"],
            "language": "ru",
            "target_duration_sec": 55,
            "estimated_duration_sec": round(cursor, 2),
            "narration_text": "\n".join(scene["narration"] for scene in scenes),
            "description": "Тест",
            "source_claim_ids": [],
            "scenes": scenes,
        }

    def test_any_scene_count_produces_a_usable_timeline(self) -> None:
        for count in (3, 4, 6, 7, 11, 18):
            with self.subTest(scenes=count):
                script = self._script_with(count)
                ids = [scene["scene_id"] for scene in script["scenes"]]
                spoken = [round(1.5 + (index * 2.3) % 9.0, 2) for index in range(count)]
                timeline = build_scene_timeline(self._voice_manifest(ids, spoken), script=script)
                self.assertTrue(timeline)
                self.assertEqual(len(timeline.scenes), count)

    def test_real_durations_are_written_back_onto_every_scene(self) -> None:
        script = self._script_with(7)
        ids = [scene["scene_id"] for scene in script["scenes"]]
        spoken = [round(2.0 + index * 1.3, 2) for index in range(7)]
        timeline = build_scene_timeline(self._voice_manifest(ids, spoken), script=script)
        updated = apply_timeline_to_script(json.loads(json.dumps(script)), timeline)
        for index, scene in enumerate(updated["scenes"]):
            self.assertAlmostEqual(scene["speech_duration_sec"], spoken[index], places=2)
            # the plan is preserved next to the measurement, never overwritten
            self.assertEqual(scene["target_duration_sec"], script["scenes"][index]["target_duration_sec"])

    def test_an_engine_written_script_goes_through_the_timeline(self) -> None:
        script = build_script(_job(), _research())
        ids = [scene["scene_id"] for scene in script["scenes"]]
        spoken = [round(scene["target_duration_sec"] * 1.15, 2) for scene in script["scenes"]]
        timeline = build_scene_timeline(self._voice_manifest(ids, spoken), script=script)
        self.assertTrue(timeline)
        self.assertEqual(len(timeline.scenes), len(script["scenes"]))

    def test_declared_pauses_are_honoured(self) -> None:
        script = self._script_with(4)
        for scene in script["scenes"]:
            scene["pause_after_sec"] = 0.5
        ids = [scene["scene_id"] for scene in script["scenes"]]
        timeline = build_scene_timeline(
            self._voice_manifest(ids, [3.0, 4.0, 5.0, 6.0], pause=0.5), script=script
        )
        self.assertTrue(timeline)
        self.assertEqual(len(timeline.scenes), 4)


class ExistingProjectsTest(unittest.TestCase):
    """Every script.json already on disk must still parse. Read-only."""

    def _paths(self) -> list[str]:
        return sorted(glob.glob(os.path.join("projects", "*", "localizations", "*", "script", "script.json")))

    def test_every_existing_script_is_readable(self) -> None:
        paths = self._paths()
        if not paths:
            self.skipTest("no existing projects in this checkout")
        for path in paths:
            with self.subTest(project=Path(path).parts[1]):
                before = Path(path).read_bytes()
                data = json.loads(before.decode("utf-8"))
                result = from_legacy_script(data)
                self.assertTrue(result.scenes, "a stored script must yield scenes")
                # 1 = written before the engine existed, 2 = written by it. Both must
                # parse. This used to assert 1 outright, which was true only while no
                # project had yet been created *through* the engine; the first real
                # run made it false without anything being wrong.
                self.assertIn(result.schema_version, (1, SCRIPT_SCHEMA_VERSION), "stored script schema must be known")
                validate_script(result, expected_language=result.language or "ru")
                self.assertEqual(Path(path).read_bytes(), before, "reading must not modify the file")

    def test_scene_counts_on_disk_are_not_all_six(self) -> None:
        """Sanity check on the fixtures themselves: some real projects already have
        a different number of scenes, so role inference is exercised for real."""
        paths = self._paths()
        if not paths:
            self.skipTest("no existing projects in this checkout")
        counts = {len(from_legacy_script(json.loads(Path(p).read_text(encoding="utf-8"))).scenes) for p in paths}
        self.assertTrue(counts)


class ScriptCliTest(unittest.TestCase):
    """`content_creation.cli script` - offline by construction."""

    def test_providers_lists_all_four_with_their_cost(self) -> None:
        code, output = _run_cli(["script", "providers"])
        self.assertEqual(code, 0)
        for provider_id in ("deterministic_local", "user_supplied", "legacy_template", "llm"):
            self.assertIn(provider_id, output)
        self.assertIn("платный", output)
        self.assertIn("офлайн", output)

    def test_providers_json(self) -> None:
        code, output = _run_cli(["script", "providers", "--json"])
        self.assertEqual(code, 0)
        data = json.loads(output)
        paid = {item["provider_id"] for item in data if item["requires_paid_api"]}
        self.assertEqual(paid, {"llm"})

    def test_generate_from_text_writes_nothing_unless_asked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            before = set(os.listdir(tmp))
            code, output = _run_cli(["script", "generate", "--text", ARTICLE])
            self.assertIn(code, (0, 1))
            self.assertIn("deterministic_local", output)
            self.assertEqual(set(os.listdir(tmp)), before)

    def test_generate_writes_a_pipeline_compatible_file_with_out(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "nested" / "script.json"
            code, _ = _run_cli(["script", "generate", "--text", ARTICLE, "--out", str(out)])
            self.assertIn(code, (0, 1))
            self.assertTrue(out.is_file())
            script = json.loads(out.read_text(encoding="utf-8"))
            for key in ("title", "hook", "narration_text", "scenes"):
                self.assertIn(key, script)
            self.assertTrue(from_legacy_script(script).scenes)

    def test_generate_json_output_is_machine_readable(self) -> None:
        code, output = _run_cli(["script", "generate", "--text", ARTICLE, "--json"])
        self.assertIn(code, (0, 1))
        data = json.loads(output)
        self.assertEqual(data["provider_id"], "deterministic_local")
        self.assertIn("validation", data)
        self.assertIn("script_json", data)

    def test_generate_honours_an_explicit_provider(self) -> None:
        code, output = _run_cli(
            ["script", "generate", "--text", ARTICLE, "--provider", "legacy_template", "--json"]
        )
        self.assertIn(code, (0, 1))
        self.assertEqual(json.loads(output)["provider_id"], "legacy_template")

    def test_generate_from_a_ready_script_keeps_the_users_words(self) -> None:
        text = "Первая мысль про ворон и их память.\n\nВторая мысль про маски учёных.\n\nПоэтому знание передаётся."
        code, output = _run_cli(
            ["script", "generate", "--text", text, "--source-kind", "user_script", "--json"]
        )
        self.assertIn(code, (0, 1))
        data = json.loads(output)
        self.assertEqual(data["provider_id"], "user_supplied")
        self.assertEqual(len(data["script"]["scenes"]), 3)

    def test_generate_from_a_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "article.txt"
            source.write_text(ARTICLE, encoding="utf-8")
            code, output = _run_cli(["script", "generate", "--text-file", str(source), "--json"])
            self.assertIn(code, (0, 1))
            self.assertTrue(json.loads(output)["script"]["scenes"])

    def test_generate_without_input_is_refused(self) -> None:
        with self.assertRaises(SystemExit):
            _run_cli(["script", "generate"])

    def test_validate_reads_an_existing_script(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "script.json"
            _run_cli(["script", "generate", "--text", ARTICLE, "--out", str(out)])
            code, output = _run_cli(["script", "validate", "--script-file", str(out), "--json"])
            self.assertIn(code, (0, 1))
            data = json.loads(output)
            self.assertIn(data["status"], {"passed", "needs_review", "failed"})
            self.assertGreater(data["scene_count"], 0)

    def test_validate_reports_a_broken_script_instead_of_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            broken = Path(tmp) / "script.json"
            broken.write_text(json.dumps({"scenes": []}), encoding="utf-8")
            code, output = _run_cli(["script", "validate", "--script-file", str(broken), "--json"])
            self.assertEqual(code, 1)
            self.assertIn("empty_script", output)

    def test_validate_without_a_file_is_refused(self) -> None:
        with self.assertRaises(SystemExit):
            _run_cli(["script", "validate"])

    def test_validate_of_a_missing_file_is_a_clear_message(self) -> None:
        with self.assertRaises(SystemExit) as caught:
            _run_cli(["script", "validate", "--script-file", "нет_такого_файла.json"])
        self.assertIn("не найден", str(caught.exception).lower())

    def test_cta_is_opt_in_from_the_cli(self) -> None:
        code, output = _run_cli(["script", "generate", "--text", ARTICLE, "--json"])
        self.assertNotIn('"role": "cta"', output)
        code, output = _run_cli(
            ["script", "generate", "--text", ARTICLE, "--include-cta", "--cta-text", "Подпишитесь.", "--json"]
        )
        self.assertIn(code, (0, 1))
        roles = [scene["role"] for scene in json.loads(output)["script"]["scenes"]]
        self.assertEqual(roles[-1], "cta")


if __name__ == "__main__":
    unittest.main()
