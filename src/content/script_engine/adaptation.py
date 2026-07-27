"""Asset-aware script adaptation: change how a scene is said, never what it claims.

The problem this solves is concrete. A scene reads "in January 2023 they collected
samples in the McMurdo Dry Valleys". No stock library has footage of that expedition, so
the scene has no exact material and, before stage Q2.2B, no video could be produced. But
the same sentence can be shown honestly by two frames - the Dry Valleys, and a neutral
close-up of soil being sampled - if the *search* stops demanding one frame that is both.

So adaptation here is mostly not rewriting. It is:

1. splitting a scene into visual parts, so the assembly stage may fill it with two
   assets instead of failing to find one;
2. relaxing what the *search* requires, while the narration keeps every word.

Rewriting the narration is supported through the same contract, but the adapter shipped
with the project does not do it: a deterministic Russian paraphraser that provably
preserves facts is not something this repository has, and an LLM call is never made
without explicit, separate permission. When no rewriting happens, autonomous completion
still works - it falls through to the visual fallback ladder, which is the design.

Every proposal is verified against ``fact_locks`` before it is accepted. A proposal that
drops a number, a date, a name, an uncertainty marker or a source attribution is
rejected and the original line is kept, with the violation recorded.

Exactly one adaptation pass is ever run. There is no rewrite/search/rewrite loop.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Protocol

from .fact_locks import FactLock, FactLockSet, verify_scene_adaptation

ADAPTATION_SCHEMA_VERSION = 1

# --- Adaptation modes --------------------------------------------------------
ADAPT_NONE = "none"
ADAPT_LIGHT = "light"
ADAPTATION_MODES = (ADAPT_NONE, ADAPT_LIGHT)
DEFAULT_ADAPTATION_MODE = ADAPT_NONE

# Only ever one pass: initial script -> initial search -> adapt the problem scenes ->
# search only those -> keep whichever result is better. See MAX_ADAPTATION_PASSES.
MAX_ADAPTATION_PASSES = 1

# --- Rule ids ----------------------------------------------------------------
RULE_SPLIT_VISUAL_PARTS = "split_into_visual_parts"
RULE_RELAX_ACTION = "relax_required_action"
RULE_ENTITY_TO_CONTEXT = "exact_entity_becomes_context"
RULE_BROADEN_SOURCE_CLASS = "broaden_source_class"
RULE_ALLOW_STILLS = "allow_still_images"
RULE_REPHRASE = "rephrase_narration"

# Clause separators a Russian or English sentence really uses. Splitting on these keeps
# every word, so the split can never change a fact.
_CLAUSE_SPLIT_RE = re.compile(r",\s+(?=(?:и|а|но|где|которые|которая|который|and|where|which)\b)|\s+—\s+|;\s+")
_MIN_CLAUSE_WORDS = 3


@dataclass
class SceneAdaptationRequest:
    """One problem scene, and what the retrieval stage could not answer about it."""

    scene_id: str
    narration: str
    reason: str = ""
    missing_slots: list[str] = field(default_factory=list)
    rejected_reasons: list[str] = field(default_factory=list)
    unmatched_requirements: list[str] = field(default_factory=list)
    visual_brief: dict[str, Any] = field(default_factory=dict)
    source_class: str = ""
    scene_duration_sec: float = 0.0
    locks: list[FactLock] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "scene_id": self.scene_id,
            "narration": self.narration,
            "reason": self.reason,
            "missing_slots": list(self.missing_slots),
            "rejected_reasons": list(self.rejected_reasons),
            "unmatched_requirements": list(self.unmatched_requirements),
            "visual_brief": dict(self.visual_brief),
            "source_class": self.source_class,
            "scene_duration_sec": round(float(self.scene_duration_sec), 3),
            "lock_count": len(self.locks),
        }


@dataclass
class SceneAdaptationProposal:
    """What an adapter suggests for one scene. Never applied before verification."""

    scene_id: str
    narration: str = ""
    visual_parts: list[str] = field(default_factory=list)
    revised_brief: dict[str, Any] = field(default_factory=dict)
    rules_applied: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not (self.narration or self.visual_parts or self.revised_brief)


@dataclass
class SceneAdaptation:
    """The accepted (or rejected) outcome for one scene, with its full diff."""

    scene_id: str
    original_narration: str = ""
    adapted_narration: str = ""
    visual_parts: list[str] = field(default_factory=list)
    revised_brief: dict[str, Any] = field(default_factory=dict)
    rules_applied: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    triggered_by: str = ""
    locked_facts: list[str] = field(default_factory=list)
    fact_violations: list[str] = field(default_factory=list)
    accepted: bool = False
    rejection_reason: str = ""

    @property
    def changed(self) -> bool:
        return self.accepted and bool(
            self.visual_parts or self.revised_brief or self.adapted_narration != self.original_narration
        )

    @property
    def narration_changed(self) -> bool:
        return self.accepted and self.adapted_narration != self.original_narration

    def to_dict(self) -> dict[str, Any]:
        return {
            "scene_id": self.scene_id,
            "original_narration": self.original_narration,
            "adapted_narration": self.adapted_narration,
            "narration_changed": self.narration_changed,
            "visual_parts": list(self.visual_parts),
            "revised_brief": dict(self.revised_brief),
            "rules_applied": list(self.rules_applied),
            "reasons": list(self.reasons),
            "triggered_by": self.triggered_by,
            "locked_facts": list(self.locked_facts),
            "fact_violations": list(self.fact_violations),
            "accepted": self.accepted,
            "changed": self.changed,
            "rejection_reason": self.rejection_reason,
        }


@dataclass
class ScriptAdaptationReport:
    mode: str = DEFAULT_ADAPTATION_MODE
    adapter_id: str = ""
    pass_index: int = 0
    scenes: list[SceneAdaptation] = field(default_factory=list)
    fact_lock_kinds: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    schema_version: int = ADAPTATION_SCHEMA_VERSION

    @property
    def changed_scene_ids(self) -> list[str]:
        return [item.scene_id for item in self.scenes if item.changed]

    def for_scene(self, scene_id: str) -> SceneAdaptation | None:
        return next((item for item in self.scenes if item.scene_id == scene_id), None)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "mode": self.mode,
            "adapter_id": self.adapter_id,
            "pass_index": self.pass_index,
            "max_passes": MAX_ADAPTATION_PASSES,
            "changed_scene_ids": self.changed_scene_ids,
            "fact_lock_kinds": list(self.fact_lock_kinds),
            "scene_count": len(self.scenes),
            "scenes": [item.to_dict() for item in self.scenes],
            "warnings": list(self.warnings),
        }


class ScriptAdapter(Protocol):
    """A source of adaptation proposals. Implementations must be side-effect free."""

    adapter_id: str
    paid: bool

    def adapt(self, request: SceneAdaptationRequest) -> SceneAdaptationProposal:
        ...


class NeutralPhrasingAdapter:
    """The offline, deterministic adapter shipped with the project.

    It changes the *requirements*, not the words. Two rules do the work:

    ``split_into_visual_parts``  a sentence with two clauses becomes two visual parts,
                                 so the scene may be filled by two assets instead of one
    ``exact_entity_becomes_context`` a proper noun no provider indexes stops being a hard
                                 search requirement and becomes context - the name stays
                                 in the narration, untouched, because it is a fact

    Everything it produces preserves the narration verbatim, so fact verification is
    guaranteed to pass. That is a property of this adapter, not an excuse to skip the
    check: a different adapter (an LLM one) goes through exactly the same gate.
    """

    adapter_id = "neutral_local_v1"
    paid = False

    def adapt(self, request: SceneAdaptationRequest) -> SceneAdaptationProposal:
        proposal = SceneAdaptationProposal(scene_id=request.scene_id, narration=request.narration)
        brief = dict(request.visual_brief or {})
        revised: dict[str, Any] = {}

        parts = split_visual_parts(request.narration)
        if len(parts) >= 2 and request.scene_duration_sec >= 4.0:
            proposal.visual_parts = parts
            proposal.rules_applied.append(RULE_SPLIT_VISUAL_PARTS)
            proposal.reasons.append("сцена описывает две визуальные части, их можно показать двумя материалами")

        unmatched = {str(item).strip().casefold() for item in request.unmatched_requirements if str(item).strip()}
        must_include = [str(item) for item in (brief.get("must_include") or [])]
        exact_entities = [str(item) for item in (brief.get("exact_entities") or [])]
        if unmatched:
            kept = [item for item in must_include if item.strip().casefold() not in unmatched]
            moved = [item for item in must_include if item.strip().casefold() in unmatched]
            if moved:
                revised["must_include"] = kept
                revised["context"] = _unique(
                    [str(item) for item in (brief.get("context") or [])] + moved
                )
                proposal.rules_applied.append(RULE_ENTITY_TO_CONTEXT)
                proposal.reasons.append(
                    "точное название не индексируется провайдерами: остаётся в тексте, "
                    "но перестаёт быть обязательным условием поиска — " + ", ".join(moved)
                )

        missing = {str(item).split(":")[-1] for item in request.missing_slots}
        if "action" in missing and brief.get("action"):
            revised["action"] = ""
            proposal.rules_applied.append(RULE_RELAX_ACTION)
            proposal.reasons.append("точное действие не находится: остаётся предмет и место")

        if request.source_class in {"exact_location", "specific_object"} and "location" in missing:
            revised["source_class"] = "generic_broll"
            proposal.rules_applied.append(RULE_BROADEN_SOURCE_CLASS)
            proposal.reasons.append(
                "материал именно этого места не найден: сцена ищется как тематический b-roll "
                "и помечается для ручной замены"
            )

        media_types = [str(item) for item in (brief.get("media_types") or [])]
        if media_types and "image" not in media_types:
            revised["media_types"] = _unique(media_types + ["image"])
            proposal.rules_applied.append(RULE_ALLOW_STILLS)
            proposal.reasons.append("разрешены фотографии, а не только видео")

        # ``must_avoid`` is never relaxed: it is the author's refusal, not a search hint.
        if brief.get("must_avoid"):
            revised.setdefault("must_avoid", list(brief["must_avoid"]))
        if exact_entities and "exact_entities" not in revised and revised:
            revised.setdefault("exact_entities", exact_entities)
        proposal.revised_brief = revised
        return proposal


def split_visual_parts(narration: str) -> list[str]:
    """Break one sentence into visual parts without changing a single word."""
    text = str(narration or "").strip()
    if not text:
        return []
    parts = [part.strip(" ,;—") for part in _CLAUSE_SPLIT_RE.split(text) if part and part.strip(" ,;—")]
    parts = [part for part in parts if len(part.split()) >= _MIN_CLAUSE_WORDS]
    return parts if len(parts) >= 2 else []


_ADAPTERS: dict[str, Any] = {}


def register_adapter(adapter: Any) -> None:
    """Make an adapter available by id. Used by tests and by future LLM adapters."""
    _ADAPTERS[str(getattr(adapter, "adapter_id", "") or "")] = adapter


def get_adapter(adapter_id: str = "") -> Any:
    """The requested adapter, or the offline default. Never returns a paid one by name
    it was not asked for."""
    key = str(adapter_id or "").strip()
    if key and key in _ADAPTERS:
        return _ADAPTERS[key]
    return _ADAPTERS[NeutralPhrasingAdapter.adapter_id]


def list_adapters() -> list[dict[str, Any]]:
    return [
        {"adapter_id": key, "paid": bool(getattr(adapter, "paid", False))}
        for key, adapter in sorted(_ADAPTERS.items())
    ]


register_adapter(NeutralPhrasingAdapter())


def normalize_adaptation_mode(value: str | None) -> str:
    text = str(value or "").strip().lower()
    return text if text in ADAPTATION_MODES else DEFAULT_ADAPTATION_MODE


def adapt_scenes(
    *,
    requests: list[SceneAdaptationRequest],
    fact_locks: FactLockSet,
    adapter: Any | None = None,
    mode: str = ADAPT_LIGHT,
    pass_index: int = 0,
    allow_paid: bool = False,
) -> ScriptAdaptationReport:
    """Run exactly one adaptation pass over the scenes that could not be answered.

    Every proposal is checked against the scene's own fact locks before it is accepted.
    A rejected proposal is recorded in full - what was proposed and which fact it would
    have changed - and the original line is kept.
    """
    mode = normalize_adaptation_mode(mode)
    engine = adapter or get_adapter()
    report = ScriptAdaptationReport(
        mode=mode,
        adapter_id=str(getattr(engine, "adapter_id", "") or ""),
        pass_index=pass_index,
        fact_lock_kinds=fact_locks.kinds(),
    )
    if mode == ADAPT_NONE:
        report.warnings.append("script_adaptation_disabled")
        return report
    if pass_index >= MAX_ADAPTATION_PASSES:
        report.warnings.append("adaptation_pass_limit_reached")
        return report
    if bool(getattr(engine, "paid", False)) and not allow_paid:
        report.warnings.append(f"adapter_{report.adapter_id}_requires_explicit_paid_approval")
        return report

    for request in requests:
        locks = request.locks or fact_locks.for_scene(request.scene_id)
        outcome = SceneAdaptation(
            scene_id=request.scene_id,
            original_narration=request.narration,
            adapted_narration=request.narration,
            triggered_by=request.reason,
            locked_facts=[f"{lock.kind}:{lock.surface}" for lock in locks],
        )
        try:
            proposal = engine.adapt(request)
        except Exception as exc:  # an adapter must never take the pipeline down with it
            outcome.rejection_reason = f"adapter_failed:{exc}"
            report.scenes.append(outcome)
            continue
        if proposal is None or proposal.is_empty:
            outcome.rejection_reason = "adapter_proposed_no_change"
            report.scenes.append(outcome)
            continue
        candidate_text = proposal.narration or request.narration
        violations = verify_scene_adaptation(
            candidate_text,
            locks,
            original=request.narration,
        )
        if violations:
            outcome.fact_violations = violations
            outcome.rejection_reason = "fact_lock_violation"
            outcome.reasons = list(proposal.reasons)
            outcome.rules_applied = list(proposal.rules_applied)
            report.scenes.append(outcome)
            continue
        outcome.adapted_narration = candidate_text
        outcome.visual_parts = list(proposal.visual_parts)
        outcome.revised_brief = dict(proposal.revised_brief)
        outcome.rules_applied = list(proposal.rules_applied)
        outcome.reasons = list(proposal.reasons)
        outcome.accepted = True
        report.scenes.append(outcome)
    return report


def apply_adaptation_to_script(script: dict[str, Any], report: ScriptAdaptationReport) -> dict[str, Any]:
    """A copy of the script with accepted adaptations applied.

    Additive and reversible: the original text of every adapted scene is kept on the
    scene as ``original_narration``, and the untouched original script is written beside
    the adapted one by the caller.
    """
    updated = dict(script)
    scenes: list[dict[str, Any]] = []
    for index, scene in enumerate(script.get("scenes") or [], start=1):
        if not isinstance(scene, dict):
            scenes.append(scene)
            continue
        scene_id = str(scene.get("scene_id") or f"scene_{index:03d}")
        adaptation = report.for_scene(scene_id)
        if adaptation is None or not adaptation.changed:
            scenes.append(dict(scene))
            continue
        adapted = dict(scene)
        if adaptation.narration_changed:
            adapted["original_narration"] = adaptation.original_narration
            adapted["narration"] = adaptation.adapted_narration
        if adaptation.visual_parts:
            adapted["visual_parts"] = list(adaptation.visual_parts)
        if adaptation.revised_brief:
            brief = dict(adapted.get("visual_brief") or {})
            brief.update({key: value for key, value in adaptation.revised_brief.items()})
            adapted["visual_brief"] = {key: value for key, value in brief.items() if value not in ("", [], {})}
            adapted["visual_brief_adapted"] = True
        adapted["adaptation_rules"] = list(adaptation.rules_applied)
        scenes.append(adapted)
    updated["scenes"] = scenes
    updated["narration_text"] = "\n".join(
        str(scene.get("narration") or "") for scene in scenes if isinstance(scene, dict)
    )
    updated["script_adaptation"] = {
        "adapter_id": report.adapter_id,
        "mode": report.mode,
        "pass_index": report.pass_index,
        "changed_scene_ids": report.changed_scene_ids,
    }
    return updated


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
    "ADAPTATION_MODES",
    "ADAPTATION_SCHEMA_VERSION",
    "ADAPT_LIGHT",
    "ADAPT_NONE",
    "DEFAULT_ADAPTATION_MODE",
    "MAX_ADAPTATION_PASSES",
    "RULE_ALLOW_STILLS",
    "RULE_BROADEN_SOURCE_CLASS",
    "RULE_ENTITY_TO_CONTEXT",
    "RULE_RELAX_ACTION",
    "RULE_REPHRASE",
    "RULE_SPLIT_VISUAL_PARTS",
    "NeutralPhrasingAdapter",
    "SceneAdaptation",
    "SceneAdaptationProposal",
    "SceneAdaptationRequest",
    "ScriptAdaptationReport",
    "ScriptAdapter",
    "adapt_scenes",
    "apply_adaptation_to_script",
    "get_adapter",
    "list_adapters",
    "normalize_adaptation_mode",
    "register_adapter",
    "split_visual_parts",
]
