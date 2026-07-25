from __future__ import annotations

from typing import Any

# Single source of truth for language choices across CLI, wizard, and any future
# UI - nothing else in src.content_creation should hardcode a language list.
LANGUAGES: list[dict[str, str]] = [
    {"code": "ru", "display_name": "Русский"},
    {"code": "en", "display_name": "English"},
    {"code": "es", "display_name": "Español"},
]

_BY_CODE = {item["code"]: item for item in LANGUAGES}


def list_languages() -> list[dict[str, str]]:
    return [dict(item) for item in LANGUAGES]


def is_known_language(code: str) -> bool:
    return str(code or "").strip().lower() in _BY_CODE


def display_name(code: str) -> str:
    item = _BY_CODE.get(str(code or "").strip().lower())
    return item["display_name"] if item else code


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
