"""The UI layer and the runtime must resolve voice profiles identically.

Audit finding (2026-07-25): capabilities.resolve_voice_profile only looked in
channels/<id>/voices.yaml, while src.news.voice_adapter.load_voice_profile_for_channel
falls back to every other channel's voices.yaml. A channel without its own file
(nature_pulse) therefore had its user-chosen voice cleared by the wizard even though
the pipeline would have accepted it - producing a run with no narration.

Fixture isolation (2026-08-01): these tests used to os.chdir() into a temporary
tree. That stopped isolating anything once versioned resources began resolving
against the repository root instead of the process cwd
(src.config_resolver.paths._REPOSITORY_ROOT), so the registry silently read the
real channels/ and answered with ru_dom. The temporary tree is now selected
through the existing repository_root seam of resolve_application_paths - the same
seam tests/test_stage3_workspace_paths.py already uses - which is what both
capabilities._channels_root and voice_profile_registry._channels_root consult.
Neither resolve_voice_profile nor load_voice_profile_for_channel takes a
channels_dir argument, so redirecting their one shared path owner is the only way
to exercise the parity contract against a fixture at all.

No network, no provider call, no writes: only registry lookups over files that are
already in the repository, plus tempfile-backed channel dirs.
"""

from __future__ import annotations

import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

from src.audio.voice_profile_registry import VoiceProfileRegistryError, channel_voices_path
from src.config_resolver import paths as config_paths
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


@contextmanager
def _temp_channels():
    """A channels/ tree with one voice-owning channel and one without.

    Yields the fixture's channels root and, for as long as the block runs, makes it
    the channels root every caller of resolve_application_paths() sees.
    """
    with tempfile.TemporaryDirectory() as tmp:
        # resolve() to match _absolute() on the production side: on Windows the
        # temp dir may otherwise differ from its resolved form.
        repository = Path(tmp).resolve()
        root = repository / "channels"
        (root / "with_voices").mkdir(parents=True)
        (root / "with_voices" / "voices.yaml").write_text(_VOICES_YAML, encoding="utf-8")
        (root / "without_voices").mkdir(parents=True)

        real_resolve = config_paths.resolve_application_paths

        def _scoped(**kwargs):
            kwargs.setdefault("repository_root", repository)
            return real_resolve(**kwargs)

        with mock.patch.object(config_paths, "resolve_application_paths", _scoped):
            # Guard the thing that silently broke before: if the fixture ever stops
            # taking effect, fail here rather than assert against the real channels/.
            selected = channel_voices_path("with_voices").parent.parent
            if selected != root:
                raise RuntimeError(f"Fixture channels root is not in effect: {selected}")
            yield root


class ResolutionParityTests(unittest.TestCase):
    def test_ui_and_runtime_agree_for_a_channel_without_its_own_voices_yaml(self) -> None:
        with _temp_channels():
            ui = capabilities.resolve_voice_profile("without_voices", "ru_test")
            runtime = load_voice_profile_for_channel("without_voices", {}, profile_override="ru_test")
            self.assertEqual(ui, "ru_test")
            self.assertEqual(runtime.profile_id, "ru_test")

    def test_ui_and_runtime_agree_for_a_channel_with_its_own_voices_yaml(self) -> None:
        with _temp_channels():
            ui = capabilities.resolve_voice_profile("with_voices", "ru_test")
            runtime = load_voice_profile_for_channel("with_voices", {}, profile_override="ru_test")
            self.assertEqual(ui, runtime.profile_id)

    def test_display_name_resolves_the_same_way(self) -> None:
        with _temp_channels():
            self.assertEqual(capabilities.resolve_voice_profile("without_voices", "Тест"), "ru_test")

    def test_unknown_profile_still_raises_with_a_clear_message(self) -> None:
        with _temp_channels():
            with self.assertRaises(VoiceProfileRegistryError) as ctx:
                capabilities.resolve_voice_profile("without_voices", "no_such_profile")
            self.assertIn("no_such_profile", str(ctx.exception))

    def test_list_voice_profiles_reports_where_a_borrowed_profile_lives(self) -> None:
        with _temp_channels():
            profiles = capabilities.list_voice_profiles("without_voices")
            self.assertEqual([p["profile_id"] for p in profiles], ["ru_test"])
            self.assertEqual(profiles[0]["source_channel_id"], "with_voices")

            own = capabilities.list_voice_profiles("with_voices")
            self.assertEqual(own[0]["source_channel_id"], "with_voices")

    def test_global_fallback_can_be_switched_off(self) -> None:
        with _temp_channels():
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
