"""The string a provider actually receives, and the language it is written in.

Three languages were being conflated: the language the script is narrated in, the
language the semantic intent is recorded in, and the language a given provider can
search. ``src.content.visual_planning`` already keeps the first two apart and marks an
intent ``requires_translation``; nothing acted on that mark, so Russian intents were
posted verbatim to English-indexed APIs. Wikimedia and NASA returned nothing at all in
the confirmed run (16 requests each, 0 results), and the stock libraries returned
whatever their fuzzy matching produced for a foreign keyword salad.

This module refuses to do that. For a provider that does not declare the intent's
language it builds an English query from evidence that is actually English:

1. queries the author wrote in the scene's visual brief;
2. the brief's own English fields (subject / action / place / exact entities);
3. a small deterministic glossary of shot vocabulary and stable domain terms;
4. Latin tokens already present in the source text (``PET``, ``McMurdo``).

If none of that yields a usable query the scene is reported as
``query_translation_required`` and **no request is sent**. There is no translator here
and none is invented: a guessed translation would silently swap the subject of the
video, which is worse than an empty result.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

STATUS_OK = "ok"
STATUS_TRANSLATION_REQUIRED = "query_translation_required"

SOURCE_EXPLICIT = "explicit_override"
SOURCE_BRIEF_FIELDS = "visual_brief_fields"
SOURCE_GLOSSARY = "deterministic_glossary"
SOURCE_LATIN_TOKENS = "latin_tokens_in_source"
SOURCE_SAME_LANGUAGE = "provider_supports_source_language"

# Providers whose indexes this project can actually search in a non-English language.
# Everything else is treated as English-only, which is the honest default: none of the
# registered providers documents reliable Russian retrieval.
PROVIDER_QUERY_LANGUAGES: dict[str, tuple[str, ...]] = {
    "pexels": ("en",),
    "pixabay": ("en",),
    "wikimedia": ("en",),
    "nasa_images": ("en",),
    "internet_archive": ("en",),
    "unsplash": ("en",),
    "envato_manual": ("en",),
    # Searched against local filenames and local metadata, which this project writes
    # in whatever language the project uses.
    "local_library": ("en", "ru"),
    # Deterministic offline fixture; it matches on nothing, so language is irrelevant.
    "fake": ("en", "ru"),
}

# Small, closed and deterministic. Only terms whose English form is not a judgement
# call: shot vocabulary and words that name what is in frame rather than what it means.
# This is not a translator and must not grow into one - anything domain-specific
# belongs in the scene's visual brief, where the author can be held to it.
GLOSSARY: dict[str, str] = {
    "аэросъёмка": "aerial", "аэросъемка": "aerial", "с воздуха": "aerial",
    "крупный план": "close up", "общий план": "wide shot", "панорама": "panorama",
    "дрон": "drone", "замедленная съёмка": "slow motion",
    "лаборатория": "laboratory", "лабораторн": "laboratory",
    "микроскоп": "microscope", "спектрометр": "spectrometer", "прибор": "instrument",
    "образец": "sample", "образцы": "samples", "проба": "sample", "пробы": "samples",
    "почва": "soil", "грунт": "soil", "песок": "sand", "камен": "rock", "скал": "rock",
    "лёд": "ice", "лед": "ice", "ледник": "glacier", "снег": "snow",
    "пустыня": "desert", "долина": "valley", "долины": "valleys", "гора": "mountain",
    "антарктида": "Antarctica", "антарктик": "Antarctic", "арктика": "Arctic",
    "учёные": "scientists", "ученые": "scientists", "исследователи": "researchers",
    "экспедиция": "expedition", "станция": "station",
    "пластик": "plastic", "микропластик": "microplastic", "частицы": "particles",
    "полиэтилен": "polyethylene", "полистирол": "polystyrene", "пвх": "PVC",
    "шина": "tyre", "шины": "tyres", "ветер": "wind", "атмосфера": "atmosphere",
    "спутник": "satellite", "земля": "Earth", "планета": "planet",
}

_LATIN_RE = re.compile(r"[A-Za-z][A-Za-z0-9.\-']*")
_CYRILLIC_RE = re.compile(r"[Ѐ-ӿ]")
_MAX_QUERY_TERMS = 8


@dataclass
class ProviderQuery:
    """One query for one provider, with a record of where its words came from."""

    provider: str = ""
    query: str = ""
    language: str = "en"
    kind: str = "primary"
    fallback_level: int = 1
    source: str = SOURCE_SAME_LANGUAGE
    status: str = STATUS_OK
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "query": self.query,
            "language": self.language,
            "kind": self.kind,
            "fallback_level": self.fallback_level,
            "source": self.source,
            "status": self.status,
            "notes": self.notes,
        }


@dataclass
class SceneQueryPlan:
    """Every provider query for one scene, plus what could not be built."""

    scene_id: str = ""
    intent_language: str = "ru"
    queries: list[ProviderQuery] = field(default_factory=list)
    untranslatable_providers: list[str] = field(default_factory=list)

    def for_provider(self, provider: str) -> list[ProviderQuery]:
        return [item for item in self.queries if item.provider == provider and item.status == STATUS_OK]

    def to_dict(self) -> dict[str, Any]:
        return {
            "scene_id": self.scene_id,
            "intent_language": self.intent_language,
            "queries": [item.to_dict() for item in self.queries],
            "untranslatable_providers": list(self.untranslatable_providers),
        }


def provider_query_languages(provider: str, capabilities: dict[str, Any] | None = None) -> tuple[str, ...]:
    """Languages a provider can be searched in. Capabilities win over the table."""
    declared = (capabilities or {}).get("query_languages")
    if declared:
        return tuple(str(item).lower() for item in declared)
    return PROVIDER_QUERY_LANGUAGES.get(provider, ("en",))


def build_scene_queries(
    scene: dict[str, Any],
    *,
    providers: list[str],
    intent_language: str = "ru",
    capabilities: dict[str, dict[str, Any]] | None = None,
) -> SceneQueryPlan:
    """Build the queries every provider in ``providers`` should receive for ``scene``."""
    caps = capabilities or {}
    source_queries = _source_language_queries(scene)
    english = _english_queries(scene, intent_language=intent_language)
    plan = SceneQueryPlan(scene_id=str(scene.get("scene_id") or ""), intent_language=intent_language)

    # A plan may declare Russian and still carry English queries (an English brief, or
    # a plan written in English). Judging by the script the words are actually in beats
    # trusting the declaration, and is what lets an already-English plan reach an
    # English-only provider untouched.
    source_is_latin = bool(source_queries) and not any(
        _CYRILLIC_RE.search(str(item["query"])) for item in source_queries
    )
    for provider in providers:
        languages = provider_query_languages(provider, caps.get(provider))
        if source_is_latin and "en" in languages:
            for index, item in enumerate(source_queries):
                plan.queries.append(
                    ProviderQuery(
                        provider=provider,
                        query=item["query"],
                        language="en",
                        kind=str(item.get("kind") or "primary"),
                        fallback_level=int(item.get("fallback_level") or index + 1),
                        source=SOURCE_SAME_LANGUAGE,
                    )
                )
            continue
        if intent_language.lower() in languages and source_queries:
            for index, item in enumerate(source_queries):
                plan.queries.append(
                    ProviderQuery(
                        provider=provider,
                        query=item["query"],
                        language=intent_language,
                        kind=str(item.get("kind") or "primary"),
                        fallback_level=int(item.get("fallback_level") or index + 1),
                        source=SOURCE_SAME_LANGUAGE,
                    )
                )
            continue
        explicit = _explicit_provider_queries(scene, provider)
        chosen = explicit or english
        if not chosen:
            plan.queries.append(
                ProviderQuery(
                    provider=provider,
                    query="",
                    language="en",
                    status=STATUS_TRANSLATION_REQUIRED,
                    source=SOURCE_BRIEF_FIELDS,
                    notes=(
                        "Нет английского запроса для этой сцены: добавьте provider_queries или "
                        "английские поля в visual brief. Русский запрос не отправлен."
                    ),
                )
            )
            plan.untranslatable_providers.append(provider)
            continue
        for index, item in enumerate(chosen):
            plan.queries.append(
                ProviderQuery(
                    provider=provider,
                    query=str(item["query"]),
                    language="en",
                    kind=str(item.get("kind") or "primary"),
                    fallback_level=int(item.get("fallback_level") or index + 1),
                    source=str(item.get("source") or SOURCE_BRIEF_FIELDS),
                )
            )
    return plan


# --- Targeted per-slot queries (stage Q2.3) ----------------------------------
# Composite assembly may find that the *general* per-scene query above covered some
# semantic slots but not others. A targeted query is built from exactly the brief
# fields that slot means - never a new translation source, only a narrower read of
# the same English evidence ``_english_queries`` already draws the combined query
# from.
SLOT_QUERY_FIELDS: dict[str, tuple[str, ...]] = {
    "subject": ("exact_entities", "subject"),
    "action": ("subject", "action"),
    "location": ("place",),
    "context": ("subject", "must_include"),
}


def build_slot_queries(
    scene: dict[str, Any],
    slot_name: str,
    *,
    providers: list[str],
    capabilities: dict[str, dict[str, Any]] | None = None,
) -> SceneQueryPlan:
    """One targeted query per provider for exactly the semantic slot ``slot_name``.

    Built only from the author's own English brief fields, restricted to the ones
    ``SLOT_QUERY_FIELDS`` says that slot means. A provider that cannot search English,
    or a brief with nothing English to say about this slot, gets an explicit
    ``query_translation_required`` entry rather than a guessed or repeated query - the
    same honesty rule ``build_scene_queries`` already applies to the general query.
    """
    caps = capabilities or {}
    plan = SceneQueryPlan(scene_id=str(scene.get("scene_id") or ""), intent_language="en")
    query_text = " ".join(_slot_english_terms(scene, slot_name))
    for provider in providers:
        languages = provider_query_languages(provider, caps.get(provider))
        if not query_text or "en" not in languages:
            plan.queries.append(
                ProviderQuery(
                    provider=provider,
                    query="",
                    language="en",
                    kind=f"slot_{slot_name}",
                    status=STATUS_TRANSLATION_REQUIRED,
                    source=SOURCE_BRIEF_FIELDS,
                    notes=(
                        f"Нет английских терминов брифа для слота '{slot_name}'."
                        if not query_text
                        else "Провайдер не ищет по-английски."
                    ),
                )
            )
            plan.untranslatable_providers.append(provider)
            continue
        plan.queries.append(
            ProviderQuery(
                provider=provider,
                query=query_text,
                language="en",
                kind=f"slot_{slot_name}",
                fallback_level=1,
                source=SOURCE_BRIEF_FIELDS,
            )
        )
    return plan


def _slot_english_terms(scene: dict[str, Any], slot_name: str) -> list[str]:
    brief = scene.get("visual_brief") if isinstance(scene.get("visual_brief"), dict) else {}
    fields = SLOT_QUERY_FIELDS.get(slot_name, ())
    parts: list[str] = []
    if "exact_entities" in fields:
        parts.extend(
            str(item).strip()
            for item in (brief.get("exact_entities") or [])
            if str(item).strip() and not _CYRILLIC_RE.search(str(item))
        )
    if "subject" in fields:
        parts.append(_english_only(str(brief.get("subject") or "")))
    if "action" in fields:
        parts.append(_english_only(str(brief.get("action") or "")))
    if "place" in fields:
        parts.append(_english_only(str(brief.get("place") or brief.get("location") or "")))
    if "must_include" in fields:
        parts.extend(_english_only(str(item)) for item in (brief.get("must_include") or []))
    return _terms([part for part in parts if part])


def _explicit_provider_queries(scene: dict[str, Any], provider: str) -> list[dict[str, Any]]:
    """Queries the author wrote, either for this provider by name or for all of them."""
    brief = scene.get("visual_brief") if isinstance(scene.get("visual_brief"), dict) else {}
    raw = brief.get("provider_queries") or scene.get("provider_queries") or {}
    values: list[str] = []
    if isinstance(raw, dict):
        for key in (provider, "en", "english", "default", "*"):
            entry = raw.get(key)
            if entry:
                values = [entry] if isinstance(entry, str) else [str(item) for item in entry]
                break
    elif isinstance(raw, (list, tuple)):
        values = [str(item) for item in raw]
    elif isinstance(raw, str):
        values = [raw]
    return [
        {"query": text.strip(), "kind": "explicit", "fallback_level": index + 1, "source": SOURCE_EXPLICIT}
        for index, text in enumerate(values)
        if str(text).strip()
    ]


def _english_queries(scene: dict[str, Any], *, intent_language: str) -> list[dict[str, Any]]:
    """An English query built from English evidence, never from a guessed translation."""
    brief = scene.get("visual_brief") if isinstance(scene.get("visual_brief"), dict) else {}
    exact = [str(item).strip() for item in (brief.get("exact_entities") or []) if str(item).strip()]
    subject = _english_only(str(brief.get("subject") or ""))
    action = _english_only(str(brief.get("action") or ""))
    place = _english_only(str(brief.get("place") or brief.get("location") or ""))
    must = [_english_only(str(item)) for item in (brief.get("must_include") or [])]
    shot = _english_only(str(brief.get("shot_type") or scene.get("shot_type") or ""))

    exact_english = [item for item in exact if not _CYRILLIC_RE.search(item)]
    # A shot type is a modifier, never a query on its own: "action" and "payoff" name
    # how to frame a subject, not what to look for. Without a subject, a place or an
    # exact name there is nothing here to search with.
    has_topic = bool(exact_english or subject or place)
    primary_terms = _terms(exact_english + [subject, action, place, shot]) if has_topic else []
    if primary_terms:
        queries = [{"query": " ".join(primary_terms), "kind": "primary", "fallback_level": 1, "source": SOURCE_BRIEF_FIELDS}]
        broad_terms = _terms(exact_english + [subject, place])
        if broad_terms and broad_terms != primary_terms:
            queries.append(
                {"query": " ".join(broad_terms), "kind": "alternative", "fallback_level": 2, "source": SOURCE_BRIEF_FIELDS}
            )
        context_terms = _terms([place] + [item for item in must if item])
        if context_terms and all(item["query"] != " ".join(context_terms) for item in queries):
            queries.append(
                {"query": " ".join(context_terms), "kind": "context_fallback", "fallback_level": 3, "source": SOURCE_BRIEF_FIELDS}
            )
        return queries

    # No brief. Fall back to whatever the source text itself offers in English: a
    # deterministic glossary hit, or a Latin token the script already contains.
    glossary_terms = _glossary_terms(scene)
    latin_terms = _latin_terms(scene)
    combined = _terms(glossary_terms + latin_terms)
    if not combined:
        return []
    source = SOURCE_GLOSSARY if glossary_terms else SOURCE_LATIN_TOKENS
    return [{"query": " ".join(combined), "kind": "primary", "fallback_level": 2, "source": source}]


def _source_language_queries(scene: dict[str, Any]) -> list[dict[str, Any]]:
    """The plan's own queries, in the language the plan was written in."""
    queries: list[dict[str, Any]] = []
    primary = str(scene.get("primary_query") or "").strip()
    if primary:
        queries.append({"query": primary, "kind": "primary", "fallback_level": 1})
    for index, alternative in enumerate(scene.get("alternative_queries") or [], start=2):
        text = str(alternative).strip()
        if text and all(text != item["query"] for item in queries):
            queries.append({"query": text, "kind": "alternative", "fallback_level": index})
    return queries


def _glossary_terms(scene: dict[str, Any]) -> list[str]:
    text = " ".join(
        str(scene.get(key) or "")
        for key in ("narration", "visual_description", "visual_intent", "primary_query")
    ).lower()
    if not text.strip():
        return []
    matched: list[str] = []
    for russian, english in GLOSSARY.items():
        if russian in text and english not in matched:
            matched.append(english)
    return matched


def _latin_terms(scene: dict[str, Any]) -> list[str]:
    semantic = scene.get("semantic") if isinstance(scene.get("semantic"), dict) else {}
    pieces = [
        *(str(item) for item in (semantic.get("subject") or [])),
        *(str(item) for item in (semantic.get("location") or [])),
        str(scene.get("primary_query") or ""),
    ]
    found: list[str] = []
    for piece in pieces:
        for token in _LATIN_RE.findall(piece):
            if len(token) > 1 and token.lower() not in {item.lower() for item in found}:
                found.append(token)
    return found


def _english_only(value: str) -> str:
    """Drop anything that is not Latin script: a brief field left in Russian is not
    an English query and must not be smuggled into one."""
    text = (value or "").strip()
    if not text or _CYRILLIC_RE.search(text):
        return ""
    return text


def _terms(values: list[str]) -> list[str]:
    seen: set[str] = set()
    words: list[str] = []
    for value in values:
        for word in str(value or "").split():
            key = word.lower()
            if key and key not in seen:
                seen.add(key)
                words.append(word)
    return words[:_MAX_QUERY_TERMS]


__all__ = [
    "GLOSSARY",
    "PROVIDER_QUERY_LANGUAGES",
    "SLOT_QUERY_FIELDS",
    "SOURCE_BRIEF_FIELDS",
    "SOURCE_EXPLICIT",
    "SOURCE_GLOSSARY",
    "SOURCE_LATIN_TOKENS",
    "SOURCE_SAME_LANGUAGE",
    "STATUS_OK",
    "STATUS_TRANSLATION_REQUIRED",
    "ProviderQuery",
    "SceneQueryPlan",
    "build_scene_queries",
    "build_slot_queries",
    "provider_query_languages",
]
