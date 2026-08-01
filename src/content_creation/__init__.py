"""Application-слой создания контента: единый service, Wizard и compatibility CLI.

Пакет отвечает за путь от запроса пользователя до вызова конкретного workflow:
разбор и валидацию входа, разрешение шаблона по каталогу, интерактивный Wizard,
подтверждение платных операций и отчёт о результате. Сам контент он не
производит.

Публичные точки входа: ``service.create_content`` — единственный вход создания;
``models.ContentCreationRequest`` / ``ContentCreationResult`` /
``ContentCreationError``; ``request_builder`` (CLI-аргументы -> request);
``wizard.run_wizard``; ``capabilities`` (что доступно в текущей конфигурации);
``commands`` (определения парсеров активного приложения); ``input_validation``,
``languages``, ``output_report``, ``presentation``.

Поток: аргументы или Wizard -> ``request_builder`` -> ``ContentCreationRequest``
-> ``service.create_content`` разрешает шаблон и проверяет запрос ->
делегирование canonical boundary
``src.ai_youtube.apps.content_creator.workflows.story_card`` или
``...workflows.fullscreen_voiceover`` -> ``ContentCreationResult`` и отчёт.

Persisted artifacts пакет не пишет: проект, манифесты и рендер создают
владельцы соответствующих workflow и storage.

Не владеет: production catalog, project state, ассетами и правами, voice/TTS,
субтитрами, рендером и порядком стадий. Канонический CLI живёт в
``src.ai_youtube.cli``.

Переходное состояние: ``cli.py``, ``fullscreen_voiceover_use_case.py`` и
``story_card_use_case.py`` — compatibility wrappers существующих canonical
boundaries; ``wizard.py`` — facade над ``wizard_state``, ``wizard_steps`` и
``wizard_presentation``. Новые возможности добавляются в canonical места, а не
в wrappers.

Инварианты: ``create_content`` остаётся единственной точкой входа для CLI и
Wizard; шаблон, отсутствующий среди реализованных, даёт явную ошибку вместо
частичного выполнения; платная операция требует явного подтверждения, а не
наличия настроенного провайдера.

Расширение: новый шаблон подключается регистрацией в ``production_catalog`` и
маршрутом в ``service`` к новому application boundary; второй application
service и второй request builder не создаются.

См. также: ``docs/current/SYSTEM_MAP.md``,
``docs/adr/0009-fullscreen-voiceover-application-boundary.md``,
``docs/adr/0010-story-card-application-boundary.md``.
"""
