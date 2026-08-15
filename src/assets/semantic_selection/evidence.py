"""What a provider's metadata can, and cannot, confirm about an asset.

Split out of ``candidate_ranker`` at stage Q2.2A-2 so that the score and the slot
decision read the same evidence through the same rules. Before the split the ranker
was the only thing that knew what counted as evidence; the slot layer needed exactly
that knowledge, and a second copy of it would have been a second answer to the same
question.

The rules themselves are unchanged:

- Only fields a provider really wrote about the asset are evidence. ``search_query``
  is excluded unconditionally, and a field whose whole value *is* the query repeated
  back is dropped with it.
- Absent metadata is reported as absent (``metadata_status="unavailable"``), never
  rounded up to a match.
- A term written in a script the metadata cannot contain is *undecidable*, not
  unmatched: an English title neither confirms nor denies a Russian subject.

What C79 corrected is not a rule but a disagreement. Extraction has always stemmed:
``visual_planning.entities`` groups ``панель`` and ``панелей`` under one key and picks
a scene's subject out of that group. This side had only a prefix relation, which cannot
express Russian inflection at all - Russian changes the character *at* the boundary, so
``панель`` and ``панелей`` share no prefix - and a scene's own subject went unmatched in
metadata that named it. The same stemmer is now reused here, as an addition to the
prefix relation rather than a replacement for it.

That closes the half of C79 these primitives own, and not the other half. Every question
asked through ``semantic_stem_score`` - the slot verdict, the support status, the
required-slot refusal - now reads an inflected word as the word it is. The ranker's
weighted average still asks ``semantic_literal_score`` about the same derived
description, so it still reads that word as absent, and it is the half that decides
whether a candidate is selected. That is ``C89``, and it is a bounded slice of its own:
the one-line swap was measured against the frozen PLAN-9D ground truth and moved a scene
off the annotator's preferred candidate, which is not a change to make in passing.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

METADATA_AVAILABLE = "available"
METADATA_UNAVAILABLE = "unavailable"
METADATA_QUERY_DERIVED = "query_derived_only"

# Fields emitted by the canonical ``AssetCandidate`` contract that carry prose written
# by the provider about the asset. Provider labels live in ``tags``; ``keywords`` is a
# tolerated compatibility alias added by manifest adapters. Deliberately excludes
# ``search_query``/``query`` and anything derived from them.
METADATA_FIELDS = ("title", "description")
TAG_FIELDS = ("tags", "keywords")
VISION_EVIDENCE_FIELDS = (
    "vision_tags",
    "vision_tags_asset_id",
    "vision_tags_source_sha256",
    "vision_tags_cache_key",
)
QUERY_FIELDS = ("search_query", "query")

WORD_RE = re.compile(r"[^\W_]+", re.UNICODE)
CYRILLIC_RE = re.compile(r"[Ѐ-ӿ]")

# Shortest word for which a shared prefix is meaningful. "antarctic"/"antarctica" is a
# morphological variant of one name; "car"/"cargo" is not, and four letters is not
# enough to tell those apart. The floor guards both relations in
# ``morphological_variant``, which the slot layer reaches through ``semantic_stem_score``.
MIN_STEM_LENGTH = 5

# A positive multiword claim from broad prose is coherent only when all of its words
# fit inside a small lexical neighbourhood. Six intervening words allow ordinary
# descriptions ("hummingbird hovering almost motionless in the open air") while
# refusing tokens collected from unrelated sentences or catalogue sections. Strong
# provider labels (title/tags/keywords) are already bounded fields and do not need this
# window. Boundary behaviour is covered by PLAN-9C-3 regressions.
LOCAL_MATCH_MAX_GAP = 6

# One word in a free-form description is useful supporting evidence, but it cannot by
# itself prove that a catalogue item depicts that entity. Titles, provider tags and
# Vision tags remain full-strength. A multiword phrase/local window in a description
# may also remain full-strength, regardless of the description's total length.
DESCRIPTION_SINGLE_WORD_SCORE = 75.0


@dataclass(frozen=True)
class EvidenceField:
    """One provider-authored field, kept separate so provenance is not flattened."""

    name: str
    text: str

    @property
    def token_sequence(self) -> tuple[str, ...]:
        return tuple(WORD_RE.findall(self.text.lower()))

    @property
    def token_set(self) -> set[str]:
        return set(self.token_sequence)


def provider_evidence_fields(candidate: dict[str, Any]) -> tuple[EvidenceField, ...]:
    """Provider-authored evidence with field boundaries preserved.

    The old evidence path joined everything before matching. That made unrelated words
    in a long description indistinguishable from a coherent title or provider tag.
    """
    queries = {str(candidate.get(key) or "").strip().lower() for key in QUERY_FIELDS}
    queries.discard("")
    fields: list[EvidenceField] = []
    for key in METADATA_FIELDS:
        values = evidence_values(candidate.get(key, ""), queries)
        if values:
            fields.append(EvidenceField(key, _normalize_text(" ".join(values))))
    if str(candidate.get("tags_source") or "provider") != "query_derived":
        for key in TAG_FIELDS:
            values = evidence_values(candidate.get(key, ""), queries)
            if values:
                fields.append(EvidenceField(key, _normalize_text(" ".join(values))))
    return tuple(field for field in fields if field.text)


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").lower()).strip()


def provider_evidence_text(candidate: dict[str, Any]) -> str:
    """Everything the *provider* said about this asset - and nothing we said to it.

    Tags are excluded when the provider admits it synthesised them from the query
    (``tags_source="query_derived"``), which is what the Pexels adapter does for videos
    because the API returns no description.
    """
    return _normalize_text(" ".join(field.text for field in provider_evidence_fields(candidate)))


def evidence_values(value: Any, queries: set[str]) -> list[str]:
    """One metadata field as evidence, unless the field *is* the query repeated back.

    The check is whole-value equality on purpose: a real title that happens to contain
    the searched words is genuine evidence and must not be thrown away with it.
    """
    values = [str(item) for item in value] if isinstance(value, list) else [str(value)]
    return [item for item in values if item.strip() and item.strip().lower() not in queries]


def metadata_status(candidate: dict[str, Any], text: str, vision_tags: list[str]) -> tuple[str, float]:
    """How much real provider metadata there is, and how far it can be trusted.

    Never returns a high score for an absence: an unlabelled candidate scores 0 and is
    reported as such, instead of matching everything by default.
    """
    if str(candidate.get("tags_source") or "") == "query_derived" and not text:
        return METADATA_QUERY_DERIVED, 0.0
    if not text:
        return (METADATA_AVAILABLE, 20.0) if vision_tags else (METADATA_UNAVAILABLE, 0.0)
    words = tokens(text)
    # Three descriptive words is the least that can distinguish one asset from another.
    score = min(100.0, 100.0 * len(words) / 8.0)
    return METADATA_AVAILABLE, round(score, 3)


def tokens(text: str) -> set[str]:
    """Words in any script. A ``[a-z0-9]+`` pattern silently drops every Cyrillic
    token, so a Russian ``must_avoid`` could never match anything."""
    return set(WORD_RE.findall(text.lower()))


def script_mismatch(concept: str, text: str) -> bool:
    """True when ``concept`` and ``text`` are written in scripts that cannot overlap.

    Absent evidence is *not* a script mismatch. A provider that returned no metadata
    told us nothing rather than something incomparable, and treating that as merely
    "unverifiable" would let an unlabelled candidate slip past a requirement it plainly
    cannot meet.
    """
    if not concept or not text:
        return False
    return bool(CYRILLIC_RE.search(concept)) != bool(CYRILLIC_RE.search(text))


def concept_score(concept: str, token_set: set[str], text: str) -> float:
    """Literal match: the whole phrase, or the share of its words present verbatim."""
    normalized = concept.lower().strip()
    if not normalized:
        return 100.0
    if normalized in text:
        return 100.0
    words = [word for word in WORD_RE.findall(normalized) if word]
    if not words:
        return 0.0
    matched = sum(1 for word in words if word in token_set)
    return 100.0 * matched / len(words)


def contains_concept(concept: str, token_set: set[str], text: str) -> bool:
    return concept_score(concept, token_set, text) >= 99.0


_ENTITY_STEM: Callable[[str], str] | None = None


def _entity_stem() -> Callable[[str], str]:
    """``visual_planning.entities.stem``, resolved on first use and kept.

    Imported here rather than at module scope because at module scope it is a cycle:
    ``visual_planning``'s package import reaches ``script_engine.text_analysis`` and
    from there ``src.news``, which imports this subpackage back - measured, not feared.
    Deferring it to the first comparison lets the same one stemmer be reused without
    either side having to be loaded first, and ``sys.modules`` caches the module, so
    this costs a lookup rather than an import.
    """
    global _ENTITY_STEM
    if _ENTITY_STEM is None:
        from src.content.visual_planning.entities import stem

        _ENTITY_STEM = stem
    return _ENTITY_STEM


def morphological_variant(word: str, other: str) -> bool:
    """Whether two words of evidence length are inflections of one word.

    Two relations, and the second only ever adds to the first:

    - a **shared prefix**, from five characters up. ``Antarctica`` in a brief and
      ``antarctic`` in a title are the same place, and a slot that calls that "missing"
      refuses correct material for a suffix. The floor keeps this a spelling allowance
      rather than a guess: ``sampling`` and ``samples`` do not match;
    - a **shared stem**, computed by the one stemmer this repository has -
      ``visual_planning.entities.stem``, the key extraction already groups a scene's
      words by. The prefix relation cannot reach a Russian inflection, because Russian
      changes the character at the boundary: ``панель`` and ``панелей`` diverge at the
      sixth letter and share no prefix, yet extraction had already called them one word.

    Neither relation is weakened by the other's presence, and the pair that documents
    the floor is still refused by both. The stemmer strips Cyrillic endings only, so on
    a Latin pair stem equality collapses to plain equality and every English case above
    is decided exactly as it was before - which is why ``antarctica``/``antarctic``
    still needs the prefix relation and could not be replaced by this one.
    """
    if len(word) < MIN_STEM_LENGTH or len(other) < MIN_STEM_LENGTH:
        return False
    if other.startswith(word) or word.startswith(other):
        return True
    # ``stem`` never returns a stub for a word this long: it strips an ending only when
    # at least ``MIN_STEM_CHARS`` survive, and returns the word untouched otherwise.
    stem = _entity_stem()
    return stem(word) == stem(other)


def stem_match(word: str, token_set: set[str]) -> bool:
    """Whether ``word`` appears in the evidence, allowing a morphological variant."""
    if word in token_set:
        return True
    if len(word) < MIN_STEM_LENGTH:
        return False
    return any(morphological_variant(word, other) for other in token_set)


def stem_concept_score(concept: str, token_set: set[str], text: str) -> float:
    """Like ``concept_score``, but tolerant of morphological variants.

    Used for the *derived* description of a scene (subject, action, place, context),
    which is prose written by an author rather than a name that must survive verbatim.
    The author's literal requirements (``must_include``) are still checked literally.
    """
    normalized = concept.lower().strip()
    if not normalized:
        return 100.0
    if normalized in text:
        return 100.0
    words = [word for word in WORD_RE.findall(normalized) if word]
    if not words:
        return 0.0
    matched = sum(1 for word in words if stem_match(word, token_set))
    return 100.0 * matched / len(words)


def semantic_concept_score(
    concept: str,
    fields: tuple[EvidenceField, ...],
    *,
    stem: bool = False,
) -> float:
    """Positive semantic evidence, preserving field quality and lexical locality.

    Hard requirements and declared conflicts intentionally continue to use the strict
    corpus-wide literal/stem primitives above. Weakening negative evidence would turn
    this correctness repair into a way around ``must_avoid``.
    """
    normalized = concept.lower().strip()
    if not normalized:
        return 100.0
    words = [word for word in WORD_RE.findall(normalized) if word]
    if not words:
        return 0.0
    scores: list[float] = []
    for evidence_field in fields:
        if evidence_field.name == "description":
            scores.append(_description_concept_score(words, evidence_field.token_sequence, stem=stem))
            continue
        scorer = stem_concept_score if stem else concept_score
        scores.append(scorer(concept, evidence_field.token_set, evidence_field.text))
    return max(scores, default=0.0)


def _description_concept_score(
    words: list[str],
    sequence: tuple[str, ...],
    *,
    stem: bool,
) -> float:
    if not sequence:
        return 0.0
    if len(words) == 1:
        return (
            DESCRIPTION_SINGLE_WORD_SCORE
            if any(_token_matches(words[0], token, stem=stem) for token in sequence)
            else 0.0
        )

    window_size = len(words) + LOCAL_MATCH_MAX_GAP
    best = 0
    for start in range(len(sequence)):
        window = sequence[start : start + window_size]
        matched = sum(
            1
            for word in words
            if any(_token_matches(word, token, stem=stem) for token in window)
        )
        best = max(best, matched)
        if best == len(words):
            return 100.0
    return 100.0 * best / len(words)


def _token_matches(word: str, token: str, *, stem: bool) -> bool:
    if word == token:
        return True
    return stem and morphological_variant(word, token)


@dataclass(frozen=True)
class CandidateEvidence:
    """One candidate's provider metadata, read once and asked many questions."""

    text: str = ""
    token_set: frozenset[str] = field(default_factory=frozenset)
    vision_tags: tuple[str, ...] = ()
    fields: tuple[EvidenceField, ...] = ()
    metadata_status: str = METADATA_UNAVAILABLE
    metadata_score: float = 0.0

    @property
    def has_metadata(self) -> bool:
        """True when there is something to judge on at all."""
        return self.metadata_status == METADATA_AVAILABLE or bool(self.vision_tags)

    def is_undecidable(self, concept: str) -> bool:
        """The term cannot be compared with this evidence, in either direction."""
        if not self.has_metadata:
            return True
        return script_mismatch(concept, self.text)

    def literal_score(self, concept: str) -> float:
        return concept_score(concept, set(self.token_set), self.text)

    def stem_score(self, concept: str) -> float:
        return stem_concept_score(concept, set(self.token_set), self.text)

    def semantic_literal_score(self, concept: str) -> float:
        return semantic_concept_score(concept, self.fields, stem=False)

    def semantic_stem_score(self, concept: str) -> float:
        return semantic_concept_score(concept, self.fields, stem=True)

    def contains(self, concept: str) -> bool:
        return contains_concept(concept, set(self.token_set), self.text)


def bind_vision_tags(
    candidate: dict[str, Any],
    tags: list[str],
    *,
    source_sha256: str,
    cache_key: str,
) -> dict[str, Any]:
    """Attach Vision evidence to the candidate and source snapshot it observed."""
    normalized = list(dict.fromkeys(str(tag).strip() for tag in tags if str(tag).strip()))
    candidate["vision_tags"] = normalized
    candidate["vision_tags_asset_id"] = str(candidate.get("asset_id") or "")
    candidate["vision_tags_source_sha256"] = str(source_sha256 or "")
    candidate["vision_tags_cache_key"] = str(cache_key or "")
    return candidate


def carry_vision_evidence(source: dict[str, Any], target: dict[str, Any]) -> dict[str, Any]:
    """Carry only the canonical Vision evidence envelope during object rebuilds."""
    for field_name in VISION_EVIDENCE_FIELDS:
        if field_name in source:
            value = source[field_name]
            target[field_name] = list(value) if field_name == "vision_tags" else value
    return target


def current_vision_tags(candidate: dict[str, Any]) -> tuple[str, ...]:
    """Return Vision tags only when their candidate/bytes binding is still valid."""
    tags = tuple(str(tag).lower() for tag in candidate.get("vision_tags", []) or [])
    if not tags:
        return ()
    asset_id = str(candidate.get("asset_id") or candidate.get("id") or "").strip()
    bound_asset_id = str(candidate.get("vision_tags_asset_id") or "").strip()
    if not asset_id or not bound_asset_id or bound_asset_id != asset_id:
        return ()
    current_sha256 = str(candidate.get("checksum_sha256") or "").strip().casefold()
    source_sha256 = str(candidate.get("vision_tags_source_sha256") or "").strip().casefold()
    cache_key = str(candidate.get("vision_tags_cache_key") or "").strip()
    if not current_sha256 or not source_sha256 or not cache_key:
        return ()
    if source_sha256 != current_sha256:
        return ()
    return tags


def build_evidence(candidate: dict[str, Any]) -> CandidateEvidence:
    provider_fields = provider_evidence_fields(candidate)
    text = _normalize_text(" ".join(field.text for field in provider_fields))
    vision_tags = current_vision_tags(candidate)
    vision_fields = (
        (EvidenceField("vision_tags", _normalize_text(" ".join(vision_tags))),)
        if vision_tags
        else ()
    )
    status, score = metadata_status(candidate, text, list(vision_tags))
    return CandidateEvidence(
        text=text,
        token_set=frozenset(tokens(text)) | frozenset(vision_tags),
        vision_tags=vision_tags,
        fields=provider_fields + vision_fields,
        metadata_status=status,
        metadata_score=score,
    )


__all__ = [
    "CYRILLIC_RE",
    "DESCRIPTION_SINGLE_WORD_SCORE",
    "EvidenceField",
    "LOCAL_MATCH_MAX_GAP",
    "METADATA_AVAILABLE",
    "METADATA_FIELDS",
    "METADATA_QUERY_DERIVED",
    "METADATA_UNAVAILABLE",
    "MIN_STEM_LENGTH",
    "QUERY_FIELDS",
    "TAG_FIELDS",
    "WORD_RE",
    "CandidateEvidence",
    "build_evidence",
    "concept_score",
    "contains_concept",
    "evidence_values",
    "metadata_status",
    "morphological_variant",
    "provider_evidence_fields",
    "provider_evidence_text",
    "semantic_concept_score",
    "script_mismatch",
    "stem_concept_score",
    "stem_match",
    "tokens",
]
