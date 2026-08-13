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

# PROJECT AUDIT INDEX

## 1. Назначение аудита

Этот аудит фиксирует фактическое состояние проекта автоматизации YouTube-контента в `G:\Projects\AI-YouTube`: какие подсистемы реально есть в коде, как они связаны, где pipeline проходит, где разрывается, какие части являются production-like, prototype, experiment или legacy, и какой порядок развития выглядит безопасным.

Аудит выполнен без реализации улучшений, без запуска тестов, без рендера, без скачивания материалов и без вызова платных API.

## 2. Дата, корень, Git

- Дата аудита: `2026-07-22T22:07:00+03:00`
- Корень проекта: `G:\Projects\AI-YouTube`
- Git branch: `master`
- Git commit: `adb40fa944318646aef66102cbb1352e40b7cacc`
- Тесты: не запускались

Начальный `git status --short` до создания файлов аудита:

```text
 M .gitignore
 M pipeline.py
 M requirements.txt
?? PROJECT_AUDIT.md
?? anime_factory/
?? apps/
?? channels/nature_science_news_ru/
?? docs/apps/
?? docs/architecture/
?? docs/project_map_and_app_split_plan.md
?? docs/superpowers/
?? outputs/audio_edits/
?? packages/
?? project_solar_vs_nuclear/
?? src/assets/
?? src/audio/
?? src/news/
?? src/production_plan/
?? tests/test_anime_factory_candidates.py
?? tests/test_anime_factory_cleanup.py
?? tests/test_anime_factory_dynamic_crop.py
?? tests/test_anime_factory_paths.py
?? tests/test_anime_factory_transcribe.py
?? tests/test_anime_factory_v3.py
?? tests/test_anime_factory_v4.py
?? tests/test_apps_structure.py
?? tests/test_news_to_short_assets.py
?? tests/test_news_to_short_delivery.py
?? tests/test_news_to_short_models.py
?? tests/test_news_to_short_pipeline.py
?? tests/test_news_to_short_renderer.py
?? tests/test_semantic_asset_selection.py
?? tests/test_voice_workflow.py
?? tests/test_youtube_shorts_production_plan.py
```

Важно: существующий `PROJECT_AUDIT.md` был рассмотрен как вторичный источник, но не изменялся и не считался источником истины без проверки по коду.

## 3. Изученные части

Полностью статически изучены:

- корневой entrypoint `pipeline.py`;
- app wrappers в `apps/`;
- основной news-to-short pipeline в `src/news/`;
- старый documentary/quote/visual pipeline в `src/`;
- production-plan и `project_solar_vs_nuclear`;
- `anime_factory`;
- providers и downloader-логика для Pexels, Pixabay, Unsplash, локальных файлов и медиатеки;
- voice/TTS-модули ElevenLabs, manual WAV, MOSS;
- subtitles, music, render-модули;
- конфигурации `.env.example`, `requirements.txt`, `config/`, `channels/`, `anime_factory/config.yaml`;
- manifests существующих проектов в `projects/` и `project_solar_vs_nuclear/`;
- локальная медиатека `assets/library/metadata/media_index.json`;
- тесты в `tests/` без запуска;
- документация `README.md` и `docs/`;
- legacy-модули в `legacy/`.

## 4. Не изученные полностью части

Не выполнялось глубокое чтение двоичных/тяжёлых данных:

- `.git`;
- `venv`;
- `__pycache__`;
- `MOSS_TTS_Nano` как внешний локальный движок и набор весов;
- готовые видео, аудио, изображения, рендеры и временные файлы;
- содержимое секретов в `.env`;
- фактическая работоспособность внешних API.

Тесты, рендер, скачивание ассетов, ElevenLabs, OpenAI, Pexels/Pixabay/Unsplash live-запросы не запускались.

## 5. Файлы аудита

- [Обзор](PROJECT_AUDIT_OVERVIEW.md)
- [Архитектура](PROJECT_AUDIT_ARCHITECTURE.md)
- [Pipeline](PROJECT_AUDIT_PIPELINES.md)
- [Компоненты](PROJECT_AUDIT_COMPONENTS.md)
- [Риски и тесты](PROJECT_AUDIT_RISKS_TESTS.md)
- [План развития](PROJECT_AUDIT_ROADMAP.md)
- [Machine-readable snapshot](PROJECT_AUDIT_SNAPSHOT.json)

## 6. Executive summary

Проект уже содержит несколько самостоятельных направлений автоматизации видео: старый documentary/quote pipeline, новый news-to-short pipeline, project-specific `solar_vs_nuclear`, отдельный `anime_factory`, size comparison и набор voice/render/downloader workflows.

Главный продуктовый замысел уже читается хорошо: брать тему, текст или URL, строить сценарий, сцены, визуальный план, подбирать материалы, озвучивать, субтитровать и рендерить вертикальные видео. Но фактическая реализация неоднородна: часть стадий полноценнее в старом pipeline, часть лучше спроектирована в новом `src/news`, а часть существует как отдельные эксперименты.

Самый важный технический разрыв находится в новом news-to-short pipeline: поиск ассетов возвращает metadata candidates, но основная цепочка не скачивает выбранные Pexels/Pixabay-видео и не передаёт стабильный local path в final renderer. В результате search -> selected asset -> download -> render не является надёжной end-to-end цепочкой.

Система лицензий и provenance пока недостаточна для коммерческого продукта: provider/source URL частично сохраняются, но author, rights_status, license URL, attribution, commercial-use flags, checksum и license snapshot не являются единой обязательной схемой.

Есть несколько дублирующих реализаций providers/downloaders/renderers/TTS. Новые источники вроде Wikimedia, NASA, Internet Archive, Envato Manual и Local Library можно добавить только после выделения общего provider-контракта, иначе дублирование и потеря метаданных усилятся.

## 7. Общая оценка зрелости

| Область | Оценка |
|---|---|
| Прототипирование видео-automation | сильная база |
| Надёжный один основной pipeline | работает частично |
| Коммерческая готовность | низкая |
| Лицензирование и provenance | требует исправления |
| UI для обычного пользователя | отсутствует |
| Расширяемость providers | требует архитектурной стабилизации |
| Тестовая база | есть полезные unit/integration-style тесты, но не запускались |
| CI/CD и упаковка | отсутствует |

## 8. Основные pipeline

| Pipeline | Начинается | Заканчивается | End-to-end | Ручные шаги | Критический разрыв | Состояние |
|---|---|---:|---:|---|---|---|
| News-to-short | `pipeline.py --news-to-short`, `python -m apps.news_to_short` | export/final render manifest | Нет стабильно | voice approval/manual WAV, review | stock search не скачивает selected assets | работает частично |
| Старый documentary/quote | `pipeline.py --channel ... --video ...` | `outputs/.../final_video.mp4` | Частично | config/content подготовка | смешаны legacy и текущие схемы | прототип/legacy |
| Production plan generator | `pipeline.py --production-plan solar_vs_nuclear` | `project_solar_vs_nuclear` manifests | Да как генератор | ручная проверка материалов/озвучки | заточен под один проект | experiment |
| Solar render | `pipeline.py --render-production-plan ...` | `05_project/final_vertical.mp4` | Условно | финальный WAV или paid TTS | платный ElevenLabs без общего approval gate | experiment |
| Anime Factory | `anime_factory/pipeline.py` | clips/previews/report | Частично | локальный episode input, выбор clips | отдельный продукт, нет stock/license flow | experiment |
| Size comparison | config `video_type=cinematic_size_comparison` | rendered comparison | Частично | CSV/content config | специализированный движок | experiment |
| Voice workflow | `pipeline.py --voice-action ...` | voice manifests/previews | Частично | approve/import | безопасный flow не полностью склеен с render | работает частично |
| Stock downloader scripts | отдельные модули | локальные stock files | Частично | запуск отдельными командами/функциями | не подключены к main news stage | prototype/legacy |

## 9. Основные компоненты

| Компонент | Состояние | Что реально работает | Главная проблема |
|---|---|---|---|
| Article ingestion | работает частично | URL/text/topic input, простой HTML parsing | нет robust extraction/fact checking |
| Script generation | прототип | deterministic Shorts script | нет LLM/factual validation |
| Scene planning | работает частично | scene timings/visual descriptions | разные схемы между pipeline |
| Visual semantics | прототип | heuristic `SemanticScene`, query generation, metadata rank | topic-specific, нет vision |
| Pexels | работает частично | официальный API search, часть download в отдельных модулях | не единый contract, landscape bias |
| Pixabay | работает частично | официальный API video/image/music в разных местах | дублирование, слабые licenses |
| Unsplash | прототип | image search metadata | не склеен с render |
| Local library | работает частично | index/search/dedupe by URL/path | нет rights_status/author/checksum |
| Asset download | работает частично | отдельные downloaders | search-render gap в news |
| Voice | работает частично | safe workflow + legacy ElevenLabs | несколько TTS путей, разная safety |
| Subtitles | работает частично | SRT/ASS generation | timing heuristic, нет word alignment |
| Music/SFX | прототип/отсутствует | old music engine | news music/SFX stage отсутствует |
| Render | работает частично | FFmpeg/MoviePy vertical render | нет smart crop/validation/resume |
| UI/API | отсутствует | static HTML previews only | нет product interface |
| Tests | работает частично | много тестовых файлов | не запускались; нет live/e2e гарантий |

## 10. Самые критичные проблемы

1. News-to-short asset search не скачивает выбранные provider assets.
2. Final renderer news требует локальный `path`, но selected candidates часто содержат только metadata URL.
3. `src/news/stock_video_downloader.py` существует, но не подключён к `src/news/pipeline.py`.
4. Voice stage в news безопасно блокирует paid TTS, но main path без ручного WAV/approval не идёт до финала.
5. Production-plan render может вызвать ElevenLabs напрямую при отсутствии WAV.
6. License/provenance schema неполная и несовместимая между pipeline.
7. Media library records не содержат `author` и `rights_status`.
8. Provider/downloader logic дублируется минимум в пяти местах.
9. Visual matching основан на metadata и heuristics, без анализа превью/кадров.
10. Pexels/Pixabay search часто запрашивает landscape/horizontal, а итоговый формат Shorts 9:16.
11. Нет retry/backoff/rate-limit strategy для внешних API.
12. Есть silent failures через broad `except`/`pass`.
13. Нет versioned schemas/migrations для manifests.
14. Нет atomic writes/locks/idempotency для проектного состояния.
15. Existing project statuses могут не соответствовать фактическому output.
16. Нет UI для просмотра/замены ассетов и управления генерацией.
17. Preview render в news зависит от уже существующего final output.
18. News music/SFX стадии отсутствуют.
19. Localization directories есть, но translation/adaptation flow отсутствует.
20. CI/CD, упаковка, lint/type gates отсутствуют.

## 11. Что реально можно использовать сегодня

- CLI-запуск старого pipeline для заранее подготовленных channel/content configs.
- News project scaffolding, script/visual-plan/asset-manifest generation и безопасный voice workflow.
- Manual WAV import/approval workflow.
- Отдельные stock search/download utilities при ручной интеграции результатов.
- Solar-vs-nuclear как project-specific experiment.
- Anime Factory как отдельный локальный workflow для нарезки/анализа видео.
- Media library index/search как начальную основу, но не как юридически надёжный provenance store.

## 12. Что блокирует полноценный результат

Главный блокер: отсутствие единой цепочки asset candidate -> selected asset -> downloaded file -> license/provenance -> renderer. Пока эта цепочка не стабилизирована, подключение новых источников увеличит хаос, а не качество результата.

## 13. Рекомендуемый следующий этап

Этап 0: зафиксировать schemas/manifests/tests и определить один основной pipeline, который должен пройти end-to-end на fake/local providers без внешних API. После этого вводить единый provider contract и только затем расширять Pexels/Pixabay и новые источники.

## 14. Подтверждение ограничений

Реализация улучшений не выполнялась. Исходный код, конфигурации, `.env`, зависимости, существующая документация, тесты, проекты, outputs и media assets не изменялись. Разрешёнными изменениями являются только файлы аудита `PROJECT_AUDIT_*`.

