from __future__ import annotations

import unittest


class VoiceProfileRegistryTests(unittest.TestCase):
    def _registry(self):
        from src.audio.tts.models import VoiceProfile
        from src.audio.voice_profile_registry import VoiceProfileRegistry

        return VoiceProfileRegistry(
            {
                "ru_dom": VoiceProfile(
                    profile_id="ru_dom",
                    display_name="Dom",
                    provider="elevenlabs",
                    voice_id="hDfThiytYnsDMuVgm6Qy",
                    model_id="eleven_multilingual_v2",
                    language="ru",
                )
            }
        )

    def test_resolve_by_exact_profile_id(self) -> None:
        registry = self._registry()
        self.assertEqual(registry.resolve("ru_dom").profile_id, "ru_dom")

    def test_resolve_cyrillic_alias(self) -> None:
        registry = self._registry()
        self.assertEqual(registry.resolve("Дом").profile_id, "ru_dom")
        self.assertEqual(registry.resolve("дом").profile_id, "ru_dom")

    def test_resolve_latin_alias(self) -> None:
        registry = self._registry()
        self.assertEqual(registry.resolve("Dom").profile_id, "ru_dom")

    def test_resolve_by_display_name_case_insensitive(self) -> None:
        registry = self._registry()
        self.assertEqual(registry.find_by_display_name("dom").profile_id, "ru_dom")
        self.assertEqual(registry.find_by_display_name("DOM").profile_id, "ru_dom")

    def test_unknown_query_raises(self) -> None:
        from src.audio.voice_profile_registry import VoiceProfileRegistryError

        registry = self._registry()
        with self.assertRaises(VoiceProfileRegistryError):
            registry.resolve("nonexistent_voice")

    def test_loads_real_channel_yaml_and_resolves_dom(self) -> None:
        from src.audio.voice_profile_registry import VoiceProfileRegistry
        from src.config_resolver.paths import resolve_application_paths

        channels_root = resolve_application_paths().channels_root
        registry = VoiceProfileRegistry.from_yaml(
            channels_root / "nature_science_news_ru" / "voices.yaml"
        )
        self.assertEqual(registry.resolve("Дом").profile_id, "ru_dom")
        self.assertNotIn("api_key", registry.get("ru_dom").settings)

    def test_no_conflicting_voice_ids_by_default(self) -> None:
        from src.audio.voice_profile_registry import validate_no_conflicting_voice_ids

        registry = self._registry()
        self.assertEqual(validate_no_conflicting_voice_ids(registry.profiles()), [])

    def test_conflicting_voice_ids_produce_warning(self) -> None:
        from src.audio.tts.models import VoiceProfile
        from src.audio.voice_profile_registry import validate_no_conflicting_voice_ids

        profiles = {
            "a": VoiceProfile(profile_id="a", display_name="A", provider="elevenlabs", voice_id="shared", model_id="m", language="ru"),
            "b": VoiceProfile(profile_id="b", display_name="B", provider="elevenlabs", voice_id="shared", model_id="m", language="ru"),
        }
        warnings = validate_no_conflicting_voice_ids(profiles)
        self.assertEqual(len(warnings), 1)
        self.assertIn("shared", warnings[0])


if __name__ == "__main__":
    unittest.main()
