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
"""

from __future__ import annotations

import re
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
# enough to tell those apart. Used only by the slot layer - see ``stem_match``.
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


def stem_match(word: str, token_set: set[str]) -> bool:
    """Whether ``word`` appears in the evidence, allowing a morphological variant.

    ``Antarctica`` in a brief and ``antarctic`` in a title are the same place, and a
    slot that calls that "missing" refuses correct material for a suffix. Only a
    genuine prefix relation counts, and only from five characters up, so this stays a
    spelling allowance rather than a guess: ``sampling`` and ``samples`` do not match.
    """
    if word in token_set:
        return True
    if len(word) < MIN_STEM_LENGTH:
        return False
    return any(
        len(other) >= MIN_STEM_LENGTH and (other.startswith(word) or word.startswith(other))
        for other in token_set
    )


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
    if not stem or len(word) < MIN_STEM_LENGTH or len(token) < MIN_STEM_LENGTH:
        return False
    return token.startswith(word) or word.startswith(token)


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
    "provider_evidence_fields",
    "provider_evidence_text",
    "semantic_concept_score",
    "script_mismatch",
    "stem_concept_score",
    "stem_match",
    "tokens",
]
