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

import re
from dataclasses import dataclass, field
from typing import Any

from src.content.script_engine.text_analysis import STOPWORDS

from .models import MEDIA_KINDS, SHOT_TYPES

# Field names are the plan's own (``place``, not "location"; ``must_avoid``, not
# "negative_keywords"), so a brief reads like the model it overrides. "location" is
# accepted as an alias because it is the word most people reach for.
_PLACE_KEYS = ("place", "location")

# The active remote providers all search English indexes. This producer does not
# translate into English: it only packages English evidence that is already present
# in the script, a planner's structured semantics, or a claim linked to the scene.
_PROVIDER_LANGUAGE = "en"
_MAX_PROVIDER_QUERIES = 3
_MAX_PROVIDER_QUERY_TERMS = 8
_PROVIDER_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9.'-]*")
_CYRILLIC_RE = re.compile(r"[Ѐ-ӿ]")

# A query made only of production vocabulary is a plausible-looking substitute, not
# evidence of what is in frame. Topic/domain nouns are deliberately absent here.
_NON_FACTUAL_QUERY_TERMS = {
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
    """
    queries = _provider_queries(scene, script_scene=script_scene, claims=claims or [])
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
        subject=_provider_field(getattr(scene, "subject", "")),
        action=_provider_field(getattr(scene, "action", "")),
        place=_provider_field(getattr(scene, "place", "")),
        exact_entities=[item for item in must_include if _provider_field(item)],
        must_include=must_include,
        must_avoid=must_avoid,
        shot_type=shot_type if shot_type in SHOT_TYPES else "",
        media_types=allowed_media,
        provider_queries={_PROVIDER_LANGUAGE: queries},
    )


def _provider_queries(
    scene: Any,
    *,
    script_scene: Any,
    claims: list[dict[str, Any]],
) -> list[str]:
    candidates: list[str] = []

    # Structured scene semantics are the strongest automatic evidence: the planner
    # has already separated subject/action/environment from narration.
    for intent in getattr(scene, "intents", None) or []:
        query = _query_from_values(list(getattr(intent, "terms", None) or []))
        if query:
            candidates.append(query)

    # Prepared script keywords are the modern carrier for the legacy practice of
    # keeping provider-ready visual keywords separate from narration.
    keywords = _value(script_scene, "keywords")
    if isinstance(keywords, (list, tuple)):
        query = _query_from_values([str(item) for item in keywords])
        if query:
            candidates.append(query)

    # Research is scene-local only when the script names the claim it came from.
    claim_ids = {
        str(item)
        for item in (getattr(scene, "claim_ids", None) or [])
        if str(item)
    }
    if claim_ids:
        for claim in claims:
            if not isinstance(claim, dict):
                continue
            if str(claim.get("claim_id") or "") not in claim_ids:
                continue
            if claim.get("safe_for_script") is False:
                continue
            query = _query_from_values(
                [str(claim.get("source_excerpt") or claim.get("text") or "")]
            )
            if query:
                candidates.append(query)

    return _unique_queries(candidates)[:_MAX_PROVIDER_QUERIES]


def _query_from_values(values: list[str]) -> str:
    terms: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = " ".join(str(value or "").split())
        if not text or _CYRILLIC_RE.search(text) or _looks_like_locator(text):
            continue
        for token in _PROVIDER_TOKEN_RE.findall(text):
            key = token.casefold()
            if key in STOPWORDS or key in _NON_FACTUAL_QUERY_TERMS or key in seen:
                continue
            seen.add(key)
            terms.append(token)
            if len(terms) >= _MAX_PROVIDER_QUERY_TERMS:
                break
        if len(terms) >= _MAX_PROVIDER_QUERY_TERMS:
            break
    # One word is usually a category or name with too little scene intent to search
    # truthfully. Keeping the threshold at two also rejects generic slugs and labels.
    return " ".join(terms) if len(terms) >= 2 else ""


def _provider_field(value: Any) -> str:
    text = " ".join(str(value or "").split())
    if not text or _CYRILLIC_RE.search(text) or _looks_like_locator(text):
        return ""
    return text if _PROVIDER_TOKEN_RE.search(text) else ""


def _looks_like_locator(value: str) -> bool:
    lowered = value.casefold()
    return any(marker in lowered for marker in ("://", "\\", "/", "_"))


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


__all__ = ["VisualBrief", "apply_brief", "parse_brief"]
