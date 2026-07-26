"""Проверка набора cues. Ошибки и предупреждения разделены намеренно.

**Ошибка** - артефакт нельзя отдавать рендеру: сломанное время, пересечение,
потерянный текст, чужой язык. **Предупреждение** - субтитр читается, но не
идеален: слишком быстро, слишком длинная строка, legacy-тайминг. Ни одно
предупреждение не делает старый проект нечитаемым - это условие
обратной совместимости, а не мягкость.

Коды стабильны и живут в ``src.subtitles.models`` (тот же приём, что у
``src.localization.models``): CLI и пайплайн смотрят на код, а не на текст.
"""

from __future__ import annotations

import math

from .models import (
    ERR_CUE_ORDER_INVALID,
    ERR_CUE_OUTSIDE_NARRATION,
    ERR_CUE_OUTSIDE_SCENE,
    ERR_CUE_OVERLAP,
    ERR_CUE_WITHOUT_SCENE,
    ERR_DUPLICATE_SCENE_ID,
    ERR_EMPTY_CUE_TEXT,
    ERR_END_NOT_AFTER_START,
    ERR_LANGUAGE_MISMATCH,
    ERR_NEGATIVE_TIME,
    ERR_NON_FINITE_TIME,
    ERR_NO_CUES,
    ERR_TEXT_NOT_COVERED,
    ERR_UNKNOWN_SCENE_ID,
    TIMING_SOURCE_LEGACY_PLANNED,
    WARN_CUE_TOO_LONG,
    WARN_CUE_TOO_SHORT,
    WARN_DUPLICATE_TEXT,
    WARN_GAP_TOO_LARGE,
    WARN_LEGACY_ARTIFACT,
    WARN_LEGACY_TIMING,
    WARN_LINE_TOO_LONG,
    WARN_NARRATION_DURATION_UNKNOWN,
    WARN_ON_SCREEN_TEXT_USED,
    WARN_ORPHAN_LINE,
    WARN_READING_SPEED,
    WARN_TOO_MANY_LINES,
    TEXT_FIELD_NARRATION,
    SubtitleCue,
    SubtitleIssue,
    SubtitlePolicy,
    SubtitleValidationResult,
    error,
    warning,
)
from .segmentation import tokenize

# Допуск сравнения времён: округление до миллисекунд при записи SRT/ASS не должно
# превращаться в «cue вышел за сцену на 0.0004 с».
TIME_TOLERANCE_SEC = 0.011


def _check_times(cue: SubtitleCue, issues: list[SubtitleIssue]) -> bool:
    """Базовая арифметическая корректность одного cue. ``False`` - дальше проверять
    нечего (сравнения с NaN бессмысленны)."""
    for label, value in (("start_sec", cue.start_sec), ("end_sec", cue.end_sec)):
        if not math.isfinite(value):
            issues.append(
                error(ERR_NON_FINITE_TIME, f"{cue.cue_id}: {label} не является числом ({value!r}).",
                      scene_id=cue.scene_id, cue_id=cue.cue_id)
            )
            return False
        if value < 0:
            issues.append(
                error(ERR_NEGATIVE_TIME, f"{cue.cue_id}: {label} отрицательное ({value}).",
                      scene_id=cue.scene_id, cue_id=cue.cue_id)
            )
            return False
    if cue.end_sec <= cue.start_sec:
        issues.append(
            error(ERR_END_NOT_AFTER_START,
                  f"{cue.cue_id}: конец ({cue.end_sec}) не позже начала ({cue.start_sec}).",
                  scene_id=cue.scene_id, cue_id=cue.cue_id)
        )
        return False
    return True


def _check_policy(cue: SubtitleCue, policy: SubtitlePolicy, issues: list[SubtitleIssue]) -> None:
    duration = cue.duration_sec
    if duration + TIME_TOLERANCE_SEC < policy.min_cue_duration_sec:
        issues.append(
            warning(WARN_CUE_TOO_SHORT,
                    f"{cue.cue_id}: {duration:.2f} с короче минимума {policy.min_cue_duration_sec:.2f} с.",
                    scene_id=cue.scene_id, cue_id=cue.cue_id)
        )
    if duration > policy.max_cue_duration_sec + TIME_TOLERANCE_SEC:
        issues.append(
            warning(WARN_CUE_TOO_LONG,
                    f"{cue.cue_id}: {duration:.2f} с длиннее максимума {policy.max_cue_duration_sec:.2f} с.",
                    scene_id=cue.scene_id, cue_id=cue.cue_id)
        )
    if cue.reading_speed_cps > policy.max_reading_speed_cps:
        issues.append(
            warning(WARN_READING_SPEED,
                    f"{cue.cue_id}: {cue.reading_speed_cps:.1f} символов/с при допустимых "
                    f"{policy.max_reading_speed_cps:.1f}.",
                    scene_id=cue.scene_id, cue_id=cue.cue_id)
        )
    lines = cue.lines
    if len(lines) > policy.max_lines:
        issues.append(
            warning(WARN_TOO_MANY_LINES, f"{cue.cue_id}: строк {len(lines)} при допустимых {policy.max_lines}.",
                    scene_id=cue.scene_id, cue_id=cue.cue_id)
        )
    for line in lines:
        if len(line) > policy.max_characters_per_line:
            issues.append(
                warning(WARN_LINE_TOO_LONG,
                        f"{cue.cue_id}: строка длиной {len(line)} при лимите "
                        f"{policy.max_characters_per_line}.",
                        scene_id=cue.scene_id, cue_id=cue.cue_id)
            )
    if len(lines) > 1:
        for line in lines:
            if 0 < len(line.strip()) < policy.min_line_characters:
                issues.append(
                    warning(WARN_ORPHAN_LINE, f"{cue.cue_id}: строка из {len(line.strip())} символов осталась одна.",
                            scene_id=cue.scene_id, cue_id=cue.cue_id)
                )
                break


def _check_coverage(
    cues: tuple[SubtitleCue, ...],
    scene_texts: dict[str, str],
    issues: list[SubtitleIssue],
) -> None:
    """Ни одно слово не потеряно, не продублировано и не переставлено.

    Сравниваются последовательности токенов, а не строки: перенос строки внутри
    cue - это оформление, а не изменение текста.
    """
    by_scene: dict[str, list[SubtitleCue]] = {}
    for cue in cues:
        by_scene.setdefault(cue.scene_id, []).append(cue)
    for scene_id, text in scene_texts.items():
        expected = [token for token, _, _ in tokenize(text)]
        actual: list[str] = []
        for cue in sorted(by_scene.get(scene_id, []), key=lambda item: item.scene_cue_index):
            actual.extend(cue.plain_text.split())
        if expected != actual:
            issues.append(
                error(ERR_TEXT_NOT_COVERED,
                      f"{scene_id}: субтитры не совпадают с текстом сцены "
                      f"(слов в сцене {len(expected)}, в субтитрах {len(actual)}).",
                      scene_id=scene_id)
            )


def validate_cues(
    cues: tuple[SubtitleCue, ...] | list[SubtitleCue],
    *,
    policy: SubtitlePolicy,
    language: str = "",
    scene_order: tuple[str, ...] | list[str] = (),
    scene_bounds: dict[str, tuple[float, float]] | None = None,
    scene_texts: dict[str, str] | None = None,
    narration_duration_sec: float = 0.0,
) -> SubtitleValidationResult:
    """Полная проверка набора cues.

    ``scene_bounds`` и ``scene_texts`` необязательны: артефакт, прочитанный с диска
    без сценария, всё равно проверяется на арифметику, порядок, пересечения и
    политику. Это то, что позволяет валидировать старые файлы.
    """
    issues: list[SubtitleIssue] = []
    ordered = list(cues)
    if not ordered:
        issues.append(error(ERR_NO_CUES, "Набор субтитров пуст."))
        return SubtitleValidationResult(tuple(issues))

    known_scenes = list(scene_order) or None
    if known_scenes is not None and len(known_scenes) != len(set(known_scenes)):
        duplicates = sorted({scene for scene in known_scenes if known_scenes.count(scene) > 1})
        issues.append(error(ERR_DUPLICATE_SCENE_ID, f"Сценарий содержит повторяющиеся scene_id: {', '.join(duplicates)}."))

    previous: SubtitleCue | None = None
    scene_positions: list[int] = []
    for cue in ordered:
        if not cue.plain_text:
            issues.append(error(ERR_EMPTY_CUE_TEXT, f"{cue.cue_id or cue.index}: пустой текст.",
                                scene_id=cue.scene_id, cue_id=cue.cue_id))
        if not cue.scene_id:
            # Артефакт, созданный до Q3, сцен не хранил вообще: для него это факт
            # происхождения, а не поломка. Ошибкой отсутствие сцены становится
            # только там, где сценарий известен и связь обязана быть.
            issues.append(
                error(ERR_CUE_WITHOUT_SCENE, f"cue {cue.index} не привязан к сцене.", cue_id=cue.cue_id)
                if known_scenes is not None
                else warning(WARN_LEGACY_ARTIFACT,
                             f"cue {cue.index}: артефакт не хранит scene_id (создан до этапа Q3).",
                             cue_id=cue.cue_id)
            )
        elif known_scenes is not None:
            if cue.scene_id not in known_scenes:
                issues.append(error(ERR_UNKNOWN_SCENE_ID, f"{cue.cue_id}: сцена {cue.scene_id!r} отсутствует в сценарии.",
                                    scene_id=cue.scene_id, cue_id=cue.cue_id))
            else:
                scene_positions.append(known_scenes.index(cue.scene_id))
        if language and cue.language and cue.language != language:
            issues.append(error(ERR_LANGUAGE_MISMATCH,
                                f"{cue.cue_id}: язык cue {cue.language!r} не совпадает с языком локализации {language!r}.",
                                scene_id=cue.scene_id, cue_id=cue.cue_id))
        if cue.timing_source == TIMING_SOURCE_LEGACY_PLANNED:
            issues.append(warning(WARN_LEGACY_TIMING,
                                  f"{cue.cue_id}: тайминг взят из планового target_duration_sec (legacy).",
                                  scene_id=cue.scene_id, cue_id=cue.cue_id))
        if cue.source_field != TEXT_FIELD_NARRATION:
            issues.append(warning(WARN_ON_SCREEN_TEXT_USED,
                                  f"{cue.cue_id}: текст взят из {cue.source_field!r}, а не из narration.",
                                  scene_id=cue.scene_id, cue_id=cue.cue_id))
        if not _check_times(cue, issues):
            previous = None
            continue
        _check_policy(cue, policy, issues)

        if previous is not None:
            if cue.plain_text.casefold() == previous.plain_text.casefold():
                issues.append(warning(WARN_DUPLICATE_TEXT, f"{cue.cue_id}: текст дублирует предыдущий cue.",
                                      scene_id=cue.scene_id, cue_id=cue.cue_id))
            if cue.start_sec + TIME_TOLERANCE_SEC < previous.start_sec:
                issues.append(error(ERR_CUE_ORDER_INVALID,
                                    f"{cue.cue_id}: начинается раньше предыдущего cue {previous.cue_id}.",
                                    scene_id=cue.scene_id, cue_id=cue.cue_id))
            gap = cue.start_sec - previous.end_sec
            if not policy.allow_overlap and gap < -TIME_TOLERANCE_SEC:
                issues.append(error(ERR_CUE_OVERLAP,
                                    f"{cue.cue_id}: пересекается с {previous.cue_id} на {-gap:.3f} с.",
                                    scene_id=cue.scene_id, cue_id=cue.cue_id))
            elif gap > policy.max_gap_sec:
                issues.append(warning(WARN_GAP_TOO_LARGE,
                                      f"{cue.cue_id}: пауза без субтитра {gap:.2f} с после {previous.cue_id}.",
                                      scene_id=cue.scene_id, cue_id=cue.cue_id))
        if scene_bounds and cue.scene_id in scene_bounds:
            start, end = scene_bounds[cue.scene_id]
            if cue.start_sec + TIME_TOLERANCE_SEC < start or cue.end_sec > end + TIME_TOLERANCE_SEC:
                issues.append(error(ERR_CUE_OUTSIDE_SCENE,
                                    f"{cue.cue_id}: [{cue.start_sec:.3f}, {cue.end_sec:.3f}] выходит за сцену "
                                    f"[{start:.3f}, {end:.3f}].",
                                    scene_id=cue.scene_id, cue_id=cue.cue_id))
        if narration_duration_sec > 0 and cue.end_sec > narration_duration_sec + TIME_TOLERANCE_SEC:
            issues.append(error(ERR_CUE_OUTSIDE_NARRATION,
                                f"{cue.cue_id}: заканчивается на {cue.end_sec:.3f} с при длительности озвучки "
                                f"{narration_duration_sec:.3f} с.",
                                scene_id=cue.scene_id, cue_id=cue.cue_id))
        previous = cue

    if scene_positions and scene_positions != sorted(scene_positions):
        issues.append(error(ERR_CUE_ORDER_INVALID, "Порядок сцен в субтитрах не совпадает с порядком сценария."))
    if narration_duration_sec <= 0:
        issues.append(warning(WARN_NARRATION_DURATION_UNKNOWN,
                              "Длительность озвучки неизвестна: выход за её пределы проверить нельзя."))
    if scene_texts:
        _check_coverage(tuple(ordered), scene_texts, issues)
    return SubtitleValidationResult(tuple(issues))


def merge(*results: SubtitleValidationResult) -> SubtitleValidationResult:
    issues: list[SubtitleIssue] = []
    for result in results:
        issues.extend(result.issues)
    return SubtitleValidationResult(tuple(issues))


__all__ = ["TIME_TOLERANCE_SEC", "merge", "validate_cues"]
