# AI-YouTube

Локальный MVP-пайплайн для автоматизированного производства YouTube-видео. Сейчас проект рендерит короткий dev preview с цитатой Jordan Peterson, но структура уже разделяет настройки, планы, ассеты и рендер так, чтобы позже расшириться до 4-10 минутных роликов.

## Что уже есть

- `config/video_style.json` - главный файл настроек стиля и пайплайна.
- `pipeline.py` - единая точка запуска.
- `src/` - модули пайплайна.
- `outputs/quote_plan.json` - промежуточный план цитат.
- `outputs/scene_plan.json` - структурный план сцен.
- `outputs/asset_plan.json` - найденные ассеты и fallback-решения.
- `outputs/render_plan.json` - параметры рендера.
- `outputs/self_eval.json` - простая проверка результата после рендера.

## Установка

```bash
python -m venv venv
source venv/Scripts/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Для Git Bash на Windows:

```bash
source venv/Scripts/activate
```

Для PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

## Запуск dev preview

```bash
python pipeline.py --dev
```

Результат:

```text
outputs/final_preview.mp4
```

Dev mode короткий и быстрый: по умолчанию 7 секунд, 1280x720, 15 fps.

## Где менять стиль

Меняй настройки в:

```text
config/video_style.json
```

Ключевые поля:

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

Для кириллицы важно использовать полный путь к Windows-шрифту, например:

```json
"font_path": "C:/Windows/Fonts/arial.ttf"
```

## Куда класть музыку

Положи фон в:

```text
music/background.mp3
```

Если файла нет, пайплайн не падает и рендерит видео без музыки.

## Куда класть картинки

Положи портрет Jordan Peterson в:

```text
assets/images/
```

Лучше назвать файл понятно, например:

```text
assets/images/jordan_peterson.jpg
```

Если картинки нет, пайплайн создаст аккуратную темную заглушку.

## API ключи

Сейчас MVP не требует API ключей. На следующих этапах могут понадобиться:

- `OPENAI_API_KEY` - генерация интро-картинок, сценариев, планов сцен.
- `PEXELS_API_KEY` - поиск B-roll или изображений.
- `ELEVENLABS_API_KEY` - озвучка, но она намеренно не подключена в MVP.

Создай `.env` на основе `.env.example`. Не коммить `.env`.

## Архитектурный принцип

Пайплайн не пытается сразу “AI делает видео”. Он сначала создает промежуточные структуры:

- quote plan
- scene plan
- asset plan
- render plan

Это упрощает дебаг, повторяемость, self-eval и будущие production renders.
