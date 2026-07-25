# Anime Factory

MVP-пайплайн для создания YouTube Shorts из локального `mp4`-файла аниме.

Пайплайн работает только с локальным видео. Он не скачивает серии, не публикует ролики на YouTube и не включает отдельные режимы вроде подкастов или стримов.

## Установка

```powershell
pip install -r anime_factory/requirements.txt
```

Также нужен `ffmpeg`, доступный из консоли:

```powershell
ffmpeg -version
ffprobe -version
```

Если команда не найдена, установите ffmpeg и добавьте папку `bin` в `PATH`.

## Подготовка видео

Положите исходный файл в:

```text
anime_factory/input/source.mp4
```

## Запуск

По умолчанию пайплайн ищет до 10 кандидатов и использует `--crop-mode auto`:

```powershell
python anime_factory/pipeline.py --input anime_factory/input/source.mp4 --episode episode_001 --max-clips 10 --crop-mode auto --force
```

Preview workflow для ручного выбора:

```powershell
python anime_factory/pipeline.py --input anime_factory/input/source.mp4 --episode episode_001 --candidate-count 30 --preview-only --force
```

Для сравнения вариантов кадрирования в отчете добавьте:

```powershell
python anime_factory/pipeline.py --input anime_factory/input/source.mp4 --episode episode_001 --candidate-count 30 --preview-only --compare-crops --force
```

После просмотра `report.html` создайте `selected.json`, например:

```json
{
  "selected_candidate_ids": [3, 7, 12, 18, 24]
}
```

И отрендерите выбранные клипы:

```powershell
python anime_factory/pipeline.py --input anime_factory/input/source.mp4 --episode episode_001 --render-selected anime_factory/episodes/episode_001/selected.json --crop-mode auto
```

Режимы камеры:

```powershell
python anime_factory/pipeline.py --input anime_factory/input/source.mp4 --episode episode_001 --max-clips 10 --crop-mode center --force
python anime_factory/pipeline.py --input anime_factory/input/source.mp4 --episode episode_001 --max-clips 10 --crop-mode blur --force
python anime_factory/pipeline.py --input anime_factory/input/source.mp4 --episode episode_001 --max-clips 10 --crop-mode dynamic --force
```

Готовые ролики появятся в:

```text
anime_factory/episodes/episode_001/output/
```

Промежуточные файлы сохраняются в:

```text
anime_factory/episodes/episode_001/artifacts/
```

Артефакты камеры:

```text
anime_factory/episodes/episode_001/artifacts/crops/
```

HTML-отчет:

```text
anime_factory/episodes/episode_001/report.html
```

## Crop Modes

- `auto` — пробует face-aware dynamic crop. Если лиц мало или детекция не сработала, использует center fallback.
- `smart_static` — выбирает один статический crop по найденным лицам/персонажам на протяжении клипа.
- `dynamic` — строит crop path по лицам, но тоже не падает и откатывается в center, если детекций мало.
- `center` — старое стабильное центральное кадрирование 1080x1920.
- `blur` — размытый вертикальный фон плюс исходная сцена поверх, чтобы сохранить больше контекста.

Для каждого short сохраняются:

- `short_001_faces.json` — найденные лица по сэмплам.
- `short_001_crop_path.json` — путь камеры или fallback crop.
- `short_001.srt` и `short_001.ass` — субтитры.

## Флаги

- `--input` путь к исходному видео.
- `--episode` имя эпизода, например `episode_001`.
- `--max-clips` количество клипов, по умолчанию `10`.
- `--candidate-count` сколько кандидатов искать и сохранять в `candidates.json`, по умолчанию `30`.
- `--preview-only` создать preview mp4, `report.html` и `selected.example.json` без финального render.
- `--preview-quality` качество preview: `fast` или `better`.
- `--compare-crops` создать side-by-side preview для сравнения `center`, `smart_static` и `blur`.
- `--render-selected` путь к `selected.json` для финального рендера выбранных candidate id.
- `--refine-boundaries` уточнить границы кандидатов по репликам, тишине и scene cuts.
- `--trim-edges-silence` обрезать тишину по краям при refinement.
- `--scene-detect` найти резкие смены сцен и сохранить `artifacts/scene_cuts.json`.
- `--min-duration` минимальная длина клипа в секундах, по умолчанию `20`.
- `--max-duration` максимальная длина клипа в секундах, по умолчанию `45`.
- `--crop-mode` режим камеры: `auto`, `smart_static`, `dynamic`, `center`, `blur`.
- `--disable-face-crop` отключить face-aware crop.
- `--crop-debug` оставить временное dynamic-видео без очистки.
- `--skip-transcribe` пропустить транскрибацию, если `transcript.json` и `subtitles_raw.srt` уже существуют.
- `--skip-render` не рендерить финальные ролики.
- `--force` очистить только `output/`, `previews/`, `artifacts/crops/` и `report.html` перед новым рендером. `source.mp4`, `audio.wav`, `transcript.json`, `subtitles_raw.srt`, `audio_features.json` и `candidates.json` не удаляются.
- `--clean-output` очистить только `output/` указанного episode и завершить работу без пересчета transcript/audio.
- `--whisper-model` модель faster-whisper, по умолчанию `small`.
