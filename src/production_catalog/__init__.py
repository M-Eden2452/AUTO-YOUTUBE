"""Единственный честный реестр приложений, форматов, шаблонов и export targets.

Пакет отвечает на вопрос «что продукт умеет на самом деле»: какие приложения
включены, какие форматы имеют шаблон, какой workflow и renderer стоят за
шаблоном, куда его можно экспортировать. Он декларативен и ничего не исполняет.

Публичные точки входа: ``catalog.get_default_catalog`` и
``catalog.ProductionCatalog``, определения в ``models`` (``ApplicationDefinition``,
``FormatDefinition``, ``TemplateDefinition``, ``ExportTargetDefinition``,
``CatalogValidationError``), реестры в ``registry`` и read-only
``cli.run_production_catalog_cli``.

Поток: ``get_default_catalog`` собирает и кэширует четыре реестра ->
``src.content_creation.service`` разрешает по нему шаблон запроса и проверяет
совместимость формата -> CLI, Wizard и capabilities показывают только то, что
каталог объявил.

Persisted artifacts отсутствуют: каталог существует в памяти. Render preset
шаблона хранится отдельно (``config/render_presets/``) и принадлежит своему
владельцу.

Не владеет: реализацией workflow, рендерерами, project state, правами,
провайдерами и policy озвучки — ``workflow_binding`` только называет
существующих владельцев. Второй каталог шаблонов, второй registry рендереров и
``production_plan.json``, копирующий манифесты, не создаются.

Инварианты: ``implementation_status`` и ``enabled`` описывают фактическое
состояние, а не намерение; формат без зарегистрированного шаблона остаётся
``enabled=False``, иначе вызывающая сторона упирается в тупик; активными
объявляются только реально работающие шаблоны — сегодня
``story_card_text_only_v1`` и ``fullscreen_voiceover_v1``; согласованность
каталога и capabilities проверяет ``tests/test_capability_consistency.py``.

Расширение: новый шаблон или формат добавляется записью в
``catalog._build_*`` вместе с реальной реализацией и её тестами; включение
``enabled=True`` выполняется тем же изменением, что регистрирует работающий
workflow.

См. также: ``docs/current/SYSTEM_MAP.md``, ``docs/current/PRODUCT_PLAN.md``,
``docs/adr/0016-two-engine-product-architecture.md``.
"""

from __future__ import annotations
