"""Readable, safe, unique project identifiers.

Why this exists
---------------
Both project systems built their folder name out of whatever text happened to be
at hand, and both got it wrong in a different way:

- ``src.news.models.NewsJob.create`` used ``slugify(topic or input_text[:80])`` and
  kept Cyrillic letters as-is, which produced folders like
  ``wizard_установил_questionary_единственная_подходящая_библиотека__20260724T210156``
  - the first words of a pasted script, not a name;
- ``src.project_foundation.projects._slugify`` stripped every non-ASCII character,
  so any Russian title collapsed to nothing and the project became ``project-61958823``.

This module is the one place that answers "what should this folder be called".
Pure functions, no I/O: the caller supplies the collision check, because only the
caller knows which root the id has to be unique in.

Format
------
``YYYY-MM-DD_transliterated-title`` (plus ``-2``, ``-3``... only when that exact
name is already taken). The date first because it sorts chronologically in any
file browser, which is what someone looking for "the video I made on Tuesday"
actually does.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Callable, Iterable

MAX_SLUG_LENGTH = 48
MAX_COLLISION_ATTEMPTS = 99

# Simplified GOST-style transliteration: aimed at a readable folder name, not at
# reversibility. "щ" -> "sch" rather than "shch" keeps names shorter.
CYRILLIC_TO_LATIN = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "h", "ц": "c", "ч": "ch", "ш": "sh", "щ": "sch",
    "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
    # Ukrainian/Belarusian letters that turn up in copied text.
    "і": "i", "ї": "yi", "є": "ye", "ґ": "g", "ў": "u",
}

# Windows refuses these as a file or folder name, with or without an extension.
WINDOWS_RESERVED_NAMES = frozenset(
    {"con", "prn", "aux", "nul"}
    | {f"com{digit}" for digit in range(1, 10)}
    | {f"lpt{digit}" for digit in range(1, 10)}
)


def transliterate(text: str) -> str:
    """Cyrillic to Latin. Characters with no mapping are left for the slugifier."""
    return "".join(CYRILLIC_TO_LATIN.get(char, CYRILLIC_TO_LATIN.get(char.lower(), char)) for char in str(text or ""))


def slugify_title(title: str, *, max_length: int = MAX_SLUG_LENGTH, fallback: str = "project") -> str:
    """A lowercase, hyphenated, Windows-safe fragment of a human title.

    Truncation happens on a word boundary where possible - ``pochemu-vorony-zapo``
    is worse than ``pochemu-vorony`` for someone scanning a folder list.
    """
    text = transliterate(str(title or "")).lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    text = re.sub(r"-{2,}", "-", text)
    if not text:
        return fallback
    if len(text) > max_length:
        cut = text[:max_length]
        # Keep the last whole word unless that would leave almost nothing.
        boundary = cut.rfind("-")
        text = cut[:boundary] if boundary >= max_length // 2 else cut
        text = text.strip("-")
    if text.lower() in WINDOWS_RESERVED_NAMES:
        # "con" is a legal title but an impossible folder name on Windows.
        text = f"{text}-project"
    return text or fallback


def _date_prefix(created_at: str | datetime | None) -> str:
    if isinstance(created_at, datetime):
        return created_at.strftime("%Y-%m-%d")
    text = str(created_at or "").strip()
    if text:
        # Accept both ISO ("2026-07-25T21:03:04+03:00") and the compact stamp the
        # news pipeline used ("20260724T214350").
        match = re.match(r"^(\d{4})-?(\d{2})-?(\d{2})", text)
        if match:
            return "-".join(match.groups())
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def build_project_id(
    title: str,
    *,
    created_at: str | datetime | None = None,
    is_taken: Callable[[str], bool] | Iterable[str] | None = None,
    max_slug_length: int = MAX_SLUG_LENGTH,
    fallback: str = "project",
) -> str:
    """Build ``YYYY-MM-DD_slug``, made unique against ``is_taken``.

    ``is_taken`` may be a predicate or any container of existing ids. When it is
    omitted the id is fully deterministic, which keeps tests and dry runs stable.
    Collisions get ``-2``, ``-3``... and only after 99 of them (i.e. never, in
    practice) does a random suffix appear - a readable name is the whole point.
    """
    slug = slugify_title(title, max_length=max_slug_length, fallback=fallback)
    base = f"{_date_prefix(created_at)}_{slug}"

    if is_taken is None:
        return base
    taken = is_taken if callable(is_taken) else (lambda candidate, ids=frozenset(is_taken): candidate in ids)

    if not taken(base):
        return base
    for attempt in range(2, MAX_COLLISION_ATTEMPTS + 1):
        candidate = f"{base}-{attempt}"
        if not taken(candidate):
            return candidate
    return f"{base}-{uuid.uuid4().hex[:8]}"


def suggest_title(*candidates: str, max_length: int = 60, fallback: str = "Без названия") -> str:
    """First usable candidate, trimmed to something a person would type.

    Used to pre-fill the wizard's title question from the topic or the first line
    of a pasted script, so the common case is one Enter press rather than typing.
    """
    for candidate in candidates:
        text = " ".join(str(candidate or "").split())
        if not text:
            continue
        # A pasted script starts with a sentence, not a title: take the first one.
        sentence = re.split(r"(?<=[.!?])\s", text)[0].strip()
        text = sentence or text
        if len(text) > max_length:
            cut = text[:max_length]
            boundary = cut.rfind(" ")
            text = (cut[:boundary] if boundary >= max_length // 2 else cut).rstrip(" ,;:-")
        if text:
            return text
    return fallback


__all__ = [
    "CYRILLIC_TO_LATIN",
    "MAX_SLUG_LENGTH",
    "WINDOWS_RESERVED_NAMES",
    "build_project_id",
    "slugify_title",
    "suggest_title",
    "transliterate",
]
