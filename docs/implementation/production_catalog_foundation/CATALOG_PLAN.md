# Production Catalog Foundation — Plan

Этап 2A из `docs/handoff/NEXT_PLAN.md` (добавлен как новый этап перед Stage 2:
универсальный пользовательский CLI). Цель — минимальный read-only каталог
пользовательской иерархии `Application → Format → Template → Export Target`,
без проектов, каналов, EvidenceBundle или creator workflow.

## Объём работы

1. Immutable/validated dataclasses: `ApplicationDefinition`, `FormatDefinition`,
   `TemplateDefinition`, `ExportTargetDefinition` в `src/production_catalog/models.py`.
   Закрытый набор `implementation_status`: `active | planned | experimental`.
2. Deterministic in-memory registries в `src/production_catalog/registry.py`:
   `ApplicationRegistry`, `FormatCatalog`, `TemplateRegistry` (canonical id +
   legacy alias), `ExportTargetCatalog`.
3. Фактическая регистрация данных в `src/production_catalog/catalog.py`:
   `content_creator` (active/enabled), `video_repurposer` (planned/disabled),
   3 формата, 1 шаблон `story_card_text_only_v1` (legacy alias
   `story_card_short_v1`), 5 export targets.
4. Read-only CLI в `src/production_catalog/cli.py`, подключенный в `pipeline.py`
   как 4 новые команды: `applications`, `formats`, `templates`, `export-targets`,
   каждая с `list`/`inspect` и опциональным `--json`.
5. `COMMANDS.md` — пользовательская шпаргалка.
6. Targeted tests: `tests/test_production_catalog_foundation.py`.
7. Обновление handoff-документов.

## Не входит в этот этап

Проекты, каналы, EvidenceBundle, creator workflow, Video Repurposer workflow,
интерактивный UI, Bash launcher, provider search, Vision, TTS, downloads,
render, изменение renderer/preset/owl artifacts.

## Источники истины, использованные при проектировании

- `CLAUDE.md`, `docs/handoff/START_HERE.md`, `CURRENT_STATE.md`, `NEXT_PLAN.md`,
  `CLI_CHEATSHEET.md`, `HANDOFF_MANIFEST.json`.
- `pipeline.py` — argparse conventions (`command`/`subcommand`, `raise SystemExit`
  для явных ошибок, `run_voice_cli(args) -> int` как образец для
  `run_production_catalog_cli`).
- `config/render_presets/story_card_short_v1.json`,
  `src/production_plan/story_card_short_render.py` — источник `render_preset_id`.
- `src/news/models.py`, `src/assets/models.py` — конвенции dataclass +
  `to_dict()`/`from_dict()`, closed value sets, `asdict_clean`.
- `src/providers/__init__.py` — конвенция явного `__all__`/реестра модулей.
