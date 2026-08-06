# Assets

## Purpose

`src/assets/` — общий слой работы с визуальным материалом: контракт провайдера,
строка запроса и её язык, поиск и нормализация кандидатов, права и
происхождение, скачивание с технической валидацией, semantic evidence,
детерминированный отбор, лестница завершённости и отчёты для автора.

Пакет переиспользуется workflow, но ни одному из них не принадлежит. Он не
знает про стадии `news_to_short`, не читает `job.json` и не собирает ролик.

## Canonical ownership

| Ответственность | Owner |
|---|---|
| Контракт провайдера, типы ошибок, render-gate прав | `provider_contract.py` |
| Модели ассета, `ASSET_SCHEMA_VERSION`, словарь rights statuses | `models.py` |
| Права, лицензии, owner review | `license_policy.py` |
| Строка, отправляемая провайдеру, и её язык | `query_adapter.py` |
| Класс сцены и порядок опроса провайдеров | `scene_strategy.py`, `provider_routing.py` |
| HTTP, скачивание, техническая валидация файла | `http_client.py`, `download.py` |
| Кадры, метрики, перцептивное сходство, превью | `frame_primitives.py`, `frame_sampling.py`, `visual_metrics.py`, `perceptual_similarity.py`, `temporal_video_analysis.py`, `visual_preview.py` |
| Evidence и explainable verdict по кандидату | `semantic_selection/` |
| Semantic Vision backends, кэш, конфигурация, калибровка | `semantic_visual_*.py`, `semantic_decision_policy.py` |
| Завершённость сцены, fallback ladder, замена слота | `completion/` |
| Инфографика, нарисованная из данных сцены | `generated_infographic.py` |
| Отчёты автору и атрибуция | `review_bundle.py`, `attribution_export.py`, `completion/report.py` |
| Мост к `EvidenceRecord` проекта | `evidence_adapter.py` |

## Public boundaries

Снаружи импортируются: re-exports пакета (`src.assets.__init__`),
`src.assets.provider_contract`, `src.assets.license_policy`,
`src.assets.query_adapter`, `src.assets.completion`,
`src.assets.semantic_selection`, `src.assets.download`,
`src.assets.frame_sampling`, `src.assets.visual_preview`.

Реализации провайдеров и default registry находятся в `src/providers/`, а
единственный production-оркестратор поиска сегодня — `src.news.asset_manager`
и `src.news.asset_manifest_builder` (стадия `asset_search` шаблона
`fullscreen_voiceover_v1`).

## Main workflow

```text
visual plan / VisualBrief        src.content.visual_planning, src.news.visual_plan
  -> query_adapter               строка запроса и её язык для конкретного провайдера
  -> scene_strategy              класс сцены (source class)
  -> provider_routing            порядок опроса провайдеров
  -> StockProvider.search        src/providers/*  ->  AssetCandidate
  -> license_policy              решение о правах до любого использования
  -> candidate_ranker            оценка по метаданным, которые провайдер реально дал
  -> semantic_selection.decision explainable verdict по требованиям сцены
  -> semantic_visual_*           дополнительное Vision-evidence, если включено конфигом
  -> download + validate         checksum, размеры, длительность, целостность файла
  -> AssetProvenance             provider, источник, запрос, время, checksum
  -> completion.assembly/ladder  слоты сцены, ступень fallback, tier завершённости
  -> assets_manifest.json        пишет владелец стадии (src.news.asset_manager)
  -> потребители                 preview, replacement, quality_check, final render, export
```

Semantic evidence и Vision — включаемые части этого потока, а не обязательные:
без них отбор остаётся детерминированным.

## Main subpackages

- `completion/` — `modes` (что значит «готово»), `assembly` (сцена как
  несколько слотов), `ladder` (шесть ступеней fallback), `report`
  (слабые фрагменты), `replacement` (ручная замена одного слота).
- `semantic_selection/` — `scene_analyzer`, `evidence`, `candidate_ranker`,
  `decision`, `continuity_checker`, `models`.

## Persisted artifacts

Пакет не владеет состоянием проекта. Он производит содержимое и пишет
собственные отчёты; манифест ассетов записывает владелец стадии.

| Артефакт | Кто пишет |
|---|---|
| `assets/assets_manifest.json`, `assets/missing_assets.json` | `src.news.asset_manager` из содержимого этого пакета |
| `assets/sources.json`, `assets/ATTRIBUTION.md`, `assets/youtube_sources.txt` | `attribution_export.py` |
| `assets/review/visual_review_manifest.json`, `assets/review/visual_review_board.html` | `review_bundle.py` |
| `replacement/replacement_report.json`, `.html`, `replacement_queue.json`, `timeline_replacement_map.csv` | `completion/report.py` |
| Кэш превью (workspace-relative, по умолчанию `assets/cache/previews`) | `visual_preview.py` |
| Кэш semantic-результатов | `semantic_visual_cache.py` |

Формат записи ассета версионирован `ASSET_SCHEMA_VERSION`; старые манифесты
читаются tolerant-нормализацией, массовая миграция не выполняется.

## Rights and provenance

`license_policy.evaluate_asset_policy` и `apply_policy_to_candidate` —
единственный авторитет прав. Решение политики авторитетно: оно перезаписывает
поля лицензии кандидата, включая `review_required`.

Словарь допустимых `rights_status` — отдельная ответственность и принадлежит
`models.py`: `RIGHTS_ALLOWED_STATUSES` (immutable `frozenset` из `user_owned`,
`licensed`, `creative_commons`, `public_domain`) плюс именованные `RIGHTS_*`.
Consumers импортируют этот набор и своих копий не держат; `src.news.models`
re-export'ит исторические имена, но второго объявления не содержит. Словарь
задаёт только написание статуса и разрешением сам по себе не является:
`review_required`, `allowed_for_render` и политика сохраняют собственное вето, а
статус вне набора блокируется. Единственное санкционированное расширение —
`cleared` в `completion/modes.py` для evidence сгенерированных story card;
оно объявлено как `RIGHTS_LEGACY_CLEARED` и в canonical набор не входит.

Требование ревью monotonic. Уже записанное `review_required=True` — вход
политики, а не то, что она вправе снять: оно становится причиной
`record_review_required` и блокирует ассет. Учитываются все фактически
присутствующие представления записи — корневой флаг, копия внутри `license` и
сохранённый `policy_decision`; одного `True` достаточно, отсутствующее
представление разрешением не является. Снимает требование только подтверждённая
per-asset `rights_declaration` через `_manual_declaration_is_confirmed`.

Происхождение требования политика намеренно не выясняет: сохранённая запись не
позволяет отличить флаг оператора от прошлого ответа самой политики, а попытка
угадать — то, из-за чего помеченный ассет проходил. Owner decision 2026-08-06
принял цену этого решения как safety contract: policy re-evaluation, дозаполнение
metadata, resume и rebuild могут установить `True`, но сами по себе ревью больше
не снимают — ассет остаётся заблокированным до явного подтверждения владельца.
Это намеренное поведение, а не открытый дефект.

`provider_contract.ensure_license_allows_render` — точка, где отсутствие прав
превращается в отказ (`LicenseReviewRequired`), а не в тихое использование.

Каждый скачанный или скопированный файл получает `AssetProvenance` с provider,
`provider_asset_id`, source page, download URL, поисковым запросом, временем и
`checksum_sha256`. Ассет, заблокированный по правам, не попадает ни на одну
ступень `completion`.

## Completion and replacement

`completion/modes.py` разделяет вопросы, которые раньше сводились к одному
флагу: можно ли показать в черновике, можно ли выбрать автоматически, можно ли
публиковать, нужна ли ручная замена, заблокировано ли использование вовсе.

`completion/ladder.py` — шесть ступеней от точного совпадения до нейтральной
карточки, которая ничего не утверждает. Каждая ступень проходит через
`blocking_reasons`, поэтому материал без прав, с битым файлом, с попаданием в
`must_avoid` или с противоречащим evidence не появляется ни на одной из них.

`strict` остаётся режимом по умолчанию. `draft_complete` — явный opt-in,
всегда `publish_ready=false`; он не ослабляет права и не отключает gates.

`completion/replacement.py` заменяет один визуальный слот без повторного
research, script и asset search, определяя тип проекта через read-only
`ProjectRepository` и обновляя существующие записи владельцев.

## Does not own

- сценарий и нарратив — `src/content/script_engine`, `src/news/script_generator`;
- визуальный план сцен — `src/content/visual_planning`, `src/news/visual_plan`;
- voice, TTS и approval — `src/audio`;
- SceneTimeline и длительности сцен — `src.audio.scene_timeline`;
- субтитры — `src/subtitles`;
- финальную сборку ролика и кодирование — `src/news/final_renderer`;
- порядок стадий, resume и force-stage — `src/news/pipeline`;
- состояние проекта — `src/projects`, `src/project_foundation`,
  `src/news/project_store`;
- реализации провайдеров и default provider set — `src/providers`;
- AI research и извлечение фактов — `src/news/research_engine`;
- перевод произвольной темы: `query_adapter` не является переводчиком, и
  неподдерживаемый raw intent остаётся `query_translation_required`.

Второй provider contract, второй asset pipeline, второй semantic selector,
второй completion ladder и второй путь к локальной медиатеке не создаются.

## Important invariants

- `StockProvider` — единственный контракт провайдера; adapters и registry
  строятся вокруг него, а не рядом с ним.
- Решение о правах принимается до использования материала, а не после отбора.
- Поисковый запрос не является evidence: `candidate_ranker` не засчитывает
  `search_query` и производные от него теги как подтверждение совпадения.
- Отсутствующие метаданные сообщаются как `metadata_status="unavailable"` и не
  округляются до совпадения.
- Порядок отбора детерминирован и не зависит от того, какой провайдер ответил
  первым.
- Скачанный файл технически валидируется, а его `checksum_sha256` сохраняется.
- `completion` и его отчёты не обращаются ни к провайдеру, ни к сети, ни к
  платному сервису.
- Платный Vision не является обязательной runtime-зависимостью: он включается
  конфигурацией, а `semantic_selection.vision_validator` сам вызовов не делает.
- Сгенерированная инфографика детерминирована и становится обычным
  project-owned активом с provenance и checksum.

## How to extend

- **Новый провайдер** — реализация `StockProvider` в `src/providers/` и
  регистрация в `src.providers.registry`; второй контракт не создаётся.
- **Новый media type** — через существующие `models.py` и правила
  `config/license_policy.json`, а не через отдельный набор моделей.
- **Новый semantic evidence backend** — через `SemanticVisualBackend` и
  существующую конфигурацию; второй selector не создаётся.
- **Новая ступень завершённости** — только через `completion/modes.py` и
  `completion/ladder.py`.
- **Новый источник строки запроса** — через `query_adapter`, который остаётся
  единственной границей формирования provider-запроса.
- **Новый отчёт автору** — рядом с существующими `review_bundle` и
  `completion/report`, без второго review-формата на ту же информацию.

## Tests and verification

Ключевые области: `tests/test_asset_foundation_models.py`,
`tests/test_asset_foundation_providers.py`,
`tests/test_asset_foundation_http_download.py`,
`tests/test_asset_import_boundaries.py`,
`tests/test_provider_foundation_hardening.py`,
`tests/test_provider_routing.py`,
`tests/test_semantic_asset_selection.py`,
`tests/test_semantic_slot_decisions.py`,
`tests/test_semantic_visual_foundation.py`,
`tests/test_news_asset_manager_contract.py`,
`tests/test_news_to_short_assets.py`,
`tests/test_manual_asset_replacement.py`,
`tests/test_project_rights_report.py`.

Запускай targeted-модули изменяемой области через `.\venv\Scripts\python.exe`;
сеть, provider search, скачивание и Vision требуют отдельного разрешения
владельца.

## Related documents

- [AGENTS.md](../../AGENTS.md) — общие правила и границы.
- [docs/current/SYSTEM_MAP.md](../../docs/current/SYSTEM_MAP.md) — карта областей
  и текущих владельцев.
- [docs/current/ARCHITECTURE_BOUNDARY_MAP.md](../../docs/current/ARCHITECTURE_BOUNDARY_MAP.md)
  — callers, tests и persisted contracts.
- [docs/current/PRODUCT_PLAN.md](../../docs/current/PRODUCT_PLAN.md) —
  продуктовое направление и список «не создавать второго owner».
- [docs/current/PROJECT_EXECUTION_PLAN.md](../../docs/current/PROJECT_EXECUTION_PLAN.md)
  — порядок работ и текущий checkpoint.
- [docs/current/CLEANUP_REGISTRY.md](../../docs/current/CLEANUP_REGISTRY.md) —
  открытые findings и gates.
- ADR [0008](../../docs/adr/0008-canonical-provider-registry.md) — canonical
  provider registry; [0016](../../docs/adr/0016-two-engine-product-architecture.md)
  — два application engines поверх общих services.
