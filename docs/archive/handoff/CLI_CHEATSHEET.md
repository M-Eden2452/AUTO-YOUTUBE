# CLI Cheatsheet

Команды ниже основаны на текущем `pipeline.py`. Команды `story-card create` и `story-card batch` пока не существуют и указаны только как planned в `NEXT_PLAN.md`.

## Git Bash старт

```bash
cd /g/Projects/AI-YouTube
source venv/Scripts/activate
python -B pipeline.py --help
```

## news-to-short

Создать job до `visual_plan` без платных API:

```bash
python -B pipeline.py --news-to-short --news-action create --topic "Тема короткого ролика" --dry-run --until-stage visual_plan
```

Создать job из текста до `visual_plan`:

```bash
python -B pipeline.py --news-to-short --news-action create --text "Короткий исходный текст" --dry-run --until-stage visual_plan
```

Запустить существующий job:

```bash
python -B pipeline.py --news-to-short --news-action run --job-id <job_id> --dry-run
```

Resume существующего job:

```bash
python -B pipeline.py --news-to-short --news-action resume --job-id <job_id> --dry-run
```

Запустить только `asset_search` для существующего job:

```bash
python -B pipeline.py --news-to-short --news-action run --job-id <job_id> --stage asset_search --dry-run
```

### Strict и autonomous draft completion

`strict` остаётся default и сохраняет прежний publish gate. Opt-in draft:

```bash
python -B pipeline.py --news-to-short --news-action resume --job-id <job_id> \
  --completion-mode draft_complete --script-adaptation light
```

`--script-adaptation none` отключает единственный adaptation pass. Штатный `light`
работает offline и детерминированно; не вызывает LLM. Draft допускает честный
`partial_support`, но никогда неизвестные/запрещённые права, `must_avoid`, конфликт,
misleading content или технически непригодный файл. Итоговый MP4 имеет имя
`draft_1080x1920.mp4` и `publish_ready=false`.

Слабые slots перечислены в:

```text
replacement/replacement_report.json
replacement/replacement_report.html
replacement/replacement_queue.json
replacement/timeline_replacement_map.csv
```

Заменить один slot, не повторяя research/script/search:

```bash
python -m src.content_creation.cli assets replace \
  --project-id <job_id> --scene-id <scene_id> --slot-id <slot_id> \
  --file <local-image-or-video> \
  --source-url <optional-url> --license-file <optional-proof>
```

Операция сохраняет checksum/provenance и помечает downstream quality/render как
`stale`. Команда одновременно является явной декларацией права пользователя на этот
локальный файл; `--license-file` прикладывает дополнительное подтверждение.
Если голос не настроен, draft run возвращает `voice_provider_required`,
сохраняя visual assembly и replacement reports; после импорта WAV используйте resume.

## Visual preview / semantic inspect

Подготовить visual preview для одной сцены в offline/cache режиме:

```bash
python -B pipeline.py visual-preview prepare --project-id <job_id> --scene-id <scene_id> --offline
```

Посмотреть summary visual preview:

```bash
python -B pipeline.py visual-preview inspect --project-id <job_id>
```

Посмотреть summary semantic visual:

```bash
python -B pipeline.py semantic-visual inspect --project-id <job_id>
```

## Voice workflow

Список voice profiles:

```bash
python -B pipeline.py --voice-action list --news-channel nature_science_news_ru
```

Preflight без генерации аудио:

```bash
python -B pipeline.py --voice-action preflight --news-channel nature_science_news_ru --voice-profile <profile_id> --text "Короткий тест."
```

Импорт ручного WAV:

```bash
python -B pipeline.py --voice-action import-audio --job-id <job_id> --audio-file <path/to/manual.wav>
```

## Production catalog (read-only)

```bash
python -B pipeline.py applications list
python -B pipeline.py applications inspect --application content_creator
python -B pipeline.py formats list
python -B pipeline.py formats inspect --format vertical_short
python -B pipeline.py templates list
python -B pipeline.py templates list --application content_creator
python -B pipeline.py templates list --format vertical_short
python -B pipeline.py templates inspect --template story_card_text_only_v1
python -B pipeline.py templates inspect --template story_card_short_v1
python -B pipeline.py export-targets list
python -B pipeline.py export-targets inspect --target youtube_shorts
```

Добавьте `--json` к любой из команд выше для машиночитаемого вывода. Эти
команды не вызывают сеть, providers, Vision, TTS, не создают project/render
файлов. Подробности: `docs/implementation/production_catalog_foundation/CATALOG_REPORT.md`.

## Targeted unittest

```bash
python -m unittest tests.test_story_card_short_renderer -v
python -m unittest tests.test_temporal_video_analysis -v
python -m unittest tests.test_semantic_decision_policy -v
python -m unittest tests.test_production_catalog_foundation -v
```

## Готовая сова

Текущий готовый файл:

```text
projects/story_card_owl_test/final_test.mp4
```

В Git Bash можно открыть проводником:

```bash
explorer.exe projects/story_card_owl_test
```

## Запрещено без отдельного разрешения

```bash
python -B pipeline.py semantic-backend evaluate --backend openai --allow-paid-vision ...
python -B pipeline.py semantic-visual analyse --backend openai ...
python -B pipeline.py --voice-action audition ...
python -B pipeline.py --test-moss-tts
python -B pipeline.py --test-moss-voices
python -B pipeline.py media-library migrate --apply ...
python -m unittest discover
git reset ...
git clean ...
```

Planned, пока не поддерживается текущим `pipeline.py`:

```bash
python -B pipeline.py story-card create ...
python -B pipeline.py story-card batch --queue <queue.json>
```
