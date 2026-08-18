"""The controlled expansion ladder: one provider-language idea, several queries.

Search failed for two different reasons and only one of them was a language problem.
The other was that every scene got *one* string. A single exact query either hits or
returns nothing, and nothing is what the confirmed runs returned. The pre-Q2 engine
answered this with four fixed English strings for every video ever made; the legacy
documentary engine answered it with a real ladder, but one that required English
keywords on the way in and carried a channel's topic literals on the way out.

This module keeps the ladder and drops both of those. It expands an idea that is
*already* in the provider's language - produced by ``brief.produce_brief`` from the
script's own evidence, or written by the author - into progressively wider queries:

    1. the exact subject, under its exact name
    2. the subject and what it is doing
    3. the subject, what it is doing and where
    4. the entity's other names (alternatives, never invented synonyms)
    5. a wider, meaning-preserving context
    6. the same idea seen as its environment instead of its subject
    7. the leading query truncated to its two most specific terms

There is no vocabulary here, no synonym table and no translator: rungs 4 and 5 use
names the evidence already carries. An idea with nothing in the provider's language
expands to nothing, which is the honest outcome and the one the query adapter is
built to report.

``must_avoid`` is part of what a query *means*, not a post-filter on results: a scene
that says "not a dolphin" must never send a query that asks for one, so a rung whose
words contain an avoided phrase is dropped before it is ever offered.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

from src.content.script_engine.text_analysis import STOPWORDS

# Both limits come from the legacy ladder: a cap on how many variants exist at all,
# and a smaller cap on how many are actually executed. Widening search is only useful
# while it stays bounded - the failure mode being replaced is a scene that asks a
# provider the same thing twelve times.
MAX_EXPANSION_QUERIES = 12
MAX_PROVIDER_QUERIES = 4

# The active remote providers all search English indexes; this layer packages English
# evidence and never produces it.
PROVIDER_LANGUAGE = "en"

_MAX_QUERY_TERMS = 8
_MIN_QUERY_TERMS = 2

_PROVIDER_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9.'-]*")
# The same token shape without the alphabet, for comparing a ban with a query rather
# than for building one. Building is deliberately Latin-only - the active providers
# search English indexes - but *refusing* is not: a ban the author wrote in the
# script's own language tokenised to nothing under the rule above, so it vetoed
# nothing at all, not even a query written in that same language (C104).
_AVOIDED_TOKEN_RE = re.compile(r"[^\W\d_](?:[^\W_]|[.'-])*", re.UNICODE)
_CYRILLIC_RE = re.compile(r"[Ѐ-ӿ]")

# A query made only of production vocabulary is a plausible-looking substitute, not
# evidence of what is in frame. Topic/domain nouns are deliberately absent here, and
# the legacy ladder's mood and style suffixes ("cinematic", "documentary footage")
# are deliberately *not* migrated: they widen the wording, not the idea.
NON_FACTUAL_QUERY_TERMS = frozenset(
    {
        "broll",
        "channel",
        "cinematic",
        "clip",
        "content",
        "footage",
        "generic",
        "image",
        "images",
        "nature",
        "observation",
        "photo",
        "photos",
        "scene",
        "science",
        "shot",
        "topic",
        "unknown",
        "video",
    }
)


@dataclass(frozen=True)
class QueryPlanningInput:
    """One scene's idea, normalised into the language a provider can search.

    Deliberately not a scene, a brief or a plan: the ladder must be reusable by any
    workflow, template or format, so it is given the meaning and nothing else.
    """

    subject: str = ""
    action: str = ""
    place: str = ""
    # Other names for the same thing - "Orcinus orca" beside "killer whale". These are
    # the only synonyms this layer will ever use, because they are the only ones the
    # evidence actually stated.
    entities: tuple[str, ...] = ()
    # What surrounds the subject without replacing it.
    context: tuple[str, ...] = ()
    must_avoid: tuple[str, ...] = ()

    @property
    def is_empty(self) -> bool:
        return not any([self.subject, self.action, self.place, self.entities, self.context])


def provider_language_text(value: object) -> str:
    """A single field in the provider's language, or an empty string.

    A brief field left in the source language is not an English query and must not be
    smuggled into one; neither is a path, a URL or a slug.
    """
    text = " ".join(str(value or "").split())
    if not text or _CYRILLIC_RE.search(text) or _looks_like_locator(text):
        return ""
    return text if _PROVIDER_TOKEN_RE.search(text) else ""


def provider_language_query(values: list[str]) -> str:
    """One query string built from ``values``, most specific term first.

    One word is usually a category or a name with too little scene intent to search
    truthfully, so the two-term floor is kept: it is also what rejects bare slugs and
    labels.
    """
    terms: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = " ".join(str(value or "").split())
        if not text or _CYRILLIC_RE.search(text) or _looks_like_locator(text):
            continue
        for token in _PROVIDER_TOKEN_RE.findall(text):
            key = token.casefold()
            if key in STOPWORDS or key in NON_FACTUAL_QUERY_TERMS or key in seen:
                continue
            seen.add(key)
            terms.append(token)
            if len(terms) >= _MAX_QUERY_TERMS:
                break
        if len(terms) >= _MAX_QUERY_TERMS:
            break
    return " ".join(terms) if len(terms) >= _MIN_QUERY_TERMS else ""


def planning_input(
    *,
    subject: object = "",
    action: object = "",
    place: object = "",
    entities: list[object] | tuple[object, ...] = (),
    context: list[object] | tuple[object, ...] = (),
    must_avoid: list[object] | tuple[object, ...] = (),
) -> QueryPlanningInput:
    """Normalise stated meaning into the ladder's input. Nothing is inferred."""
    return QueryPlanningInput(
        subject=provider_language_text(subject),
        action=provider_language_text(action),
        place=provider_language_text(place),
        entities=tuple(_unique(provider_language_text(item) for item in entities)),
        context=tuple(_unique(provider_language_text(item) for item in context)),
        # Kept in whatever language it was written in: an avoided phrase only has to
        # match the query, and the query is compared to it token by token.
        must_avoid=tuple(_unique(" ".join(str(item or "").split()) for item in must_avoid)),
    )


def planning_input_from_scene(scene: object) -> QueryPlanningInput:
    """Read the ladder's input off a planned scene and the brief it carries.

    The brief wins field by field, exactly as it does everywhere else: an author who
    stated the subject has stated it for the query too.
    """
    brief = getattr(scene, "brief", None)
    return planning_input(
        subject=_first(_of(brief, "subject"), _of(scene, "subject")),
        action=_first(_of(brief, "action"), _of(scene, "action")),
        place=_first(_of(brief, "place"), _of(scene, "place")),
        entities=[
            *(_of(brief, "exact_entities") or []),
            *(_of(scene, "secondary_subjects") or []),
        ],
        context=[
            *(_of(brief, "must_include") or []),
            *(_of(scene, "must_include") or []),
        ],
        must_avoid=[
            *(_of(brief, "must_avoid") or []),
            *(_of(scene, "must_avoid") or []),
        ],
    )


def expand_queries(
    data: QueryPlanningInput,
    *,
    seeds: list[str] | tuple[str, ...] = (),
    limit: int = MAX_EXPANSION_QUERIES,
) -> list[str]:
    """The ladder for one idea: ``seeds`` first, then progressively wider rungs.

    ``seeds`` are queries the evidence already produced verbatim (structured intents,
    prepared script keywords, a linked claim, an author's own provider queries). They
    lead because nothing this function builds can be more exact than they are.
    """
    subject, action, place = data.subject, data.action, data.place
    entities = list(data.entities)
    context = list(data.context)
    head_entity = entities[0] if entities else ""

    rungs: list[list[str]] = [
        # Rungs 1-3: the exact subject, then what it is doing, then where.
        [head_entity, subject],
        [subject, action],
        [subject, action, place],
        # Rung 4: the entity's other stated names. Never an invented synonym.
        entities,
        # Rungs 5-5b: wider, without changing what the scene is about.
        [subject, place],
        [subject, *context[:1]],
        # Rung 6: the same idea as its environment rather than its subject.
        [place, *context[:1]],
        [place, *entities[:1]],
    ]

    stated: list[str] = []
    for value in seeds:
        query = " ".join(str(value or "").split())
        if query:
            stated.append(query)

    ordered = list(stated)
    for parts in rungs:
        query = provider_language_query([part for part in parts if part])
        if query:
            ordered.append(query)

    # Rung 7, from the legacy ladder: the leading stated query truncated to its two
    # most specific terms. A long exact query and its short form fail differently.
    # Applied only to what the evidence stated as one phrase - truncating a rung this
    # function composed would cut a phrase in half and change what it asks for.
    ordered.extend(_truncations(stated[:1]))

    allowed = [query for query in _dedupe(ordered) if not _mentions_avoided(query, data.must_avoid)]
    return allowed[: max(0, limit)]


def mentions_avoided(text: str, must_avoid: Iterable[str]) -> bool:
    """True when ``text`` asks for something the scene said not to show.

    The ladder's own test, exported so anything that *produces* meaning can refuse it
    with the same comparison the ladder applies to a finished query. A second answer to
    "does this ask for the forbidden thing" is how a phrase gets blocked in the query
    and allowed in the brief it was built from.
    """
    return _mentions_avoided(" ".join(str(text or "").split()), tuple(must_avoid))


def _truncations(queries: list[str]) -> list[str]:
    short: list[str] = []
    for query in queries:
        terms = query.split()
        if len(terms) > _MIN_QUERY_TERMS:
            short.append(" ".join(terms[:_MIN_QUERY_TERMS]))
    return short


def _mentions_avoided(query: str, must_avoid: tuple[str, ...]) -> bool:
    """True when ``query`` asks for something the scene said not to show.

    Matched as a consecutive token phrase, so "Suez Canal" does not veto a query about
    the Panama Canal and "blue whale" does not veto one about whale watching. Both
    sides are tokenised with the same provider-token rule used to build queries, so
    punctuation ("Panama Canal," or a truncated "Panama Canal.") cannot smuggle an
    avoided phrase past a raw-whitespace split.
    """
    tokens = _avoided_match_tokens(query)
    for phrase in must_avoid:
        wanted = _avoided_match_tokens(phrase)
        if not wanted or len(wanted) > len(tokens):
            continue
        for start in range(len(tokens) - len(wanted) + 1):
            if tokens[start : start + len(wanted)] == wanted:
                return True
    return False


def _avoided_match_tokens(text: str) -> list[str]:
    """Case-normalised tokens for ``_mentions_avoided`` comparison, in any script.

    Same token shape as the one queries are built from, minus its alphabet: a word
    starts with a letter and may carry digits or ``.``/``'``/``-`` afterwards, so an
    abbreviation like "U.S." tokenises whole. That rule leaves ordinary sentence
    punctuation ("Canal." at a truncation boundary) stuck to the last word, stripped
    here on both sides of the comparison so it cannot hide a match.

    The alphabet is dropped because a ban is not a query. Queries stay Latin-only - the
    providers search English indexes - but the ban is kept in whatever language its
    author wrote it in, and under ``_PROVIDER_TOKEN_RE`` a Cyrillic ban produced an
    empty token list and therefore matched nothing at all: not the English query it was
    never comparable with, and not the Russian one naming the forbidden thing verbatim.
    What this does not do is bridge two scripts - "люди" still does not match "people",
    and that bridge is a translation contract, not a tokeniser.
    """
    return [token.strip(".'-").casefold() for token in _AVOIDED_TOKEN_RE.findall(text)]


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        key = " ".join(value.casefold().split())
        if key and key not in seen:
            seen.add(key)
            result.append(value)
    return result


def _unique(values) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        text = str(value or "").strip()
        key = text.casefold()
        if text and key not in seen:
            seen.add(key)
            ordered.append(text)
    return ordered


def _looks_like_locator(value: str) -> bool:
    lowered = value.casefold()
    return any(marker in lowered for marker in ("://", "\\", "/", "_"))


def _of(source: object, key: str):
    if source is None:
        return None
    return source.get(key) if isinstance(source, dict) else getattr(source, key, None)


def _first(*values: object) -> str:
    for value in values:
        text = " ".join(str(value or "").split())
        if text:
            return text
    return ""


__all__ = [
    "MAX_EXPANSION_QUERIES",
    "MAX_PROVIDER_QUERIES",
    "NON_FACTUAL_QUERY_TERMS",
    "PROVIDER_LANGUAGE",
    "QueryPlanningInput",
    "expand_queries",
    "mentions_avoided",
    "planning_input",
    "planning_input_from_scene",
    "provider_language_query",
    "provider_language_text",
]
