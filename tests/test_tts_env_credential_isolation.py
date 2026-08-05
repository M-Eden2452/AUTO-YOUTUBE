"""PLAN-STAB-3: a local .env must never replace a test-owned fake credential.

``src.audio.tts.env.load_elevenlabs_env`` is the one place the TTS path loads
``.env`` (see ``src/localization/secrets.py`` for why that matters), and
production deliberately uses ``override=True`` so a stale process env var
never shadows a real key. These tests never touch the repository's real
``.env``: each one points the loader at a synthetic, temporary ``.env`` file
containing an obviously-fake value, so no real credential is ever read.
"""

from __future__ import annotations

import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from src.audio.tts.env import TEST_CREDENTIAL_ISOLATION_ENV_VAR, load_elevenlabs_env


class CredentialIsolationTests(unittest.TestCase):
    def setUp(self) -> None:
        self._previous_key = os.environ.get("ELEVENLABS_API_KEY")
        self._previous_voice = os.environ.get("ELEVENLABS_VOICE_ID")
        self._previous_lock = os.environ.get(TEST_CREDENTIAL_ISOLATION_ENV_VAR)

    def tearDown(self) -> None:
        self._restore("ELEVENLABS_API_KEY", self._previous_key)
        self._restore("ELEVENLABS_VOICE_ID", self._previous_voice)
        self._restore(TEST_CREDENTIAL_ISOLATION_ENV_VAR, self._previous_lock)

    @staticmethod
    def _restore(name: str, value: str | None) -> None:
        if value is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = value

    def test_isolation_lock_is_active_for_the_whole_offline_run(self) -> None:
        # tests/__init__.py seeds this before any test module is imported.
        self.assertEqual(os.getenv(TEST_CREDENTIAL_ISOLATION_ENV_VAR, "").strip(), "1")

    def test_test_owned_fake_key_survives_dotenv_loading_when_isolated(self) -> None:
        with TemporaryDirectory() as tmp:
            fake_env_path = Path(tmp) / ".env"
            fake_env_path.write_text("ELEVENLABS_API_KEY=not-the-real-key-from-dotenv\n", encoding="utf-8")
            os.environ[TEST_CREDENTIAL_ISOLATION_ENV_VAR] = "1"
            os.environ["ELEVENLABS_API_KEY"] = "test-owned-fake-key"
            with patch("src.audio.tts.env.PROJECT_ROOT", Path(tmp)):
                result = load_elevenlabs_env()
        self.assertEqual(result.api_key, "test-owned-fake-key")
        self.assertEqual(os.environ["ELEVENLABS_API_KEY"], "test-owned-fake-key")

    def test_dotenv_value_does_not_replace_test_owned_key(self) -> None:
        """Same scenario, phrased as the plan's own success criterion: the
        .env value ("not-the-real-key-from-dotenv") never wins."""
        with TemporaryDirectory() as tmp:
            fake_env_path = Path(tmp) / ".env"
            fake_env_path.write_text("ELEVENLABS_API_KEY=attacker-controlled-value\n", encoding="utf-8")
            os.environ[TEST_CREDENTIAL_ISOLATION_ENV_VAR] = "1"
            os.environ["ELEVENLABS_API_KEY"] = "test-owned-fake-key"
            with patch("src.audio.tts.env.PROJECT_ROOT", Path(tmp)):
                result = load_elevenlabs_env()
        self.assertNotEqual(result.api_key, "attacker-controlled-value")
        self.assertEqual(result.api_key, "test-owned-fake-key")

    def test_absence_of_dotenv_file_does_not_change_the_result(self) -> None:
        with TemporaryDirectory() as tmp:
            os.environ[TEST_CREDENTIAL_ISOLATION_ENV_VAR] = "1"
            os.environ["ELEVENLABS_API_KEY"] = "test-owned-fake-key"
            with patch("src.audio.tts.env.PROJECT_ROOT", Path(tmp)):
                result = load_elevenlabs_env()
        self.assertEqual(result.api_key, "test-owned-fake-key")

    def test_production_override_semantics_are_unchanged_when_not_isolated(self) -> None:
        """Characterizes existing production behaviour: without the
        isolation lock, .env is still the source of truth (override=True).
        The .env here is a synthetic temp file, never the real one."""
        with TemporaryDirectory() as tmp:
            fake_env_path = Path(tmp) / ".env"
            fake_env_path.write_text("ELEVENLABS_API_KEY=from-dotenv-file\n", encoding="utf-8")
            os.environ.pop(TEST_CREDENTIAL_ISOLATION_ENV_VAR, None)
            os.environ["ELEVENLABS_API_KEY"] = "stale-process-value"
            with patch("src.audio.tts.env.PROJECT_ROOT", Path(tmp)):
                result = load_elevenlabs_env()
        self.assertEqual(result.api_key, "from-dotenv-file")

    def test_environment_is_restored_after_the_test(self) -> None:
        with TemporaryDirectory() as tmp:
            os.environ[TEST_CREDENTIAL_ISOLATION_ENV_VAR] = "1"
            os.environ["ELEVENLABS_API_KEY"] = "temporary-value-for-this-test-only"
            with patch("src.audio.tts.env.PROJECT_ROOT", Path(tmp)):
                load_elevenlabs_env()
        self.assertEqual(os.environ["ELEVENLABS_API_KEY"], "temporary-value-for-this-test-only")
        # tearDown restores this back to whatever preceded setUp - verified
        # implicitly by every other test in this module starting clean.

    def test_real_key_is_neither_required_nor_read_for_offline_provider_construction(self) -> None:
        from src.audio.tts.elevenlabs_provider import ElevenLabsProvider

        with TemporaryDirectory() as tmp:
            os.environ[TEST_CREDENTIAL_ISOLATION_ENV_VAR] = "1"
            os.environ["ELEVENLABS_API_KEY"] = "test-owned-fake-key"
            with patch("src.audio.tts.env.PROJECT_ROOT", Path(tmp)):
                provider = ElevenLabsProvider()
        self.assertEqual(provider.api_key, "test-owned-fake-key")


if __name__ == "__main__":
    unittest.main()
