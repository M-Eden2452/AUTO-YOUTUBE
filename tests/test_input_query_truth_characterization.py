"""Pre-fix characterization for the active Content Creator input/query path.

These assertions intentionally record current defects before PLAN-9B-1.  The
wrong glossary matches and the fail-closed skips are expected to change when
the provider-language foundation is corrected; the test must then be reviewed,
not preserved as desired product behaviour.

The tests run the canonical ``create_content`` application entrypoint in-process.
Only the existing provider-factory seam is replaced: production still builds the
visual plan, ``ProviderQuery`` values, canonical ``AssetSearchRequest`` objects,
and the persisted ``assets_manifest.json``.  The package-wide network guard stays
active throughout.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

from src.assets.models import ProviderCapabilities
from src.assets.provider_contract import (
    AssetSearchRequest,
    ProviderHealth,
)
from src.content_creation.models import (
    ContentCreationRequest,
    ExecutionFlags,
    VoiceRequestConfig,
)
from src.content_creation.service import create_content
from tests.network_guard import blocked_attempts


_PROVIDER_IDS = (
    "wikimedia",
    "nasa_images",
    "internet_archive",
    "pexels",
    "pixabay",
)


class _RecordingStockProvider:
    """Canonical offline provider that records exactly what production sends."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.search_requests: list[AssetSearchRequest] = []

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            provider=self.name,
            media_types=["video", "image"],
            supports_preview=False,
            supports_download=False,
            query_languages=["en"],
        )

    def search(self, request: AssetSearchRequest) -> list[Any]:
        if not isinstance(request, AssetSearchRequest):
            raise AssertionError(
                f"{self.name} received {type(request)!r}, not AssetSearchRequest"
            )
        self.search_requests.append(request)
        return []

    def get_preview(self, candidate: Any) -> Any:
        raise AssertionError("An empty offline search must not request previews")

    def resolve_license(self, candidate: Any) -> Any:
        raise AssertionError("An empty offline search must not resolve licenses")

    def download(self, candidate: Any, destination: Path, context: Any) -> Any:
        raise AssertionError("An empty offline search must not download")

    def health_check(self) -> ProviderHealth:
        return ProviderHealth(
            provider=self.name,
            configured=True,
            status="ready",
        )


class InputQueryTruthCharacterizationTests(unittest.TestCase):
    def _run_topic(self, topic: str) -> dict[str, Any]:
        providers = [_RecordingStockProvider(name) for name in _PROVIDER_IDS]
        network_attempts_before = list(blocked_attempts)

        with tempfile.TemporaryDirectory() as tmp:
            request = ContentCreationRequest(
                channel_id="nature_science_news_ru",
                template_id="fullscreen_voiceover_v1",
                language="ru",
                content_input_mode="topic",
                topic=topic,
                voice=VoiceRequestConfig(provider="disabled"),
                execution=ExecutionFlags(prepare_only=True),
                project_overrides={"projects_root": tmp},
            )
            with patch(
                "src.news.asset_manager.create_default_asset_providers",
                return_value=providers,
            ):
                result = create_content(request)

            project_root = Path(result.project_root)
            manifest_path = project_root / "assets" / "assets_manifest.json"
            script_path = (
                project_root
                / "localizations"
                / "ru"
                / "script"
                / "script.json"
            )
            self.assertTrue(manifest_path.is_file())
            self.assertTrue(script_path.is_file())
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            script = json.loads(script_path.read_text(encoding="utf-8"))

        self.assertEqual(blocked_attempts, network_attempts_before)
        return {
            "manifest": manifest,
            "providers": providers,
            "script": script,
        }

    def test_current_provider_dispatch_and_persisted_query_plan(self) -> None:
        # These are the three controlled offline inputs from the deep-dive.  Exact
        # counts and wrong strings are pre-fix characterization for PLAN-9B-1.
        cases = (
            {
                "topic": "Почему вороны запоминают человеческие лица",
                "search_calls": 10,
                "query_plan_ok": 5,
                "skipped": 25,
                "skipped_scenes": 5,
                "queries": {"ice researchers"},
            },
            {
                "topic": "Солнечная электростанция и аккумуляторное хранилище",
                "search_calls": 50,
                "query_plan_ok": 25,
                "skipped": 5,
                "skipped_scenes": 1,
                "queries": {"station", "ice researchers station"},
            },
            {
                "topic": "Строительство большого канала через пустыню",
                "search_calls": 10,
                "query_plan_ok": 5,
                "skipped": 25,
                "skipped_scenes": 5,
                "queries": {"ice researchers"},
            },
        )

        for case in cases:
            with self.subTest(topic=case["topic"]):
                observed = self._run_topic(str(case["topic"]))
                manifest = observed["manifest"]
                providers = observed["providers"]
                requests = [
                    request
                    for provider in providers
                    for request in provider.search_requests
                ]

                self.assertEqual(len(requests), case["search_calls"])
                self.assertTrue(
                    all(isinstance(request, AssetSearchRequest) for request in requests)
                )
                self.assertEqual({request.query for request in requests}, case["queries"])
                self.assertEqual(
                    {provider.name for provider in providers if provider.search_requests},
                    set(_PROVIDER_IDS),
                )
                self.assertEqual(
                    {len(provider.search_requests) for provider in providers},
                    {int(case["search_calls"]) // len(_PROVIDER_IDS)},
                )

                attempts = manifest["provider_attempts"]
                skipped = [
                    attempt
                    for attempt in attempts
                    if attempt.get("status") == "skipped"
                    and attempt.get("reason") == "query_translation_required"
                ]
                completed = [
                    attempt
                    for attempt in attempts
                    if attempt.get("status") == "completed"
                ]
                self.assertEqual(len(skipped), case["skipped"])
                self.assertEqual(
                    len({attempt["scene_id"] for attempt in skipped}),
                    case["skipped_scenes"],
                )
                self.assertEqual(
                    {attempt["provider"] for attempt in skipped},
                    set(_PROVIDER_IDS),
                )
                self.assertEqual(len(completed), case["query_plan_ok"])
                self.assertEqual(
                    {attempt["query_source"] for attempt in completed},
                    {"deterministic_glossary"},
                )

                # Read the minimal meaningful persisted subset from the real JSON,
                # rather than snapshotting the unrelated manifest fields.
                query_plans = [scene["query_plan"] for scene in manifest["scenes"]]
                persisted_queries = [
                    query
                    for plan in query_plans
                    for query in plan["queries"]
                ]
                ok_queries = [
                    query for query in persisted_queries if query["status"] == "ok"
                ]
                translation_required = [
                    query
                    for query in persisted_queries
                    if query["status"] == "query_translation_required"
                ]
                self.assertEqual(len(persisted_queries), 30)
                self.assertEqual(len(ok_queries), case["query_plan_ok"])
                self.assertEqual(len(translation_required), case["skipped"])
                self.assertEqual(
                    {query["query"] for query in ok_queries},
                    case["queries"],
                )
                self.assertEqual(
                    {query["source"] for query in ok_queries},
                    {"deterministic_glossary"},
                )
                self.assertEqual(
                    {query["source"] for query in translation_required},
                    {"visual_brief_fields"},
                )
                self.assertEqual(
                    sum(len(plan["untranslatable_providers"]) for plan in query_plans),
                    case["skipped"],
                )

    def test_topic_only_thin_input_currently_passes_legacy_template(self) -> None:
        observed = self._run_topic(
            "Почему вороны запоминают человеческие лица"
        )
        script = observed["script"]

        self.assertEqual(script["script_provider"], "legacy_template")
        self.assertEqual(script["script_validation"]["status"], "passed")
        self.assertTrue(script["script_validation"]["valid"])
        self.assertEqual(
            script["script_metadata"]["fallback_provider"],
            "legacy_template",
        )
        self.assertEqual(
            script["script_metadata"]["fallback_reason"],
            "insufficient_source_material",
        )
        self.assertTrue(
            any(
                "insufficient_source_material" in warning
                for warning in script["script_warnings"]
            )
        )


if __name__ == "__main__":
    unittest.main()
