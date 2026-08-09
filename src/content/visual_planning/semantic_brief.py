"""What a scene means, when the scene's own words are not the provider's words.

``brief.produce_brief`` packages provider-language evidence that the material already
contains. An ordinary prepared script in another language contains none, and that is
not a wiring defect: the producer runs, finds nothing English to say, and returns an
empty brief so the query adapter stays fail-closed. Deterministic extraction cannot
close the gap either, because it ranks words by how the sentence uses them rather than
by what they name - the word that names the shot and the word the sentence repeats are
routinely not the same word, and the confirmed failure was a run where most scenes
reached the adapter with nothing to send and the one that did sent a single environment
noun.

This module adds the missing step and nothing else. Given one scene's own evidence, a
model states *what should be shown* as fields of the existing ``VisualBrief``:

    scene evidence -> model -> existing VisualBrief -> existing expansion ladder
                                                   -> existing query adapter

It is deliberately **not** a translator. It never receives a token some earlier
heuristic picked out and is never asked to render that token in another language; it
receives the scene and answers what the frame must contain. It is deliberately **not**
a second planner: it produces no query string, no ranking and no plan, and every query
a provider ever sees is still built by ``expansion`` from the brief filled in here.

Nothing here calls an API. Exactly like ``script_engine.providers.llm``:

- there is no API client, no key lookup and no network import in this module;
- the model call is an injected callable, so the only way to run this adapter is for a
  caller to hand it one;
- without one the adapter is unavailable, and an unavailable adapter changes nothing:
  the deterministic plan is what it always was;
- even with one it refuses to run unless ``approved=True`` is passed explicitly,
  mirroring the on-disk approval gate that already protects paid TTS.

Wiring a real model to this seam is a separate decision and is not made here: a text
model call has no class in ``src.runtime_network.NETWORK_ACTIONS`` today, and network
permission and paid approval are two different gates.

What *is* implemented is the part that has to be right before any money is spent: the
response contract and its parser. The answer is closed - unknown fields, unknown shot
types, wrong types, source-language leakage, a subject made only of production
vocabulary and anything the scene forbade are all refused outright. A refused answer
leaves the scene exactly as the planner left it, keeping the honest
``query_translation_required`` state rather than a plausible brief nobody can trace
back to the script.

Failing closed is for the failures that are *expected*. A model that times out, a
backend that is down and an answer that does not match the contract are all ordinary
outcomes of asking, and each becomes one of this module's own errors so a caller can
tell them apart. A callable with the wrong signature, or one that raises out of its own
defect, is none of those: it is the integration being wrong, and it is left to escape
exactly as ``script_engine.providers.llm`` leaves it. Swallowing it would spend the run
looking for a model that was never the problem.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Callable

from src.content.script_engine.text_analysis import STOPWORDS

from .brief import VisualBrief, apply_brief, scene_claim_texts
from .contract import VisualPlannerError, VisualPlannerUnavailableError
from .expansion import (
    NON_FACTUAL_QUERY_TERMS,
    PROVIDER_LANGUAGE,
    mentions_avoided,
    provider_language_text,
)
from .models import SHOT_TYPES

ADAPTER_ID = "model_semantic_brief"

# The exact JSON a model must return. Kept next to the parser so the two cannot drift
# apart; the prompt builder lives here for the same reason.
#
# Every key is an existing ``VisualBrief`` field. Nothing that carries authority is
# offered: ``must_include`` is a hard requirement a candidate is refused for missing,
# ``must_avoid`` is a rights- and meaning-level constraint, and ``provider_queries``
# bypasses query building entirely. A model may say what the scene is about; it may not
# invent what the author forbade or hand a provider a string of its own.
RESPONSE_CONTRACT: dict[str, Any] = {
    "subject": (
        "str - what must be in frame, in the provider's language. "
        "Empty when the evidence does not say what to show."
    ),
    "action": "str, optional - what the subject is doing",
    "place": "str, optional - where it happens",
    "context": ["str, optional - what surrounds the subject without replacing it"],
    "shot_type": f"str, optional - one of: {' | '.join(SHOT_TYPES)}",
}
RESPONSE_FIELDS = frozenset(RESPONSE_CONTRACT)

# One field is a phrase, not a sentence: the same eight-term ceiling the ladder applies
# to a finished query, so a model cannot smuggle a paragraph into a subject.
MAX_FIELD_TERMS = 8
MAX_CONTEXT_ITEMS = 4

SemanticBriefCompletionFn = Callable[[str, dict[str, Any]], "str | dict[str, Any]"]


class SemanticBriefUnavailableError(VisualPlannerUnavailableError):
    """No model call to make, no approval to make it, or nothing to ask about."""

    code = "semantic_brief_unavailable"


class SemanticBriefResponseError(VisualPlannerError):
    """The model answered something this layer refuses to turn into a brief."""

    code = "semantic_brief_response"


@dataclass(frozen=True)
class SceneBriefEvidence:
    """Everything the adapter may know about one scene, and nothing else.

    Topic, title and channel are absent on purpose: they are the literals the retired
    broad queries were built from, and a brief derived from them describes the channel
    rather than the scene. What is here is what the script itself states about *this*
    scene, plus the constraints already attached to it.
    """

    scene_id: str = ""
    narration: str = ""
    on_screen_text: str = ""
    keywords: tuple[str, ...] = ()
    # Research the script linked to this scene by claim id, already filtered to what is
    # safe to say.
    claims: tuple[str, ...] = ()
    must_include: tuple[str, ...] = ()
    must_avoid: tuple[str, ...] = ()
    shot_type: str = ""

    @property
    def is_empty(self) -> bool:
        """True when there is nothing to reason about, so nothing is asked."""
        return not any([self.narration, self.on_screen_text, self.keywords, self.claims])


def evidence_for_scene(
    scene: Any,
    *,
    script_scene: Any = None,
    claims: Iterable[dict[str, Any]] = (),
    author_brief: VisualBrief | None = None,
) -> SceneBriefEvidence:
    """Read one scene's evidence off the objects the pipeline already has.

    ``author_brief`` supplies the constraints the author wrote but the plan does not carry
    yet: the author's brief is applied *after* this pass, so a scene briefed with nothing
    but ``must_avoid`` would otherwise be asked about without the prohibition being stated.
    Only the constraints are read - a brief that states meaning is not asked about at all,
    and nothing here gives a model authority over what it is told.
    """
    required = list(_texts(getattr(scene, "must_include", None)))
    avoided = list(_texts(getattr(scene, "must_avoid", None)))
    if author_brief is not None:
        required += list(author_brief.exact_entities) + list(author_brief.must_include)
        avoided += list(author_brief.must_avoid)
    return SceneBriefEvidence(
        scene_id=str(getattr(scene, "scene_id", "") or ""),
        narration=str(_value(script_scene, "narration") or getattr(scene, "meaning", "") or ""),
        on_screen_text=str(_value(script_scene, "on_screen_text") or ""),
        keywords=tuple(_texts(_value(script_scene, "keywords"))),
        claims=tuple(scene_claim_texts(scene, list(claims))),
        must_include=tuple(_unique_texts(required)),
        must_avoid=tuple(_unique_texts(avoided)),
        shot_type=str(getattr(scene, "shot_type", "") or ""),
    )


def build_prompt(evidence: SceneBriefEvidence) -> str:
    """The instruction a model would receive. Pure string building, no I/O."""
    lines = [
        "Ты определяешь, что должно быть в кадре одной сцены видео.",
        "Опиши смысл сцены, а не переводи отдельные слова: назови то, что зритель"
        " должен увидеть.",
        f"Все значения — на языке провайдера ({PROVIDER_LANGUAGE}), короткими фразами.",
        "Не выдумывай сущность, место и факты, которых нет в материале ниже."
        " Если материал не говорит, что показывать, верни пустой subject.",
        "Ответ — строго JSON по схеме, без каких-либо других ключей:",
        json.dumps(RESPONSE_CONTRACT, ensure_ascii=False, indent=2),
        "",
        f"Текст сцены:\n{evidence.narration}",
    ]
    if evidence.on_screen_text:
        lines.append(f"Текст на экране: {evidence.on_screen_text}")
    if evidence.keywords:
        lines.append("Подготовленные ключевые слова: " + ", ".join(evidence.keywords))
    if evidence.claims:
        lines.append("Проверенные утверждения:\n" + "\n".join(f"- {text}" for text in evidence.claims))
    if evidence.must_include:
        lines.append("Обязательно присутствует в кадре: " + ", ".join(evidence.must_include))
    if evidence.must_avoid:
        lines.append("Показывать запрещено: " + ", ".join(evidence.must_avoid))
    if evidence.shot_type:
        lines.append(f"Планируемый тип кадра: {evidence.shot_type}")
    return "\n".join(lines).strip()


def parse_response(raw: Any, *, evidence: SceneBriefEvidence) -> VisualBrief:
    """Turn a model answer into a ``VisualBrief``, or refuse it.

    Refusing is the normal outcome for anything doubtful. The alternative - repairing a
    half-valid answer - would produce a brief the script cannot account for, and a brief
    is exactly the thing every downstream stage trusts without re-deriving.

    An answer with no subject is *not* an error: it is the model saying the evidence
    does not state what to show. That returns an empty brief, which is the same
    fail-closed state as having no adapter at all. A place or an action without a
    subject is not promoted to a brief either - "somewhere outdoors" is how a scene
    turns into generic footage.
    """
    data = _decode(raw)
    unknown = sorted(set(data) - RESPONSE_FIELDS)
    if unknown:
        raise SemanticBriefResponseError(
            f"Ответ модели содержит неизвестные поля: {', '.join(unknown)}.", planner=ADAPTER_ID
        )

    subject = _field(data, "subject")
    action = _field(data, "action")
    place = _field(data, "place")
    context = _context(data)
    shot_type = _field(data, "shot_type", provider_language=False)

    if not subject:
        return VisualBrief()
    if not _states_something_filmable(subject):
        raise SemanticBriefResponseError(
            "Предмет сцены состоит только из производственной лексики: "
            f"{subject!r} не называет, что в кадре.",
            planner=ADAPTER_ID,
        )
    if shot_type and shot_type not in SHOT_TYPES:
        raise SemanticBriefResponseError(
            f"Неизвестный тип кадра {shot_type!r} в ответе модели.", planner=ADAPTER_ID
        )
    stated = " ".join([subject, action, place, *context])
    if mentions_avoided(stated, evidence.must_avoid):
        raise SemanticBriefResponseError(
            "Ответ модели просит показать то, что сцена запретила.", planner=ADAPTER_ID
        )

    return VisualBrief(
        subject=subject,
        action=action,
        place=place,
        context=context,
        shot_type=shot_type,
    )


class ModelSemanticBriefAdapter:
    """A wired *and* approved model, asked what one scene should show.

    Not registered as a planner: the deterministic planner still plans, and this only
    supplies the meaning that the script could not state in the provider's language.
    Making it a planner id would make the two mutually exclusive, which is the opposite
    of what the capability is for.
    """

    adapter_id = ADAPTER_ID

    def __init__(
        self,
        completion_fn: SemanticBriefCompletionFn | None = None,
        *,
        approved: bool = False,
        model_id: str = "",
    ) -> None:
        self.completion_fn = completion_fn
        self.approved = approved
        self.model_id = model_id

    def is_available(self) -> bool:
        """Wired to a model *and* allowed to spend what calling it costs."""
        return self.completion_fn is not None and self.approved

    def brief_for(self, evidence: SceneBriefEvidence) -> VisualBrief:
        """What this scene should show, or a ``VisualPlannerError`` explaining why not.

        Only the expected failures become that error. Anything else the injected callable
        raises is a defect in the caller's own integration and is not disguised as a
        model that could not answer - see the module docstring.
        """
        if self.completion_fn is None:
            raise SemanticBriefUnavailableError(
                "Смысловой адаптер брифа не подключён: вызов модели не передан.",
                planner=ADAPTER_ID,
            )
        if not self.approved:
            raise SemanticBriefUnavailableError(
                "Смысловой бриф моделью требует явного подтверждения.", planner=ADAPTER_ID
            )
        if evidence.is_empty:
            raise SemanticBriefUnavailableError(
                f"Сцена {evidence.scene_id or '?'} не содержит материала для разбора.",
                planner=ADAPTER_ID,
            )
        prompt = build_prompt(evidence)
        options = {
            "model_id": self.model_id,
            "language": PROVIDER_LANGUAGE,
            "scene_id": evidence.scene_id,
        }
        try:
            raw = self.completion_fn(prompt, options)
        except VisualPlannerError:
            # A backend built on this package's own error contract has already said which
            # kind of failure this is - unavailable, refused, retryable. Re-raising it
            # unchanged keeps that answer instead of flattening every outcome into one.
            raise
        except OSError as exc:
            # The stdlib family that means "the outside world did not answer" - a dropped
            # connection, a refused socket, ``TimeoutError``. This is the expected way a
            # model call fails, and the pipeline's answer is that the scene has no model
            # brief.
            raise SemanticBriefUnavailableError(
                f"Вызов модели для сцены {evidence.scene_id or '?'} не выполнен: {exc}",
                planner=ADAPTER_ID,
                retryable=True,
            ) from exc
        return parse_response(raw, evidence=evidence)


def apply_semantic_brief(scene: Any, brief: VisualBrief) -> Any:
    """Overlay a brief a *model* stated: meaning only, never authority.

    ``brief.apply_brief`` implements the **author's** authority, where an unstated field
    is itself an answer: an author who rewrote the subject has also answered what the
    scene must contain, so ``must_include`` is replaced by what they listed and a stem
    the planner guessed at does not survive next to a subject the author rewrote.

    A model is never asked that question - ``RESPONSE_CONTRACT`` has no constraint field,
    because ``must_include`` is a hard requirement a candidate is refused for missing and
    ``must_avoid`` is a rights- and meaning-level limit. Its silence is therefore not an
    answer, and applying the author's rule to it let a model that merely named a subject
    delete a requirement it was never offered. The constraints are restored rather than
    the mapping duplicated, so there stays exactly one place that knows which brief field
    lands on which scene field.
    """
    required = list(getattr(scene, "must_include", None) or [])
    avoided = list(getattr(scene, "must_avoid", None) or [])
    apply_brief(scene, brief)
    scene.must_include = required
    scene.must_avoid = avoided
    return scene


def _decode(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str):
        raise SemanticBriefResponseError(
            f"Ответ модели имеет неподдерживаемый тип {type(raw).__name__}.", planner=ADAPTER_ID
        )
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text.split("\n", 1)[1] if "\n" in text else text
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SemanticBriefResponseError(
            f"Ответ модели не является корректным JSON: {exc}", planner=ADAPTER_ID
        ) from exc
    if not isinstance(data, dict):
        raise SemanticBriefResponseError(
            "Ответ модели не является объектом.", planner=ADAPTER_ID
        )
    return data


def _field(data: dict[str, Any], key: str, *, provider_language: bool = True) -> str:
    value = data.get(key, "")
    if value is None:
        return ""
    if not isinstance(value, str):
        raise SemanticBriefResponseError(
            f"Поле {key!r} ответа модели должно быть строкой.", planner=ADAPTER_ID
        )
    text = " ".join(value.split())
    if not text:
        return ""
    if len(text.split()) > MAX_FIELD_TERMS:
        raise SemanticBriefResponseError(
            f"Поле {key!r} ответа модели длиннее {MAX_FIELD_TERMS} слов.", planner=ADAPTER_ID
        )
    if provider_language and not provider_language_text(text):
        raise SemanticBriefResponseError(
            f"Поле {key!r} ответа модели не на языке провайдера: {text!r}.", planner=ADAPTER_ID
        )
    return text


def _context(data: dict[str, Any]) -> list[str]:
    value = data.get("context") or []
    if isinstance(value, str) or not isinstance(value, (list, tuple)):
        raise SemanticBriefResponseError(
            "Поле 'context' ответа модели должно быть списком строк.", planner=ADAPTER_ID
        )
    if len(value) > MAX_CONTEXT_ITEMS:
        raise SemanticBriefResponseError(
            f"Поле 'context' ответа модели длиннее {MAX_CONTEXT_ITEMS} элементов.",
            planner=ADAPTER_ID,
        )
    items = [_field({"context": item}, "context") for item in value]
    return [item for item in items if item]


def _states_something_filmable(subject: str) -> bool:
    """True when the subject names a thing rather than a production category.

    ``NON_FACTUAL_QUERY_TERMS`` already lists the words that describe how material was
    made instead of what is in it; a subject built only from those is the "generic
    nature footage" answer, which is a plausible-looking substitute for not knowing.
    """
    for word in subject.split():
        key = word.strip(".,;:!?'\"()-").casefold()
        if key and key not in STOPWORDS and key not in NON_FACTUAL_QUERY_TERMS:
            return True
    return False


def _unique_texts(values: Iterable[Any]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        text = " ".join(str(value).split())
        key = text.casefold()
        if key and key not in seen:
            seen.add(key)
            ordered.append(text)
    return ordered


def _texts(value: Any) -> list[str]:
    if not isinstance(value, (list, tuple, set)):
        return []
    return [" ".join(str(item).split()) for item in value if str(item).strip()]


def _value(source: Any, key: str) -> Any:
    if source is None:
        return None
    return source.get(key) if isinstance(source, dict) else getattr(source, key, None)


__all__ = [
    "ADAPTER_ID",
    "MAX_CONTEXT_ITEMS",
    "MAX_FIELD_TERMS",
    "RESPONSE_CONTRACT",
    "RESPONSE_FIELDS",
    "ModelSemanticBriefAdapter",
    "SceneBriefEvidence",
    "SemanticBriefCompletionFn",
    "SemanticBriefResponseError",
    "SemanticBriefUnavailableError",
    "apply_semantic_brief",
    "build_prompt",
    "evidence_for_scene",
    "parse_response",
]
