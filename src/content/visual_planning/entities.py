"""Pulling the things a scene is about out of the scene's own words.

Deliberately modest about what it is. There is no morphological analyser, no
gazetteer and no LLM in this layer, so this module does four things it can defend
and refuses the rest:

1. **Same word across cases.** Russian inflects endings, so ``ворона``/``вороны``/
   ``ворону`` are recognised as one entity by a crude common-prefix stem. That stem
   is an internal key only - it is never shown to a provider and never spoken.
2. **Salience by repetition.** A thing named in several scenes, in the topic, or in
   the title is what the video is about. This is counting, not understanding.
3. **Verb-like and proper-noun-like tokens** by suffix and by capitalisation after a
   locative preposition. Both are real signals in Russian and both are recorded with
   the surface wording, never a synonym.
4. **Years and centuries** by pattern.

Every value returned is a substring of the input. Nothing is translated, replaced
with a general category, or invented - that rule is what keeps a plan honest about
which animal, country or technology the script actually named.

Word splitting, stopwords and set similarity are reused from
``src.content.script_engine.text_analysis`` rather than reimplemented.
"""

from __future__ import annotations

import re

from src.content.script_engine.text_analysis import STOPWORDS, words

from .models import VisualEntity

# Endings stripped to compare two inflections of the same word. Longest first, so
# "ами" wins over "и". Crude on purpose: over-stripping merges two related words,
# which costs a little precision in grouping and nothing in output wording.
_ENDINGS = (
    "ированием", "ированию", "ированием", "ования", "ованию",
    "ами", "ями", "ому", "ему", "ого", "его", "ыми", "ими", "ах", "ях", "ов", "ев", "ей",
    "ой", "ый", "ий", "ая", "яя", "ое", "ее", "ые", "ие", "ам", "ям", "ом", "ем", "ум",
    "ешь", "ете", "ет", "ут", "ют", "ат", "ят", "ит", "им", "ыми",
    "а", "я", "о", "е", "у", "ю", "ы", "и", "ь", "й",
)

# Suffixes that make a Russian token look like a verb or a participle. Used only to
# label a token as an action; the token itself is kept as written.
_VERB_SUFFIXES = (
    "ться", "тся", "ались", "ились", "алась", "илась", "ывал", "ивал",
    "ает", "яет", "еет", "ует", "ают", "яют", "еют", "уют", "ит", "ят", "ат",
    "ал", "ял", "ел", "ил", "ала", "яла", "ела", "ила", "али", "яли", "ели", "или",
    "ющий", "ающий", "ящий", "вший", "нный", "тый", "мый",
)

# Prepositions that make the next capitalised word a place rather than an actor.
_LOCATIVE_PREPOSITIONS = {"в", "во", "на", "из", "под", "над", "у", "около", "вокруг", "близ", "при"}

# Words that pass the stopword filter (they are long enough and carry meaning in a
# sentence) but name nothing a camera can point at: relative pronouns, quantifiers,
# discourse connectives, bare time-words. Without this list they end up in search
# queries, where "который" or "больше" matches everything and ranks nothing.
_NON_VISUAL = {
    "который", "которая", "которое", "которые", "которых", "которым", "которой", "котором",
    "больше", "меньше", "много", "мало", "несколько", "самый", "самая", "самое", "самые",
    "никто", "ничто", "никого", "ничего", "кто-то", "что-то", "любой", "любого", "любому",
    "значит", "поэтому", "потому", "затем", "тогда", "теперь", "сейчас", "просто", "очень",
    "более", "менее", "каждый", "каждая", "каждое", "другой", "другая", "другие", "других",
    "такой", "такая", "такое", "такие", "этот", "эта", "это", "эти", "весь", "вся", "все",
    "год", "года", "году", "годы", "годов", "годами", "раз", "разы", "случай", "случае",
    "вопрос", "ответ", "пример", "образом", "может", "можно", "нужно", "должен", "должна",
    "стало", "стали", "стал", "стала", "будет", "были", "было", "есть", "почему", "зачем",
    "when", "which", "that", "there", "here", "very", "more", "less", "many", "much",
    "подряд", "никогда", "всегда", "снова", "сразу", "обычно", "именно", "точно",
    "полностью", "действительно", "например", "кстати", "конечно", "вообще",
    # Reporting/relationship verbs describe how a claim is framed, not a
    # filmable action that stock footage must literally verify.
    "связывают",
}

# A small disambiguation list for actor nouns that happen to end like Russian
# past-tense verbs. Keep them filmable as entities, but never turn them into an
# action requirement.
_NON_ACTION = {"исследователи"}

_YEAR_RE = re.compile(r"\b(\d{3,4})\s*(?:год|году|года|г\.)", re.IGNORECASE)
_CENTURY_RE = re.compile(r"\b([IVXLC]+|\d{1,2})\s*(?:век|века|веке)", re.IGNORECASE)
_DECADE_RE = re.compile(r"\b(\d{4})\s*-?\s*[хx]\b", re.IGNORECASE)
_TOKEN_RE = re.compile(r"[^\W\d_]+", re.UNICODE)

# Below this a token is a function word or a fragment, not a thing to film.
MIN_ENTITY_CHARS = 4
# A stem this short after stripping is not distinctive enough to group on.
MIN_STEM_CHARS = 3


def stem(word: str) -> str:
    """Crude common-prefix form of ``word``. An internal grouping key, not language."""
    lowered = (word or "").strip().lower()
    if len(lowered) <= MIN_STEM_CHARS:
        return lowered
    for ending in _ENDINGS:
        if lowered.endswith(ending) and len(lowered) - len(ending) >= MIN_STEM_CHARS:
            return lowered[: -len(ending)]
    return lowered


def looks_like_verb(token: str) -> bool:
    lowered = (token or "").lower()
    return len(lowered) > 4 and lowered.endswith(_VERB_SUFFIXES)


def is_latin(token: str) -> bool:
    """Already written in the Latin alphabet, so usable in a stock query as-is."""
    return bool(token) and all(character.isascii() for character in token)


def is_filmable(token: str) -> bool:
    """False for function words, quantifiers and bare time-words - see ``_NON_VISUAL``."""
    lowered = (token or "").lower()
    return (
        len(lowered) >= MIN_ENTITY_CHARS
        and lowered not in STOPWORDS
        and lowered not in _NON_VISUAL
    )


def content_tokens(text: str) -> list[str]:
    """Meaningful words of ``text`` in order of appearance, original wording kept."""
    return [token for token in _TOKEN_RE.findall(text or "") if is_filmable(token)]


def extract_period(text: str) -> str:
    """A year, decade or century named in the text, exactly as written. '' if none."""
    for pattern in (_YEAR_RE, _DECADE_RE, _CENTURY_RE):
        match = pattern.search(text or "")
        if match:
            return match.group(0).strip()
    return ""


def extract_places(text: str) -> list[str]:
    """Capitalised words introduced by a locative preposition, in order.

    "в Вашингтонском университете" -> ["Вашингтонском"]. A capitalised word without
    that preposition could equally be a person or an organisation, so it is not
    claimed as a place.
    """
    tokens = _TOKEN_RE.findall(text or "")
    places: list[str] = []
    for index, token in enumerate(tokens[1:], start=1):
        previous = tokens[index - 1].lower()
        if previous not in _LOCATIVE_PREPOSITIONS:
            continue
        if len(token) >= MIN_ENTITY_CHARS and token[:1].isupper():
            if token not in places:
                places.append(token)
    return places


def extract_actions(text: str) -> list[str]:
    """Verb-like tokens of ``text``, as written, lower-case ones first.

    The suffix test cannot tell a past-plural verb from a plural agent noun -
    ``ловили`` and ``исследователи`` both end in a listed suffix. Capitalisation
    breaks the tie in the common case: a Russian finite verb is not capitalised
    unless it opens the sentence, and a sentence usually opens with its subject.
    Lower-case candidates are therefore preferred, and capitalised ones are kept only
    when the scene offers nothing else.
    """
    lowercase: list[str] = []
    capitalised: list[str] = []
    for token in _TOKEN_RE.findall(text or ""):
        if (
            not (looks_like_verb(token) and is_filmable(token))
            or token.lower() in _NON_ACTION
        ):
            continue
        bucket = capitalised if token[:1].isupper() else lowercase
        if token not in bucket:
            bucket.append(token)
    return [*lowercase, *capitalised]


def collect_entities(
    *,
    scene_texts: dict[str, str],
    topic: str = "",
    title: str = "",
    claims: list[dict] | None = None,
) -> list[VisualEntity]:
    """Rank the things named across the whole script, most salient first.

    Salience counts: how many scenes name it, whether the topic or the title names
    it, and whether a research claim names it. All three are evidence that the thing
    is what the video is about rather than a passing word.
    """
    claims = claims or []
    topic_stems = {stem(token) for token in content_tokens(topic)}
    title_stems = {stem(token) for token in content_tokens(title)}
    claim_stems: dict[str, list[str]] = {}
    for claim in claims:
        claim_id = str(claim.get("claim_id") or "")
        for token in content_tokens(str(claim.get("text") or "")):
            claim_stems.setdefault(stem(token), []).append(claim_id)

    grouped: dict[str, VisualEntity] = {}
    for scene_id, text in scene_texts.items():
        for token in content_tokens(text):
            key = stem(token)
            if len(key) < MIN_STEM_CHARS or looks_like_verb(token):
                continue
            entity = grouped.get(key)
            if entity is None:
                entity = VisualEntity(surface=token, stem=key)
                grouped[key] = entity
            elif len(token) < len(entity.surface):
                # Prefer the shortest wording seen: closest to the dictionary form.
                entity.surface = token
            if scene_id not in entity.scene_ids:
                entity.scene_ids.append(scene_id)

    for key, entity in grouped.items():
        entity.salience = float(len(entity.scene_ids))
        if key in topic_stems:
            entity.salience += 3.0
            entity.kind = "topic_entity"
        if key in title_stems:
            entity.salience += 1.5
        refs = claim_stems.get(key) or []
        if refs:
            entity.salience += 1.0
            entity.source_refs = sorted({ref for ref in refs if ref})
        if is_latin(entity.surface):
            # A Latin token needs no translation to reach a stock provider, which
            # makes it disproportionately useful as a search term.
            entity.salience += 0.5

    return sorted(grouped.values(), key=lambda item: (-item.salience, item.stem))


def entities_in(text: str, entities: list[VisualEntity]) -> list[VisualEntity]:
    """Those of ``entities`` whose stem appears in ``text``, most salient first."""
    present = {stem(token) for token in content_tokens(text)}
    return [entity for entity in entities if entity.stem in present]


__all__ = [
    "MIN_ENTITY_CHARS",
    "collect_entities",
    "content_tokens",
    "entities_in",
    "extract_actions",
    "extract_period",
    "extract_places",
    "is_filmable",
    "is_latin",
    "looks_like_verb",
    "stem",
]
