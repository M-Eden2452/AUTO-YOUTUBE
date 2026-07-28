---
status: current
last_verified_commit: fb374fd
last_verified_date: 2026-07-28
source_paths:
  - projects/2026-07-28_pochemu-kosatki-vzryvayut-ogromnyh-ryb-2/job.json
  - projects/2026-07-28_pochemu-kosatki-vzryvayut-ogromnyh-ryb-2/quality/quality_report.json
  - projects/2026-07-28_pochemu-kosatki-vzryvayut-ogromnyh-ryb-2/render/final_render_manifest.json
  - projects/2026-07-28_pochemu-kosatki-vzryvayut-ogromnyh-ryb-2/localizations/ru/output/project_manifest.json
  - projects/2026-07-28_pochemu-kosatki-vzryvayut-ogromnyh-ryb-2/quality/visual_qa/contact_sheet_6frames.png
  - docs/handoff/PROJECT_RESCUE_MASTER_PLAN.md
---

# Product Evidence Gate 4.5

Код, Git и фактические runtime-артефакты имеют приоритет над этим отчётом.

## Результат

**FAIL.**

Технически исправный Short существует, но проверенный эталон не доказывает
визуально приемлемый video-first продукт: он сохранён как непубликуемый
`draft_complete`, все три сцены имеют только `partial_support`, а видео занимает
39% длительности. Две статичные фотографии удерживаются суммарно около 22.3 s
(61% ролика); последняя показывает выступление косатки в бассейне с трибунами
вместо требуемого open ocean.

## Эталон и неизменяемые доказательства

- Project ID:
  `2026-07-28_pochemu-kosatki-vzryvayut-ogromnyh-ryb-2`.
- MP4:
  `projects/2026-07-28_pochemu-kosatki-vzryvayut-ogromnyh-ryb-2/localizations/ru/output/draft_1080x1920.mp4`.
- MP4 SHA-256:
  `c45527c9af6b8a1d8196362115605e2d719acd1d91e4f15535e428ec94a76156`.
- Сохранённый contact sheet:
  `projects/2026-07-28_pochemu-kosatki-vzryvayut-ogromnyh-ryb-2/quality/visual_qa/contact_sheet_6frames.png`.
- Contact sheet SHA-256:
  `323fe3d678a871b6858f7432fe2f8c33ba9fa3bf3d83c2c048c67284f5c5fb2a`.
- Quality report SHA-256:
  `cbdb3688fb8096c97f9069e53945b95d1d02d7cde3ce29eacaa433fe3fa00098`.
- Final render manifest SHA-256:
  `c601382107764620e3101a60d9b9638a7b6b27ddb8c5f1b5c9f9941e2c7f5ff7`.
- Export manifest SHA-256:
  `90f660e6bc883286844d58d8e61cc10d18fc7dac5fa8af2056e0af0038731203`.

## Проверка gate

| Критерий | Результат | Доказательство |
|---|---|---|
| Файл существует и декодируется | Pass | 7,957,298 bytes; полный локальный decode video+audio завершился без ошибок |
| Vertical Short | Pass | H.264, 1080×1920, 9:16, 30 fps, 36.967 s |
| Звук | Pass технически | AAC mono 48 kHz, 36.459 s; narration WAV 36.459 s; mean −23.3 dB, peak −7.2 dB, клиппинг не обнаружен |
| Субтитры | Pass визуально | 19 SRT cues до 36.459 s; на contact sheets текст читаем, safe zone и края не нарушены |
| Права/provenance | Pass | `project rights-report` вернул `verified`: 3/3 assets, без missing source/license/checksum/local file |
| Реальные материалы | Pass | Pexels video и две Pixabay photos; infographic отсутствует |
| Без emergency fallback | Pass | `F_emergency=0`, но все три фрагмента только `C_good_context` |
| Video-first | **Fail** | 1 video + 2 images; только 39% video duration |
| Визуальная релевантность | **Fail** | 0 publish-ready scenes; 3/3 partial-support; сцена 003 показывает captive show вместо open ocean |
| Итоговый completion gate | **Fail** | `status=needs_review`, `output_kind=draft`, `publish_ready=false`, 3/3 slots требуют replacement |

Дополнительный contact sheet был локально извлечён во временный каталог в точках
начала, середины, границ сцен и конца. Он подтвердил отсутствие чёрных кадров и
обрезанных субтитров, но также подтвердил длительное удержание двух фотографий и
семантическое расхождение третьей сцены. Временный файл не является project
artifact и после проверки удалён.

## Повторная локальная верификация

На HEAD `fb374fd` результат независимо подтверждён без изменения runtime-проекта:

- хэши MP4, сохранённого contact sheet и manifests совпали с указанными выше;
- `ffprobe` подтвердил H.264 1080×1920 30 fps 36.967 s и AAC mono 48 kHz
  36.459 s; полный decode video и audio завершился без ошибок;
- свежий временный contact sheet из начала и границ сцен подтвердил читаемые
  субтитры, переход к статичному материалу около 14.2 s и captive-show фото
  примерно с 28.6 s до конца;
- narration WAV имеет mean −23.3 dB и peak −7.1 dB; обнаружена одна пауза
  0.535 s на границе сцен;
- `project status` по-прежнему возвращает `quality_status=needs_review` и 3/3
  `partial_support`, а `project rights-report` — `verified` для 3/3 assets.

Итог gate остаётся **FAIL**. Сеть, API, TTS, provider search/download, Vision и
реальный render при повторной проверке не запускались.

## Воспроизводимые команды

Фактически выполненная read-only проверка существующего проекта:

```powershell
.\venv\Scripts\python.exe -m ai_youtube project status `
  --project-id 2026-07-28_pochemu-kosatki-vzryvayut-ogromnyh-ryb-2 --json
```

Безопасная offline-проверка входа `create` в отдельном временном workspace:

```powershell
$stage45Input = (
  Get-Content -Raw -Encoding UTF8 `
    "projects\2026-07-28_pochemu-kosatki-vzryvayut-ogromnyh-ryb-2\input\input.json" |
  ConvertFrom-Json
).input_text
$stage45Workspace = Join-Path ([System.IO.Path]::GetTempPath()) "ai-youtube-stage45-repro"
.\venv\Scripts\python.exe -m ai_youtube --workspace $stage45Workspace create `
  --format vertical_short --template fullscreen_voiceover_v1 `
  --channel nature_science_news_ru --language ru `
  --pasted-script $stage45Input --input-mode pasted_script `
  --completion-mode draft_complete --dry-run --json
```

Безопасная offline-проверка `resume` существующего проекта:

```powershell
.\venv\Scripts\python.exe -m ai_youtube resume `
  --project-id 2026-07-28_pochemu-kosatki-vzryvayut-ogromnyh-ryb-2 `
  --dry-run --json
```

Синтаксис `create` и `resume` проверен по текущему `--help`. Две последние команды
на этом этапе не запускались: для gate было достаточно существующего complete E2E
проекта, а сохранённое состояние проекта не изменялось.

## Следующий ограниченный этап: 4.5-R Product Repair

Статус: **подготовлен, не начат**.

Цель: улучшить только визуальную сборку указанного проекта до повторного Product
Evidence Gate.

Ограниченная область:

1. Сначала просмотреть уже скачанные локальные video-кандидаты проекта; не выполнять
   provider search или download без отдельного разрешения.
2. Заменить только слабые визуальные слоты существующего проекта: убрать длительные
   still-image holds и captive-show материал, использовать rights-cleared
   open-ocean/research video, не выдавая generic B-roll за редкий удар.
3. Не менять research, claims, narration, TTS, project/storage contracts или CLI.
4. После явного разрешения на render повторить только stale
   `quality_check` → `final_render` → `export`.
5. Повторно проверить actual MP4 и contact sheet. Pass допустим только при
   video-first сборке, нормальных звуке/субтитрах, отсутствии emergency/infographic
   основного визуала и честном visual support.

Этапы 4.6, 5 и последующие до результата 4.5-R не начинаются.
