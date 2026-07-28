"""D2/E2: the resolved localization must decide the voice, and must decide it the
same way everywhere.

Two kinds of test live here:

* **characterization** - for every channel really on disk, the resolved localization
  produces the same voice selection the pre-D2 reader produced. If one of these
  fails, behaviour has changed, and D2 is not allowed to change behaviour.
* **the gaps D2 closes** - the ``languages.<lang>.voice`` block is now read, a
  missing credential now picks the declared fallback instead of reaching the network,
  narration that already exists is reused instead of overwritten, and a voice profile
  of the wrong language is an explicit error instead of a silent Russian voice.

No network, no TTS, no Vision, no downloads, no paid API: the secret probe is always
injected, providers are never instantiated for synthesis, and the network guard is
installed around every test that touches the voice stage.
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
import wave
from pathlib import Path

from tests.network_guard import install_network_guard, uninstall_network_guard

CHANNELS_DIR = Path("channels")
NEWS_TEMPLATE = "fullscreen_voiceover_v1"
NEWS_FORMAT = "vertical_short"

_NO_SECRET = lambda env_var: False  # noqa: E731 - подставляемая проверка «ключ настроен»
_HAS_SECRET = lambda env_var: True  # noqa: E731

_VOICES_YAML = """
voices:
  ru_voice:
    display_name: Русский голос
    provider: elevenlabs
    voice_id: ru-voice-id
    model_id: eleven_multilingual_v2
    language: ru
    enabled: true
    settings:
      stability: 0.5
  en_voice:
    display_name: English voice
    provider: elevenlabs
    voice_id: en-voice-id
    model_id: eleven_multilingual_v2
    language: en
    enabled: true
"""

_CHANNEL_CONFIG = {
    "channel_id": "twolang",
    "mode": "news_to_short",
    "language": "ru",
    "voice": {
        "provider": "elevenlabs",
        "voice_profile": "ru_voice",
        "voice_id": "ru-voice-id",
        "model": "eleven_multilingual_v2",
        "settings": {"stability": 0.5},
    },
    "languages": {
        "ru": {"enabled": True, "script_locale": "ru-RU", "voice": {"voice_profile": "ru_voice"}},
        "en": {"enabled": True, "script_locale": "en-US", "voice": {"voice_profile": "en_voice"}},
    },
}


def _real_channel_ids() -> list[str]:
    if not CHANNELS_DIR.is_dir():
        return []
    return [
        entry.name
        for entry in sorted(CHANNELS_DIR.iterdir())
        if entry.is_dir() and ((entry / "channel.json").is_file() or (entry / "channel_config.json").is_file())
    ]


class _TwoLanguageChannel:
    """A channels/ tree with one channel that really has two language voices.

    Written to a tempdir and made current, so no file in the repository's own
    channels/ or projects/ is read or touched by these tests.
    """

    def __enter__(self) -> Path:
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        channel_dir = root / "channels" / "twolang"
        channel_dir.mkdir(parents=True)
        (channel_dir / "channel_config.json").write_text(
            json.dumps(_CHANNEL_CONFIG, ensure_ascii=False), encoding="utf-8"
        )
        (channel_dir / "voices.yaml").write_text(_VOICES_YAML, encoding="utf-8")
        self._previous = Path.cwd()
        os.chdir(root)
        return root

    def __exit__(self, *exc) -> None:
        os.chdir(self._previous)
        self._tmp.cleanup()


def _resolve(**kwargs):
    from src.localization import resolve_localization

    kwargs.setdefault("template_id", NEWS_TEMPLATE)
    kwargs.setdefault("format_id", NEWS_FORMAT)
    kwargs.setdefault("secret_probe", _NO_SECRET)
    if kwargs.get("channel_id") == "twolang":
        kwargs.setdefault("channels_dir", str(Path.cwd() / "channels"))
    return resolve_localization(**kwargs)


def _write_wav(path: Path, seconds: float = 1.0) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(8000)
        handle.writeframes(b"\x00\x00" * int(8000 * seconds))


def _script() -> dict:
    return {
        "narration_text": "Первое предложение. Второе предложение.",
        "scenes": [
            {"scene_id": "scene_001", "text": "Первое предложение.", "target_duration_sec": 3.0},
            {"scene_id": "scene_002", "text": "Второе предложение.", "target_duration_sec": 3.0},
        ],
    }


class LanguageNormalizationTests(unittest.TestCase):
    def test_aliases_and_locales_normalize(self) -> None:
        from src.localization import default_locale, normalize_language, normalize_locale

        cases = {
            "ru": "ru",
            "ru-RU": "ru",
            "ru_RU": "ru",
            "Russian": "ru",
            "русский": "ru",
            "RU": "ru",
            "en": "en",
            "en-US": "en",
            "English": "en",
            "es-MX": "es",
        }
        for raw, expected in cases.items():
            with self.subTest(language=raw):
                self.assertEqual(normalize_language(raw), expected)
        self.assertEqual(normalize_language("klingon"), "")
        self.assertEqual(default_locale("ru"), "ru-RU")
        self.assertEqual(normalize_locale("", language="en"), "en-US")
        self.assertEqual(normalize_locale("ru_ru"), "ru-RU")
        self.assertEqual(normalize_locale("pt-br"), "pt-BR")

    def test_ui_language_list_comes_from_the_same_table(self) -> None:
        """One list of languages, not two: the UI list must be the locales table."""
        from src.content_creation import languages
        from src.localization import locales

        self.assertEqual(
            [item["code"] for item in languages.list_languages()],
            [item.code for item in locales.LANGUAGE_DEFINITIONS],
        )
        self.assertEqual(languages.display_name("ru-RU"), "Русский")
        self.assertTrue(languages.is_known_language("Russian"))

    def test_localization_id_is_never_renamed(self) -> None:
        """Нормализация - только про ответ «какой это язык». Папка остаётся своей,
        иначе старый проект перестал бы находить свои файлы."""
        resolved = _resolve(channel_id="nature_science_news_ru", language="ru-RU")
        self.assertEqual(resolved.localization_id, "ru-RU")
        self.assertEqual(resolved.language, "ru")
        self.assertEqual(resolved.locale, "ru-RU")


class VoiceSelectionParityTests(unittest.TestCase):
    """The pre-D2 selection block and the resolved one must agree."""

    def test_every_configured_channel_keeps_its_voice_selection(self) -> None:
        from src.news.pipeline import _load_channel_voice_config
        from src.news.voice_stage import _legacy_selection

        checked = 0
        for channel_id in _real_channel_ids():
            channel_voice = _load_channel_voice_config(channel_id)
            if not channel_voice:
                continue  # каналы без блока voice сравнивать не с чем
            with self.subTest(channel=channel_id):
                resolved = _resolve(channel_id=channel_id, language="ru")
                self.assertEqual(resolved.voice_selection(), _legacy_selection("ru", channel_voice))
                checked += 1
        self.assertTrue(checked, "Ни один канал не имеет блока voice - тест бессмысленен.")

    def test_policy_matches_the_pre_d2_voice_policy(self) -> None:
        from src.news.pipeline import _load_channel_voice_config, _load_channel_workflow_config
        from src.news.voice_adapter import resolve_voice_policy_for_channel

        import dataclasses

        for channel_id in _real_channel_ids():
            with self.subTest(channel=channel_id):
                expected = resolve_voice_policy_for_channel(
                    _load_channel_voice_config(channel_id), _load_channel_workflow_config(channel_id)
                )
                resolved = _resolve(channel_id=channel_id, language="ru")
                for field in dataclasses.fields(expected):
                    self.assertEqual(
                        getattr(expected, field.name),
                        getattr(resolved.policy, field.name),
                        f"{channel_id}: {field.name}",
                    )

    def test_resolution_is_deterministic(self) -> None:
        first = _resolve(channel_id="nature_science_news_ru", language="ru")
        second = _resolve(channel_id="nature_science_news_ru", language="ru")
        self.assertEqual(first.to_dict(), second.to_dict())


class PriorityTests(unittest.TestCase):
    """The D1 layer order must be exactly what D1 left behind."""

    def test_d1_priority_order_is_unchanged(self) -> None:
        from src.config_resolver.models import SOURCE_PRIORITY

        self.assertEqual(
            [source for source, _ in sorted(SOURCE_PRIORITY.items(), key=lambda item: item[1])],
            [
                "global_default",
                "format_policy",
                "channel_profile",
                "channel_config",
                "template_policy",
                "project_override",
                "localization_override",
                "runtime_override",
                "environment",
            ],
        )

    def test_template_policy_still_overrides_channel_config(self) -> None:
        """Совместимость D1: шаблон выше канала. D2 это не меняет - только объясняет."""
        from src.config_resolver.models import SOURCE_TEMPLATE_POLICY, WARNING_TEMPLATE_OVER_CHANNEL

        resolved = _resolve(channel_id="nature_science_news_ru", language="ru")
        fallback = resolved.config.resolved("voice.fallback_policy")
        self.assertEqual(fallback.source, SOURCE_TEMPLATE_POLICY)
        self.assertEqual(fallback.value, "manual_audio")
        self.assertIn(WARNING_TEMPLATE_OVER_CHANNEL, fallback.warnings)

    def test_localization_override_wins_over_channel_config(self) -> None:
        from src.config_resolver.models import SOURCE_LOCALIZATION_OVERRIDE

        with _TwoLanguageChannel():
            english = _resolve(channel_id="twolang", language="en")
            self.assertEqual(english.voice_profile_id, "en_voice")
            self.assertEqual(english.resolved_voice_id, "en-voice-id")
            self.assertEqual(
                english.config.source_of("voice.voice_profile"), SOURCE_LOCALIZATION_OVERRIDE
            )
            russian = _resolve(channel_id="twolang", language="ru")
            self.assertEqual(russian.voice_profile_id, "ru_voice")
            self.assertEqual(russian.resolved_voice_id, "ru-voice-id")

    def test_runtime_override_wins_over_localization_override(self) -> None:
        from src.config_resolver.models import SOURCE_RUNTIME_OVERRIDE

        with _TwoLanguageChannel():
            resolved = _resolve(channel_id="twolang", language="ru", voice_profile_override="ru_voice")
            self.assertEqual(resolved.config.source_of("voice.voice_profile"), SOURCE_RUNTIME_OVERRIDE)
            self.assertEqual(resolved.voice_profile_id, "ru_voice")


class SecretTests(unittest.TestCase):
    def test_secret_is_only_ever_a_boolean(self) -> None:
        secret = "sk-do-not-leak-4242"
        previous = os.environ.get("ELEVENLABS_API_KEY")
        os.environ["ELEVENLABS_API_KEY"] = secret
        try:
            from src.localization import is_secret_configured

            self.assertIs(is_secret_configured("ELEVENLABS_API_KEY"), True)
            resolved = _resolve(
                channel_id="nature_science_news_ru", language="ru", secret_probe=is_secret_configured
            )
            self.assertTrue(resolved.secret_configured)
            payload = json.dumps(
                resolved.to_dict(include_config=True, include_trace=True), ensure_ascii=False, default=str
            )
            self.assertNotIn(secret, payload)
            self.assertNotIn(secret, json.dumps([row for row in resolved.explain_rows()], default=str))
        finally:
            if previous is None:
                os.environ.pop("ELEVENLABS_API_KEY", None)
            else:
                os.environ["ELEVENLABS_API_KEY"] = previous

    def test_missing_secret_applies_the_declared_fallback_without_network(self) -> None:
        from src.localization import NARRATION_SOURCE_MANUAL_AUDIO, STATUS_AWAITING_SOURCE

        install_network_guard()
        try:
            resolved = _resolve(channel_id="nature_science_news_ru", language="ru", secret_probe=_NO_SECRET)
        finally:
            uninstall_network_guard()
        self.assertEqual(resolved.fallback_policy, "manual_audio")
        self.assertTrue(resolved.fallback_applied)
        self.assertEqual(resolved.narration_source, NARRATION_SOURCE_MANUAL_AUDIO)
        self.assertEqual(resolved.status, STATUS_AWAITING_SOURCE)
        self.assertFalse(resolved.tts_allowed)
        self.assertEqual(resolved.tts_blocked_reason, "secret_missing")
        # Голос при fallback не подменяется - меняется только источник звука.
        self.assertEqual(resolved.voice_profile_id, "ru_dom")
        self.assertIn("ELEVENLABS_API_KEY", resolved.fallback_reason)

    def test_configured_secret_allows_generation_after_approval(self) -> None:
        from src.localization import NARRATION_SOURCE_TTS, STATUS_READY_FOR_GENERATION

        resolved = _resolve(channel_id="nature_science_news_ru", language="ru", secret_probe=_HAS_SECRET)
        self.assertEqual(resolved.narration_source, NARRATION_SOURCE_TTS)
        self.assertEqual(resolved.status, STATUS_READY_FOR_GENERATION)
        self.assertTrue(resolved.tts_allowed)
        self.assertFalse(resolved.fallback_applied)

    def test_secret_in_stored_config_is_an_error(self) -> None:
        from src.localization import validate_stored_localization_config

        issues = validate_stored_localization_config(
            {"voice": {"provider": "elevenlabs", "api_key": "sk-oops"}}, localization_id="ru"
        )
        self.assertTrue(issues)
        self.assertEqual(issues[0].code, "secret_in_config")
        self.assertNotIn("sk-oops", issues[0].message)


class NarrationSourceTests(unittest.TestCase):
    def test_manual_audio_does_not_call_tts(self) -> None:
        from src.localization import NARRATION_SOURCE_MANUAL_AUDIO, STATUS_MANUAL_AUDIO_READY

        install_network_guard()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                manual = Path(tmp) / "manual.wav"
                _write_wav(manual)
                resolved = _resolve(
                    channel_id="nature_science_news_ru",
                    language="ru",
                    project_root=tmp,
                    manual_audio_path=str(manual),
                    secret_probe=_HAS_SECRET,
                )
        finally:
            uninstall_network_guard()
        self.assertEqual(resolved.narration_source, NARRATION_SOURCE_MANUAL_AUDIO)
        self.assertEqual(resolved.status, STATUS_MANUAL_AUDIO_READY)
        self.assertFalse(resolved.tts_allowed)
        self.assertEqual(resolved.tts_blocked_reason, "manual_audio_source")

    def test_missing_manual_audio_file_is_an_error(self) -> None:
        resolved = _resolve(
            channel_id="nature_science_news_ru", language="ru", manual_audio_path="no/such/file.wav"
        )
        self.assertFalse(resolved.valid)
        self.assertIn("manual_audio_missing", [issue.code for issue in resolved.errors])

    def test_existing_artifact_is_reused_and_does_not_call_tts(self) -> None:
        from src.localization import NARRATION_SOURCE_EXISTING_ARTIFACT, STATUS_COMPLETED

        install_network_guard()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                narration = root / "localizations" / "ru" / "voice" / "narration.wav"
                _write_wav(narration)
                _write_manifest(root, "ru", {"status": "completed", "audio_path": str(narration), "language": "ru"})
                resolved = _resolve(
                    channel_id="nature_science_news_ru",
                    language="ru",
                    project_root=root,
                    secret_probe=_HAS_SECRET,
                )
        finally:
            uninstall_network_guard()
        self.assertEqual(resolved.narration_source, NARRATION_SOURCE_EXISTING_ARTIFACT)
        self.assertEqual(resolved.status, STATUS_COMPLETED)
        self.assertTrue(resolved.reuse_existing_narration)
        self.assertFalse(resolved.tts_allowed)
        self.assertEqual(resolved.existing_narration_path, str(narration))

    def test_manifest_pointing_at_a_deleted_file_is_not_finished_narration(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_manifest(
                root, "ru", {"status": "completed", "audio_path": str(root / "gone.wav"), "language": "ru"}
            )
            resolved = _resolve(
                channel_id="nature_science_news_ru", language="ru", project_root=root, secret_probe=_HAS_SECRET
            )
        self.assertEqual(resolved.existing_narration_path, "")
        self.assertFalse(resolved.reuse_existing_narration)

    def test_existing_artifact_of_another_language_is_not_reused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            narration = root / "localizations" / "ru" / "voice" / "narration.wav"
            _write_wav(narration)
            _write_manifest(root, "ru", {"status": "completed", "audio_path": str(narration), "language": "en"})
            resolved = _resolve(
                channel_id="nature_science_news_ru", language="ru", project_root=root, secret_probe=_HAS_SECRET
            )
        self.assertFalse(resolved.reuse_existing_narration)
        self.assertIn(
            "existing_narration_language_mismatch", [issue.code for issue in resolved.errors]
        )

    def test_existing_artifact_of_another_profile_warns_but_is_reused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            narration = root / "localizations" / "ru" / "voice" / "narration.wav"
            _write_wav(narration)
            _write_manifest(
                root,
                "ru",
                {
                    "status": "completed",
                    "audio_path": str(narration),
                    "language": "ru",
                    "voice_profile": "some_other_voice",
                },
            )
            resolved = _resolve(
                channel_id="nature_science_news_ru", language="ru", project_root=root, secret_probe=_HAS_SECRET
            )
        self.assertTrue(resolved.reuse_existing_narration)
        self.assertIn(
            "existing_narration_profile_mismatch", [issue.code for issue in resolved.warnings]
        )

    def test_exactly_one_narration_source_is_active(self) -> None:
        from src.localization import validate_localization_set

        with tempfile.TemporaryDirectory() as tmp:
            manual = Path(tmp) / "manual.wav"
            _write_wav(manual)
            resolved = _resolve(
                channel_id="nature_science_news_ru",
                language="ru",
                project_root=tmp,
                manual_audio_path=str(manual),
                secret_probe=_HAS_SECRET,
            )
        issues = validate_localization_set([resolved])
        self.assertNotIn("multiple_active_narration_sources", [issue.code for issue in issues])


class VoiceStageTests(unittest.TestCase):
    """The stage that actually writes voice_manifest.json."""

    def test_resolved_selection_is_written_into_the_stub_manifest(self) -> None:
        install_network_guard()
        try:
            with _TwoLanguageChannel(), tempfile.TemporaryDirectory() as tmp:
                from src.news.voice_stage import build_safe_voice_manifest

                resolved = _resolve(channel_id="twolang", language="en", project_root=tmp)
                manifest = build_safe_voice_manifest(
                    project_root=tmp, language="en", script=_script(), localization=resolved
                )
        finally:
            uninstall_network_guard()
        self.assertEqual(manifest["selection"]["voice_profile"], "en_voice")
        self.assertEqual(manifest["selection"]["voice_id"], "en-voice-id")
        self.assertEqual(manifest["locale"], "en-US")
        # Статус стадии не меняется: это по-прежнему «ничего не сгенерировано».
        self.assertEqual(manifest["status"], "provider_selection_required")
        self.assertEqual(manifest["localization_status"], "provider_selection_required")
        self.assertEqual(manifest["narration_source"], "manual_audio")
        self.assertIs(manifest["secret_configured"], False)

    def test_stage_status_strings_are_existing_voice_states(self) -> None:
        """D2 не заводит новый словарь статусов."""
        from src.audio.narration_workflow import EXTENDED_VOICE_STATES
        from src.localization import models

        for status in (
            models.STATUS_AWAITING_SOURCE,
            models.STATUS_BLOCKED,
            models.STATUS_COMPLETED,
            models.STATUS_MANUAL_AUDIO_READY,
            models.STATUS_READY_FOR_GENERATION,
            models.STATUS_SKIPPED,
        ):
            with self.subTest(status=status):
                self.assertIn(status, EXTENDED_VOICE_STATES)

    def test_existing_narration_is_not_overwritten_by_the_stage(self) -> None:
        """Защита B3: повторный проход стадии не превращает готовый манифест в заглушку."""
        install_network_guard()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                from src.news.voice_stage import build_or_generate_voice_manifest

                root = Path(tmp)
                narration = root / "localizations" / "ru" / "voice" / "narration.wav"
                _write_wav(narration)
                manifest_path = _write_manifest(
                    root,
                    "ru",
                    {
                        "status": "completed",
                        "voice_stage_status": "completed",
                        "audio_path": str(narration),
                        "language": "ru",
                        "voice_profile": "ru_dom",
                    },
                )
                before = manifest_path.read_bytes()
                resolved = _resolve(
                    channel_id="nature_science_news_ru",
                    language="ru",
                    project_root=root,
                    secret_probe=_HAS_SECRET,
                )
                returned = build_or_generate_voice_manifest(
                    project_root=root,
                    language="ru",
                    script=_script(),
                    channel_id="nature_science_news_ru",
                    job_id="job_001",
                    execute=False,
                    localization=resolved,
                )
                self.assertEqual(manifest_path.read_bytes(), before)
                self.assertEqual(returned["status"], "completed")
                self.assertEqual(returned["audio_path"], str(narration))
        finally:
            uninstall_network_guard()

    def test_execute_without_secret_never_reaches_a_provider(self) -> None:
        install_network_guard()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                from src.news.voice_stage import build_or_generate_voice_manifest

                resolved = _resolve(
                    channel_id="nature_science_news_ru",
                    language="ru",
                    project_root=tmp,
                    secret_probe=_NO_SECRET,
                )
                manifest = build_or_generate_voice_manifest(
                    project_root=tmp,
                    language="ru",
                    script=_script(),
                    channel_id="nature_science_news_ru",
                    job_id="job_001",
                    execute=True,
                    localization=resolved,
                )
        finally:
            uninstall_network_guard()
        self.assertEqual(manifest["status"], "provider_selection_required")
        self.assertIs(manifest["paid_call_performed"], False)
        self.assertEqual(manifest["tts_blocked_reason"], "secret_missing")

    def test_legacy_signature_still_produces_the_pre_d2_manifest(self) -> None:
        """Старая подпись (без localization) работает и даёт прежний результат."""
        from src.news.pipeline import _load_channel_voice_config
        from src.news.voice_stage import build_or_generate_voice_manifest, build_safe_voice_manifest

        channel_voice = _load_channel_voice_config("nature_science_news_ru")
        with tempfile.TemporaryDirectory() as one, tempfile.TemporaryDirectory() as two:
            baseline = build_safe_voice_manifest(
                project_root=one, language="ru", script=_script(), channel_voice_config=channel_voice
            )
            adapted = build_or_generate_voice_manifest(
                project_root=two,
                language="ru",
                script=_script(),
                channel_voice_config=channel_voice,
                channel_id="nature_science_news_ru",
                job_id="job_001",
                execute=False,
            )
        self.assertEqual(baseline, adapted)
        self.assertNotIn("localization_status", baseline)


class ValidationTests(unittest.TestCase):
    def test_voice_profile_of_the_wrong_language_is_a_clear_error(self) -> None:
        resolved = _resolve(channel_id="nature_science_news_ru", language="en")
        codes = [issue.code for issue in resolved.errors]
        self.assertIn("voice_profile_language_mismatch", codes)
        message = next(issue.message for issue in resolved.errors if issue.code == "voice_profile_language_mismatch")
        self.assertIn("languages.en.voice", message)
        self.assertFalse(resolved.tts_allowed)

    def test_unknown_provider_is_a_clear_error(self) -> None:
        resolved = _resolve(
            channel_id="nature_science_news_ru", language="ru", voice_provider_override="totally_made_up"
        )
        self.assertIn("unknown_provider", [issue.code for issue in resolved.errors])

    def test_unknown_language_is_reported_but_still_resolves(self) -> None:
        resolved = _resolve(channel_id="nature_science_news_ru", language="klingon")
        self.assertIn("unknown_language", [issue.code for issue in resolved.warnings])
        self.assertEqual(resolved.localization_id, "klingon")

    def test_unresolvable_voice_profile_is_a_clear_error(self) -> None:
        with _TwoLanguageChannel():
            resolved = _resolve(
                channel_id="twolang", language="ru", voice_profile_override="does_not_exist"
            )
        self.assertIn("voice_profile_not_found", [issue.code for issue in resolved.errors])

    def test_local_tts_fallback_reports_that_no_local_provider_exists(self) -> None:
        from src.audio.voice_policy import FALLBACK_POLICY_LOCAL_TTS
        from src.config_resolver import keys as k

        resolved = _resolve(
            channel_id="nature_science_news_ru",
            language="ru",
            overrides={k.KEY_VOICE_FALLBACK_POLICY: FALLBACK_POLICY_LOCAL_TTS},
            secret_probe=_NO_SECRET,
        )
        self.assertIn("local_tts_unavailable", [issue.code for issue in resolved.errors])
        self.assertEqual(resolved.tts_blocked_reason, "local_tts_unavailable")

    def test_fallback_none_blocks_instead_of_switching_silently(self) -> None:
        from src.audio.voice_policy import FALLBACK_POLICY_NONE
        from src.config_resolver import keys as k
        from src.localization import STATUS_BLOCKED

        resolved = _resolve(
            channel_id="nature_science_news_ru",
            language="ru",
            overrides={k.KEY_VOICE_FALLBACK_POLICY: FALLBACK_POLICY_NONE},
            secret_probe=_NO_SECRET,
        )
        self.assertEqual(resolved.status, STATUS_BLOCKED)
        self.assertIn("fallback_unavailable", [issue.code for issue in resolved.errors])

    def test_a_path_outside_the_project_is_a_warning(self) -> None:
        from src.localization import validate_local_path

        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(validate_local_path("voice/manual.wav", project_root=tmp), [])
            issues = validate_local_path("../../elsewhere.wav", project_root=tmp)
        self.assertEqual([issue.code for issue in issues], ["path_outside_project"])


class MultipleLocalizationTests(unittest.TestCase):
    def test_each_language_gets_its_own_voice_and_output_path(self) -> None:
        from src.localization import validate_localization_set

        with _TwoLanguageChannel(), tempfile.TemporaryDirectory() as tmp:
            russian = _resolve(channel_id="twolang", language="ru", project_root=tmp)
            english = _resolve(channel_id="twolang", language="en", project_root=tmp)

        self.assertEqual(russian.voice_profile_id, "ru_voice")
        self.assertEqual(english.voice_profile_id, "en_voice")
        self.assertEqual(russian.locale, "ru-RU")
        self.assertEqual(english.locale, "en-US")
        self.assertNotEqual(russian.narration_output_path, english.narration_output_path)
        self.assertIn("localizations", russian.narration_output_path)
        self.assertEqual(validate_localization_set([russian, english]), list(russian.issues) + list(english.issues))

    def test_two_localizations_sharing_an_output_path_is_an_error(self) -> None:
        import dataclasses

        from src.localization import validate_localization_set

        with _TwoLanguageChannel(), tempfile.TemporaryDirectory() as tmp:
            russian = _resolve(channel_id="twolang", language="ru", project_root=tmp)
            english = _resolve(channel_id="twolang", language="en", project_root=tmp)
        collided = dataclasses.replace(english, narration_output_path=russian.narration_output_path)
        issues = validate_localization_set([russian, collided])
        self.assertIn("duplicate_narration_output_path", [issue.code for issue in issues])

    def test_duplicate_localization_id_is_an_error(self) -> None:
        from src.localization import validate_localization_set

        with _TwoLanguageChannel(), tempfile.TemporaryDirectory() as tmp:
            russian = _resolve(channel_id="twolang", language="ru", project_root=tmp)
        issues = validate_localization_set([russian, russian])
        self.assertIn("duplicate_localization_id", [issue.code for issue in issues])

    def test_job_model_already_carries_several_localization_entries(self) -> None:
        from src.news.models import NewsJob

        job = NewsJob.create(channel_id="nature_science_news_ru", input_mode="topic", topic="тема", language="ru")
        self.assertEqual(sorted(job.localizations), ["en", "es", "ru"])
        self.assertTrue(job.localizations["ru"].enabled)
        self.assertFalse(job.localizations["en"].enabled)
        self.assertEqual(job.localizations["en"].script_locale, "en-US")


class BackwardCompatibilityTests(unittest.TestCase):
    def test_pre_d2_manifest_without_new_fields_is_read(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            narration = root / "localizations" / "ru" / "voice" / "narration.wav"
            _write_wav(narration)
            # Ровно та форма, которую писал voice_stage до schema_version:
            # ни localization_id, ни narration_source, ни secret_configured.
            _write_manifest(
                root,
                "ru",
                {
                    "status": "completed",
                    "voice_stage_status": "completed",
                    "audio_path": str(narration),
                    "language": "ru",
                },
            )
            resolved = _resolve(
                channel_id="nature_science_news_ru", language="ru", project_root=root, secret_probe=_HAS_SECRET
            )
        self.assertTrue(resolved.reuse_existing_narration)
        self.assertTrue(resolved.valid)

    def test_real_projects_on_disk_are_readable_and_untouched(self) -> None:
        """Исторические проекты читаются read-only и не изменяются."""
        from src.projects.repository import ProjectRepository

        projects_dir = Path("projects")
        if not projects_dir.is_dir():
            self.skipTest("В репозитории нет папки projects/.")
        repository = ProjectRepository(projects_dir)
        checked = 0
        for entry in sorted(projects_dir.iterdir()):
            if not entry.is_dir():
                continue
            job_path = entry / "job.json"
            if not job_path.is_file():
                continue
            before = job_path.read_bytes()
            job = json.loads(before.decode("utf-8"))
            resolved = _resolve(
                channel_id=str(job.get("channel_id") or "nature_science_news_ru"),
                language=str(job.get("language") or "ru"),
                project_id=entry.name,
                project_root=entry,
                projects_dir=str(projects_dir),
            )
            self.assertTrue(resolved.localization_id)
            self.assertEqual(job_path.read_bytes(), before, f"{entry.name}: job.json изменился")
            self.assertIsNotNone(repository.detect_kind(entry.name))
            checked += 1
        self.assertTrue(checked, "Ни одного news-проекта на диске - тест бессмысленен.")


class WizardAndCliTests(unittest.TestCase):
    def test_wizard_offers_only_voices_of_the_chosen_language(self) -> None:
        from src.content_creation.wizard import _profiles_for_language

        profiles = [
            {"profile_id": "ru_voice", "language": "ru"},
            {"profile_id": "en_voice", "language": "en"},
            {"profile_id": "any_voice", "language": ""},
        ]
        self.assertEqual(
            [item["profile_id"] for item in _profiles_for_language(profiles, "en")],
            ["en_voice", "any_voice"],
        )
        self.assertEqual(
            [item["profile_id"] for item in _profiles_for_language(profiles, "ru-RU")],
            ["ru_voice", "any_voice"],
        )

    def test_cli_explain_is_read_only_and_hides_the_secret(self) -> None:
        import contextlib
        import io

        from src.content_creation.cli import main

        secret = "sk-cli-must-not-print-9999"
        previous = os.environ.get("ELEVENLABS_API_KEY")
        os.environ["ELEVENLABS_API_KEY"] = secret
        install_network_guard()
        buffer = io.StringIO()
        try:
            with contextlib.redirect_stdout(buffer):
                code = main(
                    ["voices", "explain", "--channel", "nature_science_news_ru", "--language", "ru", "--json"]
                )
        finally:
            uninstall_network_guard()
            if previous is None:
                os.environ.pop("ELEVENLABS_API_KEY", None)
            else:
                os.environ["ELEVENLABS_API_KEY"] = previous
        output = buffer.getvalue()
        self.assertEqual(code, 0)
        self.assertNotIn(secret, output)
        payload = json.loads(output)
        localization = payload["localizations"][0]
        self.assertEqual(localization["localization_id"], "ru")
        self.assertIs(localization["secret_configured"], True)
        self.assertEqual(localization["voice_profile_id"], "ru_dom")
        for value in payload["localizations"][0]["config"]["values"].values():
            if value["is_secret"]:
                self.assertEqual(value["value"], "***")

    def test_cli_explain_reports_an_error_localization_with_code_1(self) -> None:
        import contextlib
        import io

        from src.content_creation.cli import main

        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = main(["voices", "explain", "--channel", "nature_science_news_ru", "--language", "en"])
        output = buffer.getvalue()
        self.assertEqual(code, 1)
        self.assertIn("[error]", output)
        self.assertIn("languages.en.voice", output)
        self.assertIn("TTS будет вызван", output)


def _write_manifest(root: Path, localization_id: str, data: dict) -> Path:
    path = root / "localizations" / localization_id / "voice" / "voice_manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


if __name__ == "__main__":
    unittest.main()
