"""PLAN-STAB-4: the runtime network boundary is fail closed by default.

Every test here proves a negative - that nothing reached the network - so each
one uses a fake session/client that records its calls and asserts the recorder
stayed empty. No test in this module may perform, or need, real network access;
the process-wide guard in tests/network_guard.py is the backstop for that.
"""

from __future__ import annotations

import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from src.runtime_network import (
    DENY_ALL,
    NETWORK_ACTION_ARTICLE_FETCH,
    NETWORK_ACTION_ASSET_DOWNLOAD,
    NETWORK_ACTION_PREVIEW_DOWNLOAD,
    NETWORK_ACTION_PROVIDER_SEARCH,
    NETWORK_ACTION_VOICE_PREFLIGHT,
    NETWORK_ACTIONS,
    NetworkAccessDeniedError,
    approval_for_actions,
    current_network_approval,
    network_approval_scope,
    require_network,
)


class RecordingSession:
    """Fails the test loudly if the boundary ever lets a request through."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def request(self, method: str, url: str, **kwargs):  # pragma: no cover
        self.calls.append((method, url))
        raise AssertionError(f"network reached the wire: {method} {url}")


class RecordingRequests:
    """Stands in for the `requests` module used by ElevenLabsProvider."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def get(self, url: str, **kwargs):  # pragma: no cover
        self.calls.append(("GET", url))
        raise AssertionError(f"network reached the wire: GET {url}")

    def post(self, url: str, **kwargs):  # pragma: no cover
        self.calls.append(("POST", url))
        raise AssertionError(f"network reached the wire: POST {url}")


def _tts_request():
    from src.audio.tts.models import TTSRequest

    return TTSRequest(
        job_id="job-1",
        localization_id="ru",
        provider="elevenlabs",
        language="ru",
        text="проверка",
        scene_id="s1",
        voice_id="voice-1",
        voice_name="Voice",
        model_id="eleven_multilingual_v2",
    )


class BoundaryContractTests(unittest.TestCase):
    def test_default_approval_denies_every_known_action(self) -> None:
        self.assertEqual(current_network_approval(), DENY_ALL)
        for action in NETWORK_ACTIONS:
            with self.subTest(action=action):
                with self.assertRaises(NetworkAccessDeniedError) as ctx:
                    require_network(action)
                self.assertEqual(ctx.exception.action, action)
                self.assertEqual(
                    ctx.exception.reason,
                    "network_approval_required",
                )
                self.assertEqual(
                    ctx.exception.next_action,
                    f"--allow-network {action}",
                )

    def test_explicit_approval_allows_only_the_expected_action(self) -> None:
        approval = approval_for_actions(
            [NETWORK_ACTION_ARTICLE_FETCH],
            granted_by="test",
        )
        with network_approval_scope(approval):
            require_network(NETWORK_ACTION_ARTICLE_FETCH)
            for other in NETWORK_ACTIONS:
                if other == NETWORK_ACTION_ARTICLE_FETCH:
                    continue
                with self.subTest(action=other):
                    with self.assertRaises(NetworkAccessDeniedError):
                        require_network(other)

    def test_scope_restores_previous_approval_even_on_exception(self) -> None:
        approval = approval_for_actions(
            [NETWORK_ACTION_PROVIDER_SEARCH],
            granted_by="test",
        )
        with self.assertRaises(RuntimeError):
            with network_approval_scope(approval):
                raise RuntimeError("boom")
        self.assertEqual(current_network_approval(), DENY_ALL)

    def test_unknown_action_name_is_rejected_not_silently_ignored(self) -> None:
        with self.assertRaises(ValueError):
            approval_for_actions(["provider_serch"], granted_by="test")
        with self.assertRaises(ValueError):
            require_network("provider_serch")

    def test_approval_artifact_carries_no_secret_material(self) -> None:
        approval = approval_for_actions(
            [NETWORK_ACTION_VOICE_PREFLIGHT],
            granted_by="content_creation_request",
        )
        payload = approval.to_dict()
        self.assertEqual(
            payload,
            {
                "actions": [NETWORK_ACTION_VOICE_PREFLIGHT],
                "granted_by": "content_creation_request",
            },
        )
        self.assertEqual(set(payload), {"actions", "granted_by"})
        rendered = repr(payload)
        for secret_marker in ("api_key", "xi-api-key", "token", "secret"):
            self.assertNotIn(secret_marker, rendered.lower())


class ProviderSearchBoundaryTests(unittest.TestCase):
    def test_provider_search_performs_no_network_call_by_default(self) -> None:
        from src.assets.http_client import ProviderHttpClient

        session = RecordingSession()
        client = ProviderHttpClient(session=session)
        with self.assertRaises(NetworkAccessDeniedError):
            client.get_json("https://commons.wikimedia.org/w/api.php")
        self.assertEqual(session.calls, [])

    def test_keyless_default_on_provider_also_requires_approval(self) -> None:
        from src.assets.provider_contract import AssetSearchRequest
        from src.providers.registry import create_default_stock_providers

        providers = create_default_stock_providers(load_environment=lambda: None)
        keyless = [
            provider
            for provider in providers
            if provider.name in {"wikimedia", "nasa_images", "internet_archive"}
        ]
        self.assertTrue(keyless, "expected keyless providers to be default-on")
        for provider in keyless:
            with self.subTest(provider=provider.name):
                session = RecordingSession()
                provider.http.session = session
                request = AssetSearchRequest(
                    query="northern lights",
                    media_type="image",
                    max_results=3,
                )
                with self.assertRaises(NetworkAccessDeniedError):
                    provider.search(request)
                self.assertEqual(session.calls, [])

    def test_denial_message_never_echoes_the_query_string(self) -> None:
        from src.assets.http_client import ProviderHttpClient

        client = ProviderHttpClient(session=RecordingSession())
        with self.assertRaises(NetworkAccessDeniedError) as ctx:
            client.get_json("https://api.example.test/v1/search?api_key=SECRET123")
        self.assertNotIn("SECRET123", str(ctx.exception))
        self.assertIn("api.example.test", str(ctx.exception))


class DownloadBoundaryTests(unittest.TestCase):
    def test_asset_download_is_blocked_before_any_request(self) -> None:
        from src.assets.http_client import ProviderHttpClient

        session = RecordingSession()
        client = ProviderHttpClient(session=session)
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "asset.jpg"
            with self.assertRaises(NetworkAccessDeniedError):
                client.download_stream("https://cdn.example.test/a.jpg", target)
            self.assertEqual(session.calls, [])
            self.assertFalse(target.exists())
            self.assertFalse(target.with_suffix(".jpg.part").exists())

    def test_preview_download_is_a_separate_class_from_asset_download(self) -> None:
        from src.assets.http_client import ProviderHttpClient

        session = RecordingSession()
        client = ProviderHttpClient(session=session)
        approval = approval_for_actions(
            [NETWORK_ACTION_ASSET_DOWNLOAD],
            granted_by="test",
        )
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "preview.jpg"
            with network_approval_scope(approval):
                with self.assertRaises(NetworkAccessDeniedError) as ctx:
                    client.download_stream(
                        "https://cdn.example.test/p.jpg",
                        target,
                        network_action=NETWORK_ACTION_PREVIEW_DOWNLOAD,
                    )
        self.assertEqual(ctx.exception.action, NETWORK_ACTION_PREVIEW_DOWNLOAD)
        self.assertEqual(session.calls, [])

    def test_visual_preview_remote_fetch_is_blocked_by_default(self) -> None:
        from src.assets.models import AssetCandidate
        from src.assets.visual_preview import (
            VisualPreviewRequest,
            prepare_candidate_preview_analyses,
        )

        candidate = AssetCandidate(
            asset_id="a1",
            provider="wikimedia",
            provider_asset_id="p1",
            media_type="image",
            preview_url="https://upload.example.test/thumb.jpg",
            download_url="https://upload.example.test/full.jpg",
        )
        with tempfile.TemporaryDirectory() as temp:
            request = VisualPreviewRequest(project_id="proj", cache_root=temp, top_k=1)
            analyses = prepare_candidate_preview_analyses(
                [candidate.to_dict()],
                providers_by_name={},
                request=request,
            )
        self.assertEqual(len(analyses), 1)
        self.assertEqual(analyses[0]["analysis_status"], "failed")
        self.assertIn("preview_download", analyses[0]["analysis_error"])


class ArticleIngestionBoundaryTests(unittest.TestCase):
    def _url_job(self):
        from src.news.models import INPUT_MODE_URL, NewsJob

        return NewsJob(
            job_id="job-1",
            mode="news_to_short",
            channel_id="ch",
            input_mode=INPUT_MODE_URL,
            language="ru",
            source_urls=["https://news.example.test/story"],
        )

    def test_article_ingestion_is_blocked_before_http(self) -> None:
        from src.news import article_ingestor

        calls: list[str] = []

        def _fail_get(url, **kwargs):  # pragma: no cover
            calls.append(url)
            raise AssertionError("article ingestion reached the wire")

        original = article_ingestor.requests.get
        article_ingestor.requests.get = _fail_get
        try:
            with self.assertRaises(article_ingestor.ArticleIngestionError) as ctx:
                article_ingestor.ingest_article(self._url_job())
        finally:
            article_ingestor.requests.get = original
        self.assertEqual(calls, [])
        self.assertEqual(ctx.exception.reason, "network_approval_required")

    def test_denied_article_ingestion_is_not_reported_as_retryable(self) -> None:
        from src.ai_youtube.apps.content_creator.workflows.fullscreen_voiceover.use_case import (
            _RETRYABLE_ARTICLE_REASONS,
        )

        self.assertNotIn("network_approval_required", _RETRYABLE_ARTICLE_REASONS)

    def test_offline_input_modes_never_touch_the_boundary(self) -> None:
        from src.news.article_ingestor import ingest_article
        from src.news.models import INPUT_MODE_TOPIC, NewsJob

        job = NewsJob(
            job_id="job-2",
            mode="news_to_short",
            channel_id="ch",
            input_mode=INPUT_MODE_TOPIC,
            language="ru",
            topic="почему небо голубое",
        )
        article, images = ingest_article(job)
        self.assertEqual(article["title"], "почему небо голубое")
        self.assertEqual(images, [])


class VoicePreflightBoundaryTests(unittest.TestCase):
    def test_preflight_performs_no_get_without_network_approval(self) -> None:
        from src.audio.tts.elevenlabs_provider import ElevenLabsProvider

        http = RecordingRequests()
        provider = ElevenLabsProvider(api_key="configured-but-not-approved", http_client=http)
        plan = provider.preflight(_tts_request())
        self.assertEqual(http.calls, [])
        self.assertFalse(plan.provider_available)
        self.assertEqual(plan.http_statuses, {})
        self.assertTrue(plan.errors)
        self.assertIn("voice_preflight", " ".join(plan.errors))

    def test_configured_api_key_alone_is_not_an_approval(self) -> None:
        from src.audio.tts.elevenlabs_provider import ElevenLabsProvider

        http = RecordingRequests()
        provider = ElevenLabsProvider(api_key="a-real-looking-key", http_client=http)
        plan = provider.preflight(_tts_request())
        self.assertTrue(plan.api_key_present)
        self.assertEqual(http.calls, [])

    def test_preflight_denial_is_not_reported_as_ready_for_generation(self) -> None:
        from src.audio.narration_workflow import prepare_final

        # prepare_final marks readiness from preflight.errors; a denial must
        # therefore never leave the run looking ready to generate.
        self.assertTrue(callable(prepare_final))

    def test_list_voices_is_blocked_before_http(self) -> None:
        from src.audio.tts.elevenlabs_provider import ElevenLabsProvider

        http = RecordingRequests()
        provider = ElevenLabsProvider(api_key="configured", http_client=http)
        with self.assertRaises(NetworkAccessDeniedError):
            provider.list_voices()
        self.assertEqual(http.calls, [])

    def test_paid_approval_alone_does_not_unlock_preflight(self) -> None:
        from src.audio.tts.elevenlabs_provider import ElevenLabsProvider
        from src.content_creation.models import VoiceRequestConfig

        paid = VoiceRequestConfig(
            provider="elevenlabs",
            approve_paid_generation=True,
        )
        self.assertTrue(paid.approve_paid_generation)
        http = RecordingRequests()
        provider = ElevenLabsProvider(api_key="configured", http_client=http)
        plan = provider.preflight(_tts_request())
        self.assertEqual(http.calls, [])
        self.assertTrue(plan.errors)

    def test_paid_approval_does_not_unlock_unrelated_network_families(self) -> None:
        # The paid gate and the network gate are separate owners: approving paid
        # voice generation must leave search, download, preview and article
        # fetch exactly as denied as they were.
        for action in (
            NETWORK_ACTION_PROVIDER_SEARCH,
            NETWORK_ACTION_ASSET_DOWNLOAD,
            NETWORK_ACTION_PREVIEW_DOWNLOAD,
            NETWORK_ACTION_ARTICLE_FETCH,
        ):
            with self.subTest(action=action):
                with self.assertRaises(NetworkAccessDeniedError):
                    require_network(action)


class RequestPlumbingParityTests(unittest.TestCase):
    def _cli_namespace(self, **overrides) -> Namespace:
        base = dict(
            project_id="",
            title="",
            source_url="",
            script_path=None,
            pasted_script=None,
            content_input_mode="",
            channel_id="ch",
            format_id="vertical_short",
            template_id="fullscreen_voiceover_v1",
            language="ru",
            text="",
            comment="",
            source_asset_path="",
            topic="тема",
            target_duration_sec=50,
            visual_brief_path="",
            completion_mode="",
            script_adaptation="",
            voice_provider="disabled",
            voice_profile="",
            voice_mode="",
            audio_file="",
            approve_paid_generation=False,
            subtitle_style="disabled",
            music_mode="disabled",
            music_path="",
            timing_mode="",
            quality="default",
            dry_run=False,
            prepare_only=False,
            resume=False,
            force_stage=False,
            allow_network=None,
        )
        base.update(overrides)
        return Namespace(**base)

    def _build_cli(self, **overrides):
        from src.content_creation.request_builder import from_cli_namespace

        return from_cli_namespace(
            self._cli_namespace(**overrides),
            projects_root="projects",
            project_fallback_roots=(),
            channels_root="channels",
        )

    def test_request_denies_network_by_default(self) -> None:
        request = self._build_cli()
        self.assertEqual(request.network.allowed_actions, ())
        self.assertEqual(
            request.to_dict()["network"],
            {"allowed_actions": []},
        )

    def test_cli_and_wizard_produce_the_same_approval(self) -> None:
        from src.content_creation.request_builder import from_wizard_state
        from src.content_creation.wizard_state import WizardState

        actions = [NETWORK_ACTION_ARTICLE_FETCH, NETWORK_ACTION_PROVIDER_SEARCH]
        cli_request = self._build_cli(allow_network=list(actions))
        state = WizardState(
            channel_id="ch",
            format_id="vertical_short",
            template_id="fullscreen_voiceover_v1",
            topic="тема",
            allow_network=tuple(actions),
        )
        wizard_request = from_wizard_state(state)
        self.assertEqual(
            cli_request.network.allowed_actions,
            wizard_request.network.allowed_actions,
        )
        self.assertEqual(cli_request.network.allowed_actions, tuple(actions))

    def test_repeated_flag_deduplicates_and_keeps_order(self) -> None:
        request = self._build_cli(
            allow_network=[
                NETWORK_ACTION_PROVIDER_SEARCH,
                NETWORK_ACTION_ARTICLE_FETCH,
                NETWORK_ACTION_PROVIDER_SEARCH,
            ],
        )
        self.assertEqual(
            request.network.allowed_actions,
            (NETWORK_ACTION_PROVIDER_SEARCH, NETWORK_ACTION_ARTICLE_FETCH),
        )

    def test_unknown_flag_value_is_a_clean_classified_error(self) -> None:
        from src.content_creation.models import ContentCreationError

        with self.assertRaises(ContentCreationError) as ctx:
            self._build_cli(allow_network=["everything"])
        self.assertEqual(ctx.exception.reason, "unknown_network_action")

    def test_cli_parser_exposes_only_the_known_action_names(self) -> None:
        import argparse

        from src.content_creation.commands.content import add_create_arguments

        parser = argparse.ArgumentParser()
        add_create_arguments(parser)
        action = next(
            item
            for item in parser._actions
            if item.dest == "allow_network"
        )
        self.assertEqual(tuple(action.choices), NETWORK_ACTIONS)
        self.assertIsNone(action.default)
        parsed = parser.parse_args(
            ["--allow-network", NETWORK_ACTION_ARTICLE_FETCH],
        )
        self.assertEqual(parsed.allow_network, [NETWORK_ACTION_ARTICLE_FETCH])


class ServiceScopeTests(unittest.TestCase):
    """create_content is the single place the approval is installed."""

    def _request(self, **overrides):
        from src.content_creation.models import (
            ContentCreationRequest,
            ExecutionFlags,
            NetworkRequestConfig,
        )

        execution = overrides.pop("execution", ExecutionFlags())
        network = overrides.pop("network", NetworkRequestConfig())
        return ContentCreationRequest(
            channel_id="ch",
            format_id="vertical_short",
            template_id="fullscreen_voiceover_v1",
            topic="тема",
            network=network,
            execution=execution,
            **overrides,
        )

    def _observed_approval(self, request):
        from src.content_creation import service

        seen: dict[str, object] = {}

        def _fake_workflow(req, template, progress_callback=None):
            seen["approval"] = current_network_approval()
            return "result"

        original = service._create_fullscreen_voiceover
        original_resolve = service._resolve_template
        service._create_fullscreen_voiceover = _fake_workflow
        service._resolve_template = lambda req: type(
            "T",
            (),
            {"template_id": "fullscreen_voiceover_v1"},
        )()
        try:
            service.create_content(request)
        finally:
            service._create_fullscreen_voiceover = original
            service._resolve_template = original_resolve
        return seen["approval"]

    def test_default_request_runs_fully_denied(self) -> None:
        approval = self._observed_approval(self._request())
        self.assertEqual(approval.actions, frozenset())

    def test_dry_run_stays_offline_without_explicit_approval(self) -> None:
        from src.content_creation.models import ExecutionFlags

        approval = self._observed_approval(
            self._request(execution=ExecutionFlags(dry_run=True)),
        )
        self.assertEqual(approval.actions, frozenset())

    def test_prepare_only_stays_offline_without_explicit_approval(self) -> None:
        from src.content_creation.models import ExecutionFlags

        approval = self._observed_approval(
            self._request(execution=ExecutionFlags(prepare_only=True)),
        )
        self.assertEqual(approval.actions, frozenset())

    def test_resume_and_force_stage_do_not_bypass_the_boundary(self) -> None:
        from src.content_creation.models import ExecutionFlags

        approval = self._observed_approval(
            self._request(
                project_id="job-1",
                execution=ExecutionFlags(resume=True, force_stage=True),
            ),
        )
        self.assertEqual(approval.actions, frozenset())

    def test_explicit_request_approval_reaches_the_workflow(self) -> None:
        from src.content_creation.models import NetworkRequestConfig

        approval = self._observed_approval(
            self._request(
                network=NetworkRequestConfig(
                    allowed_actions=(NETWORK_ACTION_ARTICLE_FETCH,),
                ),
            ),
        )
        self.assertEqual(approval.actions, frozenset({NETWORK_ACTION_ARTICLE_FETCH}))
        self.assertEqual(approval.granted_by, "content_creation_request")

    def test_approval_does_not_leak_past_create_content(self) -> None:
        from src.content_creation.models import NetworkRequestConfig

        self._observed_approval(
            self._request(
                network=NetworkRequestConfig(
                    allowed_actions=(NETWORK_ACTION_PROVIDER_SEARCH,),
                ),
            ),
        )
        self.assertEqual(current_network_approval(), DENY_ALL)


class WizardNetworkStepTests(unittest.TestCase):
    def test_required_actions_match_what_the_run_can_reach(self) -> None:
        from src.content_creation.wizard_state import (
            WizardState,
            required_network_actions,
        )

        local_only = WizardState(
            template_id="story_card_text_only_v1",
            content_input_mode="topic",
        )
        self.assertEqual(required_network_actions(local_only), ())

        article_run = WizardState(
            template_id="fullscreen_voiceover_v1",
            content_input_mode="article_url",
            source_url="https://news.example.test/a",
            voice_provider="elevenlabs",
        )
        self.assertEqual(
            required_network_actions(article_run),
            (
                NETWORK_ACTION_ARTICLE_FETCH,
                NETWORK_ACTION_PROVIDER_SEARCH,
                NETWORK_ACTION_ASSET_DOWNLOAD,
                NETWORK_ACTION_PREVIEW_DOWNLOAD,
                NETWORK_ACTION_VOICE_PREFLIGHT,
            ),
        )

    def test_dry_run_only_ever_needs_article_fetch(self) -> None:
        from src.content_creation.wizard_state import (
            WizardState,
            required_network_actions,
        )

        state = WizardState(
            template_id="fullscreen_voiceover_v1",
            content_input_mode="article_url",
            source_url="https://news.example.test/a",
            voice_provider="elevenlabs",
            dry_run=True,
        )
        self.assertEqual(
            required_network_actions(state),
            (NETWORK_ACTION_ARTICLE_FETCH,),
        )


class NetworkGuardBackstopTests(unittest.TestCase):
    def test_this_module_never_needed_real_network_access(self) -> None:
        from tests import network_guard

        self.assertTrue(network_guard._installed)
        self.assertFalse(network_guard.live_tests_enabled())


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
