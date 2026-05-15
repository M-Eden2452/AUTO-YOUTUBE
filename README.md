# AI-YouTube

Локальный MVP-pipeline для структурированного производства YouTube-видео. Сейчас проект собирает короткое превью с цитатой Jordan Peterson, сохраняет данные ролика в JSON-планы, генерирует YouTube-метаданные и экспортирует Markdown-заметку в Obsidian.

## Установка

```bash
python -m venv venv
source venv/Scripts/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Активация в PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

## Dev-превью

```bash
python pipeline.py --dev
```

Ожидаемые результаты:

- `outputs/final_preview.mp4`
- `outputs/quote_plan.json`
- `outputs/scene_plan.json`
- `outputs/asset_plan.json`
- `outputs/render_plan.json`
- `outputs/self_eval.json`
- `outputs/youtube_metadata.json`
- заметка в Obsidian или резервный файл `outputs/obsidian_note_preview.md`

Режим разработки специально короткий и быстрый: по умолчанию 7 секунд, 1280x720, 15 fps.

## Production-режим

```bash
python pipeline.py --prod
```

Продакшен-режим использует поля `prod_resolution`, `prod_fps` и `prod_scene_duration` из `config/video_style.json`. Это фундамент для будущих роликов на 4-10 минут: несколько сцен, интро, переходы, B-roll и voice-over.

## Экспорт в Obsidian

Настройки Obsidian находятся в:

```text
config/video_style.json
```

Текущий блок:

```json
"obsidian": {
  "enabled": true,
  "vault_path": "G:\\ObsidianBase\\ObsidianBase",
  "folder": "YouTube/Цитаты",
  "note_template": "quote_video",
  "write_json_links": true,
  "write_asset_links": true,
  "fallback_to_outputs": true
}
```

Если `vault_path` существует, заметка сохраняется сюда:

```text
G:\ObsidianBase\ObsidianBase\YouTube\Цитаты
```

Если путь к vault не найден, pipeline не падает. Вместо этого создается:

```text
outputs/obsidian_note_preview.md
```

Запустить только экспорт заметки из уже готовых outputs:

```bash
python pipeline.py --export-obsidian
```

Отключить экспорт в Obsidian для одного запуска:

```bash
python pipeline.py --dev --no-obsidian
```

Пропустить рендер и обновить только metadata/Obsidian:

```bash
python pipeline.py --dev --skip-render
```

## Что сохраняется в Obsidian

Markdown-заметка содержит:

- статус ролика
- базовые данные видео
- цитату или основной текст
- идеи заголовков
- описание, теги, ключевые слова и идею обложки для YouTube
- визуальный стиль
- ассеты
- ссылки на production JSON-планы
- следующие действия
- блок для ручных заметок
- self-eval проверки и предупреждения

## Конфиг

Стили и пути меняются здесь:

```text
config/video_style.json
```

Важные поля:

- `visual_style`
- `image_style`
- `intro_style`
- `layout`
- `resolution`
- `fps`
- `scene_duration`
- `font_path`
- `font_size`
- `text_color`
- `background_color`
- `music_path`
- `music_volume`
- `animation_type`
- `transition_type`

Для кириллицы оставляй полный путь к Windows-шрифту:

```json
"font_path": "C:/Windows/Fonts/arial.ttf"
```

## Ассеты

Музыка кладется сюда:

```text
music/background.mp3
```

Если музыки нет, pipeline соберет видео без музыки и не упадет.

Изображения кладутся сюда:

```text
assets/images/
```

Пример:

```text
assets/images/jordan_peterson.jpg
```

Если изображение не найдено, pipeline создаст темную placeholder-картинку и продолжит работу.

## API-ключи

MVP не требует API-ключей. На следующих этапах могут понадобиться:

- `OPENAI_API_KEY` для сценариев, структурных планов и генерации intro-изображений
- `PEXELS_API_KEY` для поиска ассетов
- `ELEVENLABS_API_KEY` для озвучки

Создай `.env` на основе `.env.example`. Никогда не коммить `.env`.

## GSD/Superpowers-процесс

Рекомендуемый цикл работы:

1. Проверить `git status`.
2. Закоммитить рабочее состояние перед рискованными изменениями.
3. Сделать небольшой архитектурный шаг.
4. Запустить `python pipeline.py --dev`.
5. Проверить outputs и self-eval.
6. Коммитить только безопасные исходники, конфиг, документацию, JSON и Markdown.

Pipeline использует промежуточные структуры:

- quote plan
- scene plan
- asset plan
- render plan
- YouTube metadata
- Obsidian note

Так систему проще дебажить и расширять от коротких preview до production-видео.

## Безопасный commit перед крупными изменениями

```bash
git status
git add .
git status --short
git commit -m "working MVP before large change"
```

Перед commit проверь, что не staged:

- `.env`
- `venv/`
- `outputs/*.mp4`
- `outputs/*.mov`
- `outputs/*.wav`
- `outputs/*.mp3`
- `assets/broll/`
- `music/*.mp3`

## Откат

Если нужно удалить локальные изменения и вернуться к последнему commit:

```bash
git reset --hard HEAD
```

Используй это осторожно: команда удаляет незакоммиченные изменения.
