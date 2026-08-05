from __future__ import annotations

import os

from src.audio.tts.env import TEST_CREDENTIAL_ISOLATION_ENV_VAR

from .network_guard import install_network_guard


# Seed a test-owned fake credential and lock credential isolation before any
# test module can import code that constructs a TTS provider. This guarantees
# a local .env can never override it (see src.audio.tts.env) and that no test
# ever needs, reads or displays a real ELEVENLABS_API_KEY.
os.environ[TEST_CREDENTIAL_ISOLATION_ENV_VAR] = "1"
os.environ["ELEVENLABS_API_KEY"] = "test-fake-elevenlabs-key-not-real"

install_network_guard()

