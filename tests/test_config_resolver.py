from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


class _FixtureCase(unittest.TestCase):
    """A throwaway channels/ and projects/ tree so no test touches the real ones."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.channels = self.root / "channels"
        self.projects = self.root / "projects"
        self.channels.mkdir()
        self.projects.mkdir()
        self.addCleanup(self._tmp.cleanup)

    def write_channel_config(self, channel_id: str, data: dict[str, Any]) -> None:
        _write_json(self.channels / channel_id / "channel_config.json", data)

    def write_channel_profile(self, channel_id: str, data: dict[str, Any]) -> None:
        _write_json(self.channels / channel_id / "channel.json", data)

    def resolve(self, **kwargs: Any):
        from src.config_resolver import resolve_config

        kwargs.setdefault("channels_dir", str(self.channels))
        kwargs.setdefault("projects_dir", str(self.projects))
        kwargs.setdefault("include_secrets", False)
        return resolve_config(**kwargs)


class KeyRegistryTests(unittest.TestCase):
    def test_every_setting_has_a_known_value_type(self) -> None:
        from src.config_resolver import keys

        for setting in keys.SETTINGS:
            self.assertIn(setting.value_type, keys.VALUE_TYPES, setting.key)

    def test_keys_are_unique(self) -> None:
        from src.config_resolver import keys

        listed = keys.list_keys()
        self.assertEqual(len(listed), len(set(listed)))

    def test_only_secret_settings_declare_an_env_var(self) -> None:
        from src.config_resolver import keys

        for setting in keys.SETTINGS:
            self.assertEqual(bool(setting.env_var), setting.is_secret, setting.key)

    def test_get_setting_rejects_unknown_key(self) -> None:
        from src.config_resolver import get_setting

        with self.assertRaises(KeyError):
            get_setting("voice.does_not_exist")

    def test_global_defaults_repeat_the_hardcoded_values_in_the_consumers(self) -> None:
        """These defaults are only honest if they equal what the code falls back to."""
        from src.audio.voice_policy import VoicePolicy
        from src.config_resolver import keys
        from src.news.models import NewsJob

        policy = VoicePolicy()
        job = NewsJob.create(channel_id="c", input_mode="topic", topic="t")
        expected = {
            keys.KEY_LANGUAGE: job.language,
            keys.KEY_TARGET_DURATION: job.target_duration_sec,
            keys.KEY_WIDTH: job.resolution["width"],
            keys.KEY_HEIGHT: job.resolution["height"],
            keys.KEY_ASPECT_RATIO: job.aspect_ratio,
            keys.KEY_VOICE_ENABLED: policy.enabled,
            keys.KEY_VOICE_REQUIRED: policy.required,
            keys.KEY_VOICE_PROVIDER: policy.provider,
            keys.KEY_VOICE_PROFILE: policy.voice_profile,
            keys.KEY_VOICE_MODEL_ID: policy.model_id,
            keys.KEY_VOICE_OUTPUT_MODE: policy.output_mode,
            keys.KEY_VOICE_TIMING_MODE: policy.timing_mode,
            keys.KEY_VOICE_APPROVAL_REQUIRED: policy.approval_required,
            keys.KEY_VOICE_AUDITION_REQUIRED: policy.audition_required,
            keys.KEY_VOICE_SCENE_LEVEL: policy.scene_level_generation,
            keys.KEY_VOICE_FALLBACK_POLICY: policy.fallback_policy,
            keys.KEY_VOICE_FAILURE_POLICY: policy.failure_policy,
            keys.KEY_VOICE_OUTPUT_FORMAT: policy.output_format,
            keys.KEY_VOICE_SAMPLE_RATE: policy.target_sample_rate,
            keys.KEY_VOICE_CHANNELS: policy.target_channels,
            keys.KEY_VOICE_SPEED: policy.speed,
        }
        for key, value in expected.items():
            self.assertEqual(keys.get_setting(key).default, value, key)


#: Keys that really sit in a `config/channels/*/channel_config.json` and that no
#: module reads, each kept on purpose and each with the reason it is kept.
#:
#: Measured with `_channel_config_leaf_keys` below, so the number is recomputable
#: rather than quoted: of 79 distinct leaf keys across five channel configs, 14
#: appeared nowhere in `src/`, `tools/` or `scripts/`; after
#: `assets.allow_unknown_rights` was deleted, 78 and 13. The test-system audit
#: §7.5 said 76, this comment repeated it, and an independent review of the slice
#: recounted with this file's own helper - the census total was wrong, the
#: load-bearing count of dead keys was not. That is not an accident anyone can see - the owner
#: opens their channel file and reads it as settings, because a file of settings
#: is what it looks like. This list is what turns each of them from an accident
#: into a decision, and the test below is what stops a fifteenth appearing
#: quietly.
#:
#: The bar for being here is narrow: a key may be a *declared intent* nobody has
#: wired yet. A key may not be here if it reads as a safety control - a switch
#: that promises to restrain rights, money or the network and does nothing is
#: worse than no switch, and `assets.allow_unknown_rights` was deleted from
#: `nature_science_news_ru` rather than declared for exactly that reason (rights
#: are enforced by `src/projects/rights.py` and `src/assets/license_policy.py`,
#: which never read it).
#:
#: A key leaves this list in one of two ways: something starts reading it (then
#: it belongs in `keys.SETTINGS` with real consumers), or it is deleted.
DECLARATIVE_UNREAD_CHANNEL_KEYS: dict[str, str] = {
    "approval.script_required": "заявленный порядок приёмки; ladder приёмки живёт в completion, ключ канала в него не заведён",
    "approval.assets_required": "то же самое для ассетов",
    "approval.final_render_required": "то же самое для финального рендера",
    "assets.prefer_user_assets": "приоритет пользовательских ассетов; сегодня порядок источников задаёт retrieval, не канал",
    "assets.use_local_library": "выключатель локальной библиотеки, который ничего не выключает — строка реестра C83, решение «читать или удалить» за владельцем",
    "assets.future_paid_providers": "список на будущее и прямо назван будущим; потребителя нет и не должно быть сейчас",
    "content.niche": "ниша канала как продуктовое описание, а не настройка",
    "content.avoid_exaggeration": "редакционное правило для человека, пишущего сценарий",
    "content.distinguish_hypotheses": "то же самое",
    "content_rules": "редакционные правила размером с абзац; в size_comparison",
    "default_style_profile": "заявленный стилевой профиль канала; в psychology, quotes, survival",
    "voice_workflow.audition_max_characters": "ограничение прослушивания; сама audition читает свои параметры из voice-блока",
    "voice_workflow.audition_model_strategy": "то же самое",
}


def _channel_config_leaf_keys() -> dict[str, list[Any]]:
    """Every leaf key of every real channel config: dotted name -> values seen."""
    found: dict[str, list[Any]] = {}

    def walk(value: Any, path: tuple[str, ...]) -> None:
        if isinstance(value, dict):
            for name, item in value.items():
                walk(item, path + (name,))
            return
        found.setdefault(".".join(path), []).append(value)

    for config in sorted(REPO_ROOT.glob("config/channels/*/channel_config.json")):
        walk(json.loads(config.read_text(encoding="utf-8")), ())
    return found


def _names_present_in_code() -> set[str]:
    """Leaf names that appear literally anywhere in ``src``/``tools``/``scripts``.

    Weak evidence of a consumer, and deliberately the same weak evidence the
    test-system audit used to count the fourteen dead keys - so this test agrees
    with the number the owner already accepted, instead of inventing a second.
    A name that appears somewhere is not proof that the value is honoured; a name
    that appears **nowhere** is proof that it is not.
    """
    names: set[str] = set()
    text = "\n".join(
        source.read_text(encoding="utf-8", errors="ignore")
        for folder in ("src", "tools", "scripts")
        for source in (REPO_ROOT / folder).rglob("*.py")
    )
    for key in _channel_config_leaf_keys():
        leaf = key.rsplit(".", 1)[-1]
        if leaf in text:
            names.add(key)
    return names


class ChannelKeyConsumerTests(unittest.TestCase):
    """Every key a channel file carries is either read or declared unread.

    The declared-consumer check the test-system audit asked for (§7.5, slice S5),
    built out of what already exists rather than as a config framework: the
    resolver's own `keys.SETTINGS` already says which module reads what, and
    `no_consumer_yet` already exists as a state. What was missing is the
    obligation to say *something* about a key at all.

    Deliberately not a schema and not a grep for forbidden names: a new key is
    allowed, it just cannot arrive silently.
    """

    def test_every_channel_key_is_read_or_declared_unread(self) -> None:
        from src.config_resolver import keys

        answered = set(keys.list_keys()) | _names_present_in_code()
        undeclared = sorted(
            key
            for key in _channel_config_leaf_keys()
            if key not in answered and key not in DECLARATIVE_UNREAD_CHANNEL_KEYS
        )
        self.assertEqual(
            [],
            undeclared,
            "ключ канала, которого не читает никто и который нигде не объявлен: "
            "заведи его в keys.SETTINGS с настоящим потребителем, добавь строку "
            "в DECLARATIVE_UNREAD_CHANNEL_KEYS с причиной, или удали ключ",
        )

    def test_the_declared_list_does_not_outlive_its_keys(self) -> None:
        """A key that was deleted or wired must leave the list in the same slice.

        Without this the list becomes the same kind of scenery it exists to
        prevent - a record of what channel files used to carry.
        """
        from src.config_resolver import keys

        present = set(_channel_config_leaf_keys())
        answered = set(keys.list_keys()) | _names_present_in_code()
        stale = {
            key: (
                "больше нет ни в одном channel_config.json"
                if key not in present
                else "теперь читается — место этому ключу в keys.SETTINGS"
            )
            for key in DECLARATIVE_UNREAD_CHANNEL_KEYS
            if key not in present or key in answered
        }
        self.assertEqual({}, stale)

    def test_no_declared_key_promises_to_restrain_rights_money_or_network(self) -> None:
        """The one thing this list may not be used for.

        Declaring a dead safety switch would make the list a way to keep a false
        promise tidy. The words below are the ones such a switch is written with
        in this repository - `allow_unknown_rights` was the case that prompted
        the rule, and it was deleted rather than declared.
        """
        restraining = ("rights", "allow", "paid", "budget", "network", "usd", "cost", "license")
        values = _channel_config_leaf_keys()
        offenders = [
            key
            for key in DECLARATIVE_UNREAD_CHANNEL_KEYS
            # A switch is a boolean. ``assets.future_paid_providers`` carries the
            # word and is a list of names for later - it promises nothing to
            # restrain, and reading it as a switch would make this check noise.
            if any(isinstance(value, bool) for value in values.get(key, ()))
            and any(word in key.rsplit(".", 1)[-1].casefold() for word in restraining)
        ]
        self.assertEqual([], offenders)


class PrecedenceTests(_FixtureCase):
    def test_all_layers_apply_in_order(self) -> None:
        """One key touched by every layer: each stronger layer must win in turn."""
        from src.config_resolver import (
            SOURCE_CHANNEL_CONFIG,
            SOURCE_CHANNEL_PROFILE,
            SOURCE_FORMAT_POLICY,
            SOURCE_GLOBAL_DEFAULT,
            SOURCE_LOCALIZATION_OVERRIDE,
            SOURCE_PROJECT_OVERRIDE,
            SOURCE_RUNTIME_OVERRIDE,
            SOURCE_TEMPLATE_POLICY,
            keys,
        )

        self.write_channel_profile("c", {"channel_id": "c", "default_language": "es"})
        self.assertEqual(self.resolve(channel_id="c").source_of(keys.KEY_LANGUAGE), SOURCE_CHANNEL_PROFILE)
        self.assertEqual(self.resolve().source_of(keys.KEY_LANGUAGE), SOURCE_GLOBAL_DEFAULT)

        self.write_channel_config(
            "c",
            {
                "language": "en",
                "voice": {"provider": "elevenlabs", "voice_profile": "ch_profile"},
                "languages": {"de": {"enabled": True, "voice": {"voice_profile": "loc_profile"}}},
            },
        )
        resolved = self.resolve(channel_id="c")
        self.assertEqual(resolved.source_of(keys.KEY_LANGUAGE), SOURCE_CHANNEL_CONFIG)
        self.assertEqual(resolved.get(keys.KEY_LANGUAGE), "en")

        # format layer supplies geometry the global default also has
        resolved = self.resolve(channel_id="c", format_id="longform")
        self.assertEqual(resolved.source_of(keys.KEY_WIDTH), SOURCE_FORMAT_POLICY)
        self.assertEqual(resolved.get(keys.KEY_WIDTH), 1920)

        # template beats channel for voice policy fields
        resolved = self.resolve(channel_id="c", template_id="fullscreen_voiceover_v1")
        self.assertEqual(resolved.source_of(keys.KEY_VOICE_OUTPUT_MODE), SOURCE_TEMPLATE_POLICY)

        _write_json(self.projects / "p" / "job.json", {"language": "fr"})
        resolved = self.resolve(channel_id="c", project_id="p")
        self.assertEqual(resolved.source_of(keys.KEY_LANGUAGE), SOURCE_PROJECT_OVERRIDE)
        self.assertEqual(resolved.get(keys.KEY_LANGUAGE), "fr")

        resolved = self.resolve(channel_id="c", project_id="p", language="de")
        self.assertEqual(resolved.source_of(keys.KEY_VOICE_PROFILE), SOURCE_LOCALIZATION_OVERRIDE)
        self.assertEqual(resolved.get(keys.KEY_VOICE_PROFILE), "loc_profile")

        resolved = self.resolve(
            channel_id="c", project_id="p", language="de", overrides={keys.KEY_VOICE_PROFILE: "cli_profile"}
        )
        self.assertEqual(resolved.source_of(keys.KEY_VOICE_PROFILE), SOURCE_RUNTIME_OVERRIDE)
        self.assertEqual(resolved.get(keys.KEY_VOICE_PROFILE), "cli_profile")

    def test_source_priorities_are_strictly_ordered(self) -> None:
        from src.config_resolver import SOURCE_PRIORITY

        priorities = list(SOURCE_PRIORITY.values())
        self.assertEqual(priorities, sorted(priorities))
        self.assertEqual(len(priorities), len(set(priorities)))

    def test_trace_names_the_winner_and_everyone_it_overrode(self) -> None:
        from src.config_resolver import (
            OUTCOME_OVERRIDDEN,
            OUTCOME_SELECTED,
            SOURCE_CHANNEL_CONFIG,
            SOURCE_GLOBAL_DEFAULT,
            SOURCE_RUNTIME_OVERRIDE,
            keys,
        )

        self.write_channel_config("c", {"language": "en"})
        value = self.resolve(channel_id="c", overrides={keys.KEY_LANGUAGE: "es"}).resolved(keys.KEY_LANGUAGE)
        outcomes = {step.source: step.outcome for step in value.trace}
        self.assertEqual(outcomes[SOURCE_GLOBAL_DEFAULT], OUTCOME_OVERRIDDEN)
        self.assertEqual(outcomes[SOURCE_CHANNEL_CONFIG], OUTCOME_OVERRIDDEN)
        self.assertEqual(outcomes[SOURCE_RUNTIME_OVERRIDE], OUTCOME_SELECTED)
        self.assertEqual(value.value, "es")

    def test_template_over_channel_conflict_is_reported_not_hidden(self) -> None:
        from src.config_resolver import WARNING_TEMPLATE_OVER_CHANNEL, keys

        self.write_channel_config(
            "c", {"voice_workflow": {"never_auto_fallback_to_paid": True}}
        )
        value = self.resolve(channel_id="c", template_id="fullscreen_voiceover_v1").resolved(
            keys.KEY_VOICE_FALLBACK_POLICY
        )
        self.assertEqual(value.value, "manual_audio")
        self.assertIn(WARNING_TEMPLATE_OVER_CHANNEL, value.warnings)

    def test_used_default_is_true_only_when_no_file_supplied_a_value(self) -> None:
        from src.config_resolver import keys

        self.write_channel_config("c", {"language": "en"})
        resolved = self.resolve(channel_id="c")
        self.assertFalse(resolved.resolved(keys.KEY_LANGUAGE).used_default)
        self.assertTrue(resolved.resolved(keys.KEY_SUBTITLES_STYLE).used_default)


class NormalizationTests(_FixtureCase):
    def test_blank_string_is_treated_as_unset(self) -> None:
        """A disabled language's placeholder fields must not wipe the channel voice."""
        from src.config_resolver import OUTCOME_BLANK, SOURCE_CHANNEL_CONFIG, keys

        self.write_channel_config(
            "c",
            {
                "voice": {"voice_profile": "ru_dom", "model": "eleven_multilingual_v2"},
                "languages": {"en": {"enabled": True, "voice": {"voice_profile": "", "model": ""}}},
            },
        )
        value = self.resolve(channel_id="c", language="en").resolved(keys.KEY_VOICE_PROFILE)
        self.assertEqual(value.value, "ru_dom")
        self.assertEqual(value.source, SOURCE_CHANNEL_CONFIG)
        self.assertIn(OUTCOME_BLANK, [step.outcome for step in value.trace])

    def test_empty_provider_settings_block_is_treated_as_unset(self) -> None:
        from src.config_resolver import keys

        self.write_channel_config(
            "c",
            {
                "voice": {"settings": {"stability": 0.6}},
                "languages": {"en": {"enabled": True, "voice": {"settings": {}}}},
            },
        )
        resolved = self.resolve(channel_id="c", language="en")
        self.assertEqual(resolved.get(keys.KEY_VOICE_PROVIDER_SETTINGS), {"stability": 0.6})

    def test_disabled_language_block_contributes_nothing(self) -> None:
        from src.config_resolver import SOURCE_LOCALIZATION_OVERRIDE, keys

        self.write_channel_config(
            "c",
            {
                "voice": {"voice_profile": "ru_dom"},
                "languages": {"en": {"enabled": False, "voice": {"voice_profile": "en_voice"}}},
            },
        )
        resolved = self.resolve(channel_id="c", language="en")
        self.assertEqual(resolved.get(keys.KEY_VOICE_PROFILE), "ru_dom")
        layer = next(layer for layer in resolved.layers if layer.source == SOURCE_LOCALIZATION_OVERRIDE)
        self.assertEqual(layer.values, {})
        self.assertIn("enabled=false", layer.note)

    def test_string_number_is_coerced_and_flagged(self) -> None:
        from src.config_resolver import keys

        self.write_channel_config("c", {"target_duration_sec": "40"})
        value = self.resolve(channel_id="c").resolved(keys.KEY_TARGET_DURATION)
        self.assertEqual(value.value, 40)
        self.assertTrue(value.normalized)

    def test_uncoercible_value_is_skipped_and_reported(self) -> None:
        from src.config_resolver import OUTCOME_INVALID, WARNING_INVALID_LAYER_VALUE, keys

        self.write_channel_config("c", {"target_duration_sec": "около минуты"})
        value = self.resolve(channel_id="c").resolved(keys.KEY_TARGET_DURATION)
        self.assertEqual(value.value, 55)
        self.assertIn(WARNING_INVALID_LAYER_VALUE, value.warnings)
        self.assertIn(OUTCOME_INVALID, [step.outcome for step in value.trace])

    def test_settings_nobody_reads_are_marked(self) -> None:
        from src.config_resolver import WARNING_NO_CONSUMER, keys

        self.write_channel_config("c", {"min_duration_sec": 35, "target_duration_sec": 55})
        resolved = self.resolve(channel_id="c")
        self.assertIn(WARNING_NO_CONSUMER, resolved.resolved(keys.KEY_MIN_DURATION).warnings)
        self.assertNotIn(WARNING_NO_CONSUMER, resolved.resolved(keys.KEY_TARGET_DURATION).warnings)


class SecretTests(_FixtureCase):
    def test_secret_value_is_a_presence_flag_not_the_key(self) -> None:
        from src.config_resolver import SOURCE_ENVIRONMENT, keys, resolve_config

        with mock.patch.dict(os.environ, {"ELEVENLABS_API_KEY": "sk-super-secret-value"}, clear=False):
            resolved = resolve_config(channels_dir=str(self.channels), projects_dir=str(self.projects))
        value = resolved.resolved(keys.KEY_SECRET_ELEVENLABS)
        self.assertIs(value.value, True)
        self.assertTrue(value.is_secret)
        self.assertEqual(value.source, SOURCE_ENVIRONMENT)
        self.assertNotIn("sk-super-secret-value", json.dumps(value.to_dict(), ensure_ascii=False))

    def test_no_secret_reaches_any_serialized_output(self) -> None:
        from src.config_resolver import resolve_config

        secret = "sk-must-never-appear-anywhere"
        env = {name: secret for name in ("ELEVENLABS_API_KEY", "OPENAI_API_KEY", "PEXELS_API_KEY", "PIXABAY_API_KEY")}
        with mock.patch.dict(os.environ, env, clear=False):
            resolved = resolve_config(channels_dir=str(self.channels), projects_dir=str(self.projects))
        dumped = json.dumps(resolved.to_dict(include_trace=True), ensure_ascii=False, default=str)
        self.assertNotIn(secret, dumped)
        for row in resolved.explain_rows():
            self.assertNotIn(secret, json.dumps(row, ensure_ascii=False))

    def test_secret_display_and_redaction_never_show_a_value(self) -> None:
        from src.config_resolver import REDACTED, keys, resolve_config

        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "sk-x"}, clear=False):
            value = resolve_config(channels_dir=str(self.channels)).resolved(keys.KEY_SECRET_OPENAI)
        self.assertEqual(value.display_value, "настроен")
        self.assertEqual(value.redacted_value, REDACTED)

    def test_missing_secret_reports_not_configured(self) -> None:
        from src.config_resolver import keys, resolve_config

        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "   "}, clear=False):
            value = resolve_config(channels_dir=str(self.channels)).resolved(keys.KEY_SECRET_OPENAI)
        self.assertIs(value.value, False)
        self.assertEqual(value.display_value, "не настроен")

    def test_get_refuses_to_serve_a_secret_key(self) -> None:
        from src.config_resolver import ConfigResolutionError, keys

        resolved = self.resolve()
        with self.assertRaises(ConfigResolutionError) as ctx:
            resolved.get(keys.KEY_SECRET_OPENAI)
        self.assertEqual(ctx.exception.reason, "secret_access")

    def test_secret_cannot_be_supplied_through_overrides(self) -> None:
        from src.config_resolver import ConfigResolutionError, ConfigResolutionRequest, keys

        with self.assertRaises(ConfigResolutionError) as ctx:
            ConfigResolutionRequest(overrides={keys.KEY_SECRET_PEXELS: "sk-nope"})
        self.assertEqual(ctx.exception.reason, "secret_override")

    def test_include_secrets_false_skips_the_environment_entirely(self) -> None:
        from src.config_resolver import SOURCE_ENVIRONMENT

        with mock.patch("os.getenv", side_effect=AssertionError("окружение читаться не должно")):
            resolved = self.resolve()
        layer = next(layer for layer in resolved.layers if layer.source == SOURCE_ENVIRONMENT)
        self.assertEqual(layer.values, {})

    def test_environment_layer_emits_booleans_only(self) -> None:
        """The one structural guarantee behind every other secret test: the layer that
        touches os.getenv stores the result of bool(), so no key string ever enters the
        resolution machinery - not into a trace, not into a coercion error message."""
        from src.config_resolver.layers import environment_layer

        with mock.patch.dict(os.environ, {"PEXELS_API_KEY": "sk-value"}, clear=False):
            layer = environment_layer()
        self.assertTrue(layer.values)
        for value in layer.values.values():
            self.assertIsInstance(value, bool)

    def test_secret_presence_adapter_returns_only_booleans(self) -> None:
        from src.config_resolver import SECRET_KEYS, resolve_config, secret_presence

        with mock.patch.dict(os.environ, {"PEXELS_API_KEY": "sk-a"}, clear=False):
            presence = secret_presence(resolve_config(channels_dir=str(self.channels)))
        self.assertEqual(sorted(presence), sorted(SECRET_KEYS))
        for value in presence.values():
            self.assertIsInstance(value, bool)


class ErrorTests(_FixtureCase):
    def test_unknown_channel_raises_a_clear_error(self) -> None:
        from src.config_resolver import ConfigResolutionError

        with self.assertRaises(ConfigResolutionError) as ctx:
            self.resolve(channel_id="no_such_channel")
        self.assertEqual(ctx.exception.reason, "unknown_channel")
        self.assertIn("no_such_channel", str(ctx.exception))

    def test_unknown_template_raises_a_clear_error(self) -> None:
        from src.config_resolver import ConfigResolutionError

        self.write_channel_config("c", {})
        with self.assertRaises(ConfigResolutionError) as ctx:
            self.resolve(channel_id="c", template_id="no_such_template")
        self.assertEqual(ctx.exception.reason, "unknown_template")

    def test_unknown_format_raises_a_clear_error(self) -> None:
        from src.config_resolver import ConfigResolutionError

        with self.assertRaises(ConfigResolutionError) as ctx:
            self.resolve(format_id="no_such_format")
        self.assertEqual(ctx.exception.reason, "unknown_format")

    def test_unknown_project_raises_a_clear_error(self) -> None:
        from src.config_resolver import ConfigResolutionError

        with self.assertRaises(ConfigResolutionError) as ctx:
            self.resolve(project_id="no_such_project")
        self.assertEqual(ctx.exception.reason, "unknown_project")

    def test_unreadable_channel_profile_raises_the_resolver_error_not_a_traceback(self) -> None:
        from src.config_resolver import ConfigResolutionError

        path = self.channels / "c" / "channel.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{ это не json", encoding="utf-8")
        with self.assertRaises(ConfigResolutionError) as ctx:
            self.resolve(channel_id="c")
        self.assertEqual(ctx.exception.reason, "invalid_channel_profile")

    def test_unreadable_channel_config_is_treated_as_absent_like_the_pipeline_does(self) -> None:
        """`src.news.pipeline._load_channel_config` swallows a broken channel_config.json
        and returns {}. The resolver must not start failing where the pipeline copes."""
        from src.config_resolver import SOURCE_CHANNEL_CONFIG, keys

        path = self.channels / "c" / "channel_config.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{ это не json", encoding="utf-8")
        resolved = self.resolve(channel_id="c")
        self.assertEqual(resolved.get(keys.KEY_LANGUAGE), "ru")
        layer = next(layer for layer in resolved.layers if layer.source == SOURCE_CHANNEL_CONFIG)
        self.assertEqual(layer.values, {})
        self.assertTrue(layer.note)

    def test_unknown_override_key_is_rejected_not_ignored(self) -> None:
        from src.config_resolver import ConfigResolutionError, ConfigResolutionRequest

        with self.assertRaises(ConfigResolutionError) as ctx:
            ConfigResolutionRequest(overrides={"voice.made_up": 1})
        self.assertEqual(ctx.exception.reason, "unknown_key")

    def test_resolved_lookup_of_unknown_key_raises(self) -> None:
        from src.config_resolver import ConfigResolutionError

        with self.assertRaises(ConfigResolutionError):
            self.resolve().resolved("nope")


class ReadOnlyTests(_FixtureCase):
    def test_resolution_writes_nothing(self) -> None:
        self.write_channel_config("c", {"language": "en", "voice": {"voice_profile": "x"}})
        _write_json(self.projects / "p" / "job.json", {"language": "fr"})
        before = {path: path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
        self.resolve(channel_id="c", project_id="p", template_id="fullscreen_voiceover_v1", language="en")
        after = {path: path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
        self.assertEqual(before, after)

    def test_resolution_is_reproducible(self) -> None:
        self.write_channel_config("c", {"language": "en"})
        first = self.resolve(channel_id="c").to_dict(include_trace=True)
        second = self.resolve(channel_id="c").to_dict(include_trace=True)
        self.assertEqual(first, second)

    def test_resolver_holds_no_state_between_calls(self) -> None:
        from src.config_resolver import ConfigResolutionRequest, ConfigResolver, keys

        request = ConfigResolutionRequest(channels_dir=str(self.channels), include_secrets=False)
        resolver = ConfigResolver(request)
        self.write_channel_config("c", {"language": "en"})
        self.assertEqual(resolver.resolve().get(keys.KEY_LANGUAGE), "ru")


class ExplainOutputTests(_FixtureCase):
    def test_every_row_answers_value_and_origin(self) -> None:
        from src.config_resolver import keys

        self.write_channel_config("c", {"language": "en"})
        rows = self.resolve(channel_id="c").explain_rows()
        self.assertEqual(len(rows), len(keys.SETTINGS))
        for row in rows:
            self.assertTrue(row["value"])
            self.assertTrue(row["resolved_from"])
            self.assertTrue(row["resolved_from_display"])

    def test_origins_are_posix_paths_on_every_platform(self) -> None:
        """Origins are printed and stored, so a Windows run must not produce a different
        string from a POSIX one."""
        self.write_channel_config("c", {"language": "en"})
        _write_json(self.projects / "p" / "job.json", {"language": "fr"})
        resolved = self.resolve(channel_id="c", project_id="p", language="en")
        for value in resolved.values.values():
            self.assertNotIn("\\", value.origin, value.key)
        for layer in resolved.layers:
            self.assertNotIn("\\", layer.origin, layer.source)

    def test_layers_are_reported_weakest_first_with_a_reason_when_empty(self) -> None:
        from src.config_resolver import SOURCE_PROJECT_OVERRIDE

        self.write_channel_config("c", {})
        resolved = self.resolve(channel_id="c")
        priorities = [layer.priority for layer in resolved.layers]
        self.assertEqual(priorities, sorted(priorities))
        project_layer = next(layer for layer in resolved.layers if layer.source == SOURCE_PROJECT_OVERRIDE)
        self.assertTrue(project_layer.note)


class AdapterTests(_FixtureCase):
    def test_voice_adapter_leaves_unmentioned_fields_at_their_dataclass_default(self) -> None:
        from src.audio.voice_policy import VoicePolicy
        from src.config_resolver import to_voice_policy

        self.write_channel_config("c", {})
        policy = to_voice_policy(self.resolve(channel_id="c"))
        self.assertEqual(policy.pause_policy, VoicePolicy().pause_policy)
        self.assertEqual(policy.notes, VoicePolicy().notes)

    def test_render_adapter_returns_the_shape_the_renderers_use(self) -> None:
        from src.config_resolver import to_render_settings

        settings = to_render_settings(self.resolve(format_id="vertical_short"))
        self.assertEqual(settings, {"width": 1080, "height": 1920, "fps": 30, "aspect_ratio": "9:16"})


class ExplainCliTests(unittest.TestCase):
    """The acceptance criterion: `channels show --explain` prints the table and changes nothing."""

    def _run(self, argv: list[str]) -> tuple[int, str]:
        import contextlib
        import io

        from src.content_creation.cli import build_parser, run_content_creation_cli

        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = run_content_creation_cli(build_parser().parse_args(argv))
        return code, buffer.getvalue()

    def test_explain_prints_value_and_source_for_a_real_channel(self) -> None:
        code, output = self._run(
            ["channels", "show", "--channel", "nature_science_news_ru", "--explain"]
        )
        self.assertEqual(code, 0)
        self.assertIn("voice.voice_profile", output)
        self.assertIn("ru_dom", output)
        self.assertIn("channel_config", output)

    def test_explain_json_carries_resolved_from_for_every_key(self) -> None:
        from src.config_resolver import keys

        code, output = self._run(
            ["channels", "show", "--channel", "nature_science_news_ru", "--explain", "--json"]
        )
        self.assertEqual(code, 0)
        data = json.loads(output)
        self.assertEqual(sorted(data["values"]), sorted(keys.list_keys()))
        for value in data["values"].values():
            self.assertTrue(value["resolved_from"])

    def test_explain_json_redacts_every_secret(self) -> None:
        from src.config_resolver import REDACTED, keys

        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "sk-cli-secret"}, clear=False):
            code, output = self._run(
                ["channels", "show", "--channel", "nature_pulse", "--explain", "--json", "--trace"]
            )
        self.assertEqual(code, 0)
        self.assertNotIn("sk-cli-secret", output)
        self.assertEqual(json.loads(output)["values"][keys.KEY_SECRET_OPENAI]["value"], REDACTED)

    def test_explain_reports_unknown_channel_without_a_traceback(self) -> None:
        code, output = self._run(["channels", "show", "--channel", "no_such_channel", "--explain"])
        self.assertEqual(code, 1)
        self.assertIn("no_such_channel", output)

    def test_channels_show_without_explain_is_unchanged(self) -> None:
        from src.content_creation import capabilities

        code, output = self._run(["channels", "show", "--channel", "nature_pulse", "--json"])
        self.assertEqual(code, 0)
        expected = next(c for c in capabilities.list_channels() if c["channel_id"] == "nature_pulse")
        self.assertEqual(json.loads(output), expected)


if __name__ == "__main__":
    unittest.main()
