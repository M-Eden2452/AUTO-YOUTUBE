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

A query refused for its language is written into the plan as
``query_language_unsupported`` rather than dropped in silence. It stays unsendable,
but it is now visible: while a scene kept at least one English query the loss of its
most precise one was recorded nowhere, so "the language broke" and "the plan was
narrow" produced identical evidence.

It also refuses to ask about something else. A query may be built from perfectly
English evidence and still lose the subject the video is about: of the 42 distinct
queries the two frozen runs sent, 15 named no form of the topic at all - ``battery
pack``, ``factory machines industrial production line``, ``sunset`` - while the plan
that produced them stated ``topic_entity`` = "панель" and nothing compared the two
(C98, ADR 0022, measured 2026-08-18). So the plan now hands the scene a
``TopicAnchor``: the English form of its topic, read from the plan's own English
evidence, and every English query that does not name it gets it back. The anchor is
prepended, never substituted - the rest of the query is the scene's own evidence.

The anchor is never translated. When the topic is written in Russian and the plan's
scenes offer no recurring English subject, no anchor is invented: the scene's queries
are marked ``query_subject_unverified`` and stay visible as unchecked, because a
guessed translation would swap the subject of the video silently, which is the exact
failure this module exists to refuse.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any

STATUS_OK = "ok"
STATUS_TRANSLATION_REQUIRED = "query_translation_required"
#: A single candidate string this provider cannot be searched with. Written into the
#: plan instead of being dropped in silence: while a scene still had *some* English
#: query, the loss of its most precise one left no record anywhere, so a language
#: failure and a deliberately narrow plan looked identical in the saved evidence
#: (language audit 2026-08-16, K9). It is never sendable - ``for_provider`` returns
#: only ``STATUS_OK`` - so no request and no budget follows from it.
STATUS_LANGUAGE_UNSUPPORTED = "query_language_unsupported"
#: The plan named a topic, and no English form of it could be read from the plan's
#: own English evidence, so no query of this scene could be checked against it. The
#: queries are still sent - they are the only evidence there is - but the fact that
#: nobody verified their subject is written down instead of assumed away (C98).
#: Never sendable itself: ``for_provider`` returns only ``STATUS_OK``.
STATUS_SUBJECT_UNVERIFIED = "query_subject_unverified"

#: Where the English form of the topic came from. Both are English written by the
#: planner or by the brief; neither is a translation of a Russian field.
ANCHOR_SOURCE_TOPIC_ENTITY = "plan_topic_entity"
ANCHOR_SOURCE_SCENE_SUBJECTS = "plan_scene_subjects"
#: The topic is stated but has no English form anywhere in the plan.
ANCHOR_SOURCE_UNRESOLVED = "topic_not_in_english_evidence"

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
_WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)
_MAX_QUERY_TERMS = 8

# Exact outputs of the upstream compatibility fallback. Canonical plans distinguish
# them structurally (they are absent from ``visual_intents``), but old flat plans do
# not carry provenance. Excluding these four known values prevents the new per-query
# reader from promoting a previously rejected generic fallback into fake adaptation.
_LEGACY_BROAD_QUERIES = frozenset(
    {
        "whale mother calf aerial ocean",
        "scientific researchers nature field observation",
        "ocean wildlife aerial waves",
        "nature science wildlife observation",
    }
)

# Four legacy seed entries are intentionally word stems rather than full words.
# They may consume only a known Russian ending within one token; arbitrary
# prefix/substring matching is never used.
_GLOSSARY_STEMS = frozenset({"лабораторн", "камен", "скал", "антарктик"})
_RUSSIAN_INFLECTION_SUFFIXES = (
    "иями",
    "ями",
    "ами",
    "ого",
    "ему",
    "ому",
    "ыми",
    "ими",
    "ую",
    "юю",
    "ая",
    "яя",
    "ое",
    "ее",
    "ые",
    "ие",
    "ый",
    "ий",
    "ой",
    "ей",
    "ом",
    "ем",
    "ах",
    "ях",
    "ам",
    "ям",
    "ов",
    "ев",
    "а",
    "я",
    "ы",
    "и",
    "у",
    "ю",
)
_GLOSSARY_STEM_ENDINGS = frozenset(
    {
        "",
        "ь",
        "а",
        "я",
        "ы",
        "и",
        "у",
        "ю",
        "е",
        "ой",
        "ей",
        "ом",
        "ем",
        "ами",
        "ями",
        "ах",
        "ях",
        "ный",
        "ная",
        "ное",
        "ные",
        "ного",
        "ному",
        "ным",
        "ную",
        "ных",
        "ными",
        "ый",
        "ая",
        "ое",
        "ые",
        "ого",
        "ому",
        "ым",
        "ую",
        "ых",
        "ыми",
        "ческий",
        "ческая",
        "ческое",
        "ческие",
        "ческого",
        "ческому",
        "ческим",
        "ческую",
        "ческих",
        "ческими",
    }
)

# These words describe framing, a generic role or a facility, not the missing
# subject. Alone they would turn an unknown intent into a plausible-looking lie
# such as ``station`` or ``researchers``. They remain usable beside a real anchor.
_GLOSSARY_CONTEXT_ONLY = frozenset(
    {
        "aerial",
        "close up",
        "wide shot",
        "panorama",
        "drone",
        "slow motion",
        "scientists",
        "researchers",
        "expedition",
        "station",
        "instrument",
        "sample",
        "samples",
        "particles",
    }
)


# A topic is what a plan returns to, not what one of its scenes happens to be
# about: below two scenes a recurring word is a coincidence, not the subject.
_ANCHOR_MIN_SCENES = 2

# English function words carry no subject. Without this a plan whose subjects all
# start with "the" would anchor on "the", and every query would "keep the topic".
_ANCHOR_FUNCTION_WORDS = frozenset(
    {
        "a", "an", "the", "of", "in", "on", "at", "to", "into", "with", "and",
        "or", "for", "from", "by", "over", "under", "near", "its", "their",
    }
)


@dataclass(frozen=True)
class TopicAnchor:
    """The English form of the video's topic, and the evidence it was read from.

    ``stems`` is empty when the plan states a topic that has no English form in the
    plan at all. That is not "no topic": it is a topic nobody could check the
    queries against, and ``build_scene_queries`` records it rather than pretending
    the check passed.
    """

    text: str = ""
    stems: tuple[str, ...] = ()
    source: str = ANCHOR_SOURCE_UNRESOLVED
    topic_entity: str = ""

    @property
    def resolved(self) -> bool:
        return bool(self.stems)

    def carried_by(self, query: str) -> bool:
        """True when ``query`` still names the topic in some form.

        One shared stem is enough, and deliberately so: this is the same rule the
        C98 census counts by, so what the code enforces and what the measurement
        reports cannot drift apart. ``solar panels power plant`` keeps the topic of
        ``solar panel``; ``manufacturing plant`` does not.
        """

        return bool(set(_anchor_stems(query)) & set(self.stems))


def plan_topic_anchor(visual_plan: dict[str, Any]) -> TopicAnchor | None:
    """The anchor every query of ``visual_plan`` has to keep, or ``None``.

    ``None`` means the plan states no topic, so there is nothing to keep and
    nothing to report - the queries are built exactly as they were before C98.

    Two sources, both already English inside the plan:

    1. ``topic_entity`` itself, when the plan wrote it in English;
    2. otherwise the English ``subject``/``exact_entities`` its scenes return to.

    A Russian ``topic_entity`` is never rendered into English here. The same rule
    that keeps a guessed translation out of a query (K9) keeps it out of the
    anchor: a wrong anchor would be pushed into *every* query of the plan.
    """

    topic = _clean_query_text(str(visual_plan.get("topic_entity") or ""))
    if not topic:
        return None
    if _query_language(topic) == "en":
        stems = _anchor_stems(topic)
        if stems:
            return TopicAnchor(topic, stems, ANCHOR_SOURCE_TOPIC_ENTITY, topic)
        return TopicAnchor(topic_entity=topic)
    phrases = _plan_english_subject_phrases(visual_plan)
    scenes_by_stem: dict[str, set[int]] = {}
    for index, phrase in phrases:
        for stem in _anchor_stems(phrase):
            scenes_by_stem.setdefault(stem, set()).add(index)
    recurring = {
        stem
        for stem, scenes in scenes_by_stem.items()
        if len(scenes) >= _ANCHOR_MIN_SCENES
    }
    if not recurring:
        return TopicAnchor(topic_entity=topic)
    best_text = ""
    best_key: tuple[int, int, int] | None = None
    for position, (_, phrase) in enumerate(phrases):
        kept = [
            word
            for word in phrase.split()
            if (_anchor_stems(word) or ("",))[0] in recurring
        ]
        if not kept:
            continue
        text = " ".join(kept)
        # Most of the topic first, then the shortest way of saying it, then the
        # scene that said it first: one phrase, chosen the same way every run.
        key = (-len(_anchor_stems(text)), len(kept), position)
        if best_key is None or key < best_key:
            best_key, best_text = key, text
    if not best_text:
        return TopicAnchor(topic_entity=topic)
    return TopicAnchor(
        best_text, _anchor_stems(best_text), ANCHOR_SOURCE_SCENE_SUBJECTS, topic
    )


def _plan_english_subject_phrases(visual_plan: dict[str, Any]) -> list[tuple[int, str]]:
    """Every English thing the plan's scenes say they are *about*, scene by scene.

    Only ``exact_entities`` and ``subject``: place, action and mood describe the
    shot, and anchoring on them is how ``sunset`` became a query in the first place.
    """

    scenes = visual_plan.get("scenes")
    if not isinstance(scenes, list):
        return []
    phrases: list[tuple[int, str]] = []
    for index, scene in enumerate(scenes):
        if not isinstance(scene, dict):
            continue
        brief = _sub_dict(scene, "visual_brief")
        for value in [*(brief.get("exact_entities") or []), brief.get("subject")]:
            text = _english_only(str(value or ""))
            if text:
                phrases.append((index, text))
    return phrases


def _sub_dict(container: dict[str, Any], key: str) -> dict[str, Any]:
    """``container[key]`` when it is a mapping, ``{}`` otherwise.

    Tolerant readers keep meeting plans that wrote a scalar, a null or nothing at
    all where a mapping belongs. Reading it once instead of twice also lets the
    type checker see the narrowing, which is why this module leaves the mypy
    baseline with this slice.
    """

    value = container.get(key)
    return value if isinstance(value, dict) else {}


def _anchor_stems(value: str) -> tuple[str, ...]:
    """Content words of ``value``, folded to the one inflection stock English varies
    by. Order preserved and duplicates dropped, so the anchor reads as it was written."""

    stems: list[str] = []
    for token in _word_tokens(value):
        if len(token) < 2 or token in _ANCHOR_FUNCTION_WORDS:
            continue
        stem = _english_number_stem(token)
        if stem not in stems:
            stems.append(stem)
    return tuple(stems)


def _english_number_stem(word: str) -> str:
    if len(word) > 4 and word.endswith("ies"):
        return word[:-3] + "y"
    if len(word) > 4 and word.endswith(("ses", "xes", "zes", "ches", "shes")):
        return word[:-2]
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


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
    topic_anchor: TopicAnchor | None = None,
) -> SceneQueryPlan:
    """Build the queries every provider in ``providers`` should receive for ``scene``.

    ``topic_anchor`` is the plan's, not the scene's: a scene cannot tell that its
    own subject drifted off the topic of the video. Pass ``plan_topic_anchor(plan)``
    from the owner that holds the plan. Left ``None`` the queries are exactly what
    they were before C98, which is what a caller with no plan in hand should get.
    """
    caps = capabilities or {}
    source_queries = _source_language_queries(scene)
    english = _english_queries(scene, intent_language=intent_language)
    brief_ready = [
        item for item in english if item.get("source") == SOURCE_BRIEF_FIELDS
    ]
    adapted = [
        item for item in english if item.get("source") != SOURCE_BRIEF_FIELDS
    ]
    plan = SceneQueryPlan(scene_id=str(scene.get("scene_id") or ""), intent_language=intent_language)

    for provider in providers:
        languages = provider_query_languages(provider, caps.get(provider))
        candidates = [
            *_explicit_provider_queries(scene, provider),
            *brief_ready,
            *(
                {
                    **item,
                    "source": SOURCE_SAME_LANGUAGE,
                }
                for item in source_queries
            ),
            *adapted,
        ]
        chosen, dropped = _provider_ready_candidates(candidates, languages=languages)
        if topic_anchor is not None and topic_anchor.resolved:
            chosen = _anchored_to_topic(chosen, topic_anchor)
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
            plan.queries.extend(_dropped_records(provider, dropped, languages=languages))
            continue
        for index, item in enumerate(chosen):
            plan.queries.append(
                ProviderQuery(
                    provider=provider,
                    query=str(item["query"]),
                    language=str(item["language"]),
                    kind=str(item.get("kind") or "primary"),
                    fallback_level=int(item.get("fallback_level") or index + 1),
                    source=str(item.get("source") or SOURCE_BRIEF_FIELDS),
                    notes=str(item.get("notes") or ""),
                )
            )
        if topic_anchor is not None and not topic_anchor.resolved:
            plan.queries.append(_subject_unverified_record(provider, topic_anchor))
        plan.queries.extend(_dropped_records(provider, dropped, languages=languages))
    return plan


def _anchored_to_topic(
    chosen: list[dict[str, Any]],
    anchor: TopicAnchor,
) -> list[dict[str, Any]]:
    """Put the topic back into every English query of this scene that dropped it.

    Prepended, not substituted: the rest of the query is the scene's own evidence
    about what this shot shows, and it stays. A query that already names the topic
    is untouched, and a query written in another language is untouched too - an
    English anchor glued onto a Russian string would produce a mixed-script query
    that no provider in ``PROVIDER_QUERY_LANGUAGES`` can be searched with.

    Anchoring can make two different queries collide (``industrial plant`` and
    ``manufacturing plant`` both become the same anchored string once the topic is
    in front), so the result is deduplicated again here rather than sending the
    same request twice on the scene's budget.
    """

    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in chosen:
        query = str(item.get("query") or "")
        if str(item.get("language") or "") == "en" and not anchor.carried_by(query):
            anchored = " ".join(_terms([anchor.text, query]))
            item = {
                **item,
                "query": anchored,
                "notes": (
                    f"Запрос {query!r} не называл предмет темы "
                    f"({anchor.topic_entity!r}); добавлен якорь {anchor.text!r}, "
                    f"прочитанный из плана ({anchor.source})."
                ),
            }
            query = anchored
        key = _query_key(query)
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def _subject_unverified_record(provider: str, anchor: TopicAnchor) -> ProviderQuery:
    """The plan names a topic this module could not check the queries against."""

    return ProviderQuery(
        provider=provider,
        query="",
        language="en",
        kind="topic_anchor",
        fallback_level=0,
        source=SOURCE_BRIEF_FIELDS,
        status=STATUS_SUBJECT_UNVERIFIED,
        notes=(
            f"Тема плана {anchor.topic_entity!r} не имеет английской формы ни в "
            "одном subject/exact_entities этого плана: запросы отправлены без "
            "проверки предмета. Перевод не выдумывается; добавьте английский "
            "subject или provider_queries, чтобы проверка стала возможной."
        ),
    )


def _dropped_records(
    provider: str,
    dropped: list[dict[str, Any]],
    *,
    languages: tuple[str, ...],
) -> list[ProviderQuery]:
    """The queries this provider was *not* asked, and why.

    Appended after the sendable ones so the position of the plan's first entry -
    which existing readers use to tell a fully blocked scene from a working one -
    keeps its meaning.
    """

    supported = ", ".join(str(language).casefold() for language in languages)
    return [
        ProviderQuery(
            provider=provider,
            query=str(item["query"]),
            language=str(item["language"]),
            kind=str(item.get("kind") or "primary"),
            fallback_level=int(item.get("fallback_level") or 0),
            source=str(item.get("source") or SOURCE_BRIEF_FIELDS),
            status=STATUS_LANGUAGE_UNSUPPORTED,
            notes=(
                f"Запрос написан на {item['language']!r}, провайдер ищет только на "
                f"{supported!r}: не отправлен, бюджет не потрачен."
            ),
        )
        for item in dropped
    ]


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
    topic_anchor: TopicAnchor | None = None,
) -> SceneQueryPlan:
    """One targeted query per provider for exactly the semantic slot ``slot_name``.

    Built only from the author's own English brief fields, restricted to the ones
    ``SLOT_QUERY_FIELDS`` says that slot means. A provider that cannot search English,
    or a brief with nothing English to say about this slot, gets an explicit
    ``query_translation_required`` entry rather than a guessed or repeated query - the
    same honesty rule ``build_scene_queries`` already applies to the general query.

    A slot narrows a query on purpose, which is exactly how a subject gets dropped:
    the ``location`` slot of a scene whose place is ``sunset`` asks for ``sunset``.
    So the same ``topic_anchor`` applies here (C98). No ``query_subject_unverified``
    record is written on this path: a slot plan is transient - it is consumed by the
    targeted search and never persisted - and the scene's unverified mark is already
    in the plan that ``build_scene_queries`` wrote for the same scene.
    """
    caps = capabilities or {}
    plan = SceneQueryPlan(scene_id=str(scene.get("scene_id") or ""), intent_language="en")
    query_text = " ".join(_slot_english_terms(scene, slot_name))
    if query_text and topic_anchor is not None and topic_anchor.resolved:
        if not topic_anchor.carried_by(query_text):
            query_text = " ".join(_terms([topic_anchor.text, query_text]))
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
    brief = _sub_dict(scene, "visual_brief")
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
    brief = _sub_dict(scene, "visual_brief")
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
    brief = _sub_dict(scene, "visual_brief")
    exact = [str(item).strip() for item in (brief.get("exact_entities") or []) if str(item).strip()]
    subject = _english_only(str(brief.get("subject") or ""))
    action = _english_only(str(brief.get("action") or ""))
    place = _english_only(str(brief.get("place") or brief.get("location") or ""))
    must = [_english_only(str(item)) for item in (brief.get("must_include") or [])]
    shot = _english_only(str(brief.get("shot_type") or scene.get("shot_type") or ""))

    exact_english = [item for item in exact if _query_language(item) == "en"]
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
    if glossary_terms and not latin_terms and all(
        term in _GLOSSARY_CONTEXT_ONLY for term in glossary_terms
    ):
        glossary_terms = []
    combined = _terms(glossary_terms + latin_terms)
    if not combined:
        return []
    source = SOURCE_GLOSSARY if glossary_terms else SOURCE_LATIN_TOKENS
    return [{"query": " ".join(combined), "kind": "primary", "fallback_level": 2, "source": source}]


def _source_language_queries(scene: dict[str, Any]) -> list[dict[str, Any]]:
    """The planner's own queries, preserving structured provenance when present.

    The canonical legacy writer appends its broad compatibility query only to the
    flat ``alternative_queries`` list. It is not a ``visual_intent`` because it is
    not semantic evidence. Reading structured intents first therefore keeps the
    compatibility field persisted without presenting it as successful adaptation.
    Plans written before structured intents existed retain their tolerant flat read.
    """
    raw_intents = scene.get("visual_intents")
    structured = (
        [item for item in raw_intents if isinstance(item, dict)]
        if isinstance(raw_intents, list)
        else []
    )
    if structured:
        queries: list[dict[str, Any]] = []
        for index, intent in enumerate(structured, start=1):
            raw_terms = intent.get("terms")
            if isinstance(raw_terms, (list, tuple)):
                terms = [str(item).strip() for item in raw_terms if str(item).strip()]
            else:
                terms = [
                    str(item).strip()
                    for item in (
                        intent.get("subject"),
                        *(intent.get("modifiers") or []),
                        *(intent.get("context") or []),
                    )
                    if str(item or "").strip()
                ]
            text = " ".join(_terms(terms))
            if text:
                queries.append(
                    {
                        "query": text,
                        "kind": str(intent.get("kind") or "primary"),
                        "fallback_level": int(
                            intent.get("fallback_level") or index
                        ),
                    }
                )
        return queries

    queries = []
    primary = str(scene.get("primary_query") or "").strip()
    if primary and not _is_legacy_broad_query(primary):
        queries.append({"query": primary, "kind": "primary", "fallback_level": 1})
    for index, alternative in enumerate(scene.get("alternative_queries") or [], start=2):
        text = str(alternative).strip()
        if (
            text
            and not _is_legacy_broad_query(text)
            and all(text != item["query"] for item in queries)
        ):
            queries.append({"query": text, "kind": "alternative", "fallback_level": index})
    return queries


def _provider_ready_candidates(
    candidates: list[dict[str, Any]],
    *,
    languages: tuple[str, ...],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Filter and stably deduplicate candidates for one provider.

    Language belongs to each candidate string, not to the set it arrived in. This
    lets safe English alternatives survive beside a Russian primary while keeping
    every unsupported or mixed-script string away from an English-only provider.

    Returns the sendable candidates *and* the ones refused for their language, so
    the caller can record the refusal. Only the language refusal is returned: an
    empty string and a repeat of a query already chosen are not a loss of evidence,
    and reporting them would bury the one line a reader needs.
    """
    supported = {str(language).casefold() for language in languages}
    seen: set[str] = set()
    chosen: list[dict[str, Any]] = []
    dropped: list[dict[str, Any]] = []
    for item in candidates:
        query = _clean_query_text(str(item.get("query") or ""))
        language = _query_language(query)
        key = _query_key(query)
        if not query or not language or key in seen:
            continue
        if language not in supported:
            seen.add(key)
            dropped.append({**item, "query": query, "language": language})
            continue
        seen.add(key)
        chosen.append({**item, "query": query, "language": language})
    return chosen, dropped


def _glossary_terms(scene: dict[str, Any]) -> list[str]:
    text = " ".join(
        str(scene.get(key) or "")
        for key in ("narration", "visual_description", "visual_intent", "primary_query")
    )
    tokens = _word_tokens(text)
    if not tokens:
        return []
    matched: list[str] = []
    for russian, english in GLOSSARY.items():
        if (
            _contains_lexicon_phrase(tokens, _word_tokens(russian))
            and english not in matched
        ):
            matched.append(english)
    return matched


def _latin_terms(scene: dict[str, Any]) -> list[str]:
    semantic = _sub_dict(scene, "semantic")
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
    text = _clean_query_text(value)
    return text if _query_language(text) == "en" else ""


def _terms(values: list[str]) -> list[str]:
    seen: set[str] = set()
    words: list[str] = []
    for value in values:
        for word in str(value or "").split():
            key = _normalize_text(word)
            if key and key not in seen:
                seen.add(key)
                words.append(word)
    return words[:_MAX_QUERY_TERMS]


def _contains_lexicon_phrase(tokens: list[str], phrase: list[str]) -> bool:
    if not phrase or len(phrase) > len(tokens):
        return False
    for start in range(len(tokens) - len(phrase) + 1):
        if all(
            _lexicon_token_matches(token, expected)
            for token, expected in zip(
                tokens[start : start + len(phrase)],
                phrase,
            )
        ):
            return True
    return False


def _lexicon_token_matches(token: str, expected: str) -> bool:
    if token == expected:
        return True
    if expected in _GLOSSARY_STEMS:
        return (
            token.startswith(expected)
            and token[len(expected) :] in _GLOSSARY_STEM_ENDINGS
        )
    return _russian_morph_key(token) == _russian_morph_key(expected)


def _russian_morph_key(token: str) -> str:
    if not _CYRILLIC_RE.search(token):
        return token
    for suffix in _RUSSIAN_INFLECTION_SUFFIXES:
        if token.endswith(suffix) and len(token) - len(suffix) >= 4:
            return token[: -len(suffix)]
    return token


def _word_tokens(value: str) -> list[str]:
    return _WORD_RE.findall(_normalize_text(value))


def _query_language(value: str) -> str:
    text = _normalize_text(value)
    if not text:
        return ""
    if _CYRILLIC_RE.search(text):
        return "ru"
    if _LATIN_RE.search(text):
        return "en"
    return ""


def _query_key(value: str) -> str:
    return " ".join(_normalize_text(value).split())


def _is_legacy_broad_query(value: str) -> bool:
    return _query_key(value) in _LEGACY_BROAD_QUERIES


def _clean_query_text(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value or "").split())


def _normalize_text(value: str) -> str:
    return unicodedata.normalize("NFKC", value or "").casefold().replace("ё", "е")


__all__ = [
    "GLOSSARY",
    "PROVIDER_QUERY_LANGUAGES",
    "SLOT_QUERY_FIELDS",
    "SOURCE_BRIEF_FIELDS",
    "SOURCE_EXPLICIT",
    "SOURCE_GLOSSARY",
    "SOURCE_LATIN_TOKENS",
    "SOURCE_SAME_LANGUAGE",
    "ANCHOR_SOURCE_SCENE_SUBJECTS",
    "ANCHOR_SOURCE_TOPIC_ENTITY",
    "ANCHOR_SOURCE_UNRESOLVED",
    "STATUS_LANGUAGE_UNSUPPORTED",
    "STATUS_OK",
    "STATUS_SUBJECT_UNVERIFIED",
    "STATUS_TRANSLATION_REQUIRED",
    "ProviderQuery",
    "SceneQueryPlan",
    "TopicAnchor",
    "build_scene_queries",
    "build_slot_queries",
    "plan_topic_anchor",
    "provider_query_languages",
]
