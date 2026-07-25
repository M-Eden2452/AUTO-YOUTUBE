# News To Short

## Назначение

`news_to_short` - новый режим для создания вертикальных роликов из новости, идеи, текста и пользовательских материалов. Первая фаза A+B создает структуру проекта, исследование, сценарий и визуальный план без платных API, озвучки и финального рендера.

## Структура проекта

Каждый запуск создает `projects/<job_id>/`:

```text
projects/<job_id>/
  input/
  article/
  research/
  assets/
  master/
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

## Что пока не реализовано

- Полноценная AI-локализация сценария.
- Автоматический поиск первоисточников.
- Интеграция Storyblocks/Envato.
- Скачивание исходников из внешних провайдеров для этого режима.
- ElevenLabs audition/final synthesis.
- Продвинутый финальный render с реальными скачанными video clips, переходами, burn-in ASS и музыкой.

## Команды

```powershell
.\venv\Scripts\python.exe pipeline.py --news-to-short --topic "Почему киты-матери переворачиваются брюхом вверх?" --dry-run
.\venv\Scripts\python.exe pipeline.py --news-to-short --text "Текст новости..." --dry-run
.\venv\Scripts\python.exe pipeline.py --news-to-short --news-action resume --job-id "<JOB_ID>" --dry-run
.\venv\Scripts\python.exe pipeline.py --news-to-short --news-action run --job-id "<JOB_ID>" --until-stage export
```

Если quality check возвращает `needs_review`, `final_render` сохраняет блокирующий manifest вместо того, чтобы создавать финальный MP4 с неожиданно неполными ассетами или голосом.

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
