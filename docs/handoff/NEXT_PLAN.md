# Next Plan

> **Статус: исторический документ.** Этапы 1, 2A, 2B и 3 (универсальный CLI) выполнены.
> Актуальный план — `docs/handoff/AUTONOMOUS_IMPLEMENTATION_PLAN.md`.

Работать строго по этапам. Не добавлять новую архитектуру, если можно соединить существующие модули.

## Этап 1: адаптивный story_card_short_v1 — готово

Сделать единственный `story_card_short_v1` адаптивным.

Требования:

- Сохранить один фирменный стиль.
- Измерять реальную высоту текста.
- Динамически увеличивать центральное видео.
- Убрать большие пустые зоны.
- Нижний комментарий приблизить к нижнему краю.
- Не резервировать место под рекламу или аватар.
- Продолжительность определять событием или озвучкой.
- Повтор по умолчанию выключить.
- Бесплатно перерендерить существующую сову в `projects/story_card_owl_test/final_test_v2.mp4`.
- Не выполнять поиск, Vision или TTS.
- Не перезаписывать `projects/story_card_owl_test/final_test.mp4`.

Проверять targeted:

```bash
python -m unittest tests.test_story_card_short_renderer -v
```

## Этап 2A: Production Catalog Foundation — готово

Read-only каталог `Application → Format → Template → Export Target` в
`src/production_catalog/`. Подробности: `docs/handoff/CURRENT_STATE.md`,
`docs/implementation/production_catalog_foundation/CATALOG_REPORT.md`.

## Этап 2B: Project / Channel / Evidence Foundation — следующий этап

Требования:

- `ChannelProfile` — профиль канала (используется каталогом Applications/Templates).
- `ProjectManifest` — минимальный контракт проекта, ссылается на `template_id` из каталога.
- `ProjectFactory` — создание project-файлов на основе `ProjectManifest` (сейчас каталог их не создаёт).
- `EvidenceBundle` — сейчас в `TemplateDefinition.output_contract` только декларируется `evidence_required`; сама сущность ещё не реализована.
- `ChannelOutputPolicy`.
- CLI: `channels list`, `channels inspect`.
- Тестовый канал `nature_pulse`.

Не создавать новую параллельную provider/preview/semantic/voice/renderer архитектуру — использовать существующие модули и каталог из Этапа 2A.

## Этап 3: универсальный пользовательский CLI

Добавить команду:

```bash
python -B pipeline.py story-card create ...
```

Команда должна соединять существующие части:

- тема;
- короткий оригинальный сценарий;
- поисковые запросы;
- preview candidates;
- temporal analysis;
- semantic/shadow selection;
- загрузка одного original;
- лицензия и provenance;
- adaptive story-card render;
- manual WAV или выбранный voice workflow;
- финальный MP4.

Не создавать новую параллельную архитектуру для provider, preview, semantic, voice или renderer. Опираться на `template_id` из каталога Этапа 2A и на `ProjectManifest`/`ProjectFactory` из Этапа 2B.

## Этап 4: batch-команда

Добавить JSON queue для серии story-card задач.

Планируемая команда:

```bash
python -B pipeline.py story-card batch --queue <queue.json>
```

## Этап 5: реальные тестовые Shorts

Создать несколько реальных тестовых Shorts после готовности адаптивного renderer и universal CLI.

Каждый тест должен сохранять:

- project manifest;
- selected asset;
- license/provenance;
- render manifest;
- final MP4;
- краткий report.

## Этап 6: UI и cleanup

Только после успешных E2E-тестов переходить к UI.

Cleanup/reorganization делать после UI-проверки, миграции и резервной копии. Legacy не удалять заранее.
