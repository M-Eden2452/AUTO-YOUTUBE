---
status: historical
audit_date: 2026-07-22
---

> **HISTORICAL (2026-07-22) — не текущая инструкция и не карта текущей
> архитектуры.** Эта серия описывает репозиторий **до** governance-reset:
> `pipeline.py` как основной вход, `asset_finder` / `video_asset_engine` как
> действующая asset-система, модули, часть которых уже удалена или ретайрена.
> Канонический CLI сегодня — `python -m ai_youtube`. Current truth:
> [SYSTEM_MAP.md](../current/SYSTEM_MAP.md) и
> [CLEANUP_REGISTRY.md](../current/CLEANUP_REGISTRY.md); индекс каталога —
> [README.md](README.md). Команды и пути отсюда не исполнять.

# PROJECT AUDIT ROADMAP

## Принцип

Это не план реализации в текущем задании. Это рекомендуемая последовательность развития, чтобы не усиливать текущие разрывы архитектуры.

## Этап 0. Защита текущего состояния

- Цель: зафиксировать фактические schemas, manifests and expected behavior before refactor.
- Зависимости: текущий код, existing sample projects, fake assets.
- Затрагиваемые файлы: `src/news/models.py`, `src/news/project_store.py`, `tests/*`, sample fixtures.
- Что нельзя делать раньше: подключать новые providers, менять render flow, переписывать pipeline.
- Критерии готовности: schemas documented, JSON validation exists, fake-provider e2e test exists, old manifests readable.
- Тесты: no-network news pipeline to fake final render; schema roundtrip; media index validation.
- Риски: можно формализовать текущие плохие схемы; нужно явно отделить legacy compatibility.
- Сложность: M.
- Результат: безопасная база для изменения pipeline без потери проектов.

## Этап 1. Стабилизация основного pipeline

- Цель: выбрать `src/news` как основной future pipeline and make one no-network end-to-end path.
- Зависимости: Этап 0.
- Затрагиваемые файлы: `src/news/pipeline.py`, `src/news/asset_manager.py`, `src/news/final_renderer.py`, `src/news/quality_check.py`.
- Что нельзя делать раньше: UI, new providers, vision reranking.
- Критерии готовности: topic/text -> script -> scenes -> fake/local assets -> manual/fake voice -> subtitles -> MP4.
- Тесты: fake provider, manual WAV, renderer synthetic video, resume.
- Риски: старый pipeline может остаться полезным, его нельзя ломать.
- Сложность: L.
- Результат: один проверяемый основной pipeline.

## Этап 2. Единая provider architecture

- Цель: ввести общий `StockProvider`.
- Зависимости: Этап 1.
- Затрагиваемые файлы: `src/providers/*`, `src/news/asset_manager.py`, `src/news/stock_video_downloader.py`, `src/video_asset_engine.py`.
- Что нельзя делать раньше: массово подключать Wikimedia/NASA/Archive/Envato.
- Критерии готовности: provider supports search, preview metadata, download, license, validation, diagnostics.
- Тесты: fake provider contract, Pexels/Pixabay mocked API, retry tests.
- Риски: придётся поддерживать старые manifests during migration.
- Сложность: L.
- Результат: новые источники добавляются без правок renderer/pipeline core.

## Этап 3. Единая схема assets и лицензий

- Цель: создать обязательные `Asset`, `AssetCandidate`, `SelectedAsset`, `DownloadedAsset`, `AssetLicense`, `Provenance`.
- Зависимости: Этап 2.
- Затрагиваемые файлы: `src/news/models.py`, `src/media_library.py`, provider modules, manifests.
- Что нельзя делать раньше: коммерческое использование или upload.
- Критерии готовности: каждый final visual has provider, asset_id, source_url, download_url, author if available, license, license_url, rights flags, checksum, download_date, project_id, scene_id.
- Тесты: license completeness; blocked unknown rights; source list generation.
- Риски: часть существующей библиотеки останется unknown and must be quarantined or grandfathered.
- Сложность: L.
- Результат: proof-grade provenance baseline.

## Этап 4. Pexels и Pixabay

- Цель: перенести текущие Pexels/Pixabay flows на новую architecture.
- Зависимости: Этапы 2-3.
- Затрагиваемые файлы: `src/providers/pexels_provider.py`, `src/providers/pixabay_provider.py`, old duplicate wrappers.
- Что нельзя делать раньше: удалить дубли без тестов.
- Критерии готовности: search/download/license/retry/vertical strategy all covered.
- Тесты: mocked API responses, download validation, duplicate prevention.
- Риски: provider license terms may need legal/product decision.
- Сложность: M.
- Результат: two reliable first-class providers.

## Этап 5. Новые источники

### Wikimedia Commons

- Встроить: `src/providers/wikimedia_provider.py` behind `StockProvider`.
- Нужны интерфейсы: license normalization, attribution, file page/source page, author extraction.
- Риски: complex licenses, attribution requirements, public domain vs CC variants.

### NASA Image and Video Library

- Встроить: `src/providers/nasa_provider.py`.
- Нужны интерфейсы: collection/media asset mapping, preview/download URL, rights notes.
- Риски: NASA media often permissive but not all content is automatically free of third-party restrictions.

### Internet Archive

- Встроить: `src/providers/internet_archive_provider.py`.
- Нужны интерфейсы: item metadata, files list, license URL, derivatives.
- Риски: heterogeneous metadata, large files, unclear rights.

### Local Library Provider

- Встроить: `src/providers/local_library_provider.py` using migrated `src/media_library.py`.
- Нужны интерфейсы: semantic tags, checksums, used_in, quarantine, rights status.
- Риски: unknown legacy licenses.

### Envato Manual Provider

- Встроить: `src/providers/envato_manual_provider.py` plus UI/manual import stage.
- Нужны интерфейсы: generated search URL, manual downloaded file import, purchase/license proof attachment.
- Риски: account-specific license proof, manual errors, cannot automate download safely.

- Зависимости: Этапы 2-4.
- Сложность: XL as group.
- Результат: expandable provider ecosystem.

## Этап 6. Visual reranking

- Цель: improve suitability beyond metadata.
- Зависимости: downloaded/preview assets and license-safe preview pipeline.
- Затрагиваемые файлы: semantic selection, providers, asset cache.
- Что нельзя делать раньше: call paid vision APIs without cost controls.
- Критерии готовности: preview thumbnails, frame sampling, duplicate detection, continuity rules.
- Тесты: fixture previews, frame tags, neighbor-scene duplicate avoidance.
- Риски: cost and false positives.
- Сложность: L.
- Результат: better scene-material match.

## Этап 7. Voice и audio

- Цель: one safe audio system.
- Зависимости: stage schemas and paid-call policy.
- Затрагиваемые файлы: `src/audio/*`, `src/news/voice_stage.py`, `src/voice_engine.py`, `solar_vs_nuclear_render.py`.
- Что нельзя делать раньше: expose UI paid button without budget/accounting.
- Критерии готовности: approval, audition, manual import, retries, 401/429 handling, duration validation.
- Тесты: mocked ElevenLabs, manual WAV, denial paths.
- Риски: accidental paid calls.
- Сложность: M.
- Результат: predictable voice generation.

## Этап 8. Render quality

- Цель: improve final video quality.
- Зависимости: reliable local assets and timings.
- Затрагиваемые файлы: `src/news/final_renderer.py`, shared FFmpeg helpers, subtitles.
- Что нельзя делать раньше: dynamic crop without validated source metadata.
- Критерии готовности: smart crop, transitions, subtitles safe zones, platform variants, output validation.
- Тесты: synthetic render, vertical/horizontal/cyrillic paths, corrupted asset handling.
- Риски: FFmpeg complexity and Windows escaping.
- Сложность: L.
- Результат: stable good-looking renders.

## Этап 9. UI

- Цель: project review and manual control.
- Зависимости: stable pipeline, assets, licenses, voice approval.
- Затрагиваемые файлы: new app/server/UI layer plus API boundary.
- Что нельзя делать раньше: build UI around unstable schemas.
- Критерии готовности: create project, scene review, candidate preview, replace asset, upload manual file, progress, errors, resume.
- Тесты: UI smoke, API contract, no paid calls without approval.
- Риски: UI может закрепить временную архитектуру.
- Сложность: XL.
- Результат: product usable by non-developer.

## Этап 10. Commercial readiness

- Цель: prepare for closed beta/commercial use.
- Зависимости: stable product UI and provenance.
- Затрагиваемые файлы: auth/user storage/BYOK/billing/logging/packaging.
- Что нельзя делать раньше: sell without license and secret isolation.
- Критерии готовности: user isolation, BYOK, license reports, billing/cost limits, packaging, support diagnostics.
- Тесты: security, multi-user, quota, backup/restore.
- Риски: legal/security/cost exposure.
- Сложность: XL.
- Результат: foundation for beta/SaaS/desktop.

## Рекомендуемый первый этап

Начать с Этапа 0: schemas, manifests, fake-provider no-network tests, data validation. Это создаст безопасную опору для всех следующих работ.

## Что нельзя реализовывать до него

- новые stock providers;
- UI выбора материалов;
- paid vision reranking;
- автоматический upload/publishing;
- коммерческий license report;
- масштабный refactor old providers.

## Что сохранить

- staged news project store;
- safe voice approval/manual WAV workflow;
- semantic scene schema as prototype;
- media library concept;
- old renderer/download lessons;
- anime_factory as isolated experiment;
- solar project as reference, not core.

## Что не следует расширять напрямую

- `src/production_plan/solar_vs_nuclear_render.py` as generic provider/render core;
- `legacy/*`;
- duplicated Pexels/Pixabay downloaders;
- old `src/voice_engine.py` as paid-call authority;
- static HTML previews as final UI foundation.

## Вопросы владельца проекта

1. Какой pipeline объявляем основным: `src/news` или old documentary?
2. Нужен ли коммерческий license proof с самого начала?
3. Какой режим paid APIs допустим: manual approval, budget, BYOK?
4. Какие форматы приоритетны: Shorts only or long YouTube too?
5. Нужна ли локальная desktop app раньше web UI?
6. Какие источники legal/product-approved: Pexels/Pixabay/Wikimedia/NASA/Archive/Envato?
7. Нужно ли сохранять anime_factory как отдельный продукт?

