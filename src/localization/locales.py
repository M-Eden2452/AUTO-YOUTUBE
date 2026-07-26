"""Одно место, которое знает: какой код языка канонический, какой locale ему
соответствует и какие написания того же языка встречаются на диске.

Таблица не выдумана. Коды ``ru``/``en``/``es`` и locale ``ru-RU``/``en-US``/``es-ES`` -
это ровно то, что уже лежит в ``channels/*/channel_config.json``
(``languages.<code>.script_locale``) и что захардкожено в
``src.news.models.NewsJob.create``. Отображаемые имена - те же, что уже показывает
``src.content_creation.languages`` (этот модуль теперь берёт список отсюда, чтобы
списка языков не стало два).

Нормализация нужна на runtime, а не в файлах: старые проекты могли записать
``ru-RU`` или ``Russian`` в ``job.json``, и они должны продолжать читаться. Поэтому
``normalize_language`` только *отвечает*, какой это язык; ни один файл не
переписывается, и ``localization_id`` (имя папки) никогда не нормализуется - см.
``src.localization.models.ResolvedLocalization``.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class LanguageDefinition:
    code: str
    locale: str
    display_name: str
    # Написания того же языка, которые могут прийти из CLI, старого job.json или
    # channel_config.json. Всё сравнивается в casefold.
    aliases: tuple[str, ...] = field(default_factory=tuple)


LANGUAGE_DEFINITIONS: tuple[LanguageDefinition, ...] = (
    LanguageDefinition(
        code="ru",
        locale="ru-RU",
        display_name="Русский",
        aliases=("ru-ru", "ru_ru", "rus", "russian", "русский", "рус"),
    ),
    LanguageDefinition(
        code="en",
        locale="en-US",
        display_name="English",
        aliases=("en-us", "en_us", "en-gb", "en_gb", "eng", "english", "английский"),
    ),
    LanguageDefinition(
        code="es",
        locale="es-ES",
        display_name="Español",
        aliases=("es-es", "es_es", "es-mx", "es_mx", "spa", "spanish", "español", "espanol", "испанский"),
    ),
)

_BY_CODE: dict[str, LanguageDefinition] = {item.code: item for item in LANGUAGE_DEFINITIONS}
_BY_ALIAS: dict[str, LanguageDefinition] = {}
for _definition in LANGUAGE_DEFINITIONS:
    _BY_ALIAS[_definition.code] = _definition
    _BY_ALIAS[_definition.locale.casefold()] = _definition
    for _alias in _definition.aliases:
        _BY_ALIAS[_alias.casefold()] = _definition


def list_language_definitions() -> list[LanguageDefinition]:
    return list(LANGUAGE_DEFINITIONS)


def known_language_codes() -> tuple[str, ...]:
    return tuple(_BY_CODE)


def normalize_language(value: str) -> str:
    """Канонический код языка, или ``""`` если язык неизвестен.

    Пустой ответ - это не ошибка сам по себе: вызывающий решает, считать ли
    неизвестный язык ошибкой (валидация) или просто оставить как есть
    (совместимость со старым проектом).
    """
    text = str(value or "").strip()
    if not text:
        return ""
    definition = _BY_ALIAS.get(text.casefold())
    if definition is not None:
        return definition.code
    # "ru-RU-x-custom" и подобное: берём первый сегмент, если он сам по себе известен.
    head = text.split("-")[0].split("_")[0].casefold()
    definition = _BY_ALIAS.get(head)
    return definition.code if definition is not None else ""


def is_known_language(value: str) -> bool:
    return bool(normalize_language(value))


def default_locale(value: str) -> str:
    """Locale по умолчанию для языка, или ``""`` для неизвестного языка."""
    code = normalize_language(value)
    definition = _BY_CODE.get(code)
    return definition.locale if definition is not None else ""


def normalize_locale(value: str, *, language: str = "") -> str:
    """Locale в виде ``xx-YY``.

    Если ``value`` пуст или не похож на locale, берётся locale по умолчанию для
    ``language``. Регион приводится к верхнему регистру, язык - к нижнему, чтобы
    ``ru_ru`` и ``RU-ru`` читались как один и тот же ``ru-RU``.
    """
    text = str(value or "").strip().replace("_", "-")
    if text:
        parts = [part for part in text.split("-") if part]
        if len(parts) >= 2:
            return f"{parts[0].lower()}-{parts[1].upper()}"
        fallback = default_locale(parts[0])
        if fallback:
            return fallback
    return default_locale(language)


def display_name(value: str) -> str:
    """Человекочитаемое имя языка; для неизвестного - то, что передали."""
    definition = _BY_CODE.get(normalize_language(value))
    return definition.display_name if definition is not None else str(value or "")


__all__ = [
    "LANGUAGE_DEFINITIONS",
    "LanguageDefinition",
    "default_locale",
    "display_name",
    "is_known_language",
    "known_language_codes",
    "list_language_definitions",
    "normalize_language",
    "normalize_locale",
]
