# News To Short

## Назначение

`news_to_short` — режим создания вертикальных роликов из новости, идеи, текста и
пользовательских материалов. Он сохраняет строгий production gate по умолчанию и
поддерживает явно включаемый autonomous draft completion для сборки проверяемого
черновика, когда идеальный материал найден не для каждой сцены.

## Структура проекта

Каждый запуск создает `projects/<job_id>/`:

```text
projects/<job_id>/
  input/
  article/
  research/
  assets/
  master/
  replacement/
  localizations/
    ru/
      script/
      voice/
      subtitles/
      visual/
      output/
    en/
    es/
```

`master/` хранит общий визуальный план и источники. `localizations/<language>/` хранит отдельный сценарий, озвучку, субтитры, тайминги и output для языка.

## Что уже реализовано

- Создание job из URL, topic или text.
- Сохранение `job.json` и `input/input.json`.
- Базовый article ingestion.
- `research/claims.json`.
- `localizations/<language>/script/script.json`.
- `localizations/<language>/script/narration.txt`.
- `master/master_visual_plan.json`.
- `localizations/<language>/visual/visual_plan.json`.
- Dry-run до asset query manifest без загрузки тяжелых исходников.
- Resume существующего job.
- Модели локализаций `ru`, `en`, `es`.
- Модель прав на ассеты с блокировкой `reference_only`.
- `assets/assets_manifest.json` с приоритетом пользовательских файлов.
- Подбор разрешенных ассетов из локальной библиотеки `assets/library/metadata/media_index.json`.
- Запись `assets/missing_assets.json` для сцен, где нет разрешенного материала.
- Запись ошибок провайдеров без остановки всего manifest.
- Архитектурный TTS-контракт без автоматического ElevenLabs synthesis.
- Безопасный voice stage с `voice_manifest.json`, который не вызывает платный TTS без approval.
- Импорт ручной WAV-озвучки через `audio_file` provider со статусом `source_type=user_provided`.
- Генерация `subtitles.srt` и `subtitles.ass`.
- Технический `preview/preview.mp4` для проверки цепочки стадий.
- `quality/quality_report.json`.
- Финальный vertical MP4 renderer `news_to_short_final_renderer_v1`, который собирает 1080x1920 видео из локальных ассетов или безопасных авто text-card сцен.
- Export manifest, `description.txt`, `sources.json` и копии субтитров в `localizations/<language>/output/`.
- Два completion mode: backward-compatible `strict` (default) и явный
  `draft_complete`.
- `visual_assembly.slots`: от 1 до 4 визуальных отрезков на общей scene timeline;
  старый `selected_asset` читается как один полноэкранный slot без миграции.
- Fallback ladder `A_exact → B_composite → C_good_context → D_partial →
  E_generated → F_emergency` с детерминированным выбором и контролируемым reuse.
- Раздельные флаги draft/publish readiness. `partial_support` может попасть в draft,
  но не становится publish-ready и получает рекомендацию на замену.
- `--script-adaptation none|light`: максимум один проход только по проблемным сценам.
  Штатный light-адаптер offline/deterministic, не вызывает LLM; fact locks защищают
  числа, даты, измерения, имена/географию, uncertainty, causality и superlatives.
- Draft renderer создаёт `draft_1080x1920.mp4` и явно сохраняет
  `publish_ready=false`.
- Четыре артефакта замены: JSON, self-contained HTML, ordered queue и CSV timeline map
  в `replacement/`.
- Штатная замена одного slot через `assets replace`; исходник не меняется, операция
  сохраняет checksum/provenance/rights и помечает downstream render stages как stale.
- При отсутствии narration audio сохраняются visual assembly и replacement reports,
  а job завершается понятным статусом `voice_provider_required`.
- Rights/unknown license, `must_avoid`, conflicting/misleading content и технически
  непригодные файлы блокируются в обоих режимах.

## Что пока не реализовано

- Полноценная AI-локализация сценария.
- Автоматический поиск первоисточников.
- Автоматическая интеграция и скачивание Storyblocks/Envato.
- AI image generation: tier E/F сейчас использует только детерминированные локальные
  инфографики, текстовые карточки и backdrop.
- Обязательный live Vision gate; Q2.2B опирается на уже сохранённые semantic decisions
  и не выполняет Vision-вызовы.
- Автоматическая публикация на YouTube.
- Автоматическое принятие CC BY-SA: такие лицензии остаются под действующей policy и
  manual review.
- Голос остаётся configuration/approval dependent; draft completion не подменяет TTS.
- Продвинутые переходы, burn-in ASS и music mix в финальном render.

## Команды

```powershell
.\venv\Scripts\python.exe pipeline.py --news-to-short --topic "Почему киты-матери переворачиваются брюхом вверх?" --dry-run
.\venv\Scripts\python.exe pipeline.py --news-to-short --text "Текст новости..." --dry-run
.\venv\Scripts\python.exe pipeline.py --news-to-short --news-action resume --job-id "<JOB_ID>" --dry-run
.\venv\Scripts\python.exe pipeline.py --news-to-short --news-action run --job-id "<JOB_ID>" --until-stage export
```

В `strict`, если quality check возвращает `needs_review`, `final_render` сохраняет
блокирующий manifest. В `draft_complete` вместо publish gate применяется отдельный
draft gate: каждый narration scene должен иметь безопасный usable slot и существующее
narration audio.

Явный autonomous draft (без флага остаётся `strict`):

```powershell
.\venv\Scripts\python.exe pipeline.py --news-to-short --news-action resume `
  --job-id "<JOB_ID>" --completion-mode draft_complete --script-adaptation light
```

Отключить adaptation, не выключая draft completion:

```powershell
.\venv\Scripts\python.exe pipeline.py --news-to-short --news-action resume `
  --job-id "<JOB_ID>" --completion-mode draft_complete --script-adaptation none
```

Заменить ровно один visual slot без повторного research/script/asset search:

```powershell
.\venv\Scripts\python.exe -m src.content_creation.cli assets replace `
  --project-id "<JOB_ID>" --scene-id "scene_006" --slot-id "scene_006_slot_001" `
  --file "path\to\replacement.png" --source-url "https://optional.example/source" `
  --license-file "path\to\optional-proof.pdf"
```

После замены выполните обычный resume: stale `preview_render`, `quality_check`,
`final_render` и `export` будут построены заново, а research и asset search останутся
нетронутыми.

Импорт ручной озвучки:

```powershell
.\venv\Scripts\python.exe pipeline.py --voice-action import-audio --job-id "<JOB_ID>" --language ru --audio-file "path\to\narration.wav"
```

Approval записи для будущей полной ElevenLabs-генерации:

```powershell
.\venv\Scripts\python.exe pipeline.py --voice-action approve --job-id "<JOB_ID>" --language ru --voice-profile ru_dom
```

Новая app-граница:

```powershell
.\venv\Scripts\python.exe -m apps.news_to_short --topic "Почему киты поют?" --until-stage export
```
