"""Нарезка текста сцены на куски субтитров. Чистые функции, без сети и моделей.

Главное свойство, которое проверяется тестами и валидатором: **последовательность
слов сохраняется полностью**. Нарезка только расставляет границы - она не
переписывает, не сокращает, не переставляет и не выбрасывает ни одного слова.
Именно поэтому здесь не переиспользуется
``src.news.research_engine.split_sentences``: он отбрасывает фрагменты короче 9
символов (``len(part.strip()) > 8``), что для субтитров означало бы потерю текста.
Границы предложений считаются здесь заново, но по тем же знакам.

Морфологии нет намеренно: правила - пунктуация, длина и несколько защит от
очевидно плохих разрывов (одинокое слово, число без единицы измерения,
сокращение). Тяжёлые NLP-зависимости для этого не нужны.
"""

from __future__ import annotations

import re

from .models import SubtitlePolicy, SubtitleSegment

_TOKEN_RE = re.compile(r"\S+")

# Конец предложения. Двоеточие тоже считается сильной паузой: в закадровом тексте
# после него почти всегда идёт перечисление или расшифровка.
_SENTENCE_END = ".!?…:"
# Слабее предложения, но лучше, чем разрыв посреди фразы.
_CLAUSE_END = ",;—–-"

# Сокращения, после которых точка не заканчивает предложение. Список короткий и
# закрытый: он покрывает то, что реально встречается в закадровом тексте.
_ABBREVIATIONS = {
    "т", "тт", "др", "им", "св", "г", "гг", "в", "вв", "с", "стр", "рис", "табл",
    "напр", "см", "ср", "мл", "млн", "млрд", "тыс", "проц", "руб", "долл",
    "mr", "mrs", "ms", "dr", "prof", "st", "vs", "etc", "fig", "no", "vol",
}

# Короткие слова, которые не должны оставаться в одиночестве после числа:
# «5 метров», «12 тысяч», «3 млн». Проверяется не список единиц, а сам факт
# «число + короткое слово», чтобы правило работало и для русского, и для
# английского без словаря единиц измерения.
_NUMBER_RE = re.compile(r"^\d[\d\s.,]*$")
_ALPHA_RE = re.compile(r"[^\W\d_]+", re.UNICODE)


def _strip_punctuation(token: str) -> str:
    return _ALPHA_RE.findall(token.lower())[-1] if _ALPHA_RE.search(token) else ""


def _is_abbreviation(token: str) -> bool:
    if not token.endswith("."):
        return False
    stem = token[:-1]
    # "т.д." / "т.е." - несколько точек внутри: это тоже сокращение.
    if "." in stem:
        return True
    return _strip_punctuation(stem) in _ABBREVIATIONS


def ends_sentence(token: str) -> bool:
    """Заканчивает ли этот токен предложение (с поправкой на сокращения)."""
    stripped = token.rstrip("\"'»)]")
    if not stripped or stripped[-1] not in _SENTENCE_END:
        return False
    return not _is_abbreviation(stripped)


def ends_clause(token: str) -> bool:
    stripped = token.rstrip("\"'»)]")
    return bool(stripped) and stripped[-1] in _CLAUSE_END


def _is_number(token: str) -> bool:
    return bool(_NUMBER_RE.match(token.strip()))


def tokenize(text: str) -> list[tuple[str, int, int]]:
    """``(токен, начало, конец)`` в координатах исходной строки."""
    return [(match.group(0), match.start(), match.end()) for match in _TOKEN_RE.finditer(text or "")]


def _greedy_lines(words: list[str], width: int) -> list[str]:
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        if current and len(" ".join(current + [word])) > width:
            lines.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(" ".join(current))
    return lines


def wrap_lines(text: str, *, max_characters_per_line: int, max_lines: int) -> str:
    """Разложить один cue по строкам. Слова не переносятся и не теряются.

    Число строк - жёсткое ограничение кадра: три строки внизу вертикального видео
    налезают на защищённую зону. Поэтому ширина строки, наоборот, ограничение
    мягкое: если в ``max_characters_per_line`` текст в ``max_lines`` строк не
    укладывается, берётся минимальная ширина, при которой укладывается, и строки
    получаются максимально ровными. Перебор по ширине отметит валидатор
    (``line_too_long``) - но обрезать текст или добавлять строку движок не будет.
    """
    words = text.split()
    if not words:
        return ""
    limit = max(1, max_characters_per_line)
    lines_allowed = max(1, max_lines)
    joined = " ".join(words)
    if lines_allowed <= 1 or len(joined) <= limit:
        return joined
    longest_word = max(len(word) for word in words)
    width = limit
    while len(_greedy_lines(words, width)) > lines_allowed and width < len(joined):
        width += 1
    width = max(width, longest_word)
    # При найденной ширине жадная раскладка уже даёт нужное число строк; сузить её
    # ещё немного нельзя, а вот выровнять строки - можно, и это убирает «хвост» из
    # одного слова в последней строке.
    lines = _greedy_lines(words, width)
    for candidate in range(width, longest_word - 1, -1):
        balanced = _greedy_lines(words, candidate)
        if len(balanced) == len(lines):
            lines = balanced
        else:
            break
    return "\n".join(lines)


def _break_index(
    tokens: list[tuple[str, int, int]],
    start: int,
    policy: SubtitlePolicy,
) -> int:
    """Индекс токена, на котором заканчивается очередной cue (исключительно).

    Сначала набирается окно токенов, влезающих в ограничения политики, затем
    внутри окна выбирается лучшая граница: конец предложения → конец оборота →
    просто конец окна.
    """
    limit_chars = policy.max_characters_per_cue
    limit_words = max(1, policy.max_words_per_cue)
    window_end = start
    length = 0
    while window_end < len(tokens):
        token = tokens[window_end][0]
        projected = length + (1 if length else 0) + len(token)
        if window_end > start and (projected > limit_chars or window_end - start >= limit_words):
            break
        # Конец предложения внутри окна - лучшая возможная граница, дальше не идём.
        length = projected
        window_end += 1
        # Конец предложения - лучшая возможная граница, но не ценой cue из одного
        # короткого слова: «Невероятно.» отдельным кадром читается хуже, чем
        # вместе со следующей фразой.
        if ends_sentence(token) and (window_end - start >= 2 or window_end >= len(tokens)):
            return window_end
    if window_end >= len(tokens):
        return len(tokens)
    for index in range(window_end - 1, start, -1):
        if ends_clause(tokens[index][0]):
            return index + 1
    return window_end


def _shift_off_number(tokens: list[tuple[str, int, int]], start: int, end: int) -> int:
    """Не отрывать число от следующего за ним короткого слова («5 метров»).

    На конце предложения не срабатывает: «...в 2024.» - это законная граница, а не
    оторванная единица измерения.
    """
    if end <= start + 1 or end >= len(tokens):
        return end
    if ends_sentence(tokens[end - 1][0]):
        return end
    if _is_number(tokens[end - 1][0]) and len(tokens[end][0]) <= 6:
        return end - 1
    return end


def _merge_orphan_tail(spans: list[tuple[int, int]], tokens: list[tuple[str, int, int]], policy: SubtitlePolicy) -> None:
    """Не оставлять последний cue из одного короткого слова.

    Допускается перебор до 25 % от лимита символов: одна лишняя пара символов в
    предыдущем cue читается лучше, чем отдельный кадр со словом «океане».
    """
    if len(spans) < 2:
        return
    last_start, last_end = spans[-1]
    if last_end - last_start != 1:
        return
    orphan = tokens[last_start][0]
    if len(orphan) > policy.max_characters_per_line:
        return
    prev_start, _ = spans[-2]
    merged_length = sum(len(tokens[i][0]) + 1 for i in range(prev_start, last_end)) - 1
    if merged_length <= policy.max_characters_per_cue * 1.25:
        spans[-2] = (prev_start, last_end)
        spans.pop()


def split_scene_text(
    text: str,
    *,
    scene_id: str,
    scene_index: int,
    source_field: str,
    policy: SubtitlePolicy,
) -> list[SubtitleSegment]:
    """Разбить текст одной сцены на куски субтитров.

    Возвращает пустой список для пустого текста. Символьные диапазоны указывают
    на ``text``, поэтому валидатор может проверить полноту покрытия, ничего не
    домысливая.
    """
    tokens = tokenize(text)
    if not tokens:
        return []
    spans: list[tuple[int, int]] = []
    cursor = 0
    while cursor < len(tokens):
        end = _break_index(tokens, cursor, policy)
        end = _shift_off_number(tokens, cursor, end)
        end = max(end, cursor + 1)
        spans.append((cursor, end))
        cursor = end
    _merge_orphan_tail(spans, tokens, policy)

    segments: list[SubtitleSegment] = []
    for index, (first, last) in enumerate(spans, start=1):
        char_start = tokens[first][1]
        char_end = tokens[last - 1][2]
        raw = " ".join(tokens[position][0] for position in range(first, last))
        segments.append(
            SubtitleSegment(
                scene_id=scene_id,
                scene_index=scene_index,
                index=index,
                text=wrap_lines(
                    raw,
                    max_characters_per_line=policy.max_characters_per_line,
                    max_lines=policy.max_lines,
                ),
                source_field=source_field,
                char_start=char_start,
                char_end=char_end,
                ends_sentence=ends_sentence(tokens[last - 1][0]),
            )
        )
    return segments


def scene_text(scene: dict, policy: SubtitlePolicy) -> tuple[str, str]:
    """Текст сцены и поле, из которого он взят.

    Порядок задаётся политикой. По умолчанию первым идёт ``narration`` - то, что
    действительно произносится. До Q3 первым читался ``on_screen_text``, а он у
    всех провайдеров сценария равен первым пяти словам реплики
    (``text_analysis.first_words``), поэтому в кадре висели только первые пять
    слов каждой сцены (дефект W2 аудита V1).
    """
    for field_name in policy.text_field_priority:
        value = str(scene.get(field_name) or "").strip()
        if value:
            return value, field_name
    return "", policy.text_field_priority[0] if policy.text_field_priority else ""


__all__ = [
    "ends_clause",
    "ends_sentence",
    "scene_text",
    "split_scene_text",
    "tokenize",
    "wrap_lines",
]
