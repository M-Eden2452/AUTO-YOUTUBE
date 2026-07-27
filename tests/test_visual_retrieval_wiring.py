"""Stage Q2.2A: the wiring gaps and the hard gates the Q2.1 retest exposed.

The retest could not deliver a visual brief through any command - it had to be written
into the project's script.json by hand. The infographic specification was silently
dropped between the brief and the plan. A scene whose picture the project draws itself
was still offered to three photo archives and came back with a photograph of Mars,
selected while its own record said the requirement could not be verified.

Each test below pins one of those. No network, no paid API, no downloads, no render.
"""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from src.assets.generated_infographic import spec_from_scene
from src.assets.scene_strategy import build_strategy
from src.assets.semantic_selection import SemanticScene, rank_candidates
from src.content.visual_planning.brief import parse_brief
from src.content_creation import input_validation
from src.content_creation.cli import main
from src.news.asset_manager import build_assets_manifest
from src.news.models import INPUT_MODE_TEXT, NewsJob
from src.news.research_engine import build_research
from src.news.script_generator import build_script, build_script_request
from src.news.visual_plan import build_visual_plan

ALL_PROVIDERS = ["local_library", "pexels", "pixabay", "wikimedia", "nasa_images", "internet_archive"]

BRIEF_FILE = {
    "1": {
        "subject": "McMurdo Dry Valleys",
        "place": "McMurdo Dry Valleys, Antarctica",
        "exact_entities": ["McMurdo Dry Valleys", "Antarctica"],
        "must_avoid": ["tropical forest", "city"],
        "source_class": "exact_location",
        "shot_type": "establishing",
        "provider_queries": {"nasa_images": ["McMurdo Dry Valleys Antarctica satellite aerial"]},
    },
    "scene_002": {
        "source_class": "data_infographic",
        "media_types": ["image"],
        "infographic": {
            "title": "Нанопластик в пробах грунта",
            "headline_value": "54%",
            "caption": "участков верхнего слоя",
            "total_points": 13,
            "active_points": 7,
            "top_layer_label": "верхний слой 0–5 см",
            "top_layer_marks": 7,
            "deep_layer_label": "глубокий слой >20 см",
            "deep_layer_marks": 2,
        },
    },
}
SCRIPT_TEXT = "Первая сцена про Сухие долины Антарктиды.\n\nВторая сцена про пятьдесят четыре процента проб."


def _write(directory: Path, name: str, payload) -> str:
    path = directory / name
    if isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
    else:
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return str(path)


def _run_cli(argv: list[str]) -> tuple[int, str]:
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        code = main(argv)
    return code, buffer.getvalue()


def _job(**overrides) -> NewsJob:
    base = {
        "channel_id": "nature_science_news_ru",
        "input_mode": INPUT_MODE_TEXT,
        "topic": "Нанопластик",
        "input_text": SCRIPT_TEXT,
        "language": "ru",
        "target_duration_sec": 30,
        "script_source": "user_script",
    }
    base.update(overrides)
    return NewsJob.create(**base)


def _candidate(asset_id: str, title: str, **overrides) -> dict:
    candidate = {
        "asset_id": asset_id,
        "provider": "wikimedia",
        "media_type": "image",
        "type": "image",
        "title": title,
        "description": title,
        "tags": title.lower().split(),
        "tags_source": "provider",
        "source_page_url": f"https://example.test/{asset_id}",
        "license": {"license_name": "test", "rights_status": "licensed", "allowed_for_render": True, "review_required": False},
        "rights_status": "licensed",
        "allowed_for_render": True,
        "review_required": False,
        "width": 1080,
        "height": 1920,
        "duration_sec": 0,
    }
    candidate.update(overrides)
    return candidate


class BriefEntryPointTests(unittest.TestCase):
    """Gap 1: a brief must reach a real project through a command, not by hand."""

    def test_a_brief_file_reaches_the_script_through_the_job(self) -> None:
        job = _job(visual_briefs=BRIEF_FILE)
        request = build_script_request(job, build_research(job, {"title": "t", "text": SCRIPT_TEXT}))
        self.assertEqual(request.visual_briefs["1"]["subject"], "McMurdo Dry Valleys")
        script = build_script(job, build_research(job, {"title": "t", "text": SCRIPT_TEXT}))
        self.assertEqual(script["script_provider"], "user_supplied")
        self.assertEqual(script["scenes"][0]["visual_brief"]["place"], "McMurdo Dry Valleys, Antarctica")
        self.assertEqual(script["scenes"][1]["visual_brief"]["source_class"], "data_infographic")

    def test_the_brief_never_reaches_what_is_spoken(self) -> None:
        job = _job(visual_briefs=BRIEF_FILE)
        script = build_script(job, build_research(job, {"title": "t", "text": SCRIPT_TEXT}))
        self.assertNotIn("McMurdo", script["narration_text"])
        self.assertNotIn("data_infographic", script["narration_text"])
        self.assertEqual(script["narration_text"].split("\n"), [s.strip() for s in SCRIPT_TEXT.split("\n\n")])

    def test_scene_ids_are_unchanged_by_a_brief(self) -> None:
        with_brief = build_script(_job(visual_briefs=BRIEF_FILE), build_research(_job(), {"title": "t", "text": SCRIPT_TEXT}))
        without = build_script(_job(), build_research(_job(), {"title": "t", "text": SCRIPT_TEXT}))
        self.assertEqual(
            [s["scene_id"] for s in with_brief["scenes"]], [s["scene_id"] for s in without["scenes"]]
        )
        self.assertEqual(
            [s["narration"] for s in with_brief["scenes"]], [s["narration"] for s in without["scenes"]]
        )

    def test_a_job_without_briefs_behaves_exactly_as_before(self) -> None:
        script = build_script(_job(), build_research(_job(), {"title": "t", "text": SCRIPT_TEXT}))
        for scene in script["scenes"]:
            self.assertNotIn("visual_brief", scene)

    def test_a_job_json_written_before_this_field_still_loads(self) -> None:
        data = _job().to_dict()
        data.pop("visual_briefs")
        self.assertEqual(NewsJob.from_dict(data).visual_briefs, {})

    def test_the_offline_cli_check_reports_the_brief_and_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            script_file = _write(directory, "script.txt", SCRIPT_TEXT)
            brief_file = _write(directory, "brief.json", BRIEF_FILE)
            before = set(directory.iterdir())
            code, out = _run_cli([
                "script", "generate", "--source-kind", "user_script",
                "--text-file", script_file, "--visual-brief", brief_file,
                "--language", "ru", "--target-duration", "30",
            ])
            self.assertEqual(code, 0)
            self.assertIn("McMurdo Dry Valleys", out)
            self.assertIn("data_infographic", out)
            self.assertEqual(set(directory.iterdir()), before, "the check must write nothing")

    def test_a_broken_brief_file_is_refused_with_a_message(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            self.assertFalse(input_validation.validate_visual_brief_file(str(directory / "missing.json")).valid)
            bad_json = directory / "bad.json"
            bad_json.write_text("{not json", encoding="utf-8")
            result = input_validation.validate_visual_brief_file(str(bad_json))
            self.assertFalse(result.valid)
            self.assertEqual(result.reason, "invalid_json")
            wrong_shape = _write(directory, "shape.json", {"1": "not an object"})
            self.assertEqual(input_validation.validate_visual_brief_file(wrong_shape).reason, "invalid_scene_brief")
            not_a_map = _write(directory, "list.json", ["a"])
            self.assertEqual(input_validation.validate_visual_brief_file(not_a_map).reason, "invalid_shape")

    def test_a_valid_brief_file_loads(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(Path(tmp), "brief.json", BRIEF_FILE)
            self.assertTrue(input_validation.validate_visual_brief_file(path).valid)
            self.assertEqual(input_validation.load_visual_briefs(path)["1"]["source_class"], "exact_location")


class InfographicSpecTravelTests(unittest.TestCase):
    """Gap 2: the numbers must arrive at the generator exactly as written."""

    def test_the_spec_survives_brief_to_plan(self) -> None:
        job = _job(visual_briefs=BRIEF_FILE)
        script = build_script(job, build_research(job, {"title": "t", "text": SCRIPT_TEXT}))
        plan = build_visual_plan(script, language="ru")
        scene = plan["scenes"][1]
        self.assertEqual(scene["source_class"], "data_infographic")
        spec = spec_from_scene(scene)
        self.assertIsNotNone(spec, "the generator must receive the spec from the plan")
        self.assertEqual(spec.headline_value, "54%")
        self.assertEqual(spec.total_points, 13)
        self.assertEqual(spec.active_points, 7)
        self.assertEqual(spec.top_layer_marks, 7)
        self.assertEqual(spec.deep_layer_marks, 2)
        self.assertEqual(spec.caption, "участков верхнего слоя")

    def test_the_spec_round_trips_through_parse_and_serialise(self) -> None:
        brief = parse_brief(BRIEF_FILE["scene_002"])
        self.assertEqual(brief.infographic["total_points"], 13)
        self.assertEqual(parse_brief(brief.to_dict()).infographic, brief.infographic)

    def test_a_brief_without_an_infographic_is_still_valid(self) -> None:
        brief = parse_brief(BRIEF_FILE["1"])
        self.assertEqual(brief.infographic, {})
        self.assertFalse(brief.is_empty)

    def test_unknown_keys_do_not_cost_the_known_ones(self) -> None:
        brief = parse_brief({"subject": "kept", "какое-то-поле": "ignored", "infographic": {"headline_value": "9%"}})
        self.assertEqual(brief.subject, "kept")
        self.assertEqual(brief.infographic["headline_value"], "9%")

    def test_statistics_are_never_guessed_from_narration(self) -> None:
        job = _job()
        script = build_script(job, build_research(job, {"title": "t", "text": SCRIPT_TEXT}))
        plan = build_visual_plan(script, language="ru")
        for scene in plan["scenes"]:
            self.assertIsNone(spec_from_scene(scene))


class DataInfographicIsolationTests(unittest.TestCase):
    """Gap 3: a drawn figure is never sourced from a photo archive."""

    def test_no_external_provider_is_asked(self) -> None:
        scene = {"scene_id": "scene_001", "visual_type": "image", "visual_brief": {"source_class": "data_infographic"}}
        strategy = build_strategy(scene, available_providers=ALL_PROVIDERS)
        self.assertEqual(strategy.provider_order, ["local_library"])
        for provider in ("pexels", "pixabay", "wikimedia", "nasa_images", "internet_archive"):
            self.assertIn(provider, strategy.skipped_providers)

    def test_manual_required_asks_nobody(self) -> None:
        scene = {"scene_id": "scene_001", "visual_type": "video", "visual_brief": {"source_class": "manual_required"}}
        self.assertEqual(build_strategy(scene, available_providers=ALL_PROVIDERS).provider_order, [])

    def test_a_spec_produces_a_project_owned_asset(self) -> None:
        plan = self._plan(BRIEF_FILE["scene_002"])
        with tempfile.TemporaryDirectory() as tmp:
            manifest = build_assets_manifest(
                visual_plan=plan, user_assets=[], media_index={"version": 1, "items": []},
                providers=[], dry_run=False, project_root=Path(tmp) / "p", project_id="p",
            )
            selected = manifest["scenes"][0]["selected_asset"]
            self.assertIsNotNone(selected)
            self.assertEqual(selected["provider"], "generated")
            self.assertEqual(selected["rights_status"], "user_owned")
            self.assertTrue(Path(selected["path"]).is_file())
            self.assertEqual(len(selected["checksum_sha256"]), 64)
            self.assertEqual(manifest["missing_scenes"], [])

    def test_without_a_spec_the_scene_is_unresolved_not_substituted(self) -> None:
        plan = self._plan({"source_class": "data_infographic", "media_types": ["image"]})
        with tempfile.TemporaryDirectory() as tmp:
            manifest = build_assets_manifest(
                visual_plan=plan, user_assets=[], media_index={"version": 1, "items": []},
                providers=[], dry_run=False, project_root=Path(tmp) / "p", project_id="p",
            )
            self.assertIsNone(manifest["scenes"][0]["selected_asset"])
            self.assertEqual(manifest["missing_scenes"][0]["reason"], "unresolved_generator_failed")

    def _plan(self, brief: dict) -> dict:
        script = {
            "language": "ru",
            "scenes": [{
                "scene_id": "scene_001",
                "narration": "Наночастицы обнаружили на пятидесяти четырёх процентах участков.",
                "target_duration_sec": 8.0,
                "visual_brief": brief,
            }],
        }
        return build_visual_plan(script, language="ru")


class HardGateTests(unittest.TestCase):
    """No automatic selection without semantic and technical confirmation."""

    def test_an_unverifiable_requirement_blocks_selection(self) -> None:
        scene = SemanticScene(scene_id="s", subject=["грунте"], must_include=["грунте"], visual_priority="exact_subject")
        ranked = rank_candidates(scene, [_candidate("mars", "Spring Fans and Polygons on Mars", provider="nasa_images", width=2880, height=1800)])
        self.assertTrue(ranked[0]["rejected"])
        self.assertIn("semantic_unverified:грунте", ranked[0]["reject_reason"])

    def test_a_candidate_with_no_metadata_at_all_blocks_selection(self) -> None:
        scene = SemanticScene(scene_id="s", subject=["antarctica"], visual_priority="environment")
        ranked = rank_candidates(scene, [_candidate("blank", "", tags=[], description="")])
        self.assertTrue(ranked[0]["rejected"])
        self.assertIn("semantic_unverified", ranked[0]["reject_reason"])

    def test_an_incidental_unverifiable_field_does_not_block(self) -> None:
        """The requirement is met; a Russian verb nobody asked for cannot veto it."""
        scene = SemanticScene(
            scene_id="s", subject=["ocean"], action=["выглядит"], must_include=["ocean"], visual_priority="environment"
        )
        ranked = rank_candidates(scene, [_candidate("ok", "Ocean waves aerial view")])
        self.assertFalse(ranked[0]["rejected"], ranked[0]["reject_reason"])
        self.assertEqual(ranked[0]["semantic_match_status"], "unverified")
        self.assertIn("action", ranked[0]["undecidable_fields"])

    def test_a_landscape_frame_too_small_to_crop_is_refused(self) -> None:
        scene = SemanticScene(scene_id="s", visual_priority="environment")
        ranked = rank_candidates(scene, [_candidate("wide", "Antarctic valley from the air", width=1280, height=720)])
        self.assertTrue(ranked[0]["rejected"])
        self.assertIn("framing_unusable", ranked[0]["reject_reason"])
        self.assertEqual(ranked[0]["framing_check"]["effective_width"], 405)

    def test_a_landscape_frame_with_enough_pixels_passes(self) -> None:
        scene = SemanticScene(scene_id="s", visual_priority="environment")
        ranked = rank_candidates(scene, [_candidate("hd", "Antarctic valley from the air", width=1920, height=1080)])
        self.assertEqual(ranked[0]["framing_status"], "usable")
        self.assertFalse(ranked[0]["rejected"], ranked[0]["reject_reason"])

    def test_a_vertical_frame_passes_untouched(self) -> None:
        scene = SemanticScene(scene_id="s", visual_priority="environment")
        ranked = rank_candidates(scene, [_candidate("vertical", "Antarctic valley", width=1080, height=1920)])
        self.assertEqual(ranked[0]["framing_check"]["effective_width"], 1080)
        self.assertFalse(ranked[0]["rejected"])

    def test_the_framing_verdict_is_always_recorded(self) -> None:
        scene = SemanticScene(scene_id="s", visual_priority="environment")
        check = rank_candidates(scene, [_candidate("c", "Antarctic valley", width=1280, height=720)])[0]["framing_check"]
        self.assertEqual(check["source_width"], 1280)
        self.assertEqual(check["target_aspect_ratio"], "9:16")
        self.assertEqual(check["min_short_edge"], 540)


if __name__ == "__main__":
    unittest.main()
