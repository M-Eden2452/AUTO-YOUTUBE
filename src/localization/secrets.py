"""Признак «секрет настроен» - и ничего кроме признака.

Ни одна функция здесь не возвращает, не логирует и не сохраняет значение ключа:
наружу выходит только ``bool``. Это тот же контракт, что у
``src.config_resolver`` (тип ``secret_presence``).

Зачем отдельный модуль, если слой окружения резолвера уже отдаёт этот бит.
``src/config_resolver/layers.environment_layer`` намеренно не открывает ``.env``:
для отчёта «что настроено в этом процессе» это правильно. Но решение о fallback
принимать по этому биту нельзя - ``ElevenLabsProvider.__init__`` загружает ``.env``
сам (``src.audio.tts.env.load_elevenlabs_env``), поэтому «ключ лежит в .env, но
процесс его ещё не загрузил» выглядело бы как «ключа нет» и включало бы fallback
там, где сегодня озвучка успешно генерируется. Проверка ниже повторяет ровно то,
что делает провайдер, и берёт от результата только ``bool``.
"""

from __future__ import annotations

import os
from typing import Callable

ELEVENLABS_API_KEY_ENV = "ELEVENLABS_API_KEY"

# Провайдер → переменная окружения с его ключом. Только провайдеры, реально
# зарегистрированные в TTSProviderManager (см. src/news/voice_stage.py):
# audio_file ключа не требует, поэтому его здесь нет.
PROVIDER_SECRET_ENV: dict[str, str] = {
    "elevenlabs": ELEVENLABS_API_KEY_ENV,
}

SecretPresenceProbe = Callable[[str], bool]


def secret_env_var(provider: str) -> str:
    """Переменная окружения, нужная провайдеру, или ``""`` если секрет не нужен."""
    return PROVIDER_SECRET_ENV.get(str(provider or "").strip(), "")


def is_secret_configured(env_var: str) -> bool:
    """Настроен ли секрет. Возвращает только признак, никогда - значение."""
    if not env_var:
        return False
    if (os.getenv(env_var) or "").strip():
        return True
    if env_var == ELEVENLABS_API_KEY_ENV:
        from src.audio.tts.env import load_elevenlabs_env

        # api_key_present - это bool; сама строка ключа отсюда не выходит.
        return load_elevenlabs_env().api_key_present
    return False


__all__ = [
    "ELEVENLABS_API_KEY_ENV",
    "PROVIDER_SECRET_ENV",
    "SecretPresenceProbe",
    "is_secret_configured",
    "secret_env_var",
]
