"""The author's explicit "what to show" for one scene, and how it overrides extraction.

Automatic extraction from Russian narration produced ``одном`` as a subject, ``Результат``
as an action and ``которую`` as a secondary subject, and never recovered a place at all -
``Антарктида`` and ``Мак-Мердо`` were in the text of every relevant scene and ``location``
came back empty for seven scenes out of eight. No ranking can recover from that, because
the words being searched for are not the words that name the shot.

A brief lets the author state the shot directly. It is optional and additive: a scene
without one behaves exactly as before. When present, each field *replaces* the extracted
value for that field only - a brief that names a subject but no action leaves the action
to extraction rather than blanking it.

Nothing here is ever spoken. The brief lives beside the narration, never inside it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .expansion import (
    MAX_PROVIDER_QUERIES,
    PROVIDER_LANGUAGE,
    expand_queries,
    planning_input_from_scene,
    provider_language_query,
    provider_language_text,
)
from .models import MEDIA_KINDS, SHOT_TYPES

# Field names are the plan's own (``place``, not "location"; ``must_avoid``, not
# "negative_keywords"), so a brief reads like the model it overrides. "location" is
# accepted as an alias because it is the word most people reach for.
_PLACE_KEYS = ("place", "location")

# The active remote providers all search English indexes. This producer does not
# translate into English: it only packages English evidence that is already present
# in the script, a planner's structured semantics, or a claim linked to the scene.
# The language, the term rules and the expansion ladder all live in ``expansion``,
# so there is exactly one owner for what a provider-ready query may contain.


@dataclass
class VisualBrief:
    """One scene's explicit visual instruction. Every field optional."""

    visual_description: str = ""
    subject: str = ""
    action: str = ""
    place: str = ""
    # Names that must survive verbatim into the provider query: "McMurdo Dry Valleys",
    # "Antarctica". These are the reason a brief exists - an extracted stem cannot
    # carry a proper noun.
    exact_entities: list[str] = field(default_factory=list)
    must_include: list[str] = field(default_factory=list)
    must_avoid: list[str] = field(default_factory=list)
    # What is going on around the subject: "wind", "atmospheric transport", "sample
    # analysis". A scene set in Antarctica that is *about* a research station and
    # airborne transport is not answered by any picture of Antarctica, and this is
    # where the author says so. Never inferred: an unstated context constrains nothing.
    context: list[str] = field(default_factory=list)
    # Material that would be explicitly *something else*: "mars mission", "spacecraft".
    # Weaker than ``must_avoid``, which forbids the thing outright - this only says the
    # match may not be called complete without a person looking at it.
    conflicting_context: list[str] = field(default_factory=list)
    shot_type: str = ""
    media_types: list[str] = field(default_factory=list)
    # One of src.assets.scene_strategy.SOURCE_CLASSES. Decides which providers are asked.
    source_class: str = ""
    # Provider-ready queries: {"en": [...]} or {"pexels": [...]}. Bypasses query building.
    provider_queries: dict[str, list[str]] = field(default_factory=dict)
    # What to do when nothing is found: "unresolved" | "generated_infographic".
    fallback_visual: str = ""
    # Values for a figure the project draws itself (headline, sample counts, layers).
    # Passed through untouched to src.assets.generated_infographic - this layer never
    # reads, rounds or reinterprets them, because a number the pipeline adjusted on its
    # own would be a claim the script never made.
    infographic: dict[str, Any] = field(default_factory=dict)
    notes: str = ""

    @property
    def is_empty(self) -> bool:
        return not any(
            [
                self.visual_description, self.subject, self.action, self.place,
                self.exact_entities, self.must_include, self.must_avoid, self.shot_type,
                self.context, self.conflicting_context,
                self.media_types, self.source_class, self.provider_queries,
                self.fallback_visual, self.infographic, self.notes,
            ]
        )

    def to_dict(self) -> dict[str, Any]:
        data = {
            "visual_description": self.visual_description,
            "subject": self.subject,
            "action": self.action,
            "place": self.place,
            "exact_entities": list(self.exact_entities),
            "must_include": list(self.must_include),
            "must_avoid": list(self.must_avoid),
            "context": list(self.context),
            "conflicting_context": list(self.conflicting_context),
            "shot_type": self.shot_type,
            "media_types": list(self.media_types),
            "source_class": self.source_class,
            "provider_queries": {key: list(value) for key, value in self.provider_queries.items()},
            "fallback_visual": self.fallback_visual,
            "infographic": dict(self.infographic),
            "notes": self.notes,
        }
        return {key: value for key, value in data.items() if value}


# The fields by which an author states *what the frame shows*, as opposed to bounding or
# labelling an answer someone else supplies. ``visual_description`` replaces the scene's
# meaning outright, ``subject`` is what must be in frame, and ``provider_queries`` skips
# query building entirely - past any of those, nothing automatic can still change what the
# scene is about.
AUTHOR_SEMANTIC_FIELDS: tuple[str, ...] = ("visual_description", "subject", "provider_queries")


def author_semantics_are_sufficient(brief: VisualBrief | None) -> bool:
    """Whether this brief already answers "what should this scene show".

    Not the same question as "is this brief non-empty", and the difference is the whole
    point. ``must_include`` is a hard requirement a candidate is *refused* for missing and
    ``must_avoid`` forbids material outright: both bound an answer without being one, and
    an author who wrote ``must_include: ["orca"]`` has said the shot must contain an orca,
    not what the orca is doing or where. ``notes``, ``media_types``, ``source_class``,
    ``shot_type`` and ``exact_entities`` are metadata, delivery constraints and names -
    ``fallback_visual`` and ``infographic`` say what to do when nothing is found. None of
    them states the scene's meaning, and treating their presence as a full answer left the
    scene with whatever extraction guessed, which is the failure this layer exists to fix.

    ``action`` and ``place`` are deliberately not sufficient either, for the reason
    ``semantic_brief.parse_response`` already refuses them from a model: a place without a
    subject - "somewhere outdoors" - is how a scene turns into generic footage. An author
    who stated only one of those still wins on that field, because they are applied last.
    """
    if brief is None:
        return False
    return any(bool(getattr(brief, name, None)) for name in AUTHOR_SEMANTIC_FIELDS)


def parse_brief(data: dict[str, Any] | None) -> VisualBrief:
    """Read a brief off a script scene. Unknown keys are ignored, never guessed at."""
    if not isinstance(data, dict):
        return VisualBrief()
    place = ""
    for key in _PLACE_KEYS:
        if str(data.get(key) or "").strip():
            place = str(data[key]).strip()
            break
    shot_type = str(data.get("shot_type") or "").strip().lower()
    media_types = [str(item).strip().lower() for item in _as_list(data.get("media_types") or data.get("allowed_media_kinds"))]
    return VisualBrief(
        visual_description=str(data.get("visual_description") or "").strip(),
        subject=str(data.get("subject") or "").strip(),
        action=str(data.get("action") or "").strip(),
        place=place,
        exact_entities=_as_list(data.get("exact_entities")),
        must_include=_as_list(data.get("must_include")),
        must_avoid=_as_list(data.get("must_avoid")),
        context=_as_list(data.get("context")),
        conflicting_context=_as_list(data.get("conflicting_context")),
        shot_type=shot_type if shot_type in SHOT_TYPES else "",
        media_types=[item for item in media_types if item in MEDIA_KINDS],
        source_class=str(data.get("source_class") or "").strip(),
        provider_queries=_as_query_map(data.get("provider_queries")),
        fallback_visual=str(data.get("fallback_visual") or "").strip(),
        infographic=dict(data.get("infographic") or {}),
        notes=str(data.get("notes") or "").strip(),
    )


def apply_brief(scene: Any, brief: VisualBrief) -> Any:
    """Overlay a brief onto a planned scene, field by field.

    Returns the same ``SceneVisualPlan`` instance, mutated. Only fields the brief
    actually states are replaced; the rest keep whatever the planner derived.
    """
    if brief.is_empty:
        return scene
    if brief.visual_description:
        scene.meaning = brief.visual_description
    if brief.subject:
        scene.subject = brief.subject
    if brief.action:
        scene.action = brief.action
    if brief.place:
        scene.place = brief.place
    if brief.shot_type:
        scene.shot_type = brief.shot_type
    if brief.media_types:
        scene.allowed_media_kinds = list(brief.media_types)
        scene.preferred_media_kind = brief.media_types[0]
    # The exact names are what a provider must be given verbatim, so they lead
    # must_include: a query that loses "McMurdo" is not a query for this scene.
    #
    # An author who described the shot has spoken about what it must contain, and their
    # answer replaces the extracted one *including when it is empty*. Keeping a stem the
    # planner guessed at, next to a subject the author rewrote, leaves a hard requirement
    # nobody stated and which no longer matches the scene it guards.
    required = _unique(list(brief.exact_entities) + list(brief.must_include))
    if required or brief.subject or brief.place:
        scene.must_include = required
    if brief.must_avoid:
        scene.must_avoid = list(brief.must_avoid)
    if brief.exact_entities:
        scene.secondary_subjects = _unique(
            [item for item in brief.exact_entities if item != scene.subject] + list(scene.secondary_subjects)
        )
    if brief.notes:
        scene.notes = brief.notes
    return scene


def produce_brief(
    scene: Any,
    *,
    script_scene: Any = None,
    claims: list[dict[str, Any]] | None = None,
) -> VisualBrief:
    """Package existing provider-language evidence into the existing brief.

    This is intentionally not a translator or another visual planner. The scene has
    already been planned; this function only exposes short English search candidates
    that the evidence already contains. Topic/title/channel literals are not inputs,
    narration is never copied wholesale, and insufficient evidence returns an empty
    brief so the existing query adapter remains fail-closed.

    What the evidence states verbatim leads; ``expansion`` then widens it into the
    ladder, so a scene offers a provider several genuinely different ways to fail
    instead of one exact string and nothing else.
    """
    queries = expand_queries(
        planning_input_from_scene(scene),
        seeds=_provider_queries(scene, script_scene=script_scene, claims=claims or []),
        limit=MAX_PROVIDER_QUERIES,
    )
    if not queries:
        return VisualBrief()

    must_include = [str(item) for item in (getattr(scene, "must_include", None) or [])]
    must_avoid = [str(item) for item in (getattr(scene, "must_avoid", None) or [])]
    allowed_media = [
        str(item)
        for item in (getattr(scene, "allowed_media_kinds", None) or [])
        if str(item) in MEDIA_KINDS
    ]
    shot_type = str(getattr(scene, "shot_type", "") or "")
    return VisualBrief(
        subject=provider_language_text(getattr(scene, "subject", "")),
        action=provider_language_text(getattr(scene, "action", "")),
        place=provider_language_text(getattr(scene, "place", "")),
        exact_entities=[item for item in must_include if provider_language_text(item)],
        must_include=must_include,
        must_avoid=must_avoid,
        shot_type=shot_type if shot_type in SHOT_TYPES else "",
        media_types=allowed_media,
        provider_queries={PROVIDER_LANGUAGE: queries},
    )


def _provider_queries(
    scene: Any,
    *,
    script_scene: Any,
    claims: list[dict[str, Any]],
) -> list[str]:
    """What the evidence already says verbatim, before any widening."""
    candidates: list[str] = []

    # Structured scene semantics are the strongest automatic evidence: the planner
    # has already separated subject/action/environment from narration.
    for intent in getattr(scene, "intents", None) or []:
        query = provider_language_query(list(getattr(intent, "terms", None) or []))
        if query:
            candidates.append(query)

    # Prepared script keywords are the modern carrier for the legacy practice of
    # keeping provider-ready visual keywords separate from narration.
    keywords = _value(script_scene, "keywords")
    if isinstance(keywords, (list, tuple)):
        query = provider_language_query([str(item) for item in keywords])
        if query:
            candidates.append(query)

    # Research is scene-local only when the script names the claim it came from.
    for text in scene_claim_texts(scene, claims):
        query = provider_language_query([text])
        if query:
            candidates.append(query)

    return _unique_queries(candidates)


def scene_claim_texts(scene: Any, claims: list[dict[str, Any]]) -> list[str]:
    """Research this scene is actually allowed to be illustrated from, in claim order.

    Scene-local by construction: a claim belongs to a scene because the script named its
    id, never because it is in the same project. Anything marked unsafe for the script
    is dropped here, so no consumer has to remember that it must be.
    """
    claim_ids = {
        str(item)
        for item in (getattr(scene, "claim_ids", None) or [])
        if str(item)
    }
    if not claim_ids:
        return []
    texts: list[str] = []
    for claim in claims:
        if not isinstance(claim, dict):
            continue
        if str(claim.get("claim_id") or "") not in claim_ids:
            continue
        if claim.get("safe_for_script") is False:
            continue
        text = " ".join(str(claim.get("source_excerpt") or claim.get("text") or "").split())
        if text:
            texts.append(text)
    return texts


def _unique_queries(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        key = " ".join(value.casefold().split())
        if key and key not in seen:
            seen.add(key)
            result.append(value)
    return result


def _value(source: Any, key: str) -> Any:
    return source.get(key) if isinstance(source, dict) else getattr(source, key, None)


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _as_query_map(value: Any) -> dict[str, list[str]]:
    if isinstance(value, dict):
        return {str(key): _as_list(item) for key, item in value.items() if _as_list(item)}
    values = _as_list(value)
    return {"en": values} if values else {}


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        key = str(value).strip().casefold()
        if key and key not in seen:
            seen.add(key)
            ordered.append(str(value).strip())
    return ordered


__all__ = [
    "AUTHOR_SEMANTIC_FIELDS",
    "VisualBrief",
    "apply_brief",
    "author_semantics_are_sufficient",
    "parse_brief",
    "produce_brief",
    "scene_claim_texts",
]
