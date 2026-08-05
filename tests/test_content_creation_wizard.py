from __future__ import annotations

import io
import contextlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.content_creation.models import ContentCreationError, ContentCreationResult
from src.content_creation.wizard import (
    CANCEL,
    PlainAdapter,
    QuestionaryAdapter,
    _default_adapter,
    _status_icon_key,
    choose_icon_set,
    run_wizard,
)


class ScriptedAdapter:
    """Mock prompt adapter for tests: feeds canned answers, never touches a real
    terminal or keyboard, and records every select() call for assertions."""

    def __init__(
        self,
        answers: list,
        *,
        auto_title: bool = True,
        auto_network: bool = True,
    ) -> None:
        self._answers = list(answers)
        self._auto_title = auto_title
        self._auto_network = auto_network
        self.select_calls: list[tuple[str, list[tuple[str, str]]]] = []
        self.text_calls: list[tuple[str, str]] = []
        self.confirm_calls: list[str] = []

    def _next(self):
        if not self._answers:
            raise AssertionError("ScriptedAdapter ran out of canned answers")
        return self._answers.pop(0)

    def select(self, message: str, choices: list[tuple[str, str]], *, allow_cancel: bool = True) -> str:
        self.select_calls.append((message, list(choices)))
        return self._next()

    def text(self, message: str, default: str = "") -> str:
        self.text_calls.append((message, default))
        if self._auto_title and "Название ролика" in message:
            # The title question is pre-filled from the topic/script, so accepting the
            # suggestion is one Enter press. Modelling that here keeps every existing
            # canned script valid; tests that care about a custom title pass
            # auto_title=False and script the answer themselves.
            return default
        return self._next()

    def confirm(self, message: str, default: bool = False) -> bool:
        self.confirm_calls.append(message)
        if self._auto_network and "сетевые действия" in message:
            # PLAN-STAB-4 added an explicit network step before creation. Like the
            # pre-filled title above, answering it here keeps every existing canned
            # script valid; tests that care about the answer pass auto_network=False
            # and script it themselves.
            return True
        return self._next()

    @property
    def exhausted(self) -> bool:
        return not self._answers


class FakeCreateFn:
    """Records requests and returns/raises canned results in order - stands in
    for src.content_creation.service.create_content without touching network,
    ElevenLabs, or real projects/."""

    def __init__(self, outcomes: list) -> None:
        self._outcomes = list(outcomes)
        self.requests: list = []

    def __call__(self, request, progress_callback=None):
        self.requests.append(request)
        outcome = self._outcomes.pop(0) if self._outcomes else ContentCreationResult(
            status="completed", project_id="p", project_root="/tmp/p"
        )
        if progress_callback:
            progress_callback("stage_a", "running")
            progress_callback("stage_a", "completed")
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


# The wizard now opens with "new project / continue an unfinished one" (Stage B3);
# every scripted run below starts a new one.
START_NEW = "new"


def _story_card_answers(tail: list) -> list:
    return [START_NEW, "vertical_short", "story_card_text_only_v1", "nature_pulse", "ru", *tail]


def _fullscreen_answers(tail: list) -> list:
    # Prompt order after start action/format/template/channel/language:
    #   content-input (+ its text), title (auto-accepted by ScriptedAdapter), target
    #   duration, voice provider (+ profile or WAV path), subtitles, music (+ path
    #   when local_file), dry_run, edit menu.
    # Output mode and timing mode are NOT asked - they come from the template's
    # audio policy (see capabilities.describe_template_capabilities).
    return [START_NEW, "vertical_short", "fullscreen_voiceover_v1", "nature_science_news_ru", "ru", *tail]


class StoryCardWizardTests(unittest.TestCase):
    def test_topic_style_prompts_are_not_shown(self) -> None:
        # Story Card asks only for card text + local asset, never a "content
        # input mode" chooser (topic/article_url/pasted_script/script_file).
        adapter = ScriptedAdapter(
            _story_card_answers(
                [
                    "Кошка слышит звуки, которые человек не различает.",  # card text
                    "projects/story_card_owl_test/final_test.mp4",  # source asset
                    True,  # dry_run
                    "run",  # edit menu
                ]
            )
        )
        result = run_wizard(adapter=adapter, create_fn=FakeCreateFn([]))
        self.assertIsNotNone(result)
        messages = [message for message, _ in adapter.select_calls]
        self.assertFalse(any("Источник сценария" in m for m in messages))
        self.assertFalse(any("озвучки" in m for m in messages))
        self.assertFalse(any("Субтитры" in m for m in messages))

    def test_does_not_ask_voice_or_subtitles(self) -> None:
        adapter = ScriptedAdapter(_story_card_answers(["текст", "asset.mp4", True, "run"]))
        create_fn = FakeCreateFn([])
        run_wizard(adapter=adapter, create_fn=create_fn)
        request = create_fn.requests[0]
        self.assertEqual(request.voice.provider, "disabled")
        self.assertEqual(request.subtitles.style, "disabled")
        self.assertEqual(request.music.mode, "disabled")

    def test_cancel_at_format_returns_none(self) -> None:
        adapter = ScriptedAdapter([CANCEL])
        self.assertIsNone(run_wizard(adapter=adapter, create_fn=FakeCreateFn([])))


class FullscreenTopicModeTests(unittest.TestCase):
    def test_topic_mode_builds_expected_request(self) -> None:
        adapter = ScriptedAdapter(
            _fullscreen_answers(
                [
                    "topic",  # input mode
                    "Почему кошки мурчат",  # topic text
                    "60",  # target duration
                    "disabled",  # voice provider
                    "disabled",  # subtitles
                    "disabled",  # music
                    True,  # dry_run
                    "run",  # edit menu
                ]
            )
        )
        create_fn = FakeCreateFn([])
        result = run_wizard(adapter=adapter, create_fn=create_fn)
        self.assertIsNotNone(result)
        request = create_fn.requests[0]
        self.assertEqual(request.content_input_mode, "topic")
        self.assertEqual(request.topic, "Почему кошки мурчат")
        self.assertEqual(request.source_url, "")


class TargetDurationTests(unittest.TestCase):
    def test_preset_choice_saved_on_request(self) -> None:
        adapter = ScriptedAdapter(
            _fullscreen_answers(["topic", "Тема", "45", "disabled", "disabled", "disabled", True, "run"])
        )
        create_fn = FakeCreateFn([])
        run_wizard(adapter=adapter, create_fn=create_fn)
        self.assertEqual(create_fn.requests[0].target_duration_sec, 45)

    def test_manual_duration_entry_rejects_non_numeric_then_accepts(self) -> None:
        adapter = ScriptedAdapter(
            _fullscreen_answers(
                [
                    "topic",
                    "Тема",
                    "manual",  # pick manual entry
                    "abc",  # rejected: not a number
                    "50",  # accepted
                    "disabled",
                    "disabled",
                    "disabled",  # music
                    True,
                    "run",
                ]
            )
        )
        create_fn = FakeCreateFn([])
        run_wizard(adapter=adapter, create_fn=create_fn)
        self.assertEqual(create_fn.requests[0].target_duration_sec, 50)


class FullscreenArticleUrlModeTests(unittest.TestCase):
    def test_valid_article_url_accepted(self) -> None:
        adapter = ScriptedAdapter(
            _fullscreen_answers(
                [
                    "article_url",
                    "https://example.com/real-article",
                    "60",
                    "disabled",
                    "disabled",
                    "disabled",  # music
                    True,
                    "run",
                ]
            )
        )
        create_fn = FakeCreateFn([])
        run_wizard(adapter=adapter, create_fn=create_fn)
        self.assertEqual(create_fn.requests[0].source_url, "https://example.com/real-article")

    def test_google_search_url_rejected_before_any_creation_call(self) -> None:
        adapter = ScriptedAdapter(
            _fullscreen_answers(
                [
                    "article_url",
                    "https://www.google.com/search?q=crows",  # rejected
                    "retry",  # try again
                    "https://example.com/real-article",  # now valid
                    "60",
                    "disabled",
                    "disabled",
                    "disabled",  # music
                    True,
                    "run",
                ]
            )
        )
        create_fn = FakeCreateFn([])
        result = run_wizard(adapter=adapter, create_fn=create_fn)
        self.assertIsNotNone(result)
        self.assertEqual(len(create_fn.requests), 1)
        self.assertEqual(create_fn.requests[0].source_url, "https://example.com/real-article")

    def test_bing_yandex_duckduckgo_rejected_offers_use_topic(self) -> None:
        adapter = ScriptedAdapter(
            _fullscreen_answers(
                [
                    "article_url",
                    "https://www.bing.com/search?q=x",
                    "use_topic",
                    "Тема вместо статьи",
                    "60",
                    "disabled",
                    "disabled",
                    "disabled",  # music
                    True,
                    "run",
                ]
            )
        )
        create_fn = FakeCreateFn([])
        run_wizard(adapter=adapter, create_fn=create_fn)
        request = create_fn.requests[0]
        self.assertEqual(request.content_input_mode, "topic")
        self.assertEqual(request.topic, "Тема вместо статьи")


class FullscreenPastedScriptAndFileModeTests(unittest.TestCase):
    def test_pasted_script_mode(self) -> None:
        adapter = ScriptedAdapter(
            _fullscreen_answers(
                [
                    "pasted_script",
                    "Готовый текст сценария целиком.",
                    "60",
                    "disabled",
                    "disabled",
                    "disabled",  # music
                    True,
                    "run",
                ]
            )
        )
        create_fn = FakeCreateFn([])
        run_wizard(adapter=adapter, create_fn=create_fn)
        request = create_fn.requests[0]
        self.assertEqual(request.content_input_mode, "pasted_script")
        self.assertEqual(request.pasted_script, "Готовый текст сценария целиком.")

    def test_script_file_mode_requires_existing_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "script.txt"
            path.write_text("Текст.", encoding="utf-8")
            adapter = ScriptedAdapter(
                _fullscreen_answers(
                    [
                        "script_file",
                        "/no/such/file.txt",  # rejected: not found
                        True,  # try another path
                        str(path),  # valid
                        "60",
                        "disabled",
                        "disabled",
                        "disabled",  # music
                        True,
                        "run",
                    ]
                )
            )
            create_fn = FakeCreateFn([])
            result = run_wizard(adapter=adapter, create_fn=create_fn)
            self.assertIsNotNone(result)
            self.assertEqual(create_fn.requests[0].script_path, str(path))


class NetworkErrorRecoveryTests(unittest.TestCase):
    def test_http_429_retry_then_success(self) -> None:
        adapter = ScriptedAdapter(
            _fullscreen_answers(
                [
                    "topic",
                    "Тема",
                    "60",
                    "disabled",
                    "disabled",
                    "disabled",  # music
                    False,  # not dry_run
                    "run",
                    "retry",  # after error, choose retry
                ]
            )
        )
        create_fn = FakeCreateFn(
            [ContentCreationError("Article request failed with HTTP 429.", reason="http_429", retryable=True)]
        )
        result = run_wizard(adapter=adapter, create_fn=create_fn)
        self.assertIsNotNone(result)
        self.assertEqual(result.status, "completed")
        self.assertEqual(len(create_fn.requests), 2)

    def test_http_403_handled_without_traceback(self) -> None:
        adapter = ScriptedAdapter(
            _fullscreen_answers(["topic", "Тема", "60", "disabled", "disabled", "disabled", False, "run", "retry"])
        )
        create_fn = FakeCreateFn([ContentCreationError("HTTP 403", reason="http_403", retryable=False)])
        try:
            result = run_wizard(adapter=adapter, create_fn=create_fn)
        except Exception as exc:  # pragma: no cover - the whole point is this must not happen
            self.fail(f"run_wizard leaked an exception instead of handling it: {exc!r}")
        self.assertIsNotNone(result)

    def test_timeout_handled_and_retryable(self) -> None:
        adapter = ScriptedAdapter(
            _fullscreen_answers(["topic", "Тема", "60", "disabled", "disabled", "disabled", False, "run", "retry"])
        )
        create_fn = FakeCreateFn([ContentCreationError("timed out", reason="timeout", retryable=True)])
        result = run_wizard(adapter=adapter, create_fn=create_fn)
        self.assertIsNotNone(result)

    def test_change_input_after_error(self) -> None:
        adapter = ScriptedAdapter(
            _fullscreen_answers(
                [
                    "article_url",
                    "https://example.com/article-one",
                    "60",
                    "disabled",
                    "disabled",
                    "disabled",  # music
                    False,
                    "run",
                    "change_input",  # after error
                    "article_url",
                    "https://example.com/article-two",
                ]
            )
        )
        create_fn = FakeCreateFn([ContentCreationError("timed out", reason="timeout", retryable=True)])
        result = run_wizard(adapter=adapter, create_fn=create_fn)
        self.assertIsNotNone(result)
        self.assertEqual(create_fn.requests[0].source_url, "https://example.com/article-one")
        self.assertEqual(create_fn.requests[1].source_url, "https://example.com/article-two")

    def test_use_topic_fallback_after_error(self) -> None:
        adapter = ScriptedAdapter(
            _fullscreen_answers(
                [
                    "article_url",
                    "https://example.com/article",
                    "60",
                    "disabled",
                    "disabled",
                    "disabled",  # music
                    False,
                    "run",
                    "use_topic",
                    "Резервная тема",
                ]
            )
        )
        create_fn = FakeCreateFn([ContentCreationError("timed out", reason="timeout", retryable=True)])
        result = run_wizard(adapter=adapter, create_fn=create_fn)
        self.assertIsNotNone(result)
        self.assertEqual(create_fn.requests[1].content_input_mode, "topic")
        self.assertEqual(create_fn.requests[1].topic, "Резервная тема")

    def test_cancel_after_error(self) -> None:
        adapter = ScriptedAdapter(
            _fullscreen_answers(["topic", "Тема", "60", "disabled", "disabled", "disabled", False, "run", CANCEL])
        )
        create_fn = FakeCreateFn([ContentCreationError("timed out", reason="timeout", retryable=True)])
        result = run_wizard(adapter=adapter, create_fn=create_fn)
        self.assertIsNone(result)


class MusicValidationTests(unittest.TestCase):
    def test_local_file_music_is_offered_for_fullscreen_voiceover(self) -> None:
        # local_file used to be hidden here because nothing wrote
        # assets/music/music_manifest.json. src.audio.music_manifest now writes it and
        # the renderer's existing mixing/ducking path consumes it, so the option is real
        # and must be offered.
        adapter = ScriptedAdapter(
            _fullscreen_answers(["topic", "Тема", "60", "disabled", "disabled", "disabled", True, "run"])
        )
        create_fn = FakeCreateFn([])
        run_wizard(adapter=adapter, create_fn=create_fn)
        request = create_fn.requests[0]
        self.assertEqual(request.music.mode, "disabled")
        self.assertEqual(request.music.path, "")
        messages = [message for message, _ in adapter.select_calls]
        self.assertTrue(any("Музыка" in m for m in messages))
        music_choices = next(choices for message, choices in adapter.select_calls if "Музыка" in message)
        self.assertIn("local_file", [value for value, _ in music_choices])

    def test_local_file_music_path_is_validated_and_kept(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            track = Path(tmp) / "bed.mp3"
            track.write_bytes(b"not-real-audio-but-a-real-file")
            adapter = ScriptedAdapter(
                _fullscreen_answers(
                    ["topic", "Тема", "60", "disabled", "disabled", "local_file", str(track), True, "run"]
                )
            )
            create_fn = FakeCreateFn([])
            run_wizard(adapter=adapter, create_fn=create_fn)
            request = create_fn.requests[0]
            self.assertEqual(request.music.mode, "local_file")
            self.assertEqual(request.music.path, str(track))

    def test_missing_music_file_can_be_abandoned_back_to_disabled(self) -> None:
        adapter = ScriptedAdapter(
            _fullscreen_answers(
                [
                    "topic",
                    "Тема",
                    "60",
                    "disabled",
                    "disabled",
                    "local_file",
                    "/no/such/track.mp3",  # rejected
                    False,  # do not try another path
                    True,  # dry_run
                    "run",
                ]
            )
        )
        create_fn = FakeCreateFn([])
        run_wizard(adapter=adapter, create_fn=create_fn)
        request = create_fn.requests[0]
        self.assertEqual(request.music.mode, "disabled")
        self.assertEqual(request.music.path, "")

    def test_disabled_music_clears_path(self) -> None:
        adapter = ScriptedAdapter(
            _fullscreen_answers(["topic", "Тема", "60", "disabled", "disabled", "disabled", True, "run"])
        )
        create_fn = FakeCreateFn([])
        run_wizard(adapter=adapter, create_fn=create_fn)
        request = create_fn.requests[0]
        self.assertEqual(request.music.mode, "disabled")
        self.assertEqual(request.music.path, "")

    def test_story_card_never_prompts_for_music(self) -> None:
        adapter = ScriptedAdapter(_story_card_answers(["текст", "asset.mp4", True, "run"]))
        run_wizard(adapter=adapter, create_fn=FakeCreateFn([]))
        messages = [message for message, _ in adapter.select_calls]
        self.assertFalse(any("Музыка" in m for m in messages))


class TemplateAwareQuestionTests(unittest.TestCase):
    def test_fullscreen_requires_voice_prompt(self) -> None:
        adapter = ScriptedAdapter(
            _fullscreen_answers(["topic", "Тема", "60", "disabled", "disabled", "disabled", True, "run"])
        )
        run_wizard(adapter=adapter, create_fn=FakeCreateFn([]))
        messages = [message for message, _ in adapter.select_calls]
        self.assertTrue(any("Источник озвучки" in m for m in messages))


class PaidConfirmationTests(unittest.TestCase):
    """elevenlabs + not dry_run now goes through a two-phase preflight (see
    _Wizard.run_creation_with_preflight): the first create_fn call always has
    approve_paid_generation=False (script/asset_search-only, no paid TTS) - the paid
    confirmation is only asked after that prepared result is shown, and a "yes" issues
    a second, resumed create_fn call with approve_paid_generation=True."""

    def _prepared_result(self) -> ContentCreationResult:
        return ContentCreationResult(
            status="prepared_awaiting_paid_approval",
            project_id="p1",
            project_root="/tmp/p1",
            evidence={
                "character_count": 120,
                "word_count": 20,
                "estimated_duration_sec": 51.5,
                "target_duration_sec": 60,
                "scene_count": 6,
                "cache_ready_scenes": 0,
                "cache_missing_scenes": 6,
                "voice_name": "Dom",
                "model_id": "eleven_multilingual_v2",
                "expected_credits": 120,
            },
        )

    def test_paid_confirmation_denied_keeps_prepared_result_single_call(self) -> None:
        adapter = ScriptedAdapter(
            _fullscreen_answers(
                [
                    "topic",
                    "Тема",
                    "60",
                    "elevenlabs",  # provider
                    "ru_dom",  # profile
                    "disabled",  # subtitles
                    "disabled",  # music
                    False,  # dry_run = False -> triggers paid preflight
                    "run",  # edit menu
                    False,  # paid confirmation denied
                ]
            )
        )
        create_fn = FakeCreateFn([self._prepared_result()])
        result = run_wizard(adapter=adapter, create_fn=create_fn)
        self.assertEqual(result.status, "prepared_awaiting_paid_approval")
        self.assertEqual(len(create_fn.requests), 1)
        request = create_fn.requests[0]
        self.assertFalse(request.voice.approve_paid_generation)

    def test_paid_confirmation_accepted_resumes_with_second_call(self) -> None:
        adapter = ScriptedAdapter(
            _fullscreen_answers(
                [
                    "topic",
                    "Тема",
                    "60",
                    "elevenlabs",
                    "ru_dom",
                    "disabled",
                    "disabled",  # music
                    False,
                    "run",  # edit menu
                    True,  # paid confirmation accepted
                ]
            )
        )
        create_fn = FakeCreateFn(
            [self._prepared_result(), ContentCreationResult(status="completed", project_id="p1", project_root="/tmp/p1")]
        )
        result = run_wizard(adapter=adapter, create_fn=create_fn)
        self.assertEqual(result.status, "completed")
        self.assertEqual(len(create_fn.requests), 2)
        self.assertFalse(create_fn.requests[0].voice.approve_paid_generation)
        first_request = create_fn.requests[1]
        self.assertTrue(first_request.voice.approve_paid_generation)
        self.assertTrue(first_request.execution.resume)
        self.assertEqual(first_request.project_id, "p1")

    def test_preflight_summary_printed_before_paid_confirmation(self) -> None:
        # The point of the feature: word count/char count/credits/scene count/cache
        # state must be shown to the user BEFORE the paid Yes/No prompt, not after.
        adapter = ScriptedAdapter(
            _fullscreen_answers(
                [
                    "topic",
                    "Тема",
                    "60",
                    "elevenlabs",
                    "ru_dom",
                    "disabled",
                    "disabled",  # music
                    False,
                    "run",
                    False,  # paid confirmation denied
                ]
            )
        )
        create_fn = FakeCreateFn([self._prepared_result()])
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            run_wizard(adapter=adapter, create_fn=create_fn)
        output = buffer.getvalue()
        self.assertIn("Целевая длительность: 60 сек", output)
        self.assertIn("Оценочная длительность речи: 51.5 сек", output)
        self.assertIn("Слов: 20", output)
        self.assertIn("Символов: 120", output)
        self.assertIn("Dom", output)
        self.assertIn("eleven_multilingual_v2", output)
        self.assertIn("Ожидаемый расход credits: 120", output)
        self.assertIn("Сцен: 6", output)


class ProfileResolutionTests(unittest.TestCase):
    def test_profile_ru_dom_visible_in_summary_not_dash(self) -> None:
        # Stage 2E.1 bugfix: the wizard used to show "profile=-" even after the
        # backend actually resolved ru_dom - now the summary resolves the
        # profile through the same VoiceProfileRegistry before printing it.
        adapter = ScriptedAdapter(
            _fullscreen_answers(
                [
                    "topic",
                    "Тема",
                    "60",
                    "elevenlabs",
                    "ru_dom",
                    "disabled",
                    "disabled",  # music
                    True,  # dry_run -> skip paid confirmation prompt
                    "run",
                ]
            )
        )
        create_fn = FakeCreateFn([])
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            run_wizard(adapter=adapter, create_fn=create_fn)
        output = buffer.getvalue()
        self.assertIn("profile=ru_dom", output)
        self.assertNotIn("profile=-", output)
        self.assertIn("display_name=Dom", output)
        self.assertIn("model=eleven_multilingual_v2", output)

    def test_channel_without_own_voices_yaml_borrows_a_registered_profile(self) -> None:
        # nature_pulse has no channels/nature_pulse/voices.yaml. The wizard used to
        # clear the user's voice choice here and warn that paid generation would not
        # run - but src.news.voice_adapter resolves such a profile globally and would
        # have used it. capabilities.resolve_voice_profile now matches that, so the
        # profile must survive and be labelled with the channel it comes from.
        adapter = ScriptedAdapter(
            [
                START_NEW,
                "vertical_short",
                "fullscreen_voiceover_v1",
                "nature_pulse",
                "ru",
                "topic",
                "Тема",
                "60",
                "elevenlabs",  # provider
                "ru_dom",  # profile, borrowed from nature_science_news_ru
                "disabled",  # subtitles
                "disabled",  # music
                True,  # dry_run
                "run",
            ]
        )
        create_fn = FakeCreateFn([])
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            run_wizard(adapter=adapter, create_fn=create_fn)
        output = buffer.getvalue()
        self.assertIn("profile=ru_dom", output)
        self.assertNotIn("profile=не настроено", output)
        self.assertIn("nature_science_news_ru", output)
        self.assertEqual(create_fn.requests[0].voice.profile, "ru_dom")

    def test_unresolvable_profile_warns_and_clears(self) -> None:
        """A profile no channel registers must still be reported honestly."""
        with patch(
            "src.content_creation.capabilities.resolve_voice_profile",
            side_effect=RuntimeError("nope"),
        ):
            adapter = ScriptedAdapter(
                _fullscreen_answers(
                    ["topic", "Тема", "60", "elevenlabs", "ru_dom", "disabled", "disabled", True, "run"]
                )
            )
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                run_wizard(adapter=adapter, create_fn=FakeCreateFn([]))
        output = buffer.getvalue()
        self.assertIn("не найден", output)
        self.assertIn("платная генерация не будет выполнена", output)


class ReviewEditLoopTests(unittest.TestCase):
    def test_edit_single_field_channel_only(self) -> None:
        adapter = ScriptedAdapter(
            _fullscreen_answers(
                [
                    "topic",
                    "Тема",
                    "60",
                    "disabled",
                    "disabled",
                    "disabled",  # music
                    True,
                    "edit_channel",
                    "nature_science_news_ru",  # re-pick the same channel
                    "run",
                ]
            )
        )
        create_fn = FakeCreateFn([])
        run_wizard(adapter=adapter, create_fn=create_fn)
        request = create_fn.requests[0]
        self.assertEqual(request.channel_id, "nature_science_news_ru")
        self.assertEqual(request.topic, "Тема")

    def test_edit_template_recomputes_voice_and_subtitles(self) -> None:
        # Switch story_card -> fullscreen mid-review; voice/subtitles must now
        # be asked even though they weren't during the initial fill.
        adapter = ScriptedAdapter(
            [
                START_NEW,
                "vertical_short",
                "story_card_text_only_v1",
                "nature_pulse",
                "ru",
                "текст карточки",
                "asset.mp4",
                True,  # dry_run
                "edit_template",
                "fullscreen_voiceover_v1",  # switch template
                "disabled",  # voice (now asked)
                "disabled",  # subtitles (now asked)
                "disabled",  # music
                "run",
            ]
        )
        create_fn = FakeCreateFn([])
        result = run_wizard(adapter=adapter, create_fn=create_fn)
        self.assertIsNotNone(result)
        request = create_fn.requests[0]
        self.assertEqual(request.template_id, "fullscreen_voiceover_v1")
        self.assertEqual(request.voice.provider, "disabled")

    def test_cancel_from_edit_menu_creates_nothing(self) -> None:
        adapter = ScriptedAdapter(
            _fullscreen_answers(["topic", "Тема", "60", "disabled", "disabled", "disabled", True, CANCEL])
        )
        create_fn = FakeCreateFn([])
        result = run_wizard(adapter=adapter, create_fn=create_fn)
        self.assertIsNone(result)
        self.assertEqual(len(create_fn.requests), 0)


class StatusIconTests(unittest.TestCase):
    def test_status_icon_mapping(self) -> None:
        self.assertEqual(_status_icon_key("completed"), "success")
        self.assertEqual(_status_icon_key("needs_review"), "warning")
        self.assertEqual(_status_icon_key("blocked"), "blocked")
        self.assertEqual(_status_icon_key("prepared_awaiting_paid_approval"), "paid")
        self.assertEqual(_status_icon_key("failed"), "error")

    def test_blocked_render_does_not_print_success_checkmark(self) -> None:
        # Stage 2E.1 bugfix: a "blocked" final_render must never render as a
        # plain checkmark line.
        adapter = ScriptedAdapter(
            _fullscreen_answers(["topic", "Тема", "60", "disabled", "disabled", "disabled", True, "run"])
        )
        create_fn = FakeCreateFn(
            [
                ContentCreationResult(
                    status="needs_review",
                    project_id="p1",
                    project_root="/tmp/p1",
                    stages=[
                        {"stage": "voice", "status": "needs_review"},
                        {"stage": "final_render", "status": "blocked"},
                    ],
                )
            ]
        )
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            result = run_wizard(adapter=adapter, create_fn=create_fn)
        output = buffer.getvalue()
        self.assertIsNotNone(result)
        self.assertNotIn("✅ status=needs_review", output)
        self.assertIn("status=needs_review", output)


class IconsAndFallbackTests(unittest.TestCase):
    def test_unicode_icons_by_default(self) -> None:
        icons = choose_icon_set(no_icons=False)
        self.assertEqual(icons["format"], "🎬")

    def test_no_icons_flag_forces_ascii(self) -> None:
        icons = choose_icon_set(no_icons=True)
        self.assertEqual(icons["format"], "[*]")
        for value in icons.values():
            value.encode("ascii")  # must never raise

    def test_falls_back_to_plain_adapter_when_not_a_tty(self) -> None:
        with patch("sys.stdin.isatty", return_value=False), patch("sys.stdout.isatty", return_value=False):
            adapter = _default_adapter()
        self.assertIsInstance(adapter, PlainAdapter)

    def test_uses_questionary_adapter_when_tty(self) -> None:
        with patch("sys.stdin.isatty", return_value=True), patch("sys.stdout.isatty", return_value=True):
            adapter = _default_adapter()
        self.assertIsInstance(adapter, QuestionaryAdapter)


if __name__ == "__main__":
    unittest.main()
