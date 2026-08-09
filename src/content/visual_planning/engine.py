"""One entry point: script in, validated visual plan out."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from .brief import VisualBrief, apply_brief, parse_brief, produce_brief
from .contract import VisualPlanner, VisualPlannerError, VisualPlannerUnavailableError
from .legacy_format import to_legacy_visual_plan
from .models import (
    VisualPlanRequest,
    VisualPlanResult,
    VisualPlanValidationResult,
    rebuild_intents,
)
from .registry import get_planner, resolve_planner_id
from .semantic_brief import apply_semantic_brief, evidence_for_scene
from .validation import validate_visual_plan

# The model was asked and had nothing to say. The other two outcomes a later diagnostic
# has to tell this apart from - the model could not be reached, the answer was refused -
# are recorded under the errors' own ``code``, so there is no second vocabulary. A defect
# in the injected callable is deliberately not among them: it never reaches here, because
# ``semantic_brief`` lets it out.
SEMANTIC_NO_ANSWER = "semantic_brief_no_answer"


@dataclass
class VisualPlanning:
    """A plan together with the verdict on it and how it was produced."""

    result: VisualPlanResult
    validation: VisualPlanValidationResult
    planner_id: str
    requested_planner_id: str = ""

    @property
    def used_fallback(self) -> bool:
        return bool(self.requested_planner_id) and self.requested_planner_id != self.planner_id

    def to_legacy_plan(self, **kwargs: Any) -> dict[str, Any]:
        return to_legacy_visual_plan(self.result, **kwargs)

    def to_dict(self) -> dict[str, Any]:
        return {
            "planner_id": self.planner_id,
            "requested_planner_id": self.requested_planner_id,
            "used_fallback": self.used_fallback,
            "plan": self.result.to_dict(),
            "validation": self.validation.to_dict(),
        }


def build_plan(
    request: VisualPlanRequest,
    *,
    planner: VisualPlanner | None = None,
    source_text: str = "",
    brief_adapter: Any = None,
) -> VisualPlanning:
    """Run the planner the request resolves to and validate what comes back.

    Validation never raises: an unusable plan is returned *with* its problems, so the
    caller (CLI, pipeline) decides whether to stop. Planner failures do raise - a
    planner that cannot produce a plan has nothing to report on.

    ``brief_adapter`` is the optional model-assisted semantic adapter
    (``semantic_brief.ModelSemanticBriefAdapter``). It is injected rather than resolved
    here for the same reason the planner is: this layer must not decide that money may
    be spent. Omitted - which is every production caller today - the plan is exactly
    the deterministic plan it has always been.
    """
    if planner is not None:
        engine = planner
        requested_id = getattr(planner.capabilities, "planner_id", "") or resolve_planner_id(request)
    else:
        requested_id = resolve_planner_id(request)
        engine = get_planner(requested_id)

    if not engine.supports(request):
        raise VisualPlannerUnavailableError(
            f"Планировщик {requested_id!r} не может работать с этим сценарием.", planner=requested_id
        )
    result = engine.plan(request)
    author_briefs = _author_briefs(request.script)
    _produce_scene_briefs(result, request, adapter=brief_adapter, author_briefs=author_briefs)
    _apply_scene_briefs(result, author_briefs)
    validation = validate_visual_plan(result, script=request.script, source_text=source_text)
    return VisualPlanning(
        result=result,
        validation=validation,
        planner_id=result.planner_id or requested_id,
        requested_planner_id=requested_id,
    )


def _author_briefs(script: dict[str, Any] | None) -> dict[str, VisualBrief]:
    """The author's explicit brief per scene id, parsed once.

    Read once and shared, because two stages need the same answer for opposite reasons:
    the override pass applies these last, and the automatic pass skips a scene they will
    overwrite anyway. Deriving it twice is how the two would drift into disagreeing about
    which scenes the author has already answered.
    """
    # ``script`` is a ScriptResult here and a plain dict when a plan is rebuilt from a
    # stored script.json, so both shapes are read.
    raw_scenes = script.get("scenes") if isinstance(script, dict) else getattr(script, "scenes", None)
    briefs: dict[str, VisualBrief] = {}
    for scene in raw_scenes or []:
        if isinstance(scene, dict):
            scene_id, raw = str(scene.get("scene_id") or ""), scene.get("visual_brief")
        else:
            scene_id, raw = str(getattr(scene, "scene_id", "") or ""), getattr(scene, "visual_brief", None)
        if not scene_id or not raw:
            continue
        brief = parse_brief(raw)
        if not brief.is_empty:
            briefs[scene_id] = brief
    return briefs


def _apply_scene_briefs(result: VisualPlanResult, briefs: dict[str, VisualBrief]) -> None:
    """Let the author's explicit brief win over whatever was extracted.

    Applied after the planner rather than inside it so every planner benefits and none
    has to know the brief exists. A script with no briefs is untouched.
    """
    if not briefs:
        return
    for scene in result.scenes:
        brief = briefs.get(scene.scene_id)
        if brief is None:
            continue
        apply_brief(scene, brief)
        scene.brief = brief
        # The intents were built from the extracted fields; rebuild them so the query
        # actually carries the names the author insisted on.
        scene.intents = rebuild_intents(scene, language=result.language)


def _produce_scene_briefs(
    result: VisualPlanResult,
    request: VisualPlanRequest,
    *,
    adapter: Any = None,
    author_briefs: dict[str, VisualBrief] | None = None,
) -> None:
    """Produce automatic briefs before the existing author-override pass.

    Precedence, weakest last: evidence the material already states in the provider's
    language, then - only for the scenes that still do not say what to show - what an
    injected model says the scene means. The author's explicit brief is applied after
    both by ``_apply_scene_briefs`` and wins, which is the acceptance criterion neither
    automatic path may weaken.
    """
    raw_scenes = (
        request.script.get("scenes")
        if isinstance(request.script, dict)
        else getattr(request.script, "scenes", None)
    )
    script_scenes = list(raw_scenes or [])
    by_id: dict[str, Any] = {}
    for raw in script_scenes:
        scene_id = (
            str(raw.get("scene_id") or "")
            if isinstance(raw, dict)
            else str(getattr(raw, "scene_id", "") or "")
        )
        if scene_id:
            by_id[scene_id] = raw

    answered_by_author = set(author_briefs or {})
    for position, scene in enumerate(result.scenes):
        script_scene = by_id.get(scene.scene_id)
        if script_scene is None and position < len(script_scenes):
            script_scene = script_scenes[position]
        claims = list(request.claims or [])
        brief = produce_brief(scene, script_scene=script_scene, claims=claims)
        if adapter is not None and _needs_semantic_help(scene, answered_by_author):
            semantic = _semantic_brief(
                scene,
                script_scene=script_scene,
                claims=claims,
                adapter=adapter,
                language=result.language,
            )
            # Only ever an addition. Offering assistance to a scene that already had
            # *some* provider-language evidence must not cost it that evidence when the
            # answer is refused.
            if not semantic.is_empty:
                brief = semantic
        if not brief.is_empty:
            scene.brief = brief


def _needs_semantic_help(scene: Any, answered_by_author: set[str]) -> bool:
    """Whether this scene is one an approved adapter may be asked about.

    Everything an automatic pass can observe about a scene has now been tried as an
    answer to "does planning already know what this scene is about", and each was the
    same mistake wearing a different hat:

    - ``brief.is_empty`` - non-empty as soon as *any* provider-language evidence produces
      a query, so a linked English claim or a bag of prepared keywords qualified a scene
      the plan still called ``воды``;
    - ``brief.subject`` - non-empty as soon as extraction produced something searchable,
      and on an ordinary English sentence extraction produces the place or the
      preposition: ``antarctic`` for a scene about a penguin colony;
    - the subject being marked ``ENTITY_KIND_TOPIC`` - closer, because a topic really is
      a declaration, but a declaration about the *video*. ``Antarctic penguin colonies``
      marks ``antarctic`` and ``penguin`` alike, so it cannot say which of them this scene
      shows, and the wrong one was protected by the presence of the right one.

    A word's role in a global string is not a statement about one scene, so nothing
    derived from the script's own text is asked again here. The remaining question is one
    of authority, and exactly one source in this repository has it: the author's
    ``visual_brief``, written per scene beside the narration. That brief is applied after
    this pass and replaces whatever a model would say, so asking about such a scene is
    spending on an answer that is thrown away.

    Every other scene is planned automatically and is eligible for one call. That is
    deliberately more calls than the withdrawn rule made - correctness first; a cost
    policy built on a signal that cannot tell a right subject from a wrong one is not a
    saving. Narrowing it again is a decision for real diagnostic evidence, and it needs a
    scene-level source of authority that does not exist yet rather than a new confidence
    field invented to justify skipping.

    Nothing is spent by returning ``True``: the adapter's own preconditions still decide
    whether a backend is reached, and no production caller injects one. C63 is unchanged -
    this only skips scenes whose author brief actually reached visual planning.
    """
    return getattr(scene, "scene_id", "") not in answered_by_author


def _semantic_brief(
    scene: Any,
    *,
    script_scene: Any,
    claims: list[dict[str, Any]],
    adapter: Any,
    language: str,
) -> VisualBrief:
    """What a model says this scene means, expressed as the existing brief.

    The adapter states meaning and nothing else. Overlaying it onto the scene and then
    re-running the existing producer is what keeps a single query owner: every string a
    provider can receive is still built by ``expansion`` from the overlaid scene, so this
    path cannot hand a provider a phrase the ladder did not compose.

    The overlay is rehearsed on a copy first. A semantic answer the ladder cannot turn
    into a query has to leave the scene exactly as the planner left it - otherwise a
    brief this layer refused would still reach a provider through the rebuilt intents,
    which is the opposite of failing closed.

    Whether a backend is reached at all is settled *here*, before it is called, from the
    adapter's own preconditions: an adapter that is not wired or not approved, and a scene
    with nothing to reason about, are all the same situation as having no adapter, and
    that situation has to leave the plan exactly as an adapter-less run leaves it. Once
    past this point the call happened, and every controlled way it can fail is recorded.
    """
    evidence = evidence_for_scene(scene, script_scene=script_scene, claims=claims)
    if not adapter.is_available() or evidence.is_empty:
        return VisualBrief()
    try:
        semantic = adapter.brief_for(evidence)
    except VisualPlannerError as error:
        _record_semantic_outcome(scene, error)
        return VisualBrief()
    if semantic.is_empty:
        _record_semantic_outcome(scene, None)
        return VisualBrief()

    produced = _overlay(deepcopy(scene), semantic, script_scene=script_scene, claims=claims, language=language)
    if produced.is_empty:
        _record_semantic_outcome(scene, None)
        return VisualBrief()
    _overlay(scene, semantic, script_scene=script_scene, claims=claims, language=language)
    # Only an author or a model states what surrounds the subject, so it is carried
    # across explicitly: the producer reads planner fields, and the plan has none.
    produced.context = list(semantic.context)
    return produced


def _overlay(
    scene: Any,
    semantic: VisualBrief,
    *,
    script_scene: Any,
    claims: list[dict[str, Any]],
    language: str,
) -> VisualBrief:
    # ``apply_semantic_brief``, not ``apply_brief``: the author's rule that an unstated
    # field is a deliberate answer belongs to the author, who was asked. A model is never
    # offered a constraint field, so its silence about one may not delete it.
    apply_semantic_brief(scene, semantic)
    scene.intents = rebuild_intents(scene, language=language)
    return produce_brief(scene, script_scene=script_scene, claims=claims)


def _record_semantic_outcome(scene: Any, error: VisualPlannerError | None) -> None:
    """Leave enough on the scene to tell *why* semantic assistance did not help.

    Written into the scene's existing ``warnings``, in the ``code: message`` shape the
    deterministic planner already uses for ``no_concrete_subject``. Nothing new is
    persisted and nothing new has to be read: ``planning_warnings`` already round-trips
    through ``legacy_format`` and no gate treats it as blocking.

    Reached only when a backend was actually asked, so every outcome here is recorded.
    ``retryable`` used to decide that instead, and it cannot: it answers whether asking
    again could help, and a backend that says *permanently* no - a rejected key, a model
    the account may not select - answers that the same way an unwired adapter does. A real
    failed call then left the plan byte-identical to a run with no adapter, which is the
    one distinction a later diagnostic has to be able to make. ``_semantic_brief`` decides
    "was anything asked" from the adapter's preconditions; this function no longer guesses
    it from the error.
    """
    warning = (
        f"{SEMANTIC_NO_ANSWER}: сцена {scene.scene_id} — модель не назвала, что показывать"
        if error is None
        else f"{error.code}: {error}"
    )
    if warning not in scene.warnings:
        scene.warnings.append(warning)


__all__ = ["VisualPlanning", "VisualPlannerError", "build_plan"]
