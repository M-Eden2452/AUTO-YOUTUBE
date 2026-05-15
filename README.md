# AI-YouTube

AI-YouTube - локальная система для создания русскоязычных cinematic quote/thought videos для YouTube.

Проект начинался как MVP для мотивационных и психологических видео, но текущий фокус шире: интеллектуальные ролики с цитатами, сильными фразами, идеями из книг, фразами из фильмов, аниме, мультфильмов, а также мыслями актеров, философов и публичных деятелей.

Текущий рабочий пример все еще использует тему Jordan Peterson, но архитектура проекта рассчитана на более общий формат.

## Что делает проект

Pipeline собирает ролик по шагам:

- создает план цитат и мыслей;
- создает план сцен;
- подбирает или создает визуальные ассеты;
- готовит план музыки;
- строит render plan;
- рендерит preview или production-видео;
- создает YouTube-метаданные;
- пишет self-eval;
- экспортирует Markdown-заметку в Obsidian или в `outputs/obsidian_note_preview.md`.

Главная точка входа:

```bash
python pipeline.py
```

## Установка

```bash
python -m venv venv
source venv/Scripts/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

## Конфиг

Основные настройки находятся здесь:

```text
config/video_style.json
```

Там задаются:

- тема ролика;
- персона или источник;
- язык;
- визуальный стиль;
- размеры и fps;
- длительность сцен;
- путь к музыке;
- настройки Pexels/Pixabay;
- пути к JSON-планам;
- настройки Obsidian.

## Dev preview

```bash
python pipeline.py --dev
```

Dev-режим делает короткий безопасный preview-рендер:

- `outputs/final_preview.mp4`
- `outputs/quote_plan.json`
- `outputs/scene_plan.json`
- `outputs/asset_plan.json`
- `outputs/render_plan.json`
- `outputs/music_plan.json`
- `outputs/youtube_metadata.json`
- `outputs/self_eval.json`
- `outputs/render_stage.json`

## Production

```bash
python pipeline.py --prod
```

Production-режим использует `prod_resolution`, `prod_fps`, `prod_scene_duration`, `prod_font_size` и `prod_output_filename` из `config/video_style.json`.

Он может быть долгим, поэтому не запускай его как обычную проверку.

## Полезные режимы

Пропустить рендер и обновить только планы/metadata/Obsidian:

```bash
python pipeline.py --dev --skip-render
```

Только экспортировать Obsidian-заметку из готовых outputs:

```bash
python pipeline.py --export-obsidian
```

Запустить без экспорта в Obsidian:

```bash
python pipeline.py --dev --no-obsidian
```

Production-preview на первых сценах:

```bash
python pipeline.py --prod-preview
```

Обновить только music plan:

```bash
python pipeline.py --find-music
```

Повторно искать ассеты:

```bash
python pipeline.py --prod --refresh-assets
```

## Архитектура

```text
pipeline.py
src/
  config_loader.py
  quote_generator.py
  youtube_metadata.py
  scene_planner.py
  intro_generator.py
  music_finder.py
  asset_finder.py
  image_tools.py
  layout_renderer.py
  video_renderer.py
  music_tools.py
  self_eval.py
  obsidian_exporter.py
  utils.py
config/
  video_style.json
outputs/
assets/
music/
docs/
```

`pipeline.py` связывает шаги вместе. Реальная логика живет в `src/`.

## Outputs

Рабочие JSON-файлы:

- `quote_plan.json` - цитаты, мысли и карточки текста;
- `scene_plan.json` - сцены ролика;
- `asset_plan.json` - изображения, placeholder, b-roll и музыка;
- `render_plan.json` - технический план рендера;
- `music_plan.json` - план музыки;
- `youtube_metadata.json` - заголовки, описание, теги, thumbnail idea;
- `self_eval.json` - самопроверка;
- `render_stage.json` - журнал стадий рендера.

Видео и большие ассеты не нужно коммитить.

## Obsidian

Obsidian используется как человеческая база знаний для production-процесса.

Заметка может содержать:

- тему;
- статус;
- цитаты и идеи;
- сцены;
- заголовки;
- описание;
- теги;
- ассеты;
- ссылки на JSON;
- ссылку на итоговое видео;
- ручные заметки и следующие шаги.

Настройки Obsidian находятся в блоке `obsidian` файла `config/video_style.json`.

## API keys

Секреты хранятся только в `.env`.

Никогда не коммить:

- `.env`;
- API-ключи;
- `venv/`;
- mp4/mp3/mov/wav;
- большие ассеты.

Пример переменных лежит в `.env.example`.

Возможные ключи:

- `OPENAI_API_KEY`
- `PEXELS_API_KEY`
- `PIXABAY_API_KEY`

## Документация

Подробное объяснение проекта:

```text
docs/project_explanation.md
```

Отчет по чистке:

```text
docs/cleanup_report.md
```

## Безопасные проверки

```bash
python -m compileall pipeline.py src
python pipeline.py --dev
```

Полный `--prod` не считается безопасной быстрой проверкой, потому что может запускать долгий render.

## Статус проекта

Текущий проект - рабочая основа для дальнейшего развития:

- нужно вынести контент из Python-кода в knowledge base или data-файлы;
- нужно определить политику хранения JSON outputs;
- нужно почистить старые MVP-скрипты после подтверждения;
- нужно развить связку Obsidian -> pipeline -> Obsidian;
- нужно добавить аккуратную систему шаблонов для разных типов роликов.

