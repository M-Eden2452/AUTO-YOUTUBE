"""Offline text utilities the deterministic provider is built on.

Pure functions, no network, no model calls, no randomness: the same input always
produces the same script, which is what makes the provider usable in tests.

Sentence splitting reuses ``src.news.research_engine.split_sentences`` so the
engine and the research stage cannot disagree about where a sentence ends.
"""

from __future__ import annotations

import re
import unicodedata

from src.news.research_engine import split_sentences

# Function words carry no visual or topical meaning; dropped before keywording.
_STOPWORDS_RU = {
    "а", "без", "бы", "был", "была", "были", "было", "быть", "в", "вдруг", "ведь", "весь", "во",
    "вот", "все", "всего", "всех", "вы", "где", "да", "даже", "для", "до", "его", "ее", "ей",
    "если", "есть", "еще", "же", "за", "здесь", "и", "из", "или", "им", "их", "к", "как", "когда",
    "кто", "ли", "либо", "мне", "может", "мы", "на", "над", "надо", "наш", "не", "него", "нее",
    "нет", "ни", "них", "но", "ну", "о", "об", "он", "она", "они", "оно", "от", "очень", "по",
    "под", "после", "потом", "потому", "почти", "при", "про", "с", "свое", "себя", "сейчас",
    "со", "так", "также", "такой", "там", "те", "тем", "то", "того", "тоже", "той", "только",
    "том", "тот", "ту", "ты", "у", "уже", "хотя", "чего", "чем", "что", "чтобы", "чье", "чья",
    "эта", "эти", "это", "этой", "этом", "этот", "эту", "я",
}
_STOPWORDS_EN = {
    "a", "about", "after", "all", "also", "an", "and", "any", "are", "as", "at", "be",
    "been", "but", "by", "can", "could", "did", "do", "does", "for", "from", "had", "has",
    "have", "he", "her", "his", "how", "i", "if", "in", "into", "is", "it", "its", "may",
    "more", "most", "no", "not", "of", "on", "one", "only", "or", "other", "our", "out",
    "over", "she", "so", "some", "such", "than", "that", "the", "their", "them", "then",
    "there", "these", "they", "this", "to", "was", "we", "were", "what", "when", "which",
    "who", "will", "with", "would", "you", "your",
}

STOPWORDS = _STOPWORDS_RU | _STOPWORDS_EN

# Markers used to *rank* sentences, never to generate text. They decide which of
# the author's own sentences becomes the hook or the payoff.
_HOOK_MARKERS = (
    "почему", "как ", "что если", "зачем", "оказалось", "впервые", "неожидан", "загадк",
    "секрет", "удивительн", "why", "how ", "what if", "surprising", "unexpected",
)
_PAYOFF_MARKERS = (
    "поэтому", "в итоге", "в результате", "это значит", "означает", "вывод", "итог",
    "именно поэтому", "благодаря этому", "so that", "as a result", "this means",
    "therefore", "in the end",
)
_UNCERTAIN_MARKERS = (
    "возможно", "предполага", "гипотез", "может быть", "вероятно", "не исключено",
    "could", "may ", "might", "perhaps",
)

_WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)
_CYRILLIC_RE = re.compile(r"[а-яё]", re.IGNORECASE)
_LATIN_RE = re.compile(r"[a-z]", re.IGNORECASE)


def sentences(text: str) -> list[str]:
    """Sentences of ``text``, using the same splitter as the research stage."""
    if not text or not text.strip():
        return []
    return [sentence for sentence in split_sentences(text) if sentence]


def words(text: str) -> list[str]:
    return _WORD_RE.findall(text.lower())


def normalize_for_compare(text: str) -> str:
    """Casefolded, punctuation-free form used to detect repeated scenes."""
    folded = unicodedata.normalize("NFKC", text or "").casefold()
    return " ".join(_WORD_RE.findall(folded))


def similarity(left: str, right: str) -> float:
    """Jaccard overlap of word sets. 1.0 means "the same sentence twice"."""
    left_words = set(normalize_for_compare(left).split())
    right_words = set(normalize_for_compare(right).split())
    if not left_words or not right_words:
        return 0.0
    return len(left_words & right_words) / len(left_words | right_words)


def keywords(text: str, *, limit: int = 6) -> list[str]:
    """Content words in first-appearance order, longest-first among equals.

    Deliberately simple: this is a hint for the visual layer (Q2), not an attempt
    to do semantic extraction here.
    """
    seen: dict[str, int] = {}
    for position, word in enumerate(words(text)):
        if len(word) < 4 or word in STOPWORDS:
            continue
        seen.setdefault(word, position)
    ordered = sorted(seen.items(), key=lambda item: (item[1],))
    return [word for word, _ in ordered[:limit]]


def detect_language(text: str) -> str:
    """'ru' / 'en' / '' when there is not enough evidence.

    Only distinguishes the two alphabets the pipeline actually produces; anything
    else returns '' so the language check stays silent instead of guessing wrong.
    """
    cyrillic = len(_CYRILLIC_RE.findall(text or ""))
    latin = len(_LATIN_RE.findall(text or ""))
    total = cyrillic + latin
    if total < 12:
        return ""
    if cyrillic >= latin * 2:
        return "ru"
    if latin >= cyrillic * 2:
        return "en"
    return ""


def estimate_duration_sec(text: str, *, chars_per_sec: float) -> float:
    """Planned spoken length of ``text``.

    Characters, not words: on the one confirmed live narration the per-scene rate
    was 14.6-15.2 chars/s against 1.77-2.21 words/s, i.e. characters are ~4x more
    stable as a predictor.
    """
    rate = chars_per_sec if chars_per_sec > 0 else 14.9
    return len((text or "").strip()) / rate


def hook_score(sentence: str) -> float:
    """How well a sentence works as an opening line."""
    lowered = sentence.lower()
    score = 0.0
    if sentence.rstrip().endswith("?"):
        score += 2.0
    score += sum(1.0 for marker in _HOOK_MARKERS if marker in lowered)
    if re.search(r"\d", sentence):
        score += 0.5
    length = len(sentence)
    if 40 <= length <= 140:
        score += 1.0
    elif length > 220:
        score -= 1.0
    return score


def payoff_score(sentence: str) -> float:
    """How well a sentence works as a closing thought."""
    lowered = sentence.lower()
    score = sum(1.5 for marker in _PAYOFF_MARKERS if marker in lowered)
    if re.search(r"\d", sentence):
        score += 0.3
    length = len(sentence)
    if 50 <= length <= 180:
        score += 0.8
    elif length > 240:
        score -= 1.0
    return score


def is_uncertain(sentence: str) -> bool:
    lowered = sentence.lower()
    return any(marker in lowered for marker in _UNCERTAIN_MARKERS)


def first_words(text: str, count: int = 5) -> str:
    """Short on-screen label. Same rule the previous generator used.

    Kept deliberately unchanged: how on-screen text drives subtitles is stage Q3,
    and changing it here would silently alter every rendered subtitle.
    """
    parts = (text or "").replace(":", "").split()
    return " ".join(parts[:count])


def shorten(text: str, limit: int = 160) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0]
    return (cut or text[:limit]).rstrip(" ,;:-")


__all__ = [
    "STOPWORDS",
    "detect_language",
    "estimate_duration_sec",
    "first_words",
    "hook_score",
    "is_uncertain",
    "keywords",
    "normalize_for_compare",
    "payoff_score",
    "sentences",
    "shorten",
    "similarity",
    "words",
]
