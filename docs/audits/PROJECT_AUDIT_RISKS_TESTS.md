# PROJECT AUDIT RISKS AND TESTS

## 1. Ключевое заявление по тестам

Тесты в рамках этого аудита не запускались.

Причина: пользователь запретил команды, которые могут создавать кеши, артефакты, проекты, файлы, внешние запросы или менять состояние. Тесты изучались статически.

## 2. Risk matrix

| Риск | Вероятность | Влияние | Критичность | Где находится | Как обнаружить | Рекомендуемое действие |
|---|---|---|---|---|---|---|
| News selected assets не имеют local path | Высокая | Final render fails | Critical | `src/news/asset_manager.py`, `src/news/final_renderer.py` | inspect assets_manifest vs renderer requirements | add unified download stage after selection |
| Standalone news downloader не подключён | Высокая | pipeline gap | Critical | `src/news/stock_video_downloader.py`, `src/news/pipeline.py` | call graph | integrate through provider contract |
| Incomplete license/provenance | Высокая | legal/commercial risk | Critical | `src/media_library.py`, news manifests | media index fields | define `AssetLicense` schema |
| Paid ElevenLabs call bypass in solar render | Средняя | unexpected cost | High | `src/production_plan/solar_vs_nuclear_render.py` | static code | require shared approval gate |
| Provider/download duplication | Высокая | bugs/inconsistent metadata | High | multiple provider files | duplicated APIs | one provider/downloader layer |
| No retries/backoff/rate-limit | Высокая | flaky runs | High | providers/downloaders/TTS | static code | common retry policy |
| Broad except/silent pass | Средняя | hidden failures | High | downloaders/solar | grep broad handlers | structured errors |
| Project manifests lack versioning | Высокая | migration/data breakage | High | `projects/*`, `project_store.py` | schema inspection | schema versions/migrations |
| No atomic writes/locks | Средняя | corrupted manifests | High | JSON stores | static code | temp-write rename/locks |
| Status/output mismatch | Средняя | false completed projects | High | `projects/*/job.json` | compare status vs files | validation/repair command |
| Visual matching metadata-only | Высокая | wrong visuals | High | semantic selection | inspect ranker | preview/frame validation |
| Landscape search for Shorts | Высокая | poor crop/relevance | High | Pexels/Pixabay wrappers | query params | vertical-aware strategy |
| No UI review layer | Высокая | poor usability | High | repo-wide | absence of server/UI | build after stable pipeline |
| News preview requires final output | Высокая | impossible review stage | High | `src/news/preview_renderer.py` | call path | render low-cost preview from selected assets |
| Missing music/SFX news stages | Средняя | incomplete product | Medium | `src/news/pipeline.py` | stage list | add after core stable |
| Localization is structural only | Средняя | limited multi-language product | Medium | `project_store.py`, pipeline | language flow | translation/adaptation stage |
| API keys in user env | Средняя | secret leakage risk | High | `.env`, code logs | static logs | secret-safe logging |
| Untrusted external downloads | Средняя | bad files/security risk | High | downloaders | static code | size/type/checksum validation |
| FFmpeg path/filter escaping | Средняя | Windows render failure | High | renderers | inspect subprocess args | centralized FFmpeg builder |
| No CI/CD | Высокая | regressions | High | repo root | no `.github` | add CI after tests stabilized |
| Heavy repo data/outputs committed or untracked | Высокая | repo bloat/confusion | Medium | `assets`, `outputs`, `projects` | status/counts | data policy |
| Commercial license proof absent | Высокая | cannot sell safely | Critical | all asset flows | provenance audit | rights-first asset model |
| No cost limits | Средняя | unexpected API spend | High | TTS/LLM/providers | static code | budgets/dry-run/accounting |
| No observability | Высокая | hard debugging | Medium | repo-wide | no structured logs | stage logs/events |
| Legacy code indistinct from active code | Высокая | wrong extension target | Medium | `legacy`, old `src` | import map | mark/migrate/deprecate |

## 3. Functional risks

Critical functional risks:

- automatic news-to-short cannot reliably reach final MP4 from topic/URL because visual assets are selected but not downloaded in main flow;
- final renderer assumes renderable local files;
- voice can block without manual import/approval;
- preview stage is not a true pre-final preview;
- multiple pipelines produce similar outputs with incompatible schemas.

## 4. Data risks

- Project state is stored as mutable JSON without schema versioning.
- No migration layer exists.
- No atomic write strategy was found.
- No lock/idempotency model was found.
- Generated outputs and source data live in the same repo tree, making accidental modification/versioning likely.

## 5. License and copyright risks

Most serious issue: provenance is not proof-grade.

Current data may include provider/source URLs, but not consistently:

- author missing from media library records;
- rights status missing from media library records;
- license URL/license snapshot missing;
- commercial-use and attribution flags missing;
- checksums missing;
- source page capture missing.

For article images, code correctly treats them as reference-only/unknown in some paths. But downstream guarantees are not strong enough to prove every final visual is licensed.

## 6. API and paid-call risks

- ElevenLabs is used in safe and unsafe patterns.
- OpenAI calls exist in legacy scripts.
- Pexels/Pixabay/Unsplash calls have no central quota/rate-limit handling.
- No global dry-run budget ledger exists.
- Solar render may synthesize voice if final WAV is missing.

## 7. Security risks

Observed:

- `.env` secret names exist; values were not disclosed.
- No `shell=True` was identified in reviewed grep results.
- FFmpeg is usually called with list args, which is safer than shell strings.

Risks remain:

- external downloads lack full MIME/size/checksum validation;
- user/local file paths are accepted by CLI and would need hardening before multi-user SaaS;
- absolute local paths appear in generated reports/manifests and can leak workstation structure;
- no upload sandbox/UI permission model exists;
- no secret-redaction logging layer was found.

## 8. Windows and Cyrillic risks

Project root and existing project IDs include Cyrillic. Python `Path` is used in many places, which helps, but FFmpeg subtitle/font/path handling is fragmented. Existing project names such as Russian titles create long Unicode paths. This should be explicitly tested before relying on production renders.

## 9. Performance and cost risks

- Several operations are sequential.
- No global concurrency/rate limits.
- No dedupe across all downloaders.
- Media files and generated outputs can accumulate.
- No lifecycle policy for previews/temp/renders.
- Paid TTS/LLM cost controls are not centralized.

## 10. Test files reviewed

Static test files found:

```text
tests/test_anime_factory_candidates.py
tests/test_anime_factory_cleanup.py
tests/test_anime_factory_dynamic_crop.py
tests/test_anime_factory_paths.py
tests/test_anime_factory_transcribe.py
tests/test_anime_factory_v3.py
tests/test_anime_factory_v4.py
tests/test_apps_structure.py
tests/test_documentary_visual_engine.py
tests/test_media_library.py
tests/test_moss_tts_provider.py
tests/test_news_to_short_assets.py
tests/test_news_to_short_delivery.py
tests/test_news_to_short_models.py
tests/test_news_to_short_pipeline.py
tests/test_news_to_short_renderer.py
tests/test_semantic_asset_selection.py
tests/test_size_comparison_engine.py
tests/test_voice_workflow.py
tests/test_voice_workflow_integration.py
tests/test_youtube_pipeline_channel_profiles.py
tests/test_youtube_shorts_production_plan.py
```

## 11. Static coverage map

| Test area | Files | Type by inspection | Notes |
|---|---|---|---|
| News models/pipeline | `test_news_to_short_models.py`, `test_news_to_short_pipeline.py` | unit/integration-style | uses temp projects/fakes/mocks |
| News assets | `test_news_to_short_assets.py`, `test_semantic_asset_selection.py` | unit | tests selection/ranking behavior |
| News delivery/render | `test_news_to_short_delivery.py`, `test_news_to_short_renderer.py` | integration-style | likely creates temp files if run |
| Voice workflow | `test_voice_workflow.py`, `test_voice_workflow_integration.py` | unit/integration-style | mocks safer provider behavior |
| Media library | `test_media_library.py` | unit | covers index helpers |
| Documentary visual engine | `test_documentary_visual_engine.py` | unit/integration-style | old pipeline coverage |
| Production plan | `test_youtube_shorts_production_plan.py` | unit | fixed project behavior |
| Anime | multiple `test_anime_factory_*` | unit/integration-style | local media workflow |
| MOSS | `test_moss_tts_provider.py` | unit | external availability likely skipped/mocked |
| Apps | `test_apps_structure.py` | unit | wrappers/imports |
| Size comparison | `test_size_comparison_engine.py` | unit | specialized |

## 12. What is not covered enough

Important gaps:

- live Pexels/Pixabay/Unsplash API integration;
- actual download retries/failure handling;
- license/provenance completeness;
- news full end-to-end from topic/URL to final MP4;
- paid-call safety across all TTS paths;
- FFmpeg render on Windows with Cyrillic paths;
- corrupted/partial downloads;
- migrations/versioned manifests;
- media library missing-file recovery;
- multi-language generation and export;
- UI/manual asset replacement;
- publishing/export platform-specific behavior;
- security/path traversal tests;
- performance/cost tests.

## 13. Tests needed before refactoring

Before provider/render refactor:

1. Fake provider end-to-end news pipeline test that produces a tiny MP4 using local fake assets.
2. Asset schema roundtrip test for provider -> candidate -> selected -> downloaded -> render.
3. License schema validation test.
4. Media library migration test with old records.
5. Retry/backoff tests with fake HTTP failures.
6. Windows/Cyrillic path render smoke test using synthetic assets.
7. Paid TTS approval denial/approval tests across news, old and solar paths.
8. No-network dry-run test for all CLI modes.

## 14. CI/CD

No GitHub Actions, Docker, packaging, installer, lint, format or type-check configuration was found in the reviewed structure. This is a blocker for team/commercial development, but should be added only after defining the first stable test target.

