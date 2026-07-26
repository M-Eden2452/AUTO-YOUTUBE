"""Проверки, которые имеют смысл только для набора локализаций сразу.

Всё, что можно проверить внутри одной локализации (неизвестный язык, профиль не
того языка, отсутствующий voice_id, отсутствующий секрет, ненайденный файл ручной
озвучки, несовместимый готовый артефакт), уже проверено в
``src.localization.resolver`` и лежит в ``ResolvedLocalization.issues``. Здесь -
только то, что видно при взгляде на несколько языковых версий одного проекта:
одинаковые id, одинаковые пути вывода, секрет, случайно попавший в конфигурацию
проекта, и путь, уводящий за пределы проекта.

Валидатор намеренно не строгий к старым проектам: манифест без новых полей не
даёт ни одной ошибки - он просто разрешается на compatibility-значениях.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Iterable

from .models import (
    ISSUE_DUPLICATE_LOCALIZATION_ID,
    ISSUE_DUPLICATE_OUTPUT_PATH,
    ISSUE_MULTIPLE_ACTIVE_SOURCES,
    ISSUE_PATH_OUTSIDE_PROJECT,
    ISSUE_SECRET_IN_CONFIG,
    ISSUE_UNKNOWN_NARRATION_SOURCE,
    NARRATION_SOURCES,
    NARRATION_SOURCE_EXISTING_ARTIFACT,
    NARRATION_SOURCE_MANUAL_AUDIO,
    SEVERITY_ERROR,
    SEVERITY_WARNING,
    LocalizationIssue,
    ResolvedLocalization,
)
from .secrets import PROVIDER_SECRET_ENV

# Имена полей, которых в конфигурации проекта/локализации быть не должно: секреты
# живут только в окружении. Проверяется имя, значение никогда не читается.
_SECRET_FIELD_NAMES = frozenset(
    {name.casefold() for name in PROVIDER_SECRET_ENV.values()}
    | {"api_key", "apikey", "secret", "token", "xi_api_key", "xi-api-key"}
)


def validate_localization_set(localizations: Iterable[ResolvedLocalization]) -> list[LocalizationIssue]:
    """Ошибки и предупреждения по набору локализаций одного проекта."""
    items = list(localizations)
    issues: list[LocalizationIssue] = []
    for item in items:
        issues.extend(item.issues)
        issues.extend(_single_source_issues(item))

    seen_ids: dict[str, int] = {}
    for item in items:
        seen_ids[item.localization_id] = seen_ids.get(item.localization_id, 0) + 1
    for localization_id, count in seen_ids.items():
        if count > 1:
            issues.append(
                LocalizationIssue(
                    code=ISSUE_DUPLICATE_LOCALIZATION_ID,
                    severity=SEVERITY_ERROR,
                    message=f"Локализация {localization_id!r} объявлена {count} раза.",
                    localization_id=localization_id,
                )
            )

    by_output: dict[str, list[str]] = {}
    for item in items:
        if not item.narration_output_path:
            continue
        key = os.path.normcase(os.path.normpath(item.narration_output_path))
        by_output.setdefault(key, []).append(item.localization_id)
    for path, owners in by_output.items():
        if len(set(owners)) > 1:
            issues.append(
                LocalizationIssue(
                    code=ISSUE_DUPLICATE_OUTPUT_PATH,
                    severity=SEVERITY_ERROR,
                    message=(
                        f"Один и тот же файл озвучки {path} назначен локализациям "
                        f"{', '.join(sorted(set(owners)))} - одна перезаписала бы другую."
                    ),
                    localization_id=sorted(set(owners))[0],
                )
            )
    return issues


def _single_source_issues(item: ResolvedLocalization) -> list[LocalizationIssue]:
    """Один активный источник озвучки, и он должен быть известным."""
    issues: list[LocalizationIssue] = []
    if item.narration_source not in NARRATION_SOURCES:
        issues.append(
            LocalizationIssue(
                code=ISSUE_UNKNOWN_NARRATION_SOURCE,
                severity=SEVERITY_ERROR,
                message=(
                    f"Неизвестный источник озвучки {item.narration_source!r}; известны: "
                    f"{', '.join(sorted(NARRATION_SOURCES))}."
                ),
                localization_id=item.localization_id,
            )
        )
    active = sum(
        [
            bool(item.tts_allowed),
            item.narration_source == NARRATION_SOURCE_MANUAL_AUDIO and bool(item.manual_audio_path),
            item.narration_source == NARRATION_SOURCE_EXISTING_ARTIFACT and bool(item.reuse_existing_narration),
        ]
    )
    if active > 1:
        issues.append(
            LocalizationIssue(
                code=ISSUE_MULTIPLE_ACTIVE_SOURCES,
                severity=SEVERITY_ERROR,
                message=(
                    f"Для локализации {item.localization_id!r} активны сразу несколько источников "
                    "озвучки - должен быть выбран ровно один."
                ),
                localization_id=item.localization_id,
            )
        )
    return issues


def validate_stored_localization_config(
    config: dict[str, Any] | None, *, localization_id: str = ""
) -> list[LocalizationIssue]:
    """Секрет не должен лежать в конфигурации проекта или локализации.

    Проверяются только *имена* полей; значение не читается и никуда не попадает.
    """
    if not isinstance(config, dict):
        return []
    issues: list[LocalizationIssue] = []
    for key, value in config.items():
        if str(key).casefold() in _SECRET_FIELD_NAMES and value not in (None, "", {}, []):
            issues.append(
                LocalizationIssue(
                    code=ISSUE_SECRET_IN_CONFIG,
                    severity=SEVERITY_ERROR,
                    message=(
                        f"Поле {key!r} похоже на секрет и не должно храниться в конфигурации "
                        "проекта или локализации - ключи берутся только из окружения."
                    ),
                    localization_id=localization_id,
                )
            )
        elif isinstance(value, dict):
            issues.extend(validate_stored_localization_config(value, localization_id=localization_id))
    return issues


def validate_local_path(
    path: str, *, project_root: str | Path, localization_id: str = ""
) -> list[LocalizationIssue]:
    """Путь ручной озвучки не должен уводить за пределы проекта.

    Это предупреждение, а не ошибка: пользователь имеет полное право положить свой
    WAV где угодно на диске, и сегодняшний ``--audio-file`` это разрешает. Смысл
    проверки - заметить ``../..`` в пути, который выглядит как относительный к
    проекту.
    """
    if not path:
        return []
    candidate = Path(path)
    if candidate.is_absolute():
        return []
    resolved = (Path(project_root) / candidate).resolve()
    root = Path(project_root).resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        return [
            LocalizationIssue(
                code=ISSUE_PATH_OUTSIDE_PROJECT,
                severity=SEVERITY_WARNING,
                message=f"Путь {path!r} выходит за пределы папки проекта {root.as_posix()}.",
                localization_id=localization_id,
            )
        ]
    return []


__all__ = [
    "validate_local_path",
    "validate_localization_set",
    "validate_stored_localization_config",
]
