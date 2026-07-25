"""The UI layer and the runtime must resolve voice profiles identically.

Audit finding (2026-07-25): capabilities.resolve_voice_profile only looked in
channels/<id>/voices.yaml, while src.news.voice_adapter.load_voice_profile_for_channel
falls back to every other channel's voices.yaml. A channel without its own file
(nature_pulse) therefore had its user-chosen voice cleared by the wizard even though
the pipeline would have accepted it - producing a run with no narration.

No network, no provider call, no writes: only registry lookups over files that are
already in the repository, plus tempfile-backed channel dirs.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.audio.voice_profile_registry import VoiceProfileRegistryError
from src.content_creation import capabilities
from src.news.voice_adapter import load_voice_profile_for_channel

_VOICES_YAML = """
voices:
  ru_test:
    display_name: Тест
    provider: elevenlabs
    voice_id: test-voice-id
    model_id: eleven_multilingual_v2
    language: ru
    enabled: true
"""


class _TempChannels:
    """A channels/ tree with one voice-owning channel and one without."""

    def __enter__(self):
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name) / "channels"
        (root / "with_voices").mkdir(parents=True)
        (root / "with_voices" / "voices.yaml").write_text(_VOICES_YAML, encoding="utf-8")
        (root / "without_voices").mkdir(parents=True)
        self._chdir_from = Path.cwd()
        import os

        os.chdir(self._tmp.name)
        return root

    def __exit__(self, *exc):
        import os

        os.chdir(self._chdir_from)
        self._tmp.cleanup()
        return False


class ResolutionParityTests(unittest.TestCase):
    def test_ui_and_runtime_agree_for_a_channel_without_its_own_voices_yaml(self) -> None:
        with _TempChannels():
            ui = capabilities.resolve_voice_profile("without_voices", "ru_test")
            runtime = load_voice_profile_for_channel("without_voices", {}, profile_override="ru_test")
            self.assertEqual(ui, "ru_test")
            self.assertEqual(runtime.profile_id, "ru_test")

    def test_ui_and_runtime_agree_for_a_channel_with_its_own_voices_yaml(self) -> None:
        with _TempChannels():
            ui = capabilities.resolve_voice_profile("with_voices", "ru_test")
            runtime = load_voice_profile_for_channel("with_voices", {}, profile_override="ru_test")
            self.assertEqual(ui, runtime.profile_id)

    def test_display_name_resolves_the_same_way(self) -> None:
        with _TempChannels():
            self.assertEqual(capabilities.resolve_voice_profile("without_voices", "Тест"), "ru_test")

    def test_unknown_profile_still_raises_with_a_clear_message(self) -> None:
        with _TempChannels():
            with self.assertRaises(VoiceProfileRegistryError) as ctx:
                capabilities.resolve_voice_profile("without_voices", "no_such_profile")
            self.assertIn("no_such_profile", str(ctx.exception))

    def test_list_voice_profiles_reports_where_a_borrowed_profile_lives(self) -> None:
        with _TempChannels():
            profiles = capabilities.list_voice_profiles("without_voices")
            self.assertEqual([p["profile_id"] for p in profiles], ["ru_test"])
            self.assertEqual(profiles[0]["source_channel_id"], "with_voices")

            own = capabilities.list_voice_profiles("with_voices")
            self.assertEqual(own[0]["source_channel_id"], "with_voices")

    def test_global_fallback_can_be_switched_off(self) -> None:
        with _TempChannels():
            self.assertEqual(capabilities.list_voice_profiles("without_voices", include_global=False), [])


class RepositoryChannelTests(unittest.TestCase):
    """Against the real channels/ in the repo - ru_dom must be reachable everywhere."""

    def test_ru_dom_resolves_for_every_listed_channel(self) -> None:
        for channel in capabilities.list_channels():
            channel_id = channel["channel_id"]
            ui = capabilities.resolve_voice_profile(channel_id, "ru_dom")
            runtime = load_voice_profile_for_channel(channel_id, {}, profile_override="ru_dom")
            self.assertEqual(ui, runtime.profile_id, f"mismatch for channel {channel_id!r}")

    def test_alias_dom_resolves_to_ru_dom(self) -> None:
        self.assertEqual(capabilities.resolve_voice_profile("nature_science_news_ru", "Дом"), "ru_dom")


if __name__ == "__main__":
    unittest.main()
