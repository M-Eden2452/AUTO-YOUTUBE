# AI-YouTube

AI-YouTube - локальная система для создания русскоязычных cinematic quote/thought videos для YouTube.

Текущая архитектура:

```text
одно приложение
+ много channel profiles
+ много video tasks
+ Obsidian как human knowledge base
+ JSON как machine runtime state
```

Проект больше не должен быть привязан к одному каналу или одной теме. Один и тот же `pipeline.py` может собирать ролики для `quotes`, `psychology`, `survival`, `anime_quotes`, `movie_quotes`, `philosophy` и других ниш.

## Быстрый запуск

Старый dev-режим без channel profile остается рабочим:

```bash
python pipeline.py --dev
```

Новый запуск через channel profile и video task:

```bash
python pipeline.py --channel quotes --video thoughts_too_late_001 --dev
```

Production-рендер запускай только явно:

```bash
python pipeline.py --channel quotes --video thoughts_too_late_001 --prod
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

## Experimental MOSS-TTS-Nano

MOSS-TTS-Nano is wired as an experimental local TTS provider for short test narration. It is separate from the existing ElevenLabs integration: ElevenLabs remains the default cloud voice path in `src/voice_engine.py`, while MOSS is a local subprocess provider in `src/tts_providers/moss_tts_provider.py`.

The local checkout lives at:

```text
G:/Projects/AI-YouTube/MOSS_TTS_Nano
```

It uses its own virtual environment:

```text
G:/Projects/AI-YouTube/MOSS_TTS_Nano/.venv
```

The separate venv keeps PyTorch, ONNX Runtime, Transformers, and MOSS-specific packages out of the main AI-YouTube `venv`. This matters because MOSS has ML dependencies that are larger and more fragile than the normal pipeline requirements.

Setup used for the local provider:

```powershell
cd G:/Projects/AI-YouTube/MOSS_TTS_Nano
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -e .
```

On Windows/Python 3.13, `WeTextProcessing` may fail because its `pynini` dependency tries to build from source and requires Microsoft C++ Build Tools. The current test path uses the ONNX backend without WeText normalization, so basic local generation can still work after installing the rest of the dependencies and `pip install -e .`.

Run the smoke test from the main project:

```powershell
python pipeline.py --test-moss-tts
```

The test writes:

```text
outputs/tts_tests/moss_tts_test.wav
```

MOSS config is intentionally disabled by default:

```json
"tts": {
  "provider": "moss_tts_nano",
  "moss_tts_path": "G:/Projects/AI-YouTube/MOSS_TTS_Nano",
  "enabled": false,
  "voice_clone_enabled": false,
  "prompt_audio_path": ""
}
```

MOSS is local and experimental, useful for offline testing and avoiding per-request cloud voice costs. ElevenLabs is still the production-oriented remote integration with the existing voice cache and API behavior. Voice cloning is not enabled for MOSS yet; the smoke test uses a built-in ONNX voice and does not require prompt audio.

## Структура проекта

```text
pipeline.py
src/
config/
channels/
  quotes/
    channel_config.json
    style.json
    prompts/
    templates/
  psychology/
  survival/
content/
  quotes/
    thoughts_too_late_001.json
outputs/
  quotes/
    thoughts_too_late_001/
assets/
music/
docs/
legacy/
```

`src/` - общий движок.  
`channels/` - настройки каналов.  
`content/` - конкретные video tasks.  
`outputs/` - машинные JSON-планы и локальные результаты запусков.  
`legacy/` - старые MVP-скрипты, которые больше не являются частью текущего pipeline.

## Channel Profiles

Channel profile задает стиль и контекст канала.

Пример:

```text
channels/quotes/channel_config.json
channels/quotes/style.json
```

`channel_config.json` хранит:

- `channel_id`;
- название канала;
- папку Obsidian;
- формат видео;
- язык по умолчанию;
- описание канала.

`style.json` хранит:

- visual style;
- image style;
- intro style;
- text style;
- music mood;
- transitions;
- animations;
- colors;
- avoid list.

## Video Tasks

Video task задает конкретный ролик. Это главный вход для креатива.

Пример:

```text
content/quotes/thoughts_too_late_001.json
```

В нем лежат:

- `video_id`;
- `chosen_title`;
- `title_variants`;
- `thumbnail_text`;
- `thumbnail_idea`;
- `description`;
- `disclaimer`;
- готовый список сцен;
- тексты на экране;
- авторы;
- длительности;
- mood;
- visual keywords;
- transitions;
- animations.

Codex/pipeline не должен придумывать новый креатив, если video task уже подготовлен. Он только превращает task JSON в runtime-планы, видео и Obsidian-заметку.

## Outputs

Для channel/video запуска файлы создаются здесь:

```text
outputs/quotes/thoughts_too_late_001/
```

Основные runtime-файлы:

- `quote_plan.json`;
- `scene_plan.json`;
- `asset_plan.json`;
- `render_plan.json`;
- `music_plan.json`;
- `youtube_metadata.json`;
- `self_eval.json`;
- `render_stage.json`;
- `final_preview.mp4` в dev;
- `final_video.mp4` в prod.

Видео, музыка, временные render-файлы и большие ассеты не коммитятся.

## Obsidian

Если vault существует по пути:

```text
G:/ObsidianBase/ObsidianBase/YouTube
```

pipeline создает базовую структуру:

```text
YouTube/
  00 Dashboard/
  01 Каналы/
    Цитаты и мысли/
    Психология/
    Выживание/
  02 Видео/
    Цитаты и мысли/
      thoughts_too_late_001/
  03 Шаблоны/
  04 Источники/
    Авторы/
    Фильмы/
    Аниме/
    Книги/
  05 Стили/
  06 Готовые ролики/
```

Для первого quotes video заметка создается здесь:

```text
G:/ObsidianBase/ObsidianBase/YouTube/02 Видео/Цитаты и мысли/thoughts_too_late_001/Некоторые мысли приходят слишком поздно.md
```

После dev-рендера `final_preview.mp4` копируется рядом с заметкой, а в заметке используется Obsidian-вставка:

```text
![[final_preview.mp4]]
```

Для production используется `final_video.mp4`.

## Как создать следующее видео в этом же канале

1. Создай новый файл:

```text
content/quotes/new_video_id.json
```

2. Заполни его по структуре существующего task.
3. Запусти:

```bash
python pipeline.py --channel quotes --video new_video_id --dev
```

## Как создать другой канал

1. Создай папку:

```text
channels/new_channel/
```

2. Добавь:

```text
channels/new_channel/channel_config.json
channels/new_channel/style.json
channels/new_channel/prompts/
channels/new_channel/templates/
```

3. Создай content task:

```text
content/new_channel/video_id.json
```

4. Запусти:

```bash
python pipeline.py --channel new_channel --video video_id --dev
```

## Безопасные проверки

```bash
python -m compileall pipeline.py src
python pipeline.py --dev
python pipeline.py --channel quotes --video thoughts_too_late_001 --dev
```

Полный `--prod` не запускается как обычная проверка.

## Секреты и Git

Не коммитить:

- `.env`;
- `venv/`;
- `MOSS_TTS_Nano/`;
- mp4/mp3/mov/wav;
- большие ассеты;
- `assets/broll/`;
- временные render-файлы.

`.env.example` можно хранить в Git. `.env` нельзя читать, выводить или коммитить.
