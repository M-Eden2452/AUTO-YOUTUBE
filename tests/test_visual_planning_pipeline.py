"""Stage Q2: visual planning seen from the pipeline, the asset layer and the CLI.

``tests.test_visual_planning`` covers the layer in isolation. This file covers the
seams, which is where a regression would actually hurt:

- ``build_visual_plan(script, language=..., user_assets=...)`` keeps the exact public
  contract the news_to_short pipeline has relied on since stage AB;
- the plan reaches the existing asset search through the ``semantic`` block
  ``analyze_scene`` already read, so no provider had to change;
- every ``visual_plan.json`` already on disk still parses;
- the ``visual-plan`` CLI works with no network, downloads, Vision or render.

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

from src.assets.semantic_selection import analyze_scene, ordered_queries
from src.content.script_engine import from_legacy_script
from src.content.visual_planning import from_legacy_visual_plan, validate_visual_plan
from src.content_creation.cli import main
from src.news.models import INPUT_MODE_TEXT, NewsJob
from src.news.research_engine import build_research
from src.news.script_generator import build_script
from src.news.visual_plan import build_visual_plan, make_stock_query

ARTICLE = (
    "Почему вороны узнают лица людей и помнят их годами? "
    "Исследователи в Вашингтонском университете надевали одну и ту же маску и ловили птиц. "
    "Вороны запоминали эту маску и потом кричали на любого человека, который её носил. "
    "Реакция сохранялась больше пяти лет, хотя птиц никто не трогал. "
    "Вороны передавали информацию сородичам, которые сами не попадали в ловушку. "
    "Это значит, что у ворон работает социальная передача знания об угрозе."
)


def _run_cli(argv: list[str]) -> tuple[int, str]:
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        code = main(argv)
    return code, buffer.getvalue()


def _material() -> tuple[dict, dict]:
    job = NewsJob.create(
        channel_id="nature_science_news_ru",
        input_mode=INPUT_MODE_TEXT,
        topic="Почему вороны узнают лица",
        input_text=ARTICLE,
        language="ru",
    )
    research = build_research(job, {"title": job.topic, "text": ARTICLE})
    return build_script(job, research), research


class PublicContractTest(unittest.TestCase):
    """build_visual_plan is the one function the pipeline calls. Its shape is frozen."""

    def setUp(self) -> None:
        self.script, self.research = _material()

    def test_signature_and_top_level_keys_are_unchanged(self) -> None:
        plan = build_visual_plan(self.script, language="ru", user_assets=[])
        for key in ("language", "aspect_ratio", "resolution", "scenes"):
            self.assertIn(key, plan)
        self.assertEqual(plan["language"], "ru")
        self.assertEqual(plan["resolution"], {"width": 1080, "height": 1920})

    def test_every_scene_carries_the_keys_downstream_stages_read(self) -> None:
        plan = build_visual_plan(self.script, language="ru")
        for scene in plan["scenes"]:
            for key in (
                "scene_id",
                "narration",
                "target_duration_sec",
                "visual_type",
                "visual_description",
                "primary_query",
                "alternative_queries",
                "negative_keywords",
                "preferred_asset_ids",
                "allow_user_asset",
                "allow_stock",
                "allow_article_asset",
                "fallback_type",
                "camera_effect",
                "transition",
            ):
                self.assertIn(key, scene)

    def test_one_plan_scene_per_script_scene_with_matching_ids(self) -> None:
        plan = build_visual_plan(self.script, language="ru")
        self.assertEqual(
            [scene["scene_id"] for scene in plan["scenes"]],
            [scene["scene_id"] for scene in self.script["scenes"]],
        )

    def test_durations_come_from_the_script(self) -> None:
        plan = build_visual_plan(self.script, language="ru")
        for planned, scripted in zip(plan["scenes"], self.script["scenes"], strict=True):
            self.assertAlmostEqual(planned["target_duration_sec"], scripted["target_duration_sec"], places=2)

    def test_user_assets_are_still_preferred_per_scene(self) -> None:
        plan = build_visual_plan(self.script, language="ru", user_assets=["a.mp4", "b.mp4"])
        preferred = [scene["preferred_asset_ids"] for scene in plan["scenes"]]
        self.assertEqual(preferred[0], ["user_asset_001"])
        self.assertEqual(preferred[1], ["user_asset_002"])
        self.assertEqual(preferred[2], [])

    def test_research_is_optional(self) -> None:
        without = build_visual_plan(self.script, language="ru")
        with_research = build_visual_plan(self.script, language="ru", research=self.research)
        self.assertEqual(len(without["scenes"]), len(with_research["scenes"]))

    def test_scenes_no_longer_share_one_of_four_fixed_queries(self) -> None:
        """The point of Q2: make_stock_query had four possible outputs, total."""
        plan = build_visual_plan(self.script, language="ru", research=self.research)
        primaries = [scene["primary_query"] for scene in plan["scenes"]]
        self.assertGreater(len(set(primaries)), 1)
        legacy_outputs = {
            make_stock_query(text)
            for text in ("кит", "ученые", "океан", "что угодно другое")
        }
        self.assertFalse(set(primaries) <= legacy_outputs, "запросы не должны сводиться к четырём старым строкам")

    def test_the_plan_is_serialisable(self) -> None:
        json.dumps(build_visual_plan(self.script, language="ru"), ensure_ascii=False)


class AssetLayerIntegrationTest(unittest.TestCase):
    """The plan must reach the existing search path without changing a provider."""

    def setUp(self) -> None:
        script, research = _material()
        self.plan = build_visual_plan(script, language="ru", research=research)

    def test_analyze_scene_uses_the_plan_instead_of_guessing(self) -> None:
        for scene in self.plan["scenes"]:
            with self.subTest(scene=scene["scene_id"]):
                semantic = analyze_scene(scene)
                self.assertEqual(semantic.subject, scene["semantic"]["subject"])
                self.assertEqual(semantic.must_include, scene["semantic"]["must_include"])
                self.assertEqual(semantic.visual_priority, scene["semantic"]["visual_priority"])

    def test_the_whale_prototype_heuristics_no_longer_fire(self) -> None:
        """Without an explicit semantic block, analyze_scene guessed from a hardcoded
        whale/ocean vocabulary. The plan supplies the block, so it does not."""
        for scene in self.plan["scenes"]:
            with self.subTest(scene=scene["scene_id"]):
                self.assertEqual(analyze_scene(scene).must_not_include, [])

    def test_every_scene_yields_ordered_provider_queries(self) -> None:
        for scene in self.plan["scenes"]:
            with self.subTest(scene=scene["scene_id"]):
                queries = ordered_queries(analyze_scene(scene))
                self.assertTrue(queries)
                levels = [query["fallback_level"] for query in queries]
                self.assertEqual(levels, sorted(levels))

    def test_provider_queries_are_plain_strings(self) -> None:
        """Providers take ``search(query: str, scene: dict, limit: int)`` and Q2 did
        not change that - the adapter turns structured intent into their strings."""
        for scene in self.plan["scenes"]:
            for query in ordered_queries(analyze_scene(scene)):
                self.assertIsInstance(query["query"], str)
                self.assertTrue(query["query"].strip())

    def test_visual_type_stays_in_the_vocabulary_routing_understands(self) -> None:
        for scene in self.plan["scenes"]:
            self.assertIn(scene["visual_type"], {"video", "image", "animated_image", "diagram"})

    def test_the_plan_never_claims_an_asset_is_licensed_or_chosen(self) -> None:
        """Selecting and clearing an asset is a later stage and stays there."""
        for scene in self.plan["scenes"]:
            for forbidden in ("selected_asset", "license", "license_name", "checksum_sha256", "download_url"):
                self.assertNotIn(forbidden, scene)


class PipelineStageTest(unittest.TestCase):
    """The real staged pipeline, dry-run, no network."""

    def test_visual_plan_stage_writes_a_plan_the_next_stage_can_read(self) -> None:
        from src.news.pipeline import create_news_to_short_job, run_news_to_short_job

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            job = create_news_to_short_job(
                projects_root=root, channel_id="nature_science_news_ru", text=ARTICLE, language="ru"
            )
            run_news_to_short_job(
                projects_root=root, job_id=job.job_id, until_stage="visual_plan", dry_run=True
            )
            lang_path = root / job.job_id / "localizations" / "ru" / "visual" / "visual_plan.json"
            master_path = root / job.job_id / "master" / "master_visual_plan.json"
            self.assertTrue(lang_path.is_file())
            self.assertTrue(master_path.is_file())

            plan = json.loads(lang_path.read_text(encoding="utf-8"))
            script = json.loads(
                (root / job.job_id / "localizations" / "ru" / "script" / "script.json").read_text(encoding="utf-8")
            )
            self.assertEqual(plan["planner_id"], "deterministic_local")
            self.assertEqual(len(plan["scenes"]), len(script["scenes"]))

            validation = validate_visual_plan(
                from_legacy_visual_plan(plan), script=from_legacy_script(script)
            )
            self.assertTrue(validation.valid, validation.codes())

    def test_the_asset_search_stage_still_runs_on_the_new_plan(self) -> None:
        from src.news.pipeline import create_news_to_short_job, run_news_to_short_job

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            job = create_news_to_short_job(
                projects_root=root, channel_id="nature_science_news_ru", text=ARTICLE, language="ru"
            )
            run_news_to_short_job(
                projects_root=root, job_id=job.job_id, until_stage="asset_search", dry_run=True
            )
            manifest_path = root / job.job_id / "assets" / "assets_manifest.json"
            self.assertTrue(manifest_path.is_file())
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertIn("scenes", manifest)


class ExistingProjectsTest(unittest.TestCase):
    """Every visual_plan.json already on disk must still parse. Read-only."""

    def test_every_existing_plan_is_readable(self) -> None:
        paths = sorted(glob.glob(os.path.join("projects", "*", "localizations", "*", "visual", "visual_plan.json")))
        if not paths:
            self.skipTest("no existing projects in this checkout")
        for path in paths:
            with self.subTest(project=Path(path).parts[1]):
                before = Path(path).read_bytes()
                plan = from_legacy_visual_plan(json.loads(before.decode("utf-8")))
                self.assertTrue(plan.scenes)
                validate_visual_plan(plan)
                self.assertEqual(Path(path).read_bytes(), before, "reading must not modify the file")

    def test_pre_q2_plans_are_recognised_as_schema_1(self) -> None:
        paths = sorted(glob.glob(os.path.join("projects", "*", "localizations", "*", "visual", "visual_plan.json")))
        if not paths:
            self.skipTest("no existing projects in this checkout")
        versions = {from_legacy_visual_plan(json.loads(Path(p).read_text(encoding="utf-8"))).schema_version for p in paths}
        self.assertIn(1, versions)


class VisualPlanCliTest(unittest.TestCase):
    """`content_creation.cli visual-plan` - offline by construction."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        script, research = _material()
        self.script_path = root / "script.json"
        self.claims_path = root / "claims.json"
        self.plan_path = root / "visual_plan.json"
        self.script_path.write_text(json.dumps(script, ensure_ascii=False), encoding="utf-8")
        self.claims_path.write_text(json.dumps(research, ensure_ascii=False), encoding="utf-8")

    def test_planners_lists_the_default_with_its_cost(self) -> None:
        code, output = _run_cli(["visual-plan", "planners", "--json"])
        self.assertEqual(code, 0)
        data = json.loads(output)
        self.assertEqual([item["planner_id"] for item in data], ["deterministic_local"])
        self.assertFalse(data[0]["requires_paid_api"])
        self.assertFalse(data[0]["requires_network"])

    def test_build_writes_nothing_unless_asked(self) -> None:
        before = set(os.listdir(self.tmp.name))
        code, output = _run_cli(["visual-plan", "build", "--script-file", str(self.script_path)])
        self.assertIn(code, (0, 1))
        self.assertIn("deterministic_local", output)
        self.assertEqual(set(os.listdir(self.tmp.name)), before)

    def test_build_writes_a_pipeline_compatible_file_with_out(self) -> None:
        code, _ = _run_cli(
            [
                "visual-plan", "build",
                "--script-file", str(self.script_path),
                "--claims-file", str(self.claims_path),
                "--out", str(self.plan_path),
            ]
        )
        self.assertIn(code, (0, 1))
        self.assertTrue(self.plan_path.is_file())
        stored = json.loads(self.plan_path.read_text(encoding="utf-8"))
        self.assertIn("scenes", stored)
        self.assertIn("semantic", stored["scenes"][0])
        self.assertTrue(ordered_queries(analyze_scene(stored["scenes"][0])))

    def test_build_json_output_is_machine_readable(self) -> None:
        code, output = _run_cli(["visual-plan", "build", "--script-file", str(self.script_path), "--json"])
        self.assertIn(code, (0, 1))
        data = json.loads(output)
        self.assertEqual(data["planner_id"], "deterministic_local")
        self.assertIn("validation", data)
        self.assertIn("visual_plan_json", data)

    def test_intents_prints_a_query_per_scene(self) -> None:
        _run_cli(["visual-plan", "build", "--script-file", str(self.script_path), "--out", str(self.plan_path)])
        code, output = _run_cli(["visual-plan", "intents", "--plan-file", str(self.plan_path), "--json"])
        self.assertEqual(code, 0)
        data = json.loads(output)
        self.assertTrue(data)
        for entry in data:
            self.assertTrue(entry["intents"], entry["scene_id"])

    def test_validate_checks_a_plan_against_its_script(self) -> None:
        _run_cli(["visual-plan", "build", "--script-file", str(self.script_path), "--out", str(self.plan_path)])
        code, output = _run_cli(
            [
                "visual-plan", "validate",
                "--plan-file", str(self.plan_path),
                "--script-file", str(self.script_path),
                "--json",
            ]
        )
        self.assertIn(code, (0, 1))
        self.assertIn(json.loads(output)["status"], {"passed", "needs_review", "failed"})

    def test_validate_reports_a_broken_plan_instead_of_crashing(self) -> None:
        broken = Path(self.tmp.name) / "broken.json"
        broken.write_text(json.dumps({"scenes": []}), encoding="utf-8")
        code, output = _run_cli(["visual-plan", "validate", "--plan-file", str(broken), "--json"])
        self.assertEqual(code, 1)
        self.assertIn("empty_plan", output)

    def test_missing_arguments_are_refused_clearly(self) -> None:
        for argv in (
            ["visual-plan", "build"],
            ["visual-plan", "validate"],
            ["visual-plan", "intents"],
            ["visual-plan", "build", "--script-file", "нет_такого.json"],
        ):
            with self.subTest(argv=argv):
                with self.assertRaises(SystemExit):
                    _run_cli(argv)


if __name__ == "__main__":
    unittest.main()
