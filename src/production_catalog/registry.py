"""Canonical boundary хранения записей каталога: четыре in-memory реестра.

Модуль отвечает за то, **как** каталог хранится и опрашивается, а не за то,
**что** в нём объявлено: состав задаёт ``src.production_catalog.catalog``.
Второй каталог приложений, форматов или шаблонов не создаётся.

Responsibilities:
- ``ApplicationRegistry``, ``FormatCatalog``, ``TemplateRegistry`` и
  ``ExportTargetCatalog``: регистрация, поиск, перечисление и сериализация;
- отказ от повторной регистрации одного идентификатора;
- разрешение legacy alias шаблона в canonical ``template_id`` и защита от
  столкновения alias с существующим идентификатором;
- понятная ``CatalogValidationError`` с перечнем известных идентификаторов
  вместо голого ``KeyError``.

Does not own:
- состав каталога и объявленные статусы — ``src.production_catalog.catalog``;
- формы записей — ``src.production_catalog.models``;
- выбор шаблона под конкретный запрос — ``src.content_creation.service``;
- реализацию workflow и рендереров: реестр хранит только их объявленные имена.

Inputs: объекты определений, переданные при сборке каталога.

Outputs: те же объекты и их ``to_dict()``-представления. Ни одного файла модуль
не читает и не пишет.

Important invariants:
- реестры детерминированы и хранят порядок регистрации;
- идентификатор регистрируется ровно один раз; повторная регистрация — ошибка,
  а не молчаливая перезапись;
- legacy alias разрешается в canonical идентификатор, но собственной записью не
  становится;
- обращение к неизвестному идентификатору всегда завершается
  ``CatalogValidationError``, а не пустым результатом;
- реестры не зависят от окружения, файловой системы и сети.

See also: ``src/production_catalog/catalog.py``,
``src/production_catalog/models.py``, ``src/production_catalog/__init__.py``.
"""

from __future__ import annotations

from typing import Any

from .models import (
    ApplicationDefinition,
    CatalogValidationError,
    ExportTargetDefinition,
    FormatDefinition,
    TemplateDefinition,
)


class ApplicationRegistry:
    """Deterministic, in-memory registry of ApplicationDefinition records."""

    def __init__(self) -> None:
        self._items: dict[str, ApplicationDefinition] = {}

    def register(self, application: ApplicationDefinition) -> None:
        if application.application_id in self._items:
            raise CatalogValidationError(f"Duplicate application_id: {application.application_id!r}.")
        self._items[application.application_id] = application

    def get(self, application_id: str) -> ApplicationDefinition:
        try:
            return self._items[application_id]
        except KeyError as exc:
            raise CatalogValidationError(
                f"Unknown application_id {application_id!r}. Known application_id values: {sorted(self._items)}."
            ) from exc

    def list_all(self) -> list[ApplicationDefinition]:
        return list(self._items.values())

    def serialize(self) -> list[dict[str, Any]]:
        return [item.to_dict() for item in self.list_all()]


class FormatCatalog:
    """Deterministic, in-memory registry of FormatDefinition records."""

    def __init__(self) -> None:
        self._items: dict[str, FormatDefinition] = {}

    def register(self, format_definition: FormatDefinition) -> None:
        if format_definition.format_id in self._items:
            raise CatalogValidationError(f"Duplicate format_id: {format_definition.format_id!r}.")
        self._items[format_definition.format_id] = format_definition

    def get(self, format_id: str) -> FormatDefinition:
        try:
            return self._items[format_id]
        except KeyError as exc:
            raise CatalogValidationError(
                f"Unknown format_id {format_id!r}. Known format_id values: {sorted(self._items)}."
            ) from exc

    def validate(self, format_id: str) -> None:
        self.get(format_id)

    def list_all(self) -> list[FormatDefinition]:
        return list(self._items.values())

    def serialize(self) -> list[dict[str, Any]]:
        return [item.to_dict() for item in self.list_all()]


class TemplateRegistry:
    """Deterministic, in-memory registry of TemplateDefinition records with legacy alias resolution."""

    def __init__(self) -> None:
        self._items: dict[str, TemplateDefinition] = {}
        self._aliases: dict[str, str] = {}

    def register(self, template: TemplateDefinition) -> None:
        if template.template_id in self._items:
            raise CatalogValidationError(f"Duplicate template_id: {template.template_id!r}.")
        if template.template_id in self._aliases:
            raise CatalogValidationError(
                f"template_id {template.template_id!r} collides with an existing legacy alias."
            )
        for alias in template.legacy_aliases:
            if alias in self._aliases:
                raise CatalogValidationError(f"Duplicate legacy alias: {alias!r}.")
            if alias in self._items:
                raise CatalogValidationError(
                    f"Legacy alias {alias!r} collides with an existing template_id."
                )
        self._items[template.template_id] = template
        for alias in template.legacy_aliases:
            self._aliases[alias] = template.template_id

    def resolve_id(self, template_id_or_alias: str) -> str:
        if template_id_or_alias in self._items:
            return template_id_or_alias
        if template_id_or_alias in self._aliases:
            return self._aliases[template_id_or_alias]
        raise CatalogValidationError(
            f"Unknown template id or legacy alias {template_id_or_alias!r}. "
            f"Known template_id values: {sorted(self._items)}. Known aliases: {sorted(self._aliases)}."
        )

    def get(self, template_id_or_alias: str) -> TemplateDefinition:
        canonical_id = self.resolve_id(template_id_or_alias)
        return self._items[canonical_id]

    def list_all(self) -> list[TemplateDefinition]:
        return list(self._items.values())

    def filter_by_application(self, application_id: str) -> list[TemplateDefinition]:
        return [item for item in self.list_all() if item.application_id == application_id]

    def filter_by_format(self, format_id: str) -> list[TemplateDefinition]:
        return [item for item in self.list_all() if item.format_id == format_id]

    def filter_by_enabled(self, enabled: bool) -> list[TemplateDefinition]:
        return [item for item in self.list_all() if item.enabled == enabled]

    def serialize(self) -> list[dict[str, Any]]:
        return [item.to_dict() for item in self.list_all()]


class ExportTargetCatalog:
    """Deterministic, in-memory registry of ExportTargetDefinition records."""

    def __init__(self) -> None:
        self._items: dict[str, ExportTargetDefinition] = {}

    def register(self, target: ExportTargetDefinition) -> None:
        if target.target_id in self._items:
            raise CatalogValidationError(f"Duplicate target_id: {target.target_id!r}.")
        self._items[target.target_id] = target

    def get(self, target_id: str) -> ExportTargetDefinition:
        try:
            return self._items[target_id]
        except KeyError as exc:
            raise CatalogValidationError(
                f"Unknown target_id {target_id!r}. Known target_id values: {sorted(self._items)}."
            ) from exc

    def validate(self, target_id: str) -> None:
        self.get(target_id)

    def list_all(self) -> list[ExportTargetDefinition]:
        return list(self._items.values())

    def serialize(self) -> list[dict[str, Any]]:
        return [item.to_dict() for item in self.list_all()]
