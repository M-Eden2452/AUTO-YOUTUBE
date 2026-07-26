"""Contracts for the visual planning layer: what to show in each scene.

Value objects only - nothing here knows about files, providers or the network. The
bridge to the ``visual_plan.json`` the news_to_short pipeline already stores lives
in ``legacy_format``; the bridge to provider query strings lives in
``query_adapter``.

Severity vocabulary is imported from the script engine rather than redefined: a
project with two meanings of "warning" is a project that reports neither.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from src.content.script_engine.models import SEVERITY_ERROR, SEVERITY_WARNING

# Version of the *engine* view of a visual plan. The stored visual_plan.json keeps
# its own (previously implicit) shape; see legacy_format.
VISUAL_PLAN_SCHEMA_VERSION = 2

# --- Media kinds -------------------------------------------------------------
# The vocabulary the pipeline can actually route today (src.assets.provider_routing
# maps everything onto an image or a video search) plus the two kinds a documentary
# format will need. Nothing outside this set is valid: an unknown kind would reach
# provider routing as a silent "video".
MEDIA_VIDEO = "video"
MEDIA_IMAGE = "image"
MEDIA_ANIMATED_IMAGE = "animated_image"
MEDIA_DIAGRAM = "diagram"
MEDIA_MAP = "map"
MEDIA_ARCHIVE_FOOTAGE = "archive_footage"

MEDIA_KINDS = (
    MEDIA_VIDEO,
    MEDIA_IMAGE,
    MEDIA_ANIMATED_IMAGE,
    MEDIA_DIAGRAM,
    MEDIA_MAP,
    MEDIA_ARCHIVE_FOOTAGE,
)

# How each kind reaches the existing search layer, which only knows image vs video.
MEDIA_KIND_SEARCH_TYPE = {
    MEDIA_VIDEO: "video",
    MEDIA_IMAGE: "image",
    MEDIA_ANIMATED_IMAGE: "image",
    MEDIA_DIAGRAM: "image",
    MEDIA_MAP: "image",
    MEDIA_ARCHIVE_FOOTAGE: "video",
}

# --- Shot types --------------------------------------------------------------
# What the frame has to do dramatically. Distinct from the script's scene role: a
# development scene can need a detail shot or an evidence shot.
SHOT_ESTABLISHING = "establishing"
SHOT_ACTION = "action"
SHOT_DETAIL = "detail"
SHOT_EVIDENCE = "evidence"
SHOT_PAYOFF = "payoff"
SHOT_CONTEXT = "context"

SHOT_TYPES = (SHOT_ESTABLISHING, SHOT_ACTION, SHOT_DETAIL, SHOT_EVIDENCE, SHOT_PAYOFF, SHOT_CONTEXT)

# --- Intent kinds ------------------------------------------------------------
# Why this particular query exists. The order a scene's intents are tried in is the
# order they appear in; the kind explains what was given up to widen the search.
INTENT_PRIMARY = "primary"
INTENT_ALTERNATIVE = "alternative"
INTENT_CONTEXT_FALLBACK = "context_fallback"
INTENT_ATMOSPHERIC_FALLBACK = "atmospheric_fallback"

INTENT_KINDS = (INTENT_PRIMARY, INTENT_ALTERNATIVE, INTENT_CONTEXT_FALLBACK, INTENT_ATMOSPHERIC_FALLBACK)


@dataclass
class VisualEntity:
    """One thing named by the source text, with a record of where it was found.

    ``surface`` is the wording as it appears in the script - never a synonym, never
    a translation, never a generalisation. ``stem`` is a crude common-prefix form
    used only to recognise the same entity across grammatical cases; it is not
    linguistics and is never shown to a provider.
    """

    surface: str
    stem: str = ""
    kind: str = "entity"
    salience: float = 0.0
    scene_ids: list[str] = field(default_factory=list)
    source_refs: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "surface": self.surface,
            "stem": self.stem,
            "kind": self.kind,
            "salience": round(self.salience, 3),
            "scene_ids": list(self.scene_ids),
            "source_refs": list(self.source_refs),
        }


@dataclass
class VisualSearchIntent:
    """One search idea, structured, with the language it is written in.

    Kept deliberately separate from the string a provider receives. The project has
    no translation layer (verified: nothing in ``src/`` translates), and inventing
    one here would silently swap the script's animal, country or technology for a
    near-miss. So the terms stay in the source language, say so, and
    ``requires_translation`` marks the ones a future provider-specific adapter has
    to handle before a stock search can be expected to work.
    """

    kind: str = INTENT_PRIMARY
    subject: str = ""
    modifiers: list[str] = field(default_factory=list)
    context: list[str] = field(default_factory=list)
    language: str = "ru"
    # 1 = exactly what the scene is about, higher = progressively more general.
    fallback_level: int = 1
    requires_translation: bool = False
    notes: str = ""

    @property
    def terms(self) -> list[str]:
        """Every term of this intent, most specific first, de-duplicated."""
        seen: set[str] = set()
        ordered: list[str] = []
        for term in [self.subject, *self.modifiers, *self.context]:
            cleaned = (term or "").strip()
            key = cleaned.casefold()
            if cleaned and key not in seen:
                seen.add(key)
                ordered.append(cleaned)
        return ordered

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "subject": self.subject,
            "modifiers": list(self.modifiers),
            "context": list(self.context),
            "language": self.language,
            "fallback_level": self.fallback_level,
            "requires_translation": self.requires_translation,
            "terms": self.terms,
            "notes": self.notes,
        }


@dataclass
class SceneVisualPlan:
    """What to show in one scene. Bound to the script by ``scene_id``.

    This says nothing about which file will be used, whether it is licensed, or
    whether it exists: choosing and clearing an asset is a later stage and stays
    there.
    """

    scene_id: str
    index: int = 0
    meaning: str = ""
    subject: str = ""
    secondary_subjects: list[str] = field(default_factory=list)
    action: str = ""
    place: str = ""
    period: str = ""
    shot_type: str = SHOT_CONTEXT
    allowed_media_kinds: list[str] = field(default_factory=list)
    preferred_media_kind: str = MEDIA_VIDEO
    must_include: list[str] = field(default_factory=list)
    must_avoid: list[str] = field(default_factory=list)
    intents: list[VisualSearchIntent] = field(default_factory=list)
    # Back-references into the material, so a frame can be traced to what it
    # illustrates. Not a rights claim - see EvidenceBundle for that.
    claim_ids: list[str] = field(default_factory=list)
    source_refs: list[str] = field(default_factory=list)
    entities: list[VisualEntity] = field(default_factory=list)
    duration_sec: float = 0.0
    notes: str = ""
    warnings: list[str] = field(default_factory=list)
    # The author's explicit instruction, when they gave one. Set by the engine after
    # the planner has run; ``None`` means the scene was planned by extraction alone.
    brief: Any | None = None

    @property
    def primary_intent(self) -> VisualSearchIntent | None:
        return self.intents[0] if self.intents else None

    @property
    def fallback_intents(self) -> list[VisualSearchIntent]:
        return self.intents[1:]

    def to_dict(self) -> dict[str, Any]:
        return {
            "scene_id": self.scene_id,
            "index": self.index,
            "meaning": self.meaning,
            "subject": self.subject,
            "secondary_subjects": list(self.secondary_subjects),
            "action": self.action,
            "place": self.place,
            "period": self.period,
            "shot_type": self.shot_type,
            "allowed_media_kinds": list(self.allowed_media_kinds),
            "preferred_media_kind": self.preferred_media_kind,
            "must_include": list(self.must_include),
            "must_avoid": list(self.must_avoid),
            "intents": [intent.to_dict() for intent in self.intents],
            "claim_ids": list(self.claim_ids),
            "source_refs": list(self.source_refs),
            "entities": [entity.to_dict() for entity in self.entities],
            "duration_sec": round(self.duration_sec, 3),
            "notes": self.notes,
            "warnings": list(self.warnings),
        }


@dataclass
class VisualPlanRequest:
    """Everything a planner needs. The script is the material, not a suggestion."""

    script: Any = None  # ScriptResult; typed loosely to keep this module import-light
    language: str = "ru"
    topic: str = ""
    title: str = ""
    # Research claims exactly as src.news.research_engine writes them, when the
    # caller has them. The planner works without them.
    claims: list[dict[str, Any]] = field(default_factory=list)
    format_id: str = "vertical_short"
    template_id: str = ""
    channel_id: str = ""
    aspect_ratio: str = "9:16"
    user_asset_count: int = 0
    planner_id: str = ""
    planner_options: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "language": self.language,
            "topic": self.topic,
            "title": self.title,
            "claim_count": len(self.claims),
            "format_id": self.format_id,
            "template_id": self.template_id,
            "channel_id": self.channel_id,
            "aspect_ratio": self.aspect_ratio,
            "user_asset_count": self.user_asset_count,
            "planner_id": self.planner_id,
            "planner_options": dict(self.planner_options),
        }


@dataclass
class VisualPlanResult:
    """A finished plan: one entry per script scene, in script order."""

    scenes: list[SceneVisualPlan] = field(default_factory=list)
    language: str = "ru"
    topic_entity: str = ""
    planner_id: str = ""
    planner_version: str = ""
    format_id: str = "vertical_short"
    aspect_ratio: str = "9:16"
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: int = VISUAL_PLAN_SCHEMA_VERSION

    @property
    def scene_ids(self) -> list[str]:
        return [scene.scene_id for scene in self.scenes]

    def scene(self, scene_id: str) -> SceneVisualPlan | None:
        return next((scene for scene in self.scenes if scene.scene_id == scene_id), None)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "language": self.language,
            "topic_entity": self.topic_entity,
            "planner_id": self.planner_id,
            "planner_version": self.planner_version,
            "format_id": self.format_id,
            "aspect_ratio": self.aspect_ratio,
            "scene_count": len(self.scenes),
            "scenes": [scene.to_dict() for scene in self.scenes],
            "warnings": list(self.warnings),
            "metadata": dict(self.metadata),
        }


@dataclass
class VisualPlanValidationIssue:
    code: str
    message: str
    severity: str = SEVERITY_ERROR
    scene_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "severity": self.severity,
            "scene_id": self.scene_id,
        }


@dataclass
class VisualPlanValidationResult:
    issues: list[VisualPlanValidationIssue] = field(default_factory=list)

    @property
    def errors(self) -> list[VisualPlanValidationIssue]:
        return [issue for issue in self.issues if issue.severity == SEVERITY_ERROR]

    @property
    def warnings(self) -> list[VisualPlanValidationIssue]:
        return [issue for issue in self.issues if issue.severity == SEVERITY_WARNING]

    @property
    def valid(self) -> bool:
        """No errors. Choosing what to show is creative; only broken plans fail."""
        return not self.errors

    @property
    def status(self) -> str:
        if self.errors:
            return "failed"
        return "needs_review" if self.warnings else "passed"

    def codes(self) -> list[str]:
        return [issue.code for issue in self.issues]

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "valid": self.valid,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "issues": [issue.to_dict() for issue in self.issues],
        }


__all__ = [
    "INTENT_ALTERNATIVE",
    "INTENT_ATMOSPHERIC_FALLBACK",
    "INTENT_CONTEXT_FALLBACK",
    "INTENT_KINDS",
    "INTENT_PRIMARY",
    "MEDIA_ANIMATED_IMAGE",
    "MEDIA_ARCHIVE_FOOTAGE",
    "MEDIA_DIAGRAM",
    "MEDIA_IMAGE",
    "MEDIA_KINDS",
    "MEDIA_KIND_SEARCH_TYPE",
    "MEDIA_MAP",
    "MEDIA_VIDEO",
    "SHOT_ACTION",
    "SHOT_CONTEXT",
    "SHOT_DETAIL",
    "SHOT_ESTABLISHING",
    "SHOT_EVIDENCE",
    "SHOT_PAYOFF",
    "SHOT_TYPES",
    "VISUAL_PLAN_SCHEMA_VERSION",
    "SceneVisualPlan",
    "VisualEntity",
    "VisualPlanRequest",
    "VisualPlanResult",
    "VisualPlanValidationIssue",
    "VisualPlanValidationResult",
    "VisualSearchIntent",
]


def rebuild_intents(scene: "SceneVisualPlan", *, language: str = "ru") -> list[VisualSearchIntent]:
    """Intents for a scene whose fields were just replaced by an explicit brief.

    The planner built its intents from extracted words; once a brief has overridden
    the subject, action and place, those intents describe a scene that no longer
    exists. Rebuilding them here keeps one intent shape for both paths instead of
    giving briefed scenes a parallel query format.

    ``requires_translation`` is decided per intent by the script the terms are written
    in, not by the script's narration language: an English brief on a Russian video
    produces English intents that need no adapter.
    """
    subject = scene.subject
    secondary = list(scene.secondary_subjects)
    place = scene.place
    intents: list[VisualSearchIntent] = []
    seen: set[tuple[str, ...]] = set()

    def add(kind: str, subj: str, modifiers: list[str], context: list[str], level: int, notes: str) -> None:
        if not subj:
            return
        intent = VisualSearchIntent(
            kind=kind,
            subject=subj,
            modifiers=[item for item in modifiers if item],
            context=[item for item in context if item],
            language=_terms_language(subj, modifiers, context, default=language),
            fallback_level=level,
            notes=notes,
        )
        intent.requires_translation = _needs_translation(intent.terms)
        key = tuple(term.casefold() for term in intent.terms)
        if key and key not in seen:
            seen.add(key)
            intents.append(intent)

    add(INTENT_PRIMARY, subject, [scene.action, scene.period], [place, *secondary[:1]], 1, "явный бриф сцены")
    add(INTENT_ALTERNATIVE, subject, [], [place], 2, "предмет брифа без действия")
    context_terms = [term for term in (place, *secondary) if term]
    if context_terms:
        add(INTENT_CONTEXT_FALLBACK, context_terms[0], [], context_terms[1:], 3, "место сцены без её предмета")
    return intents


def _terms_language(subject: str, modifiers: list[str], context: list[str], *, default: str) -> str:
    terms = [subject, *modifiers, *context]
    return default if _needs_translation(terms) else "en"


def _needs_translation(terms: list[str]) -> bool:
    """True when any term is written in a script an English index cannot match."""
    return any(_CYRILLIC_RE.search(str(term or "")) for term in terms)


_CYRILLIC_RE = re.compile(r"[Ѐ-ӿ]")
