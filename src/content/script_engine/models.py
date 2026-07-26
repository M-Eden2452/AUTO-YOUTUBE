"""Contracts for the script engine: request, scene, result, validation.

These are storage-independent value objects. The bridge to the on-disk
``script.json`` used by the news_to_short pipeline lives in
``src.content.script_engine.legacy_format`` - nothing here knows about files.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Version of the *engine* view of a script. The on-disk script.json keeps its own
# (previously implicit) shape; see legacy_format for how the two map onto each other.
SCRIPT_SCHEMA_VERSION = 2

# --- Scene roles -------------------------------------------------------------
# The Shorts dramaturgy the engine has to be able to express. A CTA is a legal
# role, but it is never added unless the caller asks for it (ScriptRequest.include_cta).
SCENE_ROLE_HOOK = "hook"
SCENE_ROLE_DEVELOPMENT = "development"
SCENE_ROLE_PAYOFF = "payoff"
SCENE_ROLE_CTA = "cta"

SCENE_ROLES = (SCENE_ROLE_HOOK, SCENE_ROLE_DEVELOPMENT, SCENE_ROLE_PAYOFF, SCENE_ROLE_CTA)

# --- Input kinds -------------------------------------------------------------
# What the caller actually has. Providers declare which of these they support,
# so a "ready narration" input can never be silently re-written as if it were
# raw article text (which is exactly what the pipeline used to do).
SOURCE_TOPIC = "topic"
SOURCE_RESEARCH = "research"
SOURCE_USER_SCRIPT = "user_script"
SOURCE_NARRATION_TEXT = "narration_text"

SOURCE_KINDS = (SOURCE_TOPIC, SOURCE_RESEARCH, SOURCE_USER_SCRIPT, SOURCE_NARRATION_TEXT)

# --- Validation severities ---------------------------------------------------
SEVERITY_ERROR = "error"
SEVERITY_WARNING = "warning"


@dataclass
class ScriptConstraints:
    """Limits a script must respect. Not a scene count - explicitly a duration budget.

    The engine is never allowed to hard-code "six scenes": how many scenes there
    are follows from how many complete thoughts fit into ``target_duration_sec``.
    """

    target_duration_sec: float = 55.0
    min_scene_duration_sec: float = 2.0
    max_scene_duration_sec: float = 16.0
    min_scene_count: int = 3
    max_scene_count: int = 24
    # Measured on the confirmed live fullscreen_voiceover_v1 render: six scenes of
    # real ElevenLabs narration came out at 14.6-15.2 characters per second, a far
    # more stable figure than words per second (1.77-2.21). Used only to *estimate*
    # a planned duration; the real timing is written later by src.audio.scene_timeline.
    speech_chars_per_sec: float = 14.9
    # Pause the assembler inserts between scenes (src.audio.pause_policy,
    # vertical_short). Counted against the budget so the spoken result lands on target.
    pause_between_scenes_sec: float = 0.35

    def clamp_duration(self, value: float) -> float:
        return max(self.min_scene_duration_sec, min(self.max_scene_duration_sec, value))

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_duration_sec": self.target_duration_sec,
            "min_scene_duration_sec": self.min_scene_duration_sec,
            "max_scene_duration_sec": self.max_scene_duration_sec,
            "min_scene_count": self.min_scene_count,
            "max_scene_count": self.max_scene_count,
            "speech_chars_per_sec": self.speech_chars_per_sec,
            "pause_between_scenes_sec": self.pause_between_scenes_sec,
        }


@dataclass
class ScriptRequest:
    """Everything a provider needs to write one script.

    ``source_kind`` is authoritative: it says what ``raw_text``/``claims`` mean.
    A provider that cannot honour a source kind must say so via ``supports()``
    rather than reinterpreting the input.
    """

    source_kind: str = SOURCE_TOPIC
    language: str = "ru"
    title: str = ""
    topic: str = ""
    # Article text (research), the user's finished script (user_script), or the
    # finished narration (narration_text). Empty for a bare topic request.
    raw_text: str = ""
    summary: str = ""
    # Research claims exactly as src.news.research_engine writes them.
    claims: list[dict[str, Any]] = field(default_factory=list)
    source_urls: list[str] = field(default_factory=list)
    constraints: ScriptConstraints = field(default_factory=ScriptConstraints)
    format_id: str = "vertical_short"
    template_id: str = ""
    channel_id: str = ""
    # A CTA is opt-in. Requirement: never append one automatically.
    include_cta: bool = False
    cta_text: str = ""
    provider_id: str = ""
    provider_options: dict[str, Any] = field(default_factory=dict)
    # Explicit "what to show" per scene, keyed by 1-based scene number as a string
    # ("1", "2", ...) or by scene_id ("scene_001"). Additive and optional: a caller
    # that supplies none gets exactly the previous behaviour. Only a provider that
    # preserves the author's scene boundaries can honour these, which today means
    # ``user_supplied``; see src.content.visual_planning.brief for the fields.
    visual_briefs: dict[str, dict[str, Any]] = field(default_factory=dict)

    def brief_for(self, index: int, scene_id: str = "") -> dict[str, Any]:
        """The brief for one scene, looked up by number or by id. Empty when absent."""
        for key in (str(index), scene_id, f"scene_{index:03d}"):
            if key and isinstance(self.visual_briefs.get(key), dict):
                return dict(self.visual_briefs[key])
        return {}

    @property
    def target_duration_sec(self) -> float:
        return self.constraints.target_duration_sec

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_kind": self.source_kind,
            "language": self.language,
            "title": self.title,
            "topic": self.topic,
            "raw_text": self.raw_text,
            "summary": self.summary,
            "claims": list(self.claims),
            "source_urls": list(self.source_urls),
            "constraints": self.constraints.to_dict(),
            "format_id": self.format_id,
            "template_id": self.template_id,
            "channel_id": self.channel_id,
            "include_cta": self.include_cta,
            "cta_text": self.cta_text,
            "provider_id": self.provider_id,
            "provider_options": dict(self.provider_options),
            "visual_briefs": {key: dict(value) for key, value in self.visual_briefs.items()},
        }


@dataclass
class ScriptScene:
    """One complete thought: what is said, how long it takes, what to show."""

    scene_id: str
    index: int
    role: str
    narration: str
    duration_sec: float
    start_sec: float = 0.0
    on_screen_text: str = ""
    visual_intent: str = ""
    emotion: str = ""
    keywords: list[str] = field(default_factory=list)
    claim_ids: list[str] = field(default_factory=list)
    # Where this scene's text came from (claim id, sentence index, "user_script", ...).
    source_refs: list[str] = field(default_factory=list)
    pause_after_sec: float | None = None
    notes: str = ""
    # What to show, when the author says it explicitly. Never spoken: the voice stage
    # reads ``narration`` only, so nothing here can reach the audio. Empty for every
    # script written before this existed, and for every provider that does not set it.
    # Consumed by src.content.visual_planning; see its ``brief`` module for the fields.
    visual_brief: dict[str, Any] = field(default_factory=dict)

    @property
    def end_sec(self) -> float:
        return self.start_sec + self.duration_sec

    def to_dict(self) -> dict[str, Any]:
        return {
            "scene_id": self.scene_id,
            "index": self.index,
            "role": self.role,
            "narration": self.narration,
            "duration_sec": round(self.duration_sec, 3),
            "start_sec": round(self.start_sec, 3),
            "on_screen_text": self.on_screen_text,
            "visual_intent": self.visual_intent,
            "emotion": self.emotion,
            "keywords": list(self.keywords),
            "claim_ids": list(self.claim_ids),
            "source_refs": list(self.source_refs),
            "pause_after_sec": self.pause_after_sec,
            "notes": self.notes,
            "visual_brief": dict(self.visual_brief),
        }


@dataclass
class ScriptResult:
    """A finished script, independent of how it will be stored or rendered."""

    scenes: list[ScriptScene] = field(default_factory=list)
    title: str = ""
    hook: str = ""
    description: str = ""
    language: str = "ru"
    source_kind: str = SOURCE_TOPIC
    provider_id: str = ""
    provider_version: str = ""
    target_duration_sec: float = 0.0
    source_claim_ids: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: int = SCRIPT_SCHEMA_VERSION

    @property
    def estimated_duration_sec(self) -> float:
        return round(sum(scene.duration_sec for scene in self.scenes), 2)

    @property
    def narration_text(self) -> str:
        return "\n".join(scene.narration for scene in self.scenes)

    def scenes_by_role(self, role: str) -> list[ScriptScene]:
        return [scene for scene in self.scenes if scene.role == role]

    def renumber(self) -> "ScriptResult":
        """Re-assign ids, indexes and start times in list order.

        Providers build scenes incrementally; this is the single place that makes
        the sequence consistent, so no provider has to get the arithmetic right.
        """
        cursor = 0.0
        for index, scene in enumerate(self.scenes, start=1):
            scene.index = index
            scene.scene_id = f"scene_{index:03d}"
            scene.start_sec = round(cursor, 3)
            cursor += scene.duration_sec
        return self

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "title": self.title,
            "hook": self.hook,
            "description": self.description,
            "language": self.language,
            "source_kind": self.source_kind,
            "provider_id": self.provider_id,
            "provider_version": self.provider_version,
            "target_duration_sec": self.target_duration_sec,
            "estimated_duration_sec": self.estimated_duration_sec,
            "narration_text": self.narration_text,
            "source_claim_ids": list(self.source_claim_ids),
            "scene_count": len(self.scenes),
            "scenes": [scene.to_dict() for scene in self.scenes],
            "warnings": list(self.warnings),
            "metadata": dict(self.metadata),
        }


@dataclass
class ScriptValidationIssue:
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
class ScriptValidationResult:
    issues: list[ScriptValidationIssue] = field(default_factory=list)

    @property
    def errors(self) -> list[ScriptValidationIssue]:
        return [issue for issue in self.issues if issue.severity == SEVERITY_ERROR]

    @property
    def warnings(self) -> list[ScriptValidationIssue]:
        return [issue for issue in self.issues if issue.severity == SEVERITY_WARNING]

    @property
    def valid(self) -> bool:
        """No errors. Warnings are informational and never block a render."""
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
    "SCENE_ROLES",
    "SCENE_ROLE_CTA",
    "SCENE_ROLE_DEVELOPMENT",
    "SCENE_ROLE_HOOK",
    "SCENE_ROLE_PAYOFF",
    "SCRIPT_SCHEMA_VERSION",
    "SEVERITY_ERROR",
    "SEVERITY_WARNING",
    "SOURCE_KINDS",
    "SOURCE_NARRATION_TEXT",
    "SOURCE_RESEARCH",
    "SOURCE_TOPIC",
    "SOURCE_USER_SCRIPT",
    "ScriptConstraints",
    "ScriptRequest",
    "ScriptResult",
    "ScriptScene",
    "ScriptValidationIssue",
    "ScriptValidationResult",
]
