"""The user already wrote it: keep their words, only give them structure.

Before this existed, a pasted script went in as ``input_text``, was cut into
sentences by the research stage and then re-wrapped in the template generator's
own phrases - the user's script was used as raw material *about* itself. Here it
is authoritative: the provider splits it into scenes, times them and labels the
roles, and does not add, remove or rewrite a single sentence.

Scene boundaries, in order of preference:
1. blank lines - the way people actually separate scenes when writing one;
2. explicit markers (``Сцена 3:``, ``SCENE 3:``, ``[hook]``), which are stripped
   from the spoken text but honoured as boundaries;
3. sentences, grouped up to the per-scene duration limit.
"""

from __future__ import annotations

import re

from ..contract import BaseScriptProvider, ScriptProviderCapabilities, ScriptProviderInputError
from ..models import (
    SCENE_ROLE_CTA,
    SCENE_ROLE_DEVELOPMENT,
    SCENE_ROLE_HOOK,
    SCENE_ROLE_PAYOFF,
    SOURCE_NARRATION_TEXT,
    SOURCE_USER_SCRIPT,
    ScriptConstraints,
    ScriptRequest,
    ScriptResult,
    ScriptScene,
)
from ..text_analysis import estimate_duration_sec, first_words, keywords, sentences, shorten

PROVIDER_ID = "user_supplied"

_SCENE_MARKER_RE = re.compile(
    r"^\s*(?:\[(?P<role>[a-zа-я_]+)\]|"
    r"(?:сцена|scene|кадр|shot)\s*[№#]?\s*\d+\s*[.:)-]?|"
    r"\d+\s*[.)]\s)\s*",
    re.IGNORECASE,
)
_ROLE_ALIASES = {
    "hook": SCENE_ROLE_HOOK,
    "крючок": SCENE_ROLE_HOOK,
    "development": SCENE_ROLE_DEVELOPMENT,
    "развитие": SCENE_ROLE_DEVELOPMENT,
    "payoff": SCENE_ROLE_PAYOFF,
    "развязка": SCENE_ROLE_PAYOFF,
    "reward": SCENE_ROLE_PAYOFF,
    "cta": SCENE_ROLE_CTA,
    "призыв": SCENE_ROLE_CTA,
}


class UserSuppliedScriptProvider(BaseScriptProvider):
    capabilities_spec = ScriptProviderCapabilities(
        provider_id=PROVIDER_ID,
        display_name="Готовый сценарий пользователя",
        description=(
            "Берёт написанный вами сценарий или текст озвучки как есть: делит на сцены, "
            "считает длительность, расставляет роли. Ни одно слово не переписывается."
        ),
        supported_source_kinds=(SOURCE_USER_SCRIPT, SOURCE_NARRATION_TEXT),
        requires_network=False,
        requires_paid_api=False,
        deterministic=True,
        implementation_status="targeted_tested",
    )

    def generate(self, request: ScriptRequest) -> ScriptResult:
        text = (request.raw_text or "").strip()
        if not text:
            raise ScriptProviderInputError(
                "Готовый сценарий пуст: передайте текст в raw_text.", provider=PROVIDER_ID
            )
        limits = request.constraints
        blocks = _split_blocks(text, limits)
        if not blocks:
            raise ScriptProviderInputError(
                "В переданном тексте не нашлось ни одной произносимой строки.", provider=PROVIDER_ID
            )

        roles = _assign_roles([role for role, _ in blocks])
        warnings: list[str] = []
        if len(blocks) > limits.max_scene_count:
            warnings.append(
                f"too_many_scenes: в тексте {len(blocks)} сцен при пределе {limits.max_scene_count}; "
                "лишние не отброшены, но проверьте длительность"
            )

        scenes: list[ScriptScene] = []
        for index, ((_, block), role) in enumerate(zip(blocks, roles, strict=True), start=1):
            duration = limits.clamp_duration(
                estimate_duration_sec(block, chars_per_sec=limits.speech_chars_per_sec)
            )
            scenes.append(
                ScriptScene(
                    scene_id=f"scene_{index:03d}",
                    index=index,
                    role=role,
                    narration=block,
                    duration_sec=round(duration, 2),
                    on_screen_text=first_words(block),
                    visual_intent=shorten(block, 160),
                    emotion=_emotion(role),
                    keywords=keywords(block),
                    source_refs=[f"user_block_{index:03d}"],
                    # The author's own "what to show" for this block, if they wrote one.
                    # Attached by position, which is meaningful here precisely because
                    # this provider never reorders or merges the author's scenes.
                    visual_brief=request.brief_for(index, f"scene_{index:03d}"),
                )
            )

        title = request.title.strip() or request.topic.strip() or shorten(scenes[0].narration, 90)
        result = ScriptResult(
            scenes=scenes,
            title=title,
            hook=scenes[0].narration,
            description=shorten(request.summary.strip() or scenes[0].narration, 300),
            language=request.language,
            source_kind=request.source_kind,
            provider_id=PROVIDER_ID,
            provider_version="1.0",
            target_duration_sec=request.target_duration_sec,
            warnings=warnings,
            metadata={
                "user_text_chars": len(text),
                "scene_split": "blank_lines" if "\n\n" in text else "sentences",
            },
        ).renumber()
        return result


def _split_blocks(text: str, limits: ScriptConstraints) -> list[tuple[str, str]]:
    """Return [(declared_role_or_empty, spoken_text)] in the author's own order."""
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    if len(paragraphs) < 2:
        paragraphs = [line.strip() for line in text.splitlines() if line.strip()]
    if len(paragraphs) < 2:
        paragraphs = [text.strip()]

    blocks: list[tuple[str, str]] = []
    for paragraph in paragraphs:
        role, body = _strip_marker(paragraph)
        body = " ".join(body.split())
        if not body:
            continue
        for chunk in _fit_to_limit(body, limits):
            blocks.append((role, chunk))
            # A declared role belongs to the first chunk only; the rest are its
            # continuation and must not claim to be a second hook.
            role = ""
    return blocks


def _strip_marker(paragraph: str) -> tuple[str, str]:
    match = _SCENE_MARKER_RE.match(paragraph)
    if not match:
        return "", paragraph
    declared = (match.group("role") or "").lower()
    return _ROLE_ALIASES.get(declared, ""), paragraph[match.end() :]


def _fit_to_limit(text: str, limits: ScriptConstraints) -> list[str]:
    """Group whole sentences so no scene exceeds the per-scene duration limit."""
    max_chars = limits.max_scene_duration_sec * limits.speech_chars_per_sec
    if len(text) <= max_chars:
        return [text]
    parts = sentences(text) or [text]
    chunks: list[str] = []
    buffer = ""
    for part in parts:
        candidate = f"{buffer} {part}".strip() if buffer else part
        if buffer and len(candidate) > max_chars:
            chunks.append(buffer)
            buffer = part
        else:
            buffer = candidate
    if buffer:
        chunks.append(buffer)
    return chunks or [text]


def _assign_roles(declared: list[str]) -> list[str]:
    """Honour roles the author declared; infer the rest by position."""
    count = len(declared)
    roles = list(declared)
    if count == 1:
        return [roles[0] or SCENE_ROLE_HOOK]
    if not roles[0]:
        roles[0] = SCENE_ROLE_HOOK
    if not roles[-1]:
        # A declared CTA at the end still needs a payoff before it, but we never
        # relabel the author's own text - the validator reports the missing payoff.
        roles[-1] = SCENE_ROLE_PAYOFF
    for index in range(1, count - 1):
        if not roles[index]:
            roles[index] = SCENE_ROLE_DEVELOPMENT
    if roles[-1] == SCENE_ROLE_CTA and SCENE_ROLE_PAYOFF not in roles and count >= 3:
        roles[-2] = SCENE_ROLE_PAYOFF
    return roles


def _emotion(role: str) -> str:
    return {
        SCENE_ROLE_HOOK: "intrigue",
        SCENE_ROLE_DEVELOPMENT: "explanation",
        SCENE_ROLE_PAYOFF: "insight",
        SCENE_ROLE_CTA: "invitation",
    }.get(role, "explanation")


__all__ = ["PROVIDER_ID", "UserSuppliedScriptProvider"]
