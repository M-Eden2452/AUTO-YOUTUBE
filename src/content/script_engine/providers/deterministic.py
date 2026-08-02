"""The default provider: a real script, built offline from the source material.

What it does differently from ``legacy_template``
-------------------------------------------------
Every sentence a viewer hears comes from the source (the article, the research
claims, the text the user pasted). The provider decides *which* sentences, in
what order, how many scenes they make, and how long each one is - it does not
supply the sentences itself.

- **Scene count follows the material and the duration budget**, not a constant.
- **Scene length follows the text**: ~14.9 characters per second, the rate measured
  on the confirmed live narration. Short thought - short scene.
- **Hook and payoff are chosen**, by ranking the source's own sentences for
  opening/closing qualities, instead of being written for it.
- Nothing is invented: no claims, no numbers, no sources.

No network, no model call, no randomness - the same input always yields the same
script, which is what makes it usable as the test and offline path.

Thin input
----------
A topic with no article behind it contains no material to write from. Rather than
padding it with filler, the provider hands over to ``legacy_template`` and says so
in ``warnings`` and ``metadata``. Disable with
``provider_options={"allow_legacy_fallback": False}``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..contract import BaseScriptProvider, ScriptProviderCapabilities, ScriptProviderInputError
from ..models import (
    SCENE_ROLE_CTA,
    SCENE_ROLE_DEVELOPMENT,
    SCENE_ROLE_HOOK,
    SCENE_ROLE_PAYOFF,
    SOURCE_KINDS,
    SOURCE_TOPIC,
    ScriptConstraints,
    ScriptRequest,
    ScriptResult,
    ScriptScene,
)
from ..text_analysis import (
    estimate_duration_sec,
    first_words,
    hook_score,
    is_uncertain,
    keywords,
    payoff_score,
    sentences,
    shorten,
    similarity,
)
from .legacy_template import LegacyTemplateScriptProvider

PROVIDER_ID = "deterministic_local"

# A fragment shorter than this is not a thought; it gets merged into its neighbour.
MIN_UNIT_CHARS = 25
# Two source sentences this alike are the same statement; the second is dropped.
UNIT_SIMILARITY_THRESHOLD = 0.8
# Below either of these the input is too thin to write from - see "Thin input".
MIN_UNITS_FOR_REAL_SCRIPT = 2
THIN_INPUT_DURATION_RATIO = 0.35
THIN_INPUT_DURATION_FLOOR_SEC = 12.0

_DEFAULT_CTA = {
    "ru": "Подпишитесь, если хотите больше таких историй.",
    "en": "Subscribe if you want more stories like this.",
}


@dataclass
class _Unit:
    """One candidate thought, with a record of where it came from."""

    text: str
    ref: str
    claim_id: str = ""
    uncertain: bool = False
    extras: list[str] = field(default_factory=list)

    @property
    def refs(self) -> list[str]:
        return [self.ref, *self.extras]


class DeterministicScriptProvider(BaseScriptProvider):
    capabilities_spec = ScriptProviderCapabilities(
        provider_id=PROVIDER_ID,
        display_name="Локальный смысловой сценарий",
        description=(
            "Строит сценарий из самого исходного текста: выбирает крючок и развязку, "
            "делит материал на законченные мысли, считает длительность по объёму речи. "
            "Работает офлайн и бесплатно, результат воспроизводим."
        ),
        supported_source_kinds=SOURCE_KINDS,
        requires_network=False,
        requires_paid_api=False,
        deterministic=True,
        implementation_status="targeted_tested",
    )

    def generate(self, request: ScriptRequest) -> ScriptResult:
        limits = request.constraints
        units = _collect_units(request)
        warnings: list[str] = []
        metadata: dict[str, Any] = {
            "source_unit_count": len(units),
            "speech_chars_per_sec": limits.speech_chars_per_sec,
        }

        if _is_thin(units, limits):
            return self._fallback(request, units, metadata)

        hook_unit, payoff_unit, body_units = _pick_structure(units)
        scenes = _assemble(
            request,
            hook_unit=hook_unit,
            payoff_unit=payoff_unit,
            body_units=body_units,
            warnings=warnings,
        )
        if not scenes:
            raise ScriptProviderInputError(
                "Из этого текста не удалось собрать ни одной сцены.", provider=PROVIDER_ID
            )

        title = request.title.strip() or request.topic.strip() or shorten(scenes[0].narration, 90)
        description = _description(request, scenes)
        result = ScriptResult(
            scenes=scenes,
            title=title,
            hook=scenes[0].narration,
            description=description,
            language=request.language,
            source_kind=request.source_kind,
            provider_id=PROVIDER_ID,
            provider_version="1.0",
            target_duration_sec=request.target_duration_sec,
            source_claim_ids=[unit.claim_id for unit in units if unit.claim_id],
            warnings=warnings,
            metadata={**metadata, "used_scene_count": len(scenes)},
        ).renumber()
        return result

    def _fallback(self, request: ScriptRequest, units: list[_Unit], metadata: dict[str, Any]) -> ScriptResult:
        """Not enough source material: reproduce the previous behaviour, loudly."""
        if not request.provider_options.get("allow_legacy_fallback", True):
            raise ScriptProviderInputError(
                "Insufficient source material for a factual script: provide an article URL "
                "or source text, or explicitly use draft/template mode.",
                provider=PROVIDER_ID,
                code="insufficient_source_material",
            )
        result = LegacyTemplateScriptProvider().generate(request)
        result.warnings.append(
            "insufficient_source_material: исходного текста не хватило на осмысленный сценарий, "
            "использован прежний шаблонный движок"
        )
        result.metadata.update(
            {
                **metadata,
                "requested_provider": PROVIDER_ID,
                "fallback_provider": result.provider_id,
                "fallback_reason": "insufficient_source_material",
            }
        )
        return result


# --- source material ---------------------------------------------------------


def _collect_units(request: ScriptRequest) -> list[_Unit]:
    """Turn the request's inputs into de-duplicated candidate thoughts.

    Research claims come first because they carry ids and a safety flag; the
    article's remaining sentences top them up, since the research stage only ever
    records the first eight.
    """
    units: list[_Unit] = []
    for claim in request.claims:
        if not claim.get("safe_for_script", True):
            continue
        text = str(claim.get("text") or "").strip()
        if not text:
            continue
        units.append(
            _Unit(
                text=text,
                ref=str(claim.get("claim_id") or f"claim_{len(units) + 1:03d}"),
                claim_id=str(claim.get("claim_id") or ""),
                uncertain=str(claim.get("claim_type") or "") in {"hypothesis", "interpretation", "uncertain"}
                or is_uncertain(text),
            )
        )

    for index, sentence in enumerate(sentences(request.raw_text), start=1):
        units.append(_Unit(text=sentence, ref=f"sentence_{index:03d}", uncertain=is_uncertain(sentence)))

    if not units and request.summary.strip():
        units.append(_Unit(text=request.summary.strip(), ref="summary"))

    return _merge_short(_dedupe(units))


def _dedupe(units: list[_Unit]) -> list[_Unit]:
    kept: list[_Unit] = []
    for unit in units:
        duplicate_of = next(
            (existing for existing in kept if similarity(existing.text, unit.text) >= UNIT_SIMILARITY_THRESHOLD),
            None,
        )
        if duplicate_of is not None:
            # Keep the provenance of the copy - the same statement can arrive as
            # both a claim and an article sentence.
            if unit.ref not in duplicate_of.refs:
                duplicate_of.extras.append(unit.ref)
            if unit.claim_id and not duplicate_of.claim_id:
                duplicate_of.claim_id = unit.claim_id
            continue
        kept.append(unit)
    return kept


def _merge_short(units: list[_Unit]) -> list[_Unit]:
    """Glue fragments into whole thoughts, so no scene is a half-sentence."""
    merged: list[_Unit] = []
    for unit in units:
        if merged and len(unit.text) < MIN_UNIT_CHARS:
            previous = merged[-1]
            previous.text = f"{previous.text.rstrip()} {unit.text.lstrip()}".strip()
            previous.extras.extend(unit.refs)
            continue
        merged.append(unit)
    if len(merged) >= 2 and len(merged[0].text) < MIN_UNIT_CHARS:
        first, second = merged[0], merged[1]
        second.text = f"{first.text.rstrip()} {second.text.lstrip()}".strip()
        second.extras = [*first.refs, *second.extras]
        second.claim_id = second.claim_id or first.claim_id
        merged = merged[1:]
    return merged


def _is_thin(units: list[_Unit], limits: ScriptConstraints) -> bool:
    if len(units) < MIN_UNITS_FOR_REAL_SCRIPT:
        return True
    available = sum(estimate_duration_sec(unit.text, chars_per_sec=limits.speech_chars_per_sec) for unit in units)
    floor = max(THIN_INPUT_DURATION_FLOOR_SEC, limits.target_duration_sec * THIN_INPUT_DURATION_RATIO)
    return available < floor


# --- structure ---------------------------------------------------------------


def _pick_structure(units: list[_Unit]) -> tuple[_Unit, _Unit, list[_Unit]]:
    """Choose which of the source's own sentences open and close the video."""
    hook_index = max(range(len(units)), key=lambda i: (hook_score(units[i].text), -i))
    remaining = [index for index in range(len(units)) if index != hook_index]
    payoff_index = max(remaining, key=lambda i: (payoff_score(units[i].text), i))
    body = [units[index] for index in remaining if index != payoff_index]
    return units[hook_index], units[payoff_index], body


def _assemble(
    request: ScriptRequest,
    *,
    hook_unit: _Unit,
    payoff_unit: _Unit,
    body_units: list[_Unit],
    warnings: list[str],
) -> list[ScriptScene]:
    limits = request.constraints
    cta_text = ""
    if request.include_cta:
        cta_text = request.cta_text.strip() or _DEFAULT_CTA.get(request.language, _DEFAULT_CTA["ru"])
        if not request.cta_text.strip():
            warnings.append("cta_default_used: призыв к действию взят по умолчанию, свой текст не задан")

    planned: list[tuple[str, _Unit]] = [(SCENE_ROLE_HOOK, hook_unit)]
    tail: list[tuple[str, _Unit]] = [(SCENE_ROLE_PAYOFF, payoff_unit)]
    if cta_text:
        tail.append((SCENE_ROLE_CTA, _Unit(text=cta_text, ref="cta")))

    def duration_of(text: str) -> float:
        return limits.clamp_duration(estimate_duration_sec(text, chars_per_sec=limits.speech_chars_per_sec))

    def total_of(items: list[tuple[str, _Unit]]) -> float:
        durations = [duration_of(unit.text) for _, unit in items]
        return sum(durations) + limits.pause_between_scenes_sec * max(0, len(durations) - 1)

    body_pool: list[_Unit] = []
    for unit in body_units:
        body_pool.extend(_split_long(unit, limits))

    for unit in body_pool:
        candidate = [*planned, (SCENE_ROLE_DEVELOPMENT, unit), *tail]
        if len(candidate) > limits.max_scene_count:
            break
        if total_of(candidate) > limits.target_duration_sec and len(candidate) > limits.min_scene_count:
            break
        planned.append((SCENE_ROLE_DEVELOPMENT, unit))

    planned.extend(tail)
    if total_of(planned) < limits.target_duration_sec * 0.6:
        warnings.append(
            "short_script: исходного материала хватило только на "
            f"{total_of(planned):.0f} с из запрошенных {limits.target_duration_sec:.0f} с"
        )

    scenes: list[ScriptScene] = []
    for index, (role, unit) in enumerate(planned, start=1):
        text = unit.text.strip()
        scenes.append(
            ScriptScene(
                scene_id=f"scene_{index:03d}",
                index=index,
                role=role,
                narration=text,
                duration_sec=round(duration_of(text), 2),
                on_screen_text=first_words(text),
                visual_intent=shorten(text, 160),
                emotion=_emotion(role, unit),
                keywords=keywords(text),
                claim_ids=[unit.claim_id] if unit.claim_id else [],
                source_refs=unit.refs,
            )
        )
    return scenes


def _split_long(unit: _Unit, limits: ScriptConstraints) -> list[_Unit]:
    """Break a thought that would overrun the per-scene limit, on sentence borders."""
    max_chars = limits.max_scene_duration_sec * limits.speech_chars_per_sec
    if len(unit.text) <= max_chars:
        return [unit]
    parts = sentences(unit.text) or [unit.text]
    if len(parts) == 1:
        parts = _split_on_punctuation(unit.text, max_chars)
    chunks: list[_Unit] = []
    buffer = ""
    for part in parts:
        candidate = f"{buffer} {part}".strip() if buffer else part
        if buffer and len(candidate) > max_chars:
            chunks.append(_Unit(text=buffer, ref=unit.ref, claim_id=unit.claim_id, uncertain=unit.uncertain))
            buffer = part
        else:
            buffer = candidate
    if buffer:
        chunks.append(_Unit(text=buffer, ref=unit.ref, claim_id=unit.claim_id, uncertain=unit.uncertain))
    return chunks or [unit]


def _split_on_punctuation(text: str, max_chars: float) -> list[str]:
    """Last resort for one very long sentence: cut at the nearest clause break."""
    parts: list[str] = []
    remainder = text.strip()
    while len(remainder) > max_chars:
        window = remainder[: int(max_chars)]
        cut = max(window.rfind(", "), window.rfind("; "), window.rfind(" — "), window.rfind(" - "))
        if cut <= 0:
            cut = window.rfind(" ")
        if cut <= 0:
            break
        parts.append(remainder[:cut].strip(" ,;-—"))
        remainder = remainder[cut:].strip(" ,;-—")
    if remainder:
        parts.append(remainder)
    return parts


def _emotion(role: str, unit: _Unit) -> str:
    """A tone label derived from the scene's own content, not from a fixed table."""
    if role == SCENE_ROLE_HOOK:
        return "intrigue"
    if role == SCENE_ROLE_CTA:
        return "invitation"
    if role == SCENE_ROLE_PAYOFF:
        return "insight"
    if unit.uncertain:
        return "caution"
    if any(character.isdigit() for character in unit.text):
        return "detail"
    return "explanation"


def _description(request: ScriptRequest, scenes: list[ScriptScene]) -> str:
    summary = request.summary.strip()
    if summary:
        return shorten(summary, 300)
    body = next((scene for scene in scenes if scene.role == SCENE_ROLE_DEVELOPMENT), None)
    if body is not None:
        return shorten(body.narration, 300)
    return shorten(scenes[0].narration, 300) if scenes else request.topic


def default_constraints(target_duration_sec: float, *, source_kind: str = SOURCE_TOPIC) -> ScriptConstraints:
    """Constraints for a vertical short of the given length."""
    return ScriptConstraints(target_duration_sec=float(target_duration_sec or 55.0))


__all__ = [
    "MIN_UNITS_FOR_REAL_SCRIPT",
    "PROVIDER_ID",
    "THIN_INPUT_DURATION_FLOOR_SEC",
    "THIN_INPUT_DURATION_RATIO",
    "DeterministicScriptProvider",
    "default_constraints",
]
