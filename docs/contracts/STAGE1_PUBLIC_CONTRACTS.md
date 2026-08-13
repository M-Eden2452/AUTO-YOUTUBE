---
status: historical
document_date: 2026-07-28
---

# Stage 1 public contracts

> **HISTORICAL (2026-07-28) — не текущий контракт.** Единственный файл в
> `docs/contracts/`; называет `python pipeline.py` и `src.content_creation.cli`
> «current», хотя канонический CLI — `python -m ai_youtube`, а оба названных
> входа переведены в compatibility. Реестр держит это как **C22**; целевая
> судьба файла (обновить или архивировать) принадлежит **PLAN-12E**.
> Current truth: [SYSTEM_MAP.md](../current/SYSTEM_MAP.md) и исполняемые тесты.

Status: characterized on 2026-07-28.

The code and executable tests are authoritative. This page is an index, not a
second implementation.

## Public command surfaces

- `python pipeline.py ...` is the legacy all-in-one entry point. Its maintenance
  command names, safe defaults, and catalog dispatch are protected by
  `tests/test_stage1_characterization.py`.
- `python -m src.content_creation.cli ...` is the current content-creation CLI.
  Its catalog, create, project list/status, resume, and paid-generation flag
  behavior are protected by `tests/test_content_creation_cli.py`,
  `tests/test_project_naming_and_resume.py`, and
  `tests/test_stage1_characterization.py`.
- `python anime_factory/pipeline.py ...` is the Anime Factory entry point. Its
  required `--episode`, defaults, validation errors, and non-zero failure result
  are protected by `tests/test_stage1_characterization.py`.
- `python -m src.project_foundation.cli ...` is the project/channel foundation
  compatibility CLI. Its JSON output and failure codes are protected by
  `tests/test_project_foundation_cli.py`.

No command may perform a paid call merely because a provider is configured.
Paid TTS requires the explicit CLI approval flag and the persisted approval
record enforced by the voice workflow.

## Persisted artifact schemas

The current tolerant contracts live in `schemas/`:

- `job.schema.json`
- `project.schema.json`
- `stage-state.schema.json`
- `assets.schema.json`
- `voice.schema.json`
- `evidence.schema.json`
- `render.schema.json`
- `export.schema.json`

The schemas intentionally allow additive fields. Several readers accept older,
versionless manifests, so absence of a version on an old artifact is not by
itself corruption.

## Reproducible offline baseline

- Direct dependencies: `pyproject.toml` and `requirements.txt`
- Fully pinned core environment: `requirements.lock`
- Offline CI: `.github/workflows/offline-tests.yml`
- Text and binary normalization: `.gitattributes`

Anime Factory's heavy local transcription/crop dependencies remain an optional
extra in `pyproject.toml`; the core offline suite does not download models,
invoke providers, synthesize speech, or render real video.
