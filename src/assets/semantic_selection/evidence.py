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

# Fields that carry description written by the provider about the asset. Deliberately
# excludes ``search_query``/``query`` and anything derived from them.
METADATA_FIELDS = ("title", "description", "categories", "depicts", "location")
QUERY_FIELDS = ("search_query", "query")

WORD_RE = re.compile(r"[^\W_]+", re.UNICODE)
CYRILLIC_RE = re.compile(r"[Ѐ-ӿ]")

# Shortest word for which a shared prefix is meaningful. "antarctic"/"antarctica" is a
# morphological variant of one name; "car"/"cargo" is not, and four letters is not
# enough to tell those apart. Used only by the slot layer - see ``stem_match``.
MIN_STEM_LENGTH = 5


def provider_evidence_text(candidate: dict[str, Any]) -> str:
    """Everything the *provider* said about this asset - and nothing we said to it.

    Tags are excluded when the provider admits it synthesised them from the query
    (``tags_source="query_derived"``), which is what the Pexels adapter does for videos
    because the API returns no description.
    """
    queries = {str(candidate.get(key) or "").strip().lower() for key in QUERY_FIELDS}
    queries.discard("")
    pieces: list[str] = []
    for key in METADATA_FIELDS:
        pieces.extend(evidence_values(candidate.get(key, ""), queries))
    if str(candidate.get("tags_source") or "provider") != "query_derived":
        for key in ("tags", "keywords"):
            pieces.extend(evidence_values(candidate.get(key, ""), queries))
    return re.sub(r"\s+", " ", " ".join(piece for piece in pieces if piece).lower()).strip()


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


@dataclass(frozen=True)
class CandidateEvidence:
    """One candidate's provider metadata, read once and asked many questions."""

    text: str = ""
    token_set: frozenset[str] = field(default_factory=frozenset)
    vision_tags: tuple[str, ...] = ()
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

    def contains(self, concept: str) -> bool:
        return contains_concept(concept, set(self.token_set), self.text)


def build_evidence(candidate: dict[str, Any]) -> CandidateEvidence:
    text = provider_evidence_text(candidate)
    vision_tags = tuple(str(tag).lower() for tag in candidate.get("vision_tags", []) or [])
    status, score = metadata_status(candidate, text, list(vision_tags))
    return CandidateEvidence(
        text=text,
        token_set=frozenset(tokens(text)) | frozenset(vision_tags),
        vision_tags=vision_tags,
        metadata_status=status,
        metadata_score=score,
    )


__all__ = [
    "CYRILLIC_RE",
    "METADATA_AVAILABLE",
    "METADATA_FIELDS",
    "METADATA_QUERY_DERIVED",
    "METADATA_UNAVAILABLE",
    "MIN_STEM_LENGTH",
    "QUERY_FIELDS",
    "WORD_RE",
    "CandidateEvidence",
    "build_evidence",
    "concept_score",
    "contains_concept",
    "evidence_values",
    "metadata_status",
    "provider_evidence_text",
    "script_mismatch",
    "stem_concept_score",
    "stem_match",
    "tokens",
]
