from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ROOT = REPO_ROOT / "schemas"
SCHEMA_NAMES = {
    "job",
    "project",
    "stage-state",
    "assets",
    "voice",
    "evidence",
    "render",
    "export",
}


def _load_schema(name: str) -> dict[str, Any]:
    return json.loads((SCHEMA_ROOT / f"{name}.schema.json").read_text(encoding="utf-8"))


class ArtifactSchemaContractTests(unittest.TestCase):
    def assert_matches_top_level_schema(
        self,
        schema_name: str,
        payload: dict[str, Any],
    ) -> None:
        schema = _load_schema(schema_name)
        self.assertEqual(schema["type"], "object")
        for key in schema.get("required", []):
            self.assertIn(key, payload, f"{schema_name}: missing required key {key!r}")
        for key, value in payload.items():
            declaration = schema.get("properties", {}).get(key)
            if not declaration or "type" not in declaration:
                continue
            expected = declaration["type"]
            expected_types = expected if isinstance(expected, list) else [expected]
            self.assertTrue(
                any(_is_json_type(value, item) for item in expected_types),
                f"{schema_name}.{key}: {type(value).__name__} does not match {expected_types}",
            )

    def test_schema_catalog_is_complete_and_parseable(self) -> None:
        discovered = {
            path.name.removesuffix(".schema.json")
            for path in SCHEMA_ROOT.glob("*.schema.json")
        }
        self.assertEqual(discovered, SCHEMA_NAMES)
        for name in sorted(SCHEMA_NAMES):
            schema = _load_schema(name)
            self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
            self.assertTrue(schema["$id"].endswith(".schema.json"))
            self.assertIsInstance(schema.get("required"), list)

    def test_job_and_stage_state_match_their_contracts(self) -> None:
        from src.news.models import NewsJob

        job = NewsJob.create(
            channel_id="nature_science_news_ru",
            input_mode="topic",
            topic="Characterization",
            now="2026-07-28T00:00:00+00:00",
        )
        payload = job.to_dict()

        self.assert_matches_top_level_schema("job", payload)
        self.assertEqual(payload["mode"], "news_to_short")
        self.assertGreater(len(payload["stages"]), 0)
        for stage in payload["stages"].values():
            self.assert_matches_top_level_schema("stage-state", stage)

    def test_project_manifest_matches_its_contract(self) -> None:
        from src.project_foundation.models import ProjectManifest

        payload = ProjectManifest(
            project_id="contract-project",
            channel_id="nature_pulse",
            application_id="content_creator",
            format_id="vertical_short",
            template_id="story_card_text_only_v1",
        ).to_dict()

        self.assert_matches_top_level_schema("project", payload)

    def test_assets_manifest_matches_its_contract_offline(self) -> None:
        from src.news.asset_manager import build_assets_manifest

        payload = build_assets_manifest(
            visual_plan={"language": "ru", "scenes": []},
            user_assets=[],
            media_index={"version": 1, "items": []},
            providers=[],
            dry_run=True,
        )

        self.assert_matches_top_level_schema("assets", payload)
        self.assertEqual(payload["provider_order"], ["user_assets", "local_library"])

    def test_voice_manifest_matches_its_contract_without_a_paid_call(self) -> None:
        from src.audio.narration_models import build_narration_request_from_scenes
        from src.audio.tts.models import VoiceProfile
        from src.audio.voice_manifest import build_voice_manifest
        from src.audio.voice_policy import VoicePolicy

        request = build_narration_request_from_scenes(
            project_id="contract-project",
            job_id="contract-job",
            channel_id="nature_science_news_ru",
            localization_id="ru",
            language="ru",
            format_id="vertical_short",
            template_id="fullscreen_voiceover_v1",
            voice_profile=VoiceProfile(
                profile_id="ru_dom",
                display_name="Dom",
                provider="elevenlabs",
                voice_id="voice",
                model_id="model",
                language="ru",
            ),
            policy=VoicePolicy(enabled=True, output_mode="scene_audio"),
            scenes=[{"scene_id": "scene_001", "text": "Текст."}],
            full_text="Текст.",
            output_root="unused",
        )
        payload = build_voice_manifest(request, status="awaiting_voice_approval")

        self.assert_matches_top_level_schema("voice", payload)
        self.assertFalse(payload["paid_call_performed"])
        self.assertIsNone(payload["approval"])

    def test_evidence_record_matches_its_contract(self) -> None:
        from src.project_foundation.models import EvidenceRecord

        payload = EvidenceRecord(evidence_id="evidence-001").to_dict()

        self.assert_matches_top_level_schema("evidence", payload)

    def test_render_contract_accepts_blocked_and_completed_shapes(self) -> None:
        blocked = {
            "status": "blocked",
            "reason": "quality_check_requires_review",
            "output_path": "",
            "completion_mode": "strict",
        }
        completed = {
            "status": "completed",
            "render_status": "completed",
            "output_path": "output/master_1080x1920.mp4",
            "outputs": {"master_1080x1920": "output/master_1080x1920.mp4"},
            "scene_count": 1,
            "segment_count": 1,
            "segments": [{}],
            "resolution": {"width": 1080, "height": 1920},
            "renderer": "news_to_short_final_renderer_v2",
        }

        self.assert_matches_top_level_schema("render", blocked)
        self.assert_matches_top_level_schema("render", completed)

    def test_export_writer_matches_its_contract(self) -> None:
        from src.news.exporter import export_localization

        with tempfile.TemporaryDirectory() as tmp:
            result = export_localization(
                project_root=tmp,
                language="ru",
                job={
                    "job_id": "contract-job",
                    "mode": "news_to_short",
                    "channel_id": "nature_science_news_ru",
                },
                script={"description": "Contract description"},
                research={"claims": []},
                assets_manifest={"scenes": [], "provider_errors": []},
                quality_report={"status": "passed"},
            )
            payload = json.loads(Path(result["manifest_path"]).read_text(encoding="utf-8"))

        self.assert_matches_top_level_schema("export", payload)


def _is_json_type(value: Any, expected: str) -> bool:
    if expected == "null":
        return value is None
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, int | float) and not isinstance(value, bool)
    if expected == "string":
        return isinstance(value, str)
    if expected == "array":
        return isinstance(value, list)
    if expected == "object":
        return isinstance(value, dict)
    return False


if __name__ == "__main__":
    unittest.main()
