"""What a script may never lose when it is rephrased to fit the material that exists.

Asset-aware adaptation is allowed to change *how* a scene is said. It is never allowed
to change what the scene claims. The difference has to be checkable by a machine before
an adapted line is accepted, otherwise "light rewriting" is just an unaudited rewrite.

A fact lock is one such immutable: a number, a date, a named entity, a measurement, a
causal claim, an uncertainty marker, the direction of a comparison, a first/only/largest
claim, an attributed source, a quotation. Locks are extracted from the *original*
narration and every adapted line is verified against them; a line that drops or changes
one is rejected and the original is kept.

Deliberately conservative in both directions:

- extraction never guesses at meaning (no NLP model, no knowledge base) - it recognises
  surface forms, which is exactly what has to survive verbatim;
- verification is a containment test, so an adaptation may add or reorder wording but
  can never quietly delete a locked fact.

Bilingual because the narration is Russian and the briefs are English.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any

FACT_LOCK_SCHEMA_VERSION = 1

# --- Lock kinds --------------------------------------------------------------
LOCK_NUMBER = "number"
LOCK_DATE = "date"
LOCK_ENTITY = "named_entity"
LOCK_GEOGRAPHY = "geography"
LOCK_MEASUREMENT = "measurement"
LOCK_UNCERTAINTY = "uncertainty"
LOCK_CERTAINTY = "certainty"
LOCK_COMPARISON = "comparison"
LOCK_SUPERLATIVE = "superlative"
LOCK_CAUSAL = "causal"
LOCK_SOURCE = "source_attribution"
LOCK_QUOTE = "quote"

LOCK_KINDS = (
    LOCK_NUMBER, LOCK_DATE, LOCK_ENTITY, LOCK_GEOGRAPHY, LOCK_MEASUREMENT,
    LOCK_UNCERTAINTY, LOCK_CERTAINTY, LOCK_COMPARISON, LOCK_SUPERLATIVE,
    LOCK_CAUSAL, LOCK_SOURCE, LOCK_QUOTE,
)

_NUMBER_RE = re.compile(r"(?<![\w])[-+]?\d+(?:[.,]\d+)?\s*%?")
_FULL_DATE_RE = re.compile(
    r"\b(?:\d{1,2}[./-]\d{1,2}[./-]\d{2,4}|\d{4}[./-]\d{1,2}[./-]\d{1,2})\b"
)
_YEAR_RE = re.compile(r"\b(?:1[5-9]\d{2}|20\d{2})\b")
_QUOTE_RE = re.compile(r"«([^»]{2,})»|“([^”]{2,})”|\"([^\"]{2,})\"")
# A Latin-script token inside a Cyrillic narration, or a capitalised token that is not
# the first word of a sentence: both are how a proper noun shows up in this project's
# scripts ("McMurdo", "Антарктида", "PTR-TOF").
_LATIN_TOKEN_RE = re.compile(r"\b[A-Z][A-Za-z0-9\-]{1,}\b")
_CYRILLIC_CAPITAL_RE = re.compile(r"\b[А-ЯЁ][а-яё\-]{2,}\b")

_MONTHS = {
    "январ", "феврал", "март", "апрел", "мая", "май", "июн", "июл", "август", "сентябр",
    "октябр", "ноябр", "декабр", "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
}
_UNITS = {
    "мкм", "нм", "мм", "см", "км", "кг", "мг", "г", "тонн", "процент", "процентах",
    "градус", "мл", "л", "м/с", "км/ч", "µm", "μm", "nm", "mm", "cm", "km", "kg",
    "mg", "ml", "ppm", "ppb",
}
_UNCERTAINTY_LEVELS = {
    "probable": {
        "вероятно", "скорее всего", "probably", "likely",
    },
    "possible": {
        "возможно", "может", "могут", "не исключено", "perhaps", "may", "might",
    },
    "tentative": {
        "предположительно", "по-видимому", "гипотеза", "гипотезу", "suggests", "appears",
    },
}
_UNCERTAINTY = set().union(*_UNCERTAINTY_LEVELS.values())
_CERTAINTY = {
    "доказано", "установлено", "подтверждено", "показало", "показали", "обнаружили",
    "нашли", "зафиксировали", "proved", "confirmed", "established", "found",
}
_COMPARISON = {
    "больше", "меньше", "выше", "ниже", "быстрее", "медленнее", "чаще", "реже",
    "more", "less", "higher", "lower", "faster", "slower",
}
_SUPERLATIVE = {
    "впервые", "самый", "самая", "самое", "самые", "крупнейший", "крупнейшая",
    "наибольш", "наименьш", "единственн", "первый", "первая", "first", "largest",
    "smallest", "only",
}
_CAUSAL = {
    "потому что", "из-за", "поэтому", "приводит", "вызывает", "следствие", "благодаря",
    "because", "causes", "leads to", "due to", "therefore",
}
_SOURCE = {
    "по данным", "исследование", "исследования", "учёные", "ученые", "авторы",
    "according to", "study", "researchers", "authors",
}
# Words that start a Russian sentence often enough that treating them as proper nouns
# would lock ordinary wording in place.
_CAPITAL_STOPWORDS = {
    "Это", "Эти", "Этот", "Эта", "Так", "Там", "Тогда", "Теперь", "Но", "И", "А", "Он",
    "Она", "Они", "Мы", "Вы", "Я", "Что", "Как", "Когда", "Если", "Даже", "Ещё", "Еще",
    "Результат", "Именно", "Среди", "Внутри", "Может", "Можно", "Через", "После", "Один",
    "Одном", "Одна", "Все", "Всё", "Каждый", "Такой", "Затем", "Потом", "Поэтому", "The",
    "This", "That", "These", "Those", "And", "But", "It", "They", "We",
}

_MEASUREMENT_RE = re.compile(
    rf"(?<![\w])[-+]?\d+(?:[.,]\d+)?\s*"
    rf"(?:%|°\s*[cCfFсСфФ]|{'|'.join(sorted((re.escape(unit) for unit in _UNITS), key=len, reverse=True))})"
    rf"(?![\w])",
    re.IGNORECASE,
)
_RUSSIAN_SUPERLATIVE_PHRASE_RE = re.compile(
    r"\bсам(?:ый|ая|ое|ые|ого|ой|ую|ых|ыми?|ом)\s+[а-яё-]+",
    re.IGNORECASE,
)

# These entries intentionally match the start of an inflected word. All other
# semantic markers use token boundaries, so e.g. English "may" is not found in
# "maybe" and Russian "могут" is not found inside an unrelated word.
_PREFIX_MARKERS = {
    "январ", "феврал", "март", "апрел", "мая", "май", "июн", "июл", "август",
    "сентябр", "октябр", "ноябр", "декабр", "наибольш", "наименьш", "единственн",
}


@dataclass
class FactLock:
    """One thing an adapted line has to keep, and where it came from."""

    kind: str
    surface: str
    scene_id: str = ""
    normalized: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "surface": self.surface,
            "scene_id": self.scene_id,
            "normalized": self.normalized or normalize_text(self.surface),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FactLock":
        return cls(
            kind=str(data.get("kind") or ""),
            surface=str(data.get("surface") or ""),
            scene_id=str(data.get("scene_id") or ""),
            normalized=str(data.get("normalized") or ""),
        )


@dataclass
class FactLockSet:
    locks: list[FactLock] = field(default_factory=list)
    schema_version: int = FACT_LOCK_SCHEMA_VERSION

    def for_scene(self, scene_id: str) -> list[FactLock]:
        return [lock for lock in self.locks if lock.scene_id == scene_id]

    def kinds(self) -> list[str]:
        return sorted({lock.kind for lock in self.locks})

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "lock_count": len(self.locks),
            "kinds": self.kinds(),
            "locks": [lock.to_dict() for lock in self.locks],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "FactLockSet":
        data = data if isinstance(data, dict) else {}
        return cls(
            locks=[FactLock.from_dict(item) for item in (data.get("locks") or []) if isinstance(item, dict)],
            schema_version=int(data.get("schema_version") or FACT_LOCK_SCHEMA_VERSION),
        )


def normalize_text(value: str) -> str:
    """Case-folded, whitespace-collapsed, ё->е. Never changes digits or letters."""
    text = unicodedata.normalize("NFKC", str(value or "")).replace("ё", "е").replace("Ё", "Е")
    return re.sub(r"\s+", " ", text).strip().casefold()


def _contains_marker(text: str, marker: str) -> bool:
    """Whether a normalized marker occurs as a token (or an intentional stem)."""
    normalized_text = normalize_text(text)
    normalized_marker = normalize_text(marker)
    if not normalized_marker:
        return False
    if normalized_marker in _PREFIX_MARKERS:
        return re.search(rf"(?<![\w]){re.escape(normalized_marker)}[\w-]*", normalized_text) is not None
    return re.search(
        rf"(?<![\w]){re.escape(normalized_marker)}(?![\w])",
        normalized_text,
    ) is not None


def _markers_present(text: str, markers: set[str]) -> set[str]:
    return {
        normalize_text(marker)
        for marker in markers
        if _contains_marker(text, marker)
    }


def _uncertainty_levels(text: str) -> set[str]:
    return {
        level
        for level, markers in _UNCERTAINTY_LEVELS.items()
        if _markers_present(text, markers)
    }


def _canonical_number(value: str) -> str:
    normalized = normalize_text(value).replace(" ", "").replace(",", ".")
    return normalized[1:] if normalized.startswith("+") else normalized


def _canonical_measurement(value: str) -> str:
    return (
        normalize_text(value)
        .replace(" ", "")
        .replace(",", ".")
        .replace("μ", "µ")
    )


def _canonical_date(value: str) -> str:
    normalized = normalize_text(value)
    if _FULL_DATE_RE.fullmatch(normalized):
        return re.sub(r"[./]", "-", normalized)
    return normalized


def _overlaps(span: tuple[int, int], protected: list[tuple[int, int]]) -> bool:
    return any(span[0] < end and start < span[1] for start, end in protected)


def _number_values(text: str) -> set[str]:
    protected = [match.span() for match in _FULL_DATE_RE.finditer(text)]
    protected.extend(match.span() for match in _YEAR_RE.finditer(text))
    return {
        _canonical_number(match.group(0))
        for match in _NUMBER_RE.finditer(text)
        if not _overlaps(match.span(), protected)
    }


def _measurement_values(text: str) -> set[str]:
    return {
        _canonical_measurement(match.group(0))
        for match in _MEASUREMENT_RE.finditer(text)
    }


def _date_values(text: str) -> set[str]:
    values = {_canonical_date(match.group(0)) for match in _FULL_DATE_RE.finditer(text)}
    values.update(_canonical_date(match.group(0)) for match in _YEAR_RE.finditer(text))
    values.update(
        normalize_text(month)
        for month in _MONTHS
        if _contains_marker(text, month)
    )
    return values


def _superlative_phrases(text: str) -> list[str]:
    return [match.group(0) for match in _RUSSIAN_SUPERLATIVE_PHRASE_RE.finditer(text)]


def _string_values(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, (list, tuple, set)):
        return [
            item
            for nested in value
            for item in _string_values(nested)
        ]
    return []


def _unique_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        key = normalize_text(value)
        if key and key not in seen:
            seen.add(key)
            result.append(str(value).strip())
    return result


def extract_scene_locks(
    narration: str,
    *,
    scene_id: str = "",
    extra_entities: list[str] | None = None,
    extra_geography: list[str] | None = None,
) -> list[FactLock]:
    """Every immutable this one line carries."""
    text = str(narration or "")
    locks: list[FactLock] = []

    def add(kind: str, surface: str) -> None:
        surface = str(surface or "").strip()
        if not surface:
            return
        normalized = normalize_text(surface)
        if any(lock.kind == kind and lock.normalized == normalized for lock in locks):
            return
        locks.append(FactLock(kind=kind, surface=surface, scene_id=scene_id, normalized=normalized))

    full_date_spans: list[tuple[int, int]] = []
    for match in _FULL_DATE_RE.finditer(text):
        add(LOCK_DATE, match.group(0))
        full_date_spans.append(match.span())
    year_spans: list[tuple[int, int]] = []
    for match in _YEAR_RE.finditer(text):
        add(LOCK_DATE, match.group(0))
        year_spans.append(match.span())
    for month in sorted(_MONTHS):
        if _contains_marker(text, month):
            add(LOCK_DATE, month)
    for match in _MEASUREMENT_RE.finditer(text):
        add(LOCK_MEASUREMENT, match.group(0))
    for match in _NUMBER_RE.finditer(text):
        if _overlaps(match.span(), full_date_spans + year_spans):
            continue
        value = match.group(0).strip()
        add(LOCK_NUMBER, value)
    for match in _QUOTE_RE.finditer(text):
        add(LOCK_QUOTE, next(group for group in match.groups() if group))
    for token in _LATIN_TOKEN_RE.findall(text):
        if token not in _CAPITAL_STOPWORDS:
            add(LOCK_ENTITY, token)
    for position, token in enumerate(_CYRILLIC_CAPITAL_RE.findall(text)):
        if token in _CAPITAL_STOPWORDS:
            continue
        # The first capitalised word of the line is normal sentence case; anything
        # capitalised later is a name.
        if position == 0 and text.strip().startswith(token):
            continue
        add(LOCK_ENTITY, token)
    for entity in extra_entities or []:
        if _contains_marker(text, entity):
            add(LOCK_ENTITY, entity)
    for place in extra_geography or []:
        if _contains_marker(text, place):
            add(LOCK_GEOGRAPHY, place)
    for phrase in _superlative_phrases(text):
        add(LOCK_SUPERLATIVE, phrase)
    for group, kind in (
        (_UNCERTAINTY, LOCK_UNCERTAINTY),
        (_CERTAINTY, LOCK_CERTAINTY),
        (_COMPARISON, LOCK_COMPARISON),
        (_SUPERLATIVE, LOCK_SUPERLATIVE),
        (_CAUSAL, LOCK_CAUSAL),
        (_SOURCE, LOCK_SOURCE),
    ):
        for marker in sorted(group, key=lambda item: (-len(item), item)):
            if _contains_marker(text, marker):
                add(kind, marker)
    return locks


def extract_fact_locks(script: dict[str, Any], *, research: dict[str, Any] | None = None) -> FactLockSet:
    """Locks for a whole script, scene by scene.

    Research claims, when the caller has them, contribute their own entities: a name the
    study established is a fact of the material even if the narration wraps it in a case
    ending this module cannot decline.
    """
    entities: list[str] = []
    geography: list[str] = []
    for claim in (research or {}).get("claims") or []:
        if isinstance(claim, dict):
            entities.extend(_string_values(claim.get("entities")))
            for key in ("geography", "locations", "location", "places", "place"):
                geography.extend(_string_values(claim.get(key)))
    locks: list[FactLock] = []
    for index, scene in enumerate(script.get("scenes") or [], start=1):
        if not isinstance(scene, dict):
            continue
        scene_id = str(scene.get("scene_id") or f"scene_{index:03d}")
        visual_brief = scene.get("visual_brief")
        visual_brief = visual_brief if isinstance(visual_brief, dict) else {}
        scene_entities = list(entities)
        scene_geography = list(geography)
        for key in ("exact_entities", "entities", "named_entities"):
            scene_entities.extend(_string_values(visual_brief.get(key)))
            scene_entities.extend(_string_values(scene.get(key)))
        for key in ("place", "places", "location", "locations", "geography"):
            scene_geography.extend(_string_values(visual_brief.get(key)))
            scene_geography.extend(_string_values(scene.get(key)))
        locks.extend(
            extract_scene_locks(
                str(scene.get("narration") or scene.get("narration_text") or ""),
                scene_id=scene_id,
                extra_entities=_unique_strings(scene_entities),
                extra_geography=_unique_strings(scene_geography),
            )
        )
    return FactLockSet(locks=locks)


def verify_scene_adaptation(
    adapted: str,
    locks: list[FactLock],
    *,
    original: str = "",
) -> list[str]:
    """Return every invariant violated by an adapted line.

    ``original`` is optional for compatibility with existing callers. When supplied,
    the verifier also rejects newly introduced facts (numbers, measurements, dates),
    a changed uncertainty level, or newly introduced certainty, causality and
    superlatives. The lock-only path still prevents deletion of every extracted fact.
    """
    text = normalize_text(adapted)
    numbers_present = _number_values(adapted)
    measurements_present = _measurement_values(adapted)
    dates_present = _date_values(adapted)
    uncertainty_present = _uncertainty_levels(adapted)
    violations: list[str] = []
    for lock in locks:
        needle = lock.normalized or normalize_text(lock.surface)
        if not needle:
            continue
        if lock.kind == LOCK_NUMBER:
            if _canonical_number(lock.surface) not in numbers_present:
                violations.append(f"{lock.kind}:{lock.surface}")
            continue
        if lock.kind == LOCK_MEASUREMENT:
            if _canonical_measurement(lock.surface) not in measurements_present:
                violations.append(f"{lock.kind}:{lock.surface}")
            continue
        if lock.kind == LOCK_DATE:
            if _canonical_date(lock.surface) not in dates_present:
                violations.append(f"{lock.kind}:{lock.surface}")
            continue
        if lock.kind == LOCK_UNCERTAINTY:
            wanted_levels = _uncertainty_levels(lock.surface)
            if wanted_levels:
                if not wanted_levels.intersection(uncertainty_present):
                    violations.append(f"{lock.kind}:{lock.surface}")
            elif not _contains_marker(text, needle):
                violations.append(f"{lock.kind}:{lock.surface}")
            continue
        if lock.kind == LOCK_CERTAINTY:
            if not _markers_present(text, _CERTAINTY):
                violations.append(f"{lock.kind}:{lock.surface}")
            continue
        if not _contains_marker(text, needle):
            violations.append(f"{lock.kind}:{lock.surface}")

    if original:
        original_numbers = _number_values(original)
        if numbers_present != original_numbers:
            for value in sorted(numbers_present - original_numbers):
                violations.append(f"number:added:{value}")

        original_measurements = _measurement_values(original)
        if measurements_present != original_measurements:
            for value in sorted(measurements_present - original_measurements):
                violations.append(f"measurement:added:{value}")

        original_dates = _date_values(original)
        if dates_present != original_dates:
            for value in sorted(dates_present - original_dates):
                violations.append(f"date:added:{value}")

        original_uncertainty = _uncertainty_levels(original)
        if uncertainty_present != original_uncertainty:
            before = ",".join(sorted(original_uncertainty)) or "none"
            after = ",".join(sorted(uncertainty_present)) or "none"
            violations.append(f"uncertainty_level:{before}->{after}")

        original_causal = bool(_markers_present(original, _CAUSAL))
        adapted_causal = bool(_markers_present(adapted, _CAUSAL))
        if original_causal != adapted_causal:
            violations.append(f"causal:{'added' if adapted_causal else 'removed'}")

        original_certainty = bool(_markers_present(original, _CERTAINTY))
        adapted_certainty = bool(_markers_present(adapted, _CERTAINTY))
        if original_certainty != adapted_certainty:
            violations.append(f"certainty:{'added' if adapted_certainty else 'removed'}")

        original_superlative = bool(
            _markers_present(original, _SUPERLATIVE) or _superlative_phrases(original)
        )
        adapted_superlative = bool(
            _markers_present(adapted, _SUPERLATIVE) or _superlative_phrases(adapted)
        )
        if original_superlative != adapted_superlative:
            violations.append(f"superlative:{'added' if adapted_superlative else 'removed'}")

    return list(dict.fromkeys(violations))


__all__ = [
    "FACT_LOCK_SCHEMA_VERSION",
    "LOCK_CAUSAL",
    "LOCK_CERTAINTY",
    "LOCK_COMPARISON",
    "LOCK_DATE",
    "LOCK_ENTITY",
    "LOCK_GEOGRAPHY",
    "LOCK_KINDS",
    "LOCK_MEASUREMENT",
    "LOCK_NUMBER",
    "LOCK_QUOTE",
    "LOCK_SOURCE",
    "LOCK_SUPERLATIVE",
    "LOCK_UNCERTAINTY",
    "FactLock",
    "FactLockSet",
    "extract_fact_locks",
    "extract_scene_locks",
    "normalize_text",
    "verify_scene_adaptation",
]
