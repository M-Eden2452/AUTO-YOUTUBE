"""The characterization test D1 exists for: the resolver must return exactly what the
current readers return, for every channel that is really on disk.

If one of these fails, the resolver has changed behaviour - which stage D1 is not
allowed to do. Fix the resolver, not the expectation.
"""

from __future__ import annotations

import dataclasses
import json
import unittest
from pathlib import Path

CHANNELS_DIR = Path("channels")


def _real_channel_ids() -> list[str]:
    if not CHANNELS_DIR.is_dir():
        return []
    return [
        entry.name
        for entry in sorted(CHANNELS_DIR.iterdir())
        if entry.is_dir()
        and ((entry / "channel.json").is_file() or (entry / "channel_config.json").is_file())
    ]


class VoicePolicyParityTests(unittest.TestCase):
    """`to_voice_policy(resolve_config(...))` == `resolve_voice_policy_for_channel(...)`."""

    def test_every_channel_resolves_to_the_same_voice_policy_as_today(self) -> None:
        from src.config_resolver import resolve_config, to_voice_policy
        from src.news.pipeline import _load_channel_voice_config, _load_channel_workflow_config
        from src.news.voice_adapter import resolve_voice_policy_for_channel

        channel_ids = _real_channel_ids()
        self.assertTrue(channel_ids, "В репозитории нет ни одного канала - тест бессмысленен.")
        for channel_id in channel_ids:
            with self.subTest(channel=channel_id):
                current = resolve_voice_policy_for_channel(
                    _load_channel_voice_config(channel_id), _load_channel_workflow_config(channel_id)
                )
                resolved = to_voice_policy(
                    resolve_config(
                        channel_id=channel_id,
                        # News-to-Short is what resolve_voice_policy_for_channel assumes.
                        template_id="fullscreen_voiceover_v1",
                        format_id="vertical_short",
                        include_secrets=False,
                    )
                )
                for field in dataclasses.fields(current):
                    self.assertEqual(
                        getattr(current, field.name),
                        getattr(resolved, field.name),
                        f"{channel_id}: поле {field.name}",
                    )

    def test_resolver_covers_every_voice_field_the_current_layers_can_set(self) -> None:
        """Parity above must be structural, not a coincidence: any VoicePolicy field that
        AUDIO_POLICY_DEFAULTS or the channel adapter can set has to be a resolver key."""
        from src.audio.voice_policy import AUDIO_POLICY_DEFAULTS, voice_policy_from_channel_config
        from src.config_resolver import VOICE_KEYS

        settable: set[str] = set()
        for policy in AUDIO_POLICY_DEFAULTS.values():
            settable.update(policy)
        for channel_id in _real_channel_ids():
            config_path = CHANNELS_DIR / channel_id / "channel_config.json"
            if not config_path.is_file():
                continue
            data = json.loads(config_path.read_text(encoding="utf-8"))
            settable.update(voice_policy_from_channel_config(data.get("voice"), data.get("voice_workflow")))

        covered = {key.split(".", 1)[1] for key in VOICE_KEYS}
        self.assertEqual(
            settable - covered,
            set(),
            "Эти поля VoicePolicy задаются существующими слоями, но у резолвера для них нет ключа.",
        )


class ChannelReaderParityTests(unittest.TestCase):
    def test_language_matches_the_reader_each_workflow_uses(self) -> None:
        """The two create paths resolve language differently today
        (`request.language or channel.default_language` for story card,
        `request.language or "ru"` for news). The resolver must reproduce whichever
        source each channel actually has."""
        from src.config_resolver import keys, resolve_config
        from src.news.pipeline import _load_channel_config
        from src.project_foundation.channels import ChannelRegistry

        for channel_id in _real_channel_ids():
            with self.subTest(channel=channel_id):
                resolved = resolve_config(channel_id=channel_id, include_secrets=False)
                config_language = _load_channel_config(channel_id).get("language")
                if config_language:
                    expected = config_language
                elif (CHANNELS_DIR / channel_id / "channel.json").is_file():
                    expected = ChannelRegistry().get(channel_id).default_language
                else:
                    expected = "ru"
                self.assertEqual(resolved.get(keys.KEY_LANGUAGE), expected)

    def test_voice_profile_matches_what_the_voice_stage_would_load(self) -> None:
        """`load_voice_profile_for_channel` reads `voice.voice_profile` from
        channel_config.json and falls back to "ru_dom". The resolver must name the same
        profile id before that fallback applies."""
        from src.config_resolver import keys, resolve_config
        from src.news.pipeline import _load_channel_voice_config

        for channel_id in _real_channel_ids():
            with self.subTest(channel=channel_id):
                expected = (_load_channel_voice_config(channel_id) or {}).get("voice_profile") or ""
                resolved = resolve_config(
                    channel_id=channel_id, format_id="vertical_short", include_secrets=False
                )
                self.assertEqual(resolved.get(keys.KEY_VOICE_PROFILE), expected)

    def test_geometry_matches_the_catalog_format(self) -> None:
        from src.config_resolver import keys, resolve_config, to_render_settings
        from src.production_catalog.catalog import get_default_catalog

        for definition in get_default_catalog().formats.list_all():
            with self.subTest(format=definition.format_id):
                resolved = resolve_config(format_id=definition.format_id, include_secrets=False)
                settings = to_render_settings(resolved)
                self.assertEqual(settings["width"], definition.width)
                self.assertEqual(settings["height"], definition.height)
                self.assertEqual(settings["aspect_ratio"], definition.aspect_ratio)
                self.assertEqual(resolved.get(keys.KEY_FPS), 30)

    def test_legacy_template_alias_resolves_to_the_canonical_template(self) -> None:
        """`story_card_short_v1` is a legacy alias in the catalog. The resolver must
        accept it and report the canonical id, not the alias, as the origin."""
        from src.config_resolver import resolve_config

        alias = resolve_config(template_id="story_card_short_v1", include_secrets=False)
        canonical = resolve_config(template_id="story_card_text_only_v1", include_secrets=False)
        self.assertEqual(
            alias.to_dict(include_trace=True)["values"],
            canonical.to_dict(include_trace=True)["values"],
        )
        self.assertIn("story_card_text_only_v1", alias.resolved("voice.output_mode").origin)

    def test_template_capability_layer_agrees_with_capabilities_report(self) -> None:
        from src.config_resolver import keys, resolve_config
        from src.content_creation.capabilities import describe_template_capabilities
        from src.production_catalog.catalog import get_default_catalog

        for template in get_default_catalog().templates.list_all():
            with self.subTest(template=template.template_id):
                capabilities = describe_template_capabilities(template.template_id)
                resolved = resolve_config(template_id=template.template_id, include_secrets=False)
                if not capabilities["subtitles_allowed"]:
                    self.assertFalse(resolved.get(keys.KEY_SUBTITLES_ENABLED))
                    self.assertEqual(resolved.get(keys.KEY_SUBTITLES_STYLE), "disabled")
                if not capabilities["music_allowed"]:
                    self.assertFalse(resolved.get(keys.KEY_MUSIC_ENABLED))
                self.assertEqual(resolved.get(keys.KEY_VOICE_OUTPUT_MODE), capabilities["default_voice_mode"])
                self.assertEqual(resolved.get(keys.KEY_VOICE_TIMING_MODE), capabilities["default_timing_mode"])


class RealProjectsAreReadableTests(unittest.TestCase):
    def test_existing_projects_resolve_without_error_and_without_writes(self) -> None:
        """Every project already on disk - both manifest kinds, including pre-B3 ones -
        must be readable as a config layer, and reading must not modify it."""
        from src.config_resolver import ConfigResolutionError, resolve_config
        from src.projects.repository import ProjectRepository

        repository = ProjectRepository("projects")
        project_ids = [
            project_id
            for project_id in repository.list_ids()
            if repository.detect_kind(project_id) != "unknown"
        ]
        if not project_ids:
            self.skipTest("В projects/ нет проектов ни одного из двух видов.")
        for project_id in project_ids:
            with self.subTest(project=project_id):
                manifest = repository.project_root(project_id)
                before = {
                    path: path.read_bytes()
                    for path in (manifest / "job.json", manifest / "project.json")
                    if path.is_file()
                }
                try:
                    resolved = resolve_config(project_id=project_id, include_secrets=False)
                except ConfigResolutionError as exc:  # pragma: no cover - diagnostic
                    self.fail(f"{project_id}: {exc}")
                self.assertTrue(resolved.values)
                after = {path: path.read_bytes() for path in before}
                self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
