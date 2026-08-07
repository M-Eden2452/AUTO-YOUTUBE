"""The default planner: works out what to show from the script's own words.

Replaces a four-branch ``if`` in the retired ``news.visual_plan`` stock query (whale,
scientist, ocean, everything else) that returned one of four fixed English strings
for every video ever made.

What it does
------------
- ranks the things the whole script names, so the video's actual subject is known
  before any single scene is planned;
- gives each scene a subject, an action, a place and a period **only when the scene
  itself contains them**;
- picks a shot type from what the scene is doing dramatically, not from its index;
- builds a primary search intent plus genuinely different fallbacks, each one a step
  more general, so a failed exact search degrades instead of repeating itself.

What it refuses to do
---------------------
- invent an entity, a place or a date that is not in the script or the claims;
- replace the named animal, country or technology with a general category;
- translate: intents come out in the script's language and say so.

No network, no model call, no randomness: the same script always produces the same
plan, which is what makes it usable offline and in tests.
"""

from __future__ import annotations

from typing import Any

from ..contract import BaseVisualPlanner, VisualPlannerCapabilities, VisualPlannerInputError
from ..entities import (
    collect_entities,
    entities_in,
    extract_actions,
    extract_period,
    extract_places,
    is_latin,
)
from ..entities import stem as _stem
from ..models import (
    INTENT_ALTERNATIVE,
    INTENT_ATMOSPHERIC_FALLBACK,
    INTENT_CONTEXT_FALLBACK,
    INTENT_PRIMARY,
    MEDIA_ANIMATED_IMAGE,
    MEDIA_ARCHIVE_FOOTAGE,
    MEDIA_IMAGE,
    MEDIA_MAP,
    MEDIA_VIDEO,
    SHOT_ACTION,
    SHOT_CONTEXT,
    SHOT_DETAIL,
    SHOT_ESTABLISHING,
    SHOT_EVIDENCE,
    SHOT_PAYOFF,
    SceneVisualPlan,
    VisualPlanRequest,
    VisualPlanResult,
    VisualSearchIntent,
)

PLANNER_ID = "deterministic_local"

# Scene roles as the script engine writes them.
_ROLE_HOOK = "hook"
_ROLE_PAYOFF = "payoff"
_ROLE_CTA = "cta"

# How many secondary things one scene may carry before the frame is a crowd.
MAX_SECONDARY_SUBJECTS = 2
# A scene naming fewer than this many known entities has nothing concrete to film.
MIN_ENTITIES_FOR_CONCRETE_SCENE = 1


class DeterministicVisualPlanner(BaseVisualPlanner):
    capabilities_spec = VisualPlannerCapabilities(
        planner_id=PLANNER_ID,
        display_name="Локальный смысловой визуальный план",
        description=(
            "Определяет предмет, действие, место и эпоху каждой сцены по её собственному "
            "тексту, выбирает тип кадра и строит поисковые intents с расширяющимися "
            "запасными вариантами. Работает офлайн и бесплатно, результат воспроизводим."
        ),
        requires_network=False,
        requires_paid_api=False,
        deterministic=True,
        intent_language="source",
        implementation_status="targeted_tested",
    )

    def plan(self, request: VisualPlanRequest) -> VisualPlanResult:
        scenes = list(getattr(request.script, "scenes", None) or [])
        if not scenes:
            raise VisualPlannerInputError(
                "Сценарий не содержит сцен: планировать нечего.", planner=PLANNER_ID
            )

        scene_texts = {scene.scene_id: scene.narration for scene in scenes}
        entities = collect_entities(
            scene_texts=scene_texts,
            topic=request.topic,
            title=request.title,
            claims=request.claims,
        )
        topic_entity = entities[0] if entities else None
        language = request.language or getattr(request.script, "language", "") or "ru"

        planned: list[SceneVisualPlan] = []
        warnings: list[str] = []
        for index, scene in enumerate(scenes, start=1):
            planned.append(
                _plan_scene(
                    scene,
                    index=index,
                    entities=entities,
                    topic_entity=topic_entity,
                    language=language,
                    request=request,
                )
            )

        _warn_on_identical_intents(planned, warnings)
        return VisualPlanResult(
            scenes=planned,
            language=language,
            topic_entity=topic_entity.surface if topic_entity else "",
            planner_id=PLANNER_ID,
            planner_version="1.0",
            format_id=request.format_id,
            aspect_ratio=request.aspect_ratio,
            warnings=warnings,
            metadata={
                "entity_count": len(entities),
                "requires_translation": any(
                    intent.requires_translation for plan in planned for intent in plan.intents
                ),
                "intent_language": language,
            },
        )


def _plan_scene(
    scene: Any,
    *,
    index: int,
    entities: list,
    topic_entity: Any,
    language: str,
    request: VisualPlanRequest,
) -> SceneVisualPlan:
    narration = getattr(scene, "narration", "") or ""
    role = getattr(scene, "role", "") or ""

    actions = extract_actions(narration)
    action = actions[0] if actions else ""
    places = extract_places(narration)
    place = places[0] if places else ""
    period = extract_period(narration)

    # A place is where the scene happens, not what it is about: "в Вашингтонском
    # университете" must not become the thing the camera points at.
    place_stems = {_stem(token) for token in places}
    present = [
        entity for entity in entities_in(narration, entities) if entity.stem not in place_stems
    ]

    subject_entity = _pick_subject(present, topic_entity)
    subject = subject_entity.surface if subject_entity else ""
    secondary = [
        entity.surface
        for entity in present
        if entity is not subject_entity
    ][:MAX_SECONDARY_SUBJECTS]

    claim_ids = list(getattr(scene, "claim_ids", []) or [])
    shot_type = _shot_type(role=role, action=action, place=place, claim_ids=claim_ids, text=narration)
    preferred, allowed = _media_kinds(subject=subject, period=period, place=place, shot_type=shot_type)

    # ``must_include`` is a hard requirement: the term has to reach the provider query
    # verbatim *and* be found in the returned metadata, or the candidate is refused.
    # A term this planner extracted from Russian narration can do neither - every remote
    # provider is English-only (src.assets.query_adapter), so the word is never sent and
    # can never appear in an answer. Promoting it anyway made the requirement
    # unverifiable by construction, and an unverifiable requirement refuses *every*
    # candidate: the retest left scene_002 and scene_008 empty over `долинах` and
    # `пластик`, words the author never asked for. The extracted subject and place stay
    # where they can still be judged - the subject and location slots, which score
    # partial evidence instead of demanding a literal hit.
    must_include = [subject] if subject and is_latin(subject) else []
    if shot_type in {SHOT_ESTABLISHING, SHOT_EVIDENCE} and place and is_latin(place):
        must_include.append(place)

    warnings: list[str] = []
    if not subject:
        # An abstract scene is legitimate (a payoff often is), but it cannot be
        # searched for exactly, and saying so is more useful than a vague query.
        warnings.append("no_concrete_subject: в сцене не названо ни одной конкретной сущности")

    intents = _build_intents(
        subject=subject,
        action=action,
        place=place,
        period=period,
        secondary=secondary,
        topic_entity=topic_entity,
        language=language,
    )

    return SceneVisualPlan(
        scene_id=getattr(scene, "scene_id", "") or f"scene_{index:03d}",
        index=index,
        meaning=_meaning(narration),
        subject=subject,
        secondary_subjects=secondary,
        action=action,
        place=place,
        period=period,
        shot_type=shot_type,
        allowed_media_kinds=allowed,
        preferred_media_kind=preferred,
        must_include=must_include,
        # Nothing is put here by default on purpose: inventing negatives without
        # domain knowledge is exactly how the previous prototype ended up refusing
        # deserts and mountains for every video because one of them was about whales.
        must_avoid=[],
        intents=intents,
        claim_ids=claim_ids,
        source_refs=list(getattr(scene, "source_refs", []) or []),
        entities=[entity for entity in present[:4]],
        duration_sec=float(getattr(scene, "duration_sec", 0.0) or 0.0),
        warnings=warnings,
    )


def _pick_subject(present: list, topic_entity: Any):
    """The scene's own most salient thing, preferring the video's subject.

    Continuity matters: if the scene names the animal the whole video is about, that
    is what the frame should show, even when the scene also names something rarer.
    """
    if not present:
        return None
    if topic_entity is not None:
        for entity in present:
            if entity.stem == topic_entity.stem:
                return entity
    return present[0]


def _shot_type(*, role: str, action: str, place: str, claim_ids: list[str], text: str) -> str:
    if role == _ROLE_HOOK:
        return SHOT_ESTABLISHING
    if role == _ROLE_PAYOFF:
        return SHOT_PAYOFF
    if role == _ROLE_CTA:
        return SHOT_CONTEXT
    if claim_ids and place:
        # A scene that cites where something was established is showing evidence.
        return SHOT_EVIDENCE
    if action:
        return SHOT_ACTION
    if any(character.isdigit() for character in text):
        return SHOT_DETAIL
    return SHOT_CONTEXT


def _media_kinds(*, subject: str, period: str, place: str, shot_type: str) -> tuple[str, list[str]]:
    """What kinds of material could carry this scene. Video first: this is a short."""
    allowed = [MEDIA_VIDEO, MEDIA_IMAGE]
    preferred = MEDIA_VIDEO
    if period:
        # Something dated cannot be filmed today; archive material is legitimate.
        allowed.append(MEDIA_ARCHIVE_FOOTAGE)
    if place and not subject:
        # A place with nothing in it to film is what a map is for.
        allowed.append(MEDIA_MAP)
    if not subject:
        preferred = MEDIA_ANIMATED_IMAGE
        allowed.append(MEDIA_ANIMATED_IMAGE)
    return preferred, allowed


def _build_intents(
    *,
    subject: str,
    action: str,
    place: str,
    period: str,
    secondary: list[str],
    topic_entity: Any,
    language: str,
) -> list[VisualSearchIntent]:
    """Primary plus fallbacks, each a real step more general than the last.

    A fallback that repeats the primary is not a fallback, so anything that ends up
    with the same terms as an earlier intent is dropped rather than kept for show.
    """
    candidates: list[VisualSearchIntent] = []

    if subject:
        candidates.append(
            VisualSearchIntent(
                kind=INTENT_PRIMARY,
                subject=subject,
                modifiers=[term for term in (action, period) if term],
                context=[term for term in (place, *secondary[:1]) if term],
                language=language,
                fallback_level=1,
                notes="точный предмет сцены с действием и местом",
            )
        )
        candidates.append(
            VisualSearchIntent(
                kind=INTENT_ALTERNATIVE,
                subject=subject,
                modifiers=[],
                context=[term for term in secondary[:1] if term],
                language=language,
                fallback_level=2,
                notes="тот же предмет без действия",
            )
        )

    context_terms = [term for term in (place, *secondary) if term]
    if context_terms:
        candidates.append(
            VisualSearchIntent(
                kind=INTENT_CONTEXT_FALLBACK,
                subject=context_terms[0],
                modifiers=[],
                context=context_terms[1:],
                language=language,
                fallback_level=3,
                notes="окружение сцены без её предмета",
            )
        )

    if topic_entity is not None:
        candidates.append(
            VisualSearchIntent(
                kind=INTENT_ATMOSPHERIC_FALLBACK,
                subject=topic_entity.surface,
                modifiers=[],
                context=[],
                language=language,
                fallback_level=4,
                notes="общая тема видео",
            )
        )

    intents: list[VisualSearchIntent] = []
    seen: set[tuple[str, ...]] = set()
    for intent in candidates:
        key = tuple(term.casefold() for term in intent.terms)
        if not key or key in seen:
            continue
        seen.add(key)
        intent.requires_translation = not all(is_latin(term) for term in intent.terms)
        intents.append(intent)
    return intents


def _meaning(narration: str) -> str:
    """One-line statement of what the scene says, in the scene's own words."""
    text = " ".join((narration or "").split())
    return text if len(text) <= 200 else text[:200].rsplit(" ", 1)[0]


def _warn_on_identical_intents(planned: list[SceneVisualPlan], warnings: list[str]) -> None:
    """Every scene searching for the same thing is the defect Q2 exists to remove."""
    primaries = [
        tuple(term.casefold() for term in plan.intents[0].terms)
        for plan in planned
        if plan.intents
    ]
    if len(primaries) > 1 and len(set(primaries)) == 1:
        warnings.append(
            "identical_primary_intents: у всех сцен получился одинаковый основной запрос — "
            "материала не хватило, чтобы различить сцены"
        )


__all__ = ["MAX_SECONDARY_SUBJECTS", "PLANNER_ID", "DeterministicVisualPlanner"]
