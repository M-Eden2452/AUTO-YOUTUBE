"""Regression coverage for the active Content Creator input/query path.

The query assertions are the post-fix contract for PLAN-9B-1: prepared English
evidence reaches providers, unsafe source-language text stays out, and persisted
query plans explain both dispatched and fail-closed outcomes. The separate
legacy-template assertion remains pre-fix characterization for PLAN-9B-4.

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
from src.assets.query_adapter import (
    SOURCE_BRIEF_FIELDS,
    SOURCE_EXPLICIT,
    SOURCE_GLOSSARY,
    SOURCE_SAME_LANGUAGE,
)
from src.content_creation.models import (
    ContentCreationRequest,
    ExecutionFlags,
    VoiceRequestConfig,
)
from src.content_creation.service import create_content
from src.news.asset_manager import build_assets_manifest
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
        # Raw topics are not translations. Two have no safe provider-ready evidence;
        # the third contains the seed's unambiguous environment concept ``desert``.
        # Counts remain measurements, not invariants.
        cases = (
            {
                "topic": "Почему вороны запоминают человеческие лица",
                "required_terms": set(),
                "forbidden_terms": {"ice", "station", "nature"},
            },
            {
                "topic": "Солнечная электростанция и аккумуляторное хранилище",
                "required_terms": set(),
                "forbidden_terms": {"ice", "station", "nature"},
            },
            {
                "topic": "Строительство большого канала через пустыню",
                "required_terms": {"desert"},
                "forbidden_terms": {"ice", "station", "nature"},
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
                request_queries = {request.query for request in requests}
                request_words = {
                    word.casefold()
                    for query in request_queries
                    for word in query.split()
                }

                self.assertTrue(
                    all(isinstance(request, AssetSearchRequest) for request in requests)
                )
                self.assertTrue(
                    set(case["forbidden_terms"]).isdisjoint(request_words)
                )
                self.assertTrue(
                    all(
                        not any("Ѐ" <= char <= "ӿ" for char in query)
                        for query in request_queries
                    )
                )
                if case["required_terms"]:
                    self.assertTrue(
                        all(
                            set(case["required_terms"]).intersection(
                                query.casefold().split()
                            )
                            for query in request_queries
                        )
                    )
                    self.assertEqual(
                        {
                            provider.name
                            for provider in providers
                            if provider.search_requests
                        },
                        set(_PROVIDER_IDS),
                    )
                else:
                    self.assertEqual(requests, [])

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
                self.assertGreater(len(skipped), 0)
                self.assertEqual(
                    {attempt["provider"] for attempt in skipped},
                    set(_PROVIDER_IDS),
                )
                if case["required_terms"]:
                    self.assertEqual(
                        {attempt["query_source"] for attempt in completed},
                        {SOURCE_GLOSSARY},
                    )
                else:
                    self.assertEqual(completed, [])

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
                persisted_query_strings = {
                    query["query"] for query in ok_queries
                }
                persisted_words = {
                    word.casefold()
                    for query in persisted_query_strings
                    for word in query.split()
                }
                self.assertTrue(request_queries.issubset(persisted_query_strings))
                self.assertTrue(
                    set(case["forbidden_terms"]).isdisjoint(persisted_words)
                )
                self.assertTrue(
                    set(case["required_terms"]).issubset(persisted_words)
                )
                self.assertGreater(len(translation_required), 0)
                self.assertEqual(
                    {query["source"] for query in translation_required},
                    {SOURCE_BRIEF_FIELDS},
                )
                self.assertEqual(
                    sum(len(plan["untranslatable_providers"]) for plan in query_plans),
                    len(translation_required),
                )

    def test_prepared_evidence_reaches_fake_providers_with_provenance(self) -> None:
        explicit_queries = {
            "corvid bird recognizing human face",
            "crow watching person outdoors",
        }
        alternative_queries = {
            "solar power plant battery storage",
            "solar farm electrical grid",
        }
        providers = [_RecordingStockProvider(name) for name in _PROVIDER_IDS]
        network_attempts_before = list(blocked_attempts)
        manifest = build_assets_manifest(
            visual_plan={
                "intent_language": "ru",
                "scenes": [
                    {
                        "scene_id": "scene_001",
                        "visual_type": "video",
                        "primary_query": "ворона узнаёт лицо",
                        "alternative_queries": [],
                        "visual_brief": {
                            "subject": "corvid bird",
                            "action": "recognizing human face",
                            "place": "urban park",
                            "provider_queries": {
                                "default": [
                                    *sorted(explicit_queries),
                                    "  CORVID   BIRD recognizing human face  ",
                                    "ворона узнаёт лицо",
                                ]
                            },
                        },
                    },
                    {
                        "scene_id": "scene_002",
                        "visual_type": "video",
                        "primary_query": "солнечная электростанция",
                        "alternative_queries": [
                            *sorted(alternative_queries),
                            "nature science wildlife observation",
                        ],
                        "visual_intents": [
                            {
                                "kind": "primary",
                                "terms": ["солнечная", "электростанция"],
                                "language": "ru",
                                "fallback_level": 1,
                                "requires_translation": True,
                            },
                            {
                                "kind": "alternative",
                                "terms": ["solar power plant", "battery storage"],
                                "language": "en",
                                "fallback_level": 2,
                                "requires_translation": False,
                            },
                            {
                                "kind": "context_fallback",
                                "terms": ["solar farm", "electrical grid"],
                                "language": "en",
                                "fallback_level": 3,
                                "requires_translation": False,
                            },
                        ],
                    },
                ],
            },
            user_assets=[],
            media_index={"version": 1, "items": []},
            providers=providers,
            dry_run=False,
            project_id="query-foundation-fixture",
        )
        self.assertEqual(blocked_attempts, network_attempts_before)

        for provider in providers:
            sent = {request.query for request in provider.search_requests}
            self.assertTrue(explicit_queries.issubset(sent))
            self.assertTrue(alternative_queries.issubset(sent))
            self.assertNotIn("nature science wildlife observation", sent)
            self.assertTrue(
                all(not any("Ѐ" <= char <= "ӿ" for char in query) for query in sent)
            )

        persisted = [
            query
            for scene in manifest["scenes"]
            for query in scene["query_plan"]["queries"]
            if query["status"] == "ok"
        ]
        by_text = {
            query["query"]: query["source"]
            for query in persisted
            if query["query"] in explicit_queries | alternative_queries
        }
        self.assertEqual(
            {by_text[query] for query in explicit_queries},
            {SOURCE_EXPLICIT},
        )
        self.assertEqual(
            {by_text[query] for query in alternative_queries},
            {SOURCE_SAME_LANGUAGE},
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
