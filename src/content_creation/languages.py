from __future__ import annotations

from typing import Any

from src.localization import locales

# The language choices offered by CLI, wizard and any future UI. Derived from
# src.localization.locales, which is the single table of «код → locale → написания»
# for the whole project - so the UI list and the runtime normalizer can never drift
# apart. The shape of this list is unchanged.
LANGUAGES: list[dict[str, str]] = [
    {"code": item.code, "display_name": item.display_name} for item in locales.LANGUAGE_DEFINITIONS
]


def list_languages() -> list[dict[str, str]]:
    return [dict(item) for item in LANGUAGES]


def is_known_language(code: str) -> bool:
    return locales.is_known_language(code)


def display_name(code: str) -> str:
    return locales.display_name(code)


def language_support_warnings(*, channel: dict[str, Any] | None, template_requires_voice: bool, voice_profiles: list[dict[str, Any]], language: str) -> list[str]:
    """Non-blocking warnings about a language choice, for wizard/CLI display only.

    Never raises - Stage 2E.1 explicitly asks for warnings here, not hard
    failures, since a channel/profile mismatch may still be intentional.
    """
    warnings: list[str] = []
    if channel is not None:
        supported = channel.get("supported_languages") or []
        if supported and language not in supported:
            warnings.append(
                f"Канал {channel.get('channel_id')!r} не настроен для языка {language!r} "
                f"(поддерживает: {supported})."
            )
    if template_requires_voice:
        matching = [p for p in voice_profiles if p.get("language") == language]
        if voice_profiles and not matching:
            warnings.append(f"Нет голосового профиля для языка {language!r} в этом канале.")
    return warnings
